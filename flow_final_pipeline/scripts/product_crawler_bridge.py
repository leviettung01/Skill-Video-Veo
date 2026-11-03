# -*- coding: utf-8 -*-
"""
Bridge tích hợp trực tiếp bộ Crawler Sản Phẩm & Giải Captcha BoxPhone (`tiktok_crawler/`)
đóng gói độc lập (100% Standalone) bên trong thư mục `Skill Video Veo`:
  - Hỗ trợ nhận Link sản phẩm TikTok (vt.tiktok.com, shop.tiktok.com, tiktok.com/@.../video/...) hoặc ID sản phẩm (15-22 chữ số).
  - Kiểm tra nếu sản phẩm đã có sẵn trong `projects/<pid>/product_images/` hoặc trong `data/tiktok_crawler/` thì đồng bộ sang ngay.
  - Nếu chưa có (hoặc yêu cầu crawl lại), tự động chạy:
      + Cách 1 (`spaiauto` / `auto`): SPAI Auto API -> tự động fallback sang Cách 2 nếu lỗi.
      + Cách 2 (`browser`): Chrome TikTokShop (`data/tiktok_crawler/tiktok_shop/profiles/tiktok_chrome_profile`)
        + Giải Captcha tự động (`tiktok_crawler/boxphone_captcha/weights/08102026_detect.torchscript`).
  - Tự động tải toàn bộ ảnh sản phẩm về `projects/<pid>/product_images/`, chuyển đổi sang `prod_1.jpg`..`prod_N.jpg`,
    lưu `info.json`, sinh `prompts.json` + `spec_*.json` theo Template được chọn (mặc định: `Template/Nhà Xưởng`),
    và có thể kích hoạt chạy đa luồng `run_all_7_videos_mt.py <pid>` ngay lập tức.
"""
import os
import re
import sys
import glob
import json
import time
import shutil
import argparse
import subprocess
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
WS_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
FINAL_VIDEOS_DIR = os.path.join(WS_DIR, "final_videos")

TIKTOK_CRAWLER_RUNTIME_DIR = os.path.join(WS_DIR, "data", "tiktok_crawler")
TIKTOK_CRAWLER_DATA_DIR = os.path.join(TIKTOK_CRAWLER_RUNTIME_DIR, "data")
TIKTOK_CRAWLER_PROD_IMGS_DIR = os.path.join(TIKTOK_CRAWLER_DATA_DIR, "product_images")
TIKTOK_CRAWLER_HOT_PRODS_DIR = os.path.join(TIKTOK_CRAWLER_DATA_DIR, "hot_products")
TIKTOK_CRAWLER_RESEARCH_JSON = os.path.join(TIKTOK_CRAWLER_DATA_DIR, "tiktok-product-research.json")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
if WS_DIR not in sys.path:
    sys.path.insert(0, WS_DIR)

try:
    from tiktok_crawler import config as tt_config
    from tiktok_crawler import research as tt_research
except Exception as e:
    tt_config = None
    tt_research = None
    print(f"[WARN] Could not import standalone tiktok_crawler package: {e}", flush=True)

from template_manager import generate_prompts_for_product, list_video_templates
from sync_web_ui_state import sync_web_ui


def extract_or_resolve_pid(raw_input: str) -> tuple:
    """
    Trích xuất Product ID (15-22 số) từ ID hoặc Link TikTok bất kỳ.
    Trả về (pid, resolved_url, error_str).
    """
    text = (raw_input or "").strip()
    if not text:
        return ("", "", "Chưa nhập Link hoặc ID sản phẩm")

    # 1. Nếu là chuỗi số 15-22 chữ số và không phải link rút gọn
    m_direct = re.search(r"(?<!\d)(\d{15,22})(?!\d)", text)
    if m_direct and ("vt.tiktok.com" not in text and "vm.tiktok.com" not in text):
        pid = m_direct.group(1)
        return (pid, f"https://shop.tiktok.com/vn/pdp/{pid}", None)

    # 2. Dùng resolver của tiktok_crawler
    if tt_research is not None:
        try:
            pid = tt_research.extract_product_id(text)
            if pid:
                return (pid, f"https://shop.tiktok.com/vn/pdp/{pid}", None)
            resolved = tt_research.resolve_tiktok_share(text)
            pid = resolved.get("product_id") or ""
            if pid:
                return (pid, resolved.get("url") or f"https://shop.tiktok.com/vn/pdp/{pid}", None)
        except Exception as e:
            return ("", "", f"Lỗi giải mã link TikTok: {e}")

    if m_direct:
        pid = m_direct.group(1)
        return (pid, f"https://shop.tiktok.com/vn/pdp/{pid}", None)

    return ("", "", f"Không tìm thấy ID sản phẩm hợp lệ từ: {text[:100]}")


