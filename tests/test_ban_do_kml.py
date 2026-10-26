"""1.0.32 Đợt 2 (người dùng 26/10/2026): quy đổi WGS84 <-> VN-2000 (toa_do), đọc / xuất bản đồ .kml / .kmz (ban_do_kml), file datum
Bentley VN2000.dty làm nguồn tham số. Số tham chiếu tọa độ tính bằng PROJ (pyproj, phép EPSG "VN-2000 to WGS 84 (2)" + tmerc
107°45' k 0,9999) - pyproj không có trong môi trường, chỉ ghi kết quả. Bản đồ, thửa, lô rừng, file datum: GIẢ LẬP."""
from __future__ import annotations
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from pabt import ban_do_cad, ban_do_kml, csdl, toa_do
from tests.test_toc_do import _du_an


def _dty(ts, phuong_phap=9, ten=b'VN2000') -> bytes:
    """Thư viện datum CS-MAP giả lập: dấu + một bản ghi cs_Dtdef_ (tên, elipxoit, 7 số thực, mã phương pháp)."""
    r = bytearray(400)
    r[0:len(ten)] = ten
    r[24:29] = b'WGS84'
    r[152:208] = struct.pack('<7d', *ts)
    r[338:340] = struct.pack('<h', phuong_phap)
    return b'\x82\x19\x13\x02' + b'\x00' * 60 + bytes(r)


