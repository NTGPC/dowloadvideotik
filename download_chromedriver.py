#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download ChromeDriver for current Chrome version
"""
import subprocess
import requests
import zipfile
import os
import shutil

def get_chrome_version():
    """Get installed Chrome version"""
    try:
        result = subprocess.run(
            ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
            capture_output=True,
            text=True
        )
        version = result.stdout.split()[-1]
        major_version = version.split('.')[0]
        return major_version
    except:
        print("Không thể lấy Chrome version, dùng version mặc định 131")
        return "131"

def download_chromedriver(version):
    """Download ChromeDriver for Windows"""
    print(f"🔽 Đang tải ChromeDriver cho Chrome {version}...")
    
    # ChromeDriver download URL for Chrome 115+
    if int(version) >= 115:
        # New ChromeDriver URL structure
        url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}.0.6778.204/win64/chromedriver-win64.zip"
    else:
        url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{version}"
        response = requests.get(url)
        full_version = response.text.strip()
        url = f"https://chromedriver.storage.googleapis.com/{full_version}/chromedriver_win32.zip"
    
    # Download
    response = requests.get(url)
    
    if response.status_code != 200:
        # Try alternative - latest stable
        print("⚠️ Không tìm thấy version chính xác, dùng version ổn định nhất...")
        url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
        response = requests.get(url)
        data = response.json()
        download_url = data['channels']['Stable']['downloads']['chromedriver'][0]['url']  # Windows 64-bit
        response = requests.get(download_url)
    
    # Save and extract
    zip_path = "chromedriver.zip"
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    
    print("📦 Đang giải nén...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(".")
    
    # Move chromedriver.exe to current directory
    for root, dirs, files in os.walk("."):
        for file in files:
            if file == "chromedriver.exe":
                source = os.path.join(root, file)
                shutil.move(source, "./chromedriver.exe")
                break
    
    # Cleanup
    os.remove(zip_path)
    for item in os.listdir("."):
        if "chromedriver-" in item and os.path.isdir(item):
            shutil.rmtree(item)
    
    print("✅ ChromeDriver đã sẵn sàng tại: chromedriver.exe")

if __name__ == "__main__":
    chrome_version = get_chrome_version()
    print(f"📌 Chrome version: {chrome_version}")
    download_chromedriver(chrome_version)
