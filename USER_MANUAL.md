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

Select **Open folder** to browse these folders inside the ERP, upload files, open
or download synchronized files, and upload replacement versions. The workspace
stays inside the Customers page and is arranged as **Folder tree → Items →
Preview** with draggable dividers. Select **Back to customers** to return to the
preserved customer list and open another customer immediately. Select a PNG,
JPEG, TIFF, BMP, WebP, or another supported image format to preview it on the
right. PDF documents open in the embedded PDF viewer. Files not present in the
local cache are fetched securely from Backblaze in the background.

## Security

Never share passwords or `.env`. Administrators should grant the minimum role
needed. Provider credentials are configured on the machine, not entered into
customer records or committed to Git.
