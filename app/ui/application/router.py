"""In-memory page routing for the application shell."""

from PySide6.QtWidgets import QStackedWidget, QWidget


class PageRouter(QStackedWidget):
    """Route named pages without coupling navigation to page implementations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pages: dict[str, QWidget] = {}

    def register_page(self, name: str, page: QWidget) -> None:
        if name in self._pages:
            raise ValueError(f"Page is already registered: {name}")
        self._pages[name] = page
        self.addWidget(page)

    def navigate(self, name: str) -> None:
        try:
            page = self._pages[name]
        except KeyError as error:
            raise KeyError(f"Unknown page: {name}") from error
        self.setCurrentWidget(page)

    @property
    def current_page_name(self) -> str:
        current = self.currentWidget()
        for name, page in self._pages.items():
            if page is current:
                return name
        return ""
