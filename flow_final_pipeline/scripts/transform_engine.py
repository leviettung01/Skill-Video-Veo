"""Universal Character + Product Transformation Studio Engine (Template 006+)."""
import base64
import concurrent.futures
import io
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import threading
import time
from uuid import uuid4

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_ROOT = ROOT / "Template"
ASSETS = TEMPLATES_ROOT / "Bien Hinh Thoi Trang"
ALT_DEMO_ASSETS = TEMPLATES_ROOT / "Biến hình Làm nông, Bán cá" / "Video mẫu"
JOBS = ROOT / "projects"
LOCK = threading.RLock()
_QUEUE_COND = threading.Condition()
_ACTIVE_JOBS: set[str] = set()
_STOPPED_JOBS: set[str] = set()


class JobStoppedError(RuntimeError):
    pass


def _is_stopped(job_id: str) -> bool:
    return bool(job_id) and job_id in _STOPPED_JOBS


def _max_transform_slots(runner=None) -> int:
    try:
        _flow_cnt = len([c for c in runner.flow_account_candidates() if c and c[0]]) if runner is not None else 0
    except Exception:
        _flow_cnt = 1
    try:
        import engine_settings_manager as _esm_st
        _eff_st = _esm_st.get_effective_flow_concurrency()
        return max(1, min(16, int(_eff_st.get("parallel_products") or max(2, _flow_cnt or 1))))
    except Exception:
        return max(1, min(8, max(2, _flow_cnt or 2)))
RESERVED_TEMPLATE_FOLDERS = {"Biến hình Làm nông, Bán cá"}
DEFAULT_VIDEO_MODEL = "Omni 1.1 Flash"
SUPPORTED_VIDEO_MODELS = (
    "Omni 1.1 Flash",
    "Omni Flash",
    "Omni 1.2 Flash",
    "Veo 3.1 - Fast",
    "Veo 3.1 - Quality",
    "Veo 3.1 - Lite",
)
PRESETS = {
    "farm": {
        "title": "Làm nông", "icon": "🌾", "badge": "Cuốc đất → Biệt thự",
        "transition_style": "sunlit", "demo": "01_lam_nong.mp4", "alt_demo": "Làm nông.mp4",
        "cover_item": "the mud-darkened flat iron hoe blade she holds",
        "summary": "Cuốc đất tốc độ thật → lau mồ hôi & nhìn thẳng → đưa lưỡi cuốc dính bùn che kín 100% camera → bước ra cửa biệt thự nắng vàng cùng thần thái sải bước quý phái.",
        "before": ("A Vietnamese adult woman with a loose low work bun, natural damp skin without glam makeup, wearing a "
                   "faded plaid cotton long-sleeve button-up shirt, soil-dusted loose brown trousers, and olive-green rubber boots, "
                   "bent slightly in active fieldwork inside a lush outdoor vegetable garden with yellow squash blossoms while swinging "
                   "a wooden-handled flat iron hoe into dark garden soil. Soft cloudy daylight, earthy green and brown tones. Medium-full "
                   "9:16 portrait framing with clean headroom and both hands gripping the hoe clearly visible."),
        "s1_t1": "0.0s–2.0s", "s1_t2": "2.0s–4.9s", "s1_t3": "4.9s–7.0s", "s1_t4": "7.0s–8.0s",
        "work_open": ("All motion at crisp, natural 1.0x real-time 24fps live-action human speed (strictly no slow-motion); mouth stays "
                      "closed silently. She swings the iron hoe downward firmly into the dark garden earth twice with grounded weight, lifting "
                      "moist soil before straightening up cleanly."),
        "work": ("Pausing with feet firmly planted in the garden soil and one hand resting on the upright wooden hoe handle, she wipes "
                 "sweat smoothly across her forehead with the back of her forearm and locks a calm, composed, determined gaze straight into the lens (strictly silent, zero dialogue)."),
        "cover": ("Keeping steady eye contact while the vegetable garden behind remains naturally lit, she grips the hoe with both hands "
                  "and briskly pushes the wide mud-darkened flat iron blade forward toward the camera glass, bringing it smoothly into an oversized "
                  "macro close-up pressed flush over the lens until dark wet iron and soil fill 100% of the viewport."),
        "after": ("Grand sunlit luxury estate portico outside towering wide-open carved dark mahogany double doors above wide polished cream granite "
                  "entrance steps flanked by floral stone urns. Dramatic golden morning cinematic rim light and sleek crisp shadows. Eye-level full-body 9:16 editorial composition centering her head-to-toe clearly unobstructed with generous headroom."),
        "s2_t1": "0.0s–2.2s", "s2_t2": "2.2s–4.8s", "s2_t3": "4.8s–8.0s",
        "reveal_open": ("Crisp 24fps live-action entrance (never sluggish or slow-motion): stepping gracefully forward out through the carved mahogany villa double doors into warm golden sunlight wearing the exact Reference 2 outfit, bag, hair styling, and footwear; she turns her poised chin slightly with calm old-money composure and a subtle knowing power smile."),
        "reveal_mid": ("Medium-full smooth Steadicam tracking as she descends the grand marble entrance steps at a confident, poised catwalk pace — lightly steadying her handbag strap or grazing the fabric drape with relaxed fingers while keeping head, neck, shoulders, and torso naturally aligned forward (zero spinning or turning away)."),
        "reveal_end": ("Steadicam glides smoothly backward ahead of her as she strides purposefully straight toward the lens down the sunlit stone terrace in effortless aristocratic elegance — maintaining a cool, self-assured power smile and keeping 100% of neckline, collar, print, seams, bag, and shoes razor-sharp through 8.0s. 8K cinema film quality, natural surface realism.")
    },
    "fish": {
        "title": "Bán cá", "icon": "🐟", "badge": "Thoại chợ cá → VIP Xế hộp & Vệ sĩ",
        "transition_style": "night_flash", "demo": "02_ban_ca.mp4", "alt_demo": "Bán cá.mp4",
        "has_dialogue": True,
        "dialogue_line": "Tháng sau bọn anh cưới, rảnh thì qua chung vui nhé. Nhớ rửa tay cho sạch mùi cá.",
        "cover_item": "her wet bright-pink rubber-gloved open right hand and palm",
        "summary": "Đánh vảy cá (0–3.0s) → cắt cận đôi nam nữ cũ đưa thiệp & nam thoại 'Tháng sau bọn anh cưới...' (3.0–5.4s) → cận nữ rưng rưng im lặng (5.4–7.0s) & đưa găng hồng áp sát che kín 100% ống kính (7.0–8.0s) → bước ra khỏi xế hộp Maybach cỡ lớn cùng 4 vệ sĩ trên hành lang đá hoa cương & đèn flash phóng viên.",
        "before": ("High-angle 9:16 candid shot inside a bustling outdoor Vietnamese wet-market fish stall: a Vietnamese adult woman "
                   "with a low tied-back messy bun and bare natural unretouched skin, wearing a faded dusty-pink short-sleeve T-shirt, "
                   "floral market trousers, and bright-pink rubber work gloves on both hands, squatting low behind red and blue plastic "
                   "basins brimming with fresh silver fish, crushed ice, and a wet round wooden chopping block as she scales a fish with a "
                   "small knife; wet-market shoppers and vegetable stalls fill the background in crisp overcast morning daylight."),
        "s1_t1": "0.0s–3.0s", "s1_t2": "3.0s–5.4s", "s1_t3": "5.4s–7.0s", "s1_t4": "7.0s–8.0s",
        "work_open": ("All motion runs at crisp natural 1.0x real-time 24fps human speed (strictly no slow-motion); all characters keep mouths closed silently during this full 3.0-second establishing shot. "
                      "From 0.0s to 1.8s, squatting beside the wet wooden block and red/blue fish basins, the fish-seller woman focuses down and briskly scrapes silver scales off a fish with both pink-gloved hands without looking up yet. "
                      "From 1.8s to 3.0s, a smug young ex-boyfriend and his arrogant new girlfriend in black jackets walk into the market stall edge beside her holding a white wedding invitation card, and she stops scraping to look up at them — HOLD this shot cleanly until 3.0s before making any cut."),
        "work_label": "Hard Cut to Couple — Ex-Boyfriend Speaks Only",
        "work": ("At exactly 3.0s, hard camera cut to a medium close-up angled over the seated fish-seller's shoulder facing THE EX-BOYFRIEND AND HIS NEW GIRLFRIEND straight on (only the back-left corner of the fish-seller's dark hair appears in the lower-left foreground; her face is angled away). "
                 "EX-BOYFRIEND (THE ONLY SPEAKING CHARACTER): leaning slightly forward with raised eyebrows and a smug mocking half-smirk across 3.2s–5.3s, casually flicking the crisp white wedding card downward toward her stall — ONLY his lips move naturally as he speaks Vietnamese at brisk conversational pace: \"Tháng sau bọn anh cưới, rảnh thì qua chung vui nhé.\" "
                 "NEW GIRLFRIEND BESIDE HIM (STRICTLY SILENT): arms folded tight across her chest, chin raised, scowling down disdainfully with a tightly closed mouth."),
        "cover_label": "Silent Tearful Close-Up & Straight-to-Lens Pink-Glove Cover",
        "cover": ("At 5.4s, hard eye-level close-up cut directly onto the FISH-SELLER WOMAN'S FACE (Reference 1, soft shallow-DOF background with couple blurred behind). "
                  "FISH-SELLER EXPRESSION & ACTION (STRICTLY NON-SPEAKING — ZERO LIP MOVEMENT): keep her mouth gently closed with faintly trembling pressed lips — DO NOT speak, shout, or open her mouth; glistening tears brim along her lower eyelashes in hurt, humiliated yet dignified silence from 5.4s to 6.4s. "
                  "Right at 6.4s, at crisp 1.0x real-time speed without stopping mid-air, she forcefully thrusts her wet bright-pink rubber-gloved palm (with four fingers kept tightly pressed together — zero splayed finger gaps) continuously straight forward directly into the center of the camera lens while lens focus racks aggressively onto the approaching palm — the expanding bright-pink rubber surface rushes closer across 6.4s–7.0s until her pink-gloved hand completely engulfs her face, eyes, and entire frame before pressing flush against the camera glass."),
        "after": ("Dramatic evening grand hotel valet porte-cochere outside tall illuminated limestone columns and a WIDE FLAT polished cream-and-black granite promenade walkway running beside a level dark asphalt driveway lane (clean level forecourt straight ahead toward camera with ZERO narrow steps beneath the car or obstructing her stride). "
                  "Parked solidly on the flat street driveway lane on the mid-background left sits a MASSIVE, genuine full-size long-wheelbase flagship glossy black luxury sedan (true Mercedes-Maybach S-Class real-world automotive scale: ~5.4m long chassis and ~1.50m tall roofline matching eye/chin height of a person standing beside it, heavy thick open rear passenger door swung outward cleanly toward the curb edge, full-height 20-inch chrome alloy wheels planted flat on the asphalt — NEVER shrunk or toy-sized). "
                  "Standing politely on the driveway curb beside the outer edge of the open rear door is ONE tall male bodyguard in a tailored black suit and dark sunglasses holding the door handle. "
                  "Standing clearly ~1.5 meters IN FRONT OF and cleanly separated from the open car door on the flat granite walkway (zero overlap or clipping with the car door or fender) is the transformed heroine head-to-toe occupying ~58%–62% of frame height so both her exact Reference 2 outfit and the towering full-scale luxury black sedan read in authentic real-world proportion, matching Reference 1 face with sleek luxury waves, refined editorial makeup, lifted chin, cool assured power half-smile, wearing the entire Reference 2 outfit, accessories, handbag, socks/footwear verbatim."),
        "s2_t1": "0.0s–2.2s", "s2_t2": "2.2s–4.8s", "s2_t3": "4.8s–8.0s",
        "reveal_open": ("Crisp natural 1.0x real-time 24fps cinema speed (strictly no sluggish or floaty slow-motion): on the wide flat granite walkway cleanly ahead of the stationary full-size glossy black luxury sedan, the door bodyguard holds the rear car door steady in place beside the driveway while the heroine (wearing verbatim Reference 2 clothing, footwear, handbag, and accessories) calmly turns her aristocratic face straight forward, lightly steadies her handbag strap or skirt hem, and begins striding straight FORWARD down the open granite promenade AWAY from the parked sedan (zero walking across, behind, or into the car)."),
        "reveal_mid": ("Fluid eye-level Steadicam tracking shot gliding smoothly backward straight ahead of her along the wide open promenade as she clears well ahead of the stationary black luxury sedan; 4 tall dignified male bodyguards FULLY DRESSED in buttoned tailored black formal suit jackets, crisp white dress shirts, black silk neckties, dark suit trousers, and black sunglasses (strictly fully clothed from collar to shoes — ZERO shirtless men, ZERO bare chests, ZERO exposed torsos) step briskly IN FROM THE OUTER LEFT AND OUTER RIGHT stone portico pillars well clear of the car chassis — NEVER emerging from behind, inside, over, or through the car — aligning smoothly into a symmetrical V-escort well behind her shoulders without touching her outfit silhouette or overlapping the parked vehicle."),
        "reveal_end": ("Steadicam glides briskly and smoothly backward straight down the grand granite promenade ahead of her at confident live-action runway pace as she strides powerfully forward with commanding old-money swagger and a serene power smile, escorted well behind by the 4 fully suited dark-jacket white-shirt necktie sunglasses-wearing bodyguards while brief cool-white optical camera flashes blink cleanly from DSLR lenses held by blurred foreground press photographers along the outer side edges (zero fireworks, zero sparklers, zero sparks, zero smoke), and the massive full-size glossy black luxury sedan smoothly recedes untouched in the rear background. Strict physical solidity constraint: car doors, hood, roof, fenders, and cabin remain completely solid and opaque — NO person or bodyguard ever clips through, passes inside, or emerges out of the solid car body, and every bodyguard stays 100% dressed in buttoned black suit jacket and white dress shirt. Ultra-detailed 8K cinema film quality, hyper-realistic skin, fabric, granite, glass, and chrome textures, no text, no subtitles, no logos, no watermark.")
    }
}
PRODUCT_PROMPT = (
    "Extract the complete fashion outfit and ALL visible accessories and footwear worn or carried by the model in the reference photo "
    "into an ultra-clean, luxury studio e-commerce flat-lay product sheet on a seamless pure solid white background (#FFFFFF) with soft, "
    "subtle natural contact shadows directly beneath each piece. Completely remove the person, body, skin, face, hair, mannequin, hanger, "
    "background scenery, harsh outdoor shadows, and any seller text or graphic overlays.\n"
    "Organize every item neatly with generous white margins and crisp balanced spacing in a structured 2-column knolling grid:\n"
    "- LEFT COLUMN (~55% width — Main Clothing Garment(s)): Sculpt the main clothing with invisible ghost-mannequin 3D volume, natural pleats, "
    "and crisp pressed fabric drape. For a two-piece outfit, align top/outerwear cleanly above bottoms (skirt/shorts/pants); for a single dress "
    "or jumpsuit, center the piece cleanly keeping its EXACT true width-to-length silhouette proportion (keep short above-knee mini dresses "
    "short and naturally flared — never stretch or elongate them vertically). Preserve exact neckline, collar, sleeve puff/volume, buttons, "
    "closures, seams, weave texture, micro-print placement, and true colors.\n"
    "- RIGHT COLUMN (~45% width — Coordinated Accessories & Footwear, stacked cleanly top-to-bottom): Cleanly isolate EVERY visible accessory "
    "and footwear piece from the reference photo (hair bow/clip/scrunchie, eyewear, necklace/choker, bracelet/watch, belt, upright handbag/shoulder bag "
    "with neat strap, socks, and paired shoes/boots/sneakers/heels) cleanly spaced vertically. Keep every item strictly faithful in color, "
    "material, stitching, hardware, and design to the reference photo; omit empty slots cleanly instead of inventing unrelated items.\n"
    "High-key diffused studio product photography, 80mm macro lens sharpness, natural fabric grain, pure #FFFFFF white backdrop, 2K crisp lookbook quality."
)


