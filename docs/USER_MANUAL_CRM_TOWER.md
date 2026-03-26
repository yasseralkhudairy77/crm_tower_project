# User Manual CRM Tower

## 1. Gambaran Umum

CRM Tower adalah aplikasi web internal untuk membantu tim CRM memantau member, prospek after-sales, tugas, kendala, keluhan, laporan, dan monitoring supervisor.

Aplikasi ini dipakai untuk:

- mencatat data member dan progres relasi
- memantau prospek program lanjutan
- mencatat keluhan dan kendala member
- mengelola tugas CRM harian
- melihat KPI operasional dan monitoring supervisor

## 2. Siapa yang Menggunakan

- CRM: menjalankan operasional harian, input dan update data
- Supervisor: memantau KPI, progres kerja, tugas prioritas, dan antrean follow up

## 3. Cara Menjalankan Aplikasi

Untuk operasional harian di laptop CRM:

1. Sambungkan laptop CRM ke WiFi kantor yang biasa dipakai.
2. Buka folder project CRM Tower.
3. Jalankan file `4-buka-crm-harian.bat`.
4. Tunggu sampai jendela Command Prompt menampilkan link akses.
5. Biarkan jendela Command Prompt tetap terbuka selama aplikasi dipakai.

Catatan penting:

- jika jendela Command Prompt ditutup, webapp akan berhenti
- laptop CRM harus tetap menyala agar supervisor bisa mengakses aplikasi

## 4. Cara Akses

### Akses CRM

CRM membuka aplikasi dari laptop CRM melalui browser:

`http://127.0.0.1:5000`

### Akses Supervisor

Supervisor membuka aplikasi dari device lain yang tersambung ke WiFi yang sama, menggunakan alamat IP lokal laptop CRM.

Contoh:

`http://192.168.18.123:5000/supervisor`

Alamat IP bisa berubah jika jaringan berubah. Gunakan alamat yang tampil pada saat file `4-buka-crm-harian.bat` dijalankan.

## 5. Menu Utama

Menu utama aplikasi terdiri dari:

- Dashboard
- Member
- Peluang Lanjutan
- Keluhan
- Kendala
- Supervisor
- Laporan
- Backup

## 6. Dashboard

Halaman Dashboard digunakan untuk melihat ringkasan kondisi CRM secara umum.

Fungsi utama:

- melihat total member aktif
- melihat prospek program lanjutan
- melihat follow up hari ini
- melihat member yang perlu perhatian
- melihat kontak terbaru dan reminder follow up

Kapan dipakai:

- saat memulai hari kerja
- saat ingin melihat fokus kerja harian dengan cepat

## 7. Menu Member

Menu Member digunakan untuk mengelola data relasi member.

Fungsi utama:

- melihat daftar member
- menambah member baru
- mengedit data member
- menjadwalkan follow up berikutnya
- melihat detail member
- menambahkan catatan
- menambahkan riwayat pembelian
- export data member ke CSV

Yang biasa diupdate oleh CRM:

- status member
- tahap progress
- tanggal kontak terakhir
- tanggal tindak lanjut berikutnya
- ringkasan kondisi
- langkah berikutnya

## 8. Detail Member

Pada halaman detail member, CRM dapat:

- melihat identitas lengkap member
- melihat riwayat pembelian
- melihat catatan member
- melihat tugas terkait member
- melihat keluhan member
- menambahkan catatan baru
- menambahkan riwayat pembelian

Halaman ini dipakai saat CRM ingin melihat konteks lengkap sebelum follow up.

## 9. Menu Peluang Lanjutan

Menu Peluang Lanjutan dipakai untuk memantau pembeli webinar atau program awal yang berpotensi ditawarkan ke program lanjutan.

Fungsi utama:

- import CSV OrderOnline
- auto-import dari file terbaru
- melihat antrean prospek
- update status follow up
- tandai sudah WhatsApp
- memasukkan prospek ke CRM
- export prospek ke CSV

Status follow up yang tersedia:

- Belum Dihubungi
- Sudah Dihubungi
- Tertarik
- Perlu Follow Up Lagi
- Tidak Tertarik
- Closing After Sales

## 10. Menu Tugas

