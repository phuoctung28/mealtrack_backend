"""Neutral SQLAlchemy declarative base shared by runtime and migrations."""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class with async attribute support."""
