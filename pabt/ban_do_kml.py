"""Bản đồ .kml / .kmz (Google Earth, ứng dụng bản đồ điện thoại) <-> bản đồ thửa đất của dự án (1.0.32). Không Qt, chỉ thư viện chuẩn
(zipfile, xml.etree) - chạy cả bản Windows 7.

1. doc_kml: .kml (XML) / .kmz (file nén chứa doc.kml) -> [PlacemarkKml]: tên, mô tả, dữ liệu kèm (ExtendedData: Data / SimpleData),
   thư mục (Folder), đa giác (vòng ngoài + lỗ, MultiGeometry), đường, điểm - tọa độ WGS84 (kinh độ, vĩ độ). An toàn: chữ ký đầu tệp,
   chặn "bom nén" / đường dẫn vượt thư mục trong .kmz và XML có DOCTYPE / ENTITY.
2. phan_tich_kml: đa giác -> ThuaCad (như bản vẽ .dxf - lưu bằng ban_do_cad.luu vào bảng thua_ban_do): tọa độ đổi sang VN-2000 (toa_do,
   kinh tuyến trục của tỉnh), DT hình tính trên mặt chiếu như bản vẽ địa chính; số tờ / số thửa / loại đất / diện tích lấy từ dữ liệu kèm
   (so_to, so_thua, loai_dat, dien_tich… không phân biệt hoa thường, không dấu) hoặc tên ("Thửa 12 tờ 5", "5/12", "TK126-K6-L34");
   lô rừng: tờ = "TK<tiểu khu>/K<khoảnh>", thửa = lô (cùng cách ghi với phiếu kiểm đếm). Đa giác tên / thư mục có chữ "ranh" = ranh thu
   hồi -> DT trong ranh của từng thửa.
3. xuat_kml: bản đồ thửa của dự án -> .kml / .kmz (mỗi thửa một Placemark tô màu theo đồng thuận, dữ liệu kèm: tờ, thửa, loại đất, DT,
   mã hộ, chủ sử dụng) - mở bằng Google Earth / điện thoại.
"""
from __future__ import annotations
import html
import math
import os
import re
import xml.etree.ElementTree as ET
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from .ban_do_cad import KetQuaCad, LoiCad, ThuaCad, _cham_hop, _hop_bao, dien_tich, dien_tich_giao, doc_co_nho, tam_giac_hoa
from .sua_font_kml import sua_font_kml
from .tien import D

DUOI_KML = ('.kml', '.kmz')


@dataclass
class PlacemarkKml:
    ten: str = ''
    mo_ta: str = ''
    du_lieu: dict = field(default_factory=dict)          # {khóa chữ thường không dấu: giá trị}
    thu_muc: str = ''                                    # "Thư mục cha / thư mục con"
    da_giac: list = field(default_factory=list)          # [(vòng ngoài [(kđ, vđ)], [lỗ…])]
    duong: list = field(default_factory=list)
    diem: list = field(default_factory=list)
    mau_duong: str = ''                                  # '#RRGGBB' từ LineStyle (KML aabbggrr)
    rong_duong: float = 1.0
    mau_nhan: str = ''
    lop_cad: str = ''                                    # "Level 10" — mô tả MicroStation / gCadas
    ban_ve: str = ''                                     # "tanan2" trước dấu |


def _the(e) -> str:
    return e.tag.rsplit('}', 1)[-1] if isinstance(e.tag, str) else ''


def _khoa(s: str) -> str:
    from .lap_pa import bo_dau
    return re.sub(r'[^a-z0-9]+', '_', bo_dau(str(s or '')).lower()).strip('_')


def _toa_do(chu: str) -> list:
    """'106.9,10.9,0 107.0,11.0' -> [(106.9, 10.9), (107.0, 11.0)] (bỏ độ cao; cặp sai bỏ qua). Một số phần mềm CAD ghi
    cả đường bằng dấu phẩy, không có khoảng trắng ('lon,lat,alt,lon,lat,alt') — tách theo bộ ba."""
    kq = []
    raw = str(chu or '').strip()
    if not raw:
        return kq
    cap = raw.split()
    if len(cap) == 1 and cap[0].count(',') >= 5:
        so = cap[0].split(',')
        i = 0
        while i + 1 < len(so):
            try:
                kd, vd = float(so[i]), float(so[i + 1])
            except ValueError:
                i += 1
                continue
            if -180 <= kd <= 180 and -90 <= vd <= 90:
                kq.append((kd, vd))
            i += 3 if i + 2 < len(so) else 2
        return kq
    for t in cap:
        p = t.split(',')
        try:
            kd, vd = float(p[0]), float(p[1])
        except (IndexError, ValueError):
            continue
        if -180 <= kd <= 180 and -90 <= vd <= 90:
            kq.append((kd, vd))
    return kq


