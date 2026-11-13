"""Commercial readiness & clean-buyer isolation regression tests (offline, no paid API calls)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "flow_final_pipeline" / "scripts"
for p in (str(ROOT_DIR), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import engine_settings_manager as esm
import cooking_storyboard_engine as cooking
import token_manager as tm
import server


class CommercialGuardrailsTests(unittest.TestCase):
    def test_media_path_resolution_blocks_outside_root_and_non_media(self):
        with tempfile.TemporaryDirectory() as ws_tmp, tempfile.TemporaryDirectory() as ext_tmp:
            ws = Path(ws_tmp)
            ext = Path(ext_tmp)
            finals = ws / "final_videos"
            proj_dir = ws / "projects" / "demo"
            finals.mkdir(parents=True)
            proj_dir.mkdir(parents=True)

            ok_img = proj_dir / "thumb.png"
            ok_img.write_bytes(b"pngdata")
            ok_vid = finals / "out.mp4"
            ok_vid.write_bytes(b"mp4data")
            bad_py = ws / "secret_config.py"
            bad_py.write_text("SECRET='x'", encoding="utf-8")
            bad_json = ws / "accounts.json"
            bad_json.write_text("[]", encoding="utf-8")
            ext_txt = ext / "secret.txt"
            ext_txt.write_text("nope", encoding="utf-8")
            ext_jpg = ext / "outside.jpg"
            ext_jpg.write_bytes(b"jpgdata")

            with patch.object(server, "SKILL_DIR", ws), \
                 patch.object(server, "FINAL_VIDEOS_DIR", finals), \
                 patch.object(esm, "load_engine_settings", return_value={"final_videos_dir": str(finals)}):
                self.assertEqual(server._resolve_allowed_media_path(str(ok_img)), (ok_img.resolve(), False))
                self.assertEqual(server._resolve_allowed_media_path("projects/demo/thumb.png"), (ok_img.resolve(), False))
                self.assertEqual(server._resolve_allowed_media_path(str(ok_vid)), (ok_vid.resolve(), False))

                self.assertEqual(server._resolve_allowed_media_path(str(bad_py)), (None, True))
                self.assertEqual(server._resolve_allowed_media_path(str(bad_json)), (None, True))
                self.assertEqual(server._resolve_allowed_media_path(str(ext_txt)), (None, True))
                self.assertEqual(server._resolve_allowed_media_path(str(ext_jpg)), (None, True))
                self.assertEqual(server._resolve_allowed_media_path(f"{ws}/../{ext.name}/outside.jpg"), (None, True))

    def test_clean_buyer_workspace_does_not_fabricate_dev_accounts_or_uuids(self):
        with tempfile.TemporaryDirectory() as clean_tmp:
            ws = Path(clean_tmp)
            (ws / "cookies").mkdir()
            (ws / "data" / "google_flow_grok" / "cookies").mkdir(parents=True)

            with patch.object(esm, "WS_DIR", str(ws)), \
                 patch.object(esm, "PROJECTS_DIR", str(ws / "projects")), \
                 patch.object(tm, "COOKIES_DIR", ws / "cookies"), \
                 patch.object(tm, "DATA_DIR", ws / "data" / "google_flow_grok"), \
                 patch.object(cooking, "ROOT", ws), \
                 patch.dict(os.environ, {"FLOW_DEFAULT_PROJECT_ID": ""}, clear=False):
                self.assertEqual(esm.list_available_flow_accounts(), [])
                self.assertEqual(esm.get_default_flow_project_id(), "")

                mgr = tm.TokenManager()
                self.assertEqual(mgr._discover_profiles(), [])

                self.assertEqual(cooking.list_cooking_flow_accounts(), [])
                with patch.object(cooking, "get_status", return_value={"is_running": False, "clips": []}):
                    with self.assertRaisesRegex(ValueError, "Chưa có tài khoản"):
                        cooking.launch_stage("clean_proj", "storyboards")

    def test_cliproxy_config_and_model_priority_resolution(self):
        with patch.dict(os.environ, {"CLIPROXY_API_KEY": "test-proxy-key", "CLIPROXY_BASE_URL": "http://127.0.0.1:8317/"}, clear=False):
            cfg = esm.get_cliproxy_config()
            self.assertEqual(cfg["url"], "http://127.0.0.1:8317")
            self.assertEqual(cfg["api_key"], "test-proxy-key")

        class _FakeResp:
            def __init__(self, payload: bytes):
                self._buf = payload
            def read(self):
                return self._buf
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        fake_models = {
            "data": [
                {"id": "gpt-image-1"},
                {"id": "gpt-6-luna"},
                {"id": "gemini-3.5-flash-lite"},
                {"id": "claude-sonnet-4-6"},
            ]
        }
        payload = json.dumps(fake_models).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=_FakeResp(payload)):
            models = esm.resolve_cliproxy_chat_models(force_refresh=True)
        self.assertGreaterEqual(len(models), 3)
        self.assertEqual(models[0], "gemini-3.5-flash-lite")
        self.assertNotIn("gpt-image-1", models)

    def test_fashion_ref_cache_reuses_split_clips_and_frames(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg/ffprobe not installed")
        import fashion_motion_control_engine as fmce

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref_mp4 = root / "sample_tpl.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", "color=c=navy:s=180x320:d=4:r=30",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    str(ref_mp4),
                ],
                check=True,
                timeout=30,
            )
            out1 = root / "proj_1"
            out2 = root / "proj_2"
            out1.mkdir()
            out2.mkdir()
            studio_dir = root / "fashion_motion_projects"
            studio_dir.mkdir()

            with patch.object(fmce, "FASHION_STUDIO_DIR", str(studio_dir)):
                res1 = fmce.analyze_and_split_reference_video(
                    str(ref_mp4), str(out1), preferred_chunk_sec="6",
                )
                self.assertTrue(res1.get("ok"))
                self.assertGreaterEqual(len(res1.get("scenes", [])), 1)
                clip1 = Path(res1["scenes"][0]["ref_clip_path"])
                self.assertTrue(clip1.is_file())

                with patch.object(fmce.subprocess, "run", side_effect=AssertionError("Warm _ref_cache should skip FFmpeg")):
                    res2 = fmce.analyze_and_split_reference_video(
                        str(ref_mp4), str(out2), preferred_chunk_sec="6",
                    )
                self.assertTrue(res2.get("ok"))
                self.assertEqual(len(res2.get("scenes", [])), len(res1.get("scenes", [])))
                clip2 = Path(res2["scenes"][0]["ref_clip_path"])
                self.assertTrue(clip2.is_file())
                self.assertTrue(str(clip2).startswith(str(out2)))


if __name__ == "__main__":
    unittest.main()
