"""Số tiền, diện tích, đơn giá: tính bằng Decimal và làm tròn giống hàm ROUND của Excel."""
from __future__ import annotations
import re
import functools
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

KHONG = Decimal(0)


def D(x) -> Decimal:
    """Chuyển giá trị bất kỳ (số, chuỗi '1.480.500', '143,8', None) thành Decimal; rỗng -> 0."""
    if x is None:
        return KHONG
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        return Decimal(int(x))
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, float):
        return Decimal(repr(x))          # 143.8 -> '143.8' (không lấy đuôi nhị phân)
    if type(x) is str:
        return _d_chuoi(x)
    return _d_chuoi_goc(str(x))


@functools.lru_cache(maxsize=1 << 16)
def _d_chuoi(x: str) -> Decimal:
    """Chuỗi -> Decimal, nhớ kết quả (Decimal bất biến): số liệu đọc từ CSDL lặp lại rất nhiều (tải lại 3.000 hộ: ~440.000 lần
    đổi số, phần lớn trùng chuỗi). Lỗi (ValueError) không được nhớ."""
    return _d_chuoi_goc(x)


def _d_chuoi_goc(x: str) -> Decimal:
    s = str(x).strip().replace(' ', '').replace(' ', '')
    if s == '':
        return KHONG
    # kiểu Việt Nam: 1.480.500 hoặc 143,8
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f'không đọc được số: {x!r}')
    # Decimal nhận cả "nan", "inf", "1_000": gõ vào ô số lượng thành vô cực / NaN (NaN so sánh ném InvalidOperation, không phải LoiNhap)
    if not d.is_finite() or '_' in s:
        raise ValueError(f'không đọc được số: {x!r}')
    return d


_RE_NGHIN_CHAM = re.compile(r'[-+]?[1-9]\d{0,2}(\.\d{3})+')        # 1.070 / 2.500.000: dấu chấm ngăn nghìn (không bắt 0.125)
_RE_NGHIN_PHAY = re.compile(r'[-+]?[1-9]\d{0,2}(,\d{3}){2,}')      # 1,500,000 kiểu Anh (từ 2 nhóm: "1,500" vẫn là 1,5)


def doc_so_vn(x) -> Decimal:
    """Số NGƯỜI DÙNG GÕ hoặc ô chữ trong file Excel / Word / PDF -> Decimal, một quy tắc chung cho mọi chỗ nhập liệu:
    '1.070' = 1.070 (chấm ngăn nghìn), '2.500.000', '1.070,5' = 1070,5, '12,5' = 12,5, '0.125' / '12.5' = số lẻ dấu chấm,
    '1,500,000' = 1500000. Sai -> ValueError.
    Khác D(): D đọc chuỗi LƯU TRONG CSDL (tien.chuoi ghi '1.07' cho 1,07) - không dùng D cho chữ người gõ (trước đây '1.070' gõ
    vào ô diện tích Excel thành 1,07 m², '1.070,5' ở số tiền quyết định thành 10.705)."""
    if not isinstance(x, str):
        return D(x)
    s = x.strip().replace(' ', '').replace(' ', '')
    if _RE_NGHIN_CHAM.fullmatch(s):
        s = s.replace('.', '')
    elif _RE_NGHIN_PHAY.fullmatch(s):
        s = s.replace(',', '')
    return D(s)


def _so_trong_cong_thuc(t: str) -> Decimal:
    """Một số trong công thức: cùng quy tắc doc_so_vn (1.480.500 / 4,2 / 1.000,5 / 4.2)."""
    try:
        return doc_so_vn(t)
    except ValueError:
        raise ValueError(f'không đọc được số "{t}"') from None


def la_cong_thuc(s) -> bool:
    """Chuỗi người dùng gõ có phải công thức (=4,2*5,7 / 12+3,5 / (10-2)x3) chứ không phải một số."""
    import re
    s = str(s or '').strip()
    return s.startswith('=') or bool(re.search(r'[+*/x×:()]|\d\s*-', s.lower()))


