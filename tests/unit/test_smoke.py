def test_project_imports() -> None:
    from app.main import MainWindow

    assert MainWindow is not None
