# Codex Master Instructions

You are implementing KMS DTF ERP, a Python 3.12 + PySide6 Windows desktop application.

Rules:
1. Read `docs/PROJECT_BIBLE.md` before editing.
2. Use UI → Service → Repository → Database separation.
3. Do not query the database directly from UI widgets.
4. Do not modify unrelated modules.
5. Do not add dependencies without updating requirements files and explaining the reason.
6. Preserve original artwork files; use bounded previews in the UI.
7. Do not commit secrets, databases, customer artwork, or model weights.
8. Add or update tests for every implemented behavior.
9. Run `pytest`, `ruff check .`, and `black --check .` before completion.
10. Update `CHANGELOG.md` and relevant documentation.
