"""Nhập bản vẽ địa chính CAD (.dxf) và dữ liệu bản đồ thửa đất (0.9.87 - người dùng 14/10/2026). Không Qt.

Đọc bằng ezdxf: hình KHÉP KÍN (LWPOLYLINE / POLYLINE đóng) trên lớp ranh thửa = thửa; chữ (TEXT, MTEXT, thuộc tính ATTRIB của khối
nhãn) đặt BÊN TRONG thửa = nhãn thửa -> số thửa (số nguyên đầu tiên), diện tích (số có phần thập phân), loại đất (mã có trong danh mục
loại đất). Số tờ: tham số, không thì chữ "TỜ (BẢN ĐỒ) SỐ n" trong bản vẽ, không thì chữ số trong tên file. Lớp ranh thửa không chỉ định:
lớp có nhiều hình khép kín nhất. Lớp ranh thu hồi (tùy chọn): DT TRONG RANH của từng thửa = diện tích giao (tam giác hóa ranh, cắt thửa
theo từng tam giác - đúng cả ranh hành lang không lồi). Tọa độ giữ nguyên hệ của bản vẽ (VN-2000, mét); cung tròn (bulge) tính theo dây
cung. DWG: lưu sang DXF bằng AutoCAD / MicroStation trước (ezdxf không đọc DWG).

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

BANG = 'thua_ban_do'
SQL_BANG = f'''CREATE TABLE IF NOT EXISTS {BANG} (
    id INTEGER PRIMARY KEY,
    so_to TEXT NOT NULL,
    so_thua TEXT NOT NULL,
    loai_dat TEXT NOT NULL DEFAULT '',
    dt_ban_ve TEXT,                     -- diện tích ghi trên nhãn bản vẽ (m²)
    dt_hinh TEXT,                       -- diện tích tính theo hình (m²)
    dt_trong_ranh TEXT,                 -- diện tích nằm trong ranh thu hồi (m²) - trống: không có lớp ranh
    toa_do TEXT NOT NULL,               -- JSON [[x, y], …] hệ tọa độ bản vẽ
    nhan TEXT NOT NULL DEFAULT '',      -- chữ nhãn gốc trong thửa
    lop TEXT NOT NULL DEFAULT '',
    nguon TEXT NOT NULL DEFAULT '',     -- tên file .dxf
    luc TEXT NOT NULL,
    UNIQUE (so_to, so_thua)
)'''


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
    while len(pts) > 3 and vong < len(pts) * len(pts) + 10:
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


@dataclass
class KetQuaCad:
    thua: list = field(default_factory=list)
    canh_bao: list = field(default_factory=list)
    lop_thua: str = ''
    lop_ranh: str = ''
    so_to: str = ''
    nguon: str = ''


def _ezdxf():
    import logging
    logging.getLogger('fontTools').setLevel(logging.ERROR)     # fontTools (ezdxf dùng) cảnh báo phông hệ thống lỗi bảng 'name'
    try:
        import ezdxf
        return ezdxf
    except ImportError:
        raise LoiCad('Máy chưa có thư viện ezdxf (đọc bản vẽ CAD) - cài lại phần mềm bản 0.9.87 trở lên.') from None


def _mo(file):
    p = Path(file)
    if p.suffix.lower() == '.dwg':
        raise LoiCad('File .dwg chưa đọc được trực tiếp: mở bằng AutoCAD / MicroStation, Lưu thành (Save As) dạng DXF rồi nhập.')
    ez = _ezdxf()
    try:
        return ez.readfile(str(p))
    except IOError as e:
        raise LoiCad(f'Không mở được {p.name}: {e}') from None
    except ez.DXFStructureError:
        try:
            from ezdxf import recover
            doc, _ = recover.readfile(str(p))
            return doc
        except Exception as e:                           # noqa: BLE001 - mọi lỗi cấu trúc: báo tiếng Việt
            raise LoiCad(f'{p.name} hỏng cấu trúc DXF: {e}') from None


def _hinh_kin(e) -> list | None:
    """Tọa độ hình khép kín của LWPOLYLINE / POLYLINE (bỏ điểm cuối trùng điểm đầu), hoặc None."""
    t = e.dxftype()
    try:
        if t == 'LWPOLYLINE':
            p = [(float(x), float(y)) for x, y, *_ in e.get_points('xy')]
            kin = bool(e.closed)
        elif t == 'POLYLINE' and not e.is_3d_polyline and not e.is_poly_face_mesh and not e.is_polygon_mesh:
            p = [(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]
            kin = bool(e.is_closed)
        else:
            return None
    except Exception:                                    # noqa: BLE001 - thực thể hỏng: bỏ qua
        return None
    if len(p) >= 2 and p[0] == p[-1]:
        p.pop()
        kin = True
    return p if kin and len(p) >= 3 and dien_tich(p) > 1e-6 else None


def _chu(e) -> list:
    """[(chữ, x, y)] của TEXT / MTEXT / thuộc tính khối."""
    t = e.dxftype()
    kq = []
    try:
        if t == 'TEXT':
            p = e.dxf.align_point if e.dxf.hasattr('align_point') and (e.dxf.halign or e.dxf.valign) else e.dxf.insert
            kq.append((e.dxf.text, float(p[0]), float(p[1])))
        elif t == 'MTEXT':
            kq.append((e.plain_text(), float(e.dxf.insert[0]), float(e.dxf.insert[1])))
        elif t == 'INSERT':
            for a in e.attribs:
                kq.append((a.dxf.text, float(a.dxf.insert[0]), float(a.dxf.insert[1])))
            if not e.attribs:                            # khối nhãn không thuộc tính: chữ bên trong khối, đặt ở điểm chèn
                try:
                    for v in e.virtual_entities():
                        kq.extend(_chu(v))
                except Exception:                        # noqa: BLE001
                    pass
    except Exception:                                    # noqa: BLE001
        pass
    return [(str(c or '').strip(), x, y) for c, x, y in kq if str(c or '').strip()]


def doc_lop(file) -> list:
    """[(tên lớp, số hình khép kín, số chữ)] - chọn lớp ranh thửa / ranh thu hồi."""
    doc = _mo(file)
    dem = {}
    for e in doc.modelspace():
        lop = e.dxf.layer if e.dxf.hasattr('layer') else '0'
        d = dem.setdefault(lop, [0, 0])
        if _hinh_kin(e) is not None:
            d[0] += 1
        elif e.dxftype() in ('TEXT', 'MTEXT', 'INSERT'):
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
    for e in doc.modelspace():
        lop = e.dxf.layer if e.dxf.hasattr('layer') else '0'
        p = _hinh_kin(e)
        if p is not None:
            hinh.setdefault(lop, []).append(p)
            continue
        if e.dxftype() in ('TEXT', 'MTEXT', 'INSERT'):
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


def _khoa(so) -> str:
    s = str(so or '').strip()
    return str(int(s)) if s.isdigit() else s.upper()


def chi_muc_thua(con) -> dict:
    """{(số tờ, số thửa) chuẩn hóa: (mã thửa, mã hộ, dt_thu_hoi, loai_dat)} của hồ sơ kiểm kê."""
    return {(_khoa(r['so_to']), _khoa(r['so_thua'])): (r['ma_thua'], r['ma_ho'], r['dt_thu_hoi'], r['loai_dat'])
            for r in con.execute('SELECT ma_thua, ma_ho, so_to, so_thua, dt_thu_hoi, loai_dat FROM thua')}


def luu(con, kq: KetQuaCad, cap_nhat_dt: set | None = None, cap_nhat_loai: bool = False) -> dict:
    """Ghi thửa bản vẽ vào dự án (thay thửa cùng số tờ / số thửa). cap_nhat_dt: tập (tờ, thửa) cập nhật DT thu hồi của hồ sơ theo DT
    trong ranh (không có ranh: DT bản vẽ / DT hình). Trả {'luu', 'khop', 'cap_nhat'}."""
    if not dam_bao_bang(con):
        raise LoiCad('File dự án đang mở chỉ xem / bị khóa: không ghi được bản đồ.')
    cm = chi_muc_thua(con)
    luc = datetime.now().isoformat(timespec='seconds')
    khop = cap_nhat = 0
    with csdl.giao_dich(con):
        for t in kq.thua:
            con.execute(f'''INSERT INTO {BANG} (so_to, so_thua, loai_dat, dt_ban_ve, dt_hinh, dt_trong_ranh, toa_do, nhan, lop, nguon, luc)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(so_to, so_thua) DO UPDATE SET loai_dat = excluded.loai_dat,
                            dt_ban_ve = excluded.dt_ban_ve, dt_hinh = excluded.dt_hinh, dt_trong_ranh = excluded.dt_trong_ranh,
                            toa_do = excluded.toa_do, nhan = excluded.nhan, lop = excluded.lop, nguon = excluded.nguon,
                            luc = excluded.luc''',
                        (t.so_to, t.so_thua, t.loai_dat, None if t.dt_ban_ve is None else chuoi(t.dt_ban_ve), chuoi(t.dt_hinh),
                         None if t.dt_trong_ranh is None else chuoi(t.dt_trong_ranh), json.dumps(t.toa_do), t.nhan, t.lop,
                         kq.nguon, luc))
            k = (_khoa(t.so_to), _khoa(t.so_thua))
            if k in cm:
                khop += 1
                if cap_nhat_dt and k in cap_nhat_dt:
                    moi = t.dt_trong_ranh if t.dt_trong_ranh is not None else (t.dt_ban_ve or t.dt_hinh)
                    sets, ts = ['dt_thu_hoi = ?'], [chuoi(moi)]
                    if cap_nhat_loai and t.loai_dat:
                        sets.append('loai_dat = ?')
                        ts.append(t.loai_dat)
                    con.execute(f'UPDATE thua SET {", ".join(sets)} WHERE ma_thua = ?', (*ts, cm[k][0]))
                    cap_nhat += 1
        csdl.ghi_nhat_ky(con, 'Nhập bản vẽ CAD', f'{kq.nguon}: {len(kq.thua)} thửa tờ {kq.so_to} (khớp hồ sơ {khop}, cập nhật DT '
                                                 f'{cap_nhat})')
    return dict(luu=len(kq.thua), khop=khop, cap_nhat=cap_nhat)


# trạng thái đồng thuận của hộ (ý kiến ở đợt niêm yết gần nhất) -> màu trên bản đồ
TRANG_THAI = {'dong_y': ('Đã đồng thuận', '#16A34A'), 'khong': ('Chưa đồng thuận', '#DC2626'),
              'chua': ('Chưa lấy ý kiến', '#F59E0B'), 'khong_gan': ('Chưa gắn hộ (không có trong hồ sơ)', '#94A3B8')}


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


def doc_ban_do(con, so_to: str | None = None) -> list:
    """Các thửa đã nhập bản vẽ (lọc theo tờ), kèm hộ (theo số tờ / số thửa của hồ sơ) và trạng thái đồng thuận."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return []
    cm = chi_muc_thua(con)
    ten = {r['ma_ho']: r['ho_ten'] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
    tt = trang_thai_ho(con)
    kq = []
    sql = f'SELECT * FROM {BANG}' + (' WHERE so_to = ?' if so_to else '') + ' ORDER BY so_to, CAST(so_thua AS INTEGER), so_thua'
    for r in con.execute(sql, (so_to,) if so_to else ()):
        k = cm.get((_khoa(r['so_to']), _khoa(r['so_thua'])))
        ma = k[1] if k else None
        kq.append(ThuaBanDo(r['so_to'], r['so_thua'], r['loai_dat'], json.loads(r['toa_do']), r['dt_hinh'], r['dt_trong_ranh'], ma,
                            ten.get(ma, ''), tt.get(ma, 'chua') if ma is not None else 'khong_gan'))
    return kq


def ds_to(con) -> list:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return []
    return [r[0] for r in con.execute(f'SELECT DISTINCT so_to FROM {BANG} ORDER BY CAST(so_to AS INTEGER), so_to')]
