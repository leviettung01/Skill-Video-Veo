# -*- coding: utf-8 -*-
"""
Thin Stdio-to-HTTP MCP Proxy for SkillAutoVeo.
Zero business logic or source code dependencies — safe to ship alongside compiled binaries
(or invoke via `SkillAutoVeo.exe --mcp-stdio`) for Claude Desktop, Codex, Gemini CLI, and Antigravity.

Usage:
  SKILL_MCP_URL=http://127.0.0.1:8456/mcp SKILL_MCP_TOKEN=skv_mcp_... python mcp_stdio_proxy.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def run_stdio_proxy(url: str = "", token: str = "") -> int:
    endpoint = (url or os.environ.get("SKILL_MCP_URL") or "http://127.0.0.1:8456/mcp").strip()
    bearer = (token or os.environ.get("SKILL_MCP_TOKEN") or "").strip()

    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        req_id = msg.get("id") if isinstance(msg, dict) else None
        is_notification = isinstance(msg, dict) and ("id" not in msg or msg.get("id") is None) and str(msg.get("method") or "").startswith("notifications/")

        headers = {"Content-Type": "application/json"}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

        try:
            req = urllib.request.Request(endpoint, data=raw.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = resp.read().decode("utf-8", errors="replace").strip()
                if not is_notification and body:
                    sys.stdout.write(body + "\n")
                    sys.stdout.flush()
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace").strip()
            if not is_notification:
                try:
                    parsed = json.loads(err_body)
                    if isinstance(parsed, dict) and "jsonrpc" in parsed:
                        if req_id is not None and parsed.get("id") is None:
                            parsed["id"] = req_id
                        sys.stdout.write(json.dumps(parsed, ensure_ascii=False) + "\n")
                    else:
                        raise ValueError("non-jsonrpc")
                except Exception:
                    sys.stdout.write(json.dumps({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32000, "message": f"SkillAutoVeo MCP HTTP {he.code}"},
                    }, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            if not is_notification:
                sys.stdout.write(json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": f"Không kết nối được SkillAutoVeo Server tại {endpoint} ({exc})"},
                }, ensure_ascii=False) + "\n")
                sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_stdio_proxy())
