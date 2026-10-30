"""Cây trồng: quy cách đường kính <-> chu vi, mật độ trồng (cây trong / ngoài mật độ); tài sản trong / ngoài ranh thu hồi.

Đơn giá cây lâm nghiệp, cây cảnh ghi quy cách theo đường kính thân ("Sao đen (d >15-18 cm)", "Si cảnh - 10cm < Đk thân ≤ 20cm…"),
còn khi kiểm đếm thường đo chu vi: chu vi = π × đường kính. Mật độ cây ăn trái ghi ở ghi chú danh mục ("Mật độ 210 cây/ha");
bảng quy_chuan_mat_do của dự án ghi đè mật độ / tỷ lệ bồi thường phần ngoài mật độ (không thuộc danh mục khóa).
"""
from __future__ import annotations
import functools

import math
import re
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from fractions import Fraction

from . import csdl
from .lap_pa import bo_dau
from .tien import D, KHONG, chuoi, doc_so_vn, so_vn

PI = Decimal('3.14159265358979')


# ---------------------------------------------------------------- đường kính <-> chu vi
@dataclass(frozen=True)
class KhoangDK:
    """Khoảng đường kính thân (cm) của một mục danh mục; None = không giới hạn phía đó."""
    tu: Decimal | None
    den: Decimal | None
    gom_tu: bool = False            # tu ≤ d (True) hay tu < d (False)
    gom_den: bool = True            # d ≤ den (True) hay d < den (False)

    def chua(self, d: Decimal) -> bool:
        if self.tu is not None and (d < self.tu or (d == self.tu and not self.gom_tu)):
            return False
        if self.den is not None and (d > self.den or (d == self.den and not self.gom_den)):
            return False
        return True

    def mo_ta(self, he=Decimal(1), don_vi='cm') -> str:
        def f(x):
            return so_vn((x * he).quantize(Decimal('0.1')))
        if self.tu is not None and self.den is not None:
            return f'{"≥" if self.gom_tu else ">"} {f(self.tu)} đến {"≤" if self.gom_den else "<"} {f(self.den)} {don_vi}'
        if self.tu is not None:
            return f'{"≥" if self.gom_tu else ">"} {f(self.tu)} {don_vi}'
        if self.den is not None:
            return f'{"≤" if self.gom_den else "<"} {f(self.den)} {don_vi}'
        return ''


_SO = r'(\d+(?:[.,]\d+)?)'


def _d(s) -> Decimal:
    return D(str(s).replace(',', '.'))


def khoang_duong_kinh(ten: str):
    """KhoangDK theo tên mục danh mục, hoặc None nếu tên không ghi đường kính thân (chậu kiểng: không tính)."""
    return _khoang_duong_kinh(' '.join(str(ten or '').split()))


@functools.lru_cache(maxsize=32768)
def _khoang_duong_kinh(t: str):
    if re.search(r'(?i)chậu', t):
        return None
    m = re.search(r'\(\s*d\s*([<>]=?|≤|≥)?\s*' + _SO + r'\s*(?:-\s*' + _SO + r')?\s*cm\s*\)', t, re.I)
    if m:
        dau, a, b = m.group(1) or '', _d(m.group(2)), m.group(3)
        if b is not None:                                   # (d >21-24 cm): 21 < d ≤ 24
            return KhoangDK(a, _d(b), gom_tu=False, gom_den=True)
        if dau in ('<', '≤', '<='):
            return KhoangDK(None, a, gom_den=dau != '<')
        return KhoangDK(a, None, gom_tu=dau in ('≥', '>='))
    dk = r'(?:đk|đường kính)\s*(?:thân)?'
    m = re.search(_SO + r'\s*cm\s*(<|≤|<=)\s*' + dk + r'\s*(<|≤|<=)\s*' + _SO + r'\s*cm', t, re.I)
    if m:
        return KhoangDK(_d(m.group(1)), _d(m.group(4)), gom_tu=m.group(2) != '<', gom_den=m.group(3) != '<')
    m = re.search(dk + r'\s*(<|≤|<=|>|≥|>=)\s*' + _SO + r'\s*cm', t, re.I)
    if m:
        dau, a = m.group(1), _d(m.group(2))
        if dau in ('<', '≤', '<='):
            return KhoangDK(None, a, gom_den=dau != '<')
        return KhoangDK(a, None, gom_tu=dau in ('≥', '>='))
    return None


