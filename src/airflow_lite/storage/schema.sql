CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              TEXT PRIMARY KEY,     -- UUID
    pipeline_name   TEXT NOT NULL,
    execution_date  TEXT NOT NULL,        -- YYYY-MM-DD
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- pending | queued | running | success | failed
    started_at      TEXT,                 -- ISO 8601
    finished_at     TEXT,                 -- ISO 8601
    trigger_type    TEXT NOT NULL DEFAULT 'scheduled',
                    -- scheduled | manual | backfill
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS step_runs (
    id                TEXT PRIMARY KEY,   -- UUID
    pipeline_run_id   TEXT NOT NULL REFERENCES pipeline_runs(id),
    step_name         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
                      -- pending | running | success | failed | skipped
    started_at        TEXT,
    finished_at       TEXT,
    records_processed INTEGER DEFAULT 0,
    error_message     TEXT,
    retry_count       INTEGER DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_exec_date
    ON pipeline_runs(execution_date);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_step_runs_pipeline_run
    ON step_runs(pipeline_run_id);

CREATE TABLE IF NOT EXISTS connections (
    conn_id       TEXT PRIMARY KEY,
    conn_type     TEXT NOT NULL,
    host          TEXT,
    port          INTEGER,
    schema        TEXT,
    login         TEXT,
    password      TEXT,
    extra         TEXT,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS variables (
    key           TEXT PRIMARY KEY,
    val           TEXT,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS pools (
    pool_name     TEXT PRIMARY KEY,
    slots         INTEGER NOT NULL DEFAULT 1,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_configs (
    name              TEXT PRIMARY KEY,
    source_table      TEXT NOT NULL,
    partition_column  TEXT NOT NULL,
    strategy          TEXT NOT NULL DEFAULT 'full',
    schedule          TEXT NOT NULL,
    chunk_size        INTEGER,
    columns           TEXT,
    incremental_key   TEXT
);
