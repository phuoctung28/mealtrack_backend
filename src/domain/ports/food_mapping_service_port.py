from abc import ABC, abstractmethod
from typing import Any, Dict


class FoodMappingServicePort(ABC):
    """
    Port interface for transforming provider payloads into internal models.

    This layer isolates mapping logic and normalization rules (nutrient ID
    mapping, serving normalization, field renaming) from consumers.
    """

    @abstractmethod
    def map_search_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
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
    def map_food_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
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
