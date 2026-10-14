"""0.9.29: quyền quản trị sửa bộ đơn giá; trang chủ xóa / thay dự án; đồng bộ quy ước tương đương."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, don_gia, don_gia_rieng as dgr, quan_tri_bo
from pabt.lap_pa import LoiNhap

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class CoSoMay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestQuanTriBo(CoSoMay):
    def test_mat_khau_dat_va_kiem(self):
        self.assertFalse(quan_tri_bo.da_dat())
        self.assertFalse(quan_tri_bo.dung('abcdef'))
        with self.assertRaises(LoiNhap):
            quan_tri_bo.dat('123')                          # ngắn
        quan_tri_bo.dat('abcdef')
        self.assertTrue(quan_tri_bo.da_dat())
        self.assertTrue(quan_tri_bo.dung('abcdef'))
        self.assertFalse(quan_tri_bo.dung('sairoi'))
        with self.assertRaises(LoiNhap):
            quan_tri_bo.dat('ghijkl', cu='sai')
        quan_tri_bo.dat('ghijkl', cu='abcdef')
        self.assertTrue(quan_tri_bo.dung('ghijkl'))
        self.assertFalse(quan_tri_bo.la_quan_tri_may_chu())
        self.assertFalse(quan_tri_bo.bi_chan_may_chu())


class TestSuaBoDonGia(CoSoMay):
    def test_them_sua_xoa_thay(self):
        gt = dict(ma='ZZ99', nhom=2, phan_loai='Thử', ten='Mục thử quản trị', dvt='cái', don_gia='123000', ghi_chu='test')
        kq = don_gia.them_dong('dm_taisan', gt)
        self.assertEqual(kq['ma'], 'ZZ99')
        self.assertEqual(don_gia.doc_dong('dm_taisan', 'ZZ99')['ten'], 'Mục thử quản trị')
        self.assertTrue(Path(don_gia.file_dang_dung()).resolve() == don_gia.file_cap_nhat().resolve())
        don_gia.sua_dong('dm_taisan', 'ZZ99', dict(gt, ten='Mục thử đã sửa', don_gia='150000'))
        self.assertEqual(don_gia.doc_dong('dm_taisan', 'ZZ99')['ten'], 'Mục thử đã sửa')
        don_gia.thay_the_dong('dm_taisan', 'ZZ99', dict(gt, ma='ZZ98', ten='Mục thay'))
        self.assertIsNone(don_gia.doc_dong('dm_taisan', 'ZZ99'))
        self.assertEqual(don_gia.doc_dong('dm_taisan', 'ZZ98')['ten'], 'Mục thay')
        xoa = don_gia.xoa_dong('dm_taisan', 'ZZ98')
        self.assertEqual(xoa['ma'], 'ZZ98')
        self.assertIsNone(don_gia.doc_dong('dm_taisan', 'ZZ98'))
        with self.assertRaises(LoiNhap):
            don_gia.them_dong('dm_taisan', dict(ma='', ten='X', dvt='cái', don_gia='1', nhom=2))
        with self.assertRaises(LoiNhap):
            don_gia.xoa_dong('dm_taisan', 'KHONG_CO')


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestHopVaTrangChu(CoSoMay):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_hop_bo_can_mat_khau_va_them(self):
        from pabt.man_hinh_don_gia import HopBoDonGia
        con = csdl.tao_moi(self.td / 'a.pabt')
        don_gia.ap_vao_du_an(con)
        d = HopBoDonGia(None, con)
        d.im_lang = True
        self.assertFalse(d._da_mo_khoa)
        self.assertIsNone(d.them_muc(gt=dict(ma='ZZ97', ten='A', dvt='cái', don_gia='1', nhom=2, phan_loai='', ghi_chu='')))
        self.assertIsNone(don_gia.doc_dong('dm_taisan', 'ZZ97'))
        kq = d.them_muc(gt=dict(ma='ZZ97', ten='A', dvt='cái', don_gia='1000', nhom=2, phan_loai='', ghi_chu=''),
                        mat_khau='matkhau1')
        self.assertEqual(kq['ma'], 'ZZ97')
        self.assertTrue(d._da_mo_khoa)
        self.assertTrue(any(d.the.widget(0).item(r, 0).text() == 'ZZ97' for r in range(d.the.widget(0).rowCount())))
        con.close()

    def test_quy_uoc_chi_con_o_don_gia_dac_biet(self):
        """0.9.69 (người dùng 12/10/2026: "xóa bỏ toàn bộ phần quy ước, tùy biến trên từng máy, từng dự án"): bộ đơn giá không còn
        thẻ / dòng quy ước gắn sẵn; quy ước riêng của dự án nhập ở Đơn giá đặc biệt (don_gia_rieng) vẫn dùng được."""
        from pabt import lap_pa
        from pabt.man_hinh import ds_chon_nhanh
        from pabt.man_hinh_don_gia import HopBoDonGia
        con = csdl.tao_moi(self.td / 'b.pabt')
        don_gia.ap_vao_du_an(con)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM quy_uoc').fetchone()[0], 0)    # bộ đóng gói: không còn quy ước mẫu
        d = HopBoDonGia(None, con)
        d.im_lang = True
        self.assertNotIn('Quy ước', ' '.join(d.the.tabText(i) for i in range(d.the.count())))
        d.nap_quy_uoc()                                     # không còn thẻ: không làm gì, không lỗi
        m = lap_pa.DanhMuc(con).muc[2][0]
        dgr.luu(con, [dict(id=None, ten_thuc_te='Mái che đặc biệt', ten_tuong_duong=m.ten, dvt=m.dvt, don_gia='123000',
                           can_cu='thử', ghi_chu='')])
        nhan = [x[0] for x in ds_chon_nhanh(lap_pa.DanhMuc(con), 2)]
        self.assertTrue(any('Mái che đặc biệt' in t for t in nhan))
        con.close()

    def test_trang_chu_xoa_va_thay_du_an(self):
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        (self.td / 'mot').mkdir()
        (self.td / 'hai').mkdir()
        p1 = _du_an(self.td / 'mot', 3)
        p2 = _du_an(self.td / 'hai', 2)
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        self.assertIn('Xóa dự án…', w.lenh)
        self.assertIn('Xóa dự án…', [a.text() for a in w.menu_tren['Tệp tin'].actions() if a.text()])
        self.assertIn('Đóng dự án', [a.text() for a in w.menu_tren['Tệp tin'].actions() if a.text()])
        w.mo(str(p1))
        self.assertEqual(w.file.resolve(), Path(p1).resolve())
        w.ve_trang_chu()
        self.assertTrue(w.lenh['Đóng dự án'].isEnabled())
        self.assertTrue(w.lenh['Xóa dự án…'].isEnabled())
        self.assertGreaterEqual(w.ds_gan_day.rowCount(), 1)
        w.mo(str(p2))                                       # thay dự án: không thoát phần mềm
        self.assertEqual(w.file.resolve(), Path(p2).resolve())
        self.assertTrue(Path(p1).exists())
        w.ve_trang_chu()
        w.xoa_du_an(str(p1), xoa_file=False, xac_nhan=True)
        self.assertTrue(Path(p1).exists())
        self.assertNotIn(str(Path(p1).resolve()).lower(), [x.lower() for x in ud.doc_gan_day()])
        w.xoa_du_an(xoa_file=True, xac_nhan=True)           # xóa dự án đang mở
        self.assertFalse(Path(p2).exists())
        self.assertIsNone(w.file)
        self.assertIsNone(w.con)
        w.close()


if __name__ == '__main__':
    unittest.main()
