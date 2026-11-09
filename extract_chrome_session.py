# -*- coding: utf-8 -*-
"""
=============================================================================
 CHROME SESSION EXTRACTOR — Lấy Cookies + Google Labs Access Token
 Từ bất kỳ Chrome Profile nào (System Chrome hoặc Native Profile của Tool)
=============================================================================
 Cách hoạt động:
   1. Dùng Playwright launch Chrome với profile thật (copy sang temp folder)
   2. Navigate đến flow.google.com → extract cookies + WIZ tokens
   3. Lưu ra file cookies/<profile>.json đúng format tool dùng

 Cách chạy:
   python extract_chrome_session.py                      # Interactive menu
   python extract_chrome_session.py --profile Profile13  # Tự động lấy Profile 13
   python extract_chrome_session.py --profile all        # Lấy tất cả profiles có flow.google.com
   python extract_chrome_session.py --cdp               # Dùng Chrome đang chạy (CDP port 9222)
=============================================================================
"""
from __future__ import annotations
import os, sys, json, shutil, time, argparse, tempfile, subprocess
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
TOOL_DIR = Path(__file__).resolve().parent
COOKIES_DIR    = TOOL_DIR / "cookies"
NATIVE_DIR     = TOOL_DIR / "data" / "google_flow_grok" / "native_profiles"
SYSTEM_CHROME  = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Google" / "Chrome" / "User Data"
CHROME_EXE     = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CDP_PORT       = 9222

# URLs cần navigate để lấy token
FLOW_URL = "https://flow.google.com"
FLOW_PROJECT_URL = "https://flow.google.com/project"

# ── Helpers ────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌", "STEP": "▶️ "}.get(level, "")
    print(f"{prefix} {msg}", flush=True)


def get_system_profiles() -> dict[str, dict]:
    """Liệt kê tất cả System Chrome profiles (C:\\...\\User Data\\Profile N)."""
    profiles = {}
    if not SYSTEM_CHROME.exists():
        return profiles
    ls_path = SYSTEM_CHROME / "Local State"
    if ls_path.exists():
        try:
            ls = json.loads(ls_path.read_text(encoding="utf-8"))
            info_cache = ls.get("profile", {}).get("info_cache", {})
        except Exception:
            info_cache = {}
    else:
        info_cache = {}

    for item in SYSTEM_CHROME.iterdir():
        if not item.is_dir():
            continue
        cookie_file = item / "Network" / "Cookies"
        if not cookie_file.exists():
            continue
        pinfo = info_cache.get(item.name, {})
        profiles[item.name] = {
            "path": str(item),
            "name": pinfo.get("name", item.name),
            "email": pinfo.get("user_name", ""),
            "source": "system",
        }
    return profiles


def get_native_profiles() -> dict[str, dict]:
    """Liệt kê Native Profiles của Tool."""
    profiles = {}
    if not NATIVE_DIR.exists():
        return profiles
    for item in NATIVE_DIR.iterdir():
        if not item.is_dir():
            continue
        cookie_file = item / "Default" / "Network" / "Cookies"
        if not cookie_file.exists():
            continue
        # Map profile folder name → email from accounts.json nếu có
        profiles[item.name] = {
            "path": str(item),
            "name": item.name,
            "email": f"{item.name}@gmail.com",  # heuristic
            "source": "native",
        }
    return profiles


def copy_profile_to_temp(profile_path: str) -> Path:
    """Copy profile sang temp để tránh ProcessSingleton lock."""
    src = Path(profile_path)
    tmp = Path(tempfile.mkdtemp(prefix="chrome_extract_"))
    log(f"Copying profile to temp: {tmp}", "STEP")

    # Chỉ copy Default folder và Local State (không copy cache để nhanh hơn)
    items_to_copy = ["Local State", "Default"]
    for item in items_to_copy:
        src_item = src / item
        dst_item = tmp / item
        if src_item.exists():
            if src_item.is_dir():
                shutil.copytree(str(src_item), str(dst_item), ignore=shutil.ignore_patterns(
                    "Cache", "Code Cache", "GPUCache", "Service Worker",
                    "CacheStorage", "blob_storage", "VideoDecodeStats",
                    "*.log", "*.lock"
                ))
            else:
                shutil.copy2(str(src_item), str(dst_item))

    log(f"Profile copied ({tmp})", "OK")
    return tmp


