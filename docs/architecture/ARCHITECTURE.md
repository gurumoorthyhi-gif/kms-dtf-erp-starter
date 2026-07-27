# Architecture

## Runtime shape

KMS DTF ERP is a modular Windows desktop application.

```text
PySide6 UI
    ↓
Application services and permission checks
    ↓
Repositories / provider adapters
    ↓
SQLite + local cache + Backblaze B2 + optional Google Drive
```

The current source of truth for structured operational data is local SQLite. The
current source of truth for durable cloud binaries is private Backblaze B2.
Google Drive provides an optional catalogue and customer spreadsheet.

## Startup composition

`app/main.py`:

1. loads typed configuration;
2. resolves and creates runtime directories;
3. configures logging and global exception handling;
4. applies Alembic migrations;
5. creates the SQLAlchemy engine/session factory;
6. composes repositories and services;
7. restores Backblaze configuration from local metadata plus the OS credential
   vault;
8. starts the maximized Qt application.

Development mode starts a development administrator session. Production mode
routes through Login.

## Layers

### UI

`app/ui` contains navigation, themes, dialogs, pages, and preview widgets. It may
call services and consume typed results but must not import ORM models to query
the database.

Customers launches a dedicated full-screen file window while preserving the
customer-list page behind it. The file window uses nested splitters:

`Folder tree | File items | Preview`

The folder pane owns its navigation state and moves upward from a customer's
dated work folders to the customer folder and then the main Customers folder.

### Services

`app/modules/*/service.py` owns validation, permission checks, workflow
transitions, background scheduling, and cross-provider orchestration.

### Repositories

Repositories own SQLAlchemy statements and transaction-scoped sessions. Returned
ORM entities are fully loaded before leaving a session.

### Database

SQLite is configured through a shared engine/session foundation. The code avoids
SQLite-only queries where reasonable, preserving a future hosted PostgreSQL path.
Every schema change is an Alembic revision.

## File storage

`CloudStorageService` writes an upload into the local cache and `cloud_files`
before transfer. Customer uploads request `auto_sync=False`, then schedule the
single cloud worker. This guarantees immediate UI response and ordered retry.

Backblaze uses its S3-compatible API with Signature V4. Provider access supports:

- upload/download;
- connectivity checks scoped to the configured bucket;
- temporary signed download URLs.

Customer storage paths use a stable stored prefix. Explicit date folders are
tracked in `customer_storage_dates`; four marker objects establish the Backblaze
prefixes asynchronously.

## Google integration

`GoogleCustomerSheetSync` owns OAuth token use, root provisioning, Customer
Master updates, customer/date folders, and third-party catalogue entries.

One `ThreadPoolExecutor(max_workers=1)` serializes Google state and API mutation.
Folder tasks are deduplicated by customer/date and Sheet refreshes are coalesced.
Customer root creation is separate from explicit date creation.

## Responsiveness

- Backblaze customer uploads run in a background queue.
- Google folders and Sheet updates run in a serialized background worker.
- Remote previews use Qt's global thread pool.
- Preview results are selection-aware so stale downloads cannot replace the
  current file.
- UI timers refresh queued transfer status without blocking navigation.

## Authentication and permissions

Authentication follows the same layered boundary. Password verification and
activity recording remain below the UI. Pages are hidden according to the
authenticated user's permission set, while services enforce permissions again.

## Configuration and secrets

- Non-secret Backblaze settings: `local_data/storage_settings.json`.
- Backblaze application key: Windows Credential Manager.
- Google OAuth token/state: configured files under `local_data/google`.
- General runtime configuration: `.env`.
- Backend/Supabase placeholders: `.env.backend` (future, server-only).

No runtime secret or business data belongs in the installer or repository.

## Planned hosted architecture

A hosted multi-device backend is not yet active. When implemented, Supabase or
another PostgreSQL service should own tenant/user metadata and stable gateway
authorization, while Backblaze remains the object store. The desktop application
must keep its local cache/offline queue and synchronize through explicit conflict
rules.
