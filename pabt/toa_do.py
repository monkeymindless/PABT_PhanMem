"""Quy đổi tọa độ WGS84 (GPS điện thoại, Google Earth, file .kml / .kmz) <-> VN-2000 (bản đồ địa chính, mét) - 1.0.32. Không Qt, chỉ
thư viện chuẩn (math) - chạy cả Python 3.8 bản Windows 7.

VN-2000: elipxoit WGS-84; phép chiếu Transverse Mercator múi 3° theo KINH TUYẾN TRỤC của tỉnh (Thông tư 973/2001/TT-TCĐC; hệ số tỷ lệ
k0 = 0,9999, Đông giả 500.000 m, Bắc giả 0) - tính bằng chuỗi Krüger bậc 6 (sai số dưới 1 mm trong múi). Chuyển datum VN-2000 -> WGS84
bằng 7 tham số Helmert (QĐ 05/2007/QĐ-BTNMT) theo quy ước "coordinate frame" - như EPSG "VN-2000 to WGS 84 (2)" và thư viện datum
VN2000.dty của Bentley MicroStation (phương pháp 9 = 7 tham số CS-MAP). Chuỗi proj4 hay gặp trên mạng "+towgs84=…,-0.00928836,
0.01975479,-0.00427372,…" hiểu cùng con số theo quy ước NGƯỢC (position vector) - lệch ~1 m. Đã so với PROJ (pyproj) - lệch < 1 mm.
Nguồn tham số: file datum Bentley (hồ sơ địa phương ban_do.file_datum, không ghi thì VN2000.dty trong thư mục cài Bentley nếu máy có -
người dùng 26/10/2026 "dùng file VN2000.dty làm nguồn"), không đọc được thì TOWGS84 gắn sẵn (cùng con số).
Tọa độ VN-2000 viết (đông, bắc) như bản vẽ DXF (trục X = Đông, Y = Bắc) - sổ địa chính Việt Nam ghi X = Bắc, Y = Đông: đừng lẫn.
Kinh tuyến trục: hồ sơ địa phương ban_do.kinh_tuyen_truc (độ thập phân hoặc "107°45'"), không ghi thì KINH_TUYEN_MAC_DINH (Đồng Nai).
"""
from __future__ import annotations
import math
import re

A = 6378137.0                           # bán trục lớn WGS-84 (m)
F = 1 / 298.257223563                   # độ dẹt
K0 = 0.9999                             # hệ số tỷ lệ múi 3°
DONG_GIA = 500000.0                     # Đông giả (m)
# VN-2000 -> WGS84: dX, dY, dZ (m), quay rX, rY, rZ (giây cung, quy ước coordinate frame), tỷ lệ (ppm) - QĐ 05/2007/QĐ-BTNMT
TOWGS84 = (-191.90441429, -39.30318279, -111.45032835, -0.00928836, 0.01975479, -0.00427372, 0.252906278)
FILE_DATUM_BENTLEY = (r'C:\Program Files (x86)\Bentley\VN2000.dty', r'C:\Program Files\Bentley\VN2000.dty')
KINH_TUYEN_MAC_DINH = 107.75            # 107°45' - Đồng Nai
# kinh tuyến trục hay gặp (gợi ý ô chọn); tỉnh khác ghi ở hồ sơ địa phương
DS_KINH_TUYEN = (103.0, 104.0, 104.5, 104.75, 105.0, 105.5, 105.75, 106.0, 106.25, 106.5, 107.0, 107.25, 107.5, 107.75, 108.0,
                 108.25, 108.5)

_E2 = F * (2 - F)
_N = F / (2 - F)
_A_HOA = A / (1 + _N) * (1 + _N ** 2 / 4 + _N ** 4 / 64 + _N ** 6 / 256)
_ALPHA = (_N / 2 - 2 / 3 * _N ** 2 + 5 / 16 * _N ** 3 + 41 / 180 * _N ** 4 - 127 / 288 * _N ** 5 + 7891 / 37800 * _N ** 6,
          13 / 48 * _N ** 2 - 3 / 5 * _N ** 3 + 557 / 1440 * _N ** 4 + 281 / 630 * _N ** 5 - 1983433 / 1935360 * _N ** 6,
          61 / 240 * _N ** 3 - 103 / 140 * _N ** 4 + 15061 / 26880 * _N ** 5 + 167603 / 181440 * _N ** 6,
          49561 / 161280 * _N ** 4 - 179 / 168 * _N ** 5 + 6601661 / 7257600 * _N ** 6,
          34729 / 80640 * _N ** 5 - 3418889 / 1995840 * _N ** 6,
          212378941 / 319334400 * _N ** 6)
