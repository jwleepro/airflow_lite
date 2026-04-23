"""Incremental Migration 파이프라인 통합 테스트 (IM-01 ~ IM-05).

날짜별 증분 추출 및 Parquet append 동작을 검증한다.
"""
from datetime import date

import pytest

from airflow_lite.engine.stage import StageContext
from .conftest import INCR_ROWS_BY_DAY, TEST_INCR_TABLE


def _make_incr_ctx(pipeline_config, day, run_id="run-001", chunk_size=10):
    return StageContext(
        pipeline_name=pipeline_config.name,
        execution_date=date(2026, 3, day),
        table_config=pipeline_config,
        run_id=run_id,
        chunk_size=chunk_size,
    )


def _run_incr_etl(strategy, ctx):
    for chunk in strategy.extract(ctx):
        arrow_table = strategy.transform(chunk, ctx)
        strategy.load(arrow_table, ctx)


@pytest.mark.integration
class TestIncrementalMigration:

    def test_extract_single_day(self, incr_strategy, incr_pipeline_config):
        """IM-01: 3/15 데이터 추출 시 10행을 반환한다."""
        ctx = _make_incr_ctx(incr_pipeline_config, 15)
        total = sum(len(c) for c in incr_strategy.extract(ctx))
        assert total == INCR_ROWS_BY_DAY[15]

    def test_load_appends(self, incr_strategy, incr_pipeline_config):
        """IM-02: 3/15 적재 후 3/16 추가 적재 시 Parquet에 15행이 누적된다."""
        for day in [15, 16]:
            ctx = _make_incr_ctx(incr_pipeline_config, day, run_id=f"run-{day}")
            _run_incr_etl(incr_strategy, ctx)

        expected = INCR_ROWS_BY_DAY[15] + INCR_ROWS_BY_DAY[16]
        assert incr_strategy.parquet_writer.count_rows(TEST_INCR_TABLE, 2026, 3) == expected

    def test_verify_succeeds(self, incr_strategy, incr_pipeline_config):
        """IM-03: 3/15 ETL 완료 후 verify()가 True를 반환한다."""
        ctx = _make_incr_ctx(incr_pipeline_config, 15)
        _run_incr_etl(incr_strategy, ctx)
        assert incr_strategy.verify(ctx) is True

    def test_query_date_range(self, incr_strategy, incr_pipeline_config):
        """IM-04: 생성된 쿼리가 올바른 날짜 범위 WHERE절을 포함한다."""
        ctx = _make_incr_ctx(incr_pipeline_config, 15)
        query = incr_strategy._build_incremental_query(ctx)
        assert "UPDATED_AT" in query
        assert "2026-03-15" in query
        assert "2026-03-16" in query

    def test_multiple_days_accumulate(self, incr_strategy, incr_pipeline_config):
        """IM-05: 3일치(3/15, 3/16, 3/17) 누적 적재 시 23행이 된다."""
        for day in [15, 16, 17]:
            ctx = _make_incr_ctx(incr_pipeline_config, day, run_id=f"run-{day}")
            _run_incr_etl(incr_strategy, ctx)

        total_expected = sum(INCR_ROWS_BY_DAY.values())
        assert incr_strategy.parquet_writer.count_rows(TEST_INCR_TABLE, 2026, 3) == total_expected
