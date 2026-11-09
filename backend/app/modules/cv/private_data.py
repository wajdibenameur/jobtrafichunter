import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import SecretStr

from app.core.errors import AppError


class PrivateCvData:
    """Authenticated encryption for CV/profile database payloads, not files."""

    def __init__(self, key: SecretStr) -> None:
        self._key = key

    def _cipher(self, salt: bytes, context: bytes) -> AESGCM:
        master = base64.b64decode(self._key.get_secret_value(), validate=True)
        return AESGCM(
            HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                info=b"jobhunter/cv/private-db/v1/" + context,
            ).derive(master)
        )

    def seal(self, data: bytes, context: bytes) -> bytes:
        if len(data) > 512 * 1024:
            raise AppError("CV_DATA_LIMIT", "Private CV data limit exceeded", 422)
        salt, nonce = os.urandom(32), os.urandom(12)
        return (
            b"JHDB\x01" + salt + nonce + self._cipher(salt, context).encrypt(nonce, data, context)
        )

    def open(self, data: bytes, context: bytes) -> bytes:
        try:
            if len(data) > 512 * 1024 + 65 or data[:5] != b"JHDB\x01":
                raise ValueError
            return self._cipher(data[5:37], context).decrypt(data[37:49], data[49:], context)
        except (InvalidTag, ValueError):
            raise AppError("CV_INTEGRITY_FAILED", "Private CV data integrity failed", 409) from None
