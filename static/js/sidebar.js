document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("sidebarToggle");
  const dashboardTab = document.getElementById("dashboardTab");

  toggleBtn.addEventListener("click", () => {
    const isCollapsed = sidebar.classList.contains("collapsed");

    if (isCollapsed) {
      sidebar.classList.remove("collapsed");
      toggleBtn.classList.add("open");
    } else {
      sidebar.classList.add("collapsed");
      toggleBtn.classList.remove("open");
    }

    window.dispatchEvent(new Event("sidebarToggled"));
  });

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
        viewerArea.style.minHeight = "0";
        viewerArea.getBoundingClientRect();
        viewerArea.style.minHeight = "auto";

        window.dispatchEvent(new Event("resize"));
      });
    }
  });
});
