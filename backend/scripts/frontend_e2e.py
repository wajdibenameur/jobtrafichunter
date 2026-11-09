"""Run Angular browser tests against FastAPI and an isolated schema in .env.test.

No real owner is created or modified. No database credentials are written to artifacts.
"""

import asyncio
import base64
import json
import os
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.engine import make_url

# CLI is invoked from backend; expose the application package to script entry points.
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.db import make_runtime  # noqa: E402
from app.core.settings import Settings  # noqa: E402
from app.modules.auth import AuthService  # noqa: E402
from app.setup import create_tls  # noqa: E402
from tests.document_fixtures import pdf_fixture  # noqa: E402

ROOT = BACKEND.parent
ARTIFACTS = ROOT / ".cache" / "frontend-e2e"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def settings_for_test(schema: str, origin: str) -> Settings:
    values = dotenv_values(BACKEND / ".env.test")
    url = os.environ.get("TEST_DATABASE_URL") or values.get("DATABASE_URL")
    if not url or not str(make_url(url).database).endswith("_test"):
        raise RuntimeError("Configure backend/.env.test with a dedicated database ending in _test")
    return Settings(
        _env_file=None,
        database_url=url,
        database_schema=schema,
        environment="test",
        jwt_secret=secrets.token_urlsafe(64),
        cv_encryption_key=base64.b64encode(secrets.token_bytes(32)).decode(),
        allowed_origins=[origin],
        cv_storage_path=ROOT / ".cache" / "frontend-e2e" / "cv-storage" / schema,
    )


async def create_schema(settings: Settings) -> None:
    runtime = make_runtime(settings.model_copy(update={"database_schema": "public"}))
    try:
        async with runtime.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{settings.database_schema}"'))
    finally:
        await runtime.engine.dispose()


async def remove_schema(settings: Settings) -> None:
    schema = settings.database_schema
    if not schema.startswith("e2e_") or len(schema) != 36:
        raise RuntimeError("Refusing unsafe cleanup target")
    runtime = make_runtime(settings.model_copy(update={"database_schema": "public"}))
    try:
        async with runtime.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    finally:
        await runtime.engine.dispose()


async def create_owner(settings: Settings, email: str, password: str) -> None:
    runtime = make_runtime(settings)
    try:
        async with runtime.sessions() as session:
            await AuthService(session, settings).setup_owner(email, password)
    finally:
        await runtime.engine.dispose()


