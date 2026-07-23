from app.main import MainWindow


def test_main_window_opens(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.show()

    assert window.isVisible()
    assert window.windowTitle() == "KMS DTF ERP"
    assert window.centralWidget() is not None
