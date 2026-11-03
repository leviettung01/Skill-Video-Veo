# -*- coding: utf-8 -*-
import json
import os
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QComboBox, QPushButton, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import httpx

APP_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = APP_DIR / "veo3_config.json"


def load_vbee_token():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return data.get("vbee_token", "")
        except:
            pass
    return ""


def save_vbee_token(token: str):
    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except:
            pass
    data["vbee_token"] = token
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except:
        pass


class VbeeTTSWorker(QThread):
    finished_signal = pyqtSignal(str, str)  # error_msg, output_path
    progress_signal = pyqtSignal(str)

    def __init__(self, token: str, text: str, voice: str, output_path: str):
        super().__init__()
        self.token = token
        self.text = text
        self.voice = voice
        self.output_path = output_path

    def run(self):
        try:
            self.progress_signal.emit("Đang gửi yêu cầu tới Vbee API...")
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            # Sử dụng API public của Vbee AIVoice Studio
            url = "https://vbee.vn/api/v1/convert-tts"
            payload = {
                "input_text": self.text,
                "voice": self.voice,
                "rate": 1.0,
                "audio_type": "mp3"
            }
            
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, headers=headers, json=payload)
                
                if resp.status_code >= 400:
                    err_msg = resp.text[:200]
                    self.finished_signal.emit(f"Lỗi API {resp.status_code}: {err_msg}", "")
                    return
                
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    data = resp.json()
                    audio_url = data.get("audio_link") or data.get("url")
                    if not audio_url:
                        self.finished_signal.emit(f"Không tìm thấy link audio trong phản hồi: {data}", "")
                        return
                    
                    self.progress_signal.emit("Đang tải file audio...")
                    audio_resp = client.get(audio_url)
                    with open(self.output_path, "wb") as f:
                        f.write(audio_resp.content)
                else:
                    with open(self.output_path, "wb") as f:
                        f.write(resp.content)
            
            self.finished_signal.emit("", self.output_path)
            
        except Exception as e:
            self.finished_signal.emit(f"Ngoại lệ: {e}", "")


class VbeeTTSDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎙 Tạo Voice bằng Vbee AI")
        self.setMinimumSize(500, 450)
        
        self.output_mp3 = None
        
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #e2e8f0; font-weight: bold; }
            QLineEdit, QTextEdit { 
                background-color: #1e293b; color: #f8fafc; 
                border: 1px solid #475569; border-radius: 6px; padding: 6px; 
            }
            QComboBox { 
                background: #1e293b; color: #38bdf8; 
                border: 1px solid #475569; border-radius: 4px; padding: 4px; font-weight: bold; 
            }
            QPushButton { 
                background-color: #3b82f6; color: white; border: none; 
                border-radius: 6px; padding: 8px 16px; font-weight: bold; 
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #334155; color: #94a3b8; }
        """)
        
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        
        lay.addWidget(QLabel("🔑 Vbee API Token:"))
        self.edit_token = QLineEdit()
        self.edit_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_token.setText(load_vbee_token())
        self.edit_token.setPlaceholderText("Nhập mã Token từ Vbee Studio...")
        lay.addWidget(self.edit_token)
        
        lay.addWidget(QLabel("🗣 Chọn Giọng Đọc:"))
        self.combo_voice = QComboBox()
        self.combo_voice.addItem("Ngọc Lam (Nữ miền Bắc)", "hn_female_ngoclam")
        self.combo_voice.addItem("Mai Ngọc (Nữ miền Bắc)", "hn_female_maingoc_news")
        self.combo_voice.addItem("Lê Yến (Nữ miền Nam)", "sg_female_leyen_diengiai")
        self.combo_voice.addItem("Xuân Tín (Nam miền Bắc)", "hn_male_xuantin")
        self.combo_voice.addItem("Trọng Lĩnh (Nam miền Nam)", "sg_male_tronglinh")
        self.combo_voice.setEditable(True)
        lay.addWidget(self.combo_voice)
        
        lay.addWidget(QLabel("📝 Nội dung văn bản:"))
        self.edit_text = QTextEdit()
        self.edit_text.setPlaceholderText("Nhập văn bản cần chuyển thành giọng nói tại đây...")
        lay.addWidget(self.edit_text)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #fbbf24; font-size: 11px;")
        lay.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.btn_cancel = QPushButton("Huỷ")
        self.btn_cancel.setStyleSheet("background-color: #475569;")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        self.btn_gen = QPushButton("🎙 Tạo MP3")
        self.btn_gen.clicked.connect(self._generate)
        btns.addWidget(self.btn_gen)
        
        lay.addLayout(btns)
        
        self.worker = None

    def _generate(self):
        token = self.edit_token.text().strip()
        text = self.edit_text.toPlainText().strip()
        voice = self.combo_voice.currentData() or self.combo_voice.currentText()
        
        if not token:
            QMessageBox.warning(self, "Thiếu Token", "Vui lòng nhập Vbee API Token!")
            return
        if not text:
            QMessageBox.warning(self, "Thiếu Văn bản", "Vui lòng nhập văn bản cần đọc!")
            return
            
        save_vbee_token(token)
        
        out_dir = APP_DIR / "output_videos" / "vbee_voices"
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = f"vbee_{int(time.time())}.mp3"
        self.output_mp3 = str(out_dir / fname)
        
        self.btn_gen.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText("Đang khởi tạo kết nối...")
        
        self.worker = VbeeTTSWorker(token, text, voice, self.output_mp3)
        self.worker.progress_signal.connect(self.lbl_status.setText)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()
        
    def _on_finished(self, err_msg, out_path):
        self.btn_gen.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress.setVisible(False)
        
        if err_msg:
            self.lbl_status.setText("❌ Lỗi tạo voice!")
            QMessageBox.critical(self, "Lỗi API", f"Quá trình tạo voice thất bại:\n{err_msg}")
            self.output_mp3 = None
        else:
            self.lbl_status.setText("✅ Tạo voice thành công!")
            QMessageBox.information(self, "Thành công", f"Đã lưu file mp3 tại:\n{out_path}")
            self.accept()
