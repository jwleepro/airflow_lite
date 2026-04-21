from airflow_lite.dag_api import Pipeline

pipelines = [
    Pipeline(
        id="production_log",
        table="PRODUCTION_LOG",
        source_where_template="LOG_DATE >= :data_interval_start AND LOG_DATE < :data_interval_end",
        strategy="full",
        schedule="0 2 * * *",
        chunk_size=5000,
    ),
]
