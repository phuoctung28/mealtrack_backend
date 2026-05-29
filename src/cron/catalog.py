import asyncio
import logging

logger = logging.getLogger(__name__)


class CatalogCronRunner:
    def __init__(
        self,
        *,
        coverage,
        generation,
        repo_stats,
        max_meals_per_run: int = 50,
    ) -> None:
        self._coverage = coverage
        self._generation = generation
        self._repo_stats = repo_stats
        self._max_meals_per_run = max_meals_per_run

    async def run_once(self) -> int:
        counts = self._repo_stats.count_by_cell()
        gaps = self._coverage.find_gaps(counts)
        budget = self._max_meals_per_run
        created = 0
        for gap in gaps:
            if budget <= 0:
                break
            count = min(gap.needed, budget)
            created += await self._generation.generate_for(gap.spec, count)
            budget -= count
        logger.info("catalog cron created %d meals", created)
        return created


async def _main() -> None:
    logger.warning("catalog cron wiring is not configured in this environment")


if __name__ == "__main__":
    asyncio.run(_main())
