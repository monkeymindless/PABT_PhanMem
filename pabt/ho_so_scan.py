"""Hồ sơ scan (PDF / ảnh) đính kèm từng hộ và danh sách hộ hoàn tất công tác bồi thường (0.9.96, người dùng 16/10/2026). Không Qt.

- File scan lưu ĐƯỜNG DẪN (không chép file) vào bảng `anh_hien_trang` có sẵn (v16) với `khop_theo = KHOP` - không đổi lược đồ.
- "Hoàn tất công tác bồi thường" (CTBT) của một hộ = đã có quyết định phê duyệt VÀ đã bàn giao mặt bằng (đã nhận tiền hay chưa không
  xét - hộ không nhận tiền, tiền gửi kho bạc vẫn hoàn tất khi đã bàn giao). Nhóm theo đợt trình của hộ (ho.dot_id).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import an_toan as _an_toan
from . import csdl

KHOP = 'ho_so_scan'
DUOI = ('.pdf', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp')
LOC_FILE = 'PDF, ảnh (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)'
CHUA_XEP_DOT = 'Chưa xếp đợt'

_BANG = '''CREATE TABLE IF NOT EXISTS anh_hien_trang (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    duong_dan TEXT NOT NULL, ten_file TEXT NOT NULL, khop_theo TEXT NOT NULL DEFAULT '', luc TEXT NOT NULL,
    UNIQUE (ma_ho, duong_dan))'''


def _co_bang(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'anh_hien_trang'").fetchone() is not None


def ds_file(con, ma_ho: int) -> list:
    """[dict(id, duong_dan, ten_file, luc, con)] - con: file còn trên đĩa."""
    if not _co_bang(con):
        return []
    return [dict(id=r[0], duong_dan=r[1], ten_file=r[2], luc=r[3], con=Path(r[1]).exists())
            for r in con.execute('SELECT id, duong_dan, ten_file, luc FROM anh_hien_trang WHERE ma_ho = ? AND khop_theo = ? '
                                 'ORDER BY id', (ma_ho, KHOP))]


def dem_theo_ho(con) -> dict:
    """{ma_ho: số file scan} (một truy vấn - dùng cho bảng tiến độ nhiều hộ)."""
    if not _co_bang(con):
        return {}
    return {r[0]: r[1] for r in con.execute('SELECT ma_ho, COUNT(*) FROM anh_hien_trang WHERE khop_theo = ? GROUP BY ma_ho', (KHOP,))}


def them_file(con, ma_ho: int, files) -> int:
    """Đính kèm các file (đường dẫn đầy đủ) vào hộ; file đã gắn bỏ qua. Trả số file thêm mới."""
    from .lap_pa import kiem_ho_nhan_viec
    kiem_ho_nhan_viec(con, ma_ho)
    ds = [Path(f) for f in files if str(f).strip()]
    if not ds:
        return 0
    luc = datetime.now().strftime('%d/%m/%Y %H:%M')
    n = 0
    with csdl.giao_dich(con):
        con.execute(_BANG)
        for f in ds:
            cur = con.execute('INSERT OR IGNORE INTO anh_hien_trang (ma_ho, duong_dan, ten_file, khop_theo, luc) VALUES (?, ?, ?, ?, ?)',
                              (ma_ho, str(f.resolve()), f.name, KHOP, luc))
            n += cur.rowcount
        csdl.ghi_nhat_ky(con, f'Đính kèm {n} file hồ sơ scan vào hộ {ma_ho}', ', '.join(f.name for f in ds))
    return n


def bo_file(con, ma_ho: int, ds_id) -> int:
    """Bỏ đính kèm (chỉ xóa liên kết, KHÔNG xóa file trên đĩa). Trả số liên kết đã bỏ."""
    from .lap_pa import kiem_ho_nhan_viec
    kiem_ho_nhan_viec(con, ma_ho)
    ds_id = [int(i) for i in ds_id]
    if not ds_id or not _co_bang(con):
        return 0
    n = 0
    with csdl.giao_dich(con):
        for i in ds_id:
            n += con.execute('DELETE FROM anh_hien_trang WHERE id = ? AND ma_ho = ? AND khop_theo = ?', (i, ma_ho, KHOP)).rowcount
        csdl.ghi_nhat_ky(con, f'Bỏ {n} file hồ sơ scan của hộ {ma_ho}')
    return n


# ---------------------------------------------------------------- hoàn tất công tác bồi thường
def hoan_tat(x) -> bool:
    """x: theo_doi.TongHopHo. Đã có quyết định phê duyệt và đã bàn giao mặt bằng."""
    return bool(x.qd) and bool(x.da_ban_giao)


def ten_dot_theo_ho(con) -> dict:
    """{ma_ho: 'Đợt N[ - tên]'} của các hộ đã xếp đợt trình."""
    kq = {}
    for r in con.execute('SELECT h.ma_ho, d.so, d.ten FROM ho h JOIN dot_trinh d ON d.id = h.dot_id'):
        kq[r[0]] = f'Đợt {r[1]}' + (f' - {r[2]}' if r[2] and str(r[2]).strip() and str(r[2]).strip() != f'Đợt {r[1]}' else '')
    return kq


def chu_hoan_tat(x, dot: str) -> str:
    """Chữ cột "Hoàn tất CTBT" của bảng tiến độ: 'Hoàn tất · Đợt 2' / 'Hoàn tất' / ''."""
    if not hoan_tat(x):
        return ''
    return 'Hoàn tất' + (f' · {dot}' if dot else '')


def ds_hoan_tat(con, ds=None) -> list:
    """[(đợt, [TongHopHo hoàn tất])] theo thứ tự đợt (chưa xếp đợt cuối). ds: danh sách TongHopHo có sẵn (không thì đọc)."""
    from . import theo_doi
    ds = theo_doi.tong_hop(con, tinh_pa=False) if ds is None else ds
    dot = ten_dot_theo_ho(con)
    so_dot = {r[0]: r[1] for r in con.execute('SELECT h.ma_ho, d.so FROM ho h JOIN dot_trinh d ON d.id = h.dot_id')}
    nhom = {}
    for x in ds:
        if hoan_tat(x):
            nhom.setdefault(dot.get(x.ma_ho, CHUA_XEP_DOT), []).append(x)
    thu_tu = {}
    for x in ds:
        k = dot.get(x.ma_ho, CHUA_XEP_DOT)
        thu_tu.setdefault(k, so_dot.get(x.ma_ho, 10 ** 9))
    return sorted(nhom.items(), key=lambda kv: (thu_tu.get(kv[0], 10 ** 9), kv[0]))


def xuat_excel_hoan_tat_ctbt(con, file_ra, ds=None, ten_du_an: str = '') -> int:
    """Danh sách hộ hoàn tất công tác bồi thường theo từng đợt -> .xlsx (CHỈ Excel). Trả số hộ."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, Side
    from .tien import KHONG
    nhom = ds_hoan_tat(con, ds)
    scan = dem_theo_ho(con)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Hoàn tất CTBT'
    cot = ['STT', 'Mã hộ', 'Họ và tên', 'Địa chỉ', 'Quyết định phê duyệt', 'Tổng phê duyệt (đ)', 'Đã nhận (đ)', 'Ngày bàn giao',
           'HS đính kèm (file)']
    rong = (6, 8, 28, 30, 30, 18, 18, 14, 12)
    ws.append(['DANH SÁCH HỘ HOÀN TẤT CÔNG TÁC BỒI THƯỜNG (đã có quyết định phê duyệt, đã bàn giao mặt bằng)'])
    ws.append([f'Dự án: {ten_du_an}' if ten_du_an else ''])
    ws.append(cot)
    vien = Side(style='thin', color='999999')
    k = Border(left=vien, right=vien, top=vien, bottom=vien)
    for c, w in enumerate(rong, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = w
        o = ws.cell(3, c)
        o.font, o.border = Font(bold=True), k
        o.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws['A1'].font = Font(bold=True, size=13)
    n = 0
    for dot, ds_ho in nhom:
        ws.append([f'{dot}: {len(ds_ho)} hộ'])
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(cot))
        ws.cell(r, 1).font = Font(bold=True)
        for stt, x in enumerate(ds_ho, start=1):
            ws.append([stt, x.ma_ho, x.ho_ten, x.dia_chi, '; '.join(f'{q["so_qd"]}' + (f' ({q["ngay_qd"]})' if q['ngay_qd'] else '')
                                                                   for q in x.qd),
                       float(x.tong_phe_duyet), float(x.da_nhan) if x.da_nhan != KHONG else None, x.ban_giao_ngay,
                       scan.get(x.ma_ho, 0)])
            r = ws.max_row
            for c in range(1, len(cot) + 1):
                ws.cell(r, c).border = k
                ws.cell(r, c).alignment = Alignment(vertical='center', wrap_text=True)
            for c in (6, 7):
                ws.cell(r, c).number_format = '#,##0'
            n += 1
    ws.append([])
    ws.append([f'Tổng cộng: {n} hộ hoàn tất'])
    ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.freeze_panes = 'A4'
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    _an_toan.luu_xlsx(wb, file_ra)
    return n
