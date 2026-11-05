"""Tự dựng thửa từ bản vẽ ĐƯỜNG (KML / KMZ xuất từ MicroStation, gCadas, AutoCAD: LineString + nhãn Point, không có đa giác). Không Qt, chỉ
thư viện chuẩn, chạy được ở luồng nền.

Bản vẽ địa chính xuất ra KML thường KHÔNG có vùng thửa: lưới thửa là các đoạn thẳng rời, số thửa / loại đất / diện tích là các điểm có tên.
Module này ghép lại như một người đo đạc đọc bản vẽ:

1. Ghép lưới thửa: nút hóa các đoạn (tách tại giao điểm, chữ T), bỏ nhánh cụt, duyệt mặt phẳng -> các vùng khép kín (kể cả lỗ).
   Lớp nào là lưới thửa: KHÔNG viết cố định "Level 9 / Level 10" (mỗi bản vẽ một quy ước) - thử lần lượt các lớp, giữ lớp làm tăng số vùng
   có đúng một số thửa và diện tích hình khớp nhãn diện tích (`chon_lop_luoi`).
2. Gán nhãn: số thửa, loại đất, diện tích, nhãn "(xxx)" nằm trong vùng nào thuộc vùng đó. Vùng nhiều số thửa: thửa hẹp (mương, đường) không đủ chỗ
   ghi chữ, người vẽ đặt nhãn sang thửa bên cạnh rồi kẻ gạch dẫn - số nào có nhãn DT khớp diện tích vùng là chủ vùng, số kia về vùng không số gần đó có
   diện tích khớp nhãn của nó (`_tach_nhieu_so`). Không có bằng chứng diện tích thì KHÔNG đoán - ghi vào `chua_tach`.
3. Ranh thu hồi: lớp đường đi qua các vòng tròn mốc (đường có chữ "ranh" trong tên cũng tính), bỏ mẩu thừa ở chỗ nối, đóng hai đầu tuyến -> vùng
   hành lang (`tim_ranh`). DT thu hồi của thửa = diện tích giao hình học, ĐỐI CHIẾU với tổng các nhãn diện tích nằm trong hành lang.
4. Số tờ: nhãn "Tờ số n" gần nhất mà đoạn nối tới nó KHÔNG cắt đường ranh tờ (đường nằm giữa các cặp nhãn "Tờ a | Tờ b").

Không có gì được coi là đúng nếu chưa đối chiếu: mỗi thửa mang `doi_chieu` (dt = hình so nhãn, thu_hoi = hình so nhãn) và `ly_do` khi lệch. Màn hình
hiện nguyên trạng thái này, thửa lệch không tự đánh dấu cập nhật hồ sơ."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

from .ban_do_cad import KetQuaCad, ThuaCad, _cham_hop, _hop_bao, chua_diem, dien_tich, dien_tich_co_dau, dien_tich_giao, tam_giac_hoa
from .tien import D

SAI_NUT = 0.02                   # m: hai đầu mút trong khoảng này là một nút (bản vẽ thật: các đầu mút trùng khít tới mm)
SAI_NUT_RANH = 0.30              # m: chỗ nối các đoạn tuyến ranh của nhiều bản vẽ hở nhiều hơn
O_LUOI = 60.0                    # m: cỡ ô lưới chỉ mục đoạn thẳng
O_NHAN = 120.0                   # m: cỡ ô lưới chỉ mục vùng cho nhãn
DT_MAT_TOI_THIEU = 0.05          # m²: nhỏ hơn là khe hở do hai đường gần trùng, không phải vùng
SAI_DT_TUYET_DOI = 1.0           # m²: nhãn làm tròn tới 0,1 - 1 m² (đo trên file thật: 150/151 thửa lệch dưới 1 m²)
SAI_DT_TUONG_DOI = 0.002         # 0,2%: thửa lớn lệch do làm tròn / phép chiếu
SAI_THU_HOI_TUYET_DOI = 1.0      # m²: DT thu hồi hình học so với tổng nhãn trong ranh
SAI_THU_HOI_TUONG_DOI = 0.001    # 0,1%: nhiều nhãn phần cộng lại, mỗi nhãn làm tròn 0,1 m²
SO_NHAN_TAP_CON = 14             # thử tổ hợp tối đa ngần này nhãn phần của một thửa (2^14 tổng)
NHAN_LECH_TOI_DA = 15.0          # m: nhãn phần nhỏ không đủ chỗ ghi trong phần đó, người vẽ đặt sang bên cạnh (file thật: tới hơn 10 m)
TY_LE_LOP_TOI_THIEU = 0.002      # lớp ngắn hơn 0,2% tổng chiều dài bản vẽ: ký hiệu, không thử làm lưới thửa
DAI_LOP_TOI_THIEU = 60.0
SO_LOP_THU_TOI_DA = 24
CO_VONG_MOC, SO_DINH_VONG_MOC = 3.8, 8     # = ban_do_kml: vòng tròn nhỏ quanh cọc mốc
GAN_VONG_MOC = 0.20              # m: đường đi qua tâm vòng mốc
TY_LE_RANH_TOI_THIEU = 0.15      # lớp đi qua ít nhất 15% số vòng mốc là đường ranh
MAU_THUA_CUT = 60.0              # m: mẩu đường ranh cụt ngắn hơn là phần thừa ở chỗ nối hai bản vẽ, dài hơn là đầu tuyến
DONG_DAU_TOI_DA = 400.0          # m: hai đầu tuyến ranh cách nhau trong khoảng này thì đóng lại
DT_RANH_TOI_THIEU = 50.0
CAP_NHAN_TO_TOI_DA = 40.0        # m: cặp nhãn "Tờ a | Tờ b" đặt hai bên đường ranh tờ
DUONG_RANH_TO_MOI_CAT = 400.0    # m: lớp ranh tờ ngắn - cứ tối đa ngần này mét lại nằm giữa một cặp nhãn tờ (lớp lưới thửa dài hơn nhiều)
GAN_MOC = 1.5                    # m: mốc coi là thuộc ranh thửa khi tâm cách ranh thửa trong khoảng này
CAP_NHAN_DT = 15.0               # m: nhãn DT đi với số thửa gần nó trong cùng một vùng
GAN_NHAN_LD = 12.0               # m: nhãn loại đất đi với số thửa
TIM_VUNG_HEP = 80.0              # m: số thửa đặt nhãn lệch: tìm vùng không số trong khoảng này

_RE_SO_THUA = re.compile(r'\d{1,5}[a-zA-Z]?(?:\s*/)?')
_RE_LOAI_DAT = re.compile(r'[A-ZĐ]{2,4}(?:\s*\+\s*[A-ZĐ]{2,4})*')


def loai_nhan_ghep(chu: str, lop_cad: str = '') -> str:
    """ban_do_kml.loai_nhan thêm hai dạng của bản vẽ thật: số thửa có chữ cái ("1230A", "231a" - thửa tách) và loại đất có khoảng trắng
    ("ONT+CLN +LUK"). Quy tắc chung với LARC Mobile giữ ở loai_nhan."""
    from .ban_do_kml import loai_nhan
    c = str(chu or '').strip()
    loai = loai_nhan(c, lop_cad)
    if loai == 'ghi_chu':
        if _RE_SO_THUA.fullmatch(c):
            return 'thua'
        if _RE_LOAI_DAT.fullmatch(c):
            return 'ld'
    return loai


def so_thua_chuan(chu: str) -> str:
    """'1230 /' -> '1230', '0231a' -> '231A' (số bỏ 0 đầu, chữ cái viết hoa như ban_do_cad._khoa)."""
    s = re.sub(r'[\s/]+', '', str(chu or ''))
    m = re.fullmatch(r'0*(\d+)([a-zA-Z]?)', s)
    return (m.group(1) + m.group(2).upper()) if m else s


def so_nhan(chu: str):
    """'(1.331,3)' / '1331.3' -> float | None: số của nhãn diện tích (chỉ để so hình học; số lưu vào CSDL đi qua Decimal)."""
    s = re.sub(r'[()\s]', '', str(chu or ''))
    if not s:
        return None
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    else:
        s = s.replace(',', '.')
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


# ---------------------------------------------------------------- đối tượng đọc từ bản vẽ
@dataclass
class DuongVe:
    nhom: tuple                  # (bản vẽ, lớp CAD)
    mau: str
    diem: list                   # [(đông, bắc)]
    ten: str = ''


@dataclass
class NhanVe:
    loai: str
    chu: str
    x: float
    y: float
    lop: str = ''
    ban_ve: str = ''
    mau: str = ''


@dataclass
class BanVe:
    duong: list = field(default_factory=list)
    nhan: list = field(default_factory=list)
    vong_moc: list = field(default_factory=list)   # [(x, y)] tâm vòng tròn mốc


def doc_ban_ve(ds: list, kinh_tuyen: float) -> BanVe:
    """[PlacemarkKml] -> đường (bỏ vòng tròn mốc), nhãn, tâm vòng mốc - tọa độ VN-2000 theo kinh tuyến trục. Đa giác nhỏ và đường đi kèm cùng một
    vòng tròn được tính là một vòng mốc."""
    from .toa_do import wgs84_sang_vn2000
    bv = BanVe()
    da_vong = set()

    def doi(ds_diem):
        return [wgs84_sang_vn2000(vd, kd, kinh_tuyen) for kd, vd in ds_diem]

    def la_vong(q):
        xs, ys = [p[0] for p in q], [p[1] for p in q]
        return len(q) >= SO_DINH_VONG_MOC and max(max(xs) - min(xs), max(ys) - min(ys)) < CO_VONG_MOC

    def them_vong(q):
        xs, ys = [p[0] for p in q], [p[1] for p in q]
        tam = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        k = (round(tam[0], 1), round(tam[1], 1))
        if k not in da_vong:
            da_vong.add(k)
            bv.vong_moc.append(tam)

    for pm in ds:
        try:
            for ngoai, _lo in pm.da_giac:
                q = doi(ngoai)
                if la_vong(q):
                    them_vong(q)
            for ln in pm.duong:
                q = doi(ln)
                if la_vong(q):
                    them_vong(q)
                elif len(q) >= 2:
                    bv.duong.append(DuongVe((pm.ban_ve, pm.lop_cad), pm.mau_duong, q, pm.ten))
            for kd, vd in pm.diem:
                if pm.ten:
                    x, y = wgs84_sang_vn2000(vd, kd, kinh_tuyen)
                    bv.nhan.append(NhanVe(loai_nhan_ghep(pm.ten, pm.lop_cad), pm.ten.strip(), x, y, pm.lop_cad, pm.ban_ve, pm.mau_nhan))
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
    return bv


# ---------------------------------------------------------------- nút hóa + duyệt mặt phẳng
def _nut_hoa(doan: list, sai: float) -> dict:
    """[(a, b)] -> đồ thị {nút: {nút kề}}: mọi giao điểm (cả chữ T hở dưới `sai` m, cả đoạn gần trùng nhau) đều thành nút."""
    goc = {}

    def nut(p):
        return goc.setdefault((round(p[0] / sai), round(p[1] / sai)), p)
    dd = []
    for a, b in doan:
        a, b = nut(a), nut(b)
        if a != b:
            dd.append((a, b))
    luoi = defaultdict(list)
    for i, (a, b) in enumerate(dd):
        for ox in range(int(min(a[0], b[0]) // O_LUOI), int(max(a[0], b[0]) // O_LUOI) + 1):
            for oy in range(int(min(a[1], b[1]) // O_LUOI), int(max(a[1], b[1]) // O_LUOI) + 1):
                luoi[(ox, oy)].append(i)
    cat = defaultdict(list)
    da = set()
    for ds_i in luoi.values():
        for u in range(len(ds_i)):
            i = ds_i[u]
            a, b = dd[i]
            rx, ry = b[0] - a[0], b[1] - a[1]
            lr = math.hypot(rx, ry)
            for v in range(u + 1, len(ds_i)):
                j = ds_i[v]
                k = (i, j) if i < j else (j, i)
                if k in da:
                    continue
                da.add(k)
                c, d = dd[j]
                sx, sy = d[0] - c[0], d[1] - c[1]
                ls = math.hypot(sx, sy)
                m = rx * sy - ry * sx
                if abs(m) <= 1e-7 * lr * ls:             # gần song song: đầu mút đoạn này nằm trên đoạn kia thì tách tại đó
                    for p, (x1, y1, dx, dy, l2, o) in ((c, (a[0], a[1], rx, ry, lr, i)), (d, (a[0], a[1], rx, ry, lr, i)),
                                                       (a, (c[0], c[1], sx, sy, ls, j)), (b, (c[0], c[1], sx, sy, ls, j))):
                        t = ((p[0] - x1) * dx + (p[1] - y1) * dy) / (l2 * l2)
                        if 0 < t < 1 and abs((p[0] - x1) * dy - (p[1] - y1) * dx) / l2 <= sai:
                            cat[o].append(p)
                    continue
                t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / m
                w = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / m
                dt, dw = sai / lr, sai / ls
                if -dt <= t <= 1 + dt and -dw <= w <= 1 + dw:
                    p = nut((a[0] + t * rx, a[1] + t * ry))
                    cat[i].append(p)
                    cat[j].append(p)
    ke = defaultdict(set)
    for i, (a, b) in enumerate(dd):
        pts = [a, b]
        if i in cat:
            rx, ry = b[0] - a[0], b[1] - a[1]
            l2 = (rx * rx + ry * ry) or 1.0
            pts = sorted({a, b, *cat[i]}, key=lambda p: ((p[0] - a[0]) * rx + (p[1] - a[1]) * ry) / l2)
        for u in range(len(pts) - 1):
            p, q = pts[u], pts[u + 1]
            if p != q:
                ke[p].add(q)
                ke[q].add(p)
    return ke


def _bo_nhanh_cut(ke: dict) -> None:
    hang = [n for n, v in ke.items() if len(v) == 1]
    while hang:
        n = hang.pop()
        if len(ke[n]) != 1:
            continue
        m = next(iter(ke[n]))
        ke[n].clear()
        ke[m].discard(n)
        if len(ke[m]) == 1:
            hang.append(m)


@dataclass
class VungVe:
    vong: list                   # vòng ngoài, ngược chiều kim đồng hồ
    dt: float                    # diện tích đã trừ lỗ
    lo: list = field(default_factory=list)
    hop: tuple = ()


def _vung_tu_do_thi(ke: dict) -> list:
    """Duyệt mặt phẳng: mỗi cạnh có hướng thuộc đúng một mặt (mặt bên trái). Mặt dương = vùng; mặt âm = vòng ngoài của một cụm - nằm trong vùng khác thì
    là LỖ của vùng đó (thửa bao quanh thửa khác không nối lưới)."""
    huong = {n: sorted(v, key=lambda m: math.atan2(m[1] - n[1], m[0] - n[0])) for n, v in ke.items() if v}
    vi_tri = {n: {m: i for i, m in enumerate(v)} for n, v in huong.items()}
    da_di = set()
    duong, am = [], []
    for n, v in huong.items():
        for m in v:
            if (n, m) in da_di:
                continue
            vong = []
            a, b = n, m
            while (a, b) not in da_di:
                da_di.add((a, b))
                vong.append(a)
                ds_b = huong[b]
                a, b = b, ds_b[vi_tri[b][a] - 1]
            s = dien_tich_co_dau(vong)
            if s > DT_MAT_TOI_THIEU:
                duong.append(VungVe(vong, s, hop=_hop_bao(vong)))
            elif s < -DT_MAT_TOI_THIEU:
                am.append((vong, -s))
    am.sort(key=lambda x: x[1])
    for vong, s in am:
        x, y = vong[0]
        cha = None
        for f in duong:
            h = f.hop
            if f.vong is not vong and h[0] <= x <= h[2] and h[1] <= y <= h[3] and s < f.dt and vong[0] not in _dinh(f) \
                    and chua_diem(f.vong, x, y) and (cha is None or f.dt < cha.dt):
                cha = f
        if cha is not None:
            cha.lo.append(vong)
            cha.dt -= s
    return duong


def _dinh(f: VungVe) -> set:
    d = getattr(f, '_dinh', None)
    if d is None:
        d = set(f.vong)
        f._dinh = d
    return d


def ghep_vung(doan: list, sai: float = SAI_NUT) -> list:
    """Các đoạn thẳng -> [VungVe] khép kín."""
    ke = _nut_hoa(doan, sai)
    _bo_nhanh_cut(ke)
    return _vung_tu_do_thi(ke)


class _ChiMucVung:
    """Vùng chứa một điểm: lưới ô để khỏi dò hết các vùng cho từng nhãn."""

    def __init__(self, ds: list):
        self.ds, self.o = ds, defaultdict(list)
        for i, f in enumerate(ds):
            h = f.hop
            for ox in range(int(h[0] // O_NHAN), int(h[2] // O_NHAN) + 1):
                for oy in range(int(h[1] // O_NHAN), int(h[3] // O_NHAN) + 1):
                    self.o[(ox, oy)].append(i)

    def tim(self, x: float, y: float):
        """Chỉ số vùng NHỎ NHẤT chứa điểm (nằm trong lỗ của vùng thì không thuộc vùng đó) | None."""
        tot = None
        for i in self.o.get((int(x // O_NHAN), int(y // O_NHAN)), ()):
            f = self.ds[i]
            h = f.hop
            if h[0] <= x <= h[2] and h[1] <= y <= h[3] and chua_diem(f.vong, x, y) and not any(chua_diem(v, x, y) for v in f.lo) \
                    and (tot is None or f.dt < self.ds[tot].dt):
                tot = i
        return tot


def _doan_cua(ds_duong: list) -> list:
    return [(d.diem[i], d.diem[i + 1]) for d in ds_duong for i in range(len(d.diem) - 1)]


def _khop_dt(hinh: float, nhan: float) -> bool:
    return abs(hinh - nhan) <= max(SAI_DT_TUYET_DOI, nhan * SAI_DT_TUONG_DOI)


def _diem_chon(ds_vung: list, nhan_thua: list, nhan_dt: list) -> int:
    """Độ tốt của một cách ghép lưới: vùng một số thửa + DT khớp nhãn được 3 điểm, một số thửa được 1, nhiều số thửa khác nhau bị trừ."""
    cm = _ChiMucVung(ds_vung)
    so, dt = defaultdict(set), defaultdict(list)
    for n in nhan_thua:
        i = cm.tim(n.x, n.y)
        if i is not None:
            so[i].add(so_thua_chuan(n.chu))
    for n, v in nhan_dt:
        i = cm.tim(n.x, n.y)
        if i is not None:
            dt[i].append(v)
    diem = 0
    for i, s in so.items():
        if len(s) > 1:
            diem += 1 if any(_khop_dt(ds_vung[i].dt, v) for v in dt.get(i, ())) else -1      # thửa bên đặt nhãn sang: vẫn là vùng đúng nếu có DT khớp
        elif any(_khop_dt(ds_vung[i].dt, v) for v in dt.get(i, ())):
            diem += 3
        else:
            diem += 1
    return diem


def chon_lop_luoi(bv: BanVe) -> tuple:
    """Chọn các lớp (bản vẽ, lớp CAD) tạo thành lưới thửa: thêm dần từ lớp dài nhất, giữ lớp làm điểm tăng. Trả (tập lớp, [VungVe])."""
    theo = defaultdict(list)
    dai = defaultdict(float)
    for d in bv.duong:
        theo[d.nhom].append(d)
        dai[d.nhom] += sum(math.hypot(d.diem[i + 1][0] - d.diem[i][0], d.diem[i + 1][1] - d.diem[i][1]) for i in range(len(d.diem) - 1))
    tong = sum(dai.values())
    ung = sorted((k for k in theo if dai[k] >= DAI_LOP_TOI_THIEU and dai[k] >= tong * TY_LE_LOP_TOI_THIEU), key=lambda k: -dai[k])[:SO_LOP_THU_TOI_DA]
    nhan_thua = [n for n in bv.nhan if n.loai == 'thua']
    # chỉ nhãn DT nguyên thửa: nhãn "(xxx)" là DT từng phần - đường ranh cắt thửa cũng làm vùng khớp phần đó, chọn nhầm ranh thành lưới thửa
    nhan_dt = [(n, v) for n in bv.nhan if n.loai == 'dt' for v in [so_nhan(n.chu)] if v]
    chon, doan, tot, ds_tot = [], [], 0, []
    for k in ung:
        thu = doan + _doan_cua(theo[k])
        ds = ghep_vung(thu)
        d = _diem_chon(ds, nhan_thua, nhan_dt)
        if d > tot or (not chon and ds):                 # lớp đầu tiên khép được vùng: nhận (vùng toàn số chồng nhau vẫn phải báo, không im lặng)
            chon.append(k)
            doan, tot, ds_tot = thu, d, ds
    return set(chon), ds_tot


# ---------------------------------------------------------------- ranh thu hồi
def _khoang_cach_doan(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2)) if l2 else 0.0
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])


def _lop_ranh(bv: BanVe, lop_luoi: set) -> list:
    """Các đường ranh thu hồi: có chữ "ranh" trong tên, hoặc thuộc lớp (ngoài lưới thửa) đi qua nhiều vòng mốc."""
    from .ban_do_kml import la_ten_ranh
    co_ten = [d for d in bv.duong if la_ten_ranh(d.ten)]
    if co_ten:
        return co_ten
    if not bv.vong_moc:
        return []
    theo = defaultdict(list)
    for d in bv.duong:
        if d.nhom not in lop_luoi:
            theo[(d.nhom, d.mau)].append(d)
    dem = {}
    o = 2.0
    vong = defaultdict(list)
    for x, y in bv.vong_moc:
        vong[(int(x // o), int(y // o))].append((x, y))
    for k, ds in theo.items():
        gap = set()
        for d in ds:
            for i in range(len(d.diem) - 1):
                a, b = d.diem[i], d.diem[i + 1]
                # các ô quanh đoạn thẳng: đoạn dài thì đi dọc theo đoạn
                n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / o))
                for t in range(n + 1):
                    x, y = a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n
                    for ox in (int(x // o) - 1, int(x // o), int(x // o) + 1):
                        for oy in (int(y // o) - 1, int(y // o), int(y // o) + 1):
                            for p in vong.get((ox, oy), ()):
                                if p not in gap and _khoang_cach_doan(p, a, b) <= GAN_VONG_MOC:
                                    gap.add(p)
        dem[k] = len(gap)
    can = max(3, int(len(bv.vong_moc) * TY_LE_RANH_TOI_THIEU))
    return [d for k, ds in theo.items() if dem[k] >= can for d in ds]


def _do_dai_nhanh(ke: dict, n) -> tuple:
    """Từ đầu cụt n đi tới nút rẽ: (chiều dài, [các nút đã qua, không gồm nút rẽ])."""
    qua = []
    dai = 0.0
    truoc, hien = None, n
    while len(ke[hien]) <= 2:
        qua.append(hien)
        tiep = [m for m in ke[hien] if m != truoc]
        if not tiep:
            break
        dai += math.hypot(tiep[0][0] - hien[0], tiep[0][1] - hien[1])
        truoc, hien = hien, tiep[0]
    return dai, qua


def tim_ranh(bv: BanVe, lop_luoi: set) -> tuple:
    """Vùng hành lang thu hồi từ các đường ranh: ([VungVe], [đoạn đóng đầu tuyến]). Các đoạn tuyến của nhiều bản vẽ chồng mép nhau một đoạn ở chỗ nối: mẩu cụt
    ngắn hơn MAU_THUA_CUT bị bỏ; hai đầu tuyến còn lại (đường ranh dừng ở mép bản vẽ) được đóng bằng đoạn thẳng."""
    ds = _lop_ranh(bv, lop_luoi)
    if not ds:
        return [], []
    ke = _nut_hoa(_doan_cua(ds), SAI_NUT_RANH)
    for n in [x for x, v in ke.items() if len(v) == 1]:
        if n in ke and len(ke[n]) == 1:
            dai, qua = _do_dai_nhanh(ke, n)
            if dai < MAU_THUA_CUT:
                for q in qua:
                    for m in list(ke[q]):
                        ke[m].discard(q)
                    ke[q].clear()
    dau = [x for x, v in ke.items() if len(v) == 1]
    dong = []
    con = set(dau)
    cap = sorted(((math.hypot(a[0] - b[0], a[1] - b[1]), a, b) for i, a in enumerate(dau) for b in dau[i + 1:]), key=lambda x: x[0])
    for m, a, b in cap:
        if m <= DONG_DAU_TOI_DA and a in con and b in con:
            ke[a].add(b)
            ke[b].add(a)
            con -= {a, b}
            dong.append((a, b))
    _bo_nhanh_cut(ke)
    ra = [f for f in _vung_tu_do_thi(ke) if f.dt >= DT_RANH_TOI_THIEU]
    return ra, dong


# ---------------------------------------------------------------- số tờ
def _cat_nhau(a, b, c, d) -> bool:
    rx, ry = b[0] - a[0], b[1] - a[1]
    sx, sy = d[0] - c[0], d[1] - c[1]
    m = rx * sy - ry * sx
    if abs(m) < 1e-12:
        return False
    t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / m
    w = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / m
    return 0 <= t <= 1 and 0 <= w <= 1


def _so_to_cua(chu: str) -> str:
    m = re.search(r'(\d+)', chu or '')
    return str(int(m.group(1))) if m else ''


class TimTo:
    """Số tờ của một điểm: nhãn "Tờ số n" gần nhất mà đoạn nối KHÔNG cắt đường ranh tờ. Đường ranh tờ = lớp nằm giữa các cặp nhãn "Tờ a | Tờ b" và ngắn so với số
    lần cắt (lớp lưới thửa cũng cắt nhưng dài hơn nhiều)."""

    def __init__(self, bv: BanVe):
        self.nhan = [(_so_to_cua(n.chu), n.x, n.y) for n in bv.nhan if n.loai == 'to' and _so_to_cua(n.chu)]
        self.ranh = []
        if not self.nhan:
            return
        cap, da = [], set()
        for i, a in enumerate(self.nhan):
            if i in da:
                continue
            tot, dm = None, CAP_NHAN_TO_TOI_DA
            for j, b in enumerate(self.nhan):
                if j != i and j not in da and a[0] != b[0]:
                    m = math.hypot(a[1] - b[1], a[2] - b[2])
                    if m < dm:
                        tot, dm = j, m
            if tot is not None:
                da |= {i, tot}
                cap.append((a[1:], self.nhan[tot][1:]))
        theo, dai = defaultdict(list), defaultdict(float)
        for d in bv.duong:
            theo[d.nhom].append(d)
            dai[d.nhom] += sum(math.hypot(d.diem[i + 1][0] - d.diem[i][0], d.diem[i + 1][1] - d.diem[i][1]) for i in range(len(d.diem) - 1))
        for k, ds in theo.items():
            lan = sum(1 for a, b in cap if any(_cat_nhau(a, b, d.diem[i], d.diem[i + 1]) for d in ds for i in range(len(d.diem) - 1)))
            if lan and dai[k] / lan <= DUONG_RANH_TO_MOI_CAT:
                self.ranh += _doan_cua(ds)

    def tim(self, x: float, y: float) -> tuple:
        """(số tờ, chắc chắn?). Không có nhãn nào thấy được: nhãn gần nhất, chắc chắn = False."""
        if not self.nhan:
            return '', False
        ds = sorted(self.nhan, key=lambda n: (n[1] - x) ** 2 + (n[2] - y) ** 2)
        for so, a, b in ds:
            if not any(_cat_nhau((x, y), (a, b), s[0], s[1]) for s in self.ranh):
                return so, bool(self.ranh)
        return ds[0][0], False


# ---------------------------------------------------------------- bản vẽ đường -> thửa
def _kc_diem_vong(p, vong: list) -> float:
    return min(_khoang_cach_doan(p, vong[i], vong[(i + 1) % len(vong)]) for i in range(len(vong)))


def _dt_trong_ranh(f: VungVe, ranh: list, tam_giac: list, hop_ranh: list) -> float:
    tr = 0.0
    for j, r in enumerate(ranh):
        if _cham_hop(f.hop, hop_ranh[j]):
            tr += dien_tich_giao(f.vong, r.vong, tam_giac[j]) - sum(dien_tich_giao(v, r.vong, tam_giac[j]) for v in f.lo)
    return max(tr, 0.0)


def _trong_ranh(ranh: list, hop_ranh: list, x: float, y: float) -> bool:
    return any(h[0] <= x <= h[2] and h[1] <= y <= h[3] and chua_diem(r.vong, x, y) for r, h in zip(ranh, hop_ranh))


def ghep_thua(ds: list, kinh_tuyen: float, so_to: str = '', nguon: str = '', ranh_da_giac: list | None = None) -> KetQuaCad:
    """[PlacemarkKml] của bản vẽ đường -> KetQuaCad như bản vẽ có đa giác (lưu bằng ban_do_cad.luu). Mỗi thửa kèm chi_tiet: doi_chieu, ly_do, phan (nhãn diện tích
    từng phần: trong / ngoài ranh), moc, ghi_chu, neo (điểm đặt số thửa), vung_phu (vùng thêm khi một số thửa có nhiều vùng). ranh_da_giac: các vòng ranh thu hồi
    đã có sẵn dạng đa giác trong file (khỏi dò đường ranh)."""
    from .toa_do import chu_kinh_tuyen
    kq = KetQuaCad(nguon=nguon, so_to=str(so_to or ''))
    bv = doc_ban_ve(ds, kinh_tuyen)
    lop_luoi, vung = chon_lop_luoi(bv)
    kq.lop_thua = f'tự ghép từ đường ({", ".join(sorted({k[1] for k in lop_luoi}))}; kinh tuyến trục {chu_kinh_tuyen(kinh_tuyen)})' if lop_luoi else ''
    kq.thong_ke = dict(so_vung=len(vung), so_duong=len(bv.duong), so_nhan=len(bv.nhan), so_vong_moc=len(bv.vong_moc))
    if not vung:
        return kq
    if ranh_da_giac:
        ranh, dong = [VungVe(list(v), dien_tich(v), hop=_hop_bao(v)) for v in ranh_da_giac], []
    else:
        ranh, dong = tim_ranh(bv, lop_luoi)
    kq.ranh_vung = [[list(p) for p in r.vong] for r in ranh]
    kq.ranh_dong = [[list(a), list(b)] for a, b in dong]
    if ranh:
        kq.lop_ranh = 'đường qua mốc ranh'
    tam_giac = [tam_giac_hoa(r.vong) for r in ranh]
    hop_ranh = [r.hop for r in ranh]
    tim_to = TimTo(bv)
    cm = _ChiMucVung(vung)
    theo = defaultdict(lambda: defaultdict(list))
    ngoai_vung = []
    for n in bv.nhan:
        if n.loai in ('thua', 'ld', 'dt', 'dt_th', 'ghi_chu'):
            i = cm.tim(n.x, n.y)
            if i is None:
                if n.loai == 'thua':
                    ngoai_vung.append(n)
            else:
                theo[i][n.loai].append(n)
    # mốc: tâm vòng tròn (chính xác) mang tên nhãn mốc gần nhất
    moc = _moc_co_ten(bv)
    chua_tach = _tach_nhieu_so(vung, theo, ngoai_vung)
    # gom vùng theo (tờ, thửa)
    theo_so = defaultdict(list)
    for i, f in enumerate(vung):
        nhan_so = theo[i].get('thua', [])
        so = {so_thua_chuan(n.chu) for n in nhan_so}
        if len(so) != 1:
            continue
        n0 = nhan_so[0]
        to, chac = (str(so_to), True) if so_to else tim_to.tim(n0.x, n0.y)
        theo_so[(to, next(iter(so)))].append((i, n0, chac))
    kq.chua_tach = chua_tach
    kq.khong_khep = [dict(so_thua=so_thua_chuan(n.chu), x=n.x, y=n.y, trong_ranh=_trong_ranh(ranh, hop_ranh, n.x, n.y)) for n in ngoai_vung]
    nhan_phan = [n for n in bv.nhan if n.loai in ('dt', 'dt_th')]
    for (to, thua), ds_vung in theo_so.items():
        kq.thua.append(_thua_tu_vung(to, thua, ds_vung, vung, theo, ranh, tam_giac, hop_ranh, dong, moc, nhan_phan))
    kq.thua.sort(key=lambda t: (_sap_so(t.so_to), _sap_so(t.so_thua)))
    _ghi_canh_bao(kq, ranh, dong)
    kq.so_to = kq.so_to or ', '.join(sorted({t.so_to for t in kq.thua if t.so_to}, key=_sap_so))
    return kq


def _kc2(a, b) -> float:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def _cap_so_dt(nhan_so: list, nhan_dt: list) -> dict:
    """{id(nhãn số): nhãn DT gần nhất chưa dùng} (cặp gần trước, dưới CAP_NHAN_DT m)."""
    ds = sorted((_kc2(a, b), i, j) for i, a in enumerate(nhan_so) for j, b in enumerate(nhan_dt) if _kc2(a, b) <= CAP_NHAN_DT ** 2)
    cap, da_so, da_dt = {}, set(), set()
    for _m, i, j in ds:
        if i not in da_so and j not in da_dt:
            cap[id(nhan_so[i])] = nhan_dt[j]
            da_so.add(i)
            da_dt.add(j)
    return cap


def _chuyen_nhan(goc: dict, dich: dict, n0, cap_dt) -> None:
    """Chuyển số thửa n0 (kèm nhãn DT của nó, nhãn loại đất gần nhất) từ vùng goc sang vùng dich."""
    goc['thua'].remove(n0)
    dich.setdefault('thua', []).append(n0)
    if cap_dt is not None:
        goc['dt'].remove(cap_dt)
        dich.setdefault('dt', []).append(cap_dt)
    ld = sorted((x for x in goc.get('ld', ()) if _kc2(x, n0) <= GAN_NHAN_LD ** 2), key=lambda x: _kc2(x, n0))
    if ld:
        goc['ld'].remove(ld[0])
        dich.setdefault('ld', []).append(ld[0])


def _tach_nhieu_so(vung: list, theo: dict, ngoai_vung: list) -> list:
    """Vùng có nhiều số thửa khác nhau. Số có nhãn DT khớp diện tích vùng = chủ vùng; số còn lại (thửa hẹp đặt nhãn sang đây) về vùng không số gần đó có diện tích
    khớp nhãn DT của nó, không có thì thành số thửa không khép kín. Không xác định được chủ vùng: trả về danh sách chưa tách. Sửa theo, ngoai_vung tại chỗ."""
    chua_tach, le = [], []
    for i, f in enumerate(vung):
        nhan_so = theo[i].get('thua', []) if i in theo else []
        so = {so_thua_chuan(n.chu) for n in nhan_so}
        if len(so) < 2:
            continue
        nhan_dt = [n for n in theo[i].get('dt', ()) if so_nhan(n.chu)]
        cap = _cap_so_dt(nhan_so, nhan_dt)
        chu = {so_thua_chuan(n.chu) for n in nhan_so if id(n) in cap and _khop_dt(f.dt, so_nhan(cap[id(n)].chu))}
        if len(chu) != 1:
            chua_tach.append(dict(so_thua=sorted(so), dt=round(f.dt, 1), vong=[list(p) for p in f.vong]))
            continue
        ten_chu = next(iter(chu))
        for n in [x for x in nhan_so if so_thua_chuan(x.chu) != ten_chu]:
            le.append((i, n, cap.get(id(n))))
    for i, n, cap_dt in le:
        v = so_nhan(cap_dt.chu) if cap_dt is not None else None
        tot, dm = None, TIM_VUNG_HEP
        if v:
            for j, f in enumerate(vung):
                if j in theo and theo[j].get('thua'):
                    continue
                h = f.hop
                if h[0] - dm <= n.x <= h[2] + dm and h[1] - dm <= n.y <= h[3] + dm and _khop_dt(f.dt, v):
                    m = _kc_diem_vong((n.x, n.y), f.vong)
                    if m < dm:
                        tot, dm = j, m
        if tot is not None:
            _chuyen_nhan(theo[i], theo[tot], n, cap_dt)
        else:
            theo[i]['thua'].remove(n)
            if cap_dt is not None:
                theo[i]['dt'].remove(cap_dt)
            ngoai_vung.append(n)
    return chua_tach


def _sap_so(s) -> tuple:
    m = re.match(r'(\d+)(.*)', str(s))
    return (int(m.group(1)), m.group(2)) if m else (10 ** 9, str(s))


def _moc_co_ten(bv: BanVe) -> list:
    """[(tên, x, y)]: nhãn mốc đặt lệch cọc (file thật tới 25 m) - tọa độ lấy tâm vòng tròn gần nhất chưa có tên, không có vòng thì lấy điểm đặt nhãn."""
    moc = [n for n in bv.nhan if n.loai == 'moc']
    if not moc:
        return []
    cap = sorted(((math.hypot(n.x - v[0], n.y - v[1]), i, j) for i, n in enumerate(moc) for j, v in enumerate(bv.vong_moc)
                  if abs(n.x - v[0]) <= 30 and abs(n.y - v[1]) <= 30), key=lambda x: x[0])
    gan, dung = {}, set()
    for _m, i, j in cap:
        if i not in gan and j not in dung:
            gan[i] = j
            dung.add(j)
    return [(n.chu, *(bv.vong_moc[gan[i]] if i in gan else (n.x, n.y))) for i, n in enumerate(moc)]


def _tap_gan_nhat(muc_tieu: float, ds: list, sai: float):
    """Tổng của tập con ds gần muc_tieu nhất, trong khoảng sai | None. Không so từng nhãn: một phần đất có thể nằm ở nhiều nhãn, nhãn phần nhỏ đặt lệch vị trí."""
    tong = [0.0]
    for v in ds[:SO_NHAN_TAP_CON]:
        tong += [x + v for x in tong]
    tot = None
    for t in tong[1:]:
        m = abs(t - muc_tieu)
        if m <= sai and (tot is None or m < abs(tot - muc_tieu)):
            tot = t
    return tot


def doi_chieu_thu_hoi(hinh: float, dt_thua: float, phan: list, lan_can: list) -> tuple:
    """DT trong ranh hình học so với nhãn: (giá trị theo nhãn, cách khớp) hoặc (None, ''). Cách khớp: 'cong' = tổng các nhãn phần trong thửa; 'tru' = DT thửa trừ các
    phần ngoài ranh; 'lan_can' = có nhãn đặt lệch sang bên cạnh. Nhãn là con số chính thức của người đo, hình học là phép kiểm: lệch thì không khớp."""
    sai = max(SAI_THU_HOI_TUYET_DOI, hinh * SAI_THU_HOI_TUONG_DOI)
    t = _tap_gan_nhat(hinh, [v for v in phan if v <= hinh + sai], sai)
    if t is not None:
        return t, 'cong'
    con = dt_thua - hinh
    if con > 0:
        t = _tap_gan_nhat(con, [v for v in phan if v <= con + sai], sai)
        if t is not None:
            return dt_thua - t, 'tru'
    t = _tap_gan_nhat(hinh, [v for v in (*phan, *lan_can) if v <= hinh + sai], sai)
    if t is not None:
        return t, 'lan_can'
    return None, ''


def _thua_tu_vung(to, thua, ds_vung, vung, theo, ranh, tam_giac, hop_ranh, dong, moc, nhan_phan) -> ThuaCad:
    ds_f = [vung[i] for i, _n, _c in ds_vung]
    chinh_i = max(range(len(ds_f)), key=lambda k: ds_f[k].dt)
    chinh = ds_f[chinh_i]
    tong = sum(f.dt for f in ds_f)
    nhan = defaultdict(list)
    for i, _n, _c in ds_vung:
        for k, v in theo[i].items():
            nhan[k] += v
    n0 = ds_vung[chinh_i][1]
    ly_do = []
    if len(ds_f) > 1:
        ly_do.append(f'Một số thửa có {len(ds_f)} vùng trên bản vẽ')
    if not all(c for _i, _n, c in ds_vung):
        ly_do.append('Số tờ chưa chắc (không có ranh tờ / nhãn tờ để xác định)')
    # loại đất: nhãn gần số thửa nhất
    ld = sorted(nhan.get('ld', ()), key=lambda n: (n.x - n0.x) ** 2 + (n.y - n0.y) ** 2)
    loai = re.sub(r'\s*\+\s*', '+', ld[0].chu).upper() if ld else ''
    # diện tích nhãn: nhãn khớp hình nhất; không khớp thì nhãn lớn nhất (DT nguyên thửa)
    so_dt = [(so_nhan(n.chu), n) for n in nhan.get('dt', ())]
    so_dt = [x for x in so_dt if x[0]]
    dt_nhan, dt_khop = None, False
    if so_dt:
        gan = min(so_dt, key=lambda x: abs(x[0] - tong))
        if _khop_dt(tong, gan[0]):
            dt_nhan, dt_khop = gan[1], True
        else:
            dt_nhan = max(so_dt, key=lambda x: x[0])[1]
    doi_dt = 'khop' if dt_khop else ('lech' if dt_nhan is not None else 'chua_co_nhan')
    if doi_dt == 'lech':
        ly_do.append(f'DT hình {tong:.1f} m² khác nhãn {so_nhan(dt_nhan.chu):.1f} m²')
    # các phần diện tích ghi trên bản vẽ ("(1331,3)", và nhãn không phải DT nguyên thửa)
    phan = []
    for n in (*nhan.get('dt_th', ()), *nhan.get('dt', ())):
        if n is dt_nhan:
            continue
        v = so_nhan(n.chu)
        if v:
            phan.append(dict(dt=v, trong=_trong_ranh(ranh, hop_ranh, n.x, n.y) if ranh else None))
    # DT thu hồi: giao hình học là phép đo, nhãn là con số chính thức: khớp thì lấy nhãn, không khớp thì lấy hình học và báo
    trong, doi_th, dt_th_hinh, nhan_trong = None, 'khong_ranh', None, None
    if ranh:
        dt_th_hinh = sum(_dt_trong_ranh(f, ranh, tam_giac, hop_ranh) for f in ds_f)
        dt_thua = so_nhan(dt_nhan.chu) if dt_khop else tong
        gia_tri = [p['dt'] for p in phan]
        if dt_th_hinh <= SAI_THU_HOI_TUYET_DOI:
            trong, doi_th = 0.0, 'ngoai_ranh'
        elif abs(dt_th_hinh - tong) <= SAI_THU_HOI_TUYET_DOI:
            trong, doi_th = dt_thua, 'ca_thua'           # nằm trọn trong ranh
        else:
            nhan_trong, cach = doi_chieu_thu_hoi(dt_th_hinh, dt_thua, gia_tri, _nhan_lan_can(chinh, nhan_phan, nhan))
            if nhan_trong is not None:
                trong, doi_th = nhan_trong, 'khop'
            elif gia_tri:
                trong, doi_th = dt_th_hinh, 'lech'
                ly_do.append(f'DT trong ranh hình học {dt_th_hinh:.1f} m² không khớp các nhãn: ' + ', '.join(f'{v:.1f}' for v in gia_tri[:6]))
            else:
                trong, doi_th = dt_th_hinh, 'chi_hinh'
                ly_do.append(f'Không có nhãn diện tích phần trong ranh để đối chiếu (hình học {dt_th_hinh:.1f} m²)')
        if dong and doi_th in ('lech', 'chi_hinh', 'ca_thua') and any(
                _cat_nhau(a, b, chinh.vong[i], chinh.vong[(i + 1) % len(chinh.vong)]) for a, b in dong for i in range(len(chinh.vong))):
            ly_do.append('Thửa ở đầu tuyến: ranh dừng ở mép bản vẽ, đoạn đóng đầu tuyến là ước lượng')
    ten_moc = sorted({m[0] for m in moc if chinh.hop[0] - GAN_MOC <= m[1] <= chinh.hop[2] + GAN_MOC and chinh.hop[1] - GAN_MOC <= m[2] <= chinh.hop[3] + GAN_MOC
                      and (chua_diem(chinh.vong, m[1], m[2]) or _kc_diem_vong(m[1:], chinh.vong) <= GAN_MOC)})
    ghi_chu = sorted({n.chu for n in nhan.get('ghi_chu', ())})
    ct = dict(doi_chieu=dict(dt=doi_dt, thu_hoi=doi_th), ly_do=ly_do, phan=phan, moc=ten_moc, ghi_chu=ghi_chu, neo=[round(n0.x, 3), round(n0.y, 3)],
              dt_th_hinh=None if dt_th_hinh is None else round(dt_th_hinh, 1), dt_nhan_trong=None if nhan_trong is None else round(nhan_trong, 1))
    if len(ds_f) > 1:
        ct['vung_phu'] = [[[round(x, 3), round(y, 3)] for x, y in f.vong] for k, f in enumerate(ds_f) if k != chinh_i]
    if chinh.lo:
        ct['so_lo'] = len(chinh.lo)
    chu_nhan = ' | '.join(x for x in (thua, loai, dt_nhan.chu if dt_nhan is not None else '', *ghi_chu) if x)
    return ThuaCad(to, thua, loai, None if dt_nhan is None else D(f'{so_nhan(dt_nhan.chu):.1f}'), D(f'{tong:.1f}'),
                   None if trong is None else D(f'{trong:.1f}'), [[round(x, 3), round(y, 3)] for x, y in chinh.vong], chu_nhan[:500], kq_lop(n0), ct)


def _nhan_lan_can(f: VungVe, nhan_phan: list, cua_thua: dict) -> list:
    """Giá trị các nhãn diện tích ngoài thửa nhưng cách ranh thửa dưới NHAN_LECH_TOI_DA m (gần trước), tối đa 8 nhãn."""
    da = {id(n) for k in ('dt', 'dt_th') for n in cua_thua.get(k, ())}
    h = f.hop
    ds = []
    for n in nhan_phan:
        if id(n) in da or not (h[0] - NHAN_LECH_TOI_DA <= n.x <= h[2] + NHAN_LECH_TOI_DA and h[1] - NHAN_LECH_TOI_DA <= n.y <= h[3] + NHAN_LECH_TOI_DA):
            continue
        m = _kc_diem_vong((n.x, n.y), f.vong)
        v = so_nhan(n.chu)
        if v and m <= NHAN_LECH_TOI_DA:
            ds.append((m, v))
    return [v for _m, v in sorted(ds)[:8]]


def kq_lop(n: NhanVe) -> str:
    return ' · '.join(x for x in (n.ban_ve, n.lop) if x)


def _ghi_canh_bao(kq: KetQuaCad, ranh: list, dong: list) -> None:
    from .tien import so_vn
    if kq.chua_tach:
        vd = ', '.join('/'.join(x['so_thua'][:3]) for x in kq.chua_tach[:6])
        kq.canh_bao.append(f'{so_vn(len(kq.chua_tach))} vùng có nhiều số thửa ({vd}…): bản vẽ thiếu đường tách, chưa tạo thửa - kiểm tra bản vẽ gốc.')
    trong = [x for x in kq.khong_khep if x['trong_ranh']]
    if kq.khong_khep:
        kq.canh_bao.append(f'{so_vn(len(kq.khong_khep))} số thửa nằm ngoài vùng khép kín (bản vẽ không có đủ ranh của thửa)' +
                           (f', trong đó {so_vn(len(trong))} nằm trong ranh thu hồi: ' + ', '.join(x['so_thua'] for x in trong[:12]) if trong else '') + '.')
    lech = [t for t in kq.thua if t.chi_tiet.get('ly_do')]
    if lech:
        kq.canh_bao.append(f'{so_vn(len(lech))} thửa cần xem lại (cột Đối chiếu); các thửa này không được đánh dấu cập nhật sẵn.')
    if ranh and dong:
        kq.canh_bao.append(f'Ranh thu hồi dừng ở mép bản vẽ: đã đóng {so_vn(len(dong))} đầu tuyến bằng đoạn thẳng.')
    if not ranh:
        kq.canh_bao.append('Không nhận ra đường ranh thu hồi: chưa tính DT thu hồi theo bản vẽ.')
    if not any(t.so_to for t in kq.thua):
        kq.canh_bao.append('Không tìm thấy nhãn số tờ: nhập ở ô "Số tờ".')

