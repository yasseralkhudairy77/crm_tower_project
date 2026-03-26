from __future__ import annotations

from ..constants import KATEGORI_POTENSI, STATUS_MEMBER, TAHAP_PROGRESS
from ..services import references
from ..services.brands import BRAND_OPTIONS
from ..services.members import MemberInput, add_member, get_member_detail, list_members, search_members, update_member
from ..services.notes import add_note
from ..services.purchases import add_purchase
from ..utils.helpers import bool_label, score_potensi
from ..utils.validator import ValidationError
from .menu_helpers import header, input_tanggal, pilih_id, pilih_opsi, yn_prompt


def _pick_reference():
    sumber_id = pilih_id(references.list_sumber_data(), "id_sumber", "nama_sumber", "Pilih Sumber Data")
    pic_id = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih Penanggung Jawab")
    return sumber_id, pic_id


def tambah_member_baru():
    header("Tambah Member Baru")
    sumber_id, pic_id = _pick_reference()
    if not sumber_id or not pic_id:
        print("Proses dibatalkan.")
        return
    data = MemberInput(
        nama_member=input("Nama member: ").strip(),
        nomor_whatsapp=input("Nomor WhatsApp: ").strip(),
        email=input("Email (opsional): ").strip(),
        kota=input("Kota (opsional): ").strip(),
        brand_utama=pilih_opsi("Brand Utama", BRAND_OPTIONS + ["Umum"]),
        id_sumber=sumber_id,
        penanggung_jawab=pic_id,
        status_member=pilih_opsi("Status Member Awal", STATUS_MEMBER),
        tahap_progress=pilih_opsi("Tahap Progress Awal", TAHAP_PROGRESS),
        sudah_mulai_praktik=yn_prompt("Sudah mulai praktik?"),
        kategori_potensi=pilih_opsi("Kategori Potensi", KATEGORI_POTENSI),
        tanggal_kontak_terakhir=input_tanggal("Tanggal kontak terakhir (YYYY-MM-DD, opsional): ", wajib=False),
        tanggal_tindak_lanjut_berikutnya=input_tanggal("Tanggal tindak lanjut berikutnya (YYYY-MM-DD): "),
        ringkasan_kondisi=input("Ringkasan kondisi awal: ").strip(),
        langkah_berikutnya=input("Langkah berikutnya: ").strip(),
    )
    try:
        member_id = add_member(data)
        print(f"Member berhasil ditambahkan dengan ID #{member_id}.")
        tambah_beli = yn_prompt("Tambahkan riwayat pembelian sekarang?")
        if tambah_beli:
            tambah_riwayat_pembelian(default_member_id=member_id)
        tambah_catatan = yn_prompt("Tambahkan catatan awal sekarang?")
        if tambah_catatan:
            tambah_catatan_member(default_member_id=member_id)
    except ValidationError as exc:
        print(f"Gagal menyimpan member: {exc}")


def tampilkan_semua_member():
    header("Daftar Member")
    rows = list_members()
    if not rows:
        print("Belum ada member.")
        return
    for row in rows:
        print(
            f"#{row['id_member']} | {row['nama_member']} | {row['nomor_whatsapp']} | "
            f"PIC: {row['nama_pengguna']} | Status: {row['status_member']} | "
            f"Tindak lanjut: {row['tanggal_tindak_lanjut_berikutnya']} | {row['status_keterlambatan']}"
        )


def cari_member():
    keyword = input("Masukkan nama atau nomor WhatsApp: ").strip()
    header(f"Hasil Pencarian: {keyword}")
    rows = search_members(keyword)
    if not rows:
        print("Data belum ditemukan.")
        return
    for row in rows:
        print(
            f"#{row['id_member']} | {row['nama_member']} | {row['nomor_whatsapp']} | "
            f"PIC: {row['nama_pengguna']} | Status: {row['status_member']}"
        )


