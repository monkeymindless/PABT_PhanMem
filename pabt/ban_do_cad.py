"""Nhập bản vẽ địa chính CAD (.dxf) và dữ liệu bản đồ thửa đất (0.9.87 - người dùng 14/10/2026). Không Qt.

Đọc bằng pabt.dxf_thuan (Python thuần, không cần ezdxf / numpy): hình KHÉP KÍN (LWPOLYLINE / POLYLINE đóng) trên lớp ranh thửa = thửa; chữ (TEXT, MTEXT, thuộc tính ATTRIB của khối
nhãn) đặt BÊN TRONG thửa = nhãn thửa -> số thửa (số nguyên đầu tiên), diện tích (số có phần thập phân), loại đất (mã có trong danh mục
loại đất). Số tờ: tham số, không thì chữ "TỜ (BẢN ĐỒ) SỐ n" trong bản vẽ, không thì chữ số trong tên file. Lớp ranh thửa không chỉ định:
lớp có nhiều hình khép kín nhất. Lớp ranh thu hồi (tùy chọn): DT TRONG RANH của từng thửa = diện tích giao (tam giác hóa ranh, cắt thửa
theo từng tam giác - đúng cả ranh hành lang không lồi). Tọa độ giữ nguyên hệ của bản vẽ (VN-2000, mét); cung tròn (bulge) tính theo dây
cung. DWG: lưu sang DXF bằng AutoCAD / MicroStation trước (DWG là định dạng đóng).

Lưu vào bảng thua_ban_do của file dự án (không đổi PHIEN_BAN_CSDL - csdl.mo tạo khi file có hộ, như nhat_ky_van_dong): ghép với hồ
sơ theo (số tờ, số thửa); bảng Hoàn tác được. Màn hình: man_hinh_ban_do (nhập, xem bản đồ).
"""
from __future__ import annotations
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import csdl
from .tien import D, chuoi

from .sql_bang_phu import BANG_BAN_DO as BANG      # noqa: E402 - câu SQL ở module lá
from .sql_bang_phu import SQL_BAN_DO as SQL_BANG      # noqa: E402


class LoiCad(ValueError):
    """Không đọc được bản vẽ (thông báo tiếng Việt)."""


# ---------------------------------------------------------------- hình học (mặt phẳng, mét)
def dien_tich_co_dau(p: list) -> float:
    s = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        s += x1 * y2 - x2 * y1
    return s / 2


def dien_tich(p: list) -> float:
    return abs(dien_tich_co_dau(p))


def chua_diem(p: list, x: float, y: float) -> bool:
    """Điểm (x, y) nằm trong đa giác p (tia ngang)."""
    trong = False
    j = len(p) - 1
    for i in range(len(p)):
        xi, yi = p[i]
        xj, yj = p[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-300) + xi:
            trong = not trong
        j = i
    return trong


def _cat_loi(chu_the: list, cat: list) -> list:
    """Sutherland-Hodgman: cắt đa giác bất kỳ theo đa giác LỒI cat (ngược chiều kim đồng hồ). Diện tích kết quả = diện tích giao."""
    def trong(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def giao(p1, p2, a, b):
        x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        m = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(m) < 1e-15:
            return p2
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / m
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    ra = list(chu_the)
    for i in range(len(cat)):
        a, b = cat[i], cat[(i + 1) % len(cat)]
        vao, ra = ra, []
        if not vao:
            break
        s = vao[-1]
        for e in vao:
            if trong(e, a, b):
                if not trong(s, a, b):
                    ra.append(giao(s, e, a, b))
                ra.append(e)
            elif trong(s, a, b):
                ra.append(giao(s, e, a, b))
            s = e
    return ra


def tam_giac_hoa(p: list) -> list:
    """Chia đa giác đơn (không tự cắt) thành tam giác (cắt tai), mỗi tam giác ngược chiều kim đồng hồ."""
    pts = [tuple(x) for x in p]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if dien_tich_co_dau(pts) < 0:
        pts.reverse()
    kq = []
    vong = 0
    tran = len(pts) * len(pts) + 10                     # 1.0.58: tính MỘT lần (trần theo len đang giảm: ranh >= 30 đỉnh thoát sớm, DT sai)
    while len(pts) > 3 and vong < tran:
        vong += 1
        n = len(pts)
        cat = False
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-12:
                continue                                    # đỉnh lõm / thẳng hàng
            if any(chua_diem([a, b, c], *q) for q in pts if q not in (a, b, c)):
                continue
            kq.append([a, b, c])
            pts.pop(i)
            cat = True
            break
        if not cat:                                          # đa giác suy biến: lấy phần còn lại như một quạt
            break
    if len(pts) >= 3:
        for i in range(1, len(pts) - 1):
            kq.append([pts[0], pts[i], pts[i + 1]])
    return kq


def dien_tich_giao(thua: list, ranh: list, tam_giac: list | None = None) -> float:
    """Diện tích phần thửa nằm trong ranh (cả hai là đa giác đơn, ranh có thể lõm)."""
    tg = tam_giac if tam_giac is not None else tam_giac_hoa(ranh)
    return sum(dien_tich(_cat_loi(thua, t)) for t in tg)


def _hop_bao(p: list) -> tuple:
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)


def _cham_hop(a: tuple, b: tuple) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


