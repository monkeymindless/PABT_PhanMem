"""Các chính sách hỗ trợ (mục 4) theo cách tính: tên chính sách ngắn theo câu chữ quy định, các ô nhập theo từng loại và chuỗi
"cách tính" in ra phương án (thay ĐVT / số lượng / đơn giá / tỷ lệ), căn cứ ghi ở cột Ghi chú.

  - Ổn định đời sống (CS1-06, 34, 35): số nhân khẩu × số kg gạo × số tháng × giá gạo × tỷ lệ
      -> "4 nhân khẩu x 30kg gạo x 6 tháng x 16.000 đồng x 50%"
  - Đào tạo, chuyển đổi nghề và tìm kiếm việc làm (CS9, CS10): mỗi thửa đất nông nghiệp một dòng: diện tích × đơn giá đất ×
    tỷ lệ (150% / 50%)
  - Thuê nhà ở, tạm cư chờ tái định cư / tự lo chỗ ở (CS17, 18, 23, 24): (1 hộ (4 nhân khẩu) × số tháng × mức hộ) + (số nhân khẩu
    tăng thêm × mức mỗi khẩu × số tháng), một dòng
  - Tái định cư: tình trạng của hộ (lap_pa.TAI_DINH_CU), không phải dòng tiền.
Không phụ thuộc Qt.
"""
from __future__ import annotations

import re

from .nghiep_vu import (MA_DAO_TAO, MA_ON_DINH, MA_TDC, MA_THEO_NK, NK_CO_BAN, NGUON_DM, DongKhoan,  # noqa: F401 - xuất lại
                        _muc_khau_vuot_tinh_khac, he_so, tap_ma_dao_tao, tap_ma_on_dinh, tap_ma_tdc, tap_ma_theo_nk)
from .tien import D, so_vn

# chính sách không có trong bộ đơn giá, người dùng nhập số tiền (tên theo câu chữ quy định)
CHINH_SACH_KHAC = ['Hỗ trợ học phí', 'Hỗ trợ y tế', 'Hỗ trợ khác']


def loai_theo_ten(ten: str) -> str:
    """Loại chính sách theo TÊN khoản hỗ trợ (bộ đơn giá tỉnh khác không dùng mã CSn của Đồng Nai): 'od' / 'dt' / 'tn' / 'tdc' / ''.
    So không dấu, không phân biệt hoa thường; thứ tự quan trọng ("tự lo chỗ ở" trước "tái định cư": hỗ trợ tự lo chỗ ở thay tái định cư)."""
    from .lap_pa import bo_dau
    t = ' '.join(bo_dau(str(ten or '')).lower().split())
    if not t:
        return ''
    if 'on dinh doi song' in t:
        return 'od'
    if 'dao tao' in t and ('chuyen doi nghe' in t or 'viec lam' in t):
        return 'dt'
    if 'thue nha' in t or 'tam cu' in t or 'tu lo cho o' in t:
        return 'tn'
    if 'tai dinh cu' in t:
        return 'tdc'
    return ''


def loai(ma: str, ten: str = '') -> str:
    """'od' ổn định đời sống, 'dt' đào tạo chuyển đổi nghề, 'tn' thuê nhà / tự lo chỗ ở, 'tdc' tái định cư, '' khoản khác.
    Theo MÃ trước (tap_ma_*: mã chuẩn HỢP mã khai báo ở hồ sơ địa phương), thứ tự ổn định -> đào tạo -> theo nhân khẩu -> tái định cư:
    mã ổn định / theo nhân khẩu không bao giờ thành TĐC dù tên có chữ "tái định cư". Mã không thuộc nhóm nào mà có ten thì nhận theo
    tên (loai_theo_ten). Gọi không có ten: chỉ theo mã."""
    if ma in tap_ma_on_dinh():
        return 'od'
    if ma in tap_ma_dao_tao():
        return 'dt'
    if ma in tap_ma_theo_nk():
        return 'tn'
    if ma in tap_ma_tdc():
        return 'tdc'
    return loai_theo_ten(ten) if ten else ''


