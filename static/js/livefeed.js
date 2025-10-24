// static/js/livefeed.js

const liveFeedTab = document.getElementById("liveFeedTab");

liveFeedTab.addEventListener("click", () => {
    // 1. Manage Active Tabs
    document.querySelectorAll(".nav-tab").forEach(li => li.classList.remove("active"));
    liveFeedTab.classList.add("active");

    // 2. Toggle View Visibility
    document.getElementById("dashboardView").style.display = 'none';
    document.getElementById("historyView").style.display = 'none';
    
    // Show the live feed view
    const liveFeedView = document.getElementById("liveFeedView");
    liveFeedView.style.display = 'block';

    // Update status message
    document.getElementById("liveFeedStatus").textContent = "Streaming...";
    
    // Note: The live feed image's src="/video_feed" automatically handles the stream
});