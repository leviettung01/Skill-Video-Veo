import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "flow_final_pipeline" / "scripts"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import engine_settings_manager as esm  # noqa: E402
import grok_video_tool as gvt  # noqa: E402
import transform_engine as te  # noqa: E402


def _write_jpeg(path: Path, color=(210, 120, 60), size=(720, 1280)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(str(path), format="JPEG", quality=92)


def _make_synthetic_mp4(path: Path, duration: float = 2.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=s=1080x1920:r=30:d={duration}",
        "-f", "lavfi", "-i", f"aevalsrc=0:d={duration}:s=44100:c=stereo",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg synthetic mp4 failed: {res.stderr}")


def _probe_mp4(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:format_tags=comment",
        "-of", "json", str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {res.stderr}")
    return json.loads(res.stdout).get("format") or {}


class TestThumbnailUnifiedFlow(unittest.TestCase):
    def test_flow_batch_delegates_to_run_veo_flow_with_failover_per_account_project_and_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ref_img = tmp_path / "ref.jpg"
            out1 = tmp_path / "thumb_1.jpg"
            out2 = tmp_path / "thumb_2.jpg"
            _write_jpeg(ref_img)

            fake_accounts = [
                {
                    "name": "Google_acc1",
                    "profile_name": "prof_1",
                    "active": True,
                    "api_key": "",
                    "project_id": "proj-acc-1",
                },
                {
                    "name": "Google_acc2",
                    "profile_name": "prof_2",
                    "active": True,
                    "api_key": "flow_cookie:SID=valid_2",
                    "project_id": "proj-acc-2",
                },
            ]

            calls = []
            refreshed_profiles = []
            invalidated_profiles = []

            async def _fake_run_veo_flow(job, token, project_id, bridge, log, progress):
                calls.append({
                    "id": job.id,
                    "profile": job.google_profile_name,
                    "account": job.account_name,
                    "token": token,
                    "project_id": project_id,
                    "model": job.model,
                    "resolution": job.resolution,
                    "aspect_ratio": job.aspect_ratio,
                    "flow_request_only": job.flow_request_only,
                    "prefer_bearer_request": job.prefer_bearer_request,
                    "require_all_reference_uploads": job.require_all_reference_uploads,
                    "character_id": getattr(job, "character_id", ""),
                })
                if job.google_profile_name == "prof_1":
                    job.error = "simulated prof_1 failure"
                    return False
                _write_jpeg(Path(job.local_path), color=(40, 180, 90), size=(1536, 2752))
                return True

            def _fake_refresh(prof_name, prefer_profile=True):
                refreshed_profiles.append(prof_name)
                return True, f"flow_cookie:REF={prof_name}", "", f"session_verified:{prof_name}@example.com"

            def _fake_invalidate(prof_name=""):
                invalidated_profiles.append(prof_name)

            meta1 = {
                "pid": "proj_test",
                "vkey": "v1",
                "char_v": "v1",
                "prompt": "Luxury studio thumbnail",
                "reference_images": [str(ref_img)],
                "char_uuid": "char-uuid-123",
                "flow_project_id": "proj-acc-1",
            }
            meta2 = dict(meta1, vkey="v2", char_v="v2")

            with esm._THUMB_PREFERRED_LOCK:
                prev_prefs = list(esm._THUMB_PREFERRED_PROFILES)
                esm._THUMB_PREFERRED_PROFILES.clear()
            try:
                with mock.patch.object(esm, "list_available_flow_accounts", return_value=fake_accounts), \
                     mock.patch.object(esm, "get_default_flow_project_id", side_effect=lambda p="": {"prof_1": "proj-acc-1", "prof_2": "proj-acc-2"}.get(p, "")), \
                     mock.patch.object(gvt, "run_veo_flow", side_effect=_fake_run_veo_flow), \
                     mock.patch.object(gvt, "_load_flow_cookie_header", return_value=""), \
                     mock.patch.object(gvt, "_refresh_google_profile", side_effect=_fake_refresh), \
                     mock.patch.object(gvt, "invalidate_flow_chrome_session", side_effect=_fake_invalidate), \
                     mock.patch.object(gvt, "CaptchaBridge", side_effect=lambda *a, **kw: mock.MagicMock(last_browser_headers={})):
                    outcomes = esm._render_thumbnails_via_google_flow_batch([
                        {"meta": meta1, "out_thumb_proj": str(out1)},
                        {"meta": meta2, "out_thumb_proj": str(out2)},
                    ])
            finally:
                with esm._THUMB_PREFERRED_LOCK:
                    esm._THUMB_PREFERRED_PROFILES[:] = prev_prefs

            self.assertTrue(outcomes["v1"][0], outcomes["v1"])
            self.assertTrue(outcomes["v2"][0], outcomes["v2"])
            self.assertEqual(refreshed_profiles, ["prof_1"])
            self.assertEqual(invalidated_profiles, ["prof_1"])
            # Call 1: prof_1 with proj-acc-1; Call 2: prof_2 failover with proj-acc-2; Call 3: prof_2 winner promoted first!
            self.assertEqual([c["profile"] for c in calls], ["prof_1", "prof_2", "prof_2"])
            self.assertEqual([c["project_id"] for c in calls], ["proj-acc-1", "proj-acc-2", "proj-acc-2"])
            for c in calls:
                self.assertEqual(c["model"], "Nano Banana 2")
                self.assertEqual(c["resolution"], "2K")
                self.assertEqual(c["aspect_ratio"], "9:16")
                self.assertTrue(c["flow_request_only"])
                self.assertFalse(c["prefer_bearer_request"])
                self.assertTrue(c["require_all_reference_uploads"])
                self.assertEqual(c["character_id"], "char-uuid-123")

    def test_generate_thumbnail_defaults_inject_01s_and_prefer_existing_ref_with_real_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            proj_dir = tmp_path / "projects"
            thumbs_dir = tmp_path / "thumbnails"
            finals_dir = tmp_path / "final_videos"
            fashion_dir = tmp_path / "fashion_motion_projects"
            pid = "transform_demo_001"
            pdir = proj_dir / pid
            pdir.mkdir(parents=True, exist_ok=True)
            thumbs_dir.mkdir(parents=True, exist_ok=True)
            finals_dir.mkdir(parents=True, exist_ok=True)

            reveal = pdir / "reveal_2k.jpg"
            prod = pdir / "product_2k.jpg"
            _write_jpeg(reveal, (180, 90, 90), size=(1536, 2752))
            _write_jpeg(prod, (90, 140, 200), size=(1536, 2752))

            raw2k = pdir / "thumbnails" / f"{pid}_nv1_v1_thumb_raw2k.jpg"
            _write_jpeg(raw2k, (230, 190, 80), size=(1536, 2752))

            final_mp4 = pdir / "video_final.mp4"
            _make_synthetic_mp4(final_mp4, duration=2.0)
            dur_before = float(_probe_mp4(final_mp4)["duration"])

            with open(pdir / "transform.json", "w", encoding="utf-8") as f:
                json.dump({
                    "id": pid,
                    "preset": "farm",
                    "status": "done",
                    "product_name": "Váy hoa biếng lười",
                    "final": f"/media/projects/{pid}/video_final.mp4",
                }, f)

            cfg_stub = {
                "auto_generate_thumbnail": True,
                "auto_inject_thumbnail_01s": True,
                "thumbnail_provider": "google_flow",
                "thumbnail_selection_mode": "auto_category",
                "thumbnail_preset_id": "kitchen_minimal",
                "thumbnail_duration_sec": 0.1,
                "thumbnail_add_text_badge": False,
            }

            with mock.patch.object(esm, "WS_DIR", str(tmp_path)), \
                 mock.patch.object(esm, "PROJECTS_DIR", str(proj_dir)), \
                 mock.patch.object(esm, "THUMBS_ROOT_DIR", str(thumbs_dir)), \
                 mock.patch.object(esm, "FINAL_VIDEOS_DIR", str(finals_dir)), \
                 mock.patch.object(esm, "FASHION_STUDIO_PROJECTS_DIR", str(fashion_dir)), \
                 mock.patch.object(esm, "load_engine_settings", return_value=cfg_stub), \
                 mock.patch.object(esm, "_render_thumbnails_via_google_flow_batch") as mock_flow:
                res = esm.generate_thumbnail_for_variant(
                    pid=pid,
                    vkey="nv1_v1",
                    prefer_existing_ref=True,
                    inject_01s=None,
                )
                mock_flow.assert_not_called()
                self.assertTrue(res["ok"], res)
                self.assertTrue(res["injected_01s"], res)
                self.assertTrue(os.path.isfile(res["thumbnail_path"]))

                probe1 = _probe_mp4(final_mp4)
                dur_after1 = float(probe1["duration"])
                comment1 = str((probe1.get("tags") or {}).get("comment") or "")
                self.assertIn("skillautoveo_thumb_intro=0.1", comment1)
                self.assertGreater(dur_after1, dur_before + 0.05)

                # Idempotent re-injection replaces intro without growing duration again
                res2 = esm.ensure_project_variant_thumbnail_and_inject(
                    pid=pid,
                    vkey="nv1_v1",
                    final_video_path=str(final_mp4),
                    prefer_existing_ref=True,
                )
                self.assertTrue(res2["injected_01s"], res2)
                self.assertTrue((res2.get("inject_detail") or {}).get("replaced_existing_intro"))
                dur_after2 = float(_probe_mp4(final_mp4)["duration"])
                self.assertLess(abs(dur_after2 - dur_after1), 0.08)

    def test_build_prompt_and_all_variants_support_transform_fashion_cooking(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            proj_dir = tmp_path / "projects"
            thumbs_dir = tmp_path / "thumbnails"
            finals_dir = tmp_path / "final_videos"
            fashion_dir = tmp_path / "fashion_motion_projects"
            thumbs_dir.mkdir(parents=True, exist_ok=True)
            finals_dir.mkdir(parents=True, exist_ok=True)

            # 1. Transform project
            t_pid = "transform_abc123"
            t_dir = proj_dir / t_pid
            t_dir.mkdir(parents=True, exist_ok=True)
            _write_jpeg(t_dir / "reveal_2k.jpg", (200, 100, 120))
            _write_jpeg(t_dir / "before_2k.jpg", (100, 120, 100))
            _write_jpeg(t_dir / "product_2k.jpg", (80, 90, 200))
            with open(t_dir / "transform.json", "w", encoding="utf-8") as f:
                json.dump({"id": t_pid, "preset": "farm", "product_name": "Set áo váy biến hình"}, f)

            # 2. Cooking project
            c_pid = "cooking_def456"
            c_dir = proj_dir / c_pid
            c_dir.mkdir(parents=True, exist_ok=True)
            dish_img = c_dir / "frame_01.jpg"
            _write_jpeg(dish_img, (210, 160, 70))
            with open(c_dir / "cooking_manifest.json", "w", encoding="utf-8") as f:
                json.dump({
                    "project_id": c_pid,
                    "title": "Bò kho tiêu xanh",
                    "dish_name": "Bò kho tiêu xanh",
                    "dish_photo_path": str(dish_img),
                    "scenes": [{"id": "s1", "title": "Thành phẩm", "first_frame_path": str(dish_img)}],
                }, f)

            # 3. Fashion studio project
            f_pid = "fashion_ghi789"
            f_pdir = fashion_dir / f_pid
            f_pdir.mkdir(parents=True, exist_ok=True)
            char_img = f_pdir / "char.jpg"
            outfit_img = f_pdir / "outfit.jpg"
            _write_jpeg(char_img, (180, 140, 150))
            _write_jpeg(outfit_img, (60, 60, 180))
            with open(f_pdir / "fashion_project.json", "w", encoding="utf-8") as f:
                json.dump({
                    "project_id": f_pid,
                    "product_name": "Đầm dạ hội lụa",
                    "char_sheet_2k": {"path": str(char_img)},
                    "outfits": [{"path": str(outfit_img)}],
                    "hook_title": "LÊN ĐỒ SANG XỊN",
                }, f)

            cfg_stub = {
                "auto_generate_thumbnail": True,
                "auto_inject_thumbnail_01s": True,
                "thumbnail_provider": "google_flow",
                "thumbnail_selection_mode": "auto_category",
                "thumbnail_preset_id": "kitchen_minimal",
                "thumbnail_duration_sec": 0.1,
            }

            def _fake_flow_batch(items):
                out = {}
                for it in items:
                    _write_jpeg(Path(it["out_thumb_proj"]), (150, 160, 210), size=(1536, 2752))
                    out[it["meta"]["vkey"]] = (True, "google_flow (Nano Banana 2 2K)", "")
                return out

            with mock.patch.object(esm, "WS_DIR", str(tmp_path)), \
                 mock.patch.object(esm, "PROJECTS_DIR", str(proj_dir)), \
                 mock.patch.object(esm, "THUMBS_ROOT_DIR", str(thumbs_dir)), \
                 mock.patch.object(esm, "FINAL_VIDEOS_DIR", str(finals_dir)), \
                 mock.patch.object(esm, "FASHION_STUDIO_PROJECTS_DIR", str(fashion_dir)), \
                 mock.patch.object(esm, "load_engine_settings", return_value=cfg_stub), \
                 mock.patch.object(esm, "_render_thumbnails_via_google_flow_batch", side_effect=_fake_flow_batch):
                t_meta = esm.build_thumbnail_prompt_for_variant(t_pid, "nv1_v1")
                self.assertEqual(t_meta["detected_category"], "quan_ao_nu")
                self.assertEqual(t_meta["template_id"], "fashion_lookbook")
                self.assertIn(str(t_dir / "reveal_2k.jpg"), t_meta["reference_images"])

                c_meta = esm.build_thumbnail_prompt_for_variant(c_pid, "pov")
                self.assertEqual(c_meta["detected_category"], "food")
                self.assertEqual(c_meta["template_id"], "food_editorial")
                self.assertIn(str(dish_img), c_meta["reference_images"])

                f_meta = esm.build_thumbnail_prompt_for_variant(f_pid, "nv1_v1")
                self.assertEqual(f_meta["detected_category"], "quan_ao_nu")
                self.assertEqual(f_meta["template_id"], "fashion_lookbook")
                self.assertIn(str(outfit_img), f_meta["reference_images"])

                for p, vk in ((t_pid, "nv1_v1"), (c_pid, "pov"), (f_pid, "nv1_v1")):
                    batch_res = esm.generate_thumbnails_for_all_variants(p)
                    self.assertTrue(batch_res["ok"], (p, batch_res))
                    self.assertEqual(batch_res["success_count"], 1)
                    self.assertTrue(os.path.isfile(thumbs_dir / f"{p}_{vk}_thumb.jpg"))

                # Manifests updated
                self.assertTrue(json.loads((t_dir / "transform.json").read_text(encoding="utf-8")).get("thumbnail_path"))
                self.assertTrue(json.loads((c_dir / "cooking_manifest.json").read_text(encoding="utf-8")).get("thumbnail_path"))
                self.assertTrue(json.loads((f_pdir / "fashion_project.json").read_text(encoding="utf-8")).get("thumbnail_path"))

    def test_cliproxy_image_model_resolution_and_no_proxy(self):
        class _FakeResp:
            def __init__(self, payload_bytes):
                self._buf = io.BytesIO(payload_bytes)
            def read(self):
                return self._buf.read()
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        fake_opener = mock.MagicMock()
        fake_opener.open.return_value = _FakeResp(
            json.dumps({"data": [{"id": "gpt-image-2"}, {"id": "gemini-3.1-flash-image"}]}).encode("utf-8")
        )
        with mock.patch("urllib.request.build_opener", return_value=fake_opener) as mock_bo:
            op = esm._cliproxy_no_proxy_opener()
            self.assertIs(op, fake_opener)
            # ProxyHandler({}) passed so system HTTP proxy is bypassed for 127.0.0.1
            self.assertEqual(mock_bo.call_args.args[0].proxies, {})
            self.assertEqual(esm._resolve_cliproxy_image_model("gpt-image-1", opener=op), "gpt-image-2")
            self.assertEqual(esm._resolve_cliproxy_image_model("grok-imagine-image", opener=op), "gpt-image-2")

    def test_transform_project_view_reports_real_thumbnail_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            folder = tmp_path / "projects" / "transform_pv01"
            folder.mkdir(parents=True, exist_ok=True)
            _write_jpeg(folder / "product_2k.jpg")
            _write_jpeg(folder / "reveal_2k.jpg")
            state = {
                "id": "transform_pv01",
                "preset": "farm",
                "status": "done",
                "image_provider": "flow",
                "message": "Đã xuất video 16 giây.",
                "refs": {"product_2k": "/media/p.jpg", "reveal_2k": "/media/r.jpg"},
                "scenes": [{"title": "Cảnh 1", "ref": "product_2k.jpg", "image_prompt": "", "prompt": ""}],
            }
            with mock.patch.object(te, "ROOT", tmp_path):
                pv_before = te.project_view(folder, state)
                self.assertFalse(pv_before["products"][0]["has_thumbnail"])
                self.assertEqual(pv_before["thumbnails_count"], 0)
                real_thumb = folder / "thumbnails" / "transform_pv01_nv1_v1_thumb.jpg"
                _write_jpeg(real_thumb, (50, 200, 100), size=(1536, 2752))
                pv_after = te.project_view(folder, state)
                self.assertTrue(pv_after["products"][0]["has_thumbnail"])
                self.assertEqual(pv_after["thumbnails_count"], 1)
                self.assertEqual(pv_after["products"][0]["thumbnail_path"], str(real_thumb))


if __name__ == "__main__":
    unittest.main()
