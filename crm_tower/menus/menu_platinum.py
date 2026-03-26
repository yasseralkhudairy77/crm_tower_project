from __future__ import annotations

from ..constants import KATEGORI_KENDALA, STATUS_KENDALA, TINGKAT_URGENSI
from ..services import references
from ..services.members import list_members, search_members, update_member
from ..services.obstacles import add_or_update_obstacle, list_obstacles_open
from .menu_helpers import header, input_tanggal, pilih_id, pilih_opsi, yn_prompt


def _member_platinum():
    rows = []
    for row in list_members():
        # platinum jika ada pembelian premium/platinum akan lebih baik dicek dari pembelian,
        # tapi untuk v1 kita pakai kata kunci pada ringkasan/riwayat pembelian sebagai titik awal pemantauan manual.
        rows.append(row)
    return rows


def daftar_member_belum_mulai_praktik():
    header("Member Belum Mulai Praktik")
    rows = [r for r in _member_platinum() if int(r["sudah_mulai_praktik"] or 0) == 0 and int(r["aktif"]) == 1]
    if not rows:
        print("Tidak ada member yang belum mulai praktik.")
        return
    for row in rows:
        print(f"#{row['id_member']} | {row['nama_member']} | PIC: {row['nama_pengguna']} | Tindak lanjut: {row['tanggal_tindak_lanjut_berikutnya']}")


def isi_progress_member():
    member_id = pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        return
    status_member = pilih_opsi("Status member baru", [
        "Sudah Dihubungi",
        "Sedang Dipantau",
        "Masih Terkendala",
        "Menunggu Arahan",
        "Sudah Mulai Belajar",
        "Sudah Mulai Praktik",
        "Tidak Aktif",
    ])
    tahap = pilih_opsi("Tahap progress baru", [
        "Belum dimulai",
        "Belajar dasar",
        "Menyiapkan langkah awal",
        "Mulai praktik",
        "Sedang berjalan",
        "Perlu evaluasi",
    ])
    praktik = yn_prompt("Sudah mulai praktik?")
    ringkasan = input("Ringkasan kondisi terbaru: ").strip()
    langkah = input("Langkah berikutnya: ").strip()
    tindak_lanjut = input_tanggal("Tanggal tindak lanjut berikutnya (YYYY-MM-DD): ")
    update_member(member_id, {
        "status_member": status_member,
        "tahap_progress": tahap,
        "sudah_mulai_praktik": praktik,
        "ringkasan_kondisi": ringkasan,
        "langkah_berikutnya": langkah,
        "tanggal_tindak_lanjut_berikutnya": tindak_lanjut,
    })
    print("Progress member berhasil diperbarui.")


def isi_kendala_member():
    member_id = pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        return
    pembuat = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih PIC pencatat")
    if not pembuat:
        return
    kategori = pilih_opsi("Kategori kendala", KATEGORI_KENDALA)
    detail = input("Detail kendala: ").strip()
    urgensi = pilih_opsi("Tingkat urgensi", TINGKAT_URGENSI)
    mentor = yn_prompt("Perlu bantuan mentor?")
    solusi = input("Solusi awal yang sudah diarahkan (opsional): ").strip()
    status = pilih_opsi("Status kendala", STATUS_KENDALA)
    add_or_update_obstacle(member_id, kategori, detail, urgensi, mentor, solusi, status, pembuat)
    update_member(member_id, {"status_member": "Masih Terkendala"})
    print("Kendala member berhasil dicatat.")


def tampilkan_member_terkendala():
    header("Member yang Sedang Terkendala")
    rows = list_obstacles_open()
    if not rows:
        print("Belum ada kendala terbuka.")
        return
    for row in rows:
        print(
            f"#{row['id_member']} | {row['nama_member']} | {row['kategori_kendala']} | "
            f"{row['tingkat_urgensi']} | Mentor: {'Ya' if row['perlu_bantuan_mentor'] else 'Belum'}"
        )


def menu_platinum():
    while True:
        header("Pantauan Member Platinum")
        print("1. Lihat member belum mulai praktik")
        print("2. Isi progress member")
        print("3. Isi kendala member")
        print("4. Lihat member yang sedang terkendala")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            daftar_member_belum_mulai_praktik()
        elif choice == "2":
            isi_progress_member()
        elif choice == "3":
            isi_kendala_member()
        elif choice == "4":
            tampilkan_member_terkendala()
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")