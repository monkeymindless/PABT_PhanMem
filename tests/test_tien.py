from __future__ import annotations

import unittest
from decimal import Decimal

from pabt.tien import D, lam_tron, vn, chuoi


class TestTien(unittest.TestCase):
    def test_doc_so(self):
        self.assertEqual(D('1.480.500'), Decimal('1480500'))
        self.assertEqual(D('143,8'), Decimal('143.8'))
        self.assertEqual(D(143.8), Decimal('143.8'))
        self.assertEqual(D(None), 0)
        self.assertEqual(D(''), 0)
        self.assertEqual(D('1,234.5'), Decimal('1234.5'))

    def test_doc_so_nguoi_go(self):
        """Một quy tắc đọc số gõ / ô chữ trong file cho mọi chỗ nhập liệu (tien.doc_so_vn)."""
        from pabt.tien import doc_so_vn
        for chu, so in (('1.070', '1070'), ('2.500.000', '2500000'), ('1.070,5', '1070.5'), ('12,5', '12.5'), ('0.125', '0.125'),
                        ('12.5', '12.5'), ('1,500,000', '1500000'), ('1,500', '1.5'), ('-1.000', '-1000'), (' 4 320 000 ', '4320000'),
                        ('1,234.5', '1234.5'), (1070.5, '1070.5'), (None, '0')):
            self.assertEqual(doc_so_vn(chu), Decimal(so), repr(chu))
        with self.assertRaises(ValueError):
            doc_so_vn('1,2,3')
        self.assertEqual(D('1.07'), Decimal('1.07'))                   # D: chuỗi lưu trong CSDL (tien.chuoi) không đổi

    def test_cac_cho_nhap_cung_quy_tac(self):
        """Trước đây '1.070' ô diện tích Excel -> 1,07 m²; '1.070,5' số tiền quyết định -> 10.705; '0.500' -> 500."""
        from pabt import cay_trong, lap_pa, nhap_excel, nhap_tho, theo_doi
        from pabt.tien import tinh_cong_thuc
        self.assertEqual(nhap_tho._doc_dt('1.070'), 1070)
        self.assertEqual(nhap_tho._doc_dt('1.070,5 m2'), Decimal('1070.5'))
        self.assertEqual(nhap_excel._so('1.070'), '1070')
        self.assertIsNone(nhap_excel._so_hoac_rong('abc'))
        self.assertEqual(theo_doi._tien('1.070,5'), '1070.5')
        self.assertEqual(theo_doi._tien('1,500,000'), '1500000')
        self.assertEqual(lap_pa.doc_so('0.500', 'x'), Decimal('0.5'))
        self.assertEqual(tinh_cong_thuc('0.125*8'), 1)
        self.assertEqual(tinh_cong_thuc('1,500,000:2'), 750000)
        self.assertEqual(cay_trong.mat_do_tu_danh_muc('', 'Mật độ 1.111 cây/ha'), 1111)

    def test_lam_tron_nhu_excel(self):
        self.assertEqual(lam_tron(Decimal('2188800'), -3), 2189000)       # 3,8 m³ x 576.000
        self.assertEqual(lam_tron(Decimal('29894784'), -3), 29895000)     # 12 cây x 2.491.232
        self.assertEqual(lam_tron(Decimal('1500'), -3), 2000)             # nửa: làm tròn lên (xa số 0)
        self.assertEqual(lam_tron(Decimal('-1500'), -3), -2000)
        self.assertEqual(lam_tron(Decimal('1499.99'), -3), 1000)
        self.assertEqual(lam_tron(Decimal('456932.58'), 0), 456933)

    def test_dinh_dang(self):
        self.assertEqual(vn(812506000), '812.506.000')
        self.assertEqual(vn(Decimal('143.8'), 1), '143,8')
        self.assertEqual(chuoi(Decimal('1E+3')), '1000')

    def test_so_luong_kieu_ke_toan(self):
        """Số lượng kiểu kế toán (15/10/2026): tài sản (mục 2) *,00; đất, cây, hỗ trợ, khác *,0; số nhiều chữ số lẻ hơn hiện đủ (tối đa 4)."""
        from pabt.tien import dinh_dang_so_luong, so_luong_vn
        for v, chu in (('20', '20,00'), ('79.8', '79,80'), ('1250', '1.250,00'), ('35.15', '35,15'), ('0', '0,00'), ('1.23456', '1,2346'),
                        ('35.155', '35,155')):
            self.assertEqual(so_luong_vn(Decimal(v), 2), chu, v)
        for muc in (None, 1, 3, 4, 5, 7):
            for v, chu in (('16', '16,0'), ('1453', '1.453,0'), ('35.8', '35,8'), ('0', '0,0'), ('0.0325', '0,0325')):
                self.assertEqual(so_luong_vn(Decimal(v), muc), chu, (muc, v))
            self.assertEqual(dinh_dang_so_luong(muc), '#,##0.0###')
        self.assertEqual(dinh_dang_so_luong(2), '#,##0.00##')


if __name__ == '__main__':
    unittest.main()
