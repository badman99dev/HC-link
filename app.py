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
# HubCloud ka current working domain (Change if needed)
HUB_DOMAIN = "https://hubcloud.fyi" 

# --- 🛠️ ROBUST SESSION ---
def create_robust_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 104])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

# --- 🧠 CORE LOGIC: ID to DIRECT LINK ---
def generate_stream_links(file_id):
    session = create_robust_session()
    logs = []
    links = {"google": None, "pixeldrain": None}
    
    hub_url = f"{HUB_DOMAIN}/drive/{file_id}"
    logs.append(f"[{get_timestamp()}] 🕵️‍♂️ Visiting HubCloud: {hub_url}")

    try:
        # Step 1: HubCloud Page
        time.sleep(random.uniform(0.2, 0.8)) # Tiny delay
        resp = session.get(hub_url, timeout=15)
        
        if resp.status_code != 200:
            logs.append(f"[{get_timestamp()}] ❌ Failed to fetch HubCloud (Status: {resp.status_code})")
            return None, logs
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        generate_btn = soup.find('a', id='download')
        
        if not generate_btn:
            logs.append(f"[{get_timestamp()}] ❌ 'Generate Link' button not found. Invalid ID?")
            return None, logs
            
        next_url = generate_btn['href']
        logs.append(f"[{get_timestamp()}] ✅ Token Generated. Bypassing GamerXYT...")

        # Step 2: GamerXYT (With Referer)
        session.headers.update({'Referer': hub_url}) # IMPORTANT
        time.sleep(random.uniform(0.5, 1.2)) # Anti-ban delay
        
        resp2 = session.get(next_url, timeout=15)
        if resp2.status_code != 200:
            logs.append(f"[{get_timestamp()}] ❌ GamerXYT Failed (Status: {resp2.status_code})")
            return None, logs
            
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        
        # A. Find Google Link
        vd_tag = soup2.find('a', id='vd')
        if vd_tag:
            links['google'] = vd_tag['href']
            logs.append(f"[{get_timestamp()}] 🔥 Google 10Gbps Link Found!")
        else:
            logs.append(f"[{get_timestamp()}] ⚠️ Google Link not found in source.")

        # B. Find PixelDrain
        for tag in soup2.find_all(['iframe', 'a']):
            src = tag.get('src') or tag.get('href')
            if src and 'pixeldrain' in src:
                # Clean URL
                if 'embed' in src:
                    # https://pixeldrain.com/u/xxxx?embed -> https://pixeldrain.com/api/file/xxxx
                    clean_id = src.split('/u/')[1].split('?')[0]
                    links['pixeldrain'] = f"https://pixeldrain.com/api/file/{clean_id}"
                elif '/u/' in src:
                    clean_id = src.split('/u/')[1]
                    links['pixeldrain'] = f"https://pixeldrain.com/api/file/{clean_id}"
                
                logs.append(f"[{get_timestamp()}] 🐢 PixelDrain Link Found!")
                break
        
        return links, logs

    except Exception as e:
        logs.append(f"[{get_timestamp()}] 💥 System Error: {str(e)}")
        return None, logs

# --- 🌐 ROUTES ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    file_id = data.get('id')
    
    if not file_id:
        return jsonify({"error": "ID Missing"}), 400
        
    links, logs = generate_stream_links(file_id)
    
    return jsonify({
        "status": "success" if links else "failed",
        "data": links,
        "logs": logs
    })

