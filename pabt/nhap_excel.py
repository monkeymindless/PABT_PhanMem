"""Nhập file PABT Excel (.xlsm) hiện tại vào một file dự án .pabt.

Đọc thẳng file (không cần mở Excel), theo TÊN tiêu đề cột chứ không theo vị trí cột,
kiểm tra mã trùng / dữ liệu mồ côi, rồi ghi tất cả trong một giao dịch.
"""
from __future__ import annotations
import re
from collections import Counter
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import openpyxl

from . import csdl
from .tien import D, chuoi, co_so, doc_so_vn


def chuan_hoa(s) -> str:
    """'Diện tích\\nthu hồi' -> 'dien tich thu hoi' (bỏ dấu, chữ thường, gộp khoảng trắng)."""
    s = unicodedata.normalize('NFD', str(s or '')).replace('đ', 'd').replace('Đ', 'D')
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return ' '.join(s.lower().split())


def _txt(v) -> str:
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if hasattr(v, 'strftime'):
        return v.strftime('%d/%m/%Y')
    return str(v).strip()


def _so_hoac_rong(v):
    """Ô số của file Excel (ô số hoặc ô chữ gõ kiểu Việt Nam '1.070' / '1.070,5' - tien.doc_so_vn) -> chuỗi lưu CSDL; trống /
    không phải số -> None."""
    if v is None or str(v).strip() == '':
        return None
    try:
        return chuoi(doc_so_vn(v))
    except ValueError:
        return None


def _so(v) -> str:
    r = _so_hoac_rong(v)
    return '0' if r is None else r


@dataclass
class BaoCaoNhap:
    file_excel: str = ''
    file_pabt: str = ''
    so_ho: int = 0
    so_thua: int = 0
    so_ho_co_pa: int = 0
    so_dong: dict = field(default_factory=dict)
    so_danh_muc: dict = field(default_factory=dict)
    loi: list = field(default_factory=list)          # lỗi chặn (không nhập)
    canh_bao: list = field(default_factory=list)     # điểm cần xem lại
    tong_excel: dict = field(default_factory=dict)   # mã hộ -> {1..5, 'tong'} theo THEO_DOI của Excel


class Bang:
    """Một sheet dạng bảng: dòng 1 là tiêu đề."""

    def __init__(self, ws):
        rows = ws.iter_rows(values_only=True)
        try:
            self.tieu_de = [chuan_hoa(h) for h in next(rows)]
        except StopIteration:
            self.tieu_de = []
        self.dong = [r for r in rows if r and any(v not in (None, '') for v in r)]

    def cot(self, *ten, bat_buoc=True):
        for t in ten:
            t = chuan_hoa(t)
            for i, h in enumerate(self.tieu_de):
                if h == t:
                    return i
            for i, h in enumerate(self.tieu_de):
                if h.startswith(t):
                    return i
        if bat_buoc:
            raise KeyError(f'không thấy cột {ten[0]!r}')
        return None

    def gia_tri(self, r, i):
        return r[i] if i is not None and i < len(r) else None


def _ten_dinh_danh(wb, ten):
    """Giá trị ô của tên định danh (DA_TEN...) -> (sheet, ô) hoặc None."""
    try:
        dn = wb.defined_names[ten]
    except KeyError:
        return None
    for sh, ref in dn.destinations:
        m = re.match(r'\$?([A-Z]+)\$?(\d+)', ref.split(':')[0])
        if m and sh in wb.sheetnames:
            return sh, m.group(1), int(m.group(2))
    return None


def _doc_o(wb, sh, cot, dong):
    for r in wb[sh].iter_rows(min_row=dong, max_row=dong, values_only=True):
        c = openpyxl.utils.column_index_from_string(cot)
        return r[c - 1] if c - 1 < len(r) else None
    return None


def nhap(file_excel, file_pabt) -> BaoCaoNhap:
    """Nhập file Excel -> file dự án. Có lỗi chặn thì không tạo file (xem BaoCaoNhap.loi)."""
    wb = openpyxl.load_workbook(str(file_excel), read_only=True, data_only=True)
    try:
        return _nhap(wb, file_excel, file_pabt)
    finally:
        wb.close()                       # nhả file Excel (Windows khóa file đang mở)


