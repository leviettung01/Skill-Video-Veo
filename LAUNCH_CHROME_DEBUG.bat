@echo off
echo ============================================
echo  CHROME DEBUG LAUNCHER - Google Flow Tool
echo ============================================
echo.
echo Script nay se:
echo 1. Dong Chrome hien tai (cac tab se duoc phuc hoi)
echo 2. Mo lai Chrome voi Remote Debugging Port 9222
echo.
echo Sau khi Chrome mo lai, cac tab se tu dong phuc hoi.
echo Tool se tu dong ket noi va lay session.
echo.
pause

echo Dang dong Chrome...
taskkill /f /im chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Dang mo lai Chrome voi debug port...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --restore-last-session

echo.
echo Chrome da mo voi debug port 9222!
echo Cho 5 giay de Chrome tai xong...
timeout /t 5 /nobreak >nul

echo.
echo Kiem tra ket noi CDP...
curl -s http://localhost:9222/json/version

echo.
echo Done! Gio co the chay Flow submission script.
pause

