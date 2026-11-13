# -*- coding: utf-8 -*-
"""
Cửa sổ Python (PyQt6) Quản Lý & Đăng Nhập Đa Tài Khoản Google Flow
Khởi động tức thì (< 0.5s), đọc/ghi trực tiếp data/google_flow_grok/accounts.json
và dùng google_flow_auth.py giống hệt grok_video_tool.py.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

SKILL_DIR = Path(__file__).resolve().parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import google_flow_auth as gfa

AUTH_ROOT = SKILL_DIR / "data" / "google_flow_grok"
ACCOUNTS_FILE = AUTH_ROOT / "accounts.json"
REGISTRY_FILE = AUTH_ROOT / "Flow_nhieu_worker_accounts.json"
DEFAULT_PROJECT_ID = os.environ.get("FLOW_DEFAULT_PROJECT_ID", "").strip()


def _load_accounts() -> list[dict]:
    AUTH_ROOT.mkdir(parents=True, exist_ok=True)
    if not ACCOUNTS_FILE.is_file():
        return []
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8", errors="ignore"))
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
    except Exception:
        return []


def _save_accounts(rows: list[dict]) -> None:
    AUTH_ROOT.mkdir(parents=True, exist_ok=True)
    ACCOUNTS_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_google_account(acc: dict) -> bool:
    name = str(acc.get("name") or "").strip().lower()
    if name.startswith(("codex", "grok", "xai", "openai")):
        return False
    return name.startswith(("google", "flow", "veo")) or bool(acc.get("profile_name"))


def _profile_for_acc(acc: dict) -> str:
    prof = str(acc.get("profile_name") or "").strip()
    if prof:
        return prof
    name = str(acc.get("name") or "").strip()
    clean = re.sub(r"^(?:google|flow|veo)[_:\-\s]*", "", name, flags=re.IGNORECASE).strip()
    if "@" in clean:
        clean = clean.split("@", 1)[0]
    return clean or "default_flow"


def _upsert_registry(email: str, prof: str, proj_id: str) -> None:
    try:
        rows = []
        if REGISTRY_FILE.is_file():
            raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(raw, list):
                rows = [r for r in raw if isinstance(r, dict)]
        pdir, cfile = gfa.profile_paths(AUTH_ROOT, prof)
        matched = None
        for r in rows:
            if str(r.get("email") or "").lower() == email.lower() or Path(str(r.get("profile_dir") or "")).name.lower() == prof.lower():
                matched = r
                break
        if matched is None:
            matched = {
                "email": email,
                "total_generated": 0,
                "total_credits_used": 0,
                "monthly_credits_used": 0,
                "credit_limit": 25000,
                "credits_remaining": 25000,
                "is_grok": False,
            }
            rows.append(matched)
        matched["email"] = email
        matched["profile_dir"] = str(pdir)
        matched["cookies_file"] = str(cfile)
        matched["project_id"] = proj_id or DEFAULT_PROJECT_ID
        matched["status"] = "ready"
        matched["last_login"] = datetime.now().isoformat()
        REGISTRY_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _check_flow_token_fast(token: str):
    import httpx
    def _factory(timeout=12, target_url="", use_proxy=True, **kwargs):
        return httpx.Client(timeout=timeout, follow_redirects=True, **kwargs)
    return gfa.check_token(token, _factory)


def _persist_flow_state_fast(context, snapshot: Path) -> bool:
    try:
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(snapshot))
        return snapshot.is_file()
    except Exception:
        return False


class FastLoginWorker(QThread):
    status_sig = pyqtSignal(str, str)
    success_sig = pyqtSignal(str, str, str)
    error_sig = pyqtSignal(str)

    def __init__(self, profile_name: str):
        super().__init__()
        self.profile_name = profile_name

    def run(self):
        try:
            res = gfa.acquire_session(
                AUTH_ROOT,
                self.profile_name,
                _check_flow_token_fast,
                _persist_flow_state_fast,
                interactive=True,
                expected="",
                cancelled=lambda: False,
                status=lambda msg: self.status_sig.emit(msg, "#a78bfa"),
            )
            if res.ok and res.token:
                eff_email = res.email or f"{self.profile_name}@gmail.com"
                eff_proj = res.project or DEFAULT_PROJECT_ID
                gfa.commit_login(AUTH_ROOT, self.profile_name, eff_email, res.token, eff_proj)
                self.success_sig.emit(eff_email, res.token, eff_proj)
            else:
                self.error_sig.emit(res.error or "Chưa lấy được phiên đăng nhập Google Flow.")
        except Exception as e:
            self.error_sig.emit(str(e))


class FastRefreshWorker(QThread):
    status_sig = pyqtSignal(str, str)
    done_sig = pyqtSignal(int, int)

    def __init__(self, profiles: list[str]):
        super().__init__()
        self.profiles = profiles

    def run(self):
        ok_cnt = 0
        exp_cnt = 0
        accs = _load_accounts()
        for prof in self.profiles:
            self.status_sig.emit(f"🔄 Đang kiểm tra & lấy Cookie mới cho Profile '{prof}'...", "#38bdf8")
            res = gfa.acquire_session(
                AUTH_ROOT,
                prof,
                _check_flow_token_fast,
                _persist_flow_state_fast,
                interactive=False,
                expected="",
            )
            if res.ok and res.token:
                ok_cnt += 1
                email = res.email or f"{prof}@gmail.com"
                proj_id = res.project or DEFAULT_PROJECT_ID
                for a in accs:
                    if _is_google_account(a) and _profile_for_acc(a).lower() == prof.lower():
                        a["api_key"] = res.token
                        a["auth_state"] = "ready"
                        a["auth_revision"] = time.time_ns()
                        if email:
                            a["google_email"] = email
                            a["name"] = f"Google_{email}"
                        if proj_id:
                            a["proxy_url"] = proj_id
                        _upsert_registry(email, prof, proj_id)
            else:
                exp_cnt += 1
        _save_accounts(accs)
        self.done_sig.emit(ok_cnt, exp_cnt)


class GoogleFlowAccountWindow(QMainWindow):
    def __init__(self, initial_profile: str = "", auto_start_login: bool = False):
        super().__init__()
        self.setWindowTitle("🐍 Quản Lý & Đăng Nhập Đa Tài Khoản Google Flow (Python Desktop Tool)")
        self.resize(840, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.login_worker = None
        self.refresh_worker = None

        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QFrame#card { background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; }
            QLineEdit { background-color: #090d16; border: 1px solid #475569; border-radius: 6px; padding: 7px 10px; color: #f8fafc; font-size: 13px; }
            QLineEdit:focus { border-color: #3b82f6; }
            QPushButton { border-radius: 6px; padding: 7px 12px; font-weight: bold; font-size: 12px; }
        """)

        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(14, 14, 14, 14)
        main_lay.setSpacing(10)

        hdr = QFrame()
        hdr.setObjectName("card")
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 12, 14, 12)
        title_lbl = QLabel("🌐 CÔNG CỤ PYTHON QUẢN LÝ & ĐĂNG NHẬP ĐA TÀI KHOẢN GOOGLE FLOW")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #38bdf8;")
        hdr_lay.addWidget(title_lbl)

        desc_lbl = QLabel(
            "• Mỗi tài khoản Google Flow có 1 Profile Chrome ĐỘC LẬP riêng biệt (lưu tại data/google_flow_grok/native_profiles/<tên_profile>).\n"
            "• Extension giải Captcha (LeVietTung_autoveo) chạy ở 1 Profile Chrome RIÊNG ('captcha_bridge_solver'), KHÔNG cần login tài khoản Google nào, chỉ treo để giải reCAPTCHA!\n"
            "• Bấm '➕ Tạo Profile & Mở Chrome Đăng Nhập' -> Đăng nhập Google Flow 1 lần -> Đóng cửa sổ Chrome đó để lưu Cookie vĩnh viễn."
        )
        desc_lbl.setStyleSheet("font-size: 11.5px; color: #cbd5e1; line-height: 1.4;")
        hdr_lay.addWidget(desc_lbl)

        act_row = QHBoxLayout()
        self.prof_inp = QLineEdit()
        self.prof_inp.setPlaceholderText("Nhập tên Profile Chrome mới (VD: flow_acc_2, leviettung05)...")
        self.prof_inp.setText(initial_profile or self._suggest_next_profile())
        act_row.addWidget(self.prof_inp, stretch=1)

        btn_add_open = QPushButton("➕ Tạo Profile & Mở Chrome Đăng Nhập")
        btn_add_open.setStyleSheet("background-color: #16a34a; color: white; padding: 8px 14px;")
        btn_add_open.clicked.connect(self.on_click_login_from_input)
        act_row.addWidget(btn_add_open)

        btn_bulk_check = QPushButton("🔄 Tự Lấy Cookie Mới (Tất Cả)")
        btn_bulk_check.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 14px;")
        btn_bulk_check.clicked.connect(self.do_bulk_refresh)
        act_row.addWidget(btn_bulk_check)

        btn_ext_solver = QPushButton("🧩 Mở Chrome Riêng Treo Extension Captcha (Không Login)")
        btn_ext_solver.setStyleSheet("background-color: #d97706; color: white; padding: 8px 12px;")
        btn_ext_solver.clicked.connect(self.open_captcha_solver_chrome)
        act_row.addWidget(btn_ext_solver)

        hdr_lay.addLayout(act_row)

        self.status_lbl = QLabel("✅ Sẵn sàng. Nhập tên Profile rồi bấm '➕ Tạo Profile & Mở Chrome Đăng Nhập'.")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet(
            "background-color: #090d16; border: 1px solid #334155; border-radius: 6px; padding: 8px 10px; color: #a5f3fc; font-weight: bold; font-size: 12px;"
        )
        hdr_lay.addWidget(self.status_lbl)
        main_lay.addWidget(hdr)

        list_card = QFrame()
        list_card.setObjectName("card")
        list_lay = QVBoxLayout(list_card)
        list_lay.setContentsMargins(12, 12, 12, 12)
        lbl_list_title = QLabel("📋 DANH SÁCH TÀI KHOẢN GOOGLE FLOW ĐANG CÓ")
        lbl_list_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #fbbf24;")
        list_lay.addWidget(lbl_list_title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_content = QWidget()
        self.scroll_lay = QVBoxLayout(self.scroll_content)
        self.scroll_lay.setSpacing(6)
        self.scroll_lay.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.scroll_content)
        list_lay.addWidget(self.scroll, stretch=1)
        main_lay.addWidget(list_card, stretch=1)

        self.draw_accounts_list()

        if auto_start_login and initial_profile:
            QTimer.singleShot(250, lambda: self.start_google_login(initial_profile))

    def _clear_topmost(self):
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            self.show()

    def _suggest_next_profile(self) -> str:
        accs = _load_accounts()
        existing = {_profile_for_acc(a).lower() for a in accs if _is_google_account(a)}
        idx = 2
        while f"flow_acc_{idx}" in existing:
            idx += 1
        return f"flow_acc_{idx}"

    def set_status(self, text: str, color: str = "#a5f3fc"):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"background-color: #090d16; border: 1px solid #334155; border-radius: 6px; padding: 8px 10px; color: {color}; font-weight: bold; font-size: 12px;"
        )

    def on_click_login_from_input(self):
        raw = self.prof_inp.text().strip() or self._suggest_next_profile()
        clean_prof = re.sub(r"[^a-zA-Z0-9._@-]+", "_", raw)
        self.prof_inp.setText(clean_prof)
        self.start_google_login(clean_prof)

    def open_captcha_solver_chrome(self):
        self._clear_topmost()
        solver_dir = (AUTH_ROOT / "native_profiles" / "captcha_bridge_solver").resolve()
        solver_dir.mkdir(parents=True, exist_ok=True)
        gfa._ensure_chrome_profile_display_name(solver_dir, "🧩 Captcha Bridge Solver (Không Login)")
        exe = gfa.find_system_chrome()
        if not exe:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy Google Chrome trên máy tính!")
            return
        ext_dir = (SKILL_DIR / "Extension Recapcha" / "LeVietTung_autoveo").resolve()
        cmd = [
            str(exe),
            f"--user-data-dir={solver_dir}",
            "--profile-directory=Default",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
        ]
        if ext_dir.is_dir():
            cmd.extend([
                f"--disable-extensions-except={ext_dir}",
                f"--load-extension={ext_dir}",
            ])
        cmd.append("https://flow.google.com/about")
        subprocess.Popen(cmd, cwd=str(SKILL_DIR))
        self.set_status(
            "🧩 Đã mở Profile Chrome RIÊNG BIỆT 'captcha_bridge_solver' gắn sẵn Extension LeVietTung_autoveo! "
            "Không cần đăng nhập tài khoản nào trong cửa sổ này — chỉ để treo giải Captcha.",
            "#fbbf24",
        )

    def open_chrome_normal(self, prof_name: str):
        self._clear_topmost()
        gfa.save_browser_settings(AUTH_ROOT, prof_name, {"channel": "chrome", "login_mode": "system_chrome"})
        pdir, _ = gfa.profile_paths(AUTH_ROOT, prof_name)
        pdir.mkdir(parents=True, exist_ok=True)
        exe = gfa.find_system_chrome()
        if not exe:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy Google Chrome trên máy tính!")
            return
        cmd = gfa.native_login_command(str(exe), pdir)
        subprocess.Popen(cmd, cwd=str(SKILL_DIR))
        self.set_status(
            f"🌐 Đã mở cửa sổ Chrome độc lập cho Profile '{prof_name}'! "
            "Sau khi đăng nhập/kiểm tra xong, hãy đóng cửa sổ Chrome đó để lưu Cookie.",
            "#4ade80",
        )

    def start_google_login(self, prof_name: str, existing_acc_name: str = ""):
        self._clear_topmost()
        prof_clean = re.sub(r"[^a-zA-Z0-9._@-]+", "_", prof_name.strip()) or "default_flow"
        gfa.save_browser_settings(AUTH_ROOT, prof_clean, {"channel": "chrome", "login_mode": "system_chrome"})
        pdir, _ = gfa.profile_paths(AUTH_ROOT, prof_clean)
        pdir.mkdir(parents=True, exist_ok=True)

        # Đảm bảo tài khoản xuất hiện ngay trong danh sách
        accs = _load_accounts()
        if not any(_is_google_account(a) and _profile_for_acc(a).lower() == prof_clean.lower() for a in accs):
            accs.append({
                "name": f"Google_{prof_clean}",
                "proxy_url": DEFAULT_PROJECT_ID,
                "api_key": "",
                "active": True,
                "profile_name": prof_clean,
                "google_email": prof_clean,
                "auth_state": "login_required",
                "credits": -1,
            })
            _save_accounts(accs)
            self.draw_accounts_list()

        self.set_status(
            f"🔍 Đang mở Chrome cho Profile '{prof_clean}'... Hãy đăng nhập Google Flow rồi ĐÓNG cửa sổ Chrome đó để lưu Cookie!",
            "#a78bfa",
        )
        self.login_worker = FastLoginWorker(prof_clean)
        self.login_worker.status_sig.connect(lambda t, c: self.set_status(f"[{prof_clean}] {t}", c or "#a78bfa"))

        def on_success(email: str, token: str, proj_id: str):
            eff_proj = proj_id or DEFAULT_PROJECT_ID
            accs_now = _load_accounts()
            acc_name = f"Google_{email}"
            matched = False
            for a in accs_now:
                if a.get("name") in (existing_acc_name, acc_name) or _profile_for_acc(a).lower() == prof_clean.lower():
                    a["name"] = acc_name
                    a["google_email"] = email
                    a["api_key"] = token
                    a["auth_revision"] = time.time_ns()
                    a["auth_state"] = "ready"
                    a["proxy_url"] = eff_proj
                    a["profile_name"] = prof_clean
                    a["active"] = True
                    matched = True
                    break
            if not matched:
                accs_now.append({
                    "name": acc_name,
                    "proxy_url": eff_proj,
                    "api_key": token,
                    "active": True,
                    "profile_name": prof_clean,
                    "google_email": email,
                    "auth_state": "ready",
                    "auth_revision": time.time_ns(),
                    "credits": -1,
                })
            _save_accounts(accs_now)
            _upsert_registry(email, prof_clean, eff_proj)
            self.draw_accounts_list()
            self.prof_inp.setText(self._suggest_next_profile())
            self.set_status(f"✅ Đăng nhập & lưu Cookie thành công: {email} (Profile: {prof_clean})!", "#4ade80")

        def on_error(err_msg: str):
            self.draw_accounts_list()
            self.set_status(f"⚠️ ({prof_clean}): {err_msg}", "#fbbf24")

        self.login_worker.success_sig.connect(on_success)
        self.login_worker.error_sig.connect(on_error)
        self.login_worker.start()

    def do_bulk_refresh(self):
        accs = [a for a in _load_accounts() if _is_google_account(a)]
        if not accs:
            QMessageBox.warning(self, "Thông báo", "Chưa có tài khoản Google Flow nào!")
            return
        profs = [_profile_for_acc(a) for a in accs]
        self.set_status("🔄 Đang kiểm tra & tự động lấy Cookie mới cho tất cả Profile...", "#38bdf8")
        self.refresh_worker = FastRefreshWorker(profs)
        self.refresh_worker.status_sig.connect(lambda t, c: self.set_status(t, c))

        def on_done(ok_cnt: int, exp_cnt: int):
            self.draw_accounts_list()
            if exp_cnt == 0:
                self.set_status(f"✅ Tất cả {ok_cnt} tài khoản Google Flow đều sẵn sàng!", "#4ade80")
            else:
                self.set_status(f"⚠️ {ok_cnt} tài khoản OK, {exp_cnt} tài khoản cần bấm '🔑 Đăng Nhập & Bắt Cookie'.", "#fbbf24")

        self.refresh_worker.done_sig.connect(on_done)
        self.refresh_worker.start()

    def do_single_refresh(self, prof: str):
        self.refresh_worker = FastRefreshWorker([prof])
        self.refresh_worker.status_sig.connect(lambda t, c: self.set_status(t, c))
        self.refresh_worker.done_sig.connect(
            lambda ok_c, _: (
                self.draw_accounts_list(),
                self.set_status(
                    f"✅ Đã làm mới Cookie cho Profile '{prof}'!" if ok_c > 0 else f"⚠️ Profile '{prof}' cần bấm '🔑 Đăng Nhập' 1 lần.",
                    "#4ade80" if ok_c > 0 else "#fbbf24",
                ),
            )
        )
        self.refresh_worker.start()

    def draw_accounts_list(self):
        accs = _load_accounts()
        while self.scroll_lay.count():
            item = self.scroll_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        g_accs = [a for a in accs if _is_google_account(a)]
        if not g_accs:
            lbl = QLabel("Chưa có tài khoản Google Flow nào. Hãy bấm nút '➕ Tạo Profile & Mở Chrome Đăng Nhập' ở trên.")
            lbl.setStyleSheet("color: #94a3b8; font-style: italic; padding: 16px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_lay.addWidget(lbl)
            return

        for acc in g_accs:
            row = QFrame()
            row.setStyleSheet("background-color: #090d16; border: 1px solid #334155; border-radius: 8px; padding: 6px;")
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(10, 6, 10, 6)

            prof = _profile_for_acc(acc)
            tok = str(acc.get("api_key") or "")
            has_tok = len(tok) > 20
            _, cfile = gfa.profile_paths(AUTH_ROOT, prof)
            has_cookie = cfile.is_file()
            state_badge = "✅ Đã có Token & Cookie" if has_tok else ("🍪 Đã có Cookie" if has_cookie else "⚠️ Cần Login 1 lần")
            badge_col = "#4ade80" if (has_tok or has_cookie) else "#fbbf24"
            a_name = str(acc.get("name") or f"Google_{prof}")

            info_lbl = QLabel(
                f"<b style='color:#f8fafc; font-size:13px;'>🌐 {a_name}</b> "
                f"<span style='color:{badge_col}; font-weight:bold;'>[{state_badge}]</span><br>"
                f"<span style='color:#94a3b8; font-size:11px;'>Profile Chrome: <b style='color:#fde68a;'>{prof}</b> | Project: {acc.get('proxy_url') or DEFAULT_PROJECT_ID}</span>"
            )
            r_lay.addWidget(info_lbl, stretch=1)

            btn_open = QPushButton("🌐 Mở Chrome")
            btn_open.setStyleSheet("background-color: #059669; color: white; padding: 5px 10px;")
            btn_open.clicked.connect(lambda _, p=prof: self.open_chrome_normal(p))
            r_lay.addWidget(btn_open)

            btn_ref = QPushButton("🔄 Lấy Cookie")
            btn_ref.setStyleSheet("background-color: #0284c7; color: white; padding: 5px 10px;")
            btn_ref.clicked.connect(lambda _, p=prof: self.do_single_refresh(p))
            r_lay.addWidget(btn_ref)

            btn_login = QPushButton("🔑 Login & Bắt Cookie")
            btn_login.setStyleSheet("background-color: #7c3aed; color: white; padding: 5px 10px;")
            btn_login.clicked.connect(lambda _, p=prof, n=a_name: self.start_google_login(p, n))
            r_lay.addWidget(btn_login)

            is_act = bool(acc.get("active", True))
            cb = QCheckBox("Bật" if is_act else "Tắt")
            cb.setChecked(is_act)
            cb.setStyleSheet("color: #cbd5e1; font-weight: bold;")

            def on_toggle(state, target_name=a_name):
                all_a = _load_accounts()
                for a2 in all_a:
                    if a2.get("name") == target_name:
                        a2["active"] = bool(state)
                        break
                _save_accounts(all_a)
                self.draw_accounts_list()

            cb.stateChanged.connect(on_toggle)
            r_lay.addWidget(cb)

            btn_del = QPushButton("🗑️")
            btn_del.setStyleSheet("background-color: #dc2626; color: white; padding: 5px 8px;")

            def on_del(_, target_name=a_name):
                if QMessageBox.question(self, "Xác nhận", f"Xóa tài khoản '{target_name}'?") == QMessageBox.StandardButton.Yes:
                    all_a = [x for x in _load_accounts() if x.get("name") != target_name]
                    _save_accounts(all_a)
                    self.draw_accounts_list()

            btn_del.clicked.connect(on_del)
            r_lay.addWidget(btn_del)

            self.scroll_lay.addWidget(row)

        self.scroll_lay.addStretch(1)


def main():
    import argparse
    import ctypes
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="", help="Profile name to prefill or auto-login")
    parser.add_argument("--auto-login", action="store_true", help="Immediately open Chrome login for --profile")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    win = GoogleFlowAccountWindow(initial_profile=args.profile, auto_start_login=args.auto_login)
    win.show()
    win.raise_()
    win.activateWindow()
    if sys.platform == "win32":
        try:
            hwnd = int(win.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
