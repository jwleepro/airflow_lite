"""Presentation view models used by the WebUI renderers.

View models are decoupled from `airflow_lite.storage.models` so that UI
code (templates, renderers) does not depend on persistence layer types.
"""

from airflow_lite.api.viewmodels.admin import (
    AdminPageViewData,
    ConnectionVM,
    PoolVM,
    VariableVM,
)

__all__ = [
    "AdminPageViewData",
    "ConnectionVM",
    "PoolVM",
    "VariableVM",
]
