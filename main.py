from fastapi import FastAPI, Request, File, Form, UploadFile
from fastapi.responses import HTMLResponse
import httpx
import os
import base64
import json

app = FastAPI()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Helper</title>
<style>
body{background:#0a0a0f;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:20px;}
.card{background:rgba(255,255,255,0.05);backdrop-filter:blur(20px);border-radius:30px;padding:30px;max-width:450px;width:100%;border:1px solid rgba(255,255,255,0.08);}
input,textarea{width:100%;padding:14px;margin:10px 0;border-radius:16px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.04);color:#fff;font-size:16px;outline:none;}
button{width:100%;padding:14px;border-radius:60px;border:none;background:linear-gradient(135deg,#00f0ff,#b000ff);color:#fff;font-weight:bold;font-size:18px;cursor:pointer;}
#response{background:rgba(255,255,255,0.03);border-radius:16px;padding:16px;margin-top:16px;white-space:pre-wrap;min-height:60px;}
</style>
</head>
<body>
<div class="card">
<h2 style="text-align:center;">AI Assistant</h2>
<input id="key" placeholder="License key" value="TEST123">
<textarea id="prompt" rows="4" placeholder="Ask anything...">Hello</textarea>
<button onclick="ask()">Send</button>
<div id="response">Ready.</div>
</div>
<script>
async function ask(){
  const key = document.getElementById('key').value;
  const prompt = document.getElementById('prompt').value;
  const res = document.getElementById('response');
  res.textContent = 'Thinking...';
  try{
    const r = await fetch('/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({key:key, prompt:prompt})
    });
    const data = await r.json();
    res.textContent = data.reply || 'No reply';
  }catch(e){
    res.textContent = 'Error: ' + e.message;
  }
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    key = data.get("key", "")
    prompt = data.get("prompt", "")
    
    if key != "TEST123":
        return {"reply": "Invalid key - use TEST123"}
    
    if not GEMINI_KEY:
        return {"reply": "Missing Gemini key - add it in Environment"}
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                reply = result["candidates"][0]["content"]["parts"][0]["text"]
                return {"reply": reply}
            else:
                return {"reply": f"Gemini error: {resp.status_code} - {resp.text}"}
        except Exception as e:
            return {"reply": f"Error: {str(e)}"}