def _normalize_preset_item(pid: str, raw: dict, folder_path: Path | None = None) -> dict:
    item = dict(raw or {})
    item.setdefault("title", pid.replace("_", " ").title())
    item.setdefault("icon", "🎬")
    item.setdefault("badge", "")
    item.setdefault("summary", f"Kịch bản {item['title']} · 2 cảnh 8s → 16s")
    item.setdefault("transition_style", "night_flash" if pid == "fish" else "sunlit")
    item.setdefault("demo", f"{pid}.mp4")
    if folder_path:
        item["_folder"] = str(folder_path)
    return item


def _is_transform_studio_config(cfg: dict, folder_name: str = "") -> bool:
    if not isinstance(cfg, dict):
        return False
    pk = str(cfg.get("pipeline_kind") or "").strip().lower()
    ui_studio = str(cfg.get("ui_studio") or "").strip().lower()
    if ui_studio in {"transform", "transform_studio", "character_product"}:
        return True
    if pk in {"fashion_transformation", "transform_studio", "character_product_studio"}:
        return True
    if isinstance(cfg.get("presets"), (dict, list)) and cfg.get("presets"):
        return True
    if isinstance(cfg.get("transform_presets"), (dict, list)) and cfg.get("transform_presets"):
        return True
    return str(cfg.get("template_code") or "").strip() == "006" or folder_name == "Bien Hinh Thoi Trang"


