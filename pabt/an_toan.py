"""Kiểm tra dữ liệu nhận từ bên ngoài (gọn từ 0.9.16 - người dùng bỏ màn hình "Kiểm tra an toàn", quét virus chủ động, toàn vẹn
bản cài, chữ ký số; Microsoft Defender của máy vẫn tự quét file khi tải về / mở):
  - ngu_canh_tls: kết nối HTTPS bắt buộc kiểm tra chứng chỉ, TLS >= 1.2 (chặn chứng chỉ giả / hết hạn / tự ký);
  - kiem_tra_zip / kiem_tra_xml: chặn file nén "bom" (giải nén ra hàng GB), đường dẫn vượt thư mục và XML có thực thể (tấn
    công "billion laughs") khi đọc .docx / .xlsx / gói .pabtcn.
Tắt macro khi tự động hóa Word / Excel nằm ngay trong mã VBS (AutomationSecurity = 3: in_an, nhap_don_gia, van_ban_trinh) - giữ.
Chỉ dùng thư viện chuẩn (chạy cả Python 3.8 bản Windows 7/8).
"""
from __future__ import annotations
import re
import ssl
import zipfile
from pathlib import Path


class LoiAnToan(Exception):
    pass


# ---------------------------------------------------------------- Excel xuất ra: chặn công thức do dữ liệu người dùng gõ (1.0.19)
# Họ tên / địa chỉ / ghi chú bắt đầu bằng "=" mà ghi vào ô thì openpyxl lưu thành CÔNG THỨC (vd =HYPERLINK(...)). Phần mềm tự ghi
# công thức chỉ gồm SUM / ROUND trên ô và số; mọi công thức khác trong file xuất ra bị ép về chữ (quotePrefix) ở MỘT cổng: luu_xlsx.
CONG_THUC_CHO_PHEP = ('SUM', 'ROUND')
_RE_O_THAM_CHIEU = re.compile(r'\$?[A-Z]{1,3}\$?\d+')
_RE_KY_TU_CONG_THUC = re.compile(r'^[A-Z0-9$:.,%*+\-/() ]*$')


def la_cong_thuc_an_toan(s) -> bool:
    """Công thức chỉ gồm SUM / ROUND, tham chiếu ô, số và phép tính - đúng loại phần mềm tự ghi."""
    s = str(s)
    if not s.startswith('=') or len(s) > 200:
        return False
    than = s[1:].upper()
    if not _RE_KY_TU_CONG_THUC.match(than):          # không có " ! | [ ] { } ; @ ' & < > _ hay chữ thường
        return False
    con_lai = _RE_O_THAM_CHIEU.sub('', than)
    return all(t in CONG_THUC_CHO_PHEP for t in re.findall(r'[A-Z]+', con_lai))


def khu_cong_thuc(wb) -> int:
    """Ép mọi ô công thức KHÔNG an toàn của workbook thành chữ thường (không còn là công thức); trả số ô đã ép."""
    so = 0
    for ws in wb.worksheets:
        for c in list(ws._cells.values()):
            if c.data_type == 'f' and not la_cong_thuc_an_toan(c.value):
                chu = str(c.value)
                c.value = chu
                c.data_type = 's'
                try:
                    c.quotePrefix = True
                except (AttributeError, TypeError):
                    pass
                so += 1
    return so


def luu_xlsx(wb, duong_dan) -> int:
    """Lưu workbook xuất ra cho người dùng: khu_cong_thuc rồi wb.save. MỌI file Excel xuất ra đi qua đây."""
    so = khu_cong_thuc(wb)
    wb.save(str(duong_dan))
    return so


# ---------------------------------------------------------------- dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP)
KHOA_CHE_CCCD = 'CHE_CCCD'          # cai_dat của dự án: '1' = bản in / văn bản trình che số CCCD (bản niêm yết công khai)


def che_cccd(chu: str) -> str:
    """1.0.04 (người dùng 19/10/2026): BỎ che số CCCD trên toàn hệ thống - luôn trả nguyên chuỗi (giữ tên hàm cho mã gọi cũ:
    bản in, văn bản trình, Niêm yết, phiếu kiểm đếm)."""
    return chu or ''


def can_che_cccd(con) -> bool:
    """1.0.04: không còn chế độ che CCCD - luôn False (khóa cai_dat CHE_CCCD của dự án cũ bỏ qua)."""
    return False


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


def la_loi_chung_chi(e) -> bool:
    """Lỗi xác minh chứng chỉ HTTPS (không phải lỗi mạng / HTTP)."""
    ly_do = getattr(e, 'reason', e)
    return isinstance(ly_do, ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in str(ly_do).upper()


_DA_NAP_GOC = {}                    # tên máy chủ -> kết quả nạp (mỗi máy chủ thử một lần mỗi phiên)


def nap_goc_ca_windows(url: str, cho: int = 20) -> bool:
    """Windows tải chứng chỉ gốc khi chính Windows (CryptoAPI) dựng chuỗi chứng chỉ ("Automatic Root Certificates Update");
    Python chỉ đọc các chứng chỉ gốc ĐÃ có trong kho -> lần đầu gặp CA gốc mới báo CERTIFICATE_VERIFY_FAILED dù trình duyệt mở
    bình thường (vbpl.vn - GlobalSign R46, đo 12/10/2026: Python lỗi, .NET mở được, sau đó Python mở được). Cho Windows kết nối
    thử (VẪN xác minh chứng chỉ đầy đủ - không tắt kiểm tra) để kho có gốc CA rồi gọi lại. True = Windows tin chứng chỉ."""
    import re
    import subprocess
    import sys
    import urllib.parse
    if sys.platform != 'win32':
        return False
    may = urllib.parse.urlparse(url).hostname or ''
    if not re.fullmatch(r'[A-Za-z0-9.\-]{1,253}', may):  # chỉ tên máy chủ - không chèn được lệnh vào PowerShell
        return False
    if may in _DA_NAP_GOC:
        return _DA_NAP_GOC[may]
    lenh = ("$ErrorActionPreference='Stop';try{[Net.ServicePointManager]::SecurityProtocol=3072}catch{};"
            f"$r=[Net.HttpWebRequest]::Create('https://{may}/');$r.Method='HEAD';$r.Timeout={int(cho) * 1000};"
            "try{$x=$r.GetResponse();$x.Close();exit 0}catch [Net.WebException]{"
            "if($_.Exception.Status -eq 'TrustFailure'){exit 2};if($_.Exception.Response){exit 0};exit 3}")
    try:
        kq = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', lenh], capture_output=True,
                            timeout=cho + 10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        ok = kq.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    _DA_NAP_GOC[may] = ok
    return ok


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
