from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Integer, String

from src.infra.database.config import Base


class UserTasteProfile(Base):
    __tablename__ = "user_taste_profile"

    user_id = Column(String(128), primary_key=True)
    cuisine_affinity = Column(JSON, nullable=False, default=dict)
    ingredient_affinity = Column(JSON, nullable=False, default=dict)
    tag_affinity = Column(JSON, nullable=False, default=dict)
    macro_shape_pref = Column(JSON, nullable=False, default=dict)
    taste_embedding = Column(Vector(512), nullable=True)
    swipe_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