def ten_goc(ten: str) -> str:
    """Tên loại cây bỏ phần quy cách: 'Sao đen (d >15-18 cm)' -> 'Sao đen'; 'Si cảnh - 10cm < Đk…' -> 'Si cảnh';
    'cây bưởi - Năm thứ 1' -> 'cây bưởi'."""
    t = ' '.join(str(ten or '').split())
    t = re.sub(r'\s*\(\s*d\s*[^)]*\)\s*$', '', t)
    t = re.split(r'\s+-\s+', t)[0]
    return t.strip()


def chu_vi_sang_duong_kinh(chu_vi) -> Decimal:
    return (D(chu_vi) / PI).quantize(Decimal('0.01'))


def duong_kinh_sang_chu_vi(dk) -> Decimal:
    return (D(dk) * PI).quantize(Decimal('0.1'))


def mo_ta_chu_vi(ten: str) -> str:
    """Quy cách đổi sang chu vi để nhập liệu: 'chu vi > 47,1 đến ≤ 56,5 cm' (trống nếu tên không ghi đường kính)."""
    k = khoang_duong_kinh(ten)
    return ('chu vi ' + k.mo_ta(PI)) if k else ''


def ten_loai_dk(ten: str) -> str:
    """Tên nhóm để chọn theo chu vi: cây ghi '(d …)' (cây lâm nghiệp) và cây ghi 'Đk thân' (cây cảnh) cùng tên được tách riêng."""
    goc = ten_goc(ten)
    return goc if re.search(r'\(\s*d\s*[<>≤≥=]?\s*\d', str(ten or '')) else f'{goc} (cây cảnh, theo Đk thân)'


class BangCayDK:
    """Các mục cây trồng ghi đường kính, gom theo loại cây (để chọn mục theo chu vi đo được)."""

    def __init__(self, ds_muc: list):
        self.loai = {}                                      # tên nhóm -> [(KhoangDK, mục)]
        for m in ds_muc:
            k = khoang_duong_kinh(m.ten)
            if k is not None:
                self.loai.setdefault(ten_loai_dk(m.ten), []).append((k, m))

    def ten_loai(self, tu_khoa: str = '') -> list:
        tu = bo_dau(tu_khoa).split()
        return sorted((t for t in self.loai if all(x in bo_dau(t) for x in tu)), key=lambda t: bo_dau(t))

    def tim(self, ten_loai: str, chu_vi):
        """Mục danh mục ứng với chu vi đo được (cm), hoặc None nếu không khoảng nào chứa."""
        d = D(chu_vi) / PI
        for k, m in self.loai.get(ten_loai, []):
            if k.chua(d):
                return m
        return None


def doc_ds_chu_vi(text: str) -> list:
    """'45, 52 x3; 60*2' / mỗi dòng một số -> [(chu vi, số cây)]. Lỗi -> ValueError (thông báo tiếng Việt)."""
    kq = []
    for phan in re.split(r'[;,\n]+', str(text or '')):
        p = phan.strip().lower().replace('cm', '')
        if not p:
            continue
        m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*(?:[x×*]\s*(\d+))?', p)
        if not m:
            raise ValueError(f'Không đọc được "{phan.strip()}": ghi chu vi (cm), có thể kèm số cây, ví dụ 45 hoặc 52x3.')
        cv = _d(m.group(1))
        if cv <= 0:
            raise ValueError('Chu vi phải lớn hơn 0.')
        kq.append((cv, int(m.group(2) or 1)))
    return kq


def gom_theo_kich_thuoc(bang: BangCayDK, ten_loai: str, ds: list, la_duong_kinh: bool = False) -> tuple:
    """Như gom_theo_chu_vi; la_duong_kinh: các số đo là đường kính thân (cm) thay vì chu vi.
    Trả ([(mục, số cây, số đo nhỏ nhất, lớn nhất)], [số đo không khớp])."""
    if not la_duong_kinh:
        return gom_theo_chu_vi(bang, ten_loai, ds)
    nhom, loi = {}, []
    for dk, so in ds:
        m = next((m for k, m in bang.loai.get(ten_loai, []) if k.chua(D(dk))), None)
        if m is None:
            loi.append(dk)
            continue
        x = nhom.setdefault(m.ma, [m, 0, dk, dk])
        x[1] += so
        x[2], x[3] = min(x[2], dk), max(x[3], dk)
    return [tuple(v) for v in nhom.values()], loi


