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
    # "35c/15cm", "04c/25" (biên bản lâm nghiệp: 35 cây đường kính 15 cm) - 1.0.32
    ('c_dk', re.compile(r'(\d+)\s*c\s*/\s*(\d+(?:[.,]\d+)?)\s*(?:cm)?' + _SAU_CHU, re.I)),
    # "ĐK 10-15cm": khoảng đường kính -> lấy cận trên (quy cách "(d >10-15 cm)") - 1.0.32
    ('dk', re.compile(r'(?:đường\s+kính|đk|ø|phi|d)\s*(?:thân|gốc)?\s*[:=]?\s*(\d[\d.,]*)(?:\s*-\s*(\d[\d.,]*))?\s*(?:cm)?'
                      + _SAU_CHU, re.I)),
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
                          r'tuổi|năm\s+thứ|\d\s*vụ|\d\s*(?:m\s*)?[x×*]\s*\d|'
                          r'\d\s*c\s*/\s*\d|trồng\s+(?:vào\s+)?năm\s*\d|năm\s+trồng|sâu\s*\d', re.I)
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
    elif k == 'c_dk':
        if kq['so_luong'] or kq['so_do']:
            return False
        kq['so_luong'], kq['so_do'], kq['kieu'] = str(int(m.group(1))), m.group(2).rstrip('.,'), 'dk'     # "03c" -> 3 cây
        kq['dvt'] = kq['dvt'] or 'cây'
    elif k in ('dk', 'cv'):
        if kq['so_do']:
            return False
        # "d" trơn chỉ là đường kính cây khi đứng SAU số lượng ("Tràm cây 1500 d28"); trước số lượng là tên ("Đường ống D110 md 12,5")
        if k == 'dk' and re.match(r'(?i)d\s*\d', m.group(0)) and not kq['so_luong']:
            return False
        kq['so_do'], kq['kieu'] = m.group(1).rstrip('.,'), k
        if k == 'dk' and m.group(2):                    # khoảng "10-15": cận trên vào quy cách, khoảng gốc giữ ở ghi chú
            kq['so_do'] = m.group(2).rstrip('.,')
            kq['ghi_chu'].append(f'ĐK {m.group(1).rstrip(".,")}-{kq["so_do"]} cm')
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


# ---------------------------------------------------------------- biên bản kiểm đếm thực địa (mẫu QĐ 42, 1.0.32)
_PHI = r'(?:ϕ|Φ|φ|ø|phi(?![^\W\d_]))'
_SO_DO_M = r'\d+(?:[.,]\d+)?\s*(?:cm(?![^\W\d_])|m(?![23²³]|[^\W\d_]))?'
_TICH = _SO_DO_M + r'(?:\s*[x×*]\s*' + _SO_DO_M + r')+'
_CUM = r'(?:\(\s*' + _TICH + r'\s*\)|' + _TICH + r')'
_RE_BIEU_THUC = re.compile(r'(?<![\w.,])(?P<bt>' + _CUM + r'(?:\s*\+\s*' + _CUM + r')*)(?:\s*(?P<dv>m2|m²|m3|m³)(?![^\W\d_]))?',
                           re.I)
_RE_THUA_SO = re.compile(r'(\d+(?:[.,]\d+)?)\s*(cm|m)?', re.I)
_RE_TEN_TRUOC_KT = re.compile(r'(?:\s*[,:(=-]|\s+(?:kt|kích\s+thước|kich\s+thuoc|diện\s+tích|dt)\.?)\s*$', re.I)
_RE_NAM_TRONG = re.compile(r'[\s,;-]*(?:năm\s+trồng|trồng\s+(?:vào\s+)?năm)\s*[:=]?\s*(\d{4})(?!\d)', re.I)
_RE_DK_TEN = re.compile(r'[\s,;-]*(?:đường\s+kính|đk)\s*(?:gốc|thân)?\s*[:=]?\s*(\d+(?:[.,]\d+)?)(?:\s*-\s*(\d+(?:[.,]\d+)?))?'
                        r'\s*cm(?![^\W\d_])', re.I)
