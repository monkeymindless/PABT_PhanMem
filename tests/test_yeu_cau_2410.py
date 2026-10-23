"""24/10/2026 (người dùng): chữ ký dịch trái, đường kẻ dưới "Dự án" / "CHI NHÁNH" / tiêu ngữ, nhãn "DỰ ÁN" / "Dự án" theo tên dự án in hoa hay
không, dòng "CHI NHÁNH …" của bảng tổng hợp, tiêu đề mục I theo chủ sử dụng. Tên, số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl  # noqa: E402

from pabt import csdl, du_lieu_in, in_an  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class TestNhanDuAn(unittest.TestCase):
    def test_in_hoa_hay_khong(self):
        self.assertEqual(du_lieu_in.nhan_du_an('ĐƯỜNG NGUYỄN ĐÌNH CHIỂU'), 'DỰ ÁN')
        self.assertEqual(du_lieu_in.nhan_du_an('Đường Nguyễn Đình Chiểu'), 'Dự án')
        self.assertEqual(du_lieu_in.nhan_du_an('đường nguyễn đình chiểu'), 'Dự án')
        self.assertEqual(du_lieu_in.nhan_du_an('ĐƯỜNG 25B - KHU 3'), 'DỰ ÁN')            # số, dấu gạch không ảnh hưởng
        self.assertEqual(du_lieu_in.nhan_du_an(''), 'Dự án')


class TestBangTongHopDauTrang(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        self.con = csdl.mo(_du_an(self.td, 2))
        self.addCleanup(self.con.close)

    def _bang(self, ten: str, du_thao: bool = False):
        with self.con:
            self.con.execute("UPDATE du_an SET ten = ?, don_vi_cap_tren = 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT', "
                             "don_vi_tieu_de = 'THÀNH PHỐ ĐỒNG NAI' WHERE id = 1", (ten,))
        return openpyxl.load_workbook(in_an.lap_bang_tong_hop(self.con, self.td / f'b{abs(hash((ten, du_thao)))}.xlsx', du_thao=du_thao)).active

    def test_dong_chi_nhanh_va_nhan_du_an(self):
        ws = self._bang('ĐƯỜNG MẪU')
        self.assertEqual(ws['A1'].value, 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT THÀNH PHỐ ĐỒNG NAI')       # dòng 1: cơ quan chủ quản (một dòng)
        self.assertTrue(ws['A2'].value.startswith('CHI NHÁNH'))                                   # dòng 2: CHI NHÁNH … đậm
        self.assertTrue(ws['A2'].font.b)
        self.assertEqual(ws['A6'].value, 'DỰ ÁN ĐƯỜNG MẪU')
        self.assertEqual(self._bang('Đường Mẫu')['A6'].value, 'Dự án Đường Mẫu')

    def test_du_thao_hien_chu_du_thao_chinh_thuc_khong(self):
        dt, ct = self._bang('ĐƯỜNG MẪU', True), self._bang('ĐƯỜNG MẪU', False)
        chu = lambda ws: ' '.join(str(o.value) for o in ws._cells.values() if isinstance(o.value, str))      # noqa: E731
        self.assertIn('(DỰ THẢO)', chu(dt))
        self.assertNotIn('DỰ THẢO', chu(ct))


class TestDuongKe(unittest.TestCase):
    def test_hang_so_duong_ke(self):
        self.assertEqual(in_an.DK_CHI_NHANH_NGAN_CM, 1.0)            # đường kẻ dưới CHI NHÁNH ngắn hơn chữ 1 cm
        self.assertLess(in_an.DK_CACH_DU_AN, in_an.DK_CACH)           # đường kẻ dưới Dự án gần chữ hơn các đường khác
        self.assertGreater(in_an.DK_CACH_DU_AN, 0)


if __name__ == '__main__':
    unittest.main()
