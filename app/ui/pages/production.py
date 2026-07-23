"""Production queue, stage board, controls, quality checks, and history."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.modules.orders import OrderService
from app.modules.production import (
    PRODUCTION_PRIORITIES,
    PRODUCTION_STAGES,
    InvalidProductionTransition,
    ProductionJobDetails,
    ProductionJobInput,
    ProductionService,
    QualityCheckInput,
)


class ProductionHistoryDialog(QDialog):
    def __init__(self, job: ProductionJobDetails, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Production history · {job.order_number}")
        self.resize(650, 520)
        layout = QVBoxLayout(self)
        summary = QLabel(
            f"{job.stage} · {job.priority} · Wastage {job.wastage_metres} m · "
            f"Reprints {job.reprint_count}"
        )
        layout.addWidget(summary)
        history = QListWidget()
        for event in job.events:
            transition = (
                f" {event.from_stage or 'Start'} → {event.to_stage}" if event.to_stage else ""
            )
            history.addItem(
                f"{event.created_at:%Y-%m-%d %H:%M} · {event.event_type}{transition} · "
                f"{event.details}"
            )
        layout.addWidget(history)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)


class ProductionPage(QWidget):
    def __init__(
        self,
        service: ProductionService,
        order_service: OrderService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.order_service = order_service
        self.job_ids: list[int] = []
        root = QVBoxLayout(self)
        create_row = QHBoxLayout()
        self.orders = QComboBox()
        self.priority = QComboBox()
        self.priority.addItems(PRODUCTION_PRIORITIES)
        self.priority.setCurrentText("Normal")
        self.has_due_date = QCheckBox("Due date")
        self.due_date = QDateEdit(QDate.currentDate())
        self.due_date.setCalendarPopup(True)
        self.due_date.setEnabled(False)
        self.has_due_date.toggled.connect(self.due_date.setEnabled)
        create = QPushButton("Create production job")
        create_row.addWidget(self.orders, 1)
        create_row.addWidget(self.priority)
        create_row.addWidget(self.has_due_date)
        create_row.addWidget(self.due_date)
        create_row.addWidget(create)
        root.addLayout(create_row)

        self.stage_board = QTabWidget()
        self.stage_lists: dict[str, QListWidget] = {}
        for stage in PRODUCTION_STAGES:
            stage_list = QListWidget()
            self.stage_lists[stage] = stage_list
            self.stage_board.addTab(stage_list, stage)
        root.addWidget(self.stage_board)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Order",
                "Customer",
                "Stage",
                "Priority",
                "Machine",
                "Operator",
                "Due",
                "Wastage",
                "State",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

        controls = QHBoxLayout()
        self.machine = QLineEdit()
        self.machine.setPlaceholderText("Machine")
        self.operator_id = QSpinBox()
        self.operator_id.setRange(0, 1_000_000)
        self.operator_id.setSpecialValueText("Unassigned")
        self.reason = QLineEdit()
        self.reason.setPlaceholderText("Pause, reprint, or wastage reason")
        self.wastage = QLineEdit("0.000")
        for widget in (self.machine, self.operator_id, self.reason, self.wastage):
            controls.addWidget(widget)
        root.addLayout(controls)
        actions = QHBoxLayout()
        for label, handler in (
            ("Assign", self.assign),
            ("Next stage", self.next_stage),
            ("Pause", self.pause),
            ("Resume", self.resume),
            ("Record reprint", self.reprint),
            ("Record wastage", self.record_wastage),
            ("Quality check", self.quality_check),
            ("History", self.history),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            actions.addWidget(button)
        root.addLayout(actions)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Production notes")
        self.notes.setMaximumHeight(70)
        save_notes = QPushButton("Save notes")
        root.addWidget(self.notes)
        root.addWidget(save_notes)
        create.clicked.connect(self.create_job)
        save_notes.clicked.connect(self.save_notes)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        selected_order = self.orders.currentData()
        self.orders.clear()
        for order in self.order_service.list_orders():
            self.orders.addItem(f"{order.order_number} · {order.customer_name}", order.id)
        index = self.orders.findData(selected_order)
        if index >= 0:
            self.orders.setCurrentIndex(index)
        jobs = self.service.list_jobs()
        self.job_ids = [job.id for job in jobs]
        self.table.setRowCount(len(jobs))
        for stage_list in self.stage_lists.values():
            stage_list.clear()
        for row, job in enumerate(jobs):
            values = (
                job.order_number,
                job.customer_name,
                job.stage,
                job.priority,
                job.machine_name,
                job.operator_name,
                job.due_date.isoformat() if job.due_date else "—",
                str(job.wastage_metres),
                f"Paused: {job.pause_reason}" if job.is_paused else "Active",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            self.stage_lists[job.stage].addItem(
                f"{job.order_number} · {job.priority}" + (" · PAUSED" if job.is_paused else "")
            )

    def selected_job(self) -> ProductionJobDetails | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.job_ids):
            return None
        return self.service.get_job(self.job_ids[row])

    def create_job(self) -> None:
        order_id = self.orders.currentData()
        if order_id is None:
            return
        due_date = None
        if self.has_due_date.isChecked():
            selected = self.due_date.date()
            due_date = date(selected.year(), selected.month(), selected.day())
        self.service.create_job(
            ProductionJobInput(
                int(order_id),
                priority=self.priority.currentText(),
                due_date=due_date,
            )
        )
        self.refresh()

    def assign(self) -> None:
        job = self.selected_job()
        if job:
            self.service.assign(
                job.id,
                machine_name=self.machine.text(),
                operator_user_id=self.operator_id.value() or None,
            )
            self.refresh()

    def next_stage(self) -> None:
        job = self.selected_job()
        if not job:
            return
        index = PRODUCTION_STAGES.index(job.stage)
        if index + 1 >= len(PRODUCTION_STAGES):
            return
        try:
            self.service.transition(job.id, PRODUCTION_STAGES[index + 1])
        except InvalidProductionTransition as error:
            QMessageBox.warning(self, "Invalid transition", str(error))
        self.refresh()

    def pause(self) -> None:
        job = self.selected_job()
        if job:
            self._action(lambda: self.service.pause(job.id, self.reason.text()))

    def resume(self) -> None:
        job = self.selected_job()
        if job:
            self._action(lambda: self.service.resume(job.id))

    def reprint(self) -> None:
        job = self.selected_job()
        if job:
            self._action(lambda: self.service.record_reprint(job.id, self.reason.text()))

    def record_wastage(self) -> None:
        job = self.selected_job()
        if not job:
            return
        try:
            metres = Decimal(self.wastage.text())
        except InvalidOperation:
            QMessageBox.warning(self, "Invalid wastage", "Enter a numeric metre value.")
            return
        self._action(lambda: self.service.record_wastage(job.id, metres, self.reason.text()))

    def quality_check(self) -> None:
        job = self.selected_job()
        if not job:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Quality check")
        layout = QFormLayout(dialog)
        print_ok, colour_ok, curing_ok = QCheckBox(), QCheckBox(), QCheckBox()
        notes = QLineEdit()
        layout.addRow("Print quality", print_ok)
        layout.addRow("Colour", colour_ok)
        layout.addRow("Curing", curing_ok)
        layout.addRow("Notes", notes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._action(
                lambda: self.service.record_quality_check(
                    job.id,
                    QualityCheckInput(
                        print_ok.isChecked(),
                        colour_ok.isChecked(),
                        curing_ok.isChecked(),
                        notes.text(),
                    ),
                )
            )

    def save_notes(self) -> None:
        job = self.selected_job()
        if job:
            self._action(lambda: self.service.update_notes(job.id, self.notes.toPlainText()))

    def history(self) -> None:
        job = self.selected_job()
        if job:
            ProductionHistoryDialog(job, self).exec()

    def _action(self, action: Callable[[], object]) -> None:
        try:
            action()
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Production update failed", str(error))
        self.refresh()
