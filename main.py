from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
import os
import json
import time
import secrets
import re
from datetime import datetime, timedelta

app = FastAPI()

# --- CONFIG ---
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_KEY:
    print("WARNING: GROQ_API_KEY not set. AI will not work.")

# --- LICENSE DATABASE (in-memory) ---
# Pre-generate 100 random-looking license keys
# Format: "license-key-XXXXX" where XXXXX is a random alphanumeric
LICENSES = {}
def generate_license_key():
    # Generate a random string like "license-key-a7f9k"
    random_part = ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6))
    return f"license-key-{random_part}"

# Generate 100 keys
for _ in range(99):
    key = generate_license_key()
    LICENSES[key] = {
        "admin": False,
        "active": True,
        "used_by": None,
        "last_active": None,
        "restrictions": "",
        "created": datetime.now().isoformat()
    }

# The special admin key (with a slightly different pattern)
ADMIN_KEY = "AyoitsjamesonJamo67"
LICENSES[ADMIN_KEY] = {
    "admin": True,
    "active": True,
    "used_by": None,
    "last_active": None,
    "restrictions": "",
    "created": datetime.now().isoformat()
}

# Track active sessions
active_sessions = {}  # key -> last ping time (timestamp)

# --- HELPER FUNCTIONS ---
def get_license_info(key):
    return LICENSES.get(key)

def is_admin(key):
    info = get_license_info(key)
    return info and info.get("admin", False)

def is_active(key):
    info = get_license_info(key)
    return info and info.get("active", False)

def get_restrictions(key):
    info = get_license_info(key)
    return info.get("restrictions", "") if info else ""

def update_last_active(key, username="anonymous"):
    if key in LICENSES:
        LICENSES[key]["used_by"] = username
        LICENSES[key]["last_active"] = datetime.now().isoformat()
        active_sessions[key] = time.time()

