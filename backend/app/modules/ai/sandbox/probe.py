"""Known synthetic isolation probe. Never pass a real private file as canary."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

request = json.loads(sys.stdin.buffer.read(8192))
if request.get("mode") == "sleep":
    time.sleep(30)
elif request.get("mode") == "flood":
    sys.stdout.write("x" * (512 * 1024))
    raise SystemExit(0)
elif request.get("mode") == "memory":
    try:
        bytearray(512 * 1024 * 1024)
        print(json.dumps({"memory_limited": False}))
    except MemoryError:
        print(json.dumps({"memory_limited": True}))
    raise SystemExit(0)
result = {"secret_in_env": "JOBHUNTER_PROBE_SECRET" in os.environ}
config = json.loads(Path(__file__).with_name("runtime.json").read_text(encoding="ascii"))
try:
    probe = Path(config["container_folder"]) / ".jobhunter-synthetic-write-probe"
    probe.write_bytes(b"synthetic")
    probe.unlink()
    result["container_storage_write"] = True
except OSError:
    result["container_storage_write"] = False
try:
    Path(request["canary"]).read_bytes()
    result["private_file_read"] = True
except OSError:
    result["private_file_read"] = False
try:
    Path(__file__).with_suffix(".write").write_bytes(b"synthetic")
    result["runtime_write"] = True
except OSError:
    result["runtime_write"] = False
try:
    connection = socket.create_connection(("127.0.0.1", request["port"]), timeout=1)
    connection.close()
    result["network"] = True
except OSError:
    result["network"] = False
try:
    subprocess.run([sys.executable, "-I", "-S", "-c", "pass"], timeout=2, check=True)
    result["child_process"] = True
except (OSError, subprocess.SubprocessError):
    result["child_process"] = False
print(json.dumps(result))
