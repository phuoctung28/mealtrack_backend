from __future__ import annotations

from typing import Optional

from sqlalchemy import func


def local_date_expr(session, dt_col, user_timezone: Optional[str]) -> object:
    """
    SQL expression for grouping a UTC timestamp into the user's local DATE.

    Supports:
    - PostgreSQL: DATE(timezone(tz, timestamptz))
    - SQLite: DATE(ts) (tests)

    This project targets PostgreSQL in production (SQLite in tests).
    """
    if not user_timezone or user_timezone == "UTC":
        return func.date(dt_col)

    dialect = getattr(getattr(session, "bind", None), "dialect", None)
    dialect_name = getattr(dialect, "name", "") if dialect else ""

    if dialect_name == "postgresql":
        return func.date(func.timezone(user_timezone, dt_col))

    return func.date(dt_col)

