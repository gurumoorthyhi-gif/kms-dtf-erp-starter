# WhatsApp Workspace test plan

## Automated

- Verify allowed WhatsApp/supporting hosts and their subdomains.
- Reject HTTP, lookalike domains, credential-bearing attacker URLs, and non-web schemes.
- Verify URL redaction removes credentials, ports, queries, and fragments.
- Verify the persistent profile path has isolated storage and cache directories.

## Manual Windows acceptance

1. Open **WhatsApp**, scan the QR code, close KMS ERP, reopen it, and confirm the session persists.
2. Exercise Back, Forward, Refresh, WhatsApp Home, panel toggle, full-screen, and external-open confirmation.
3. Click a link outside the allow-list and confirm it never loads inside the embedded workspace.
4. Disconnect the network and confirm the failed/offline state is visible; reconnect and refresh.
5. Clear the session, restart KMS ERP, and confirm WhatsApp requires QR login again.
6. Temporarily remove the WebEngine package and confirm the ERP starts with an explicit WhatsApp dependency error.
