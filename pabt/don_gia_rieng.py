"""Đơn giá riêng của dự án: quy ước giá tương đương nhập tay và đơn giá thẩm định giá (tài sản đặc biệt).

Cả hai lưu trong bảng quy_uoc của file dự án (không đổi cấu trúc CSDL):
- dòng của bộ đơn giá có id < ID_RIENG; "Áp bộ đơn giá vào dự án" thay các dòng này theo bộ mới;
- dòng riêng của dự án (nhập tay, sửa từ dòng của bộ, nhập từ chứng thư thẩm định giá) có id >= ID_RIENG và được giữ lại
  khi áp bộ đơn giá (don_gia.ap_vao_du_an);
- dòng đơn giá thẩm định có ten_tuong_duong = TD_THAM_DINH; can_cu ghi chứng thư, đơn vị thẩm định, quyết định phê duyệt.

Trong cửa sổ lập phương án, các dòng này nằm ở nhóm "Quy ước tương đương" (ô chọn nhanh mục 2, 3 và Chọn từ danh mục):
chọn một dòng thì thêm hạng mục mang tên thực tế, đơn giá / ĐVT theo dòng đã chọn, căn cứ ghi ở cột căn cứ giá.
"""
from __future__ import annotations
import re
from pathlib import Path

from . import csdl
from .lap_pa import LoiNhap, bo_dau
from .tien import D

ID_RIENG = 1000000
TD_THAM_DINH = 'Đơn giá thẩm định'
QD_TAI_SAN_DAC_BIET = 'Quyết định số 18/2026/QĐ-UBND ngày 04/3/2026'   # đơn giá nhà, công trình (bộ đơn giá, bảng van_ban)
COT = ('ten_thuc_te', 'ten_tuong_duong', 'dvt', 'don_gia', 'can_cu')


def la_tham_dinh(ten_tuong_duong: str) -> bool:
    return bo_dau(ten_tuong_duong or '').startswith(bo_dau(TD_THAM_DINH))


def doc(con) -> list:
    """Các dòng quy ước của dự án: dict(id, ten_thuc_te, ten_tuong_duong, dvt, don_gia, can_cu, rieng, tham_dinh)."""
    kq = []
    for r in con.execute('SELECT * FROM quy_uoc ORDER BY id'):
        d = {k: (r[k] if r[k] is not None else '') for k in ('id',) + COT}
        d['rieng'] = r['id'] >= ID_RIENG
        d['tham_dinh'] = la_tham_dinh(d['ten_tuong_duong'])
        kq.append(d)
    return kq


def chuan_gia(v) -> str:
    """'1.854.000' / '1854000' / 1854000 -> '1854000'; trống -> ''. Sai -> LoiNhap."""
    s = str(v if v is not None else '').strip().replace(' ', '')
    if not s:
        return ''
    s2 = re.sub(r'[.,](?=\d{3}(?:\D|$))', '', s).replace(',', '.') if re.fullmatch(r'[\d.,]+', s) else s
    try:
        g = D(s2)
    except (ValueError, ArithmeticError):
        raise LoiNhap(f'Đơn giá "{v}" không phải số.') from None
    if g < 0:
        raise LoiNhap(f'Đơn giá "{v}" âm.')
    g = g.normalize()
    return str(int(g)) if g == int(g) else format(g, 'f')


def _sach(d: dict) -> tuple:
    ten = ' '.join(str(d.get('ten_thuc_te') or '').split())
    td = ' '.join(str(d.get('ten_tuong_duong') or '').split())
    dvt = ' '.join(str(d.get('dvt') or '').split())
    cc = ' '.join(str(d.get('can_cu') or '').split())
    return ten, td, dvt, chuan_gia(d.get('don_gia')), cc


