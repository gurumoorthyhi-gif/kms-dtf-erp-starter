"""Image Editor page shell.

The controls are intentionally presentation-only until each tool's behaviour is
specified.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSettings, QSignalBlocker, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QImage,
    QImageReader,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QShortcut,
    QTransform,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.customers.service import (
    CUSTOMER_STORAGE_FOLDERS,
    CustomerStorageDateExistsError,
)

if TYPE_CHECKING:
    from app.modules.customers import CustomerService

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif);;All files (*)"

TOOL_NAMES = (
    "Background Remover",
    "Image Upscaler",
    "Eraser",
    "Magic Eraser",
    "Select",
    "Crop",
    "Magic Wand",
    "Colour Panel",
    "Text Editor",
    "Shape Editor",
    "Trace Bitmap",
)


@dataclass
class ImageDocument:
    """Independent state for one open editor tab."""

    path: Path
    pixmap: QPixmap
    source_file_id: int | None
    dpi_x: float
    dpi_y: float
    modified: bool = False
    zoom: float = 1.0
    rotation: float = 0.0
    undo_stack: list[tuple[QPixmap, bool, float]] = dataclass_field(default_factory=list)
    redo_stack: list[tuple[QPixmap, bool, float]] = dataclass_field(default_factory=list)


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
            target = self._widget_origin + (event.globalPosition().toPoint() - self._drag_origin)
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


class CropOverlay(QWidget):
    """Interactive crop boundary with Photoshop-style handles and guides."""

    HANDLE_SIZE = 12
    MINIMUM_SIZE = 20

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.crop_rect = QRectF()
        self._drag_mode = ""
        self._drag_start = QPoint()
        self._start_rect = QRectF()
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.hide()

    def begin(self, image_geometry: QRect) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.crop_rect = QRectF(image_geometry)
        self.show()
        self.raise_()
        self.update()

    def _handles(self) -> dict[str, QPoint]:
        rect = self.crop_rect
        return {
            "top_left": rect.topLeft().toPoint(),
            "top": QPoint(round(rect.center().x()), round(rect.top())),
            "top_right": rect.topRight().toPoint(),
            "right": QPoint(round(rect.right()), round(rect.center().y())),
            "bottom_right": rect.bottomRight().toPoint(),
            "bottom": QPoint(round(rect.center().x()), round(rect.bottom())),
            "bottom_left": rect.bottomLeft().toPoint(),
            "left": QPoint(round(rect.left()), round(rect.center().y())),
        }

    def _hit_test(self, position: QPoint) -> str:
        radius = self.HANDLE_SIZE
        for name, centre in self._handles().items():
            if (position - centre).manhattanLength() <= radius:
                return name
        return "move" if self.crop_rect.contains(position) else ""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self._drag_mode = self._hit_test(event.position().toPoint())
        if not self._drag_mode:
            event.ignore()
            return
        self._drag_start = event.position().toPoint()
        self._start_rect = QRectF(self.crop_rect)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        position = event.position().toPoint()
        if not self._drag_mode:
            cursor = self._hit_test(position)
            cursor_shape = {
                "top_left": Qt.CursorShape.SizeFDiagCursor,
                "bottom_right": Qt.CursorShape.SizeFDiagCursor,
                "top_right": Qt.CursorShape.SizeBDiagCursor,
                "bottom_left": Qt.CursorShape.SizeBDiagCursor,
                "top": Qt.CursorShape.SizeVerCursor,
                "bottom": Qt.CursorShape.SizeVerCursor,
                "left": Qt.CursorShape.SizeHorCursor,
                "right": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.SizeAllCursor,
            }.get(cursor, Qt.CursorShape.ArrowCursor)
            self.setCursor(cursor_shape)
            return
        delta = position - self._drag_start
        rect = QRectF(self._start_rect)
        if self._drag_mode == "move":
            rect.translate(delta.x(), delta.y())
            rect.moveLeft(max(0, min(rect.left(), self.width() - rect.width())))
            rect.moveTop(max(0, min(rect.top(), self.height() - rect.height())))
        else:
            if "left" in self._drag_mode:
                rect.setLeft(min(rect.right() - self.MINIMUM_SIZE, rect.left() + delta.x()))
            if "right" in self._drag_mode:
                rect.setRight(max(rect.left() + self.MINIMUM_SIZE, rect.right() + delta.x()))
            if "top" in self._drag_mode:
                rect.setTop(min(rect.bottom() - self.MINIMUM_SIZE, rect.top() + delta.y()))
            if "bottom" in self._drag_mode:
                rect.setBottom(max(rect.top() + self.MINIMUM_SIZE, rect.bottom() + delta.y()))
            rect.setLeft(max(0, rect.left()))
            rect.setTop(max(0, rect.top()))
            rect.setRight(min(self.width() - 1, rect.right()))
            rect.setBottom(min(self.height() - 1, rect.bottom()))
        self.crop_rect = rect.normalized()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_mode:
            self._drag_mode = ""
            event.accept()
            return
        event.ignore()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        crop = self.crop_rect
        shade = QColor(0, 0, 0, 135)
        painter.fillRect(QRectF(0, 0, self.width(), crop.top()), shade)
        painter.fillRect(QRectF(0, crop.bottom(), self.width(), self.height()), shade)
        painter.fillRect(QRectF(0, crop.top(), crop.left(), crop.height()), shade)
        painter.fillRect(
            QRectF(crop.right(), crop.top(), self.width() - crop.right(), crop.height()),
            shade,
        )
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawRect(crop)
        painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
        for fraction in (1 / 3, 2 / 3):
            x = crop.left() + crop.width() * fraction
            y = crop.top() + crop.height() * fraction
            painter.drawLine(round(x), round(crop.top()), round(x), round(crop.bottom()))
            painter.drawLine(round(crop.left()), round(y), round(crop.right()), round(y))
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(QColor("#FFFFFF"))
        half = self.HANDLE_SIZE // 2
        for centre in self._handles().values():
            painter.drawRect(
                centre.x() - half,
                centre.y() - half,
                self.HANDLE_SIZE,
                self.HANDLE_SIZE,
            )


class SelectionOverlay(QWidget):
    """Lightweight move/resize preview for the visible artwork."""

    HANDLE_SIZE = 10
    MINIMUM_SIZE = 8

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.transform_completed = None
        self.aspect_locked = None
        self.movement_bounds = QRect()
        self._drag_start = QPoint()
        self._start_geometry = QRect()
        self._drag_mode = ""
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.hide()

    def begin(self, geometry: QRect, movement_bounds: QRect) -> None:
        self.movement_bounds = QRect(movement_bounds)
        self.setGeometry(geometry)
        self.show()
        self.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._start_geometry = self.geometry()
            self._drag_mode = self._hit_test(event.position().toPoint())
            if self._drag_mode == "move":
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        start = QRect(self._start_geometry)
        end = self.geometry()
        mode = self._drag_mode
        self._drag_mode = ""
        self._update_cursor(event.position().toPoint())
        if callable(self.transform_completed) and start != end:
            self.transform_completed(start, end, mode)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not event.buttons() & Qt.MouseButton.LeftButton:
            self._update_cursor(event.position().toPoint())
            event.accept()
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        target = QRect(self._start_geometry)
        bounds = self.movement_bounds
        mode = self._drag_mode
        if mode == "move":
            target.translate(delta)
            target.moveLeft(
                max(bounds.left(), min(target.left(), bounds.right() - target.width() + 1))
            )
            target.moveTop(
                max(bounds.top(), min(target.top(), bounds.bottom() - target.height() + 1))
            )
        else:
            if "left" in mode:
                target.setLeft(
                    max(
                        bounds.left(),
                        min(target.left() + delta.x(), target.right() - self.MINIMUM_SIZE + 1),
                    )
                )
            if "right" in mode:
                target.setRight(
                    min(
                        bounds.right(),
                        max(target.right() + delta.x(), target.left() + self.MINIMUM_SIZE - 1),
                    )
                )
            if "top" in mode:
                target.setTop(
                    max(
                        bounds.top(),
                        min(target.top() + delta.y(), target.bottom() - self.MINIMUM_SIZE + 1),
                    )
                )
            if "bottom" in mode:
                target.setBottom(
                    min(
                        bounds.bottom(),
                        max(target.bottom() + delta.y(), target.top() + self.MINIMUM_SIZE - 1),
                    )
                )
            if "_" in mode and callable(self.aspect_locked) and self.aspect_locked():
                aspect = self._start_geometry.width() / max(1, self._start_geometry.height())
                horizontal_change = abs(delta.x()) / max(1, self._start_geometry.width())
                vertical_change = abs(delta.y()) / max(1, self._start_geometry.height())
                if horizontal_change >= vertical_change:
                    height = max(self.MINIMUM_SIZE, round(target.width() / aspect))
                    if "top" in mode:
                        target.setTop(target.bottom() - height + 1)
                    else:
                        target.setBottom(target.top() + height - 1)
                else:
                    width = max(self.MINIMUM_SIZE, round(target.height() * aspect))
                    if "left" in mode:
                        target.setLeft(target.right() - width + 1)
                    else:
                        target.setRight(target.left() + width - 1)
                target = target.intersected(bounds)
        self.setGeometry(target)
        event.accept()

    def _handles(self) -> dict[str, QPoint]:
        rect = self.rect()
        return {
            "top_left": rect.topLeft(),
            "top": QPoint(rect.center().x(), rect.top()),
            "top_right": rect.topRight(),
            "right": QPoint(rect.right(), rect.center().y()),
            "bottom_right": rect.bottomRight(),
            "bottom": QPoint(rect.center().x(), rect.bottom()),
            "bottom_left": rect.bottomLeft(),
            "left": QPoint(rect.left(), rect.center().y()),
        }

    def _hit_test(self, position: QPoint) -> str:
        radius = self.HANDLE_SIZE
        closest = min(
            self._handles().items(),
            key=lambda item: (position - item[1]).manhattanLength(),
        )
        if (position - closest[1]).manhattanLength() <= radius:
            return closest[0]
        return "move"

    def _update_cursor(self, position: QPoint) -> None:
        mode = self._hit_test(position)
        cursors = {
            "top_left": Qt.CursorShape.SizeFDiagCursor,
            "bottom_right": Qt.CursorShape.SizeFDiagCursor,
            "top_right": Qt.CursorShape.SizeBDiagCursor,
            "bottom_left": Qt.CursorShape.SizeBDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
        }
        self.setCursor(cursors.get(mode, Qt.CursorShape.SizeAllCursor))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#32C5FF"), 2, Qt.PenStyle.DashLine))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#273151"), 1))
        size = self.HANDLE_SIZE
        half = size // 2
        for point in self._handles().values():
            painter.drawRect(point.x() - half, point.y() - half, size, size)


class CustomerImageDialog(QDialog):
    """Three-pane browser for managed customer images and save locations."""

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
        self._preview_pixmap = QPixmap()
        self.setWindowTitle(
            "Open images from customer folders" if select_file else "Save image to customer folder"
        )
        self.resize(1200, 720)
        self.setMinimumSize(960, 600)

        layout = QVBoxLayout(self)
        heading = QLabel("Select images to open" if select_file else "Select a destination folder")
        heading.setObjectName("detailsTitle")
        layout.addWidget(heading)

        self.browser_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.browser_splitter.setChildrenCollapsible(False)

        tree_panel = QFrame()
        tree_panel.setObjectName("glassCard")
        tree_layout = QVBoxLayout(tree_panel)
        tree_title = QLabel("Customers and folders")
        tree_title.setObjectName("detailsTitle")
        tree_layout.addWidget(tree_title)
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMinimumWidth(260)
        tree_layout.addWidget(self.folder_tree, 1)
        self.create_date_button = QPushButton("Create Current Date Folder")
        self.create_date_button.setObjectName("secondaryButton")
        self.import_designs_button = QPushButton("Import Designs")
        self.import_designs_button.setObjectName("primaryButton")
        self.import_designs_button.setEnabled(False)
        tree_layout.addWidget(self.create_date_button)
        tree_layout.addWidget(self.import_designs_button)
        self.browser_splitter.addWidget(tree_panel)

        files_panel = QFrame()
        files_panel.setObjectName("glassCard")
        files_layout = QVBoxLayout(files_panel)
        self.folder_heading = QLabel("Select a customer folder")
        self.folder_heading.setObjectName("detailsTitle")
        files_layout.addWidget(self.folder_heading)
        self.file_table = QTableWidget(0, 3)
        self.file_table.setHorizontalHeaderLabels(["File", "Size", "Status"])
        self.file_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self.file_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.file_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        files_layout.addWidget(self.file_table, 1)
        self.browser_splitter.addWidget(files_panel)

        preview_panel = QFrame()
        preview_panel.setObjectName("glassCard")
        preview_layout = QVBoxLayout(preview_panel)
        preview_title = QLabel("Preview")
        preview_title.setObjectName("detailsTitle")
        preview_layout.addWidget(preview_title)
        self.preview_label = QLabel("Select an image to preview")
        self.preview_label.setObjectName("emptyState")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setWidget(self.preview_label)
        self.preview_scroll.viewport().installEventFilter(self)
        preview_layout.addWidget(self.preview_scroll, 1)
        self.preview_name = QLabel("No image selected")
        self.preview_name.setObjectName("cardBody")
        self.preview_name.setWordWrap(True)
        preview_layout.addWidget(self.preview_name)
        self.browser_splitter.addWidget(preview_panel)
        self.browser_splitter.setSizes([280, 520, 400])
        layout.addWidget(self.browser_splitter, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open
            if select_file
            else QDialogButtonBox.StandardButton.Save
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.folder_tree.currentItemChanged.connect(self._load_folder)
        self.file_table.itemSelectionChanged.connect(self._preview_selection)
        self.file_table.doubleClicked.connect(
            lambda: self._accept_selection() if self._select_file else None
        )
        self.create_date_button.clicked.connect(self._create_current_date_folder)
        self.import_designs_button.clicked.connect(self._import_designs)
        self._populate_tree()

    def _populate_tree(
        self,
        selected_location: tuple[int, str, str] | None = None,
    ) -> None:
        self.folder_tree.clear()
        first_customer = None
        selected_folder = None
        for serial, customer in enumerate(
            self._service.list_customers(active=None),
            start=1,
        ):
            customer_item = QTreeWidgetItem([f"{serial}. {customer.display_identifier}"])
            customer_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                ("customer", customer.id, customer.display_identifier),
            )
            self.folder_tree.addTopLevelItem(customer_item)
            first_customer = first_customer or customer_item
            for date_name in self._service.customer_storage_dates(customer.id):
                date_item = QTreeWidgetItem([date_name])
                customer_item.addChild(date_item)
                for folder_name in CUSTOMER_STORAGE_FOLDERS:
                    folder_item = QTreeWidgetItem([folder_name])
                    folder_item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        (
                            "folder",
                            customer.id,
                            date_name,
                            folder_name,
                            customer.display_identifier,
                        ),
                    )
                    date_item.addChild(folder_item)
                    if selected_location == (
                        customer.id,
                        date_name,
                        folder_name,
                    ):
                        selected_folder = folder_item
                date_item.setExpanded(False)
            customer_item.setExpanded(False)
        target = selected_folder or first_customer
        if target is not None:
            if selected_folder is not None:
                parent = selected_folder.parent()
                while parent is not None:
                    parent.setExpanded(True)
                    parent = parent.parent()
            self.folder_tree.setCurrentItem(target)

    def _current_location(self) -> tuple[int, str, str] | None:
        item = self.folder_tree.currentItem()
        value = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if value and value[0] == "folder":
            return int(value[1]), value[2], value[3]
        return None

    def _load_folder(self, item: QTreeWidgetItem | None, _previous=None) -> None:
        self._files = []
        self.file_table.setRowCount(0)
        self._show_preview_message("Select an image to preview")
        self.import_designs_button.setEnabled(False)
        value = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if not value or value[0] != "folder":
            self.folder_heading.setText("Select a customer folder")
            return
        customer_id, date_name, folder_name = value[1], value[2], value[3]
        self.import_designs_button.setEnabled(folder_name == "Design")
        self.folder_heading.setText(f"{value[4]}  /  {date_name}  /  {folder_name}")
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
        self.file_table.setRowCount(len(self._files))
        for row, record in enumerate(self._files):
            size_bytes = int(getattr(record, "size_bytes", 0) or 0)
            size_text = (
                f"{size_bytes / 1_048_576:.1f} MB"
                if size_bytes >= 1_048_576
                else f"{size_bytes / 1024:.1f} KB"
            )
            values = (
                record.original_name,
                size_text,
                str(getattr(record, "transfer_state", "")).title(),
            )
            for column, text in enumerate(values):
                self.file_table.setItem(row, column, QTableWidgetItem(text))

    def _selected_customer_id(self) -> int | None:
        item = self.folder_tree.currentItem()
        while item is not None:
            value = item.data(0, Qt.ItemDataRole.UserRole)
            if value and value[0] in {"customer", "folder"}:
                return int(value[1])
            item = item.parent()
        return None

    def _create_current_date_folder(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is None:
            QMessageBox.information(
                self,
                "Customer required",
                "Select a customer before creating the current date folder.",
            )
            return
        try:
            date_name = self._service.create_customer_date_folder(customer_id)
        except CustomerStorageDateExistsError as error:
            QMessageBox.information(self, "Folder already exists", str(error))
            date_names = self._service.customer_storage_dates(customer_id)
            if not date_names:
                return
            date_name = date_names[0]
        except Exception as error:
            QMessageBox.warning(self, "Folder not created", str(error))
            return
        self._populate_tree((customer_id, date_name, "Design"))

    def _import_designs(self) -> None:
        location = self._current_location()
        if location is None or location[2] != "Design":
            QMessageBox.information(
                self,
                "Design folder required",
                "Select a dated Design folder before importing images.",
            )
            return
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Import designs to customer folder",
            "",
            IMAGE_FILTER,
        )
        failures = []
        for filename in filenames:
            try:
                self._service.upload_customer_file(
                    *location,
                    Path(filename),
                )
            except Exception as error:
                failures.append(f"{Path(filename).name}: {error}")
        if failures:
            QMessageBox.warning(
                self,
                "Some designs were not imported",
                "\n".join(failures),
            )
        if filenames:
            self._load_folder(self.folder_tree.currentItem())

    def _selected_record(self):
        row = self.file_table.currentRow()
        return self._files[row] if 0 <= row < len(self._files) else None

    def _preview_selection(self) -> None:
        record = self._selected_record()
        if record is None:
            self.preview_name.setText("No image selected")
            self._show_preview_message("Select an image to preview")
            return
        self.preview_name.setText(record.original_name)
        path = Path(record.local_path)
        if not path.is_file():
            cache = Path(gettempdir()) / "kms_dtf_erp_image_browser_previews"
            cache.mkdir(parents=True, exist_ok=True)
            path = cache / f"{record.id}{Path(record.original_name).suffix.casefold()}"
            try:
                self._service.download_customer_file(record.id, path)
            except Exception as error:
                self._show_preview_message(f"Preview unavailable.\n{error}")
                return
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self._show_preview_message("Preview is not available for this image.")
            return
        self._preview_pixmap = QPixmap.fromImage(image)
        self._scale_preview()

    def _show_preview_message(self, message: str) -> None:
        self._preview_pixmap = QPixmap()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(message)

    def _scale_preview(self) -> None:
        if self._preview_pixmap.isNull():
            return
        viewport = self.preview_scroll.viewport().size()
        self.preview_label.setText("")
        self.preview_label.setPixmap(
            self._preview_pixmap.scaled(
                max(80, viewport.width() - 20),
                max(80, viewport.height() - 20),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def eventFilter(self, watched, event) -> bool:
        if watched is self.preview_scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._scale_preview()
        return super().eventFilter(watched, event)

    def _accept_selection(self) -> None:
        if self._current_location() is None:
            QMessageBox.information(
                self,
                "Customer folder required",
                "Select a dated customer folder.",
            )
            return
        if self._select_file and not self.selected_files:
            QMessageBox.information(
                self,
                "Images required",
                "Select one or more images to open.",
            )
            return
        self.accept()

    @property
    def location(self) -> tuple[int, str, str]:
        location = self._current_location()
        if location is None:
            raise RuntimeError("No customer folder selected")
        return location

    @property
    def selected_files(self):
        rows = sorted(index.row() for index in self.file_table.selectionModel().selectedRows())
        return [self._files[row] for row in rows if 0 <= row < len(self._files)]


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
        self._selection_rotation = 0.0
        self._image_rotation = 0.0
        self._eraser_drawing = False
        self._eraser_last_point = QPoint()
        self._selection_source = QPixmap()
        self._selection_width = 0
        self._selection_height = 0
        self._selection_centre_x = 0.0
        self._selection_centre_y = 0.0
        self._visible_bounds_cache_key = 0
        self._visible_bounds_cache: QRect | None = None
        self._documents: list[ImageDocument] = []
        self._active_document_index = -1
        self._switching_document = False
        self.setObjectName("imageEditorPage")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(10)

        command_bar = QFrame()
        command_bar.setObjectName("editorCommandBar")
        command_layout = QHBoxLayout(command_bar)
        command_layout.setContentsMargins(12, 8, 12, 8)
        self.open_button = QPushButton("Open")
        self.save_button = QPushButton("Save")
        for button in (
            self.open_button,
            self.save_button,
        ):
            button.setObjectName("secondaryButton")
            command_layout.addWidget(button)
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
            field.setKeyboardTracking(True)
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
        command_layout.addWidget(QLabel("Rotate:"))
        self.rotation_value = QDoubleSpinBox()
        self.rotation_value.setObjectName("imageDimension")
        self.rotation_value.setRange(-180.0, 180.0)
        self.rotation_value.setDecimals(1)
        self.rotation_value.setSuffix("°")
        self.rotation_value.setKeyboardTracking(False)
        self.rotation_value.setMinimumWidth(78)
        self.rotation_value.setEnabled(False)
        command_layout.addWidget(self.rotation_value)
        command_layout.addWidget(QLabel("Resolution:"))
        self.resolution_value = QDoubleSpinBox()
        self.resolution_value.setObjectName("imageDimension")
        self.resolution_value.setRange(1.0, 2400.0)
        self.resolution_value.setDecimals(0)
        self.resolution_value.setSuffix(" dpi")
        self.resolution_value.setKeyboardTracking(False)
        self.resolution_value.setMinimumWidth(92)
        self.resolution_value.setValue(96.0)
        self.resolution_value.setToolTip(
            "DPI changes physical print size and saved metadata, not screen pixels."
        )
        command_layout.addWidget(self.resolution_value)
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

        self.document_tabs = QTabBar()
        self.document_tabs.setObjectName("imageDocumentTabs")
        self.document_tabs.setTabsClosable(True)
        self.document_tabs.setMovable(True)
        self.document_tabs.setExpanding(False)
        self.document_tabs.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.document_tabs.setUsesScrollButtons(True)
        self.document_tabs.setVisible(False)
        self.document_tabs.currentChanged.connect(self._activate_document)
        self.document_tabs.tabCloseRequested.connect(self._close_document)
        self.document_tabs.tabMoved.connect(self._move_document)
        outer_layout.addWidget(self.document_tabs)
        selected_theme = QSettings("KMS", "DTF ERP").value("ui/theme", "dark")
        self.set_theme_progress(0.0 if selected_theme == "dark" else 1.0)

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
            button.clicked.connect(lambda _checked=False, name=tool_name: self._select_tool(name))
            names_layout.addWidget(button)
            self.tool_labels[tool_name] = button
        self.trim_button = QPushButton("TRIM")
        self.trim_button.setObjectName("editorToolName")
        self.trim_button.setToolTip("Trim transparent edge pixels (Ctrl+T)")
        self.trim_button.setMinimumHeight(38)
        self.trim_button.setEnabled(False)
        names_layout.addWidget(self.trim_button)
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
        self.crop_overlay = CropOverlay(self.canvas_workspace)
        self.crop_overlay.installEventFilter(self.canvas_scroll)
        self.selection_overlay = SelectionOverlay(self.canvas_workspace)
        self.selection_overlay.transform_completed = self._selection_transform_completed
        self.selection_overlay.aspect_locked = self.aspect_lock_button.isChecked
        self.selection_overlay.installEventFilter(self.canvas_scroll)
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

        history_bar = QFrame()
        history_bar.setObjectName("editorHistoryBar")
        history_layout = QHBoxLayout(history_bar)
        history_layout.setContentsMargins(12, 7, 12, 7)
        self.apply_crop_button = QPushButton("Apply Crop")
        self.cancel_crop_button = QPushButton("Cancel")
        self.apply_crop_button.setObjectName("primaryButton")
        self.cancel_crop_button.setObjectName("secondaryButton")
        self.apply_crop_button.setVisible(False)
        self.cancel_crop_button.setVisible(False)
        history_layout.addWidget(self.apply_crop_button)
        history_layout.addWidget(self.cancel_crop_button)
        self.eraser_controls = QFrame()
        eraser_layout = QHBoxLayout(self.eraser_controls)
        eraser_layout.setContentsMargins(0, 0, 0, 0)
        eraser_layout.addWidget(QLabel("Round Eraser Size:"))
        self.eraser_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.eraser_size_slider.setRange(1, 500)
        self.eraser_size_slider.setValue(30)
        self.eraser_size_slider.setMinimumWidth(180)
        self.eraser_size_value = QSpinBox()
        self.eraser_size_value.setRange(1, 500)
        self.eraser_size_value.setValue(30)
        self.eraser_size_value.setSuffix(" px")
        eraser_layout.addWidget(self.eraser_size_slider)
        eraser_layout.addWidget(self.eraser_size_value)
        self.eraser_controls.setVisible(False)
        history_layout.addWidget(self.eraser_controls)
        self.magic_eraser_controls = QFrame()
        magic_layout = QHBoxLayout(self.magic_eraser_controls)
        magic_layout.setContentsMargins(0, 0, 0, 0)
        magic_layout.addWidget(QLabel("Magic Eraser Tolerance:"))
        self.magic_eraser_tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.magic_eraser_tolerance_slider.setRange(0, 255)
        self.magic_eraser_tolerance_slider.setValue(24)
        self.magic_eraser_tolerance_slider.setMinimumWidth(180)
        self.magic_eraser_tolerance_value = QSpinBox()
        self.magic_eraser_tolerance_value.setRange(0, 255)
        self.magic_eraser_tolerance_value.setValue(24)
        self.magic_eraser_contiguous = QCheckBox("Contiguous")
        self.magic_eraser_contiguous.setChecked(True)
        self.magic_eraser_contiguous.setToolTip(
            "Erase only matching pixels connected to the clicked area"
        )
        magic_layout.addWidget(self.magic_eraser_tolerance_slider)
        magic_layout.addWidget(self.magic_eraser_tolerance_value)
        magic_layout.addWidget(self.magic_eraser_contiguous)
        self.magic_eraser_controls.setVisible(False)
        history_layout.addWidget(self.magic_eraser_controls)
        history_layout.addStretch()
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        for button in (self.undo_button, self.redo_button):
            button.setObjectName("secondaryButton")
            history_layout.addWidget(button)
        outer_layout.addWidget(history_bar)

        self.open_button.setEnabled(customer_service is not None)
        self.save_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_customer_image)
        self.save_button.clicked.connect(self.save_customer_image)
        self.trim_button.clicked.connect(self.trim_transparent_pixels)
        self.apply_crop_button.clicked.connect(self.apply_interactive_crop)
        self.cancel_crop_button.clicked.connect(self.cancel_interactive_crop)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.units_combo.currentIndexChanged.connect(self._update_dimensions)
        self.width_value.editingFinished.connect(lambda: self._resize_from_dimensions("width"))
        self.height_value.editingFinished.connect(lambda: self._resize_from_dimensions("height"))
        self.width_value.valueChanged.connect(
            lambda value: self._preview_linked_dimension("width", value)
        )
        self.height_value.valueChanged.connect(
            lambda value: self._preview_linked_dimension("height", value)
        )
        self.rotation_value.editingFinished.connect(self._rotate_image)
        self.resolution_value.editingFinished.connect(self._change_resolution)
        self.aspect_lock_button.toggled.connect(self._set_aspect_lock)
        self.eraser_size_slider.valueChanged.connect(self.eraser_size_value.setValue)
        self.eraser_size_value.valueChanged.connect(self.eraser_size_slider.setValue)
        self.eraser_size_value.valueChanged.connect(self._update_eraser_cursor)
        self.magic_eraser_tolerance_slider.valueChanged.connect(
            self.magic_eraser_tolerance_value.setValue
        )
        self.magic_eraser_tolerance_value.valueChanged.connect(
            self.magic_eraser_tolerance_slider.setValue
        )
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.open_shortcut = QShortcut(QKeySequence.StandardKey.Open, self)
        self.save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        self.trim_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.crop_shortcut = QShortcut(QKeySequence("C"), self)
        self.select_shortcut = QShortcut(QKeySequence("V"), self)
        self.apply_crop_shortcut = QShortcut(QKeySequence("Return"), self)
        self.apply_crop_numpad_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Enter),
            self,
        )
        self.undo_shortcut.activated.connect(self.undo)
        self.redo_shortcut.activated.connect(self.redo)
        self.open_shortcut.activated.connect(self.open_customer_image)
        self.save_shortcut.activated.connect(self.save_customer_image)
        self.trim_shortcut.activated.connect(self.trim_transparent_pixels)
        self.crop_shortcut.activated.connect(lambda: self._select_tool("Crop"))
        self.select_shortcut.activated.connect(lambda: self._select_tool("Select"))
        self.apply_crop_shortcut.activated.connect(self._finish_current_edit)
        self.apply_crop_numpad_shortcut.activated.connect(self._finish_current_edit)
        self.tool_labels["Crop"].setToolTip("Crop (C)")
        self.tool_labels["Select"].setToolTip("Select and move artwork (V)")
        QApplication.instance().installEventFilter(self)
        self._update_history_actions()

        self.setStyleSheet(
            """
            QFrame#editorCommandBar, QFrame#editorPanel, QFrame#imageEditorCanvas,
            QFrame#editorHistoryBar,
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

    def eventFilter(self, watched, event) -> bool:
        """Activate canvas tools even when a child widget owns keyboard focus."""
        if (
            event.type() == QEvent.Type.KeyPress
            and self.isVisible()
            and QApplication.activeModalWidget() is None
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            if event.key() == Qt.Key.Key_V:
                self._select_tool("Select")
                event.accept()
                return True
            if event.key() == Qt.Key.Key_C:
                self._select_tool("Crop")
                event.accept()
                return True
        if (
            self._active_tool == "Magic Eraser"
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            local = self.canvas_placeholder.mapFromGlobal(event.globalPosition().toPoint())
            if self.canvas_placeholder.rect().contains(local):
                self._push_undo()
                self._magic_erase_at(self._image_point_from_local(local))
                self._image_modified = True
                self._sync_active_document()
                return True
        if self._active_tool == "Eraser" and event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            local = self.canvas_placeholder.mapFromGlobal(event.globalPosition().toPoint())
            inside_image = self.canvas_placeholder.rect().contains(local)
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
                and inside_image
            ):
                self._push_undo()
                self._eraser_drawing = True
                self._eraser_last_point = self._image_point_from_local(local)
                self._erase_segment(self._eraser_last_point, self._eraser_last_point)
                return True
            if event.type() == QEvent.Type.MouseMove and self._eraser_drawing:
                if inside_image:
                    point = self._image_point_from_local(local)
                    self._erase_segment(self._eraser_last_point, point)
                    self._eraser_last_point = point
                return True
            if (
                event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and self._eraser_drawing
            ):
                self._eraser_drawing = False
                self._image_modified = True
                self._update_image_info()
                self._sync_active_document()
                return True
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
            and self.isVisible()
            and QApplication.activeModalWidget() is None
        ):
            global_position = event.globalPosition().toPoint()
            viewport = self.canvas_scroll.viewport()
            viewport_rect = QRect(viewport.mapToGlobal(QPoint()), viewport.size())
            image_rect = QRect(
                self.canvas_placeholder.mapToGlobal(QPoint()),
                self.canvas_placeholder.size(),
            )
            selection_rect = QRect()
            if not self.selection_overlay.isHidden():
                selection_rect = QRect(
                    self.selection_overlay.mapToGlobal(QPoint()),
                    self.selection_overlay.size(),
                )
            if (
                viewport_rect.contains(global_position)
                and not image_rect.contains(global_position)
                and not selection_rect.contains(global_position)
            ):
                self._clear_active_tool()
        return super().eventFilter(watched, event)

    def _image_point_from_local(self, local: QPoint) -> QPoint:
        return QPoint(
            round(local.x() * self._pixmap.width() / max(1, self.canvas_placeholder.width())),
            round(local.y() * self._pixmap.height() / max(1, self.canvas_placeholder.height())),
        )

    def _erase_segment(self, start: QPoint, end: QPoint) -> None:
        if self._pixmap.isNull():
            return
        image = self._pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        pen = QPen(Qt.GlobalColor.transparent, self.eraser_size_value.value())
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self._pixmap = QPixmap.fromImage(image)
        preview = self._pixmap.scaled(
            self.canvas_placeholder.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.canvas_placeholder.setPixmap(preview)

    def _magic_erase_at(self, point: QPoint) -> None:
        """Clear every visible pixel within tolerance of the clicked colour."""
        if self._pixmap.isNull():
            return
        import numpy as np

        image = self._pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        pixels = np.frombuffer(image.bits(), dtype=np.uint8, count=image.sizeInBytes()).reshape(
            image.height(), image.bytesPerLine()
        )
        rgba = pixels[:, : image.width() * 4].reshape(image.height(), image.width(), 4)
        x = max(0, min(point.x(), image.width() - 1))
        y = max(0, min(point.y(), image.height() - 1))
        target = rgba[y, x, :3].astype(np.int16)
        difference = np.abs(rgba[:, :, :3].astype(np.int16) - target)
        tolerance = self.magic_eraser_tolerance_value.value()
        if self.magic_eraser_contiguous.isChecked():
            from PIL import Image, ImageDraw

            pil_image = Image.frombytes(
                "RGBA",
                (image.width(), image.height()),
                bytes(image.bits()),
                "raw",
                "RGBA",
                image.bytesPerLine(),
            )
            clicked = tuple(int(value) for value in rgba[y, x])
            ImageDraw.floodfill(
                pil_image,
                (x, y),
                (clicked[0], clicked[1], clicked[2], 0),
                thresh=tolerance,
            )
            data = pil_image.tobytes()
            image = QImage(
                data,
                image.width(),
                image.height(),
                image.width() * 4,
                QImage.Format.Format_RGBA8888,
            ).copy()
        else:
            mask = (difference.max(axis=2) <= tolerance) & (rgba[:, :, 3] > 0)
            rgba[mask, 3] = 0
        self._pixmap = QPixmap.fromImage(image)
        self.set_zoom(self._zoom, smooth=False)

    def _update_eraser_cursor(self) -> None:
        if not hasattr(self, "canvas_placeholder") or self._active_tool != "Eraser":
            return
        diameter = max(7, min(96, round(self.eraser_size_value.value() * self._zoom)))
        cursor_pixmap = QPixmap(diameter + 4, diameter + 4)
        cursor_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, diameter - 1, diameter - 1)
        painter.end()
        centre = cursor_pixmap.width() // 2
        self.canvas_placeholder.setCursor(QCursor(cursor_pixmap, centre, centre))

    def _clear_active_tool(self) -> None:
        """Deselect every tool when the user clicks the empty pasteboard."""
        self.cancel_interactive_crop()
        self.cancel_selection()
        self._eraser_drawing = False
        self.eraser_controls.setVisible(False)
        self.magic_eraser_controls.setVisible(False)
        self.canvas_placeholder.unsetCursor()
        self._active_tool = ""
        for button in self.tool_labels.values():
            button.setChecked(False)
            button.setProperty("active", False)
            button.style().unpolish(button)
            button.style().polish(button)

    def set_theme_progress(self, progress: float) -> None:
        """Apply the application dark/light transition to document tabs."""

        def mix(dark: str, light: str) -> str:
            dark_color = QColor(dark)
            light_color = QColor(light)
            return QColor(
                round(dark_color.red() + (light_color.red() - dark_color.red()) * progress),
                round(dark_color.green() + (light_color.green() - dark_color.green()) * progress),
                round(dark_color.blue() + (light_color.blue() - dark_color.blue()) * progress),
            ).name()

        bar = mix("#2F3136", "#E8EEF8")
        tab = mix("#3A3D43", "#DCE6F5")
        selected = mix("#50535A", "#FFFFFF")
        border = mix("#50535A", "#B8C7DE")
        text = mix("#C7CBD3", "#52617A")
        selected_text = mix("#FFFFFF", "#1D2B4C")
        self.document_tabs.setStyleSheet(
            f"""
            QTabBar {{
                background: {bar};
                border: 1px solid {border};
                border-radius: 7px;
            }}
            QTabBar::tab {{
                color: {text};
                background: {tab};
                border-right: 1px solid {border};
                min-width: 150px;
                max-width: 260px;
                padding: 9px 28px 9px 12px;
            }}
            QTabBar::tab:selected {{
                color: {selected_text};
                background: {selected};
                border-bottom: 2px solid #32C5FF;
            }}
            QTabBar::close-button {{
                subcontrol-position: right;
            }}
            """
        )

    def _sync_active_document(self) -> None:
        if self._switching_document:
            return
        if not 0 <= self._active_document_index < len(self._documents):
            return
        document = self._documents[self._active_document_index]
        document.path = self._image_path
        document.pixmap = self._pixmap
        document.source_file_id = self._source_file_id
        document.dpi_x = self._dpi_x
        document.dpi_y = self._dpi_y
        document.modified = self._image_modified
        document.zoom = self._zoom
        document.rotation = self._image_rotation
        self._update_document_tab(self._active_document_index)

    def _update_document_tab(self, index: int) -> None:
        if not 0 <= index < len(self._documents):
            return
        document = self._documents[index]
        modified = " *" if document.modified else ""
        zoom_value = document.zoom * 100
        zoom = f"{zoom_value:.1f}" if zoom_value < 1 else str(round(zoom_value))
        self.document_tabs.setTabText(
            index,
            f"{document.path.name}{modified} @ {zoom}%",
        )
        self.document_tabs.setTabToolTip(index, str(document.path))

    def _activate_document(self, index: int) -> None:
        if self._switching_document or not 0 <= index < len(self._documents):
            return
        self.cancel_interactive_crop()
        self.cancel_selection()
        self._sync_active_document()
        self._active_document_index = index
        document = self._documents[index]
        self._switching_document = True
        self._image_path = document.path
        self._source_file_id = document.source_file_id
        self._pixmap = document.pixmap
        self._dpi_x = document.dpi_x
        self._dpi_y = document.dpi_y
        self._image_modified = document.modified
        self._image_rotation = document.rotation
        with QSignalBlocker(self.rotation_value):
            self.rotation_value.setValue(self._image_rotation)
        self.canvas_placeholder.setText("")
        self.set_zoom(document.zoom)
        viewport = self.canvas_scroll.viewport().size()
        self.canvas_workspace.resize(
            max(viewport.width() * 3, self._pixmap.width() + viewport.width() * 2),
            max(viewport.height() * 3, self._pixmap.height() + viewport.height() * 2),
        )
        scaled_size = self.canvas_placeholder.size()
        self.canvas_placeholder.move(
            (self.canvas_workspace.width() - scaled_size.width()) // 2,
            (self.canvas_workspace.height() - scaled_size.height()) // 2,
        )
        self.canvas_scroll.horizontalScrollBar().setValue(
            self.canvas_placeholder.x() - ((viewport.width() - scaled_size.width()) // 2)
        )
        self.canvas_scroll.verticalScrollBar().setValue(
            self.canvas_placeholder.y() - ((viewport.height() - scaled_size.height()) // 2)
        )
        self._update_dimensions()
        self.save_button.setEnabled(self._customer_service is not None)
        self.trim_button.setEnabled(True)
        self.rotation_value.setEnabled(True)
        self._switching_document = False
        self._update_history_actions()

    def _close_document(self, index: int) -> None:
        if not 0 <= index < len(self._documents):
            return
        active_document = (
            self._documents[self._active_document_index]
            if 0 <= self._active_document_index < len(self._documents)
            else None
        )
        if index == self._active_document_index:
            self._sync_active_document()
        with QSignalBlocker(self.document_tabs):
            self.document_tabs.removeTab(index)
        self._documents.pop(index)
        if not self._documents:
            self._active_document_index = -1
            self._image_path = None
            self._source_file_id = None
            self._pixmap = QPixmap()
            self.canvas_placeholder.clear()
            self.canvas_placeholder.setText("CANVAS")
            self.canvas_placeholder.setMinimumSize(400, 300)
            self.image_info.setText("No image loaded")
            self.zoom_percentage.setText("100%")
            self.document_tabs.setVisible(False)
            self.save_button.setEnabled(False)
            self.trim_button.setEnabled(False)
            self.rotation_value.setEnabled(False)
            self._image_rotation = 0.0
            with QSignalBlocker(self.rotation_value):
                self.rotation_value.setValue(0.0)
            self._update_dimensions()
            self._update_history_actions()
            return
        next_index = next(
            (
                document_index
                for document_index, document in enumerate(self._documents)
                if document is active_document
            ),
            min(index, len(self._documents) - 1),
        )
        self._active_document_index = -1
        with QSignalBlocker(self.document_tabs):
            self.document_tabs.setCurrentIndex(next_index)
        self._activate_document(next_index)

    def _move_document(self, from_index: int, to_index: int) -> None:
        if from_index == to_index:
            return
        document = self._documents.pop(from_index)
        self._documents.insert(to_index, document)
        if self._active_document_index == from_index:
            self._active_document_index = to_index
        elif from_index < self._active_document_index <= to_index:
            self._active_document_index -= 1
        elif to_index <= self._active_document_index < from_index:
            self._active_document_index += 1

    def _current_document(self) -> ImageDocument | None:
        if 0 <= self._active_document_index < len(self._documents):
            return self._documents[self._active_document_index]
        return None

    def _push_undo(self) -> None:
        document = self._current_document()
        if document is None or self._pixmap.isNull():
            return
        # QPixmap is implicitly shared. This snapshot is constant-time until either
        # copy is modified, unlike copy(), which duplicates every high-resolution pixel.
        document.undo_stack.append(
            (QPixmap(self._pixmap), self._image_modified, self._image_rotation)
        )
        if len(document.undo_stack) > 50:
            document.undo_stack.pop(0)
        document.redo_stack.clear()
        self._update_history_actions()

    def _restore_history(self, snapshot: tuple[QPixmap, bool, float]) -> None:
        self._pixmap, self._image_modified, self._image_rotation = snapshot
        with QSignalBlocker(self.rotation_value):
            self.rotation_value.setValue(self._image_rotation)
        self.set_zoom(self._zoom)
        self._update_dimensions()
        self._sync_active_document()
        self._update_history_actions()

    def undo(self) -> None:
        document = self._current_document()
        if document is None or not document.undo_stack:
            return
        document.redo_stack.append(
            (QPixmap(self._pixmap), self._image_modified, self._image_rotation)
        )
        self._restore_history(document.undo_stack.pop())

    def redo(self) -> None:
        document = self._current_document()
        if document is None or not document.redo_stack:
            return
        document.undo_stack.append(
            (QPixmap(self._pixmap), self._image_modified, self._image_rotation)
        )
        self._restore_history(document.redo_stack.pop())

    def _update_history_actions(self) -> None:
        document = self._current_document()
        self.undo_button.setEnabled(bool(document and document.undo_stack))
        self.redo_button.setEnabled(bool(document and document.redo_stack))
        self.undo_button.setToolTip("Undo (Ctrl+Z)")
        self.redo_button.setToolTip("Redo (Ctrl+Shift+Z)")

    def _select_tool(self, selected_name: str) -> None:
        if selected_name != "Crop":
            self.cancel_interactive_crop()
        if selected_name != "Select":
            self.cancel_selection()
        self._active_tool = selected_name
        self.eraser_controls.setVisible(selected_name == "Eraser")
        self.magic_eraser_controls.setVisible(selected_name == "Magic Eraser")
        if selected_name != "Eraser":
            self.canvas_placeholder.unsetCursor()
        if selected_name == "Magic Eraser":
            self.canvas_placeholder.setCursor(Qt.CursorShape.CrossCursor)
        for tool_name, button in self.tool_labels.items():
            active = tool_name == selected_name
            button.setChecked(active)
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
        if selected_name == "Crop":
            self.start_interactive_crop()
        elif selected_name == "Select":
            self.start_selection()
        elif selected_name == "Eraser":
            self._update_eraser_cursor()
        self.width_value.setToolTip("Image width")
        self.height_value.setToolTip("Image height")

    def set_zoom(self, zoom: float, *, smooth: bool = True) -> None:
        if self._pixmap.isNull():
            return
        crop_active = not self.crop_overlay.isHidden()
        selection_active = not self.selection_overlay.isHidden()
        old_image_geometry = QRectF(self.canvas_placeholder.geometry())
        old_crop = QRectF(self.crop_overlay.crop_rect)
        relative_crop = None
        if crop_active and old_image_geometry.width() > 0 and old_image_geometry.height() > 0:
            relative_crop = QRectF(
                (old_crop.left() - old_image_geometry.left()) / old_image_geometry.width(),
                (old_crop.top() - old_image_geometry.top()) / old_image_geometry.height(),
                old_crop.width() / old_image_geometry.width(),
                old_crop.height() / old_image_geometry.height(),
            )
        self._zoom = max(0.005, min(8.0, zoom))
        size = self._pixmap.size() * self._zoom
        size = QSize(max(1, size.width()), max(1, size.height()))
        scaled = self._pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            (
                Qt.TransformationMode.SmoothTransformation
                if smooth
                else Qt.TransformationMode.FastTransformation
            ),
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
        if crop_active:
            self.crop_overlay.setGeometry(self.canvas_workspace.rect())
            if relative_crop is not None:
                image_geometry = QRectF(self.canvas_placeholder.geometry())
                self.crop_overlay.crop_rect = QRectF(
                    image_geometry.left() + relative_crop.left() * image_geometry.width(),
                    image_geometry.top() + relative_crop.top() * image_geometry.height(),
                    relative_crop.width() * image_geometry.width(),
                    relative_crop.height() * image_geometry.height(),
                )
            self.crop_overlay.raise_()
            self.crop_overlay.update()
        if selection_active:
            self._position_selection_overlay()
        self._update_image_info()
        zoom_value = self._zoom * 100
        zoom_text = f"{zoom_value:.1f}" if zoom_value < 1 else str(round(zoom_value))
        self.zoom_percentage.setText(f"{zoom_text}%")
        self._update_eraser_cursor()
        self._sync_active_document()

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

    def _visible_pixel_bounds(self) -> QRect | None:
        if self._pixmap.isNull():
            return None
        cache_key = self._pixmap.cacheKey()
        if cache_key == self._visible_bounds_cache_key:
            return (
                QRect(self._visible_bounds_cache)
                if self._visible_bounds_cache is not None
                else None
            )
        import numpy as np

        image = self._pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        pixels = np.frombuffer(
            image.constBits(),
            dtype=np.uint8,
            count=image.sizeInBytes(),
        ).reshape(image.height(), image.bytesPerLine())
        alpha = pixels[:, 3 : image.width() * 4 : 4]
        visible_y, visible_x = np.nonzero(alpha)
        if not len(visible_x):
            self._visible_bounds_cache_key = cache_key
            self._visible_bounds_cache = None
            return None
        left = int(visible_x.min())
        top = int(visible_y.min())
        bounds = QRect(
            left,
            top,
            int(visible_x.max()) - left + 1,
            int(visible_y.max()) - top + 1,
        )
        self._visible_bounds_cache_key = cache_key
        self._visible_bounds_cache = QRect(bounds)
        return bounds

    def _position_selection_overlay(self) -> None:
        bounds = self._visible_pixel_bounds()
        if bounds is None:
            self.selection_overlay.hide()
            return
        image_geometry = self.canvas_placeholder.geometry()
        scale_x = image_geometry.width() / self._pixmap.width()
        scale_y = image_geometry.height() / self._pixmap.height()
        if not self._selection_source.isNull() and self._selection_width > 0:
            width = max(8, round(self._selection_width * scale_x))
            height = max(8, round(self._selection_height * scale_y))
            centre_x = image_geometry.x() + self._selection_centre_x * scale_x
            centre_y = image_geometry.y() + self._selection_centre_y * scale_y
            geometry = QRect(
                round(centre_x - width / 2),
                round(centre_y - height / 2),
                width,
                height,
            )
        else:
            geometry = QRect(
                round(image_geometry.x() + bounds.x() * scale_x),
                round(image_geometry.y() + bounds.y() * scale_y),
                max(8, round(bounds.width() * scale_x)),
                max(8, round(bounds.height() * scale_y)),
            )
        # A transformed layer may extend beyond the document canvas. Keeping its
        # true rectangle on the pasteboard prevents full-canvas artwork from locking.
        self.selection_overlay.begin(geometry, self.canvas_workspace.rect())

    def start_selection(self) -> None:
        bounds = self._visible_pixel_bounds()
        if self._pixmap.isNull() or bounds is None:
            return
        # Keep one pristine source for the whole Select session. Every resize is
        # rendered from this source, so shrinking and enlarging never compounds blur.
        self._selection_source = self._pixmap.copy(bounds)
        self._selection_width = bounds.width()
        self._selection_height = bounds.height()
        self._selection_centre_x = bounds.x() + bounds.width() / 2
        self._selection_centre_y = bounds.y() + bounds.height() / 2
        self._selection_rotation = 0.0
        self._position_selection_overlay()
        self._update_dimensions()

    def cancel_selection(self) -> None:
        if not hasattr(self, "selection_overlay"):
            return
        self.selection_overlay.hide()
        self._selection_source = QPixmap()

    def _transform_selected_artwork(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        rotation_delta: float = 0.0,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        bounds = self._visible_pixel_bounds()
        if bounds is None or self._selection_source.isNull():
            return
        target_width = max(1, width or self._selection_width)
        target_height = max(1, height or self._selection_height)
        self._selection_width = target_width
        self._selection_height = target_height
        self._selection_rotation += rotation_delta
        self._selection_centre_x += offset_x
        self._selection_centre_y += offset_y
        source = self._selection_source.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if self._selection_rotation:
            source = source.transformed(
                QTransform().rotate(self._selection_rotation),
                Qt.TransformationMode.SmoothTransformation,
            )
        destination_x = round(self._selection_centre_x - source.width() / 2)
        destination_y = round(self._selection_centre_y - source.height() / 2)
        self._push_undo()
        canvas = QPixmap(self._pixmap.size())
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(destination_x, destination_y, source)
        painter.end()
        self._pixmap = canvas
        self._image_modified = True
        self.set_zoom(self._zoom, smooth=False)
        self._update_dimensions()

    def _move_selected_artwork(self, display_delta: QPoint) -> None:
        if self._zoom <= 0:
            return
        self._transform_selected_artwork(
            offset_x=round(display_delta.x() / self._zoom),
            offset_y=round(display_delta.y() / self._zoom),
        )

    def _selection_transform_completed(self, start: QRect, end: QRect, mode: str = "") -> None:
        """Commit a cheap overlay preview as one pixel transformation."""
        image_geometry = self.canvas_placeholder.geometry()
        if self._pixmap.isNull() or image_geometry.width() <= 0 or image_geometry.height() <= 0:
            return
        scale_x = image_geometry.width() / self._pixmap.width()
        scale_y = image_geometry.height() / self._pixmap.height()
        target_width = max(1, round(end.width() / scale_x))
        target_height = max(1, round(end.height() / scale_y))
        if "_" in mode and self.aspect_lock_button.isChecked():
            aspect = self._selection_width / max(1, self._selection_height)
            width_change = abs(target_width - self._selection_width) / max(1, self._selection_width)
            height_change = abs(target_height - self._selection_height) / max(
                1, self._selection_height
            )
            if width_change >= height_change:
                target_height = max(1, round(target_width / aspect))
            else:
                target_width = max(1, round(target_height * aspect))
        offset_x = round((end.center().x() - start.center().x()) / scale_x)
        offset_y = round((end.center().y() - start.center().y()) / scale_y)
        self._transform_selected_artwork(
            width=target_width,
            height=target_height,
            offset_x=offset_x,
            offset_y=offset_y,
        )

    def _rotate_image(self) -> None:
        """Rotate the complete image; the top bar never targets Select artwork."""
        if self._pixmap.isNull():
            return
        requested = self.rotation_value.value()
        delta = requested - self._image_rotation
        if abs(delta) < 0.01:
            return
        self.cancel_selection()
        self._push_undo()
        self._pixmap = self._pixmap.transformed(
            QTransform().rotate(delta),
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_rotation = requested
        self._image_modified = True
        self.set_zoom(self._zoom)
        self._update_dimensions()
        self._sync_active_document()

    def _update_dimensions(self) -> None:
        if self._pixmap.isNull():
            self.width_value.setValue(0)
            self.height_value.setValue(0)
            return
        pixel_width = self._pixmap.width()
        pixel_height = self._pixmap.height()
        unit = self.units_combo.currentData()
        if unit == "px":
            width = float(pixel_width)
            height = float(pixel_height)
            decimals = 0
        else:
            width_inches = pixel_width / self._dpi_x
            height_inches = pixel_height / self._dpi_y
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
        with QSignalBlocker(self.resolution_value):
            self.resolution_value.setValue((self._dpi_x + self._dpi_y) / 2)

    def _change_resolution(self) -> None:
        """Change print-resolution metadata without resampling image pixels."""
        if self._pixmap.isNull():
            return
        resolution = self.resolution_value.value()
        self._dpi_x = resolution
        self._dpi_y = resolution
        self._image_modified = True
        self._update_dimensions()
        self._update_image_info()
        self._sync_active_document()

    def _preview_linked_dimension(self, changed: str, value: float) -> None:
        """Update the locked partner field live, then resample once on commit."""
        if self._pixmap.isNull() or not self.aspect_lock_button.isChecked():
            return
        aspect = self._pixmap.width() / max(1, self._pixmap.height())
        target = self.height_value if changed == "width" else self.width_value
        linked_value = value / aspect if changed == "width" else value * aspect
        with QSignalBlocker(target):
            target.setValue(linked_value)

    def _update_image_info(self) -> None:
        """Expose both pixel and physical size so DPI changes are verifiable."""
        if self._pixmap.isNull() or self._image_path is None:
            self.image_info.setText("No image loaded")
            return
        print_width = self._pixmap.width() / max(1.0, self._dpi_x)
        print_height = self._pixmap.height() / max(1.0, self._dpi_y)
        dpi = (self._dpi_x + self._dpi_y) / 2
        self.image_info.setText(
            f"{self._image_path.name}  •  {self._pixmap.width()} × "
            f"{self._pixmap.height()} px  •  Print {print_width:.2f} × "
            f"{print_height:.2f} in @ {dpi:.0f} DPI"
        )

    def _finish_current_edit(self) -> None:
        """Commit the active editor operation for Return and numpad Enter."""
        if not self.crop_overlay.isHidden():
            self.apply_interactive_crop()
        else:
            focused = QApplication.focusWidget()
            editor = focused
            while editor is not None and editor not in (
                self.width_value,
                self.height_value,
                self.rotation_value,
                self.resolution_value,
            ):
                editor = editor.parentWidget()
            if editor is self.width_value:
                self._resize_from_dimensions("width")
            elif editor is self.height_value:
                self._resize_from_dimensions("height")
            elif editor is self.rotation_value:
                self._rotate_image()
            elif editor is self.resolution_value:
                self._change_resolution()
            if self._active_tool == "Select" and not self.selection_overlay.isHidden():
                self.cancel_selection()

        focused = QApplication.focusWidget()
        if focused is not None:
            blockers = [QSignalBlocker(focused)]
            parent = focused.parentWidget()
            if parent is not None:
                blockers.append(QSignalBlocker(parent))
            with blockers[0]:
                focused.clearFocus()
        self.canvas_scroll.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _set_aspect_lock(self, locked: bool) -> None:
        self.aspect_lock_button.setText("🔒" if locked else "🔓")
        self.aspect_lock_button.setToolTip("Unlock aspect ratio" if locked else "Lock aspect ratio")

    def _resize_from_dimensions(self, changed_dimension: str | None = None) -> None:
        if self._pixmap.isNull():
            return
        if not self.crop_overlay.isHidden():
            self.cancel_interactive_crop()
        self.cancel_selection()
        base_width = self._pixmap.width()
        base_height = self._pixmap.height()
        aspect_ratio = base_width / base_height
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
        if width_pixels == base_width and height_pixels == base_height:
            return
        self._push_undo()
        # Top-bar dimensions always resize the complete image. Canvas extension
        # belongs exclusively to the interactive Crop overlay, never to these fields.
        self._pixmap = self._pixmap.scaled(
            width_pixels,
            height_pixels,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_modified = True
        self.set_zoom(self._zoom)
        self._update_dimensions()

    def start_interactive_crop(self) -> None:
        if self._pixmap.isNull():
            return
        self.crop_overlay.begin(self.canvas_placeholder.geometry())
        self.apply_crop_button.setVisible(True)
        self.cancel_crop_button.setVisible(True)

    def cancel_interactive_crop(self) -> None:
        if not hasattr(self, "crop_overlay"):
            return
        self.crop_overlay.hide()
        self.apply_crop_button.setVisible(False)
        self.cancel_crop_button.setVisible(False)

    def apply_interactive_crop(self) -> None:
        if self._pixmap.isNull() or self.crop_overlay.isHidden():
            return
        crop = QRectF(self.crop_overlay.crop_rect)
        image = QRectF(self.canvas_placeholder.geometry())
        if crop.width() < 1 or crop.height() < 1 or image.width() < 1 or image.height() < 1:
            return
        scale_x = self._pixmap.width() / image.width()
        scale_y = self._pixmap.height() / image.height()
        target_width = max(1, round(crop.width() * scale_x))
        target_height = max(1, round(crop.height() * scale_y))
        offset_x = round((image.left() - crop.left()) * scale_x)
        offset_y = round((image.top() - crop.top()) * scale_y)
        self._push_undo()
        canvas = QPixmap(target_width, target_height)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(offset_x, offset_y, self._pixmap)
        painter.end()
        self.cancel_interactive_crop()
        self._pixmap = canvas
        self._image_modified = True
        self.set_zoom(self._zoom)
        self._update_dimensions()

    def trim_transparent_pixels(self) -> None:
        if self._pixmap.isNull():
            return
        import numpy as np

        image = self._pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
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
        self._push_undo()
        self._pixmap = QPixmap.fromImage(image.copy(QRect(left, top, width, height)))
        self._image_modified = True
        self.set_zoom(self._zoom)
        self._update_dimensions()

    def _edited_source(self) -> Path:
        if not self._image_modified or self._image_path is None:
            return self._image_path
        output_directory = Path(gettempdir()) / "kms_dtf_erp_image_editor_edits"
        output_directory.mkdir(parents=True, exist_ok=True)
        output = output_directory / (f"{self._active_document_index}-{self._image_path.name}")
        image = self._pixmap.toImage()
        image.setDotsPerMeterX(round(self._dpi_x / 0.0254))
        image.setDotsPerMeterY(round(self._dpi_y / 0.0254))
        if not image.save(str(output)):
            raise RuntimeError("The resized image could not be encoded")
        return output

    def fit_to_canvas(self) -> None:
        if self._pixmap.isNull():
            return
        self.set_zoom(self._fit_zoom_for_pixmap(self._pixmap))

    def _fit_zoom_for_pixmap(self, pixmap: QPixmap) -> float:
        """Fit an image into the viewport without enlarging it above 100%."""

        available = self.canvas_scroll.viewport().size()
        width = max(1, available.width() - 40)
        height = max(1, available.height() - 40)
        return min(
            1.0,
            width / pixmap.width(),
            height / pixmap.height(),
        )

    def open_customer_image(self) -> None:
        if self._customer_service is None:
            return
        dialog = CustomerImageDialog(self._customer_service, self, select_file=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for record in dialog.selected_files:
            path = Path(record.local_path)
            if not path.is_file():
                cache = Path(gettempdir()) / "kms_dtf_erp_image_editor"
                cache.mkdir(parents=True, exist_ok=True)
                path = cache / f"{record.id}{Path(record.original_name).suffix.casefold()}"
                try:
                    self._customer_service.download_customer_file(record.id, path)
                except Exception as error:
                    QMessageBox.warning(
                        self,
                        f"{record.original_name} unavailable",
                        str(error),
                    )
                    continue
            self.load_image(path, source_file_id=record.id)

    def load_image(self, path: Path, *, source_file_id: int | None = None) -> bool:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, "Image not opened", reader.errorString())
            return False
        dots_per_metre_x = image.dotsPerMeterX()
        dots_per_metre_y = image.dotsPerMeterY()
        document = ImageDocument(
            path=path,
            pixmap=QPixmap.fromImage(image),
            source_file_id=source_file_id,
            dpi_x=dots_per_metre_x * 0.0254 if dots_per_metre_x > 0 else 96.0,
            dpi_y=dots_per_metre_y * 0.0254 if dots_per_metre_y > 0 else 96.0,
        )
        document.zoom = self._fit_zoom_for_pixmap(document.pixmap)
        self._sync_active_document()
        self._documents.append(document)
        index = len(self._documents) - 1
        with QSignalBlocker(self.document_tabs):
            self.document_tabs.addTab(path.name)
            self.document_tabs.setCurrentIndex(index)
        self.document_tabs.setVisible(True)
        self._update_document_tab(index)
        self._activate_document(index)
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
            self._image_modified = False
            self._sync_active_document()
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
        self._image_modified = False
        self._sync_active_document()
        QMessageBox.information(
            self,
            "Image saved",
            "The original-quality image was queued in the selected customer folder.",
        )
