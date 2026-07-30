"""Image Editor page shell.

The controls are intentionally presentation-only until each tool's behaviour is
specified.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, QRect, QSignalBlocker, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QImageReader,
    QMouseEvent,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.modules.customers.service import CUSTOMER_STORAGE_FOLDERS

if TYPE_CHECKING:
    from app.modules.customers import CustomerService

IMAGE_FILTER = (
    "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif);;All files (*)"
)

TOOL_NAMES = (
    "Background Remover",
    "Image Upscaler",
    "Eraser",
    "Selection",
    "Crop",
    "Magic Wand",
    "Colour Panel",
    "Text Editor",
    "Shape Editor",
    "Trace Bitmap",
)


class PanScrollArea(QScrollArea):
    """Scroll area with wheel zoom and middle-button canvas panning."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pan_start: QPoint | None = None
        self._horizontal_start = 0
        self._vertical_start = 0
        self.zoom_handler = None
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Wheel and self.zoom_handler is not None:
            factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
            self.zoom_handler(factor, event.globalPosition().toPoint())
            event.accept()
            return True
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.MiddleButton
        ):
            self._pan_start = event.globalPosition().toPoint()
            self._horizontal_start = self.horizontalScrollBar().value()
            self._vertical_start = self.verticalScrollBar().value()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return True
        if event.type() == QEvent.Type.MouseMove and self._pan_start is not None:
            delta = event.globalPosition().toPoint() - self._pan_start
            self.horizontalScrollBar().setValue(self._horizontal_start - delta.x())
            self.verticalScrollBar().setValue(self._vertical_start - delta.y())
            event.accept()
            return True
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.MiddleButton
        ):
            self._pan_start = None
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return True
        return super().eventFilter(watched, event)


