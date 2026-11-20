import asyncio
import base64
import io
import json
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

import character_library_manager as clm  # noqa: E402
import engine_settings_manager as esm  # noqa: E402
import flow_workflow_engine as fwe  # noqa: E402
import grok_video_tool as gvt  # noqa: E402
import veo_skill_cli as vsc  # noqa: E402


def _make_jpeg_bytes(color=(180, 90, 60), size=(64, 64), min_bytes: int = 0) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    if min_bytes > 0:
        w, h = size
        px = img.load()
        for y in range(h):
            for x in range(w):
                px[x, y] = ((x * 37 + y * 13) % 255, (x * 19 + y * 53) % 255, (x * 71 + y * 29) % 255)
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _make_png_bytes(color=(40, 160, 220, 255), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _write_image(path: Path, raw_bytes: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw_bytes)
    return str(path)


class _FakeHttpResp:
    def __init__(self, payload_obj, status_code: int = 200):
        self._bytes = (
            payload_obj
            if isinstance(payload_obj, (bytes, bytearray))
            else json.dumps(payload_obj).encode("utf-8")
        )
        self.status_code = status_code
        self.text = self._bytes.decode("utf-8", errors="replace")

    def read(self):
        return self._bytes

    def json(self):
        return json.loads(self.text)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestCliproxyUnifiedImages(unittest.TestCase):
    def test_esm_candidates_and_size_normalization(self):
        avail = ["gpt-image-2", "gpt-image-2.5", "gpt-image-1.5", "gemini-3.1-flash-image"]
        self.assertEqual(esm._cliproxy_image_candidates("gemini-3.1-flash-image", avail), [])
        self.assertEqual(
            esm._cliproxy_image_candidates("gpt-image-1", avail)[:3],
            ["gpt-image-2", "gpt-image-2.5", "gpt-image-1.5"],
        )
        self.assertEqual(esm._cliproxy_image_candidates("grok-imagine-image", avail), [])
        self.assertEqual(
            esm._cliproxy_image_candidates("grok-2-image", ["grok-imagine-image", "gpt-image-2"]),
            ["grok-imagine-image"],
        )
        self.assertEqual(esm._normalize_cliproxy_image_size("1152x2048"), "1024x1536")
        self.assertEqual(esm._normalize_cliproxy_image_size("", "16:9"), "1536x1024")
        self.assertEqual(esm._normalize_cliproxy_image_size("", "1:1"), "1024x1024")

    def test_esm_prepare_ref_image_and_normalize_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            big_png = _write_image(t / "big_rgba.png", _make_png_bytes(size=(2200, 2600)))
            raw_b, fname, mime = esm._prepare_cliproxy_ref_image(big_png)
            self.assertEqual(mime, "image/jpeg")
            self.assertTrue(fname.endswith(".jpg"))
            self.assertTrue(raw_b.startswith(b"\xff\xd8"))
            with Image.open(io.BytesIO(raw_b)) as im:
                self.assertLessEqual(max(im.size), 1536)

            out_png = t / "out.png"
            out_png.write_bytes(_make_jpeg_bytes())
            esm._normalize_saved_image_to_jpg(str(out_png))
            self.assertTrue(out_png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

            out_jpg = t / "out.jpg"
            out_jpg.write_bytes(_make_png_bytes())
            esm._normalize_saved_image_to_jpg(str(out_jpg))
            self.assertTrue(out_jpg.read_bytes().startswith(b"\xff\xd8"))

    def test_esm_render_chatgpt_multi_ref_gemini_chat_and_grok(self):
        b64_img = base64.b64encode(_make_jpeg_bytes()).decode("ascii")
        b64_png = base64.b64encode(_make_png_bytes()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            r1 = _write_image(t / "r1.jpg", _make_jpeg_bytes())
            r2 = _write_image(t / "r2.png", _make_png_bytes())

            # 1. Codex ChatGPT multi-ref -> multipart `image[]` to `/v1/images/edits`
            seen_requests = []

            def _fake_open_codex(req, timeout=0):
                seen_requests.append((req.full_url, req.data or b""))
                if req.full_url.endswith("/v1/models"):
                    return _FakeHttpResp({"data": [{"id": "gpt-image-2"}, {"id": "gemini-3.1-flash-image"}]})
                return _FakeHttpResp({"data": [{"b64_json": b64_img}]})

            fake_op = mock.MagicMock()
            fake_op.open.side_effect = _fake_open_codex
            out1 = str(t / "thumb_gpt.jpg")
            with mock.patch.object(esm, "_cliproxy_no_proxy_opener", return_value=fake_op), \
                 mock.patch.object(esm, "get_cliproxy_config", return_value={"url": "http://127.0.0.1:8317", "api_key": "k"}):
                ok, eng, err = esm._render_thumbnail_via_chatgpt(
                    {
                        "prompt": "Lookbook",
                        "model_name": "gpt-image-1",
                        "aspect_ratio": "9:16",
                        "reference_images": [r1, r2],
                    },
                    out1,
                )
            self.assertTrue(ok, err)
            self.assertIn("gpt-image-2 Ref Image Edit", eng)
            self.assertTrue(Path(out1).is_file())
            edit_calls = [(u, d) for (u, d) in seen_requests if u.endswith("/v1/images/edits")]
            self.assertEqual(len(edit_calls), 1)
            self.assertIn(b'name="image[]"', edit_calls[0][1])

            # 2. Gemini CLIProxy -> `/v1/chat/completions` with `image_url` data URIs
            gem_requests = []

            def _fake_open_gem(req, timeout=0):
                gem_requests.append((req.full_url, req.data or b""))
                if req.full_url.endswith("/v1/models"):
                    return _FakeHttpResp({"data": [{"id": "gpt-image-2"}, {"id": "gemini-3.1-flash-image"}]})
                return _FakeHttpResp({
                    "choices": [{
                        "message": {
                            "images": [{"image_url": {"url": f"data:image/png;base64,{b64_png}"}}]
                        }
                    }]
                })

            fake_op2 = mock.MagicMock()
            fake_op2.open.side_effect = _fake_open_gem
            out2 = str(t / "thumb_gem.jpg")
            with mock.patch.object(esm, "_cliproxy_no_proxy_opener", return_value=fake_op2), \
                 mock.patch.object(esm, "get_cliproxy_config", return_value={"url": "http://127.0.0.1:8317", "api_key": "k"}):
                ok, eng, err = esm._render_thumbnail_via_chatgpt(
                    {
                        "prompt": "Fashion portrait",
                        "model_name": "gemini-3.1-flash-image",
                        "aspect_ratio": "9:16",
                        "reference_images": [r1, r2],
                    },
                    out2,
                )
            self.assertTrue(ok, err)
            self.assertIn("cliproxy_gemini", eng)
            self.assertTrue(Path(out2).read_bytes().startswith(b"\xff\xd8"))
            chat_calls = [json.loads(d.decode("utf-8")) for (u, d) in gem_requests if u.endswith("/v1/chat/completions")]
            self.assertEqual(len(chat_calls), 1)
            img_parts = [p for p in chat_calls[0]["messages"][0]["content"] if p.get("type") == "image_url"]
            self.assertEqual(len(img_parts), 2)

            # 3. Grok missing from `/v1/models` -> explicit Vietnamese guidance (NO fallback to gpt-image-2)
            fake_op3 = mock.MagicMock()
            fake_op3.open.side_effect = lambda req, timeout=0: _FakeHttpResp({"data": [{"id": "gpt-image-2"}]})
            with mock.patch.object(esm, "_cliproxy_no_proxy_opener", return_value=fake_op3), \
                 mock.patch.object(esm, "get_cliproxy_config", return_value={"url": "http://127.0.0.1:8317", "api_key": "k"}):
                ok, _, err = esm._render_thumbnail_via_chatgpt(
                    {"prompt": "Grok test", "model_name": "grok-imagine-image", "reference_images": [r1]},
                    str(t / "thumb_grok_fail.jpg"),
                )
            self.assertFalse(ok)
            self.assertIn("chưa có tài khoản xAI Grok", err)

            # 4. Grok present in `/v1/models` -> sends multipart `image[]` to `/v1/images/edits`
            grok_requests = []

            def _fake_open_grok(req, timeout=0):
                grok_requests.append((req.full_url, req.data or b""))
                if req.full_url.endswith("/v1/models"):
                    return _FakeHttpResp({"data": [{"id": "grok-imagine-image"}]})
                return _FakeHttpResp({"data": [{"b64_json": b64_img}]})

            fake_op4 = mock.MagicMock()
            fake_op4.open.side_effect = _fake_open_grok
            out4 = str(t / "thumb_grok_ok.jpg")
            with mock.patch.object(esm, "_cliproxy_no_proxy_opener", return_value=fake_op4), \
                 mock.patch.object(esm, "get_cliproxy_config", return_value={"url": "http://127.0.0.1:8317", "api_key": "k"}):
                ok, eng, err = esm._render_thumbnail_via_chatgpt(
                    {"prompt": "Grok ok", "model_name": "grok-imagine-image", "reference_images": [r1, r2]},
                    out4,
                )
            self.assertTrue(ok, err)
            self.assertIn("grok-imagine-image Ref Image Edit", eng)
            self.assertTrue(any(u.endswith("/v1/images/edits") for u, _ in grok_requests))

    def test_generate_thumbnail_for_variant_routes_cliproxy_providers(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pid = "proj_thumb_test"
            pdir = t / "projects" / pid
            thumbs_root = t / "thumbnails"
            pdir.mkdir(parents=True, exist_ok=True)
            ref1 = _write_image(pdir / "char.jpg", _make_jpeg_bytes())
            ref2 = _write_image(pdir / "prod.jpg", _make_jpeg_bytes())

            captured_metas = []

            big_jpg = _make_jpeg_bytes(size=(256, 256), min_bytes=6000)

            def _fake_render(meta, out_thumb_proj):
                captured_metas.append(dict(meta))
                Path(out_thumb_proj).parent.mkdir(parents=True, exist_ok=True)
                Path(out_thumb_proj).write_bytes(big_jpg)
                return True, f"mock ({meta.get('image_model')})", ""

            fake_meta = {
                "char_v": "nv1_v1",
                "template_id": "fashion_lookbook",
                "template_name": "Lookbook",
                "short_name": "Lookbook",
                "hook_title": "Hook",
                "product_name": "Ao so mi",
                "product_info": "Cotton shirt",
                "price": "199k",
                "char_holding_prod_img": ref1,
                "prod_img_path": ref2,
                "prompt": "Hero thumbnail",
                "reference_images": [ref1, ref2],
                "prod_img_paths": [ref2],
                "headline": "",
                "subject_mode": "auto",
            }
            with mock.patch.object(esm, "PROJECTS_DIR", str(t / "projects")), \
                 mock.patch.object(esm, "THUMBS_ROOT_DIR", str(thumbs_root)), \
                 mock.patch.object(esm, "load_engine_settings", return_value={"thumbnail_provider": "chatgpt"}), \
                 mock.patch.object(esm, "build_thumbnail_prompt_for_variant", return_value=fake_meta), \
                 mock.patch.object(esm, "get_template_by_id", return_value={"id": "fashion_lookbook", "name": "Lookbook", "short_name": "Lookbook"}), \
                 mock.patch.object(esm, "_render_thumbnail_via_chatgpt", side_effect=_fake_render), \
                 mock.patch.object(esm, "_persist_thumbnail_to_project_manifests"):
                for prov in ("chatgpt", "cliproxy_gemini", "grok"):
                    res = esm.generate_thumbnail_for_variant(pid=pid, vkey="nv1_v1", provider=prov, inject_01s=False)
                    self.assertTrue(res["ok"], (prov, res))

            self.assertEqual(
                [m.get("image_model") or m.get("model_name") for m in captured_metas],
                ["gpt-image-2", "gemini-3.1-flash-image", "grok-imagine-image"],
            )
            for m in captured_metas:
                self.assertEqual(m["reference_images"], [ref1, ref2])

    def test_character_library_manager_cliproxy_refs_and_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            char_ref = _write_image(t / "char_ref.jpg", _make_jpeg_bytes())
            prod_ref = _write_image(t / "prod_ref.jpg", _make_jpeg_bytes())
            captured = []

            def _fake_gen(meta, out_path):
                captured.append((dict(meta), out_path))
                _write_image(Path(out_path), _make_jpeg_bytes())
                return True, "cliproxy_gemini (gemini-3.1-flash-image Ref Image Edit)", ""

            fake_state = {"characters": [{"key": "nv1", "name": "Mai", "ref_image_path": char_ref}]}
            with mock.patch.object(clm, "CHARS_DIR", str(t / "chars")), \
                 mock.patch.object(clm, "PROJECTS_DIR", str(t / "projects")), \
                 mock.patch.object(clm, "get_character_library_state", return_value=fake_state), \
                 mock.patch.object(esm, "generate_image_via_cliproxy", side_effect=_fake_gen):
                res = clm.generate_character_or_product_image({
                    "mode": "product_ref",
                    "model": "cliproxy_gemini",
                    "char_key": "nv1",
                    "custom_prompt": "Holding product",
                    "product_image_path": prod_ref,
                    "reference_images": [char_ref],
                })
            self.assertTrue(res["ok"], res)
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0][0]["image_model"], "gemini-3.1-flash-image")
            self.assertEqual(captured[0][0]["reference_images"], [char_ref, prod_ref])

            with mock.patch.object(clm, "CHARS_DIR", str(t / "chars")), \
                 mock.patch.object(clm, "PROJECTS_DIR", str(t / "projects")), \
                 mock.patch.object(clm, "get_character_library_state", return_value={"characters": []}), \
                 mock.patch.object(esm, "generate_image_via_cliproxy", return_value=(False, "", "CLIProxy offline")):
                err_res = clm.generate_character_or_product_image({
                    "mode": "character_sheet",
                    "model": "chatgpt",
                    "char_key": "nv1",
                    "custom_prompt": "Sheet",
                })
            self.assertFalse(err_res["ok"])
            self.assertIn("CLIProxy offline", err_res["error"])

    def test_flow_workflow_engine_cliproxy_image_delegation(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            r1 = _write_image(t / "r1.jpg", _make_jpeg_bytes())
            r2 = _write_image(t / "r2.jpg", _make_jpeg_bytes())
            out_f = str(t / "wf_out.jpg")
            calls = []

            def _fake_gen(meta, out_path):
                calls.append((dict(meta), out_path))
                _write_image(Path(out_path), _make_jpeg_bytes())
                return True, "chatgpt", ""

            with mock.patch.object(esm, "generate_image_via_cliproxy", side_effect=_fake_gen):
                ok, path, err = fwe.call_cliproxy_image_generation(
                    "Studio lookbook", out_f, model_name="gpt-image-1", ratio="9:16", reference_images=[r1, r2]
                )
            self.assertTrue(ok, err)
            self.assertEqual(path, out_f)
            self.assertEqual(calls[0][0]["image_model"], "gpt-image-2")
            self.assertEqual(calls[0][0]["image_size"], "1024x1536")
            self.assertEqual(calls[0][0]["reference_images"], [r1, r2])

    def test_grok_video_tool_unified_image_sync_and_errors(self):
        self.assertEqual(gvt.clean_model_name("gpt-image-1"), "gpt-image-2")
        self.assertEqual(gvt.clean_model_name("dall-e-3"), "gpt-image-2")
        self.assertEqual(gvt.clean_model_name("grok-2-image"), "grok-imagine-image")
        ui_models = gvt.get_ui_image_models()
        self.assertIn("gpt-image-2.5", ui_models)
        self.assertIn("gemini-3.1-flash-image", ui_models)

        err_msg = gvt._cliproxy_format_api_error(
            400,
            '{"error":{"message":"unknown provider for model grok-imagine-video","code":"model_not_found"}}',
            "grok-imagine-video",
        )
        self.assertIn("xAI Grok", err_msg)

        b64_img = base64.b64encode(_make_jpeg_bytes()).decode("ascii")
        b64_png = base64.b64encode(_make_png_bytes()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            r1 = _write_image(t / "r1.jpg", _make_jpeg_bytes())
            r2 = _write_image(t / "r2.jpg", _make_jpeg_bytes())

            # 1. Grok WITH 2 refs preserves refs via multipart `image[]`
            captured_posts = []

            class _FakeClient:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False
                def _handle_post(self, url, kwargs):
                    captured_posts.append((url, kwargs))
                    if url.endswith("/v1/chat/completions"):
                        return _FakeHttpResp({
                            "choices": [{"message": {"images": [{"image_url": {"url": f"data:image/png;base64,{b64_png}"}}]}}]
                        })
                    return _FakeHttpResp({"data": [{"b64_json": b64_img}]})
                def post(self, url, **kwargs):
                    return self._handle_post(url, kwargs)

            class _FakeAsyncClient(_FakeClient):
                async def post(self, url, **kwargs):
                    return self._handle_post(url, kwargs)

            with mock.patch.object(gvt, "make_httpx_client", side_effect=lambda *a, **kw: _FakeClient()), \
                 mock.patch.object(gvt, "make_httpx_async_client", side_effect=lambda *a, **kw: _FakeAsyncClient()):
                kind, val = gvt._cliproxy_run_image_sync(
                    "http://127.0.0.1:8317",
                    "",
                    "grok-imagine-image",
                    "Edit outfit",
                    "1152x2048",
                    ref_paths=[r1, r2],
                )
                self.assertEqual((kind, val), ("base64", b64_img))
                self.assertTrue(captured_posts[-1][0].endswith("/v1/images/edits"))
                self.assertEqual([f[0] for f in captured_posts[-1][1]["files"]], ["image[]", "image[]"])
                self.assertEqual(captured_posts[-1][1]["data"]["size"], "1024x1536")

                # 2. Gemini via `/v1/chat/completions`
                kind2, val2 = gvt._cliproxy_run_image_sync(
                    "http://127.0.0.1:8317",
                    "",
                    "gemini-3.1-flash-image",
                    "Gemini portrait",
                    "1024x1536",
                    aspect="9:16",
                    ref_paths=[r1, r2],
                )
                self.assertEqual((kind2, val2), ("base64", b64_png))
                self.assertTrue(captured_posts[-1][0].endswith("/v1/chat/completions"))

                # 3. GrokClient.generate_image_edit accepts list of refs (completely offline mock)
                client = gvt.GrokClient("http://127.0.0.1:8317", "")
                kind3, val3 = asyncio.run(client.generate_image_edit("Test", "gpt-image-1", "1024x1536", [r1, r2]))
                self.assertEqual((kind3, val3), ("base64", b64_img))
                self.assertEqual(captured_posts[-1][1]["data"]["model"], "gpt-image-2")

    def test_veo_skill_cli_accounts_info_reflects_live_models(self):
        fake_accounts = [
            gvt.Account("Local CLIProxy (Default)", "http://127.0.0.1:8317", "k"),
            gvt.Account("Codex - leviettung05@gmail.com", "http://127.0.0.1:8317", "k"),
        ]
        fake_mgr = mock.MagicMock()
        fake_mgr.accounts = fake_accounts
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(gvt, "AccountManager", return_value=fake_mgr), \
             mock.patch.object(esm, "_cliproxy_fetch_models", return_value=(True, ["gpt-image-2", "gpt-image-2.5", "gemini-3.1-flash-image"], "")):
            runner = vsc.MultiThreadSkillRunner(tmp)
            info = runner.get_accounts_info()

        grok_accs = info["grok_accounts"]
        self.assertEqual(len(grok_accs), 2)
        codex_acc = next(a for a in grok_accs if "Codex" in a["name"])
        self.assertEqual(codex_acc["available_video_models"], ["gpt-image-2", "gpt-image-2.5"])
        default_acc = next(a for a in grok_accs if "Default" in a["name"])
        self.assertIn("gemini-3.1-flash-image", default_acc["available_video_models"])
        self.assertNotIn("grok-imagine-video", default_acc["available_video_models"])


if __name__ == "__main__":
    unittest.main()
