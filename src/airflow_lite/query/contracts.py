from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class AnalyticsFilterType(str, Enum):
    DATE_RANGE = "date_range"
    SELECT = "select"
    MULTI_SELECT = "multi_select"


class SummaryPrecision(str, Enum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    PERCENT = "percent"


class ChartGranularity(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class DashboardChartType(str, Enum):
    LINE = "line"
    BAR = "bar"


class DashboardLayoutSpan(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class DashboardActionType(str, Enum):
    DRILLDOWN = "drilldown"
    EXPORT = "export"


class DashboardRequestMethod(str, Enum):
    GET = "GET"
    POST = "POST"


class DashboardActionScope(str, Enum):
    DASHBOARD = "dashboard"
    CARD = "card"
    CHART = "chart"


class DashboardActionStatus(str, Enum):
    AVAILABLE = "available"
    PLANNED = "planned"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class DetailColumnType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DATE = "date"
    DATETIME = "datetime"


class ExportFormat(str, Enum):
    CSV_ZIP = "csv.zip"
    PARQUET = "parquet"
    XLSX = "xlsx"


class ExportJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FilterOption(BaseModel):
    value: str
    label: str


class FilterDefinition(BaseModel):
    key: str
    label: str
    type: AnalyticsFilterType
    required: bool = False
    supports_multiple: bool = False
    options: list[FilterOption] = Field(default_factory=list)


class DateRangeFilterValue(BaseModel):
    start: date | None = None
    end: date | None = None


class SummaryQueryRequest(BaseModel):
    dataset: str
    window: DateRangeFilterValue | None = None
    filters: dict[str, list[str]] = Field(default_factory=dict)


class SummaryMetricCard(BaseModel):
    key: str
    label: str
    value: float | int
    precision: SummaryPrecision = SummaryPrecision.INTEGER
    unit: str | None = None
    delta: float | None = None
    comparison_label: str | None = None


class SummaryQueryResponse(BaseModel):
    dataset: str
    generated_at: datetime
    filters_applied: dict[str, list[str]] = Field(default_factory=dict)
    metrics: list[SummaryMetricCard] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChartQueryRequest(BaseModel):
    dataset: str
    chart_id: str
    granularity: ChartGranularity = ChartGranularity.DAY
    limit: int = Field(default=31, ge=1, le=366)
    window: DateRangeFilterValue | None = None
    filters: dict[str, list[str]] = Field(default_factory=dict)
    language: str = "en"  # i18n 언어


class ChartPoint(BaseModel):
    bucket: str
    value: float | int
    label: str | None = None


class ChartSeries(BaseModel):
    key: str
    label: str
    points: list[ChartPoint] = Field(default_factory=list)


class ChartQueryResponse(BaseModel):
    dataset: str
    chart_id: str
    title: str
    granularity: ChartGranularity
    filters_applied: dict[str, list[str]] = Field(default_factory=dict)
    series: list[ChartSeries] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyticsFilterMetadataResponse(BaseModel):
    dataset: str
    filters: list[FilterDefinition] = Field(default_factory=list)


class DetailSortField(BaseModel):
    field: str
    direction: SortDirection = SortDirection.ASC


class DetailQueryRequest(BaseModel):
    dataset: str
    detail_key: str
    filters: dict[str, list[str]] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort: list[DetailSortField] = Field(default_factory=list)


class DetailColumnDefinition(BaseModel):
    key: str
    label: str
    type: DetailColumnType
    sortable: bool = True


class DetailQueryResponse(BaseModel):
    dataset: str
    detail_key: str
    columns: list[DetailColumnDefinition] = Field(default_factory=list)
    rows: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    sort: list[DetailSortField] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DashboardCardDefinition(BaseModel):
    key: str
    label: str
    metric_key: str
    description: str | None = None
    summary_endpoint: str = ""
    request_method: DashboardRequestMethod = DashboardRequestMethod.POST
    filter_keys: list[str] = Field(default_factory=list)
    span: DashboardLayoutSpan = DashboardLayoutSpan.SMALL


class DashboardChartDefinition(BaseModel):
    chart_id: str
    title: str
    chart_type: DashboardChartType
    default_granularity: ChartGranularity
    query_endpoint: str
    request_method: DashboardRequestMethod = DashboardRequestMethod.POST
    filter_keys: list[str] = Field(default_factory=list)
    limit: int = Field(default=12, ge=1, le=366)
    span: DashboardLayoutSpan = DashboardLayoutSpan.LARGE


class DashboardActionDefinition(BaseModel):
    key: str
    label: str
    type: DashboardActionType
    status: DashboardActionStatus = DashboardActionStatus.PLANNED
    description: str | None = None
    scope: DashboardActionScope = DashboardActionScope.DASHBOARD
    target_key: str | None = None
    endpoint: str | None = None
    request_method: DashboardRequestMethod | None = None
    filter_keys: list[str] = Field(default_factory=list)
    format: str | None = None
    status_reason: str | None = None


class DashboardDefinitionResponse(BaseModel):
    contract_version: str = "dashboard.v1"
    dashboard_id: str
    title: str
    description: str | None = None
    dataset: str
    last_refreshed_at: datetime | None = None
    filters: list[FilterDefinition] = Field(default_factory=list)
    cards: list[DashboardCardDefinition] = Field(default_factory=list)
    charts: list[DashboardChartDefinition] = Field(default_factory=list)
    drilldown_actions: list[DashboardActionDefinition] = Field(default_factory=list)
    export_actions: list[DashboardActionDefinition] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExportCreateRequest(BaseModel):
    dataset: str
    action_key: str
    format: ExportFormat
    filters: dict[str, list[str]] = Field(default_factory=dict)


class ExportCreateResponse(BaseModel):
    job_id: str
    status: ExportJobStatus
    format: ExportFormat
    created_at: datetime


class ExportJobResponse(BaseModel):
    job_id: str
    dataset: str
    action_key: str
    status: ExportJobStatus
    format: ExportFormat
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    row_count: int | None = None
    file_name: str | None = None
    download_endpoint: str | None = None
    error_message: str | None = None
