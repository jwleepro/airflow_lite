"""청크 스트리밍 메모리 검증 테스트 (MS-01 ~ MS-03).

작은 chunk_size로도 전체 데이터가 정확히 처리되고 피크 메모리가 합리적인지 검증한다.
"""
import tracemalloc
from datetime import date

import pytest

from airflow_lite.engine.stage import StageContext
from airflow_lite.engine.strategy import FullMigrationStrategy
from airflow_lite.extract.chunked_reader import ChunkedReader
from airflow_lite.transform.parquet_writer import ParquetWriter
from .conftest import JANUARY_ROWS, TEST_FULL_TABLE


def _make_ctx(pipeline_config, execution_date, chunk_size, run_id="ms-run"):
    return StageContext(
        pipeline_name=pipeline_config.name,
        execution_date=execution_date,
        table_config=pipeline_config,
        run_id=run_id,
        chunk_size=chunk_size,
    )


@pytest.mark.integration
class TestMemoryStreaming:

    def test_small_chunk_completes(self, oracle_client, full_pipeline_config, tmp_path):
        """MS-01: chunk_size=5로 50행을 처리해도 정상 완료된다."""
        writer = ParquetWriter(str(tmp_path))
        reader = ChunkedReader(connection=None, chunk_size=5)
        strategy = FullMigrationStrategy(oracle_client, reader, writer)

        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1), chunk_size=5)
        for chunk in strategy.extract(ctx):
            arrow_table = strategy.transform(chunk, ctx)
            strategy.load(arrow_table, ctx)

        assert writer.count_rows(TEST_FULL_TABLE, 2026, 1) == JANUARY_ROWS

    def test_total_matches_with_small_chunks(
        self, oracle_client, full_pipeline_config, tmp_path
    ):
        """MS-02: chunk_size=3 청크 합산 행 수가 총 Oracle 행 수와 일치한다."""
        writer = ParquetWriter(str(tmp_path))
        reader = ChunkedReader(connection=None, chunk_size=3)
        strategy = FullMigrationStrategy(oracle_client, reader, writer)

        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1), chunk_size=3)
        total = 0
        for chunk in strategy.extract(ctx):
            total += len(chunk)

        assert total == JANUARY_ROWS

    def test_peak_memory_bounded(self, oracle_client, full_pipeline_config, tmp_path):
        """MS-03: chunk_size=10 스트리밍 처리 중 피크 메모리가 20MB 이하다."""
        writer = ParquetWriter(str(tmp_path))
        reader = ChunkedReader(connection=None, chunk_size=10)
        strategy = FullMigrationStrategy(oracle_client, reader, writer)

        ctx = _make_ctx(full_pipeline_config, date(2026, 1, 1), chunk_size=10)

        tracemalloc.start()
        for chunk in strategy.extract(ctx):
            arrow_table = strategy.transform(chunk, ctx)
            strategy.load(arrow_table, ctx)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 테스트 데이터(50행)는 매우 작으므로 20MB 이내여야 함
        assert peak < 20 * 1024 * 1024, f"피크 메모리 {peak / 1024 / 1024:.1f}MB 초과"