def _convert_and_normalize_images_in_dir(prod_img_dir: str) -> list:
    """
    Đảm bảo các ảnh trong `projects/<pid>/product_images/` đều có bản `prod_1.jpg`..`prod_N.jpg` chuẩn RGB.
    Hỗ trợ cả ảnh dạng `prod_1.webp`, `img_0.webp`, `thumb.webp`, v.v.
    Trả về danh sách tên file `['prod_1.jpg', ...]`.
    """
    os.makedirs(prod_img_dir, exist_ok=True)

    candidates = []
    for fn in os.listdir(prod_img_dir):
        fl = fn.lower()
        if fl.endswith((".jpg", ".jpeg", ".png", ".webp")) and not fl.endswith(".upload_tmp.jpg"):
            candidates.append(fn)

    def _sort_key(fname):
        fl = fname.lower()
        m_prod = re.search(r"prod_(\d+)", fl)
        if m_prod:
            return (0, int(m_prod.group(1)), fname)
        m_img = re.search(r"img_(\d+)", fl)
        if m_img:
            return (1, int(m_img.group(1)) + 1, fname)
        if fl.startswith("thumb."):
            return (2, 1, fname)
        return (3, 999, fname)

    candidates.sort(key=_sort_key)

    converted_jpgs = []
    idx_counter = 1
    seen_indices = set()

    for fn in candidates:
        fl = fn.lower()
        m_prod = re.search(r"prod_(\d+)", fl)
        m_img = re.search(r"img_(\d+)", fl)
        if m_prod:
            idx = int(m_prod.group(1))
        elif m_img:
            idx = int(m_img.group(1)) + 1
        else:
            idx = None

        if idx is None or idx in seen_indices:
            if fl.startswith("thumb.") and 1 in seen_indices:
                continue
            while idx_counter in seen_indices:
                idx_counter += 1
            idx = idx_counter
        seen_indices.add(idx)

        src_path = os.path.join(prod_img_dir, fn)
        dst_name = f"prod_{idx}.jpg"
        dst_path = os.path.join(prod_img_dir, dst_name)

        if os.path.abspath(src_path).lower() == os.path.abspath(dst_path).lower():
            if os.path.getsize(dst_path) > 2000:
                converted_jpgs.append((idx, dst_name))
            continue

        if not os.path.exists(dst_path) or os.path.getsize(dst_path) < 2000:
            try:
                with Image.open(src_path) as im:
                    im_rgb = im.convert("RGB")
                    im_rgb.save(dst_path, format="JPEG", quality=93)
            except Exception:
                pass

        if os.path.exists(dst_path) and os.path.getsize(dst_path) > 2000:
            converted_jpgs.append((idx, dst_name))

    converted_jpgs.sort(key=lambda x: x[0])
    result = []
    for _, dname in converted_jpgs:
        if dname not in result:
            result.append(dname)
    return result


