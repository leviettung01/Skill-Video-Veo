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
import veo_skill_cli as core
import grok_video_tool as gvt
import sync_web_ui_state as _sws
import template_manager as _tm
import product_crawler_bridge as _pcb
import character_library_manager as _clm

FINAL_VIDEOS_DIR = _sws.FINAL_VIDEOS_DIR
_SWS_MTIME = 0.0
_TM_MTIME = 0.0
_PCB_MTIME = 0.0


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


def sync_web_ui(force: bool = True):
    return _ensure_latest_sws().sync_web_ui(force=force)


def delete_final_video(pid: str, vkey: str = "", final_video_path: str = ""):
    return _ensure_latest_sws().delete_final_video(pid=pid, vkey=vkey, final_video_path=final_video_path)


def clean_product_rendered_cache(pid: str, also_delete_finals: bool = False):
    return _ensure_latest_sws().clean_product_rendered_cache(pid=pid, also_delete_finals=also_delete_finals)

PORT = 8456
STATIC_DIR = SKILL_DIR / "static"

_RUNNER = core.MultiThreadSkillRunner()
_LOGIN_STATUS = {"state": "idle", "message": "Sẵn sàng đăng nhập tài khoản."}


def _allow_foreground_window():
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass


def _open_in_windows_explorer(target_path: Path):
    """Mở thư mục hoặc chọn file trực tiếp trong Windows Explorer và đưa cửa sổ lên phía trước."""
    _allow_foreground_window()
    resolved = target_path.resolve()
    norm = os.path.normpath(str(resolved))
    if sys.platform == "win32":
        if resolved.is_file():
            subprocess.Popen(["explorer.exe", f"/select,{norm}"])
        else:
            subprocess.Popen(["explorer.exe", norm])
    return norm


def _is_port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            s.connect(("127.0.0.1", port))
            return True
    except Exception:
        return False


