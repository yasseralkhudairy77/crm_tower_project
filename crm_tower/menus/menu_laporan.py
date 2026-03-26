from __future__ import annotations

from pathlib import Path

from ..services.reports import build_period_report, export_period_report
from .menu_helpers import header

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output_laporan"


def tampilkan_laporan(period: str) -> None:
    header(f"Laporan {period.title()}")
    print(build_period_report(period))


def export_laporan(period: str) -> None:
    path = export_period_report(period, OUTPUT_DIR)
    print(f"Laporan berhasil diekspor ke: {path}")


def menu_laporan():
    while True:
        header("Laporan Tim")
        print("1. Tampilkan laporan harian")
        print("2. Tampilkan laporan mingguan")
        print("3. Tampilkan laporan bulanan")
        print("4. Ekspor laporan harian")
        print("5. Ekspor laporan mingguan")
        print("6. Ekspor laporan bulanan")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            tampilkan_laporan("daily")
        elif choice == "2":
            tampilkan_laporan("weekly")
        elif choice == "3":
            tampilkan_laporan("monthly")
        elif choice == "4":
            export_laporan("daily")
        elif choice == "5":
            export_laporan("weekly")
        elif choice == "6":
            export_laporan("monthly")
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")