$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

python -m pytest
python -m ruff check .
python -m black --check .
python scripts\generate_icon.py
python -m PyInstaller --noconfirm kms_dtf_erp.spec

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    throw "Inno Setup 6 is required to build the installer (ISCC.exe not found)."
}
& $iscc.Source "installer\KMS_DTF_ERP.iss"
