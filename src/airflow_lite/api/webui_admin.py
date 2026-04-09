from html import escape

from airflow_lite.api.paths import MONITOR_ADMIN_PATH
from airflow_lite.api.webui_helpers import fmt, render_layout, t


def render_admin_page(
    connections: list,
    variables: list,
    pools: list,
    pipelines: list,
    *,
    language: str,
) -> str:
    # --- Connections ---
    conn_rows = ""
    for connection in connections:
        conn_rows += f"""<tr>
            <td>{fmt(connection.conn_id)}</td>
            <td>{fmt(connection.conn_type)}</td>
            <td>{fmt(connection.host)}</td>
            <td>{fmt(connection.port)}</td>
            <td>{fmt(connection.schema)}</td>
            <td>{fmt(connection.login)}</td>
            <td>********</td>
            <td>{fmt(connection.description)}</td>
            <td style="text-align: right;">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/connections/delete" style="display:inline;" onsubmit="return confirm('Delete connection?');">
                    <input type="hidden" name="conn_id" value="{escape(connection.conn_id)}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>"""
    if not conn_rows:
        conn_rows = '<tr><td colspan="9" class="empty">No connections found.</td></tr>'

    conn_html = f"""
    <section class="panel">
        <div class="panel-head">
            <h2>Connections</h2>
        </div>
        <div class="table-wrap" style="margin-top:12px;">
            <table>
                <thead>
                    <tr><th>Conn ID</th><th>Type</th><th>Host</th><th>Port</th><th>Schema</th><th>Login</th><th>Password</th><th>Description</th><th style="width:80px;"></th></tr>
                </thead>
                <tbody>{conn_rows}</tbody>
            </table>
        </div>
        <div style="margin-top: 16px; padding: 12px; background: var(--panel-soft); border-radius: 8px; border: 1px solid var(--line);">
            <h3 style="margin-top: 0; font-size: 1rem;">Add Connection</h3>
            <form method="POST" action="{MONITOR_ADMIN_PATH}/connections" class="grid-3" style="align-items: end;">
                <div class="filter-field">
                    <label class="eyebrow">Conn ID</label>
                    <input type="text" name="conn_id" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Type</label>
                    <input type="text" name="conn_type" value="oracle" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Host</label>
                    <input type="text" name="host" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Port</label>
                    <input type="number" name="port" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Schema</label>
                    <input type="text" name="schema" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Login</label>
                    <input type="text" name="login" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Password</label>
                    <input type="password" name="password" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field" style="grid-column: span 2;">
                    <label class="eyebrow">Description</label>
                    <input type="text" name="description" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div style="grid-column: span 3; text-align: right;">
                    <button type="submit" class="primary">Add Connection</button>
                </div>
            </form>
        </div>
    </section>
    """

    # --- Variables ---
    var_rows = ""
    for variable in variables:
        var_rows += f"""<tr>
            <td>{fmt(variable.key)}</td>
            <td>{fmt(variable.val)}</td>
            <td>{fmt(variable.description)}</td>
            <td style="text-align: right;">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/variables/delete" style="display:inline;" onsubmit="return confirm('Delete variable?');">
                    <input type="hidden" name="key" value="{escape(variable.key)}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>"""
    if not var_rows:
        var_rows = '<tr><td colspan="4" class="empty">No variables found.</td></tr>'

    var_html = f"""
    <section class="panel">
        <div class="panel-head">
            <h2>Variables</h2>
        </div>
        <div class="table-wrap" style="margin-top:12px;">
            <table>
                <thead>
                    <tr><th>Key</th><th>Value</th><th>Description</th><th style="width:80px;"></th></tr>
                </thead>
                <tbody>{var_rows}</tbody>
            </table>
        </div>
        <div style="margin-top: 16px; padding: 12px; background: var(--panel-soft); border-radius: 8px; border: 1px solid var(--line);">
            <h3 style="margin-top: 0; font-size: 1rem;">Add Variable</h3>
            <form method="POST" action="{MONITOR_ADMIN_PATH}/variables" class="grid-3" style="align-items: end;">
                <div class="filter-field">
                    <label class="eyebrow">Key</label>
                    <input type="text" name="key" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Value</label>
                    <input type="text" name="val" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Description</label>
                    <input type="text" name="description" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div style="grid-column: span 3; text-align: right;">
                    <button type="submit" class="primary">Add Variable</button>
                </div>
            </form>
        </div>
    </section>
    """

    # --- Pools ---
    pool_rows = ""
    for pool in pools:
        pool_rows += f"""<tr>
            <td>{fmt(pool.pool_name)}</td>
            <td>{fmt(pool.slots)}</td>
            <td>{fmt(pool.description)}</td>
            <td style="text-align: right;">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/pools/delete" style="display:inline;" onsubmit="return confirm('Delete pool?');">
                    <input type="hidden" name="pool_name" value="{escape(pool.pool_name)}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>"""
    if not pool_rows:
        pool_rows = '<tr><td colspan="4" class="empty">No pools found.</td></tr>'

    pool_html = f"""
    <section class="panel">
        <div class="panel-head">
            <h2>Pools</h2>
        </div>
        <div class="table-wrap" style="margin-top:12px;">
            <table>
                <thead>
                    <tr><th>Pool Name</th><th>Slots</th><th>Description</th><th style="width:80px;"></th></tr>
                </thead>
                <tbody>{pool_rows}</tbody>
            </table>
        </div>
        <div style="margin-top: 16px; padding: 12px; background: var(--panel-soft); border-radius: 8px; border: 1px solid var(--line);">
            <h3 style="margin-top: 0; font-size: 1rem;">Add Pool</h3>
            <form method="POST" action="{MONITOR_ADMIN_PATH}/pools" class="grid-3" style="align-items: end;">
                <div class="filter-field">
                    <label class="eyebrow">Pool Name</label>
                    <input type="text" name="pool_name" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Slots</label>
                    <input type="number" name="slots" value="1" min="1" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Description</label>
                    <input type="text" name="description" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div style="grid-column: span 3; text-align: right;">
                    <button type="submit" class="primary">Add Pool</button>
                </div>
            </form>
        </div>
    </section>
    """

    # --- Pipelines ---
    pipeline_rows = ""
    for pipeline in pipelines:
        escaped_name = escape(pipeline.name)
        edit_row_id = f"pipeline-edit-{escaped_name}"
        is_incremental = pipeline.strategy == "incremental"
        pipeline_rows += f"""<tr>
            <td>{fmt(pipeline.name)}</td>
            <td>{fmt(pipeline.table)}</td>
            <td>{fmt(pipeline.partition_column)}</td>
            <td>{fmt(pipeline.strategy)}</td>
            <td>{fmt(pipeline.schedule)}</td>
            <td>{fmt(pipeline.chunk_size)}</td>
            <td>{fmt(pipeline.columns)}</td>
            <td>{fmt(pipeline.incremental_key)}</td>
            <td style="text-align: right; white-space: nowrap;">
                <button type="button" class="secondary" onclick="togglePipelineEdit('{edit_row_id}')">Edit</button>
                <form method="POST" action="{MONITOR_ADMIN_PATH}/pipelines/delete" style="display:inline;" onsubmit="return confirm('Delete pipeline?');">
                    <input type="hidden" name="name" value="{escaped_name}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>
        <tr id="{edit_row_id}" style="display:none;">
            <td colspan="9">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/pipelines/edit" class="grid-3" style="padding: 12px; background: var(--panel-soft); border: 1px solid var(--line); border-radius: 8px;">
                    <div class="filter-field">
                        <label class="eyebrow">Name</label>
                        <input type="text" name="name" value="{escaped_name}" readonly style="padding:8px; border:1px solid var(--line); border-radius:6px; background:#f5f5f5;"/>
                    </div>
                    <div class="filter-field">
                        <label class="eyebrow">Table</label>
                        <input type="text" name="table" value="{escape(pipeline.table)}" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                    </div>
                    <div class="filter-field">
                        <label class="eyebrow">Partition Column</label>
                        <input type="text" name="partition_column" value="{escape(pipeline.partition_column)}" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                    </div>
                    <div class="filter-field">
                        <label class="eyebrow">Strategy</label>
                        <select name="strategy" onchange="toggleIncrementalField(this, '{edit_row_id}')" style="padding:8px; border:1px solid var(--line); border-radius:6px;">
                            <option value="full" {'selected' if pipeline.strategy == 'full' else ''}>full</option>
                            <option value="incremental" {'selected' if is_incremental else ''}>incremental</option>
                        </select>
                    </div>
                    <div class="filter-field">
                        <label class="eyebrow">Schedule</label>
                        <input type="text" name="schedule" value="{escape(pipeline.schedule)}" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                    </div>
                    <div class="filter-field">
                        <label class="eyebrow">Chunk Size</label>
                        <input type="number" name="chunk_size" value="{'' if pipeline.chunk_size is None else pipeline.chunk_size}" min="1" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                    </div>
                    <div class="filter-field" style="grid-column: span 2;">
                        <label class="eyebrow">Columns</label>
                        <textarea name="columns" rows="2" placeholder="COL1, COL2, COL3" style="padding:8px; border:1px solid var(--line); border-radius:6px; width:100%;">{escape(pipeline.columns or '')}</textarea>
                    </div>
                    <div class="filter-field incremental-key-field" data-prefix="{edit_row_id}" style="display: {'block' if is_incremental else 'none'};">
                        <label class="eyebrow">Incremental Key</label>
                        <input type="text" name="incremental_key" value="{escape(pipeline.incremental_key or '')}" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                    </div>
                    <div style="grid-column: span 3; text-align: right;">
                        <button type="submit" class="primary">Save Pipeline</button>
                    </div>
                </form>
            </td>
        </tr>"""
    if not pipeline_rows:
        pipeline_rows = '<tr><td colspan="9" class="empty">No pipelines found.</td></tr>'

    pipelines_html = f"""
    <section class="panel">
        <div class="panel-head">
            <h2>Pipelines</h2>
        </div>
        <div style="margin-top: 12px; padding: 10px 12px; background: #fff6dd; border: 1px solid #f0d58c; border-radius: 8px; color: #6b4f00;">
            Pipeline settings changes require a service restart.
        </div>
        <div class="table-wrap" style="margin-top:12px;">
            <table>
                <thead>
                    <tr>
                        <th>Name</th><th>Table</th><th>Partition Col</th><th>Strategy</th><th>Schedule</th><th>Chunk Size</th><th>Columns</th><th>Incr. Key</th><th style="width:180px;"></th>
                    </tr>
                </thead>
                <tbody>{pipeline_rows}</tbody>
            </table>
        </div>
        <div style="margin-top: 16px; padding: 12px; background: var(--panel-soft); border-radius: 8px; border: 1px solid var(--line);">
            <h3 style="margin-top: 0; font-size: 1rem;">Add Pipeline</h3>
            <form method="POST" action="{MONITOR_ADMIN_PATH}/pipelines" class="grid-3" style="align-items: end;">
                <div class="filter-field">
                    <label class="eyebrow">Name</label>
                    <input type="text" name="name" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Table</label>
                    <input type="text" name="table" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Partition Column</label>
                    <input type="text" name="partition_column" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Strategy</label>
                    <select name="strategy" onchange="toggleIncrementalField(this, 'new-pipeline')" style="padding:8px; border:1px solid var(--line); border-radius:6px;">
                        <option value="full" selected>full</option>
                        <option value="incremental">incremental</option>
                    </select>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Schedule</label>
                    <input type="text" name="schedule" value="0 2 * * *" required style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field">
                    <label class="eyebrow">Chunk Size</label>
                    <input type="number" name="chunk_size" min="1" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div class="filter-field" style="grid-column: span 2;">
                    <label class="eyebrow">Columns</label>
                    <textarea name="columns" rows="2" placeholder="COL1, COL2, COL3" style="padding:8px; border:1px solid var(--line); border-radius:6px; width:100%;"></textarea>
                </div>
                <div class="filter-field incremental-key-field" data-prefix="new-pipeline" style="display:none;">
                    <label class="eyebrow">Incremental Key</label>
                    <input type="text" name="incremental_key" style="padding:8px; border:1px solid var(--line); border-radius:6px;"/>
                </div>
                <div style="grid-column: span 3; text-align: right;">
                    <button type="submit" class="primary">Add Pipeline</button>
                </div>
            </form>
        </div>
    </section>
    """

    script_html = """
    <script>
    function togglePipelineEdit(rowId) {
        const row = document.getElementById(rowId);
        if (!row) return;
        row.style.display = row.style.display === "none" ? "table-row" : "none";
    }

    function toggleIncrementalField(selectEl, prefix) {
        const section = document.querySelector('.incremental-key-field[data-prefix="' + prefix + '"]');
        if (!section) return;
        section.style.display = selectEl.value === "incremental" ? "block" : "none";
        if (selectEl.value !== "incremental") {
            const input = section.querySelector('input[name="incremental_key"]');
            if (input) input.value = "";
        }
    }
    </script>
    """

    content_html = f"{conn_html}<br>{var_html}<br>{pool_html}<br>{pipelines_html}{script_html}"

    return render_layout(
        title=t(language, "webui.layout.nav.admin"),
        subtitle="Manage connections, variables, pools, and pipelines.",
        active_path=MONITOR_ADMIN_PATH,
        content_html=content_html,
        language=language,
    )
