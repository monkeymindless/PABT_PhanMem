"""Đọc chữ file Word 97-2003 (.doc) bằng Python thuần - không cần Microsoft Word hay LibreOffice.

Đủ cho công cụ quét: lời văn, điều khoản, đơn giá. Bảng phức tạp (ô gộp, hình) đọc đúng hơn khi máy có Word hoặc LibreOffice
(`nhap_don_gia.chuyen_office` chuyển sang .docx trước). Chạy được trên Python 3.8. Không đọc file có mật khẩu.
"""
from __future__ import annotations

import struct
from pathlib import Path

from .doc_xls import MAGIC, LoiXls, _Cfb


class LoiDoc(Exception):
    """File .doc không đọc được bằng bộ đọc thuần Python."""


def _bang(word: bytes) -> str:
    """Tên luồng bảng ('0Table' / '1Table') theo cờ FIB."""
    if len(word) < 12 or struct.unpack_from('<H', word, 0)[0] != 0xA5EC:
        raise LoiDoc('không phải tài liệu Word 97-2003')
    co = struct.unpack_from('<H', word, 0x0A)[0]
    return '1Table' if co & 0x0200 else '0Table'


def _plc(clx: bytes) -> tuple:
    """(danh sách CP, danh sách Fc của từng mảnh chữ) từ CLX. Không có bảng mảnh: (), ()."""
    i, plc = 0, b''
    while i < len(clx):
        loai = clx[i]
        if loai == 1 and i + 3 <= len(clx):
            cb = struct.unpack_from('<H', clx, i + 1)[0]
            i += 3 + cb
        elif loai == 2 and i + 5 <= len(clx):
            lcb = struct.unpack_from('<I', clx, i + 1)[0]
            plc = clx[i + 5:i + 5 + lcb]
            break
        else:
            break
    if len(plc) < 12:
        return (), ()
    n = (len(plc) - 4) // 12
    if n <= 0 or (n + 1) * 4 + n * 8 > len(plc):
        return (), ()
    cp = struct.unpack_from('<%dI' % (n + 1), plc, 0)
    fc = []
    goc = (n + 1) * 4
    for k in range(n):
        fc.append(struct.unpack_from('<I', plc, goc + k * 8 + 2)[0])
    return cp, fc


def _manh(word: bytes, fc: int, so_ky_tu: int) -> str:
    """Một mảnh chữ: bit nén = ANSI (cp1258), không nén = UTF-16."""
    nen = bool(fc & 0x40000000)
    vt = (fc & 0x3FFFFFFF) >> 1 if nen else (fc & 0x3FFFFFFF)
    if so_ky_tu <= 0 or vt < 0 or vt >= len(word):
        return ''
    if nen:
        tho = word[vt:vt + so_ky_tu]
        return tho.decode('cp1258', 'replace')
    tho = word[vt:vt + so_ky_tu * 2]
    if len(tho) % 2:
        tho = tho[:-1]
    return tho.decode('utf-16-le', 'replace')


def _sach(chu: str) -> str:
    """Ký tự điều khiển của Word thành xuống dòng / tab; bỏ mã trường và ký tự không in được."""
    ra = []
    for ch in chu:
        o = ord(ch)
        if ch in '\r\n' or o in (0x0B, 0x0C):
            ra.append('\n')
        elif o == 0x07:
            ra.append('\t')
        elif o == 0x09:
            ra.append('\t')
        elif o < 32 or o in (0x0D,):
            continue
        elif ch == '\u0000':
            continue
        else:
            ra.append(ch)
    return ''.join(ra)


def chu_tu_luong(word: bytes, bang: bytes | None) -> str:
    """Chữ của luồng WordDocument + bảng mảnh (0Table/1Table). Dùng được khi kiểm thử không cần cả file OLE."""
    if bang:
        try:
            fc_clx, lcb = struct.unpack_from('<II', word, 0x01A2)
        except struct.error as e:
            raise LoiDoc('thiếu bảng mảnh chữ') from e
        cp, fc = _plc(bang[fc_clx:fc_clx + lcb] if lcb else b'')
        if cp and fc:
            ra = [_manh(word, f, int(cp[i + 1]) - int(cp[i])) for i, f in enumerate(fc)]
            return _sach(''.join(ra))
    if len(word) < 0x50:
        raise LoiDoc('tài liệu Word quá ngắn')
    fc_min = struct.unpack_from('<I', word, 0x18)[0]
    ccp = struct.unpack_from('<I', word, 0x4C)[0]
    if not ccp or ccp > 5_000_000:
        raise LoiDoc('không thấy phần chữ của tài liệu')
    return _sach(_manh(word, fc_min, ccp) or _manh(word, fc_min | 0x40000000, ccp))


def doc_chu(file) -> str:
    """Toàn bộ chữ đọc được của file .doc. Lỗi: LoiDoc."""
    p = Path(file)
    try:
        du = p.read_bytes()
    except OSError as e:
        raise LoiDoc(str(e)) from None
    if len(du) < 512 or not du.startswith(MAGIC) or len(du) > 40 * 2 ** 20:
        raise LoiDoc('không phải file Word 97-2003 hoặc file quá lớn')
    try:
        cfb = _Cfb(du)
    except LoiXls as e:
        raise LoiDoc(str(e)) from None
    word = cfb.luong(('WordDocument',))
    if not word:
        raise LoiDoc('file không có nội dung Word')
    try:
        ten = _bang(word)
    except LoiDoc:
        ten = '1Table'
    return chu_tu_luong(word, cfb.luong((ten, '0Table', '1Table')))


def doc_dong(file) -> list:
    """Các dòng (danh sách ô) để `doc_bang` / công cụ quét dùng như file chữ. Ô trong bảng ngăn bằng tab."""
    chu = doc_chu(file)
    dong = []
    for ln in chu.splitlines():
        if not ln.strip():
            continue
        dong.append([o.strip() for o in ln.split('\t')])
    if not dong:
        raise LoiDoc('không đọc được chữ trong file Word 97-2003')
    return dong