def _discover_studio_templates() -> list[dict]:
    found: list[dict] = []
    if TEMPLATES_ROOT.is_dir():
        for entry in sorted(TEMPLATES_ROOT.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir() or entry.name.startswith((".", "_")) or entry.name in RESERVED_TEMPLATE_FOLDERS:
                continue
            cfg_path = entry / "template_config.json"
            if not cfg_path.is_file():
                continue
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not _is_transform_studio_config(cfg, entry.name):
                continue
            code = str(cfg.get("code") or cfg.get("template_code") or entry.name).strip()
            raw_presets = cfg.get("presets") or cfg.get("transform_presets")
            presets_map: dict[str, dict] = {}
            if isinstance(raw_presets, dict):
                for pk, pv in raw_presets.items():
                    if isinstance(pv, dict):
                        presets_map[str(pk)] = _normalize_preset_item(str(pk), pv, entry)
            elif isinstance(raw_presets, list):
                for idx, pv in enumerate(raw_presets, 1):
                    if isinstance(pv, dict):
                        pk = str(pv.get("id") or pv.get("key") or f"preset_{idx}")
                        presets_map[pk] = _normalize_preset_item(pk, pv, entry)
            if not presets_map and (code == "006" or entry.name == "Bien Hinh Thoi Trang"):
                presets_map = {k: _normalize_preset_item(k, v, entry) for k, v in PRESETS.items()}
            elif code == "006" or entry.name == "Bien Hinh Thoi Trang":
                merged = {k: _normalize_preset_item(k, v, entry) for k, v in PRESETS.items()}
                merged.update(presets_map)
                presets_map = merged
            if not presets_map:
                continue
            found.append({
                "code": code,
                "name": str(cfg.get("name") or cfg.get("template_name") or entry.name),
                "subtitle": str(cfg.get("subtitle") or cfg.get("short_description") or ""),
                "description": str(cfg.get("description") or cfg.get("short_description") or ""),
                "folder_name": entry.name,
                "folder_path": entry,
                "pipeline_kind": str(cfg.get("pipeline_kind") or "fashion_transformation"),
                "supports_character": cfg.get("supports_character", True) is not False,
                "supports_product": cfg.get("supports_product", True) is not False,
                "character_label": str(cfg.get("character_label") or "Nhân vật tham chiếu"),
                "product_label": str(cfg.get("product_label") or "Sản phẩm / Trang phục"),
                "product_prompt": str(cfg.get("product_prompt") or PRODUCT_PROMPT),
                "presets": presets_map,
            })
    if not any(t["code"] == "006" for t in found):
        found.insert(0, {
            "code": "006",
            "name": "Biến hình thời trang",
            "subtitle": "2 cảnh 8s + chuyển cảnh mượt & khớp nhạc mẫu",
            "description": "Studio tạo video biến hình nhân vật + sản phẩm từ ảnh tham chiếu 2K.",
            "folder_name": ASSETS.name,
            "folder_path": ASSETS,
            "pipeline_kind": "fashion_transformation",
            "supports_character": True,
            "supports_product": True,
            "character_label": "Nhân vật tham chiếu",
            "product_label": "Sản phẩm / Trang phục",
            "product_prompt": PRODUCT_PROMPT,
            "presets": {k: _normalize_preset_item(k, v, ASSETS) for k, v in PRESETS.items()},
        })
    found.sort(key=lambda t: (0 if str(t["code"]).isdigit() else 1, int(t["code"]) if str(t["code"]).isdigit() else str(t["code"])))
    return found


def _resolve_template_and_preset(preset: str, template_code: str | None = None) -> tuple[dict, str, dict]:
    templates = _discover_studio_templates()
    target_tpl = None
    if template_code:
        needle = str(template_code).strip().lower()
        target_tpl = next(
            (t for t in templates if t["code"].lower() == needle or t["folder_name"].lower() == needle),
            None,
        )
    if target_tpl is None and preset:
        target_tpl = next((t for t in templates if preset in t["presets"]), None)
    if target_tpl is None:
        target_tpl = next((t for t in templates if t["code"] == "006"), templates[0])
    presets = target_tpl["presets"]
    chosen = preset if preset in presets else next(iter(presets))
    return target_tpl, chosen, presets[chosen]


def demo_video_path(preset, template_code=None):
    tpl_meta, chosen, cfg = _resolve_template_and_preset(preset, template_code)
    demo_rel = str(cfg.get("demo") or f"{chosen}.mp4")
    tpl_dir = Path(cfg.get("_folder") or tpl_meta["folder_path"])
    candidates = [
        ASSETS / "demo_videos" / demo_rel,
        tpl_dir / "demo_videos" / demo_rel,
        tpl_dir / demo_rel,
    ]
    raw_demo_path = str(cfg.get("demo_path") or "").strip()
    if raw_demo_path:
        dp = Path(raw_demo_path)
        candidates.insert(0, dp if dp.is_absolute() else (ROOT / dp))
    alt_name = cfg.get("alt_demo")
    if alt_name:
        candidates.extend([
            tpl_dir / "demo_videos" / alt_name,
            tpl_dir / "Video mẫu" / alt_name,
            ALT_DEMO_ASSETS / alt_name,
        ])
    for cand in candidates:
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return (tpl_dir / "demo_videos" / demo_rel) if tpl_dir != ASSETS else candidates[0]


def media(path):
    resolved = Path(path).resolve()
    if resolved.is_relative_to(ROOT):
        return str(resolved.relative_to(ROOT)).replace("\\", "/")
    return str(resolved).replace("\\", "/")


def _list_library_characters():
    try:
        import character_library_manager as clm
        lib = clm.get_character_library_state()
        out = []
        for c in lib.get("characters") or []:
            abs_p = Path(str(c.get("ref_image_abs") or ""))
            if not abs_p.is_file():
                continue
            try:
                rel = media(abs_p)
            except ValueError:
                continue
            out.append({
                "key": str(c.get("key") or ""),
                "name": str(c.get("name") or c.get("key") or "Nhân vật"),
                "preview": rel,
                "path": str(abs_p),
            })
        return out
    except Exception:
        return []


def make_prompts(preset, has_character=False, template_code=None, preset_cfg=None):
    p = dict(preset_cfg) if isinstance(preset_cfg, dict) and preset_cfg else _resolve_template_and_preset(preset, template_code)[2]
    if isinstance(p.get("scenes"), list) and len(p["scenes"]) >= 2:
        out_scenes = []
        for idx, sc in enumerate(p["scenes"][:2], 1):
            sc = dict(sc or {})
            out_scenes.append({
                "id": str(sc.get("id") or f"s{idx}"),
                "title": str(sc.get("title") or (f"Cảnh {idx}/2")),
                "duration_sec": int(sc.get("duration_sec") or 8),
                "ref": str(sc.get("ref") or ("before_2k.jpg" if idx == 1 else "reveal_2k.jpg")),
                "image_prompt": str(sc.get("image_prompt") or ""),
                "prompt": str(sc.get("prompt") or ""),
            })
        return out_scenes
    fallback_subject = str(p.get("subject_description") or "Cast one fictional Vietnamese adult woman in her mid-20s.")
    identity = (
        "Match ONLY facial identity (eyes, nose bridge, cheekbones, jawline, lips, skin tone, natural adult proportions) "
        "to Reference 1. Even if Reference 1 is a multi-panel character turnaround sheet or collage, ignore its grid panels, "
        "white borders, and casual/studio outfits and render ONE continuous edge-to-edge single-frame 9:16 live-action photograph."
        if has_character else fallback_subject
    )
    allow_speech = bool(p.get("has_dialogue") or p.get("dialogue_line"))
    speech_tail = (
        "Zero captions, subtitle text overlays, logos, watermarks, or split-screens."
        if allow_speech else
        "Zero captions, text overlays, logos, watermarks, split-screens, or spoken dialogue."
    )
    continuity = (
        "Preserve exact facial geometry and bodily proportions across both shots; only hair, makeup, clothes, and "
        "environment transform. Realistic live-action cinematography, vertical 9:16, natural skin texture and true fabric "
        f"physics, restrained grading. {speech_tail}"
    )
    lock = ("The white-background outfit product sheet (Reference 2) defines the entire reveal wardrobe verbatim: "
            "preserve exact neckline, collar, sleeves, waist, true skirt/dress length and flare (keep short mini silhouettes "
            "above the knee — never elongate them), print placement, buttons, color, seams, and closures, AND style the model "
            "coherently with the extracted footwear, socks, handbag, and hair/jewelry accessories shown in Column 2 of Reference 2. "
            "Never swap garment or cover it with coats.")
    reveal_img_refs = (
        "Reference 1 supplies ONLY face identity (ignore any sheet layout or clothes in Reference 1); "
        "Reference 2 (white background) defines the exact reveal outfit verbatim; "
        "Reference 3 anchors human scale and natural skin realism (replace her old work outfit completely with Reference 2)."
        if has_character else
        "Reference 1 establishes face identity and proportions; Reference 2 (white background) defines the exact reveal garment."
    )
    cover_item = str(p.get("cover_item") or "the held foreground prop or hand")
    work_open = str(p.get("work_open") or f"Immediately engage in the grounded authentic chore shown in the opening frame while holding {cover_item}.")
    work_label = str(p.get("work_label") or "Poised Pause & Direct Gaze")
    cover_label = str(p.get("cover_label") or "Advance Held Item Toward Lens")
    s1_t1 = str(p.get("s1_t1") or "0.0s–1.8s")
    s1_t2 = str(p.get("s1_t2") or "1.8s–4.8s")
    s1_t3 = str(p.get("s1_t3") or "4.8s–6.7s")
    s1_t4 = str(p.get("s1_t4") or "6.7s–8.0s")
    s2_t1 = str(p.get("s2_t1") or "0.0s–2.0s")
    s2_t2 = str(p.get("s2_t2") or "2.0s–4.8s")
    s2_t3 = str(p.get("s2_t3") or "4.8s–8.0s")
    s1_img = p.get("scene1_image_prompt") or f"Single clean edge-to-edge opening still. {identity} {p.get('before', '')} Subject and hands visible, authentic grounded posture. {continuity}"
    s1_vid = p.get("scene1_video_prompt") or (
        f"One continuous 8-second live-action sequence matching the opening reference at crisp natural 1.0x real-time 24fps pace (zero slow-motion). {p.get('before', '')} "
        f"[{s1_t1} Establish Action]: {work_open} "
        f"[{s1_t2} {work_label}]: {p.get('work', '')} "
        f"[{s1_t3} {cover_label}]: {p.get('cover', '')} "
        f"[{s1_t4} Complete 100% Lens Occlusion Contact]: At the start of {s1_t4}, thrust {cover_item} aggressively forward until it physically touches and presses airtight flat against the camera glass — expanding to extreme out-of-focus macro contact that fills 100% of the screen edge-to-edge covering every corner with zero background, face, eyes, hair, or empty void remaining until 8.0s finishes (darkening seamlessly into pitch-black occlusion — NEVER stop halfway at arm's length and never retract or pull back). Zero unwanted cuts. {continuity}"
    )
    s2_img = p.get("scene2_image_prompt") or (
        f"Single clean edge-to-edge luxury fashion reveal still. {reveal_img_refs} Dress the same woman with sleek sculpted luxury hair, refined editorial makeup, and poised commanding aristocratic charisma. "
        f"{p.get('after', '')} {lock} {continuity}"
    )
    s2_vid = p.get("scene2_video_prompt") or (
        f"One seamless 8-second 8K live-action cinema reveal anchored to the opening still at crisp natural human pacing (strictly no dragged slow-motion). "
        f"[{s2_t1} Poised VIP Entrance]: {p.get('reveal_open', '')} "
        f"[{s2_t2} Commanding Presence & Motion]: {p.get('reveal_mid', '')} "
        f"[{s2_t3} Executive Finale & Stance]: {p.get('reveal_end', '')} "
        f"Head, neck, shoulders, and torso move cohesively together — zero body spinning, zero awkward back turns, zero warped garment geometry, 8k cinema film quality. {lock} {continuity}"
    )
    s1_default_title = (
        "Trước biến hình (0–8s · Thoại & Găng hồng che kín camera)"
        if allow_speech else
        "Trước biến hình (0–8s · Vật che tiến sát kín camera)"
    )
    return [
        {"id": "s1", "title": str(p.get("scene1_title") or s1_default_title),
         "duration_sec": 8, "ref": "before_2k.jpg", "image_prompt": s1_img, "prompt": s1_vid},
        {"id": "s2", "title": str(p.get("scene2_title") or "Biến hình quý phái (8–16s · Chuyển cảnh & Pose thanh lịch)"),
         "duration_sec": 8, "ref": "reveal_2k.jpg", "image_prompt": s2_img, "prompt": s2_vid},
    ]


def default(template_code=None):
    templates = _discover_studio_templates()
    active_tpl = None
    if template_code:
        needle = str(template_code).strip().lower()
        active_tpl = next(
            (t for t in templates if t["code"].lower() == needle or t["folder_name"].lower() == needle),
            None,
        )
    if active_tpl is None:
        active_tpl = next((t for t in templates if t["code"] == "006"), templates[0])
    presets_out = {}
    for k, v in active_tpl["presets"].items():
        d_path = demo_video_path(k, active_tpl["code"])
        try:
            demo_rel = media(d_path)
        except ValueError:
            demo_rel = media(ASSETS / "demo_videos" / str(v.get("demo") or f"{k}.mp4"))
        presets_out[k] = {
            "title": v["title"],
            "icon": v.get("icon", "🎬"),
            "badge": v.get("badge", ""),
            "transition_style": v.get("transition_style", "sunlit"),
            "summary": v["summary"],
            "demo": demo_rel,
            "demo_exists": bool(d_path.is_file()),
            "scenes": make_prompts(k, template_code=active_tpl["code"], preset_cfg=v),
        }
    return {
        "ok": True,
        "template": {
            "code": active_tpl["code"],
            "name": active_tpl["name"],
            "subtitle": active_tpl["subtitle"],
            "description": active_tpl["description"],
            "folder_name": active_tpl["folder_name"],
            "pipeline_kind": active_tpl["pipeline_kind"],
            "supports_character": active_tpl["supports_character"],
            "supports_product": active_tpl["supports_product"],
            "character_label": active_tpl["character_label"],
            "product_label": active_tpl["product_label"],
        },
        "studio_templates": [
            {
                "code": t["code"],
                "name": t["name"],
                "subtitle": t["subtitle"],
                "folder_name": t["folder_name"],
                "pipeline_kind": t["pipeline_kind"],
                "preset_count": len(t["presets"]),
                "supports_character": t["supports_character"],
                "supports_product": t["supports_product"],
            }
            for t in templates
        ],
        "presets": presets_out,
        "characters": _list_library_characters(),
        "product_prompt": active_tpl.get("product_prompt") or PRODUCT_PROMPT,
    }


def _write_json_safe(target: Path, payload: dict):
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp = target.parent / f".{target.name}.{uuid4().hex}.tmp"
    try:
        tmp.write_text(text, encoding="utf-8")
        for attempt in range(8):
            try:
                tmp.replace(target)
                return
            except OSError:
                time.sleep(0.04 * (attempt + 1))
        target.write_text(text, encoding="utf-8")
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _read_json_safe(target: Path) -> dict:
    last_exc = None
    for attempt in range(6):
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            last_exc = exc
            time.sleep(0.03 * (attempt + 1))
    raise last_exc


def save(folder, state):
    with LOCK:
        now_ts = round(time.time(), 3)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
        state.setdefault("created_ts", now_ts)
        state.setdefault("created_at", now_str)
        state["updated_ts"] = now_ts
        state["updated_at"] = now_str
        _write_json_safe(folder / "transform.json", state)
        _write_json_safe(folder / "project.json", project_view(folder, state))


def status(job):
    if not re.fullmatch(r"transform_[0-9a-f]{16}", job):
        raise ValueError("Mã dự án không hợp lệ.")
    state = _read_json_safe(JOBS / job / "transform.json")
    if state["status"] in {"running", "queued"} and not is_active(job, state):
        if _is_stopped(job):
            state.update(status="stopped", message="Đã dừng theo yêu cầu người dùng.")
        else:
            state.update(status="error", message="Tiến trình đã dừng. Kiểm tra job trong Flow trước khi tạo lại.")
    return state


def _is_pid_alive(pid):
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return exit_code.value == 259  # STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def is_active(job, state=None):
    if _is_stopped(job):
        return False
    if state is None:
        tj = JOBS / job / "transform.json"
        if not tj.is_file():
            return False
        try:
            state = _read_json_safe(tj)
        except Exception:
            return False
    if not isinstance(state, dict) or state.get("status") not in {"queued", "running"}:
        return False
    if any(t.name == job and t.is_alive() for t in threading.enumerate()):
        return True
    wpid = state.get("worker_pid")
    if wpid:
        return _is_pid_alive(wpid)
    try:
        updated_ts = float(state.get("updated_ts") or 0.0)
    except (TypeError, ValueError):
        updated_ts = 0.0
    if not updated_ts:
        tj = JOBS / job / "transform.json"
        if tj.is_file():
            updated_ts = tj.stat().st_mtime
    return bool(updated_ts and (time.time() - updated_ts) < 120.0)


def product_library():
    from product_crawler_bridge import list_all_products_store
    return {str(p["product_id"]): p for p in list_all_products_store()["products"] if p.get("local_images")}


def products():
    return {"ok": True, "products": [
        {"id": key, "title": p["title"], "category": p["category"],
         "images": [{"index": i, "path": media(path)} for i, path in enumerate(p["local_images"])
                    if Path(path).resolve().is_relative_to(ROOT)]}
        for key, p in product_library().items()]}


def read_image(upload=None, source=None):
    if source:
        source = Path(source).resolve()
        if not source.is_relative_to(ROOT) or source.stat().st_size > 12_000_000:
            raise ValueError("Ảnh trong kho không hợp lệ hoặc vượt 12 MB.")
        raw = source.read_bytes()
    else:
        if not isinstance(upload, str) or len(upload) > 16_000_050:
            raise ValueError("Chọn ảnh quần áo JPG, PNG hoặc WebP, tối đa 12 MB.")
        raw = base64.b64decode(upload.split(",", 1)[-1], validate=True)
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in {"JPEG", "PNG", "WEBP"} or img.width * img.height > 40_000_000:
                raise ValueError("Chỉ hỗ trợ JPG, PNG, WebP tối đa 40 megapixel.")
            return ImageOps.exif_transpose(img).convert("RGB")
    except OSError as exc:
        raise ValueError("Không đọc được ảnh đã chọn.") from exc


def _clean_product_label(raw_label: str) -> str:
    txt = str(raw_label or "").strip()
    if not txt:
        return ""
    if re.search(r"\.(?:jpg|jpeg|png|webp)$", txt, re.IGNORECASE):
        txt = Path(txt).stem
    txt = re.sub(r"\s+", " ", txt).strip(" -_.")
    return txt[:64]


def _run_queued_job(job: str, folder: Path, state: dict, runner=None):
    slot_acquired = False
    try:
        while True:
            with _QUEUE_COND:
                if _is_stopped(job):
                    with LOCK:
                        if state.get("status") in {"queued", "running"}:
                            state.pop("worker_pid", None)
                            state.update(status="stopped", message="Đã dừng theo yêu cầu người dùng.")
                            save(folder, state)
                    return
                limit = _max_transform_slots(runner)
                if len(_ACTIVE_JOBS) < limit:
                    _ACTIVE_JOBS.add(job)
                    slot_acquired = True
                    break
                _QUEUE_COND.wait(timeout=1.5)
        if _is_stopped(job):
            with LOCK:
                if state.get("status") in {"queued", "running"}:
                    state.pop("worker_pid", None)
                    state.update(status="stopped", message="Đã dừng theo yêu cầu người dùng.")
                    save(folder, state)
            return
        with LOCK:
            state["worker_pid"] = os.getpid()
            if state.get("status") == "queued":
                state.update(status="running", message="Đang khởi chạy render video...")
                save(folder, state)
        run(folder, state, runner)
    finally:
        with _QUEUE_COND:
            if slot_acquired:
                _ACTIVE_JOBS.discard(job)
            _STOPPED_JOBS.discard(job)
            _QUEUE_COND.notify_all()


def stop_job(job_id: str) -> dict:
    job = str(job_id or "").strip()
    if not re.fullmatch(r"transform_[0-9a-f]{16}", job):
        raise ValueError("Mã dự án không hợp lệ.")
    folder = JOBS / job
    tj = folder / "transform.json"
    if not tj.is_file():
        return {"ok": False, "error": "Không tìm thấy dự án Biến hình."}
    with _QUEUE_COND:
        _STOPPED_JOBS.add(job)
        _QUEUE_COND.notify_all()
    with LOCK:
        state = _read_json_safe(tj)
        prev_status = str(state.get("status") or "")
        if prev_status in {"queued", "running"}:
            state.pop("worker_pid", None)
            state["status"] = "stopped"
            state["message"] = "Đã dừng theo yêu cầu người dùng."
            save(folder, state)
        return {"ok": True, "id": job, "status": state.get("status"), "previous_status": prev_status}


def list_jobs(template_code: str = "", limit: int = 24) -> dict:
    tpl_filter = str(template_code or "").strip().lstrip("#")
    rows = []
    if JOBS.is_dir():
        for file in JOBS.glob("transform_*/transform.json"):
            try:
                st = _read_json_safe(file)
                code = str(st.get("template_code") or "006").lstrip("#")
                if tpl_filter and code != tpl_filter:
                    continue
                pid = str(st.get("id") or file.parent.name)
                active_now = st.get("status") in {"queued", "running"} and is_active(pid, st)
                pv = project_view(file.parent, st)
                rows.append({
                    "id": pid,
                    "name": pv.get("name") or pid,
                    "template_code": code,
                    "template_name": str(st.get("template_name") or ""),
                    "preset": str(st.get("preset") or ""),
                    "preset_title": str(st.get("preset_title") or ""),
                    "product_label": str(st.get("product_label") or ""),
                    "status": st.get("status") or "queued",
                    "is_running": active_now,
                    "is_queued": bool(active_now and st.get("status") == "queued"),
                    "message": str(st.get("message") or ""),
                    "progress_pct": int(pv.get("progress_pct") or 0),
                    "final": str(st.get("final") or ""),
                    "updated_ts": float(pv.get("updated_ts") or 0.0),
                    "created_ts": float(pv.get("created_ts") or 0.0),
                })
            except Exception:
                continue
    rows.sort(
        key=lambda r: (
            0 if (r["is_running"] and not r["is_queued"]) else (1 if r["is_queued"] else (2 if r["status"] == "done" else 3)),
            -r["created_ts"],
            -r["updated_ts"],
        )
    )
    active_cnt = sum(1 for r in rows if r["is_running"] and not r["is_queued"])
    queued_cnt = sum(1 for r in rows if r["is_queued"])
    return {
        "ok": True,
        "jobs": rows[: max(1, int(limit or 24))],
        "active_count": active_cnt,
        "queued_count": queued_cnt,
        "max_slots": _max_transform_slots(None),
    }


def resume(job_id: str, runner=None) -> dict:
    job = str(job_id or "").strip()
    if not re.fullmatch(r"transform_[0-9a-f]{16}", job):
        raise ValueError("Mã dự án không hợp lệ.")
    folder = JOBS / job
    tj = folder / "transform.json"
    if not tj.is_file():
        raise ValueError("Không tìm thấy dự án Biến hình.")
    with LOCK:
        state = _read_json_safe(tj)
        if state.get("status") in {"queued", "running"} and is_active(job, state):
            return {"ok": True, "id": job, "already_running": True, "project": project_view(folder, state)}
        _STOPPED_JOBS.discard(job)
        state["resume_existing"] = True
        state["status"] = "queued"
        state["message"] = "Đang xếp hàng chạy tiếp các bước còn thiếu..."
        state.pop("worker_pid", None)
        save(folder, state)
        threading.Thread(target=_run_queued_job, args=(job, folder, state, runner), name=job, daemon=True).start()
    return {"ok": True, "id": job, "project": project_view(folder, state)}


def start(body, runner=None):
    template_code = str(body.get("template_code") or "").strip() or None
    raw_preset = str(body.get("preset") or "").strip()
    model = body.get("image_provider", "banana")
    video_model = str(body.get("video_model") or DEFAULT_VIDEO_MODEL).strip() or DEFAULT_VIDEO_MODEL
    try:
        tpl_meta, preset, preset_cfg = _resolve_template_and_preset(raw_preset, template_code)
    except ValueError:
        tpl_meta, preset, preset_cfg = None, "", {}
    if not tpl_meta or raw_preset not in tpl_meta["presets"] or model not in {"banana", "chatgpt", "cliproxy_gemini"}:
        raise ValueError("Chọn kịch bản và model ảnh hợp lệ.")
    if video_model not in SUPPORTED_VIDEO_MODELS:
        raise ValueError("Chọn model tạo video hợp lệ.")
    if not shutil.which("ffmpeg"):
        raise ValueError("Cần cài FFmpeg trước khi tạo video.")
    demo_path = demo_video_path(preset, tpl_meta["code"])
    if body.get("music") is not False and not demo_path.is_file():
        raise ValueError("Thiếu video mẫu để ghép âm thanh. Hãy tắt âm thanh hoặc khôi phục video mẫu.")
    source = None
    product_label = _clean_product_label(body.get("product_label") or body.get("product_filename") or "")
    if body.get("product_id"):
        item = product_library().get(str(body["product_id"]))
        idx = int(body.get("image_index", 0))
        if not item or not 0 <= idx < len(item["local_images"]):
            raise ValueError("Ảnh sản phẩm đã chọn không còn trong kho.")
        source = item["local_images"][idx]
        if not product_label:
            product_label = _clean_product_label(item.get("title") or "")
    garment = read_image(body.get("product_upload"), source)
    character = None
    char_key = str(body.get("character_key") or "").strip()
    if body.get("character_upload"):
        character = read_image(body["character_upload"])
    elif char_key:
        match_char = next((c for c in _list_library_characters() if c["key"] == char_key), None)
        if not match_char:
            raise ValueError("Nhân vật đã chọn không còn ảnh tham chiếu trong thư viện.")
        character = read_image(source=match_char["path"])
    job = "transform_" + uuid4().hex[:16]
    folder = JOBS / job
    now_ts = round(time.time(), 3)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
    refs_init = {}
    state = {"ok": True, "id": job, "status": "queued", "message": "Đang xếp hàng chạy đa luồng — chờ luồng trống...",
             "created_ts": now_ts, "updated_ts": now_ts, "created_at": now_str, "updated_at": now_str,
             "template_code": tpl_meta["code"], "template_name": tpl_meta["name"],
             "template_folder": tpl_meta["folder_name"],
             "preset": preset, "preset_title": preset_cfg.get("title", preset),
             "product_label": product_label,
             "transition_style": preset_cfg.get("transition_style", "night_flash" if preset == "fish" else "sunlit"),
             "image_provider": model, "video_model": video_model,
             "music": body.get("music") is not False,
             "character_key": char_key,
             "product_prompt": tpl_meta.get("product_prompt") or PRODUCT_PROMPT,
             "scenes": make_prompts(preset, character is not None, template_code=tpl_meta["code"], preset_cfg=preset_cfg),
             "refs": refs_init}
    with LOCK:
        max_concurrent_jobs = _max_transform_slots(runner)
        active_now = len(_ACTIVE_JOBS)
        if active_now < max_concurrent_jobs:
            state["message"] = f"Đang khởi tạo luồng render ({active_now + 1}/{max_concurrent_jobs})..."
        else:
            state["message"] = f"Đang xếp hàng chạy đa luồng ({active_now}/{max_concurrent_jobs} luồng bận)..."
        folder.mkdir(parents=True)
        garment.save(folder / "product_input.jpg", quality=97)
        if character:
            char_dest = folder / "character_input.jpg"
            character.save(char_dest, quality=97)
            refs_init["character"] = {"path": media(char_dest), "dimensions": list(character.size)}
        save(folder, state)
        threading.Thread(target=_run_queued_job, args=(job, folder, state, runner), name=job, daemon=True).start()
        proj_snapshot = project_view(folder, state)
    return {"ok": True, "id": job, "project": proj_snapshot, "max_slots": max_concurrent_jobs}


def native_dimensions(path):
    with Image.open(path) as im:
        w, h = im.size
        if max(w, h) < 2048 or min(w, h) < 1152:
            scale = max(2048 / max(1, max(w, h)), 1152 / max(1, min(w, h)))
            tw = max(2, int(round(w * scale / 2.0)) * 2)
            th = max(2, int(round(h * scale / 2.0)) * 2)
            up = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            ext_low = str(Path(path).suffix or "").lower()
            if ext_low in (".jpg", ".jpeg"):
                up.save(path, format="JPEG", quality=96, subsampling=0)
            else:
                up.save(path, format="PNG")
            return [tw, th]
        return [w, h]


def _probe_stream_duration(path: Path, stream_selector: str = "a:0") -> tuple[bool, float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path or not Path(path).is_file():
        return (bool(path and Path(path).is_file()), 0.0)
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", stream_selector,
             "-show_entries", "stream=index,duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if r.returncode != 0:
            return (False, 0.0)
        lines = [line.strip() for line in (r.stdout or "").splitlines() if line.strip()]
        if not lines:
            return (False, 0.0)
        for v in lines[1:]:
            if v != "N/A":
                try:
                    return (True, float(v))
                except ValueError:
                    continue
        # Fallback to container duration only after confirming the stream actually exists.
        rf = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=15, check=False,
        )
        for v in (rf.stdout or "").splitlines():
            v = v.strip()
            if v and v != "N/A":
                try:
                    return (True, float(v))
                except ValueError:
                    continue
        return (True, 0.0)
    except Exception:
        return (False, 0.0)


def _probe_audio_duration(path: Path) -> tuple[bool, float]:
    return _probe_stream_duration(path, "a:0")


def _detect_occlusion_peak(clip_path: Path, vid_dur: float) -> float | None:
    """Locate an early lens-occlusion dip when Veo lowers the hoe/hand before 8.0s."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or vid_dur < 5.2 or not clip_path.is_file():
        return None
    scan_start, scan_fps, w, h = 4.5, 15, 24, 42
    frame_bytes = w * h
    try:
        proc = subprocess.run(
            [ffmpeg, "-v", "error", "-ss", f"{scan_start:.3f}", "-i", str(clip_path),
             "-vf", f"fps={scan_fps},scale={w}:{h},format=gray",
             "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
            capture_output=True, timeout=20, check=False,
        )
        raw = proc.stdout or b""
        n_frames = len(raw) // frame_bytes
        if n_frames < 8:
            return None
        stats = []
        for i in range(n_frames):
            buf = raw[i * frame_bytes:(i + 1) * frame_bytes]
            mean_y = sum(buf) / frame_bytes
            center_vals = [buf[r * w + c] for r in range(11, 31) for c in range(6, 18)]
            center_y = sum(center_vals) / len(center_vals)
            dark_ratio = sum(1 for px in buf if px < 52) / frame_bytes
            score = 0.52 * mean_y + 0.48 * center_y - 26.0 * dark_ratio
            stats.append((scan_start + i / scan_fps, mean_y, dark_ratio, score))
        best_t, min_y, min_dark, _ = min(stats, key=lambda item: item[3])
        tail_frames = [s[1] for s in stats[-6:]]
        tail_y = sum(tail_frames) / len(tail_frames)
        # Only trim & align if the clip genuinely hit a near-black lens cover and then accidentally pulled away.
        # Prevents false-triggering on darker close-up portraits or bright-colored covers (like pink gloves) which caused 1.45x slow-mo!
        if best_t < vid_dur - 0.45 and min_y < 36.0 and min_dark >= 0.72 and (tail_y - min_y >= 22.0):
            return max(5.2, min(best_t, vid_dur))
    except Exception:
        return None
    return None


def _detect_fish_scene_cuts(clip_path: Path, vid_dur: float) -> tuple[float, float] | None:
    """Detect the two hard shot cuts (market -> ex-couple, ex-couple -> tearful woman) inside Scene 1."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or vid_dur < 4.5 or not clip_path.is_file():
        return None
    scan_fps, w, h = 20, 24, 42
    frame_bytes = w * h
    try:
        proc = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(clip_path),
             "-t", f"{min(vid_dur, 8.2):.3f}",
             "-vf", f"fps={scan_fps},scale={w}:{h},format=gray",
             "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
            capture_output=True, timeout=20, check=False,
        )
        raw = proc.stdout or b""
        n_frames = len(raw) // frame_bytes
        if n_frames < 20:
            return None
        diffs = []
        for i in range(1, n_frames):
            a = raw[(i - 1) * frame_bytes:i * frame_bytes]
            b = raw[i * frame_bytes:(i + 1) * frame_bytes]
            diff = sum(abs(b[k] - a[k]) for k in range(frame_bytes)) / frame_bytes
            diffs.append((i / scan_fps, diff))
        cands1 = [(t, d) for t, d in diffs if 0.85 <= t <= min(4.30, vid_dur - 2.20) and d >= 28.0]
        if not cands1:
            return None
        c1, _ = max(cands1, key=lambda item: item[1])
        cands2 = [(t, d) for t, d in diffs if max(c1 + 1.10, 2.50) <= t <= min(6.75, vid_dur - 0.90) and d >= 28.0]
        if not cands2:
            return None
        c2, _ = max(cands2, key=lambda item: item[1])
        return (c1, c2)
    except Exception:
        return None