# --- HTML PAGE (embedded with all styling and logic) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Jamo's OP AI</title>
  <!-- Three.js for Earth effect -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <style>
    /* --- RESET & BASE --- */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #050510;
      color: #fff;
      overflow: hidden;
      height: 100vh;
      width: 100vw;
    }

    /* --- SPLASH SCREEN (Earth + Title) --- */
    #splash {
      position: fixed;
      top: 0; left: 0;
      width: 100%; height: 100%;
      z-index: 1000;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      background: #050510;
      transition: opacity 1.2s ease, visibility 1.2s ease;
    }
    #splash.hide {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
    }
    #splash canvas {
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
      display: block;
    }
    #splash h1 {
      position: relative;
      z-index: 10;
      font-size: clamp(2.8rem, 12vw, 5.5rem);
      font-weight: 800;
      background: linear-gradient(135deg, #00f0ff, #a855f7, #ec4899);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 0 60px rgba(0,240,255,0.3);
      letter-spacing: -0.02em;
      animation: pulseGlow 2.5s ease-in-out infinite alternate;
      text-align: center;
      padding: 0 20px;
    }
    @keyframes pulseGlow {
      0% { text-shadow: 0 0 40px rgba(0,240,255,0.2); }
      100% { text-shadow: 0 0 80px rgba(168,85,247,0.5); }
    }
    #splash .sub {
      position: relative;
      z-index: 10;
      margin-top: 12px;
      font-size: clamp(1rem, 3vw, 1.4rem);
      opacity: 0.6;
      letter-spacing: 0.3em;
      text-transform: uppercase;
      color: #a0aec0;
    }

    /* --- MAIN APP (hidden until splash fades) --- */
    #app {
      position: fixed;
      top: 0; left: 0;
      width: 100%; height: 100%;
      display: none;
      flex-direction: column;
      background: #0a0a14;
      padding: 16px;
      overflow-y: auto;
    }
    #app.visible {
      display: flex;
      animation: fadeIn 0.8s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: scale(0.98); }
      to { opacity: 1; transform: scale(1); }
    }

    /* --- LOGIN SCREEN --- */
    #login-screen {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      flex: 1;
      padding: 20px;
      max-width: 440px;
      margin: 0 auto;
      width: 100%;
    }
    #login-screen .logo {
      font-size: 2.4rem;
      font-weight: 800;
      background: linear-gradient(135deg, #00f0ff, #a855f7);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 8px;
    }
    #login-screen .subtitle {
      color: #94a3b8;
      margin-bottom: 32px;
      font-size: 0.95rem;
    }
    #login-screen input {
      width: 100%;
      padding: 16px 20px;
      border-radius: 60px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      backdrop-filter: blur(10px);
      color: #fff;
      font-size: 1rem;
      outline: none;
      transition: border-color 0.3s, box-shadow 0.3s;
      text-align: center;
      letter-spacing: 0.5px;
    }
    #login-screen input:focus {
      border-color: #00f0ff;
      box-shadow: 0 0 30px rgba(0,240,255,0.15);
    }
    #login-screen button {
      margin-top: 18px;
      width: 100%;
      padding: 16px;
      border-radius: 60px;
      border: none;
      background: linear-gradient(135deg, #00f0ff, #a855f7);
      color: #fff;
      font-weight: 700;
      font-size: 1.1rem;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.3s;
      box-shadow: 0 4px 30px rgba(0,240,255,0.2);
    }
    #login-screen button:active {
      transform: scale(0.97);
    }
    #login-error {
      color: #f87171;
      margin-top: 14px;
      font-size: 0.9rem;
      min-height: 24px;
    }

    /* --- CHAT UI (shown after login) --- */
    #chat-ui {
      display: none;
      flex-direction: column;
      flex: 1;
      max-width: 720px;
      margin: 0 auto;
      width: 100%;
    }
    #chat-ui.active {
      display: flex;
    }

    /* Top bar */
    #topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0 16px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      flex-wrap: wrap;
      gap: 8px;
    }
    #topbar .brand {
      font-weight: 700;
      font-size: 1.2rem;
      background: linear-gradient(135deg, #00f0ff, #a855f7);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    #topbar .badge {
      background: rgba(168,85,247,0.15);
      padding: 4px 14px;
      border-radius: 40px;
      font-size: 0.7rem;
      border: 1px solid rgba(168,85,247,0.2);
      color: #c084fc;
      font-weight: 600;
      letter-spacing: 0.3px;
    }
    #topbar .admin-badge {
      background: rgba(0,240,255,0.12);
      border-color: rgba(0,240,255,0.25);
      color: #00f0ff;
      cursor: pointer;
    }
    #topbar .admin-badge:hover {
      background: rgba(0,240,255,0.2);
    }

    /* Messages */
    #messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px 0;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 300px;
      max-height: 55vh;
    }
    .msg {
      padding: 12px 18px;
      border-radius: 20px;
      max-width: 88%;
      word-wrap: break-word;
      line-height: 1.6;
      font-size: 0.95rem;
      animation: slideUp 0.25s ease;
    }
    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, rgba(0,240,255,0.12), rgba(168,85,247,0.12));
      border: 1px solid rgba(0,240,255,0.12);
      border-bottom-right-radius: 6px;
    }
    .msg.ai {
      align-self: flex-start;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
      border-bottom-left-radius: 6px;
    }
    .msg .restricted-tag {
      font-size: 0.6rem;
      opacity: 0.5;
      display: block;
      margin-top: 6px;
      color: #fbbf24;
    }
    @keyframes slideUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Typing indicator */
    #typing {
      display: none;
      align-self: flex-start;
      padding: 10px 18px;
      background: rgba(255,255,255,0.03);
      border-radius: 40px;
      gap: 6px;
    }
    #typing span {
      width: 8px; height: 8px;
      background: #a855f7;
      border-radius: 50%;
      display: inline-block;
      animation: bounce 1.4s infinite;
    }
    #typing span:nth-child(2) { animation-delay: 0.2s; }
    #typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
      0%,60%,100% { transform: translateY(0); opacity: 0.3; }
      30% { transform: translateY(-8px); opacity: 1; }
    }

    /* Input bar */
    #input-bar {
      display: flex;
      gap: 10px;
      padding: 12px 0 8px 0;
      border-top: 1px solid rgba(255,255,255,0.05);
      background: #0a0a14;
      position: sticky;
      bottom: 0;
    }
    #input-bar input {
      flex: 1;
      padding: 14px 18px;
      border-radius: 60px;
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.03);
      color: #fff;
      font-size: 0.95rem;
      outline: none;
      transition: border-color 0.3s;
    }
    #input-bar input:focus {
      border-color: #00f0ff;
    }
    #input-bar button {
      padding: 14px 28px;
      border-radius: 60px;
      border: none;
      background: linear-gradient(135deg, #00f0ff, #a855f7);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.15s;
    }
    #input-bar button:active {
      transform: scale(0.95);
    }

    /* --- ADMIN PANEL --- */
    #admin-panel {
      display: none;
      margin-top: 20px;
      background: rgba(255,255,255,0.03);
      border-radius: 24px;
      padding: 20px;
      border: 1px solid rgba(255,255,255,0.06);
      max-height: 400px;
      overflow-y: auto;
    }
    #admin-panel.open {
      display: block;
      animation: fadeIn 0.3s ease;
    }
    #admin-panel h3 {
      color: #00f0ff;
      margin-bottom: 12px;
      font-size: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #admin-panel table {
      width: 100%;
      font-size: 0.7rem;
      border-collapse: collapse;
    }
    #admin-panel th {
      text-align: left;
      color: #94a3b8;
      font-weight: 600;
      padding: 6px 4px;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    #admin-panel td {
      padding: 6px 4px;
      border-bottom: 1px solid rgba(255,255,255,0.03);
      word-break: break-all;
    }
    #admin-panel .status-online { color: #4ade80; }
    #admin-panel .status-offline { color: #94a3b8; }
    #admin-panel .action-btn {
      background: none;
      border: 1px solid rgba(255,255,255,0.1);
      color: #fff;
      padding: 2px 10px;
      border-radius: 30px;
      font-size: 0.6rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    #admin-panel .action-btn:hover {
      background: rgba(255,255,255,0.05);
    }
    #admin-panel .action-btn.danger {
      border-color: rgba(248,113,113,0.3);
      color: #f87171;
    }
    #admin-panel .add-key-area {
      display: flex;
      gap: 8px;
      margin: 12px 0;
      flex-wrap: wrap;
    }
    #admin-panel .add-key-area input {
      flex: 1;
      padding: 8px 14px;
      border-radius: 40px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.03);
      color: #fff;
      font-size: 0.8rem;
      outline: none;
      min-width: 100px;
    }
    #admin-panel .add-key-area button {
      padding: 8px 18px;
      border-radius: 40px;
      border: none;
      background: #00f0ff;
      color: #050510;
      font-weight: 700;
      font-size: 0.8rem;
      cursor: pointer;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 10px; }

    /* Responsive */
    @media (max-width: 480px) {
      #login-screen .logo { font-size: 1.8rem; }
      #topbar .brand { font-size: 1rem; }
      .msg { font-size: 0.9rem; padding: 10px 14px; }
      #input-bar button { padding: 12px 18px; font-size: 0.9rem; }
      #admin-panel { padding: 12px; font-size: 0.65rem; }
    }
  </style>
