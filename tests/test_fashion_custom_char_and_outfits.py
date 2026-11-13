# -*- coding: utf-8 -*-
import base64
import io
import os
import sys
import unittest
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flow_final_pipeline.scripts import fashion_motion_control_engine as fmce


def _make_dummy_png_base64(color=(220, 40, 90), size=(600, 900)) -> str:
    img = Image.new("RGB", size, color)
    # Vẽ 1 vùng quần áo ở giữa để test tách nền trắng local
    for y in range(200, 700):
        for x in range(150, 450):
            img.putpixel((x, y), (30, 80, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


class TestFashionCustomCharAndOutfits(unittest.TestCase):
    def test_01_library_includes_all_characters_with_own_bg(self):
        lib = fmce.list_fashion_characters_and_outfits_library()
        chars = lib.get("characters", [])
        self.assertTrue(len(chars) >= 2, "Library must include default + character library entries")
        char_ids = {c.get("id") for c in chars}
        # Kiểm tra NV1 hoặc NV2 từ voices_and_characters.json có mặt (id: char_store_nv1 / char_store_nv2)
        self.assertTrue("char_store_nv1" in char_ids or "char_store_nv2" in char_ids)
        for c in chars:
            cid = c.get("id")
            if cid in ("char_store_nv1", "char_store_nv2"):
                self.assertNotIn(
                    "07_Nhan_Vat_Basic_Phong_Ngu_2K.png",
                    c.get("bg_path", ""),
                    f"Custom character {cid} must not default to NV5 bedroom bg",
                )
                self.assertEqual(c.get("char_path"), c.get("bg_path"))

    def test_02_upload_custom_character_and_outfit_base64(self):
        b64_char = _make_dummy_png_base64((240, 200, 190))
        res_char = fmce.upload_custom_fashion_asset_base64(
            filename="my_custom_model.png",
            data_base64=b64_char,
            kind="character",
            name="Người Mẫu Custom Test",
            project_id_slug="qa_custom_fashion_test",
        )
        self.assertTrue(res_char.get("ok"), f"Upload character failed: {res_char}")
        char_path = res_char.get("path")
        self.assertTrue(os.path.isfile(char_path))
        char_fn = os.path.basename(char_path)

        b64_outfit1 = _make_dummy_png_base64((245, 245, 245))
        res_out1 = fmce.upload_custom_fashion_asset_base64(
            filename="vay_do_custom_1.png",
            data_base64=b64_outfit1,
            kind="outfit",
            name="Váy Đỏ Dự Tiệc Custom 1",
            project_id_slug="qa_custom_fashion_test",
            auto_white_bg_local=True,
        )
        self.assertTrue(res_out1.get("ok"), f"Upload outfit 1 failed: {res_out1}")
        out1_obj = res_out1.get("outfit")
        self.assertIsInstance(out1_obj, dict)
        out1_fn = out1_obj.get("filename")
        self.assertTrue(os.path.isfile(out1_obj.get("path")))

        b64_outfit2 = _make_dummy_png_base64((240, 240, 240))
        res_out2 = fmce.upload_custom_fashion_asset_base64(
            filename="set_vest_custom_2.png",
            data_base64=b64_outfit2,
            kind="outfit",
            name="Set Vest Công Sở Custom 2",
            project_id_slug="qa_custom_fashion_test",
            auto_white_bg_local=False,
        )
        self.assertTrue(res_out2.get("ok"), f"Upload outfit 2 failed: {res_out2}")
        out2_obj = res_out2.get("outfit")
        out2_fn = out2_obj.get("filename")

        # Tạo/cập nhật dự án với Nhân Vật Custom + 2 Sản Phẩm Custom
        proj = fmce.create_or_update_fashion_motion_project(
            project_id_slug="qa_custom_fashion_test",
            title="QA Custom Character & 2 Custom Outfits",
            base_char_path=char_path,
            char_sheet_path="",  # Để trống để kiểm tra auto-sync = base_char_path
            outfit_items=[out1_obj, out2_obj],
            generation_mode="google_vids",
            auto_render_preview_final=False,
        )
        self.assertTrue(proj.get("ok"), f"Create project failed: {proj}")
        self.assertEqual(proj["base_char_2k"]["filename"], char_fn)
        self.assertEqual(proj["char_sheet_2k"]["filename"], char_fn)
        self.assertTrue(proj.get("disable_overall_sheet"))
        self.assertEqual(len(proj.get("outfits", [])), 2)

        scenes = proj.get("scenes", [])
        self.assertTrue(len(scenes) >= 2)
        s1 = scenes[0]
        s2 = scenes[1]

        # Scene 1 phải có đúng 1 bộ đồ (out1_fn) và dùng nhân vật char_fn, tuyệt đối không chứa ảnh mặc định NV5
        for p_key in ("prompt_google_vids", "prompt_chained_i2v", "prompt_timeline_pro"):
            p_txt = s1.get(p_key, "")
            self.assertIn(char_fn, p_txt, f"{p_key} in Scene 1 must reference custom character {char_fn}")
            self.assertIn(out1_fn, p_txt, f"{p_key} in Scene 1 must reference custom outfit 1 {out1_fn}")
            self.assertNotIn("07_Nhan_Vat_Basic_Phong_Ngu_2K.png", p_txt)
            self.assertNotIn("01_Character_Sheet_4_Outfits_2K.png", p_txt)
            self.assertNotIn("02_Character_Sheet_Basic_Poses_2K.png", p_txt)

        # Scene 2 phải có bộ đồ 2 (out2_fn) và nối từ scene_s1_last_frame_2k.png
        for p_key in ("prompt_google_vids", "prompt_chained_i2v", "prompt_timeline_pro"):
            p_txt = s2.get(p_key, "")
            self.assertIn("scene_s1_last_frame_2k.png", p_txt)
            self.assertIn(out2_fn, p_txt, f"{p_key} in Scene 2 must reference custom outfit 2 {out2_fn}")
            self.assertNotIn("07_Nhan_Vat_Basic_Phong_Ngu_2K.png", p_txt)
            self.assertNotIn("01_Character_Sheet_4_Outfits_2K.png", p_txt)

        # Kiểm tra cả khi người dùng chỉ chọn đúng 1 sản phẩm (1 outfit)
        proj_1 = fmce.create_or_update_fashion_motion_project(
            project_id_slug="qa_custom_fashion_test",
            title="QA Custom Character & 1 Custom Outfit",
            base_char_path=char_path,
            char_sheet_path=char_path,
            outfit_items=[out1_obj],
            generation_mode="google_vids",
            auto_render_preview_final=False,
        )
        self.assertTrue(proj_1.get("ok"))
        sc1_single = proj_1["scenes"][0]
        sc2_single = proj_1["scenes"][1]
        self.assertEqual(len(sc1_single.get("transitions", [])), 1)
        self.assertEqual(len(sc2_single.get("transitions", [])), 0)
        for p_key in ("prompt_google_vids", "prompt_chained_i2v"):
            self.assertIn(out1_fn, sc1_single.get(p_key, ""))
            self.assertIn("scene_s1_last_frame_2k.png", sc2_single.get(p_key, ""))
            self.assertNotIn("01_Character_Sheet_4_Outfits_2K.png", sc2_single.get(p_key, ""))
            self.assertNotIn("Look 3", sc2_single.get(p_key, ""))


if __name__ == "__main__":
    unittest.main()
