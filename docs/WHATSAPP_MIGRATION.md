# WhatsApp Workspace migration

Phase 1 replaces the former generic WhatsApp message-table page at the existing `whatsapp` route. The sidebar location and `communications.view` permission remain unchanged. The old communication service and database records are not deleted; email and any existing communication history continue to use that service.

There is no database migration in Phase 1 because the browser session belongs in the isolated WebEngine profile rather than the ERP database. On first opening the new workspace, the user scans the normal WhatsApp Web QR code. Subsequent launches reuse that session until the user logs out through WhatsApp, clears the workspace session, or removes the Windows profile data.

Deployment must install the project's `PySide6` dependency including Qt WebEngine. If WebEngine is unavailable or cannot load its runtime libraries, the WhatsApp route reports the dependency error while the remaining ERP pages continue to operate.
