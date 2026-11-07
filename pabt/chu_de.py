"""Chủ đề giao diện (1.0.17, nền tảng giao diện 2.0 - người dùng 23/10/2026): MẬT ĐỘ BẢNG (Gọn / Chuẩn / Thoáng) và TƯƠNG PHẢN CAO theo Windows.
Không Qt (kiểm thử độc lập): chỉ giữ bảng cấu hình, phát hiện chế độ tương phản cao của Windows, đọc / ghi lựa chọn vào QSettings do nơi gọi đưa
vào. Áp dụng ở giao_dien (dat_mat_do, ap_dung).

Mật độ: chiều cao dòng + tiêu đề bảng dữ liệu (danh sách hộ, tổng hợp, tiến độ…). Gọn cho màn hình nhỏ (1366 x 768: thêm ~4 dòng nhìn thấy), Thoáng
cho màn hình lớn / người dùng cần vùng bấm to. Đổi có hiệu lực ngay.
Tương phản cao: Windows đang bật chủ đề tương phản cao (Cài đặt > Trợ năng) -> phần mềm dùng bảng màu hệ thống thay cho bảng màu riêng
(tránh chữ mất hút trên nền cố định). 'theo_windows' (mặc định) / 'bat' / 'tat'. Đổi cần mở lại phần mềm.
Biến môi trường PABT_MAT_DO / PABT_TUONG_PHAN_CAO (gon|chuan|thoang, bat|tat|theo_windows) ghi đè - dùng cho kiểm thử và hỗ trợ từ xa."""
from __future__ import annotations

import os
import sys

# tên -> (nhãn, cao dòng bảng, cao hàng tiêu đề cột) - 'chuan' = giá trị của 1.0.16
MAT_DO = {'gon': ('Gọn', 26, 30), 'chuan': ('Chuẩn', 30, 34), 'thoang': ('Thoáng', 36, 40)}
MAC_DINH_MAT_DO = 'chuan'
TUONG_PHAN = {'theo_windows': 'Theo Windows', 'bat': 'Luôn bật', 'tat': 'Tắt'}
MAC_DINH_TUONG_PHAN = 'theo_windows'
KHOA_MAT_DO = 'giao_dien/mat_do'
KHOA_TUONG_PHAN = 'giao_dien/tuong_phan_cao'
# 1.0.33 TÔNG NỀN bề mặt: tên -> (nhãn, nền cửa sổ, nền khung / ô, vạch ngăn, chữ chính, chữ phụ). giao_dien đổi các màu này trên bảng
# kiểu chung (dat_tong_nen); áp ngay, nhớ cho lần mở sau. 1.0.35 (người dùng 29/10/2026 chọn 5 phương án): mặc định PA1 Calm Executive
# Slate-Navy (menu trái sáng); PA2 Ấm áp, PA3 Xanh ngọc, PA4 Titan (menu tối), PA5 Tối chuyên gia; giữ Dịu mắt và Trắng tương phản.
TONG_NEN = {
    'sang': ('Sáng dịu Slate-Navy (mặc định)', '#F3F6FA', '#FFFFFF', '#D5DEE8', '#0F172A', '#475569'),
    'titan': ('Titan (menu trái than chì, bảng sáng)', '#F3F5F8', '#FFFFFF', '#D5DCE5', '#0F172A', '#475569'),
    'am': ('Ấm áp (giấy kem, làm việc lâu)', '#F4F1EA', '#FCFBF7', '#DDD6C8', '#1C1917', '#57534E'),
    'ngoc': ('Xanh ngọc (kiểu bảng tính tài chính)', '#F2F7F5', '#FFFFFF', '#CFE0D8', '#0F172A', '#3F5A52'),
    'toi': ('Tối chuyên gia (ban đêm)', '#0B1120', '#1E293B', '#334155', '#F1F5F9', '#CBD5E1'),
    'diu': ('Dịu mắt (Slate Studio)', '#E2E8F0', '#F8FAFC', '#94A3B8', '#0F172A', '#334155'),
    'trang': ('Trắng tương phản (máy chiếu / ngoài trời)', '#FFFFFF', '#FFFFFF', '#94A3B8', '#000000', '#1E293B'),
}
# 1.0.35: màu chính (nút đặc, tiêu đề bảng, chữ nhấn), dải banner 3 tầng và kiểu MENU TRÁI của từng tông. menu: nen / vien / chu (lệnh) /
# re (nền rê chuột) / chon_nen + chon_chu + vach_chon (lệnh đang chọn) / nhom (tiêu đề nhóm) / tat (lệnh tắt) / icon + icon_chon / cuon
_MENU_SANG = dict(nen='#E8EEF5', vien='#D5DEE8', chu='#334155', re='#DCE5F0', chon_nen='#DBEAFE', chon_chu='#1E3A5F',
                  vach_chon='#2563EB', nhom='#1E3A5F', tat='#6B7A90', icon='#475569', icon_chon='#1E3A5F', cuon='#B8C4D3', toi=False)
