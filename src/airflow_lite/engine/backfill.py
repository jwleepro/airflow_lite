from datetime import date
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
        force_rerun: bool = True,
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

    def backup_existing(self, table_name: str, year: int, month: int) -> Path | None:
        """기존 Parquet 파일을 .bak 확장자로 이동.

        예: {TABLE_NAME}_{YYYY}_{MM}.parquet → {TABLE_NAME}_{YYYY}_{MM}.parquet.bak
        파일이 없으면 None 반환.
        """
        parquet_dir = (
            self.parquet_base_path / table_name / f"year={year:04d}" / f"month={month:02d}"
        )
        parquet_file = parquet_dir / f"{table_name}_{year:04d}_{month:02d}.parquet"

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