</head>
<body>

<!-- SPLASH SCREEN -->
<div id="splash">
  <canvas id="earthCanvas"></canvas>
  <h1>Jamo's OP AI</h1>
  <div class="sub">Unrestricted • Limitless</div>
</div>

<!-- MAIN APP -->
<div id="app">
  <!-- Login Screen -->
  <div id="login-screen">
    <div class="logo">🔮 Jamo's OP AI</div>
    <div class="subtitle">Enter your license key to continue</div>
    <input id="licenseInput" type="text" placeholder="license-key-xxxxx" autofocus>
    <button id="loginBtn">Unlock Access</button>
    <div id="login-error"></div>
  </div>

  <!-- Chat UI -->
  <div id="chat-ui">
    <div id="topbar">
      <span class="brand">⚡ Jamo AI</span>
      <span id="keyDisplay" style="font-size:0.65rem;opacity:0.4;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>
      <span id="adminToggle" class="badge admin-badge" style="display:none;">🛠 Admin</span>
    </div>
    <div id="messages">
      <div class="msg ai">Welcome. Ask anything — no limits, no filters.</div>
    </div>
    <div id="typing"><span></span><span></span><span></span></div>
    <div id="admin-panel">
      <h3>🔐 License Control <span style="font-size:0.6rem;opacity:0.5;">(refresh to apply)</span></h3>
      <div class="add-key-area">
        <input id="newKeyInput" placeholder="New key (e.g. license-key-abc123)">
        <input id="newKeyRestrict" placeholder="Restrictions (optional)">
        <button id="addKeyBtn">➕ Add</button>
      </div>
      <div style="overflow-x:auto;">
        <table id="adminTable">
          <thead><tr><th>Key</th><th>Status</th><th>User</th><th>Restrictions</th><th>Action</th></tr></thead>
          <tbody id="adminTableBody"></tbody>
        </table>
      </div>
    </div>
    <div id="input-bar">
      <input id="chatInput" type="text" placeholder="Ask anything...">
      <button id="sendBtn">Send</button>
    </div>
  </div>
