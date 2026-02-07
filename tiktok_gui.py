import sys
import os
import asyncio
import pandas as pd
from datetime import datetime
import yt_dlp
import requests
from playwright.async_api import async_playwright

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QFileDialog, QMessageBox, QMenu, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QAction, QCursor, QPixmap, QIcon

# ============================================================================
# CẤU HÌNH ĐƯỜNG DẪN GỐC (ROOT PATH)
# ============================================================================
BASE_DATA_FOLDER = "TIKTOK_DATA" # Tất cả sẽ chui vào thư mục này

# ============================================================================
# PHẦN 1: BACKEND (LOGIC TẢI VÀO ĐÚNG THƯ MỤC)
# ============================================================================
class TikTokBackend:
    def __init__(self):
        pass # Không set cứng download folder ở đây nữa

    def parse_view_count(self, text):
        try:
            text = text.strip().upper()
            if 'K' in text: return int(float(text.replace('K', '').strip()) * 1000)
            elif 'M' in text: return int(float(text.replace('M', '').strip()) * 1000000)
            else: return int(''.join(filter(str.isdigit, text)))
        except: return 0

    def download_video(self, link, username):
        # TẠO ĐƯỜNG DẪN CỨNG: TIKTOK_DATA / username
        user_folder = os.path.join(BASE_DATA_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        
        ydl_opts = {
            # Lưu video trực tiếp vào thư mục của user
            'outtmpl': f'{user_folder}/%(title)s [%(id)s].%(ext)s',
            'restrictfilenames': False, 'windowsfilenames': True, 'trim_file_name': 200,
            'format': 'bestvideo[height>=1080]+bestaudio/best',
            'noplaylist': True, 'quiet': True, 'no_warnings': True,
            'writethumbnail': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                title = info.get('title', 'No_Title')
                thumbnail_url = info.get('thumbnail', None)
                ydl.download([link])
                video_filename = ydl.prepare_filename(info)
                return True, title, thumbnail_url, video_filename
        except Exception as e:
            return False, str(e), None, None

# ============================================================================
# PHẦN 2: WORKER THREAD
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
        self.progress_signal.emit(f"🚀 Đang mở kênh: {self.username}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--start-maximized'])
            context = await browser.new_context()
            page = await context.new_page()
            
            try: await page.goto(url, timeout=60000)
            except: pass

            self.progress_signal.emit("⚠️ HÃY KÉO CAPTCHA NẾU CÓ!")
            for i in range(5):
                self.progress_signal.emit(f"📜 Cuộn trang {i+1}/5...")
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)

            self.progress_signal.emit(f"📂 Đang tải về thư mục: {BASE_DATA_FOLDER}/{self.username} ...")
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
                    success, title, thumb_url, local_path = self.backend.download_video(clean_link, self.username)
                    
                    pixmap_data = None
                    if thumb_url:
                        try:
                            response = requests.get(thumb_url, timeout=5)
                            pixmap_data = response.content
                        except: pass

                    video_data = {
                        'Link': clean_link,
                        'Title': title if success else "Error",
                        'Views': views,
                        'Status': '✅ Đã tải' if success else '❌ Lỗi',
                        'Reup_Status': 'Chưa đăng',
                        'Thumb_Data': pixmap_data,
                        'Local_Path': local_path
                    }
                    self.data_signal.emit(video_data)
                except: continue
            
            await browser.close()
            self.progress_signal.emit("✨ ĐÃ QUÉT XONG!")
            self.finished_signal.emit()

# ============================================================================
# PHẦN 3: GIAO DIỆN (QUẢN LÝ TẬP TRUNG)
# ============================================================================
class TikTokManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIKTOK MANAGER V3.5 - ORGANIZED EDITION")
        self.setGeometry(100, 100, 1400, 850)
        self.setStyleSheet("""
            QMainWindow {background-color: #f0f2f5;}
            QLabel {font-size: 13px; font-weight: bold; color: #333;}
            QLineEdit {padding: 6px; border: 1px solid #ccc; border-radius: 4px; background: white;}
            QComboBox {padding: 5px; border: 1px solid #ccc; border-radius: 4px; background: white;}
            QTableWidget {font-size: 13px; border: 1px solid #ddd; background: white;}
            QHeaderView::section {background-color: #e9e9e9; padding: 6px; font-weight: bold; border: none; border-bottom: 1px solid #ccc;}
        """)
        
        # --- PATH MANAGEMENT ---
        self.current_username = "" # Lưu user đang làm việc
        self.video_paths = {}

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # --- TOP BAR ---
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Username:"))
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Nhập ID kênh...")
        
        self.btn_start = QPushButton("🚀 QUÉT & TẢI")
        self.btn_start.setStyleSheet("background-color: #007bff; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_scraping)
        
        # Nút Mở Thư Mục Nhanh
        self.btn_open_folder = QPushButton("📂 MỞ THƯ MỤC")
        self.btn_open_folder.setStyleSheet("background-color: #17a2b8; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_open_folder.clicked.connect(self.open_current_folder)

        self.btn_load = QPushButton("📥 NHẬP EXCEL")
        self.btn_load.setStyleSheet("background-color: #28a745; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_load.clicked.connect(self.load_excel)
        
        self.btn_save = QPushButton("💾 LƯU EXCEL")
        self.btn_save.setStyleSheet("background-color: #dc3545; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_save.clicked.connect(self.save_excel)
        
        top_layout.addWidget(self.txt_user)
        top_layout.addWidget(self.btn_start)
        top_layout.addWidget(self.btn_open_folder) # Thêm nút mở folder
        top_layout.addWidget(self.btn_load)
        top_layout.addWidget(self.btn_save)
        layout.addLayout(top_layout)

        # --- FILTER BAR ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #e3f2fd; border-radius: 5px; border: 1px solid #90caf9;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 5, 10, 5)
        filter_layout.addWidget(QLabel("🔍 Tìm kiếm:"))
        self.txt_search = QLineEdit()
        self.txt_search.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.txt_search)
        filter_layout.addWidget(QLabel("👁️ Views:"))
        self.combo_filter_view = QComboBox()
        self.combo_filter_view.addItems(["Tất cả", "> 10K View", "> 100K View", "> 1 Triệu View"])
        self.combo_filter_view.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.combo_filter_view)
        filter_layout.addWidget(QLabel("📌 Trạng thái:"))
        self.combo_filter_status = QComboBox()
        self.combo_filter_status.addItems(["Tất cả", "Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"])
        self.combo_filter_status.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.combo_filter_status)
        layout.addWidget(filter_frame)

        self.lbl_status = QLabel(f"Dữ liệu sẽ lưu tại: {os.path.abspath(BASE_DATA_FOLDER)}")
        self.lbl_status.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.lbl_status)

        # --- TABLE ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["HÌNH ẢNH", "Tiêu Đề Video", "Views", "Trạng Thái Tải", "QUẢN LÝ ĐĂNG", "Link Gốc"])
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(70)
        self.table.setIconSize(QSize(60, 80))

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 400)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 120)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 130)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

    # --- LOGIC MỚI: MỞ FOLDER ---
    def open_current_folder(self):
        if not self.current_username:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn Username nào!")
            return
        folder_path = os.path.join(os.getcwd(), BASE_DATA_FOLDER, self.current_username)
        if os.path.exists(folder_path):
            os.startfile(folder_path)
        else:
            QMessageBox.warning(self, "Lỗi", "Thư mục chưa tồn tại (Chưa tải video nào)!")

    # --- CÁC HÀM XỬ LÝ ---
    def start_scraping(self):
        user = self.txt_user.text().strip()
        if not user: return
        
        self.current_username = user # Lưu user hiện tại
        self.btn_start.setEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.video_paths = {}

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
        
        img_item = QTableWidgetItem()
        if data.get('Thumb_Data'):
            pixmap = QPixmap()
            pixmap.loadFromData(data['Thumb_Data'])
            img_item.setIcon(QIcon(pixmap))
        else: img_item.setText("No Img")
        
        if data.get('Local_Path'):
            self.video_paths[data['Link']] = data['Local_Path']

        img_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, 0, img_item)
        self.table.setItem(row, 1, QTableWidgetItem(str(data['Title'])))
        
        view_val = int(data['Views'])
        view_item = QTableWidgetItem()
        view_item.setData(Qt.ItemDataRole.DisplayRole, f"{view_val:,}")
        view_item.setData(Qt.ItemDataRole.EditRole, view_val)
        self.table.setItem(row, 2, view_item)
        
        status_item = QTableWidgetItem(data['Status'])
        status_item.setForeground(QColor("green") if "Đã tải" in data['Status'] else QColor("red"))
        self.table.setItem(row, 3, status_item)

        combo = QComboBox()
        combo.addItems(["Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"])
        current_reup = str(data.get('Reup_Status', 'Chưa đăng'))
        if str(current_reup) == 'nan': current_reup = 'Chưa đăng'
        index = combo.findText(current_reup)
        if index >= 0: combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(lambda text, r=row: self.on_combo_change(r, text))
        self.table.setCellWidget(row, 4, combo)

        self.table.setItem(row, 5, QTableWidgetItem(data['Link']))
        if current_reup == "✅ ĐÃ ĐĂNG": self.colorize_row(row, True)

    def save_excel(self):
        if not self.current_username:
            user = self.txt_user.text().strip()
            if user: self.current_username = user
            else: 
                QMessageBox.warning(self, "Lỗi", "Không xác định được Username để lưu vào folder!")
                return

        rows = self.table.rowCount()
        data_to_save = []
        for r in range(rows):
            combo = self.table.cellWidget(r, 4)
            view_val = self.table.item(r, 2).data(Qt.ItemDataRole.EditRole)
            item_data = {
                'Tên Video': self.table.item(r, 1).text(),
                'Views': view_val,
                'Trạng Thái': self.table.item(r, 3).text(),
                'Reup_Status': combo.currentText(),
                'Link': self.table.item(r, 5).text(),
                'Local_Path': self.video_paths.get(self.table.item(r, 5).text(), '')
            }
            data_to_save.append(item_data)
        
        df = pd.DataFrame(data_to_save)
        
        # --- LOGIC LƯU VÀO ĐÚNG FOLDER TIKTOK_DATA ---
        folder_path = os.path.join(BASE_DATA_FOLDER, self.current_username)
        os.makedirs(folder_path, exist_ok=True)
        default_name = os.path.join(folder_path, f"Report_{self.current_username}.xlsx")

        filename, _ = QFileDialog.getSaveFileName(self, "Lưu file Excel", default_name, "Excel Files (*.xlsx)")
        
        if filename:
            try:
                writer = pd.ExcelWriter(filename, engine='xlsxwriter')
                df.to_excel(writer, index=False)
                writer.close()
                QMessageBox.information(self, "Thành công", f"Đã lưu vào: {filename}")
            except Exception as e: QMessageBox.critical(self, "Lỗi", str(e))

    def load_excel(self):
        # Mặc định mở folder TIKTOK_DATA để tìm cho dễ
        start_dir = os.path.join(os.getcwd(), BASE_DATA_FOLDER)
        if not os.path.exists(start_dir): start_dir = os.getcwd()

        filename, _ = QFileDialog.getOpenFileName(self, "Mở file Excel", start_dir, "Excel Files (*.xlsx)")
        if filename:
            try:
                # Trích xuất username từ tên file hoặc folder nếu có thể
                # (Logic đơn giản: Lấy tên folder cha làm username)
                parent_folder = os.path.basename(os.path.dirname(filename))
                self.current_username = parent_folder
                self.txt_user.setText(parent_folder)

                self.table.setSortingEnabled(False)
                df = pd.read_excel(filename)
                self.table.setRowCount(0)
                for index, row in df.iterrows():
                    title = row.get('Tên Video') if 'Tên Video' in df.columns else row.get('Title', '')
                    status = row.get('Trạng Thái') if 'Trạng Thái' in df.columns else row.get('Status', '')
                    reup = row.get('Reup_Status', 'Chưa đăng')
                    local_path = str(row.get('Local_Path', ''))
                    
                    data = {
                        'Title': str(title) if str(title) != 'nan' else '',
                        'Views': row.get('Views', 0),
                        'Status': str(status) if str(status) != 'nan' else '',
                        'Reup_Status': str(reup),
                        'Link': str(row.get('Link', '')),
                        'Thumb_Data': None,
                        'Local_Path': local_path
                    }
                    self.add_row_to_table(data)
                self.table.setSortingEnabled(True)
                self.lbl_status.setText(f"📂 Đã load: {filename}")
            except Exception as e: QMessageBox.critical(self, "Lỗi", str(e))

    # --- CÁC HÀM PHỤ TRỢ (Preview, Filter, Color...) ---
    def on_cell_clicked(self, row, col):
        if col == 0 or col == 1:
            link = self.table.item(row, 5).text()
            local_path = self.video_paths.get(link)
            if local_path and os.path.exists(local_path): os.startfile(local_path)
            else: os.startfile(link)

    def on_combo_change(self, row, text):
        self.colorize_row(row, text == "✅ ĐÃ ĐĂNG")
        self.apply_filters()

    def colorize_row(self, row, is_done):
        color = QColor("#d4edda") if is_done else QColor("white")
        for i in range(6):
            item = self.table.item(row, i)
            if item: item.setBackground(color)

    def scraping_finished(self):
        self.btn_start.setEnabled(True)
        self.table.setSortingEnabled(True)
        self.lbl_status.setText(f"✅ Đã tải xong vào: {BASE_DATA_FOLDER}/{self.current_username}")
        QMessageBox.information(self, "Thông báo", "Đã quét xong!")
        # Tự động lưu file excel sau khi quét xong (Auto-save)
        self.save_excel()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("📋 Copy Nội Dung", self)
        copy_action.triggered.connect(self.copy_cell_content)
        menu.addAction(copy_action)
        copy_link_action = QAction("🔗 Copy Link Gốc", self)
        copy_link_action.triggered.connect(self.copy_link_row)
        menu.addAction(copy_link_action)
        menu.exec(QCursor.pos())

    def copy_cell_content(self):
        item = self.table.currentItem()
        if item: QApplication.clipboard().setText(item.text())

    def copy_link_row(self):
        row = self.table.currentRow()
        if row >= 0: QApplication.clipboard().setText(self.table.item(row, 5).text())

    def apply_filters(self):
        keyword = self.txt_search.text().lower()
        view_filter = self.combo_filter_view.currentIndex()
        status_filter_text = self.combo_filter_status.currentText()
        rows = self.table.rowCount()
        for r in range(rows):
            title_item = self.table.item(r, 1)
            view_item = self.table.item(r, 2)
            combo_widget = self.table.cellWidget(r, 4)
            if not title_item or not view_item or not combo_widget: continue
            
            title_text = title_item.text().lower()
            view_val = view_item.data(Qt.ItemDataRole.EditRole)
            current_row_status = combo_widget.currentText()

            match_keyword = keyword in title_text
            match_view = True
            if view_filter == 1 and view_val < 10000: match_view = False
            if view_filter == 2 and view_val < 100000: match_view = False
            if view_filter == 3 and view_val < 1000000: match_view = False
            
            match_status = True
            if status_filter_text != "Tất cả":
                if status_filter_text != current_row_status: match_status = False

            self.table.setRowHidden(r, not (match_keyword and match_view and match_status))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TikTokManagerApp()
    window.show()
    sys.exit(app.exec())
