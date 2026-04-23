from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from airflow_lite.api.dependencies import get_language
from airflow_lite.api.paths import MONITOR_ASSETS_PATH
from airflow_lite.api.webui_assets import render_assets_page

router = APIRouter(include_in_schema=False)


@router.get(MONITOR_ASSETS_PATH, response_class=HTMLResponse)
def get_assets_page(language: str = Depends(get_language)):
    return HTMLResponse(render_assets_page(language=language))
