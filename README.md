# CRM Tower v1

CRM Tower adalah aplikasi operasional CRM berbasis Python + SQLite yang kini punya:

- mode CLI untuk operasional cepat
- mode webapp berbasis Flask untuk akses lewat browser

Dirancang untuk:

- merapikan data member
- mencatat histori pembelian dan interaksi
- memantau member webinar
- memantau member platinum yang belum bergerak
- mencatat kendala member
- mengelola tugas harian tim CRM
- mencatat keluhan dan pertanyaan
- membuat ringkasan dan laporan sederhana

## Dasar rancangan
Aplikasi ini dibangun berdasarkan:
- jobdesk CRM: manajemen database, follow up & nurturing, customer experience, upselling, reporting
- SOP setelah webinar
- SOP setelah after sales kelas premium
- alur data dari OrderOnline dan histori CS
- kebutuhan tim CRM untuk menjaga relasi member dan mendorong progress member platinum

## Cara menjalankan

Masuk ke folder project:

```bash
cd /path/ke/crm_tower_project
```

Install dependensi:

```bash
pip install -r requirements.txt
```

Inisialisasi database:

```bash
python -m crm_tower.main --init-db --no-cli
```

Isi data demo:

```bash
python -m crm_tower.main --seed-demo --no-cli
```

Jalankan mode CLI:

```bash
python -m crm_tower.main
```

Jalankan webapp:

```bash
python -m crm_tower.main --web
```

Lalu buka:

```text
http://127.0.0.1:5000
```

Untuk akses dari device lain di WiFi yang sama:

```bash
python -m crm_tower.main --web --lan
```

Setelah server jalan, aplikasi akan menampilkan alamat lokal yang bisa dibuka supervisor, misalnya:

```text
http://192.168.1.10:5000
```

Untuk operasional harian yang lebih mudah di laptop CRM, cukup jalankan file:

```text
4-buka-crm-harian.bat
```

File ini akan:

- memastikan database dasar siap
- menampilkan link untuk CRM
- menampilkan link supervisor di WiFi yang sama
- lalu menjalankan server CRM

## Deploy ke GitHub + PythonAnywhere

Untuk kebutuhan tim kecil dengan 1 supervisor dan 1 CRM, jalur paling sederhana saat ini adalah:

- simpan source code di GitHub
- deploy webapp Flask ke PythonAnywhere
- tetap pakai SQLite pada tahap awal

Panduan langkah demi langkah ada di:

- `DEPLOY_PYTHONANYWHERE.md`

## Menu utama
- Ringkasan
- Data Member
- Pantauan Setelah Webinar
- Pantauan Member Platinum
- Keluhan & Pertanyaan
- Laporan Tim
- Pengaturan Dasar

## Fitur Webapp Saat Ini
- dashboard ringkasan CRM
- daftar, detail, tambah, dan edit member
- modul `Peluang Lanjutan` untuk upload CSV pembeli webinar/zoom dari OrderOnline
- pencatatan catatan member
- riwayat pembelian dari halaman detail member
- manajemen tugas CRM
- keluhan dan pertanyaan
- pantauan kendala member
- laporan harian, mingguan, dan bulanan

## API JSON
Endpoint JSON disediakan untuk memudahkan integrasi frontend React/Vue:

- `GET /api/dashboard`
- `GET /api/references`
- `GET /api/members`
- `POST /api/members`
- `GET /api/members/<id>`
- `PATCH /api/members/<id>`
- `GET /api/tasks`
- `POST /api/tasks`
- `POST /api/tasks/<id>/complete`
- `GET /api/issues`
- `POST /api/issues`
- `PATCH /api/issues/<id>`
- `GET /api/obstacles`
- `POST /api/obstacles`
- `GET /api/reports?period=daily|weekly|monthly`
- `GET /api/orderonline`
- `POST /api/orderonline/auto-import`
- `PATCH /api/orderonline/<id>/followup`
- `POST /api/orderonline/<id>/quick-wa`
- `GET /api/settings/backup`
- `POST /api/settings/backup`
- `POST /api/settings/backup/run`

Contoh cepat:

```bash
curl http://127.0.0.1:5000/api/members
```

## Backup Google Drive
Untuk penggunaan 1 orang, pola yang dipakai adalah:

- database aktif tetap lokal: `crm_tower.db`
- backup disalin ke folder Google Drive
- backup otomatis dicek saat aplikasi dijalankan

Atur folder backup lewat web:

```text
http://127.0.0.1:5000/settings/backup
```

Fitur backup:

- simpan folder backup Google Drive
- backup manual sekali klik
- backup otomatis saat aplikasi dijalankan jika backup terakhir lebih dari 12 jam

## Workflow Peluang Lanjutan
Untuk data pembeli webinar/zoom dari OrderOnline:

1. buka menu `Peluang Lanjutan` di webapp
2. upload file CSV export dari OrderOnline
3. sistem menyimpan lead yang eligible follow up ke tabel staging
4. klik `Masukkan ke CRM` per lead, atau lakukan `Import Massal`
5. sistem akan membuat:

- member CRM baru jika nomor belum ada
- riwayat pembelian
- catatan awal import
- tugas `Bahas program lanjutan`

Data yang diproses difokuskan ke order yang:

- `status = completed`
- `payment_status = paid`
- produk mengandung kata `zoom` atau `webinar`

Tambahan workflow harian:

- `Auto Import CSV Terbaru` dari folder Downloads
- klik `WhatsApp`
- klik `Sudah WA` untuk update cepat
- export lead `Belum Dihubungi` ke CSV
- antrean lead otomatis punya prioritas `Tinggi/Sedang/Rendah`
- ada reminder lead yang sudah lewat 2 hari belum ditindaklanjuti
- template pesan WhatsApp menyesuaikan status follow up lead
- ada dashboard supervisor mingguan
- ada segmentasi lead berdasarkan umur pembelian
- auto-task follow up dibuat dari `next_followup_date` untuk lead yang sudah masuk CRM

## Catatan Pengembangan Lanjutan
- autentikasi dan role-based login
- impor data CSV/Excel
- filter dan pagination yang lebih lengkap
- dashboard KPI yang lebih mendalam
- API backend terpisah untuk frontend modern