_MENU_TOI = dict(nen='#1E293B', vien='#334155', chu='#CBD5E1', re='rgba(59, 130, 246, 0.16)', chon_nen='#334155', chon_chu='#FFFFFF',
                 vach_chon='#60A5FA', nhom='#93C5FD', tat='#8391A7', icon='#CBD5E1', icon_chon='#FFFFFF', cuon='#475569', toi=True)
MAU_TONG = {
    'sang': dict(chinh='#1E3A5F', chinh_re='#152C48', banner=('#1E3A5F', '#24476F', '#2D5580'), menu=_MENU_SANG),
    'titan': dict(chinh='#26446E', chinh_re='#1B3354', banner=('#1E293B', '#26446E', '#2F527F'), menu=_MENU_TOI),
    'am': dict(chinh='#2A5582', chinh_re='#1F426A', banner=('#2A5582', '#2F5F8F', '#3A6B9B'),
               menu=dict(_MENU_SANG, nen='#ECE7DC', vien='#DDD6C8', chu='#3F3A33', re='#E3DCCD', chon_nen='#DCE6F2', chon_chu='#2A5582',
                         vach_chon='#2A5582', nhom='#2A5582', tat='#7D766B', icon='#57534E', icon_chon='#2A5582', cuon='#C9C0AE')),
    'ngoc': dict(chinh='#115E59', chinh_re='#0B4440', banner=('#0B4440', '#115E59', '#0F766E'),
                 menu=dict(_MENU_SANG, nen='#E6F0EC', vien='#CFE0D8', chu='#294A42', re='#D8E8E1', chon_nen='#CCEFE0', chon_chu='#0B4440',
                           vach_chon='#115E59', nhom='#115E59', tat='#6D8A81', icon='#3F5A52', icon_chon='#0B4440', cuon='#A9C7BB')),
    'toi': dict(chinh='#2563EB', chinh_re='#1D4ED8', banner=('#0B1120', '#16213A', '#1E293B'),
                menu=dict(_MENU_TOI, nen='#0F172A', vien='#1E293B', chon_nen='#1E3A5F', vach_chon='#38BDF8', nhom='#60A5FA')),
    'diu': dict(chinh='#1E3A5F', chinh_re='#152C48', banner=('#1E3A5F', '#24476F', '#2D5580'),
                menu=dict(_MENU_SANG, nen='#DCE3EC', re='#D0D9E5')),
    'trang': dict(chinh='#1E3A5F', chinh_re='#152C48', banner=('#1E3A5F', '#24476F', '#2D5580'),
                  menu=dict(_MENU_SANG, nen='#FFFFFF', vien='#94A3B8', chu='#000000', icon='#1E293B', nhom='#000000', tat='#4B5563')),
}


