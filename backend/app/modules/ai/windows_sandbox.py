"""Fail-closed Windows AppContainer runner for developer-owned parser scripts."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from app.core.errors import AppError

MAX_OUTPUT = 256 * 1024


class WindowsSandbox:
    def __init__(self, runtime: Path) -> None:
        self.runtime = runtime.resolve()

    async def invoke(self, script: str, payload: bytes, *, deadline_seconds: float = 20) -> bytes:
        if sys.platform != "win32" or script not in {"probe.py", "extract.py"}:
            raise AppError("CV_SANDBOX_UNAVAILABLE", "Isolated CV parser unavailable", 503)
        if len(payload) > 8 * 1024 * 1024:
            raise AppError("CV_SIZE_INVALID", "CV parser input too large", 413)
        try:
            raw = await asyncio.to_thread(
                (self.runtime / "runtime.json").read_text, encoding="ascii"
            )
            config = json.loads(raw)
            profile = config["profile"]
            if not isinstance(profile, str) or not profile.startswith("JobHunter.CvParser."):
                raise ValueError
        except (OSError, ValueError, KeyError, TypeError):
            raise AppError(
                "CV_SANDBOX_UNAVAILABLE", "Isolated CV parser unavailable", 503
            ) from None
        system = Path(os.environ.get("SYSTEMROOT", "C:/Windows"))
        environment = {
            name: os.environ[name]
            for name in ("SYSTEMROOT", "USERPROFILE", "LOCALAPPDATA", "TEMP", "TMP")
            if name in os.environ
        }
        environment["PATH"] = str(system / "System32")
        try:
            process = await asyncio.create_subprocess_exec(
                str(self.runtime / "Runner.exe"),
                profile,
                str(self.runtime / "python.exe"),
                str(self.runtime / script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=environment,
                cwd=str(self.runtime),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError:
            raise AppError(
                "CV_SANDBOX_UNAVAILABLE", "Isolated CV parser unavailable", 503
            ) from None

        async def send() -> None:
            assert process.stdin is not None
            try:
                process.stdin.write(payload)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.stdin.close()

        async def receive() -> bytes:
            assert process.stdout is not None
            result = bytearray()
            while data := await process.stdout.read(8192):
                result.extend(data)
                if len(result) > MAX_OUTPUT:
                    raise AppError("CV_PARSER_OUTPUT_LIMIT", "CV parser output limit exceeded", 422)
            return bytes(result)

        tasks = [asyncio.create_task(send()), asyncio.create_task(receive())]
        try:
            async with asyncio.timeout(deadline_seconds):
                _, output = await asyncio.gather(*tasks)
                if await process.wait():
                    raise AppError("CV_SANDBOX_FAILED", "Isolated CV parser failed", 503)
                assert isinstance(output, bytes)
                return output
        except TimeoutError:
            raise AppError("CV_PARSER_TIMEOUT", "CV parser time limit exceeded", 422) from None
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if process.returncode is None:
                # Closing the launcher's Job Object kills the isolated child too.
                process.kill()
            # Proactor transports wait for pipe EOF. Discard buffered stdout
            # after termination: an over-limit producer must not deadlock wait().
            assert process.stdout is not None
            async with asyncio.timeout(5):
                while await process.stdout.read(8192):
                    pass
                await process.wait()