Menu Tugas dipakai untuk mengelola pekerjaan CRM harian.

Fungsi utama:

- menambah tugas baru
- melihat tugas hari ini
- melihat tugas terlambat
- menandai tugas selesai
- memfilter tugas berdasarkan status dan PIC

Supervisor bisa memakai halaman ini untuk melihat beban kerja CRM.

## 11. Menu Keluhan

Menu Keluhan dipakai untuk mencatat dan memantau masalah atau komplain dari member.

Fungsi utama:

- mencatat keluhan baru
- melihat daftar keluhan
- update status penanganan
- memantau keluhan yang belum selesai

Contoh penggunaan:

- member mengeluh akses kelas
- member menanyakan urutan langkah
- member mengalami kebingungan operasional

## 12. Menu Kendala

Menu Kendala dipakai untuk mencatat hambatan belajar, hambatan praktik, atau hambatan progres member.

Fungsi utama:

- mencatat kendala baru
- mengupdate kendala yang sudah ada
- menandai apakah butuh bantuan mentor
- memantau kendala yang masih terbuka

Contoh:

- belum mulai praktik
- bingung langkah awal
- butuh bantuan mentor
- belum paham materi lanjutan

## 13. Dashboard Supervisor

Dashboard Supervisor dipakai khusus untuk monitoring kerja CRM.

Isi utamanya:

- follow up hari ini
- member terlambat
- tugas hari ini
- tugas terlambat
- kontak CRM per periode
- closing per periode
- ringkasan kinerja
- skor kinerja PIC
- tugas prioritas
- member yang perlu perhatian
- antrean follow up
- aktivitas terbaru

Halaman ini dipakai supervisor untuk:

- melihat progres kerja harian
- mengecek apakah CRM aktif follow up
- melihat beban kerja dan item yang tertinggal
- melihat hasil kerja pada periode harian, mingguan, atau bulanan

## 14. Menu Laporan

Menu Laporan dipakai untuk melihat KPI CRM dalam format periodik.

Pilihan periode:

- Harian
- Mingguan
- Bulanan

Isi laporan:

- KPI utama
- kesehatan CRM
- breakdown per brand
- status follow up
- jenis keluhan
- kategori kendala
- kinerja per PIC
- aktivitas terbaru

## 15. Menu Backup

Menu Backup dipakai untuk mengelola salinan database.

Fungsi utama:

- menentukan folder backup
- menjalankan backup manual
- melihat riwayat backup
- reset database untuk mode percobaan

Catatan:

- reset database akan menghapus data aktif dari aplikasi
- gunakan fitur reset hanya untuk kebutuhan percobaan atau pembersihan awal

## 16. Alur Kerja Harian CRM

Alur sederhana yang disarankan:

1. Buka `4-buka-crm-harian.bat`.
2. Buka Dashboard untuk melihat fokus kerja hari ini.
3. Cek menu Peluang Lanjutan untuk prospek baru dan pending.
4. Cek menu Member untuk relasi yang harus di-follow up.
5. Update tugas, keluhan, dan kendala sepanjang hari.
6. Di akhir hari, pastikan data follow up dan tugas sudah diperbarui.

## 17. Alur Monitoring Harian Supervisor

Alur sederhana yang disarankan:

1. Buka halaman Supervisor.
2. Cek KPI utama dan ringkasan kinerja.
3. Periksa tugas terlambat.
4. Periksa member yang perlu perhatian.
5. Periksa antrean follow up yang belum disentuh.
6. Gunakan aktivitas terbaru untuk memastikan progres kerja benar-benar berjalan.

## 18. Jika Aplikasi Tidak Bisa Diakses

Periksa hal berikut:

- laptop CRM masih menyala
- jendela Command Prompt masih terbuka
- laptop CRM dan device supervisor berada di WiFi yang sama
- alamat IP yang dipakai supervisor benar
- firewall Windows tidak memblokir akses

## 19. Penutup

CRM Tower dirancang agar operasional CRM lebih rapi, lebih terukur, dan lebih mudah dipantau supervisor. Gunakan update data secara konsisten agar dashboard dan laporan menampilkan kondisi nyata di lapangan.
