import json
import socket
import sys
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.modules.ai.windows_sandbox import WindowsSandbox

RUNTIME = Path(__file__).resolve().parents[5] / ".cache/cv-sandbox"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows AppContainer security contract")
async def test_actual_appcontainer_blocks_private_file_network_write_and_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not (RUNTIME / "runtime.json").exists():
        pytest.fail("Prepare the Windows runtime with scripts/setup_cv_sandbox.py first")
    canary = tmp_path / "synthetic-canary.txt"
    canary.write_text("synthetic probe only", encoding="ascii")
    monkeypatch.setenv("JOBHUNTER_PROBE_SECRET", "synthetic-environment-canary")
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        output = await WindowsSandbox(RUNTIME).invoke(
            "probe.py",
            json.dumps({"canary": str(canary), "port": server.getsockname()[1]}).encode(),
        )
        assert json.loads(output) == {
            "secret_in_env": False,
            "container_storage_write": False,
            "private_file_read": False,
            "runtime_write": False,
            "network": False,
            "child_process": False,
        }
        server.settimeout(0.05)
        with pytest.raises(TimeoutError):
            server.accept()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows AppContainer security contract")
async def test_actual_job_enforces_memory_and_output_and_deadline() -> None:
    sandbox = WindowsSandbox(RUNTIME)
    assert json.loads(await sandbox.invoke("probe.py", b'{"mode":"memory"}')) == {
        "memory_limited": True
    }
    with pytest.raises(AppError) as flood:
        await sandbox.invoke("probe.py", b'{"mode":"flood"}')
    assert flood.value.code == "CV_PARSER_OUTPUT_LIMIT"
    with pytest.raises(AppError) as timeout:
        await sandbox.invoke("probe.py", b'{"mode":"sleep"}', deadline_seconds=0.5)
    assert timeout.value.code == "CV_PARSER_TIMEOUT"


async def test_missing_runtime_and_non_allowlisted_script_fail_closed(tmp_path: Path) -> None:
    sandbox = WindowsSandbox(tmp_path)
    for script in ("probe.py", "../untrusted.py"):
        with pytest.raises(AppError) as error:
            await sandbox.invoke(script, b"{}")
        assert error.value.code == "CV_SANDBOX_UNAVAILABLE"
