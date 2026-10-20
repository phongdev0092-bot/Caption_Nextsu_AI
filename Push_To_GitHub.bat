@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo   CAPTION NEXTSU AI - DAY CODE LEN GITHUB
echo ===================================================
echo Repository: https://github.com/phongdev0092-bot/Caption_Nextsu_AI.git
echo Nhanh (Branch): main
echo.
echo Dang day code len GitHub...
git push -u origin main
echo.
if %ERRORLEVEL% equ 0 (
    echo ===================================================
    echo   THANH CONG! Code da duoc day len GitHub.
    echo ===================================================
) else (
    echo ===================================================
    echo   CO LOI XAY RA! Vui long kiem tra tai khoan GitHub.
    echo ===================================================
)
echo.
pause
