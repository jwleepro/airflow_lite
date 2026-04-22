from datetime import date

import pandas as pd
import pytest

from airflow_lite.pipeline_config_validation import (
    build_query_render_context,
    validate_data_interval_schedule,
)


def test_build_query_render_context_daily_cron_interval():
    context = build_query_render_context(
        execution_date=date(2026, 3, 15),
        schedule="0 2 * * *",
    )

    assert context["logical_date"] == pd.Timestamp("2026-03-14 02:00:00").to_pydatetime()
    assert context["data_interval_start"] == pd.Timestamp("2026-03-14 02:00:00").to_pydatetime()
    assert context["data_interval_end"] == pd.Timestamp("2026-03-15 02:00:00").to_pydatetime()


def test_build_query_render_context_monthly_cron_interval():
    context = build_query_render_context(
        execution_date=date(2027, 1, 1),
        schedule="0 2 1 * *",
    )

    assert context["data_interval_start"] == pd.Timestamp("2026-12-01 02:00:00").to_pydatetime()
    assert context["data_interval_end"] == pd.Timestamp("2027-01-01 02:00:00").to_pydatetime()


def test_validate_data_interval_schedule_accepts_interval_expression():
    assert validate_data_interval_schedule("interval:15m") == "interval:15m"


def test_validate_data_interval_schedule_rejects_unknown_expression():
    with pytest.raises(ValueError, match="data_interval 계산을 위해 schedule"):
        validate_data_interval_schedule("every day 2am")

