# -*- coding: utf-8 -*-
"""
Skill Video Veo — Local Web Server (Nhân Microsoft Edge App Mode)
=================================================================
Cung cấp giao diện Basic Web Local (http://127.0.0.1:8456) với 3 phân mục:
1. Dashboard & Dự Án (Theo dõi tiến độ đa luồng, nhập hàng loạt sản phẩm, xem kịch bản & Video Final)
2. Role Skill (Quản lý & chỉnh sửa các file .MD định nghĩa quy tắc kịch bản cho AI Agent)
3. Tài Khoản (Đăng nhập Google Flow / Veo 3, Grok / Codex CLIProxy, kết nối Extension Captcha Bridge)
"""

import argparse
import ctypes
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_DIR = Path(__file__).resolve().parent
PIPELINE_SCRIPTS_DIR = SKILL_DIR / "flow_final_pipeline" / "scripts"
for _p in (SKILL_DIR, PIPELINE_SCRIPTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import importlib
import google_flow_auth as gfa
import veo_skill_cli as core
import grok_video_tool as gvt
import sync_web_ui_state as _sws
import template_manager as _tm
import product_crawler_bridge as _pcb
import character_library_manager as _clm
import engine_settings_manager as _esm

FINAL_VIDEOS_DIR = _sws.FINAL_VIDEOS_DIR
_SWS_MTIME = 0.0
_TM_MTIME = 0.0
_PCB_MTIME = 0.0
_FWE_MTIME = 0.0
_FWE_MOD = None


def _get_fwe():
    global _FWE_MTIME, _FWE_MOD
    import flow_workflow_engine as _fwe
    try:
        mf = (PIPELINE_SCRIPTS_DIR / "flow_workflow_engine.py").stat().st_mtime
        if _FWE_MOD is None:
            _FWE_MOD = _fwe
            _FWE_MTIME = mf
        elif mf != _FWE_MTIME:
            old_status = dict(getattr(_fwe, "_WORKFLOW_RUN_STATUS", {}))
            old_locks = dict(getattr(_fwe, "_PROFILE_LOCKS", {}))
            _FWE_MOD = importlib.reload(_fwe)
            _FWE_MOD._WORKFLOW_RUN_STATUS.update(old_status)
            _FWE_MOD._PROFILE_LOCKS.update(old_locks)
            _FWE_MTIME = mf
    except Exception:
        _FWE_MOD = _fwe
    return _FWE_MOD


def _ensure_latest_sws():
    global _SWS_MTIME, _TM_MTIME, _PCB_MTIME
    try:
        m = (PIPELINE_SCRIPTS_DIR / "sync_web_ui_state.py").stat().st_mtime
        if m != _SWS_MTIME:
            importlib.reload(_sws)
            _SWS_MTIME = m
    except Exception:
        pass
    try:
        mt = (PIPELINE_SCRIPTS_DIR / "template_manager.py").stat().st_mtime
        if mt != _TM_MTIME:
            importlib.reload(_tm)
            _TM_MTIME = mt
    except Exception:
        pass
    try:
        mp = (PIPELINE_SCRIPTS_DIR / "product_crawler_bridge.py").stat().st_mtime
        if mp != _PCB_MTIME:
            importlib.reload(_pcb)
            _PCB_MTIME = mp
    except Exception:
        pass
    return _sws


_SYNC_BG_RUNNING = False


def sync_web_ui(force: bool = True):
    return _ensure_latest_sws().sync_web_ui(force=force)


def trigger_async_sync_web_ui():
    """Chạy sync_web_ui(force=False) trong background thread để không bao giờ làm chậm /api/status hay /api/project."""
    global _SYNC_BG_RUNNING
    if _SYNC_BG_RUNNING:
        return

    def _worker():
        global _SYNC_BG_RUNNING
        _SYNC_BG_RUNNING = True
        try:
            _ensure_latest_sws().sync_web_ui(force=False)
        except Exception:
            pass
        finally:
            _SYNC_BG_RUNNING = False

    threading.Thread(target=_worker, daemon=True).start()


def delete_final_video(pid: str, vkey: str = "", final_video_path: str = ""):
    return _ensure_latest_sws().delete_final_video(pid=pid, vkey=vkey, final_video_path=final_video_path)


def clean_product_rendered_cache(pid: str, also_delete_finals: bool = False):
    return _ensure_latest_sws().clean_product_rendered_cache(pid=pid, also_delete_finals=also_delete_finals)

PORT = 8456
STATIC_DIR = SKILL_DIR / "static"

_RUNNER = core.MultiThreadSkillRunner()
_LOGIN_STATUS = {"state": "idle", "message": "Sẵn sàng đăng nhập tài khoản.", "auth_url": ""}
_ACTIVE_GOOGLE_WORKERS = {}
_ACTIVE_CLIPROXY_WORKERS = {}


def _allow_foreground_window():
    if sys.platform == "win32":
        try:
            # Gửi xung phím Alt ảo (VK_MENU = 0x12) để mở khóa quyền đưa cửa sổ mới lên Foreground trên Windows 10/11
            ctypes.windll.user32.keybd_event(0x12, 0, 1, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 3, 0)
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass


def _open_in_windows_explorer(target_path: Path):
    """Mở thư mục hoặc chọn file trực tiếp trong Windows Explorer trên màn hình chính (WinSta0\\Default) và đưa cửa sổ lên phía trước."""
    _allow_foreground_window()
    resolved = target_path.resolve()
    norm = os.path.normpath(str(resolved))
    if sys.platform == "win32":
        gfa.cleanup_hidden_desktop_windows()
        before_hwnds = gfa.list_default_desktop_explorer_hwnds()
        if resolved.is_file():
            gfa.spawn_process_on_user_desktop(["explorer.exe", f"/select,{norm}"])
        else:
            gfa.spawn_process_on_user_desktop(["explorer.exe", "/n,", norm])

        def _focus_exp(p_val: Path, prev_h: set[int]):
            for delay in (0.3, 0.7, 1.2):
                time.sleep(delay)
                gfa.bring_explorer_window_to_front(p_val, prev_h)

        threading.Thread(target=_focus_exp, args=(resolved, before_hwnds), daemon=True).start()
    return norm


def _launch_chrome_profile_window(prof_name: str, target_url: str = "https://flow.google.com/") -> str:
    """Mở ngay cửa sổ Chrome độc lập cho profile Google Flow lên phía trước màn hình (WinSta0\\Default, không gắn Extension Captcha)."""
    _allow_foreground_window()
    prof_clean = re.sub(r"[^a-zA-Z0-9._@-]+", "_", (prof_name or "default_flow").strip()) or "default_flow"
    gfa.save_browser_settings(gvt.GROK_AUTH_ROOT, prof_clean, {"channel": "chrome", "login_mode": "system_chrome"})
    pdir, _ = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof_clean)
    pdir.mkdir(parents=True, exist_ok=True)
    # Nếu có tiến trình Chrome ẩn/headless đang giữ lockfile mà không có cửa sổ hiển thị trên màn hình chính -> đóng ngay
    vis_pid = gfa.has_visible_chrome_profile_window(pdir)
    if vis_pid > 0:
        gfa._bring_chrome_window_to_front(vis_pid, profile_dir=pdir)
        return str(pdir)
    if gfa._is_chrome_profile_open(pdir):
        gfa.close_chrome_profile_processes(pdir, timeout_sec=4.0)
    exe = gfa.find_system_chrome()
    cmd = gfa.native_login_command(exe, pdir)
    if target_url and cmd and cmd[-1].startswith("http"):
        cmd[-1] = target_url
    clean_env = os.environ.copy()
    for _pk in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        clean_env.pop(_pk, None)
    proc = gfa.spawn_process_on_user_desktop(cmd, env=clean_env)

    def _focus_later(pid_val: int, pdir_val: Path):
        for delay in (0.45, 0.85, 1.4):
            time.sleep(delay)
            gfa._bring_chrome_window_to_front(pid_val, profile_dir=pdir_val)

    threading.Thread(target=_focus_later, args=(getattr(proc, "pid", 0), pdir), daemon=True).start()
    return str(pdir)


def _launch_captcha_extension_chrome_window(dry_run: bool = False) -> dict:
    """Mở 1 Profile Chrome RIÊNG BIỆT trên màn hình chính (WinSta0\\Default) chỉ để bật Extension LeVietTung_autoveo treo giải Captcha (KHÔNG đăng nhập tài khoản Google nào)."""
    _allow_foreground_window()
    solver_prof_dir = (gvt.GROK_AUTH_ROOT / "native_profiles" / "captcha_bridge_solver").resolve()
    solver_prof_dir.mkdir(parents=True, exist_ok=True)
    gfa._ensure_chrome_profile_display_name(solver_prof_dir, "🧩 Captcha Bridge Solver (Không Login)")
    exe = gfa.find_system_chrome()
    ext_dir = (SKILL_DIR / "Extension Recapcha" / "LeVietTung_autoveo").resolve()
    cmd = [
        str(exe),
        f"--user-data-dir={solver_prof_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        "--window-size=1280,860",
        "--window-position=110,50",
    ]
    if ext_dir.is_dir():
        cmd.extend([
            f"--disable-extensions-except={ext_dir}",
            f"--load-extension={ext_dir}",
        ])
    # Mở trang giới thiệu công khai /about của Flow (có sẵn reCAPTCHA Enterprise, không cần login tài khoản Google)
    cmd.append("https://flow.google.com/about")
    if not dry_run:
        vis_pid = gfa.has_visible_chrome_profile_window(solver_prof_dir)
        if vis_pid > 0:
            gfa._bring_chrome_window_to_front(vis_pid, profile_dir=solver_prof_dir)
        else:
            if gfa._is_chrome_profile_open(solver_prof_dir):
                gfa.close_chrome_profile_processes(solver_prof_dir, timeout_sec=4.0)
            clean_env = os.environ.copy()
            for _pk in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
                clean_env.pop(_pk, None)
            proc = gfa.spawn_process_on_user_desktop(cmd, env=clean_env)
            threading.Thread(
                target=lambda p=getattr(proc, "pid", 0): (
                    time.sleep(0.7),
                    gfa._bring_chrome_window_to_front(p, profile_dir=solver_prof_dir),
                ),
                daemon=True,
            ).start()
    return {
        "ok": True,
        "profile_name": "captcha_bridge_solver",
        "profile_dir": str(solver_prof_dir),
        "extension_dir": str(ext_dir),
        "chrome_exe": str(exe),
        "command": cmd,
        "message": (
            "🧩 Đã mở Profile Chrome RIÊNG BIỆT 'captcha_bridge_solver' gắn sẵn Extension LeVietTung_autoveo! "
            "Profile này KHÔNG đăng nhập tài khoản Google nào — chỉ để treo giải reCAPTCHA cho toàn bộ các tài khoản Flow."
        ),
    }


_GOOGLE_REFRESH_LOCK = threading.Lock()
_PERIODIC_REFRESHER_STARTED = False


def _sync_cookie_file_to_skill_dirs(prof_name: str):
    """Đồng bộ file cookies/<prof_name>.json giữa GROK_AUTH_ROOT và SKILL_DIR/cookies."""
    src_cookie = gvt.GROK_AUTH_ROOT / "cookies" / f"{prof_name}.json"
    if not src_cookie.is_file():
        return
    try:
        raw = src_cookie.read_text(encoding="utf-8")
        for c_dir in (SKILL_DIR / "data" / "google_flow_grok" / "cookies", SKILL_DIR / "cookies"):
            c_dir.mkdir(parents=True, exist_ok=True)
            dst = c_dir / f"{prof_name}.json"
            if dst.resolve() != src_cookie.resolve():
                dst.write_text(raw, encoding="utf-8")
    except Exception:
        pass


