from __future__ import annotations

import asyncio
import logging
import os

from src.infra.config.settings import settings
from src.worker.consumer import run_worker_forever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _async_main() -> None:
    role = os.getenv("SERVICE_ROLE", settings.SERVICE_ROLE)
    logger.info("Starting worker process (SERVICE_ROLE=%s)", role)

    if role != "worker":
        logger.error(
            "SERVICE_ROLE is '%s', but worker.main was invoked. "
            "Set SERVICE_ROLE=worker for this process.",
            role,
        )
        return

    await run_worker_forever()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()

