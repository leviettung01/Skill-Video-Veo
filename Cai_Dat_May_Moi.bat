@echo off
chcp 65001 >nul
title Le Viet Tung - SkillAutoVeo | Cai Dat May Moi Tu A-Z
cd /d "%~dp0"
echo ========================================================================
echo   LE VIET TUNG - SKILLAUTOVEO (STANDALONE AI VIDEO STUDIO)
echo   Zalo: 0915967790 ^| Facebook: https://www.facebook.com/tungbinh.38/
echo ========================================================================
echo.
python setup_and_verify_agent.py --install
echo.
echo HOAN TAT CAI DAT! Ban co the chay "Chay_Skill_Web.bat" de mo Web Studio.
pause
