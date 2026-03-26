from __future__ import annotations

from ..database import fetchall


def list_pengguna():
    return fetchall("SELECT * FROM pengguna WHERE aktif = 1 ORDER BY nama_pengguna")


def list_sumber_data():
    return fetchall("SELECT * FROM sumber_data ORDER BY nama_sumber")


def list_program():
    return fetchall("SELECT * FROM program WHERE status_program = 'Aktif' ORDER BY nama_program")