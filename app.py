from flask import Flask, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import re
import os
import time
from datetime import datetime

app = Flask(__name__)

# --- 🎭 HEADERS (Sudmas Mode) ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

session = requests.Session()
session.headers.update(HEADERS)

# --- 🛠️ HELPER FUNCTIONS ---

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def get_soup(url, referer=None):
    try:
        headers = HEADERS.copy()
        if referer: headers['Referer'] = referer
        resp = session.get(url, headers=headers, timeout=20) # Timeout increased slightly
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, 'html.parser'), resp.status_code
        return None, resp.status_code
    except Exception as e:
        return None, str(e)

def process_chain(task_data):
    """
    Ek Unique Chain ko process karta hai.
    Target: HubDrive Space -> HubCloud ID
    """
    quality = task_data['quality']
    start_link = task_data['url'] 
    logs = []
    
    logs.append(f"[{get_timestamp()}] ⏳ [{quality}] Processing Chain: {start_link} ...")

    # --- STEP 1: GyaniGurus ---
    soup_gg, status = get_soup(start_link)
    if not soup_gg: 
        logs.append(f"[{get_timestamp()}] ❌ [{quality}] Failed to fetch GyaniGurus (Status: {status})")
        return None, logs

    hubdrive_link = None
    
    # 🎯 FIX: Strictly find 'hubdrive.space'
    # Page par bohot links hote hain, hame specific domain chahiye
    all_links = soup_gg.find_all('a', href=True)
    for a in all_links:
        href = a['href']
        # Hum specifically 'hubdrive.space' dhund rahe hain
        if 'hubdrive.space' in href:
            hubdrive_link = href
            break
            
    if not hubdrive_link:
        # Fallback: Agar space nahi mila, to general hubdrive check karo (but warn logs)
        # logs.append(f"[{get_timestamp()}] ⚠️ [{quality}] 'hubdrive.space' not found, checking alternatives...")
        for a in all_links:
            href = a['href']
            if 'hubdrive' in href and 'drivehub.cfd' not in href: # Avoid CFD garbage
                hubdrive_link = href
                break
    
    if not hubdrive_link: 
        logs.append(f"[{get_timestamp()}] ❌ [{quality}] Target HubDrive Link NOT found on Gyani.")
        return None, logs
    
    logs.append(f"[{get_timestamp()}] ✅ [{quality}] HubDrive Found: {hubdrive_link}")

    # --- STEP 2: HubDrive ---
    soup_hd, status = get_soup(hubdrive_link, referer=start_link)
    if not soup_hd: 
        logs.append(f"[{get_timestamp()}] ❌ [{quality}] Failed to fetch HubDrive (Status: {status})")
        return None, logs

    hubcloud_link = None
    for a in soup_hd.find_all('a', href=True):
        href = a['href']
        text = a.get_text().lower()
        # HubCloud dhundne ka logic (Text or Link)
        if ('hubcloud' in href or 'hubcloud' in text) and 'drive' in href:
            hubcloud_link = href
            break
            
    if not hubcloud_link: 
        logs.append(f"[{get_timestamp()}] ❌ [{quality}] HubCloud Link NOT found on HubDrive.")
        return None, logs

    logs.append(f"[{get_timestamp()}] ✅ [{quality}] HubCloud Found: {hubcloud_link}")

    # --- STEP 3: Extract ID ---
    # Regex to catch ID from: https://hubcloud.foo/drive/ID_HERE
    match = re.search(r'\/drive\/([a-zA-Z0-9]+)', hubcloud_link)
    if match:
        final_id = match.group(1)
        logs.append(f"[{get_timestamp()}] 🔥 [{quality}] ID EXTRACTED: {final_id}")
        return {
            'quality': quality,
            'hub_id': final_id,
            'hub_link': hubcloud_link
        }, logs
    else:
        logs.append(f"[{get_timestamp()}] ⚠️ [{quality}] Link found but Regex failed for ID.")
        return None, logs

# --- 🌐 WEB ROUTES ---

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scrape', methods=['POST'])
def scrape_movie():
    data = request.json
    target_url = data.get('url')
    
    if not target_url:
        return jsonify({"error": "URL missing"}), 400

    main_logs = []
    main_logs.append(f"[{get_timestamp()}] 🚀 HEIST STARTED on: {target_url}")

    soup, status = get_soup(target_url)
    if not soup:
        return jsonify({
            "error": "Failed to fetch DesireMovies page", 
            "logs": [f"❌ Critical Error: Could not load DesireMovies page (Status: {status})"]
        }), 500

    tasks = []
    seen_urls = set() # 🧠 DUPLICATE CHECKER
    
    # DesireMovies Links Dhundo
    # Hum sare links check karenge (G-DRIVE, DOWNLOAD, etc.)
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text().strip().upper()
        
        # Link Filter: GyaniGurus/Shorteners
        if ('gyanigurus' in href or 'gurl' in href) and ('DOWNLOAD' in text or 'G-DRIVE' in text):
            
            # 🛑 DEDUPLICATION LOGIC
            # Agar ye URL pehle dikh chuka hai, to skip karo
            if href in seen_urls:
                continue
            
            seen_urls.add(href) # Mark as seen

            # Quality Guessing
            quality = "Unknown"
            prev = link.find_previous(['p', 'h3', 'h4', 'strong', 'span'])
            if prev:
                prev_text = prev.get_text().strip()
                if '480p' in prev_text: quality = "480p"
                elif '720p' in prev_text: quality = "720p"
                elif '1080p' in prev_text: quality = "1080p"
                elif '4k' in prev_text or '2160p' in prev_text: quality = "4K"
            
            tasks.append({'quality': quality, 'url': href})

    main_logs.append(f"[{get_timestamp()}] 🔍 Scanned page. Found {len(tasks)} UNIQUE chains to process.")

    results = []
    all_thread_logs = []

    # Multi-threading (5 Workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(process_chain, task): task for task in tasks}
        
        for future in concurrent.futures.as_completed(future_to_url):
            data, logs = future.result()
            all_thread_logs.extend(logs)
            if data: 
                results.append(data)

    main_logs.extend(all_thread_logs)
    main_logs.append(f"[{get_timestamp()}] 🏁 Heist Completed. Total IDs Found: {len(results)}")

    return jsonify({
        "status": "success",
        "results": results,
        "logs": main_logs
    })

