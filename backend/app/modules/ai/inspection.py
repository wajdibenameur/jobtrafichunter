import asyncio
import base64
import json
import socket
import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.ai.windows_sandbox import WindowsSandbox
from app.shared.document import DocumentInspection

PARSER_ERRORS = {
    "CV_FORMAT_INVALID",
    "CV_DOCUMENT_LIMIT",
    "CV_UNSAFE_DOCUMENT",
    "CV_ENCRYPTED_DOCUMENT",
    "CV_DOC_UNAVAILABLE",
    "CV_SIZE_INVALID",
}


class LocalDocumentInspector:
    def __init__(self, runtime: Path) -> None:
        self.sandbox = WindowsSandbox(runtime)
        self._verified = False
        self._lock = asyncio.Lock()

    async def verify(self) -> None:
        async with self._lock:
            if self._verified:
                return
            # Private synthetic canary, never a user document or actual secret.
            folder = await asyncio.to_thread(tempfile.TemporaryDirectory)
            try:
                canary = Path(folder.name) / "synthetic-canary.txt"
                await asyncio.to_thread(canary.write_bytes, b"jobhunter synthetic canary")
                with socket.socket() as server:
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    probe = await self.sandbox.invoke(
                        "probe.py",
                        json.dumps(
                            {
                                "canary": str(canary),
                                "port": server.getsockname()[1],
                            }
                        ).encode(),
                    )
                    if json.loads(probe) != {
                        "secret_in_env": False,
                        "container_storage_write": False,
                        "private_file_read": False,
                        "runtime_write": False,
                        "network": False,
                        "child_process": False,
                    }:
                        raise AppError(
                            "CV_ISOLATION_FAILED", "CV parser isolation check failed", 503
                        )
                    server.settimeout(0.01)
                    try:
                        connection, _ = server.accept()
                    except TimeoutError:
                        self._verified = True
                    else:
                        connection.close()
                        raise AppError(
                            "CV_ISOLATION_FAILED", "CV parser isolation check failed", 503
                        )
            finally:
                await asyncio.to_thread(folder.cleanup)

    async def __call__(
        self, content: bytes, filename: str, content_type: str
    ) -> DocumentInspection:
        if not content or len(content) > 5 * 1024 * 1024:
            raise AppError("CV_SIZE_INVALID", "CV size must be between 1 byte and 5 MiB", 413)
        await self.verify()
        output = await self.sandbox.invoke(
            "extract.py",
            json.dumps(
                {
                    "content": base64.b64encode(content).decode("ascii"),
                    "filename": filename,
                    "content_type": content_type,
                }
            ).encode(),
        )
        try:
            data = json.loads(output)
            if isinstance(data, dict) and data.get("error") in PARSER_ERRORS:
                raise AppError(data["error"], "CV document cannot be processed safely", 422)
            inspection = DocumentInspection.model_validate(data)
            if sum(len(p.text) for p in inspection.pages) > 50000:
                raise ValueError
            return inspection
        except (ValueError, TypeError, ValidationError):
            raise AppError(
                "CV_PARSER_RESPONSE_INVALID", "Invalid CV parser response", 503
            ) from None