# 1.0.79 (người dùng 07/11/2026): 6 phương án Navy dịu mắt, chỉ áp cho các tông nền sáng trung tính + Ấm; Tối, Titan, Ngọc giữ màu riêng.
# chinh, chinh_re: màu chính, rê chuột; chinh_am: màu chính ở tông Ấm; td_*: tiêu đề bảng ngang (nền, chữ, vạch cột, viền đáy, rê chuột);
# dau_*: đầu khung phụ Sổ nhật ký vận động (nền, chữ, viền). Tương phản chữ / nền đã tính theo WCAG: tests/test_phuong_an_navy.py.
PHUONG_AN_NAVY = {
    'pa1_nordic': dict(ten='PA1: Xanh Đá Bắc Âu dịu mắt (Nordic Slate)', chinh='#345678', chinh_re='#284460', chinh_am='#3A5A78',
                       td_nen='#345678', td_chu='#FFFFFF', td_vach='#43688E', td_day='#608AB5', td_re='#284460',
                       dau_nen='#EAF1F8', dau_chu='#284460', dau_vien='#CBD9E8'),
    'pa2_suong_nhat': dict(ten='PA2: Tiêu đề bảng Nền Sương Nhạt (Fluent Mist)', chinh='#2B4C73', chinh_re='#213B59', chinh_am='#325478',
                           td_nen='#E6EEF7', td_chu='#1E3A5F', td_vach='#CBD9E8', td_day='#8FB0D4', td_re='#D8E4F2',
                           dau_nen='#EBF2FA', dau_chu='#1E3A5F', dau_vien='#CBD9E8'),
    'pa3_thep_diu': dict(ten='PA3: Xanh Thép Chân Trời hạ bão hòa (Horizon Steel)', chinh='#3B5978', chinh_re='#2E4761', chinh_am='#3E5C76',
                         td_nen='#3B5978', td_chu='#FFFFFF', td_vach='#4A6B8C', td_day='#587A9E', td_re='#2E4761',
                         dau_nen='#EDF2F7', dau_chu='#2E4761', dau_vien='#CBD5E1'),
    'pa4_cobalt_diu': dict(ten='PA4: Xanh Lam Hành Chính chuẩn mực (Serene Cobalt)', chinh='#2F5275', chinh_re='#24405C', chinh_am='#35587A',
                           td_nen='#2F5275', td_chu='#FFFFFF', td_vach='#3D658C', td_day='#4D78A3', td_re='#24405C',
                           dau_nen='#E8F0F8', dau_chu='#24405C', dau_vien='#C5D7EA'),
    'pa5_khoi_am': dict(ten='PA5: Xanh Khói Ấm chống mỏi mắt (Cashmere Slate)', chinh='#3A5874', chinh_re='#2D455C', chinh_am='#3A5874',
                        td_nen='#3A5874', td_chu='#FFFFFF', td_vach='#496A8A', td_day='#5B7FA0', td_re='#2D455C',
                        dau_nen='#EFECE6', dau_chu='#2D455C', dau_vien='#D8D0C5'),
    'pa6_khoang_sang': dict(ten='PA6: Xanh Khoáng Chất sáng nhẹ (Airy Mineral)', chinh='#3D6082', chinh_re='#304D69', chinh_am='#406282',
                            td_nen='#3D6082', td_chu='#FFFFFF', td_vach='#4C7296', td_day='#648CB3', td_re='#304D69',
                            dau_nen='#EBF3FA', dau_chu='#304D69', dau_vien='#CFE0F0'),
}
MAC_DINH_PHUONG_AN = 'pa1_nordic'
KHOA_PHUONG_AN = 'giao_dien/phuong_an_navy'
TONG_THEO_PHUONG_AN = ('sang', 'diu', 'trang', 'am')
_PHUONG_AN = [MAC_DINH_PHUONG_AN]


def phuong_an_hien() -> str:
    return _PHUONG_AN[0]


def dat_phuong_an(ma: str) -> str:
    _PHUONG_AN[0] = ma if ma in PHUONG_AN_NAVY else MAC_DINH_PHUONG_AN
    return _PHUONG_AN[0]


def mau_phuong_an(ten: str) -> dict | None:
    """Màu của phương án đang chọn cho tông ten; tông giữ màu riêng: None."""
    if ten not in TONG_THEO_PHUONG_AN:
        return None
    pa = PHUONG_AN_NAVY[_PHUONG_AN[0]]
    return dict(pa, chinh=pa['chinh_am']) if ten == 'am' else pa


def mau_tong(ten: str) -> dict:
    """Màu chính / banner / menu của tông (tông lạ: mặc định); tông theo phương án Navy lấy màu chính của phương án."""
    mt = MAU_TONG.get(ten, MAU_TONG[MAC_DINH_TONG_NEN])
    pa = mau_phuong_an(ten)
    return dict(mt, chinh=pa['chinh'], chinh_re=pa['chinh_re']) if pa else mt