class _KhongFileBentley(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(toa_do, 'FILE_DATUM_BENTLEY', ())     # máy có Bentley hay không: dùng tham số gắn sẵn
        p.start()
        self.addCleanup(p.stop)


class TestToaDo(_KhongFileBentley):
    def test_khop_proj(self):
        for (vd, kd), (e, n) in (((11.1234567, 106.9876543), (416531.023, 1230219.402)),
                                 ((10.95, 107.1), (428761.842, 1211004.076))):
            x, y = toa_do.wgs84_sang_vn2000(vd, kd, 107.75)
            self.assertAlmostEqual(x, e, delta=0.002)
            self.assertAlmostEqual(y, n, delta=0.002)
            vd2, kd2 = toa_do.vn2000_sang_wgs84(x, y, 107.75)
            self.assertLess(toa_do.khoang_cach_m(vd, kd, vd2, kd2), 0.001)          # đi - về lệch < 1 mm

    def test_kinh_tuyen(self):
        for x in (107.75, '107.75', '107,75', "107°45'", '107 45', '107°45′'):
            self.assertEqual(toa_do.doc_kinh_tuyen(x), 107.75, x)
        with self.assertRaises(ValueError):
            toa_do.doc_kinh_tuyen(45)
        self.assertEqual(toa_do.chu_kinh_tuyen(107.75), "107°45'")
        self.assertEqual(toa_do.chu_kinh_tuyen(105.0), '105°')

    def test_file_datum(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'VN2000.dty'
            ts = list(toa_do.TOWGS84[:6]) + [1 + toa_do.TOWGS84[6] * 1e-6]       # tỷ lệ ghi dạng hệ số như file Bentley
            f.write_bytes(_dty(ts))
            kq = toa_do.doc_file_datum(f)
            self.assertEqual(kq[1], 'coordinate_frame')
            self.assertAlmostEqual(kq[0][6], 0.252906278, places=6)
            f.write_bytes(_dty(ts, phuong_phap=3))
            self.assertEqual(toa_do.doc_file_datum(f)[1], 'position_vector')
            f.write_bytes(b'khong phai datum')
            self.assertIsNone(toa_do.doc_file_datum(f))
            # hồ sơ chỉ file datum: tham số lấy từ file (đổi dX để thấy khác)
            f.write_bytes(_dty([-200.0] + ts[1:]))
            with mock.patch('pabt.dia_phuong.lay', lambda k, *a: str(f) if k == 'ban_do.file_datum' else None):
                ts2, qu, nguon = toa_do.tham_so_datum()
                self.assertEqual((ts2[0], qu, nguon), (-200.0, 'coordinate_frame', str(f)))
        self.assertEqual(toa_do.tham_so_datum()[2], 'QĐ 05/2007/QĐ-BTNMT (gắn sẵn)')


def _vuong(e0, n0, canh=100.0, kt=107.75):
    """Hình vuông VN-2000 -> chuỗi tọa độ KML (kinh độ, vĩ độ)."""
    dinh = [(e0, n0), (e0 + canh, n0), (e0 + canh, n0 + canh), (e0, n0 + canh), (e0, n0)]
    return ' '.join(f'{kd:.9f},{vd:.9f},0' for vd, kd in (toa_do.vn2000_sang_wgs84(x, y, kt) for x, y in dinh))


def _kml(thu_muc_ranh='Ranh thu hồi') -> str:
    e0, n0 = 420000.0, 1220000.0
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Thử</name>
<Folder><name>Thửa đất</name>
 <Placemark><name>Thửa 103 tờ 11</name><Polygon><outerBoundaryIs><LinearRing><coordinates>{_vuong(e0, n0)}</coordinates>
  </LinearRing></outerBoundaryIs></Polygon></Placemark>
 <Placemark><name>Lô rừng</name><ExtendedData><Data name="Tiểu khu"><value>126</value></Data><Data name="Khoảnh"><value>06</value></Data>
  <Data name="Lô"><value>34</value></Data><Data name="Loại đất"><value>rsx</value></Data><Data name="Diện tích"><value>10.000,5</value></Data>
  </ExtendedData><Polygon><outerBoundaryIs><LinearRing><coordinates>{_vuong(e0 + 200, n0)}</coordinates></LinearRing></outerBoundaryIs>
  </Polygon></Placemark>
 <Placemark><name>Cột mốc</name><Point><coordinates>107,11,0</coordinates></Point></Placemark>
</Folder>
<Folder><name>{thu_muc_ranh}</name><Placemark><name>RG</name><Polygon><outerBoundaryIs><LinearRing>
 <coordinates>{_vuong(e0 - 50, n0, 300, 107.75)}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Folder>
</Document></kml>'''


class TestKml(_KhongFileBentley):
    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.f = Path(self.td.name) / 'ban_do.kml'
        self.f.write_text(_kml(), encoding='utf-8')

    def test_doc_va_phan_tich(self):
        ds = ban_do_kml.doc_kml(self.f)
        self.assertEqual([p.ten for p in ds], ['Thửa 103 tờ 11', 'Lô rừng', 'Cột mốc', 'RG'])
        self.assertEqual(ds[1].du_lieu['tieu_khu'], '126')
        self.assertTrue(ban_do_kml.la_ranh(ds[3]))
        kq = ban_do_kml.phan_tich_kml(self.f, kinh_tuyen=107.75)
        t = {(x.so_to, x.so_thua): x for x in kq.thua}
        self.assertEqual(set(t), {('11', '103'), ('TK126/K06', '34')})
        a = t[('11', '103')]
        self.assertAlmostEqual(float(a.dt_hinh), 10000.0, delta=0.2)            # DT trên mặt chiếu VN-2000 như bản vẽ
        self.assertAlmostEqual(a.toa_do[0][0], 420000.0, delta=0.005)
        self.assertAlmostEqual(float(a.dt_trong_ranh), 10000.0, delta=0.5)      # nằm trọn trong ranh (e0 - 50 .. e0 + 250)
        b = t[('TK126/K06', '34')]
        self.assertEqual((b.loai_dat, str(b.dt_ban_ve)), ('RSX', '10000.5'))
        self.assertAlmostEqual(float(b.dt_trong_ranh), 10000.0 - 5000.0, delta=0.5)   # lô e0 + 200 .. e0 + 300: nửa trong ranh
        self.assertTrue(any('điểm / đường' in c for c in kq.canh_bao))

    def test_kmz_va_an_toan(self):
        kmz = Path(self.td.name) / 'ban_do.kmz'
        with zipfile.ZipFile(kmz, 'w') as z:
            z.writestr('doc.kml', _kml())
        self.assertEqual(len(ban_do_kml.phan_tich_kml(kmz, kinh_tuyen=107.75).thua), 2)
        xau = Path(self.td.name) / 'xau.kmz'
        with zipfile.ZipFile(xau, 'w') as z:
            z.writestr('../ngoai.kml', _kml())
        with self.assertRaises(ban_do_cad.LoiCad):
            ban_do_kml.doc_kml(xau)
        doc = Path(self.td.name) / 'doc.kml'
        doc.write_text('<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY x "y">]><kml/>', encoding='utf-8')
        with self.assertRaises(ban_do_cad.LoiCad):
            ban_do_kml.doc_kml(doc)
        gia = Path(self.td.name) / 'gia.kml'
        gia.write_bytes(b'MZ\x90\x00' + b'\x00' * 50)
        with self.assertRaises(ban_do_cad.LoiCad):
            ban_do_kml.doc_kml(gia)

    def test_luu_khop_ho_va_xuat_lai(self):
        p = _du_an(Path(self.td.name), 4)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        with con:                                       # lô rừng ghi "TK126-K6" trong hồ sơ: vẫn khớp "TK126/K06" của bản đồ
            con.execute("UPDATE thua SET so_to = 'TK126-K6', so_thua = '34' WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua "
                        "WHERE ma_ho = 3)")
        kq = ban_do_kml.phan_tich_kml(self.f, kinh_tuyen=107.75)
        self.assertEqual(ban_do_cad.luu(con, kq)['khop'], 2)
        bd = {(t.so_to, t.so_thua): t.ma_ho for t in ban_do_cad.doc_ban_do(con)}
        self.assertEqual(bd, {('11', '103'): 2, ('TK126/K06', '34'): 3})
        ra = Path(self.td.name) / 'xuat.kmz'
        self.assertEqual(ban_do_kml.xuat_kml(con, ra, kinh_tuyen=107.75)['so_thua'], 2)
        lai = ban_do_kml.phan_tich_kml(ra, kinh_tuyen=107.75)               # xuất rồi nhập lại: cùng thửa, cùng diện tích
        self.assertEqual({(t.so_to, t.so_thua): round(float(t.dt_hinh)) for t in lai.thua},
                         {('11', '103'): 10000, ('TK126/K06', '34'): 10000})
        pm = {x.ten: x.du_lieu for x in ban_do_kml.doc_kml(ra)}
        self.assertEqual(pm['Thửa 103 tờ 11']['ma_ho'], '2')

    def test_man_hinh(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest('không có Qt')
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_ban_do import HopBanDo, HopNhapCad
        p = _du_an(Path(self.td.name), 4)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        h = HopNhapCad(con)
        h.im_lang = True
        self.assertTrue(h.chon_file(str(self.f)))
        self.assertTrue(h.cb_kt.isEnabled() and not h.cb_thua.isEnabled())
        self.assertEqual(h.bang.rowCount(), 2)
        h.cb_kt.setEditText("107°45'")
        self.assertEqual(h.kinh_tuyen(), 107.75)
        self.assertEqual(h.luu()['luu'], 2)
        b = HopBanDo(con)
        b.im_lang = True
        self.assertTrue(b.b_xuat.isEnabled())
        self.assertTrue(Path(b.xuat_kml(str(Path(self.td.name) / 'bd.kml'))).is_file())
        b._hien_toa_do(420050.0, 1220050.0)
        self.assertIn('GPS 11.', b.lb_toa_do.text())
        h.close()
        b.close()


if __name__ == '__main__':
    unittest.main()
