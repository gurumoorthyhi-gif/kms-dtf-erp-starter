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

## First run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python run.py
```

## First administrator

After installing dependencies, create the initial administrator from the project
root. The password is requested securely and is never accepted as a command-line
argument:

```powershell
python -m scripts.seed_admin --username admin --full-name "System Administrator"
```
