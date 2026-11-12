"""Mã tài sản, chính sách từ 0.9.69 (người dùng 12/10/2026): nhà, công trình TS1, TS2…; cây trồng CT1, CT2…; vật nuôi VN1, VN2…;
chính sách hỗ trợ CS1, CS2…; thưởng bàn giao mặt bằng TH1, TH2… (biểu thưởng không lưu mã: đánh theo thứ tự mức).

Mã cũ (bộ đơn giá đến 0.9.68, file PABT Excel): nhà TS1-TS139 (giữ nguyên), cây TS140-TS5649, vật nuôi VN01-VN17, hỗ trợ HT01-
HT39, các dòng HT / TH nhóm 4, 5 trong dm_taisan (trùng dm_hotro / bieu_thuong - bỏ), mã cập nhật từ file HTN### / TSN####.
`doi_ma(ma, nhom)` theo quy tắc; `chuyen_csdl(con)` chuyển một file (dự án / bộ đơn giá) - gọi khi nâng cấp CSDL v13 -> v14, sau
khi nhập file PABT Excel, khi dựng bộ đơn giá. Chuyển nhiều lần không đổi thêm (mã mới không khớp quy tắc cũ).
"""
from __future__ import annotations

import re


def la_vat_nuoi(phan_loai: str) -> bool:
    """Mục danh mục (dm_taisan.phan_loai) thuộc nhóm vật nuôi (QĐ 31/2025)."""
    return 'vật nuôi' in str(phan_loai or '').lower()


# mã cây trồng cũ TS140 = cây đầu tiên (nhà TS1-TS139): CT1 = TS140
CAY_TS_DAU = 140
_RE_HT = re.compile(r'^HT0*(\d+)$')
_RE_VN = re.compile(r'^VN0+(\d+)$')
_RE_TS = re.compile(r'^TS(\d+)$')
_RE_TH = re.compile(r'^TH0+(\d+)$')
NHOM_CAY = 3


def doi_ma(ma: str, nhom: int, vat_nuoi: bool = False) -> str:
    """Mã mới theo quy tắc, hoặc chính mã đó nếu không thuộc quy tắc (mã mới / mã người dùng tự đặt).
    nhom: 2 nhà, 3 cây (vật nuôi: vat_nuoi=True hoặc mã VN), 4 hỗ trợ, 5 thưởng; ct_khoan: mục 7 = vật nuôi."""
    ma = (ma or '').strip()
    m = _RE_HT.match(ma)
    if m:
        return f'CS{int(m.group(1))}'
    m = _RE_VN.match(ma)
    if m:
        return f'VN{int(m.group(1))}'
    m = _RE_TH.match(ma)
    if m:
        return f'TH{int(m.group(1))}'
    m = _RE_TS.match(ma)
    if m and nhom in (NHOM_CAY, 7) and not vat_nuoi and int(m.group(1)) >= CAY_TS_DAU:
        return f'CT{int(m.group(1)) - CAY_TS_DAU + 1}'
    return ma


def _tien_to_moi(nhom: int, vat_nuoi: bool) -> str:
    if nhom == 4:
        return 'CS'
    if nhom == 5:
        return 'TH'
    if nhom in (NHOM_CAY, 7):
        return 'VN' if vat_nuoi else 'CT'
    return 'TS'


def _so(ma: str, tien_to: str):
    m = re.fullmatch(re.escape(tien_to) + r'(\d+)', ma or '')
    return int(m.group(1)) if m else None


def bang_doi(con) -> dict:
    """{(bảng, mã cũ): mã mới} cho dm_taisan / dm_hotro của file: theo quy tắc; mã ngoài quy tắc dạng cũ (HTN### / TSN####) cấp
    số tiếp theo của tiền tố mới - không trùng mã có sẵn."""
    doi = {}
    da_co = {}                                       # tiền tố -> số lớn nhất đã dùng
    ds_ts = [(r[0], int(r[1] or 0), r[2]) for r in con.execute('SELECT ma, nhom, phan_loai FROM dm_taisan ORDER BY rowid')]
    ds_ht = [r[0] for r in con.execute('SELECT ma FROM dm_hotro ORDER BY rowid')]
    cho = []                                         # (bảng, mã cũ, tiền tố) chờ cấp số
    for bang, ds in (('dm_hotro', [(ma, 4, '') for ma in ds_ht]), ('dm_taisan', ds_ts)):
        for ma, nhom, pl in ds:
            vn = nhom == NHOM_CAY and (str(ma).upper().startswith('VN') or la_vat_nuoi(pl))
            moi = doi_ma(ma, nhom, vn)
            tt = _tien_to_moi(nhom, vn)
            if moi == ma and re.fullmatch(r'(HTN|TSN)\d+', ma or ''):
                cho.append((bang, ma, tt))
                continue
            doi[(bang, ma)] = moi
            n = _so(moi, tt)
            if n is not None:
                da_co[tt] = max(da_co.get(tt, 0), n)
    for bang, ma, tt in cho:
        da_co[tt] = da_co.get(tt, 0) + 1
        doi[(bang, ma)] = f'{tt}{da_co[tt]}'
    return doi


