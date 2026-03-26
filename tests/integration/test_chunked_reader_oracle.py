"""실제 Oracle cursor.fetchmany 스트리밍 검증 테스트 (CR-01 ~ CR-08).

ChunkedReader가 실제 Oracle 커서에서 DataFrame 청크를 올바르게 읽는지 검증한다.
"""
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from airflow_lite.extract.chunked_reader import ChunkedReader
from .conftest import JANUARY_ROWS, TEST_FULL_TABLE


@pytest.mark.integration
class TestChunkedReaderOracle:

    def _make_reader(self, oracle_client, chunk_size=10):
        conn = oracle_client.get_connection()
        return ChunkedReader(conn, chunk_size=chunk_size)

    def _jan_query(self):
        return (
            f"SELECT * FROM {TEST_FULL_TABLE} "
            f"WHERE LOG_DATE >= DATE '2026-01-01' AND LOG_DATE < DATE '2026-02-01'"
        )

    def test_read_chunks_returns_dataframes(self, oracle_client):
        """CR-01: read_chunks()가 pd.DataFrame 청크를 반환한다."""
        reader = self._make_reader(oracle_client)
        chunks = list(reader.read_chunks(self._jan_query()))
        assert len(chunks) > 0
        assert all(isinstance(c, pd.DataFrame) for c in chunks)

    def test_chunk_sizes_respected(self, oracle_client):
        """CR-02: chunk_size=10, 1월 50행 → 5개 청크."""
        reader = self._make_reader(oracle_client, chunk_size=10)
        chunks = list(reader.read_chunks(self._jan_query()))
        assert len(chunks) == JANUARY_ROWS // 10

    def test_column_names_match_schema(self, oracle_client):
        """CR-03: DataFrame 컬럼명이 Oracle 컬럼명(대문자)과 일치한다."""
        reader = self._make_reader(oracle_client)
        chunks = list(reader.read_chunks(self._jan_query()))
        assert len(chunks) > 0
        expected_cols = {"LOG_ID", "PRODUCT_CODE", "LOG_DATE", "QUANTITY", "STATUS"}
        assert set(chunks[0].columns) == expected_cols

    def test_data_types_preserved(self, oracle_client):
        """CR-04: NUMBER→int/float, VARCHAR2→str, DATE→datetime."""
        reader = self._make_reader(oracle_client, chunk_size=5)
        chunks = list(reader.read_chunks(self._jan_query()))
        first = chunks[0]
        # DATE 컬럼 → datetime
        assert isinstance(first["LOG_DATE"].iloc[0], datetime)
        # VARCHAR2 컬럼 → str
        assert isinstance(first["PRODUCT_CODE"].iloc[0], str)
        # NUMBER 컬럼 → int, float, 또는 numpy 정수/실수 타입
        assert isinstance(first["LOG_ID"].iloc[0], (int, float, np.integer, np.floating))

    def test_empty_result_yields_nothing(self, oracle_client):
        """CR-05: WHERE 1=0 쿼리는 청크를 반환하지 않는다."""
        conn = oracle_client.get_connection()
        reader = ChunkedReader(conn, chunk_size=10)
        chunks = list(reader.read_chunks(f"SELECT * FROM {TEST_FULL_TABLE} WHERE 1=0"))
        assert chunks == []

    def test_cursor_closed_after_iteration(self, oracle_client):
        """CR-06: 이터레이션 완료 후 커서가 정리된다 (예외 없이 다음 쿼리 가능)."""
        reader = self._make_reader(oracle_client)
        list(reader.read_chunks(self._jan_query()))
        # 커서가 정리되어 있으면 동일 연결에서 다음 쿼리가 성공해야 함
        conn = oracle_client.get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {TEST_FULL_TABLE}")
        cur.fetchone()
        cur.close()

    def test_large_chunk_single_fetch(self, oracle_client):
        """CR-07: chunk_size=1000, 50행 → 1개 청크."""
        reader = self._make_reader(oracle_client, chunk_size=1000)
        chunks = list(reader.read_chunks(self._jan_query()))
        assert len(chunks) == 1
        assert len(chunks[0]) == JANUARY_ROWS

    def test_total_row_count_matches(self, oracle_client):
        """CR-08: 청크 합산 행 수가 SELECT COUNT(*)와 일치한다."""
        conn = oracle_client.get_connection()
        # Oracle COUNT 조회
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT COUNT(*) FROM {TEST_FULL_TABLE} "
            f"WHERE LOG_DATE >= DATE '2026-01-01' AND LOG_DATE < DATE '2026-02-01'"
        )
        oracle_count = cursor.fetchone()[0]
        cursor.close()

        # ChunkedReader 총합
        reader = ChunkedReader(conn, chunk_size=10)
        total = sum(len(c) for c in reader.read_chunks(self._jan_query()))

        assert total == oracle_count == JANUARY_ROWS
