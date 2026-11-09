"""Local PostgreSQL search worker. --once checks DB and processes one task cycle."""

import argparse
import asyncio
import logging
import signal
import traceback
from pathlib import Path
from types import FrameType

from app.core.db import Runtime, make_runtime
from app.core.logging import configure_logging
from app.core.settings import Settings
from app.modules.auth import AuthService
from app.modules.cv import CvMaintenance
from app.modules.search import SearchQueue
from app.modules.sources import SourceService

# This composition root must register all tables referenced by worker-owned writes,
# even when the API is running in a different process.
assert AuthService is not None and SourceService is not None

logger = logging.getLogger("jobhunter.worker")


async def run_worker(runtime: Runtime, stop: asyncio.Event, *, once: bool = False) -> None:
    try:
        while not stop.is_set():
            recovered = await CvMaintenance(runtime).run_once()
            processed = await SearchQueue(runtime).run_once()
            processed = processed or recovered
            logger.info("worker_cycle_completed" if processed else "worker_idle")
            if once:
                return
            try:
                await asyncio.wait_for(stop.wait(), timeout=1 if processed else 2)
            except TimeoutError:
                pass
    finally:
        await runtime.engine.dispose()
        logger.info("worker_stopped")


async def start(*, once: bool) -> None:
    configure_logging()
    runtime = make_runtime(Settings())
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop(signum: int, frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(stop.set)

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, request_stop)
    await run_worker(runtime, stop, once=once)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once", action="store_true", help="Check DB, process one task cycle and exit"
    )
    args = parser.parse_args()
    try:
        asyncio.run(start(once=args.once))
    except Exception as exc:
        # Locations and exception type only: never SQL parameters or imported text.
        locations = ",".join(
            f"{Path(frame.filename).name}:{frame.lineno}"
            for frame in traceback.extract_tb(exc.__traceback__)[-4:]
        )
        logger.error("worker_failed_%s_at_%s", type(exc).__name__, locations)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