_BETA = (_N / 2 - 2 / 3 * _N ** 2 + 37 / 96 * _N ** 3 - 1 / 360 * _N ** 4 - 81 / 512 * _N ** 5 + 96199 / 604800 * _N ** 6,
         1 / 48 * _N ** 2 + 1 / 15 * _N ** 3 - 437 / 1440 * _N ** 4 + 46 / 105 * _N ** 5 - 1118711 / 3870720 * _N ** 6,
         17 / 480 * _N ** 3 - 37 / 840 * _N ** 4 - 209 / 4480 * _N ** 5 + 5569 / 90720 * _N ** 6,
         4397 / 161280 * _N ** 4 - 11 / 504 * _N ** 5 - 830251 / 7257600 * _N ** 6,
         4583 / 161280 * _N ** 5 - 108847 / 3991680 * _N ** 6,
         20648693 / 638668800 * _N ** 6)
_GIAY = math.pi / (180 * 3600)


def doc_kinh_tuyen(x) -> float:
    """107.75 / "107.75" / "107,75" / "107°45'" / "107 45" -> độ thập phân. Sai -> ValueError."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        v = float(x)
    else:
        s = str(x or '').strip().replace(',', '.')
        m = re.fullmatch(r"(\d{2,3})\s*(?:°|độ|\s)\s*(\d{1,2}(?:\.\d+)?)\s*(?:'|′|phút)?", s)
        v = int(m.group(1)) + float(m.group(2)) / 60 if m else float(s)
    if not 100 <= v <= 115:
        raise ValueError(f'Kinh tuyến trục {x} nằm ngoài lãnh thổ Việt Nam (100° - 115°).')
    return v


def kinh_tuyen_truc() -> float:
    """Kinh tuyến trục VN-2000 của tỉnh (hồ sơ địa phương ban_do.kinh_tuyen_truc), không ghi / sai -> 107°45'."""
    try:
        from . import dia_phuong
        v = dia_phuong.lay('ban_do.kinh_tuyen_truc')
        return doc_kinh_tuyen(v) if v not in (None, '') else KINH_TUYEN_MAC_DINH
    except Exception:                                    # noqa: BLE001 - hồ sơ hỏng: dùng mặc định
        return KINH_TUYEN_MAC_DINH


def chu_kinh_tuyen(v: float) -> str:
    """107.75 -> "107°45'"."""
    d = int(v)
    p = round((v - d) * 60, 2)
    return f"{d}°{p:g}'" if p else f'{d}°'


# ---------------------------------------------------------------- Transverse Mercator (chuỗi Krüger)
def _thuan(phi: float, lam: float, lam0: float) -> tuple:
    """(vĩ độ, kinh độ) radian -> (đông, bắc) mét trên mặt chiếu."""
    e = math.sqrt(_E2)
    t = math.sinh(math.atanh(math.sin(phi)) - e * math.atanh(e * math.sin(phi)))
    dl = lam - lam0
    xi = math.atan2(t, math.cos(dl))
    eta = math.atanh(math.sin(dl) / math.sqrt(1 + t * t))
    x, y = eta, xi
    for j, a in enumerate(_ALPHA, start=1):
        x += a * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
        y += a * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
    return DONG_GIA + K0 * _A_HOA * x, K0 * _A_HOA * y