# --- 🖥️ UI TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HubCloud Heist Terminal 2.0</title>
    <style>
        body {
            background-color: #0d1117;
            color: #00ff41;
            font-family: 'Courier New', Courier, monospace;
            margin: 0;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 {
            text-align: center;
            border-bottom: 2px solid #30363d;
            padding-bottom: 10px;
            color: #eebb0e;
        }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input {
            flex: 1; padding: 12px; background: #161b22;
            border: 1px solid #30363d; color: #fff; border-radius: 5px;
        }
        button {
            padding: 12px 25px; background: #238636; border: none;
            color: white; font-weight: bold; cursor: pointer; border-radius: 5px;
        }
        button:hover { background: #2ea043; }
        button:disabled { background: #555; }
        
        .panel {
            background: #161b22; border: 1px solid #30363d;
            border-radius: 10px; padding: 15px; margin-bottom: 20px;
        }
        .logs {
            height: 350px; overflow-y: auto; font-size: 13px;
            white-space: pre-wrap; color: #c9d1d9;
            background: #000; padding: 10px; border-radius: 5px;
        }
        .log-entry { margin-bottom: 4px; border-bottom: 1px solid #222; }
        .log-entry.error { color: #ff6b6b; }
        .log-entry.success { color: #00ff41; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #30363d; padding: 10px; text-align: left; }
        th { background: #21262d; color: #58a6ff; }
        td { color: #fff; }
        code { background: #222; padding: 2px 5px; border-radius: 3px; color: #eebb0e; }
        a { color: #58a6ff; text-decoration: none; }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕵️‍♂️ HubCloud Heist Terminal 2.0</h1>
        
        <div class="input-group">
            <input type="text" id="urlInput" placeholder="Enter DesireMovies Link..." value="https://desiremovies.group/avengers-endgame-full-movie-download/">
            <button id="startBtn" onclick="startHeist()">EXTRACT IDs</button>
        </div>

        <div class="panel">
            <h3 style="margin-top:0; color:#58a6ff;">📟 Live System Logs</h3>
            <div class="logs" id="logBox">System Ready...</div>
        </div>

        <div class="panel hidden" id="resultPanel">
            <h3 style="margin-top:0; color:#00ff41;">💎 Extraction Results</h3>
            <table id="resultTable">
                <thead>
                    <tr>
                        <th>Quality</th>
                        <th>Extracted ID</th>
                        <th>HubLink</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <script>
        async function startHeist() {
            const url = document.getElementById('urlInput').value;
            const btn = document.getElementById('startBtn');
            const logBox = document.getElementById('logBox');
            const resultPanel = document.getElementById('resultPanel');
            const tbody = document.querySelector('#resultTable tbody');

            if(!url) return alert("URL Missing!");

            btn.disabled = true;
            btn.innerText = "RUNNING...";
            logBox.innerHTML = "🔄 Initializing Agents...\\n";
            resultPanel.classList.add('hidden');
            tbody.innerHTML = "";

            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();

                // Display Logs
                logBox.innerHTML = "";
                if(data.logs) {
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.textContent = log;
                        if(log.includes('❌') || log.includes('⚠️')) div.classList.add('error');
                        if(log.includes('✅') || log.includes('🔥')) div.classList.add('success');
                        logBox.appendChild(div);
                    });
                    logBox.scrollTop = logBox.scrollHeight;
                }

                // Display Results
                if(data.results && data.results.length > 0) {
                    data.results.forEach(item => {
                        const row = `<tr>
                            <td><b>${item.quality}</b></td>
                            <td><code>${item.hub_id}</code></td>
                            <td><a href="${item.hub_link}" target="_blank">Open</a></td>
                        </tr>`;
                        tbody.innerHTML += row;
                    });
                    resultPanel.classList.remove('hidden');
                } else {
                    logBox.innerHTML += "\\n❌ Extraction Failed: No Valid Chains Found.";
                }

            } catch (error) {
                logBox.innerHTML += `\\n❌ NETWORK ERROR: ${error.message}`;
            } finally {
                btn.disabled = false;
                btn.innerText = "EXTRACT IDs";
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
