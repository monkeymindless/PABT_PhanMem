"""0.9.66 (người dùng 12/10/2026): mỗi lệnh một chỗ - lệnh đã có ở menu trái không lặp ở thanh menu; lệnh của menu trái / thanh
menu không lặp thành nút trên thanh tiêu đề, thanh công cụ danh sách hộ, chân trang màn hình chào. Giữ: thẻ bắt đầu của màn hình
chào (Dự án mới / Mở / Nhập Excel) và menu chuột phải (ngữ cảnh) - dùng chính QAction của lệnh."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tests.test_toc_do import _du_an


class TestKhongTrungLenh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # dọn qua addCleanup (chạy SAU khi đóng cửa sổ - LIFO): xóa thư mục khi cửa sổ còn mở file dự án -> WinError 32
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')

    def _cua_so(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        self._so = getattr(self, '_so', 0) + 1                      # mỗi cửa sổ một file dự án (cửa sổ trước còn giữ file)
        d = Path(self.tmp.name) / f'da_{self._so}'
        d.mkdir()
        w.mo(str(_du_an(d, 3)))
        self.app.processEvents()
        return w

    def test_khong_trung_menu_trai(self):
        from PySide6.QtWidgets import QToolButton
        w = self._cua_so()
        trai = {b.defaultAction() for b in w.khung_menu.findChildren(QToolButton) if b.defaultAction() is not None}
        self.assertIn(w.lenh['Thông tin dự án…'], trai)
        for nhom, m in w.menu_tren.items():
            for a in m.actions():
                self.assertNotIn(a, trai, f'"{a.text()}" ở cả menu trái và menu {nhom}')
        self.assertNotIn('Thông tin dự án…', [a.text() for a in w.menu_tren['Cài đặt'].actions()])

    def test_nut_khong_lap_lenh_menu(self):
        from PySide6.QtWidgets import QToolButton
        w = self._cua_so()
        trai = {b.defaultAction() for b in w.khung_menu.findChildren(QToolButton) if b.defaultAction() is not None}
        tren = {a for m in w.menu_tren.values() for a in m.actions() if not a.isSeparator()}
        the_chao = set(w.nut_chao.values())                              # thẻ bắt đầu: giữ (màn hình chưa mở dự án)
        w.ve_trang_chu()                                                 # 1.0.07: tổng quan dự án - thẻ khởi tạo cũng là thẻ bắt đầu
        the_chao |= set(w.tong_quan.the_khoi_tao.values())
        for b in w.findChildren(QToolButton):
            a = b.defaultAction()
            if a is None or b in the_chao or w.khung_menu.isAncestorOf(b):
                continue
            self.assertNotIn(a, trai | tren, f'nút "{a.text()}" trùng lệnh menu')
        # 31/10/2026: Xem hộ trên bản đồ (người dùng yêu cầu nút ngoài bảng) - không có ở menu trái / thanh menu
        self.assertEqual(set(w.nut_ds), {'Thêm hộ…', 'Chọn hộ niêm yết…', 'Xóa hộ…', 'Xem hộ trên bản đồ…'})
        self.assertFalse(hasattr(w, 'hang_chon'))
        self.assertFalse(hasattr(w, 'nut_chao_du_an'))
        t = w.thanh_td
        if t is not None:
            from PySide6.QtWidgets import QAbstractButton
            self.assertEqual({b for b in t.findChildren(QAbstractButton) if not t.mb.isAncestorOf(b)},   # trừ nút "»" của QMenuBar
                         set(t.nut_cua_so.values()))

    def test_moi_muc_menu_bam_duoc(self):
        """0.9.68 (người dùng 12/10/2026: "nút Tệp tin không bấm được"): khung điều khiển tab (KhungLamViecDaTab, không xếp trong
        bố cục) từng HIỆN ở góc (0, 0) cửa sổ, trong suốt 100 x 30, nuốt cú bấm vào "Tệp tin". Tâm mọi mục menu phải là thanh
        menu (cả khung Windows / bản Qt 5)."""
        for khung_windows in (False, True):
            if khung_windows:
                os.environ['PABT_KHUNG_WINDOWS'] = '1'
                self.addCleanup(os.environ.pop, 'PABT_KHUNG_WINDOWS', None)
            w = self._cua_so()
            w.resize(1300, 760)
            self.app.processEvents()
            self.assertFalse(w.khung_tab.isVisible())
            mb = w.menuBar()
            for a in mb.actions():
                p = mb.mapTo(w, mb.actionGeometry(a).center())
                o = w.childAt(p)
                self.assertTrue(o is mb or mb.isAncestorOf(o), f'"{a.text()}" bị che bởi {type(o).__name__}')

    def test_lenh_van_dung_duoc(self):
        """Bỏ nút không bỏ lệnh: vẫn có trong self.lenh và ở đúng một chỗ trên giao diện."""
        w = self._cua_so()
        for ten in ('Thông tin dự án…', 'Theo dõi tiến độ', 'Xuất báo cáo đối chiếu…', 'Bộ đơn giá…', 'Lập phương án hộ…',
                    'Xuất danh sách hộ…', 'Hướng dẫn sử dụng', 'Bảng giá đất NQ 28…'):
            self.assertIn(ten, w.lenh)
        self.assertEqual(w.lenh['Hướng dẫn sử dụng'].shortcut().toString(), 'F1')


if __name__ == '__main__':
    unittest.main()
