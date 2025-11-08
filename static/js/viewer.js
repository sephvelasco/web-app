import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const viewerArea = document.getElementById("viewerArea");
const viewerCanvas = document.getElementById("viewer");

// SCENE & RENDERER
const renderer = new THREE.WebGLRenderer({
  canvas: viewerCanvas,
  antialias: true,
});
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);

// Initial dimensions for Camera Aspect Ratio
const initialRect = viewerArea.getBoundingClientRect();
const initialAspect = initialRect.width / initialRect.height;

// CAMERA SETUP
const camera = new THREE.PerspectiveCamera(60, initialAspect, 1, 8000);
camera.position.set(0, 200, 400);

// LIGHTING
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
directionalLight.position.set(5, 10, 7.5);
scene.add(directionalLight);

// ORBIT CONTROLS
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 1, 0);
controls.minDistance = 5;
controls.maxDistance = 5000;

export const resizeRenderer = () => {
  // 1. Get the current dimensions of the parent container
  const rect = viewerArea.getBoundingClientRect();
  const containerWidth = rect.width;
  const containerHeight = rect.height;

  // 2. Set the renderer size to fill the container
  renderer.setSize(containerWidth, containerHeight);

  // 3. Update the camera aspect ratio
  camera.aspect = containerWidth / containerHeight;
  camera.updateProjectionMatrix();

  // 4. Update CSS for canvas (ensure it fills the space)
  viewerCanvas.style.width = "100%";
  viewerCanvas.style.height = "100%";
};

// Initial setup call
resizeRenderer();

// Add global event listeners for resizing
window.addEventListener("resize", resizeRenderer);
// sidebar.js will dispatch 'sidebarToggled'
window.addEventListener("sidebarToggled", resizeRenderer);

// LOAD MODEL
const loader = new GLTFLoader();
loader.load(
  "/static/models/text_3d.glb",
  (gltf) => {
    const model = gltf.scene;
    model.scale.set(0.5, 0.5, 0.5);
    model.position.set(0, 0, 0);
    scene.add(model);

    // AUTO-FIT CAMERA TO MODEL
    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);

    const fov = camera.fov * (Math.PI / 180);
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
    cameraZ *= 2.5; // add padding

    camera.position.set(center.x, center.y + maxDim / 2, cameraZ);
    camera.lookAt(center);
    controls.target.copy(center);
    controls.update();
  },
  (xhr) => {
    console.log(`Model ${((xhr.loaded / xhr.total) * 100).toFixed(2)}% loaded`);
  },
  (error) => {
    console.error("Error loading model:", error);
  }
);

// ANIMATION LOOP & PAUSE LOGIC
let paused = false;

// Listens for the event dispatched by dashboard.js when switching tabs
window.addEventListener("pause3DRender", (e) => {
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
