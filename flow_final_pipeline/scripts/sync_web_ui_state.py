# -*- coding: utf-8 -*-
import os
from pathlib import Path
import re
import sys
import glob
import json
import time
import shutil
import ast
import builtins
import importlib
import threading

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _hotpatch_live_modules():
    """Keep long-lived server.py in-memory transform_engine & grok_video_tool Flow
    RPC helpers synchronized with disk without restarting CaptchaBridge on :4000.
    """
    cache = getattr(builtins, "_SKILLVEO_HOTPATCH_MTIMES", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(builtins, "_SKILLVEO_HOTPATCH_MTIMES", cache)

    here = Path(__file__).resolve()
    root_dir = here.parents[2]
    try:
        sws_mtime = here.stat().st_mtime
        if cache.get("sws_mtime") != sws_mtime:
            cache.clear()
            cache["sws_mtime"] = sws_mtime
    except Exception:
        pass

    for mod_name in ("transform_engine", "flow_final_pipeline.scripts.transform_engine"):
        t_mod = sys.modules.get(mod_name)
        t_file = here.parent / "transform_engine.py"
        if t_mod is not None and t_file.is_file():
            try:
                mtime = t_file.stat().st_mtime
                if cache.get(f"te:{mod_name}") != mtime:
                    prev_lock = getattr(t_mod, "LOCK", None)
                    prev_queue_cond = getattr(t_mod, "_QUEUE_COND", None)
                    prev_active_jobs = getattr(t_mod, "_ACTIVE_JOBS", None)
                    prev_stopped_jobs = getattr(t_mod, "_STOPPED_JOBS", None)
                    importlib.reload(t_mod)
                    if prev_lock is not None:
                        t_mod.LOCK = prev_lock
                    if prev_queue_cond is not None:
                        t_mod._QUEUE_COND = prev_queue_cond
                    if isinstance(prev_active_jobs, set):
                        t_mod._ACTIVE_JOBS = prev_active_jobs
                    if isinstance(prev_stopped_jobs, set):
                        t_mod._STOPPED_JOBS = prev_stopped_jobs
                    cache[f"te:{mod_name}"] = mtime
            except Exception:
                pass

    for mod_name in ("thumbnail_template_engine", "flow_final_pipeline.scripts.thumbnail_template_engine"):
        tt_mod = sys.modules.get(mod_name)
        tt_file = here.parent / "thumbnail_template_engine.py"
        if tt_mod is not None and tt_file.is_file():
            try:
                mtime = tt_file.stat().st_mtime
                if cache.get(f"tte:{mod_name}") != mtime:
                    importlib.reload(tt_mod)
                    cache[f"tte:{mod_name}"] = mtime
            except Exception:
                pass

    for mod_name in ("cooking_studio_projection", "flow_final_pipeline.scripts.cooking_studio_projection"):
        csp_mod = sys.modules.get(mod_name)
        csp_file = here.parent / "cooking_studio_projection.py"
        if csp_mod is not None and csp_file.is_file():
            try:
                mtime = csp_file.stat().st_mtime
                if cache.get(f"csp:{mod_name}") != mtime:
                    importlib.reload(csp_mod)
                    cache[f"csp:{mod_name}"] = mtime
            except Exception:
                pass

    for mod_name in ("engine_settings_manager", "flow_final_pipeline.scripts.engine_settings_manager"):
        e_mod = sys.modules.get(mod_name)
        e_file = here.parent / "engine_settings_manager.py"
        if e_mod is not None and e_file.is_file():
            try:
                mtime = e_file.stat().st_mtime
                if cache.get(f"esm:{mod_name}") != mtime:
                    prev_hw = getattr(e_mod, "_HW_CACHE", None)
                    prev_pref_lock = getattr(e_mod, "_THUMB_PREFERRED_LOCK", None)
                    prev_pref_list = getattr(e_mod, "_THUMB_PREFERRED_PROFILES", None)
                    importlib.reload(e_mod)
                    if prev_hw is not None:
                        e_mod._HW_CACHE = prev_hw
                    if prev_pref_lock is not None:
                        e_mod._THUMB_PREFERRED_LOCK = prev_pref_lock
                    if isinstance(prev_pref_list, list):
                        e_mod._THUMB_PREFERRED_PROFILES = prev_pref_list
                    if mod_name == "engine_settings_manager":
                        globals()["_esm"] = e_mod
                    cache[f"esm:{mod_name}"] = mtime
            except Exception:
                pass

    gvt_mod = sys.modules.get("grok_video_tool")
    gvt_file = root_dir / "grok_video_tool.py"
    if gvt_mod is not None and gvt_file.is_file():
        try:
            mtime = gvt_file.stat().st_mtime
            if cache.get("gvt") != mtime:
                import threading as _th_hp
                prev_actor = getattr(gvt_mod, "_flow_browser_actor_instance", None)
                if prev_actor is not None and hasattr(prev_actor, "shutdown"):
                    try:
                        prev_actor.shutdown()
                    except Exception:
                        pass
                src = gvt_file.read_text(encoding="utf-8")
                tree = ast.parse(src, filename=str(gvt_file))
                target_names = {
                    "VideoJob",
                    "_FLOW_HIJACK_BYPASS_JS",
                    "_FLOW_RECAPTCHA_SITEKEY",
                    "_cookie_str_to_playwright_list",
                    "_load_playwright_cookies_for_flow",
                    "_FlowBrowserActor",
                    "_get_flow_browser_actor",
                    "invalidate_flow_chrome_session",
                    "_execute_flow_rpc_in_chrome",
                    "_find_signed_flow_urls",
                    "_request_captcha_for_account",
                    "get_connected_extension_bridge",
                    "fetch_flow_wiz_http",
                    "ExtensionHttpFlowPage",
                    "open_extension_flow_session",
                    "_cookie_header_to_dict_list",
                    "_ExtBrowserContext",
                    "_ExtBrowser",
                    "_ExtChromiumLauncher",
                    "_ExtPlaywrightShim",
                    "flow_playwright_or_extension",
                    "_run_veo_flow_batchexecute",
                    "_run_veo_flow_single_attempt",
                    "run_veo_flow",
                }
                nodes = []
                for node in tree.body:
                    if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                        nodes.append(node)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name in target_names:
                            nodes.append(node)
                    elif isinstance(node, ast.Assign):
                        if any(isinstance(t, ast.Name) and t.id in target_names for t in node.targets):
                            nodes.append(node)
                if "_flow_browser_actor_lock" not in gvt_mod.__dict__:
                    gvt_mod.__dict__["_flow_browser_actor_lock"] = _th_hp.Lock()
                if "_flow_mzza6b_preferred_profiles" not in gvt_mod.__dict__:
                    gvt_mod.__dict__["_flow_mzza6b_preferred_profiles"] = set()
                if "_SHARED_EXT_BRIDGE_LOCK" not in gvt_mod.__dict__:
                    gvt_mod.__dict__["_SHARED_EXT_BRIDGE_LOCK"] = _th_hp.Lock()
                if "_SHARED_EXT_BRIDGE" not in gvt_mod.__dict__:
                    gvt_mod.__dict__["_SHARED_EXT_BRIDGE"] = None
                gvt_mod.__dict__["_flow_browser_actor_instance"] = None
                if nodes:
                    patch_mod = ast.Module(body=nodes, type_ignores=[])
                    ast.fix_missing_locations(patch_mod)
                    exec(compile(patch_mod, str(gvt_file), "exec"), gvt_mod.__dict__)
                cache["gvt"] = mtime
        except Exception:
            pass

    vsc_mod = sys.modules.get("veo_skill_cli")
    vsc_file = root_dir / "veo_skill_cli.py"
    if vsc_mod is not None and vsc_file.is_file():
        try:
            mtime = vsc_file.stat().st_mtime
            if cache.get("veo_skill_cli") != mtime:
                src = vsc_file.read_text(encoding="utf-8")
                tree = ast.parse(src, filename=str(vsc_file))
                cls_nodes = [
                    node for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == "MultiThreadSkillRunner"
                ]
                if cls_nodes:
                    tmp_ns = dict(vsc_mod.__dict__)
                    patch_mod = ast.Module(body=cls_nodes, type_ignores=[])
                    ast.fix_missing_locations(patch_mod)
                    exec(compile(patch_mod, str(vsc_file), "exec"), tmp_ns)
                    new_cls = tmp_ns.get("MultiThreadSkillRunner")
                    old_cls = getattr(vsc_mod, "MultiThreadSkillRunner", None)
                    if new_cls is not None and old_cls is not None:
                        for attr_name in (
                            "FLOW_SUBMIT_DELAY_SEC",
                            "FLOW_GLOBAL_STAGGER_SEC",
                            "_throttle_flow_submit",
                            "mark_account_cooldown",
                            "_schedule_profile_heal",
                            "ensure_captcha_bridge",
                            "_resolve_flow_token_for_account",
                            "flow_account_candidates",
                            "_next_account",
                            "_run_veo_flow_with_failover",
                            "_generate_single_scene_image",
                            "_generate_single_scene_video",
                            "run_single_product",
                            "run_project_batch",
                        ):
                            if attr_name in new_cls.__dict__:
                                setattr(old_cls, attr_name, new_cls.__dict__[attr_name])
                cache["veo_skill_cli"] = mtime
        except Exception:
            pass


_hotpatch_live_modules()

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    import engine_settings_manager as _esm
except Exception:
    _esm = None

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECTS_DIR = os.path.join(WORKSPACE, "projects")
FINAL_VIDEOS_DIR = os.path.join(WORKSPACE, "final_videos")
CHARS_DIR = os.path.join(WORKSPACE, "flow_final_pipeline", "characters")

os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)

