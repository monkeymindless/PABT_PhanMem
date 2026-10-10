"""Theo dõi phê duyệt, chi trả, bàn giao mặt bằng (từ 0.9.12, CSDL v10).

- Một quyết định phê duyệt (tổng, hoặc bổ sung) gồm nhiều hộ: bảng `quyet_dinh`; mỗi hộ trong quyết định một dòng `qd_ho`
  (số tiền phê duyệt của hộ trong quyết định, chia theo đất / tài sản / cây / hỗ trợ / thưởng, phương án chi tiết số, quyết
  định chi tiết số, chi trả theo từng quyết định: đã nhận, ngày, số tiền, biên lai / biên bản, lý do chưa nhận).
- Một hộ có thể có nhiều quyết định (phê duyệt bổ sung): tổng phê duyệt = cộng các quyết định; theo dõi nhận tiền từng quyết định.
- Bàn giao mặt bằng theo hộ (bảng ho: da_ban_giao, ban_giao_ngay, ly_do_ban_giao, bien_ban_ban_giao).
- Các cột tóm tắt trên bảng ho (da_phe_duyet, qd_so, qd_ngay, qd_so_tien, qd_file, da_chi_tra, chi_tra_ngay, chi_tra_so_tien)
  được tính lại từ qd_ho sau mỗi thay đổi (dong_bo_ho) để bộ lọc, kiểm tra lỗi, báo cáo cũ dùng tiếp.

Không phụ thuộc Qt.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import csdl
from .lap_pa import LoiNhap, bo_dau
from .quan_ly import chuan_ngay
from .tien import D, KHONG, chuoi, doc_so_vn, vn

TIEN_QD = ('so_tien', 'tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'tien_thuong', 'chi_tra_so_tien')
NGAY_QD = ('ngay_pa', 'qd_ct_ngay', 'chi_tra_ngay')
TRUONG_QD_HO = ('so_tien', 'tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'tien_thuong', 'so_pa', 'ngay_pa', 'qd_ct_so',
                'qd_ct_ngay', 'da_chi_tra', 'chi_tra_ngay', 'chi_tra_so_tien', 'chung_tu', 'ly_do_chua_nhan', 'ghi_chu')
TEN_TRUONG = dict(so_tien='Số tiền phê duyệt', tien_dat='Tiền đất', tien_tai_san='Tiền nhà, công trình, tài sản',
                  tien_cay='Tiền cây trồng', tien_ho_tro='Các chính sách hỗ trợ', tien_thuong='Thưởng bàn giao',
                  so_pa='Phương án chi tiết số', ngay_pa='Ngày phương án', qd_ct_so='Quyết định chi tiết số',
                  qd_ct_ngay='Ngày ban hành QĐ chi tiết', da_chi_tra='Đã nhận tiền', chi_tra_ngay='Ngày nhận tiền',
                  chi_tra_so_tien='Số tiền đã nhận', chung_tu='Biên lai / biên bản chi trả', ly_do_chua_nhan='Lý do chưa nhận',
                  ghi_chu='Ghi chú')
TRUONG_BAN_GIAO = ('da_ban_giao', 'ban_giao_ngay', 'ly_do_ban_giao', 'bien_ban_ban_giao')


def _tien(v) -> str:
    s = str(v if v is not None else '').strip()
    if not s:
        return ''
    try:
        return chuoi(doc_so_vn(s))                  # trước đây '1.070,5' -> 10.705 (đổi phẩy thành chấm rồi bỏ mọi dấu chấm)
    except (ValueError, ArithmeticError) as e:
        raise LoiNhap(f'Số tiền "{s}" không đúng.') from e


def _so(v):
    s = str(v or '').strip()
    return D(s) if s else None


def _chuan(k: str, v):
    if k == 'da_chi_tra' or k == 'da_ban_giao':
        return 1 if v else 0
    if k in TIEN_QD:
        return _tien(v)
    if k in NGAY_QD or k == 'ban_giao_ngay':
        return chuan_ngay(v)
    if k in ('ly_do_chua_nhan', 'ghi_chu', 'ly_do_ban_giao'):
        return str(v or '').strip()
    return ' '.join(str(v or '').split())


# ---------------------------------------------------------------- quyết định
@dataclass
class QuyetDinh:
    id: int
    so: str
    ngay: str = ''
    trich_yeu: str = ''
    tong_tien: str = ''
    file: str = ''
    ghi_chu: str = ''
    so_ho: int = 0
    tong_ho: object = KHONG          # cộng số tiền các hộ
    so_ho_da_nhan: int = 0
    da_chi: object = KHONG

    @property
    def nhan(self) -> str:
        """'Quyết định số 1234/QĐ-UBND ngày 05/10/2026 - 45 hộ'."""
        return f'{self.so or "(chưa có số)"}' + (f' ngày {self.ngay}' if self.ngay else '') + f' - {self.so_ho} hộ'


def ds_quyet_dinh(con) -> list:
    """Các quyết định, mới nhất trước (theo ngày), kèm số hộ, tổng tiền, số hộ đã nhận tiền."""
    dem = {r[0]: r for r in con.execute(
        '''SELECT qd_id, COUNT(*), SUM(CAST(NULLIF(so_tien, '') AS REAL)), SUM(da_chi_tra),
                  SUM(CASE WHEN da_chi_tra = 1 THEN CAST(NULLIF(chi_tra_so_tien, '') AS REAL) ELSE 0 END)
           FROM qd_ho GROUP BY qd_id''')}
    tien = {}
    for r in con.execute("SELECT qd_id, so_tien, da_chi_tra, chi_tra_so_tien FROM qd_ho"):
        t = tien.setdefault(r[0], [KHONG, KHONG])
        t[0] += _so(r[1]) or KHONG
        if r[2]:
            t[1] += _so(r[3]) or _so(r[1]) or KHONG
    kq = []
    for r in con.execute('SELECT * FROM quyet_dinh'):
        d = dem.get(r['id'])
        t = tien.get(r['id'], [KHONG, KHONG])
        kq.append(QuyetDinh(r['id'], r['so'], r['ngay'], r['trich_yeu'], r['tong_tien'], r['file'], r['ghi_chu'],
                            d[1] if d else 0, t[0], (d[3] or 0) if d else 0, t[1]))

    def khoa(q):
        try:
            n = datetime.strptime(q.ngay, '%d/%m/%Y')
        except ValueError:
            n = datetime.min
        return (n, q.id)
    return sorted(kq, key=khoa, reverse=True)


def lay_qd(con, qd_id: int) -> QuyetDinh:
    for q in ds_quyet_dinh(con):
        if q.id == qd_id:
            return q
    raise LoiNhap('Quyết định không còn trong dự án.')


def tim_qd(con, so: str, ngay: str = ''):
    """id quyết định có cùng số (không phân biệt hoa thường, dấu cách) - và cùng ngày nếu cả hai có ngày; None nếu chưa có."""
    k = _khoa_so(so)
    if not k:
        return None
    for r in con.execute('SELECT id, so, ngay FROM quyet_dinh'):
        if _khoa_so(r['so']) == k and (not ngay or not r['ngay'] or r['ngay'] == chuan_ngay(ngay)):
            return r['id']
    return None


def _khoa_so(so: str) -> str:
    return re.sub(r'\s+', '', bo_dau(so or ''))


def luu_qd(con, qd_id, so: str, ngay: str = '', trich_yeu: str = '', tong_tien='', file: str = '', ghi_chu: str = '') -> int:
    """Thêm (qd_id None) hoặc sửa quyết định. Trả id."""
    so = ' '.join(str(so or '').split())
    if not so:
        raise LoiNhap('Nhập số quyết định (ví dụ 1234/QĐ-UBND).')
    ngay = chuan_ngay(ngay)
    trung = tim_qd(con, so, ngay)
    if trung is not None and trung != qd_id:
        raise LoiNhap(f'Đã có quyết định số {so}' + (f' ngày {ngay}' if ngay else '') + '.')
    gt = (so, ngay, str(trich_yeu or '').strip(), _tien(tong_tien), str(file or ''), str(ghi_chu or '').strip())
    with csdl.giao_dich(con):
        if qd_id is None:
            qd_id = con.execute('INSERT INTO quyet_dinh (so, ngay, trich_yeu, tong_tien, file, ghi_chu) VALUES (?,?,?,?,?,?)',
                                gt).lastrowid
            csdl.ghi_nhat_ky(con, 'Thêm quyết định', f'{so} {ngay}')
        else:
            con.execute('UPDATE quyet_dinh SET so = ?, ngay = ?, trich_yeu = ?, tong_tien = ?, file = ?, ghi_chu = ? WHERE id = ?',
                        (*gt, qd_id))
            for m in ho_cua_qd(con, qd_id):
                dong_bo_ho(con, m)
            csdl.ghi_nhat_ky(con, 'Sửa quyết định', f'{so} {ngay}')
    return qd_id


def xoa_qd(con, qd_id: int) -> int:
    """Xóa quyết định và các dòng hộ của nó (hồ sơ hộ, phương án giữ nguyên). Trả số hộ bị bỏ ra."""
    ds = ho_cua_qd(con, qd_id)
    with csdl.giao_dich(con):
        so = con.execute('SELECT so FROM quyet_dinh WHERE id = ?', (qd_id,)).fetchone()
        con.execute('DELETE FROM qd_ho WHERE qd_id = ?', (qd_id,))
        con.execute('DELETE FROM quyet_dinh WHERE id = ?', (qd_id,))
        for m in ds:
            dong_bo_ho(con, m)
        csdl.ghi_nhat_ky(con, 'Xóa quyết định', f'{so[0] if so else qd_id}: {len(ds)} hộ')
    return len(ds)


def ho_cua_qd(con, qd_id: int) -> list:
    return [r[0] for r in con.execute(
        'SELECT q.ma_ho FROM qd_ho q JOIN ho h ON h.ma_ho = q.ma_ho WHERE q.qd_id = ? ORDER BY h.thu_tu, h.ma_ho', (qd_id,))]


# ---------------------------------------------------------------- hộ trong quyết định
def doc_qd_ho(con, ma_ho: int) -> list:
    """Các quyết định của hộ (cũ trước): dict gồm các trường qd_ho + so_qd, ngay_qd, trich_yeu, file_qd, qd_id."""
    kq = []
    for r in con.execute('''SELECT q.*, d.so AS so_qd, d.ngay AS ngay_qd, d.trich_yeu, d.file AS file_qd
                            FROM qd_ho q JOIN quyet_dinh d ON d.id = q.qd_id WHERE q.ma_ho = ?''', (ma_ho,)):
        kq.append(dict(r))

    def khoa(x):
        try:
            return (datetime.strptime(x['ngay_qd'], '%d/%m/%Y'), x['id'])
        except ValueError:
            return (datetime.min, x['id'])
    return sorted(kq, key=khoa)


def ghi_qd_ho(con, qd_id: int, ma_ho: int, gia_tri: dict, ghi_nhat_ky: bool = True) -> None:
    """Thêm hộ vào quyết định hoặc sửa dòng đã có: chỉ ghi các trường có trong gia_tri."""
    gt = {}
    for k, v in gia_tri.items():
        if k not in TRUONG_QD_HO:
            raise KeyError(k)
        gt[k] = _chuan(k, v)
    if gt.get('da_chi_tra') == 0:                    # bỏ đánh dấu đã nhận: xóa ngày, số tiền nhận
        gt.setdefault('chi_tra_ngay', '')
        gt.setdefault('chi_tra_so_tien', '')
    with csdl.giao_dich(con):
        moi = con.execute('INSERT OR IGNORE INTO qd_ho (qd_id, ma_ho) VALUES (?, ?)', (qd_id, ma_ho)).rowcount
        if moi and 'so_pa' not in gt:                   # hộ mới vào quyết định: lấy số / ngày PA chi tiết đã đánh ở đợt trình
            try:
                con.execute('''UPDATE qd_ho SET so_pa = (SELECT so_pa FROM ho WHERE ma_ho = ?),
                               ngay_pa = (SELECT ngay_pa FROM ho WHERE ma_ho = ?) WHERE qd_id = ? AND ma_ho = ?''',
                            (ma_ho, ma_ho, qd_id, ma_ho))
            except sqlite3.OperationalError:            # file phiên bản cũ chưa có cột (không xảy ra sau khi nâng cấp v11)
                pass
        if gt:
            con.execute(f'UPDATE qd_ho SET {", ".join(k + " = ?" for k in gt)} WHERE qd_id = ? AND ma_ho = ?',
                        (*gt.values(), qd_id, ma_ho))
        dong_bo_ho(con, ma_ho)
        if ghi_nhat_ky:
            csdl.ghi_nhat_ky(con, 'Quyết định - hộ', f'QĐ {qd_id}, hộ {ma_ho}: ' + ', '.join(f'{k}={v}' for k, v in gt.items())[:300])


def bo_ho_khoi_qd(con, qd_id: int, ma_ho: int) -> None:
    with csdl.giao_dich(con):
        con.execute('DELETE FROM qd_ho WHERE qd_id = ? AND ma_ho = ?', (qd_id, ma_ho))
        dong_bo_ho(con, ma_ho)
        csdl.ghi_nhat_ky(con, 'Bỏ hộ khỏi quyết định', f'QĐ {qd_id}, hộ {ma_ho}')


def them_ho_theo_pa(con, qd_id: int, ds_ma: list) -> int:
    """Thêm các hộ vào quyết định, tiền từng hạng mục theo phương án hiện tại: đọc phương án một lượt, một giao dịch."""
    from .nghiep_vu import BoiCanh, doc_tat_ca_phuong_an, tinh_pa
    bc = BoiCanh.tu(con)
    pas = doc_tat_ca_phuong_an(con, list(ds_ma))
    with csdl.giao_dich(con):
        for m in ds_ma:
            ct = _chi_tiet_kq(tinh_pa(pas[m], bc)) if m in pas else chi_tiet_tu_phuong_an(con, m, bc)
            ghi_qd_ho(con, qd_id, m, ct, ghi_nhat_ky=False)
        csdl.ghi_nhat_ky(con, 'Quyết định - thêm hộ', f'QĐ {qd_id}: {len(ds_ma)} hộ')
    return len(ds_ma)


def bo_cac_ho_khoi_qd(con, qd_id: int, ds_ma: list) -> int:
    with csdl.giao_dich(con):
        for m in ds_ma:
            con.execute('DELETE FROM qd_ho WHERE qd_id = ? AND ma_ho = ?', (qd_id, m))
            dong_bo_ho(con, m)
        csdl.ghi_nhat_ky(con, 'Bỏ hộ khỏi quyết định', f'QĐ {qd_id}: {len(ds_ma)} hộ')
    return len(ds_ma)


def chi_tiet_tu_phuong_an(con, ma_ho: int, bc=None) -> dict:
    """Tiền đất / tài sản / cây / hỗ trợ / thưởng / tổng theo phương án hiện tại của hộ (điền sẵn khi chưa có số liệu QĐ)."""
    from .nghiep_vu import tinh_ho
    return _chi_tiet_kq(tinh_ho(con, ma_ho, bc))


def _chi_tiet_kq(k) -> dict:
    return dict(so_tien=chuoi(k.tong), tien_dat=chuoi(k.muc[1]), tien_tai_san=chuoi(k.muc[2]), tien_cay=chuoi(k.muc[3]),
                tien_ho_tro=chuoi(k.muc[4]), tien_thuong=chuoi(k.muc[5]))


def ghi_chi_tra(con, ds: list, ngay: str = '', chung_tu: str = '', theo_qd: bool = True) -> int:
    """Ghi nhận đã nhận tiền cho các cặp (qd_id, ma_ho): số tiền nhận = số tiền phê duyệt (nếu chưa nhập). Trả số dòng."""
    n = 0
    with csdl.giao_dich(con):
        for qd_id, ma in ds:
            r = con.execute('SELECT so_tien, chi_tra_so_tien FROM qd_ho WHERE qd_id = ? AND ma_ho = ?', (qd_id, ma)).fetchone()
            if r is None:
                continue
            gt = dict(da_chi_tra=1, chi_tra_ngay=chuan_ngay(ngay), ly_do_chua_nhan='',
                      chi_tra_so_tien=r['chi_tra_so_tien'] or r['so_tien'])
            if chung_tu:
                gt['chung_tu'] = str(chung_tu)
            con.execute(f'UPDATE qd_ho SET {", ".join(k + " = ?" for k in gt)} WHERE qd_id = ? AND ma_ho = ?',
                        (*gt.values(), qd_id, ma))
            dong_bo_ho(con, ma)
            n += 1
        csdl.ghi_nhat_ky(con, 'Ghi nhận chi trả', f'{n} hộ - quyết định, ngày {ngay}')
    return n


def ghi_kieu_cu(con, ma_ho: int, x: dict) -> dict:
    """Trường phê duyệt / chi trả kiểu cũ (một quyết định / hộ: da_phe_duyet, qd_so, qd_ngay, qd_so_tien, qd_file, da_chi_tra,
    chi_tra_ngay, chi_tra_so_tien - đã chuẩn hóa) ghi vào quyết định của hộ: quyết định có số qd_so (tạo nếu chưa có), không ghi
    số thì quyết định mới nhất của hộ. Hộ chưa có quyết định nào và không ghi số: trả lại các trường để ghi thẳng vào bảng ho
    (như phiên bản cũ). Không mở giao dịch riêng."""
    if x.get('da_phe_duyet') == 0:
        con.execute('DELETE FROM qd_ho WHERE ma_ho = ?', (ma_ho,))
        dong_bo_ho(con, ma_ho)
        return {k: v for k, v in x.items() if k not in ('da_phe_duyet', 'qd_so', 'qd_ngay', 'qd_so_tien', 'qd_file')}
    co = doc_qd_ho(con, ma_ho)
    qd_id = None
    if x.get('qd_so'):
        qd_id = tim_qd(con, x['qd_so'], x.get('qd_ngay', ''))
        if qd_id is None:
            qd_id = con.execute('INSERT INTO quyet_dinh (so, ngay, file) VALUES (?,?,?)',
                                (x['qd_so'], x.get('qd_ngay', ''), x.get('qd_file', ''))).lastrowid
    elif co:
        qd_id = co[-1]['qd_id']
    if qd_id is None:
        return x
    if x.get('qd_ngay'):
        con.execute("UPDATE quyet_dinh SET ngay = ? WHERE id = ? AND ngay = ''", (x['qd_ngay'], qd_id))
    if x.get('qd_file'):
        con.execute('UPDATE quyet_dinh SET file = ? WHERE id = ?', (x['qd_file'], qd_id))
    con.execute('INSERT OR IGNORE INTO qd_ho (qd_id, ma_ho) VALUES (?, ?)', (qd_id, ma_ho))
    gt = {}
    if 'qd_so_tien' in x:
        gt['so_tien'] = x['qd_so_tien']
    for k in ('da_chi_tra', 'chi_tra_ngay', 'chi_tra_so_tien'):
        if k in x:
            gt[k] = x[k]
    if gt:
        con.execute(f'UPDATE qd_ho SET {", ".join(k + " = ?" for k in gt)} WHERE qd_id = ? AND ma_ho = ?',
                    (*gt.values(), qd_id, ma_ho))
    dong_bo_ho(con, ma_ho)
    return {}


def ghi_ban_giao(con, ds_ma_ho: list, gia_tri: dict) -> int:
    gt = {}
    for k, v in gia_tri.items():
        if k not in TRUONG_BAN_GIAO:
            raise KeyError(k)
        gt[k] = _chuan(k, v)
    if not gt or not ds_ma_ho:
        return 0
    if gt.get('da_ban_giao') == 1:
        gt.setdefault('ly_do_ban_giao', '')
    with csdl.giao_dich(con):
        for m in ds_ma_ho:
            con.execute(f'UPDATE ho SET {", ".join(k + " = ?" for k in gt)} WHERE ma_ho = ?', (*gt.values(), m))
        csdl.ghi_nhat_ky(con, 'Bàn giao mặt bằng', f'{len(ds_ma_ho)} hộ: ' + ', '.join(f'{k}={v}' for k, v in gt.items())[:300])
    return len(ds_ma_ho)


def dong_bo_ho(con, ma_ho: int) -> None:
    """Tính lại phần tóm tắt trên bảng ho từ các quyết định của hộ (không mở giao dịch riêng)."""
    ds = doc_qd_ho(con, ma_ho)
    if not ds:
        con.execute("""UPDATE ho SET da_phe_duyet = 0, qd_so = '', qd_ngay = '', qd_so_tien = '', qd_file = '', da_chi_tra = 0,
                       chi_tra_ngay = '', chi_tra_so_tien = '' WHERE ma_ho = ?""", (ma_ho,))
        return
    tong = sum((_so(x['so_tien']) or KHONG for x in ds), KHONG)
    nhan = [x for x in ds if x['da_chi_tra']]
    da_nhan = sum((_so(x['chi_tra_so_tien']) or _so(x['so_tien']) or KHONG for x in nhan), KHONG)
    ngay_nhan = sorted((x['chi_tra_ngay'] for x in nhan if x['chi_tra_ngay']), key=_khoa_ngay)
    con.execute('''UPDATE ho SET da_phe_duyet = 1, qd_so = ?, qd_ngay = ?, qd_so_tien = ?, qd_file = ?, da_chi_tra = ?,
                   chi_tra_ngay = ?, chi_tra_so_tien = ? WHERE ma_ho = ?''',
                ('; '.join(x['so_qd'] for x in ds), ds[-1]['ngay_qd'], chuoi(tong), ds[-1]['file_qd'],
                 1 if len(nhan) == len(ds) else 0, ngay_nhan[-1] if ngay_nhan else '', chuoi(da_nhan) if nhan else '', ma_ho))


def _khoa_ngay(s: str):
    try:
        return datetime.strptime(s, '%d/%m/%Y')
    except ValueError:
        return datetime.min


# ---------------------------------------------------------------- tổng hợp theo hộ
@dataclass
class TongHopHo:
    ma_ho: int
    thu_tu: int
    ho_ten: str
    dia_chi: str
    thua: list                      # [dict so_to, so_thua, dt_thu_hoi, loai_dat]
    qd: list                        # doc_qd_ho
    tong_pa: object = KHONG
    da_ban_giao: bool = False
    ban_giao_ngay: str = ''
    ly_do_ban_giao: str = ''
    bien_ban_ban_giao: str = ''
    theo_doi: str = ''
    muc_pa: dict = field(default_factory=dict)

    @property
    def tong_phe_duyet(self):
        return sum((_so(x['so_tien']) or KHONG for x in self.qd), KHONG)

    @property
    def da_nhan(self):
        return sum((_so(x['chi_tra_so_tien']) or _so(x['so_tien']) or KHONG for x in self.qd if x['da_chi_tra']), KHONG)

    @property
    def qd_chua_nhan(self) -> list:
        return [x for x in self.qd if not x['da_chi_tra']]

    @property
    def dt(self):
        return sum((_so(t['dt_thu_hoi']) or KHONG for t in self.thua), KHONG)

    @property
    def trang_thai(self) -> str:
        """Trạng thái ngắn gọn cho danh sách hộ."""
        if self.da_ban_giao:
            return 'Đã bàn giao MB'
        if self.qd and not self.qd_chua_nhan:
            return 'Đã nhận tiền, chưa bàn giao'
        if self.qd and len(self.qd_chua_nhan) < len(self.qd):
            return f'Đã nhận {len(self.qd) - len(self.qd_chua_nhan)}/{len(self.qd)} QĐ'
        if self.qd:
            return 'Đã phê duyệt' + (f' ({len(self.qd)} QĐ)' if len(self.qd) > 1 else '') + ', chưa nhận tiền'
        return 'Đã lập phương án' if self.tong_pa > 0 else 'Chưa lập phương án'


def tong_hop(con, ds_ma_ho: list | None = None, tinh_pa: bool = True) -> list:
    """[TongHopHo] theo thứ tự hộ: thửa, các quyết định, bàn giao, tổng phương án."""
    from .nghiep_vu import ket_qua_ho
    kqh = ket_qua_ho(con) if tinh_pa else {}            # dùng chung kết quả đã tính (danh sách hộ vừa tính xong)
    thua = {}
    for t in con.execute('SELECT ma_ho, so_to, so_thua, dt_thu_hoi, loai_dat FROM thua ORDER BY thu_tu, ma_thua'):
        thua.setdefault(t['ma_ho'], []).append(dict(t))
    qd = {}
    for r in con.execute('''SELECT q.*, d.so AS so_qd, d.ngay AS ngay_qd, d.trich_yeu, d.file AS file_qd
                            FROM qd_ho q JOIN quyet_dinh d ON d.id = q.qd_id'''):
        qd.setdefault(r['ma_ho'], []).append(dict(r))
    for v in qd.values():
        v.sort(key=lambda x: (_khoa_ngay(x['ngay_qd']), x['id']))
    chon = set(ds_ma_ho) if ds_ma_ho is not None else None
    kq = []
    for h in con.execute('SELECT * FROM ho ORDER BY thu_tu, ma_ho'):
        if chon is not None and h['ma_ho'] not in chon:
            continue
        x = TongHopHo(h['ma_ho'], h['thu_tu'], h['ho_ten'], h['dia_chi'], thua.get(h['ma_ho'], []), qd.get(h['ma_ho'], []),
                      da_ban_giao=bool(h['da_ban_giao']), ban_giao_ngay=h['ban_giao_ngay'], ly_do_ban_giao=h['ly_do_ban_giao'],
                      bien_ban_ban_giao=h['bien_ban_ban_giao'], theo_doi=h['theo_doi'])
        if tinh_pa and h['ma_ho'] in kqh:
            k = kqh[h['ma_ho']][0]
            x.tong_pa, x.muc_pa = k.tong, dict(k.muc)
        kq.append(x)
    return kq


# ---------------------------------------------------------------- lọc tiến độ
LOC_TIEN_DO = [
    ('', 'Tất cả hộ'), ('chua_pd', 'Chưa có quyết định phê duyệt'), ('da_pd', 'Đã có quyết định phê duyệt'),
    ('nhieu_qd', 'Có từ 2 quyết định trở lên'), ('chua_nhan', 'Còn quyết định chưa nhận tiền'),
    ('da_nhan_het', 'Đã nhận tiền đủ các quyết định'), ('chua_bg', 'Chưa bàn giao mặt bằng'),
    ('da_nhan_chua_bg', 'Đã nhận tiền, chưa bàn giao'), ('da_bg', 'Đã bàn giao mặt bằng'),
]


def hop_loc(x: TongHopHo, khoa: str, ds_qd: set | None = None) -> bool:
    """Hộ x có thỏa bộ lọc tiến độ khoa không. ds_qd: chỉ xét các quyết định này (rỗng / None: mọi quyết định)."""
    qd = [q for q in x.qd if not ds_qd or q['qd_id'] in ds_qd]
    if ds_qd and not qd:
        return False
    chua = [q for q in qd if not q['da_chi_tra']]
    return {
        '': True, 'chua_pd': not x.qd, 'da_pd': bool(qd), 'nhieu_qd': len(x.qd) >= 2,
        'chua_nhan': bool(chua), 'da_nhan_het': bool(qd) and not chua,
        'chua_bg': not x.da_ban_giao, 'da_nhan_chua_bg': bool(qd) and not chua and not x.da_ban_giao, 'da_bg': x.da_ban_giao,
    }.get(khoa, True)


# ---------------------------------------------------------------- nhập quyết định từ file
def nhap_tu_ket_qua(con, so: str, ngay: str, ds: list, file=None, trich_yeu: str = '', tong_tien='',
                    lay_chi_tiet_pa: bool = True) -> dict:
    """Tạo (hoặc dùng lại) quyết định số / ngày và ghi các hộ đã khớp (quan_ly.DongKhop có chon). Số tiền của hộ: theo file;
    file không có số tiền thì lấy tổng phương án. lay_chi_tiet_pa: điền tiền đất / tài sản / cây / hỗ trợ theo phương án
    khi số tiền phê duyệt bằng tổng phương án. Trả dict(qd_id, so_ho, moi)."""
    qd_id = tim_qd(con, so, ngay)
    moi = qd_id is None
    if moi:
        qd_id = luu_qd(con, None, so, ngay, trich_yeu, tong_tien, str(file or ''))
    from .nghiep_vu import BoiCanh, doc_tat_ca_phuong_an, tinh_pa
    bc = BoiCanh.tu(con) if lay_chi_tiet_pa else None
    # phương án các hộ cần điền chi tiết: đọc một lượt (3 câu truy vấn) thay vì 3 câu mỗi hộ
    can = [d.ma_ho for d in ds if getattr(d, 'chon', True) and d.ma_ho is not None and not getattr(d, 'chi_tiet', None)]
    pas = doc_tat_ca_phuong_an(con, can) if lay_chi_tiet_pa and can else {}
    n = 0
    with csdl.giao_dich(con):                           # cả lô một giao dịch (trước đây mỗi hộ một lần ghi đĩa)
        for d in ds:
            if not getattr(d, 'chon', True) or d.ma_ho is None:
                continue
            tien = d.so_tien if d.so_tien is not None else d.tong_pa
            gt = {'so_tien': tien if tien is not None else ''}
            if getattr(d, 'chi_tiet', None):                  # tiền từng hạng mục đọc được trong bảng kèm quyết định
                gt.update({k: v for k, v in d.chi_tiet.items() if k in TIEN_QD})
            elif lay_chi_tiet_pa:
                ct = _chi_tiet_kq(tinh_pa(pas[d.ma_ho], bc)) if d.ma_ho in pas else chi_tiet_tu_phuong_an(con, d.ma_ho, bc)
                if tien is None or D(ct['so_tien']) == D(tien):
                    gt.update(ct)
            ghi_qd_ho(con, qd_id, d.ma_ho, gt, ghi_nhat_ky=False)
            n += 1
        csdl.ghi_nhat_ky(con, 'Nhập quyết định', f'{so} {ngay}: {n} hộ')
    return dict(qd_id=qd_id, so_ho=n, moi=moi)


# ---------------------------------------------------------------- xuất Excel
def _ghi_bang(ws, tieu_de: list, dong: list, dong_dau: int = 4, rong: list | None = None, gop: list | None = None) -> None:
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    vien = Side(style='thin', color='808080')
    khung = Border(left=vien, right=vien, top=vien, bottom=vien)
    for c, t in enumerate(tieu_de, start=1):
        o = ws.cell(dong_dau, c, t)
        o.font = Font(bold=True)
        o.fill = PatternFill('solid', fgColor='DDEBF7')
        o.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        o.border = khung
    for i, d in enumerate(dong, start=dong_dau + 1):
        for c, v in enumerate(d, start=1):
            o = ws.cell(i, c, v)
            o.border = khung
            o.alignment = Alignment(vertical='center', wrap_text=True)
            if isinstance(v, (int, float)):
                o.number_format = '#,##0' if float(v) == int(v) else '#,##0.0'
    from .in_an import _gop_o                       # gộp nhanh: mỗi hộ nhiều vùng gộp
    for (r1, c1, r2, c2) in gop or []:
        _gop_o(ws, r1 + dong_dau + 1, c1 + 1, r2 + dong_dau + 1, c2 + 1)
    for c, w in enumerate(rong or [], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(dong_dau + 1, 1)


def _so_excel(v):
    if v in (None, ''):
        return None
    v = D(v)
    return int(v) if v == v.to_integral_value() else float(v)


def xuat_excel(file, tieu_de_bang: str, tieu_de: list, dong: list, rong: list | None = None, gop: list | None = None,
               ten_du_an: str = '') -> Path:
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Tong hop'
    ws['A1'] = tieu_de_bang
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f'Dự án: {ten_du_an}' if ten_du_an else ''
    ws['A3'] = f'Lập lúc {datetime.now():%d/%m/%Y %H:%M}'
    _ghi_bang(ws, tieu_de, [[_so_excel(v) if isinstance(v, type(KHONG)) else v for v in d] for d in dong], 4, rong, gop)
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    p = Path(file)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(p)
    return p


def tien_vn(v) -> str:
    return vn(v) if v not in (None, '') and D(v) != 0 else ('0' if v not in (None, '') else '')
