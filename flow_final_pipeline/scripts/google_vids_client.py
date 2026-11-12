# -*- coding: utf-8 -*-
"""
Google Vids Web (`docs.google.com/videos`) Native 1080p Video Generation Client.

Reverse-engineered from Google Vids Espresso / AppsGenAI Web RPC (`vids_mod_tertiary.js`):
  - Zero Playwright / Zero Browser / Zero reCAPTCHA Enterprise!
  - Uses pure Python HTTP (`urllib.request` + `http.cookiejar.CookieJar`) with saved Google account cookies.
  - Completes `OSID` cookie handshake on `docs.google.com/videos/u/0/` (requires `LSID` + `SAPISID` cookies).
  - Extracts `docs-est` (`X-Server-Token`), `espresso_api_key`, `docs-gaopd`, and `docs-tbuu`.
  - Uploads up to 3 reference images (2K PNG/JPG/WebP) via Scotty resumable temporaryblob upload:
    `POST https://docs.google.com/upload/temporaryblob/videos?authuser=0` -> `AYGXpj...` token.
  - Encodes inline `@Hình ảnh1` / `@Hình ảnh2` / `@Hình ảnh3` mentions into true Closure JSPB `Amv` UUID chip AST
    nodes (`O7(new N7, UUID)` -> `Znp`), preventing the plain-text degradation bug from browser multiline paste.
  - Generates native 1080p MP4 (`9:16` enum=6, `16:9` enum=5) with duration `4..15s` on `Omni` (`model=12`) or
    `Veo 3.1` (`model=9`) via `POST https://appsgenaiserver-pa.clients6.google.com/v1/genai/generate`.
"""

import hashlib
import http.cookiejar
import json
import os
import pathlib
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Dict, List, Optional, Tuple, Union

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
WS_DIR = SCRIPTS_DIR.parent.parent
DATA_DIR = WS_DIR / "data"
SESSIONS_CACHE_FILE = DATA_DIR / "google_vids_sessions.json"

ORIGIN = "https://docs.google.com"
DEFAULT_GENAI_HOST = "appsgenaiserver-pa.clients6.google.com"
DEFAULT_UPLOAD_PATH = "/upload/temporaryblob/videos"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)

# Model enum (`erp[1]`) in Google Vids GenAI options
VIDS_MODELS = {
    "omni": 12,
    "veo_3_1": 9,
    "veo3.1": 9,
    "veo": 9,
}

# Combined Aspect Ratio + Resolution enum (`Skv` -> `erp[4]`)
# 1 = 16:9 @ 720p, 2 = 9:16 @ 720p, 5 = 16:9 @ 1080p, 6 = 9:16 @ 1080p
ASPECT_RES_ENUM = {
    ("16:9", "720p"): 1,
    ("9:16", "720p"): 2,
    ("16:9", "1080p"): 5,
    ("9:16", "1080p"): 6,
}

# Request action codes
ACTION_TEXT_TO_VIDEO = 374
ACTION_ANIMATE_IMAGE = 375
ACTION_INGREDIENTS_TO_VIDEO = 376
QUOTA_FEATURE_VEO_VIDS = 1189


def strip_xssi(text: str) -> str:
    """Strip Google's `)]}'` XSSI prefix and leading length/junk before JSON payload."""
    s = (text or "").lstrip()
    if s.startswith(")]}'"):
        nl = s.find("\n")
        s = s[nl + 1 :].lstrip() if nl >= 0 else s[4:].lstrip()
    arr_idx = s.find("[")
    obj_idx = s.find("{")
    if arr_idx >= 0 and (obj_idx < 0 or arr_idx < obj_idx):
        return s[arr_idx:]
    if obj_idx >= 0:
        return s[obj_idx:]
    return s


def sanitize_upload_filename(filename: str) -> str:
    """Ensure HTTP header-safe ASCII filename for `X-Goog-Upload-File-Name`."""
    base = os.path.basename(filename or "image.png")
    stem, ext = os.path.splitext(base)
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_") or "ref_image"
    safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext) or ".png"
    if not safe_ext.startswith("."):
        safe_ext = "." + safe_ext
    return f"{safe_stem[:80]}{safe_ext[:10]}"


def resolve_aspect_res_enum(aspect_ratio: str = "9:16", resolution: str = "1080p") -> int:
    ar = "16:9" if "16:9" in str(aspect_ratio or "") or "land" in str(aspect_ratio or "").lower() else "9:16"
    res = "720p" if "720" in str(resolution or "") else "1080p"
    return ASPECT_RES_ENUM[(ar, res)]


def resolve_model_id(model: Union[str, int] = "omni") -> int:
    if isinstance(model, int) and model in (9, 12):
        return model
    key = str(model or "omni").strip().lower().replace("-", "_").replace(" ", "_")
    return VIDS_MODELS.get(key, 12)


