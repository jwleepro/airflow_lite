var TaskLogs = (function() {
  var currentLevel = 'ALL';
  var autoScroll = true;

  function init() {
    if (autoScroll) scrollToBottom();
  }

  function filterByLevel(level) {
    currentLevel = level;
    document.querySelectorAll('.logs-level-btn').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.level === level);
    });
    applyFilters();
  }

  function filterLogs() {
    applyFilters();
  }

  function applyFilters() {
    var search = document.getElementById('logs-search-input').value.toLowerCase();
    var lines = document.querySelectorAll('.log-line');
    var visibleCount = 0;

    lines.forEach(function(line) {
      var level = line.dataset.level;
      var message = line.querySelector('.log-message');
      var text = message.textContent.toLowerCase();

      var levelMatch = currentLevel === 'ALL' || level === currentLevel;
      var searchMatch = !search || text.includes(search);

      if (levelMatch && searchMatch) {
        line.hidden = false;
        visibleCount++;
        if (search) {
          var regex = new RegExp('(' + search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
          message.innerHTML = message.textContent.replace(regex, '<mark class="log-highlight">$1</mark>');
        } else {
          message.innerHTML = message.textContent;
        }
      } else {
        line.hidden = true;
      }
    });

    document.getElementById('logs-count').textContent = visibleCount + ' lines';
  }

  function toggleWrap() {
    var output = document.getElementById('logs-output');
    output.classList.toggle('wrap', document.getElementById('logs-wrap').checked);
  }

  function toggleAutoScroll() {
    autoScroll = document.getElementById('logs-autoscroll').checked;
    if (autoScroll) scrollToBottom();
  }

  function scrollToBottom() {
    var output = document.getElementById('logs-output');
    if (output) output.scrollTop = output.scrollHeight;
  }

  function selectAttempt(num) {
    var url = new URL(window.location.href);
    url.searchParams.set('attempt', num);
    window.location.href = url.toString();
  }

  function toggleFullscreen() {
    var output = document.getElementById('logs-output');
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else if (output) {
      output.requestFullscreen();
    }
  }

  return {
    init: init,
    filterByLevel: filterByLevel,
    filterLogs: filterLogs,
    toggleWrap: toggleWrap,
    toggleAutoScroll: toggleAutoScroll,
    selectAttempt: selectAttempt,
    toggleFullscreen: toggleFullscreen
  };
})();

window.filterByLevel = function(level) { TaskLogs.filterByLevel(level); };
window.filterLogs = function() { TaskLogs.filterLogs(); };
window.toggleWrap = function() { TaskLogs.toggleWrap(); };
window.toggleAutoScroll = function() { TaskLogs.toggleAutoScroll(); };
window.selectAttempt = function(num) { TaskLogs.selectAttempt(num); };
window.toggleFullscreen = function() { TaskLogs.toggleFullscreen(); };
