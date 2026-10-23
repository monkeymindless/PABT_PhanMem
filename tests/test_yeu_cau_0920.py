"""0.9.20: kinh phí tổ chức thực hiện theo QĐ 08/2025/QĐ-UBND (theo tuyến 3,5%, cụm / vùng 2,5%), lấy mẫu in từ file một sheet /
mẫu riêng, chọn nhóm hộ đưa vào đợt trình."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an, lap_pa, quan_ly
from pabt.lap_pa import BoSoan, LoiNhap
from pabt.tien import D
from tests.test_toc_do import _du_an

MAU = Path(__file__).resolve().parents[1] / 'mau_in'


class TestKinhPhi(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.con = csdl.mo(_du_an(Path(self.td.name), 4))

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_loai_theo_ten(self):
        for ten, loai in (('Xây dựng đường số 9 đoạn qua xã Trị An', 'tuyen'), ('Nạo vét kênh tiêu', 'tuyen'),
                          ('Đường dây 110kV', 'tuyen'), ('Khu tái định cư đường ĐT768', 'khac'),
                          ('Cụm công nghiệp Thạnh Phú', 'khac'), ('Xây dựng khu dân cư', 'khac'), ('Trường tiểu học', 'khac')):
            self.assertEqual(lap_pa.loai_kinh_phi_tu_ten(ten), loai, ten)

    def test_luu_va_gioi_han(self):
        self.con.execute("UPDATE du_an SET ten = 'Xây dựng đường số 9' WHERE id = 1")
        self.con.commit()
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con), ('tuyen', D('3.5'), True))
        lap_pa.luu_kinh_phi_to_chuc(self.con, 'khac', '')
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con), ('khac', D('2.5'), False))
        with self.assertRaises(LoiNhap):                                  # không quá mức tối đa của loại
            lap_pa.luu_kinh_phi_to_chuc(self.con, 'khac', '3')
        lap_pa.luu_kinh_phi_to_chuc(self.con, 'tuyen', '3,2')
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con)[1], D('3.2'))

    def test_bang_tong_hop_theo_ty_le(self):
        self.con.execute("UPDATE du_an SET ten = 'Xây dựng đường số 9' WHERE id = 1")
        self.con.commit()
        p = in_an.lap_bang_tong_hop(self.con, Path(self.td.name) / 'bth.xlsx')
        ws = openpyxl.load_workbook(p).worksheets[0]
        chu = [str(c.value) for r in ws.iter_rows() for c in r if isinstance(c.value, str) and 'Kinh phí đảm bảo' in c.value]
        # 16/10/2026 (người dùng): dòng kinh phí không ghi "(theo Quyết định số 08/2025/QĐ-UBND …)"
        self.assertTrue(chu and '3,5%' in chu[0] and '08/2025/QĐ-UBND' not in chu[0], chu)
        cong_thuc = [c.value for r in ws.iter_rows() for c in r if isinstance(c.value, str) and c.value.startswith('=ROUND(')]
        self.assertTrue(any('*3.5%' in x for x in cong_thuc), cong_thuc)


class TestNhomHoDot(unittest.TestCase):
    def test_nhom(self):
        td = tempfile.TemporaryDirectory()
        con = csdl.mo(_du_an(Path(td.name), 6))
        try:
            ma = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
            with con:                                                     # tự lập lúc tạo dự án: lưu từ hôm trước
                con.execute("UPDATE ho SET luu_luc = '2026-01-01T08:00:00'")
            BoSoan(con, ma[1]).luu()                                      # hộ 2: người dùng mở soát và lưu hôm nay
            self.assertEqual(quan_ly.ho_theo_nhom(con, 'chua_xep'), ma)
            self.assertEqual(quan_ly.ho_theo_nhom(con, 'da_lap'), [ma[1]])
            self.assertEqual(quan_ly.ho_theo_nhom(con, 'gan_nhat'), [ma[1]])
            d1 = quan_ly.tao_dot(con, 'Đợt 1')
            quan_ly.gan_dot(con, ma[:2], d1)
            self.assertEqual(quan_ly.ho_theo_nhom(con, 'chua_xep'), ma[2:])
            d2 = quan_ly.tao_dot(con, 'Đợt 2')
            self.assertEqual(quan_ly.ho_theo_nhom(con, 'chua_duyet', d2), ma[:2])    # đợt 1 chưa phê duyệt: trình lại
            self.assertEqual(quan_ly.ho_theo_nhom(con, 'chua_duyet', d1), [])
        finally:
            con.close()
            td.cleanup()


if __name__ == '__main__':
    unittest.main()
