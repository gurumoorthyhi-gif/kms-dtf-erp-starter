"""Customer list, form, and details UI backed only by CustomerService."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import gettempdir

from PySide6.QtCore import (
    QEvent,
    QObject,
    QRegularExpression,
    QRunnable,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QDesktopServices,
    QDoubleValidator,
    QImageReader,
    QPixmap,
    QRegularExpressionValidator,
)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.customers import (
    AddressInput,
    CustomerDeletionError,
    CustomerDetails,
    CustomerInput,
    CustomerService,
    CustomerStorageDateExistsError,
    CustomerSyncError,
    CustomerValidationError,
    DuplicateCustomerCodeError,
)
from app.modules.customers.pincode_lookup import lookup_pincode
from app.modules.customers.service import CUSTOMER_STORAGE_FOLDERS
from app.ui.components.effects import apply_soft_shadow

INDIA_STATES_AND_UNION_TERRITORIES = (
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)


class AddressEditor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self.door_number = QLineEdit()
        self.street_name = QLineEdit()
        self.village_city = QLineEdit()
        self.landmark = QLineEdit()
        self.district = QLineEdit()
        self.state = QComboBox()
        self.state.setEditable(True)
        self.state.addItems(INDIA_STATES_AND_UNION_TERRITORIES)
        self.state.setCurrentIndex(-1)
        self.state.setPlaceholderText("Type to search state")
        state_completer = QCompleter(INDIA_STATES_AND_UNION_TERRITORIES, self.state)
        state_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        state_completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.state.setCompleter(state_completer)
        self.postal_code = QLineEdit()
        self.postal_code.setMaxLength(6)
        self.postal_code.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,6}"), self.postal_code)
        )
        self.postal_code.setPlaceholderText("Enter 6-digit pincode")
        self.postal_code.textChanged.connect(self._autofill_from_pincode)
        self.country = QLineEdit("India")
        self.country.setReadOnly(True)
        for label, field in (
            ("Door No.", self.door_number),
            ("Street name", self.street_name),
            ("Village / City", self.village_city),
            ("Landmark", self.landmark),
            ("Pincode", self.postal_code),
            ("District", self.district),
            ("State", self.state),
            ("Country", self.country),
        ):
            field.setObjectName("customerInput")
            layout.addRow(label, field)

    def value(self) -> AddressInput:
        return AddressInput(
            line1=self.door_number.text(),
            line2=self.street_name.text(),
            city=self.village_city.text(),
            landmark=self.landmark.text(),
            district=self.district.text(),
            state=self.state.currentText(),
            postal_code=self.postal_code.text(),
            country=self.country.text(),
        )

    def set_value(self, address: AddressInput) -> None:
        self.door_number.setText(address.line1)
        self.street_name.setText(address.line2)
        self.village_city.setText(address.city)
        self.landmark.setText(address.landmark)
        self.district.setText(address.district)
        self.state.setCurrentText(address.state)
        self.postal_code.setText(address.postal_code)
        self.country.setText(address.country)

    def _autofill_from_pincode(self, pincode: str) -> None:
        details = lookup_pincode(pincode)
        if details is None:
            return
        self.district.setText(details.district)
        self.state.setCurrentText(details.state)


class CustomerFormDialog(QDialog):
    def __init__(
        self,
        customer: CustomerDetails | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit customer" if customer else "New customer")
        self.resize(1080, 650)
        self.setMinimumSize(900, 580)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(14)
        self._customer_code = customer.summary.code if customer else ""
        self._save_operation = None

        columns = QHBoxLayout()
        columns.setSpacing(18)
        customer_panel = QFrame()
        customer_panel.setObjectName("customerFormPanel")
        customer_layout = QVBoxLayout(customer_panel)
        customer_layout.setContentsMargins(16, 14, 16, 14)
        customer_title = QLabel("Customer details")
        customer_title.setObjectName("detailsTitle")
        customer_layout.addWidget(customer_title)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.name = QLineEdit()
        self.business_name = QLineEdit()
        self.phone = QLineEdit()
        self.whatsapp = QLineEdit()
        self.delivery_type = QComboBox()
        self.delivery_type.addItems(("Courier", "Local"))
        self.preferred_courier = QComboBox()
        self.preferred_courier.addItem("Select preferred courier", "")
        self.preferred_courier.addItems(
            ("ST", "PROFESSIONAL", "DTDC", "BUS", "TRAIN", "OTHER TRANSPORT")
        )
        self.other_transport_name = QLineEdit()
        self.other_transport_name.setPlaceholderText("Enter transport name")
        self.other_transport_name.setObjectName("customerInput")
        self.other_transport_name.setVisible(False)
        self.preferred_courier.currentTextChanged.connect(
            lambda value: self.other_transport_name.setVisible(value == "OTHER TRANSPORT")
        )
        self.email = QLineEdit()
        self.gst = QLineEdit()
        self.preferred_rate = QLineEdit("0.00")
        rate_validator = QDoubleValidator(0.0, 9999999999.99, 2, self.preferred_rate)
        rate_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.preferred_rate.setValidator(rate_validator)
        for label, field in (
            ("Customer name *", self.name),
            ("Business name", self.business_name),
            ("Phone *", self.phone),
            ("Email", self.email),
            ("GST number", self.gst),
            ("Preferred rate", self.preferred_rate),
        ):
            field.setObjectName("customerInput")
            form.addRow(label, field)
        whatsapp_row = QWidget()
        whatsapp_layout = QHBoxLayout(whatsapp_row)
        whatsapp_layout.setContentsMargins(0, 0, 0, 0)
        self.whatsapp.setObjectName("customerInput")
        self.same_as_phone_button = QPushButton("Same as phone")
        self.same_as_phone_button.setObjectName("secondaryButton")
        self.same_as_phone_button.clicked.connect(lambda: self.whatsapp.setText(self.phone.text()))
        whatsapp_layout.addWidget(self.whatsapp, 1)
        whatsapp_layout.addWidget(self.same_as_phone_button)
        form.addRow("WhatsApp number", whatsapp_row)
        form.addRow("Delivery type", self.delivery_type)
        form.addRow("Preferred courier *", self.preferred_courier)
        form.addRow("Other transport name *", self.other_transport_name)
        self._preferred_courier_label = form.labelForField(self.preferred_courier)
        self._other_transport_label = form.labelForField(self.other_transport_name)
        if self._other_transport_label is not None:
            self._other_transport_label.setVisible(False)
            self.preferred_courier.currentTextChanged.connect(
                lambda value: self._other_transport_label.setVisible(
                    self.delivery_type.currentText() == "Courier" and value == "OTHER TRANSPORT"
                )
            )
        self.delivery_type.currentTextChanged.connect(self._update_courier_fields)
        customer_layout.addLayout(form)

        self.notes = QTextEdit()
        self.notes.setObjectName("customerNotes")
        self.notes.setPlaceholderText("Customer notes")
        self.notes.setMaximumHeight(88)
        customer_layout.addWidget(QLabel("Notes"))
        customer_layout.addWidget(self.notes)
        customer_layout.addStretch()

        address_panel = QFrame()
        address_panel.setObjectName("customerFormPanel")
        address_layout = QVBoxLayout(address_panel)
        address_layout.setContentsMargins(16, 14, 16, 14)
        address_title = QLabel("Billing and shipping details")
        address_title.setObjectName("detailsTitle")
        address_layout.addWidget(address_title)

        address_scroll = QScrollArea()
        address_scroll.setWidgetResizable(True)
        address_scroll.setFrameShape(QFrame.Shape.NoFrame)
        address_content = QWidget()
        address_content_layout = QVBoxLayout(address_content)
        address_content_layout.setContentsMargins(0, 0, 8, 0)
        address_content_layout.setSpacing(12)

        billing_title = QLabel("Billing address")
        billing_title.setObjectName("sectionTitle")
        self.billing = AddressEditor()
        self.shipping = AddressEditor()
        address_content_layout.addWidget(billing_title)
        address_content_layout.addWidget(self.billing)

        shipping_heading = QWidget()
        shipping_heading_layout = QHBoxLayout(shipping_heading)
        shipping_heading_layout.setContentsMargins(0, 0, 0, 0)
        shipping_title = QLabel("Shipping address")
        shipping_title.setObjectName("sectionTitle")
        self.same_as_billing_button = QPushButton("Same as billing address")
        self.same_as_billing_button.setObjectName("secondaryButton")
        self.same_as_billing_button.clicked.connect(
            lambda: self.shipping.set_value(self.billing.value())
        )
        shipping_heading_layout.addWidget(shipping_title)
        shipping_heading_layout.addStretch()
        shipping_heading_layout.addWidget(self.same_as_billing_button)
        address_content_layout.addWidget(shipping_heading)
        address_content_layout.addWidget(self.shipping)
        address_content_layout.addStretch()
        address_scroll.setWidget(address_content)
        address_layout.addWidget(address_scroll, 1)

        columns.addWidget(customer_panel, 1)
        columns.addWidget(address_panel, 1)
        layout.addLayout(columns, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons = buttons
        buttons.accepted.connect(self._attempt_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if customer is not None:
            self._load(customer)
        self._update_courier_fields()

    def set_save_operation(self, operation) -> None:
        """Run persistence before accepting so invalid forms remain editable."""

        self._save_operation = operation

    def _attempt_save(self) -> None:
        if self._save_operation is None:
            self.accept()
            return
        try:
            self._save_operation(self.customer_input())
        except (CustomerValidationError, DuplicateCustomerCodeError) as error:
            QMessageBox.warning(self, "Customer not saved", str(error))
            return
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Customer not saved", "Preferred rate must be a valid amount")
            self.preferred_rate.setFocus()
            return
        except CustomerSyncError as error:
            QMessageBox.warning(self, "Google sync failed", str(error))
        self.accept()

    def customer_input(self) -> CustomerInput:
        return CustomerInput(
            name=self.name.text(),
            phone=self.phone.text(),
            code=self._customer_code,
            business_name=self.business_name.text(),
            whatsapp_number=self.whatsapp.text(),
            delivery_type=self.delivery_type.currentText(),
            preferred_courier=(
                self.preferred_courier.currentData() or self.preferred_courier.currentText()
                if self.delivery_type.currentText() == "Courier"
                else ""
            ),
            other_transport_name=(
                self.other_transport_name.text()
                if self.delivery_type.currentText() == "Courier"
                else ""
            ),
            preferred_rate=Decimal(self.preferred_rate.text() or "0.00"),
            email=self.email.text() or None,
            gst_number=self.gst.text(),
            billing_address=self.billing.value(),
            shipping_address=self.shipping.value(),
            notes=self.notes.toPlainText(),
        )

    def _load(self, customer: CustomerDetails) -> None:
        summary = customer.summary
        self.name.setText(summary.name)
        self.business_name.setText(summary.business_name)
        self.phone.setText(summary.phone)
        self.whatsapp.setText(customer.whatsapp_number)
        self.delivery_type.setCurrentText(summary.delivery_type)
        self.preferred_courier.setCurrentText(summary.preferred_courier)
        self.other_transport_name.setText(summary.other_transport_name)
        self.preferred_rate.setText(f"{summary.preferred_rate:.2f}")
        self.email.setText(summary.email or "")
        self.gst.setText(customer.gst_number)
        self.billing.set_value(customer.billing_address)
        self.shipping.set_value(customer.shipping_address)
        self.notes.setPlainText(customer.notes)

    def _update_courier_fields(self) -> None:
        courier_selected = self.delivery_type.currentText() == "Courier"
        self.preferred_courier.setVisible(courier_selected)
        if self._preferred_courier_label is not None:
            self._preferred_courier_label.setVisible(courier_selected)
        show_other = courier_selected and self.preferred_courier.currentText() == "OTHER TRANSPORT"
        self.other_transport_name.setVisible(show_other)
        if self._other_transport_label is not None:
            self._other_transport_label.setVisible(show_other)


class CustomerDetailsDialog(QDialog):
    def __init__(self, customer: CustomerDetails, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Customer · {customer.summary.name}")
        self.resize(520, 520)
        layout = QVBoxLayout(self)
        summary = customer.summary
        title = QLabel(summary.name)
        title.setObjectName("detailsTitle")
        layout.addWidget(title)
        form = QFormLayout()
        for label, value in (
            ("Customer No.", summary.display_identifier),
            ("Business", summary.business_name or "—"),
            ("Phone", summary.phone),
            ("WhatsApp", customer.whatsapp_number or "—"),
            ("Delivery type", summary.delivery_type),
            ("Preferred courier", _preferred_courier_text(summary)),
            ("Preferred rate", f"{summary.preferred_rate:.2f}"),
            ("Email", summary.email or "—"),
            ("GST", customer.gst_number or "—"),
            ("Status", "Active" if summary.is_active else "Inactive"),
            ("Billing", _format_address(customer.billing_address)),
            ("Shipping", _format_address(customer.shipping_address)),
            ("Notes", customer.notes or "—"),
            (
                "Files",
                "\n".join(f"{label}: {path}" for label, path in customer.file_references) or "—",
            ),
        ):
            text = QLabel(value)
            text.setWordWrap(True)
            form.addRow(label, text)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class _PreviewSignals(QObject):
    loaded = Signal(int, object, str)


class _PreviewDownloadTask(QRunnable):
    def __init__(
        self,
        service: CustomerService,
        file_id: int,
        destination: Path,
    ) -> None:
        super().__init__()
        self._service = service
        self._file_id = file_id
        self._destination = destination
        self.signals = _PreviewSignals()

    def run(self) -> None:
        try:
            path = self._service.download_customer_file(
                self._file_id,
                self._destination,
            )
        except Exception as error:
            self.signals.loaded.emit(self._file_id, None, str(error))
        else:
            self.signals.loaded.emit(self._file_id, path, "")


class CustomerFolderDialog(QDialog):
    """Browse a customer's dated Backblaze folders in a dedicated window."""

    back_requested = Signal()

    def __init__(
        self,
        service: CustomerService,
        customer_id: int,
        parent: QWidget | None = None,
        *,
        embedded: bool = False,
    ) -> None:
        super().__init__(parent)
        self._embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)
        self._service = service
        self._customer_id = customer_id
        self._customer_label = ""
        self._tree_level = "contents"
        self._file_ids: list[int] = []
        self._files_by_id = {}
        self._preview_file_id: int | None = None
        self._preview_pixmap = QPixmap()
        self._preview_tasks: set[_PreviewDownloadTask] = set()
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(800)
        self._status_timer.timeout.connect(self.refresh_files)
        details = service.ensure_customer_storage(customer_id)
        self._customer_label = details.summary.display_identifier
        self.setWindowTitle(f"Customer folder — {details.summary.display_identifier}")
        self.resize(1440, 900)
        if not embedded:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        layout = QVBoxLayout(self)
        self.heading = QLabel(details.summary.display_identifier)
        self.heading.hide()
        window_toolbar = QHBoxLayout()
        window_toolbar.addStretch()
        self.close_folder_button = QPushButton("Close")
        self.close_folder_button.setObjectName("secondaryButton")
        window_toolbar.addWidget(self.close_folder_button)
        layout.addLayout(window_toolbar)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)

        preview = QFrame()
        self.preview_panel = preview
        preview.setObjectName("glassCard")
        preview_layout = QVBoxLayout(preview)
        preview_title = QLabel("Preview")
        preview_title.setObjectName("detailsTitle")
        preview_layout.addWidget(preview_title)
        self.preview_stack = QStackedWidget()
        self.preview_message = QLabel("Select an image or PDF to preview")
        self.preview_message.setObjectName("emptyState")
        self.preview_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_message.setWordWrap(True)
        self.preview_stack.addWidget(self.preview_message)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setWidget(self.image_label)
        self.image_scroll.viewport().installEventFilter(self)
        self.preview_stack.addWidget(self.image_scroll)

        self._pdf_document = QPdfDocument(self)
        self.pdf_view = QPdfView()
        self.pdf_view.setDocument(self._pdf_document)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.preview_stack.addWidget(self.pdf_view)
        preview_layout.addWidget(self.preview_stack, 1)
        self.preview_name = QLabel("No file selected")
        self.preview_name.setObjectName("cardBody")
        self.preview_name.setWordWrap(True)
        preview_layout.addWidget(self.preview_name)

        browser = QWidget()
        self.browser_panel = browser
        browser_layout = QVBoxLayout(browser)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.browser_splitter = browser_splitter
        browser_splitter.setChildrenCollapsible(False)
        tree_panel = QWidget()
        self.tree_panel = tree_panel
        tree_layout = QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_toolbar = QHBoxLayout()
        self.tree_back_button = QPushButton("← Back")
        self.tree_back_button.setObjectName("secondaryButton")
        self.tree_location = QLabel()
        self.tree_location.setObjectName("cardBody")
        tree_toolbar.addWidget(self.tree_back_button)
        tree_toolbar.addWidget(self.tree_location, 1)
        tree_layout.addLayout(tree_toolbar)
        self.create_today_button = QPushButton("Create Folders")
        self.create_today_button.setObjectName("primaryButton")
        tree_layout.addWidget(self.create_today_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Customer folders")
        self.tree.setMinimumWidth(220)
        tree_layout.addWidget(self.tree, 1)
        browser_splitter.addWidget(tree_panel)

        files_widget = QWidget()
        right = QVBoxLayout(files_widget)
        right.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["File", "Size", "Status", "Uploaded"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.upload_button = QPushButton("Upload file")
        self.open_button = QPushButton("Open")
        self.download_button = QPushButton("Download")
        self.replace_button = QPushButton("Replace / new version")
        for button in (
            self.upload_button,
            self.open_button,
            self.download_button,
            self.replace_button,
        ):
            button.setObjectName("secondaryButton")
            actions.addWidget(button)
        actions.addStretch()
        right.addLayout(actions)
        browser_splitter.addWidget(files_widget)
        browser_splitter.setSizes([260, 720])
        browser_layout.addWidget(browser_splitter, 1)
        self.workspace_splitter.addWidget(browser)
        self.workspace_splitter.addWidget(preview)
        self.workspace_splitter.setSizes([920, 520])
        layout.addWidget(self.workspace_splitter, 1)

        self.tree.currentItemChanged.connect(self.refresh_files)
        self.tree.itemActivated.connect(self._open_tree_item)
        self.tree_back_button.clicked.connect(self._tree_back)
        self.table.itemSelectionChanged.connect(self._update_file_actions)
        self.table.itemSelectionChanged.connect(self.preview_selected)
        self.upload_button.clicked.connect(self.upload_file)
        self.create_today_button.clicked.connect(self.create_today_folder)
        self.open_button.clicked.connect(self.open_file)
        self.download_button.clicked.connect(self.download_file)
        self.replace_button.clicked.connect(self.replace_file)
        self.table.doubleClicked.connect(self.open_file)
        self.close_folder_button.clicked.connect(
            self.back_requested.emit if embedded else self.accept
        )
        self._populate_tree()

    def _populate_tree(self, selected_date: str | None = None) -> None:
        self.tree.clear()
        if self._tree_level == "root":
            self.tree_location.setText("Main customer folder")
            self.tree_back_button.setEnabled(False)
            root_item = QTreeWidgetItem(["Customers"])
            root_item.setData(0, Qt.ItemDataRole.UserRole, ("navigate", "customers", ""))
            self.tree.addTopLevelItem(root_item)
            self._clear_file_view()
            return
        if self._tree_level == "customers":
            self.tree_location.setText("Customers")
            self.tree_back_button.setEnabled(True)
            for customer in self._service.list_customers("", active=True):
                customer_item = QTreeWidgetItem([customer.display_identifier])
                customer_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("customer", customer.id, customer.display_identifier),
                )
                self.tree.addTopLevelItem(customer_item)
            self._clear_file_view()
            return
        self.tree_location.setText(self._customer_label)
        self.tree_back_button.setEnabled(True)
        self.create_today_button.setEnabled(True)
        selected_item = None
        for date_name in self._service.customer_storage_dates(self._customer_id):
            date_item = QTreeWidgetItem([date_name])
            date_item.setData(0, Qt.ItemDataRole.UserRole, ("date", date_name, ""))
            self.tree.addTopLevelItem(date_item)
            for folder_name in CUSTOMER_STORAGE_FOLDERS:
                folder_item = QTreeWidgetItem([folder_name])
                folder_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("folder", date_name, folder_name),
                )
                date_item.addChild(folder_item)
                if date_name == selected_date and selected_item is None:
                    selected_item = folder_item
            date_item.setExpanded(True)
        if selected_item is not None:
            self.tree.setCurrentItem(selected_item)
        if self.tree.topLevelItemCount():
            first_date = self.tree.topLevelItem(0)
            if self.tree.currentItem() is None and first_date.childCount():
                self.tree.setCurrentItem(first_date.child(0))
        else:
            self.table.setRowCount(0)
            self._file_ids = []
            self._files_by_id = {}
            self._show_preview_message(
                "No date folders yet.\nSelect Create today's folder when work begins."
            )

    def _tree_back(self) -> None:
        if self._tree_level == "contents":
            self._tree_level = "customers"
        elif self._tree_level == "customers":
            self._tree_level = "root"
        self._populate_tree()

    def _open_tree_item(self, item: QTreeWidgetItem, _column: int) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if not value:
            return
        if value[0] == "customer":
            self._customer_id = value[1]
            details = self._service.ensure_customer_storage(self._customer_id)
            self._customer_label = details.summary.display_identifier
            self.heading.setText(self._customer_label)
            self.setWindowTitle(f"Customer folder — {self._customer_label}")
            self._tree_level = "contents"
        elif value[0] == "navigate":
            self._tree_level = value[1]
        else:
            return
        self._populate_tree()

    def _clear_file_view(self) -> None:
        self.table.setRowCount(0)
        self._file_ids = []
        self._files_by_id = {}
        self.upload_button.setEnabled(False)
        self.create_today_button.setEnabled(False)
        self._update_file_actions()
        self.preview_name.setText("No file selected")
        self._show_preview_message("Open the customer folder and select a file to preview")

    def create_today_folder(self) -> None:
        try:
            date_name = self._service.create_customer_date_folder(self._customer_id)
        except CustomerStorageDateExistsError as error:
            QMessageBox.information(self, "Folder already exists", str(error))
            return
        except Exception as error:
            QMessageBox.warning(self, "Folder not created", str(error))
            return
        self._populate_tree(date_name)

    def _selection(self) -> tuple[str, str] | None:
        item = self.tree.currentItem()
        value = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if value and value[0] == "folder":
            return value[1], value[2]
        return None

    def _selected_file_id(self) -> int | None:
        row = self.table.currentRow()
        return self._file_ids[row] if 0 <= row < len(self._file_ids) else None

    def _update_file_actions(self) -> None:
        has_file = self._selected_file_id() is not None
        self.open_button.setEnabled(has_file)
        self.download_button.setEnabled(has_file)
        self.replace_button.setEnabled(has_file)

    def preview_selected(self) -> None:
        file_id = self._selected_file_id()
        self._preview_file_id = file_id
        if file_id is None:
            self._show_preview_message("Select an image or PDF to preview")
            self.preview_name.setText("No file selected")
            return
        record = self._files_by_id.get(file_id)
        if record is None:
            return
        self.preview_name.setText(record.original_name)
        local_path = Path(record.local_path)
        if local_path.is_file():
            self._display_preview(local_path)
            return
        if record.transfer_state != "synced":
            self._show_preview_message("Preview will be available after upload completes.")
            return
        cache_dir = Path(gettempdir()) / "kms_dtf_erp_previews"
        cache_dir.mkdir(parents=True, exist_ok=True)
        destination = cache_dir / f"{file_id}{Path(record.original_name).suffix.casefold()}"
        if destination.is_file():
            self._display_preview(destination)
            return
        self._show_preview_message("Loading secure preview from Backblaze…")
        task = _PreviewDownloadTask(self._service, file_id, destination)
        self._preview_tasks.add(task)
        task.signals.loaded.connect(self._preview_downloaded)
        task.signals.loaded.connect(
            lambda *_args, current_task=task: self._preview_tasks.discard(current_task)
        )
        QThreadPool.globalInstance().start(task)

    def _preview_downloaded(self, file_id: int, path, error: str) -> None:
        if file_id != self._preview_file_id:
            return
        if error or path is None:
            self._show_preview_message(f"Preview could not be loaded.\n{error}")
            return
        self._display_preview(Path(path))

    def _display_preview(self, path: Path) -> None:
        if path.suffix.casefold() == ".pdf":
            self._preview_pixmap = QPixmap()
            self._pdf_document.close()
            error = self._pdf_document.load(str(path))
            if error != QPdfDocument.Error.None_:
                self._show_preview_message("This PDF could not be rendered.")
                return
            self.preview_stack.setCurrentWidget(self.pdf_view)
            return
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self._show_preview_message(
                "Preview is not available for this file type.\nUse Open or Download."
            )
            return
        self._preview_pixmap = QPixmap.fromImage(image)
        self.preview_stack.setCurrentWidget(self.image_scroll)
        self._scale_image_preview()

    def _show_preview_message(self, message: str) -> None:
        self.preview_message.setText(message)
        self.preview_stack.setCurrentWidget(self.preview_message)

    def _scale_image_preview(self) -> None:
        if self._preview_pixmap.isNull():
            return
        viewport = self.image_scroll.viewport().size()
        width = max(80, viewport.width() - 20)
        height = max(80, viewport.height() - 20)
        self.image_label.setPixmap(
            self._preview_pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.image_scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._scale_image_preview()
        return super().eventFilter(watched, event)

    def refresh_files(self, *_args) -> None:
        selected_id = self._selected_file_id()
        selection = self._selection()
        files = (
            self._service.list_customer_files(self._customer_id, *selection) if selection else []
        )
        self._file_ids = [item.id for item in files]
        self._files_by_id = {item.id: item for item in files}
        self.table.setRowCount(len(files))
        for row, item in enumerate(files):
            values = (
                item.original_name,
                _format_file_size(item.size_bytes),
                item.transfer_state.title(),
                item.created_at.strftime("%d %b %Y %I:%M %p"),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            if item.id == selected_id:
                self.table.selectRow(row)
        self.upload_button.setEnabled(selection is not None)
        self._update_file_actions()
        if any(item.transfer_state == "queued" for item in files):
            self._status_timer.start()
        else:
            self._status_timer.stop()

    def upload_file(self) -> None:
        selection = self._selection()
        if selection is None:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Upload customer file")
        if not filename:
            return
        try:
            self._service.upload_customer_file(
                self._customer_id,
                *selection,
                Path(filename),
            )
        except Exception as error:
            QMessageBox.warning(self, "Upload failed", str(error))
        self.refresh_files()

    def open_file(self) -> None:
        file_id = self._selected_file_id()
        if file_id is None:
            return
        try:
            QDesktopServices.openUrl(QUrl(self._service.customer_file_url(file_id)))
        except Exception as error:
            QMessageBox.warning(self, "File unavailable", str(error))

    def download_file(self) -> None:
        row = self.table.currentRow()
        file_id = self._selected_file_id()
        if file_id is None or row < 0:
            return
        filename = self.table.item(row, 0).text()
        destination, _ = QFileDialog.getSaveFileName(self, "Download file", filename)
        if not destination:
            return
        try:
            self._service.download_customer_file(file_id, Path(destination))
        except Exception as error:
            QMessageBox.warning(self, "Download failed", str(error))

    def replace_file(self) -> None:
        if self._selected_file_id() is not None:
            self.upload_file()


class CustomersPage(QWidget):
    def __init__(
        self,
        service: CustomerService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._customer_ids: list[int] = []
        self._folder_workspace: CustomerFolderDialog | None = None
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.page_stack = QStackedWidget()
        self.customer_list_page = QWidget()
        self.page_stack.addWidget(self.customer_list_page)
        root_layout.addWidget(self.page_stack)
        layout = QVBoxLayout(self.customer_list_page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        toolbar = QFrame()
        toolbar.setObjectName("customerToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("customerSearch")
        self.search_input.setPlaceholderText("Search name, business, or phone")
        self.status_filter = QComboBox()
        self.status_filter.addItem("Active", True)
        self.status_filter.addItem("Inactive", False)
        self.status_filter.addItem("All", None)
        new_button = QPushButton("New customer")
        new_button.setObjectName("primaryButton")
        toolbar_layout.addWidget(self.search_input, 1)
        toolbar_layout.addWidget(self.status_filter)
        toolbar_layout.addWidget(new_button)
        apply_soft_shadow(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("customerTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Customer No.",
                "Customer Name",
                "Business",
                "Phone",
                "Preferred Courier",
                "Customer Folder",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        actions = QHBoxLayout()
        view_button = QPushButton("View")
        edit_button = QPushButton("Edit")
        deactivate_button = QPushButton("Deactivate")
        self.delete_button = QPushButton("Delete")
        for button in (view_button, edit_button, deactivate_button, self.delete_button):
            button.setObjectName("secondaryButton")
            actions.addWidget(button)
        actions.addStretch()

        self.empty_label = QLabel("No customers found")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(toolbar)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_label)
        layout.addLayout(actions)

        self.search_input.textChanged.connect(self.refresh)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        new_button.clicked.connect(self.create_customer)
        view_button.clicked.connect(self.view_selected)
        edit_button.clicked.connect(self.edit_selected)
        deactivate_button.clicked.connect(self.deactivate_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.table.doubleClicked.connect(self.view_selected)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        active = self.status_filter.currentData()
        try:
            customers = self._service.list_customers(self.search_input.text(), active=active)
        except Exception:
            customers = []
        self._customer_ids = [customer.id for customer in customers]
        self.table.setRowCount(len(customers))
        for row, customer in enumerate(customers):
            values = (
                customer.display_identifier,
                customer.name,
                customer.business_name,
                customer.phone,
                _preferred_courier_text(customer),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            folder_button = QPushButton("Open folder")
            folder_button.setObjectName("secondaryButton")
            folder_button.setProperty("customerId", customer.id)
            folder_button.clicked.connect(
                lambda checked=False, customer_id=customer.id: self.open_customer_folder(
                    customer_id
                )
            )
            self.table.setCellWidget(row, 5, folder_button)
        self.empty_label.setVisible(not customers)

    def selected_customer_id(self) -> int | None:
        row = self.table.currentRow()
        return self._customer_ids[row] if 0 <= row < len(self._customer_ids) else None

    def create_customer(self) -> None:
        dialog = CustomerFormDialog(parent=self)
        dialog.set_save_operation(self._service.create_customer)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit_selected(self) -> None:
        customer_id = self.selected_customer_id()
        if customer_id is None:
            return
        customer = self._service.get_customer(customer_id)
        dialog = CustomerFormDialog(customer, self)
        dialog.set_save_operation(
            lambda customer_input: self._service.update_customer(customer_id, customer_input)
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def view_selected(self) -> None:
        customer_id = self.selected_customer_id()
        if customer_id is not None:
            CustomerDetailsDialog(self._service.get_customer(customer_id), self).exec()

    def open_customer_folder(self, customer_id: int) -> None:
        try:
            workspace = CustomerFolderDialog(
                self._service,
                customer_id,
                self,
            )
        except Exception as error:
            QMessageBox.warning(self, "Customer folder unavailable", str(error))
            return
        if self._folder_workspace is not None:
            self._folder_workspace.close()
        self._folder_workspace = workspace
        workspace.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        workspace.destroyed.connect(
            lambda _object=None, window=workspace: self._folder_window_closed(window)
        )
        workspace.showFullScreen()

    def _folder_window_closed(self, window: CustomerFolderDialog) -> None:
        if self._folder_workspace is window:
            self._folder_workspace = None

    def show_customer_list(self) -> None:
        self.page_stack.setCurrentWidget(self.customer_list_page)
        if self._folder_workspace is not None:
            self._folder_workspace.close()
            self._folder_workspace = None
        self.refresh()

    def deactivate_selected(self) -> None:
        customer_id = self.selected_customer_id()
        if customer_id is not None:
            try:
                self._service.deactivate_customer(customer_id)
            except CustomerSyncError as error:
                QMessageBox.warning(self, "Google sync failed", str(error))
            self.refresh()

    def delete_selected(self) -> None:
        customer_id = self.selected_customer_id()
        if customer_id is None:
            return
        customer = self._service.get_customer(customer_id)
        answer = QMessageBox.question(
            self,
            "Delete customer",
            (
                f'Permanently delete "{customer.summary.name}" '
                f"({customer.summary.display_identifier})?\n\nThis action cannot be undone."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._service.delete_customer(customer_id)
        except (CustomerDeletionError, CustomerSyncError) as error:
            QMessageBox.warning(self, "Customer not deleted", str(error))
            return
        self.refresh()

    def _save(self, operation) -> None:
        try:
            operation()
        except (CustomerValidationError, DuplicateCustomerCodeError) as error:
            QMessageBox.warning(self, "Customer not saved", str(error))
            return
        except CustomerSyncError as error:
            QMessageBox.warning(self, "Google sync failed", str(error))
        self.refresh()


def _format_address(address: AddressInput) -> str:
    return (
        ", ".join(
            part
            for part in (
                address.line1,
                address.line2,
                address.city,
                address.landmark,
                address.district,
                address.state,
                address.postal_code,
                address.country,
            )
            if part
        )
        or "—"
    )


def _preferred_courier_text(customer) -> str:
    if customer.preferred_courier == "OTHER TRANSPORT":
        return customer.other_transport_name or "OTHER TRANSPORT"
    return customer.preferred_courier


def _format_file_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"
