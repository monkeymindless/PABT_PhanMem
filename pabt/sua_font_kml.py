"""Khôi phục chữ tiếng Việt lỗi font trong bản đồ .kml / .kmz xuất từ MicroStation / gCadas (người dùng 27/10/2026, file thật Vành đai 4
GĐ2 - Tân An). Không Qt, chỉ thư viện chuẩn. Ứng dụng điện thoại di_dong/ có bản JS cùng từ điển (suaFontKml) - sửa một bên thì sửa cả hai
(test so khớp tests/test_sua_font_kml.py).

Hai kiểu lỗi gặp trong file thật:
1. Chữ mã TCVN3 (ABC) bị đọc như Latin-1: "ngµy 27/12/2022 cña UBND tØnh §ång Nai" -> đổi lại CHÍNH XÁC theo bảng mã (chỉ khi chuỗi có ký tự
   đặc trưng TCVN3 và không có chữ Việt Unicode thật - tránh làm hỏng chữ đúng).
2. Mỗi chữ có dấu bị thay bằng MỘT ký tự "�" (U+FFFD) hoặc "∅" ("H�nh lang b�o v� ngu�n n��c", "t∅nh") - thông tin đã mất, chỉ khôi phục được
   theo từ điển: các từ dưới đây lấy từ đúng các nhãn trong 21 file .kmz thật; có xét từ đứng trước / sau ("b� t�ng" = bê tông, "B� m��ng" =
   Bờ mương). Từ không chắc chắn GIỮ NGUYÊN (không đoán).
"""
from __future__ import annotations
import re

# ---------------------------------------------------------------- 1. TCVN3 (ABC) đọc nhầm Latin-1 -> Unicode
_TCVN3 = {
    'µ': 'à', '¸': 'á', '¶': 'ả', '·': 'ã', '¹': 'ạ', '¨': 'ă', '»': 'ằ', '¾': 'ắ', '¼': 'ẳ', '½': 'ẵ', 'Æ': 'ặ',
    '©': 'â', 'Ç': 'ầ', 'Ê': 'ấ', 'È': 'ẩ', 'É': 'ẫ', 'Ë': 'ậ', '®': 'đ', '§': 'Đ', 'Ì': 'è', 'Ð': 'é', 'Î': 'ẻ', 'Ï': 'ẽ',
    'Ñ': 'ẹ', 'ª': 'ê', 'Ò': 'ề', 'Õ': 'ế', 'Ó': 'ể', 'Ô': 'ễ', 'Ö': 'ệ', '×': 'ì', 'Ý': 'í', 'Ø': 'ỉ', 'Ü': 'ĩ', 'Þ': 'ị',
    'ß': 'ò', 'ã': 'ó', 'á': 'ỏ', 'â': 'õ', 'ä': 'ọ', '«': 'ô', 'å': 'ồ', 'è': 'ố', 'æ': 'ổ', 'ç': 'ỗ', 'é': 'ộ', '¬': 'ơ',
    'ê': 'ờ', 'í': 'ớ', 'ë': 'ở', 'ì': 'ỡ', 'î': 'ợ', 'ï': 'ù', 'ó': 'ú', 'ñ': 'ủ', 'ò': 'ũ', 'ô': 'ụ', '\xad': 'ư', 'õ': 'ừ',
    'ø': 'ứ', 'ö': 'ử', '÷': 'ữ', 'ù': 'ự', 'ú': 'ỳ', 'ý': 'ý', 'û': 'ỷ', 'ü': 'ỹ', 'þ': 'ỵ', '¡': 'Ă', '¢': 'Â', '£': 'Ê',
    '¤': 'Ô', '¥': 'Ơ', '¦': 'Ư', '∅': 'ỉ',      # "∅": phần mềm xuất thay "Ø" (= ỉ) bằng ký hiệu tập rỗng ("t∅nh")
}
# ký tự CHỈ có ở TCVN3 đọc nhầm (không gặp trong tiếng Việt Unicode) - dấu hiệu nhận ra chuỗi TCVN3
_DAU_TCVN3 = set('µ¸¶·¹¨»¾¼½Æ©ÇÊÈÉË®§ÌÐÎÏÑªÒÕÓÔÖ×ØÜÞß«¬\xad¡¢£¤¥¦∅')
_RE_VIET = re.compile('[ĂăĐđƠơƯưẠ-ỹ]')


def tu_tcvn3(s: str) -> str:
    """Chuỗi TCVN3 đọc nhầm Latin-1 -> Unicode; chuỗi không phải TCVN3 giữ nguyên."""
    if not s or _RE_VIET.search(s) or not any(c in _DAU_TCVN3 for c in s):
        return s
    return ''.join(_TCVN3.get(c, c) for c in s)


