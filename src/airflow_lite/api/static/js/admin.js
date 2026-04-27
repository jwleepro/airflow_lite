var AdminPage = (function() {
  function init() {
    AirflowTabs.init();
  }

  function filterTable(inputId, tableId) {
    var input = document.getElementById(inputId);
    var filter = input.value.toLowerCase();
    var table = document.getElementById(tableId);
    var tr = table.getElementsByTagName('tr');
    for (var i = 1; i < tr.length; i++) {
      var tds = tr[i].getElementsByTagName('td');
      var matched = false;
      for (var j = 0; j < tds.length && !matched; j++) {
        var txtValue = tds[j].textContent || tds[j].innerText;
        if (txtValue.toLowerCase().indexOf(filter) > -1) {
          matched = true;
        }
      }
      tr[i].style.display = matched ? '' : 'none';
    }
  }

  function filterConnectionsTable() {
    filterTable('conn-search', 'conn-table');
  }

  function filterVariablesTable() {
    filterTable('var-search', 'var-table');
  }

  function toggleSection(btn) {
    var body = btn.nextElementSibling;
    body.classList.toggle('collapsed');
    var span = btn.querySelector('span');
    if (span) {
      var label = span.textContent.replace(/\s*[\u25b8\u25be]\s*$/, '');
      span.textContent = label + (body.classList.contains('collapsed') ? ' \u25b8' : ' \u25be');
    }
  }

  function onEditXcom(btn) {
    var dagId = btn.dataset.dagId || '-';
    var taskId = btn.dataset.taskId || '-';
    var key = btn.dataset.key || '-';
    window.alert('Edit XCom is not implemented yet. (' + dagId + ' / ' + taskId + ' / ' + key + ')');
  }

  function onDeleteXcom(btn) {
    var dagId = btn.dataset.dagId || '-';
    var taskId = btn.dataset.taskId || '-';
    var key = btn.dataset.key || '-';
    window.alert('Delete XCom is not implemented yet. (' + dagId + ' / ' + taskId + ' / ' + key + ')');
  }

  return {
    init: init,
    filterTable: filterTable,
    filterConnectionsTable: filterConnectionsTable,
    filterVariablesTable: filterVariablesTable,
    toggleSection: toggleSection,
    onEditXcom: onEditXcom,
    onDeleteXcom: onDeleteXcom
  };
})();

window.filterTable = function() { AdminPage.filterConnectionsTable(); };
window.toggleSection = function(btn) { AdminPage.toggleSection(btn); };
window.onEditXcom = function(btn) { AdminPage.onEditXcom(btn); };
window.onDeleteXcom = function(btn) { AdminPage.onDeleteXcom(btn); };
