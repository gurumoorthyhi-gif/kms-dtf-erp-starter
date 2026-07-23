# Database Schema

Initial modules will introduce tables incrementally through Alembic migrations.

Priority entities: users, roles, customers, orders, order_items, artworks, production_jobs, inventory_items, invoices, payments, dispatch_records, activity_logs, and settings.

The migration environment is initialized under `app/database/migrations`.
No business tables are part of the database foundation; each module introduces
its schema through a reviewed Alembic revision.
