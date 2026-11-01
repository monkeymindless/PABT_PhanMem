"""Trường hợp biên của pabt/tien.py (đợt rà soát 30/10/2026): làm tròn hiển thị phải giống ROUND của Excel như lam_tron (trước:
vn(x, so_le > 0) làm tròn kiểu ngân hàng - 23.450.000 hiện "23,4 triệu"), số vô cực / NaN từ float không được coi là số, công thức
lồng ngoặc quá sâu báo LoiNhap thay vì RecursionError (hộp lỗi chương trình), đọc tiền bằng chữ đúng cách đọc tiếng Việt."""
from __future__ import annotations

import unittest
from decimal import Decimal

from pabt import tien


class TestLamTronHienThi(unittest.TestCase):
    def test_vn_so_le_lam_tron_xa_so_0_nhu_excel(self):
        for x, le, chu in (('0.25', 1, '0,3'), ('-0.25', 1, '-0,3'), ('2.345', 2, '2,35'), ('2.344', 2, '2,34'),
                           ('143.8', 1, '143,8'), ('1234567.125', 2, '1.234.567,13'), ('0.05', 1, '0,1')):
            self.assertEqual(tien.vn(Decimal(x), le), chu, x)
            self.assertEqual(tien.vn(Decimal(x), le).replace('.', '').replace(',', '.'), str(tien.lam_tron(Decimal(x), le)), x)

    def test_vn_gon_cung_cach_lam_tron(self):
        self.assertEqual(tien.vn_gon(23450000), '23,5 triệu')
        self.assertEqual(tien.vn_gon(185450000000), '185,5 tỷ')
        self.assertEqual(tien.vn_gon(999960000), '1,0 tỷ')                 # lên bậc tỷ sau khi làm tròn (giữ hành vi cũ)
        self.assertEqual(tien.vn_gon(999000), '999.000')

    def test_so_vn_khong_hien_so_0_thua_sau_khi_lam_tron(self):
        self.assertEqual(tien.so_vn(Decimal('1.000005')), '1')            # trước: "1,0000"
        self.assertEqual(tien.so_vn(Decimal('0.123450')), '0,1235')       # trước: "0,1234" (làm tròn kiểu ngân hàng)
        self.assertEqual(tien.so_vn(Decimal('410.6')), '410,6')
        self.assertEqual(tien.so_vn(Decimal('135000')), '135.000')
        self.assertEqual(tien.so_vn(Decimal('-2.50')), '-2,5')

    def test_phan_tram_bien(self):
        self.assertEqual(tien.phan_tram(1, 0), '0%')
        self.assertEqual(tien.phan_tram(49, 60), '81,7%')
        self.assertEqual(tien.phan_tram(1, 2), '50%')
        self.assertEqual(tien.phan_tram(1, 3), '33,3%')


class TestDocSoBien(unittest.TestCase):
    def test_float_vo_cuc_nan_khong_phai_so(self):
        for x in (float('inf'), float('-inf'), float('nan')):
            with self.assertRaises(ValueError, msg=repr(x)):
                tien.D(x)
            self.assertFalse(tien.co_so(x), repr(x))

    def test_chuoi_dac_biet(self):
        for chu in ('nan', 'inf', '-Infinity', '1_000', '1e', 'abc', '1,2,3'):
            with self.assertRaises(ValueError, msg=chu):
                tien.D(chu)
        self.assertEqual(tien.D(' 1.480.500 '), Decimal('1480500'))     # khoảng trắng không ngắt (chép từ Word / web)
        self.assertEqual(tien.D(True), 1)
        self.assertFalse(tien.co_so(''))
        self.assertFalse(tien.co_so(None))
        self.assertTrue(tien.co_so('0'))

    def test_lam_tron_bien(self):
        self.assertEqual(tien.lam_tron(Decimal('-2.5')), -3)                   # nửa: xa số 0 như Excel
        self.assertEqual(tien.lam_tron(Decimal('0.5')), 1)
        self.assertEqual(tien.lam_tron(Decimal('-0.4')), 0)
        self.assertEqual(tien.chuoi(tien.lam_tron(Decimal('-0.4'))), '0')     # không lưu "-0"
        self.assertEqual(tien.lam_tron(Decimal('1.005'), 2), Decimal('1.01'))
        self.assertEqual(tien.lam_tron(Decimal('999999999999.5')), Decimal('1000000000000'))