_RE_SAU_GIENG = re.compile(r'[\s,;-]*(?:độ\s+)?sâu\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m(?![^\W\d_])', re.I)
_RE_NHIEU_CO = re.compile(r'^(?P<ten>[^:;|\t]+?)\s*:\s*(?P<ds>(?:' + _PHI + r'|D)\s*\d.*)$', re.I)
_RE_MOT_CO = re.compile(r'^(?:' + _PHI + r'|D)\s*(\d+(?:[.,]\d+)?)\s*(mm|cm)?\s*[:=]\s*(.+)$', re.I)


def nam_hien_tai() -> int:
    from datetime import date
    return date.today().year


def _phan_tich_bieu_thuc(bt: str, dv: str = '') -> dict | None:
    """Biểu thức kích thước (đã tách đơn vị cuối) -> {'cong_thuc', 'dvt', 'so_cum', 'so_thua_so'}; mỗi cụm 2-3 thừa số, cùng loại
    (diện tích / thể tích). Cụm 3 thừa số mà thừa số cuối KHÔNG có đơn vị sau hai cạnh có "m" ("7m x 2m x 2") = diện tích x số cái;
    còn lại 3 thừa số = thể tích. Có "cm" -> None (không tự đổi đơn vị)."""
    loai, cong, toi_da = set(), [], 0
    for p in bt.split('+'):
        ts = _RE_THUA_SO.findall(p.strip().strip('()'))
        if not 2 <= len(ts) <= 3 or any(u.lower() == 'cm' for _, u in ts):
            return None
        toi_da = max(toi_da, len(ts))
        if len(ts) == 2 or (not ts[2][1] and any(u for _, u in ts[:2])) or dv.lower() in ('m2', 'm²'):
            loai.add(2)
        else:
            loai.add(3)
        cong.append('x'.join(v for v, _ in ts))
    if dv.lower() in ('m3', 'm³'):
        if 2 in loai and toi_da < 3:
            return None
        loai = {3}
    if len(loai) != 1:
        return None
    ct = cong[0] if len(cong) == 1 else '+'.join(f'({x})' for x in cong)
    return dict(cong_thuc=ct, dvt='m3' if loai.pop() == 3 else 'm2', so_cum=len(cong), so_thua_so=toi_da)


def tinh_bieu_thuc_kich_thuoc(chuoi: str) -> dict | None:
    """Kích thước cán bộ ghi trên biên bản -> {'cong_thuc', 'dvt', 'so_cum', 'so_thua_so'} (công thức tính bằng tien.tinh_cong_thuc):
        '(11m x 3,8m) + (1,3 x 18m) + (16,5 x 1,5m) + (7m x 2m x 2)' -> '(11x3,8)+(1,3x18)+(16,5x1,5)+(7x2x2)', m2 (= 117,95)
        '1,5m x 2,4m x 1,2m' / 'Bể nước 2,0 x 2,0 x 1,2m' -> '1,5x2,4x1,2' / '2,0x2,0x1,2', m3
    Không có biểu thức / lẫn diện tích với thể tích / có "cm" -> None."""
    s = ' '.join(unicodedata.normalize('NFC', str(chuoi or '')).split())
    m = _RE_BIEU_THUC.search(s)
    kt = _phan_tich_bieu_thuc(m.group('bt'), m.group('dv') or '') if m else None
    if kt is not None:
        kt['dau'], kt['cuoi'] = m.start(), m.end()      # vị trí trong chuỗi đã gộp khoảng trắng
    return kt


