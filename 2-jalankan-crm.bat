@echo off
setlocal
cd /d "%~dp0"

set "GIT_CMD="
where git >nul 2>nul
if %errorlevel%==0 set "GIT_CMD=git"

set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PY_CMD=py -3"

if not defined PY_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo Python belum ditemukan di laptop ini.
    echo Jalankan 1-setup-crm.bat setelah Python terpasang.
    pause
    exit /b 1
)

echo ==========================================
echo CRM Tower - Jalankan Webapp
echo Folder kerja: %cd%
if defined GIT_CMD echo Git: %GIT_CMD%
echo Python: %PY_CMD%
echo ==========================================
echo.
echo Sinkronkan source code terbaru...
if defined GIT_CMD (
    call %GIT_CMD% pull origin main
    if errorlevel 1 (
        echo Git pull gagal. CRM tetap akan mencoba jalan memakai versi lokal yang ada.
    )
) else (
    echo Git tidak ditemukan. Lewati update otomatis.
)
echo.
echo Menjalankan CRM...
echo Buka browser ke:
echo http://127.0.0.1:5000
echo.

call %PY_CMD% -m crm_tower.main --web

echo.
echo Server berhenti.
pause
endlocal
