# -*- coding: utf-8 -*-
"""Live HTTP integration test between Skill Video Veo CloudAccountClient and standalone skillautoveo-server."""

from __future__ import annotations

import io
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile
from pathlib import Path

import uvicorn

CLIENT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = CLIENT_ROOT / "flow_final_pipeline" / "scripts"
SERVER_ROOT = CLIENT_ROOT.parent / "skillautoveo-server"

for p in (str(SCRIPTS_DIR), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import cloud_account_client as cac
from app.config import ServerSettings
from app.main import create_app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestCloudClientLiveIntegration(unittest.TestCase):
    @unittest.skipUnless(SERVER_ROOT.exists(), "Standalone skillautoveo-server directory not present")
    def test_end_to_end_client_against_live_server(self) -> None:
        with tempfile.TemporaryDirectory() as srv_tmp, tempfile.TemporaryDirectory() as cli_tmp:
            port = _find_free_port()
            srv_root = Path(srv_tmp)
            settings = ServerSettings(
                host="127.0.0.1",
                port=port,
                public_base_url=f"http://127.0.0.1:{port}",
                data_dir=srv_root / "data",
                db_path=srv_root / "data" / "srv.db",
                keys_dir=srv_root / "data" / "keys",
                storage_mode="local",
                local_storage_dir=srv_root / "storage",
                cors_origins=("*",),
                offline_grace_hours=72,
                max_monthly_unbinds=2,
                presigned_ttl_seconds=300,
                admin_email="admin@live.local",
                admin_password="AdminLiveTestPassword!",
                r2_account_id="",
                r2_access_key_id="",
                r2_secret_access_key="",
                r2_bucket="test",
            )
            app = create_app(settings)
            config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
            server = uvicorn.Server(config)
            th = threading.Thread(target=server.run, daemon=True)
            th.start()
            try:
                base_url = f"http://127.0.0.1:{port}"
                for _ in range(40):
                    try:
                        with urllib.request.urlopen(f"{base_url}/api/v1/health", timeout=1.0) as r:
                            if r.status == 200:
                                break
                    except Exception:
                        time.sleep(0.1)

                cli_ws = Path(cli_tmp) / "ws"
                (cli_ws / "Template").mkdir(parents=True, exist_ok=True)
                client = cac.CloudAccountClient(
                    data_dir=Path(cli_tmp) / "cloud_data",
                    ws_dir=cli_ws,
                    default_server_url=base_url,
                )

                # 1. Client registers -> pending -> login blocked
                reg = client.register("buyer@live.vn", "pass12345", "Buyer Demo", "0909123456")
                self.assertTrue(reg["ok"], reg)
                uid = reg["user_id"]
                blocked = client.login("buyer@live.vn", "pass12345")
                self.assertFalse(blocked["ok"])
                self.assertEqual(blocked["error_code"], "ACCOUNT_PENDING_APPROVAL")

                # 2. Admin approves 30 days & publishes 1 template zip + 1 release zip
                adm_login = app.state.service.admin_login("admin@live.local", "AdminLiveTestPassword!")
                app.state.service.admin_activate_user("admin:test", uid, days=30, plan_tier="pro", max_devices=1)

                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    zf.writestr("template_config.json", '{"code": "099", "name": "OTA Sample"}')
                meta_up = app.state.storage.put_bytes("templates/tpl_099.zip", zip_buf.getvalue())
                app.state.service.admin_upsert_template(
                    "admin:test",
                    {
                        "id": "tpl_099",
                        "pack_id": "pack_core",
                        "kind": "video_template",
                        "title": "OTA Sample #099",
                        "access_type": "paid_addon",
                        "price_vnd": 199000,
                        "meta_storage_key": meta_up["storage_key"],
                        "meta_sha256": meta_up["sha256"],
                        "meta_size_bytes": meta_up["size_bytes"],
                    },
                )

                rel_up = app.state.storage.put_bytes("releases/patch_6_2_5.zip", b"PATCH_ZIP_DATA")
                app.state.service.admin_publish_release(
                    "admin:test",
                    {
                        "version": "6.2.5",
                        "release_type": "patch_zip",
                        "storage_key": rel_up["storage_key"],
                        "sha256": rel_up["sha256"],
                        "size_bytes": rel_up["size_bytes"],
                        "changelog": "Live integration patch",
                    },
                )

                # 3. Client logs in and verifies offline Ed25519 JWT status
                ok_login = client.login("buyer@live.vn", "pass12345")
                self.assertTrue(ok_login["ok"], ok_login)
                st_offline = client.get_status(refresh_online=False)
                self.assertTrue(st_offline["authenticated"])
                self.assertEqual(st_offline["user"]["days_remaining"], 30)

                # 4. Paid addon blocked until Admin grants it
                dl_denied = client.sync_template_from_store("tpl_099", kind="video_template")
                self.assertFalse(dl_denied["ok"])
                self.assertEqual(dl_denied["error_code"], "TEMPLATE_NOT_UNLOCKED")

                app.state.service.admin_grant_template("admin:test", 1, uid, "template", "tpl_099", "Paid 199k")
                dl_ok = client.sync_template_from_store("tpl_099", kind="video_template")
                self.assertTrue(dl_ok["ok"], dl_ok)
                self.assertTrue((cli_ws / "Template" / "tpl_099" / "template_config.json").is_file())

                # 5. Stage app update & unbind device
                upd = client.stage_app_update()
                self.assertTrue(upd["ok"], upd)
                self.assertTrue(Path(upd["staged_path"]).is_file())

                ub = client.unbind_current_device()
                self.assertTrue(ub["ok"], ub)
                self.assertFalse(client.get_status(refresh_online=False)["authenticated"])
            finally:
                server.should_exit = True
                th.join(timeout=3.0)


if __name__ == "__main__":
    unittest.main()