def sync_product_from_tiktok_web_cache(pid: str) -> bool:
    """
    Kiểm tra xem `data/tiktok_crawler` đã có ảnh/thông tin của `pid` chưa.
    Nếu có thì copy sang `projects/<pid>/product_images/` và tạo `prod_1.jpg`..`prod_N.jpg` + `info.json`.
    """
    pdir = os.path.join(PROJECTS_DIR, pid)
    prod_img_dir = os.path.join(pdir, "product_images")
    os.makedirs(prod_img_dir, exist_ok=True)

    src_dirs = [
        os.path.join(TIKTOK_CRAWLER_PROD_IMGS_DIR, pid, "images"),
        os.path.join(TIKTOK_CRAWLER_PROD_IMGS_DIR, pid),
        os.path.join(TIKTOK_CRAWLER_HOT_PRODS_DIR, pid, "images"),
        os.path.join(TIKTOK_CRAWLER_HOT_PRODS_DIR, pid),
    ]
    for sdir in src_dirs:
        if os.path.isdir(sdir):
            for fn in sorted(os.listdir(sdir)):
                fl = fn.lower()
                if fl.endswith((".webp", ".jpg", ".jpeg", ".png")) or fn == "info.json":
                    s_fp = os.path.join(sdir, fn)
                    d_fp = os.path.join(prod_img_dir, fn)
                    if os.path.isfile(s_fp) and (not os.path.exists(d_fp) or os.path.getsize(d_fp) < 500):
                        try:
                            shutil.copy2(s_fp, d_fp)
                        except Exception:
                            pass

    research_item = None
    if os.path.exists(TIKTOK_CRAWLER_RESEARCH_JSON):
        try:
            rdata = json.load(open(TIKTOK_CRAWLER_RESEARCH_JSON, "r", encoding="utf-8"))
            for p in rdata.get("products", []):
                p_id = str(p.get("product_id") or p.get("id") or "").strip()
                if p_id == str(pid):
                    research_item = p
                    break
        except Exception:
            pass

    info_path = os.path.join(prod_img_dir, "info.json")
    info_data = {}
    if os.path.exists(info_path):
        try:
            info_data = json.load(open(info_path, "r", encoding="utf-8"))
        except Exception:
            pass

    if research_item:
        if not info_data.get("name") and research_item.get("title"):
            info_data["name"] = research_item["title"]
        if not info_data.get("title") and research_item.get("title"):
            info_data["title"] = research_item["title"]
        if not info_data.get("price") and research_item.get("price"):
            info_data["price"] = research_item["price"]
        if not info_data.get("original_price") and research_item.get("original_price"):
            info_data["original_price"] = research_item["original_price"]
        if not info_data.get("sold_count") and (research_item.get("sold_count") or research_item.get("sold_total")):
            info_data["sold_count"] = research_item.get("sold_count") or research_item.get("sold_total")
        if not info_data.get("sold_count_label") and research_item.get("sold_total_label"):
            info_data["sold_count_label"] = research_item["sold_total_label"]
        if not info_data.get("shop") and (research_item.get("shop_name") or research_item.get("seller")):
            info_data["shop"] = research_item.get("shop_name") or research_item.get("seller")
        if not info_data.get("description") and research_item.get("description"):
            info_data["description"] = research_item["description"]
        if not info_data.get("variations") and research_item.get("variations"):
            info_data["variations"] = research_item["variations"]
        if not info_data.get("images") and research_item.get("images"):
            info_data["images"] = research_item["images"]
        if not info_data.get("desc_images") and research_item.get("desc_images"):
            info_data["desc_images"] = research_item["desc_images"]
        info_data["product_id"] = pid
        info_data["web_url"] = research_item.get("pdp_url") or research_item.get("web_url") or f"https://shop.tiktok.com/vn/pdp/{pid}"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)

    jpgs = _convert_and_normalize_images_in_dir(prod_img_dir)
    # Nếu trong research_item đã có danh sách URL ảnh remote mà chưa tải về đĩa, tự động tải về luôn
    if not jpgs and research_item and research_item.get("images"):
        try:
            import urllib.request
            crawler_prod_dir = os.path.join(TIKTOK_CRAWLER_PROD_IMGS_DIR, pid)
            crawler_imgs_sub = os.path.join(crawler_prod_dir, "images")
            os.makedirs(crawler_imgs_sub, exist_ok=True)
            headers_dl = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36", "Referer": "https://www.tiktok.com/"}
            for idx, img_url in enumerate(research_item.get("images", [])[:12]):
                w_fp = os.path.join(crawler_imgs_sub, f"img_{idx}.webp")
                if not os.path.exists(w_fp) or os.path.getsize(w_fp) < 200:
                    req = urllib.request.Request(img_url, headers=headers_dl)
                    with urllib.request.urlopen(req, timeout=10) as r_dl:
                        b_dl = r_dl.read()
                        if len(b_dl) > 200:
                            with open(w_fp, "wb") as wf:
                                wf.write(b_dl)
                            if idx == 0:
                                with open(os.path.join(crawler_prod_dir, "thumb.webp"), "wb") as tf:
                                    tf.write(b_dl)
                if os.path.exists(w_fp) and os.path.getsize(w_fp) > 200:
                    shutil.copy2(w_fp, os.path.join(prod_img_dir, f"img_{idx}.webp"))
            with open(os.path.join(crawler_prod_dir, "info.json"), "w", encoding="utf-8") as cf:
                json.dump(info_data, cf, ensure_ascii=False, indent=2)
            jpgs = _convert_and_normalize_images_in_dir(prod_img_dir)
        except Exception:
            pass

    return len(jpgs) > 0 and bool(info_data.get("name") or info_data.get("title"))


