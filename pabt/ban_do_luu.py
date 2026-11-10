"""Bản đồ lưu TRONG file dự án (người dùng 31/10/2026: "lưu, ghi nhớ bản đồ vào file dự án .larc, sau này mở lên có sẵn không phải tải
lại"). Không Qt.

- ban_do_lop: lớp KML / KMZ đã mở để xem (nội dung XML KML nén zlib - đã qua kiểm tra an toàn khi mở), mở bản đồ là có lại.
- ban_do_o: ô ảnh nền (vệ tinh / đường / địa hình) của vùng dự án, mở trên máy khác / mất mạng vẫn có (gửi file dự án là gửi theo).

KHÔNG đổi PHIEN_BAN_CSDL: bảng tạo khi lưu lần đầu (bản cũ mở file vẫn được - bảng thừa). Không thuộc DANH_MUC, không vào sổ hoàn tác
(hoan_tac.BO_QUA). Ô ảnh chỉ nhận JPEG / PNG (an_toan.nhan_dang_dau_tep)."""
from __future__ import annotations

import zlib

from . import csdl

BANG_LOP, BANG_O = 'ban_do_lop', 'ban_do_o'
# TỔNG ô ảnh nền lưu một lần (chỉ lớp ảnh, ~25-35 KB / ô: tối đa ~12 MB) - nhiều hơn thì bớt mức phóng sâu nhất. Rà soát 31/10/2026:
# 1.500 ô x 3 lớp làm file dự án +65 MB -> mỗi bản sao lưu tự động / mốc khôi phục / lần Google Drive đồng bộ cũng +65 MB
O_LUU_TOI_DA = 400
KB_MOI_O = 30                    # ước dung lượng một ô ảnh (hộp xác nhận)
KML_TOI_DA = 60 * 2 ** 20


def co_bang(con, bang: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (bang,)).fetchone())


def dam_bao_bang(con) -> None:
    con.execute(f'''CREATE TABLE IF NOT EXISTS {BANG_LOP} (ten TEXT PRIMARY KEY, du_lieu BLOB NOT NULL, ngay TEXT NOT NULL DEFAULT '')''')
    con.execute(f'''CREATE TABLE IF NOT EXISTS {BANG_O} (lop TEXT NOT NULL, z INTEGER NOT NULL, x INTEGER NOT NULL, y INTEGER NOT NULL,
                    anh BLOB NOT NULL, PRIMARY KEY (lop, z, x, y))''')


def _bay_gio() -> str:
    import datetime
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


# ---------------------------------------------------------------- lớp KML
def luu_lop(con, ds: list) -> int:
    """ds = [(tên, XML KML bytes)] -> lưu (tên trùng thì thay). Trả số lớp."""
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')                 # vai trò tài khoản máy chủ (phan_quyen)
    ds = [(str(t), bytes(x)) for t, x in ds if x and len(x) <= KML_TOI_DA]
    if not ds:
        return 0
    with csdl.giao_dich(con):
        dam_bao_bang(con)
        for ten, xml in ds:
            con.execute(f'INSERT OR REPLACE INTO {BANG_LOP} (ten, du_lieu, ngay) VALUES (?, ?, ?)', (ten, zlib.compress(xml, 6), _bay_gio()))
        csdl.ghi_nhat_ky(con, 'Lưu bản đồ vào dự án', f'{len(ds)} lớp KML: ' + ', '.join(t for t, _ in ds)[:300])
    return len(ds)


def ds_lop(con) -> list:
    """[(tên, XML KML bytes)] đã lưu (dòng hỏng bỏ qua)."""
    if con is None or not co_bang(con, BANG_LOP):
        return []
    kq = []
    for ten, du in con.execute(f'SELECT ten, du_lieu FROM {BANG_LOP} ORDER BY rowid'):
        try:
            kq.append((ten, zlib.decompress(du)))
        except (zlib.error, TypeError):
            continue
    return kq


def xoa_lop(con, ten: list | None = None) -> int:
    """Bỏ lớp KML đã lưu (ten None = tất cả). Trả số lớp bỏ."""
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')                 # vai trò tài khoản máy chủ (phan_quyen)
    if not co_bang(con, BANG_LOP):
        return 0
    with csdl.giao_dich(con):
        if ten is None:
            n = con.execute(f'DELETE FROM {BANG_LOP}').rowcount
        else:
            n = sum(con.execute(f'DELETE FROM {BANG_LOP} WHERE ten = ?', (t,)).rowcount for t in ten)
        if n:
            csdl.ghi_nhat_ky(con, 'Bỏ bản đồ đã lưu', f'{n} lớp KML')
    if n:
        thu_gon(con)
    return n


