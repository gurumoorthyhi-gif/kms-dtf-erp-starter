# WhatsApp Workspace

Phase 1 embeds the official WhatsApp Web site in KMS ERP using Qt WebEngine. It does not scrape WhatsApp, automate its DOM, send messages through an unofficial API, or store chat content in the ERP database.

The workspace is lazy-loaded from the existing **WhatsApp** sidebar route. Its named browser profile is stored per Windows user under `AppData/Local/KMS ERP/browser_profiles/whatsapp`, with separate persistent-storage and disk-cache directories. Cookies therefore survive an ERP restart. **Clear session** deletes cookies, clears WebEngine cache and browser local/session storage, then returns to WhatsApp Home; the user must scan the QR code again.

Top-level navigation is HTTPS-only and centrally allow-listed for WhatsApp and the supporting WhatsApp/Facebook CDN domains. Blocked links require an explicit confirmation before opening in the system browser. Query strings, fragments, credentials, and ports are removed from the URL displayed in that warning or suitable for logs.

If Qt WebEngine cannot load, the rest of KMS ERP remains usable and the WhatsApp page displays a direct dependency error with a retry action.

Later phases will add customer and order context, attachment workflows, reminders, follow-ups, search, audit events, exports, and reporting. Those features are intentionally absent from Phase 1.
