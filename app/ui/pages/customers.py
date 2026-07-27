"""Customer list, form, and details UI backed only by CustomerService."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    CustomerDetails,
    CustomerInput,
    CustomerService,
    CustomerValidationError,
    DuplicateCustomerCodeError,
)
from app.ui.components.effects import apply_soft_shadow


class AddressEditor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self.line1 = QLineEdit()
        self.line2 = QLineEdit()
        self.city = QLineEdit()
        self.state = QLineEdit()
        self.postal_code = QLineEdit()
        self.country = QLineEdit("India")
        for label, field in (
            ("Address line 1", self.line1),
            ("Address line 2", self.line2),
            ("City", self.city),
            ("State", self.state),
            ("Postal code", self.postal_code),
            ("Country", self.country),
        ):
            field.setObjectName("customerInput")
            layout.addRow(label, field)

    def value(self) -> AddressInput:
        return AddressInput(
            self.line1.text(),
            self.line2.text(),
            self.city.text(),
            self.state.text(),
            self.postal_code.text(),
            self.country.text(),
        )

    def set_value(self, address: AddressInput) -> None:
        self.line1.setText(address.line1)
        self.line2.setText(address.line2)
        self.city.setText(address.city)
        self.state.setText(address.state)
        self.postal_code.setText(address.postal_code)
        self.country.setText(address.country)


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
        for label, field in (
            ("Customer name *", self.name),
            ("Business name", self.business_name),
            ("Phone *", self.phone),
            ("Email", self.email),
            ("GST number", self.gst),
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
            ("Business", summary.business_name or "—"),
            ("Phone", summary.phone),
            ("WhatsApp", customer.whatsapp_number or "—"),
            ("Delivery type", summary.delivery_type),
            ("Preferred courier", _preferred_courier_text(summary)),
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
        for button in (view_button, edit_button, deactivate_button):
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
                customer.code,
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
            self._service.deactivate_customer(customer_id)
            self.refresh()

    def _save(self, operation) -> None:
        try:
            operation()
        except (CustomerValidationError, DuplicateCustomerCodeError) as error:
            QMessageBox.warning(self, "Customer not saved", str(error))
            return
        self.refresh()


def _format_address(address: AddressInput) -> str:
    return (
        ", ".join(
            part
            for part in (
                address.line1,
                address.line2,
                address.city,
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
