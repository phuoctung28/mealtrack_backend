from src.app.services.web_funnel_claim_completion import _result


def test_claim_result_derives_calories_from_server_macro_values() -> None:
    result = _result({"birth_year": 1995, "birth_month": 4, "birth_day": 20, "gender": "female", "height": 168, "weight": 62, "job_type": "desk", "training_days_per_week": 3, "training_minutes_per_session": 45, "goal": "recomp", "custom_protein_g": 110, "custom_carbs_g": 200, "custom_fat_g": 60})
    assert result["version"] == "claim_result_v1"
    assert result["macros"]["calories"] == 1780
