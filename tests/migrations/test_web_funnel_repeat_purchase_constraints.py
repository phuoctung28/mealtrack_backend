from pathlib import Path

from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelRedemption,
)

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260809000001_allow_repeat_web_funnel_purchases.py"
)


def test_repeat_purchase_migration_drops_only_global_uid_constraints() -> None:
    migration_text = MIGRATION_PATH.read_text()

    assert migration_text.count("op.drop_constraint(") == 3
    assert '"web_funnel_leads_claimed_uid_key"' in migration_text
    assert '"web_funnel_redemptions_redeemer_uid_key"' in migration_text
    assert '"web_funnel_redemptions_finalized_uid_key"' in migration_text
    assert '"web_funnel_redemptions_finalization_key_hash_key"' not in migration_text
    assert '"uq_web_funnel_redemptions_redemption_link_hash"' not in migration_text


def test_repeat_purchase_models_allow_one_user_across_multiple_purchase_rows() -> None:
    assert WebFunnelLead.__table__.c.claimed_uid.unique is not True
    assert WebFunnelRedemption.__table__.c.redeemer_uid.unique is not True
    assert WebFunnelRedemption.__table__.c.finalized_uid.unique is not True

    assert WebFunnelRedemption.__table__.c.finalization_key_hash.unique is True
    assert WebFunnelRedemption.__table__.c.redemption_link_hash.unique is True
