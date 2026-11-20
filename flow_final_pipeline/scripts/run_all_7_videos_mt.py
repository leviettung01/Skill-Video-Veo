# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import uuid
import base64
import random
import shutil
import threading
import urllib.parse
import subprocess
import concurrent.futures
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
WS_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
GROK_DIR = WS_DIR
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
BUILD_FINAL_SCRIPT = os.path.join(SCRIPTS_DIR, "build_final.py")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
if WS_DIR not in sys.path:
    sys.path.insert(0, WS_DIR)
import grok_video_tool as gvt
import google_flow_auth as gfa
from google_flow_auth import profile_paths
from playwright.sync_api import sync_playwright
from curl_cffi import requests as cffi_requests
from sync_web_ui_state import sync_web_ui, get_final_video_filename

try:
    import engine_settings_manager as _esm
except Exception:
    _esm = None

ALL_PIDS = [
    "1738086213622335480",
    "1735109997221349342",
    "1738260652434293979",
    "1735811961345574265",
    "1737365863541671120",
    "1738175423853987061",
    "1735424296473888680",
    "1737909342761027082",
]


def _resolve_initial_prof_name() -> str:
    try:
        if _esm is not None:
            accs = [a for a in _esm.list_available_flow_accounts() if a.get("active", True)]
            if accs:
                return str(accs[0].get("profile_name") or "").strip() or "default_flow"
    except Exception:
        pass
    return gvt._default_google_profile_name() or "default_flow"


PROF_NAME = _resolve_initial_prof_name()
shared_dir = gvt._resolve_flow_shared_dir(PROF_NAME)
profile_dir, cookies_file = profile_paths(shared_dir, PROF_NAME)

_PW_RUNNER_FN = [None]


def _run_pw_safe(fn, *args, **kwargs):
    runner = _PW_RUNNER_FN[0]
    if callable(runner):
        return runner(fn, *args, **kwargs)
    return fn(*args, **kwargs)

STATE_LOCK = threading.Lock()
UI_SYNC_LOCK = threading.Lock()
FFMPEG_SUBMITTED = set()
_LAST_MT_SYNC_TS = 0.0


def safe_sync_ui(force: bool = False):
    global _LAST_MT_SYNC_TS
    with UI_SYNC_LOCK:
        now_t = time.time()
        if not force and (now_t - _LAST_MT_SYNC_TS) < 6.0:
            return
        _LAST_MT_SYNC_TS = now_t
        try:
            sync_web_ui(force=force)
        except Exception as e:
            print(f"[UI-SYNC WARN] {e}", flush=True)


def _sanitize_chrome_ua(raw_ua: str = "") -> str:
    """Strip HeadlessChrome token so reCAPTCHA and Flow HTTP requests always present a real desktop Chrome UA."""
    if hasattr(gvt, "sanitize_chrome_ua"):
        return gvt.sanitize_chrome_ua(raw_ua)
    ua = str(raw_ua or "").strip()
    if ua:
        ua = ua.replace("HeadlessChrome/", "Chrome/")
        if "Chrome/" in ua and "Headless" not in ua:
            return ua
    return str(
        getattr(gvt, "UA_CHROME_131_WIN", "")
        or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )


def call_flow_rpc_cffi(http_session, cookie_hdr, wiz, project_id, rpcid, payload_obj):
    url = (
        f"https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute"
        f"?rpcids={rpcid}&source-path=%2Fproject%2F{project_id}"
        f"&bl={urllib.parse.quote(wiz['bl'])}&f.sid={urllib.parse.quote(str(wiz['fsid']))}"
        f"&hl=vi&_reqid={random.randint(100000, 999999)}&rt=c"
    )
    f_req = json.dumps(
        [[[rpcid, json.dumps(payload_obj, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    body = f"f.req={urllib.parse.quote(f_req)}&at={urllib.parse.quote(wiz['at'])}&"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://flow.google.com",
        "Referer": f"https://flow.google.com/project/{project_id}",
        "User-Agent": _sanitize_chrome_ua(wiz.get("ua", "")),
        "X-Same-Domain": "1",
        "Cookie": cookie_hdr,
    }
    r = http_session.post(url, headers=headers, data=body, timeout=90)
    if r.status_code != 200:
        return False, None, f"HTTP {r.status_code}: {r.text[:250]}"
    return gvt._parse_batchexecute_wrb(r.text, rpcid)


def find_img_url(obj):
    if isinstance(obj, str) and (
        obj.startswith("https://lh3.googleusercontent.com/")
        or obj.startswith("https://flow-content.google/image/")
    ):
        return obj
    if isinstance(obj, list):
        for x in obj:
            r = find_img_url(x)
            if r:
                return r
    return None


_EXT_BRIDGE_BOX = [None]
_EXT_RCAP_TMT_STREAK = [0]
_EXT_CAPTCHA_STREAK = [0]
_EXT_CAPTCHA_COOL_UNTIL = [0.0]
_EXT_LAST_RESET_TS = [0.0]
_ACC_TMT_STREAK = {}
_ACC_LAST_RPC_TS = {}
_ACC_LOCKS_GUARD = threading.Lock()
_SPRCAD_CONSEC_FAILS = [0]
_SPRCAD_SKIP_UNTIL = [0.0]
_SPRCAD_LOCK = threading.Lock()
_ACC_PAGE_LOCKS = {}
_ACC_COOKIE_MAP = {}
_FLOW_SITEKEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"


def _get_acc_page_lock(prof_name: str):
    key = str(prof_name or "_default").strip() or "_default"
    with _ACC_LOCKS_GUARD:
        lk = _ACC_PAGE_LOCKS.get(key)
        if lk is None:
            lk = threading.RLock()
            _ACC_PAGE_LOCKS[key] = lk
        return lk


def _eval_flow_rcap(page, action: str, clear_cookie: bool = False):
    """Execute grecaptcha Enterprise inside active Flow page/extension without propagating unhandled exceptions."""
    try:
        if clear_cookie and getattr(page, "context", None):
            try:
                page.context.clear_cookies(name="_grecaptcha")
            except Exception:
                pass
        if hasattr(page, "mouse"):
            try:
                page.mouse.move(random.randint(240, 740), random.randint(220, 560), steps=3)
            except Exception:
                pass
        tok = page.evaluate(
            f"""async () => {{
                const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
                return await fn({json.dumps(_FLOW_SITEKEY)}, {{action: {json.dumps(action)}}});
            }}"""
        )
        if not tok:
            return None, "Empty reCAPTCHA token"
        return tok, None
    except Exception as exc:
        return None, str(exc)


def _post_flow_rpc(page, wiz, project_id, rpcid, payload_builder_fn, recaptcha_action, cookie_hdr="", prof_name="", use_ext=True):
    """Execute protected Flow batchexecute RPC via Extension :4000 (+cffi) first, falling back seamlessly to Stealth Playwright."""
    eff_ck = str(cookie_hdr or _ACC_COOKIE_MAP.get(prof_name, "") or "").strip()
    acc_key = str(prof_name or "_default").strip() or "_default"
    br = _EXT_BRIDGE_BOX[0] if use_ext else None
    with _ACC_LOCKS_GUARD:
        cur_tmt_st = int(_ACC_TMT_STREAK.get(acc_key, 0) or 0)
        wait_rpc = max(0.0, 1.3 - (time.time() - float(_ACC_LAST_RPC_TS.get(acc_key, 0.0) or 0.0)))
    if wait_rpc > 0.05:
        time.sleep(wait_rpc)
    with _ACC_LOCKS_GUARD:
        _ACC_LAST_RPC_TS[acc_key] = time.time()

    # When Extension reCAPTCHA score is cooling down after UNUSUAL_ACTIVITY, route directly to Stealth Playwright
    # so accounts keep producing with fresh per-account sessions while Extension resets tabs.
    ext_in_captcha_cool = (time.time() < float(_EXT_CAPTCHA_COOL_UNTIL[0] or 0.0)) and (page is not None)
    try_ext_first = (
        (br is not None and bool(eff_ck))
        and not ext_in_captcha_cool
        and not (cur_tmt_st >= 2 and (cur_tmt_st % 2 == 1) and page is not None)
    )
    if try_ext_first:
        try:
            tok_ext = br.request_recaptcha_for_account(action=recaptcha_action, timeout=18, account_key=prof_name or "")
            if tok_ext:
                payload_ext = payload_builder_fn(tok_ext)
                with cffi_requests.Session(impersonate="chrome131") as s_ext:
                    ok_ext, inner_ext, err_ext = call_flow_rpc_cffi(s_ext, eff_ck, wiz, project_id, rpcid, payload_ext)
                if ok_ext and isinstance(inner_ext, list):
                    try:
                        br.notify_success()
                    except Exception:
                        pass
                    _EXT_RCAP_TMT_STREAK[0] = 0
                    _EXT_CAPTCHA_STREAK[0] = 0
                    _EXT_CAPTCHA_COOL_UNTIL[0] = 0.0
                    with _ACC_LOCKS_GUARD:
                        _ACC_TMT_STREAK[acc_key] = 0
                    return True, inner_ext, None
                err_up = str(err_ext or "").upper()
                is_unusual_captcha = any(k in err_up for k in ("UNUSUAL_ACTIVITY", "RECAPTCHA"))
                is_rcap_or_tmt = is_unusual_captcha or any(
                    k in err_up for k in ("TOO_MUCH_TRAFFIC", "HIGH_TRAFFIC", "THROTTLED", "HTTP 429", "EXC_")
                )
                fmt_ext_err = f"{rpcid} {err_ext}" if rpcid in ("SPrCad", "p0UkFb", "maseQ") else str(err_ext)
                err_ext_up = str(err_ext or "").upper()
                is_hard_rate_or_biz = any(
                    k in err_ext_up
                    for k in (
                        "TOO_MUCH_TRAFFIC",
                        "HIGH_TRAFFIC",
                        "RESOURCE_EXHAUSTED",
                        "INSUFFICIENT_CREDITS",
                        "QUOTA",
                        "INVALID_ARGUMENT",
                        "POLICY_VIOLATION",
                        "SAFETY",
                    )
                ) or ("[8]" in str(err_ext or ""))
                if not is_rcap_or_tmt or is_hard_rate_or_biz:
                    if "TOO_MUCH_TRAFFIC" in err_ext_up or "[8]" in str(err_ext or "") or "HIGH_TRAFFIC" in err_ext_up:
                        with _ACC_LOCKS_GUARD:
                            _ACC_TMT_STREAK[acc_key] = int(_ACC_TMT_STREAK.get(acc_key, 0) or 0) + 1
                    # Do NOT fall through to Playwright page.evaluate when Flow already returned [8] / quota / policy!
                    return False, None, fmt_ext_err
                if is_unusual_captcha:
                    do_ext_reset = False
                    with _ACC_LOCKS_GUARD:
                        _EXT_CAPTCHA_STREAK[0] += 1
                        if _EXT_CAPTCHA_STREAK[0] >= 2:
                            # Put burnt Extension pool on 45s cooldown & force Stealth Playwright per-account session
                            _EXT_CAPTCHA_COOL_UNTIL[0] = max(_EXT_CAPTCHA_COOL_UNTIL[0], time.time() + 45.0)
                            if (time.time() - _EXT_LAST_RESET_TS[0]) >= 35.0:
                                _EXT_CAPTCHA_STREAK[0] = 0
                                _EXT_LAST_RESET_TS[0] = time.time()
                                do_ext_reset = True
                    if do_ext_reset:
                        print("🔄 [Captcha-Fallback] Extension tụt điểm reCAPTCHA ([7]) -> reset tab Extension & chuyển tạm sang Playwright Stealth 45s!", flush=True)
                        try:
                            br.notify_recaptcha_score_dead()
                        except Exception:
                            pass
                    # Always fall through to Stealth Playwright on UNUSUAL_ACTIVITY instead of deadlocking!
                else:
                    _EXT_RCAP_TMT_STREAK[0] += 1
                    do_ext_reset = False
                    with _ACC_LOCKS_GUARD:
                        if _EXT_RCAP_TMT_STREAK[0] >= 6 and (time.time() - _EXT_LAST_RESET_TS[0]) >= 60.0:
                            _EXT_RCAP_TMT_STREAK[0] = 0
                            _EXT_LAST_RESET_TS[0] = time.time()
                            do_ext_reset = True
                    if do_ext_reset:
                        try:
                            br.notify_recaptcha_score_dead()
                        except Exception:
                            pass
                    with _ACC_LOCKS_GUARD:
                        _ACC_TMT_STREAK[acc_key] = int(_ACC_TMT_STREAK.get(acc_key, 0) or 0) + 1
                        new_st = _ACC_TMT_STREAK[acc_key]
                    if new_st >= 2:
                        return False, None, fmt_ext_err
        except Exception as exc_ext_rpc:
            print(f"   [RPC-EXT WARN {acc_key} | {rpcid}] {exc_ext_rpc}", flush=True)

    if page is None:
        return False, None, f"{rpcid} no Playwright page available"

    def _do_pw_rpc():
        with _get_acc_page_lock(prof_name):
            with _ACC_LOCKS_GUARD:
                pw_should_clear = int(_ACC_TMT_STREAK.get(acc_key, 0) or 0) >= 3
            rcap, rcap_err = _eval_flow_rcap(page, recaptcha_action, clear_cookie=pw_should_clear)
            if not rcap:
                return None, f"{rpcid} rcap failed: {rcap_err}"
            payload_obj = payload_builder_fn(rcap)
            f_req_str = json.dumps(
                [[[rpcid, json.dumps(payload_obj, separators=(",", ":")), None, "generic"]]],
                separators=(",", ":"),
            )
            reqid = random.randint(100000, 999999)
            r_obj = page.evaluate(
                """async ({rpcid, projectId, bl, fsid, reqid, fReq, at}) => {
                    const sp = projectId ? `/project/${projectId}` : '/';
                    const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=${rpcid}&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
                    const body = `f.req=${encodeURIComponent(fReq)}&at=${encodeURIComponent(at)}&`;
                    const r = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                            'x-same-domain': '1'
                        },
                        body
                    });
                    return {status: r.status, text: await r.text()};
                }""",
                {
                    "rpcid": rpcid,
                    "projectId": project_id,
                    "bl": wiz["bl"],
                    "fsid": str(wiz["fsid"]),
                    "reqid": reqid,
                    "fReq": f_req_str,
                    "at": wiz["at"],
                },
            )
            return r_obj, ""

    resp_obj, pw_err_msg = _run_pw_safe(_do_pw_rpc)
    if pw_err_msg:
        return False, None, pw_err_msg
    if not resp_obj or resp_obj.get("status") != 200:
        st_code = (resp_obj or {}).get("status")
        return False, None, (f"{rpcid} HTTP {st_code}" if rpcid in ("SPrCad", "p0UkFb", "maseQ") else f"HTTP {st_code}")
    ok_w, inner_w, err_w = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), rpcid)
    if not ok_w or not isinstance(inner_w, list):
        err_pw_up = str(err_w or "").upper()
        if any(k in err_pw_up for k in ("TOO_MUCH_TRAFFIC", "UNUSUAL_ACTIVITY", "HIGH_TRAFFIC", "RECAPTCHA", "THROTTLED", "429")):
            with _ACC_LOCKS_GUARD:
                _ACC_TMT_STREAK[acc_key] = int(_ACC_TMT_STREAK.get(acc_key, 0) or 0) + 1
        return False, None, (f"{rpcid} {err_w}" if rpcid in ("SPrCad", "p0UkFb", "maseQ") else f"{err_w}")
    with _ACC_LOCKS_GUARD:
        _ACC_TMT_STREAK[acc_key] = 0
    return True, inner_w, None


def upload_single_product_ref_in_page(page, wiz, project_id, img_path, quality=95, cookie_hdr="", prof_name=""):
    """Upload ONLY 1 single-variant product or 2K reference image via maseQ."""
    with Image.open(img_path) as im:
        im_rgb = im.convert("RGB")
        tmp_jpg = img_path + ".upload_tmp.jpg"
        im_rgb.save(tmp_jpg, format="JPEG", quality=int(quality or 95))
    try:
        raw_bytes = open(tmp_jpg, "rb").read()
    finally:
        if os.path.exists(tmp_jpg):
            try:
                os.remove(tmp_jpg)
            except OSError:
                pass
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    wf_seed = str(uuid.uuid4())
    media_seed = str(uuid.uuid4())
    base_name = os.path.basename(img_path)

    def _build_maseq(rcap):
        U = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
        return [U, b64_str, "image/jpeg", True, None, None, None, False, base_name, None, wf_seed, media_seed, None, [1]]

    ok_u, inner_u, err_u = _post_flow_rpc(page, wiz, project_id, "maseQ", _build_maseq, "UPLOAD_IMAGE", cookie_hdr=cookie_hdr, prof_name=prof_name)
    if not ok_u or not isinstance(inner_u, list):
        return False, None, err_u
    media_uuid = inner_u[0][0]
    if not isinstance(media_uuid, str) or len(media_uuid) < 32:
        return False, None, f"Unexpected maseQ {inner_u}"
    return True, media_uuid, None


def upsample_image_2k_in_page(page, wiz, project_id, img_uuid, out_file, cookie_hdr="", prof_name=""):
    """Upsample & download a Flow image at 2K resolution (1536x2752) via SPrCad (ts=1, 0 credits)."""
    def _build_sprcad(rcap):
        S = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
        return [img_uuid, 1, S]

    ok_s, inner_s, err_s = _post_flow_rpc(page, wiz, project_id, "SPrCad", _build_sprcad, "IMAGE_GENERATION", cookie_hdr=cookie_hdr, prof_name=prof_name)
    if not ok_s or not isinstance(inner_s, list) or len(inner_s) < 2 or not isinstance(inner_s[1], str):
        return False, 0, err_s or "SPrCad invalid response"
    raw_2k = base64.b64decode(inner_s[1])
    if len(raw_2k) < 50000:
        return False, 0, f"SPrCad too small ({len(raw_2k)} B)"
    with open(out_file, "wb") as f:
        f.write(raw_2k)
    refs_dir = os.path.join(os.path.dirname(out_file), "refs")
    os.makedirs(refs_dir, exist_ok=True)
    shutil.copy2(out_file, os.path.join(refs_dir, os.path.basename(out_file)))
    return True, len(raw_2k), None


def _submit_ogi_image_request(page, wiz, project_id, prod_uuids, char_id, prompt_str, allow_multi_refs=False, cookie_hdr="", prof_name=""):
    """Submit ogiZ0b image generation request (BELUGA 9:16) and return (ok, gen_uuid, img_url_or_None, err)."""
    max_refs = 5 if allow_multi_refs else 1
    clean_uuids = [u for u in (prod_uuids or []) if u][:max_refs]
    eff_char_id = char_id or ""
    if eff_char_id and not clean_uuids:
        clean_uuids = [eff_char_id]
        eff_char_id = ""

    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    seed = random.randint(100000, 999999)
    aa = [[u, None, None, None, 1] for u in clean_uuids]
    f_prompt = [[[prompt_str]]]

    def _build_ogi(rcap):
        S = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
        yb = [
            None,
            None,
            aa,
            seed,
            2,          # 9:16 portrait
            "BELUGA",   # Nano Banana 2.1
            None,
            S,
            f_prompt,
            None,
            [[eff_char_id]] if eff_char_id else [],
            [],
            wf_uuid,
            m_uuid,
        ]
        return [None, [yb], True, S, [b_uuid]]

    ok_i, inner_i, err_i = _post_flow_rpc(page, wiz, project_id, "ogiZ0b", _build_ogi, "IMAGE_GENERATION", cookie_hdr=cookie_hdr, prof_name=prof_name)
    if not ok_i or not isinstance(inner_i, list):
        return False, None, None, err_i

    gen_uuid = m_uuid
    try:
        cand = inner_i[0][0][0]
        if isinstance(cand, str) and len(cand) >= 32:
            gen_uuid = cand
    except Exception:
        pass
    return True, gen_uuid, find_img_url(inner_i), None


def submit_ref_image_ogi_in_page(page, wiz, task):
    """Non-blocking ogiZ0b submission for a variant 9:16 Ref Image."""
    return _submit_ogi_image_request(
        page=page,
        wiz=wiz,
        project_id=task["project_id"],
        prod_uuids=task.get("prod_uuids") or [],
        char_id=task.get("char_id") or "",
        prompt_str=task["prompt_str"],
        allow_multi_refs=bool(task.get("allow_multi_refs")),
        cookie_hdr=task.get("cookie_hdr") or "",
        prof_name=task.get("worker_profile") or "",
    )


def poll_ref_image_one(default_cookie_hdr, default_wiz, default_dl_headers, task):
    """Poll as29s for a pending ref_img generation and download preview image for 2K SPrCad upgrade."""
    cookie_hdr = task.get("cookie_hdr") or default_cookie_hdr
    wiz = task.get("wiz") or default_wiz
    dl_headers = task.get("dl_headers") or default_dl_headers
    gen_uuid = task["media_uuid"]
    project_id = task["project_id"]
    out_file = task["out_file"]
    with cffi_requests.Session(impersonate="chrome131") as s:
        ok_p, inner_p, err_p = call_flow_rpc_cffi(s, cookie_hdr, wiz, project_id, "as29s", [gen_uuid, None, [2]])
        if not ok_p or not isinstance(inner_p, list):
            return f"rpc_err:{str(err_p)[:180]}", None
        img_url = find_img_url(inner_p)
        if img_url:
            try:
                r_img = s.get(img_url, headers=dl_headers, timeout=60, allow_redirects=True)
                if r_img.status_code != 200 or len(r_img.content) < 5000:
                    r_img = s.get(
                        img_url,
                        headers={"Referer": "https://flow.google.com/", "User-Agent": wiz["ua"]},
                        timeout=60,
                        allow_redirects=True,
                    )
                if r_img.status_code == 200 and len(r_img.content) >= 5000:
                    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
                    with open(out_file, "wb") as f:
                        f.write(r_img.content)
                    return "ready_for_2k_ref", len(r_img.content)
                return f"dl_err:HTTP {r_img.status_code}", None
            except Exception as ex_dl:
                return f"dl_err:{type(ex_dl).__name__}", None
    if hasattr(gvt, "extract_flow_as29s_error"):
        is_failed, status_code, detail = gvt.extract_flow_as29s_error(inner_p)
        if is_failed:
            code_lbl = status_code if status_code is not None else "err"
            return (f"failed_{code_lbl}:{detail[:180]}" if detail else f"failed_{code_lbl}"), None
    return "running_ref", None


def _local_upscale_2k_fallback(img_path: str) -> tuple:
    """Upscale a Flow preview image to 2K (1536x2752) locally and copy to its refs folder."""
    if hasattr(gvt, "upscale_image_local_2k"):
        ok_loc, sz_loc = gvt.upscale_image_local_2k(img_path, 1536, 2752)
    else:
        ok_loc, sz_loc = False, (os.path.getsize(img_path) if os.path.exists(img_path) else 0)
        try:
            from PIL import ImageFilter
            with Image.open(img_path) as im_fb:
                im_2k = im_fb.convert("RGB").resize((1536, 2752), Image.Resampling.LANCZOS)
                im_2k = im_2k.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=2))
                im_2k.save(img_path, format="JPEG", quality=98, subsampling=0)
            ok_loc, sz_loc = True, os.path.getsize(img_path)
        except Exception:
            pass
    if ok_loc and os.path.exists(img_path):
        refs_dir = os.path.join(os.path.dirname(img_path), "refs")
        os.makedirs(refs_dir, exist_ok=True)
        shutil.copy2(img_path, os.path.join(refs_dir, os.path.basename(img_path)))
    return ok_loc, sz_loc


