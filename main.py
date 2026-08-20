from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
import os
import secrets
import time
from datetime import datetime

app = FastAPI()

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

# --- LICENSE DATABASE ---
LICENSES = {}

def generate_license_key():
    return f"license-key-{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6))}"

for _ in range(99):
    key = generate_license_key()
    LICENSES[key] = {"admin": False, "active": True, "used_by": None, "last_active": None, "restrictions": ""}

ADMIN_KEY = "AyoitsjamesonJamo67"
LICENSES[ADMIN_KEY] = {"admin": True, "active": True, "used_by": None, "last_active": None, "restrictions": ""}

def update_last_active(key, username="anonymous"):
    if key in LICENSES:
        LICENSES[key]["used_by"] = username
        LICENSES[key]["last_active"] = datetime.now().isoformat()

# --- SIMPLE HTML (no Earth, but clean and works) ---
HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jamo's OP AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a14;color:#fff;font-family:system-ui,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:16px}
.card{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border-radius:32px;padding:30px;max-width:500px;width:100%;border:1px solid rgba(255,255,255,0.06)}
h1{font-size:2rem;font-weight:800;background:linear-gradient(135deg,#00f0ff,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;margin-bottom:4px}
.sub{text-align:center;color:#94a3b8;font-size:0.9rem;margin-bottom:24px}
input,textarea{width:100%;padding:14px 18px;border-radius:60px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.03);color:#fff;font-size:1rem;outline:none;margin-top:10px}
input:focus,textarea:focus{border-color:#00f0ff;box-shadow:0 0 30px rgba(0,240,255,0.1)}
button{width:100%;padding:14px;border-radius:60px;border:none;background:linear-gradient(135deg,#00f0ff,#a855f7);color:#fff;font-weight:700;font-size:1.1rem;cursor:pointer;margin-top:12px;transition:transform 0.15s}
button:active{transform:scale(0.97)}
#response{background:rgba(255,255,255,0.03);border-radius:16px;padding:16px;margin-top:16px;min-height:50px;white-space:pre-wrap}
#admin-panel{display:none;margin-top:20px;background:rgba(255,255,255,0.03);border-radius:16px;padding:16px;max-height:300px;overflow-y:auto}
#admin-panel.open{display:block}
table{width:100%;font-size:0.7rem;border-collapse:collapse}
th{text-align:left;color:#94a3b8;padding:4px}
td{padding:4px;border-bottom:1px solid rgba(255,255,255,0.03)}
.status-online{color:#4ade80}
.status-offline{color:#94a3b8}
.action-btn{background:none;border:1px solid rgba(255,255,255,0.1);color:#fff;padding:2px 10px;border-radius:30px;font-size:0.6rem;cursor:pointer}
.action-btn.danger{border-color:rgba(248,113,113,0.3);color:#f87171}
.add-area{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap}
.add-area input{flex:1;padding:6px 12px;border-radius:40px;font-size:0.8rem;margin:0}
.add-area button{padding:6px 16px;border-radius:40px;font-size:0.8rem;margin:0;width:auto}
.admin-badge{display:inline-block;background:rgba(0,240,255,0.12);padding:2px 14px;border-radius:40px;font-size:0.7rem;border:1px solid rgba(0,240,255,0.2);color:#00f0ff;cursor:pointer;margin-top:8px}
.msg{background:rgba(255,255,255,0.03);border-radius:16px;padding:12px 16px;margin-bottom:8px}
.msg.user{background:rgba(0,240,255,0.08);border-left:3px solid #00f0ff}
.msg.ai{background:rgba(168,85,247,0.08);border-left:3px solid #a855f7}
#typing{display:none;color:#94a3b8;padding:8px 0}
#input-bar{display:flex;gap:10px;margin-top:12px}
#input-bar input{flex:1;margin:0}
#input-bar button{width:auto;padding:14px 24px;margin:0}
#key-display{font-size:0.65rem;opacity:0.4;text-align:center;margin-top:4px}
</style>
</head>
<body>
<div class="card">
  <h1>⚡ Jamo's OP AI</h1>
  <div class="sub">Unrestricted • Limitless</div>

  <div id="login-area">
    <input id="license-input" placeholder="Enter license key..." autofocus>
    <button id="login-btn">Unlock Access</button>
    <div id="login-error" style="color:#f87171;font-size:0.9rem;margin-top:8px;min-height:20px"></div>
  </div>

  <div id="chat-area" style="display:none">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
      <span style="font-weight:700;background:linear-gradient(135deg,#00f0ff,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent">⚡ Jamo AI</span>
      <span id="key-display"></span>
      <span id="admin-toggle" class="admin-badge" style="display:none">🛠 Admin</span>
    </div>
    <div id="messages" style="max-height:50vh;overflow-y:auto;margin-top:12px">
      <div class="msg ai">Welcome. Ask anything — no limits.</div>
    </div>
    <div id="typing">⏳ Thinking...</div>
    <div id="admin-panel">
      <h4 style="color:#00f0ff;margin:8px 0">🔐 License Control</h4>
      <div class="add-area">
        <input id="new-key" placeholder="New key...">
        <input id="new-restrict" placeholder="Restrictions">
        <button id="add-key-btn">➕ Add</button>
      </div>
      <div style="overflow-x:auto"><table><thead><tr><th>Key</th><th>Status</th><th>User</th><th>Action</th></tr></thead><tbody id="admin-table"></tbody></table></div>
    </div>
    <div id="input-bar">
      <input id="chat-input" placeholder="Ask anything...">
      <button id="send-btn">Send</button>
    </div>
  </div>
</div>

<script>
let currentKey = null, isAdmin = false;

const loginArea = document.getElementById('login-area');
const chatArea = document.getElementById('chat-area');
const licenseInput = document.getElementById('license-input');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const messages = document.getElementById('messages');
const typing = document.getElementById('typing');
const keyDisplay = document.getElementById('key-display');
const adminToggle = document.getElementById('admin-toggle');
const adminPanel = document.getElementById('admin-panel');
const adminTable = document.getElementById('admin-table');
const newKeyInput = document.getElementById('new-key');
const newRestrict = document.getElementById('new-restrict');
const addKeyBtn = document.getElementById('add-key-btn');

async function login() {
  const key = licenseInput.value.trim();
  if (!key) { loginError.textContent = 'Enter a key.'; return; }
  loginError.textContent = 'Checking...';
  try {
    const r = await fetch('/api/login', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key}) });
    const data = await r.json();
    if (r.ok && data.valid) {
      currentKey = key; isAdmin = data.admin || false;
      loginArea.style.display = 'none';
      chatArea.style.display = 'block';
      keyDisplay.textContent = key.length > 16 ? key.slice(0,14)+'...' : key;
      if (isAdmin) { adminToggle.style.display = 'inline-block'; adminToggle.textContent = '🛠 Admin'; loadAdmin(); }
      addMessage('ai', data.restrictions ? '⚠️ Restricted: '+data.restrictions : '🔓 Full access.');
      loginError.textContent = '';
    } else {
      loginError.textContent = data.error || 'Invalid key.';
    }
  } catch(e) { loginError.textContent = 'Server error.'; }
}

loginBtn.onclick = login;
licenseInput.onkeydown = e => { if(e.key==='Enter') login(); };

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = '';
  addMessage('user', text);
  typing.style.display = 'block';
  try {
    const r = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key:currentKey, prompt:text}) });
    const data = await r.json();
    typing.style.display = 'none';
    addMessage('ai', r.ok ? (data.reply || 'No reply.') : ('⚠️ Error: '+data.error));
  } catch(e) { typing.style.display = 'none'; addMessage('ai', '⚠️ Network error.'); }
}

sendBtn.onclick = sendMessage;
chatInput.onkeydown = e => { if(e.key==='Enter') sendMessage(); };

function addMessage(type, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + type;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

adminToggle.onclick = () => {
  if (adminPanel.classList.contains('open')) { adminPanel.classList.remove('open'); }
  else { adminPanel.classList.add('open'); loadAdmin(); }
};

async function loadAdmin() {
  if (!isAdmin) return;
  try {
    const r = await fetch('/api/admin/keys', { headers:{'X-Admin-Key':currentKey} });
    const data = await r.json();
    if (r.ok && data.keys) renderTable(data.keys);
  } catch(e) {}
}

function renderTable(keys) {
  let html = '';
  const now = Date.now();
  for (const [k, info] of Object.entries(keys)) {
    const online = info.last_active && (now - new Date(info.last_active).getTime() < 60000);
    const status = info.active ? (online ? '🟢 Online' : '⚪ Inactive') : '🔴 Disabled';
    const cls = info.active ? (online ? 'status-online' : 'status-offline') : 'status-offline';
    html += `<tr><td style="max-width:80px;overflow:hidden;text-overflow:ellipsis">${k}</td><td class="${cls}">${status}</td><td>${info.used_by||'—'}</td><td>
      <button class="action-btn" onclick="toggleKey('${k}')">${info.active?'Disable':'Enable'}</button>
      ${k!=='AyoitsjamesonJamo67'?`<button class="action-btn danger" onclick="deleteKey('${k}')">Delete</button>`:''}
    </td></tr>`;
  }
  adminTable.innerHTML = html;
}

window.toggleKey = async function(k) {
  if (!isAdmin) return;
  await fetch('/api/admin/toggle', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({admin_key:currentKey, target_key:k}) });
  loadAdmin();
};
window.deleteKey = async function(k) {
  if (!isAdmin || k==='AyoitsjamesonJamo67') return;
  if (!confirm('Delete?')) return;
  await fetch('/api/admin/delete', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({admin_key:currentKey, target_key:k}) });
  loadAdmin();
};
addKeyBtn.onclick = async () => {
  if (!isAdmin) return;
  const k = newKeyInput.value.trim(), r = newRestrict.value.trim();
  if (!k) return;
  await fetch('/api/admin/add', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({admin_key:currentKey, new_key:k, restrictions:r}) });
  newKeyInput.value=''; newRestrict.value=''; loadAdmin();
};
setInterval(() => { if (isAdmin && adminPanel.classList.contains('open')) loadAdmin(); }, 15000);
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    key = data.get("key", "").strip()
    info = LICENSES.get(key)
    if not info:
        return JSONResponse({"valid": False, "error": "Key not found."})
    if not info.get("active"):
        return JSONResponse({"valid": False, "error": "Key disabled."})
    update_last_active(key, "web-user")
    return JSONResponse({"valid": True, "admin": info.get("admin", False), "restrictions": info.get("restrictions", "")})

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    key = data.get("key", "").strip()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return JSONResponse({"error": "Empty prompt."}, status_code=400)
    info = LICENSES.get(key)
    if not info or not info.get("active"):
        return JSONResponse({"error": "Invalid key."}, status_code=403)
    restrictions = info.get("restrictions", "")
    if restrictions:
        prompt = f"[RESTRICTION: {restrictions}] {prompt}"
    update_last_active(key, "chat-user")
    if not GROQ_KEY:
        return JSONResponse({"error": "Groq key missing."}, status_code=500)
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama3-70b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 2048}
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return JSONResponse({"reply": resp.json()["choices"][0]["message"]["content"]})
            return JSONResponse({"error": f"Groq error {resp.status_code}"}, status_code=500)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

def check_admin(request_key):
    info = LICENSES.get(request_key)
    return info and info.get("admin", False) and info.get("active", True)

@app.get("/api/admin/keys")
async def admin_list_keys(request: Request):
    admin_key = request.headers.get("X-Admin-Key", "")
    if not check_admin(admin_key):
        raise HTTPException(403, "Admin required.")
    return JSONResponse({"keys": LICENSES})

@app.post("/api/admin/toggle")
async def admin_toggle(request: Request):
    data = await request.json()
    admin_key = data.get("admin_key", "")
    target_key = data.get("target_key", "")
    if not check_admin(admin_key) or target_key not in LICENSES:
        raise HTTPException(403, "Denied.")
    if target_key == "AyoitsjamesonJamo67":
        raise HTTPException(403, "Cannot disable master.")
    LICENSES[target_key]["active"] = not LICENSES[target_key]["active"]
    return JSONResponse({"success": True})

@app.post("/api/admin/delete")
async def admin_delete(request: Request):
    data = await request.json()
    admin_key = data.get("admin_key", "")
    target_key = data.get("target_key", "")
    if not check_admin(admin_key) or target_key not in LICENSES:
        raise HTTPException(403, "Denied.")
    if target_key == "AyoitsjamesonJamo67":
        raise HTTPException(403, "Cannot delete master.")
    del LICENSES[target_key]
    return JSONResponse({"success": True})

@app.post("/api/admin/add")
async def admin_add(request: Request):
    data = await request.json()
    admin_key = data.get("admin_key", "")
    new_key = data.get("new_key", "").strip()
    restrictions = data.get("restrictions", "").strip()
    if not check_admin(admin_key) or not new_key or new_key in LICENSES:
        raise HTTPException(400, "Invalid.")
    LICENSES[new_key] = {"admin": False, "active": True, "used_by": None, "last_active": None, "restrictions": restrictions}
    return JSONResponse({"success": True})
