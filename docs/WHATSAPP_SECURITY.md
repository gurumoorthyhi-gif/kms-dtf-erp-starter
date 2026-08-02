# WhatsApp Workspace security

Phase 1 uses the official `https://web.whatsapp.com/` application inside Qt WebEngine. KMS ERP does not read the WhatsApp DOM, intercept messages, capture QR codes, or retain WhatsApp chat data in its database.

The named WebEngine profile is isolated under the signed-in Windows user's local AppData directory. Persistent cookies are necessary to retain the user's linked-device session. Anyone with access to that Windows account may therefore be able to use the linked WhatsApp session; Windows account access and disk protection remain operational requirements.

Only HTTPS top-level navigation to centrally allow-listed WhatsApp and required supporting domains is accepted. Subresources are not blocked by the top-level policy. A navigation outside that list is stopped and may open in the system browser only after the user confirms a warning. URLs shown by the workspace are redacted to exclude credentials, ports, query strings, and fragments.

**Clear session** removes cookies, HTTP cache, local/session storage, Cache Storage entries, service-worker registrations, and IndexedDB databases available to the WhatsApp origin. The command is destructive and requires confirmation.

No production secrets, phone numbers, message bodies, session cookies, or signed URLs should be written to logs. Later phases must preserve these boundaries when adding ERP customer and order context.