def luu(con, ds: list) -> dict:
    """Ghi lại toàn bộ bảng quy ước của dự án theo ds (các dict như doc(); dòng mới không có id).
    Dòng của bộ đơn giá giữ nguyên nội dung thì giữ id; dòng sửa / thêm thành dòng riêng của dự án (id >= ID_RIENG)."""
    cu = {r['id']: r for r in doc(con)}
    ra, loi = [], []
    for i, d in enumerate(ds, 1):
        try:
            ten, td, dvt, gia, cc = _sach(d)
        except LoiNhap as e:
            loi.append(f'Dòng {i}: {e}')
            continue
        if not ten and not td and not gia:
            continue                                    # dòng trống
        if not ten:
            loi.append(f'Dòng {i}: chưa có tên tài sản thực tế.')
        if not gia:
            loi.append(f'Dòng {i} ({ten or td}): chưa có đơn giá.')
        if not dvt:
            loi.append(f'Dòng {i} ({ten or td}): chưa có đơn vị tính.')
        ra.append([d.get('id'), ten, td, dvt, gia, cc])
    if loi:
        raise LoiNhap('Chưa lưu được:\n' + '\n'.join(loi[:20]) + ('\n…' if len(loi) > 20 else ''))
    tiep = max([ID_RIENG - 1] + [k for k in cu if k >= ID_RIENG]) + 1
    dem = dict(bo=0, rieng=0, moi=0)
    for x in ra:
        id_ = x[0]
        c = cu.get(id_)
        if c is not None and id_ < ID_RIENG:
            if tuple(x[1:]) == tuple(_sach(c)):
                dem['bo'] += 1
                continue                                # dòng của bộ đơn giá, không sửa
            x[0] = None                                 # sửa dòng của bộ: thành dòng riêng
        if x[0] is None or x[0] not in cu:
            x[0] = tiep
            tiep += 1
            dem['moi'] += 1
        else:
            dem['rieng'] += 1
    with con, csdl.mo_khoa_danh_muc(con):
        con.execute('DELETE FROM quy_uoc')
        con.executemany(f'INSERT INTO quy_uoc (id, {", ".join(COT)}) VALUES (?,?,?,?,?,?)', ra)
        xoa = len(set(cu) - {x[0] for x in ra})
        csdl.ghi_nhat_ky(con, 'Sửa đơn giá riêng của dự án (quy ước tương đương)',
                         f'{len(ra)} dòng: {dem["moi"]} dòng mới / sửa, {xoa} dòng bỏ')
    return dict(tong=len(ra), **dem)


def doc_rieng(con) -> list:
    """Các dòng riêng của dự án (để giữ lại khi áp bộ đơn giá)."""
    return [tuple(r) for r in con.execute(f'SELECT id, {", ".join(COT)} FROM quy_uoc WHERE id >= ?', (ID_RIENG,))]


def tra_rieng(con, rieng: list) -> None:
    """Ghi lại các dòng riêng sau khi bảng quy_uoc bị thay bằng bộ đơn giá (gọi trong `with con, csdl.mo_khoa_danh_muc`).
    Dòng của bộ trùng tên thực tế với dòng riêng (dòng của bộ người dùng đã sửa cho dự án) thì bỏ, dùng dòng riêng."""
    if not rieng:
        return
    ten = {bo_dau(r[1]) for r in rieng}
    bo = [r[0] for r in con.execute('SELECT id, ten_thuc_te FROM quy_uoc WHERE id < ?', (ID_RIENG,)) if bo_dau(r[1]) in ten]
    con.executemany('DELETE FROM quy_uoc WHERE id = ?', [(i,) for i in bo])
    con.executemany(f'INSERT OR REPLACE INTO quy_uoc (id, {", ".join(COT)}) VALUES (?,?,?,?,?,?)', rieng)


# ---------------------------------------------------------------- chứng thư / kết quả thẩm định giá
_RE_CHUNG_THU = re.compile(r'(?i)chứng\s+thư(?:\s+thẩm\s+định(?:\s+giá)?)?\s+số\s*:?\s*([\w./-]+[\w])')
_RE_DON_VI = re.compile(r'(?i)\b((?:công\s+ty|trung\s+tâm|doanh\s+nghiệp)\b[^,;:\n]{0,120}?thẩm\s+định\s+giá[^,;:\n]{0,80})')
_RE_NGAY = re.compile(r'(?i)ngày\s*(\d{1,2})\s*(?:/|-|tháng)\s*(\d{1,2})\s*(?:/|-|năm)\s*(\d{4})')


def thong_tin_chung_thu(dong: list) -> dict:
    """Số chứng thư, đơn vị thẩm định, ngày (từ các dòng đầu file); không thấy thì để trống cho người dùng gõ."""
    chu = '\n'.join(' '.join(' '.join(str(c) for c in r if c).split()) for r in dong[:120])
    so = don_vi = ngay = ''
    m = _RE_CHUNG_THU.search(chu)
    if m:
        so = m.group(1).strip('.,;')
        mn = _RE_NGAY.search(chu[m.end(): m.end() + 200])
        if mn:
            ngay = f'{int(mn.group(1)):02d}/{int(mn.group(2)):02d}/{mn.group(3)}'
    m = _RE_DON_VI.search(chu)
    if m:
        don_vi = ' '.join(m.group(1).split()).rstrip(' .')
    return dict(so_chung_thu=so, ngay=ngay, don_vi=don_vi)