</div>

<script>
// ------------------------------------------------------------
// THREE.JS EARTH (Splash)
// ------------------------------------------------------------
(function() {
  const canvas = document.getElementById('earthCanvas');
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const geometry = new THREE.SphereGeometry(1.2, 64, 64);
  const textureLoader = new THREE.TextureLoader();
  const earthMap = textureLoader.load('https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg');
  const material = new THREE.MeshPhongMaterial({ map: earthMap, specular: new THREE.Color(0x333333), shininess: 5 });
  const earth = new THREE.Mesh(geometry, material);
  scene.add(earth);

  const starsGeometry = new THREE.BufferGeometry();
  const starsCount = 3000;
  const starsPos = new Float32Array(starsCount * 3);
  for (let i = 0; i < starsCount * 3; i += 3) {
    const r = 30 + Math.random() * 20;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos((Math.random() * 2) - 1);
    starsPos[i] = r * Math.sin(phi) * Math.cos(theta);
    starsPos[i+1] = r * Math.sin(phi) * Math.sin(theta);
    starsPos[i+2] = r * Math.cos(phi);
  }
  starsGeometry.setAttribute('position', new THREE.BufferAttribute(starsPos, 3));
  const starsMaterial = new THREE.PointsMaterial({ color: 0xffffff, size: 0.12, transparent: true, opacity: 0.8 });
  const stars = new THREE.Points(starsGeometry, starsMaterial);
  scene.add(stars);

  const light = new THREE.DirectionalLight(0xffffff, 1.2);
  light.position.set(5, 5, 10);
  scene.add(light);
  const ambient = new THREE.AmbientLight(0x404060);
  scene.add(ambient);

  camera.position.z = 3.5;

  let rotation = 0;
  function animate() {
    requestAnimationFrame(animate);
    rotation += 0.0015;
    earth.rotation.y = rotation;
    stars.rotation.y = rotation * 0.02;
    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
})();

// ------------------------------------------------------------
// APP LOGIC
// ------------------------------------------------------------
const splash = document.getElementById('splash');
const app = document.getElementById('app');
const loginScreen = document.getElementById('login-screen');
const chatUI = document.getElementById('chat-ui');
const licenseInput = document.getElementById('licenseInput');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('login-error');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const messages = document.getElementById('messages');
const typing = document.getElementById('typing');
const keyDisplay = document.getElementById('keyDisplay');
const adminToggle = document.getElementById('adminToggle');
const adminPanel = document.getElementById('admin-panel');
const adminTableBody = document.getElementById('adminTableBody');
const newKeyInput = document.getElementById('newKeyInput');
const newKeyRestrict = document.getElementById('newKeyRestrict');
const addKeyBtn = document.getElementById('addKeyBtn');

let currentLicense = null;
let isAdmin = false;

// --- Splash transition ---
setTimeout(() => {
  splash.classList.add('hide');
  app.classList.add('visible');
  setTimeout(() => {
    splash.style.display = 'none';
  }, 1200);
}, 2500);

// --- Login ---
async function login() {
  const key = licenseInput.value.trim();
  if (!key) {
    loginError.textContent = 'Please enter a license key.';
    return;
  }
  loginError.textContent = 'Checking...';
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key })
    });
    const data = await res.json();
    if (res.ok && data.valid) {
      currentLicense = key;
      isAdmin = data.admin || false;
      loginScreen.style.display = 'none';
      chatUI.classList.add('active');
      keyDisplay.textContent = key.length > 16 ? key.slice(0,14)+'...' : key;
      if (isAdmin) {
        adminToggle.style.display = 'inline-block';
        adminToggle.textContent = '🛠 Admin';
        loadAdminPanel();
      } else {
        adminToggle.style.display = 'none';
      }
      // Add system message about restrictions
      if (data.restrictions) {
        addMessage('ai', '⚠️ This key has restrictions: ' + data.restrictions);
      } else {
        addMessage('ai', '🔓 Full access granted. Ask anything.');
      }
      loginError.textContent = '';
    } else {
      loginError.textContent = data.error || 'Invalid license key.';
    }
  } catch (e) {
    loginError.textContent = 'Error connecting to server.';
  }
}

