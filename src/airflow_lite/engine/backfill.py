from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING
from dateutil.relativedelta import relativedelta
import logging

if TYPE_CHECKING:
    from airflow_lite.engine.pipeline import PipelineRunner

logger = logging.getLogger("airflow_lite.engine.backfill")


class BackfillManager:
    def __init__(
        self,
        pipeline_runner: PipelineRunner,
        parquet_base_path: str,
    ):
        self.pipeline_runner = pipeline_runner
        self.parquet_base_path = parquet_base_path

    def run_backfill(
        self,
        pipeline_name: str,
        start_date: date,
        end_date: date,
        force_rerun: bool = False,
    ) -> list:
        """날짜 범위를 월 단위로 분할하여 순차 실행.

        1. start_date~end_date를 월 경계로 분할
        2. 각 월에 대해 PipelineRunner.run(execution_date=해당월)
        3. 결과를 리스트로 반환
        """
        if end_date < start_date:
            raise ValueError("end_date는 start_date보다 같거나 이후여야 합니다.")

        months = self._split_into_months(start_date, end_date)
        results = []

        for month_date in months:
            logger.info(f"백필 실행: {pipeline_name} / {month_date}")
            run = self.pipeline_runner.run(
                execution_date=month_date,
                trigger_type="backfill",
                force_rerun=force_rerun,
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

    def _parquet_path(self, table_name: str, year: int, month: int) -> Path:
        base = Path(self.parquet_base_path)
        return (
            base
            / table_name
            / f"year={year:04d}"
            / f"month={month:02d}"
            / f"{table_name}_{year:04d}_{month:02d}.parquet"
        )

    def backup_existing(self, table_name: str, year: int, month: int) -> Path | None:
        """기존 parquet 파일을 `.bak`으로 이동(백업)하고 백업 경로를 반환한다.

        - 파일이 없으면 None을 반환한다.
        - 백업은 같은 디렉토리 내 rename으로 수행한다.
        """
        parquet_path = self._parquet_path(table_name, year, month)
        if not parquet_path.exists():
            return None

        bak_path = parquet_path.with_suffix(parquet_path.suffix + ".bak")
        try:
            if bak_path.exists():
                bak_path.unlink()
            parquet_path.replace(bak_path)
        except OSError:
            # Windows 파일 잠금 등의 환경 이슈에서는 예외를 표면화한다.
            raise
        return bak_path

    def remove_backup(self, bak_path: Path | None) -> None:
        """백업 파일을 삭제한다. (None/미존재 경로는 무시)"""
        if not bak_path:
            return
        try:
            path = Path(bak_path)
            if path.exists():
                path.unlink()
        except OSError:
            # 운영에서는 백업 제거 실패가 치명적이지 않으므로, 호출자에서 처리 가능하게 무시한다.
            return

    def restore_backup(self, bak_path: Path | None) -> None:
        """`.bak`을 원본 parquet로 복원한다. (None/미존재 경로는 무시)"""
        if not bak_path:
            return
        path = Path(bak_path)
        if not path.exists():
            return
        if path.suffix != ".bak":
            return
        original_path = path.with_suffix("")  # drop ".bak"
        try:
            if original_path.exists():
                original_path.unlink()
            path.replace(original_path)
        except OSError:
            raise