def ten_ngan(ten: str, ma: str = '') -> str:
    """Tên chính sách theo câu chữ quy định, bỏ phần điều kiện / mức: 'Hỗ trợ ổn định đời sống - Thu hồi dưới 30%…' ->
    'Hỗ trợ ổn định đời sống'; 'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm (hệ số 1,5)' -> '… việc làm'."""
    if ma in MA_THEO_NK:
        return 'Hỗ trợ tiền thuê nhà ở, tạm cư chờ tái định cư' if ma in ('CS23', 'CS24') else 'Hỗ trợ tự lo chỗ ở'
    t = ' '.join(str(ten or '').split())
    t = re.split(r'\s+-\s+|:\s', t)[0]
    t = re.sub(r'\s*\([^)]*\)\s*$', '', t)
    return t.strip()


def can_cu_ghi_chu(can_cu: str) -> str:
    """Căn cứ trong danh mục hỗ trợ -> câu ghi chú in ra: 'Hỗ trợ theo Điều 19 NĐ 88/2024/NĐ-CP; Điều 10 QĐ 42/2025/QĐ-UBND…'."""
    c = ' '.join(str(can_cu or '').split())
    if not c:
        return ''
    return c if c.lower().startswith('hỗ trợ theo') else f'Hỗ trợ theo {c[0].lower() + c[1:] if c[:5] in ("Khoản", "Điểm") else c}'


def phan_tram(v) -> str:
    return f'{so_vn(D(v) * 100)}%'


# ---------------------------------------------------------------- ổn định đời sống
def mac_dinh_on_dinh(bc, ten: str) -> dict:
    """Số tháng, tỷ lệ theo tên khoản danh mục ('…: 6 tháng…', 'mức 50%'); giá gạo, số kg theo tham số."""
    m = re.search(r'(\d+)\s*tháng', ten or '')
    t = re.search(r'mức\s*(\d+)\s*%', ten or '')
    return dict(thang=D(m.group(1)) if m else D(6), ty_le=D(t.group(1)) / 100 if t else D(1),
                gia_gao=bc.so_ts('GIA_GAO') or D(16450), kg=bc.so_ts('KG_GAO') or D(30))


def dong_on_dinh(m, nhan_khau, gia_gao, kg, thang, ty_le) -> DongKhoan:
    """Một dòng: SL = nhân khẩu, ĐG = kg × giá gạo × tháng (mỗi khẩu), tỷ lệ; cách tính in nguyên công thức."""
    nk, gia, kg, th, tl = D(nhan_khau), D(gia_gao), D(kg), D(thang), he_so(ty_le)
    return DongKhoan(muc=4, ma=m.ma, ten=ten_ngan(m.ten, m.ma), dvt='Nhân khẩu', so_luong=nk, don_gia=kg * gia * th, ty_le=tl,
                     nguon_gia=NGUON_DM, ghi_chu=can_cu_ghi_chu(m.can_cu),
                     cach_tinh=cach_tinh_on_dinh(nk, kg, th, gia, tl))


def cach_tinh_on_dinh(nk, kg, thang, gia, ty_le) -> str:
    return f'{so_vn(nk)} nhân khẩu x {so_vn(kg)}kg gạo x {so_vn(thang)} tháng x {so_vn(gia)} đồng x {phan_tram(ty_le)}'


def doi_nhan_khau_on_dinh(d: DongKhoan, nk) -> None:
    """Đổi số nhân khẩu của dòng ổn định đời sống (số lượng và chuỗi cách tính)."""
    d.so_luong = D(nk)
    if d.cach_tinh:
        d.cach_tinh = re.sub(r'^[\d.,]+\s*nhân khẩu', f'{so_vn(nk)} nhân khẩu', d.cach_tinh)


# ---------------------------------------------------------------- đào tạo, chuyển đổi nghề
def ds_thua_nn(bo, ma: str = '') -> list:
    """Các dòng đất nông nghiệp ở mục 1 của hộ đang soạn: dict(mo_ta, dien_tich, don_gia) - để tính hỗ trợ đào tạo theo thửa."""
    from .nghiep_vu import la_giao_khoan, mo_ta_thua
    kq = []
    for d in bo.pa.dat:
        if d.nhom_dat != 'Nông nghiệp':
            continue
        if ma and la_giao_khoan(d, bo.bc) != (ma == 'CS10'):     # 1.0.58: CS9 đất thường, CS10 đất giao khoán: không lẫn tỷ lệ
            continue
        t = bo.bc.thua.get(d.ma_thua) or {}
        mt = mo_ta_thua(t.get('so_to', ''), t.get('so_thua', ''), d.loai_dat, bo.bc.cap_dia_ban, bo.bc.ten_dia_ban,
                        d.vi_tri or t.get('vi_tri'))
        kq.append(dict(mo_ta=mt, dien_tich=d.dien_tich, don_gia=d.gia_bang_gia * d.he_so_k, dong=d))
    return kq


