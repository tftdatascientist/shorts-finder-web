"""Orkiestracja pełnego pipeline'u analizy — transkrypcja → AI → wyniki."""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional

from models import Analysis, AnalysisStatus, Proposal, get_analysis
from transcription import fetch_transcript
from ai_analysis import analyze_transcript

logger = logging.getLogger(__name__)


async def run_pipeline(session_id: str, openai_api_key: str) -> None:
    """Uruchamia pełny pipeline w tle. Aktualizuje obiekt Analysis w store."""
    analysis = get_analysis(session_id)
    if not analysis:
        return

    work_dir = Path(tempfile.mkdtemp(prefix=f"shorts_{session_id[:8]}_"))

    try:
        # Krok 1: metadane
        _update(analysis, AnalysisStatus.fetching_meta, "Pobieram metadane filmu…")
        video_id, title = await _fetch_meta(analysis.url)
        analysis.video_id = video_id
        analysis.video_title = title
        _update(analysis, AnalysisStatus.fetching_meta, f"Film: {title}")

        # Krok 2: transkrypcja
        _update(analysis, AnalysisStatus.transcribing, "Szukam transkrypcji…")

        segments = []
        progress_msgs = []

        def on_progress(msg: str):
            progress_msgs.append(msg)
            _update(analysis, AnalysisStatus.transcribing, msg)

        loop = asyncio.get_event_loop()
        segments = await loop.run_in_executor(
            None,
            lambda: fetch_transcript(
                url=analysis.url,
                work_dir=work_dir,
                openai_api_key=openai_api_key,
                progress=on_progress,
            ),
        )

        if not segments:
            _update(analysis, AnalysisStatus.error, "Nie udało się uzyskać transkrypcji — film może nie mieć napisów YT, a klucz OpenAI nie jest skonfigurowany.")
            return

        _update(analysis, AnalysisStatus.transcribing, f"Transkrypcja gotowa: {len(segments)} segmentów")

        # Krok 3: analiza AI
        _update(analysis, AnalysisStatus.analyzing, "Analizuję transkrypcję przez AI (30–60 sekund)…")

        async def ai_progress(msg: str):
            _update(analysis, AnalysisStatus.analyzing, msg)

        proposals_raw = await analyze_transcript(
            segments=segments,
            api_key=openai_api_key,
            model="gpt-4o-mini",
            progress_fn=ai_progress,
        )

        if not proposals_raw:
            _update(analysis, AnalysisStatus.error, "AI nie zwróciło żadnych propozycji. Spróbuj ponownie.")
            return

        analysis.proposals = [Proposal(**p) for p in proposals_raw]
        _update(analysis, AnalysisStatus.done, f"Gotowe — {len(analysis.proposals)} propozycji")

    except Exception as exc:
        logger.exception("Pipeline błąd dla sesji %s", session_id)
        _update(analysis, AnalysisStatus.error, f"Błąd: {exc}")
    finally:
        # Sprzątanie plików tymczasowych
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


async def _fetch_meta(url: str) -> tuple[str, str]:
    """Zwraca (video_id, title) przez yt-dlp bez pobierania."""
    import yt_dlp

    def _run():
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("id", ""), info.get("title", "Film bez tytułu")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


def _update(analysis: Analysis, status: AnalysisStatus, msg: str) -> None:
    analysis.status = status
    analysis.progress_msg = msg
    logger.info("[%s] %s: %s", analysis.id[:8], status.value, msg)
