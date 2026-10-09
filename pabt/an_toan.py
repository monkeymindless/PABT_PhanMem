"""Kiểm tra dữ liệu nhận từ bên ngoài (gọn từ 0.9.16 - người dùng bỏ màn hình "Kiểm tra an toàn", quét virus chủ động, toàn vẹn
bản cài, chữ ký số; Microsoft Defender của máy vẫn tự quét file khi tải về / mở):
  - ngu_canh_tls: kết nối HTTPS bắt buộc kiểm tra chứng chỉ, TLS >= 1.2 (chặn chứng chỉ giả / hết hạn / tự ký);
  - kiem_tra_zip / kiem_tra_xml: chặn file nén "bom" (giải nén ra hàng GB), đường dẫn vượt thư mục và XML có thực thể (tấn
    công "billion laughs") khi đọc .docx / .xlsx / gói .pabtcn.
Tắt macro khi tự động hóa Word / Excel nằm ngay trong mã VBS (AutomationSecurity = 3: in_an, nhap_don_gia, van_ban_trinh) - giữ.
Chỉ dùng thư viện chuẩn (chạy cả Python 3.8 bản Windows 7/8).
"""
from __future__ import annotations
import ssl
import zipfile
from pathlib import Path


class LoiAnToan(Exception):
    pass


# ---------------------------------------------------------------- mạng: HTTPS kiểm tra chứng chỉ, TLS >= 1.2
def ngu_canh_tls() -> ssl.SSLContext:
    ctx = ssl.create_default_context()                  # kiểm tra chứng chỉ + tên máy chủ (chặn chứng chỉ giả, tự ký, hết hạn)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except (AttributeError, ValueError):
        ctx.options |= getattr(ssl, 'OP_NO_TLSv1', 0) | getattr(ssl, 'OP_NO_TLSv1_1', 0)
    return ctx


# ---------------------------------------------------------------- file nén, XML độc
def kiem_tra_zip(p, toi_da: int = 400 * 2 ** 20, ti_le: int = 250, so_muc: int = 20000) -> None:
    """File Office (.xlsx / .docx) / gói .pabtcn là file nén: chặn "bom nén" (giải nén ra quá lớn) và tên file vượt thư mục."""
    try:
        with zipfile.ZipFile(p) as z:
            ds = z.infolist()
    except (zipfile.BadZipFile, OSError) as e:
        raise LoiAnToan(f'File nén "{Path(p).name}" hỏng: {e}') from None
    if len(ds) > so_muc:
        raise LoiAnToan(f'File "{Path(p).name}" chứa quá nhiều mục ({len(ds)}): nghi file độc, không mở.')
    tong = sum(x.file_size for x in ds)
    nen = max(1, sum(x.compress_size for x in ds))
    if tong > toi_da or tong / nen > ti_le and tong > 50 * 2 ** 20:
        raise LoiAnToan(f'File "{Path(p).name}" giải nén ra {tong / 2 ** 20:.0f} MB (nén {nen / 2 ** 20:.1f} MB): nghi "bom nén", '
                        'không mở.')
    for x in ds:
        if x.filename.startswith(('/', '\\')) or '..' in Path(x.filename).parts or ':' in x.filename:
            raise LoiAnToan(f'File "{Path(p).name}" có đường dẫn nguy hiểm bên trong ({x.filename}): không mở.')


def kiem_tra_xml(du: bytes, ten: str = '') -> None:
    """Chặn XML có khai báo DOCTYPE / ENTITY (tấn công mở rộng thực thể, đọc file máy qua thực thể ngoài)."""
    dau = du[:4096].upper()
    if b'<!DOCTYPE' in dau or b'<!ENTITY' in du.upper():
        raise LoiAnToan(f'Nội dung XML {ten} có khai báo DOCTYPE / ENTITY: nghi file độc, không mở.')
