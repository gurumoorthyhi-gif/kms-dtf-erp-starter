"""One-click Google Drive provisioning and customer-sheet synchronization."""

from __future__ import annotations

import json
import sys
from pathlib import Path
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

    def connect(self) -> str:
        """Authorize Gmail, create the Drive structure, and perform the first sync."""

        try:
            credentials = self._credentials(interactive=True)
            state = self._load_state()
            if not state.get("spreadsheet_id"):
                state = self._provision_drive(credentials)
                self._save_state(state)
            self._sync_with_credentials(credentials, state["spreadsheet_id"])
            return self.spreadsheet_url or ""
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
                        "description": (
                            "Stored securely in Backblaze B2. Open with KMS DTF ERP."
                        ),
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

    @staticmethod
    def _catalog_parent(state: dict[str, Any], object_key: str) -> str:
        folders = state.get("folder_ids", {})
        prefix = object_key.split("/", 1)[0]
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
        bundled = (
            Path(bundle_root) / "google" / "google_oauth_client.json"
            if bundle_root
            else None
        )
        if bundled is not None and bundled.exists():
            return bundled
        raise FileNotFoundError("The application Google credential is missing.")

    def _provision_drive(self, credentials: Credentials) -> dict[str, Any]:
        drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        root_id = self._create_folder(drive, ROOT_FOLDER_NAME, parent_id=None)
        folder_ids = {
            name: self._create_folder(drive, name, parent_id=root_id)
            for name in CHILD_FOLDER_NAMES
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
        target_range = f"'{CUSTOMER_SHEET_NAME}'!A:AG"
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
            billing.district if billing is not None and billing.district else "DISTRICT"
        ).strip().upper()

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
        ]
