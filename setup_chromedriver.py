#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromeDriver Setup Helper
Auto-downloads the correct ChromeDriver for your Chrome version
"""

import os
import sys
import zipfile
import urllib.request
import json
import subprocess


def get_chrome_version():
    """Get installed Chrome version on Windows"""
    try:
        # Try reading Chrome version from registry
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except:
        try:
            # Fallback: check Chrome executable
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            result = subprocess.run([chrome_path, "--version"], capture_output=True, text=True)
            version = result.stdout.strip().split()[-1]
            return version
        except:
            return None


def download_chromedriver(chrome_version):
    """Download ChromeDriver matching Chrome version"""
    major_version = chrome_version.split('.')[0]
    
    print(f"🔍 Chrome version: {chrome_version}")
    print(f"📦 Major version: {major_version}")
    
    # Get download URL from Chrome for Testing API
    api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    
    try:
        print("🌐 Fetching ChromeDriver download info...")
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read())
        
        # Get ChromeDriver URL for win64
        chromedriver_info = data['channels']['Stable']['downloads']['chromedriver']
        download_url = None
        
        for item in chromedriver_info:
            if item['platform'] == 'win64':
                download_url = item['url']
                break
        
        if not download_url:
            print("❌ Không tìm thấy ChromeDriver cho Windows 64-bit")
            return False
        
        print(f"⬇️ Downloading: {download_url}")
        
        # Create drivers folder
        os.makedirs("drivers", exist_ok=True)
        
        # Download
        zip_path = "drivers/chromedriver.zip"
        urllib.request.urlretrieve(download_url, zip_path)
        
        print("📦 Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("drivers/")
        
        # Remove zip
        os.remove(zip_path)
        
        print("✅ ChromeDriver installed successfully!")
        print(f"📁 Location: {os.path.abspath('drivers')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("="*50)
    print("  ChromeDriver Setup Helper")
    print("="*50)
    print()
    
    chrome_version = get_chrome_version()
    
    if not chrome_version:
        print("❌ Cannot detect Chrome version!")
        print("Please make sure Google Chrome is installed.")
        sys.exit(1)
    
    success = download_chromedriver(chrome_version)
    
    if success:
        print()
        print("="*50)
        print("✨ Setup Complete!")
        print("="*50)
    else:
        print()
        print("❌ Setup Failed!")
        sys.exit(1)
