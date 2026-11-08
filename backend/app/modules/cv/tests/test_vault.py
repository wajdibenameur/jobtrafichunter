import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.errors import AppError
from app.modules.cv import CvBlob, CvVault, VaultIdentity
from app.modules.cv.vault import MAX_CV_BYTES


@pytest.fixture
def vault(tmp_path: Path) -> CvVault:
    return CvVault(tmp_path / "private", SecretStr(base64.b64encode(bytes(range(32))).decode()))


def identity() -> VaultIdentity:
    return VaultIdentity(uuid4(), uuid4(), uuid4())


def blob() -> CvBlob:
    # Opaque storage fixture, deliberately not a valid PDF. No parser claims.
    return CvBlob("synthetic-original.pdf", "application/pdf", b"private synthetic bytes")


def test_encrypted_original_roundtrip_without_plaintext_on_disk(
    vault: CvVault, tmp_path: Path
) -> None:
    key = identity()
    original = blob()
    vault.store(key, original)
    assert vault.read(key) == original
    files = list((tmp_path / "private").rglob("*.cv"))
    assert len(files) == 1
    encrypted = files[0].read_bytes()
    assert original.content not in encrypted and original.filename.encode() not in encrypted
    assert not list((tmp_path / "private").rglob(".pending-*"))
    assert original.filename not in repr(original) and original.content.decode() not in repr(
        original
    )
    assert "AAECA" not in repr(vault)


def test_immutable_versions_concurrent_publication(vault: CvVault) -> None:
    key = identity()

    def put() -> str:
        try:
            vault.store(key, blob())
            return "STORED"
        except AppError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: put(), range(4)))
    assert results.count("STORED") == 1
    assert results.count("CV_VERSION_EXISTS") == 3
    assert vault.read(key) == blob()


def test_tampering_and_swapping_identity_fail_closed(vault: CvVault, tmp_path: Path) -> None:
    first, second = identity(), identity()
    vault.store(first, blob())
    vault.store(second, blob())
    paths = [
        tmp_path / "private" / str(k.owner_id) / str(k.document_id) / f"{k.version_id}.cv"
        for k in (first, second)
    ]
    # Equal plaintext produces distinct envelopes; AAD binds all identity dimensions.
    assert paths[0].read_bytes() != paths[1].read_bytes()
    original = paths[1].read_bytes()
    paths[1].write_bytes(paths[0].read_bytes())
    with pytest.raises(AppError, match="integrity") as error:
        vault.read(second)
    assert error.value.code == "CV_INTEGRITY_FAILED"
    paths[1].write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(AppError):
        vault.read(second)


def test_wrong_key_missing_file_and_idempotent_deletion(vault: CvVault, tmp_path: Path) -> None:
    key = identity()
    vault.store(key, blob())
    wrong = CvVault(tmp_path / "private", SecretStr(base64.b64encode(bytes(range(1, 33))).decode()))
    with pytest.raises(AppError) as error:
        wrong.read(key)
    assert error.value.code == "CV_INTEGRITY_FAILED"
    vault.remove(key)
    vault.remove(key)
    with pytest.raises(AppError) as missing:
        vault.read(key)
    assert missing.value.status == 404


@pytest.mark.parametrize("filename", ["../cv.pdf", "a\\b.pdf", "a\n.pdf", "", ".", "x" * 201])
def test_client_filename_cannot_be_a_path(filename: str) -> None:
    with pytest.raises(AppError):
        CvBlob(filename, "application/pdf", b"fixture")


@pytest.mark.parametrize("size", [0, MAX_CV_BYTES + 1])
def test_size_is_bounded(size: int) -> None:
    with pytest.raises(AppError) as error:
        CvBlob("cv.pdf", "application/pdf", b"x" * size)
    assert error.value.code == "CV_SIZE_INVALID"


def test_maximum_file_and_unicode_filename_are_preserved(vault: CvVault) -> None:
    original = CvBlob("CV-études-ملف.pdf", "application/pdf", b"x" * MAX_CV_BYTES)
    key = identity()
    vault.store(key, original)
    assert vault.read(key) == original


def test_failed_publication_cleans_temporary_ciphertext(
    vault: CvVault, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object) -> None:
        raise OSError("private provider detail must not escape")

    monkeypatch.setattr("app.modules.cv.vault.os.link", fail)
    with pytest.raises(AppError) as error:
        vault.store(identity(), blob())
    assert error.value.code == "CV_STORAGE_UNAVAILABLE"
    assert "private provider" not in str(error.value)
    assert not list(tmp_path.rglob(".pending-*")) and not list(tmp_path.rglob("*.cv"))