def ty_le_dao_tao(bc, ma: str):
    """Tỷ lệ hỗ trợ đào tạo theo giá đất NN: 150% (CS9) / 50% đất giao khoán (CS10)."""
    return bc.so_ts('HS_DAOTAO_2' if ma == 'CS10' else 'HS_DAOTAO') or (D('0.5') if ma == 'CS10' else D('1.5'))


def dong_dao_tao(m, mo_ta: str, dien_tich, don_gia, ty_le) -> DongKhoan:
    """Một dòng đào tạo, chuyển đổi nghề cho một thửa: 'Thửa đất số …' × m² × đơn giá đất × tỷ lệ."""
    return DongKhoan(muc=4, ma=m.ma, ten=mo_ta, dvt='m²', so_luong=D(dien_tich), don_gia=D(don_gia),
                     ty_le=he_so(ty_le), nguon_gia=NGUON_DM, ghi_chu=can_cu_ghi_chu(m.can_cu), quy_cach=ten_ngan(m.ten, m.ma))


# ---------------------------------------------------------------- thuê nhà, tự lo chỗ ở
def gia_thue_nha(bc, ma: str) -> tuple:
    """(mức hộ đến N khẩu / tháng, mức mỗi khẩu tăng thêm / tháng, N). Mã thuê nhà tỉnh khác (hồ sơ địa phương
    chinh_sach_ho_tro.ma_theo_nk): mức cơ bản = đơn giá danh mục, mức khẩu vượt = chinh_sach_ho_tro.muc_khau_vuot (1.0.31 - trước
    đây KeyError)."""
    co_ban_ma, them_ma = MA_THEO_NK.get(ma, (None, None))
    co_ban = (bc.so_ts(co_ban_ma) if co_ban_ma else D(0)) or D((bc.hotro.get(ma) or {}).get('don_gia') or 0)
    them = bc.so_ts(them_ma) if them_ma else _muc_khau_vuot_tinh_khac(ma)
    return co_ban, them, getattr(bc, 'nguong_nk', NK_CO_BAN) or NK_CO_BAN


def cach_tinh_thue_nha(nk, thang, co_ban, them, nguong) -> str:
    nk, n = int(D(nk or 0)), int(nguong)
    s = f'(1 hộ ({min(nk, n) if nk else n} nhân khẩu) * {so_vn(thang)} tháng * {so_vn(co_ban)} đồng)'
    if nk > n:
        s += f' + ({nk - n} nhân khẩu tăng thêm * {so_vn(them)} đồng * {so_vn(thang)} tháng)'
    return s


def dong_thue_nha(m, bc, nhan_khau, thang, co_ban=None, them=None) -> DongKhoan:
    cb, th, n = gia_thue_nha(bc, m.ma)
    cb = D(co_ban) if co_ban not in (None, '') else cb
    th = D(them) if them not in (None, '') else th
    nk = int(D(nhan_khau or 0))
    dg = cb + th * max(nk - n, 0)
    return DongKhoan(muc=4, ma=m.ma, ten=ten_ngan(m.ten, m.ma), dvt='Tháng', so_luong=D(thang), don_gia=dg, nguon_gia=NGUON_DM,
                     ghi_chu=can_cu_ghi_chu(m.can_cu), cach_tinh=cach_tinh_thue_nha(nk, thang, cb, th, n))


def tinh_lai_thue_nha(d: DongKhoan, bc, nhan_khau) -> None:
    """Đổi nhân khẩu: đơn giá tháng và cách tính của dòng thuê nhà / tự lo chỗ ở tính lại (giữ số tháng, mức đã nhập)."""
    cb, th, n = gia_thue_nha(bc, d.ma)
    m = re.search(r'\*\s*([\d.]+)\s*đồng\)', d.cach_tinh or '')
    if m:
        cb = D(m.group(1).replace('.', ''))
    m = re.search(r'tăng thêm\s*\*\s*([\d.]+)\s*đồng', d.cach_tinh or '')
    if m:
        th = D(m.group(1).replace('.', ''))
    nk = int(D(nhan_khau or 0))
    d.don_gia = cb + th * max(nk - n, 0)
    d.cach_tinh = cach_tinh_thue_nha(nk, d.so_luong, cb, th, n)