def _vong(e, giu_kin: bool = False) -> list:
    """Tọa độ trong phần tử. Vòng đa giác: bỏ điểm cuối trùng điểm đầu. giu_kin (đường LineString): giữ - đường khép kín mà mất đoạn cuối thì thửa vẽ bằng một đường liền bị hở."""
    for c in e.iter():
        if _the(c) == 'coordinates':
            p = _toa_do(''.join(c.itertext()) if c.text is None else c.text)
            if not giu_kin and len(p) >= 2 and p[0] == p[-1]:
                p.pop()
            return p
    return []


def _hinh(geo, pm: PlacemarkKml) -> None:
    t = _the(geo)
    if t == 'Polygon':
        ngoai, lo = [], []
        for c in geo:
            if _the(c) == 'outerBoundaryIs':
                ngoai = _vong(c)
            elif _the(c) == 'innerBoundaryIs':
                v = _vong(c)
                if len(v) >= 3:
                    lo.append(v)
        if len(ngoai) >= 3:
            pm.da_giac.append((ngoai, lo))
    elif t == 'LineString':
        p = _vong(geo, giu_kin=True)
        if len(p) >= 2:
            pm.duong.append(p)
    elif t == 'Point':
        p = _vong(geo)
        if p:
            pm.diem.append(p[0])
    elif t == 'MultiGeometry':
        for c in geo:
            _hinh(c, pm)


_RE_LOP_CAD = re.compile(r'^(?:([^|\n]{1,40})\|)?\s*(Level\s*[\w-]+|ghichu)\s*$', re.I)


def mau_kml_abgr(chu) -> str:
    """Màu KML 'aabbggrr' -> '#RRGGBB'; gần trong suốt (alpha < 16) hoặc sai định dạng -> ''."""
    c = str(chu or '').strip().lstrip('#')
    if not re.fullmatch(r'[0-9A-Fa-f]{8}', c) or int(c[:2], 16) < 16:
        return ''
    return f'#{c[6:8]}{c[4:6]}{c[2:4]}'.upper()


def lop_cad_tu_mo_ta(mo_ta: str) -> tuple:
    """Mô tả MicroStation/gCadas 'tanan2|Level 10' -> (bản vẽ, lớp CAD). Không khớp -> ('', '')."""
    m = _RE_LOP_CAD.match(str(mo_ta or '').strip())
    if not m:
        return '', ''
    return (m.group(1) or '').strip(), (m.group(2) or '').strip()


# 1.1.07: tên CAD / MicroStation / gCadas tự đặt ("Style1", "Style14", "Placemark 3", "Polygon_001"): không phải nhãn địa chính
TEN_TU_SINH = re.compile(r'(?:style|placemark|feature|point|line|polygon|polyline|path|text|cell|block)[ _-]?\d*', re.I)


def la_ten_tu_sinh(chu) -> bool:
    return bool(TEN_TU_SINH.fullmatch(str(chu or '').strip()))


def loai_nhan(chu: str, lop_cad: str = '') -> str:
    """Chữ của điểm KML -> loại nhãn địa chính (cùng quy tắc với LARC Mobile: loaiNhan). Tên tự sinh -> ký hiệu (bỏ qua)."""
    c = str(chu or '').strip()
    if not c or TEN_TU_SINH.fullmatch(c):
        return 'ky_hieu'
    if re.fullmatch(r'[A-Z]{1,3}\d?\.[A-Z]{1,2}\d+[A-Z]?', c) or (
            re.fullmatch(r'Level 4[45]', str(lop_cad or '')) and re.fullmatch(r'[A-Z0-9.\-]{2,12}', c)):
        return 'moc'
    if re.fullmatch(r'\d{1,4}(\s*/)?', c):
        return 'thua'
    if re.fullmatch(r'\(\s*\d+(?:[.,]\d+)?\s*\)', c):
        return 'dt_th'
    if re.fullmatch(r'\d+[.,]\d+', c):
        return 'dt'
    if re.fullmatch(r'[A-Z]{2,4}(?:\+[A-Z]{2,4})*', c):
        return 'ld'
    if re.match(r'^tờ\s*(?:bản\s*đồ\s*)?(?:số)?\s*\d+', c, re.I):
        return 'to'
    if len(c) <= 1:
        return 'ky_hieu'
    return 'ghi_chu'


NGUONG_NHAN = {'ld': 12.0, 'dt': 10.0, 'dt_th': 30.0}     # mét: ghép loại đất / DT về số thửa gần nhất


