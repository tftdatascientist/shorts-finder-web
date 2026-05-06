from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time
import uuid


class AnalysisStatus(str, Enum):
    pending = "pending"
    fetching_meta = "fetching_meta"
    transcribing = "transcribing"
    analyzing = "analyzing"
    done = "done"
    error = "error"


@dataclass
class Proposal:
    title: str
    start_s: float
    end_s: float
    duration_s: float
    reason: str


@dataclass
class Analysis:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    video_id: str = ""
    video_title: str = ""
    status: AnalysisStatus = AnalysisStatus.pending
    progress_msg: str = ""
    proposals: List[Proposal] = field(default_factory=list)
    error_msg: str = ""
    created_at: float = field(default_factory=time.time)


# Prosty in-memory store — wystarczy dla 2-3 użytkowników
_store: dict[str, Analysis] = {}


def create_analysis(url: str) -> Analysis:
    a = Analysis(url=url)
    _store[a.id] = a
    return a


def get_analysis(session_id: str) -> Optional[Analysis]:
    return _store.get(session_id)


def list_analyses(limit: int = 20) -> List[Analysis]:
    sorted_items = sorted(_store.values(), key=lambda a: a.created_at, reverse=True)
    return sorted_items[:limit]
