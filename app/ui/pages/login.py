"""Login page backed exclusively by the authentication service."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
    CredentialStoreProtocol,
    WindowsCredentialStore,
)
from app.ui.components.effects import apply_soft_shadow


class CreateAdministratorDialog(QDialog):
    """Collect the initial administrator identity without exposing role selection."""

    def __init__(
        self,
        authentication_service: AuthenticationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._authentication_service = authentication_service
        self.setWindowTitle("Create administrator account")
        self.setMinimumWidth(440)
        form = QFormLayout(self)
        self.full_name = QLineEdit()
        self.username = QLineEdit()
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.confirm_password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, field in (
            ("Administrator name", self.full_name),
            ("Username", self.username),
            ("Email (optional)", self.email),
            ("Password", self.password),
            ("Confirm password", self.confirm_password),
        ):
            form.addRow(label, field)
        self.error_label = QLabel()
        self.error_label.setObjectName("loginError")
        self.error_label.setWordWrap(True)
        form.addRow(self.error_label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.create_account)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def create_account(self) -> None:
        if self.password.text() != self.confirm_password.text():
            self.error_label.setText("Passwords do not match")
            return
        if self.email.text() and "@" not in self.email.text():
            self.error_label.setText("Enter a valid email address")
            return
        try:
            self._authentication_service.create_initial_administrator(
                username=self.username.text(),
                password=self.password.text(),
                full_name=self.full_name.text(),
                email=self.email.text() or None,
            )
        except (ValueError, PermissionError) as error:
            self.error_label.setText(str(error))
            return
        self.accept()


class LoginPage(QWidget):
    """Credential form with no direct persistence access."""

    login_succeeded = Signal(object)

    def __init__(
        self,
        authentication_service: AuthenticationService,
        credential_store: CredentialStoreProtocol | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._authentication_service = authentication_service
        self._credential_store = credential_store or WindowsCredentialStore()

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
        self.remember_me = QCheckBox("Remember me on this computer")

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
        card_layout.addWidget(self.remember_me)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(self.login_button)
        self.create_account_button = QPushButton("Create administrator account")
        self.create_account_button.setObjectName("secondaryButton")
        self.create_account_button.clicked.connect(self.open_create_account)
        card_layout.addWidget(self.create_account_button)
        self._update_create_account_visibility()

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

        if self.remember_me.isChecked():
            try:
                self._credential_store.save(
                    self.username_input.text(),
                    self.password_input.text(),
                )
            except (ValueError, RuntimeError) as error:
                self.error_label.setText(str(error))
                self.error_label.setVisible(True)
        else:
            self._credential_store.clear()
        self.password_input.clear()
        self.login_succeeded.emit(user)

    def reset(self) -> None:
        remembered = self._credential_store.load()
        if remembered:
            username, password = remembered
            self.username_input.setText(username)
            self.password_input.setText(password)
            self.remember_me.setChecked(True)
        else:
            self.username_input.clear()
            self.password_input.clear()
            self.remember_me.setChecked(False)
        self.error_label.clear()
        self.error_label.setVisible(False)
        self._update_create_account_visibility()

    def open_create_account(self) -> None:
        dialog = CreateAdministratorDialog(self._authentication_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.username_input.setText(dialog.username.text().strip().casefold())
            self.error_label.setText("Administrator created. Enter the password to sign in.")
            self.error_label.setVisible(True)
            self._update_create_account_visibility()

    def _update_create_account_visibility(self) -> None:
        self.create_account_button.setVisible(
            self._authentication_service.can_create_initial_administrator()
        )

    def authenticated_user(self) -> AuthenticatedUser | None:
        """Expose current identity only for presentation-state checks."""

        return self._authentication_service.current_session.user