def mo_ta_do(a, z, la_duong_kinh: bool) -> str:
    """Quy cách ghi vào dòng cây theo số đo: chu vi đo (kèm đường kính quy đổi) hoặc đường kính đo (kèm chu vi quy đổi)."""
    def khoang(x, y):
        return so_vn(x) if x == y else f'{so_vn(x)}–{so_vn(y)}'
    if la_duong_kinh:
        return f'Đường kính đo {khoang(a, z)} cm (chu vi quy đổi {khoang(duong_kinh_sang_chu_vi(a), duong_kinh_sang_chu_vi(z))} cm)'
    return f'Chu vi đo {khoang(a, z)} cm (đường kính quy đổi {khoang(chu_vi_sang_duong_kinh(a), chu_vi_sang_duong_kinh(z))} cm)'


def gom_theo_chu_vi(bang: BangCayDK, ten_loai: str, ds: list) -> tuple:
    """[(chu vi, số cây)] -> ([(mục danh mục, số cây, chu vi nhỏ nhất, lớn nhất)], [chu vi không khớp khoảng nào])."""
    nhom, loi = {}, []
    for cv, so in ds:
        m = bang.tim(ten_loai, cv)
        if m is None:
            loi.append(cv)
            continue
        x = nhom.setdefault(m.ma, [m, 0, cv, cv])
        x[1] += so
        x[2], x[3] = min(x[2], cv), max(x[3], cv)
    return [tuple(v) for v in nhom.values()], loi


# ---------------------------------------------------------------- mật độ cây trồng
def mat_do_tu_danh_muc(ten: str, ghi_chu: str = ''):
    """Mật độ (cây/ha) ghi trong tên / ghi chú danh mục ('Mật độ 1.111 cây/ha'), hoặc None."""
    m = re.search(r'(?i)mật độ\s*([\d.,]+)\s*(?:cây|bụi|khóm|gốc)?\s*/\s*ha', f'{ten} {ghi_chu}')
    if not m:
        return None
    s = m.group(1).strip('.,')
    try:
        v = doc_so_vn(s)                                 # kiểu Việt Nam: 1.111 = một nghìn một trăm mười một
    except ValueError:
        return None
    return v if v > 0 else None


@dataclass
class QuyChuanMatDo:
    ten_cay: str
    mat_do: Decimal | None              # cây/ha
    ty_le_ngoai: Decimal = KHONG        # tỷ lệ bồi thường cây ngoài mật độ (0..1)
    can_cu: str = ''
    nguon: str = ''                     # 'danh mục' / 'dự án'


def quy_chuan_mat_do(con, ten_cay: str, ten_muc: str = '', ghi_chu_muc: str = '') -> QuyChuanMatDo:
    """Quy chuẩn mật độ của một loại cây: bảng quy_chuan_mat_do của dự án, không có thì đọc từ danh mục."""
    goc = ten_goc(ten_cay)
    tl_mac_dinh = D(csdl.doc_cai_dat(con, 'TL_NGOAI_MAT_DO', '0'))
    try:
        r = con.execute('SELECT * FROM quy_chuan_mat_do WHERE ten_cay = ?', (goc,)).fetchone()
    except sqlite3.OperationalError:
        r = None
    if r is not None and r['mat_do'] not in (None, ''):
        return QuyChuanMatDo(goc, D(r['mat_do']), D(r['ty_le_ngoai'] or 0), r['can_cu'], 'dự án')
    md = mat_do_tu_danh_muc(ten_muc, ghi_chu_muc)
    if md is None:
        for x in con.execute("SELECT ten, ghi_chu FROM dm_taisan WHERE nhom = 3 AND (ten LIKE ? OR ten LIKE ?)",
                             (goc + ' -%', goc + ' (%')):
            md = mat_do_tu_danh_muc(x['ten'], x['ghi_chu'])
            if md is not None:
                break
    if md is None:
        q = _mat_do_gan_dung(con, goc)
        if q is not None:
            return QuyChuanMatDo(goc, q[1], tl_mac_dinh, f'Theo mật độ của "{q[0]}" trong danh mục đơn giá (tên gần đúng)',
                                 'gần đúng')
    return QuyChuanMatDo(goc, md, tl_mac_dinh, 'Ghi chú danh mục đơn giá' if md else '', 'danh mục' if md else '')


