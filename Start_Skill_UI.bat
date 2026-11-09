@echo off
chcp 65001 >nul
title Skill Video Veo - Local Web UI
cd /d "%~dp0"
echo Starting Skill Video Veo Local Web Server (http://127.0.0.1:8456)...
python -u "%~dp0server.py" --restart
if errorlevel 1 pause
