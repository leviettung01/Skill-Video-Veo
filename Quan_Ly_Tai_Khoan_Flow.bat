@echo off
chcp 65001 >nul
title Quan Ly & Dang Nhap Tai Khoan Google Flow (Python Tool)
cd /d "%~dp0"
python -u flow_account_gui.py
if errorlevel 1 pause