def _mat_do_gan_dung(con, goc: str):
    """(tên loại, mật độ) của loại cây có mật độ trong danh mục mà tên là phần đầu tên cây này ("Xoài ghép" -> "Xoài"), hoặc
    ngược lại (tên cây là phần đầu tên loại: "Cà phê" -> "Cà phê vối"); trùng hẳn tên (bỏ chữ "Cây" đầu tên) trước, rồi tên dài
    nhất khớp. None nếu không có."""
    def gon(x: str) -> str:                         # danh mục ghi "Cây bưởi", người nhập "Bưởi da xanh": bỏ chữ "cây" đầu tên
        return re.sub(r'^cay\s+', '', bo_dau(x).strip())
    t = gon(goc)
    if not t:
        return None
    tot, diem_tot = None, None
    for r in con.execute("SELECT ten, ghi_chu FROM dm_taisan WHERE nhom = 3 AND ghi_chu LIKE '%ật độ%'"):
        md = mat_do_tu_danh_muc(r['ten'], r['ghi_chu'])
        g = ten_goc(r['ten'])
        k = gon(g)
        if md is None or not k or g == goc:
            continue
        if k == t or t.startswith(k + ' ') or k.startswith(t + ' '):
            diem = (k == t, len(k))                     # trùng hẳn tên trước, rồi tên dài nhất
            if diem_tot is None or diem > diem_tot:
                tot, diem_tot = (g, md), diem
    return tot


def mat_do_thuc_te(so_cay, dien_tich_m2):
    """Mật độ thực tế (cây/ha) = số cây × 10.000 / diện tích trồng; None khi chưa có diện tích."""
    dt = D(dien_tich_m2)
    return (D(so_cay) * Decimal(10000) / dt).quantize(Decimal('1')) if dt > 0 else None


def luu_quy_chuan_mat_do(con, q: QuyChuanMatDo) -> None:
    with con:
        con.execute('INSERT INTO quy_chuan_mat_do (ten_cay, mat_do, ty_le_ngoai, can_cu) VALUES (?,?,?,?) '
                    'ON CONFLICT(ten_cay) DO UPDATE SET mat_do = excluded.mat_do, ty_le_ngoai = excluded.ty_le_ngoai, '
                    'can_cu = excluded.can_cu',
                    (ten_goc(q.ten_cay), chuoi(q.mat_do) if q.mat_do is not None else '', chuoi(q.ty_le_ngoai), q.can_cu))
        csdl.ghi_nhat_ky(con, 'Quy chuẩn mật độ', f'{q.ten_cay}: {q.mat_do} cây/ha, ngoài mật độ {q.ty_le_ngoai}')


def ds_quy_chuan_mat_do(con) -> list:
    """Mọi loại cây có mật độ (danh mục + dự án), sắp theo tên."""
    kq = {}
    tl_mac_dinh = D(csdl.doc_cai_dat(con, 'TL_NGOAI_MAT_DO', '0'))     # đọc một lần (trước: mỗi loại cây một truy vấn - 327 lần)
    for r in con.execute('SELECT ten, ghi_chu FROM dm_taisan WHERE nhom = 3'):
        md = mat_do_tu_danh_muc(r['ten'], r['ghi_chu'])
        if md is not None:
            g = ten_goc(r['ten'])
            kq.setdefault(g, QuyChuanMatDo(g, md, tl_mac_dinh, 'Ghi chú danh mục đơn giá', 'danh mục'))
    try:
        ds = con.execute('SELECT * FROM quy_chuan_mat_do').fetchall()
    except sqlite3.OperationalError:                # bộ đơn giá / file cũ chưa có bảng quy chuẩn
        ds = []
    for r in ds:
        kq[r['ten_cay']] = QuyChuanMatDo(r['ten_cay'], D(r['mat_do']) if r['mat_do'] else None, D(r['ty_le_ngoai'] or 0),
                                         r['can_cu'], 'dự án')
    return sorted(kq.values(), key=lambda q: bo_dau(q.ten_cay))


def so_cay_toi_da(mat_do_ha, dien_tich_m2) -> int:
    """Số cây tối đa theo mật độ trên diện tích trồng (làm tròn xuống, tối thiểu 1 cây khi có diện tích)."""
    if mat_do_ha is None or D(dien_tich_m2) <= 0:
        return 0
    n = (D(mat_do_ha) * D(dien_tich_m2) / Decimal(10000)).to_integral_value(rounding=ROUND_FLOOR)
    return max(int(n), 1)


