"""AI Research & Crawl Sản phẩm TikTok Shop (Standalone trong Skill Video Veo).
Hỗ trợ 2 cách tải thông tin & ảnh sản phẩm:
- Cách 1: SPAI Auto API (Nhanh)
- Cách 2: Trình duyệt Chrome TikTokShop + tự động giải Captcha BoxPhone (YOLO TorchScript)
"""
from __future__ import annotations

import io
import json
import re
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import config


def parse_number(text: str | int | float | None) -> int:
    """Chuyển đổi chuỗi số TikTok ('58.8K', '2.4M', '43.000đ', '85.551₫ (-73%)', '9500') sang số nguyên."""
    if text is None:
        return 0
    if isinstance(text, (int, float)):
        return int(text)
    s = str(text).strip()
    if not s:
        return 0
    s = re.sub(r"\(.*?\)", "", s).strip()
    parts = re.split(r"[₫đ]|vnd|vnđ", s, flags=re.I)
    if parts and parts[0].strip():
        s = parts[0].strip()
    s = s.upper().replace(" ", "")
    if "K" in s:
        s = s.replace("K", "").replace(",", ".")
        try:
            return int(float(s) * 1000)
        except ValueError:
            return 0
    if "M" in s:
        s = s.replace("M", "").replace(",", ".")
        try:
            return int(float(s) * 1_000_000)
        except ValueError:
            return 0
    cleaned = re.sub(r"[^\d]", "", s)
    try:
        return int(cleaned) if cleaned else 0
    except ValueError:
        return 0


def extract_product_id(url_or_text: str | None) -> str:
    """Trích xuất ID sản phẩm từ URL chia sẻ hoặc chuỗi văn bản."""
    if not url_or_text:
        return ""
    text = str(url_or_text).strip()
    for pat in (
        r"product[/_]?id=([0-9]{12,25})",
        r"/product/([0-9]{12,25})",
        r"/pdp/([0-9]{12,25})",
        r"/p/([0-9]{12,25})",
        r"sku_id=([0-9]{12,25})",
        r"\b([0-9]{15,22})\b",
    ):
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def resolve_tiktok_share(raw_text: str, timeout: float = 4.0) -> dict[str, str]:
    text = (raw_text or "").strip()
    if not text:
        return {"url": "", "product_id": "", "title": "", "raw": ""}

    url_match = re.search(r"https?://[^\s<>\"'()]+", text)
    found_url = url_match.group(0) if url_match else ""

    title = ""
    if found_url and not text.startswith(found_url):
        prefix = text[:text.find(found_url)].strip()
        prefix = re.sub(r"(?i)(hãy xem sản phẩm này trên tiktok shop|xem sản phẩm trên tiktok shop|tiktok shop).*", "", prefix).strip()
        prefix = re.sub(r"[!?:.\-_|]+$", "", prefix).strip()
        if len(prefix) >= 3:
            title = prefix

    product_id = extract_product_id(found_url or text)
    final_url = found_url

    is_short = bool(found_url and any(d in found_url.lower() for d in ("vt.tiktok.com", "vm.tiktok.com", "/t/")))
    if found_url and (is_short or not product_id):
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            resp = requests.get(found_url, headers=headers, allow_redirects=True, timeout=timeout)
            if resp.url:
                final_url = resp.url
                extracted = extract_product_id(final_url)
                if extracted:
                    product_id = extracted
            if not title and resp.text:
                m_og = re.search(r'<meta[^>]+property=[\'"]og:title[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', resp.text, re.I)
                if not m_og:
                    m_og = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+property=[\'"]og:title[\'"]', resp.text, re.I)
                if m_og:
                    t = re.sub(r"(?i)\s*[-|]\s*tiktok shop.*", "", m_og.group(1).strip()).strip()
                    if t:
                        title = t
        except Exception:
            pass

    if not product_id:
        product_id = extract_product_id(text)
    if not title:
        title = f"Sản phẩm #{product_id}" if product_id else "Sản phẩm TikTok Shop"

    return {
        "url": final_url or found_url,
        "product_id": product_id,
        "title": title,
        "raw": text,
    }


def to_desktop_pdp_url(product_id_or_url: str | None) -> str:
    if not product_id_or_url:
        return ""
    text = str(product_id_or_url).strip()
    pid = extract_product_id(text)
    if pid:
        return f"https://shop.tiktok.com/vn/pdp/{pid}"
    if text.startswith("http://") or text.startswith("https://"):
        resolved = resolve_tiktok_share(text)
        if resolved.get("product_id"):
            return f"https://shop.tiktok.com/vn/pdp/{resolved['product_id']}"
        return text
    return ""


