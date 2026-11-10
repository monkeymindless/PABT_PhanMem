"""Chuẩn hóa chữ đọc từ file (1.0.90, bộ quét file thông minh). Không Qt, chỉ thư viện chuẩn.

- Phông cũ: văn bản hành chính soạn bằng phông TCVN3 (.VnTime, .VnArial...; bộ chữ HOA .VnTimeH) hay VNI (VNI-Times) lưu MÃ của phông, không
  phải chữ Unicode: đọc thẳng ra "Quy\xb8t ®Þnh". `tcvn3_sang_unicode` / `vni_sang_unicode` đổi lại; `chuyen_theo_phong` theo tên phông của
  đoạn chữ (Word ghi tên phông từng đoạn), `doan_ma_cu` đoán khi không biết phông (PDF, file chữ).
- `chuan_hoa`: NFC (chữ tách dấu NFD -> dựng sẵn), bỏ ký tự vô hình (ZWSP, gạch nối mềm, BOM), khoảng trắng lạ -> dấu cách, gạch đầu dòng
  phông Symbol / Wingdings (vùng riêng) -> "-".
- `danh_gia`: chỉ số chất lượng chữ (ký tự hỏng, chữ phông cũ còn sót, tỷ lệ chữ có dấu) để cảnh báo người dùng xem lại, không đoán bừa.
Không đổi chữ đã đúng Unicode: bảng TCVN3 / VNI chỉ áp cho đoạn chữ của phông cũ hoặc đoạn có dấu hiệu rõ (nhiều ký tự mã cũ, không có chữ Việt
Unicode)."""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- TCVN3 (ABC): mã 1 byte -> chữ thường (bộ chữ HOA dùng phông riêng ...H)
_TCVN3 = {
    0xB8: 'á', 0xB5: 'à', 0xB6: 'ả', 0xB7: 'ã', 0xB9: 'ạ',
    0xA8: 'ă', 0xBE: 'ắ', 0xBB: 'ằ', 0xBC: 'ẳ', 0xBD: 'ẵ', 0xC6: 'ặ',
    0xA9: 'â', 0xCA: 'ấ', 0xC7: 'ầ', 0xC8: 'ẩ', 0xC9: 'ẫ', 0xCB: 'ậ',
    0xAE: 'đ',
    0xD0: 'é', 0xCC: 'è', 0xCE: 'ẻ', 0xCF: 'ẽ', 0xD1: 'ẹ',
    0xAA: 'ê', 0xD5: 'ế', 0xD2: 'ề', 0xD3: 'ể', 0xD4: 'ễ', 0xD6: 'ệ',
    0xDD: 'í', 0xD7: 'ì', 0xD8: 'ỉ', 0xDC: 'ĩ', 0xDE: 'ị',
    0xE3: 'ó', 0xDF: 'ò', 0xE1: 'ỏ', 0xE2: 'õ', 0xE4: 'ọ',
    0xAB: 'ô', 0xE8: 'ố', 0xE5: 'ồ', 0xE6: 'ổ', 0xE7: 'ỗ', 0xE9: 'ộ',
    0xAC: 'ơ', 0xED: 'ớ', 0xEA: 'ờ', 0xEB: 'ở', 0xEC: 'ỡ', 0xEE: 'ợ',
    0xF3: 'ú', 0xEF: 'ù', 0xF1: 'ủ', 0xF2: 'ũ', 0xF4: 'ụ',
    0xAD: 'ư', 0xF8: 'ứ', 0xF5: 'ừ', 0xF6: 'ử', 0xF7: 'ữ', 0xF9: 'ự',
    0xFD: 'ý', 0xFA: 'ỳ', 0xFB: 'ỷ', 0xFC: 'ỹ', 0xFE: 'ỵ',
    0xA1: 'Ă', 0xA2: 'Â', 0xA7: 'Đ', 0xA3: 'Ê', 0xA4: 'Ô', 0xA5: 'Ơ', 0xA6: 'Ư',
}
_BANG_TCVN3 = {k: v for k, v in _TCVN3.items()}