def _build_scene1_video_filter(clip_path: Path, preset: str = "", demo_path: Path | None = None) -> str:
    _, vid_dur = _probe_stream_duration(clip_path, "v:0")
    peak_t = _detect_occlusion_peak(clip_path, vid_dur)
    scale_base = "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    is_fish = preset == "fish"
    cuts = _detect_fish_scene_cuts(clip_path, vid_dur) if is_fish else None
    if cuts:
        c1, c2 = cuts
        cover_end = min(vid_dur, peak_t + 0.14) if peak_t and peak_t > c2 + 0.85 else vid_dur
        # Lock visual cuts onto demo 02_ban_ca.mp4 speech timing (cut1 ~3.05s, dialogue 3.18..5.30s, cut2 ~5.40s).
        target_c1, target_c2, target_end = 3.00, 5.42, 7.78
        if demo_path and Path(demo_path).is_file():
            _, d_dur = _probe_stream_duration(Path(demo_path), "v:0")
            demo_cuts = _detect_fish_scene_cuts(Path(demo_path), min(d_dur or 8.0, 8.2))
            if demo_cuts:
                dc1, dc2 = demo_cuts
                if 2.4 <= dc1 <= 3.8 and dc1 + 1.5 <= dc2 <= 6.2:
                    target_c1, target_c2 = dc1, dc2
        dur1 = max(0.50, c1)
        dur2 = max(0.60, c2 - c1)
        dur3 = max(0.60, cover_end - c2)
        d_target1 = target_c1
        d_target2 = max(1.40, target_c2 - target_c1)
        d_target3 = max(1.40, target_end - target_c2)
        s1_warp = max(0.65, min(1.55, d_target1 / dur1))
        s2_warp = max(0.65, min(1.65, d_target2 / dur2))
        s3_warp = max(0.65, min(1.65, d_target3 / dur3))
        pad1 = max(0.0, d_target1 - dur1 * s1_warp) + 0.25
        pad2 = max(0.0, d_target2 - dur2 * s2_warp) + 0.25
        pad3 = max(0.0, d_target3 - dur3 * s3_warp) + 0.25
        head = (
            f"[0:v]{scale_base},split=3[sv1][sv2][sv3];"
            f"[sv1]trim=start=0:end={c1:.3f},setpts=(PTS-STARTPTS)*{s1_warp:.5f},"
            f"tpad=stop_mode=clone:stop_duration={pad1:.3f},trim=duration={d_target1:.3f},setpts=PTS-STARTPTS[sp1];"
            f"[sv2]trim=start={c1:.3f}:end={c2:.3f},setpts=(PTS-STARTPTS)*{s2_warp:.5f},"
            f"tpad=stop_mode=clone:stop_duration={pad2:.3f},trim=duration={d_target2:.3f},setpts=PTS-STARTPTS[sp2];"
            f"[sv3]trim=start={c2:.3f}:end={cover_end:.3f},setpts=(PTS-STARTPTS)*{s3_warp:.5f},"
            f"tpad=stop_mode=clone:stop_duration={pad3:.3f},trim=duration={d_target3:.3f},setpts=PTS-STARTPTS[sp3];"
            f"[sp1][sp2][sp3]concat=n=3:v=1:a=0,tpad=stop_mode=clone:stop_duration=0.40,trim=duration=8,setpts=PTS-STARTPTS"
        )
    elif peak_t:
        trim_end = min(vid_dur, peak_t + 0.14)
        stretch = 7.76 / max(trim_end, 1.0)
        head = (f"[0:v]trim=start=0:end={trim_end:.3f},setpts=(PTS-STARTPTS)*{stretch:.5f},"
                f"{scale_base},tpad=stop_mode=clone:stop_duration=2,trim=duration=8,setpts=PTS-STARTPTS")
    else:
        head = f"[0:v]{scale_base},tpad=stop_mode=clone:stop_duration=8,trim=duration=8,setpts=PTS-STARTPTS"
    # Push smoothly right into the solid center-lower palm across 6.68-7.48s and darken cleanly into lens seal by 7.76s.
    zoom_strength = 1.90 if is_fish else 0.52
    zoom_start = 6.68 if is_fish else 6.50
    zoom_span = 0.80 if is_fish else 1.28
    y_bias = 0.66 if is_fish else 0.50
    # Note: ffmpeg crop keeps init iw/ih when paired with scale(eval=frame); bind crop x/y directly to scaled dimensions via t.
    zoom_expr = f"(1+{zoom_strength:.2f}*pow(clip((t-{zoom_start:.2f})/{zoom_span:.2f},0,1),2))"
    scaled_w = f"trunc(1080*{zoom_expr}/2)*2"
    scaled_h = f"trunc(1920*{zoom_expr}/2)*2"
    push_zoom = (
        f"scale=w='{scaled_w}':h='{scaled_h}':eval=frame:flags=bilinear,"
        f"crop=1080:1920:x='({scaled_w}-1080)/2':y='({scaled_h}-1920)*{y_bias:.2f}',setsar=1"
    )
    eclipse = (
        "fade=t=out:st=7.32:d=0.44,drawbox=color=black:t=fill:enable='gte(t,7.76)'"
        if is_fish
        else "fade=t=out:st=7.58:d=0.20,drawbox=color=black:t=fill:enable='gte(t,7.78)'"
    )
    return f"{head},{push_zoom},{eclipse}[a]"


