"""Create the first administrator account from an interactive terminal."""

from __future__ import annotations

import argparse
import getpass

from app.core.config import Settings, initialize_directories
from app.database import (
    create_database_engine,
    create_session_factory,
    upgrade_database,
)
from app.modules.authentication import (
    ActivityRepository,
    AuthenticationService,
    CurrentUserSession,
    PasswordHasher,
    RoleRepository,
    UserRepository,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a KMS DTF ERP administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--email")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    password = getpass.getpass("Administrator password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    settings = Settings.load()
    paths = initialize_directories(settings)
    upgrade_database(settings.database_url, base_directory=paths.base_directory)
    engine = create_database_engine(
        settings.database_url,
        base_directory=paths.base_directory,
    )
    factory = create_session_factory(engine)
    service = AuthenticationService(
        UserRepository(factory),
        RoleRepository(factory),
        ActivityRepository(factory),
        PasswordHasher(),
        CurrentUserSession(),
    )
    try:
        user = service.create_administrator(
            username=arguments.username,
            password=password,
            full_name=arguments.full_name,
            email=arguments.email,
        )
    finally:
        engine.dispose()

    print(f"Administrator created: {user.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
