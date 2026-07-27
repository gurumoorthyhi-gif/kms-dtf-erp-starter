"""Reset an existing user's password from an interactive terminal."""

from __future__ import annotations

import argparse
import getpass

from app.core.config import Settings, initialize_directories
from app.database import create_database_engine, create_session_factory, upgrade_database
from app.modules.authentication import PasswordHasher, UserRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reset a KMS DTF ERP password")
    parser.add_argument("--username", required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    username = arguments.username.strip().casefold()
    password = getpass.getpass("New password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match. Password was not changed.")

    password_hash = PasswordHasher().hash(password)
    settings = Settings.load()
    paths = initialize_directories(settings)
    upgrade_database(settings.database_url, base_directory=paths.base_directory)
    engine = create_database_engine(settings.database_url, base_directory=paths.base_directory)
    repository = UserRepository(create_session_factory(engine))
    try:
        user = repository.get_by_username(username)
        if user is None:
            raise SystemExit(f"User not found: {username}")
        repository.update_password(user.id, password_hash)
    finally:
        engine.dispose()

    print(f"Password changed successfully for: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
