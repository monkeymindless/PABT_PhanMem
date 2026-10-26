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
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .ban_do_cad import KetQuaCad, LoiCad, ThuaCad, _cham_hop, _hop_bao, dien_tich, dien_tich_giao, tam_giac_hoa
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


def _the(e) -> str:
    return e.tag.rsplit('}', 1)[-1] if isinstance(e.tag, str) else ''


def _khoa(s: str) -> str:
    from .lap_pa import bo_dau
    return re.sub(r'[^a-z0-9]+', '_', bo_dau(str(s or '')).lower()).strip('_')


def _toa_do(chu: str) -> list:
    """'106.9,10.9,0 107.0,11.0' -> [(106.9, 10.9), (107.0, 11.0)] (bỏ độ cao; cặp sai bỏ qua)."""
    kq = []
    for cap in str(chu or '').split():
        p = cap.split(',')
        try:
            kd, vd = float(p[0]), float(p[1])
        except (IndexError, ValueError):
            continue
        if -180 <= kd <= 180 and -90 <= vd <= 90:
            kq.append((kd, vd))
    return kq


def _vong(e) -> list:
    for c in e.iter():
        if _the(c) == 'coordinates':
            p = _toa_do(c.text)
            if len(p) >= 2 and p[0] == p[-1]:
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
        p = _vong(geo)
        if len(p) >= 2:
            pm.duong.append(p)
    elif t == 'Point':
        p = _vong(geo)
        if p:
            pm.diem.append(p[0])
    elif t == 'MultiGeometry':
        for c in geo:
            _hinh(c, pm)


def _placemark(e, thu_muc: str) -> PlacemarkKml:
    pm = PlacemarkKml(thu_muc=thu_muc)
    for c in e:
        t = _the(c)
        if t == 'name':
            pm.ten = ' '.join(str(c.text or '').split())
        elif t == 'description':
            pm.mo_ta = str(c.text or '').strip()
        elif t == 'ExtendedData':
            for d in c.iter():
                td = _the(d)
                if td == 'Data' and d.get('name'):
                    v = next((str(x.text or '').strip() for x in d if _the(x) == 'value'), '')
                    pm.du_lieu[_khoa(d.get('name'))] = v
                elif td == 'SimpleData' and d.get('name'):
                    pm.du_lieu[_khoa(d.get('name'))] = str(d.text or '').strip()
        elif t in ('Polygon', 'LineString', 'Point', 'MultiGeometry'):
            _hinh(c, pm)
    return pm


def _duyet(e, thu_muc: str, ra: list) -> None:
    for c in e:
        t = _the(c)
        if t == 'Placemark':
            ra.append(_placemark(c, thu_muc))
        elif t in ('Folder', 'Document'):
            ten = next((' '.join(str(x.text or '').split()) for x in c if _the(x) == 'name'), '')
            _duyet(c, (f'{thu_muc} / {ten}' if thu_muc else ten) if t == 'Folder' and ten else thu_muc, ra)


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
    except (OSError, zipfile.BadZipFile) as e:
        raise LoiCad(f'Không đọc được "{p.name}": {e}') from None
    return du


def doc_kml(file) -> list:
    """File .kml / .kmz -> [PlacemarkKml] theo thứ tự trong file."""
    du = doc_byte_kml(file)
    try:
        goc = ET.fromstring(du)
    except ET.ParseError as e:
        raise LoiCad(f'File "{Path(file).name}" không phải KML hợp lệ: {e}') from None
    ra = []
    _duyet([goc] if _the(goc) != 'kml' else goc, '', ra)
    return ra


# ---------------------------------------------------------------- KML -> thửa của dự án
_KHOA_TO = ('so_to', 'soto', 'to', 'to_bd', 'to_ban_do', 'sh_to', 'shbando', 'so_hieu_to', 'sotobando', 'mapsheet', 'sheet')
_KHOA_THUA = ('so_thua', 'sothua', 'thua', 'sh_thua', 'shthua', 'so_hieu_thua', 'parcel', 'parcel_no')
_KHOA_LOAI = ('loai_dat', 'loaidat', 'mdsd', 'ma_loai_dat', 'kyhieumdsd', 'muc_dich', 'mucdich', 'landuse')
_KHOA_DT = ('dien_tich', 'dientich', 'dt', 'area', 'dtpl', 'dien_tich_m2')
_KHOA_TK, _KHOA_KHOANH, _KHOA_LO = ('tieu_khu', 'tieukhu', 'tk'), ('khoanh', 'kh'), ('lo', 'lo_kk', 'lo_rung', 'lot')
_RE_RANH = re.compile(r'(^|[^a-z])ranh([^a-z]|$)')
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


def la_ranh(pm: PlacemarkKml) -> bool:
    """Đa giác ranh thu hồi / ranh dự án (tên hoặc thư mục có chữ "ranh")."""
    return bool(_RE_RANH.search(_khoa(f'{pm.ten} {pm.thu_muc}').replace('_', ' ')))


def phan_tich_kml(file, so_to: str | None = None, kinh_tuyen: float | None = None) -> KetQuaCad:
    """File .kml / .kmz -> KetQuaCad (thửa tọa độ VN-2000 theo kinh tuyến trục) - xem trước rồi ban_do_cad.luu như bản vẽ .dxf."""
    from .toa_do import chu_kinh_tuyen, kinh_tuyen_truc, wgs84_sang_vn2000
    kt = kinh_tuyen if kinh_tuyen is not None else kinh_tuyen_truc()
    ds = doc_kml(file)
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
    da_co, khong_hinh = set(), 0
    for pm in ds:
        if la_ranh(pm):
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
    if khong_hinh:
        kq.canh_bao.append(f'{khong_hinh} mục chỉ có điểm / đường (không phải đa giác thửa): bỏ qua.')
    if not kq.thua:
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
    e = html.escape
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
        mo_ta = (f'Thửa {t.so_thua} tờ {t.so_to} {t.loai_dat}; DT {so_vn(t.dt_hinh)} m²'
                 + (f' (trong ranh {so_vn(t.dt_trong_ranh)} m²)' if t.dt_trong_ranh not in (None, '') else '')
                 + (f'; hộ {t.ho_ten}' if t.ho_ten else '') + f'; {ban_do_cad.TRANG_THAI[t.trang_thai][0]}')
        pm.append(f'<Placemark><name>{e(f"Thửa {t.so_thua} tờ {t.so_to}")}</name><description>{e(mo_ta)}</description>'
                  f'<styleUrl>#{t.trang_thai}</styleUrl><ExtendedData>'
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
