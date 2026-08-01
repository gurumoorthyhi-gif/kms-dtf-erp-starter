# Changelog

## Unreleased

- Added a round transparent Eraser with a zoom-aware circular cursor, linked
  1-500 px size slider/value, continuous strokes, and one Undo step per stroke.
- Added a Magic Eraser with 0-255 color tolerance and a default-on Contiguous
  option for connected-region versus image-wide matching-color removal.
- Made `V` reliably activate Select from child canvas controls and retained `C`
  for Crop through page-level key handling.
- Empty-pasteboard clicks now deselect every Image Editor tool and close active
  Crop/Select overlays without consuming image or selection clicks.
- Removed the Crop-dependent top-dimension path: Width/Height always scale the
  complete image, while only the interactive Crop boundary extends canvas.
- Select can now move and enlarge full-canvas artwork beyond image bounds while
  retaining its true off-canvas transform rectangle.
- Width/Height update their locked partner live, DPI is displayed with pixel and
  physical print size and saved as metadata, and absolute per-document rotation
  persists through edits, tab changes, Undo, and Redo.
- Improved Select performance with lightweight live overlay transforms,
  copy-on-write history, cached alpha bounds, and single resampling on release.

- Added multi-select managed Open and customer-browser design import, with each
  opened image using an independent closable and movable document tab.
- Newly opened images now fit fully inside the canvas while remaining capped at
  100% zoom so smaller source images are never enlarged automatically.
- Image Editor document tabs now follow the application Dark/Light theme and
  participate in the animated theme transition.
- Replaced the Image Editor managed Open/Save picker with a three-pane customer
  browser: folder tree, file details, live preview, and bottom action controls.
- Customer trees now follow creation serial order. The Image Editor browser can
  create the current date folder and import multiple designs directly into its
  Design folder; the standalone editor Import button was removed.
- Customer/date folder trees now start collapsed and expand only the path the
  user chooses or the newly created current-date Design path.
- Added per-tab pixel/canvas Undo and Redo controls at the bottom of Image
  Editor, moved Trim into the left tool panel, and added Ctrl+Z,
  Ctrl+Shift+Z, Ctrl+O, Ctrl+S, and Ctrl+T shortcuts.
- Replaced numeric-only Crop behavior with an interactive canvas overlay using
  eight drag handles, rule-of-thirds guides, shaded outside area, transparent
  extension, explicit Apply/Cancel, and per-tab Undo support.
- Interactive Crop now remains active during mouse-wheel zoom and middle-button
  pan, with its boundary and handles transformed accurately with the canvas.
- Lowered the Image Editor minimum zoom from 10% to 0.5% and added accurate
  sub-1% percentage display in the top bar and document tabs.
- Added `C` to activate Crop and `Enter` to apply the active crop boundary.
- Numeric keypad Enter also confirms and applies the active Crop tool.
- Added a Select tool that detects visible artwork, displays a draggable
  selection boundary, moves or enlarges it beyond the canvas, and performs
  proportional handle transforms with Undo/Redo support.
- Added an Image Editor icon and functional workspace with tool labels, a central
  canvas, document tabs, and Layers/Channels inspector tabs.
- Ordered Image Editor tools from basic to advanced and selected Background
  Remover as the initial tool.
- Added Image Editor Open and Save actions for managed customer folders, local
  Import, and native-resolution canvas display without preview scaling.
- Image Editor Save now replaces the same managed customer file after Open,
  preserving its record identity and folder location.
- Added a Photoshop-style transparency checkerboard to the Image Editor canvas
  and made the unnumbered tool-name rail directly selectable.
- Added canvas zoom in/out, 100%, fit, hand-pan, and image-move controls, plus
  a Crop destination in the Image Editor tool rail.
- Simplified canvas navigation to mouse-wheel zoom and middle-button drag-pan,
  with only the current zoom percentage displayed in the top command bar.
- Matched reference-editor cursor-centred wheel zoom and added live image width
  and height readouts in inches, millimetres, centimetres, or pixels.
- Made Width and Height editable so changes resample the image and are persisted
  on Save, and expanded the canvas workspace for two-axis middle-button panning.
- Added a locked-by-default aspect-ratio control between Width and Height for
  proportional resizing, with an unlock option for independent dimensions.
- Added transparent-edge Trim and interactive Crop bounds for transparent page
  extension or destructive cropping; top Width/Height remain image resampling.
- Separated the Image Editor pasteboard from the image canvas: the non-working
  area is dark, while transparency checks appear only inside editable bounds.
- Replaced the expanding navigation concept with a permanently collapsed
  neon-glass icon rail and reusable hover tooltips.
- Reworked Customers around local/courier numbering, Indian address and pincode
  lookup, preferred courier and rate fields, guarded deletion, and a responsive
  two-column editor.
- Added stable customer storage roots and explicit, duplicate-safe dated work
  folders containing Design, Gangsheet, Invoice Copy, and Payment Receipt.
- Added a separate full-screen customer file workspace ordered as Folder tree,
  Items, and adjustable Preview. Folder-panel navigation moves upward to the
  customer folder and main Customers folder.
- Added asynchronous Backblaze B2 folder, upload, download, and preview
  operations so remote storage does not block the desktop interface.
- Added optional Google Drive catalog and customer-sheet synchronization while
  keeping private binaries in Backblaze and operational records in local SQLite.
- Added database migrations 0020 and 0021 for customer storage roots and dated
  work-folder records.
- Reconciled the project Bible, requirements, architecture, database, UI,
  workflow, deployment, and user documentation with the implemented product.

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
- Added the initial Phase 3 Qt Widgets shell and animated navigation foundation.
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
