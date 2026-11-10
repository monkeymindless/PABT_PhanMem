"""1.0.79 (người dùng 07/11/2026, Nghị quyết 28 Điều 5, 6, Phụ lục VIII): Vị trí 1 / 2, Phạm vi, trần sàn; nhãn ngưỡng theo địa bàn. Số trong ví dụ lấy từ văn bản."""
from __future__ import annotations

import os
import unittest
from decimal import Decimal as Dc

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pabt  # noqa: E402,F401
from pabt import gia_dat_qd03 as g  # noqa: E402

NN, O = ('DAT_NONG_NGHIEP', 'nn_cay'), ('DAT_O', 'dat_o')


def tinh(gia, nhom, ma, dia_ban='Xã Phú Lý', doan=None):
    return g.tinh_don_gia(g.DauVao(dia_ban=dia_ban, nhom_dat=nhom[0], cot_gia=nhom[1], don_gia_bang_gia=Dc(gia), ma_vi_tri_dat=ma, he_so_k1=Dc(1)), doan)


class TestGoi(unittest.TestCase):
    def test_du_muc(self):
        self.assertEqual([x['ma'] for x in g.muc_vi_tri_dat()], ['VT1_PV1', 'VT1_PV2', 'VT1_PV3', 'VT2_PV1', 'VT2_PV2'])

    def test_phu_luc_viii(self):
        self.assertEqual(g.gioi_han_nong_nghiep('Xã Phú Lý', 'nn_cay'), (35000, 60000))
        self.assertEqual(g.gioi_han_nong_nghiep('Phú Lý', 'nn_rung_nts'), (25000, 50000))
        self.assertEqual(g.gioi_han_nong_nghiep('Xã Không Có', 'nn_cay'), (None, None))

    def test_phu_luc_viii_tach_loai_dat(self):
        self.assertEqual(g.gioi_han_nong_nghiep('Phường Bình Phước', 'nn_cay', loai='cln')[0], 240000)
        self.assertEqual(g.gioi_han_nong_nghiep('Phường Bình Phước', 'nn_cay', loai='hang_nam')[0], 170000)
        self.assertIsNone(g.gioi_han_nong_nghiep('Phường Bình Phước', 'nn_rung_nts', loai='rung')[0])   # ô trống trong văn bản
        self.assertEqual([m for m, _ in g.loai_nn_can_chon('Phường Bình Phước', 'nn_cay')], ['cln', 'hang_nam'])
        self.assertEqual(g.loai_nn_can_chon('Xã Phú Lý', 'nn_cay'), [])


