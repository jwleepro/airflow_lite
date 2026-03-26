"""Full Migration 파이프라인 통합 테스트 (FM-01 ~ FM-09).

Oracle → ChunkedReader → PyArrow → ParquetWriter의 전체 흐름을 검증한다.
"""
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from airflow_lite.engine.stage import StageContext
from .conftest import (
    FEBRUARY_ROWS,
    JANUARY_ROWS,
    MARCH_ROWS,
    TEST_FULL_TABLE,
)


def _make_ctx(pipeline_config, execution_date, run_id="run-001", chunk_size=10):
    return StageContext(
        pipeline_name=pipeline_config.name,
        execution_date=execution_date,
        table_config=pipeline_config,
        run_id=run_id,
        chunk_size=chunk_size,
    )


def _run_etl(strategy, ctx):
    """extract → transform → load 실행. 총 적재 행 수 반환."""
    total = 0
    for chunk in strategy.extract(ctx):
        arrow_table = strategy.transform(chunk, ctx)
        total += strategy.load(arrow_table, ctx)
    return total


@pytest.mark.integration
class TestFullMigration:

    def test_extract_january(self, full_strategy, full_pipeline_config):
        """FM-01: 1월 파티션에서 50행을 추출한다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        total = sum(len(c) for c in full_strategy.extract(ctx))
        assert total == JANUARY_ROWS

    def test_transform_produces_arrow(self, full_strategy, full_pipeline_config):
        """FM-02: 각 청크가 PyArrow Table로 변환된다."""
        import pyarrow as pa
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        for chunk in full_strategy.extract(ctx):
            result = full_strategy.transform(chunk, ctx)
            assert isinstance(result, pa.Table)
            assert result.num_rows > 0

    def test_load_creates_parquet(self, full_strategy, full_pipeline_config, tmp_path):
        """FM-03: ETL 후 Parquet 파일이 올바른 경로에 생성된다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        _run_etl(full_strategy, ctx)

        expected = (
            tmp_path / TEST_FULL_TABLE / "year=2026" / "month=01"
            / f"{TEST_FULL_TABLE}_2026_01.parquet"
        )
        assert expected.exists()

    def test_etl_row_count_matches(self, full_strategy, full_pipeline_config):
        """FM-04: ETL 후 count_rows()가 Oracle 행 수와 일치한다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        _run_etl(full_strategy, ctx)
        assert full_strategy.parquet_writer.count_rows(TEST_FULL_TABLE, 2026, 1) == JANUARY_ROWS

    def test_verify_returns_true(self, full_strategy, full_pipeline_config):
        """FM-05: ETL 완료 후 verify()가 True를 반환한다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        _run_etl(full_strategy, ctx)
        assert full_strategy.verify(ctx) is True

    def test_february_partition(self, full_strategy, full_pipeline_config):
        """FM-06: 2월 파티션 ETL이 별도 Parquet 파일에 30행을 기록한다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 2, 1))
        _run_etl(full_strategy, ctx)
        assert full_strategy.parquet_writer.count_rows(TEST_FULL_TABLE, 2026, 2) == FEBRUARY_ROWS

    def test_parquet_snappy_compression(self, full_strategy, full_pipeline_config):
        """FM-07: Parquet 파일이 SNAPPY 압축으로 저장된다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        _run_etl(full_strategy, ctx)

        _, output_file = full_strategy.parquet_writer._get_paths(TEST_FULL_TABLE, 2026, 1)
        metadata = pq.read_metadata(str(output_file))
        for rg in range(metadata.num_row_groups):
            for col in range(metadata.num_columns):
                assert metadata.row_group(rg).column(col).compression == "SNAPPY"

    def test_parquet_data_matches_oracle(
        self, full_strategy, full_pipeline_config, oracle_raw_connection
    ):
        """FM-08: Parquet에 저장된 LOG_ID 집합이 Oracle과 일치한다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))
        _run_etl(full_strategy, ctx)

        # Parquet에서 LOG_ID 읽기
        _, output_file = full_strategy.parquet_writer._get_paths(TEST_FULL_TABLE, 2026, 1)
        parquet_ids = sorted(
            pq.read_table(str(output_file)).column("LOG_ID").to_pylist()
        )

        # Oracle에서 LOG_ID 조회
        cursor = oracle_raw_connection.cursor()
        cursor.execute(
            f"SELECT LOG_ID FROM {TEST_FULL_TABLE} "
            f"WHERE LOG_DATE >= DATE '2026-01-01' AND LOG_DATE < DATE '2026-02-01'"
        )
        oracle_ids = sorted(row[0] for row in cursor.fetchall())
        cursor.close()

        assert parquet_ids == oracle_ids

    def test_backup_on_rerun(self, full_strategy, full_pipeline_config):
        """FM-09: 동일 파티션 재실행 시 기존 파일이 .bak으로 백업된다."""
        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1))

        # 첫 번째 실행
        _run_etl(full_strategy, ctx)
        _, output_file = full_strategy.parquet_writer._get_paths(TEST_FULL_TABLE, 2026, 1)
        assert output_file.exists()

        # 두 번째 실행: FullMigrationStrategy 새 인스턴스 필요 (_is_first_chunk 리셋)
        from airflow_lite.engine.strategy import FullMigrationStrategy
        from airflow_lite.extract.chunked_reader import ChunkedReader
        strategy2 = FullMigrationStrategy(
            full_strategy.oracle_client,
            ChunkedReader(connection=None, chunk_size=10),
            full_strategy.parquet_writer,
        )
        _run_etl(strategy2, ctx)

        bak_file = output_file.with_suffix(".bak")
        assert bak_file.exists()
