"""Customer list, form, and details UI backed only by CustomerService."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QRegularExpression, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.modules.customers import (
    AddressInput,
    CustomerDeletionError,
    CustomerDetails,
    CustomerInput,
    CustomerService,
    CustomerSyncError,
    CustomerValidationError,
    DuplicateCustomerCodeError,
)
from app.modules.customers.pincode_lookup import lookup_pincode
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
        self.same_as_phone_button.clicked.connect(
            lambda: self.whatsapp.setText(self.phone.text())
        )
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
                    self.delivery_type.currentText() == "Courier"
                    and value == "OTHER TRANSPORT"
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
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if customer is not None:
            self._load(customer)
        self._update_courier_fields()

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
        show_other = (
            courier_selected and self.preferred_courier.currentText() == "OTHER TRANSPORT"
        )
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
        layout = QVBoxLayout(self)
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
        self.google_drive_button = QPushButton()
        self.google_drive_button.setObjectName("secondaryButton")
        self.google_drive_button.setVisible(
            bool(getattr(self._service, "google_drive_available", False))
        )
        self._update_google_drive_button()
        toolbar_layout.addWidget(self.search_input, 1)
        toolbar_layout.addWidget(self.status_filter)
        toolbar_layout.addWidget(self.google_drive_button)
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
                "Details",
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
        self.google_drive_button.clicked.connect(self.connect_google_drive)
        view_button.clicked.connect(self.view_selected)
        edit_button.clicked.connect(self.edit_selected)
        deactivate_button.clicked.connect(self.deactivate_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.table.doubleClicked.connect(self.view_selected)
        if auto_refresh:
            self.refresh()

    def connect_google_drive(self) -> None:
        if getattr(self._service, "google_drive_connected", False):
            sheet_url = getattr(self._service, "customer_sheet_url", None)
            if sheet_url:
                QDesktopServices.openUrl(QUrl(sheet_url))
            return
        self.google_drive_button.setEnabled(False)
        self.google_drive_button.setText("Connecting...")
        try:
            self._service.connect_google_drive()
        except CustomerSyncError as error:
            QMessageBox.warning(self, "Google Drive not connected", str(error))
        else:
            QMessageBox.information(
                self,
                "Google Drive connected",
                (
                    "Google Drive is connected.\n\n"
                    "DTF ERP folders and the Customer Master Sheet were created "
                    "automatically. Future customer changes will sync automatically."
                ),
            )
        finally:
            self.google_drive_button.setEnabled(True)
            self._update_google_drive_button()

    def _update_google_drive_button(self) -> None:
        connected = bool(getattr(self._service, "google_drive_connected", False))
        self.google_drive_button.setText(
            "Google Drive Connected ✓" if connected else "Connect Google Drive"
        )
        self.google_drive_button.setToolTip(
            "Open Customer Master Sheet"
            if connected
            else "Sign in with Gmail and create Drive folders automatically"
        )

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
            details_button = QPushButton("Details")
            details_button.setObjectName("secondaryButton")
            details_button.setProperty("customerId", customer.id)
            self.table.setCellWidget(row, 5, details_button)
        self.empty_label.setVisible(not customers)

    def selected_customer_id(self) -> int | None:
        row = self.table.currentRow()
        return self._customer_ids[row] if 0 <= row < len(self._customer_ids) else None

    def create_customer(self) -> None:
        dialog = CustomerFormDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save(lambda: self._service.create_customer(dialog.customer_input()))

    def edit_selected(self) -> None:
        customer_id = self.selected_customer_id()
        if customer_id is None:
            return
        customer = self._service.get_customer(customer_id)
        dialog = CustomerFormDialog(customer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save(lambda: self._service.update_customer(customer_id, dialog.customer_input()))

    def view_selected(self) -> None:
        customer_id = self.selected_customer_id()
        if customer_id is not None:
            CustomerDetailsDialog(self._service.get_customer(customer_id), self).exec()

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