def ensure_product_crawled(
    raw_id_or_url: str,
    method: str = "auto",
    force_crawl: bool = False,
) -> dict:
    """
    Đảm bảo sản phẩm đã có đủ thông tin (`info.json`) và bộ ảnh (`prod_1.jpg`..`prod_N.jpg`)
    trong `projects/<pid>/product_images/`.
    Nếu chưa có sẵn trong thư mục dự án hoặc cache, tự động crawl qua:
      - `method="auto"`: Cách 1 (SPAI Auto API) -> tự động fallback Cách 2 Browser nếu lỗi.
      - `method="spaiauto"`: Chỉ chạy Cách 1 (SPAI Auto API).
      - `method="browser"`: Cách 2 (Trình duyệt Chrome TikTokShop + Captcha BoxPhone).
    """
    pid, resolved_url, err = extract_or_resolve_pid(raw_id_or_url)
    if not pid:
        return {"ok": False, "error": err or "Không xác định được ID sản phẩm"}

    pdir = os.path.join(PROJECTS_DIR, pid)
    prod_img_dir = os.path.join(pdir, "product_images")
    os.makedirs(prod_img_dir, exist_ok=True)
    info_path = os.path.join(prod_img_dir, "info.json")

    if not force_crawl:
        existing_jpgs = _convert_and_normalize_images_in_dir(prod_img_dir)
        info_data = {}
        for cand_info in (os.path.join(prod_img_dir, "info.json"), os.path.join(pdir, "info.json")):
            if os.path.exists(cand_info):
                try:
                    with open(cand_info, "r", encoding="utf-8") as f:
                        info_data = json.load(f)
                    if info_data:
                        break
                except Exception:
                    pass
        if existing_jpgs and (info_data.get("name") or info_data.get("title")):
            return {
                "ok": True,
                "pid": pid,
                "source": "local_project",
                "product_dir": pdir,
                "info": info_data,
                "images": existing_jpgs,
            }

        if sync_product_from_tiktok_web_cache(pid):
            existing_jpgs = _convert_and_normalize_images_in_dir(prod_img_dir)
            info_data = json.load(open(info_path, "r", encoding="utf-8")) if os.path.exists(info_path) else {}
            return {
                "ok": True,
                "pid": pid,
                "source": "tiktok_crawler_cache",
                "product_dir": pdir,
                "info": info_data,
                "images": existing_jpgs,
            }

    if tt_research is None:
        return {"ok": False, "pid": pid, "error": "Không tìm thấy module tiktok_crawler.research"}

    mode = (method or "auto").strip().lower()
    if mode == "browser":
        crawl_res = tt_research.fetch_product_details_browser(pid, download_images=True)
    elif mode == "spaiauto":
        crawl_res = tt_research.fetch_product_details_spaiauto(pid, download_images=True, allow_browser_fallback=False)
    else:
        crawl_res = tt_research.fetch_product_details_spaiauto(pid, download_images=True, allow_browser_fallback=True)

    if crawl_res.get("success"):
        try:
            store = tt_research.ResearchStore()
            store.add_or_update({
                "id": pid,
                "title": crawl_res.get("title") or "",
                "shop_name": crawl_res.get("shop_name") or "",
                "price": crawl_res.get("price") or 0,
                "original_price": crawl_res.get("original_price") or 0,
                "sold_total": crawl_res.get("sold_count") or 0,
                "sold_total_label": crawl_res.get("sold_count_label") or "",
                "description": crawl_res.get("description") or "",
                "images": crawl_res.get("images") or [],
                "desc_images": crawl_res.get("desc_images") or [],
                "variations": crawl_res.get("variations") or [],
                "image_url": crawl_res.get("image_url") or "",
                "local_thumb": crawl_res.get("local_thumb") or "",
                "pdp_url": crawl_res.get("pdp_url") or resolved_url,
                "share_url": resolved_url,
                "has_details": True,
            })
        except Exception:
            pass

    sync_product_from_tiktok_web_cache(pid)
    jpgs = _convert_and_normalize_images_in_dir(prod_img_dir)

    info_data = {}
    if os.path.exists(info_path):
        try:
            info_data = json.load(open(info_path, "r", encoding="utf-8"))
        except Exception:
            pass

    if crawl_res.get("success"):
        info_data.update({
            "product_id": pid,
            "name": crawl_res.get("title") or info_data.get("name") or "",
            "title": crawl_res.get("title") or info_data.get("title") or "",
            "shop": crawl_res.get("shop_name") or info_data.get("shop") or "",
            "price": crawl_res.get("price") or info_data.get("price") or "",
            "original_price": crawl_res.get("original_price") or info_data.get("original_price") or "",
            "sold_count": crawl_res.get("sold_count") or info_data.get("sold_count") or "",
            "sold_count_label": crawl_res.get("sold_count_label") or info_data.get("sold_count_label") or "",
            "description": crawl_res.get("description") or info_data.get("description") or "",
            "variations": crawl_res.get("variations") or info_data.get("variations") or [],
            "images": crawl_res.get("images") or info_data.get("images") or [],
            "desc_images": crawl_res.get("desc_images") or info_data.get("desc_images") or [],
            "source": crawl_res.get("source") or mode,
            "web_url": crawl_res.get("pdp_url") or resolved_url,
        })
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)

    if not jpgs and not crawl_res.get("success"):
        return {
            "ok": False,
            "pid": pid,
            "error": crawl_res.get("error") or "Không tải được ảnh và thông tin sản phẩm",
            "crawl_result": crawl_res,
        }

    return {
        "ok": True,
        "pid": pid,
        "source": crawl_res.get("source") or mode,
        "product_dir": pdir,
        "info": info_data,
        "images": jpgs,
        "crawl_result": crawl_res,
    }