def generate_variant_ref_image_in_page(page, wiz, cookie_hdr, dl_headers, task):
    """Generate a unique 9:16 reference image or AI Thumbnail (ogiZ0b / BELUGA) and download it at 2K (1536x2752) via SPrCad."""
    pid = task["pid"]
    v_key = task["v_key"]
    project_id = task["project_id"]
    out_file = task["out_file"]
    prof_name = task.get("worker_profile") or ""

    ok_sub, gen_uuid, img_url, err_sub = _submit_ogi_image_request(
        page=page,
        wiz=wiz,
        project_id=project_id,
        prod_uuids=task.get("prod_uuids") or [],
        char_id=task.get("char_id") or "",
        prompt_str=task["prompt_str"],
        allow_multi_refs=bool(task.get("allow_multi_refs")),
        cookie_hdr=cookie_hdr,
        prof_name=prof_name,
    )
    if not ok_sub or not gen_uuid:
        return False, None, err_sub

    with cffi_requests.Session(impersonate="chrome131") as s:
        if not img_url:
            for _ in range(15):
                time.sleep(2.5)
                ok_p, inner_p, _ = call_flow_rpc_cffi(s, cookie_hdr, wiz, project_id, "as29s", [gen_uuid, None, [2]])
                if ok_p:
                    img_url = find_img_url(inner_p)
                    if img_url:
                        break
        if not img_url:
            return False, None, f"No image URL for {gen_uuid}"

        # Step 2 (Standard Pipeline): Upsample & download at 2K (1536x2752) via SPrCad (0 credits) with circuit-breaker
        ok_2k, nbytes_2k, err_2k = False, 0, "SPrCad cooldown"
        with _SPRCAD_LOCK:
            spr_open = time.time() < _SPRCAD_SKIP_UNTIL[0]
        if hasattr(gvt, "is_sprcad_circuit_open") and gvt.is_sprcad_circuit_open():
            spr_open = True
        if not spr_open:
            for attempt_2k in range(1, 3):
                ok_2k, nbytes_2k, err_2k = upsample_image_2k_in_page(
                    page, wiz, project_id, gen_uuid, out_file, cookie_hdr=cookie_hdr, prof_name=prof_name
                )
                with _SPRCAD_LOCK:
                    if ok_2k and nbytes_2k > 50000:
                        _SPRCAD_CONSEC_FAILS[0] = 0
                        if hasattr(gvt, "record_sprcad_result"):
                            gvt.record_sprcad_result(True)
                        break
                    _SPRCAD_CONSEC_FAILS[0] += 1
                    if _SPRCAD_CONSEC_FAILS[0] >= 3:
                        _SPRCAD_SKIP_UNTIL[0] = max(_SPRCAD_SKIP_UNTIL[0], time.time() + 300.0)
                if hasattr(gvt, "record_sprcad_result"):
                    gvt.record_sprcad_result(False, str(err_2k or ""))
                if "TOO_MUCH_TRAFFIC" in str(err_2k or "").upper() or "[8]" in str(err_2k or ""):
                    break
                if attempt_2k < 2:
                    time.sleep(2.0)

        if not (ok_2k and nbytes_2k > 50000):
            if task.get("require_native_2k"):
                return False, None, f"Native 2K download required; SPrCad failed: {err_2k}"
            print(f"   [2K-FALLBACK {pid} | {v_key}] SPrCad returned {err_2k}, downloading & upscaling to 2K (1536x2752)...", flush=True)
            r_img = s.get(img_url, headers=dl_headers, timeout=60, allow_redirects=True)
            if r_img.status_code != 200 or len(r_img.content) < 5000:
                return False, None, f"Download HTTP {r_img.status_code}"
            with open(out_file, "wb") as f:
                f.write(r_img.content)
            _, nbytes_2k = _local_upscale_2k_fallback(out_file)
            if nbytes_2k <= 0:
                nbytes_2k = len(r_img.content)

    refs_dir = os.path.join(os.path.dirname(out_file), "refs")
    os.makedirs(refs_dir, exist_ok=True)
    shutil.copy2(out_file, os.path.join(refs_dir, os.path.basename(out_file)))

    # Step 2b (Standard Pipeline): Upload the downloaded 2K (1536x2752) Ref Image back to Google Flow via maseQ
    # so all 3 video scenes use the true 2K uploaded Reference Image + Product Image + Voice!
    if not task.get("skip_reupload_2k"):
        uploaded_2k_ok = False
        for u2k_try in range(1, 4):
            try:
                ok_u2k, uuid_2k, err_u2k = upload_single_product_ref_in_page(
                    page, wiz, project_id, out_file, quality=98, cookie_hdr=cookie_hdr, prof_name=prof_name
                )
                if ok_u2k and uuid_2k:
                    gen_uuid = uuid_2k
                    uploaded_2k_ok = True
                    break
            except Exception as e_u2k:
                err_u2k = str(e_u2k)
            if u2k_try < 3:
                time.sleep(2.0)
        if not uploaded_2k_ok:
            print(f"   [WARN {pid} | {v_key}] 2K re-upload fallback to gen_uuid", flush=True)

    upload_label = "downloaded 2K (explicit upload follows)" if task.get("skip_reupload_2k") else "downloaded 2K & re-uploaded 2K Ref Image"
    print(f"🖼️ [{pid} | {v_key.upper()}] Generated, {upload_label} {os.path.basename(out_file)} ({nbytes_2k//1024} KB) -> media_uuid={gen_uuid}", flush=True)
    return True, gen_uuid, None


def submit_scene_in_page(page, wiz, task):
    """Mint reCAPTCHA Enterprise token AND execute MZZa6b fetch with ALL 3 ingredients: [2K ref_uuid, prod_uuid] + [voice_id]."""
    pid = task["pid"]
    sc = task["sc"]
    sc_id = sc["id"]
    project_id = task["project_id"]
    ref_uuid = task["ref_uuid"]
    prod_uuid = task.get("prod_uuid")
    voice_id = "" if task.get("_drop_voice_id") else task["voice_id"]
    worker_prof = task.get("worker_profile") or ""
    if voice_id and worker_prof:
        try:
            import character_library_manager as _clm_mt
            voice_id = _clm_mt.resolve_voice_id_for_account(voice_id, worker_prof)
        except Exception:
            pass

    if (not prod_uuid or prod_uuid == ref_uuid) and not task.get("storyboard_only"):
        return False, None, "Missing prod_uuid (Standard workflow requires [2K Ref Image + Product Image + Voice])"

    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    h_prompt = [None, None, [[[sc["prompt"]]]]]
    l_item = [None, None, None, None, m_uuid, wf_uuid]
    x_batch = [b_uuid, 1]
    dur_sec = int(sc.get("duration_sec") or task.get("scene_duration_sec") or 10)
    raw_model = str(sc.get("model_key") or task.get("model_key") or task.get("flow_video_model") or "").strip().lower()
    if raw_model.endswith(("_6s", "_8s", "_10s")):
        model_key = sc.get("model_key") or task.get("model_key")
    elif "1.2" in raw_model or "macaron" in raw_model:
        model_key = f"macaron_cookie_r2v_{dur_sec}s"
    else:
        model_key = "abra_r2v_6s" if dur_sec <= 6 else ("abra_r2v_8s" if dur_sec <= 8 else "abra_r2v_10s")
    aspect_int = 1  # 9:16 portrait
    ref_list = [[None, ref_uuid]] if task.get("storyboard_only") else [[None, ref_uuid], [None, prod_uuid]]
    voice_list = [[voice_id]] if voice_id else []
    item_g = [
        h_prompt,
        ref_list,
        model_key,
        aspect_int,
        None,
        l_item,
        None,
        voice_list,
        None,
        [],
        [],
    ]

    def _build_mzza(rcap):
        k_ctx = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
        return [[item_g], k_ctx, x_batch]

    ok_v, inner_v, err_v = _post_flow_rpc(
        page,
        wiz,
        project_id,
        "MZZa6b",
        _build_mzza,
        "VIDEO_GENERATION",
        cookie_hdr=task.get("cookie_hdr") or "",
        prof_name=worker_prof,
    )
    if not ok_v or not isinstance(inner_v, list):
        return False, None, f"{err_v}"

    ret_uuid = m_uuid
    try:
        if len(inner_v) > 3 and isinstance(inner_v[3], list) and inner_v[3]:
            cand_u = inner_v[3][0][0]
            if isinstance(cand_u, str) and len(cand_u) >= 32:
                ret_uuid = cand_u
    except Exception:
        pass
    credits_left = inner_v[1] if len(inner_v) > 1 and isinstance(inner_v[1], int) else None
    if credits_left is not None and worker_prof and hasattr(gvt, "update_flow_account_credits_realtime"):
        gvt.update_flow_account_credits_realtime(worker_prof, credits_left)
    task["_last_credits_left"] = credits_left
    prod_tag = f"+prod={prod_uuid[:8]}" if prod_uuid else ""
    print(f"🚀 [{pid} | {sc_id}] Submitted MZZa6b (ref={ref_uuid[:8]}{prod_tag} | TK:{worker_prof}) -> media_uuid={ret_uuid} (Credits: {credits_left})", flush=True)
    return True, ret_uuid, None


def submit_upsample_1080p_in_page(page, wiz, task):
    """Submit 1080p video upsample via p0UkFb (veo_3_1_upsampler_1080p, resolution=2, 0 credits)."""
    pid = task["pid"]
    sc_id = task["sc"]["id"]
    project_id = task["project_id"]
    base_video_uuid = task["base_video_uuid"]

    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    l_item = [None, None, None, None, m_uuid, wf_uuid]
    item_x = [None] * 32
    item_x[0] = [None, base_video_uuid]          # field 1: baseVideoId
    item_x[2] = 1                                # field 3: aspectRatio (1 = 9:16 portrait)
    item_x[4] = l_item                           # field 5: metadata / destination
    item_x[6] = 2                                # field 7: resolution (2 = 1080p)
    item_x[31] = "veo_3_1_upsampler_1080p"       # field 32: videoModelKey (0 credits)

    def _build_p0uk(rcap):
        k_ctx = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
        return [[item_x], k_ctx, [b_uuid, 1]]

    ok_v, inner_v, err_v = _post_flow_rpc(
        page,
        wiz,
        project_id,
        "p0UkFb",
        _build_p0uk,
        "VIDEO_GENERATION",
        cookie_hdr=task.get("cookie_hdr") or "",
        prof_name=task.get("worker_profile") or "",
    )
    if not ok_v or not isinstance(inner_v, list):
        return False, None, (err_v if str(err_v or "").startswith("p0UkFb") else f"p0UkFb {err_v}")

    upsampled_uuid = f"{base_video_uuid}_upsampled"
    try:
        if len(inner_v) > 3 and isinstance(inner_v[3], list) and inner_v[3]:
            cand_u = inner_v[3][0][0]
            if isinstance(cand_u, str) and len(cand_u) >= 32:
                upsampled_uuid = cand_u
    except Exception:
        pass
    print(f"✨ [{pid} | {sc_id}] Submitted 1080p Upsample p0UkFb -> {upsampled_uuid} (0 credits)", flush=True)
    return True, upsampled_uuid, None


def poll_and_download_one(default_cookie_hdr, default_wiz, default_dl_headers, task):
    cookie_hdr = task.get("cookie_hdr") or default_cookie_hdr
    wiz = task.get("wiz") or default_wiz
    dl_headers = task.get("dl_headers") or default_dl_headers
    uid = task["media_uuid"]
    project_id = task["project_id"]
    out_mp4 = task["out_mp4"]
    stage = task.get("stage", "upsample_1080p" if str(uid).endswith("_upsampled") else "base_720p")

    with cffi_requests.Session(impersonate="chrome131") as s:
        ok_p, inner_p, err_p = call_flow_rpc_cffi(s, cookie_hdr, wiz, project_id, "as29s", [uid, None, [2]])
        if not ok_p or not isinstance(inner_p, list):
            return f"rpc_err:{str(err_p)[:180]}", None

        v_urls = gvt._find_signed_flow_urls(inner_p, "https://flow-content.google/video/")
        if not v_urls:
            v_urls = gvt._find_signed_flow_urls(inner_p, "https://storage.googleapis.com/")
        if v_urls:
            v_url = v_urls[0]
            r_dl = None
            last_dl_err = "HTTP 0"
            for dl_try in range(1, 4):
                try:
                    r_dl = s.get(v_url, headers=dl_headers, timeout=120, allow_redirects=True)
                    if r_dl.status_code != 200 or len(r_dl.content) <= 10000:
                        r_dl = s.get(
                            v_url,
                            headers={"Referer": "https://flow.google.com/", "User-Agent": wiz["ua"]},
                            timeout=120,
                            allow_redirects=True,
                        )
                    if r_dl.status_code == 200 and len(r_dl.content) > 10000:
                        break
                    last_dl_err = f"HTTP {r_dl.status_code}"
                except Exception as exc_dl:
                    last_dl_err = f"EXC_{type(exc_dl).__name__}"
                if dl_try < 3:
                    time.sleep((1.0 * dl_try) + random.uniform(0.05, 0.35))

            if r_dl is not None and r_dl.status_code == 200 and len(r_dl.content) > 10000:
                if stage == "base_720p":
                    # Save 720p backup in case 1080p upsample fails, then transition to 1080p upsample
                    with open(out_mp4 + ".720p.tmp", "wb") as f:
                        f.write(r_dl.content)
                    return "ready_for_1080p", len(r_dl.content)
                else:
                    with open(out_mp4, "wb") as f:
                        f.write(r_dl.content)
                    if os.path.exists(out_mp4 + ".720p.tmp"):
                        try:
                            os.remove(out_mp4 + ".720p.tmp")
                        except OSError:
                            pass
                    return "done", len(r_dl.content)
            return f"dl_err:{last_dl_err}", None

    if hasattr(gvt, "extract_flow_as29s_error"):
        is_failed, status_code, detail = gvt.extract_flow_as29s_error(inner_p)
        if is_failed:
            print(f"   [POLL-ERR {uid[:8]}] code={status_code} | {detail[:220]}", flush=True)
            code_lbl = status_code if status_code is not None else "err"
            return (f"failed_{code_lbl}:{detail[:180]}" if detail else f"failed_{code_lbl}"), None
    status_code = None
    try:
        status_code = inner_p[5][8][0]
    except Exception:
        pass
    if status_code is None:
        try:
            status_code = inner_p[0][0][5][8][0]
        except Exception:
            pass
    if status_code is None:
        try:
            status_code = inner_p[0][0][3]
        except Exception:
            pass
    if status_code is None:
        try:
            status_code = inner_p[5][7][0]
        except Exception:
            pass
    raw_s = json.dumps(inner_p, ensure_ascii=False)
    pub_match = None
    try:
        import re as _re_mt
        m_pub = _re_mt.search(r"PUBLIC_ERROR_[A-Z0-9_]+", raw_s)
        if m_pub:
            pub_match = m_pub.group(0)
    except Exception:
        pass
    if status_code in (3, 4, 5, 6, 7, 8, "FAILED", "CANCELED", "ERROR", "REJECTED"):
        return (f"failed_{status_code}:{pub_match}" if pub_match else f"failed_{status_code}"), None
    if any(tok in raw_s.upper() for tok in ("PUBLIC_ERROR_", "POLICY_VIOLATION", "SAFETY_ERROR", "GENERATION_FAILED", "MEDIA_GENERATION_FAILED")) or inner_p == [None] or inner_p == []:
        print(f"   [POLL-ERR {uid[:8]}] {raw_s[:220]}", flush=True)
        return (f"failed_err:{pub_match}" if pub_match else "failed_err"), None
    return f"running_{status_code}", None


THUMB_FUTURES_BY_KEY = {}


def run_ffmpeg_build(pid, pdir, v_key):
    with STATE_LOCK:
        th_fut = THUMB_FUTURES_BY_KEY.get((pid, v_key))
    if th_fut is not None and not th_fut.done():
        try:
            th_fut.result(timeout=240)
        except Exception:
            pass
    spec_path = os.path.join(pdir, f"spec_{v_key}.json")
    print(f"🎞️ [FFMPEG-THREAD | {pid} | {v_key.upper()}] Building Final 30s 1080p video...", flush=True)
    res = subprocess.run(
        [sys.executable, BUILD_FINAL_SCRIPT, spec_path, "--skip-auto-thumb", "--inject-existing-thumb"],
        cwd=pdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        err_tail = (res.stderr or res.stdout or "")[-400:].strip()
        print(f"❌ [FFMPEG-THREAD | {pid} | {v_key.upper()}] Failed: {err_tail}", flush=True)
        if hasattr(gvt, "record_diagnostic_error"):
            gvt.record_diagnostic_error("FFmpegBuild", target=pid, scene=v_key, error_text=err_tail)
        try:
            st_p = os.path.join(pdir, "flow_state.json")
            with STATE_LOCK:
                cur_st = json.load(open(st_p, encoding="utf-8")) if os.path.exists(st_p) else {}
                cur_st.setdefault("scene_errors", {})[f"{v_key}_ffmpeg"] = {
                    "account": "local_ffmpeg",
                    "message": f"Lỗi ghép FFmpeg: {err_tail[:220]}",
                    "terminal": True,
                    "updated_at": time.strftime("%H:%M:%S"),
                }
                gvt.atomic_write_json(st_p, cur_st)
        except Exception:
            pass
        return False
    print(f"✅ [FFMPEG-THREAD | {pid} | {v_key.upper()}] {res.stdout.strip()}", flush=True)
    safe_sync_ui()
    return True


def check_and_queue_ffmpeg(ffmpeg_pool, ffmpeg_futures, pid, pdir, v_key, scenes):
    key = f"{pid}_{v_key}"
    with STATE_LOCK:
        if key in FFMPEG_SUBMITTED:
            return
        final_mp4 = os.path.join(WS_DIR, "final_videos", get_final_video_filename(pid, v_key))
        if os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 50000:
            FFMPEG_SUBMITTED.add(key)
            return
        all_ready = all(
            os.path.exists(os.path.join(pdir, sc["file"]))
            and os.path.getsize(os.path.join(pdir, sc["file"])) > 50000
            for sc in scenes
        )
        if not all_ready:
            return
        FFMPEG_SUBMITTED.add(key)
    fut = ffmpeg_pool.submit(run_ffmpeg_build, pid, pdir, v_key)
    ffmpeg_futures.append(fut)


def save_prod_state(pdir, state, refs_state=None):
    with STATE_LOCK:
        state_path = os.path.join(pdir, "flow_state.json")
        if hasattr(gvt, "atomic_write_json"):
            gvt.atomic_write_json(state_path, state)
        else:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        if refs_state is not None:
            refs_path = os.path.join(pdir, "flow_refs_state.json")
            if hasattr(gvt, "atomic_write_json"):
                gvt.atomic_write_json(refs_path, refs_state)
            else:
                with open(refs_path, "w", encoding="utf-8") as f:
                    json.dump(refs_state, f, ensure_ascii=False, indent=2)


def is_ref_image_2k(img_path):
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            return w >= 1200 and h >= 2000
    except Exception:
        return False


def _resolve_default_flow_pid(prof_name: str = "") -> str:
    if _esm is not None:
        try:
            pid_v = str(_esm.get_default_flow_project_id(prof_name or PROF_NAME) or "").strip()
            if pid_v:
                return pid_v
        except Exception:
            pass
    return str(getattr(gvt, "DEFAULT_PROJECT_ID", "") or "").strip()


def _http_check_flow_cookies(cookies_list: list, target_pid: str = "", timeout_sec: float = 10.0) -> tuple:
    """Kiểm tra nhanh cookie Google Flow bằng HTTP (không mở Chrome) để loại sớm tài khoản hết hạn."""
    if not cookies_list:
        return False, "empty_cookies"
    chosen = {}
    for c in cookies_list:
        nm = str(c.get("name") or "")
        val = str(c.get("value") or "")
        if not nm or not val or "GRECAPTCHA" in nm.upper():
            continue
        dom = str(c.get("domain") or "").lower()
        rank = 3 if "flow.google" in dom else (2 if "labs.google" in dom else 1)
        if nm not in chosen or rank >= chosen[nm][0]:
            chosen[nm] = (rank, val)
    hdr = "; ".join(f"{k}={v[1]}" for k, v in chosen.items())
    if not hdr:
        return False, "no_valid_cookie_pairs"

    urls = []
    if target_pid:
        urls.append(f"https://flow.google.com/project/{target_pid}")
    urls.append("https://flow.google.com/")
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    for idx_u, u in enumerate(urls):
        try:
            resp = cffi_requests.get(
                u,
                headers={"Cookie": hdr, "User-Agent": ua, "Accept": "text/html,application/xhtml+xml"},
                timeout=timeout_sec,
                allow_redirects=True,
                impersonate="chrome131",
            )
            final_url = str(getattr(resp, "url", "") or "")
            if "accounts.google.com" in final_url or "CookieMismatch" in final_url:
                return False, f"auth_redirect:{final_url[:80]}"
            body = resp.text or ""
            if '"SNlM0e"' in body:
                m_pid = __import__("re").search(r"/project/([0-9a-fA-F-]{20,})", final_url or "")
                found_pid = m_pid.group(1) if m_pid else target_pid
                return True, found_pid
            if resp.status_code == 404 and idx_u == 0 and len(urls) > 1:
                continue
            if idx_u + 1 >= len(urls):
                has_lsid = any(
                    str(c.get("name", "") or "") in ("LSID", "__Host-1PLSID", "__Host-3PLSID")
                    for c in (cookies_list or [])
                    if isinstance(c, dict)
                )
                if resp.status_code == 200 and has_lsid:
                    return True, f"needs_chrome_refresh:{target_pid}"
        except Exception as exc:
            if idx_u + 1 >= len(urls):
                # Lỗi mạng thoáng qua chưa chắc cookie chết -> cho phép Chrome thử tiếp
                return True, f"net_warn:{type(exc).__name__}"
    return False, "missing_SNlM0e"


def _build_variant_followup_tasks(t, gen_uuid, u_id, eff_proj_id, owner_acc, pdir, flow_video_model=""):
    """Build scene video + optional AI thumbnail tasks right after a 2K reference image is ready."""
    pid = t["pid"]
    v_key = t["v_key"]
    base_char = t["base_char"]
    new_tasks = []
    for sc in (t.get("scenes") or []):
        sc_id = sc["id"]
        out_mp4 = os.path.join(pdir, sc["file"])
        if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 50000:
            continue
        new_tasks.append({
            "type": "vid_scene",
            "stage": "base_720p",
            "key": f"{pid}_{sc_id}",
            "pid": pid,
            "pdir": pdir,
            "v_key": v_key,
            "base_char": base_char,
            "primary_prod_img": t["primary_prod_img"],
            "ref_img_abs": t["out_file"],
            "sc": sc,
            "scene_duration_sec": int(sc.get("duration_sec") or t.get("scene_duration_sec") or 10),
            "flow_video_model": flow_video_model,
            "project_id": eff_proj_id,
            "owner_account": owner_acc,
            "ref_uuid": gen_uuid,
            "prod_uuid": u_id,
            "voice_id": t["voice_id"],
            "out_mp4": out_mp4,
            "retries": 0,
            "media_uuid": None,
            "submitted_at": 0,
        })
    return new_tasks


def _parse_cli_args(argv):
    prof_override = ""
    profiles_override = []
    pids = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in ("--profile", "-p") and i + 1 < len(argv):
            prof_override = str(argv[i + 1] or "").strip()
            i += 2
            continue
        if tok.startswith("--profile="):
            prof_override = str(tok.split("=", 1)[1] or "").strip()
            i += 1
            continue
        if tok in ("--profiles",) and i + 1 < len(argv):
            profiles_override = [p.strip() for p in str(argv[i + 1] or "").split(",") if p.strip()]
            i += 2
            continue
        if tok.startswith("--profiles="):
            profiles_override = [p.strip() for p in str(tok.split("=", 1)[1] or "").split(",") if p.strip()]
            i += 1
            continue
        if tok and not tok.startswith("-"):
            pids.append(tok)
        i += 1
    return prof_override, profiles_override, pids


class _PerPidLogRouter:
    """Tee stdout lines to each active product's `projects/<pid>/pipeline_run.log` so bulk runs show live logs on every product."""

    def __init__(self, orig_stream, active_pids_ref: list):
        self._orig = orig_stream
        self._pids_ref = active_pids_ref
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, data: str):
        ret = self._orig.write(data)
        if not data:
            return ret
        with self._lock:
            self._buf += data
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                self._route_line(line + "\n")
        return ret

    def _route_line(self, line: str):
        s = line.strip()
        if not s:
            return
        cur_pids = list(self._pids_ref)
        if not cur_pids:
            return
        matched = [p for p in cur_pids if p in line or (len(p) >= 8 and f"{p[-4:]}:" in line)]
        is_global = any(k in line for k in ("⚙️", "=== ", "⛔", "🎉", "⚠️ PIPELINE", "✅ Extension Captcha"))
        targets = matched if matched else (cur_pids if is_global else [])
        for pid_t in targets:
            # Skip first_pid if stdout is already redirected directly to first_pid/pipeline_run.log by Popen
            if pid_t == cur_pids[0] and not sys.stdout.isatty():
                continue
            lp = os.path.join(PROJECTS_DIR, pid_t, "pipeline_run.log")
            try:
                if os.path.isdir(os.path.dirname(lp)):
                    with open(lp, "a", encoding="utf-8", errors="replace") as fh:
                        fh.write(line)
            except Exception:
                pass

    def flush(self):
        return self._orig.flush()

    def isatty(self):
        return getattr(self._orig, "isatty", lambda: False)()

    def __getattr__(self, name):
        return getattr(self._orig, name)


