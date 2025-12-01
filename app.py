import requests
from bs4 import BeautifulSoup
import time
import random

# --- ⚙️ CONFIGURATION ---
# HubCloud ka current domain (ye badalta rahta hai, abhi .fyi ya .foo chal raha hai)
# Recent logs me 'hubcloud.fyi' mila tha, wahi use karte hain.
HUB_DOMAIN = "https://hubcloud.fyi" 

# Test ID (Jo tumne abhi extract ki thi)
TEST_ID = "p1zc1n0dfqhd0ad"

# --- 🎭 SUDMAS HEADERS ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def generate_direct_links(file_id):
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # URL Construct karo
    hub_url = f"{HUB_DOMAIN}/drive/{file_id}"
    
    print(f"🕵️‍♂️ Step 1: Visiting HubCloud [{hub_url}]...")
    
    try:
        # 1. HubCloud Page Fetch
        resp = session.get(hub_url, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Failed to load HubCloud. Status: {resp.status_code}")
            return None
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 'Generate Link' button dhundo (id="download")
        generate_btn = soup.find('a', id='download')
        
        if not generate_btn:
            print("❌ 'Generate Link' button nahi mila. ID galat hai ya Domain change ho gaya.")
            return None
            
        next_url = generate_btn['href']
        print(f"✅ Token Generated: {next_url}")
        
        # ---------------------------------------------------------
        
        # 2. GamerXYT Page (The Magic Step)
        print(f"🕵️‍♂️ Step 2: Bypassing GamerXYT (Applying Referer Trick)...")
        
        # ⚠️ CRITICAL: Referer set karna zaroori hai warna Ads aayenge
        session.headers.update({'Referer': hub_url})
        
        # Thoda delay taaki server ko shak na ho
        time.sleep(random.uniform(0.5, 1.5))
        
        resp2 = session.get(next_url, timeout=15)
        if resp2.status_code != 200:
            print(f"❌ Failed to load GamerXYT. Status: {resp2.status_code}")
            return None
            
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        
        # --- A. Google 10Gbps Link (id="vd") ---
        google_link = None
        vd_tag = soup2.find('a', id='vd')
        if vd_tag:
            google_link = vd_tag['href']
        
        # --- B. PixelDrain Link (Backup) ---
        pixel_link = None
        # Iframe ya direct link check karo
        for tag in soup2.find_all(['iframe', 'a']):
            src = tag.get('src') or tag.get('href')
            if src and 'pixeldrain' in src:
                # Clean link extraction
                if 'embed' in src:
                    src = src.split('?')[0].replace('/u/', '/api/file/') # Convert to direct API
                elif '/u/' in src:
                    src = src.replace('/u/', '/api/file/')
                
                pixel_link = src
                break # Ek mil gaya kaafi hai

        return {
            "google_10gbps": google_link,
            "pixeldrain": pixel_link
        }

    except Exception as e:
        print(f"💥 Error: {e}")
        return None

# --- TEST RUNNER ---
if __name__ == "__main__":
    print(f"🚀 TESTING ID: {TEST_ID}\n")
    
    links = generate_direct_links(TEST_ID)
    
    if links:
        print("\n" + "="*50)
        print("🎉 MISSION SUCCESS! LINKS GENERATED")
        print("="*50)
        
        if links['google_10gbps']:
            print(f"⚡ HIGH SPEED (Google): \n{links['google_10gbps']}\n")
            print("👉 (Note: Ye link turant expire hota hai, ise player me daal kar check karo)")
        else:
            print("❌ Google Link nahi mila.")
            
        if links['pixeldrain']:
            print(f"🐢 BACKUP (PixelDrain): \n{links['pixeldrain']}")
        else:
            print("❌ PixelDrain nahi mila.")
            
        print("="*50)
    else:
        print("\n👎 Failed to generate links.")