def gom_cum_nhan_thua(diem: list) -> list:
    """Các điểm đã phân loại (dict loai/x/y/chu, tọa độ mét) -> cụm nhãn thửa (số thửa + loại đất + DT)."""
    neo = [d for d in diem if d.get('loai') == 'thua']
    ra = []
    for a in neo:
        ra.append(dict(kieu='nhan_thua', neo=a, so_thua=re.sub(r'\s*/\s*$', '', str(a.get('chu') or '')),
                       x=a['x'], y=a['y'], ld=None, dt=None, dt_th=None, to=None,
                       lat=a.get('lat'), lon=a.get('lon'), lop_cad=a.get('lop_cad', ''), ban_ve=a.get('ban_ve', '')))
    theo = {id(a): ra[i] for i, a in enumerate(neo)}
    ds_to = [d for d in diem if d.get('loai') == 'to']
    for c in ra:
        tot, dm = None, 400.0
        for d in ds_to:
            m = ((d['x'] - c['x']) ** 2 + (d['y'] - c['y']) ** 2) ** 0.5
            if m < dm:
                tot, dm = d, m
        if tot is not None:
            c['to'] = tot
            c['cach_to'] = round(dm)
            mso = re.search(r'(\d+)', str(tot.get('chu') or ''))
            c['so_to'] = mso.group(1) if mso else ''
        else:
            c['so_to'] = ''
            c['cach_to'] = None
    for d in diem:
        gh = NGUONG_NHAN.get(d.get('loai') or '', 0)
        if not gh or not neo:
            continue
        tot, dm = None, gh
        for a in neo:
            m = ((a['x'] - d['x']) ** 2 + (a['y'] - d['y']) ** 2) ** 0.5
            if m < dm:
                tot, dm = a, m
        if tot is None:
            continue
        c, k = theo[id(tot)], d['loai']
        if c[k] is None or dm < c[k][1]:
            c[k] = (d, dm)
    for c in ra:
        c['chu_ld'] = c['ld'][0]['chu'] if c['ld'] else ''
        c['chu_dt'] = c['dt'][0]['chu'] if c['dt'] else ''
        c['chu_dt_th'] = re.sub(r'[()\s]', '', c['dt_th'][0]['chu']) if c['dt_th'] else ''
    return ra


def la_vong_moc_wgs(vong: list) -> bool:
    """Vòng tròn nhỏ quanh cọc mốc (tọa độ độ): ước lượng cạnh khung theo mét."""
    if len(vong) < SO_DINH_VONG_MOC:
        return False
    xs, ys = [p[0] for p in vong], [p[1] for p in vong]
    kx = 111320.0 * max(0.2, abs(math.cos(math.radians(ys[0]))))
    return max((max(xs) - min(xs)) * kx, (max(ys) - min(ys)) * 110540.0) < CO_VONG_MOC


def tom_tat_cad(ds: list) -> str:
    """Tóm tắt lớp KML CAD (đường ranh, nhãn thửa, mốc, ghi chú) — cùng nội dung với LARC Mobile."""
    n_duong = sum(1 for pm in ds for d in pm.duong if not la_vong_moc_wgs(d))   # vòng tròn quanh cọc mốc không phải đường ranh, đa giác thửa
    n_vung = sum(1 for pm in ds for n, _lo in pm.da_giac if not la_vong_moc_wgs(n))
    loai = [loai_nhan(pm.ten, pm.lop_cad) for pm in ds if pm.diem]
    n_thua = sum(1 for x in loai if x == 'thua')
    n_moc = sum(1 for x in loai if x == 'moc')
    n_gc = sum(1 for x in loai if x == 'ghi_chu')
    from .tien import so_vn
    def n(a, t):
        return f'{so_vn(a)} {t}' if a else ''
    return ', '.join(x for x in (n(n_duong, 'đường ranh / lưới thửa'), n(n_thua, 'nhãn thửa'), n(n_moc, 'mốc'),
                                 n(n_gc, 'ghi chú'), n(n_vung, 'đa giác thửa')) if x)


def _doc_kieu(el) -> dict:
    """Style KML -> {line, w, nhan} (màu '#RRGGBB')."""
    kq = {'line': '', 'w': 1.0, 'nhan': ''}
    for c in el.iter():
        t = _the(c)
        if t == 'LineStyle':
            for x in c:
                tx = _the(x)
                if tx == 'color':
                    kq['line'] = mau_kml_abgr(x.text)
                elif tx == 'width':
                    try:
                        kq['w'] = max(0.5, float(str(x.text or '1').replace(',', '.')))
                    except ValueError:
                        pass
        elif t in ('LabelStyle', 'IconStyle') and not kq['nhan']:
            for x in c:
                if _the(x) == 'color':
                    kq['nhan'] = mau_kml_abgr(x.text)
    return kq


