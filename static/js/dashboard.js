const cameraTab = document.getElementById("cameraTab");
const modelTab = document.getElementById("modelTab");

const cameraContainer = document.getElementById("cameraContainer");
const viewerCanvas = document.getElementById("viewer");

const liveStreamImg = document.getElementById("liveStream");
const captureBtn = document.getElementById("captureBtn");

// Upload/Image tab removed (live camera feeds are the validation source)

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
    viewerCanvas.style.display = "none";
    liveStreamImg.style.display = "block";
  } else if (which === "model") {
    cameraContainer.style.display = "none";
    viewerCanvas.style.display = "block";
    // ensure 3D viewer gets resized
    setTimeout(() => window.dispatchEvent(new Event("resize")), 100);
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
      // Since History is now auto-saved, capture is just an optional manual save.
      alert("Saved to History.");
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
