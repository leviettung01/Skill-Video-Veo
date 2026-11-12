# -*- coding: utf-8 -*-
"""Offline unit & integration tests for Google Vids Web (`google_vids_client.py`) and Studio integration."""

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

WS_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WS_DIR / "flow_final_pipeline" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import engine_settings_manager as esm
import fashion_motion_control_engine as fmce
import google_vids_client as gvc


class GoogleVidsClientTests(unittest.TestCase):
    def test_sapisidhash_and_enums(self):
        hdr = gvc.make_sapisidhash_header(
            {
                "SAPISID": "sec0",
                "__Secure-1PAPISID": "sec1",
                "__Secure-3PAPISID": "sec3",
            },
            origin="https://docs.google.com",
            timestamp=1700000000,
        )
        expected_h0 = hashlib.sha1(b"1700000000 sec0 https://docs.google.com").hexdigest()
        expected_h1 = hashlib.sha1(b"1700000000 sec1 https://docs.google.com").hexdigest()
        expected_h3 = hashlib.sha1(b"1700000000 sec3 https://docs.google.com").hexdigest()
        self.assertEqual(
            hdr,
            f"SAPISIDHASH 1700000000_{expected_h0} SAPISID1PHASH 1700000000_{expected_h1} SAPISID3PHASH 1700000000_{expected_h3}",
        )

        self.assertEqual(gvc.resolve_aspect_res_enum("9:16", "1080p"), 6)
        self.assertEqual(gvc.resolve_aspect_res_enum("16:9", "1080p"), 5)
        self.assertEqual(gvc.resolve_aspect_res_enum("9:16", "720p"), 2)
        self.assertEqual(gvc.resolve_aspect_res_enum("16:9", "720p"), 1)
        self.assertEqual(gvc.resolve_model_id("omni"), 12)
        self.assertEqual(gvc.resolve_model_id("veo_3_1"), 9)

    def test_strip_xssi_and_quota_parser(self):
        payload = [
            [
                [
                    [
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        [
                            None,
                            None,
                            None,
                            None,
                            "https://contribution-rt.usercontent.google.com/download?c=TEST",
                        ],
                    ]
                ]
            ],
            None,
            None,
            None,
            [[None, ["10000", None, "9966", None, None, None, ["1796112000"]], "34"]],
        ]
        raw = ")]}'\n\n" + json.dumps(payload)
        parsed = json.loads(gvc.strip_xssi(raw))
        urls = gvc.find_video_urls_recursive(parsed)
        self.assertEqual(urls, ["https://contribution-rt.usercontent.google.com/download?c=TEST"])
        quota = gvc.parse_generate_quota_telemetry(parsed)
        self.assertEqual(quota, {"limit": 10000, "remaining": 9966, "reset_epoch": 1796112000, "used": 34})

    def test_amv_ast_from_template_tags(self):
        tags = {
            "{IMG1}": {"uuid": "UUID-1", "label": "Hình ảnh1"},
            "[03_Product_Sheet_Quan_Xanh_2K.png]": {"uuid": "UUID-2", "label": "Hình ảnh2"},
        }
        ast = gvc.build_amv_ast_from_template(
            "Start from {IMG1} and switch into [03_Product_Sheet_Quan_Xanh_2K.png].",
            tags,
        )
        chunks = ast[3][0]
        chip_nodes = [c for c in chunks if len(c) > 7 and c[7] is not None]
        self.assertEqual(len(chip_nodes), 2)
        self.assertEqual(chip_nodes[0][7][1][2], "Hình ảnh1")
        self.assertEqual(chip_nodes[0][7][2][7][0], "UUID-1")
        self.assertEqual(chip_nodes[1][7][1][2], "Hình ảnh2")
        self.assertEqual(chip_nodes[1][7][2][7][0], "UUID-2")

    def test_fashion_google_vids_prompt_binds_three_2k_chips_for_s1_and_s2(self):
        s1_info = {
            "id": "s1",
            "scene_index": 1,
            "duration": 8,
            "transitions": [
                {
                    "timestamp_sec": 4.47,
                    "timestamp_colon": "0:04.5",
                    "outfit": {
                        "id": "outfit_1",
                        "filename": "03_Product_Sheet_Quan_Xanh_2K.png",
                        "en_desc": "pastel yellow halter top and cobalt trousers",
                    },
                },
                {
                    "timestamp_sec": 6.45,
                    "timestamp_colon": "0:06.5",
                    "outfit": {
                        "id": "outfit_2",
                        "filename": "04_Product_Sheet_Vay_Vang_2K.png",
                        "en_desc": "butter-yellow tiered mini dress",
                    },
                },
            ],
        }
        start_ref = {"asset_key": "base_char_2k", "filename": "02_Character_Sheet_Basic_Poses_2K.png"}
        bg_ref = {"asset_key": "char_sheet_2k", "filename": "07_Nhan_Vat_Basic_Phong_Ngu_2K.png"}

        res_s1 = fmce.build_scene_timeline_prompt(
            s1_info, start_ref, bg_ref, prompt_style="google_vids", bpm_info={"estimated_bpm": 140, "beat_interval_sec": 0.43}
        )
        media_s1 = [seg["title"] for seg in res_s1["segments_spec"] if seg["type"] == "media"]
        self.assertIn("07_Nhan_Vat_Basic_Phong_Ngu_2K.png", media_s1)
        self.assertIn("03_Product_Sheet_Quan_Xanh_2K.png", media_s1)
        self.assertIn("04_Product_Sheet_Vay_Vang_2K.png", media_s1)
        self.assertEqual(len(set(media_s1)), 3)

        s2_info = {
            "id": "s2",
            "scene_index": 2,
            "duration": 8,
            "transitions": [
                {
                    "timestamp_sec": 2.30,
                    "timestamp_colon": "0:02.3",
                    "outfit": {
                        "id": "outfit_3",
                        "filename": "05_Product_Sheet_Ao_Hong_Quan_Xam_2K.png",
                        "en_desc": "pink top and grey trousers",
                    },
                },
                {
                    "timestamp_sec": 4.90,
                    "timestamp_colon": "0:04.9",
                    "outfit": {
                        "id": "outfit_4",
                        "filename": "06_Product_Sheet_Vay_Trang_2K.png",
                        "en_desc": "white lace mini dress",
                    },
                },
            ],
        }
        prev_lf = {"asset_key": "scene_s1_last_frame_2k", "filename": "scene_s1_last_frame_2k.png"}
        res_s2 = fmce.build_scene_timeline_prompt(
            s2_info,
            start_ref,
            bg_ref,
            prompt_style="google_vids",
            prev_scene_last_outfit=s1_info["transitions"][-1]["outfit"],
            prev_scene_last_frame_ref=prev_lf,
        )
        media_s2 = [seg["title"] for seg in res_s2["segments_spec"] if seg["type"] == "media"]
        self.assertIn("scene_s1_last_frame_2k.png", media_s2)
        self.assertIn("05_Product_Sheet_Ao_Hong_Quan_Xam_2K.png", media_s2)
        self.assertIn("06_Product_Sheet_Vay_Trang_2K.png", media_s2)
        self.assertEqual(len(set(media_s2)), 3)

    def test_mocked_generate_video_builds_exact_mode_376_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            img1 = tmp_p / "board_2k.png"
            img1.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 1024)
            out_mp4 = tmp_p / "out_1080p.mp4"

            client = gvc.GoogleVidsClient(workspace_dir=tmp_p)
            fake_sess = {
                "profile": "leviettung04",
                "email": "leviettung04@gmail.com",
                "doc_id": "1d7kx4mW2NHsd7wmgd3JlqkzeH-vAWwtP3JNS0lsvFpM",
                "server_token": "AIwbfakeServerToken",
                "api_key": "AIzaFakeApiKey",
                "genai_host": "appsgenaiserver-pa.clients6.google.com",
                "upload_path": "/upload/temporaryblob/videos",
                "editor_url": "https://docs.google.com/videos/d/1d7kx4mW2NHsd7wmgd3JlqkzeH-vAWwtP3JNS0lsvFpM/edit",
                "sapisid_map": {"SAPISID": "secret_sapisid"},
                "bootstrapped_at": 9999999999.0,
            }

            captured_gen_payload = {}

            class FakeResp:
                def __init__(self, body_bytes: bytes, status: int = 200):
                    self._body = body_bytes
                    self.status = status
                    self.headers = {"Content-Type": "video/mp4"}

                def read(self):
                    return self._body

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            class FakeOpener:
                def open(self, req, timeout=60):
                    url = req.full_url
                    if "/v1/genai/generate" in url:
                        captured_gen_payload["data"] = json.loads(req.data.decode("utf-8"))
                        resp_str = ")]}'\n" + json.dumps([
                            [[[[None, None, None, None, None, None, [None, None, None, None, "https://contribution-rt.usercontent.google.com/download?c=FAKE_VID"]]]]],
                            None,
                            None,
                            None,
                            [[None, ["10000", None, "9965", None, None, None, ["1796112000"]], "35"]],
                        ])
                        return FakeResp(resp_str.encode("utf-8"))
                    if "contribution-rt.usercontent.google.com" in url:
                        return FakeResp(b"\x00\x00\x00\x18ftypmp42" + b"V" * 30000)
                    raise AssertionError(f"Unexpected URL: {url}")

            fake_sess["opener"] = FakeOpener()

            with patch.object(client, "bootstrap_session", return_value=fake_sess), patch.object(
                client, "upload_image", return_value="AYGXpjFakeBlobToken"
            ):
                res = client.generate_video(
                    out_mp4=out_mp4,
                    prompt="Six-panel cooking storyboard video prompt.",
                    image_paths=[str(img1)],
                    profile_name="leviettung04",
                    model="omni",
                    aspect_ratio="9:16",
                    resolution="1080p",
                    duration_sec=10,
                    ingredient_role="storyboard",
                )

            self.assertTrue(res["ok"])
            self.assertTrue(out_mp4.is_file())
            self.assertGreater(res["bytes"], 25000)
            self.assertEqual(res["quota"]["remaining"], 9965)

            payload = captured_gen_payload["data"]
            self.assertEqual(payload[0], 376)
            erp = payload[4][15]
            self.assertEqual(erp, [0, 12, None, 0, 6, None, None, None, 10])
            # Verify auto-injected @Hình ảnh1 chip node in Amv AST
            chunks = payload[3][3][0]
            chips = [c for c in chunks if len(c) > 7 and c[7] is not None]
            self.assertEqual(len(chips), 1)
            self.assertEqual(chips[0][7][1][2], "Hình ảnh1")

    def test_engine_settings_saves_video_provider_and_fashion_mode_normalizer(self):
        self.assertEqual(fmce.normalize_fashion_generation_mode("google_vids"), "google_vids")
        self.assertEqual(fmce.normalize_fashion_generation_mode("chained_i2v"), "chained_i2v")
        self.assertEqual(fmce.normalize_fashion_generation_mode("video_ref"), "video_ref")

        with tempfile.TemporaryDirectory() as tmp:
            fake_json = str(pathlib.Path(tmp) / "engine_settings_test.json")
            with patch.object(esm, "ENGINE_SETTINGS_JSON", fake_json):
                saved = esm.save_engine_settings({"video_provider": "google_vids", "google_vids_model": "veo_3_1"})
                self.assertTrue(saved["ok"])
                self.assertEqual(saved["settings"]["video_provider"], "google_vids")
                self.assertEqual(saved["settings"]["google_vids_model"], "veo_3_1")


if __name__ == "__main__":
    unittest.main()
