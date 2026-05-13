"""Declarative Base for all ORM models.

The single `Base` is the canonical SQLAlchemy registry that alembic's
``target_metadata`` points at. Adding a new model = importing it from this
package's ``__init__`` so its table attaches to ``Base.metadata``.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base."""