def _khoa_style(u: str) -> str:
    s = str(u or '').strip()
    return ('#' + s.split('#', 1)[-1]) if '#' in s else s


def _thu_thap_kieu(goc) -> tuple:
    kieu, ban_do = {}, {}
    for e in goc.iter():
        t, i = _the(e), e.get('id')
        if t == 'Style' and i:
            kieu['#' + i] = _doc_kieu(e)
        elif t == 'StyleMap' and i:
            for pr in e:
                if _the(pr) != 'Pair':
                    continue
                key = next((str(x.text or '').strip() for x in pr if _the(x) == 'key'), '')
                url = next((str(x.text or '').strip() for x in pr if _the(x) == 'styleUrl'), '')
                if key == 'normal' and url:
                    ban_do['#' + i] = _khoa_style(url)
    return kieu, ban_do


def _kieu_cua(pm_el, kieu: dict, ban_do: dict) -> dict:
    for c in pm_el:
        t = _the(c)
        if t == 'Style':
            return _doc_kieu(c)
        if t == 'styleUrl':
            k = _khoa_style(c.text)
            for _i in range(4):
                k = ban_do.get(k, k)
            return kieu.get(k) or {}
    return {}


def _gan_hinh(el, pm: PlacemarkKml) -> None:
    """Mọi Polygon / LineString / Point trong Placemark (kể cả bọc MultiGeometry) — giống getElementsByTagName của điện thoại."""
    for c in el.iter():
        if _the(c) in ('Polygon', 'LineString', 'Point'):
            _hinh(c, pm)


def _placemark(e, thu_muc: str, kieu: dict | None = None, ban_do: dict | None = None) -> PlacemarkKml:
    pm = PlacemarkKml(thu_muc=thu_muc)
    for c in e:
        t = _the(c)
        if t == 'name':
            pm.ten = sua_font_kml(' '.join(str(c.text or '').split()))
        elif t == 'description':
            pm.mo_ta = sua_font_kml(str(c.text or '').strip())
        elif t == 'ExtendedData':
            for d in c.iter():
                td = _the(d)
                if td == 'Data' and d.get('name'):
                    v = next((str(x.text or '').strip() for x in d if _the(x) == 'value'), '')
                    pm.du_lieu[_khoa(d.get('name'))] = sua_font_kml(v)
                elif td == 'SimpleData' and d.get('name'):
                    pm.du_lieu[_khoa(d.get('name'))] = sua_font_kml(str(d.text or '').strip())
    pm.ban_ve, pm.lop_cad = lop_cad_tu_mo_ta(pm.mo_ta)
    st = _kieu_cua(e, kieu or {}, ban_do or {})
    pm.mau_duong, pm.rong_duong, pm.mau_nhan = st.get('line') or '', float(st.get('w') or 1), st.get('nhan') or ''
    _gan_hinh(e, pm)
    return pm


def _duyet(e, thu_muc: str, ra: list, kieu: dict | None = None, ban_do: dict | None = None) -> None:
    for c in e:
        t = _the(c)
        if t == 'Placemark':
            ra.append(_placemark(c, thu_muc, kieu, ban_do))
        elif t in ('Folder', 'Document'):
            ten = next((' '.join(str(x.text or '').split()) for x in c if _the(x) == 'name'), '')
            _duyet(c, (f'{thu_muc} / {ten}' if thu_muc else ten) if t == 'Folder' and ten else thu_muc, ra, kieu, ban_do)


