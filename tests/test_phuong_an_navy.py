"""1.0.79 (người dùng 07/11/2026): 6 phương án Navy dịu mắt: đủ tương phản WCAG, áp đúng tông, đổi ngay, nhớ đệm bảng đổi màu."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pabt  # noqa: E402,F401
from PySide6.QtWidgets import QApplication  # noqa: E402
from pabt import chu_de, giao_dien as g  # noqa: E402


def _do_sang(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def tuong_phan(a, b):
    x, y = sorted((_do_sang(a), _do_sang(b)), reverse=True)
    return (x + .05) / (y + .05)


class TestPhuongAn(unittest.TestCase):
    def setUp(self):
        self.addCleanup(chu_de.dat_phuong_an, chu_de.phuong_an_hien())

    def test_du_6_phuong_an_mac_dinh_pa1(self):
        self.assertEqual(len(chu_de.PHUONG_AN_NAVY), 6)
        self.assertEqual(chu_de.MAC_DINH_PHUONG_AN, 'pa1_nordic')
        self.assertEqual(chu_de.PHUONG_AN_NAVY['pa1_nordic']['chinh'], '#345678')

    def test_tuong_phan_wcag(self):
        for ma, x in chu_de.PHUONG_AN_NAVY.items():
            self.assertGreaterEqual(tuong_phan(x['chinh'], '#FFFFFF'), 6.0, ma)
            self.assertGreaterEqual(tuong_phan(x['chinh_am'], '#FFFFFF'), 6.0, ma)
            self.assertGreaterEqual(tuong_phan(x['td_chu'], x['td_nen']), 6.0, ma)
            self.assertGreaterEqual(tuong_phan(x['td_chu'], x['td_re']), 4.5, ma)
            self.assertGreaterEqual(tuong_phan(x['dau_chu'], x['dau_nen']), 6.0, ma)

    def test_menu_trai_cung_mau_chinh(self):
        for ma in chu_de.PHUONG_AN_NAVY:
            chu_de.dat_phuong_an(ma)
            self.addCleanup(chu_de.dat_phuong_an, chu_de.MAC_DINH_PHUONG_AN)
            m = chu_de.mau_tong('sang')
            self.assertEqual(m['menu']['nhom'], m['chinh'])
            self.assertEqual(m['menu']['chon_chu'], m['chinh'])
        self.assertEqual(chu_de.MAU_TONG['sang']['menu']['nhom'], '#1E3A5F')      # bảng gốc không bị sửa

    def test_tong_rieng_khong_theo_phuong_an(self):
        for ten in ('toi', 'titan', 'ngoc'):
            self.assertIsNone(chu_de.mau_phuong_an(ten))
            self.assertEqual(chu_de.mau_tong(ten)['chinh'], chu_de.MAU_TONG[ten]['chinh'])
        chu_de.dat_phuong_an('pa3_thep_diu')
        self.assertEqual(chu_de.mau_tong('sang')['chinh'], '#3B5978')
        self.assertEqual(chu_de.mau_tong('am')['chinh'], '#3E5C76')

    def test_ma_la_ve_mac_dinh(self):
        self.assertEqual(chu_de.dat_phuong_an('khong_co'), chu_de.MAC_DINH_PHUONG_AN)

    def test_doc_tu_bien_moi_truong_cai_dat(self):
        os.environ['PABT_PHUONG_AN_NAVY'] = 'pa2_suong_nhat'
        self.addCleanup(os.environ.pop, 'PABT_PHUONG_AN_NAVY', None)
        self.assertEqual(chu_de.doc(None)['phuong_an_navy'], 'pa2_suong_nhat')


class TestBangKieu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        goc, tong = chu_de.phuong_an_hien(), g.TONG_NEN[0]
        self.addCleanup(lambda: (g.dat_phuong_an_navy(goc, ap_lai=False), g.dat_tong_nen(tong, ap_lai=False)))

    def _tieu_de(self):
        q = g.ap_tong_nen(g._qss())
        i = q.index('QHeaderView::section:horizontal {')
        return q[i:q.index('}', i)]

    def test_tieu_de_bang_pa1(self):
        g.dat_phuong_an_navy('pa1_nordic', ap_lai=False)
        t = self._tieu_de()
        for mau in ('#345678', '#FFFFFF', '#43688E', '#608AB5'):
            self.assertIn(mau, t.upper())
        self.assertNotIn('#2563EB', t.upper())

    def test_tieu_de_bang_nen_suong_pa2(self):
        g.dat_phuong_an_navy('pa2_suong_nhat', ap_lai=False)
        t = self._tieu_de().upper()
        for mau in ('#E6EEF7', '#1E3A5F', '#CBD9E8', '#8FB0D4'):
            self.assertIn(mau, t)

    def test_tong_toi_giu_tieu_de_cu(self):
        g.dat_tong_nen('toi', ap_lai=False)
        self.assertEqual(g.mau_theo_tong('#1E3A5F', 'nen'), chu_de.MAU_TONG['toi']['chinh'].upper())
        self.assertIn(chu_de.MAU_TONG['toi']['chinh'].upper(), self._tieu_de().upper())

    def test_mau_theo_tong_doi_theo_phuong_an_va_nho_dem(self):
        g.dat_phuong_an_navy('pa4_cobalt_diu', ap_lai=False)
        self.assertEqual(g.mau_theo_tong('#1E3A5F', 'chu'), '#2F5275')
        a = g._bang_doi_mau('sang')
        self.assertIs(g._bang_doi_mau('sang'), a)                       # không dựng lại
        g.dat_phuong_an_navy('pa6_khoang_sang', ap_lai=False)
        self.assertEqual(g.mau_theo_tong('#1E3A5F', 'chu'), '#3D6082')

    def test_hop_giao_dien(self):
        from pabt.man_hinh_giao_dien import HopGiaoDien
        h = HopGiaoDien(im_lang=True)
        self.addCleanup(h.deleteLater)
        self.assertEqual(h.cb_navy.count(), 6)
        self.assertEqual(h.cb_navy.currentData(), chu_de.phuong_an_hien())


if __name__ == '__main__':
    unittest.main()