def fetch_product_details_browser(
    product_id_or_url: str,
    download_images: bool = True,
    log_fn: Any = None,
) -> dict[str, Any]:
    """Cách 2: Mở trình duyệt Chrome với tài khoản có sẵn + giải Captcha tự động từ BoxPhone."""
    from .browser_crawler import fetch_product_details_via_browser

    kwargs: dict[str, Any] = {"download_images": download_images}
    if callable(log_fn):
        kwargs["log_fn"] = log_fn
    return fetch_product_details_via_browser(product_id_or_url, **kwargs)


def fetch_product_details_spaiauto(
    product_id_or_url: str,
    download_images: bool = True,
    allow_browser_fallback: bool = True,
    log_fn: Any = None,
) -> dict[str, Any]:
    """Tải và lấy toàn bộ thông tin sản phẩm:
    - Cách 1 (Ưu tiên): SPAI Auto API (https://tools.spaiauto.com/lay-thong-tin-san-pham).
    - Cách 2 (Dự phòng tự động khi Cách 1 lỗi): Mở trực tiếp trình duyệt Chrome TikTokShop
      kết hợp giải Captcha tự động từ model training của BoxPhone.
    """
    pid = extract_product_id(product_id_or_url)
    pdp_url = to_desktop_pdp_url(product_id_or_url)
    if not pdp_url:
        return {"success": False, "error": "Không tìm thấy ID sản phẩm hoặc URL hợp lệ."}

    import requests

    api_url = "https://tools.spaiauto.com/api.php"
    payload = {
        "action": "extract_product",
        "url": pdp_url,
        "recaptcha_token": "",
    }
    headers = {
        "Accept": "*/*",
        "Accept-Language": "vi,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://tools.spaiauto.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    spai_error = ""
    res_json: dict[str, Any] = {}
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=12)
        resp.raise_for_status()
        res_json = resp.json()
    except Exception as e:
        spai_error = f"Lỗi kết nối SPAI Auto: {e}"

    if not spai_error and not res_json.get("success"):
        spai_error = res_json.get("message") or "SPAI Auto không trích xuất được sản phẩm."

    raw = (res_json.get("data") or {}) if not spai_error else {}
    title = str(raw.get("title") or "").strip()
    images = [str(x) for x in raw.get("images", []) if x]

    if not spai_error and not title and not images:
        spai_error = "SPAI Auto trả về dữ liệu rỗng (không có tiêu đề và ảnh)."

    if spai_error:
        if allow_browser_fallback:
            if callable(log_fn):
                log_fn(f"⚠️ Cách 1 (SPAI Auto) lỗi ({spai_error}) → Chuyển sang Cách 2 (Trình duyệt TikTokShop + Giải Captcha BoxPhone)...")
            browser_res = fetch_product_details_browser(
                product_id_or_url,
                download_images=download_images,
                log_fn=log_fn,
            )
            if browser_res.get("success"):
                browser_res["fallback_from"] = "spaiauto"
                browser_res["spaiauto_error"] = spai_error
                return browser_res
            return {
                "success": False,
                "error": f"Cách 1 lỗi ({spai_error}) | Cách 2 lỗi ({browser_res.get('error', 'Không rõ')})",
            }
        return {"success": False, "error": spai_error}

    shop_name = str(raw.get("shop_name") or "").strip()
    price = parse_number(raw.get("price"))
    orig_price = parse_number(raw.get("original_price"))
    sold_count = parse_number(raw.get("sold_count"))
    sold_raw = str(raw.get("sold_count") or "").strip()
    desc = str(raw.get("description") or "").strip()
    desc_images = [str(x) for x in raw.get("description_images", []) if x]
    variations = raw.get("variations", [])
    primary_image = images[0] if images else ""

    local_thumb_path = ""
    local_images = []

    if download_images and pid:
        try:
            prod_img_dir = config.PRODUCT_IMAGES_DIR / pid
            prod_img_dir.mkdir(parents=True, exist_ok=True)

            if primary_image:
                thumb_file = prod_img_dir / "thumb.webp"
                if not thumb_file.is_file() or thumb_file.stat().st_size == 0:
                    img_resp = requests.get(primary_image, timeout=15)
                    if img_resp.status_code == 200:
                        thumb_file.write_bytes(img_resp.content)
                if thumb_file.is_file():
                    local_thumb_path = f"product_images/{pid}/thumb.webp"

            images_subdir = prod_img_dir / "images"
            images_subdir.mkdir(parents=True, exist_ok=True)
            for idx, img_url in enumerate(images):
                img_path = images_subdir / f"img_{idx}.webp"
                if not img_path.is_file() or img_path.stat().st_size == 0:
                    try:
                        r = requests.get(img_url, timeout=12)
                        if r.status_code == 200:
                            img_path.write_bytes(r.content)
                    except Exception:
                        pass
                if img_path.is_file():
                    local_images.append(str(img_path))

            info_file = prod_img_dir / "info.json"
            full_info = {
                "product_id": pid,
                "pdp_url": pdp_url,
                "title": title,
                "shop_name": shop_name,
                "price": price,
                "original_price": orig_price,
                "sold_count": sold_count,
                "sold_count_label": sold_raw,
                "description": desc,
                "images": images,
                "description_images": desc_images,
                "variations": variations,
                "local_images": local_images,
                "fetched_at": time.time(),
            }
            info_file.write_text(json.dumps(full_info, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {
        "success": True,
        "product_id": pid,
        "pdp_url": pdp_url,
        "title": title,
        "shop_name": shop_name,
        "price": price,
        "original_price": orig_price,
        "sold_count": sold_count,
        "sold_count_label": sold_raw,
        "description": desc,
        "images": images,
        "desc_images": desc_images,
        "variations": variations,
        "image_url": primary_image,
        "local_thumb": local_thumb_path,
        "local_images": local_images,
        "total_images": len(images),
        "source": "spaiauto",
    }


@dataclass
class ResearchProduct:
    id: str
    title: str = ""
    price: int = 0
    original_price: int = 0
    commission: int = 0
    sold_total: int = 0
    sold_total_label: str = ""
    orders_7d: int = 0
    creators_7d: int = 0
    ratio: float = 0.0
    ratio_label: str = ""
    status: str = "POTENTIAL"
    status_label: str = "Tiềm năng"
    share_url: str = ""
    pdp_url: str = ""
    image_url: str = ""
    local_thumb: str = ""
    images: list[str] = field(default_factory=list)
    desc_images: list[str] = field(default_factory=list)
    description: str = ""
    shop_name: str = ""
    variations: list[str] = field(default_factory=list)
    has_details: bool = False
    category: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    notes: str = ""
    is_hot: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_product(
    price: int,
    sold_total: int,
    orders_7d: int,
    creators_7d: int,
    max_price: int = 200000,
    max_sold_total: int = 50000,
    min_ratio: float = 2.0,
    max_ratio: float = 9999.0,
) -> tuple[str, str, float, str]:
    creators = max(1, creators_7d)
    ratio = round(orders_7d / creators, 2)
    ratio_label = f"1 : {ratio}" if creators_7d > 0 else "—"

    pass_price = (price <= max_price) if price > 0 else True
    pass_sold = (sold_total <= max_sold_total) if sold_total > 0 else True
    pass_ratio = (ratio >= min_ratio) if creators_7d > 0 else False

    score = int(pass_price) + int(pass_sold) + int(pass_ratio)
    if score == 3:
        return "WIN", f"🎯 Sản phẩm WIN (3/3 tiêu chí, tỉ lệ 1:{ratio})", ratio, ratio_label
    if score == 2:
        return "WIN", f"✨ ĐẠT 2/3 tiêu chí (tỉ lệ 1:{ratio})", ratio, ratio_label
    if score == 1:
        return "POTENTIAL", "Chỉ đạt 1/3 tiêu chí", ratio, ratio_label
    return "SATURATED", "Không đạt tiêu chí", ratio, ratio_label


class ResearchStore:
    def __init__(self, file_path: Path | None = None):
        self.file_path = Path(file_path or config.STORE_RESEARCH)
        self.lock = threading.RLock()
        self._cache: dict[str, ResearchProduct] = {}
        self._last_mtime: float = 0.0
        self.criteria: dict[str, Any] = {
            "maxPrice": 200000,
            "maxSoldTotal": 50000,
            "bestSoldTotal": 5000,
            "minRatio": 2.0,
            "maxRatio": 9999.0,
            "targetCategory": "",
            "autoScanCount": 20,
        }
        self.on_update = None
        self.load()

    def load(self) -> None:
        with self.lock:
            if not self.file_path.is_file():
                self._cache = {}
                return
            try:
                self._last_mtime = self.file_path.stat().st_mtime
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                products = data.get("products", [])
                self.criteria.update(data.get("criteria", {}))
                self._cache = {}
                for p in products:
                    if isinstance(p, dict) and p.get("id"):
                        prod = ResearchProduct(**{k: v for k, v in p.items() if k in ResearchProduct.__annotations__})
                        self._cache[prod.id] = prod
            except Exception:
                self._cache = {}

    def save(self, create_backup: bool = True) -> None:
        with self.lock:
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "criteria": self.criteria,
                    "updatedAt": time.time(),
                    "products": [p.to_dict() for p in self._cache.values()],
                }
                self.file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                self._last_mtime = self.file_path.stat().st_mtime
            except Exception:
                pass

    def _ensure_fresh(self) -> None:
        try:
            if self.file_path.is_file() and self.file_path.stat().st_mtime > self._last_mtime:
                self.load()
        except Exception:
            pass

    def list_products(self) -> list[dict[str, Any]]:
        with self.lock:
            self._ensure_fresh()
            items = sorted(self._cache.values(), key=lambda x: (x.status == "WIN", x.created_at), reverse=True)
            return [p.to_dict() for p in items]

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        with self.lock:
            self._ensure_fresh()
            p = self._cache.get(product_id)
            return p.to_dict() if p else None

    def add_or_update(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self._ensure_fresh()
            prod_id = str(data.get("id") or data.get("product_id") or "").strip()
            if not prod_id:
                prod_id = extract_product_id(data.get("share_url") or data.get("url") or "")
            if not prod_id:
                prod_id = f"prod_{int(time.time() * 1000)}"

            existing = self._cache.get(prod_id)
            price = parse_number(data.get("price")) if "price" in data else (existing.price if existing else 0)
            orig_price = parse_number(data.get("original_price")) if "original_price" in data else (existing.original_price if existing else 0)
            sold_total = parse_number(data.get("sold_total") or data.get("sold_count")) if ("sold_total" in data or "sold_count" in data) else (existing.sold_total if existing else 0)
            orders_7d = parse_number(data.get("orders_7d")) if "orders_7d" in data else (existing.orders_7d if existing else 0)
            creators_7d = parse_number(data.get("creators_7d")) if "creators_7d" in data else (existing.creators_7d if existing else 0)

            status, status_label, ratio, ratio_label = evaluate_product(
                price=price,
                sold_total=sold_total,
                orders_7d=orders_7d,
                creators_7d=creators_7d,
            )

            title = str(data.get("title") or (existing.title if existing else "") or f"Sản phẩm #{prod_id}").strip()
            share_url = str(data.get("share_url") or data.get("url") or (existing.share_url if existing else "")).strip()
            pdp_url = str(data.get("pdp_url") or (existing.pdp_url if existing else "") or to_desktop_pdp_url(share_url or prod_id)).strip()
            image_url = str(data.get("image_url") or (existing.image_url if existing else "")).strip()
            local_thumb = str(data.get("local_thumb") or (existing.local_thumb if existing else "")).strip()
            images = list(data.get("images") or (existing.images if existing else []))
            desc_images = list(data.get("desc_images") or (existing.desc_images if existing else []))
            description = str(data.get("description") or (existing.description if existing else "")).strip()
            shop_name = str(data.get("shop_name") or (existing.shop_name if existing else "")).strip()
            variations = list(data.get("variations") or (existing.variations if existing else []))
            has_details = bool(data.get("has_details", (existing.has_details if existing else bool(title and images))))

            product = ResearchProduct(
                id=prod_id,
                title=title,
                price=price,
                original_price=orig_price,
                sold_total=sold_total,
                sold_total_label=str(data.get("sold_total_label") or data.get("sold_count_label") or (existing.sold_total_label if existing else "")),
                orders_7d=orders_7d,
                creators_7d=creators_7d,
                ratio=ratio,
                ratio_label=ratio_label,
                status=status,
                status_label=status_label,
                share_url=share_url,
                pdp_url=pdp_url,
                image_url=image_url,
                local_thumb=local_thumb,
                images=images,
                desc_images=desc_images,
                description=description,
                shop_name=shop_name,
                variations=variations,
                has_details=has_details,
                created_at=existing.created_at if existing else time.time(),
            )
            self._cache[product.id] = product
        self.save()
        return product.to_dict()

    def remove_product(self, product_id: str) -> bool:
        with self.lock:
            self._ensure_fresh()
            existed = product_id in self._cache
            self._cache.pop(product_id, None)
        if existed:
            self.save()
        return existed


store = ResearchStore()
list_products = store.list_products
get_product = store.get_product
add_or_update = store.add_or_update
remove_product = store.remove_product


