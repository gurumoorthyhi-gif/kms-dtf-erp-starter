"""Responsive Artwork Studio with zoom, pan, and local transformations."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.modules.artwork import ArtworkService
from app.modules.artwork_studio import ArtworkStudioService, EditSpec, StudioDocument


class ImageCanvas(QGraphicsView):
    """Pixmap canvas with wheel zoom and hand-drag panning."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._item = QGraphicsPixmapItem()
        self._scene.addItem(self._item)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMinimumSize(320, 300)

    def set_image(self, path: Path) -> None:
        self.resetTransform()
        self._item.setPixmap(QPixmap(str(path)))
        self._scene.setSceneRect(self._item.boundingRect())
        self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)


class BeforeAfterView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        before_box = QGroupBox("Before")
        before_layout = QVBoxLayout(before_box)
        self.before = ImageCanvas()
        before_layout.addWidget(self.before)
        after_box = QGroupBox("After")
        after_layout = QVBoxLayout(after_box)
        self.after = ImageCanvas()
        after_layout.addWidget(self.after)
        layout.addWidget(before_box, 1)
        layout.addWidget(after_box, 1)


class StudioWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class StudioWorker(QRunnable):
    def __init__(
        self,
        service: ArtworkStudioService,
        document: StudioDocument,
        destination: Path,
        spec: EditSpec,
    ) -> None:
        super().__init__()
        self.service = service
        self.document = document
        self.destination = destination
        self.spec = spec
        self.signals = StudioWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.service.edit_and_save(
                self.document.artwork_id,
                self.destination,
                self.spec,
                "Edited in Artwork Studio",
            )
            updated = self.service.open_artwork(self.document.artwork_id)
        except Exception as error:
            self.signals.failed.emit(str(error))
            return
        self.signals.finished.emit(updated)


class ArtworkStudioPage(QWidget):
    def __init__(
        self,
        studio_service: ArtworkStudioService,
        artwork_service: ArtworkService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.studio_service = studio_service
        self.artwork_service = artwork_service
        self.document: StudioDocument | None = None
        self.thread_pool = QThreadPool.globalInstance()
        self.temporary = tempfile.TemporaryDirectory(prefix="kms-artwork-studio-")
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.artwork = QComboBox()
        open_button = QPushButton("Open artwork")
        self.apply_button = QPushButton("Apply and save new version")
        self.apply_button.setEnabled(False)
        toolbar.addWidget(self.artwork, 1)
        toolbar.addWidget(open_button)
        toolbar.addWidget(self.apply_button)
        layout.addLayout(toolbar)

        workspace = QHBoxLayout()
        controls = QGroupBox("Local image tools")
        form = QFormLayout(controls)
        self.crop_left = self._spin()
        self.crop_top = self._spin()
        self.crop_right = self._spin()
        self.crop_bottom = self._spin()
        self.resize_width = self._spin()
        self.resize_height = self._spin()
        self.rotation = QComboBox()
        self.rotation.addItems(("0°", "90°", "180°", "270°"))
        self.flip_horizontal = QCheckBox("Horizontal")
        self.flip_vertical = QCheckBox("Vertical")
        form.addRow("Crop left", self.crop_left)
        form.addRow("Crop top", self.crop_top)
        form.addRow("Crop right", self.crop_right)
        form.addRow("Crop bottom", self.crop_bottom)
        form.addRow("Resize width", self.resize_width)
        form.addRow("Resize height", self.resize_height)
        form.addRow("Rotate", self.rotation)
        form.addRow("Flip", self.flip_horizontal)
        form.addRow("", self.flip_vertical)
        self.metadata = QLabel("Open an artwork to inspect it.")
        self.metadata.setWordWrap(True)
        form.addRow("Checks", self.metadata)
        workspace.addWidget(controls)
        self.comparison = BeforeAfterView()
        workspace.addWidget(self.comparison, 1)
        layout.addLayout(workspace, 1)
        self.status = QLabel("Ready")
        layout.addWidget(self.status)

        open_button.clicked.connect(self.open_selected)
        self.apply_button.clicked.connect(self.apply_edit)
        if auto_refresh:
            self.refresh()

    @staticmethod
    def _spin() -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 100_000)
        return spin

    def refresh(self) -> None:
        selected = self.artwork.currentData()
        self.artwork.clear()
        for item in self.artwork_service.list_artwork():
            self.artwork.addItem(f"{item.title} · v{item.version_count}", item.id)
        index = self.artwork.findData(selected)
        if index >= 0:
            self.artwork.setCurrentIndex(index)

    def open_selected(self) -> None:
        artwork_id = self.artwork.currentData()
        if artwork_id is None:
            return
        try:
            self.document = self.studio_service.open_artwork(int(artwork_id))
        except (LookupError, OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot open artwork", str(error))
            return
        document = self.document
        self.comparison.before.set_image(document.preview_path)
        self.comparison.after.set_image(document.preview_path)
        width, height = document.inspection.width, document.inspection.height
        for spin, maximum, value in (
            (self.crop_left, width, 0),
            (self.crop_top, height, 0),
            (self.crop_right, width, width),
            (self.crop_bottom, height, height),
            (self.resize_width, 100_000, 0),
            (self.resize_height, 100_000, 0),
        ):
            spin.setMaximum(maximum)
            spin.setValue(value)
        inspection = document.inspection
        self.metadata.setText(
            f"{inspection.width} × {inspection.height} px\n"
            f"{inspection.dpi_x} × {inspection.dpi_y} DPI\n"
            f"Transparency: {'Yes' if inspection.has_transparency else 'No'}\n"
            f"Colour profile: {inspection.colour_profile}\n"
            f"300 DPI ready: {'Yes' if inspection.print_ready_300_dpi else 'No'}"
        )
        self.status.setText(f"Opened {document.title} version {document.version_number}")
        self.apply_button.setEnabled(True)

    def apply_edit(self) -> None:
        if self.document is None:
            return
        resize = None
        if self.resize_width.value() or self.resize_height.value():
            if not self.resize_width.value() or not self.resize_height.value():
                QMessageBox.warning(self, "Invalid resize", "Enter both width and height.")
                return
            resize = (self.resize_width.value(), self.resize_height.value())
        spec = EditSpec(
            crop=(
                self.crop_left.value(),
                self.crop_top.value(),
                self.crop_right.value(),
                self.crop_bottom.value(),
            ),
            resize=resize,
            rotation_degrees=self.rotation.currentIndex() * 90,
            flip_horizontal=self.flip_horizontal.isChecked(),
            flip_vertical=self.flip_vertical.isChecked(),
        )
        destination = Path(self.temporary.name) / f"{uuid4().hex}.png"
        worker = StudioWorker(self.studio_service, self.document, destination, spec)
        worker.signals.finished.connect(self._edit_finished)
        worker.signals.failed.connect(self._edit_failed)
        self.apply_button.setEnabled(False)
        self.status.setText("Processing in background…")
        self.thread_pool.start(worker)

    @Slot(object)
    def _edit_finished(self, document: StudioDocument) -> None:
        self.document = document
        self.comparison.after.set_image(document.preview_path)
        self.status.setText(f"Saved as version {document.version_number}")
        self.apply_button.setEnabled(True)
        self.refresh()

    @Slot(str)
    def _edit_failed(self, message: str) -> None:
        self.status.setText("Edit failed")
        self.apply_button.setEnabled(True)
        QMessageBox.warning(self, "Artwork edit failed", message)
