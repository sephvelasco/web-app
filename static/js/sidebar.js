// static/js/sidebar.js

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("sidebarToggle");
  const dashboardTab = document.getElementById("dashboardTab");

  // The initial HTML already sets it to 'collapsed', so we just add the listener

  toggleBtn.addEventListener("click", () => {
    const isCollapsed = sidebar.classList.contains("collapsed");

    if (isCollapsed) {
      sidebar.classList.remove("collapsed");
      toggleBtn.classList.add("open");
    } else {
      sidebar.classList.add("collapsed");
      toggleBtn.classList.remove("open");
    }

    // Dispatch a custom event to notify other components (e.g., Three.js viewer)
    // that the sidebar has toggled and a resize might be necessary.
    window.dispatchEvent(new Event("sidebarToggled"));
  });

  // Since the original HTML relied on a full reload to restore the dashboard,
  // we'll explicitly add the logic here to restore the dashboard view's visibility.
  dashboardTab.addEventListener("click", () => {
    // Manage Active Tabs
    document
      .querySelectorAll(".nav-tab")
      .forEach((li) => li.classList.remove("active"));
    dashboardTab.classList.add("active");

    // Toggle View Visibility back to the dashboard
    document.getElementById("historyView").style.display = "none";
    document.getElementById("liveFeedView").style.display = "none";
    document.getElementById("dashboardView").style.display = "block";
  });

  // Force reflow fix to eliminate gap when returning to Dashboard
  document.getElementById("dashboardTab").addEventListener("click", () => {
    const dashboardView = document.getElementById("dashboardView");
    const viewerArea = dashboardView.querySelector(".viewer-area");

    if (viewerArea) {
      // Wait for browser to finish showing the dashboard
      requestAnimationFrame(() => {
        // Trigger a flexbox recalculation and resize
        viewerArea.style.minHeight = "0";
        viewerArea.getBoundingClientRect(); // force reflow
        viewerArea.style.minHeight = "auto";

        // Notify Three.js renderer or other layout-dependent scripts
        window.dispatchEvent(new Event("resize"));
      });
    }
  });
});
