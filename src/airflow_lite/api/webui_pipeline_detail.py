"""Pipeline detail (dag details) page renderer."""

from __future__ import annotations

from airflow_lite.api.paths import (
    MONITOR_PATH,
    MONITOR_PIPELINES_PATH,
    PIPELINES_PATH,
    monitor_pipeline_backfill_path,
    monitor_pipeline_trigger_path,
    pipeline_runs_path,
)
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import build_url, t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_pipeline_detail_page(
    page: dict,
    *,
    language: str = DEFAULT_LANGUAGE,
    actions: dict | None = None,
    operation_notice: dict | None = None,
) -> str:
    pipeline = page["pipeline"]
    latest_run = page.get("latest_run")
    actions = actions or {}

    hero_links = [
        (t(language, "webui.pipeline_detail.hero.back_to_list"), MONITOR_PIPELINES_PATH),
        (t(language, "webui.pipeline_detail.hero.runs_api"), pipeline_runs_path(pipeline["name"])),
        (t(language, "webui.pipeline_detail.hero.pipeline_api"), build_url(PIPELINES_PATH)),
    ]
    if latest_run and latest_run.get("id"):
        hero_links.append(
            (
                t(language, "webui.pipeline_detail.hero.latest_run"),
                f"{MONITOR_PIPELINES_PATH}/{pipeline['name']}/runs/{latest_run['id']}",
            )
        )

    hero_actions = []
    if actions.get("can_trigger"):
        hero_actions.append(
            {
                "href": monitor_pipeline_trigger_path(pipeline["name"]),
                "label": t(language, "webui.actions.trigger_now"),
                "class_name": "btn-primary",
                "fields": {},
            }
        )
        if latest_run and latest_run.get("execution_date"):
            hero_actions.append(
                {
                    "href": monitor_pipeline_trigger_path(pipeline["name"]),
                    "label": t(language, "webui.actions.rerun_latest"),
                    "class_name": "btn-ghost",
                    "fields": {
                        "execution_date": latest_run["execution_date"],
                        "force": "true",
                    },
                }
            )

    chrome = PageChrome(
        title=t(language, "webui.pipeline_detail.title", pipeline_name=pipeline["name"]),
        subtitle=t(
            language,
            "webui.pipeline_detail.subtitle",
            table=pipeline["table"],
            schedule=pipeline["schedule"],
        ),
        active_path=MONITOR_PIPELINES_PATH,
        page_tag=t(language, "webui.layout.page_tag.pipelines"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.layout.nav.pipelines"), MONITOR_PIPELINES_PATH),
            (pipeline["name"], None),
        ],
        hero_links=hero_links,
        hero_actions=hero_actions,
    )
    return render_page(
        "pipeline_detail.html",
        chrome=chrome,
        language=language,
        pipeline=pipeline,
        summary=page["summary"],
        latest_run=latest_run,
        recent_failures=page["recent_failures"],
        runs=page["runs"],
        grid=page["grid"],
        task_rows=page["task_rows"],
        graph_nodes=page["graph_nodes"],
        actions=actions,
        operation_notice=operation_notice,
        backfill_form_action=monitor_pipeline_backfill_path(pipeline["name"]),
    )