def detail_member():
    member_id = input("Masukkan ID member: ").strip()
    if not member_id.isdigit():
        print("ID member harus angka.")
        return
    data = get_member_detail(int(member_id))
    if not data:
        print("Member tidak ditemukan.")
        return
    m = data["member"]
    header(f"Detail Member #{m['id_member']}")
    print(f"Nama                    : {m['nama_member']}")
    print(f"Nomor WhatsApp          : {m['nomor_whatsapp']}")
    print(f"Kota                    : {m['kota'] or '-'}")
    print(f"Sumber Data             : {m['nama_sumber']}")
    print(f"PIC                     : {m['nama_pengguna']} ({m['peran']})")
    print(f"Status Member           : {m['status_member']}")
    print(f"Tahap Progress          : {m['tahap_progress']}")
    print(f"Sudah Mulai Praktik     : {bool_label(m['sudah_mulai_praktik'])}")
    print(f"Kategori Potensi        : {m['kategori_potensi']}")
    print(f"Nilai Potensi           : {m['nilai_potensi']}")
    print(f"Kontak Terakhir         : {m['tanggal_kontak_terakhir'] or '-'}")
    print(f"Tindak Lanjut Berikutnya: {m['tanggal_tindak_lanjut_berikutnya']}")
    print(f"Status Keterlambatan    : {m['status_keterlambatan']}")
    print(f"Ringkasan Kondisi       : {m['ringkasan_kondisi'] or '-'}")
    print(f"Langkah Berikutnya      : {m['langkah_berikutnya'] or '-'}")

    print("\nRiwayat Pembelian")
    if data["pembelian"]:
        for row in data["pembelian"]:
            print(f"- {row['tanggal_beli']} | {row['nama_program']} | {row['status_pembelian']} | Order: {row['nomor_order'] or '-'}")
    else:
        print("- Belum ada riwayat pembelian.")

    print("\nCatatan Terbaru")
    if data["catatan"][:5]:
        for row in data["catatan"][:5]:
            print(f"- {row['tanggal_catatan']} | {row['jenis_catatan']} | {row['nama_pengguna']}: {row['isi_catatan']}")
    else:
        print("- Belum ada catatan.")

    print("\nKendala Terbaru")
    kendala = data["kendala_terbaru"]
    if kendala:
        print(f"- {kendala['kategori_kendala']} | {kendala['tingkat_urgensi']} | Mentor: {bool_label(kendala['perlu_bantuan_mentor'])}")
        print(f"  Detail: {kendala['detail_kendala']}")
        print(f"  Solusi awal: {kendala['solusi_awal'] or '-'}")
    else:
        print("- Belum ada kendala tercatat.")


def ubah_data_member():
    member_id = input("Masukkan ID member yang ingin diubah: ").strip()
    if not member_id.isdigit():
        print("ID member harus angka.")
        return
    detail = get_member_detail(int(member_id))
    if not detail:
        print("Member tidak ditemukan.")
        return
    m = detail["member"]
    header(f"Ubah Data Member #{m['id_member']} - {m['nama_member']}")
    print("Kosongkan isian jika tidak ingin mengubah nilai.")
    updates = {}
    kota = input(f"Kota [{m['kota'] or '-'}]: ").strip()
    if kota:
        updates["kota"] = kota
    pic_id = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih PIC baru (kosongkan untuk tetap)")
    if pic_id:
        updates["penanggung_jawab"] = pic_id
    if yn_prompt("Ubah status member?"):
        updates["status_member"] = pilih_opsi("Pilih status member baru", STATUS_MEMBER)
    if yn_prompt("Ubah tahap progress?"):
        updates["tahap_progress"] = pilih_opsi("Pilih tahap progress baru", TAHAP_PROGRESS)
    praktik = input("Sudah mulai praktik? [y/n/kosong]: ").strip().lower()
    if praktik in {"y","ya","n","no","tidak"}:
        updates["sudah_mulai_praktik"] = 1 if praktik in {"y","ya"} else 0
    if yn_prompt("Ubah kategori potensi?"):
        kategori = pilih_opsi("Pilih kategori potensi baru", KATEGORI_POTENSI)
        updates["kategori_potensi"] = kategori
        updates["nilai_potensi"] = score_potensi(kategori)
    kontak = input_tanggal("Tanggal kontak terakhir baru (YYYY-MM-DD, kosongkan jika tetap): ", wajib=False)
    if kontak:
        updates["tanggal_kontak_terakhir"] = kontak
    tl = input_tanggal("Tanggal tindak lanjut berikutnya baru (YYYY-MM-DD, kosongkan jika tetap): ", wajib=False)
    if tl:
        updates["tanggal_tindak_lanjut_berikutnya"] = tl
    ringkasan = input("Ringkasan kondisi baru (kosongkan jika tetap): ").strip()
    if ringkasan:
        updates["ringkasan_kondisi"] = ringkasan
    langkah = input("Langkah berikutnya baru (kosongkan jika tetap): ").strip()
    if langkah:
        updates["langkah_berikutnya"] = langkah
    aktif = input("Apakah member tetap aktif? [y/n/kosong]: ").strip().lower()
    if aktif in {"y","ya","n","no","tidak"}:
        updates["aktif"] = 1 if aktif in {"y","ya"} else 0
    update_member(int(member_id), updates)
    print("Data member berhasil diperbarui.")