def list_all_products_store() -> dict:
    """
    Trả về danh sách hợp nhất toàn bộ sản phẩm từ:
      1. Thư mục `projects/<pid>` của Skill Video Veo
      2. Database `data/tiktok_crawler/data/tiktok-product-research.json`
    kèm theo trạng thái ảnh, thông tin giá/lượt bán/shop, phân loại SKU, mô tả, thư mục local, số lượng video Final, và danh sách Template.
    """
    research_map = {}
    if os.path.exists(TIKTOK_CRAWLER_RESEARCH_JSON):
        try:
            rdata = json.load(open(TIKTOK_CRAWLER_RESEARCH_JSON, "r", encoding="utf-8"))
            for p in rdata.get("products", []):
                pid = str(p.get("product_id") or p.get("id") or "").strip()
                if pid:
                    research_map[pid] = p
        except Exception:
            pass

    project_pids = []
    if os.path.isdir(PROJECTS_DIR):
        for entry in sorted(os.listdir(PROJECTS_DIR)):
            full_e = os.path.join(PROJECTS_DIR, entry)
            if os.path.isdir(full_e) and re.match(r"^\d{10,25}$", entry):
                project_pids.append(entry)

    all_pids = []
    for pid in project_pids + list(research_map.keys()):
        if pid not in all_pids:
            all_pids.append(pid)

    items = []
    for pid in all_pids:
        pdir = os.path.join(PROJECTS_DIR, pid)
        prod_img_dir = os.path.join(pdir, "product_images")
        crawler_prod_dir = os.path.join(TIKTOK_CRAWLER_PROD_IMGS_DIR, pid)
        info_path = os.path.join(prod_img_dir, "info.json")
        prompts_path = os.path.join(pdir, "prompts.json")

        info_data = {}
        for cand_info in (
            os.path.join(prod_img_dir, "info.json"),
            os.path.join(pdir, "info.json"),
            os.path.join(crawler_prod_dir, "info.json"),
        ):
            if os.path.exists(cand_info):
                try:
                    with open(cand_info, "r", encoding="utf-8") as f:
                        info_data = json.load(f)
                    if info_data:
                        break
                except Exception:
                    pass

        prompts_data = {}
        if os.path.exists(prompts_path):
            try:
                prompts_data = json.load(open(prompts_path, "r", encoding="utf-8"))
            except Exception:
                pass

        r_item = research_map.get(pid, {})

        local_imgs = []
        if os.path.isdir(prod_img_dir):
            local_imgs = [
                os.path.join(prod_img_dir, fn)
                for fn in sorted(os.listdir(prod_img_dir))
                if fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and not fn.lower().endswith(".upload_tmp.jpg")
            ]
            only_prod_jpgs = [p for p in local_imgs if re.match(r"^prod_\d+\.jpg$", os.path.basename(p).lower())]
            if only_prod_jpgs:
                only_prod_jpgs.sort(key=lambda p: int(re.findall(r"prod_(\d+)", os.path.basename(p).lower())[0]))
                local_imgs = only_prod_jpgs

        if not local_imgs:
            for cand_dir in (
                os.path.join(TIKTOK_CRAWLER_PROD_IMGS_DIR, pid, "images"),
                os.path.join(TIKTOK_CRAWLER_PROD_IMGS_DIR, pid),
            ):
                if os.path.isdir(cand_dir):
                    found = [
                        os.path.join(cand_dir, fn)
                        for fn in sorted(os.listdir(cand_dir))
                        if fn.lower().endswith((".webp", ".jpg", ".jpeg", ".png"))
                    ]
                    if found:
                        local_imgs = found
                        break

        title = (
            prompts_data.get("product_name")
            or info_data.get("name")
            or info_data.get("title")
            or r_item.get("title")
            or ""
        )
        price = str(info_data.get("price") or r_item.get("price") or "")
        original_price = str(info_data.get("original_price") or r_item.get("original_price") or "")
        sold_count = str(info_data.get("sold_count") or r_item.get("sold_count") or r_item.get("sold_total") or "")
        sold_count_label = str(info_data.get("sold_count_label") or r_item.get("sold_total_label") or "")
        seller = str(info_data.get("shop") or info_data.get("shop_name") or r_item.get("shop_name") or r_item.get("seller") or "")
        description = str(info_data.get("description") or r_item.get("description") or "")
        variations = info_data.get("variations") or r_item.get("variations") or []
        remote_images = info_data.get("images") or r_item.get("images") or []
        desc_images = info_data.get("desc_images") or info_data.get("description_images") or r_item.get("desc_images") or []
        category = str(info_data.get("category") or r_item.get("category") or "Chưa phân loại")
        status_label = str(r_item.get("status_label") or ("Đã tải đầy đủ thông tin" if local_imgs else "Chưa tải chi tiết"))
        ratio_label = str(r_item.get("ratio_label") or "—")
        is_hot = bool(r_item.get("is_hot") or info_data.get("is_hot") or False)
        crawl_source = str(info_data.get("source") or r_item.get("source") or "")

        final_videos = []
        if os.path.isdir(FINAL_VIDEOS_DIR):
            for fp in sorted(glob.glob(os.path.join(FINAL_VIDEOS_DIR, f"{pid}_*.mp4"))):
                if os.path.isfile(fp) and os.path.getsize(fp) > 50000:
                    final_videos.append(fp)

        primary_refs = prompts_data.get("primary_product_refs") or []
        primary_img_path = ""
        if primary_refs and os.path.exists(os.path.join(prod_img_dir, primary_refs[0])):
            primary_img_path = os.path.join(prod_img_dir, primary_refs[0])
        elif local_imgs:
            primary_img_path = local_imgs[0]

        has_details = bool(title and not title.startswith("Sản phẩm #") and len(local_imgs) > 0)
        status = "ready" if has_details else "pending"

        active_folder = pdir if os.path.isdir(pdir) else (crawler_prod_dir if os.path.isdir(crawler_prod_dir) else "")
        folder_files = []
        if os.path.isdir(crawler_prod_dir):
            if os.path.isdir(os.path.join(crawler_prod_dir, "images")):
                folder_files.append({"type": "dir", "name": "images", "size_label": ""})
            for fn_chk in ("info.json", "thumb.webp"):
                fp_chk = os.path.join(crawler_prod_dir, fn_chk)
                if os.path.isfile(fp_chk):
                    kb = max(1, int(round(os.path.getsize(fp_chk) / 1024)))
                    folder_files.append({"type": "file", "name": fn_chk, "size_label": f"{kb} KB"})
        if os.path.isdir(pdir):
            if os.path.isdir(prod_img_dir):
                folder_files.append({"type": "dir", "name": f"product_images ({len(local_imgs)} ảnh)", "size_label": ""})
            if os.path.isfile(prompts_path):
                kb_p = max(1, int(round(os.path.getsize(prompts_path) / 1024)))
                folder_files.append({"type": "file", "name": "prompts.json", "size_label": f"{kb_p} KB"})

        # Tính toán timestamp & nhãn ngày/giờ hiển thị theo phong cách bảng Sản phẩm Tiềm năng
        raw_ct = r_item.get("created_at") or info_data.get("created_at") or info_data.get("crawled_at") or 0
        created_ts = 0.0
        if isinstance(raw_ct, (int, float)) and raw_ct > 1000000000:
            created_ts = float(raw_ct) / 1000.0 if raw_ct > 1e12 else float(raw_ct)
        elif isinstance(raw_ct, str) and raw_ct.strip():
            try:
                created_ts = float(raw_ct.strip())
                if created_ts > 1e12:
                    created_ts /= 1000.0
            except Exception:
                pass
        if created_ts <= 0:
            for cand_p in (prompts_path, info_path, os.path.join(crawler_prod_dir, "info.json"), pdir, crawler_prod_dir):
                if cand_p and os.path.exists(cand_p):
                    try:
                        created_ts = float(os.path.getmtime(cand_p))
                        break
                    except Exception:
                        pass
        if created_ts <= 0:
            created_ts = time.time()

        import datetime as _dt
        dt_obj = _dt.datetime.fromtimestamp(created_ts)
        today_date = _dt.datetime.now().date()
        prod_date = dt_obj.date()
        date_key = prod_date.strftime("%Y-%m-%d")
        time_label = dt_obj.strftime("%H:%M")
        if prod_date == today_date:
            date_label = "Hôm nay"
        elif prod_date == (today_date - _dt.timedelta(days=1)):
            date_label = "Hôm qua"
        else:
            date_label = f"Ngày {prod_date.day:02d} tháng {prod_date.month:02d}, {prod_date.year}"

        items.append({
            "product_id": pid,
            "title": title,
            "price": price,
            "original_price": original_price,
            "sold_count": sold_count,
            "sold_count_label": sold_count_label,
            "seller": seller,
            "description": description,
            "variations": variations,
            "remote_images": remote_images,
            "desc_images": desc_images,
            "category": category,
            "status_label": status_label,
            "ratio_label": ratio_label,
            "is_hot": is_hot,
            "crawl_source": crawl_source,
            "web_url": info_data.get("web_url") or r_item.get("pdp_url") or r_item.get("web_url") or f"https://shop.tiktok.com/vn/pdp/{pid}",
            "status": status,
            "image_count": len(local_imgs),
            "local_images": local_imgs,
            "primary_image_path": primary_img_path,
            "primary_product_refs": primary_refs,
            "slide_overlay_files": prompts_data.get("slide_overlay_files") or [],
            "template_code": prompts_data.get("template_code") or "001",
            "template_name": prompts_data.get("template_name") or "Nhà Xưởng",
            "videos_per_character": prompts_data.get("videos_per_character") or 3,
            "has_project": os.path.isdir(pdir) and os.path.exists(prompts_path),
            "final_videos_count": len(final_videos),
            "final_videos": final_videos,
            "project_dir": pdir if os.path.isdir(pdir) else "",
            "crawler_dir": crawler_prod_dir if os.path.isdir(crawler_prod_dir) else active_folder,
            "folder_files": folder_files,
            "created_at": created_ts,
            "created_ts": created_ts,
            "date_key": date_key,
            "date_label": date_label,
            "time_label": time_label,
        })

    items.sort(key=lambda x: (-float(x.get("created_ts") or 0), 0 if x["final_videos_count"] > 0 else 1))
    return {
        "ok": True,
        "total": len(items),
        "products": items,
        "templates": list_video_templates(),
    }


