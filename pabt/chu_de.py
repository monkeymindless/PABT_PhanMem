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
    """{'mat_do': …, 'tuong_phan': …}: biến môi trường > QSettings (cai_dat, có thể None) > mặc định; giá trị lạ bỏ qua."""
    def lay(khoa):
        try:
            return cai_dat.value(khoa) if cai_dat is not None else None
        except (AttributeError, RuntimeError):
            return None
    md = os.environ.get('PABT_MAT_DO') or lay(KHOA_MAT_DO)
    tp = os.environ.get('PABT_TUONG_PHAN_CAO') or lay(KHOA_TUONG_PHAN)
    return {'mat_do': _chon(md, MAT_DO, MAC_DINH_MAT_DO), 'tuong_phan': _chon(tp, TUONG_PHAN, MAC_DINH_TUONG_PHAN)}


def ghi(cai_dat, mat_do: str | None = None, tuong_phan: str | None = None) -> None:
    """Ghi lựa chọn (chỉ phần được đưa vào) vào cai_dat (QSettings); không có cai_dat thì bỏ qua."""
    if cai_dat is None:
        return
    if mat_do is not None:
        cai_dat.setValue(KHOA_MAT_DO, _chon(mat_do, MAT_DO, MAC_DINH_MAT_DO))
    if tuong_phan is not None:
        cai_dat.setValue(KHOA_TUONG_PHAN, _chon(tuong_phan, TUONG_PHAN, MAC_DINH_TUONG_PHAN))


def dang_tuong_phan_cao(tuong_phan: str = MAC_DINH_TUONG_PHAN) -> bool:
    """Có dùng bảng màu hệ thống (tương phản cao) không: 'bat' -> có, 'tat' -> không, 'theo_windows' -> theo cài đặt Windows."""
    tuong_phan = _chon(tuong_phan, TUONG_PHAN, MAC_DINH_TUONG_PHAN)
    if tuong_phan == 'bat':
        return True
    if tuong_phan == 'tat':
        return False
    return tuong_phan_cao_windows()