def extract_via_playwright(profile_path: str, profile_name: str, is_native: bool = False) -> Optional[dict]:
    """
    Launch Chrome với profile copy, navigate flow.google.com,
    extract cookies + WIZ tokens.
    """
    from playwright.sync_api import sync_playwright, Error as PwError

    tmp_dir = None
    try:
        tmp_dir = copy_profile_to_temp(profile_path)

        with sync_playwright() as pw:
            log(f"Launching Chrome for profile: {profile_name}", "STEP")
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=str(tmp_dir),
                channel="chrome",
                headless=False,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-sync",
                    "--disable-background-networking",
                    "--disable-client-side-phishing-detection",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-popup-blocking",
                    "--disable-translate",
                    "--disable-features=TranslateUI",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--safebrowsing-disable-auto-update",
                ],
                ignore_https_errors=True,
                timeout=30000,
            )

            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()

                # Navigate flow.google.com
                log(f"Navigating to {FLOW_URL}", "STEP")
                page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)

                # Check if logged in
                current_url = page.url
                log(f"Current URL: {current_url}")

                if "accounts.google.com" in current_url or "signin" in current_url.lower():
                    log(f"Profile {profile_name} chưa đăng nhập vào Google Flow", "WARN")
                    ctx.close()
                    return None

                # Extract cookies
                cookies = ctx.cookies([FLOW_URL, "https://google.com", "https://accounts.google.com"])
                log(f"Got {len(cookies)} cookies", "OK")

                # Extract WIZ tokens (SNlM0e = at, cfb2h = bl, FdrFJe = fsid)
                wiz = page.evaluate("""() => {
                    const w = window.WIZ_global_data || {};
                    return {
                        at:   w.SNlM0e   || '',
                        bl:   w.cfb2h    || '',
                        fsid: w.FdrFJe   || '',
                        afv:  w.S06Grb   || '',
                        has_wiz: !!window.WIZ_global_data,
                    };
                }""")
                log(f"WIZ tokens: at={'✅' if wiz['at'] else '❌'}, bl={'✅' if wiz['bl'] else '❌'}, fsid={'✅' if wiz['fsid'] else '❌'}", "OK")

                # Nếu chưa có WIZ (trang chưa load xong), thử navigate sang project page
                if not wiz['at']:
                    log("WIZ 'at' missing, trying reload...", "WARN")
                    page.reload(wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(4000)
                    wiz = page.evaluate("""() => {
                        const w = window.WIZ_global_data || {};
                        return { at: w.SNlM0e||'', bl: w.cfb2h||'', fsid: w.FdrFJe||'' };
                    }""")

                # Get account info from page
                account_email = page.evaluate("""() => {
                    // Try to find user email from various sources
                    const meta = document.querySelector('meta[name="google-signin-client_id"]');
                    const img = document.querySelector('[data-email]');
                    if (img) return img.getAttribute('data-email');
                    // Try from WIZ data
                    const w = window.WIZ_global_data || {};
                    return w.AH9kgc || w.uxLjje || '';
                }""") or ""

                # Build SAPISIDHASH
                sapisid = ""
                for c in cookies:
                    if c["name"] == "SAPISID" and "google.com" in c.get("domain", ""):
                        sapisid = c["value"]
                        break

                result = {
                    "profile_name": profile_name,
                    "email": account_email,
                    "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                    "cookies": [
                        {
                            "name":     c["name"],
                            "value":    c["value"],
                            "domain":   c["domain"],
                            "path":     c.get("path", "/"),
                            "expires":  c.get("expires", -1),
                            "httpOnly": c.get("httpOnly", False),
                            "secure":   c.get("secure", False),
                            "sameSite": c.get("sameSite", "Lax"),
                        }
                        for c in cookies
                        if c.get("value")
                    ],
                    "wiz_tokens": {
                        "at":   wiz.get("at", ""),
                        "bl":   wiz.get("bl", ""),
                        "fsid": wiz.get("fsid", ""),
                    },
                    "sapisid": sapisid,
                }

                log(f"Extracted {len(result['cookies'])} cookies + WIZ tokens for {profile_name}", "OK")
                return result

            finally:
                try:
                    ctx.close()
                except Exception:
                    pass

    except PwError as e:
        log(f"Playwright error for {profile_name}: {e}", "ERR")
        return None
    except Exception as e:
        import traceback
        log(f"Error extracting {profile_name}: {e}", "ERR")
        traceback.print_exc()
        return None
    finally:
        if tmp_dir and tmp_dir.exists():
            try:
                shutil.rmtree(str(tmp_dir), ignore_errors=True)
                log(f"Cleaned up temp dir: {tmp_dir}")
            except Exception:
                pass


