// static/js/dashboard.js

// DOM Elements
const imageTab = document.getElementById("imageTab");
const modelTab = document.getElementById("modelTab");
const imageContainer = document.getElementById("imageContainer");
const viewerCanvas = document.getElementById("viewer");
const uploadBtn = document.getElementById("uploadBtn");
const imageInput = document.getElementById("imageInput");

// Initialize state: start on Image view
viewerCanvas.style.display = "none";
imageContainer.style.display = "flex";

/**
 * Handles the logic for uploading a file to the backend.
 * @param {File} file - The image file to upload.
 */
async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        const res = await fetch("/upload", { method: "POST", body: formData });
        const data = await res.json();

        // Update Image View
        document.querySelector(".drop-text").style.display = "none";
        const img = document.getElementById("uploadedImage");
        img.src = data.image_url;
        img.style.display = "block";

        // Update Detections List
        const list = document.getElementById("detectionsList");
        list.innerHTML = "";
        data.detections.forEach((det) => {
            const li = document.createElement("li");
            // Use fallback properties for robustness
            const crackType = det.class || det.type || det.name || "unknown";
            li.textContent = `${crackType} (${(det.confidence * 100).toFixed(1)}%)`;
            list.appendChild(li);
        });

        // Update Info Boxes
        document.getElementById("status").textContent = data.status || "--";
        document.getElementById("recommendation").textContent = data.recommendation || "--";
        document.getElementById("timestamp").textContent = data.timestamp || "--";

    } catch (error) {
        console.error("Upload failed:", error);
        alert("Image upload and analysis failed.");
    }
}

// --- Event Listeners ---

// File Upload
uploadBtn.addEventListener("click", () => imageInput.click());
imageInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
});

// Drag and Drop
imageContainer.addEventListener("dragover", (e) => {
    e.preventDefault();
    imageContainer.classList.add('drag-over');
});
imageContainer.addEventListener("dragleave", () => {
    imageContainer.classList.remove('drag-over');
});
imageContainer.addEventListener("drop", (e) => {
    e.preventDefault();
    imageContainer.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        uploadFile(e.dataTransfer.files[0]);
    }
});

// Tab Switching: Image View
imageTab.addEventListener("click", () => {
    imageTab.classList.add("active");
    modelTab.classList.remove("active");
    imageContainer.style.display = "flex";
    viewerCanvas.style.display = "none";
    // Pause the 3D render loop
    window.dispatchEvent(
        new CustomEvent("pause3DRender", { detail: true })
    );
});

// Tab Switching: 3D Model View
modelTab.addEventListener("click", () => {
    modelTab.classList.add("active");
    imageTab.classList.remove("active");
    imageContainer.style.display = "none";
    viewerCanvas.style.display = "block";
    // Resume the 3D render loop
    window.dispatchEvent(
        new CustomEvent("pause3DRender", { detail: false })
    );
    // Force a resize to ensure 3D viewer uses full space after display change
    window.dispatchEvent(new Event('resize')); 
});