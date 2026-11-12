# -*- coding: utf-8 -*-
import os
import re
import sys
import glob
import json
import time
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
                state = json.load(open(state_path, encoding="utf-8"))
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


def sync_web_ui(force: bool = True):
    global _LAST_SYNC_TS
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
        if os.path.isfile(os.path.join(pdir, 'cooking_manifest.json')):
            continue  # Dedicated projection preserves storyboard clips and cooking prompts.
        prod_img_dir = os.path.join(pdir, "product_images")
        prompts_path = os.path.join(pdir, "prompts.json")
        info_path = os.path.join(prod_img_dir, "info.json")
        marker_path = os.path.join(pdir, ".cleaned_new")

        info_data = {}
        if os.path.exists(info_path):
            try:
                info_data = json.load(open(info_path, encoding="utf-8"))
            except Exception:
                pass

        prompts_data = {}
        if os.path.exists(prompts_path):
            try:
                prompts_data = json.load(open(prompts_path, encoding="utf-8"))
            except Exception:
                pass

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
        state = {"uploaded_refs": {}, "scene_uuids": {}, "built_finals": []}
        if os.path.exists(state_path):
            try:
                state = json.load(open(state_path, encoding="utf-8"))
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
            for vkey in ordered_vkeys:
                vcfg = videos[vkey]
                char_key = vcfg.get("character", "nv1")
                ck_low = (char_key or "").lower()
                if "nv3" in ck_low or vkey.lower().startswith("nv3"):
                    char_sheet_abs = os.path.join(CHARS_DIR, "nv3_ref.jpg")
                elif "nv2" in ck_low or vkey.lower() in ("v2", "v4", "v6", "v8", "v10") or vkey.lower().startswith("nv2"):
                    char_sheet_abs = os.path.join(CHARS_DIR, "nv2_ref.png")
                else:
                    char_sheet_abs = os.path.join(CHARS_DIR, "nv1_ref.jpg")

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

                scenes_ui = []
                any_scene_done = False
                any_scene_tmp = False
                for idx, sc in enumerate(vcfg.get("scenes", []), start=1):
                    s_file = sc["file"]
                    s_abs = os.path.join(pdir, s_file)
                    s_tmp = s_abs + ".720p.tmp"
                    s_done = os.path.exists(s_abs) and os.path.getsize(s_abs) > 50000
                    s_has_tmp = (not s_done) and os.path.exists(s_tmp) and os.path.getsize(s_tmp) > 10000
                    if s_done:
                        any_scene_done = True
                    if s_has_tmp:
                        any_scene_tmp = True
                    scenes_ui.append({
                        "scene_number": idx,
                        "scene_title": f"Phân cảnh {idx} (10s - {sc['words']} từ)",
                        "scene_description": f"Omni Flash 10s (9:16) — {char_v.upper()} | Voice: {vcfg.get('voice_name','')}",
                        "image_prompt": vcfg.get("ref_image_prompt", "9:16 Factory / Workshop Reference Image (Nano Banana 2.1)"),
                        "video_prompt": sc["prompt"],
                        "image_path": ref_img_abs if ref_exists else "",
                        "video_path": s_abs if s_done else (s_tmp if s_has_tmp else ""),
                        "primary_product_image_path": primary_prod_abs,
                        "character_sheet_path": char_sheet_abs if os.path.exists(char_sheet_abs) else "",
                        "status": "done" if s_done else ("running" if s_has_tmp else "pending"),
                        "error_msg": "",
                    })

                p_status = "done" if final_exists else ("vid_gen" if (any_scene_done or any_scene_tmp) else ("queued" if ref_exists else "img_gen"))
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
                    "error_msg": "",
                    "final_video_path": final_in_dedicated if final_exists else "",
                    "final_video_mtime": int(os.path.getmtime(final_in_dedicated)) if final_exists else 0,
                    "scenes": scenes_ui,
                    "created_at": now_str,
                })

        if state_dirty and os.path.exists(prompts_path) and not is_marked_clean:
            state["built_finals"] = sorted(list(built_finals))
            try:
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
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
            "created_at": now_str,
            "updated_at": now_str,
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
        with open(os.path.join(pdir, "project.json"), "w", encoding="utf-8") as f:
            json.dump(proj_obj, f, ensure_ascii=False, indent=2)

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
                "created_at": now_str,
                "updated_at": now_str,
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
                fproj = json.load(open(fjson_path, encoding="utf-8"))
            except Exception:
                continue
            fpid = str(fproj.get("project_id") or os.path.basename(os.path.dirname(fjson_path))).strip()
            if not fpid:
                continue
            fdir = os.path.dirname(fjson_path)
            f_status = str(fproj.get("status") or "")
            is_f_running = (f_status == "running_flow")
            final_vid_path = fproj.get("final_video_path") or os.path.join(FINAL_VIDEOS_DIR, f"{fpid}_final.mp4")
            if not os.path.exists(final_vid_path):
                alt_final = os.path.join(FINAL_VIDEOS_DIR, f"{fpid}_final_1080p_60fps.mp4")
                if os.path.exists(alt_final):
                    final_vid_path = alt_final
            final_exists = os.path.exists(final_vid_path) and os.path.getsize(final_vid_path) > 50000

            f_scenes = fproj.get("scenes") or []
            any_sc_done = any(
                os.path.exists(sc.get("output_video_path") or "") and os.path.getsize(sc.get("output_video_path") or "") > 50000
                for sc in f_scenes
            )
            # Chỉ đưa vào Tổng Hợp những dự án Thời Trang đang chạy, đã có cảnh render hoặc đã có Video Final
            if not (final_exists or any_sc_done or is_f_running):
                continue

            base_char_abs = (fproj.get("base_char_2k") or {}).get("path") or ""
            room_char_abs = (fproj.get("char_sheet_2k") or {}).get("path") or base_char_abs
            overall_abs = overall_sheet_default if os.path.exists(overall_sheet_default) else room_char_abs
            outfit_paths = [
                o.get("path") for o in (fproj.get("outfits") or [])
                if o.get("path") and os.path.exists(o.get("path"))
            ]
            raw_fvt_code = str(fproj.get("source_template_code") or "").strip()
            tpl_code_f = "004"
            tpl_name_f = "Motion Control Video Fashion"
            ftitle = str(fproj.get("title") or fpid).strip()
            proj_title_f = f"👗 {ftitle}" if not ftitle.startswith("👗") else ftitle

            scenes_ui_f = []
            for sc_i, sc in enumerate(f_scenes, start=1):
                sc_vid = sc.get("output_video_path") or os.path.join(fdir, sc.get("output_video_file") or f"fashion_scene_s{sc_i}_1080p.mp4")
                sc_done = os.path.exists(sc_vid) and os.path.getsize(sc_vid) > 50000
                sc_thumb = sc.get("keyframe_sheet_path") or sc.get("ref_clip_thumb") or room_char_abs
                start_s = float(sc.get("start_sec", (sc_i - 1) * 8) or 0)
                end_s = float(sc.get("end_sec", sc_i * 8) or (sc_i * 8))
                dur_s = round(max(1.0, end_s - start_s), 1)
                summary_vn = sc.get("ai_motion_summary_vn") or f"Phân cảnh {sc_i} ({start_s:g}s–{end_s:g}s): Chuyển động & biến hình trang phục theo nhạc"
                scenes_ui_f.append({
                    "scene_number": sc_i,
                    "scene_title": f"Phân cảnh {sc_i} ({start_s:g}s – {end_s:g}s)",
                    "scene_description": summary_vn,
                    "dialogue_vn": summary_vn,
                    "duration_sec": int(dur_s) if dur_s.is_integer() else dur_s,
                    "image_prompt": "2K Character Sheet + Outfit Product Sheets + Room Reference 2K",
                    "video_prompt": sc.get("prompt") or sc.get("prompt_timeline_pro") or "",
                    "image_path": sc_thumb if (sc_thumb and os.path.exists(sc_thumb)) else room_char_abs,
                    "video_path": sc_vid if sc_done else "",
                    "primary_product_image_path": overall_abs,
                    "character_sheet_path": base_char_abs,
                    "status": "done" if sc_done else ("running" if is_f_running else "pending"),
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
                "primary_product_image_path": overall_abs,
                "slide_overlay_image_paths": outfit_paths[:5],
                "all_product_image_paths": [p for p in ([overall_abs, room_char_abs] + outfit_paths) if p][:8],
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
                "status": "done" if final_exists else ("vid_gen" if (is_f_running or any_sc_done) else "queued"),
                "error_msg": "",
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
                min(95, int(round(((f_done_refs + f_done_scenes) / f_total_steps) * 100)))
                if (any_sc_done or f_done_refs)
                else (20 if is_f_running else 0)
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
                "primary_product_image_path": overall_abs,
                "slide_overlay_image_paths": outfit_paths[:5],
                "all_product_image_paths": [p for p in ([overall_abs, room_char_abs] + outfit_paths) if p][:8],
                "role_skill_file": "FlowFinalPipeline.MD",
                "created_at": fproj.get("created_at") or now_str,
                "updated_at": fproj.get("updated_at") or now_str,
                "total_products": len(f_products),
                "done_products": f_done_cnt,
                "running_products": f_run_cnt,
                "failed_products": 0,
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
                "logs": [f_step_msg] if f_step_msg else [],
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
            with open(os.path.join(mirror_pdir, "project.json"), "w", encoding="utf-8") as f_out:
                json.dump(f_proj_obj, f_out, ensure_ascii=False, indent=2)

            # Đặt sort_group = -2 (nếu đang chạy) hoặc -1 (nếu đã có Video Final Thời Trang) để luôn nổi lên ĐẦU danh sách Tổng Hợp!
            f_sort_group = -2 if is_f_running else (-1 if f_done_cnt > 0 else 1)
            raw_index_items.append((
                f_sort_group,
                f_idx,
                {
                    "id": fpid,
                    "name": proj_title_f,
                    "price": f_proj_obj["price"],
                    "primary_product_image_path": overall_abs,
                    "final_videos_dir": FINAL_VIDEOS_DIR,
                    "project_dir": fdir,
                    "role_skill_file": "FlowFinalPipeline.MD",
                    "created_at": fproj.get("created_at") or now_str,
                    "updated_at": fproj.get("updated_at") or now_str,
                    "total_products": len(f_products),
                    "done_products": f_done_cnt,
                    "running_products": f_run_cnt,
                    "failed_products": 0,
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
        raw_index_items.append((-1 if cooking_item['done_products'] else 1, -100 + cooking_idx, cooking_item))

    # Products with Final Videos (>0) stay at the TOP; products with 0 Final Videos move to the BOTTOM!
    raw_index_items.sort(key=lambda x: (x[0], x[1]))
    index_list = [item[2] for item in raw_index_items]

    with open(os.path.join(PROJECTS_DIR, "projects_index.json"), "w", encoding="utf-8") as f:
        json.dump(index_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sync_web_ui(force=True)
    print("[SYNC] Updated projects_index.json and synced with final_videos/ folder!")