def run() -> int:
    api_port, frontend_port = free_port(), free_port()
    origin = f"https://localhost:{frontend_port}"
    settings = settings_for_test("e2e_" + uuid4().hex, origin)
    email, password = "browser-owner@example.test", secrets.token_urlsafe(24)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        DATABASE_URL=settings.database_url.get_secret_value(),
        DATABASE_SCHEMA=settings.database_schema,
        JWT_SECRET=settings.jwt_secret.get_secret_value(),
        CV_ENCRYPTION_KEY=settings.cv_encryption_key.get_secret_value(),
        ALLOWED_ORIGINS=json.dumps([origin]),
        ENVIRONMENT="test",
        CV_STORAGE_PATH=str(settings.cv_storage_path),
        CV_SANDBOX_PATH=str(settings.cv_sandbox_path),
        NG_CLI_ANALYTICS="false",
        npm_config_offline="false",
        npm_config_cache=str(ROOT / ".cache" / "npm"),
    )
    node_folder = ROOT / ".tools" / "node-v22.22.3-win-x64"
    node = node_folder / "node.exe"
    npm_cli = node_folder / "node_modules/npm/bin/npm-cli.js"
    if not node.exists():
        node_command, npm_command = shutil.which("node"), shutil.which("npm")
        if not node_command or not npm_command:
            raise RuntimeError("Supported Node and npm are required; see frontend README")
        node = Path(node_command)
        node_folder = node.parent
        npm_cli = (
            Path(npm_command).resolve()
            if os.name != "nt"
            else node_folder / "node_modules/npm/bin/npm-cli.js"
        )
    env["PATH"] = str(node_folder) + os.pathsep + env["PATH"]
    created = False
    api_process = None
    worker_process = None
    worker_log = None
    config_path = ARTIFACTS / "session.json"
    cv_fixture = ARTIFACTS / "synthetic-cv.pdf"
    cv_fixture.write_bytes(pdf_fixture())
    try:
        asyncio.run(create_schema(settings))
        created = True
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            timeout=30,
        )
        if migration.returncode:
            raise RuntimeError("E2E migration failed; database credentials hidden")
        asyncio.run(create_owner(settings, email, password))
        tls_work = ARTIFACTS / "backend"
        tls_work.mkdir(exist_ok=True)
        cert = ARTIFACTS / "local-data" / "tls" / "localhost.crt"
        key = cert.with_suffix(".key")
        if not cert.exists() or not key.exists():
            previous = Path.cwd()
            try:
                os.chdir(tls_work)
                create_tls()
            finally:
                os.chdir(previous)
        env.update(
            JOBHUNTER_FRONTEND_PORT=str(frontend_port),
            JOBHUNTER_API_TARGET=f"https://127.0.0.1:{api_port}",
            JOBHUNTER_TLS_KEY=str(key),
            JOBHUNTER_TLS_CERT=str(cert),
            JOBHUNTER_E2E_CONFIG=str(config_path),
        )
        # Only throwaway owner credentials, never the PostgreSQL URL.
        config_path.write_text(
            json.dumps(
                {
                    "baseURL": origin,
                    "email": email,
                    "password": password,
                    "cvFixturePath": str(cv_fixture),
                }
            ),
            encoding="utf-8",
        )
        config_path.chmod(0o600)
        with (ARTIFACTS / "backend.log").open("w", encoding="utf-8") as log:
            api_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--ssl-keyfile",
                    str(key),
                    "--ssl-certfile",
                    str(cert),
                    "--no-access-log",
                    "--no-proxy-headers",
                ],
                cwd=BACKEND,
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            context = ssl._create_unverified_context()  # loopback fixture's self-signed certificate
            opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
            deadline = time.monotonic() + 30
            while True:
                try:
                    with opener.open(
                        Request(f"https://127.0.0.1:{api_port}/health"), timeout=2
                    ) as response:
                        if response.status == 200:
                            break
                except Exception:
                    if api_process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("E2E API did not become healthy") from None
                    time.sleep(0.3)
            worker_log = (ARTIFACTS / "worker.log").open("w", encoding="utf-8")
            worker_process = subprocess.Popen(
                [sys.executable, "-m", "app.worker"],
                cwd=BACKEND,
                env=env,
                stdout=worker_log,
                stderr=worker_log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            result = subprocess.run(
                [str(node), str(npm_cli), "run", "e2e"],
                cwd=ROOT / "frontEnd" / "jobhunter",
                env=env,
                timeout=240,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            output = result.stdout.replace(password, "[REDACTED]").replace(
                settings.database_url.get_secret_value(), "[REDACTED]"
            )
            (ARTIFACTS / "playwright.log").write_text(output, encoding="utf-8")
            print(output)
            return result.returncode
    finally:
        config_path.unlink(missing_ok=True)
        cv_fixture.unlink(missing_ok=True)
        if worker_process is not None:
            worker_process.terminate()
            try:
                worker_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker_process.kill()
                worker_process.wait(timeout=5)
        if worker_log is not None:
            worker_log.close()
        if api_process is not None:
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_process.kill()
                api_process.wait(timeout=5)
        if created:
            asyncio.run(remove_schema(settings))
            print("E2E fixture schema and credentials cleaned up.")
        cv_folder = settings.cv_storage_path.resolve()
        if cv_folder.exists():
            expected = (ARTIFACTS / "cv-storage").resolve()
            if not cv_folder.is_relative_to(expected) or cv_folder.name != settings.database_schema:
                raise RuntimeError("Refusing unsafe CV fixture cleanup")
            shutil.rmtree(cv_folder)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as error:
        print(f"Frontend E2E failed ({type(error).__name__}); no credentials displayed.")
        raise SystemExit(1) from None
