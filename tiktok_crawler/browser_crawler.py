"""Cách 2 (Standalone trong Skill Video Veo): Crawl thông tin & ảnh sản phẩm TikTok Shop trực tiếp bằng trình duyệt Chrome
tích hợp tự động giải Captcha bằng model YOLO TorchScript từ BoxPhone (`tiktok_crawler/boxphone_captcha/`).

Luồng hoạt động:
1. Mở / kết nối trình duyệt Chrome thật qua CDP port 9222 với profile TikTokShop trong `data/tiktok_crawler/tiktok_shop/profiles/tiktok_chrome_profile`.
2. Truy cập trang sản phẩm `https://www.tiktok.com/shop/pdp/{id}` hoặc `https://shop.tiktok.com/vn/pdp/{id}`.
3. Nếu gặp Captcha (Kéo trượt `cap_truot`, Xoay tròn `cap_xoay`, Chọn 2 hình giống nhau `cap_chon`):
   - Dùng model YOLO TorchScript đã đóng gói sẵn trong `tiktok_crawler/boxphone_captcha/weights/08102026_detect.torchscript`
     (cùng `detect_s.torchscript`, `detect.torchscript` và bộ `templates/*.png`) để nhận diện chính xác
     loại captcha, toạ độ khung captcha, nút kéo (`thanhkeo`), nút làm mới (`refresh`), nút xác nhận (`xacnhan`).
   - Tự động tính toán khoảng cách kéo / góc xoay / cặp vật thể đồng dạng bằng OpenCV + Torch và thao tác chuột
     mượt như người thật (`human_like_drag`) để vượt Captcha.
4. Cuộn trang, bóc tách toàn bộ JSON nhúng (`__MODERN_ROUTER_DATA__`, `__UNIVERSAL_DATA_FOR_WEB__`, `RENDER_DATA`)
   kết hợp DOM JS Scraper để lấy đầy đủ thông tin và ảnh sản phẩm.
5. Tải ảnh về `config.PRODUCT_IMAGES_DIR / pid` (`thumb.webp`, `images/img_*.webp`, `info.json`).
"""
from __future__ import annotations

import base64
import io
import json
import math
import os
import random
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from . import config

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    try:
        print(f"[BrowserCrawler] {msg}")
    except UnicodeEncodeError:
        print(f"[BrowserCrawler] {msg}".encode("utf-8", errors="replace").decode("ascii", errors="ignore"))


# ==============================================================================
# 1. NHẬN DIỆN CAPTCHA TỪ MODEL TRAINING CỦA BOXPHONE (YOLO TORCHSCRIPT + TEMPLATES)
# ==============================================================================

