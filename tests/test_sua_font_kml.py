"""Bản đồ .kml / .kmz xuất từ MicroStation / gCadas (người dùng 27/10/2026, file thật Vành đai 4 GĐ2): chữ lỗi font (TCVN3 đọc nhầm, "�"),
XML có "&" trần / ký tự điều khiển, vòng tròn nhỏ quanh cọc mốc không phải thửa, bản vẽ chỉ có đường -> báo rõ. Dữ liệu GIẢ LẬP theo đúng
cấu trúc file thật (không chép số liệu thật). Ứng dụng điện thoại có bản JS cùng từ điển: di_dong/tests/test_phan_tach.py (CAU_LOI_FONT)."""
from __future__ import annotations

import math
import tempfile
import unittest
import zipfile
from pathlib import Path

from pabt.ban_do_kml import (doc_kml, lam_sach_xml, loai_nhan, lop_cad_tu_mo_ta, mau_kml_abgr, phan_tich_kml, tom_tat_cad,
                             _toa_do)
from pabt.sua_font_kml import sua_font_kml, tu_tcvn3

L = '�'
# (chữ lỗi, chữ đúng) - cùng danh sách với di_dong/tests/test_phan_tach.py
CAU_LOI_FONT = [
    (f'H{L}nh lang b{L}o v{L} ngu{L}n n{L}{L}c theo Quy{L}t {L}{L}nh', 'Hành lang bảo vệ nguồn nước theo Quyết định'),
    (f'S{L} 60/2022/Q{L}-UBNDng{L}y 27/12/2022 c{L}a', 'Số 60/2022/QĐ-UBND ngày 27/12/2022 của'),
    ('UBND t∅nh ' + L * 2 + 'ng Nai.', 'UBND tỉnh Đồng Nai.'),
    (f'T{L} s{L} 59', 'Tờ số 59'),
    (f'{L}{L}{L}ng ranh c{L}ch m{L}p {L}{L}{L}ng giao th{L}ng v{L}o 100m', 'Đường ranh cách mép đường giao thông vào 100m'),
    (f'B{L} m{L}{L}ng', 'Bờ mương'),
    (f'{L}{L}{L}ng b{L} t{L}ng', 'Đường bê tông'),
    (f'C{L}ch m{L}p d{L}y ngo{L}i c{L}ng 6m theo Ngh{L} {L}{L}nh 14/2014/N{L}-CP', 'Cách mép dây ngoài cùng 6m theo Nghị định 14/2014/NĐ-CP'),
    (f'Su{L}i R{L}ch {L}{L}ng', 'Suối Rạch Đông'),
    (f'{L}T.768.Nh{L}a', 'ĐT.768.Nhựa'),
    (f'X{L} B{L}nh Minh', 'Xã Bình Minh'),
    ('ngµy 27/12/2022 cña UBND tØnh §ång Nai.', 'ngày 27/12/2022 của UBND tỉnh Đồng Nai.'),
    (f'S{L}ng L{L}nh', f'Sông L{L}nh'),                     # không chắc chắn: giữ nguyên, không đoán
]


class TestSuaFont(unittest.TestCase):
    def test_cau_that(self):
        for loi, dung in CAU_LOI_FONT:
            self.assertEqual(sua_font_kml(loi), dung, loi)

    def test_khong_lam_hong_chu_dung(self):
        for s in ('Hành lang bảo vệ', 'Thửa 549 tờ 59', 'CLN', '(3600.7)', 'DN.T737', 'Café á Đông', ''):
            self.assertEqual(sua_font_kml(s), s)
        self.assertEqual(tu_tcvn3('Café'), 'Café')             # có chữ Latin-1 nhưng không có dấu hiệu TCVN3


def _kml(ds_pm: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            '<Style id="d"><LineStyle><color>ffffffff</color><width>1</width></LineStyle></Style>'
            '<StyleMap id="m"><Pair><key>normal</key><styleUrl>#d</styleUrl></Pair></StyleMap>'
            f'<Folder><name>Entity Features</name>{ds_pm}</Folder></Document></kml>')


def _vong_tron(lat, lon, r_m, n=50):
    kx = 111320 * math.cos(math.radians(lat))
    return ' '.join(f'{lon + r_m * math.cos(2 * math.pi * i / n) / kx:.9f},{lat + r_m * math.sin(2 * math.pi * i / n) / 110540:.9f},0' for i in range(n + 1))


