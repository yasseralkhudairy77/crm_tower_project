from __future__ import annotations

from ..constants import JENIS_TUGAS, PRIORITAS
from ..services import references
from ..services.members import list_members
from ..services.tasks import add_task, complete_task, list_tasks_by_pic, list_tasks_overdue, list_tasks_today
from .menu_helpers import header, input_tanggal, pilih_id, pilih_opsi


def lihat_tugas_hari_ini():
    header("Daftar Tugas Hari Ini")
    rows = list_tasks_today()
    if not rows:
        print("Tidak ada tugas hari ini.")
        return
    for row in rows:
        print(f"#{row['id_tugas']} | {row['nama_member']} | {row['jenis_tugas']} | {row['prioritas']} | {row['status_tugas']}")


def lihat_tugas_terlambat():
    header("Daftar Tugas Terlambat")
    rows = list_tasks_overdue()
    if not rows:
        print("Tidak ada tugas terlambat.")
        return
    for row in rows:
        print(f"#{row['id_tugas']} | {row['nama_member']} | {row['jenis_tugas']} | Jatuh tempo: {row['tanggal_jatuh_tempo']}")


def tambah_tugas():
    member_id = pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        return
    pic_id = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih Penanggung Jawab")
    if not pic_id:
        return
    jenis = pilih_opsi("Jenis tugas", JENIS_TUGAS)
    jatuh_tempo = input_tanggal("Tanggal jatuh tempo (YYYY-MM-DD): ")
    prioritas = pilih_opsi("Prioritas", PRIORITAS)
    catatan = input("Catatan tugas (opsional): ").strip()
    add_task(member_id, jenis, pic_id, jatuh_tempo, prioritas, catatan)
    print("Tugas berhasil ditambahkan.")


def tandai_selesai():
    task_id = input("Masukkan ID tugas yang selesai: ").strip()
    if not task_id.isdigit():
        print("ID tugas harus angka.")
        return
    complete_task(int(task_id))
    print("Tugas ditandai selesai.")


def lihat_tugas_per_pic():
    pic_id = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih PIC")
    if not pic_id:
        return
    header("Tugas per PIC")
    rows = list_tasks_by_pic(pic_id)
    if not rows:
        print("Belum ada tugas untuk PIC tersebut.")
        return
    for row in rows:
        print(f"#{row['id_tugas']} | {row['nama_member']} | {row['jenis_tugas']} | {row['tanggal_jatuh_tempo']} | {row['status_tugas']}")


def menu_tugas():
    while True:
        header("Daftar Tugas")
        print("1. Lihat tugas hari ini")
        print("2. Lihat tugas terlambat")
        print("3. Tambah tugas baru")
        print("4. Tandai tugas selesai")
        print("5. Lihat tugas per PIC")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            lihat_tugas_hari_ini()
        elif choice == "2":
            lihat_tugas_terlambat()
        elif choice == "3":
            tambah_tugas()
        elif choice == "4":
            tandai_selesai()
        elif choice == "5":
            lihat_tugas_per_pic()
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")