loginBtn.addEventListener('click', login);
licenseInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') login(); });

// --- Send message ---
async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = '';
  addMessage('user', text);
  typing.style.display = 'flex';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: currentLicense, prompt: text })
    });
    const data = await res.json();
    typing.style.display = 'none';
    if (res.ok) {
      addMessage('ai', data.reply || 'No response.');
    } else {
      addMessage('ai', '⚠️ Error: ' + (data.error || 'Unknown error.'));
    }
  } catch (e) {
    typing.style.display = 'none';
    addMessage('ai', '⚠️ Network error. Please try again.');
  }
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });

function addMessage(type, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + type;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// --- Admin panel ---
adminToggle.addEventListener('click', () => {
  if (adminPanel.classList.contains('open')) {
    adminPanel.classList.remove('open');
  } else {
    loadAdminPanel();
    adminPanel.classList.add('open');
  }
});

async function loadAdminPanel() {
  if (!isAdmin) return;
  try {
    const res = await fetch('/api/admin/keys', {
      headers: { 'X-Admin-Key': currentLicense }
    });
    const data = await res.json();
    if (res.ok && data.keys) {
      renderAdminTable(data.keys);
    }
  } catch (e) {
    console.error('Admin load error', e);
  }
}

function renderAdminTable(keys) {
  let html = '';
  const now = Date.now();
  for (const [key, info] of Object.entries(keys)) {
    const isOnline = (info.last_active && (now - new Date(info.last_active).getTime() < 60000));
    const status = info.active ? (isOnline ? '🟢 Online' : '⚪ Inactive') : '🔴 Disabled';
    const statusClass = info.active ? (isOnline ? 'status-online' : 'status-offline') : 'status-offline';
    const user = info.used_by || '—';
    const restrictions = info.restrictions || '—';
    html += `<tr>
      <td style="max-width:100px;overflow:hidden;text-overflow:ellipsis;">${key}</td>
      <td class="${statusClass}">${status}</td>
      <td>${user}</td>
      <td>${restrictions}</td>
      <td>
        <button class="action-btn" onclick="toggleKey('${key}')">${info.active ? 'Disable' : 'Enable'}</button>
        ${key !== 'AyoitsjamesonJamo67' ? `<button class="action-btn danger" onclick="deleteKey('${key}')">Delete</button>` : ''}
      </td>
    </tr>`;
  }
  adminTableBody.innerHTML = html;
}

window.toggleKey = async function(key) {
  if (!isAdmin) return;
  try {
    const res = await fetch('/api/admin/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_key: currentLicense, target_key: key })
    });
    if (res.ok) loadAdminPanel();
  } catch (e) {}
};

window.deleteKey = async function(key) {
  if (!isAdmin || key === 'AyoitsjamesonJamo67') return;
  if (!confirm('Delete this key?')) return;
  try {
    const res = await fetch('/api/admin/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_key: currentLicense, target_key: key })
    });
    if (res.ok) loadAdminPanel();
  } catch (e) {}
};

addKeyBtn.addEventListener('click', async () => {
  if (!isAdmin) return;
  const newKey = newKeyInput.value.trim();
  const restrictions = newKeyRestrict.value.trim();
  if (!newKey) return;
  try {
    const res = await fetch('/api/admin/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_key: currentLicense, new_key: newKey, restrictions })
    });
    if (res.ok) {
      newKeyInput.value = '';
      newKeyRestrict.value = '';
      loadAdminPanel();
    } else {
      const err = await res.json();
      alert(err.error || 'Failed to add key.');
    }
  } catch (e) {}
});

