var AirflowTabs = (function() {
  function init(btnSelector, paneSelector) {
    btnSelector = btnSelector || '.dag-tab-btn';
    paneSelector = paneSelector || '.dag-tab-pane';

    var btns = document.querySelectorAll(btnSelector);
    var panes = document.querySelectorAll(paneSelector);

    btns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        btns.forEach(function(b) { b.classList.remove('active'); });
        panes.forEach(function(p) { p.classList.remove('active'); });
        btn.classList.add('active');
        var tabId = 'tab-' + btn.dataset.tab;
        var targetPane = document.getElementById(tabId);
        if (targetPane) {
          targetPane.classList.add('active');
        }
      });
    });
  }

  function initRunDetail() {
    init('.tab-btn', '.tab-pane');
  }

  return { init: init, initRunDetail: initRunDetail };
})();
