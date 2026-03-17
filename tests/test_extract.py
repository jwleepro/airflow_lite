"""Task-004: 마이그레이션 전략 + 데이터 추출/변환 테스트.

oracledb는 실제 Oracle 서버 없이는 동작하지 않으므로 연결 부분은 모킹 처리.
"""
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import pyarrow as pa
import pytest

from airflow_lite.engine.stage import (
    RETRYABLE_ORACLE_ERRORS,
    NonRetryableOracleError,
    RetryableOracleError,
    StageContext,
)
from airflow_lite.engine.strategy import (
    FullMigrationStrategy,
    IncrementalMigrationStrategy,
    MigrationStrategy,
)
from airflow_lite.extract.chunked_reader import ChunkedReader
from airflow_lite.extract.oracle_client import OracleClient
from airflow_lite.transform.parquet_writer import ParquetWriter


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_oracle_error(code: int):
    """oracledb.DatabaseError를 모사하는 에러 객체 생성."""
    error_obj = MagicMock()
    error_obj.code = code
    err = Exception(error_obj)
    err.args = (error_obj,)
    return err


def _make_context(
    table="TEST_TABLE",
    partition_column="DATE_COL",
    strategy="full",
    execution_date=date(2026, 3, 1),
    chunk_size=100,
    incremental_key=None,
) -> StageContext:
    table_config = MagicMock()
    table_config.table = table
    table_config.partition_column = partition_column
    table_config.strategy = strategy
    table_config.incremental_key = incremental_key
    return StageContext(
        pipeline_name="test_pipeline",
        execution_date=execution_date,
        table_config=table_config,
        run_id="run-001",
        chunk_size=chunk_size,
    )


# ── OracleClient 테스트 ────────────────────────────────────────────────────────

class TestOracleClientClassifyError:
    """OracleClient.classify_error: 에러 코드 기반 재시도 여부 분류."""

    def setup_method(self):
        config = MagicMock()
        self.client = OracleClient(config)

    def test_retryable_error_codes(self):
        for code in RETRYABLE_ORACLE_ERRORS:
            err = _make_oracle_error(code)
            result = self.client.classify_error(err)
            assert isinstance(result, RetryableOracleError), (
                f"ORA-{code:05d}는 RetryableOracleError여야 함"
            )

    def test_non_retryable_error_code(self):
        err = _make_oracle_error(1)  # ORA-00001: unique constraint violated
        result = self.client.classify_error(err)
        assert isinstance(result, NonRetryableOracleError)

    def test_non_retryable_error_code_1400(self):
        err = _make_oracle_error(1400)  # ORA-01400: cannot insert NULL
        result = self.client.classify_error(err)
        assert isinstance(result, NonRetryableOracleError)

    def test_unknown_code_is_non_retryable(self):
        err = _make_oracle_error(9999)
        result = self.client.classify_error(err)
        assert isinstance(result, NonRetryableOracleError)

    def test_error_without_code_is_non_retryable(self):
        error_obj = MagicMock(spec=[])  # code 속성 없음
        err = Exception(error_obj)
        err.args = (error_obj,)
        result = self.client.classify_error(err)
        assert isinstance(result, NonRetryableOracleError)


class TestOracleClientConnection:
    """OracleClient 연결 관리."""

    def setup_method(self):
        self.config = MagicMock()
        self.config.host = "localhost"
        self.config.port = 1521
        self.config.service_name = "ORCL"
        self.config.user = "scott"
        self.config.password = "tiger"
        self.client = OracleClient(self.config)

    def test_get_connection_creates_new_when_none(self):
        mock_conn = MagicMock()
        self.client._create_connection = MagicMock(return_value=mock_conn)
        result = self.client.get_connection()
        assert result is mock_conn
        self.client._create_connection.assert_called_once()

    def test_get_connection_reuses_alive_connection(self):
        mock_conn = MagicMock()
        self.client._connection = mock_conn
        self.client._is_alive = MagicMock(return_value=True)
        result = self.client.get_connection()
        assert result is mock_conn

    def test_get_connection_reconnects_when_dead(self):
        old_conn = MagicMock()
        new_conn = MagicMock()
        self.client._connection = old_conn
        self.client._is_alive = MagicMock(return_value=False)
        self.client._create_connection = MagicMock(return_value=new_conn)
        result = self.client.get_connection()
        assert result is new_conn

    def test_is_alive_returns_true_when_ping_succeeds(self):
        mock_conn = MagicMock()
        mock_conn.ping.return_value = None
        self.client._connection = mock_conn
        assert self.client._is_alive() is True

    def test_is_alive_returns_false_when_ping_fails(self):
        mock_conn = MagicMock()
        mock_conn.ping.side_effect = Exception("connection lost")
        self.client._connection = mock_conn
        assert self.client._is_alive() is False

    def test_close_clears_connection(self):
        mock_conn = MagicMock()
        self.client._connection = mock_conn
        self.client.close()
        mock_conn.close.assert_called_once()
        assert self.client._connection is None

    def test_close_when_already_none(self):
        self.client._connection = None
        self.client.close()  # 예외 없이 통과해야 함


