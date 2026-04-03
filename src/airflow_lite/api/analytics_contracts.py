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