def doc_byte_kml(file) -> bytes:
    """Nội dung XML của file .kml / .kmz (đã kiểm tra an toàn)."""
    from .an_toan import LoiAnToan, kiem_tra_magic_bytes, kiem_tra_xml, kiem_tra_zip
    p = Path(file)
    try:
        loai = kiem_tra_magic_bytes(p, {'xml', 'zip'})
        if loai == 'zip':
            kiem_tra_zip(p, toi_da=200 * 2 ** 20)
            with zipfile.ZipFile(p) as z:
                ten = [x for x in z.namelist() if x.lower().endswith('.kml')]
                if not ten:
                    raise LoiCad(f'File "{p.name}" không có bản đồ .kml bên trong.')
                du = z.read('doc.kml' if 'doc.kml' in ten else sorted(ten, key=lambda x: (x.count('/'), x))[0])
        else:
            du = p.read_bytes()
        kiem_tra_xml(du, p.name)
    except LoiAnToan as e:
        raise LoiCad(str(e)) from None
    except (OSError, zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as e:
        raise LoiCad(f'Không đọc được "{p.name}": {e}') from None
    return du


_RE_DIEU_KHIEN = re.compile(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]')
_RE_AMP_TRAN = re.compile(rb'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)')


def lam_sach_xml(du: bytes) -> bytes:
    """XML xuất từ phần mềm CAD: ký tự điều khiển, "&" trần (chưa thành &amp;) làm cả file không đọc được -> làm sạch (giống lamSachXml của
    ứng dụng điện thoại)."""
    return _RE_AMP_TRAN.sub(b'&amp;', _RE_DIEU_KHIEN.sub(b'', du))


def doc_kml(file) -> list:
    """File .kml / .kmz -> [PlacemarkKml] theo thứ tự trong file (XML lỗi nhẹ: làm sạch rồi đọc lại). 1.0.33: nhớ theo file (mtime / cỡ) -
    hộp Nhập bản đồ phân tích lại khi đổi số tờ / kinh tuyến trục không giải nén + đọc XML lại. Trả bản sao danh sách (không sửa phần tử)."""
    return list(doc_co_nho(file, _doc_kml))


def _doc_kml(file) -> list:
    return doc_kml_xml(doc_byte_kml(file), Path(file).name)


def doc_kml_xml(du: bytes, ten: str = 'KML') -> list:
    """Nội dung XML KML (doc_byte_kml - đã kiểm tra an toàn; hoặc bản lưu trong dự án) -> [PlacemarkKml]."""
    from .an_toan import LoiAnToan, kiem_tra_xml
    try:
        kiem_tra_xml(du, ten)
    except LoiAnToan as e:
        raise LoiCad(str(e)) from None
    try:
        goc = ET.fromstring(du)
    except ET.ParseError:
        try:
            goc = ET.fromstring(lam_sach_xml(du))
        except ET.ParseError as e:
            raise LoiCad(f'File "{ten}" không phải KML hợp lệ: {e}') from None
    ra = []
    kieu, ban_do = _thu_thap_kieu(goc)
    _duyet([goc] if _the(goc) != 'kml' else goc, '', ra, kieu, ban_do)
    return ra


# ---------------------------------------------------------------- KML -> thửa của dự án
_KHOA_TO = ('so_to', 'soto', 'to', 'to_bd', 'to_ban_do', 'sh_to', 'shbando', 'so_hieu_to', 'sotobando', 'mapsheet', 'sheet')
_KHOA_THUA = ('so_thua', 'sothua', 'thua', 'sh_thua', 'shthua', 'so_hieu_thua', 'parcel', 'parcel_no')
_KHOA_LOAI = ('loai_dat', 'loaidat', 'mdsd', 'ma_loai_dat', 'kyhieumdsd', 'muc_dich', 'mucdich', 'landuse')
_KHOA_DT = ('dien_tich', 'dientich', 'dt', 'area', 'dtpl', 'dien_tich_m2')
_KHOA_TK, _KHOA_KHOANH, _KHOA_LO = ('tieu_khu', 'tieukhu', 'tk'), ('khoanh', 'kh'), ('lo', 'lo_kk', 'lo_rung', 'lot')
_RE_RANH = re.compile(r'(^|[^a-z])ranh([^a-z]|$)')
SO_DINH_VONG_MOC, CO_VONG_MOC = 8, 3.8      # đa giác >= 8 đỉnh, cạnh khung < 3,8 m = vòng tròn quanh cọc mốc (file CAD thật: 50 đỉnh, ~1 m)
_RE_LO_RUNG = re.compile(r'(?:tiểu\s*khu|tk)\s*[:.]?\s*(\d+)\D{0,12}?(?:khoảnh|k)\s*[:.]?\s*(\d+)\D{0,12}?(?:lô|l)\s*[:.]?\s*(\w+)', re.I)
_RE_THUA_TO = re.compile(r'thửa\s*(?:số)?\s*[:.]?\s*(\d+)\D{0,12}?tờ\s*(?:bản\s*đồ)?\s*(?:số)?\s*[:.]?\s*(\d+)', re.I)
_RE_TO_THUA = re.compile(r'tờ\s*(?:bản\s*đồ)?\s*(?:số)?\s*[:.]?\s*(\d+)\D{0,12}?thửa\s*(?:số)?\s*[:.]?\s*(\d+)', re.I)


def _lay(d: dict, khoa: tuple) -> str:
    return next((str(d[k]).strip() for k in khoa if str(d.get(k) or '').strip()), '')


def so_hieu(pm: PlacemarkKml, so_to_mac_dinh: str = '') -> tuple:
    """(số tờ, số thửa, loại đất, DT ghi kèm | None) của một Placemark; lô rừng -> ("TK<tk>/K<khoảnh>", lô)."""
    from .phieu_kiem_dem import khoa_lo_rung
    from .tien import doc_so_vn
    d = pm.du_lieu
    to, thua = _lay(d, _KHOA_TO), _lay(d, _KHOA_THUA)
    tk, kh, lo = _lay(d, _KHOA_TK), _lay(d, _KHOA_KHOANH), _lay(d, _KHOA_LO)
    if lo and (tk or kh):
        to, thua = khoa_lo_rung(tk, kh), lo
    if not thua:
        for chu in (pm.ten, pm.mo_ta):
            m = _RE_LO_RUNG.search(chu or '')
            if m:
                to, thua = khoa_lo_rung(m.group(1), m.group(2)), m.group(3)
                break
            m = _RE_THUA_TO.search(chu or '')
            if m:
                thua, to = m.group(1), to or m.group(2)
                break
            m = _RE_TO_THUA.search(chu or '')
            if m:
                to, thua = to or m.group(1), m.group(2)
                break
            m = re.fullmatch(r'\s*(\d{1,4})\s*/\s*(\d{1,5})\s*', chu or '')        # "5/12" = tờ / thửa
            if m:
                to, thua = to or m.group(1), m.group(2)
                break
            m = re.fullmatch(r'\s*(?:thửa\s*(?:số)?\s*)?(\d{1,5})\s*', chu or '', re.I)
            if m:
                thua = m.group(1)
                break
    to = to or so_to_mac_dinh
    dt = None
    chu_dt = _lay(d, _KHOA_DT)
    if chu_dt:
        try:
            dt = doc_so_vn(re.sub(r'\s*(m2|m²)\s*$', '', chu_dt, flags=re.I))
        except (ValueError, ArithmeticError):
            dt = None
    chuan = (lambda s: str(int(s)) if str(s).isdigit() else str(s))
    return chuan(to) if to else '', chuan(thua) if thua else '', _lay(d, _KHOA_LOAI).upper(), dt


def la_ten_ranh(chu: str) -> bool:
    """Tên có từ "ranh" (không dấu, không phân biệt hoa thường)."""
    return bool(_RE_RANH.search(_khoa(chu).replace('_', ' ')))


def la_ranh(pm: PlacemarkKml) -> bool:
    """Đa giác ranh thu hồi / ranh dự án (tên hoặc thư mục có chữ "ranh")."""
    return la_ten_ranh(f'{pm.ten} {pm.thu_muc}')


def phan_tich_kml(file, so_to: str | None = None, kinh_tuyen: float | None = None) -> KetQuaCad:
    """File .kml / .kmz -> KetQuaCad (thửa tọa độ VN-2000 theo kinh tuyến trục) - xem trước rồi ban_do_cad.luu như bản vẽ .dxf."""
    from .toa_do import chu_kinh_tuyen, co_dinh_datum, kinh_tuyen_truc, wgs84_sang_vn2000
    kt = kinh_tuyen if kinh_tuyen is not None else kinh_tuyen_truc()
    with co_dinh_datum():
        return _phan_tich_ds(doc_kml(file), file, so_to, kt, chu_kinh_tuyen, wgs84_sang_vn2000)


def phan_tich_du_lieu(xml: bytes, ten: str, so_to: str | None = None, kinh_tuyen: float | None = None) -> KetQuaCad:
    """Như phan_tich_kml nhưng từ nội dung XML (lớp KML đã lưu trong dự án, không còn file gốc)."""
    from .toa_do import chu_kinh_tuyen, co_dinh_datum, kinh_tuyen_truc, wgs84_sang_vn2000
    kt = kinh_tuyen if kinh_tuyen is not None else kinh_tuyen_truc()
    with co_dinh_datum():
        return _phan_tich_ds(doc_kml_xml(xml, ten), ten, so_to, kt, chu_kinh_tuyen, wgs84_sang_vn2000)


def _phan_tich_ds(ds, file, so_to, kt, chu_kinh_tuyen, wgs84_sang_vn2000) -> KetQuaCad:
    kq = KetQuaCad(nguon=Path(file).name, lop_thua=f'KML (kinh tuyến trục {chu_kinh_tuyen(kt)})', so_to=str(so_to or ''))

    def doi(vong):
        return [list(wgs84_sang_vn2000(vd, kd, kt)) for kd, vd in vong]
    ranh = []
    for pm in ds:
        if pm.da_giac and la_ranh(pm):
            ranh.extend(doi(ngoai) for ngoai, _ in pm.da_giac)
    if ranh:
        kq.lop_ranh = 'đa giác "ranh" trong KML'
    tam_giac = [tam_giac_hoa(r) for r in ranh]
    hop_ranh = [_hop_bao(r) for r in ranh]
    da_co, khong_hinh, vong_moc = set(), 0, 0

    def la_vong_moc(ngoai):
        v = doi(ngoai)
        xs, ys = [x for x, _ in v], [y for _, y in v]
        return len(v) >= SO_DINH_VONG_MOC and max(max(xs) - min(xs), max(ys) - min(ys)) < CO_VONG_MOC
    for pm in ds:
        if la_ranh(pm):
            continue
        if pm.da_giac and all(la_vong_moc(n) for n, _ in pm.da_giac):
            vong_moc += 1
            continue
        if not pm.da_giac:
            khong_hinh += 1
            continue
        to, thua, loai, dt_kem = so_hieu(pm, str(so_to or ''))
        if not thua:
            kq.canh_bao.append(f'Đa giác "{(pm.ten or pm.thu_muc or "không tên")[:40]}" không đọc được số thửa / lô: bỏ qua.')
            continue
        if (to, thua) in da_co:
            kq.canh_bao.append(f'Thửa {thua} tờ {to} xuất hiện nhiều lần: lấy đa giác đầu tiên.')
            continue
        da_co.add((to, thua))
        hinh = [(doi(ngoai), [doi(x) for x in lo]) for ngoai, lo in pm.da_giac]
        dt = sum(dien_tich(n) - sum(dien_tich(x) for x in lo) for n, lo in hinh)
        chinh = max(hinh, key=lambda h: dien_tich(h[0]))[0]
        trong = None
        if ranh:
            trong = 0.0
            for n, lo in hinh:
                hb = _hop_bao(n)
                for j, r in enumerate(ranh):
                    if _cham_hop(hb, hop_ranh[j]):
                        trong += dien_tich_giao(n, r, tam_giac[j]) - sum(dien_tich_giao(x, r, tam_giac[j]) for x in lo)
        nhan = ' | '.join(x for x in (pm.ten, *(f'{k}={v}' for k, v in pm.du_lieu.items() if v)) if x)
        kq.thua.append(ThuaCad(to, thua, loai, dt_kem, D(f'{dt:.1f}'), None if trong is None else D(f'{max(trong, 0):.1f}'),
                               [[round(x, 3), round(y, 3)] for x, y in chinh], nhan[:500], 'KML'))
        kq.thua[-1].mau = pm.du_lieu.get('mau', '')     # file do phần mềm xuất: giữ màu tô tay (ban_do_cad.luu lọc qua chuan_mau)
    if vong_moc:
        kq.canh_bao.append(f'{vong_moc} vòng tròn nhỏ (< {CO_VONG_MOC} m) quanh cọc mốc: không phải thửa, bỏ qua.')
    if khong_hinh:
        kq.canh_bao.append(f'{khong_hinh} mục chỉ có điểm / đường (không phải đa giác thửa): bỏ qua.')
    if not kq.thua:
        so_duong = sum(len(pm.duong) for pm in ds)
        so_nhan = sum(1 for pm in ds if pm.diem and pm.ten)
        if so_duong:
            # bản vẽ đường của phần mềm CAD (không có đa giác thửa): tự ghép lưới thửa thành vùng rồi gán nhãn (ban_do_ghep)
            from . import ban_do_ghep
            ghep = ban_do_ghep.ghep_thua(ds, kt, str(so_to or ''), Path(file).name, ranh)
            if ghep.thua:
                return ghep
            kq.canh_bao.append(f'File là bản vẽ đường của phần mềm CAD ({so_duong} đường lưới thửa / ranh, {so_nhan} nhãn số thửa, loại đất, mốc…): không '
                               'ghép được vùng thửa nào có số thửa (lưới thửa chưa khép kín). Bản vẽ vẫn hiện trên bản đồ (lưới thửa, ranh, số thửa, '
                               'mốc); muốn tô màu theo thửa: xuất lại từ phần mềm địa chính dạng vùng (polygon) hoặc dùng bản vẽ .dxf.')
        else:
            kq.canh_bao.append('File không có đa giác thửa nào đọc được số thửa / lô.')
    kq.so_to = kq.so_to or (kq.thua[0].so_to if kq.thua else '')
    return kq


# ---------------------------------------------------------------- bản đồ dự án -> KML / KMZ
def _mau_kml(hex_rgb: str, alpha: str) -> str:
    """'#2F7D54' -> 'aabbggrr' (thứ tự màu của KML)."""
    h = hex_rgb.lstrip('#')
    return f'{alpha}{h[4:6]}{h[2:4]}{h[0:2]}'.lower()


def tao_kml(con, so_to: str | None = None, kinh_tuyen: float | None = None, ten_du_an: str = '') -> str:
    """Chữ KML của bản đồ thửa (lọc tờ) - Placemark tô màu theo đồng thuận, dữ liệu kèm để nhập lại / điện thoại khớp hộ."""
    from . import ban_do_cad
    from .tien import so_vn
    from .toa_do import kinh_tuyen_truc, vn2000_sang_wgs84
    kt = kinh_tuyen if kinh_tuyen is not None else kinh_tuyen_truc()
    ds = ban_do_cad.doc_ban_do(con, so_to)

    def e(s):                                           # 1.0.58: ký tự điều khiển (họ tên dán từ OCR / PDF) làm hỏng cả file KML
        return html.escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]', ' ', str(s)))
    kieu = ''.join(f'<Style id="{k}"><LineStyle><color>{_mau_kml(m, "ff")}</color><width>1.5</width></LineStyle>'
                   f'<PolyStyle><color>{_mau_kml(m, "66")}</color></PolyStyle></Style>'
                   for k, (_, m) in ban_do_cad.TRANG_THAI.items())
    pm = []
    for t in ds:
        vong = [vn2000_sang_wgs84(x, y, kt) for x, y in t.toa_do]
        if len(vong) < 3:
            continue
        vong.append(vong[0])
        td = ' '.join(f'{kd:.8f},{vd:.8f},0' for vd, kd in vong)
        du = dict(so_to=t.so_to, so_thua=t.so_thua, loai_dat=t.loai_dat, dien_tich=t.dt_hinh or '',
                  dien_tich_trong_ranh=t.dt_trong_ranh or '', ma_ho='' if t.ma_ho is None else str(t.ma_ho), chu_su_dung=t.ho_ten,
                  trang_thai=ban_do_cad.TRANG_THAI[t.trang_thai][0])
        kieu_rieng = ''
        if t.mau:                                       # màu tô tay thắng màu theo trạng thái (như trên bản đồ); dữ liệu kèm để nhập lại còn màu
            du['mau'] = t.mau
            kieu_rieng = (f'<Style><LineStyle><color>{_mau_kml(t.mau, "ff")}</color><width>1.5</width></LineStyle>'
                          f'<PolyStyle><color>{_mau_kml(t.mau, "66")}</color></PolyStyle></Style>')
        mo_ta = (f'Thửa {t.so_thua} tờ {t.so_to} {t.loai_dat}; DT {so_vn(t.dt_hinh)} m²'
                 + (f' (trong ranh {so_vn(t.dt_trong_ranh)} m²)' if t.dt_trong_ranh not in (None, '') else '')
                 + (f'; hộ {t.ho_ten}' if t.ho_ten else '') + f'; {ban_do_cad.TRANG_THAI[t.trang_thai][0]}')
        pm.append(f'<Placemark><name>{e(f"Thửa {t.so_thua} tờ {t.so_to}")}</name><description>{e(mo_ta)}</description>'
                  f'<styleUrl>#{t.trang_thai}</styleUrl>{kieu_rieng}<ExtendedData>'
                  + ''.join(f'<Data name="{k}"><value>{e(str(v))}</value></Data>' for k, v in du.items())
                  + f'</ExtendedData><Polygon><outerBoundaryIs><LinearRing><coordinates>{td}</coordinates></LinearRing>'
                  '</outerBoundaryIs></Polygon></Placemark>')
    ten = e(ten_du_an or 'Bản đồ thửa đất') + (f' - tờ {e(str(so_to))}' if so_to else '')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f'<name>{ten}</name>{kieu}' + ''.join(pm) + '</Document></kml>\n')


def xuat_kml(con, file, so_to: str | None = None, kinh_tuyen: float | None = None) -> dict:
    """Ghi bản đồ thửa của dự án ra .kml hoặc .kmz (theo đuôi file; ghi file tạm rồi thay). Trả {'file', 'so_thua'}."""
    from . import ban_do_cad
    p = Path(file)
    if p.suffix.lower() not in DUOI_KML:
        p = p.with_suffix('.kml')
    ds = ban_do_cad.doc_ban_do(con, so_to)
    if not ds:
        raise LoiCad('Dự án chưa có bản đồ thửa (nhập bản vẽ .dxf / .kml trước).')
    r = con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
    chu = tao_kml(con, so_to, kinh_tuyen, (r[0] if r else '') or '')
    tam = p.with_name(p.name + '.tmp')
    if p.suffix.lower() == '.kmz':
        with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('doc.kml', chu.encode('utf-8'))
    else:
        tam.write_text(chu, encoding='utf-8')
    os.replace(tam, p)
    return dict(file=p, so_thua=len(ds))