def chuyen_csdl(con) -> dict:
    """Chuyển mã một file sang mã 0.9.69 (trong một giao dịch, mở khóa danh mục). Bỏ các dòng nhóm 4 / 5 của dm_taisan (trùng
    chính sách hỗ trợ / biểu thưởng). Trả {'doi': số mã đổi, 'bo': số dòng bỏ}."""
    from contextlib import nullcontext
    from . import csdl
    co_khoa = con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'khoa_dm'").fetchone()
    with csdl.giao_dich(con), (csdl.mo_khoa_danh_muc(con) if co_khoa else nullcontext()):
        bo = con.execute('DELETE FROM dm_taisan WHERE nhom IN (4, 5)').rowcount
        doi = {k: v for k, v in bang_doi(con).items() if k[1] != v}
        theo_bang = {}
        for (bang, cu), moi in doi.items():
            theo_bang.setdefault(bang, {})[cu] = moi
        for bang, m in theo_bang.items():
            # hai bước qua mã tạm: tránh trùng khóa chính khi mã mới của dòng này là mã cũ của dòng khác
            for i, cu in enumerate(m):
                con.execute(f'UPDATE {bang} SET ma = ? WHERE ma = ?', (f'__doi_{i}', cu))
            for i, (cu, moi) in enumerate(m.items()):
                con.execute(f'UPDATE {bang} SET ma = ? WHERE ma = ?', (moi, f'__doi_{i}'))
        # dòng phương án: theo bảng đổi của danh mục; mã không còn trong danh mục thì theo quy tắc + mục của dòng
        dm = {**theo_bang.get('dm_taisan', {}), **theo_bang.get('dm_hotro', {})}
        bang_ct = {r[1] for r in con.execute('PRAGMA table_info(ct_khoan)')}
        if bang_ct:
            for rid, muc, ma, ma_td in con.execute(
                    'SELECT rowid, muc, ma, ' + ('ma_tuong_duong' if 'ma_tuong_duong' in bang_ct else "''") +
                    ' FROM ct_khoan').fetchall():
                moi = dm.get(ma) or doi_ma(ma, 4 if muc == 4 else int(muc or 0), muc == 7)
                moi_td = dm.get(ma_td) or doi_ma(ma_td, 4 if muc == 4 else int(muc or 0), muc == 7) if ma_td else ma_td
                if moi != ma or moi_td != ma_td:
                    if 'ma_tuong_duong' in bang_ct:
                        con.execute('UPDATE ct_khoan SET ma = ?, ma_tuong_duong = ? WHERE rowid = ?', (moi, moi_td, rid))
                    else:
                        con.execute('UPDATE ct_khoan SET ma = ? WHERE rowid = ?', (moi, rid))
    return {'doi': len(doi), 'bo': bo}


def ma_tiep(con, bang: str, tien_to: str, da_cap: dict | None = None) -> str:
    """Mã mới tiếp theo của tiền tố (TS / CT / VN / CS) trong bảng - thêm mục bộ đơn giá (cập nhật từ file, Sửa bộ đơn giá).
    da_cap: {tiền tố: số cuối} giữ giữa các lần gọi trong cùng giao dịch."""
    if da_cap is not None and tien_to in da_cap:
        da_cap[tien_to] += 1
        return f'{tien_to}{da_cap[tien_to]}'
    n = 0
    for (ma,) in con.execute(f'SELECT ma FROM {bang} WHERE ma LIKE ?', (tien_to + '%',)):
        k = _so(ma, tien_to)
        if k is not None:
            n = max(n, k)
    if da_cap is not None:
        da_cap[tien_to] = n + 1
    return f'{tien_to}{n + 1}'


def tien_to(nhom: int, vat_nuoi: bool = False) -> str:
    """Tiền tố mã mới của nhóm: 2 TS, 3 CT (vật nuôi VN), 4 CS, 5 TH."""
    return _tien_to_moi(nhom, vat_nuoi)


def ma_thuong(i: int) -> str:
    """Mã hiển thị của mức thưởng thứ i (1 = mức thấp nhất)."""
    return f'TH{i}'
