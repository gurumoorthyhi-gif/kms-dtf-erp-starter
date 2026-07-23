"""Login page backed exclusively by the authentication service."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.modules.authentication import (
    AuthenticatedUser,
    AuthenticationError,
    AuthenticationService,
)
from app.ui.components.effects import apply_soft_shadow


class LoginPage(QWidget):
    """Credential form with no direct persistence access."""

    login_succeeded = Signal(object)

    def __init__(
        self,
        authentication_service: AuthenticationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._authentication_service = authentication_service

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 38, 42, 38)
        card_layout.setSpacing(14)

        title = QLabel("Welcome back")
        title.setObjectName("loginTitle")
        subtitle = QLabel("Sign in to continue to KMS DTF ERP")
        subtitle.setObjectName("pageSubtitle")

        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText("Username")
        self.username_input.setAccessibleName("Username")

        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setPlaceholderText("Password")
        self.password_input.setAccessibleName("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.error_label = QLabel("")
        self.error_label.setObjectName("loginError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        self.login_button = QPushButton("Sign in")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self.submit)
        self.password_input.returnPressed.connect(self.submit)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(self.login_button)

        page_layout.addStretch()
        page_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        page_layout.addStretch()
        apply_soft_shadow(card)

    def submit(self) -> None:
        """Authenticate through the service and publish a safe identity."""

        self.error_label.setVisible(False)
        try:
            user = self._authentication_service.authenticate(
                self.username_input.text(),
                self.password_input.text(),
            )
        except AuthenticationError as error:
            self.password_input.clear()
            self.error_label.setText(str(error))
            self.error_label.setVisible(True)
            return

        self.password_input.clear()
        self.login_succeeded.emit(user)

    def reset(self) -> None:
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.clear()
        self.error_label.setVisible(False)

    def authenticated_user(self) -> AuthenticatedUser | None:
        """Expose current identity only for presentation-state checks."""

        return self._authentication_service.current_session.user
