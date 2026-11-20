# -*- coding: utf-8 -*-
"""Focused unit tests for Template #006 atomic JSON persistence, Flow Tier-2 fallback,
Playwright cookie mapping, signed URL priority, and live hot-patch safety.
"""
import asyncio
import base64
import builtins
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "flow_final_pipeline" / "scripts"
for p in (str(ROOT_DIR), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import grok_video_tool as gvt
import sync_web_ui_state as sw
import transform_engine as te


class _DummyResponse:
    def __init__(self, status_code=200, text="", content=b""):
        self.status_code = status_code
        self.text = text
        self.content = content


class _DummyBridge:
    def __init__(self):
        self._last_extension_error = "grecaptcha not available"
        self.request_calls = 0

    def extension_liveness(self):
        return "connected"

    def request_recaptcha(self, action, timeout=20):
        self.request_calls += 1
        return None

    def notify_success(self):
        pass


class _DummyGClient:
    def __init__(self, as29s_payloads, img_bytes):
        self._as29s_payloads = list(as29s_payloads)
        self._img_bytes = img_bytes
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        if "flow.google.com/project/" in url:
            html = '"SNlM0e":"mock_at","cfb2h":"mock_bl","FdrFJe":"123456"'
            return _DummyResponse(200, text=html, content=html.encode("utf-8"))
        return _DummyResponse(200, content=self._img_bytes)

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        if "rpcids=as29s" in url:
            inner = self._as29s_payloads.pop(0) if self._as29s_payloads else []
            line = json.dumps([["wrb.fr", "as29s", json.dumps(inner), None, None, None, "generic"]])
            return _DummyResponse(200, text=")]}'\n" + line)
        return _DummyResponse(403, text="blocked")


class TransformAndFlowTier2Tests(unittest.TestCase):
    def test_save_and_read_json_safe_concurrent_no_winerror(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "transform_0123456789abcdef"
            folder.mkdir(parents=True)
            errors = []

            def writer():
                for i in range(30):
                    try:
                        te.save(
                            folder,
                            {
                                "ok": True,
                                "id": folder.name,
                                "status": "running" if i < 29 else "done",
                                "message": f"step {i}",
                                "preset": "farm",
                                "image_provider": "banana",
                                "music": True,
                                "scenes": [],
                                "refs": {},
                            },
                        )
                    except Exception as exc:
                        errors.append(exc)

            def reader():
                for _ in range(40):
                    p = folder / "transform.json"
                    if p.exists():
                        try:
                            data = te._read_json_safe(p)
                            self.assertEqual(data["id"], folder.name)
                        except Exception as exc:
                            errors.append(exc)

            t1 = threading.Thread(target=writer)
            t2 = threading.Thread(target=writer)
            t3 = threading.Thread(target=reader)
            t1.start(); t2.start(); t3.start()
            t1.join(); t2.join(); t3.join()
            self.assertEqual(errors, [])
            final = te._read_json_safe(folder / "transform.json")
            self.assertEqual(final["id"], folder.name)
            self.assertTrue((folder / "project.json").is_file())

    def test_cookie_mapping_and_storage_state_excludes_grecaptcha(self):
        cookie_str = (
            "SID=s1; SAPISID=sap1; OSID=osid_fresh; __Secure-OSID=sosid1; "
            "LSID=lsid1; __Host-1PLSID=hplsid1; _GRECAPTCHA=bad_tok"
        )
        pw_list = gvt._cookie_str_to_playwright_list(cookie_str)
        by_name = {c["name"]: c for c in pw_list}
        self.assertEqual(by_name["SID"]["domain"], ".google.com")
        self.assertEqual(by_name["OSID"]["domain"], "flow.google.com")
        self.assertEqual(by_name["__Secure-OSID"]["domain"], "flow.google.com")
        self.assertEqual(by_name["LSID"]["domain"], "accounts.google.com")
        self.assertEqual(by_name["__Host-1PLSID"]["url"], "https://accounts.google.com/")
        self.assertNotIn("domain", by_name["__Host-1PLSID"])

        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp)
            cdir = app_dir / "data" / "google_flow_grok" / "cookies"
            cdir.mkdir(parents=True)
            (cdir / "testprof.json").write_text(
                json.dumps(
                    {
                        "cookies": [
                            {"name": "OSID", "value": "osid_stale", "domain": "flow.google.com", "path": "/", "sameSite": "Lax", "secure": True, "httpOnly": True},
                            {"name": "__Host-1PLSID", "value": "hv", "domain": "accounts.google.com", "path": "/", "sameSite": "Lax", "secure": True, "httpOnly": True},
                            {"name": "_GRECAPTCHA", "value": "drop_me", "domain": "www.google.com", "path": "/", "sameSite": "None", "secure": True},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(gvt, "APP_DIR", app_dir), patch.object(gvt, "_resolve_google_profile_name", return_value="testprof"):
                loaded = gvt._load_playwright_cookies_for_flow("OSID=osid_fresh; EXTRA=e1", profile_name="testprof")
            names = [c["name"] for c in loaded]
            self.assertNotIn("_GRECAPTCHA", names)
            osid_entry = next(c for c in loaded if c["name"] == "OSID")
            self.assertEqual(osid_entry["value"], "osid_fresh")
            self.assertIn("EXTRA", names)

    def test_find_signed_flow_urls_priority(self):
        tree = [
            "https://lh3.googleusercontent.com/fallback_avatar",
            {"nested": ["https://flow-content.google/image/primary_img?sig=1"]},
            "https://storage.googleapis.com/fallback_vid.mp4",
            "https://flow-content.google/video/primary_vid.mp4",
        ]
        imgs = gvt._find_signed_flow_urls(tree, ("https://flow-content.google/image/", "https://lh3.googleusercontent.com/"))
        self.assertEqual(imgs[0], "https://flow-content.google/image/primary_img?sig=1")
        vids = gvt._find_signed_flow_urls(tree, ("https://flow-content.google/video/", "https://storage.googleapis.com/"))
        self.assertEqual(vids[0], "https://flow-content.google/video/primary_vid.mp4")

    def test_flow_request_only_falls_back_to_tier2_and_polls_as29s_before_sprcad(self):
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 600
        b64_2k = base64.b64encode(png_bytes).decode("ascii")

        for sprcad_succeeds in (True, False):
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                inp = tmp_dir / "input.jpg"
                inp.write_bytes(b"\xff\xd8\xff\xe0" + b"1" * 600)
                out = tmp_dir / "out.png"

                job = gvt.VideoJob(
                    prompt="test dress",
                    model="nano-banana-pro",
                    aspect_ratio="9:16",
                    resolution="2K",
                    image_url=str(inp),
                    flow_request_only=True,
                    prefer_extension_captcha=False,
                    google_profile_name="leviettung04",
                )
                bridge = _DummyBridge()

                rpc_sequence = []
                gclient = _DummyGClient(
                    as29s_payloads=[[["https://flow-content.google/image/generated_img?sig=abc"]]],
                    img_bytes=png_bytes,
                )

                def fake_chrome_exec(project_id, cookie_str, rpcid, payload_builder_fn, recaptcha_action, profile_name=""):
                    rpc_sequence.append((rpcid, recaptcha_action, profile_name))
                    if rpcid == "maseQ":
                        return True, [["11111111-1111-1111-1111-111111111111"]], ""
                    if rpcid == "ogiZ0b":
                        return True, [[["22222222-2222-2222-2222-222222222222"]]], ""
                    if rpcid == "SPrCad":
                        self.assertTrue(
                            any("rpcids=as29s" in u for m, u in gclient.calls if m == "POST"),
                            msg="SPrCad must run AFTER as29s confirms image readiness",
                        )
                        if sprcad_succeeds:
                            return True, ["ok", b64_2k], ""
                        return False, None, "upscale unsupported"
                    return False, None, "unexpected rpc"

                with patch.object(gvt, "_GoogleApiClient", return_value=gclient), \
                     patch.object(gvt, "_execute_flow_rpc_in_chrome", side_effect=fake_chrome_exec), \
                     patch("asyncio.sleep", return_value=None):
                    ok = asyncio.run(
                        gvt._run_veo_flow_batchexecute(
                            job=job,
                            project_id="proj-1",
                            auth_cookie="OSID=x; SID=y",
                            captcha_bridge=bridge,
                            _log=lambda m: None,
                            progress=None,
                            out_file=out,
                        )
                    )

                self.assertTrue(ok, msg=f"sprcad_succeeds={sprcad_succeeds}, err={job.error}")
                self.assertTrue(out.is_file())
                self.assertEqual([r[0] for r in rpc_sequence], ["maseQ", "ogiZ0b", "SPrCad"])
                self.assertEqual(rpc_sequence[0][2], "leviettung04")
                # Explicit opt-out (prefer_extension_captcha=False) bypasses Extension :4000
                self.assertEqual(bridge.request_calls, 0)
                # Ensure as29s poll executed BEFORE SPrCad
                post_urls = [u for m, u in gclient.calls if m == "POST"]
                self.assertTrue(any("rpcids=as29s" in u for u in post_urls))

    def test_default_extension_first_falls_back_to_chrome_when_extension_fails(self):
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 600
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            out = tmp_dir / "out.png"
            job = gvt.VideoJob(
                prompt="test dress",
                model="nano-banana-pro",
                aspect_ratio="9:16",
                resolution="1K",
                flow_request_only=True,
                google_profile_name="leviettung04",
            )
            bridge = _DummyBridge()
            gclient = _DummyGClient(
                as29s_payloads=[[["https://flow-content.google/image/generated_img?sig=abc"]]],
                img_bytes=png_bytes,
            )

            def fake_chrome_exec(project_id, cookie_str, rpcid, payload_builder_fn, recaptcha_action, profile_name=""):
                return True, [[["22222222-2222-2222-2222-222222222222"]]], ""

            with patch.object(gvt, "_GoogleApiClient", return_value=gclient), \
                 patch.object(gvt, "_execute_flow_rpc_in_chrome", side_effect=fake_chrome_exec), \
                 patch("asyncio.sleep", return_value=None):
                ok = asyncio.run(
                    gvt._run_veo_flow_batchexecute(
                        job=job,
                        project_id="proj-1",
                        auth_cookie="OSID=x; SID=y",
                        captcha_bridge=bridge,
                        _log=lambda m: None,
                        progress=None,
                        out_file=out,
                    )
                )
            self.assertTrue(ok)
            self.assertEqual(bridge.request_calls, 1)

    def test_extension_first_http_handles_many_accounts_without_launching_chrome(self):
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 600
        b64_2k = base64.b64encode(png_bytes).decode("ascii")

        class _LiveExtBridge:
            def __init__(self):
                self.last_browser_headers = {"user-agent": "Chrome/148.0.0.0"}
                self.actions = []
                self.successes = 0

            def extension_liveness(self):
                return "connected"

            def request_recaptcha(self, action, timeout=25):
                self.actions.append(action)
                return f"rcap_{len(self.actions)}_{action}"

            def notify_success(self):
                self.successes += 1

        class _HttpSuccessGClient:
            def __init__(self):
                self.posts = []
                self.gets = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, **kwargs):
                self.gets.append((url, kwargs.get("headers", {})))
                if "flow.google.com/project/" in url:
                    cookie = (kwargs.get("headers") or {}).get("Cookie", "")
                    tag = "acc1" if "acc1" in cookie else "acc2"
                    html = f'"SNlM0e":"at_{tag}","cfb2h":"mock_bl","FdrFJe":"123"'
                    return _DummyResponse(200, text=html, content=html.encode("utf-8"))
                return _DummyResponse(200, content=png_bytes)

            async def post(self, url, **kwargs):
                hdrs = kwargs.get("headers") or {}
                data_s = kwargs.get("data") or ""
                self.posts.append((url, hdrs.get("Cookie", ""), data_s))
                rpcid = url.split("rpcids=")[1].split("&")[0]
                if rpcid == "maseQ":
                    inner = [["11111111-1111-1111-1111-111111111111"]]
                elif rpcid == "ogiZ0b":
                    inner = [[["22222222-2222-2222-2222-222222222222"]]]
                elif rpcid == "as29s":
                    inner = [[["https://flow-content.google/image/generated_img?sig=ok"]]]
                elif rpcid == "SPrCad":
                    inner = ["ok", b64_2k]
                else:
                    return _DummyResponse(400, text="bad")
                line = json.dumps([["wrb.fr", rpcid, json.dumps(inner), None, None, None, "generic"]])
                return _DummyResponse(200, text=")]}'\n" + line)

        bridge = _LiveExtBridge()
        gclient = _HttpSuccessGClient()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            inp = tmp_dir / "ref.jpg"
            inp.write_bytes(b"\xff\xd8\xff\xe0" + b"1" * 600)
            for idx, (pid, ck) in enumerate((
                ("proj-acc-1", "SID=acc1; __Secure-1PSID=a1"),
                ("proj-acc-2", "SID=acc2; __Secure-1PSID=a2"),
            ), start=1):
                out = tmp_dir / f"out_{idx}.png"
                job = gvt.VideoJob(
                    prompt="editorial look",
                    model="nano-banana-pro",
                    aspect_ratio="9:16",
                    resolution="2K",
                    image_url=str(inp),
                    flow_request_only=True,
                    google_profile_name=f"flow_acc_{idx}",
                )
                with patch.object(gvt, "_GoogleApiClient", return_value=gclient), \
                     patch.object(gvt, "_execute_flow_rpc_in_chrome", side_effect=AssertionError("Must not launch Chrome!")), \
                     patch.object(gvt, "_get_flow_browser_actor", side_effect=AssertionError("Must not spawn Chrome actor!")), \
                     patch("asyncio.sleep", return_value=None):
                    ok = asyncio.run(
                        gvt._run_veo_flow_batchexecute(
                            job=job,
                            project_id=pid,
                            auth_cookie=ck,
                            captcha_bridge=bridge,
                            _log=lambda m: None,
                            progress=None,
                            out_file=out,
                        )
                    )
                self.assertTrue(ok, msg=f"acc {idx} failed: {job.error}")
                self.assertTrue(out.is_file())

        self.assertEqual(bridge.actions, ["UPLOAD_IMAGE", "IMAGE_GENERATION", "IMAGE_GENERATION"] * 2)
        self.assertEqual(bridge.successes, 6)
        self.assertTrue(any("proj-acc-1" in u and "SID=acc1" in c and "at_acc1" in b for u, c, b in gclient.posts))
        self.assertTrue(any("proj-acc-2" in u and "SID=acc2" in c and "at_acc2" in b for u, c, b in gclient.posts))

    def test_eb1hjf_unusual_activity_rotates_to_mzza6b_over_http_extension(self):
        mp4_bytes = b"\x00\x00\x00\x18ftypmp42" + b"0" * 1200

        class _LiveExtBridge:
            def __init__(self):
                self.last_browser_headers = {}
                self.calls = 0

            def extension_liveness(self):
                return "connected"

            def request_recaptcha(self, action, timeout=25):
                self.calls += 1
                return f"tok_{self.calls}"

            def notify_success(self):
                pass

            def notify_failure(self):
                pass

            def notify_recaptcha_score_dead(self):
                pass

        class _RotateHttpClient:
            def __init__(self):
                self.rpcs = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, **kwargs):
                if "flow.google.com/project/" in url:
                    html = '"SNlM0e":"at_v","cfb2h":"bl_v","FdrFJe":"99"'
                    return _DummyResponse(200, text=html, content=html.encode("utf-8"))
                return _DummyResponse(200, content=mp4_bytes)

            async def post(self, url, **kwargs):
                rpcid = url.split("rpcids=")[1].split("&")[0]
                self.rpcs.append(rpcid)
                if rpcid == "maseQ":
                    line = json.dumps([["wrb.fr", "maseQ", json.dumps([["33333333-3333-3333-3333-333333333333"]]), None, None, None, "generic"]])
                elif rpcid == "eb1hJf":
                    line = json.dumps([["wrb.fr", "eb1hJf", None, None, None, [7, None, [["type.googleapis.com/google.rpc.ErrorInfo", ["PUBLIC_ERROR_UNUSUAL_ACTIVITY"]]]], "generic"]])
                elif rpcid == "MZZa6b":
                    line = json.dumps([["wrb.fr", "MZZa6b", json.dumps([None, 30, None, [["44444444-4444-4444-4444-444444444444"]]]), None, None, None, "generic"]])
                elif rpcid == "as29s":
                    line = json.dumps([["wrb.fr", "as29s", json.dumps([[["https://flow-content.google/video/vid.mp4?sig=1"]]]), None, None, None, "generic"]])
                else:
                    return _DummyResponse(400, text="bad")
                return _DummyResponse(200, text=")]}'\n" + line)

        prof = "test_http_rotate_mzza6b"
        gvt._flow_mzza6b_preferred_profiles.discard(prof)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                inp = tmp_dir / "ref.jpg"
                inp.write_bytes(b"\xff\xd8\xff\xe0" + b"1" * 600)
                out = tmp_dir / "out.mp4"
                job = gvt.VideoJob(
                    prompt="walk gracefully",
                    model="Veo 3.1 - Fast",
                    mode="image-to-video",
                    aspect_ratio="9:16",
                    duration=8,
                    image_url=str(inp),
                    flow_request_only=True,
                    google_profile_name=prof,
                )
                gclient = _RotateHttpClient()
                bridge = _LiveExtBridge()
                with patch.object(gvt, "_GoogleApiClient", return_value=gclient), \
                     patch.object(gvt, "_execute_flow_rpc_in_chrome", side_effect=AssertionError("Must not launch Chrome!")), \
                     patch("asyncio.sleep", return_value=None):
                    ok = asyncio.run(
                        gvt._run_veo_flow_batchexecute(
                            job=job,
                            project_id="proj-1",
                            auth_cookie="SID=v; __Secure-1PSID=v",
                            captcha_bridge=bridge,
                            _log=lambda m: None,
                            progress=None,
                            out_file=out,
                        )
                    )
                self.assertTrue(ok, msg=f"err={job.error}")
                self.assertTrue(out.is_file())
                self.assertEqual(gclient.rpcs, ["maseQ", "eb1hJf", "MZZa6b", "as29s"])
                self.assertEqual(bridge.calls, 3)
        finally:
            gvt._flow_mzza6b_preferred_profiles.discard(prof)

    def test_captcha_bridge_remote_client_shares_server_port(self):
        import urllib.request
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        server_bridge = gvt.CaptchaBridge(lambda m: None, port=port)
        self.assertTrue(server_bridge.start())
        try:
            server_bridge.record_extension_heartbeat(version="2.2.2", profile_id="ext-1", has_flow_tab=True)
            client_bridge = gvt.CaptchaBridge(lambda m: None, port=port)
            self.assertTrue(client_bridge.start(allow_remote=True))
            self.assertTrue(client_bridge._remote_bridge)
            self.assertEqual(client_bridge.extension_liveness(), "connected")

            def _fake_extension_worker():
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/internal/captcha/poll?timeout=5000", timeout=6) as r:
                    cmds = json.loads(r.read().decode()).get("commands") or []
                if cmds:
                    cid = cmds[0]["commandId"]
                    body = json.dumps({
                        "commandId": cid,
                        "token": "remote_rcap_token_123",
                        "browserHeaders": {"user-agent": "Chrome/149.0.0.0"},
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{port}/api/internal/captcha/result",
                        data=body,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=5).read()

            t = threading.Thread(target=_fake_extension_worker, daemon=True)
            t.start()
            tok = client_bridge.request_recaptcha("UPLOAD_IMAGE", timeout=8)
            t.join(timeout=3)
            self.assertEqual(tok, "remote_rcap_token_123")
            self.assertEqual(client_bridge.last_browser_headers.get("user-agent"), "Chrome/149.0.0.0")
            server_bridge._consecutive_failures = 2
            client_bridge.notify_success()
            self.assertEqual(server_bridge._consecutive_failures, 0)
        finally:
            server_bridge.stop()

    def test_veo_skill_cli_prefers_live_disk_cookie_over_stale_accounts_json(self):
        import veo_skill_cli as vsc
        runner = vsc.MultiThreadSkillRunner()
        fake_acc = MagicMock()
        fake_acc.name = "Google_leviettung05@gmail.com"
        fake_acc.active = True
        fake_acc.api_key = "flow_cookie:OSID=stale_api_key"
        fake_acc.proxy_url = "810bcc8c-1c1c-41a0-84e4-c34b5dc2bd58"
        fake_mgr = MagicMock()
        fake_mgr.accounts = [fake_acc]
        with patch.object(runner.gvt, "AccountManager", return_value=fake_mgr), \
             patch.object(runner.gvt, "_is_google_flow_account", return_value=True), \
             patch.object(runner.gvt, "_google_profile_name_for_account", return_value="flow_acc_2"), \
             patch.object(runner.gvt, "_load_flow_cookie_header", return_value="SID=fresh; OSID=fresh_disk"):
            cands = runner.flow_account_candidates()
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0][1], "flow_cookie:SID=fresh; OSID=fresh_disk")

    def test_flow_browser_actor_reuses_context_and_evicts_on_unusual_activity(self):
        actor = gvt._FlowBrowserActor()
        created = []

        class _FakePage:
            def __init__(self, fail_unusual=False):
                self.closed = False
                self.url = "https://flow.google.com/project/p1"
                self.mouse = MagicMock()
                self._fail_unusual = fail_unusual

            def is_closed(self):
                return self.closed

            def goto(self, *a, **kw):
                pass

            def evaluate(self, script, arg=None):
                if "WIZ_global_data" in str(script) and "return {" in str(script):
                    return {"at": "at_tok", "bl": "bl_val", "fsid": "99", "ua": "UA"}
                if "batchexecute" in str(script):
                    if self._fail_unusual:
                        line = json.dumps([["wrb.fr", "eb1hJf", None, None, None, [7, None, [["type.googleapis.com/google.rpc.ErrorInfo", ["PUBLIC_ERROR_UNUSUAL_ACTIVITY"]]]], "generic"]])
                        return {"status": 200, "text": ")]}'\n" + line}
                    line = json.dumps([["wrb.fr", "maseQ", json.dumps([["uuid-1"]]), None, None, None, "generic"]])
                    return {"status": 200, "text": ")]}'\n" + line}
                return "rcap_tok"

            def wait_for_function(self, *a, **kw):
                pass

            def wait_for_timeout(self, *a, **kw):
                pass

            def close(self):
                self.closed = True

        class _FakeCtx:
            def __init__(self, fail_unusual=False):
                self.pg = _FakePage(fail_unusual=fail_unusual)

            def add_init_script(self, *a, **kw):
                pass

            def add_cookies(self, *a, **kw):
                pass

            def new_page(self):
                return self.pg

            def close(self):
                self.pg.close()

        class _FakeBrowser:
            def is_connected(self):
                return True

            def new_context(self, **kw):
                idx = len(created)
                c = _FakeCtx(fail_unusual=(idx == 0))
                created.append(c)
                return c

        actor._browser = _FakeBrowser()
        with patch.object(actor, "_ensure_browser", return_value=actor._browser), \
             patch.object(actor, "_cookie_fingerprint", return_value="fp1"), \
             patch.object(gvt, "_load_playwright_cookies_for_flow", return_value=[]):
            try:
                ok1, _, err1 = actor.execute_rpc("p1", "SID=1", "eb1hJf", lambda t: [t], "VIDEO_GENERATION", "prof1")
                self.assertFalse(ok1)
                self.assertIn("PUBLIC_ERROR_UNUSUAL_ACTIVITY", err1)
                self.assertTrue(created[0].pg.closed)

                ok2, inner2, _ = actor.execute_rpc("p1", "SID=1", "maseQ", lambda t: [t], "UPLOAD_IMAGE", "prof1")
                ok3, inner3, _ = actor.execute_rpc("p1", "SID=1", "maseQ", lambda t: [t], "UPLOAD_IMAGE", "prof1")
                self.assertTrue(ok2 and ok3)
                self.assertEqual(len(created), 2)
                self.assertEqual(inner2, [["uuid-1"]])
                self.assertEqual(inner3, [["uuid-1"]])
            finally:
                actor.shutdown()

    def test_i2v_syncs_to_mzza6b_on_unusual_activity(self):
        mp4_bytes = b"\x00\x00\x00\x18ftypmp42" + b"0" * 1200
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            inp = tmp_dir / "ref.jpg"
            inp.write_bytes(b"\xff\xd8\xff\xe0" + b"1" * 600)
            out1 = tmp_dir / "sc1.mp4"
            out2 = tmp_dir / "sc2.mp4"

            rpc_calls = []

            def fake_chrome_exec(project_id, cookie_str, rpcid, payload_builder_fn, recaptcha_action, profile_name=""):
                rpc_calls.append(rpcid)
                if rpcid == "maseQ":
                    return True, [["33333333-3333-3333-3333-333333333333"]], ""
                if rpcid == "eb1hJf":
                    return False, None, '[7, null, [["type.googleapis.com/google.rpc.ErrorInfo", ["PUBLIC_ERROR_UNUSUAL_ACTIVITY"]]]]'
                if rpcid == "MZZa6b":
                    return True, [None, 30, None, [["44444444-4444-4444-4444-444444444444"]]], ""
                return False, None, "unexpected"

            gvt._flow_mzza6b_preferred_profiles.discard("test_mzza6b_prof")
            try:
                for out_target in (out1, out2):
                    gclient = _DummyGClient(
                        as29s_payloads=[[["https://flow-content.google/video/vid.mp4?sig=1"]]],
                        img_bytes=mp4_bytes,
                    )
                    job = gvt.VideoJob(
                        prompt="walk in garden",
                        model="Veo 3.1 - Fast",
                        mode="image-to-video",
                        aspect_ratio="9:16",
                        duration=8,
                        image_url=str(inp),
                        flow_request_only=True,
                        google_profile_name="test_mzza6b_prof",
                    )
                    with patch.object(gvt, "_GoogleApiClient", return_value=gclient), \
                         patch.object(gvt, "_execute_flow_rpc_in_chrome", side_effect=fake_chrome_exec), \
                         patch("asyncio.sleep", return_value=None):
                        ok = asyncio.run(
                            gvt._run_veo_flow_batchexecute(
                                job=job,
                                project_id="proj-1",
                                auth_cookie="OSID=x; SID=y",
                                captcha_bridge=None,
                                _log=lambda m: None,
                                progress=None,
                                out_file=out_target,
                            )
                        )
                    self.assertTrue(ok, msg=f"err={job.error}")
                    self.assertTrue(out_target.is_file())

                self.assertEqual(rpc_calls, ["maseQ", "eb1hJf", "MZZa6b", "maseQ", "MZZa6b"])
            finally:
                gvt._flow_mzza6b_preferred_profiles.discard("test_mzza6b_prof")

    def test_hotpatch_live_modules_preserves_lock(self):
        orig_lock = te.LOCK
        cache = getattr(builtins, "_SKILLVEO_HOTPATCH_MTIMES", None)
        if isinstance(cache, dict):
            cache.clear()
        sw._hotpatch_live_modules()
        import transform_engine as te_after
        self.assertIs(te_after.LOCK, orig_lock)
        cache_after = getattr(builtins, "_SKILLVEO_HOTPATCH_MTIMES", {})
        self.assertIn("gvt", cache_after)

    def test_template006_timeline_prompts_and_character_sheet_lock(self):
        self.assertIn("2-column knolling", te.PRODUCT_PROMPT)
        self.assertIn("Accessories & Footwear", te.PRODUCT_PROMPT)
        self.assertIn("true width-to-length", te.PRODUCT_PROMPT)
        self.assertNotIn("styling accessories unrelated", te.PRODUCT_PROMPT)
        for preset in ("farm", "fish"):
            scenes = te.make_prompts(preset, has_character=True)
            self.assertEqual(len(scenes), 2)
            s1, s2 = scenes
            for marker in ("1.0x real-time", "never retract", "100% of the screen", "empty void"):
                self.assertIn(marker, s1["prompt"])
            for marker in ("8K", "aristocratic", "zero body spinning"):
                self.assertIn(marker, s2["prompt"])
            self.assertNotIn("360-degree", s2["prompt"])
            self.assertIn("turnaround sheet", s1["image_prompt"])
            self.assertIn("single-frame 9:16", s1["image_prompt"])
            self.assertIn("IGNORE", s2["image_prompt"].upper())
            if preset == "fish":
                for marker in ("[0.0s–3.0s", "[3.0s–5.4s", "[5.4s–7.0s", "[7.0s–8.0s"):
                    self.assertIn(marker, s1["prompt"])
                for marker in ("[0.0s–2.2s", "[2.2s–4.8s", "[4.8s–8.0s"):
                    self.assertIn(marker, s2["prompt"])
                self.assertIn("Tháng sau bọn anh cưới, rảnh thì qua chung vui nhé.", s1["prompt"])
                self.assertIn("STRICTLY NON-SPEAKING", s1["prompt"])
                self.assertIn("glistening tears", s1["prompt"])
                self.assertIn("black luxury sedan", s2["prompt"])
                self.assertIn("bodyguards", s2["prompt"])
                self.assertIn("camera flashes", s2["prompt"])
                self.assertNotIn("spoken dialogue", s1["prompt"])
            else:
                for marker in ("[0.0s–2.0s", "[2.0s–4.9s", "[4.9s–7.0s", "[7.0s–8.0s"):
                    self.assertIn(marker, s1["prompt"])
                self.assertIn("spoken dialogue", s1["prompt"])

    def test_template006_start_saves_structured_character_ref_and_project_view(self):
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGB", (320, 480), (220, 180, 140)).save(buf, format="JPEG")
        b64_img = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        chars = te._list_library_characters()
        with tempfile.TemporaryDirectory(dir=ROOT_DIR / "tests") as tmp:
            tmp_dir = Path(tmp)
            with patch.object(te, "JOBS", tmp_dir), \
                 patch.object(te.threading, "Thread") as mock_thread:
                mock_thread.return_value.start.return_value = None
                payload = {
                    "preset": "farm",
                    "image_provider": "banana",
                    "music": True,
                    "product_upload": b64_img,
                }
                if chars:
                    payload["character_key"] = chars[0]["key"]
                else:
                    payload["character_upload"] = b64_img
                res = te.start(payload)
                self.assertTrue(res["ok"])
                folder = tmp_dir / res["id"]
                st = te._read_json_safe(folder / "transform.json")
                char_ref = st["refs"].get("character")
                self.assertIsInstance(char_ref, dict)
                self.assertIn("path", char_ref)
                self.assertEqual(len(char_ref.get("dimensions", [])), 2)
                pv = te.project_view(folder, st)
                self.assertEqual(pv["pipeline_kind"], "fashion_transformation")
                self.assertEqual(pv["template_code"], "006")
                self.assertTrue(pv["character_image_path"].endswith("character_input.jpg"))
                self.assertEqual(pv["products"][0]["character_image_path"], pv["character_image_path"])

    def test_template006_export_early_occlusion_rewind_black_end_and_demo_music(self):
        import shutil
        import subprocess
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.skipTest("FFmpeg not installed")
        demo_farm = te.demo_video_path("farm")
        demo_fish = te.demo_video_path("fish")
        if not (demo_farm.is_file() and demo_fish.is_file()):
            self.skipTest("Demo videos missing")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            c1 = tmp_dir / "c1.mp4"
            c2 = tmp_dir / "c2.mp4"
            # Simulate Veo darkening lens around 6.7-7.0s then accidentally reopening to gray 7.1-8.0s
            subprocess.run([
                ffmpeg, "-v", "error", "-y",
                "-f", "lavfi", "-i", "color=c=#999999:s=360x640:r=24:d=8",
                "-vf", "drawbox=color=black:t=fill:enable='between(t,6.65,7.05)'",
                "-c:v", "libx264", "-preset", "ultrafast", str(c1),
            ], check=True)
            subprocess.run([
                ffmpeg, "-v", "error", "-y",
                "-f", "lavfi", "-i", "color=c=#3388cc:s=360x640:r=24:d=8",
                "-c:v", "libx264", "-preset", "ultrafast", str(c2),
            ], check=True)
            peak_t = te._detect_occlusion_peak(c1, 8.0)
            self.assertIsNotNone(peak_t)
            self.assertGreaterEqual(peak_t, 6.4)
            self.assertLessEqual(peak_t, 7.2)

            fish_inputs, fish_graph = te._build_audio_spec("fish", demo_fish, 18.0, True)
            self.assertIn("16.000", fish_inputs)
            self.assertNotIn("3.080", fish_inputs)
            self.assertIn("atrim=duration=16", fish_graph)

            for preset, demo in (("farm", demo_farm), ("fish", demo_fish)):
                out = tmp_dir / f"out_{preset}.mp4"
                te.export([c1, c2], demo, out, preset=preset)
                self.assertTrue(out.is_file())
                has_a, a_dur = te._probe_stream_duration(out, "a:0")
                has_v, v_dur = te._probe_stream_duration(out, "v:0")
                self.assertTrue(has_a and has_v)
                self.assertGreaterEqual(v_dur, 15.8)
                self.assertGreaterEqual(a_dur, 15.5)
                # Verify final frame of Scene 1 (t=7.88s) is pitch-black and Scene 2 (t=8.35s) is lit
                blk = subprocess.check_output([
                    ffmpeg, "-v", "error", "-ss", "7.88", "-i", str(out),
                    "-frames:v", "1", "-vf", "scale=16:16,format=gray", "-f", "rawvideo", "pipe:1",
                ])
                rev = subprocess.check_output([
                    ffmpeg, "-v", "error", "-ss", "8.35", "-i", str(out),
                    "-frames:v", "1", "-vf", "scale=16:16,format=gray", "-f", "rawvideo", "pipe:1",
                ])
                self.assertLessEqual(max(blk), 5)
                self.assertGreaterEqual(sum(rev) / len(rev), 70.0)

    def test_template_manager_excludes_duplicate_007_video_mau_folder(self):
        import template_manager as tm
        tpls = tm.list_video_templates()
        folder_names = {t.get("folder_name") for t in tpls}
        codes = {str(t.get("code") or "").lstrip("#") for t in tpls}
        self.assertIn("Bien Hinh Thoi Trang", folder_names)
        self.assertIn("006", codes)
        self.assertNotIn("Biến hình Làm nông, Bán cá", folder_names)

    def test_universal_studio_discovers_and_starts_custom_template_007(self):
        from PIL import Image
        import io as _io
        buf = _io.BytesIO()
        Image.new("RGB", (64, 64), (200, 120, 80)).save(buf, format="JPEG")
        b64_img = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            tpl_root = tmp_dir / "Template"
            t007 = tpl_root / "007_Cong_So"
            (t007 / "demo_videos").mkdir(parents=True)
            (t007 / "demo_videos" / "office.mp4").write_bytes(b"fake_mp4_bytes")
            (t007 / "template_config.json").write_text(json.dumps({
                "code": "007",
                "name": "Biến Hình Công Sở",
                "subtitle": "Bàn làm việc → Dạ tiệc",
                "ui_studio": "transform",
                "pipeline_kind": "fashion_transformation",
                "presets": {
                    "office": {
                        "title": "Công sở → Dạ tiệc",
                        "icon": "💼",
                        "badge": "Văn phòng → Sảnh tiệc",
                        "transition_style": "night_flash",
                        "demo": "office.mp4",
                        "summary": "Đóng laptop → che tay vào ống kính → bước ra sảnh tiệc.",
                        "before": "Office woman working late at desk.",
                        "work": "Closes laptop and looks at camera.",
                        "cover": "Covers lens with hand until pitch black.",
                        "after": "Evening ballroom entrance in golden bokeh.",
                        "reveal_open": "Emerges cleanly into ballroom light.",
                        "reveal_mid": "Confident runway turn in dress.",
                        "reveal_end": "Hero full-body pose through 8.0s."
                    }
                }
            }, ensure_ascii=False), encoding="utf-8")
            jobs_dir = tmp_dir / "projects"
            jobs_dir.mkdir(parents=True)

            with patch.object(te, "TEMPLATES_ROOT", tpl_root), \
                 patch.object(te, "JOBS", jobs_dir), \
                 patch.object(te.threading, "Thread") as mock_thread:
                mock_thread.return_value.start.return_value = None
                d_res = te.default("007")
                self.assertTrue(d_res["ok"])
                self.assertEqual(d_res["template"]["code"], "007")
                self.assertEqual(d_res["template"]["name"], "Biến Hình Công Sở")
                self.assertIn("office", d_res["presets"])
                self.assertGreaterEqual(len(d_res["studio_templates"]), 2)

                res = te.start({
                    "template_code": "007",
                    "preset": "office",
                    "image_provider": "banana",
                    "music": True,
                    "product_upload": b64_img,
                    "character_upload": b64_img,
                })
                self.assertTrue(res["ok"])
                st = te._read_json_safe(jobs_dir / res["id"] / "transform.json")
                self.assertEqual(st["template_code"], "007")
                self.assertEqual(st["preset"], "office")
                self.assertEqual(st["transition_style"], "night_flash")
                pv = te.project_view(jobs_dir / res["id"], st)
                self.assertEqual(pv["template_code"], "007")
                self.assertEqual(pv["template_name"], "Biến Hình Công Sở")
                self.assertIn("Công sở", pv["name"])

    def test_import_template_zip_and_zip_slip_protection(self):
        import io as _io
        import zipfile as _zf
        import template_manager as tm

        buf = _io.BytesIO()
        with _zf.ZipFile(buf, "w") as z:
            z.writestr("008_TiecCuoi/template_config.json", json.dumps({
                "code": "008",
                "name": "Biến Hình Tiệc Cưới",
                "pipeline_kind": "fashion_transformation",
                "presets": {"wedding": {"title": "Cô dâu", "summary": "Demo"}}
            }, ensure_ascii=False))
            z.writestr("008_TiecCuoi/ROLE_SKILL.md", "# Role Skill 008")

        with tempfile.TemporaryDirectory() as tmp:
            tpl_root = Path(tmp) / "Template"
            tpl_root.mkdir(parents=True)
            with patch.object(tm, "TEMPLATE_ROOT_DIR", str(tpl_root)):
                res = tm.import_template_zip(buf.getvalue())
                self.assertTrue(res["ok"])
                self.assertEqual(res["folder_name"], "008_TiecCuoi")
                self.assertEqual(res["installed"]["code"], "008")
                self.assertEqual(res["installed"]["ui_studio"], "transform")
                self.assertEqual(res["installed"]["presets_count"], 1)
                self.assertTrue((tpl_root / "008_TiecCuoi" / "ROLE_SKILL.md").is_file())

                bad = _io.BytesIO()
                with _zf.ZipFile(bad, "w") as bz:
                    bz.writestr("008_Bad/template_config.json", "{}")
                    bz.writestr("../../outside.txt", "evil")
                with self.assertRaises(ValueError):
                    tm.import_template_zip(bad.getvalue())

    def test_captcha_bridge_parallel_pool_and_duplicate_token_retry(self):
        import time as _time
        import urllib.request as _ureq

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        free_port = sock.getsockname()[1]
        sock.close()

        bridge = gvt.CaptchaBridge(log_func=lambda m: None, port=free_port)
        bridge.SAME_ACCOUNT_COOLDOWN_SEC = 0.05
        bridge.DEFAULT_MIN_INTERVAL_SEC = 0.01
        bridge.GLOBAL_DISPATCH_STAGGER_SEC = 0.01
        bridge._bridge_secret = "unit_test_bridge_secret"
        stop_ev = threading.Event()

        def _fake_extension_poller():
            dup_tok = "03AFcWeA_DUP_" + ("A" * 90)
            fresh_tokens = [
                dup_tok,
                dup_tok,
                "03AFcWeA_UNIQ_1_" + ("B" * 90),
                "03AFcWeA_UNIQ_2_" + ("C" * 90),
            ]
            tok_idx = 0
            hdrs = {"x-local-auth": "unit_test_bridge_secret"}
            while not stop_ev.is_set():
                try:
                    req = _ureq.Request(
                        f"http://127.0.0.1:{free_port}/api/internal/captcha/poll?profileId=ext_pool&readyTabs=3&poolSize=3&timeout=1",
                        headers=hdrs,
                    )
                    with _ureq.urlopen(req, timeout=3) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    for cmd in data.get("commands") or []:
                        tok = fresh_tokens[min(tok_idx, len(fresh_tokens) - 1)]
                        tok_idx += 1
                        body = json.dumps({
                            "commandId": cmd["commandId"],
                            "token": tok,
                            "profileId": "ext_pool",
                            "readyTabs": 3,
                            "poolSize": 3,
                        }).encode("utf-8")
                        post_req = _ureq.Request(
                            f"http://127.0.0.1:{free_port}/api/internal/captcha/result",
                            data=body,
                            headers={**hdrs, "Content-Type": "application/json"},
                            method="POST",
                        )
                        with _ureq.urlopen(post_req, timeout=3):
                            pass
                except Exception:
                    _time.sleep(0.05)

        bridge.start()
        t_poll = threading.Thread(target=_fake_extension_poller, daemon=True)
        try:
            t_poll.start()
            deadline = _time.time() + 5.0
            while bridge._effective_concurrency() < 3 and _time.time() < deadline:
                _time.sleep(0.05)
            self.assertEqual(bridge._effective_concurrency(), 3)

            results = {}
            errors = []

            def _fetch(acct):
                try:
                    results[acct] = bridge.request_recaptcha_for_account(
                        action="VIDEO_GENERATION",
                        timeout=8,
                        account_key=acct,
                    )
                except Exception as exc:
                    errors.append(str(exc))

            t0 = _time.monotonic()
            t1 = threading.Thread(target=_fetch, args=("acc_a",))
            t2 = threading.Thread(target=_fetch, args=("acc_b",))
            t1.start()
            t2.start()
            t1.join(timeout=8)
            t2.join(timeout=8)
            elapsed = _time.monotonic() - t0

            self.assertEqual(errors, [])
            self.assertIn("acc_a", results)
            self.assertIn("acc_b", results)
            self.assertTrue(len(results["acc_a"]) >= 80 and len(results["acc_b"]) >= 80)
            self.assertNotEqual(results["acc_a"], results["acc_b"])
            self.assertLess(elapsed, 6.0)
        finally:
            stop_ev.set()
            t_poll.join(timeout=2)
            bridge.stop()

    def test_batchexecute_inline_auto_refresh_on_missing_snlm0e_and_401(self):
        import google_flow_auth as _gfa

        mp4_bytes = b"\x00\x00\x00\x18ftypmp42" + b"0" * 1200

        class _InlineResp:
            def __init__(self, status_code=200, text="", content=b"", url="https://flow.google.com/project/proj-inline"):
                self.status_code = status_code
                self.text = text
                self.content = content if content else text.encode("utf-8")
                self.url = url
                self.headers = {}

        class _InlineBridge:
            def __init__(self):
                self.last_browser_headers = {}

            def extension_liveness(self):
                return "connected"

            def request_recaptcha_for_account(self, action, timeout=35, account_key=""):
                return "03AFcWeA_inline_" + ("Z" * 80)

            def request_recaptcha(self, action, timeout=25):
                return "03AFcWeA_inline_" + ("Z" * 80)

            def notify_success(self):
                pass

            def notify_failure(self):
                pass

            def notify_recaptcha_score_dead(self):
                pass

        for scenario in ("login_redirect", "http_401"):
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                out_mp4 = tmp_dir / f"inline_{scenario}.mp4"
                seen_cookies = []
                state = {"wiz_gets": 0, "rpc_calls": 0}

                class _ScenarioClient:
                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *a):
                        return False

                    async def get(self, url, **kwargs):
                        ck = (kwargs.get("headers") or {}).get("Cookie", "")
                        if "flow.google.com/project/" in url:
                            state["wiz_gets"] += 1
                            if scenario == "login_redirect" and state["wiz_gets"] == 1:
                                return _InlineResp(
                                    200,
                                    text="<html>Sign in accounts.google.com/v3/signin</html>",
                                    url="https://accounts.google.com/v3/signin",
                                )
                            html = '"SNlM0e":"at_fresh","cfb2h":"bl_fresh","FdrFJe":"777"'
                            return _InlineResp(200, text=html, url="https://flow.google.com/project/proj-inline")
                        return _InlineResp(200, content=mp4_bytes)

                    async def post(self, url, **kwargs):
                        ck = (kwargs.get("headers") or {}).get("Cookie", "")
                        seen_cookies.append(ck)
                        state["rpc_calls"] += 1
                        rpcid = url.split("rpcids=")[1].split("&")[0]
                        if scenario == "http_401" and state["rpc_calls"] == 1:
                            return _InlineResp(401, text="UNAUTHENTICATED")
                        if rpcid in ("YhhmEf", "eb1hJf", "MZZa6b"):
                            inner = [None, 30, None, [["55555555-5555-5555-5555-555555555555"]]]
                        elif rpcid == "as29s":
                            inner = [[["https://flow-content.google/video/inline.mp4?sig=ok"]]]
                        else:
                            return _InlineResp(400, text="bad")
                        line = json.dumps([["wrb.fr", rpcid, json.dumps(inner), None, None, None, "generic"]])
                        return _InlineResp(200, text=")]}'\n" + line)

                job = gvt.VideoJob(
                    prompt="city street walk",
                    model="Veo 3.1 - Fast",
                    mode="text-to-video",
                    aspect_ratio="9:16",
                    duration=8,
                    flow_request_only=True,
                    google_profile_name="prof_inline",
                )
                with patch.object(gvt, "GROK_AUTH_ROOT", tmp_dir / "auth"), \
                     patch.object(gvt, "_GoogleApiClient", return_value=_ScenarioClient()), \
                     patch.object(gvt, "_execute_flow_rpc_in_chrome", side_effect=AssertionError("Must not fall back to Chrome RPC")), \
                     patch.object(gvt, "_refresh_google_profile", return_value=(True, "flow_cookie:SID=fresh_ck; __Secure-1PSID=fresh_p", "proj-inline", "session_verified:inline@gmail.com")) as mock_ref, \
                     patch.object(_gfa, "commit_login", return_value=None), \
                     patch.object(gvt, "_load_flow_cookie_header", return_value="SID=fresh_ck; __Secure-1PSID=fresh_p"), \
                     patch("asyncio.sleep", return_value=None):
                    ok = asyncio.run(
                        gvt._run_veo_flow_batchexecute(
                            job=job,
                            project_id="proj-inline",
                            auth_cookie="SID=stale_ck; __Secure-1PSID=stale_p",
                            captcha_bridge=_InlineBridge(),
                            _log=lambda m: None,
                            progress=None,
                            out_file=out_mp4,
                        )
                    )
                self.assertTrue(ok, msg=f"scenario={scenario} failed: {job.error}")
                self.assertTrue(out_mp4.is_file())
                self.assertEqual(mock_ref.call_count, 1, msg=f"scenario={scenario} should trigger inline refresh once")
                self.assertTrue(any("SID=fresh_ck" in c for c in seen_cookies))

    def test_veo_skill_cli_per_account_throttle_does_not_block_distinct_accounts(self):
        import time as _time
        import veo_skill_cli as _vsc

        runner = _vsc.MultiThreadSkillRunner(captcha_bridge=None)
        runner.FLOW_SUBMIT_DELAY_SEC = 4.0
        runner.FLOW_GLOBAL_STAGGER_SEC = 0.05

        timings = {}
        runner._throttle_flow_submit(account_key="acc_1")

        def _hit(key):
            t0 = _time.monotonic()
            runner._throttle_flow_submit(account_key=key)
            timings[key] = _time.monotonic() - t0

        t_other = threading.Thread(target=_hit, args=("acc_2",))
        t_other.start()
        t_other.join(timeout=3.0)

        self.assertIn("acc_2", timings)
        self.assertLess(timings["acc_2"], 1.5, "Distinct account acc_2 must NOT sleep 4s behind acc_1")

    def test_transform_engine_rotates_accounts_and_parallelizes_scenes(self):
        import types as _types
        from PIL import Image as _PILImage

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            folder = ws / "projects" / "transform_unit_1"
            folder.mkdir(parents=True)
            _PILImage.new("RGB", (64, 64), (200, 120, 40)).save(folder / "product_input.jpg", format="JPEG")
            _PILImage.new("RGB", (64, 64), (80, 140, 220)).save(folder / "character_input.jpg", format="JPEG")

            state = {
                "id": "transform_unit_1",
                "preset": "fish",
                "template_code": "006",
                "template_name": "Bien hinh",
                "music": False,
                "image_provider": "flow",
                "product_prompt": "Extract garment cleanly.",
                "refs": {},
                "scenes": [
                    {"title": "S1", "ref": "before_2k.jpg", "image_prompt": "before img", "prompt": "scene 1 prompt"},
                    {"title": "S2", "ref": "reveal_2k.jpg", "image_prompt": "reveal img", "prompt": "scene 2 prompt"},
                ],
                "status": "queued",
                "logs": [],
            }

            acc1 = _types.SimpleNamespace(name="Google_a1", api_key="flow_cookie:SID=a1", proxy_url="proj_a1")
            acc2 = _types.SimpleNamespace(name="Google_a2", api_key="flow_cookie:SID=a2", proxy_url="proj_a2")

            class _FakeRunner:
                def __init__(self):
                    self.gvt = gvt

                def flow_account_candidates(self):
                    return [
                        (acc1, "flow_cookie:SID=a1", "proj_a1"),
                        (acc2, "flow_cookie:SID=a2", "proj_a2"),
                    ]

                def _throttle_flow_submit(self, log_fn=None, account_key=""):
                    return None

                def ensure_captcha_bridge(self):
                    return None

            used_accounts = []
            scene_threads = set()
            scene_barrier = threading.Barrier(2, timeout=2.0)
            req_lock = threading.Lock()

            async def _fake_run_veo_flow(job, token, project, bridge, log=None, progress=None):
                with req_lock:
                    used_accounts.append(job.account_name)
                if job.mode == "image-to-video":
                    scene_threads.add(threading.get_ident())
                    # Blocks unless both scene_1.mp4 and scene_2.mp4 run concurrently in vid_pool
                    scene_barrier.wait()
                    Path(job.local_path).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 512)
                else:
                    _PILImage.new("RGB", (64, 64), (50, 180, 90)).save(job.local_path, format="PNG")
                return True

            def _fake_export(clips, music_path, out_path, preset="", transition_style=""):
                Path(out_path).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"1" * 1024)

            import engine_settings_manager as _esm
            with patch.object(te, "ROOT", ws), \
                 patch.object(gvt, "GROK_AUTH_ROOT", ws / "auth"), \
                 patch.object(gvt, "_load_flow_cookie_header", return_value=""), \
                 patch.object(gvt, "_google_profile_name_for_account", side_effect=lambda acc, allow_unresolved=True: acc.name.replace("Google_", "")), \
                 patch.object(gvt.GoogleTokenRefreshWorker, "_check_token", return_value=(True, "user@gmail.com")), \
                 patch.object(gvt, "run_veo_flow", side_effect=_fake_run_veo_flow), \
                 patch.object(te, "export", side_effect=_fake_export), \
                 patch.object(_esm, "ensure_project_variant_thumbnail_and_inject", return_value={}):
                te.run(folder, state, runner=_FakeRunner())

            self.assertEqual(state.get("status"), "done", msg=f"transform failed: {state.get('message')}")
            self.assertTrue((folder / "video_final.mp4").is_file())
            self.assertIn("Google_a1", used_accounts)
            self.assertIn("Google_a2", used_accounts)
            self.assertEqual(len(scene_threads), 2, "scene_1.mp4 and scene_2.mp4 must execute on concurrent worker threads")

    def test_transform_engine_resume_existing_skips_completed_assets(self):
        import os as _os
        import types as _types
        from PIL import Image as _PILImage

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            folder = ws / "projects" / "transform_resume_1"
            folder.mkdir(parents=True)
            noisy_rgb = _os.urandom(512 * 512 * 3)
            for name in ("product_input.jpg", "character_input.jpg", "product_2k.jpg", "before_2k.jpg", "reveal_2k.jpg"):
                _PILImage.frombytes("RGB", (512, 512), noisy_rgb).save(folder / name, format="JPEG", quality=92)
                self.assertGreater((folder / name).stat().st_size, 20_000)
            (folder / "scene_1.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"A" * 210_000)

            state = {
                "id": "transform_resume_1",
                "preset": "fish",
                "template_code": "006",
                "template_name": "Bien hinh",
                "music": False,
                "image_provider": "flow",
                "product_prompt": "Extract garment cleanly.",
                "resume_existing": True,
                "refs": {},
                "scenes": [
                    {"title": "S1", "ref": "before_2k.jpg", "image_prompt": "before img", "prompt": "scene 1 prompt"},
                    {"title": "S2", "ref": "reveal_2k.jpg", "image_prompt": "reveal img", "prompt": "scene 2 prompt"},
                ],
                "status": "error",
                "logs": [],
            }

            acc1 = _types.SimpleNamespace(name="Google_a1", api_key="flow_cookie:SID=a1", proxy_url="proj_a1")

            class _FakeRunner:
                def __init__(self):
                    self.gvt = gvt

                def flow_account_candidates(self):
                    return [(acc1, "flow_cookie:SID=a1", "proj_a1")]

                def _throttle_flow_submit(self, log_fn=None, account_key=""):
                    return None

                def ensure_captcha_bridge(self):
                    return None

            requested_targets = []

            async def _fake_run_veo_flow(job, token, project, bridge, log=None, progress=None):
                requested_targets.append((job.mode, Path(job.local_path).name))
                Path(job.local_path).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"B" * 210_000)
                return True

            def _fake_export(clips, music_path, out_path, preset="", transition_style=""):
                Path(out_path).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"1" * 1024)

            import engine_settings_manager as _esm
            with patch.object(te, "ROOT", ws), \
                 patch.object(gvt, "GROK_AUTH_ROOT", ws / "auth"), \
                 patch.object(gvt, "_load_flow_cookie_header", return_value=""), \
                 patch.object(gvt, "_google_profile_name_for_account", return_value="a1"), \
                 patch.object(gvt.GoogleTokenRefreshWorker, "_check_token", return_value=(True, "user@gmail.com")), \
                 patch.object(te, "_probe_stream_duration", return_value=(True, 8.0)), \
                 patch.object(gvt, "run_veo_flow", side_effect=_fake_run_veo_flow), \
                 patch.object(te, "export", side_effect=_fake_export), \
                 patch.object(_esm, "ensure_project_variant_thumbnail_and_inject", return_value={}):
                te.run(folder, state, runner=_FakeRunner())

            self.assertEqual(state.get("status"), "done", msg=f"resume failed: {state.get('message')}")
            self.assertEqual(requested_targets, [("image-to-video", "scene_2.mp4")])
            self.assertNotIn("resume_existing", state)
            persisted = json.loads((folder / "transform.json").read_text(encoding="utf-8"))
            self.assertNotIn("resume_existing", persisted)

    def test_fish_postproduction_aligns_scene1_cuts_to_demo_dialogue(self):
        import shutil as _shutil
        import subprocess as _sub

        ffmpeg = _shutil.which("ffmpeg")
        if not ffmpeg:
            self.skipTest("ffmpeg not available")

        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            scene1_early = tdir / "scene_1.mp4"
            scene2_clip = tdir / "scene_2.mp4"
            demo_sync = tdir / "demo_fish.mp4"
            out_final = tdir / "final.mp4"

            # Synthetic Scene 1 with early cuts (1.40s and 4.40s) + Scene 2
            _sub.run([
                ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#808080:s=180x320:r=15:d=1.4",
                "-f", "lavfi", "-i", "color=c=white:s=180x320:r=15:d=3.0",
                "-f", "lavfi", "-i", "color=c=#203870:s=180x320:r=15:d=3.6",
                "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
                "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", str(scene1_early),
            ], check=True)
            _sub.run([
                ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#182430:s=180x320:r=15:d=8.0",
                "-c:v", "libx264", "-preset", "ultrafast", str(scene2_clip),
            ], check=True)
            # Synthetic Demo with target cuts at 3.10s & 5.50s and 16.5s audio
            _sub.run([
                ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#808080:s=180x320:r=15:d=3.1",
                "-f", "lavfi", "-i", "color=c=white:s=180x320:r=15:d=2.4",
                "-f", "lavfi", "-i", "color=c=#203870:s=180x320:r=15:d=11.0",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=16.5",
                "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
                "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(demo_sync),
            ], check=True)

            raw_cuts = te._detect_fish_scene_cuts(scene1_early, 8.0)
            self.assertIsNotNone(raw_cuts)
            self.assertAlmostEqual(raw_cuts[0], 1.40, delta=0.20)
            self.assertAlmostEqual(raw_cuts[1], 4.40, delta=0.20)

            te.export([scene1_early, scene2_clip], demo_sync, out_final, preset="fish", transition_style="night_flash")
            self.assertTrue(out_final.is_file())

            aligned_cuts = te._detect_fish_scene_cuts(out_final, 8.0)
            self.assertIsNotNone(aligned_cuts, "Aligned fish Scene 1 must preserve both shot cuts cleanly")
            self.assertAlmostEqual(aligned_cuts[0], 3.10, delta=0.25)
            self.assertAlmostEqual(aligned_cuts[1], 5.50, delta=0.25)

            prompts = te.make_prompts("fish", has_character=True, template_code="006")
            self.assertIn("3.0s", prompts[0]["prompt"])
            self.assertIn("5.4s", prompts[0]["prompt"])
            self.assertIn("airtight flat against the camera glass", prompts[0]["prompt"])
            self.assertIn("5.4m", prompts[1]["image_prompt"])
            self.assertIn("NO person or bodyguard ever clips through", prompts[1]["prompt"])

    def test_template006_defaults_to_omni_1_1_flash(self):
        self.assertEqual(te.DEFAULT_VIDEO_MODEL, "Omni 1.1 Flash")
        self.assertIn("Omni 1.1 Flash", te.SUPPORTED_VIDEO_MODELS)
        self.assertEqual(gvt.get_veo_model_key("Omni 1.1 Flash", "image-to-video", True, 8), "abra_i2v_8s")
        self.assertEqual(gvt.get_veo_model_key("Omni 1.1 Flash", "reference-to-video", True, 8), "abra_r2v_8s")

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "transform_test_omni"
            folder.mkdir(parents=True, exist_ok=True)
            state = {
                "id": "transform_test_omni",
                "status": "done",
                "message": "OK",
                "template_code": "006",
                "template_name": "Biến hình thời trang",
                "preset": "fish",
                "preset_title": "Bán cá",
                "image_provider": "banana",
                "video_model": "Omni 1.1 Flash",
                "scenes": [],
                "refs": {},
            }
            view = te.project_view(folder, state)
            self.assertEqual(view["settings"]["vid_model"], "Omni 1.1 Flash")
            state_legacy = dict(state)
            state_legacy.pop("video_model")
            view_legacy = te.project_view(folder, state_legacy)
            self.assertEqual(view_legacy["settings"]["vid_model"], "Omni 1.1 Flash")

    def test_flow_concurrency_profile_scaling_and_settings_modes(self):
        import engine_settings_manager as esm

        prof_1 = esm.compute_flow_concurrency_profile(1, ready_tabs=4, multi_account_enabled=True)
        prof_2 = esm.compute_flow_concurrency_profile(2, ready_tabs=4, multi_account_enabled=True)
        prof_5 = esm.compute_flow_concurrency_profile(5, ready_tabs=6, multi_account_enabled=True)
        prof_20 = esm.compute_flow_concurrency_profile(20, ready_tabs=8, multi_account_enabled=True)

        self.assertGreater(prof_2["optimal"]["flow_api_workers"], prof_1["optimal"]["flow_api_workers"])
        self.assertGreater(prof_5["optimal"]["est_requests_per_min"], prof_2["optimal"]["est_requests_per_min"])
        self.assertGreater(prof_20["optimal"]["max_total_inflight"], prof_5["optimal"]["max_total_inflight"])
        for prof in (prof_1, prof_2, prof_5, prof_20):
            self.assertGreaterEqual(prof["max"]["flow_api_workers"], prof["optimal"]["flow_api_workers"])
            self.assertGreaterEqual(prof["max"]["est_requests_per_min"], prof["optimal"]["est_requests_per_min"])
            self.assertLessEqual(
                prof["optimal"]["effective_global_interval_sec"],
                prof["optimal"]["submit_delay_sec"] + 0.01,
            )

        with tempfile.TemporaryDirectory() as tmp:
            fake_json = Path(tmp) / "engine_settings.json"
            fake_accs = [
                {"name": "Google_a1", "active": True},
                {"name": "Google_a2", "active": True},
                {"name": "Google_a3", "active": True},
                {"name": "Google_off", "active": False},
            ]
            with patch.object(esm, "ENGINE_SETTINGS_JSON", str(fake_json)), \
                 patch.object(esm, "list_available_flow_accounts", return_value=fake_accs), \
                 patch.object(esm, "get_live_extension_ready_tabs", return_value=4):
                loaded_opt = esm.load_engine_settings()
                self.assertEqual(loaded_opt["flow_concurrency_mode"], "optimal")
                self.assertTrue(loaded_opt["auto_flow_concurrency"])
                self.assertEqual(loaded_opt["flow_api_workers"], 9)
                self.assertEqual(loaded_opt["max_total_inflight"], 15)
                self.assertIn("flow_recommended", loaded_opt)

                saved_max = esm.save_engine_settings({"flow_concurrency_mode": "max"})["settings"]
                self.assertEqual(saved_max["flow_concurrency_mode"], "max")
                self.assertTrue(saved_max["auto_flow_concurrency"])
                self.assertEqual(saved_max["flow_api_workers"], 36)
                self.assertEqual(saved_max["max_total_inflight"], 36)
                self.assertGreaterEqual(saved_max["submit_delay_sec"], 3.0)

                saved_custom = esm.save_engine_settings({
                    "flow_api_workers": 18,
                    "upscale_download_workers": 12,
                    "submit_delay_sec": 3.0,
                })["settings"]
                self.assertEqual(saved_custom["flow_concurrency_mode"], "custom")
                self.assertFalse(saved_custom["auto_flow_concurrency"])
                self.assertEqual(saved_custom["flow_api_workers"], 18)
                self.assertEqual(saved_custom["upscale_download_workers"], 12)
                self.assertEqual(saved_custom["submit_delay_sec"], 3.0)

                saved_back_opt = esm.save_engine_settings({"flow_concurrency_mode": "optimal"})["settings"]
                self.assertEqual(saved_back_opt["flow_concurrency_mode"], "optimal")
                self.assertTrue(saved_back_opt["auto_flow_concurrency"])
                self.assertEqual(saved_back_opt["flow_api_workers"], 9)

    def test_captcha_bridge_scaling_pool_size_and_batch_poll(self):
        import time
        import urllib.request

        with socket.socket() as sock_probe:
            sock_probe.bind(("127.0.0.1", 0))
            free_port = sock_probe.getsockname()[1]

        bridge = gvt.CaptchaBridge(lambda msg: None, port=free_port)
        bridge._bridge_secret = "sec_test"
        self.assertTrue(bridge.start())
        try:
            bridge.record_extension_heartbeat(ready_tabs=6, profile_id="prof_a", has_flow_tab=True)
            bridge.record_extension_heartbeat(ready_tabs=6, profile_id="prof_b", has_flow_tab=True)
            self.assertEqual(bridge._effective_concurrency(), 12)

            bridge.apply_concurrency_settings(per_account_delay_sec=3.0, global_stagger_sec=0.5, pool_tabs=6)
            self.assertEqual(bridge._get_desired_pool_size(), 3)

            for idx in range(8):
                bridge._pending_commands.put({"commandId": f"cmd_{idx}", "type": "CAPTCHA", "action": "VIDEO"})

            req_poll = urllib.request.Request(
                f"http://127.0.0.1:{bridge.port}/api/internal/captcha/poll?profileId=prof_a&readyTabs=8&flowTabPresent=1",
                headers={"X-Bridge-Secret": "sec_test"},
            )
            with urllib.request.urlopen(req_poll, timeout=3.0) as resp:
                poll_payload = json.loads(resp.read().decode("utf-8"))

            self.assertEqual(poll_payload["desiredPoolSize"], 3)
            self.assertEqual(len(poll_payload["commands"]), 8)

            req_cfg = urllib.request.Request(f"http://127.0.0.1:{bridge.port}/api/internal/captcha/config")
            with urllib.request.urlopen(req_cfg, timeout=3.0) as resp:
                cfg_payload = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(cfg_payload["desiredPoolSize"], 3)

            w1 = bridge._reserve_account_dispatch_time("acc_1")
            w2_other = bridge._reserve_account_dispatch_time("acc_2")
            w3_same = bridge._reserve_account_dispatch_time("acc_1")
            self.assertAlmostEqual(w1, 0.0, delta=0.1)
            self.assertLess(w2_other, 0.5)
            self.assertGreater(w3_same, 1.2)
            _ = time.time()
        finally:
            bridge.stop()

    def test_decoupled_async_media_finalize_and_veo_cli_pipeline_overlap(self):
        import time
        import veo_skill_cli as vsc

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            out_media = tmp_dir / "bg_media.mp4"
            gate = threading.Event()

            def _bg_download():
                gate.wait(timeout=3.0)
                out_media.write_bytes(b"mp4bytes")
                return True

            job = gvt.VideoJob(
                id="job_async_1",
                prompt="test",
                local_path=str(out_media),
                async_media_finalize=True,
            )
            pool = gvt.get_flow_media_download_pool(4)
            job.media_finalize_future = pool.submit(_bg_download)
            self.assertFalse(out_media.exists())
            gate.set()
            self.assertEqual(gvt.wait_for_all_media_jobs([job], timeout=3.0), [True])
            self.assertTrue(out_media.is_file())

            fake_proj_root = tmp_dir / "projects"
            proj_id = "proj_pipe"
            proj_dir = fake_proj_root / proj_id
            prod_dir = proj_dir / "products" / "p1"
            prod_dir.mkdir(parents=True, exist_ok=True)
            img1 = prod_dir / "scene_01" / "image_scene_01.jpg"
            img2 = prod_dir / "scene_02" / "image_scene_02.jpg"
            vid1 = prod_dir / "scene_01" / "video_scene_01.mp4"
            vid2 = prod_dir / "scene_02" / "video_scene_02.mp4"
            final_mp4 = prod_dir / "final_product.mp4"
            for p in (img1, img2, vid1, vid2):
                p.parent.mkdir(parents=True, exist_ok=True)

            proj_doc = {
                "id": proj_id,
                "name": "Pipeline Test",
                "products": [{
                    "id": "p1",
                    "product_name": "Test Item",
                    "output_dir": str(prod_dir),
                    "aspect": "9:16",
                    "seconds_per_scene": 8,
                    "vid_model": "Omni 1.1 Flash",
                    "status": "pending",
                    "scenes": [
                        {"scene_number": 1, "image_prompt": "s1", "video_prompt": "v1"},
                        {"scene_number": 2, "image_prompt": "s2", "video_prompt": "v2"},
                    ],
                }],
            }
            (proj_dir / "project.json").write_text(json.dumps(proj_doc), encoding="utf-8")

            scene2_img_gate = threading.Event()
            vid1_started = threading.Event()
            defer_flags = []

            def fake_img_gen(pid, prod, scene):
                snum = int(scene["scene_number"])
                if snum == 2:
                    scene2_img_gate.wait(timeout=3.0)
                target = img1 if snum == 1 else img2
                target.write_bytes(b"jpgdata")
                return str(target)

            def fake_vid_gen(pid, prod, scene, defer_media=False):
                snum = int(scene["scene_number"])
                defer_flags.append((snum, bool(defer_media)))
                if snum == 1:
                    vid1_started.set()
                    scene2_img_gate.wait(timeout=3.0)
                target = vid1 if snum == 1 else vid2
                target.write_bytes(b"mp4data")
                return str(target)

            def fake_concat(pid, prod):
                final_mp4.write_bytes(b"finalmp4")
                return str(final_mp4.resolve())

            import engine_settings_manager as esm
            runner = vsc.MultiThreadSkillRunner()
            with patch.object(vsc, "PROJECTS_DIR", fake_proj_root), \
                 patch.object(vsc, "append_project_log", lambda *a, **kw: None), \
                 patch.object(esm, "ensure_project_variant_thumbnail_and_inject", return_value={}), \
                 patch.object(runner, "_get_flow_limits", return_value={
                     "flow_api_workers": 4,
                     "upscale_download_workers": 4,
                     "submit_delay_sec": 1.0,
                     "global_submit_stagger_sec": 0.25,
                     "extension_pool_tabs": 4,
                     "parallel_products": 2,
                 }), \
                 patch.object(runner, "_generate_single_scene_image", side_effect=fake_img_gen), \
                 patch.object(runner, "_generate_single_scene_video", side_effect=fake_vid_gen), \
                 patch.object(runner, "_concat_final_video", side_effect=fake_concat):
                res_holder = {}
                t_run = threading.Thread(target=lambda: res_holder.update({"res": runner.run_single_product(proj_id, "p1")}))
                t_run.start()
                self.assertTrue(vid1_started.wait(timeout=2.5), "Scene 1 video must start while Scene 2 image is still running")
                scene2_img_gate.set()
                t_run.join(timeout=5.0)
                prod_out = res_holder["res"]["products"][0]
                self.assertEqual(prod_out["status"], "done")
                self.assertEqual(dict(defer_flags).get(1), True)
                self.assertEqual(dict(defer_flags).get(2), True)
                self.assertTrue(final_mp4.is_file())
                _ = time.time()

    def test_flow_workflow_batch_pipeline_runs_batches_concurrently(self):
        import engine_settings_manager as esm
        import flow_workflow_engine as fwe

        with tempfile.TemporaryDirectory() as tmp:
            wf_out_root = Path(tmp) / "wf_outs"
            wf_out_root.mkdir(parents=True, exist_ok=True)
            doc = {
                "id": "wf_batch_test",
                "workflow": {
                    "name": "Batch Parallel Test",
                    "settings": {"parallel": True, "stop_on_error": True},
                    "nodes": [{
                        "node_id": "n1",
                        "node_type": "generate",
                        "node_name": "Gen Video",
                        "config": {},
                    }],
                    "edges": [],
                    "timeline": [],
                },
            }
            barrier = threading.Barrier(2, timeout=2.5)
            seen_dirs = []
            seen_lock = threading.Lock()

            def fake_exec_node(nd, nodes_by_id, edges, node_outputs, wf_out_dir, profile_name=""):
                barrier.wait()
                out_file = Path(wf_out_dir) / "out.mp4"
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_bytes(b"mp4")
                with seen_lock:
                    seen_dirs.append(str(wf_out_dir))
                return {"ok": True, "primary_path": str(out_file)}

            with patch.object(fwe, "WORKFLOW_OUTPUTS_DIR", str(wf_out_root)), \
                 patch.object(fwe, "_WORKFLOW_RUN_STATE", {}), \
                 patch.object(fwe, "save_workflow_document", MagicMock()), \
                 patch.object(fwe, "execute_single_node_in_context", side_effect=fake_exec_node), \
                 patch.object(esm, "get_effective_flow_concurrency", return_value={"parallel_products": 4, "global_submit_stagger_sec": 0.25, "flow_api_workers": 4}):
                res = fwe.run_workflow_batch_pipeline(
                    doc,
                    batch_config={"enabled": True, "mode": "variations", "batch_count": 2, "max_workers": 2, "auto_export_mp4": False},
                )

            self.assertEqual(res["status"], "done")
            self.assertEqual(res["batch_completed"], 2)
            self.assertEqual(len(set(seen_dirs)), 2)

    def test_flow_error_classification_and_global_cooldown(self):
        import flow_workflow_engine as fwe

        self.assertEqual(gvt.classify_flow_error("HTTP 400 PUBLIC_ERROR_MINOR_UPLOAD"), "content_policy")
        self.assertEqual(gvt.classify_flow_error("INVALID_ARGUMENT: bad image"), "content_policy")
        self.assertEqual(gvt.classify_flow_error("HTTP 403 PUBLIC_ERROR_USER_QUOTA_REACHED"), "account_quota")
        self.assertEqual(gvt.classify_flow_error("PUBLIC_ERROR_CREDITS_EXHAUSTED"), "account_quota")
        self.assertEqual(gvt.classify_flow_error("HTTP 401 UNAUTHENTICATED"), "account_auth")
        self.assertEqual(gvt.classify_flow_error("HTTP 429 PUBLIC_ERROR_HIGH_TRAFFIC"), "rate_limit")
        self.assertEqual(gvt.classify_flow_error("HTTP 403 PUBLIC_ERROR_UNUSUAL_ACTIVITY"), "captcha_score")
        self.assertEqual(gvt.classify_flow_error("HTTP 502 Bad Gateway"), "transient")

        self.assertTrue(gvt.is_non_retryable_error("HTTP 403 PUBLIC_ERROR_USER_QUOTA_REACHED"))
        self.assertTrue(gvt.should_stop_all_accounts("PUBLIC_ERROR_UNSAFE_GENERATION"))
        self.assertFalse(gvt.should_stop_all_accounts("PUBLIC_ERROR_USER_QUOTA_REACHED"))
        self.assertFalse(fwe._is_flow_account_error_wf("PUBLIC_ERROR_MINOR_UPLOAD"))
        self.assertTrue(fwe._is_flow_account_error_wf("PUBLIC_ERROR_USER_QUOTA_REACHED"))

        try:
            gvt.mark_flow_account_cooldown("_test_acc_1", "account_quota", "PUBLIC_ERROR_USER_QUOTA_REACHED")
            in_cd, rem, kind = gvt.is_flow_account_in_cooldown("_test_acc_1")
            self.assertTrue(in_cd)
            self.assertEqual(kind, "account_quota")
            self.assertGreater(rem, 100.0)

            ordered = gvt.sort_flow_candidates_by_health(["_test_acc_1", "_test_acc_2", "_test_acc_3"], lambda x: x)
            self.assertEqual(ordered, ["_test_acc_2", "_test_acc_3", "_test_acc_1"])

            gvt.clear_flow_account_cooldown("_test_acc_1")
            ordered_restored = gvt.sort_flow_candidates_by_health(["_test_acc_1", "_test_acc_2"], lambda x: x)
            self.assertEqual(ordered_restored, ["_test_acc_1", "_test_acc_2"])
        finally:
            gvt.clear_flow_account_cooldown("_test_acc_1")

    def test_captcha_bridge_reset_storm_debounce_and_lock_reset(self):
        bridge = gvt.CaptchaBridge(log_func=lambda _m: None)
        bridge._last_reset_at = 0.0
        bridge.MIN_RESET_COOLDOWN_SEC = 20.0
        reset_calls = []

        def fake_reset(kind="hard_reset", timeout=35):
            reset_calls.append((kind, timeout))
            return True

        with patch.object(bridge, "reset_session", side_effect=fake_reset):
            t1 = threading.Thread(target=bridge.notify_recaptcha_score_dead)
            t2 = threading.Thread(target=bridge.notify_recaptcha_score_dead)
            t1.start()
            t2.start()
            t1.join(timeout=3.0)
            t2.join(timeout=3.0)
            bridge.notify_failure()

        self.assertEqual(len(reset_calls), 1)
        self.assertEqual(reset_calls[0][0], "hard_reset")
        self.assertIsNone(bridge._pending_reset)

    def test_cdn_download_micro_retry_recovers_on_transient_502(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_img = Path(tmp) / "out.png"
            job = gvt.VideoJob(
                id="cdn_retry_img",
                prompt="studio shot",
                mode="text-to-video",
                model="Nano Banana 2",
                resolution="1K",
                aspect_ratio="9:16",
                local_path=str(out_img),
                flow_request_only=True,
                google_profile_name="prof_cdn_test",
            )
            ogi_calls = []
            cdn_calls = []

            class FakeClient:
                def __init__(self, *args, **kwargs):
                    pass

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    return False

                async def get(self, url, **kwargs):
                    if "batchexecute" in url or "flow.google.com/project" in url:
                        html = '<script>window.WIZ_global_data={"SNlM0e":"at_tok","cfb2h":"bl_1","FdrFJe":"fs_1"};</script>'
                        return _DummyResponse(200, html, html.encode("utf-8"))
                    cdn_calls.append(url)
                    if len(cdn_calls) == 1:
                        return _DummyResponse(502, "Bad Gateway", b"bad gateway")
                    png = b"\x89PNG\r\n\x1a\n" + (b"x" * 1024)
                    return _DummyResponse(200, "", png)

                async def post(self, url, **kwargs):
                    if "rpcids=ogiZ0b" in url:
                        ogi_calls.append(url)
                        wrb = ')]}\'\n\n123\n[["wrb.fr","ogiZ0b","[[[\\"11111111-1111-1111-1111-111111111111\\",null,null,null,null,\\"https://flow-content.google/image/sample_test\\"]]]",null,null,null,"generic"]]\n'
                        return _DummyResponse(200, wrb, wrb.encode("utf-8"))
                    wrb = ')]}\'\n\n50\n[["wrb.fr","as29s","[]",null,null,null,"generic"]]\n'
                    return _DummyResponse(200, wrb, wrb.encode("utf-8"))

            bridge = _DummyBridge()
            bridge.request_recaptcha = lambda _a, timeout=20: "tok_ok_" + ("a" * 90)

            async def _fast_sleep(_sec):
                return None

            with patch.object(gvt, "_GoogleApiClient", return_value=FakeClient()), \
                 patch.object(gvt, "_load_flow_cookie_header", return_value="SID=1; HSID=2"), \
                 patch.object(gvt, "_resolve_flow_shared_dir", return_value=tmp), \
                 patch.object(gvt, "_get_effective_ua_and_sec_ch_ua", return_value=("UA", "")), \
                 patch("grok_video_tool.asyncio.sleep", side_effect=_fast_sleep):
                ok = asyncio.run(
                    gvt._run_veo_flow_batchexecute(
                        job=job,
                        project_id="proj-cdn-test",
                        auth_cookie="SID=1; HSID=2",
                        captcha_bridge=bridge,
                        _log=lambda _m: None,
                        progress=None,
                        out_file=out_img,
                    )
                )

            self.assertTrue(ok, msg=f"Unexpected job.error={job.error}")
            self.assertEqual(len(ogi_calls), 1)
            self.assertEqual(len(cdn_calls), 2)
            self.assertTrue(out_img.is_file())
            self.assertTrue(out_img.read_bytes().startswith(b"\x89PNG"))

    def test_veo_skill_failover_stops_on_policy_and_cooldowns_quota(self):
        import veo_skill_cli as vsc

        class _Acc:
            def __init__(self, name, proxy=""):
                self.name = name
                self.active = True
                self.proxy_url = proxy or gvt.DEFAULT_PROJECT_ID
                self.api_key = "flow_cookie:SID=1"

        runner = vsc.MultiThreadSkillRunner()
        acc1 = _Acc("acc_policy_1")
        acc2 = _Acc("acc_policy_2")

        with tempfile.TemporaryDirectory() as tmp:
            out_ok = Path(tmp) / "ok.png"
            out_ok.write_bytes(b"\x89PNG\r\n\x1a\n" + (b"z" * 600))

            # 1) content_policy must stop after 1st account without touching acc2
            tried_policy = []

            async def fake_run_policy(job, bearer, pid, bridge, log=None, progress=None):
                tried_policy.append(job.account_name)
                job.error = "Google Flow từ chối tạo ảnh: PUBLIC_ERROR_UNSAFE_GENERATION"
                return False

            with patch.object(runner, "flow_account_candidates", return_value=[(acc1, "t1", gvt.DEFAULT_PROJECT_ID), (acc2, "t2", gvt.DEFAULT_PROJECT_ID)]), \
                 patch.object(runner, "_throttle_flow_submit"), \
                 patch.object(runner, "ensure_captcha_bridge", return_value=_DummyBridge()), \
                 patch.object(runner.gvt, "run_veo_flow", side_effect=fake_run_policy), \
                 patch.object(runner.gvt, "_google_profile_name_for_account", side_effect=lambda a, allow_unresolved=True: a.name):
                with self.assertRaises(RuntimeError):
                    runner._run_veo_flow_with_failover(
                        lambda a, p: gvt.VideoJob(id="j1", prompt="p", account_name=a.name, google_profile_name=p),
                        "",
                        lambda _m: None,
                    )
            self.assertEqual(tried_policy, ["acc_policy_1"])

            # 2) PUBLIC_ERROR_USER_QUOTA_REACHED must cooldown acc1 and immediately failover to acc2
            tried_quota = []

            async def fake_run_quota(job, bearer, pid, bridge, log=None, progress=None):
                tried_quota.append(job.account_name)
                if job.account_name == "acc_policy_1":
                    job.error = "HTTP 403 PUBLIC_ERROR_USER_QUOTA_REACHED"
                    return False
                job.local_path = str(out_ok)
                return True

            try:
                with patch.object(runner, "flow_account_candidates", return_value=[(acc1, "t1", gvt.DEFAULT_PROJECT_ID), (acc2, "t2", gvt.DEFAULT_PROJECT_ID)]), \
                     patch.object(runner, "_throttle_flow_submit"), \
                     patch.object(runner, "ensure_captcha_bridge", return_value=_DummyBridge()), \
                     patch.object(runner.gvt, "run_veo_flow", side_effect=fake_run_quota), \
                     patch.object(runner.gvt, "_google_profile_name_for_account", side_effect=lambda a, allow_unresolved=True: a.name):
                    res_path = runner._run_veo_flow_with_failover(
                        lambda a, p: gvt.VideoJob(id="j2", prompt="p", account_name=a.name, google_profile_name=p),
                        "",
                        lambda _m: None,
                    )
                self.assertEqual(tried_quota, ["acc_policy_1", "acc_policy_2"])
                self.assertTrue(Path(res_path).is_file())
                in_cd, _, kind = gvt.is_flow_account_in_cooldown("acc_policy_1")
                self.assertTrue(in_cd)
                self.assertEqual(kind, "account_quota")
            finally:
                gvt.clear_flow_account_cooldown("acc_policy_1")
                gvt.clear_flow_account_cooldown("acc_policy_2")

    def test_extract_flow_as29s_error_nested_slots_and_bare_codes(self):
        # Nested [5][8]
        p_58 = [None, None, None, None, None, [None, None, None, None, None, None, None, None, [4, "PUBLIC_ERROR_PROMINENT_PEOPLE_FILTER_FAILED"]]]
        failed, code, detail = gvt.extract_flow_as29s_error(p_58)
        self.assertTrue(failed)
        self.assertEqual(code, 4)
        self.assertIn("PUBLIC_ERROR_PROMINENT_PEOPLE_FILTER_FAILED", detail)
        self.assertEqual(gvt.classify_flow_error(f"Google Flow render FAILED (code={code}): {detail}"), "content_policy")

        # Deep nested [0][0][5][8]
        p_0058 = [[[None, None, None, None, None, [None, None, None, None, None, None, None, None, [7, "PUBLIC_ERROR_AUDIO_FILTERED"]]]]]
        failed2, code2, detail2 = gvt.extract_flow_as29s_error(p_0058)
        self.assertTrue(failed2)
        self.assertEqual(code2, 7)
        self.assertIn("PUBLIC_ERROR_AUDIO_FILTERED", detail2)
        self.assertEqual(gvt.classify_content_rejection_subtype(detail2), "audio_filtered")

        # Bare code=4 at [0][0][3] with no [5][7]
        failed3, code3, detail3 = gvt.extract_flow_as29s_error([[[None, None, None, 4]]])
        self.assertTrue(failed3)
        self.assertEqual(code3, 4)
        self.assertEqual(detail3, "")
        self.assertEqual(gvt.classify_flow_error(f"Google Flow render FAILED (code={code3}): {detail3}"), "content_policy")

        # Normal running status=1 must not fail
        failed_run, code_run, _ = gvt.extract_flow_as29s_error([[[None, None, None, 1]]])
        self.assertFalse(failed_run)
        self.assertEqual(code_run, 1)

    def test_classify_flow_error_precedence_with_localized_prefixes(self):
        # Generic localized prefixes must NOT shadow account/rate/captcha classes
        self.assertEqual(gvt.classify_flow_error("Google Flow từ chối tạo video: HTTP 429 Too Many Requests"), "rate_limit")
        self.assertEqual(gvt.classify_flow_error("Google Flow từ chối tạo ảnh: PUBLIC_ERROR_UNUSUAL_ACTIVITY"), "captcha_score")
        self.assertEqual(gvt.classify_flow_error("Google Flow từ chối tạo video: PUBLIC_ERROR_USER_QUOTA_REACHED"), "account_quota")
        self.assertEqual(gvt.classify_flow_error("Google Flow từ chối tạo video: HTTP 401 UNAUTHENTICATED"), "account_auth")
        # Genuine backend internal error on as29s remains transient
        self.assertEqual(gvt.classify_flow_error("Google Flow render FAILED (code=4): PUBLIC_ERROR_INTERNAL"), "transient")
        # Policy / empty render code / Vietnamese invalid content errors are content_policy
        self.assertEqual(gvt.classify_flow_error("Google Flow render FAILED (code=4): "), "content_policy")
        self.assertEqual(gvt.classify_flow_error("Lỗi nội dung không hợp lệ hoặc vướng bộ lọc"), "content_policy")

    def test_sanitize_prompt_and_describe_flow_error_vi(self):
        orig = "A young girl holding a knife with red blood and wearing a bikini"
        safe, changed = gvt.sanitize_prompt_for_flow_policy(orig, "unsafe_generation")
        self.assertTrue(changed)
        self.assertNotIn("knife", safe.lower())
        self.assertNotIn("blood", safe.lower())
        self.assertNotIn("bikini", safe.lower())
        self.assertNotIn("girl", safe.lower())
        # Idempotent once commercial safety suffix is present
        safe2, changed2 = gvt.sanitize_prompt_for_flow_policy(safe, "unsafe_generation")
        self.assertFalse(changed2)
        self.assertEqual(safe2, safe)

        vi_msg = gvt.describe_flow_error_vi("Google Flow render FAILED (code=4): PUBLIC_ERROR_PROMINENT_PEOPLE_FILTER_FAILED")
        self.assertIn("người nổi tiếng", vi_msg)
        self.assertIn("PUBLIC_ERROR_PROMINENT_PEOPLE_FILTER_FAILED", vi_msg)
        # Idempotent error formatting
        self.assertEqual(gvt.describe_flow_error_vi(vi_msg), vi_msg)

    def test_run_veo_flow_content_policy_single_mitigation_and_upload_stop(self):
        import asyncio

        # A) First attempt blocked -> second sanitized attempt succeeds on same account
        calls_ok = []

        async def _fake_attempt_recover(job, bearer, pid, bridge, log, progress):
            calls_ok.append(job.prompt)
            if len(calls_ok) == 1:
                job.error = "Google Flow render FAILED (code=4): PUBLIC_ERROR_UNSAFE_GENERATION"
                return False
            return True

        job_ok = gvt.VideoJob(
            id="j_rec",
            prompt="A girl slicing mango with a knife",
            account_name="acc_pol_test",
            google_profile_name="acc_pol_test",
            max_retries=3,
        )
        with patch.object(gvt, "_run_veo_flow_single_attempt", side_effect=_fake_attempt_recover):
            ok = asyncio.run(gvt.run_veo_flow(job_ok, "tok", gvt.DEFAULT_PROJECT_ID, None, None, None))
        self.assertTrue(ok)
        self.assertEqual(len(calls_ok), 2)
        self.assertTrue(getattr(job_ok, "_policy_sanitized_retried", False))
        self.assertNotIn("knife", job_ok.prompt.lower())

        # B) Persistent content_policy stops immediately after 1 sanitized retry even when max_retries=4
        calls_fail = []

        async def _fake_attempt_fail(job, bearer, pid, bridge, log, progress):
            calls_fail.append(job.prompt)
            job.error = "Google Flow render FAILED (code=4): PUBLIC_ERROR_UNSAFE_GENERATION"
            return False

        job_fail = gvt.VideoJob(
            id="j_fail",
            prompt="A girl on a beach",
            account_name="acc_pol_test",
            google_profile_name="acc_pol_test",
            max_retries=4,
        )
        with patch.object(gvt, "_run_veo_flow_single_attempt", side_effect=_fake_attempt_fail):
            ok_f = asyncio.run(gvt.run_veo_flow(job_fail, "tok", gvt.DEFAULT_PROJECT_ID, None, None, None))
        self.assertFalse(ok_f)
        self.assertEqual(len(calls_fail), 2)
        self.assertIn("PUBLIC_ERROR_UNSAFE_GENERATION", job_fail.error)
        self.assertIn("Gợi ý:", job_fail.error)

        # C) Image upload rejection (maseQ MINOR_UPLOAD) never retries at all
        calls_up = []

        async def _fake_attempt_upload(job, bearer, pid, bridge, log, progress):
            calls_up.append(job.prompt)
            job.error = "Lỗi tải ảnh lên Google Flow (maseQ): HTTP 400 PUBLIC_ERROR_MINOR_UPLOAD"
            return False

        job_up = gvt.VideoJob(
            id="j_up",
            prompt="Portrait video",
            account_name="acc_pol_test",
            google_profile_name="acc_pol_test",
            max_retries=4,
        )
        with patch.object(gvt, "_run_veo_flow_single_attempt", side_effect=_fake_attempt_upload):
            ok_u = asyncio.run(gvt.run_veo_flow(job_up, "tok", gvt.DEFAULT_PROJECT_ID, None, None, None))
        self.assertFalse(ok_u)
        self.assertEqual(len(calls_up), 1)
        self.assertIn("PUBLIC_ERROR_MINOR_UPLOAD", job_up.error)
        self.assertIn("trẻ vị thành niên", job_up.error)

    def test_server_load_valid_index_html_heals_truncated_copy(self):
        import server

        real_html = (ROOT_DIR / "static" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("truncated for diff preview", real_html)
        self.assertTrue(real_html.strip().endswith("</html>"))

        anchor = "          if (rCook && rCook.ok) {"
        pos = real_html.rfind(anchor)
        self.assertGreater(pos, 0)

        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)
            recovery_src = ROOT_DIR / "static" / "_index_tail_recovery.html"
            self.assertTrue(recovery_src.is_file())
            (tmp_dir / "_index_tail_recovery.html").write_bytes(recovery_src.read_bytes())

            broken = real_html[: pos + len(anchor)] + "\r\n...[truncated for diff preview]"
            broken_file = tmp_dir / "index.html"
            broken_file.write_text(broken, encoding="utf-8")

            healed_bytes = server._load_valid_index_html(broken_file)
            healed = healed_bytes.decode("utf-8")
            self.assertNotIn("truncated for diff preview", healed)
            self.assertTrue(healed.strip().endswith("</html>"))
            self.assertIn("</script>", healed)
            self.assertIn("/static/transform_studio.js", healed)
            self.assertEqual(healed.count("const rCook = await apiPost(\"/api/cooking/run\""), 1)
            self.assertEqual(healed_bytes, broken_file.read_bytes())

            # Also verify truncation at tpl === "004" (line ~9067, BEFORE rCook) heals cleanly without illegal return
            early_cut = "onSelectFashionProjectSlug(projectId);"
            early_pos = real_html.rfind(early_cut)
            self.assertGreater(early_pos, 0)
            broken2 = real_html[: early_pos + len(early_cut)] + "\r\n          }\r\n        }, 120);\r\n        return;\r\n      }\r\n... [truncated for diff preview]"
            broken_file2 = tmp_dir / "index_early.html"
            broken_file2.write_text(broken2, encoding="utf-8")
            healed2 = server._load_valid_index_html(broken_file2).decode("utf-8")
            self.assertNotIn("truncated for diff preview", healed2)
            self.assertEqual(healed2.count("const rCook = await apiPost(\"/api/cooking/run\""), 1)
            self.assertIn("isTransformStudioTemplate(tpl, proj)", healed2)
            self.assertTrue(healed2.strip().endswith("</html>"))

    def test_transform_engine_queues_unlimited_and_runs_parallel_slots(self):
        import base64 as _b64
        import io as _io
        import time
        from PIL import Image as _PILImage

        buf = _io.BytesIO()
        _PILImage.new("RGB", (64, 64), (120, 40, 200)).save(buf, format="PNG")
        data_uri = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            jobs_dir = ws / "projects"
            jobs_dir.mkdir(parents=True)

            active_lock = threading.Lock()
            max_parallel_seen = [0]
            curr_parallel = [0]
            first_two_barrier = threading.Barrier(2, timeout=3.0)
            ran_order = []

            def _fake_run(folder, state, runner=None):
                with active_lock:
                    curr_parallel[0] += 1
                    max_parallel_seen[0] = max(max_parallel_seen[0], curr_parallel[0])
                    idx = len(ran_order)
                    ran_order.append(state["id"])
                try:
                    if idx < 2:
                        first_two_barrier.wait()
                    else:
                        time.sleep(0.05)
                    final_mp4 = folder / "video_final.mp4"
                    final_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 512)
                    state["final"] = str(final_mp4)
                    state["status"] = "done"
                    state["message"] = "Xong"
                    te.save(folder, state)
                finally:
                    with active_lock:
                        curr_parallel[0] -= 1

            with patch.object(te, "JOBS", jobs_dir), \
                 patch.object(te, "ROOT", ws), \
                 patch.object(te, "_max_transform_slots", return_value=2), \
                 patch.object(te, "run", side_effect=_fake_run), \
                 patch.object(te.shutil, "which", return_value="ffmpeg"):
                with te._QUEUE_COND:
                    te._ACTIVE_JOBS.clear()
                    te._STOPPED_JOBS.clear()

                responses = []
                for idx in range(3):
                    res = te.start({
                        "template_code": "006",
                        "preset": "farm",
                        "image_provider": "banana",
                        "video_model": "Omni 1.1 Flash",
                        "music": False,
                        "product_label": f"vay-mau-{idx + 1}.jpg",
                        "product_upload": data_uri,
                    })
                    responses.append(res)

                self.assertEqual(len(responses), 3)
                for idx, res in enumerate(responses):
                    self.assertTrue(res["ok"])
                    self.assertIn("project", res)
                    self.assertEqual(res["project"]["id"], res["id"])
                    self.assertIn(f"vay-mau-{idx + 1}", res["project"]["name"])

                deadline = time.time() + 5.0
                while time.time() < deadline:
                    statuses = [te.status(r["id"]).get("status") for r in responses]
                    if all(s == "done" for s in statuses):
                        break
                    time.sleep(0.05)

                self.assertEqual([te.status(r["id"]).get("status") for r in responses], ["done", "done", "done"])
                self.assertEqual(max_parallel_seen[0], 2, "Should run strictly up to max_slots=2 concurrently and drain queued job 3")
                listed = te.list_jobs(limit=10)
                self.assertTrue(listed["ok"])
                self.assertEqual(len(listed["jobs"]), 3)

    def test_transform_engine_stop_resume_and_engine_settings_monitor(self):
        import base64 as _b64
        import io as _io
        import time
        import engine_settings_manager as esm
        from PIL import Image as _PILImage

        buf = _io.BytesIO()
        _PILImage.new("RGB", (64, 64), (20, 140, 180)).save(buf, format="PNG")
        data_uri = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            jobs_dir = ws / "projects"
            jobs_dir.mkdir(parents=True)
            entered_run = threading.Event()
            resume_saw_flag = [None]

            def _fake_run_pausable(folder, state, runner=None):
                if state.get("resume_existing"):
                    resume_saw_flag[0] = True
                    final_mp4 = folder / "video_final.mp4"
                    final_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"1" * 512)
                    state["final"] = str(final_mp4)
                    state.pop("resume_existing", None)
                    state.update(status="done", message="Đã chạy nốt xong")
                    te.save(folder, state)
                    return
                entered_run.set()
                try:
                    for _ in range(80):
                        if te._is_stopped(state["id"]):
                            raise te.JobStoppedError("Đã dừng theo yêu cầu người dùng.")
                        time.sleep(0.05)
                except te.JobStoppedError as exc:
                    state.pop("worker_pid", None)
                    state.update(status="stopped", message=str(exc))
                    te.save(folder, state)

            with patch.object(te, "JOBS", jobs_dir), \
                 patch.object(te, "ROOT", ws), \
                 patch.object(esm, "PROJECTS_DIR", str(jobs_dir)), \
                 patch.object(esm, "FASHION_STUDIO_PROJECTS_DIR", str(ws / "fashion_none")), \
                 patch.object(te, "_max_transform_slots", return_value=2), \
                 patch.object(te, "run", side_effect=_fake_run_pausable), \
                 patch.object(te.shutil, "which", return_value="ffmpeg"):
                with te._QUEUE_COND:
                    te._ACTIVE_JOBS.clear()
                    te._STOPPED_JOBS.clear()

                started = te.start({
                    "template_code": "006",
                    "preset": "farm",
                    "image_provider": "banana",
                    "video_model": "Omni 1.1 Flash",
                    "music": False,
                    "product_upload": data_uri,
                })
                pid = started["id"]
                self.assertTrue(entered_run.wait(timeout=3.0))

                running_list = esm.list_all_running_pipelines()
                self.assertTrue(any(r.get("pid") == pid and r.get("pipeline_kind") == "fashion_transformation" for r in running_list))

                stop_res = esm.stop_running_pipeline(pid)
                self.assertTrue(stop_res.get("ok"))

                deadline = time.time() + 3.0
                while time.time() < deadline:
                    if te.status(pid).get("status") == "stopped":
                        break
                    time.sleep(0.05)
                self.assertEqual(te.status(pid).get("status"), "stopped")

                resumed = te.resume(pid)
                self.assertTrue(resumed.get("ok"))
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    if te.status(pid).get("status") == "done":
                        break
                    time.sleep(0.05)
                self.assertEqual(te.status(pid).get("status"), "done")
                self.assertTrue(resume_saw_flag[0])

    def test_sync_web_ui_concurrent_atomic_write(self):
        import sync_web_ui_state as sws

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            proj_dir = ws / "projects"
            fv_dir = ws / "final_videos"
            proj_dir.mkdir(parents=True)
            fv_dir.mkdir(parents=True)
            for idx in range(2):
                pid = f"transform_{idx:016x}"
                d = proj_dir / pid
                d.mkdir(parents=True)
                state = {
                    "id": pid,
                    "status": "done",
                    "message": "OK",
                    "template_code": "006",
                    "template_name": "Biến hình thời trang",
                    "preset": "farm",
                    "preset_title": "Làm nông",
                    "product_label": f"sp-{idx}",
                    "image_provider": "banana",
                    "video_model": "Omni 1.1 Flash",
                    "scenes": [],
                    "refs": {},
                }
                (d / "video_final.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 64)
                te.save(d, state)

            errors = []

            def _sync_worker():
                try:
                    sws.sync_web_ui(force=True)
                except Exception as exc:
                    errors.append(exc)

            with patch.object(sws, "WORKSPACE", str(ws)), \
                 patch.object(sws, "PROJECTS_DIR", str(proj_dir)), \
                 patch.object(sws, "FINAL_VIDEOS_DIR", str(fv_dir)), \
                 patch.object(sws, "ALL_PIDS", []):
                threads = [threading.Thread(target=_sync_worker) for _ in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=5.0)

            self.assertEqual(errors, [])
            index_data = json.loads((proj_dir / "projects_index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(index_data), 2)


if __name__ == "__main__":
    unittest.main()
