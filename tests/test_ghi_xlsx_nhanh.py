"""Phương án đột phá 7 (30/10/2026): ghi_xlsx_nhanh dựng <sheetData> bằng chuỗi cho trang tính lớn - file ra phải GIỐNG wb.save thường
(giá trị, kiểu từng ô, ô gộp, cao / ẩn dòng, rộng cột, thiết lập in, ngắt trang). Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import shutil
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.pagebreak import Break

from pabt import an_toan, ghi_xlsx_nhanh


def _so_sanh(test, a: Path, b: Path):
    wa, wb_ = load_workbook(a), load_workbook(b)
    test.assertEqual(wa.sheetnames, wb_.sheetnames)
    for x, y in zip(wa.worksheets, wb_.worksheets):
        test.assertEqual(x.dimensions, y.dimensions, x.title)
        test.assertEqual(sorted(map(str, x.merged_cells.ranges)), sorted(map(str, y.merged_cells.ranges)))
        test.assertEqual(set(x._cells), set(y._cells), x.title)
        for k, c in x._cells.items():
            d = y._cells[k]
            test.assertEqual((c.value, c.data_type, c.number_format), (d.value, d.data_type, d.number_format), (x.title, k))
            for thuoc in ('font', 'border', 'fill', 'alignment', 'protection'):     # StyleProxy không so bằng nội dung: so đích
                test.assertEqual(getattr(c, thuoc)._StyleProxy__target, getattr(d, thuoc)._StyleProxy__target, (x.title, k, thuoc))
            test.assertEqual(c.quotePrefix, d.quotePrefix, k)
        test.assertEqual({r: dict(v) for r, v in x.row_dimensions.items()}, {r: dict(v) for r, v in y.row_dimensions.items()})
        test.assertEqual({k: dict(v) for k, v in x.column_dimensions.items()}, {k: dict(v) for k, v in y.column_dimensions.items()})
        test.assertEqual((x.print_title_rows, x.page_setup.scale, x.page_setup.orientation),
                         (y.print_title_rows, y.page_setup.scale, y.page_setup.orientation))
        test.assertEqual([b.id for b in x.row_breaks.brk], [b.id for b in y.row_breaks.brk])


def _wb_mau(so_dong: int) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Bảng'
    vien = Border(*(Side(style='thin'),) * 4)
    ws['A1'] = 'BẢNG TỔNG HỢP & <thử> "ngoặc"'
    ws['A1'].font = Font(bold=True, size=16)
    ws.merge_cells('A1:F1')
    for r in range(2, so_dong + 2):
        ws.cell(r, 1, r - 1).border = vien
        ws.cell(r, 2, f'  Hộ {r}  ' if r % 7 == 0 else f'Nguyễn Văn {r}\nẤp 1').alignment = Alignment(wrap_text=True, vertical='top')
        ws.cell(r, 3, Decimal('1234.5') * r).number_format = '#,##0.0#'
        ws.cell(r, 4, 0.1 * r if r % 3 else None)
        ws.cell(r, 5, f'=SUM(C{r}:D{r})')
        ws.cell(r, 6, r % 2 == 0)
        if r % 5 == 0:
            ws.cell(r, 7).fill = PatternFill('solid', fgColor='FFF4DB')     # ô chỉ có kiểu
            ws.row_dimensions[r].height = 31.5
        if r % 13 == 0:
            ws.row_dimensions[r].hidden = True
        ws.cell(r, 8, '   ')                                              # chỉ khoảng trắng
    for r in range(11, so_dong, 22):                                      # ô gộp dọc (ô bị gộp: MergedCell có kiểu viền)
        ws.merge_cells(start_row=r, start_column=2, end_row=r + 1, end_column=2)
    ws.row_dimensions[so_dong + 5].height = 20                            # dòng chỉ có chiều cao, không ô
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['D'].hidden = True
    ws.print_title_rows = '1:1'
    ws.page_setup.scale = 55
    ws.page_setup.orientation = 'landscape'
    ws.row_breaks.append(Break(id=50))
    nho = wb.create_sheet('Nhỏ')
    nho['A1'] = 'trang nhỏ ghi thường'
    return wb


class TestGhiNhanh(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_xlsx_'))
        self.addCleanup(shutil.rmtree, self.td, True)

    def test_giong_ghi_thuong(self):
        wb = _wb_mau(3000)
        self.assertEqual(ghi_xlsx_nhanh.luu(wb, self.td / 'nhanh.xlsx'), 1)
        _wb_mau(3000).save(self.td / 'thuong.xlsx')
        _so_sanh(self, self.td / 'nhanh.xlsx', self.td / 'thuong.xlsx')
        with zipfile.ZipFile(self.td / 'nhanh.xlsx') as z:
            self.assertIsNone(z.testzip())
            xml = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
        self.assertIn('xml:space="preserve"', xml)
        self.assertIn('&lt;thử&gt;', xml)
        self.assertFalse(list(self.td.glob('*.dang_ghi')))
        # ô của workbook không bị đổi sau khi lưu nhanh (lưu lần hai vẫn đủ)
        self.assertEqual(wb.active['B3'].value, 'Nguyễn Văn 3\nẤp 1')
        ghi_xlsx_nhanh.luu(wb, self.td / 'lan2.xlsx')
        _so_sanh(self, self.td / 'lan2.xlsx', self.td / 'thuong.xlsx')

    def test_nho_hoac_o_dac_biet_ghi_thuong(self):
        self.assertEqual(ghi_xlsx_nhanh.luu(_wb_mau(50), self.td / 'nho.xlsx'), 0)
        import datetime
        wb = _wb_mau(3000)
        wb.active['Z9'] = datetime.date(2026, 10, 30)                     # ô ngày: trang này ghi thường
        self.assertEqual(ghi_xlsx_nhanh.luu(wb, self.td / 'ngay.xlsx'), 0)
        wb = _wb_mau(3000)
        wb.active['Z9'].hyperlink = 'https://vi.du'
        self.assertEqual(ghi_xlsx_nhanh.luu(wb, self.td / 'lk.xlsx'), 0)
        self.assertEqual(load_workbook(self.td / 'ngay.xlsx').active['Z9'].value.year, 2026)

    def test_cong_luu_xlsx_van_khu_cong_thuc(self):
        wb = _wb_mau(3000)
        wb.active['Z1'] = '=HYPERLINK("http://x","y")'
        an_toan.luu_xlsx(wb, self.td / 'an_toan.xlsx')
        c = load_workbook(self.td / 'an_toan.xlsx').active['Z1']
        self.assertEqual((c.data_type, c.quotePrefix), ('s', True))
        self.assertEqual(load_workbook(self.td / 'an_toan.xlsx').active['E2'].value, '=SUM(C2:D2)')

    def test_bang_tong_hop_that(self):
        """Bảng tổng hợp lập từ dự án giả lập: ghi nhanh và ghi thường cho cùng nội dung, kể cả sau bước chèn đường kẻ."""
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest('không có Qt')
        QApplication.instance() or QApplication([])
        from pabt import csdl, in_an
        from tests.test_toc_do import _du_an
        con = csdl.mo(_du_an(self.td, 400))
        self.addCleanup(con.close)
        with mock.patch.object(ghi_xlsx_nhanh, 'NGUONG_O', 1000):
            in_an.lap_bang_tong_hop(con, self.td / 'bth_nhanh.xlsx')
        with mock.patch.object(ghi_xlsx_nhanh, 'NGUONG_O', 10 ** 9):
            in_an.lap_bang_tong_hop(con, self.td / 'bth_thuong.xlsx')
        _so_sanh(self, self.td / 'bth_nhanh.xlsx', self.td / 'bth_thuong.xlsx')


if __name__ == '__main__':
    unittest.main()
