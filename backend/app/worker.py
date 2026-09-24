"""Standalone durable worker entry point: ``python -m app.worker``."""

from __future__ import annotations

import asyncio
import logging
import signal

from .database import init_db
from .logging_config import setup_logging
from .post_processing import worker_loop
from .telemetry import configure_telemetry, shutdown_telemetry
from .config import settings


async def _main() -> None:
    setup_logging()
    configure_telemetry(settings)
    await init_db()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_shutdown() -> None:
        logging.getLogger(__name__).info("Worker shutdown requested; draining current job")
        stop_event.set()

    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, request_shutdown)
        except (NotImplementedError, RuntimeError):
            signal.signal(signal_name, lambda *_: loop.call_soon_threadsafe(request_shutdown))

    try:
        await worker_loop(stop_event)
    finally:
        await asyncio.to_thread(shutdown_telemetry)


if __name__ == "__main__":
    asyncio.run(_main())