class TestKmlCad(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.td.cleanup()

    def _file(self, ten, kml, kmz=True):
        f = Path(self.td.name) / ten
        if kmz:
            with zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED) as z:
                z.writestr('doc.kml', kml)
        else:
            f.write_text(kml, encoding='utf-8')
        return f

    def test_xml_loi_nhe_va_font(self):
        pm = (f'<Placemark><name>M{L}{L}ng &amp; b{L} m{L}{L}ng</name><description>Level 39</description>'
              '<Point><coordinates>106.95,11.02,0</coordinates></Point></Placemark>'
              '<Placemark><name>Mương & bờ\x01</name><Point><coordinates>106.95,11.02,0</coordinates></Point></Placemark>')
        f = self._file('loi.kml', _kml(pm), kmz=False)
        ds = doc_kml(f)                                           # "&" trần + ký tự điều khiển: làm sạch rồi đọc
        self.assertEqual([p.ten for p in ds], ['Mương & bờ mương', 'Mương & bờ'])
        self.assertEqual(lam_sach_xml(b'a & b &amp; c\x02'), b'a &amp; b &amp; c')

    def test_vong_moc_va_ban_ve_duong(self):
        pm = (f'<Placemark><name>Polygon_001</name><description>Level 11</description><Polygon><outerBoundaryIs><LinearRing>'
              f'<coordinates>{_vong_tron(11.02, 106.95, 0.6)}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>'
              '<Placemark><name>Polyline_005</name><description>tanan2|Level 10</description><styleUrl>#m</styleUrl>'
              '<LineString><coordinates>106.95,11.02,0 106.951,11.021,0</coordinates></LineString></Placemark>'
              '<Placemark><name>549</name><description>Level 3</description><Point><coordinates>106.9501,11.0201,0</coordinates></Point></Placemark>')
        kq = phan_tich_kml(self._file('cad.kmz', _kml(pm)))
        self.assertEqual(kq.thua, [])
        chu = ' '.join(kq.canh_bao)
        self.assertIn('1 vòng tròn nhỏ', chu)
        self.assertIn('bản vẽ đường của phần mềm CAD (1 đường', chu)

    def test_loai_nhan_va_lop_cad(self):
        self.assertEqual(loai_nhan('549'), 'thua')
        self.assertEqual(loai_nhan('CLN'), 'ld')
        self.assertEqual(loai_nhan('3600.7'), 'dt')
        self.assertEqual(loai_nhan('(120.5)'), 'dt_th')
        self.assertEqual(loai_nhan('DN.T737'), 'moc')
        self.assertEqual(loai_nhan('A1.P12', 'Level 45'), 'moc')
        self.assertEqual(loai_nhan('Tờ số 59'), 'to')
        self.assertEqual(loai_nhan('Hành lang bảo vệ'), 'ghi_chu')
        self.assertEqual(loai_nhan('*'), 'ky_hieu')
        self.assertEqual(lop_cad_tu_mo_ta('tanan2|Level 10'), ('tanan2', 'Level 10'))
        self.assertEqual(lop_cad_tu_mo_ta('Level 44'), ('', 'Level 44'))
        self.assertEqual(mau_kml_abgr('ffffffff'), '#FFFFFF')
        self.assertEqual(mau_kml_abgr('ff0000ff'), '#FF0000')
        self.assertEqual(mau_kml_abgr('00ffffff'), '')          # gần trong suốt

    def test_style_va_toa_do_khong_khoang_trang(self):
        pm = ('<Placemark><name>Polyline_005</name><description>tanan2|Level 10</description><styleUrl>#m</styleUrl>'
              '<LineString><coordinates>106.95,11.02,0,106.951,11.021,0,106.952,11.022,0</coordinates></LineString></Placemark>'
              '<Placemark><name>549</name><description>Level 3</description>'
              '<Point><coordinates>106.9501,11.0201,0</coordinates></Point></Placemark>')
        ds = doc_kml(self._file('cad_style.kml', _kml(pm), kmz=False))
        duong = next(p for p in ds if p.duong)
        self.assertEqual(duong.lop_cad, 'Level 10')
        self.assertEqual(duong.ban_ve, 'tanan2')
        self.assertEqual(duong.mau_duong, '#FFFFFF')             # StyleMap -> Style d: ffffffff
        self.assertGreaterEqual(len(duong.duong[0]), 2)          # tọa độ dính nhau bằng dấu phẩy vẫn thành đường
        nhan = next(p for p in ds if p.diem)
        self.assertEqual(loai_nhan(nhan.ten, nhan.lop_cad), 'thua')
        self.assertIn('đường ranh', tom_tat_cad(ds))
        self.assertGreaterEqual(len(_toa_do('106.95,11.02,0,106.951,11.021,0')), 2)


if __name__ == '__main__':
    unittest.main()