def tach_dong_qd42(dong: str) -> list:
    """Một dòng biên bản ghi gộp nhiều cỡ -> nhiều dòng: 'Ống nhựa Bình Minh: ϕ 114: 3300m; ϕ 90: 3400m; ϕ 21: 3300m' ->
    ['Ống nhựa Bình Minh Φ114: 3300m', 'Ống nhựa Bình Minh Φ90: 3400m', 'Ống nhựa Bình Minh Φ21: 3300m']. Không phải dòng gộp ->
    [dòng] nguyên văn (giữ cả Tab của ô Excel)."""
    s = ' '.join(unicodedata.normalize('NFC', str(dong or '')).split())
    m = _RE_NHIEU_CO.match(s)
    if m:
        phan = [x.strip() for x in re.split(r'[;|]', m.group('ds')) if x.strip()]
        co = [_RE_MOT_CO.match(x) for x in phan]
        if len(phan) >= 2 and all(co):
            return [f"{m.group('ten').strip()} Φ{x.group(1)}{x.group(2) or ''}: {x.group(3).strip()}" for x in co]
    return [dong] if str(dong or '').strip() else []


def _rut_them(s: str, nam=None) -> tuple:
    """Rút khỏi dòng các cụm biên bản thực địa (đứng ở đâu cũng được): "trồng năm 2012" -> năm tuổi (năm kiểm đếm - năm trồng, ít
    nhất 1), "ĐK gốc 10-15cm" -> số đo (cận trên), "sâu 8m" của giếng -> số lượng m. Trả (dòng còn lại, {khóa: giá trị},
    giếng có độ sâu?)."""
    them = dict(tuoi='', so_do='', kieu='', so_luong='', dvt='', ghi_chu=[])
    m = _RE_NAM_TRONG.search(s)
    if m:
        y, n = int(m.group(1)), int(nam or nam_hien_tai())
        if 1900 < y <= n:
            them['tuoi'] = str(max(1, n - y))
            them['ghi_chu'].append(f'trồng năm {y}')
            s = (s[:m.start()] + s[m.end():]).strip()
    m = _RE_DK_TEN.search(s)
    if m:
        them['so_do'], them['kieu'] = (m.group(2) or m.group(1)), 'dk'
        if m.group(2):
            them['ghi_chu'].append(f'ĐK gốc {m.group(1)}-{m.group(2)} cm')
        s = (s[:m.start()] + s[m.end():]).strip()
    gieng = False
    if 'gieng' in bo_dau(s).lower():
        m = _RE_SAU_GIENG.search(s)
        if m:
            them['so_luong'], them['dvt'], gieng = m.group(1), 'm', True
            them['ghi_chu'].append(f'sâu {m.group(1)} m')
            s = (s[:m.start()] + s[m.end():]).strip()
    return s, them, gieng


def _tach_bieu_thuc(s: str) -> dict | None:
    """Dòng có biểu thức kích thước nhiều cụm / 3 thừa số -> kết quả tach_dong (công thức ở so_luong); dòng hai thừa số đơn ("4 x 6,7m")
    để bộ đọc cũ xử lý như trước."""
    kt = tinh_bieu_thuc_kich_thuoc(s)
    if kt is None or (kt['so_cum'] == 1 and kt['so_thua_so'] < 3):
        return None
    ten = s[:kt['dau']]
    while True:
        t2 = _RE_TEN_TRUOC_KT.sub('', ten)
        if t2 == ten:
            break
        ten = t2
    kq = _doc_phan(s[kt['cuoi']:], chat=False)
    kq['so_luong'], kq['dvt'], kq['ten'] = kt['cong_thuc'], kt['dvt'], ten.strip(' ,;:-')
    return kq if kq['ten'] else None


