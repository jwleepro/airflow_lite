from __future__ import annotations

from dataclasses import dataclass, field

from airflow_lite.mart.execution import MartBuildResult


@dataclass(frozen=True)
class MartValidationIssue:
    severity: str
    message: str


@dataclass
class MartValidationReport:
    issues: list[MartValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def add_issue(self, severity: str, message: str) -> None:
        self.issues.append(MartValidationIssue(severity=severity, message=message))


class DuckDBMartValidator:
    """Validate that staging builds contain the expected source tables and metadata."""

    REQUIRED_METADATA_TABLES = (
        "mart_dataset_files",
        "mart_dataset_sources",
        "mart_datasets",
    )

    def validate_build(self, build_result: MartBuildResult) -> MartValidationReport:
        report = MartValidationReport()
        staging_path = build_result.plan.paths.staging_db_path
        if not staging_path.exists():
            report.add_issue("error", f"staging database is missing: {staging_path}")
            return report

        import duckdb

        connection = duckdb.connect(str(staging_path), read_only=True)
        try:
            for table_name in self.REQUIRED_METADATA_TABLES:
                table_exists = connection.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                    [table_name],
                ).fetchone()[0]
                if not table_exists:
                    report.add_issue("error", f"required mart metadata table is missing: {table_name}")

            raw_table_exists = connection.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [build_result.raw_table_name],
            ).fetchone()[0]
            if not raw_table_exists:
                report.add_issue("error", f"required raw mart table is missing: {build_result.raw_table_name}")
                return report

            actual_row_count = connection.execute(
                f'SELECT COUNT(*) FROM "{build_result.raw_table_name}"'
            ).fetchone()[0]
            if actual_row_count != build_result.row_count:
                report.add_issue(
                    "error",
                    f"row count mismatch for {build_result.raw_table_name}: expected {build_result.row_count}, got {actual_row_count}",
                )

            source_row = connection.execute(
                """
                SELECT row_count, file_count, last_build_id
                FROM mart_dataset_sources
                WHERE dataset_name = ? AND source_name = ?
                """,
                [build_result.dataset_name, build_result.source_name],
            ).fetchone()
            if source_row is None:
                report.add_issue(
                    "error",
                    f"dataset source metadata is missing: {build_result.dataset_name}/{build_result.source_name}",
                )
            else:
                row_count, file_count, last_build_id = source_row
                if row_count != build_result.row_count:
                    report.add_issue(
                        "error",
                        f"dataset source row_count mismatch: expected {build_result.row_count}, got {row_count}",
                    )
                if file_count != build_result.file_count:
                    report.add_issue(
                        "error",
                        f"dataset source file_count mismatch: expected {build_result.file_count}, got {file_count}",
                    )
                if last_build_id != build_result.plan.request.build_id:
                    report.add_issue(
                        "error",
                        f"dataset source build id mismatch: expected {build_result.plan.request.build_id}, got {last_build_id}",
                    )

            actual_file_rows = connection.execute(
                """
                SELECT COALESCE(SUM(row_count), 0), COUNT(*)
                FROM mart_dataset_files
                WHERE dataset_name = ? AND source_name = ?
                """,
                [build_result.dataset_name, build_result.source_name],
            ).fetchone()
            if actual_file_rows is None:
                report.add_issue(
                    "error",
                    f"dataset file metadata is missing: {build_result.dataset_name}/{build_result.source_name}",
                )
            else:
                total_rows, file_count = actual_file_rows
                if total_rows != build_result.row_count:
                    report.add_issue(
                        "error",
                        f"dataset file metadata row_count mismatch: expected {build_result.row_count}, got {total_rows}",
                    )
                if file_count != build_result.file_count:
                    report.add_issue(
                        "error",
                        f"dataset file metadata count mismatch: expected {build_result.file_count}, got {file_count}",
                    )

            dataset_row = connection.execute(
                """
                SELECT total_rows, total_files
                FROM mart_datasets
                WHERE dataset_name = ?
                """,
                [build_result.dataset_name],
            ).fetchone()
            if dataset_row is None:
                report.add_issue("error", f"dataset summary is missing: {build_result.dataset_name}")
            else:
                total_rows, total_files = dataset_row
                if total_rows < build_result.row_count:
                    report.add_issue(
                        "error",
                        f"dataset summary total_rows is smaller than source rows: {total_rows} < {build_result.row_count}",
                    )
                if total_files < build_result.file_count:
                    report.add_issue(
                        "error",
                        f"dataset summary total_files is smaller than source files: {total_files} < {build_result.file_count}",
                    )
        finally:
            connection.close()

        return report
