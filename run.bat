@echo off
chcp 65001 > nul
title Caption Nextsu AI - Localhost
echo ======================================================================
echo    CAPTION NEXTSU AI - MAY CHU WEB LOCALHOST
echo ======================================================================
echo.
echo [*] Dang khoi dong Web Server...
echo [*] Neu cong 5000 dang ban, he thong se TU DONG chuyen sang cong trong tiep theo (5001, ...).
echo [*] Trinh duyet se tu dong mo dung dia chi localhost cua may chu.
echo.
echo [Luu y] De ngat may chu, hay dong cua so Command Prompt nay hoac bam Ctrl+C.
echo ======================================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" server.py
) else (
    python server.py
)
if errorlevel 1 (
    echo.
    echo [LOI] Khong the khoi dong server. Vui long kiem tra Python.
    pause
)
