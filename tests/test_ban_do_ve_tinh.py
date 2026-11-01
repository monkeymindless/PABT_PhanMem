"""Bản đồ trên máy tính như LARC Mobile (người dùng 31/10/2026): nền nhiều lớp tải theo vùng đang xem, mở KML / KMZ để xem (không ghi vào
dự án), tìm thửa theo số tờ / thửa và xem thửa thu hồi của một hộ (máy không có GPS), lưu lớp KML + ảnh nền vào file dự án. Bản đồ, hộ,
ảnh: GIẢ LẬP; KHÔNG gọi mạng."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import ban_do_cad, ban_do_kml, ban_do_luu, csdl, nen_ban_do
from tests.test_ban_do_kml import _KhongFileBentley, _kml
from tests.test_ban_do_pa4 import _png
from tests.test_toc_do import _du_an


class TestNenNhieuLop(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_nen2_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        p = mock.patch.object(nen_ban_do, 'thu_muc_dem', lambda: self.td / 'esri')
        p.start()
        self.addCleanup(p.stop)

    def test_lop_va_muc_phong(self):
        self.assertEqual(set(nen_ban_do.NEN[nen_ban_do.NEN_MAC_DINH][1]) - set(nen_ban_do.LOP), set())
        for _ten, lop, *_x in nen_ban_do.NEN.values():
            self.assertTrue(set(lop) <= set(nen_ban_do.LOP))
        self.assertEqual(nen_ban_do.z_cho_khung(1.0, 11.0, 17), 17)                  # 1 m / điểm: sâu nhất (giới hạn 17)
        z = nen_ban_do.z_cho_khung(150.0, 11.0, 17)
        self.assertTrue(8 <= z <= 11)
        z2, ds = nen_ban_do.o_cua_khung((10.0, 12.0, 106.0, 108.0), 17)               # khung lớn: lùi mức cho đủ ít ô
        self.assertLess(z2, 17)
        self.assertLessEqual(len(ds), nen_ban_do.O_TOI_DA_KHUNG)

    def test_tai_o_lop_khac(self):
        anh, url = _png(), []
        self.assertEqual(nen_ban_do.tai_o(15, 3, 4, lay=lambda u: url.append(u) or anh, lop='osm'), anh)
        self.assertEqual(url, ['https://tile.openstreetmap.org/15/3/4.png'])
        self.assertTrue((self.td / 'osm' / '15' / '3' / '4.png').is_file())          # đệm riêng từng lớp
        self.assertIsNone(nen_ban_do.tai_o(15, 3, 4, lay=lambda u: anh, lop='la'))   # lớp lạ


class _Qt(_KhongFileBentley):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('không có Qt')
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.td = Path(tempfile.mkdtemp(prefix='pabt_vt_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.kml = self.td / 'ban_do.kml'
        self.kml.write_text(_kml(), encoding='utf-8')
        p = mock.patch.object(nen_ban_do, 'thu_muc_dem', lambda: self.td / 'nen')
        p.start()
        self.addCleanup(p.stop)

    def _hop(self, con, **k):
        from pabt.man_hinh_ban_do import HopBanDo
        h = HopBanDo(con, **k)
        h.im_lang = True

        def dong():
            h.done(0)
            h.deleteLater()
            self.app.processEvents()
        self.addCleanup(dong)
        h.resize(900, 600)
        h.view.resize(800, 500)
        return h


class TestXemKml(_Qt):
    def test_khong_du_an_mo_kml_va_tim(self):
        h = self._hop(None)                                         # chưa mở dự án: vẫn xem KML trên nền
        self.assertFalse(h.b_luu.isVisibleTo(h))
        self.assertGreater(h.mo_kml([self.kml]), 0)
        self.assertTrue(h.b_bo_kml.isEnabled())
        self.assertFalse(h.view.khung_thua().isEmpty())
        khoa = {k for k, _it, _m in h.view.kml_thua}
        self.assertIn(('11', '103'), khoa)                           # "Thửa 103 tờ 11"
        self.assertIn(('TK126/K6', '34'), khoa)                      # lô rừng
        self.assertEqual(h.tim_thua('11/103'), 1)
        self.assertEqual(h.tim_thua('thửa 103 tờ 11'), 1)
        self.assertEqual(h.tim_thua('103'), 1)
        self.assertEqual(h.tim_thua('11/999'), 0)
        self.assertIn('Không thấy', h.lb.text())
        h.bo_kml()
        self.assertEqual(h.view.kml, [])

    def test_doc_chu_tim(self):
        from pabt.man_hinh_ban_do import HopBanDo
        self.assertEqual(HopBanDo.doc_chu_tim('5/12'), ('5', '12'))
        self.assertEqual(HopBanDo.doc_chu_tim('tờ 5 thửa 12'), ('5', '12'))
        self.assertEqual(HopBanDo.doc_chu_tim('Thửa số 12 tờ bản đồ 5'), ('5', '12'))
        self.assertEqual(HopBanDo.doc_chu_tim(' 12 '), ('', '12'))
        self.assertEqual(HopBanDo.doc_chu_tim('abc'), ('', ''))


class TestDuAn(_Qt):
    def setUp(self):
        super().setUp()
        self.f = _du_an(self.td, 4)
        self.con = csdl.mo(self.f)
        self.addCleanup(self.con.close)
        with self.con:                                              # hộ 3 có thửa trùng số với vùng KML "Thửa 103 tờ 11"
            self.con.execute("UPDATE thua SET so_to = '11', so_thua = '103' WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua "
                             "WHERE ma_ho = 3)")

    def test_xem_ho_va_luu_vao_du_an(self):
        h = self._hop(self.con)
        self.assertTrue(h.b_luu.isVisibleTo(h))
        self.assertEqual(h.xem_ho(3), 0)                            # chưa có bản đồ
        self.assertIn('chưa thấy thửa', h.lb.text())
        h.mo_kml([self.kml])
        self.assertEqual(h.xem_ho(3), 1)                            # vùng KML khớp số tờ / thửa của hộ
        self.assertIn('viền xanh', h.lb.text())
        it = next(it for k, it, m in h.view.kml_thua if k == ('11', '103'))
        self.assertIn('Khớp hồ sơ dự án', it.toolTip())
        anh = _png()
        kq = h.luu_vao_du_an(tai=lambda z, x, y, lp: anh)
        self.assertEqual(kq['lop'], 1)
        self.assertGreater(kq['o'], 0)
        tt = ban_do_luu.tom_tat(self.con)
        self.assertEqual((tt['lop'], tt['o']), (1, kq['o']))
        # mở lại: lớp KML có sẵn, ảnh nền lấy từ file dự án - không tải mạng
        goi = []
        with mock.patch.object(nen_ban_do, 'tai_o', lambda z, x, y, **k: goi.append(1)):
            h2 = self._hop(self.con)
            self.assertEqual([t for t, _ in h2.lop_kml], ['ban_do.kml'])
            self.assertEqual(h2.xem_ho(3), 1)
            h2.cb_nen.setCurrentIndex(h2.cb_nen.findData('ve_tinh'))
            h2.view.vua()
            h2.nap_nen()
            h2.nen.cho_xong(5)
        self.assertTrue(h2.view.o_nen)                              # ô đặt từ bản lưu
        self.assertEqual(goi, [])
        self.assertTrue(h2.b_bo_luu.isVisibleTo(h2))
        h2.bo_kml()                                                 # bỏ lớp: xóa cả bản đã lưu
        self.assertEqual(ban_do_luu.ds_lop(self.con), [])
        cu = Path(self.f).stat().st_size
        self.assertEqual(h2.bo_ban_do_da_luu()['o'], kq['o'])      # bỏ ảnh nền đã lưu: file thu gọn
        self.assertEqual(ban_do_luu.tom_tat(self.con)['o'], 0)
        self.assertLessEqual(Path(self.f).stat().st_size, cu)
        self.assertFalse(h2.b_bo_luu.isVisibleTo(h2))

    def test_du_an_dong_khi_cua_so_con_mo(self):
        """Cửa sổ bản đồ không chặn: đóng dự án rồi bấm Lưu / Bỏ bản đồ đã lưu không lỗi (kiểm tra giao diện 31/10/2026)."""
        import sqlite3
        c = csdl.mo(self.f)
        h = self._hop(c)
        c.close()
        self.assertIsNone(h.luu_vao_du_an())
        self.assertIsNone(h.bo_ban_do_da_luu())
        self.assertEqual(h.xem_ho(3), 0)
        h.nap()
        self.assertIsNone(h.con)
        with self.assertRaises(sqlite3.ProgrammingError):
            c.execute('SELECT 1')

    def test_chi_doc_khong_luu(self):
        h = self._hop(self.con, chi_doc=True)
        self.assertFalse(h.b_luu.isEnabled())
        self.assertIsNone(h.luu_vao_du_an())

    def test_thua_du_an_tim_theo_to(self):
        ban_do_cad.luu(self.con, ban_do_kml.phan_tich_kml(self.kml, kinh_tuyen=107.75))
        h = self._hop(self.con)
        self.assertEqual(h.xem_ho(3), 1)                            # thửa đã nhập bản đồ của hộ
        self.assertEqual(h.tim_thua('11/103'), 1)


if __name__ == '__main__':
    unittest.main()
