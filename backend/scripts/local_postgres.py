"""Start/stop an isolated test cluster using existing PostgreSQL binaries (no Docker).

Never uses or modifies the running system cluster or backend/.env.test.
Its generated .env.test.local contains credentials and is ignored by Git.
"""

import argparse
import os
import secrets
import socket
import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".cache" / "postgres-tests"
CONFIG = ROOT / "backend" / ".env.test.local"
BIN = Path(os.environ.get("PG_BIN", r"C:\Program Files\PostgreSQL\17\bin"))


def run(name: str, *args: str, env: dict[str, str] | None = None) -> None:
    executable = BIN / (name + (".exe" if os.name == "nt" else ""))
    result = subprocess.run(
        [str(executable), *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        env=env,
        timeout=60,
    )
    if result.returncode:
        raise SystemExit(f"{name} failed (exit {result.returncode}); no credentials displayed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "stop"])
    command = parser.parse_args().command
    # Explicit containment check before any lifecycle operation.
    if not DATA.resolve().is_relative_to(ROOT) or DATA.name != "postgres-tests":
        raise SystemExit("Unsafe cluster path")
    if command == "stop":
        if (DATA / "postmaster.pid").exists():
            run("pg_ctl", "-D", str(DATA), "-m", "fast", "-w", "stop")
        print("Dedicated test cluster stopped; system PostgreSQL untouched.")
        return
    running = (DATA / "postmaster.pid").exists()
    if DATA.exists():
        if not CONFIG.exists():
            raise SystemExit("Existing fixture cluster without config; refusing to overwrite")
        values = dotenv_values(CONFIG)
        port = str(values["TEST_CLUSTER_PORT"])
    else:
        if CONFIG.exists():
            raise SystemExit("Existing fixture config; refusing to overwrite")
        DATA.parent.mkdir(parents=True, exist_ok=True)
        password = secrets.token_urlsafe(32)
        password_file = DATA.parent / "postgres-tests-init.secret"
        try:
            password_file.write_text(password, encoding="utf-8")
            password_file.chmod(0o600)
            run(
                "initdb",
                "-D",
                str(DATA),
                "-U",
                "jobhunter_test",
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
                f"--pwfile={password_file}",
            )
        finally:
            password_file.unlink(missing_ok=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = str(sock.getsockname()[1])
        CONFIG.write_text(
            f"DATABASE_URL=postgresql+asyncpg://jobhunter_test:{password}@127.0.0.1:{port}/jobhunter_test\n"
            f"TEST_CLUSTER_PORT={port}\n",
            encoding="utf-8",
        )
        CONFIG.chmod(0o600)
    if not running:
        run(
            "pg_ctl",
            "-D",
            str(DATA),
            "-l",
            str(DATA.parent / "postgres-tests.log"),
            "-o",
            f"-p {port} -h 127.0.0.1",
            "-w",
            "start",
        )
    if not (DATA / "jobhunter_database_created").exists():
        from sqlalchemy.engine import make_url

        url = make_url(str(dotenv_values(CONFIG)["DATABASE_URL"]))
        env = os.environ.copy()
        env["PGPASSWORD"] = str(url.password)
        run(
            "createdb",
            "-h",
            "127.0.0.1",
            "-p",
            port,
            "-U",
            "jobhunter_test",
            "jobhunter_test",
            env=env,
        )
        (DATA / "jobhunter_database_created").touch()
    print("Dedicated PostgreSQL fixture started. Use JOBHUNTER_TEST_ENV=.env.test.local.")


if __name__ == "__main__":
    main()
