# Codex Reconstruction and Continuing-Development Commands

This document is the implementation handoff for recreating the current KMS DTF
ERP desktop application from this repository. It records the files, contracts,
algorithms, controls, shortcuts, and validation commands behind the implemented
work. It is intentionally more detailed than a normal prompt list.

## 1. Mandatory reading order

Before changing the application, read these files in order:

1. `docs/PROJECT_BIBLE.md` for product and architecture invariants.
2. `docs/REQUIREMENTS.md` for implemented functional requirements.
3. `docs/architecture/ARCHITECTURE.md` and
   `docs/database/DATABASE_SCHEMA.md` for service and persistence boundaries.
4. `docs/ui/UI_DESIGN_SYSTEM.md` for visual and interaction contracts.
5. `USER_MANUAL.md` for operator-visible workflows.
6. `CHANGELOG.md` for delivered behavior.
7. The implementation and tests named in the relevant section below.

Never describe planned behavior as implemented. Preserve unrelated workspace
changes, never commit credentials or customer data, and use forward-only
Alembic migrations for schema changes.

## 2. Application reconstruction map

- Entry point: `app/main.py`.
- Main shell and routing: `app/ui/application/main_window.py`.
- Fixed navigation rail: `app/ui/components/sidebar.py`.
- Theme and branded assets: `app/ui/themes/light.py`, `app/ui/branding.py`,
  `app/ui/icons/gradient.py`, and `assets/`.
- Customer domain: `app/modules/customers/`.
- Managed/cloud files: `app/modules/cloud_storage/`.
- Customer UI and full-screen file workspace: `app/ui/pages/customers.py`.
- Image Editor: `app/ui/pages/image_editor.py`.
- Image Editor/application-shell regression coverage:
  `tests/unit/test_application_shell.py`.
- Customer UI regression coverage: `tests/unit/test_customers_ui.py`.

The dependency direction remains `UI -> Service -> Repository -> Database`.
The Image Editor may manipulate its in-memory `QPixmap`, but managed customer
file reads/writes must still route through `CustomerService`.

## 3. Image Editor exact implementation contract

### 3.1 Page and document model

Implement `ImageEditorPage(QWidget)` in `app/ui/pages/image_editor.py`. Keep an
`ImageDocument` per open tab containing path, working pixmap, managed source file
ID, X/Y DPI, modified state, zoom, absolute rotation, and independent undo/redo
stacks. Tabs must be closable, movable, theme-aware, and show filename,
modification marker, and zoom.

Open accepts multiple managed images. The customer browser has a collapsed
customer/date tree on the left, folder file details in the centre, preview on
the right, and bottom actions. It can create the current date folder and import
multiple local designs into that date's Design folder. There is no standalone
Import button in the editor command bar. Save replaces the same managed file
when the document originated from a customer file; otherwise it asks for a
managed destination.

### 3.2 Canvas model

- `PanScrollArea` owns mouse-wheel zoom and middle-button panning.
- Zoom range is 0.5% through 800%; opening fits the complete image but never
  enlarges above 100%.
- Wheel zoom is cursor-centred. Middle-button drag pans in both axes.
- The pasteboard is dark and non-editable. Checkerboard appears only inside the
  image canvas and represents transparent pixels.
- Zoom remains available while Crop, Select, Eraser, or Magic Eraser is active.
- Clicking empty dark pasteboard cancels Crop/Select, hides contextual controls,
  clears every checked tool button, and leaves image clicks untouched.

### 3.3 Top command bar

Controls are Open, Save, units, Width, aspect lock, Height, Rotate, Resolution,
image information, and zoom percentage.

- Units: inches, millimetres, centimetres, or pixels.
- Width and Height always describe and resize the complete image, regardless of
  the selected tool. They never become Select properties and never extend the
  canvas merely because Crop is active.
- Aspect lock defaults on. With it on, editing either dimension updates its
  partner live using the current pixel aspect ratio. Actual high-quality
  resampling happens once on Enter/edit completion.
- Rotate is an absolute per-document value. Entering 90 leaves 90 displayed;
  changing 90 to 45 applies a -45 degree delta. Undo/redo and tab switching
  restore the displayed rotation.
- Resolution is 1-2400 DPI. Changing DPI changes physical print dimensions and
  saved metadata without changing screen pixels. Show `pixel dimensions`,
  `Print W x H in`, and `@ DPI` together so the result is verifiable.
- Encoding edited output must set `QImage.setDotsPerMeterX/Y(round(dpi/0.0254))`.

### 3.4 Universal commit behavior

Return and numpad Enter commit the current Width, Height, Rotate, Resolution, or
Crop operation exactly once, clear entry focus, and return focus to the canvas.
When Select is active, Enter finishes that transform session. Use signal blockers
when clearing spin-box focus to avoid duplicate transformations.

### 3.5 Undo and redo

Each document owns up to 50 snapshots. A snapshot contains an implicitly shared
`QPixmap`, modified flag, and absolute rotation. Do not call `pixmap.copy()` for
history because that eagerly duplicates every high-resolution pixel. Use
`QPixmap(pixmap)` and rely on Qt copy-on-write. Redo is cleared on new edits.

### 3.6 Crop

`CropOverlay(QWidget)` draws the crop rectangle, eight handles, rule-of-thirds
guides, and shaded outside region. It supports inward crop and outward transparent
canvas extension. The overlay tracks image coordinates through zoom and pan.
Apply/Cancel appear in the bottom bar. `C` activates Crop; Return or numpad Enter
applies it. Top Width/Height still resample the whole image. Canvas extension is
performed only by dragging Crop beyond image bounds.

### 3.7 Select

