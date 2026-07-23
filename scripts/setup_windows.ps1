$ErrorActionPreference = "Stop"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

pre-commit install
Write-Host "KMS DTF ERP development environment is ready."