def make_sapisidhash_header(sapisid_map: Dict[str, str], origin: str = ORIGIN, timestamp: Optional[int] = None) -> str:
    """Compute `SAPISIDHASH` + `SAPISID1PHASH` + `SAPISID3PHASH` Authorization header for `docs.google.com`."""
    ts = int(timestamp if timestamp is not None else time.time())
    s0 = (
        sapisid_map.get("SAPISID")
        or sapisid_map.get("__Secure-1PAPISID")
        or sapisid_map.get("__Secure-3PAPISID")
    )
    if not s0:
        raise RuntimeError("Thiếu cookie SAPISID / __Secure-1PAPISID trong phiên đăng nhập Google.")
    s1 = sapisid_map.get("__Secure-1PAPISID") or s0
    s3 = sapisid_map.get("__Secure-3PAPISID") or s0

    def _sha1(secret: str) -> str:
        return hashlib.sha1(f"{ts} {secret} {origin}".encode("utf-8")).hexdigest()

    return f"SAPISIDHASH {ts}_{_sha1(s0)} SAPISID1PHASH {ts}_{_sha1(s1)} SAPISID3PHASH {ts}_{_sha1(s3)}"


def candidate_cookie_dirs(workspace_dir: Optional[pathlib.Path] = None) -> List[pathlib.Path]:
    ws = pathlib.Path(workspace_dir) if workspace_dir else WS_DIR
    return [
        ws / "cookies",
        ws / "data" / "google_flow_grok" / "cookies",
        ws / "flow_final_pipeline" / "cookies",
    ]


def find_cookie_json_for_profile(
    profile_name: str = "",
    workspace_dir: Optional[pathlib.Path] = None,
) -> Optional[pathlib.Path]:
    """Locate the saved cookie JSON file for `profile_name` (or best available account if empty/`auto`)."""
    prof = str(profile_name or "").strip()
    dirs = candidate_cookie_dirs(workspace_dir)
    if prof and prof.lower() != "auto":
        for d in dirs:
            cand = d / f"{prof}.json"
            if cand.is_file() and cand.stat().st_size > 50:
                return cand
        # Case-insensitive fallback
        for d in dirs:
            if d.is_dir():
                for p in sorted(d.glob("*.json")):
                    if p.stem.lower() == prof.lower() and p.stat().st_size > 50:
                        return p
        return None

    # Auto-pick: prefer leviettung04, flow_acc_2, or any cookie file containing SAPISID + LSID
    preferred = ["leviettung04", "flow_acc_2"]
    for pref in preferred:
        found = find_cookie_json_for_profile(pref, workspace_dir=workspace_dir)
        if found:
            return found
    for d in dirs:
        if d.is_dir():
            for p in sorted(d.glob("*.json")):
                if p.stat().st_size > 200:
                    return p
    return None


def inspect_cookie_file(cookie_path: pathlib.Path) -> dict:
    """Inspect a cookie JSON file without making network requests."""
    info = {
        "profile_name": cookie_path.stem,
        "cookie_path": str(cookie_path),
        "has_sapisid": False,
        "has_lsid": False,
        "has_osid": False,
        "has_sid": False,
        "ready_for_vids": False,
    }
    try:
        raw = json.loads(cookie_path.read_text(encoding="utf-8"))
        clist = raw.get("cookies", raw) if isinstance(raw, dict) else raw
        for c in clist or []:
            if not isinstance(c, dict):
                continue
            nm = str(c.get("name") or "")
            val = str(c.get("value") or "")
            dom = str(c.get("domain") or "")
            if not val:
                continue
            if nm in ("SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID"):
                info["has_sapisid"] = True
            elif nm in ("SID", "__Secure-1PSID", "__Secure-3PSID"):
                info["has_sid"] = True
            elif nm == "LSID" and "accounts.google" in dom:
                info["has_lsid"] = True
            elif nm == "OSID" and "docs.google" in dom:
                info["has_osid"] = True
        info["ready_for_vids"] = bool(info["has_sapisid"] and info["has_sid"] and (info["has_lsid"] or info["has_osid"]))
    except Exception as exc:
        info["error"] = str(exc)
    return info


def list_available_vids_accounts(workspace_dir: Optional[pathlib.Path] = None) -> List[dict]:
    """List all saved Google profiles and whether their cookies are ready for Google Vids."""
    seen = {}
    for d in candidate_cookie_dirs(workspace_dir):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            if p.stem in seen or p.stat().st_size < 50:
                continue
            seen[p.stem] = inspect_cookie_file(p)
    return list(seen.values())


