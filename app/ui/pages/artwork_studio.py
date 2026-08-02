"""Artwork Studio: production gangsheet workspace for DTF artwork."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from tempfile import gettempdir

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.modules.artwork import ArtworkInput, ArtworkService
from app.modules.customers import CustomerService
from app.modules.gang_sheets import GangSheetDetails, GangSheetInput, GangSheetService
from app.ui.pages.gang_sheets import GangSheetCanvas, LayoutHistory
from app.ui.pages.image_editor import CustomerImageDialog

HIDDEN_SIDE_ALLOWANCE_MM = Decimal("10")
DEFAULT_VISIBLE_WIDTH_MM = Decimal("576.58")
DEFAULT_LENGTH_MM = Decimal("1000")
DEFAULT_OBJECT_MM = Decimal("100")
UNIT_TO_MM = {
    "cm": Decimal("10"),
    "mm": Decimal("1"),
    "inches": Decimal("25.4"),
}


class ArtworkStudioPage(QWidget):
    """Three-column DTF layout editor backed by the gangsheet service."""

    def __init__(
        self,
        service: GangSheetService,
        artwork_service: ArtworkService,
        customer_service: CustomerService | None = None,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.artwork_service = artwork_service
        self.customer_service = customer_service
        self.details: GangSheetDetails | None = None
        self.history = LayoutHistory()
        self._clipboard = None
        self._unit = "inches"
        self._build_ui()
        self._connect_signals()
        if auto_refresh:
            self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(9)
        root.addLayout(self._build_header())

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setChildrenCollapsible(False)
        workspace.addWidget(self._build_left_panel())
        self.canvas = GangSheetCanvas()
        self.canvas.setObjectName("artworkStudioCanvas")
        self.canvas.set_sheet_size(
            DEFAULT_VISIBLE_WIDTH_MM + HIDDEN_SIDE_ALLOWANCE_MM,
            DEFAULT_LENGTH_MM,
        )
        workspace.addWidget(self.canvas)
        workspace.addWidget(self._build_right_panel())
        workspace.setSizes((270, 760, 235))
        workspace.setStretchFactor(0, 0)
        workspace.setStretchFactor(1, 1)
        workspace.setStretchFactor(2, 0)
        root.addWidget(workspace, 1)
        root.addLayout(self._build_footer())

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(7)
        title = QLabel("Production Studio")
        title.setObjectName("studioTitle")
        header.addWidget(title)

        self.view_mode = QComboBox()
        self.view_mode.addItems(("Wireframe", "Normal", "Enhanced"))
        self.view_mode.setCurrentText("Normal")
        self.units = QComboBox()
        self.units.addItems(("cm", "mm", "inches"))
        self.units.setCurrentText("inches")
        self.sheets = QComboBox()
        load = QPushButton("Load")
        load.setObjectName("studioSecondaryButton")
        self.load_button = load
        self.name = QLineEdit("Untitled gangsheet")
        self.name.setMinimumWidth(170)
        self.sheet_width = self._measurement(self._from_mm(DEFAULT_VISIBLE_WIDTH_MM))
        self.sheet_length = self._measurement(self._from_mm(DEFAULT_LENGTH_MM))
        self.sheet_width.setRange(self._from_mm(Decimal("100")), self._from_mm(Decimal("3000")))
        self.sheet_length.setRange(self._from_mm(Decimal("4")), self._from_mm(Decimal("5000")))
        self.set_length_button = QPushButton("Set length")
        self.set_length_button.setObjectName("studioPrimaryButton")

        for label, widget in (
            ("View", self.view_mode),
            ("Unit", self.units),
            ("Saved layout", self.sheets),
        ):
            header.addWidget(QLabel(label))
            header.addWidget(widget)
        header.addWidget(load)
        header.addWidget(self.name, 1)
        header.addWidget(QLabel("Width"))
        header.addWidget(self.sheet_width)
        header.addWidget(QLabel("Length"))
        header.addWidget(self.sheet_length)
        header.addWidget(self.set_length_button)
        return header

    def _build_left_panel(self) -> QWidget:
        panel = QGroupBox("DESIGN TOOLS")
        panel.setObjectName("studioPanel")
        panel.setMinimumWidth(245)
        layout = QVBoxLayout(panel)

        size_box = QGroupBox("Selected design dimensions")
        size_form = QFormLayout(size_box)
        self.item_width = self._measurement(self._from_mm(DEFAULT_OBJECT_MM))
        self.item_height = self._measurement(self._from_mm(DEFAULT_OBJECT_MM))
        self.item_width.setRange(self._from_mm(Decimal("2")), self._from_mm(Decimal("10000")))
        self.item_height.setRange(self._from_mm(Decimal("2")), self._from_mm(Decimal("10000")))
        self.lock_proportions = QCheckBox("Lock proportions")
        self.lock_proportions.setChecked(True)
        self.lock_proportions.setVisible(False)
        self.apply_size_button = QPushButton("Apply size")
        self.apply_size_button.setObjectName("studioSecondaryButton")
        self.apply_size_button.setVisible(False)
        self.object_units = QComboBox()
        self.object_units.addItems(("cm", "mm", "inches"))
        self.object_units.setCurrentText(self._unit)
        self.rotation_value = QDoubleSpinBox()
        self.rotation_value.setRange(-360, 360)
        self.rotation_value.setDecimals(1)
        self.rotation_value.setSuffix("°")
        for control in (self.item_width, self.item_height, self.rotation_value):
            control.setEnabled(False)
        size_form.addRow("Width", self.item_width)
        size_form.addRow("Height", self.item_height)
        size_form.addRow("Units", self.object_units)
        size_form.addRow("Rotation", self.rotation_value)
        layout.addWidget(size_box)

        designs_box = QGroupBox("Designs / import")
        designs_layout = QVBoxLayout(designs_box)
        self.designs = QListWidget()
        self.designs.setObjectName("studioDesignList")
        self.designs.setDragEnabled(True)
        self.designs.setIconSize(self.designs.iconSize().expandedTo(self.designs.iconSize()))
        self.add_designs_button = QPushButton("Add designs")
        self.add_designs_button.setObjectName("studioPrimaryButton")
        self.add_designs_button.setEnabled(self.customer_service is not None)
        self.add_designs_button.setToolTip("Select designs from a customer folder")
        self.add_design_button = QPushButton("Add selected design")
        self.add_design_button.setObjectName("studioPrimaryButton")
        designs_layout.addWidget(self.add_designs_button)
        designs_layout.addWidget(self.designs)
        designs_layout.addWidget(self.add_design_button)
        layout.addWidget(designs_box, 1)
        layout.insertWidget(0, self.add_designs_button)
        designs_box.setVisible(False)

        tools = QGroupBox("Upscale / background / trim")
        tools_layout = QVBoxLayout(tools)
        self.remove_background = QCheckBox("Local background removal")
        self.auto_trim = QCheckBox("Auto trim")
        self.sharpen = QCheckBox("Sharpen")
        self.upscale = QComboBox()
        self.upscale.addItems(("Original", "2× upscale", "4× upscale"))
        self.apply_tools_button = QPushButton("Apply image tools")
        self.apply_tools_button.setEnabled(False)
        self.apply_tools_button.setToolTip(
            "Image-processing service will be connected in a later Artwork Studio phase"
        )
        for widget in (
            self.remove_background,
            self.auto_trim,
            self.sharpen,
            self.upscale,
            self.apply_tools_button,
        ):
            tools_layout.addWidget(widget)
        layout.addWidget(tools)
        tools.setVisible(False)
        for title in ("Text", "Colour", "Stroke", "Shapes"):
            placeholder = QGroupBox(title)
            placeholder_layout = QVBoxLayout(placeholder)
            placeholder_layout.addWidget(QLabel("Coming soon"))
            layout.addWidget(placeholder)
            placeholder.setVisible(False)
        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QGroupBox("LAYOUT / EXPORT")
        panel.setObjectName("studioPanel")
        panel.setMinimumWidth(215)
        layout = QVBoxLayout(panel)
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 10_000)
        self.quantity.setValue(1)
        layout.addWidget(QLabel("Quantity"))
        layout.addWidget(self.quantity)

        self.apply_copies_button = QPushButton("Apply copies")
        self.export_button = QPushButton("Export gangsheet")
        self.auto_arrange_button = QPushButton("Auto arrange copies")
        self.adjust_page_button = QPushButton("Adjust page to designs")
        for button in (
            self.apply_copies_button,
            self.export_button,
            self.auto_arrange_button,
            self.adjust_page_button,
        ):
            button.setObjectName("studioPrimaryButton")
            layout.addWidget(button)

        layout.addSpacing(8)
        layout.addWidget(QLabel("Preview canvas"))
        colours = QHBoxLayout()
        for colour in ("#00d9ff", "#e6007e", "#111111", "#ffffff", "#39ff14"):
            button = QPushButton()
            button.setFixedSize(27, 27)
            button.setToolTip(colour)
            button.setStyleSheet(
                f"background-color: {colour}; border: 1px solid rgba(255,255,255,90);"
                "border-radius: 13px;"
            )
            button.clicked.connect(
                lambda checked=False, value=colour: self.canvas.set_preview_colour(value)
            )
            colours.addWidget(button)
        layout.addLayout(colours)

        layout.addSpacing(8)
        self.usage = QLabel("DTF metres: 0.000 m")
        self.usage.setObjectName("studioMetric")
        self.selection_status = QLabel("Selected: 0 objects")
        self.selection_status.setWordWrap(True)
        layout.addWidget(self.usage)
        layout.addWidget(self.selection_status)

        layout.addStretch()
        for label, callback in (
            ("Delete selected", self.delete_selected),
            ("Rotate selected 90°", self.rotate_selected),
            ("Align left", lambda: self.align("left")),
            ("Align top", lambda: self.align("top")),
        ):
            button = QPushButton(label)
            button.setObjectName("studioSecondaryButton")
            button.clicked.connect(callback)
            layout.addWidget(button)
        return panel

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        self.save_button = QPushButton("Save layout")
        self.save_button.setObjectName("studioPrimaryButton")
        footer.addWidget(self.undo_button)
        footer.addWidget(self.redo_button)
        footer.addStretch()
        footer.addWidget(self.save_button)
        return footer

    def _connect_signals(self) -> None:
        self.load_button.clicked.connect(self.open_selected)
        self.set_length_button.clicked.connect(self.save_layout)
        self.save_button.clicked.connect(self.save_layout)
        self.add_design_button.clicked.connect(self.add_selected_design)
        self.add_designs_button.clicked.connect(self.add_designs_from_customer_folder)
        self.designs.itemDoubleClicked.connect(lambda _item: self.add_selected_design())
        self.apply_size_button.clicked.connect(self.resize_selected)
        self.apply_copies_button.clicked.connect(self.apply_copies)
        self.export_button.clicked.connect(self.export)
        self.auto_arrange_button.clicked.connect(self.auto_arrange)
        self.adjust_page_button.clicked.connect(self.adjust_page_to_designs)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.units.currentTextChanged.connect(self._unit_changed)
        self.view_mode.currentTextChanged.connect(self._view_mode_changed)
        self.canvas.canvas_scene.selectionChanged.connect(self._selection_changed)
        self.item_width.editingFinished.connect(self.resize_selected)
        self.item_height.editingFinished.connect(self.resize_selected)
        self.object_units.currentTextChanged.connect(self.units.setCurrentText)
        self.rotation_value.editingFinished.connect(self.apply_rotation_value)
        self.sheet_width.editingFinished.connect(self._preview_sheet_size)
        self.sheet_length.editingFinished.connect(self._preview_sheet_size)
        self._shortcuts = []
        for key, callback in (
            (QKeySequence.StandardKey.Copy, self.copy_selected),
            (QKeySequence.StandardKey.Cut, self.cut_selected),
            (QKeySequence.StandardKey.Paste, self.paste_selected),
            (QKeySequence(Qt.Key.Key_Delete), self.delete_selected),
            (QKeySequence(Qt.Key.Key_Backspace), self.delete_selected),
            (QKeySequence.StandardKey.Undo, self.undo),
            (QKeySequence.StandardKey.Redo, self.redo),
            (QKeySequence("Ctrl+Shift+Z"), self.redo),
        ):
            shortcut = QShortcut(key, self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    @staticmethod
    def _measurement(value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.01, 100_000)
        spin.setDecimals(3)
        spin.setValue(value)
        spin.setMinimumWidth(82)
        return spin

    def _to_mm(self, value: float) -> Decimal:
        return (Decimal(str(value)) * UNIT_TO_MM[self._unit]).quantize(Decimal("0.01"))

    def _from_mm(self, value: Decimal) -> float:
        return float(value / UNIT_TO_MM[self._unit])

    def refresh(self) -> None:
        selected_sheet = self.sheets.currentData()
        self.sheets.clear()
        for sheet in self.service.list():
            self.sheets.addItem(sheet.name, sheet.id)
        index = self.sheets.findData(selected_sheet)
        if index >= 0:
            self.sheets.setCurrentIndex(index)

        self.designs.clear()
        for artwork in self.artwork_service.list_artwork():
            item = QListWidgetItem(artwork.title)
            item.setData(Qt.ItemDataRole.UserRole, artwork.id)
            version = artwork.latest_version
            try:
                preview = self.artwork_service.preview_file(version.preview_path)
                item.setIcon(QIcon(str(preview)))
                item.setToolTip(str(preview))
            except (FileNotFoundError, OSError):
                item.setToolTip(version.original_filename)
            self.designs.addItem(item)

    def save_layout(self) -> None:
        width_mm = self._to_mm(self.sheet_width.value()) + HIDDEN_SIDE_ALLOWANCE_MM
        length_mm = self._to_mm(self.sheet_length.value())
        try:
            if self.details is None:
                self.details = self.service.create(
                    GangSheetInput(
                        self.name.text(),
                        width_mm,
                        length_mm,
                        Decimal("5"),
                        Decimal("5"),
                    )
                )
                self.history = LayoutHistory()
            else:
                self.details = self.service.resize_sheet(
                    self.details.id,
                    width_mm=width_mm,
                    length_mm=length_mm,
                    margin_mm=Decimal("5"),
                    spacing_mm=Decimal("5"),
                )
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Save layout failed", str(error))
            return
        current_id = self.details.id
        self.refresh()
        self.sheets.setCurrentIndex(self.sheets.findData(current_id))
        self._render()

    def open_selected(self) -> None:
        sheet_id = self.sheets.currentData()
        if sheet_id is None:
            return
        try:
            self.details = self.service.get(int(sheet_id))
        except LookupError as error:
            QMessageBox.warning(self, "Load failed", str(error))
            return
        self.history = LayoutHistory()
        self.name.setText(self.details.name)
        visible_width = max(Decimal("0"), self.details.width_mm - HIDDEN_SIDE_ALLOWANCE_MM)
        self.sheet_width.setValue(self._from_mm(visible_width))
        self.sheet_length.setValue(self._from_mm(self.details.length_mm))
        self._render()

    def add_selected_design(self) -> None:
        item = self.designs.currentItem()
        if item is None:
            QMessageBox.information(self, "Artwork Studio", "Select a design first.")
            return
        if self.details is None:
            self.save_layout()
        if self.details is None:
            return
        artwork_id = int(item.data(Qt.ItemDataRole.UserRole))
        sheet_id = self.details.id
        self._mutate(lambda: self.service.add_artwork(sheet_id, artwork_id, quantity=1))

    def add_designs_from_customer_folder(self) -> None:
        if self.customer_service is None:
            return
        dialog = CustomerImageDialog(self.customer_service, self, select_file=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if self.details is None:
            self.save_layout()
        if self.details is None:
            return
        customer_id = dialog.location[0]
        existing = {
            artwork.title: artwork.id for artwork in self.artwork_service.list_artwork()
        }
        failures: list[str] = []
        for record in dialog.selected_files:
            title = Path(record.original_name).stem
            artwork_id = existing.get(title)
            try:
                if artwork_id is None:
                    source = Path(record.local_path)
                    if not source.is_file():
                        source = (
                            Path(gettempdir())
                            / "kms_dtf_erp_studio_imports"
                            / str(record.id)
                            / record.original_name
                        )
                        self.customer_service.download_customer_file(record.id, source)
                    artwork = self.artwork_service.upload(
                        ArtworkInput(
                            title=title,
                            source_path=source,
                            customer_id=customer_id,
                            notes="Added from customer Design folder",
                        )
                    )
                    artwork_id = artwork.summary.id
                    existing[title] = artwork_id
                self._mutate(
                    lambda selected_id=artwork_id: self.service.add_artwork(
                        self.details.id,
                        selected_id,
                        quantity=1,
                    )
                )
            except (ValueError, LookupError, OSError) as error:
                failures.append(f"{record.original_name}: {error}")
        self.refresh()
        if failures:
            QMessageBox.warning(
                self,
                "Some designs were not added",
                "\n".join(failures),
            )

    def apply_copies(self) -> None:
        selected = self.canvas.selected_ids()
        if len(selected) != 1:
            QMessageBox.information(
                self,
                "Apply copies",
                "Select exactly one artwork object before applying copies.",
            )
            return
        additional = self.quantity.value() - 1
        if additional <= 0:
            return
        self._mutate(lambda: self.service.duplicate(selected[0], additional))

    def resize_selected(self) -> None:
        selected = self.canvas.selected_ids()
        if not selected or self.details is None:
            return
        width = self._to_mm(self.item_width.value())
        height = self._to_mm(self.item_height.value())
        if len(selected) > 1:
            self._mutate(
                lambda: self.service.resize_selection(
                    self.details.id,
                    selected,
                    width_mm=width,
                    height_mm=height,
                )
            )
            return
        if self.lock_proportions.isChecked():
            current = next(item for item in self.details.items if item.id == selected[0])
            if current.width_mm:
                height = (width * current.height_mm / current.width_mm).quantize(Decimal("0.01"))
                self.item_height.setValue(self._from_mm(height))
        self._mutate(
            lambda: self.service.update_item(
                selected[0],
                width_mm=width,
                height_mm=height,
            )
        )

    def delete_selected(self) -> None:
        selected = self.canvas.selected_ids()
        if not selected:
            return
        for item_id in selected:
            self._mutate(lambda item=item_id: self.service.delete_item(item))

    def copy_selected(self) -> None:
        if self.details is None:
            return
        selected = self.canvas.selected_ids()
        if len(selected) == 1:
            self._clipboard = next(
                item for item in self.details.items if item.id == selected[0]
            )

    def cut_selected(self) -> None:
        self.copy_selected()
        self.delete_selected()

    def paste_selected(self) -> None:
        if self.details is None or self._clipboard is None:
            return
        self._mutate(
            lambda: self.service.paste_item(self.details.id, self._clipboard)
        )

    def rotate_selected(self) -> None:
        if self.details is None:
            return
        selected = self.canvas.selected_ids()
        if len(selected) != 1:
            return
        placement = next(item for item in self.details.items if item.id == selected[0])
        self._mutate(
            lambda: self.service.update_item(
                placement.id,
                rotation_degrees=(placement.rotation_degrees + 90) % 360,
            )
        )

    def apply_rotation_value(self) -> None:
        if self.details is None:
            return
        selected = self.canvas.selected_ids()
        if len(selected) != 1:
            return
        self._mutate(
            lambda: self.service.update_item(
                selected[0],
                rotation_degrees=round(self.rotation_value.value()) % 360,
            )
        )

    def _preview_sheet_size(self) -> None:
        self.canvas.set_sheet_size(
            self._to_mm(self.sheet_width.value()) + HIDDEN_SIDE_ALLOWANCE_MM,
            self._to_mm(self.sheet_length.value()),
        )

    def align(self, edge: str) -> None:
        if self.details is None:
            return
        sheet_id = self.details.id
        self._mutate(lambda: self.service.align(sheet_id, self.canvas.selected_ids(), edge))

    def auto_arrange(self) -> None:
        if self.details is None:
            return
        sheet_id = self.details.id
        self._mutate(lambda: self.service.auto_nest(sheet_id))

    def adjust_page_to_designs(self) -> None:
        if self.details is None or not self.details.items:
            QMessageBox.information(self, "Adjust page", "Place at least one design first.")
            return
        required_length = max(item.y_mm + item.height_mm for item in self.details.items) + Decimal(
            "2"
        )
        try:
            self.details = self.service.resize_sheet(
                self.details.id,
                width_mm=self.details.width_mm,
                length_mm=max(Decimal("4"), required_length),
                margin_mm=self.details.margin_mm,
                spacing_mm=self.details.spacing_mm,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Adjust page failed", str(error))
            return
        self.sheet_length.setValue(self._from_mm(self.details.length_mm))
        self._render()

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
            self.save_layout()
        if self.details is None:
            return
        try:
            output = self.service.export(self.details.id)
        except (ValueError, OSError, LookupError) as error:
            QMessageBox.warning(self, "Export failed", str(error))
            return
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export gangsheet",
            str(output),
            "PNG image (*.png)",
        )
        if selected and selected != str(output):
            output.replace(selected)
        QMessageBox.information(self, "Export complete", f"Saved to {selected or output}")

    def _view_mode_changed(self, mode: str) -> None:
        self.canvas.set_view_mode(mode)
        self._render()

    def _unit_changed(self, unit: str) -> None:
        if unit == self._unit:
            return
        old_factor = UNIT_TO_MM[self._unit]
        values_mm = (
            Decimal(str(self.sheet_width.value())) * old_factor,
            Decimal(str(self.sheet_length.value())) * old_factor,
            Decimal(str(self.item_width.value())) * old_factor,
            Decimal(str(self.item_height.value())) * old_factor,
        )
        self._unit = unit
        self.object_units.blockSignals(True)
        self.object_units.setCurrentText(unit)
        self.object_units.blockSignals(False)
        for control, value_mm in zip(
            (self.sheet_width, self.sheet_length, self.item_width, self.item_height),
            values_mm,
            strict=True,
        ):
            control.setValue(self._from_mm(value_mm))

    def _selection_changed(self) -> None:
        selected = self.canvas.selected_ids()
        count = len(selected)
        self.item_width.setEnabled(count > 0)
        self.item_height.setEnabled(count > 0)
        self.rotation_value.setEnabled(count == 1)
        self.selection_status.setText(
            "Selected: 1 object" if count == 1 else f"Selected: {count} objects"
        )
        if count == 1 and self.details is not None:
            item = next(value for value in self.details.items if value.id == selected[0])
            self.item_width.setValue(self._from_mm(item.width_mm))
            self.item_height.setValue(self._from_mm(item.height_mm))
            self.rotation_value.setValue(float(item.rotation_degrees))
        elif count > 1 and self.details is not None:
            items = [item for item in self.details.items if item.id in selected]
            width = max(item.x_mm + item.width_mm for item in items) - min(
                item.x_mm for item in items
            )
            height = max(item.y_mm + item.height_mm for item in items) - min(
                item.y_mm for item in items
            )
            self.item_width.setValue(self._from_mm(width))
            self.item_height.setValue(self._from_mm(height))

    def _moved(self, item_id: int, x_mm: Decimal, y_mm: Decimal) -> None:
        self._mutate(
            lambda: self.service.move_item_or_group(item_id, x_mm=x_mm, y_mm=y_mm)
        )

    def _resized(
        self,
        item_id: int,
        x_mm: Decimal,
        y_mm: Decimal,
        width_mm: Decimal,
        height_mm: Decimal,
    ) -> None:
        self._mutate(
            lambda: self.service.update_item(
                item_id,
                x_mm=x_mm,
                y_mm=y_mm,
                width_mm=width_mm,
                height_mm=height_mm,
            )
        )

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

    def _render(self) -> None:
        if self.details is None:
            self.usage.setText("DTF metres: 0.000 m")
            return
        self.canvas.render_sheet(self.details, self.service, self._moved, self._resized)
        self.usage.setText(f"DTF metres: {self.details.metre_usage} m")
        self.undo_button.setEnabled(bool(self.history.undo_stack))
        self.redo_button.setEnabled(bool(self.history.redo_stack))
