# Architecture

The application follows a modular layered architecture:

1. UI layer
2. Service layer
3. Repository layer
4. Database layer

The UI must not query SQLite directly.

Database access uses a shared SQLAlchemy declarative base, engine factory, and
transaction-scoped session factory. Engine creation applies SQLite-specific
thread handling only for SQLite URLs, keeping other SQLAlchemy backends available.

Authentication follows the same UI → Service → Repository → Database boundary.
The UI receives only an authentication service and safe current-user identity;
password verification and activity recording remain below the UI layer.