# ---------------------------------------------------------------- ô ảnh nền
def luu_o(con, ds: list) -> int:
    """ds = [(lớp, z, x, y, ảnh bytes)] -> lưu (chỉ JPEG / PNG). Trả số ô đã lưu."""
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')                 # vai trò tài khoản máy chủ (phan_quyen)
    from .an_toan import nhan_dang_dau_tep
    hop = [(lp, int(z), int(x), int(y), bytes(a)) for lp, z, x, y, a in ds
           if a and nhan_dang_dau_tep(bytes(a[:16])) in ('jpeg', 'png')]
    if not hop:
        return 0
    with csdl.giao_dich(con):
        dam_bao_bang(con)
        con.executemany(f'INSERT OR REPLACE INTO {BANG_O} (lop, z, x, y, anh) VALUES (?, ?, ?, ?, ?)', hop)
        csdl.ghi_nhat_ky(con, 'Lưu bản đồ vào dự án', f'{len(hop)} ô ảnh nền')
    return len(hop)


def doc_o(con, lop: str, z: int, ds_xy: list) -> dict:
    """{(x, y): ảnh} của các ô đã lưu trong danh sách (lớp, mức z)."""
    if con is None or not ds_xy or not co_bang(con, BANG_O):
        return {}
    can = set(ds_xy)
    xs = [x for x, _ in can]
    ys = [y for _, y in can]
    kq = {}
    for x, y, a in con.execute(f'SELECT x, y, anh FROM {BANG_O} WHERE lop = ? AND z = ? AND x BETWEEN ? AND ? AND y BETWEEN ? AND ?',
                               (lop, int(z), min(xs), max(xs), min(ys), max(ys))):
        if (x, y) in can:
            kq[(x, y)] = bytes(a)
    return kq


def tom_tat(con) -> dict:
    """{'lop': số lớp KML, 'o': số ô ảnh, 'kich': tổng byte} đã lưu."""
    kq = {'lop': 0, 'o': 0, 'kich': 0}
    if con is None:
        return kq
    if co_bang(con, BANG_LOP):
        n, k = con.execute(f'SELECT COUNT(*), COALESCE(SUM(LENGTH(du_lieu)), 0) FROM {BANG_LOP}').fetchone()
        kq['lop'], kq['kich'] = n, k
    if co_bang(con, BANG_O):
        n, k = con.execute(f'SELECT COUNT(*), COALESCE(SUM(LENGTH(anh)), 0) FROM {BANG_O}').fetchone()
        kq['o'], kq['kich'] = n, kq['kich'] + k
    return kq


def xoa_o(con) -> int:
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')                 # vai trò tài khoản máy chủ (phan_quyen)
    if not co_bang(con, BANG_O):
        return 0
    with csdl.giao_dich(con):
        n = con.execute(f'DELETE FROM {BANG_O}').rowcount
        if n:
            csdl.ghi_nhat_ky(con, 'Bỏ bản đồ đã lưu', f'{n} ô ảnh nền')
    if n:
        thu_gon(con)
    return n


def thu_gon(con) -> None:
    """VACUUM sau khi bỏ ảnh / lớp: file dự án nhỏ lại thật (không thì giữ nguyên cỡ). Lỗi (file khóa, đang giao dịch): bỏ qua."""
    try:
        if not con.in_transaction:
            con.execute('VACUUM')
    except Exception:                                   # noqa: BLE001
        pass


def o_vung_du_an(khung: tuple, z_max: int, toi_da: int = O_LUU_TOI_DA) -> list:
    """Ô (z, x, y) phủ khung dự án (nới 10%) từ mức vừa khung tới z_max; quá toi_da thì bớt mức sâu nhất (như "lưu khi mất sóng" của
    LARC Mobile)."""
    from . import nen_ban_do as nb
    vmin, vmax, kmin, kmax = khung
    dv, dk = (vmax - vmin) * nb.LE_KHUNG + 1e-4, (kmax - kmin) * nb.LE_KHUNG + 1e-4
    vmin, vmax, kmin, kmax = vmin - dv, vmax + dv, kmin - dk, kmax + dk

    def o_muc(z):
        x0, y0 = nb.o_tu_toa_do(vmax, kmin, z)
        x1, y1 = nb.o_tu_toa_do(vmin, kmax, z)
        return [(z, x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    z_dau = z_max
    for z in range(z_max, 2, -1):                   # mức vừa khung: cả khung <= 4 ô
        if len(o_muc(z)) <= 4:
            z_dau = z
            break
    while True:
        ds = [o for z in range(z_dau, z_max + 1) for o in o_muc(z)]
        if len(ds) <= toi_da or z_max <= z_dau:
            return ds[:toi_da]
        z_max -= 1