def _refresh_and_commit_google_account(
    prof_name: str,
    force_refresh: bool = False,
    check_credits: bool = False,
) -> dict:
    """Kiểm tra token/cookie hiện tại của Profile Chrome; nếu hết hạn hoặc force_refresh=True thì tự động mở ngầm Profile Chrome để lấy Cookie/Token mới (chuẩn grok_video_tool.py)."""
    prof_clean = re.sub(r"[^a-zA-Z0-9._@-]+", "_", (prof_name or "").strip())
    if not prof_clean:
        return {"ok": False, "error": "Thiếu tên Profile Chrome"}

    pdir, cfile = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof_clean)
    if _ACTIVE_GOOGLE_WORKERS.get(prof_clean) or gfa._is_chrome_profile_open(pdir):
        if force_refresh:
            # Khi người dùng chủ động bấm "🔄 Tự Lấy Cookie Mới", tự động đóng cửa sổ Chrome của đúng Profile này
            # để lưu/trích xuất Cookie ngay mà không bắt người dùng tự tìm đóng cửa sổ!
            gfa.close_chrome_profile_processes(pdir, timeout_sec=4.5)
            t_wait = time.monotonic()
            while _ACTIVE_GOOGLE_WORKERS.get(prof_clean) and time.monotonic() - t_wait < 12.0:
                time.sleep(0.4)
        if _ACTIVE_GOOGLE_WORKERS.get(prof_clean) or gfa._is_chrome_profile_open(pdir):
            return {
                "ok": False,
                "profile_name": prof_clean,
                "refreshed": False,
                "error": f"Profile '{prof_clean}' đang mở cửa sổ Chrome trực tiếp — vui lòng hoàn tất đăng nhập trên cửa sổ đó.",
            }

    acc_mgr = gvt.AccountManager()
    target_acc = None
    for a in acc_mgr.accounts:
        if gvt._is_google_flow_account(a):
            resolved_p = gvt._google_profile_name_for_account(a, allow_unresolved=True)
            if resolved_p.lower() == prof_clean.lower() or a.name.lower() == f"google_{prof_clean}".lower():
                target_acc = a
                break

    cur_tok = str(target_acc.api_key or "").strip() if target_acc else ""
    cur_proj = (
        str(target_acc.proxy_url or "").strip()
        if (target_acc and target_acc.proxy_url and not str(target_acc.proxy_url).startswith("http"))
        else gvt.DEFAULT_PROJECT_ID
    )
    cur_email = (
        getattr(target_acc, "google_email", "")
        or (target_acc.name[len("Google_"):] if (target_acc and target_acc.name.startswith("Google_")) else "")
    )

    if not force_refresh and cur_tok:
        ok_ck, ck_detail = gvt.GoogleTokenRefreshWorker._check_token(cur_tok)
        if ok_ck or gfa.transient_auth_error(ck_detail):
            verified_email = ck_detail if (ok_ck and "@" in str(ck_detail or "")) else (cur_email or f"{prof_clean}@gmail.com")
            gfa.commit_login(gvt.GROK_AUTH_ROOT, prof_clean, verified_email, cur_tok, cur_proj)
            gvt._upsert_flow_profile_registry(verified_email, prof_clean, cur_proj, mark_login=True)
            _sync_cookie_file_to_skill_dirs(prof_clean)
            return {
                "ok": True,
                "profile_name": prof_clean,
                "email": verified_email,
                "project_id": cur_proj,
                "refreshed": False,
                "message": f"✅ Phiên Google Flow '{verified_email}' (Profile: {prof_clean}) đang còn hạn & sẵn sàng.",
            }

    # Nếu chưa có cur_tok (hoặc hết hạn) nhưng đã có file cookie JSON -> thử kiểm tra HTTP nhẹ, KHÔNG mở Chrome khi idle
    if not force_refresh:
        if not cur_tok and cfile.is_file():
            try:
                snap = gfa.read_json(cfile, default=None)
                c_list = snap.get("cookies", []) if isinstance(snap, dict) else (snap if isinstance(snap, list) else [])
                flow_tok_from_file = gfa._cookies_list_to_flow_token(c_list)
                if flow_tok_from_file:
                    ok_ck2, ck_detail2 = gvt.GoogleTokenRefreshWorker._check_token(flow_tok_from_file)
                    if ok_ck2:
                        verified_email = ck_detail2 if "@" in str(ck_detail2 or "") else (cur_email or f"{prof_clean}@gmail.com")
                        gfa.commit_login(gvt.GROK_AUTH_ROOT, prof_clean, verified_email, flow_tok_from_file, cur_proj)
                        gvt._upsert_flow_profile_registry(verified_email, prof_clean, cur_proj, mark_login=True)
                        _sync_cookie_file_to_skill_dirs(prof_clean)
                        return {
                            "ok": True,
                            "profile_name": prof_clean,
                            "email": verified_email,
                            "project_id": cur_proj,
                            "refreshed": False,
                            "message": f"✅ Phiên Google Flow '{verified_email}' (Profile: {prof_clean}) đã xác thực từ Cookie lưu sẵn.",
                        }
            except Exception:
                pass
        return {
            "ok": False,
            "profile_name": prof_clean,
            "email": cur_email or prof_clean,
            "refreshed": False,
            "error": "Phiên chưa sẵn sàng hoặc đã hết hạn (chỉ kiểm tra HTTP khi chạy ngầm, không tự bật Chrome).",
        }

    # Khi force_refresh=True -> Mở Chrome Profile để lấy lại Cookie/Token mới
    ok_ref, new_tok, new_proj, note = gvt._refresh_google_profile(prof_clean)
    if ok_ref and new_tok:
        verified_email = cur_email
        if isinstance(note, str) and note.startswith("session_verified:"):
            cand_em = note.split("session_verified:", 1)[1].strip()
            if "@" in cand_em:
                verified_email = cand_em
        if not verified_email or "@" not in verified_email:
            meta = gfa.load_session_metadata(gvt.GROK_AUTH_ROOT, prof_clean)
            verified_email = str(meta.get("email") or "").strip() or f"{prof_clean}@gmail.com"
        eff_proj = new_proj or cur_proj or gvt.DEFAULT_PROJECT_ID
        gfa.commit_login(gvt.GROK_AUTH_ROOT, prof_clean, verified_email, new_tok, eff_proj)
        gvt._upsert_flow_profile_registry(verified_email, prof_clean, eff_proj, mark_login=True)
        _sync_cookie_file_to_skill_dirs(prof_clean)

        credits_val = None
        tier_tag = ""
        if check_credits:
            try:
                credits_val, tier_tag = gvt.GoogleTokenRefreshWorker._fetch_google_credits(prof_clean, token=new_tok)
                if credits_val is not None or tier_tag:
                    am2 = gvt.AccountManager()
                    for a2 in am2.accounts:
                        if gvt._google_profile_name_for_account(a2, allow_unresolved=True) == prof_clean:
                            if credits_val is not None and credits_val >= 0:
                                a2.credits = credits_val
                            if tier_tag:
                                a2.tag = tier_tag
                    am2.save()
            except Exception:
                pass

        return {
            "ok": True,
            "profile_name": prof_clean,
            "email": verified_email,
            "project_id": eff_proj,
            "credits": credits_val,
            "tag": tier_tag,
            "refreshed": True,
            "message": f"🔄 Đã tự động lấy Cookie/Token mới từ Chrome Profile '{prof_clean}' ({verified_email})!",
        }

    # Chỉ chạy fallback mở Chrome Playwright khi người dùng chủ động yêu cầu (force_refresh=True)
    if not ok_ref and force_refresh:
        try:
            import importlib.util as _ilu_ecs
            _spec_ecs = _ilu_ecs.spec_from_file_location("extract_chrome_session", str(Path(__file__).parent / "extract_chrome_session.py"))
            _mod_ecs = _ilu_ecs.module_from_spec(_spec_ecs)
            _spec_ecs.loader.exec_module(_mod_ecs)
            found_p = _mod_ecs.find_profile_by_name(prof_clean)
            if found_p:
                pname_f, ppath_f, is_native_f = found_p
                print(f"[ExtractFallback] Thu extract tu Chrome profile: {pname_f} ({ppath_f})", flush=True)
                data_f = _mod_ecs.extract_via_playwright(ppath_f, pname_f, is_native_f)
                if data_f and data_f.get("cookies"):
                    _mod_ecs.save_session(data_f, prof_clean)
                    new_tok_f = gvt._load_flow_cookie_header(prof_clean) or ""
                    if new_tok_f:
                        em_f = data_f.get("email", "")
                        verified_email_f = em_f or cur_email or prof_clean
                        eff_proj_f = cur_proj or gvt.DEFAULT_PROJECT_ID
                        gfa.commit_login(gvt.GROK_AUTH_ROOT, prof_clean, verified_email_f, new_tok_f, eff_proj_f)
                        gvt._upsert_flow_profile_registry(verified_email_f, prof_clean, eff_proj_f, mark_login=True)
                        _sync_cookie_file_to_skill_dirs(prof_clean)
                        print(f"[ExtractFallback] Thanh cong! Email: {verified_email_f}", flush=True)
                        return {
                            "ok": True,
                            "profile_name": prof_clean,
                            "email": verified_email_f,
                            "project_id": eff_proj_f,
                            "credits": None,
                            "tag": "",
                            "refreshed": True,
                            "message": f"🔑 Session tu dong lay tu Chrome Profile '{prof_clean}' qua Playwright!",
                        }
        except Exception as _ecs_e:
            print(f"[ExtractFallback] Warning: {_ecs_e}", flush=True)

    return {
        "ok": False,
        "profile_name": prof_clean,
        "email": cur_email or prof_clean,
        "refreshed": False,
        "error": str(note or "Không thể tự động lấy Cookie — hãy bấm Mở Chrome Đăng Nhập 1 lần cho Profile này."),
    }


def auto_refresh_all_google_accounts(
    force_refresh: bool = False,
    check_credits: bool = False,
    reason: str = "startup",
) -> dict:
    """Tự động quét toàn bộ Profile Chrome đã lưu và làm mới Cookie/Token Google Flow khi khởi động tool hoặc định kỳ."""
    with _GOOGLE_REFRESH_LOCK:
        acc_mgr = gvt.AccountManager()
        ignored_profs = {"captcha_bridge_solver", "test_sbx"}
        # Loại bỏ các profile nội bộ giải Captcha hoặc test nếu vô tình có trong accounts.json
        cleaned_accounts = [
            a for a in acc_mgr.accounts
            if not (
                gvt._is_google_flow_account(a)
                and gvt._google_profile_name_for_account(a, allow_unresolved=True).lower() in ignored_profs
            )
        ]
        if len(cleaned_accounts) != len(acc_mgr.accounts):
            acc_mgr.accounts = cleaned_accounts
            acc_mgr.save()

        existing_profs = {
            gvt._google_profile_name_for_account(a, allow_unresolved=True)
            for a in acc_mgr.accounts
            if gvt._is_google_flow_account(a)
        }
        discovered = set(gfa.discover_profiles(gvt.GROK_AUTH_ROOT))
        added_new = 0
        for prof in sorted(discovered):
            if not prof or prof in existing_profs or prof.lower() in ignored_profs:
                continue
            pdir, cfile = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof)
            meta = gfa.load_session_metadata(gvt.GROK_AUTH_ROOT, prof)
            # Chỉ tự động khôi phục các Profile thực sự đã từng đăng nhập (có file cookie, metadata hoặc cookie Google trên đĩa)
            if cfile.is_file() or meta.get("email") or meta.get("token") or gfa._profile_has_google_cookies_on_disk(pdir):
                em = str(meta.get("email") or prof).strip()
                proj = str(meta.get("project_id") or gvt.DEFAULT_PROJECT_ID).strip()
                tok = str(meta.get("token") or "").strip()
                acc_name = em if em.startswith("Google_") else f"Google_{em}"
                acc_mgr.accounts.append(
                    gvt.Account(
                        name=acc_name,
                        proxy_url=proj,
                        api_key=tok,
                        profile_name=prof,
                        google_email=em if "@" in em else "",
                        auth_state="ready" if tok else " stale",
                        active=True,
                    )
                )
                existing_profs.add(prof)
                added_new += 1
        if added_new > 0:
            acc_mgr.save()

        acc_mgr = gvt.AccountManager()
        google_accs = [a for a in acc_mgr.accounts if gvt._is_google_flow_account(a)]
        results = []
        ok_count = 0
        refreshed_count = 0
        for a in google_accs:
            if not force_refresh and getattr(a, "auth_state", "") == "logging_in":
                continue
            prof = gvt._google_profile_name_for_account(a, allow_unresolved=True)
            if not prof:
                continue
            res = _refresh_and_commit_google_account(
                prof,
                force_refresh=force_refresh,
                check_credits=check_credits,
            )
            results.append(res)
            if res.get("ok"):
                ok_count += 1
                if res.get("refreshed"):
                    refreshed_count += 1

        if google_accs:
            if ok_count == len(google_accs):
                _LOGIN_STATUS["state"] = "done"
                _LOGIN_STATUS["message"] = (
                    f"✅ Đã tự động đồng bộ Cookie/Token ({reason}): {ok_count}/{len(google_accs)} tài khoản Google Flow sẵn sàng"
                    + (f" (vừa lấy mới {refreshed_count} phiên)." if refreshed_count else ".")
                )
            else:
                _LOGIN_STATUS["state"] = "done" if ok_count > 0 else "idle"
                _LOGIN_STATUS["message"] = (
                    f"ℹ️ Kiểm tra Cookie Google Flow ({reason}): {ok_count}/{len(google_accs)} sẵn sàng. "
                    "Tài khoản chưa đăng nhập chỉ cần bấm 'Mở Chrome Đăng Nhập' 1 lần duy nhất."
                )
        return {
            "ok": True,
            "total_google": len(google_accs),
            "ready_count": ok_count,
            "refreshed_count": refreshed_count,
            "results": results,
            "accounts": _RUNNER.get_accounts_info(),
            "message": _LOGIN_STATUS["message"],
        }


def _start_interactive_google_login(prof_name: str, initial_email: str = "", initial_proj_id: str = ""):
    """Mở cửa sổ Chrome thực độc lập trên màn hình chính (WinSta0\\Default) cho đúng Profile `prof_name`."""
    prof_clean = re.sub(r"[^a-zA-Z0-9._@-]+", "_", (prof_name or "default_flow").strip()) or "default_flow"
    _allow_foreground_window()

    gfa.save_browser_settings(gvt.GROK_AUTH_ROOT, prof_clean, {"channel": "chrome", "login_mode": "system_chrome"})
    pdir_check, _ = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof_clean)
    pdir_check.mkdir(parents=True, exist_ok=True)

    acc_mgr_init = gvt.AccountManager()
    if not any(
        (getattr(a, "profile_name", "") or "").strip().lower() == prof_clean.lower()
        for a in acc_mgr_init.accounts
        if gvt._is_google_flow_account(a)
    ):
        disp = (initial_email or prof_clean).strip()
        acc_name = disp if disp.startswith("Google_") else f"Google_{disp}"
        acc_mgr_init.accounts.append(
            gvt.Account(
                name=acc_name,
                proxy_url=initial_proj_id or gvt.DEFAULT_PROJECT_ID,
                api_key="",
                profile_name=prof_clean,
                google_email=disp if "@" in disp else "",
                auth_state="logging_in",
                active=True,
            )
        )
        acc_mgr_init.save()

    vis_pid = gfa.has_visible_chrome_profile_window(pdir_check)
    if vis_pid > 0:
        gfa._bring_chrome_window_to_front(vis_pid, profile_dir=pdir_check)
        _LOGIN_STATUS["state"] = "running"
        _LOGIN_STATUS["auth_url"] = ""
        _LOGIN_STATUS["profile_name"] = prof_clean
        _LOGIN_STATUS["message"] = (
            f"🌐 Cửa sổ Google Chrome riêng của Profile '{prof_clean}' đã được đưa lên trước màn hình! "
            "Hãy đăng nhập Google Flow trên cửa sổ Chrome đó rồi ĐÓNG cửa sổ (hoặc bấm '🔄 Tự Lấy Cookie Mới') để tự động lưu Cookie vĩnh viễn."
        )
        return

    # Nếu lockfile đang bị giữ bởi một tiến trình Chrome ẩn/headless mà không có cửa sổ hiển thị -> giải phóng ngay
    if gfa._is_chrome_profile_open(pdir_check):
        gfa.close_chrome_profile_processes(pdir_check, timeout_sec=4.0)

    if _ACTIVE_GOOGLE_WORKERS.get(prof_clean):
        try:
            _launch_chrome_profile_window(prof_clean)
        except Exception:
            pass
        _LOGIN_STATUS["state"] = "running"
        _LOGIN_STATUS["auth_url"] = ""
        _LOGIN_STATUS["profile_name"] = prof_clean
        _LOGIN_STATUS["message"] = (
            f"🌐 Đã mở cửa sổ Google Chrome riêng của Profile '{prof_clean}' lên trước màn hình! "
            "Hãy đăng nhập Google Flow trên cửa sổ Chrome đó rồi ĐÓNG cửa sổ (hoặc bấm '🔄 Tự Lấy Cookie Mới') để tự động lưu Cookie vĩnh viễn."
        )
        return

    def _bg_worker():
        _LOGIN_STATUS["state"] = "running"
        _LOGIN_STATUS["auth_url"] = ""
        _LOGIN_STATUS["profile_name"] = prof_clean
        _LOGIN_STATUS["message"] = (
            f"🌐 Đang mở Google Chrome độc lập cho Profile '{prof_clean}'... "
            "Hãy đăng nhập Google Flow 1 lần rồi ĐÓNG cửa sổ Chrome đó (hoặc bấm '🔄 Tự Lấy Cookie Mới') để tool tự động trích xuất & lưu Cookie!"
        )
        _ACTIVE_GOOGLE_WORKERS[prof_clean] = True
        lock = gvt._get_google_refresh_lock(prof_clean)
        acquired = False
        try:
            deadline_lk = time.monotonic() + 15
            while time.monotonic() < deadline_lk:
                if lock.acquire(timeout=0.5):
                    acquired = True
                    break
            res = gfa.acquire_session(
                gvt.GROK_AUTH_ROOT,
                prof_clean,
                gvt.GoogleTokenRefreshWorker._check_token,
                gvt._persist_flow_storage_state,
                interactive=True,
                expected="",
                cancelled=lambda: False,
                status=lambda msg: _LOGIN_STATUS.update({"message": f"[{prof_clean}] {msg}"}),
            )
            if res.ok and res.token:
                verified_email = (res.email or initial_email or f"{prof_clean}@gmail.com").strip()
                eff_proj = res.project or initial_proj_id or gvt.DEFAULT_PROJECT_ID
                gfa.commit_login(gvt.GROK_AUTH_ROOT, prof_clean, verified_email, res.token, eff_proj)
                gvt._upsert_flow_profile_registry(verified_email, prof_clean, eff_proj, mark_login=True)
                _sync_cookie_file_to_skill_dirs(prof_clean)
                _LOGIN_STATUS["state"] = "done"
                _LOGIN_STATUS["message"] = (
                    f"✅ Đã đăng nhập & lưu tự động tài khoản Google Flow: {verified_email} (Profile: {prof_clean}). "
                    "Từ giờ mỗi lần bật tool hoặc khi hết hạn sẽ tự động lấy Cookie mới!"
                )
            else:
                if "profile_busy" in str(res.error or ""):
                    try:
                        _launch_chrome_profile_window(prof_clean)
                    except Exception:
                        pass
                    _LOGIN_STATUS["state"] = "done"
                    _LOGIN_STATUS["message"] = (
                        f"🌐 Cửa sổ Chrome của Profile '{prof_clean}' đang mở — "
                        "hãy đăng nhập xong rồi đóng cửa sổ Chrome đó để lưu Cookie!"
                    )
                else:
                    _LOGIN_STATUS["state"] = "error"
                    _LOGIN_STATUS["message"] = f"ℹ️ Chưa hoàn tất đăng nhập Profile '{prof_clean}': {res.error}"
        except Exception as e:
            _LOGIN_STATUS["state"] = "error"
            _LOGIN_STATUS["message"] = f"❌ Lỗi khi đăng nhập Profile '{prof_clean}': {str(e)[:180]}"
        finally:
            if acquired:
                try:
                    lock.release()
                except Exception:
                    pass
            _ACTIVE_GOOGLE_WORKERS.pop(prof_clean, None)

    threading.Thread(target=_bg_worker, daemon=True).start()


def _start_periodic_google_cookie_refresher():
    """Khởi chạy luồng ngầm tự động lấy Cookie mới ngay khi mở tool và kiểm tra làm mới mỗi 15 phút."""
    global _PERIODIC_REFRESHER_STARTED
    if _PERIODIC_REFRESHER_STARTED:
        return
    _PERIODIC_REFRESHER_STARTED = True

    def _loop():
        time.sleep(1.5)
        try:
            auto_refresh_all_google_accounts(force_refresh=False, check_credits=False, reason="khởi động tool")
        except Exception:
            pass
        while True:
            time.sleep(900)  # Kiểm tra định kỳ mỗi 15 phút
            try:
                auto_refresh_all_google_accounts(force_refresh=False, check_credits=False, reason="tự động định kỳ")
            except Exception:
                pass

    threading.Thread(target=_loop, daemon=True).start()