def extract_via_cdp(cdp_port: int = CDP_PORT) -> Optional[dict]:
    """Kết nối Chrome đang chạy qua CDP, extract từ tab flow.google.com."""
    from playwright.sync_api import sync_playwright

    log(f"Connecting to Chrome CDP at port {cdp_port}...", "STEP")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://localhost:{cdp_port}", timeout=5000)
            log(f"Connected! Contexts: {len(browser.contexts)}", "OK")

            # Tìm trang Flow
            flow_page = None
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    if "flow.google.com" in pg.url:
                        flow_page = pg
                        log(f"Found Flow tab: {pg.url}", "OK")
                        break
                if flow_page:
                    break

            if not flow_page:
                # Mở tab mới
                log("No Flow tab found, opening new one...", "WARN")
                ctx = browser.contexts[0]
                flow_page = ctx.new_page()
                flow_page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                flow_page.wait_for_timeout(4000)

            # Extract cookies từ context
            ctx = flow_page.context
            cookies = ctx.cookies([FLOW_URL, "https://google.com", "https://accounts.google.com"])
            log(f"Got {len(cookies)} cookies from CDP", "OK")

            # WIZ tokens
            wiz = flow_page.evaluate("""() => {
                const w = window.WIZ_global_data || {};
                return {
                    at:   w.SNlM0e   || '',
                    bl:   w.cfb2h    || '',
                    fsid: w.FdrFJe   || '',
                };
            }""")
            log(f"WIZ: at={'✅' if wiz['at'] else '❌'}, bl={'✅' if wiz['bl'] else '❌'}", "OK")

            sapisid = next((c["value"] for c in cookies if c["name"] == "SAPISID" and "google.com" in c.get("domain", "")), "")

            # Find account email
            account_email = ""
            for c in cookies:
                if "OSID" in c["name"] or "__Secure" in c["name"]:
                    pass  # Can't directly get email from cookies
            # Try from page
            try:
                account_email = flow_page.evaluate("""() => {
                    const w = window.WIZ_global_data || {};
                    return w.uxLjje || w.AH9kgc || '';
                }""") or ""
            except Exception:
                pass

            result = {
                "profile_name": "cdp_session",
                "email": account_email,
                "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "cookies": [
                    {
                        "name":     c["name"],
                        "value":    c["value"],
                        "domain":   c["domain"],
                        "path":     c.get("path", "/"),
                        "expires":  c.get("expires", -1),
                        "httpOnly": c.get("httpOnly", False),
                        "secure":   c.get("secure", False),
                        "sameSite": c.get("sameSite", "Lax"),
                    }
                    for c in cookies
                    if c.get("value")
                ],
                "wiz_tokens": {
                    "at":   wiz.get("at", ""),
                    "bl":   wiz.get("bl", ""),
                    "fsid": wiz.get("fsid", ""),
                },
                "sapisid": sapisid,
            }
            return result

    except Exception as e:
        log(f"CDP extraction failed: {e}", "ERR")
        return None


def save_session(data: dict, profile_name: str):
    """Lưu session data ra file cookies/<profile_name>.json."""
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = COOKIES_DIR / f"{profile_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"Saved → {out_path}", "OK")
    return out_path


def print_summary(data: dict):
    """In tóm tắt session đã extract."""
    print("\n" + "=" * 60)
    print(f"  PROFILE : {data.get('profile_name', '?')}")
    print(f"  EMAIL   : {data.get('email', 'unknown')}")
    print(f"  TIME    : {data.get('extracted_at', '')}")
    print(f"  COOKIES : {len(data.get('cookies', []))}")
    wiz = data.get("wiz_tokens", {})
    at = wiz.get("at", "")
    bl = wiz.get("bl", "")
    fsid = wiz.get("fsid", "")
    print(f"  WIZ.at  : {'✅ ' + at[:30] + '...' if at else '❌ MISSING'}")
    print(f"  WIZ.bl  : {'✅ ' + bl[:20] + '...' if bl else '❌ MISSING'}")
    print(f"  WIZ.fsid: {'✅ ' + fsid[:20] + '...' if fsid else '❌ MISSING'}")
    # Key cookies
    key_names = {"SID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID", "OSID", "__Secure-OSID", "SIDCC"}
    found_keys = {c["name"] for c in data.get("cookies", []) if c["name"] in key_names}
    missing_keys = key_names - found_keys
    print(f"  KEY COOKIES FOUND   : {', '.join(sorted(found_keys)) or 'none'}")
    if missing_keys:
        print(f"  KEY COOKIES MISSING : {', '.join(sorted(missing_keys))}")
    print("=" * 60 + "\n")


