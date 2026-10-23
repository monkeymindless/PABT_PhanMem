"""Bộ mẫu in chuẩn nhúng trong mã (zlib mức 9 + Base64) - TỰ SINH bởi tao_mau_nhung.py, đừng sửa tay.

Dùng khi máy không có thư mục mẫu in (máy trắng): in_an.thu_muc_mau trả THU_MUC_NHUNG, in_an.nap_mau_bytes / _doc_dk
lấy bytes ở đây. Mẫu người dùng đã sửa (%APPDATA%\\PABT\\mau_in, mau_in\\ cạnh PABT.exe) vẫn được ưu tiên."""
from __future__ import annotations

import base64
import hashlib
import zlib

BYTES_MAU_TONG_HOP = (
    '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'
)

XML_DUONG_KE_BTH = (
    'eNrtVl1u00AQvorl9633196N6ki2YyMkBAgk3o1jt1Ztb2SbxFXVO3AB7sAzfUXcozdhvf4pVAkgVEoRzUsmM9/MNzNZf97jbl0v'
    '2p0M0qLwquRU1svj3pXVshysRBZLdmxN5uR7kWVL5NhMcDEHe5+O13K3xIO7NydfH8eMQjiHdIb1PWErb4id/cQEC4bgnfDObF31'
    'emOUcVJL1zQHX7UNeu/LcSfJ8+3L2sjXrolNo4rL1DU/v//y8frqQ3VinF1/ujKwSowXadc+a9rRMt7VuWteRBH2WRhRECkLUOhT'
    '4IdUgAgTHmInCjCxL/tsZC+SOo3bXFZP10ZXFlWzUE7XPG3bzcKymuQ0LePmqMxVp43M2qNElpbMsjxJrXUd7/LqxMIQUauM88rU'
    '7V4gFtmREAGwGfQAFQ4Evs9WwKGCc5tz5pDg0rTUSnTP07eewppHn7cwbsUag7fW1GgrXnRZXRpZkW/euCbSi1FdGp1rCgQhJsI0'
    'zl3TthnlsKcetpWoOFKnClHbNBIFgGNbfbUetKmb9kkqS6M3XLPIq1TXjreq2wE6QXp3URk7xcgw06hGFvk6yotC/6hP3gZFbWzj'
    'QvHoz0j2Dczqa4yDNjcztudFOtR/lWZqyd00o/5/0rns+gyNNTWyR2Sq7pwEf5w0YvV2sixN2l9NnNGaUVY3iWVeyXpfctvNrAN+'
    'mnqY1ZqfkvEcFHlatau4jadzsEdGfqosGB2QFkIoFvQPSgvG+5kxpg6C7O+JCzkgLuSBissKqSc4cChwGAoBDZ0V8IJAAMdTvBx5'
    'ZBVG9ycumHFEGKUH1QWrNxa20aO6/Afqgg5dXCCmiBy4QNh3oS7owM3F5pBTeifEvyUu9IC40AcqLtDzA8bUVSW0bQg4hyHgwvMB'
    'JZysPN/3MeX3Jy6IccIYZFpcEBdC4FvqQqC6TCH6qC7/tLp8BeVkS74='
)

SHA256 = {
    'BYTES_MAU_TONG_HOP': '821ad6fa7ea4ae7a4f2684035d62b9ec95b5cec954bc5a8e2b6cfb84fe962433',
    'XML_DUONG_KE_BTH': '4d5604e856a87c38cf86585f8396666cdb38ccc9070d5661be3348ea0c8c7ab3',
}

# tên mẫu (stem file) -> hằng
MAU = {
    'IN_BANGTONGHOP': 'BYTES_MAU_TONG_HOP',
}
DUONG_KE = {
    'IN_BANGTONGHOP': 'XML_DUONG_KE_BTH',
}

_GIAI = {}


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
