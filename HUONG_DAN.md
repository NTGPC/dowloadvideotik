# HƯỚNG DẪN SỬ DỤNG

## Bước 1: Mở Chrome với debugging (CHỈ LÀM 1 LẦN)

Chạy lệnh này trong PowerShell:
```powershell
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222"
```

Hoặc double-click file: `start_chrome_debug.bat`

## Bước 2: Chạy script

```bash
python tiktok_scraper.py
```

## Bước 3: Nhập username

Khi được hỏi, nhập một trong các dạng sau:
- `@xoaingotaudio`
- `xoaingotaudio`  
- `https://www.tiktok.com/@xoaingotaudio`

## Bước 4: Chờ kết quả

File Excel sẽ được tạo trong thư mục `output/`

---

## LƯU Ý QUAN TRỌNG

⚠️ Chrome PHẢI được mở với `--remote-debugging-port=9222`  
⚠️ MỞ Chrome TRƯỚC khi chạy script  
⚠️ Chỉ cần mở Chrome 1 lần, sau đó chạy script bao nhiêu lần cũng được
