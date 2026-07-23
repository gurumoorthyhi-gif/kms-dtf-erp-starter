from PyInstaller.utils.hooks import collect_data_files

datas = [("assets/kms_dtf_erp.svg", "assets")] + collect_data_files("alembic")

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["app.database.migrations.env"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "mypy", "black", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="KMS_DTF_ERP",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, disable_windowed_traceback=False,
    icon="assets/kms_dtf_erp.ico",
    version="installer/version_info.txt",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="KMS_DTF_ERP")