def _build_scene2_video_filter(preset: str, transition_style: str = "") -> str:
    base = ("fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
            "tpad=stop_mode=clone:stop_duration=8,trim=duration=8,setpts=PTS-STARTPTS")
    is_flash = transition_style == "night_flash" or (not transition_style and preset == "fish")
    zoom_amt = 0.22 if is_flash else 0.18
    zoom_dur = 0.50 if is_flash else 0.55
    settle_zoom = (
        f"scale=w='trunc(1080*(1+{zoom_amt}*pow(clip(1-t/{zoom_dur},0,1),2))/2)*2':"
        f"h='trunc(1920*(1+{zoom_amt}*pow(clip(1-t/{zoom_dur},0,1),2))/2)*2':eval=frame:flags=bilinear,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)*0.36,setsar=1"
    )
    if is_flash:
        reveal_fx = (
            "fade=t=in:st=0:d=0.14,"
            "eq=brightness='0.34*exp(-pow((t-0.12)/0.075,2))':"
            "gamma='1+0.25*exp(-pow((t-0.12)/0.08,2))':"
            "saturation='1+0.22*exp(-pow((t-0.18)/0.16,2))':eval=frame:enable='between(t,0.02,0.52)'"
        )
    else:
        reveal_fx = (
            "fade=t=in:st=0:d=0.14,"
            "eq=brightness='0.22*exp(-pow((t-0.12)/0.09,2))':"
            "contrast='1+0.12*exp(-pow((t-0.12)/0.11,2))':"
            "saturation='1+0.18*exp(-pow((t-0.16)/0.16,2))':eval=frame:enable='between(t,0.02,0.56)'"
        )
    return f"[1:v]{base},{settle_zoom},{reveal_fx}[b]"


