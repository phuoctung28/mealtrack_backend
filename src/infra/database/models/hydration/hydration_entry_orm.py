"""SQLAlchemy ORM model for hydration_entries table."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index

from src.infra.database.config import Base


class HydrationEntryORM(Base):
    """Persisted hydration log entry. Primary key is a UUID string."""

    __tablename__ = "hydration_entries"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    drink_type = Column(String(32), nullable=False)
    # Per-entry volume: 1–2000 ml (enforced at application layer)
    volume_ml = Column(Integer, nullable=False)
    logged_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_hydration_entries_user_id_logged_at", "user_id", "logged_at"
        ),
    )
