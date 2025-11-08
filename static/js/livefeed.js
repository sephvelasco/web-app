// static/js/livefeed.js

const liveFeedTab = document.getElementById("liveFeedTab");

liveFeedTab.addEventListener("click", () => {
  // 1. Manage Active Tabs
  document
    .querySelectorAll(".nav-tab")
    .forEach((li) => li.classList.remove("active"));
  liveFeedTab.classList.add("active");

  // 2. Toggle View Visibility
  document.getElementById("dashboardView").style.display = "none";
  document.getElementById("historyView").style.display = "none";

  // Show the live feed view
  const liveFeedView = document.getElementById("liveFeedView");
  liveFeedView.style.display = "block";

  // Update status message
  document.getElementById("liveFeedStatus").textContent = "Streaming...";

  // Note: The live feed image's src="/video_feed" automatically handles the stream
});

const toggleDetectionBtn = document.getElementById("toggleDetectionBtn");

if (toggleDetectionBtn) {
  toggleDetectionBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/toggle_detection", { method: "POST" });
      const data = await res.json();

      if (data.detection_enabled) {
        toggleDetectionBtn.textContent = "Stop Detection";
        toggleDetectionBtn.style.backgroundColor = "#a52a2a";
      } else {
        toggleDetectionBtn.textContent = "Start Detection";
        toggleDetectionBtn.style.backgroundColor = "#191970";
      }
    } catch (err) {
      console.error("Error toggling detection:", err);
    }
  });
}
