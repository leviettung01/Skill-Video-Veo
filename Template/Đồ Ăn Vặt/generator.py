# -*- coding: utf-8 -*-
"""
Generator cho Template "Đồ Ăn Vặt" & Biến thể "Đồ Ăn Vặt POV (Có Voice)"
Xây dựng dựa trên:
- role_skills/DoAnVat.MD (Random 8 Background Pool + Creative Culinary Staging + Uncropped Original Product Images)
- role_skills/DoAnVat_POV_Voice.MD (POV Tabletop + Selectable Voice ID + Timeline Visual & Voice Sync [0.0-3.5s], [3.5-7.0s], [7.0-10.0s] + TikTok Policy Safe + 60 FPS Karaoke Subtitles)
"""
import os
import re
import glob
import json
import random

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(TEMPLATE_DIR, "template_config.json")
SKILL_ROOT = os.path.dirname(os.path.dirname(TEMPLATE_DIR))
VOICES_JSON_PATH = os.path.join(SKILL_ROOT, "flow_final_pipeline", "voices_and_characters.json")

# Danh sách 8 Background Đồ Ăn Vặt chuẩn Role Skill DoAnVat (Random ngẫu nhiên cho mỗi video, giữ cố định trong 3 scene của video đó)
RANDOM_BG_POOL = [
    {
        "id": "hanoi_snack_shop",
        "label": "Quầy Tiệm Ăn Vặt Hiện Đại Hà Nội",
        "block": (
            "Setting: a bright modern Vietnamese snack shop in Hanoi, large floor-to-ceiling glass storefront windows behind, "
            "green trees visible outside, passing motorbikes and cars softly blurred beyond the glass, clean glass display cabinets "
            "and neatly arranged product shelves inside, clean light-toned counter in the foreground, soft natural daytime light "
            "coming from the left through the glass, gentle realistic reflections on the glass surfaces, premium tidy warm inviting atmosphere. "
            "Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "genz_study_desk",
        "label": "Góc Bàn Học Gen Z Bên Cửa Sổ Nắng Chiều",
        "block": (
            "Setting: a cozy Gen Z study desk by a large apartment window, warm natural afternoon sunlight streaming through sheer white curtains "
            "from the left, an iPad placed on an acrylic stand, a minimalist white mechanical keyboard, pastel wireless mouse, aesthetic desk mat, "
            "small desk lamp turned on, neatly stacked notebooks, indoor plants adding fresh greenery, clean Scandinavian-inspired bedroom workspace, "
            "soft realistic lighting, cozy productive atmosphere. Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "modern_kitchen_island",
        "label": "Đảo Bếp Đá Hoa Cương Hiện Đại Nắng Sớm",
        "block": (
            "Setting: a clean modern minimalist home kitchen with a bright white marble island countertop in the foreground, "
            "warm morning sunlight streaming through a kitchen window from the left, neatly arranged wooden spice jars and small potted herbs "
            "softly blurred in the background, warm oak cabinets, bright airy inviting culinary atmosphere. Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "garden_cafe_table",
        "label": "Bàn Gỗ Quán Cà Phê Sân Vườn Thoáng Đãng",
        "block": (
            "Setting: a warm natural oak wooden café table next to a large glass window overlooking a lush green tropical garden patio, "
            "dappled natural morning sunlight filtering through leaves onto the tabletop, warm bokeh lights and tidy café counter softly blurred "
            "in the background, fresh relaxing lifestyle café atmosphere. Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "office_pantry_counter",
        "label": "Quầy Pantry / Bàn Trà Văn Phòng Hiện Đại",
        "block": (
            "Setting: a bright tidy modern office breakroom and pantry counter with a light wood tabletop in the foreground, "
            "large office windows with soft afternoon daylight coming from the left, a sleek coffee machine and green indoor plants "
            "softly blurred in the background, clean energetic snack-break atmosphere. Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "cozy_sofa_coffee_table",
        "label": "Bàn Trà Sofa Phòng Khách Ấm Cúng Xem Phim",
        "block": (
            "Setting: a cozy Scandinavian living room low wooden coffee table in the foreground, soft beige fabric sofa and warm floor lamp "
            "softly blurred in the background, natural afternoon daylight from a balcony window on the left, tidy warm home relaxation "
            "and movie-snack atmosphere. Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "balcony_chill_table",
        "label": "Bàn Trà Ban Công Chung Cư Nhiều Cây Xanh",
        "block": (
            "Setting: a clean light-toned wooden tea table on a bright airy apartment balcony, lush potted green plants along the railing, "
            "soft golden afternoon sunlight coming from the left, softly blurred city skyline in the far background, breezy fresh outdoor chill atmosphere. "
            "Vertical 9:16 realistic commercial UGC style."
        ),
    },
    {
        "id": "artisan_bakery_counter",
        "label": "Quầy Gỗ Tiệm Bánh & Trà Chiều Ấm Áp",
        "block": (
            "Setting: a warm-lit artisan bakery and afternoon tea wooden counter in the foreground, glass pastry display warm lights "
            "and ceramic tea canisters softly blurred in the background, soft natural side lighting from the left, appetizing cozy culinary atmosphere. "
            "Vertical 9:16 realistic commercial UGC style."
        ),
    },
]

HAND_POOL = [
    "a feminine hand with a glossy white glitter manicure, elegant natural pose",
    "a feminine hand with clean natural short nails, soft smooth skin, gentle caring touch, natural comfortable food-prep pose",
]

# Từ ngữ vi phạm Policy TikTok Shop cần tự động làm sạch
POLICY_REPLACEMENTS = [
    (r"\bnhất thế giới\b", "cực kỳ cuốn"),
    (r"\bsố 1 việt nam\b", "được ưa chuộng"),
    (r"\bsố 1\b", "hàng đầu"),
    (r"\bcam kết 100%\b", "yên tâm"),
    (r"\b100%\b", "chuẩn chỉnh"),
    (r"\bchữa bệnh\b", "thưởng thức"),
    (r"\bđặc trị\b", "hỗ trợ"),
    (r"\bgiảm cân\b", "nhâm nhi nhẹ nhàng"),
    (r"\bkhông béo\b", "vừa miệng"),
    (r"\brẻ nhất\b", "giá cực hời"),
    (r"\btiktok\b", "kênh"),
    (r"\bshopee\b", "cửa hàng"),
]


def load_template_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_voices_catalog() -> dict:
    if os.path.exists(VOICES_JSON_PATH):
        try:
            with open(VOICES_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def sanitize_tiktok_policy(text: str) -> str:
    out = text
    for pat, repl in POLICY_REPLACEMENTS:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def select_best_product_images(prod_img_dir: str) -> tuple:
    """
    Luôn sử dụng ảnh sản phẩm gốc nguyên bản (prod_1.jpg..prod_N.jpg),
    TUYỆT ĐỐI KHÔNG dùng ảnh bị cắt xén (prod_clean.jpg).
    """
    clean_p = os.path.join(prod_img_dir, "prod_clean.jpg")
    if os.path.exists(clean_p):
        try:
            os.remove(clean_p)
        except OSError:
            pass

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
        bn = os.path.basename(p)
        if bn == "prod_clean.jpg":
            continue
        try:
            if os.path.getsize(p) > 2000:
                valid_rels.append(bn)
        except OSError:
            pass
    if not valid_rels:
        valid_rels = [os.path.basename(jpgs[0])]
    return ([valid_rels[0]], valid_rels[:5])


def _clean_short_product_name_vn(raw_title: str) -> str:
    clean = re.sub(r"\[[^\]]*\]", "", raw_title or "").strip()
    clean = re.sub(r"\([^\)]*\)", "", clean).strip()
    clean = re.sub(r"\bhủ\s*(\d+)g\b", r"hũ \1 gam", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bhũ\s*(\d+)g\b", r"hũ \1 gam", clean, flags=re.IGNORECASE)
    words = clean.split()
    if len(words) > 7:
        clean = " ".join(words[:7])
    return clean or "món ngon này"


def _format_price_spoken_vn(raw_price: str) -> str:
    if not raw_price:
        return "giá ưu đãi rất hời"
    digits = re.sub(r"[^\d]", "", str(raw_price))
    if not digits:
        return "giá ưu đãi rất hời"
    val = int(digits)
    if val >= 1000:
        k_val = val // 1000
        return f"chỉ hơn {k_val} nghìn"
    return f"chỉ {val} nghìn"


def _build_culinary_staging_plan(title: str, desc: str, hand_block: str) -> dict:
    """
    Xây dựng kế hoạch bày biện ẩm thực sáng tạo (Creative Culinary Staging) & chuyển động 3 cảnh theo đúng loại món ăn:
    - Nhóm Sốt chấm / Kho quẹt / Mắm / Đồ rim: Bày hũ sản phẩm thật cạnh nồi đất sốt sánh kẹo bốc khói nhẹ (tôm khô, tốp mỡ, thịt ba rọi, tiêu xanh, ớt đỏ) + đĩa rau củ luộc xanh mướt & cơm cháy giòn rụm; múc sốt & chấm cơm cháy/rau củ.
    - Nhóm Topping / Đồ uống / Mứt / Hạt đác: Bày hũ sản phẩm thật cạnh ly đá viên mát lạnh đọng sương + bát sữa chua; múc muỗng topping óng ánh.
    - Nhóm Bánh / Đồ ăn có nhân kín bên trong: Bày bao bì sản phẩm thật cạnh đĩa bánh nguyên vẹn + tách trà chiều ấm áp; HẠN CHẾ không tự ý bẻ đôi/cắt bánh lộ nhân bên trong.
    - Nhóm Đồ ăn vặt / Snack / Thực phẩm khác: Bày bao bì sản phẩm thật cạnh đĩa/tô món ăn bắt mắt + ly nước mát lạnh.
    """
    text = f"{title} {desc}".lower()

    if any(k in text for k in ["kho quẹt", "làng chài xưa", "mắm nhỉ", "tôm khô", "tóp mỡ", "cá cơm"]):
        prod_desc_en = (
            "the exact 250g cylindrical clear jar of 'Làng Chài Xưa Kho Quẹt Nồi Đất Đặc Biệt Full Topping' "
            "with its glossy bright red ribbed screw lid, transparent top and bottom sections showing dark-amber caramelized fish sauce "
            "and savory toppings inside, and white wrap-around label featuring the red square 'LÀNG CHÀI XƯA' logo at top, "
            "bold red 'KHO QUẸT NỒI ĐẤT' title, bold blue 'ĐẶC BIỆT FULL TOPPING' subtitle, and round clay-pot illustration on the front label"
        )
        staging_en = (
            "APPETIZING CULINARY STAGING: The authentic red-lid Làng Chài Xưa jar stands prominently on the tabletop right beside a warm rustic brown clay pot (nồi đất) "
            "resting on a woven rattan trivet. The clay pot is brimming with glossy, thick dark-amber caramelized kho quẹt dipping sauce loaded with visible whole dried shrimp (tôm khô), "
            "golden crispy pork cracklings (tốp mỡ), braised pork belly cubes (thịt ba rọi), savory anchovies, fresh green peppercorn clusters (tiêu xanh), and whole red chili peppers, "
            "with gentle wisps of warm steam rising. Beside the clay pot sits a neat bamboo platter of fresh colorful boiled vegetables (bright green okra, luffa slices, carrots, cauliflower) "
            "and golden crispy scorched rice (cơm cháy), exactly like the appetizing presentation in the uploaded reference image."
        )
        return {
            "category": "savory_sauce_kho_quet",
            "prod_desc_en": prod_desc_en,
            "staging_en": staging_en,
            "negative_en": "No human face shown, no fake brand logos, no distorted label text, no watermarks.",
            "s1_img_action": (
                f"POV 25-degree tabletop angle: {hand_block} holds a small wooden spoon dipping into the steaming clay pot of glossy full-topping kho quẹt "
                "right next to the upright red-lid Làng Chài Xưa jar and the platter of fresh boiled vegetables and crispy cơm cháy."
            ),
            "s1_vis_t1": (
                "POV 25-degree tabletop medium shot showcasing the mouth-watering spread: the authentic red-lid Làng Chài Xưa Kho Quẹt jar stands beside "
                "the steaming rustic clay pot brimming with glossy caramelized sauce, dried shrimp, crispy pork cracklings, and green peppercorns, with boiled veggies and crispy cơm cháy."
            ),
            "s1_vis_t2": (
                f"Camera performs a smooth slow push-in toward the clay pot and jar as {hand_block} uses a small spoon to gently stir and lift a generous spoonful "
                "of thick, glossy amber kho quẹt loaded with whole dried shrimp and golden tốp mỡ."
            ),
            "s1_vis_t3": (
                "The rich syrupy fish sauce glistens in the natural light and slowly drips from the spoon back into the clay pot right beside the crisp Làng Chài Xưa jar, "
                "holding a steady, appetizing composition for Scene 2."
            ),
            "s2_img_action": (
                f"Closer POV medium-macro angle on the same tabletop: {hand_block} dips a golden piece of crispy scorched rice (cơm cháy) into the clay pot "
                "of glossy full-topping kho quẹt right beside the authentic red-lid Làng Chài Xưa jar."
            ),
            "s2_vis_t1": (
                "SCENE INHERITANCE FROM SCENE 1: Starting from the exact tabletop spread at the end of Scene 1, the camera focuses in a closer medium-macro view "
                "on the brimming clay pot of kho quẹt and the authentic red-lid Làng Chài Xưa jar side by side."
            ),
            "s2_vis_t2": (
                f"The {hand_block} picks up a piece of golden crispy scorched rice (cơm cháy) and dips it generously into the warm clay pot, "
                "coating the crispy rice with thick caramelized kho quẹt sauce, dried shrimp, and crispy pork cracklings."
            ),
            "s2_vis_t3": (
                "The hand lifts the sauce-coated crispy cơm cháy slightly toward the camera in an irresistible close-up while the authentic Làng Chài Xưa jar "
                "and green boiled vegetables remain clearly framed on the table."
            ),
            "s3_img_action": (
                f"Balanced POV hero tabletop shot: the authentic red-lid Làng Chài Xưa jar, steaming clay pot of kho quẹt, and boiled vegetable platter sit together "
                f"while {hand_block} touches the jar lightly and gestures toward the bottom-left corner."
            ),
            "s3_vis_t1": (
                "SCENE INHERITANCE FROM SCENE 2: Inheriting the exact tabletop spread from Scene 2, the camera smoothly pulls back to reveal the complete, inviting meal setup "
                "with the authentic 250g Làng Chài Xưa jar, the full-topping clay pot, and the plate of boiled vegetables and crispy cơm cháy."
            ),
            "s3_vis_t2": (
                f"The {hand_block} lightly touches the side of the authentic Làng Chài Xưa jar to highlight its convenient 250g packaging, "
                "then makes a natural open-palm gesture pointing down toward the bottom-left corner of the vertical frame."
            ),
            "s3_vis_t3": (
                "Camera holds a warm, mouth-watering final hero shot of the Làng Chài Xưa jar and steaming clay pot of kho quẹt as the voiceover finishes cleanly."
            ),
        }

    if any(k in text for k in ["bánh pía", "bánh trung thu", "bánh mochi", "bánh bông lan", "bánh nướng", "bánh dẻo", "bánh có nhân", "nhân chảy"]):
        # Nhóm Bánh / Đồ có nhân kín: Vẫn bày biện bàn trà chiều hấp dẫn nhưng HẠN CHẾ tự ý cắt/bẻ lộ nhân bên trong
        prod_desc_en = (
            f"the exact packaged pastry product '{title[:80]}' strictly matching the uploaded reference photo 100%, "
            "preserving its exact outer packaging design, brand logo, Vietnamese typography, and colors"
        )
        staging_en = (
            "CONTROLLED APPETIZING AFTERNOON-TEA STAGING (NO HALLUCINATED INNER FILLINGS): The authentic product packaging is arranged neatly on the tabletop "
            "beside a clean white ceramic plate displaying a few intact, whole golden-baked pastries (strictly whole exterior only—do NOT cut, break open, or expose internal fillings) "
            "and a warm ceramic cup of fragrant afternoon tea on a wooden coaster."
        )
        return {
            "category": "filled_pastry_controlled",
            "prod_desc_en": prod_desc_en,
            "staging_en": staging_en,
            "negative_en": "No human face shown, DO NOT cut or break open pastries, DO NOT expose or invent internal fillings, no text overlays, no watermarks.",
            "s1_img_action": (
                f"POV 25-degree tabletop angle: the authentic pastry packaging sits beside a white plate of intact whole pastries and a warm cup of tea "
                f"while {hand_block} gently touches the product package."
            ),
            "s1_vis_t1": (
                "POV 25-degree tabletop medium shot of the cozy afternoon-tea spread: the authentic product packaging sits beside a white ceramic plate "
                "of intact whole golden pastries and a steaming cup of fragrant tea."
            ),
            "s1_vis_t2": (
                f"Camera slowly pushes in as {hand_block} gently lifts one individual sealed pastry packet (or intact whole pastry) slightly toward the warm window light, "
                "keeping the pastry completely intact without opening or breaking it."
            ),
            "s1_vis_t3": (
                "The hand sets the intact pastry neatly back onto the plate beside the authentic packaging, holding a clean composition for Scene 2."
            ),
            "s2_img_action": (
                f"Closer POV close-up on the same tabletop: {hand_block} holds an intact individual pastry packet beside the plate of whole pastries and teacup."
            ),
            "s2_vis_t1": (
                "SCENE INHERITANCE FROM SCENE 1: Inheriting the exact afternoon-tea tabletop setup from Scene 1, camera moves into a crisp close-up "
                "of the authentic packaging and the plate of intact whole pastries."
            ),
            "s2_vis_t2": (
                f"The {hand_block} gently rotates the intact product package 10 degrees in the sunlight to showcase the crisp printed label and appetizing whole exterior "
                "without tearing wrappers or exposing any internal filling."
            ),
            "s2_vis_t3": (
                "The hand places the product smoothly back at the center of the tray beside the warm teacup, ready for Scene 3."
            ),
            "s3_img_action": (
                f"Balanced POV hero shot of the authentic pastry packaging, plate of intact whole pastries, and teacup while {hand_block} gestures toward the bottom-left corner."
            ),
            "s3_vis_t1": (
                "SCENE INHERITANCE FROM SCENE 2: Camera smoothly pulls back from the close-up to frame the complete cozy afternoon-tea pastry spread on the tabletop."
            ),
            "s3_vis_t2": (
                f"The {hand_block} lightly touches the authentic product package, then makes a gentle open-palm gesture pointing toward the bottom-left corner of the frame."
            ),
            "s3_vis_t3": (
                "Camera holds a warm, inviting final hero shot of the afternoon-tea pastry spread as the voiceover finishes cleanly."
            ),
        }

    if any(k in text for k in ["hạt đác", "chanh dây", "mứt", "trà", "sữa chua", "topping", "nước", "đồ uống"]):
        prod_desc_en = (
            f"the exact packaged beverage/topping product '{title[:80]}' strictly matching the uploaded reference photo 100%, "
            "preserving its exact jar/container shape, lid, Vietnamese label artwork, and visible contents"
        )
        staging_en = (
            "APPETIZING BEVERAGE & TOPPING STAGING: The authentic product jar stands on a wooden tray right beside a tall crystal-clear glass of iced fruit drink "
            "filled with glistening ice cubes, cold condensation droplets on the glass, a fresh green mint sprig on top, and a small white ceramic bowl of smooth yogurt with a spoon."
        )
        return {
            "category": "beverage_topping",
            "prod_desc_en": prod_desc_en,
            "staging_en": staging_en,
            "negative_en": "No human face shown, no fake text overlays, no watermarks.",
            "s1_img_action": (
                f"POV 25-degree tabletop shot: the authentic product jar sits on a wooden tray beside a tall frosty glass of iced fruit drink and a small bowl "
                f"while {hand_block} holds a spoon dipping into the glossy fruit topping."
            ),
            "s1_vis_t1": (
                "POV 25-degree tabletop medium shot of the refreshing spread: the authentic product jar sits beside a tall iced drink glass with condensation droplets "
                "and a small ceramic bowl of glossy fruit topping."
            ),
            "s1_vis_t2": (
                f"Camera slowly pushes in as {hand_block} uses a clean spoon to lift a generous spoonful of glossy, chewy fruit topping and golden syrup "
                "right beside the authentic product jar."
            ),
            "s1_vis_t3": (
                "Golden syrup glistens in the sunlight and drips gently back down while the iced drink glass sparkles beside the jar, holding position for Scene 2."
            ),
            "s2_img_action": (
                f"Closer POV medium-macro shot: {hand_block} spoons glossy fruit topping into the tall iced glass beside the authentic product jar."
            ),
            "s2_vis_t1": (
                "SCENE INHERITANCE FROM SCENE 1: Starting from the exact wooden tray setup at the end of Scene 1, camera focuses closer on the iced glass and the authentic product jar."
            ),
            "s2_vis_t2": (
                f"The {hand_block} spoons the glossy fruit topping and syrup into the iced drink glass (or yogurt bowl), swirling gently so the ice cubes and fruit pieces glisten."
            ),
            "s2_vis_t3": (
                "The hand rests the spoon neatly on the tray beside the authentic product jar and refreshing iced glass."
            ),
            "s3_img_action": (
                f"Balanced POV hero shot of the authentic product jar, frosty iced drink glass, and topping bowl while {hand_block} gestures toward the bottom-left corner."
            ),
            "s3_vis_t1": (
                "SCENE INHERITANCE FROM SCENE 2: Camera smoothly pulls back to frame the complete refreshing drink and topping spread on the sunlit tabletop."
            ),
            "s3_vis_t2": (
                f"The {hand_block} lightly touches the authentic product jar, then makes a natural open-palm gesture pointing toward the bottom-left corner of the frame."
            ),
            "s3_vis_t3": (
                "Camera holds a crisp, refreshing final hero shot of the product jar and iced drink as the voiceover finishes cleanly."
            ),
        }

    # Mặc định cho các món Đồ ăn vặt / Thực phẩm đặc sản khác: Bày bao bì thật cạnh đĩa/tô món ăn hấp dẫn + ly nước mát
    prod_desc_en = (
        f"the exact packaged food product '{title[:80]}' strictly matching the uploaded reference photo 100%, "
        "preserving its exact packaging form, container shape, color palette, brand logo, and Vietnamese label layout"
    )
    staging_en = (
        "APPETIZING FOOD REVIEW STAGING: The authentic packaged product stands prominently on the tabletop right beside a neat ceramic dish/bowl "
        "presenting an appetizing serving of the food/snack accompanied by chopsticks/spoon and a refreshing glass of iced tea."
    )
    return {
        "category": "general_snack_food",
        "prod_desc_en": prod_desc_en,
        "staging_en": staging_en,
        "negative_en": "No human face shown, no cutting open filled cakes to invent fake fillings, no text overlays, no watermarks.",
        "s1_img_action": (
            f"POV 25-degree tabletop shot: the authentic product package stands beside an appetizing ceramic dish of the food and an iced drink "
            f"while {hand_block} touches the product and holds chopsticks/spoon."
        ),
        "s1_vis_t1": (
            "POV 25-degree tabletop medium shot of the inviting snack spread: the authentic product package sits beside a neat ceramic dish of appetizing food and a cold drink."
        ),
        "s1_vis_t2": (
            f"Camera slowly pushes in as {hand_block} gently touches the authentic product package and lifts a piece/spoonful from the serving dish beside it to catch the natural light."
        ),
        "s1_vis_t3": (
            "The hand steadies the serving dish beside the authentic product package in a clean composition, ready for Scene 2."
        ),
        "s2_img_action": (
            f"Closer POV medium-macro shot on the same tabletop: {hand_block} lifts an appetizing piece/spoonful from the serving dish right beside the authentic product package."
        ),
        "s2_vis_t1": (
            "SCENE INHERITANCE FROM SCENE 1: Starting from the exact tabletop spread at the end of Scene 1, camera moves closer to the serving dish and authentic product package."
        ),
        "s2_vis_t2": (
            f"The {hand_block} holds up an appetizing piece/spoonful of the food slightly toward the camera to highlight its delicious texture while the authentic package stands clearly beside it."
        ),
        "s2_vis_t3": (
            "The hand sets the spoon/chopsticks neatly back onto the ceramic dish beside the authentic product package."
        ),
        "s3_img_action": (
            f"Balanced POV hero shot of the authentic product package and serving dish on the tabletop while {hand_block} gestures toward the bottom-left corner."
        ),
        "s3_vis_t1": (
            "SCENE INHERITANCE FROM SCENE 2: Camera smoothly pulls back to reveal the complete, appetizing tabletop snack spread."
        ),
        "s3_vis_t2": (
            f"The {hand_block} lightly touches the authentic product package, then makes a natural open-palm gesture pointing toward the bottom-left corner of the frame."
        ),
        "s3_vis_t3": (
            "Camera holds a warm, appetizing final hero shot of the product package and food spread as the voiceover finishes cleanly."
        ),
    }


def _extract_flavor_highlights_vn(title: str, desc: str) -> tuple:
    """
    Trích xuất các điểm nhấn hương vị & độ ngon từ tên/mô tả sản phẩm (chuẩn Policy TikTok, câu gọn ~12-14 từ/mốc).
    Trả về (flavor_line_1, flavor_line_2, occasion_line).
    """
    text = f"{title} {desc}".lower()
    if any(k in text for k in ["kho quẹt", "làng chài xưa", "mắm nhỉ", "cá cơm", "tôm khô", "tóp mỡ"]):
        return (
            "Sốt mắm nhỉ bốn mươi độ đạm sánh kẹo, thơm lừng mùi tôm khô cá cơm rim",
            "Đầy ắp thịt ba rọi cùng tóp mỡ giòn béo, chấm rau củ luộc hay cơm cháy đều cuốn",
            "Hũ hai trăm năm mươi gam đóng gói sạch sẽ, mở ra ăn kèm cơm nóng cực tiện",
        )
    if any(k in text for k in ["cay", "tê", "bò", "que", "tăm", "hồ nam", "miếng", "snack"]):
        return (
            "Hương vị thơm lừng đậm đà, gia vị thấm đều từng thớ ăn vào rất bắt miệng",
            "Độ dai giòn vừa vặn, vị mặn ngọt cay nhẹ hòa quyện khiến ai thử cũng thích",
            "Mua sẵn để bàn học hay bàn làm việc, buồn miệng lấy ra nhâm nhi là hết sẩy",
        )
    if any(k in text for k in ["bánh", "kẹo", "sữa", "trứng", "phô mai", "ngọt", "dẻo", "mềm"]):
        return (
            "Mùi thơm dịu nhẹ cuốn hút, vị ngọt thanh vừa phải quyện cùng độ mềm rất dễ ăn",
            "Từng phần được đóng gói chỉn chu sạch sẽ, giữ trọn độ tươi ngon và vị thơm béo",
            "Rất hợp nhâm nhi buổi chiều cùng tách trà, mang đi học hay đi làm đều tiện",
        )
    if any(k in text for k in ["trà", "nước", "đác", "mứt", "chanh", "bí đao", "sữa chua"]):
        return (
            "Hương vị thanh mát tự nhiên, mùi thơm dịu quyện cùng độ giòn sần sật rất cuốn miệng",
            "Đóng gói sạch sẽ tiện lợi, dùng ăn trực tiếp hay pha đồ uống giải khát đều hợp",
            "Trời nóng hay lúc học tập làm việc căng thẳng có món này thưởng thức là tỉnh táo",
        )
    if any(k in text for k in ["khô", "mực", "gà", "heo", "cá", "cơm cháy", "hạt", "rong biển"]):
        return (
            "Mùi thơm hấp dẫn lan tỏa, gia vị nêm nếm đậm đà giữ trọn độ giòn ngon tự nhiên",
            "Nguyên liệu chọn lọc kỹ lưỡng, đóng gói kín đáo giúp bảo quản độ thơm ngon lâu dài",
            "Để sẵn trên bàn làm việc, nhâm nhi lúc xem phim hay tụ tập bạn bè đều hợp",
        )
    return (
        "Hương vị thơm ngon đậm đà, nêm nếm vừa miệng tạo cảm giác cuốn hút ngay từ đầu",
        "Bao bì đóng gói dày dặn sạch sẽ, giữ trọn độ tươi ngon và hương thơm đặc trưng",
        "Cực kỳ tiện lợi để nhâm nhi lúc học bài, làm việc văn phòng hay thư giãn cuối tuần",
    )


def _split_into_karaoke_phrases(text: str, max_chars: int = 26) -> list:
    clean = re.sub(r"[\"“”]", "", text)
    clean = re.sub(r"[,.;:!?\-]+", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return [["REVIEW ĐỒ ĂN VẶT NGON", 5]]
    words = clean.split()
    phrases = []
    cur = []
    for w in words:
        wu = w.upper()
        cand = " ".join(cur + [wu])
        if len(cand) <= max_chars and len(cur) < 6:
            cur.append(wu)
        else:
            if cur:
                phrases.append([" ".join(cur), max(1, len(cur))])
            cur = [wu[:max_chars]]
    if cur:
        phrases.append([" ".join(cur), max(1, len(cur))])
    return phrases


def _build_pov_voice_scenes_for_variant(
    vkey: str,
    variant_idx: int,
    pname: str,
    price_str: str,
    desc: str,
    bg_item: dict,
    hand_block: str,
    voice_prompt_en: str = "",
) -> list:
    """
    Sinh 3 phân cảnh × 10 giây (Tổng 30s) cho biến thể Đồ Ăn Vặt POV Có Voice:
    - Sáng tạo bày biện ẩm thực hấp dẫn (Creative Culinary Staging): Hũ/gói sản phẩm thật chuẩn 100% đặt cạnh nồi đất sốt sánh kẹo / đĩa rau củ luộc / cơm cháy giòn / ly nước đá (riêng bánh có nhân thì hạn chế bẻ lộ nhân).
    - Đồng bộ Timeline kép: VISUAL & CAMERA TIMELINE ([0.0-3.5s], [3.5-7.0s], [7.0-10.0s]) khớp 1:1 với VOICEOVER TIMELINE ([0.0-3.5s], [3.5-7.0s], [7.0-10.0s]).
    - Kế thừa phân cảnh (Scene Inheritance): Cảnh 2 kế thừa cuối Cảnh 1, Cảnh 3 kế thừa cuối Cảnh 2.
    - Kịch bản Voice chuẩn Policy TikTok Shop, tập trung vào độ ngon & trải nghiệm thưởng thức.
    """
    short_name = _clean_short_product_name_vn(pname)
    price_spoken = _format_price_spoken_vn(price_str)
    flav_1, flav_2, occ_line = _extract_flavor_highlights_vn(pname, desc)
    bg_block = bg_item["block"]
    plan = _build_culinary_staging_plan(pname, desc, hand_block)
    prod_desc_en = plan["prod_desc_en"]
    staging_en = plan["staging_en"]
    neg_en = plan["negative_en"]

    if variant_idx % 2 == 1:
        # Kịch bản 1: Hook Tín Đồ Ẩm Thực & Độ Ngon Cuốn Miệng (~38-42 từ / cảnh 10s)
        s1_t1 = sanitize_tiktok_policy(f"Ai mê đồ ngon đậm vị thì đừng bỏ qua {short_name} này nha")
        s1_t2 = sanitize_tiktok_policy("Nhìn phần sốt sánh kẹo đầy ắp tôm khô tóp mỡ là thấy thèm liền")
        s1_t3 = sanitize_tiktok_policy(f"Giá hôm nay lại {price_spoken} nên mình phải lên clip review ngay")
        if plan["category"] == "filled_pastry_controlled":
            s1_t2 = sanitize_tiktok_policy("Bày ra đĩa thưởng thức cùng tách trà chiều là chuẩn bài thơm ngon")

        s2_t1 = sanitize_tiktok_policy(flav_1)
        s2_t2 = sanitize_tiktok_policy(flav_2)
        s2_t3 = sanitize_tiktok_policy("Từng nguyên liệu hòa quyện đậm đà khiến bữa ăn thêm tròn vị")

        s3_t1 = sanitize_tiktok_policy(occ_line)
        s3_t2 = sanitize_tiktok_policy("Đợt này trên kênh đang có ưu đãi trợ giá rất hời cho mọi người")
        s3_t3 = sanitize_tiktok_policy("Bấm ngay vào giỏ hàng góc trái màn hình để rinh về thưởng thức nhé")
    else:
        # Kịch bản 2: Hook Bữa Ăn Tiện Lợi & Hương Vị Đậm Đà (~38-42 từ / cảnh 10s)
        s1_t1 = sanitize_tiktok_policy(f"Tìm được chân ái cho bữa ăn ngon miệng với {short_name} cực cuốn")
        s1_t2 = sanitize_tiktok_policy("Múc một muỗng đầy ắp topping thơm nức mũi nhìn thôi đã mê")
        s1_t3 = sanitize_tiktok_policy(f"Mức giá đang {price_spoken} cực kỳ hợp túi tiền mọi gia đình")
        if plan["category"] == "filled_pastry_controlled":
            s1_t2 = sanitize_tiktok_policy("Vỏ bánh vàng ươm thơm dịu bày lên đĩa nhìn cực kỳ bắt mắt")

        s2_t1 = sanitize_tiktok_policy(flav_2)
        s2_t2 = sanitize_tiktok_policy(flav_1)
        s2_t3 = sanitize_tiktok_policy("Hương vị truyền thống hài hòa giúp món ăn kèm thêm ngon miệng")

        s3_t1 = sanitize_tiktok_policy(occ_line)
        s3_t2 = sanitize_tiktok_policy("Mỗi tài khoản đang có mã giảm giá riêng rất tiết kiệm ở bên dưới")
        s3_t3 = sanitize_tiktok_policy("Mọi người chạm nhẹ vào giỏ hàng góc trái màn hình để chốt đơn nha")

    scene_specs = [
        {
            "num": 1,
            "title": f"CẢNH 1 (0–10s): POV HOOK & KHÁM PHÁ MÓN NGON ({bg_item['label']})",
            "t1": s1_t1,
            "t2": s1_t2,
            "t3": s1_t3,
            "img_prompt": (
                f"Use the uploaded product image as the strict product reference. Vertical 9:16 realistic commercial POV food review image. "
                f"{bg_block} "
                f"PRODUCT LOCK: {prod_desc_en}. Keep the packaged product 100% faithful to the uploaded reference image. "
                f"{staging_en} "
                f"Action & Framing: {plan['s1_img_action']} "
                f"Shallow depth of field, appetizing 8K commercial food photography, {neg_en}"
            ),
            "vis_t1": plan["s1_vis_t1"],
            "vis_t2": plan["s1_vis_t2"],
            "vis_t3": plan["s1_vis_t3"],
        },
        {
            "num": 2,
            "title": f"CẢNH 2 (10–20s): KẾ THỪA CẢNH 1 — CẬN CẢNH THƯỞNG THỨC & ĐỘ NGON ({bg_item['label']})",
            "t1": s2_t1,
            "t2": s2_t2,
            "t3": s2_t3,
            "img_prompt": (
                f"Use the uploaded product image as the strict product reference. Vertical 9:16 realistic commercial POV close-up food image. "
                f"{bg_block} "
                f"PRODUCT LOCK: {prod_desc_en}. "
                f"{staging_en} "
                f"Scene Inheritance from Scene 1: {plan['s2_img_action']} "
                f"Shallow depth of field, photorealistic 8K, {neg_en}"
            ),
            "vis_t1": plan["s2_vis_t1"],
            "vis_t2": plan["s2_vis_t2"],
            "vis_t3": plan["s2_vis_t3"],
        },
        {
            "num": 3,
            "title": f"CẢNH 3 (20–30s): KẾ THỪA CẢNH 2 — BỐ CỤC HERO & ĐIỀU HƯỚNG GIỎ HÀNG ({bg_item['label']})",
            "t1": s3_t1,
            "t2": s3_t2,
            "t3": s3_t3,
            "img_prompt": (
                f"Use the uploaded product image as the strict product reference. Vertical 9:16 realistic commercial POV hero food image. "
                f"{bg_block} "
                f"PRODUCT LOCK: {prod_desc_en}. "
                f"{staging_en} "
                f"Scene Inheritance from Scene 2: {plan['s3_img_action']} "
                f"Warm inviting natural daylight, photorealistic 8K, {neg_en}"
            ),
            "vis_t1": plan["s3_vis_t1"],
            "vis_t2": plan["s3_vis_t2"],
            "vis_t3": plan["s3_vis_t3"],
        },
    ]

    scenes_out = []
    v_dir_en = voice_prompt_en or "cheerful, appetizing Vietnamese food reviewer voiceover, natural conversational pace"
    for sc in scene_specs:
        sc_num = sc["num"]
        full_dialogue_vn = f"{sc['t1']}. {sc['t2']}. {sc['t3']}."
        vid_prompt = (
            f"10-second vertical 9:16 realistic commercial POV food review video clip. "
            f"CONTINUITY & APPETIZING CULINARY STAGING: Inherit the exact tabletop scene, natural window lighting, hand identity ({hand_block}), "
            f"authentic packaged product ({prod_desc_en}), and appetizing served food accompaniment from the reference image. "
            f"{staging_en} "
            f"{bg_block} "
            f"VISUAL & CAMERA TIMELINE (synchronized with voiceover): "
            f"[0.0-3.5s]: {sc['vis_t1']} "
            f"[3.5-7.0s]: {sc['vis_t2']} "
            f"[7.0-10.0s]: {sc['vis_t3']} "
            f"VOICEOVER TIMELINE ({v_dir_en}, finishing cleanly before 9.5s): "
            f"[0.0-3.5s] Voice says: \"{sc['t1']}\" "
            f"[3.5-7.0s] Voice says: \"{sc['t2']}\" "
            f"[7.0-10.0s] Voice says: \"{sc['t3']}\" "
            f"STRICT NEGATIVE: {neg_en} Photorealistic."
        )
        word_cnt = len(full_dialogue_vn.split())
        scenes_out.append({
            "id": f"{vkey}_s{sc_num}",
            "file": f"{vkey}_s{sc_num}.mp4",
            "scene_title": sc["title"],
            "scene_description": full_dialogue_vn,
            "dialogue": full_dialogue_vn,
            "voice_timeline": {
                "0.0-3.5s": sc["t1"],
                "3.5-7.0s": sc["t2"],
                "7.0-10.0s": sc["t3"],
            },
            "visual_timeline": {
                "0.0-3.5s": sc["vis_t1"],
                "3.5-7.0s": sc["vis_t2"],
                "7.0-10.0s": sc["vis_t3"],
            },
            "image_prompt": sc["img_prompt"],
            "prompt": vid_prompt,
            "words": max(8, word_cnt),
            "phrases": _split_into_karaoke_phrases(full_dialogue_vn),
        })
    return scenes_out


def generate_project_from_template(
    pid: str,
    pdir: str,
    info_data: dict,
    characters_data: dict = None,
    videos_per_character: int = None,
    primary_product_refs: list = None,
    slide_overlay_files: list = None,
    selected_voice_key: str = None,
) -> dict:
    """
    Sinh prompts.json và spec_v*.json trong thư mục projects/<pid>/ theo Template Đồ Ăn Vặt POV (Có Voice + Random Background + Creative Culinary Staging + Timeline Sync + 60fps Subtitles).
    """
    cfg = load_template_config()
    voices_cat = load_voices_catalog()
    os.makedirs(pdir, exist_ok=True)
    prod_img_dir = os.path.join(pdir, "product_images")
    os.makedirs(prod_img_dir, exist_ok=True)

    auto_primary, auto_slides = select_best_product_images(prod_img_dir)
    primary_refs = [r for r in (primary_product_refs or auto_primary) if r != "prod_clean.jpg"] or auto_primary
    slide_overlays = [r for r in (slide_overlay_files or auto_slides) if r != "prod_clean.jpg"] or auto_slides

    pname = (
        info_data.get("name")
        or info_data.get("title")
        or info_data.get("product_name")
        or f"Sản phẩm {pid}"
    )
    price_str = str(info_data.get("price") or info_data.get("sale_price") or "")
    desc = info_data.get("description") or ""

    num_variants = int(videos_per_character or cfg.get("default_videos_per_character", 2))
    num_variants = max(1, min(6, num_variants))

    # Lấy thông tin Voice & Project từ voices_and_characters.json (character_id để rỗng "" vì quay POV sản phẩm)
    chars_dict = (characters_data or {}).get("characters") or voices_cat.get("characters") or {}
    voices_dict = (characters_data or {}).get("voices") or voices_cat.get("voices") or {}

    nv1_info = chars_dict.get("nv1", {})
    nv2_info = chars_dict.get("nv2", {})
    voice_presets = [
        {
            "char_key": "nv1",
            "voice_id": voices_dict.get("nv1", {}).get("voice_id") or nv1_info.get("voice_id") or "27f51973-e290-4a38-bd7a-9d6fbe81b2f6",
            "voice_name": voices_dict.get("nv1", {}).get("name") or nv1_info.get("voice_name") or "Nhân Vật 1 Affi Giọng Bắc",
            "voice_prompt_en": voices_dict.get("nv1", {}).get("voice_prompt_en") or nv1_info.get("voice_prompt_en") or "",
            "project_id": nv1_info.get("project_id") or "932bc2a1-07ea-4199-b147-80ab0018d41c",
        },
        {
            "char_key": "nv2",
            "voice_id": voices_dict.get("nv2", {}).get("voice_id") or nv2_info.get("voice_id") or "75a3d14a-ed10-4bdc-862c-44adb02a5562",
            "voice_name": voices_dict.get("nv2", {}).get("name") or nv2_info.get("voice_name") or "Nhân Vật 2 Affi Giọng Bắc Năng Lượng",
            "voice_prompt_en": voices_dict.get("nv2", {}).get("voice_prompt_en") or nv2_info.get("voice_prompt_en") or "",
            "project_id": nv2_info.get("project_id") or "bf4979d1-548a-44bd-a265-3927bba76dc1",
        },
    ]
    if selected_voice_key and selected_voice_key in voices_dict:
        v_sel = voices_dict[selected_voice_key]
        voice_presets = [{
            "char_key": selected_voice_key if selected_voice_key in ("nv1", "nv2") else "nv1",
            "voice_id": v_sel.get("voice_id") or "27f51973-e290-4a38-bd7a-9d6fbe81b2f6",
            "voice_name": v_sel.get("name") or selected_voice_key,
            "voice_prompt_en": v_sel.get("voice_prompt_en") or "",
            "project_id": nv1_info.get("project_id") or "932bc2a1-07ea-4199-b147-80ab0018d41c",
        }]

    # Random ngẫu nhiên Background từ 8 Background trong DoAnVat cho mỗi video
    chosen_bgs = random.sample(RANDOM_BG_POOL, k=min(num_variants, len(RANDOM_BG_POOL)))
    while len(chosen_bgs) < num_variants:
        chosen_bgs.append(random.choice(RANDOM_BG_POOL))

    videos_json = {}
    nv_counts = {"nv1": 0, "nv2": 0}

    for idx in range(num_variants):
        vkey = f"v{idx + 1}"
        vp = voice_presets[idx % len(voice_presets)]
        ck = vp["char_key"]
        nv_counts[ck] = nv_counts.get(ck, 0) + 1
        char_v = f"{ck}_v{nv_counts[ck]}"
        bg_item = chosen_bgs[idx]
        hand_block = HAND_POOL[idx % len(HAND_POOL)]

        hook_title = (
            f"POV Review Có Voice #{idx + 1}: {bg_item['label']} ({vp['voice_name']})"
        )
        style_label = f"POV Đồ Ăn Vặt Có Voice • {bg_item['label']} • {vp['voice_name']}"

        built_scenes = _build_pov_voice_scenes_for_variant(
            vkey=vkey,
            variant_idx=idx + 1,
            pname=pname,
            price_str=price_str,
            desc=desc,
            bg_item=bg_item,
            hand_block=hand_block,
            voice_prompt_en=vp.get("voice_prompt_en", ""),
        )

        scenes_list = []
        spec_scenes = []
        for s in built_scenes:
            scenes_list.append({
                "id": s["id"],
                "file": s["file"],
                "scene_title": s["scene_title"],
                "scene_description": s["scene_description"],
                "dialogue": s["dialogue"],
                "voice_timeline": s["voice_timeline"],
                "visual_timeline": s["visual_timeline"],
                "image_prompt": s["image_prompt"],
                "prompt": s["prompt"],
                "words": s["words"],
                "phrases": s["phrases"],
            })
            spec_scenes.append({
                "file": s["file"],
                "words": s["words"],
                "phrases": s["phrases"],
            })

        ref_img_name = f"{vkey}-refimg.jpg"
        videos_json[vkey] = {
            "char_v": char_v,
            "character": ck,
            "character_id": "",  # Quay POV trực diện bàn ăn & sản phẩm, không chèn nhân vật nhà xưởng
            "voice_id": vp["voice_id"],
            "voice_name": vp["voice_name"],
            "project_id": vp["project_id"],
            "background_id": bg_item["id"],
            "background_label": bg_item["label"],
            "hook_title": hook_title,
            "style": style_label,
            "template_id": cfg.get("id", "do_an_vat_pov_voice"),
            "template_name": cfg.get("folder_name", "Đồ Ăn Vặt"),
            "ref_image": ref_img_name,
            "ref_image_prompt": built_scenes[0]["image_prompt"] if built_scenes else "",
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
        "template_id": cfg.get("id", "do_an_vat_pov_voice"),
        "template_name": cfg.get("folder_name", "Đồ Ăn Vặt"),
        "videos_per_character": num_variants,
        "primary_product_refs": primary_refs,
        "slide_overlay_files": slide_overlays,
        "ref_img_prompt_nv1": videos_json.get("v1", {}).get("ref_image_prompt", ""),
        "ref_img_prompt_nv2": videos_json.get("v2", {}).get("ref_image_prompt", ""),
        "videos": videos_json,
    }
    with open(os.path.join(pdir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_obj, f, ensure_ascii=False, indent=2)

    return prompts_obj
