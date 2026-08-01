# KMS DTF ERP User Manual

## Getting started

Launch KMS DTF ERP and sign in with the account created by your administrator.
The narrow navigation shows each module name when its icon is hovered. Pages are
visible according to your role.

## Workflow

Create the customer, products and order; upload artwork; obtain approval; build
the gang sheet; move the job through production and quality; pack and dispatch;
then issue the invoice and record payments. Inventory movements, communications,
reports and audit history remain linked to these records.

## Backup and recovery

Open **Reports & Backup** and choose **Backup now** before upgrades or major
changes. Use **Restore wizard** to verify a backup and restore it to a selected
database file. Close the application before replacing the active database.

## Offline work

Cloud uploads are cached and queued when offline. Open **Cloud Storage** and
select **Synchronize** after connectivity returns. Failed transfers retain their
local files and retry state.

## Backblaze file storage

Open **Settings**, enter the private Backblaze B2 S3 endpoint, bucket, application
key ID and application key, then select **Test connection**. Save only after the
test succeeds. The application key is stored in the operating system credential
vault and is not written to the ERP database or settings file.

Use **Cloud Storage** to upload and synchronize files. Select a synchronized file
and choose **Open selected** to obtain temporary private access. When Google Drive
is connected, the ERP creates metadata-only Drive catalog entries automatically;
the original file remains in Backblaze and does not consume Drive file storage.

The universal **Google Drive** button is located at the bottom-right of the
application. It connects or opens the main DTF ERP Drive folder from any module.

Creating a customer creates only its stable customer root in Backblaze and Google
Drive. When new work begins, open the customer and select **Create today's
folder**. The ERP creates that date once with **Design**, **Gangsheet**,
**Invoice Copy**, and **Payment Receipt** folders. Selecting the button again on
the same day shows an alert and creates nothing. This keeps the customer tree
limited to dates that contain real work.

Select **Open folder** to launch a separate full-screen ERP file window, upload
files, open or download synchronized files, and upload replacement versions.
The window is arranged as **Folder tree → Items → Preview** with draggable
dividers. In the folder panel, select **Back** once to see the customer folder
and again to see the main Customers folder. Close the window to return to the
preserved customer list. Select a PNG,
JPEG, TIFF, BMP, WebP, or another supported image format to preview it on the
right. PDF documents open in the embedded PDF viewer. Files not present in the
local cache are fetched securely from Backblaze in the background.

## Image Editor

Open **Image Editor** from the navigation rail. Select **Open** to use the
three-pane customer browser and choose one or more managed images. Each image
opens in its own movable, closable tab. The browser can create today's dated
folder and import local designs into its Design folder. **Save** replaces the
same managed file when it was opened from a customer folder.

Use the mouse wheel to zoom from 0.5% to 800% and hold the middle mouse button
to pan. The percentage appears at the top. The dark area is pasteboard; the
checkerboard inside the image represents transparency. Click empty pasteboard
to deselect all tools.

The top Width, Height, Rotate, and Resolution values always apply to the complete
image. Choose inches, millimetres, centimetres, or pixels. Keep the lock closed
for proportional dimensions; the paired value updates while typing. Press Enter
to commit. Rotate remains at the entered absolute angle. DPI changes print size
and saved resolution metadata, not the on-screen pixel count; verify it in the
top status text showing pixels, print inches, and DPI.

- **Select** (`V`): move artwork and resize with eight handles. Locked corner
  handles remain proportional. The boundary may extend beyond the canvas.
- **Crop** (`C`): drag inward to crop or outward to extend transparent canvas;
  press Enter to apply.
- **Trim** (`Ctrl+T`): remove transparent edge pixels.
- **Eraser**: drag a round transparent brush. Adjust its 1-500 px size in the
  bottom bar. Each stroke is one Undo operation.
- **Magic Eraser**: click a color to remove it. Tolerance controls color range.
  Keep **Contiguous** checked to remove only the connected clicked region;
  uncheck it to remove matching colors across the image.

Use `Ctrl+Z` for Undo, `Ctrl+Shift+Z` for Redo, `Ctrl+O` for Open, and `Ctrl+S`
for Save. Return and numpad Enter finish the active numeric or Crop operation.

## Security

Never share passwords or `.env`. Administrators should grant the minimum role
needed. Provider credentials are configured on the machine, not entered into
customer records or committed to Git.