MAC_DINH_TONG_NEN = 'sang'
KHOA_TONG_NEN = 'giao_dien/tong_nen'


def cao_dong(ten: str) -> int:
    return MAT_DO.get(ten, MAT_DO[MAC_DINH_MAT_DO])[1]


def cao_tieu_de(ten: str) -> int:
    return MAT_DO.get(ten, MAT_DO[MAC_DINH_MAT_DO])[2]


def tuong_phan_cao_windows() -> bool:
    """Windows đang bật chủ đề tương phản cao (SystemParametersInfo SPI_GETHIGHCONTRAST, cờ HCF_HIGHCONTRASTON). Hệ điều hành khác /
    không gọi được: False."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes

        class HighContrast(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint), ('dwFlags', ctypes.c_uint), ('lpszDefaultScheme', ctypes.c_void_p)]
        hc = HighContrast()
        hc.cbSize = ctypes.sizeof(HighContrast)
        ok = ctypes.windll.user32.SystemParametersInfoW(0x0042, hc.cbSize, ctypes.byref(hc), 0)     # SPI_GETHIGHCONTRAST
        return bool(ok and (hc.dwFlags & 0x1))
    except (OSError, AttributeError):
        return False


def _chon(gia_tri, hop_le: dict, mac_dinh: str) -> str:
    g = str(gia_tri or '').strip().lower()
    return g if g in hop_le else mac_dinh


def doc(cai_dat=None) -> dict:
    """{'mat_do': …, 'tuong_phan': …, 'tong_nen': …}: biến môi trường (PABT_MAT_DO / PABT_TUONG_PHAN_CAO / PABT_TONG_NEN) > QSettings
    (cai_dat, có thể None) > mặc định; giá trị lạ bỏ qua."""
    def lay(khoa):
        try:
            return cai_dat.value(khoa) if cai_dat is not None else None
        except (AttributeError, RuntimeError):
            return None
    md = os.environ.get('PABT_MAT_DO') or lay(KHOA_MAT_DO)
    tp = os.environ.get('PABT_TUONG_PHAN_CAO') or lay(KHOA_TUONG_PHAN)
    tn = os.environ.get('PABT_TONG_NEN') or lay(KHOA_TONG_NEN)
    pa = os.environ.get('PABT_PHUONG_AN_NAVY') or lay(KHOA_PHUONG_AN)
    return {'mat_do': _chon(md, MAT_DO, MAC_DINH_MAT_DO), 'tuong_phan': _chon(tp, TUONG_PHAN, MAC_DINH_TUONG_PHAN),
            'tong_nen': _chon(tn, TONG_NEN, MAC_DINH_TONG_NEN), 'phuong_an_navy': _chon(pa, PHUONG_AN_NAVY, MAC_DINH_PHUONG_AN)}


def ghi(cai_dat, mat_do: str | None = None, tuong_phan: str | None = None, tong_nen: str | None = None, phuong_an_navy: str | None = None) -> None:
    """Ghi lựa chọn (chỉ phần được đưa vào) vào cai_dat (QSettings); không có cai_dat thì bỏ qua."""
    if cai_dat is None:
        return
    if mat_do is not None:
        cai_dat.setValue(KHOA_MAT_DO, _chon(mat_do, MAT_DO, MAC_DINH_MAT_DO))
    if tuong_phan is not None:
        cai_dat.setValue(KHOA_TUONG_PHAN, _chon(tuong_phan, TUONG_PHAN, MAC_DINH_TUONG_PHAN))
    if tong_nen is not None:
        cai_dat.setValue(KHOA_TONG_NEN, _chon(tong_nen, TONG_NEN, MAC_DINH_TONG_NEN))
    if phuong_an_navy is not None:
        cai_dat.setValue(KHOA_PHUONG_AN, _chon(phuong_an_navy, PHUONG_AN_NAVY, MAC_DINH_PHUONG_AN))


# 1.0.51 (người dùng 02/11/2026): LƯU TỰ ĐỘNG cửa sổ lập phương án / Khái toán - lưu sau N giây NGỪNG thao tác (không cắt ngang ô đang
# gõ, không hộp thoại). 0 = tắt. Nhớ ở QSettings (KHOA_LUU_TU_DONG); biến môi trường PABT_TU_LUU (giây) ghi đè. Không có QSettings
# (chạy offscreen - kiểm thử) mà chưa đặt trong phiên: TẮT, để bài kiểm thử không tự ghi CSDL ngoài ý muốn.
CAC_MUC_LUU_TU_DONG = ((10, '10 giây'), (30, '30 giây'), (60, '1 phút'), (120, '2 phút'), (0, 'Tắt'))
CHU_KY_LUU_MAC_DINH = 30
KHOA_LUU_TU_DONG = 'lap_pa/chu_ky_tu_luu'
_CHU_KY_HOP_LE = tuple(g for g, _ in CAC_MUC_LUU_TU_DONG)
_chu_ky_phien = None                # giá trị đặt trong phiên khi không có QSettings (kiểm thử)
_chu_ky_nho = None                  # đã đọc QSettings (đọc mỗi lần gõ phím là thừa)


def _so_chu_ky(gia_tri, mac_dinh: int) -> int:
    try:
        g = int(str(gia_tri).strip())
    except (TypeError, ValueError):
        return mac_dinh
    return g if g in _CHU_KY_HOP_LE else mac_dinh


def _cai_dat_mac_dinh():
    try:
        from .giao_dien import cai_dat_nho
        return cai_dat_nho()
    except Exception:                   # không có Qt / chưa có QApplication
        return None


def chu_ky_luu_tu_dong(cai_dat=None) -> int:
    """Chu kỳ lưu tự động (giây): 10 / 60 / 120, 0 = tắt. PABT_TU_LUU > giá trị đặt trong phiên > QSettings > 10 giây."""
    env = os.environ.get('PABT_TU_LUU')
    if env:
        return _so_chu_ky(env, 0)
    global _chu_ky_nho
    if _chu_ky_phien is not None:
        return _chu_ky_phien
    if cai_dat is None:
        if _chu_ky_nho is not None:
            return _chu_ky_nho
        cai_dat = _cai_dat_mac_dinh()
        if cai_dat is None:
            return 0
        nho = True
    else:
        nho = False
    try:
        g = _so_chu_ky(cai_dat.value(KHOA_LUU_TU_DONG, CHU_KY_LUU_MAC_DINH), CHU_KY_LUU_MAC_DINH)
    except (AttributeError, RuntimeError):
        g = CHU_KY_LUU_MAC_DINH
    if nho:
        _chu_ky_nho = g
    return g


def dat_chu_ky_luu_tu_dong(giay: int, cai_dat=None) -> int:
    """Ghi chu kỳ lưu tự động (0, 10, 60, 120 giây; số lạ -> 10). Trả giá trị đã ghi."""
    global _chu_ky_phien, _chu_ky_nho
    giay = _so_chu_ky(giay, CHU_KY_LUU_MAC_DINH)
    _chu_ky_nho = giay
    cai_dat = cai_dat if cai_dat is not None else _cai_dat_mac_dinh()
    if cai_dat is None:
        _chu_ky_phien = giay
    else:
        try:
            cai_dat.setValue(KHOA_LUU_TU_DONG, giay)
        except (AttributeError, RuntimeError):
            _chu_ky_phien = giay
    return giay


def nhan_chu_ky(giay: int) -> str:
    return dict(CAC_MUC_LUU_TU_DONG).get(giay, f'{giay} giây')


def dao_nhanh_tong_nen(hien_tai: str = MAC_DINH_TONG_NEN) -> str:
    """1.0.34: tông kế tiếp khi bấm nút đổi nhanh (banner): đang Tối -> Sáng Sapphire; tông khác -> Tối chuyên gia."""
    return MAC_DINH_TONG_NEN if hien_tai == 'toi' else 'toi'


def dang_tuong_phan_cao(tuong_phan: str = MAC_DINH_TUONG_PHAN) -> bool:
    """Có dùng bảng màu hệ thống (tương phản cao) không: 'bat' -> có, 'tat' -> không, 'theo_windows' -> theo cài đặt Windows."""
    tuong_phan = _chon(tuong_phan, TUONG_PHAN, MAC_DINH_TUONG_PHAN)
    if tuong_phan == 'bat':
        return True
    if tuong_phan == 'tat':
        return False
    return tuong_phan_cao_windows()