def tambah_riwayat_pembelian(default_member_id: int | None = None):
    header("Tambah Riwayat Pembelian")
    member_id = default_member_id or pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        print("Proses dibatalkan.")
        return
    program_id = pilih_id(references.list_program(), "id_program", "nama_program", "Pilih Program")
    if not program_id:
        print("Program wajib dipilih.")
        return
    from ..services.purchases import add_purchase

    tanggal_beli = input_tanggal("Tanggal beli (YYYY-MM-DD): ")
    nomor_order = input("Nomor order (opsional): ").strip()
    nilai_raw = input("Nilai transaksi (opsional): ").strip()
    nilai = float(nilai_raw) if nilai_raw else None
    status_pembelian = input("Status pembelian [berhasil/pending/batal]: ").strip() or "berhasil"
    sumber_transaksi = input("Sumber transaksi [default: OrderOnline]: ").strip() or "OrderOnline"
    catatan = input("Catatan pembelian (opsional): ").strip()
    brand_name = input("Brand pembelian (opsional): ").strip() or None
    add_purchase(member_id, program_id, tanggal_beli, nomor_order, nilai, brand_name, status_pembelian, sumber_transaksi, catatan)
    print("Riwayat pembelian berhasil ditambahkan.")


def tambah_catatan_member(default_member_id: int | None = None):
    from ..constants import JENIS_CATATAN
    member_id = default_member_id or pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        print("Proses dibatalkan.")
        return
    dibuat_oleh = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih pembuat catatan")
    if not dibuat_oleh:
        print("Pembuat catatan wajib dipilih.")
        return
    jenis = pilih_opsi("Pilih jenis catatan", JENIS_CATATAN)
    isi = input("Isi catatan: ").strip()
    try:
        add_note(member_id, jenis, isi, dibuat_oleh)
        print("Catatan berhasil ditambahkan.")
    except ValidationError as exc:
        print(f"Gagal menambah catatan: {exc}")


def menu_data_member():
    while True:
        header("Menu Data Member")
        print("1. Tambah member baru")
        print("2. Lihat semua member")
        print("3. Cari member")
        print("4. Detail member")
        print("5. Ubah data member")
        print("6. Tambah riwayat pembelian")
        print("7. Tambah catatan member")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            tambah_member_baru()
        elif choice == "2":
            tampilkan_semua_member()
        elif choice == "3":
            cari_member()
        elif choice == "4":
            detail_member()
        elif choice == "5":
            ubah_data_member()
        elif choice == "6":
            tambah_riwayat_pembelian()
        elif choice == "7":
            tambah_catatan_member()
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")
