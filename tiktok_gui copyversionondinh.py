import sys
import os

# Ép Tool tìm thư viện CUDA ở ổ D (không chiếm ổ C)
sys.path.insert(0, r"D:\AI_Fix")
os.environ["PATH"] += os.pathsep + r"D:\AI_Fix\nvidia\cublas\lib"
os.environ["PATH"] += os.pathsep + r"D:\AI_Fix\nvidia\cudnn\lib"
import asyncio
import pandas as pd
from datetime import datetime
import yt_dlp
import requests
import subprocess 
import re 
from playwright.async_api import async_playwright
# --- THÊM THƯ VIỆN AI ---
from faster_whisper import WhisperModel
from playwright_stealth import stealth_async

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QFileDialog, QMessageBox, QMenu, QFrame,
                             QDialog, QCheckBox, QGroupBox, QTabWidget, QSlider, QSizePolicy, QListWidget, QProgressBar, QTextEdit, QColorDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QAction, QCursor, QPixmap, QIcon, QPainter, QTransform, QPen

BASE_DATA_FOLDER = "TIKTOK_DATA"

# ============================================================================
# 0. AI SUBTITLE GENERATOR (NEW)
# ============================================================================
class AISubtitleGenerator:
    def __init__(self):
        # Chuyển sang 'cpu' và 'int8' để không bao giờ bị lỗi thiếu DLL nữa
        self.model = WhisperModel("base", device="cpu", compute_type="int8")

    def format_time_ass(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    def create_sub_karaoke(self, video_path, output_ass, color_hex="#FFFF00", effect_type="Karaoke", margin_v=500):
        # Chuyển Hex (RGB) sang định dạng ASS (BGR)
        r, g, b = color_hex[1:3], color_hex[3:5], color_hex[5:7]
        ass_color = f"&H00{b}{g}{r}&" # Màu bro chọn (Màu sáng lên)
        bg_color = "&H00FFFFFF&"     # Màu mặc định (Trắng - lúc chưa đọc tới)

        # Transcribe lấy thời gian từng từ
        segments, info = self.model.transcribe(video_path, beam_size=5, language="vi", word_timestamps=True)
        
        # Style này cực giống TikTok: Chữ to (95), viền dày (5), vị trí do bro chọn
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokStyle,Arial,95,{ass_color},{bg_color},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(output_ass, "w", encoding="utf-8") as f:
            f.write(ass_header)
            for segment in segments:
                words = list(segment.words)
                if not words: continue

                # Cắt dòng 4 từ một để chữ to không bị tràn màn hình
                chunk_size = 4 
                for i in range(0, len(words), chunk_size):
                    chunk = words[i:i + chunk_size]
                    start_time = self.format_time_ass(chunk[0].start)
                    end_time = self.format_time_ass(chunk[-1].end)
                    
                    line_text = ""
                    for w in chunk:
                        # Thời gian chạy của mỗi từ (centiseconds)
                        duration = int((w.end - w.start) * 100)
                        word_clean = w.word.strip().upper()
                        if effect_type == "Karaoke":
                            line_text += f"{{\\k{duration}}}{word_clean} "
                        else:
                            line_text += f"{word_clean} "
                    
                    f.write(f"Dialogue: 0,{start_time},{end_time},TikTokStyle,,0,0,0,,{line_text.strip()}\n")
        return True

# ============================================================================
# 1. RENDER ENGINE (CẬP NHẬT FILTER SUB)
# ============================================================================
class RenderEngine:
    def __init__(self):
        self.ffmpeg_exe = "ffmpeg.exe"
        self.ffmpeg_ready = os.path.exists(self.ffmpeg_exe)

    def extract_frame(self, video_path):
        if not self.ffmpeg_ready: return None
        try:
            cmd = [self.ffmpeg_exe, '-ss', '00:00:01', '-i', video_path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-']
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, startupinfo=startupinfo)
            return proc.stdout
        except: return None

    def render_video(self, input_path, output_path, options):
        if not self.ffmpeg_ready: return False, "Thiếu file ffmpeg.exe!"
        
        cmd = [self.ffmpeg_exe, '-y', '-i', input_path]
        filter_chain = []
        
        # 1. Video Filters cơ bản
        bg_filters = []
        if options['flip']: bg_filters.append("hflip") # Lật ngang
        if options['speed_1_1']: bg_filters.append("setpts=PTS/1.1")
        
        # 2. XỬ LÝ SUBTITLES (MỚI)
        if options.get('sub_path'):
            # FFmpeg yêu cầu escape đường dẫn sub (thay \ thành / và : thành \:)
            escaped_sub = options['sub_path'].replace("\\", "/").replace(":", "\\:")
            bg_filters.append(f"subtitles='{escaped_sub}':force_style='Alignment=2'")

        # Gộp filter cho video gốc
        if bg_filters:
            filter_chain.append(f"[0:v]{','.join(bg_filters)}[bg]")
            bg_stream = "[bg]"
        else:
            filter_chain.append("[0:v]null[bg]")
            bg_stream = "[bg]"

        # 2. Xử lý Logo (Nếu có)
        if options['logo_path']:
            cmd.extend(['-i', options['logo_path']]) # Input 1 là Logo
            
            # Tính toán tham số
            scale_pct = options['logo_scale'] / 100.0
            opacity_val = options['logo_opacity'] / 100.0
            x_expr = f"(main_w-overlay_w)*{options['logo_x']}/100"
            y_expr = f"(main_h-overlay_h)*{options['logo_y']}/100"
            
            # Chuỗi lệnh Logo:
            # [1:v][bg]scale2ref... -> Scale logo theo [bg] (video nền đã lật)
            # format=rgba,colorchannelmixer... -> Chỉnh độ mờ
            # [bg][logo_out]overlay... -> Đắp lên nhau
            
            logo_filter = (f"[1:v]{bg_stream}scale2ref=w=iw*{scale_pct}:h=-1[logo_scaled][bg_ref];"
                           f"[logo_scaled]format=rgba,colorchannelmixer=aa={opacity_val}[logo_final];"
                           f"[bg_ref][logo_final]overlay=x={x_expr}:y={y_expr}[v_out]")
            
            filter_chain.append(logo_filter)
            final_out = "[v_out]"
        else:
            # Không có logo thì output chính là bg
            final_out = bg_stream

        # Gộp chuỗi filter
        cmd.extend(['-filter_complex', ";".join(filter_chain)])
        cmd.extend(['-map', final_out])

        # 3. Xử lý Audio
        if options['mute_audio']: pass 
        elif options['speed_1_1']:
            cmd.extend(['-filter:a', "atempo=1.1"])
            cmd.extend(['-map', '0:a'])
        else:
            cmd.extend(['-map', '0:a'])

        # 4. GPU Output
        cmd.extend([
            '-c:v', 'h264_nvenc', '-preset', 'p4', '-rc', 'constqp', '-qp', '26', 
            '-pix_fmt', 'yuv420p', 
            '-c:a', 'aac', 
            output_path
        ])
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, startupinfo=startupinfo)
            return True, "OK"
        except subprocess.CalledProcessError as e: return False, f"Lỗi Render: {e}"
        except Exception as e: return False, str(e)

