"""Browse page renderers.

Each renderer receives a page-specific context and passes it through to the
template so templates can render real data (or an empty state) instead of
relying on static placeholder text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Context dataclasses — stable presentation contracts for each Browse page
# ---------------------------------------------------------------------------


@dataclass
class BrowseBackfillsContext:
    """Context for the Browse > Backfills page."""

    backfills: list[Any] = field(default_factory=list)
    total_count: int = 0
    pending_count: int = 0
    running_count: int = 0


@dataclass
class BrowseJobsContext:
    """Context for the Browse > Jobs page."""

    jobs: list[Any] = field(default_factory=list)
    total_count: int = 0
    active_count: int = 0
    search_query: str = ""
    selected_type: str = "all"


@dataclass
class BrowseAuditLogsContext:
    """Context for the Browse > Audit Logs page."""

    audit_logs: list[Any] = field(default_factory=list)
    total_count: int = 0
    search_query: str = ""
    selected_action: str = "all"
    selected_user: str = ""
    users: list[str] = field(default_factory=list)


@dataclass
class BrowseTaskInstancesContext:
    """Context for the Browse > Task Instances page."""

    task_instances: list[Any] = field(default_factory=list)
    total_count: int = 0
    running_count: int = 0
    failed_count: int = 0
    search_query: str = ""
    selected_status: str = "all"
    selected_dag: str = ""
    dag_ids: list[str] = field(default_factory=list)


@dataclass
class BrowseDagRunsContext:
    """Context for the Browse > DAG Runs page."""

    dag_runs: list[Any] = field(default_factory=list)
    total_count: int = 0
    running_count: int = 0
    failed_count: int = 0
    search_query: str = ""
    selected_status: str = "all"
    selected_dag: str = ""
    dag_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render_browse_page(
    template_name: str,
    *,
    title_key: str,
    subtitle_key: str,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
    **context: Any,
) -> str:
    """Render a Browse page with the given page-specific context.

    Extra keyword arguments are forwarded verbatim to the template so each
    Browse page can receive its own data (counts, rows, filter state, ...).
    """
    chrome = PageChrome(
        title=t(language, title_key),
        subtitle=t(language, subtitle_key),
        active_path=active_path,
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, title_key), None),
        ],
    )
    return render_page(template_name, chrome=chrome, language=language, **context)