# ---------------------------------------------------------------- VNI: chữ gốc + ký tự dấu đi sau (VNI-Times...)
# dấu thanh / mũ / móc của VNI (chữ thường; chữ hoa dùng mã hoa tương ứng)
_VNI_DAU = {
    'ù': '́', 'ø': '̀', 'û': '̉', 'õ': '̃', 'ï': '̣',          # sắc, huyền, hỏi, ngã, nặng
    'Ù': '́', 'Ø': '̀', 'Û': '̉', 'Õ': '̃', 'Ï': '̣',
}
_VNI_MU = {                                                                     # sau a / e / o: â ê ô (kèm dấu thanh gộp sẵn)
    'â': ('̂', ''), 'á': ('̂', '́'), 'à': ('̂', '̀'), 'å': ('̂', '̉'), 'ã': ('̂', '̃'),
    'ä': ('̂', '̣'),
    'Â': ('̂', ''), 'Á': ('̂', '́'), 'À': ('̂', '̀'), 'Å': ('̂', '̉'), 'Ã': ('̂', '̃'),
    'Ä': ('̂', '̣'),
}
_VNI_TRANG = {                                                                  # sau a: ă (kèm dấu thanh)
    'ê': ('̆', ''), 'é': ('̆', '́'), 'è': ('̆', '̀'), 'ú': ('̆', '̉'), 'ü': ('̆', '̃'),
    'ë': ('̆', '̣'),
    'Ê': ('̆', ''), 'É': ('̆', '́'), 'È': ('̆', '̀'), 'Ú': ('̆', '̉'), 'Ü': ('̆', '̃'),
    'Ë': ('̆', '̣'),
}
_VNI_DON = {'ñ': 'đ', 'Ñ': 'Đ', 'ô': 'ơ', 'Ô': 'Ơ', 'ö': 'ư', 'Ö': 'Ư', 'ò': 'ị', 'Ò': 'Ị', 'ó': 'í', 'Ó': 'Í', 'ì': 'ì', 'Ì': 'Ì',
            'î': 'ĩ', 'Î': 'Ĩ', 'æ': 'ỉ', 'Æ': 'Ỉ'}


def tcvn3_sang_unicode(s: str, hoa: bool = False) -> str:
    """Chữ phông TCVN3 -> Unicode. hoa=True: phông bộ chữ HOA (.VnTimeH...) - mã chữ thường hiển thị thành chữ hoa."""
    ra = ''.join(_BANG_TCVN3.get(ord(c), c) for c in str(s or ''))
    return ra.upper() if hoa else ra


def vni_sang_unicode(s: str) -> str:
    """Chữ phông VNI -> Unicode (chữ gốc + mã dấu đi sau)."""
    s = str(s or '')
    ra = []
    i = 0
    while i < len(s):
        c = s[i]
        sau = s[i + 1] if i + 1 < len(s) else ''
        if c in 'aAeEoO' and sau in _VNI_MU:
            mu, dau = _VNI_MU[sau]
            ra.append(unicodedata.normalize('NFC', c + mu + dau))
            i += 2
            continue
        if c in 'aA' and sau in _VNI_TRANG:
            tr, dau = _VNI_TRANG[sau]
            ra.append(unicodedata.normalize('NFC', c + tr + dau))
            i += 2
            continue
        if c in _VNI_DON:
            c = _VNI_DON[c]
        if c in 'ơƠưƯaAeEiIoOuUyY' and sau in _VNI_DAU:
            ra.append(unicodedata.normalize('NFC', c + _VNI_DAU[sau]))
            i += 2
            continue
        if ra and sau == '' and c in _VNI_DAU:
            ra.append(c)
            i += 1
            continue
        ra.append(c)
        i += 1
    return unicodedata.normalize('NFC', ''.join(ra))


def loai_phong(ten_phong: str) -> str:
    """'tcvn3' | 'tcvn3_hoa' | 'vni' | '' theo tên phông của đoạn chữ Word."""
    t = str(ten_phong or '').strip().lower()
    if t.startswith('.vn'):
        return 'tcvn3_hoa' if t.endswith('h') else 'tcvn3'
    if t.startswith('vni-') or t.startswith('vni '):
        return 'vni'
    return ''


