"""Bounded, context-bound authenticated encryption shared by private DB payloads."""

import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import SecretStr

from app.core.errors import AppError


class PrivatePayload:
    def __init__(
        self,
        key: SecretStr,
        *,
        namespace: bytes,
        magic: bytes,
        limit_code: str = "PRIVATE_DATA_LIMIT",
        integrity_code: str = "PRIVATE_INTEGRITY_FAILED",
        limit_message: str = "Private data limit exceeded",
        integrity_message: str = "Private data integrity failed",
    ) -> None:
        if len(magic) != 5:
            raise ValueError("Private payload marker must be five bytes")
        self._key, self.namespace, self.magic = key, namespace, magic
        self.limit_code, self.integrity_code = limit_code, integrity_code
        self.limit_message, self.integrity_message = limit_message, integrity_message

    def _cipher(self, salt: bytes, context: bytes) -> AESGCM:
        master = base64.b64decode(self._key.get_secret_value(), validate=True)
        return AESGCM(
            HKDF(
                algorithm=hashes.SHA256(), length=32, salt=salt, info=self.namespace + context
            ).derive(master)
        )

    def seal(self, data: bytes, context: bytes) -> bytes:
        if len(data) > 512 * 1024:
            raise AppError(self.limit_code, self.limit_message, 422)
        salt, nonce = os.urandom(32), os.urandom(12)
        return self.magic + salt + nonce + self._cipher(salt, context).encrypt(nonce, data, context)

    def digest(self, data: bytes, context: bytes) -> str:
        master = base64.b64decode(self._key.get_secret_value(), validate=True)
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=self.namespace + b"cache/" + context,
        ).derive(master)
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    def open(self, data: bytes, context: bytes) -> bytes:
        try:
            if len(data) > 512 * 1024 + 65 or data[:5] != self.magic:
                raise ValueError
            return self._cipher(data[5:37], context).decrypt(data[37:49], data[49:], context)
        except (InvalidTag, ValueError):
            raise AppError(self.integrity_code, self.integrity_message, 409) from None
