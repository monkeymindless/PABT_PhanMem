"""Đóng gói bộ mẫu in chuẩn (mau_in\\) vào mã nguồn: pabt\\mau_in_nhung.py (zlib mức 9 + Base64).

Chạy lại MỖI KHI sửa mẫu chuẩn trong mau_in\\ (test tests/test_mau_in_nhung.py báo khi bản nhúng lệch file mẫu):
    .venv\\Scripts\\python tao_mau_nhung.py
Phần mềm dùng bản nhúng khi máy không có thư mục mẫu (máy trắng, bản cài thiếu mau_in\\) - in_an.thu_muc_mau.
"""
from __future__ import annotations

import base64
import hashlib
import sys
import zlib
from pathlib import Path

GOC = Path(__file__).resolve().parent
MAU = GOC / 'mau_in'
RA = GOC / 'pabt' / 'mau_in_nhung.py'

# (tên hằng, file trong mau_in\, tên mẫu dùng khi tra)
DS = (
    ('BYTES_MAU_CHI_TIET', 'IN_CHITIET.xlsx', 'IN_CHITIET'),
    ('BYTES_MAU_DU_THAO', 'IN_CHITIET__Du thao.xlsx', 'IN_CHITIET__Du thao'),
    ('BYTES_MAU_TONG_HOP', 'IN_BANGTONGHOP.xlsx', 'IN_BANGTONGHOP'),
    ('XML_DUONG_KE_CT', 'IN_CHITIET.duong_ke.xml', 'IN_CHITIET'),
    ('XML_DUONG_KE_BTH', 'IN_BANGTONGHOP.duong_ke.xml', 'IN_BANGTONGHOP'),
)
RONG = 100


def ma_hoa(du_lieu: bytes) -> str:
    return base64.b64encode(zlib.compress(du_lieu, 9)).decode('ascii')


def tao() -> str:
    dong = ['"""Bộ mẫu in chuẩn nhúng trong mã (zlib mức 9 + Base64) - TỰ SINH bởi tao_mau_nhung.py, đừng sửa tay.',
            '',
            'Dùng khi máy không có thư mục mẫu in (máy trắng): in_an.thu_muc_mau trả THU_MUC_NHUNG, in_an.nap_mau_bytes / _doc_dk',
            'lấy bytes ở đây. Mẫu người dùng đã sửa (%APPDATA%\\\\PABT\\\\mau_in, mau_in\\\\ cạnh PABT.exe) vẫn được ưu tiên."""',
            'from __future__ import annotations', '',
            'import base64', 'import hashlib', 'import zlib', '']
    sha = {}
    for ten_hang, f, _ in DS:
        b = (MAU / f).read_bytes()
        sha[ten_hang] = hashlib.sha256(b).hexdigest()
        s = ma_hoa(b)
        dong.append(f'{ten_hang} = (')
        dong += [f"    '{s[i:i + RONG]}'" for i in range(0, len(s), RONG)]
        dong += [')', '']
    dong.append('SHA256 = {')
    dong += [f"    '{k}': '{v}'," for k, v in sha.items()]
    dong += ['}', '']
    dong.append('# tên mẫu (stem file) -> hằng')
    dong.append('MAU = {')
    dong += [f"    '{ten}': '{h}'," for h, f, ten in DS if f.endswith('.xlsx')]
    dong += ['}', 'DUONG_KE = {']
    dong += [f"    '{ten}': '{h}'," for h, f, ten in DS if f.endswith('.xml')]
    dong += ['}', '']
    dong.append('''_GIAI = {}


def _giai(ten_hang: str) -> bytes:
    b = _GIAI.get(ten_hang)
    if b is None:
        b = zlib.decompress(base64.b64decode(globals()[ten_hang]))
        if hashlib.sha256(b).hexdigest() != SHA256[ten_hang]:
            raise ValueError(f'Mẫu in nhúng {ten_hang} hỏng (sai mã SHA-256).')
        _GIAI[ten_hang] = b
    return b


def _chuan(ten: str) -> str:
    ten = str(ten)
    for duoi in ('.xlsx', '.duong_ke.xml'):
        if ten.lower().endswith(duoi):
            ten = ten[:-len(duoi)]
    return ten


def co_mau(ten: str) -> bool:
    return _chuan(ten) in MAU


def lay_bytes_mau(ten: str) -> bytes:
    """Bytes file .xlsx của mẫu nhúng (ten = 'IN_CHITIET', 'IN_BANGTONGHOP', 'IN_CHITIET__Du thao'; có hoặc không đuôi)."""
    t = _chuan(ten)
    if t not in MAU:
        raise KeyError(f'Không có mẫu in nhúng {ten}.')
    return _giai(MAU[t])


def lay_duong_ke(ten: str) -> str:
    """XML đường kẻ của mẫu nhúng ('' nếu mẫu không có)."""
    t = _chuan(ten)
    return _giai(DUONG_KE[t]).decode('utf-8') if t in DUONG_KE else ''
''')
    return '\n'.join(dong)


def main() -> int:
    RA.write_text(tao(), encoding='utf-8', newline='\r\n')
    print(f'Đã ghi {RA} ({RA.stat().st_size:,} byte).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
