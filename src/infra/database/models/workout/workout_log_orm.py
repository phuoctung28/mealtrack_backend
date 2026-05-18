"""SQLAlchemy ORM model for workout_logs table."""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey, Index

from src.infra.database.config import Base


class WorkoutLogORM(Base):
    """Persisted workout session. Primary key is a UUID string."""

    __tablename__ = "workout_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    workout_type = Column(String(32), nullable=False)
    intensity = Column(String(16), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    met_value = Column(Numeric(4, 2), nullable=False)
    weight_kg_snapshot = Column(Numeric(5, 2), nullable=True)
    estimated_burn_kcal = Column(Numeric(7, 1), nullable=True)
    logged_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_workout_logs_user_id_logged_at", "user_id", "logged_at"),
    )