def load_cookie_jar(cookie_json_path: pathlib.Path) -> Tuple[urllib.request.OpenerDirector, http.cookiejar.CookieJar, Dict[str, str]]:
    """Build an authenticated `urllib` opener + `CookieJar` + `sapisid_map` from saved cookie JSON."""
    cj = http.cookiejar.CookieJar()
    raw = json.loads(cookie_json_path.read_text(encoding="utf-8"))
    clist = raw.get("cookies", raw) if isinstance(raw, dict) else raw
    now = int(time.time())
    sapisid_map: Dict[str, str] = {}

    for c in clist or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        name = str(c["name"])
        val = str(c.get("value") or "")
        domain = str(c.get("domain") or "")
        if not val or "GRECAPTCHA" in name.upper():
            continue
        if name in ("SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID") and (
            ".google.com" in domain or domain == "google.com" or not domain
        ):
            sapisid_map[name] = val
        exp = c.get("expires")
        exp_int = int(exp) if isinstance(exp, (int, float)) and exp > now else now + 86400 * 30
        ck = http.cookiejar.Cookie(
            version=0,
            name=name,
            value=val,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=bool(domain),
            domain_initial_dot=domain.startswith("."),
            path=str(c.get("path") or "/"),
            path_specified=True,
            secure=bool(c.get("secure", True)),
            expires=exp_int,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        cj.set_cookie(ck)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [
        ("User-Agent", DEFAULT_UA),
        ("Accept-Language", "vi,en-US;q=0.9,en;q=0.8"),
    ]
    return opener, cj, sapisid_map


def build_mentioned_image_entry(img_uuid: str, blob_token: str, display_label: str) -> list:
    """Build Closure JSPB `Gmv` + `Cmv` mentioned-image context entry for `RequestContext[25]`."""
    return [
        [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            [
                img_uuid,
                [
                    None,
                    None,
                    None,
                    None,
                    None,
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
                        None,
                        None,
                        None,
                        None,
                        [None, None, None, blob_token, 1],
                        None,
                        None,
                        None,
                        None,
                        display_label,
                    ],
                ],
            ],
        ]
    ]


def build_chip_ast_node(img_uuid: str, display_label: str) -> list:
    """Build Closure JSPB `Amv` inline `@Hình ảnhX` mention chip node (`O7(new N7, uuid)`)."""
    return [
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        [
            None,
            [None, None, display_label],
            [None, None, None, None, None, None, None, [img_uuid]],
        ],
    ]


def _append_chip_with_safe_spacing(nodes: list, img_uuid: str, label: str, next_text: str = "") -> None:
    if nodes:
        prev = nodes[-1]
        prev_txt = prev[2] if len(prev) > 2 and isinstance(prev[2], str) else None
        prev_is_chip = len(prev) > 7 and prev[7] is not None
        if (prev_txt and not prev_txt[-1].isspace()) or prev_is_chip:
            nodes.append([None, None, " "])
    nodes.append(build_chip_ast_node(img_uuid, label))
    if next_text and not next_text[0].isspace() and next_text[0] not in ".,:;!?)":
        nodes.append([None, None, " "])


def build_amv_ast_from_template(prompt_template: str, tag_map: Dict[str, dict]) -> list:
    """
    Convert a prompt string containing placeholders (`{IMG1}`, `@Hình ảnh1`, `[filename.png]`, etc.)
    into the exact Closure JSPB `Amv` structured prompt AST `[None, None, None, [nodes]]`.
    """
    if not tag_map:
        return [None, None, None, [[[None, None, prompt_template]]]]

    # Sort keys longest-first so `@Hình ảnh1` matches before `Hình ảnh1`
    sorted_keys = sorted([k for k in tag_map.keys() if k], key=len, reverse=True)
    escaped = "|".join(re.escape(k) for k in sorted_keys)
    pattern = re.compile(f"({escaped})")
    parts = pattern.split(prompt_template)

    nodes: list = []
    for idx, part in enumerate(parts):
        if not part:
            continue
        if part in tag_map:
            info = tag_map[part]
            nxt = parts[idx + 1] if idx + 1 < len(parts) else ""
            nxt_plain = "" if nxt in tag_map else nxt
            _append_chip_with_safe_spacing(nodes, info["uuid"], info["label"], next_text=nxt_plain)
            if idx + 1 < len(parts) and parts[idx + 1] in tag_map:
                # Handled by next iteration's prev_is_chip check
                pass
        else:
            nodes.append([None, None, part])

    if not nodes:
        nodes.append([None, None, prompt_template])
    return [None, None, None, [nodes]]


def build_amv_ast_from_segments(segments_spec: List[dict], key_to_chip: Dict[str, dict]) -> list:
    """
    Convert `fashion_motion_control_engine` `segments_spec` (`type="text"` / `type="media"`)
    directly into Closure JSPB `Amv` structured prompt AST `[None, None, None, [nodes]]`.
    """
    nodes: list = []
    total = len(segments_spec or [])
    for idx, seg in enumerate(segments_spec or []):
        stype = seg.get("type")
        if stype == "text":
            txt = str(seg.get("text") or "")
            if txt:
                nodes.append([None, None, txt])
        elif stype == "media":
            akey = str(seg.get("asset_key") or "")
            title = str(seg.get("title") or "")
            chip_info = key_to_chip.get(akey) or key_to_chip.get(title)
            nxt_txt = ""
            if idx + 1 < total and segments_spec[idx + 1].get("type") == "text":
                nxt_txt = str(segments_spec[idx + 1].get("text") or "")
            if chip_info:
                _append_chip_with_safe_spacing(nodes, chip_info["uuid"], chip_info["label"], next_text=nxt_txt)
            elif title:
                nodes.append([None, None, title])
    if not nodes:
        nodes.append([None, None, ""])
    return [None, None, None, [nodes]]