# ---------------------------------------------------------------- đọc DXF
@dataclass
class ThuaCad:
    so_to: str
    so_thua: str
    loai_dat: str
    dt_ban_ve: object                    # Decimal hoặc None
    dt_hinh: object
    dt_trong_ranh: object                # None: không có lớp ranh
    toa_do: list
    nhan: str = ''
    lop: str = ''
    chi_tiet: dict = field(default_factory=dict)         # thửa tự ghép từ đường (ban_do_ghep): đối chiếu, các phần DT, mốc, ghi chú
    mau: str = ''                        # màu tô tay của thửa chưa lưu (#RRGGBB); trong dự án nằm ở chi_tiet['mau']


@dataclass
class KetQuaCad:
    thua: list = field(default_factory=list)
    canh_bao: list = field(default_factory=list)
    lop_thua: str = ''
    lop_ranh: str = ''
    so_to: str = ''
    nguon: str = ''
    # bản vẽ đường (ban_do_ghep): vùng hành lang thu hồi, đoạn đóng đầu tuyến, vùng nhiều số thửa, số thửa ngoài vùng khép kín, thống kê
    ranh_vung: list = field(default_factory=list)
    ranh_dong: list = field(default_factory=list)
    chua_tach: list = field(default_factory=list)
    khong_khep: list = field(default_factory=list)
    thong_ke: dict = field(default_factory=dict)


NHO_DOC_TOI_DA = 2              # 1.0.33: số file bản đồ giữ kết quả đọc trong RAM (đọc danh sách lớp rồi phân tích = cùng một file)
_NHO_DOC: dict = {}


def doc_co_nho(file, ham):
    """ham(file) nhớ theo (đường dẫn, mtime_ns, cỡ, tên hàm): hộp Nhập bản đồ đọc danh sách lớp rồi phân tích, đổi lớp / số tờ / kinh tuyến
    rồi phân tích lại - cùng một file chỉ đọc + giải nén một lần. File sửa (mtime / cỡ đổi) thì đọc lại. KHÔNG sửa đối tượng trả về."""
    p = Path(file)
    try:
        st = p.stat()
        khoa = (str(p.resolve()), st.st_mtime_ns, st.st_size, ham.__name__)
    except OSError:
        return ham(p)
    if khoa in _NHO_DOC:
        return _NHO_DOC[khoa]
    kq = ham(p)
    while len(_NHO_DOC) >= NHO_DOC_TOI_DA:
        _NHO_DOC.pop(next(iter(_NHO_DOC)))
    _NHO_DOC[khoa] = kq
    return kq


def _doc_dxf(p: Path) -> list:
    from .dxf_thuan import LoiDxf, doc
    try:
        return doc(p)
    except LoiDxf as e:
        raise LoiCad(str(e)) from None


def _mo(file) -> list:
    """Thực thể của bản vẽ (pabt.dxf_thuan - Python thuần, 16/10/2026: bỏ ezdxf + numpy khỏi bản cài, máy yếu nhẹ ~30 MB)."""
    p = Path(file)
    if p.suffix.lower() == '.dwg':
        raise LoiCad('File .dwg chưa đọc được trực tiếp: mở bằng AutoCAD / MicroStation, Lưu thành (Save As) dạng DXF rồi nhập.')
    return doc_co_nho(p, _doc_dxf)


def _hinh_kin(e) -> list | None:
    """Tọa độ hình khép kín của LWPOLYLINE / POLYLINE 2D (bỏ điểm cuối trùng điểm đầu), hoặc None."""
    if e.loai not in ('LWPOLYLINE', 'POLYLINE'):
        return None
    p = list(e.diem)
    kin = e.kin
    if len(p) >= 2 and p[0] == p[-1]:
        p.pop()
        kin = True
    return p if kin and len(p) >= 3 and dien_tich(p) > 1e-6 else None


def _chu(e) -> list:
    """[(chữ, x, y)] của TEXT / MTEXT / thuộc tính khối (hoặc chữ trong khối không thuộc tính)."""
    return [(str(c or '').strip(), x, y) for c, x, y in e.chu if str(c or '').strip()]


def doc_lop(file) -> list:
    """[(tên lớp, số hình khép kín, số chữ)] - chọn lớp ranh thửa / ranh thu hồi."""
    doc = _mo(file)
    dem = {}
    for e in doc:
        lop = e.lop
        d = dem.setdefault(lop, [0, 0])
        if _hinh_kin(e) is not None:
            d[0] += 1
        elif e.loai in ('TEXT', 'MTEXT', 'INSERT'):
            d[1] += 1
    return sorted(((k, v[0], v[1]) for k, v in dem.items()), key=lambda x: (-x[1], -x[2], x[0]))


_RE_TO = re.compile(r't[oờ]\s*(?:b[aả]n\s*[dđ][oồ]\s*)?(?:s[oố]\s*)?:?\s*(\d{1,4})\b', re.I)
_RE_SO = re.compile(r'(?<![\w.,])(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,4})?|\d+(?:[.,]\d{1,4})?)(?![\w])')


def _ma_loai_dat() -> set:
    try:
        from .loai_dat import LOAI_DAT
        return {x[0].upper() for x in LOAI_DAT}
    except Exception:                                    # noqa: BLE001
        return set()


