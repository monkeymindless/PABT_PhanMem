"""0.9.80 (người dùng 13/10/2026): màn hình chào - bỏ "● Máy đơn" trên banner, trạng thái trống của bảng dự án gần đây, cụm nút thao tác
trên đầu bảng, làm mờ nhóm 4 / 5 / 6 của menu trái khi chưa mở dự án, chân trang 4 liên kết, tên đơn vị vàng kim, khung nút A− / A+."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_toc_do import _du_an

NHOM_MO = ('Lập phương án hộ…', 'Dự thảo PABT…', 'Kiểm tra lỗi…', 'Xuất báo cáo đối chiếu…', 'Tổng hợp tiền theo phương án',
           'Đợt trình…', 'In / Xuất…', 'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Báo cáo tổng hợp…')
NHOM_SANG = ('Màn hình chính', 'Thông tin dự án…', 'Bộ đơn giá…', 'Đơn giá riêng dự án…', 'Bảng giá đất NQ 28…', 'Dự toán & khái toán')


class CoSo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from pabt import app as ud
        from pabt import giao_dien
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        giao_dien.ap_dung(self.app)
        self.ud = ud
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(self.w.close)


class TestBannerVaThanhTrangThai(CoSo):
    def test_bo_may_don_tren_banner_giu_o_nut_tk(self):
        from PySide6.QtWidgets import QLabel
        from pabt import giao_dien
        b = self.w.banner_ten
        self.assertFalse(hasattr(b, 'lb_lan'))
        self.assertFalse(hasattr(self.w, 'lb_lan_nho'))
        chu = ' '.join(x.text() for x in b.findChildren(QLabel)) + ' ' + ' '.join(
            x.text() for x in b.goc_phai.findChildren(__import__('PySide6.QtWidgets', fromlist=['QPushButton']).QPushButton))
        self.assertNotIn('Máy đơn', chu)
        self.assertIn('Phiên bản', chu)
        self.assertIn('Chưa mở dự án', chu)
        self.assertIn('Máy đơn', self.w.nut_tk.text())                 # trạng thái kết nối: DUY NHẤT ở thanh trạng thái
        self.assertFalse(hasattr(giao_dien, 'dat_den_lan'))
        self.assertIn('#FCD34D', b.lb_don_vi.styleSheet())              # tên đơn vị: vàng kim nhạt trên nền navy

    def test_ap_dung_goi_lai_khong_chong_bo_loc(self):
        """Gọi ap_dung nhiều lần (mỗi setUp) không cài thêm bộ lọc sự kiện / không đặt lại bảng kiểu - trước 0.9.80 bộ lọc chồng N
        lớp làm bộ test chậm bậc hai tới mức tưởng treo."""
        from pabt import giao_dien
        bo = self.app._bo_to_mau
        qss = self.app.styleSheet()
        with mock.patch.object(self.app, 'installEventFilter') as cai, mock.patch.object(self.app, 'setStyleSheet') as dat:
            giao_dien.ap_dung(self.app)
            giao_dien.ap_dung(self.app)
        cai.assert_not_called()
        dat.assert_not_called()
        self.assertIs(self.app._bo_to_mau, bo)
        self.assertEqual(self.app.styleSheet(), qss)

    def test_khung_nut_a_tru_a_cong(self):
        for k in ('nho', 'to'):
            b = self.w.nut_ty_le[k]
            self.assertEqual(b.objectName(), 'nut_zoom')
            qss = b.styleSheet()
            for s in ('#CBD5E1', '1px solid'):
                self.assertIn(s, qss)
            self.assertRegex(qss, r'border-radius: [45]px')                 # 4px (phóng cỡ chữ -> 5px)
        self.assertNotEqual(self.w.nut_ty_le['ty_le'].objectName(), 'nut_zoom')       # "110%" là chữ bấm, không khung


class TestBangGanDay(CoSo):
    def test_trang_thai_trong(self):
        w = self.w
        w.show()
        self.app.processEvents()
        self.assertEqual(w.ds_gan_day.rowCount(), 0)
        self.assertEqual(w.ngan_gan_day.currentIndex(), 1)                 # hiện trạng thái trống, không phải lưới trắng
        self.assertIn('Chưa có hồ sơ dự án nào được mở gần đây.', w.lb_trong.text())
        self.assertIn("'Dự án mới' hoặc 'Mở dự án' phía trên để bắt đầu.", w.lb_trong.text())
        self.assertFalse(w.ds_gan_day.isVisible())
        self.assertFalse(w.khung_nut_gan.isVisible())                      # bảng trống: ẩn cụm nút thao tác
        self.assertFalse(w.o_tim_gan.isEnabled())
        self.assertEqual(w.o_tim_gan.placeholderText(), 'Tìm theo tên dự án, địa bàn...')
        self.assertRegex(w.o_tim_gan.styleSheet(), r'border-radius: [67]px')    # 6px (phóng cỡ chữ 110% -> 7px)

    def test_co_du_an_thi_hien_bang_va_nut_tren_dau(self):
        from PySide6.QtCore import QPoint
        w = self.w
        p = _du_an(Path(self.tmp.name), 3)
        w.mo(str(p))
        w.dong_du_an_lenh()
        w.show()
        self.app.processEvents()
        self.assertEqual(w.ds_gan_day.rowCount(), 1)
        self.assertEqual(w.ngan_gan_day.currentIndex(), 0)
        self.assertTrue(w.khung_nut_gan.isVisible())
        self.assertTrue(w.o_tim_gan.isEnabled())

        def vi_tri(x):
            return x.mapTo(w, QPoint(0, 0))
        bang = vi_tri(w.ngan_gan_day)
        for b in (w.b_mo_gan, w.b_bo_gan):
            self.assertIs(b.parentWidget(), w.khung_nut_gan)
            self.assertLess(vi_tri(b).y(), bang.y())                       # trên đầu bảng
            self.assertLess(vi_tri(b).x(), vi_tri(w.o_tim_gan).x())        # bên trái ô tìm
        self.assertLess(vi_tri(w.b_mo_gan).x(), vi_tri(w.b_bo_gan).x())
        # không còn hàng nút dưới bảng
        for b in (w.b_mo_gan, w.b_bo_gan, w.b_xoa_gan):
            self.assertLess(vi_tri(b).y() + b.height(), bang.y() + 1)
        w.ds_gan_day.selectRow(0)
        self.assertTrue(w.b_mo_gan.isEnabled())

    def test_tim_theo_ten_va_dia_ban(self):
        w = self.w
        p = _du_an(Path(self.tmp.name), 3)                                  # tên dự án 'Thử', địa bàn Xã Bàu Hàm
        w.mo(str(p))
        w.dong_du_an_lenh()
        w._loc_gan_day('bau ham')                                           # địa bàn (không dấu)
        self.assertFalse(w.ds_gan_day.isRowHidden(0))
        w._loc_gan_day('xyz không có')
        self.assertTrue(w.ds_gan_day.isRowHidden(0))
        w._loc_gan_day('')
        self.assertFalse(w.ds_gan_day.isRowHidden(0))


class TestMenuTraiMoTheoDuAn(CoSo):
    def _trang_thai(self, ten):
        return self.w.lenh[ten].isEnabled()

    def test_chua_mo_du_an_lam_mo_nhom_4_5_6(self):
        for ten in NHOM_MO:
            self.assertFalse(self._trang_thai(ten), ten)
        for ten in NHOM_SANG:
            self.assertTrue(self._trang_thai(ten), ten)

    def test_mo_bat_sang_dong_lam_mo_lai(self):
        p = _du_an(Path(self.tmp.name), 3)
        self.w.mo(str(p))
        for ten in NHOM_MO + NHOM_SANG:
            self.assertTrue(self._trang_thai(ten), ten)
        self.w.dong_du_an_lenh()
        for ten in NHOM_MO:
            self.assertFalse(self._trang_thai(ten), ten)
        for ten in NHOM_SANG:
            self.assertTrue(self._trang_thai(ten), ten)

    def test_mo_chi_xem_van_tat_lap_phuong_an(self):
        p = _du_an(Path(self.tmp.name), 3)
        self.w.mo(str(p), chi_doc=True)
        self.assertFalse(self._trang_thai('Lập phương án hộ…'))
        for ten in NHOM_MO:
            if ten != 'Lập phương án hộ…':
                self.assertTrue(self._trang_thai(ten), ten)

    def test_nut_menu_trai_hien_mo(self):
        from PySide6.QtWidgets import QToolButton
        nut = [b for b in self.w.khung_menu.findChildren(QToolButton)
               if b.defaultAction() is self.w.lenh['Kiểm tra lỗi…']]
        self.assertTrue(nut)
        self.assertFalse(nut[0].isEnabled())


class TestChanTrang(CoSo):
    def test_bon_lien_ket_dung_thu_tu(self):
        w = self.w
        self.assertEqual([lk.text() for lk in w.lien_ket_chan.values()],
                         ['Hướng dẫn sử dụng (F1)', 'Tra cứu Bảng giá đất NQ 28', 'Quy trình 16 bước QĐ 18', 'Lịch sử cập nhật phần mềm'])
        self.assertIs(w.lk_huong_dan, w.lien_ket_chan['lich_su'])
        w.show()
        self.app.processEvents()
        x = [lk.mapTo(w, lk.rect().topLeft()).x() for lk in w.lien_ket_chan.values()]
        self.assertEqual(x, sorted(x))                                      # xếp ngang, từ trái sang phải
        y = {lk.mapTo(w, lk.rect().topLeft()).y() for lk in w.lien_ket_chan.values()}
        self.assertEqual(len(y), 1)                                         # cùng một hàng

    def test_bam_lien_ket_chay_dung_lenh(self):
        w = self.w
        with mock.patch.object(w, 'huong_dan') as hd, mock.patch.object(w, 'bang_gia_dat') as bg, \
                mock.patch.object(w, 'quy_trinh_16_buoc') as qt, mock.patch.object(w, 'lich_su_cap_nhat') as ls:
            for ten in ('huong_dan', 'bang_gia_dat', 'quy_trinh', 'lich_su'):
                w.lien_ket_chan[ten].bam()
        for m in (hd, bg, qt, ls):
            m.assert_called_once()

    def test_hop_quy_trinh_16_buoc(self):
        from pabt import quy_trinh_qd18
        hop = self.w.quy_trinh_16_buoc(cho=False)
        self.addCleanup(hop.deleteLater)
        self.assertEqual(hop.bang.rowCount(), 16)
        self.assertEqual([hop.bang.item(r, 0).text() for r in range(16)], [f'Bước {i}' for i in range(1, 17)])
        self.assertEqual(len(quy_trinh_qd18.BUOC), 16)
        chu = ' '.join(hop.bang.item(r, 3).text() for r in range(16))   # cột 2 = Thời hạn (SLA, 0.9.87)
        for nhom in ('1. Khái toán & dự toán', '4. Lập phương án', '5. Tổng hợp & trình duyệt', '6. Phê duyệt & bàn giao'):
            self.assertIn(nhom, chu)


if __name__ == '__main__':
    unittest.main()
