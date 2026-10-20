"""Hiểu dòng tài sản viết tự nhiên (người dùng 15/10/2026) - dùng chung cho hộp "Dán danh sách tài sản" (phương án hộ, Khái toán &
dự toán) và nhập Phiếu kiểm đếm thực địa:

    Nhà tạm: 46m2                                         -> Nhà tạm | m² | 46
    Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2  -> áp giá "Nhà 01 tầng - Kết cấu loại 4", ghi chú tên thực tế
    Xoài: 16 cây, 17 năm tuổi                             -> mục xoài đúng năm tuổi (Năm thứ 14-18) | cây | 16
    Tràm: 1453 cây, đường kính 28cm.                      -> loại "Keo lá tràm" theo đường kính 28 cm | 1453 cây
    Tràm cây 1500 d28                                     -> như trên (không có dấu hai chấm)
    Ao nuôi cá ghép: 1,5ha, 1 năm 1 vụ.                   -> vật nuôi "Ao nuôi cá - Nuôi ghép cá các loại…" | 1,5 | ghi chú

1. tach_dong: tên (trước dấu ":" hoặc trước nhóm số liệu cuối dòng) + các phần số liệu: số lượng + ĐVT, đường kính / chu vi (cm),
   năm tuổi, tỷ lệ %, số vụ; phần còn lại vào ghi chú.
2. bo_sung: sau khi phan_loai_tai_san xếp loại - cây có đường kính / chu vi -> loại cây trong bảng quy cách đường kính (so CÓ DẤU
   trước: "tràm" không phải "trám"); cây có năm tuổi -> mục đúng khoảng năm của loài; tên khác cách viết của bộ đơn giá -> khớp
   theo từ (mọi từ của tên có trong tên mục, ít từ thừa nhất). "<tên> tính bằng / tương đương <mục>" áp giá theo <mục>.
Không phụ thuộc Qt.
"""
from __future__ import annotations
import re
import unicodedata

from .lap_pa import bo_dau

DON_VI = (r'100\s?m3\s?/\s?vụ|100\s?m³\s?/\s?vụ|ha\s?/\s?vụ|m2\s?sàn|m²\s?sàn|nhân\s+khẩu|m\s+dài|kg\s+yến(?:\s+thô)?|'
          r'm2|m²|m3|m³|md|ha|cây|bụi|khóm|gốc|chậu|con|kg|cái|chiếc|bộ|trụ|cột|ngôi|mộ|hộ|khẩu|tháng|tấn|lít|m')
_SAU_CHU = r'(?![^\W\d_])'                          # sau đơn vị không còn chữ cái ("m" không ăn "mái")
_SO = r'\d[\d.,]*(?:\s*[*x×]\s*\d[\d.,]*)*'
# kích thước dài x rộng = diện tích (người dùng 20/10/2026): "4,7x3,0", "4,7*3,0", "3,7m x 4,3m", "3,7 * 4,3", "3,7 x 4,3 m2" -> m²;
# số không bị cắt giữa chừng ("2,5x3,5x1" không khớp "2,5x3,"), ba thừa số / đơn vị khác sau ("3x4 cây", "2x3 m3") để quy tắc số lượng
_SO_KT = r'(\d+(?:[.,]\d+)*)(?![.,]?\d)'
_RE_KICH_THUOC = re.compile(_SO_KT + r'\s*(?:m(?=\s*[x×*])\s*)?([x×*])\s*' + _SO_KT +
                            r'(?:\s*(m2|m²|m(?![23²³]))' + _SAU_CHU + r'|(?!\s*[x×*]\s*\d)(?!\s*(?:' + DON_VI + r')' + _SAU_CHU + r'))',
                            re.I)
