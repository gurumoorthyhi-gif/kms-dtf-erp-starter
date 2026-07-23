"""Operational reports, consistent SQLite backups, restore, and audit."""

import csv
import hashlib
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from sqlalchemy import Engine, func, select

from app.database import SessionFactory, session_scope
from app.modules.authentication.models import ActivityLog
from app.modules.inventory.models import InventoryMovement
from app.modules.operations.models import AuditRecord, BackupHistory
from app.modules.orders.models import Order
from app.modules.production.models import ProductionJob
from app.modules.sales.models import Invoice
from app.modules.shipping.models import Dispatch


class ReportService:
    REPORTS = (
        "daily sales",
        "monthly sales",
        "production metres",
        "pending orders",
        "completed jobs",
        "wastage",
        "inventory consumption",
        "outstanding payments",
        "customer profitability",
        "order profitability",
        "machine performance",
        "staff activity",
        "dispatch performance",
    )

    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def generate(self, report: str) -> list[dict[str, str]]:
        if report not in self.REPORTS:
            raise ValueError("Unknown report")
        with session_scope(self.factory) as session:
            rows: Any
            if report in ("daily sales", "monthly sales"):
                rows = session.execute(
                    select(Invoice.issue_date, func.sum(Invoice.total))
                    .where(Invoice.document_type == "Invoice")
                    .group_by(Invoice.issue_date)
                )
                return [{"period": str(day), "sales": str(total)} for day, total in rows]
            if report == "pending orders":
                rows = session.scalars(
                    select(Order).where(Order.status.not_in(("Completed", "Cancelled")))
                )
                return [
                    {"order": x.order_number, "status": x.status, "balance": str(x.balance)}
                    for x in rows
                ]
            if report == "completed jobs":
                rows = session.scalars(
                    select(ProductionJob).where(ProductionJob.stage == "Dispatch")
                )
                return [{"job": str(x.id), "order_id": str(x.order_id)} for x in rows]
            if report == "wastage":
                rows = session.scalars(
                    select(ProductionJob).where(ProductionJob.wastage_metres > 0)
                )
                return [{"job": str(x.id), "metres": str(x.wastage_metres)} for x in rows]
            if report == "inventory consumption":
                rows = session.scalars(
                    select(InventoryMovement).where(InventoryMovement.quantity_change < 0)
                )
                return [
                    {"item_id": str(x.inventory_item_id), "quantity": str(-x.quantity_change)}
                    for x in rows
                ]
            if report == "outstanding payments":
                rows = session.scalars(
                    select(Invoice).where(Invoice.balance > 0, Invoice.document_type == "Invoice")
                )
                return [{"invoice": x.document_number, "balance": str(x.balance)} for x in rows]
            if report == "dispatch performance":
                rows = session.scalars(select(Dispatch))
                return [
                    {
                        "dispatch": x.dispatch_number,
                        "status": x.delivery_status,
                        "date": str(x.dispatch_date),
                    }
                    for x in rows
                ]
            if report == "staff activity":
                rows = session.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()))
                return [
                    {"action": x.action, "details": x.details, "date": str(x.created_at)}
                    for x in rows
                ]
            if report == "machine performance":
                rows = session.execute(
                    select(
                        ProductionJob.machine_name,
                        func.count(ProductionJob.id),
                        func.sum(ProductionJob.wastage_metres),
                    ).group_by(ProductionJob.machine_name)
                )
                return [
                    {
                        "machine": machine or "Unassigned",
                        "jobs": str(jobs),
                        "wastage": str(waste or 0),
                    }
                    for machine, jobs, waste in rows
                ]
            if report in ("customer profitability", "order profitability"):
                rows = session.scalars(select(Order))
                return [
                    {"order": x.order_number, "revenue": str(x.total), "profit": str(x.total)}
                    for x in rows
                ]
            rows = session.scalars(select(ProductionJob))
            return [{"job": str(x.id), "metres": str(Decimal("0"))} for x in rows]

    @staticmethod
    def export_csv(rows: list[dict[str, str]], path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            if rows:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        return path

    @staticmethod
    def export_pdf(rows: list[dict[str, str]], path: Path, title: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = QTextDocument()
        document.setHtml(f"<h1>{title}</h1><pre>{json.dumps(rows, indent=2)}</pre>")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(path))
        document.print_(printer)
        return path


class BackupService:
    def __init__(
        self, engine: Engine, factory: SessionFactory, backup_root: Path, cloud_service=None
    ) -> None:
        self.engine, self.factory = engine, factory
        self.backup_root, self.cloud_service = backup_root.resolve(), cloud_service
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create(self, backup_type: str = "manual", cloud: bool = False) -> BackupHistory:
        target = self.backup_root / f"kms-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        source_path = Path(self.engine.url.database or "").resolve()
        source = sqlite3.connect(source_path)
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        verified = self.verify(target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        cloud_key = ""
        if verified and cloud and self.cloud_service:
            cloud_key = self.cloud_service.queue_upload(target, "orders/").object_key
        with session_scope(self.factory) as session:
            history = BackupHistory(
                backup_path=str(target),
                backup_type=backup_type,
                size_bytes=target.stat().st_size,
                checksum_sha256=digest,
                verified=verified,
                cloud_object_key=cloud_key,
            )
            session.add(history)
            session.flush()
            history_id = history.id
        return self.history(history_id)

    @staticmethod
    def verify(path: Path) -> bool:
        connection = sqlite3.connect(path)
        try:
            return connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            connection.close()

    def restore(self, backup: Path, destination: Path) -> Path:
        if not self.verify(backup):
            raise ValueError("Backup verification failed")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source, target = sqlite3.connect(backup), sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        if not self.verify(destination):
            raise ValueError("Restored database verification failed")
        return destination

    def history(self, record_id: int) -> BackupHistory:
        with session_scope(self.factory) as session:
            record = session.get(BackupHistory, record_id)
            if not record:
                raise LookupError("Backup history not found")
            return record


class AuditService:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def record(
        self,
        action: str,
        entity_type: str,
        entity_id: str = "",
        *,
        before=None,
        after=None,
        details="",
        actor_user_id=None,
    ) -> AuditRecord:
        if action not in ("create", "update", "delete", "payment", "order_status", "settings"):
            raise ValueError("Invalid audit action")
        with session_scope(self.factory) as session:
            item = AuditRecord(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_json=json.dumps(before or {}, sort_keys=True),
                after_json=json.dumps(after or {}, sort_keys=True),
                details=details,
            )
            session.add(item)
            session.flush()
            item_id = item.id
        return self.get(item_id)

    def get(self, item_id: int) -> AuditRecord:
        with session_scope(self.factory) as session:
            item = session.get(AuditRecord, item_id)
            if not item:
                raise LookupError("Audit record not found")
            return item

    def list(self) -> list[AuditRecord]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(select(AuditRecord).order_by(AuditRecord.created_at.desc()))
            )
