var PipelineDetail = (function() {
  var currentZoom = 1;
  var dagId = '';

  function init(pipelineName) {
    dagId = pipelineName || '';
    AirflowTabs.init();
    initTaskPanelTabs();
  }

  function zoomGraph(delta) {
    currentZoom = Math.max(0.3, Math.min(2, currentZoom + delta));
    var g = document.getElementById('dag-graph-group');
    if (g) g.style.transform = 'scale(' + currentZoom + ')';
    var zoomLabel = document.getElementById('zoom-level');
    if (zoomLabel) zoomLabel.textContent = Math.round(currentZoom * 100) + '%';
  }

  function resetZoom() {
    currentZoom = 1;
    var g = document.getElementById('dag-graph-group');
    if (g) g.style.transform = 'scale(1)';
    var zoomLabel = document.getElementById('zoom-level');
    if (zoomLabel) zoomLabel.textContent = '100%';
  }

  function selectNode(el) {
    var name = el.dataset.node;
    var rawStatus = el.dataset.status || 'queued';
    var duration = el.dataset.duration || '-';
    var statusMap = { ok: 'success', warn: 'running', bad: 'failed', neutral: 'queued' };
    var toneMap = { success: 'ok', completed: 'ok', running: 'warn', pending: 'warn', queued: 'neutral', failed: 'bad' };
    var tone = toneMap[rawStatus] || rawStatus;
    var normalizedStatus = statusMap[tone] || rawStatus;
    var panel = document.getElementById('node-panel');
    document.getElementById('panel-task-name').textContent = name;
    document.getElementById('panel-status').innerHTML = '<span class="status ' + tone + '">' + normalizedStatus + '</span>';
    document.getElementById('panel-duration').textContent = duration;
    panel.hidden = false;
  }

  function showTaskPanel(cell) {
    var panel = document.getElementById('task-panel');
    var taskName = cell.dataset.task || '';
    var runId = cell.dataset.runId || '';
    var rawStatus = cell.dataset.status || 'queued';
    var duration = cell.dataset.duration || '-';
    var statusMap = { ok: 'success', warn: 'running', bad: 'failed', neutral: 'queued' };
    var toneMap = { success: 'ok', completed: 'ok', running: 'warn', pending: 'warn', queued: 'neutral', failed: 'bad' };
    var tone = toneMap[rawStatus] || rawStatus;

    document.getElementById('task-panel-name').textContent = taskName;
    document.getElementById('task-panel-run').textContent = cell.dataset.run || '';
    document.getElementById('task-panel-status').innerHTML = '<span class="status ' + tone + '">' + (statusMap[tone] || rawStatus) + '</span>';
    document.getElementById('task-panel-duration').textContent = duration;

    var logsLink = document.getElementById('task-panel-logs-link');
    var logsLink2 = document.getElementById('task-panel-logs-link-2');
    var logsNa = document.getElementById('task-panel-logs-na');
    if (runId) {
      var basePath = '/monitor/pipelines/' + encodeURIComponent(dagId) + '/runs/' + encodeURIComponent(runId);
      var langParam = new URLSearchParams(window.location.search).get('lang');
      var href = langParam ? (basePath + '?lang=' + encodeURIComponent(langParam)) : basePath;
      logsLink.href = href;
      logsLink.hidden = false;
      logsLink2.href = href;
      logsLink2.hidden = false;
      if (logsNa) logsNa.hidden = true;
    } else {
      logsLink.hidden = true;
      logsLink2.hidden = true;
      if (logsNa) logsNa.hidden = false;
    }

    switchPanelTab('details');
    panel.hidden = false;
  }

  function switchPanelTab(tabName) {
    var paneIds = ['task-pane-details', 'task-pane-logs', 'task-pane-xcom'];
    var tabMap = { details: 'task-pane-details', logs: 'task-pane-logs', xcom: 'task-pane-xcom' };
    paneIds.forEach(function(id) {
      var el = document.getElementById(id);
      if (el) el.hidden = (id !== tabMap[tabName]);
    });
    document.querySelectorAll('[data-panel-tab]').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.panelTab === tabName);
    });
  }

  function initTaskPanelTabs() {
    var tabs = document.querySelectorAll('[data-panel-tab]');
    tabs.forEach(function(btn) {
      btn.addEventListener('click', function() {
        switchPanelTab(btn.dataset.panelTab);
      });
    });
  }

  function closeNodePanel() {
    var panel = document.getElementById('node-panel');
    if (panel) panel.hidden = true;
  }

  function closeTaskPanel() {
    var panel = document.getElementById('task-panel');
    if (panel) panel.hidden = true;
  }

  return {
    init: init,
    zoomGraph: zoomGraph,
    resetZoom: resetZoom,
    selectNode: selectNode,
    showTaskPanel: showTaskPanel,
    closeNodePanel: closeNodePanel,
    closeTaskPanel: closeTaskPanel
  };
})();

window.zoomGraph = function(delta) { PipelineDetail.zoomGraph(delta); };
window.resetZoom = function() { PipelineDetail.resetZoom(); };
window.selectNode = function(el) { PipelineDetail.selectNode(el); };
window.showTaskPanel = function(cell) { PipelineDetail.showTaskPanel(cell); };
