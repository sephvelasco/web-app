// static/js/history.js

const historyTab = document.getElementById("historyTab");
const mainContent = document.getElementById("mainContent");
const dashboardTab = document.getElementById("dashboardTab");

// --- History View Logic ---

historyTab.addEventListener("click", async () => {
    // 1. Manage Active Tabs (handled by a simpler routing function in a real app, 
    // but doing it manually here)
    document.querySelectorAll(".nav-tab").forEach(li => li.classList.remove("active"));
    historyTab.classList.add("active");
    
    // Hide other views (assuming a single-page app structure)
    document.getElementById("dashboardView").style.display = 'none';
    document.getElementById("liveFeedView").style.display = 'none';
    
    // 2. Load the History View content
    const historyView = document.getElementById("historyView");
    historyView.style.display = 'block';
    historyView.innerHTML = '<h2>Upload History</h2><div class="history-grid">Loading history...</div>';
    
    const grid = historyView.querySelector(".history-grid");

    try {
        const res = await fetch("/history");
        const images = await res.json();

        if (images.length === 0) {
            grid.innerHTML = "<p>No uploaded images found.</p>";
            return;
        }

        grid.innerHTML = ""; // Clear 'Loading' message

        images.forEach((img) => {
            const div = document.createElement("div");
            div.className = "history-item";
            
            // Format detections list
            const detectionsHtml = img.detections
                .map(
                    (det) => `
                        <p>${det.crack_type} (${det.confidence}%)</p>
                    `
                )
                .join("");
                
            div.innerHTML = `
                <img src="${img.image_url}" alt="${img.filename}">
                <p><b>${img.filename}</b></p>
                <p><small>${img.timestamp}</small></p>
                ${detectionsHtml}
            `;
            grid.appendChild(div);
        });
    } catch (error) {
        console.error("Failed to fetch history:", error);
        grid.innerHTML = "<p>Error loading history data.</p>";
    }
});

// --- Image Preview Logic (re-using existing overlay) ---

// Double-click to open preview
document.addEventListener('dblclick', function(e) {
    const item = e.target.closest('.history-item img');
    if (item) {
        const src = item.src;
        // Filename is the text content of the next sibling <p>
        const filename = item.nextElementSibling.textContent;

        const overlay = document.getElementById('imagePreviewOverlay');
        const previewImg = document.getElementById('previewImage');
        const previewName = document.getElementById('previewFilename');

        previewImg.src = src;
        previewName.textContent = filename;
        overlay.style.display = 'flex';
    }
});

// Close Preview: 'x' button
document.getElementById('closePreview').addEventListener('click', () => {
    document.getElementById('imagePreviewOverlay').style.display = 'none';
});

// Close Preview: click outside image
document.getElementById('imagePreviewOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'imagePreviewOverlay') {
        e.currentTarget.style.display = 'none';
    }
});