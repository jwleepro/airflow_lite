var AirflowSearch = (function() {
  var overlay, input, results, routes;

  function init(routeData) {
    overlay = document.getElementById("global-search-overlay");
    input = document.getElementById("search-input");
    results = document.getElementById("search-results");
    routes = routeData || [];

    if (!overlay || !input || !results) return;

    document.addEventListener("keydown", function(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (overlay.hidden) {
          openSearch();
        } else {
          closeSearch();
        }
      }
      if (event.key === "Escape") {
        closeSearch();
      }
    });

    var searchBtn = document.getElementById("global-search-btn");
    if (searchBtn) {
      searchBtn.addEventListener("click", openSearch);
    }

    overlay.addEventListener("click", function(event) {
      if (event.target === overlay) {
        closeSearch();
      }
    });

    input.addEventListener("input", function() {
      renderResults(input.value);
    });
  }

  function renderResults(query) {
    var q = query.toLowerCase().trim();
    var filtered = routes.filter(function(route) {
      return !q || route.label.toLowerCase().includes(q) || route.section.toLowerCase().includes(q);
    });
    if (!filtered.length) {
      results.innerHTML = '<p class="search-placeholder-text">No results found</p>';
      return;
    }

    var html = "";
    var lastSection = "";
    filtered.forEach(function(route) {
      if (route.section !== lastSection) {
        html += '<div class="search-section-label">' + route.section + '</div>';
        lastSection = route.section;
      }
      html += '<a class="search-result-item" href="' + route.path + '">' + route.label + '</a>';
    });
    results.innerHTML = html;
  }

  function openSearch() {
    overlay.hidden = false;
    input.value = "";
    renderResults("");
    input.focus();
  }

  function closeSearch() {
    overlay.hidden = true;
    input.value = "";
  }

  return { init: init };
})();