def tach_dong(dong: str, nam=None) -> dict | None:
    """Một dòng viết tự nhiên -> dict(ten, dvt, so_luong, ty_le, ghi_chu, so_do, kieu ('dk' / 'cv' / ''), tuoi), hoặc None nếu không
    đọc ra số liệu nào (để bộ đọc cũ "Tên ␣ ĐVT ␣ Số lượng" xử lý). nam: năm kiểm đếm để đổi "trồng năm …" ra năm tuổi (mặc định năm
    nay)."""
    s = ' '.join(unicodedata.normalize('NFC', str(dong or '')).split()).strip().rstrip('.;')
    if not s:
        return None
    s, them, gieng = _rut_them(s, nam)
    if gieng:                                           # "Giếng khoan CN: ϕ 140 sâu 85m": độ sâu là khối lượng, phần còn lại là tên
        kq = dict(so_luong='', dvt='', ty_le='', so_do='', kieu='', tuoi='', ghi_chu='', ten=' '.join(s.replace(':', ' ').split()))
        return _gop_them(kq, them) if kq['ten'] else None
    kq = _tach_bieu_thuc(s)
    if kq is not None:
        return _gop_them(kq, them)
    kq = _tach_dong_cu(s)
    if kq is None and any(them[k] for k in ('tuoi', 'so_do')) and s:
        kq = dict(so_luong='', dvt='', ty_le='', so_do='', kieu='', tuoi='', ghi_chu='', ten=s.strip(' ,;:-'))
    return _gop_them(kq, them) if kq is not None and kq['ten'] else None


def _gop_them(kq: dict, them: dict) -> dict:
    for k in ('tuoi', 'so_do', 'kieu', 'so_luong', 'dvt'):
        if them[k] and not kq.get(k):
            kq[k] = them[k]
    gc = kq.get('ghi_chu') or ''
    kq['ghi_chu'] = '; '.join(x for x in [*them['ghi_chu'], *([gc] if isinstance(gc, str) else gc)] if x)
    return kq


def _tach_dong_cu(s: str) -> dict | None:
    """Bộ đọc trước 1.0.32 (dòng đã rút năm trồng / ĐK / độ sâu)."""
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


def _tu_co_dau(ten: str) -> list:
    k = re.sub(r'[^\w ]+', ' ', unicodedata.normalize('NFC', str(ten or '')).lower())
    return [str(int(w)) if w.isdigit() else w for w in k.split()]


def khop_theo_tu(dm, ten: str, cac_muc=(2, 3, 7, 4)):
    """(mục, độ giống) - mục có ĐỦ mọi từ của tên (tên >= 2 từ), ít từ thừa nhất: "Nhà 01 tầng kết cấu loại 4" -> "Nhà 01 tầng - Kết
    cấu loại 4"; "Ao nuôi cá ghép" -> "Ao nuôi cá - Nuôi ghép cá các loại (…)". Không có -> None.
    1.0.32: tên gõ CÓ DẤU thì so có dấu ("Cọ dầu" không khớp "Cây đậu cô ve" - bỏ dấu thì cùng hai từ "co", "dau")."""
    q = set(_tu(ten))
    if len(q) < 2:
        return None
    co_dau = bo_dau(ten).lower() != unicodedata.normalize('NFC', str(ten or '')).lower()
    q_dau = set(_tu_co_dau(ten))
    tot = None
    for muc in cac_muc:
        for m in dm.muc.get(muc, []):
            c = _tu(m.ten)
            if not q <= set(c):
                continue
            if co_dau and not q_dau <= set(_tu_co_dau(m.ten)):
                continue
            chinh = set(_tu(re.sub(r'\(.*?\)', ' ', m.ten)))
            diem = (len(q & chinh) / max(1, len(chinh)), -len(c))
            if tot is None or diem > tot[1]:
                tot = (m, diem)
    return (tot[0], tot[1][0]) if tot else None


def khop_tu_hiem(dm, ten: str, muc: int = 2, dai_toi_thieu: int = 6):
    """(mục, từ) khi tên có một từ dài (>= dai_toi_thieu chữ, không dấu) chỉ xuất hiện ở ĐÚNG MỘT mục của bộ đơn giá: "Sân gạch Terrazzo"
    -> "Nền lát gạch con sâu, gạch Terrazzo". Nhiều mục / không có -> None."""
    ds = dm.muc.get(muc, [])
    for w in sorted({x for x in _tu(ten) if len(x) >= dai_toi_thieu and not x.isdigit()}, key=len, reverse=True):
        co = [m for m in ds if w in _tu(m.ten)]
        if len(co) == 1:
            return co[0], w
    return None


