# 🎬 TikTok Video Link Scraper

Tool Python để **tự động lấy link video và số lượt xem** từ profile TikTok, xuất ra file Excel.

## ✨ Tính năng

✅ **2 phương thức**: Selenium (dùng Chrome đã login) & Playwright (bypass bot tốt hơn)  
✅ **Tự động login**: Lưu session Chrome, không cần đăng nhập lại  
✅ **Lấy link video đầy đủ**: Không bị rút gọn thành link profile  
✅ **Xuất Excel**: File `.xlsx` với STT, Link, Views  
✅ **Bypass bot detection**: Dùng undetected-chromedriver + Playwright stealth  

---

## 📋 Yêu cầu hệ thống

- **Windows 10/11**
- **Python 3.7+**
- **Google Chrome** (phiên bản mới nhất)

---

## 🚀 Cài đặt

### Bước 1: Clone repository
```bash
git clone https://github.com/NTGPC/dowloadvideotik.git
cd dowloadvideotik
```

### Bước 2: Tạo virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Bước 3: Cài đặt dependencies

**CHỌN 1 TRONG 2 CÁCH:**

#### 🔵 Cách 1: Dùng Selenium (Khuyến nghị cho người mới)
```bash
pip install -r requirements.txt
```

#### 🟢 Cách 2: Dùng Playwright (Bypass bot tốt hơn)
Chạy file: **`SETUP_PLAYWRIGHT.bat`**

Hoặc thủ công:
```bash
pip install playwright pandas openpyxl
playwright install chromium
```

---

## 🎯 Cách sử dụng

### 🔵 Phương thức 1: Selenium (Chrome đã login)

#### Lần đầu tiên:
1. **Đóng tất cả Chrome**
2. Chạy file: **`CHAY.bat`**
3. Chrome sẽ tự mở → **Đăng nhập TikTok**
4. Nhấn **ENTER** trong CMD
5. Nhập username TikTok (VD: `xoaingotaudio`)
6. Đợi → File Excel sẽ xuất hiện trong thư mục

#### Lần sau:
1. Chạy: **`CHAY.bat`**
2. Chrome mở (đã login sẵn)
3. Nhấn **ENTER**
4. Nhập username → Xong!

**File chạy:** `CHAY.bat` hoặc `RUN_ALL.bat`

---

### 🟢 Phương thức 2: Playwright (Không cần login thủ công)

1. Chạy file: **`CHAY_PLAYWRIGHT.bat`**
2. Nhập username TikTok (VD: `xoaingotaudio`)
3. Đợi → File Excel xuất hiện

**Ưu điểm:** 
- Bypass bot detection tốt hơn
- Không cần Chrome profile riêng
- Headless mode (có thể chạy ngầm)

---

## 📂 Kết quả

File Excel: **`tiktok_videos_YYYYMMDD_HHMMSS.xlsx`**

**Cấu trúc:**

| STT | Link | Views |
|-----|------|-------|
| 1 | https://www.tiktok.com/@xoaingotaudio/video/7601025258388213010 | 47000 |
| 2 | https://www.tiktok.com/@xoaingotaudio/video/7600655160645258512 | 2807 |

---

## ⚠️ Lưu ý quan trọng

### ✅ Link đầy đủ, không bị rút gọn
Tool này lấy **link video đầy đủ** (có `/video/[ID]`), không phải link profile.

**Đúng:** `https://www.tiktok.com/@username/video/1234567890`  
**Sai:** `https://www.tiktok.com/@username/`

### 🔄 Nếu lỗi hoặc bị block IP
- **Selenium:** Xóa thư mục `tiktok_scraper_profile` và chạy lại
- **Playwright:** Đợi vài phút rồi thử lại (TikTok có rate limit)
- Thử đổi IP hoặc dùng VPN

### 🚫 Không đóng Chrome khi đang chạy
Script cần Chrome mở để lấy dữ liệu.

---

## 📁 Cấu trúc project

```
Tool Getlink tiktok/
├── tiktok_scraper.py           # Script chính (Selenium)
├── tiktok_playwright.py        # Script Playwright
├── CHAY.bat                    # Chạy Selenium
├── CHAY_PLAYWRIGHT.bat         # Chạy Playwright
├── SETUP_PLAYWRIGHT.bat        # Setup Playwright
├── requirements.txt            # Dependencies Selenium
├── requirements_playwright.txt # Dependencies Playwright
├── README.md                   # Hướng dẫn
└── .gitignore                  # Git ignore config
```

---

## 🐛 Troubleshooting

### Lỗi: "Can't parse this link, check video availablity"
➡️ **Nguyên nhân:** Tool lấy được link profile thay vì link video  
➡️ **Giải pháp:** Dùng Playwright (`CHAY_PLAYWRIGHT.bat`) - bypass bot tốt hơn

### Lỗi: "ChromeDriver version mismatch"
➡️ Cập nhật Chrome lên phiên bản mới nhất  
➡️ Hoặc dùng Playwright (không cần ChromeDriver)

### Lỗi: "No videos found"
➡️ Profile TikTok có thể bị private hoặc không có video  
➡️ Kiểm tra xem profile có public không

---

## 📝 License

MIT License - Sử dụng tự do cho mục đích cá nhân và thương mại.

---

## 👨‍💻 Support

Nếu gặp lỗi, tạo [Issue](https://github.com/NTGPC/dowloadvideotik/issues) trên GitHub.

---

## 🎉 Credits

Developed with ❤️ by NTGPC
