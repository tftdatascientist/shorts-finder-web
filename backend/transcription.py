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
    """Pobiera napisy — próbuje youtube-transcript-api, potem Innertube."""
    segs = _try_transcript_api(url)
    if segs:
        return segs
    return _try_innertube(url)


def _try_transcript_api(url: str) -> List[dict]:
    """youtube-transcript-api — działa lokalnie, blokowane na serwerach DC."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        video_id = _extract_video_id(url)
        if not video_id:
            return []
        api = YouTubeTranscriptApi()
        for lang in ("pl", "en", None):
            try:
                tl = api.list(video_id)
                t = tl.find_transcript([lang]) if lang else next(iter(tl))
                fetched = t.fetch()
                segs = []
                for s in fetched:
                    text = str(s.text).strip()
                    if text:
                        segs.append({"start": float(s.start), "end": float(s.start + s.duration), "text": text})
                if segs:
                    return segs
            except Exception:
                continue
    except Exception as exc:
        logger.debug("youtube-transcript-api błąd: %s", exc)
    return []


def _try_innertube(url: str) -> List[dict]:
    """Innertube API — wewnętrzne API YouTube, jako fallback."""
    import json as _json, urllib.request, urllib.error, html, re as _re

    video_id = _extract_video_id(url)
    if not video_id:
        return []

    try:
        # Krok 1: pobierz player response przez Innertube
        innertube_url = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
        payload = _json.dumps({
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.09.37",
                    "androidSdkVersion": 30,
                    "hl": "pl",
                    "gl": "PL",
                }
            }
        }).encode()

        req = urllib.request.Request(
            innertube_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11)",
                "X-YouTube-Client-Name": "3",
                "X-YouTube-Client-Version": "19.09.37",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            player = _json.loads(r.read())

        # Krok 2: wyciągnij URL listy napisów (timedtext)
        captions_data = (
            player.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        if not captions_data:
            logger.debug("Innertube: brak napisów dla %s", video_id)
            return []

        # Preferuj pl → en → pierwsze
        track = None
        for lang in ("pl", "en"):
            track = next((t for t in captions_data if t.get("languageCode") == lang), None)
            if track:
                break
        if not track:
            track = captions_data[0]

        base_url = track["baseUrl"]
        # Pobierz w formacie XML (domyślny) i przekonwertuj
        xml_url = base_url + "&fmt=srv3"
        with urllib.request.urlopen(xml_url, timeout=15) as r:
            xml_text = r.read().decode("utf-8", errors="replace")

        return _parse_timedtext_xml(xml_text)

    except Exception as exc:
        logger.debug("Innertube API błąd: %s", exc)
        return []


def _parse_timedtext_xml(xml: str) -> List[dict]:
    import re as _re, html
    segs = []
    seen = set()
    for m in _re.finditer(r'<p\b[^>]*\bt="(\d+)"[^>]*\bd="(\d+)"[^>]*>(.*?)</p>', xml, _re.DOTALL):
        start_ms = int(m.group(1))
        dur_ms = int(m.group(2))
        raw = m.group(3)
        text = html.unescape(_re.sub(r"<[^>]+>", "", raw)).strip()
        if text and text not in seen:
            seen.add(text)
            segs.append({
                "start": start_ms / 1000,
                "end": (start_ms + dur_ms) / 1000,
                "text": text,
            })
    return segs


def _parse_srt_text(srt: str) -> List[dict]:
    import re as _re, html
    segs = []
    seen = set()
    blocks = _re.split(r"\n\s*\n", srt.strip())
    time_re = _re.compile(
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
    )
    for block in blocks:
        lines = block.strip().splitlines()
        m = None
        text_lines = []
        for line in lines:
            if m is None:
                m = time_re.match(line.strip())
            elif not line.strip().isdigit():
                text_lines.append(line.strip())
        if not m or not text_lines:
            continue
        h1, m1, s1, ms1 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        h2, m2, s2, ms2 = int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8))
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        text = html.unescape(" ".join(text_lines)).strip()
        text = _re.sub(r"<[^>]+>", "", text).strip()
        if text and text not in seen and end > start:
            seen.add(text)
            segs.append({"start": start, "end": end, "text": text})
    return segs


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
