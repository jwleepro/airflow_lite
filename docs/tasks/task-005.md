# Task-005: 백필 매니저

## 목적

과거 데이터를 안전하게 재이관하는 백필(재처리) 매니저를 구현한다. 날짜 범위를 월별로 분할하여 순차 실행하고, 기존 Parquet 파일의 백업/복원으로 안전성을 보장한다.

## 입력

- Task-003의 PipelineRunner
- Task-004의 ParquetWriter (파일 경로 규칙)
- 백필 요청: pipeline_name, start_date, end_date

## 출력

- `src/airflow_lite/engine/backfill.py` — BackfillManager

## 구현 제약

- 멱등성 보장 (P2) — 동일 날짜 범위 재실행 시 동일 결과
- 실패 격리 (P3) — 특정 월 실패 시 이전 월 결과 보존
- 월 단위 파티셔닝 (D5) — 월 경계로 분할하여 실행

## 구현 상세

### backfill.py — BackfillManager

```python
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
import shutil
import logging

logger = logging.getLogger("airflow_lite.engine.backfill")

class BackfillManager:
    def __init__(
        self,
        pipeline_runner: "PipelineRunner",
        parquet_base_path: str,
    ):
        self.pipeline_runner = pipeline_runner
        self.parquet_base_path = Path(parquet_base_path)

    def run_backfill(
        self,
        pipeline_name: str,
        start_date: date,
        end_date: date,
    ) -> list["PipelineRun"]:
        """날짜 범위를 월 단위로 분할하여 순차 실행.

        1. start_date~end_date를 월 경계로 분할
        2. 각 월에 대해 PipelineRunner.run(execution_date=해당월)
        3. 결과를 리스트로 반환
        """
        months = self._split_into_months(start_date, end_date)
        results = []

        for month_date in months:
            logger.info(f"백필 실행: {pipeline_name} / {month_date}")
            run = self.pipeline_runner.run(
                execution_date=month_date,
                trigger_type="backfill",
            )
            results.append(run)

        return results

    def _split_into_months(self, start_date: date, end_date: date) -> list[date]:
        """날짜 범위를 월 경계로 분할.

        예시:
            start_date=2026-01-15, end_date=2026-04-10
            → [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]

        각 월의 1일을 execution_date로 사용한다.
        """
        months = []
        current = start_date.replace(day=1)
        end_month = end_date.replace(day=1)

        while current <= end_month:
            months.append(current)
            current += relativedelta(months=1)

        return months
```

### 안전한 덮어쓰기 프로세스 (.bak 백업/복원)

```python
    def backup_existing(self, table_name: str, year: int, month: int) -> Path | None:
        """기존 Parquet 파일을 .bak 확장자로 이동.

        예: {TABLE_NAME}_{YYYY}_{MM}.parquet → {TABLE_NAME}_{YYYY}_{MM}.parquet.bak
        파일이 없으면 None 반환.
        """
        parquet_dir = self.parquet_base_path / table_name / f"YYYY={month:02d}"
        parquet_file = parquet_dir / f"{table_name}_{year}_{month:02d}.parquet"

        if not parquet_file.exists():
            return None

        bak_file = parquet_file.with_suffix(".parquet.bak")
        shutil.move(str(parquet_file), str(bak_file))
        logger.info(f"백업 생성: {parquet_file} → {bak_file}")
        return bak_file

    def remove_backup(self, bak_path: Path) -> None:
        """검증(verify) 성공 시 .bak 파일 삭제."""
        if bak_path and bak_path.exists():
            bak_path.unlink()
            logger.info(f"백업 삭제: {bak_path}")

    def restore_backup(self, bak_path: Path) -> None:
        """실패 시 .bak 파일을 원본 위치로 복원."""
        if bak_path and bak_path.exists():
            original = bak_path.with_suffix("")  # .bak 제거
            shutil.move(str(bak_path), str(original))
            logger.info(f"백업 복원: {bak_path} → {original}")
```

### 백필 실행 흐름 (안전한 덮어쓰기 포함)

```
1. backup_existing() → 기존 파일을 .bak으로 이동
2. PipelineRunner.run() → extract → transform → load → verify
3-a. verify 성공 → remove_backup() → .bak 파일 삭제
3-b. verify 실패 또는 예외 → restore_backup() → .bak 파일 복원
```

## 완료 조건

- [ ] `_split_into_months()` 테스트: 다양한 날짜 범위 → 월별 분할 확인
  - 같은 월 내 범위 (예: 2026-03-01 ~ 2026-03-31 → [2026-03-01])
  - 여러 월 범위 (예: 2026-01-15 ~ 2026-04-10 → 4개월)
  - 연도 경계 (예: 2025-11-01 ~ 2026-02-28 → 4개월)
- [ ] `backup_existing()` 테스트: .bak 파일 생성 확인
- [ ] `remove_backup()` 테스트: .bak 파일 삭제 확인
- [ ] `restore_backup()` 테스트: .bak → 원본 복원 확인
- [ ] `run_backfill()` 통합 테스트: 월별 순차 실행 + 결과 리스트 반환
- [ ] 파일 없는 경우 backup_existing() → None 반환 확인

## 참고 (선택)

- 백필 설계: `docs/architecture.md` 섹션 3.5
- 파티셔닝 구조: `{base_path}/{TABLE_NAME}/YYYY={MM}/`
