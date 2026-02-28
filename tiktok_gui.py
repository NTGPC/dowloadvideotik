import sys
import os
import asyncio
import pandas as pd
from datetime import datetime
import yt_dlp
import requests
import subprocess 
import re 
from playwright.async_api import async_playwright

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QFileDialog, QMessageBox, QMenu, QFrame,
                             QDialog, QCheckBox, QGroupBox, QTabWidget, QSlider, QSizePolicy, QListWidget, QProgressBar, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QAction, QCursor, QPixmap, QIcon, QPainter, QTransform, QPen

BASE_DATA_FOLDER = "TIKTOK_DATA"

# ============================================================================
# 1. RENDER ENGINE 
# ============================================================================
class RenderEngine:
    def __init__(self):
        self.ffmpeg_exe = "ffmpeg.exe"
        self.ffmpeg_ready = os.path.exists(self.ffmpeg_exe)

    def extract_frame(self, video_path):
        if not self.ffmpeg_ready:
            return None
        try:
            cmd = [self.ffmpeg_exe, '-ss', '00:00:01', '-i', video_path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-']
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, startupinfo=startupinfo)
            return proc.stdout
        except:
            return None

    def render_video(self, input_path, output_path, options):
        if not self.ffmpeg_ready:
            return False, "Thiếu file ffmpeg.exe!"
        
        cmd = [self.ffmpeg_exe, '-y', '-i', input_path]
        
        # Filter Chain
        video_filters = []
        if options['flip']:
            video_filters.append("hflip")
        if options['speed_1_1']:
            video_filters.append("setpts=PTS/1.1")
        
        # Logic nền [bg]
        bg_node = "[0:v]"
        if video_filters:
            cmd.extend(['-filter_complex', f"[0:v]{','.join(video_filters)}[bg]"])
            bg_node = "[bg]"
            
        # Logic Logo
        if options['logo_path']:
            cmd.extend(['-i', options['logo_path']])
            scale_pct = options['logo_scale'] / 100.0
            opacity_val = options['logo_opacity'] / 100.0
            x_expr = f"(main_w-overlay_w)*{options['logo_x']}/100"
            y_expr = f"(main_h-overlay_h)*{options['logo_y']}/100"
            
            if video_filters:
                # Nối tiếp: [bg] -> Overlay
                complex_str = (f"[0:v]{','.join(video_filters)}[bg];"
                               f"[1:v][bg]scale2ref=w=iw*{scale_pct}:h=-1[logo_sized][bg_ref];"
                               f"[logo_sized]format=rgba,colorchannelmixer=aa={opacity_val}[logo_final];"
                               f"[bg_ref][logo_final]overlay=x={x_expr}:y={y_expr}")
                # Reset cmd filter
                cmd = [c for c in cmd if c != '-filter_complex'] 
                cmd.extend(['-filter_complex', complex_str])
            else:
                # Chưa có filter nền
                complex_str = (f"[1:v][0:v]scale2ref=w=iw*{scale_pct}:h=-1[logo_sized][bg_ref];"
                               f"[logo_sized]format=rgba,colorchannelmixer=aa={opacity_val}[logo_final];"
                               f"[bg_ref][logo_final]overlay=x={x_expr}:y={y_expr}")
                cmd.extend(['-filter_complex', complex_str])
        else:
            if video_filters and not options['logo_path']:
                cmd.extend(['-map', '[bg]'])

        if options['mute_audio']:
            pass 
        elif options['speed_1_1']:
            cmd.extend(['-filter:a', "atempo=1.1"])
            cmd.extend(['-map', '0:a'])
        else:
            cmd.extend(['-map', '0:a'])

        cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p4', '-rc', 'constqp', '-qp', '26', '-pix_fmt', 'yuv420p', '-c:a', 'aac', output_path])
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, startupinfo=startupinfo)
            return True, "OK"
        except Exception as e:
            return False, str(e)

