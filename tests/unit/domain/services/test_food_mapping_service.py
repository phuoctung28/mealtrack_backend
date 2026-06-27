from src.domain.services.food_mapping_service import FoodMappingService


def test_map_fdc_barcode_product_returns_flat_barcode_shape():
    service = FoodMappingService()

    result = service.map_fdc_barcode_product(
        {
            "fdcId": 1,
            "description": "Test Cereal",
            "brandOwner": "Test Brand",
            "servingSize": 30,
            "servingSizeUnit": "g",
            "foodNutrients": [
                {"nutrientId": 1003, "value": 8},
                {"nutrientId": 1005, "value": 72},
                {"nutrientId": 1004, "value": 2.5},
                {"nutrientId": 1079, "value": 6},
                {"nutrientId": 2000, "value": 18},
            ],
        },
        barcode="00036000291452",
    )

    assert result["name"] == "Test Cereal"
    assert result["brand"] == "Test Brand"
    assert result["barcode"] == "00036000291452"
    assert result["protein_100g"] == 8
    assert result["carbs_100g"] == 72
    assert result["fat_100g"] == 2.5
    assert result["fiber_100g"] == 6
    assert result["sugar_100g"] == 18
    assert result["source"] == "usda_fdc"
    assert result["is_verified"] is True