class TestTinh(unittest.TestCase):
    def test_khong_chon_va_100_giu_nguyen_khong_them_chu(self):
        a, b = tinh(1200000, O, ''), tinh(1200000, O, 'VT1_PV1')
        self.assertEqual(a.don_gia_da_lam_tron, b.don_gia_da_lam_tron)
        self.assertEqual(a.buoc_lap_luan, b.buoc_lap_luan)
        self.assertIsNone(b.gia_truoc_vi_tri)

    def test_vi_tri_1_pham_vi(self):
        self.assertEqual(tinh(1200000, O, 'VT1_PV2').don_gia_nq28, 960000)
        self.assertEqual(tinh(1200000, O, 'VT1_PV3').don_gia_nq28, 720000)
        self.assertEqual(tinh(230000, NN, 'VT1_PV2').don_gia_nq28, 184000)
        self.assertEqual(tinh(230000, NN, 'VT1_PV3').don_gia_nq28, 138000)

    def test_vi_du_trong_nghi_quyet_khong_doan_duong(self):
        kq = tinh(2000000, O, 'VT2_PV1')                # đường giá 2 triệu: 15% = 0,3 triệu (Điều 6)
        self.assertEqual(kq.don_gia_nq28, 300000)
        self.assertEqual(kq.gia_truoc_vi_tri, 2000000)
        self.assertTrue(any('sàn' in c or 'cây lâu năm' in c for c in kq.canh_bao))      # không có đoạn đường: báo chưa áp sàn
        self.assertEqual(tinh(2000000, O, 'VT2_PV2').don_gia_nq28, 200000)

    def test_vi_tri_2_nong_nghiep_tran_san(self):
        self.assertEqual(tinh(230000, NN, 'VT2_PV1').don_gia_nq28, 60000)   # 30% = 69.000 vượt trần 60.000
        self.assertEqual(tinh(100000, NN, 'VT2_PV1').don_gia_nq28, 35000)   # 30% = 30.000 dưới sàn 35.000
        self.assertEqual(tinh(150000, NN, 'VT2_PV1').don_gia_nq28, 45000)

    def test_vi_tri_1_nong_nghiep_chi_san_khong_tran(self):
        self.assertEqual(tinh(1000000, NN, 'VT1_PV3').don_gia_nq28, 600000)
        self.assertEqual(tinh(40000, NN, 'VT1_PV3').don_gia_nq28, 35000)

    def test_xa_khong_co_trong_phu_luc_bao(self):
        kq = tinh(230000, NN, 'VT2_PV1', 'Xã Không Có')
        self.assertEqual(kq.don_gia_nq28, 69000)
        self.assertTrue(any('Phụ lục VIII' in c for c in kq.canh_bao))

    def test_giai_trinh_co_can_cu(self):
        kq = tinh(230000, NN, 'VT2_PV1')
        self.assertTrue(any('Điều 5' in x and '30%' in x and 'tối đa' in x for x in kq.buoc_lap_luan))
        self.assertIn('Vị trí 2', g.ghi_chu_ap_gia(kq))

    def test_vi_du_phu_ly_tran_60000_co_dien_giai(self):
        # 1.0.80 (người dùng hỏi vì sao 60.000): Điều 5 khoản 1 điểm b: 30% x 230.000 = 69.000 vượt tối đa Xã Phú Lý 60.000 (Phụ lục VIII), rồi mới nhân K
        kq = tinh(230000, NN, 'VT2_PV1')
        self.assertEqual(kq.don_gia_nq28, 60000)
        self.assertEqual(kq.gia_truoc_vi_tri, 230000)
        self.assertEqual(kq.dien_giai_vi_tri, '230.000 × 30% = 69.000 đ/m², vượt giá tối đa của Xã Phú Lý nên lấy 60.000 đ/m² (Phụ lục VIII)')
        self.assertIn('69.000', g.ghi_chu_ap_gia(kq))
        k = g.tinh_don_gia(g.DauVao(dia_ban='Xã Phú Lý', nhom_dat=NN[0], cot_gia=NN[1], don_gia_bang_gia=Dc(230000), ma_vi_tri_dat='VT2_PV1', he_so_k1=Dc('1.45')), None)
        self.assertEqual(k.don_gia_ap_dung, 87000)                   # bảng giá x hệ số (Điều 3 khoản 2 QĐ 03): 60.000 x 1,45

    def test_vi_tri_1_pham_vi_1_khong_co_dien_giai(self):
        self.assertEqual(tinh(230000, NN, 'VT1_PV1').dien_giai_vi_tri, '')
        self.assertEqual(tinh(230000, NN, '').dien_giai_vi_tri, '')

    def test_dien_giai_khi_duoi_san_va_trong_khoang(self):
        self.assertIn('thấp hơn giá tối thiểu của Xã Phú Lý nên lấy 35.000', tinh(100000, NN, 'VT2_PV1').dien_giai_vi_tri)
        self.assertEqual(tinh(150000, NN, 'VT2_PV1').dien_giai_vi_tri, '150.000 × 30% = 45.000 đ/m²')

    def test_goi_khong_khai_bao_thi_nhu_cu(self):
        goi = dict(g._goi(None))
        goi.pop('vi_tri_dat')
        self.assertEqual(g.muc_vi_tri_dat(goi), [])
        kq = g.tinh_don_gia(g.DauVao(nhom_dat='DAT_O', cot_gia='dat_o', don_gia_bang_gia=Dc(1000), ma_vi_tri_dat='VT2_PV1', he_so_k1=Dc(1)), None, goi)
        self.assertEqual(kq.don_gia_nq28, 1000)


class TestNhanNguong(unittest.TestCase):
    def _x(self, vt):
        return next(x for x in g._goi(None)['vi_tri'] if x.get('vi_tri') == vt)

    def _doan(self, xa, cu_the=None):
        from pabt import gia_dat_nq28 as nq
        r = next(r for r in nq.tat_ca() if cu_the(r))
        return dict(tt_bat_dau=r['tt'], ten_duong=r['ten_duong']), r['xa']

    def test_nhan_theo_nguong(self):
        d, xa = self._doan('', lambda r: r.get('nguong') == [600, 400] and r.get('vi_tri') == 'MT')
        n = g.nhan_vi_tri(self._x('T1'), d, xa)
        self.assertIn('≤600m', n)
        self.assertIn('≤400m', n)
        self.assertNotIn('1000', n)
        self.assertIn('400-600m', g.nhan_vi_tri(self._x('T2'), d, xa))
        self.assertIn('≤600m', g.nhan_vi_tri(self._x('K1'), d, xa))     # dòng không đấu nối nêu đủ điều kiện

    def test_nhan_xa_giu_1000_500(self):
        d, xa = self._doan('', lambda r: r.get('nguong') == [1000, 500] and r.get('vi_tri') == 'MT')
        self.assertIn('≤1000m', g.nhan_vi_tri(self._x('T1'), d, xa))
        self.assertEqual(g.nhan_vi_tri(self._x('T1'), None), self._x('T1')['ten'])


class TestManHinh(unittest.TestCase):
    def test_chon_vi_tri_2_khoa_dong_1(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        h = HopTinhGiaDat(im_lang=True) if 'im_lang' in HopTinhGiaDat.__init__.__code__.co_varnames else HopTinhGiaDat()
        self.addCleanup(h.deleteLater)
        h.cb_vi_tri.setCurrentIndex(2)
        h.cb_vt_dat.setCurrentIndex(h.cb_vt_dat.findData('VT2_PV1'))
        self.assertEqual(h.cb_vi_tri.currentIndex(), 0)
        self.assertFalse(h.cb_vi_tri.isEnabled())
        self.assertEqual(h.dau_vao().ma_vi_tri_dat, 'VT2_PV1')
        self.assertIn('Vị trí: ', h.lb_ct.text())                # phép tính hiện ngay trên màn hình
        h.cb_vt_dat.setCurrentIndex(0)
        self.assertTrue(h.cb_vi_tri.isEnabled())


if __name__ == '__main__':
    unittest.main()