def build_request_context(
    doc_id: str,
    mentioned_context: Optional[list] = None,
    locale: str = "vi",
    tz: str = "Asia/Bangkok",
) -> list:
    req_tag = f"goog_{random.randint(1000000000, 2147483647)}"
    return [
        9,
        None,
        None,
        None,
        req_tag,
        None,
        "0",
        None,
        [
            None,
            None,
            None,
            [[[None, None, None, None, None, None, None, [None, None, [[doc_id, "application/vnd.google-apps.flix", None, None, 1]]]]]],
        ],
        None,
        None,
        [24, 0],
        None,
        locale,
        None,
        None,
        None,
        None,
        None,
        1,
        None,
        None,
        None,
        None,
        None,
        mentioned_context if mentioned_context else None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        tz,
        None,
        None,
        None,
        None,
        None,
        0,
    ]


def find_video_urls_recursive(obj, found: Optional[List[str]] = None) -> List[str]:
    if found is None:
        found = []
    if isinstance(obj, str):
        if obj.startswith("https://") and (
            "contribution-rt.usercontent.google.com" in obj
            or "usercontent.google.com/download" in obj
            or ".mp4" in obj
        ):
            if obj not in found:
                found.append(obj)
    elif isinstance(obj, list):
        for item in obj:
            find_video_urls_recursive(item, found)
    elif isinstance(obj, dict):
        for val in obj.values():
            find_video_urls_recursive(val, found)
    return found


def parse_generate_quota_telemetry(resp_json) -> dict:
    """Extract live monthly quota telemetry from `$[4][0]` of a `/v1/genai/generate` response."""
    out = {}
    try:
        q_block = resp_json[4][0]
        if isinstance(q_block, list):
            if len(q_block) > 1 and isinstance(q_block[1], list):
                meta = q_block[1]
                if len(meta) > 0 and meta[0] is not None:
                    out["limit"] = int(meta[0])
                if len(meta) > 2 and meta[2] is not None:
                    out["remaining"] = int(meta[2])
                if len(meta) > 6 and isinstance(meta[6], list) and meta[6]:
                    out["reset_epoch"] = int(meta[6][0])
            if len(q_block) > 2 and q_block[2] is not None:
                out["used"] = int(q_block[2])
    except Exception:
        pass
    return out