def _build_audio_spec(preset: str, demo: Path, audio_dur: float, clip1_has_audio: bool) -> tuple[list[str], str]:
    fmt = "aformat=sample_rates=44100:channel_layouts=stereo"
    use_beat_sync = (preset == "farm" and audio_dur >= 12.6) or (preset == "fish" and audio_dur >= 16.0)
    if use_beat_sync and preset == "farm":
        # Chorus beat drop in 01_lam_nong.mp4 is at 5.40s -> starting main song at t=2.60s lands drop cleanly at 8.00s.
        main_dur = min(audio_dur - 0.02, 12.68)
        tail_dur = 1.15
        tail_start = max(0.0, main_dur - tail_dur)
        intro_dur = 2.78
        extra_inputs = [
            "-ss", "0", "-t", f"{intro_dur:.3f}", "-i", str(demo),
            "-ss", "0", "-t", f"{main_dur:.3f}", "-i", str(demo),
            "-ss", f"{tail_start:.3f}", "-t", f"{tail_dur:.3f}", "-i", str(demo),
        ]
        if clip1_has_audio:
            intro = (
                f"[2:a:0]{fmt},lowpass=f=280,volume=0.14,afade=t=in:st=0:d=0.60[dm];"
                f"[0:a:0]{fmt},atrim=0:{intro_dur:.3f},asetpts=PTS-STARTPTS,"
                f"highpass=f=120,lowpass=f=5500,volume=3.6,alimiter=limit=0.78,afade=t=in:st=0:d=0.20[c1];"
                f"[dm][c1]amix=inputs=2:duration=first:normalize=0[ap];"
            )
        else:
            intro = f"[2:a:0]{fmt},lowpass=f=320,volume=0.28,afade=t=in:st=0:d=0.60[ap];"
        graph = (
            f";{intro}"
            f"[3:a:0]{fmt},afade=t=in:st=0:d=0.55[am];"
            f"[ap][am]acrossfade=d=0.18:c1=tri:c2=tri[apam];"
            f"[4:a:0]{fmt},lowpass=f=360,volume=0.42,afade=t=in:st=0:d=0.18[at];"
            f"[apam][at]acrossfade=d=0.18:c1=tri:c2=tri,atrim=duration=16,afade=t=out:st=14.95:d=1.05[aout]"
        )
        return (extra_inputs, graph)
    if use_beat_sync and preset == "fish":
        # 02_ban_ca.mp4 has exact dramatic timing aligned to our 8.0s+8.0s structure:
        # 0.00..7.80s wet-market scaling SFX + verbatim Vietnamese dialogue ("Tháng sau bọn anh cưới..."),
        # seamlessly hitting the song chorus drop ("Vốn phận mình thân nữ nhi...") right at ~7.80..8.00s.
        return (
            ["-ss", "0", "-t", "16.000", "-i", str(demo)],
            f";[2:a:0]{fmt},atrim=duration=16,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.12,afade=t=out:st=15.30:d=0.70[aout]",
        )
    return (
        ["-stream_loop", "-1", "-i", str(demo)],
        f";[2:a:0]{fmt},atrim=duration=16,asetpts=PTS-STARTPTS,afade=t=out:st=15.35:d=0.65[aout]",
    )


