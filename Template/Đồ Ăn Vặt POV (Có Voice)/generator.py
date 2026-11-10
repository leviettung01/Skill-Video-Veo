# -*- coding: utf-8 -*-
"""
Generator cho Biến thể #002 "Đồ Ăn Vặt POV (Có Voice)"
Sử dụng cấu hình riêng `Template/Đồ Ăn Vặt POV (Có Voice)/template_config.json` (`id="do_an_vat_pov_voice"`, 3 cảnh × 10s, có Voice ID theo nhân vật đang bật):
- Giữ nguyên ảnh sản phẩm gốc (không tự ý crop).
- Sáng tạo bày biện ẩm thực hấp dẫn (nồi đất kho quẹt bốc khói + rau củ luộc + cơm cháy, ly đá viên mát lạnh, v.v.), hạn chế bẻ lộ nhân đối với các loại bánh có nhân kín.
- Quay POV + Chọn Voice theo nhân vật đang bật trong thư viện + Timeline kép [0.0-3.5s], [3.5-7.0s], [7.0-10.0s] + Random 8 Background + Render 60 FPS Karaoke Subtitles.
"""
import os
import importlib.util

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(TEMPLATE_DIR, "template_config.json")

_BASE_GEN_PATH = os.path.join(
    os.path.dirname(TEMPLATE_DIR),
    "Đồ Ăn Vặt",
    "generator.py",
)
_spec = importlib.util.spec_from_file_location("_do_an_vat_base_gen", _BASE_GEN_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

RANDOM_BG_POOL = _mod.RANDOM_BG_POOL
HAND_POOL = _mod.HAND_POOL


def load_template_config(config_path: str = None) -> dict:
    return _mod.load_template_config(config_path or CONFIG_PATH)


def generate_project_from_template(
    pid: str,
    pdir: str,
    info_data: dict,
    characters_data: dict = None,
    videos_per_character: int = None,
    primary_product_refs: list = None,
    slide_overlay_files: list = None,
    selected_voice_key: str = None,
    config_path_override: str = None,
) -> dict:
    eff_cfg = config_path_override or CONFIG_PATH
    return _mod.generate_project_from_template(
        pid=pid,
        pdir=pdir,
        info_data=info_data,
        characters_data=characters_data,
        videos_per_character=videos_per_character,
        primary_product_refs=primary_product_refs,
        slide_overlay_files=slide_overlay_files,
        selected_voice_key=selected_voice_key,
        config_path_override=eff_cfg,
    )
