from __future__ import annotations

from ..database import get_connection
from ..utils.helpers import now_str
from ..utils.validator import ValidationError, validasi_tanggal, wajib_isi


def add_purchase(
    member_id: int,
    program_id: int,
    tanggal_beli: str,
    nomor_order: str,
    nilai_transaksi: float | None,
    brand_name: str | None,
    status_pembelian: str,
    sumber_transaksi: str,
    catatan_pembelian: str,
) -> int:
    wajib_isi(str(member_id), "Member")
    wajib_isi(str(program_id), "Program")
    validasi_tanggal(tanggal_beli, "Tanggal beli")
    wajib_isi(status_pembelian, "Status pembelian")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO riwayat_pembelian (
                id_member, id_program, tanggal_beli, nomor_order, nilai_transaksi, brand_name,
                status_pembelian, sumber_transaksi, catatan_pembelian, dibuat_pada
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_id,
                program_id,
                tanggal_beli,
                nomor_order.strip() or None,
                nilai_transaksi,
                brand_name.strip() if brand_name else None,
                status_pembelian,
                sumber_transaksi.strip() or None,
                catatan_pembelian.strip() or None,
                now_str(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
