"""Persist processed AI results as new managed artwork versions."""

from pathlib import Path

from app.modules.artwork import ArtworkService


class AIResultHandler:
    def __init__(self, artwork_service: ArtworkService) -> None:
        self.artwork_service = artwork_service

    def save(self, artwork_id: int, result_path: Path, tool_name: str) -> Path:
        details = self.artwork_service.add_version(
            artwork_id,
            result_path,
            f"Processed by AI tool: {tool_name}",
        )
        return self.artwork_service.preview_file(details.summary.latest_version.preview_path)
