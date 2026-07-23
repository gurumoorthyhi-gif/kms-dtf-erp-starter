"""Products and pricing configuration UI."""

from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.modules.products import ProductInput, ProductService


class ProductFormDialog(QDialog):
    def __init__(self, service: ProductService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New product")
        layout = QFormLayout(self)
        self.code, self.name, self.unit = QLineEdit(), QLineEdit(), QLineEdit("piece")
        self.size_input, self.colour, self.gsm, self.style_input = (
            QLineEdit(),
            QLineEdit(),
            QLineEdit(),
            QLineEdit(),
        )
        self.base_price, self.tax_rate = QLineEdit("0.00"), QLineEdit("0.00")
        self.category = QComboBox()
        for category_id, name in service.list_categories():
            self.category.addItem(name, category_id)
        for label, widget in (
            ("Code", self.code),
            ("Name", self.name),
            ("Category", self.category),
            ("Unit", self.unit),
            ("Size", self.size_input),
            ("Colour", self.colour),
            ("GSM", self.gsm),
            ("Style", self.style_input),
            ("Base price", self.base_price),
            ("Tax %", self.tax_rate),
        ):
            layout.addRow(label, widget)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def value(self) -> ProductInput:
        return ProductInput(
            self.code.text(),
            self.name.text(),
            int(self.category.currentData()),
            self.unit.text(),
            Decimal(self.base_price.text()),
            Decimal(self.tax_rate.text()),
            self.size_input.text(),
            self.colour.text(),
            self.gsm.text(),
            self.style_input.text(),
        )


class ProductsPage(QWidget):
    def __init__(
        self, service: ProductService, *, auto_refresh: bool = True, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.service = service
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search products")
        new_button = QPushButton("New product")
        pricing_button = QPushButton("Pricing rules")
        toolbar.addWidget(self.search)
        toolbar.addWidget(pricing_button)
        toolbar.addWidget(new_button)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Code", "Product", "Category", "Unit", "Price", "Tax %"]
        )
        layout.addLayout(toolbar)
        layout.addWidget(self.table)
        self.search.textChanged.connect(self.refresh)
        new_button.clicked.connect(self.create_product)
        pricing_button.clicked.connect(self.configure_pricing)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        products = self.service.list_products(self.search.text())
        self.table.setRowCount(len(products))
        for row, product in enumerate(products):
            for column, value in enumerate(
                (
                    product.code,
                    product.name,
                    product.category,
                    product.unit,
                    str(product.base_price),
                    str(product.tax_rate),
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def create_product(self) -> None:
        dialog = ProductFormDialog(self.service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.service.create_product(dialog.value())
            self.refresh()

    def configure_pricing(self) -> None:
        PricingConfigurationDialog(self.service, self).exec()


class PricingConfigurationDialog(QDialog):
    """Configure quantity prices, discounts, and taxes without embedding rules in UI."""

    def __init__(self, service: ProductService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Pricing configuration")
        self.resize(460, 300)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._price_rule_tab(), "Quantity price")
        tabs.addTab(self._discount_tab(), "Discount")
        tabs.addTab(self._tax_tab(), "Tax")
        layout.addWidget(tabs)
        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        layout.addWidget(close_button)

    def _price_rule_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.rule_product = QComboBox()
        for product in self.service.list_products():
            self.rule_product.addItem(f"{product.code} - {product.name}", product.id)
        self.rule_minimum = QLineEdit("1")
        self.rule_price = QLineEdit("0.00")
        save = QPushButton("Add price rule")
        save.clicked.connect(self._save_price_rule)
        form.addRow("Product", self.rule_product)
        form.addRow("Minimum quantity", self.rule_minimum)
        form.addRow("Unit price", self.rule_price)
        form.addRow(save)
        return tab

    def _discount_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.discount_name = QLineEdit()
        self.discount_minimum = QLineEdit("0.00")
        self.discount_percentage = QLineEdit("0.00")
        save = QPushButton("Add discount rule")
        save.clicked.connect(self._save_discount)
        form.addRow("Name", self.discount_name)
        form.addRow("Minimum subtotal", self.discount_minimum)
        form.addRow("Percentage", self.discount_percentage)
        form.addRow(save)
        return tab

    def _tax_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.tax_name = QLineEdit()
        self.tax_percentage = QLineEdit("0.00")
        save = QPushButton("Add tax configuration")
        save.clicked.connect(self._save_tax)
        form.addRow("Name", self.tax_name)
        form.addRow("Percentage", self.tax_percentage)
        form.addRow(save)
        return tab

    def _save_price_rule(self) -> None:
        product_id = self.rule_product.currentData()
        if product_id is not None:
            self.service.add_price_rule(
                int(product_id),
                Decimal(self.rule_minimum.text()),
                Decimal(self.rule_price.text()),
            )

    def _save_discount(self) -> None:
        self.service.add_discount_rule(
            self.discount_name.text(),
            Decimal(self.discount_minimum.text()),
            Decimal(self.discount_percentage.text()),
        )

    def _save_tax(self) -> None:
        self.service.add_tax_configuration(
            self.tax_name.text(),
            Decimal(self.tax_percentage.text()),
        )
