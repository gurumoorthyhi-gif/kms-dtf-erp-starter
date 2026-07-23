# Database Schema

Initial modules will introduce tables incrementally through Alembic migrations.

Priority entities: users, roles, customers, orders, order_items, artworks, production_jobs, inventory_items, invoices, payments, dispatch_records, activity_logs, and settings.

The migration environment is initialized under `app/database/migrations`.
No business tables are part of the database foundation; each module introduces
its schema through a reviewed Alembic revision.

## Authentication

Phase 4 introduces `users`, `roles`, `permissions`, `user_roles`,
`role_permissions`, and immutable `activity_logs`. Passwords are represented only
by versioned scrypt hashes. Customer and order tables remain out of scope.

## Customers

Phase 6 adds `customers`, `customer_addresses`, and
`customer_file_references`. Customer codes are unique, addresses are separated
into billing and shipping records, and file references store managed relative
paths rather than machine-specific absolute paths. Order tables remain out of scope.

## Products and pricing

Phase 7 adds product categories, products, quantity/metre price tiers, discount
rules, and tax configuration. Monetary values use fixed-precision decimals.

## Orders

Phase 8 adds `orders`, `order_items`, and `order_status_history`. Orders snapshot
the calculated unit prices and totals for each item, store advance and balance
amounts, and retain every workflow status transition. Artwork processing remains
out of scope until Phase 9.
