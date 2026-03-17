# Task-004: 마이그레이션 전략 + 데이터 추출/변환

## 목적

Oracle 11g에서 데이터를 청크 단위로 추출하고, Parquet 파일로 변환/저장하는 데이터 처리 파이프라인을 구현한다. Strategy 패턴으로 전체 이관(Full)과 증분 이관(Incremental) 전략을 분리한다.

## 입력

- Task-003의 엔진 코어 (StageContext, StageResult, MigrationStrategy ABC)
- Oracle 11g 연결 정보 (Settings.oracle)
- YAML 설정의 파이프라인 정의 (테이블명, 파티션 컬럼, 전략, 청크 사이즈 등)

## 출력

- `src/airflow_lite/engine/strategy.py` — MigrationStrategy ABC + Full/Incremental 구현
- `src/airflow_lite/extract/oracle_client.py` — Oracle 연결 관리 (재시도 포함)
- `src/airflow_lite/extract/chunked_reader.py` — 청크 기반 커서 스트리밍
- `src/airflow_lite/transform/parquet_writer.py` — Parquet 직렬화

## 구현 제약

- 500MB 메모리 예산 (P5) — 모든 데이터 처리는 청크 기반 스트리밍
- 멱등성 보장 (P2) — 동일 execution_date 재실행 시 동일 결과
- oracledb 사용 (Oracle 11g 연결은 thick mode 필요 — `oracle_home` 설정 필수)
- Parquet: Snappy 압축, pyarrow 사용

## 구현 상세

### strategy.py — MigrationStrategy ABC + 구현체

```python
from abc import ABC, abstractmethod
from typing import Iterator
import pandas as pd
import pyarrow as pa

class MigrationStrategy(ABC):
    """마이그레이션 전략 추상 클래스"""

    @abstractmethod
    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        """Oracle에서 청크 단위로 데이터 추출"""

    @abstractmethod
    def transform(self, chunk: pd.DataFrame, context: StageContext) -> pa.Table:
        """DataFrame을 PyArrow Table로 변환"""

    @abstractmethod
    def load(self, table: pa.Table, context: StageContext) -> int:
        """Parquet 파일로 저장, 처리 건수 반환"""

    @abstractmethod
    def verify(self, context: StageContext) -> bool:
        """소스-타겟 건수 일치 검증"""


class FullMigrationStrategy(MigrationStrategy):
    """전체 이관: 월별 파티션 전체를 덮어쓰기.

    extract: partition_column 기반 WHERE절로 해당 월 전체 데이터 추출
    load: 기존 Parquet 파일을 .bak으로 이동 후 새 파일 생성
    verify: Oracle 건수 vs Parquet 행 수 비교
    """

    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        self.oracle_client = oracle_client
        self.chunked_reader = chunked_reader
        self.parquet_writer = parquet_writer

    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        query = self._build_full_query(context)
        return self.chunked_reader.read_chunks(query)

    def _build_full_query(self, context: StageContext) -> str:
        """월별 파티션 쿼리 생성.
        예: SELECT * FROM PRODUCTION_LOG
            WHERE LOG_DATE >= DATE '2026-03-01'
              AND LOG_DATE < DATE '2026-04-01'
        """


class IncrementalMigrationStrategy(MigrationStrategy):
    """증분 이관: 마지막 이관 이후 변경분만 처리.

    extract: incremental_key 기반 WHERE절로 변경분 추출
    load: 기존 Parquet에 append 또는 merge
    verify: 추출 건수 vs 적재 건수 비교
    """

    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        self.oracle_client = oracle_client
        self.chunked_reader = chunked_reader
        self.parquet_writer = parquet_writer
```

### oracle_client.py — Oracle 연결 관리

