// Dashboard logic: camera/model tabs, live status polling, and scan automation

const cameraTab = document.getElementById("cameraTab");
const modelTab = document.getElementById("modelTab");

const cameraContainer = document.getElementById("cameraContainer");
const viewerCanvas = document.getElementById("viewer");

const detectionsList = document.getElementById("detectionsList");
const bogieStatusEl = document.getElementById("bogieStatus");
const recommendationBox = document.getElementById("recommendation");
const timestampBox = document.getElementById("timestamp");

const scanBtn = document.getElementById("scanBtn");
const scanStopBtn = document.getElementById("scanStopBtn");

// Default to Camera tab
showOnly("camera");

let livePollingHandle = null;
const POLL_INTERVAL_MS = 1000;

// --- Tab handlers ---
cameraTab?.addEventListener("click", () => {
  setActiveTopTab(cameraTab);
  showOnly("camera");
  startLivePolling();
  window.dispatchEvent(new CustomEvent("pause3DRender", { detail: true }));
});

modelTab?.addEventListener("click", () => {
  setActiveTopTab(modelTab);
  showOnly("model");
  stopLivePolling();
  window.dispatchEvent(new CustomEvent("pause3DRender", { detail: false }));
  // Ensure canvas fits
  setTimeout(() => window.dispatchEvent(new Event("resize")), 100);
});

function setActiveTopTab(tabEl) {
  document.querySelectorAll(".tab-btn").forEach((el) => el.classList.remove("active"));
  tabEl?.classList.add("active");
}

function showOnly(which) {
  if (which === "camera") {
    cameraContainer.style.display = "flex";
    viewerCanvas.style.display = "none";
  } else if (which === "model") {
    cameraContainer.style.display = "none";
    viewerCanvas.style.display = "block";
    setTimeout(() => window.dispatchEvent(new Event("resize")), 50);
  }
}

// --- Live polling ---
async function pollLiveStatus() {
  try {
    const res = await fetch("/live_status");
    if (!res.ok) return;
    const data = await res.json();

    // detections
    if (detectionsList) {
      detectionsList.innerHTML = "";
      (data.detections || []).forEach((det) => {
        const li = document.createElement("li");
        li.textContent = `${det.name} (${(det.confidence * 100).toFixed(1)}%)`;
        detectionsList.appendChild(li);
      });
    }

    // bogie info
    if (bogieStatusEl) bogieStatusEl.textContent = data.status || "--";
    if (recommendationBox) recommendationBox.textContent = data.recommendation || "--";
    if (timestampBox) timestampBox.textContent = data.timestamp || "--";
  } catch (err) {
    console.error("pollLiveStatus error", err);
  }
}

function startLivePolling() {
  if (livePollingHandle) return;
  pollLiveStatus();
  livePollingHandle = setInterval(pollLiveStatus, POLL_INTERVAL_MS);
}

function stopLivePolling() {
  if (!livePollingHandle) return;
  clearInterval(livePollingHandle);
  livePollingHandle = null;
}

// start on load
startLivePolling();

// --- Scan automation ---
scanBtn?.addEventListener("click", async () => {
  if (!scanBtn) return;
  scanBtn.disabled = true;
  const oldText = scanBtn.textContent;
  scanBtn.textContent = "Scanning...";
  try {
    const res = await fetch("/scan/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ distance_mm: 950.0, return_home: true }),
    });
    const out = await res.json();
    if (!out.ok) {
      alert(out.error || "Failed to start scan");
      scanBtn.disabled = false;
      scanBtn.textContent = oldText;
    }
  } catch (e) {
    alert(String(e));
    scanBtn.disabled = false;
    scanBtn.textContent = oldText;
  }
});

scanStopBtn?.addEventListener("click", async () => {
  try {
    await fetch("/scan/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  } catch (e) {}
});

async function pollScanStatus() {
  const scanEl = document.getElementById("scanStatus");
  if (!scanEl) return;
  try {
    const res = await fetch("/scan/status");
    if (!res.ok) return;
    const out = await res.json();
    if (!out.ok) return;
    const st = out.state || {};
    const motor = out.motor || {};
    const pct = st.progress != null ? Math.round(st.progress * 100) : 0;
    scanEl.textContent =
      `running=${!!st.running} phase=${st.phase || "idle"} progress=${pct}%\n` +
      `msg=${st.message || ""}\n` +
      `x_mm=${(motor.posMm ?? 0).toFixed ? motor.posMm.toFixed(2) : motor.posMm} moving=${!!motor.moving}`;

    if (!st.running && scanBtn) {
      scanBtn.disabled = false;
      scanBtn.textContent = "Scan";
    }
  } catch (e) {}
}

setInterval(pollScanStatus, 500);
pollScanStatus();
