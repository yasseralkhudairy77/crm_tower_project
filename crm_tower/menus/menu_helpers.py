from __future__ import annotations

from typing import Iterable, Sequence


def header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def pilih_opsi(title: str, options: Sequence[str]) -> str:
    header(title)
    for idx, opt in enumerate(options, 1):
        print(f"{idx}. {opt}")
    while True:
        choice = input("Pilih nomor: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        print("Pilihan belum sesuai, coba lagi ya.")


def pilih_id(rows: Iterable, id_key: str, label_key: str, title: str):
    rows = list(rows)
    header(title)
    if not rows:
        print("Belum ada data.")
        return None
    for row in rows:
        print(f"{row[id_key]}. {row[label_key]}")
    while True:
        choice = input("Masukkan ID (kosong untuk batal): ").strip()
        if not choice:
            return None
        if choice.isdigit():
            val = int(choice)
            for row in rows:
                if row[id_key] == val:
                    return val
        print("ID belum sesuai, coba lagi ya.")


def input_tanggal(label: str, wajib: bool = True) -> str:
    while True:
        value = input(label).strip()
        if not value and not wajib:
            return ""
        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            return value
        print("Gunakan format tanggal YYYY-MM-DD.")


def yn_prompt(label: str) -> int:
    value = input(f"{label} (y/n): ").strip().lower()
    return 1 if value in {"y", "ya"} else 0