# ---------------------------------------------------------------- 2. "�" -> chữ có dấu theo từ điển (lấy từ nhãn trong file thật)
L = '�'
TU = {  # từ lỗi (đúng chữ hoa / thường như trong file) -> từ đúng
    '���ng': 'đường', 's�': 'số', 'S�': 'Số', 'T�': 'Tờ', 'M��ng': 'Mương', 'm��ng': 'mương', 'X�': 'Xã', '��t': 'đất', 'T�n': 'Tân',
    'm�p': 'mép', 'v�o': 'vào', 'c�ch': 'cách', 'C�ch': 'Cách', 'th�ng': 'thông', 'Su�i': 'Suối', 'H�nh': 'Hành', 'b�o': 'bảo',
    '��nh': 'định', 'c�a': 'của', 'R�ch': 'Rạch', 'n��c': 'nước', 'Ng�y': 'Ngày', 'ng�y': 'ngày', 'Quy�t': 'Quyết', 'ngu�n': 'nguồn',
    'c�ng': 'công', 't�ng': 'tông', '�n': 'án', 'V�nh': 'Vành', '�ai': 'đai', '�o�n': 'đoạn', 'D�': 'Dự', 'd�': 'dự', 'tuy�n': 'tuyến',
    'B�n': 'Bồn', 'b�n': 'bản', 'Ch�nh': 'Chính', 'tr�nh': 'trình', 'l��i': 'lưới', '�i�n': 'điện', 'd�y': 'dây', 'ngo�i': 'ngoài',
    'Ngh�': 'Nghị', '�p': 'Ấp', 'Nh�a': 'Nhựa', 'nh�a': 'nhựa', 'S�ng': 'Sông', 'Th�nh': 'Thành', 'th�nh': 'thành', '�ng': 'ống',
    'H�': 'Hồ', 'h�': 'hồ', 'ch�': 'chí', 'Ch�': 'Chí', 'd�n': 'dẫn', 'c�u': 'cầu', 'C�u': 'Cầu', 'Th�': 'Thủ', 'Bi�n': 'Biên',
    'c�y': 'cây', 'Vi�t': 'Việt', 'k�nh': 'kênh', 'Th�c': 'Thực', 'hi�n': 'hiện', 'V�n': 'Văn', 'vi�c': 'việc', 'ch�p': 'chấp',
    'thu�n': 'thuận', 'c�m': 'cắm', 'c�c': 'cọc', 'gi�i': 'giải', 'ph�ng': 'phóng', 'm�t': 'mặt', 'b�ng': 'bằng', 'C�p': 'Cập',
    'nh�t': 'nhật', 'M�y': 'Mây', 'B�nh': 'Bình', 'ph�': 'phố', '��NG': 'ĐỒNG', '��ng': 'Đông', 'B�': 'Bờ', 'b�': 'bờ', 'L�': 'Lề', 'Th�ng': 'Thăng',
}
# (từ đứng trước, từ lỗi) / (từ lỗi, từ đứng sau) -> từ đúng: đọc theo ngữ cảnh; giá trị None = không chắc chắn, giữ nguyên
TRUOC = {('ngo�i', 'c�ng'): 'cùng', ('Ch�nh', 'ph�'): 'phủ', ('b�o', 'v�'): 'vệ', ('h�', 's�'): 'sơ'}
SAU = {('��ng', 'Nai'): 'Đồng', ('��NG', 'NAI'): 'ĐỒNG', ('b�', 't�ng'): 'bê', ('B�', 't�ng'): 'Bê', ('v�', 'vi�c'): 'về',
       ('l�', 'than'): None}
# đoạn trong từ có số / ký hiệu ("60/2022/Q�-UBNDng�y", "�T.768.Nh�a", "n��ctheo") - thay theo thứ tự
DOAN = (('UBNDng' + L + 'y', 'UBND ngày'), ('CPng' + L + 'y', 'CP ngày'), ('Q' + L + '-', 'QĐ-'), ('Q' + L + '.', 'QĐ.'), ('N' + L + '-', 'NĐ-'),
        (L + 'T.', 'ĐT.'), ('.Ng' + L + 'y', '.Ngày'), ('Nh' + L + 'a', 'Nhựa'), ('nh' + L + 'a', 'nhựa'), ('n' + L + L + 'ctheo', 'nước theo'))
_RE_TU = re.compile(r'^([("\'\[]*)(.*?)([)\]"\'.,;:!?]*)$', re.S)


def sua_font_kml(s: str) -> str:
    """Nhãn lỗi font -> chữ đúng (TCVN3 đổi chính xác; "�" theo từ điển, từ không chắc giữ nguyên)."""
    if not s:
        return s or ''
    s = tu_tcvn3(s)
    if L not in s:
        return s
    phan = re.split(r'(\s+)', s)
    loi = [i for i, x in enumerate(phan) if x and not x.isspace()]
    goc = [_RE_TU.match(phan[i]).groups() for i in loi]
    loi_dau = loi[0] if loi else -1
    for j, i in enumerate(loi):
        dau, loi_tu, duoi = goc[j]
        if L not in loi_tu:
            continue
        truoc = goc[j - 1][1] if j else ''
        sau = goc[j + 1][1] if j + 1 < len(goc) else ''
        if (truoc, loi_tu) in TRUOC:
            dung = TRUOC[(truoc, loi_tu)]
        elif (loi_tu, sau) in SAU:
            dung = SAU[(loi_tu, sau)]
        else:
            dung = TU.get(loi_tu)
        if dung is None:
            dung = loi_tu
            for a, b in DOAN:
                dung = dung.replace(a, b)
        if i == loi_dau and loi_tu.startswith(L) and dung[:1].islower():
            dung = dung[:1].upper() + dung[1:]              # chữ đầu chuỗi: "���ng ranh…" -> "Đường ranh…"
        phan[i] = dau + dung + duoi
    return ''.join(phan)
