import pytest

from src.cron.catalog import CatalogCronRunner


class FakeCoverage:
    def find_gaps(self, counts):
        from src.domain.services.crave.catalog_coverage_service import Gap

        return [Gap("lunch", "italian", 500, needed=5)]


class FakeGen:
    def __init__(self):
        self.calls = []

    async def generate_for(self, spec, count):
        self.calls.append((spec, count))
        return count


class FakeRepoStats:
    def count_by_cell(self):
        return {}


@pytest.mark.asyncio
async def test_run_once_fills_gaps_bounded_by_max():
    generation = FakeGen()
    runner = CatalogCronRunner(
        coverage=FakeCoverage(),
        generation=generation,
        repo_stats=FakeRepoStats(),
        max_meals_per_run=3,
    )

    created = await runner.run_once()

    assert created == 3
    assert generation.calls[0][1] == 3
