from flask import Flask, request, jsonify, render_template_string
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# --- ⚙️ CONFIGURATION ---
HUB_DOMAIN = "https://hubcloud.fyi" 

def create_robust_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Upgrade-Insecure-Requests': '1',
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def generate_stream_links(file_id):
    session = create_robust_session()
    logs = []
    links = {"google": None, "pixeldrain": None}
    
    hub_url = f"{HUB_DOMAIN}/drive/{file_id}"
    logs.append(f"[{get_timestamp()}] 🕵️‍♂️ Visiting HubCloud: {hub_url}")

    try:
        # Step 1: HubCloud
        time.sleep(random.uniform(0.2, 0.5))
        resp = session.get(hub_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        generate_btn = soup.find('a', id='download')
        if not generate_btn:
            logs.append(f"[{get_timestamp()}] ❌ 'Generate Link' button missing.")
            return None, logs
            
        next_url = generate_btn['href']
        logs.append(f"[{get_timestamp()}] ✅ Token Generated.")

        # Step 2: GamerXYT
        session.headers.update({'Referer': hub_url})
        time.sleep(random.uniform(0.5, 1.0))
        
        resp2 = session.get(next_url, timeout=15)
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        
        # --- A. GOOGLE LINK STRATEGY ---
        google_link = None
        
        # Strategy 1: Hidden ID 'vd' (Fastest)
        vd_tag = soup2.find('a', id='vd')
        if vd_tag:
            google_link = vd_tag['href']
            logs.append(f"[{get_timestamp()}] 🔥 Direct Google Link found (Strategy 1).")
        
        # Strategy 2: Regex in href (Reliable)
        if not google_link:
            g_tag = soup2.find('a', href=re.compile(r'video-downloads\.googleusercontent\.com'))
            if g_tag:
                google_link = g_tag['href']
                logs.append(f"[{get_timestamp()}] 🔥 Google Link found via Regex (Strategy 2).")

        # Strategy 3: Resolve 'pixel.hubcdn.fans' redirect (The "Redirect" Trick)
        if not google_link:
            hubcdn_tag = soup2.find('a', href=re.compile(r'pixel\.hubcdn\.fans'))
            if hubcdn_tag:
                raw_link = hubcdn_tag['href']
                logs.append(f"[{get_timestamp()}] 🕵️‍♂️ Resolving Redirect: {raw_link[:40]}...")
                try:
                    # Request without following redirect to catch the header
                    # IMPORTANT: Referer must be the GamerXYT url (next_url)
                    redir_req = session.get(raw_link, headers={'Referer': next_url}, allow_redirects=False, timeout=10)
                    
                    if 'Location' in redir_req.headers:
                        loc = redir_req.headers['Location']
                        if 'googleusercontent' in loc:
                            google_link = loc
                            logs.append(f"[{get_timestamp()}] 🔥 Redirect Resolved to Google Drive (Strategy 3)!")
                        else:
                            logs.append(f"[{get_timestamp()}] ⚠️ Redirected to: {loc}")
                except Exception as ex:
                    logs.append(f"[{get_timestamp()}] 💥 Redirect Resolution Failed: {str(ex)}")

        if google_link:
            links['google'] = google_link
        else:
            logs.append(f"[{get_timestamp()}] ❌ Failed to extract Google Link.")

        # --- B. PIXELDRAIN ---
        for tag in soup2.find_all(['iframe', 'a']):
            src = tag.get('src') or tag.get('href')
            if src and 'pixeldrain' in src:
                if 'embed' in src:
                    clean_id = src.split('/u/')[1].split('?')[0]
                    links['pixeldrain'] = f"https://pixeldrain.com/api/file/{clean_id}?download"
                elif '/u/' in src:
                    clean_id = src.split('/u/')[1]
                    links['pixeldrain'] = f"https://pixeldrain.com/api/file/{clean_id}?download"
                logs.append(f"[{get_timestamp()}] 🐢 PixelDrain Link Found.")
                break
        
        return links, logs

    except Exception as e:
        logs.append(f"[{get_timestamp()}] 💥 Error: {str(e)}")
        return None, logs

# --- 🌐 ROUTES ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    file_id = data.get('id')
    if not file_id: return jsonify({"error": "ID Missing"}), 400
    links, logs = generate_stream_links(file_id)
    return jsonify({"status": "success" if links else "failed", "data": links, "logs": logs})

# --- UI TEMPLATE (Same as before) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stream Generator v3.0</title>
    <style>
        body { background-color: #0d1117; color: #00ff41; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; border-bottom: 2px solid #30363d; padding-bottom: 10px; color: #eebb0e; }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 12px; background: #161b22; border: 1px solid #30363d; color: #fff; border-radius: 5px; font-size: 16px; }
        button { padding: 12px 25px; background: #238636; border: none; color: white; font-weight: bold; cursor: pointer; border-radius: 5px; }
        button:hover { background: #2ea043; }
        button:disabled { background: #555; }
        .panel { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
        .logs { height: 250px; overflow-y: auto; font-size: 13px; background: #000; padding: 10px; border-radius: 5px; white-space: pre-wrap; color: #8b949e; }
        .log-entry.success { color: #00ff41; }
        .log-entry.error { color: #ff6b6b; }
        .link-card { background: #0d1117; border: 1px solid #30363d; padding: 15px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .link-card h4 { margin: 0; color: #58a6ff; }
        .link-card a { background: #1f6feb; color: white; text-decoration: none; padding: 8px 15px; border-radius: 4px; font-size: 14px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Stream Link Generator</h1>
        <div class="input-group">
            <input type="text" id="idInput" placeholder="Enter HubCloud ID..." value="">
            <button id="genBtn" onclick="generateLink()">GENERATE</button>
        </div>
        <div class="panel">
            <h3 style="margin-top:0; color:#58a6ff;">📟 Server Logs</h3>
            <div class="logs" id="logBox">Waiting for input...</div>
        </div>
        <div class="panel hidden" id="resultPanel">
            <h3 style="margin-top:0; color:#eebb0e;">🎉 Generated Links</h3>
            <div class="link-card" id="googleCard" style="display:none">
                <div><h4>⚡ Google 10Gbps</h4><small style="color:#8b949e">Direct Stream</small></div>
                <a href="#" target="_blank" id="googleBtn">PLAY</a>
            </div>
            <div class="link-card" id="pixelCard" style="display:none">
                <div><h4>🐢 PixelDrain (Direct API)</h4><small style="color:#8b949e">Requires 'Referer' Header</small></div>
                <a href="#" target="_blank" id="pixelBtn">PLAY</a>
            </div>
        </div>
    </div>
    <script>
        async function generateLink() {
            const id = document.getElementById('idInput').value.trim();
            const btn = document.getElementById('genBtn');
            const logBox = document.getElementById('logBox');
            const resultPanel = document.getElementById('resultPanel');
            if(!id) return alert("ID missing!");
            btn.disabled = true;
            btn.innerText = "PROCESSING...";
            logBox.innerHTML = "🔄 Starting...\\n";
            resultPanel.classList.add('hidden');
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                });
                const data = await response.json();
                if(data.logs) {
                    logBox.innerHTML = "";
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.textContent = log;
                        if(log.includes('❌') || log.includes('⚠️')) div.classList.add('error');
                        if(log.includes('🔥') || log.includes('✅')) div.classList.add('success');
                        logBox.appendChild(div);
                    });
                    logBox.scrollTop = logBox.scrollHeight;
                }
                if(data.status === 'success' && data.data) {
                    if(data.data.google) {
                        document.getElementById('googleBtn').href = data.data.google;
                        document.getElementById('googleCard').style.display = 'flex';
                    }
                    if(data.data.pixeldrain) {
                        document.getElementById('pixelBtn').href = data.data.pixeldrain;
                        document.getElementById('pixelCard').style.display = 'flex';
                    }
                    resultPanel.classList.remove('hidden');
                } else {
                    logBox.innerHTML += "\\n❌ Extraction Failed.";
                }
            } catch (error) {
                logBox.innerHTML += `\\n❌ Error: ${error.message}`;
            } finally {
                btn.disabled = false;
                btn.innerText = "GENERATE";
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
