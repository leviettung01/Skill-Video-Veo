# -*- coding: utf-8 -*-
"""Offline unit tests for Studio project filtering, idle-Chrome prevention, multi-account failover, and batch dispatch."""
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "flow_final_pipeline" / "scripts"
for p in (str(ROOT_DIR), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import fashion_motion_control_engine as fmce
import flow_workflow_engine as wf
import grok_video_tool as gvt
import product_crawler_bridge as pcb
import run_all_7_videos_mt as mt
import server
import sync_web_ui_state as sw


class StudioMultithreadAndSyncTests(unittest.TestCase):
    def test_sync_web_ui_excludes_bare_crawled_products_and_preserves_created_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            projects_dir = ws / "projects"
            finals_dir = ws / "final_videos"
            chars_dir = ws / "flow_final_pipeline" / "characters"
            projects_dir.mkdir(parents=True)
            finals_dir.mkdir(parents=True)
            chars_dir.mkdir(parents=True)

            # 1. Bare crawled product (info only, no prompts.json, no finals, not running)
            bare_dir = projects_dir / "1730000000000000001"
            (bare_dir / "product_images").mkdir(parents=True)
            (bare_dir / "product_images" / "info.json").write_text(
                json.dumps({"product_id": "1730000000000000001", "title": "Bare Product"}),
                encoding="utf-8",
            )

            # 2. Product with generated prompts.json
            prompted_dir = projects_dir / "1730000000000000002"
            (prompted_dir / "product_images").mkdir(parents=True)
            (prompted_dir / "product_images" / "info.json").write_text(
                json.dumps({"product_id": "1730000000000000002", "title": "Prompted Product"}),
                encoding="utf-8",
            )
            (prompted_dir / "prompts.json").write_text(
                json.dumps({"product_name": "Prompted Product", "videos": {"v1": {"character": "nv1", "scenes": []}}}),
                encoding="utf-8",
            )

            # 3. Custom user-created blank Studio project
            custom_dir = projects_dir / "proj_20261113_custom_test"
            custom_dir.mkdir()
            (custom_dir / "project.json").write_text(
                json.dumps({"id": "proj_20261113_custom_test", "name": "Custom Studio Proj", "products": [], "settings": {}}),
                encoding="utf-8",
            )

            # 4. Currently queued / running product
            running_dir = projects_dir / "1730000000000000003"
            (running_dir / "product_images").mkdir(parents=True)
            (running_dir / "product_images" / "info.json").write_text(
                json.dumps({"product_id": "1730000000000000003", "title": "Running Product"}),
                encoding="utf-8",
            )
            (running_dir / "pipeline_status.json").write_text(
                json.dumps({"is_running": True, "current_step_text": "Running"}),
                encoding="utf-8",
            )

            with patch.object(sw, "WORKSPACE", str(ws)), \
                 patch.object(sw, "PROJECTS_DIR", str(projects_dir)), \
                 patch.object(sw, "FINAL_VIDEOS_DIR", str(finals_dir)), \
                 patch.object(sw, "CHARS_DIR", str(chars_dir)):
                sw.sync_web_ui(force=True)

            idx_file = projects_dir / "projects_index.json"
            self.assertTrue(idx_file.is_file())
            idx_data = json.loads(idx_file.read_text(encoding="utf-8"))
            ids = {str(p.get("id")) for p in idx_data}

            self.assertNotIn("1730000000000000001", ids)
            self.assertFalse((bare_dir / "project.json").exists(), "Bare product must not receive fabricated project.json")
            self.assertIn("1730000000000000002", ids)
            self.assertIn("proj_20261113_custom_test", ids)
            self.assertIn("1730000000000000003", ids)
            self.assertEqual(len(ids), 3)

    def test_refresh_and_commit_google_account_idle_never_launches_chrome(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_root = Path(tmp) / "auth"
            auth_root.mkdir()
            fake_acc = types.SimpleNamespace(
                name="Google_acc_idle",
                api_key="expired_tok",
                proxy_url="11111111-1111-1111-1111-111111111111",
                google_email="idle@gmail.com",
            )
            fake_mgr = types.SimpleNamespace(accounts=[fake_acc])

            with patch.object(gvt, "GROK_AUTH_ROOT", auth_root), \
                 patch.object(gvt, "AccountManager", return_value=fake_mgr), \
                 patch.object(gvt, "_is_google_flow_account", return_value=True), \
                 patch.object(gvt, "_google_profile_name_for_account", return_value="acc_idle"), \
                 patch.object(gvt.GoogleTokenRefreshWorker, "_check_token", return_value=(False, "cookie expired")), \
                 patch.object(gvt, "_refresh_google_profile", side_effect=AssertionError("Idle check must never launch Chrome")) as mock_refresh, \
                 patch.object(server, "_ACTIVE_GOOGLE_WORKERS", {}):
                res_expired = server._refresh_and_commit_google_account("acc_idle", force_refresh=False)

            self.assertFalse(res_expired.get("ok"))
            self.assertFalse(res_expired.get("refreshed"))
            self.assertEqual(mock_refresh.call_count, 0)

            with patch.object(gvt, "GROK_AUTH_ROOT", auth_root), \
                 patch.object(gvt, "AccountManager", return_value=fake_mgr), \
                 patch.object(gvt, "_is_google_flow_account", return_value=True), \
                 patch.object(gvt, "_google_profile_name_for_account", return_value="acc_idle"), \
                 patch.object(gvt.GoogleTokenRefreshWorker, "_check_token", return_value=(True, "idle@gmail.com")), \
                 patch.object(gvt, "_upsert_flow_profile_registry"), \
                 patch.object(server.gfa, "commit_login"), \
                 patch.object(server, "_sync_cookie_file_to_skill_dirs"), \
                 patch.object(gvt, "_refresh_google_profile", side_effect=AssertionError("Valid HTTP check must not launch Chrome")), \
                 patch.object(server, "_ACTIVE_GOOGLE_WORKERS", {}):
                res_valid = server._refresh_and_commit_google_account("acc_idle", force_refresh=False)

            self.assertTrue(res_valid.get("ok"))
            self.assertFalse(res_valid.get("refreshed"))
            self.assertEqual(res_valid.get("email"), "idle@gmail.com")

    def test_no_hardcoded_932bc2a1_and_workflow_failover_on_missing_snlm0e(self):
        # Verify default PID resolution never injects stale hardcoded 932bc2a1
        with patch.object(mt, "_esm", None), patch.object(mt.gvt, "DEFAULT_PROJECT_ID", ""):
            self.assertEqual(mt._resolve_default_flow_pid("acc_any"), "")

        self.assertTrue(wf._is_flow_account_error_wf("Thiếu mã bảo mật SNlM0e từ trang Flow"))
        self.assertTrue(wf._is_flow_account_error_wf("HTTP 401 unauthorized cookie expired"))

        with tempfile.TemporaryDirectory() as tmp:
            wf_dir = Path(tmp) / "wf_out"
            wf_dir.mkdir()
            calls = []

            class _FakePage:
                def __init__(self, prof_tag):
                    self.prof_tag = prof_tag
                def add_init_script(self, script):
                    pass
                def goto(self, url, wait_until="domcontentloaded", timeout=60000):
                    calls.append((self.prof_tag, url))
                def wait_for_timeout(self, ms):
                    pass
                def evaluate(self, script):
                    if "SNlM0e" in script:
                        if self.prof_tag == "acc_bad":
                            return {"at": "", "bl": "bl_bad", "fsid": "f", "ua": "ua"}
                        return {"at": "valid_sn_token", "bl": "bl_good", "fsid": "f", "ua": "ua"}
                    return {}

            class _FakeCtx:
                def __init__(self, prof_tag):
                    self.pages = [_FakePage(prof_tag)]
                def new_page(self):
                    return self.pages[0]
                def close(self):
                    pass

            class _FakeChromium:
                def launch_persistent_context(self, user_data_dir="", **kwargs):
                    tag = "acc_bad" if "acc_bad" in str(user_data_dir) else "acc_good"
                    return _FakeCtx(tag)

            class _FakePW:
                def __init__(self):
                    self.chromium = _FakeChromium()
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False

            def _fake_gen_img(page, wiz, cookie_hdr, dl_headers, ref_task):
                Path(ref_task["out_file"]).write_bytes(b"\xff\xd8\xff\xe0FAKEJPEG")
                return True, "media_uuid_ok", None

            with patch.object(wf, "_get_ordered_flow_account_candidates_wf", return_value=[("acc_bad", "pid_1"), ("acc_good", "pid_2")]), \
                 patch.object(gvt, "_resolve_flow_shared_dir", return_value=tmp), \
                 patch.object(gvt, "_load_flow_cookie_header", return_value="SID=fake; HSID=fake"), \
                 patch("playwright.sync_api.sync_playwright", return_value=_FakePW()), \
                 patch.object(mt, "generate_variant_ref_image_in_page", side_effect=_fake_gen_img), \
                 patch.object(fmce, "ensure_image_is_2k", return_value={"width": 1536, "height": 2752}):
                fmce._UNHEALTHY_FLOW_PROFILES.clear()
                res = wf.execute_flow_generation_node(
                    {"node_id": "node_1", "media_type": "Image", "ratio": "9:16", "model": "Nano Banana Pro"},
                    "Test prompt",
                    [],
                    str(wf_dir),
                )

            self.assertTrue(res.get("ok"), f"Expected failover success, got: {res}")
            self.assertEqual(res.get("account_used"), "acc_good")
            self.assertEqual(len(calls), 2)
            self.assertIn("acc_bad", fmce._UNHEALTHY_FLOW_PROFILES)
            fmce._UNHEALTHY_FLOW_PROFILES.clear()

    def test_batch_prepare_and_optionally_run_products_launches_single_shared_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            projects_dir = ws / "projects"
            (projects_dir / "111").mkdir(parents=True)
            (projects_dir / "222").mkdir(parents=True)

            def _fake_prepare(*args, **kwargs):
                pid = str(args[0] if args else (kwargs.get("raw_id_or_url") or kwargs.get("raw_input_or_id") or kwargs.get("raw_input") or ""))
                return {"ok": True, "pid": pid, "project_dir": str(projects_dir / pid)}

            fake_proc = types.SimpleNamespace(pid=42424)
            with patch.object(pcb, "WS_DIR", str(ws)), \
                 patch.object(pcb, "PROJECTS_DIR", str(projects_dir)), \
                 patch.object(pcb, "prepare_and_optionally_run_product", side_effect=_fake_prepare), \
                 patch.object(pcb, "sync_web_ui"), \
                 patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
                res = pcb.batch_prepare_and_optionally_run_products(
                    ["111", "222"],
                    template_name="001",
                    auto_run_pipeline=True,
                )

            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("pids"), ["111", "222"])
            self.assertEqual(mock_popen.call_count, 1, "Batch selection must spawn ONE shared multi-PID worker")
            cmd_args = mock_popen.call_args[0][0]
            self.assertIn("111", cmd_args)
            self.assertIn("222", cmd_args)
            for pid in ("111", "222"):
                st = json.loads((projects_dir / pid / "pipeline_status.json").read_text(encoding="utf-8"))
                self.assertTrue(st.get("is_running"))
                self.assertEqual(st.get("pid_os"), 42424)


if __name__ == "__main__":
    unittest.main()
