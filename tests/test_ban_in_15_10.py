"""Bản in phương án chi tiết (người dùng 15/10/2026, sau 0.9.92): khoảng hở nguồn gốc đất -> mục III, dòng tên chính sách hỗ trợ đào tạo
không lặp số của dòng thửa, dòng Tái định cư nhãn đậm + nội dung chữ thường. Số liệu GIẢ LẬP."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import chinh_sach, csdl, in_an, lap_pa
from tests.test_toc_do import _du_an

NGUON_GOC = ('Đất do ông Nguyễn Văn A khai phá sử dụng ổn định từ năm 1990, không tranh chấp; năm 2002 chuyển nhượng cho bà Nguyễn '
             'Thị B, sau đó ông Nguyễn Thanh C được thừa kế và sử dụng tới nay.')


class TestBanInChiTiet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        td = Path(cls.tmp.name)
        con = csdl.mo(_du_an(td, 3))
        try:
            bo = lap_pa.BoSoan(con, 2)
            m = next(x for x in bo.dm.muc[4] if x.ma == 'CS9')
            bo.pa.khoan[4] = [d for d in bo.pa.khoan[4] if d.ma not in ('CS9', 'CS10')]
            bo.them_dong_ho_tro([chinh_sach.dong_dao_tao(m, 'Thửa đất số 394, tờ bản đồ số 35, loại đất NTS', '215,1', '610000',
                                                         '1,5')])
            bo.luu()
            with con:
                con.execute('UPDATE thua SET nguon_goc = ? WHERE ma_ho = 2', (NGUON_GOC,))
                con.execute('UPDATE ho SET tai_dinh_cu = ? WHERE ma_ho = 2', (lap_pa.TAI_DINH_CU[3],))
            f = in_an.lap_chi_tiet(con, 2, td / 'ct.xlsx')
        finally:
            con.close()
        cls.ws = openpyxl.load_workbook(f, rich_text=True).active

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _dong(self, dau: str) -> int:
        return next(r for r in range(1, self.ws.max_row + 1)
                    if any(str(self.ws.cell(r, c).value or '').lstrip(in_an.NBSP).startswith(dau) for c in (1, 2)))

    def test_nguon_goc_sat_muc_iii(self):
        ws = self.ws
        r, r3 = self._dong('Đất do ông'), self._dong('III.')
        co_chu = [rr for rr in range(r, r3) if ws.cell(rr, 1).value]
        for rr in range(r, r3):                         # dòng thừa của vùng gộp mẫu: ẩn (trước đây cao 4 pt mỗi dòng)
            self.assertTrue(rr in co_chu or ws.row_dimensions[rr].hidden, rr)
        self.assertEqual(co_chu, list(range(r, co_chu[-1] + 1)))                     # các dòng nguồn gốc liền nhau
        rong, phong = in_an._rong_vung(ws, 1, 8), in_an._phong(ws.cell(r, 1))
        for rr in co_chu:                               # 16/10/2026: đệm 1,5 pt giữa các dòng, dòng cuối (trước III) thêm 4 pt
            so = len(in_an._ngat(ws.cell(rr, 1).value, rong, *phong, treo=False))
            self.assertAlmostEqual(ws.row_dimensions[rr].height, in_an.cao_doan_van(so, 14, cuoi=rr == co_chu[-1]), places=2)
            self.assertLess(ws.row_dimensions[rr].height, in_an.cao_dong_bang(so, 14))   # đệm nhỏ hơn ô bảng (8 pt)

    def test_dong_ten_dao_tao_khong_lap_so(self):
        ws = self.ws
        r = self._dong('Hỗ trợ đào tạo')
        self.assertEqual([ws.cell(r, c).value for c in range(3, 8)], [None] * 5)     # ĐVT, SL, ĐG, tỷ lệ, thành tiền trống
        self.assertTrue(str(ws.cell(r, 8).value or ''))                                # căn cứ giữ
        con = [ws.cell(r + 1, c).value for c in range(1, 8)]
        self.assertEqual(con[0], '-')
        self.assertEqual((con[3], con[6]), (215.1, 196817000))                         # số liệu ở dòng thửa

    def test_tai_dinh_cu_nhan_dam_noi_dung_thuong(self):
        o = self.ws.cell(self._dong('IV'), 2)
        khoi = list(o.value)
        self.assertEqual(khoi[0].text, in_an.NHAN_TDC)
        self.assertTrue(khoi[0].font.b)
        self.assertTrue(khoi[1].text.strip().startswith('Đủ điều kiện'))
        self.assertFalse(khoi[1].font.b)
        self.assertFalse(khoi[1].font.i)
        self.assertNotEqual(khoi[1].text, khoi[1].text.upper())


if __name__ == '__main__':
    unittest.main()