class MoveableImageLabel(QLabel):
    """Image layer that can be repositioned inside the canvas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.move_enabled = False
        self._drag_origin: QPoint | None = None
        self._widget_origin = QPoint()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.move_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._widget_origin = self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.move_enabled and self._drag_origin is not None:
            target = self._widget_origin + (
                event.globalPosition().toPoint() - self._drag_origin
            )
            self.move(max(0, target.x()), max(0, target.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.move_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class CustomerImageDialog(QDialog):
    """Select an image location in the managed customer-folder hierarchy."""

    def __init__(
        self,
        service: CustomerService,
        parent: QWidget | None = None,
        *,
        select_file: bool,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._select_file = select_file
        self._files = []
        self.setWindowTitle(
            "Open from customer folders" if select_file else "Save to customer folder"
        )
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.customer_combo = QComboBox()
        self.date_combo = QComboBox()
        self.folder_combo = QComboBox()
        self.folder_combo.addItems(CUSTOMER_STORAGE_FOLDERS)
        form.addRow("Customer", self.customer_combo)
        form.addRow("Date", self.date_combo)
        form.addRow("Folder", self.folder_combo)
        self.file_combo = QComboBox()
        if select_file:
            form.addRow("Image", self.file_combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open
            if select_file
            else QDialogButtonBox.StandardButton.Save
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.customer_combo.currentIndexChanged.connect(self._load_dates)
        self.date_combo.currentIndexChanged.connect(self._load_files)
        self.folder_combo.currentIndexChanged.connect(self._load_files)
        for customer in service.list_customers(active=None):
            self.customer_combo.addItem(customer.display_identifier, customer.id)
        self._load_dates()

    def _load_dates(self) -> None:
        self.date_combo.clear()
        customer_id = self.customer_combo.currentData()
        if customer_id is not None:
            self.date_combo.addItems(self._service.customer_storage_dates(customer_id))
        self._load_files()

    def _load_files(self) -> None:
        self._files = []
        self.file_combo.clear()
        if not self._select_file:
            return
        customer_id = self.customer_combo.currentData()
        date_name = self.date_combo.currentText()
        folder_name = self.folder_combo.currentText()
        if customer_id is None or not date_name or not folder_name:
            return
        self._files = [
            item
            for item in self._service.list_customer_files(
                customer_id,
                date_name,
                folder_name,
            )
            if Path(item.original_name).suffix.casefold()
            in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}
        ]
        for item in self._files:
            self.file_combo.addItem(item.original_name, item.id)

    def _accept_selection(self) -> None:
        if self.customer_combo.currentData() is None or not self.date_combo.currentText():
            QMessageBox.information(
                self,
                "Customer folder required",
                "Select a dated customer folder.",
            )
            return
        if self._select_file and self.file_combo.currentData() is None:
            QMessageBox.information(self, "Image required", "Select an image to open.")
            return
        self.accept()

    @property
    def location(self) -> tuple[int, str, str]:
        return (
            int(self.customer_combo.currentData()),
            self.date_combo.currentText(),
            self.folder_combo.currentText(),
        )

    @property
    def selected_file(self):
        index = self.file_combo.currentIndex()
        return self._files[index] if 0 <= index < len(self._files) else None


class ImageEditorPage(QWidget):
    """Responsive image editor workspace."""

    def __init__(
        self,
        customer_service: CustomerService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._customer_service = customer_service
        self._image_path: Path | None = None
        self._source_file_id: int | None = None
        self._pixmap = QPixmap()
        self._zoom = 1.0
        self._dpi_x = 96.0
        self._dpi_y = 96.0
        self._image_modified = False
        self._active_tool = TOOL_NAMES[0]
        self.setObjectName("imageEditorPage")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(10)

        command_bar = QFrame()
        command_bar.setObjectName("editorCommandBar")
        command_layout = QHBoxLayout(command_bar)
        command_layout.setContentsMargins(12, 8, 12, 8)
        self.open_button = QPushButton("Open")
        self.import_button = QPushButton("Import")
        self.save_button = QPushButton("Save")
        self.trim_button = QPushButton("Trim")
        for button in (
            self.open_button,
            self.import_button,
            self.save_button,
            self.trim_button,
        ):
            button.setObjectName("secondaryButton")
            command_layout.addWidget(button)
        self.trim_button.setToolTip("Remove transparent pixels around the artwork")
        self.trim_button.setEnabled(False)
        command_layout.addSpacing(10)
        command_layout.addWidget(QLabel("Units:"))
        self.units_combo = QComboBox()
        self.units_combo.addItem("inches", "in")
        self.units_combo.addItem("millimetres", "mm")
        self.units_combo.addItem("centimetres", "cm")
        self.units_combo.addItem("pixels", "px")
        command_layout.addWidget(self.units_combo)
        self.width_value = QDoubleSpinBox()
        self.height_value = QDoubleSpinBox()
        for field in (self.width_value, self.height_value):
            field.setObjectName("imageDimension")
            field.setDecimals(2)
            field.setRange(0, 1_000_000)
            field.setKeyboardTracking(False)
            field.setMinimumWidth(92)
        command_layout.addWidget(QLabel("W:"))
        command_layout.addWidget(self.width_value)
        self.aspect_lock_button = QPushButton("🔒")
        self.aspect_lock_button.setObjectName("aspectLockButton")
        self.aspect_lock_button.setCheckable(True)
        self.aspect_lock_button.setChecked(True)
        self.aspect_lock_button.setToolTip("Lock aspect ratio")
        self.aspect_lock_button.setFixedSize(34, 30)
        command_layout.addWidget(self.aspect_lock_button)
        command_layout.addWidget(QLabel("H:"))
        command_layout.addWidget(self.height_value)
        command_layout.addStretch()
        self.image_info = QLabel("No image loaded")
        self.image_info.setObjectName("cardBody")
        command_layout.addWidget(self.image_info)
        self.zoom_percentage = QLabel("100%")
        self.zoom_percentage.setObjectName("zoomPercentage")
        self.zoom_percentage.setMinimumWidth(52)
        self.zoom_percentage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        command_layout.addWidget(self.zoom_percentage)
        outer_layout.addWidget(command_bar)

        workspace = QWidget()
        page_layout = QHBoxLayout(workspace)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)
        outer_layout.addWidget(workspace, 1)

        self.tool_names_panel = QFrame()
        self.tool_names_panel.setObjectName("editorPanel")
        self.tool_names_panel.setMinimumWidth(145)
        self.tool_names_panel.setMaximumWidth(190)
        names_layout = QVBoxLayout(self.tool_names_panel)
        names_layout.setContentsMargins(12, 16, 12, 16)
        names_layout.setSpacing(14)

        self.tool_labels: dict[str, QPushButton] = {}
        for tool_index, tool_name in enumerate(TOOL_NAMES):
            button = QPushButton(tool_name.upper())
            button.setObjectName("editorToolName")
            button.setProperty("active", tool_index == 0)
            button.setCheckable(True)
            button.setChecked(tool_index == 0)
            button.setMinimumHeight(38)
            button.clicked.connect(
                lambda _checked=False, name=tool_name: self._select_tool(name)
            )
            names_layout.addWidget(button)
            self.tool_labels[tool_name] = button
        names_layout.addStretch(1)
        page_layout.addWidget(self.tool_names_panel)

        self.canvas = QFrame()
        self.canvas.setObjectName("imageEditorCanvas")
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        canvas_layout = QVBoxLayout(self.canvas)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        self.canvas_scroll = PanScrollArea()
        self.canvas_scroll.setObjectName("imageEditorCanvasScroll")
        self.canvas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_scroll.setWidgetResizable(False)
        checkerboard = QPixmap(24, 24)
        painter = QPainter(checkerboard)
        painter.fillRect(0, 0, 24, 24, QColor("#FFFFFF"))
        painter.fillRect(0, 0, 12, 12, QColor("#D8D8D8"))
        painter.fillRect(12, 12, 12, 12, QColor("#D8D8D8"))
        painter.end()
        self.canvas_workspace = QWidget()
        self.canvas_workspace.setObjectName("imageEditorWorkspace")
        self.canvas_workspace.setMinimumSize(800, 600)
        workspace_palette = self.canvas_workspace.palette()
        workspace_palette.setBrush(
            QPalette.ColorRole.Window,
            QBrush(QColor("#303030")),
        )
        self.canvas_workspace.setPalette(workspace_palette)
        self.canvas_workspace.setAutoFillBackground(True)
        self.canvas_workspace.installEventFilter(self.canvas_scroll)
        self.canvas_placeholder = MoveableImageLabel(self.canvas_workspace)
        self.canvas_placeholder.setObjectName("canvasPlaceholder")
        canvas_palette = self.canvas_placeholder.palette()
        canvas_palette.setBrush(
            QPalette.ColorRole.Window,
            QBrush(checkerboard),
        )
        self.canvas_placeholder.setPalette(canvas_palette)
        self.canvas_placeholder.setAutoFillBackground(True)
        self.canvas_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_placeholder.setMinimumSize(400, 300)
        self.canvas_placeholder.move(200, 150)
        self.canvas_placeholder.installEventFilter(self.canvas_scroll)
        self.canvas_scroll.zoom_handler = self.zoom_at
        self.canvas_scroll.setWidget(self.canvas_workspace)
        canvas_layout.addWidget(self.canvas_scroll)
        page_layout.addWidget(self.canvas, 1)

        self.inspector = QTabWidget()
        self.inspector.setObjectName("imageEditorInspector")
        self.inspector.setMinimumWidth(170)
        self.inspector.setMaximumWidth(240)
        self.layers_panel = QWidget()
        self.layers_panel.setObjectName("inspectorPage")
        self.channels_panel = QWidget()
        self.channels_panel.setObjectName("inspectorPage")
        self.inspector.addTab(self.layers_panel, "LAYERS")
        self.inspector.addTab(self.channels_panel, "CHANNELS")
        page_layout.addWidget(self.inspector)

        self.open_button.setEnabled(customer_service is not None)
        self.save_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_customer_image)
        self.import_button.clicked.connect(self.import_local_image)
        self.save_button.clicked.connect(self.save_customer_image)
        self.trim_button.clicked.connect(self.trim_transparent_pixels)
        self.units_combo.currentIndexChanged.connect(self._update_dimensions)
        self.width_value.editingFinished.connect(
            lambda: self._resize_from_dimensions("width")
        )
        self.height_value.editingFinished.connect(
            lambda: self._resize_from_dimensions("height")
        )
        self.aspect_lock_button.toggled.connect(self._set_aspect_lock)

        self.setStyleSheet(
            """
            QFrame#editorCommandBar, QFrame#editorPanel, QFrame#imageEditorCanvas,
            QTabWidget#imageEditorInspector::pane {
                background: rgba(255, 255, 255, 205);
                border: 1px solid rgba(255, 255, 255, 225);
                border-radius: 16px;
            }
            QPushButton#editorToolName {
                color: #273151;
                font: 600 11px "Segoe UI";
                background: transparent;
                border: 1px solid transparent;
                border-radius: 9px;
                padding: 4px;
            }
            QPushButton#editorToolName:hover {
                background: rgba(108, 92, 231, 14);
                border: 1px solid rgba(108, 92, 231, 38);
            }
            QPushButton#editorToolName[active="true"] {
                color: #5147B8;
                background: rgba(108, 92, 231, 24);
                border: 1px solid rgba(108, 92, 231, 75);
            }
            QLabel#canvasPlaceholder {
                color: rgba(39, 49, 81, 120);
                font: 600 44px "Segoe UI";
            }
            QLabel#zoomPercentage {
                color: #5147B8;
                font: 700 12px "Segoe UI";
                background: rgba(108, 92, 231, 20);
                border: 1px solid rgba(108, 92, 231, 55);
                border-radius: 8px;
                padding: 5px 8px;
            }
            QDoubleSpinBox#imageDimension {
                color: #273151;
                background: rgba(255, 255, 255, 170);
                border: 1px solid rgba(108, 92, 231, 45);
                border-radius: 7px;
                padding: 4px 6px;
            }
            QPushButton#aspectLockButton {
                color: #5147B8;
                background: rgba(108, 92, 231, 20);
                border: 1px solid rgba(108, 92, 231, 55);
                border-radius: 7px;
                font-size: 14px;
            }
            QPushButton#aspectLockButton:checked {
                background: rgba(108, 92, 231, 42);
                border-color: rgba(108, 92, 231, 100);
            }
            QScrollArea#imageEditorCanvasScroll {
                border: 0;
            }
            QTabWidget#imageEditorInspector::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background: transparent;
                color: #7A84A3;
                border: 0;
                padding: 12px 9px 9px 9px;
                font: 600 11px "Segoe UI";
            }
            QTabBar::tab:selected {
                color: #5147B8;
                border-bottom: 2px solid #6C5CE7;
            }
            QWidget#inspectorPage {
                background: transparent;
            }
            """
        )

    def _select_tool(self, selected_name: str) -> None:
        self._active_tool = selected_name
        for tool_name, button in self.tool_labels.items():
            active = tool_name == selected_name
            button.setChecked(active)
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
        if selected_name == "Crop":
            self.width_value.setToolTip("Crop or extend canvas width")
            self.height_value.setToolTip("Crop or extend canvas height")
        else:
            self.width_value.setToolTip("Resize image width")
            self.height_value.setToolTip("Resize image height")

    def set_zoom(self, zoom: float) -> None:
        if self._pixmap.isNull():
            return
        self._zoom = max(0.1, min(8.0, zoom))
        size = self._pixmap.size() * self._zoom
        scaled = self._pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.canvas_placeholder.setPixmap(scaled)
        self.canvas_placeholder.setFixedSize(scaled.size())
        viewport = self.canvas_scroll.viewport().size()
        self.canvas_workspace.resize(
            max(
                viewport.width() * 3,
                self.canvas_placeholder.x() + scaled.width() + viewport.width(),
            ),
            max(
                viewport.height() * 3,
                self.canvas_placeholder.y() + scaled.height() + viewport.height(),
            ),
        )
        self.image_info.setText(
            f"{self._image_path.name}  •  {self._pixmap.width()} × "
            f"{self._pixmap.height()} px"
        )
        self.zoom_percentage.setText(f"{round(self._zoom * 100)}%")

    def zoom_at(self, factor: float, global_position: QPoint) -> None:
        if self._pixmap.isNull():
            return
        viewport_position = self.canvas_scroll.viewport().mapFromGlobal(global_position)
        horizontal = self.canvas_scroll.horizontalScrollBar()
        vertical = self.canvas_scroll.verticalScrollBar()
        content_x = horizontal.value() + viewport_position.x()
        content_y = vertical.value() + viewport_position.y()
        image_x = self.canvas_placeholder.x()
        image_y = self.canvas_placeholder.y()
        old_zoom = self._zoom
        self.set_zoom(old_zoom * factor)
        applied_factor = self._zoom / old_zoom
        anchored_x = image_x + ((content_x - image_x) * applied_factor)
        anchored_y = image_y + ((content_y - image_y) * applied_factor)
        horizontal.setValue(round(anchored_x - viewport_position.x()))
        vertical.setValue(round(anchored_y - viewport_position.y()))

    def _update_dimensions(self) -> None:
        if self._pixmap.isNull():
            self.width_value.setValue(0)
            self.height_value.setValue(0)
            return
        unit = self.units_combo.currentData()
        if unit == "px":
            width = float(self._pixmap.width())
            height = float(self._pixmap.height())
            decimals = 0
        else:
            width_inches = self._pixmap.width() / self._dpi_x
            height_inches = self._pixmap.height() / self._dpi_y
            multiplier = {"in": 1.0, "mm": 25.4, "cm": 2.54}[unit]
            width = width_inches * multiplier
            height = height_inches * multiplier
            decimals = 2
        suffix = {"in": " in", "mm": " mm", "cm": " cm", "px": " px"}[unit]
        for field, value in (
            (self.width_value, width),
            (self.height_value, height),
        ):
            with QSignalBlocker(field):
                field.setDecimals(decimals)
                field.setSuffix(suffix)
                field.setValue(value)

    def _set_aspect_lock(self, locked: bool) -> None:
        self.aspect_lock_button.setText("🔒" if locked else "🔓")
        self.aspect_lock_button.setToolTip(
            "Unlock aspect ratio" if locked else "Lock aspect ratio"
        )

    def _resize_from_dimensions(self, changed_dimension: str | None = None) -> None:
        if self._pixmap.isNull():
            return
        aspect_ratio = self._pixmap.width() / self._pixmap.height()
        unit = self.units_combo.currentData()
        width = self.width_value.value()
        height = self.height_value.value()
        if unit == "px":
            width_pixels = round(width)
            height_pixels = round(height)
        else:
            divisor = {"in": 1.0, "mm": 25.4, "cm": 2.54}[unit]
            width_pixels = round((width / divisor) * self._dpi_x)
            height_pixels = round((height / divisor) * self._dpi_y)
        if self.aspect_lock_button.isChecked():
            if changed_dimension == "width":
                height_pixels = round(width_pixels / aspect_ratio)
            elif changed_dimension == "height":
                width_pixels = round(height_pixels * aspect_ratio)
        width_pixels = max(1, width_pixels)
        height_pixels = max(1, height_pixels)
        if (
            width_pixels == self._pixmap.width()
            and height_pixels == self._pixmap.height()
        ):
            return
        if self._active_tool == "Crop":
            canvas = QPixmap(width_pixels, height_pixels)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.drawPixmap(
                (width_pixels - self._pixmap.width()) // 2,
                (height_pixels - self._pixmap.height()) // 2,
                self._pixmap,
            )
            painter.end()
            self._pixmap = canvas
        else:
            self._pixmap = self._pixmap.scaled(
                width_pixels,
                height_pixels,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._image_modified = True
        self.set_zoom(self._zoom)
        self._update_dimensions()

    def trim_transparent_pixels(self) -> None:
        if self._pixmap.isNull():
            return
        import numpy as np

        image = self._pixmap.toImage().convertToFormat(
            QImage.Format.Format_RGBA8888
        )
        buffer = image.constBits()
        pixels = np.frombuffer(buffer, dtype=np.uint8, count=image.sizeInBytes())
        rows = pixels.reshape(image.height(), image.bytesPerLine())
        alpha = rows[:, 3 : image.width() * 4 : 4]
        visible_y, visible_x = np.nonzero(alpha)
        if not len(visible_x):
            QMessageBox.information(
                self,
                "Nothing to trim",
                "The image contains no visible pixels.",
            )
            return
        left = int(visible_x.min())
        top = int(visible_y.min())
        width = int(visible_x.max()) - left + 1
        height = int(visible_y.max()) - top + 1
        if left == 0 and top == 0 and width == image.width() and height == image.height():
            QMessageBox.information(
                self,
                "Nothing to trim",
                "There are no transparent edge pixels to remove.",
            )
            return
        self._pixmap = QPixmap.fromImage(image.copy(QRect(left, top, width, height)))
        self._image_modified = True
        self.set_zoom(self._zoom)
        self._update_dimensions()

    def _edited_source(self) -> Path:
        if not self._image_modified or self._image_path is None:
            return self._image_path
        output_directory = Path(gettempdir()) / "kms_dtf_erp_image_editor_edits"
        output_directory.mkdir(parents=True, exist_ok=True)
        output = output_directory / self._image_path.name
        if not self._pixmap.save(str(output)):
            raise RuntimeError("The resized image could not be encoded")
        return output

    def fit_to_canvas(self) -> None:
        if self._pixmap.isNull():
            return
        available = self.canvas_scroll.viewport().size()
        zoom = min(
            available.width() / self._pixmap.width(),
            available.height() / self._pixmap.height(),
        )
        self.set_zoom(zoom)

    def import_local_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import image from local system",
            "",
            IMAGE_FILTER,
        )
        if filename:
            self.load_image(Path(filename))

    def open_customer_image(self) -> None:
        if self._customer_service is None:
            return
        dialog = CustomerImageDialog(self._customer_service, self, select_file=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        record = dialog.selected_file
        if record is None:
            return
        path = Path(record.local_path)
        if not path.is_file():
            cache = Path(gettempdir()) / "kms_dtf_erp_image_editor"
            cache.mkdir(parents=True, exist_ok=True)
            path = cache / f"{record.id}{Path(record.original_name).suffix.casefold()}"
            try:
                self._customer_service.download_customer_file(record.id, path)
            except Exception as error:
                QMessageBox.warning(self, "Image unavailable", str(error))
                return
        self.load_image(path, source_file_id=record.id)

    def load_image(self, path: Path, *, source_file_id: int | None = None) -> bool:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, "Image not opened", reader.errorString())
            return False
        self._image_path = path
        self._source_file_id = source_file_id
        self._pixmap = QPixmap.fromImage(image)
        self._image_modified = False
        dots_per_metre_x = image.dotsPerMeterX()
        dots_per_metre_y = image.dotsPerMeterY()
        self._dpi_x = dots_per_metre_x * 0.0254 if dots_per_metre_x > 0 else 96.0
        self._dpi_y = dots_per_metre_y * 0.0254 if dots_per_metre_y > 0 else 96.0
        self.canvas_placeholder.setText("")
        self.set_zoom(1.0)
        viewport = self.canvas_scroll.viewport().size()
        self.canvas_workspace.resize(
            max(viewport.width() * 3, self._pixmap.width() + viewport.width() * 2),
            max(viewport.height() * 3, self._pixmap.height() + viewport.height() * 2),
        )
        self.canvas_placeholder.move(
            (self.canvas_workspace.width() - self._pixmap.width()) // 2,
            (self.canvas_workspace.height() - self._pixmap.height()) // 2,
        )
        self.canvas_scroll.horizontalScrollBar().setValue(
            self.canvas_placeholder.x()
            - ((viewport.width() - self._pixmap.width()) // 2)
        )
        self.canvas_scroll.verticalScrollBar().setValue(
            self.canvas_placeholder.y()
            - ((viewport.height() - self._pixmap.height()) // 2)
        )
        self._update_dimensions()
        self.save_button.setEnabled(self._customer_service is not None)
        self.trim_button.setEnabled(True)
        return True

    def save_customer_image(self) -> None:
        if self._customer_service is None or self._image_path is None:
            return
        try:
            source = self._edited_source()
        except Exception as error:
            QMessageBox.warning(self, "Image not saved", str(error))
            return
        if self._source_file_id is not None:
            try:
                self._customer_service.replace_customer_file(
                    self._source_file_id,
                    source,
                )
            except Exception as error:
                QMessageBox.warning(self, "Image not saved", str(error))
                return
            QMessageBox.information(
                self,
                "Image saved",
                "The existing customer image was updated in the same file.",
            )
            return
        dialog = CustomerImageDialog(self._customer_service, self, select_file=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        filename, accepted = QInputDialog.getText(
            self,
            "Save image",
            "File name",
            text=self._image_path.name,
        )
        if not accepted or not filename.strip():
            return
        suffix = self._image_path.suffix.casefold()
        if Path(filename).suffix.casefold() != suffix:
            QMessageBox.information(
                self,
                "Original format retained",
                f"The file extension must remain {suffix} to preserve the original image bytes.",
            )
            return
        staging = Path(gettempdir()) / "kms_dtf_erp_image_editor_save"
        staging.mkdir(parents=True, exist_ok=True)
        destination = staging / Path(filename).name
        destination.write_bytes(source.read_bytes())
        try:
            record = self._customer_service.upload_customer_file(
                *dialog.location,
                destination,
            )
        except Exception as error:
            QMessageBox.warning(self, "Image not saved", str(error))
            return
        self._source_file_id = record.id
        QMessageBox.information(
            self,
            "Image saved",
            "The original-quality image was queued in the selected customer folder.",
        )
