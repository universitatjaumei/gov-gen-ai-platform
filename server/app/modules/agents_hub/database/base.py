"""Bases ORM de SQLAlchemy para agents_hub."""
from typing import Any

from sqlalchemy import ARRAY, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class HubConfigBase(DeclarativeBase):
    """Modelos de configuración: se sincronizan de cloud a edge."""
    type_annotation_map = {dict[str, Any]: JSONB, list[str]: ARRAY(String)}


class HubOperationalBase(DeclarativeBase):
    """Modelos operacionales: viven sólo en el edge node."""
    type_annotation_map = {dict[str, Any]: JSONB, list[str]: ARRAY(String)}
