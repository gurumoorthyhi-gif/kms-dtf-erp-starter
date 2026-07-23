"""AI image engine request, response, and job records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AITool(StrEnum):
    REMOVE_BACKGROUND = "remove_background"
    REMOVE_COLOUR = "remove_colour"
    REMOVE_BACKGROUND_PROTECTED = "remove_background_protected"
    REMOVE_CONTIGUOUS_COLOUR = "remove_contiguous_colour"
    UPSCALE = "upscale"
    ENHANCE = "enhance"
    GENERATE = "generate"
    EDIT = "edit"
    ANALYSE = "analyse"


class AIJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AIJobRequest:
    artwork_id: int
    tool: AITool
    source_path: Path
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineJobResponse:
    job_id: str
    status: AIJobStatus
    progress: int = 0
    message: str = ""


@dataclass(frozen=True, slots=True)
class AIJobSnapshot:
    id: str
    engine_job_id: str
    request: AIJobRequest
    status: AIJobStatus
    progress: int
    message: str
    attempts: int
    result_preview_path: Path | None = None
