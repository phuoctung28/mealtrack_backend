"""Cheat day database model."""
from sqlalchemy import Column, String, Date, DateTime, UniqueConstraint, Index
from src.infra.database.config import Base


class CheatDay(Base):
    __tablename__ = 'cheat_days'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    date = Column(Date, nullable=False)
    marked_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_user_cheat_date'),
        Index('ix_user_cheat_date', 'user_id', 'date'),
    )

    def to_domain(self):
        from src.domain.model.cheat_day import CheatDay as DomainCheatDay
        return DomainCheatDay(
            cheat_day_id=self.id,
            user_id=self.user_id,
            date=self.date,
            marked_at=self.marked_at,
        )

    @classmethod
    def from_domain(cls, domain):
        return cls(
            id=domain.cheat_day_id,
            user_id=domain.user_id,
            date=domain.date,
            marked_at=domain.marked_at,
        )
