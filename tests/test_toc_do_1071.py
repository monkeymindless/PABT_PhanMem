"""Đợt tăng tốc 1.0.71: kết quả không đổi. Làm tròn tiền (đường nhanh), tắt dọn rác có phạm vi, tên máy, trợ giúp dòng lệnh, tìm Tesseract. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import gc
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from pabt import csdl, loai_dat, ocr, tien


class TestLamTron(unittest.TestCase):
    def test_nua_xa_so_khong_nhu_excel(self):
        for x, kq in (('0.5', '1'), ('-0.5', '-1'), ('1.5', '2'), ('2.5', '3'), ('-2.5', '-3'), ('0.49999', '0'), ('999.5', '1000')):
            self.assertEqual(str(tien.lam_tron(Decimal(x))), kq, x)

    def test_khong_ra_am_khong(self):
        for x in ('-0.4', '-0.49', '-0', '-0.0000'):
            self.assertEqual(str(tien.lam_tron(Decimal(x))), '0', x)
            self.assertEqual(tien.vn(Decimal(x)), '0', x)

    def test_so_chu_so_khac(self):
        self.assertEqual(str(tien.lam_tron(Decimal('1234'), -2)), '1200')
        self.assertEqual(str(tien.lam_tron(Decimal('1250'), -2)), '1300')
        self.assertEqual(str(tien.lam_tron(Decimal('1.005'), 2)), '1.01')
        self.assertEqual(str(tien.lam_tron(Decimal('-1.005'), 2)), '-1.01')
        self.assertEqual(tien.vn(Decimal('1480500')), '1.480.500')
        self.assertEqual(tien.vn(Decimal('-1480500.5')), '-1.480.501')
        self.assertEqual(tien.vn(Decimal('143.85'), 1), '143,9')
        self.assertEqual(tien.so_vn(Decimal('410.6')), '410,6')

    def test_chuoi_va_none_van_doc_duoc(self):
        self.assertEqual(tien.vn('1.480.500'), '1.480.500')
        self.assertEqual(tien.vn(None), '0')
        self.assertEqual(tien.vn(143.8, 1), '143,8')

    def test_bo_dau_nhan_moi_kieu(self):
        self.assertEqual(loai_dat._bo_dau('Đất Ở'), 'dat o')
        self.assertEqual(loai_dat._bo_dau(None), '')
        self.assertEqual(loai_dat._bo_dau(5), '5')
        self.assertTrue(tien.la_cong_thuc('12x3+1,5'))
        self.assertFalse(tien.la_cong_thuc('1.480.500'))


class TestTamTatGc(unittest.TestCase):
    def setUp(self):
        self.addCleanup(gc.enable)

    def test_tra_lai_trang_thai(self):
        gc.enable()
        with csdl.tam_tat_gc():
            self.assertFalse(gc.isenabled())
            with csdl.tam_tat_gc():                     # lồng: tầng trong không được bật lại
                pass
            self.assertFalse(gc.isenabled())
        self.assertTrue(gc.isenabled())

    def test_loi_van_bat_lai(self):
        gc.enable()
        with self.assertRaises(ValueError):
            with csdl.tam_tat_gc():
                raise ValueError
        self.assertTrue(gc.isenabled())

    def test_khong_tu_bat_neu_truoc_do_da_tat(self):
        gc.disable()
        with csdl.tam_tat_gc():
            pass
        self.assertFalse(gc.isenabled())

    def test_dung_lam_decorator_nhieu_lan(self):
        gc.enable()

        @csdl.tam_tat_gc()
        def f():
            return gc.isenabled()
        self.assertFalse(f())
        self.assertFalse(f())
        self.assertTrue(gc.isenabled())


class TestKhac(unittest.TestCase):
    def test_ten_may_chi_hoi_he_thong_mot_lan(self):
        csdl._TEN_MAY.clear()
        self.addCleanup(csdl._TEN_MAY.clear)
        with mock.patch('socket.gethostname', return_value='MAY-A') as g:
            self.assertEqual(csdl.ten_may(), 'MAY-A')
            self.assertEqual(csdl.ten_may(), 'MAY-A')
        self.assertEqual(g.call_count, 1)

    def test_ten_may_loi_khong_nho(self):
        csdl._TEN_MAY.clear()
        self.addCleanup(csdl._TEN_MAY.clear)
        with mock.patch('socket.gethostname', side_effect=OSError):
            self.assertEqual(csdl.ten_may(), '')
        with mock.patch('socket.gethostname', return_value='MAY-B'):
            self.assertEqual(csdl.ten_may(), 'MAY-B')

    def test_tro_giup_dong_lenh_khong_phu_thuoc_docstring(self):
        s = (Path(__file__).resolve().parents[1] / 'chay.py').read_text(encoding='utf-8')
        self.assertNotIn('print(__doc__)', s)
        self.assertIn('print(_CACH_DUNG)', s)
        self.assertIn('python chay.py nhap', s)

    def test_tim_tesseract_o_x64_khi_chay_ngay_x86(self):
        cuc = Path('C:/zip/x86/PABT.exe')
        with mock.patch.object(sys, 'frozen', True, create=True), mock.patch.object(sys, 'executable', str(cuc)):
            ds = [str(x).replace('\\', '/') for x in ocr._ung_vien()]
        self.assertEqual(ds[0], 'C:/zip/x86/tesseract/tesseract.exe')
        self.assertEqual(ds[1], 'C:/zip/x64/tesseract/tesseract.exe')


if __name__ == '__main__':
    unittest.main()
