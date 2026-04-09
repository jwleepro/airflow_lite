import pytest
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