def ensure_background_services():
    """Đảm bảo CaptchaBridge (:4000) và CLIProxy (:8317) luôn sẵn sàng."""
    _RUNNER.ensure_captcha_bridge()
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
    """Mở giao diện trên nhân Microsoft Edge ở chế độ App Mode (--app)."""
    edge_candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    for exe in edge_candidates:
        if exe.is_file():
            subprocess.Popen(
                [
                    str(exe),
                    f"--app={url}",
                    "--window-size=1420,900",
                    "--disable-features=Translate",
                ],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return True
    import webbrowser
    webbrowser.open(url)
    return False


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

        if path == "/api/status":
            try:
                sync_web_ui(force=False)
            except Exception:
                pass
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
            prof_default = gvt._default_google_profile_name() or "leviettung04"
            has_cookies = bool(gvt._load_flow_cookie_header(prof_default))
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
            })
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
            try:
                sync_web_ui(force=False)
            except Exception:
                pass
            self._send_json({"ok": True, "projects": core._load_projects_index()})
            return

        if path == "/api/project":
            try:
                sync_web_ui(force=False)
            except Exception:
                pass
            pid = (qs.get("id") or [""])[0]
            proj = core.load_project(pid)
            if not proj:
                self._send_json({"ok": False, "error": "Không tìm thấy dự án"}, 404)
                return
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
            if fpath_str:
                fpath_str = os.path.normpath(fpath_str.strip())
            if not fpath_str or not Path(fpath_str).is_file():
                self.send_response(404)
                self.send_header("Connection", "close")
                self.end_headers()
                return
            fpath = Path(fpath_str)
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

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

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
            project_id = body.get("project_id") or ""
            product_id = body.get("product_id") or ""
            prod_workers = int(body.get("product_workers", 2))
            scene_workers = int(body.get("scene_workers", 3))
            pdir = core.PROJECTS_DIR / project_id
            mt_script = PIPELINE_SCRIPTS_DIR / "run_all_7_videos_mt.py"
            if (pdir / "prompts.json").is_file() and mt_script.is_file():
                marker = pdir / ".cleaned_new"
                if marker.is_file():
                    try:
                        marker.unlink()
                    except OSError:
                        pass
                subprocess.Popen(
                    [sys.executable, "-u", str(mt_script), project_id],
                    cwd=str(SKILL_DIR),
                )
                sync_web_ui(force=True)
                self._send_json({"ok": True, "message": f"Đã kích hoạt tạo mới 6 Video Final đa luồng cho SP {project_id}!"})
                return

            product_ids = [product_id] if product_id else None
            threading.Thread(
                target=_RUNNER.run_project_batch,
                args=(project_id, prod_workers, scene_workers, product_ids),
                daemon=True,
            ).start()
            self._send_json({"ok": True, "message": "Đã kích hoạt chạy đa luồng!"})
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
            project_id = body.get("project_id") or ""
            idx = core._load_projects_index()
            idx = [p for p in idx if p["id"] != project_id]
            core._save_projects_index(idx)
            pdir = core.PROJECTS_DIR / project_id
            if pdir.is_dir():
                shutil.rmtree(pdir, ignore_errors=True)
            self._send_json({"ok": True})
            return

        if path == "/api/open-folder":
            target = (body.get("path") or "").strip()
            default_final_dir = Path(FINAL_VIDEOS_DIR)
            default_final_dir.mkdir(parents=True, exist_ok=True)
            if not target or target == "final_videos":
                p = default_final_dir
            else:
                p = Path(os.path.normpath(target))
                if not p.exists():
                    p = default_final_dir
            try:
                opened = _open_in_windows_explorer(p)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
                return
            self._send_json({"ok": True, "opened": opened})
            return

        if path == "/api/open-file":
            target = (body.get("path") or "").strip()
            if not target:
                self._send_json({"ok": False, "error": "Thiếu đường dẫn file"}, 400)
                return
            p = Path(os.path.normpath(target))
            if not p.exists():
                self._send_json({"ok": False, "error": f"File không tồn tại: {p}"}, 404)
                return
            if sys.platform == "win32":
                try:
                    _allow_foreground_window()
                    os.startfile(str(p.resolve()))
                except Exception as e:
                    self._send_json({"ok": False, "error": str(e)}, 500)
                    return
            self._send_json({"ok": True, "opened": str(p.resolve())})
            return

        if path == "/api/templates/save-doc":
            _ensure_latest_sws()
            tname = (body.get("template") or body.get("name") or "001").strip()
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
            acc_mgr.accounts = [a for a in acc_mgr.accounts if a.name != name]
            acc_mgr.save()
            self._send_json({"ok": True, "accounts": _RUNNER.get_accounts_info()})
            return

        if path == "/api/accounts/login-google":
            prof_name = (body.get("profile_name") or "default_flow").strip()

            def _bg_google_login():
                _LOGIN_STATUS["state"] = "running"
                _LOGIN_STATUS["message"] = f"🔍 Đang mở Chrome Profile '{prof_name}' để đăng nhập Google Flow..."
                worker = gvt.GoogleLoginWorker(profile_name=prof_name)
                worker.status_sig.connect(lambda t, c: _LOGIN_STATUS.update({"message": t}))

                def _on_ok(email, token, proj_id):
                    saved_prof = getattr(worker, "profile_name", "") or gvt._resolve_google_profile_name(email) or prof_name
                    acc_name = f"Google_{email}"
                    acc_mgr = gvt.AccountManager()
                    exists = False
                    for a in acc_mgr.accounts:
                        if a.name == acc_name:
                            a.api_key = token
                            a.proxy_url = proj_id
                            a.profile_name = saved_prof
                            a.active = True
                            exists = True
                            break
                    if not exists:
                        acc_mgr.accounts.append(
                            gvt.Account(
                                name=acc_name,
                                proxy_url=proj_id,
                                api_key=token,
                                profile_name=saved_prof,
                                active=True,
                            )
                        )
                    acc_mgr.save()
                    gvt._upsert_flow_profile_registry(email, saved_prof, proj_id, mark_login=True)
                    _LOGIN_STATUS["state"] = "done"
                    _LOGIN_STATUS["message"] = f"✅ Đã đăng nhập thành công Google Flow: {email}"

                def _on_err(err):
                    _LOGIN_STATUS["state"] = "error"
                    _LOGIN_STATUS["message"] = f"❌ Lỗi đăng nhập Google: {err}"

                worker.success_sig.connect(_on_ok)
                worker.error_sig.connect(_on_err)
                worker.run()

            threading.Thread(target=_bg_google_login, daemon=True).start()
            self._send_json({"ok": True, "message": "Đã mở trình duyệt đăng nhập Google Flow."})
            return

        if path == "/api/accounts/login-cliproxy":
            provider = body.get("provider") or "xAI Grok"

            def _bg_cliproxy_login():
                _LOGIN_STATUS["state"] = "running"
                _LOGIN_STATUS["message"] = f"🔑 Đang mở trình duyệt đăng nhập {provider}..."
                worker = gvt.LoginWorker(login_type=provider)
                worker.status_sig.connect(lambda t, c: _LOGIN_STATUS.update({"message": t}))

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
                worker.run()

            threading.Thread(target=_bg_cliproxy_login, daemon=True).start()
            self._send_json({"ok": True, "message": f"Đã khởi chạy đăng nhập {provider}."})
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


def main():
    parser = argparse.ArgumentParser(description="Skill Video Veo Local Web Server")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true", help="Không tự mở cửa sổ Microsoft Edge App")
    args = parser.parse_args()

    ensure_background_services()
    core.sync_role_skills_dirs()
    try:
        sync_web_ui(force=True)
    except Exception:
        pass

    url = f"http://127.0.0.1:{args.port}"
    if _is_port_open(args.port):
        print(f"Server Skill Video Veo đã chạy sẵn tại {url}")
        if not args.no_browser:
            launch_microsoft_edge_app(url)
        return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), SkillWebHandler)
    print(f"🚀 Skill Video Veo Server đang chạy tại: {url}")
    if not args.no_browser:
        threading.Timer(0.8, lambda: launch_microsoft_edge_app(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng server...")
        server.server_close()


if __name__ == "__main__":
    main()