# --- 🖥️ UI TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stream Generator Lab 🧪</title>
    <style>
        body { background-color: #0d1117; color: #00ff41; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; border-bottom: 2px solid #30363d; padding-bottom: 10px; color: #eebb0e; }
        
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 12px; background: #161b22; border: 1px solid #30363d; color: #fff; border-radius: 5px; font-family: inherit; font-size: 16px; }
        button { padding: 12px 25px; background: #238636; border: none; color: white; font-weight: bold; cursor: pointer; border-radius: 5px; }
        button:hover { background: #2ea043; }
        button:disabled { background: #555; }

        .panel { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
        .logs { height: 200px; overflow-y: auto; font-size: 13px; background: #000; padding: 10px; border-radius: 5px; white-space: pre-wrap; color: #8b949e; }
        .log-entry.success { color: #00ff41; }
        .log-entry.error { color: #ff6b6b; }

        .result-box { display: flex; flex-direction: column; gap: 10px; }
        .link-card { background: #0d1117; border: 1px solid #30363d; padding: 15px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .link-card h4 { margin: 0; color: #58a6ff; }
        .link-card a { background: #1f6feb; color: white; text-decoration: none; padding: 8px 15px; border-radius: 4px; font-size: 14px; }
        .link-card a.copy { background: #238636; margin-left: 5px; cursor: pointer;}
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Stream Link Generator</h1>
        
        <div class="input-group">
            <input type="text" id="idInput" placeholder="Enter HubCloud ID (e.g. p1zc1n0dfqhd0ad)" value="">
            <button id="genBtn" onclick="generateLink()">GENERATE</button>
        </div>

        <div class="panel">
            <h3 style="margin-top:0; color:#58a6ff;">📟 Server Logs</h3>
            <div class="logs" id="logBox">Waiting for input...</div>
        </div>

        <div class="panel hidden" id="resultPanel">
            <h3 style="margin-top:0; color:#eebb0e;">🎉 Generated Links</h3>
            <div class="result-box">
                <div class="link-card" id="googleCard">
                    <div>
                        <h4>⚡ Google 10Gbps (Expire soon)</h4>
                        <small style="color:#8b949e">Direct Stream | No Buffering</small>
                    </div>
                    <div>
                        <a href="#" target="_blank" id="googleBtn">PLAY VIDEO</a>
                    </div>
                </div>

                <div class="link-card" id="pixelCard">
                    <div>
                        <h4>🐢 PixelDrain (Permanent)</h4>
                        <small style="color:#8b949e">Reliable Backup</small>
                    </div>
                    <div>
                        <a href="#" target="_blank" id="pixelBtn">PLAY VIDEO</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function generateLink() {
            const id = document.getElementById('idInput').value.trim();
            const btn = document.getElementById('genBtn');
            const logBox = document.getElementById('logBox');
            const resultPanel = document.getElementById('resultPanel');

            if(!id) return alert("ID kon dalega bhai?");

            btn.disabled = true;
            btn.innerText = "PROCESSING...";
            logBox.innerHTML = "🔄 Initializing Stream Engine...\\n";
            resultPanel.classList.add('hidden');

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                });

                const data = await response.json();

                // Display Logs
                if(data.logs) {
                    logBox.innerHTML = "";
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.textContent = log;
                        if(log.includes('❌')) div.classList.add('error');
                        if(log.includes('🔥') || log.includes('✅')) div.classList.add('success');
                        logBox.appendChild(div);
                    });
                    logBox.scrollTop = logBox.scrollHeight;
                }

                if(data.status === 'success' && data.data) {
                    // Update Google Link
                    const gBtn = document.getElementById('googleBtn');
                    if(data.data.google) {
                        gBtn.href = data.data.google;
                        gBtn.style.display = 'inline-block';
                        gBtn.innerText = "PLAY (10Gbps)";
                    } else {
                        gBtn.style.display = 'none';
                    }

                    // Update Pixel Link
                    const pBtn = document.getElementById('pixelBtn');
                    if(data.data.pixeldrain) {
                        pBtn.href = data.data.pixeldrain;
                        pBtn.style.display = 'inline-block';
                    } else {
                        pBtn.style.display = 'none';
                    }

                    resultPanel.classList.remove('hidden');
                } else {
                    logBox.innerHTML += "\\n❌ Generation Failed. Check ID or Server Logs.";
                }

            } catch (error) {
                logBox.innerHTML += `\\n❌ CLIENT ERROR: ${error.message}`;
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