def tinh_cong_thuc(s) -> Decimal:
    """Tính công thức cộng, trừ, nhân, chia, ngoặc: '=4,2*5,7' -> 23,94; '12x3 + 1,5' -> 37,5; '50%*200' -> 100.
    Nhân: * x × ; chia: / : ; số kiểu Việt Nam (dấu phẩy thập phân). Lỗi -> ValueError (thông báo tiếng Việt)."""
    import re
    s = str(s or '').strip().lstrip('=').strip().lower()
    if not s:
        raise ValueError('công thức trống')
    tok = re.findall(r'\d[\d.,]*|[-+*/x×:()%]|\S', s)
    vi_tri = [0]

    def xem():
        return tok[vi_tri[0]] if vi_tri[0] < len(tok) else None

    def lay():
        t = xem()
        vi_tri[0] += 1
        return t

    def bieu_thuc():
        v = so_hang()
        while xem() in ('+', '-'):
            v = v + so_hang() if lay() == '+' else v - so_hang()
        return v

    def so_hang():
        v = thua_so()
        while xem() in ('*', 'x', '×', '/', ':'):
            dau = lay()
            w = thua_so()
            if dau in ('/', ':'):
                if w == 0:
                    raise ValueError('chia cho 0')
                v = v / w
            else:
                v = v * w
        return v

    def thua_so():
        t = lay()
        if t in ('-', '+'):
            v = thua_so()
            return -v if t == '-' else v
        if t == '(':
            v = bieu_thuc()
            if lay() != ')':
                raise ValueError('thiếu dấu ")"')
        elif t is not None and t[0].isdigit():
            v = _so_trong_cong_thuc(t)
        elif t is None:                             # "4*5+": trước đây báo 'ký tự "" không hợp lệ'
            raise ValueError('công thức thiếu số ở cuối')
        else:
            raise ValueError(f'ký tự "{t}" không hợp lệ')
        if xem() == '%':
            lay()
            v = v / 100
        return v

    v = bieu_thuc()
    if xem() is not None:
        raise ValueError(f'ký tự "{xem()}" không hợp lệ')
    return v


def co_so(x) -> bool:
    """x có phải một số (không rỗng) không."""
    if x is None:
        return False
    try:
        D(x)
        return str(x).strip() != ''
    except ValueError:
        return False


def lam_tron(x, so_chu_so: int = 0) -> Decimal:
    """ROUND(x, so_chu_so) của Excel: làm tròn nửa xa số 0; so_chu_so âm = làm tròn hàng chục, trăm, nghìn..."""
    x = D(x)
    mau = Decimal(1).scaleb(-so_chu_so)          # -3 -> 1E+3
    q = (abs(x) / mau).quantize(Decimal(1), rounding=ROUND_HALF_UP) * mau
    q = q if x >= 0 else -q
    return q.quantize(Decimal(1)) if so_chu_so <= 0 else q


def chuoi(x) -> str:
    """Decimal -> chuỗi lưu CSDL (bỏ số 0 thừa, không dùng dạng 1E+3)."""
    x = D(x)
    s = format(x.normalize(), 'f')
    return '0' if s in ('-0', '') else s


def vn(x, so_le: int = 0) -> str:
    """Định dạng số kiểu Việt Nam: 1.480.500 ; 143,8"""
    x = D(x)
    if so_le == 0:
        s = f'{lam_tron(x, 0):,.0f}'
        return s.replace(',', '.')
    s = f'{x:,.{so_le}f}'
    return s.replace(',', '#').replace('.', ',').replace('#', '.')


def vn_gon(x) -> str:
    """Số tiền gọn cho thẻ số liệu (0.9.23): 185.412.000.000 -> "185,4 tỷ"; 23.500.000 -> "23,5 triệu"; dưới 1 triệu: vn().
    Chỉ để xem nhanh - số đầy đủ ở chú thích / bảng."""
    x = D(x)
    for nguong, ten in ((D(10) ** 9, 'tỷ'), (D(10) ** 6, 'triệu')):
        # 999.960.000 làm tròn 1 chữ số lẻ thành "1.000,0 triệu": so sau khi làm tròn để lên bậc tỷ ("1,0 tỷ")
        if abs(x) >= nguong or (ten == 'tỷ' and abs(lam_tron(x / 10 ** 6, 1)) >= 1000):
            return f'{vn(x / nguong, 1)} {ten}'
    return vn(x)


def phan_tram(phan, tong) -> str:
    """Tỷ lệ phần / tổng kiểu VN cho thẻ số liệu (17/10/2026): 49/60 -> "81,7%"; tròn -> "50%"; tổng 0 -> "0%". Decimal, không float."""
    tong = D(tong)
    if tong == 0:
        return '0%'
    p = lam_tron(D(phan) * 100 / tong, 1)
    return f'{vn(p)}%' if p == p.to_integral_value() else f'{vn(p, 1)}%'


def so_vn(x) -> str:
    """Số trong câu chữ: 410,6 ; 135.000 (tự bỏ phần lẻ khi là số nguyên)."""
    x = D(x)
    if x == x.to_integral_value():
        return vn(x)
    le = min(max(-x.normalize().as_tuple().exponent, 1), 4)
    return vn(x, le)


