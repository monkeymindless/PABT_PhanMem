"""0.9.65 rà soát tải lớn 5.000 hộ / 10.000 thửa (ket_qua_kiem_tra/thu_that/do_tai_lon.py): tối ưu cho kết quả GIỐNG HỆT bản cũ,
và lỗi tên mẫu dự thảo có dấu."""
from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from tests.test_toc_do import _du_an


class TestLoiFontNhanh(unittest.TestCase):
    def test_duong_tat_giong_nhanh_day_du(self):
        from pabt import kiem_loi
        random.seed(7)
        bang = list('abcAZ09 ,.-()ÀàảãạăằđĐƯươờØø∅Φ²µ¸¶©Ç\t\n') + ['́', '̣', 'ß', '€', '漢', '\x07']
        for _ in range(30000):
            s = ''.join(random.choice(bang) for _ in range(random.randint(0, 14)))
            self.assertEqual(kiem_loi.loi_font(s), kiem_loi._loi_font_day_du(s), repr(s))

    def test_vi_du(self):
        from pabt.kiem_loi import loi_font
        self.assertEqual(loi_font('Nguyễn Văn Thử, ấp 7 – xã Trị An'), '')
        self.assertEqual(loi_font('Ống Ø114 dài 2m'), '')
        self.assertIn('tổ hợp', loi_font('Nguyễn'))
        self.assertIn('TCVN3', loi_font('NguyÔn V¨n'))


class TestBaoCaoDoiChieuKieu(unittest.TestCase):
    """Báo cáo đối chiếu chép mảng chỉ số kiểu (nhanh ×2,3 với 5.000 hộ): mọi ô vẫn đúng viền / định dạng số / nền."""

    def test_kieu_tung_o(self):
        import openpyxl
        from pabt import csdl, doi_chieu
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = Path(td.name)
        con = csdl.mo(_du_an(d, 6))
        self.addCleanup(con.close)
        kq = doi_chieu.doi_chieu(con)
        f = d / 'dc.xlsx'
        doi_chieu.xuat_bao_cao(kq, f, 'Thử', 'x', ra_soat=[])
        ws = openpyxl.load_workbook(f)['TONG_HO']
        for r in range(6, 6 + len(kq.ho)):
            for c in range(1, 12):
                o = ws.cell(r, c)
                self.assertEqual(o.border.left.style, 'thin', o.coordinate)
                self.assertEqual(o.number_format, doi_chieu._SO if 3 <= c <= 10 else 'General', o.coordinate)
            mau = ws.cell(r, 11).fill.fgColor.rgb
            self.assertIn(mau, ('00F8CBAD', '00E2EFDA', 'FFF8CBAD', 'FFE2EFDA'))
        self.assertEqual(ws.cell(5, 1).font.b, True)                    # tiêu đề cột không bị chép kiểu ô số liệu
