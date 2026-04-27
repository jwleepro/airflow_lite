(function() {
  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark";
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("airflow_lite_theme", theme); } catch (e) {}
    document.querySelectorAll("[data-theme-choice]").forEach(function(button) {
      button.classList.toggle("active", button.getAttribute("data-theme-choice") === theme);
    });
  }

  document.querySelectorAll("[data-theme-choice]").forEach(function(button) {
    button.addEventListener("click", function() {
      setTheme(button.getAttribute("data-theme-choice"));
    });
  });
  setTheme(currentTheme());

  var sidebar = document.getElementById("sidebar");
  var sidebarToggle = document.getElementById("sidebar-toggle");
  if (sidebar && sidebarToggle) {
    var collapsed = false;
    try {
      collapsed = localStorage.getItem("airflow_lite_sidebar_collapsed") === "1";
    } catch (e) {}

    function setSidebarCollapsed(value) {
      sidebar.setAttribute("data-collapsed", value ? "true" : "false");
      sidebarToggle.setAttribute("aria-expanded", value ? "false" : "true");
      try { localStorage.setItem("airflow_lite_sidebar_collapsed", value ? "1" : "0"); } catch (e) {}
    }

    setSidebarCollapsed(collapsed);
    sidebarToggle.addEventListener("click", function() {
      setSidebarCollapsed(sidebar.getAttribute("data-collapsed") !== "true");
    });
  }

  document.querySelectorAll("[data-submenu-toggle]").forEach(function(toggle) {
    var name = toggle.getAttribute("data-submenu-toggle");
    var panel = document.querySelector("[data-submenu-panel='" + name + "']");
    if (!panel) {
      return;
    }
    toggle.addEventListener("click", function() {
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      if (expanded) {
        panel.setAttribute("hidden", "");
      } else {
        panel.removeAttribute("hidden");
      }
    });
  });
})();
