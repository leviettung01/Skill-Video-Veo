# -*- coding: utf-8 -*-
"""Standalone Configuration for TikTok Crawler & BoxPhone Captcha Solver inside Skill Video Veo."""
import os
from pathlib import Path

CRAWLER_PKG_DIR = Path(__file__).resolve().parent
SKILL_DIR = CRAWLER_PKG_DIR.parent

RUNTIME_DIR = Path(
    os.environ.get("TIKTOK_WEB_RUNTIME_DIR", str(SKILL_DIR / "data" / "tiktok_crawler"))
).resolve()

DATA_DIR = RUNTIME_DIR / "data"
WORK_DIR = RUNTIME_DIR / "work"
DIAGNOSTICS_DIR = WORK_DIR / "diagnostics"

STORE_ACCOUNTS = DATA_DIR / "tiktok-accounts.json"
STORE_VIDEOS = DATA_DIR / "tiktok-videos.json"
STORE_PRODUCTS = DATA_DIR / "tiktok-products.json"
STORE_SETTINGS = DATA_DIR / "tiktok-settings.json"
STORE_RESEARCH = DATA_DIR / "tiktok-product-research.json"
PRODUCT_IMAGES_DIR = DATA_DIR / "product_images"
HOT_PRODUCTS_DIR = DATA_DIR / "hot_products"
UPLOAD_STAGING_DIR = WORK_DIR / "upload_staging"

TIKTOK_SHOP_DIR = Path(
    os.environ.get("TIKTOK_SHOP_DIR", str(RUNTIME_DIR / "tiktok_shop"))
).resolve()
TIKTOK_SHOP_PROFILE_DIR = TIKTOK_SHOP_DIR / "profiles" / "tiktok_chrome_profile"
CHROME_DEBUG_PORT = int(os.environ.get("TIKTOK_CHROME_DEBUG_PORT", "9222"))

BOXPHONE_DIR = Path(
    os.environ.get("BOXPHONE_DIR", str(CRAWLER_PKG_DIR / "boxphone_captcha"))
).resolve()
BOXPHONE_WEIGHTS_DIR = BOXPHONE_DIR / "weights"
BOXPHONE_TEMPLATES_DIR = BOXPHONE_DIR / "templates"


def ensure_dirs() -> None:
    for d in (
        DATA_DIR,
        WORK_DIR,
        DIAGNOSTICS_DIR,
        PRODUCT_IMAGES_DIR,
        HOT_PRODUCTS_DIR,
        UPLOAD_STAGING_DIR,
        TIKTOK_SHOP_PROFILE_DIR,
        BOXPHONE_WEIGHTS_DIR,
        BOXPHONE_TEMPLATES_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


ensure_dirs()

