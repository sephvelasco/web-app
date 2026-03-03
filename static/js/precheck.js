let liveVerified = false;
let uploadVerified = false;

// Elements
const liveClassText = document.getElementById("liveClassText");
const uploadClassText = document.getElementById("uploadClassText");
const continueBtn = document.getElementById("continueBtn");
const refreshBtn = document.getElementById("refreshBtn");

const verifyFile = document.getElementById("verifyFile");
const verifyBtn = document.getElementById("verifyBtn");

const uploadPreviewImg = document.getElementById("uploadPreviewImg");
const uploadPlaceholder = document.getElementById("uploadPlaceholder");
const bogieIdInput = document.getElementById("bogieIdInput");

function setContinueEnabled() {
  continueBtn.disabled = !(liveVerified || uploadVerified);
}

document.addEventListener("DOMContentLoaded", () => {
  const liveImg = document.getElementById("liveFeed");
  if (!liveImg) return;

  liveImg.style.visibility = "hidden";
  liveImg.addEventListener("load", () => {
    liveImg.style.visibility = "visible";
  }, { once: true });
});

// Suggest a bogie ID (optional)
async function loadSuggestedBogieId() {
  if (!bogieIdInput) return;
  try {
    const res = await fetch('/bogie/suggest_id', { cache: 'no-store' });
    const data = await res.json();
    if (data && data.suggested && !bogieIdInput.value) {
      bogieIdInput.placeholder = `${data.suggested} (leave blank to auto)`;
    }
  } catch (e) {}
}
loadSuggestedBogieId();

// ---- Live poll (USB camera verification) ----
// Expecting /bogie_check to return JSON like:
// { verified: bool, message: str, best: {name, conf} }  (best optional)
async function pollLive() {
  try {
    const res = await fetch("/bogie_check", { cache: "no-store" });
    const data = await res.json();

	liveVerified = !!data.live_verified;

    // Show classification only (no "Status:" label)
    // Prefer best.name/conf if server provides it; fallback to message
    if (data.best && data.best.name) {
      const conf = typeof data.best.conf === "number" ? data.best.conf.toFixed(2) : data.best.conf;
      liveClassText.textContent = `${data.best.name} (${conf})`;
    } else if (data.message) {
      liveClassText.textContent = data.message;
    } else {
      liveClassText.textContent = liveVerified ? "Verified" : "Searching...";
    }

    setContinueEnabled();
  } catch (e) {
    liveClassText.textContent = "Live verification unavailable.";
    liveVerified = false;
    setContinueEnabled();
  }
}

// Run poll continuously
setInterval(pollLive, 700);
pollLive();

// ---- Upload preview ----
if (verifyFile) {
  verifyFile.addEventListener("change", () => {
    const f = verifyFile.files && verifyFile.files[0];
    uploadVerified = false;
    setContinueEnabled();

    if (!f) {
      uploadClassText.textContent = "Upload an image to verify.";
      uploadPreviewImg.style.display = "none";
      uploadPlaceholder.style.display = "grid";
      return;
    }

    const url = URL.createObjectURL(f);
    uploadPreviewImg.src = url;
    uploadPreviewImg.style.display = "block";
    uploadPlaceholder.style.display = "none";
    uploadClassText.textContent = "Ready to verify.";
  });
}


// ---- Upload verify ----
// Expecting /verify_image to return JSON like:
// { ok: bool, best: {name, conf}, message?: str }
if (verifyBtn) {
  verifyBtn.addEventListener("click", async () => {
    const f = verifyFile.files && verifyFile.files[0];
    if (!f) {
      uploadClassText.textContent = "Please choose an image first.";
      return;
    }

    uploadClassText.textContent = "Verifying...";
    uploadVerified = false;
    setContinueEnabled();

    try {
      const form = new FormData();
      form.append("file", f);

      const res = await fetch("/verify_image", {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      uploadVerified = !!data.ok;

      if (data.best && data.best.name) {
        const conf = typeof data.best.conf === "number" ? data.best.conf.toFixed(2) : data.best.conf;
        uploadClassText.textContent = `${data.best.name} (${conf})`;
      } else if (data.message) {
        uploadClassText.textContent = data.message;
      } else {
        uploadClassText.textContent = uploadVerified ? "Verified" : "Not verified";
      }

      // IMPORTANT: do NOT auto-continue
      setContinueEnabled();
    } catch (e) {
      uploadClassText.textContent = "Upload verification failed.";
      uploadVerified = false;
      setContinueEnabled();
    }
  });
}

// ---- Refresh button ----
if (refreshBtn) {
  refreshBtn.addEventListener("click", () => {
    // Force refresh the live feed image (cache-bust)
    const liveImg = document.getElementById("liveFeed");
    if (liveImg) {
      const base = "/usb_video_feed";
      liveImg.src = `${base}?t=${Date.now()}`;
    }
    pollLive();
  });
}

// ---- Continue button ----
// Only proceeds when you click Continue (even if upload verification passed)
if (continueBtn) {
  continueBtn.addEventListener("click", async () => {
  if (!(liveVerified || uploadVerified)) return;

  const bogie_id = (bogieIdInput && bogieIdInput.value ? bogieIdInput.value : '').trim();

  try {
    const res = await fetch("/set_verified", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bogie_id }),
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.ok) {
      liveVerified = false;
      uploadVerified = false;
      setContinueEnabled();
      liveClassText.textContent = data.message || "Verification required.";
      return;
    }

    window.location.href = "/dashboard";
  } catch (e) {
    liveClassText.textContent = "Server error. Please try again.";
  }
});
}
