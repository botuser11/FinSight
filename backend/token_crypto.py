import os

from cryptography.fernet import Fernet, InvalidToken


class TokenEncryptionNotConfigured(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv('TOKEN_ENCRYPTION_KEY')
    if not key:
        raise TokenEncryptionNotConfigured('TOKEN_ENCRYPTION_KEY is not set')
    return Fernet(key)


def encrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str | None) -> str | None:
    """Returns None for empty values and for anything that isn't a valid token
    under the current key (e.g. plaintext tokens stored before encryption)."""
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return None
