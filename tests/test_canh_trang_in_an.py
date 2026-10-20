"""Bộ căn trang thông minh bản in phương án chi tiết (pabt/canh_trang_in_an.py, người dùng 20/10/2026 - "trang 2 mồ côi"). Số liệu GIẢ
LẬP; trang tính dựng tay bằng openpyxl (không cần Excel)."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl                                                                  # noqa: E402
from PySide6.QtWidgets import QApplication                                       # noqa: E402

from pabt import csdl, in_an                                                     # noqa: E402
from pabt.canh_trang_in_an import NGUONG_DU_1_TRANG_PT, BoCanhTrangInAn          # noqa: E402


def _ws(cao_dong: list):
    """Trang tính A4 dọc, lề phương án chi tiết, tỷ lệ 100%, dòng r cao cao_dong[r - 1] (có chữ để xep_trang thấy)."""
    ws = openpyxl.Workbook().active
    ws.page_setup.paperSize, ws.page_setup.orientation = 9, 'portrait'
    in_an.chuan_le_trang(ws, 'chi_tiet')
    ws.page_setup.scale = 100
    for r, h in enumerate(cao_dong, start=1):
        ws.cell(r, 1).value = f'dòng {r}'
        ws.row_dimensions[r].height = h
    return ws


class TestGomMotTrang(unittest.TestCase):
    def test_tran_it_gom_vua_1_trang(self):
        cap = in_an.cao_trang_in(_ws([20]))
        n = int((cap + 60) // 20)                       # tràn ~60 pt
        ws = _ws([20] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        self.assertEqual(len(trang), 2)
        in_an.ghi_ngat_trang(ws, trang)
        ws.print_title_rows = '1:1'
        kq = BoCanhTrangInAn.tu_dong_chinh_trang(ws, trang, cap)
        self.assertTrue(kq['mot_trang'])
        # 1.0.07: không bật "vừa N trang" - thu tỷ lệ in (>= TI_LE_CT_MIN) cho vừa một trang
        self.assertFalse(ws.sheet_properties.pageSetUpPr.fitToPage)
        self.assertTrue(in_an.TI_LE_CT_MIN <= int(ws.page_setup.scale) < 100)
        self.assertLessEqual(BoCanhTrangInAn.tong_noi_dung(ws, trang), in_an.cao_trang_in(ws) + 0.5)
        self.assertEqual(ws.row_breaks.brk, [])
        self.assertIsNone(ws.print_title_rows)
        self.assertEqual((ws.page_setup.orientation, int(ws.page_setup.paperSize)), ('portrait', 9))

    def test_tran_nhieu_giu_hai_trang(self):
        cap = in_an.cao_trang_in(_ws([20]))
        n = int((cap + NGUONG_DU_1_TRANG_PT + 80) // 20)
        ws = _ws([20] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        kq = BoCanhTrangInAn.tu_dong_chinh_trang(ws, trang, cap)
        self.assertFalse(kq['mot_trang'])
        self.assertEqual(len(kq['trang']), 2)
        self.assertFalse(bool(ws.sheet_properties.pageSetUpPr and ws.sheet_properties.pageSetUpPr.fitToPage))

    def test_tat_gom(self):
        cap = in_an.cao_trang_in(_ws([20]))
        n = int((cap + 40) // 20)
        ws = _ws([20] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        self.assertFalse(BoCanhTrangInAn.tu_dong_chinh_trang(ws, trang, cap, cho_phep_fit_1_trang=False)['mot_trang'])


class TestCanBangHaiTrang(unittest.TestCase):
    def test_trang_2_bat_dau_tron_mot_muc(self):
        cap = in_an.cao_trang_in(_ws([20]))
        n = int((cap * 1.6) // 20)
        ws = _ws([20] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        self.assertEqual(len(trang), 2)
        dau2 = trang[1][0]
        muc = [dau2 - 4, dau2 + 3]                      # tiêu đề mục: 4 dòng trước ranh (trang 2 bắt đầu GIỮA mục) và sau
        moi = BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, muc)
        self.assertEqual(moi[1][0], dau2 - 4)           # dời ngắt lên trước tiêu đề mục
        self.assertEqual(moi[0][1], dau2 - 5)
        self.assertLessEqual(moi[1][2], cap)

    def test_khong_doi_khi_da_dung_dau_muc_hoac_trang_1_qua_vang(self):
        cap = in_an.cao_trang_in(_ws([20]))
        n = int((cap * 1.6) // 20)
        ws = _ws([20] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        self.assertIs(BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, [trang[1][0]]), trang)
        self.assertIs(BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, [3]), trang)       # trang 1 chỉ còn 2 dòng: không dời


class TestAnDongTrong(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_an_cccd_sdt_trong(self):
        ws = openpyxl.Workbook().active
        for r, nhan in enumerate(('Họ và tên:', 'Số CCCD:', 'Địa chỉ thường trú:', 'Số điện thoại:'), start=1):
            ws.cell(r, 1).value = nhan
        an = BoCanhTrangInAn.an_dong_trong_khoi_i(ws, 10, dict(cccd='', dien_thoai='0900000000'))
        self.assertEqual(an, [2])
        self.assertTrue(ws.row_dimensions[2].hidden)
        self.assertFalse(ws.row_dimensions[4].hidden)

    def test_ban_in_chi_tiet_an_dong_trong(self):
        from tests.test_in_16_10 import _du_an_to_chuc
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            con = csdl.mo(_du_an_to_chuc(td, 1, 1))
            try:
                ma = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
                with con:
                    con.execute("UPDATE ho SET so_cccd = '', dien_thoai = '' WHERE ma_ho = ?", (ma[1],))
                ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, ma[1], td / 'a.xlsx')).active
                for nhan in ('Số CCCD:', 'Số điện thoại:'):
                    r = next(r for r in range(1, 20) if any(ws.cell(r, c).value == nhan for c in range(1, 9)))
                    self.assertTrue(ws.row_dimensions[r].hidden, nhan)
                with con:
                    con.execute("UPDATE ho SET so_cccd = '079123456789', dien_thoai = '0900000000' WHERE ma_ho = ?", (ma[1],))
                ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, ma[1], td / 'b.xlsx')).active
                r = next(r for r in range(1, 20) if any(ws.cell(r, c).value == 'Số CCCD:' for c in range(1, 9)))
                self.assertFalse(ws.row_dimensions[r].hidden)
            finally:
                con.close()

    def test_le_trang_va_kho_a4(self):
        le = in_an.LE_TRANG['chi_tiet']
        self.assertEqual((le['top'], le['bottom'], le['left'], le['right']), (0.394, 0.315, 0.315, 0.118))   # 1.0.07: 1,0 / 0,8 / 0,8 / 0,3 cm
        ws = openpyxl.Workbook().active
        self.assertEqual(in_an.chuan_le_trang(ws, 'chi_tiet')['top'], 0.394)               # hồ sơ địa phương mặc định cùng số
        self.assertEqual(in_an.DEM_DONG, 4.0)
        self.assertEqual(in_an.CAO_DONG_BANG_TOI_THIEU, 20.0)
        self.assertIn(f'dem = {in_an.DEM_DONG}', in_an._VBS)                               # VBS xuất PDF cùng đệm
        self.assertIn('cmin = 20', in_an._VBS)


if __name__ == '__main__':
    unittest.main()