def chuyen_theo_phong(s: str, ten_phong: str) -> str:
    """Đổi chữ của một đoạn theo phông của nó (phông Unicode: giữ nguyên)."""
    lp = loai_phong(ten_phong)
    if lp == 'tcvn3':
        return tcvn3_sang_unicode(s)
    if lp == 'tcvn3_hoa':
        return tcvn3_sang_unicode(s, hoa=True)
    if lp == 'vni':
        return vni_sang_unicode(s)
    return s


_RE_VIET = re.compile(r'[ạảãàáâậầấẩẫăắằặẳẵêếềệểễôốồộổỗơớờợởỡưứừựửữđịỉĩìíọỏõòóụủũùúỵỷỹỳý]', re.I)
_MA_TCVN3 = frozenset(chr(k) for k in _TCVN3)


def _so_viet_that(s: str) -> int:
    """Số chữ Việt Unicode ngoài vùng Latin-1 (đ, ơ, ư, ạ, ế...): chữ TCVN3 đọc thẳng chỉ có ký tự <= U+00FF (è, é, ò cũng là mã TCVN3)."""
    return sum(1 for c in _RE_VIET.findall(s) if ord(c) > 0xFF)


def doan_ma_cu(s: str) -> str:
    """Đoán chữ còn mã phông cũ khi không biết phông (PDF, file chữ): 'tcvn3' khi có nhiều ký tự mã TCVN3 (®, ¸, µ, ­...) mà gần như không
    có chữ Việt Unicode; '' nếu không chắc (không đổi gì - tránh làm hỏng chữ đúng)."""
    s = str(s or '')
    if len(s) < 20:
        return ''
    n_ma = sum(1 for c in s if c in _MA_TCVN3)
    n_viet = _so_viet_that(s)
    chu = sum(1 for c in s if c.isalpha()) or 1
    if n_ma >= 8 and n_ma / chu > 0.04 and n_viet <= n_ma * 0.05:
        return 'tcvn3'
    return ''


_VO_HINH = dict.fromkeys(map(ord, '​‌‍⁠﻿­'), None)
_KHOANG = {ord(c): ' ' for c in '              　'}


def chuan_hoa(s: str) -> str:
    """NFC + bỏ ký tự vô hình + khoảng trắng lạ -> dấu cách + gạch đầu dòng phông ký hiệu (vùng riêng U+F0xx) -> '-'. Giữ xuống dòng, Tab."""
    s = str(s or '')
    if not s:
        return s
    s = s.translate(_VO_HINH).translate(_KHOANG)
    s = re.sub('[-]', '-', s)
    return unicodedata.normalize('NFC', s)


def sua_chu(s: str) -> tuple:
    """(chữ đã chuẩn hóa, loại mã cũ đã đổi hoặc ''). Dùng cho chữ không biết phông (PDF, txt, kết quả bộ đọc khác)."""
    lp = doan_ma_cu(s)
    if lp == 'tcvn3':
        s = tcvn3_sang_unicode(s)
    return chuan_hoa(s), lp


def danh_gia(s: str) -> dict:
    """Chỉ số chất lượng chữ đã đọc: ky_tu, hong (U+FFFD), ma_cu (ký tự mã TCVN3 còn sót), ty_le_viet (chữ có dấu / chữ cái), canh_bao [chữ]."""
    s = str(s or '')
    chu = sum(1 for c in s if c.isalpha())
    hong = s.count('�')
    ma_cu = sum(1 for c in s if c in _MA_TCVN3) if not _so_viet_that(s[:20000]) else 0
    viet = len(_RE_VIET.findall(s))
    kq = dict(ky_tu=len(s), chu_cai=chu, hong=hong, ma_cu=ma_cu, ty_le_viet=round(viet / chu, 3) if chu else 0.0, canh_bao=[])
    if hong:
        kq['canh_bao'].append(f'{hong} ký tự không đọc được (�): đối chiếu bản gốc ở các chỗ này.')
    if ma_cu > 20:
        kq['canh_bao'].append('Chữ có thể còn mã phông cũ (TCVN3 / VNI) chưa đổi được: mở bằng Word, đổi sang phông Unicode rồi quét lại.')
    if chu > 400 and kq['ty_le_viet'] < 0.02:
        kq['canh_bao'].append('Rất ít chữ có dấu tiếng Việt: văn bản có thể không phải tiếng Việt, hoặc phông / nhận dạng chữ bị lỗi.')
    return kq
