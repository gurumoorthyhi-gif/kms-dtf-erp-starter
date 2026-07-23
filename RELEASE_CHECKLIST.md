# Version 1.0.0 Release Checklist

- [ ] Full tests, Ruff, Black and Mypy pass
- [ ] All Alembic migrations apply to a blank database
- [ ] Backup, integrity verification and restore pass
- [ ] Startup profile recorded; optimizations tied to measured results
- [ ] Disconnected cloud and interrupted upload recovery pass
- [ ] Unavailable AI and communication providers fail safely
- [ ] Large PNG/TIFF workflows tested on representative production files
- [ ] PyInstaller executable launches on clean Windows x64
- [ ] Installer, desktop shortcut and Start Menu shortcut work
- [ ] Upgrade preserves the configured database and local files
- [ ] Uninstaller leaves business data intact
- [ ] `.env`, credentials, databases and customer files absent from build
- [ ] Version displays as 1.0.0
- [ ] README, user manual, deployment guide and changelog reviewed
- [ ] Git tag `v1.0.0` points to the approved main commit