def select_profile_interactive() -> Optional[tuple[str, str, bool]]:
    """Interactive menu để chọn profile."""
    system_profs = get_system_profiles()
    native_profs = get_native_profiles()

    all_profs = []
    print("\n" + "=" * 60)
    print("  DANH SÁCH CHROME PROFILES")
    print("=" * 60)

    print("\n[A] SYSTEM CHROME PROFILES (C:\\...\\User Data)")
    sys_items = sorted(system_profs.items())
    for i, (pname, pdata) in enumerate(sys_items):
        email = pdata.get("email", "")
        name = pdata.get("name", pname)
        email_str = f" ({email})" if email else ""
        print(f"  {len(all_profs)+1:2d}. {pname} → {name}{email_str}")
        all_profs.append((pname, pdata["path"], False))

    print("\n[B] NATIVE TOOL PROFILES")
    for i, (pname, pdata) in enumerate(sorted(native_profs.items())):
        email = pdata.get("email", "")
        print(f"  {len(all_profs)+1:2d}. [TOOL] {pname}{f' ({email})' if email else ''}")
        all_profs.append((pname, pdata["path"], True))

    print("\n  0. Thoát")
    print("=" * 60)

    while True:
        try:
            choice = input("\nChọn số profile (0 để thoát, 'all' để lấy tất cả): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if choice == "0":
            return None
        if choice.lower() == "all":
            return "all", "", False

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_profs):
                return all_profs[idx]
        except ValueError:
            pass
        print("  ❌ Không hợp lệ, thử lại.")


def find_profile_by_name(name: str) -> Optional[tuple[str, str, bool]]:
    """Tìm profile theo tên (Profile13, leviettung04, v.v.)."""
    system_profs = get_system_profiles()
    native_profs = get_native_profiles()

    # Normalize
    name_lower = name.lower().replace(" ", "")

    # Check system profiles
    for pname, pdata in system_profs.items():
        if (pname.lower().replace(" ", "") == name_lower
                or (pdata.get("email") or "").lower().split("@")[0] == name_lower
                or (pdata.get("name") or "").lower().replace(" ", "") == name_lower):
            return pname, pdata["path"], False

    # Check native profiles
    for pname, pdata in native_profs.items():
        if pname.lower() == name_lower:
            return pname, pdata["path"], True

    return None


# ── MAIN ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Chrome Session Extractor - Lấy cookies + WIZ tokens từ Chrome profiles")
    parser.add_argument("--profile", "-p", help="Tên profile (ví dụ: Profile13, leviettung04, all)")
    parser.add_argument("--cdp", action="store_true", help="Dùng Chrome đang chạy qua CDP port 9222")
    parser.add_argument("--cdp-port", type=int, default=9222, help="CDP port (default: 9222)")
    parser.add_argument("--output-name", "-o", help="Tên file output (không có .json)")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════╗
║   CHROME SESSION EXTRACTOR — Cookies + Google Flow Token  ║
║   Dùng Playwright để lấy session từ Chrome profile thật  ║
╚══════════════════════════════════════════════════════════╝
""")

    # CDP mode
    if args.cdp:
        log(f"Dùng CDP mode (port {args.cdp_port})...", "STEP")
        data = extract_via_cdp(args.cdp_port)
        if data:
            profile_name = args.output_name or "cdp_session"
            save_session(data, profile_name)
            print_summary(data)
        else:
            log("CDP extraction thất bại. Chrome có thể chưa được bật với --remote-debugging-port", "ERR")
            log(f"Chạy lệnh: chrome.exe --remote-debugging-port={args.cdp_port}", "INFO")
        return

    # Profile-based mode
    if args.profile and args.profile.lower() == "all":
        # Extract all profiles
        system_profs = get_system_profiles()
        native_profs = get_native_profiles()
        all_p = [(n, d["path"], False) for n, d in system_profs.items()]
        all_p += [(n, d["path"], True) for n, d in native_profs.items()]
        log(f"Extracting {len(all_p)} profiles...", "STEP")
        for pname, ppath, is_native in all_p:
            log(f"\n── {pname} ──────────────────────────────", "STEP")
            data = extract_via_playwright(ppath, pname, is_native)
            if data:
                out_name = args.output_name or pname
                save_session(data, out_name)
                print_summary(data)
        return

    if args.profile:
        found = find_profile_by_name(args.profile)
        if not found:
            log(f"Không tìm thấy profile: {args.profile}", "ERR")
            return
        pname, ppath, is_native = found
        log(f"Profile: {pname} ({ppath})", "STEP")
        data = extract_via_playwright(ppath, pname, is_native)
        if data:
            out_name = args.output_name or pname
            save_session(data, out_name)
            print_summary(data)
        return

    # Interactive mode
    choice = select_profile_interactive()
    if not choice:
        log("Đã thoát.", "INFO")
        return

    if isinstance(choice, tuple) and choice[0] == "all":
        # Extract all — gọi lại với --profile all
        import subprocess
        subprocess.run([sys.executable, __file__, "--profile", "all"])
        return

    pname, ppath, is_native = choice
    log(f"\nExtracting profile: {pname}", "STEP")
    data = extract_via_playwright(ppath, pname, is_native)
    if data:
        out_name = args.output_name or pname
        save_session(data, out_name)
        print_summary(data)
    else:
        log("Extraction thất bại. Profile có thể chưa đăng nhập hoặc Chrome bị chặn.", "ERR")


if __name__ == "__main__":
    main()

