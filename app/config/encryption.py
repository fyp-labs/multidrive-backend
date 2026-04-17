import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_LENGTH = 12


def _get_encryption_key() -> bytes:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable is not set")
    return bytes.fromhex(key)


def encrypt(text: str) -> str:
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LENGTH)

    encrypted = aesgcm.encrypt(nonce, text.encode("utf-8"), None)

    return f"{nonce.hex()}:{encrypted.hex()}"


def decrypt(encrypted_text: str) -> str:
    key = _get_encryption_key()
    parts = encrypted_text.split(":")

    if len(parts) != 2:
        raise ValueError("Invalid encrypted text format")

    nonce = bytes.fromhex(parts[0])
    encrypted = bytes.fromhex(parts[1])

    aesgcm = AESGCM(key)
    decrypted = aesgcm.decrypt(nonce, encrypted, None)

    return decrypted.decode("utf-8")
