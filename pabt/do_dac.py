"""Đo đạc và định vị trên bản đồ thửa đất (05/11/2026). Không Qt, chỉ thư viện chuẩn.

Đo trên MẶT CHIẾU VN-2000 (mét) như bản đồ địa chính: chiều dài, diện tích khớp cách tính của hồ sơ đo đạc (không phải khoảng cách trên mặt elipxoit như Google Earth - trong
múi 3° hai cách lệch dưới 0,03%). Tọa độ: VN-2000 ghi theo quy ước sổ địa chính X = Bắc, Y = Đông; GPS = WGS84.

vi_tri_may: vị trí của máy qua dịch vụ định vị Windows (GPS rời / Wi-Fi), mức chính xác cao nhất; trả kèm sai số do Windows báo - vị trí theo Wi-Fi sai hàng chục tới hàng trăm mét,
KHÔNG dùng để xác định ranh thửa. Chạy PowerShell cố định, không gửi gì ngoài yêu cầu tới Windows; chạy ở luồng nền."""
from __future__ import annotations

import json
import math
import re
import subprocess

from .tien import so_vn, vn
from .toa_do import chu_kinh_tuyen, vn2000_sang_wgs84, wgs84_sang_vn2000

HA = 10000.0
GIAY_CHO_VI_TRI = 15             # Windows đang tìm vị trí: chờ tối đa ngần này giây
SAI_SO_THAM_KHAO = 30.0          # m: sai số lớn hơn thì báo "chỉ tham khảo"


def do_dai(diem: list) -> float:
    """Tổng chiều dài đường gấp khúc [(đông, bắc)] (mét)."""
    return sum(math.hypot(diem[i + 1][0] - diem[i][0], diem[i + 1][1] - diem[i][1]) for i in range(len(diem) - 1))


def cac_doan(diem: list) -> list:
    return [math.hypot(diem[i + 1][0] - diem[i][0], diem[i + 1][1] - diem[i][1]) for i in range(len(diem) - 1)]


