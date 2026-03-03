import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const viewerArea = document.getElementById("viewerArea");
const viewerCanvas = document.getElementById("viewer");

// -------------------- Scene / renderer --------------------
const renderer = new THREE.WebGLRenderer({ canvas: viewerCanvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);

// Initial dimensions for camera aspect ratio
const initialRect = viewerArea.getBoundingClientRect();
const initialAspect = initialRect.width / initialRect.height;

// Camera
const camera = new THREE.PerspectiveCamera(60, initialAspect, 1, 8000);
camera.position.set(0, 200, 400);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
directionalLight.position.set(5, 10, 7.5);
scene.add(directionalLight);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 0, 0);
controls.minDistance = 5;
controls.maxDistance = 5000;

export const resizeRenderer = () => {
  const rect = viewerArea.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height);
  camera.aspect = rect.width / rect.height;
  camera.updateProjectionMatrix();
  viewerCanvas.style.width = "100%";
  viewerCanvas.style.height = "100%";
};

resizeRenderer();
window.addEventListener("resize", resizeRenderer);
window.addEventListener("sidebarToggled", resizeRenderer);

// -------------------- Model loading + auto-scale/rotate --------------------
let bogieModel = null;
let bogieHalfLength = 950.0; // mm; updated after load

const loader = new GLTFLoader();
loader.load(
  "/static/models/bogie800k.glb",
  (gltf) => {
    const model = gltf.scene;

    // Reset transforms
    model.position.set(0, 0, 0);
    model.rotation.set(0, 0, 0);
    model.scale.set(1, 1, 1);
    scene.add(model);

    // Measure bounding box (native units)
    const box0 = new THREE.Box3().setFromObject(model);
    const size0 = box0.getSize(new THREE.Vector3());

    // Decide which axis is "length" (largest dimension)
    const dims = [size0.x, size0.y, size0.z];
    let axisIndex = 0;
    if (dims[1] > dims[axisIndex]) axisIndex = 1;
    if (dims[2] > dims[axisIndex]) axisIndex = 2;

    // Scale so the length becomes 1900mm
    const REAL_LENGTH_MM = 1900.0;
    const lengthNative = dims[axisIndex] || 1.0;
    const scaleFactor = REAL_LENGTH_MM / lengthNative;
    model.scale.setScalar(scaleFactor);

    // Rotate so the length axis aligns with world X
    if (axisIndex === 1) {
      // Y -> X
      model.rotation.z = -Math.PI / 2;
    } else if (axisIndex === 2) {
      // Z -> X
      model.rotation.y = Math.PI / 2;
    }

    // Center model at origin
    const box2 = new THREE.Box3().setFromObject(model);
    const center2 = box2.getCenter(new THREE.Vector3());
    model.position.sub(center2);

    // Final size (mm)
    const box3 = new THREE.Box3().setFromObject(model);
    const size3 = box3.getSize(new THREE.Vector3());
    bogieHalfLength = (size3.x || REAL_LENGTH_MM) / 2.0;

    bogieModel = model;

    // Side-view camera
    const maxDim = Math.max(size3.x, size3.y, size3.z);
    const dist = maxDim * 1.8;
    camera.position.set(0, maxDim * 0.25, dist);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
  },
  (xhr) => {
    if (xhr.total) console.log(`Model ${((xhr.loaded / xhr.total) * 100).toFixed(2)}% loaded`);
  },
  (error) => {
    console.error("Error loading model:", error);
  }
);

// -------------------- Mapping markers --------------------
const markerGroup = new THREE.Group();
scene.add(markerGroup);

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let __markerPayloadByUuid = new Map();

function clearMarkers() {
  while (markerGroup.children.length) markerGroup.remove(markerGroup.children[0]);
  __markerPayloadByUuid = new Map();
}

function markerColorForPoint(pt) {
  // Basic coloring: transverse = red-ish, longitudinal = blue-ish, otherwise purple
  const dets = Array.isArray(pt.detections) ? pt.detections : [];
  const types = dets.map((d) => String(d.crack_type || "").toLowerCase());
  const hasTrans = types.some((t) => t.includes("transverse"));
  const hasLong = types.some((t) => t.includes("longitudinal"));
  if (hasTrans && hasLong) return 0x7c3aed; // purple
  if (hasTrans) return 0xef4444; // red
  if (hasLong) return 0x3b82f6; // blue
  return 0xf59e0b; // amber
}