# ── ChunkedReader 테스트 ───────────────────────────────────────────────────────

class TestChunkedReader:
    """ChunkedReader.read_chunks: 청크 단위 커서 스트리밍."""

    def _make_cursor(self, rows: list, columns: list[str]):
        cursor = MagicMock()
        cursor.description = [(col, None, None, None, None, None, None) for col in columns]
        # fetchmany 호출마다 chunk_size씩 반환 후 빈 리스트
        call_count = [0]
        chunk_size_ref = [10]

        def fetchmany(size=None):
            size = size or chunk_size_ref[0]
            start = call_count[0] * size
            call_count[0] += 1
            chunk = rows[start : start + size]
            return chunk

        cursor.fetchmany.side_effect = fetchmany
        return cursor

    def test_yields_dataframes_in_chunks(self):
        rows = [(i, f"val_{i}") for i in range(25)]
        columns = ["ID", "VAL"]
        cursor = self._make_cursor(rows, columns)
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn, chunk_size=10)
        chunks = list(reader.read_chunks("SELECT * FROM T"))

        assert len(chunks) == 3  # 10 + 10 + 5
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5
        assert list(chunks[0].columns) == ["ID", "VAL"]

    def test_yields_nothing_for_empty_result(self):
        cursor = MagicMock()
        cursor.description = [("ID", None, None, None, None, None, None)]
        cursor.fetchmany.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn, chunk_size=10)
        chunks = list(reader.read_chunks("SELECT * FROM T"))
        assert chunks == []

    def test_cursor_closed_on_success(self):
        cursor = MagicMock()
        cursor.description = [("ID", None, None, None, None, None, None)]
        cursor.fetchmany.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn)
        list(reader.read_chunks("SELECT 1 FROM DUAL"))
        cursor.close.assert_called_once()

    def test_cursor_closed_on_exception(self):
        cursor = MagicMock()
        cursor.description = [("ID", None, None, None, None, None, None)]
        cursor.execute.side_effect = RuntimeError("DB error")
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn)
        with pytest.raises(RuntimeError):
            list(reader.read_chunks("SELECT 1 FROM DUAL"))
        cursor.close.assert_called_once()

    def test_previous_chunk_reference_released(self):
        """각 청크는 독립적인 DataFrame이며, 이전 청크 참조 없이 next()로 진행 가능."""
        rows = [(i,) for i in range(20)]
        columns = ["ID"]
        cursor = self._make_cursor(rows, columns)
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn, chunk_size=10)
        gen = reader.read_chunks("SELECT * FROM T")

        chunk1 = next(gen)
        chunk1_data = chunk1["ID"].tolist()
        chunk1 = None  # 이전 청크 참조 해제 후 다음 청크 진행

        chunk2 = next(gen)
        # 두 청크는 서로 다른 데이터여야 함
        assert chunk2["ID"].tolist() != chunk1_data
        assert chunk2["ID"].iloc[0] == 10  # 두 번째 청크는 10부터 시작

    def test_params_passed_to_execute(self):
        cursor = MagicMock()
        cursor.description = [("ID", None, None, None, None, None, None)]
        cursor.fetchmany.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn)
        params = {"date": "2026-03-01"}
        list(reader.read_chunks("SELECT * FROM T WHERE d = :date", params))
        cursor.execute.assert_called_once_with(
            "SELECT * FROM T WHERE d = :date", params
        )

    def test_no_params_passes_empty_dict(self):
        cursor = MagicMock()
        cursor.description = [("ID", None, None, None, None, None, None)]
        cursor.fetchmany.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = cursor

        reader = ChunkedReader(conn)
        list(reader.read_chunks("SELECT * FROM T"))
        cursor.execute.assert_called_once_with("SELECT * FROM T", {})


