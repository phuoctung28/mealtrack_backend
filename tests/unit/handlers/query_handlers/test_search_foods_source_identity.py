from src.app.handlers.query_handlers.search_foods_query_handler import (
    SearchFoodsQueryHandler,
)


def test_merge_keeps_distinct_provider_ids_with_same_display_name():
    handler = SearchFoodsQueryHandler(
        cache_service=None,
        mapping_service=None,
        fat_secret_service=None,
    )

    result = handler._merge_search_results(
        [],
        [
            {
                "source": "fatsecret",
                "source_namespace": "fatsecret",
                "source_food_id": "1",
                "description": "Rice",
            },
            {
                "source": "fatsecret",
                "source_namespace": "fatsecret",
                "source_food_id": "2",
                "description": "Rice",
            },
        ],
        10,
    )

    assert [item["source_food_id"] for item in result] == ["1", "2"]
