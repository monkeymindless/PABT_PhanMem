"""Nền ảnh vệ tinh cho bản đồ thửa trên máy tính (phương án đột phá 4, người dùng 30/10/2026). Không Qt.

Ô ảnh Web Mercator của Esri World Imagery (cùng nguồn với LARC Mobile), mức phóng chọn sao cho khung dự án cần <= O_TOI_DA ô. Ô đã tải
lưu đệm ở <thư mục máy>\\nen_ban_do\\esri\\<z>\\<x>\\<y>.<jpg|png> để xem lại khi mất mạng. Chỉ gửi TỌA ĐỘ Ô ẢNH (vị trí gần đúng
của khu dự án) tới máy chủ bản đồ - không gửi số liệu hộ; mặc định TẮT, người dùng bật ở cửa sổ bản đồ. Dữ liệu tải về phải là ảnh
JPEG / PNG (an_toan.nhan_dang_dau_tep), <= KICH_TOI_DA byte; ghi đệm qua file tạm + os.replace."""
from __future__ import annotations

import math
import os
from pathlib import Path

NGUON = 'esri'
URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
GHI_NGUON = 'Ảnh nền: Esri, Maxar, Earthstar Geographics và cộng đồng người dùng GIS'
Z_TOI_DA = 17                    # sâu hơn nhiều vùng Việt Nam chỉ có ảnh "Map data not yet available" (như LARC Mobile)
Z_ANH_TOI_DA = 19                # 05/11/2026 máy tính: thử tới mức này (khu Đồng Nai có ảnh thật tới 19); ô giữ chỗ bị nhận ra, giữ ảnh mức <= Z_TOI_DA làm nền
KHONG_CO_ANH = b''               # tai_o: máy chủ trả ô "Map data not yet available" (khác None = lỗi mạng)
# ô giữ chỗ của Esri World Imagery: JPEG giống hệt nhau ở mọi vị trí, mọi mức
CO_O_GIU_CHO = 2521
BAM_O_GIU_CHO = '9eafd300d61393184a4abc1d458564cfd1cd9b6f9c4e9c74687045c0a0e5b858'
Z_TOI_THIEU = 10
O_TOI_DA = 64                    # số ô tối đa một lần nạp (khung dự án lớn: mức phóng thấp hơn)
CHO_GIAY = 10
KICH_TOI_DA = 2_000_000
LE_KHUNG = 0.10                  # nới khung dự án mỗi phía 10%
KHUNG_VN = (8.0, 24.0, 101.5, 110.5)      # (vĩ độ min, max, kinh độ min, max) - ngoài khung: tọa độ bản vẽ không phải VN-2000


