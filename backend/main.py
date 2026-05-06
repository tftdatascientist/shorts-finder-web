"""FastAPI backend — Shorts Finder Web."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models import AnalysisStatus, create_analysis, get_analysis, list_analyses
from pipeline import run_pipeline

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Shorts Finder API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji zawęź do domeny frontendu
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

YT_URL_RE = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]+"
)


# ── Schematy ──────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    url: str


class AnalyzeResponse(BaseModel):
    session_id: str


# ── Endpointy ─────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "openai_configured": bool(OPENAI_API_KEY),
        "youtube_api_configured": bool(os.getenv("YOUTUBE_API_KEY")),
        "version": "3",
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    url = req.url.strip()
    if not YT_URL_RE.search(url):
        raise HTTPException(status_code=422, detail="Podaj poprawny link YouTube.")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Brak klucza OPENAI_API_KEY na serwerze.")

    analysis = create_analysis(url)
    background_tasks.add_task(run_pipeline, analysis.id, OPENAI_API_KEY)
    return AnalyzeResponse(session_id=analysis.id)


@app.get("/stream/{session_id}")
async def stream(session_id: str):
    """SSE stream — wysyła aktualizacje statusu co 1s aż do done/error."""
    analysis = get_analysis(session_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Sesja nie istnieje.")

    async def event_generator() -> AsyncGenerator[str, None]:
        last_msg = ""
        timeout = 300  # max 5 minut
        elapsed = 0

        while elapsed < timeout:
            a = get_analysis(session_id)
            if not a:
                break

            current_msg = f"{a.status.value}:{a.progress_msg}"
            if current_msg != last_msg:
                payload = json.dumps({
                    "status": a.status.value,
                    "message": a.progress_msg,
                }, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                last_msg = current_msg

            if a.status in (AnalysisStatus.done, AnalysisStatus.error):
                yield "data: {\"status\": \"stream_end\"}\n\n"
                break

            await asyncio.sleep(1)
            elapsed += 1

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/results/{session_id}")
async def results(session_id: str):
    analysis = get_analysis(session_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Sesja nie istnieje.")

    return {
        "session_id": analysis.id,
        "status": analysis.status.value,
        "video_id": analysis.video_id,
        "video_title": analysis.video_title,
        "url": analysis.url,
        "error_msg": analysis.error_msg,
        "proposals": [
            {
                "title": p.title,
                "start_s": p.start_s,
                "end_s": p.end_s,
                "duration_s": p.duration_s,
                "reason": p.reason,
            }
            for p in analysis.proposals
        ],
    }


@app.get("/history")
async def history():
    analyses = list_analyses(limit=20)
    return [
        {
            "session_id": a.id,
            "video_title": a.video_title or a.url,
            "video_id": a.video_id,
            "status": a.status.value,
            "proposals_count": len(a.proposals),
            "created_at": a.created_at,
        }
        for a in analyses
    ]