def can_cu_tham_dinh(so_chung_thu: str = '', ngay: str = '', don_vi: str = '', qd_phe_duyet: str = '',
                     qd_ap_dung: str = QD_TAI_SAN_DAC_BIET) -> str:
    """Câu căn cứ ghi ở cột căn cứ giá của dòng phương án dùng đơn giá thẩm định."""
    ct = ' '.join(x for x in (f'Chứng thư thẩm định giá số {so_chung_thu}' if so_chung_thu else '',
                               f'ngày {ngay}' if ngay and so_chung_thu else '',
                               f'của {don_vi}' if don_vi else '') if x)
    ve = [x for x in (ct, f'phê duyệt tại {qd_phe_duyet}' if qd_phe_duyet else '',
                      f'tài sản đặc biệt theo {qd_ap_dung}' if qd_ap_dung else '') if x]
    return '; '.join(ve)


def doc_file_tham_dinh(file, dong: list | None = None) -> tuple:
    """File kết quả thẩm định giá (Excel / Word / PDF / CSV) -> ([nhap_don_gia.Muc], thông tin chứng thư, [câu cần xem]).
    Có bảng (Tên, ĐVT, Đơn giá) thì đọc theo cột; không có bảng thì tìm "<số> đồng/<ĐVT>" trong lời văn."""
    from . import nhap_don_gia as ndg
    if dong is None:
        dong = ndg.doc_bang(file)
    ds, xem = ndg.nhan_muc(dong), []
    if not ds:
        ds, xem = ndg.muc_tu_loi_van(dong)
    if not ds:
        raise LoiNhap(f'Không tìm thấy đơn giá trong file "{Path(file).name}": cần bảng có cột Tên tài sản, ĐVT, Đơn giá '
                      '(hoặc câu ghi "… <số tiền> đồng/<đơn vị>").')
    for m in ds:
        m.ten = ' '.join(m.ten.split())[:200]
    return ds, thong_tin_chung_thu(dong), xem


def them_tham_dinh(con, ds: list, can_cu: str, nhan: str = TD_THAM_DINH) -> dict:
    """Ghi các mục đơn giá thẩm định đã chọn vào quy ước của dự án (dòng riêng). Trùng tên + ĐVT với dòng thẩm định đã có
    thì cập nhật giá, căn cứ. ds: [nhap_don_gia.Muc] (chỉ lấy mục chon)."""
    chon = [m for m in ds if getattr(m, 'chon', True)]
    if not chon:
        raise LoiNhap('Chưa chọn dòng đơn giá nào.')
    cu = {}
    for r in doc(con):
        if r['rieng'] and r['tham_dinh']:
            cu[(bo_dau(r['ten_thuc_te']), bo_dau(r['dvt']))] = r['id']
    tiep = max([ID_RIENG - 1] + [r[0] for r in con.execute('SELECT id FROM quy_uoc WHERE id >= ?', (ID_RIENG,))]) + 1
    moi = cap_nhat = 0
    with con, csdl.mo_khoa_danh_muc(con):
        for m in chon:
            ten, dvt = ' '.join(m.ten.split()), ' '.join((m.dvt or '').split())
            if not ten or not dvt or not m.don_gia:
                raise LoiNhap(f'Dòng "{ten or "(không tên)"}" thiếu tên, ĐVT hoặc đơn giá.')
            k = (bo_dau(ten), bo_dau(dvt))
            if k in cu:
                con.execute('UPDATE quy_uoc SET don_gia = ?, can_cu = ?, ten_tuong_duong = ? WHERE id = ?',
                            (chuan_gia(m.don_gia), can_cu, nhan, cu[k]))
                cap_nhat += 1
            else:
                con.execute(f'INSERT INTO quy_uoc (id, {", ".join(COT)}) VALUES (?,?,?,?,?,?)',
                            (tiep, ten, nhan, dvt, chuan_gia(m.don_gia), can_cu))
                cu[k] = tiep
                tiep += 1
                moi += 1
        csdl.ghi_nhat_ky(con, 'Nhập đơn giá thẩm định', f'{moi} mục mới, {cap_nhat} mục cập nhật giá; {can_cu}')
    return dict(moi=moi, cap_nhat=cap_nhat)