# ============================================================================
# 2. BACKEND & WORKER
# ============================================================================
class TikTokBackend:
    def parse_view_count(self, text):
        try:
            text = text.strip().upper()
            if 'K' in text: return int(float(text.replace('K', '').strip()) * 1000)
            elif 'M' in text: return int(float(text.replace('M', '').strip()) * 1000000)
            else: return int(''.join(filter(str.isdigit, text)))
        except: return 0

    def download_video(self, link, username, progress_callback=None):
        user_folder = os.path.join(BASE_DATA_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        
        def my_hook(d):
            if d['status'] == 'downloading':
                try:
                    p = d.get('_percent_str', '0%').replace('%','')
                    if progress_callback: progress_callback(float(p))
                except: pass

        ydl_opts = {
            'outtmpl': f'{user_folder}/%(title)s [%(id)s].%(ext)s',
            'restrictfilenames': False, 'windowsfilenames': True, 'trim_file_name': 200,
            'format': 'bestvideo[height>=1080]+bestaudio/best',
            'noplaylist': True, 'quiet': True, 'no_warnings': True,
            'writethumbnail': True,
            'progress_hooks': [my_hook],
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                title = info.get('title', 'No_Title')
                thumb = info.get('thumbnail', None)
                ydl.download([link])
                fname = ydl.prepare_filename(info)
                return True, title, thumb, fname
        except Exception as e: return False, str(e), None, None

class ScraperWorker(QThread):
    progress_log_signal = pyqtSignal(str) 
    video_found_signal = pyqtSignal(str)          
    download_progress_signal = pyqtSignal(str, int) 
    video_finished_signal = pyqtSignal(dict)      
    finished_signal = pyqtSignal()

    def __init__(self, username, proxy_str=None):
        super().__init__()
        self.username = username
        self.proxy_str = proxy_str
        self.backend = TikTokBackend()

    def run(self):
        asyncio.run(self.run_scraper())

    async def run_scraper(self):
        clean_user = self.username.replace("@", "").strip()
        url = f"https://www.tiktok.com/@{clean_user}"
        self.progress_log_signal.emit(f"🚀 Khởi động...")
        
        user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
        async with async_playwright() as p:
            proxy_config = None
            if self.proxy_str and len(self.proxy_str.split(':')) == 4:
                parts = self.proxy_str.split(':')
                proxy_config = {"server": f"http://{parts[0]}:{parts[1]}", "username": parts[2], "password": parts[3]}
            
            try:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir, headless=False, proxy=proxy_config,
                    args=['--disable-blink-features=AutomationControlled', '--start-maximized', '--no-sandbox'], viewport=None
                )
                page = browser.pages[0]
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                try:
                    await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                except: pass
                
                self.progress_log_signal.emit("⏳ Đang quét...")
                await asyncio.sleep(3)
                
                for i in range(3):
                    await page.mouse.wheel(0, 2000)
                    await asyncio.sleep(2)
                
                all_elements = await page.query_selector_all('a')
                processed = set()
                
                for el in all_elements:
                    try:
                        href = await el.get_attribute('href')
                        if not href or '/video/' not in href: continue
                        clean_link = href.split('?')[0].strip()
                        if clean_link in processed: continue
                        processed.add(clean_link)
                        
                        self.video_found_signal.emit(clean_link)

                        def update_prog(pct):
                            self.download_progress_signal.emit(clean_link, int(pct))

                        success, title, thumb_url, local_path = self.backend.download_video(clean_link, clean_user, update_prog)
                        
                        views = 0
                        try:
                            t = await el.inner_text()
                            views = self.backend.parse_view_count(t)
                        except: pass

                        pixmap_data = None
                        if thumb_url:
                            try: pixmap_data = requests.get(thumb_url, timeout=3).content
                            except: pass

                        self.video_finished_signal.emit({
                            'Link': clean_link, 'Title': title if success else "Error",
                            'Views': views, 'Status': '✅ Đã tải' if success else '❌ Lỗi',
                            'Reup_Status': 'Chưa đăng', 'Thumb_Data': pixmap_data, 'Local_Path': local_path
                        })
                    except: continue
                
                await browser.close()
                self.finished_signal.emit()
            except Exception as e:
                self.progress_log_signal.emit(f"❌ Lỗi: {str(e)}")

class RenderWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal()
    def __init__(self, items, options):
        super().__init__()
        self.items = items
        self.options = options
        self.engine = RenderEngine()
    def run(self):
        total = len(self.items)
        for i, item in enumerate(self.items):
            input_path = item['Local_Path']
            if not input_path or not os.path.exists(input_path): continue
            folder = os.path.dirname(input_path)
            render_folder = os.path.join(folder, "Rendered")
            os.makedirs(render_folder, exist_ok=True)
            name = os.path.basename(input_path)
            name_no_ext, ext = os.path.splitext(name)
            output_path = os.path.join(render_folder, f"{name_no_ext}_EDITED{ext}")
            
            self.progress_signal.emit(int((i / total) * 100), f"🎬 Render ({i+1}/{total}): {name[:20]}...")
            success, msg = self.engine.render_video(input_path, output_path, self.options)
            
            if success: self.progress_signal.emit(int(((i+1) / total) * 100), f"✅ Xong: {name[:20]}")
            else: self.progress_signal.emit(int(((i+1) / total) * 100), f"❌ Lỗi: {msg}")
            
        self.finished_signal.emit()

# ============================================================================
# 3. WIDGET EDITOR
# ============================================================================
class DraggablePreviewLabel(QLabel):
    positionChanged = pyqtSignal(int, int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("color: white; background-color: black; border: 1px solid #555;")
        self.setMouseTracking(True) 
    def mousePressEvent(self, event): self.update_position(event.pos())
    def mouseMoveEvent(self, event): 
        if event.buttons() & Qt.MouseButton.LeftButton: self.update_position(event.pos())
    def update_position(self, pos):
        w = self.width(); h = self.height()
        if w == 0 or h == 0: return
        x = max(0, min(pos.x(), w)); y = max(0, min(pos.y(), h))
        x_pct = int((x / w) * 100); y_pct = int((y / h) * 100)
        self.positionChanged.emit(x_pct, y_pct)

class EmbeddedEditorWidget(QWidget):
    render_requested = pyqtSignal(dict) 
    def __init__(self):
        super().__init__()
        self.engine = RenderEngine(); self.original_pixmap = None; self.current_video_path = None; self.queue_items = []
        layout = QHBoxLayout(self)
        left_panel = QFrame(); left_panel.setFixedWidth(300); left_layout = QVBoxLayout(left_panel)
        g_vid = QGroupBox("1. HÌNH ẢNH"); l_vid = QVBoxLayout()
        self.chk_flip = QCheckBox("Lật Ngược"); self.chk_flip.stateChanged.connect(self.update_preview)
        self.chk_speed = QCheckBox("Tăng Tốc 1.1x"); l_vid.addWidget(self.chk_flip); l_vid.addWidget(self.chk_speed); g_vid.setLayout(l_vid)
        g_aud = QGroupBox("2. ÂM THANH"); l_aud = QHBoxLayout()
        self.chk_mute = QCheckBox("Tắt Tiếng"); self.chk_mute.stateChanged.connect(self.update_audio_visual)
        self.lbl_audio = QLabel("🔊"); l_aud.addWidget(self.chk_mute); l_aud.addWidget(self.lbl_audio); g_aud.setLayout(l_aud)
        g_logo = QGroupBox("3. LOGO (KÉO THẢ)"); l_logo = QVBoxLayout()
        btn_brow = QPushButton("Chọn Ảnh..."); btn_brow.clicked.connect(self.browse_logo)
        self.lbl_logo_path = QLabel("Chưa chọn"); self.lbl_logo_path.setStyleSheet("color:gray; font-size:9px")
        l_logo.addWidget(btn_brow); l_logo.addWidget(self.lbl_logo_path)
        l_logo.addWidget(QLabel("Size:")); self.sl_scale = QSlider(Qt.Orientation.Horizontal); self.sl_scale.setRange(5, 80); self.sl_scale.setValue(20); self.sl_scale.valueChanged.connect(self.update_preview); l_logo.addWidget(self.sl_scale)
        l_logo.addWidget(QLabel("Độ mờ:")); self.sl_opacity = QSlider(Qt.Orientation.Horizontal); self.sl_opacity.setRange(10, 100); self.sl_opacity.setValue(100); self.sl_opacity.valueChanged.connect(self.update_preview); l_logo.addWidget(self.sl_opacity)
        self.sl_x = QSlider(Qt.Orientation.Horizontal); self.sl_x.setRange(0, 100); self.sl_x.setValue(95); self.sl_x.setVisible(False)
        self.sl_y = QSlider(Qt.Orientation.Horizontal); self.sl_y.setRange(0, 100); self.sl_y.setValue(5); self.sl_y.setVisible(False)
        g_logo.setLayout(l_logo)
        self.btn_render = QPushButton("🔥 RENDER TẤT CẢ 🔥"); self.btn_render.setStyleSheet("background-color: #d63384; color: white; font-weight: bold; height: 50px;")
        self.btn_render.clicked.connect(self.emit_render_signal)
        left_layout.addWidget(g_vid); left_layout.addWidget(g_aud); left_layout.addWidget(g_logo); left_layout.addStretch(); left_layout.addWidget(self.btn_render)
        mid_panel = QFrame(); mid_layout = QVBoxLayout(mid_panel); mid_panel.setStyleSheet("background: #000;")
        self.lbl_screen = DraggablePreviewLabel("Chọn video bên phải để xem"); self.lbl_screen.positionChanged.connect(self.on_mouse_drag)
        self.lbl_screen.setScaledContents(False); self.lbl_screen.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        mid_layout.addWidget(self.lbl_screen)
        right_panel = QFrame(); right_panel.setFixedWidth(300); right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("DANH SÁCH CHỜ:")); self.list_queue = QListWidget(); self.list_queue.itemClicked.connect(self.on_queue_item_clicked); right_layout.addWidget(self.list_queue)
        right_layout.addWidget(QLabel("TIẾN TRÌNH:")); self.p_bar = QProgressBar(); right_layout.addWidget(self.p_bar)
        self.txt_log = QTextEdit(); self.txt_log.setReadOnly(True); self.txt_log.setStyleSheet("font-size:10px; color: #333;"); right_layout.addWidget(self.txt_log)
        layout.addWidget(left_panel); layout.addWidget(mid_panel); layout.addWidget(right_panel)
    def set_queue(self, items):
        self.queue_items = items; self.list_queue.clear(); self.txt_log.clear(); self.p_bar.setValue(0)
        for item in items: self.list_queue.addItem(os.path.basename(item['Local_Path']))
        if items: self.load_video(items[0]['Local_Path'])
    def log_message(self, msg): self.txt_log.append(msg); self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())
    def update_progress(self, val): self.p_bar.setValue(val)
    def on_queue_item_clicked(self, item):
        idx = self.list_queue.row(item)
        if idx >= 0: self.load_video(self.queue_items[idx]['Local_Path'])
    def load_video(self, video_path):
        self.current_video_path = video_path
        img_data = self.engine.extract_frame(video_path)
        if img_data:
            pixmap = QPixmap(); pixmap.loadFromData(img_data); self.original_pixmap = pixmap; self.update_preview()
        else: self.lbl_screen.setText("❌ Lỗi Video")
    def on_mouse_drag(self, x, y): self.sl_x.setValue(x); self.sl_y.setValue(y); self.update_preview()
    def update_preview(self):
        if not self.original_pixmap: return
        preview = self.original_pixmap.copy()
        if self.chk_flip.isChecked(): preview = preview.transformed(QTransform().scale(-1, 1), Qt.TransformationMode.SmoothTransformation)
        logo_path = self.lbl_logo_path.property("path")
        if logo_path and os.path.exists(logo_path):
            painter = QPainter(preview); logo_pix = QPixmap(logo_path)
            scale_percent = self.sl_scale.value() / 100; new_w = int(preview.width() * scale_percent)
            logo_pix = logo_pix.scaledToWidth(new_w, Qt.TransformationMode.SmoothTransformation)
            opacity = self.sl_opacity.value() / 100.0; painter.setOpacity(opacity)
            pos_x = int((preview.width() - logo_pix.width()) * (self.sl_x.value() / 100))
            pos_y = int((preview.height() - logo_pix.height()) * (self.sl_y.value() / 100))
            painter.drawPixmap(pos_x, pos_y, logo_pix); painter.end()
        target_size = self.lbl_screen.size()
        self.lbl_screen.setPixmap(preview.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    def browse_logo(self):
        f, _ = QFileDialog.getOpenFileName(self, "Logo", "", "Img (*.png *.jpg)")
        if f: self.lbl_logo_path.setText(os.path.basename(f)); self.lbl_logo_path.setProperty("path", f); self.update_preview()
    def update_audio_visual(self):
        if self.chk_mute.isChecked(): self.lbl_audio.setText("🔇")
        else: self.lbl_audio.setText("🔊")
    def get_options(self):
        return { 'flip': self.chk_flip.isChecked(), 'speed_1_1': self.chk_speed.isChecked(), 'mute_audio': self.chk_mute.isChecked(), 'logo_path': self.lbl_logo_path.property("path") if self.lbl_logo_path.property("path") else "", 'logo_x': self.sl_x.value(), 'logo_y': self.sl_y.value(), 'logo_scale': self.sl_scale.value(), 'logo_opacity': self.sl_opacity.value() }
    def emit_render_signal(self): self.render_requested.emit(self.get_options())
    def resizeEvent(self, event): self.update_preview(); super().resizeEvent(event)

# ============================================================================
# MAIN APP
# ============================================================================
class TikTokManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIKTOK MANAGER V12.2 - FINAL STABLE (NO ERRORS)")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("QMainWindow {background-color: #f0f2f5;} QLabel {color: #333; font-weight: bold;}")
        
        self.current_username = ""
        self.video_paths = {}

        main = QWidget(); self.setCentralWidget(main); layout = QVBoxLayout(main)

        top = QHBoxLayout()
        top.addWidget(QLabel("Kênh:")); self.txt_user = QLineEdit(); self.txt_user.setPlaceholderText("Nhập ID..."); top.addWidget(self.txt_user)
        top.addWidget(QLabel("Proxy:")); self.txt_proxy = QLineEdit(); self.txt_proxy.setPlaceholderText("Để trống nếu dùng mạng thường"); top.addWidget(self.txt_proxy)
        btn_start = QPushButton("🚀 QUÉT TẢI"); btn_start.clicked.connect(self.start_scraping); btn_start.setStyleSheet("background-color:#007bff; color:white; font-weight:bold;"); top.addWidget(btn_start)
        btn_folder = QPushButton("📂 FOLDER"); btn_folder.clicked.connect(self.open_folder); btn_folder.setStyleSheet("background-color:#ffc107; color:black;"); top.addWidget(btn_folder)
        btn_load = QPushButton("📥 LOAD DATA"); btn_load.clicked.connect(self.load_excel); top.addWidget(btn_load)
        btn_save = QPushButton("💾 LƯU EXCEL"); btn_save.clicked.connect(self.save_excel); top.addWidget(btn_save)
        layout.addLayout(top)

        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        
        tab1 = QWidget(); l1 = QVBoxLayout(tab1)
        filter_frame = QFrame(); filter_frame.setStyleSheet("background:#e3f2fd;")
        fl = QHBoxLayout(filter_frame); fl.setContentsMargins(5,5,5,5)
        self.btn_select_all = QPushButton("☑️ CHỌN ALL"); self.btn_select_all.clicked.connect(self.toggle_select_all); fl.addWidget(self.btn_select_all)
        self.txt_search = QLineEdit(); self.txt_search.setPlaceholderText("Tìm kiếm..."); self.txt_search.textChanged.connect(self.apply_filter)
        fl.addWidget(QLabel("🔍")); fl.addWidget(self.txt_search); fl.addStretch()
        self.combo_status = QComboBox(); self.combo_status.addItems(["All", "Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"]); self.combo_status.currentTextChanged.connect(self.apply_filter)
        fl.addWidget(QLabel("📌")); fl.addWidget(self.combo_status); l1.addWidget(filter_frame)

        self.lbl_status = QLabel("Sẵn sàng."); l1.addWidget(self.lbl_status)

        self.table = QTableWidget(); self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["CHỌN", "IMG", "Tiêu Đề", "Views", "Trạng Thái", "QUẢN LÝ", "Link"])
        self.table.verticalHeader().setDefaultSectionSize(70); self.table.setIconSize(QSize(60, 80))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 50)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 80)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive); self.table.setColumnWidth(2, 350)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        l1.addWidget(self.table)
        self.tabs.addTab(tab1, "🎬 1. DANH SÁCH VIDEO")

        self.editor_widget = EmbeddedEditorWidget()
        self.editor_widget.render_requested.connect(self.start_batch_render)
        self.tabs.addTab(self.editor_widget, "🏭 2. XƯỞNG RENDER")
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def start_scraping(self):
        user = self.txt_user.text().strip(); proxy = self.txt_proxy.text().strip()
        if user.startswith("@"): user = user[1:]
        if not user: return
        self.current_username = user; self.table.setRowCount(0); self.video_paths = {}
        self.worker = ScraperWorker(user, proxy)
        self.worker.progress_log_signal.connect(lambda t: self.lbl_status.setText(t))
        
        self.worker.video_found_signal.connect(self.on_video_found)
        self.worker.download_progress_signal.connect(self.on_download_progress)
        self.worker.video_finished_signal.connect(self.on_video_finished)
        self.worker.finished_signal.connect(self.finish_scraping)
        
        self.worker.start()

    def on_video_found(self, link):
        r = self.table.rowCount(); self.table.insertRow(r)
        chk = QTableWidgetItem(); chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled); chk.setCheckState(Qt.CheckState.Unchecked); self.table.setItem(r, 0, chk)
        self.table.setItem(r, 1, QTableWidgetItem("..."))
        self.table.setItem(r, 2, QTableWidgetItem("Đang tải..."))
        self.table.setItem(r, 3, QTableWidgetItem("..."))
        p_bar = QProgressBar(); p_bar.setStyleSheet("QProgressBar {border: 1px solid grey; border-radius: 5px; text-align: center;} QProgressBar::chunk {background-color: #05B8CC;}"); p_bar.setValue(0); self.table.setCellWidget(r, 4, p_bar)
        self.table.setItem(r, 5, QTableWidgetItem(""))
        self.table.setItem(r, 6, QTableWidgetItem(link))

    def on_download_progress(self, link, percent):
        items = self.table.findItems(link, Qt.MatchFlag.MatchExactly)
        if items:
            row = items[0].row()
            p_bar = self.table.cellWidget(row, 4)
            if isinstance(p_bar, QProgressBar): p_bar.setValue(percent)

    def on_video_finished(self, data):
        items = self.table.findItems(data['Link'], Qt.MatchFlag.MatchExactly)
        if items:
            r = items[0].row()
            img = QTableWidgetItem()
            if data.get('Thumb_Data'):
                p = QPixmap(); p.loadFromData(data['Thumb_Data']); img.setIcon(QIcon(p))
            else: img.setText("No Img")
            self.table.setItem(r, 1, img)
            self.table.setItem(r, 2, QTableWidgetItem(str(data['Title'])))
            v = QTableWidgetItem(); v.setData(Qt.ItemDataRole.DisplayRole, f"{data['Views']:,}"); v.setData(Qt.ItemDataRole.EditRole, data['Views']); self.table.setItem(r, 3, v)
            self.table.removeCellWidget(r, 4)
            st = QTableWidgetItem("✅ Đã tải"); st.setForeground(QColor("green")); self.table.setItem(r, 4, st)
            cb = QComboBox(); cb.addItems(["Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"]); cb.currentTextChanged.connect(self.apply_filter); self.table.setCellWidget(r, 5, cb)
            if data.get('Local_Path'): self.video_paths[data['Link']] = data['Local_Path']

    def toggle_select_all(self):
        rows = self.table.rowCount()
        if rows == 0: return
        first_item = self.table.item(0, 0)
        new_state = Qt.CheckState.Checked if first_item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
        for r in range(rows):
            if not self.table.isRowHidden(r): self.table.item(r, 0).setCheckState(new_state)

    def on_tab_changed(self, index):
        if index == 1:
            items_to_render = []
            for r in range(self.table.rowCount()):
                chk_item = self.table.item(r, 0)
                if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                    link = self.table.item(r, 6).text(); path = self.video_paths.get(link)
                    if path and os.path.exists(path): items_to_render.append({'Local_Path': path, 'Link': link})
            if not items_to_render:
                QMessageBox.warning(self, "Chú ý", "Hãy TÍCH CHỌN video ở Tab 1 trước!"); self.tabs.setCurrentIndex(0) 
            else: self.editor_widget.set_queue(items_to_render)

    def start_batch_render(self, options):
        if not self.editor_widget.queue_items: QMessageBox.warning(self, "Lỗi", "Danh sách chờ trống!"); return
        self.editor_widget.btn_render.setEnabled(False); self.editor_widget.log_message("⏳ BẮT ĐẦU RENDER...")
        self.r_worker = RenderWorker(self.editor_widget.queue_items, options)
        self.r_worker.progress_signal.connect(self.update_render_progress)
        self.r_worker.finished_signal.connect(self.render_finished)
        self.r_worker.start()

    def update_render_progress(self, val, msg): self.editor_widget.update_progress(val); self.editor_widget.log_message(msg)
    def render_finished(self): self.editor_widget.btn_render.setEnabled(True); self.editor_widget.log_message("✅ HOÀN TẤT!"); QMessageBox.information(self, "OK", "Đã Render Xong!")
    def finish_scraping(self): self.lbl_status.setText("✅ Xong!"); QMessageBox.information(self, "OK", "Quét xong!"); self.save_excel()
    def open_folder(self):
        if self.current_username:
            path = os.path.join(BASE_DATA_FOLDER, self.current_username)
            if os.path.exists(path): os.startfile(path)
    def save_excel(self):
        if not self.current_username: return
        data = []
        for r in range(self.table.rowCount()):
            cb = self.table.cellWidget(r, 5)
            # Fix lỗi khi đang tải mà bấm lưu (chưa có item text)
            try: title = self.table.item(r, 2).text()
            except: title = "Downloading..."
            try: view = self.table.item(r, 3).data(Qt.ItemDataRole.EditRole)
            except: view = 0
            # Check nếu đang là progress bar thì ghi "Đang tải"
            if self.table.cellWidget(r, 4): status = "Đang tải"
            else: status = self.table.item(r, 4).text()
            
            reup = cb.currentText() if cb else "Chưa đăng"
            link = self.table.item(r, 6).text()
            path = self.video_paths.get(link, "")
            
            data.append({ 'Tên Video': title, 'Views': view, 'Trạng Thái': status, 'Reup_Status': reup, 'Link': link, 'Local_Path': path })
        df = pd.DataFrame(data)
        path = os.path.join(BASE_DATA_FOLDER, self.current_username)
        os.makedirs(path, exist_ok=True)
        fname = os.path.join(path, f"Report_{self.current_username}.xlsx")
        
        # --- FIX LỖI CÚ PHÁP Ở ĐÂY (TÁCH DÒNG) ---
        try:
            with pd.ExcelWriter(fname, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            QMessageBox.information(self, "OK", f"Đã lưu: {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
        # ----------------------------------------

    def load_excel(self):
        start_dir = os.path.join(os.getcwd(), BASE_DATA_FOLDER); 
        if not os.path.exists(start_dir): start_dir = os.getcwd()
        fname, _ = QFileDialog.getOpenFileName(self, "Mở Excel", start_dir, "Excel (*.xlsx)")
        if fname:
            try:
                folder_path = os.path.dirname(fname); self.current_username = os.path.basename(folder_path); self.txt_user.setText(self.current_username); self.table.setRowCount(0); self.video_paths = {}
                df = pd.read_excel(fname)
                try: files_in_folder = os.listdir(folder_path)
                except: files_in_folder = []
                for index, row in df.iterrows():
                    link = str(row.get('Link', '') if 'Link' in df.columns else row.get('Link Gốc', ''))
                    title = str(row.get('Tên Video', '') if 'Tên Video' in df.columns else row.get('Title', ''))
                    local_path = str(row.get('Local_Path', ''))
                    thumb_data = None; found_base = ""
                    def clean_str(s): return re.sub(r'[^a-zA-Z0-9]', '', s).lower()
                    clean_title_excel = clean_str(title)[:30] 
                    if not local_path or local_path == 'nan' or not os.path.exists(local_path):
                        for f in files_in_folder:
                            if not f.endswith(".mp4"): continue
                            if clean_title_excel in clean_str(f): local_path = os.path.join(folder_path, f); found_base = os.path.splitext(f)[0]; break
                    else: found_base = os.path.splitext(os.path.basename(local_path))[0]
                    if found_base:
                        # Fix logic tìm ảnh (để chắc chắn tìm được ảnh của V5.5)
                        for f in files_in_folder:
                            # Tìm file bắt đầu bằng found_base và có đuôi ảnh
                            if f.startswith(found_base) and (f.endswith(".webp") or f.endswith(".jpg") or f.endswith(".image") or f.endswith(".png")):
                                try: 
                                    with open(os.path.join(folder_path, f), 'rb') as f_img: 
                                        thumb_data = f_img.read()
                                    break
                                except: pass
                    
                    self.add_row_view_mode({'Title': title, 'Views': row.get('Views', 0), 'Status': '✅ Đã tải', 'Reup_Status': row.get('Reup_Status', 'Chưa đăng'), 'Link': link, 'Local_Path': local_path, 'Thumb_Data': thumb_data})
                self.lbl_status.setText(f"📂 Load xong: {self.current_username}")
            except Exception as e: QMessageBox.critical(self, "Lỗi", str(e))
    
    def add_row_view_mode(self, data):
        r = self.table.rowCount(); self.table.insertRow(r)
        chk = QTableWidgetItem(); chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled); chk.setCheckState(Qt.CheckState.Unchecked); self.table.setItem(r, 0, chk)
        img = QTableWidgetItem()
        if data.get('Thumb_Data'): p = QPixmap(); p.loadFromData(data['Thumb_Data']); img.setIcon(QIcon(p))
        else: img.setText("No Img")
        self.table.setItem(r, 1, img)
        if data.get('Local_Path'): self.video_paths[data['Link']] = data['Local_Path']
        self.table.setItem(r, 2, QTableWidgetItem(str(data['Title'])))
        v = QTableWidgetItem(); v.setData(Qt.ItemDataRole.DisplayRole, f"{data['Views']:,}"); v.setData(Qt.ItemDataRole.EditRole, data['Views']); self.table.setItem(r, 3, v)
        st = QTableWidgetItem(data['Status']); st.setForeground(QColor("green")); self.table.setItem(r, 4, st)
        cb = QComboBox(); cb.addItems(["Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"]); current = str(data.get('Reup_Status', 'Chưa đăng')); idx = cb.findText(current); 
        if idx >= 0: cb.setCurrentIndex(idx)
        cb.currentTextChanged.connect(self.apply_filter); self.table.setCellWidget(r, 5, cb)
        self.table.setItem(r, 6, QTableWidgetItem(data['Link']))

    def apply_filter(self):
        txt = self.txt_search.text().lower(); fs = self.combo_status.currentText()
        for r in range(self.table.rowCount()):
            t = self.table.item(r, 2).text().lower(); s = self.table.cellWidget(r, 5).currentText(); show = True
            if txt not in t: show = False
            if fs != "All" and fs != s: show = False
            self.table.setRowHidden(r, not show)
    def on_cell_clicked(self, r, c):
        if c in [1, 2]:
            lnk = self.table.item(r, 6).text(); path = self.video_paths.get(lnk)
            if path and os.path.exists(path): os.startfile(path)
            else: os.startfile(lnk)
    def show_context_menu(self, pos):
        menu = QMenu(self); copy_action = QAction("📋 Copy Nội Dung", self); copy_action.triggered.connect(self.copy_cell_content); menu.addAction(copy_action)
        copy_link_action = QAction("🔗 Copy Link Gốc", self); copy_link_action.triggered.connect(self.copy_link_row); menu.addAction(copy_link_action); menu.exec(QCursor.pos())
    def copy_cell_content(self):
        item = self.table.currentItem(); 
        if item: QApplication.clipboard().setText(item.text())
    def copy_link_row(self):
        row = self.table.currentRow(); 
        if row >= 0: QApplication.clipboard().setText(self.table.item(row, 6).text())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TikTokManagerApp()
    window.show()
    sys.exit(app.exec())