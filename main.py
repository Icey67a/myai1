from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import httpx
import os

app = FastAPI()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

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
    
    if not GROQ_KEY:
        return {"reply": "Missing Groq key - add it in Environment"}
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"]
                return {"reply": reply}
            else:
                return {"reply": f"Groq error: {resp.status_code} - {resp.text}"}
        except Exception as e:
            return {"reply": f"Error: {str(e)}"}
