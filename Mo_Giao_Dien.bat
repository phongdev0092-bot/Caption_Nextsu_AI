@echo off
chcp 65001 > nul
title Caption Nextsu AI - Giao Dien
echo Đang khởi động giao diện điều khiển Caption Nextsu AI...
start "" pythonw app_gui.py
if errorlevel 1 (
    echo Không khởi động được bằng pythonw, đang thử lại với python...
    python app_gui.py
    pause
)
