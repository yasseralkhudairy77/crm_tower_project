from __future__ import annotations

from ..services import references
from .menu_helpers import header


def show_pengaturan():
    while True:
        header("Pengaturan Dasar")
        print("1. Lihat data pengguna/PIC")
        print("2. Lihat sumber data")
        print("3. Lihat daftar program")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            header("Data Pengguna/PIC")
            for row in references.list_pengguna():
                print(f"#{row['id_pengguna']} | {row['nama_pengguna']} | {row['peran']} | {row['tim']}")
        elif choice == "2":
            header("Sumber Data")
            for row in references.list_sumber_data():
                print(f"#{row['id_sumber']} | {row['nama_sumber']} | {row['keterangan'] or '-'}")
        elif choice == "3":
            header("Program")
            for row in references.list_program():
                print(f"#{row['id_program']} | {row['nama_program']} | {row['jenis_program']}")
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")