def export(clips, demo, out, preset="farm", transition_style=""):
    if len(clips) != 2:
        raise ValueError("Template 006 cần đúng hai cảnh.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Không tìm thấy FFmpeg.")
    args = [ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-filter_complex_threads", "2"]
    for clip in clips:
        args += ["-i", str(clip)]
    has_audio, audio_dur = _probe_audio_duration(Path(demo)) if demo else (False, 0.0)
    clip1_has_audio, clip1_aud_dur = _probe_audio_duration(Path(clips[0]))
    s1_filter = _build_scene1_video_filter(Path(clips[0]), preset=preset, demo_path=Path(demo) if demo else None)
    s2_filter = _build_scene2_video_filter(preset, transition_style)
    graph = f"{s1_filter};{s2_filter};[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]"
    audio_map = []
    if demo and has_audio:
        extra_inputs, audio_graph = _build_audio_spec(
            preset, Path(demo), audio_dur, clip1_has_audio and clip1_aud_dur >= 6.0
        )
        args += extra_inputs
        graph += audio_graph
        audio_map = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    args += ["-filter_complex", graph, "-map", "[v]", *audio_map]
    args += ["-t", "16", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(out)]
    subprocess.run(args, check=True, capture_output=True, timeout=240)


def run(folder, state, runner=None):
    import asyncio

    def update(message, phase="running"):
        if phase in {"running", "queued"} and _is_stopped(state["id"]):
            raise JobStoppedError("Đã dừng theo yêu cầu người dùng.")
        if phase in {"running", "queued"}:
            state["worker_pid"] = os.getpid()
        else:
            state.pop("worker_pid", None)
        state.update(status=phase, message=message)
        save(folder, state)

    try:
        if runner is None:
            with _QUEUE_COND:
                runner = globals().get("_SHARED_TRANSFORM_RUNNER")
                if runner is None:
                    from veo_skill_cli import MultiThreadSkillRunner
                    runner = MultiThreadSkillRunner()
                    globals()["_SHARED_TRANSFORM_RUNNER"] = runner
        flow = runner.gvt
        candidates = [
            (account.name, flow._google_profile_name_for_account(account, allow_unresolved=True), token, project)
            for account, token, project in runner.flow_account_candidates()
        ]

        from google_flow_auth import expected_email
        auth_root = flow._auth_root_value(None)

        def matches_profile(profile, email):
            expected = str(expected_email(auth_root, profile) or "").strip().casefold() if profile else ""
            actual = str(email or "").strip().casefold()
            return "@" in actual and (not expected or actual == expected)

        def is_bearer(token):
            return len(token or "") >= 20 and not (
                token.startswith("flow_cookie:") or ("SID=" in token and "__Secure-" in token))

        def _validate_candidate(candidate):
            name, profile, token, project = candidate
            if is_bearer(token):
                valid, identity = flow.GoogleTokenRefreshWorker._check_token(token)
                if valid and matches_profile(profile, identity):
                    return candidate
            cookie = flow._load_flow_cookie_header(profile) if profile else ""
            cand_tokens = []
            if cookie:
                cand_tokens.append("flow_cookie:" + cookie)
            if token and not is_bearer(token):
                cand_tok = token if (token.startswith("flow_cookie:") or "SID=" in token) else ""
                if cand_tok and cand_tok not in cand_tokens:
                    cand_tokens.append(cand_tok)
            for tok in cand_tokens:
                valid, identity = flow.GoogleTokenRefreshWorker._check_token(tok)
                if valid and matches_profile(profile, identity):
                    return (name, profile, tok, project)
            return None

        valid_candidates = []
        seen_profiles = set()
        if len(candidates) > 1:
            update(f"Đang kiểm tra song song {len(candidates)} phiên Google Flow...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(candidates))) as ck_pool:
                checked_list = list(ck_pool.map(_validate_candidate, candidates))
        else:
            checked_list = [_validate_candidate(c) for c in candidates]
        for res_cand in checked_list:
            if res_cand:
                valid_candidates.append(res_cand)
                seen_profiles.add(res_cand[1] or res_cand[0])

        refreshable_candidates = [
            (name, profile, project)
            for name, profile, _, project in candidates
            if profile and (profile not in seen_profiles and name not in seen_profiles)
        ]

        def _try_refresh_backups():
            recovered = []
            while refreshable_candidates:
                name, profile, project = refreshable_candidates.pop(0)
                if profile in seen_profiles:
                    continue
                update(f"Đang làm mới phiên Flow dự phòng của {profile}...")
                valid, token, new_project, identity = flow._refresh_google_profile(profile)
                if not valid or not token:
                    continue
                email = str(identity).removeprefix("session_verified:")
                if matches_profile(profile, email):
                    cand = (name, profile, token, new_project or project)
                    valid_candidates.append(cand)
                    seen_profiles.add(profile)
                    recovered.append(cand)
            return recovered

        if not valid_candidates:
            _try_refresh_backups()
        if not valid_candidates:
            raise RuntimeError(f"Không có phiên Flow hợp lệ sau khi kiểm tra {len(candidates)} tài khoản đang bật.")

        _state_lock = threading.Lock()
        _rr_lock = threading.Lock()
        _rr_cursor = [0]

        def request(label, prompt, out, model, refs, *, video=False, aspect_ratio="9:16"):
            if _is_stopped(state["id"]):
                raise JobStoppedError("Đã dừng theo yêu cầu người dùng.")
            last_err = ""
            last_kind = "transient"
            tried_keys = set()
            transient_retried = False
            while True:
                with _rr_lock:
                    available = [c for c in valid_candidates if (c[1] or c[0]) not in tried_keys]
                    if available:
                        start = _rr_cursor[0] % len(available)
                        _rr_cursor[0] += 1
                        attempts = available[start:] + available[:start]
                        if hasattr(flow, "sort_flow_candidates_by_health"):
                            attempts = flow.sort_flow_candidates_by_health(attempts, lambda c: c[1] or c[0])
                    else:
                        attempts = []
                if not attempts:
                    with _rr_lock:
                        if _try_refresh_backups():
                            continue
                    if (
                        not transient_retried
                        and valid_candidates
                        and last_kind in ("transient", "captcha_score")
                    ):
                        transient_retried = True
                        tried_keys.clear()
                        wait_s = random.uniform(2.0, 4.0)
                        update(f"⏳ {label} gặp lỗi tạm thời [{last_kind}], chờ {wait_s:.1f}s rồi thử lại...")
                        time.sleep(wait_s)
                        continue
                    break
                has_more = (len(attempts) + len(refreshable_candidates)) > 1
                for cand_idx, cand in enumerate(attempts):
                    c_name, c_profile, c_token, c_project = cand
                    acct_key = c_profile or c_name
                    tried_keys.add(acct_key)
                    update(f"Đang gửi request Flow · {label} ({acct_key}).")
                    job = flow.VideoJob(
                        id=f"{state['id']}_{out.stem}", prompt=prompt, model=model,
                        resolution="720p" if video else "2K", aspect_ratio=aspect_ratio,
                        mode="image-to-video" if video else "text-to-video", duration=8,
                        image_url=str(refs[0]) if video else None,
                        reference_image_urls=[] if video else list(map(str, refs)),
                        local_path=str(out), account_name=c_name, google_profile_name=c_profile,
                        max_retries=1 if has_more else 2,
                        prefer_bearer_request=is_bearer(c_token),
                        require_all_reference_uploads=True, flow_request_only=True,
                    )
                    runner._throttle_flow_submit(account_key=acct_key)
                    ok = asyncio.run(
                        flow.run_veo_flow(
                            job,
                            c_token,
                            c_project,
                            runner.ensure_captcha_bridge(),
                            log=lambda msg, lb=label: update(f"{lb}: {msg}"),
                            progress=None,
                        )
                    )
                    if ok and out.is_file():
                        if hasattr(flow, "clear_flow_account_cooldown"):
                            for _k in (c_profile, c_name):
                                if _k:
                                    flow.clear_flow_account_cooldown(_k)
                        return
                    last_err = job.error or "Flow không trả file."
                    last_kind = (
                        flow.classify_flow_error(last_err)
                        if hasattr(flow, "classify_flow_error")
                        else "transient"
                    )
                    short_err = (
                        flow.format_flow_error_short(last_err, 120)
                        if hasattr(flow, "format_flow_error_short")
                        else last_err[:120]
                    )
                    if (
                        (hasattr(flow, "should_stop_all_accounts") and flow.should_stop_all_accounts(last_err))
                        or last_kind == "content_policy"
                    ):
                        vi_err = (
                            flow.describe_flow_error_vi(last_err)
                            if hasattr(flow, "describe_flow_error_vi")
                            else last_err
                        )
                        update(f"❌ {label}: {vi_err}")
                        raise RuntimeError(f"{label}: {vi_err}")

                    if hasattr(flow, "mark_flow_account_cooldown"):
                        for _k in (c_profile, c_name):
                            if _k:
                                flow.mark_flow_account_cooldown(_k, last_kind, last_err)
                    if c_profile and last_kind in ("account_auth", "captcha_score") and hasattr(flow, "invalidate_flow_chrome_session"):
                        flow.invalidate_flow_chrome_session(c_profile)
                    if cand_idx + 1 < len(attempts) or refreshable_candidates:
                        update(f"⚠️ {label} lỗi [{last_kind}] trên {acct_key} ({short_err}), tự động chuyển sang tài khoản tiếp theo...")
            final_vi = (
                flow.describe_flow_error_vi(last_err)
                if last_err and hasattr(flow, "describe_flow_error_vi")
                else (last_err or "Flow không trả file.")
            )
            raise RuntimeError(f"{label}: {final_vi}")

        def image(name, prompt, inputs, aspect_ratio="9:16"):
            out = folder / f"{name}_2k.jpg"
            if state.get("resume_existing") and out.is_file() and out.stat().st_size > 20_000:
                dims = native_dimensions(out)
                with _state_lock:
                    state["refs"][name] = {"path": media(out), "dimensions": dims}
                    save(folder, state)
                return out
            raw = out.with_suffix(".png")
            if state["image_provider"] in ("chatgpt", "cliproxy_gemini"):
                from engine_settings_manager import _render_thumbnail_via_chatgpt
                is_gem = state["image_provider"] == "cliproxy_gemini"
                update(f"Đang tạo ảnh {name} bằng {'Gemini CLIProxy' if is_gem else 'ChatGPT Image'}.")
                ok, _, error = _render_thumbnail_via_chatgpt({
                    "image_model": "gemini-3.1-flash-image" if is_gem else "gpt-image-2",
                    "image_size": "1024x1536",
                    "aspect_ratio": aspect_ratio,
                    "output_format": "png",
                    "reference_images": list(map(str, inputs)),
                    "prompt": prompt,
                }, str(raw))
                if not ok:
                    raise RuntimeError(f"Tạo ảnh {name}: {error}")
            else:
                request(f"Ảnh {name}", prompt, raw, "Nano Banana 2", inputs, aspect_ratio=aspect_ratio)
            dims = native_dimensions(raw)
            with Image.open(raw) as im:
                im.convert("RGB").save(out, quality=98, subsampling=0)
            raw.unlink()
            with _state_lock:
                state["refs"][name] = {"path": media(out), "dimensions": dims}
                save(folder, state)
            return out

        first, second = state["scenes"]
        character = folder / "character_input.jpg"
        first_inputs = [character] if character.is_file() else []
        first_prompt = first["image_prompt"]
        needs_product_for_before = not first_inputs and state["image_provider"] in ("chatgpt", "cliproxy_gemini")
        video_model = str(state.get("video_model") or DEFAULT_VIDEO_MODEL).strip() or DEFAULT_VIDEO_MODEL

        def _render_scene(idx_and_pair):
            i, scene, ref = idx_and_pair
            clip = folder / f"scene_{i}.mp4"
            if state.get("resume_existing") and clip.is_file() and clip.stat().st_size > 200_000:
                ok_dur, vid_dur = _probe_stream_duration(clip, "v:0")
                if ok_dur and vid_dur >= 6.0:
                    with _state_lock:
                        scene["video_path"] = media(clip)
                        save(folder, state)
                    return i, clip
            request(f"Cảnh {i}/2", scene["prompt"], clip, video_model, [ref], video=True)
            with _state_lock:
                scene["video_path"] = media(clip)
                save(folder, state)
            return i, clip

        try:
            import engine_settings_manager as _esm_tf
            _tf_workers = max(4, min(16, int(_esm_tf.get_effective_flow_concurrency().get("flow_api_workers") or 6)))
        except Exception:
            _tf_workers = 4

        clips_map = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=_tf_workers) as dag_pool:
            if needs_product_for_before:
                product = image("product", state.get("product_prompt") or PRODUCT_PROMPT, [folder / "product_input.jpg"], aspect_ratio="3:4")
                first_inputs = [product]
                first_prompt += " Ignore the input garment for this shot; it appears only after the transformation."
                before = image("before", first_prompt, first_inputs)
                fut_s1 = dag_pool.submit(_render_scene, (1, first, before))
                reveal_inputs = [character, product, before] if character.is_file() else [before, product]
                reveal = image("reveal", second["image_prompt"], reveal_inputs)
                fut_s2 = dag_pool.submit(_render_scene, (2, second, reveal))
            else:
                fut_prod = dag_pool.submit(
                    image, "product", state.get("product_prompt") or PRODUCT_PROMPT, [folder / "product_input.jpg"], aspect_ratio="3:4"
                )
                fut_before = dag_pool.submit(image, "before", first_prompt, first_inputs)
                # Gối đầu: ngay khi có ảnh Trước biến hình -> chạy luôn Cảnh 1 trong khi vẫn tạo Reveal + tải 2K Product!
                before = fut_before.result()
                fut_s1 = dag_pool.submit(_render_scene, (1, first, before))
                product = fut_prod.result()
                reveal_inputs = [character, product, before] if character.is_file() else [before, product]
                reveal = image("reveal", second["image_prompt"], reveal_inputs)
                fut_s2 = dag_pool.submit(_render_scene, (2, second, reveal))

            for fut_sc in (fut_s1, fut_s2):
                i_sc, clip_sc = fut_sc.result()
                clips_map[i_sc] = clip_sc
        clips = [clips_map[i] for i in sorted(clips_map)]
        update("Đang ghép chuyển cảnh mượt & đồng bộ nhạc video mẫu.")
        final = folder / "video_final.mp4"
        demo = demo_video_path(state["preset"], state.get("template_code"))
        export(clips, demo if state["music"] else None, final, preset=state["preset"], transition_style=state.get("transition_style", ""))
        state["final"] = media(final)
        update("Đang tự động tạo Ảnh Thumbnail AI và ghép 0.1s đầu video.")
        try:
            import engine_settings_manager as _esm
            th_res = _esm.ensure_project_variant_thumbnail_and_inject(
                state["id"],
                vkey="nv1_v1",
                final_video_path=str(final),
                log_cb=lambda m: update(m),
            )
            t_path = str(th_res.get("project_thumbnail_path") or th_res.get("thumbnail_path") or "").strip()
            if t_path and Path(t_path).is_file():
                state["thumbnail"] = media(Path(t_path))
                state["thumbnail_path"] = t_path
                state["thumbnail_injected_01s"] = bool(th_res.get("injected_01s"))
        except Exception as ex_th:
            update(f"Bỏ qua tự tạo thumbnail: {ex_th}")
        try:
            fv_dir = ROOT / "final_videos"
            fv_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(final, fv_dir / f"{state['id']}_{state['preset']}_final.mp4")
        except OSError:
            pass
        state.pop("resume_existing", None)
        update("Đã xuất video 16 giây.", "done")
    except JobStoppedError as exc:
        state.pop("resume_existing", None)
        state.pop("worker_pid", None)
        state.update(status="stopped", message=str(exc) or "Đã dừng theo yêu cầu người dùng.")
        save(folder, state)
    except Exception as exc:
        state.pop("resume_existing", None)
        if isinstance(exc, subprocess.CalledProcessError):
            raw_err_b = exc.stderr or exc.stdout or b""
            error = raw_err_b.decode("utf-8", errors="replace") if isinstance(raw_err_b, bytes) else str(raw_err_b)
            error = f"FFmpeg lỗi (rc={exc.returncode}): {error.strip()[-500:]}"
        else:
            error = str(exc)
        print(f"[Transform][ERROR] {state.get('id')}: {error}", flush=True)
        try:
            if hasattr(flow, "record_diagnostic_error"):
                flow.record_diagnostic_error("TransformStudio", target=str(state.get("id") or ""), error_text=error)
        except Exception:
            pass
        update(error[:1000] or type(exc).__name__, "error")


def project_view(folder, state=None):
    state = state or _read_json_safe(folder / "transform.json")
    tpl_code = str(state.get("template_code") or "006")
    tpl_name = str(state.get("template_name") or "Biến hình thời trang")
    preset_key = str(state.get("preset") or "")
    preset_title = str(state.get("preset_title") or (PRESETS.get(preset_key, {}) or {}).get("title") or preset_key or tpl_name)
    base_name = f"{tpl_name} · {preset_title}" if tpl_code != "006" else ("Biến hình · " + preset_title)
    product_label = str(state.get("product_label") or "").strip()
    name = f"{base_name} · {product_label}" if product_label else base_name
    pid = state["id"]
    running = state["status"] in {"queued", "running"} and is_active(pid, state)
    final = folder / "video_final.mp4"
    done = state["status"] == "done" and final.is_file()
    scenes = []
    for i, scene in enumerate(state["scenes"], 1):
        image, clip = folder / scene["ref"], folder / f"scene_{i}.mp4"
        scenes.append({"scene_number": i, "scene_title": scene["title"], "duration_sec": 8,
                       "image_path": str(image) if image.is_file() else "",
                       "video_path": str(clip) if clip.is_file() else "",
                       "image_prompt": scene["image_prompt"], "video_prompt": scene["prompt"],
                       "status": "done" if clip.is_file() else "queued"})
    product_image = folder / ("product_2k.jpg" if (folder / "product_2k.jpg").is_file() else "product_input.jpg")
    char_image = folder / "character_input.jpg"
    before_img = folder / "before_2k.jpg"
    reveal = folder / "reveal_2k.jpg"
    reference_images = [str(p) for p in (char_image, product_image, before_img, reveal) if p.is_file()]
    real_thumb = ""
    for th_cand in (
        Path(str(state.get("thumbnail_path") or "")) if state.get("thumbnail_path") else None,
        folder / "thumbnails" / f"{pid}_nv1_v1_thumb.jpg",
        ROOT / "thumbnails" / f"{pid}_nv1_v1_thumb.jpg",
    ):
        if th_cand and th_cand.is_file() and th_cand.stat().st_size > 1000:
            real_thumb = str(th_cand)
            break
    st_raw = str(state.get("status") or "")
    prod_status = (
        "done" if done
        else ("vid_gen" if (running and st_raw == "running")
              else ("queued" if (running and st_raw == "queued")
                    else ("failed" if st_raw == "error"
                          else ("stopped" if st_raw == "stopped" else "queued"))))
    )
    done_scenes_cnt = sum(s["status"] == "done" for s in scenes)
    done_refs_cnt = len(state.get("refs") or {})
    if done:
        progress_pct = 100
    elif running or done_refs_cnt or done_scenes_cnt:
        progress_pct = min(95, 5 + 15 * min(3, done_refs_cnt) + 20 * done_scenes_cnt)
    else:
        progress_pct = 0
    product = {"id": pid + "_nv1_v1", "vkey": "nv1_v1", "product_name": name,
               "status": prod_status,
               "product_image_path": str(product_image), "primary_product_image_path": str(product_image),
               "character_image_path": str(char_image) if char_image.is_file() else "",
               "thumbnail_path": real_thumb or (str(reveal) if reveal.is_file() else ""), "has_thumbnail": bool(real_thumb),
               "final_video_path": str(final) if done else "", "output_dir": str(folder),
               "scenes": scenes, "num_scenes": 2, "seconds_per_scene": 8, "duration_sec": 16, "aspect": "9:16"}
    settings = {"num_scenes": 2, "seconds_per_scene": 8, "aspect": "9:16", "video_resolution": "1080p",
                "img_model": state["image_provider"], "vid_model": str(state.get("video_model") or DEFAULT_VIDEO_MODEL), "has_subtitles": False}
    tj = folder / "transform.json"
    base_mtime = (
        final.stat().st_mtime if final.is_file()
        else (tj.stat().st_mtime if tj.is_file() else (folder.stat().st_mtime if folder.is_dir() else time.time()))
    )
    updated_ts = float(state.get("updated_ts") or base_mtime)
    created_ts = float(state.get("created_ts") or (folder.stat().st_ctime if folder.is_dir() else updated_ts))
    updated_at = str(state.get("updated_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated_ts)))
    created_at = str(state.get("created_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_ts)))
    return {"id": pid, "name": name, "pipeline_kind": "fashion_transformation",
            "template_code": tpl_code, "template_name": tpl_name, "videos_per_character": 1,
            "product_label": product_label,
            "created_at": created_at, "updated_at": updated_at,
            "created_ts": round(created_ts, 3), "updated_ts": round(updated_ts, 3),
            "total_products": 1, "done_products": int(done), "running_products": int(running),
            "failed_products": int(st_raw == "error"), "project_dir": str(folder),
            "final_videos_dir": str(folder), "primary_product_image_path": str(product_image),
            "character_image_path": str(char_image) if char_image.is_file() else "",
            "reference_images": reference_images,
            "products": [product], "settings": settings, "is_running": running,
            "status": st_raw, "current_step_text": state.get("message", ""),
            "live_status": {"is_running": running, "current_step_text": state.get("message", ""),
                            "done_refs": done_refs_cnt, "total_scenes": 2,
                            "done_scenes": done_scenes_cnt, "done_finals": int(done)},
            "has_rendered_cache": bool(state["refs"]), "is_clean_new": not bool(state["refs"]),
            "rendered_files_count": done_refs_cnt + sum(bool(s["video_path"]) for s in scenes),
            "thumbnails_count": int(bool(real_thumb)), "progress_pct": progress_pct,
            "logs": [state.get("message", "")]}
