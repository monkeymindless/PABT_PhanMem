"""P2 (03/11/2026): bảng tổng hợp - chữ nguồn gốc ghép nhiều thửa trong MỘT đoạn ("1. Thửa 17 … 2. Thửa 16 …") chia đúng cho từng
thửa (trước đây cả đoạn lặp lại ở mọi dòng thửa của hộ). Chữ giả lập."""
from __future__ import annotations

import unittest

from pabt.in_an import doan_theo_thua, nguon_goc_cua_thua, tach_nguon_goc_theo_thua

CHU = 'Nguồn gốc do ông A khai phá năm 1990: 1. Thửa 17 tờ 5 sử dụng đất ở từ năm 1995. 2. Thửa 16 tờ 5 trồng cây lâu năm.'


class TestNguonGocNhieuThua(unittest.TestCase):
    def test_tach_muc_danh_so(self):
        self.assertEqual(doan_theo_thua(CHU), ['Nguồn gốc do ông A khai phá năm 1990:',
                                               '1. Thửa 17 tờ 5 sử dụng đất ở từ năm 1995.', '2. Thửa 16 tờ 5 trồng cây lâu năm.'])

    def test_moi_thua_mot_phan(self):
        kq = tach_nguon_goc_theo_thua([(CHU, '17', '5'), (CHU, '16', '5')])
        self.assertIn('Thửa 17', kq[0])
        self.assertNotIn('Thửa 16', kq[0])
        self.assertIn('Thửa 16', kq[1])
        self.assertTrue(all(x.startswith('Nguồn gốc do ông A') for x in kq))     # câu chung đứng đầu mỗi thửa
        self.assertEqual(nguon_goc_cua_thua(CHU, '16'), kq[1])

    def test_sau_dau_cham_va_gach_dau_dong(self):
        self.assertEqual(doan_theo_thua('Đất khai hoang. Thửa đất số 16 tờ 3 trồng lúa; - Thửa 18 làm nhà ở'),
                         ['Đất khai hoang.', 'Thửa đất số 16 tờ 3 trồng lúa;', '- Thửa 18 làm nhà ở'])

    def test_giu_nguyen_khi_thua_nhac_giua_cau(self):
        c = 'Thửa 16 và thửa 17 cùng nguồn gốc nhận chuyển nhượng năm 2001.'
        self.assertEqual(doan_theo_thua(c), [c])
        self.assertIsNone(tach_nguon_goc_theo_thua([(c, '16', '1'), (c, '17', '1'), (c, '18', '1')]))   # thửa 18 không có đoạn riêng

    def test_mot_thua_mot_doan_nhu_cu(self):
        c = 'Sử dụng ổn định từ năm 1980, không tranh chấp.\nThửa 5 tờ 2 trồng cây.'
        self.assertEqual(doan_theo_thua(c), ['Sử dụng ổn định từ năm 1980, không tranh chấp.', 'Thửa 5 tờ 2 trồng cây.'])


if __name__ == '__main__':
    unittest.main()
