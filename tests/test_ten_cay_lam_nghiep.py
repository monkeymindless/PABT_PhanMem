"""26/10/2026 (người dùng): tên Việt Nam khác của cây lâm nghiệp (Phụ lục VI QĐ 48/2025/QĐ-UBND) trong bộ đơn giá cây trồng - tìm cây
theo tên gọi khác; tên cũ (bản in / văn bản không ghi tên khác) vẫn khớp."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, don_gia, ten_cay_lam_nghiep as t


class TestTenKhac(unittest.TestCase):
    def test_them_va_bo_ten_khac(self):
        self.assertEqual(t.them_ten_khac('Bách xanh (d >6-9 cm)'), 'Bách xanh (Tùng hương) (d >6-9 cm)')
        self.assertEqual(t.them_ten_khac('Cẩm lai (d <3 cm)'), 'Cẩm lai (Cẩm lai bông, Cẩm lai mật) (d <3 cm)')
        self.assertEqual(t.them_ten_khac('Huỷnh (d >3-6 cm)'), 'Huỷnh (Huyện) (d >3-6 cm)')          # văn bản "Huỳnh", bộ "Huỷnh"
        self.assertEqual(t.them_ten_khac('Gội nước.hoa to (d <3 cm)'), 'Gội nước hoa to (Gội gác, Gội tẻ) (d <3 cm)')
        x = t.them_ten_khac('Bách xanh (d >6-9 cm)')
        self.assertEqual(t.them_ten_khac(x), x)                                  # gọi lại không thêm lần nữa
        self.assertEqual(t.bo_ten_khac(x), 'Bách xanh (d >6-9 cm)')
        for giu in ('Bách đài loan (d <3 cm)', 'Cây mít - Năm thứ 1', 'Bách xanh', 'Nhà cấp 4'):
            self.assertEqual(t.them_ten_khac(giu), giu)                          # không tên khác / không phải dòng đường kính

    def test_bo_don_gia_dong_goi_da_co_ten_khac(self):
        c = sqlite3.connect(csdl.uri_chi_doc(don_gia.file_goc()), uri=True)
        try:
            ten = [r[0] for r in c.execute('SELECT ten FROM dm_taisan WHERE nhom = 3')]
        finally:
            c.close()
        self.assertIn('Bách xanh (Tùng hương) (d >6-9 cm)', ten)
        self.assertIn('Dó bầu (Trầm hương) (d >6-9 cm)', ten)
        self.assertIn('Lòng mức trung bộ (Thừng mực) (d >6-9 cm)', ten)
        self.assertFalse([x for x in ten if t.them_ten_khac(x) != x])               # đủ, không còn dòng thiếu

    def test_du_an_cu_va_ban_may_tu_bo_sung(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'cu.sqlite'
            shutil.copyfile(don_gia.file_goc(), f)
            con = csdl.mo(f)
            try:
                with con, csdl.mo_khoa_danh_muc(con):                         # giả lập bộ / dự án lập trước 26/10/2026
                    for ma, ten in con.execute('SELECT ma, ten FROM dm_taisan WHERE nhom = 3').fetchall():
                        con.execute('UPDATE dm_taisan SET ten = ? WHERE ma = ?', (t.bo_ten_khac(ten), ma))
                gia = dict(con.execute('SELECT ma, don_gia FROM dm_taisan').fetchall())
                n = t.ap_ten_khac(con)
                self.assertGreater(n, 2000)
                self.assertEqual(t.ap_ten_khac(con), 0)
                self.assertEqual(dict(con.execute('SELECT ma, don_gia FROM dm_taisan').fetchall()), gia)
                self.assertTrue(con.execute("SELECT 1 FROM nhat_ky WHERE viec LIKE 'Bổ sung tên khác%'").fetchone())
            finally:
                con.close()

    def test_tim_theo_ten_khac(self):
        from pabt.lap_pa import DanhMuc, bo_dau
        con = csdl.mo(don_gia.file_goc(), chi_doc=True)
        try:
            dm = DanhMuc(con)
        finally:
            con.close()
        tim = [m.ten for m in dm.muc[3] if 'tung huong' in bo_dau(m.ten).lower()]
        self.assertTrue(tim and all(x.startswith('Bách xanh') for x in tim))
        tim = [m.ten for m in dm.muc[3] if 'tram huong' in bo_dau(m.ten).lower()]
        self.assertTrue(tim and all(x.startswith('Dó bầu') for x in tim))

    def test_khop_ten_cu_khi_nhap(self):
        from pabt import nhap_chi_tiet
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'a.sqlite'
            shutil.copyfile(don_gia.file_goc(), f)
            con = csdl.mo(f)
            try:
                khop = nhap_chi_tiet._KhopDanhMuc(con)
                gia = khop.tim(3, 'Bách xanh (Tùng hương) (d >6-9 cm)', None)[0].don_gia
                dung, _ = khop.tim(3, 'Bách xanh (d >6-9 cm)', gia)                 # bản in cũ, không có tên khác
                self.assertIsNotNone(dung)
                self.assertEqual(dung.ten, 'Bách xanh (Tùng hương) (d >6-9 cm)')
            finally:
                con.close()


if __name__ == '__main__':
    unittest.main()
