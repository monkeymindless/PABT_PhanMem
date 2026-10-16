"""15/10/2026 (người dùng): bỏ thanh tab ngang giữa thanh tiêu đề và nội dung - chuyển trang bằng menu trái / thanh menu
(Ctrl+1..6), thu hồi chiều cao cho bảng; hộ / bộ đơn giá / niêm yết vẫn giữ trong RAM (khung_tab là bộ điều khiển ẩn)."""
from __future__ import annotations

from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class TestBoThanhTab(CoSo):
    w = None

    def tearDown(self):
        if self.w is not None:                          # đóng dự án trước khi xóa thư mục tạm (file .larc đang mở)
            for k in [k for k in self.w.khung_tab.khoa if isinstance(k, tuple)]:
                self.w.khung_tab.widget[k].bo_thay_doi()
            self.w.close()
            self.w.dong_du_an() if self.w.con is not None else None
        super().tearDown()

    def _cua_so(self, so_ho=3):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.w = w
        w.show()
        w.mo(str(_du_an(self.td, so_ho)))
        self.app.processEvents()
        return ud, w

    def test_khong_thanh_tab_chuyen_trang_bang_menu(self):
        ud, w = self._cua_so()
        for i, t in enumerate(ud.TRANG):                                # mở lần lượt mọi trang: thanh tab vẫn không hiện
            w.lenh[t].trigger()
            self.app.processEvents()
            self.assertIs(w.ngan_lv.currentWidget(), w.trang)
            self.assertEqual(w.trang.currentIndex(), ud.STACK_CUA_TRANG[i])
            self.assertTrue(w.lenh[t].isChecked())
        self.assertGreaterEqual(w.thanh_tab.count(), 2)                 # danh sách trang đang mở vẫn giữ (Ctrl+Tab)
        self.assertFalse(w.thanh_tab.isVisibleTo(w))
        self.assertIs(w.thanh_tab.parentWidget(), w.khung_tab)          # không nằm trong bố cục cửa sổ chính
        self.assertFalse(hasattr(w, 'lb_du_an'))                        # tên dự án chỉ ở tiêu đề cửa sổ (thanh menu trắng)
        self.assertTrue(w.windowTitle().startswith('LARC - '))
        # thẻ số liệu ngay dưới banner: không còn dòng nào chen giữa (thanh tab, dòng tên dự án)
        w.mo_trang(ud.TRANG_DS)
        self.app.processEvents()
        self.assertLessEqual(w.hang_the.mapTo(w.centralWidget(), w.hang_the.rect().topLeft()).y(),
                             w.banner_ten.height() + 12)

    def test_ctrl_so_chuyen_trang(self):
        ud, w = self._cua_so()
        from PySide6.QtGui import QKeySequence
        for i, t in enumerate(ud.TRANG):
            self.assertEqual(w.lenh[t].shortcut(), QKeySequence(f'Ctrl+{i + 1}'))
            self.assertIn(w.lenh[t], w.actions())
        phim = [a.shortcut().toString() for a in w.findChildren(type(w.lenh[ud.TRANG[0]])) if not a.shortcut().isEmpty()]
        self.assertEqual(len(phim), len(set(phim)), phim)               # không trùng phím (Qt bỏ qua cả hai)

    def test_ho_va_trang_phu_van_giu(self):
        ud, w = self._cua_so()
        ma = [r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
        a = w.mo_lap_pa(ma[0], cho=True)
        self.assertIs(w.ngan_lv.currentWidget(), w.khung_tab.stack_phu)
        w.lenh['Danh sách hộ'].trigger()                                # rời hộ bằng menu trái
        self.assertIs(w.ngan_lv.currentWidget(), w.trang)
        self.assertIs(w.mo_lap_pa(ma[0], cho=True), a)                  # mở lại: cùng cửa sổ, không tạo mới
        # hộ khác: hộ cũ không có thay đổi -> đóng (không chất cửa sổ ẩn); hộ có thay đổi chưa lưu -> giữ
        b = w.mo_lap_pa(ma[1], cho=True)
        self.assertNotIn(('ho', int(ma[0])), w.khung_tab.khoa)
        b.bo.sua_dat(0, 'dien_tich', '12.5') if b.bo.pa.dat else b.bo.dat_nhan_khau(3)
        self.assertTrue(b.bo.co_thay_doi)
        w.mo_lap_pa(ma[2], cho=True)
        self.assertIn(('ho', int(ma[1])), w.khung_tab.khoa)
        b.bo_thay_doi()
        dg = w.bo_don_gia(cho=True)
        self.assertIs(w.ngan_lv.currentWidget(), w.khung_tab.stack_phu)
        w.lenh['Dự toán & khái toán'].trigger()
        self.assertIs(w.bo_don_gia(cho=True), dg)
        for k in [k for k in w.khung_tab.khoa if isinstance(k, tuple)]:
            w.khung_tab.widget[k].bo_thay_doi()
        self.assertFalse(w.thanh_tab.isVisibleTo(w))

    def test_ten_du_an_chi_o_tieu_de(self):
        """Tên dự án ở MỘT chỗ - tiêu đề giữa thanh menu trắng: "LARC - <tên> · <địa bàn> (<file>)"; banner không còn ô dự án."""
        ud, w = self._cua_so()
        da = w.con.execute('SELECT ten, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
        self.assertTrue(w.windowTitle().startswith(f'LARC - {da[0]} · {da[1]} ('), w.windowTitle())
        self.assertTrue(w.windowTitle().endswith(f'({w.file.name})'))
        self.assertFalse(hasattr(w.banner_ten, 'lb_du_an'))
        from pabt import lap_pa
        lap_pa.luu_du_an(w.con, dict(lap_pa.doc_du_an(w.con), ten='Đường ĐT 762'))   # sửa Thông tin dự án -> tiêu đề đổi theo
        w.tai_lai()
        self.assertIn('LARC - Đường ĐT 762 · ', w.windowTitle())
        if w.thanh_td is not None:
            self.assertEqual(w.thanh_td.tieu_de(), w.windowTitle())
        w.dong_du_an_lenh()                                             # Tệp tin -> Đóng dự án
        self.assertEqual(w.windowTitle(), 'LARC - ' + ud.MO_TA_UD)
