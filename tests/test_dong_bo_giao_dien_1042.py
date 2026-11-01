"""1.0.42: đồng bộ giao diện (TOKEN, WCAG, mnemonic, lệnh niêm yết, thanh tiêu đề theo tông)."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from pabt import giao_dien
from tests.test_chuan_giao_dien_wcag import AA_CHU, AA_PHI_CHU, tuong_phan


def _app():
    return QApplication.instance() or QApplication([])


class TestDongBoMau(unittest.TestCase):
    def test_so_0_va_vien_o_dat_wcag(self):
        self.assertGreaterEqual(tuong_phan(giao_dien.MAU_SO_KHONG, '#FFFFFF'), AA_CHU)
        self.assertGreaterEqual(tuong_phan('#8696AB', '#FFFFFF'), AA_PHI_CHU)

    def test_chu_hien_idempotent(self):
        self.assertEqual(giao_dien.chu_hien('A & B'), 'A && B')
        self.assertEqual(giao_dien.chu_hien('A && B'), 'A && B')


class TestLenhNiemYet(unittest.TestCase):
    def test_chon_ho_niem_yet_trong_lenh_can_du_an(self):
        from pabt.app import LENH_CAN_DU_AN
        self.assertIn('Chọn hộ niêm yết…', LENH_CAN_DU_AN)

    def test_chua_mo_du_an_nut_niem_yet_tat(self):
        _app()
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        self.addCleanup(w.close)
        a = w.lenh['Chọn hộ niêm yết…']
        self.assertFalse(a.isEnabled())
        self.assertIsNone(w.chon_ho_niem_yet(cho=False))


class TestMenuTitleCase(unittest.TestCase):
    def test_nhom_menu_khong_in_hoa_toan_bo(self):
        _app()
        from pabt.app import CuaSoChinh
        w = CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        m = w.khung_menu
        chu = m.tieu_de_nhom['1. Khái toán & dự toán'].text()
        self.assertIn('Khái toán', chu)
        self.assertNotIn('KHÁI TOÁN', chu)
        self.assertIn('&&', chu)


class TestThanhTieuDeTheoTong(unittest.TestCase):
    def test_mau_chrome_khong_con_xam_vscode(self):
        from pabt.thanh_tieu_de import _mau_chrome
        nen, vach, chu, mo = _mau_chrome()
        self.assertEqual((nen, vach, chu, mo), (
            giao_dien.TOKEN['nen'], giao_dien.TOKEN['vach'],
            giao_dien.TOKEN['chu'], giao_dien.TOKEN['chu_phu']))
        self.assertNotEqual(nen, '#F8F8F8')


class TestLichSu(unittest.TestCase):
    def test_phien_ban_dau_muc_khop(self):
        from pabt import __version__
        from pabt.lich_su_cap_nhat import MUC
        self.assertEqual(MUC[0][0], __version__)