def phan_tich_mat_do(so_cay, dien_tich_m2, mat_do_ha) -> dict:
    """Đối chiếu số cây kiểm đếm với mật độ quy định: diện tích mỗi cây, số cây tối đa trên diện tích trồng, diện tích cần
    cho số cây kiểm đếm, số cây vượt / đảm bảo mật độ, diện tích còn thiếu."""
    md, dt, so = D(mat_do_ha), D(dien_tich_m2), int(D(so_cay))
    m2 = (Decimal(10000) / md).quantize(Decimal('0.01')) if md > 0 else KHONG
    can = (Decimal(so) * Decimal(10000) / md).quantize(Decimal('0.1')) if md > 0 else KHONG
    trong, ngoai = tach_mat_do(so, dt, md)
    return dict(m2_moi_cay=m2, toi_da=so_cay_toi_da(md, dt), dt_can=can, trong=trong, ngoai=ngoai,
                dt_thieu=max(can - dt, KHONG))


def tach_mat_do(so_cay, dien_tich_m2, mat_do_ha) -> tuple:
    """(số cây trong mật độ, số cây ngoài mật độ)."""
    so = int(D(so_cay))
    toi_da = so_cay_toi_da(mat_do_ha, dien_tich_m2)
    if mat_do_ha is None or toi_da == 0:
        return so, 0
    trong = min(so, toi_da)
    return trong, so - trong


@dataclass
class DongMatDo:
    """Một dòng cây trồng đưa vào phân bổ diện tích theo mật độ (phan_bo_mat_do). mat_do None = chưa có mật độ (không tính)."""
    ten: str
    so_cay: int
    mat_do: Decimal | None
    don_gia: Decimal = KHONG
    ty_le: Decimal = Decimal(1)     # tỷ lệ bồi thường của dòng (giá trị cây = số cây x đơn giá x tỷ lệ)
    thu_tu: int = 0                 # kết quả: thứ tự ưu tiên (1 = tính trước), 0 = không tính
    trong: int = 0                  # số cây trong mật độ
    ngoai: int = 0                  # số cây vượt mật độ
    dt_dung: Decimal = KHONG        # diện tích (m²) phần trong mật độ chiếm
    dt_con: Decimal = KHONG         # diện tích còn lại sau dòng này

    @property
    def m2_moi_cay(self) -> Decimal:
        return Decimal(10000) / D(self.mat_do) if self.mat_do else KHONG


def _thap_phan(x: Fraction) -> Decimal:
    return Decimal(x.numerator) / Decimal(x.denominator)


def phan_bo_mat_do(ds: list, dien_tich_m2) -> Decimal:
    """Nhiều loại cây trồng trên cùng diện tích trồng (người dùng 30/10/2026): cây ĐƠN GIÁ CAO tính trước làm cây trồng chính - trong
    mật độ được tối đa (diện tích còn lại × mật độ / 10.000) cây, mỗi cây chiếm 10.000 / mật độ m²; diện tích còn dư tính tiếp cho cây
    đơn giá cao thứ hai… tới khi hết diện tích; phần không còn chỗ là vượt mật độ. Cùng đơn giá: theo thứ tự dòng. Dòng chưa có mật độ
    không chiếm diện tích (giữ nguyên số cây). Ghi kết quả vào từng DongMatDo, trả diện tích còn lại. Tính bằng phân số (không sai số
    làm tròn); chỉ một loại cây thì giống tach_mat_do (diện tích có mà chưa đủ một cây vẫn được 1 cây)."""
    tong = Fraction(D(dien_tich_m2)) if D(dien_tich_m2) > 0 else Fraction(0)
    con = tong
    co = sorted((x for x in ds if x.mat_do and D(x.mat_do) > 0), key=lambda x: -D(x.don_gia))   # sorted giữ thứ tự khi bằng giá
    for x in ds:
        x.thu_tu, x.trong, x.ngoai, x.dt_dung, x.dt_con = 0, int(x.so_cay), 0, KHONG, KHONG
    for k, x in enumerate(co, start=1):
        md = Fraction(D(x.mat_do))
        vua = math.floor(con * md / 10000)
        if vua == 0 and con == tong and tong > 0:       # như so_cay_toi_da: có diện tích thì tối thiểu 1 cây
            vua = 1
        x.thu_tu = k
        x.trong = min(int(x.so_cay), vua)
        x.ngoai = int(x.so_cay) - x.trong
        dung = min(Fraction(x.trong * 10000) / md, con)
        con -= dung
        x.dt_dung, x.dt_con = _thap_phan(dung), _thap_phan(con)
    return _thap_phan(con)


