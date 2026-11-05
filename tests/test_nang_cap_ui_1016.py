"""1.0.16 (người dùng 22/10/2026, nâng cấp giao diện): menu trái tự thu gọn khi soạn phương án hộ trên cửa sổ hẹp (1366 @125% = 1093 điểm),
nút / ô nhập có tên truy cập (trình đọc màn hình), nút xóa chữ của ô tìm có chú thích, ô chọn lần / thanh nút lập phương án không cắt chữ."""
from __future__ import annotations

import unittest

from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class TestNangCapUi(CoSo):
    w = None

    def tearDown(self):
        if self.w is not None:
            for k in [k for k in self.w.khung_tab.khoa if isinstance(k, tuple)]:
                self.w.khung_tab.widget[k].bo_thay_doi()
            self.w.close()
            self.w.dong_du_an() if self.w.con is not None else None
        super().tearDown()

    def _cua_so(self, rong):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.w = w
        w.resize(rong, 700)
        w.show()
        w.mo(str(_du_an(self.td, 3)))
        self.app.processEvents()
        return ud, w

    def test_menu_tu_thu_gon_khi_soan_phuong_an_o_cua_so_hep(self):
        ud, w = self._cua_so(1100)
        self.assertLess(w.width(), w.RONG_CUA_SO_HEP)
        self.assertFalse(w.khung_menu.thu_gon)
        ma = w.ho_dang_chon() if hasattr(w, 'ho_dang_chon') and w.ho_dang_chon() else \
            w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        w.mo_lap_pa(ma)
        self.app.processEvents()
        self.assertTrue(w.khung_menu.thu_gon)                           # tự thu gọn: trả ~200 điểm chiều ngang cho phương án
        w.mo_trang(ud.TRANG_DS)
        self.app.processEvents()
        self.assertFalse(w.khung_menu.thu_gon)                          # rời trang soạn phương án: mở lại

    def test_nguoi_dung_tu_mo_menu_thi_khong_tu_thu_gon_lai(self):
        ud, w = self._cua_so(1100)
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        w.mo_lap_pa(ma)
        self.app.processEvents()
        self.assertTrue(w.khung_menu.thu_gon)
        w.khung_menu.nut_thu_gon.click()                                # người dùng bấm Mở rộng
        self.assertFalse(w.khung_menu.thu_gon)
        w.mo_trang(ud.TRANG_DS)
        self.app.processEvents()
        self.assertFalse(w.khung_menu.thu_gon)                          # giữ nguyên lựa chọn của người dùng

    def test_cua_so_rong_khong_tu_thu_gon(self):
        ud, w = self._cua_so(1600)
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        w.mo_lap_pa(ma)
        self.app.processEvents()
        self.assertFalse(w.khung_menu.thu_gon)

    def test_ten_truy_cap_nut_va_o_nhap(self):
        from PySide6.QtWidgets import QAbstractButton, QLineEdit, QPushButton, QToolButton, QWidget
        from pabt import giao_dien
        k = QWidget()
        b1 = QPushButton('&Lưu && đóng')
        b2 = QToolButton()
        b2.setToolTip('Xóa dòng\nXóa dòng đang chọn khỏi bảng')
        b3 = QPushButton('Đã đặt tên')
        b3.setAccessibleName('Tên riêng')
        o1 = QLineEdit()
        o1.setPlaceholderText('Tìm mã hộ, chủ hộ…')
        for x in (b1, b2, b3, o1):
            x.setParent(k)
        giao_dien.dat_ten_truy_cap(k)
        self.assertEqual(b1.accessibleName(), 'Lưu & đóng')               # bỏ ký tự phím tắt, giữ dấu &
        self.assertEqual(b2.accessibleName(), 'Xóa dòng')                 # nút chỉ biểu tượng: dòng đầu chú thích
        self.assertEqual(b3.accessibleName(), 'Tên riêng')                # không ghi đè tên đặt tay
        self.assertEqual(o1.accessibleName(), 'Tìm mã hộ, chủ hộ…')
        self.assertTrue(all(isinstance(x, QAbstractButton) for x in (b1, b2, b3)))

    def test_nut_xoa_chu_o_tim_co_chu_thich(self):
        from PySide6.QtWidgets import QToolButton
        from pabt import giao_dien
        o = giao_dien.OTimKiemThongMinh()
        ds = [b for b in o.findChildren(QToolButton)]
        self.assertTrue(ds)
        self.assertTrue(all(b.toolTip() == 'Xóa chữ đã gõ' and b.accessibleName() for b in ds))

    def test_lap_pa_nut_khong_cat_chu_o_cua_so_hep(self):
        from PySide6.QtWidgets import QPushButton
        ud, w = self._cua_so(1280)
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        w.mo_lap_pa(ma)
        for _ in range(5):
            self.app.processEvents()
        cs = w.khung_tab.widget[('ho', ma)]
        for b in cs.thanh_tren.findChildren(QPushButton):
            if b.isVisibleTo(cs) and b.text():
                self.assertTrue(b.text().strip())
        self.assertEqual(cs.b_luu.text(), 'Lưu (Ctrl+S)')
        self.assertEqual(cs.btn_toggle_preview.text(), 'Xem trước')
        self.assertIn('Ctrl+S', cs.b_luu.toolTip())
        self.assertIn('F4', cs.btn_toggle_preview.toolTip())


if __name__ == '__main__':
    unittest.main()
