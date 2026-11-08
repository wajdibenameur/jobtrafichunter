"""Prepare an isolated, secret-free Python runtime for Windows AppContainer.

Only developer runtime files are copied; never copy backend config/site-packages.
No document parsing is performed by this setup command.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
RUNTIME = PROJECT / ".cache" / "cv-sandbox"
SOURCE = PROJECT / "backend/app/modules/ai/sandbox"


def main() -> None:
    if sys.platform != "win32" or sys.version_info[:2] != (3, 11):
        raise SystemExit("Windows / Python 3.11 required")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    base = Path(sys.base_prefix)
    for name in ("python.exe", "python311.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        if (base / name).exists():
            shutil.copy2(base / name, RUNTIME / name)
    dlls = RUNTIME / "DLLs"
    dlls.mkdir(exist_ok=True)
    for source in (base / "DLLs").iterdir():
        if source.suffix.lower() in {".dll", ".pyd"}:
            shutil.copy2(source, dlls / source.name)
    library = base / "Lib"
    with zipfile.ZipFile(RUNTIME / "python311.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for source in library.rglob("*.py"):
            relative = source.relative_to(library)
            if not any(
                p in {"site-packages", "test", "tests", "idlelib", "tkinter"}
                for p in relative.parts
            ):
                archive.write(source, relative.as_posix())
    (RUNTIME / "python311._pth").write_text("python311.zip\nDLLs\n.\n", encoding="ascii")
    shutil.copy2(SOURCE / "probe.py", RUNTIME / "probe.py")
    profile = "JobHunter.CvParser." + hashlib.sha256(str(PROJECT).encode()).hexdigest()[:16]
    system = Path(os.environ.get("SYSTEMROOT", "C:/Windows"))
    build_temp = PROJECT / ".cache" / "cv-build"
    build_temp.mkdir(exist_ok=True)
    environment = {
        "SYSTEMROOT": str(system),
        "PATH": str(system / "System32"),
        "TEMP": str(build_temp),
        "TMP": str(build_temp),
    }
    compiler = system / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    runner = RUNTIME / "Runner.exe"
    result = subprocess.run(
        [
            str(compiler),
            "/nologo",
            "/target:exe",
            "/platform:x64",
            f"/out:{runner}",
            str(SOURCE / "Runner.cs"),
        ],
        env=environment,
        capture_output=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise SystemExit("Sandbox helper compilation failed")
    result = subprocess.run(
        [str(runner), profile, "--sid"],
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sid = result.stdout.decode("ascii", errors="strict").strip()
    if (
        result.returncode
        or not sid.startswith("S-1-15-2-")
        or not all(c.isdigit() or c in "S-" for c in sid)
    ):
        raise SystemExit("AppContainer profile creation failed")
    # Grant read/execute only to this private package SID, on copied runtime only.
    # Never grant access to backend, .env, original CV files or the master Python.
    result = subprocess.run(
        [
            str(system / "System32/icacls.exe"),
            str(RUNTIME),
            "/grant:r",
            f"*{sid}:(OI)(CI)(RX)",
            "/T",
            "/Q",
        ],
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise SystemExit("Sandbox runtime ACL preparation failed")
    (RUNTIME / "runtime.json").write_text(json.dumps({"profile": profile}), encoding="ascii")
    print("Secret-free runtime prepared. Isolation probes still required before document parsing.")


if __name__ == "__main__":
    main()
