"""Packing completion, controlled dispatch, labels, and delivery status."""

from datetime import date
from html import escape
from pathlib import Path

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter

from app.modules.authentication import AuthenticationService
from app.modules.shipping.models import Dispatch, Packing
from app.modules.shipping.repository import ShippingRepository
from app.modules.shipping.schemas import (
    DispatchInput,
    DispatchSummary,
    PackingInput,
    PackingSummary,
)

DELIVERY_STATUSES = ("Dispatched", "In Transit", "Out for Delivery", "Delivered", "Returned")


class PackingService:
    def __init__(
        self,
        repository: ShippingRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create(self, data: PackingInput) -> PackingSummary:
        self._require("packing.manage")
        if data.package_count < 1 or data.package_weight <= 0:
            raise ValueError("Package count and weight must be positive")
        return self._summary(
            self.repository.create_packing(
                data.order_id,
                self._number(),
                data.package_count,
                data.package_weight,
                data.notes.strip(),
                self._user_id(),
            )
        )

    def complete(self, packing_id: int) -> PackingSummary:
        self._require("packing.manage")
        return self._summary(self.repository.complete_packing(packing_id))

    def list(self) -> list[PackingSummary]:
        self._require("packing.view")
        return [self._summary(item) for item in self.repository.list_packings()]

    def _number(self) -> str:
        prefix = f"PKG-{date.today():%Y%m%d}-"
        sequence = self.repository.next_sequence(prefix, Packing.packing_number)
        return f"{prefix}{sequence:04d}"

    @staticmethod
    def _summary(item: Packing) -> PackingSummary:
        return PackingSummary(
            item.id,
            item.packing_number,
            item.order_id,
            item.order.order_number,
            item.order.customer.name,
            item.packing_list,
            item.package_count,
            item.package_weight,
            item.is_complete,
        )

    def _require(self, permission: str) -> None:
        if self.authentication_service:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if not self.authentication_service:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None


class DispatchService:
    def __init__(
        self,
        repository: ShippingRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create(self, data: DispatchInput) -> DispatchSummary:
        self._require("dispatch.manage")
        if not data.courier.strip() or not data.tracking_number.strip():
            raise ValueError("Courier and tracking number are required")
        if data.authorized_override:
            self._require("dispatch.override")
        proof = data.proof_of_dispatch_path.strip()
        if proof and not Path(proof).expanduser().is_file():
            raise ValueError("Proof-of-dispatch file does not exist")
        prefix = f"DSP-{date.today():%Y%m%d}-"
        number = f"{prefix}{self.repository.next_sequence(prefix, Dispatch.dispatch_number):04d}"
        return self._summary(
            self.repository.create_dispatch(
                data.packing_id,
                number,
                data.courier.strip(),
                data.tracking_number.strip(),
                str(Path(proof).expanduser().resolve()) if proof else "",
                data.authorized_override,
                self._user_id(),
            )
        )

    def update_delivery(self, dispatch_id: int, status: str, details: str = "") -> DispatchSummary:
        self._require("dispatch.manage")
        if status not in DELIVERY_STATUSES:
            raise ValueError("Invalid delivery status")
        return self._summary(
            self.repository.update_delivery(dispatch_id, status, details.strip(), self._user_id())
        )

    def list(self) -> list[DispatchSummary]:
        self._require("dispatch.view")
        return [self._summary(item) for item in self.repository.list_dispatches()]

    def export_shipping_label(self, dispatch_id: int, destination: Path) -> Path:
        self._require("dispatch.view")
        dispatch = self.repository.get_dispatch(dispatch_id)
        destination = destination.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        document = QTextDocument()
        document.setHtml(
            "<h1>KMS DTF ERP — SHIPPING LABEL</h1>"
            f"<h2>{escape(dispatch.dispatch_number)}</h2>"
            f"<p><b>Customer:</b> {escape(dispatch.order.customer.name)}<br>"
            f"<b>Order:</b> {escape(dispatch.order.order_number)}<br>"
            f"<b>Courier:</b> {escape(dispatch.courier)}<br>"
            f"<b>Tracking:</b> {escape(dispatch.tracking_number)}<br>"
            f"<b>Packages:</b> {dispatch.packing.package_count}<br>"
            f"<b>Weight:</b> {dispatch.packing.package_weight} kg</p>"
        )
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(destination))
        document.print_(printer)
        self.repository.set_label_path(dispatch_id, str(destination))
        return destination

    @staticmethod
    def _summary(item: Dispatch) -> DispatchSummary:
        return DispatchSummary(
            item.id,
            item.dispatch_number,
            item.order.order_number,
            item.order.customer.name,
            item.courier,
            item.tracking_number,
            item.dispatch_date,
            item.delivery_status,
            item.proof_of_dispatch_path,
            item.shipping_label_path,
            tuple(
                (event.from_status, event.to_status, event.details, event.created_at)
                for event in item.events
            ),
        )

    def _require(self, permission: str) -> None:
        if self.authentication_service:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if not self.authentication_service:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None