# ---------------------------------------------------------------- ống / giếng theo đường kính (1.0.32)
_RE_DK_DONG = re.compile(r'(?:' + _PHI + r'|(?<![^\W\d_])d)\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?(?![^\W\d_])', re.I)
_VAT_LIEU_ONG = (('nhua', ('nhua', 'pvc', 'upvc', 'hdpe', 'ppr', 'binh minh', 'tien phong')), ('amiang', ('amiang',)),
                 ('sanh', ('sanh',)), ('cong', ('ong cong', 'be tong')))


def _mm(so: str, dv: str, mac_dinh_m: bool) -> float:
    """Số đo đường kính -> mm: '1' + 'm' -> 1000; '140' -> 140; không ghi đơn vị: số < 10 là mét (ϕ 1, ϕ 0,8) - mac_dinh_m."""
    v = float(so.replace(',', '.'))
    dv = (dv or '').lower()
    if dv == 'm' or (not dv and mac_dinh_m and v < 10):
        return v * 1000
    return v * 10 if dv == 'cm' else v


def _khoang_dk_muc(ten: str):
    """Khoảng đường kính (mm) ghi trong tên mục bộ đơn giá: 'Φ0,8 - 1m' -> (800, 1000); '(ống Φ49 - Φ60 mm)' -> (49, 60);
    '(ống > Φ114 mm)' -> (114 không gồm, vô cùng); 'Φ60 mm' / 'uPVC D114' -> (60, 60) / (114, 114). Không có -> None."""
    t = unicodedata.normalize('NFC', ten).replace('φ', 'Φ').replace('ϕ', 'Φ')
    m = re.search(r'Φ\s*(\d+(?:[.,]\d+)?)\s*(mm|m)?\s*-\s*Φ?\s*(\d+(?:[.,]\d+)?)\s*(mm|m)(?![^\W\d_])', t)
    if m:
        dv = m.group(2) or m.group(4)
        return _mm(m.group(1), dv, False), _mm(m.group(3), m.group(4), False), False
    m = re.search(r'>\s*Φ\s*(\d+(?:[.,]\d+)?)\s*(mm|m)?', t)
    if m:
        return _mm(m.group(1), m.group(2) or 'mm', False), float('inf'), True
    m = re.search(r'(?:Φ|(?<![^\W\d_])D)\s*(\d+(?:[.,]\d+)?)\s*(mm|m)?(?![^\W\d_])', t)
    if m:
        v = _mm(m.group(1), m.group(2) or 'mm', False)
        return v, v, False
    return None


