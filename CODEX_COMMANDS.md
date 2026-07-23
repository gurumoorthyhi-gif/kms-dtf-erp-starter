# Commands to paste into Codex

## Task 1 — Validate the foundation

Read `docs/PROJECT_BIBLE.md`, `docs/CODEX_MASTER_PROMPT.md`, and the repository structure. Validate imports, configuration files, and startup. Fix only foundation problems. Ensure `python run.py` opens a basic PySide6 window. Add a smoke test. Run pytest, ruff, and black checks. Update CHANGELOG.md.

## Task 2 — Build configuration and logging

Create typed application settings loaded from `.env`, directory initialization, and Loguru-based rotating logs. Keep configuration under `app/core/config` and logging under `app/core/logging`. Add unit tests. Do not build any business modules yet.

## Task 3 — Build database foundation

Implement SQLAlchemy engine/session management, declarative base, Alembic initialization, and a health check. Use SQLite for development and preserve future compatibility with PostgreSQL/MySQL. Add tests. Do not create customer or order tables yet.

## Task 4 — Build the application shell

Implement the PySide6 main window, page router, glassmorphism theme foundation, top bar, icons-only gradient sidebar, and expand-on-hover behavior. Create only Dashboard and Settings placeholder pages. Keep widgets reusable and avoid business logic in the UI.

## Task 5 — Build authentication foundation

Implement users, roles, permissions, secure password hashing, login/logout, current-user session, and activity logging. Add migrations, repositories, services, UI pages, and tests. Do not build customers or orders.

## Working rule for every task

Before editing, inspect current Git status and relevant files. Work only within the requested scope. At completion, summarize files changed, tests run, remaining risks, and the recommended commit message.
