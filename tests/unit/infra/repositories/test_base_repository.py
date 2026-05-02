from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from src.infra.repositories.base import BaseRepository


@dataclass
class _Model:
    id: str | None = None


def test_get_builds_query_chain():
    session = Mock()
    q = session.query.return_value
    q.filter.return_value.first.return_value = "x"

    repo = BaseRepository(_Model, session)
    assert repo.get("1") == "x"
    session.query.assert_called_once_with(_Model)
    assert q.filter.called
    assert q.filter.return_value.first.called


def test_add_assigns_uuid_if_missing_and_flushes():
    session = Mock()
    repo = BaseRepository(_Model, session)

    m = _Model(id=None)
    out = repo.add(m)

    assert out.id is not None and out.id != ""
    session.add.assert_called_once_with(m)
    session.flush.assert_called_once()


def test_update_adds_and_flushes():
    session = Mock()
    repo = BaseRepository(_Model, session)

    m = _Model(id="123")
    out = repo.update(m)

    assert out is m
    session.add.assert_called_once_with(m)
    session.flush.assert_called_once()


def test_delete_deletes_when_found():
    session = Mock()
    repo = BaseRepository(_Model, session)
    repo.get = Mock(return_value=_Model(id="1"))

    assert repo.delete("1") is True
    session.delete.assert_called_once()
    session.flush.assert_called_once()


def test_delete_returns_false_when_missing():
    session = Mock()
    repo = BaseRepository(_Model, session)
    repo.get = Mock(return_value=None)

    assert repo.delete("1") is False
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_async_wrappers_delegate():
    session = Mock()
    repo = BaseRepository(_Model, session)
    repo.get = Mock(return_value="x")
    repo.add = Mock(return_value="y")

    assert await repo.get_async("1") == "x"
    assert await repo.add_async(_Model()) == "y"
