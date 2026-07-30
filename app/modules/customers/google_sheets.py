"""One-click Google Drive provisioning and customer-sheet synchronization."""

from __future__ import annotations

import json
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from app.modules.customers.models import Customer
    from app.modules.customers.repository import CustomerRepository

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
SPREADSHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
THIRD_PARTY_SHORTCUT_MIME_TYPE = "application/vnd.google-apps.drive-sdk"
ROOT_FOLDER_NAME = "DTF ERP"
CHILD_FOLDER_NAMES = ("CUSTOMERS", "ORDERS", "DESIGN", "REPORTS")
CUSTOMER_SHEET_NAME = "CUSTOMER MASTER"
CUSTOMER_CONTENT_FOLDERS = (
    "DESIGN",
    "GANGSHEET",
    "INVOICE COPY",
    "PAYMENT RECEIPT",
)

CUSTOMER_HEADERS = (
    "customer_identifier",
    "id",
    "code",
    "name",
    "business_name",
    "phone",
    "whatsapp_number",
    "email",
    "gst_number",
    "notes",
    "is_active",
    "created_at",
    "updated_at",
    "delivery_type",
    "preferred_courier",
    "other_transport_name",
    "preferred_rate",
    "billing_door_no",
    "billing_street",
    "billing_village_city",
    "billing_landmark",
    "billing_pincode",
    "billing_district",
    "billing_state",
    "billing_country",
    "shipping_door_no",
    "shipping_street",
    "shipping_village_city",
    "shipping_landmark",
    "shipping_pincode",
    "shipping_district",
    "shipping_state",
    "shipping_country",
    "storage_prefix",
    "google_drive_folder_id",
)


class CustomerSyncError(RuntimeError):
    """Raised when Google authorization, provisioning, or synchronization fails."""