function addMarker(pt) {
  if (pt.x_mm == null || pt.y_mm == null) return;

  // Map: x_mm is 0..1900 -> world X is roughly [-halfLen..+halfLen]
  const x = Number(pt.x_mm) - bogieHalfLength;
  const z = Number(pt.y_mm); // left/right across width (depth in side view)

  const geom = new THREE.SphereGeometry(10, 16, 16); // 10mm radius
  const mat = new THREE.MeshStandardMaterial({ color: markerColorForPoint(pt), roughness: 0.35, metalness: 0.05 });
  const m = new THREE.Mesh(geom, mat);
  m.position.set(x, 0, z);
  markerGroup.add(m);
  __markerPayloadByUuid.set(m.uuid, pt);
}

function formatConfidence(conf) {
  if (conf === null || conf === undefined) return "--";
  const n = Number(conf);
  if (!Number.isFinite(n)) return String(conf);
  return n.toFixed(1);
}

function openPreview(pt) {
  const overlay = document.getElementById("imagePreviewOverlay");
  const previewImg = document.getElementById("previewImage");
  const previewDetails = document.getElementById("previewDetails");
  if (!overlay || !previewImg || !previewDetails) return;

  previewImg.src = pt.image_url || "#";

  const dets = Array.isArray(pt.detections) ? pt.detections : [];
  const ts = pt.timestamp || "--";
  const status = pt.status || "--";
  const rec = pt.recommendation || "--";
  const seg = pt.segment ? `Segment ${pt.segment}` : "--";
  const pos = `x=${pt.x_mm != null ? Number(pt.x_mm).toFixed(1) : "--"}mm, y=${pt.y_mm != null ? Number(pt.y_mm).toFixed(1) : "--"}mm`;

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
        <div><span class="preview-label">Segment</span><div class="preview-value">${seg}</div></div>
      </div>
      <div class="preview-row">
        <div><span class="preview-label">Status</span><div class="preview-value">${status}</div></div>
        <div><span class="preview-label">Position</span><div class="preview-value">${pos}</div></div>
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
}

function handleCanvasClick(ev) {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -(((ev.clientY - rect.top) / rect.height) * 2 - 1);
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(markerGroup.children, true);
  if (!hits || hits.length === 0) return;
  const uuid = hits[0].object.uuid;
  const pt = __markerPayloadByUuid.get(uuid);
  if (pt) openPreview(pt);
}

viewerCanvas?.addEventListener('click', handleCanvasClick);

async function loadMarkersForBogie(bogie_id) {
  if (!bogie_id) return;
  try {
    const res = await fetch(`/mapping/points?bogie_id=${encodeURIComponent(bogie_id)}`, { cache: 'no-store' });
    const out = await res.json();
    const pts = out && Array.isArray(out.points) ? out.points : [];
    clearMarkers();
    pts.forEach(addMarker);
  } catch (e) {
    console.warn('Failed to load mapping points', e);
  }
}

// On load, try to get current bogie id and show markers
async function initMarkers() {
  try {
    const res = await fetch('/bogie/current', { cache: 'no-store' });
    const out = await res.json();
    if (out && out.bogie_id) {
      await loadMarkersForBogie(out.bogie_id);
    }
  } catch (e) {}
}
initMarkers();

// Refresh markers when dashboard says mapping changed
window.addEventListener('mappingUpdated', async (e) => {
  const bid = e?.detail?.bogie_id;
  if (bid) await loadMarkersForBogie(bid);
});

// Also refresh when user opens the model tab (optional)
window.addEventListener('pause3DRender', async (e) => {
  if (e.detail === false) {
    try {
      const res = await fetch('/bogie/current', { cache: 'no-store' });
      const out = await res.json();
      if (out && out.bogie_id) await loadMarkersForBogie(out.bogie_id);
    } catch (err) {}
  }
});

// -------------------- Animation loop & pause logic --------------------
let paused = false;
window.addEventListener('pause3DRender', (e) => {
  paused = e.detail;
});

function animate() {
  requestAnimationFrame(animate);
  if (!paused) {
    controls.update();
    renderer.render(scene, camera);
  }
}
animate();
