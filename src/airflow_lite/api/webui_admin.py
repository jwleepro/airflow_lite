from html import escape
from airflow_lite.api.paths import MONITOR_ADMIN_PATH
from airflow_lite.api.webui_helpers import render_layout, t, fmt

def render_admin_page(
    connections: list,
    variables: list,
    pools: list,
    *,
    language: str,
) -> str:
    # --- Connections ---
    conn_rows = ""
    for c in connections:
        conn_rows += f"""<tr>
            <td>{fmt(c.conn_id)}</td>
            <td>{fmt(c.conn_type)}</td>
            <td>{fmt(c.host)}</td>
            <td>{fmt(c.port)}</td>
            <td>{fmt(c.schema)}</td>
            <td>{fmt(c.login)}</td>
            <td>********</td>
            <td>{fmt(c.description)}</td>
            <td style="text-align: right;">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/connections/delete" style="display:inline;" onsubmit="return confirm('Delete connection?');">
                    <input type="hidden" name="conn_id" value="{escape(c.conn_id)}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>"""
    if not conn_rows:
        conn_rows = f'<tr><td colspan="9" class="empty">No connections found.</td></tr>'
        
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
    for v in variables:
        var_rows += f"""<tr>
            <td>{fmt(v.key)}</td>
            <td>{fmt(v.val)}</td>
            <td>{fmt(v.description)}</td>
            <td style="text-align: right;">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/variables/delete" style="display:inline;" onsubmit="return confirm('Delete variable?');">
                    <input type="hidden" name="key" value="{escape(v.key)}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>"""
    if not var_rows:
        var_rows = f'<tr><td colspan="4" class="empty">No variables found.</td></tr>'
        
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
    for p in pools:
        pool_rows += f"""<tr>
            <td>{fmt(p.pool_name)}</td>
            <td>{fmt(p.slots)}</td>
            <td>{fmt(p.description)}</td>
            <td style="text-align: right;">
                <form method="POST" action="{MONITOR_ADMIN_PATH}/pools/delete" style="display:inline;" onsubmit="return confirm('Delete pool?');">
                    <input type="hidden" name="pool_name" value="{escape(p.pool_name)}" />
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </td>
        </tr>"""
    if not pool_rows:
        pool_rows = f'<tr><td colspan="4" class="empty">No pools found.</td></tr>'
        
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

    content_html = f"{conn_html}<br>{var_html}<br>{pool_html}"

    return render_layout(
        title=t(language, "webui.layout.nav.admin"),
        subtitle="Manage connections, variables, and pools for pipelines.",
        active_path=MONITOR_ADMIN_PATH,
        content_html=content_html,
        language=language,
    )
