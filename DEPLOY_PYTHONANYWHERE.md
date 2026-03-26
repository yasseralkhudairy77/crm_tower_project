# Deploy CRM Tower ke GitHub + PythonAnywhere

Panduan ini cocok untuk formasi kecil:

- 1 supervisor
- 1 CRM
- backend Flask
- database SQLite

## 1. Siapkan repo GitHub

Masuk ke folder project:

```powershell
cd C:\Users\user\Downloads\CRM\crm_tower_project\crm_tower_project
```

Inisialisasi git:

```powershell
git init
git add .
git commit -m "Initial CRM Tower setup"
```

Buat repository baru di GitHub, lalu hubungkan:

```powershell
git remote add origin https://github.com/USERNAME/NAMA-REPO.git
git branch -M main
git push -u origin main
```

Catatan:

- file database lokal tidak ikut ter-push karena sudah masuk `.gitignore`
- ini aman untuk deploy awal tanpa membawa data percobaan dari laptop

## 2. Buat akun PythonAnywhere

Daftar di:

- https://www.pythonanywhere.com/

Lalu buat akun gratis terlebih dahulu.

## 3. Clone project dari GitHub di PythonAnywhere

Buka `Bash console` di PythonAnywhere, lalu jalankan:

```bash
git clone https://github.com/USERNAME/NAMA-REPO.git
cd NAMA-REPO
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Kalau versi Python di akun Anda berbeda, sesuaikan `python3.13`.

## 4. Buat web app Flask di PythonAnywhere

Di dashboard PythonAnywhere:

1. buka tab `Web`
2. klik `Add a new web app`
3. pilih `Manual configuration`
4. pilih versi Python yang tersedia

Setelah web app dibuat, buka file WSGI-nya lalu ganti isinya menjadi:

```python
import sys
from pathlib import Path

project_home = Path("/home/USERNAME/NAMA-REPO")
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from wsgi import application
```

Ganti:

- `USERNAME` dengan username PythonAnywhere Anda
- `NAMA-REPO` dengan nama repository GitHub Anda

## 5. Set virtualenv di PythonAnywhere

Di tab `Web`, isi bagian `Virtualenv` dengan path:

```text
/home/USERNAME/NAMA-REPO/.venv
```

## 6. Inisialisasi database di server

Masih di `Bash console` PythonAnywhere:

```bash
cd ~/NAMA-REPO
source .venv/bin/activate
python -m crm_tower.main --init-db --no-cli
```

Kalau ingin isi data demo:

```bash
python -m crm_tower.main --seed-demo --no-cli
```

## 7. Reload web app

Kembali ke tab `Web`, lalu klik `Reload`.

Sesudah itu buka domain PythonAnywhere Anda, misalnya:

```text
https://USERNAME.pythonanywhere.com/
```

## 8. Update aplikasi setelah ada perubahan

Setelah Anda edit di laptop dan push ke GitHub:

```bash
cd ~/NAMA-REPO
git pull
source .venv/bin/activate
pip install -r requirements.txt
```

Lalu klik `Reload` di tab `Web`.

## Catatan penting

- Untuk tahap awal, SQLite masih cukup karena user hanya 2 orang.
- Jangan commit file `crm_tower.db` dari laptop ke GitHub.
- Jika nanti trafik dan akses bersamaan bertambah, pindah ke PostgreSQL.
- Simpan `SECRET_KEY` sebagai environment variable di PythonAnywhere bila aplikasi mulai dipakai sungguhan.

## Rekomendasi operasional

- pakai database kosong saat deploy pertama
- isi data lewat webapp atau import CSV
- lakukan backup rutin dari menu backup
- jika ingin supervisor memantau CRM, langkah berikutnya adalah tambah login dan dashboard supervisor
