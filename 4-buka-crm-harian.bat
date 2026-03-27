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
    echo Install Python 3 terlebih dulu, lalu jalankan file ini lagi.
    pause
    exit /b 1
)

set "LOCAL_IP="
for /f "usebackq delims=" %%i in (`%PY_CMD% -c "from crm_tower.main import detect_local_ip; print(detect_local_ip())"`) do set "LOCAL_IP=%%i"

echo ==========================================
echo CRM Tower - Buka Operasional Harian
echo Folder kerja: %cd%
if defined GIT_CMD echo Git: %GIT_CMD%
echo Python: %PY_CMD%
echo ==========================================
echo.
echo [1/4] Sinkronkan source code terbaru...
if defined GIT_CMD (
    call %GIT_CMD% pull origin main
    if errorlevel 1 (
        echo Git pull gagal. CRM tetap akan mencoba jalan memakai versi lokal yang ada.
    )
) else (
    echo Git tidak ditemukan. Lewati update otomatis.
)

echo.
echo [2/4] Cek database dan referensi dasar...
call %PY_CMD% -m crm_tower.main --init-db --no-cli
if errorlevel 1 goto :error

echo.
echo [3/4] Informasi akses hari ini
echo CRM buka di laptop ini:
echo http://127.0.0.1:5000
echo.
if defined LOCAL_IP (
    echo Supervisor buka di device yang WiFi-nya sama:
    echo http://%LOCAL_IP%:5000/supervisor
) else (
    echo IP lokal belum berhasil terdeteksi otomatis.
    echo Jalankan ipconfig untuk melihat IPv4 Address laptop ini.
)
echo.
echo [4/4] Menjalankan server CRM...
echo Jangan tutup jendela ini selama webapp masih dipakai.
echo.

call %PY_CMD% -m crm_tower.main --web --lan
goto :end

:error
echo.
echo CRM gagal dijalankan. Cek pesan error di atas.
pause
exit /b 1

:end
echo.
echo Server berhenti.
pause
endlocal
