"""Order intake, customer information, details, and status timeline UI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QIcon, QInputDevice, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.customers import CustomerService, CustomerStorageDateExistsError
from app.modules.orders import (
    ORDER_STATUSES,
    ORDER_TYPES,
    OrderDetails,
    OrderInput,
    OrderService,
)
from app.modules.products import ProductService
from app.ui.pages.customers import CustomerFormDialog

QUICK_ORDER_STATUSES = ("Designing", "Printing", "Completed")


class TransparentDesignPreview(QGraphicsView):
    """Interactive alpha-aware preview with mouse and touchpad navigation."""

    def __init__(self, source: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.source = source
        self.original = QPixmap(str(source))
        self.setMinimumSize(640, 460)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._user_interacted = False
        self._relative_zoom = 1.0
        self._middle_panning = False
        self._last_pan_position = QPoint()
        checkerboard = QPixmap(32, 32)
        painter = QPainter(checkerboard)
        painter.fillRect(0, 0, 32, 32, QColor("#FFFFFF"))
        painter.fillRect(0, 0, 16, 16, QColor("#D8D8D8"))
        painter.fillRect(16, 16, 16, 16, QColor("#D8D8D8"))
        painter.end()
        self.setBackgroundBrush(QBrush(checkerboard))
        self.preview_scene = QGraphicsScene(self)
        self.setScene(self.preview_scene)
        if self.original.isNull():
            self.image_item = None
            self.preview_scene.addText(f"Large preview is unavailable for {source.name}")
        else:
            self.image_item = self.preview_scene.addPixmap(self.original)
            self.preview_scene.setSceneRect(self.image_item.boundingRect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.image_item is not None and not self._user_interacted:
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._relative_zoom = 1.0

    def wheelEvent(self, event) -> None:
        device_type = event.device().type() if event.device() is not None else None
        touchpad_pan = (
            device_type == QInputDevice.DeviceType.TouchPad
            and not event.modifiers() & Qt.KeyboardModifier.ControlModifier
        )
        if touchpad_pan:
            delta = event.pixelDelta()
            if delta.isNull():
                angle = event.angleDelta()
                delta = QPoint(angle.x() // 2, angle.y() // 2)
            self._pan_by(delta)
        else:
            amount = event.angleDelta().y() or event.pixelDelta().y()
            self._apply_zoom(1.18 if amount > 0 else 1 / 1.18)
        event.accept()

    def viewportEvent(self, event) -> bool:
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                self._apply_zoom(max(0.2, 1.0 + event.value()))
                event.accept()
                return True
            if event.gestureType() == Qt.NativeGestureType.PanNativeGesture:
                self._pan_by(event.delta())
                event.accept()
                return True
        return super().viewportEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_panning = True
            self._last_pan_position = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._middle_panning:
            position = event.position().toPoint()
            self._pan_by(position - self._last_pan_position)
            self._last_pan_position = position
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._middle_panning:
            self._middle_panning = False
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_zoom(self, factor: float) -> None:
        target_zoom = self._relative_zoom * factor
        if 0.03 <= target_zoom <= 30:
            self._user_interacted = True
            self._relative_zoom = target_zoom
            self.scale(factor, factor)

    def _pan_by(self, delta: QPoint) -> None:
        self._user_interacted = True
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - round(delta.x())
        )
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - round(delta.y())
        )


class DesignPreviewDialog(QDialog):
    def __init__(self, source: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Design preview — {source.name}")
        self.resize(1000, 760)
        layout = QVBoxLayout(self)
        filename = QLabel(source.name)
        filename.setObjectName("sectionTitle")
        filename.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(filename)
        instructions = QLabel(
            "Mouse wheel or touchpad pinch: zoom  •  Drag or press the mouse wheel: pan  •  "
            "Touchpad scroll/pan gestures: pan"
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setObjectName("cardBody")
        layout.addWidget(instructions)
        self.image_preview = TransparentDesignPreview(source, self)
        layout.addWidget(self.image_preview, 1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)


class OrderCreationDialog(QDialog):
    def __init__(
        self,
        customer_service: CustomerService,
        product_service: ProductService | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        del product_service
        self.customer_service = customer_service
        self._staged_designs: list[Path] = []
        self.setWindowTitle("New order")
        self.resize(720, 650)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.customer = QComboBox()
        self.add_customer_button = QPushButton("Add new customer")
        self.add_customer_button.setObjectName("secondaryButton")
        self.add_customer_button.clicked.connect(self._add_customer)
        customer_row = QWidget()
        customer_layout = QHBoxLayout(customer_row)
        customer_layout.setContentsMargins(0, 0, 0, 0)
        customer_layout.addWidget(self.customer, 1)
        customer_layout.addWidget(self.add_customer_button)

        self.order_type = QComboBox()
        self.order_type.addItems(ORDER_TYPES)
        self.order_type.installEventFilter(self)
        self.import_design_button = QPushButton("Import design")
        self.import_design_button.setObjectName("secondaryButton")
        self.import_design_button.clicked.connect(self._import_designs)
        self.import_design_status = QLabel("Select a customer before importing designs")
        self.import_design_status.setWordWrap(True)
        self.design_preview = QListWidget()
        self.design_preview.setObjectName("orderDesignPreview")
        self.design_preview.setViewMode(QListView.ViewMode.IconMode)
        self.design_preview.setResizeMode(QListView.ResizeMode.Adjust)
        self.design_preview.setMovement(QListView.Movement.Static)
        self.design_preview.setIconSize(QSize(150, 110))
        self.design_preview.setGridSize(QSize(220, 225))
        self.design_preview.setSpacing(10)
        self.design_preview.setMinimumHeight(260)
        self.design_preview.itemDoubleClicked.connect(self._open_design_preview)
        self._reload_customers()

        form.addRow("Customer", customer_row)
        form.addRow("Product type", self.order_type)
        form.addRow("Customer design", self.import_design_button)
        layout.addLayout(form)
        layout.addWidget(self.import_design_status)
        preview_title = QLabel("Uploaded design previews")
        preview_title.setObjectName("sectionTitle")
        layout.addWidget(preview_title)
        layout.addWidget(self.design_preview, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reload_customers(self, selected_customer_id: int | None = None) -> None:
        self.customer.clear()
        self.customer.addItem("Select customer", None)
        for customer in self.customer_service.list_customers():
            self.customer.addItem(customer.display_identifier, customer.id)
        if selected_customer_id is not None:
            selected_index = self.customer.findData(selected_customer_id)
            if selected_index >= 0:
                self.customer.setCurrentIndex(selected_index)

    def _add_customer(self) -> None:
        created_customer = None

        def save_customer(customer_input):
            nonlocal created_customer
            created_customer = self.customer_service.create_customer(customer_input)
            return created_customer

        dialog = CustomerFormDialog(parent=self)
        dialog.set_save_operation(save_customer)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected_id = created_customer.summary.id if created_customer is not None else None
        self._reload_customers(selected_id)

    def _import_designs(self) -> None:
        customer_id = self.customer.currentData()
        if customer_id is None:
            QMessageBox.warning(self, "Select customer", "Select a customer before importing.")
            return
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Import customer designs",
            "",
            "Design files (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.pdf *.svg "
            "*.ai *.eps *.cdr);;All files (*.*)",
        )
        if not filenames:
            return
        for filename in filenames:
            source = Path(filename)
            if source not in self._staged_designs:
                self._add_design_preview(source)
        self.import_design_status.setText(
            f"{len(self._staged_designs)} design(s) ready — files upload when you click Save"
        )

    def _add_design_preview(self, source: Path) -> None:
        pixmap = QPixmap(str(source))
        item = QListWidgetItem(source.name)
        if not pixmap.isNull():
            item.setIcon(QIcon(pixmap))
        item.setToolTip(str(source))
        item.setData(Qt.ItemDataRole.UserRole, str(source))
        item.setSizeHint(QSize(210, 215))
        self.design_preview.addItem(item)
        self._staged_designs.append(source)
        tile = QFrame()
        tile.setObjectName("orderDesignTile")
        tile.setProperty("previewSource", str(source))
        tile.installEventFilter(self)
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(7, 5, 7, 7)
        tile_layout.setSpacing(5)
        remove_row = QHBoxLayout()
        remove_row.setContentsMargins(0, 0, 0, 0)
        remove_row.addStretch()
        remove_button = QPushButton("×")
        remove_button.setObjectName("dangerButton")
        remove_button.setToolTip(f"Remove {source.name} from this order")
        remove_button.setFixedSize(26, 26)
        remove_button.setStyleSheet(
            "QPushButton { color: white; background: #D64545; border: 0; "
            "border-radius: 13px; font: 700 16px 'Segoe UI'; padding: 0; } "
            "QPushButton:hover { background: #B92F2F; }"
        )
        remove_button.clicked.connect(lambda: self._remove_design_preview(item))
        remove_row.addWidget(remove_button)
        tile_layout.addLayout(remove_row)
        thumbnail = QLabel()
        thumbnail.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail.setFixedSize(190, 130)
        if pixmap.isNull():
            thumbnail.setText(source.suffix.removeprefix(".").upper() or "FILE")
        else:
            thumbnail.setPixmap(
                pixmap.scaled(
                    thumbnail.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        tile_layout.addWidget(thumbnail, alignment=Qt.AlignmentFlag.AlignHCenter)
        name = QLabel()
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setFixedHeight(24)
        name.setText(
            QFontMetrics(name.font()).elidedText(
                source.name,
                Qt.TextElideMode.ElideMiddle,
                190,
            )
        )
        name.setToolTip(str(source))
        tile_layout.addWidget(name)
        self.design_preview.setItemWidget(item, tile)

    def _remove_design_preview(self, item: QListWidgetItem) -> None:
        source_value = item.data(Qt.ItemDataRole.UserRole)
        if source_value:
            source = Path(source_value)
            if source in self._staged_designs:
                self._staged_designs.remove(source)
        row = self.design_preview.row(item)
        if row >= 0:
            self.design_preview.takeItem(row)
        self.import_design_status.setText(
            f"{len(self._staged_designs)} design(s) ready — files upload when you click Save"
            if self._staged_designs
            else "No designs selected"
        )

    def _open_design_preview(self, item: QListWidgetItem, _column: int = 0) -> None:
        source = item.data(Qt.ItemDataRole.UserRole)
        if source:
            DesignPreviewDialog(Path(source), self).exec()

    def order_input(self) -> OrderInput:
        return OrderInput(
            customer_id=int(self.customer.currentData()),
            order_type=self.order_type.currentText(),
        )

    def eventFilter(self, watched, event) -> bool:
        preview_source = watched.property("previewSource") if isinstance(watched, QFrame) else None
        if preview_source and event.type() == QEvent.Type.MouseButtonDblClick:
            DesignPreviewDialog(Path(preview_source), self).exec()
            return True
        if (
            watched is self.order_type
            and self.customer.currentData() is None
            and event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress)
        ):
            QMessageBox.warning(self, "Select customer", "Select a customer first.")
            return True
        return super().eventFilter(watched, event)

    def _upload_staged_designs(self, customer_id: int) -> bool:
        if not self._staged_designs:
            return True
        today = date.today().isoformat()
        date_name = today
        try:
            if today not in self.customer_service.customer_storage_dates(customer_id):
                date_name = self.customer_service.create_customer_date_folder(customer_id)
        except CustomerStorageDateExistsError:
            date_name = today
        except Exception as error:
            QMessageBox.warning(self, "Design not imported", str(error))
            return False
        failures = []
        for source in self._staged_designs:
            try:
                self.customer_service.upload_customer_file(
                    customer_id,
                    date_name,
                    "Design",
                    source,
                )
            except Exception as error:
                failures.append(f"{source.name}: {error}")
        if failures:
            QMessageBox.warning(self, "Some designs were not imported", "\n".join(failures))
            return False
        self.import_design_status.setText(
            f"Uploaded {len(self._staged_designs)} design(s) to {date_name} / Design"
        )
        return True

    def _validate_and_accept(self) -> None:
        if self.customer.currentData() is None:
            QMessageBox.warning(self, "Select customer", "Select a customer first.")
            return
        if not self._upload_staged_designs(int(self.customer.currentData())):
            return
        self.accept()


class OrderDetailsDialog(QDialog):
    def __init__(
        self,
        service: OrderService,
        details: OrderDetails,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.details = details
        self.setWindowTitle(details.summary.order_number)
        self.resize(700, 600)
        self.root_layout = QVBoxLayout(self)
        self._render()

    def _render(self) -> None:
        summary = self.details.summary
        title = QLabel(f"{summary.order_number} · {summary.customer_name}")
        title.setObjectName("detailsTitle")
        self.root_layout.addWidget(title)
        form = QFormLayout()
        for label, value in (
            ("Customer No.", summary.customer_code),
            ("Customer", summary.customer_name),
            ("Product type", summary.order_type),
            ("Status", summary.status),
            ("Priority", summary.priority),
            ("Due date", summary.due_date.isoformat() if summary.due_date else "Not set"),
            ("Notes", self.details.notes or "—"),
        ):
            form.addRow(label, QLabel(value))
        self.root_layout.addLayout(form)

        self.root_layout.addWidget(QLabel("Status timeline"))
        timeline = QListWidget()
        for event in self.details.status_history:
            transition = (
                event.to_status
                if event.from_status is None
                else f"{event.from_status} → {event.to_status}"
            )
            note = f" — {event.note}" if event.note else ""
            timeline.addItem(f"{event.changed_at:%Y-%m-%d %H:%M} · {transition}{note}")
        self.root_layout.addWidget(timeline)

        status_row = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItems(ORDER_STATUSES)
        self.status.setCurrentText(summary.status)
        self.status_note = QLineEdit()
        self.status_note.setPlaceholderText("Status note")
        change = QPushButton("Change status")
        status_row.addWidget(self.status)
        status_row.addWidget(self.status_note, 1)
        status_row.addWidget(change)
        self.root_layout.addLayout(status_row)
        change.clicked.connect(self.change_status)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        self.root_layout.addWidget(close)

    def change_status(self) -> None:
        self.details = self.service.change_status(
            self.details.summary.id,
            self.status.currentText(),
            self.status_note.text(),
        )
        QMessageBox.information(self, "Status updated", "The order status was recorded.")
        self.accept()


class OrdersPage(QWidget):
    order_changed = Signal()

    def __init__(
        self,
        service: OrderService,
        customer_service: CustomerService,
        product_service: ProductService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.customer_service = customer_service
        self.product_service = product_service
        self.order_ids: list[int] = []
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search order number or customer")
        new_order = QPushButton("New order")
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(new_order)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Order", "Customer", "Product type", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        view = QPushButton("View order")
        layout.addWidget(view, alignment=Qt.AlignmentFlag.AlignLeft)
        self.search.textChanged.connect(self.refresh)
        new_order.clicked.connect(self.create_order)
        view.clicked.connect(self.view_selected)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.view_selected())
        if auto_refresh:
            self.refresh()

    def _refresh_legacy(self) -> None:
        orders = self.service.list_orders(self.search.text())
        self.order_ids = [order.id for order in orders]
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            for column, value in enumerate(
                (
                    order.order_number,
                    order.customer_code,
                    order.customer_name,
                    order.order_type,
                    order.status,
                    order.priority,
                    order.due_date.isoformat() if order.due_date else "—",
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def refresh(self) -> None:
        orders = self.service.list_orders(self.search.text())
        self.order_ids = [order.id for order in orders]
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            for column, value in enumerate(
                (
                    order.order_number,
                    order.customer_display_identifier,
                    order.order_type,
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
            status = QComboBox()
            if order.status == "Cancelled":
                status.addItem("Canceled", "Cancelled")
                status.setEnabled(False)
            elif order.status in QUICK_ORDER_STATUSES:
                current_index = QUICK_ORDER_STATUSES.index(order.status)
                status.addItem(order.status, order.status)
                for available in QUICK_ORDER_STATUSES[current_index + 1 :]:
                    status.addItem(available, available)
                if order.status == "Completed":
                    status.setEnabled(False)
                else:
                    status.addItem("Canceled", "Cancelled")
            else:
                status.addItem("Select status", "")
                status.addItems(QUICK_ORDER_STATUSES)
                status.addItem("Canceled", "Cancelled")
            status.currentIndexChanged.connect(
                lambda _index, order_id=order.id, control=status: self._set_quick_status(
                    order_id,
                    control,
                )
            )
            self.table.setCellWidget(row, 3, status)

    def _set_quick_status(self, order_id: int, control: QComboBox) -> None:
        status = control.currentData() or control.currentText()
        if status not in (*QUICK_ORDER_STATUSES, "Cancelled"):
            return
        try:
            self.service.change_status(order_id, status)
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Status not updated", str(error))
            return
        self.order_changed.emit()

    def create_order(self) -> None:
        dialog = OrderCreationDialog(self.customer_service, self.product_service, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            details = self.service.create_order(dialog.order_input())
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Order not created", str(error))
            return
        self.refresh()
        self.order_changed.emit()
        OrderDetailsDialog(self.service, details, self).exec()

    def view_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.order_ids):
            return
        details = self.service.get_order(self.order_ids[row])
        OrderDetailsDialog(self.service, details, self).exec()
        self.refresh()
        self.order_changed.emit()
