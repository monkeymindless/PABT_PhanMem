"""30/10/2026 (người dùng): (1) văn bản đơn giá cây lâu năm chỉ ghi "Năm thứ 1, 2, 3" và "Năm thu hoạch thứ…", KHÔNG có chú thích
"(Năm thứ 3,4,5)" - năm tuổi tính theo cấu trúc (năm thu hoạch thứ k = số năm kiến thiết của loài + k), tên trong bộ đơn giá bỏ chú
thích; (2) xuất phương án chi tiết ra Excel - các hộ trong MỘT file, mỗi hộ một sheet."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from tests import APP  # noqa: F401

from pabt import hieu_tai_san as h


class TestNamTuoi(unittest.TestCase):
    DS = ['Cây cam - Năm thứ 1', 'Cây cam - Năm thứ 2', 'Cây cam - Năm thứ 3', 'Cây cam - Năm thu hoạch thứ 1 - 3',
          'Cây cam - Năm thu hoạch thứ 4 - 6', 'Cây cam - Năm thu hoạch thứ 10 trở đi',
          'Cây dứa - Năm 1', 'Cây dứa - Năm thu hoạch thứ 1', 'Cây dứa - Năm thu hoạch thứ 2',
          'Cây dừa - Năm thứ 1', 'Cây dừa - Năm thứ 2', 'Cây dừa - Năm thứ 3', 'Cây dừa - Năm thứ 4', 'Cây dừa - Năm thu hoạch thứ 1 - 5',
          'Cây cóc - Năm 1', 'Cây cóc - Năm 2', 'Cây cóc - Năm thu hoạch 6 - 10']

    def test_theo_cau_truc(self):
        bt = h.bang_tuoi(self.DS)
        self.assertEqual(bt['Cây cam - Năm thứ 3'], (3, 3))
        self.assertEqual(bt['Cây cam - Năm thu hoạch thứ 1 - 3'], (4, 6))            # 3 năm kiến thiết + năm thu hoạch 1-3
        self.assertEqual(bt['Cây cam - Năm thu hoạch thứ 10 trở đi'], (13, None))
        self.assertEqual(bt['Cây dứa - Năm thu hoạch thứ 1'], (2, 2))                  # dứa (1 năm kiến thiết) khác dừa (4 năm)
        self.assertEqual(bt['Cây dừa - Năm thu hoạch thứ 1 - 5'], (5, 9))
        self.assertEqual(bt['Cây cóc - Năm thu hoạch 6 - 10'], (8, 12))               # "Năm thu hoạch 6 - 10" (văn bản không ghi "thứ")

    def test_chu_thich_cu_khong_con_quyet_dinh(self):
        # tên cũ còn chú thích sai ("(Năm thứ 3,4,5)" của cam): theo cấu trúc, không theo chú thích
        bt = h.bang_tuoi(['Cây cam - Năm thứ 1', 'Cây cam - Năm thứ 2', 'Cây cam - Năm thứ 3',
                          'Cây cam - Năm thu hoạch thứ 1-3 (Năm thứ 3,4,5)'])
        self.assertEqual(bt['Cây cam - Năm thu hoạch thứ 1-3 (Năm thứ 3,4,5)'], (4, 6))
        self.assertEqual(h.khoang_tuoi('Cây xoài - Năm thu hoạch thứ 1-5 (Năm thứ 4,5,6,7,8)'), (4, 8))   # gọi lẻ: vẫn đọc chú thích

    def test_chon_theo_tuoi(self):
        class M:
            def __init__(self, ten):
                self.ten = ten
        ds = [M(t) for t in self.DS]
        self.assertEqual(h.chon_theo_tuoi(ds, 'Cam', 5).ten, 'Cây cam - Năm thu hoạch thứ 1 - 3')
        self.assertEqual(h.chon_theo_tuoi(ds, 'Cam', 2).ten, 'Cây cam - Năm thứ 2')
        self.assertEqual(h.chon_theo_tuoi(ds, 'Cam', 30).ten, 'Cây cam - Năm thu hoạch thứ 10 trở đi')


class TestExcelNhieuSheet(unittest.TestCase):
    def setUp(self):
        from tests.test_toc_do import _du_an
        from pabt import csdl
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 4))
        self.ds = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def test_moi_ho_mot_sheet(self):
        from openpyxl import load_workbook
        from pabt import in_excel_chi_tiet as xe
        f = xe.xuat_chi_tiet_xlsx(self.con, self.ds, Path(self.tmp.name) / 'ct.xlsx')
        wb = load_workbook(f)
        self.assertEqual(len(wb.worksheets), len(self.ds))
        ws = wb.worksheets[0]
        self.assertTrue(ws.title.startswith('1. '))
        chu = [c.value for r in ws.iter_rows() for c in r if c.value is not None]
        self.assertIn('PHƯƠNG ÁN CHI TIẾT', chu)
        self.assertIn('TỔNG CỘNG', chu)
        # thành tiền là SỐ; dòng TỔNG CỘNG = tổng phương án của hộ
        from pabt.nghiep_vu import BoiCanh, doc_phuong_an, tinh_pa
        kq = tinh_pa(doc_phuong_an(self.con, self.ds[0]), BoiCanh.tu(self.con))
        r_tc = next(c.row for r in ws.iter_rows() for c in r if c.value == 'TỔNG CỘNG')
        self.assertEqual(ws.cell(r_tc, 7).value, int(kq.tong))
        self.assertEqual(ws.cell(r_tc, 7).number_format, '#,##0')
        self.assertEqual(str(ws.page_setup.paperSize), str(ws.PAPERSIZE_A4))
        self.assertTrue(ws.print_title_rows)

    def test_ten_sheet_hop_le_khong_trung(self):
        from pabt.in_excel_chi_tiet import ten_sheet
        da = set()
        a = ten_sheet(1, 'Nguyễn Văn A / B: [đồng sở hữu]*', da)
        b = ten_sheet(1, 'Nguyễn Văn A / B: [đồng sở hữu]*', da)
        self.assertNotRegex(a, r'[:\\/?*\[\]]')
        self.assertLessEqual(len(a), 31)
        self.assertNotEqual(a.lower(), b.lower())
        self.assertTrue(b.endswith('(2)'))

    def test_xuat_bo_ho_so_kem_excel(self):
        from pabt import van_ban_trinh as vb
        kq = vb.xuat_bo_ho_so(self.con, self.ds, Path(self.tmp.name) / 'in', chi_tiet=False, bang_tong_hop=False,
                              chi_tiet_excel=True)
        self.assertEqual([p.name for p in kq['excel']], ['PHUONG_AN_CHI_TIET.xlsx'])
        self.assertEqual(kq['excel'][0].parent.name, vb.THU_MUC_CT)


if __name__ == '__main__':
    unittest.main()
