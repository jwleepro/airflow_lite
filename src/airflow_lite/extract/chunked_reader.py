import logging
from typing import Iterator

import pandas as pd

logger = logging.getLogger("airflow_lite.extract.chunked_reader")


class ChunkedReader:
    """fetchmany(chunk_size)로 청크 단위 읽기.
    각 청크는 즉시 Parquet row group으로 변환되어 메모리에서 해제.

    chunk_size 산출 기준:
        chunk_size = floor((500MB * 0.6) / avg_row_bytes)
        나머지 40%는 Parquet 변환 및 런타임 오버헤드.
        YAML 설정에서 테이블별 chunk_size 명시, 미지정 시 기본값 10,000.
    """

    def __init__(self, connection, chunk_size: int = 10000):
        self.connection = connection
        self.chunk_size = chunk_size

    def read_chunks(
        self, query: str, params: dict | None = None
    ) -> Iterator[pd.DataFrame]:
        """Oracle 커서에서 fetchmany로 청크 단위 읽기.

        데이터 흐름:
        Oracle 커서 → fetchmany() → pd.DataFrame → (caller로 yield)
        → pa.Table → Parquet row group → 파일 시스템

        각 청크가 처리된 후 이전 청크의 DataFrame/Table 참조는 해제된다.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or {})
            columns = [desc[0] for desc in cursor.description]

            while True:
                rows = cursor.fetchmany(self.chunk_size)
                if not rows:
                    break
                yield pd.DataFrame(rows, columns=columns)
        finally:
            cursor.close()
