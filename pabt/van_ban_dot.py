"""Văn bản, biên bản theo từng mục của đợt niêm yết (1.0.58, người dùng 04/11/2026: Thông báo niêm yết trong mục Niêm yết, Giấy mời trong mục
Lấy ý kiến, Giấy mời / Thông báo trong mục Đối thoại, các Biên bản…) và đọc KẾT QUẢ từ file scan / Word / Excel (dùng quan_ly.doc_van_ban:
PDF ảnh, ảnh qua Tesseract trên máy) để ghi ý kiến / kết luận đối thoại của từng hộ. Không Qt.

Bảng van_ban_dot tạo khi ghi lần đầu (CREATE IF NOT EXISTS: file cũ mở được, bản cũ bỏ qua bảng lạ). File đính kèm: giữ đường dẫn đầy đủ như HS đính kèm."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import csdl, du_thao
from .lap_pa import LoiNhap, bo_dau, kiem_quyen

BANG = '''CREATE TABLE IF NOT EXISTS van_ban_dot (
    id INTEGER PRIMARY KEY,
    dot_id INTEGER NOT NULL REFERENCES dot_du_thao(id) ON DELETE CASCADE,
    muc TEXT NOT NULL,
    loai TEXT NOT NULL DEFAULT '',
    so_hieu TEXT NOT NULL DEFAULT '',
    ngay TEXT NOT NULL DEFAULT '',
    noi_dung TEXT NOT NULL DEFAULT '',
    duong_dan TEXT NOT NULL DEFAULT '',
    luc TEXT NOT NULL DEFAULT ''
)'''
# theo thứ tự thẻ của màn hình Niêm yết
MUC = (('niem_yet', 'Niêm yết công khai'), ('y_kien', 'Lấy ý kiến nhân dân'), ('doi_thoai', 'Đối thoại & Tiếp thu'), ('tong_hop', 'Tổng hợp kết quả ý kiến'))
TEN_MUC = dict(MUC)
LOAI_THEO_MUC = {
    'niem_yet': ('Thông báo niêm yết công khai', 'Biên bản niêm yết công khai', 'Biên bản kết thúc niêm yết', 'Văn bản khác'),
    'y_kien': ('Giấy mời lấy ý kiến', 'Biên bản lấy ý kiến', 'Phiếu lấy ý kiến', 'Văn bản khác'),
    'doi_thoai': ('Giấy mời đối thoại', 'Thông báo đối thoại', 'Biên bản đối thoại', 'Văn bản khác'),
    'tong_hop': ('Báo cáo tổng hợp ý kiến', 'Biên bản tổng hợp ý kiến', 'Văn bản khác'),
}
DUOI_FILE = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp', '.doc', '.docx', '.xls', '.xlsx', '.xlsm')


def _co_bang(con) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'van_ban_dot'").fetchone())


def ds(con, dot_id: int, muc: str | None = None) -> list:
    """[sqlite3.Row] văn bản của đợt (của một mục nếu có muc), cũ trước."""
    if not _co_bang(con):
        return []
    if muc:
        return con.execute('SELECT * FROM van_ban_dot WHERE dot_id = ? AND muc = ? ORDER BY id', (dot_id, muc)).fetchall()
    return con.execute('SELECT * FROM van_ban_dot WHERE dot_id = ? ORDER BY id', (dot_id,)).fetchall()


def dem(con, dot_id: int) -> dict:
    if not _co_bang(con):
        return {}
    return {r[0]: r[1] for r in con.execute('SELECT muc, COUNT(*) FROM van_ban_dot WHERE dot_id = ? GROUP BY muc', (dot_id,))}


def _kiem_file(duong_dan: str) -> str:
    duong_dan = str(duong_dan or '').strip()
    if not duong_dan:
        return ''
    from .an_toan import LoiAnToan, kiem_tra_magic_bytes
    p = Path(duong_dan)
    if p.suffix.lower() not in DUOI_FILE:
        raise LoiNhap(f'File "{p.name}" không phải loại văn bản (PDF, ảnh, Word, Excel).')
    try:
        if p.is_file():
            kiem_tra_magic_bytes(p)
    except LoiAnToan as e:
        raise LoiNhap(str(e)) from None
    return str(p.resolve())


def luu(con, dot_id: int, muc: str, loai: str, so_hieu: str = '', ngay: str = '', noi_dung: str = '', duong_dan: str = '', id_: int | None = None) -> int:
    """Thêm (id_ None) / sửa một văn bản. ngay: dd/mm/yyyy hoặc trống. Trả id."""
    kiem_quyen(con, 'niem_yet')
    if muc not in TEN_MUC:
        raise LoiNhap('Mục không hợp lệ.')
    loai = ' '.join(str(loai or '').split())
    if not loai:
        raise LoiNhap('Chọn hoặc gõ loại văn bản.')
    n = du_thao.ngay_iso(du_thao.doc_ngay(ngay)) if str(ngay or '').strip() else ''
    f = _kiem_file(duong_dan)
    gt = (loai, ' '.join(str(so_hieu or '').split()), n, str(noi_dung or '').strip(), f)
    with csdl.giao_dich(con):
        con.execute(BANG)
        if id_ is None:
            id_ = con.execute('INSERT INTO van_ban_dot (dot_id, muc, loai, so_hieu, ngay, noi_dung, duong_dan, luc) VALUES (?,?,?,?,?,?,?,?)',
                              (dot_id, muc, *gt, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))).lastrowid
        else:
            con.execute('UPDATE van_ban_dot SET loai = ?, so_hieu = ?, ngay = ?, noi_dung = ?, duong_dan = ? WHERE id = ?', (*gt, id_))
        csdl.ghi_nhat_ky(con, f'{TEN_MUC[muc]}: lưu văn bản', f'Đợt {dot_id}: {loai} {gt[1]}')
    return id_


def xoa(con, id_: int) -> None:
    kiem_quyen(con, 'niem_yet')
    with csdl.giao_dich(con):
        con.execute('DELETE FROM van_ban_dot WHERE id = ?', (id_,))
        csdl.ghi_nhat_ky(con, 'Xóa văn bản của đợt niêm yết', str(id_))


def doc_thong_tin(file, bao_tien_do=None, cho=None) -> dict:
    """Đọc file văn bản (PDF ảnh, ảnh, Word, Excel): {'so_hieu', 'ngay', 'noi_dung'} để điền sẵn."""
    from .nhap_don_gia import phan_tich_van_ban
    from .quan_ly import doc_van_ban
    dong, _ = doc_van_ban(file, bao_tien_do, cho)
    vb = phan_tich_van_ban(dong, str(file).replace('\\', '/').rsplit('/', 1)[-1])
    return dict(so_hieu=vb.get('so_hieu', ''), ngay=vb.get('ngay', ''), noi_dung=vb.get('trich_yeu', ''))


# ---------------------------------------------------------------- đọc kết quả từng hộ
@dataclass
class KetQuaDong:
    ma_ho: int
    ho_ten: str
    loai: str               # dong_y / khong_dong_y / y_kien_khac / '' = không nhận ra
    noi_dung: str
    nguon: str              # dòng gốc để đối chiếu
    khop_theo: str
    chon: bool = True


def phan_loai(chu: str) -> str:
    k = bo_dau(chu)
    if re.search(r'khong (dong y|nhat tri|thong nhat)', k):
        return 'khong_dong_y'
    if re.search(r'y kien khac|kien nghi|de nghi|khieu nai|phan anh', k):
        return 'y_kien_khac'
    if re.search(r'dong y|nhat tri|thong nhat', k):
        return 'dong_y'
    return ''


def _ten_chuan(s) -> str:
    from .quan_ly import _ten_chuan as f
    return f(s)


def doc_ket_qua(con, dot_id: int, files, bao_tien_do=None, cho=None) -> dict:
    """Đọc các file kết quả, ghép dòng với hộ TRONG ĐỢT theo số CCCD rồi họ tên đủ chữ (tên trùng hai hộ: không ghép).
    {'dong': [KetQuaDong], 'tong_dong': số dòng file, 'scan': có nhận dạng chữ}. Không ghi gì."""
    from .quan_ly import doc_van_ban
    ho = [dict(r) for r in con.execute('''SELECT h.ma_ho, h.ho_ten, h.so_cccd FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho
                                          WHERE y.dot_id = ?''', (dot_id,))]
    theo_cccd = {re.sub(r'\D', '', h['so_cccd'] or ''): h for h in ho if len(re.sub(r'\D', '', h['so_cccd'] or '')) >= 9}
    theo_ten = {}
    for h in ho:
        k = _ten_chuan(h['ho_ten'])
        if len(k.split()) >= 2:
            theo_ten.setdefault(k, []).append(h)
    kq, da, tong, scan = [], set(), 0, False
    for f in ([files] if isinstance(files, (str, Path)) else files):
        dong, s = doc_van_ban(f, bao_tien_do, cho)
        scan = scan or bool(s)
        for r in dong:
            cac = [str(c) for c in r if str(c or '').strip()]
            if not cac:
                continue
            tong += 1
            chu = ' '.join(cac)
            so = re.findall(r'(?<!\d)\d{9}(?:\d{3})?(?!\d)', re.sub(r'(?<=\d)[ .\-](?=\d)', '', chu))
            h, cach = next((theo_cccd[x] for x in so if x in theo_cccd), None), 'CCCD'
            if h is None:
                k = f' {_ten_chuan(chu)} '
                trung = [(t, ds_h) for t, ds_h in theo_ten.items() if f' {t} ' in k]
                if trung:
                    t, ds_h = max(trung, key=lambda x: len(x[0]))        # "Nguyễn Văn An" trong "Nguyễn Văn An Bình": lấy tên dài nhất
                    h, cach = (ds_h[0], 'họ tên') if len(ds_h) == 1 else (None, '')
            if h is None or h['ma_ho'] in da:
                continue
            da.add(h['ma_ho'])
            bo_ten = [c for c in cac if _ten_chuan(c) != _ten_chuan(h['ho_ten']) and re.search(r'[^\W\d_]{2}', c)]
            nd = max(bo_ten, key=len, default='') if len(cac) > 1 else re.sub(re.escape(h['ho_ten'] or ''), '', chu, flags=re.I).strip(' .:-')
            loai = phan_loai(chu)
            # nhận ra được hộ nhưng không rõ kết quả: hiện để đối chiếu, không chọn sẵn
            kq.append(KetQuaDong(h['ma_ho'], h['ho_ten'], loai, nd, chu, cach, chon=bool(loai)))
    return dict(dong=kq, tong_dong=tong, scan=scan)


def ap_dung(con, dot_id: int, muc: str, dong: list, ngay: str = '', dia_diem: str = '') -> int:
    """Ghi các dòng chon: mục Đối thoại -> biên bản đối thoại (kết luận = nội dung đọc được); mục khác -> ý kiến của hộ. Trả số hộ."""
    kiem_quyen(con, 'niem_yet')
    n = 0
    with csdl.giao_dich(con):
        for d in dong:
            if not d.chon:
                continue
            if muc == 'doi_thoai':
                du_thao.ghi_doi_thoai(con, dot_id, d.ma_ho, ngay or datetime.now().strftime('%d/%m/%Y'), dia_diem, d.noi_dung)
            else:
                thay = dict(noi_dung=d.noi_dung)
                if d.loai:
                    thay['loai'] = d.loai
                du_thao.cap_nhat_y_kien(con, dot_id, d.ma_ho, **thay)
            n += 1
        csdl.ghi_nhat_ky(con, f'{TEN_MUC.get(muc, muc)}: nhập kết quả từ file', f'Đợt {dot_id}: {n} hộ')
    return n