def boc_nhan(chu: str, ma_loai: set) -> tuple:
    """(số thửa, diện tích Decimal | None, loại đất) từ chữ nhãn của một thửa ("12\\n245,6\\nONT", "12/245.6 ONT", "ONT 12 245,6")."""
    loai = next((t for t in re.findall(r'[A-ZĐ]{2,5}(?:\+[A-ZĐ]{2,5})*', chu.upper()) if all(x in ma_loai for x in t.split('+'))), '')
    so_thua, dt = '', None
    for m in _RE_SO.finditer(chu):
        s = m.group(1)
        if re.fullmatch(r'\d+', s):
            if not so_thua:
                so_thua = str(int(s))
            elif dt is None and len(s) >= len(so_thua) + 1:
                dt = D(s)                                # "12 245": số nguyên dài hơn sau số thửa = diện tích
        elif dt is None:
            from .tien import doc_so_vn
            try:
                dt = doc_so_vn(s)
            except Exception:                            # noqa: BLE001
                pass
    return so_thua, dt, loai


def phan_tich(file, lop_thua: str | None = None, lop_ranh: str | None = None, so_to: str | None = None) -> KetQuaCad:
    """Đọc bản vẽ -> KetQuaCad (thửa có nhãn; thửa không đọc được số thửa ghi ở canh_bao)."""
    doc = _mo(file)
    kq = KetQuaCad(nguon=Path(file).name)
    hinh, chu, ranh = {}, [], []
    for e in doc:
        lop = e.lop
        p = _hinh_kin(e)
        if p is not None:
            hinh.setdefault(lop, []).append(p)
            continue
        if e.loai in ('TEXT', 'MTEXT', 'INSERT'):
            chu.extend(_chu(e))
    if not hinh:
        raise LoiCad('Bản vẽ không có hình khép kín (polyline đóng) nào - ranh thửa vẽ bằng đường rời (LINE) cần tạo vùng (topology / '
                     'Create Polygon) trước khi xuất DXF.')
    if lop_thua is None or lop_thua not in hinh:
        lop_thua = max((k for k in hinh if k != lop_ranh), key=lambda k: len(hinh[k]), default=next(iter(hinh)))
    kq.lop_thua = lop_thua
    if lop_ranh:
        ranh = hinh.get(lop_ranh, [])
        if not ranh:
            kq.canh_bao.append(f'Lớp ranh thu hồi "{lop_ranh}" không có hình khép kín: không tính diện tích trong ranh.')
        kq.lop_ranh = lop_ranh
    # số tờ
    if not so_to:
        m = next((m for c, _, _ in chu for m in [_RE_TO.search(c)] if m), None)
        so_to = m.group(1) if m else (re.findall(r'\d+', Path(file).stem) or [''])[-1]
    kq.so_to = str(int(so_to)) if str(so_to).isdigit() else str(so_to or '')
    if not kq.so_to:
        kq.canh_bao.append('Không tìm thấy số tờ bản đồ: nhập ở ô "Số tờ".')
    ma_loai = _ma_loai_dat()
    tam_giac = [tam_giac_hoa(r) for r in ranh]
    hop_ranh = [_hop_bao(r) for r in ranh]
    thua = hinh[lop_thua]
    hop = [_hop_bao(p) for p in thua]
    dt = [dien_tich(p) for p in thua]
    nhan = [[] for _ in thua]
    for c, x, y in chu:                                  # chữ thuộc thửa NHỎ NHẤT chứa điểm đặt chữ
        tot = None
        for i, p in enumerate(thua):
            h = hop[i]
            if h[0] <= x <= h[2] and h[1] <= y <= h[3] and chua_diem(p, x, y) and (tot is None or dt[i] < dt[tot]):
                tot = i
        if tot is not None:
            nhan[tot].append(c)
    da_co = set()
    for i, p in enumerate(thua):
        chu_thua = '\n'.join(nhan[i])
        so_thua, dt_nhan, loai = boc_nhan(chu_thua, ma_loai)
        if not so_thua:
            if chu_thua:
                kq.canh_bao.append(f'Hình khép kín có chữ "{chu_thua[:40]}" nhưng không đọc được số thửa: bỏ qua.')
            continue
        if (kq.so_to, so_thua) in da_co:
            kq.canh_bao.append(f'Thửa {so_thua} tờ {kq.so_to} xuất hiện nhiều lần trên bản vẽ: lấy hình đầu tiên.')
            continue
        da_co.add((kq.so_to, so_thua))
        trong = None
        if ranh:
            trong = sum(dien_tich_giao(p, ranh[j], tam_giac[j]) for j in range(len(ranh)) if _cham_hop(hop[i], hop_ranh[j]))
        kq.thua.append(ThuaCad(kq.so_to, so_thua, loai, dt_nhan, D(f'{dt[i]:.1f}'),
                               None if trong is None else D(f'{trong:.1f}'), [[round(x, 3), round(y, 3)] for x, y in p],
                               chu_thua, lop_thua))
    if not kq.thua:
        kq.canh_bao.append(f'Lớp "{lop_thua}" không có thửa nào có nhãn số thửa bên trong.')
    return kq


# ---------------------------------------------------------------- lưu / đọc trong dự án
def dam_bao_bang(con) -> bool:
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return True
    try:
        with csdl.giao_dich(con):
            con.execute(SQL_BANG)
    except sqlite3.OperationalError:
        return False
    return True


def co_cot_chi_tiet(con) -> bool:
    return 'chi_tiet' in {r[1] for r in con.execute(f'PRAGMA table_info({BANG})')}


