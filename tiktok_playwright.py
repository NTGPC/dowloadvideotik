"""
TIKTOK AUTOMATION - VERSION SUPER HD & MAX SPEED
- Force 1080p/Original Quality.
- Tối ưu tốc độ tải đa luồng.
- Giữ nguyên tên gốc (Full Caption).
"""

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime
import sys
import os
import yt_dlp

# Fix lỗi hiển thị
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

class TikTokUltimateBot:
    def __init__(self):
        self.videos = []
        self.download_folder = "Downloads"
    
    def parse_view_count(self, text):
        try:
            text = text.strip().upper()
            if 'K' in text: return int(float(text.replace('K', '').strip()) * 1000)
            elif 'M' in text: return int(float(text.replace('M', '').strip()) * 1000000)
            elif 'B' in text: return int(float(text.replace('B', '').strip()) * 1000000000)
            else:
                clean_text = ''.join(filter(str.isdigit, text))
                return int(clean_text) if clean_text else 0
        except: return 0

    def download_video_now(self, link, folder_name):
        save_path = os.path.join(self.download_folder, folder_name)
        os.makedirs(save_path, exist_ok=True)

        # === CẤU HÌNH MAX PING CHO DÂN PRO ===
        ydl_opts = {
            # 1. TÊN FILE: Giữ nguyên caption gốc
            'outtmpl': f'{save_path}/%(title)s [%(id)s].%(ext)s',
            'restrictfilenames': False, 
            'windowsfilenames': True,  
            'trim_file_name': 200,

            # 2. CHẤT LƯỢNG: Ưu tiên 1080p -> 720p -> Best
            # Lệnh này ép yt-dlp chọn file to nhất, bitrate cao nhất
            'format': 'bestvideo[height>=1080]+bestaudio/bestvideo+bestaudio/best', 
            
            # 3. TỐC ĐỘ: Tối ưu mạng
            'concurrent_fragment_downloads': 10, # Mở 10 luồng tải cùng lúc
            'buffersize': 1024 * 1024, # Tăng bộ nhớ đệm
            'retries': 10, # Thử lại 10 lần nếu mạng lag
            'fragment_retries': 10,
            
            # 4. KHÁC
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            # Giả lập iPhone để lấy video nét hơn (User Agent Mobile)
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                video_title = info.get('title', 'No_Title')
                ydl.download([link])
                return True, video_title
        except Exception as e:
            # Nếu tải thất bại lần 1, thử lại với format mặc định (fallback)
            try:
                print("   ⚠️ Đang thử lại với format dự phòng...")
                ydl_opts['format'] = 'best' # Fallback xuống best available
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                return True, "Video_Reup_Mode"
            except:
                return False, str(e)

    async def run(self, username):
        url = f"https://www.tiktok.com/@{username}"
        
        async with async_playwright() as p:
            print(f"🚀 BOT SUPER HD ĐANG CHẠY... KÊNH: {username}")
            print("🔧 Đang mở Chrome...")
            
            browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--start-maximized'])
            context = await browser.new_context(
                viewport=None, 
                # Playwright vẫn dùng PC để Bro dễ nhìn
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page = await context.new_page()
            
            try: await page.goto(url, timeout=60000)
            except: pass

            print("\n" + "="*50)
            print("🛑 CHUẨN BỊ TẢI CHẤT LƯỢNG CAO 🛑")
            print("👉 F5 nếu trắng. Kéo Captcha.")
            print("👉 Đợi danh sách video hiện ra.")
            await asyncio.get_event_loop().run_in_executor(None, input, "⌨️  BẤM ENTER ĐỂ CHIẾN (MAX SPEED)...")
            print("="*50 + "\n")
            
            print("📜 Đang cuộn trang...")
            for i in range(5):
                try:
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1.5)
                except: pass
            
            print("🔍 Đang quét và TẢI VIDEO...")
            all_links = await page.query_selector_all('a')
            processed_links = set()
            count_success = 0

            for link_obj in all_links:
                try:
                    href = await link_obj.get_attribute('href')
                    if not href: continue
                    if '/video/' in href and '@' in href:
                        clean_link = href.split('?')[0].strip()
                        if not clean_link.startswith('http'): clean_link = 'https://www.tiktok.com' + clean_link
                        
                        if clean_link in processed_links: continue
                        processed_links.add(clean_link)

                        views = 0
                        try:
                            text = await link_obj.inner_text()
                            if text: views = self.parse_view_count(text)
                        except: pass

                        print(f"   ⬇️ Đang tải: {clean_link[-20:]} ...", end="\r")
                        is_success, result_info = self.download_video_now(clean_link, username)
                        
                        status = "✅ Đã tải" if is_success else "❌ Lỗi tải"
                        vid_title = result_info if is_success else "Error"
                        
                        if is_success:
                            display_name = (vid_title[:50] + '..') if len(vid_title) > 50 else vid_title
                            print(f"   ✅ HD OK: {display_name}")
                            count_success += 1
                        else:
                            print(f"   ❌ Lỗi: {clean_link[-20:]}")

                        self.videos.append({
                            'STT': len(self.videos) + 1,
                            'Trạng Thái': status,
                            'Tên Video': vid_title,
                            'Views': views,
                            'Link': clean_link
                        })
                except: continue
            
            print(f"\n📊 TỔNG KẾT: {count_success} video chất lượng cao.")
            await browser.close()

    def export_excel(self, username):
        if not self.videos: return
        df = pd.DataFrame(self.videos)
        filename = f"Report_{username}_{datetime.now().strftime('%H%M%S')}.xlsx"
        try:
            writer = pd.ExcelWriter(filename, engine='xlsxwriter')
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            green_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            red_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            text_wrap = workbook.add_format({'text_wrap': True})
            
            worksheet.set_column('A:A', 5)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 60, text_wrap)
            worksheet.set_column('D:D', 10)
            worksheet.set_column('E:E', 50)
            
            worksheet.conditional_format(f'B2:B{len(df)+1}', {'type': 'text', 'criteria': 'containing', 'value': 'Đã tải', 'format': green_fmt})
            worksheet.conditional_format(f'B2:B{len(df)+1}', {'type': 'text', 'criteria': 'containing', 'value': 'Lỗi', 'format': red_fmt})
            
            writer.close()
            print(f"✅ Đã xuất báo cáo: {filename}")
        except Exception as e:
            print(f"Lỗi Excel: {e}")

async def main():
    print("="*60)
    print("  TIKTOK SUPER HD DOWNLOADER")
    print("="*60)
    username = input("Nhập username: ").strip().lstrip('@')
    if username:
        bot = TikTokUltimateBot()
        await bot.run(username)
        bot.export_excel(username)
    print("\n✨ DONE!")

if __name__ == "__main__":
    asyncio.run(main())