class GoogleVidsClient:
    """Thread-safe Google Vids Web API client with session & Scotty blob caching."""

    SESSION_TTL_SEC = 1500  # 25 minutes
    BLOB_TTL_SEC = 1800     # 30 minutes

    def __init__(self, workspace_dir: Optional[pathlib.Path] = None):
        self.ws_dir = pathlib.Path(workspace_dir) if workspace_dir else WS_DIR
        self._lock = threading.RLock()
        self._sessions: Dict[str, dict] = {}
        self._blob_cache: Dict[Tuple[str, str], Tuple[str, float]] = {}
        self._doc_map: Dict[str, str] = self._load_persisted_doc_map()

    def _load_persisted_doc_map(self) -> Dict[str, str]:
        try:
            if SESSIONS_CACHE_FILE.is_file():
                data = json.loads(SESSIONS_CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in (data.get("doc_ids") or {}).items() if v}
        except Exception:
            pass
        return {}

    def _save_persisted_doc_id(self, profile: str, doc_id: str) -> None:
        if not profile or not doc_id:
            return
        with self._lock:
            self._doc_map[profile] = doc_id
            try:
                SESSIONS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                SESSIONS_CACHE_FILE.write_text(
                    json.dumps({"doc_ids": self._doc_map, "updated_at": int(time.time())}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def bootstrap_session(self, profile_name: str = "", force_refresh: bool = False) -> dict:
        cookie_path = find_cookie_json_for_profile(profile_name, workspace_dir=self.ws_dir)
        if not cookie_path:
            raise RuntimeError(
                f"Không tìm thấy file Cookie cho tài khoản '{profile_name or 'auto'}'. "
                "Hãy đăng nhập tài khoản Google trong tab Tài Khoản trước."
            )
        resolved_prof = cookie_path.stem

        with self._lock:
            cached = self._sessions.get(resolved_prof)
            if (
                not force_refresh
                and cached
                and (time.time() - cached.get("bootstrapped_at", 0)) < self.SESSION_TTL_SEC
                and cached.get("server_token")
                and cached.get("api_key")
            ):
                return cached

        opener, cj, sapisid_map = load_cookie_jar(cookie_path)
        if not sapisid_map:
            raise RuntimeError(f"[{resolved_prof}] Cookie thiếu SAPISID / __Secure-1PAPISID. Vui lòng trích xuất lại Cookie.")

        # 1. Complete OSID cookie handshake on docs.google.com/videos/u/0/
        req_home = urllib.request.Request(
            f"{ORIGIN}/videos/u/0/",
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        )
        with opener.open(req_home, timeout=35) as r_home:
            html_home = r_home.read().decode("utf-8", errors="replace")
            final_home = r_home.geturl()

        if "accounts.google.com/v3/signin" in final_home or "ServiceLogin" in final_home:
            raise RuntimeError(
                f"[{resolved_prof}] Phiên Google Vids bị chuyển hướng đăng nhập (thiếu cookie LSID trên accounts.google.com hoặc phiên đã hết hạn). "
                "Hãy đăng nhập / đồng bộ lại tài khoản Google."
            )

        # 2. Reuse persisted doc_id or first existing Vids doc on Drive; only create 1 doc if account has none
        doc_ids_home = re.findall(r"/videos/d/([a-zA-Z0-9_\-]{25,60})/", html_home)
        preferred_doc_id = self._doc_map.get(resolved_prof) or (doc_ids_home[0] if doc_ids_home else "")
        ed_urls_to_try = []
        if preferred_doc_id:
            ed_urls_to_try.append(f"{ORIGIN}/videos/d/{preferred_doc_id}/edit")
        if doc_ids_home and doc_ids_home[0] != preferred_doc_id:
            ed_urls_to_try.append(f"{ORIGIN}/videos/d/{doc_ids_home[0]}/edit")
        ed_urls_to_try.append(f"{ORIGIN}/videos/create")

        html_ed = ""
        final_ed = ""
        last_ed_err = None
        for ed_url in ed_urls_to_try:
            try:
                req_ed = urllib.request.Request(
                    ed_url,
                    headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                )
                with opener.open(req_ed, timeout=35) as r_ed:
                    html_ed = r_ed.read().decode("utf-8", errors="replace")
                    final_ed = r_ed.geturl()
                if '"docs-est"' in html_ed and '"espresso_api_key"' in html_ed:
                    break
            except urllib.error.HTTPError as he:
                last_ed_err = f"HTTP {he.code} on {ed_url}"
                continue
            except Exception as exc:
                last_ed_err = str(exc)
                continue

        if not html_ed:
            raise RuntimeError(f"[{resolved_prof}] Không mở được trình soạn thảo Google Vids ({last_ed_err}).")

        m_doc = re.search(r"/videos/d/([a-zA-Z0-9_\-]{25,60})/", final_ed) or re.search(
            r"/videos/d/([a-zA-Z0-9_\-]{25,60})/", html_ed
        )
        doc_id = m_doc.group(1) if m_doc else preferred_doc_id

        def _extract(pattern: str, default: str = "") -> str:
            m = re.search(pattern, html_ed)
            return m.group(1) if m else default

        server_token = _extract(r'"docs-est"\s*:\s*"([^"]+)"')
        api_key = _extract(r'"espresso_api_key"\s*:\s*"([^"]+)"')
        genai_host = _extract(r'"docs-gaopd"\s*:\s*"([^"]+)"', DEFAULT_GENAI_HOST)
        upload_path = _extract(r'"docs-tbuu"\s*:\s*"([^"]+)"', DEFAULT_UPLOAD_PATH)
        email = _extract(r'"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"')

        if not server_token or not api_key:
            raise RuntimeError(
                f"[{resolved_prof}] Tài khoản chưa được bật tính năng AI (Gemini/Veo) trong Google Vids "
                "(thiếu docs-est hoặc espresso_api_key)."
            )

        if doc_id:
            self._save_persisted_doc_id(resolved_prof, doc_id)

        sess = {
            "profile": resolved_prof,
            "email": email,
            "cookie_path": str(cookie_path),
            "opener": opener,
            "cookie_jar": cj,
            "sapisid_map": sapisid_map,
            "doc_id": doc_id,
            "server_token": server_token,
            "api_key": api_key,
            "genai_host": genai_host,
            "upload_path": upload_path,
            "editor_url": final_ed or f"{ORIGIN}/videos/d/{doc_id}/edit",
            "bootstrapped_at": time.time(),
        }
        with self._lock:
            self._sessions[resolved_prof] = sess
        return sess

    def get_quota_summary(self, profile_name: str = "") -> dict:
        """Check Google Vids Veo/Omni eligibility (feature 1189) via `/v1/genai/quotaSummary`."""
        sess = self.bootstrap_session(profile_name=profile_name)
        payload = [None, 1, [24], ACTION_INGREDIENTS_TO_VIDEO, None, [[None, None, QUOTA_FEATURE_VEO_VIDS]]]
        url = f"https://{sess['genai_host']}/v1/genai/quotaSummary?key={sess['api_key']}"
        headers = {
            "Authorization": make_sapisidhash_header(sess["sapisid_map"]),
            "Origin": ORIGIN,
            "Referer": f"{ORIGIN}/",
            "X-Server-Token": sess["server_token"],
            "X-Goog-AuthUser": "0",
            "Content-Type": "application/json+protobuf",
            "Accept": "*/*",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with sess["opener"].open(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                parsed = json.loads(strip_xssi(raw))
                tier_code = None
                try:
                    tier_code = parsed[0][0][1]
                except Exception:
                    pass
                return {
                    "ok": True,
                    "profile": sess["profile"],
                    "email": sess["email"],
                    "doc_id": sess["doc_id"],
                    "tier_code": tier_code,
                    "raw": parsed,
                }
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "profile": sess["profile"],
                "email": sess["email"],
                "status": he.code,
                "error": err_body[:500],
            }
        except Exception as exc:
            return {"ok": False, "profile": sess["profile"], "error": str(exc)}

    def upload_image(self, sess: dict, image_path: Union[str, pathlib.Path], use_cache: bool = True) -> str:
        """Upload an image via Scotty resumable upload (`/upload/temporaryblob/videos`) and return `AYGXpj...` token."""
        fpath = pathlib.Path(image_path)
        if not fpath.is_file():
            raise FileNotFoundError(f"Không tìm thấy ảnh tham chiếu: {fpath}")
        file_bytes = fpath.read_bytes()
        sha = hashlib.sha256(file_bytes).hexdigest()
        cache_key = (sess["profile"], sha)

        if use_cache:
            with self._lock:
                cached = self._blob_cache.get(cache_key)
                if cached and (time.time() - cached[1]) < self.BLOB_TTL_SEC:
                    return cached[0]

        ascii_name = sanitize_upload_filename(fpath.name)
        start_url = f"{ORIGIN}{sess['upload_path']}?authuser=0"
        start_headers = {
            "Origin": ORIGIN,
            "Referer": sess["editor_url"],
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Content-Length": str(len(file_bytes)),
            "X-Goog-Upload-File-Name": ascii_name,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        req_start = urllib.request.Request(start_url, data=b"", headers=start_headers, method="POST")
        with sess["opener"].open(req_start, timeout=60) as r1:
            up_status = r1.headers.get("X-Goog-Upload-Status") or r1.headers.get("x-goog-upload-status")
            up_url = r1.headers.get("X-Goog-Upload-URL") or r1.headers.get("x-goog-upload-url")
            body1 = r1.read().decode("utf-8", errors="replace")
        if not up_url:
            raise RuntimeError(f"Khởi tạo upload ảnh Google Vids thất bại (status={up_status}): {body1[:300]}")

        fin_headers = {
            "Origin": ORIGIN,
            "Referer": sess["editor_url"],
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
            "Content-Type": "application/octet-stream",
        }
        req_fin = urllib.request.Request(up_url, data=file_bytes, headers=fin_headers, method="POST")
        with sess["opener"].open(req_fin, timeout=120) as r2:
            fin_status = r2.headers.get("X-Goog-Upload-Status") or r2.headers.get("x-goog-upload-status")
            body2 = r2.read().decode("utf-8", errors="replace")
        if fin_status != "final":
            raise RuntimeError(f"Hoàn tất upload ảnh Google Vids thất bại (status={fin_status}): {body2[:300]}")

        parsed = json.loads(strip_xssi(body2))
        blob_token = parsed[0] if isinstance(parsed, list) and parsed else None
        if not blob_token or not isinstance(blob_token, str):
            raise RuntimeError(f"Phản hồi temporaryblob không hợp lệ: {body2[:300]}")

        with self._lock:
            self._blob_cache[cache_key] = (blob_token, time.time())
        return blob_token

    def invalidate_profile_blobs(self, profile_name: str) -> None:
        with self._lock:
            to_del = [k for k in self._blob_cache if k[0] == profile_name]
            for k in to_del:
                self._blob_cache.pop(k, None)

    def _prepare_prompt_ast_and_mentions(
        self,
        sess: dict,
        prompt: str = "",
        image_paths: Optional[List[Union[str, pathlib.Path, dict]]] = None,
        segments_spec: Optional[List[dict]] = None,
        asset_path_map: Optional[Dict[str, str]] = None,
        ingredient_role: str = "auto",
        use_blob_cache: bool = True,
    ) -> Tuple[list, Optional[list], int]:
        """
        Upload up to 3 reference images and construct `(prompt_ast, mentioned_context, action_code)`.
        Supports:
          1. Structured `segments_spec` + `asset_path_map` (Fashion Studio)
          2. Prompt strings with `{IMG1..3}`, `@Hình ảnh1..3`, or `[filename.png]` tags
          3. Plain prompt strings + 1..3 `image_paths` (auto-injects clean `@Hình ảnhX` header chips)
        """
        mentioned_context: list = []

        # Path A: Structured segments_spec (Fashion Studio)
        if segments_spec and asset_path_map:
            ordered_assets: List[Tuple[str, str, str]] = []  # (asset_key, title, file_path)
            seen_paths = {}
            for seg in segments_spec:
                if seg.get("type") != "media":
                    continue
                akey = str(seg.get("asset_key") or "")
                title = str(seg.get("title") or "")
                if akey.startswith("ref_video_") or title.lower().endswith(".mp4"):
                    continue
                fpath = asset_path_map.get(akey) or asset_path_map.get(title) or ""
                if not fpath or not os.path.isfile(fpath):
                    continue
                abs_p = os.path.abspath(fpath)
                if abs_p not in seen_paths and len(seen_paths) < 3:
                    seen_paths[abs_p] = len(ordered_assets)
                    ordered_assets.append((akey, title, abs_p))

            key_to_chip: Dict[str, dict] = {}
            path_to_chip: Dict[str, dict] = {}
            for idx, (akey, title, abs_p) in enumerate(ordered_assets, 1):
                label = f"Hình ảnh{idx}"
                blob_tok = self.upload_image(sess, abs_p, use_cache=use_blob_cache)
                img_uuid = str(uuid.uuid4()).upper()
                chip_info = {"uuid": img_uuid, "label": label, "blob": blob_tok, "path": abs_p}
                path_to_chip[abs_p] = chip_info
                if akey:
                    key_to_chip[akey] = chip_info
                if title:
                    key_to_chip[title] = chip_info
                mentioned_context.append(build_mentioned_image_entry(img_uuid, blob_tok, label))

            # Also map alias keys sharing the same physical file path
            for k, p in (asset_path_map or {}).items():
                if p and os.path.isfile(p):
                    abs_p = os.path.abspath(p)
                    if abs_p in path_to_chip:
                        key_to_chip[k] = path_to_chip[abs_p]

            prompt_ast = build_amv_ast_from_segments(segments_spec, key_to_chip)
            action_code = ACTION_INGREDIENTS_TO_VIDEO if mentioned_context else ACTION_TEXT_TO_VIDEO
            return prompt_ast, (mentioned_context or None), action_code

        # Path B: `image_paths` list (0..3 images) + prompt string
        norm_imgs: List[dict] = []
        seen_abs = set()
        for item in image_paths or []:
            if isinstance(item, dict):
                p = str(item.get("path") or "")
                custom_tags = list(item.get("tags") or [])
                if item.get("key"):
                    custom_tags.append(str(item["key"]))
            else:
                p = str(item or "")
                custom_tags = []
            if not p or not os.path.isfile(p):
                continue
            abs_p = os.path.abspath(p)
            if abs_p in seen_abs:
                continue
            seen_abs.add(abs_p)
            norm_imgs.append({"path": abs_p, "filename": os.path.basename(abs_p), "tags": custom_tags})
            if len(norm_imgs) >= 3:
                break

        if not norm_imgs:
            return [None, None, None, [[[None, None, prompt]]]], None, ACTION_TEXT_TO_VIDEO

        tag_map: Dict[str, dict] = {}
        chips_by_idx: List[dict] = []
        for idx, img_item in enumerate(norm_imgs, 1):
            label = f"Hình ảnh{idx}"
            blob_tok = self.upload_image(sess, img_item["path"], use_cache=use_blob_cache)
            img_uuid = str(uuid.uuid4()).upper()
            info = {"uuid": img_uuid, "label": label, "blob": blob_tok, "path": img_item["path"]}
            chips_by_idx.append(info)
            mentioned_context.append(build_mentioned_image_entry(img_uuid, blob_tok, label))

            fn = img_item["filename"]
            for alias in [
                f"{{IMG{idx}}}",
                f"@{label}",
                label,
                f"[{fn}]",
                *img_item["tags"],
            ]:
                if alias:
                    tag_map[alias] = info

        # Check if prompt already contains at least one inline tag; if not, prepend clean inline chip header
        has_inline_tag = any(alias in prompt for alias in tag_map)
        effective_prompt = prompt
        if not has_inline_tag:
            role = (ingredient_role or "auto").lower()
            if role == "storyboard" or (role == "auto" and len(chips_by_idx) == 1 and "storyboard" in prompt.lower()):
                effective_prompt = (
                    "Use {IMG1} strictly as the 6-panel visual storyboard reference for exact cookware, ingredients, "
                    "food state, lighting, and step-by-step cooking sequence (render one continuous full-frame vertical "
                    "video; never show grid borders or split panels).\n\n" + prompt
                )
            elif len(chips_by_idx) == 1:
                effective_prompt = (
                    "Use {IMG1} as the exact opening frame composition, character/subject identity, lighting, and environment reference.\n\n"
                    + prompt
                )
            elif len(chips_by_idx) == 2:
                effective_prompt = (
                    "Use {IMG1} as the exact opening scene composition, character identity, outfit, lighting, and environment reference, "
                    "and use {IMG2} as the exact product/wardrobe detail reference.\n\n" + prompt
                )
            else:
                effective_prompt = (
                    "Use {IMG1} as the exact opening scene and identity reference, {IMG2} as reference 2, and {IMG3} as reference 3.\n\n"
                    + prompt
                )

        prompt_ast = build_amv_ast_from_template(effective_prompt, tag_map)
        return prompt_ast, mentioned_context, ACTION_INGREDIENTS_TO_VIDEO

    def generate_video(
        self,
        out_mp4: Union[str, pathlib.Path],
        prompt: str = "",
        image_paths: Optional[List[Union[str, pathlib.Path, dict]]] = None,
        segments_spec: Optional[List[dict]] = None,
        asset_path_map: Optional[Dict[str, str]] = None,
        profile_name: str = "",
        fallback_profiles: Optional[List[str]] = None,
        model: str = "omni",
        aspect_ratio: str = "9:16",
        resolution: str = "1080p",
        duration_sec: int = 8,
        ingredient_role: str = "auto",
        max_retries: int = 2,
        timeout_sec: int = 270,
    ) -> dict:
        """
        Generate a native 1080p MP4 video via Google Vids Web API and save atomically to `out_mp4`.
        Supports automatic token refresh on 401/403 and optional multi-account failover on 429 quota limits.
        """
        out_path = pathlib.Path(out_mp4)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        dur_clamped = max(4, min(15, int(round(float(duration_sec or 8)))))
        model_id = resolve_model_id(model)
        ar_res_enum = resolve_aspect_res_enum(aspect_ratio=aspect_ratio, resolution=resolution)

        profiles_order: List[str] = []
        if profile_name:
            profiles_order.append(profile_name)
        for fp in fallback_profiles or []:
            if fp and fp not in profiles_order:
                profiles_order.append(fp)
        if not profiles_order:
            profiles_order.append("auto")

        last_error = "Unknown Google Vids error"
        for prof_cand in profiles_order:
            force_ref = False
            use_blob_cache = True
            for attempt in range(max_retries + 1):
                t_start = time.time()
                try:
                    sess = self.bootstrap_session(profile_name=prof_cand, force_refresh=force_ref)
                    prompt_ast, mentioned_ctx, action_code = self._prepare_prompt_ast_and_mentions(
                        sess=sess,
                        prompt=prompt,
                        image_paths=image_paths,
                        segments_spec=segments_spec,
                        asset_path_map=asset_path_map,
                        ingredient_role=ingredient_role,
                        use_blob_cache=use_blob_cache,
                    )
                    ctx = build_request_context(sess["doc_id"], mentioned_context=mentioned_ctx)
                    erp = [0, model_id, None, 0, ar_res_enum, None, None, None, dur_clamped]
                    gen_options = [None] * 15 + [erp]
                    quota_desc = [1, None, [[None, "1", QUOTA_FEATURE_VEO_VIDS]]]
                    gen_payload = [action_code, None, ctx, prompt_ast, gen_options, quota_desc, 1]

                    gen_url = f"https://{sess['genai_host']}/v1/genai/generate?key={sess['api_key']}"
                    gen_headers = {
                        "Authorization": make_sapisidhash_header(sess["sapisid_map"]),
                        "Origin": ORIGIN,
                        "Referer": f"{ORIGIN}/",
                        "Accept-Language": "vi",
                        "X-Server-Token": sess["server_token"],
                        "X-Goog-AuthUser": "0",
                        "Content-Type": "application/json+protobuf",
                        "Accept": "*/*",
                    }
                    body_bytes = json.dumps(gen_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    req_gen = urllib.request.Request(gen_url, data=body_bytes, headers=gen_headers, method="POST")
                    with sess["opener"].open(req_gen, timeout=timeout_sec) as resp:
                        resp_raw = resp.read().decode("utf-8", errors="replace")

                    resp_json = json.loads(strip_xssi(resp_raw))
                    urls = find_video_urls_recursive(resp_json)
                    quota_telemetry = parse_generate_quota_telemetry(resp_json)

                    if not urls:
                        last_error = f"[{sess['profile']}] Google Vids không trả về link tải video (có thể vướng bộ lọc an toàn nội dung)."
                        if attempt < max_retries:
                            time.sleep(2.5)
                            continue
                        break

                    dl_req = urllib.request.Request(
                        urls[0],
                        headers={"Referer": f"{ORIGIN}/", "Accept": "*/*"},
                    )
                    with sess["opener"].open(dl_req, timeout=150) as r_dl:
                        mp4_bytes = r_dl.read()

                    if len(mp4_bytes) < 20000 or b"ftyp" not in mp4_bytes[:32]:
                        raise RuntimeError(f"File tải về không phải MP4 hợp lệ ({len(mp4_bytes)} bytes).")

                    tmp_out = out_path.with_suffix(f".vids_{os.getpid()}_{random.randint(1000,9999)}.tmp")
                    tmp_out.write_bytes(mp4_bytes)
                    os.replace(str(tmp_out), str(out_path))

                    return {
                        "ok": True,
                        "provider": "google_vids",
                        "profile": sess["profile"],
                        "email": sess.get("email") or "",
                        "model": "omni" if model_id == 12 else "veo_3_1",
                        "duration_sec": dur_clamped,
                        "resolution": "720p" if ar_res_enum in (1, 2) else "1080p",
                        "aspect_ratio": "16:9" if ar_res_enum in (1, 5) else "9:16",
                        "out_mp4": str(out_path),
                        "bytes": len(mp4_bytes),
                        "elapsed_sec": round(time.time() - t_start, 1),
                        "quota": quota_telemetry,
                        "download_url": urls[0],
                    }

                except urllib.error.HTTPError as he:
                    err_txt = ""
                    try:
                        err_txt = he.read().decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    last_error = f"[{prof_cand}] HTTP {he.code}: {err_txt[:320]}"
                    # 429 / RESOURCE_EXHAUSTED -> switch immediately to next fallback account if available
                    if he.code == 429 or "RESOURCE_EXHAUSTED" in err_txt.upper():
                        break
                    # 400/401/403 -> refresh session token & re-upload blobs once
                    if he.code in (400, 401, 403) and attempt < max_retries:
                        force_ref = True
                        use_blob_cache = False
                        self.invalidate_profile_blobs(prof_cand)
                        time.sleep(1.5)
                        continue
                    if he.code >= 500 and attempt < max_retries:
                        time.sleep(3.0)
                        continue
                    break
                except Exception as exc:
                    last_error = f"[{prof_cand}] {exc}"
                    if attempt < max_retries:
                        force_ref = True
                        time.sleep(2.0)
                        continue
                    break

        return {"ok": False, "provider": "google_vids", "error": last_error}


_GLOBAL_VIDS_CLIENT: Optional[GoogleVidsClient] = None
_GLOBAL_LOCK = threading.Lock()


def get_google_vids_client() -> GoogleVidsClient:
    global _GLOBAL_VIDS_CLIENT
    with _GLOBAL_LOCK:
        if _GLOBAL_VIDS_CLIENT is None:
            _GLOBAL_VIDS_CLIENT = GoogleVidsClient()
        return _GLOBAL_VIDS_CLIENT

