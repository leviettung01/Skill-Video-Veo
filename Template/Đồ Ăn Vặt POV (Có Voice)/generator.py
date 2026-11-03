# -*- coding: utf-8 -*-
"""
Generator cho Biến thể "Đồ Ăn Vặt POV (Có Voice)"
Kế thừa trực tiếp từ Template/Đồ Ăn Vặt/generator.py để đồng bộ 100% logic:
- Giữ nguyên ảnh sản phẩm gốc (không tự ý crop).
- Sáng tạo bày biện ẩm thực hấp dẫn (nồi đất kho quẹt bốc khói + rau củ luộc + cơm cháy, ly đá viên mát lạnh, v.v.), chỉ hạn chế bẻ lộ nhân đối với các loại bánh có nhân kín.
- Quay POV + Chọn Voice từ danh sách + Timeline kép [0.0-3.5s], [3.5-7.0s], [7.0-10.0s] + Random 8 Background + Render 60 FPS Karaoke Subtitles.
"""
import os
import sys
import importlib.util

_BASE_GEN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Đồ Ăn Vặt",
    "generator.py",
)
_spec = importlib.util.spec_from_file_location("_do_an_vat_base_gen", _BASE_GEN_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

RANDOM_BG_POOL = _mod.RANDOM_BG_POOL
HAND_POOL = _mod.HAND_POOL
generate_project_from_template = _mod.generate_project_from_template