# ============================================================================
# 2. BACKEND & WORKER (GIỮ NGUYÊN)
# ============================================================================
class TikTokBackend:
    def parse_view_count(self, text):
        try:
            text = text.strip().upper()
            if 'K' in text: return int(float(text.replace('K', '').strip()) * 1000)
            elif 'M' in text: return int(float(text.replace('M', '').strip()) * 1000000)
            else: return int(''.join(filter(str.isdigit, text)))
        except: return 0
    def download_video(self, link, username):
        user_folder = os.path.join(BASE_DATA_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        ydl_opts = {
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
                thumb = info.get('thumbnail', None)
                ydl.download([link])
                fname = ydl.prepare_filename(info)
                return True, title, thumb, fname
        except Exception as e: return False, str(e), None, None

class ScraperWorker(QThread):
    progress_signal = pyqtSignal(str)
    data_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()

    def __init__(self, username, proxy_str=None):
        super().__init__()
        self.username = username
        self.proxy_str = proxy_str
        self.backend = TikTokBackend()

    def run(self):
        asyncio.run(self.run_scraper())

    async def run_scraper(self):
        # Xử lý username nếu người dùng nhập có @
        clean_user = self.username.replace("@", "").strip()
        url = f"https://www.tiktok.com/@{clean_user}"
        
        self.progress_signal.emit(f"🚀 Đang khởi động trình duyệt...")
        
        # Thư mục Profile để nhớ đăng nhập
        user_data_dir = os.path.join(os.getcwd(), "chrome_profile")

        async with async_playwright() as p:
            # 1. Setup Proxy
            proxy_config = None
            if self.proxy_str and len(self.proxy_str.split(':')) == 4:
                parts = self.proxy_str.split(':')
                proxy_config = {
                    "server": f"http://{parts[0]}:{parts[1]}",
                    "username": parts[2], "password": parts[3]
                }
                self.progress_signal.emit(f"🌐 Proxy: {parts[0]}...")
            else:
                self.progress_signal.emit(f"🏠 Mạng thường (No Proxy)...")

            # 2. Launch Browser
            try:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=False, # Hiện trình duyệt
                    proxy=proxy_config,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--start-maximized',
                        '--no-sandbox'
                    ],
                    viewport=None
                )
                
                page = browser.pages[0]
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                self.progress_signal.emit(f"🔗 Vào kênh: {clean_user}")
                
                # Tải trang (Timeout 60s)
                try:
                    await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                except:
                    self.progress_signal.emit("⚠️ Mạng chậm, vẫn đang cố xử lý...")

                # 3. CHIẾN THUẬT MỚI: KHÔNG CHỜ SELECTOR CỤ THỂ NỮA
                self.progress_signal.emit("⏳ Đợi 5 giây cho web ổn định...")
                await asyncio.sleep(5) 

                # Di chuột một chút để kích hoạt JS
                await page.mouse.move(100, 100)
                await page.mouse.move(500, 500)

                # 4. CUỘN TRANG BẤT CHẤP (Blind Scroll)
                self.progress_signal.emit("� Bắt đầu cuộn trang...")
                for i in range(5): # Tăng lên 5 lần cuộn để lấy nhiều video hơn
                    await page.mouse.wheel(0, 3000) # Cuộn mạnh xuống
                    await asyncio.sleep(2) # Nghỉ để TikTok load API
                    self.progress_signal.emit(f"📜 Đang cuộn lần {i+1}...")

                # 5. QUÉT TOÀN BỘ LINK (Get All Links)
                self.progress_signal.emit("🔍 Đang lọc video từ trang...")
                
                # Lấy tất cả thẻ 'a' trên trang, không cần class cụ thể
                all_elements = await page.query_selector_all('a')
                
                processed = set()
                count = 0

                for el in all_elements:
                    try:
                        href = await el.get_attribute('href')
                        if not href: continue
                        
                        # Chỉ cần link có chứa "/video/" là lụm
                        if '/video/' in href:
                            clean_link = href.split('?')[0].strip()
                            # Kiểm tra trùng lặp
                            if clean_link in processed: continue
                            processed.add(clean_link)
                            
                            count += 1
                            self.progress_signal.emit(f"⬇️ Tìm thấy: {clean_link[-15:]}...")
                            
                            # Download
                            success, title, thumb_url, local_path = self.backend.download_video(clean_link, clean_user)
                            
                            # Lấy view (Cố gắng lấy text bên trong thẻ a hoặc thẻ cha)
                            views = 0
                            try:
                                text = await el.inner_text()
                                if text: views = self.backend.parse_view_count(text)
                            except: pass

                            # Lấy ảnh preview
                            pixmap_data = None
                            if thumb_url:
                                try: pixmap_data = requests.get(thumb_url, timeout=3).content
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
                
                if count == 0:
                    self.progress_signal.emit("❌ KHÔNG THẤY VIDEO! (Có thể bị Captcha chặn hoặc Kênh Trống)")
                    # Giữ lại trình duyệt 30s để Bro kiểm tra
                    await asyncio.sleep(30)
                else:
                    self.progress_signal.emit(f"✨ XONG! Tổng cộng: {count} video.")
                
                await browser.close()
                self.finished_signal.emit()

            except Exception as e:
                self.progress_signal.emit(f"❌ LỖI HỆ THỐNG: {str(e)}")





class RenderWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal()
    def __init__(self, items, options):
        super().__init__()
        self.items = items
        self.options = options
        self.engine = RenderEngine()
        self.ai_sub = AISubtitleGenerator() if options.get('use_ai_sub') else None # Khởi tạo AI nếu cần

    def run(self):
        total = len(self.items)
        for i, item in enumerate(self.items):
            input_path = item['Local_Path']
            if not input_path or not os.path.exists(input_path): continue
            
            folder = os.path.dirname(input_path)
            render_folder = os.path.join(folder, "Rendered")
            os.makedirs(render_folder, exist_ok=True)
            name_no_ext = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(render_folder, f"{name_no_ext}_EDITED.mp4")

            # --- BƯỚC MỚI: TẠO SUB BẰNG AI ---
            if self.ai_sub:
                self.progress_signal.emit(int((i / total) * 100), f"🧠 AI đang nghe: {name_no_ext[:15]}...")
                ass_path = os.path.join(render_folder, f"{name_no_ext}.ass")
                try:
                    self.ai_sub.create_sub_karaoke(
                        input_path, ass_path,
                        color_hex=self.options.get('sub_color', '#FFFF00'),
                        effect_type=self.options.get('sub_effect', 'Karaoke'),
                        margin_v=self.options.get('sub_margin_v', 500)
                    )
                    self.options['sub_path'] = ass_path
                except Exception as e:
                    self.progress_signal.emit(int((i / total) * 100), f"⚠️ Lỗi AI Sub: {str(e)}")
                    self.options['sub_path'] = None
            else:
                self.options['sub_path'] = None

            # --- BƯỚC RENDER ---
            self.progress_signal.emit(int((i / total) * 100), f"🎬 Rendering ({i+1}/{total}): {name_no_ext[:15]}...")
            success, msg = self.engine.render_video(input_path, output_path, self.options)
            
            if success: self.progress_signal.emit(int(((i+1) / total) * 100), f"✅ Xong: {name_no_ext[:15]}")
            else: self.progress_signal.emit(int(((i+1) / total) * 100), f"❌ Lỗi: {msg}")
            
        self.finished_signal.emit()