def _nghich(dong: float, bac: float, lam0: float) -> tuple:
    """(đông, bắc) mét -> (vĩ độ, kinh độ) radian (nghịch Krüger + lặp vĩ độ)."""
    xi = bac / (K0 * _A_HOA)
    eta = (dong - DONG_GIA) / (K0 * _A_HOA)
    xi1, eta1 = xi, eta
    for j, b in enumerate(_BETA, start=1):
        xi1 -= b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta1 -= b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    tau1 = math.sin(xi1) / math.sqrt(math.sinh(eta1) ** 2 + math.cos(xi1) ** 2)
    lam = lam0 + math.atan2(math.sinh(eta1), math.cos(xi1))
    e = math.sqrt(_E2)
    tau = tau1                                          # vĩ độ thực từ vĩ độ bảo giác (Newton, Karney 2011)
    for _ in range(6):
        sig = math.sinh(e * math.atanh(e * tau / math.sqrt(1 + tau * tau)))
        tau_p = tau * math.sqrt(1 + sig * sig) - sig * math.sqrt(1 + tau * tau)
        d = (tau1 - tau_p) / math.sqrt(1 + tau_p * tau_p) * (1 + (1 - _E2) * tau * tau) / ((1 - _E2) * math.sqrt(1 + tau * tau))
        tau += d
        if abs(d) < 1e-14:
            break
    return math.atan(tau), lam


# ---------------------------------------------------------------- chuyển datum (Helmert 7 tham số)
def _dia_tam(phi: float, lam: float, h: float = 0.0) -> tuple:
    n = A / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    return ((n + h) * math.cos(phi) * math.cos(lam), (n + h) * math.cos(phi) * math.sin(lam), (n * (1 - _E2) + h) * math.sin(phi))


def _trac_dia(x: float, y: float, z: float) -> tuple:
    p = math.hypot(x, y)
    lam = math.atan2(y, x)
    phi = math.atan2(z, p * (1 - _E2))
    for _ in range(10):
        n = A / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
        h = p / math.cos(phi) - n
        moi = math.atan2(z, p * (1 - _E2 * n / (n + h)))
        if abs(moi - phi) < 1e-13:
            phi = moi
            break
        phi = moi
    n = A / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    return phi, lam, p / math.cos(phi) - n


def doc_file_datum(file, ten: str = 'VN2000') -> tuple | None:
    """Thư viện datum CS-MAP của Bentley (.dty, nhị phân): bản ghi `ten` -> ((dX, dY, dZ, rX, rY, rZ, ppm), quy ước 'coordinate_frame' /
    'position_vector'). Bản ghi cs_Dtdef_: tên [0:24], elipxoit [24:48], 7 số thực từ byte 152, mã phương pháp (short) ở byte 338 (9 =
    7 tham số = coordinate frame, 3 = Bursa-Wolf = position vector). Không có / sai -> None."""
    import struct
    from pathlib import Path
    try:
        b = Path(file).read_bytes()
    except OSError:
        return None
    if b[:4] != b'\x82\x19\x13\x02':                    # dấu thư viện datum CS-MAP
        return None
    khoa = ten.encode('ascii') + b'\x00'
    i = b.find(khoa)
    while i >= 0:
        if i + 344 <= len(b) and b[i + 24:i + 30] == b'WGS84\x00':
            ts = list(struct.unpack('<7d', b[i + 152:i + 208]))
            if ts[6] > 0.5:                             # tỷ lệ ghi dạng hệ số (1,000000252906278) -> ppm
                ts[6] = (ts[6] - 1) * 1e6
            pp = struct.unpack('<h', b[i + 338:i + 340])[0]
            quy_uoc = {9: 'coordinate_frame', 3: 'position_vector'}.get(pp)
            if (quy_uoc and all(abs(v) < 1000 for v in ts[:3]) and all(abs(v) < 60 for v in ts[3:6]) and abs(ts[6]) < 100):
                return tuple(ts), quy_uoc
        i = b.find(khoa, i + 1)
    return None


_NHO_DATUM: dict = {}
_CO_DINH = [0, None]                                    # [số tầng co_dinh_datum đang mở, tham số]


class co_dinh_datum:
    """`with toa_do.co_dinh_datum():` đổi hàng chục nghìn điểm một lượt (vẽ bản đồ, phân tích bản vẽ): chỉ đọc hồ sơ + stat file datum một lần (đo trên file thật: 16.000 lần stat
    chiếm 1/3 thời gian vẽ lại)."""

    def __enter__(self):
        if _CO_DINH[0] == 0:
            _CO_DINH[1] = None
            _CO_DINH[1] = tham_so_datum()
        _CO_DINH[0] += 1
        return self

    def __exit__(self, *_):
        _CO_DINH[0] -= 1
        if _CO_DINH[0] <= 0:
            _CO_DINH[0], _CO_DINH[1] = 0, None
        return False