class GoogleCustomerSheetSync:
    def __init__(
        self,
        repository: CustomerRepository,
        *,
        credentials_path: Path,
        token_path: Path,
        state_path: Path,
    ) -> None:
        self._repository = repository
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._state_path = state_path
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="google-sync")
        self._lock = Lock()
        self._sync_future: Future | None = None
        self._folder_futures: dict[tuple[str, str], Future] = {}

    @property
    def is_connected(self) -> bool:
        state = self._load_state()
        return self._token_path.exists() and bool(state.get("spreadsheet_id"))

    @property
    def spreadsheet_url(self) -> str | None:
        spreadsheet_id = self._load_state().get("spreadsheet_id")
        if not spreadsheet_id:
            return None
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    @property
    def root_folder_url(self) -> str | None:
        folder_id = self._load_state().get("root_folder_id")
        return f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else None

    def connect(self) -> str:
        """Authorize Gmail, create the Drive structure, and perform the first sync."""

        try:
            credentials = self._credentials(interactive=True)
            state = self._load_state()
            if not state.get("spreadsheet_id"):
                state = self._provision_drive(credentials)
                self._save_state(state)
            self._sync_with_credentials(credentials, state["spreadsheet_id"])
            return self.root_folder_url or ""
        except Exception as error:
            raise CustomerSyncError(
                "Google Drive could not be connected. Confirm the Google account "
                "and permission, then try again."
            ) from error

    def sync(self) -> None:
        """Synchronize only after the user has completed one-click connection."""

        if not self.is_connected:
            return
        try:
            credentials = self._credentials(interactive=False)
            spreadsheet_id = self._load_state()["spreadsheet_id"]
            self._sync_with_credentials(credentials, spreadsheet_id)
        except Exception as error:
            raise CustomerSyncError(
                "Customer data was saved locally, but Google Drive synchronization failed."
            ) from error

    def sync_async(self) -> Future:
        """Queue a coalesced customer-sheet refresh without blocking the UI."""

        with self._lock:
            if self._sync_future is None or self._sync_future.done():
                self._sync_future = self._executor.submit(self.sync)
            return self._sync_future

    def create_storage_catalog_entry(self, cloud_file) -> str:
        """Create a metadata-only Drive entry for a private Backblaze object."""

        if not self.is_connected:
            return ""
        try:
            credentials = self._credentials(interactive=False)
            state = self._load_state()
            parent_id = self._catalog_parent(state, cloud_file.object_key)
            drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
            result = (
                drive.files()
                .create(
                    body={
                        "name": cloud_file.original_name,
                        "mimeType": THIRD_PARTY_SHORTCUT_MIME_TYPE,
                        "parents": [parent_id],
                        "description": ("Stored securely in Backblaze B2. Open with KMS DTF ERP."),
                    },
                    fields="id",
                )
                .execute()
            )
            return str(result["id"])
        except Exception as error:
            raise CustomerSyncError(
                "The file is safe in Backblaze, but its Google Drive catalog "
                "entry could not be created."
            ) from error

    def provision_customer_root(self, folder_name: str) -> str:
        """Create only the permanent customer root folder."""

        if not self.is_connected:
            return ""
        try:
            credentials = self._credentials(interactive=False)
            state = self._load_state()
            drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
            customer_id, _ = self._ensure_customer_root(drive, state, folder_name)
            self._save_state(state)
            return str(customer_id)
        except Exception as error:
            raise CustomerSyncError(
                "Customer was saved, but its Google Drive root could not be created."
            ) from error

    def provision_customer_folders(self, folder_name: str, date_name: str) -> str:
        """Create one explicit date hierarchy and return the date Drive folder ID."""

        if not self.is_connected:
            return ""
        try:
            credentials = self._credentials(interactive=False)
            state = self._load_state()
            drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
            customer_id, customer_state = self._ensure_customer_root(
                drive,
                state,
                folder_name,
            )
            dates = customer_state.setdefault("dates", {})
            date_state = dates.setdefault(date_name, {})
            date_id = date_state.get("folder_id")
            if not date_id:
                date_id = self._create_folder(drive, date_name, parent_id=customer_id)
                date_state["folder_id"] = date_id
            content_ids = date_state.setdefault("folders", {})
            for content_name in CUSTOMER_CONTENT_FOLDERS:
                if not content_ids.get(content_name):
                    content_ids[content_name] = self._create_folder(
                        drive,
                        content_name,
                        parent_id=date_id,
                    )
            self._save_state(state)
            return str(date_id)
        except Exception as error:
            raise CustomerSyncError(
                "Customer was saved, but its Google Drive folders could not be created."
            ) from error

    def provision_customer_root_async(self, folder_name: str) -> Future:
        key = (folder_name, "")
        with self._lock:
            future = self._folder_futures.get(key)
            if future is None or future.done():
                future = self._executor.submit(self.provision_customer_root, folder_name)
                self._folder_futures[key] = future
            return future

    def provision_customer_folders_async(self, folder_name: str, date_name: str) -> Future:
        """Provision one hierarchy in the serialized Google worker."""

        key = (folder_name, date_name)
        with self._lock:
            future = self._folder_futures.get(key)
            if future is None or future.done():
                future = self._executor.submit(
                    self.provision_customer_folders,
                    folder_name,
                    date_name,
                )
                self._folder_futures[key] = future
            return future

    @staticmethod
    def _ensure_customer_root(drive, state, folder_name: str):
        customers_id = state["folder_ids"]["CUSTOMERS"]
        customer_folders = state.setdefault("customer_folders", {})
        customer_state = customer_folders.setdefault(folder_name, {})
        customer_id = customer_state.get("folder_id")
        if not customer_id:
            customer_id = GoogleCustomerSheetSync._create_folder(
                drive,
                folder_name,
                parent_id=customers_id,
            )
            customer_state["folder_id"] = customer_id
        return customer_id, customer_state

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    @staticmethod
    def _catalog_parent(state: dict[str, Any], object_key: str) -> str:
        folders = state.get("folder_ids", {})
        parts = object_key.split("/")
        prefix = parts[0]
        if prefix == "customers" and len(parts) >= 5:
            customer_state = state.get("customer_folders", {}).get(parts[1], {})
            date_state = customer_state.get("dates", {}).get(parts[2], {})
            content_name = {
                "design": "DESIGN",
                "gangsheet": "GANGSHEET",
                "invoice-copy": "INVOICE COPY",
                "payment-receipt": "PAYMENT RECEIPT",
            }.get(parts[3])
            content_id = date_state.get("folders", {}).get(content_name)
            if content_id:
                return str(content_id)
        folder_name = {
            "customers": "CUSTOMERS",
            "orders": "ORDERS",
            "artwork": "DESIGN",
            "gang-sheets": "DESIGN",
        }.get(prefix, "REPORTS")
        return str(folders.get(folder_name) or state["root_folder_id"])

    def _credentials(self, *, interactive: bool) -> Credentials:
        credentials: Credentials | None = None
        if self._token_path.exists():
            candidate = Credentials.from_authorized_user_file(self._token_path)
            if DRIVE_FILE_SCOPE in (candidate.scopes or ()):
                credentials = candidate
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            if not interactive:
                raise CustomerSyncError("Google Drive needs to be connected again.")
            credentials_path = self._resolved_credentials_path()
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                [DRIVE_FILE_SCOPE],
            )
            credentials = flow.run_local_server(port=0)
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def _resolved_credentials_path(self) -> Path:
        if self._credentials_path.exists():
            return self._credentials_path
        bundle_root = getattr(sys, "_MEIPASS", None)
        bundled = Path(bundle_root) / "google" / "google_oauth_client.json" if bundle_root else None
        if bundled is not None and bundled.exists():
            return bundled
        raise FileNotFoundError("The application Google credential is missing.")

    def _provision_drive(self, credentials: Credentials) -> dict[str, Any]:
        drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        root_id = self._create_folder(drive, ROOT_FOLDER_NAME, parent_id=None)
        folder_ids = {
            name: self._create_folder(drive, name, parent_id=root_id) for name in CHILD_FOLDER_NAMES
        }
        sheet = (
            drive.files()
            .create(
                body={
                    "name": CUSTOMER_SHEET_NAME,
                    "mimeType": SPREADSHEET_MIME_TYPE,
                    "parents": [folder_ids["CUSTOMERS"]],
                },
                fields="id,webViewLink",
            )
            .execute()
        )
        sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        metadata = (
            sheets.spreadsheets()
            .get(spreadsheetId=sheet["id"], fields="sheets.properties")
            .execute()
        )
        first_sheet_id = metadata["sheets"][0]["properties"]["sheetId"]
        (
            sheets.spreadsheets()
            .batchUpdate(
                spreadsheetId=sheet["id"],
                body={
                    "requests": [
                        {
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": first_sheet_id,
                                    "title": CUSTOMER_SHEET_NAME,
                                },
                                "fields": "title",
                            }
                        }
                    ]
                },
            )
            .execute()
        )
        return {
            "root_folder_id": root_id,
            "folder_ids": folder_ids,
            "spreadsheet_id": sheet["id"],
        }

    @staticmethod
    def _create_folder(drive, name: str, *, parent_id: str | None) -> str:
        body: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME_TYPE}
        if parent_id is not None:
            body["parents"] = [parent_id]
        result = drive.files().create(body=body, fields="id").execute()
        return result["id"]

    def _sync_with_credentials(
        self,
        credentials: Credentials,
        spreadsheet_id: str,
    ) -> None:
        sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        customers = self._repository.search(active=None)
        values = [list(CUSTOMER_HEADERS), *[self._customer_row(item) for item in customers]]
        target_range = f"'{CUSTOMER_SHEET_NAME}'!A:AI"
        (
            sheets.spreadsheets()
            .values()
            .clear(spreadsheetId=spreadsheet_id, range=target_range, body={})
            .execute()
        )
        (
            sheets.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=f"'{CUSTOMER_SHEET_NAME}'!A1",
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute()
        )

    def _load_state(self) -> dict[str, Any]:
        if not self._state_path.exists():
            return {}
        return json.loads(self._state_path.read_text(encoding="utf-8"))

    def _save_state(self, state: dict[str, Any]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temporary.replace(self._state_path)

    @staticmethod
    def _customer_row(customer: Customer) -> list[object]:
        addresses = {address.address_type: address for address in customer.addresses}
        billing = addresses.get("billing")
        shipping = addresses.get("shipping")
        business = (customer.business_name or customer.name or "CUSTOMER").strip().upper()
        district = (
            (billing.district if billing is not None and billing.district else "DISTRICT")
            .strip()
            .upper()
        )

        def address_values(address) -> list[str]:
            if address is None:
                return [""] * 8
            return [
                address.line1,
                address.line2,
                address.city,
                address.landmark,
                address.postal_code,
                address.district,
                address.state,
                address.country,
            ]

        return [
            f"{customer.code} - {business} - {district}",
            customer.id,
            customer.code,
            customer.name,
            customer.business_name,
            customer.phone,
            customer.whatsapp_number,
            customer.email or "",
            customer.gst_number,
            customer.notes,
            customer.is_active,
            customer.created_at.isoformat(),
            customer.updated_at.isoformat(),
            customer.delivery_type,
            customer.preferred_courier,
            customer.other_transport_name,
            str(customer.preferred_rate),
            *address_values(billing),
            *address_values(shipping),
            customer.storage_prefix,
            customer.google_drive_folder_id,
        ]