_RE_DIEN_TICH_O = re.compile(_SO_KT + r'\s*(m2|m²)$', re.I)       # một ô "42m2" / "42 m²"
_DAU_TACH = re.compile(r'^[\s,;:.+-]+|^(?:và|gồm|có|khoảng|diện\s+tích|dt|số\s+lượng|sl|khối\s+lượng|kl|dài|chiều\s+dài)(?![^\W\d_])\s*[:=]?\s*', re.I)
# (khóa, mẫu) - xét từ đầu phần số liệu còn lại; thứ tự quan trọng: năm tuổi trước số lượng ("17 năm tuổi" không phải 17 đơn vị)
_PHAN = [
    ('ty_le', re.compile(r'(\d[\d.,]*)\s*%', re.I)),
    ('dk', re.compile(r'(?:đường\s+kính|đk|ø|phi|d)\s*(?:thân|gốc)?\s*[:=]?\s*(\d[\d.,]*)\s*(?:cm)?' + _SAU_CHU, re.I)),
    ('cv', re.compile(r'(?:chu\s+vi|cv)\s*(?:thân|gốc)?\s*[:=]?\s*(\d[\d.,]*)\s*(?:cm)?' + _SAU_CHU, re.I)),
    ('vu', re.compile(r'(\d+\s*năm\s*\d+\s*vụ|\d+\s*vụ\s*/\s*năm|\d+\s*vụ)' + _SAU_CHU, re.I)),
    ('tuoi', re.compile(r'(?:(\d+)\s*(?:năm\s+tuổi|tuổi|năm)|(?:năm\s+thứ|tuổi)\s*(\d+))' + _SAU_CHU, re.I)),
    ('kt', _RE_KICH_THUOC),
    ('ngoac', re.compile(r'\(([^()]*)\)')),            # "42m2 (thửa 123)": phần trong ngoặc sau số liệu -> ghi chú
    ('sl', re.compile(r'(' + _SO + r')\s*(' + DON_VI + r')?' + _SAU_CHU, re.I)),
    ('dvt', re.compile(r'(' + DON_VI + r')' + _SAU_CHU, re.I)),
]
_RE_DON_VI_CUOI = re.compile(r'\s+(' + DON_VI + r')$', re.I)
# dòng viết tự nhiên (dùng bộ đọc này thay quy tắc "Tên ␣ ĐVT ␣ Số lượng"): có ":" hoặc có số đo / tuổi / số dính đơn vị
_RE_TU_NHIEN = re.compile(r':|\d\s*(?:m2|m²|m3|m³|ha|cm)(?![^\W\d_])|đường\s+kính|chu\s+vi|\bđk\s*\d|(?<![^\W\d_])d\s*\d|'
                          r'tuổi|năm\s+thứ|\d\s*vụ|\d\s*(?:m\s*)?[x×*]\s*\d', re.I)
_RE_TINH_BANG = re.compile(r'\s*[,(]?\s*(?:tính\s+bằng|tính\s+theo|tương\s+đương(?:\s+với)?|áp\s+(?:giá|dụng)(?:\s+theo)?|'
                           r'theo\s+đơn\s+giá)\s+', re.I)


