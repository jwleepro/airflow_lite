"""Admin page renderers."""

from __future__ import annotations

from airflow_lite.api.paths import (
    MONITOR_ADMIN_CONFIG_PATH,
    MONITOR_ADMIN_CONNECTIONS_PATH,
    MONITOR_ADMIN_PATH,
    MONITOR_ADMIN_PLUGINS_PATH,
    MONITOR_ADMIN_POOLS_PATH,
    MONITOR_ADMIN_PROVIDERS_PATH,
    MONITOR_ADMIN_VARIABLES_PATH,
    MONITOR_ADMIN_XCOMS_PATH,
    MONITOR_PATH,
)
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.viewmodels import AdminPageViewData
from airflow_lite.api.webui_helpers import t

_PLACEHOLDER_CONNECTIONS = [
    {"conn_id": "source_db_a", "conn_type": "postgres", "host": "db.internal", "port": 5432, "schema": "events_db", "description": "Primary events database"},
    {"conn_id": "source_db_b", "conn_type": "postgres", "host": "db2.internal", "port": 5432, "schema": "users_db", "description": "User database"},
    {"conn_id": "warehouse", "conn_type": "postgres", "host": "warehouse.internal", "port": 5432, "schema": "analytics", "description": "Data warehouse"},
]

_PLACEHOLDER_VARIABLES = [
    {"key": "data_interval_days", "val": "7", "description": "Rolling window for data processing", "is_masked": False},
    {"key": "slack_channel", "val": "#data-alerts", "description": "Default Slack channel", "is_masked": False},
    {"key": "db_password", "val": "••••••••", "description": "Production DB password", "is_masked": True},
]

_PLACEHOLDER_POOLS = [
    {"pool_name": "default_pool", "slots": 128, "running": 23, "queued": 5, "description": "Default task pool"},
    {"pool_name": "ml_pool", "slots": 16, "running": 8, "queued": 2, "description": "ML training tasks"},
    {"pool_name": "db_pool", "slots": 32, "running": 12, "queued": 0, "description": "Database operations"},
]

_PLACEHOLDER_PROVIDERS = [
    {"name": "apache-airflow-providers-google", "version": "10.22.0", "hooks": 48, "operators": 91, "sensors": 31, "docs_url": "https://airflow.apache.org/docs/"},
    {"name": "apache-airflow-providers-postgres", "version": "5.12.0", "hooks": 2, "operators": 3, "sensors": 1, "docs_url": "https://airflow.apache.org/docs/"},
    {"name": "apache-airflow-providers-amazon", "version": "8.25.0", "hooks": 52, "operators": 134, "sensors": 47, "docs_url": "https://airflow.apache.org/docs/"},
]

_PLACEHOLDER_CONFIG = {
    "core": {
        "dags_folder": "/opt/airflow/dags",
        "executor": "CeleryExecutor",
        "parallelism": "32",
        "max_active_runs_per_dag": "16",
        "load_examples": "False",
    },
    "scheduler": {
        "job_heartbeat_sec": "5",
        "scheduler_heartbeat_sec": "5",
        "num_runs": "-1",
        "processor_poll_interval": "1",
    },
    "webserver": {
        "base_url": "https://airflow.company.com",
        "web_server_port": "8080",
        "secret_key": "**masked**",
        "workers": "4",
    },
}

_PLACEHOLDER_XCOMS = [
    {"dag_id": "etl_daily_pipeline", "task_id": "extract_source_a", "key": "return_value", "value": '{"row_count": 45231}', "timestamp": "Today 06:04"},
    {"dag_id": "etl_daily_pipeline", "task_id": "validate_schema", "key": "return_value", "value": '{"valid": true, "rows": 45231}', "timestamp": "Today 06:05"},
]


def _make_chrome(*, language: str, title: str, subtitle: str, active_path: str) -> PageChrome:
    return PageChrome(
        title=title,
        subtitle=subtitle,
        active_path=active_path,
        page_tag=t(language, "webui.layout.page_tag.service_status"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.layout.nav.admin"), None),
        ],
    )