# cột Số lượng / Khối lượng / Diện tích - định dạng kế toán (người dùng 15/10/2026): tài sản (mục 2 nhà, công trình) "*,00"; đất,
# cây, vật nuôi, chính sách hỗ trợ và số lượng khác "*,0". Số có nhiều chữ số lẻ hơn (ha: 0,0325) hiện đủ, tối đa 4. Một nguồn cho
# màn hình (so_luong_vn) và mọi file Excel (khái toán, bản in chi tiết, đối chiếu). Trước đây khái toán dùng '#,##0.##' -> số tròn
# in "46," / "1.453," (dấu thập phân treo)
DINH_DANG_SO_LUONG = '#,##0.0###'
DINH_DANG_SO_LUONG_TAI_SAN = '#,##0.00##'
MUC_TAI_SAN = 2                                         # mục 2 (nhà, công trình) - cùng số ở phương án hộ và khái toán


def le_so_luong(muc=None) -> int:
    """Số chữ số thập phân tối thiểu của cột số lượng theo mục: tài sản 2, còn lại 1."""
    return 2 if muc == MUC_TAI_SAN else 1


def dinh_dang_so_luong(muc=None) -> str:
    """number_format Excel của cột số lượng theo mục."""
    return DINH_DANG_SO_LUONG_TAI_SAN if muc == MUC_TAI_SAN else DINH_DANG_SO_LUONG


def so_luong_vn(x, muc=None) -> str:
    """Số lượng trên màn hình (kiểu kế toán, cùng dinh_dang_so_luong): tài sản "20,00" / "1.250,00", mục khác "16,0" / "1.453,0";
    số có nhiều chữ số lẻ hơn (35,155; ha 0,0325) hiện đủ (tối đa 4) để khớp thành tiền đang tính."""
    x = D(x)
    le = min(max(-x.normalize().as_tuple().exponent, le_so_luong(muc)), 4)
    return vn(x, le)


_CHU_SO = ['không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín']


def _doc_ba_so(n: int, day_du: bool) -> str:
    """Đọc nhóm 3 chữ số (0-999); day_du: nhóm không đứng đầu nên đọc cả 'không trăm', 'linh'."""
    tram, chuc, dv = n // 100, n // 10 % 10, n % 10
    t = []
    if tram or day_du:
        t += [_CHU_SO[tram], 'trăm']
    if chuc > 1:
        t += [_CHU_SO[chuc], 'mươi']
        if dv == 1:
            t.append('mốt')
        elif dv == 5:
            t.append('lăm')
        elif dv == 4:
            t.append('tư')
        elif dv:
            t.append(_CHU_SO[dv])
    elif chuc == 1:
        t.append('mười')
        if dv == 5:
            t.append('lăm')
        elif dv:
            t.append(_CHU_SO[dv])
    elif dv:
        if tram or day_du:
            t.append('linh')
        t.append(_CHU_SO[dv])
    return ' '.join(t)


def tien_bang_chu(x, cham: bool = False) -> str:
    """Số tiền (làm tròn đến đồng) bằng chữ: 1.480.500 -> 'Một triệu bốn trăm tám mươi nghìn năm trăm đồng'.
    cham=True: kết thúc dấu chấm như văn bản hành chính ("… đồng.") - nơi gọi cũ tự thêm dấu chấm nên mặc định không có."""
    n = int(lam_tron(x, 0))
    if n == 0:
        return 'Không đồng' + ('.' if cham else '')
    am, n = n < 0, abs(n)
    nhom = []
    while n:
        nhom.append(n % 1000)
        n //= 1000
    don_vi = ['', 'nghìn', 'triệu', 'tỷ']
    t = []
    for i in range(len(nhom) - 1, -1, -1):
        g = nhom[i]
        if g == 0:
            if i % 3 == 0 and i and t and t[-1] != 'tỷ':      # hàng tỷ, tỷ tỷ... vẫn đọc tên đơn vị
                t.append('tỷ')
            continue
        t.append(_doc_ba_so(g, day_du=i < len(nhom) - 1))
        dv = don_vi[i % 3] if i % 3 else ('tỷ' if i else '')
        if i and i % 3 == 0:
            dv = 'tỷ'
        if dv:
            t.append(dv)
    s = ' '.join(x for x in t if x)
    s = ('âm ' if am else '') + s + ' đồng' + ('.' if cham else '')
    return s[0].upper() + s[1:]