# ── ParquetWriter 테스트 ───────────────────────────────────────────────────────

class TestParquetWriter:
    """ParquetWriter.write_chunk: Parquet 파일 생성 및 append."""

    def _make_table(self, n_rows: int = 5) -> pa.Table:
        return pa.table(
            {"ID": list(range(n_rows)), "VAL": [f"v{i}" for i in range(n_rows)]}
        )

    def test_write_chunk_creates_file(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        table = self._make_table(10)
        output = writer.write_chunk(table, "MY_TABLE", 2026, 3)
        assert output.exists()
        assert output.name == "MY_TABLE_2026_03.parquet"

    def test_partitioning_directory_structure(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        table = self._make_table(5)
        output = writer.write_chunk(table, "MY_TABLE", 2026, 3)
        # {base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/
        expected_dir = tmp_path / "MY_TABLE" / "year=2026" / "month=03"
        assert output.parent == expected_dir

    def test_write_chunk_append_merges_rows(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        table1 = self._make_table(5)
        table2 = pa.table({"ID": [10, 11], "VAL": ["a", "b"]})

        writer.write_chunk(table1, "T", 2026, 3, append=False)
        writer.write_chunk(table2, "T", 2026, 3, append=True)

        result = writer.count_rows("T", 2026, 3)
        assert result == 7  # 5 + 2

    def test_write_chunk_overwrite_when_not_append(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        table1 = self._make_table(10)
        table2 = self._make_table(3)

        writer.write_chunk(table1, "T", 2026, 3, append=False)
        writer.write_chunk(table2, "T", 2026, 3, append=False)

        assert writer.count_rows("T", 2026, 3) == 3

    def test_directory_auto_created(self, tmp_path):
        writer = ParquetWriter(str(tmp_path / "deep" / "nested"))
        table = self._make_table(2)
        output = writer.write_chunk(table, "T", 2026, 1)
        assert output.exists()

    def test_count_rows_returns_zero_when_no_file(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        assert writer.count_rows("NOFILE", 2026, 3) == 0

    def test_count_rows_returns_correct_count(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        table = self._make_table(42)
        writer.write_chunk(table, "T", 2026, 3)
        assert writer.count_rows("T", 2026, 3) == 42

    def test_backup_existing_renames_file(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        table = self._make_table(5)
        writer.write_chunk(table, "T", 2026, 3)

        result = writer.backup_existing("T", 2026, 3)
        assert result is True

        _, output_file = writer._get_paths("T", 2026, 3)
        bak_file = output_file.with_suffix(".bak")
        assert bak_file.exists()
        assert not output_file.exists()

    def test_backup_existing_returns_false_when_no_file(self, tmp_path):
        writer = ParquetWriter(str(tmp_path))
        result = writer.backup_existing("T", 2026, 3)
        assert result is False

    def test_snappy_compression_default(self, tmp_path):
        import pyarrow.parquet as pq
        writer = ParquetWriter(str(tmp_path))
        table = self._make_table(5)
        output = writer.write_chunk(table, "T", 2026, 3)
        metadata = pq.read_metadata(str(output))
        for rg in range(metadata.num_row_groups):
            for col in range(metadata.num_columns):
                assert metadata.row_group(rg).column(col).compression == "SNAPPY"


# ── MigrationStrategy 테스트 ───────────────────────────────────────────────────

class TestFullMigrationStrategy:
    """FullMigrationStrategy: 월별 전체 추출/적재."""

    def _make_strategy(self, tmp_path):
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = ParquetWriter(str(tmp_path))
        return FullMigrationStrategy(oracle_client, chunked_reader, parquet_writer)

    def test_build_full_query_march(self):
        strategy = self._make_strategy(Path("."))
        ctx = _make_context(execution_date=date(2026, 3, 1))
        query = strategy._build_full_query(ctx)
        assert "DATE '2026-03-01'" in query
        assert "DATE '2026-04-01'" in query

    def test_build_full_query_december_wraps_year(self):
        strategy = self._make_strategy(Path("."))
        ctx = _make_context(execution_date=date(2026, 12, 1))
        query = strategy._build_full_query(ctx)
        assert "DATE '2026-12-01'" in query
        assert "DATE '2027-01-01'" in query

    def test_extract_sets_connection_and_chunk_size(self, tmp_path):
        mock_conn = MagicMock()
        oracle_client = MagicMock()
        oracle_client.get_connection.return_value = mock_conn
        chunked_reader = MagicMock()
        chunked_reader.read_chunks.return_value = iter([])
        parquet_writer = ParquetWriter(str(tmp_path))

        strategy = FullMigrationStrategy(oracle_client, chunked_reader, parquet_writer)
        ctx = _make_context(chunk_size=500)
        list(strategy.extract(ctx))

        assert chunked_reader.connection is mock_conn
        assert chunked_reader.chunk_size == 500

    def test_load_first_chunk_appends_false(self, tmp_path):
        """첫 번째 load 호출은 기존 파일 백업 후 새로 씀."""
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = MagicMock()
        parquet_writer.backup_existing.return_value = False

        strategy = FullMigrationStrategy(oracle_client, chunked_reader, parquet_writer)
        ctx = _make_context()
        table = pa.table({"ID": [1, 2, 3]})
        count = strategy.load(table, ctx)

        assert count == 3
        parquet_writer.backup_existing.assert_called_once()
        parquet_writer.write_chunk.assert_called_once_with(
            table, "TEST_TABLE", 2026, 3, append=False
        )

    def test_load_subsequent_chunks_append_true(self, tmp_path):
        """두 번째 이후 load 호출은 append=True."""
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = MagicMock()
        parquet_writer.backup_existing.return_value = False

        strategy = FullMigrationStrategy(oracle_client, chunked_reader, parquet_writer)
        ctx = _make_context()
        t1 = pa.table({"ID": [1, 2]})
        t2 = pa.table({"ID": [3, 4]})

        strategy.load(t1, ctx)
        strategy.load(t2, ctx)

        calls = parquet_writer.write_chunk.call_args_list
        assert calls[0][1]["append"] is False
        assert calls[1][1]["append"] is True

    def test_transform_returns_pyarrow_table(self, tmp_path):
        strategy = self._make_strategy(tmp_path)
        ctx = _make_context()
        df = pd.DataFrame({"ID": [1, 2], "VAL": ["a", "b"]})
        result = strategy.transform(df, ctx)
        assert isinstance(result, pa.Table)
        assert result.num_rows == 2

    def test_is_abstract_base(self):
        from airflow_lite.engine.strategy import MigrationStrategy
        assert issubclass(FullMigrationStrategy, MigrationStrategy)


class TestIncrementalMigrationStrategy:
    """IncrementalMigrationStrategy: 증분 추출/적재."""

    def test_build_incremental_query(self):
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = MagicMock()
        strategy = IncrementalMigrationStrategy(
            oracle_client, chunked_reader, parquet_writer
        )
        ctx = _make_context(
            incremental_key="UPDATED_AT",
            execution_date=date(2026, 3, 15),
        )
        query = strategy._build_incremental_query(ctx)
        assert "UPDATED_AT" in query
        assert "2026-03-15" in query
        assert "2026-03-16" in query

    def test_load_always_appends(self):
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = MagicMock()
        strategy = IncrementalMigrationStrategy(
            oracle_client, chunked_reader, parquet_writer
        )
        ctx = _make_context()
        t1 = pa.table({"ID": [1, 2]})
        t2 = pa.table({"ID": [3]})

        strategy.load(t1, ctx)
        strategy.load(t2, ctx)

        for call in parquet_writer.write_chunk.call_args_list:
            assert call[1]["append"] is True

    def test_verify_loaded_count_le_parquet_count(self):
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = MagicMock()
        parquet_writer.count_rows.return_value = 10

        strategy = IncrementalMigrationStrategy(
            oracle_client, chunked_reader, parquet_writer
        )
        strategy._loaded_count = 10
        ctx = _make_context()
        assert strategy.verify(ctx) is True

    def test_verify_fails_when_count_mismatch(self):
        oracle_client = MagicMock()
        chunked_reader = MagicMock()
        parquet_writer = MagicMock()
        parquet_writer.count_rows.return_value = 5

        strategy = IncrementalMigrationStrategy(
            oracle_client, chunked_reader, parquet_writer
        )
        strategy._loaded_count = 10
        ctx = _make_context()
        assert strategy.verify(ctx) is False
