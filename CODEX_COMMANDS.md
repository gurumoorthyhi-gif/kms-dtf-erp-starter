# Commands for Continuing Development

The original phase-by-phase bootstrap tasks are complete. Use these current
request templates instead.

## Customer workflow change

Read the Project Bible, Requirements, customer service/repository/models, customer
UI, cloud service, Google integration, and migrations. Preserve local-first
responsiveness. Do not create cloud folders during navigation. Add tests and
update all affected documentation.

## File storage change

Inspect `CloudStorageService`, provider adapters, customer storage dates, Settings,
and Google catalogue behavior. Queue local state before network work, keep
Backblaze private, background slow operations, and verify offline/retry behavior.

## UI change

Read the UI Design System. Preserve the fixed 78 px rail, dark/light
glassmorphism, universal Google button, and in-page Customers navigation. Test
widget state, routing, and non-blocking behavior.

## Database change

Add a forward Alembic revision from the current head, update ORM/repository/service
layers, update migration and metadata tests, and revise the Database Schema.

## Release/publish

Review the whole diff for credentials and runtime files. Run the full test, Ruff,
Black, compile, and diff checks. Update changelog/docs, commit intentionally,
push the current branch, and update the existing draft PR.

## Standard completion report

- behavior delivered;
- migrations added;
- tests/checks and results;
- known external deployment requirements;
- commit, branch, push, and PR state.
