"""BackfillManager 종단간 통합 테스트 (BF-01 ~ BF-05).

다월 백필 실행 결과, SQLite 상태 기록, Parquet 파일 독립성, 멱등성을 검증한다.
"""
from datetime import date

import pytest

from airflow_lite.engine.backfill import BackfillManager
from .conftest import (
    FEBRUARY_ROWS,
    JANUARY_ROWS,
    MARCH_ROWS,
    TEST_FULL_TABLE,
)


@pytest.mark.integration
class TestBackfillE2E:

    def _make_manager(self, make_e2e_runner, full_pipeline_config, tmp_path):
        runner = make_e2e_runner(full_pipeline_config)
        return BackfillManager(runner, str(tmp_path))

    def test_backfill_three_months(
        self, make_e2e_runner, full_pipeline_config, tmp_path
    ):
        """BF-01: 1~3월 백필 시 3개 PipelineRun과 올바른 행 수 Parquet이 생성된다."""
        manager = self._make_manager(make_e2e_runner, full_pipeline_config, tmp_path)
        results = manager.run_backfill(
            full_pipeline_config.name, date(2026, 1, 1), date(2026, 3, 31)
        )
        assert len(results) == 3

        from airflow_lite.transform.parquet_writer import ParquetWriter
        writer = ParquetWriter(str(tmp_path))
        assert writer.count_rows(TEST_FULL_TABLE, 2026, 1) == JANUARY_ROWS
        assert writer.count_rows(TEST_FULL_TABLE, 2026, 2) == FEBRUARY_ROWS
        assert writer.count_rows(TEST_FULL_TABLE, 2026, 3) == MARCH_ROWS

    def test_results_all_success(
        self, make_e2e_runner, full_pipeline_config, tmp_path
    ):
        """BF-02: 백필 결과 3건 모두 status가 success다."""
        manager = self._make_manager(make_e2e_runner, full_pipeline_config, tmp_path)
        results = manager.run_backfill(
            full_pipeline_config.name, date(2026, 1, 1), date(2026, 3, 31)
        )
        assert all(r.status == "success" for r in results)

    def test_trigger_type_backfill(
        self, make_e2e_runner, full_pipeline_config, tmp_path
    ):
        """BF-03: 백필 실행 PipelineRun의 trigger_type이 'backfill'이다."""
        manager = self._make_manager(make_e2e_runner, full_pipeline_config, tmp_path)
        results = manager.run_backfill(
            full_pipeline_config.name, date(2026, 1, 1), date(2026, 1, 31)
        )
        assert results[0].trigger_type == "backfill"

    def test_parquet_files_independent(
        self, make_e2e_runner, full_pipeline_config, tmp_path
    ):
        """BF-04: 월별 Parquet 파일이 독립적인 경로에 생성된다."""
        manager = self._make_manager(make_e2e_runner, full_pipeline_config, tmp_path)
        manager.run_backfill(
            full_pipeline_config.name, date(2026, 1, 1), date(2026, 3, 31)
        )
        for year, month in [(2026, 1), (2026, 2), (2026, 3)]:
            expected = (
                tmp_path / TEST_FULL_TABLE / f"year={year:04d}" / f"month={month:02d}"
                / f"{TEST_FULL_TABLE}_{year:04d}_{month:02d}.parquet"
            )
            assert expected.exists(), f"{expected} 파일이 존재해야 함"

    def test_backfill_idempotent(
        self, make_e2e_runner, full_pipeline_config, pipeline_repos, tmp_path
    ):
        """BF-05: 동일 날짜 범위 재백필 시 기존 성공 결과를 반환한다 (새 실행 없음)."""
        run_repo, _ = pipeline_repos
        manager = self._make_manager(make_e2e_runner, full_pipeline_config, tmp_path)

        first_results = manager.run_backfill(
            full_pipeline_config.name, date(2026, 1, 1), date(2026, 1, 31)
        )
        first_id = first_results[0].id

        second_results = manager.run_backfill(
            full_pipeline_config.name, date(2026, 1, 1), date(2026, 1, 31)
        )
        second_id = second_results[0].id

        # 같은 execution_date의 성공 실행이면 동일 ID 반환
        assert first_id == second_id
