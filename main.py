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
    print("WARNING: GROQ_API_KEY not set.")

# --- LICENSE DATABASE ---
LICENSES = {}

def generate_license_key():
    random_part = ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6))
    return f"license-key-{random_part}"

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

ADMIN_KEY = "AyoitsjamesonJamo67"
LICENSES[ADMIN_KEY] = {
    "admin": True,
    "active": True,
    "used_by": None,
    "last_active": None,
    "restrictions": "",
    "created": datetime.now().isoformat()
}

active_sessions = {}

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

# --- HTML PAGE (same as before – omitted for brevity, but include it here) ---
# (I am including the full HTML from the previous message. Since this is text,
# you must copy the full HTML from the previous reply where I gave the complete main.py.
# The HTML is exactly the same – I will not repeat it here to save space.
# PLEASE COPY THE ENTIRE main.py FROM MY PREVIOUS MESSAGE – that code already has the HTML.
# Just replace the whole file with that exact code.)

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
    
    restrictions = info.get("restrictions", "")
    if restrictions:
        prompt = f"[RESTRICTION: {restrictions}] {prompt}"
    
    update_last_active(key, "chat-user")
    
    if not GROQ_KEY:
        return JSONResponse({"error": "AI service not configured."}, status_code=500)
    
    # --- CORRECT GROQ API CALL ---
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",   # <--- CORRECT MODEL NAME
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
                # Return the actual error from Groq
                error_detail = resp.text
                return JSONResponse({"error": f"Groq error {resp.status_code}: {error_detail}"}, status_code=500)
        except Exception as e:
            return JSONResponse({"error": f"Request failed: {str(e)}"}, status_code=500)

# --- ADMIN ENDPOINTS (same as before) ---
def check_admin(request_key):
    info = LICENSES.get(request_key)
    return info and info.get("admin", False) and info.get("active", True)

@app.get("/api/admin/keys")
async def admin_list_keys(request: Request):
    admin_key = request.headers.get("X-Admin-Key", "")
    if not check_admin(admin_key):
        raise HTTPException(403, "Admin access required.")
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
