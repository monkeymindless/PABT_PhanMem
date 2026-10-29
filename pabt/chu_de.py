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
# kiểu chung (dat_tong_nen); áp ngay, nhớ cho lần mở sau. 1.0.34: mặc định Sáng Sapphire (nền #F1F5F9 - khác màu gốc 1.0.33), thêm Ấm
# áp và Tối chuyên gia (Dark Studio).
TONG_NEN = {
    'sang': ('Sáng Sapphire (Flagship Pro)', '#F1F5F9', '#FFFFFF', '#CBD5E1', '#0F172A', '#475569'),
    'diu': ('Dịu mắt (Slate Studio)', '#E2E8F0', '#F8FAFC', '#94A3B8', '#0F172A', '#334155'),
    'am': ('Ấm áp (Ivory Paper)', '#F5F2EB', '#FFFDF9', '#D6CFC2', '#1C1917', '#57534E'),
    'toi': ('Tối chuyên gia (Dark Studio)', '#0B1120', '#1E293B', '#334155', '#F1F5F9', '#94A3B8'),
    'trang': ('Trắng tương phản (máy chiếu / ngoài trời)', '#FFFFFF', '#FFFFFF', '#94A3B8', '#000000', '#1E293B'),
}
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
    return {'mat_do': _chon(md, MAT_DO, MAC_DINH_MAT_DO), 'tuong_phan': _chon(tp, TUONG_PHAN, MAC_DINH_TUONG_PHAN),
            'tong_nen': _chon(tn, TONG_NEN, MAC_DINH_TONG_NEN)}


def ghi(cai_dat, mat_do: str | None = None, tuong_phan: str | None = None, tong_nen: str | None = None) -> None:
    """Ghi lựa chọn (chỉ phần được đưa vào) vào cai_dat (QSettings); không có cai_dat thì bỏ qua."""
    if cai_dat is None:
        return
    if mat_do is not None:
        cai_dat.setValue(KHOA_MAT_DO, _chon(mat_do, MAT_DO, MAC_DINH_MAT_DO))
    if tuong_phan is not None:
        cai_dat.setValue(KHOA_TUONG_PHAN, _chon(tuong_phan, TUONG_PHAN, MAC_DINH_TUONG_PHAN))
    if tong_nen is not None:
        cai_dat.setValue(KHOA_TONG_NEN, _chon(tong_nen, TONG_NEN, MAC_DINH_TONG_NEN))


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
