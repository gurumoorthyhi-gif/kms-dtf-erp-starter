from pathlib import Path

from app.version import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_windows_packaging_assets() -> None:
    assert __version__ == "1.0.0"
    for relative in (
        "kms_dtf_erp.spec",
        "installer/KMS_DTF_ERP.iss",
        "scripts/build_windows.ps1",
        "assets/kms_dtf_erp.svg",
        "README.md",
        "USER_MANUAL.md",
        "DEPLOYMENT.md",
        "RELEASE_CHECKLIST.md",
    ):
        assert (ROOT / relative).is_file(), relative


def test_installer_has_stable_upgrade_identity_and_shortcuts() -> None:
    installer = (ROOT / "installer/KMS_DTF_ERP.iss").read_text(encoding="utf-8")
    assert "AppId=" in installer
    assert "{autodesktop}" in installer
    assert "{group}" in installer
    assert '#define MyAppVersion "1.0.0"' in installer


def test_build_and_installer_do_not_include_secrets_or_runtime_data() -> None:
    spec = (ROOT / "kms_dtf_erp.spec").read_text(encoding="utf-8")
    installer = (ROOT / "installer/KMS_DTF_ERP.iss").read_text(encoding="utf-8")
    combined = spec + installer
    for forbidden in (
        '(".env",',
        '"local_data',
        '"backups',
        '"credentials',
        '"*.db',
    ):
        assert forbidden not in combined
