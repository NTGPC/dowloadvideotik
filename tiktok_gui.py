import sys
import os
import asyncio
import pandas as pd
from datetime import datetime
import yt_dlp
from playwright.async_api import async_playwright

# Thư viện giao diện
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QFileDialog, QMessageBox, QMenu) # Thêm QMenu
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QAction, QCursor # Thêm QAction, QCursor

# ============================================================================
# PHẦN 1: BACKEND (GIỮ NGUYÊN)
# ============================================================================
class TikTokBackend:
    def __init__(self):
        self.download_folder = "Downloads"

    def parse_view_count(self, text):
        try:
            text = text.strip().upper()
            if 'K' in text: return int(float(text.replace('K', '').strip()) * 1000)
            elif 'M' in text: return int(float(text.replace('M', '').strip()) * 1000000)
            else: return int(''.join(filter(str.isdigit, text)))
        except: return 0

    def download_video(self, link, folder_name):
        save_path = os.path.join(self.download_folder, folder_name)
        os.makedirs(save_path, exist_ok=True)
        
        ydl_opts = {
            'outtmpl': f'{save_path}/%(title)s [%(id)s].%(ext)s',
            'restrictfilenames': False, 'windowsfilenames': True, 'trim_file_name': 200,
            'format': 'bestvideo[height>=1080]+bestaudio/best',
            'noplaylist': True, 'quiet': True, 'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                title = info.get('title', 'No_Title')
                ydl.download([link])
                return True, title
        except Exception as e:
            return False, str(e)

# ============================================================================
# PHẦN 2: WORKER THREAD (GIỮ NGUYÊN)
# ============================================================================
class ScraperWorker(QThread):
    progress_signal = pyqtSignal(str)
    data_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.backend = TikTokBackend()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run_scraper())

    async def run_scraper(self):
        url = f"https://www.tiktok.com/@{self.username}"
        self.progress_signal.emit(f"🚀 Đang mở trình duyệt: {self.username}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--start-maximized'])
            context = await browser.new_context()
            page = await context.new_page()
            
            try: await page.goto(url, timeout=60000)
            except: pass

            self.progress_signal.emit("⚠️ HÃY KÉO CAPTCHA NẾU CÓ!")
            for i in range(5):
                self.progress_signal.emit(f"📜 Đang cuộn trang {i+1}/5...")
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)

            self.progress_signal.emit("🔍 Đang quét và TẢI VIDEO...")
            all_links = await page.query_selector_all('a')
            processed = set()
            
            for link_obj in all_links:
                try:
                    href = await link_obj.get_attribute('href')
                    if not href or '/video/' not in href or '@' not in href: continue
                    
                    clean_link = href.split('?')[0].strip()
                    if not clean_link.startswith('http'): clean_link = 'https://www.tiktok.com' + clean_link
                    if clean_link in processed: continue
                    processed.add(clean_link)

                    views = 0
                    try:
                        text = await link_obj.inner_text()
                        if text: views = self.backend.parse_view_count(text)
                    except: pass

                    self.progress_signal.emit(f"⬇️ Đang tải: {clean_link[-15:]}...")
                    success, info = self.backend.download_video(clean_link, self.username)
                    
                    video_data = {
                        'Link': clean_link,
                        'Title': info if success else "Error",
                        'Views': views,
                        'Status': '✅ Đã tải' if success else '❌ Lỗi',
                        'Reup_Status': 'Chưa đăng'
                    }
                    self.data_signal.emit(video_data)
                except: continue
            
            await browser.close()
            self.progress_signal.emit("✨ ĐÃ QUÉT XONG!")
            self.finished_signal.emit()

