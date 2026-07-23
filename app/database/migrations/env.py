"""Alembic migration environment."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import Settings
from app.database.base import Base
from app.database.session import resolve_database_url
from app.modules.artwork import models as artwork_models
from app.modules.authentication import models as authentication_models
from app.modules.cloud_storage import models as cloud_storage_models
from app.modules.communications import models as communications_models
from app.modules.customers import models as customer_models
from app.modules.gang_sheets import models as gang_sheet_models
from app.modules.inventory import models as inventory_models
from app.modules.operations import models as operations_models
from app.modules.orders import models as order_models
from app.modules.production import models as production_models
from app.modules.products import models as product_models
from app.modules.sales import models as sales_models
from app.modules.shipping import models as shipping_models

_ = (
    artwork_models,
    authentication_models,
    customer_models,
    cloud_storage_models,
    communications_models,
    gang_sheet_models,
    inventory_models,
    order_models,
    operations_models,
    product_models,
    production_models,
    sales_models,
    shipping_models,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

configured_database_url = config.attributes.get("database_url")
settings = Settings.load()
database_url = resolve_database_url(configured_database_url or settings.database_url)
config.set_main_option(
    "sqlalchemy.url",
    database_url.render_as_string(hide_password=False).replace("%", "%%"),
)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
