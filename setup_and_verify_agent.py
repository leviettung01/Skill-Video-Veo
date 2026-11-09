# -*- coding: utf-8 -*-
"""
⚡ Lê Việt Tùng - SkillAutoVeo
Zalo: 0915967790 | Facebook: https://www.facebook.com/tungbinh.38/
======================================================================
Script Tự Động Cài Đặt & Kiểm Tra Toàn Diện Dành Cho AI Agent (Máy Mới)

Cách dùng cho AI Agent hoặc Người Dùng trên máy mới:
  1. Tự động cài đặt toàn bộ thư viện + trình duyệt + khởi tạo dữ liệu:
       python setup_and_verify_agent.py --install
  2. Chỉ kiểm tra trạng thái hệ thống (Healthcheck):
       python setup_and_verify_agent.py --verify
"""
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_ROOT = Path(__file__).resolve().parent

AUTHOR_INFO = {
    "brand": "Lê Việt Tùng - SkillAutoVeo",
    "zalo": "0915967790",
    "zalo_url": "https://zalo.me/0915967790",
    "facebook": "https://www.facebook.com/tungbinh.38/",
    "extension_name": "LeVietTung_autoveo",
}

REQUIRED_DIRS = [
    "data",
    "data/tiktok_crawler",
    "data/tiktok_crawler/data",
    "data/tiktok_crawler/data/product_images",
    "data/tiktok_crawler/profiles",
    "cookies",
    "profiles",
    "native_profiles",
    "browser_settings",
    "session_metadata",
    "auth_attempts",
    "locks",
    "flow_final_pipeline/projects",
    "flow_final_pipeline/final_videos",
    "fashion_motion_projects",
    "WorkFlow/saved_workflows",
    "WorkFlow/workflow_outputs",
    "data/fashion_templates_cache",
    "Template/Nhà Xưởng",
    "Template/Motion Control Video Fashion",
    "Template/Thumbnail_Templates",
    "Template/Subtitle_Templates",
    "Template/Character_Sheet_Templates",
    "Extension Recapcha/LeVietTung_autoveo",
]

REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("curl_cffi", "curl_cffi"),
    ("PIL", "Pillow"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("playwright", "playwright"),
    ("PyQt6", "PyQt6"),
    ("torch", "torch"),
]


def ensure_directories():
    created = []
    for rel in REQUIRED_DIRS:
        p = SKILL_ROOT / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(rel)
    # Khởi tạo file dữ liệu mặc định nếu chưa có
    default_json_files = {
        "accounts.json": [],
        "Flow_nhieu_worker_accounts.json": [],
        "veo3_config.json": {"bridge_port": 4000, "jitter_min_ms": 2000, "jitter_max_ms": 5000},
        "proxy_config.json": {"proxies": [], "round_robin_idx": 0},
        "data/tiktok_crawler/data/products.json": {"products": [], "updated_at": ""},
    }
    for rel_file, default_val in default_json_files.items():
        fp = SKILL_ROOT / rel_file
        if not fp.exists():
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(json.dumps(default_val, ensure_ascii=False, indent=2), encoding="utf-8")
    return created


