@echo off
chcp 65001 >nul
title Chrome Session Extractor — Cookies + Google Flow Token
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║   CHROME SESSION EXTRACTOR — Cookies + Google Flow Token  ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Script nay se:
echo  1. Mo Chrome voi profile ban chon (copy tam, khong anh huong profile goc)
echo  2. Navigate den flow.google.com
echo  3. Lay Cookies + WIZ Tokens (at, bl, fsid) tu session dang login
echo  4. Luu vao thu muc cookies/ de tool su dung
echo.
echo ─────────────────────────────────────────────
echo Cac lenh co the dung:
echo.
echo   extract_session.bat                    Interactive menu
echo   extract_session.bat Profile13          Lay Profile 13 (leviettung04@gmail.com)
echo   extract_session.bat leviettung04       Lay Native Profile leviettung04
echo   extract_session.bat Default            Lay Profile mac dinh (account chinh)
echo   extract_session.bat all                Lay tat ca profiles
echo   extract_session.bat --cdp              Dung Chrome dang chay (DebugPort 9222)
echo ─────────────────────────────────────────────
echo.

set SCRIPT_DIR=%~dp0
set PYTHON=python

cd /d "%SCRIPT_DIR%"

if "%1"=="" (
    %PYTHON% extract_chrome_session.py
) else if "%1"=="--cdp" (
    %PYTHON% extract_chrome_session.py --cdp
) else if "%1"=="all" (
    %PYTHON% extract_chrome_session.py --profile all
) else (
    %PYTHON% extract_chrome_session.py --profile "%1"
)

echo.
pause

