document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("sidebarToggle");

  const dashboardTab = document.getElementById("dashboardTab");
  const historyTab = document.getElementById("historyTab");
  const motorTab = document.getElementById("motorTab");
  const liveFeedTab = document.getElementById("liveFeedTab"); // optional if present

  const dashboardView = document.getElementById("dashboardView");
  const historyView = document.getElementById("historyView");
  const motorView = document.getElementById("motorView");
  const liveFeedView = document.getElementById("liveFeedView");

  function setActiveTab(tabEl) {
    document.querySelectorAll(".nav-tab").forEach((li) => li.classList.remove("active"));
    if (tabEl) tabEl.classList.add("active");
  }

  function showOnly(viewEl) {
    if (dashboardView) dashboardView.style.display = "none";
    if (historyView) historyView.style.display = "none";
    if (liveFeedView) liveFeedView.style.display = "none";
    if (motorView) motorView.style.display = "none";
    if (viewEl) viewEl.style.display = "block";
  }

  if (toggleBtn) {
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
  }

  if (dashboardTab) {
    dashboardTab.addEventListener("click", () => {
      setActiveTab(dashboardTab);
      showOnly(dashboardView);

      // Force reflow fix to eliminate gap when returning to Dashboard
      const viewerArea = dashboardView?.querySelector(".viewer-area");
      if (viewerArea) {
        requestAnimationFrame(() => {
          viewerArea.style.minHeight = "0";
          viewerArea.getBoundingClientRect();
          viewerArea.style.minHeight = "auto";
          window.dispatchEvent(new Event("resize"));
        });
      }
    });
  }

  if (historyTab) {
    historyTab.addEventListener("click", () => {
      setActiveTab(historyTab);
      showOnly(historyView);
      window.dispatchEvent(new Event("historyViewShown"));
    });
  }

  // Optional support if you add a live feed nav tab later

  if (motorTab) {
    motorTab.addEventListener("click", () => {
      setActiveTab(motorTab);
      showOnly(motorView);
    });
  }

  if (liveFeedTab) {
    liveFeedTab.addEventListener("click", () => {
      setActiveTab(liveFeedTab);
      showOnly(liveFeedView);
    });
  }
});