```python
import oracledb
import logging

logger = logging.getLogger("airflow_lite.extract.oracle_client")

class OracleClient:
    """Oracle 11g 연결 관리.

    - 연결 생성 시 RetryableOracleError/NonRetryableOracleError로 래핑
    - oracledb.DatabaseError의 에러 코드를 검사하여 재시도 가능 여부 판별
    - Oracle 11g 연결을 위해 thick mode 자동 초기화 (oracle_home 설정 사용)
    """

    def __init__(self, config: "OracleConfig"):
        self.config = config
        self._connection = None

    def get_connection(self):
        """Oracle 연결 반환. 연결 끊김 시 재연결 시도."""
        if self._connection is None or not self._is_alive():
            self._connection = self._create_connection()
        return self._connection

    def _create_connection(self):
        dsn = oracledb.makedsn(
            self.config.host,
            self.config.port,
            service_name=self.config.service_name,
        )
        return oracledb.connect(
            user=self.config.user,
            password=self.config.password,
            dsn=dsn,
        )

    def _is_alive(self) -> bool:
        try:
            self._connection.ping()
            return True
        except Exception:
            return False

    def classify_error(self, error: oracledb.DatabaseError) -> Exception:
        """Oracle 에러 코드를 검사하여 재시도 가능 여부에 따라 래핑.

        RETRYABLE_ORACLE_ERRORS = {3113, 3114, 12541, 12170, 12571}
        """
        error_obj = error.args[0]
        code = getattr(error_obj, "code", None)
        if code in RETRYABLE_ORACLE_ERRORS:
            return RetryableOracleError(str(error))
        return NonRetryableOracleError(str(error))
```

### chunked_reader.py — 청크 기반 스트리밍

```python
import pandas as pd
from typing import Iterator

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
```

### parquet_writer.py — Parquet 직렬화

```python
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

class ParquetWriter:
    """Parquet 파일 직렬화 (Snappy 압축).

    파티셔닝 구조:
        /data/parquet/{TABLE_NAME}/YYYY={MM}/
            {TABLE_NAME}_{YYYY}_{MM}.parquet

    row group 단위로 append하여 메모리 사용 최소화.
    """

    def __init__(self, base_path: str, compression: str = "snappy"):
        self.base_path = Path(base_path)
        self.compression = compression

    def write_chunk(
        self,
        table: pa.Table,
        table_name: str,
        year: int,
        month: int,
        append: bool = False,
    ) -> Path:
        """PyArrow Table을 Parquet 파일로 저장.

        - 디렉터리 자동 생성
        - append=True: 기존 파일에 row group 추가
        - append=False: 새 파일 생성 (기존 파일 덮어쓰기)
        """
        output_dir = self.base_path / table_name / f"YYYY={month:02d}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{table_name}_{year}_{month:02d}.parquet"

        if append and output_file.exists():
            # 기존 파일 읽어서 병합 후 저장
            existing = pq.read_table(str(output_file))
            merged = pa.concat_tables([existing, table])
            pq.write_table(
                merged, str(output_file), compression=self.compression
            )
        else:
            pq.write_table(
                table, str(output_file), compression=self.compression
            )

        return output_file
```

## 완료 조건

- [ ] `MigrationStrategy` ABC 정의 (extract, transform, load, verify)
- [ ] `FullMigrationStrategy` 구현 — 월별 전체 추출/적재
- [ ] `IncrementalMigrationStrategy` 구현 — 증분 추출/적재
- [ ] `OracleClient` 연결 관리 + 에러 분류 테스트 (oracledb 모킹)
- [ ] `ChunkedReader.read_chunks()` 청크 단위 읽기 테스트 (커서 모킹)
- [ ] `ParquetWriter.write_chunk()` Parquet 파일 생성 테스트
- [ ] 메모리 제약: 청크 처리 중 이전 청크 참조 해제 확인
- [ ] 파티셔닝 경로 구조 확인: `{base_path}/{TABLE_NAME}/YYYY={MM}/`

## 참고 (선택)

- Strategy 패턴 설계: `docs/architecture.md` 섹션 3.1
- 청크 스트리밍 설계: `docs/architecture.md` 섹션 3.4
- 파티셔닝 구조: `docs/architecture.md` 섹션 3.5
