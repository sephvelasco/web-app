const cameraTab = document.getElementById("cameraTab");
const modelTab = document.getElementById("modelTab");
const imageTab = document.getElementById("imageTab");

const cameraContainer = document.getElementById("cameraContainer");
const imageContainer = document.getElementById("imageContainer");
const viewerCanvas = document.getElementById("viewer");

const liveStreamImg = document.getElementById("liveStream");
const captureBtn = document.getElementById("captureBtn");

const uploadBtn = document.getElementById("uploadBtn");
const imageInput = document.getElementById("imageInput");
const uploadedImage = document.getElementById("uploadedImage");

const detectionsList = document.getElementById("detectionsList");
const statusBox = document.getElementById("status");
const recommendationBox = document.getElementById("recommendation");
const timestampBox = document.getElementById("timestamp");

// Default to Camera tab on load
showOnly("camera");

let livePollingHandle = null;
const POLL_INTERVAL = 1000;

// --- Tab Handlers ---
cameraTab.addEventListener("click", () => {
  setActiveTab(cameraTab);
  showOnly("camera");
  startLivePolling();
  // Pause 3D rendering if needed
  window.dispatchEvent(new CustomEvent("pause3DRender", { detail: true }));
});

modelTab.addEventListener("click", () => {
  setActiveTab(modelTab);
  showOnly("model");
  stopLivePolling();
  // Resume 3D rendering
  window.dispatchEvent(new CustomEvent("pause3DRender", { detail: false }));
  // Force resize to ensure canvas fits
  window.dispatchEvent(new Event("resize"));
});

imageTab.addEventListener("click", () => {
  setActiveTab(imageTab);
  showOnly("image");
  stopLivePolling();
  window.dispatchEvent(new CustomEvent("pause3DRender", { detail: true }));
});

// helper: set active tab visual
function setActiveTab(tabEl) {
  document
    .querySelectorAll(".tab-btn")
    .forEach((el) => el.classList.remove("active"));
  tabEl.classList.add("active");
}

// helper: shows only camera/model/image
function showOnly(which) {
  if (which === "camera") {
    cameraContainer.style.display = "flex";
    imageContainer.style.display = "none";
    viewerCanvas.style.display = "none";
    liveStreamImg.style.display = "block";
  } else if (which === "model") {
    cameraContainer.style.display = "none";
    imageContainer.style.display = "none";
    viewerCanvas.style.display = "block";
    // ensure 3D viewer gets resized
    setTimeout(() => window.dispatchEvent(new Event("resize")), 100);
  } else {
    // image
    cameraContainer.style.display = "none";
    imageContainer.style.display = "flex";
    viewerCanvas.style.display = "none";
  }
}

// --- Live polling ---
async function pollLiveStatus() {
  try {
    const res = await fetch("/live_status");
    if (!res.ok) return;
    const data = await res.json();
    // update detections list
    detectionsList.innerHTML = "";
    data.detections.forEach((det) => {
      const li = document.createElement("li");
      li.textContent = `${det.name} (${(det.confidence * 100).toFixed(1)}%)`;
      detectionsList.appendChild(li);
    });
    // update info boxes
    statusBox.textContent = data.status || "--";
    recommendationBox.textContent = data.recommendation || "--";
    timestampBox.textContent = data.timestamp || "--";
  } catch (err) {
    console.error("pollLiveStatus error", err);
  }
}

function startLivePolling() {
  if (livePollingHandle) return;
  // immediate poll + interval
  pollLiveStatus();
  livePollingHandle = setInterval(pollLiveStatus, POLL_INTERVAL);
}

function stopLivePolling() {
  if (!livePollingHandle) return;
  clearInterval(livePollingHandle);
  livePollingHandle = null;
}

// start on load (camera tab default)
startLivePolling();

// --- Capture button ---
captureBtn.addEventListener("click", async () => {
  captureBtn.disabled = true;
  captureBtn.textContent = "Capturing...";
  try {
    const res = await fetch("/capture", { method: "POST" });
    const data = await res.json();
    if (data.saved) {
      // Switch to Image tab and display captured image
      setActiveTab(imageTab);
      showOnly("image");
      uploadedImage.src = data.image_url;
      uploadedImage.style.display = "block";
      document.querySelector(".drop-text").style.display = "none";

      // Also update detections list and info boxes from capture result
      detectionsList.innerHTML = "";
      (data.detections || []).forEach((det) => {
        const li = document.createElement("li");
        li.textContent = `${det.name} (${(det.confidence * 100).toFixed(1)}%)`;
        detectionsList.appendChild(li);
      });
      statusBox.textContent = data.recommendation ? data.recommendation : "--";
    } else {
      // Not saved (no defects)
      alert(data.message || "No defects detected; not saved.");
    }
  } catch (err) {
    console.error("Capture error", err);
    alert("Capture failed.");
  } finally {
    captureBtn.disabled = false;
    captureBtn.textContent = "Capture";
  }
});

// --- Upload button (existing logic) ---
uploadBtn.addEventListener("click", () => imageInput.click());
imageInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    const file = e.target.files[0];
    // reuse your existing upload flow (post to /upload)
    const formData = new FormData();
    formData.append("file", file);
    fetch("/upload", { method: "POST", body: formData })
      .then((r) => r.json())
      .then((data) => {
        uploadedImage.src = data.image_url;
        uploadedImage.style.display = "block";
        document.querySelector(".drop-text").style.display = "none";
        // update detections & info
        detectionsList.innerHTML = "";
        (data.detections || []).forEach((det) => {
          const li = document.createElement("li");
          li.textContent = `${det.name || det.class || det.type} (${(
            det.confidence * 100
          ).toFixed(1)}%)`;
          detectionsList.appendChild(li);
        });
        statusBox.textContent = data.status || "--";
        recommendationBox.textContent = data.recommendation || "--";
        timestampBox.textContent = data.timestamp || "--";
      })
      .catch((err) => {
        console.error("Upload failed", err);
        alert("Upload failed.");
      });
  }
});
