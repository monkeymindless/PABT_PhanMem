"""Khối chữ ký bản in: họ tên người ký căn giữa ngay dưới chức danh (in_an.can_khoi_ky) - người dùng 16/10/2026."""
from __future__ import annotations

import unittest

import openpyxl

from pabt import in_an


def _sheet():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'], ws['C1'], ws['G1'] = 'LẬP BIỂU  ', '   KIỂM TRA     ', '{CHUC_VU_KY}'
    ws.merge_cells('A1:B1')
    ws.merge_cells('C1:F1')
    ws.merge_cells('G1:H1')
    ws['A6'], ws['D6'], ws['G6'] = '{nguoi_lap}', '{nguoi_kiem_tra}', '{nguoi_ky}'
    ws.merge_cells('A6:B6')                     # đúng cột chức danh
    ws.merge_cells('D6:E6')                     # lệch: chức danh C:F
    for o in ('A6', 'D6', 'G6'):
        ws[o].alignment = openpyxl.styles.Alignment(horizontal='left', indent=2)
    return wb, ws


def _vung(ws, o):
    return next((str(m) for m in ws.merged_cells.ranges if o in m), o)


class TestKhoiKy(unittest.TestCase):
    def test_can_giua_duoi_chuc_danh(self):
        _, ws = _sheet()
        self.assertEqual(in_an.can_khoi_ky(ws), 3)
        self.assertEqual((ws['A1'].value, ws['C1'].value), ('LẬP BIỂU', 'KIỂM TRA'))      # bỏ dấu cách thừa
        self.assertEqual(ws['C6'].value, '{nguoi_kiem_tra}')                              # dời về cột đầu vùng chức danh
        self.assertEqual(_vung(ws, 'C6'), 'C6:F6')
        self.assertEqual(_vung(ws, 'G6'), 'G6:H6')                                        # một ô -> gộp theo chức danh
        self.assertEqual(_vung(ws, 'A6'), 'A6:B6')
        for o in ('A1', 'C1', 'A6', 'C6', 'G6'):
            self.assertEqual((ws[o].alignment.horizontal, ws[o].alignment.indent), ('center', 0), o)
        self.assertEqual(in_an.can_khoi_ky(ws), 3)                                        # chạy lại không đổi thêm
        self.assertEqual(_vung(ws, 'C6'), 'C6:F6')

    def test_khong_gop_de_len_o_khac(self):
        _, ws = _sheet()
        ws['F6'] = 'chữ khác'                                                             # ô trong vùng chức danh đã có chữ
        in_an.can_khoi_ky(ws)
        self.assertEqual(ws['D6'].value, '{nguoi_kiem_tra}')
        self.assertEqual(ws['F6'].value, 'chữ khác')
        self.assertEqual(ws['D6'].alignment.horizontal, 'center')


if __name__ == '__main__':
    unittest.main()
