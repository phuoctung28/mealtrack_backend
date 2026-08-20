"""ORM for angle-tolerant meal scan visual identities."""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from src.infra.database.base import Base


class MealScanVisualIdentityORM(Base):
    """Stores AI visual identity + scene signature for a scanned meal."""

    __tablename__ = "meal_scan_visual_identity"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    meal_id = Column(
        String(36),
        ForeignKey("meal.meal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source = Column(String(20), nullable=False)
    dish_slug = Column(String(128), nullable=False)
    ingredients = Column(JSON, nullable=False, default=list)
    container = Column(String(64), nullable=True)
    background = Column(String(64), nullable=True)
    identity_key = Column(String(255), nullable=False)
    scene_signature = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
