"""Asynchronous AI image tools backed by the separate engine service."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.modules.ai_engine import (
    AIJobManager,
    AIJobRequest,
    AIJobSnapshot,
    AIJobStatus,
    AITool,
)
from app.modules.artwork import ArtworkService
from app.ui.pages.artwork_studio import BeforeAfterView

TOOL_LABELS = {
    AITool.REMOVE_BACKGROUND: "Background removal",
    AITool.REMOVE_COLOUR: "Remove selected colour everywhere",
    AITool.REMOVE_BACKGROUND_PROTECTED: "Background removal (protect subject)",
    AITool.REMOVE_CONTIGUOUS_COLOUR: "Contiguous colour removal",
    AITool.UPSCALE: "Image upscaling",
    AITool.ENHANCE: "Image enhancement",
    AITool.GENERATE: "Image generation",
    AITool.EDIT: "Image editing",
    AITool.ANALYSE: "Artwork analysis",
}


class AIJobBridge(QObject):
    updated = Signal(object)


class AIToolsPage(QWidget):
    def __init__(
        self,
        job_manager: AIJobManager,
        artwork_service: ArtworkService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.job_manager = job_manager
        self.artwork_service = artwork_service
        self.current_job_id: str | None = None
        self.bridge = AIJobBridge()
        self.bridge.updated.connect(self._job_updated)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.artwork = QComboBox()
        self.tool = QComboBox()
        for tool, label in TOOL_LABELS.items():
            self.tool.addItem(label, tool)
        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Prompt or processing instructions")
        self.colour = QLineEdit("#FFFFFF")
        self.scale = QComboBox()
        self.scale.addItems(("2", "4"))
        form.addRow("Artwork", self.artwork)
        form.addRow("AI tool", self.tool)
        form.addRow("Prompt", self.prompt)
        form.addRow("Selected colour", self.colour)
        form.addRow("Upscale factor", self.scale)
        layout.addLayout(form)
        actions = QHBoxLayout()
        self.submit_button = QPushButton("Submit AI job")
        self.cancel_button = QPushButton("Cancel")
        self.retry_button = QPushButton("Retry failed job")
        self.cancel_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        actions.addWidget(self.submit_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.retry_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.comparison = BeforeAfterView()
        layout.addWidget(self.comparison, 1)
        self.submit_button.clicked.connect(self.submit)
        self.cancel_button.clicked.connect(self.cancel)
        self.retry_button.clicked.connect(self.retry)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        selected = self.artwork.currentData()
        self.artwork.clear()
        for item in self.artwork_service.list_artwork():
            self.artwork.addItem(f"{item.title} · v{item.version_count}", item.id)
        index = self.artwork.findData(selected)
        if index >= 0:
            self.artwork.setCurrentIndex(index)

    def submit(self) -> None:
        artwork_id = self.artwork.currentData()
        tool = self.tool.currentData()
        if artwork_id is None or not isinstance(tool, AITool):
            self.status.setText("Select artwork and an AI tool.")
            return
        details = self.artwork_service.get_artwork(int(artwork_id))
        latest = details.summary.latest_version
        source = self.artwork_service.original_file(latest.original_path)
        before = self.artwork_service.preview_file(latest.preview_path)
        self.comparison.before.set_image(before)
        self.comparison.after.set_image(before)
        parameters = {
            "prompt": self.prompt.text().strip(),
            "colour": self.colour.text().strip(),
            "scale": int(self.scale.currentText()),
        }
        request = AIJobRequest(int(artwork_id), tool, source, parameters)
        self.current_job_id = self.job_manager.submit(request, self.bridge.updated.emit)
        self.submit_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.retry_button.setEnabled(False)

    def cancel(self) -> None:
        if self.current_job_id is not None:
            self.job_manager.cancel(self.current_job_id)

    def retry(self) -> None:
        if self.current_job_id is None:
            return
        self.current_job_id = self.job_manager.retry(
            self.current_job_id,
            self.bridge.updated.emit,
        )
        self.submit_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.retry_button.setEnabled(False)

    @Slot(object)
    def _job_updated(self, snapshot: AIJobSnapshot) -> None:
        if self.current_job_id is not None and snapshot.id != self.current_job_id:
            return
        self.current_job_id = snapshot.id
        self.progress.setValue(snapshot.progress)
        self.status.setText(snapshot.message or snapshot.status.value.title())
        active = snapshot.status in {AIJobStatus.QUEUED, AIJobStatus.RUNNING}
        self.cancel_button.setEnabled(active)
        if snapshot.status == AIJobStatus.COMPLETED:
            self.submit_button.setEnabled(True)
            self.retry_button.setEnabled(False)
            if snapshot.result_preview_path is not None:
                self.comparison.after.set_image(snapshot.result_preview_path)
            self.refresh()
        elif snapshot.status in {AIJobStatus.FAILED, AIJobStatus.CANCELLED}:
            self.submit_button.setEnabled(True)
            self.retry_button.setEnabled(True)
