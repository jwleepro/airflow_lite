import pytest
import yaml
from airflow_lite.storage.database import Database
from airflow_lite.storage.admin_repository import AdminRepository
from airflow_lite.storage.models import ConnectionModel, PipelineModel, VariableModel, PoolModel

@pytest.fixture
def db(tmp_path):
    database_path = tmp_path / "airflow.db"
    database = Database(str(database_path))
    database.initialize()
    return database

@pytest.fixture
def admin_repo(db):
    return AdminRepository(db)


def test_connection_crud(admin_repo):
    # Create
    conn = ConnectionModel(
        conn_id="test_conn",
        conn_type="postgres",
        host="localhost",
        schema="public",
        login="admin",
        password="secretpassword",
        description="A test connection"
    )
    admin_repo.create_connection(conn)

    # Read
    fetched = admin_repo.get_connection("test_conn")
    assert fetched is not None
    assert fetched.conn_id == "test_conn"
    assert fetched.password == "secretpassword"

    # List
    all_conns = admin_repo.list_connections()
    assert len(all_conns) == 1
    assert all_conns[0].conn_id == "test_conn"

    # Update
    conn.host = "127.0.0.1"
    admin_repo.update_connection(conn)
    fetched_updated = admin_repo.get_connection("test_conn")
    assert fetched_updated.host == "127.0.0.1"

    # Delete
    admin_repo.delete_connection("test_conn")
    assert admin_repo.get_connection("test_conn") is None


def test_variable_crud(admin_repo):
    var = VariableModel(key="my_var", val="123", description="A test variable")
    
    # Create
    admin_repo.create_variable(var)
    
    # Read
    fetched = admin_repo.get_variable("my_var")
    assert fetched is not None
    assert fetched.val == "123"

    # List
    all_vars = admin_repo.list_variables()
    assert len(all_vars) == 1
    
    # Update
    var.val = "456"
    admin_repo.update_variable(var)
    assert admin_repo.get_variable("my_var").val == "456"

    # Delete
    admin_repo.delete_variable("my_var")
    assert admin_repo.get_variable("my_var") is None


def test_pool_crud(admin_repo):
    pool = PoolModel(pool_name="test_pool", slots=5, description="A test pool")
    
    # Create
    admin_repo.create_pool(pool)
    
    # Read
    fetched = admin_repo.get_pool("test_pool")
    assert fetched is not None
    assert fetched.slots == 5

    # List
    all_pools = admin_repo.list_pools()
    assert len(all_pools) == 1
    
    # Update
    pool.slots = 10
    admin_repo.update_pool(pool)
    assert admin_repo.get_pool("test_pool").slots == 10

    # Delete
    admin_repo.delete_pool("test_pool")
    assert admin_repo.get_pool("test_pool") is None


def test_pipeline_crud(admin_repo):
    pipeline = PipelineModel(
        name="production_log",
        table="PRODUCTION_LOG",
        source_where_template="LOG_DATE >= :data_interval_start AND LOG_DATE < :data_interval_end",
        strategy="incremental",
        schedule="0 */6 * * *",
        chunk_size=5000,
        columns="LOG_ID, LOG_DATE, STATUS",
        incremental_key="UPDATED_AT",
    )

    admin_repo.create_pipeline(pipeline)

    fetched = admin_repo.get_pipeline("production_log")
    assert fetched is not None
    assert fetched.table == "PRODUCTION_LOG"
    assert fetched.columns == "LOG_ID,LOG_DATE,STATUS"

    listed = admin_repo.list_pipelines()
    assert len(listed) == 1
    assert listed[0].name == "production_log"

    pipeline.strategy = "full"
    pipeline.incremental_key = None
    pipeline.columns = "LOG_ID, STATUS"
    admin_repo.update_pipeline(pipeline)
    updated = admin_repo.get_pipeline("production_log")
    assert updated.strategy == "full"
    assert updated.incremental_key is None
    assert updated.columns == "LOG_ID,STATUS"

    admin_repo.delete_pipeline("production_log")
    assert admin_repo.get_pipeline("production_log") is None


def test_pipeline_crud_supports_source_where_template_and_bind_params(admin_repo):
    pipeline = PipelineModel(
        name="production_log_template",
        table="PRODUCTION_LOG",
        source_where_template="TRAN_YEAR = :year AND TRAN_MONTH = :month",
        source_bind_params='{"year":"{{ data_interval_start.year }}","month":"{{ data_interval_start.month }}"}',
        strategy="full",
        schedule="0 2 * * *",
    )

    admin_repo.create_pipeline(pipeline)

    fetched = admin_repo.get_pipeline("production_log_template")
    assert fetched is not None
    assert fetched.source_where_template == "TRAN_YEAR = :year AND TRAN_MONTH = :month"
    assert fetched.source_bind_params == '{"month":"{{ data_interval_start.month }}","year":"{{ data_interval_start.year }}"}'


def test_migrate_from_yaml_imports_admin_entities_and_removes_legacy_sections(tmp_path):
    config_path = tmp_path / "pipelines.yaml"
    config_path.write_text(
        """\
oracle:
  host: "db.local"
  port: 1521
  service_name: "ORCL"
  user: "scott"
  password: "tiger"

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

connections:
  - conn_id: "external_conn"
    conn_type: "oracle"
    host: "db2.local"
    port: 1521
    schema: "MES"
    login: "etl"
    password: "pw"

variables:
  - key: "batch_size"
    val: "10000"
    description: "chunk size"

pools:
  - pool_name: "default_pool"
    slots: 4
    description: "default"

pipelines:
  - name: "production_log"
    table: "PRODUCTION_LOG"
    source_where_template: "LOG_DATE >= :data_interval_start AND LOG_DATE < :data_interval_end"
    strategy: "incremental"
    schedule: "0 */6 * * *"
    chunk_size: 5000
    columns: ["LOG_ID", "LOG_DATE", "STATUS"]
    incremental_key: "UPDATED_AT"
""",
        encoding="utf-8",
    )

    db = Database(str(tmp_path / "admin.db"))
    db.initialize()
    repo = AdminRepository(db, str(config_path))

    oracle = repo.get_connection("oracle")
    assert oracle is not None
    assert oracle.host == "db.local"
    assert oracle.login == "scott"
    assert oracle.password == "tiger"

    external = repo.get_connection("external_conn")
    assert external is not None
    assert external.password == "pw"

    variable = repo.get_variable("batch_size")
    assert variable is not None
    assert variable.val == "10000"

    pool = repo.get_pool("default_pool")
    assert pool is not None
    assert pool.slots == 4

    pipeline = repo.get_pipeline("production_log")
    assert pipeline is not None
    assert pipeline.columns == "LOG_ID,LOG_DATE,STATUS"

    migrated_yaml = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for removed_key in ("oracle", "connections", "variables", "pools", "pipelines"):
        assert removed_key not in migrated_yaml
    assert "storage" in migrated_yaml
