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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
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
        self.resize(620, 720)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.code = QLineEdit()
        self.name = QLineEdit()
        self.business_name = QLineEdit()
        self.phone = QLineEdit()
        self.whatsapp = QLineEdit()
        self.email = QLineEdit()
        self.gst = QLineEdit()
        for label, field in (
            ("Customer code *", self.code),
            ("Customer name *", self.name),
            ("Business name", self.business_name),
            ("Phone *", self.phone),
            ("WhatsApp number", self.whatsapp),
            ("Email", self.email),
            ("GST number", self.gst),
        ):
            field.setObjectName("customerInput")
            form.addRow(label, field)
        layout.addLayout(form)

        tabs = QTabWidget()
        self.billing = AddressEditor()
        self.shipping = AddressEditor()
        tabs.addTab(self.billing, "Billing address")
        tabs.addTab(self.shipping, "Shipping address")
        layout.addWidget(tabs)

        self.notes = QTextEdit()
        self.notes.setObjectName("customerNotes")
        self.notes.setPlaceholderText("Customer notes")
        self.notes.setMaximumHeight(90)
        layout.addWidget(self.notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if customer is not None:
            self._load(customer)

    def customer_input(self) -> CustomerInput:
        return CustomerInput(
            code=self.code.text(),
            name=self.name.text(),
            phone=self.phone.text(),
            business_name=self.business_name.text(),
            whatsapp_number=self.whatsapp.text(),
            email=self.email.text() or None,
            gst_number=self.gst.text(),
            billing_address=self.billing.value(),
            shipping_address=self.shipping.value(),
            notes=self.notes.toPlainText(),
        )

    def _load(self, customer: CustomerDetails) -> None:
        summary = customer.summary
        self.code.setText(summary.code)
        self.name.setText(summary.name)
        self.business_name.setText(summary.business_name)
        self.phone.setText(summary.phone)
        self.whatsapp.setText(customer.whatsapp_number)
        self.email.setText(summary.email or "")
        self.gst.setText(customer.gst_number)
        self.billing.set_value(customer.billing_address)
        self.shipping.set_value(customer.shipping_address)
        self.notes.setPlainText(customer.notes)


class CustomerDetailsDialog(QDialog):
    def __init__(self, customer: CustomerDetails, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Customer · {customer.summary.code}")
        self.resize(520, 520)
        layout = QVBoxLayout(self)
        summary = customer.summary
        title = QLabel(summary.name)
        title.setObjectName("detailsTitle")
        layout.addWidget(title)
        form = QFormLayout()
        for label, value in (
            ("Code", summary.code),
            ("Business", summary.business_name or "—"),
            ("Phone", summary.phone),
            ("WhatsApp", customer.whatsapp_number or "—"),
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
        self.search_input.setPlaceholderText("Search code, name, business, or phone")
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
            ["Code", "Customer", "Business", "Phone", "Email", "Status"]
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
                customer.email or "",
                "Active" if customer.is_active else "Inactive",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
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
