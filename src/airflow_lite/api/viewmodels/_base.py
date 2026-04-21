"""ViewModel 기본 클래스.

dataclass field 기반 자동 from_model 매핑을 제공한다.
"""

from __future__ import annotations

from dataclasses import fields


class ModelMappingMixin:
    """dataclass model 의 attribute 를同名 field 에 자동 매핑."""

    @classmethod
    def from_model(cls, model) -> "ModelMappingMixin":
        field_names = {f.name for f in fields(cls)}
        mapped = {name: getattr(model, name, None) for name in field_names}
        return cls(**mapped)