def main():
    global PROF_NAME, profile_dir, cookies_file
    cli_profile, cli_profiles, cli_pids = _parse_cli_args(sys.argv[1:])
    if cli_pids:
        only_pids = list(dict.fromkeys(cli_pids))
    else:
        discovered_pids = []
        if os.path.isdir(PROJECTS_DIR):
            for _d in sorted(os.listdir(PROJECTS_DIR)):
                if os.path.isfile(os.path.join(PROJECTS_DIR, _d, "prompts.json")):
                    discovered_pids.append(_d)
        only_pids = discovered_pids if discovered_pids else list(ALL_PIDS)

    orig_stdout = sys.stdout
    sys.stdout = _PerPidLogRouter(orig_stdout, only_pids)

    cfg = _esm.load_engine_settings() if _esm is not None else {}
    VIDEO_PROVIDER = str(cfg.get("video_provider") or "google_flow").strip().lower()
    VIDS_MODEL = str(cfg.get("google_vids_model") or "omni").strip().lower()
    FLOW_VIDEO_MODEL = str(cfg.get("flow_video_model") or "").strip()
    FFMPEG_WORKERS = int(cfg.get("ffmpeg_render_workers") or 4)
    multi_acc_enabled = (len(cli_profiles) > 1) or (bool(cfg.get("multi_account_enabled", True)) and not bool(cli_profile))
    avail_accs = (_esm.list_available_flow_accounts() if (_esm is not None and hasattr(_esm, "list_available_flow_accounts")) else None) or []
    detected_accs = [
        a for a in (avail_accs or cfg.get("detected_flow_accounts") or [])
        if isinstance(a, dict) and str(a.get("auth_state") or "").lower() not in ("logging_in", "login_required")
    ]
    if not detected_accs:
        detected_accs = [{"name": f"Google_{PROF_NAME}", "profile_name": PROF_NAME, "active": True}]
    acc_by_prof = {str(a.get("profile_name") or "").strip(): a for a in detected_accs if str(a.get("profile_name") or "").strip()}
    sel_prof = str(
        (cli_profiles[0] if cli_profiles else "")
        or cli_profile
        or os.environ.get("FLOW_PROFILE_NAME")
        or (cfg.get("selected_flow_profile") if not multi_acc_enabled else "")
        or ""
    ).strip()
    if sel_prof and sel_prof not in acc_by_prof and not cli_profile and not cli_profiles:
        print(f"ℹ️ [CONFIG] Tài khoản chọn cũ '{sel_prof}' không có trên máy này -> tự chuyển sang tài khoản đang hoạt động.", flush=True)
        sel_prof = ""
    if sel_prof:
        PROF_NAME = sel_prof
    elif acc_by_prof:
        PROF_NAME = next(iter(acc_by_prof.keys()))
    sh_dir_sel = gvt._resolve_flow_shared_dir(PROF_NAME)
    profile_dir, cookies_file = profile_paths(sh_dir_sel, PROF_NAME)

    if cli_profiles:
        active_flow_accs = []
        for cp in cli_profiles:
            if cp in acc_by_prof:
                active_flow_accs.append(acc_by_prof[cp])
            else:
                active_flow_accs.append({
                    "name": f"Google_{cp}",
                    "profile_name": cp,
                    "project_id": _resolve_default_flow_pid(cp),
                    "active": True,
                })
    elif sel_prof and not multi_acc_enabled:
        active_flow_accs = [acc_by_prof[sel_prof]] if sel_prof in acc_by_prof else [{
            "name": f"Google_{sel_prof}",
            "profile_name": sel_prof,
            "project_id": _resolve_default_flow_pid(sel_prof),
            "active": True,
        }]
    else:
        sel_multi = [str(p).strip() for p in (cfg.get("selected_flow_profiles") or []) if str(p).strip()]
        valid_sel_multi = [acc_by_prof[p] for p in sel_multi if p in acc_by_prof and acc_by_prof[p].get("active", True)]
        if multi_acc_enabled and valid_sel_multi:
            if len(valid_sel_multi) < len(sel_multi):
                missing_p = [p for p in sel_multi if p not in acc_by_prof]
                print(f"ℹ️ [CONFIG] Bỏ qua profile không tồn tại/chưa đăng nhập: {missing_p}", flush=True)
            active_flow_accs = valid_sel_multi
        else:
            if multi_acc_enabled and sel_multi and not valid_sel_multi:
                print(f"ℹ️ [CONFIG] Danh sách profile cũ {sel_multi} không khớp máy hiện tại -> tự động dùng tất cả tài khoản Google Flow đang bật!", flush=True)
            active_flow_accs = [a for a in detected_accs if a.get("active", True)] if multi_acc_enabled else detected_accs[:1]
    if not active_flow_accs:
        active_flow_accs = [{"name": f"Google_{PROF_NAME}", "profile_name": PROF_NAME, "active": True}]

    eff_cfg = dict(cfg)
    eff_cfg["detected_flow_accounts"] = active_flow_accs
    eff_cfg["multi_account_enabled"] = multi_acc_enabled
    eff_cfg["selected_flow_profiles"] = [a["profile_name"] for a in active_flow_accs]
    eff_flow = _esm.get_effective_flow_concurrency(cfg=eff_cfg) if (_esm is not None and hasattr(_esm, "get_effective_flow_concurrency")) else {}
    MAX_INFLIGHT = int(eff_flow.get("max_total_inflight") or cfg.get("max_total_inflight") or 10)
    MAX_INFLIGHT_PER_ACC = int(eff_flow.get("max_inflight_per_account") or cfg.get("max_inflight_per_account") or 5)
    raw_delay_sec = float(eff_flow.get("submit_delay_sec") or cfg.get("submit_delay_sec") or 4.5)
    SUBMIT_DELAY_SEC = max(4.2, raw_delay_sec) if multi_acc_enabled else max(4.0, raw_delay_sec)
    GLOBAL_STAGGER_SEC = max(0.85, float(eff_flow.get("global_submit_stagger_sec") or cfg.get("global_submit_stagger_sec") or 0.7))
    UPSCALE_DL_WORKERS = int(eff_flow.get("upscale_download_workers") or cfg.get("upscale_download_workers") or 6)
    THUMB_FUTURES_BY_KEY.clear()

    print(
        f"⚙️ [ENGINE CONFIG] Video Provider={VIDEO_PROVIDER} ({VIDS_MODEL if VIDEO_PROVIDER == 'google_vids' else (FLOW_VIDEO_MODEL or 'flow')}) | "
        f"FFmpeg Workers={FFMPEG_WORKERS} | Max Gen Inflight={MAX_INFLIGHT} (+{UPSCALE_DL_WORKERS} Upscale/DL) | "
        f"Delay/TK={SUBMIT_DELAY_SEC}s (Global stagger={GLOBAL_STAGGER_SEC}s) | Active Accounts={len(active_flow_accs)} ({', '.join(a['profile_name'] for a in active_flow_accs)})",
        flush=True,
    )

    ffmpeg_pool = concurrent.futures.ThreadPoolExecutor(max_workers=FFMPEG_WORKERS)
    poll_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(48, MAX_INFLIGHT + UPSCALE_DL_WORKERS + 8))
    thumb_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(2, min(4, len(active_flow_accs))))
    vids_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(4, min(24, MAX_INFLIGHT)))
    vids_rr_box = [0]
    thumb_rr_box = [0]
    acc_last_submit_ts = {}

    def _run_google_vids_scene_task(task_item: dict, prof_name: str, fb_profs: list, model_name: str):
        import google_vids_client as _gvc
        client = _gvc.get_google_vids_client()
        imgs = [p for p in [task_item.get("ref_img_abs"), task_item.get("primary_prod_img")] if p and os.path.isfile(p)]
        if task_item.get("sc", {}).get("storyboard_only") and imgs:
            imgs = imgs[:1]
        dur = int(task_item.get("scene_duration_sec") or (task_item.get("sc") or {}).get("duration_sec") or 10)
        return client.generate_video(
            out_mp4=task_item["out_mp4"],
            prompt=str((task_item.get("sc") or {}).get("prompt") or ""),
            image_paths=imgs,
            profile_name=prof_name,
            fallback_profiles=fb_profs,
            model=model_name,
            aspect_ratio="9:16",
            resolution="1080p",
            duration_sec=dur,
            ingredient_role="product",
            max_retries=2,
        )
    ffmpeg_futures = []

    QUEUE_LOCK = threading.RLock()
    pending_queue = []
    inflight_tasks = {}
    in_submit_tasks = {}
    prod_meta = {}
    _LAST_HB_TS = [0.0]

    def write_pipeline_heartbeat(step_text: str, is_running: bool = True, force: bool = False):
        now_t = time.time()
        with QUEUE_LOCK:
            if is_running and not force and (now_t - _LAST_HB_TS[0]) < 0.8:
                return
            _LAST_HB_TS[0] = now_t
            now_s = time.strftime("%H:%M:%S")
            active_list = [
                {
                    "key": tk.get("key"),
                    "pid": tk.get("pid"),
                    "v_key": tk.get("v_key"),
                    "sc_id": (tk.get("sc") or {}).get("id", tk.get("v_key")),
                    "stage": tk.get("stage", tk.get("type")),
                    "account": tk.get("account_name", PROF_NAME),
                    "elapsed_sec": int(time.time() - (tk.get("submitted_at") or time.time())),
                }
                for tk in list(inflight_tasks.values())
            ]
            queued_snap = list(pending_queue)
        for p_id in only_pids:
            p_dir = os.path.join(PROJECTS_DIR, p_id)
            if not os.path.isdir(p_dir):
                continue
            p_inflight = [x for x in active_list if x["pid"] == p_id]
            p_queued = [q for q in queued_snap if q.get("pid") == p_id]
            st_obj = {
                "pid": p_id,
                "pid_os": os.getpid(),
                "is_running": is_running,
                "inflight_count": len(p_inflight),
                "queued_count": len(p_queued),
                "active_tasks": p_inflight,
                "accounts_active": [a["profile_name"] for a in active_flow_accs],
                "ffmpeg_workers": FFMPEG_WORKERS,
                "current_step_text": step_text,
                "updated_at": now_s,
            }
            try:
                st_fp = os.path.join(p_dir, "pipeline_status.json")
                if hasattr(gvt, "atomic_write_json"):
                    gvt.atomic_write_json(st_fp, st_obj)
                else:
                    with open(st_fp, "w", encoding="utf-8") as sf:
                        json.dump(st_obj, sf, ensure_ascii=False, indent=2)
            except Exception:
                pass

    initial_ffmpeg_checks = []

    def _enqueue_single_product(pid: str):
        pdir = os.path.join(PROJECTS_DIR, pid)
        prompts_file_p = os.path.join(pdir, "prompts.json")
        if not os.path.isfile(prompts_file_p):
            print(f"[SKIP] {pid}: chưa có prompts.json, bỏ qua.", flush=True)
            return
        marker_clean = os.path.join(pdir, ".cleaned_new")
        if os.path.exists(marker_clean):
            try:
                os.remove(marker_clean)
            except OSError:
                pass
        prompts_data = json.load(open(prompts_file_p, encoding="utf-8"))
        refs_path = os.path.join(pdir, "flow_refs_state.json")
        refs_state = json.load(open(refs_path, encoding="utf-8")) if os.path.exists(refs_path) else {"uploaded_prod_refs": {}, "variants": {}}
        refs_state.setdefault("variants", {})
        refs_state.setdefault("uploaded_prod_refs", {})
        state_path = os.path.join(pdir, "flow_state.json")
        state = {"uploaded_refs": {}, "scene_uuids": {}}
        if os.path.exists(state_path):
            try:
                state = json.load(open(state_path, encoding="utf-8"))
            except Exception:
                pass
        # Xoá trạng thái failed_scenes cũ khi người dùng bấm chạy lại dự án này
        state["failed_scenes"] = []
        prod_meta[pid] = (pdir, prompts_data, state, refs_state)

        only_vkeys_env = {x.strip() for x in str(os.environ.get("FLOW_ONLY_VKEYS") or "").split(",") if x.strip()}
        for v_key in list(prompts_data.get("videos", {}).keys()):
            if v_key not in prompts_data.get("videos", {}):
                continue
            if only_vkeys_env and v_key not in only_vkeys_env:
                continue
            v_info = prompts_data["videos"][v_key]
            char_key = v_info.get("character", "nv1")
            ck_low = (char_key or "").lower()
            m_nv = __import__("re").search(r"(nv\d+)", ck_low) or __import__("re").search(r"(nv\d+)", v_key.lower())
            base_char = m_nv.group(1) if m_nv else (ck_low if ck_low else "nv1")
            tpl_id_low = str(v_info.get("template_id") or prompts_data.get("template_id") or "").lower()
            is_pov_only = bool(v_info.get("pov_only") or "pov" in tpl_id_low or tpl_id_low == "do_an_vat")
            scene_dur_sec = int(v_info.get("scene_duration_sec") or prompts_data.get("scene_duration_sec") or 10)
            forced_single_prof = active_flow_accs[0]["profile_name"] if (len(active_flow_accs) == 1 and not multi_acc_enabled) else ""
            project_id = _resolve_default_flow_pid(forced_single_prof) if forced_single_prof else (v_info.get("project_id") or _resolve_default_flow_pid(PROF_NAME))
            char_id = v_info.get("character_id") or ""
            voice_id = v_info.get("voice_id") or ""
            ref_img_rel = v_info["ref_image"]
            ref_img_abs = os.path.join(pdir, ref_img_rel)

            prod_uuids = refs_state.get("uploaded_prod_refs", {}).get(base_char) or refs_state.get(base_char, {}).get("prod_ref_uuids", [])
            if prod_uuids and not refs_state["uploaded_prod_refs"].get(base_char):
                refs_state["uploaded_prod_refs"][base_char] = prod_uuids[:1]
            primary_rel = (v_info.get("primary_product_refs") or prompts_data.get("primary_product_refs") or ["prod_1.jpg"])[0]
            primary_prod_img = os.path.join(pdir, "product_images", primary_rel)

            var_entry = refs_state["variants"].get(v_key, {})
            ref_uuid = var_entry.get("ref_image_uuid") or state.get("uploaded_refs", {}).get(ref_img_rel)
            has_unique_ref = bool(ref_uuid and os.path.exists(ref_img_abs) and os.path.getsize(ref_img_abs) > 10000)

            scenes = v_info["scenes"]
            char_v_code = v_info.get("char_v") or get_final_video_filename(pid, v_key).replace(f"{pid}_", "").replace(".mp4", "")
            out_thumb_proj = os.path.join(pdir, "thumbnails", f"{pid}_{char_v_code}_thumb.jpg")
            need_thumb = bool(
                cfg.get("auto_generate_thumbnail", True)
                and _esm is not None
                and not (os.path.exists(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000)
            )
            if has_unique_ref:
                state["uploaded_refs"][ref_img_rel] = ref_uuid
                save_prod_state(pdir, state, refs_state)
                needs_2k_upgrade = not is_ref_image_2k(ref_img_abs)
                if needs_2k_upgrade:
                    with QUEUE_LOCK:
                        pending_queue.append({
                            "type": "upsample_ref_2k",
                            "key": f"{pid}_{v_key}_2k",
                            "pid": pid,
                            "pdir": pdir,
                            "v_key": v_key,
                            "base_char": base_char,
                            "primary_prod_img": primary_prod_img,
                            "project_id": project_id,
                            "ref_uuid": ref_uuid,
                            "out_file": ref_img_abs,
                            "retries": 0,
                        })
                has_dl_scene = any(
                    os.path.exists(os.path.join(pdir, _s["file"])) and os.path.getsize(os.path.join(pdir, _s["file"])) > 50000
                    for _s in scenes
                )
                if need_thumb and has_dl_scene:
                    with QUEUE_LOCK:
                        pending_queue.append({
                            "type": "thumb_img",
                            "key": f"{pid}_{v_key}_thumb",
                            "pid": pid,
                            "pdir": pdir,
                            "v_key": v_key,
                            "char_v": char_v_code,
                            "base_char": base_char,
                            "primary_prod_img": primary_prod_img,
                            "project_id": project_id,
                            "char_id": char_id,
                            "ref_uuid": ref_uuid,
                            "prod_uuid": prod_uuids[0] if prod_uuids else None,
                            "out_file": out_thumb_proj,
                            "retries": 0,
                        })
                initial_ffmpeg_checks.append((pid, pdir, v_key, scenes))
            else:
                needs_2k_upgrade = False
                with QUEUE_LOCK:
                    pending_queue.append({
                        "type": "ref_img",
                        "key": f"{pid}_{v_key}_ref",
                        "pid": pid,
                        "pdir": pdir,
                        "v_key": v_key,
                        "char_v": char_v_code,
                        "base_char": base_char,
                        "primary_prod_img": primary_prod_img,
                        "project_id": project_id,
                        "char_id": char_id,
                        "pov_only": is_pov_only,
                        "scene_duration_sec": scene_dur_sec,
                        "flow_video_model": FLOW_VIDEO_MODEL,
                        "preferred_account": forced_single_prof or None,
                        "prod_uuids": prod_uuids,
                        "prompt_str": v_info["ref_image_prompt"],
                        "ref_img_rel": ref_img_rel,
                        "out_file": ref_img_abs,
                        "out_thumb_proj": out_thumb_proj,
                        "need_thumb": need_thumb,
                        "style": v_info.get("style", ""),
                        "scenes": scenes,
                        "voice_id": voice_id,
                        "retries": 0,
                    })
                continue

            for sc in scenes:
                sc_id = sc["id"]
                out_mp4 = os.path.join(pdir, sc["file"])
                if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 50000:
                    print(f"✔ [{pid} | {sc_id}] Already downloaded ({os.path.getsize(out_mp4)//1024} KB)", flush=True)
                    continue

                existing_vid_uuid = state.get("scene_uuids", {}).get(sc_id)
                can_resume_inflight = bool(has_unique_ref and not needs_2k_upgrade and existing_vid_uuid and len(inflight_tasks) < MAX_INFLIGHT)
                init_stage = "upsample_1080p" if (existing_vid_uuid and str(existing_vid_uuid).endswith("_upsampled")) else "base_720p"
                saved_scene_acc = str((state.get("scene_accounts") or {}).get(sc_id) or "").strip() if can_resume_inflight else ""
                if saved_scene_acc and not any(a["profile_name"] == saved_scene_acc for a in active_flow_accs):
                    saved_scene_acc = ""
                resumed_proj_id = (_resolve_default_flow_pid(saved_scene_acc) or project_id) if saved_scene_acc else project_id
                task_obj = {
                    "type": "vid_scene",
                    "stage": init_stage,
                    "key": f"{pid}_{sc_id}",
                    "pid": pid,
                    "pdir": pdir,
                    "v_key": v_key,
                    "base_char": base_char,
                    "primary_prod_img": primary_prod_img,
                    "ref_img_abs": ref_img_abs,
                    "sc": sc,
                    "scene_duration_sec": int(sc.get("duration_sec") or scene_dur_sec),
                    "flow_video_model": FLOW_VIDEO_MODEL,
                    "preferred_account": forced_single_prof or saved_scene_acc or None,
                    "account_name": forced_single_prof or saved_scene_acc or None,
                    "project_id": resumed_proj_id,
                    "ref_uuid": ref_uuid,
                    "prod_uuid": prod_uuids[0] if prod_uuids else None,
                    "voice_id": voice_id,
                    "out_mp4": out_mp4,
                    "retries": 0,
                    "media_uuid": existing_vid_uuid if can_resume_inflight else None,
                    "base_video_uuid": str(existing_vid_uuid).removesuffix("_upsampled") if (can_resume_inflight and init_stage == "upsample_1080p") else None,
                    "submitted_at": time.time() if can_resume_inflight else 0,
                    "_resumed_from_state": can_resume_inflight,
                }
                with QUEUE_LOCK:
                    if task_obj["media_uuid"]:
                        inflight_tasks[task_obj["key"]] = task_obj
                        print(f"🔄 [{pid} | {sc_id}] Resuming in-flight poll for media_uuid={existing_vid_uuid} ({init_stage})", flush=True)
                    else:
                        pending_queue.append(task_obj)

    for pid in list(only_pids):
        _enqueue_single_product(pid)

    print(f"\n=== MULTI-THREADED PIPELINE READY: {len(inflight_tasks)} in-flight, {len(pending_queue)} tasks queued ===", flush=True)
    write_pipeline_heartbeat(
        f"🚀 Khởi động Đa Luồng ({len(active_flow_accs)} TK Google Flow | {FFMPEG_WORKERS} luồng FFmpeg): {len(inflight_tasks)} đang xử lý, {len(pending_queue)} hàng đợi",
        is_running=True,
    )
    safe_sync_ui()

    import socket
    try:
        with socket.create_connection(("flow.google.com", 443), timeout=3.0):
            pass
    except OSError as net_err:
        write_pipeline_heartbeat(f"❌ Lỗi kết nối mạng tới flow.google.com: {net_err}", is_running=False)
        raise RuntimeError(f"Network access to flow.google.com:443 is required before launching Chrome profile: {net_err}")

    def _cookies_to_flow_header(clist):
        # Giữ cookie của google.com / flow.google.com để tránh xung đột CookieMismatch từ .youtube.com / .google.com.vn
        prio = {"flow.google.com": 4, ".flow.google.com": 3, ".google.com": 2, "google.com": 1}
        chosen = {}
        for c in clist or []:
            nm = str(c.get("name") or "").strip()
            dom = str(c.get("domain") or "").strip().lower()
            if not nm or "GRECAPTCHA" in nm.upper():
                continue
            rank = prio.get(dom, 0)
            if rank == 0:
                continue
            prev = chosen.get(nm)
            if prev is None or rank >= prev[0]:
                chosen[nm] = (rank, str(c.get("value") or ""))
        return "; ".join(f"{k}={v[1]}" for k, v in chosen.items())

    _EXT_BRIDGE_BOX[0] = None
    _ACC_COOKIE_MAP.clear()
    _ACC_PAGE_LOCKS.clear()
    if os.environ.get("USE_FLOW_EXTENSION_TIER1", "").strip() != "0" and hasattr(gvt, "get_connected_extension_bridge"):
        try:
            _pre_br = gvt.get_connected_extension_bridge()
            if _pre_br and _pre_br.extension_liveness() == "connected":
                if hasattr(_pre_br, "apply_concurrency_settings"):
                    _pre_br.apply_concurrency_settings(
                        per_account_delay_sec=SUBMIT_DELAY_SEC,
                        global_stagger_sec=GLOBAL_STAGGER_SEC,
                        pool_tabs=int(eff_flow.get("extension_pool_tabs") or 2),
                    )
                _probe_acc_key = active_flow_accs[0]["profile_name"] if active_flow_accs else PROF_NAME
                _probe_tok = _pre_br.request_recaptcha_for_account("IMAGE_GENERATION", timeout=12, account_key=_probe_acc_key)
                _probe_err = str(getattr(_pre_br, "_last_extension_error", "") or "")
                if _probe_tok:
                    _EXT_BRIDGE_BOX[0] = _pre_br
                    print(f"✅ Extension Captcha Bridge (:4000) đã kết nối -> bật giải reCAPTCHA song song đa tab + Playwright Stealth dự phòng!", flush=True)
                elif "permission" in _probe_err.lower() or "cannot access contents" in _probe_err.lower():
                    print(f"⚠️ Extension Captcha Bridge chưa có quyền truy cập tab Flow ({_probe_err}) -> Tự chuyển sang Playwright Chrome (Tier 2)!", flush=True)
                    os.environ["USE_FLOW_EXTENSION_TIER1"] = "0"
        except Exception:
            pass

    class _DedicatedPwThread:
        """Runs real sync_playwright greenlet operations on a single owner thread while letting _ExtPlaywrightShim run lock-free across threads."""

        def __init__(self):
            import queue as _q_pw
            self._q = _q_pw.Queue()
            self._ready = threading.Event()
            self.pw = None
            self.is_shim = False
            self._err = None
            self._th = threading.Thread(target=self._worker, name="MTPlaywrightOwner", daemon=True)

        def _worker(self):
            try:
                with gvt.flow_playwright_or_extension(sync_playwright) as pw_obj:
                    self.pw = pw_obj
                    self.is_shim = bool(
                        hasattr(gvt, "_ExtPlaywrightShim") and isinstance(pw_obj, gvt._ExtPlaywrightShim)
                    )
                    self._ready.set()
                    while True:
                        item = self._q.get()
                        if item is None:
                            break
                        fn_call, a_call, kw_call, fut_call = item
                        try:
                            fut_call.set_result(fn_call(*a_call, **kw_call))
                        except Exception as exc_pw:
                            fut_call.set_exception(exc_pw)
            except Exception as init_exc:
                self._err = init_exc
                self._ready.set()

        def __enter__(self):
            self._th.start()
            self._ready.wait(timeout=60)
            if self._err:
                raise self._err
            _PW_RUNNER_FN[0] = self.call
            return self.pw

        def call(self, fn, *args, **kwargs):
            if self.is_shim or threading.current_thread() is self._th:
                return fn(*args, **kwargs)
            fut = concurrent.futures.Future()
            self._q.put((fn, args, kwargs, fut))
            return fut.result(timeout=180)

        def __exit__(self, exc_type, exc_val, exc_tb):
            _PW_RUNNER_FN[0] = None
            self._q.put(None)
            self._th.join(timeout=15)

    with _DedicatedPwThread() as pw:
        print("Reading and refreshing auth cookies from persistent profile(s) & cookies_file...", flush=True)
        account_cookie_pool = []
        for acc_item in active_flow_accs:
            acc_prof = acc_item.get("profile_name") or PROF_NAME
            acc_sh_dir = gvt._resolve_flow_shared_dir(acc_prof)
            acc_p_dir, acc_c_file = profile_paths(acc_sh_dir, acc_prof)
            cand_c_files = []
            for cf_try in (
                str(acc_c_file) if acc_c_file else "",
                os.path.join(WS_DIR, "data", "google_flow_grok", "cookies", f"{acc_prof}.json"),
                os.path.join(WS_DIR, "cookies", f"{acc_prof}.json"),
            ):
                if cf_try and os.path.isfile(cf_try) and cf_try not in cand_c_files:
                    cand_c_files.append(cf_try)
            # Ưu tiên file cookie mới nhất có chứa SID / __Secure-1PSID / OSID
            cand_c_files.sort(key=lambda fp_c: os.path.getmtime(fp_c), reverse=True)
            acc_saved = []
            chosen_c_file = ""
            for cf_pick in cand_c_files:
                try:
                    with open(cf_pick, "r", encoding="utf-8") as _f_ckp:
                        c_json = json.load(_f_ckp)
                    raw_lst = c_json.get("cookies", []) if isinstance(c_json, dict) else (c_json if isinstance(c_json, list) else [])
                    clean_lst = [c for c in raw_lst if isinstance(c, dict) and "GRECAPTCHA" not in str(c.get("name", "")).upper()]
                    if any(c.get("name") in ("SID", "__Secure-1PSID", "OSID") and c.get("value") for c in clean_lst):
                        acc_saved = clean_lst
                        chosen_c_file = cf_pick
                        break
                except Exception:
                    pass
            has_auth_sid = any(c.get("name") in ("SID", "__Secure-1PSID", "OSID") and c.get("value") for c in acc_saved)
            if acc_saved and has_auth_sid:
                merged_acc = {(c.get("domain", ""), c.get("name", "")): c for c in acc_saved}
                account_cookie_pool.append({
                    "name": acc_item.get("name") or acc_prof,
                    "profile_name": acc_prof,
                    "profile_dir": acc_p_dir,
                    "cookie_file": chosen_c_file,
                    "project_id": str(acc_item.get("project_id") or "").strip(),
                    "clean_cookies": list(merged_acc.values()),
                })

        # Warm-up primary profile ONLY if saved_cookies are missing/empty (prevents TargetClosedError if profile is busy)
        saved_cookies = []
        if cookies_file and os.path.exists(str(cookies_file)):
            try:
                c_json = json.load(open(str(cookies_file), "r", encoding="utf-8"))
                if isinstance(c_json, dict) and isinstance(c_json.get("cookies"), list):
                    saved_cookies = [c for c in c_json["cookies"] if "GRECAPTCHA" not in c.get("name", "").upper()]
                elif isinstance(c_json, list):
                    saved_cookies = [c for c in c_json if "GRECAPTCHA" not in c.get("name", "").upper()]
            except Exception as e:
                print(f"[WARN] Could not read cookies_file {cookies_file}: {e}", flush=True)

        _show_browser = os.environ.get("FLOW_SHOW_BROWSER", "").strip() == "1"
        _headless_mode = not _show_browser

        raw_cookies = []
        if len(saved_cookies) < 5 and not account_cookie_pool and not gfa._is_chrome_profile_open(profile_dir):
            try:
                p_args = ["--disable-blink-features=AutomationControlled", "--window-size=1280,800", "--mute-audio"]
                p_ctx = pw.chromium.launch_persistent_context(
                    str(profile_dir),
                    channel="chrome",
                    headless=_headless_mode,
                    args=p_args,
                )
                if saved_cookies:
                    try:
                        p_ctx.add_cookies(saved_cookies)
                    except Exception as e:
                        print(f"[WARN] p_ctx.add_cookies: {e}", flush=True)
                p_page = p_ctx.pages[0] if p_ctx.pages else p_ctx.new_page()
                try:
                    p_page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=35000)
                    p_page.wait_for_timeout(2500)
                except Exception as e:
                    print(f"[WARN] Initial profile warm-up: {e}", flush=True)
                raw_cookies = p_ctx.cookies(["https://flow.google.com", "https://google.com", "https://www.google.com", "https://accounts.google.com"])
                p_ctx.close()
            except Exception as e_warm:
                print(f"[WARN] Skipping persistent profile warm-up ({e_warm}), using saved cookies pool...", flush=True)

        merged_by_key = {}
        for c in (saved_cookies + raw_cookies):
            if "GRECAPTCHA" not in c.get("name", "").upper():
                merged_by_key[(c.get("domain", ""), c.get("name", ""))] = c
        clean_cookies = list(merged_by_key.values())
        if not clean_cookies and account_cookie_pool:
            clean_cookies = list(account_cookie_pool[0].get("clean_cookies") or [])
        if not account_cookie_pool:
            account_cookie_pool.append({
                "name": f"Google_{PROF_NAME}",
                "profile_name": PROF_NAME,
                "profile_dir": profile_dir,
                "project_id": "",
                "clean_cookies": clean_cookies,
            })
        elif clean_cookies:
            account_cookie_pool[0]["clean_cookies"] = clean_cookies

        cookie_hdr_box = [_cookies_to_flow_header(clean_cookies)]
        primary_prof_name = account_cookie_pool[0]["profile_name"]
        primary_proj_id = str(account_cookie_pool[0].get("project_id") or _resolve_default_flow_pid(primary_prof_name) or "").strip()
        for _res_tk in inflight_tasks.values():
            _res_acc_n = str(_res_tk.get("account_name") or _res_tk.get("preferred_account") or primary_prof_name).strip()
            _res_tk["preferred_account"] = _res_acc_n
            _res_tk["account_name"] = _res_acc_n
            _res_acc_ent = next((e for e in account_cookie_pool if e["profile_name"] == _res_acc_n), account_cookie_pool[0])
            _res_acc_pid = str(_res_acc_ent.get("project_id") or _resolve_default_flow_pid(_res_acc_n) or "").strip()
            if _res_acc_pid:
                _res_tk["project_id"] = _res_acc_pid
            elif primary_proj_id and not _res_tk.get("project_id"):
                _res_tk["project_id"] = primary_proj_id
            _res_tk["cookie_hdr"] = _cookies_to_flow_header(_res_acc_ent.get("clean_cookies") or clean_cookies)
        print(f"Prepared clean Google Flow auth cookies across {len(account_cookie_pool)} account(s)!", flush=True)

        browser_box = [None]
        browser_init_lock = threading.Lock()
        acc_contexts = {}
        acc_ctx_locks = {e["profile_name"]: threading.Lock() for e in account_cookie_pool}
        ctx_box = [None]
        page_box = [None]
        wiz_box = [None]
        dl_headers_box = [{}]
        ctx_uses = [0]
        cur_proj_box = [None]
        acc_idx_box = [0]
        cur_acc_box = [primary_prof_name]
        unhealthy_accounts = {}
        rate_limit_streak = {}
        rate_limit_until = {}
        _acc_last_reopen_ts = {}
        consec_tmt_global = [0]
        quota_exhausted_accounts = set()
        acct_quota_hits = {}

        def _mark_acc_healthy(p_name: str):
            if not p_name:
                return
            with QUEUE_LOCK:
                unhealthy_accounts.pop(p_name, None)
                rate_limit_until.pop(p_name, None)
                rate_limit_streak[p_name] = 0
                consec_tmt_global[0] = 0
            with _ACC_LOCKS_GUARD:
                _ACC_TMT_STREAK[p_name] = 0
            if hasattr(gvt, "clear_flow_account_cooldown"):
                try:
                    gvt.clear_flow_account_cooldown(p_name)
                except Exception:
                    pass

        auth_fail_counts = {}

        def _mark_unhealthy(p_name: str, reason: str = "", cooldown_sec=None):
            if not p_name:
                return 0.0
            kind = _classify_mt_err(reason)
            if kind == "content_policy":
                return 0.0
            with QUEUE_LOCK:
                if kind == "account_auth":
                    af_cnt = int(auth_fail_counts.get(p_name, 0)) + 1
                    auth_fail_counts[p_name] = af_cnt
                    # Nếu 1 tài khoản hỏng phiên (thiếu SNlM0e / 401) >= 2 lần -> cách ly 30 phút để không làm nghẽn luồng!
                    dur = float(cooldown_sec) if (cooldown_sec is not None and af_cnt < 2) else (1800.0 if af_cnt >= 2 else 180.0)
                elif cooldown_sec is not None:
                    dur = float(cooldown_sec)
                elif kind == "rate_limit":
                    st_cnt = int(rate_limit_streak.get(p_name, 0)) + 1
                    rate_limit_streak[p_name] = st_cnt
                    consec_tmt_global[0] += 1
                    # Progressive window backoff: short retry (1-2), then genuine 35-300s drain when one account hits extended [8] lock
                    if st_cnt == 1:
                        dur = 6.0
                    elif st_cnt == 2:
                        dur = 15.0
                    elif st_cnt == 3:
                        dur = 35.0
                    elif st_cnt == 4:
                        dur = 75.0
                    elif st_cnt == 5:
                        dur = 150.0
                    else:
                        dur = min(300.0, 150.0 + 75.0 * (st_cnt - 5))
                    rate_limit_until[p_name] = max(rate_limit_until.get(p_name, 0.0), time.time() + dur)
                else:
                    dur = float({"account_quota": 900.0, "account_auth": 180.0, "captcha_score": 8.0}.get(kind, 30.0))
                unhealthy_accounts[p_name] = max(unhealthy_accounts.get(p_name, 0.0), time.time() + dur)
            if hasattr(gvt, "mark_flow_account_cooldown"):
                try:
                    gvt.mark_flow_account_cooldown(p_name, kind, reason, cooldown_sec=dur)
                except Exception:
                    pass
            if kind != "rate_limit":
                try:
                    import fashion_motion_control_engine as _fmce
                    _fmce._mark_flow_profile_unhealthy(p_name, reason or "pipeline_error")
                except Exception:
                    pass
            return dur

        def _is_prof_cooling(p_name: str, now_v: float) -> bool:
            with QUEUE_LOCK:
                if p_name in quota_exhausted_accounts:
                    return True
                if unhealthy_accounts.get(p_name, 0.0) > now_v:
                    return True
            if hasattr(gvt, "is_flow_account_in_cooldown"):
                in_cd, _, _ = gvt.is_flow_account_in_cooldown(p_name)
                return bool(in_cd)
            return False

        def ensure_browser():
            with browser_init_lock:
                b = browser_box[0]
                if b is not None:
                    try:
                        if b.is_connected():
                            return b
                    except Exception:
                        pass
                    with QUEUE_LOCK:
                        acc_contexts.clear()
                    ctx_box[0] = None
                    page_box[0] = None
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1280,800",
                    "--mute-audio",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
                try:
                    b = pw.chromium.launch(channel="chrome", headless=_headless_mode, args=launch_args)
                except Exception:
                    b = pw.chromium.launch(headless=_headless_mode, args=launch_args)
                browser_box[0] = b
                return b

        def _activate_ctx_state(st_entry):
            ctx_box[0] = st_entry["ctx"]
            page_box[0] = st_entry["pg"]
            wiz_box[0] = st_entry["wiz"]
            dl_headers_box[0] = st_entry["dl_headers"]
            cookie_hdr_box[0] = st_entry["cookie_hdr"]
            cur_proj_box[0] = st_entry["project_id"]
            cur_acc_box[0] = st_entry["profile_name"]
            ctx_uses[0] = st_entry["uses"]

        _last_acc_refresh_ts = {}

        def _open_single_acc_context(prof_name: str, project_id_hint: str = "", force_reopen: bool = False):
            return _run_pw_safe(_open_single_acc_context_inner, prof_name, project_id_hint, force_reopen)

        def _open_single_acc_context_inner(prof_name: str, project_id_hint: str = "", force_reopen: bool = False):
            acc_entry = next((e for e in account_cookie_pool if e["profile_name"] == prof_name), None)
            if acc_entry is None:
                raise RuntimeError(f"Unknown Flow profile: {prof_name}")
            c_lock = acc_ctx_locks.setdefault(prof_name, threading.Lock())
            with c_lock:
                if not force_reopen:
                    cached = acc_contexts.get(prof_name)
                    if cached and cached.get("pg") and prof_name not in quota_exhausted_accounts:
                        try:
                            if not cached["pg"].is_closed() and browser_box[0] and browser_box[0].is_connected():
                                return cached
                        except Exception:
                            pass
                old_st = acc_contexts.pop(prof_name, None)
                if old_st and old_st.get("ctx"):
                    try:
                        old_st["ctx"].close()
                    except Exception:
                        pass

                acc_own_pid = str(acc_entry.get("project_id") or _resolve_default_flow_pid(prof_name) or "").strip()
                cand_pids = []
                for p_cand in (acc_own_pid, project_id_hint, ""):
                    if p_cand not in cand_pids:
                        cand_pids.append(p_cand)

                def _load_fresh_disk_cookies_acc(pname: str) -> list:
                    sh_d = gvt._resolve_flow_shared_dir(pname)
                    _, c_fp = profile_paths(sh_d, pname)
                    cand_fs = []
                    for fp_try in (
                        acc_entry.get("cookie_file") or "",
                        str(c_fp) if c_fp else "",
                        os.path.join(WS_DIR, "data", "google_flow_grok", "cookies", f"{pname}.json"),
                        os.path.join(WS_DIR, "cookies", f"{pname}.json"),
                    ):
                        if fp_try and os.path.isfile(fp_try) and fp_try not in cand_fs:
                            cand_fs.append(fp_try)
                    cand_fs.sort(key=lambda fp_x: os.path.getmtime(fp_x), reverse=True)
                    for fp_pick in cand_fs:
                        try:
                            with open(fp_pick, "r", encoding="utf-8") as _f_rf:
                                raw_c = json.load(_f_rf)
                            clist_r = raw_c.get("cookies", raw_c) if isinstance(raw_c, dict) else raw_c
                            if isinstance(clist_r, list):
                                clean_r = [c for c in clist_r if isinstance(c, dict) and "GRECAPTCHA" not in str(c.get("name", "")).upper()]
                                if any(c.get("name") in ("SID", "__Secure-1PSID", "OSID") and c.get("value") for c in clean_r):
                                    return clean_r
                        except Exception:
                            pass
                    return []

                disk_fresh = _load_fresh_disk_cookies_acc(prof_name) if force_reopen else []
                use_cookies = disk_fresh or acc_entry.get("clean_cookies") or clean_cookies
                if disk_fresh:
                    acc_entry["clean_cookies"] = disk_fresh
                ok_http, http_info = _http_check_flow_cookies(use_cookies, cand_pids[0] if cand_pids else "")
                last_rf_ts = _last_acc_refresh_ts.get(prof_name, 0.0)
                need_prof_refresh = ((not ok_http) or force_reopen) and ((time.time() - last_rf_ts) >= 90.0)
                if need_prof_refresh and hasattr(gvt, "_refresh_google_profile"):
                    _last_acc_refresh_ts[prof_name] = time.time()
                    try:
                        print(f"🔄 [{prof_name}] Tự động làm mới phiên cookie Google Flow...", flush=True)
                        ok_rf, new_tok, new_pid, err_rf = gvt._refresh_google_profile(prof_name, prefer_profile=True)
                        if ok_rf and new_tok:
                            try:
                                from google_flow_auth import commit_login, identity_matches, expected_email
                                root_val = gvt._auth_root_value(None)
                                em_val = str(err_rf or "").removeprefix("session_verified:")
                                if identity_matches(expected_email(root_val, prof_name), em_val):
                                    commit_login(root_val, prof_name, em_val, new_tok, new_pid or cand_pids[0] or "", refresh=True)
                            except Exception:
                                pass
                            reloaded = _load_fresh_disk_cookies_acc(prof_name)
                            if reloaded:
                                use_cookies = reloaded
                                acc_entry["clean_cookies"] = reloaded
                                ok_http, http_info = _http_check_flow_cookies(use_cookies, cand_pids[0] if cand_pids else "")
                        elif err_rf:
                            print(f"⚠️ [{prof_name}] Auto-refresh cookie cảnh báo: {err_rf}", flush=True)
                    except Exception as ex_rf:
                        print(f"⚠️ [{prof_name}] Auto-refresh cookie lỗi: {ex_rf}", flush=True)
                if not ok_http:
                    last_err = f"HTTP cookie check failed ({http_info})"
                    print(f"[SKIP] [{prof_name}] Bỏ qua trước khi mở Chrome ({last_err})", flush=True)
                    _mark_unhealthy(prof_name, last_err, cooldown_sec=300.0)
                    raise RuntimeError(last_err)
                cleaned_pid = http_info.split(":", 1)[1].strip() if str(http_info or "").startswith("needs_chrome_refresh:") else str(http_info or "").strip()
                if __import__("re").match(r"^[0-9a-fA-F-]{20,}$", cleaned_pid) and cleaned_pid not in cand_pids:
                    cand_pids.insert(0, cleaned_pid)

                last_err = None
                for target_pid in cand_pids:
                    target_url = f"https://flow.google.com/project/{target_pid}" if target_pid else "https://flow.google.com/"
                    pid_tag = target_pid[:8] if target_pid else "home"
                    print(f"✨ [TK: {prof_name}] Connecting reusable Flow context (project {pid_tag})...", flush=True)
                    ctx = None
                    try:
                        b = ensure_browser()
                        ver_major = str(getattr(b, "version", "") or "").split(".")[0].strip()
                        clean_ua = (
                            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver_major}.0.0.0 Safari/537.36"
                            if ver_major.isdigit()
                            else _sanitize_chrome_ua("")
                        )
                        ctx = b.new_context(viewport={"width": 1280, "height": 800}, user_agent=clean_ua)
                        if hasattr(ctx, "profile_name"):
                            ctx.profile_name = prof_name
                        if hasattr(gvt, "inject_stealth_scripts"):
                            try:
                                gvt.inject_stealth_scripts(ctx)
                            except Exception:
                                pass
                        ctx.add_init_script(gvt._FLOW_HIJACK_BYPASS_JS)
                        ctx.add_cookies(use_cookies)
                        pg = ctx.new_page()
                        if hasattr(pg, "profile_name"):
                            pg.profile_name = prof_name
                        pg.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                        cur_u = pg.url or ""
                        if "accounts.google.com" in cur_u or "CookieMismatch" in cur_u:
                            raise RuntimeError(f"Auth redirected to {cur_u[:80]}")
                        if "/404" in cur_u:
                            print(f"   [WARN] Project {pid_tag} returned 404 for {prof_name}, trying account project...", flush=True)
                            try:
                                ctx.close()
                            except Exception:
                                pass
                            ctx = None
                            continue
                        pg.evaluate(gvt._FLOW_HIJACK_BYPASS_JS)
                        pg.wait_for_function(
                            "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise && typeof window.grecaptcha.enterprise.execute === 'function'",
                            timeout=60000,
                        )
                        pg.wait_for_timeout(1200)
                        try:
                            pg.mouse.move(random.randint(240, 520), random.randint(260, 480), steps=5)
                            pg.evaluate(
                                """async (siteKey) => {
                                    const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
                                    try { await fn(siteKey, {action: 'PAGE_VIEW'}); } catch (e) {}
                                }""",
                                _FLOW_SITEKEY,
                            )
                        except Exception:
                            pass
                        final_u = pg.url or ""
                        eff_pid = target_pid or acc_own_pid
                        if "/project/" in final_u:
                            parsed_pid = final_u.split("/project/", 1)[1].split("?", 1)[0].split("/", 1)[0].strip()
                            if len(parsed_pid) >= 16:
                                eff_pid = parsed_pid
                        wz = pg.evaluate(
                            """() => {
                                const w = window.WIZ_global_data || {};
                                return {
                                    at: w.SNlM0e || '',
                                    bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261030.00_p2',
                                    fsid: w.FdrFJe || '',
                                    ua: navigator.userAgent,
                                };
                            }"""
                        )
                        if wz:
                            wz["ua"] = _sanitize_chrome_ua(wz.get("ua") or clean_ua)
                        if not wz or not wz.get("at"):
                            raise RuntimeError(f"Phiên '{prof_name}' thiếu SNlM0e")
                        live_c = ctx.cookies(["https://flow.google.com", "https://google.com", "https://accounts.google.com"])
                        hdr = _cookies_to_flow_header(live_c)
                        _ACC_COOKIE_MAP[prof_name] = hdr
                        st_entry = {
                            "profile_name": prof_name,
                            "project_id": eff_pid or _resolve_default_flow_pid(prof_name),
                            "ctx": ctx,
                            "pg": pg,
                            "wiz": wz,
                            "cookie_hdr": hdr,
                            "dl_headers": {
                                "Cookie": hdr,
                                "Referer": "https://flow.google.com/",
                                "User-Agent": wz["ua"],
                            },
                            "uses": 0,
                        }
                        unhealthy_accounts.pop(prof_name, None)
                        if hasattr(gvt, "clear_flow_account_cooldown"):
                            try:
                                gvt.clear_flow_account_cooldown(prof_name)
                            except Exception:
                                pass
                        acc_contexts[prof_name] = st_entry
                        if not wiz_box[0] or prof_name == primary_prof_name:
                            wiz_box[0] = wz
                            cookie_hdr_box[0] = hdr
                            dl_headers_box[0] = dict(st_entry["dl_headers"])
                        return st_entry
                    except Exception as e:
                        last_err = e
                        print(f"[WARN] _open_single_acc_context ({prof_name}) failed: {e}", flush=True)
                        if ctx is not None:
                            try:
                                ctx.close()
                            except Exception:
                                pass
                        err_low = str(e).lower()
                        if "accounts.google.com" in err_low or "cookiemismatch" in err_low or "snlm0e" in err_low:
                            _mark_unhealthy(prof_name, str(e), cooldown_sec=300.0)
                            break
                        if "closed" in err_low or "timeout" in err_low:
                            _mark_unhealthy(prof_name, str(e), cooldown_sec=90.0)
                            break
                        time.sleep(1.0)
                raise RuntimeError(f"Failed to open Flow context for {prof_name}: {last_err}")

        def open_fresh_clean_context(project_id="", prefer_profile=None, force_reopen=False, rotate_next=False):
            now_ts = time.time()
            ordered_entries = []
            if prefer_profile:
                for entry in account_cookie_pool:
                    if entry["profile_name"] == prefer_profile:
                        ordered_entries.append(entry)
                        break
            start_i = acc_idx_box[0]
            if rotate_next and not prefer_profile and len(account_cookie_pool) > 1:
                start_i = (start_i + 1) % len(account_cookie_pool)
            for off in range(len(account_cookie_pool)):
                ent = account_cookie_pool[(start_i + off) % len(account_cookie_pool)]
                if ent not in ordered_entries:
                    ordered_entries.append(ent)
            healthy_entries = [e for e in ordered_entries if not _is_prof_cooling(e["profile_name"], now_ts)]
            cooldown_entries = [e for e in ordered_entries if _is_prof_cooling(e["profile_name"], now_ts)]
            ordered_entries = healthy_entries + cooldown_entries
            last_err = None
            for acc_entry in ordered_entries:
                pname = acc_entry["profile_name"]
                try:
                    st_e = _open_single_acc_context(pname, project_id_hint=project_id, force_reopen=force_reopen)
                    for idx_pos, e_pool in enumerate(account_cookie_pool):
                        if e_pool["profile_name"] == pname:
                            acc_idx_box[0] = idx_pos
                            break
                    _activate_ctx_state(st_e)
                    return
                except Exception as exc_o:
                    last_err = exc_o
                    continue
            raise RuntimeError(f"Failed to open clean Chrome context across {len(ordered_entries)} account(s): {last_err}")

        def _classify_mt_err(err_msg) -> str:
            up = str(err_msg or "").upper()
            if any(k in up for k in ("TOO_MUCH_TRAFFIC", "HIGH_TRAFFIC", "RESOURCE_EXHAUSTED", "THROTTLED", "HTTP 429")):
                return "rate_limit"
            if hasattr(gvt, "classify_flow_error"):
                return gvt.classify_flow_error(str(err_msg or ""))
            return "transient"

        single_acc_quota_hits = [0]
        quota_all_exhausted = [False]
        _last_hard_reset_call = [0.0]

        def _record_task_scene_error(task_dict: dict, err_msg: str, terminal: bool = False):
            t_pid = task_dict.get("pid")
            if not t_pid or t_pid not in prod_meta:
                return
            p_dir_e, _, st_e, _ = prod_meta[t_pid]
            sc_obj_e = task_dict.get("sc")
            err_key = (sc_obj_e.get("id") if isinstance(sc_obj_e, dict) and sc_obj_e.get("id") else f"{task_dict.get('v_key', 'v1')}_ref")
            acc_e = str(task_dict.get("account_name") or task_dict.get("worker_profile") or task_dict.get("preferred_account") or PROF_NAME)
            vi_e = gvt.describe_flow_error_vi(str(err_msg or "")) if hasattr(gvt, "describe_flow_error_vi") else str(err_msg or "")[:240]
            with STATE_LOCK:
                st_e.setdefault("scene_errors", {})[err_key] = {
                    "account": acc_e,
                    "message": vi_e,
                    "raw": str(err_msg or "")[:280],
                    "retries": int(task_dict.get("retries", 0)),
                    "terminal": bool(terminal),
                    "updated_at": time.strftime("%H:%M:%S"),
                }
                if terminal:
                    fs_list = st_e.setdefault("failed_scenes", [])
                    if err_key not in fs_list:
                        fs_list.append(err_key)
            save_prod_state(p_dir_e, st_e)
            if terminal and hasattr(gvt, "record_diagnostic_error"):
                gvt.record_diagnostic_error(
                    module="MultiThreadPipeline",
                    target=str(t_pid),
                    scene=str(err_key),
                    account=acc_e,
                    error_text=str(err_msg or ""),
                )

        def _clear_task_scene_error(task_dict: dict):
            t_pid = task_dict.get("pid")
            if not t_pid or t_pid not in prod_meta:
                return
            p_dir_e, _, st_e, _ = prod_meta[t_pid]
            sc_obj_e = task_dict.get("sc")
            err_key = (sc_obj_e.get("id") if isinstance(sc_obj_e, dict) and sc_obj_e.get("id") else f"{task_dict.get('v_key', 'v1')}_ref")
            changed_e = False
            with STATE_LOCK:
                if isinstance(st_e.get("scene_errors"), dict) and err_key in st_e["scene_errors"]:
                    st_e["scene_errors"].pop(err_key, None)
                    changed_e = True
                if isinstance(st_e.get("failed_scenes"), list) and err_key in st_e["failed_scenes"]:
                    st_e["failed_scenes"].remove(err_key)
                    changed_e = True
            if changed_e:
                save_prod_state(p_dir_e, st_e)

        def _schedule_mt_retry(task_dict, err_msg, max_retries_cap=6, front=False):
            kind = _classify_mt_err(err_msg)
            short_e = gvt.format_flow_error_short(str(err_msg or ""), 120) if hasattr(gvt, "format_flow_error_short") else str(err_msg or "")[:120]
            if kind == "account_quota" and task_dict.get("type") in ("vid_scene", "ref_img", "upsample_ref_2k"):
                with QUEUE_LOCK:
                    q_prof = str(task_dict.get("account_name") or task_dict.get("preferred_account") or cur_acc_box[0] or PROF_NAME).strip()
                    acct_quota_hits[q_prof] = acct_quota_hits.get(q_prof, 0) + 1
                    single_acc_quota_hits[0] += 1
                    print(f"⛔ [{task_dict.get('pid')} | {task_dict.get('key')}] Hết credit ({short_e}) trên tài khoản {q_prof}.", flush=True)
                    if acct_quota_hits[q_prof] >= 3:
                        quota_exhausted_accounts.add(q_prof)
                        _mark_unhealthy(q_prof, err_msg, cooldown_sec=86400.0)
                    avail_q = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in quota_exhausted_accounts]
                    if not avail_q:
                        quota_all_exhausted[0] = True
                        pending_queue[:] = [q for q in pending_queue if q.get("type") in ("upsample_1080p", "upsample_ref_2k")]
                        print("⛔ Đã hết credit trên toàn bộ tài khoản; giữ lại upscale 1080p/2K (0 credit) và build FFmpeg cho các video đã xong.", flush=True)
                        return False
                    if q_prof in quota_exhausted_accounts or len(account_cookie_pool) > 1:
                        task_dict.pop("preferred_account", None)
                        task_dict["next_retry_at"] = time.time() + 0.5
                        if front:
                            pending_queue.insert(0, task_dict)
                        else:
                            pending_queue.append(task_dict)
                        return True
                    return False
            if kind == "content_policy":
                subtype = gvt.classify_content_rejection_subtype(str(err_msg or "")) if hasattr(gvt, "classify_content_rejection_subtype") else "unsafe_generation"
                err_low = str(err_msg or "").lower()
                is_upload_reject = any(k in err_low for k in ("maseq", "uploadimage", "upload ảnh"))
                if (
                    not is_upload_reject
                    and subtype != "invalid_input"
                    and not task_dict.get("_policy_sanitized_retried")
                    and hasattr(gvt, "sanitize_prompt_for_flow_policy")
                    and task_dict.get("type") in ("vid_scene", "ref_img", "thumb_img")
                ):
                    sc_obj = task_dict.get("sc")
                    raw_p = ""
                    if isinstance(sc_obj, dict) and sc_obj.get("prompt"):
                        raw_p = str(sc_obj.get("prompt") or "")
                    elif task_dict.get("prompt"):
                        raw_p = str(task_dict.get("prompt") or "")
                    if raw_p:
                        safe_p, p_chg = gvt.sanitize_prompt_for_flow_policy(raw_p, subtype)
                        if p_chg and safe_p:
                            task_dict["_policy_sanitized_retried"] = True
                            if isinstance(sc_obj, dict) and sc_obj.get("prompt"):
                                sc_obj["prompt"] = safe_p
                            elif task_dict.get("prompt"):
                                task_dict["prompt"] = safe_p
                            task_dict["retries"] = int(task_dict.get("retries", 0)) + 1
                            task_dict["next_retry_at"] = time.time() + 1.0
                            print(
                                f"🛡️ [{task_dict.get('pid')} | {task_dict.get('key')}] Bộ lọc nội dung ({subtype}: {short_e}) "
                                "— tự làm dịu prompt an toàn và thử lại 1 lần.",
                                flush=True,
                            )
                            with QUEUE_LOCK:
                                if front:
                                    pending_queue.insert(0, task_dict)
                                else:
                                    pending_queue.append(task_dict)
                            return True
                vi_msg = gvt.describe_flow_error_vi(str(err_msg or "")) if hasattr(gvt, "describe_flow_error_vi") else short_e
                with STATE_LOCK:
                    if isinstance(task_dict.get("sc"), dict):
                        task_dict["sc"]["last_error"] = vi_msg
                        task_dict["sc"]["status_detail"] = f"❌ {vi_msg}"
                _record_task_scene_error(task_dict, str(err_msg or ""), terminal=True)
                write_pipeline_heartbeat(f"❌ [{task_dict.get('pid')} | {task_dict.get('key')}] {vi_msg}", is_running=True)
                safe_sync_ui()
                print(f"❌ [{task_dict.get('pid')} | {task_dict.get('key')}] {vi_msg} — dừng retry.", flush=True)
                return False
            err_low_r = str(err_msg or "").lower()
            if "rpc_err:[5]" in err_low_r:
                eff_cap = 3
            elif kind in ("rate_limit", "captcha_score"):
                eff_cap = max(int(max_retries_cap), 36)
            elif kind == "transient":
                eff_cap = max(int(max_retries_cap), 12)
            else:
                eff_cap = int(max_retries_cap)
            with QUEUE_LOCK:
                avail_live = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in quota_exhausted_accounts]
            is_dead_auth_reroute = (kind == "account_auth" and len(avail_live) > 1)
            if not is_dead_auth_reroute:
                task_dict["retries"] = int(task_dict.get("retries", 0)) + 1
            if task_dict["retries"] > eff_cap:
                _record_task_scene_error(task_dict, str(err_msg or ""), terminal=True)
                safe_sync_ui()
                print(f"❌ [{task_dict.get('pid')} | {task_dict.get('key')}] Đã hết {eff_cap} lần thử ({short_e}).", flush=True)
                return False
            if not is_dead_auth_reroute:
                _record_task_scene_error(task_dict, str(err_msg or ""), terminal=False)
            if any(k in err_low_r for k in ("not_found", "invalid", "upload", "media_uuid")):
                task_dict["_need_ref_reupload"] = True
            if task_dict.get("type") == "vid_scene" and task_dict.get("voice_id") and task_dict.get("retries", 0) >= 2:
                if kind in ("captcha_score",) or any(k in err_low_r for k in ("not_found", "unusual_activity", "[5]", "[7]")):
                    if not task_dict.get("_drop_voice_id"):
                        task_dict["_drop_voice_id"] = True
                        print(f"🎙️ [{task_dict.get('pid')} | {task_dict.get('key')}] Bỏ voice_id UUID cũ khi retry để tránh lỗi tài khoản khác (giữ nguyên giọng từ Prompt).", flush=True)
            has_alt_acct = (
                len(avail_live) > 1
                and task_dict.get("type") not in ("upsample_ref_2k", "upsample_1080p")
                and kind in ("account_quota", "account_auth", "rate_limit", "captcha_score")
            )
            if has_alt_acct:
                task_dict.pop("preferred_account", None)
                backoff_s = random.uniform(0.3, 0.8) if kind != "rate_limit" else random.uniform(1.5, 3.0)
            elif kind == "rate_limit":
                backoff_s = min(45.0, 8.0 + task_dict["retries"] * 2.5 + random.uniform(0.3, 1.2))
            elif kind == "captcha_score":
                backoff_s = min(16.0, 4.0 + task_dict["retries"] * 1.2 + random.uniform(0.3, 1.2))
            else:
                backoff_s = min(20.0, (1.6 ** min(task_dict["retries"], 4)) + random.uniform(0.4, 1.8))
            task_dict["next_retry_at"] = time.time() + backoff_s
            with QUEUE_LOCK:
                if front:
                    ins_idx = min(20 if task_dict["retries"] >= 3 else 6, len(pending_queue)) if kind == "rate_limit" else 0
                    pending_queue.insert(ins_idx, task_dict)
                else:
                    pending_queue.append(task_dict)
            return True

        def _poll_item_failed(task_dict, res_state: str, elapsed: float) -> bool:
            st_str = str(res_state or "")
            if "rpc_err:[5]" in st_str:
                task_dict["_rpc5_cnt"] = int(task_dict.get("_rpc5_cnt", 0)) + 1
            else:
                task_dict["_rpc5_cnt"] = 0
            st_up = st_str.upper()
            if "HTTP 400" in st_up or "INVALID_ARGUMENT" in st_up:
                task_dict["_http400_cnt"] = int(task_dict.get("_http400_cnt", 0)) + 1
            else:
                task_dict["_http400_cnt"] = 0
            if st_str.startswith("failed_") or st_str.startswith("dl_err:"):
                return True
            if "rpc_err:[5]" in st_str:
                need_hits = 4 if task_dict.get("_saw_active_status") else 2
                need_sec = 50 if task_dict.get("_saw_active_status") else 20
                if task_dict.get("_rpc5_cnt", 0) >= need_hits and elapsed >= need_sec:
                    task_dict["_need_ref_reupload"] = True
                    return True
            if task_dict.get("_http400_cnt", 0) >= 3 and elapsed >= 15:
                return True
            return elapsed > (300 if task_dict.get("stage") == "vids_1080p" else 240)

        def _handle_task_failure_switch(project_id_arg, failed_prof, err_msg, prefer_profile=None, rotate_next=True):
            kind = _classify_mt_err(err_msg)
            if kind == "content_policy":
                return
            if kind == "account_quota" and len(account_cookie_pool) <= 1:
                return
            err_up = str(err_msg or "").upper()
            is_auth_failure = (kind == "account_auth") or any(
                k in err_up for k in ("401", "UNAUTHENTICATED", "SNLM0E", "AUTH_REDIRECT", "COOKIEMISMATCH")
            )
            is_browser_closed = ("TARGET" in err_up and "CLOSED" in err_up) or ("BROWSER HAS BEEN CLOSED" in err_up)
            is_acct_issue = kind in ("account_quota", "account_auth", "rate_limit", "captcha_score") or any(
                k in err_up for k in ("401", "403", "429", "UNAUTHENTICATED", "UNUSUAL_ACTIVITY", "USER_QUOTA_REACHED", "RECAPTCHA", "SNLM0E")
            ) or is_browser_closed
            dur_applied = 0.0
            if is_acct_issue and failed_prof:
                dur_applied = _mark_unhealthy(failed_prof, str(err_msg))
                if kind == "rate_limit":
                    print(
                        f"⏱️ [Rate-Limit {failed_prof}] Flow tạm giới hạn [8] -> nghỉ {dur_applied:.0f}s (luồng khác vẫn chạy song song).",
                        flush=True,
                    )
            need_score_reset = (kind == "captcha_score")
            if kind == "rate_limit":
                with QUEUE_LOCK:
                    if consec_tmt_global[0] >= 6:
                        consec_tmt_global[0] = 0
                        need_score_reset = True
            if need_score_reset and hasattr(gvt, "get_connected_extension_bridge"):
                with QUEUE_LOCK:
                    now_r = time.time()
                    do_reset = (now_r - _last_hard_reset_call[0]) >= 120.0
                    if do_reset:
                        _last_hard_reset_call[0] = now_r
                if do_reset:
                    try:
                        _br_sc = _EXT_BRIDGE_BOX[0] or gvt.get_connected_extension_bridge()
                        if _br_sc:
                            _br_sc.notify_recaptcha_score_dead()
                    except Exception:
                        pass
            if kind == "captcha_score" and failed_prof:
                st_cached = acc_contexts.get(failed_prof)
                if st_cached and st_cached.get("ctx"):
                    try:
                        st_cached["ctx"].clear_cookies(name="_grecaptcha")
                    except Exception:
                        pass
            do_reopen_rl = False
            if kind == "rate_limit" and failed_prof:
                with QUEUE_LOCK:
                    now_re = time.time()
                    rl_st_cur = int(rate_limit_streak.get(failed_prof, 0) or 0)
                    if rl_st_cur in (6, 9, 12) and (now_re - float(_acc_last_reopen_ts.get(failed_prof, 0.0) or 0.0)) >= 120.0:
                        _acc_last_reopen_ts[failed_prof] = now_re
                        do_reopen_rl = True
            if is_auth_failure or is_browser_closed or do_reopen_rl:
                if do_reopen_rl:
                    print(f"🔄 [Session-Refresh {failed_prof}] Làm mới context & _grecaptcha sau chuỗi [8] liên tiếp...", flush=True)
                try:
                    _open_single_acc_context(
                        failed_prof or primary_prof_name,
                        project_id_hint=project_id_arg or _resolve_default_flow_pid(failed_prof),
                        force_reopen=True,
                    )
                except Exception:
                    pass

        needs_chrome_on_start = bool(inflight_tasks) or any(
            t.get("type") in ("ref_img", "upsample_ref_2k", "upsample_1080p")
            or (t.get("type") == "vid_scene" and VIDEO_PROVIDER != "google_vids")
            for t in pending_queue
        )
        if needs_chrome_on_start:
            first_pid = next((t.get("project_id") for t in pending_queue if t.get("project_id")), _resolve_default_flow_pid(primary_prof_name))
            open_fresh_clean_context(first_pid)
            for _acc_w in account_cookie_pool:
                _ap_w = _acc_w["profile_name"]
                if _ap_w not in acc_contexts and _ap_w not in quota_exhausted_accounts:
                    try:
                        _open_single_acc_context(_ap_w, project_id_hint=_resolve_default_flow_pid(_ap_w))
                    except Exception:
                        pass
            for _res_tk in inflight_tasks.values():
                _r_prof = str(_res_tk.get("account_name") or _res_tk.get("preferred_account") or primary_prof_name).strip()
                _r_ctx = acc_contexts.get(_r_prof) or acc_contexts.get(primary_prof_name)
                if _r_ctx:
                    _res_tk["wiz"] = _r_ctx["wiz"]
                    _res_tk["cookie_hdr"] = _r_ctx["cookie_hdr"]
                    _res_tk["dl_headers"] = dict(_r_ctx["dl_headers"])
                    if _r_ctx.get("project_id"):
                        _res_tk["project_id"] = _r_ctx["project_id"]
        last_submit_ts = [0.0]

        uploaded_prod_by_acc = {}
        fresh_prod_uploads = set()
        uploaded_char_by_acc = {}
        acc_variant_uploads = {}
        upload_key_locks = {}

        def _get_upload_lock(lock_k):
            with QUEUE_LOCK:
                lk = upload_key_locks.get(lock_k)
                if lk is None:
                    lk = threading.Lock()
                    upload_key_locks[lock_k] = lk
                return lk

        def ensure_single_prod_uuid(pid, pdir, state, refs_state, base_char, eff_project_id, primary_prod_img, pg=None, wiz=None, cur_acc=None, force_reupload=False):
            cur_acc = cur_acc or cur_acc_box[0]
            pg = pg or page_box[0]
            wiz = wiz or wiz_box[0]
            prod_abs = os.path.abspath(primary_prod_img) if primary_prod_img else ""
            dedup_k = (pid, eff_project_id, prod_abs or base_char)
            lk = _get_upload_lock(("prod", cur_acc, dedup_k))
            with lk:
                with STATE_LOCK:
                    acc_map = uploaded_prod_by_acc.setdefault(cur_acc, {})
                    if not force_reupload or (cur_acc, dedup_k) in fresh_prod_uploads:
                        if dedup_k in acc_map:
                            return acc_map[dedup_k]
                        if (pid, eff_project_id, base_char) in acc_map:
                            return acc_map[(pid, eff_project_id, base_char)]
                        by_acc_disk = refs_state.get("uploaded_prod_refs_by_account", {}).get(cur_acc, {})
                        acc_disk_uuids = by_acc_disk.get(f"{eff_project_id}:{base_char}") or []
                        if acc_disk_uuids:
                            acc_map[dedup_k] = acc_disk_uuids[0]
                            acc_map[(pid, eff_project_id, base_char)] = acc_disk_uuids[0]
                            return acc_disk_uuids[0]
                print(f"📤 [{pid} | {base_char.upper()} | {cur_acc}] Uploading product image {os.path.basename(primary_prod_img)}...", flush=True)
                ok_u, u_id, err_u = upload_single_product_ref_in_page(
                    pg, wiz, eff_project_id, primary_prod_img, cookie_hdr=_ACC_COOKIE_MAP.get(cur_acc, ""), prof_name=cur_acc
                )
                if not ok_u or not u_id:
                    print(f"⚠️ [{pid} | {base_char.upper()} | {cur_acc}] Product upload failed ({err_u})", flush=True)
                    return None
                with STATE_LOCK:
                    fresh_prod_uploads.add((cur_acc, dedup_k))
                    acc_map = uploaded_prod_by_acc.setdefault(cur_acc, {})
                    acc_map[dedup_k] = u_id
                    acc_map[(pid, eff_project_id, base_char)] = u_id
                    refs_state.setdefault("uploaded_prod_refs_by_account", {}).setdefault(cur_acc, {})[f"{eff_project_id}:{base_char}"] = [u_id]
                    if cur_acc == primary_prof_name:
                        refs_state.setdefault("uploaded_prod_refs", {})[base_char] = [u_id]
                save_prod_state(pdir, state, refs_state)
                print(f"✅ [{pid} | {base_char.upper()} | {cur_acc}] Uploaded single product image {os.path.basename(primary_prod_img)} -> uuid={u_id}", flush=True)
                time.sleep(1.0)
                return u_id

        def ensure_char_photo_uuid(pid, pdir, state, refs_state, base_char, eff_project_id, pg=None, wiz=None, cur_acc=None):
            cur_acc = cur_acc or cur_acc_box[0]
            pg = pg or page_box[0]
            wiz = wiz or wiz_box[0]
            lk = _get_upload_lock(("char", cur_acc, pid, base_char))
            with lk:
                with STATE_LOCK:
                    acc_cmap = uploaded_char_by_acc.setdefault(cur_acc, {})
                    if (pid, base_char) in acc_cmap:
                        return acc_cmap[(pid, base_char)]
                    if cur_acc == primary_prof_name:
                        refs_state.setdefault("uploaded_char_refs", {})
                        cached_u = refs_state["uploaded_char_refs"].get(base_char)
                        if cached_u:
                            acc_cmap[(pid, base_char)] = cached_u
                            return cached_u
                chars_dir = os.path.join(WS_DIR, "flow_final_pipeline", "characters")
                for ext in ("jpg", "png", "jpeg"):
                    cand_p = os.path.join(chars_dir, f"{base_char}_ref.{ext}")
                    if os.path.isfile(cand_p) and os.path.getsize(cand_p) > 5000:
                        print(f"📤 [{pid} | {base_char.upper()} | {cur_acc}] Uploading character reference photo {os.path.basename(cand_p)}...", flush=True)
                        ok_c, c_uid, err_c = upload_single_product_ref_in_page(
                            pg, wiz, eff_project_id, cand_p, quality=96, cookie_hdr=_ACC_COOKIE_MAP.get(cur_acc, ""), prof_name=cur_acc
                        )
                        if ok_c and c_uid:
                            with STATE_LOCK:
                                acc_cmap = uploaded_char_by_acc.setdefault(cur_acc, {})
                                acc_cmap[(pid, base_char)] = c_uid
                                if cur_acc == primary_prof_name:
                                    refs_state.setdefault("uploaded_char_refs", {})[base_char] = c_uid
                            if cur_acc == primary_prof_name:
                                save_prod_state(pdir, state, refs_state)
                            print(f"✅ [{pid} | {base_char.upper()} | {cur_acc}] Uploaded character photo -> uuid={c_uid}", flush=True)
                            time.sleep(0.4)
                            return c_uid
                        else:
                            print(f"⚠️ [{pid} | {base_char.upper()} | {cur_acc}] Character photo upload failed ({err_c})", flush=True)
                return None

        runtime_abort_box = [""]
        stop_workers = threading.Event()
        active_worker_profiles = [a["profile_name"] for a in account_cookie_pool]

        def _execute_thumb_job(th_pid: str, th_vk: str, pref_prof: str):
            now_th = time.time()
            with QUEUE_LOCK:
                avail_th_run = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in quota_exhausted_accounts] or [PROF_NAME]
                healthy_th_run = [p for p in avail_th_run if not _is_prof_cooling(p, now_th)]
                if not healthy_th_run:
                    already_q = any(
                        q.get("type") == "thumb_img" and q.get("pid") == th_pid and q.get("v_key") == th_vk
                        for q in pending_queue
                    )
                    if not already_q:
                        pending_queue.append({
                            "type": "thumb_img",
                            "key": f"{th_pid}_{th_vk}_thumb",
                            "pid": th_pid,
                            "v_key": th_vk,
                            "next_retry_at": now_th + 20.0,
                        })
                    with STATE_LOCK:
                        THUMB_FUTURES_BY_KEY.pop((th_pid, th_vk), None)
                    return {"ok": False, "deferred": True, "error": "all_accounts_cooling"}
                th_prof = pref_prof if pref_prof in healthy_th_run else healthy_th_run[0]
            res = _esm.generate_thumbnail_for_variant(
                pid=th_pid,
                vkey=th_vk,
                provider=cfg.get("thumbnail_provider", "google_flow"),
                inject_01s=bool(cfg.get("auto_inject_thumbnail_01s", True)),
                add_text_badge=False,
                preferred_profile=th_prof,
            ) if _esm else {"ok": False, "error": "Thumbnail engine unavailable"}
            if res.get("ok"):
                print(f"🖼️ Thumbnail AI saved ({th_prof}): {res.get('thumbnail_path')}", flush=True)
                safe_sync_ui()
            else:
                err_th = str(res.get("error") or "")
                print(f"⚠️ Thumbnail AI failed ({th_pid}/{th_vk} | {th_prof}): {err_th}", flush=True)
                if _classify_mt_err(err_th) in ("rate_limit", "captcha_score"):
                    _mark_unhealthy(th_prof, err_th, cooldown_sec=15.0)
            return res

        def _dispatch_side_tasks():
            """Dispatch non-blocking AI thumbnails and Google Vids tasks immediately without blocking Flow workers."""
            dispatched = []
            with QUEUE_LOCK:
                now_q = time.time()
                keep_q = []
                avail_th_profs = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in quota_exhausted_accounts] or [PROF_NAME]
                healthy_th_profs = [p for p in avail_th_profs if not _is_prof_cooling(p, now_q)]
                for q_it in pending_queue:
                    q_type = q_it.get("type")
                    if float(q_it.get("next_retry_at", 0.0) or 0.0) > now_q:
                        keep_q.append(q_it)
                        continue
                    if q_type == "thumb_img":
                        if quota_all_exhausted[0]:
                            continue
                        if not healthy_th_profs:
                            q_it["next_retry_at"] = now_q + 8.0
                            keep_q.append(q_it)
                            continue
                        dispatched.append(("thumb", q_it, list(healthy_th_profs)))
                    elif q_type == "vid_scene" and VIDEO_PROVIDER == "google_vids":
                        if quota_all_exhausted[0]:
                            continue
                        dispatched.append(("vids", q_it, None))
                    else:
                        keep_q.append(q_it)
                pending_queue[:] = keep_q

            for kind_d, t_it, extra_profs in dispatched:
                pid_d = t_it["pid"]
                if kind_d == "thumb":
                    v_k = t_it["v_key"]
                    if len(extra_profs) > 1:
                        pref_th = extra_profs[thumb_rr_box[0] % len(extra_profs)]
                        thumb_rr_box[0] += 1
                    else:
                        pref_th = str(extra_profs[0] or t_it.get("preferred_account") or PROF_NAME or "").strip()

                    with STATE_LOCK:
                        THUMB_FUTURES_BY_KEY[(pid_d, v_k)] = thumb_pool.submit(_execute_thumb_job, pid_d, v_k, pref_th)
                    write_pipeline_heartbeat(f"🖼️ Thumbnail AI đang tạo song song: {pid_d} / {v_k} ({pref_th})", is_running=True)
                elif kind_d == "vids":
                    sc_id_v = t_it["sc"]["id"]
                    chosen_prof = active_flow_accs[vids_rr_box[0] % len(active_flow_accs)]["profile_name"]
                    vids_rr_box[0] += 1
                    fb_profs = [a["profile_name"] for a in active_flow_accs if a["profile_name"] != chosen_prof]
                    t_it["stage"] = "vids_1080p"
                    t_it["submitted_at"] = time.time()
                    t_it["account_name"] = chosen_prof
                    t_it["_vids_future"] = vids_pool.submit(_run_google_vids_scene_task, t_it, chosen_prof, fb_profs, VIDS_MODEL)
                    with QUEUE_LOCK:
                        inflight_tasks[t_it["key"]] = t_it
                    print(
                        f"🌐 [{pid_d} | {sc_id_v}] Dispatched Native 1080p scene ({t_it.get('scene_duration_sec', 10)}s) via Google Vids Web ({chosen_prof})!",
                        flush=True,
                    )
                    write_pipeline_heartbeat(
                        f"🌐 [{pid_d} | {sc_id_v}] Đang tạo cảnh Native 1080p qua Google Vids Web ({chosen_prof})",
                        is_running=True,
                    )

        def _maybe_queue_variant_thumb(pid_th: str, v_k: str, pref_acc: str = ""):
            if not (cfg.get("auto_generate_thumbnail", True) and _esm is not None):
                return
            meta_entry = prod_meta.get(pid_th)
            if not meta_entry:
                return
            pdir_th, prompts_th, _, _ = meta_entry
            v_inf = (prompts_th.get("videos") or {}).get(v_k)
            if not v_inf:
                return
            char_v_th = v_inf.get("char_v") or get_final_video_filename(pid_th, v_k).replace(f"{pid_th}_", "").replace(".mp4", "")
            out_thumb_th = os.path.join(pdir_th, "thumbnails", f"{pid_th}_{char_v_th}_thumb.jpg")
            if os.path.exists(out_thumb_th) and os.path.getsize(out_thumb_th) > 10000:
                return
            with QUEUE_LOCK:
                avail_th = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in quota_exhausted_accounts] or [PROF_NAME]
                healthy_th = [p for p in avail_th if not _is_prof_cooling(p, time.time())]
                if not healthy_th:
                    already_queued_th = any(
                        q.get("type") == "thumb_img" and q.get("pid") == pid_th and q.get("v_key") == v_k
                        for q in pending_queue
                    )
                    if not already_queued_th:
                        pending_queue.append({
                            "type": "thumb_img",
                            "key": f"{pid_th}_{v_k}_thumb",
                            "pid": pid_th,
                            "v_key": v_k,
                            "next_retry_at": time.time() + 10.0,
                        })
                    return
            with STATE_LOCK:
                if (pid_th, v_k) in THUMB_FUTURES_BY_KEY:
                    return
                chosen_th = (
                    pref_acc if (pref_acc and pref_acc in healthy_th) else healthy_th[thumb_rr_box[0] % len(healthy_th)]
                )
                thumb_rr_box[0] += 1

                THUMB_FUTURES_BY_KEY[(pid_th, v_k)] = thumb_pool.submit(_execute_thumb_job, pid_th, v_k, chosen_th)

        def _pick_task_for_worker(prof_name: str, now_q: float):
            with QUEUE_LOCK:
                if not pending_queue:
                    return None
                last_acc_t = acc_last_submit_ts.get(prof_name.lower(), 0.0)
                if last_acc_t > 0.0 and (now_q - last_acc_t) < SUBMIT_DELAY_SEC:
                    return None
                # Single-probe recovery: if account is in [8] streak >= 2, allow only 1 worker to probe until healthy
                if int(rate_limit_streak.get(prof_name, 0) or 0) >= 2 and any(
                    tk_s.get("_sub_prof") == prof_name for tk_s in in_submit_tasks.values()
                ):
                    return None
                prof_exhausted = prof_name in quota_exhausted_accounts
                active_gen_cnt = sum(
                    1 for tk in inflight_tasks.values() if tk.get("stage") != "upsample_1080p"
                ) + sum(
                    1 for tk in in_submit_tasks.values() if tk.get("type") not in ("upsample_1080p", "upsample_ref_2k", "thumb_img")
                )
                active_up_cnt = sum(
                    1 for tk in inflight_tasks.values() if tk.get("stage") == "upsample_1080p"
                ) + sum(
                    1 for tk in in_submit_tasks.values() if tk.get("type") in ("upsample_1080p", "upsample_ref_2k")
                )
                acc_gen_cnt = sum(
                    1 for tk in inflight_tasks.values()
                    if tk.get("stage") != "upsample_1080p"
                    and str(tk.get("account_name") or tk.get("preferred_account") or primary_prof_name).strip() == prof_name
                ) + sum(
                    1 for tk in in_submit_tasks.values()
                    if tk.get("_sub_prof") == prof_name
                    and tk.get("type") not in ("upsample_1080p", "upsample_ref_2k", "thumb_img")
                )
                busy_other_variants = {
                    (tk_v.get("pid"), tk_v.get("v_key"))
                    for tk_v in in_submit_tasks.values()
                    if tk_v.get("_sub_prof") != prof_name and tk_v.get("type") == "vid_scene"
                }
                busy_same_acc_unready = {
                    (tk_v.get("pid"), tk_v.get("v_key"))
                    for tk_v in in_submit_tasks.values()
                    if tk_v.get("_sub_prof") == prof_name
                    and tk_v.get("type") == "vid_scene"
                    and (prof_name, tk_v.get("pid"), tk_v.get("v_key")) not in acc_variant_uploads
                }
                pending_2k_variants = {
                    (tk2.get("pid"), tk2.get("v_key"))
                    for tk2 in list(pending_queue) + list(in_submit_tasks.values())
                    if tk2.get("type") == "upsample_ref_2k"
                }

                tier0_idx = None
                tier1_idx = None
                tier2_idx = None
                tier3_idx = None

                for idx_q, q_it in enumerate(pending_queue):
                    q_type = q_it.get("type")
                    if q_type == "thumb_img" or (q_type == "vid_scene" and VIDEO_PROVIDER == "google_vids"):
                        continue
                    if q_type == "vid_scene" and (q_it.get("pid"), q_it.get("v_key")) in pending_2k_variants:
                        continue
                    if float(q_it.get("next_retry_at", 0.0) or 0.0) > now_q:
                        continue
                    if q_type == "upsample_1080p":
                        owner_p = str(q_it.get("preferred_account") or q_it.get("owner_account") or primary_prof_name).strip()
                        if owner_p in active_worker_profiles and owner_p != prof_name:
                            continue
                        if active_up_cnt < max(UPSCALE_DL_WORKERS, 24):
                            if int(q_it.get("retries", 0) or 0) == 0 or acc_gen_cnt >= MAX_INFLIGHT_PER_ACC:
                                if tier0_idx is None:
                                    tier0_idx = idx_q
                                    break
                            elif tier2_idx is None:
                                tier2_idx = idx_q
                        continue

                    if q_type == "upsample_ref_2k":
                        owner_p = str(q_it.get("preferred_account") or q_it.get("owner_account") or primary_prof_name).strip()
                        if owner_p in active_worker_profiles and owner_p != prof_name:
                            continue
                        if prof_exhausted:
                            continue
                        if tier2_idx is None:
                            tier2_idx = idx_q
                        continue

                    if prof_exhausted:
                        continue
                    if active_gen_cnt >= MAX_INFLIGHT or acc_gen_cnt >= MAX_INFLIGHT_PER_ACC:
                        continue
                    pref_p = str(q_it.get("preferred_account") or "").strip()
                    if pref_p and pref_p != prof_name and (pref_p in active_worker_profiles) and not _is_prof_cooling(pref_p, now_q):
                        continue

                    vk_pair = (q_it.get("pid"), q_it.get("v_key"))
                    owner_q = str(q_it.get("owner_account") or "").strip()
                    owned_by_healthy_other = bool(
                        owner_q
                        and owner_q != prof_name
                        and owner_q in active_worker_profiles
                        and not _is_prof_cooling(owner_q, now_q)
                    )
                    is_affinity = (
                        q_type == "vid_scene"
                        and (
                            (prof_name, q_it.get("pid"), q_it.get("v_key")) in acc_variant_uploads
                            or owner_q == prof_name
                        )
                    )
                    if is_affinity and vk_pair not in busy_other_variants and vk_pair not in busy_same_acc_unready:
                        if tier1_idx is None:
                            tier1_idx = idx_q
                    elif (not owned_by_healthy_other) and vk_pair not in busy_other_variants and vk_pair not in busy_same_acc_unready:
                        if tier2_idx is None:
                            tier2_idx = idx_q
                    else:
                        if tier3_idx is None:
                            tier3_idx = idx_q

                pick_idx = tier0_idx if tier0_idx is not None else (
                    tier1_idx if tier1_idx is not None else (
                        tier2_idx if tier2_idx is not None else tier3_idx
                    )
                )
                if pick_idx is None:
                    return None
                t_picked = pending_queue.pop(pick_idx)
                t_picked["_sub_prof"] = prof_name
                in_submit_tasks[t_picked["key"]] = t_picked
                acc_last_submit_ts[prof_name.lower()] = now_q
                return t_picked

        def _execute_single_task(t: dict, prof_name: str):
            pid = t["pid"]
            pdir, prompts_data, state, refs_state = prod_meta[pid]
            t_type = t.get("type")
            try:
                st_entry = _open_single_acc_context(
                    prof_name,
                    project_id_hint=t.get("project_id") or _resolve_default_flow_pid(prof_name),
                )
                pg = st_entry["pg"]
                wiz = st_entry["wiz"]
                ck_hdr = st_entry["cookie_hdr"]
                dl_hdrs = dict(st_entry["dl_headers"])
                eff_proj_id = st_entry["project_id"] or t["project_id"]
                t["project_id"] = eff_proj_id
                t["worker_profile"] = prof_name
                t["cookie_hdr"] = ck_hdr
                t["wiz"] = wiz
                t["dl_headers"] = dl_hdrs
                st_entry["uses"] = st_entry.get("uses", 0) + 1
                with QUEUE_LOCK:
                    now_sub = time.time()
                    last_submit_ts[0] = now_sub
                    acc_last_submit_ts[prof_name.lower()] = now_sub

                if t_type == "upsample_ref_2k":
                    v_key = t["v_key"]
                    with _SPRCAD_LOCK:
                        skip_spr = time.time() < _SPRCAD_SKIP_UNTIL[0]
                    if hasattr(gvt, "is_sprcad_circuit_open") and gvt.is_sprcad_circuit_open():
                        skip_spr = True
                    if skip_spr and os.path.exists(t["out_file"]):
                        ok_2k, nbytes_2k, err_2k = False, 0, "SPrCad skipped (cooldown)"
                    else:
                        ok_2k, nbytes_2k, err_2k = upsample_image_2k_in_page(
                            pg, wiz, eff_proj_id, t["ref_uuid"], t["out_file"], cookie_hdr=ck_hdr, prof_name=prof_name
                        )
                        with _SPRCAD_LOCK:
                            if ok_2k and nbytes_2k > 50000:
                                _SPRCAD_CONSEC_FAILS[0] = 0
                            else:
                                _SPRCAD_CONSEC_FAILS[0] += 1
                                if _SPRCAD_CONSEC_FAILS[0] >= 3:
                                    _SPRCAD_SKIP_UNTIL[0] = max(_SPRCAD_SKIP_UNTIL[0], time.time() + 300.0)
                        if hasattr(gvt, "record_sprcad_result"):
                            gvt.record_sprcad_result(bool(ok_2k and nbytes_2k > 50000), str(err_2k or ""))
                    if not (ok_2k and nbytes_2k > 50000) and os.path.exists(t["out_file"]):
                        ok_2k, nbytes_2k = _local_upscale_2k_fallback(t["out_file"])
                    if ok_2k and nbytes_2k > 50000:
                        eff_ref_uuid = t["ref_uuid"]
                        u_id_ref = None
                        if t.get("primary_prod_img") and os.path.isfile(t["primary_prod_img"]):
                            u_id_ref = ensure_single_prod_uuid(
                                pid,
                                pdir,
                                state,
                                refs_state,
                                t.get("base_char") or "nv1",
                                eff_proj_id,
                                t["primary_prod_img"],
                                pg=pg,
                                wiz=wiz,
                                cur_acc=prof_name,
                            )
                        if not u_id_ref:
                            u_id_ref = t.get("prod_uuid")
                        ok_u2k = False
                        try:
                            ok_u2k, uuid_2k, _ = upload_single_product_ref_in_page(
                                pg, wiz, eff_proj_id, t["out_file"], quality=98, cookie_hdr=ck_hdr, prof_name=prof_name
                            )
                            if ok_u2k and uuid_2k:
                                eff_ref_uuid = uuid_2k
                                ref_rel_name = t.get("ref_img_rel") or os.path.basename(t["out_file"])
                                with STATE_LOCK:
                                    state["uploaded_refs"][ref_rel_name] = uuid_2k
                                    if v_key not in refs_state.get("variants", {}) and t.get("ref_img_rel"):
                                        refs_state["variants"][v_key] = {
                                            "ref_image": t["ref_img_rel"],
                                            "ref_image_uuid": uuid_2k,
                                            "ref_image_path": t["out_file"],
                                            "style": t.get("style", ""),
                                        }
                                    elif v_key in refs_state.get("variants", {}):
                                        refs_state["variants"][v_key]["ref_image_uuid"] = uuid_2k
                                save_prod_state(pdir, state, refs_state)
                                with QUEUE_LOCK:
                                    if eff_ref_uuid and u_id_ref:
                                        acc_variant_uploads[(prof_name, pid, v_key)] = (eff_ref_uuid, u_id_ref)
                                    for q_item in pending_queue:
                                        if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") in ("vid_scene", "thumb_img"):
                                            q_item["ref_uuid"] = uuid_2k
                                            q_item["owner_account"] = prof_name
                                            if u_id_ref:
                                                q_item["prod_uuid"] = u_id_ref
                            else:
                                with QUEUE_LOCK:
                                    acc_variant_uploads.pop((prof_name, pid, v_key), None)
                                    for q_item in pending_queue:
                                        if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") == "vid_scene":
                                            q_item["_need_ref_reupload"] = True
                                            q_item["owner_account"] = prof_name
                        except Exception:
                            with QUEUE_LOCK:
                                for q_item in pending_queue:
                                    if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") == "vid_scene":
                                        q_item["_need_ref_reupload"] = True
                        if t.get("queue_scenes_after"):
                            new_scene_tasks = _build_variant_followup_tasks(
                                t,
                                gen_uuid=eff_ref_uuid,
                                u_id=u_id_ref,
                                eff_proj_id=eff_proj_id,
                                owner_acc=prof_name,
                                pdir=pdir,
                                flow_video_model=FLOW_VIDEO_MODEL,
                            )
                            if not ok_u2k and new_scene_tasks:
                                new_scene_tasks[0]["_need_ref_reupload"] = True
                            with QUEUE_LOCK:
                                if eff_ref_uuid and u_id_ref:
                                    acc_variant_uploads[(prof_name, pid, v_key)] = (eff_ref_uuid, u_id_ref)
                                pending_queue[:0] = new_scene_tasks
                        _clear_task_scene_error(t)
                        _mark_acc_healthy(prof_name)
                        print(f"✨ [{pid} | {v_key.upper()}] Ref Image 2K (1536x2752) & re-uploaded ({nbytes_2k//1024} KB) -> media_uuid={eff_ref_uuid}!", flush=True)
                        safe_sync_ui()
                    else:
                        print(f"⚠️ [{pid} | {v_key.upper()} 2K | {prof_name}] SPrCad failed ({err_2k}) ({t['retries'] + 1}/4)", flush=True)
                        _schedule_mt_retry(t, err_2k, max_retries_cap=4, front=False)
                        if _classify_mt_err(err_2k) != "rate_limit":
                            _handle_task_failure_switch(t["project_id"], prof_name, err_2k)

                elif t_type == "ref_img":
                    v_key = t["v_key"]
                    base_char = t["base_char"]
                    need_reup_ref = bool(t.pop("_need_ref_reupload", False))
                    u_id = ensure_single_prod_uuid(
                        pid, pdir, state, refs_state, base_char, eff_proj_id, t["primary_prod_img"],
                        pg=pg, wiz=wiz, cur_acc=prof_name, force_reupload=need_reup_ref,
                    )
                    if not u_id:
                        _schedule_mt_retry(t, "upload_prod_ref_failed", max_retries_cap=10, front=True)
                        _handle_task_failure_switch(t["project_id"], prof_name, "upload_prod_ref_failed")
                        return
                    eff_char_id_acc = t.get("char_id") or ""
                    if eff_char_id_acc:
                        try:
                            import character_library_manager as _clm_cid
                            if hasattr(_clm_cid, "resolve_character_id_for_account"):
                                eff_char_id_acc = _clm_cid.resolve_character_id_for_account(eff_char_id_acc, prof_name)
                        except Exception:
                            eff_char_id_acc = ""
                    t["char_id"] = eff_char_id_acc
                    if not eff_char_id_acc and not t.get("pov_only"):
                        c_photo_uuid = ensure_char_photo_uuid(
                            pid, pdir, state, refs_state, base_char, eff_proj_id, pg=pg, wiz=wiz, cur_acc=prof_name
                        )
                        if c_photo_uuid:
                            t["prod_uuids"] = [c_photo_uuid, u_id]
                            t["allow_multi_refs"] = True
                        else:
                            t["prod_uuids"] = [u_id]
                    else:
                        t["prod_uuids"] = [u_id]
                    t["prod_uuid"] = u_id
                    t["project_id"] = eff_proj_id
                    ok_sub, gen_uuid, _, err_sub = submit_ref_image_ogi_in_page(pg, wiz, t)
                    if ok_sub and gen_uuid:
                        t["media_uuid"] = gen_uuid
                        t["stage"] = "ref_img_poll"
                        t["submitted_at"] = time.time()
                        t["cookie_hdr"] = ck_hdr
                        t["wiz"] = wiz
                        t["dl_headers"] = dl_hdrs
                        t["account_name"] = prof_name
                        t["owner_account"] = prof_name
                        t["preferred_account"] = prof_name
                        with QUEUE_LOCK:
                            inflight_tasks[t["key"]] = t
                        _clear_task_scene_error(t)
                        _mark_acc_healthy(prof_name)
                        write_pipeline_heartbeat(f"🖼️ [{pid} | {v_key.upper()}] Đang tạo ảnh Ref Nano Banana 2.1 ({prof_name})...", is_running=True)
                    else:
                        print(f"⚠️ [{pid} | {v_key} REF | {prof_name}] ogiZ0b submit failed ({err_sub}) (retry {t['retries'] + 1}/12)...", flush=True)
                        _schedule_mt_retry(t, err_sub, max_retries_cap=12, front=True)
                        _handle_task_failure_switch(t["project_id"], prof_name, err_sub)

                elif t_type == "upsample_1080p":
                    sc_id = t["sc"]["id"]
                    t["project_id"] = eff_proj_id
                    if not t.get("base_video_uuid") and t.get("media_uuid"):
                        t["base_video_uuid"] = str(t["media_uuid"]).removesuffix("_upsampled")
                    if not t.get("base_video_uuid"):
                        print(f"⚠️ [{pid} | {sc_id}] Thiếu base_video_uuid cho upsample_1080p -> chuyển về render lại vid_scene.", flush=True)
                        t["type"] = "vid_scene"
                        t["stage"] = "base_720p"
                        t["media_uuid"] = None
                        t.pop("preferred_account", None)
                        _schedule_mt_retry(t, "missing_base_video_uuid", max_retries_cap=12, front=False)
                        return
                    ok, up_uuid, err = submit_upsample_1080p_in_page(pg, wiz, t)
                    if ok and up_uuid:
                        t["media_uuid"] = up_uuid
                        t["stage"] = "upsample_1080p"
                        t["submitted_at"] = time.time()
                        t["cookie_hdr"] = ck_hdr
                        t["wiz"] = wiz
                        t["dl_headers"] = dl_hdrs
                        t["account_name"] = prof_name
                        t["preferred_account"] = prof_name
                        with STATE_LOCK:
                            state["scene_uuids"][sc_id] = up_uuid
                            state.setdefault("scene_accounts", {})[sc_id] = prof_name
                        save_prod_state(pdir, state)
                        with QUEUE_LOCK:
                            inflight_tasks[t["key"]] = t
                        _clear_task_scene_error(t)
                        _mark_acc_healthy(prof_name)
                        write_pipeline_heartbeat(f"✨ [{pid} | {sc_id}] Đang Upsample 1080p ({prof_name})...", is_running=True)
                    else:
                        print(f"⚠️ [{pid} | {sc_id} | {prof_name}] 1080p Upsample submit failed ({err}) ({t['retries'] + 1}/12)...", flush=True)
                        err_up_str = str(err or "")
                        if "[5]" in err_up_str or "NOT_FOUND" in err_up_str.upper():
                            tried_accs = t.setdefault("_upsample_tried_accs", [])
                            if prof_name not in tried_accs:
                                tried_accs.append(prof_name)
                            alt_up_accs = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in tried_accs]
                            if alt_up_accs:
                                next_up = alt_up_accs[0]
                                t["preferred_account"] = next_up
                                print(f"🔁 [{pid} | {sc_id}] p0UkFb [5] trên {prof_name} -> thử chủ sở hữu {next_up}...", flush=True)
                                _schedule_mt_retry(t, err, max_retries_cap=12, front=True)
                                return
                            if os.path.exists(t["out_mp4"] + ".720p.tmp"):
                                shutil.move(t["out_mp4"] + ".720p.tmp", t["out_mp4"])
                                print(f"⚠️ [{pid} | {sc_id}] All accounts returned p0UkFb [5] -> promoted 720p backup", flush=True)
                                safe_sync_ui()
                                check_and_queue_ffmpeg(
                                    ffmpeg_pool, ffmpeg_futures, pid, pdir, t["v_key"], prompts_data["videos"][t["v_key"]]["scenes"]
                                )
                                return
                            t["type"] = "vid_scene"
                            t["stage"] = "base_720p"
                            t["media_uuid"] = None
                            t["base_video_uuid"] = None
                            t.pop("preferred_account", None)
                            with STATE_LOCK:
                                state["scene_uuids"].pop(sc_id, None)
                                (state.get("scene_accounts") or {}).pop(sc_id, None)
                            save_prod_state(pdir, state)
                            _schedule_mt_retry(t, err, max_retries_cap=12, front=False)
                            return
                        t["preferred_account"] = t.get("account_name") or prof_name
                        use_front = (int(t.get("retries", 0) or 0) == 0 and _classify_mt_err(err) != "rate_limit")
                        if not _schedule_mt_retry(t, err, max_retries_cap=12, front=use_front) and os.path.exists(t["out_mp4"] + ".720p.tmp"):
                            shutil.move(t["out_mp4"] + ".720p.tmp", t["out_mp4"])
                            print(f"⚠️ [{pid} | {sc_id}] Falling back to 720p MP4 after upsample failure", flush=True)
                            safe_sync_ui()
                            check_and_queue_ffmpeg(
                                ffmpeg_pool, ffmpeg_futures, pid, pdir, t["v_key"], prompts_data["videos"][t["v_key"]]["scenes"]
                            )
                        _handle_task_failure_switch(
                            t["project_id"],
                            prof_name,
                            err,
                            prefer_profile=t.get("preferred_account"),
                            rotate_next=False,
                        )

                else:
                    sc_id = t["sc"]["id"]
                    v_key = t["v_key"]
                    owner_acc = t.get("owner_account") or primary_prof_name
                    with QUEUE_LOCK:
                        cached_pair = acc_variant_uploads.get((prof_name, pid, v_key))
                    if cached_pair:
                        t["ref_uuid"], t["prod_uuid"] = cached_pair
                        t["owner_account"] = prof_name
                    elif not t.get("prod_uuid"):
                        u_id = ensure_single_prod_uuid(
                            pid, pdir, state, refs_state, t["base_char"], eff_proj_id, t["primary_prod_img"], pg=pg, wiz=wiz, cur_acc=prof_name
                        )
                        if u_id:
                            t["prod_uuid"] = u_id
                            if prof_name == primary_prof_name:
                                with QUEUE_LOCK:
                                    for q_item in pending_queue:
                                        if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") in ("vid_scene", "thumb_img"):
                                            q_item["prod_uuid"] = u_id

                    # Chỉ upload lại Ref 2K khi đổi tài khoản, thiếu ref_uuid, hoặc lỗi NOT_FOUND/INVALID ở lần thử trước
                    if (t.get("owner_account") or owner_acc) != prof_name or not t.get("ref_uuid") or t.get("_need_ref_reupload"):
                        if not cached_pair or t.get("_need_ref_reupload") or not t.get("ref_uuid"):
                            need_force_reup = bool(t.pop("_need_ref_reupload", None))
                            ref_img_local = t.get("ref_img_abs") or os.path.join(pdir, prompts_data["videos"][v_key]["ref_image"])
                            if os.path.isfile(ref_img_local):
                                ok_r, new_ref_u, _ = upload_single_product_ref_in_page(
                                    pg, wiz, eff_proj_id, ref_img_local, quality=98, cookie_hdr=ck_hdr, prof_name=prof_name
                                )
                                if ok_r and new_ref_u:
                                    t["ref_uuid"] = new_ref_u
                                    if prof_name == primary_prof_name:
                                        with STATE_LOCK:
                                            state["uploaded_refs"][os.path.basename(ref_img_local)] = new_ref_u
                                            if v_key in refs_state.get("variants", {}):
                                                refs_state["variants"][v_key]["ref_image_uuid"] = new_ref_u
                                    time.sleep(1.2)
                            new_prod_u = ensure_single_prod_uuid(
                                pid,
                                pdir,
                                state,
                                refs_state,
                                t["base_char"],
                                eff_proj_id,
                                t["primary_prod_img"],
                                pg=pg,
                                wiz=wiz,
                                cur_acc=prof_name,
                                force_reupload=need_force_reup,
                            )
                            if new_prod_u:
                                t["prod_uuid"] = new_prod_u
                            with QUEUE_LOCK:
                                if t.get("ref_uuid") and t.get("prod_uuid"):
                                    acc_variant_uploads[(prof_name, pid, v_key)] = (t["ref_uuid"], t["prod_uuid"])
                                    for _q_sib in pending_queue:
                                        if (
                                            _q_sib.get("pid") == pid
                                            and _q_sib.get("v_key") == v_key
                                            and _q_sib.get("type") in ("vid_scene", "thumb_img")
                                            and (not _q_sib.get("owner_account") or _q_sib.get("owner_account") == prof_name)
                                        ):
                                            _q_sib["ref_uuid"] = t["ref_uuid"]
                                            _q_sib["prod_uuid"] = t["prod_uuid"]
                                            _q_sib["owner_account"] = prof_name
                            t["owner_account"] = prof_name
                            if prof_name == primary_prof_name:
                                save_prod_state(pdir, state, refs_state)

                    t["project_id"] = eff_proj_id
                    t["worker_profile"] = prof_name
                    ok, ret_uuid, err = submit_scene_in_page(pg, wiz, t)
                    if ok and ret_uuid:
                        t["media_uuid"] = ret_uuid
                        t["stage"] = "base_720p"
                        t["submitted_at"] = time.time()
                        t["cookie_hdr"] = ck_hdr
                        t["wiz"] = wiz
                        t["dl_headers"] = dl_hdrs
                        t["account_name"] = prof_name
                        t["preferred_account"] = prof_name
                        with STATE_LOCK:
                            state["scene_uuids"][sc_id] = ret_uuid
                            state.setdefault("scene_accounts", {})[sc_id] = prof_name
                        save_prod_state(pdir, state)
                        with QUEUE_LOCK:
                            inflight_tasks[t["key"]] = t
                            live_cr = t.get("_last_credits_left")
                            if isinstance(live_cr, int) and 0 <= live_cr < 10:
                                quota_exhausted_accounts.add(prof_name)
                                print(f"⛔ [TK:{prof_name}] Credit còn {live_cr} (<10) -> tự động ngừng nhận cảnh mới trên tài khoản này.", flush=True)
                                avail_rem = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in quota_exhausted_accounts]
                                if not avail_rem:
                                    quota_all_exhausted[0] = True
                                    pending_queue[:] = [q for q in pending_queue if q.get("type") in ("upsample_1080p", "upsample_ref_2k")]
                        _clear_task_scene_error(t)
                        _mark_acc_healthy(prof_name)
                        write_pipeline_heartbeat(f"🚀 [{pid} | {sc_id}] Đã gửi render cảnh 10s ({prof_name})", is_running=True)
                    else:
                        print(f"⚠️ [{pid} | {sc_id} | {prof_name}] Submit failed ({err}) (retry {t['retries'] + 1}/12)...", flush=True)
                        _schedule_mt_retry(t, err, max_retries_cap=12, front=True)
                        _handle_task_failure_switch(t["project_id"], prof_name, err)
            except Exception as exc_t:
                print(f"⚠️ [{pid} | {t.get('key')} | {prof_name}] Submit worker exception: {exc_t}", flush=True)
                _schedule_mt_retry(t, str(exc_t), max_retries_cap=12, front=False)
                _mark_unhealthy(prof_name, str(exc_t), cooldown_sec=12.0)
            finally:
                with QUEUE_LOCK:
                    in_submit_tasks.pop(t["key"], None)

        def _account_submit_worker(prof_name: str, slot_idx: int = 0):
            if slot_idx > 0:
                stop_workers.wait(min(6.0, slot_idx * 2.2))
            while not stop_workers.is_set() and not runtime_abort_box[0]:
                now_w = time.time()
                with QUEUE_LOCK:
                    has_free_upsample = any(
                        q.get("type") in ("upsample_1080p", "upsample_ref_2k")
                        and str(q.get("preferred_account") or q.get("owner_account") or primary_prof_name).strip() == prof_name
                        for q in pending_queue
                    )
                    has_inflight_for_prof = any(
                        str(tk.get("account_name") or tk.get("preferred_account") or primary_prof_name).strip() == prof_name
                        for tk in inflight_tasks.values()
                    )
                    is_exh = prof_name in quota_exhausted_accounts
                if is_exh and not has_free_upsample:
                    if quota_all_exhausted[0] and not has_inflight_for_prof:
                        break
                    stop_workers.wait(0.5)
                    continue
                if not is_exh and _is_prof_cooling(prof_name, now_w):
                    stop_workers.wait(0.5)
                    continue
                if is_exh and rate_limit_until.get(prof_name, 0.0) > now_w:
                    stop_workers.wait(0.5)
                    continue
                with QUEUE_LOCK:
                    last_acc_t = acc_last_submit_ts.get(prof_name.lower(), 0.0)
                acc_wait = (last_acc_t + SUBMIT_DELAY_SEC - now_w) if last_acc_t > 0 else 0.0
                if acc_wait > 0.05:
                    stop_workers.wait(min(0.5, acc_wait))
                    continue

                t_job = _pick_task_for_worker(prof_name, time.time())
                if t_job is None:
                    stop_workers.wait(0.25)
                    continue
                _execute_single_task(t_job, prof_name)

        for _pid_ff, _pdir_ff, _vkey_ff, _sc_ff in initial_ffmpeg_checks:
            check_and_queue_ffmpeg(ffmpeg_pool, ffmpeg_futures, _pid_ff, _pdir_ff, _vkey_ff, _sc_ff)

        workers_per_acc = 2 if _EXT_BRIDGE_BOX[0] is not None else 1
        worker_slot_pairs = [
            (_wp, _sidx) for _sidx in range(workers_per_acc) for _wp in active_worker_profiles
        ]
        submit_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(worker_slot_pairs)))
        submit_futures = [submit_pool.submit(_account_submit_worker, _wp, _sidx) for _wp, _sidx in worker_slot_pairs]
        ffp_dir_coord = os.path.dirname(SCRIPTS_DIR)
        pending_pids_file = os.path.join(ffp_dir_coord, "pending_batch_pids.json")
        cancelled_pids_file = os.path.join(ffp_dir_coord, "cancelled_batch_pids.json")
        active_runner_file = os.path.join(ffp_dir_coord, "active_mt_runner.json")
        last_coord_check_ts = [0.0]

        def _sync_dynamic_batch_controls():
            now_c = time.time()
            if (now_c - last_coord_check_ts[0]) < 1.8:
                return
            last_coord_check_ts[0] = now_c
            # 1) Check per-PID cooperative cancellations
            if os.path.isfile(cancelled_pids_file):
                try:
                    canc_list = json.load(open(cancelled_pids_file, "r", encoding="utf-8"))
                    if isinstance(canc_list, list) and canc_list:
                        canc_set = {str(x).strip() for x in canc_list if str(x).strip()}
                        hit_canc = [p for p in list(only_pids) if p in canc_set]
                        for c_pid in hit_canc:
                            with QUEUE_LOCK:
                                pending_queue[:] = [q for q in pending_queue if q.get("pid") != c_pid]
                                for ik in [k for k, v in inflight_tasks.items() if v.get("pid") == c_pid]:
                                    inflight_tasks.pop(ik, None)
                            if c_pid in only_pids:
                                only_pids.remove(c_pid)
                            c_st_path = os.path.join(PROJECTS_DIR, c_pid, "pipeline_status.json")
                            if os.path.isdir(os.path.dirname(c_st_path)):
                                gvt.atomic_write_json(
                                    c_st_path,
                                    {
                                        "pid": c_pid,
                                        "pid_os": 0,
                                        "is_running": False,
                                        "current_step_text": "⏹️ Đã tạm dừng sản phẩm theo yêu cầu người dùng.",
                                        "updated_at": time.strftime("%H:%M:%S"),
                                    },
                                )
                            print(f"⏹️ [{c_pid}] Đã dừng riêng sản phẩm này theo yêu cầu (các sản phẩm khác tiếp tục chạy bình thường).", flush=True)
                except Exception:
                    pass
            # 2) Check newly added products in pending_batch_pids.json
            if os.path.isfile(pending_pids_file):
                try:
                    pend_list = json.load(open(pending_pids_file, "r", encoding="utf-8"))
                    if isinstance(pend_list, list) and pend_list:
                        gvt.atomic_write_json(pending_pids_file, [])
                        for new_pid in pend_list:
                            s_np = str(new_pid or "").strip()
                            if s_np and s_np not in only_pids:
                                print(f"➕ [{s_np}] Tự động nạp nóng sản phẩm mới vào luồng Đa Tài Khoản đang chạy!", flush=True)
                                only_pids.append(s_np)
                                _enqueue_single_product(s_np)
                except Exception:
                    pass

        loop_start = time.time()
        while True:
            _sync_dynamic_batch_controls()
            _dispatch_side_tasks()
            with QUEUE_LOCK:
                if quota_all_exhausted[0]:
                    has_remaining_up = any(
                        q.get("type") in ("upsample_1080p", "upsample_ref_2k") for q in pending_queue
                    ) or any(
                        tk.get("stage") in ("base_720p", "upsample_1080p", "ref_img_poll", "upsample_ref_2k")
                        for tk in inflight_tasks.values()
                    ) or any(
                        tk.get("type") in ("upsample_1080p", "upsample_ref_2k")
                        for tk in in_submit_tasks.values()
                    )
                    if not has_remaining_up:
                        runtime_abort_box[0] = "Đã hết credit trên toàn bộ tài khoản Google Flow."
                        break
                has_work = bool(inflight_tasks or pending_queue or in_submit_tasks)
                if not has_work or runtime_abort_box[0]:
                    break
                cur_inflight_snap = list(inflight_tasks.values())

            time.sleep(1.5 if cur_inflight_snap else 0.6)
            if not cur_inflight_snap:
                continue

            def _poll_inflight_item(tk):
                if tk.get("stage") == "ref_img_poll":
                    return poll_ref_image_one(cookie_hdr_box[0], wiz_box[0], dl_headers_box[0], tk)
                vfut = tk.get("_vids_future")
                if vfut is not None:
                    if not vfut.done():
                        return "running_vids_1080p", None
                    try:
                        vres = vfut.result()
                    except Exception as vexc:
                        print(f"⚠️ [VIDS-ERR {tk.get('key')}] {vexc}", flush=True)
                        return "failed_vids", None
                    if vres and vres.get("ok"):
                        return "done", vres.get("bytes") or os.path.getsize(tk["out_mp4"])
                    print(f"⚠️ [VIDS-FAIL {tk.get('key')}] {(vres or {}).get('error')}", flush=True)
                    return "failed_vids", None
                tk_acc = str(tk.get("account_name") or tk.get("preferred_account") or primary_prof_name).strip()
                st_acc = acc_contexts.get(tk_acc)
                if not tk.get("wiz") and st_acc:
                    tk["wiz"] = st_acc["wiz"]
                    tk["cookie_hdr"] = st_acc["cookie_hdr"]
                    tk["dl_headers"] = dict(st_acc["dl_headers"])
                    if st_acc.get("project_id"):
                        tk["project_id"] = st_acc["project_id"]
                if not (tk.get("wiz") or (tk_acc == primary_prof_name and wiz_box[0])):
                    return "running_init", None
                return poll_and_download_one(cookie_hdr_box[0], wiz_box[0], dl_headers_box[0], tk)

            poll_futs = {
                poll_pool.submit(_poll_inflight_item, t): t
                for t in cur_inflight_snap
            }
            status_summary = []
            for fut in concurrent.futures.as_completed(poll_futs):
                t = poll_futs[fut]
                t_key = t["key"]
                pid = t["pid"]
                v_key = t["v_key"]
                sc_id = (t.get("sc") or {}).get("id") or f"{v_key}_ref"
                pdir, prompts_data, state, _ = prod_meta[pid]
                try:
                    res_state, nbytes = fut.result()
                except Exception as poll_exc:
                    print(f"⚠️ [POLL-WORKER-EXC {pid} | {sc_id}] {type(poll_exc).__name__}: {poll_exc}", flush=True)
                    res_state, nbytes = f"rpc_err:{type(poll_exc).__name__}", None

                elapsed = int(time.time() - t["submitted_at"])
                if res_state == "ready_for_2k_ref":
                    _clear_task_scene_error(t)
                    print(f"🖼️ [{pid} | {v_key.upper()}] Base Ref ready ({nbytes//1024} KB in {elapsed}s) -> queueing 2K SPrCad...", flush=True)
                    t["type"] = "upsample_ref_2k"
                    t["stage"] = "upsample_ref_2k"
                    t["ref_uuid"] = t["media_uuid"]
                    t["media_uuid"] = None
                    t["retries"] = 0
                    t["queue_scenes_after"] = True
                    t["next_retry_at"] = 0.0
                    t["preferred_account"] = t.get("owner_account") or primary_prof_name
                    with QUEUE_LOCK:
                        inflight_tasks.pop(t_key, None)
                        pending_queue.insert(0, t)

                elif res_state == "ready_for_1080p":
                    _clear_task_scene_error(t)
                    print(f"🎬 [{pid} | {sc_id}] Base 720p ready ({nbytes//1024} KB in {elapsed}s) -> queueing 1080p Upsample (p0UkFb)...", flush=True)
                    t["type"] = "upsample_1080p"
                    t["stage"] = "upsample_1080p"
                    t["base_video_uuid"] = t["media_uuid"]
                    t["media_uuid"] = None
                    t["retries"] = 0
                    t["next_retry_at"] = 0.0
                    t["preferred_account"] = t.get("account_name") or primary_prof_name
                    with QUEUE_LOCK:
                        inflight_tasks.pop(t_key, None)
                        pending_queue.insert(0, t)

                elif res_state == "done":
                    _clear_task_scene_error(t)
                    print(f"📥 [{pid} | {sc_id}] Downloaded 1080p MP4 ({nbytes//1024} KB in {elapsed}s)!", flush=True)
                    done_acc = t.get("account_name") or primary_prof_name
                    _mark_acc_healthy(done_acc)
                    with QUEUE_LOCK:
                        inflight_tasks.pop(t_key, None)
                    _maybe_queue_variant_thumb(pid, v_key, pref_acc=done_acc)
                    write_pipeline_heartbeat(f"📥 [{pid} | {sc_id}] Tải xong cảnh 1080p ({nbytes//1024} KB)!", is_running=True)
                    safe_sync_ui()
                    check_and_queue_ffmpeg(
                        ffmpeg_pool,
                        ffmpeg_futures,
                        pid,
                        pdir,
                        v_key,
                        prompts_data["videos"][v_key]["scenes"],
                    )

                elif _poll_item_failed(t, res_state, elapsed):
                    with QUEUE_LOCK:
                        inflight_tasks.pop(t_key, None)
                    t.pop("_vids_future", None)
                    fail_acc = t.get("account_name") or primary_prof_name
                    fail_kind = _classify_mt_err(res_state)
                    if fail_kind == "account_auth" or (len(account_cookie_pool) > 1 and fail_kind in ("account_quota", "rate_limit")):
                        _mark_unhealthy(fail_acc, res_state)
                    if t.get("stage") == "ref_img_poll":
                        t["type"] = "ref_img"
                        t["stage"] = None
                        t["media_uuid"] = None
                        print(f"🔁 [{pid} | {v_key} REF] Poll {res_state} ({elapsed}s), scheduling retry ({t['retries'] + 1}/12)...", flush=True)
                        _schedule_mt_retry(t, res_state, max_retries_cap=12, front=False)
                    elif t.get("stage") == "upsample_1080p":
                        if not t.get("base_video_uuid") and t.get("media_uuid"):
                            t["base_video_uuid"] = str(t["media_uuid"]).removesuffix("_upsampled")
                        if "rpc_err:[5]" in str(res_state or ""):
                            if t.get("_resumed_from_state") and t.get("media_uuid"):
                                tried_res = t.setdefault("_tried_resume_accs", [])
                                if fail_acc not in tried_res:
                                    tried_res.append(fail_acc)
                                alt_res = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in tried_res]
                                if alt_res:
                                    nxt_res = alt_res[0]
                                    st_nxt = acc_contexts.get(nxt_res)
                                    t["account_name"] = nxt_res
                                    t["preferred_account"] = nxt_res
                                    t["_rpc5_cnt"] = 0
                                    t["_http400_cnt"] = 0
                                    t["submitted_at"] = time.time()
                                    t.pop("wiz", None)
                                    t.pop("cookie_hdr", None)
                                    t.pop("dl_headers", None)
                                    t["project_id"] = (st_nxt or {}).get("project_id") or _resolve_default_flow_pid(nxt_res) or t["project_id"]
                                    with QUEUE_LOCK:
                                        inflight_tasks[t_key] = t
                                    print(f"🔁 [{pid} | {sc_id}] Resume 1080p rpc_err:[5] trên {fail_acc} -> thử poll trên {nxt_res}...", flush=True)
                                    continue
                            tried_up = t.setdefault("_upsample_tried_accs", [])
                            if fail_acc not in tried_up:
                                tried_up.append(fail_acc)
                            other_up_accs = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in tried_up]
                            if other_up_accs:
                                alt_acc = other_up_accs[0]
                                t["type"] = "upsample_1080p"
                                t["media_uuid"] = None
                                t["preferred_account"] = alt_acc
                                print(f"🔁 [{pid} | {sc_id}] 1080p Upsample rpc_err:[5] trên {fail_acc} -> thử chủ sở hữu {alt_acc} ({t['retries'] + 1}/12)...", flush=True)
                                _schedule_mt_retry(t, res_state, max_retries_cap=12, front=True)
                                continue
                            if os.path.exists(t["out_mp4"] + ".720p.tmp"):
                                shutil.move(t["out_mp4"] + ".720p.tmp", t["out_mp4"])
                                print(f"⚠️ [{pid} | {sc_id}] Promoted 720p backup after all accounts returned rpc_err:[5]", flush=True)
                                safe_sync_ui()
                                check_and_queue_ffmpeg(
                                    ffmpeg_pool,
                                    ffmpeg_futures,
                                    pid,
                                    pdir,
                                    t["v_key"],
                                    prompts_data["videos"][t["v_key"]]["scenes"],
                                )
                                continue
                            print(f"🔁 [{pid} | {sc_id}] 1080p Upsample rpc_err:[5] không tìm thấy bản 720p gốc -> render lại cảnh.", flush=True)
                            t["type"] = "vid_scene"
                            t["stage"] = "base_720p"
                            t["media_uuid"] = None
                            t["base_video_uuid"] = None
                            t["retries"] = 0
                            t.pop("preferred_account", None)
                            with STATE_LOCK:
                                state["scene_uuids"].pop(sc_id, None)
                                (state.get("scene_accounts") or {}).pop(sc_id, None)
                            save_prod_state(pdir, state)
                            _schedule_mt_retry(t, res_state, max_retries_cap=12, front=False)
                            continue
                        t["type"] = "upsample_1080p"
                        t["media_uuid"] = None
                        t["preferred_account"] = fail_acc
                        print(f"🔁 [{pid} | {sc_id}] 1080p Upsample {res_state} ({elapsed}s), retrying ({t['retries'] + 1}/12)...", flush=True)
                        if not _schedule_mt_retry(t, res_state, max_retries_cap=12, front=False) and os.path.exists(t["out_mp4"] + ".720p.tmp"):
                            shutil.move(t["out_mp4"] + ".720p.tmp", t["out_mp4"])
                            print(f"⚠️ [{pid} | {sc_id}] Promoted 720p backup after upsample failure", flush=True)
                            safe_sync_ui()
                            check_and_queue_ffmpeg(
                                ffmpeg_pool,
                                ffmpeg_futures,
                                pid,
                                pdir,
                                v_key,
                                prompts_data["videos"][v_key]["scenes"],
                            )
                    else:
                        if "rpc_err:[5]" in str(res_state or "") and t.get("_resumed_from_state") and t.get("media_uuid"):
                            tried_res7 = t.setdefault("_tried_resume_accs", [])
                            if fail_acc not in tried_res7:
                                tried_res7.append(fail_acc)
                            alt_res7 = [a["profile_name"] for a in account_cookie_pool if a["profile_name"] not in tried_res7]
                            if alt_res7:
                                nxt_res7 = alt_res7[0]
                                st_nxt7 = acc_contexts.get(nxt_res7)
                                t["account_name"] = nxt_res7
                                t["preferred_account"] = nxt_res7
                                t["_rpc5_cnt"] = 0
                                t["_http400_cnt"] = 0
                                t["submitted_at"] = time.time()
                                t.pop("wiz", None)
                                t.pop("cookie_hdr", None)
                                t.pop("dl_headers", None)
                                t["project_id"] = (st_nxt7 or {}).get("project_id") or _resolve_default_flow_pid(nxt_res7) or t["project_id"]
                                with QUEUE_LOCK:
                                    inflight_tasks[t_key] = t
                                print(f"🔁 [{pid} | {sc_id}] Resume 720p rpc_err:[5] trên {fail_acc} -> thử poll trên {nxt_res7}...", flush=True)
                                continue
                        t["type"] = "vid_scene"
                        t["media_uuid"] = None
                        t.pop("_resumed_from_state", None)
                        with STATE_LOCK:
                            state["scene_uuids"].pop(sc_id, None)
                            (state.get("scene_accounts") or {}).pop(sc_id, None)
                        save_prod_state(pdir, state)
                        print(f"🔁 [{pid} | {sc_id}] Flow render {res_state} ({elapsed}s), scheduling retry ({t['retries'] + 1}/12)...", flush=True)
                        _schedule_mt_retry(t, res_state, max_retries_cap=12, front=False)
                else:
                    if str(res_state) in ("running_1", "running_2") or str(res_state or "").startswith("ready_"):
                        t["_saw_active_status"] = True
                    st_tag = "ref" if t.get("stage") == "ref_img_poll" else ("1080p" if t.get("stage") == "upsample_1080p" else "720p")
                    status_summary.append(f"{pid[-4:]}:{sc_id}[{st_tag}]({res_state.replace('running_','')})")

            if status_summary:
                with QUEUE_LOCK:
                    n_inf = len(inflight_tasks)
                    n_sub = len(in_submit_tasks)
                    n_q = len(pending_queue)
                summary_line = (
                    f"⏳ [Đang xử lý={n_inf} (+{n_sub} gửi) | Hàng đợi={n_q}] "
                    + ", ".join(status_summary[:10])
                )
                print(summary_line, flush=True)
                write_pipeline_heartbeat(summary_line, is_running=True)

            max_loop_sec = int(os.environ.get("FLOW_MT_TIMEOUT_SEC") or 28800)
            if time.time() - loop_start > max_loop_sec:
                print("Global timeout reached!", flush=True)
                break

        stop_workers.set()
        submit_pool.shutdown(wait=True)

        def _cleanup_pw_resources():
            for _acc_st in list(acc_contexts.values()):
                if _acc_st.get("ctx") is not None:
                    try:
                        _acc_st["ctx"].close()
                    except Exception:
                        pass
            acc_contexts.clear()
            if browser_box[0] is not None:
                try:
                    browser_box[0].close()
                except Exception:
                    pass

        _run_pw_safe(_cleanup_pw_resources)

    try:
        ffp_active_file = os.path.join(os.path.dirname(SCRIPTS_DIR), "active_mt_runner.json")
        if os.path.isfile(ffp_active_file):
            ar_cur = json.load(open(ffp_active_file, "r", encoding="utf-8"))
            if int(ar_cur.get("pid_os") or 0) == os.getpid():
                os.remove(ffp_active_file)
    except Exception:
        pass

    initial_ffmpeg_checks = []
    for pid in list(only_pids):
        if pid not in prod_meta:
            continue
        pdir, prompts_data, _, _ = prod_meta[pid]
        for v_key in list(prompts_data.get("videos", {}).keys()):
            if v_key in prompts_data.get("videos", {}):
                check_and_queue_ffmpeg(
                    ffmpeg_pool,
                    ffmpeg_futures,
                    pid,
                    pdir,
                    v_key,
                    prompts_data["videos"][v_key]["scenes"],
                )

    if ffmpeg_futures:
        write_pipeline_heartbeat(f"🎞️ Đang ghép {len(ffmpeg_futures)} Video Final 60FPS + Thumbnail 0.1s...", is_running=True)
    with STATE_LOCK:
        th_futs = list(THUMB_FUTURES_BY_KEY.values())
    if th_futs:
        concurrent.futures.wait(th_futs, timeout=600)
    thumb_pool.shutdown(wait=False)
    print(f"Waiting for {len(ffmpeg_futures)} parallel FFmpeg Final Video builds to finish...", flush=True)
    concurrent.futures.wait(ffmpeg_futures)
    ffmpeg_pool.shutdown(wait=True)
    poll_pool.shutdown(wait=False)
    vids_pool.shutdown(wait=False)

    runtime_abort_msg = runtime_abort_box[0]
    now_done_str = time.strftime("%H:%M:%S")
    for pid_end in list(only_pids):
        if pid_end not in prod_meta:
            continue
        pdir_e, pdata_e, st_end, _ = prod_meta[pid_end]
        vids_e = pdata_e.get("videos") or {}
        total_v_e = len(vids_e)
        done_v_e = sum(
            1
            for vk_e in vids_e
            if os.path.isfile(os.path.join(WS_DIR, "final_videos", get_final_video_filename(pid_end, vk_e)))
            and os.path.getsize(os.path.join(WS_DIR, "final_videos", get_final_video_filename(pid_end, vk_e))) > 50000
        )
        sc_errs_e = st_end.get("scene_errors") if isinstance(st_end.get("scene_errors"), dict) else {}
        fail_n_e = len(sc_errs_e)
        if runtime_abort_msg:
            msg_end = f"⛔ Tạm dừng ({done_v_e}/{total_v_e} Video Final): {runtime_abort_msg}"
        elif done_v_e >= total_v_e and total_v_e > 0:
            msg_end = f"🎉 Hoàn tất {done_v_e}/{total_v_e} Video Final & Thumbnail!"
        elif fail_n_e > 0:
            first_err_txt = next(
                (str(v.get("message") or v.get("error") or "") for v in sc_errs_e.values() if isinstance(v, dict)),
                "",
            )
            msg_end = f"⚠️ Hoàn tất {done_v_e}/{total_v_e} biến thể — {fail_n_e} mục lỗi: {first_err_txt[:140]}"
        else:
            msg_end = f"ℹ️ Kết thúc tiến trình ({done_v_e}/{total_v_e} Video Final)."
        st_end_file = os.path.join(pdir_e, "pipeline_status.json")
        if hasattr(gvt, "atomic_write_json"):
            gvt.atomic_write_json(
                st_end_file,
                {
                    "pid": pid_end,
                    "pid_os": 0,
                    "is_running": False,
                    "inflight_count": 0,
                    "queued_count": 0,
                    "active_tasks": [],
                    "accounts_active": [a["profile_name"] for a in active_flow_accs],
                    "current_step_text": msg_end,
                    "updated_at": now_done_str,
                },
            )
        print(f"📊 [{pid_end}] {msg_end}", flush=True)

    safe_sync_ui(force=True)
    sys.stdout = orig_stdout
    if runtime_abort_msg:
        print(f"\n⚠️ PIPELINE STOPPED EARLY: {runtime_abort_msg} (Completed work synced to Web UI)", flush=True)
    else:
        print("\n✅ MULTI-THREADED PIPELINE FINISHED AND SYNCED TO WEB UI!", flush=True)


if __name__ == "__main__":
    main()
