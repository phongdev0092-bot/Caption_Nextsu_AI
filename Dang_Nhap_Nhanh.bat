@echo off
chcp 65001 > nul
title FPT Inside Auto Login - 1 Click
echo ========================================================
echo    DANG NHAP TU DONG VAO INSIDE.FPT.NET
echo ========================================================
python cli_login.py
echo.
echo Nhấn phím bất kỳ để đóng cửa sổ này (Chrome vẫn sẽ tiếp tục mở)...
pause > nul
