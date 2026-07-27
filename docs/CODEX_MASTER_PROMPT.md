# Codex Master Instructions

You are maintaining KMS DTF ERP, a Python 3.12 + PySide6 Windows desktop
application.

Before editing:

1. Read `docs/PROJECT_BIBLE.md`, `docs/REQUIREMENTS.md`, and the relevant
   architecture/database/UI document.
2. Inspect Git status and preserve unrelated user changes.
3. Verify whether requested behavior is implemented, planned, or external
   deployment work.

Implementation rules:

1. Preserve `UI → Service → Repository → Database` separation.
2. UI widgets must not query ORM models or SQLite directly.
3. Customer creation and folder navigation must never perform synchronous cloud
   calls.
4. Backblaze files must enter the local cache/queue before transfer.
5. Google mutations must remain serialized and deduplicated.
6. Opening a customer must not create a date; only **Create today's folder** may
   do so, and duplicate dates must stop locally.
7. Preserve original artwork and use versioned replacement.
8. Keep Backblaze private; never expose application keys or permanent public URLs.
9. Keep secrets, databases, OAuth tokens, customer files, previews, and caches out
   of Git and installers.
10. Add/update tests for every behavior change and add an Alembic migration for
    every schema change.
11. Update `CHANGELOG.md` and all affected source-of-truth documents.

UI rules:

- The sidebar remains permanently collapsed at 78 px.
- Do not add pin/unpin or width expansion.
- Use transparent icon backgrounds and neon hover/selected states.
- The universal Google Drive button remains bottom-right.
- Customer workspace stays in-page and uses Folder tree → Items → Preview.
- Image/PDF previews must remain asynchronous for uncached remote files.

Completion checks:

```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m compileall -q app
git diff --check
```

Report completed behavior, validation, remaining deployment dependencies, and
whether changes were pushed.
