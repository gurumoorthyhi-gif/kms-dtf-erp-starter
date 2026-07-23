"""Inventory, supplier, and purchase workflow pages."""

from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.inventory import (
    INVENTORY_TYPES,
    InventoryItemInput,
    InventoryService,
    PurchaseInput,
    PurchaseItemInput,
    PurchaseService,
    SupplierInput,
)


class InventoryItemDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New inventory item")
        form = QFormLayout(self)
        self.sku, self.name, self.unit = QLineEdit(), QLineEdit(), QLineEdit()
        self.item_type = QComboBox()
        self.item_type.addItems(INVENTORY_TYPES)
        self.reorder = QLineEdit("0")
        self.cost = QLineEdit("0.00")
        self.allow_negative = QCheckBox()
        for label, widget in (
            ("SKU", self.sku),
            ("Name", self.name),
            ("Type", self.item_type),
            ("Unit", self.unit),
            ("Reorder level", self.reorder),
            ("Unit cost", self.cost),
            ("Allow negative", self.allow_negative),
        ):
            form.addRow(label, widget)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def value(self) -> InventoryItemInput:
        return InventoryItemInput(
            self.sku.text(),
            self.name.text(),
            self.item_type.currentText(),
            self.unit.text(),
            Decimal(self.reorder.text()),
            Decimal(self.cost.text()),
            self.allow_negative.isChecked(),
        )


class InventoryPage(QWidget):
    def __init__(self, service: InventoryService, *, auto_refresh: bool = True) -> None:
        super().__init__()
        self.service = service
        self.item_ids: list[int] = []
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        create = QPushButton("New inventory item")
        self.low_warning = QLabel()
        toolbar.addWidget(create)
        toolbar.addWidget(self.low_warning)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["SKU", "Item", "Type", "Unit", "Stock", "Reorder", "Cost", "Warning"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        self.quantity = QLineEdit("0")
        self.reason = QLineEdit()
        self.reason.setPlaceholderText("Movement or adjustment reason")
        actions.addWidget(self.quantity)
        actions.addWidget(self.reason)
        for label, handler in (
            ("Stock in", self.stock_in),
            ("Stock out", self.stock_out),
            ("Adjust to quantity", self.adjust),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            actions.addWidget(button)
        layout.addLayout(actions)
        create.clicked.connect(self.create_item)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        items = self.service.list_items()
        self.item_ids = [item.id for item in items]
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = (
                item.sku,
                item.name,
                item.item_type,
                item.unit,
                str(item.quantity_on_hand),
                str(item.reorder_level),
                str(item.unit_cost),
                "LOW STOCK" if item.is_low_stock else "",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.low_warning.setText(f"Low-stock items: {len(self.service.low_stock())}")

    def create_item(self) -> None:
        dialog = InventoryItemDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.create_item(dialog.value())
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, "Item not created", str(error))
        self.refresh()

    def selected_id(self) -> int | None:
        row = self.table.currentRow()
        return self.item_ids[row] if 0 <= row < len(self.item_ids) else None

    def stock_in(self) -> None:
        self._move("in")

    def stock_out(self) -> None:
        self._move("out")

    def adjust(self) -> None:
        self._move("adjust")

    def _move(self, kind: str) -> None:
        item_id = self.selected_id()
        if item_id is None:
            return
        try:
            quantity = Decimal(self.quantity.text())
            if kind == "in":
                self.service.stock_in(item_id, quantity, self.reason.text())
            elif kind == "out":
                self.service.stock_out(item_id, quantity, self.reason.text())
            else:
                self.service.adjust(item_id, quantity, self.reason.text())
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, "Stock update failed", str(error))
        self.refresh()


class SuppliersPage(QWidget):
    def __init__(self, service: PurchaseService, *, auto_refresh: bool = True) -> None:
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        self.code, self.name, self.phone, self.email = (
            QLineEdit(),
            QLineEdit(),
            QLineEdit(),
            QLineEdit(),
        )
        for field, placeholder in (
            (self.code, "Code"),
            (self.name, "Supplier"),
            (self.phone, "Phone"),
            (self.email, "Email"),
        ):
            field.setPlaceholderText(placeholder)
            form.addWidget(field)
        create = QPushButton("Add supplier")
        form.addWidget(create)
        layout.addLayout(form)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Code", "Supplier", "Phone", "Email"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        create.clicked.connect(self.create_supplier)
        if auto_refresh:
            self.refresh()

    def create_supplier(self) -> None:
        try:
            self.service.create_supplier(
                SupplierInput(
                    self.code.text(),
                    self.name.text(),
                    phone=self.phone.text(),
                    email=self.email.text(),
                )
            )
        except ValueError as error:
            QMessageBox.warning(self, "Supplier not created", str(error))
        self.refresh()

    def refresh(self) -> None:
        suppliers = self.service.list_suppliers()
        self.table.setRowCount(len(suppliers))
        for row, supplier in enumerate(suppliers):
            for column, value in enumerate(
                (supplier.code, supplier.name, supplier.phone, supplier.email)
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))


class PurchasesPage(QWidget):
    def __init__(
        self,
        purchase_service: PurchaseService,
        inventory_service: InventoryService,
        *,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.purchase_service = purchase_service
        self.inventory_service = inventory_service
        self.purchase_ids: list[int] = []
        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        self.supplier, self.item = QComboBox(), QComboBox()
        self.quantity, self.cost = QLineEdit("1"), QLineEdit("0.00")
        create = QPushButton("Create purchase")
        form.addWidget(self.supplier)
        form.addWidget(self.item)
        form.addWidget(self.quantity)
        form.addWidget(self.cost)
        form.addWidget(create)
        layout.addLayout(form)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Purchase", "Supplier", "Status", "Date", "Total", "Items"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        receive = QPushButton("Post purchase receipt")
        layout.addWidget(receive)
        create.clicked.connect(self.create_purchase)
        receive.clicked.connect(self.receive)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        self.supplier.clear()
        for supplier in self.purchase_service.list_suppliers():
            self.supplier.addItem(supplier.name, supplier.id)
        self.item.clear()
        for item in self.inventory_service.list_items():
            self.item.addItem(f"{item.sku} · {item.name}", item.id)
        purchases = self.purchase_service.list_purchases()
        self.purchase_ids = [purchase.id for purchase in purchases]
        self.table.setRowCount(len(purchases))
        for row, purchase in enumerate(purchases):
            for column, value in enumerate(
                (
                    purchase.purchase_number,
                    purchase.supplier_name,
                    purchase.status,
                    purchase.order_date.isoformat(),
                    str(purchase.total),
                    str(purchase.item_count),
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def create_purchase(self) -> None:
        if self.supplier.currentData() is None or self.item.currentData() is None:
            return
        try:
            self.purchase_service.create_purchase(
                PurchaseInput(
                    int(self.supplier.currentData()),
                    (
                        PurchaseItemInput(
                            int(self.item.currentData()),
                            Decimal(self.quantity.text()),
                            Decimal(self.cost.text()),
                        ),
                    ),
                )
            )
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, "Purchase not created", str(error))
        self.refresh()

    def receive(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.purchase_ids):
            try:
                self.purchase_service.receive(self.purchase_ids[row])
            except ValueError as error:
                QMessageBox.warning(self, "Receipt not posted", str(error))
            self.refresh()
