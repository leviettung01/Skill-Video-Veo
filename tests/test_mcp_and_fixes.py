# -*- coding: utf-8 -*-
import base64
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "flow_final_pipeline" / "scripts"
for _p in (str(REPO_ROOT), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _make_sample_jpeg_b64(color=(180, 120, 90), size=(64, 64)) -> str:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


class TestPart1CharacterCreationAndFlowSync(unittest.TestCase):
    def test_generate_character_sheet_from_uploaded_source_portrait(self):
        import character_library_manager as clm
        import engine_settings_manager as esm

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chars_dir = tmp_path / "characters"
            chars_dir.mkdir(parents=True, exist_ok=True)
            vc_path = tmp_path / "voices_and_characters.json"
            vc_path.write_text(
                json.dumps({"characters": {}, "voices": {}}, ensure_ascii=False),
                encoding="utf-8",
            )

            captured = {}

            def _fake_cliproxy(req, out_abs):
                captured["prompt"] = req.get("prompt", "")
                captured["reference_images"] = list(req.get("reference_images") or [])
                Image.new("RGB", (320, 180), (40, 120, 200)).save(out_abs, format="JPEG")
                return True, "CLIProxy (gpt-image-2)", ""

            with (
                mock.patch.object(clm, "CHARS_DIR", str(chars_dir)),
                mock.patch.object(clm, "VOICES_CHARS_PATH", str(vc_path)),
                mock.patch.object(clm, "WS_DIR", str(tmp_path)),
                mock.patch.object(esm, "generate_image_via_cliproxy", side_effect=_fake_cliproxy),
            ):
                res = clm.generate_character_or_product_image(
                    {
                        "mode": "character_sheet",
                        "model": "chatgpt",
                        "char_key": "nv_test_face",
                        "char_name": "Nhân Vật Test Mặt Gốc",
                        "appearance_en": "young Vietnamese woman, warm smile",
                        "source_image_base64": _make_sample_jpeg_b64(),
                        "auto_apply_to_char": True,
                    }
                )

            self.assertTrue(res.get("ok"), msg=str(res))
            self.assertTrue(res.get("applied_to_char"))
            src_file = chars_dir / "nv_test_face_source.jpg"
            self.assertTrue(src_file.is_file(), "Ảnh nhân vật gốc phải được lưu xuống đĩa")
            self.assertEqual(captured["reference_images"][0], str(src_file))
            self.assertIn("exact face", captured["prompt"].lower())

            saved_cfg = json.loads(vc_path.read_text(encoding="utf-8"))
            ch = saved_cfg["characters"]["nv_test_face"]
            self.assertEqual(ch["name"], "Nhân Vật Test Mặt Gốc")
            self.assertTrue(ch.get("ref_image_file", "").endswith(".jpg"))
            self.assertEqual(ch.get("source_image_file"), "characters/nv_test_face_source.jpg")

    def test_sync_character_to_google_flow_persists_per_account_uuids(self):
        import character_library_manager as clm
        import engine_settings_manager as esm
        import grok_video_tool as gvt

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chars_dir = tmp_path / "characters"
            chars_dir.mkdir(parents=True, exist_ok=True)
            sheet_file = chars_dir / "nv_sync.jpg"
            Image.new("RGB", (200, 200), (20, 80, 140)).save(sheet_file, format="JPEG")

            vc_path = tmp_path / "voices_and_characters.json"
            vc_path.write_text(
                json.dumps(
                    {
                        "characters": {
                            "nv_sync": {
                                "key": "nv_sync",
                                "name": "Nhân Vật Sync",
                                "ref_image_file": "characters/nv_sync.jpg",
                            }
                        },
                        "voices": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            fake_accs = [
                {
                    "name": "Google_acc_a",
                    "profile_name": "acc_a",
                    "project_id": "11111111-1111-1111-1111-111111111111",
                    "api_key": "flow_cookie:session=abc",
                    "active": True,
                },
                {
                    "name": "Google_acc_b",
                    "profile_name": "acc_b",
                    "project_id": "22222222-2222-2222-2222-222222222222",
                    "api_key": "flow_cookie:session=def",
                    "active": True,
                },
            ]

            async def _fake_upload(page, img_path, tok, proj_id, *args, **kwargs):
                if str(proj_id).startswith("1111"):
                    return "aaaaaaaa-1111-1111-1111-111111111111"
                return "bbbbbbbb-2222-2222-2222-222222222222"

            with (
                mock.patch.object(clm, "CHARS_DIR", str(chars_dir)),
                mock.patch.object(clm, "PIPELINE_DIR", str(tmp_path)),
                mock.patch.object(clm, "VOICES_CHARS_PATH", str(vc_path)),
                mock.patch.object(clm, "WS_DIR", str(tmp_path)),
                mock.patch.object(esm, "list_available_flow_accounts", return_value=fake_accs),
                mock.patch.object(gvt, "upload_veo_image", side_effect=_fake_upload),
                mock.patch.object(gvt, "CaptchaBridge", side_effect=RuntimeError("no bridge needed")),
            ):
                res = clm.sync_character_to_google_flow("nv_sync", target_profile="all")

            self.assertTrue(res.get("ok"), msg=str(res))
            self.assertEqual(res.get("synced_count"), 2)
            self.assertEqual(res["synced_accounts"]["acc_a"], "aaaaaaaa-1111-1111-1111-111111111111")
            self.assertEqual(res["synced_accounts"]["acc_b"], "bbbbbbbb-2222-2222-2222-222222222222")

            saved_cfg = json.loads(vc_path.read_text(encoding="utf-8"))
            ch = saved_cfg["characters"]["nv_sync"]
            self.assertEqual(ch["character_id"], "aaaaaaaa-1111-1111-1111-111111111111")
            self.assertEqual(ch["account_character_ids"]["acc_b"], "bbbbbbbb-2222-2222-2222-222222222222")


class TestPart2StudioRetryAndDeleteUnfinished(unittest.TestCase):
    def test_retry_project_scene_basic_clears_error_and_clip_and_respawns(self):
        import server

        # Ensure initial module mtimes are loaded before patching `_pcb`
        server._ensure_latest_sws()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            proj_dir = tmp_path / "projects" / "999001"
            finals_dir = tmp_path / "final_videos"
            proj_dir.mkdir(parents=True, exist_ok=True)
            finals_dir.mkdir(parents=True, exist_ok=True)

            (proj_dir / "prompts.json").write_text(json.dumps({"v1": {}}), encoding="utf-8")
            (proj_dir / "v1_s2.mp4").write_bytes(b"broken")
            (finals_dir / "999001_nv1_v1.mp4").write_bytes(b"oldfinal")
            (proj_dir / "flow_state.json").write_text(
                json.dumps(
                    {
                        "scene_errors": {"v1_s2": "timeout", "v1_s3": "keep"},
                        "submitted": {"v1_s2": {"job": 1}},
                        "built_finals": ["v1", "v2"],
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(server.core, "PROJECTS_DIR", tmp_path / "projects"),
                mock.patch.object(server, "FINAL_VIDEOS_DIR", finals_dir),
                mock.patch.object(server, "ensure_captcha_solver_window_if_needed"),
                mock.patch.object(server, "sync_web_ui"),
                mock.patch.object(server._pcb, "enqueue_or_spawn_mt_pipeline", return_value=(12345, "spawned")) as m_spawn,
            ):
                res = server.retry_project_scene({"project_id": "999001", "vkey": "v1", "scene_number": 2})

            self.assertTrue(res.get("ok"), msg=str(res))
            self.assertFalse((proj_dir / "v1_s2.mp4").exists())
            self.assertFalse((finals_dir / "999001_nv1_v1.mp4").exists())
            st = json.loads((proj_dir / "flow_state.json").read_text(encoding="utf-8"))
            self.assertNotIn("v1_s2", st["scene_errors"])
            self.assertIn("v1_s3", st["scene_errors"])
            self.assertNotIn("v1_s2", st["submitted"])
            self.assertNotIn("v1", st["built_finals"])
            self.assertIn("v2", st["built_finals"])
            m_spawn.assert_called_once_with(["999001"])

    def test_retry_project_scene_transform_unlinks_scene_and_resumes(self):
        import server

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            proj_dir = tmp_path / "projects" / "tr_demo_01"
            proj_dir.mkdir(parents=True, exist_ok=True)
            (proj_dir / "transform.json").write_text(json.dumps({"id": "tr_demo_01"}), encoding="utf-8")
            (proj_dir / "scene_1.mp4").write_bytes(b"bad_scene_1")
            (proj_dir / "scene_2.mp4").write_bytes(b"good_scene_2" * 20000)
            (proj_dir / "video_final.mp4").write_bytes(b"old_final")

            fake_tr = mock.MagicMock()
            fake_tr.resume.return_value = {"ok": True, "queued": True}

            with (
                mock.patch.object(server.core, "PROJECTS_DIR", tmp_path / "projects"),
                mock.patch.object(server, "ensure_captcha_solver_window_if_needed"),
                mock.patch.object(server, "sync_web_ui"),
                mock.patch.object(server, "_get_transform_engine", return_value=fake_tr),
            ):
                res = server.retry_project_scene({"project_id": "tr_demo_01", "scene_number": 1})

            self.assertTrue(res.get("ok"), msg=str(res))
            self.assertFalse((proj_dir / "scene_1.mp4").exists())
            self.assertFalse((proj_dir / "video_final.mp4").exists())
            self.assertTrue((proj_dir / "scene_2.mp4").exists())
            fake_tr.resume.assert_called_once()

    def test_delete_unfinished_variant_basic_and_single_transform(self):
        import sync_web_ui_state as sws

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            projs = tmp_path / "projects"
            finals = tmp_path / "final_videos"
            projs.mkdir(parents=True, exist_ok=True)
            finals.mkdir(parents=True, exist_ok=True)

            # 1) Multi-variant Basic project
            bdir = projs / "888001"
            bdir.mkdir()
            (bdir / "prompts.json").write_text(json.dumps({"v1": {}, "v2": {}}), encoding="utf-8")
            (bdir / "v1_s1.mp4").write_bytes(b"keep_v1")
            (bdir / "v2_s1.mp4").write_bytes(b"del_v2")
            (bdir / "ref_v2.jpg").write_bytes(b"del_ref_v2")
            (bdir / "flow_state.json").write_text(
                json.dumps({"scene_errors": {"v2_s1": "err", "v1_s1": "ok"}, "built_finals": ["v1", "v2"]}),
                encoding="utf-8",
            )

            # 2) Single-video Transform project
            tdir = projs / "tr_del_01"
            tdir.mkdir()
            (tdir / "transform.json").write_text(json.dumps({"id": "tr_del_01"}), encoding="utf-8")
            (tdir / "scene_1.mp4").write_bytes(b"half_done")

            with (
                mock.patch.object(sws, "WORKSPACE", str(tmp_path)),
                mock.patch.object(sws, "PROJECTS_DIR", str(projs)),
                mock.patch.object(sws, "FINAL_VIDEOS_DIR", str(finals)),
                mock.patch.object(sws, "sync_web_ui", return_value=None),
            ):
                r_basic = sws.delete_unfinished_variant("888001", vkey="v2")
                self.assertTrue(r_basic.get("ok"), msg=str(r_basic))
                self.assertFalse((bdir / "v2_s1.mp4").exists())
                self.assertFalse((bdir / "ref_v2.jpg").exists())
                self.assertTrue((bdir / "v1_s1.mp4").exists())
                st = json.loads((bdir / "flow_state.json").read_text(encoding="utf-8"))
                self.assertNotIn("v2_s1", st["scene_errors"])
                self.assertIn("v1_s1", st["scene_errors"])

                r_tr = sws.delete_unfinished_variant("tr_del_01", vkey="v1", delete_project_if_single=True)
                self.assertTrue(r_tr.get("ok"), msg=str(r_tr))
                self.assertTrue(r_tr.get("deleted_project"))
                self.assertFalse(tdir.exists())


class TestPart3PortableSettingsAndThumbnails(unittest.TestCase):
    def test_build_final_inject_existing_thumb_works_with_skip_auto_thumb(self):
        import build_final as bf

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdir = tmp_path / "projects" / "777001"
            finals_dir = tmp_path / "final_videos"
            pdir.mkdir(parents=True, exist_ok=True)
            finals_dir.mkdir(parents=True, exist_ok=True)

            (pdir / "v2_s1.mp4").write_bytes(b"fake_clip_1")
            (pdir / "v2_s2.mp4").write_bytes(b"fake_clip_2")
            ov_img = pdir / "v1-refimg.jpg"
            Image.new("RGB", (108, 192), (180, 180, 180)).save(ov_img, format="JPEG")
            thumb_file = pdir / "thumb_nv2_v1.jpg"
            Image.new("RGB", (108, 192), (240, 200, 120)).save(thumb_file, format="JPEG")

            spec_path = pdir / "spec_v2.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "output": "777001_nv2_v1.mp4",
                        "overlays": ["v1-refimg.jpg"],
                        "scenes": [
                            {"file": "v2_s1.mp4", "trim_start": 0.0, "trim_end": 5.0, "phrases": [["xin chao", 2]]},
                            {"file": "v2_s2.mp4", "trim_start": 0.0, "trim_end": 5.0, "phrases": [["mua ngay", 2]]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            injected_calls = []

            class _FakeEsm:
                def load_engine_settings(self):
                    return {
                        "auto_generate_thumbnail": True,
                        "auto_inject_thumbnail_01s": True,
                        "thumbnail_duration_sec": 0.1,
                    }

                def get_variant_thumbnail_path(self, pid, char_v):
                    return str(thumb_file) if (pid == "777001" and char_v == "nv2_v1") else ""

                def inject_thumbnail_01s_into_video(self, video_path, th_path, duration_sec=0.1):
                    injected_calls.append((video_path, th_path, duration_sec))
                    return {"ok": True}

            def _fake_run(cmd, *args, **kwargs):
                if cmd and "ffmpeg" in os.path.basename(str(cmd[0])).lower():
                    cwd = kwargs.get("cwd")
                    target = Path(cmd[-1])
                    if cwd and not target.is_absolute():
                        target = Path(cwd) / target
                    target.write_bytes(b"fake_final_mp4_bytes")
                    return mock.MagicMock(returncode=0, stdout="", stderr="")
                return mock.MagicMock(returncode=0, stdout="10.0\n", stderr="")

            with (
                mock.patch.object(bf, "_esm", _FakeEsm()),
                mock.patch.object(bf.subprocess, "run", side_effect=_fake_run),
                mock.patch.object(sys, "argv", ["build_final.py", str(spec_path), "--skip-auto-thumb", "--inject-existing-thumb"]),
            ):
                bf.main()

            expected_final = finals_dir / "777001_nv2_v1.mp4"
            expected_sidecar = finals_dir / "777001_nv2_v1_thumb.jpg"
            self.assertTrue(expected_final.is_file())
            self.assertEqual(len(injected_calls), 1, "Phải gọi inject_thumbnail_01s_into_video ngay cả khi --skip-auto-thumb")
            self.assertEqual(Path(injected_calls[0][0]), expected_final)
            self.assertEqual(Path(injected_calls[0][1]), thumb_file)
            self.assertTrue(expected_sidecar.is_file(), "Phải xuất kèm file thumbnail sidecar cạnh video final")

    def test_portable_settings_clears_stale_flow_profiles_and_workspace_clean(self):
        import engine_settings_manager as esm

        # 1. Workspace default engine_settings.json has no machine-specific Flow profile
        ws_cfg = json.loads((REPO_ROOT / "flow_final_pipeline" / "engine_settings.json").read_text(encoding="utf-8"))
        self.assertEqual(ws_cfg.get("selected_flow_profile", ""), "")
        self.assertEqual(ws_cfg.get("selected_flow_profiles", []), [])
        self.assertTrue(ws_cfg.get("auto_generate_thumbnail"))
        self.assertTrue(ws_cfg.get("auto_inject_thumbnail_01s"))

        # 2. load_engine_settings auto-clears stale profiles from another machine
        with tempfile.TemporaryDirectory() as tmp:
            cfg_file = Path(tmp) / "engine_settings.json"
            cfg_file.write_text(
                json.dumps(
                    {
                        "selected_flow_profile": "dev_machine_only_acc",
                        "selected_flow_profiles": ["dev_machine_only_acc", "customer_acc_1"],
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(esm, "ENGINE_SETTINGS_JSON", str(cfg_file)),
                mock.patch.object(
                    esm,
                    "list_available_flow_accounts",
                    return_value=[{"profile_name": "customer_acc_1", "active": True}],
                ),
            ):
                loaded = esm.load_engine_settings()
            self.assertEqual(loaded["selected_flow_profile"], "")
            self.assertEqual(loaded["selected_flow_profiles"], ["customer_acc_1"])

    def test_thumbnail_flow_batch_strips_foreign_dev_char_uuid(self):
        import character_library_manager as clm
        import engine_settings_manager as esm
        import grok_video_tool as gvt

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vc_path = tmp_path / "voices_and_characters.json"
            vc_path.write_text(
                json.dumps(
                    {
                        "characters": {
                            "nv1": {
                                "key": "nv1",
                                "character_id": "dev-only-uuid-9999",
                                "owner_profile": "dev_machine_acc",
                                "account_character_ids": {"dev_machine_acc": "dev-only-uuid-9999"},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            out_img = tmp_path / "thumb_out.jpg"
            ref_img = tmp_path / "ref.jpg"
            Image.new("RGB", (64, 64), (100, 100, 100)).save(ref_img, format="JPEG")
            seen_jobs = []

            async def _fake_run_veo_flow(job, *args, **kwargs):
                seen_jobs.append(job)
                # Write a >5KB JPEG so Flow size guard accepts the generated thumbnail
                img = Image.effect_noise((512, 910), 40.0).convert("RGB")
                img.save(job.local_path, format="JPEG", quality=92)
                return True

            fake_accs = [
                {
                    "name": "Google_buyer_acc_1",
                    "profile_name": "buyer_acc_1",
                    "project_id": "33333333-3333-3333-3333-333333333333",
                    "api_key": "flow_cookie:session=buyer",
                    "active": True,
                }
            ]

            with (
                mock.patch.object(clm, "VOICES_CHARS_PATH", str(vc_path)),
                mock.patch.object(esm, "list_available_flow_accounts", return_value=fake_accs),
                mock.patch.object(esm, "load_engine_settings", return_value={"selected_flow_profile": "dev_machine_acc"}),
                mock.patch.object(gvt, "run_veo_flow", side_effect=_fake_run_veo_flow),
                mock.patch.object(gvt, "CaptchaBridge", side_effect=RuntimeError("no bridge needed")),
            ):
                results = esm._render_thumbnails_via_google_flow_batch(
                    [
                        {
                            "meta": {
                                "pid": "777001",
                                "vkey": "v1",
                                "char_v": "nv1_v1",
                                "prompt": "clean studio thumbnail",
                                "reference_images": [str(ref_img)],
                                "char_uuid": "dev-only-uuid-9999",
                            },
                            "out_thumb_proj": str(out_img),
                        }
                    ]
                )

            self.assertTrue(results["v1"][0], msg=str(results))
            self.assertEqual(len(seen_jobs), 1)
            self.assertFalse(
                getattr(seen_jobs[0], "character_id", ""),
                "Không được gửi Character UUID của máy dev sang tài khoản Flow của khách hàng!",
            )


class TestPart4SecureLicenseGatedMCP(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        import mcp_bridge_service as mbs

        self.mbs = mbs
        self.patches = [
            mock.patch.object(mbs, "DATA_DIR", self.tmp_path),
            mock.patch.object(mbs, "MCP_STATE_PATH", self.tmp_path / "mcp_state.json"),
            mock.patch.object(mbs, "MCP_LICENSE_PATH", self.tmp_path / "mcp_license.json"),
            mock.patch.object(mbs, "MCP_AUDIT_PATH", self.tmp_path / "mcp_audit.jsonl"),
            mock.patch.object(mbs, "_check_cloud_session_mcp_claim", return_value=None),
            mock.patch.dict(os.environ, {"SKILL_MCP_ADMIN_UNLOCK": ""}, clear=False),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self._tmp.cleanup()

    def test_mcp_locked_by_default_and_blocks_tampered_grants(self):
        ent = self.mbs.check_mcp_entitlement()
        self.assertFalse(ent["entitled"])

        code, resp = self.mbs.handle_mcp_http_request(
            raw_body=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).encode("utf-8"),
            headers={"Host": "127.0.0.1:8456"},
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 403)
        self.assertIn("error", resp)

        # Tampered grant must fail
        good = self.mbs.issue_signed_mcp_grant(account="vip@shop.vn", days=30)
        bad_sig = good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB")
        self.assertFalse(self.mbs.verify_signed_mcp_grant(bad_sig)["ok"])
        self.assertFalse(self.mbs.install_mcp_grant_key(bad_sig)["ok"])

        # Wrong HWID grant must fail
        other_hwid = self.mbs.issue_signed_mcp_grant(account="vip@shop.vn", hwid="deadbeef0000", days=30)
        self.assertFalse(self.mbs.verify_signed_mcp_grant(other_hwid)["ok"])

    def test_mcp_signed_grant_unlocks_protocol_and_enforces_auth_and_host(self):
        grant = self.mbs.issue_signed_mcp_grant(account="khachvip@brand.vn", days=90)
        inst = self.mbs.install_mcp_grant_key(grant)
        self.assertTrue(inst["ok"])
        self.assertTrue(inst["entitled"])
        self.assertTrue(inst["enabled"])
        tok = inst["token"]
        self.assertTrue(tok.startswith("skv_mcp_"))

        # Non-localhost Host -> 403
        code, _ = self.mbs.handle_mcp_http_request(
            raw_body=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
            headers={"Host": "evil.example.com", "Authorization": f"Bearer {tok}"},
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 403)

        # Non-loopback client IP -> 403
        code, _ = self.mbs.handle_mcp_http_request(
            raw_body=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
            headers={"Host": "127.0.0.1:8456", "Authorization": f"Bearer {tok}"},
            client_host="192.168.1.50",
        )
        self.assertEqual(code, 403)

        # Missing / wrong Bearer -> 401
        code, _ = self.mbs.handle_mcp_http_request(
            raw_body=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
            headers={"Host": "127.0.0.1:8456", "Authorization": "Bearer wrong_token"},
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 401)

        hdrs = {"Host": "127.0.0.1:8456", "Authorization": f"Bearer {tok}"}

        # initialize
        code, init_resp = self.mbs.handle_mcp_http_request(
            raw_body=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).encode("utf-8"),
            headers=hdrs,
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 200)
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "SkillAutoVeo-MCP")
        self.assertIn("instructions", init_resp["result"])

        # tools/list
        code, tl_resp = self.mbs.handle_mcp_http_request(
            raw_body=json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).encode("utf-8"),
            headers=hdrs,
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 200)
        tool_names = {t["name"] for t in tl_resp["result"]["tools"]}
        for expected in (
            "studio_get_overview",
            "products_list",
            "templates_list",
            "characters_list",
            "character_save",
            "character_generate_image",
            "character_sync_flow",
            "project_create_and_run",
            "project_stop",
            "project_retry_scene",
            "project_delete_unfinished",
            "transform_start",
            "thumbnail_generate",
        ):
            self.assertIn(expected, tool_names)

        # resources/read & prompts/get
        code, res_resp = self.mbs.handle_mcp_http_request(
            raw_body=json.dumps(
                {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "skillautoveo://guide"}}
            ).encode("utf-8"),
            headers=hdrs,
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 200)
        self.assertIn("SkillAutoVeo", res_resp["result"]["contents"][0]["text"])

        code, pr_resp = self.mbs.handle_mcp_http_request(
            raw_body=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "prompts/get",
                    "params": {"name": "create_product_video", "arguments": {"product_id": "12345", "template_code": "001"}},
                }
            ).encode("utf-8"),
            headers=hdrs,
            client_host="127.0.0.1",
        )
        self.assertEqual(code, 200)
        self.assertIn("12345", pr_resp["result"]["messages"][0]["content"]["text"])

    def test_mcp_tool_call_and_source_secret_sanitization(self):
        # Sanitizer strips secrets, cookies, tokens, source filenames & tracebacks
        dirty = {
            "ok": True,
            "api_key": "sk-proj-SUPERSECRET1234567890",
            "cookie": "__Secure-1PSID=very_secret_cookie",
            "bearer_token": "ya29.secret_token_val",
            "project_dir": r"C:\Users\ADMIN\Desktop\Python\secret\projects\123",
            "local_path": r"C:\Users\ADMIN\secret.py",
            "script": "server.py",
            "video": r"C:\Users\ADMIN\Desktop\final_videos\demo_nv1_v1.mp4",
            "note": r"Error in C:\Users\ADMIN\Desktop\Python\server.py",
        }
        cleaned = self.mbs.sanitize_for_mcp(dirty)
        self.assertNotIn("api_key", cleaned)
        self.assertNotIn("cookie", cleaned)
        self.assertNotIn("bearer_token", cleaned)
        self.assertNotIn("project_dir", cleaned)
        self.assertNotIn("local_path", cleaned)
        self.assertEqual(cleaned["script"], "[protected]")
        self.assertEqual(cleaned["video"], "demo_nv1_v1.mp4")
        self.assertNotIn("C:\\Users\\ADMIN", cleaned["note"])

        safe_err = self.mbs.sanitize_error_message(
            "Traceback (most recent call last):\n  File 'C:\\Users\\ADMIN\\server.py', line 99\n"
            "RuntimeError: failed with ya29.abcdef1234567890 and __Secure-1PSID=abc123 in build_final.py"
        )
        self.assertNotIn("Traceback", safe_err)
        self.assertNotIn("ya29.abcdef", safe_err)
        self.assertNotIn("abc123", safe_err)
        self.assertNotIn("build_final.py", safe_err)

        # End-to-end tools/call + audit trail
        grant = self.mbs.issue_signed_mcp_grant(account="agent_tester", days=30)
        tok = self.mbs.install_mcp_grant_key(grant)["token"]
        hdrs = {"Host": "127.0.0.1:8456", "Authorization": f"Bearer {tok}"}

        fake_ctx = {
            "list_projects": lambda: [{"id": "p1", "name": "SP Test", "status": "done", "project_dir": r"C:\secret\p1"}],
            "list_running": lambda: [],
        }
        code, call_resp = self.mbs.handle_mcp_http_request(
            raw_body=json.dumps(
                {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "projects_list", "arguments": {}}}
            ).encode("utf-8"),
            headers=hdrs,
            client_host="127.0.0.1",
            ctx=fake_ctx,
        )
        self.assertEqual(code, 200, msg=str(call_resp))
        payload = json.loads(call_resp["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["total"], 1)
        self.assertNotIn("project_dir", payload["projects"][0])

        # Also test voices_list & characters_list tools end-to-end
        for tool_nm in ("voices_list", "characters_list"):
            c2, r2 = self.mbs.handle_mcp_http_request(
                raw_body=json.dumps(
                    {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": tool_nm, "arguments": {}}}
                ).encode("utf-8"),
                headers=hdrs,
                client_host="127.0.0.1",
            )
            self.assertEqual(c2, 200, msg=f"{tool_nm}: {r2}")
            self.assertFalse(r2["result"].get("isError"), msg=f"{tool_nm}: {r2}")
            p2 = json.loads(r2["result"]["content"][0]["text"])
            self.assertTrue(p2["ok"], msg=f"{tool_nm}: {p2}")

        logs = self.mbs.get_recent_audit_logs(5)
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0]["tool"], "characters_list")
        self.assertEqual(logs[0]["account"], "agent_tester")

    def test_mcp_client_configs_and_ui_wiring(self):
        cfgs = self.mbs.build_client_configs(port=8456, token="skv_mcp_demo_token_1234567890")
        ag = json.loads(cfgs["antigravity_gemini"])
        self.assertEqual(ag["mcpServers"]["skillautoveo"]["serverUrl"], "http://127.0.0.1:8456/mcp")
        cd = json.loads(cfgs["claude_desktop_stdio"])
        self.assertIn("SKILL_MCP_TOKEN", cd["mcpServers"]["skillautoveo"]["env"])
        self.assertIn("http://127.0.0.1:8456/mcp", cfgs["claude_code_cli"])
        self.assertIn("[mcp_servers.skillautoveo]", cfgs["codex_chatgpt_toml"])

        html = (REPO_ROOT / "static" / "index.html").read_text(encoding="utf-8")
        for needle in (
            'id="mcpSettingsMount"',
            "/static/mcp_settings_ui.js",
            'id="inpGenSourceImage"',
            'id="inpEditCharSourceFile"',
            "generateCharSheetFromEditModal(true)",
            "syncEditCharToGoogleFlow()",
            "retryProjectScene(",
            "deleteUnfinishedVariant(",
        ):
            self.assertIn(needle, html, f"Thiếu phần tử UI mới trong static/index.html: {needle}")


if __name__ == "__main__":
    unittest.main()
