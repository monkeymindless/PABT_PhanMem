"""Mật độ nhiều loại cây trên cùng diện tích (người dùng 30/10/2026): cây đơn giá cao tính trước làm cây trồng chính, diện tích còn dư
tính tiếp cho cây đơn giá thấp hơn; phần vượt mật độ tách thành dòng riêng. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from pabt import cay_trong as ct, csdl
from pabt.tien import D
from tests.test_toc_do import _du_an


def _dong(ten, so, md, gia):
    return ct.DongMatDo(ten, so, D(md) if md is not None else None, D(gia))


class TestPhanBo(unittest.TestCase):
    def test_vi_du_xoai_quyt(self):
        # 1.000 m²: xoài (giá cao) 200 cây/ha = 50 m²/cây -> tối đa 20 cây, dùng hết diện tích; quýt không còn chỗ
        xoai, quyt = _dong('Xoài', 200, 200, 500000), _dong('Quýt', 100, 400, 200000)
        con = ct.phan_bo_mat_do([quyt, xoai], 1000)          # thứ tự nhập không quan trọng: xếp theo đơn giá
        self.assertEqual((xoai.thu_tu, xoai.trong, xoai.ngoai), (1, 20, 180))
        self.assertEqual((quyt.thu_tu, quyt.trong, quyt.ngoai), (2, 0, 100))
        self.assertEqual(con, 0)

    def test_con_du_tinh_tiep_cay_thu_hai(self):
        xoai, quyt = _dong('Xoài', 10, 200, 500000), _dong('Quýt', 100, 400, 200000)
        con = ct.phan_bo_mat_do([xoai, quyt], 1000)
        self.assertEqual((xoai.trong, xoai.ngoai, xoai.dt_dung), (10, 0, 500))     # 10 cây x 50 m²
        self.assertEqual((quyt.trong, quyt.ngoai), (20, 80))                     # 500 m² x 400 / 10.000 = 20 cây
        self.assertEqual(quyt.dt_dung, 500)
        self.assertEqual(con, 0)

    def test_ba_loai_va_khong_mat_do(self):
        a, b, c = _dong('A', 5, 100, 900), _dong('B', 3, 200, 800), _dong('C', 7, None, 1000)
        ct.phan_bo_mat_do([a, b, c], 1000)
        self.assertEqual((a.thu_tu, a.trong, a.ngoai), (1, 5, 0))          # dùng 500 m²
        self.assertEqual((b.thu_tu, b.trong, b.ngoai), (2, 3, 0))          # dùng 150 m², còn 350
        self.assertEqual((c.thu_tu, c.trong, c.ngoai), (0, 7, 0))          # chưa có mật độ: giữ nguyên, không chiếm diện tích
        self.assertEqual(b.dt_con, 350)

    def test_mot_loai_giong_tach_mat_do(self):
        for so, dt, md in ((30, 1000, 210), (10, 1000, 210), (300, 1000, 200), (5, 3, 200), (1500, 1000, 1111)):
            x = _dong('X', so, md, 1)
            ct.phan_bo_mat_do([x], dt)
            self.assertEqual((x.trong, x.ngoai), ct.tach_mat_do(so, dt, md), (so, dt, md))

    def test_bang_gia_giu_thu_tu_va_phan_so(self):
        a, b = _dong('A', 50, 1111, 100), _dong('B', 200, 1111, 100)
        ct.phan_bo_mat_do([a, b], 1000)                     # 1.000 m² x 1.111 / 10.000 = 111,1 -> 111 cây cả hai loài
        self.assertEqual((a.thu_tu, b.thu_tu), (1, 2))
        self.assertEqual((a.trong, b.trong, b.ngoai), (50, 61, 139))


class TestCayXen(unittest.TestCase):
    def test_gioi_han_nua_gia_tri_cay_chinh(self):
        chinh = _dong('Gòn', 10, 200, 100000)
        ct.phan_bo_mat_do([chinh], 1000)
        self.assertEqual(ct.gia_tri_cay([chinh]), 1000000)
        a, b = _dong('A', 5, None, 300000), _dong('B', 10, None, 100000)
        con = ct.phan_bo_cay_xen([b, a], ct.gia_tri_cay([chinh]) * ct.HE_SO_CAY_XEN)   # tối đa 500.000 đ, đơn giá cao trước
        self.assertEqual((a.thu_tu, a.trong, a.ngoai), (1, 1, 4))                     # 300.000 đ, còn 200.000 đ
        self.assertEqual((b.thu_tu, b.trong, b.ngoai), (2, 2, 8))
        self.assertEqual(con, 0)

    def test_ty_le_va_gia_0(self):
        a = ct.DongMatDo('A', 10, None, D(100000), D('0.8'))                            # 80 000 đ / cây
        b = _dong('B', 7, None, 0)
        ct.phan_bo_cay_xen([a, b], 250000)
        self.assertEqual((a.trong, a.ngoai, a.dt_dung), (3, 7, 240000))
        self.assertEqual((b.trong, b.ngoai), (7, 0))


class TestTrenPhuongAn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)
        self.con = csdl.mo(_du_an(self.td, so_ho=2))
        self.addCleanup(self.con.close)
        ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        from pabt.man_hinh import CuaSoLapPA
        self.w = w = CuaSoLapPA(self.con, ma)
        self.addCleanup(w.close)
        self.addCleanup(w.bo_thay_doi)
        # hai loài cây có mật độ trong danh mục, đơn giá khác nhau
        ds, loai = [], set()
        for m in sorted(w.bo.dm.muc[3], key=lambda m: -(m.don_gia or 0)):
            g = ct.ten_goc(m.ten)
            if (m.dvt or '').strip() == 'cây' and m.don_gia and g not in loai and ct.mat_do_tu_danh_muc(m.ten, m.can_cu):
                ds.append(m)
                loai.add(g)
            if len(ds) == 2:
                break
        self.assertEqual(len(ds), 2)
        w.bo.pa.khoan[3].clear()
        self.cao, self.thap = ds
        # dòng giá thấp nhập trước: vẫn tính sau dòng giá cao
        self.i_thap, _ = w.bo.them_tu_danh_muc(3, self.thap)
        self.i_cao, _ = w.bo.them_tu_danh_muc(3, self.cao)
        self.md_cao = ct.mat_do_tu_danh_muc(self.cao.ten, self.cao.can_cu)
        self.md_thap = ct.mat_do_tu_danh_muc(self.thap.ten, self.thap.can_cu)

    def _so(self, i, so):
        self.w.bo.sua_khoan(3, i, 'so_luong', str(so))

    def test_tach_dong_vuot_va_tinh_lai(self):
        w = self.w
        dt = 1000
        toi_da_cao = int(D(dt) * self.md_cao / 10000)
        so_cao = max(toi_da_cao // 2, 1)
        self._so(self.i_cao, so_cao)
        self._so(self.i_thap, 100000)
        dlg = w.tinh_mat_do(cho=False)
        dlg.im_lang = True
        dlg.o_dt.setText(str(dt))
        dlg.o_tl.setText('0')
        self.assertEqual(dlg.bang.item(0, 1).text(), self.cao.ten)          # bảng xếp theo đơn giá: giá cao đầu tiên
        trong, ngoai, so_dong = dlg.ap_dung()
        con_lai = Decimal(dt) - Decimal(so_cao) * Decimal(10000) / self.md_cao
        trong_thap = int(con_lai * self.md_thap / 10000)
        self.assertEqual((trong, ngoai, so_dong), (so_cao + trong_thap, 100000 - trong_thap, 1))
        ds = w.bo.pa.khoan[3]
        self.assertEqual([d.ten for d in ds], [self.thap.ten, self.thap.ten, self.cao.ten])
        self.assertEqual((ds[0].so_luong, ds[1].so_luong, ds[2].so_luong), (trong_thap, 100000 - trong_thap, so_cao))
        self.assertTrue(ds[0].quy_cach.startswith('Trong mật độ (') and 'ưu tiên 2' in ds[0].quy_cach)
        self.assertTrue(ds[1].quy_cach.startswith('Ngoài mật độ ('))
        self.assertEqual(ds[1].ty_le, 0)
        self.assertIn('vượt mật độ', ds[1].ghi_chu)
        # tính lại (đổi diện tích): dòng vượt cũ gộp lại, không cộng dồn
        dlg = w.tinh_mat_do(cho=False)
        dlg.im_lang = True
        self.assertEqual(sorted(g.dong.so_cay for g in dlg.nhom), sorted([so_cao, 100000]))
        dlg.o_dt.setText('100000000')
        self.assertEqual(dlg.ap_dung()[1:], (0, 0))
        self.assertEqual([d.so_luong for d in w.bo.pa.khoan[3]], [100000, so_cao])
        self.assertEqual(w.bo.pa.khoan[3][0].ty_le, 1)
        self.assertEqual(w.bo.pa.khoan[3][0].ghi_chu, '')

    def test_ca_dong_vuot_giu_ty_le_goc(self):
        w = self.w
        self._so(self.i_cao, 100000)
        self._so(self.i_thap, 10)
        w.bo.sua_khoan(3, self.i_thap, 'ty_le', '80')
        dlg = w.tinh_mat_do(cho=False)
        dlg.im_lang = True
        dlg.o_dt.setText('1000')
        dlg.ap_dung()
        d = w.bo.pa.khoan[3][self.i_thap]
        self.assertEqual((d.so_luong, d.ty_le), (10, 0))                    # cây giá cao dùng hết diện tích
        self.assertIn('tỷ lệ gốc 80%', d.quy_cach)
        dlg = w.tinh_mat_do(cho=False)
        dlg.im_lang = True
        dlg.o_dt.setText('100000000')
        dlg.ap_dung()
        d = w.bo.pa.khoan[3][self.i_thap]
        self.assertEqual((d.so_luong, d.ty_le), (10, D('0.8')))             # đủ diện tích: trả lại tỷ lệ gốc

    def test_cay_trong_xen(self):
        w = self.w
        dt = 1000
        so_cao = max(int(D(dt) * self.md_cao / 10000) // 2, 1)
        self._so(self.i_cao, so_cao)
        self._so(self.i_thap, 100000)
        dlg = w.tinh_mat_do(cho=False)
        dlg.im_lang = True
        dlg.o_dt.setText(str(dt))
        dlg.dat_xen(self.thap.ten)
        dlg.ap_dung()
        gia_chinh = so_cao * D(self.cao.don_gia)
        so_xen = int(gia_chinh * D('0.5') / D(self.thap.don_gia))
        ds = w.bo.pa.khoan[3]
        self.assertEqual([d.so_luong for d in ds], [so_xen, 100000 - so_xen, so_cao])
        self.assertTrue(ds[0].quy_cach.startswith('Cây trồng xen ('))
        self.assertIn('không vượt quá 0,5 lần giá trị cây trồng chính', ds[0].ghi_chu)
        self.assertTrue(ds[1].quy_cach.startswith('Cây xen vượt 0,5 lần ('))
        self.assertEqual(ds[1].ty_le, 0)
        self.assertIn('vượt quá 0,5 lần giá trị cây trồng chính, không tính toán', ds[1].ghi_chu)
        self.assertTrue(ds[2].quy_cach.startswith('Trong mật độ ('))
        # tính lại: vai trò cây xen giữ, dòng vượt gộp lại
        dlg = w.tinh_mat_do(cho=False)
        g = next(g for g in dlg.nhom if g.dong.ten == self.thap.ten)
        self.assertEqual((g.xen, g.dong.so_cay), (True, 100000))
        dlg.dat_xen(self.thap.ten, False)                                    # bỏ cây xen: thành cây trồng chính, xét mật độ
        dlg.o_dt.setText('100000000')
        dlg.ap_dung()
        self.assertEqual([d.so_luong for d in w.bo.pa.khoan[3]], [100000, so_cao])
        self.assertEqual(w.bo.pa.khoan[3][0].ghi_chu, '')

    def test_canh_bao_khi_nhap(self):
        w = self.w
        self._so(self.i_cao, 1)
        w.sua_o(3, self.i_thap, 'so_luong', '100000')
        self.assertIn('vượt mật độ', w.lb_tb.text())
        self.assertIn('ưu tiên 2', w.lb_tb.text())


if __name__ == '__main__':
    unittest.main()
