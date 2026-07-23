# Windows Deployment

## Build prerequisites

- Windows 10/11 x64
- Python 3.12
- Inno Setup 6 (`ISCC.exe` on `PATH`)
- Development dependencies from `requirements-dev.txt`

Run `scripts\build_windows.ps1`. It runs tests and static checks, creates the
PyInstaller application, then produces the Inno Setup installer under
`installer-output`.

## Clean installation

Run `KMS-DTF-ERP-Setup-1.0.0.exe`. The installer creates Start Menu and optional
desktop shortcuts. The uninstaller is registered with Windows.

## Configuration and secrets

Copy `.env.example` to `.env` beside the deployed working configuration and add
provider credentials locally. Never package `.env`, databases, backups, logs,
cloud cache, artwork, or customer uploads.

## Upgrade

1. Create and verify a manual backup.
2. Exit the application.
3. Run the newer installer. Its stable AppId upgrades in place.
4. Start the application; Alembic applies forward migrations.
5. Verify login, database health, and a representative order.

Application data lives outside the installation payload and is not removed by
uninstall. Downgrades are unsupported; restore the pre-upgrade backup instead.

## Recovery

Use the restore wizard to create a verified restored database, close the
application, replace the configured SQLite database, and restart. Retain the
original database until verification is complete.
