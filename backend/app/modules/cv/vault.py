"""Encrypted immutable originals. Never treats stored bytes as a validated CV.

No document parser, external process or network access is used here. Production
ingestion must first enforce the separate format-validation/isolation contract.
"""

import base64
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import SecretStr

from app.core.errors import AppError

MAX_CV_BYTES = 5 * 1024 * 1024
MAX_ENVELOPE_BYTES = MAX_CV_BYTES + 4096
MAGIC = b"JHCV\x01"


@dataclass(frozen=True)
class VaultIdentity:
    owner_id: UUID
    document_id: UUID
    version_id: UUID

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, UUID) for value in (self.owner_id, self.document_id, self.version_id)
        ):
            raise ValueError("Vault identities must be UUIDs")

    def associated_data(self) -> bytes:
        return (
            f"jobhunter/cv/original/v1/{self.owner_id}/{self.document_id}/{self.version_id}"
        ).encode("ascii")


@dataclass(frozen=True)
class CvBlob:
    filename: str = field(repr=False)
    content_type: Literal[
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]
    content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not self.filename.strip()
            or len(self.filename) > 200
            or any(ord(c) < 32 or c in "/\\\x7f" for c in self.filename)
            or self.filename in {".", ".."}
        ):
            raise AppError("CV_FILENAME_INVALID", "Invalid CV filename", 422)
        if self.content_type not in {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }:
            raise AppError("CV_TYPE_INVALID", "Unsupported CV type", 422)
        if not self.content or len(self.content) > MAX_CV_BYTES:
            raise AppError("CV_SIZE_INVALID", "CV size must be between 1 byte and 5 MiB", 413)


class CvVault:
    """Paths are server UUIDs only; plaintext and filenames never reach disk.

    Caller owns DB transactions/audit and must retain an upload intent until
    publication is committed. Reusing an identity cannot overwrite an original.
    A fresh random salt derives a separate AES key for each encryption attempt.
    """

    def __init__(self, root: Path, key: SecretStr) -> None:
        self._root = root.absolute()
        self._key = key

    def __repr__(self) -> str:
        return "CvVault(private_storage)"

    @staticmethod
    def _regular(path: Path, *, directory: bool = False) -> None:
        try:
            info = path.lstat()
            reparse = getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            )
            if (
                reparse
                or stat.S_ISLNK(info.st_mode)
                or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            ):
                raise AppError("CV_STORAGE_UNSAFE", "Private CV storage path is unsafe", 503)
        except FileNotFoundError:
            raise AppError("CV_FILE_NOT_FOUND", "CV original is unavailable", 404) from None

    def _directory(self, identity: VaultIdentity, *, create: bool) -> Path:
        # Validate every existing ancestor BEFORE mkdir/traversal, including
        # Windows junctions. UUIDs cannot introduce arbitrary path components.
        chain = list(reversed(self._root.parents)) + [self._root]
        target = self._root / str(identity.owner_id) / str(identity.document_id)
        chain.extend([self._root / str(identity.owner_id), target])
        for path in chain:
            if not path.exists() and not path.is_symlink() and create:
                path.mkdir(mode=0o700, exist_ok=True)
            self._regular(path, directory=True)
        return target

    def _cipher(self, identity: VaultIdentity, salt: bytes) -> AESGCM:
        master = base64.b64decode(self._key.get_secret_value(), validate=True)
        if len(master) != 32:
            raise AppError("CV_KEY_INVALID", "CV storage key is invalid", 503)
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=identity.associated_data(),
        ).derive(master)
        return AESGCM(key)

    def store(self, identity: VaultIdentity, blob: CvBlob) -> None:
        folder = self._directory(identity, create=True)
        destination = folder / (str(identity.version_id) + ".cv")
        header = json.dumps(
            {"filename": blob.filename, "content_type": blob.content_type},
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        payload = len(header).to_bytes(4, "big") + header + blob.content
        salt, nonce = os.urandom(32), os.urandom(12)
        encrypted = (
            MAGIC
            + salt
            + nonce
            + self._cipher(identity, salt).encrypt(nonce, payload, identity.associated_data())
        )
        temporary = folder / (".pending-" + uuid4().hex)
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            with os.fdopen(os.open(temporary, flags, 0o600), "wb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic publication without replacement, including on Windows/NTFS.
            os.link(temporary, destination)
        except FileExistsError:
            raise AppError("CV_VERSION_EXISTS", "CV originals cannot be overwritten", 409) from None
        except OSError:
            raise AppError(
                "CV_STORAGE_UNAVAILABLE", "Private CV storage is unavailable", 503
            ) from None
        finally:
            temporary.unlink(missing_ok=True)

    def read(self, identity: VaultIdentity) -> CvBlob:
        path = self._directory(identity, create=False) / (str(identity.version_id) + ".cv")
        self._regular(path)
        try:
            with path.open("rb") as stream:
                encrypted = stream.read(MAX_ENVELOPE_BYTES + 1)
            if len(encrypted) > MAX_ENVELOPE_BYTES or encrypted[:5] != MAGIC:
                raise ValueError
            salt, nonce, ciphertext = encrypted[5:37], encrypted[37:49], encrypted[49:]
            payload = self._cipher(identity, salt).decrypt(
                nonce, ciphertext, identity.associated_data()
            )
            size = int.from_bytes(payload[:4], "big")
            if not 1 <= size <= 2048:
                raise ValueError
            metadata = json.loads(payload[4 : 4 + size])
            return CvBlob(
                filename=metadata["filename"],
                content_type=metadata["content_type"],
                content=payload[4 + size :],
            )
        except FileNotFoundError:
            raise AppError("CV_FILE_NOT_FOUND", "CV original is unavailable", 404) from None
        except (InvalidTag, ValueError, TypeError, KeyError):
            raise AppError(
                "CV_INTEGRITY_FAILED", "CV original integrity check failed", 409
            ) from None
        except OSError:
            raise AppError(
                "CV_STORAGE_UNAVAILABLE", "Private CV storage is unavailable", 503
            ) from None

    def purge_pending(self, identity: VaultIdentity) -> None:
        """Only during durable document deletion, with no publishing version."""
        try:
            folder = self._directory(identity, create=False)
            for path in folder.iterdir():
                if re.fullmatch(r"\.pending-[0-9a-f]{32}", path.name):
                    self._regular(path)
                    path.unlink()
        except AppError as error:
            if error.code != "CV_FILE_NOT_FOUND":
                raise
        except OSError:
            raise AppError(
                "CV_STORAGE_UNAVAILABLE", "Private CV storage is unavailable", 503
            ) from None

    def remove(self, identity: VaultIdentity) -> None:
        """Idempotent purge. Call only for an owner-authorized durable deletion intent."""
        try:
            path = self._directory(identity, create=False) / (str(identity.version_id) + ".cv")
            if path.exists() or path.is_symlink():
                self._regular(path)
                path.unlink()
        except AppError as exc:
            if exc.code != "CV_FILE_NOT_FOUND":
                raise
        except OSError:
            raise AppError(
                "CV_STORAGE_UNAVAILABLE", "Private CV storage is unavailable", 503
            ) from None
