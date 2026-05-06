"""Kaskadowy pipeline transkrypcji — port z gui/transcription/pipeline.py."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str], None]


def fetch_transcript(
    url: str,
    work_dir: Path,
    openai_api_key: Optional[str] = None,
    progress: Optional[ProgressFn] = None,
) -> List[dict]:
    """Zwraca listę segmentów [{"start": float, "end": float, "text": str}].

    Kaskada: YT napisy → Whisper API.
    W wersji web pomijamy embedded subs i Claude CLI (nie ma lokalnych plików wideo).
    """
    _emit(progress, "Szukam napisów YouTube…")
    segs = _try_yt_subtitles(url, work_dir)
    if segs:
        _emit(progress, f"Napisy YT: {len(segs)} segmentów")
        return segs

    if openai_api_key:
        _emit(progress, "Brak napisów YT — pobieram audio do Whisper…")
        segs = _try_whisper(url, work_dir, openai_api_key, progress)
        if segs:
            _emit(progress, f"Whisper API: {len(segs)} segmentów")
            return segs

    _emit(progress, "Nie udało się uzyskać transkrypcji.")
    return []


def _extract_video_id(url: str) -> Optional[str]:
    import re
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def _try_yt_subtitles(url: str, work_dir: Path) -> List[dict]:
    """Pobiera napisy przez youtube-transcript-api (nie wymaga logowania)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

        video_id = _extract_video_id(url)
        if not video_id:
            return []

        # Próbuj kolejno: pl, en, cokolwiek dostępne
        transcript = None
        for lang in (["pl"], ["en"], None):
            try:
                if lang:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=lang)
                else:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    t = next(iter(transcript_list), None)
                    if t:
                        transcript = t.fetch()
                if transcript:
                    break
            except Exception:
                continue

        if not transcript:
            return []

        segs = []
        for item in transcript:
            start = float(item.get("start", 0))
            duration = float(item.get("duration", 1))
            text = str(item.get("text", "")).strip()
            if text:
                segs.append({"start": start, "end": start + duration, "text": text})
        return segs

    except Exception as exc:
        logger.debug("youtube-transcript-api niedostępne: %s", exc)
        return []


def _parse_vtt(path: Path) -> List[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        import re
        segments = []
        seen = set()
        pattern = re.compile(
            r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
        )
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            m = pattern.match(lines[i].strip())
            if m:
                h1, m1, s1, ms1 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                h2, m2, s2, ms2 = int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8))
                start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
                end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    clean = re.sub(r"<[^>]+>", "", lines[i]).strip()
                    if clean:
                        text_lines.append(clean)
                    i += 1
                content = " ".join(text_lines).strip()
                if content and content not in seen and end > start:
                    seen.add(content)
                    segments.append({"start": start, "end": end, "text": content})
            else:
                i += 1
        return segments
    except Exception as exc:
        logger.debug("VTT parse error: %s", exc)
        return []


def _try_whisper(
    url: str,
    work_dir: Path,
    api_key: str,
    progress: Optional[ProgressFn],
) -> List[dict]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.debug("ffmpeg niedostępny")
        return []

    try:
        from openai import OpenAI
    except ImportError:
        return []

    audio_path = work_dir / "whisper_audio.mp3"
    try:
        # Pobierz tylko audio przez yt-dlp
        _emit(progress, "Pobieram audio (yt-dlp)…")
        import yt_dlp
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(work_dir / "whisper_src.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        src_files = list(work_dir.glob("whisper_src.*"))
        if not src_files:
            return []
        src = src_files[0]

        _emit(progress, "Konwertuję audio do MP3…")
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(src),
             "-vn", "-ar", "16000", "-ac", "1", "-b:a", "32k",
             str(audio_path), "-loglevel", "error"],
            capture_output=True, timeout=120,
        )
        src.unlink(missing_ok=True)

        if result.returncode != 0 or not audio_path.exists():
            return []

        size_mb = audio_path.stat().st_size / 1_048_576
        if size_mb > 24:
            _emit(progress, f"Audio {size_mb:.0f}MB — przycinam do limitu API…")
            trimmed = work_dir / "whisper_trim.mp3"
            subprocess.run(
                [ffmpeg, "-y", "-i", str(audio_path), "-fs", "24000000",
                 str(trimmed), "-loglevel", "error"],
                capture_output=True, timeout=60,
            )
            if trimmed.exists():
                audio_path.unlink(missing_ok=True)
                audio_path = trimmed

        _emit(progress, "Wysyłam do OpenAI Whisper API…")
        client = OpenAI(api_key=api_key)
        with audio_path.open("rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                language="pl",
            )

        segs = []
        for s in (getattr(response, "segments", None) or []):
            start = float(getattr(s, "start", 0))
            end = float(getattr(s, "end", start + 1))
            text = str(getattr(s, "text", "")).strip()
            if text and end > start:
                segs.append({"start": start, "end": end, "text": text})
        return segs

    except Exception as exc:
        logger.warning("Whisper błąd: %s", exc)
        return []
    finally:
        audio_path.unlink(missing_ok=True)
        for f in work_dir.glob("whisper_*"):
            f.unlink(missing_ok=True)


def _emit(fn: Optional[ProgressFn], msg: str) -> None:
    logger.info(msg)
    if fn:
        fn(msg)