def _is_port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            s.connect(("127.0.0.1", port))
            return True
    except Exception:
        return False


_TM_MOD_CACHE = None


def _get_token_manager_module():
    global _TM_MOD_CACHE
    if _TM_MOD_CACHE is not None:
        return _TM_MOD_CACHE
    if "token_manager" in sys.modules:
        _TM_MOD_CACHE = sys.modules["token_manager"]
        return _TM_MOD_CACHE
    import importlib.util as _ilu_tm
    _spec_tm = _ilu_tm.spec_from_file_location("token_manager", str(Path(__file__).parent / "token_manager.py"))
    _mod_tm = _ilu_tm.module_from_spec(_spec_tm)
    sys.modules["token_manager"] = _mod_tm
    _spec_tm.loader.exec_module(_mod_tm)
    _TM_MOD_CACHE = _mod_tm
    return _mod_tm


def ensure_background_services():
    """Đảm bảo CaptchaBridge (:4000), CLIProxy (:8317) và Tự động làm mới Cookie Google Flow luôn sẵn sàng."""
    _RUNNER.ensure_captcha_bridge()
    _start_periodic_google_cookie_refresher()
    # Đăng ký guard patch cho gvt mà không bật luồng mở Chrome headless=False định kỳ mỗi 20 phút khi tool đang rảnh
    try:
        _mod_tm = _get_token_manager_module()
        _mod_tm.patch_gvt()
    except Exception as _tm_e:
        print(f"[TokenMgr] Init warning: {_tm_e}", flush=True)
    if not _is_port_open(8317) and gvt.CLIPROXY_EXE.is_file():
        try:
            subprocess.Popen(
                [str(gvt.CLIPROXY_EXE), "-config", str(gvt.CLIPROXY_DIR / "config.yaml")],
                cwd=str(gvt.CLIPROXY_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception:
            pass


def launch_microsoft_edge_app(url: str):
    """Mở giao diện trên nhân Microsoft Edge ở chế độ App Mode (--app) trên màn hình chính (WinSta0\\Default)."""
    _allow_foreground_window()
    edge_candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    for exe in edge_candidates:
        if exe.is_file():
            gfa.spawn_process_on_user_desktop(
                [
                    str(exe),
                    f"--app={url}",
                    "--new-window",
                    "--window-size=1420,900",
                    "--disable-features=Translate",
                ],
            )
            return True
    import webbrowser
    webbrowser.open(url)
    return False


_FASHION_RUN_GUARD = threading.Lock()
_FASHION_RUNNING = set()
_ALLOWED_MEDIA_EXTS = frozenset({
    ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg",
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
})


def _resolve_allowed_media_path(fpath_str: str) -> tuple:
    """Resolve media path safely inside SKILL_DIR or configured output directories; returns (Path|None, is_forbidden)."""
    raw = str(fpath_str or "").strip()
    if not raw or "\x00" in raw:
        return None, False
    norm = os.path.normpath(raw)
    if norm in ("", "."):
        return None, False

    roots = [SKILL_DIR.resolve()]
    extra_candidates = []
    try:
        if FINAL_VIDEOS_DIR:
            extra_candidates.append(FINAL_VIDEOS_DIR)
    except Exception:
        pass
    try:
        cfg_dir = (_esm.load_engine_settings() or {}).get("final_videos_dir")
        if cfg_dir:
            extra_candidates.append(cfg_dir)
    except Exception:
        pass
    for ed in extra_candidates:
        try:
            rp = Path(str(ed)).resolve()
            if rp not in roots:
                roots.append(rp)
        except Exception:
            pass

    p_in = Path(norm)
    candidates = [p_in] if p_in.is_absolute() else [SKILL_DIR / p_in]
    saw_forbidden = False
    for cand in candidates:
        try:
            res = cand.resolve()
        except Exception:
            continue
        in_allowed_root = any(res == r or res.is_relative_to(r) for r in roots)
        if not in_allowed_root:
            saw_forbidden = True
            continue
        if res.suffix.lower() not in _ALLOWED_MEDIA_EXTS:
            saw_forbidden = True
            continue
        if res.is_file():
            return res, False
    return None, saw_forbidden


class SkillWebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, status: int = 200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            self._do_GET_inner()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 500)

    def _do_GET_inner(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            index_file = STATIC_DIR / "index.html"
            if not index_file.is_file():
                self._send_json({"error": "Missing static/index.html"}, 404)
                return
            raw = index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
            return

        if path.startswith("/static/"):
            rel_name = path[len("/static/"):].strip("/\\")
            target_file = (STATIC_DIR / rel_name).resolve()
            static_root = STATIC_DIR.resolve()
            if (target_file == static_root or target_file.is_relative_to(static_root)) and target_file.is_file():
                raw = target_file.read_bytes()
                ext = target_file.suffix.lower()
                ctype = (
                    "application/javascript; charset=utf-8" if ext == ".js"
                    else ("text/css; charset=utf-8" if ext == ".css" else "application/octet-stream")
                )
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(raw)
                return

        if path == "/api/status":
            trigger_async_sync_web_ui()
            roles = core.sync_role_skills_dirs()
            projects = core._load_projects_index()
            acc_info = _RUNNER.get_accounts_info()
            bridge = _RUNNER.ensure_captcha_bridge()
            bridge_port = getattr(gvt, "CAPTCHA_BRIDGE_PORT", 4000)
            running_4000 = _is_port_open(bridge_port)
            ext_connected = False
            if running_4000:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{bridge_port}/status", timeout=1.5) as r_st:
                        st_json = json.loads(r_st.read().decode("utf-8", errors="replace"))
                        ext_connected = bool(
                            st_json.get("extension_online")
                            or st_json.get("extension_liveness") == "connected"
                        )
                except Exception:
                    ext_connected = bool(bridge and hasattr(bridge, "extension_liveness") and bridge.extension_liveness() == "connected")
            secret_val = ""
            if bridge and hasattr(bridge, "get_secret"):
                secret_val = bridge.get_secret()
            prof_default = gvt._default_google_profile_name() or ""
            has_cookies = bool(prof_default and gvt._load_flow_cookie_header(prof_default))
            bridge_info = {
                "running": running_4000,
                "port": bridge_port,
                "secret": secret_val,
                "extension_connected": ext_connected,
                "has_cookies": has_cookies,
            }
            self._send_json({
                "ok": True,
                "final_videos_dir": str(FINAL_VIDEOS_DIR),
                "captcha_bridge": bridge_info,
                "cliproxy_running": _is_port_open(8317),
                "accounts": acc_info,
                "role_skills": roles,
                "projects": projects,
                "voices_and_characters": core.load_voices_and_characters(),
                "templates": _tm.list_video_templates(),
                "login_status": _LOGIN_STATUS,
                "engine_settings": _esm.load_engine_settings(),
                "running_pipelines": _esm.list_all_running_pipelines(),
            })
            return

        if path == "/api/settings":
            self._send_json({
                "ok": True,
                "settings": _esm.load_engine_settings(),
                "running_pipelines": _esm.list_all_running_pipelines(),
            })
            return

        if path == "/api/thumbnails/templates":
            es = _esm.load_engine_settings()
            self._send_json({
                "ok": True,
                "templates": es.get("thumbnail_presets", []),
                "categories": es.get("thumbnail_categories", []),
                "thumbnail_settings": es.get("thumbnail_settings", {}),
            })
            return

        if path == "/api/thumbnails/prompt":
            pid = (qs.get("pid") or qs.get("project_id") or [""])[0].strip()
            vkey = (qs.get("vkey") or ["v1"])[0].strip()
            preset_id = (qs.get("preset_id") or [""])[0].strip()
            custom_info = (qs.get("product_info") or [""])[0].strip()
            self._send_json({
                "ok": True,
                **_esm.build_thumbnail_prompt_for_variant(
                    pid=pid,
                    vkey=vkey,
                    preset_id=preset_id,
                    custom_product_info=custom_info,
                    subject_mode=(qs.get("subject_mode") or ["auto"])[0],
                    headline=(qs.get("headline") or [""])[0],
                ),
            })
            return

        if path == "/api/cooking/default":
            import cooking_storyboard_engine as cooking
            from cooking_recipe_ai import SUGGESTED_DISHES
            voices = cooking.list_cooking_voices()
            accounts = cooking.list_cooking_flow_accounts()
            default_acc = next((a["profile_name"] for a in accounts if a.get("has_cookies")), (accounts[0]["profile_name"] if accounts else ""))
            default_voice = next((v["key"] for v in voices if v.get("recommended_for_cooking")), (voices[0]["key"] if voices else ""))
            default_vid_prov = (_esm.load_engine_settings() or {}).get("video_provider", "google_flow")
            self._send_json({
                "ok": True,
                "recipe": cooking.DEFAULT_RECIPE,
                "demo_project_id": "pov_cooking_v2_20261110",
                "voices": voices,
                "accounts": accounts,
                "default_profile": default_acc,
                "default_voice_key": default_voice,
                "default_video_provider": default_vid_prov,
                "suggested_dishes": SUGGESTED_DISHES,
                "recent_projects": cooking.list_recent_cooking_projects(limit=25),
            })
            return

        if path == "/api/google_vids/status":
            try:
                import google_vids_client as _gvc
                probe = (qs.get("probe") or ["0"])[0].strip() in ("1", "true", "yes")
                prof = (qs.get("profile") or [""])[0].strip()
                accs = _gvc.list_available_vids_accounts()
                out_payload = {"ok": True, "accounts": accs}
                if probe:
                    out_payload["quota"] = _gvc.get_google_vids_client().get_quota_summary(profile_name=prof)
                self._send_json(out_payload)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, 500)
            return

        if path == "/api/cooking/status":
            try:
                import cooking_storyboard_engine as cooking
                project_id = (qs.get("project_id") or [""])[0]
                self._send_json({"ok": True, "project": cooking.get_status(project_id)})
            except (ValueError, FileNotFoundError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        if path == "/api/templates":
            _ensure_latest_sws()
            self._send_json({"ok": True, "templates": _tm.list_video_templates(), "template_root_dir": _tm.TEMPLATE_ROOT_DIR})
            return

        if path == "/api/templates/detail":
            _ensure_latest_sws()
            tname = (qs.get("name") or ["Nhà Xưởng"])[0]
            self._send_json(_tm.get_template_detail(tname))
            return

        if path == "/api/products-store":
            _ensure_latest_sws()
            self._send_json(_pcb.list_all_products_store())
            return

        if path == "/api/characters":
            self._send_json(_clm.get_character_library_state())
            return

        if path == "/api/voices":
            self._send_json({"ok": True, **core.load_voices_and_characters()})
            return

        if path == "/api/projects":
            trigger_async_sync_web_ui()
            self._send_json({"ok": True, "projects": core._load_projects_index()})
            return

        if path == "/api/matrix-overview":
            mode = (qs.get("mode") or ["videos"])[0].strip().lower()
            idx_list = core._load_projects_index()
            items = []
            total_final_vids = 0
            with_vids_cnt = 0
            with_cache_cnt = 0
            clean_new_cnt = 0
            for p in idx_list:
                dn = p.get("done_products") or 0
                has_c = bool(p.get("has_rendered_cache"))
                is_new = bool(p.get("is_clean_new"))
                total_final_vids += dn
                if dn > 0:
                    with_vids_cnt += 1
                elif has_c:
                    with_cache_cnt += 1
                else:
                    clean_new_cnt += 1

                if mode == "videos" and dn <= 0:
                    continue
                if mode == "active" and dn <= 0 and not has_c:
                    continue

                if dn <= 0 and mode == "all":
                    # Đối với sản phẩm chưa có video ở chế độ 'all', trả về bản tóm tắt siêu nhẹ để hiển thị tức thì
                    items.append({
                        "id": p["id"],
                        "name": p.get("name", p["id"]),
                        "products": [],
                        "has_rendered_cache": has_c,
                        "rendered_files_count": p.get("rendered_files_count", 0),
                        "rendered_size_mb": p.get("rendered_size_mb", 0),
                        "is_clean_new": is_new,
                    })
                    continue

                detail = core.load_project(p["id"])
                if detail:
                    slim_prods = []
                    for pr in (detail.get("products") or []):
                        slim_prods.append({
                            "id": pr.get("id", ""),
                            "vkey": pr.get("vkey", ""),
                            "char_v_code": pr.get("char_v_code", ""),
                            "pipeline_kind": pr.get("pipeline_kind", ""),
                            "product_name": pr.get("product_name", ""),
                            "final_video_path": pr.get("final_video_path", ""),
                            "thumbnail_path": pr.get("thumbnail_path", ""),
                            "product_image_path": pr.get("product_image_path", ""),
                            "primary_product_image_path": pr.get("primary_product_image_path", ""),
                        })
                    items.append({
                        "id": detail.get("id", p["id"]),
                        "pipeline_kind": detail.get("pipeline_kind", ""),
                        "name": detail.get("name", p.get("name", p["id"])),
                        "primary_product_image_path": detail.get("primary_product_image_path", ""),
                        "products": slim_prods,
                        "has_rendered_cache": has_c,
                        "rendered_files_count": p.get("rendered_files_count", 0),
                        "rendered_size_mb": p.get("rendered_size_mb", 0),
                        "is_clean_new": is_new,
                    })
            self._send_json({
                "ok": True,
                "mode": mode,
                "items": items,
                "counts": {
                    "total_projects": len(idx_list),
                    "with_videos": with_vids_cnt,
                    "with_cache": with_cache_cnt,
                    "clean_new": clean_new_cnt,
                    "total_final_videos": total_final_vids,
                },
            })
            return

        if path == "/api/project":
            trigger_async_sync_web_ui()
            pid = (qs.get("id") or [""])[0]
            proj = core.load_project(pid)
            if not proj:
                self._send_json({"ok": False, "error": "Không tìm thấy dự án"}, 404)
                return
            try:
                live_st = _esm.get_project_live_progress(pid)
                if live_st and (live_st.get("is_running") or not proj.get("live_status")):
                    proj["live_status"] = live_st
                    if live_st.get("is_running"):
                        proj["is_running"] = True
                        proj["progress_pct"] = live_st.get("progress_pct", proj.get("progress_pct", 0))
            except Exception:
                pass
            self._send_json({"ok": True, "project": proj})
            return

        if path == "/api/roles":
            self._send_json({"ok": True, "roles": core.sync_role_skills_dirs()})
            return

        if path == "/api/roles/read":
            fname = (qs.get("file") or [""])[0]
            try:
                content = core.read_role_skill(fname)
                self._send_json({"ok": True, "filename": fname, "content": content})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 404)
            return

        if path == "/api/accounts":
            self._send_json({
                "ok": True,
                "accounts": _RUNNER.get_accounts_info(),
                "login_status": _LOGIN_STATUS,
            })
            return

        if path == "/api/media":
            fpath_str = (qs.get("path") or [""])[0]
            fpath, is_forbidden = _resolve_allowed_media_path(fpath_str)
            if not fpath or not fpath.is_file():
                self.send_response(403 if is_forbidden else 404)
                self.send_header("Connection", "close")
                self.end_headers()
                return
            ext = fpath.suffix.lower()
            if ext == ".mp4":
                mime = "video/mp4"
            elif ext in (".jpg", ".jpeg"):
                mime = "image/jpeg"
            elif ext == ".png":
                mime = "image/png"
            elif ext == ".webp":
                mime = "image/webp"
            elif ext in (".mp3", ".wav"):
                try:
                    with open(fpath, "rb") as fh:
                        hdr4 = fh.read(4)
                    mime = "audio/wav" if hdr4 == b"RIFF" else "audio/mpeg"
                except Exception:
                    mime = "audio/mpeg"
            else:
                mime, _ = mimetypes.guess_type(str(fpath))
                mime = mime or "application/octet-stream"
            file_size = fpath.stat().st_size
            range_hdr = self.headers.get("Range")
            try:
                if range_hdr and range_hdr.startswith("bytes="):
                    parts = range_hdr.replace("bytes=", "").split("-")
                    start = int(parts[0]) if parts[0] else 0
                    if len(parts) > 1 and parts[1]:
                        end = int(parts[1])
                    else:
                        end = min(start + 4 * 1024 * 1024 - 1, file_size - 1)
                    end = min(end, file_size - 1)
                    if start >= file_size or start > end:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{file_size}")
                        self.send_header("Connection", "close")
                        self.end_headers()
                        return
                    chunk_len = end - start + 1
                    with open(fpath, "rb") as f:
                        f.seek(start)
                        data = f.read(chunk_len)
                    self.send_response(206)
                    self.send_header("Content-Type", mime)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(data)
                    return

                data = fpath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass
            return

        if path in ("/api/fashion_motion/projects", "/api/fashion_motion/project"):
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                req_pid = (qs.get("project_id") or [""])[0].strip()
                projs = _fmce.list_fashion_motion_projects()
                if not projs:
                    default_vid = str(SKILL_DIR / "flow_final_pipeline" / "fashion_motion_studio" / "ref_videos" / "FDown.vn_Tai_video_Facebook_1080p_6e19.mp4")
                    if os.path.exists(default_vid):
                        _fmce.create_or_update_fashion_motion_project(
                            project_id_slug="fashion_lookbook_chan_vay_6e19",
                            title="Lookbook Phối Đồ Đi Làm Tủ Gỗ 2K (Video 6e19 16.77s — 5 Bộ Đồ × 2 Cảnh 8s)",
                            ref_video_path=default_vid,
                            preferred_chunk_sec="8",
                            prompt_style="timeline_pro",
                        )
                        projs = _fmce.list_fashion_motion_projects()

                active_proj = None
                if req_pid:
                    active_proj = next((p for p in projs if p.get("project_id") == req_pid), None)
                if not active_proj:
                    # Ưu tiên hiển thị dự án đang chạy (running_flow) hoặc dự án vừa hoàn tất Video Final mới nhất
                    active_proj = next((p for p in projs if p.get("status") == "running_flow"), None)
                if not active_proj:
                    active_proj = next((p for p in projs if p.get("final_video_ready") and p.get("final_video_path")), None)
                if not active_proj:
                    active_proj = next((p for p in projs if p.get("project_id") == "fashion_lookbook_chan_vay_6e19"), None) or (projs[0] if projs else None)

                ref_vids_dir = SKILL_DIR / "flow_final_pipeline" / "fashion_motion_studio" / "ref_videos"
                ref_videos_lib = []
                if ref_vids_dir.is_dir():
                    for vf in sorted(ref_vids_dir.iterdir()):
                        if vf.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
                            ref_videos_lib.append({
                                "filename": vf.name,
                                "path": str(vf),
                                "size_mb": round(vf.stat().st_size / (1024 * 1024), 2),
                            })

                import fashion_video_template_catalog as _fvtc
                if os.path.exists(_fvtc.CATALOG_JSON_PATH):
                    try:
                        with open(_fvtc.CATALOG_JSON_PATH, "r", encoding="utf-8") as _cf:
                            tpl_cat = json.load(_cf)
                    except Exception:
                        tpl_cat = _fvtc.scan_and_sync_fashion_video_templates(force_rescan=False)
                else:
                    tpl_cat = _fvtc.scan_and_sync_fashion_video_templates(force_rescan=False)
                f_lib = _fmce.list_fashion_characters_and_outfits_library()

                self._send_json({
                    "ok": True,
                    "projects": projs,
                    "active_project": active_proj,
                    "current_project": active_proj,
                    "ref_videos_library": ref_videos_lib,
                    "default_outfits": f_lib.get("outfits") or _fmce.DEFAULT_FASHION_DEMO_OUTFITS,
                    "fashion_library": f_lib,
                    "video_templates_catalog": tpl_cat,
                    "standard_prompts": _fmce.get_standard_fashion_prompts(),
                    "characters": _clm.get_character_library_state().get("characters", []),
                    "flow_accounts": (__import__("cooking_storyboard_engine").list_cooking_flow_accounts() if os.path.exists(str(PIPELINE_SCRIPTS_DIR / "cooking_storyboard_engine.py")) else []),
                    "vids_accounts": (__import__("google_vids_client").list_available_vids_accounts() if os.path.exists(str(PIPELINE_SCRIPTS_DIR / "google_vids_client.py")) else []),
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/templates":
            try:
                import fashion_video_template_catalog as _fvtc
                import fashion_motion_control_engine as _fmce
                force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
                tpl_cat = _fvtc.scan_and_sync_fashion_video_templates(force_rescan=force)
                f_lib = _fmce.list_fashion_characters_and_outfits_library()
                self._send_json({
                    "ok": True,
                    "video_templates_catalog": tpl_cat,
                    "fashion_library": f_lib,
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/workflows/list":
            try:
                _fwe = _get_fwe()
                wfs = _fwe.list_saved_workflows()
                self._send_json({
                    "ok": True,
                    "workflows": wfs,
                    "characters": _clm.get_character_library_state().get("characters", []),
                    "flow_accounts": (__import__("cooking_storyboard_engine").list_cooking_flow_accounts() if os.path.exists(str(PIPELINE_SCRIPTS_DIR / "cooking_storyboard_engine.py")) else []),
                    "vids_accounts": (__import__("google_vids_client").list_available_vids_accounts() if os.path.exists(str(PIPELINE_SCRIPTS_DIR / "google_vids_client.py")) else []),
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/workflows/status":
            try:
                _fwe = _get_fwe()
                wf_id = (qs.get("wf_id") or [""])[0].strip()
                st = _fwe.get_workflow_run_status(wf_id)
                self._send_json({"ok": True, "status": st})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/pick_file":
            kind = (qs.get("kind") or ["image"])[0]
            filter_str = (
                "Video Files (*.mp4;*.mov;*.mkv;*.webm)|*.mp4;*.mov;*.mkv;*.webm|All Files (*.*)|*.*"
                if kind == "video"
                else "Image Files (*.png;*.jpg;*.jpeg;*.webp)|*.png;*.jpg;*.jpeg;*.webp|All Files (*.*)|*.*"
            )
            title_str = "Chọn Video Tham Chiếu (.mp4)" if kind == "video" else "Chọn Ảnh Nhân Vật 2K / Ảnh Bộ Đồ 2K"
            ps_cmd = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                f"$f.Title = '{title_str}'; "
                f"$f.Filter = '{filter_str}'; "
                "$owner = New-Object System.Windows.Forms.Form; $owner.TopMost = $true; "
                "if ($f.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.FileName }"
            )
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-STA", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    encoding="utf-8",
                    errors="replace",
                )
                chosen = (r.stdout or "").strip()
                self._send_json({"ok": bool(chosen), "path": chosen})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)})
            return

        if path == "/api/studio/overview":
            char_st = _clm.get_character_library_state() if _clm else {"characters": [], "voices_list": []}
            prods_st = _pcb.list_all_products_store() if _pcb else {"products": []}
            tpls = _tm.list_video_templates() if _tm else []
            self._send_json({
                "ok": True,
                "characters": char_st.get("characters", []),
                "voices": char_st.get("voices_list", []),
                "products": prods_st.get("products", []),
                "templates": tpls,
                "projects": core._load_projects_index(),
            })
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        try:
            self._do_POST_inner()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 500)

    def _do_POST_inner(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        if path == "/api/cooking/generate-script":
            import cooking_storyboard_engine as cooking
            from cooking_recipe_ai import generate_cooking_recipe_and_script
            try:
                dish = str(body.get("dish") or "").strip()
                if not dish:
                    self._send_json({"ok": False, "error": "Vui lòng nhập tên món ăn trước khi sinh kịch bản."}, 400)
                    return
                raw_voice = str(body.get("voice_id") or "").strip()
                raw_mode = str(body.get("audio_mode") or "").strip().lower()
                if raw_mode not in ("asmr", "voice"):
                    raw_mode = "voice" if (raw_voice and raw_voice.lower() not in ("none", "asmr", "off")) else "asmr"
                v_meta = cooking.resolve_cooking_voice(raw_voice) if raw_mode == "voice" else cooking.resolve_cooking_voice("")
                num_clips = max(1, min(6, int(body.get("num_clips") or 3)))
                gen_recipe = generate_cooking_recipe_and_script(
                    dish_name=dish,
                    num_clips=num_clips,
                    audio_mode=raw_mode,
                    voice_region=v_meta.get("region") or "north",
                    custom_notes=str(body.get("custom_notes") or "").strip(),
                    prefer_ai=body.get("prefer_ai", True) is not False,
                )
                ready = cooking.ensure_recipe_ready(
                    recipe=gen_recipe,
                    dish=dish,
                    voice_id=raw_voice if raw_mode == "voice" else "",
                    audio_mode=raw_mode,
                    num_clips=num_clips,
                    has_subtitles=bool(body.get("has_subtitles")),
                )
                self._send_json({"ok": True, "recipe": ready})
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        if path == "/api/cooking/prepare":
            import cooking_storyboard_engine as cooking
            try:
                raw_recipe = body.get("recipe")
                dish = str(body.get("dish") or (raw_recipe or {}).get("dish") or "").strip()
                if body.get("auto_script") or (not raw_recipe and dish) or body.get("voice_id") or body.get("audio_mode"):
                    raw_recipe = cooking.ensure_recipe_ready(
                        recipe=raw_recipe,
                        dish=dish,
                        voice_id=str(body.get("voice_id") or (raw_recipe or {}).get("voice_id") or "").strip(),
                        audio_mode=str(body.get("audio_mode") or (raw_recipe or {}).get("audio_mode") or "").strip(),
                        num_clips=int(body.get("num_clips") or len((raw_recipe or {}).get("clips") or []) or 3),
                        custom_notes=str(body.get("custom_notes") or "").strip(),
                        has_subtitles=bool(body.get("has_subtitles") or (raw_recipe or {}).get("has_subtitles")),
                    )
                pid = str(body.get("project_id") or "").strip() or cooking.make_cooking_project_id((raw_recipe or cooking.DEFAULT_RECIPE)["dish"])
                manifest = cooking.prepare(pid, raw_recipe)
                self._send_json({"ok": True, "project": manifest})
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        if path == "/api/cooking/quick-run":
            import cooking_storyboard_engine as cooking
            try:
                raw_recipe = body.get("recipe")
                dish = str(body.get("dish") or (raw_recipe or {}).get("dish") or "").strip()
                if not dish:
                    self._send_json({"ok": False, "error": "Vui lòng nhập tên món ăn cần làm video."}, 400)
                    return
                result = cooking.auto_create_and_launch(
                    dish=dish,
                    voice_id=str(body.get("voice_id") or "").strip(),
                    audio_mode=str(body.get("audio_mode") or "auto").strip(),
                    profile=str(body.get("profile_name") or "").strip(),
                    project_uuid=str(body.get("flow_project_id") or "auto").strip(),
                    num_clips=max(1, min(6, int(body.get("num_clips") or 3))),
                    custom_notes=str(body.get("custom_notes") or "").strip(),
                    has_subtitles=bool(body.get("has_subtitles")),
                    recipe=raw_recipe if isinstance(raw_recipe, dict) else None,
                    project_id=str(body.get("project_id") or "").strip(),
                    stage=str(body.get("stage") or "auto").strip() or "auto",
                    video_provider=str(body.get("video_provider") or "").strip(),
                )
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
                self._send_json(result)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        if path == "/api/cooking/run":
            import cooking_storyboard_engine as cooking
            try:
                result = cooking.launch_stage(
                    str(body.get("project_id") or "").strip(),
                    str(body.get("stage") or "").strip(),
                    profile=str(body.get("profile_name") or "").strip(),
                    project_uuid=str(body.get("flow_project_id") or "auto").strip(),
                    reviewed=body.get("storyboards_reviewed") is True,
                    video_provider=str(body.get("video_provider") or "").strip(),
                )
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
                self._send_json(result)
            except (ValueError, FileNotFoundError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        if path == "/api/cooking/stop":
            import cooking_storyboard_engine as cooking
            try:
                result = cooking.stop_stage(str(body.get("project_id") or "").strip())
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
                self._send_json(result)
            except (ValueError, FileNotFoundError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        if path == "/api/projects/create":
            name = (body.get("name") or "").strip()
            if not name:
                self._send_json({"ok": False, "error": "Tên dự án không được để trống"}, 400)
                return
            proj = core.create_or_get_project(
                name=name,
                role_skill_file=body.get("role_skill_file", "DoAnVat.MD"),
                img_model=body.get("img_model", "Nano Banana 2"),
                vid_model=body.get("vid_model", "Veo 3.1 - Fast"),
                aspect=body.get("aspect", "9:16"),
                num_scenes=int(body.get("num_scenes", 4)),
                seconds_per_scene=int(body.get("seconds_per_scene", 8)),
                video_resolution=body.get("video_resolution", "720p"),
                max_workers=int(body.get("max_workers", 3)),
            )
            self._send_json({"ok": True, "project": proj})
            return

        if path == "/api/projects/import-folder":
            project_id = body.get("project_id") or body.get("project_name") or ""
            folder_path = (body.get("folder_path") or "").strip().strip('"')
            role_skill = body.get("role_skill_file") or "DoAnVat.MD"
            try:
                proj = core.import_products_from_folder(
                    project_id,
                    folder_path,
                    role_skill_file=role_skill,
                    img_model=body.get("img_model", "Nano Banana 2"),
                    vid_model=body.get("vid_model", "Veo 3.1 - Fast"),
                    aspect=body.get("aspect", "9:16"),
                    num_scenes=int(body.get("num_scenes", 4)),
                )
                self._send_json({"ok": True, "project": proj})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 400)
            return

        if path == "/api/projects/import-items":
            project_id = body.get("project_id") or body.get("project_name") or ""
            items = body.get("items") or []
            role_skill = body.get("role_skill_file") or "DoAnVat.MD"
            try:
                proj = core.import_products_to_project(project_id, items, default_role_skill=role_skill)
                self._send_json({"ok": True, "project": proj})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 400)
            return

        if path == "/api/projects/submit-prompts":
            project_id = body.get("project_id") or body.get("project_name") or ""
            products_prompts = body.get("products") or []
            auto_run = bool(body.get("auto_run", False))
            try:
                proj = core.submit_agent_prompts(project_id, products_prompts)
                if auto_run:
                    threading.Thread(
                        target=_RUNNER.run_project_batch,
                        args=(proj["id"], int(body.get("product_workers", 2)), int(body.get("scene_workers", 3))),
                        daemon=True,
                    ).start()
                self._send_json({"ok": True, "project": proj})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 400)
            return

        if path == "/api/projects/run":
            project_id = (body.get("project_id") or "").strip()
            product_id = (body.get("product_id") or "").strip()
            template_name = (body.get("template_name") or "").strip()
            vpc = body.get("videos_per_character")
            vpc_int = int(vpc) if vpc is not None and str(vpc).strip() != "" else None
            force_prompts = bool(body.get("force_regenerate_prompts", False))
            prod_workers = int(body.get("product_workers", 2))
            scene_workers = int(body.get("scene_workers", 3))
            pdir = core.PROJECTS_DIR / project_id
            mt_script = PIPELINE_SCRIPTS_DIR / "run_all_7_videos_mt.py"
            marker = pdir / ".cleaned_new"

            # Nếu sản phẩm chưa có prompts.json, hoặc đang ở trạng thái Sản Phẩm Mới (.cleaned_new), hoặc người dùng chọn Template mới:
            # Tự động sinh kịch bản theo Template rồi kích hoạt đa luồng!
            if pdir.is_dir() and (not (pdir / "prompts.json").is_file() or marker.is_file() or force_prompts or template_name):
                _ensure_latest_sws()
                res = _pcb.prepare_and_optionally_run_product(
                    raw_id_or_url=project_id,
                    template_name=template_name or "001",
                    crawl_method="auto",
                    videos_per_character=vpc_int,
                    force_regenerate_prompts=True,
                    auto_run_pipeline=True,
                )
                if res.get("ok"):
                    self._send_json({
                        "ok": True,
                        "message": f"Đã tạo kịch bản Template [{res.get('template_name')}] ({res.get('videos_count', 6)} Video Final) và kích hoạt chạy đa luồng cho SP {project_id}!",
                        **res,
                    })
                else:
                    self._send_json(res, 400)
                return

            if (pdir / "prompts.json").is_file() and mt_script.is_file():
                if marker.is_file():
                    try:
                        marker.unlink()
                    except OSError:
                        pass
                log_file = pdir / "pipeline_run.log"
                log_fp = open(log_file, "a", encoding="utf-8", errors="replace")
                log_fp.write(f"\n=== RESUMED PIPELINE AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_fp.flush()
                proc = subprocess.Popen(
                    [sys.executable, "-u", str(mt_script), project_id],
                    cwd=str(SKILL_DIR),
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                )
                try:
                    st_init = {
                        "pid": project_id,
                        "pid_os": proc.pid,
                        "is_running": True,
                        "current_step_text": f"🚀 Đang khởi động tiến trình Đa Luồng cho SP {project_id}...",
                        "updated_at": time.strftime("%H:%M:%S"),
                    }
                    json.dump(st_init, open(pdir / "pipeline_status.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                except Exception:
                    pass
                sync_web_ui(force=True)
                self._send_json({"ok": True, "pid_os": proc.pid, "message": f"Đã kích hoạt chạy Đa Luồng cho SP {project_id} (PID={proc.pid})!"})
                return

        if path == "/api/projects/stop":
            pid = (body.get("project_id") or "").strip()
            res = _esm.stop_running_pipeline(pid)
            sync_web_ui(force=True)
            self._send_json(res)
            return

        if path == "/api/settings/save":
            res = _esm.save_engine_settings(body)
            self._send_json(res)
            return

        if path == "/api/fashion_motion/analyze_and_create":
            try:
                import fashion_ai_video_analyzer as _fava
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fava)
                importlib.reload(_fmce)
                slug = (body.get("project_id") or "fashion_lookbook_chan_vay_6e19").strip()
                title = (body.get("title") or "Lookbook Thời Trang Thay Đồ Theo Nhạc (2K Omni Flash)").strip()
                base_char_path = (body.get("base_char_path") or "").strip().strip('"')
                char_sheet_path = (body.get("char_sheet_path") or "").strip().strip('"')
                ref_video_path = (body.get("ref_video_path") or "").strip().strip('"')
                outfit_items = body.get("outfit_items") if isinstance(body.get("outfit_items"), list) else None
                preferred_chunk_sec = str(body.get("preferred_chunk_sec") or "auto").strip()
                generation_mode = _fmce.normalize_fashion_generation_mode(str(body.get("generation_mode") or "chained_i2v").strip())
                default_pstyle = (
                    "google_vids"
                    if generation_mode == "google_vids"
                    else ("chained_i2v" if generation_mode == "chained_i2v" else "timeline_pro")
                )
                prompt_style = str(body.get("prompt_style") or default_pstyle).strip()
                custom_scene_cuts = body.get("custom_scene_cuts") if isinstance(body.get("custom_scene_cuts"), dict) else None
                ai_provider = str(body.get("ai_provider") or "auto").strip()
                ai_model = str(body.get("ai_model") or "gemini-2.5-flash").strip()
                auto_render = bool(body.get("auto_render_preview_final", False))
                res = _fmce.create_or_update_fashion_motion_project(
                    project_id_slug=slug,
                    title=title,
                    base_char_path=base_char_path or None,
                    char_sheet_path=char_sheet_path or None,
                    ref_video_path=ref_video_path or None,
                    outfit_items=outfit_items,
                    preferred_chunk_sec=preferred_chunk_sec,
                    prompt_style=prompt_style,
                    generation_mode=generation_mode,
                    custom_scene_cuts=custom_scene_cuts,
                    ai_provider=ai_provider,
                    ai_model=ai_model,
                    auto_render_preview_final=auto_render,
                )
                res["projects"] = _fmce.list_fashion_motion_projects()
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path in ("/api/fashion_motion/switch_mode", "/api/fashion_motion/switch_generation_mode"):
            try:
                import fashion_ai_video_analyzer as _fava
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fava)
                importlib.reload(_fmce)
                slug = (body.get("project_id") or "fashion_lookbook_chan_vay_6e19").strip()
                gen_mode = str(body.get("generation_mode") or "chained_i2v").strip()
                res = _fmce.switch_fashion_project_generation_mode(slug, generation_mode=gen_mode)
                res["projects"] = _fmce.list_fashion_motion_projects()
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/run_scene":
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                slug = (body.get("project_id") or "fashion_lookbook_chan_vay_6e19").strip()
                scene_id = (body.get("scene_id") or "s1").strip()
                prof = (body.get("profile_name") or "").strip()
                gen_mode = (body.get("generation_mode") or "").strip()
                run_async = bool(body.get("async", True))
                if run_async:
                    proj_dir = os.path.join(_fmce.FASHION_STUDIO_DIR, slug)
                    m_path = os.path.join(proj_dir, "fashion_project.json")
                    cur_manifest = None
                    if os.path.exists(m_path):
                        try:
                            with open(m_path, "r", encoding="utf-8") as f:
                                cur_manifest = json.load(f)
                            if gen_mode:
                                cur_manifest["generation_mode"] = _fmce.normalize_fashion_generation_mode(gen_mode)
                            eff_sc_m = cur_manifest.get("generation_mode") or "chained_i2v"
                            cur_manifest["status"] = "running_flow"
                            cur_manifest["status_message"] = (
                                f"🌐 Đang kết nối Google Vids Web (Omni 1080p • Không reCAPTCHA) cho Phân Cảnh {scene_id.upper()}..."
                                if eff_sc_m == "google_vids"
                                else f"🚀 Đang khởi động trình duyệt Google Flow cho Phân Cảnh {scene_id.upper()}..."
                            )
                            cur_manifest["updated_at"] = time.strftime("%H:%M:%S")
                            for sc_obj in cur_manifest.get("scenes") or []:
                                if sc_obj.get("id") == scene_id:
                                    sc_obj["status"] = "preparing"
                                    sc_obj["attempt"] = 1
                                    sc_obj["max_attempts"] = 3 if eff_sc_m == "google_vids" else 4
                                    sc_obj["status_detail"] = (
                                        "🌐 Đang kết nối Google Vids Web & tải ảnh 2K qua Scotty..."
                                        if eff_sc_m == "google_vids"
                                        else "🚀 Đang kết nối Google Flow & chuẩn bị ảnh tham chiếu 2K..."
                                    )
                            with open(m_path, "w", encoding="utf-8") as f:
                                json.dump(cur_manifest, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    def _bg_scene_run():
                        try:
                            _fmce.run_single_fashion_motion_scene_on_flow(slug, scene_id, profile_name=prof, generation_mode=gen_mode)
                        except Exception as exc:
                            print(f"[FASHION-SCENE-FLOW ERR] {exc}", flush=True)
                    threading.Thread(target=_bg_scene_run, daemon=True).start()
                    try:
                        sync_web_ui(force=True)
                    except Exception:
                        pass
                    is_vids_s = "vids" in gen_mode.lower() or (cur_manifest or {}).get("generation_mode") == "google_vids"
                    self._send_json({
                        "ok": True,
                        "async": True,
                        "project_id": slug,
                        "scene_id": scene_id,
                        "project": cur_manifest,
                        "message": (
                            f"🌐 Đang tạo Video Phân Cảnh {scene_id.upper()} Native 1080p trên Google Vids Web (Không reCAPTCHA)!"
                            if is_vids_s
                            else f"🚀 Đang chạy tạo Video Phân Cảnh {scene_id.upper()} trên Google Flow!"
                        ),
                    })
                else:
                    res = _fmce.run_single_fashion_motion_scene_on_flow(slug, scene_id, profile_name=prof, generation_mode=gen_mode)
                    self._send_json(res, 200 if res.get("ok") else 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/retry_failed":
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                slug = (body.get("project_id") or "fashion_lookbook_chan_vay_6e19").strip()
                prof = (body.get("profile_name") or "").strip()

                def _bg_retry_failed():
                    try:
                        _fmce.retry_failed_fashion_scenes_on_flow(slug, profile_name=prof)
                    except Exception as exc:
                        print(f"[FASHION-RETRY-ERR] {exc}", flush=True)

                threading.Thread(target=_bg_retry_failed, daemon=True).start()
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
                self._send_json({
                    "ok": True,
                    "async": True,
                    "project_id": slug,
                    "message": f"🔁 Đang tự động Retry toàn bộ phân cảnh lỗi của dự án '{slug}' trên Google Flow!",
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/render_final":
            try:
                import fashion_motion_control_engine as _fmce
                import fashion_ai_video_analyzer as _fava
                importlib.reload(_fmce)
                importlib.reload(_fava)
                slug = (body.get("project_id") or "fashion_lookbook_chan_vay_6e19").strip()
                proj_dir = os.path.join(_fmce.FASHION_STUDIO_DIR, slug)
                manifest_path = os.path.join(proj_dir, "fashion_project.json")
                if not os.path.exists(manifest_path):
                    self._send_json({"ok": False, "error": f"Không tìm thấy dự án '{slug}'"}, 404)
                    return
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                res_final = _fava.render_fashion_postprod_final_video(slug, proj_dir, manifest, _fmce.FINAL_VIDEOS_DIR)
                if res_final.get("ok"):
                    res_final["project"] = manifest
                self._send_json(res_final, 200 if res_final.get("ok") else 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/run_flow":
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                slug = (body.get("project_id") or "fashion_motion_demo_7anh_2k").strip()
                prof = (body.get("profile_name") or "").strip()
                gen_mode = (body.get("generation_mode") or "").strip()

                proj_dir = os.path.join(_fmce.FASHION_STUDIO_DIR, slug)
                m_path = os.path.join(proj_dir, "fashion_project.json")
                if not os.path.isfile(m_path):
                    self._send_json({'ok':False,'error':'Dự án chưa được chuẩn bị. Thêm nhân vật và sản phẩm trước.'},400)
                    return
                with _FASHION_RUN_GUARD:
                    if slug in _FASHION_RUNNING:
                        self._send_json({'ok':False,'error':'Dự án đang chạy; không gửi thêm job trùng.'},409)
                        return
                    _FASHION_RUNNING.add(slug)
                cur_manifest = None
                if os.path.exists(m_path):
                    try:
                        with open(m_path, "r", encoding="utf-8") as f:
                            cur_manifest = json.load(f)
                        if gen_mode:
                            cur_manifest["generation_mode"] = _fmce.normalize_fashion_generation_mode(gen_mode)
                        eff_m = cur_manifest.get("generation_mode") or "chained_i2v"
                        cur_manifest["status"] = "running_flow"
                        cur_manifest["status_message"] = (
                            "🌐 Đang kết nối Google Vids Web (Omni 1080p Native • Không reCAPTCHA • Gắn 3 Chip Ảnh 2K)..."
                            if eff_m == "google_vids"
                            else (
                                "🚀 Đang khởi động Google Flow (Chế độ Chained Img2Video 0.1s Chuẩn Nhạc — Cắt Frame cuối Cảnh 1 nối Cảnh 2)..."
                                if eff_m == "chained_i2v"
                                else "🚀 Đang khởi động Google Flow (Chế độ Motion Control Video Ref — Cắt Frame cuối Cảnh 1 nối Cảnh 2)..."
                            )
                        )
                        cur_manifest["updated_at"] = time.strftime("%H:%M:%S")
                        for sc_obj in cur_manifest.get("scenes") or []:
                            sc_obj["status"] = "preparing"
                            sc_obj["attempt"] = 1
                            sc_obj["max_attempts"] = cur_manifest.get("max_scene_attempts", 3 if eff_m == "google_vids" else 4)
                            sc_obj["status_detail"] = (
                                "🌐 Đang kết nối Google Vids Web & chuẩn bị 3 ảnh 2K..."
                                if eff_m == "google_vids"
                                else "🚀 Đang kết nối Google Flow & chuẩn bị nguyên liệu 2K..."
                            )
                        with open(m_path, "w", encoding="utf-8") as f:
                            json.dump(cur_manifest, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                def _bg_run():
                    try:
                        _fmce.run_fashion_motion_project_on_flow(slug, profile_name=prof, generation_mode=gen_mode)
                    except Exception as exc:
                        print(f"[FASHION-FLOW ERR] {exc}", flush=True)
                    finally:
                        with _FASHION_RUN_GUARD: _FASHION_RUNNING.discard(slug)

                threading.Thread(target=_bg_run, daemon=True).start()
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
                is_vids_p = "vids" in gen_mode.lower() or (cur_manifest or {}).get("generation_mode") == "google_vids"
                self._send_json({
                    "ok": True,
                    "project_id": slug,
                    "project": cur_manifest,
                    "message": (
                        f"🌐 Đã kích hoạt chạy tạo Video Thời Trang '{slug}' Native 1080p trên Google Vids Web (Không reCAPTCHA)!"
                        if is_vids_p
                        else f"🚀 Đã kích hoạt chạy tạo Video Thời Trang '{slug}' trên Google Flow!"
                    ),
                })
            except Exception as e:
                if "slug" in locals():
                    with _FASHION_RUN_GUARD: _FASHION_RUNNING.discard(slug)
                self._send_json({"ok": False, "error": str(e)}, 500)
            return


        if path == "/api/flow/cdp_status":
            try:
                import urllib.request as _ur, json as _json
                try:
                    with _ur.urlopen("http://localhost:9222/json/version", timeout=2) as r:
                        info = _json.loads(r.read())
                    browser = info.get("Browser", "Chrome")
                    # Count Flow tabs
                    with _ur.urlopen("http://localhost:9222/json", timeout=2) as r2:
                        tabs = _json.loads(r2.read())
                    flow_tabs = sum(1 for t in tabs if "flow.google.com" in t.get("url", ""))
                    self._send_json({
                        "ok": True,
                        "browser": browser,
                        "flow_tabs": flow_tabs,
                        "account": "Đang kiểm tra...",
                    })
                except Exception as cdp_err:
                    self._send_json({"ok": False, "error": f"CDP port 9222 chưa mở: {cdp_err}"})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/flow/launch_chrome_cdp":
            try:
                # Kill Chrome and restart with debug port
                subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                               capture_output=True, timeout=5)
                time.sleep(2)
                chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                subprocess.Popen([
                    chrome_exe,
                    "--remote-debugging-port=9222",
                    "--restore-last-session",
                ])
                self._send_json({
                    "ok": True,
                    "message": "Chrome đang khởi động lại với Debug Port 9222. Chờ 5-8 giây rồi nhấn Kiểm Tra.",
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return


        if path == "/api/flow/extract_session":
            # Extract cookies + WIZ tokens từ Chrome profile
            # body: { profile: "Profile13" | "leviettung04" | "cdp" | "default" }
            try:
                profile = (body.get("profile") or "").strip()
                use_cdp = profile.lower() == "cdp"
                result_holder = {}

                def _do_extract():
                    try:
                        import sys as _sys
                        _sys.path.insert(0, str(SKILL_DIR))
                        # Import the extractor module
                        import importlib.util as _ilu
                        spec = _ilu.spec_from_file_location(
                            "extract_chrome_session",
                            str(SKILL_DIR / "extract_chrome_session.py")
                        )
                        mod = _ilu.module_from_spec(spec)
                        spec.loader.exec_module(mod)

                        if use_cdp:
                            data = mod.extract_via_cdp()
                        else:
                            found = mod.find_profile_by_name(profile or "Default")
                            if not found:
                                result_holder["error"] = f"Không tìm thấy profile: {profile}"
                                return
                            pname, ppath, is_native = found
                            data = mod.extract_via_playwright(ppath, pname, is_native)

                        if data:
                            out_name = data.get("profile_name", profile or "default_session")
                            saved = mod.save_session(data, out_name)
                            result_holder["ok"] = True
                            result_holder["saved_to"] = str(saved)
                            result_holder["cookies_count"] = len(data.get("cookies", []))
                            result_holder["has_at"] = bool(data.get("wiz_tokens", {}).get("at"))
                            result_holder["has_bl"] = bool(data.get("wiz_tokens", {}).get("bl"))
                            result_holder["email"] = data.get("email", "")
                            result_holder["profile_name"] = out_name
                        else:
                            result_holder["error"] = "Extraction thất bại (profile chưa đăng nhập hoặc Chrome bị chặn)"
                    except Exception as exc:
                        import traceback
                        result_holder["error"] = str(exc)
                        print(f"[EXTRACT-SESSION ERR] {traceback.format_exc()}", flush=True)

                t = threading.Thread(target=_do_extract, daemon=True)
                t.start()
                t.join(timeout=90)  # Wait up to 90s

                if result_holder.get("ok"):
                    self._send_json({
                        "ok": True,
                        "message": f"✅ Đã lấy {result_holder.get('cookies_count',0)} cookies từ profile {result_holder.get('profile_name','')}. WIZ.at={'✅' if result_holder.get('has_at') else '❌'}, WIZ.bl={'✅' if result_holder.get('has_bl') else '❌'}",
                        **result_holder,
                    })
                else:
                    self._send_json({"ok": False, "error": result_holder.get("error", "Timeout or unknown error")})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/flow/list_profiles":
            # List all Chrome profiles available
            try:
                import importlib.util as _ilu
                spec = _ilu.spec_from_file_location(
                    "extract_chrome_session",
                    str(SKILL_DIR / "extract_chrome_session.py")
                )
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                system_p = mod.get_system_profiles()
                native_p = mod.get_native_profiles()
                # Also check which profiles have valid saved cookies
                cookies_dir = SKILL_DIR / "cookies"
                saved_sessions = set()
                if cookies_dir.exists():
                    saved_sessions = {f.stem for f in cookies_dir.glob("*.json")}
                all_profiles = []
                for pname, pdata in sorted(system_p.items()):
                    all_profiles.append({
                        "id": pname,
                        "name": pdata.get("name", pname),
                        "email": pdata.get("email", ""),
                        "source": "system",
                        "has_session": pname in saved_sessions,
                    })
                for pname, pdata in sorted(native_p.items()):
                    all_profiles.append({
                        "id": pname,
                        "name": pname,
                        "email": pdata.get("email", ""),
                        "source": "native",
                        "has_session": pname in saved_sessions,
                    })
                self._send_json({"ok": True, "profiles": all_profiles})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/flow/token_manager_status":
            try:
                _mod_tms = _get_token_manager_module()
                self._send_json(_mod_tms.TOKEN_MANAGER.get_status())
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/flow/token_manager_toggle":
            try:
                _mod_tmt = _get_token_manager_module()
                _enabled = body.get("enabled", True)
                _profiles = body.get("profiles") or None
                if _enabled:
                    _mod_tmt.TOKEN_MANAGER.enable(profiles=_profiles, auto=True)
                    _mod_tmt.patch_gvt()
                    self._send_json({"ok": True, "message": "Token Manager đã bật - tự động làm mới session Chrome"})
                else:
                    _mod_tmt.TOKEN_MANAGER.disable()
                    self._send_json({"ok": True, "message": "Token Manager đã tắt"})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/generate_2k_asset":
            try:
                import fashion_motion_control_engine as _fmce
                asset_type = (body.get("asset_type") or "deconstructed_outfit_flatlay_2k").strip()
                prompt_str = (body.get("prompt") or body.get("prompt_str") or "").strip()
                ref_image_paths = body.get("ref_image_paths") if isinstance(body.get("ref_image_paths"), list) else []
                output_filename = (body.get("output_filename") or "").strip() or None
                slug = (body.get("project_id") or "fashion_motion_demo_7anh_2k").strip()
                prof = (body.get("profile_name") or "").strip()
                if not prompt_str:
                    std_map = _fmce.get_standard_fashion_prompts()
                    prompt_str = (std_map.get(asset_type) or {}).get("rendered_prompt") or ""
                res = _fmce.generate_fashion_2k_asset_on_flow(
                    asset_type=asset_type,
                    prompt_str=prompt_str,
                    ref_image_paths=ref_image_paths,
                    output_filename=output_filename,
                    project_id_slug=slug,
                    profile_name=prof,
                )
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/scan_templates":
            try:
                import fashion_video_template_catalog as _fvtc
                import fashion_motion_control_engine as _fmce
                force = bool(body.get("force", False))
                cat = _fvtc.scan_and_sync_fashion_video_templates(force_rescan=force)
                f_lib = _fmce.list_fashion_characters_and_outfits_library()
                self._send_json({
                    "ok": True,
                    "video_templates_catalog": cat,
                    "fashion_library": f_lib,
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/apply_template":
            try:
                import fashion_ai_video_analyzer as _fava
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fava)
                importlib.reload(_fmce)
                template_code = (body.get("template_code") or "FVT_001").strip()
                base_char_path = (body.get("base_char_path") or "").strip().strip('"') or None
                char_sheet_path = (body.get("char_sheet_path") or "").strip().strip('"') or None
                outfit_items = body.get("outfit_items") if isinstance(body.get("outfit_items"), list) else None
                project_id_slug = (body.get("project_id") or "").strip() or None
                if body.get('require_inputs') and (not base_char_path or not outfit_items):
                    self._send_json({'ok':False,'error':'Thêm nhân vật và ít nhất một sản phẩm trước khi tạo video.'},400)
                    return
                use_adult_safe_s1 = bool(body.get("use_adult_safe_s1", False))
                generation_mode = (body.get("generation_mode") or "chained_i2v").strip()
                auto_run_flow = bool(body.get("auto_run_flow") or body.get("auto_render_flow"))
                prof = (body.get("profile_name") or "").strip()

                manifest = _fmce.apply_fashion_video_template_to_project(
                    template_code=template_code,
                    base_char_path=base_char_path,
                    char_sheet_path=char_sheet_path,
                    outfit_items=outfit_items,
                    project_id_slug=project_id_slug,
                    use_adult_safe_s1=use_adult_safe_s1,
                    generation_mode=generation_mode,
                )
                if not manifest.get("ok"):
                    self._send_json(manifest, 400)
                    return

                if prof:
                    manifest["preferred_profile_name"] = prof
                if body.get('require_inputs'):
                    manifest.update(input_flow='simple',max_scene_attempts=int(body.get('max_scene_attempts') or 3))
                    with open(os.path.join(manifest['project_dir'],'fashion_project.json'),'w',encoding='utf-8') as f:
                        json.dump(manifest,f,ensure_ascii=False,indent=2)
                else:
                    manifest.pop('input_flow', None)
                    manifest.pop('input_assets_prepared', None)
                    manifest['max_scene_attempts'] = int(body.get('max_scene_attempts') or 4)
                    with open(os.path.join(manifest['project_dir'],'fashion_project.json'),'w',encoding='utf-8') as f:
                        json.dump(manifest,f,ensure_ascii=False,indent=2)
                target_slug = manifest.get("project_id")
                if auto_run_flow and target_slug:
                    eff_m = manifest.get("generation_mode") or "chained_i2v"
                    manifest["status"] = "running_flow"
                    manifest["status_message"] = (
                        f"🌐 Đang kết nối Google Vids Web cho Template {template_code} (Omni 1080p • Không reCAPTCHA)..."
                        if eff_m == "google_vids"
                        else (
                            f"🚀 Đang khởi động Google Flow cho Template {template_code} (Chế độ Chained Img2Video 0.1s Chuẩn Nhạc)..."
                            if eff_m == "chained_i2v"
                            else f"🚀 Đang khởi động Google Flow cho Template {template_code} (Chế độ Motion Control Video Ref)..."
                        )
                    )
                    manifest["updated_at"] = time.strftime("%H:%M:%S")
                    for sc_obj in manifest.get("scenes") or []:
                        sc_obj["status"] = "preparing"
                        sc_obj["attempt"] = 1
                        sc_obj["max_attempts"] = 3 if eff_m == "google_vids" else 4
                        sc_obj["status_detail"] = (
                            "🌐 Đang kết nối Google Vids Web & chuẩn bị 3 ảnh 2K..."
                            if eff_m == "google_vids"
                            else "🚀 Đang kết nối Google Flow & chuẩn bị ảnh tham chiếu 2K..."
                        )
                    try:
                        m_path = os.path.join(_fmce.FASHION_STUDIO_DIR, target_slug, "fashion_project.json")
                        with open(m_path, "w", encoding="utf-8") as f:
                            json.dump(manifest, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                    def _bg_tpl_run():
                        try:
                            _fmce.run_fashion_motion_project_on_flow(target_slug, profile_name=prof, generation_mode=eff_m)
                        except Exception as exc:
                            print(f"[FASHION-TPL-FLOW ERR] {exc}", flush=True)
                    threading.Thread(target=_bg_tpl_run, daemon=True).start()
                    manifest["flow_started"] = True
                    try:
                        sync_web_ui(force=True)
                    except Exception:
                        pass

                proj_copy = dict(manifest)
                manifest["project"] = proj_copy
                manifest["projects"] = _fmce.list_fashion_motion_projects()
                self._send_json(manifest, 200)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/deconstruct_outfit_2k":
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                source_image_path = (
                    body.get("source_image_path")
                    or body.get("raw_image_path")
                    or body.get("image_path")
                    or ""
                ).strip().strip('"')
                if not source_image_path:
                    self._send_json({"ok": False, "error": "Chưa chọn ảnh sản phẩm quần áo gốc."}, 400)
                    return
                outfit_name = (body.get("outfit_name") or "").strip()
                model_provider = (body.get("model_provider") or body.get("model_mode") or "nano_banana").strip()
                project_id_slug = (body.get("project_id") or "fashion_lookbook_chan_vay_6e19").strip()
                prof = (body.get("profile_name") or "").strip()

                res = _fmce.deconstruct_user_product_to_white_bg_sheet_2k(
                    source_image_path=source_image_path,
                    outfit_name=outfit_name,
                    model_provider=model_provider,
                    project_id_slug=project_id_slug,
                    profile_name=prof,
                )
                if isinstance(res, dict) and res.get("model_used") and not res.get("method_used"):
                    res["method_used"] = res["model_used"]
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/add_character":
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                char_image_path = (
                    body.get("char_image_path")
                    or body.get("pose_sheet_path")
                    or ""
                ).strip().strip('"')
                char_name = (body.get("char_name") or body.get("name") or "").strip()
                bg_image_path = (
                    body.get("bg_image_path")
                    or body.get("bg_ref_path")
                    or ""
                ).strip().strip('"')
                res = _fmce.add_custom_fashion_character(
                    char_image_path=char_image_path,
                    char_name=char_name,
                    bg_image_path=bg_image_path,
                )
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/fashion_motion/upload_file":
            try:
                import fashion_motion_control_engine as _fmce
                importlib.reload(_fmce)
                filename = str(body.get("filename") or "upload.png").strip()
                data_base64 = str(body.get("data_base64") or "").strip()
                kind = str(body.get("kind") or "outfit").strip()
                name = str(body.get("name") or "").strip()
                short_desc = str(body.get("short_desc") or "").strip()
                en_desc = str(body.get("en_desc") or "").strip()
                project_id_slug = str(body.get("project_id") or "").strip()
                auto_white_bg_local = bool(body.get("auto_white_bg_local", False))
                res = _fmce.upload_custom_fashion_asset_base64(
                    filename=filename,
                    data_base64=data_base64,
                    kind=kind,
                    name=name,
                    short_desc=short_desc,
                    en_desc=en_desc,
                    project_id_slug=project_id_slug,
                    auto_white_bg_local=auto_white_bg_local,
                )
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/workflows/save":
            try:
                _fwe = _get_fwe()
                wf_doc = body.get("workflow_doc") or body
                wf_id_slug = (body.get("wf_id") or wf_doc.get("_wf_id") or "").strip() or None
                saved = _fwe.save_workflow_document(wf_doc, wf_id_slug=wf_id_slug)
                self._send_json({"ok": True, "workflow": saved, "workflows": _fwe.list_saved_workflows()})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/workflows/delete":
            try:
                _fwe = _get_fwe()
                wf_id_slug = (body.get("wf_id") or "").strip()
                res = _fwe.delete_saved_workflow(wf_id_slug)
                res["workflows"] = _fwe.list_saved_workflows()
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/workflows/run":
            try:
                _fwe = _get_fwe()
                wf_doc = body.get("workflow_doc") or body
                wf_id_slug = (body.get("wf_id") or wf_doc.get("_wf_id") or "").strip() or None
                target_node_id = (body.get("target_node_id") or "").strip() or None
                selected_node_ids = body.get("selected_node_ids") if isinstance(body.get("selected_node_ids"), list) else None
                prof = (body.get("profile_name") or "").strip()
                saved = _fwe.save_workflow_document(wf_doc, wf_id_slug=wf_id_slug)
                run_sync = bool(body.get("sync", False))
                if run_sync:
                    res = _fwe.run_workflow_execution_pipeline(
                        saved,
                        target_node_id=target_node_id,
                        profile_name=prof,
                        selected_node_ids=selected_node_ids,
                    )
                    self._send_json(res, 200 if res.get("ok") else 400)
                else:
                    def _bg_wf_run():
                        try:
                            _fwe.run_workflow_execution_pipeline(
                                saved,
                                target_node_id=target_node_id,
                                profile_name=prof,
                                selected_node_ids=selected_node_ids,
                            )
                        except Exception as ex:
                            print(f"[WorkflowRunErr] {ex}")
                    threading.Thread(target=_bg_wf_run, daemon=True).start()
                    self._send_json({
                        "ok": True,
                        "async": True,
                        "wf_id": saved.get("_wf_id"),
                        "target_node_id": target_node_id,
                        "selected_node_ids": selected_node_ids,
                        "message": f"Đã khởi chạy {'Node ' + target_node_id if target_node_id else 'Workflow'} ngầm!",
                    })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path in ("/api/workflows/extract_end_frame", "/api/workflows/extract_last_frame"):
            try:
                _fwe = _get_fwe()
                video_path = (body.get("video_path") or "").strip()
                wf_id = (body.get("wf_id") or "wf").strip()
                res = _fwe.extract_video_end_frame_ffmpeg(video_path=video_path, wf_id=wf_id)
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path in ("/api/workflows/export_timeline", "/api/workflows/export_timeline_mp4"):
            try:
                _fwe = _get_fwe()
                clips = body.get("clips") if isinstance(body.get("clips"), list) else []
                wf_name = (body.get("wf_name") or body.get("wf_id") or "workflow_timeline").strip()
                out_filename = (body.get("out_filename") or "").strip() or None
                res = _fwe.export_workflow_timeline_mp4_ffmpeg(clips=clips, wf_name=wf_name, out_filename=out_filename)
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/workflows/test_prompt_ai":
            try:
                _fwe = _get_fwe()
                prompt_text = (body.get("prompt") or "").strip()
                system_prompt = (body.get("system_prompt") or "").strip()
                model_name = (body.get("model") or "gpt-5.4").strip()
                image_paths = body.get("image_paths") if isinstance(body.get("image_paths"), list) else []
                res = _fwe.call_cliproxy_chat_or_vision(
                    prompt_text=prompt_text,
                    image_paths=image_paths,
                    model_name=model_name,
                    system_instruction=system_prompt,
                )
                if isinstance(res, tuple):
                    ok, txt, err = res
                    res = {"ok": ok, "text": txt, "model": model_name, "error": err}
                self._send_json(res, 200 if res.get("ok") else 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/projects/apply-camera-broll":
            pid = (body.get("project_id") or body.get("pid") or "").strip()
            cam_cfg = body.get("camera_broll_settings") if isinstance(body.get("camera_broll_settings"), dict) else None
            fx_cfg = body.get("video_edit_fx_settings") if isinstance(body.get("video_edit_fx_settings"), dict) else None
            res = _esm.apply_camera_broll_to_project(pid=pid, override_settings=cam_cfg, override_fx=fx_cfg)
            sync_web_ui(force=True)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path in ("/api/projects/rebuild-fx", "/api/projects/rebuild-subtitles"):
            pid = (body.get("project_id") or body.get("pid") or "").strip()
            vkey = (body.get("vkey") or "").strip()
            fx_cfg = body.get("video_edit_fx_settings") if isinstance(body.get("video_edit_fx_settings"), dict) else None
            sub_cfg = body.get("subtitle_settings") if isinstance(body.get("subtitle_settings"), dict) else None
            if not pid:
                self._send_json({"ok": False, "error": "Vui lòng chọn mã Sản phẩm / Dự án cần Render lại Phụ đề (Subtitle)"}, 400)
                return
            res = _esm.rebuild_project_final_videos_with_fx(
                pid=pid,
                vkey=vkey,
                override_fx=fx_cfg,
                override_subtitle=sub_cfg,
            )
            sync_web_ui(force=True)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/thumbnails/generate":
            pid = (body.get("project_id") or body.get("pid") or "").strip()
            vkey = (body.get("vkey") or "v1").strip()
            all_variants = bool(body.get("all_variants", False))
            provider = (body.get("provider") or "").strip()
            custom_master = (body.get("custom_master_prompt") or "").strip()
            custom_prod_info = (body.get("custom_product_info") or body.get("product_info") or "").strip()
            preset_id = (body.get("preset_id") or "").strip()
            add_badge = body.get("add_text_badge")
            inject_01s = body.get("inject_01s")
            prefer_ref = bool(body.get("prefer_existing_ref", False))
            apply_template_only = bool(body.get("apply_template_only", False))
            if not pid:
                self._send_json({"ok": False, "error": "Thiếu project_id"}, 400)
                return
            if all_variants:
                res = _esm.generate_thumbnails_for_all_variants(
                    pid=pid,
                    provider=provider,
                    custom_master_prompt=custom_master,
                    preset_id=preset_id,
                    custom_product_info=custom_prod_info,
                    subject_mode=str(body.get("subject_mode") or "auto"),
                    headline=str(body.get("headline") or ""),
                    add_text_badge=add_badge,
                    inject_01s=inject_01s,
                    apply_template_only=apply_template_only,
                )
            else:
                res = _esm.generate_thumbnail_for_variant(
                    pid=pid,
                    vkey=vkey,
                    provider=provider,
                    custom_master_prompt=custom_master,
                    preset_id=preset_id,
                    custom_product_info=custom_prod_info,
                    subject_mode=str(body.get("subject_mode") or "auto"),
                    headline=str(body.get("headline") or ""),
                    add_text_badge=add_badge,
                    inject_01s=inject_01s,
                    prefer_existing_ref=prefer_ref,
                    apply_template_only=apply_template_only,
                )
            sync_web_ui(force=True)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/thumbnails/inject-01s":
            video_path = (body.get("video_path") or "").strip()
            thumb_path = (body.get("thumb_path") or "").strip()
            dur = float(body.get("duration_sec") or 0.1)
            res = _esm.inject_thumbnail_01s_into_video(video_path, thumb_path, duration_sec=dur)
            sync_web_ui(force=True)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/videos/delete-final":
            pid = (body.get("project_id") or "").strip()
            vkey = (body.get("vkey") or "").strip()
            f_path = (body.get("final_video_path") or "").strip()
            res = delete_final_video(pid=pid, vkey=vkey, final_video_path=f_path)
            self._send_json(res)
            return

        if path == "/api/projects/clean-render":
            pid = (body.get("project_id") or "").strip()
            also_del_finals = bool(body.get("also_delete_finals", False))
            clean_all_empty = bool(body.get("clean_all_empty", False))
            if clean_all_empty:
                sync_web_ui(force=True)
                idx = core._load_projects_index()
                cleaned_pids = []
                total_files = 0
                total_mb = 0.0
                for p in idx:
                    if (p.get("done_products") or 0) == 0 and p.get("has_rendered_cache"):
                        r = clean_product_rendered_cache(p["id"], also_delete_finals=False)
                        if r.get("ok"):
                            cleaned_pids.append(p["id"])
                            total_files += r.get("removed_count", 0)
                            total_mb += r.get("removed_mb", 0.0)
                self._send_json({
                    "ok": True,
                    "cleaned_pids": cleaned_pids,
                    "removed_count": total_files,
                    "removed_mb": round(total_mb, 2),
                })
                return

            if not pid:
                self._send_json({"ok": False, "error": "Thiếu ID sản phẩm"}, 400)
                return
            res = clean_product_rendered_cache(pid, also_delete_finals=also_del_finals)
            self._send_json(res)
            return

        if path == "/api/projects/delete":
            project_id = str(body.get("project_id") or "").strip()
            idx = core._load_projects_index()
            extra_dirs = [
                Path(str(p.get("project_dir") or ""))
                for p in idx
                if p.get("id") == project_id and str(p.get("project_dir") or "").strip()
            ]
            idx = [p for p in idx if p.get("id") != project_id]
            core._save_projects_index(idx)
            allowed_bases = [core.PROJECTS_DIR.resolve(), (SKILL_DIR / "fashion_motion_projects").resolve()]
            cand_dirs = list(extra_dirs)
            if project_id and Path(project_id).name == project_id and project_id not in (".", ".."):
                for base_dir in allowed_bases:
                    cand_dirs.append(base_dir / project_id)
            for cand in cand_dirs:
                try:
                    pdir = cand.resolve()
                    if any(pdir != b and pdir.is_relative_to(b) for b in allowed_bases) and pdir.is_dir():
                        shutil.rmtree(pdir, ignore_errors=True)
                except Exception:
                    pass
            self._send_json({"ok": True})
            return

        if path == "/api/open-folder":
            target = (body.get("path") or "").strip()
            dry_run = bool(body.get("dry_run", False))
            default_final_dir = Path(FINAL_VIDEOS_DIR)
            default_final_dir.mkdir(parents=True, exist_ok=True)
            if not target or target == "final_videos":
                p = default_final_dir
            else:
                norm_target = os.path.normpath(target)
                cand = Path(norm_target)
                if not cand.is_absolute():
                    cand = (SKILL_DIR / norm_target).resolve()
                if "thumbnails" in norm_target.lower() and not cand.exists() and not cand.suffix:
                    cand.mkdir(parents=True, exist_ok=True)
                if cand.exists():
                    p = cand
                elif cand.parent.exists():
                    p = cand.parent
                else:
                    p = default_final_dir
            try:
                opened = os.path.normpath(str(p.resolve())) if dry_run else _open_in_windows_explorer(p)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
                return
            self._send_json({"ok": True, "opened": opened, "is_file": p.is_file()})
            return

        if path == "/api/open-file":
            target = (body.get("path") or "").strip()
            dry_run = bool(body.get("dry_run", False))
            if not target:
                self._send_json({"ok": False, "error": "Thiếu đường dẫn file"}, 400)
                return
            p = Path(os.path.normpath(target))
            if not p.is_absolute():
                p = (SKILL_DIR / p).resolve()
            if not p.exists():
                self._send_json({"ok": False, "error": f"File không tồn tại: {p}"}, 404)
                return
            if sys.platform == "win32" and not dry_run:
                try:
                    _allow_foreground_window()
                    gfa.cleanup_hidden_desktop_windows()
                    gfa.spawn_process_on_user_desktop(["cmd.exe", "/c", "start", "", str(p.resolve())])
                except Exception as e:
                    self._send_json({"ok": False, "error": str(e)}, 500)
                    return
            self._send_json({"ok": True, "opened": str(p.resolve())})
            return

        if path == "/api/pick-folder":
            initial_dir = (body.get("initial_dir") or "").strip()
            init_path = Path(initial_dir) if initial_dir else SKILL_DIR
            if not init_path.is_Absolute() if hasattr(init_path, "is_Absolute") else not init_path.is_absolute():
                init_path = (SKILL_DIR / init_path).resolve()
            if not init_path.is_dir():
                init_path = SKILL_DIR
            tmp_out = SKILL_DIR / "data" / f"_picked_folder_{int(time.time()*1000)}.txt"
            tmp_out.parent.mkdir(parents=True, exist_ok=True)
            picker_code = (
                "import sys, pathlib, tkinter as tk; from tkinter import filedialog; "
                "root = tk.Tk(); root.geometry('1x1+400+250'); root.attributes('-topmost', True); "
                "root.lift(); root.focus_force(); root.withdraw(); "
                "d = filedialog.askdirectory(parent=root, initialdir=sys.argv[1], title='Chọn Thư Mục Trên Máy Tính — SkillAutoVeo'); "
                "pathlib.Path(sys.argv[2]).write_text(d or '', encoding='utf-8'); root.destroy()"
            )
            pyw = Path(sys.executable).with_name("pythonw.exe")
            py_bin = str(pyw) if pyw.is_file() else sys.executable
            try:
                _allow_foreground_window()
                proc = gfa.spawn_process_on_user_desktop([py_bin, "-c", picker_code, str(init_path), str(tmp_out)])
                proc.wait(timeout=180)
                picked = tmp_out.read_text(encoding="utf-8").strip() if tmp_out.is_file() else ""
            except Exception as e:
                picked = ""
            finally:
                try:
                    tmp_out.unlink(missing_ok=True)
                except Exception:
                    pass
            if picked:
                picked = os.path.normpath(picked)
            self._send_json({"ok": bool(picked), "path": picked, "cancelled": not bool(picked)})
            return

        if path in ("/api/templates/save-doc", "/api/templates/save_doc"):
            _ensure_latest_sws()
            tname = (body.get("template") or body.get("folder_name") or body.get("name") or "001").strip()
            doc_name = (body.get("doc_name") or "ROLE_SKILL.md").strip()
            content = body.get("content") or ""
            res = _tm.save_template_doc(tname, doc_name, content)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/roles/save":
            fname = (body.get("filename") or "").strip()
            content = body.get("content") or ""
            if not fname:
                self._send_json({"ok": False, "error": "Thiếu tên file Role Skill"}, 400)
                return
            saved = core.save_role_skill(fname, content)
            self._send_json({"ok": True, "path": saved, "roles": core.sync_role_skills_dirs()})
            return

        if path == "/api/roles/delete":
            fname = (body.get("filename") or "").strip()
            core.delete_role_skill(fname)
            self._send_json({"ok": True, "roles": core.sync_role_skills_dirs()})
            return

        if path == "/api/accounts/sync-cliproxy":
            acc_mgr = gvt.AccountManager()
            added, removed = acc_mgr.sync_from_cliproxy()
            self._send_json({
                "ok": True,
                "added": added,
                "removed": removed,
                "accounts": _RUNNER.get_accounts_info(),
            })
            return

        if path == "/api/accounts/toggle":
            name = body.get("name") or ""
            acc_mgr = gvt.AccountManager()
            for a in acc_mgr.accounts:
                if a.name == name:
                    a.active = not a.active
                    break
            acc_mgr.save()
            self._send_json({"ok": True, "accounts": _RUNNER.get_accounts_info()})
            return

        if path == "/api/accounts/delete":
            name = body.get("name") or ""
            acc_mgr = gvt.AccountManager()
            removed_profs = set()
            removed_emails = set()
            for a in acc_mgr.accounts:
                if a.name == name:
                    if getattr(a, "profile_name", ""):
                        removed_profs.add(a.profile_name.lower())
                    if getattr(a, "google_email", ""):
                        removed_emails.add(a.google_email.lower())
                    if a.name.startswith("Google_"):
                        removed_emails.add(a.name[len("Google_"):].lower())
            acc_mgr.accounts = [a for a in acc_mgr.accounts if a.name != name]
            acc_mgr.save()
            if removed_profs or removed_emails:
                reg_path = gvt.GROK_AUTH_ROOT / "Flow_nhieu_worker_accounts.json"
                if reg_path.is_file():
                    try:
                        reg_rows = json.loads(reg_path.read_text(encoding="utf-8"))
                        if isinstance(reg_rows, list):
                            new_reg = [
                                r for r in reg_rows
                                if not (
                                    isinstance(r, dict) and (
                                        str(r.get("email", "")).lower() in removed_emails
                                        or Path(str(r.get("profile_dir", ""))).name.lower() in removed_profs
                                    )
                                )
                            ]
                            gvt._atomic_write_json(reg_path, new_reg)
                    except Exception:
                        pass
            self._send_json({"ok": True, "accounts": _RUNNER.get_accounts_info()})
            return

        if path == "/api/accounts/open-captcha-extension-chrome":
            dry_run = bool(body.get("dry_run", False))
            res_ext = _launch_captcha_extension_chrome_window(dry_run=dry_run)
            _LOGIN_STATUS["state"] = "done"
            _LOGIN_STATUS["message"] = res_ext["message"]
            self._send_json(res_ext)
            return

        if path == "/api/accounts/open-chrome-profile":
            raw_prof = (body.get("profile_name") or "").strip() or (gvt._default_google_profile_name() or "")
            prof_name = re.sub(r"[^a-zA-Z0-9._@-]+", "_", raw_prof).strip("_")
            if not prof_name:
                self._send_json({"ok": False, "error": "Chưa có tên profile Google Flow. Hãy nhập tên profile (VD: flow_acc_1) hoặc thêm tài khoản mới trước."}, status=400)
                return
            dry_run = bool(body.get("dry_run", False))
            gfa.save_browser_settings(gvt.GROK_AUTH_ROOT, prof_name, {"channel": "chrome", "login_mode": "system_chrome"})
            pdir, _ = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof_name)
            pdir.mkdir(parents=True, exist_ok=True)
            exe = gfa.find_system_chrome()
            cmd_preview = gfa.native_login_command(exe, pdir)
            if not dry_run:
                _start_interactive_google_login(prof_name)
            self._send_json({
                "ok": True,
                "profile_name": prof_name,
                "profile_dir": str(pdir),
                "chrome_exe": str(exe),
                "command": [str(x) for x in cmd_preview],
                "accounts": _RUNNER.get_accounts_info(),
                "message": f"🌐 Đã mở cửa sổ Chrome độc lập (Profile: {prof_name}) — hãy đăng nhập rồi ĐÓNG cửa sổ Chrome đó để tự động lưu Cookie!",
            })
            return

        if path == "/api/accounts/add-google-account":
            raw_prof = (body.get("profile_name") or "").strip()
            acc_mgr = gvt.AccountManager()
            existing_profs = {
                gvt._google_profile_name_for_account(a, allow_unresolved=True)
                for a in acc_mgr.accounts
                if gvt._is_google_flow_account(a)
            }
            if not raw_prof:
                idx_num = 2
                while f"flow_acc_{idx_num}" in existing_profs:
                    idx_num += 1
                raw_prof = f"flow_acc_{idx_num}"
            prof_name = re.sub(r"[^a-zA-Z0-9._@-]+", "_", raw_prof) or "flow_acc_2"
            email_val = (body.get("email") or prof_name).strip()
            proj_id = (body.get("project_id") or gvt.DEFAULT_PROJECT_ID).strip() or gvt.DEFAULT_PROJECT_ID
            bearer_token = (body.get("bearer_token") or "").strip()
            cookie_input = (body.get("cookie_input") or "").strip()
            open_browser = bool(body.get("open_browser", True))

            flow_tok_from_cookie = ""
            if cookie_input:
                cookies_list = []
                if cookie_input.startswith("[") or cookie_input.startswith("{"):
                    try:
                        parsed_c = json.loads(cookie_input)
                        if isinstance(parsed_c, dict) and isinstance(parsed_c.get("cookies"), list):
                            cookies_list = parsed_c["cookies"]
                        elif isinstance(parsed_c, list):
                            cookies_list = parsed_c
                    except Exception:
                        cookies_list = []
                if not cookies_list:
                    for part in cookie_input.split(";"):
                        part = part.strip()
                        if "=" in part:
                            ck_name, ck_val = part.split("=", 1)
                            cookies_list.append({
                                "name": ck_name.strip(),
                                "value": ck_val.strip(),
                                "domain": ".google.com",
                                "path": "/",
                            })
                if cookies_list:
                    flow_tok_from_cookie = gfa._cookies_list_to_flow_token(cookies_list)
                    payload_c = json.dumps({"cookies": cookies_list, "origins": []}, indent=2, ensure_ascii=False)
                    for c_dir in (
                        gvt.GROK_AUTH_ROOT / "cookies",
                        SKILL_DIR / "data" / "google_flow_grok" / "cookies",
                        SKILL_DIR / "cookies",
                    ):
                        c_dir.mkdir(parents=True, exist_ok=True)
                        (c_dir / f"{prof_name}.json").write_text(payload_c, encoding="utf-8")

            try:
                gfa.save_browser_settings(gvt.GROK_AUTH_ROOT, prof_name, {"channel": "chrome", "login_mode": "system_chrome"})
                pdir_new, _ = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof_name)
                pdir_new.mkdir(parents=True, exist_ok=True)
                gvt._upsert_flow_profile_registry(email_val, prof_name, proj_id, mark_login=True)
            except Exception:
                pass

            eff_tok = bearer_token or flow_tok_from_cookie
            if eff_tok:
                gfa.commit_login(gvt.GROK_AUTH_ROOT, prof_name, email_val, eff_tok, proj_id)
                acc_name = f"Google_{email_val}" if not email_val.startswith("Google_") else email_val
            else:
                acc_name = email_val if email_val.startswith("Google_") else f"Google_{email_val}"
                found = False
                for a in acc_mgr.accounts:
                    if getattr(a, "profile_name", "") == prof_name or a.name == acc_name:
                        if proj_id:
                            a.proxy_url = proj_id
                        a.profile_name = prof_name
                        a.active = True
                        found = True
                        break
                if not found:
                    acc_mgr.accounts.append(
                        gvt.Account(
                            name=acc_name,
                            proxy_url=proj_id,
                            api_key="",
                            profile_name=prof_name,
                            google_email=email_val if "@" in email_val else "",
                            auth_state="logging_in" if open_browser else "missing",
                            active=True,
                        )
                    )
                acc_mgr.save()

            if open_browser:
                _start_interactive_google_login(prof_name, initial_email=email_val, initial_proj_id=proj_id)
                msg_out = (
                    f"🚀 Đã tạo Profile Chrome riêng '{prof_name}' và mở cửa sổ đăng nhập Google Flow! "
                    "Bạn chỉ cần đăng nhập 1 lần — hệ thống sẽ tự động bắt & làm mới Cookie mãi mãi."
                )
            else:
                _LOGIN_STATUS["state"] = "done"
                msg_out = f"✅ Đã lưu cấu hình tài khoản Google Flow: {acc_name} (Profile: {prof_name})"
                _LOGIN_STATUS["message"] = msg_out

            self._send_json({
                "ok": True,
                "profile_name": prof_name,
                "account_name": acc_name,
                "accounts": _RUNNER.get_accounts_info(),
                "message": msg_out,
            })
            return

        if path == "/api/accounts/refresh-google":
            target_prof = re.sub(r"[^a-zA-Z0-9._@-]+", "_", (body.get("profile_name") or "").strip())
            force_ref = bool(body.get("force_refresh", True))
            chk_credits = bool(body.get("check_credits", True))
            if target_prof:
                _LOGIN_STATUS["state"] = "running"
                _LOGIN_STATUS["message"] = f"🔄 Đang tự động mở ngầm Profile '{target_prof}' để lấy Cookie & Token Google Flow mới..."
                res = _refresh_and_commit_google_account(target_prof, force_refresh=force_ref, check_credits=chk_credits)
                _LOGIN_STATUS["state"] = "done" if res.get("ok") else "error"
                _LOGIN_STATUS["message"] = res.get("message") or res.get("error") or ""
                self._send_json({
                    **res,
                    "accounts": _RUNNER.get_accounts_info(),
                })
                return
            else:
                _LOGIN_STATUS["state"] = "running"
                _LOGIN_STATUS["message"] = "🔄 Đang tự động kiểm tra & lấy Cookie mới cho toàn bộ tài khoản Google Flow..."
                res = auto_refresh_all_google_accounts(
                    force_refresh=force_ref,
                    check_credits=chk_credits,
                    reason="làm mới thủ công",
                )
                self._send_json(res)
                return

        if path == "/api/accounts/sync-google-profiles":
            res = auto_refresh_all_google_accounts(
                force_refresh=False,
                check_credits=False,
                reason="quét & đồng bộ Profile Chrome",
            )
            self._send_json(res)
            return

        if path == "/api/accounts/login-google":
            prof_name = re.sub(r"[^a-zA-Z0-9._@-]+", "_", (body.get("profile_name") or "default_flow").strip()) or "default_flow"
            dry_run = bool(body.get("dry_run", False))
            pdir, _ = gfa.profile_paths(gvt.GROK_AUTH_ROOT, prof_name)
            pdir.mkdir(parents=True, exist_ok=True)
            exe = gfa.find_system_chrome()
            if not dry_run:
                _start_interactive_google_login(prof_name)
            self._send_json({
                "ok": True,
                "profile_name": prof_name,
                "profile_dir": str(pdir),
                "chrome_exe": str(exe),
                "accounts": _RUNNER.get_accounts_info(),
                "message": f"🌐 Đã mở trình duyệt Chrome (Profile: {prof_name}) để đăng nhập Google Flow 1 lần duy nhất.",
            })
            return

        if path == "/api/accounts/open-python-gui":
            _allow_foreground_window()
            prof_name = re.sub(r"[^a-zA-Z0-9._@-]+", "_", (body.get("profile_name") or "").strip())
            auto_login = bool(body.get("auto_login", False))
            dry_run = bool(body.get("dry_run", False))
            gui_script = SKILL_DIR / "flow_account_gui.py"
            pyw = Path(sys.executable).with_name("pythonw.exe")
            py_bin = str(pyw) if pyw.is_file() else sys.executable
            cmd_gui = [py_bin, str(gui_script)]
            if prof_name:
                cmd_gui.extend(["--profile", prof_name])
            if auto_login:
                cmd_gui.append("--auto-login")
            if not dry_run:
                gfa.spawn_process_on_user_desktop(cmd_gui, cwd=str(SKILL_DIR))
            self._send_json({
                "ok": True,
                "script": str(gui_script),
                "command": cmd_gui,
                "message": "🐍 Đã mở cửa sổ Quản Lý Tài Khoản Google Flow (Python Tool PyQt6) trên màn hình chính!",
            })
            return

        if path == "/api/accounts/login-cliproxy":
            provider = body.get("provider") or "xAI Grok"
            _allow_foreground_window()

            old_cw = _ACTIVE_CLIPROXY_WORKERS.get(provider)
            if old_cw is not None and getattr(old_cw, "_proc", None) is not None:
                try:
                    old_cw._proc.terminate()
                except Exception:
                    pass

            def _bg_cliproxy_login():
                _LOGIN_STATUS["state"] = "running"
                _LOGIN_STATUS["auth_url"] = ""
                _LOGIN_STATUS["message"] = f"🔑 Đang mở trình duyệt đăng nhập {provider}..."
                worker = gvt.LoginWorker(login_type=provider)
                _ACTIVE_CLIPROXY_WORKERS[provider] = worker

                def _on_st(t, c):
                    _LOGIN_STATUS["message"] = t
                    if getattr(worker, "auth_url", ""):
                        _LOGIN_STATUS["auth_url"] = worker.auth_url

                worker.status_sig.connect(_on_st)

                def _on_ok(info):
                    login_type, email = info.split("|", 1) if "|" in info else (provider, info)
                    prefix = "Codex" if "Codex" in login_type else "Grok"
                    acc_name = f"{prefix} - {email}"
                    acc_mgr = gvt.AccountManager()
                    if acc_name not in [a.name for a in acc_mgr.accounts]:
                        acc_mgr.add(acc_name, gvt.DEFAULT_PROXY_URL, "grok-video-key-001")
                    _LOGIN_STATUS["state"] = "done"
                    _LOGIN_STATUS["message"] = f"✅ Đã đăng nhập thành công: {acc_name}"

                worker.success_sig.connect(_on_ok)
                try:
                    worker.run()
                finally:
                    if getattr(worker, "auth_url", ""):
                        _LOGIN_STATUS["auth_url"] = worker.auth_url
                    if _ACTIVE_CLIPROXY_WORKERS.get(provider) is worker:
                        _ACTIVE_CLIPROXY_WORKERS.pop(provider, None)

            threading.Thread(target=_bg_cliproxy_login, daemon=True).start()
            self._send_json({"ok": True, "message": f"Đã khởi chạy đăng nhập {provider} và mở trình duyệt."})
            return

        if path == "/api/products-store/add":
            raw_input = (body.get("input") or body.get("url") or body.get("product_id") or "").strip()
            method = (body.get("method") or "auto").strip()
            force_crawl = bool(body.get("force", False))
            res = _pcb.ensure_product_crawled(raw_input, method=method, force_crawl=force_crawl)
            try:
                sync_web_ui(force=True)
            except Exception:
                pass
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/products-store/batch-add":
            raw_text = (body.get("text") or "").strip()
            method = (body.get("method") or "auto").strip()
            auto_fetch = bool(body.get("auto_fetch", True))
            lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
            added_pids = []
            errors = []
            for ln in lines:
                pid, rurl, err = _pcb.extract_or_resolve_pid(ln)
                if pid:
                    if pid not in added_pids:
                        added_pids.append(pid)
                    if _pcb.tt_research is not None:
                        try:
                            _pcb.tt_research.add_product(product_id=pid, share_url=rurl)
                        except Exception:
                            pass
                else:
                    errors.append(f"{ln[:50]}: {err}")

            if auto_fetch and added_pids:
                def _bg_batch_crawl(pids_to_crawl, m):
                    for p_id in pids_to_crawl:
                        try:
                            _pcb.ensure_product_crawled(p_id, method=m, force_crawl=False)
                        except Exception:
                            pass
                    try:
                        sync_web_ui(force=True)
                    except Exception:
                        pass

                threading.Thread(target=_bg_batch_crawl, args=(added_pids, method), daemon=True).start()

            self._send_json({
                "ok": True,
                "added_count": len(added_pids),
                "added_pids": added_pids,
                "errors": errors,
            })
            return

        if path == "/api/products-store/fetch-details":
            pid = (body.get("product_id") or body.get("input") or "").strip()
            method = (body.get("method") or "auto").strip()
            force = bool(body.get("force", True))
            if pid:
                res = _pcb.ensure_product_crawled(pid, method=method, force_crawl=force)
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
                self._send_json(res, 200 if res.get("ok") else 400)
                return
            # Batch fetch cho toàn bộ sản phẩm chưa đủ thông tin
            store = _pcb.list_all_products_store()
            pending_pids = [
                p["product_id"]
                for p in store.get("products", [])
                if force or p.get("status") != "ready" or p.get("image_count", 0) == 0
            ]
            fetched = 0
            for p_id in pending_pids:
                r = _pcb.ensure_product_crawled(p_id, method=method, force_crawl=force)
                if r.get("ok"):
                    fetched += 1
            try:
                sync_web_ui(force=True)
            except Exception:
                pass
            self._send_json({"ok": True, "fetched": fetched, "total_checked": len(pending_pids)})
            return

        if path == "/api/products-store/delete":
            pid = (body.get("product_id") or "").strip()
            also_del_project = bool(body.get("delete_project", False))
            if _pcb.tt_research is not None and pid:
                try:
                    _pcb.tt_research.remove_product(pid)
                except Exception:
                    pass
            if also_del_project and pid:
                pdir = core.PROJECTS_DIR / pid
                if pdir.is_dir():
                    shutil.rmtree(pdir, ignore_errors=True)
                try:
                    sync_web_ui(force=True)
                except Exception:
                    pass
            self._send_json({"ok": True, "product_id": pid})
            return

        if path == "/api/products-store/toggle-hot":
            pid = (body.get("product_id") or "").strip()
            is_hot = bool(body.get("is_hot", False))
            if pid and _pcb.tt_research is not None:
                try:
                    existing = _pcb.tt_research.get_product(pid)
                    if existing:
                        existing["is_hot"] = is_hot
                        _pcb.tt_research.add_or_update(existing)
                except Exception:
                    pass
            if pid:
                for p_info in (Path(_pcb.TIKTOK_CRAWLER_DATA_DIR) / "product_images" / pid / "info.json", core.PROJECTS_DIR / pid / "info.json"):
                    if p_info.is_file():
                        try:
                            info_obj = json.loads(p_info.read_text(encoding="utf-8", errors="ignore"))
                            info_obj["is_hot"] = is_hot
                            p_info.write_text(json.dumps(info_obj, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception:
                            pass
            self._send_json({"ok": True, "product_id": pid, "is_hot": is_hot})
            return

        if path == "/api/products-store/create-video":
            raw_input = (body.get("input") or body.get("product_id") or "").strip()
            template_name = (body.get("template_name") or "Nhà Xưởng").strip()
            crawl_method = (body.get("method") or "auto").strip()
            vpc = body.get("videos_per_character")
            vpc_int = int(vpc) if vpc is not None and str(vpc).strip() != "" else None
            primary_refs = body.get("primary_product_refs") or None
            slide_overlays = body.get("slide_overlay_files") or None
            force_prompts = bool(body.get("force_regenerate_prompts", True))
            auto_run = bool(body.get("auto_run", True))
            res = _pcb.prepare_and_optionally_run_product(
                raw_id_or_url=raw_input,
                template_name=template_name,
                crawl_method=crawl_method,
                videos_per_character=vpc_int,
                primary_product_refs=primary_refs,
                slide_overlay_files=slide_overlays,
                force_regenerate_prompts=force_prompts,
                auto_run_pipeline=auto_run,
            )
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/products-store/batch-create-video":
            raw_inputs = body.get("product_ids") or body.get("inputs") or []
            if not isinstance(raw_inputs, list):
                raw_inputs = [raw_inputs]
            template_name = (body.get("template_name") or "Nhà Xưởng").strip()
            crawl_method = (body.get("method") or "auto").strip()
            vpc = body.get("videos_per_character")
            vpc_int = int(vpc) if vpc is not None and str(vpc).strip() != "" else None
            force_prompts = bool(body.get("force_regenerate_prompts", True))
            auto_run = bool(body.get("auto_run", True))
            res = _pcb.batch_prepare_and_optionally_run_products(
                raw_inputs=raw_inputs,
                template_name=template_name,
                crawl_method=crawl_method,
                videos_per_character=vpc_int,
                force_regenerate_prompts=force_prompts,
                auto_run_pipeline=auto_run,
            )
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/characters/save":
            res = _clm.save_character_library_settings(body)
            self._send_json(res)
            return

        if path == "/api/characters/delete":
            ck = (body.get("char_key") or body.get("key") or "").strip()
            res = _clm.delete_character(ck)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/characters/save-voice":
            res = _clm.save_voice_profile(body)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/characters/delete-voice":
            vk = (body.get("voice_key") or body.get("key") or "").strip()
            res = _clm.delete_voice_profile(vk)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/characters/scan-flow-voices":
            res = _clm.scan_and_sync_flow_voices(body)
            self._send_json(res)
            return

        if path == "/api/characters/preview-voice-vn":
            res = _clm.preview_vietnamese_voice(body)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/characters/create-flow-custom-voice":
            res = _clm.create_custom_voice_on_flow(body)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/characters/recommend-voice":
            res = _clm.recommend_voice_for_product(body)
            self._send_json(res)
            return

        if path == "/api/characters/save-sheet-template":
            res = _clm.save_character_sheet_template(body)
            self._send_json(res)
            return

        if path == "/api/characters/generate-image":
            res = _clm.generate_character_or_product_image(body)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        self._send_json({"error": "Unknown endpoint"}, 404)


def _kill_process_on_port(port: int):
    """Giải phóng port nếu có tiến trình server cũ đang chiếm giữ."""
    if sys.platform != "win32":
        return
    try:
        out = subprocess.check_output(["netstat", "-ano", "-p", "TCP"], text=True, stderr=subprocess.DEVNULL)
        my_pid = os.getpid()
        for line in out.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = int(parts[-1])
                    if pid != my_pid and pid > 0:
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.4)
    except Exception:
        pass


def _is_http_server_healthy(port: int) -> bool:
    """Kiểm tra server trên port có thực sự phản hồi HTTP từ bên ngoài hay bị treo/kẹt trong sandbox."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Skill Video Veo Local Web Server")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true", help="Không tự mở cửa sổ Microsoft Edge App")
    parser.add_argument("--restart", action="store_true", help="Tắt server cũ trên port này và khởi động lại")
    parser.add_argument("--on-default-desktop", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        gfa.cleanup_hidden_desktop_windows()
    except Exception:
        pass

    if _is_port_open(args.port):
        if args.restart or not _is_http_server_healthy(args.port):
            _kill_process_on_port(args.port)

    ensure_background_services()
    core.sync_role_skills_dirs()
    trigger_async_sync_web_ui()

    url = f"http://127.0.0.1:{args.port}"
    if _is_port_open(args.port) and _is_http_server_healthy(args.port):
        print(f"Server Skill Video Veo đã chạy sẵn tại {url}", flush=True)
        if not args.no_browser:
            launch_microsoft_edge_app(url)
        return

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), SkillWebHandler)
    except OSError:
        _kill_process_on_port(args.port)
        server = ThreadingHTTPServer(("127.0.0.1", args.port), SkillWebHandler)

    print(f"🚀 Skill Video Veo Server đang chạy tại: {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, lambda: launch_microsoft_edge_app(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng server...", flush=True)
        server.server_close()


if __name__ == "__main__":
    main()
