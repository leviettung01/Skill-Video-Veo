@echo off
chcp 65001 >nul
title Le Viet Tung - SkillAutoVeo | AI Video Studio (Port 8456)
cd /d "%~dp0"
echo ========================================================================
echo   LE VIET TUNG - SKILLAUTOVEO — STANDALONE AI STUDIO (PORT 8456)
echo   Zalo: 0915967790 ^| Facebook: https://www.facebook.com/tungbinh.38/
echo   - Extension Chrome : Extension Recapcha\LeVietTung_autoveo
echo   - Template Video   : Template\Nha Xuong (va cac Template moi)
echo   - Crawler San Pham : Cach 1 (SPAI Auto) + Cach 2 (Browser + Captcha BoxPhone)
echo   - Thu Vien Nhan Vat: Character Sheet Templates (Nano Banana 2K / ChatGPT)
echo ========================================================================
python -u server.py --restart
pause
