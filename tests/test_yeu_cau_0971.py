"""0.9.71 (người dùng 12/10/2026): ô Khối lượng riêng ở hàng nhập tài sản (cây theo đường kính / chu vi: số đo + số cây mỗi số
đo), Enter trên nút "Thêm vào bảng" / "Thêm đất vào mục 1" (và Enter ở ô Loại đất sang ô Diện tích). Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QApplication

from pabt import cay_trong as ct
from pabt.lap_pa import LoiNhap


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)
        from pabt.man_hinh_du_toan import KhungDuToan
        self.k = KhungDuToan()
        self.k.im_lang = True
        self.addCleanup(self.k.close)
        self.k.show()
        self.app.processEvents()
        self.h = self.k.hang
        self.loai = next(iter(ct.BangCayDK(self.k.dm.muc[3]).loai))     # một loại cây có quy cách theo số đo thân


class TestKhoiLuong(_Co):
    def test_o_so_do_va_khoi_luong(self):
        h = self.h
        self.assertFalse(h.o_do.isVisible())                            # kiểu Số lượng: chỉ ô Khối lượng
        self.assertIn('Khối lượng', h.o_sl.placeholderText())
        self.k.cb_muc_nhap.setCurrentIndex(self.k.cb_muc_nhap.findData(3))     # ô Mục của thanh nhập nhanh (bố cục 0.9.71)
        self.app.processEvents()
        self.assertEqual(h.muc(), 3)
        h.cb_kieu.setCurrentIndex(h.cb_kieu.findData('dk'))
        self.app.processEvents()
        self.assertTrue(h.o_do.isVisible() and h.o_sl.isVisible())      # số đo + số cây
        h.o_do.setText('23')
        h.o_sl.setText('100')
        v = h.gia_tri()
        self.assertEqual((v['so_do'], v['so_luong'], v['kieu']), ('23', '100', 'dk'))
        r = self.k.them_nhanh(m=('nhom', self.loai))
        self.assertGreaterEqual(r, 0)
        self.assertEqual(sum(int(d.khoi_luong) for d in self.k.dt.dong), 100)  # 100 cây đường kính 23 cm
        self.assertEqual(h.o_do.text(), '')                             # thêm xong: xóa ô
        # nhiều số đo, mỗi số đo 2 cây; số cây không nguyên -> báo lỗi, không thêm
        n = len(self.k.dt.dong)
        with mock.patch.object(self.k, 'bao') as bao:
            self.assertIsNone(self.k.them_nhanh(m=('nhom', self.loai), so_do='23', so_luong='1,5'))
        self.assertIn('nguyên', bao.call_args[0][0])
        self.assertEqual(len(self.k.dt.dong), n)
        self.k.cb_muc_nhap.setCurrentIndex(self.k.cb_muc_nhap.findData(2))     # đổi mục: ô số đo ẩn lại
        self.app.processEvents()
        self.assertFalse(h.o_do.isVisible())

    def test_cach_goi_cu_van_dung(self):
        """Gọi kiểu cũ (số đo trong so_luong, không có so_do) - hộp Dán danh sách, mã cũ."""
        from pabt.nhap_tai_san import them_mot
        i, tb, _ = them_mot(self.k._dich(), 3, ('nhom', self.loai), '', '23, 23x2', '', 'dk')
        self.assertIn('3 cây', tb)
        with self.assertRaises(LoiNhap):
            them_mot(self.k._dich(), 3, ('nhom', self.loai), '', '0', '', 'dk', '', '23')


class TestPhimEnter(_Co):
    def test_enter_tren_nut(self):
        """Khái toán: MỘT nút Thêm vào bảng cho đất (ô Mục = 1. Đất) và tài sản; hàng nhập của phương án hộ giữ nút riêng."""
        dem = []
        self.k.them_nhanh = lambda **_: dem.append('ts')
        self.k.them_dat = lambda *a, **_: dem.append('dat')
        self.assertTrue(self.h.nut_them.autoDefault())                  # nút của hàng (thẻ mục phương án hộ)
        b = self.k.b_them
        self.assertTrue(b.autoDefault())
        for muc in (1, 2):
            self.k.cb_muc_nhap.setCurrentIndex(self.k.cb_muc_nhap.findData(muc))
            b.setFocus()
            self.app.processEvents()
            QTest.keyClick(b, Qt.Key.Key_Return)
        self.assertEqual(dem, ['dat', 'ts'])
        self.k.cb_muc_nhap.setCurrentIndex(0)
        self.k.cb_loai_dat.setFocus()                                    # Enter ở Loại đất: sang ô Diện tích
        QTest.keyClick(self.k.cb_loai_dat.lineEdit(), Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertTrue(self.k.o_dt_dat.hasFocus())



class TestBoCucKhaiToan(_Co):
    """Bố cục theo bo_cuc_khai_toan.txt (người dùng 12/10/2026)."""

    def test_che_do_kinh_phi_tao_moi(self):
        k = self.k
        self.assertFalse(k.tab.tabBar().isVisible())                    # 2 chế độ chọn bằng menu trái, không phải thanh thẻ
        self.assertFalse(hasattr(k, 'rd_so_sanh'))                      # 15/10/2026: bỏ nút Chế độ (trùng menu trái)
        self.assertFalse(any(x.text().startswith('KHÁI TOÁN KINH PHÍ') for x in k.findChildren(QLabel)))
        # Kinh phí QĐ08: chọn loại -> dòng chi phí mục 6 theo mức của loại; lưu cùng .pabtdt
        k.them_dat('CLN', '1000', '100000')
        k.cb_kp.setCurrentIndex(k.cb_kp.findData('tuyen'))
        k._doi_kinh_phi()
        cp = [d for d in k.dt.dong if d.muc == 6]
        self.assertEqual(str(cp[0].phan_tram), '3.5')
        f = k.luu(self.td / 'kt.pabtdt')
        from pabt.du_toan import DuToan
        self.assertEqual(DuToan.mo(f).loai_kinh_phi, 'tuyen')
        self.assertIn('TỔNG CỘNG KHÁI TOÁN', k.lb_tong.text())
        self.assertIn('Bằng chữ', k.lb_tong.text())
        k.tao_moi()
        self.assertEqual((k.dt.dong, k.o_ten.text(), k.cb_kp.currentData()), ([], '', ''))
        # thanh nhập nhanh: Đất -> ô loại đất + Tra NQ 28; mục khác -> hàng nhập tài sản dùng chung với phương án hộ
        k.cb_muc_nhap.setCurrentIndex(k.cb_muc_nhap.findData(1))
        self.assertIs(k.ngan_nhap.currentWidget().isAncestorOf(k.cb_loai_dat), True)
        self.assertTrue(k.b_tra_nq28.isVisibleTo(k))
        k.cb_muc_nhap.setCurrentIndex(k.cb_muc_nhap.findData(2))
        self.assertIs(k.ngan_nhap.currentWidget(), k.hang)
        self.assertFalse(k.b_tra_nq28.isVisibleTo(k))
        self.assertFalse(k.hang.cb_muc.isVisibleTo(k) or k.hang.nut_them.isVisibleTo(k))

    def test_ctrl_s_tren_trang_khai_toan(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        k = w.du_toan(cho=False)
        self.app.processEvents()
        with mock.patch.object(k, 'luu', return_value=self.td / 'x.pabtdt') as luu:
            self.assertTrue(w.luu_du_an_lenh())                         # chưa mở dự án .pabt: vẫn lưu được khái toán
        luu.assert_called_once()


class TestThanhMotHang(_Co):
    """Người dùng 13/10/2026 (ảnh image_5edb1e.png): "Dán danh sách…" + "Thêm vào bảng" cùng hàng với các ô nhập; ô Khối lượng 90,
    Tỷ lệ 60, Ghi chú 120-180; ô hàng 2 thông tin chuẩn bị đầu tư không cắt chữ. Màn hình hẹp: nút xuống dòng, KHÔNG ép cửa sổ
    rộng hơn màn hình (lỗi phóng to 0.9.26)."""

    def test_mot_hang_va_tu_xuong_dong(self):
        k, h = self.k, self.h
        self.assertEqual(k.b_dan.text(), 'Dán danh sách…')
        self.assertEqual((h.o_sl.minimumWidth(), h.o_sl.maximumWidth(), h.o_tl.minimumWidth(), h.o_tl.maximumWidth()),
                         (90, 90, 60, 60))
        self.assertEqual((h.o_gc.minimumWidth(), h.o_gc.maximumWidth()), (120, 180))
        self.assertEqual((k.o_quy_mo.minimumWidth(), k.o_so_thua.minimumWidth(), k.o_so_ho.minimumWidth()), (130, 75, 75))
        k.cb_muc_nhap.setCurrentIndex(k.cb_muc_nhap.findData(3))
        for du, mot in ((60, True), (-60, False)):
            k.resize(k.can_mot_hang() + 2 * 10 + du, 600)              # 10 = lề trái / phải của trang
            for _ in range(4):
                self.app.processEvents()
            self.assertEqual(k._h_d1.indexOf(k.khoi_nut_nhap) >= 0, mot, du)
            if mot:                                                     # cùng hàng với ô Ghi chú
                y = k.khoi_nut_nhap.mapTo(k, k.khoi_nut_nhap.rect().center()).y()
                y_gc = h.o_gc.mapTo(k, h.o_gc.rect().center()).y()
                self.assertLess(abs(y - y_gc), 6)
        # thanh nhập nhanh không làm trang (và cửa sổ chính) rộng ra theo hàng nút
        self.assertLess(k.minimumSizeHint().width(), k.can_mot_hang())


if __name__ == '__main__':
    unittest.main()
