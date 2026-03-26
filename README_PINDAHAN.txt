CRM TOWER - PANDUAN PINDAH KE LAPTOP LAIN
=========================================

Folder ini sudah berisi:
- aplikasi CRM
- database aktif
- file konfigurasi
- file BAT untuk setup dan menjalankan webapp

LANGKAH 1 - PINDAHKAN FOLDER
----------------------------
1. Tutup dulu webapp CRM di komputer asal.
2. Zip seluruh folder project ini.
3. Pindahkan file ZIP ke laptop tujuan.
4. Extract ke folder misalnya:
   C:\CRM\crm_tower_project

LANGKAH 2 - INSTALL PYTHON
--------------------------
1. Install Python 3 di laptop tujuan jika belum ada.
2. Saat install Python, centang:
   Add Python to PATH

LANGKAH 3 - SETUP PERTAMA KALI
------------------------------
1. Buka folder project hasil extract.
2. Double-click file:
   1-setup-crm.bat
3. Tunggu sampai proses selesai.
4. Setelah server berjalan, buka browser ke:
   http://127.0.0.1:5000

LANGKAH 4 - PEMAKAIAN HARIAN
----------------------------
Kalau aplikasi sudah pernah di-setup, untuk menjalankan CRM cukup:
1. Buka folder project
2. Double-click file:
   2-jalankan-crm.bat
3. Buka browser ke:
   http://127.0.0.1:5000

FILE PENTING
------------
Pastikan file-file ini tidak hilang:
- crm_tower.db
- crm_tower_config.json
- requirements.txt
- 1-setup-crm.bat
- 2-jalankan-crm.bat

CATATAN PENTING
---------------
- Jangan jalankan database yang sama di 2 komputer pada saat bersamaan.
- Kalau ingin memindahkan data terbaru lagi, tutup aplikasi dulu lalu copy ulang folder project atau file database.
- Jika muncul error Python tidak ditemukan, install ulang Python dan pastikan PATH aktif.

SELESAI
-------
Kalau semua langkah benar, aplikasi CRM akan bisa dibuka normal di laptop tujuan.
