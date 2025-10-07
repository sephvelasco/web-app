/* =============================
FATIGUE CRACK DETECTION DASHBOARD - VIEWER SCRIPT
============================= */

// --- SCENE SETUP ---
const viewerCanvas = document.getElementById('viewer');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(
60,
viewerCanvas.clientWidth / viewerCanvas.clientHeight,
0.1,
1000
);
const renderer = new THREE.WebGLRenderer({
canvas: viewerCanvas,
antialias: true
});
renderer.setSize(viewerCanvas.clientWidth, viewerCanvas.clientHeight);
renderer.setClearColor(0x202020);

// --- LIGHTING ---
const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(5, 10, 7.5);
scene.add(dirLight);
scene.add(new THREE.AmbientLight(0x505050));

// --- LOAD 3D MODEL ---
const loader = new THREE.GLTFLoader();
loader.load('/static/models/bogie.glb', (gltf) => {
const model = gltf.scene;
model.scale.set(1, 1, 1);
scene.add(model);
camera.position.set(0, 1, 5);
animate();
});

// --- RENDER LOOP ---
function animate() {
requestAnimationFrame(animate);
renderer.render(scene, camera);
}

// --- ADD MARKER FUNCTION ---
function addMarker(x, y, z, color = 0xff0000) {
const geometry = new THREE.SphereGeometry(0.05, 16, 16);
const material = new THREE.MeshBasicMaterial({ color });
const sphere = new THREE.Mesh(geometry, material);
sphere.position.set(x, y, z);
scene.add(sphere);
}

// --- FETCH AND DISPLAY DETECTION DATA ---
async function fetchData() {
const res = await fetch('/data/latest');
const data = await res.json();

document.getElementById('bogieId').textContent = data.bogie_id;
document.getElementById('timestamp').textContent = data.timestamp;
document.getElementById('status').textContent = data.status;
document.getElementById('status').className = data.detections.length
? "status alert"
: "status ok";
document.getElementById('recommendation').textContent = data.recommendation;

const list = document.getElementById('detectionsList');
list.innerHTML = '';

// Remove old markers before adding new ones
scene.children = scene.children.filter(obj => obj.type !== 'Mesh' || obj.geometry.type !== 'SphereGeometry');

data.detections.forEach(det => {
const li = document.createElement('li');
li.textContent = `${det.type} (${(det.confidence * 100).toFixed(1)}%)`;
list.appendChild(li);
addMarker(...det.location);
});
}

// --- REFRESH DATA REGULARLY ---
fetchData();
setInterval(fetchData, 5000); // refresh every 5 seconds

// --- HANDLE WINDOW RESIZE ---
window.addEventListener('resize', () => {
camera.aspect = viewerCanvas.clientWidth / viewerCanvas.clientHeight;
camera.updateProjectionMatrix();
renderer.setSize(viewerCanvas.clientWidth, viewerCanvas.clientHeight);
});
