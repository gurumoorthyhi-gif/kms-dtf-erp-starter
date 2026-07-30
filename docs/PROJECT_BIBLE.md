# KMS DTF ERP — Project Bible

## Product vision

KMS DTF ERP is a Windows desktop ERP for DTF printing businesses. It provides a
fast, local-first workflow that remains usable during internet interruptions and
can synchronize business files across systems. It is not a RIP application.

The product is designed for an owner plus multiple employees with role-based
permissions, thousands of customers, large artwork libraries, and long-term file
retention.

## Canonical workflow

Customer → Order → Artwork → Approval → Gangsheet → Production → Quality Check →
Packing → Dispatch → Invoice → Payment → Reports

Customers are the entry point. A customer uses a generated `LC` or `CR` prefix
with one shared four-digit sequence. The displayed identity is:

`CODE - BUSINESS NAME - DISTRICT`

## Data and storage strategy

- SQLite is the implemented local operational database.
- SQLAlchemy repositories and Alembic migrations keep a future PostgreSQL or
  Supabase migration possible; Supabase configuration is only a planned backend
  foundation and is not active runtime behavior.
- Backblaze B2 is the implemented private object store for durable files.
- Every upload is copied to a local cache and durable queue before transfer.
- Backblaze credentials are kept in the OS credential vault.
- Google Drive is an optional universal catalogue and customer-sheet integration,
  not the source of truth for large binary files.
- Network synchronization must never block customer creation, folder navigation,
  or other primary UI actions.

## Customer storage contract

Customer creation creates one stable customer root. Opening a customer must not
create a date folder.

The user explicitly selects **Create today's folder** when work begins. Duplicate
dates are rejected locally before cloud work is queued. A created date contains:

- Design
- Gangsheet
- Invoice Copy
- Payment Receipt

Backblaze uses stable object prefixes and marker objects. Google creates the
corresponding folders in a serialized background worker. Date records are stored
in `customer_storage_dates`.

## Architecture rules

The required dependency direction is:

`UI → Service → Repository → Database`

- UI widgets never query ORM models or SQLite directly.
- Services own validation, permissions, workflow, and cloud orchestration.
- Repositories own persistence and transaction boundaries.
- External providers remain behind integration/provider adapters.
- Secrets never enter customer records, source control, or logs.
- Original artwork is preserved; edits and replacements create versions.
- Slow file, Google, AI, email, and network operations run outside the UI thread.

## UI contract

- PySide6 Qt Widgets only.
- Premium dark/light glassmorphism.
- Permanently collapsed 78 px navigation rail.
- Transparent navigation icons with neon selected and hover states.
- One reusable animated tooltip; the rail never expands and has no pin behavior.
- The rail includes a separate Image Editor destination. Its initial page is a
  presentation shell with named tool rows, canvas, and Layers/Channels
  inspector; individual tools are not implemented yet.
- Image Editor Open/Save routes through managed customer folders; Import uses a
  local file picker. The canvas initially displays images at 100% native
  resolution and preserves source bytes when saving an unedited image.
- Universal Google Drive button at the bottom-right of the application.
- **Open folder** launches a separate full-screen customer file window while the
  Customers list remains open behind it.
- File-window order is **Folder tree → Items → Preview** with adjustable
  splitters. The folder panel navigates upward from dated folders to the customer
  folder and then to the main Customers folder.
- Images use Qt image decoding; PDFs use the embedded Qt PDF viewer.
- Missing preview files download from Backblaze in the background.

## Security and access

- Development mode may start a development administrator session; production uses
  authenticated users.
- Passwords use versioned scrypt hashes.
- Roles and permissions are enforced in services.
- Backblaze buckets remain private and access uses temporary signed URLs.
- Google OAuth tokens, Backblaze application keys, `.env`, databases, artwork,
  caches, and customer files are never committed.

## Scale and performance rules

- Do not create empty daily folders automatically.
- Coalesce Google Sheet updates and deduplicate folder provisioning.
- Serialize Google operations to protect state files and API quotas.
- Queue Backblaze transfers immediately and synchronize in a background worker.
- Keep stable identifiers independent of editable customer names.
- Lists, searches, and filters must be database-backed and suitable for at least
  1,000 customers.

## Source-of-truth documents

- `docs/REQUIREMENTS.md`: functional and non-functional requirements.
- `docs/architecture/ARCHITECTURE.md`: component and runtime architecture.
- `docs/database/DATABASE_SCHEMA.md`: implemented schema and migrations.
- `docs/ui/UI_DESIGN_SYSTEM.md`: visual and interaction rules.
- `USER_MANUAL.md`: operator behavior.
- `DEPLOYMENT.md`: Windows build, configuration, upgrade, and recovery.

## Git and quality rules

- Use a feature/agent branch and preserve unrelated user changes.
- Add or update tests for behavior changes.
- Run the full test suite, Ruff, Black, compilation, and diff validation before a
  release.
- Never commit secrets or runtime business data.
- Update the changelog and affected source-of-truth documents with every material
  change.
