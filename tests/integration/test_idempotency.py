"""멱등성 통합 테스트 (ID-01 ~ ID-04).

동일 execution_date 재실행 시 Oracle 재쿼리 없이 기존 결과를 반환하는지 검증한다.
"""
from datetime import date
from unittest.mock import patch

import pytest

from airflow_lite.config.settings import PipelineConfig
from .conftest import JANUARY_ROWS, TEST_FULL_TABLE


@pytest.mark.integration
class TestIdempotency:

    def test_rerun_returns_existing(self, make_e2e_runner, full_pipeline_config):
        """ID-01: 동일 execution_date 재실행 시 같은 PipelineRun.id가 반환된다."""
        runner = make_e2e_runner(full_pipeline_config)
        result1 = runner.run(date(2026, 1, 1))
        assert result1.status == "success"

        result2 = runner.run(date(2026, 1, 1))
        assert result1.id == result2.id

    def test_parquet_not_overwritten(
        self, make_e2e_runner, full_pipeline_config, tmp_path
    ):
        """ID-02: 재실행 시 Parquet 파일이 수정되지 않는다."""
        runner = make_e2e_runner(full_pipeline_config)
        runner.run(date(2026, 1, 1))

        output_file = (
            tmp_path / TEST_FULL_TABLE / "year=2026" / "month=01"
            / f"{TEST_FULL_TABLE}_2026_01.parquet"
        )
        assert output_file.exists()
        mtime_before = output_file.stat().st_mtime

        runner.run(date(2026, 1, 1))
        mtime_after = output_file.stat().st_mtime

        assert mtime_before == mtime_after

    def test_oracle_not_requeried(
        self, make_e2e_runner, full_pipeline_config, pipeline_repos
    ):
        """ID-03: 성공한 실행 재실행 시 SQLite 단계 레코드가 새로 생성되지 않는다."""
        _, step_repo = pipeline_repos
        runner = make_e2e_runner(full_pipeline_config)
        result1 = runner.run(date(2026, 1, 1))

        steps_after_first = step_repo.find_by_pipeline_run(result1.id)
        count_before = len(steps_after_first)

        runner.run(date(2026, 1, 1))  # 두 번째 실행 (멱등)

        steps_after_second = step_repo.find_by_pipeline_run(result1.id)
        assert len(steps_after_second) == count_before

    def test_failed_run_allows_retry(
        self, make_e2e_runner, pipeline_repos
    ):
        """ID-04: 실패한 실행 후 동일 execution_date 재실행 시 실제로 재실행된다."""
        run_repo, step_repo = pipeline_repos

        # 첫 번째 실행: 존재하지 않는 테이블로 실패 유도
        bad_config = PipelineConfig(
            name="test_retry_pipeline",
            table="AIRFLOW_TEST_NONEXISTENT",
            partition_column="LOG_DATE",
            strategy="full",
            schedule="0 2 * * *",
        )
        bad_runner = make_e2e_runner(bad_config)
        result1 = bad_runner.run(date(2026, 1, 1))
        assert result1.status == "failed"

        # 두 번째 실행: 올바른 테이블로 재실행 (같은 pipeline_name, 같은 execution_date)
        good_config = PipelineConfig(
            name="test_retry_pipeline",  # 같은 이름
            table=TEST_FULL_TABLE,
            partition_column="LOG_DATE",
            strategy="full",
            schedule="0 2 * * *",
        )
        good_runner = make_e2e_runner(good_config)
        # UNIQUE(pipeline_name, execution_date, trigger_type) 제약으로 인해
        # 실패 재시도는 다른 trigger_type으로 실행해야 함
        result2 = good_runner.run(date(2026, 1, 1), trigger_type="manual")

        # 실패 후 재실행이므로 새 PipelineRun이 생성되어야 함
        assert result2.status == "success"
        assert result1.id != result2.id
