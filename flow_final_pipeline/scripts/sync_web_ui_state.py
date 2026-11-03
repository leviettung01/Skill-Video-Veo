# -*- coding: utf-8 -*-
import os
import sys
import glob
import json
import time
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    if vk.startswith("nv1_") or vk.startswith("nv2_"):
        return vk
    ck = "nv2" if "nv2" in (char_key or "").lower() else "nv1"
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
        "flow_state.json",
        "flow_refs_state.json",
        "spec_v7.json",
        "spec_v8.json",
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
    elif vkey and "_" in vkey and not vkey.lower().startswith("nv"):
        vkey = vkey.split("_")[-1].lower()

    char_v = get_char_v_code(vkey)
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

    for cpath in candidates:
        if cpath and os.path.isfile(cpath):
            try:
                os.remove(cpath)
                deleted_files.append(cpath)
            except OSError:
                pass

    if os.path.isdir(pdir) and vkey:
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
    if not os.path.isdir(pdir):
        return {"ok": False, "error": f"Không tìm thấy thư mục sản phẩm: {pid}"}

    removed_count = 0
    removed_bytes = 0
    for fp in _list_rendered_intermediate_files(pdir):
        try:
            sz = os.path.getsize(fp)
            os.remove(fp)
            removed_count += 1
            removed_bytes += sz
        except OSError:
            pass

    if also_delete_finals:
        for pat in (f"{pid}_nv*_v*.mp4", f"{pid}-*-final-30s.mp4"):
            for fp in glob.glob(os.path.join(FINAL_VIDEOS_DIR, pat)):
                try:
                    sz = os.path.getsize(fp)
                    os.remove(fp)
                    removed_count += 1
                    removed_bytes += sz
                except OSError:
                    pass

    # Reset prompts.json to clean 6 variants (remove legacy v7/v8) and write .cleaned_new marker
    prompts_path = os.path.join(pdir, "prompts.json")
    if os.path.exists(prompts_path):
        try:
            pdata = json.load(open(prompts_path, encoding="utf-8"))
            vids = pdata.get("videos", {})
            for extra_k in list(vids.keys()):
                if extra_k not in ("v1", "v2", "v3", "v4", "v5", "v6"):
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
            full_e = os.path.join(PROJECTS_DIR, entry)
            if os.path.isdir(full_e) and entry not in pids:
                pids.append(entry)

    raw_index_items = []

    for order_idx, pid in enumerate(pids):
        pdir = os.path.join(PROJECTS_DIR, pid)
        if not os.path.isdir(pdir):
            continue
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
        is_marked_clean = os.path.exists(marker_path) or not has_rendered_cache

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
                is_nv1 = "nv1" in char_key.lower()
                char_sheet_abs = os.path.join(CHARS_DIR, "nv1_ref.jpg" if is_nv1 else "nv2_ref.png")

                char_v = get_char_v_code(vkey, char_key)
                char_label = vcfg.get("hook_title") or DEFAULT_HOOK_LABELS.get(vkey, char_v.upper())
                style_label = vcfg.get("style", "Xưởng nhà máy dây chuyền uy tín")
                ref_img_rel = vcfg.get("ref_image", f"{vkey}-refimg.jpg")
                ref_img_abs = os.path.join(pdir, ref_img_rel)
                ref_exists = os.path.exists(ref_img_abs) and os.path.getsize(ref_img_abs) > 5000

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
                for idx, sc in enumerate(vcfg.get("scenes", []), start=1):
                    s_file = sc["file"]
                    s_abs = os.path.join(pdir, s_file)
                    s_done = os.path.exists(s_abs) and os.path.getsize(s_abs) > 50000
                    if s_done:
                        any_scene_done = True
                    scenes_ui.append({
                        "scene_number": idx,
                        "scene_title": f"Phân cảnh {idx} (10s - {sc['words']} từ)",
                        "scene_description": f"Omni Flash 10s (9:16) — {char_v.upper()} | Voice: {vcfg.get('voice_name','')}",
                        "image_prompt": vcfg.get("ref_image_prompt", "9:16 Factory / Workshop Reference Image (Nano Banana 2.1)"),
                        "video_prompt": sc["prompt"],
                        "image_path": ref_img_abs if ref_exists else "",
                        "video_path": s_abs if s_done else "",
                        "primary_product_image_path": primary_prod_abs,
                        "character_sheet_path": char_sheet_abs if os.path.exists(char_sheet_abs) else "",
                        "status": "done" if s_done else "pending",
                        "error_msg": "",
                    })

                p_status = "done" if final_exists else ("vid_gen" if any_scene_done else ("queued" if ref_exists else "img_gen"))
                products_entries.append({
                    "id": f"{pid}_{char_v}",
                    "vkey": vkey,
                    "char_v_code": char_v,
                    "video_filename": final_filename,
                    "product_name": f"{pname} — {char_v.upper()} ({char_label} | {style_label})",
                    "product_info": f"File: {final_filename} | Giá: {price_str} | Bối cảnh: {style_label} | Voice: {vcfg.get('voice_name','')}",
                    "product_image_path": ref_img_abs if ref_exists else "",
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
            "deleted_finals_count": deleted_finals_count,
            "has_rendered_cache": has_rendered_cache,
            "rendered_files_count": rendered_files_count,
            "rendered_size_mb": rendered_size_mb,
            "is_clean_new": (done_cnt == 0 and not has_rendered_cache),
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

        raw_index_items.append((
            0 if done_cnt > 0 else 1,  # Group 0 = Còn Video Final (TOP), Group 1 = Hết Video Final (BOTTOM)
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
                "deleted_finals_count": deleted_finals_count,
                "has_rendered_cache": has_rendered_cache,
                "rendered_files_count": rendered_files_count,
                "rendered_size_mb": rendered_size_mb,
                "is_clean_new": (done_cnt == 0 and not has_rendered_cache),
                "settings": proj_obj["settings"],
            }
        ))

    # Products with Final Videos (>0) stay at the TOP; products with 0 Final Videos move to the BOTTOM!
    raw_index_items.sort(key=lambda x: (x[0], x[1]))
    index_list = [item[2] for item in raw_index_items]

    with open(os.path.join(PROJECTS_DIR, "projects_index.json"), "w", encoding="utf-8") as f:
        json.dump(index_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sync_web_ui(force=True)
    print("[SYNC] Updated projects_index.json and synced with final_videos/ folder!")