def install_dependencies():
    print("=" * 72)
    print(f"⚡ ĐANG CÀI ĐẶT HỆ THỐNG: {AUTHOR_INFO['brand']}")
    print(f"📞 Zalo: {AUTHOR_INFO['zalo']} | 🌐 FB: {AUTHOR_INFO['facebook']}")
    print("=" * 72)

    req_file = SKILL_ROOT / "requirements.txt"
    if req_file.is_file():
        print("\n[1/4] 📦 Đang cài đặt các thư viện Python từ requirements.txt...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], check=False)

    # Kiểm tra từng thư viện quan trọng, nếu thiếu thì cài bổ sung
    print("\n[2/4] 🔍 Kiểm tra & cài bổ sung các gói thư viện lõi...")
    for mod_name, pip_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(mod_name)
            print(f"  ✅ Đã có: {pip_name}")
        except ImportError:
            print(f"  ⏳ Đang cài bổ sung: {pip_name}...")
            subprocess.run([sys.executable, "-m", "pip", "install", pip_name], check=False)

    print("\n[3/4] 🌐 Đang cài đặt trình duyệt Playwright Chromium...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)

    print("\n[4/4] 📁 Đang khởi tạo cấu trúc thư mục độc lập trong Skill...")
    ensure_directories()


def verify_environment() -> dict:
    ensure_directories()
    report = {
        "ok": True,
        "author": AUTHOR_INFO,
        "skill_root": str(SKILL_ROOT),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "packages": {},
        "binaries": {},
        "components": {},
        "missing_packages": [],
        "warnings": [],
    }

    # 1. Check Python packages
    for mod_name, pip_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(mod_name)
            report["packages"][pip_name] = True
        except Exception:
            report["packages"][pip_name] = False
            report["missing_packages"].append(pip_name)
            report["ok"] = False

    # 2. Check FFmpeg & Chrome
    ffmpeg_path = shutil.which("ffmpeg")
    report["binaries"]["ffmpeg"] = ffmpeg_path or ""
    if not ffmpeg_path:
        report["warnings"].append("Chưa tìm thấy 'ffmpeg' trong PATH. Hãy cài bằng: winget install Gyan.FFmpeg")

    chrome_candidates = [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    chrome_exe = next((str(p) for p in chrome_candidates if p.is_file()), "")
    report["binaries"]["chrome"] = chrome_exe
    if not chrome_exe:
        report["warnings"].append("Chưa tìm thấy Google Chrome trên máy.")

    # 3. Check Standalone Components inside Skill folder
    ext_manifest = SKILL_ROOT / "Extension Recapcha" / "LeVietTung_autoveo" / "manifest.json"
    yolo_weights = SKILL_ROOT / "tiktok_crawler" / "boxphone_captcha" / "weights" / "08102026_detect.torchscript"
    template_nha_xuong = SKILL_ROOT / "Template" / "Nhà Xưởng" / "template_config.json"
    char_lib = SKILL_ROOT / "flow_final_pipeline" / "characters" / "nv1_ref.jpg"
    web_ui = SKILL_ROOT / "static" / "index.html"

    report["components"] = {
        "extension_LeVietTung_autoveo": ext_manifest.is_file(),
        "extension_path": str(ext_manifest.parent),
        "boxphone_yolo_captcha_weights": yolo_weights.is_file(),
        "template_nha_xuong": template_nha_xuong.is_file(),
        "character_library": char_lib.is_file(),
        "web_studio_ui": web_ui.is_file(),
    }

    for k, v in report["components"].items():
        if isinstance(v, bool) and not v:
            report["ok"] = False
            report["warnings"].append(f"Thiếu thành phần quan trọng: {k}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Lê Việt Tùng - SkillAutoVeo | Setup & Verify cho AI Agent")
    parser.add_argument("--install", action="store_true", help="Tự động cài đặt toàn bộ thư viện & Playwright")
    parser.add_argument("--verify", action="store_true", help="Kiểm tra trạng thái toàn bộ hệ thống")
    parser.add_argument("--json", action="store_true", help="In kết quả dạng JSON")
    args = parser.parse_args()

    if args.install:
        install_dependencies()

    rep = verify_environment()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return

    print("\n" + "=" * 72)
    print(f"👑 THƯƠNG HIỆU: {AUTHOR_INFO['brand']}")
    print(f"📞 Zalo: {AUTHOR_INFO['zalo']} ({AUTHOR_INFO['zalo_url']})")
    print(f"🌐 Facebook: {AUTHOR_INFO['facebook']}")
    print("=" * 72)
    print(f"📂 Thư mục Skill độc lập : {rep['skill_root']}")
    print(f"🐍 Python                : {rep['python_version']} ({rep['python_executable']})")
    print(f"🎬 FFmpeg                : {rep['binaries']['ffmpeg'] or '❌ Chưa có trong PATH'}")
    print(f"🌐 Google Chrome         : {rep['binaries']['chrome'] or '❌ Chưa tìm thấy'}")
    print(f"🧩 Extension Chrome      : {rep['components']['extension_path']} ({'✅ Sẵn sàng' if rep['components']['extension_LeVietTung_autoveo'] else '❌ Thiếu'})")
    print(f"🤖 BoxPhone Captcha YOLO : {'✅ Sẵn sàng' if rep['components']['boxphone_yolo_captcha_weights'] else '❌ Thiếu'}")
    print(f"🏭 Template Nhà Xưởng    : {'✅ Sẵn sàng' if rep['components']['template_nha_xuong'] else '❌ Thiếu'}")
    print(f"👤 Thư Viện Nhân Vật     : {'✅ Sẵn sàng' if rep['components']['character_library'] else '❌ Thiếu'}")
    print("-" * 72)
    if rep["missing_packages"]:
        print(f"⚠️ Các thư viện Python còn thiếu: {', '.join(rep['missing_packages'])}")
        print("👉 Hãy chạy: python setup_and_verify_agent.py --install")
    else:
        print("✅ TẤT CẢ THƯ VIỆN PYTHON LÕI ĐÃ ĐƯỢC CÀI ĐẶT ĐẦY ĐỦ!")
    if rep["warnings"]:
        for w in rep["warnings"]:
            print(f"⚠️ Lưu ý: {w}")
    print("=" * 72)


if __name__ == "__main__":
    main()
