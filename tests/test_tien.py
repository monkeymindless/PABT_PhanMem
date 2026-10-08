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
        """Số lượng mục 2-4: luôn ít nhất 1 chữ số thập phân; số nhiều chữ số lẻ hơn hiện đủ (khớp thành tiền)."""
        from pabt.tien import so_luong_vn
        for v, chu in (('20', '20,0'), ('79.8', '79,8'), ('1250', '1.250,0'), ('35.15', '35,15'), ('0', '0,0'), ('1.23456', '1,2346')):
            self.assertEqual(so_luong_vn(Decimal(v)), chu, v)


if __name__ == '__main__':
    unittest.main()