def tham_so_datum() -> tuple:
    """((dX, dY, dZ, rX, rY, rZ, ppm), quy ước, nguồn): file datum Bentley (hồ sơ ban_do.file_datum / thư mục cài Bentley) nếu đọc được,
    không thì TOWGS84 gắn sẵn. Nhớ theo (đường dẫn, mtime)."""
    import os
    if _CO_DINH[1] is not None:
        return _CO_DINH[1]
    ung = []
    try:
        from . import dia_phuong
        f = dia_phuong.lay('ban_do.file_datum')
        if f:
            ung.append(str(f))
    except Exception:                                    # noqa: BLE001 - hồ sơ hỏng: thử đường dẫn mặc định
        pass
    ung.extend(FILE_DATUM_BENTLEY)
    for f in ung:
        try:
            khoa = (f, os.stat(f).st_mtime_ns)
        except OSError:
            continue
        if khoa not in _NHO_DATUM:
            _NHO_DATUM[khoa] = doc_file_datum(f)
        if _NHO_DATUM[khoa] is not None:
            ts, qu = _NHO_DATUM[khoa]
            return ts, qu, f
    return TOWGS84, 'coordinate_frame', 'QĐ 05/2007/QĐ-BTNMT (gắn sẵn)'


def _helmert(x: float, y: float, z: float, nguoc: bool) -> tuple:
    (dx, dy, dz, rx, ry, rz, s), quy_uoc, _ = tham_so_datum()
    if quy_uoc == 'coordinate_frame':                   # coordinate frame = position vector đổi dấu góc quay
        rx, ry, rz = -rx, -ry, -rz
    rx, ry, rz, k = rx * _GIAY, ry * _GIAY, rz * _GIAY, 1 + s * 1e-6
    if not nguoc:                                       # VN-2000 -> WGS84
        return (dx + k * (x - rz * y + ry * z), dy + k * (rz * x + y - rx * z), dz + k * (-ry * x + rx * y + z))
    x, y, z = (x - dx) / k, (y - dy) / k, (z - dz) / k  # WGS84 -> VN-2000: ma trận quay chuyển vị
    return x + rz * y - ry * z, -rz * x + y + rx * z, ry * x - rx * y + z


# ---------------------------------------------------------------- dùng
def wgs84_sang_vn2000(vi_do: float, kinh_do: float, kinh_tuyen: float | None = None) -> tuple:
    """GPS (vĩ độ, kinh độ, độ) -> VN-2000 (đông, bắc) mét theo kinh tuyến trục (None = của tỉnh trong hồ sơ địa phương)."""
    lam0 = math.radians(kinh_tuyen if kinh_tuyen is not None else kinh_tuyen_truc())
    x, y, z = _helmert(*_dia_tam(math.radians(vi_do), math.radians(kinh_do)), nguoc=True)
    phi, lam, _ = _trac_dia(x, y, z)
    return _thuan(phi, lam, lam0)


def vn2000_sang_wgs84(dong: float, bac: float, kinh_tuyen: float | None = None) -> tuple:
    """VN-2000 (đông, bắc) mét -> GPS (vĩ độ, kinh độ) độ."""
    lam0 = math.radians(kinh_tuyen if kinh_tuyen is not None else kinh_tuyen_truc())
    phi, lam = _nghich(dong, bac, lam0)
    x, y, z = _helmert(*_dia_tam(phi, lam), nguoc=False)
    phi, lam, _ = _trac_dia(x, y, z)
    return math.degrees(phi), math.degrees(lam)


def khoang_cach_m(vd1: float, kd1: float, vd2: float, kd2: float) -> float:
    """Khoảng cách mặt đất giữa hai điểm GPS (công thức haversine, bán kính trung bình 6.371.008,8 m)."""
    p1, p2 = math.radians(vd1), math.radians(vd2)
    dp, dl = p2 - p1, math.radians(kd2 - kd1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))
