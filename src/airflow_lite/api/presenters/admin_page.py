"""Assemble data for the Admin page."""

from __future__ import annotations

from airflow_lite.api.viewmodels import AdminPageViewData


def build_admin_view_data(admin_repo) -> AdminPageViewData:
    return AdminPageViewData.from_repo_payload(
        connections=admin_repo.list_connections(),
        variables=admin_repo.list_variables(),
        pools=admin_repo.list_pools(),
        pipelines=admin_repo.list_pipelines(),
    )