def dien_tich(diem: list) -> float:
    """Diện tích đa giác [(đông, bắc)] (m²) - công thức Gauss, như diện tích hình thửa."""
    s = 0.0
    for i in range(len(diem)):
        x1, y1 = diem[i]
        x2, y2 = diem[(i + 1) % len(diem)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def chu_vi(diem: list) -> float:
    return do_dai(list(diem) + [diem[0]]) if len(diem) >= 2 else 0.0


def tu_cat(diem: list) -> bool:
    """Đa giác tự cắt (hai cạnh không kề nhau cắt nhau): công thức Gauss không còn là diện tích thật."""
    n = len(diem)
    if n < 4:
        return False

    def cat(a, b, c, d):
        m = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
        if abs(m) < 1e-12:
            return False
        t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / m
        w = ((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / m
        return 0 < t < 1 and 0 < w < 1
    for i in range(n):
        a, b = diem[i], diem[(i + 1) % n]
        for j in range(i + 2, n):
            if (j + 1) % n == i:
                continue
            if cat(a, b, diem[j], diem[(j + 1) % n]):
                return True
    return False


def _so_m(v: float, le: int = 2) -> str:
    return vn(v, le)


def chu_do_dai(m: float) -> str:
    """1.234,56 m; từ 1 km thêm (1,235 km)."""
    return f'{_so_m(m)} m' + (f' ({vn(m / 1000, 3)} km)' if m >= 1000 else '')


def chu_dien_tich(m2: float) -> str:
    """12.345,6 m² (1,2346 ha)."""
    return f'{_so_m(m2, 1)} m²' + (f' ({vn(m2 / HA, 4)} ha)' if m2 >= 1000 else '')


def _dms(do: float, duong: str, am: str) -> str:
    d = abs(do)
    a = int(d)
    p = int((d - a) * 60)
    g = (d - a - p / 60) * 3600
    return f'{a}°{p:02d}\'{g:05.2f}"{duong if do >= 0 else am}'


def chu_toa_do(dong: float, bac: float, kt: float) -> str:
    """Một dòng đủ VN-2000 + GPS (độ thập phân, độ phút giây) của điểm (đông, bắc)."""
    vd, kd = vn2000_sang_wgs84(dong, bac, kt)
    return (f'VN-2000 ({chu_kinh_tuyen(kt)}): X {_so_m(bac, 3)}  Y {_so_m(dong, 3)}  ·  GPS {vd:.7f}, {kd:.7f}  ·  '
            f'{_dms(vd, "B", "N")} {_dms(kd, "Đ", "T")}')


def ket_qua_do(che_do: str, diem: list, kt: float) -> str:
    """Chữ kết quả đo. che_do: 'duong' | 'vung' | 'diem'; diem: [(đông, bắc)]."""
    if not diem:
        return ''
    if che_do == 'diem':
        return chu_toa_do(diem[-1][0], diem[-1][1], kt)
    if che_do == 'vung':
        if len(diem) < 3:
            return f'Đo vùng: đã chọn {len(diem)} đỉnh - bấm thêm đỉnh, nhấp đúp hoặc chuột phải để kết thúc.'
        them = ' · CẢNH BÁO: các cạnh cắt nhau, diện tích không đúng - xóa và chấm lại theo một chiều' if tu_cat(diem) else ''
        return f'Đo vùng: diện tích {chu_dien_tich(dien_tich(diem))} · chu vi {chu_do_dai(chu_vi(diem))} · {so_vn(len(diem))} đỉnh{them}'
    if len(diem) < 2:
        return 'Đo đường: bấm điểm tiếp theo, nhấp đúp hoặc chuột phải để kết thúc.'
    doan = cac_doan(diem)
    chi_tiet = ' + '.join(_so_m(d) for d in doan[:12]) + (' + …' if len(doan) > 12 else '')
    return f'Đo đường: tổng {chu_do_dai(sum(doan))} · {so_vn(len(doan))} đoạn' + (f' ({chi_tiet})' if len(doan) > 1 else '')


# ---------------------------------------------------------------- đến tọa độ người dùng gõ
_RE_SO = r'[-+]?\d[\d.,\s]*\d|\d'


def _doc_so_toa_do(s: str) -> float:
    """'1.219.655,12', '1219655.12', '1 219 655,12', '410596' -> float."""
    t = re.sub(r'\s', '', s)
    if t.count(',') == 1 and (t.count('.') != 1 or t.rfind(',') > t.rfind('.')):
        t = t.replace('.', '').replace(',', '.')
    elif t.count('.') > 1:
        t = t.replace('.', '')
    else:
        t = t.replace(',', '')
    return float(t)


def doc_toa_do(chu: str, kt: float) -> tuple:
    """Chữ người dùng gõ -> (đông, bắc) VN-2000. Nhận: GPS "11.0217, 106.9567" (hoặc "11,0217 106,9567"), VN-2000 "X 1219655 Y 410596" (X = Bắc), hoặc hai số lớn liền nhau
    (số lớn hơn là Bắc). Sai -> ValueError (thông báo tiếng Việt)."""
    s = ' '.join(str(chu or '').split())
    if not s:
        raise ValueError('Chưa nhập tọa độ.')
    m = re.search(rf'X\s*[:=]?\s*({_RE_SO})\s*[,;]?\s*Y\s*[:=]?\s*({_RE_SO})', s, re.I)
    if m:
        bac, dong = _doc_so_toa_do(m.group(1)), _doc_so_toa_do(m.group(2))
        return dong, bac
    m = re.search(rf'Y\s*[:=]?\s*({_RE_SO})\s*[,;]?\s*X\s*[:=]?\s*({_RE_SO})', s, re.I)
    if m:
        dong, bac = _doc_so_toa_do(m.group(1)), _doc_so_toa_do(m.group(2))
        return dong, bac
    # "11,0217 106,9567" / "11.0217, 106.9567" / "1219655,12 ; 410596,33"
    phan = [x.strip(' ,') for x in re.split(r'\s*;\s*|\s+', s) if x.strip(' ,')]
    if len(phan) != 2 and s.count(',') == 1:
        phan = s.split(',')
    if len(phan) != 2:
        raise ValueError(f'Không đọc được tọa độ "{chu}". Gõ GPS "11.0217, 106.9567" hoặc VN-2000 "X 1219655 Y 410596".')
    try:
        a, b = _doc_so_toa_do(phan[0]), _doc_so_toa_do(phan[1])
    except ValueError:
        raise ValueError(f'Không đọc được tọa độ "{chu}". Gõ GPS "11.0217, 106.9567" hoặc VN-2000 "X 1219655 Y 410596".') from None
    if abs(a) <= 90 and abs(b) <= 180:
        return wgs84_sang_vn2000(a, b, kt)[:2]
    return (min(a, b), max(a, b))                       # Việt Nam: Bắc (X) > 900.000, Đông (Y) quanh 500.000


# ---------------------------------------------------------------- vị trí của máy (dịch vụ định vị Windows)
_LENH_VI_TRI = r"""
$ErrorActionPreference = 'Stop'
try {
  Add-Type -AssemblyName System.Device
  $w = New-Object System.Device.Location.GeoCoordinateWatcher([System.Device.Location.GeoPositionAccuracy]::High)
  $ok = $w.TryStart($false, [TimeSpan]::FromSeconds(%d))
  if (-not $ok) { '{"loi":"khong_khoi_dong"}'; exit }
  $tot = $null
  $het = (Get-Date).AddSeconds(%d)
  while ((Get-Date) -lt $het) {
    $p = $w.Position.Location
    if (-not $p.IsUnknown) {
      if ($tot -eq $null -or $p.HorizontalAccuracy -lt $tot.HorizontalAccuracy) { $tot = $p }
      if ($p.HorizontalAccuracy -le 10) { break }
    }
    if ($w.Permission -eq 'Denied') { break }
    Start-Sleep -Milliseconds 500
  }
  $quyen = [string]$w.Permission
  $w.Stop()
  if ($tot -eq $null) { '{"loi":"khong_co","quyen":"' + $quyen + '"}'; exit }
  $c = [System.Globalization.CultureInfo]::InvariantCulture
  '{"vd":' + $tot.Latitude.ToString($c) + ',"kd":' + $tot.Longitude.ToString($c) + ',"sai":' + $tot.HorizontalAccuracy.ToString($c) + '}'
} catch { '{"loi":"khong_ho_tro"}' }
"""


def vi_tri_may(chay=None, cho: int = GIAY_CHO_VI_TRI) -> dict:
    """{'vd', 'kd', 'sai'} hoặc {'loi': lời báo tiếng Việt}. chay(lệnh, hạn giây) -> chữ xuất ra (kiểm thử; mặc định PowerShell). Chạy ở LUỒNG NỀN (chờ tới vài chục giây)."""
    lenh = _LENH_VI_TRI % (cho, cho)
    try:
        if chay is not None:
            ra = chay(lenh, cho + 10)
        else:
            co = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            kq = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', lenh],
                                capture_output=True, text=True, timeout=cho + 10, creationflags=co)
            ra = kq.stdout
    except (OSError, subprocess.SubprocessError):
        return {'loi': 'Không gọi được dịch vụ định vị của Windows trên máy này.'}
    dong = [x for x in str(ra or '').splitlines() if x.strip().startswith('{')]
    try:
        d = json.loads(dong[-1])
    except (IndexError, ValueError):
        return {'loi': 'Dịch vụ định vị của Windows không trả kết quả.'}
    if 'loi' in d:
        if d.get('quyen') == 'Denied' or d['loi'] == 'khong_khoi_dong':
            return {'loi': 'Windows chưa cho phép ứng dụng dùng vị trí: bật ở Cài đặt > Quyền riêng tư > Vị trí, rồi bấm lại.'}
        if d['loi'] == 'khong_ho_tro':
            return {'loi': 'Windows trên máy này không có dịch vụ định vị. Gõ tọa độ đo được bằng máy GPS tại "Đến tọa độ…".'}
        return {'loi': 'Máy chưa xác định được vị trí (không có GPS / Wi-Fi). Gõ tọa độ đo được bằng máy GPS tại "Đến tọa độ…".'}
    try:
        return {'vd': float(d['vd']), 'kd': float(d['kd']), 'sai': float(d.get('sai') or 0)}
    except (KeyError, TypeError, ValueError):
        return {'loi': 'Dịch vụ định vị của Windows trả kết quả không đọc được.'}
