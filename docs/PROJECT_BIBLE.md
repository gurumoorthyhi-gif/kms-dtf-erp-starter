# KMS DTF ERP — Project Bible

## Product purpose

KMS DTF ERP is a Windows desktop ERP for DTF printing businesses. It manages business and production workflow; it is not a RIP application.

## Workflow

Customer → Order → Artwork → Design Approval → Gang Sheet → Production → Quality Check → Packing → Dispatch → Payment → Reports

## Architecture

UI → Service → Repository → Database

External integrations remain isolated under `app/integrations`.

## UI direction

- Glassmorphism surfaces
- Gradient icons
- Icons-only sidebar
- Expand-on-hover navigation
- Light workspace
- Rounded floating cards

## Git rules

- One feature branch per task.
- Commit before and after Codex changes.
- Never commit secrets, production databases, customer artwork, or AI model weights.
- Merge only after tests and manual verification.
