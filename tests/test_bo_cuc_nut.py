"""Bố cục nút ở cửa sổ hẹp (06/11/2026, người dùng kèm ảnh): nút không che thẻ, số tổng không bị cắt. 1093 px = màn 1366 phóng 125%. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import unittest

from tests.test_giao_dien_navy import CoNavy

CO_PHONG = os.path.isdir(r'C:\Windows\Fonts')


@unittest.skipUnless(CO_PHONG, 'cần phông Windows để đo bề rộng chữ thật')
class TestNiemYet(CoNavy):
    def _khung(self, rong):
        ud, w = self._cua_so()
        w.resize(rong, 700)
        w.mo_du_thao()
        self.app.processEvents()
        k = w.khung_tab.widget['du_thao']
        self.app.processEvents()
        return k

    def test_thanh_the_du_cho_moi_co_cua_so(self):
        k = self._khung(1920)
        cua = k.window()
        for rong in (1093, 1536, 1920):
            cua.resize(rong, 700)
            self.app.processEvents()
            b = k.tabs.tabBar()
            for i in range(4):
                k.tabs.setCurrentIndex(i)
                self.app.processEvents()
                can = sum(b.tabRect(j).width() for j in range(4))
                self.assertLessEqual(can, b.width(), f'cửa sổ {rong}, thẻ {i}')
                self.assertIsNone(k.tabs.cornerWidget())

    def test_hang_nut_theo_the_dang_mo(self):
        k = self._khung(1093)
        for i, ten in ((2, 'Xuất biên bản đối thoại'), (3, 'Xuất báo cáo tổng hợp ý kiến')):
            k.tabs.setCurrentIndex(i)
            self.app.processEvents()
            self.assertTrue(k._nut[ten].isVisibleTo(k))
            self.assertIs(k._goc_nut.parentWidget(), k.tabs.currentWidget())
            self.assertLessEqual(k._goc_nut.width(), k.tabs.currentWidget().width())
            self.assertTrue(k.b_van_ban.isVisibleTo(k))
            self.assertFalse(k.b_quet_ny.isVisibleTo(k))
            for x in (k._nut[ten], k.b_van_ban, k.b_doc_kq):
                self.assertGreaterEqual(x.width(), x.fontMetrics().horizontalAdvance(x.text()), x.text())
        k.tabs.setCurrentIndex(0)
        self.app.processEvents()
        self.assertTrue(k.b_quet_ny.isVisibleTo(k))
        self.assertFalse(k._nut['Xuất biên bản đối thoại'].isVisibleTo(k))


@unittest.skipUnless(CO_PHONG, 'cần phông Windows để đo bề rộng chữ thật')
class TestTheChaoRong(CoNavy):
    def test_the_dung_co_thiet_ke_va_ten_khong_cat(self):
        from pabt import app as ud
        from pabt.giao_dien import KICH_THE_CHAO, CO_HUY_HIEU_THE_CHAO
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.deleteLater)
        w.show()
        for rong, du in ((1920, True), (1093, False)):
            w.resize(rong, 800)
            self.app.processEvents()
            for the in w.the_chao.values():
                if du:
                    self.assertEqual(the.width(), KICH_THE_CHAO[0])
                n = the._nut
                self.assertGreaterEqual(n.width(), n.fontMetrics().horizontalAdvance(n.text()), n.text())
                if the.lb_phim is not None and the.lb_phim.isVisibleTo(the):
                    self.assertGreaterEqual(the.lb_phim.x(), (the.width() + CO_HUY_HIEU_THE_CHAO) // 2)


@unittest.skipUnless(CO_PHONG, 'cần phông Windows để đo bề rộng chữ thật')
class TestLapPhuongAn(CoNavy):
    def _cua_so_pa(self, rong):
        ud, w = self._cua_so()
        w.resize(rong, 614)
        w.mo_lap_pa(w.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0])
        self.app.processEvents()
        k = next(x for x in w.khung_tab.widget.values() if type(x).__name__ == 'CuaSoLapPA')
        self.app.processEvents()
        return w, k

    def test_so_tong_khong_bi_cat(self):
        from PySide6.QtGui import QTextDocument
        w, k = self._cua_so_pa(1093)
        doc = QTextDocument()
        doc.setDefaultFont(k.lb_chan.font())
        doc.setHtml(k.lb_chan.__class__.__mro__[1].text(k.lb_chan))
        self.assertLessEqual(doc.idealWidth(), k.lb_chan.width() + 1)
        self.assertIn('TỔNG', doc.toPlainText())
        self.assertRegex(doc.toPlainText(), r'TỔNG[^:]*: [\d.]+ đ')
        self.assertIn('TỔNG CỘNG PHƯƠNG ÁN', k.lb_chan.text())     # đủ chữ vẫn đọc được: text() + chú thích

    def test_the_muc_va_huy_hieu_khong_cat(self):
        w, k = self._cua_so_pa(1093)
        t = k.thanh_the
        fm = t.nut[0].fontMetrics()
        for b in t.nut:
            self.assertGreaterEqual(b.width(), fm.horizontalAdvance(b.text().replace('&&', '&')), b.text())
        lb = t._huy_hieu
        self.assertGreaterEqual(lb.width(), lb.fontMetrics().horizontalAdvance(lb.text()), lb.text())
        self.assertRegex(lb.text(), r'[\d.]+ đ$')

    def test_chu_the_day_du_khi_rong(self):
        from pabt.man_hinh_the_muc import ThanhTheMuc as T
        self.assertEqual(T._chu_muc('1. Đất (1 • 150,0 triệu)', 0), '1. Đất (1 • 150,0 triệu)')
        self.assertEqual(T._chu_muc('1. Đất (1 • 150,0 triệu)', 1), '1. Đất (1)')
        self.assertEqual(T._chu_muc('1. Đất (1 • 150,0 triệu)', 2), '1. Đất')
        self.assertEqual(T._chu_muc('0. Hồ sơ && Thửa (1 thửa)', 2), '0. Hồ sơ && Thửa')
        self.assertEqual(T._chu_muc('Không có ngoặc', 2), 'Không có ngoặc')

    def test_nut_hang_tren_du_chu_o_cua_so_hep(self):
        w, k = self._cua_so_pa(1093)
        for b in (k.thanh_pb.b_hd, k.thanh_pb.b_dc, k.b_luu, k.b_in, k.b_dong):
            if b.isVisibleTo(k):
                self.assertGreaterEqual(b.width(), b.fontMetrics().horizontalAdvance(b.text()), b.text())
        self.assertFalse(k.nhan_lan.isVisibleTo(k))
        w.resize(1700, 800)
        self.app.processEvents()
        self.assertTrue(k.nhan_lan.isVisibleTo(k))


if __name__ == '__main__':
    unittest.main()
