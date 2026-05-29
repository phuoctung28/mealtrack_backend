from dataclasses import dataclass

from src.domain.services.crave.catalog_generation_service import GenSpec


@dataclass
class Gap:
    meal_type: str
    cuisine: str
    calorie_band: int
    needed: int

    @property
    def spec(self) -> GenSpec:
        return GenSpec(self.meal_type, self.cuisine, self.calorie_band)


class CatalogCoverageService:
    def __init__(
        self,
        *,
        meal_types: list[str],
        cuisines: list[str],
        bands: list[int],
        target_per_cell: int = 20,
    ) -> None:
        self._meal_types = meal_types
        self._cuisines = cuisines
        self._bands = bands
        self._target_per_cell = target_per_cell

    def find_gaps(self, counts: dict[tuple[str, str, int], int]) -> list[Gap]:
        gaps = []
        for meal_type in self._meal_types:
            for cuisine in self._cuisines:
                for band in self._bands:
                    have = counts.get((meal_type, cuisine, band), 0)
                    if have < self._target_per_cell:
                        gaps.append(
                            Gap(meal_type, cuisine, band, self._target_per_cell - have)
                        )

        gaps.sort(key=lambda gap: gap.needed, reverse=True)
        return gaps