def _nhap(wb, file_excel, file_pabt) -> BaoCaoNhap:
    bc = BaoCaoNhap(file_excel=str(file_excel), file_pabt=str(file_pabt))
    can = ['DB_HO', 'DB_THUA', 'DB_DATCT', 'DB_TAISAN', 'DB_CAY', 'DB_HOTRO', 'DM_HOTRO', 'THAM_SO']
    thieu = [s for s in can if s not in wb.sheetnames]
    if thieu:
        bc.loi.append('File không phải PABT (thiếu sheet ' + ', '.join(thieu) + ').')
        return bc

    # ------------------------------------------------ đọc
    b_ho, b_thua = Bang(wb['DB_HO']), Bang(wb['DB_THUA'])
    ho = []
    c = {k: b_ho.cot(*v) for k, v in dict(ma=('MaHo',), ten=('HoTen',), cccd=('SoCCCD',), nc=('NgayCap',), noi=('NoiCap',),
                                           dc=('DiaChi',), dt=('SoDienThoai',), pl=('PhapLy',), tc=('TranhChap',),
                                           tdc=('TaiDinhCu',), gc=('GhiChu',), tt=('TrangThaiHoSo',)).items()}
    for r in b_ho.dong:
        ma = b_ho.gia_tri(r, c['ma'])
        if not co_so(ma):
            continue
        ho.append(dict(ma_ho=int(D(ma)), ho_ten=_txt(r[c['ten']]), so_cccd=_txt(r[c['cccd']]), ngay_cap=_txt(r[c['nc']]),
                       noi_cap=_txt(r[c['noi']]), dia_chi=_txt(r[c['dc']]), dien_thoai=_txt(r[c['dt']]),
                       phap_ly=_txt(r[c['pl']]), tranh_chap=_txt(r[c['tc']]), tai_dinh_cu=_txt(r[c['tdc']]),
                       ghi_chu=_txt(r[c['gc']]), trang_thai=_txt(r[c['tt']]) or 'Chưa lập phương án'))
    ma_ho = [h['ma_ho'] for h in ho]
    trung = sorted(m for m, n in Counter(ma_ho).items() if n > 1)
    if trung:
        bc.loi.append('Mã hộ bị trùng trong DB_HO: ' + ', '.join(map(str, trung)) + ' (chạy ĐÁNH LẠI MÃ HỘ trên file Excel rồi nhập lại).')

    thua = []
    c = {k: b_thua.cot(*v, bat_buoc=k != 'vt') for k, v in dict(ma=('MaThua',), ho=('MaHo',), to=('SoTo',), so=('SoThua',),
                                                                 ld=('LoaiDat',), dt=('DienTichThuHoi',), ng=('NguonGocDat',),
                                                                 vt=('ViTri',)).items()}
    for i, r in enumerate(b_thua.dong):
        if not co_so(b_thua.gia_tri(r, c['ma'])):
            continue
        thua.append(dict(ma_thua=int(D(r[c['ma']])), ma_ho=int(D(r[c['ho']])) if co_so(r[c['ho']]) else None,
                         so_to=_txt(r[c['to']]), so_thua=_txt(r[c['so']]), loai_dat=_txt(r[c['ld']]),
                         dt_thu_hoi=_so(r[c['dt']]), nguon_goc=_txt(r[c['ng']]),
                         vi_tri=' '.join(_txt(b_thua.gia_tri(r, c['vt'])).split()), thu_tu=i + 1))
    tap_ho = set(ma_ho)
    mo_coi = [t['ma_thua'] for t in thua if t['ma_ho'] not in tap_ho]
    if mo_coi:
        bc.loi.append('Thửa không thuộc hộ nào (mã thửa): ' + ', '.join(map(str, mo_coi[:20])))
    tap_thua = {t['ma_thua'] for t in thua}

    # mục 1
    b = Bang(wb['DB_DATCT'])
    c = {k: b.cot(v) for k, v in dict(ho='MaHo', thua='MaThua', ld='LoaiDat', nhom='NhomDat', dt='DienTichThuHoi', vt='ViTri',
                                      gia='GiaBangGia', k='HeSoK', tl='TyLe', tt='ThanhTien', gc='GhiChu').items()}
    ct_dat = []
    for i, r in enumerate(b.dong):
        if not co_so(r[c['ho']]):
            continue
        mt = int(D(r[c['thua']])) if co_so(r[c['thua']]) else None
        if mt is not None and mt not in tap_thua:
            bc.loi.append(f'DB_DATCT: dòng của hộ {_txt(r[c["ho"]])} trỏ tới mã thửa {mt} không có.')
        ct_dat.append(dict(ma_ho=int(D(r[c['ho']])), ma_thua=mt, thu_tu=i + 1, loai_dat=_txt(r[c['ld']]),
                           nhom_dat=_txt(r[c['nhom']]), dien_tich=_so(r[c['dt']]), vi_tri=_txt(r[c['vt']]),
                           gia_bang_gia=_so(r[c['gia']]), he_so_k=_so_hoac_rong(r[c['k']]) or '1',
                           ty_le=_so_hoac_rong(r[c['tl']]) or '1', ghi_chu=_txt(r[c['gc']]),
                           thanh_tien_excel=_so_hoac_rong(r[c['tt']])))
    # mục 2, 3, 4
    ct_khoan = []
    for muc, sh, cot_ma, cot_ten, cot_qc in ((2, 'DB_TAISAN', 'MaTS', 'TenTaiSan', 'QuyCach'), (3, 'DB_CAY', 'MaTS', 'TenTaiSan', 'QuyCach'),
                                             (4, 'DB_HOTRO', 'MaHoTro', 'TenKhoan', 'CanCu')):
        b = Bang(wb[sh])
        c = {k: b.cot(v) for k, v in dict(ho='MaHo', ma=cot_ma, ten=cot_ten, dvt='DVT', sl='SoLuong', dg='DonGia', tl='TyLe',
                                          tt='ThanhTien', qc=cot_qc, gc='GhiChu').items()}
        for i, r in enumerate(b.dong):
            if not co_so(r[c['ho']]):
                continue
            ct_khoan.append(dict(muc=muc, ma_ho=int(D(r[c['ho']])), thu_tu=i + 1, ma=_txt(r[c['ma']]), ten=_txt(r[c['ten']]),
                                 dvt=_txt(r[c['dvt']]), so_luong=_so(r[c['sl']]), don_gia=_so(r[c['dg']]),
                                 ty_le=_so_hoac_rong(r[c['tl']]) or '1', quy_cach=_txt(r[c['qc']]), ghi_chu=_txt(r[c['gc']]),
                                 thanh_tien_excel=_so_hoac_rong(r[c['tt']])))
    for d in ct_dat + ct_khoan:
        if d['ma_ho'] not in tap_ho:
            bc.loi.append(f'Dòng phương án (mục {d.get("muc", 1)}) của mã hộ {d["ma_ho"]} không có trong DB_HO.')

    # dự án
    da = dict(ten='', ten_day_du='', don_vi_cap_tren='', don_vi_lap='', cap_dia_ban='Phường', ten_dia_ban='',
              so_phuong_an='', nam=None, can_cu_dinh_kem='')
    if 'DB_DUAN' in wb.sheetnames:
        b = Bang(wb['DB_DUAN'])
        if b.dong:
            r = b.dong[0]
            g = lambda t: _txt(b.gia_tri(r, b.cot(t, bat_buoc=False)))
            da.update(ten=g('TenDuAn'), ten_day_du=g('TenDuAnDayDu'), don_vi_cap_tren=g('DonViCapTren'), don_vi_lap=g('DonViLap'),
                      ten_dia_ban=g('XaPhuong'), so_phuong_an=g('SoPhuongAn'), can_cu_dinh_kem=g('CanCuDinhKem'))
            nam = g('Nam')
            da['nam'] = int(D(nam)) if co_so(nam) else None
    for ten, khoa in (('DA_TEN', 'ten'), ('DA_CAP', 'cap_dia_ban'), ('DA_DIABAN', 'ten_dia_ban')):
        vt = _ten_dinh_danh(wb, ten)
        if vt:
            v = _txt(_doc_o(wb, *vt))
            if v:
                da[khoa] = ' '.join(v.split())
    if not da['ten_day_du']:
        da['ten_day_du'] = da['ten']

    # danh mục, tham số
    dm_ts = []
    if 'DG_NHANUOC' in wb.sheetnames:
        b = Bang(wb['DG_NHANUOC'])
        c = {k: b.cot(v) for k, v in dict(ma='Mã TS', pl='Phân loại', ten='Tên tài sản', dvt='ĐVT', dg='Đơn giá', gc='Ghi chú').items()}
        for r in b.dong:
            ma = _txt(r[c['ma']])
            if not ma:
                continue
            pl = _txt(r[c['pl']])
            nhom = int(pl[0]) if pl[:1].isdigit() else 0
            dm_ts.append((ma, nhom, pl, _txt(r[c['ten']]), _txt(r[c['dvt']]), _so_hoac_rong(r[c['dg']]), _txt(r[c['gc']])))
    b = Bang(wb['DM_HOTRO'])
    c = {k: b.cot(v) for k, v in dict(ma='MaHoTro', ten='TenKhoan', dvt='DVT', dg='DonGia', cc='CanCu', ct='CachTinh', tt='TrangThaiCanCu').items()}
    dm_ht = [(_txt(r[c['ma']]), _txt(r[c['ten']]), _txt(r[c['dvt']]), _so_hoac_rong(r[c['dg']]), _txt(r[c['cc']]),
              _txt(r[c['ct']]), _txt(r[c['tt']])) for r in b.dong if _txt(r[c['ma']])]
    dm_ld = []
    if 'DB_LOAIDAT' in wb.sheetnames:
        b = Bang(wb['DB_LOAIDAT'])
        c = {k: b.cot(v) for k, v in dict(ma='MaLoaiDat', ten='TenLoaiDat', nhom='NhomDat', cc='CanCu').items()}
        dm_ld = [(_txt(r[c['ma']]), _txt(r[c['ten']]), _txt(r[c['nhom']]), _txt(r[c['cc']])) for r in b.dong if _txt(r[c['ma']])]
    gia = []
    if 'GIA_DAT' in wb.sheetnames:
        b = Bang(wb['GIA_DAT'])
        if b.dong:
            c = {k: b.cot(v) for k, v in dict(xa='XaPhuong', ld='LoaiDat', vt='ViTri', td='TuyenDuongKhuVuc', g='GiaBangGia',
                                              k='HeSoK', cc='CanCu').items()}
            gia = [(_txt(r[c['xa']]), _txt(r[c['ld']]), _txt(r[c['vt']]), _txt(r[c['td']]), _so_hoac_rong(r[c['g']]),
                    _so_hoac_rong(r[c['k']]), _txt(r[c['cc']])) for r in b.dong]
    xa = []
    if 'DB_XA' in wb.sheetnames:
        b = Bang(wb['DB_XA'])
        c = {k: b.cot(v) for k, v in dict(ma='MaDonVi', ten='TenDonVi', loai='LoaiDonVi', cu='DonViCu', cc='CanCu', tt='TrangThai').items()}
        xa = [(int(D(r[c['ma']])), _txt(r[c['ten']]), _txt(r[c['loai']]), _txt(r[c['cu']]), _txt(r[c['cc']]), _txt(r[c['tt']]))
              for r in b.dong if co_so(r[c['ma']])]
    b = Bang(wb['THAM_SO'])
    c = {k: b.cot(v, bat_buoc=False) for k, v in dict(ma='MaThamSo', ten='TenThamSo', gt='GiaTri', dvt='DVT', cc='CanCu', tt='TrangThai').items()}
    ts = []
    for r in b.dong:
        ma = _txt(b.gia_tri(r, c['ma']))
        if not ma:
            continue
        v = b.gia_tri(r, c['gt'])
        ts.append((ma, _txt(b.gia_tri(r, c['ten'])), chuoi(D(v)) if isinstance(v, (int, float)) else _txt(v),
                   _txt(b.gia_tri(r, c['dvt'])), _txt(b.gia_tri(r, c['cc'])), _txt(b.gia_tri(r, c['tt']))))
    vb = []
    if 'CAN_CU' in wb.sheetnames:
        b = Bang(wb['CAN_CU'])
        c = {k: b.cot(v) for k, v in dict(vb='VanBan', cq='CoQuan', nd='NoiDungApDung', tt='TrangThai').items()}
        vb = [(_txt(r[c['vb']]), _txt(r[c['cq']]), _txt(r[c['nd']]), _txt(r[c['tt']])) for r in b.dong if _txt(r[c['vb']])]
    bieu, quy_uoc = [], []
    vt_tu, vt_muc = _ten_dinh_danh(wb, 'THUONG_TU'), _ten_dinh_danh(wb, 'THUONG_MUC')
    if vt_tu and vt_muc:
        sh = wb[vt_tu[0]]
        ct_, cm_ = (openpyxl.utils.column_index_from_string(vt_tu[1]) - 1, openpyxl.utils.column_index_from_string(vt_muc[1]) - 1)
        for r in sh.iter_rows(min_row=vt_tu[2], max_row=vt_tu[2] + 5, values_only=True):
            tu, muc = _so_hoac_rong(r[ct_]), _so_hoac_rong(r[cm_])
            if tu is not None and muc is not None:
                bieu.append((tu, muc))
    if 'QUY_UOC_TUONG_DUONG' in wb.sheetnames:
        for r in wb['QUY_UOC_TUONG_DUONG'].iter_rows(min_row=2, values_only=True):
            if r and co_so(r[0]) and _txt(r[1]):
                quy_uoc.append((_txt(r[1]), _txt(r[2]), _txt(r[3]), _so_hoac_rong(r[4]), _txt(r[5])))
    if not bieu:
        bc.canh_bao.append('Không đọc được biểu thưởng (tên THUONG_TU / THUONG_MUC): thưởng sẽ bằng 0.')

    # tổng từng hộ theo THEO_DOI của Excel (giá trị Excel tính lúc lưu file) để đối chiếu
    if 'THEO_DOI' in wb.sheetnames:
        hd = None
        trong = 0
        # đọc hết sheet (trước đây chỉ 400 dòng đầu: dự án > ~395 hộ thì các hộ sau không được đối chiếu với Excel)
        for i, r in enumerate(wb['THEO_DOI'].iter_rows(min_row=1, values_only=True), start=1):
            if hd is None and i > 400:
                break                                   # không có dòng tiêu đề (Mã hộ / Tổng cộng) trong 400 dòng đầu
            if hd is not None:
                if any(v is not None and str(v).strip() for v in r):
                    trong = 0
                else:
                    trong += 1
                    if trong >= 200:                    # hết dữ liệu (sheet định dạng sẵn tới cuối)
                        break
            if hd is None:
                ch = [chuan_hoa(x) for x in r]
                if 'ma ho' in ch and 'tong cong' in ch:
                    hd = {k: ch.index(k) for k in ('ma ho', '1. dat', '2. nha, ct', '3. cay trong', '4. ho tro', '5. thuong', 'tong cong')
                          if k in ch}
                continue
            m = r[hd['ma ho']] if hd['ma ho'] < len(r) else None
            if not co_so(m):
                continue
            g = lambda k: D(_so_hoac_rong(r[hd[k]])) if k in hd and _so_hoac_rong(r[hd[k]]) is not None else None
            bc.tong_excel[int(D(m))] = {1: g('1. dat'), 2: g('2. nha, ct'), 3: g('3. cay trong'), 4: g('4. ho tro'),
                                        5: g('5. thuong'), 'tong': g('tong cong')}

    # đối chiếu HS_KIEMKE (nguồn gốc) với DB_THUA
    if 'HS_KIEMKE' in wb.sheetnames:
        b = Bang(wb['HS_KIEMKE'])
        cm = b.cot('MaThua', bat_buoc=False)
        cto, cso, cdt, cvt = (b.cot('Tờ bản đồ', bat_buoc=False), b.cot('Thửa đất', bat_buoc=False),
                              b.cot('Diện tích thu hồi', bat_buoc=False), b.cot('Vị trí đất', bat_buoc=False))
        theo_ma = {t['ma_thua']: t for t in thua}
        n_kk = 0
        for r in b.dong:
            if cto is None or not _txt(b.gia_tri(r, cto)):
                continue
            n_kk += 1
            mt = b.gia_tri(r, cm)
            t = theo_ma.get(int(D(mt))) if co_so(mt) else None
            if t is None:
                bc.canh_bao.append(f'HS_KIEMKE: thửa {_txt(b.gia_tri(r, cso))} tờ {_txt(b.gia_tri(r, cto))} chưa có trong DB_THUA '
                                   '(chạy ĐỒNG BỘ trên file Excel).')
                continue
            dt_kk = _so_hoac_rong(b.gia_tri(r, cdt))
            if dt_kk is not None and D(dt_kk) != D(t['dt_thu_hoi']):
                bc.canh_bao.append(f'Thửa {t["so_thua"]} tờ {t["so_to"]}: DT HS_KIEMKE {D(dt_kk)} ≠ DB_THUA {D(t["dt_thu_hoi"])}.')
            vt_kk = ' '.join(_txt(b.gia_tri(r, cvt)).split())
            if vt_kk and not t['vi_tri']:
                t['vi_tri'] = vt_kk
        if n_kk != len(thua):
            bc.canh_bao.append(f'HS_KIEMKE có {n_kk} dòng thửa, DB_THUA có {len(thua)} thửa.')

    if bc.loi:
        return bc

    # tên tài sản, cây trồng viết hoa chữ đầu ('cây xoài' -> 'Cây xoài') - như bộ đơn giá tích hợp
    from .don_gia import viet_hoa_dau
    for d in ct_khoan:
        d['ten'] = viet_hoa_dau(d['ten'])
    dm_ts = [(r[0], r[1], r[2], viet_hoa_dau(r[3]), *r[4:]) for r in dm_ts]

    # ------------------------------------------------ ghi (một giao dịch)
    con = csdl.tao_moi(file_pabt)
    try:
        with con, csdl.mo_khoa_danh_muc(con):
            con.execute('''UPDATE du_an SET ten=?, ten_day_du=?, don_vi_cap_tren=?, don_vi_lap=?, cap_dia_ban=?, ten_dia_ban=?,
                           so_phuong_an=?, nam=?, can_cu_dinh_kem=?, nguon_nhap=?, ngay_nhap=? WHERE id=1''',
                        (da['ten'], da['ten_day_du'], da['don_vi_cap_tren'], da['don_vi_lap'], da['cap_dia_ban'], da['ten_dia_ban'],
                         da['so_phuong_an'], da['nam'], da['can_cu_dinh_kem'], Path(file_excel).name,
                         datetime.now().isoformat(timespec='seconds')))
            for i, h in enumerate(ho, start=1):
                con.execute('''INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd, ngay_cap, noi_cap, dia_chi, dien_thoai, phap_ly,
                               tranh_chap, tai_dinh_cu, ghi_chu, trang_thai) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (h['ma_ho'], i, h['ho_ten'], h['so_cccd'], h['ngay_cap'], h['noi_cap'], h['dia_chi'], h['dien_thoai'],
                             h['phap_ly'], h['tranh_chap'], h['tai_dinh_cu'], h['ghi_chu'], h['trang_thai']))
            con.executemany('''INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, thu_tu)
                               VALUES (:ma_thua,:ma_ho,:so_to,:so_thua,:loai_dat,:dt_thu_hoi,:nguon_goc,:vi_tri,:thu_tu)''', thua)
            con.executemany('''INSERT INTO ct_dat (ma_ho, ma_thua, thu_tu, loai_dat, nhom_dat, dien_tich, vi_tri, gia_bang_gia, he_so_k,
                               ty_le, ghi_chu, thanh_tien_excel) VALUES (:ma_ho,:ma_thua,:thu_tu,:loai_dat,:nhom_dat,:dien_tich,
                               :vi_tri,:gia_bang_gia,:he_so_k,:ty_le,:ghi_chu,:thanh_tien_excel)''', ct_dat)
            con.executemany('''INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ma, ten, dvt, so_luong, don_gia, ty_le, quy_cach, ghi_chu,
                               thanh_tien_excel) VALUES (:muc,:ma_ho,:thu_tu,:ma,:ten,:dvt,:so_luong,:don_gia,:ty_le,:quy_cach,
                               :ghi_chu,:thanh_tien_excel)''', ct_khoan)
            con.executemany('INSERT OR REPLACE INTO dm_taisan VALUES (?,?,?,?,?,?,?)', dm_ts)
            con.executemany('INSERT OR REPLACE INTO dm_hotro VALUES (?,?,?,?,?,?,?)', dm_ht)
            con.executemany('INSERT OR REPLACE INTO dm_loaidat VALUES (?,?,?,?)', dm_ld)
            con.executemany('INSERT INTO gia_dat (xa_phuong, loai_dat, vi_tri, tuyen_duong, gia, he_so_k, can_cu) VALUES (?,?,?,?,?,?,?)', gia)
            con.executemany('INSERT OR REPLACE INTO dm_xa VALUES (?,?,?,?,?,?)', xa)
            con.executemany('INSERT OR REPLACE INTO tham_so VALUES (?,?,?,?,?,?)', ts)
            con.executemany('INSERT INTO van_ban (so_hieu, co_quan, noi_dung, trang_thai) VALUES (?,?,?,?)', vb)
            con.executemany('INSERT OR REPLACE INTO bieu_thuong VALUES (?,?)', bieu)
            con.executemany('INSERT INTO quy_uoc (ten_thuc_te, ten_tuong_duong, dvt, don_gia, can_cu) VALUES (?,?,?,?,?)', quy_uoc)
            csdl.chuyen_vat_nuoi(con)                   # dòng vật nuôi (mã nhóm vật nuôi) ở DB_CAY -> mục Vật nuôi riêng
            con.executemany('INSERT OR REPLACE INTO tong_excel VALUES (?,?,?,?,?,?,?)',
                            [(m, *(chuoi(v[k]) if v.get(k) is not None else None for k in (1, 2, 3, 4, 5, 'tong')))
                             for m, v in bc.tong_excel.items()])
            csdl.ghi_nhat_ky(con, 'Nhập từ Excel', f'{Path(file_excel).name}: {len(ho)} hộ, {len(thua)} thửa, '
                                                   f'{len(ct_dat) + len(ct_khoan)} dòng phương án')
    finally:
        con.close()
    bc.so_ho, bc.so_thua = len(ho), len(thua)
    bc.so_ho_co_pa = len({d['ma_ho'] for d in ct_dat + ct_khoan})
    bc.so_dong = {1: len(ct_dat), 2: sum(d['muc'] == 2 for d in ct_khoan), 3: sum(d['muc'] == 3 for d in ct_khoan),
                  4: sum(d['muc'] == 4 for d in ct_khoan)}           # 3: cây trồng gồm cả vật nuôi
    bc.so_danh_muc = {'tài sản, cây trồng': len(dm_ts), 'hỗ trợ': len(dm_ht), 'loại đất': len(dm_ld), 'giá đất': len(gia),
                      'xã, phường': len(xa), 'tham số': len(ts), 'văn bản căn cứ': len(vb), 'biểu thưởng': len(bieu),
                      'quy ước tương đương': len(quy_uoc)}
    return bc
