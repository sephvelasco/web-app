// Dashboard logic: camera/model tabs, live status polling, and scan automation

const cameraTab = document.getElementById("cameraTab");
const modelTab = document.getElementById("modelTab");

const cameraContainer = document.getElementById("cameraContainer");
const viewerCanvas = document.getElementById("viewer");

const detectionsList = document.getElementById("detectionsList");
const bogieStatusEl = document.getElementById("bogieStatus");
const recommendationBox = document.getElementById("recommendation");
const timestampBox = document.getElementById("timestamp");
const bogieIdEl = document.getElementById("bogieId");
const currentSegmentEl = document.getElementById("currentSegment");
const resetBtn = document.getElementById("resetBtn");

const scanBtn = document.getElementById("scanBtn");
const scanStopBtn = document.getElementById("scanStopBtn");

// Segment modal elements
const segmentModal = document.getElementById('segmentModal');
const segmentModalClose = document.getElementById('segmentModalClose');
const segmentCancelBtn = document.getElementById('segmentCancelBtn');
const segmentStartBtn = document.getElementById('segmentStartBtn');

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

let __bogieId = null;
let __lastSegment = null;

async function loadCurrentBogieId() {
  try {
    const res = await fetch('/bogie/current', { cache: 'no-store' });
    const out = await res.json();
    if (out && out.bogie_id) {
      __bogieId = out.bogie_id;
      if (bogieIdEl) bogieIdEl.textContent = out.bogie_id;
    }
  } catch (e) {}
}
loadCurrentBogieId();

// Reset flow (start a new bogie)
resetBtn?.addEventListener('click', async () => {
  if (!confirm('Start a new bogie? This will return to verification (history stays).')) return;
  try {
    await fetch('/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  } catch (e) {}
  window.location.href = '/';
});

// --- Scan automation ---
function openSegmentModal() {
  if (!segmentModal) return;
  segmentModal.style.display = 'flex';
}
function closeSegmentModal() {
  if (!segmentModal) return;
  segmentModal.style.display = 'none';
}
segmentModalClose?.addEventListener('click', closeSegmentModal);
segmentCancelBtn?.addEventListener('click', closeSegmentModal);
segmentModal?.addEventListener('click', (e) => {
  if (e.target === segmentModal) closeSegmentModal();
});

scanBtn?.addEventListener("click", async () => {
  // Ask which segment is ready
  openSegmentModal();
});

segmentStartBtn?.addEventListener('click', async () => {
  closeSegmentModal();
  if (!scanBtn) return;
  scanBtn.disabled = true;
  const oldText = scanBtn.textContent;
  scanBtn.textContent = 'Scanning...';

  const segInput = document.querySelector('input[name="segmentChoice"]:checked');
  const segment = segInput ? Number(segInput.value) : 1;

  try {
    const res = await fetch('/scan/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ distance_mm: 950.0, return_home: true, segment }),
    });
    const out = await res.json();
    if (!out.ok) {
      alert(out.error || 'Failed to start scan');
      scanBtn.disabled = false;
      scanBtn.textContent = oldText;
      return;
    }
    __lastSegment = segment;
    if (currentSegmentEl) currentSegmentEl.textContent = `Segment ${segment}`;
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

    if (currentSegmentEl && st.segment) {
      currentSegmentEl.textContent = `Segment ${st.segment}`;
    }

    if (!st.running && scanBtn) {
      scanBtn.disabled = false;
      scanBtn.textContent = "Scan";

      // When scan completes, notify the 3D viewer to refresh markers
      if (st.phase === 'done' && __bogieId) {
        window.dispatchEvent(new CustomEvent('mappingUpdated', { detail: { bogie_id: __bogieId } }));
      }
    }
  } catch (e) {}
}

setInterval(pollScanStatus, 500);
pollScanStatus();