# ============================================================================
# PHẦN 3: GIAO DIỆN (ĐÃ CHỈNH LAYOUT & THÊM COPY CHUỘT PHẢI)
# ============================================================================
class TikTokManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIKTOK REUP MANAGER PRO - Ver 2.2 (Perfect Layout)")
        self.setGeometry(100, 100, 1300, 800)
        self.setStyleSheet("""
            QMainWindow {background-color: #f0f2f5;}
            QLabel {font-size: 14px;}
            QTableWidget {font-size: 13px; border: 1px solid #ddd;}
            QHeaderView::section {background-color: #e9e9e9; padding: 4px; font-weight: bold;}
        """)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # --- TOP BAR ---
        top_layout = QHBoxLayout()
        lbl_user = QLabel("Username TikTok:")
        lbl_user.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Nhập ID kênh (Ví dụ: nuademtheman06)")
        self.txt_user.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")

        self.btn_start = QPushButton("🚀 BẮT ĐẦU QUÉT & TẢI")
        self.btn_start.setStyleSheet("background-color: #007bff; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_scraping)

        self.btn_load = QPushButton("📂 NHẬP EXCEL CŨ")
        self.btn_load.setStyleSheet("background-color: #28a745; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_load.clicked.connect(self.load_excel)

        self.btn_save = QPushButton("💾 LƯU EXCEL")
        self.btn_save.setStyleSheet("background-color: #dc3545; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_save.clicked.connect(self.save_excel)

        top_layout.addWidget(lbl_user)
        top_layout.addWidget(self.txt_user)
        top_layout.addWidget(self.btn_start)
        top_layout.addWidget(self.btn_load)
        top_layout.addWidget(self.btn_save)
        layout.addLayout(top_layout)

        # --- STATUS BAR ---
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet("color: #666; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(self.lbl_status)

        # --- TABLE (CHỈNH SỬA LAYOUT TẠI ĐÂY) ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tiêu Đề Video", "Views", "Trạng Thái Tải", "QUẢN LÝ ĐĂNG", "Link Gốc"])
        
        # --- CẤU HÌNH TỶ LỆ CỘT ---
        header = self.table.horizontalHeader()
        
        # 1. Tiêu đề: Tự động co giãn theo tỷ lệ (Stretch) nhưng không chiếm hết
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) 
        self.table.setColumnWidth(0, 450) # Set cứng ban đầu khoảng 450px (~40% màn hình)

        # 2, 3, 4: Cố định kích thước (Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 100) # Views
        
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120) # Trạng thái tải

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 130) # Quản lý đăng

        # 5. Link Gốc: Giãn hết phần còn lại (Stretch) - ĐÚNG Ý BRO
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.table.setAlternatingRowColors(True)
        
        # --- KÍCH HOẠT MENU CHUỘT PHẢI ---
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)

    # --- HÀM XỬ LÝ MENU CHUỘT PHẢI (COPY) ---
    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Tạo Action Copy
        copy_action = QAction("📋 Copy Nội Dung Ô Này", self)
        copy_action.triggered.connect(self.copy_cell_content)
        menu.addAction(copy_action)
        
        # Tạo Action Copy Link (Dù đang bấm ở cột nào cũng copy link dòng đó)
        copy_link_action = QAction("🔗 Copy Link Video Gốc", self)
        copy_link_action.triggered.connect(self.copy_link_row)
        menu.addAction(copy_link_action)

        menu.exec(QCursor.pos())

    def copy_cell_content(self):
        # Lấy ô đang chọn
        item = self.table.currentItem()
        if item:
            clipboard = QApplication.clipboard()
            clipboard.setText(item.text())
            self.lbl_status.setText(f"✅ Đã copy: {item.text()[:30]}...")

    def copy_link_row(self):
        # Lấy dòng đang chọn
        row = self.table.currentRow()
        if row >= 0:
            link_item = self.table.item(row, 4) # Cột 4 là Link Gốc
            if link_item:
                clipboard = QApplication.clipboard()
                clipboard.setText(link_item.text())
                self.lbl_status.setText(f"✅ Đã copy Link Video!")

    # --- CÁC HÀM LOGIC CŨ GIỮ NGUYÊN ---
    def start_scraping(self):
        user = self.txt_user.text().strip()
        if not user:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập Username!")
            return
        self.btn_start.setEnabled(False)
        self.table.setRowCount(0)
        self.worker = ScraperWorker(user)
        self.worker.progress_signal.connect(self.update_status)
        self.worker.data_signal.connect(self.add_row_to_table)
        self.worker.finished_signal.connect(self.scraping_finished)
        self.worker.start()

    def update_status(self, text):
        self.lbl_status.setText(text)

    def add_row_to_table(self, data):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(data['Title'])))
        
        view_item = QTableWidgetItem()
        view_item.setData(Qt.ItemDataRole.DisplayRole, f"{data['Views']:,}")
        view_item.setData(Qt.ItemDataRole.EditRole, data['Views'])
        self.table.setItem(row, 1, view_item)
        
        status_item = QTableWidgetItem(data['Status'])
        status_item.setForeground(QColor("green") if "Đã tải" in data['Status'] else QColor("red"))
        self.table.setItem(row, 2, status_item)

        combo = QComboBox()
        combo.addItems(["Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"])
        current_reup = str(data.get('Reup_Status', 'Chưa đăng'))
        if current_reup == 'nan': current_reup = 'Chưa đăng'
        index = combo.findText(current_reup)
        if index >= 0: combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(lambda text, r=row: self.on_combo_change(r, text))
        self.table.setCellWidget(row, 3, combo)

        self.table.setItem(row, 4, QTableWidgetItem(data['Link']))

        if current_reup == "✅ ĐÃ ĐĂNG":
            self.colorize_row(row, True)

    def on_combo_change(self, row, text):
        self.colorize_row(row, text == "✅ ĐÃ ĐĂNG")

    def colorize_row(self, row, is_done):
        color = QColor("#d4edda") if is_done else QColor("white")
        for i in range(5):
            item = self.table.item(row, i)
            if item: item.setBackground(color)

    def scraping_finished(self):
        self.btn_start.setEnabled(True)
        self.lbl_status.setText("✅ Hoàn tất! Hãy kiểm tra danh sách.")
        QMessageBox.information(self, "Thông báo", "Đã quét xong!")

    def save_excel(self):
        rows = self.table.rowCount()
        data_to_save = []
        for r in range(rows):
            combo = self.table.cellWidget(r, 3)
            item_data = {
                'Tên Video': self.table.item(r, 0).text(),
                'Views': self.table.item(r, 1).text().replace(',', ''),
                'Trạng Thái': self.table.item(r, 2).text(),
                'Reup_Status': combo.currentText(),
                'Link': self.table.item(r, 4).text()
            }
            data_to_save.append(item_data)
        
        df = pd.DataFrame(data_to_save)
        filename, _ = QFileDialog.getSaveFileName(self, "Lưu file Excel", "", "Excel Files (*.xlsx)")
        if filename:
            try:
                writer = pd.ExcelWriter(filename, engine='xlsxwriter')
                df.to_excel(writer, index=False)
                writer.close()
                QMessageBox.information(self, "Thành công", "Đã lưu File Excel!")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def load_excel(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Mở file Excel", "", "Excel Files (*.xlsx)")
        if filename:
            try:
                df = pd.read_excel(filename)
                self.table.setRowCount(0)
                for index, row in df.iterrows():
                    title = row.get('Tên Video') if 'Tên Video' in df.columns else row.get('Title', '')
                    status = row.get('Trạng Thái') if 'Trạng Thái' in df.columns else row.get('Status', '')
                    reup = row.get('Reup_Status', 'Chưa đăng')
                    
                    data = {
                        'Title': str(title) if str(title) != 'nan' else '',
                        'Views': row.get('Views', 0),
                        'Status': str(status) if str(status) != 'nan' else '',
                        'Reup_Status': str(reup),
                        'Link': str(row.get('Link', ''))
                    }
                    self.add_row_to_table(data)
                self.lbl_status.setText(f"📂 Đã load {len(df)} dòng dữ liệu.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không đọc được file: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TikTokManagerApp()
    window.show()
    sys.exit(app.exec())
