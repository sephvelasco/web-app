// Motor calibration UI helpers.
// Works for BOTH:
//  1) Standalone /dashboard/motor page (dark UI) with ids: mm, period, connected, moving, posSteps, posMm, log
//  2) Integrated dashboard Calibration view with ids: cal_mm, cal_period, cal_connected, cal_moving, cal_posSteps, cal_posMm, cal_log, cal_error

async function postJson(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: data ? JSON.stringify(data) : "{}",
  });
  return res.json().catch(() => ({ ok: false, error: "Bad JSON response" }));
}

async function doStop() {
  const out = await postJson("/motor/stop");
  if (!out.ok) alert(out.error || "Stop failed");
}

async function doZero() {
  const out = await postJson("/motor/zero");
  if (!out.ok) alert(out.error || "Zero failed");
}

async function doGet() {
  const out = await postJson("/motor/get");
  if (!out.ok) alert(out.error || "GET failed");
}

async function setSpeed(stepPeriodUs) {
  const out = await postJson("/motor/speed", { stepPeriodUs: stepPeriodUs });
  if (!out.ok) alert(out.error || "Speed set failed");
}

// Standalone page helper
function applySpeedFromUi() {
  const el = document.getElementById("period");
  const v = parseInt(el?.value || "1500", 10);
  setSpeed(v);
}

async function moveMm(mmOrSign) {
  // If called from standalone page (Move + / Move -), mmOrSign is +1 or -1
  // If called from integrated view, we pass the mm directly.
  let mm = mmOrSign;

  const standaloneMm = document.getElementById("mm");
  if (standaloneMm && (mmOrSign === 1 || mmOrSign === -1)) {
    mm = parseFloat(standaloneMm.value || "0") * mmOrSign;
  }

  const out = await postJson("/motor/move_mm", { mm: mm });
  if (!out.ok) alert(out.error || "Move failed");
}

// ------- Status refresh (supports both UIs) -------

function updateStandaloneUi(state) {
  const connected = document.getElementById("connected");
  const moving = document.getElementById("moving");
  const posSteps = document.getElementById("posSteps");
  const posMm = document.getElementById("posMm");
  const log = document.getElementById("log");

  if (!connected || !moving || !posSteps || !posMm || !log) return false;

  connected.textContent = state.connected ? "Yes" : "No";
  moving.textContent = state.moving ? "Yes" : "No";
  posSteps.textContent = state.posSteps ?? "—";
  posMm.textContent = state.posMm ?? "—";
  log.textContent = state.last_line || state.lastLine || "(no data yet)";
  return true;
}

function updateIntegratedUi(state) {
  const connected = document.getElementById("cal_connected");
  const moving = document.getElementById("cal_moving");
  const posSteps = document.getElementById("cal_posSteps");
  const posMm = document.getElementById("cal_posMm");
  const log = document.getElementById("cal_log");
  const err = document.getElementById("cal_error");

  if (!connected || !moving || !posSteps || !posMm || !log) return false;

  connected.textContent = state.connected ? "Yes" : "No";
  moving.textContent = state.moving ? "Yes" : "No";
  posSteps.textContent = state.posSteps ?? "—";
  posMm.textContent = (state.posMm ?? "—");
  log.textContent = state.last_line || state.lastLine || "(no data yet)";
  if (err) err.textContent = state.last_error || "";
  return true;
}

async function refreshMotorStatus() {
  try {
    const res = await fetch("/motor/status");
    const out = await res.json();
    if (!out.ok) {
      // If gated, just show message where possible
      const msg = out.error || "Motor status unavailable";
      const log = document.getElementById("log") || document.getElementById("cal_log");
      const err = document.getElementById("cal_error");
      if (log) log.textContent = msg;
      if (err) err.textContent = msg;
      return;
    }

    const s = out.state || out; // backward compatibility
    // Try integrated first, then standalone
    if (!updateIntegratedUi(s)) {
      updateStandaloneUi(s);
    }
  } catch (e) {
    const log = document.getElementById("log") || document.getElementById("cal_log");
    const err = document.getElementById("cal_error");
    if (log) log.textContent = "Error: " + e;
    if (err) err.textContent = String(e);
  }
}

// Expose for inline onclick buttons
if (typeof window !== "undefined") {
  window.moveMm = moveMm;
  window.doStop = doStop;
  window.doZero = doZero;
  window.doGet = doGet;
  window.setSpeed = setSpeed;
  window.applySpeedFromUi = applySpeedFromUi;
}

// Start polling if either UI exists on the page.
const hasStandalone = !!document.getElementById("log");
const hasIntegrated = !!document.getElementById("cal_log");

if (hasStandalone || hasIntegrated) {
  refreshMotorStatus();
  setInterval(refreshMotorStatus, 200);
}
