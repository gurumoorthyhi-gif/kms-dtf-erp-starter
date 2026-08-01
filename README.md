# KMS DTF ERP

Windows desktop ERP for DTF printing businesses, with a local-first database,
private Backblaze file storage, optional Google Drive catalogue, and a
glassmorphism PySide6 interface.

## Current workflow

Customer → Order → Artwork → Approval → Gangsheet → Production → Quality Check →
Packing → Dispatch → Invoice → Payment → Reports

The application starts maximized. Customers are the primary workflow entry after
Dashboard. Customer files are managed through an in-page workspace:

`Folder tree → File items → Image/PDF preview`

Date folders are created explicitly only when work begins, avoiding thousands of
empty folders.

The integrated multi-document Image Editor opens and saves managed customer
images and provides fit/zoom/pan, physical or pixel sizing, DPI metadata,
persistent rotation, per-document history, Trim, outward/inward Crop, off-canvas
Select transforms, a round transparent Eraser, and tolerance/contiguous Magic
Eraser.

## Implemented technology

- Python 3.12
- PySide6 / Qt Widgets / Qt PDF
- SQLite + SQLAlchemy 2
- Alembic migrations (`0001`–`0023`)
- Pillow and OpenCV
- Backblaze B2 through the S3-compatible API (`boto3`)
- Google Drive and Sheets APIs
- Keyring / Windows Credential Manager

## Storage model

- SQLite: operational business records.
- Local cache: offline-safe upload staging and previews.
- Backblaze B2: private durable binary storage.
- Google Drive: optional customer folders, Customer Master Sheet, and
  metadata-only catalogue entries.
- Supabase: planned hosted backend; not active in the current desktop runtime.

Customer and folder navigation never waits for cloud APIs. Backblaze transfers,
Google provisioning, Sheet updates, and remote preview downloads use background
workers.

## First run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python run.py
```

Development mode starts a development administrator session. Production mode
uses the login page.

## Backblaze setup

Create a private B2 bucket and a bucket-scoped Read/Write application key. In
Settings enter:

- S3 endpoint, for example `https://s3.eu-central-003.backblazeb2.com`;
- bucket name;
- application Key ID;
- application key.

Test and save the connection. The secret is stored in Windows Credential Manager,
not in the database or settings JSON.

## Google Drive

Use the universal bottom-right Google Drive button. OAuth creates the DTF ERP root
folders and Customer Master Sheet. A published third-party shortcut gateway is
still required before Drive catalogue entries can open Backblaze files directly
outside the ERP.

## Validation

```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m compileall -q app
```

Windows builds use `scripts\build_windows.ps1`.

## Documentation

- [Project Bible](docs/PROJECT_BIBLE.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Database schema](docs/database/DATABASE_SCHEMA.md)
- [UI design system](docs/ui/UI_DESIGN_SYSTEM.md)
- [User manual](USER_MANUAL.md)
- [Deployment](DEPLOYMENT.md)
- [Release checklist](RELEASE_CHECKLIST.md)
- [Codex reconstruction commands](CODEX_COMMANDS.md)

## Version

Current release identity: **1.0.0**. Active work after 1.0.0 is documented under
the Unreleased changelog section.