`SelectionOverlay(QWidget)` draws a dashed boundary and eight real handles.
Hit-test the closest handle so small selections do not confuse top and bottom
handles. Side handles resize one axis; four corner handles preserve aspect ratio
when lock is enabled. The overlay alone moves during mouse drag; resample once
on release for responsiveness.

Capture pristine visible artwork at Select activation and render every session
resize from that source, not the previous reduced result. Cache visible alpha
bounds by `QPixmap.cacheKey()`. Preserve the true transform rectangle on the
pasteboard even when it extends beyond the image; a selection equal to the full
canvas must still move and enlarge. `V` activates Select reliably through the
page event filter even when a child canvas widget owns focus.

### 3.8 Trim

Trim scans alpha, finds the minimum visible rectangle, and removes transparent
edge pixels. It is in the left rail and uses `Ctrl+T`. If no transparent border
exists, show an explanatory message and do not create an edit.

### 3.9 Round Eraser

The Eraser tool exposes contextual bottom controls only while active:

- round brush;
- size slider and linked numeric field from 1 to 500 px;
- circular cursor scaled by zoom and clamped to a usable screen diameter;
- continuous round-cap line erasing between sampled mouse points;
- true alpha transparency, including conversion of opaque source formats to
  `QImage.Format_ARGB32_Premultiplied`;
- one undo snapshot on mouse press, not one per move event.

Use `QPainter.CompositionMode_Clear`, a transparent round-cap/round-join pen,
and update a fast canvas preview during the stroke.

### 3.10 Magic Eraser

Magic Eraser is a separate left-rail tool with a crosshair cursor. Its contextual
controls are:

- tolerance slider and linked numeric value from 0 to 255, default 24;
- Contiguous checkbox, checked by default.

On click, take one undo snapshot and map the displayed point into source pixels.
Unchecked mode uses a vectorized NumPy RGB maximum-channel-distance mask and
clears alpha for every matching visible pixel. Checked mode performs a Pillow
`ImageDraw.floodfill` from the clicked pixel with the same tolerance so only the
connected matching region becomes transparent. A separated region of the same
color must remain in contiguous mode and be removed in global mode.

### 3.11 Shortcuts

- `Ctrl+O`: Open managed images.
- `Ctrl+S`: Save current image.
- `Ctrl+Z`: Undo.
- `Ctrl+Shift+Z`: Redo.
- `Ctrl+T`: Trim transparent edges.
- `C`: Crop.
- `V`: Select.
- `Return` and numpad `Enter`: commit current operation.
- Mouse wheel: zoom.
- Middle mouse drag: pan.

### 3.12 Current left-rail order

Background Remover, Image Upscaler, Eraser, Magic Eraser, Select, Crop, Magic
Wand, Colour Panel, Text Editor, Shape Editor, Trace Bitmap, followed by Trim.
Only behavior explicitly implemented in code may be called functional.

## 4. Customer workflow reconstruction

Customers use one shared sequence with `LC` for Local and `CR` for Courier and
display as `CODE - BUSINESS NAME - DISTRICT`. Customer creation creates only a
stable root. Date folders are explicit and duplicate-safe. Each date contains
Design, Gangsheet, Invoice Copy, and Payment Receipt. Folder trees start
collapsed and expand only the selected path. Slow Backblaze and Google work is
queued/backgrounded; navigation never creates cloud folders or blocks on the
network.

The full-screen customer workspace preserves the list behind it and orders panes
as Folder tree, Items, Preview. Support secure upload, open, download, replacement,
image preview, embedded PDF preview, and asynchronous cache retrieval.

## 5. Required regression tests

At minimum preserve tests for:

- route registration, tool count/order, and every shortcut;
- Open/Save customer browser layout, collapsed trees, multiple selection, and
  same-file replacement;
- fit zoom, wheel zoom floor, pan, checkerboard/pasteboard separation;
- live proportional dimensions, global resize while Crop is selected, DPI
  metadata round-trip, persistent rotation, and Enter commit;
- Trim, inward/outward Crop, Crop through zoom/pan;
- Select move, handle resize, full-canvas move/enlarge, pristine-source resize,
  and empty-pasteboard deselection;
- Eraser size linkage, transparent round stroke, and undo;
- Magic Eraser tolerance, contiguous separation, global matching, and undo.

## 6. Validation commands

Run from the repository root using the project virtual environment:

```powershell
& 'D:\cdr\kms-erp-venv\Scripts\python.exe' -m ruff format app tests
& 'D:\cdr\kms-erp-venv\Scripts\python.exe' -m ruff check app tests
& 'D:\cdr\kms-erp-venv\Scripts\python.exe' -m pytest -q
git diff --check
git status --short
```

For focused Image Editor iteration:

```powershell
& 'D:\cdr\kms-erp-venv\Scripts\python.exe' -m pytest tests/unit/test_application_shell.py -k image_editor -q
```

## 7. Git consolidation and publishing

1. `git fetch origin --prune` and `git ls-remote --heads origin`.
2. Inspect every branch with `git merge-base --is-ancestor` and `git log main..branch`.
3. Merge genuine new work normally and resolve/test it.
4. If an old feature branch was squash-merged and only its disconnected history
   remains, attach history with an `ours` merge only after proving the tested
   `main` tree must remain authoritative.
5. Compare tree IDs before/after any history-only merge.
6. Commit intentionally, push `main`, delete fully merged remote feature branches,
   prune stale references, and confirm `HEAD == origin/main`.

## 8. Standard completion report

Report delivered behavior, files/docs changed, migrations if any, exact test and
lint results, commit hash, branch/push state, and any remaining external deployment
requirements.
