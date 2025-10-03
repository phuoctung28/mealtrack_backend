"""
Test table model for migration testing.
"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class TestTable(Base, BaseMixin):
    """Simple test table for migration testing."""
    __tablename__ = 'test_table'
    
    # Test fields
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    test_number = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<TestTable(id={self.id}, name='{self.name}')>"