def dam_bao_cot_chi_tiet(con) -> bool:
    """File cũ: thêm cột chi_tiet khi ghi bản đồ (bảng chưa có thì dam_bao_bang tạo đủ cột). False: file chỉ xem / khóa."""
    if co_cot_chi_tiet(con):
        return True
    try:
        with csdl.giao_dich(con):
            con.execute(f"ALTER TABLE {BANG} ADD COLUMN chi_tiet TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        return False
    return True


def _khoa(so) -> str:
    """Số tờ / thửa so khớp: số bỏ 0 đầu; chữ (lô rừng "TK126/K6") viết hoa, bỏ khoảng trắng, "-" "_" "." -> "/", bỏ 0 đầu từng
    nhóm số ("TK126-K06" = "TK126/K6") - 1.0.32."""
    s = str(so or '').strip()
    if s.isdigit():
        return str(int(s))
    s = re.sub(r'[-_.\\]', '/', re.sub(r'\s+', '', s).upper())
    return re.sub(r'(?<![0-9])0+(?=[0-9])', '', s)


def chi_muc_thua(con) -> dict:
    """{(số tờ, số thửa) chuẩn hóa: (mã thửa, mã hộ, dt_thu_hoi, loai_dat)} của hồ sơ kiểm kê."""
    return {(_khoa(r['so_to']), _khoa(r['so_thua'])): (r['ma_thua'], r['ma_ho'], r['dt_thu_hoi'], r['loai_dat'])
            # dòng có DT thu hồi đứng sau (thắng): thửa nhiều dòng hồ sơ gắn hộ chủ đất, không gắn hộ chỉ có tài sản
            for r in con.execute('SELECT ma_thua, ma_ho, so_to, so_thua, dt_thu_hoi, loai_dat FROM thua '
                                 'ORDER BY COALESCE(dt_thu_hoi, \'\') NOT IN (\'\', \'0\'), ma_thua')}


def luu(con, kq: KetQuaCad, cap_nhat_dt: set | None = None, cap_nhat_loai: bool = False) -> dict:
    """Ghi thửa bản vẽ vào dự án (thay thửa cùng số tờ / số thửa). cap_nhat_dt: tập (tờ, thửa) cập nhật DT thu hồi của hồ sơ theo DT
    trong ranh (không có ranh: DT bản vẽ / DT hình). Trả {'luu', 'khop', 'cap_nhat'}."""
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')                 # vai trò tài khoản máy chủ (phan_quyen)
    if not dam_bao_bang(con) or not dam_bao_cot_chi_tiet(con):
        raise LoiCad('File dự án đang mở chỉ xem / bị khóa: không ghi được bản đồ.')
    cm = chi_muc_thua(con)
    # 1.0.58: một thửa nhiều dòng hồ sơ (nhiều loại đất / hộ chỉ có tài sản): không biết ghi dòng nào -> không ghi, báo sửa tay; DT vượt
    # DT nguyên thửa: không ghi; hộ ngoài phần nhận việc (bản offline): chặn
    dong_thua = {}
    for r in con.execute('SELECT ma_thua, so_to, so_thua, dt_nguyen_thua FROM thua'):
        dong_thua.setdefault((_khoa(r['so_to']), _khoa(r['so_thua'])), []).append(r)
    from .lap_pa import kiem_ds_ho_nhan_viec
    kiem_ds_ho_nhan_viec(con, sorted({cm[k][1] for k in cap_nhat_dt or () if k in cm}))
    nhieu_dong, vuot = [], []
    luc = datetime.now().isoformat(timespec='seconds')
    khop = cap_nhat = 0
    mau_cu = {}
    for r in con.execute(f"SELECT so_to, so_thua, chi_tiet FROM {BANG} WHERE chi_tiet LIKE '%\"mau\"%'"):
        try:
            mau_cu[(r['so_to'], r['so_thua'])] = chuan_mau(json.loads(r['chi_tiet']).get('mau'))
        except (ValueError, AttributeError):              # JSON hỏng: như chưa tô, không chặn việc lưu bản đồ
            pass
    with csdl.giao_dich(con):
        for t in kq.thua:
            ct = dict(t.chi_tiet or {})
            mau = chuan_mau(getattr(t, 'mau', '')) or mau_cu.get((t.so_to, t.so_thua), '')      # nạp lại file bản vẽ không làm mất màu đã tô
            if mau:
                ct['mau'] = mau
            con.execute(f'''INSERT INTO {BANG} (so_to, so_thua, loai_dat, dt_ban_ve, dt_hinh, dt_trong_ranh, toa_do, nhan, lop, nguon, luc, chi_tiet)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(so_to, so_thua) DO UPDATE SET loai_dat = excluded.loai_dat,
                            dt_ban_ve = excluded.dt_ban_ve, dt_hinh = excluded.dt_hinh, dt_trong_ranh = excluded.dt_trong_ranh,
                            toa_do = excluded.toa_do, nhan = excluded.nhan, lop = excluded.lop, nguon = excluded.nguon,
                            luc = excluded.luc, chi_tiet = excluded.chi_tiet''',
                        (t.so_to, t.so_thua, t.loai_dat, None if t.dt_ban_ve is None else chuoi(t.dt_ban_ve), chuoi(t.dt_hinh),
                         None if t.dt_trong_ranh is None else chuoi(t.dt_trong_ranh), json.dumps(t.toa_do), t.nhan, t.lop,
                         kq.nguon, luc, json.dumps(ct, ensure_ascii=False) if ct else ''))
            k = (_khoa(t.so_to), _khoa(t.so_thua))
            if k in cm:
                khop += 1
                if cap_nhat_dt and k in cap_nhat_dt:
                    moi = t.dt_trong_ranh if t.dt_trong_ranh is not None else (t.dt_ban_ve or t.dt_hinh)
                    ds_dong = dong_thua.get(k, ())
                    if len(ds_dong) > 1:
                        nhieu_dong.append(f'{t.so_to}/{t.so_thua}')
                        continue
                    ng = ds_dong[0]['dt_nguyen_thua'] if ds_dong else None
                    if ng not in (None, '') and D(moi) > D(ng):
                        vuot.append(f'{t.so_to}/{t.so_thua}')
                        continue
                    sets, ts = ['dt_thu_hoi = ?'], [chuoi(moi)]
                    if cap_nhat_loai and t.loai_dat:
                        sets.append('loai_dat = ?')
                        ts.append(t.loai_dat)
                    con.execute(f'UPDATE thua SET {", ".join(sets)} WHERE ma_thua = ?', (*ts, cm[k][0]))
                    cap_nhat += 1
        csdl.ghi_nhat_ky(con, 'Nhập bản vẽ CAD', f'{kq.nguon}: {len(kq.thua)} thửa tờ {kq.so_to} (khớp hồ sơ {khop}, cập nhật DT '
                                                 f'{cap_nhat})')
    return dict(luu=len(kq.thua), khop=khop, cap_nhat=cap_nhat, nhieu_dong=nhieu_dong, vuot=vuot)


# trạng thái đồng thuận của hộ (ý kiến ở đợt niêm yết gần nhất) -> màu trên bản đồ
TRANG_THAI = {'dong_y': ('Đã đồng thuận', '#2F7D54'), 'khong': ('Chưa đồng thuận', '#C94545'),
              'chua': ('Chưa lấy ý kiến', '#E5A93A'), 'khong_gan': ('Chưa gắn hộ (không có trong hồ sơ)', '#94A3B8')}


def trang_thai_ho(con) -> dict:
    """{mã hộ: 'dong_y' / 'khong' / 'chua'} theo ý kiến ở đợt niêm yết GẦN NHẤT của hộ (y_kien_du_thao)."""
    kq = {}
    try:
        rows = con.execute('SELECT ma_ho, loai FROM y_kien_du_thao ORDER BY dot_id').fetchall()
    except sqlite3.OperationalError:                     # file cũ chưa có bảng niêm yết
        rows = []
    for r in rows:
        kq[r['ma_ho']] = 'dong_y' if r['loai'] == 'dong_y' else 'chua' if r['loai'] == 'chua' else 'khong'
    return kq


@dataclass
class ThuaBanDo:
    so_to: str
    so_thua: str
    loai_dat: str
    toa_do: list
    dt_hinh: str
    dt_trong_ranh: str | None
    ma_ho: int | None
    ho_ten: str
    trang_thai: str
    dt_thu_hoi: str | None = None            # 30/10/2026: DT thu hồi / DT nguyên thửa của thửa hồ sơ khớp (tô màu lệch diện tích)
    dt_nguyen_thua: str | None = None
    dt_ban_ve: str | None = None             # DT ghi trên nhãn bản vẽ
    chi_tiet: dict = field(default_factory=dict)     # bản vẽ đường (ban_do_ghep): đối chiếu, các phần DT, mốc, ghi chú, điểm đặt số thửa
    ma_thua: int | None = None               # dòng thửa của hồ sơ khớp số tờ, số thửa
    tam: bool = False                        # vừa phân tích từ file, chưa lưu vào dự án
    mau: str = ''                            # màu tô tay (#RRGGBB), thắng màu của cách tô đang chọn


# 1.0.70: tô tay từng ô thửa (chuột phải): bảng màu nhanh; màu lưu trong chi_tiet['mau'], đọc ra ThuaBanDo.mau để chi_tiet vẫn chỉ là dữ liệu đối chiếu bản vẽ
MAU_TO_TAY = (('Đỏ', '#DC2626'), ('Cam', '#EA580C'), ('Vàng', '#EAB308'), ('Xanh lá', '#16A34A'), ('Xanh dương', '#2563EB'), ('Tím', '#7C3AED'), ('Hồng', '#DB2777'), ('Xám', '#64748B'))


def chuan_mau(mau) -> str:
    """'#RRGGBB' hợp lệ, không thì ''."""
    s = str(mau or '').strip()
    return s.upper() if re.fullmatch(r'#[0-9A-Fa-f]{6}', s) else ''


def dat_mau_thua(con, so_to: str, so_thua: str, mau: str = '') -> None:
    """Ghi màu tô tay của một thửa trong bản đồ dự án; '' = bỏ màu. Không đụng hồ sơ hộ."""
    from .lap_pa import LoiNhap, kiem_quyen
    kiem_quyen(con, 'sua_ho_so')
    if mau and not chuan_mau(mau):
        raise LoiNhap(f'Mã màu không hợp lệ: {mau}.')
    if not dam_bao_cot_chi_tiet(con):
        raise LoiCad('File dự án đang mở chỉ xem / bị khóa: không ghi được bản đồ.')
    with csdl.giao_dich(con):
        r = con.execute(f'SELECT id, chi_tiet FROM {BANG} WHERE so_to = ? AND so_thua = ?', (so_to, so_thua)).fetchone()
        if r is None:
            raise LoiNhap(f'Bản đồ dự án không có thửa {so_thua} tờ {so_to}.')
        try:
            ct = json.loads(r['chi_tiet']) if r['chi_tiet'] else {}
        except ValueError:
            ct = {}
        if mau:
            ct['mau'] = chuan_mau(mau)
        else:
            ct.pop('mau', None)
        con.execute(f'UPDATE {BANG} SET chi_tiet = ? WHERE id = ?', (json.dumps(ct, ensure_ascii=False) if ct else '', r['id']))
        csdl.ghi_nhat_ky(con, 'Tô màu ô thửa trên bản đồ', f'Thửa {so_thua} tờ {so_to}: {mau or "bỏ màu"}')


# 30/10/2026 (phương án đột phá 4): tô màu bản đồ theo đồng thuận / tiến độ theo hộ / lệch diện tích bản đồ với hồ sơ
CHE_DO_MAU = (('dong_thuan', 'Đồng thuận'), ('tien_do', 'Tiến độ theo hộ'), ('lech_dt', 'Lệch diện tích bản đồ / hồ sơ'),
              ('thu_hoi', 'Phạm vi thu hồi'))
NGUONG_KHOP, NGUONG_LECH = D('0.02'), D('0.10')
LECH_DT = {'khop': ('Khớp (lệch không quá 2%)', '#2F7D54'), 'lech_nhe': ('Lệch 2-10%', '#E5A93A'),
           'lech_nhieu': ('Lệch trên 10%', '#C94545'), 'chua_dt': ('Hồ sơ chưa có diện tích', '#7F77DD'),
           'khong_gan': TRANG_THAI['khong_gan']}


def _so(x):
    if x in (None, ''):
        return None
    try:
        v = D(x)
    except (ArithmeticError, ValueError, TypeError):
        return None
    return v if v.is_finite() else None


def lech_dien_tich(t: ThuaBanDo) -> tuple:
    """(khóa LECH_DT, tỷ lệ lệch Decimal | None, DT bản đồ, DT hồ sơ, cách so). Có ranh thu hồi: DT trong ranh so với DT thu hồi
    của hồ sơ; không có ranh: DT hình thửa so với DT nguyên thửa (trống thì DT thu hồi)."""
    if t.ma_ho is None:
        return 'khong_gan', None, None, None, ''
    trong = _so(t.dt_trong_ranh)
    if trong is not None:
        bd, hs, cach = trong, _so(t.dt_thu_hoi), 'DT trong ranh thu hồi so với DT thu hồi của hồ sơ'
    else:
        nt = _so(t.dt_nguyen_thua)
        bd = _so(t.dt_hinh)
        hs, cach = (nt, 'DT hình thửa so với DT nguyên thửa của hồ sơ') if nt else \
            (_so(t.dt_thu_hoi), 'DT hình thửa so với DT thu hồi của hồ sơ')
    if bd is None or not hs or hs <= 0:
        return 'chua_dt', None, bd, hs, cach
    ty = abs(bd - hs) / hs
    return ('khop' if ty <= NGUONG_KHOP else 'lech_nhe' if ty <= NGUONG_LECH else 'lech_nhieu'), ty, bd, hs, cach


THU_HOI = {'ca_thua': ('Thu hồi cả thửa', TRANG_THAI['khong'][1]), 'mot_phan': ('Thu hồi một phần', TRANG_THAI['chua'][1]),
           'ngoai': ('Ngoài ranh thu hồi', TRANG_THAI['dong_y'][1]), 'chua_ro': ('Chưa có DT thu hồi', TRANG_THAI['khong_gan'][1])}


def muc_thu_hoi(t: ThuaBanDo) -> str:
    """Khóa THU_HOI của thửa: theo DT trong ranh của bản vẽ, bản vẽ không có ranh thì theo DT thu hồi của hồ sơ."""
    th = _so(t.dt_trong_ranh)
    if th is None:
        th = _so(t.dt_thu_hoi)
    ca = _so(t.dt_ban_ve) or _so(t.dt_hinh) or _so(t.dt_nguyen_thua)
    if th is None:
        return 'chua_ro'
    if th <= 0:
        return 'ngoai'
    return 'ca_thua' if ca and th >= ca - 1 else 'mot_phan'


def thua_tu_ket_qua(con, kq: KetQuaCad) -> list:
    """Thửa vừa phân tích từ file (chưa lưu) -> [ThuaBanDo] kèm hộ khớp số tờ, số thửa: tô màu, bấm xem ngay; con None: chỉ hình."""
    cm, ten, tt, nguyen = {}, {}, {}, {}
    if con is not None:
        cm = chi_muc_thua(con)
        ten = {r['ma_ho']: r['ho_ten'] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
        tt = trang_thai_ho(con)
        if 'dt_nguyen_thua' in {r[1] for r in con.execute('PRAGMA table_info(thua)')}:
            nguyen = {r[0]: r[1] for r in con.execute('SELECT ma_thua, dt_nguyen_thua FROM thua')}
    ra = []
    for t in kq.thua:
        k = cm.get((_khoa(t.so_to), _khoa(t.so_thua)))
        ma = k[1] if k else None
        ra.append(ThuaBanDo(t.so_to, t.so_thua, t.loai_dat, t.toa_do, chuoi(t.dt_hinh), None if t.dt_trong_ranh is None else chuoi(t.dt_trong_ranh), ma,
                            ten.get(ma, ''), tt.get(ma, 'chua') if ma is not None else 'khong_gan', k[2] if k else None,
                            nguyen.get(k[0]) if k else None, None if t.dt_ban_ve is None else chuoi(t.dt_ban_ve), t.chi_tiet,
                            k[0] if k else None, True, chuan_mau(getattr(t, 'mau', ''))))
    return ra


def sua_thua_ban_do(con, so_to: str, so_thua: str, moi: dict) -> tuple:
    """Sửa số tờ / số thửa / loại đất của một thửa TRÊN BẢN ĐỒ (bản vẽ đọc nhầm nhãn) - hồ sơ hộ không đổi. moi: so_to, so_thua, loai_dat;
    1.1.07 thêm (không bắt buộc): mau ('#RRGGBB', '' = bỏ), ghi_chu (chữ, '' = bỏ), xoa_gan_ho (True: bỏ gắn hộ - xoa_gan_ho_thua).
    Trả (tờ, thửa) mới."""
    from .lap_pa import LoiNhap, kiem_quyen
    kiem_quyen(con, 'sua_ho_so')
    to, thua = str(moi.get('so_to', so_to)).strip(), str(moi.get('so_thua', so_thua)).strip()
    if not thua:
        raise LoiNhap('Số thửa không được để trống.')
    if 'mau' in moi and moi['mau'] and not chuan_mau(moi['mau']):
        raise LoiNhap(f'Mã màu không hợp lệ: {moi["mau"]}.')
    with csdl.giao_dich(con):
        if moi.get('xoa_gan_ho'):
            xoa_gan_ho_thua(con, so_to, so_thua)
        if 'mau' in moi or 'ghi_chu' in moi:
            def dat(ct):
                if 'mau' in moi:
                    if chuan_mau(moi['mau']):
                        ct['mau'] = chuan_mau(moi['mau'])
                    else:
                        ct.pop('mau', None)
                if 'ghi_chu' in moi:
                    chu = ' '.join(str(moi['ghi_chu'] or '').split())
                    if chu:
                        ct['ghi_chu'] = [x.strip() for x in chu.split(';') if x.strip()]
                    else:
                        ct.pop('ghi_chu', None)
            _sua_chi_tiet(con, so_to, so_thua, dat, 'màu / ghi chú')
        r = con.execute(f'SELECT id, loai_dat FROM {BANG} WHERE so_to = ? AND so_thua = ?', (so_to, so_thua)).fetchone()
        if r is None:
            raise LoiNhap(f'Bản đồ dự án không có thửa {so_thua} tờ {so_to}.')
        if (to, thua) != (so_to, so_thua) and con.execute(f'SELECT 1 FROM {BANG} WHERE so_to = ? AND so_thua = ?', (to, thua)).fetchone():
            raise LoiNhap(f'Bản đồ đã có thửa {thua} tờ {to}.')
        loai = str(moi.get('loai_dat', r['loai_dat'])).strip().upper()
        con.execute(f'UPDATE {BANG} SET so_to = ?, so_thua = ?, loai_dat = ? WHERE id = ?', (to, thua, loai, r['id']))
        csdl.ghi_nhat_ky(con, 'Sửa thửa trên bản đồ', f'Thửa {so_thua} tờ {so_to} -> thửa {thua} tờ {to}, loại đất {loai}')
    return to, thua


def xoa_gan_ho_thua(con, so_to: str, so_thua: str) -> list:
    """1.1.07: bỏ gắn hộ của ô thửa (gắn nhầm) - mọi dòng thửa hồ sơ cùng số tờ / số thửa ra khỏi hồ sơ hộ (ho_so.bo_thua: thửa đã có
    dòng bồi thường đất thì từ chối, không đổi gì). Bản đồ giữ nguyên. Trả các câu đã làm; thửa chưa gắn hộ: []."""
    from . import ho_so
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')
    k = (_khoa(so_to), _khoa(so_thua))
    ds = [r['ma_thua'] for r in con.execute('SELECT ma_thua, so_to, so_thua FROM thua') if (_khoa(r['so_to']), _khoa(r['so_thua'])) == k]
    if not ds:
        return []
    with csdl.giao_dich(con):                           # nhiều dòng: một giao dịch - dòng sau bị từ chối thì dòng trước không bỏ
        return [ho_so.bo_thua(con, mt) for mt in ds]


def _sua_chi_tiet(con, so_to: str, so_thua: str, ham, nhat_ky: str) -> None:
    from .lap_pa import LoiNhap
    if not dam_bao_cot_chi_tiet(con):
        raise LoiCad('File dự án đang mở chỉ xem / bị khóa: không ghi được bản đồ.')
    r = con.execute(f'SELECT id, chi_tiet FROM {BANG} WHERE so_to = ? AND so_thua = ?', (so_to, so_thua)).fetchone()
    if r is None:
        raise LoiNhap(f'Bản đồ dự án không có thửa {so_thua} tờ {so_to}.')
    try:
        ct = json.loads(r['chi_tiet']) if r['chi_tiet'] else {}
    except ValueError:
        ct = {}
    ham(ct)
    con.execute(f'UPDATE {BANG} SET chi_tiet = ? WHERE id = ?', (json.dumps(ct, ensure_ascii=False) if ct else '', r['id']))
    csdl.ghi_nhat_ky(con, 'Sửa thửa trên bản đồ', f'Thửa {so_thua} tờ {so_to}: {nhat_ky}')


def dat_lai_thua_ban_do(con, so_to: str, so_thua: str, xoa_ho: bool = True, xoa_mau: bool = True, xoa_ghi_chu: bool = True) -> list:
    """1.1.07: đặt lại ô thửa - bỏ gắn hộ (xoa_gan_ho_thua), bỏ màu tô tay, bỏ ghi chú. Một giao dịch. Trả các câu đã làm."""
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_ho_so')
    ra = []
    with csdl.giao_dich(con):
        if xoa_ho:
            ra += xoa_gan_ho_thua(con, so_to, so_thua)
        if xoa_mau or xoa_ghi_chu:
            def bo(ct):
                if xoa_mau and ct.pop('mau', None):
                    ra.append('Đã bỏ màu tô.')
                if xoa_ghi_chu and ct.pop('ghi_chu', None):
                    ra.append('Đã bỏ ghi chú.')
            _sua_chi_tiet(con, so_to, so_thua, bo, 'đặt lại (màu, ghi chú)')
    return ra


def xoa_thua_ban_do(con, so_to: str, so_thua: str) -> None:
    """1.1.07: xóa ô thửa khỏi BẢN ĐỒ dự án (nạp nhầm) - hồ sơ hộ không đổi; nạp lại bản vẽ thì ô thửa có lại."""
    from .lap_pa import LoiNhap, kiem_quyen
    kiem_quyen(con, 'sua_ho_so')
    with csdl.giao_dich(con):
        if not con.execute(f'DELETE FROM {BANG} WHERE so_to = ? AND so_thua = ?', (so_to, so_thua)).rowcount:
            raise LoiNhap(f'Bản đồ dự án không có thửa {so_thua} tờ {so_to}.')
        csdl.ghi_nhat_ky(con, 'Xóa ô thửa trên bản đồ', f'Thửa {so_thua} tờ {so_to} (hồ sơ hộ không đổi)')


def doc_ban_do(con, so_to: str | None = None) -> list:
    """Các thửa đã nhập bản vẽ (lọc theo tờ), kèm hộ (theo số tờ / số thửa của hồ sơ) và trạng thái đồng thuận."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return []
    cm = chi_muc_thua(con)
    ten = {r['ma_ho']: r['ho_ten'] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
    tt = trang_thai_ho(con)
    nguyen = {}
    if 'dt_nguyen_thua' in {r[1] for r in con.execute('PRAGMA table_info(thua)')}:
        nguyen = {r[0]: r[1] for r in con.execute('SELECT ma_thua, dt_nguyen_thua FROM thua')}
    kq = []
    co_ct = co_cot_chi_tiet(con)
    sql = f'SELECT * FROM {BANG}' + (' WHERE so_to = ?' if so_to else '') + ' ORDER BY so_to, CAST(so_thua AS INTEGER), so_thua'
    for r in con.execute(sql, (so_to,) if so_to else ()):
        k = cm.get((_khoa(r['so_to']), _khoa(r['so_thua'])))
        ma = k[1] if k else None
        ct = r['chi_tiet'] if co_ct else ''
        try:
            ct = json.loads(ct) if ct else {}
        except ValueError:
            ct = {}
        mau = chuan_mau(ct.pop('mau', '')) if isinstance(ct, dict) else ''
        kq.append(ThuaBanDo(r['so_to'], r['so_thua'], r['loai_dat'], json.loads(r['toa_do']), r['dt_hinh'], r['dt_trong_ranh'], ma,
                            ten.get(ma, ''), tt.get(ma, 'chua') if ma is not None else 'khong_gan',
                            k[2] if k else None, nguyen.get(k[0]) if k else None, r['dt_ban_ve'], ct, k[0] if k else None, False, mau))
    return kq


def ds_khoa(con) -> set:
    """{(tờ, thửa) chuẩn hóa} các thửa đã lưu trong bản đồ dự án."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return set()
    return {(_khoa(r[0]), _khoa(r[1])) for r in con.execute(f'SELECT so_to, so_thua FROM {BANG}')}


def gop_ket_qua(ds: list) -> KetQuaCad:
    """Gộp kết quả phân tích của nhiều file (nhiều lớp KML mở cùng lúc). Thửa trùng số tờ, số thửa: giữ thửa của file đầu, báo."""
    if len(ds) == 1:
        return ds[0]
    kq = KetQuaCad(nguon=', '.join(x.nguon for x in ds if x.nguon))
    da = set()
    for x in ds:
        for t in x.thua:
            k = (_khoa(t.so_to), _khoa(t.so_thua))
            if k in da:
                kq.canh_bao.append(f'Thửa {t.so_thua} tờ {t.so_to} có ở nhiều file: lấy file đầu tiên.')
                continue
            da.add(k)
            kq.thua.append(t)
        kq.canh_bao += x.canh_bao
        kq.ranh_vung += x.ranh_vung
        kq.ranh_dong += x.ranh_dong
        kq.chua_tach += x.chua_tach
        kq.khong_khep += x.khong_khep
    kq.lop_thua = '; '.join(sorted({x.lop_thua for x in ds if x.lop_thua}))
    kq.lop_ranh = '; '.join(sorted({x.lop_ranh for x in ds if x.lop_ranh}))
    kq.so_to = ', '.join(sorted({x.so_to for x in ds if x.so_to}))
    return kq


def ds_to(con) -> list:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return []
    return [r[0] for r in con.execute(f'SELECT DISTINCT so_to FROM {BANG} ORDER BY CAST(so_to AS INTEGER), so_to')]