def prepare_and_optionally_run_product(
    raw_id_or_url: str,
    template_name: str = "Nhà Xưởng",
    crawl_method: str = "auto",
    videos_per_character: int = None,
    primary_product_refs: list = None,
    slide_overlay_files: list = None,
    force_regenerate_prompts: bool = False,
    auto_run_pipeline: bool = False,
) -> dict:
    """
    Hàm All-in-One:
      1. Nhận Link hoặc ID sản phẩm -> Kiểm tra local / cache hoặc tự động Crawl về `projects/<pid>/product_images/`.
      2. Sinh `prompts.json` + `spec_*.json` từ `Template/<template_name>`.
      3. Đồng bộ trạng thái lên Web UI (`sync_web_ui(force=True)`).
      4. Nếu `auto_run_pipeline=True`, khởi chạy tiến trình đa luồng `run_all_7_videos_mt.py <pid>`.
    """
    crawl_info = ensure_product_crawled(raw_id_or_url, method=crawl_method, force_crawl=False)
    if not crawl_info.get("ok"):
        return crawl_info

    pid = crawl_info["pid"]
    marker_clean = os.path.join(PROJECTS_DIR, pid, ".cleaned_new")
    if os.path.exists(marker_clean):
        try:
            os.remove(marker_clean)
        except OSError:
            pass
    prompts_obj = generate_prompts_for_product(
        pid=pid,
        template_name=template_name,
        videos_per_character=videos_per_character,
        primary_product_refs=primary_product_refs,
        slide_overlay_files=slide_overlay_files,
        force_regenerate=force_regenerate_prompts,
    )
    sync_web_ui(force=True)

    proc_pid = None
    if auto_run_pipeline:
        runner_script = os.path.join(SCRIPTS_DIR, "run_all_7_videos_mt.py")
        log_file = os.path.join(PROJECTS_DIR, pid, "pipeline_run.log")
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n=== AUTO START PIPELINE ({time.strftime('%Y-%m-%d %H:%M:%S')}) | Template: {template_name} ===\n")
            p = subprocess.Popen(
                [sys.executable, "-u", runner_script, pid],
                cwd=WS_DIR,
                stdout=lf,
                stderr=subprocess.STDOUT,
            )
            proc_pid = p.pid

    return {
        "ok": True,
        "pid": pid,
        "product_name": prompts_obj.get("product_name", ""),
        "template_code": prompts_obj.get("template_code", "001"),
        "template_name": prompts_obj.get("template_name", template_name),
        "videos_count": len(prompts_obj.get("videos", {})),
        "images_count": len(crawl_info.get("images", [])),
        "source": crawl_info.get("source", ""),
        "pipeline_started": bool(auto_run_pipeline),
        "pipeline_pid": proc_pid,
    }


def main():
    parser = argparse.ArgumentParser(description="Crawl sản phẩm TikTok & Tạo dự án Video theo Mã Template (001, 002, 003...)")
    parser.add_argument("input", help="Link sản phẩm TikTok hoặc ID sản phẩm")
    parser.add_argument("--template", default="001", help="Mã số độc nhất (001, 002, 003) hoặc Tên thư mục Template trong Template/ (mặc định: 001 - Nhà Xưởng)")
    parser.add_argument("--method", default="auto", choices=["auto", "spaiauto", "browser"], help="Cách crawl nếu chưa có sẵn")
    parser.add_argument("--videos-per-char", type=int, default=None, help="Số lượng video trên mỗi nhân vật (1..5)")
    parser.add_argument("--force-prompts", action="store_true", help="Tạo lại prompts.json kể cả khi đã có")
    parser.add_argument("--run", action="store_true", help="Chạy luôn pipeline tạo ảnh 2K & video 1080p")
    args = parser.parse_args()

    res = prepare_and_optionally_run_product(
        raw_id_or_url=args.input,
        template_name=args.template,
        crawl_method=args.method,
        videos_per_character=args.videos_per_char,
        force_regenerate_prompts=args.force_prompts,
        auto_run_pipeline=args.run,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