def khop_duong_kinh(dm, ten: str, so_luong_m: str = ''):
    """Ống nước / ống cống / giếng ghi đường kính -> (mục bộ đơn giá, chắc chắn?, lý do) theo TÊN + KHOẢNG ĐƯỜNG KÍNH trong bộ đơn
    giá đang dùng (không ghi cứng mã): 'Ống nhựa Bình Minh Φ114' -> 'Ống dẫn nước nhựa uPVC D114'; cỡ không có trong bộ -> cỡ lớn kế
    tiếp, chắc chắn = False (nhắc xem lại); 'Giếng đào ϕ 1m' (sâu 8 m) -> 'Giếng nước Φ0,8 - 1m, sâu < 10m'; 'Giếng khoan CN ϕ 140' ->
    'Giếng khoan công nghiệp (ống > Φ114 mm)'. Không phải ống / giếng hoặc không có cỡ phù hợp -> None."""
    t = bo_dau(ten).lower()
    m = _RE_DK_DONG.search(unicodedata.normalize('NFC', ten))
    if m is None:
        return None
    gieng = 'gieng' in t
    if not gieng and not re.search(r'(^|\s)ong(\s|$)', t):
        return None
    d = _mm(m.group(1), m.group(2), gieng)
    ds = dm.muc.get(2, [])
    if gieng:
        khoan = 'khoan' in t
        cn = 'cong nghiep' in t or re.search(r'(^|\s)cn(\s|$)', t) is not None
        pool = [x for x in ds if bo_dau(x.ten).lower().startswith('gieng') and ('khoan' in bo_dau(x.ten).lower()) == khoan
                and ('tha ong' in bo_dau(x.ten).lower()) == ('tha ong' in t)]      # giếng thả ống ciment tính theo cái
        if khoan and (cn or 'thu cong' in t):
            pool = [x for x in pool if ('cong nghiep' in bo_dau(x.ten).lower()) == cn]
    else:
        vl = next((k for k, tu in _VAT_LIEU_ONG if any(w in t for w in tu)), 'nhua' if 'ong nuoc' in t else None)
        if vl is None:
            return None
        tu_vl = dict(_VAT_LIEU_ONG)[vl]
        pool = [x for x in ds if bo_dau(x.ten).lower().startswith('ong') and any(w in bo_dau(x.ten).lower() for w in tu_vl)]
    try:
        sau = float(str(so_luong_m).replace(',', '.')) if so_luong_m else None
    except ValueError:
        sau = None
    ung = []
    for x in pool:
        k = _khoang_dk_muc(x.ten)
        if k is None:
            continue
        a, b, ho = k
        gh = re.search(r'sâu\s*<\s*(\d+(?:[.,]\d+)?)\s*m', x.ten)
        if gieng and sau is not None and gh and sau >= float(gh.group(1).replace(',', '.')):
            continue
        ung.append((x, a, b, ho))
    trong = [u for u in ung if (u[1] < d if u[3] else u[1] <= d) and d <= u[2]]
    if trong:
        x = min(trong, key=lambda u: u[2] - u[1])[0]
        return x, True, f'đường kính {m.group(0).strip()} thuộc "{x.ten}"'
    lon = [u for u in ung if u[1] == u[2] and u[1] > d]
    if lon and not gieng:
        x = min(lon, key=lambda u: u[1])[0]
        return x, False, f'không có cỡ {m.group(0).strip()} trong bộ đơn giá - áp cỡ lớn kế tiếp "{x.ten}": xem lại'
    return None


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
    if kq.khop is None or getattr(kq, 'ty_le_khop', 0) < 1:
        k = khop_duong_kinh(dm, ten_gia, d.get('so_luong', '') if bo_dau(d.get('dvt', '')).lower() in ('m', 'md') else '')
        if k is not None:                               # ống / giếng theo đường kính (biên bản QĐ 42) - 1.0.32
            m, chac, ly_do = k
            kq.khop, kq.loai, kq.ty_le_khop = m, NHA, (1.0 if chac else 0.7)
            kq.do_tin = 0.9 if chac else 0.55           # không chắc: nền vàng, nhắc xem lại
            kq.ly_do = ly_do
            if not chac:
                kq.ghi_them = '; '.join(x for x in (kq.ghi_them, f'Thực tế: {ten_gia}') if x)
            return kq
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
    if kq.khop is None and kq.loai == NHA:
        k = khop_tu_hiem(dm, ten_gia)
        if k is not None:                               # "Sân gạch Terrazzo" -> mục duy nhất có chữ "terrazzo" (1.0.32)
            kq.khop, kq.ty_le_khop = k
            kq.do_tin = 0.6
            kq.ly_do = f'chữ "{k[1]}" chỉ có ở "{k[0].ten}": xem lại'
            kq.ty_le_khop = 0.6
    if kq.khop is None and re.search(r'(^|\s)ho nuoc(\s|$)', bo_dau(ten_gia).lower()):
        # biên bản ghi "hồ nước" cho bể nước xây (bộ đơn giá: "Bể nước xây gạch…"; "Hồ chứa" là hố phân / hầm cầu) - 1.0.32
        ten2 = re.sub(r'(?i)hồ\s+nước|ho\s+nuoc', 'Bể nước', ten_gia)
        k2 = bo.phan_loai(ten2, d.get('dvt', ''))
        if k2.khop is not None:
            kq.khop, kq.loai, kq.ty_le_khop = k2.khop, k2.loai, k2.ty_le_khop
            kq.do_tin = min(k2.do_tin, 0.7)
            kq.ly_do = '"hồ nước" = bể nước; ' + k2.ly_do
    return kq
