"""Gang sheet builder with preview interaction and layout history."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.modules.artwork import ArtworkService
from app.modules.gang_sheets import GangSheetDetails, GangSheetInput, GangSheetService, Placement

PIXELS_PER_MM = 2


class LayoutHistory:
    def __init__(self) -> None:
        self.undo_stack: list[tuple[tuple[Placement, ...], tuple[Placement, ...]]] = []
        self.redo_stack: list[tuple[tuple[Placement, ...], tuple[Placement, ...]]] = []

    def record(self, before: tuple[Placement, ...], after: tuple[Placement, ...]) -> None:
        if before != after:
            self.undo_stack.append((before, after))
            self.redo_stack.clear()

    def undo(self) -> tuple[Placement, ...] | None:
        if not self.undo_stack:
            return None
        change = self.undo_stack.pop()
        self.redo_stack.append(change)
        return change[0]

    def redo(self) -> tuple[Placement, ...] | None:
        if not self.redo_stack:
            return None
        change = self.redo_stack.pop()
        self.undo_stack.append(change)
        return change[1]


class PlacementItem(QGraphicsPixmapItem):
    def __init__(
        self,
        placement: Placement,
        pixmap: QPixmap,
        moved: Callable[[int, Decimal, Decimal], None],
    ) -> None:
        super().__init__(pixmap)
        self.placement_id = placement.id
        self._moved = moved
        self.setFlags(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setPos(float(placement.x_mm) * PIXELS_PER_MM, float(placement.y_mm) * PIXELS_PER_MM)
        self.setRotation(placement.rotation_degrees)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._moved(
            self.placement_id,
            Decimal(str(self.x() / PIXELS_PER_MM)).quantize(Decimal("0.01")),
            Decimal(str(self.y() / PIXELS_PER_MM)).quantize(Decimal("0.01")),
        )


class GangSheetCanvas(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas_scene = QGraphicsScene(self)
        self.setScene(self.canvas_scene)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setMinimumSize(500, 500)

    def render_sheet(
        self,
        details: GangSheetDetails,
        service: GangSheetService,
        moved: Callable[[int, Decimal, Decimal], None],
    ) -> None:
        self.canvas_scene.clear()
        width = float(details.width_mm) * PIXELS_PER_MM
        height = float(details.length_mm) * PIXELS_PER_MM
        self.canvas_scene.setSceneRect(0, 0, width, height)
        self.canvas_scene.setBackgroundBrush(QBrush(QColor("white")))
        for placement in details.items:
            pixmap = QPixmap(str(service.preview_file(placement.preview_path)))
            pixmap = pixmap.scaled(
                max(1, round(float(placement.width_mm) * PIXELS_PER_MM)),
                max(1, round(float(placement.height_mm) * PIXELS_PER_MM)),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.canvas_scene.addItem(PlacementItem(placement, pixmap, moved))
        self.fitInView(self.canvas_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def selected_ids(self) -> tuple[int, ...]:
        return tuple(
            item.placement_id
            for item in self.canvas_scene.selectedItems()
            if isinstance(item, PlacementItem)
        )


class GangSheetPage(QWidget):
    def __init__(
        self,
        service: GangSheetService,
        artwork_service: ArtworkService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.artwork_service = artwork_service
        self.details: GangSheetDetails | None = None
        self.history = LayoutHistory()
        root = QHBoxLayout(self)
        controls = QVBoxLayout()
        form = QFormLayout()
        self.sheets = QComboBox()
        self.name = QLineEdit("New gang sheet")
        self.sheet_width = self._measurement(600)
        self.sheet_length = self._measurement(1000)
        self.margin = self._measurement(5)
        self.spacing = self._measurement(3)
        form.addRow("Saved sheet", self.sheets)
        form.addRow("Name", self.name)
        form.addRow("Width mm", self.sheet_width)
        form.addRow("Length mm", self.sheet_length)
        form.addRow("Margin mm", self.margin)
        form.addRow("Spacing mm", self.spacing)
        controls.addLayout(form)
        create = QPushButton("Create sheet")
        apply_size = QPushButton("Apply canvas size")
        controls.addWidget(create)
        controls.addWidget(apply_size)
        self.artwork = QComboBox()
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 1000)
        add = QPushButton("Place artwork")
        controls.addWidget(self.artwork)
        controls.addWidget(self.quantity)
        controls.addWidget(add)
        self.item_width = self._measurement(100)
        self.item_height = self._measurement(100)
        resize_item = QPushButton("Resize selected")
        controls.addWidget(self.item_width)
        controls.addWidget(self.item_height)
        controls.addWidget(resize_item)
        for label, handler in (
            ("Duplicate selected", self.duplicate),
            ("Delete selected", self.delete),
            ("Rotate selected 90°", self.rotate),
            ("Align left", lambda: self.align("left")),
            ("Align top", lambda: self.align("top")),
            ("Distribute horizontally", self.distribute),
            ("Automatic nesting", self.auto_nest),
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Export 300 DPI", self.export),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            controls.addWidget(button)
        self.usage = QLabel("Metre usage: 0.000 m")
        controls.addWidget(self.usage)
        controls.addStretch()
        root.addLayout(controls)
        self.canvas = GangSheetCanvas()
        root.addWidget(self.canvas, 1)
        create.clicked.connect(self.create_sheet)
        apply_size.clicked.connect(self.apply_size)
        add.clicked.connect(self.add_artwork)
        resize_item.clicked.connect(self.resize_selected)
        self.sheets.currentIndexChanged.connect(self.open_selected)
        if auto_refresh:
            self.refresh()

    @staticmethod
    def _measurement(value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 100_000)
        spin.setDecimals(2)
        spin.setValue(value)
        return spin

    def refresh(self) -> None:
        selected = self.sheets.currentData()
        self.sheets.blockSignals(True)
        self.sheets.clear()
        for sheet in self.service.list():
            self.sheets.addItem(sheet.name, sheet.id)
        self.sheets.blockSignals(False)
        index = self.sheets.findData(selected)
        if index >= 0:
            self.sheets.setCurrentIndex(index)
        self.artwork.clear()
        for artwork in self.artwork_service.list_artwork():
            self.artwork.addItem(artwork.title, artwork.id)

    def create_sheet(self) -> None:
        self.details = self.service.create(
            GangSheetInput(
                self.name.text(),
                Decimal(str(self.sheet_width.value())),
                Decimal(str(self.sheet_length.value())),
                Decimal(str(self.margin.value())),
                Decimal(str(self.spacing.value())),
            )
        )
        self.history = LayoutHistory()
        self.refresh()
        created = self.details
        self.sheets.setCurrentIndex(self.sheets.findData(created.id))
        self._render()

    def open_selected(self) -> None:
        sheet_id = self.sheets.currentData()
        if sheet_id is None:
            return
        self.details = self.service.get(int(sheet_id))
        self.history = LayoutHistory()
        self._load_controls()
        self._render()

    def apply_size(self) -> None:
        if self.details is None:
            return
        self.details = self.service.resize_sheet(
            self.details.id,
            width_mm=Decimal(str(self.sheet_width.value())),
            length_mm=Decimal(str(self.sheet_length.value())),
            margin_mm=Decimal(str(self.margin.value())),
            spacing_mm=Decimal(str(self.spacing.value())),
        )
        self._render()

    def add_artwork(self) -> None:
        if self.details is None or self.artwork.currentData() is None:
            return
        sheet_id = self.details.id
        artwork_id = int(self.artwork.currentData())
        self._mutate(
            lambda: self.service.add_artwork(
                sheet_id,
                artwork_id,
                quantity=self.quantity.value(),
            )
        )

    def duplicate(self) -> None:
        selected = self.canvas.selected_ids()
        if selected:
            self._mutate(lambda: self.service.duplicate(selected[0], self.quantity.value()))

    def delete(self) -> None:
        selected = self.canvas.selected_ids()
        if selected:
            self._mutate(lambda: self.service.delete_item(selected[0]))

    def rotate(self) -> None:
        selected = self.canvas.selected_ids()
        if not selected or self.details is None:
            return
        item = next(item for item in self.details.items if item.id == selected[0])
        self._mutate(
            lambda: self.service.update_item(
                item.id,
                rotation_degrees=(item.rotation_degrees + 90) % 360,
            )
        )

    def resize_selected(self) -> None:
        selected = self.canvas.selected_ids()
        if selected:
            self._mutate(
                lambda: self.service.update_item(
                    selected[0],
                    width_mm=Decimal(str(self.item_width.value())),
                    height_mm=Decimal(str(self.item_height.value())),
                )
            )

    def align(self, edge: str) -> None:
        if self.details is not None:
            sheet_id = self.details.id
            self._mutate(lambda: self.service.align(sheet_id, self.canvas.selected_ids(), edge))

    def distribute(self) -> None:
        if self.details is not None:
            sheet_id = self.details.id
            self._mutate(lambda: self.service.distribute(sheet_id, self.canvas.selected_ids()))

    def auto_nest(self) -> None:
        if self.details is not None:
            sheet_id = self.details.id
            self._mutate(lambda: self.service.auto_nest(sheet_id))

    def undo(self) -> None:
        if self.details is None:
            return
        placements = self.history.undo()
        if placements is not None:
            self.details = self.service.restore_layout(self.details.id, placements)
            self._render()

    def redo(self) -> None:
        if self.details is None:
            return
        placements = self.history.redo()
        if placements is not None:
            self.details = self.service.restore_layout(self.details.id, placements)
            self._render()

    def export(self) -> None:
        if self.details is None:
            return
        try:
            output = self.service.export(self.details.id)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Export failed", str(error))
            return
        selected, _ = QFileDialog.getSaveFileName(
            self, "Save gang sheet", str(output), "PNG image (*.png)"
        )
        if selected and selected != str(output):
            output.replace(selected)
        QMessageBox.information(self, "Export complete", f"Saved to {selected or output}")

    def _moved(self, item_id: int, x_mm: Decimal, y_mm: Decimal) -> None:
        self._mutate(lambda: self.service.update_item(item_id, x_mm=x_mm, y_mm=y_mm))

    def _mutate(self, action: Callable[[], GangSheetDetails]) -> None:
        if self.details is None:
            return
        before = self.details.items
        try:
            self.details = action()
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Layout change failed", str(error))
            return
        self.history.record(before, self.details.items)
        self._render()

    def _load_controls(self) -> None:
        if self.details is None:
            return
        self.name.setText(self.details.name)
        self.sheet_width.setValue(float(self.details.width_mm))
        self.sheet_length.setValue(float(self.details.length_mm))
        self.margin.setValue(float(self.details.margin_mm))
        self.spacing.setValue(float(self.details.spacing_mm))

    def _render(self) -> None:
        if self.details is None:
            return
        self.canvas.render_sheet(self.details, self.service, self._moved)
        self.usage.setText(f"Metre usage: {self.details.metre_usage} m")