HE_SO_CAY_XEN = Decimal('0.5')      # cây trồng xen bồi thường không quá 0,5 lần giá trị cây trồng chính (sửa ở cai_dat HE_SO_CAY_XEN)


def gia_tri_cay(ds: list) -> Decimal:
    """Giá trị phần được bồi thường (số cây trong x đơn giá x tỷ lệ) của các dòng đã phân bổ."""
    return sum((Decimal(x.trong) * D(x.don_gia) * D(x.ty_le) for x in ds), KHONG)


def phan_bo_cay_xen(ds: list, gia_tri_toi_da) -> Decimal:
    """Cây trồng xen (người dùng 30/10/2026, theo ảnh phương án mẫu): không xét mật độ; tổng giá trị được bồi thường không quá
    gia_tri_toi_da (= HE_SO_CAY_XEN x giá trị cây trồng chính). Cây xen ĐƠN GIÁ cao tính trước (cùng giá: thứ tự dòng), được tối đa
    floor(giá trị còn lại / (đơn giá x tỷ lệ)) cây, giá trị còn dư tính tiếp cho cây xen đơn giá thấp hơn; phần còn lại vượt 0,5 lần
    (không bồi thường). Dòng đơn giá 0 tính đủ. Kết quả ghi vào từng DongMatDo (trong / ngoai; dt_dung = giá trị đã dùng, dt_con = giá
    trị còn lại); trả giá trị còn lại."""
    con = max(D(gia_tri_toi_da), KHONG)
    for x in ds:
        x.thu_tu, x.trong, x.ngoai, x.dt_dung, x.dt_con = 0, int(x.so_cay), 0, KHONG, KHONG
    for k, x in enumerate(sorted(ds, key=lambda x: -D(x.don_gia)), start=1):
        gia = D(x.don_gia) * D(x.ty_le)
        vua = int(x.so_cay) if gia <= 0 else int((con / gia).to_integral_value(rounding=ROUND_FLOOR))
        x.thu_tu = k
        x.trong = min(int(x.so_cay), vua)
        x.ngoai = int(x.so_cay) - x.trong
        x.dt_dung = Decimal(x.trong) * gia
        con -= x.dt_dung
        x.dt_con = con
    return con


# ---------------------------------------------------------------- tài sản trong / ngoài ranh thu hồi
def tach_ranh(tong, trong_ranh, anh_huong_ket_cau: bool = False, ty_le_ngoai=KHONG) -> dict:
    """Diện tích (khối lượng) tài sản: phần trong ranh thu hồi bồi thường 100%; phần ngoài ranh bồi thường toàn bộ nếu bị
    ảnh hưởng kết cấu (không sử dụng được), không thì theo tỷ lệ ngoài ranh (mặc định 0 = không bồi thường)."""
    tong, trong = D(tong), D(trong_ranh)
    if tong <= 0:
        raise ValueError('Tổng diện tích / khối lượng phải lớn hơn 0.')
    if trong < 0 or trong > tong:
        raise ValueError('Phần trong ranh thu hồi phải từ 0 đến tổng diện tích.')
    ngoai = tong - trong
    if anh_huong_ket_cau:
        return dict(trong=tong, ngoai=KHONG, ty_le_ngoai=KHONG, ngoai_goc=ngoai)
    return dict(trong=trong, ngoai=ngoai, ty_le_ngoai=D(ty_le_ngoai), ngoai_goc=ngoai)


