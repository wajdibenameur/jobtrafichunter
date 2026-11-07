"""Worker lifecycle scaffold. Search task handlers and queue arrive in phase 3."""

import argparse
import asyncio
import logging
import signal
from types import FrameType

from sqlalchemy import text

from app.core.db import Runtime, make_runtime
from app.core.logging import configure_logging
from app.core.settings import Settings

logger = logging.getLogger("jobhunter.worker")


async def run_worker(runtime: Runtime, stop: asyncio.Event, *, once: bool = False) -> None:
    try:
        while not stop.is_set():
            async with runtime.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            logger.info("worker_idle_no_task_handlers_registered")
            if once:
                return
            try:
                await asyncio.wait_for(stop.wait(), timeout=30)
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
    parser.add_argument("--once", action="store_true", help="Check DB and exit; no task processing")
    args = parser.parse_args()
    try:
        asyncio.run(start(once=args.once))
    except Exception:
        logger.error("worker_startup_failed")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
