"""PipelineRunner 종단간 통합 테스트 (PE-01 ~ PE-07).

실제 Oracle + 실제 Parquet + 실제 SQLite 조합으로 PipelineRunner.run()을 검증한다.
"""
from datetime import date

import pytest

from airflow_lite.config.settings import PipelineConfig
from .conftest import JANUARY_ROWS, TEST_FULL_TABLE


@pytest.mark.integration
class TestPipelineRunnerE2E:

    def test_run_success_full(self, make_e2e_runner, full_pipeline_config):
        """PE-01: Full Migration 파이프라인이 성공적으로 완료된다."""
        runner = make_e2e_runner(full_pipeline_config)
        result = runner.run(date(2026, 1, 1))
        assert result.status == "success"

    def test_creates_sqlite_records(self, make_e2e_runner, full_pipeline_config, pipeline_repos):
        """PE-02: 실행 후 PipelineRun과 2개 StepRun이 SQLite에 생성된다."""
        run_repo, step_repo = pipeline_repos
        runner = make_e2e_runner(full_pipeline_config)
        result = runner.run(date(2026, 1, 1))

        run = run_repo.find_by_id(result.id)
        assert run is not None

        steps = step_repo.find_by_pipeline_run(result.id)
        assert len(steps) == 2

    def test_steps_all_success(self, make_e2e_runner, full_pipeline_config, pipeline_repos):
        """PE-03: extract_transform_load와 verify 단계 모두 success 상태다."""
        _, step_repo = pipeline_repos
        runner = make_e2e_runner(full_pipeline_config)
        result = runner.run(date(2026, 1, 1))

        steps = {s.step_name: s for s in step_repo.find_by_pipeline_run(result.id)}
        assert steps["extract_transform_load"].status == "success"
        assert steps["verify"].status == "success"

    def test_records_processed_count(self, make_e2e_runner, full_pipeline_config, pipeline_repos):
        """PE-04: StepRun.records_processed가 Oracle 행 수(50)와 일치한다."""
        _, step_repo = pipeline_repos
        runner = make_e2e_runner(full_pipeline_config)
        result = runner.run(date(2026, 1, 1))

        steps = {s.step_name: s for s in step_repo.find_by_pipeline_run(result.id)}
        assert steps["extract_transform_load"].records_processed == JANUARY_ROWS

    def test_parquet_exists_after_run(self, make_e2e_runner, full_pipeline_config, tmp_path):
        """PE-05: 실행 완료 후 Parquet 파일이 올바른 경로에 존재하고 50행을 담고 있다."""
        runner = make_e2e_runner(full_pipeline_config)
        runner.run(date(2026, 1, 1))

        expected = (
            tmp_path / TEST_FULL_TABLE / "year=2026" / "month=01"
            / f"{TEST_FULL_TABLE}_2026_01.parquet"
        )
        assert expected.exists()

        import pyarrow.parquet as pq
        assert pq.read_metadata(str(expected)).num_rows == JANUARY_ROWS

    def test_failure_marks_correctly(self, make_e2e_runner, pipeline_repos):
        """PE-06: 존재하지 않는 테이블 → ETL failed, verify skipped."""
        _, step_repo = pipeline_repos
        bad_config = PipelineConfig(
            name="test_bad_pipeline",
            table="AIRFLOW_TEST_NONEXISTENT",
            source_where_template="LOG_DATE >= :data_interval_start AND LOG_DATE < :data_interval_end",
            strategy="full",
            schedule="0 2 * * *",
        )
        runner = make_e2e_runner(bad_config)
        result = runner.run(date(2026, 1, 1))

        assert result.status == "failed"

        steps = {s.step_name: s for s in step_repo.find_by_pipeline_run(result.id)}
        assert steps["extract_transform_load"].status == "failed"
        assert steps["verify"].status == "skipped"

    def test_error_message_persisted(self, make_e2e_runner, pipeline_repos):
        """PE-07: 실패한 단계의 Oracle 에러 메시지가 SQLite에 저장된다."""
        _, step_repo = pipeline_repos
        bad_config = PipelineConfig(
            name="test_err_pipeline",
            table="AIRFLOW_TEST_NONEXISTENT",
            source_where_template="LOG_DATE >= :data_interval_start AND LOG_DATE < :data_interval_end",
            strategy="full",
            schedule="0 2 * * *",
        )
        runner = make_e2e_runner(bad_config)
        result = runner.run(date(2026, 1, 1))

        steps = {s.step_name: s for s in step_repo.find_by_pipeline_run(result.id)}
        assert steps["extract_transform_load"].error_message is not None
        assert len(steps["extract_transform_load"].error_message) > 0