# ---------------------------------------------------------------- tổng diện tích xây dựng so với diện tích thu hồi
# thứ tự ưu tiên tính vào diện tích thu hồi: nhà chính → nhà khác → mái che → công trình phụ → sân, nền
NHOM_XAY_DUNG = [
    (1, 'Nhà chính', r'nhà chính'),
    (2, 'Nhà, công trình khác', r'^(nhà|biệt thự|ki ?ốt|kios|văn phòng|xưởng|nhà xưởng|nhà kho)|\bnhà\b'),
    (3, 'Mái che, mái hiên', r'mái'),
    (4, 'Công trình phụ (bếp, vệ sinh, kho, chuồng trại)', r'bếp|vệ sinh|\bkho\b|chuồng|trại'),
    (5, 'Sân, nền', r'sân|nền'),
]
# không tính vào diện tích chiếm đất: tường, hàng rào (m² mặt tường), gác lửng / sàn tầng trên (trùng diện tích nhà), giếng, hồ…
LOAI_TRU_XAY_DUNG = r'tường|rào|lưới|vách|trụ|cổng|giếng|hồ chứa|bể|mộ|cột|gác|tầng lửng|sàn gác|lan can|cầu thang'


def nhom_xay_dung(ten: str, quy_cach: str = ''):
    """(số thứ tự ưu tiên, tên nhóm) của tài sản tính diện tích xây dựng, hoặc None (không tính)."""
    t = f'{ten} {quy_cach}'.lower()
    if re.search(LOAI_TRU_XAY_DUNG, t):
        return None
    nhom = {so: (ten_nhom, mau) for so, ten_nhom, mau in NHOM_XAY_DUNG}
    for so in (1, 4, 3, 2, 5):                      # nhận diện công trình phụ, mái che trước "nhà…" (nhà vệ sinh, nhà kho)
        if re.search(nhom[so][1], t):
            return so, nhom[so][0]
    return None


def kiem_tra_dt_xay_dung(bo, bo_qua: set | None = None) -> dict:
    """Cộng dồn diện tích (m²) các tài sản mục 2 theo thứ tự ưu tiên (nhà chính, nhà khác, mái che, công trình phụ, sân nền)
    rồi so với tổng diện tích thu hồi của hộ: dòng nào nằm trong / vượt diện tích thu hồi, vượt bao nhiêu.
    bo_qua: chỉ số các dòng người dùng bỏ không tính. Trả dict(thu_hoi, tong, vuot, dong=[...], loai_tru=[...])."""
    bo_qua = bo_qua or set()
    thu_hoi = sum((D(t['dt_thu_hoi'] or 0) for t in bo.bc.thua_cua(bo.ma_ho)), KHONG)
    tinh, loai_tru = [], []
    for i, d in enumerate(bo.pa.khoan[2]):
        m2 = bo_dau(d.dvt).replace(' ', '') in ('m2', 'm²')
        n = nhom_xay_dung(d.ten, d.quy_cach) if m2 else None
        if n is None:
            loai_tru.append(dict(i=i, ten=d.ten, dvt=d.dvt, so_luong=d.so_luong,
                                 ly_do='không phải m²' if not m2 else 'không chiếm đất (tường, rào, gác, giếng…)'))
            continue
        tinh.append(dict(i=i, nhom_so=n[0], nhom=n[1], ten=d.ten, dien_tich=d.so_luong, tinh=i not in bo_qua))
    tinh.sort(key=lambda x: (x['nhom_so'], x['i']))
    luy_ke = KHONG
    for x in tinh:
        if not x['tinh']:
            x.update(luy_ke=luy_ke, vuot=KHONG, trang_thai='Không tính')
            continue
        truoc = luy_ke
        luy_ke += x['dien_tich']
        vuot = max(KHONG, luy_ke - max(thu_hoi, truoc))
        x.update(luy_ke=luy_ke, vuot=vuot,
                 trang_thai='Trong DT thu hồi' if vuot == 0 else ('Vượt toàn bộ' if vuot >= x['dien_tich'] else
                                                                  f'Vượt {so_vn(vuot)} m²'))
    tong = sum((x['dien_tich'] for x in tinh if x['tinh']), KHONG)
    return dict(thu_hoi=thu_hoi, tong=tong, vuot=max(KHONG, tong - thu_hoi), dong=tinh, loai_tru=loai_tru)


def mo_ta_ranh(tong, trong, anh_huong: bool) -> str:
    ngoai = D(tong) - D(trong)
    s = f'Tổng {so_vn(tong)}; trong ranh thu hồi {so_vn(trong)}; ngoài ranh {so_vn(ngoai)}'
    if anh_huong and ngoai > 0:
        s += ' (phần ngoài ranh ảnh hưởng kết cấu, không sử dụng được: tính toàn bộ)'
    return s


def pi_chuoi() -> str:
    return str(round(math.pi, 4)).replace('.', ',')
