"""Local setup: never accepts passwords on command lines or logs secrets."""

import argparse
import asyncio
import base64
import getpass
import ipaddress
import secrets
from datetime import timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import ValidationError

from app.core.db import make_runtime
from app.core.errors import AppError
from app.core.settings import Settings
from app.modules.auth import AuthService
from app.shared.clock import utcnow


async def setup_owner() -> None:
    email = (await asyncio.to_thread(input, "Owner email: ")).strip()
    password = await asyncio.to_thread(getpass.getpass, "Password (12–128 characters): ")
    if password != await asyncio.to_thread(getpass.getpass, "Confirm password: "):
        raise AppError("INVALID_SETUP", "Passwords do not match")
    runtime = make_runtime(Settings())
    try:
        async with runtime.sessions() as session:
            await AuthService(session, runtime.settings).setup_owner(email, password)
        print("Owner created. Setup is now locked.")
    finally:
        await runtime.engine.dispose()


def create_tls() -> None:
    folder = Path("../local-data/tls").resolve()
    folder.mkdir(parents=True, exist_ok=True)
    key_path, cert_path = folder / "localhost.key", folder / "localhost.crt"
    if key_path.exists() or cert_path.exists():
        raise AppError("TLS_EXISTS", "Local certificate already exists; refusing to overwrite")
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.IPAddress(ipaddress.ip_address("::1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print("Local self-signed certificate created in local-data/tls (valid 30 days).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["owner", "secrets", "tls"])
    command = parser.parse_args().command
    try:
        if command == "owner":
            asyncio.run(setup_owner())
        elif command == "tls":
            create_tls()
        else:
            print("# Copy these generated secrets to backend/.env, never to Git or chat.")
            print(f"JWT_SECRET={secrets.token_urlsafe(64)}")
            print(f"CV_ENCRYPTION_KEY={base64.b64encode(secrets.token_bytes(32)).decode()}")
    except AppError as exc:
        raise SystemExit(exc.message) from None
    except ValidationError:
        raise SystemExit(
            "Invalid backend settings. Check .env without exposing its contents."
        ) from None
    except Exception:
        raise SystemExit("Setup failed. Check database access and applied migrations.") from None


if __name__ == "__main__":
    main()
