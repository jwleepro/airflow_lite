from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from airflow_lite.storage.models import ConnectionModel, VariableModel, PoolModel, PipelineModel
from airflow_lite.storage.admin_repository import AdminRepository

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_repo(request: Request) -> AdminRepository:
    repo = getattr(request.app.state, "admin_repo", None)
    if not repo:
        raise HTTPException(status_code=500, detail="AdminRepository not initialized")
    return repo


# --- Connections ---
@router.get("/connections", response_model=List[ConnectionModel])
def list_connections(repo: AdminRepository = Depends(get_admin_repo)):
    return repo.list_connections()


@router.post("/connections")
def create_connection(conn: ConnectionModel, repo: AdminRepository = Depends(get_admin_repo)):
    repo.create_connection(conn)
    return {"message": "Connection created successfully"}


@router.put("/connections/{conn_id}")
def update_connection(conn_id: str, conn: ConnectionModel, repo: AdminRepository = Depends(get_admin_repo)):
    if conn_id != conn.conn_id:
        raise HTTPException(status_code=400, detail="Connection ID mismatch")
    repo.update_connection(conn)
    return {"message": "Connection updated successfully"}


@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: str, repo: AdminRepository = Depends(get_admin_repo)):
    repo.delete_connection(conn_id)
    return {"message": "Connection deleted successfully"}


# --- Variables ---
@router.get("/variables", response_model=List[VariableModel])
def list_variables(repo: AdminRepository = Depends(get_admin_repo)):
    return repo.list_variables()


@router.post("/variables")
def create_variable(var: VariableModel, repo: AdminRepository = Depends(get_admin_repo)):
    repo.create_variable(var)
    return {"message": "Variable created successfully"}


@router.put("/variables/{key}")
def update_variable(key: str, var: VariableModel, repo: AdminRepository = Depends(get_admin_repo)):
    if key != var.key:
        raise HTTPException(status_code=400, detail="Variable Key mismatch")
    repo.update_variable(var)
    return {"message": "Variable updated successfully"}


@router.delete("/variables/{key}")
def delete_variable(key: str, repo: AdminRepository = Depends(get_admin_repo)):
    repo.delete_variable(key)
    return {"message": "Variable deleted successfully"}


# --- Pools ---
@router.get("/pools", response_model=List[PoolModel])
def list_pools(repo: AdminRepository = Depends(get_admin_repo)):
    return repo.list_pools()


@router.post("/pools")
def create_pool(pool: PoolModel, repo: AdminRepository = Depends(get_admin_repo)):
    repo.create_pool(pool)
    return {"message": "Pool created successfully"}


@router.put("/pools/{pool_name}")
def update_pool(pool_name: str, pool: PoolModel, repo: AdminRepository = Depends(get_admin_repo)):
    if pool_name != pool.pool_name:
        raise HTTPException(status_code=400, detail="Pool Name mismatch")
    repo.update_pool(pool)
    return {"message": "Pool updated successfully"}


@router.delete("/pools/{pool_name}")
def delete_pool(pool_name: str, repo: AdminRepository = Depends(get_admin_repo)):
    repo.delete_pool(pool_name)
    return {"message": "Pool deleted successfully"}


# --- Pipelines ---
@router.get("/pipelines", response_model=List[PipelineModel])
def list_pipelines(repo: AdminRepository = Depends(get_admin_repo)):
    return repo.list_pipelines()


@router.post("/pipelines")
def create_pipeline(pipeline: PipelineModel, repo: AdminRepository = Depends(get_admin_repo)):
    repo.create_pipeline(pipeline)
    return {"message": "Pipeline created successfully"}


@router.put("/pipelines/{name}")
def update_pipeline(name: str, pipeline: PipelineModel, repo: AdminRepository = Depends(get_admin_repo)):
    if name != pipeline.name:
        raise HTTPException(status_code=400, detail="Pipeline Name mismatch")
    repo.update_pipeline(pipeline)
    return {"message": "Pipeline updated successfully"}


@router.delete("/pipelines/{name}")
def delete_pipeline(name: str, repo: AdminRepository = Depends(get_admin_repo)):
    repo.delete_pipeline(name)
    return {"message": "Pipeline deleted successfully"}