class TestCongThucBien(unittest.TestCase):
    def test_tinh_dung(self):
        for s, kq in (('=4,2*5,7', '23.94'), ('12x3 + 1,5', '37.5'), ('50%*200', '100'), ('5--3', '8'), ('-(2+3)*2', '-10'),
                      ('10:4', '2.5'), ('(1.000,5+999,5)/2', '1000'), ('12×3', '36'), ('+5', '5')):
            self.assertEqual(tien.tinh_cong_thuc(s), Decimal(kq), s)

    def test_loi_bao_tieng_viet(self):
        for s, chu in (('', 'trống'), ('=', 'trống'), ('4*5+', 'thiếu số'), ('1/0', 'chia cho 0'), ('(1+2', 'thiếu dấu'),
                       ('abc', 'không hợp lệ'), ('2(3)', 'không hợp lệ'), ('1e5', 'không hợp lệ'), ('%5', 'không hợp lệ'),
                       ('1,2,3+1', 'không đọc được số')):
            with self.assertRaises(ValueError, msg=s) as cm:
                tien.tinh_cong_thuc(s)
            self.assertIn(chu, str(cm.exception), s)

    def test_long_ngoac_qua_sau_bao_loi_nhap(self):
        """Dán nhầm chuỗi rất dài vào ô số: trước đây RecursionError lọt ra thành hộp lỗi chương trình."""
        for s in ('(' * 3000 + '1' + ')' * 3000, '-' * 5000 + '1', '+'.join(['1'] * 20000)):
            with self.assertRaises(ValueError, msg=s[:20]):
                tien.tinh_cong_thuc(s)
        self.assertEqual(tien.tinh_cong_thuc('(' * 50 + '2' + ')' * 50), 2)     # lồng vừa phải vẫn tính được

    def test_doc_so_cua_o_nhap_luon_bao_loi_nhap(self):
        from pabt.lap_pa import LoiNhap, doc_so
        for s in ('(' * 3000 + '1' + ')' * 3000, '1/0', 'abc', '=4*'):
            with self.assertRaises(LoiNhap, msg=s[:20]):
                doc_so(s, 'Số lượng')


class TestTienBangChu(unittest.TestCase):
    def test_cach_doc_tieng_viet(self):
        for so, chu in ((0, 'Không đồng'), (5, 'Năm đồng'), (10, 'Mười đồng'), (11, 'Mười một đồng'), (15, 'Mười lăm đồng'),
                        (20, 'Hai mươi đồng'), (21, 'Hai mươi mốt đồng'), (24, 'Hai mươi tư đồng'), (25, 'Hai mươi lăm đồng'),
                        (105, 'Một trăm linh năm đồng'), (110, 'Một trăm mười đồng'), (1005, 'Một nghìn không trăm linh năm đồng'),
                        (1480500, 'Một triệu bốn trăm tám mươi nghìn năm trăm đồng'),
                        (1000005, 'Một triệu không trăm linh năm đồng'), (10 ** 9, 'Một tỷ đồng'),
                        (10 ** 12, 'Một nghìn tỷ đồng'), (10 ** 12 + 10 ** 6, 'Một nghìn tỷ không trăm linh một triệu đồng'),
                        (10 ** 15, 'Một triệu tỷ đồng'), (-1480500, 'Âm một triệu bốn trăm tám mươi nghìn năm trăm đồng'),
                        (Decimal('0.5'), 'Một đồng'), (Decimal('0.4'), 'Không đồng'), ('1.480.500', 'Một triệu bốn trăm tám mươi nghìn năm trăm đồng')):
            self.assertEqual(tien.tien_bang_chu(so), chu, so)

    def test_dau_cham_van_ban_hanh_chinh(self):
        self.assertEqual(tien.tien_bang_chu(0, cham=True), 'Không đồng.')
        self.assertEqual(tien.tien_bang_chu(21, cham=True), 'Hai mươi mốt đồng.')


if __name__ == '__main__':
    unittest.main()