class CaptchaDetectBoxPhone:
    """Bộ nhận diện Captcha TikTok sử dụng trực tiếp dữ liệu training đóng gói trong Skill:
    - Model chính: `08102026_detect.torchscript` (6 classes: cap_chon, cap_truot, cap_xoay, refresh, thanhkeo, xacnhan)
    - Model phụ: `detect_s.torchscript`, `detect.torchscript`
    - Templates: `tiktok_crawler/boxphone_captcha/templates/*.png`
    """

    CLASS_NAMES = {
        0: "cap_chon",    # Chọn 2 đối tượng có hình dạng giống nhau -> 2object
        1: "cap_truot",   # Kéo mảnh ghép vào vị trí -> puzle_phone
        2: "cap_xoay",    # Kéo thanh trượt để ghép hình xoay tròn -> rotating_phone
        3: "refresh",     # Nút đổi captcha mới
        4: "thanhkeo",    # Nút kéo thanh trượt (slider handle)
        5: "xacnhan",     # Nút Xác nhận / Confirm
    }

    CAPTCHA_TYPE_MAP = {
        0: "2object",
        1: "puzle_phone",
        2: "rotating_phone",
    }

    def __init__(self, weights_dir: Path | None = None, templates_dir: Path | None = None, target_size: tuple[int, int] = (640, 640)):
        self.weights_dir = weights_dir or config.BOXPHONE_WEIGHTS_DIR
        self.templates_dir = templates_dir or config.BOXPHONE_TEMPLATES_DIR
        self.target_size = target_size
        self.model = None
        self.model_path: Path | None = None
        self.templates: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._load_resources()

    def _load_resources(self) -> None:
        # 1. Load TorchScript model từ BoxPhone
        candidates = [
            self.weights_dir / "08102026_detect.torchscript",
            self.weights_dir / "detect_s.torchscript",
            self.weights_dir / "detect.torchscript",
        ]
        for weight_path in candidates:
            if weight_path.exists():
                try:
                    import torch
                    self.model = torch.jit.load(str(weight_path), map_location="cpu")
                    self.model.eval()
                    self.model_path = weight_path
                    break
                except Exception as exc:
                    print(f"[CaptchaDetectBoxPhone] Không thể nạp {weight_path.name}: {exc}")

        # 2. Load OpenCV templates từ BoxPhone
        if self.templates_dir.exists():
            for tpl_file in self.templates_dir.glob("*.png"):
                try:
                    buf = np.fromfile(str(tpl_file), dtype=np.uint8)
                    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                    if img is not None:
                        self.templates[tpl_file.stem] = img
                except Exception:
                    pass

    @staticmethod
    def resize_and_pad_image(image: np.ndarray, target_size: tuple[int, int] = (640, 640)) -> np.ndarray:
        """Letterbox resize chuẩn theo CaptchaDetect.py của BoxPhone."""
        h, w = image.shape[:2]
        tw, th = target_size
        scale = min(tw / w, th / h)
        nw, nh = int(round(w * scale)), int(round(h * scale))
        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        dw = (tw - nw) / 2.0
        dh = (th - nh) / 2.0
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return padded

    @staticmethod
    def scale_boxes(img1_shape: tuple[int, int], boxes: np.ndarray, img0_shape: tuple[int, int]) -> np.ndarray:
        """Chuyển toạ độ bounding box từ ảnh 640x640 về kích thước ảnh gốc."""
        gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])
        pad_x = (img1_shape[1] - img0_shape[1] * gain) / 2.0
        pad_y = (img1_shape[0] - img0_shape[0] * gain) / 2.0

        scaled = boxes.copy().astype(np.float32)
        scaled[:, [0, 2]] -= pad_x
        scaled[:, [1, 3]] -= pad_y
        scaled[:, :4] /= gain

        scaled[:, [0, 2]] = np.clip(scaled[:, [0, 2]], 0, img0_shape[1])
        scaled[:, [1, 3]] = np.clip(scaled[:, [1, 3]], 0, img0_shape[0])
        return scaled

    def solve(self, image_bgr: np.ndarray, conf_thres: float = 0.25, iou_thres: float = 0.45) -> dict[str, Any]:
        result: dict[str, Any] = {
            "check": False,
            "type_captcha": None,
            "captcha": None,
            "captcha_score": 0.0,
            "click": None,
            "refresh": None,
            "xacnhan": None,
            "detections": [],
        }
        if image_bgr is None or image_bgr.size == 0:
            return result

        if self.model is not None:
            try:
                import torch
                import torchvision

                with self._lock, torch.no_grad():
                    orig_h, orig_w = image_bgr.shape[:2]
                    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                    padded = self.resize_and_pad_image(rgb, self.target_size)
                    tensor = torch.from_numpy(padded).permute(2, 0, 1).float().div(255.0).unsqueeze(0)

                    preds = self.model(tensor)
                    if isinstance(preds, (list, tuple)):
                        preds = preds[0]
                    pred = preds[0].transpose(0, 1)
                    boxes_cxcywh = pred[:, :4]
                    scores_all = pred[:, 4:]
                    max_scores, cls_ids = scores_all.max(dim=1)
                    mask = max_scores > conf_thres

                    if mask.any():
                        boxes_cxcywh = boxes_cxcywh[mask]
                        max_scores = max_scores[mask]
                        cls_ids = cls_ids[mask]

                        xyxy = torch.zeros_like(boxes_cxcywh)
                        xyxy[:, 0] = boxes_cxcywh[:, 0] - boxes_cxcywh[:, 2] / 2.0
                        xyxy[:, 1] = boxes_cxcywh[:, 1] - boxes_cxcywh[:, 3] / 2.0
                        xyxy[:, 2] = boxes_cxcywh[:, 0] + boxes_cxcywh[:, 2] / 2.0
                        xyxy[:, 3] = boxes_cxcywh[:, 1] + boxes_cxcywh[:, 3] / 2.0

                        offsets = cls_ids.float() * 4096.0
                        boxes_for_nms = xyxy + offsets.unsqueeze(1)
                        keep = torchvision.ops.nms(boxes_for_nms, max_scores, iou_thres)

                        xyxy_np = xyxy[keep].cpu().numpy()
                        scores_np = max_scores[keep].cpu().numpy()
                        cls_np = cls_ids[keep].cpu().numpy().astype(int)

                        scaled_xyxy = self.scale_boxes(self.target_size, xyxy_np, (orig_h, orig_w)).astype(int)

                        captcha_candidates: list[tuple[float, int, list[int]]] = []
                        best_per_class: dict[int, tuple[float, list[int]]] = {}

                        for box, score, cid in zip(scaled_xyxy, scores_np, cls_np):
                            b_list = [int(box[0]), int(box[1]), int(box[2]), int(box[3])]
                            sc = float(score)
                            result["detections"].append({
                                "class_id": int(cid),
                                "class_name": self.CLASS_NAMES.get(int(cid), str(cid)),
                                "score": round(sc, 4),
                                "box": b_list,
                            })
                            if cid not in best_per_class or sc > best_per_class[cid][0]:
                                best_per_class[cid] = (sc, b_list)
                            if cid in (0, 1, 2) and sc >= 0.30:
                                captcha_candidates.append((sc, int(cid), b_list))

                        if captcha_candidates:
                            captcha_candidates.sort(key=lambda x: x[0], reverse=True)
                            best_sc, best_cid, best_box = captcha_candidates[0]
                            result["check"] = True
                            result["type_captcha"] = self.CAPTCHA_TYPE_MAP[best_cid]
                            result["captcha"] = best_box
                            result["captcha_score"] = round(best_sc, 4)

                        if 3 in best_per_class:
                            result["refresh"] = best_per_class[3][1]
                        if 4 in best_per_class:
                            result["click"] = best_per_class[4][1]
                        if 5 in best_per_class:
                            result["xacnhan"] = best_per_class[5][1]
            except Exception as exc:
                print(f"[CaptchaDetectBoxPhone] Lỗi suy luận YOLO: {exc}")

        if not result["check"] and self.templates:
            for tpl_name, tpl_type in (
                ("template_slide", "puzle_phone"),
                ("template_xoay", "rotating_phone"),
                ("template_object", "2object"),
            ):
                tpl = self.templates.get(tpl_name)
                if tpl is not None and image_bgr.shape[0] >= tpl.shape[0] and image_bgr.shape[1] >= tpl.shape[1]:
                    res = cv2.matchTemplate(image_bgr, tpl, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val >= 0.75:
                        th, tw = tpl.shape[:2]
                        result["check"] = True
                        result["type_captcha"] = tpl_type
                        result["captcha"] = [max_loc[0], max_loc[1], max_loc[0] + tw, max_loc[1] + th]
                        result["captcha_score"] = round(float(max_val), 4)
                        break

        return result


_CAPTCHA_DETECTOR: CaptchaDetectBoxPhone | None = None
_DETECTOR_LOCK = threading.Lock()


def get_captcha_detector() -> CaptchaDetectBoxPhone:
    global _CAPTCHA_DETECTOR
    with _DETECTOR_LOCK:
        if _CAPTCHA_DETECTOR is None:
            _CAPTCHA_DETECTOR = CaptchaDetectBoxPhone()
        return _CAPTCHA_DETECTOR


# ==============================================================================
# 2. THUẬT TOÁN GIẢI CAPTCHA TỰ ĐỘNG TRÊN TRÌNH DUYỆT (SLIDER, ROTATE, 2-OBJECT)
# ==============================================================================

class BoxPhoneCaptchaSolver:
    """Bộ giải Captcha tự động kết hợp YOLO TorchScript của BoxPhone + XPath DOM của BoxPhone + OpenCV."""

    XPATH_HAS_CAPTCHA = (
        "//div[contains(@class , 'captcha_verify_slide--button')] | "
        "//div[contains(@class , 'captcha_verify_img')] | "
        "//div[contains(@class , 'captcha-verify-image')] | "
        "//img[@id='captcha-verify-image'] | "
        "//img[@data-testid='whirl-inner-img'] | "
        "//div[contains(@class, 'secsdk-captcha-drag-icon')] | "
        "//div[contains(@class , 'cap-flex cap-flex-col cap-relative')]"
    )

    XPATH_WHIRL_INNER = "//img[@data-testid='whirl-inner-img'] | //div[contains(@class,'cap-relative')]//img[contains(@class,'cap-absolute')]"
    XPATH_WHIRL_OUTER = "//img[@data-testid='whirl-outer-img'] | //img[contains(@class,'cap-h-[170px]') or contains(@class,'sm:cap-h-[210px]')]"
    XPATH_PUZZLE_BG = "//img[@id='captcha-verify-image'] | //img[contains(@class, 'cap-rounded-lg')]"
    XPATH_PUZZLE_SLIDE = "//img[contains(@class, 'captcha_verify_img_slide')] | //img[contains(@class, 'cap-absolute') and not(@data-testid='whirl-inner-img')]"
    XPATH_DRAG_BUTTON = (
        "//div[contains(@class, 'secsdk-captcha-drag-icon')] | "
        "//*[@id='captcha_slide_button'] | "
        "//*[@id=':r2:']/div/div[2]/div[2]/div/div/button | "
        "(//div[contains(@class,'cap-flex cap-absolute')])[last()]"
    )
    XPATH_SLIDER_TRACK = (
        "//*[@id='secsdk-captcha-drag-wrapper'] | "
        "//*[@id='captcha-verify-container-main-page']/div[2]/div[2]/div | "
        "//*[@id=':r2:']/div/div[2]/div[2]/div"
    )
    XPATH_CONFIRM_BTN = (
        "//div[text()='Confirm'] | //div[text()='Xác nhận'] | "
        "//div[contains(@class, 'verify-captcha-submit-button')] | "
        "//button[contains(@class, 'TUXButton--primary')]"
    )
    XPATH_REFRESH_BTN = (
        "//a[contains(@class, 'secsdk_captcha_refresh')] | "
        "//div[contains(@class, 'secsdk_captcha_refresh')] | "
        "//button[contains(@class, 'TUXButton--borderless')]"
    )

    def __init__(self, log_fn: LogFn = _default_log):
        self.log = log_fn
        self.detector = get_captcha_detector()
        self.boxphone_api_cfg = self._load_boxphone_api_config()

    @staticmethod
    def _load_boxphone_api_config() -> dict[str, Any]:
        cfg_path = config.BOXPHONE_DIR / "config.json"
        if cfg_path.exists():
            try:
                return json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    @staticmethod
    def _download_or_extract_img(page: Any, locator_or_xpath: str) -> tuple[np.ndarray | None, dict[str, float] | None]:
        try:
            loc = page.locator(f"xpath={locator_or_xpath}").first
            if loc.count() == 0 or not loc.is_visible(timeout=1200):
                return None, None
            bbox = loc.bounding_box()
            src = loc.get_attribute("src") or ""
            img_bytes: bytes | None = None

            if src.startswith("data:image"):
                b64_part = src.split(",", 1)[-1]
                img_bytes = base64.b64decode(b64_part)
            elif src.startswith("blob:") or src.startswith("http"):
                b64_data = loc.evaluate(
                    """async (el) => {
                        try {
                            const r = await fetch(el.src);
                            const blob = await r.blob();
                            return await new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                        } catch (e) {
                            try {
                                const c = document.createElement('canvas');
                                c.width = el.naturalWidth || el.width;
                                c.height = el.naturalHeight || el.height;
                                c.getContext('2d').drawImage(el, 0, 0);
                                return c.toDataURL('image/png');
                            } catch (e2) {
                                return '';
                            }
                        }
                    }"""
                )
                if b64_data and "," in b64_data:
                    img_bytes = base64.b64decode(b64_data.split(",", 1)[-1])
                elif src.startswith("http"):
                    req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        img_bytes = resp.read()

            if not img_bytes:
                img_bytes = loc.screenshot(type="png")

            if img_bytes:
                arr = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
                return img, bbox
        except Exception:
            pass
        return None, None

    @staticmethod
    def human_like_drag(page: Any, start_x: float, start_y: float, distance: float, duration: float = 0.65) -> None:
        steps = max(18, int(abs(distance) / 6))
        page.mouse.move(start_x, start_y)
        time.sleep(random.uniform(0.08, 0.16))
        page.mouse.down()
        time.sleep(random.uniform(0.08, 0.15))

        overshoot = random.uniform(2.0, 5.0) if distance > 25 else 0.0
        total_first = distance + overshoot

        for i in range(1, steps + 1):
            t = i / steps
            ease = 1.0 - pow(1.0 - t, 3)
            cur_x = start_x + total_first * ease
            cur_y = start_y + random.uniform(-1.5, 1.5)
            page.mouse.move(cur_x, cur_y)
            time.sleep(max(0.008, (duration / steps) * random.uniform(0.7, 1.3)))

        if overshoot > 0:
            time.sleep(random.uniform(0.05, 0.10))
            back_steps = 4
            for j in range(1, back_steps + 1):
                cur_x = start_x + total_first - (overshoot * (j / back_steps))
                cur_y = start_y + random.uniform(-0.8, 0.8)
                page.mouse.move(cur_x, cur_y)
                time.sleep(random.uniform(0.015, 0.03))

        time.sleep(random.uniform(0.12, 0.24))
        page.mouse.up()

    @staticmethod
    def compute_slider_distance(bg_img: np.ndarray, piece_img: np.ndarray | None, rendered_bg_width: float, piece_offset_x: float = 0.0) -> float:
        bg_bgr = bg_img[:, :, :3] if bg_img.ndim == 3 and bg_img.shape[2] == 4 else bg_img
        bg_h, bg_w = bg_bgr.shape[:2]
        scale = (rendered_bg_width / bg_w) if (bg_w > 0 and rendered_bg_width > 0) else 1.0

        if piece_img is not None and piece_img.size > 0:
            if piece_img.ndim == 3 and piece_img.shape[2] == 4:
                alpha = piece_img[:, :, 3]
                ys, xs = np.where(alpha > 30)
                if len(xs) > 10 and len(ys) > 10:
                    x1, x2 = int(xs.min()), int(xs.max())
                    y1, y2 = int(ys.min()), int(ys.max())
                    piece_crop = piece_img[y1:y2 + 1, x1:x2 + 1, :3]
                else:
                    piece_crop = piece_img[:, :, :3]
            else:
                piece_crop = piece_img[:, :, :3] if piece_img.ndim == 3 else cv2.cvtColor(piece_img, cv2.COLOR_GRAY2BGR)

            ph, pw = piece_crop.shape[:2]
            if ph > bg_h * 0.85:
                gray_p = cv2.cvtColor(piece_crop, cv2.COLOR_BGR2GRAY)
                row_energy = (gray_p > 15).sum(axis=1)
                active_rows = np.where(row_energy > 8)[0]
                if len(active_rows) > 10:
                    ry1, ry2 = int(active_rows.min()), int(active_rows.max())
                    piece_crop = piece_crop[ry1:ry2 + 1, :]
                    bg_search = bg_bgr[max(0, ry1 - 6):min(bg_h, ry2 + 7), :]
                else:
                    bg_search = bg_bgr
            else:
                bg_search = bg_bgr

            bg_gray = cv2.GaussianBlur(cv2.cvtColor(bg_search, cv2.COLOR_BGR2GRAY), (3, 3), 0)
            pc_gray = cv2.GaussianBlur(cv2.cvtColor(piece_crop, cv2.COLOR_BGR2GRAY), (3, 3), 0)

            bg_edges = cv2.Canny(bg_gray, 80, 180)
            pc_edges = cv2.Canny(pc_gray, 80, 180)

            min_x = max(int(pc_edges.shape[1] * 0.9), int(bg_w * 0.15))
            if bg_edges.shape[0] >= pc_edges.shape[0] and bg_edges.shape[1] > min_x + pc_edges.shape[1]:
                res = cv2.matchTemplate(bg_edges[:, min_x:], pc_edges, cv2.TM_CCOEFF_NORMED)
                _, _, _, max_loc = cv2.minMaxLoc(res)
                target_x_natural = min_x + max_loc[0]
                return max(15.0, (target_x_natural * scale) - piece_offset_x)

        gray = cv2.cvtColor(bg_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 100, 200)
        start_col = int(bg_w * 0.22)
        end_col = int(bg_w * 0.92)
        col_scores = edges[:, start_col:end_col].sum(axis=0).astype(np.float32)
        kernel = np.ones(min(45, max(15, int(bg_w * 0.12))), dtype=np.float32)
        smooth_scores = np.convolve(col_scores, kernel, mode="valid")
        best_col = start_col + int(np.argmax(smooth_scores))
        return max(20.0, (best_col * scale) - piece_offset_x)

    @staticmethod
    def compute_whirl_angle(inner_img: np.ndarray, outer_img: np.ndarray) -> float:
        in_bgr = inner_img[:, :, :3] if inner_img.ndim == 3 and inner_img.shape[2] == 4 else inner_img
        out_bgr = outer_img[:, :, :3] if outer_img.ndim == 3 and outer_img.shape[2] == 4 else outer_img

        size = 240
        out_resized = cv2.resize(out_bgr, (size, size), interpolation=cv2.INTER_LINEAR)
        in_h, in_w = in_bgr.shape[:2]
        out_h, out_w = out_bgr.shape[:2]

        ratio = (in_w / out_w) if (out_w > 0 and in_w < out_w) else 0.61
        r_seam = int((size / 2.0) * ratio)
        r_in = max(12, r_seam - 3)
        r_out = min((size // 2) - 3, r_seam + 3)

        in_diam = int(round(size * ratio))
        in_resized = cv2.resize(in_bgr, (in_diam, in_diam), interpolation=cv2.INTER_LINEAR)

        in_canvas = np.zeros((size, size, 3), dtype=np.uint8)
        pad = (size - in_diam) // 2
        in_canvas[pad:pad + in_diam, pad:pad + in_diam] = in_resized

        thetas = np.deg2rad(np.arange(0, 360, 1, dtype=np.float32))
        cx, cy = size / 2.0, size / 2.0

        ix = np.clip((cx + r_in * np.cos(thetas)).astype(int), 0, size - 1)
        iy = np.clip((cy + r_in * np.sin(thetas)).astype(int), 0, size - 1)
        ox = np.clip((cx + r_out * np.cos(thetas)).astype(int), 0, size - 1)
        oy = np.clip((cy + r_out * np.sin(thetas)).astype(int), 0, size - 1)

        in_ring = cv2.GaussianBlur(in_canvas, (3, 3), 0)[iy, ix].astype(np.float32)
        out_ring = cv2.GaussianBlur(out_resized, (3, 3), 0)[oy, ox].astype(np.float32)

        best_deg = 90.0
        min_diff = float("inf")

        for deg in range(18, 342, 2):
            shift_dual = (2 * deg) % 360
            shifted_in_dual = np.roll(in_ring, shift=shift_dual, axis=0)
            diff_dual = float(np.mean(np.abs(shifted_in_dual - out_ring)))

            shifted_in_single = np.roll(in_ring, shift=deg, axis=0)
            diff_single = float(np.mean(np.abs(shifted_in_single - out_ring)))

            score = min(diff_dual, diff_single * 1.05)
            if score < min_diff:
                min_diff = score
                best_deg = float(deg)

        return best_deg

    @staticmethod
    def compute_2object_clicks(img_bgr: np.ndarray) -> list[tuple[float, float]]:
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        edges = cv2.Canny(blurred, 40, 130)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        objects: list[dict[str, Any]] = []
        min_area = (h * w) * 0.015
        max_area = (h * w) * 0.30

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                cx, cy = x + bw / 2.0, y + bh / 2.0
                if 0.08 * w <= cx <= 0.92 * w and 0.08 * h <= cy <= 0.92 * h:
                    crop = img_bgr[y:y + bh, x:x + bw]
                    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                    cv2.normalize(hist, hist)
                    objects.append({
                        "cnt": cnt,
                        "center": (cx / w, cy / h),
                        "area": area,
                        "hist": hist,
                    })

        if len(objects) >= 2:
            best_pair = (objects[0]["center"], objects[1]["center"])
            best_dist = float("inf")
            for i in range(len(objects)):
                for j in range(i + 1, len(objects)):
                    c1 = objects[i]["center"]
                    c2 = objects[j]["center"]
                    if math.hypot(c1[0] - c2[0], c1[1] - c2[1]) < 0.14:
                        continue
                    shape_dist = cv2.matchShapes(objects[i]["cnt"], objects[j]["cnt"], cv2.CONTOURS_MATCH_I1, 0.0)
                    area_ratio = abs(objects[i]["area"] - objects[j]["area"]) / max(objects[i]["area"], objects[j]["area"])
                    total_dist = shape_dist + area_ratio * 0.5
                    if total_dist < best_dist:
                        best_dist = total_dist
                        best_pair = (c1, c2)
            return [best_pair[0], best_pair[1]]

        return [(0.35, 0.45), (0.68, 0.55)]

    def has_captcha_dom(self, page: Any) -> bool:
        try:
            loc = page.locator(f"xpath={self.XPATH_HAS_CAPTCHA}").first
            return loc.count() > 0 and loc.is_visible(timeout=600)
        except Exception:
            return False

    def check_and_solve(self, page: Any, max_attempts: int = 5) -> bool:
        for attempt in range(1, max_attempts + 1):
            try:
                png_bytes = page.screenshot(type="png", full_page=False)
                img_arr = np.frombuffer(png_bytes, dtype=np.uint8)
                screenshot_bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            except Exception:
                screenshot_bgr = None

            yolo_res = self.detector.solve(screenshot_bgr) if screenshot_bgr is not None else {"check": False}
            dom_has_cap = self.has_captcha_dom(page)

            if not yolo_res.get("check") and not dom_has_cap:
                if attempt > 1:
                    self.log("✅ Đã vượt Captcha thành công!")
                return True

            cap_type = yolo_res.get("type_captcha")
            cap_score = yolo_res.get("captcha_score", 0.0)

            if not cap_type:
                try:
                    if page.locator(f"xpath={self.XPATH_WHIRL_INNER}").first.is_visible(timeout=500):
                        cap_type = "rotating_phone"
                    elif page.locator(f"xpath={self.XPATH_CONFIRM_BTN}").first.is_visible(timeout=500):
                        cap_type = "2object"
                    else:
                        cap_type = "puzle_phone"
                except Exception:
                    cap_type = "puzle_phone"

            self.log(
                f"🛡️ [BoxPhone Captcha] Phát hiện Captcha loại '{cap_type}' "
                f"(YOLO score={cap_score:.2f}, lần thử {attempt}/{max_attempts})..."
            )

            solved_action = False
            if cap_type == "rotating_phone":
                solved_action = self._solve_rotating(page, yolo_res)
            elif cap_type == "2object":
                solved_action = self._solve_2object(page, yolo_res, screenshot_bgr)
            else:
                solved_action = self._solve_slider(page, yolo_res, screenshot_bgr)

            time.sleep(2.4)

            if not self.has_captcha_dom(page):
                try:
                    png_after = page.screenshot(type="png", full_page=False)
                    after_bgr = cv2.imdecode(np.frombuffer(png_after, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if not self.detector.solve(after_bgr).get("check"):
                        self.log("✅ Đã giải xong Captcha tự động bằng model BoxPhone!")
                        return True
                except Exception:
                    return True

            if not solved_action or attempt < max_attempts:
                self._click_refresh(page, yolo_res)
                time.sleep(1.5)

        return not self.has_captcha_dom(page)

    def _get_drag_start_and_track(self, page: Any, yolo_res: dict[str, Any]) -> tuple[float, float, float]:
        start_x, start_y = 0.0, 0.0
        btn_w = 44.0
        track_w = 280.0

        try:
            btn_loc = page.locator(f"xpath={self.XPATH_DRAG_BUTTON}").first
            if btn_loc.count() > 0 and btn_loc.is_visible(timeout=800):
                rect = btn_loc.bounding_box()
                if rect:
                    start_x = rect["x"] + rect["width"] / 2.0
                    start_y = rect["y"] + rect["height"] / 2.0
                    btn_w = rect["width"]
        except Exception:
            pass

        if start_x == 0.0 and yolo_res.get("click"):
            x1, y1, x2, y2 = yolo_res["click"]
            start_x = (x1 + x2) / 2.0
            start_y = (y1 + y2) / 2.0
            btn_w = max(28.0, float(x2 - x1))

        try:
            track_loc = page.locator(f"xpath={self.XPATH_SLIDER_TRACK}").first
            if track_loc.count() > 0 and track_loc.is_visible(timeout=600):
                t_rect = track_loc.bounding_box()
                if t_rect and t_rect["width"] > 100:
                    track_w = t_rect["width"]
        except Exception:
            pass

        if track_w == 280.0 and yolo_res.get("captcha"):
            cx1, _, cx2, _ = yolo_res["captcha"]
            if (cx2 - cx1) > 150:
                track_w = float(cx2 - cx1)

        usable_w = max(120.0, track_w - btn_w)
        return start_x, start_y, usable_w

    def _solve_slider(self, page: Any, yolo_res: dict[str, Any], screenshot_bgr: np.ndarray | None) -> bool:
        try:
            bg_img, bg_box = self._download_or_extract_img(page, self.XPATH_PUZZLE_BG)
            piece_img, piece_box = self._download_or_extract_img(page, self.XPATH_PUZZLE_SLIDE)

            if bg_img is None and screenshot_bgr is not None and yolo_res.get("captcha"):
                x1, y1, x2, y2 = yolo_res["captcha"]
                bg_img = screenshot_bgr[max(0, y1):y2, max(0, x1):x2]
                bg_box = {"x": float(x1), "y": float(y1), "width": float(x2 - x1), "height": float(y2 - y1)}

            if bg_img is None:
                return False

            rendered_w = bg_box["width"] if bg_box else float(bg_img.shape[1])
            piece_offset_x = 0.0
            if bg_box and piece_box and piece_box["x"] > bg_box["x"]:
                piece_offset_x = piece_box["x"] - bg_box["x"]

            distance = self.compute_slider_distance(bg_img, piece_img, rendered_w, piece_offset_x)
            start_x, start_y, usable_w = self._get_drag_start_and_track(page, yolo_res)
            if start_x <= 0 or start_y <= 0:
                return False

            distance = min(max(18.0, distance), usable_w)
            self.log(f"🧩 [BoxPhone Captcha] Kéo mảnh ghép từ ({start_x:.0f}, {start_y:.0f}) đi {distance:.1f}px...")
            self.human_like_drag(page, start_x, start_y, distance)
            return True
        except Exception as exc:
            self.log(f"⚠️ Lỗi giải Captcha trượt: {exc}")
            return False

    def _solve_rotating(self, page: Any, yolo_res: dict[str, Any]) -> bool:
        try:
            inner_img, _ = self._download_or_extract_img(page, self.XPATH_WHIRL_INNER)
            outer_img, _ = self._download_or_extract_img(page, self.XPATH_WHIRL_OUTER)
            if inner_img is None or outer_img is None:
                return False

            best_deg = self.compute_whirl_angle(inner_img, outer_img)
            start_x, start_y, usable_w = self._get_drag_start_and_track(page, yolo_res)
            if start_x <= 0 or start_y <= 0:
                return False

            distance = (best_deg / 360.0) * usable_w
            distance = min(max(12.0, distance), usable_w)
            self.log(f"🌀 [BoxPhone Captcha] Xoay ảnh góc {best_deg:.1f}° -> kéo {distance:.1f}px...")
            self.human_like_drag(page, start_x, start_y, distance)
            return True
        except Exception as exc:
            self.log(f"⚠️ Lỗi giải Captcha xoay: {exc}")
            return False

    def _solve_2object(self, page: Any, yolo_res: dict[str, Any], screenshot_bgr: np.ndarray | None) -> bool:
        try:
            bg_img, bg_box = self._download_or_extract_img(page, self.XPATH_PUZZLE_BG)
            if bg_img is None and screenshot_bgr is not None and yolo_res.get("captcha"):
                x1, y1, x2, y2 = yolo_res["captcha"]
                bg_img = screenshot_bgr[max(0, y1):y2, max(0, x1):x2]
                bg_box = {"x": float(x1), "y": float(y1), "width": float(x2 - x1), "height": float(y2 - y1)}

            if bg_img is None or bg_box is None:
                return False

            bg_bgr = bg_img[:, :, :3] if bg_img.ndim == 3 and bg_img.shape[2] == 4 else bg_img
            rel_points = self.compute_2object_clicks(bg_bgr)
            for rx, ry in rel_points:
                cx = bg_box["x"] + rx * bg_box["width"]
                cy = bg_box["y"] + ry * bg_box["height"]
                page.mouse.click(cx, cy)
                time.sleep(random.uniform(0.25, 0.45))

            if yolo_res.get("xacnhan"):
                x1, y1, x2, y2 = yolo_res["xacnhan"]
                page.mouse.click((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                return True

            confirm_loc = page.locator(f"xpath={self.XPATH_CONFIRM_BTN}").first
            if confirm_loc.count() > 0 and confirm_loc.is_visible(timeout=800):
                confirm_loc.click()
                return True
        except Exception as exc:
            self.log(f"⚠️ Lỗi giải Captcha 2 vật thể: {exc}")
        return False

    def _click_refresh(self, page: Any, yolo_res: dict[str, Any]) -> None:
        try:
            if yolo_res.get("refresh"):
                x1, y1, x2, y2 = yolo_res["refresh"]
                page.mouse.click((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                return
            ref_loc = page.locator(f"xpath={self.XPATH_REFRESH_BTN}").first
            if ref_loc.count() > 0 and ref_loc.is_visible(timeout=600):
                ref_loc.click()
        except Exception:
            pass


# ==============================================================================
# 3. QUẢN LÝ CHROME PROFILE & BÓC TÁCH DỮ LIỆU SẢN PHẨM TỪ TIKTOKSHOP
# ==============================================================================

ENHANCED_SCRAPE_JS = r"""
() => {
    const result = {
        title: '',
        price: '',
        original_price: '',
        sold_count: '',
        seller: '',
        description: '',
        images: [],
        desc_images: [],
        variations: []
    };

    const isProductImg = (url) => {
        if (!url || !url.startsWith('http')) return false;
        const lower = url.toLowerCase();
        if (lower.includes('avatar') || lower.includes('icon') || lower.includes('logo') ||
            lower.includes('badge') || lower.includes('flag') || lower.includes('captcha') ||
            lower.includes('verify') || lower.includes('100x100') || lower.includes('64x64') ||
            lower.includes('72x72') || lower.includes('50x50') || lower.includes('.svg') ||
            lower.includes('.gif')) return false;
        return lower.includes('ibyteimg.com') || lower.includes('tiktokcdn.com') || lower.includes('ttcdn');
    };

    const seenImg = new Set();
    const addImg = (u, targetArr) => {
        if (!isProductImg(u)) return;
        const base = u.split('?')[0].replace(/~tplv-[^/]+/, '');
        if (!seenImg.has(base)) {
            seenImg.add(base);
            targetArr.push(u);
        }
    };

    const scripts = document.querySelectorAll('script');
    for (const s of scripts) {
        const text = (s.textContent || '').trim();
        if (!text || text.length < 100) continue;

        let jsonData = null;
        if (s.id === '__MODERN_ROUTER_DATA__' || s.id === '__UNIVERSAL_DATA_FOR_WEB__' || s.id === 'RENDER_DATA' || s.id === '__NEXT_DATA__') {
            try {
                jsonData = JSON.parse(decodeURIComponent(text));
            } catch (e) {
                try { jsonData = JSON.parse(text); } catch (e2) {}
            }
        } else if (text.includes('"product_base"') || text.includes('"productInfo"') || text.includes('"seller"')) {
            const m = text.match(/window\.__[A-Z0-9_]+__\s*=\s*(\{[\s\S]*\})\s*;?$/);
            if (m) {
                try { jsonData = JSON.parse(m[1]); } catch (e) {}
            }
        }

        if (jsonData) {
            const walk = (obj, depth = 0) => {
                if (!obj || typeof obj !== 'object' || depth > 14) return;
                if (Array.isArray(obj)) {
                    for (const item of obj) walk(item, depth + 1);
                    return;
                }

                const pBase = obj.product_base || obj.product_info || ((obj.product_id && obj.title && Array.isArray(obj.images)) ? obj : null);
                if (!result.title && pBase && typeof pBase.title === 'string' && pBase.title.length > 5) {
                    result.title = pBase.title;
                }

                const prObj = (pBase && pBase.price && typeof pBase.price === 'object') ? pBase.price : null;
                if (prObj) {
                    if (!result.price) result.price = prObj.real_price || prObj.sale_price || prObj.format_price || prObj.min_sku_price || '';
                    if (!result.original_price) result.original_price = prObj.original_price || prObj.min_sku_original_price || '';
                }

                if (!result.sold_count && pBase && pBase.sold_count !== undefined && typeof pBase.sold_count !== 'object') {
                    result.sold_count = String(pBase.sold_count);
                }

                if (!result.seller && pBase && pBase.seller && typeof pBase.seller.name === 'string') {
                    result.seller = pBase.seller.name;
                }
                if (!result.seller && obj.shop_info && typeof obj.shop_info.shop_name === 'string') {
                    result.seller = obj.shop_info.shop_name;
                }

                if (pBase && Array.isArray(pBase.images) && result.images.length === 0) {
                    for (const item of pBase.images) {
                        if (!item) continue;
                        const urls = item.url_list || item.urls || (item.url ? [item.url] : []);
                        if (Array.isArray(urls) && urls.length > 0) {
                            addImg(urls[0], result.images);
                        } else if (typeof item === 'string') {
                            addImg(item, result.images);
                        }
                    }
                }

                if (pBase && Array.isArray(pBase.desc_blocks)) {
                    const textBlocks = [];
                    for (const blk of pBase.desc_blocks) {
                        if (!blk) continue;
                        const txt = blk.text || blk.content || (blk.plain_text);
                        if (typeof txt === 'string' && txt.trim()) {
                            textBlocks.push(txt.trim());
                        }
                        if (blk.image && Array.isArray(blk.image.url_list) && blk.image.url_list.length > 0) {
                            addImg(blk.image.url_list[0], result.desc_images);
                        }
                    }
                    if (textBlocks.length > 0 && !result.description) {
                        result.description = textBlocks.join('\n');
                    }
                }

                if (pBase && Array.isArray(pBase.specifications) && pBase.specifications.length > 0 && !result.description) {
                    const specLines = pBase.specifications
                        .filter(sp => sp && sp.name && sp.value)
                        .map(sp => `• ${sp.name}: ${sp.value}`);
                    if (specLines.length > 0) {
                        result.description = 'Thông số sản phẩm:\n' + specLines.join('\n');
                    }
                }

                const rawDesc = (pBase && pBase.description) || obj.rich_text_description;
                if (typeof rawDesc === 'string' && rawDesc.length > 20 && !result.description) {
                    const tmp = document.createElement('div');
                    tmp.innerHTML = rawDesc;
                    result.description = (tmp.innerText || tmp.textContent || '').trim();
                    tmp.querySelectorAll('img').forEach(img => {
                        const u = img.src || img.getAttribute('data-src') || '';
                        addImg(u, result.desc_images);
                    });
                }

                const props = (pBase && pBase.sale_props) || obj.sale_props;
                if (Array.isArray(props) && props.length > 0 && result.variations.length === 0) {
                    for (const p of props) {
                        if (p && p.prop_name) {
                            const vals = (p.sale_prop_values || []).map(v => v.prop_value || v.name || '').filter(Boolean);
                            result.variations.push({ group_name: p.prop_name, options: vals });
                        }
                    }
                }

                for (const k of Object.keys(obj)) {
                    walk(obj[k], depth + 1);
                }
            };
            walk(jsonData, 0);
        }
    }

    if (!result.title) {
        const titleSelectors = [
            'h1', '[data-testid*="product-title"]', '[class*="title-v2"]',
            '[class*="product-title"]', '[class*="pdp-title"]', 'span[class*="H2-Semibold"]'
        ];
        for (const sel of titleSelectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText && el.innerText.trim().length > 5) {
                result.title = el.innerText.trim();
                break;
            }
        }
    }

    if (!result.price) {
        const priceSelectors = ['[class*="price"] span', '[data-testid*="price"]', '[class*="Price"]'];
        for (const sel of priceSelectors) {
            for (const el of document.querySelectorAll(sel)) {
                const t = (el.innerText || '').trim();
                if (t && (t.includes('₫') || t.includes('VND') || /^\d[\d.,]+$/.test(t)) && t.length < 30) {
                    result.price = t;
                    break;
                }
            }
            if (result.price) break;
        }
    }

    if (!result.sold_count) {
        const allSpans = document.querySelectorAll('span, div');
        for (const el of allSpans) {
            if (el.children.length > 0) continue;
            const t = (el.innerText || '').trim();
            if (/^(\d+([.,]\d+)?\s*[kKmM]?\+?)\s*(đã bán|sold)$/i.test(t) || /^(đã bán|sold)\s*(\d+([.,]\d+)?\s*[kKmM]?\+?)$/i.test(t)) {
                result.sold_count = t;
                break;
            }
        }
    }

    if (!result.seller) {
        const sellerSelectors = [
            '[data-testid*="shop-name"]', '[class*="shop-name"]', '[class*="seller-name"]',
            'a[href*="/shop/"] span', '[class*="ShopName"]'
        ];
        for (const sel of sellerSelectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText && el.innerText.trim().length > 1 && el.innerText.trim().length < 80) {
                result.seller = el.innerText.trim();
                break;
            }
        }
    }

    if (result.images.length === 0) {
        document.querySelectorAll('img').forEach(img => {
            const src = img.src || img.getAttribute('data-src') || '';
            const w = img.naturalWidth || img.width || 0;
            if (w > 0 && w < 180) return;
            addImg(src, result.images);
        });
    }

    if (!result.description) {
        const descSelectors = ['[data-testid*="description"]', '[class*="description-content"]', '[class*="product-desc"]', '[class*="pdp-description"]'];
        for (const sel of descSelectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText && el.innerText.trim().length > 20) {
                result.description = el.innerText.trim();
                break;
            }
        }
    }

    if (!result.title) {
        const ogTitle = document.querySelector('meta[property="og:title"]');
        if (ogTitle && ogTitle.content) result.title = ogTitle.content.replace(/\s*\|\s*TikTok.*$/i, '').trim();
    }

    return result;
}
"""


def _find_chrome_exe() -> str | None:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _resolve_tiktokshop_profile_dir() -> Path:
    candidates = [
        config.TIKTOK_SHOP_PROFILE_DIR,
        Path.home() / ".tiktok_img_tool" / "profiles" / "tiktok_chrome_profile",
    ]
    for p in candidates:
        try:
            if p.exists() and (p / "Default").exists():
                return p
        except Exception:
            continue
    config.TIKTOK_SHOP_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return config.TIKTOK_SHOP_PROFILE_DIR


def is_chrome_cdp_alive(port: int | None = None) -> bool:
    port = port or config.CHROME_DEBUG_PORT
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_chrome_cdp_running(log_fn: LogFn = _default_log) -> bool:
    port = config.CHROME_DEBUG_PORT
    if is_chrome_cdp_alive(port):
        return True

    chrome_exe = _find_chrome_exe()
    if not chrome_exe:
        log_fn("❌ Không tìm thấy Google Chrome trên máy tính.")
        return False

    profile_dir = _resolve_tiktokshop_profile_dir()

    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            if (proc.info.get("name") or "").lower() == "chrome.exe":
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "tiktok_chrome_profile" in cmdline and f"--remote-debugging-port={port}" not in cmdline:
                    proc.terminate()
    except Exception:
        pass

    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_file = profile_dir / lock_name
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass

    log_fn(f"🌐 Đang khởi động Chrome TikTokShop (Profile: {profile_dir.name}, Port: {port})...")

    cmd = [
        chrome_exe,
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
        "--disable-blink-features=AutomationControlled",
        "https://www.tiktok.com",
    ]
    creation_flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)

    for _ in range(24):
        time.sleep(0.5)
        if is_chrome_cdp_alive(port):
            log_fn("✅ Đã kết nối Chrome TikTokShop qua cổng CDP 9222!")
            time.sleep(1.0)
            return True

    log_fn("⚠️ Không kết nối được cổng CDP 9222, sẽ thử chế độ Playwright Persistent Context.")
    return False


def _parse_money_to_float(raw: Any) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw or "").strip()
    if not s:
        return 0.0
    if "-" in s:
        s = s.split("-")[0].strip()
    digits = re.sub(r"[^\d]", "", s)
    if digits:
        try:
            return float(digits)
        except ValueError:
            pass
    return 0.0


def _parse_sold_count(raw: Any) -> tuple[int, str]:
    if isinstance(raw, int):
        return raw, str(raw)
    s = str(raw or "").strip()
    if not s:
        return 0, ""
    low = s.lower().replace("đã bán", "").replace("sold", "").replace("+", "").strip()
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*([km]?)", low)
    if not m:
        return 0, s
    num_str, suffix = m.group(1), m.group(2)
    if suffix == "k":
        val = int(float(num_str.replace(",", ".")) * 1000)
    elif suffix == "m":
        val = int(float(num_str.replace(",", ".")) * 1_000_000)
    else:
        val = int(re.sub(r"[^\d]", "", num_str) or "0")
    return val, s


def _lookup_cached_tiktokshop_product(pid: str) -> dict[str, Any] | None:
    json_path = config.TIKTOK_SHOP_DIR / "crawled_products" / "products.json"
    if not json_path.exists():
        return None
    try:
        items = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and str(item.get("product_id", "")).strip() == pid:
                    return item
    except Exception:
        pass
    return None


_BROWSER_CRAWL_LOCK = threading.Lock()


def fetch_product_details_via_browser(
    product_id_or_url: str,
    download_images: bool = True,
    log_fn: LogFn = _default_log,
) -> dict[str, Any]:
    """Cách 2: Mở trực tiếp trình duyệt Chrome TikTokShop + tự động giải Captcha bằng model BoxPhone,
    sau đó bóc tách thông tin & tải toàn bộ ảnh sản phẩm về `config.PRODUCT_IMAGES_DIR / pid`.
    """
    raw = (product_id_or_url or "").strip()
    m = re.search(r"(?:pdp/|/product/|/products/|^)(\d{15,22})", raw)
    pid = m.group(1) if m else (raw if raw.isdigit() else "")
    if not pid:
        return {"success": False, "error": f"Không nhận diện được ID sản phẩm hợp lệ từ: {raw}"}

    urls_to_try = [
        f"https://www.tiktok.com/shop/pdp/{pid}",
        f"https://shop.tiktok.com/vn/pdp/{pid}",
    ]
    pdp_url = f"https://shop.tiktok.com/vn/pdp/{pid}"

    scraped: dict[str, Any] = {}
    solver = BoxPhoneCaptchaSolver(log_fn=log_fn)

    with _BROWSER_CRAWL_LOCK:
        cdp_ready = ensure_chrome_cdp_running(log_fn=log_fn)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = None
                ctx = None
                close_ctx_when_done = False

                if cdp_ready:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{config.CHROME_DEBUG_PORT}")
                    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                else:
                    profile_dir = _resolve_tiktokshop_profile_dir()
                    ctx = p.chromium.launch_persistent_context(
                        user_data_dir=str(profile_dir),
                        channel="chrome",
                        headless=False,
                        args=[
                            "--no-first-run",
                            "--no-default-browser-check",
                            "--disable-blink-features=AutomationControlled",
                        ],
                    )
                    close_ctx_when_done = True

                page = ctx.new_page()
                try:
                    for idx, target_url in enumerate(urls_to_try):
                        log_fn(f"🌐 [Cách 2 - Browser] Đang mở trang sản phẩm: {target_url}")
                        try:
                            page.goto(target_url, wait_until="domcontentloaded", timeout=28000)
                        except Exception as nav_exc:
                            log_fn(f"⚠️ Trang tải chậm ({nav_exc}), tiếp tục kiểm tra DOM...")

                        time.sleep(2.5)
                        solver.check_and_solve(page, max_attempts=5)

                        try:
                            for _ in range(4):
                                page.evaluate("window.scrollBy(0, 550)")
                                time.sleep(0.45)
                            page.evaluate("window.scrollTo(0, 0)")
                            time.sleep(0.6)
                        except Exception:
                            pass

                        solver.check_and_solve(page, max_attempts=3)

                        data = page.evaluate(ENHANCED_SCRAPE_JS)
                        if isinstance(data, dict):
                            title_cand = str(data.get("title") or "").strip()
                            imgs_cand = data.get("images") or []
                            if title_cand.lower() in ("tiktok", "tiktok shop", "security check", "verify"):
                                title_cand = ""
                                data["title"] = ""

                            if title_cand or len(imgs_cand) > 0:
                                scraped = data
                                break
                            elif idx == 0:
                                log_fn("🔄 Thử đổi sang cổng URL phụ (shop.tiktok.com/vn/pdp)...")
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
                    if close_ctx_when_done and ctx is not None:
                        try:
                            ctx.close()
                        except Exception:
                            pass
        except Exception as exc:
            log_fn(f"⚠️ Lỗi khi điều khiển trình duyệt Playwright: {exc}")

    title = str(scraped.get("title") or "").strip()
    images: list[str] = [str(u).strip() for u in (scraped.get("images") or []) if str(u).strip()]

    if not title and not images:
        cached = _lookup_cached_tiktokshop_product(pid)
        if cached:
            log_fn(f"📦 Tìm thấy dữ liệu sản phẩm {pid} trong kho TiktokShop local cache!")
            title = str(cached.get("title") or "").strip()
            images = [str(u).strip() for u in (cached.get("image_urls") or []) if str(u).strip()]
            scraped = {
                "title": title,
                "price": cached.get("price") or "",
                "original_price": "",
                "sold_count": "",
                "seller": cached.get("seller") or "",
                "description": cached.get("description") or "",
                "images": images,
                "desc_images": [],
                "variations": [],
            }

    if not title and not images:
        return {
            "success": False,
            "product_id": pid,
            "error": "Cách 2 (Trình duyệt TikTokShop) không lấy được tiêu đề/ảnh sản phẩm (có thể sản phẩm đã bị ẩn hoặc cần kiểm tra đăng nhập Chrome).",
        }

    shop_name = str(scraped.get("seller") or "").strip()
    price = int(_parse_money_to_float(scraped.get("price")))
    orig_price = int(_parse_money_to_float(scraped.get("original_price")))
    if 0 <= price <= 100 and orig_price > 1000:
        price = orig_price
    sold_count, sold_label = _parse_sold_count(scraped.get("sold_count"))
    desc = str(scraped.get("description") or "").strip()
    desc_images: list[str] = [str(u).strip() for u in (scraped.get("desc_images") or []) if str(u).strip()]
    variations: list[Any] = scraped.get("variations") if isinstance(scraped.get("variations"), list) else []

    if not images and desc_images:
        images = list(desc_images[:10])

    primary_image = images[0] if images else ""
    local_thumb_path = ""
    local_images: list[str] = []

    if download_images and pid:
        prod_dir = config.PRODUCT_IMAGES_DIR / pid
        images_dir = prod_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        thumb_file = prod_dir / "thumb.webp"

        headers_dl = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.tiktok.com/",
        }

        for idx, img_url in enumerate(images[:15]):
            target_file = images_dir / f"img_{idx}.webp"
            if not target_file.exists() or target_file.stat().st_size < 200:
                try:
                    req_img = urllib.request.Request(img_url, headers=headers_dl)
                    with urllib.request.urlopen(req_img, timeout=15) as r_img:
                        img_bytes = r_img.read()
                        if len(img_bytes) > 200:
                            target_file.write_bytes(img_bytes)
                            if idx == 0 and (not thumb_file.exists() or thumb_file.stat().st_size < 200):
                                thumb_file.write_bytes(img_bytes)
                except Exception:
                    pass
            if target_file.is_file() and target_file.stat().st_size > 200:
                local_images.append(str(target_file))

        if thumb_file.exists() and thumb_file.stat().st_size > 200:
            local_thumb_path = f"product_images/{pid}/thumb.webp"

        info_file = prod_dir / "info.json"
        try:
            info_payload = {
                "product_id": pid,
                "pdp_url": pdp_url,
                "title": title,
                "shop_name": shop_name,
                "price": price,
                "original_price": orig_price,
                "sold_count": sold_count,
                "sold_count_label": sold_label,
                "description": desc,
                "images": images,
                "description_images": desc_images,
                "variations": variations,
                "local_images": local_images,
                "source": "browser_tiktokshop",
                "fetched_at": time.time(),
            }
            info_file.write_text(json.dumps(info_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    log_fn(
        f"✨ [Cách 2 - Browser] Đã tải thành công SP {pid}: "
        f"{title[:45]}... ({len(images)} ảnh, giá {price:,.0f}₫)"
    )

    return {
        "success": True,
        "product_id": pid,
        "pdp_url": pdp_url,
        "title": title,
        "shop_name": shop_name,
        "price": price,
        "original_price": orig_price,
        "sold_count": sold_count,
        "sold_count_label": sold_label,
        "description": desc,
        "images": images,
        "desc_images": desc_images,
        "variations": variations,
        "image_url": primary_image,
        "local_thumb": local_thumb_path,
        "total_images": len(images),
        "source": "browser_tiktokshop",
    }