ALL_PIDS = [
    "1738086213622335480",
    "1735109997221349342",
    "1738260652434293979",
    "1735811961345574265",
    "1737365863541671120",
    "1738175423853987061",
    "1735424296473888680",
    "1737909342761027082",
]

VKEY_TO_CHAR_V = {
    "v1": "nv1_v1",
    "v3": "nv1_v2",
    "v5": "nv1_v3",
    "v7": "nv1_v4",
    "v9": "nv1_v5",
    "v2": "nv2_v1",
    "v4": "nv2_v2",
    "v6": "nv2_v3",
    "v8": "nv2_v4",
    "v10": "nv2_v5",
}

CHAR_V_TO_VKEY = {v: k for k, v in VKEY_TO_CHAR_V.items()}

DEFAULT_HOOK_LABELS = {
    "v1": "NV1 - Kịch bản 1: Trợ Giá Sàn",
    "v3": "NV1 - Kịch bản 2: Báo Động Giá Xưởng",
    "v5": "NV1 - Kịch bản 3: Xả Kho Lô Mới",
    "v2": "NV2 - Kịch bản 1: Giá Sốc Tận Xưởng",
    "v4": "NV2 - Kịch bản 2: Không Qua Trung Gian",
    "v6": "NV2 - Kịch bản 3: Săn Deal Tận Gốc",
}

_LAST_SYNC_TS = 0.0
_SYNC_LOCK = threading.RLock()


def get_char_v_code(vkey: str, char_key: str = "") -> str:
    vk = (vkey or "").lower().strip()
    if vk in VKEY_TO_CHAR_V:
        return VKEY_TO_CHAR_V[vk]
    if re.match(r"^nv\d+_v\d+$", vk):
        return vk
    m_ck = re.search(r"(nv\d+)", (char_key or "").lower())
    ck = m_ck.group(1) if m_ck else "nv1"
    return f"{ck}_{vk}"


def get_final_video_filename(pid: str, vkey: str, char_key: str = "") -> str:
    char_v = get_char_v_code(vkey, char_key)
    return f"{pid}_{char_v}.mp4"


def _list_rendered_intermediate_files(pdir: str) -> list:
    """Liệt kê toàn bộ ảnh ref AI, video phân cảnh 10s và trạng thái render trong thư mục sản phẩm (không đụng vào product_images/)."""
    patterns = [
        "*-refimg.jpg",
        "*-refimg.png",
        "v*_s*.mp4",
        "v*_s*.mp4.720p.tmp",
        "nv*_s*.mp4",
        "nv*-s*.mp4",
        "_norm_*.mp4",
        "_tmp_*.ass",
        "*-final-30s.mp4",
        "*_nv1_v*.mp4",
        "*_nv2_v*.mp4",
        "*_nv3_v*.mp4",
        "*_nv*_v*.mp4",
        "*_thumb.jpg",
        "storyboard_s*.jpg",
        "cooking_s*.mp4",
        "qa_gpt_thumbnail*.jpg",
        "flow_state.json",
        "flow_refs_state.json",
        "pipeline_status.json",
        "spec_*.json",
    ]
    found = []
    for pat in patterns:
        for fp in glob.glob(os.path.join(pdir, pat)):
            if os.path.isfile(fp) and fp not in found:
                found.append(fp)
    return found


