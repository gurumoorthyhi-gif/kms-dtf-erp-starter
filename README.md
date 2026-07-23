# KMS DTF ERP

A Windows desktop ERP for DTF printing businesses.

## Core workflow

Customer → Order → Artwork → Approval → Gang Sheet → Production → Quality Check → Packing → Dispatch → Payment → Reports

## Technology

- Python 3.12
- PySide6 / Qt Widgets
- SQLite + SQLAlchemy
- Alembic migrations
- Pillow and OpenCV

## Version

Current production release: **1.0.0**

## First run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python run.py
```

Run validation with `python -m pytest`. Windows release builds use
`scripts\build_windows.ps1`; see [DEPLOYMENT.md](DEPLOYMENT.md) for prerequisites,
upgrade and recovery procedures. Runtime databases, customer files and `.env`
credentials are never included in the installer.

## Documentation

- [User manual](USER_MANUAL.md)
- [Deployment and upgrade](DEPLOYMENT.md)
- [Release checklist](RELEASE_CHECKLIST.md)

## First administrator

After installing dependencies, create the initial administrator from the project
root. The password is requested securely and is never accepted as a command-line
argument:

```powershell
python -m scripts.seed_admin --username admin --full-name "System Administrator"
```
