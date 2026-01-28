const msgEl = document.getElementById("precheckMessage");
const hintEl = document.getElementById("precheckHint");
const continueBtn = document.getElementById("continueBtn");
const refreshBtn = document.getElementById("refreshBtn");

const verifyFile = document.getElementById("verifyFile");
const verifyBtn = document.getElementById("verifyBtn");
const verifyPreview = document.getElementById("verifyPreview");
const verifyResult = document.getElementById("verifyResult");

let pollHandle = null;
let uploadVerified = false;

async function pollPrecheck() {
  try {
    const res = await fetch("/bogie_check");
    if (!res.ok) return;
    const data = await res.json();

    if (data.verified) {
      // Already verified -> go straight to dashboard
      window.location.href = "/dashboard";
      return;
    }

    msgEl.textContent = data.message || "Scanning...";

    // If we have a dedicated classifier in the future, auto_supported will flip True.
    if (data.auto_supported) {
      hintEl.textContent = "Auto-verification enabled.";
    } else {
      hintEl.textContent =
        "Auto-verification model not installed. The system will enable Continue once the cameras see a valid scene.";
    }

    // Continue can be enabled by live precheck OR by uploaded image verification
    continueBtn.disabled = !(data.frame_ok || uploadVerified);
  } catch (e) {
    console.error("Precheck poll error", e);
  }
}

function startPolling() {
  if (pollHandle) return;
  pollPrecheck();
  pollHandle = setInterval(pollPrecheck, 800);
}

async function setVerified() {
  continueBtn.disabled = true;
  continueBtn.textContent = "Continuing...";
  try {
    const res = await fetch("/set_verified", { method: "POST" });
    const data = await res.json();
    if (data.verified) {
      window.location.href = "/dashboard";
    } else {
      alert("Unable to continue. Please try again.");
    }
  } catch (e) {
    console.error("set_verified error", e);
    alert("Unable to continue. Please try again.");
  } finally {
    continueBtn.textContent = "Continue";
  }
}

continueBtn.addEventListener("click", setVerified);
refreshBtn.addEventListener("click", () => {
  pollPrecheck();
});

function showPreview(file) {
  if (!file) return;
  const url = URL.createObjectURL(file);
  verifyPreview.src = url;
  verifyPreview.style.display = "block";
}

async function verifyUploadedImage() {
  const file = verifyFile.files && verifyFile.files[0];
  if (!file) {
    alert("Please choose an image first.");
    return;
  }

  verifyBtn.disabled = true;
  verifyBtn.textContent = "Verifying...";
  verifyResult.textContent = "";

  try {
    const form = new FormData();
    form.append("file", file);

    const res = await fetch("/verify_image", {
      method: "POST",
      body: form,
    });

    const data = await res.json();
    if (!res.ok) {
      verifyResult.textContent = data.error || "Unable to verify image.";
      uploadVerified = false;
      return;
    }

    if (data.verified) {
      uploadVerified = true;
      const best = data.best;
      if (best && best.name) {
        verifyResult.textContent = `Verified: ${best.name} (conf ${Math.round(best.conf * 100)}%)`;
      } else {
        verifyResult.textContent = "Verified.";
      }
      // Once verified, proceed immediately
      window.location.href = "/dashboard";
      return;
    } else {
      uploadVerified = false;
      const best = data.best;
      if (best && best.name) {
        verifyResult.textContent = `Not verified. Best match: ${best.name} (conf ${Math.round(best.conf * 100)}%)`;
      } else {
        verifyResult.textContent = "Not verified. Please try another image.";
      }
    }
  } catch (e) {
    console.error("verify_image error", e);
    verifyResult.textContent = "Unable to verify image. Please try again.";
    uploadVerified = false;
  } finally {
    verifyBtn.textContent = "Verify Image";
    verifyBtn.disabled = false;
    pollPrecheck();
  }
}

if (verifyFile) {
  verifyFile.addEventListener("change", () => {
    uploadVerified = false;
    verifyResult.textContent = "";
    showPreview(verifyFile.files && verifyFile.files[0]);
    pollPrecheck();
  });
}

if (verifyBtn) {
  verifyBtn.addEventListener("click", verifyUploadedImage);
}

startPolling();
