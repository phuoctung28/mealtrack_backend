from abc import ABC, abstractmethod
from typing import Any


class FoodMappingServicePort(ABC):
    """
    Port interface for transforming provider payloads into internal models.

    This layer isolates mapping logic and normalization rules (nutrient ID
    mapping, serving normalization, field renaming) from consumers.
    """

    @abstractmethod
    def map_search_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Transform a provider-native search result item into a simplified dict
        used by the API/application layer.

        Args:
            item: Provider-native search result dictionary.

        Returns:
            A simplified dictionary containing keys like fdc_id, name, brand, data_type.
        """
        pass

    @abstractmethod
    def map_food_details(self, details: dict[str, Any]) -> dict[str, Any]:
        """
        Transform provider-native food details into a dict capturing serving,
        calories and macro nutrients with normalized names.

        Args:
            details: Provider-native food details dictionary.

        Returns:
            A simplified dictionary with keys: fdc_id, name, brand, serving_size,
            serving_unit, calories, macros, portions.
        """
        pass

    @abstractmethod
    def map_fdc_barcode_product(
        self, item: dict[str, Any], barcode: str
    ) -> dict[str, Any]:
        """
        Transform a provider-native FDC branded row into barcode response shape.

        Args:
            item: Provider-native FDC branded search result.
            barcode: Canonical barcode to attach to the mapped result.

        Returns:
            Flat barcode product fields, including *_100g macros and source metadata.
        """
        pass
