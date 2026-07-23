"""WhatsApp shared inbox and email inbox."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.modules.communications import CommunicationService


class CommunicationInboxPage(QWidget):
    def __init__(
        self, service: CommunicationService, title: str, *, auto_refresh: bool = True
    ) -> None:
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        compose = QHBoxLayout()
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Recipient")
        self.subject = QLineEdit()
        self.subject.setPlaceholderText("Subject")
        self.body = QTextEdit()
        self.body.setPlaceholderText(f"Write {title} message")
        send, receive = QPushButton("Send"), QPushButton("Receive")
        compose.addWidget(self.recipient)
        compose.addWidget(self.subject)
        compose.addWidget(self.body, 1)
        compose.addWidget(send)
        compose.addWidget(receive)
        layout.addLayout(compose)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Direction", "From", "To", "Subject", "Message", "Customer", "Order"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        send.clicked.connect(self.send)
        receive.clicked.connect(self.receive)
        if auto_refresh:
            self.refresh()

    def send(self) -> None:
        try:
            self.service.send(
                self.recipient.text(), self.body.toPlainText(), subject=self.subject.text()
            )
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Message not sent", str(error))
        self.refresh()

    def receive(self) -> None:
        try:
            self.service.receive()
        except RuntimeError as error:
            QMessageBox.warning(self, "Inbox unavailable", str(error))
        self.refresh()

    def refresh(self) -> None:
        messages = self.service.history()
        self.table.setRowCount(len(messages))
        for row, message in enumerate(messages):
            values = (
                message.direction,
                message.sender,
                message.recipient,
                message.subject,
                message.body,
                str(message.customer_id or ""),
                str(message.order_id or ""),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))


class WhatsAppInboxPage(CommunicationInboxPage):
    def __init__(self, service: CommunicationService, *, auto_refresh: bool = True) -> None:
        super().__init__(service, "WhatsApp", auto_refresh=auto_refresh)


class EmailInboxPage(CommunicationInboxPage):
    def __init__(self, service: CommunicationService, *, auto_refresh: bool = True) -> None:
        super().__init__(service, "email", auto_refresh=auto_refresh)
