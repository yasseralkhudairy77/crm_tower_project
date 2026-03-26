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
    echo Jalankan 1-setup-crm.bat setelah Python terpasang.
    pause
    exit /b 1
)

echo ==========================================
echo CRM Tower - Jalankan via WiFi Lokal
echo Folder kerja: %cd%
echo Python: %PY_CMD%
echo ==========================================
echo.
echo Menjalankan CRM agar bisa diakses device lain
echo di jaringan WiFi yang sama.
echo.
echo Setelah server jalan, cek alamat yang tampil di bawah.
echo Contoh akses supervisor:
echo http://192.168.1.10:5000
echo.

call %PY_CMD% -m crm_tower.main --web --lan

echo.
echo Server berhenti.
pause
endlocal
