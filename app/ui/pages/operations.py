"""Reports, backup/restore, and audit workspace."""

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.operations import AuditService, BackupService, ReportService


class OperationsPage(QWidget):
    def __init__(self, reports: ReportService, backups: BackupService, audit: AuditService) -> None:
        super().__init__()
        self.reports, self.backups, self.audit = reports, backups, audit
        self.rows: list[dict[str, str]] = []
        layout = QVBoxLayout(self)
        tools = QHBoxLayout()
        self.report = QComboBox()
        self.report.addItems(ReportService.REPORTS)
        generate, csv, pdf = (
            QPushButton("Generate"),
            QPushButton("Export CSV"),
            QPushButton("Export PDF"),
        )
        backup, restore = QPushButton("Backup now"), QPushButton("Restore wizard")
        for widget in (self.report, generate, csv, pdf, backup, restore):
            tools.addWidget(widget)
        layout.addLayout(tools)
        self.table = QTableWidget(0, 1)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        generate.clicked.connect(self.generate)
        csv.clicked.connect(lambda: self.export("csv"))
        pdf.clicked.connect(lambda: self.export("pdf"))
        backup.clicked.connect(lambda: self.backups.create())
        restore.clicked.connect(self.restore)

    def generate(self) -> None:
        self.rows = self.reports.generate(self.report.currentText())
        headers = list(self.rows[0]) if self.rows else ["No data"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for row, values in enumerate(self.rows):
            for column, key in enumerate(headers):
                self.table.setItem(row, column, QTableWidgetItem(values[key]))

    def export(self, kind: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export report", f"report.{kind}")
        if path and kind == "csv":
            self.reports.export_csv(self.rows, Path(path))
        elif path:
            self.reports.export_pdf(self.rows, Path(path), self.report.currentText())

    def restore(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self, "Select verified backup", filter="Database (*.db)"
        )
        if not source:
            return
        target, _ = QFileDialog.getSaveFileName(self, "Restore database as", "restored.db")
        if target:
            self.backups.restore(Path(source), Path(target))