def _connections(view_data: AdminPageViewData) -> list:
    return view_data.connections or _PLACEHOLDER_CONNECTIONS


def _variables(view_data: AdminPageViewData) -> list:
    rows = []
    for variable in view_data.variables:
        masked = "password" in (variable.key or "").lower() or "secret" in (variable.key or "").lower()
        rows.append(
            {
                "key": variable.key,
                "val": "••••••••" if masked and variable.val else variable.val,
                "description": variable.description,
                "is_masked": masked,
            }
        )
    return rows or _PLACEHOLDER_VARIABLES


def _pools(view_data: AdminPageViewData) -> list:
    rows = []
    for pool in view_data.pools:
        rows.append(
            {
                "pool_name": pool.pool_name,
                "slots": pool.slots,
                "running": 0,
                "queued": 0,
                "description": pool.description,
            }
        )
    return rows or _PLACEHOLDER_POOLS


def render_admin_page(view_data: AdminPageViewData, *, language: str, error: str | None = None) -> str:
    chrome = _make_chrome(
        language=language,
        title=t(language, "webui.layout.nav.admin"),
        subtitle=t(language, "webui.admin.subtitle"),
        active_path=MONITOR_ADMIN_PATH,
    )
    return render_page(
        "admin.html",
        chrome=chrome,
        language=language,
        connections=_connections(view_data),
        variables=_variables(view_data),
        pools=_pools(view_data),
        error=error,
    )


def render_admin_connections_page(view_data: AdminPageViewData, *, language: str, error: str | None = None) -> str:
    return render_page(
        "admin/admin_connections.html",
        chrome=_make_chrome(language=language, title="Connections", subtitle="Connection inventory and quick actions", active_path=MONITOR_ADMIN_CONNECTIONS_PATH),
        language=language,
        connections=_connections(view_data),
        error=error,
    )


def render_admin_variables_page(view_data: AdminPageViewData, *, language: str, error: str | None = None) -> str:
    return render_page(
        "admin/admin_variables.html",
        chrome=_make_chrome(language=language, title="Variables", subtitle="Runtime key-value settings and secrets", active_path=MONITOR_ADMIN_VARIABLES_PATH),
        language=language,
        variables=_variables(view_data),
        error=error,
    )


def render_admin_pools_page(view_data: AdminPageViewData, *, language: str, error: str | None = None) -> str:
    return render_page(
        "admin/admin_pools.html",
        chrome=_make_chrome(language=language, title="Pools", subtitle="Concurrency pools and slot utilization", active_path=MONITOR_ADMIN_POOLS_PATH),
        language=language,
        pools=_pools(view_data),
        error=error,
    )


def render_admin_providers_page(*, language: str) -> str:
    return render_page(
        "admin/admin_providers.html",
        chrome=_make_chrome(language=language, title="Providers", subtitle="Installed provider packages and capability counts", active_path=MONITOR_ADMIN_PROVIDERS_PATH),
        language=language,
        providers=_PLACEHOLDER_PROVIDERS,
    )


def render_admin_plugins_page(*, language: str) -> str:
    return render_page(
        "admin/admin_plugins.html",
        chrome=_make_chrome(language=language, title="Plugins", subtitle="Plugin registry and extension status", active_path=MONITOR_ADMIN_PLUGINS_PATH),
        language=language,
        plugins=[],
        plugin_docs_url="https://airflow.apache.org/docs/",
    )


def render_admin_config_page(*, language: str) -> str:
    return render_page(
        "admin/admin_config.html",
        chrome=_make_chrome(language=language, title="Configuration", subtitle="Effective webserver, core, and scheduler settings", active_path=MONITOR_ADMIN_CONFIG_PATH),
        language=language,
        config_sections=_PLACEHOLDER_CONFIG,
    )


def render_admin_xcoms_page(*, language: str) -> str:
    return render_page(
        "admin/admin_xcoms.html",
        chrome=_make_chrome(language=language, title="XComs", subtitle="Recent cross-task payloads and metadata", active_path=MONITOR_ADMIN_XCOMS_PATH),
        language=language,
        xcoms=_PLACEHOLDER_XCOMS,
    )
