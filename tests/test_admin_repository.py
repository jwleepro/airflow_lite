import pytest
import yaml
from airflow_lite.storage.database import Database
from airflow_lite.storage.admin_repository import AdminRepository
from airflow_lite.storage.models import ConnectionModel, VariableModel, PoolModel

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

    migrated_yaml = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for removed_key in ("oracle", "connections", "variables", "pools"):
        assert removed_key not in migrated_yaml
    assert "storage" in migrated_yaml
