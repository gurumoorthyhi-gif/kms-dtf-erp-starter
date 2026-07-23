"""Password hashing based on the standard-library scrypt KDF."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32
MINIMUM_PASSWORD_LENGTH = 12


class PasswordPolicyError(ValueError):
    """Raised when a password does not satisfy the local security policy."""


class PasswordHasher:
    """Create and verify versioned scrypt password hashes."""

    algorithm = "scrypt"

    def hash(self, password: str) -> str:
        if len(password) < MINIMUM_PASSWORD_LENGTH:
            raise PasswordPolicyError(
                f"Password must contain at least {MINIMUM_PASSWORD_LENGTH} characters"
            )
        salt = secrets.token_bytes(SALT_BYTES)
        derived_key = self._derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
        return "$".join(
            (
                self.algorithm,
                str(SCRYPT_N),
                str(SCRYPT_R),
                str(SCRYPT_P),
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(derived_key).decode("ascii"),
            )
        )

    def verify(self, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, n, r, p, salt_text, expected_text = encoded_hash.split("$")
            if algorithm != self.algorithm:
                return False
            parameters = (int(n), int(r), int(p))
            if parameters != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
                return False
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected = base64.urlsafe_b64decode(expected_text.encode("ascii"))
            actual = self._derive(password, salt, *parameters)
        except (binascii.Error, ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
        return hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=KEY_BYTES,
        )
