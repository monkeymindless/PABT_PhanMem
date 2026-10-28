"""1.0.17 nền tảng giao diện 2.0: mật độ bảng + tương phản cao."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import chu_de


class _CaiDat:
    def __init__(self, d=None):
        self.d = dict(d or {})

    def value(self, k, mac_dinh=None):
        return self.d.get(k, mac_dinh)

    def setValue(self, k, v):
        self.d[k] = v


class TestChuDe(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.pop(k, None) for k in ('PABT_MAT_DO', 'PABT_TUONG_PHAN_CAO')}

    def tearDown(self):
        for k, v in self._env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_mac_dinh_va_gia_tri_la(self):
        self.assertEqual(chu_de.doc(None), {'mat_do': 'chuan', 'tuong_phan': 'theo_windows', 'tong_nen': 'sang'})   # 1.0.33: tông nền
        self.assertEqual(chu_de.doc(_CaiDat({chu_de.KHOA_MAT_DO: 'lung tung'}))['mat_do'], 'chuan')

    def test_ghi_doc_va_moi_truong(self):
        c = _CaiDat()
        chu_de.ghi(c, mat_do='gon', tuong_phan='bat')
        self.assertEqual(chu_de.doc(c), {'mat_do': 'gon', 'tuong_phan': 'bat', 'tong_nen': 'sang'})
        os.environ['PABT_MAT_DO'] = 'thoang'
        self.assertEqual(chu_de.doc(c)['mat_do'], 'thoang')

    def test_chieu_cao_tang_dan(self):
        self.assertLess(chu_de.cao_dong('gon'), chu_de.cao_dong('chuan'))
        self.assertLess(chu_de.cao_dong('chuan'), chu_de.cao_dong('thoang'))
        self.assertEqual(chu_de.cao_dong('chuan'), 30)

    def test_tuong_phan_cao(self):
        self.assertTrue(chu_de.dang_tuong_phan_cao('bat'))
        self.assertFalse(chu_de.dang_tuong_phan_cao('tat'))


class TestGiaoDien(unittest.TestCase):
    def test_dat_mat_do_va_hop(self):
        from PySide6.QtWidgets import QApplication
        from pabt import giao_dien
        app = QApplication.instance() or QApplication([])
        giao_dien.ap_dung(app)
        try:
            self.assertEqual(giao_dien.dat_mat_do('gon'), 'gon')
            self.assertEqual(giao_dien.CAO_DONG_BANG, 26)
            self.assertEqual(giao_dien.dat_mat_do('thoang'), 'thoang')
            self.assertEqual(giao_dien.CAO_DONG_BANG, 36)
            from pabt.man_hinh_giao_dien import HopGiaoDien
            h = HopGiaoDien(im_lang=True)
            self.assertEqual(set(h.r_mat_do), set(chu_de.MAT_DO))
            self.assertTrue(h.r_mat_do['thoang'].isChecked())
        finally:
            giao_dien.dat_mat_do('chuan')

    def test_qss_tuong_phan_khong_dat_mau(self):
        from pabt import giao_dien
        q = giao_dien._qss_tuong_phan_cao()
        for tu in ('color', 'background', '#'):
            self.assertNotIn(tu, q)


if __name__ == '__main__':
    unittest.main()
