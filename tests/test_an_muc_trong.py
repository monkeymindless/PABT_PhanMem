"""1.0.57 (người dùng 03/11/2026, ảnh phương án chi tiết): bảng mục III ẩn mục 2 - 6 không có tiền và không có dòng, số mục đánh lại liền
nhau; dòng thưởng in đậm. Số liệu GIẢ LẬP."""
from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace

from pabt import du_lieu_in, in_word, nghiep_vu
from pabt.du_lieu_in import TEN_MUC_DAT, an_muc_trong

T = nghiep_vu.TEN_MUC
VN = nghiep_vu.MUC_VN
O = Decimal(0)


def h(so, ten, tien):
    return ['H', [so, ten, None, None, None, None, tien, None]]


def i(stt, ten, tien, gc=None):
    return ['I', [stt, ten, 'cây', Decimal(1), None, None, tien, gc]]


def dong_mau(nha=(), cay=(), vn=(), ht=(), thuong=O, tien=None):
    tien = tien or {}
    d = [h('1', TEN_MUC_DAT, O), i('1.1', 'Thửa đất số 17, tờ bản đồ số 39', O, 'Đất do UBND xã quản lý')]
    d += [h('2', T[2], tien.get(2, O)), *nha, h('3', T[3], tien.get(3, O)), *cay, h('4', T[VN], tien.get(VN, O)), *vn,
          h('5', T[4], tien.get(4, O)), *ht]
    d += [['R', ['6', T[5], None, None, None, None, thuong, None]], ['T', [None, 'TỔNG CỘNG', None, None, None, None, O, None]]]
    return d


class TestAnMucTrong(unittest.TestCase):
    def test_khong_tien_khong_dong_thi_an_het(self):
        ra = an_muc_trong(dong_mau(), SimpleNamespace())
        self.assertEqual([x[0] for x in ra], ['H', 'I', 'T'])            # như ảnh: chỉ còn mục 1 + TỔNG CỘNG
        self.assertEqual(ra[0][1][1], TEN_MUC_DAT)

    def test_giu_muc_co_dong_khong_gia_va_danh_lai_so(self):
        cay = [i('3.1', 'Tràm', O, 'Tài sản chưa có đơn giá'), i('3.2', 'Xoài', Decimal(500000))]
        ra = an_muc_trong(dong_mau(cay=cay, thuong=Decimal(1000000), tien={3: Decimal(500000)}), None)
        dau = [(x[1][0], x[1][1]) for x in ra if x[0] in ('H', 'R')]
        self.assertEqual(dau, [('1', TEN_MUC_DAT), ('2', T[3]), ('3', T[5])])
        self.assertEqual([x[1][0] for x in ra if x[0] == 'I'], ['1.1', '2.1', '2.2'])   # "3.1" -> "2.1"

    def test_muc_co_tien_khong_dong_van_giu(self):
        ra = an_muc_trong(dong_mau(tien={4: Decimal(2000000)}), None)
        self.assertIn(T[4], [x[1][1] for x in ra if x[0] == 'H'])

    def test_theo_muc_theo_ten_sau_khi_danh_lai(self):
        cay = [i('3.1', 'Tràm', Decimal(100))]
        ra = an_muc_trong(dong_mau(cay=cay, tien={3: Decimal(100)}), None)
        tm = in_word._theo_muc(ra)
        self.assertEqual(len(tm[3]), 1)                                  # mục cây số 2 sau khi đánh lại vẫn nhận đúng mục 3
        self.assertEqual(len(tm[1]), 1)
        self.assertEqual(tm[2], [])

    def test_la_muc_nha_theo_ten(self):
        self.assertTrue(du_lieu_in.la_muc_nha(['2', T[2]]))
        self.assertFalse(du_lieu_in.la_muc_nha(['2', T[3]]))

    def test_thuong_in_dam(self):
        ra = an_muc_trong(dong_mau(thuong=Decimal(1000000)), None)
        chu = in_word._chu_cac_cot(ra, '2')
        self.assertIn((T[5], True), chu[1])                             # tên dòng thưởng đậm
        self.assertIn(('1.000.000', True), chu[6])


if __name__ == '__main__':
    unittest.main()