def delete_final_video(pid: str, vkey: str = "", final_video_path: str = "") -> dict:
    """Xoá 1 video final khỏi thư mục final_videos/ và đánh dấu đã xoá để Dashboard tự ẩn video đó."""
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not vkey and final_video_path:
        bname = os.path.basename(final_video_path).replace(".mp4", "")
        if "_nv" in bname:
            suffix = bname.split("_", 1)[1].lower()
            vkey = CHAR_V_TO_VKEY.get(suffix, suffix)
        else:
            parts = bname.replace("-final-30s", "").split("-")
            if len(parts) >= 2:
                vkey = parts[1].lower()
    if vkey and vkey.lower() in CHAR_V_TO_VKEY:
        vkey = CHAR_V_TO_VKEY[vkey.lower()]
    elif vkey and "_" in vkey and not vkey.lower().startswith(("nv", "pov")):
        vkey = vkey.split("_")[-1].lower()

    char_v = "pov" if vkey in ("pov", "pov_v1") else get_char_v_code(vkey)
    new_fname = f"{pid}_{char_v}.mp4"
    old_fname = f"{pid}-{vkey}-final-30s.mp4"

    deleted_files = []
    candidates = []
    if final_video_path:
        candidates.append(os.path.normpath(final_video_path))
    if pid and vkey:
        candidates.append(os.path.join(FINAL_VIDEOS_DIR, new_fname))
        candidates.append(os.path.join(pdir, new_fname))
        candidates.append(os.path.join(FINAL_VIDEOS_DIR, old_fname))
        candidates.append(os.path.join(pdir, old_fname))
        if vkey in ("pov", "pov_v1", "v1", "nv1_v1"):
            candidates.append(os.path.join(FINAL_VIDEOS_DIR, f"{pid}_final.mp4"))
            candidates.append(os.path.join(pdir, f"{pid}_final.mp4"))

    for cpath in candidates:
        if cpath and os.path.isfile(cpath):
            try:
                os.remove(cpath)
                deleted_files.append(cpath)
            except OSError:
                pass

    cooking_mf = os.path.join(pdir, "cooking_manifest.json")
    fashion_mf = os.path.join(WORKSPACE, "fashion_motion_projects", pid, "fashion_project.json")
    if os.path.isfile(cooking_mf):
        try:
            mdata = json.load(open(cooking_mf, encoding="utf-8"))
            mdata["final_video_path"] = ""
            if mdata.get("status") == "done":
                mdata["status"] = "storyboards_ready"
                mdata["status_message"] = "Đã xoá Video Final (còn giữ nguyên Storyboard & Clip phân cảnh)."
            with open(cooking_mf, "w", encoding="utf-8") as f:
                json.dump(mdata, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    elif os.path.isfile(fashion_mf):
        try:
            fmdata = json.load(open(fashion_mf, encoding="utf-8"))
            if fmdata.get("final_video_path") and not os.path.isfile(fmdata["final_video_path"]):
                fmdata["final_video_path"] = ""
                with open(fashion_mf, "w", encoding="utf-8") as f:
                    json.dump(fmdata, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    elif os.path.isdir(pdir) and vkey:
        state_path = os.path.join(pdir, "flow_state.json")
        state = {"uploaded_refs": {}, "scene_uuids": {}, "built_finals": []}
        if os.path.exists(state_path):
            try:
                with open(state_path, encoding="utf-8") as _f_st0:
                    state = json.load(_f_st0)
            except Exception:
                pass
        bf = set(state.get("built_finals") or [])
        bf.add(vkey)
        state["built_finals"] = sorted(list(bf))
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    sync_web_ui(force=True)
    return {"ok": True, "pid": pid, "vkey": vkey, "deleted_files": deleted_files}


def clean_product_rendered_cache(pid: str, also_delete_finals: bool = False) -> dict:
    """
    Xoá toàn bộ ảnh ref AI, video phân cảnh 10s và trạng thái render cũ của sản phẩm
    để đưa sản phẩm về nguyên trạng như 1 sản phẩm mới (giữ nguyên thư mục product_images/).
    """
    pdir = os.path.join(PROJECTS_DIR, pid)
    fashion_dir = os.path.join(WORKSPACE, "fashion_motion_projects", pid)
    if not os.path.isdir(pdir) and not os.path.isdir(fashion_dir):
        return {"ok": False, "error": f"Không tìm thấy thư mục sản phẩm: {pid}"}

    removed_count = 0
    removed_bytes = 0
    if os.path.isdir(pdir):
        for fp in _list_rendered_intermediate_files(pdir):
            try:
                sz = os.path.getsize(fp)
                os.remove(fp)
                removed_count += 1
                removed_bytes += sz
            except OSError:
                pass
    if os.path.isdir(fashion_dir):
        for pat in ("fashion_scene_s*.mp4", "final_video_thumb.jpg", "scene_s*_ai_thumb.jpg"):
            for fp in glob.glob(os.path.join(fashion_dir, pat)):
                try:
                    sz = os.path.getsize(fp)
                    os.remove(fp)
                    removed_count += 1
                    removed_bytes += sz
                except OSError:
                    pass

    if also_delete_finals:
        for pat in (f"{pid}_nv*_v*.mp4", f"{pid}-*-final-30s.mp4", f"{pid}_final.mp4", f"{pid}_pov.mp4"):
            for fp in glob.glob(os.path.join(FINAL_VIDEOS_DIR, pat)):
                try:
                    sz = os.path.getsize(fp)
                    os.remove(fp)
                    removed_count += 1
                    removed_bytes += sz
                except OSError:
                    pass
        for tdir in (os.path.join(pdir, "thumbnails"), os.path.join(WORKSPACE, "thumbnails")):
            if os.path.isdir(tdir):
                for fp in glob.glob(os.path.join(tdir, f"{pid}_*_thumb.jpg")):
                    try:
                        sz = os.path.getsize(fp)
                        os.remove(fp)
                        removed_count += 1
                        removed_bytes += sz
                    except OSError:
                        pass

    cooking_mf = os.path.join(pdir, "cooking_manifest.json")
    if os.path.isfile(cooking_mf):
        try:
            mdata = json.load(open(cooking_mf, encoding="utf-8"))
            if also_delete_finals:
                mdata["final_video_path"] = ""
            mdata["status"] = "prepared"
            mdata["status_message"] = "Đã dọn sạch file render cũ. Bấm Tạo Video Final để render lại."
            for cl in (mdata.get("clips") or []):
                cl["storyboard_done"] = False
                cl["video_done"] = False
            with open(cooking_mf, "w", encoding="utf-8") as f:
                json.dump(mdata, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # Reset prompts.json (remove legacy v7/v8 only, preserve v1..v6 and nv3_v*) and write .cleaned_new marker
    prompts_path = os.path.join(pdir, "prompts.json")
    if os.path.exists(prompts_path):
        try:
            pdata = json.load(open(prompts_path, encoding="utf-8"))
            vids = pdata.get("videos", {})
            for extra_k in list(vids.keys()):
                if extra_k in ("v7", "v8"):
                    vids.pop(extra_k, None)
            with open(prompts_path, "w", encoding="utf-8") as f:
                json.dump(pdata, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    marker_path = os.path.join(pdir, ".cleaned_new")
    try:
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        pass

    sync_web_ui(force=True)
    return {
        "ok": True,
        "pid": pid,
        "removed_count": removed_count,
        "removed_mb": round(removed_bytes / (1024 * 1024), 2),
    }


def _parse_ts_value(val, default: float = 0.0) -> float:
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else default
    text = str(val or "").strip()
    if not text:
        return default
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text[:19], fmt).timestamp()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return default


def _compute_mtime_timestamps(paths, fallback_paths=(), extra_ts=(), explicit_created="", explicit_updated="", explicit_updated_ts=0.0):
    candidates = [float(t) for t in extra_ts if t and float(t) > 0]
    for fp in paths:
        if fp and os.path.exists(fp):
            try:
                candidates.append(os.path.getmtime(fp))
            except OSError:
                pass
    if not candidates:
        for fp in fallback_paths:
            if fp and os.path.exists(fp):
                try:
                    candidates.append(os.path.getmtime(fp))
                except OSError:
                    pass
    file_mtime = max(candidates) if candidates else time.time()
    updated_ts = max(float(explicit_updated_ts or 0.0), file_mtime)
    parsed_upd = _parse_ts_value(explicit_updated, 0.0)
    if parsed_upd > updated_ts and explicit_updated_ts:
        updated_ts = parsed_upd
    all_paths = tuple(paths) + tuple(fallback_paths)
    created_candidates = [os.path.getctime(fp) for fp in all_paths if fp and os.path.exists(fp)]
    parsed_crt = _parse_ts_value(explicit_created, 0.0)
    created_ts = parsed_crt if parsed_crt > 0 else (min(created_candidates) if created_candidates else updated_ts)
    return (
        str(explicit_created or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_ts))),
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated_ts)),
        round(created_ts, 3),
        round(updated_ts, 3),
    )


def _extract_sort_ts(item: dict) -> float:
    for key in ("updated_ts", "created_ts"):
        val = item.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    for key in ("updated_at", "created_at"):
        ts = _parse_ts_value(item.get(key), 0.0)
        if ts > 0:
            return ts
    pdir = str(item.get("project_dir") or "").strip()
    if pdir and os.path.exists(pdir):
        try:
            return os.path.getmtime(pdir)
        except OSError:
            pass
    return 0.0


def _unified_sort_group(item: dict) -> int:
    if item.get("is_running"):
        return -2
    done_cnt = int(item.get("done_products") or 0)
    if done_cnt > 0:
        return -1
    failed_cnt = int(item.get("failed_products") or 0)
    step_txt = str(item.get("current_step_text") or (item.get("live_status") or {}).get("current_step_text") or "").lower()
    if failed_cnt > 0 or "lỗi" in step_txt:
        return 2
    if int(item.get("deleted_finals_count") or 0) > 0:
        return 1
    return 0


