"""0.9.32 theo ARCH-PABT-2026-V5: header 38px, đa tab (hộ / bộ đơn giá), dashboard, bỏ vàng neon."""
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
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestDacTaV5(CoSo):
    def test_header_hop_nhat_va_tab(self):
        from pabt import app as ud, giao_dien
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        self.app.processEvents()
        self.assertFalse(w.bang_tieu_de.isVisible())                    # băng 70px cũ vẫn ẩn
        if w.thanh_td is not None:
            self.assertIs(w.dai_nhan_dien, w.thanh_td.logo)             # 0.9.65: logo nằm trên thanh tiêu đề hợp nhất
        else:                                                           # bản Qt 5 (Win 7/8): khung Windows + hàng menu trắng
            self.assertEqual(w.dai_nhan_dien.height(), 28)
        self.assertEqual(w.banner_ten.height(), giao_dien.CAO_BANNER)
        # hàng menu đủ cao cho mục menu (0.9.65: ép 28 px ở DPI 125% làm mọi mục dồn vào nút "»"); 0.9.88: trong thanh tiêu đề hợp
        # nhất cao ĐÚNG bằng mục menu và canh giữa thanh (cao dư làm chữ menu lệch lên trên chữ tiêu đề)
        mb = w.menuBar()
        self.assertGreaterEqual(mb.height(), mb.sizeHint().height())
        if mb.property('trong_thanh_td'):
            self.assertEqual(mb.height(), mb.sizeHint().height())
            giua_mb, giua_thanh = mb.y() + mb.height() / 2, mb.parentWidget().height() / 2
            self.assertLessEqual(abs(giua_mb - giua_thanh), 1, (mb.geometry(), mb.parentWidget().height()))
        else:
            self.assertGreaterEqual(mb.height(), giao_dien.CAO_MENU)
        self.assertEqual(w.windowTitle(), 'LARC - Lập phương án bồi thường, hỗ trợ')   # 15/10/2026: tên dự án chỉ ở tiêu đề
        self.assertFalse(hasattr(w, 'lb_du_an_nho'))
        self.assertIn('VĨNH CỬU', w.lb_don_vi.text())
        self.assertTrue(w.lb_ban_quyen_nho.text())
        self.assertIsInstance(w.khung_tab, giao_dien.KhungLamViecDaTab)
        self.assertEqual(w.thanh_tab.count(), 1)
        self.assertEqual(w._tab_khoa, [-1])
        self.assertEqual(set(w.nut_chao), {'Dự án mới…', 'Mở dự án…', 'Nhập file Excel…', 'Tiếp nhận & Kiểm tra pháp lý dự án…'})
        self.assertEqual(w.ds_gan_day.columnCount(), 6)
        self.assertEqual(w.lk_huong_dan.text(), 'Lịch sử cập nhật phần mềm')
        from pabt.lich_su_cap_nhat import MUC
        from pabt import __version__
        self.assertEqual(MUC[0][0], __version__)
        self.assertEqual(MUC[-1][0], '0.9.53')
        self.assertFalse(hasattr(w, 'lk_cai_dat'))                      # 0.9.66: liên kết "Cài đặt" trùng menu trái: bỏ
        self.assertTrue(w.thanh_tab.isMovable())
        self.assertEqual(giao_dien.TOKEN['nhan'], '#2563EB')
        self.assertEqual(giao_dien.VANG, '#2563EB')
        self.assertNotIn('#F2B705', giao_dien.QSS_THE_CHAO)
        p = _du_an(self.td, 4)
        w.mo(str(p))
        self.assertIn('(a.pabt)', w.windowTitle())
        self.assertIn(0, w._tab_khoa)                                   # tab danh sách hộ
        w.mo_trang(ud.TRANG_DU_TOAN)
        self.assertIn(ud.TRANG_DU_TOAN, w._tab_khoa)
        self.assertGreaterEqual(w.thanh_tab.count(), 2)
        w.ve_trang_chu()
        self.assertEqual(w.trang.currentIndex(), ud.TRANG_CHAO)
        w.close()

    def test_goc_phai_banner_khoa_cung(self):
        """0.9.65 (người dùng 12/10/2026): góc phải banner (ô dự án, máy đơn, phiên bản, tem bản quyền) và nút thu nhỏ /
        phóng to / đóng của Windows luôn còn: tên dự án dài rút "…", không làm cửa sổ rộng ra; chữ bên trái nhường chỗ."""
        from PySide6.QtCore import Qt
        from pabt import app as ud, __version__
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        co = w.windowFlags()
        self.assertFalse(co & Qt.WindowType.FramelessWindowHint)
        for c in (Qt.WindowType.WindowMinimizeButtonHint, Qt.WindowType.WindowMaximizeButtonHint,
                  Qt.WindowType.WindowCloseButtonHint):
            self.assertTrue(co & c)
        w.resize(1100, 700)
        w.show()
        self.app.processEvents()
        b = w.banner_ten
        goc = b.goc_phai
        self.assertFalse(hasattr(b, 'lb_du_an'))                       # 15/10/2026: bỏ ô "Dự án: …" (tên dự án ở tiêu đề)
        for nhan in (b.lb_phien_ban, b.lb_ban_quyen):
            self.assertTrue(nhan.isVisible())
            self.assertIs(nhan.parentWidget(), goc)
        self.assertFalse(hasattr(b, 'lb_lan'))                         # 0.9.80: "● Máy đơn" chỉ ở nút nut_tk của thanh trạng thái
        self.assertEqual(b.lb_phien_ban.text(), f'Phiên bản {__version__}')
        min_truoc = w.minimumSizeHint().width()
        dai = 'LARC - ' + 'Đường giao thông nối các xã ' * 8 + '(du_an.larc)'
        w.setWindowTitle(dai)                                           # tên dự án dài: tiêu đề rút "…" ở giữa, không ép rộng
        self.app.processEvents()
        self.assertLessEqual(w.minimumSizeHint().width(), max(min_truoc, 1020) + 40)   # vài px: phông offscreen sau test khác
        if w.thanh_td is not None:
            self.assertEqual(w.thanh_td.tieu_de(), dai)
            chu = w.thanh_td.lb_tieu_de.text()
            if chu:                                                     # offscreen: menu chữ rộng có thể chiếm hết chỗ tiêu đề
                self.assertIn('…', chu)
                self.assertTrue(chu.startswith('LARC') and chu.endswith('(du_an.larc)'), chu)
        self.assertLessEqual(goc.geometry().right(), b.width())        # góc phải nằm trọn trong banner
        # cấu trúc (px phụ thuộc phông - offscreen chữ rộng gần gấp đôi Windows): góc phải cố định theo nội dung, chữ bên trái
        # Ignored (nhường chỗ, rút "…")
        from PySide6.QtWidgets import QSizePolicy
        self.assertEqual(goc.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Fixed)
        for nhan in (b.lb_ten, b.lb_don_vi):
            self.assertEqual(nhan.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Ignored)

    def test_thanh_tieu_de_hop_nhat(self):
        """0.9.65 (người dùng 12/10/2026, mẫu VS Code): biểu tượng + menu + Hoàn tác / Làm lại | tiêu đề giữa | Hướng dẫn,
        Cài đặt, nút cửa sổ trên MỘT hàng. Offscreen (không Win32) -> nhánh dự phòng: khung Windows, ẩn nút tự vẽ."""
        from PySide6.QtCore import QPoint, Qt
        import pabt
        from pabt import app as ud, thanh_tieu_de as ttd
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        t = w.thanh_td
        if getattr(pabt, 'QT5', False):                                 # bản Qt 5 (Win 7/8) giữ thanh tiêu đề Windows
            self.assertFalse(ttd.dung_thanh_hop_nhat())
            self.assertIsNone(t)
            self.assertIs(w.menuWidget(), w.menuBar())
            return
        self.assertIsInstance(t, ttd.ThanhTieuDe)
        self.assertIs(w.menuWidget(), t)
        self.assertIs(w.menuBar().parentWidget(), t)                   # menuBar() = thanh menu trong thanh tiêu đề
        self.assertEqual([a.text().replace('&', '') for a in w.menuBar().actions()],
                         ['Tệp tin', 'Chỉnh sửa', 'Dữ liệu', 'Công cụ', 'Cài đặt', 'Trợ giúp'])
        self.assertEqual(set(t.nut_cua_so), {'thu_nho', 'phong_to', 'dong'})
        self.assertTrue(all(b.property('nut_cua_so') for b in t.nut_cua_so.values()))
        # 0.9.66: không nút Hoàn tác / Làm lại / Hướng dẫn / Cài đặt trên thanh (trùng menu) - chỉ 3 nút cửa sổ
        from PySide6.QtWidgets import QAbstractButton
        self.assertEqual({b for b in t.findChildren(QAbstractButton) if not t.mb.isAncestorOf(b)},   # trừ nút "»" của QMenuBar
                         set(t.nut_cua_so.values()))
        self.assertTrue(t.khung_windows)                                # offscreen: không gắn Win32
        self.assertFalse(w.windowFlags() & Qt.WindowType.FramelessWindowHint)
        w.resize(1300, 700)
        w.show()
        self.app.processEvents()
        self.assertEqual(t.height(), ttd.CAO)
        self.assertFalse(any(b.isVisible() for b in t.nut_cua_so.values()))   # khung Windows có nút riêng: không trùng
        w.setWindowTitle('LARC - Thử.pabt')
        self.app.processEvents()
        self.assertEqual(t.tieu_de(), 'LARC - Thử.pabt')
        mb = w.menuBar()
        muc = mb.actionGeometry(mb.actions()[0]).center()
        self.assertFalse(t.la_vung_keo(mb.mapTo(t, muc)))               # mục menu: bấm được
        trong = QPoint(mb.geometry().right() + 20, ttd.CAO // 2)
        self.assertTrue(t.la_vung_keo(trong))                           # vùng trống: kéo cửa sổ (HTCAPTION)
        t.dung_khung_windows()                                          # gọi lại: an toàn
        self.assertFalse(t.nut_cua_so['dong'].isVisible())

    def test_khung_windows_theo_lua_chon(self):
        """--khung-windows / PABT_KHUNG_WINDOWS: thanh tiêu đề Windows + hàng menu trắng như 0.9.64."""
        from pabt import app as ud
        os.environ['PABT_KHUNG_WINDOWS'] = '1'
        self.addCleanup(os.environ.pop, 'PABT_KHUNG_WINDOWS', None)
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        self.assertIsNone(w.thanh_td)
        self.assertIs(w.menuWidget(), w.menuBar())
        self.assertIn('Tệp tin', [a.text().replace('&', '') for a in w.menuBar().actions()])

    def test_tab_ho_va_bo_don_gia_giu_ram(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        p = _du_an(self.td, 3)
        w.mo(str(p))
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        hop = w.mo_lap_pa(ma, cho=True)
        self.assertIsNotNone(hop)
        self.assertTrue(hop.property('nhung_tab'))
        self.assertIn(('ho', int(ma)), w._tab_khoa)
        hop2 = w.mo_lap_pa(ma, cho=True)
        self.assertIs(hop2, hop)                                        # cùng widget — không tạo lại
        dg = w.bo_don_gia(cho=True)
        self.assertTrue(dg.property('nhung_tab'))
        self.assertIn('don_gia', w._tab_khoa)
        self.assertIs(w.bo_don_gia(cho=True), dg)
        hop.bo.sua_dat(0, 'dien_tich', '77.7')
        self.assertTrue(hop.bo.co_thay_doi)
        w.khung_tab.chon(('ho', int(ma)))
        self.assertTrue(w.luu_du_an_lenh())
        self.assertFalse(hop.bo.co_thay_doi)
        w.khung_tab.ke(1)
        self.assertGreaterEqual(w.thanh_tab.count(), 3)
        w.close()

    def test_ghim_du_an_len_dau(self):
        from pabt import app as ud
        (self.td / 'a').mkdir()
        (self.td / 'b').mkdir()
        a = _du_an(self.td / 'a', 2)
        b = _du_an(self.td / 'b', 2)
        ud.ghi_gan_day(a)
        ud.ghi_gan_day(b)                                               # b mới hơn — đứng đầu nếu không ghim
        ud.ghim_du_an(a, True)
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w._nap_gan_day()
        self.assertGreaterEqual(w.ds_gan_day.rowCount(), 2)
        dau = w.ds_gan_day.item(0, 0).data(ud.Qt.ItemDataRole.UserRole)
        self.assertEqual(Path(dau).resolve(), Path(a).resolve())
        w.close()


if __name__ == '__main__':
    unittest.main()
