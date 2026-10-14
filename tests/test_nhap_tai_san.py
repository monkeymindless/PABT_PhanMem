"""0.9.67 (người dùng 12/10/2026): MỘT bộ công cụ nhập tài sản cho lập phương án hộ và Dự toán & khái toán - cùng hàng nhập nhanh
(hang_nhap_nhanh.HangNhapNhanh), cùng lệnh thêm (nhap_tai_san.them_mot / them_dong_tho), cùng hộp "Dán danh sách tài sản".
Cùng một thao tác nhập trên hai đích ra cùng tên, số lượng, đơn giá, tỷ lệ, ghi chú."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tests.test_toc_do import _du_an


class CoSo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        from pabt import csdl
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 3))
        self.addCleanup(self.con.close)

    def _hai_dich(self):
        from pabt import lap_pa
        from pabt.du_toan import DuToan
        from pabt.nhap_tai_san import DichDuToan, DichPhuongAn
        ma = self.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        bo = lap_pa.BoSoan(self.con, ma)
        dt = DuToan()
        return bo, dt, DichPhuongAn(bo), DichDuToan(dt, bo.dm)


class TestCungMotLenh(CoSo):
    def test_danh_muc_cong_thuc_ty_le_ghi_chu(self):
        from pabt.nhap_tai_san import them_mot
        from pabt.tien import D
        bo, dt, pa, du = self._hai_dich()
        m = bo.dm.muc[2][0]
        i, _, tu_do = them_mot(pa, 2, m, '', '=4,2*5,7', '80', 'sl', 'Điều 14')
        j, _, tu_do2 = them_mot(du, 2, m, '', '=4,2*5,7', '80', 'sl', 'Điều 14')
        self.assertFalse(tu_do or tu_do2)
        k, d = bo.pa.khoan[2][i], dt.dong[j]
        self.assertEqual((k.ten, k.dvt, k.so_luong, k.don_gia, k.ty_le, k.ghi_chu),
                         (d.ten, d.dvt, d.khoi_luong, d.don_gia, d.he_so, d.ghi_chu))
        self.assertEqual(d.khoi_luong, D('23.9'))                     # =4,2*5,7 = 23,94 -> 1 chữ số như phương án

    def test_ten_tu_do_va_loi_tieng_viet(self):
        from pabt.lap_pa import LoiNhap
        from pabt.nhap_tai_san import them_mot
        bo, dt, pa, du = self._hai_dich()
        for dich in (pa, du):
            with self.assertRaises(LoiNhap):
                them_mot(dich, 2, None, '', '5')                        # chưa chọn / chưa gõ tên
            with self.assertRaises(LoiNhap):
                them_mot(dich, 2, bo.dm.muc[2][0], '', 'abc')           # số lượng sai: không thêm dòng
        self.assertEqual(len(dt.dong), 0)
        i, tb, tu_do = them_mot(du, 3, None, 'Cây kiểng đặc biệt', '2')
        self.assertTrue(tu_do)
        self.assertIn('không có trong đơn giá', tb)
        self.assertEqual((dt.dong[i].muc, dt.dong[i].ten, dt.dong[i].khoi_luong), (3, 'Cây kiểng đặc biệt', 2))

    def test_vat_nuoi_gop_muc_3_du_toan(self):
        from pabt.nghiep_vu import MUC_VN
        from pabt.nhap_tai_san import them_mot
        bo, dt, pa, du = self._hai_dich()
        if not bo.dm.muc[MUC_VN]:
            self.skipTest('danh mục chưa có vật nuôi')
        i, _, _ = them_mot(du, MUC_VN, bo.dm.muc[MUC_VN][0], '', '3')
        self.assertEqual(dt.dong[i].muc, 3)                             # dự toán: vật nuôi gộp mục 3 (du_toan.muc_du_toan)

    def test_cay_theo_duong_kinh_hai_dich_nhu_nhau(self):
        from pabt import cay_trong as ct
        from pabt.nhap_tai_san import them_mot
        bo, dt, pa, du = self._hai_dich()
        bang = ct.BangCayDK(bo.dm.muc[3])
        ten = next(iter(bang.loai), None)
        if ten is None:
            self.skipTest('danh mục không có cây theo đường kính')
        khoang = bang.loai[ten][0][0]
        do = khoang.den if khoang.den is not None else (khoang.tu or 0) + 1
        them_mot(pa, 3, ('nhom', ten), '', f'{do}x2', '', 'dk')
        them_mot(du, 3, ('nhom', ten), '', f'{do}x2', '', 'dk')
        self.assertEqual([(k.ten, k.so_luong) for k in bo.pa.khoan[3]], [(d.ten, d.khoi_luong) for d in dt.dong])
        self.assertEqual(sum(d.khoi_luong for d in dt.dong), 2)


class TestManHinhDungChung(CoSo):
    def test_cung_mot_hang_nhap_va_hop_dan(self):
        from pabt import app as ud
        from pabt.hang_nhap_nhanh import HangNhapNhanh
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        p = self.con.execute('PRAGMA database_list').fetchone()[2]
        self.con.close()
        w.mo(p)
        lp = w.mo_lap_pa(cho=False)
        self.addCleanup(lp.bo_thay_doi)
        dt = w.du_toan(cho=False)
        self.assertIsInstance(lp.bang[2].hang, HangNhapNhanh)
        self.assertIsInstance(dt.hang, HangNhapNhanh)
        self.assertIs(type(lp.bang[2].hang), type(dt.hang))
        self.assertFalse(hasattr(dt, 'b_hm'))                           # "Thêm hạng mục" (hộp chọn riêng): bỏ
        self.assertEqual([dt.hang.cb_muc.itemText(i) for i in range(dt.hang.cb_muc.count())],
                         ['Nhà, công trình', 'Cây trồng', 'Vật nuôi', 'Hỗ trợ', 'Thưởng'])
        # hàng nhập nhanh của dự toán: chọn mục nhà đầu tiên, số lượng công thức
        m = dt.dm.muc[2][0]
        r = dt.them_nhanh(muc=2, m=m, ten='', so_luong='=2*3', ty_le='', kieu='sl', ghi_chu='')
        self.assertGreaterEqual(r, 0)
        self.assertEqual((dt.dt.dong[r].ten, dt.dt.dong[r].khoi_luong), (m.ten, 6))
        # cùng hộp "Dán danh sách tài sản"
        n0 = len(dt.dt.dong)
        hop = dt.dan_tai_san('Nhà cấp 4 mái tôn\tm2\t45\nGà ta\tcon\t40', cho=False)
        self.addCleanup(hop.deleteLater)
        hop.im_lang = True
        self.assertEqual(len(hop.phan_loai()), 2)
        self.assertEqual(hop.them(), 2)
        self.assertEqual(len(dt.dt.dong), n0 + 2)
        self.assertIn('2 dòng', dt.lb_tb.text())
        # thưởng: không danh mục - gõ tên
        dt.hang.cb_muc.setCurrentIndex(4)
        self.app.processEvents()
        r = dt.them_nhanh(m=None, ten='Thưởng bàn giao mặt bằng', so_luong='1')
        self.assertEqual(dt.dt.dong[r].muc, 5)


if __name__ == '__main__':
    unittest.main()
