// --- History View Logic ---

let __historyCache = [];
let __historyFilter = "All"; // All | Transverse | Longitudinal

function formatConfidence(conf) {
  if (conf === null || conf === undefined) return "--";
  const n = Number(conf);
  if (!Number.isFinite(n)) return String(conf);
  // If model gives 0..1, convert to percentage
  const pct = n <= 1 ? n * 100 : n;
  return pct.toFixed(1);
}

function ensureHistoryLayout() {
  const historyView = document.getElementById("historyView");
  if (!historyView) return null;

  // Build layout if empty/missing
  let grid = historyView.querySelector(".history-grid");
  if (!grid) {
    historyView.innerHTML = `
      <div class="history-header">
        <h2 class="history-title">Upload History</h2>
        <button id="historyFilterBtn" class="history-filter-btn" type="button">All</button>
      </div>
      <div class="history-grid"></div>
    `;
    grid = historyView.querySelector(".history-grid");
  }

  // Wire filter button once
  const btn = document.getElementById("historyFilterBtn");
  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => {
      cycleHistoryFilter();
      btn.textContent = __historyFilter;
      renderHistoryCards(__historyCache);
    });
  }

  return grid;
}

function cycleHistoryFilter() {
  if (__historyFilter === "All") __historyFilter = "Transverse";
  else if (__historyFilter === "Transverse") __historyFilter = "Longitudinal";
  else __historyFilter = "All";
}

function matchesFilter(card) {
  if (__historyFilter === "All") return true;

  const wanted = __historyFilter.toLowerCase();
  const dets = Array.isArray(card.detections) ? card.detections : [];
  return dets.some((d) => String(d.crack_type || "").toLowerCase().includes(wanted));
}

function renderHistoryCards(cards) {
  const historyView = document.getElementById("historyView");
  const grid = historyView.querySelector(".history-grid");
  const filterBtn = document.getElementById("historyFilterBtn");

  if (filterBtn) filterBtn.textContent = __historyFilter;

  const filtered = cards.filter(matchesFilter);

  if (filtered.length === 0) {
    grid.innerHTML = "<p>No matching history records.</p>";
    return;
  }

  grid.innerHTML = "";

  filtered.forEach((img) => {
    const div = document.createElement("div");
    div.className = "history-item";

    // --- Preview (card) content: timestamp + crack types only ---
    const dets = Array.isArray(img.detections) ? img.detections : [];
    const ts = img.timestamp || "--";

    // Unique crack types, keep order of first appearance
    const seen = new Set();
    const crackTypes = [];
    dets.forEach((d) => {
      const t = String(d.crack_type || "").trim();
      if (!t) return;
      const key = t.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        crackTypes.push(t);
      }
    });

    const pillsHtml =
      crackTypes.length === 0
        ? `<span class="crack-pill crack-pill--none">No cracks</span>`
        : crackTypes
            .map((t) => `<span class="crack-pill">${t}</span>`)
            .join("");

    div.innerHTML = `
      <img src="${img.image_url}" alt="History image">
      <p class="history-timestamp">${ts}</p>
      <div class="history-cracks">${pillsHtml}</div>
    `;

    // Store full details for preview overlay
    div.dataset.imageUrl = img.image_url || "";
    div.dataset.timestamp = img.timestamp || "--";
    div.dataset.status = img.status || "--";
    div.dataset.recommendation = img.recommendation || "--";
    div.dataset.filename = img.filename || "";
    div.dataset.detections = JSON.stringify(dets);

    grid.appendChild(div);
  });
}

async function loadHistory() {
  const grid = ensureHistoryLayout();
  if (!grid) return;
  try {
    const res = await fetch("/history");
    const images = await res.json();

    __historyCache = Array.isArray(images) ? images : [];

    if (__historyCache.length === 0) {
      grid.innerHTML = "<p>No saved images found.</p>";
      return;
    }

    renderHistoryCards(__historyCache);
  } catch (error) {
    console.error("Failed to fetch history:", error);
    grid.innerHTML = "<p>Error loading history data.</p>";
  }
}

// --- Image Preview Logic (re-using existing overlay) ---
// Double-click to open preview
document.addEventListener("dblclick", function (e) {
  const imgEl = e.target.closest(".history-item img");
  if (!imgEl) return;

  const card = imgEl.closest(".history-item");
  if (!card) return;

  const overlay = document.getElementById("imagePreviewOverlay");
  const previewImg = document.getElementById("previewImage");
  const previewDetails = document.getElementById("previewDetails");
  if (!overlay || !previewImg || !previewDetails) return;

  previewImg.src = card.dataset.imageUrl || imgEl.src;

  // Build bottom details panel (blue flair)
  let dets = [];
  try {
    dets = JSON.parse(card.dataset.detections || "[]") || [];
  } catch {
    dets = [];
  }

  const ts = card.dataset.timestamp || "--";
  const status = card.dataset.status || "--";
  const rec = card.dataset.recommendation || "--";

  const detListHtml =
    dets.length === 0
      ? `<div class="preview-cracks"><span class="crack-pill crack-pill--none">No cracks</span></div>`
      : `<div class="preview-cracks">${dets
          .map((d) => {
            const t = d.crack_type ?? "unknown";
            const c = formatConfidence(d.confidence);
            return `<span class="crack-pill">${t} <span class="pill-conf">${c}%</span></span>`;
          })
          .join("")}</div>`;

  previewDetails.innerHTML = `
    <div class="preview-details-panel">
      <div class="preview-row">
        <div><span class="preview-label">Time</span><div class="preview-value">${ts}</div></div>
        <div><span class="preview-label">Status</span><div class="preview-value">${status}</div></div>
      </div>
      <div class="preview-row">
        <div class="preview-wide"><span class="preview-label">Recommendation</span><div class="preview-value">${rec}</div></div>
      </div>
      <div class="preview-row">
        <div class="preview-wide"><span class="preview-label">Detected Cracks</span>${detListHtml}</div>
      </div>
    </div>
  `;

  overlay.style.display = "flex";
});

// Close Preview: click outside image
const __overlay = document.getElementById("imagePreviewOverlay");
if (__overlay) {
  __overlay.addEventListener("click", (e) => {
    if (e.target.id === "imagePreviewOverlay") {
      e.currentTarget.style.display = "none";
    }
  });
}

// Refresh when History tab is shown
window.addEventListener("historyViewShown", () => {
  loadHistory();
});

function closePreview() {
  const overlay = document.getElementById("imagePreviewOverlay");
  const img = document.getElementById("previewImage");
  const details = document.getElementById("previewDetails");

  if (img) img.src = "#";
  if (details) details.innerHTML = "";
  if (overlay) overlay.style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.getElementById("imagePreviewOverlay");
  const closeBtn = document.getElementById("closePreview");

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      if (overlay) overlay.style.display = "none";
    });
  }

  if (overlay) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.style.display = "none";
    });
  }
});