def _thuong(s: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', str(s or '')).lower().split())


def la_dong_tu_nhien(dong: str) -> bool:
    return bool(_RE_TU_NHIEN.search(str(dong or '')))


def doc_kich_thuoc(o: str) -> tuple | None:
    """Một ô số lượng viết kiểu kích thước / diện tích -> (số lượng, ĐVT, ĐVT tự suy?): '3,7m x 4,3m' -> ('3,7x4,3', 'm2', False),
    '4,7*3,0' -> ('4,7*3,0', 'm2', True) (không ghi đơn vị: dài x rộng là diện tích), '42m2' -> ('42', 'm2', False); khác -> None."""
    s = ' '.join(unicodedata.normalize('NFC', str(o or '')).split())
    m = _RE_KICH_THUOC.fullmatch(s)
    if m:
        return m.group(1) + m.group(2).lower() + m.group(3), _dvt_kich_thuoc(m.group(4)), not m.group(4)
    m = _RE_DIEN_TICH_O.fullmatch(s)
    if m:
        return m.group(1), m.group(2), False
    return None


def _dvt_kich_thuoc(dv: str | None) -> str:
    """Đơn vị viết sau kích thước: "m" (3,7m x 4,3m) / không ghi -> m2; m2 / m² giữ như người dùng gõ."""
    return dv if dv and dv.lower() != 'm' else 'm2'


def _bo_tach(s: str) -> str:
    while True:
        s2 = _DAU_TACH.sub('', s, count=1)
        if s2 == s:
            return s
        s = s2


def _ghi(kq: dict, k: str, m) -> bool:
    """Ghi một phần số liệu vào kq; False nếu trùng phần đã có (số lượng thứ hai, số đo thứ hai…)."""
    if k == 'ty_le':
        if kq['ty_le']:
            return False
        kq['ty_le'] = m.group(1).rstrip('.,') + '%'
    elif k in ('dk', 'cv'):
        if kq['so_do']:
            return False
        # "d" trơn chỉ là đường kính cây khi đứng SAU số lượng ("Tràm cây 1500 d28"); trước số lượng là tên ("Đường ống D110 md 12,5")
        if k == 'dk' and re.match(r'(?i)d\s*\d', m.group(0)) and not kq['so_luong']:
            return False
        kq['so_do'], kq['kieu'] = m.group(1).rstrip('.,'), k
    elif k == 'vu':
        kq['ghi_chu'].append(m.group(1))
    elif k == 'tuoi':
        if kq['tuoi']:
            return False
        kq['tuoi'] = m.group(1) or m.group(2)
    elif k == 'kt':
        if kq['so_luong']:
            return False
        kq['so_luong'] = m.group(1) + m.group(2).lower() + m.group(3)   # công thức (dấu nhân như người dùng gõ): doc_danh_sach tính thành diện tích, giữ ở chú thích ô
        if not kq['dvt']:
            kq['dvt'] = _dvt_kich_thuoc(m.group(4))
            kq['dvt_ngam'] = not m.group(4)
    elif k == 'ngoac':
        kq['ghi_chu'].append(m.group(1).strip())
    elif k == 'sl':
        if kq['so_luong']:
            return False
        kq['so_luong'] = re.sub(r'\s+', '', m.group(1)).rstrip('.,')
        if m.group(2):
            kq['dvt'] = m.group(2)
    elif k == 'dvt':
        if kq['dvt']:
            return False
        kq['dvt'] = m.group(1)
    return True


def _doc_phan(con: str, chat: bool) -> dict | None:
    """Phần số liệu -> dict. chat=True (dòng không có dấu ":"): phải đọc hết - còn chữ lạ / số liệu trùng -> None; chat=False:
    phần không hiểu (tới dấu phẩy kế tiếp) vào ghi chú."""
    kq = dict(so_luong='', dvt='', ty_le='', so_do='', kieu='', tuoi='', ghi_chu=[])
    s = con
    while True:
        s = _bo_tach(s)
        if not s:
            break
        da = False
        for k, mau in _PHAN:
            m = mau.match(s)
            if m and m.end() > 0:
                if _ghi(kq, k, m):
                    s = s[m.end():]
                    da = True
                break
        if da:
            continue
        if chat:
            return None
        m = re.match(r'(?:[^,;]|,(?=\d))+', s)           # tới dấu phẩy ngăn ý ("cao 1,5m": phẩy thập phân không ngắt)
        kq['ghi_chu'].append(m.group(0).strip(' .'))
        s = s[m.end():]
    kq['ghi_chu'] = '; '.join(x for x in kq['ghi_chu'] if x)
    return kq


def tach_dong(dong: str) -> dict | None:
    """Một dòng viết tự nhiên -> dict(ten, dvt, so_luong, ty_le, ghi_chu, so_do, kieu ('dk' / 'cv' / ''), tuoi), hoặc None nếu không
    đọc ra số liệu nào (để bộ đọc cũ "Tên ␣ ĐVT ␣ Số lượng" xử lý)."""
    s = ' '.join(unicodedata.normalize('NFC', str(dong or '')).split()).strip().rstrip('.;')
    if not s:
        return None
    if ':' in s:
        ten, con = s.split(':', 1)
        kq = _doc_phan(con, chat=False)
    else:
        # không có ":" - tách ở số đầu tiên mà từ đó tới cuối dòng là số liệu đọc được ("Tràm cây 1500 d28")
        kq, ten = None, ''
        for m in re.finditer(r'(?<![^\W\d_])(?:\d|(?:đường\s+kính|chu\s+vi|đk|d)\s*\d)', s, re.I):
            if m.start() == 0:
                continue
            if re.search(r'(?:[\d.,]|[+\-*/×(=]\s*|(?<![^\W\d_])x\s*)$', s[:m.start()], re.I):   # giữa phép tính ("Sân m2 3+2*4"): không tách ở đây
                continue
            kq = _doc_phan(s[m.start():], chat=True)
            # không có ":" - số trơn cuối tên chưa chắc là số lượng ("Nhà cấp 4"): phải kèm đơn vị / số đo / tuổi
            if kq is not None and not (kq['dvt'] or kq['so_do'] or kq['tuoi']) and not _RE_DON_VI_CUOI.search(s[:m.start()].strip()):
                kq = None
            if kq is not None:
                ten = s[:m.start()]
                break
    if kq is None:
        return None
    ten = ten.strip(' ,;-')
    m = _RE_DON_VI_CUOI.search(ten)                     # "Tràm cây" / "Nhà tạm m2": đơn vị viết ngay sau tên
    if m and (not kq['dvt'] or kq.pop('dvt_ngam', False)) and len(ten[:m.start()].split()) >= 1:
        kq['dvt'], ten = m.group(1), ten[:m.start()].strip()
    kq.pop('dvt_ngam', None)
    if not ten or not (kq['so_luong'] or kq['so_do'] or kq['tuoi']):
        return None
    kq['ten'] = ten
    return kq


# ---------------------------------------------------------------- tên áp giá ("… tính bằng …")
def ten_ap_gia(ten: str) -> tuple:
    """'Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4' -> ('Nhà 01 tầng kết cấu loại 4', 'Gác để ở'); không có -> (ten, '')."""
    m = _RE_TINH_BANG.search(ten or '')
    if not m or not ten[m.end():].strip():
        return ten, ''
    return ten[m.end():].strip(' )'), ten[:m.start()].strip(' ,(')


# ---------------------------------------------------------------- loài cây
def _chuan_loai(t: str) -> str:
    return re.sub(r'^cây\s+', '', _thuong(re.sub(r'\(.*?\)', ' ', str(t or '')))).strip(' -')


def loai_cay_dk(bang, ten: str) -> str | None:
    """Tên loại trong bảng quy cách đường kính (cay_trong.BangCayDK) của cây gõ ten. So có dấu trước ("tràm" -> "Keo lá tràm", không
    phải "Trám đen"), cây gỗ trước cây cảnh; không có thì so không dấu."""
    q = _chuan_loai(ten)
    if not q:
        return None
    ds = list(bang.loai)

    def uu_tien(t):
        return ('cây cảnh' in t, len(t))
    for dk in (lambda c: c == q,
               lambda c: re.search(r'(^|\s)' + re.escape(q) + r'(\s|$)', c) is not None,
               lambda c: bo_dau(c) == bo_dau(q),
               lambda c: re.search(r'(^|\s)' + re.escape(bo_dau(q)) + r'(\s|$)', bo_dau(c)) is not None):
        ung = [t for t in ds if dk(_chuan_loai(t))]
        if ung:
            return min(ung, key=uu_tien)
    return None


# ---------------------------------------------------------------- năm tuổi
_SO_CHU = {'nhat': 1, 'mot': 1, 'hai': 2, 'ba': 3, 'bon': 4, 'tu': 4, 'nam': 5}


def khoang_tuoi(ten: str):
    """Khoảng năm tuổi (từ, đến - None = trở đi) của mục cây trồng theo tên, hoặc None nếu tên không ghi năm."""
    t = bo_dau(ten)
    t = re.sub(r'nam thu (nhat|mot|hai|ba|bon|tu|nam)\b', lambda m: f'nam thu {_SO_CHU[m.group(1)]}', t)
    m = re.search(r'\(nam thu ([\d,\s]+?)\s*(tro di)?\s*\)', t)          # "(Năm thứ 4,5,6,7,8)" / "(Năm thứ 19 trở đi)"
    if m:
        so = [int(x) for x in re.findall(r'\d+', m.group(1))]
        return (min(so), None if m.group(2) else max(so)) if so else None
    m = re.search(r'tu nam thu (\d+) den nam thu (\d+)', t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(tu |tren |duoi )?(\d+) nam tuoi( tro len)?', t)      # "Trên 5 năm tuổi", "dưới 2 năm tuổi", "từ 3 năm tuổi trở lên"
    if m:
        n = int(m.group(2))
        if m.group(1) == 'duoi ':
            return 0, n - 1
        if m.group(1) == 'tren ':
            return n + 1, None
        if m.group(3):
            return n, None
        return n, n
    m = re.search(r'-\s*nam (?:thu )?(\d+)(?:\s*-\s*(\d+))?\s*(tro di)?\s*$', t)   # "- Năm 1", "- Năm thứ 2", "- Năm thứ 2-3"
    if m:
        a = int(m.group(1))
        return a, None if m.group(3) else int(m.group(2) or a)
    return None


def chon_theo_tuoi(ds_muc: list, ten: str, tuoi) -> object | None:
    """Mục cây trồng của loài ten đúng năm tuổi (quá năm cuối cùng thì lấy khoảng cuối)."""
    from .cay_trong import ten_goc
    try:
        n = int(str(tuoi).strip())
    except ValueError:
        return None
    q = _chuan_loai(ten)
    if not q:
        return None
    co_tuoi = [(m, khoang_tuoi(m.ten)) for m in ds_muc]
    co_tuoi = [(m, k) for m, k in co_tuoi if k is not None]
    for so in (lambda c: c == q, lambda c: bo_dau(c) == bo_dau(q)):
        loai = [(m, k) for m, k in co_tuoi if so(_chuan_loai(ten_goc(m.ten)))]
        if not loai:
            continue
        for m, (a, b) in loai:
            if a <= n and (b is None or n <= b):
                return m
        return max(loai, key=lambda x: x[1][0])[0] if n > max(k[0] for _, k in loai) else min(loai, key=lambda x: x[1][0])[0]
    return None


# ---------------------------------------------------------------- khớp theo từ
def _tu(ten: str) -> list:
    k = re.sub(r'[^0-9a-z ]+', ' ', bo_dau(ten))
    return [str(int(w)) if w.isdigit() else w for w in k.split()]


def khop_theo_tu(dm, ten: str, cac_muc=(2, 3, 7, 4)):
    """(mục, độ giống) - mục có ĐỦ mọi từ của tên (tên >= 2 từ), ít từ thừa nhất: "Nhà 01 tầng kết cấu loại 4" -> "Nhà 01 tầng - Kết
    cấu loại 4"; "Ao nuôi cá ghép" -> "Ao nuôi cá - Nuôi ghép cá các loại (…)". Không có -> None."""
    q = set(_tu(ten))
    if len(q) < 2:
        return None
    tot = None
    for muc in cac_muc:
        for m in dm.muc.get(muc, []):
            c = _tu(m.ten)
            if not q <= set(c):
                continue
            chinh = set(_tu(re.sub(r'\(.*?\)', ' ', m.ten)))
            diem = (len(q & chinh) / max(1, len(chinh)), -len(c))
            if tot is None or diem > tot[1]:
                tot = (m, diem)
    return (tot[0], tot[1][0]) if tot else None


def bo_sung(bo, dm, d: dict, kq):
    """Sau phan_loai_tai_san.BoPhanLoai.phan_loai: chọn loại cây theo đường kính, mục theo năm tuổi, khớp theo từ; ghi vào kq
    (kieu, loai_cay, so_do, khop, loai, do_tin, ly_do). d: dòng của doc_danh_sach / tach_dong."""
    from .phan_loai_tai_san import CAY, NHA, VAT_NUOI, _loai_muc
    ten_gia, ten_tt = ten_ap_gia(d.get('ten', ''))
    if ten_tt:                                          # "Gác để ở tính bằng Nhà 01 tầng…": áp giá theo phần sau
        k2 = bo.phan_loai(ten_gia, d.get('dvt', ''))
        if k2.khop is not None or k2.do_tin >= kq.do_tin:
            kq.khop, kq.loai, kq.do_tin, kq.ty_le_khop = k2.khop, k2.loai, k2.do_tin, k2.ty_le_khop
        kq.ly_do = f'áp giá theo "{ten_gia}"; ' + k2.ly_do
        kq.ghi_them = f'Thực tế: {ten_tt}'
    if d.get('so_do') and d.get('kieu') in ('dk', 'cv') and kq.loai in (CAY, NHA):
        from .cay_trong import BangCayDK
        tl = loai_cay_dk(BangCayDK(dm.muc.get(3, [])), ten_gia)
        if tl:
            kq.loai, kq.khop, kq.kieu, kq.loai_cay, kq.so_do = CAY, None, d['kieu'], tl, d['so_do']
            kq.do_tin = max(kq.do_tin, 0.85)
            kq.ly_do = (f'cây theo {"đường kính" if d["kieu"] == "dk" else "chu vi"} {d["so_do"]} cm -> loại "{tl}" '
                        '(quy cách theo số đo)')
            return kq
    if d.get('tuoi') and kq.loai in (CAY, NHA):
        m = chon_theo_tuoi(dm.muc.get(3, []), ten_gia, d['tuoi'])
        if m is not None:
            kq.loai, kq.khop, kq.ty_le_khop = CAY, m, 1.0
            kq.do_tin = max(kq.do_tin, 0.9)
            kq.ly_do = f'{d["tuoi"]} năm tuổi -> "{m.ten}"'
            return kq
    if kq.khop is None:
        k = khop_theo_tu(dm, ten_gia)
        if k is not None:
            m, r = k
            kq.khop, kq.loai, kq.ty_le_khop = m, _loai_muc(m), r
            kq.do_tin = max(kq.do_tin, 0.6 + 0.3 * r)
            kq.ly_do = f'đủ các từ của tên trong "{m.ten}"' + ('; xem lại mức (thời gian nuôi / định mức)' if kq.loai == VAT_NUOI else '')
            if kq.loai == VAT_NUOI:
                kq.do_tin = min(kq.do_tin, 0.55)        # nhiều mức theo thời gian nuôi: nhắc xem lại (nền vàng)
    return kq