def o_tu_toa_do(vi_do: float, kinh_do: float, z: int) -> tuple:
    """(x, y) của ô Web Mercator chứa điểm."""
    n = 2 ** z
    vd = max(min(vi_do, 85.0511), -85.0511)
    x = int((kinh_do + 180.0) / 360.0 * n)
    r = math.radians(vd)
    y = int((1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def goc_o(z: int, x: int, y: int) -> tuple:
    """(vĩ độ, kinh độ) góc TRÊN-TRÁI của ô (x, y) mức z; (x + 1, y + 1) cho góc dưới-phải."""
    n = 2 ** z
    kd = x / n * 360.0 - 180.0
    vd = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return vd, kd


def trong_vn(khung: tuple) -> bool:
    vmin, vmax, kmin, kmax = khung
    a, b, c, d = KHUNG_VN
    return a <= vmin <= vmax <= b and c <= kmin <= kmax <= d


def ds_o(khung: tuple, toi_da: int = O_TOI_DA, z_toi_da: int = Z_TOI_DA) -> tuple:
    """khung (vĩ độ min, max, kinh độ min, max) -> (z, [(x, y)]): mức phóng sâu nhất mà khung (nới LE_KHUNG) cần <= toi_da ô."""
    vmin, vmax, kmin, kmax = khung
    dv, dk = (vmax - vmin) * LE_KHUNG, (kmax - kmin) * LE_KHUNG
    vmin, vmax, kmin, kmax = vmin - dv, vmax + dv, kmin - dk, kmax + dk
    for z in range(z_toi_da, Z_TOI_THIEU - 1, -1):
        x0, y0 = o_tu_toa_do(vmax, kmin, z)
        x1, y1 = o_tu_toa_do(vmin, kmax, z)
        if (x1 - x0 + 1) * (y1 - y0 + 1) <= toi_da or z == Z_TOI_THIEU:
            ds = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
            return z, ds[:toi_da]
    return Z_TOI_THIEU, []


def _esri(dv: str) -> str:
    return f'https://server.arcgisonline.com/ArcGIS/rest/services/{dv}/MapServer/tile/{{z}}/{{y}}/{{x}}'


# 31/10/2026 (người dùng: "xem bản đồ KML / KMZ vệ tinh trên máy tính y như mobile"): CÙNG các nền của LARC Mobile (di_dong NEN).
# LOP: mã lớp ảnh -> mẫu địa chỉ ô (mã cũng là tên thư mục đệm; 'esri' = ảnh vệ tinh như trước). NEN: loại nền -> (tên, [lớp dưới lên
# trên], mức phóng tối đa, ghi nguồn). OpenStreetMap: chỉ tải ô của vùng đang xem (chính sách sử dụng ô cấm tải hàng loạt).
LOP = {'esri': URL,
       'esri_duong': _esri('Reference/World_Transportation'),
       'esri_dia_danh': _esri('Reference/World_Boundaries_and_Places'),
       'esri_dia_hinh': _esri('World_Topo_Map'),
       'osm': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}
NEN = {'ve_tinh': ('Vệ tinh', ('esri',), Z_ANH_TOI_DA, GHI_NGUON),
       've_tinh_ten': ('Vệ tinh + tên đường, địa danh', ('esri', 'esri_duong', 'esri_dia_danh'), Z_ANH_TOI_DA,
                       'Ảnh nền, đường, địa danh: Esri, Maxar, Earthstar Geographics, HERE, Garmin'),
       'duong': ('Bản đồ đường phố', ('osm',), 19, '© Những người đóng góp OpenStreetMap'),
       'dia_hinh': ('Địa hình', ('esri_dia_hinh',), 18, 'Bản đồ địa hình: Esri, HERE, Garmin, USGS')}
NEN_MAC_DINH = 've_tinh_ten'
KHONG_NEN = 'khong_nen'          # ô "Nền bản đồ" của máy tính: không tải ảnh, không giữ ô nền trong cảnh - tô màu ô thửa nhẹ máy nhất
TEN_KHONG_NEN = 'Không nền'
O_TOI_DA_KHUNG = 80              # số ô tối đa của vùng đang xem (mỗi lớp) - nhiều hơn thì lùi một mức phóng


def z_cho_khung(m_moi_diem: float, vi_do: float, z_toi_da: int = Z_TOI_DA, z_toi_thieu: int = 3) -> int:
    """Mức phóng có điểm ảnh ô gần nhất với m_moi_diem (mét / điểm màn hình) ở vĩ độ đó."""
    if not m_moi_diem or m_moi_diem <= 0:
        return z_toi_da
    goc = 156543.03392 * math.cos(math.radians(max(min(vi_do, 85.0), -85.0)))      # mét / điểm ảnh ở z = 0
    z = int(round(math.log2(goc / m_moi_diem)))
    return max(z_toi_thieu, min(z_toi_da, z))


def o_cua_khung(khung: tuple, z: int, toi_da: int = O_TOI_DA_KHUNG, z_toi_thieu: int = 3) -> tuple:
    """khung (vĩ độ min, max, kinh độ min, max) đang xem -> (z, [(x, y)]) không quá toi_da ô (lùi mức phóng nếu cần)."""
    vmin, vmax, kmin, kmax = khung
    while True:
        x0, y0 = o_tu_toa_do(vmax, kmin, z)
        x1, y1 = o_tu_toa_do(vmin, kmax, z)
        if (x1 - x0 + 1) * (y1 - y0 + 1) <= toi_da or z <= z_toi_thieu:
            return z, [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)][:toi_da]
        z -= 1


def la_o_giu_cho(du: bytes) -> bool:
    """Ô "Map data not yet available" (không phải ảnh thật): không đặt lên bản đồ, không lưu đệm."""
    if len(du) != CO_O_GIU_CHO:
        return False
    import hashlib
    return hashlib.sha256(du).hexdigest() == BAM_O_GIU_CHO


def thu_muc_dem() -> Path:
    from .dia_phuong import thu_muc_may
    return thu_muc_may() / 'nen_ban_do' / NGUON


def _thu_muc_lop(lop: str) -> Path:
    goc = thu_muc_dem()
    return goc if lop == NGUON else goc.parent / lop


def file_dem(z: int, x: int, y: int, lop: str = NGUON) -> Path | None:
    """Ô đã lưu đệm (None: chưa có)."""
    goc = _thu_muc_lop(lop) / str(z) / str(x)
    for duoi in ('.jpg', '.png'):
        p = goc / f'{y}{duoi}'
        if p.is_file():
            return p
    return None


def _lay_mang(url: str) -> bytes:
    import urllib.request
    from . import __version__, an_toan
    req = urllib.request.Request(url, headers={'User-Agent': f'LARC/{__version__} (ban do thua dat)'})
    with urllib.request.urlopen(req, timeout=CHO_GIAY, context=an_toan.ngu_canh_tls()) as r:
        return r.read(KICH_TOI_DA + 1)


def tai_o(z: int, x: int, y: int, lay=None, lop: str = NGUON) -> bytes | None:
    """Ảnh của ô (lớp lop của LOP): đệm trước, không có thì tải (lay(url) -> bytes; mặc định HTTPS có kiểm chứng chỉ). Không phải
    JPEG / PNG, quá lớn, lỗi mạng, lớp lạ: None (không lưu đệm)."""
    from . import an_toan
    if lop not in LOP:
        return None
    p = file_dem(z, x, y, lop)
    if p is not None:
        try:
            du = p.read_bytes()
            return KHONG_CO_ANH if la_o_giu_cho(du) else du
        except OSError:
            pass
    try:
        du = (lay or _lay_mang)(LOP[lop].format(z=z, x=x, y=y))
    except Exception:                                   # noqa: BLE001 - mất mạng, hết giờ, chứng chỉ, 404: bỏ qua ô này
        return None
    if not du or len(du) > KICH_TOI_DA:
        return None
    if la_o_giu_cho(du):
        return KHONG_CO_ANH
    loai = an_toan.nhan_dang_dau_tep(du[:16])
    if loai not in ('jpeg', 'png'):
        return None
    dich = _thu_muc_lop(lop) / str(z) / str(x) / f'{y}.{"jpg" if loai == "jpeg" else "png"}'
    try:
        dich.parent.mkdir(parents=True, exist_ok=True)
        tam = dich.with_name(dich.name + '.tmp')
        tam.write_bytes(du)
        os.replace(tam, dich)
    except OSError:                                     # không ghi được đệm: vẫn dùng ảnh vừa tải
        pass
    return du
