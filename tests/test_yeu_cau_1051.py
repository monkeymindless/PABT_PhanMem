"""1.0.51 (người dùng 02/11/2026): LƯU TỰ ĐỘNG 10 giây / 1 phút / 2 phút / Tắt ở cửa sổ lập phương án và Khái toán - không hộp thoại,
không dựng lại bảng (giữ ô đang chọn), lùi lại khi đang gõ dở trong ô bảng. Dữ liệu GIẢ LẬP (tests.test_toc_do._du_an)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import chu_de, csdl  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class _Co(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self._env = os.environ.pop('PABT_TU_LUU', None)
        chu_de._chu_ky_phien = None
        chu_de._chu_ky_nho = None

    def tearDown(self):
        chu_de._chu_ky_phien = None
        chu_de._chu_ky_nho = None
        if self._env is not None:
            os.environ['PABT_TU_LUU'] = self._env
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.doCleanups()
        self.tmp.cleanup()


class TestChuKy(_Co):
    def test_doc_ghi_chu_ky(self):
        self.assertEqual(chu_de.chu_ky_luu_tu_dong(), 0)                   # offscreen, chưa đặt: tắt (kiểm thử không tự ghi)
        self.assertEqual(chu_de.dat_chu_ky_luu_tu_dong(60), 60)
        self.assertEqual(chu_de.chu_ky_luu_tu_dong(), 60)
        self.assertEqual(chu_de.dat_chu_ky_luu_tu_dong(7), chu_de.CHU_KY_LUU_MAC_DINH)   # số lạ -> mặc định 30 giây
        os.environ['PABT_TU_LUU'] = '120'
        try:
            self.assertEqual(chu_de.chu_ky_luu_tu_dong(), 120)
        finally:
            os.environ.pop('PABT_TU_LUU')
        self.assertEqual([g for g, _ in chu_de.CAC_MUC_LUU_TU_DONG], [10, 30, 60, 120, 0])

    def test_qsettings(self):
        class _CaiDat(dict):
            def value(self, k, md=None):
                return self.get(k, md)

            def setValue(self, k, v):
                self[k] = v
        cd = _CaiDat()
        self.assertEqual(chu_de.chu_ky_luu_tu_dong(cd), 30)                 # mặc định 30 giây
        chu_de.dat_chu_ky_luu_tu_dong(0, cd)
        self.assertEqual(chu_de.chu_ky_luu_tu_dong(cd), 0)


class TestLapPA(_Co):
    def setUp(self):
        super().setUp()
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 4))
        self.addCleanup(self.con.close)
        self.ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1 OFFSET 2').fetchone()[0]
        from pabt import man_hinh
        self.mh = man_hinh
        chu_de.dat_chu_ky_luu_tu_dong(10)
        self.w = man_hinh.CuaSoLapPA(self.con, self.ma)
        self.w.show()

        def dong():
            self.w.bo_thay_doi()
            self.w.close()
            self.w.deleteLater()
        self.addCleanup(dong)

    def _so_dong_csdl(self) -> int:
        return self.con.execute('SELECT COUNT(*) FROM ct_dat WHERE ma_ho = ?', (self.ma,)).fetchone()[0]

    def test_tu_luu_khong_dung_lai_bang(self):
        w = self.w
        self.assertEqual(w.cb_tu_luu.currentText(), '10 giây')
        b = w.bang[1]
        n = self._so_dong_csdl()
        self.assertGreaterEqual(n, 2)
        b._bam_o(1, b.c_xoa)                                                  # xóa một dòng đất (chưa lưu)
        self.assertTrue(w.bo.co_thay_doi)
        self.assertTrue(w._hen_luu_tu_dong.isActive())
        self.assertLessEqual(w._hen_luu_tu_dong.remainingTime(), 10000)
        self.assertIn('Chưa lưu', w.lb_trang_thai_luu.text())
        o_truoc = b.bang.item(0, 1)
        b.bang.setCurrentCell(0, 2)
        with mock.patch.object(self.mh.QMessageBox, 'warning', side_effect=AssertionError('hộp thoại')), \
                mock.patch.object(w, 'nap_ho', side_effect=AssertionError('dựng lại bảng')):
            w._thuc_hien_luu_tu_dong()
        self.assertEqual(self._so_dong_csdl(), n - 1)                          # đã ghi CSDL
        self.assertFalse(w.bo.co_thay_doi)
        self.assertIs(b.bang.item(0, 1), o_truoc)                              # không dựng lại bảng
        self.assertEqual((b.bang.currentRow(), b.bang.currentColumn()), (0, 2))
        self.assertIn('Đã tự lưu', w.lb_trang_thai_luu.text())
        self.assertTrue(str(w.bo.pa.ho.trang_thai).startswith(self.mh.DA_LAP_LUU))
        b._bam_o(0, b.c_xoa)                                                  # sửa tiếp sau khi tự lưu: lưu tiếp đúng
        w._thuc_hien_luu_tu_dong()
        self.assertEqual(self._so_dong_csdl(), n - 2)

    def test_lui_khi_dang_sua_o(self):
        w = self.w
        b = w.bang[1]
        n = self._so_dong_csdl()
        b._bam_o(1, b.c_xoa)
        with mock.patch.object(w, '_dang_sua_o_bang', return_value=True):
            w._thuc_hien_luu_tu_dong()
        self.assertEqual(self._so_dong_csdl(), n)                              # chưa ghi
        self.assertTrue(w._hen_luu_tu_dong.isActive())
        self.assertLessEqual(w._hen_luu_tu_dong.remainingTime(), 2000)         # lùi 2 giây
        from PySide6.QtWidgets import QAbstractItemView
        with mock.patch.object(type(b.bang), 'state', return_value=QAbstractItemView.State.EditingState):
            self.assertTrue(w._dang_sua_o_bang())

    def test_tat_va_loi_nhap_im_lang(self):
        w = self.w
        w.cb_tu_luu.setCurrentIndex(w.cb_tu_luu.findData(0))
        w._doi_chu_ky_tu_luu()
        self.assertEqual(chu_de.chu_ky_luu_tu_dong(), 0)
        b = w.bang[1]
        b._bam_o(1, b.c_xoa)
        self.assertFalse(w._hen_luu_tu_dong.isActive())                        # tắt: không hẹn
        from pabt.lap_pa import LoiNhap
        with mock.patch.object(w.bo, 'luu_tai_cho', side_effect=LoiNhap('Diện tích âm')), \
                mock.patch.object(self.mh.QMessageBox, 'warning', side_effect=AssertionError('hộp thoại')):
            self.assertFalse(w.luu(tu_dong=True))
        self.assertIn('Tự lưu tạm hoãn', w.lb_tb.text())

    def test_ho_so_tu_luu_im_lang(self):
        w = self.w
        o = w.ho_so.o['ho_ten']
        o.setText('')                                                           # họ tên trống: hồ sơ không hợp lệ
        if not w.ho_so.co_thay_doi():
            self.skipTest('hồ sơ giả lập không đổi khi xóa họ tên')
        with mock.patch.object(self.mh.QMessageBox, 'warning', side_effect=AssertionError('hộp thoại')), \
                mock.patch('pabt.man_hinh_ho_so.QMessageBox.warning', side_effect=AssertionError('hộp thoại')):
            ok = w.luu(tu_dong=True)
        if not ok:
            self.assertIn('Tự lưu tạm hoãn', w.lb_tb.text())


class TestKhaiToan(_Co):
    def test_tu_luu_file_du_toan(self):
        from pabt.man_hinh_du_toan import KhungDuToan
        from pabt.du_toan import DongDT
        chu_de.dat_chu_ky_luu_tu_dong(10)
        k = KhungDuToan()
        self.addCleanup(k.deleteLater)
        k.show()
        f = Path(self.tmp.name) / 'kt.pabtdt'
        self.assertFalse(k._thuc_hien_luu_tu_dong())                           # chưa có file: không tự lưu
        k.luu(str(f))
        truoc = f.read_text(encoding='utf-8')
        self.assertFalse(k._thuc_hien_luu_tu_dong())                           # không đổi: không ghi
        k.dt.dong.append(DongDT(muc=2, ten='Nhà tạm', dvt='m²', khoi_luong='10', don_gia='1000'))
        self.assertTrue(k._thuc_hien_luu_tu_dong())
        self.assertNotEqual(f.read_text(encoding='utf-8'), truoc)
        self.assertIn('Nhà tạm', f.read_text(encoding='utf-8'))
        self.assertIn('Đã tự lưu', k.lb_tb.text())


class TestAnDanh(unittest.TestCase):
    def test_che_du_lieu_ca_nhan_khong_che_so_tien(self):
        from pabt import tro_ly
        s = tro_ly.an_danh('Chủ hộ: Nguyễn Văn An, CCCD: 075 092 123 456, ĐT 0912.345.678')
        self.assertEqual(s, 'Chủ hộ: [HO_TEN], CCCD: [CCCD], ĐT [SĐT]')
        self.assertEqual(tro_ly.an_danh('Nhà cấp 4: 120.000.000 đồng, 45 m2'), 'Nhà cấp 4: 120.000.000 đồng, 45 m2')
        self.assertEqual(tro_ly.an_danh('bà con nhân dân đồng ý'), 'bà con nhân dân đồng ý')
        self.assertEqual(tro_ly.an_danh('Ông Trần Văn Bình ở ấp 3'), 'Ông [HO_TEN] ở ấp 3')
        self.assertEqual(tro_ly.an_danh('GCN CS 123456; 10.95123, 106.81234; X: 1234567.12'), 'GCN [SO_GCN]; [TOA_DO]; [TOA_DO]')
        self.assertEqual(tro_ly.an_danh('Mã CT5511 tràm 1500 cây'), 'Mã CT5511 tràm 1500 cây')

    def test_ma_phien_wifi_16_ky_tu(self):
        from pabt import nhan_wifi
        with tempfile.TemporaryDirectory() as td:
            m = nhan_wifi.MayNhan('127.0.0.1', thu_muc=Path(td))
            self.assertGreaterEqual(len(m.ma), 16)
            self.assertTrue(m.ma.isalnum())


class TestGiaoDien(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])

    def test_mau_tong_toi(self):
        from pabt import bang_ao, giao_dien
        cu = giao_dien.TONG_NEN[0]
        try:
            giao_dien.TONG_NEN[0] = 'toi'
            self.assertEqual(bang_ao._but_so_tien().color().name().upper(), '#93C5FD')     # không còn navy trên nền tối
            self.assertEqual(giao_dien.mau_theo_tong(giao_dien.MAU_TRANG_THAI['tin'][0], 'chu').upper(), '#7DD3FC')
            self.assertNotEqual(giao_dien.mau_chu_nut('in').upper(), giao_dien.MAU['in'][0].upper())
            giao_dien.TONG_NEN[0] = 'sang'
            self.assertEqual(bang_ao._but_so_tien().color().name().upper(), giao_dien.mau_theo_tong(giao_dien.MAU_SO_TIEN, 'chu').upper())     # 1.0.79: theo phương án Navy
        finally:
            giao_dien.TONG_NEN[0] = cu

    def test_vong_tieu_diem_va_vien_xoa(self):
        from pabt import giao_dien
        self.assertIn('QPushButton:focus', giao_dien._qss_day_du())
        self.assertNotEqual(giao_dien.NUT_XOA[2].upper(), '#FECACA')

    def test_danh_sach_goi_y_lat_len_khi_gan_day(self):
        from PySide6.QtWidgets import QLineEdit
        from pabt import giao_dien
        o = QLineEdit()
        o.resize(200, 24)
        vung = o.screen().availableGeometry()
        o.move(vung.left() + 10, vung.bottom() - 40)
        o.show()
        try:
            x, (y, cao) = giao_dien.vi_tri_danh_sach_noi(o, 640, 400)
            self.assertLessEqual(y + cao, vung.bottom() + 1)               # không tràn đáy màn hình
            self.assertLess(y, o.mapToGlobal(o.rect().topLeft()).y())      # lật lên trên ô
        finally:
            o.close()
            o.deleteLater()


if __name__ == '__main__':
    unittest.main()
