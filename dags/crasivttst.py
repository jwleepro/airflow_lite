from airflow_lite.dag_api import Pipeline

pipelines = [
    Pipeline(
        id="CRAIVTTST",
        table="CRAIVTTST",
        source_where_template=(
            "TRAN_TIME >= :data_interval_start "
            "AND TRAN_TIME < :data_interval_end"
        ),
        strategy="full",
        schedule="56 0 * * *",
        chunk_size=5000,
    ),
]
