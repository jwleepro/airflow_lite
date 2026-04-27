(function() {
  try {
    var saved = localStorage.getItem("airflow_lite_theme");
    if (saved === "dark" || saved === "light") {
      document.documentElement.setAttribute("data-theme", saved);
      return;
    }
  } catch (e) {}
  document.documentElement.setAttribute("data-theme", "dark");
})();
