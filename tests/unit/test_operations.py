import sqlite3
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.database import Base, create_database_engine, create_session_factory
from app.modules.customers import models as customer_models
from app.modules.gang_sheets import models as gang_sheet_models
from app.modules.operations import AuditService, BackupService, ReportService
from app.modules.products import models as product_models

_ = (customer_models, product_models, gang_sheet_models)


@pytest.fixture
def operations(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'application.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield (
        ReportService(factory),
        BackupService(engine, factory, tmp_path / "backups"),
        AuditService(factory),
        engine,
        tmp_path,
    )
    engine.dispose()


def test_all_reports_generate_and_export_csv_pdf(operations, qapp: QApplication) -> None:
    reports, _, _, _, tmp_path = operations
    for name in reports.REPORTS:
        assert isinstance(reports.generate(name), list)
    csv_path = reports.export_csv([{"sales": "100"}], tmp_path / "report.csv")
    pdf_path = reports.export_pdf([{"sales": "100"}], tmp_path / "report.pdf", "Sales")
    assert "sales" in csv_path.read_text(encoding="utf-8-sig")
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_consistent_backup_verification_history_and_restore(operations) -> None:
    _, backups, _, _, tmp_path = operations
    history = backups.create()
    assert history.verified is True
    assert len(history.checksum_sha256) == 64
    restored = backups.restore(Path(history.backup_path), tmp_path / "restored.db")
    assert backups.verify(restored)
    connection = sqlite3.connect(restored)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        connection.close()
    assert "orders" in tables


def test_corrupt_backup_is_rejected(operations) -> None:
    _, backups, _, _, tmp_path = operations
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not sqlite")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        backups.restore(corrupt, tmp_path / "unsafe.db")


def test_audit_records_are_append_only(operations) -> None:
    _, _, audit, _, _ = operations
    item = audit.record(
        "payment",
        "invoice",
        "INV-1",
        before={"balance": "100"},
        after={"balance": "50"},
        details="Part payment",
    )
    assert item.before_json == '{"balance": "100"}'
    assert audit.list()[0].id == item.id
    assert not hasattr(audit, "update") and not hasattr(audit, "delete")
