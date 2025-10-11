// Import Three.js and OrbitControls (loaded via import map in index.html)
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// --- SCENE SETUP ---
const viewerCanvas = document.getElementById('viewer');

// Create a smaller 3D viewport that adjusts dynamically with the window
const renderer = new THREE.WebGLRenderer({ canvas: viewerCanvas, antialias: true });
const resizeRenderer = () => {
  const containerWidth = window.innerWidth * 0.7;  // smaller width
  const containerHeight = window.innerHeight * 0.8; // smaller height
  renderer.setSize(containerWidth, containerHeight);
};
resizeRenderer();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);

// --- CAMERA SETUP (fix clipping and distance) ---
const aspect = (window.innerWidth * 0.7) / (window.innerHeight * 0.8);
const camera = new THREE.PerspectiveCamera(60, aspect, 1, 8000); // larger far plane
camera.position.set(0, 200, 400); // start farther away

// --- LIGHTING ---
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
directionalLight.position.set(5, 10, 7.5);
scene.add(directionalLight);

// --- ORBIT CONTROLS ---
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 1, 0);
controls.minDistance = 5;
controls.maxDistance = 5000;

// --- LOAD MODEL ---
const loader = new GLTFLoader();
loader.load(
  '/static/models/sample_bogie.glb', // your model path
  (gltf) => {
    const model = gltf.scene;
    model.scale.set(0.5, 0.5, 0.5);
    model.position.set(0, 0, 0);
    scene.add(model);

    // --- AUTO-FIT CAMERA TO MODEL ---
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
    console.log(`Model ${(xhr.loaded / xhr.total * 100).toFixed(2)}% loaded`);
  },
  (error) => {
    console.error('Error loading model:', error);
  }
);

// --- ANIMATION LOOP ---
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

// --- RESPONSIVE RESIZING ---
window.addEventListener('resize', () => {
  const containerWidth = window.innerWidth * 0.7;
  const containerHeight = window.innerHeight * 0.8;
  camera.aspect = containerWidth / containerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(containerWidth, containerHeight);
});
