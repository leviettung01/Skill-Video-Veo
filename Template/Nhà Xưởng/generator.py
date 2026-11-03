# -*- coding: utf-8 -*-
"""
Generator cho Template "Nhà Xưởng" (Template/Nhà Xưởng/generator.py)
Tự động phân tích thông tin sản phẩm (info.json + ảnh trong product_images/)
và sinh ra prompts.json + spec_v*.json chuẩn cho pipeline tạo ảnh 2K & video 1080p.
"""
import os
import re
import glob
import json
import math
from PIL import Image

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(TEMPLATE_DIR, "template_config.json")


def load_template_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _parse_price_k(price_raw) -> tuple:
    """Trả về (price_k_str, ceil_anchor_k_str, high1_str, high2_str). VD: ('69K', '70K', '200', '150')."""
    s = str(price_raw or "").strip()
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return ("69K", "70K", "200", "150")
    val = int(digits)
    if val >= 1000:
        k = max(10, round(val / 1000))
    else:
        k = max(10, val)
    ceil_k = int(math.ceil((k + 1) / 10.0) * 10)
    high2 = max(ceil_k + 50, 150)
    high1 = max(high2 + 50, 200)
    return (f"{k}K", f"{ceil_k}K", str(high1), str(high2))


def _extract_short_vn_name(title: str) -> str:
    """Rút gọn tên sản phẩm tiếng Việt để đọc thoại tự nhiên (khoảng 5-8 từ)."""
    t = (title or "").strip()
    t = re.sub(r"\[[^\]]*\]|\([^\)]*\)", " ", t)
    t = re.sub(r"-\s*[A-Za-z0-9_]+$", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return "sản phẩm chính hãng tại xưởng"
    words = t.split()
    short = " ".join(words[:7])
    short_lower = short.lower()
    short_lower = re.sub(r"\b304\b", "ba lẻ tư", short_lower)
    short_lower = re.sub(r"\b5kg\b", "năm ký", short_lower)
    short_lower = re.sub(r"\b10kg\b", "mười ký", short_lower)
    return short_lower.strip(" ,.-")


def _infer_product_en_and_scale(title: str, desc: str) -> tuple:
    """Suy luận mô tả loại sản phẩm và kích thước cầm tay bằng tiếng Anh cho Prompt Ảnh Ref 2K."""
    text = f"{title} {desc}".lower()
    mapping = [
        (["cân tiểu ly", "cân điện tử", "cân nhà bếp"], "compact digital kitchen scale", "true-to-life compact 18x14cm hand-held scale relative to her hands and body"),
        (["thắt lưng", "dây nịt", "belt"], "coiled men's belt", "true-to-life palm-sized coiled belt scale relative to her hands and body"),
        (["kính", "mắt kính", "gọng kính"], "folded eyeglasses frame", "true-to-life palm-sized eyewear frame relative to her hands and body"),
        (["ví", "bóp", "wallet"], "compact leather wallet", "true-to-life palm-sized wallet relative to her hands and body"),
        (["túi", "balo", "cặp"], "handbag / backpack", "true-to-life natural bag proportion relative to her hands and body"),
        (["đồng hồ", "watch"], "wristwatch", "true-to-life compact wristwatch scale relative to her hands and body"),
        (["tai nghe", "loa", "bluetooth"], "compact audio device", "true-to-life palm-sized gadget scale relative to her hands and body"),
        (["bình giữ nhiệt", "cốc", "ly"], "insulated tumbler cup", "true-to-life hand-held tumbler size relative to her hands and body"),
        (["máy cạo râu", "tông đơ", "máy sấy", "bàn chải"], "compact personal care appliance", "true-to-life compact hand-held device relative to her hands and body"),
        (["áo", "quần", "váy", "đầm"], "neatly folded garment item", "true-to-life natural clothing item proportion relative to her hands and body"),
        (["giày", "dép", "sandal"], "single footwear item", "true-to-life natural shoe size relative to her hands and body"),
        (["nồi", "chảo", "bếp", "máy xay"], "kitchen appliance item", "true-to-life realistic household appliance size relative to her hands and body"),
        (["kem", "serum", "sữa rửa mặt", "nước hoa", "son", "mỹ phẩm"], "cosmetic bottle / skincare item", "true-to-life palm-sized cosmetic container relative to her hands and body"),
    ]
    for keywords, prod_en, scale_en in mapping:
        if any(kw in text for kw in keywords):
            return prod_en, scale_en
    return "product item", "true-to-life natural hand-held scale relative to her hands and body"


def _split_into_karaoke_phrases(text: str, max_chars: int = 28) -> list:
    """
    Tách câu thoại tiếng Việt thành danh sách các phrase [TEXT_IN_HOA <= 28 ký tự, số_từ_nói].
    """
    clean = re.sub(r"[\"“”]", "", text)
    clean = re.sub(r"[,.;:!?\-]+", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return [["ƯU ĐÃI TẬN XƯỞNG HÔM NAY", 6]]

    words = clean.split()
    phrases = []
    cur_words = []

    def _spoken_word_count(w_list):
        cnt = 0
        for w in w_list:
            wu = w.upper()
            if wu in ("200", "300", "400", "500"):
                cnt += 2
            elif wu in ("150", "250", "350"):
                cnt += 3
            elif re.match(r"^\d+K$", wu):
                cnt += 2
            else:
                cnt += 1
        return max(1, cnt)

    for w in words:
        wu = w.upper()
        candidate = " ".join(cur_words + [wu])
        if len(candidate) <= max_chars and len(cur_words) < 6:
            cur_words.append(wu)
        else:
            if cur_words:
                phrases.append([" ".join(cur_words), _spoken_word_count(cur_words)])
            cur_words = [wu[:max_chars]]
    if cur_words:
        phrases.append([" ".join(cur_words), _spoken_word_count(cur_words)])
    return phrases


def _extract_usp_lines(title: str, desc: str, short_name: str) -> list:
    """Trích xuất 3 câu USP ngắn gọn từ mô tả sản phẩm cho Cảnh 3."""
    raw_text = f"{desc or ''}. {title or ''}"
    sents = [s.strip() for s in re.split(r"[.\n•\-]+", raw_text) if len(s.strip()) > 15]
    usp_pairs = [
        (
            "Hàng chuẩn xưởng chất lượng cao, gia công tỉ mỉ bền đẹp từng chi tiết.",
            "Đóng gói kỹ lưỡng đầy đủ phụ kiện, các bác chốt ngay giúp em.",
        ),
        (
            "Thiết kế chắc chắn hiện đại, sử dụng tiện lợi và cực kỳ bền bỉ.",
            "Hàng xuất trực tiếp từ nhà máy, kiểm tra kỹ từng sản phẩm trước khi giao.",
        ),
        (
            "Chất liệu cao cấp chọn lọc kỹ, hoàn thiện sắc nét chuẩn hàng chính hãng.",
            "Mua dùng hay làm quà đều rất hợp lý, cam kết y hình từ nhà xưởng.",
        ),
    ]
    if sents:
        cleaned_s = []
        for s in sents[:6]:
            s_clean = re.sub(r"\s+", " ", s).strip()
            s_Words = s_clean.split()
            if 6 <= len(s_Words) <= 18:
                cleaned_s.append(" ".join(s_Words[:14]))
        if len(cleaned_s) >= 1:
            u0 = cleaned_s[0].rstrip(",.;") + "."
            u0 = re.sub(r"\b304\b", "ba lẻ tư", u0, flags=re.I)
            u0 = re.sub(r"\b10kg\b", "mười ký", u0, flags=re.I)
            u0 = re.sub(r"\b5kg\b", "năm ký", u0, flags=re.I)
            usp_pairs[0] = (u0, usp_pairs[0][1])
    return usp_pairs


def select_best_product_images(prod_img_dir: str) -> tuple:
    """Chọn primary_product_refs (1 ảnh đơn rõ nét) và slide_overlay_files (tối đa 5 ảnh)."""
    jpgs = sorted(
        glob.glob(os.path.join(prod_img_dir, "prod_*.jpg")),
        key=lambda p: int(re.findall(r"prod_(\d+)", os.path.basename(p))[0]) if re.findall(r"prod_(\d+)", os.path.basename(p)) else 999,
    )
    if not jpgs:
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            jpgs.extend(sorted(glob.glob(os.path.join(prod_img_dir, ext))))
    if not jpgs:
        return (["prod_1.jpg"], ["prod_1.jpg"])

    valid_rels = []
    for p in jpgs:
        try:
            if os.path.getsize(p) > 3000:
                valid_rels.append(os.path.basename(p))
        except OSError:
            pass
    if not valid_rels:
        valid_rels = [os.path.basename(jpgs[0])]

    primary_rel = valid_rels[0]
    slides = valid_rels[:5]
    return ([primary_rel], slides)


def _adapt_dialect_lines(timed_lines: list, region: str) -> list:
    if (region or "").lower() != "south":
        return timed_lines
    out = []
    for ln in timed_lines:
        s = ln
        s = re.sub(r"\bcác bác\b", "cả nhà", s, flags=re.I)
        s = re.sub(r"\bCác bác\b", "Cả nhà", s)
        s = re.sub(r"\bnhé\b", "nha", s, flags=re.I)
        s = re.sub(r"\bđó ạ\b", "luôn nghen", s, flags=re.I)
        s = re.sub(r"\bgiúp em ạ\b", "giúp em nha", s, flags=re.I)
        s = re.sub(r"\bthôi ạ\b", "thôi nghen", s, flags=re.I)
        out.append(s)
    return out


def make_video_prompt(scene_idx: int, timed_lines: list, scene_actions: dict, voice_prompt_en: str = "") -> str:
    action_str = scene_actions.get(str(scene_idx)) or scene_actions.get(1) or (
        "The woman looks directly at the camera with a confident, energetic expression, "
        "naturally speaking while holding the exact product from the reference image steady at waist level, "
        "tilting it slightly toward the camera to showcase it, then keeping the presenting pose at the end."
    )
    voice_block = "\n".join(timed_lines)
    voice_dir = f" ({voice_prompt_en})" if voice_prompt_en else ""
    return (
        "A 10-second vertical 9:16 video starting directly from the provided reference image, "
        "one continuous medium shot, front-facing camera. Keep the character, the exact product in her hands, "
        "the items on the table, and the background 100% unchanged from the reference image — "
        "do not alter, redesign, or replace the product's shape, color, pattern, or logo.\n\n"
        f"ACTION: {action_str}\n\n"
        f"VOICE{voice_dir} — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment "
        "fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — "
        "no repetition, no looping, no added words, then stay silent:\n"
        f"{voice_block}\n\n"
        "No background music, no watermark.\n"
        "Negative: changed product, altered product design, repeating voice, looping dialogue, second voice pass, rushed reading, changed face"
    )


def generate_project_from_template(
    pid: str,
    pdir: str,
    info_data: dict,
    characters_data: dict,
    videos_per_character: int = None,
    primary_product_refs: list = None,
    slide_overlay_files: list = None,
) -> dict:
    """
    Sinh prompts.json và spec_v*.json trong thư mục projects/<pid>/ theo Template Nhà Xưởng.
    Hỗ trợ tuỳ chỉnh số lượng video trên mỗi nhân vật (videos_per_character).
    """
    cfg = load_template_config()
    scene_actions = cfg.get("scene_actions", {})
    char_presets_map = cfg.get("character_presets", {})

    os.makedirs(pdir, exist_ok=True)
    prod_img_dir = os.path.join(pdir, "product_images")
    os.makedirs(prod_img_dir, exist_ok=True)

    auto_primary, auto_slides = select_best_product_images(prod_img_dir)
    primary_refs = primary_product_refs if primary_product_refs else auto_primary
    slide_overlays = slide_overlay_files if slide_overlay_files else auto_slides

    pname = (
        info_data.get("name")
        or info_data.get("title")
        or info_data.get("product_name")
        or f"Sản phẩm {pid}"
    )
    desc = info_data.get("description") or ""
    price_raw = info_data.get("price") or info_data.get("price_str") or "69.000₫"

    price_k, ceil_k, high1, high2 = _parse_price_k(price_raw)
    short_vn = _extract_short_vn_name(pname)
    prod_type_en, prod_scale_en = _infer_product_en_and_scale(pname, desc)
    usp_pairs = _extract_usp_lines(pname, desc, short_vn)

    chars_dict = characters_data.get("characters", {})
    voices_dict = characters_data.get("voices", {})
    default_vpc = int(
        videos_per_character
        or characters_data.get("default_videos_per_character")
        or cfg.get("default_videos_per_character", 3)
    )

    hook_templates = [
        (
            '[0.0-3.7s] "Cái này là cho các bác này. Sàn người ta cho chứ không phải bán nữa rồi."',
            f'[3.7-7.8s] "Siêu phẩm {short_vn} đang được trợ giá cực rẻ tại xưởng,"',
            '[7.8-10.0s] "các bác bấm giỏ hàng xem giá giúp em nhé."',
        ),
        (
            f'[0.0-4.0s] "{price_k} cho siêu phẩm {short_vn} này các bác ơi."',
            '[4.0-7.8s] "Ở đâu bán giá này em cũng bái phục, tận xưởng không thể rẻ vậy."',
            '[7.8-10.0s] "Hôm nay kênh em được trợ giá rất rẻ luôn."',
        ),
        (
            '[0.0-3.5s] "Các bác khoan hãy lướt qua video này kẻo tiếc hùi hụi luôn nha."',
            f'[3.5-7.4s] "Tại tổng kho hôm nay mẫu {short_vn} đang xả trợ giá cực sâu,"',
            '[7.4-10.0s] "bấm ngay vào giỏ hàng kiểm tra giá giúp em nhé."',
        ),
        (
            '[0.0-3.5s] "Đừng mua ở ngoài làm gì cho đắt đỏ tốn kém các bác ơi."',
            f'[3.5-7.4s] "Lấy trực tiếp tại xưởng mẫu {short_vn} hôm nay rẻ bất ngờ,"',
            '[7.4-10.0s] "các bác mở giỏ hàng góc trái xem thử ngay nhé."',
        ),
        (
            f'[0.0-3.6s] "Tin vui cho các bác đang tìm {short_vn} chuẩn xưởng giá bình dân."',
            '[3.6-7.4s] "Lô mới xuất xưởng hôm nay đang được sàn tài trợ giá cực tốt,"',
            '[7.4-10.0s] "các bác ấn ngay vào giỏ hàng xem ưu đãi nhé."',
        ),
        (
            '[0.0-3.5s] "Thật sự mức giá hôm nay làm em đứng tại xưởng cũng bất ngờ."',
            f'[3.5-7.4s] "Nguyên một siêu phẩm {short_vn} chuẩn xịn mà giá chỉ bằng bữa sáng,"',
            '[7.4-10.0s] "các bác bấm giỏ hàng bên dưới xem ngay nha."',
        ),
    ]

    scene2_templates = [
        (
            f'[0.0-3.6s] "Giá không phải {high1}, không phải {high2}, {ceil_k} cũng không luôn."',
            '[3.6-6.0s] "Mỗi tài khoản các bác sẽ thấy một giá khác nhau."',
            f'[6.0-10.0s] "Bấm giỏ hàng góc trái nha, nếu thấy giá dưới {ceil_k} thì săn liền giúp em ạ."',
        ),
        (
            f'[0.0-3.7s] "Giá không phải {high1}, không phải {high2}, {ceil_k} cũng không luôn."',
            '[3.7-5.7s] "Mà mỗi tài khoản một giá khác nhau nha."',
            f'[5.7-10.0s] "Các bác bấm giỏ hàng góc trái, thấy dưới {ceil_k} thì săn liền giúp em ạ."',
        ),
        (
            f'[0.0-3.6s] "Giá không phải {high1}, không phải {high2}, {ceil_k} cũng không luôn."',
            '[3.6-6.2s] "Tùy từng tài khoản mà sàn áp mức giảm khác nhau."',
            f'[6.2-10.0s] "Các bác mở giỏ hàng góc trái, thấy dưới {ceil_k} là chốt đơn liền tay nha."',
        ),
    ]

    scene3_closings = [
        '[7.0-10.0s] "ưu đãi chớp nhoáng hôm nay, hết là về giá gốc đó ạ."',
        '[7.0-10.0s] "số lượng ưu đãi có hạn nên các bác đặt sớm nhé."',
        '[7.0-10.0s] "chương trình chỉ mở trong hôm nay thôi ạ."',
    ]

    videos_json = {}
    enabled_chars = [
        (ck, cval)
        for ck, cval in chars_dict.items()
        if cval.get("enabled", True) is not False
    ]
    if not enabled_chars:
        enabled_chars = list(chars_dict.items())

    global_var_counter = 0
    for char_idx, (ck, cval) in enumerate(enabled_chars):
        char_vpc = int(
            videos_per_character
            if videos_per_character is not None
            else cval.get("videos_per_character", default_vpc)
        )
        char_vpc = max(1, min(5, char_vpc))
        voice_key = cval.get("default_voice", ck)
        v_obj = voices_dict.get(voice_key, {})
        voice_id = cval.get("voice_id") or v_obj.get("voice_id", "")
        voice_name = cval.get("voice_name") or v_obj.get("name", "")
        voice_region = cval.get("voice_region") or v_obj.get("region", "north")
        voice_prompt_en = cval.get("voice_prompt_en") or v_obj.get("voice_prompt_en", "")
        char_id = cval.get("character_id", "")
        proj_id = cval.get("project_id", "")
        appearance_en = cval.get("appearance_en") or (
            "shoulder-length layered black hair, black-framed glasses, identical face"
            if "nv1" in ck.lower()
            else "long wavy dark-brown hair in a high ponytail with colourful pastel hair clips, identical face, no glasses"
        )

        presets = char_presets_map.get(ck) or char_presets_map.get("nv1" if char_idx % 2 == 0 else "nv2", [])

        for v_idx in range(1, char_vpc + 1):
            global_var_counter += 1
            preset = presets[(v_idx - 1) % len(presets)] if presets else {}
            if ck == "nv1" and v_idx <= 5:
                vkey = f"v{(v_idx - 1) * 2 + 1}"
            elif ck == "nv2" and v_idx <= 5:
                vkey = f"v{v_idx * 2}"
            else:
                vkey = f"{ck}_v{v_idx}"

            char_v = f"{ck}_v{v_idx}"
            hook_title = preset.get("hook_title") or f"{ck.upper()} - Kịch bản {v_idx}"
            style_label = preset.get("style") or "Xưởng sản xuất & Kiểm định chất lượng"
            outfit_en = preset.get("outfit_en") or "wearing a polite professional blazer over a collared shirt and dark trousers"
            setting_en = preset.get("setting_en") or "standing behind a display worktable in a modern manufacturing and inspection facility"

            ref_img_prompt = (
                "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
                f"the exact same woman from the character reference ({appearance_en}), "
                f"{outfit_en}, {setting_en}. "
                f"She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact {prod_type_en} from the product reference image in her hands at waist level facing the camera "
                f"({prod_scale_en}, NOT oversized), with neat retail packaging boxes on the worktable beside her. "
                "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
            )

            h_seg1, h_seg2, h_seg3 = hook_templates[(global_var_counter - 1) % len(hook_templates)]
            s2_seg1, s2_seg2, s2_seg3 = scene2_templates[(global_var_counter - 1) % len(scene2_templates)]
            u_line1, u_line2 = usp_pairs[(global_var_counter - 1) % len(usp_pairs)]
            s3_seg1 = f'[0.0-3.7s] "{u_line1}"'
            s3_seg2 = f'[3.7-7.0s] "{u_line2}"'
            s3_seg3 = scene3_closings[(global_var_counter - 1) % len(scene3_closings)]

            raw_scenes = [
                (1, f"{vkey}_s1", f"{vkey}_s1.mp4", _adapt_dialect_lines([h_seg1, h_seg2, h_seg3], voice_region)),
                (2, f"{vkey}_s2", f"{vkey}_s2.mp4", _adapt_dialect_lines([s2_seg1, s2_seg2, s2_seg3], voice_region)),
                (3, f"{vkey}_s3", f"{vkey}_s3.mp4", _adapt_dialect_lines([s3_seg1, s3_seg2, s3_seg3], voice_region)),
            ]

            scenes_list = []
            spec_scenes = []
            for sc_num, sc_id, sc_file, timed_lines in raw_scenes:
                joined_dialogue = " ".join(
                    re.sub(r"^\[[^\]]+\]\s*", "", ln).strip().strip('"')
                    for ln in timed_lines
                )
                phrases = _split_into_karaoke_phrases(joined_dialogue, max_chars=28)
                total_w = sum(w for _, w in phrases)
                v_prompt = make_video_prompt(sc_num, timed_lines, scene_actions, voice_prompt_en=voice_prompt_en)
                scenes_list.append({
                    "id": sc_id,
                    "file": sc_file,
                    "words": total_w,
                    "prompt": v_prompt,
                })
                spec_scenes.append({
                    "file": sc_file,
                    "words": total_w,
                    "phrases": phrases,
                })

            ref_img_name = f"{vkey}-refimg.jpg"
            videos_json[vkey] = {
                "char_v": char_v,
                "character": ck,
                "hook_title": hook_title,
                "style": style_label,
                "template_id": cfg.get("id", "nha_xuong"),
                "template_name": cfg.get("folder_name", "Nhà Xưởng"),
                "character_id": char_id,
                "project_id": proj_id,
                "voice_id": voice_id,
                "voice_name": voice_name,
                "ref_image": ref_img_name,
                "ref_image_prompt": ref_img_prompt,
                "primary_product_refs": primary_refs,
                "slide_overlay_files": slide_overlays,
                "scenes": scenes_list,
            }

            spec_obj = {
                "scenes": spec_scenes,
                "overlays": [os.path.join("product_images", f) for f in slide_overlays],
                "output": f"{pid}_{char_v}.mp4",
            }
            with open(os.path.join(pdir, f"spec_{vkey}.json"), "w", encoding="utf-8") as f:
                json.dump(spec_obj, f, ensure_ascii=False, indent=2)

    prompts_obj = {
        "product_id": pid,
        "product_name": pname,
        "template_id": cfg.get("id", "nha_xuong"),
        "template_name": cfg.get("folder_name", "Nhà Xưởng"),
        "videos_per_character": default_vpc,
        "primary_product_refs": primary_refs,
        "slide_overlay_files": slide_overlays,
        "ref_img_prompt_nv1": videos_json.get("v1", {}).get("ref_image_prompt", ""),
        "ref_img_prompt_nv2": videos_json.get("v2", {}).get("ref_image_prompt", ""),
        "videos": videos_json,
    }
    with open(os.path.join(pdir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_obj, f, ensure_ascii=False, indent=2)

    return prompts_obj

