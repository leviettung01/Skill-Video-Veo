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

    def test_sync_web_ui_orders_newest_projects_first_across_all_pipelines(self):
        import os

        def _make_transform(projects_dir: Path, tid: str, status: str, ts: float, with_final: bool = False):
            tdir = projects_dir / tid
            tdir.mkdir(parents=True, exist_ok=True)
            (tdir / "product_input.jpg").write_bytes(b"jpg")
            if with_final:
                (tdir / "video_final.mp4").write_bytes(b"\x00" * 60000)
                os.utime(tdir / "video_final.mp4", (ts, ts))
            state = {
                "id": tid,
                "status": status,
                "message": "Loi thu nghiem" if status == "error" else "OK",
                "template_code": "006",
                "template_name": "Bien hinh",
                "preset": "fish",
                "image_provider": "banana",
                "scenes": [
                    {"title": "S1", "ref": "before_2k.jpg", "image_prompt": "a", "prompt": "b"},
                    {"title": "S2", "ref": "reveal_2k.jpg", "image_prompt": "c", "prompt": "d"},
                ],
                "refs": {},
                "updated_ts": ts,
                "created_ts": ts - 10,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts - 10)),
            }
            (tdir / "transform.json").write_text(json.dumps(state), encoding="utf-8")
            os.utime(tdir / "transform.json", (ts, ts))

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            projects_dir = ws / "projects"
            finals_dir = ws / "final_videos"
            chars_dir = ws / "flow_final_pipeline" / "characters"
            projects_dir.mkdir(parents=True)
            finals_dir.mkdir(parents=True)
            chars_dir.mkdir(parents=True)

            # Older finished cooking project (#005)
            cook_dir = projects_dir / "cooking_old"
            cook_dir.mkdir()
            cook_final = cook_dir / "cooking_old_pov.mp4"
            cook_final.write_bytes(b"\x00" * 60000)
            os.utime(cook_final, (1700001000.0, 1700001000.0))
            (cook_dir / "cooking_manifest.json").write_text(json.dumps({
                "project_id": "cooking_old",
                "dish": "Mon Cu",
                "status": "done",
                "final_video_path": str(cook_final),
                "clips": [],
                "updated_ts": 1700001000.0,
            }), encoding="utf-8")

            # Alphabetically FIRST but older transform finished (#006)
            _make_transform(projects_dir, "transform_0000000000000001", "done", 1700002000.0, with_final=True)
            # Newer standard product project (#001)
            prod_pid = "1730000000000000099"
            prod_dir = projects_dir / prod_pid
            (prod_dir / "product_images").mkdir(parents=True)
            (prod_dir / "product_images" / "info.json").write_text(json.dumps({"product_id": prod_pid, "title": "Newer Prod"}), encoding="utf-8")
            (prod_dir / "prompts.json").write_text(json.dumps({
                "product_name": "Newer Prod",
                "videos": {"v1": {"character": "nv1", "scenes": []}},
            }), encoding="utf-8")
            prod_final = finals_dir / f"{prod_pid}_nv1_v1.mp4"
            prod_final.write_bytes(b"\x00" * 60000)
            os.utime(prod_final, (1700004000.0, 1700004000.0))
            os.utime(prod_dir / "prompts.json", (1700004000.0, 1700004000.0))
            # Alphabetically LAST but NEWEST transform finished (#006)
            _make_transform(projects_dir, "transform_ffffffffffffffff", "done", 1700005000.0, with_final=True)

            # Pending/queued projects (newest must come before older)
            _make_transform(projects_dir, "transform_0000000000000002", "queued", 1700001500.0)
            _make_transform(projects_dir, "transform_eeeeee0000000001", "queued", 1700006000.0)

            # Errored projects (newest must come before older)
            _make_transform(projects_dir, "transform_0000000000000003", "error", 1700001200.0)
            _make_transform(projects_dir, "transform_dddddd0000000001", "error", 1700003500.0)

            with patch.object(sw, "WORKSPACE", str(ws)), \
                 patch.object(sw, "PROJECTS_DIR", str(projects_dir)), \
                 patch.object(sw, "FINAL_VIDEOS_DIR", str(finals_dir)), \
                 patch.object(sw, "CHARS_DIR", str(chars_dir)):
                sw.sync_web_ui(force=True)

            idx_data = json.loads((projects_dir / "projects_index.json").read_text(encoding="utf-8"))
            ordered_ids = [str(p.get("id")) for p in idx_data]
            self.assertEqual(ordered_ids, [
                "transform_ffffffffffffffff",
                prod_pid,
                "transform_0000000000000001",
                "cooking_old",
                "transform_eeeeee0000000001",
                "transform_0000000000000002",
                "transform_dddddd0000000001",
                "transform_0000000000000003",
            ])

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

    def test_auto_refresh_expired_background_heals_saved_profile_with_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_root = Path(tmp) / "auth"
            cookies_dir = auth_root / "cookies"
            prof_dir = auth_root / "native_profiles" / "acc_bg"
            cookies_dir.mkdir(parents=True)
            prof_dir.mkdir(parents=True)
            (cookies_dir / "acc_bg.json").write_text(
                json.dumps([{"name": "PREF", "value": "1"}]),
                encoding="utf-8",
            )

            fake_acc = types.SimpleNamespace(
                name="Google_acc_bg",
                api_key="",
                proxy_url="proj_old",
                google_email="bg@gmail.com",
            )
            fake_mgr = types.SimpleNamespace(accounts=[fake_acc])
            import google_flow_auth as _gfa
            saved_cooldown = dict(server._AUTO_REFRESH_COOLDOWN)
            server._AUTO_REFRESH_COOLDOWN.clear()
            try:
                with patch.object(gvt, "GROK_AUTH_ROOT", auth_root), \
                     patch.object(gvt, "AccountManager", return_value=fake_mgr), \
                     patch.object(gvt.GoogleTokenRefreshWorker, "_check_token", return_value=(False, "expired")), \
                     patch.object(gvt, "_refresh_google_profile", return_value=(True, "flow_cookie:SID=new; __Secure-1PSID=new", "proj_1", "session_verified:bg@gmail.com")) as mock_refresh, \
                     patch.object(_gfa, "commit_login", return_value=None), \
                     patch.object(server, "_sync_cookie_file_to_skill_dirs", return_value=None):
                    res_idle = server._refresh_and_commit_google_account(
                        "acc_bg",
                        force_refresh=False,
                        auto_refresh_expired=False,
                    )
                    self.assertEqual(mock_refresh.call_count, 0, f"Idle mode must not launch Chrome: {res_idle}")

                    res_heal = server._refresh_and_commit_google_account(
                        "acc_bg",
                        force_refresh=False,
                        auto_refresh_expired=True,
                    )
                    self.assertTrue(res_heal.get("ok"), msg=f"Background heal failed: {res_heal}")
                    self.assertTrue(res_heal.get("refreshed"), msg=f"Expected refreshed=True: {res_heal}")
                    self.assertEqual(mock_refresh.call_count, 1)
                    self.assertEqual(mock_refresh.call_args[0][0], "acc_bg")

                    fake_acc.api_key = ""
                    res_cool = server._refresh_and_commit_google_account(
                        "acc_bg",
                        force_refresh=False,
                        auto_refresh_expired=True,
                    )
                    self.assertEqual(mock_refresh.call_count, 1, f"Cooldown must block immediate second Chrome launch: {res_cool}")
            finally:
                server._AUTO_REFRESH_COOLDOWN.clear()
                server._AUTO_REFRESH_COOLDOWN.update(saved_cooldown)

    def test_extension_http_flow_page_executes_without_chrome_when_bridge_connected(self):
        def fake_real_sync_pw():
            raise AssertionError("Real Chrome sync_playwright must NOT be called when Extension bridge is connected")

        fake_real_sync_pw.__module__ = "playwright.sync_api._context_manager"

        class _FakeResp:
            def __init__(self, status_code=200, text="", headers=None, content=None):
                self.status_code = status_code
                self.text = text
                self.headers = headers or {}
                self.content = content if content is not None else text.encode("utf-8")

        class _FakeSession:
            def __init__(self, *a, **kw):
                self.calls = []
                self.cookies = {}

            def get(self, url, **kwargs):
                self.calls.append(("GET", url))
                html = '<script>window.WIZ_global_data = {"SNlM0e":"wiz_at_ok","cfb2h":"bl_ok","FdrFJe":"fsid_ok","oPEP7c":"ext@gmail.com"};</script>'
                return _FakeResp(200, text=html)

            def post(self, url, **kwargs):
                self.calls.append(("POST", url))
                if "batchexecute" in url:
                    inner = [["batch_uuid_ok"]]
                    line = json.dumps([["wrb.fr", "maseQ", json.dumps(inner), None, None, None, "generic"]])
                    return _FakeResp(200, text=")]}'\n" + line)
                if "/upload/v1/flow/upload/video/" in url:
                    return _FakeResp(200, text="{}", headers={"x-goog-upload-url": "https://flow.google.com/upload/scotty_put_1"})
                if "scotty_put_1" in url:
                    return _FakeResp(200, text=json.dumps({"mediaGenerationId": {"mediaGenerationId": "scotty_vid_1"}}))
                return _FakeResp(404, text="not found")

            def close(self):
                pass

        class _FakeBridge:
            def __init__(self):
                self.req_calls = []

            def extension_liveness(self):
                return "connected"

            def request_recaptcha_for_account(self, action="VIDEO_GENERATION", timeout=35, account_key=""):
                self.req_calls.append((action, account_key))
                return "03AFcWeA_" + ("R" * 100)

        fake_bridge = _FakeBridge()
        sessions = []

        def _make_session(*a, **kw):
            s = _FakeSession(*a, **kw)
            sessions.append(s)
            return s

        import curl_cffi.requests as _cc_req
        with patch.object(gvt, "get_connected_extension_bridge", return_value=fake_bridge), \
             patch.object(gvt, "_load_flow_cookie_header", return_value="SID=ext_sid; __Secure-1PSID=ext_psid"), \
             patch.object(_cc_req, "Session", side_effect=_make_session):
            with gvt.flow_playwright_or_extension(fake_real_sync_pw, profile_name="acc_ext", project_id="proj_ext") as pw:
                ctx = pw.chromium.launch_persistent_context("C:/fake/profile", headless=True)
                pg = ctx.new_page()
                pg.goto("https://flow.google.com/project/proj_ext", wait_until="domcontentloaded", timeout=15000)

                wiz = pg.evaluate(
                    """() => {
                        const w = window.WIZ_global_data || {};
                        return { at: w.SNlM0e || '', bl: w.cfb2h || '', fsid: w.FdrFJe || '', ua: navigator.userAgent || '' };
                    }"""
                )
                self.assertEqual(wiz.get("at"), "wiz_at_ok")
                self.assertEqual(wiz.get("bl"), "bl_ok")
                self.assertEqual(wiz.get("fsid"), "fsid_ok")

                tok = pg.evaluate(
                    """async ({siteKey, action}) => {
                        return await window.grecaptcha.enterprise.execute(siteKey, {action});
                    }""",
                    {"siteKey": "site_k", "action": "IMAGE_GENERATION"},
                )
                self.assertTrue(str(tok).startswith("03AFcWeA_"))

                rpc_res = pg.evaluate(
                    """async ({rpcid, projectId, bl, fsid, reqid, fReq, at}) => {
                        const r = await fetch(`/u/0/_/LabsAiSandboxUi/data/batchexecute?rpcids=${rpcid}&f.sid=${fsid}&bl=${bl}&_reqid=${reqid}`, {
                            method: 'POST',
                            body: new URLSearchParams({ 'f.req': fReq, at })
                        });
                        return { status: r.status, text: await r.text() };
                    }""",
                    {"rpcid": "maseQ", "projectId": "proj_ext", "bl": "bl_ok", "fsid": "fsid_ok", "reqid": 123456, "fReq": "[]", "at": "wiz_at_ok"},
                )
                self.assertEqual(rpc_res.get("status"), 200)
                self.assertIn("batch_uuid_ok", rpc_res.get("text", ""))

                import base64 as _b64
                raw_mp4 = b"mp4bytes"
                scotty_res = pg.evaluate(
                    """async ({projectId, atToken, fileName, b64Video, byteLength}) => {
                        const r = await fetch(`/upload/v1/flow/upload/video/${projectId}`, { method: 'POST', body: b64Video });
                        return await r.json();
                    }""",
                    {
                        "projectId": "proj_ext",
                        "atToken": "wiz_at_ok",
                        "fileName": "ref.mp4",
                        "b64Video": _b64.b64encode(raw_mp4).decode("ascii"),
                        "byteLength": len(raw_mp4),
                    },
                )
                self.assertTrue(scotty_res.get("ok"), msg=f"Scotty upload failed: {scotty_res}")
                self.assertIn("scotty_vid_1", scotty_res.get("text", ""))
                ctx.close()

        self.assertGreaterEqual(len(fake_bridge.req_calls), 1)
        self.assertEqual(fake_bridge.req_calls[0][0], "IMAGE_GENERATION")

    def test_sanitize_ua_sprcad_circuit_local_2k_and_secret_cache(self):
        self.assertEqual(
            gvt.sanitize_chrome_ua("Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessChrome/157.0.0.0 Safari/537.36"),
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/157.0.0.0 Safari/537.36",
        )
        fake_browser = types.SimpleNamespace(version="157.0.8103.78")
        self.assertIn("Chrome/157.0.0.0", gvt.sanitize_chrome_ua("", browser=fake_browser))
        self.assertNotIn("HeadlessChrome", gvt.sanitize_chrome_ua("", browser=fake_browser))

        # SPrCad shared circuit breaker opens after 3 fails and closes on success
        gvt.record_sprcad_result(True)
        self.assertFalse(gvt.is_sprcad_circuit_open())
        gvt.record_sprcad_result(False, "TOO_MUCH_TRAFFIC")
        gvt.record_sprcad_result(False, "TOO_MUCH_TRAFFIC")
        self.assertFalse(gvt.is_sprcad_circuit_open())
        gvt.record_sprcad_result(False, "TOO_MUCH_TRAFFIC")
        self.assertTrue(gvt.is_sprcad_circuit_open())
        gvt.record_sprcad_result(True)
        self.assertFalse(gvt.is_sprcad_circuit_open())

        with tempfile.TemporaryDirectory() as tmp:
            from PIL import Image
            img_p = Path(tmp) / "ref.jpg"
            Image.new("RGB", (768, 1376), (80, 90, 100)).save(str(img_p), format="JPEG")
            ok_2k, sz_2k = gvt.upscale_image_local_2k(str(img_p), 1536, 2752)
            self.assertTrue(ok_2k)
            self.assertGreater(sz_2k, 5000)
            with Image.open(str(img_p)) as out_im:
                self.assertEqual(out_im.size, (1536, 2752))

            sec_p = Path(tmp) / "captcha-bridge.secret"
            sec_p.write_text("abc_secret_123", encoding="utf-8")
            logs = []
            with patch.object(gvt.CaptchaBridge, "BRIDGE_SECRET_PATH", str(sec_p)):
                gvt.CaptchaBridge._SECRET_CACHE.update({"path": "", "mtime": -1.0, "val": ""})
                b1 = gvt.CaptchaBridge(log_func=logs.append, port=0)
                b2 = gvt.CaptchaBridge(log_func=logs.append, port=0)
                self.assertEqual(b1._bridge_secret, "abc_secret_123")
                self.assertEqual(b2._bridge_secret, "abc_secret_123")
                self.assertEqual(sum(1 for x in logs if "Bridge Secret" in x), 1)

    def test_thumbnail_rotates_account_on_rate_limit_and_safe_max_delay(self):
        import engine_settings_manager as esm
        prof = esm.compute_flow_concurrency_profile(2, ready_tabs=3, multi_account_enabled=True)
        self.assertGreaterEqual(prof["max"]["submit_delay_sec"], 3.5)

        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "projects" / "p_thumb"
            (pdir / "thumbnails").mkdir(parents=True)
            thumbs_root = Path(tmp) / "thumbnails"
            thumbs_root.mkdir(parents=True)
            seen_profs = []

            def fake_batch(items):
                m = items[0]["meta"]
                prof_used = m.get("google_profile_name")
                seen_profs.append(prof_used)
                if prof_used == "acc_bad":
                    return {"v1": (False, "google_flow", "PUBLIC_ERROR_UNUSUAL_ACTIVITY_TOO_MUCH_TRAFFIC [8]")}
                out_p = Path(items[0]["out_thumb_proj"])
                from PIL import Image
                import os as _os
                Image.frombytes("RGB", (256, 256), _os.urandom(256 * 256 * 3)).save(str(out_p), format="JPEG", quality=95)
                return {"v1": (True, "google_flow", "")}

            fake_meta = {
                "char_v": "nv1_v1",
                "template_id": "tpl_1",
                "prompt": "thumb prompt",
                "product_info": "Prod info",
                "char_holding_prod_img": "",
                "reference_images": [],
                "hook_title": "Hook",
                "product_name": "Prod",
                "price": "100k",
                "prod_img_path": "",
            }
            fake_cfg = {
                "thumbnail_provider": "google_flow",
                "multi_account_enabled": True,
                "selected_flow_profile": "acc_bad",
                "selected_flow_profiles": ["acc_bad", "acc_good"],
                "auto_inject_thumbnail_01s": False,
            }
            try:
                with patch.object(esm, "PROJECTS_DIR", str(Path(tmp) / "projects")), \
                     patch.object(esm, "THUMBS_ROOT_DIR", str(thumbs_root)), \
                     patch.object(esm, "load_engine_settings", return_value=fake_cfg), \
                     patch.object(esm, "build_thumbnail_prompt_for_variant", return_value=fake_meta), \
                     patch.object(esm, "_render_thumbnails_via_google_flow_batch", side_effect=fake_batch):
                    res = esm.generate_thumbnail_for_variant("p_thumb", "v1")
                    self.assertTrue(res.get("ok"), msg=res)
                    self.assertEqual(seen_profs, ["acc_bad", "acc_good"])
            finally:
                gvt.clear_flow_account_cooldown("acc_bad")
                gvt.clear_flow_account_cooldown("acc_good")

    def test_flow_error_classification_and_progressive_rate_limit_cooldown(self):
        # [8] / TOO_MUCH_TRAFFIC must ALWAYS classify as rate_limit (never captcha_score or content_policy)
        for sample in (
            "PUBLIC_ERROR_UNUSUAL_ACTIVITY_TOO_MUCH_TRAFFIC [8]",
            "MZZa6b [8] TOO_MUCH_TRAFFIC",
            "poll failed: code=8 resource exhausted",
            "video_failed:8:throttled",
        ):
            self.assertEqual(gvt.classify_flow_error(sample), "rate_limit", msg=sample)
            self.assertTrue(gvt.is_google_rate_limit_error(sample), msg=sample)

        # code=7 -> captcha_score; code=5 -> transient; bare HTTP 403 -> account_auth
        self.assertEqual(gvt.classify_flow_error("MZZa6b [7] PERMISSION_DENIED"), "captcha_score")
        self.assertEqual(gvt.classify_flow_error("poll failed: code=5 NOT_FOUND"), "transient")
        self.assertEqual(gvt.classify_flow_error("HTTP 403 Forbidden"), "account_auth")

        # Progressive rate-limit cooldown ladder
        acc_test = "unit_rate_ladder_acc"
        gvt.clear_flow_account_cooldown(acc_test)
        try:
            d1 = gvt.mark_flow_account_cooldown(acc_test, error_kind="rate_limit", reason="[8] TOO_MUCH_TRAFFIC")
            d2 = gvt.mark_flow_account_cooldown(acc_test, error_kind="rate_limit", reason="[8] TOO_MUCH_TRAFFIC")
            self.assertGreaterEqual(d1, 20.0)
            self.assertGreater(d2, d1)
        finally:
            gvt.clear_flow_account_cooldown(acc_test)
        self.assertEqual(gvt.is_flow_account_in_cooldown(acc_test)[1], 0.0)

        # Structured diagnostic error recording
        entry = gvt.record_diagnostic_error(
            "UnitTestModule",
            target="173999000111:v1:s1",
            account="tungultra18.11",
            error_text="MZZa6b [8] TOO_MUCH_TRAFFIC",
        )
        self.assertEqual(entry["kind"], "rate_limit")
        self.assertEqual(entry["category"], "rate_limit")
        self.assertTrue(entry["hint"])
        recent = gvt.get_recent_diagnostic_errors(5)
        self.assertTrue(any(e.get("target") == "173999000111:v1:s1" for e in recent))

    def test_character_and_voice_account_isolation(self):
        import character_library_manager as clm
        # Private leviettung04 voice/character UUIDs must NEVER leak to standalone accounts
        v_owner = clm.resolve_voice_id_for_account("nv1", "leviettung04")
        v_mapped = clm.resolve_voice_id_for_account("nv1", "flow_acc_4")
        v_other = clm.resolve_voice_id_for_account("nv1", "tungultra18.11")
        self.assertTrue(v_owner)
        self.assertTrue(v_mapped)
        self.assertNotEqual(v_owner, v_mapped)
        self.assertEqual(v_other, "")

        c_owner = clm.resolve_character_id_for_account("nv1", "leviettung04")
        c_other = clm.resolve_character_id_for_account("nv1", "tungultra18.11")
        self.assertTrue(c_owner)
        self.assertEqual(c_other, "")

        sheet_nv5 = clm.resolve_character_sheet_path("nv5")
        self.assertIsInstance(sheet_nv5, str)

    def test_sync_web_ui_surfaces_scene_errors_and_preserves_concurrent_flow_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            projects_dir = ws / "projects"
            finals_dir = ws / "final_videos"
            chars_dir = ws / "flow_final_pipeline" / "characters"
            projects_dir.mkdir(parents=True)
            finals_dir.mkdir(parents=True)
            chars_dir.mkdir(parents=True)

            pid = "1730000000000099999"
            pdir = projects_dir / pid
            (pdir / "product_images").mkdir(parents=True)
            (pdir / "product_images" / "info.json").write_text(
                json.dumps({"product_id": pid, "title": "Error Surface Prod"}),
                encoding="utf-8",
            )
            (pdir / "prompts.json").write_text(
                json.dumps({
                    "product_name": "Error Surface Prod",
                    "videos": {
                        "v1": {
                            "character": "nv1",
                            "scenes": [
                                {"id": "v1_s1", "file": "v1_s1.mp4", "prompt": "scene 1"},
                                {"id": "v1_s2", "file": "v1_s2.mp4", "prompt": "scene 2"},
                            ],
                        },
                        "v2": {
                            "character": "nv2",
                            "scenes": [{"id": "v2_s1", "file": "v2_s1.mp4", "prompt": "scene 2_1"}],
                        },
                    },
                }),
                encoding="utf-8",
            )
            # v2 has a finished final video; v1_s1 failed with a clear Flow diagnostic
            (finals_dir / f"{pid}_nv2_v1.mp4").write_bytes(b"\x00" * 70000)
            (pdir / "flow_state.json").write_text(
                json.dumps({
                    "uploaded_refs": {"acc1::prod": "uuid_keep_me"},
                    "scene_uuids": {"v1_s2": "uuid_scene_keep"},
                    "built_finals": [],
                    "scene_errors": {"v1_s1": "[TK:tungultra18.11] MZZa6b [8] TOO_MUCH_TRAFFIC"},
                    "failed_scenes": ["v1_s1"],
                }),
                encoding="utf-8",
            )

            with patch.object(sw, "WORKSPACE", str(ws)), \
                 patch.object(sw, "PROJECTS_DIR", str(projects_dir)), \
                 patch.object(sw, "FINAL_VIDEOS_DIR", str(finals_dir)), \
                 patch.object(sw, "CHARS_DIR", str(chars_dir)):
                sw.sync_web_ui(force=True)

            proj_data = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
            v1_card = next(p for p in proj_data["products"] if p["vkey"] == "v1")
            self.assertEqual(v1_card["status"], "failed")
            self.assertIn("TOO_MUCH_TRAFFIC", v1_card["error_msg"])
            s1_item = v1_card["scenes"][0]
            self.assertEqual(s1_item["status"], "failed")
            self.assertIn("TOO_MUCH_TRAFFIC", s1_item["error_msg"])

            saved_state = json.loads((pdir / "flow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_state["uploaded_refs"].get("acc1::prod"), "uuid_keep_me")
            self.assertEqual(saved_state["scene_uuids"].get("v1_s2"), "uuid_scene_keep")
            self.assertIn("v2", saved_state["built_finals"])

    def test_workflow_batch_pipeline_and_cooperative_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "wf_outputs"
            out_dir.mkdir()
            doc = wf.normalize_workflow_document({
                "id": "wf_batch_unit",
                "workflow": {
                    "name": "Batch Unit WF",
                    "settings": {"parallel": True, "stop_on_error": False},
                    "nodes": [
                        {"id": "img1", "node_type": "image", "label": "SP", "config": {"file_path": ""}},
                        {"id": "gen1", "node_type": "generate", "label": "Gen", "config": {"media_type": "Image", "prompt": "p"}},
                    ],
                    "edges": [{"source_node_id": "img1", "target_node_id": "gen1"}],
                },
            })
            seen_inputs = []

            def _fake_exec_single(nd_item, nodes_by_id, edges, node_outputs, wf_out_dir, profile_name):
                if nd_item["node_id"] == "img1":
                    p = (nd_item.get("config") or {}).get("file_path") or nd_item.get("local_path") or ""
                    seen_inputs.append(p)
                    return {"ok": True, "primary_path": p}
                return {"ok": False, "error": "Simulated node error"}

            with patch.object(wf, "WORKFLOW_OUTPUTS_DIR", str(out_dir)), \
                 patch.object(wf, "save_workflow_document", side_effect=lambda d, **kw: d), \
                 patch.object(wf, "execute_single_node_in_context", side_effect=_fake_exec_single):
                st = wf.run_workflow_batch_pipeline(
                    doc,
                    batch_config={
                        "mode": "product_swap",
                        "target_image_node_id": "img1",
                        "file_paths": ["sp_a.jpg", "sp_b.jpg"],
                        "auto_export_timeline": False,
                        "max_workers": 2,
                    },
                )
                self.assertEqual(sorted(seen_inputs), ["sp_a.jpg", "sp_b.jpg"])
                self.assertFalse(st.get("ok"))
                self.assertEqual(st.get("batch_completed"), 2)

                stop_res = wf.request_stop_workflow("wf_batch_unit")
                self.assertTrue(stop_res.get("ok"))
                self.assertTrue(wf.is_workflow_stopped("wf_batch_unit"))
                wf._WORKFLOW_STOP_FLAGS.discard("wf_batch_unit")

    def test_cooking_storyboards_stage_and_hot_queue_batch_pid(self):
        import cooking_storyboard_engine as cooking
        import engine_settings_manager as esm
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            projects_dir = ws / "projects"
            projects_dir.mkdir(parents=True)
            cook_pid = "cook_stage_storyboards_unit"
            cdir = projects_dir / cook_pid
            cdir.mkdir()
            sb_jpg = cdir / "clip1_storyboard.jpg"
            import hashlib as _hl
            sb_bytes = b"\xff\xd8\xff\xe0" + (b"\x00" * 60000)
            sb_jpg.write_bytes(sb_bytes)
            manifest = {
                "project_id": cook_pid,
                "dish": "Mon Test",
                "status": "prepared",
                "profile": "acc_cook",
                "flow_project_id": "11111111-2222-3333-4444-555555555555",
                "recipe": cooking.DEFAULT_RECIPE,
                "clips": [
                    {
                        "id": "c1",
                        "index": 1,
                        "title": "Clip 1",
                        "storyboard_file": sb_jpg.name,
                        "file": "clip1.mp4",
                        "image_prompt": "img p",
                        "prompt": "vid p",
                        "duration_sec": 8,
                        "native_2k": True,
                        "uploaded_2k_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "sha256": _hl.sha256(sb_bytes).hexdigest(),
                    }
                ],
            }
            (cdir / "cooking_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            with patch.object(cooking, "ROOT", ws), \
                 patch.object(cooking, "load_cooking_cookies", return_value=[{"name": "SID", "value": "1", "domain": ".google.com", "path": "/"}]), \
                 patch.object(cooking, "resolve_cooking_account", return_value=("acc_cook", "11111111-2222-3333-4444-555555555555")), \
                 patch.object(cooking, "sync_cooking_project"):
                out_m = cooking.run(cook_pid, stage="storyboards", profile="acc_cook", project_uuid="11111111-2222-3333-4444-555555555555")
            self.assertEqual(out_m["status"], "boards_ready")

            # Coordinated batch hot-queue + cooperative single-PID cancel
            fpipe_dir = ws / "flow_final_pipeline"
            fpipe_dir.mkdir(parents=True)
            (projects_dir / "111").mkdir()
            (projects_dir / "333").mkdir()
            import os as _os
            active_runner_path = fpipe_dir / "active_mt_runner.json"
            active_runner_path.write_text(
                json.dumps({"pid_os": _os.getpid(), "initial_pids": ["111", "222"], "started_at": "2026-11-18 20:00:00"}),
                encoding="utf-8",
            )
            pending_q_path = fpipe_dir / "pending_batch_pids.json"
            with patch.object(pcb, "WS_DIR", str(ws)), \
                 patch.object(pcb, "PROJECTS_DIR", str(projects_dir)), \
                 patch("subprocess.Popen", side_effect=AssertionError("Must enqueue into live runner, not spawn second Popen")):
                q_pid_os, q_sched, q_joined = pcb.enqueue_or_spawn_mt_pipeline(["333"])
            self.assertEqual(q_pid_os, _os.getpid())
            self.assertEqual(q_sched, ["333"])
            self.assertTrue(q_joined)
            self.assertIn("333", json.loads(pending_q_path.read_text(encoding="utf-8")))

            # Cooperative stop on 1 PID inside multi-PID batch must NOT taskkill sibling process!
            fake_ext_pid = 999991
            (projects_dir / "111" / "pipeline_status.json").write_text(
                json.dumps({"is_running": True, "pid_os": fake_ext_pid}),
                encoding="utf-8",
            )
            (projects_dir / "333" / "pipeline_status.json").write_text(
                json.dumps({"is_running": True, "pid_os": fake_ext_pid}),
                encoding="utf-8",
            )
            with patch.object(esm, "WS_DIR", str(ws)), \
                 patch.object(esm, "PROJECTS_DIR", str(projects_dir)), \
                 patch.object(esm, "is_os_pid_running", return_value=True), \
                 patch("subprocess.run", side_effect=AssertionError("Must cooperatively cancel single PID without taskkill when sibling is running")):
                stop_r = esm.stop_running_pipeline("333")
            self.assertTrue(stop_r.get("ok"))
            cancelled_list = json.loads((fpipe_dir / "cancelled_batch_pids.json").read_text(encoding="utf-8"))
            self.assertIn("333", cancelled_list)


if __name__ == "__main__":
    unittest.main()
