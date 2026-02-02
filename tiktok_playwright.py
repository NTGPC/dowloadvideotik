"""
TIKTOK SCRAPER - PLAYWRIGHT VERSION
Bypass bot detection tốt hơn Selenium
"""

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime
import re

class TikTokScraperPlaywright:
    def __init__(self):
        self.videos = []
    
    def parse_view_count(self, text):
        """Convert view count to number"""
        text = text.strip().upper()
        if 'K' in text:
            return int(float(text.replace('K', '').strip()) * 1000)
        elif 'M' in text:
            return int(float(text.replace('M', '').strip()) * 1000000)
        else:
            return int(text)
    
    async def scrape_profile(self, username):
        """Scrape TikTok profile"""
        url = f"https://www.tiktok.com/@{username}"
        
        async with async_playwright() as p:
            print("🔧 Đang mở Chrome...")
            
            # Launch with anti-detection
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Anti-detection script
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()
            
            print(f"🔗 Đang mở: {url}")
            await page.goto(url, wait_until='networkidle')
            
            print("⏳ Đợi 5 giây cho trang load...")
            await asyncio.sleep(5)
            
            print("📜 Đang scroll để load video...")
            for i in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                print(f"   Scroll {i+1}/5")
            
            print("📊 Đang lấy data...")
            
            # Get video links and views
            videos = await page.query_selector_all('div[data-e2e="user-post-item"]')
            
            print(f"✅ Tìm thấy {len(videos)} video!")
            
            for idx, video in enumerate(videos, 1):
                try:
                    # Get link - Try multiple methods to ensure we get full video URL
                    link_elem = await video.query_selector('a')
                    link = await link_elem.get_attribute('href') if link_elem else None
                    
                    # Ensure full URL
                    if link:
                        if not link.startswith('http'):
                            link = 'https://www.tiktok.com' + link
                        
                        # Debug: Print raw link to verify it's complete
                        print(f"   🔍 DEBUG - Raw link: {link}")
                        
                        # Validate that it's a video link (should contain /video/)
                        if '/video/' not in link and '/@' in link:
                            print(f"   ⚠️ WARNING: Link seems to be profile link, not video link!")
                    
                    # Get view count
                    view_elem = await video.query_selector('strong[data-e2e="video-views"]')
                    view_text = await view_elem.inner_text() if view_elem else '0'
                    views = self.parse_view_count(view_text)
                    
                    if link and '/video/' in link:  # Only save if it's a valid video link
                        self.videos.append({
                            'STT': idx,
                            'Link': link,
                            'Views': views
                        })
                        print(f"   ✅ {idx}. {views:,} views - {link[:80]}...")
                    else:
                        print(f"   ❌ Skipped invalid link: {link}")
                
                except Exception as e:
                    print(f"   ⚠️ Lỗi video {idx}: {e}")
                    continue
            
            await browser.close()
    
    def export_excel(self):
        """Export to Excel"""
        if not self.videos:
            print("❌ Không có data!")
            return
        
        df = pd.DataFrame(self.videos)
        filename = f"tiktok_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"\n✅ Đã lưu: {filename}")
        print(f"📊 Tổng: {len(self.videos)} video")

async def main():
    print("="*60)
    print("  TIKTOK SCRAPER - PLAYWRIGHT")
    print("="*60)
    print()
    
    username = input("Nhập username (không cần @): ").strip().lstrip('@')
    
    scraper = TikTokScraperPlaywright()
    await scraper.scrape_profile(username)
    scraper.export_excel()
    
    print("\n✨ XONG!")

if __name__ == "__main__":
    asyncio.run(main())