// Auto-refresh admin panel every 15 seconds
setInterval(() => {
  if (isAdmin && adminPanel.classList.contains('open')) {
    loadAdminPanel();
  }
}, 15000);
</script>
</body>
</html>
"""

# --- API ENDPOINTS ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    key = data.get("key", "").strip()
    info = LICENSES.get(key)
    if not info:
        return JSONResponse({"valid": False, "error": "License key not found."})
    if not info.get("active", False):
        return JSONResponse({"valid": False, "error": "License key is disabled."})
    
    update_last_active(key, "web-user")
    return JSONResponse({
        "valid": True,
        "admin": info.get("admin", False),
        "restrictions": info.get("restrictions", "")
    })

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    key = data.get("key", "").strip()
    prompt = data.get("prompt", "").strip()
    
    if not prompt:
        return JSONResponse({"error": "Empty prompt."}, status_code=400)
    
    info = LICENSES.get(key)
    if not info or not info.get("active", False):
        return JSONResponse({"error": "Invalid or disabled license."}, status_code=403)
    
    # Apply restrictions if any
    restrictions = info.get("restrictions", "")
    if restrictions:
        prompt = f"[RESTRICTION: {restrictions}] {prompt}"
    
    update_last_active(key, "chat-user")
    
    if not GROQ_KEY:
        return JSONResponse({"error": "AI service not configured."}, status_code=500)
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"]
                return JSONResponse({"reply": reply})
            else:
                return JSONResponse({"error": f"Groq API error: {resp.status_code}"}, status_code=500)
        except Exception as e:
            return JSONResponse({"error": f"Request failed: {str(e)}"}, status_code=500)

# --- ADMIN API (protected by admin key check) ---
def check_admin(request_key):
    info = LICENSES.get(request_key)
    return info and info.get("admin", False) and info.get("active", True)

@app.get("/api/admin/keys")
async def admin_list_keys(request: Request):
    admin_key = request.headers.get("X-Admin-Key", "")
    if not check_admin(admin_key):
        raise HTTPException(403, "Admin access required.")
    # Return a sanitized copy
    return JSONResponse({"keys": LICENSES})

@app.post("/api/admin/toggle")
async def admin_toggle(request: Request):
    data = await request.json()
    admin_key = data.get("admin_key", "")
    target_key = data.get("target_key", "")
    if not check_admin(admin_key):
        raise HTTPException(403, "Admin access required.")
    if target_key not in LICENSES:
        raise HTTPException(404, "Key not found.")
    if target_key == "AyoitsjamesonJamo67":
        raise HTTPException(403, "Cannot disable master admin key.")
    LICENSES[target_key]["active"] = not LICENSES[target_key]["active"]
    return JSONResponse({"success": True})

@app.post("/api/admin/delete")
async def admin_delete(request: Request):
    data = await request.json()
    admin_key = data.get("admin_key", "")
    target_key = data.get("target_key", "")
    if not check_admin(admin_key):
        raise HTTPException(403, "Admin access required.")
    if target_key not in LICENSES:
        raise HTTPException(404, "Key not found.")
    if target_key == "AyoitsjamesonJamo67":
        raise HTTPException(403, "Cannot delete master admin key.")
    del LICENSES[target_key]
    return JSONResponse({"success": True})

@app.post("/api/admin/add")
async def admin_add(request: Request):
    data = await request.json()
    admin_key = data.get("admin_key", "")
    new_key = data.get("new_key", "").strip()
    restrictions = data.get("restrictions", "").strip()
    if not check_admin(admin_key):
        raise HTTPException(403, "Admin access required.")
    if not new_key:
        raise HTTPException(400, "Key cannot be empty.")
    if new_key in LICENSES:
        raise HTTPException(400, "Key already exists.")
    LICENSES[new_key] = {
        "admin": False,
        "active": True,
        "used_by": None,
        "last_active": None,
        "restrictions": restrictions,
        "created": datetime.now().isoformat()
    }
    return JSONResponse({"success": True})
