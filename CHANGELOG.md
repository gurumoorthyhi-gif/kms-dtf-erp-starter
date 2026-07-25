# Changelog

## Unreleased

- Added the supplied KMS DTF ERP icon set to application navigation with
  transparent symbol backgrounds and glass-style active states.
- Added responsive shell sizing, compact header controls, and scrollable navigation
  so icons and labels remain separated in small, maximized, and restored windows.
- Removed the sidebar collapse alignment jump, centered collapsed navigation icons,
  restored a font-independent password eye button, and packaged the Windows
  credential backend used by Remember me.
- Replaced hover expansion with a glass-style arrow below the KMS logo and shifted
  collapsed navigation icons slightly left for improved visual alignment.
- Aligned each active glass selection with its icon and tightened the logo-to-arrow
  spacing in the collapsed sidebar.
- Widened the collapsed sidebar and standardized compact navigation buttons to a
  square glass selection footprint.
- Added the supplied KMS logo, centered the painted toggle arrow, and balanced the
  vertical logo-to-arrow and arrow-to-Dashboard spacing.
- Split the collapsed sidebar into centered icon and scrollbar lanes, aligned the
  logo and toggle to the icon lane, and applied the KMS logo to application icons.
- Moved the scrollbar lane farther right while preserving the established icon
  centerline and equalizing the visual gap beside navigation selections.
- Rebuilt the navigation to match the supplied dark glass reference with a narrow
  icon rail, gradient symbol tiles, compact label rows, active pill, and fixed
  bottom double-chevron control.

## 1.0.0

- Prepared the tested Windows x64 release, installer/uninstaller, shortcuts,
  upgrade-safe metadata, application icon, profiling, and release documentation.
- Deferred measured heavy image/UI imports until application launch.

## 0.1.0

- Initialized project structure.
- Added configuration, dependency, Git, and documentation foundations.
- Fixed Windows CI test discovery by invoking pytest through Python.
- Added typed environment settings, runtime directory initialization, and rotating logs.
- Added the SQLAlchemy session, health-check, and Alembic migration foundations.
- Completed Phase 2 with centralized path resolution and global exception handling.
- Added the Phase 3 Qt Widgets shell with animated navigation and placeholder pages.
- Added Phase 4 authentication, users, roles, permissions, login/logout, and activity logs.
- Added the Phase 5 operational dashboard with service-backed empty states and activity.
- Added Phase 6 customer management with addresses, validation, search, and deactivation.
- Added Phase 7 products and configurable Decimal pricing rules.
- Added Phase 8 order management with multi-item pricing, balances, and status history.
- Added Phase 9 managed artwork storage, previews, metadata, versions, and approvals.
- Added Phase 10 non-destructive Artwork Studio tools with background processing.
- Added Phase 11 separate AI image engine jobs with progress, cancellation, and retry.
- Added Phase 12 gang sheet layouts, nesting tools, metre usage, and 300 DPI export.
- Added Phase 13 production queues, validated stages, quality, wastage, and history.
- Added Phase 14 inventory, stock movements, low-stock warnings, suppliers, purchases,
  and transactional purchase receipts.
- Added Phase 15 quotations, invoices, PDF export, transactional payments, credit
  notes, outstanding balances, and customer/supplier ledgers.
- Added Phase 16 packing lists, package measurements, controlled dispatch, shipping
  labels, proof files, delivery histories, and customer notification events.
- Added Phase 17 provider-neutral cloud storage, local caching, durable offline
  queues, interrupted-transfer retry, synchronization, and progress UI.
- Added Phase 18 provider-neutral WhatsApp and email inboxes, templates, replies,
  forwards, attachments, customer/order links, and conversation history.
- Added Phase 19 reports with CSV/PDF export, consistent verified backups, restore,
  backup history, and append-only audit records.
