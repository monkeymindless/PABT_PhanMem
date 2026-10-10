"""0.9.20: kinh phí tổ chức thực hiện theo QĐ 08/2025/QĐ-UBND (theo tuyến 3,5%, cụm / vùng 2,5%), lấy mẫu in từ file một sheet /
mẫu riêng, chọn nhóm hộ đưa vào đợt trình."""
from __future__ import annotations
import shutil
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
        for ten, loai in (('Xây dựng đường ĐT762 đoạn qua xã Trị An', 'tuyen'), ('Nạo vét kênh tiêu', 'tuyen'),
                          ('Đường dây 110kV', 'tuyen'), ('Khu tái định cư đường ĐT768', 'khac'),
                          ('Cụm công nghiệp Thạnh Phú', 'khac'), ('Xây dựng khu dân cư', 'khac'), ('Trường tiểu học', 'khac')):
            self.assertEqual(lap_pa.loai_kinh_phi_tu_ten(ten), loai, ten)

    def test_luu_va_gioi_han(self):
        self.con.execute("UPDATE du_an SET ten = 'Xây dựng đường ĐT762' WHERE id = 1")
        self.con.commit()
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con), ('tuyen', D('3.5'), True))
        lap_pa.luu_kinh_phi_to_chuc(self.con, 'khac', '')
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con), ('khac', D('2.5'), False))
        with self.assertRaises(LoiNhap):                                  # không quá mức tối đa của loại
            lap_pa.luu_kinh_phi_to_chuc(self.con, 'khac', '3')
        lap_pa.luu_kinh_phi_to_chuc(self.con, 'tuyen', '3,2')
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con)[1], D('3.2'))

    def test_bang_tong_hop_theo_ty_le(self):
        self.con.execute("UPDATE du_an SET ten = 'Xây dựng đường ĐT762' WHERE id = 1")
        self.con.commit()
        p = in_an.lap_bang_tong_hop(self.con, Path(self.td.name) / 'bth.xlsx')
        ws = openpyxl.load_workbook(p).worksheets[0]
        chu = [str(c.value) for r in ws.iter_rows() for c in r if isinstance(c.value, str) and 'Kinh phí đảm bảo' in c.value]
        self.assertTrue(chu and '3,5%' in chu[0] and '08/2025/QĐ-UBND' in chu[0], chu)
        cong_thuc = [c.value for r in ws.iter_rows() for c in r if isinstance(c.value, str) and c.value.startswith('=ROUND(')]
        self.assertTrue(any('*3.5%' in x for x in cong_thuc), cong_thuc)


class TestMauIn(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        for f in MAU.glob('IN_*.xlsx'):
            if '_' not in f.stem[3:]:                                     # IN_CHITIET / IN_BANGTONGHOP (mẫu chính)
                shutil.copy2(f, self.d / f.name)

    def tearDown(self):
        self.td.cleanup()

    def test_file_chi_mot_sheet(self):
        # trước đây: "File Excel không có sheet IN_BANGTONGHOP" khi file chỉ có mẫu chi tiết
        tao = in_an.tao_mau_tu_excel(MAU / 'IN_CHITIET.xlsx', self.d / 'ra')
        self.assertEqual([p.name for p in tao if p.suffix == '.xlsx'], ['IN_CHITIET.xlsx'])
        tao = in_an.tao_mau_tu_excel(MAU / 'IN_BANGTONGHOP.xlsx', self.d / 'ra')
        self.assertEqual([p.name for p in tao if p.suffix == '.xlsx'], ['IN_BANGTONGHOP.xlsx'])
        in_an.tao_mau_tu_excel(MAU / 'IN_CHITIET.xlsx', self.d / 'ra')                  # thay lần 2: mẫu cũ chép vào cu\
        self.assertEqual(len(list((self.d / 'ra' / 'cu').glob('IN_CHITIET_*.xlsx'))), 1)

    def test_mau_rieng_ten_sheet_khac_va_chon_khi_in(self):
        wb = openpyxl.load_workbook(MAU / 'IN_CHITIET.xlsx')
        wb.worksheets[0].title = 'Du thao'
        wb.worksheets[0]['A3'] = 'Số:      /{ky_hieu_so}\n(DỰ THẢO)'
        f = self.d / 'mau_du_thao.xlsx'
        wb.save(f)
        tao = in_an.tao_mau_tu_excel(f, self.d, ten_mau='Dự thảo')
        rieng = self.d / 'IN_CHITIET__Dự thảo.xlsx'
        self.assertIn(rieng, tao)
        self.assertEqual(openpyxl.load_workbook(rieng).sheetnames, ['IN_CHITIET'])
        con_td = tempfile.TemporaryDirectory()
        con = csdl.mo(_du_an(Path(con_td.name), 3))
        try:
            from unittest import mock
            with mock.patch.object(in_an, 'thu_muc_mau', return_value=self.d), \
                    mock.patch.object(in_an, 'thu_muc_mau_ghi', return_value=self.d):
                ds = in_an.ds_mau(in_an.TEN_CT)
                self.assertEqual([t for t, _ in ds], ['Mẫu chính', 'Dự thảo'])
                ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
                p = in_an.lap_chi_tiet(con, ma, self.d / 'ra.xlsx', ds[1][1])
            self.assertIn('DỰ THẢO', str(openpyxl.load_workbook(p).worksheets[0]['A3'].value))
        finally:
            con.close()
            con_td.cleanup()

    def test_khong_nhan_ra_thi_hoi(self):
        wb = openpyxl.Workbook()                                          # mẫu đã sửa nhưng có dấu hiệu của cả hai loại
        wb.active['A1'] = 'BẢNG TỔNG HỢP {du_an}'
        wb.active['A2'] = 'Họ và tên: {ho_ten}'
        f = self.d / 'la.xlsx'
        wb.save(f)
        with self.assertRaises(in_an.LoiChuaRoMau):
            in_an.tao_mau_tu_excel(f, self.d / 'ra')
        tao = in_an.tao_mau_tu_excel(f, self.d / 'ra', loai=in_an.TEN_BTH)
        self.assertEqual(tao[0].name, 'IN_BANGTONGHOP.xlsx')


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
