# KMS DTF ERP User Manual

## Getting started

Launch KMS DTF ERP and sign in with the account created by your administrator.
The left navigation expands on hover. Pages are visible according to your role.

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

## Security

Never share passwords or `.env`. Administrators should grant the minimum role
needed. Provider credentials are configured on the machine, not entered into
customer records or committed to Git.
