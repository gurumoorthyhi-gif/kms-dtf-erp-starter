from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_communications_migration_creates_conversation_tables(tmp_path: Path) -> None:
    url = "sqlite:///communications.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)
    assert {
        "communication_messages",
        "communication_attachments",
        "message_templates",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()
