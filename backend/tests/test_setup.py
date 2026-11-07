from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.errors import AppError
from app.setup import create_tls


def test_local_tls_key_and_certificate_are_valid_and_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    working = tmp_path / "backend"
    working.mkdir()
    monkeypatch.chdir(working)
    create_tls()
    folder = tmp_path / "local-data" / "tls"
    original = (folder / "localhost.key").read_bytes()
    key = serialization.load_pem_private_key(original, password=None)
    cert = x509.load_pem_x509_certificate((folder / "localhost.crt").read_bytes())
    assert key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ) == cert.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key.public_key().verify(
        cert.signature,
        cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "localhost" in names.get_values_for_type(x509.DNSName)
    with pytest.raises(AppError, match="refusing to overwrite"):
        create_tls()
    assert (folder / "localhost.key").read_bytes() == original