def _sync_web_ui_locked(force: bool = True):
    global _LAST_SYNC_TS
    _hotpatch_live_modules()
    now_ts = time.time()
    if not force and (now_ts - _LAST_SYNC_TS) < 1.2:
        return
    _LAST_SYNC_TS = now_ts

    os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    pids = list(ALL_PIDS)
    if os.path.isdir(PROJECTS_DIR):
        for entry in sorted(os.listdir(PROJECTS_DIR)):
            if entry.startswith("fashion_"):
                continue
            full_e = os.path.join(PROJECTS_DIR, entry)
            if os.path.isdir(full_e) and entry not in pids:
                pids.append(entry)

    raw_index_items = []

    for order_idx, pid in enumerate(pids):
        pdir = os.path.join(PROJECTS_DIR, pid)
        if not os.path.isdir(pdir):
            continue
        if os.path.isfile(os.path.join(pdir, 'transform.json')):
            from transform_engine import project_view
            try:
                item = project_view(Path(pdir))
                group = -2 if item['is_running'] else (-1 if item['done_products'] else 1)
                raw_index_items.append((group, order_idx, {k: v for k, v in item.items() if k != 'products'}))
            except (ValueError, KeyError, OSError):
                pass
            continue
        if os.path.isfile(os.path.join(pdir, 'cooking_manifest.json')):
            continue  # Dedicated projection preserves storyboard clips and cooking prompts.
        prod_img_dir = os.path.join(pdir, "product_images")
        prompts_path = os.path.join(pdir, "prompts.json")
        info_path = os.path.join(prod_img_dir, "info.json")
        marker_path = os.path.join(pdir, ".cleaned_new")

        info_data = {}
        if os.path.exists(info_path):
            try:
                with open(info_path, encoding="utf-8") as _f_inf:
                    info_data = json.load(_f_inf)
            except Exception:
                pass

        prompts_data = {}
        if os.path.exists(prompts_path):
            try:
                with open(prompts_path, encoding="utf-8") as _f_prm:
                    prompts_data = json.load(_f_prm)
            except Exception:
                pass

        proj_json_path = os.path.join(pdir, "project.json")
        existing_proj_data = {}
        if os.path.isfile(proj_json_path):
            try:
                with open(proj_json_path, encoding="utf-8") as _f_prj:
                    existing_proj_data = json.load(_f_prj)
            except Exception:
                existing_proj_data = {}

        if str(pid).startswith("proj_") and isinstance(existing_proj_data, dict) and existing_proj_data.get("id") and not prompts_data:
            c_prods = existing_proj_data.get("products") or []
            c_done = sum(1 for pr in c_prods if isinstance(pr, dict) and pr.get("status") == "done")
            c_run = sum(1 for pr in c_prods if isinstance(pr, dict) and pr.get("status") in ("scripting", "img_gen", "vid_gen", "assembling"))
            c_fail = sum(1 for pr in c_prods if isinstance(pr, dict) and pr.get("status") == "failed")
            c_prim = next((str(pr.get("product_image_path") or "") for pr in c_prods if isinstance(pr, dict) and pr.get("product_image_path")), "")
            c_sort = -1 if c_run > 0 else (0 if c_done > 0 else 1)
            raw_index_items.append((
                c_sort,
                order_idx,
                {
                    "id": pid,
                    "name": existing_proj_data.get("name") or pid,
                    "primary_product_image_path": c_prim,
                    "final_videos_dir": FINAL_VIDEOS_DIR,
                    "project_dir": pdir,
                    "role_skill_file": existing_proj_data.get("role_skill_file") or "DoAnVat.MD",
                    "created_at": existing_proj_data.get("created_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(proj_json_path))),
                    "updated_at": existing_proj_data.get("updated_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(proj_json_path))),
                    "updated_ts": round(_parse_ts_value(existing_proj_data.get("updated_at"), 0.0) or os.path.getmtime(proj_json_path), 3),
                    "total_products": len(c_prods),
                    "done_products": c_done,
                    "running_products": c_run,
                    "failed_products": c_fail,
                    "thumbnails_count": 0,
                    "deleted_finals_count": 0,
                    "has_rendered_cache": c_done > 0,
                    "rendered_files_count": c_done,
                    "rendered_size_mb": 0,
                    "is_clean_new": len(c_prods) == 0,
                    "is_running": c_run > 0,
                    "progress_pct": int(round((c_done / max(1, len(c_prods))) * 100)) if c_prods else 0,
                    "current_step_text": "",
                    "template_code": "",
                    "template_name": existing_proj_data.get("role_skill_file") or "Custom Studio",
                    "videos_per_character": 1,
                    "is_custom_project": True,
                    "settings": existing_proj_data.get("settings") or {},
                },
            ))
            continue

        if not prompts_data and not info_data and not os.path.isdir(prod_img_dir):
            continue

        pname = (
            prompts_data.get("product_name")
            or info_data.get("name")
            or info_data.get("title")
            or info_data.get("product_name")
            or pid
        )
        price_str = str(info_data.get("price") or info_data.get("price_str") or "")
        shop_str = info_data.get("shop", "")

        cand_jpgs = sorted(glob.glob(os.path.join(prod_img_dir, "prod_*.jpg")))
        primary_rel_list = prompts_data.get("primary_product_refs") or []
        primary_prod_abs = os.path.join(prod_img_dir, primary_rel_list[0]) if primary_rel_list else ""
        if not primary_prod_abs or not os.path.exists(primary_prod_abs):
            primary_prod_abs = cand_jpgs[0] if cand_jpgs else ""

        slide_rel_list = prompts_data.get("slide_overlay_files") or primary_rel_list
        slide_abs_list = [
            os.path.join(prod_img_dir, f)
            for f in slide_rel_list
            if os.path.exists(os.path.join(prod_img_dir, f))
        ]
        if not slide_abs_list and cand_jpgs:
            slide_abs_list = cand_jpgs[:4]
        all_prod_imgs = cand_jpgs

        rendered_files = _list_rendered_intermediate_files(pdir)
        rendered_files_count = len(rendered_files)
        rendered_size_mb = round(sum(os.path.getsize(fp) for fp in rendered_files if os.path.exists(fp)) / (1024 * 1024), 1)
        has_rendered_cache = rendered_files_count > 0

        if has_rendered_cache and os.path.exists(marker_path):
            try:
                os.remove(marker_path)
            except OSError:
                pass
        has_prompts = os.path.exists(prompts_path) and bool(prompts_data.get("videos"))
        is_marked_clean = os.path.exists(marker_path) or (not has_rendered_cache and not has_prompts)
        tpl_code = str(prompts_data.get("template_code") or info_data.get("template_code") or "001")
        tpl_name = str(prompts_data.get("template_name") or info_data.get("template_name") or "Nhà Xưởng")
        vpc_val = int(prompts_data.get("videos_per_character") or 3)

        state_path = os.path.join(pdir, "flow_state.json")
        state_mtime_orig = os.path.getmtime(state_path) if os.path.exists(state_path) else 0.0
        state = {"uploaded_refs": {}, "scene_uuids": {}, "built_finals": []}
        if os.path.exists(state_path):
            try:
                with open(state_path, encoding="utf-8") as _f_st0:
                    state = json.load(_f_st0)
            except Exception:
                pass
        built_finals = set(state.get("built_finals") or [])
        state_dirty = False

        products_entries = []
        videos = prompts_data.get("videos", {})

        base_order = ["v1", "v3", "v5", "v2", "v4", "v6"]
        extra_vkeys = [k for k in videos.keys() if k not in base_order]
        ordered_vkeys = [k for k in base_order if k in videos] + extra_vkeys

        deleted_finals_count = 0

        if not is_marked_clean:
            scene_errors_map = state.get("scene_errors") if isinstance(state.get("scene_errors"), dict) else {}
            failed_scenes_set = set(state.get("failed_scenes") or [])
            for vkey in ordered_vkeys:
                vcfg = videos[vkey]
                char_key = vcfg.get("character", "nv1")
                char_sheet_abs = _resolve_char_sheet_for_sync(char_key, vkey)

                char_v = get_char_v_code(vkey, char_key)
                char_label = vcfg.get("hook_title") or DEFAULT_HOOK_LABELS.get(vkey, char_v.upper())
                style_label = vcfg.get("style", "Xưởng nhà máy dây chuyền uy tín")
                ref_img_rel = vcfg.get("ref_image", f"{vkey}-refimg.jpg")
                ref_img_abs = os.path.join(pdir, ref_img_rel)
                ref_exists = os.path.exists(ref_img_abs) and os.path.getsize(ref_img_abs) > 5000

                thumb_abs = ""
                if _esm is not None:
                    try:
                        thumb_abs = _esm.get_variant_thumbnail_path(pid, char_v)
                    except Exception:
                        thumb_abs = ""
                if not thumb_abs:
                    cand_thumb = os.path.join(pdir, "thumbnails", f"{pid}_{char_v}_thumb.jpg")
                    if os.path.exists(cand_thumb) and os.path.getsize(cand_thumb) > 5000:
                        thumb_abs = cand_thumb
                has_thumb = bool(thumb_abs and os.path.exists(thumb_abs))

                final_filename = get_final_video_filename(pid, vkey, char_key)
                old_final_filename = f"{pid}-{vkey}-final-30s.mp4"
                final_in_dedicated = os.path.join(FINAL_VIDEOS_DIR, final_filename)
                old_in_dedicated = os.path.join(FINAL_VIDEOS_DIR, old_final_filename)
                final_in_pdir = os.path.join(pdir, final_filename)
                old_in_pdir = os.path.join(pdir, old_final_filename)

                # Auto-migrate legacy filename in final_videos/ -> {pid}_{nv1/nv2}_v{1/2/3}.mp4
                if os.path.exists(old_in_dedicated) and os.path.getsize(old_in_dedicated) > 50000:
                    if not os.path.exists(final_in_dedicated):
                        try:
                            shutil.move(old_in_dedicated, final_in_dedicated)
                        except OSError:
                            pass
                    else:
                        try:
                            os.remove(old_in_dedicated)
                        except OSError:
                            pass

                for cand_pdir in (final_in_pdir, old_in_pdir):
                    if os.path.exists(cand_pdir) and os.path.getsize(cand_pdir) > 50000:
                        if vkey not in built_finals or not os.path.exists(final_in_dedicated):
                            try:
                                shutil.copy2(cand_pdir, final_in_dedicated)
                            except Exception:
                                pass
                        try:
                            os.remove(cand_pdir)
                        except OSError:
                            pass

                final_exists = os.path.exists(final_in_dedicated) and os.path.getsize(final_in_dedicated) > 50000
                if final_exists:
                    if vkey not in built_finals:
                        built_finals.add(vkey)
                        state_dirty = True
                else:
                    if vkey in built_finals:
                        deleted_finals_count += 1
                        continue

                ref_err_obj = scene_errors_map.get(f"{vkey}_ref") or scene_errors_map.get(f"ref_{vkey}")
                ref_err_msg = ""
                if not ref_exists and isinstance(ref_err_obj, dict):
                    ref_err_msg = str(ref_err_obj.get("message") or ref_err_obj.get("error") or "").strip()
                elif not ref_exists and isinstance(ref_err_obj, str):
                    ref_err_msg = ref_err_obj.strip()

                scenes_ui = []
                any_scene_done = False
                any_scene_tmp = False
                any_scene_failed = False
                first_variant_err = ref_err_msg
                for idx, sc in enumerate(vcfg.get("scenes", []), start=1):
                    s_file = sc["file"]
                    s_stem = os.path.splitext(s_file)[0]
                    s_abs = os.path.join(pdir, s_file)
                    s_tmp = s_abs + ".720p.tmp"
                    s_done = os.path.exists(s_abs) and os.path.getsize(s_abs) > 50000
                    s_has_tmp = (not s_done) and os.path.exists(s_tmp) and os.path.getsize(s_tmp) > 10000
                    if s_done:
                        any_scene_done = True
                    if s_has_tmp:
                        any_scene_tmp = True

                    s_err_msg = ""
                    s_is_terminal_fail = False
                    if not s_done and not final_exists:
                        raw_sc_err = (
                            scene_errors_map.get(s_stem)
                            or scene_errors_map.get(f"{vkey}_s{idx}")
                            or scene_errors_map.get(s_file)
                        )
                        if isinstance(raw_sc_err, dict):
                            acc_tag = f"[TK:{raw_sc_err.get('account')}] " if raw_sc_err.get("account") else ""
                            s_err_msg = f"{acc_tag}{raw_sc_err.get('message') or raw_sc_err.get('error') or ''}".strip()
                            s_is_terminal_fail = bool(raw_sc_err.get("terminal")) or (s_stem in failed_scenes_set)
                        elif isinstance(raw_sc_err, str) and raw_sc_err.strip():
                            s_err_msg = raw_sc_err.strip()
                            s_is_terminal_fail = (s_stem in failed_scenes_set)
                        elif ref_err_msg and idx == 1:
                            s_err_msg = ref_err_msg
                            s_is_terminal_fail = (f"{vkey}_ref" in failed_scenes_set)

                    if s_is_terminal_fail and not s_done:
                        any_scene_failed = True
                    if s_err_msg and not first_variant_err:
                        first_variant_err = s_err_msg

                    sc_ui_status = (
                        "done"
                        if s_done
                        else ("failed" if s_is_terminal_fail else ("running" if s_has_tmp else "pending"))
                    )
                    scenes_ui.append({
                        "scene_number": idx,
                        "scene_title": f"Phân cảnh {idx} (10s - {sc.get('words', 0)} từ)",
                        "scene_description": f"Omni Flash 10s (9:16) — {char_v.upper()} | Voice: {vcfg.get('voice_name','')}",
                        "image_prompt": vcfg.get("ref_image_prompt", "9:16 Factory / Workshop Reference Image (Nano Banana 2.1)"),
                        "video_prompt": sc.get("prompt", ""),
                        "image_path": ref_img_abs if ref_exists else "",
                        "video_path": s_abs if s_done else (s_tmp if s_has_tmp else ""),
                        "primary_product_image_path": primary_prod_abs,
                        "character_sheet_path": char_sheet_abs if os.path.exists(char_sheet_abs) else "",
                        "status": sc_ui_status,
                        "error_msg": "" if s_done else s_err_msg,
                    })

                if final_exists:
                    p_status = "done"
                elif any_scene_failed:
                    p_status = "failed"
                elif any_scene_done or any_scene_tmp:
                    p_status = "vid_gen"
                elif ref_exists:
                    p_status = "queued"
                elif ref_err_msg and (f"{vkey}_ref" in failed_scenes_set):
                    p_status = "failed"
                else:
                    p_status = "img_gen"
                products_entries.append({
                    "id": f"{pid}_{char_v}",
                    "vkey": vkey,
                    "char_v_code": char_v,
                    "video_filename": final_filename,
                    "product_name": f"{pname} — {char_v.upper()} ({char_label} | {style_label})",
                    "product_info": f"File: {final_filename} | Giá: {price_str} | Bối cảnh: {style_label} | Voice: {vcfg.get('voice_name','')}",
                    "product_image_path": ref_img_abs if ref_exists else "",
                    "thumbnail_path": thumb_abs if has_thumb else "",
                    "has_thumbnail": has_thumb,
                    "primary_product_image_path": primary_prod_abs,
                    "slide_overlay_image_paths": slide_abs_list,
                    "all_product_image_paths": all_prod_imgs,
                    "character_sheet_path": char_sheet_abs if os.path.exists(char_sheet_abs) else "",
                    "role_skill_file": "FlowFinalPipeline.MD",
                    "img_model": "Nano Banana 2.1 (2K)",
                    "vid_model": "Omni Flash (1080p)",
                    "aspect": "9:16",
                    "num_scenes": len(scenes_ui),
                    "seconds_per_scene": 10,
                    "video_resolution": "1080p",
                    "character_id": vcfg.get("character_id", ""),
                    "voice_id": vcfg.get("voice_id", ""),
                    "flow_project_id": vcfg.get("project_id", ""),
                    "output_dir": FINAL_VIDEOS_DIR,
                    "project_dir": pdir,
                    "status": p_status,
                    "error_msg": "" if final_exists else first_variant_err,
                    "final_video_path": final_in_dedicated if final_exists else "",
                    "final_video_mtime": int(os.path.getmtime(final_in_dedicated)) if final_exists else 0,
                    "scenes": scenes_ui,
                    "created_at": now_str,
                })

        if state_dirty and os.path.exists(prompts_path) and not is_marked_clean:
            # Re-read latest flow_state.json right before merge so live scene_uuids/scene_accounts/scene_errors
            # written concurrently by run_all_7_videos_mt.py are NEVER clobbered!
            try:
                latest_state = {}
                if os.path.exists(state_path):
                    with open(state_path, encoding="utf-8") as _f_ls:
                        latest_state = json.load(_f_ls)
                if not isinstance(latest_state, dict):
                    latest_state = dict(state)
                merged_finals = sorted(set(latest_state.get("built_finals") or []) | built_finals)
                latest_state["built_finals"] = merged_finals
                _sync_atomic_write_json(state_path, latest_state)
            except Exception:
                pass

        done_cnt = sum(1 for e in products_entries if e["status"] == "done")
        if done_cnt == 0 and deleted_finals_count > 0:
            # Khi toàn bộ Video Final của sản phẩm này đã bị xoá (sau khi upload),
            # ẩn hết các thẻ variant còn dư để chuyển hẳn sang danh sách "Sản phẩm đã upload hết Video Final"
            products_entries = []
        run_cnt = sum(1 for e in products_entries if e["status"] != "done")
        fail_cnt = sum(1 for e in products_entries if e["status"] == "failed")

        live_prog = {}
        recent_logs = []
        if _esm is not None and (has_rendered_cache or has_prompts):
            try:
                live_prog = _esm.get_project_live_progress(pid)
                recent_logs = live_prog.get("logs", [])
            except Exception:
                pass

        is_pipeline_running = bool(live_prog.get("is_running", False))
        progress_pct = int(live_prog.get("progress_pct", 0))
        thumbs_cnt = sum(1 for e in products_entries if e.get("has_thumbnail"))

        p_created_at, p_updated_at, p_created_ts, p_updated_ts = _compute_mtime_timestamps(
            [prompts_path],
            fallback_paths=[info_path, pdir],
            extra_ts=[state_mtime_orig] + [e.get("final_video_mtime", 0) for e in products_entries],
            explicit_created=existing_proj_data.get("created_at") or "",
            explicit_updated=existing_proj_data.get("updated_at") or "",
            explicit_updated_ts=float(existing_proj_data.get("updated_ts") or 0.0),
        )

        proj_title = f"{pname[:48]} ({pid}) — {price_str}" if price_str else f"{pname[:48]} ({pid})"
        proj_obj = {
            "id": pid,
            "name": proj_title,
            "full_product_name": pname,
            "price": price_str,
            "shop": shop_str,
            "final_videos_dir": FINAL_VIDEOS_DIR,
            "project_dir": pdir,
            "primary_product_image_path": primary_prod_abs,
            "slide_overlay_image_paths": slide_abs_list,
            "all_product_image_paths": all_prod_imgs,
            "role_skill_file": "FlowFinalPipeline.MD",
            "created_at": p_created_at,
            "updated_at": p_updated_at,
            "created_ts": p_created_ts,
            "updated_ts": p_updated_ts,
            "total_products": len(products_entries),
            "done_products": done_cnt,
            "running_products": run_cnt,
            "failed_products": fail_cnt,
            "thumbnails_count": thumbs_cnt,
            "deleted_finals_count": deleted_finals_count,
            "has_rendered_cache": has_rendered_cache,
            "rendered_files_count": rendered_files_count,
            "rendered_size_mb": rendered_size_mb,
            "is_clean_new": (done_cnt == 0 and is_marked_clean),
            "is_running": is_pipeline_running,
            "progress_pct": progress_pct,
            "live_status": live_prog,
            "logs": recent_logs,
            "template_code": tpl_code,
            "template_name": tpl_name,
            "videos_per_character": vpc_val,
            "settings": {
                "role_skill_file": "FlowFinalPipeline.MD",
                "img_model": "Nano Banana 2.1 (2K)",
                "vid_model": "Omni Flash (1080p)",
                "aspect": "9:16",
                "num_scenes": 3,
                "seconds_per_scene": 10,
                "video_resolution": "1080p",
                "max_workers": 3,
            },
            "products": products_entries,
        }

        # Chỉ hiển thị trong Studio Dự Án những project thực sự đã khởi tạo kịch bản/video/cache hoặc đang chạy.
        # Sản phẩm thô mới crawl (chưa có prompts.json, chưa có video/cache) chỉ nằm ở tab Sản Phẩm.
        is_created_studio_project = bool(
            has_prompts
            or has_rendered_cache
            or done_cnt > 0
            or deleted_finals_count > 0
            or is_pipeline_running
        )
        if not is_created_studio_project:
            continue

        _sync_atomic_write_json(os.path.join(pdir, "project.json"), proj_obj)

        # Group -1 = Đang chạy trực tiếp (TOP-MOST), Group 0 = Còn Video Final (TOP), Group 1 = Hết Video Final (BOTTOM)
        sort_group = -1 if is_pipeline_running else (0 if done_cnt > 0 else 1)
        raw_index_items.append((
            sort_group,
            order_idx,
            {
                "id": pid,
                "name": proj_title,
                "primary_product_image_path": primary_prod_abs,
                "final_videos_dir": FINAL_VIDEOS_DIR,
                "project_dir": pdir,
                "role_skill_file": "FlowFinalPipeline.MD",
                "created_at": p_created_at,
                "updated_at": p_updated_at,
                "created_ts": p_created_ts,
                "updated_ts": p_updated_ts,
                "total_products": len(products_entries),
                "done_products": done_cnt,
                "running_products": run_cnt,
                "failed_products": fail_cnt,
                "thumbnails_count": thumbs_cnt,
                "deleted_finals_count": deleted_finals_count,
                "has_rendered_cache": has_rendered_cache,
                "rendered_files_count": rendered_files_count,
                "rendered_size_mb": rendered_size_mb,
                "is_clean_new": (done_cnt == 0 and is_marked_clean),
                "is_running": is_pipeline_running,
                "progress_pct": progress_pct,
                "current_step_text": live_prog.get("current_step_text", ""),
                "template_code": tpl_code,
                "template_name": tpl_name,
                "videos_per_character": vpc_val,
                "settings": proj_obj["settings"],
            }
        ))

    # Đồng bộ thêm các dự án Video Thời Trang (fashion_motion_projects/*) đã có Video Final hoặc đang chạy vào Tổng Hợp (Studio Dự Án & Matrix)
    fashion_root = os.path.join(WORKSPACE, "fashion_motion_projects")
    if os.path.isdir(fashion_root):
        fashion_json_files = glob.glob(os.path.join(fashion_root, "*", "fashion_project.json"))
        fashion_json_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        overall_sheet_default = os.path.join(WORKSPACE, "ảnh mẫu thumbnail", "Tron_Bo_7_Anh_2K", "01_Character_Sheet_4_Outfits_2K.png")
        for f_idx, fjson_path in enumerate(fashion_json_files):
            try:
                with open(fjson_path, encoding="utf-8") as _f_fp:
                    fproj = json.load(_f_fp)
            except Exception:
                continue
            fpid = str(fproj.get("project_id") or os.path.basename(os.path.dirname(fjson_path))).strip()
            if not fpid:
                continue
            fdir = os.path.dirname(fjson_path)
            f_status = str(fproj.get("status") or "")
            f_scenes = fproj.get("scenes") or []
            active_sc_states = ("preparing", "submitting", "submitted_720p", "upsampling_1080p", "rendering_720p", "rendering_1080p", "retrying_auto", "running")
            is_f_running = (f_status in ("running_flow", "preparing", "retrying_auto")) or any(
                str(sc.get("status") or "") in active_sc_states for sc in f_scenes
            )
            any_sc_failed = (f_status in ("failed_scenes", "failed_auth", "failed_upload", "failed_input_preparation")) or any(
                str(sc.get("status") or "").startswith("failed") for sc in f_scenes
            )
            final_vid_path = fproj.get("final_video_path") or os.path.join(FINAL_VIDEOS_DIR, f"{fpid}_final.mp4")
            if not os.path.exists(final_vid_path):
                alt_final = os.path.join(FINAL_VIDEOS_DIR, f"{fpid}_final_1080p_60fps.mp4")
                if os.path.exists(alt_final):
                    final_vid_path = alt_final
            final_exists = os.path.exists(final_vid_path) and os.path.getsize(final_vid_path) > 50000

            any_sc_done = any(
                os.path.exists(sc.get("output_video_path") or "") and os.path.getsize(sc.get("output_video_path") or "") > 50000
                for sc in f_scenes
            )
            # Đưa vào Studio Dự Án tất cả dự án Thời Trang đang chạy, đang xử lý dở, lỗi cảnh hoặc đã có Video Final
            if not (final_exists or any_sc_done or is_f_running or any_sc_failed):
                continue

            base_char_abs = (fproj.get("base_char_2k") or {}).get("path") or ""
            room_char_abs = (fproj.get("char_sheet_2k") or {}).get("path") or base_char_abs
            overall_abs = overall_sheet_default if os.path.exists(overall_sheet_default) else room_char_abs
            outfit_paths = [
                o.get("path") for o in (fproj.get("outfits") or [])
                if o.get("path") and os.path.exists(o.get("path"))
            ]
            use_custom_assets = bool(fproj.get("disable_overall_sheet") or outfit_paths)
            primary_prod_f = (outfit_paths[0] if (use_custom_assets and outfit_paths) else (base_char_abs or overall_abs))
            all_prod_f = (
                [p for p in ([base_char_abs] + outfit_paths) if p][:8]
                if use_custom_assets
                else [p for p in ([overall_abs, room_char_abs] + outfit_paths) if p][:8]
            )
            raw_fvt_code = str(fproj.get("source_template_code") or "").strip()
            tpl_code_f = "004"
            tpl_name_f = "Motion Control Video Fashion"
            ftitle = str(fproj.get("title") or fpid).strip()
            proj_title_f = f"👗 {ftitle}" if not ftitle.startswith("👗") else ftitle

            scenes_ui_f = []
            sc_weight_sum = 0.0
            f_logs = []
            if fproj.get("status_message"):
                f_logs.append(f"[{fproj.get('updated_at') or now_str}] {fproj.get('status_message')}")
            for sc_i, sc in enumerate(f_scenes, start=1):
                sc_vid = sc.get("output_video_path") or os.path.join(fdir, sc.get("output_video_file") or f"fashion_scene_s{sc_i}_1080p.mp4")
                sc_done = os.path.exists(sc_vid) and os.path.getsize(sc_vid) > 50000
                sc_st_raw = str(sc.get("status") or "")
                if sc_done or sc_st_raw == "completed_1080p":
                    sc_weight_sum += 1.0
                elif sc_st_raw in ("submitted_720p", "upsampling_1080p", "rendering_1080p"):
                    sc_weight_sum += 0.72
                elif sc_st_raw in ("submitting", "rendering_720p", "retrying_auto"):
                    sc_weight_sum += 0.45
                elif sc_st_raw in ("preparing", "running"):
                    sc_weight_sum += 0.22
                sc_thumb = sc.get("start_frame_path") or sc.get("keyframe_sheet_path") or sc.get("ref_clip_thumb") or room_char_abs
                start_s = float(sc.get("start_sec", (sc_i - 1) * 8) or 0)
                end_s = float(sc.get("end_sec", sc_i * 8) or (sc_i * 8))
                dur_s = round(max(1.0, end_s - start_s), 1)
                summary_vn = sc.get("ai_motion_summary_vn") or f"Phân cảnh {sc_i} ({start_s:g}s–{end_s:g}s): Chuyển động & biến hình trang phục theo nhạc"
                sc_detail = sc.get("status_detail") or sc.get("last_error") or ""
                if sc_detail:
                    f_logs.append(f"• Cảnh {sc_i} ({sc_st_raw or 'pending'}): {sc_detail}")
                scenes_ui_f.append({
                    "scene_number": sc_i,
                    "scene_title": f"Phân cảnh {sc_i} ({start_s:g}s – {end_s:g}s)",
                    "scene_description": f"{ f'[{sc_detail}] ' if (sc_detail and not sc_done) else '' }{summary_vn}",
                    "dialogue_vn": f"{ f'[{sc_detail}] ' if (sc_detail and not sc_done) else '' }{summary_vn}",
                    "duration_sec": int(dur_s) if dur_s.is_integer() else dur_s,
                    "image_prompt": "2K Character Sheet + Outfit Product Sheets + Room Reference 2K",
                    "video_prompt": sc.get("prompt") or sc.get("prompt_timeline_pro") or "",
                    "image_path": sc_thumb if (sc_thumb and os.path.exists(sc_thumb)) else room_char_abs,
                    "video_path": sc_vid if sc_done else "",
                    "primary_product_image_path": primary_prod_f,
                    "character_sheet_path": base_char_abs,
                    "status": "done" if sc_done else ("failed" if sc_st_raw.startswith("failed") else ("running" if (is_f_running or sc_st_raw in active_sc_states) else "pending")),
                    "error_msg": sc.get("last_error") or "",
                })

            mirror_pdir = os.path.join(PROJECTS_DIR, fpid)
            os.makedirs(mirror_pdir, exist_ok=True)

            f_products = []
            final_thumb_jpg = os.path.join(fdir, "final_video_thumb.jpg")
            if final_exists and (not os.path.exists(final_thumb_jpg) or os.path.getmtime(final_thumb_jpg) < os.path.getmtime(final_vid_path)):
                try:
                    import subprocess as _sp
                    _sp.run(
                        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", "2.6", "-i", final_vid_path, "-frames:v", "1", "-q:v", "2", final_thumb_jpg],
                        capture_output=True,
                        timeout=10,
                    )
                except Exception:
                    pass

            thumb_candidates_f = [
                os.path.join(WORKSPACE, "thumbnails", f"{fpid}_nv1_v1_thumb.jpg"),
                os.path.join(WORKSPACE, "thumbnails", f"{fpid}_v1_thumb.jpg"),
                os.path.join(mirror_pdir, "thumbnails", f"{fpid}_nv1_v1_thumb.jpg"),
                os.path.join(mirror_pdir, "thumbnails", f"{fpid}_v1_thumb.jpg"),
                os.path.join(fdir, "thumbnails", f"{fpid}_nv1_v1_thumb.jpg"),
                final_thumb_jpg,
            ]
            use_final_thumb = next(
                (tp for tp in thumb_candidates_f if tp and os.path.isfile(tp) and os.path.getsize(tp) > 3000),
                "",
            )
            has_thumb_f = bool(use_final_thumb and os.path.isfile(use_final_thumb))
            hook_sub = f"{raw_fvt_code} • " if (raw_fvt_code and raw_fvt_code not in ("#004", "004")) else ""
            total_dur_s = int(sum(float(s.get("duration_sec") or 8) for s in scenes_ui_f)) or (len(scenes_ui_f) * 8)

            # Chuẩn Basic Studio: 1 Card = 1 Video Final (các phân cảnh 8s nằm trong cột bên phải của Card)
            f_products.append({
                "id": f"{fpid}_nv1_v1",
                "vkey": "v1",
                "char_v_code": "nv1_v1",
                "video_filename": os.path.basename(final_vid_path) if final_exists else f"{fpid}_final.mp4",
                "product_name": f"{ftitle} — Kịch bản 1: {hook_sub}Biến Hình {len(scenes_ui_f)} Cảnh ({total_dur_s}s)",
                "product_info": f"File: {os.path.basename(final_vid_path)} | Mẫu: #004 {raw_fvt_code} | Ghép {len(scenes_ui_f)} cảnh + Nhạc gốc",
                "product_image_path": room_char_abs,
                "thumbnail_path": use_final_thumb,
                "has_thumbnail": has_thumb_f,
                "primary_product_image_path": primary_prod_f,
                "slide_overlay_image_paths": outfit_paths[:5],
                "all_product_image_paths": all_prod_f,
                "character_sheet_path": base_char_abs,
                "role_skill_file": "FlowFinalPipeline.MD",
                "img_model": "Nano Banana 2.1 (2K)",
                "vid_model": "Omni 1.1 Flash (abra_edit 1080p)",
                "aspect": "9:16",
                "num_scenes": len(scenes_ui_f),
                "seconds_per_scene": 8,
                "video_resolution": "1080p",
                "character_id": "nv5_fashion",
                "voice_id": "",
                "flow_project_id": fproj.get("flow_project_id") or "",
                "output_dir": FINAL_VIDEOS_DIR,
                "project_dir": fdir,
                "status": "done" if final_exists else ("failed" if any_sc_failed else ("vid_gen" if (is_f_running or any_sc_done) else "queued")),
                "error_msg": fproj.get("status_message") if any_sc_failed else "",
                "final_video_path": final_vid_path if final_exists else "",
                "final_video_mtime": int(os.path.getmtime(final_vid_path)) if final_exists else 0,
                "scenes": scenes_ui_f,
                "created_at": fproj.get("created_at") or now_str,
            })

            f_done_cnt = sum(1 for e in f_products if e["status"] == "done" and e.get("final_video_path"))
            f_run_cnt = sum(1 for e in f_products if e["status"] != "done")
            f_done_scenes = sum(1 for s in scenes_ui_f if s["status"] == "done")
            f_done_refs = int(bool(room_char_abs and os.path.exists(room_char_abs)))
            f_done_thumbs = int(has_thumb_f)
            f_total_steps = max(1, 1 + len(scenes_ui_f) + 1)
            f_pct = 100 if final_exists else (
                max(
                    12 if is_f_running else 0,
                    min(96, int(round(((f_done_refs + max(float(f_done_scenes), sc_weight_sum)) / f_total_steps) * 100))),
                )
                if (any_sc_done or sc_weight_sum > 0 or f_done_refs)
                else (15 if is_f_running else 0)
            )

            f_inter_files = []
            for pat in ("fashion_scene_s*.mp4", "*.png", "final_video_thumb.jpg", "scene_s*_ai_thumb.jpg"):
                for fp in glob.glob(os.path.join(fdir, pat)):
                    if os.path.isfile(fp) and fp not in f_inter_files:
                        f_inter_files.append(fp)
            f_rendered_mb = round(sum(os.path.getsize(fp) for fp in f_inter_files) / (1024 * 1024), 1)
            f_step_msg = fproj.get("status_message") or ""

            f_proj_obj = {
                "id": fpid,
                "name": proj_title_f,
                "full_product_name": ftitle,
                "price": raw_fvt_code if (raw_fvt_code and raw_fvt_code != "#004") else "",
                "shop": "Video Thời Trang (#004)",
                "final_videos_dir": FINAL_VIDEOS_DIR,
                "project_dir": fdir,
                "primary_product_image_path": primary_prod_f,
                "slide_overlay_image_paths": outfit_paths[:5],
                "all_product_image_paths": all_prod_f,
                "role_skill_file": "FlowFinalPipeline.MD",
                "created_at": fproj.get("created_at") or now_str,
                "updated_at": fproj.get("updated_at") or now_str,
                "total_products": len(f_products),
                "done_products": f_done_cnt,
                "running_products": f_run_cnt,
                "failed_products": 1 if any_sc_failed else 0,
                "thumbnails_count": f_done_thumbs,
                "deleted_finals_count": 0,
                "has_rendered_cache": bool(len(f_inter_files) > 0),
                "rendered_files_count": len(f_inter_files),
                "rendered_size_mb": f_rendered_mb,
                "is_clean_new": not bool(len(f_inter_files) > 0),
                "is_running": is_f_running,
                "progress_pct": f_pct,
                "live_status": {
                    "is_running": is_f_running,
                    "progress_pct": f_pct,
                    "done_refs": f_done_refs,
                    "done_scenes": f_done_scenes,
                    "total_scenes": len(scenes_ui_f),
                    "done_thumbnails": f_done_thumbs,
                    "done_finals": f_done_cnt,
                    "total_variants": len(f_products),
                    "current_step": f_step_msg,
                    "current_step_text": f_step_msg,
                },
                "logs": f_logs if f_logs else ([f_step_msg] if f_step_msg else []),
                "template_code": tpl_code_f,
                "template_name": tpl_name_f,
                "videos_per_character": 1,
                "is_fashion_motion_project": True,
                "settings": {
                    "role_skill_file": "FlowFinalPipeline.MD",
                    "img_model": "Nano Banana 2.1 (2K)",
                    "vid_model": "Omni 1.1 Flash (1080p)",
                    "aspect": "9:16",
                    "num_scenes": len(f_scenes),
                    "seconds_per_scene": 8,
                    "video_resolution": "1080p",
                    "max_workers": 2,
                },
                "products": f_products,
            }
            _sync_atomic_write_json(os.path.join(mirror_pdir, "project.json"), f_proj_obj)

            # Đặt sort_group = -2 (nếu đang chạy) hoặc -1 (nếu đã có Video Final Thời Trang) để luôn nổi lên ĐẦU danh sách Tổng Hợp!
            f_sort_group = -2 if is_f_running else (-1 if f_done_cnt > 0 else 1)
            raw_index_items.append((
                f_sort_group,
                f_idx,
                {
                    "id": fpid,
                    "name": proj_title_f,
                    "price": f_proj_obj["price"],
                    "primary_product_image_path": primary_prod_f,
                    "final_videos_dir": FINAL_VIDEOS_DIR,
                    "project_dir": fdir,
                    "role_skill_file": "FlowFinalPipeline.MD",
                    "created_at": fproj.get("created_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(fjson_path))),
                    "updated_at": fproj.get("updated_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(fjson_path))),
                    "updated_ts": float(fproj.get("updated_ts") or os.path.getmtime(fjson_path)),
                    "total_products": len(f_products),
                    "done_products": f_done_cnt,
                    "running_products": f_run_cnt,
                    "failed_products": 1 if any_sc_failed else 0,
                    "thumbnails_count": f_done_thumbs,
                    "deleted_finals_count": 0,
                    "has_rendered_cache": f_proj_obj["has_rendered_cache"],
                    "rendered_files_count": f_proj_obj["rendered_files_count"],
                    "rendered_size_mb": f_proj_obj["rendered_size_mb"],
                    "is_clean_new": f_proj_obj["is_clean_new"],
                    "is_running": is_f_running,
                    "progress_pct": f_pct,
                    "current_step_text": f_step_msg,
                    "template_code": tpl_code_f,
                    "template_name": tpl_name_f,
                    "videos_per_character": 1,
                    "is_fashion_motion_project": True,
                    "settings": f_proj_obj["settings"],
                }
            ))

    from cooking_studio_projection import sync_projects as sync_cooking_projects
    for cooking_idx, cooking_item in enumerate(sync_cooking_projects(PROJECTS_DIR)):
        c_sort_group = -2 if cooking_item.get("is_running") else (-1 if cooking_item.get("done_products") else 1)
        raw_index_items.append((c_sort_group, -100 + cooking_idx, cooking_item))

    # Sort uniformly across all templates: Running -> Has Final Video -> Pending/Queued -> Uploaded Empty -> Errored,
    # always ordering NEWEST projects FIRST within every section.
    index_list = [item[2] for item in raw_index_items]
    index_list.sort(key=lambda it: (_unified_sort_group(it), -_extract_sort_ts(it), str(it.get("id") or "")))

    index_path = os.path.join(PROJECTS_DIR, "projects_index.json")
    _sync_atomic_write_json(index_path, index_list)


def sync_web_ui(force: bool = True):
    with _SYNC_LOCK:
        _sync_web_ui_locked(force=force)


def _sync_atomic_write_json(path: str, payload: object, retries: int = 7) -> bool:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    except Exception:
        pass
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        with open(tmp, "w", encoding="utf-8") as fw:
            fw.write(text)
        for attempt in range(max(1, int(retries))):
            try:
                os.replace(tmp, path)
                return True
            except OSError:
                time.sleep(0.02 * (attempt + 1))
        with open(path, "w", encoding="utf-8") as fw2:
            fw2.write(text)
        return True
    except Exception:
        return False
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _resolve_char_sheet_for_sync(char_key: str, vkey: str) -> str:
    try:
        import character_library_manager as _clm
        if hasattr(_clm, "resolve_character_sheet_path"):
            eff_ck = char_key
            if not eff_ck:
                vk_l = (vkey or "").lower()
                if vk_l.startswith("nv") and "_" in vk_l:
                    eff_ck = vk_l.split("_", 1)[0]
                elif vk_l in ("v2", "v4", "v6", "v8", "v10"):
                    eff_ck = "nv2"
                else:
                    eff_ck = "nv1"
            resolved = _clm.resolve_character_sheet_path(eff_ck, fallback_assets_dir=CHARS_DIR)
            if resolved and os.path.isfile(resolved):
                return resolved
    except Exception:
        pass
    ck_low = (char_key or "").lower()
    vk_low = (vkey or "").lower()
    for n_idx in range(9, 0, -1):
        tag = f"nv{n_idx}"
        if tag in ck_low or vk_low.startswith(f"{tag}_"):
            for ext in (".jpg", ".png", ".jpeg", ".webp"):
                cand = os.path.join(CHARS_DIR, f"{tag}_ref{ext}")
                if os.path.isfile(cand):
                    return cand
    if vk_low in ("v2", "v4", "v6", "v8", "v10"):
        return os.path.join(CHARS_DIR, "nv2_ref.png")
    return os.path.join(CHARS_DIR, "nv1_ref.jpg")


if __name__ == "__main__":
    sync_web_ui(force=True)
    print("[SYNC] Updated projects_index.json and synced with final_videos/ folder!")
