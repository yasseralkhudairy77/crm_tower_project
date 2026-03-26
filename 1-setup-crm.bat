@echo off
setlocal
cd /d "%~dp0"

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

echo ==========================================
echo CRM Tower - Setup Pertama Kali
echo Folder kerja: %cd%
echo Python: %PY_CMD%
echo ==========================================
echo.

echo [1/3] Install dependency...
call %PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo [2/3] Inisialisasi database...
call %PY_CMD% -m crm_tower.main --init-db --no-cli
if errorlevel 1 goto :error

echo.
echo [3/3] Menjalankan webapp CRM...
echo Setelah server jalan, buka browser ke:
echo http://127.0.0.1:5000
echo.
call %PY_CMD% -m crm_tower.main --web
goto :end

:error
echo.
echo Setup gagal. Cek pesan error di atas.
pause
exit /b 1

:end
echo.
echo Proses selesai.
pause
endlocal
