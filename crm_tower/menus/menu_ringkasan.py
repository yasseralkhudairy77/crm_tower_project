from __future__ import annotations

from ..services.reports import dashboard_summary, important_lists
from .menu_helpers import header


def show_ringkasan() -> None:
    summary = dashboard_summary()
    lists = important_lists()

    header("Ringkasan CRM Tower")
    print(f"Total member aktif            : {summary['total_member_aktif']}")
    print(f"Member baru hari ini          : {summary['member_baru_hari_ini']}")
    print(f"Tindak lanjut hari ini        : {summary['tindak_lanjut_hari_ini']}")
    print(f"Member terlambat ditindaklanjuti: {summary['member_terlambat']}")
    print(f"Member masih terkendala       : {summary['member_terkendala']}")
    print(f"Peluang sangat potensial      : {summary['peluang_sangat_potensial']}")
    print(f"Keluhan belum selesai         : {summary['keluhan_belum_selesai']}")

    print("\n5 Tugas Paling Mendesak")
    if lists["tugas_mendesak"]:
        for row in lists["tugas_mendesak"]:
            print(f"- #{row['id_tugas']} | {row['nama_member']} | {row['jenis_tugas']} | {row['prioritas']} | {row['tanggal_jatuh_tempo']}")
    else:
        print("- Belum ada tugas mendesak.")

    print("\n5 Member yang Butuh Perhatian")
    if lists["member_perhatian"]:
        for row in lists["member_perhatian"]:
            print(f"- #{row['id_member']} | {row['nama_member']} | {row['status_member']} | {row['status_keterlambatan']}")
    else:
        print("- Tidak ada member kritis saat ini.")

    print("\n5 Peluang Program Lanjutan Teratas")
    if lists["peluang_top"]:
        for row in lists["peluang_top"]:
            print(f"- #{row['id_peluang']} | {row['nama_member']} | {row['tingkat_potensi']} | {row['status_penawaran']}")
    else:
        print("- Belum ada peluang tercatat.")