# ============================================================================
# 3. WIDGET EDITOR (GIỮ NGUYÊN)
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
        self.engine = RenderEngine()
        self.original_pixmap = None
        self.current_video_path = None
        self.queue_items = []

        layout = QHBoxLayout(self)

        # CỘT 1
        left_panel = QFrame(); left_panel.setFixedWidth(300); left_layout = QVBoxLayout(left_panel)
        g_vid = QGroupBox("1. HÌNH ẢNH"); l_vid = QVBoxLayout()
        self.chk_flip = QCheckBox("Lật Ngược"); self.chk_flip.stateChanged.connect(self.update_preview)
        self.chk_speed = QCheckBox("Tăng Tốc 1.1x")
        self.chk_ai_sub = QCheckBox("🧠 Tạo Sub Tiếng Việt (AI)")
        self.chk_ai_sub.setStyleSheet("color: #d63384; font-weight: bold;")

        # --- Nút chọn màu ---
        self.btn_pick_color = QPushButton("🎨 Chọn Màu Chữ")
        self.btn_pick_color.clicked.connect(self.pick_sub_color)
        self.current_sub_color = "#FFFF00"  # Mặc định vàng
        self.lbl_color_demo = QLabel()
        self.lbl_color_demo.setFixedSize(20, 20)
        self.lbl_color_demo.setStyleSheet(f"background-color: {self.current_sub_color}; border: 1px solid white;")

        # --- Chọn hiệu ứng ---
        self.combo_effect = QComboBox()
        self.combo_effect.addItems(["Karaoke (Chữ chạy)", "Hiện từng dòng"])

        color_layout = QHBoxLayout()
        color_layout.addWidget(self.btn_pick_color)
        color_layout.addWidget(self.lbl_color_demo)

        # --- Thanh chỉnh vị trí Sub ---
        l_vid.addWidget(QLabel("Vị trí Sub (Cao/Thấp):"))
        self.sl_sub_y = QSlider(Qt.Orientation.Horizontal)
        self.sl_sub_y.setRange(100, 1700)
        self.sl_sub_y.setValue(500)
        self.sl_sub_y.valueChanged.connect(self.update_preview)

        l_vid.addWidget(self.chk_flip); l_vid.addWidget(self.chk_speed); l_vid.addWidget(self.chk_ai_sub)
        l_vid.addLayout(color_layout)
        l_vid.addWidget(QLabel("Hiệu ứng:"))
        l_vid.addWidget(self.combo_effect)
        l_vid.addWidget(self.sl_sub_y)
        g_vid.setLayout(l_vid)

        g_aud = QGroupBox("2. ÂM THANH"); l_aud = QHBoxLayout()
        self.chk_mute = QCheckBox("Tắt Tiếng"); self.chk_mute.stateChanged.connect(self.update_audio_visual)
        self.lbl_audio = QLabel("🔊"); l_aud.addWidget(self.chk_mute); l_aud.addWidget(self.lbl_audio); g_aud.setLayout(l_aud)

        g_logo = QGroupBox("3. LOGO (KÉO THẢ)")
        l_logo = QVBoxLayout()
        btn_brow = QPushButton("Chọn Ảnh..."); btn_brow.clicked.connect(self.browse_logo)
        self.lbl_logo_path = QLabel("Chưa chọn"); self.lbl_logo_path.setStyleSheet("color:gray; font-size:9px")
        l_logo.addWidget(btn_brow); l_logo.addWidget(self.lbl_logo_path)
        l_logo.addWidget(QLabel("Size:")); self.sl_scale = QSlider(Qt.Orientation.Horizontal); self.sl_scale.setRange(5, 80); self.sl_scale.setValue(20); self.sl_scale.valueChanged.connect(self.update_preview); l_logo.addWidget(self.sl_scale)
        l_logo.addWidget(QLabel("Độ mờ (Opacity):")); self.sl_opacity = QSlider(Qt.Orientation.Horizontal); self.sl_opacity.setRange(10, 100); self.sl_opacity.setValue(100); self.sl_opacity.valueChanged.connect(self.update_preview); l_logo.addWidget(self.sl_opacity)
        self.sl_x = QSlider(Qt.Orientation.Horizontal); self.sl_x.setRange(0, 100); self.sl_x.setValue(95); self.sl_x.setVisible(False)
        self.sl_y = QSlider(Qt.Orientation.Horizontal); self.sl_y.setRange(0, 100); self.sl_y.setValue(5); self.sl_y.setVisible(False)
        g_logo.setLayout(l_logo)

        self.btn_render = QPushButton("🔥 RENDER TẤT CẢ 🔥")
        self.btn_render.setStyleSheet("background-color: #d63384; color: white; font-weight: bold; height: 50px;")
        self.btn_render.clicked.connect(self.emit_render_signal)

        left_layout.addWidget(g_vid); left_layout.addWidget(g_aud); left_layout.addWidget(g_logo); left_layout.addStretch(); left_layout.addWidget(self.btn_render)

        # CỘT 2
        mid_panel = QFrame(); mid_layout = QVBoxLayout(mid_panel); mid_panel.setStyleSheet("background: #000;")
        self.lbl_screen = DraggablePreviewLabel("Chọn video bên phải để xem")
        self.lbl_screen.positionChanged.connect(self.on_mouse_drag)
        self.lbl_screen.setScaledContents(False)
        self.lbl_screen.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        mid_layout.addWidget(self.lbl_screen)

        # CỘT 3
        right_panel = QFrame(); right_panel.setFixedWidth(300); right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("DANH SÁCH CHỜ:"))
        self.list_queue = QListWidget(); self.list_queue.itemClicked.connect(self.on_queue_item_clicked) 
        right_layout.addWidget(self.list_queue)
        right_layout.addWidget(QLabel("TIẾN TRÌNH:"))
        self.p_bar = QProgressBar(); right_layout.addWidget(self.p_bar)
        self.txt_log = QTextEdit(); self.txt_log.setReadOnly(True); self.txt_log.setStyleSheet("font-size:10px; color: #333;")
        right_layout.addWidget(self.txt_log)

        layout.addWidget(left_panel); layout.addWidget(mid_panel); layout.addWidget(right_panel)

    def set_queue(self, items):
        self.queue_items = items; self.list_queue.clear(); self.txt_log.clear(); self.p_bar.setValue(0)
        for item in items: self.list_queue.addItem(os.path.basename(item['Local_Path']))
        if items: self.load_video(items[0]['Local_Path'])

    def log_message(self, msg):
        self.txt_log.append(msg); self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    def update_progress(self, val): self.p_bar.setValue(val)

    def on_queue_item_clicked(self, item):
        idx = self.list_queue.row(item)
        if idx >= 0: self.load_video(self.queue_items[idx]['Local_Path'])

    def load_video(self, video_path):
        self.current_video_path = video_path
        img_data = self.engine.extract_frame(video_path)
        if img_data:
            pixmap = QPixmap(); pixmap.loadFromData(img_data)
            self.original_pixmap = pixmap; self.update_preview()
        else: self.lbl_screen.setText("❌ Lỗi Video")

    def on_mouse_drag(self, x, y):
        self.sl_x.setValue(x); self.sl_y.setValue(y); self.update_preview()

    def update_preview(self):
        if not self.original_pixmap: return
        preview = self.original_pixmap.copy()
        
        # 1. Vẽ lật ngược nếu có
        if self.chk_flip.isChecked():
            preview = preview.transformed(QTransform().scale(-1, 1), Qt.TransformationMode.SmoothTransformation)
        
        painter = QPainter(preview)
        
        # 2. VẼ CHỮ SUB MẪU ĐỂ XEM TRƯỚC VỊ TRÍ
        if self.chk_ai_sub.isChecked():
            font = QFont("Arial", 80, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Tính toán vị trí dựa trên slider (MarginV tính từ đáy lên)
            margin_v = self.sl_sub_y.value()
            # PlayResY của sub là 1920, ta tính vị trí Y trên ảnh gốc
            y_pos = preview.height() - int((margin_v / 1920) * preview.height())
            
            # Vẽ viền đen cho chữ mẫu
            painter.setPen(QPen(Qt.GlobalColor.black, 10))
            painter.drawText(0, y_pos - 100, preview.width(), 150, Qt.AlignmentFlag.AlignCenter, "MẪU CHỮ CHẠY")
            
            # Vẽ chữ màu bro chọn
            painter.setPen(QColor(self.current_sub_color))
            painter.drawText(0, y_pos - 100, preview.width(), 150, Qt.AlignmentFlag.AlignCenter, "MẪU CHỮ CHẠY")

        # 3. Vẽ Logo nếu có
        logo_path = self.lbl_logo_path.property("path")
        if logo_path and os.path.exists(logo_path):
            logo_pix = QPixmap(logo_path)
            scale_percent = self.sl_scale.value() / 100
            new_w = int(preview.width() * scale_percent)
            logo_pix = logo_pix.scaledToWidth(new_w, Qt.TransformationMode.SmoothTransformation)
            
            opacity = self.sl_opacity.value() / 100.0
            painter.setOpacity(opacity)
            
            pos_x = int((preview.width() - logo_pix.width()) * (self.sl_x.value() / 100))
            pos_y = int((preview.height() - logo_pix.height()) * (self.sl_y.value() / 100))
            painter.drawPixmap(pos_x, pos_y, logo_pix)

        painter.end()
        target_size = self.lbl_screen.size()
        self.lbl_screen.setPixmap(preview.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def browse_logo(self):
        f, _ = QFileDialog.getOpenFileName(self, "Logo", "", "Img (*.png *.jpg)")
        if f: self.lbl_logo_path.setText(os.path.basename(f)); self.lbl_logo_path.setProperty("path", f); self.update_preview()

    def update_audio_visual(self):
        if self.chk_mute.isChecked(): self.lbl_audio.setText("🔇")
        else: self.lbl_audio.setText("🔊")

    def pick_sub_color(self):
        color = QColorDialog.getColor(QColor(self.current_sub_color), self, "Chọn Màu Chữ Sub")
        if color.isValid():
            self.current_sub_color = color.name()
            self.lbl_color_demo.setStyleSheet(f"background-color: {self.current_sub_color}; border: 1px solid white;")
            self.update_preview()

    def get_options(self):
        # Map tên hiệu ứng tiếng Việt -> key cho engine
        effect_map = {"Karaoke (Chữ chạy)": "Karaoke", "Hiện từng dòng": "Normal"}
        return { 
            'flip': self.chk_flip.isChecked(), 'speed_1_1': self.chk_speed.isChecked(), 'mute_audio': self.chk_mute.isChecked(),
            'use_ai_sub': self.chk_ai_sub.isChecked(),
            'sub_color': self.current_sub_color,
            'sub_effect': effect_map.get(self.combo_effect.currentText(), "Karaoke"),
            'sub_margin_v': self.sl_sub_y.value(),
            'logo_path': self.lbl_logo_path.property("path") if self.lbl_logo_path.property("path") else "",
            'logo_x': self.sl_x.value(), 'logo_y': self.sl_y.value(), 'logo_scale': self.sl_scale.value(),
            'logo_opacity': self.sl_opacity.value()
        }
    
    def emit_render_signal(self):
        self.render_requested.emit(self.get_options())
    
    def resizeEvent(self, event): self.update_preview(); super().resizeEvent(event)

# ============================================================================
# MAIN APP
# ============================================================================
class TikTokManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIKTOK MANAGER V11.2 - FINAL FIX (REALLY)")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("QMainWindow {background-color: #f0f2f5;} QLabel {color: #333; font-weight: bold;}")
        
        self.current_username = ""
        self.video_paths = {}

        main = QWidget(); self.setCentralWidget(main); layout = QVBoxLayout(main)

        top = QHBoxLayout()
        top.addWidget(QLabel("Kênh:")); self.txt_user = QLineEdit(); self.txt_user.setPlaceholderText("Nhập ID..."); top.addWidget(self.txt_user)
        
        # Thêm ô Proxy và nhãn trạng thái
        top.addWidget(QLabel("Proxy (IP:PORT:U:P):"))
        self.txt_proxy = QLineEdit()
        self.txt_proxy.setPlaceholderText("Dán proxy vào đây...")
        # Dán sẵn cái của bạn để test
        self.txt_proxy.setText("123.28.194.208:49126:proxymart49126:hJXJBtAm") 
        top.addWidget(self.txt_proxy)

        btn_start = QPushButton("🚀 QUÉT TẢI"); 
        btn_start.clicked.connect(self.start_scraping); 
        btn_start.setStyleSheet("background-color:#007bff; color:white; font-weight:bold;"); 
        top.addWidget(btn_start)
        btn_folder = QPushButton("📂 FOLDER"); btn_folder.clicked.connect(self.open_folder); btn_folder.setStyleSheet("background-color:#ffc107; color:black;"); top.addWidget(btn_folder)
        btn_load = QPushButton("📥 LOAD DATA"); btn_load.clicked.connect(self.load_excel); top.addWidget(btn_load)
        btn_save = QPushButton("💾 LƯU EXCEL"); btn_save.clicked.connect(self.save_excel); top.addWidget(btn_save)
        layout.addLayout(top)

        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        
        # TAB 1
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

        # TAB 2
        self.editor_widget = EmbeddedEditorWidget()
        self.editor_widget.render_requested.connect(self.start_batch_render)
        self.tabs.addTab(self.editor_widget, "🏭 2. XƯỞNG RENDER")
        self.tabs.currentChanged.connect(self.on_tab_changed)

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

    def start_scraping(self):
        user = self.txt_user.text().strip()
        proxy = self.txt_proxy.text().strip() # Lấy proxy từ ô mới thêm
        
        if user.startswith("@"): user = user[1:]
        if not user: return
        
        self.current_username = user; self.table.setRowCount(0); self.video_paths = {}
        
        # Truyền thêm biến proxy vào đây
        self.worker = ScraperWorker(user, proxy) 
        
        self.worker.progress_signal.connect(lambda t: self.lbl_status.setText(t))
        self.worker.data_signal.connect(self.add_row)
        self.worker.finished_signal.connect(self.finish_scraping)
        self.worker.start()

    def add_row(self, data):
        r = self.table.rowCount(); self.table.insertRow(r)
        chk = QTableWidgetItem(); chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled); chk.setCheckState(Qt.CheckState.Unchecked); self.table.setItem(r, 0, chk)
        img = QTableWidgetItem()
        if data.get('Thumb_Data'): p = QPixmap(); p.loadFromData(data['Thumb_Data']); img.setIcon(QIcon(p))
        else: img.setText("No Img")
        self.table.setItem(r, 1, img)
        if data.get('Local_Path'): self.video_paths[data['Link']] = data['Local_Path']
        self.table.setItem(r, 2, QTableWidgetItem(str(data['Title'])))
        v = QTableWidgetItem(); v.setData(Qt.ItemDataRole.DisplayRole, f"{data['Views']:,}"); v.setData(Qt.ItemDataRole.EditRole, data['Views']); self.table.setItem(r, 3, v)
        st = QTableWidgetItem(data['Status']); st.setForeground(QColor("green") if "Đã tải" in data['Status'] else QColor("red")); self.table.setItem(r, 4, st)
        cb = QComboBox(); cb.addItems(["Chưa đăng", "✅ ĐÃ ĐĂNG", "🕒 Lên lịch"]); current = str(data.get('Reup_Status', 'Chưa đăng'))
        if current == 'nan': current = 'Chưa đăng'
        idx = cb.findText(current); 
        if idx >= 0: cb.setCurrentIndex(idx)
        cb.currentTextChanged.connect(self.apply_filter); self.table.setCellWidget(r, 5, cb)
        self.table.setItem(r, 6, QTableWidgetItem(data['Link']))

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
            data.append({ 'Tên Video': self.table.item(r, 2).text(), 'Views': self.table.item(r, 3).data(Qt.ItemDataRole.EditRole), 'Trạng Thái': self.table.item(r, 4).text(), 'Reup_Status': cb.currentText(), 'Link': self.table.item(r, 6).text(), 'Local_Path': self.video_paths.get(self.table.item(r, 6).text(), '') })
        df = pd.DataFrame(data); path = os.path.join(BASE_DATA_FOLDER, self.current_username); os.makedirs(path, exist_ok=True); fname = os.path.join(path, f"Report_{self.current_username}.xlsx")
        try:
            with pd.ExcelWriter(fname, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
            QMessageBox.information(self, "OK", f"Đã lưu: {fname}")
        except Exception as e: QMessageBox.critical(self, "Lỗi", str(e))
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
                        for f in files_in_folder:
                            if f.startswith(found_base) and (f.endswith(".webp") or f.endswith(".jpg") or f.endswith(".image")):
                                try:
                                    with open(os.path.join(folder_path, f), 'rb') as f_img: thumb_data = f_img.read(); break
                                except: pass
                    self.add_row({ 'Title': title, 'Views': row.get('Views', 0), 'Status': row.get('Trạng Thái', ''), 'Reup_Status': row.get('Reup_Status', 'Chưa đăng'), 'Link': link, 'Local_Path': local_path, 'Thumb_Data': thumb_data })
                self.lbl_status.setText(f"📂 Load xong: {self.current_username}")
            except Exception as e: QMessageBox.critical(self, "Lỗi", str(e))
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