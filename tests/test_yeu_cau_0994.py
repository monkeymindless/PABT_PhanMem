"""0.9.94 (người dùng 15/10/2026): danh sách dự án gần đây không bị file tạm đẩy mất; Niêm yết & Lấy ý kiến - nút Xuất bảng niêm
yết trên hàng nút đợt, cột "CCCD" (số vẫn che), 4 thẻ gọn, bề rộng cột chuẩn + sàn tiêu đề; thẻ KPI / nút gọn."""
from __future__ import annotations

import json
import os

from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class TestGanDay(CoSo):
    def test_bo_file_da_mat_khi_ghi(self):
        from pabt import app as ud
        that = [self.td / f'that_{i}.larc' for i in range(3)]
        for p in that:
            p.write_bytes(b'x')
        tam = [str(self.td / 'da_xoa' / f'tam_{i}.pabt') for i in range(ud.GAN_DAY_TOI_DA)]
        f = ud._file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(tam + [str(p) for p in that]), encoding='utf-8')   # file tạm (đã xóa) chiếm hết chỗ
        moi = self.td / 'moi.larc'
        moi.write_bytes(b'x')
        ud.ghi_gan_day(moi)
        ds = ud.doc_gan_day()
        self.assertEqual(ds[0], str(moi.resolve()))
        self.assertFalse([x for x in ds if 'da_xoa' in x])
        for p in that:                                                   # dự án thật không còn bị đẩy ra khỏi danh sách
            self.assertIn(str(p), ds)

    def test_thu_muc_may_test_khong_phai_appdata(self):
        """Bộ kiểm thử không ghi vào %APPDATA%\\PABT của người dùng (tests/__init__ + bài tự đặt thì trả lại giá trị cũ)."""
        from pabt import may_chu
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            self.assertNotEqual(os.path.normcase(str(may_chu.thu_muc_may())),
                                os.path.normcase(os.path.join(appdata, 'PABT')))


class TestNiemYet(CoSo):
    def _khung(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.w = w
        w.resize(1300, 800)
        w.show()
        w.mo(str(_du_an(self.td, 4)))
        w.mo_du_thao()
        self.app.processEvents()
        return w, w.khung_tab.widget['du_thao']

    def tearDown(self):
        w = getattr(self, 'w', None)
        if w is not None:
            w.close()
            w.dong_du_an()
        super().tearDown()

    def test_nut_xuat_cot_cccd_va_the_gon(self):
        from PySide6.QtWidgets import QPushButton
        w, k = self._khung()
        self.assertFalse(w.hang_the.isVisibleTo(w))                     # không hai hàng thẻ số (danh sách hộ + Niêm yết)
        self.assertEqual(k.bang_ny.horizontalHeaderItem(2).text(), 'CCCD')
        b = k._nut['Xuất bảng niêm yết']
        self.assertIs(b, k.b_xuat_ny)
        self.assertIs(b.parentWidget(), k.b_tao.parentWidget())         # cùng hàng nút đợt, không nằm trong thẻ 1
        trang1 = k.tach.widget(0)
        self.assertFalse([x for x in trang1.findChildren(QPushButton)])  # thẻ 1: bảng sát thanh thẻ
        self.assertIn('padding: 4px 12px', k.tabs.styleSheet())
        self.assertIn('font-size: 12px', k.tabs.styleSheet())
        for t in k.the.values():                                         # KPI: nhãn + (số | chữ phụ) - 2 hàng thay 3
            self.assertIs(t.gia.parentWidget(), t)
            self.assertEqual(t.layout().count(), 2)

    def test_be_rong_cot_va_san_tieu_de(self):
        from PySide6.QtWidgets import QHeaderView
        w, k = self._khung()
        hd = k.bang_ny.horizontalHeader()
        self.assertEqual(hd.sectionResizeMode(5), QHeaderView.ResizeMode.Stretch)     # Địa điểm giãn
        self.assertEqual(hd.sectionResizeMode(4), QHeaderView.ResizeMode.Interactive)
        self.assertGreaterEqual(k.bang_ny.columnWidth(4), 155)                        # Tổng tiền dự thảo
        self.assertGreaterEqual(k.bang_vm.columnWidth(3), 175)                        # Nhóm vướng
        self.assertEqual(k.bang_vm.horizontalHeader().sectionResizeMode(4), QHeaderView.ResizeMode.Stretch)
        for b in (k.bang_ny, k.bang_yk, k.bang_dt, k.bang_th, k.bang_vm):
            h = b.horizontalHeader()
            self.assertGreaterEqual(h.minimumSectionSize(), 60)
            fm = h.fontMetrics()
            for c in range(b.columnCount()):
                if h.sectionResizeMode(c) == QHeaderView.ResizeMode.Stretch:
                    continue
                chu = b.horizontalHeaderItem(c).text()
                self.assertGreaterEqual(b.columnWidth(c), fm.horizontalAdvance(chu) + 26, chu)
        # kéo hẹp cột rồi nạp lại: sàn tiêu đề trả về đủ chữ
        k.bang_ny.setColumnWidth(4, 40)
        k.nap()
        self.assertGreaterEqual(k.bang_ny.columnWidth(4), hd.fontMetrics().horizontalAdvance('Tổng tiền dự thảo') + 26)

    def test_nut_va_the_so_gon(self):
        w, _k = self._khung()
        w.mo_trang(0)
        self.assertTrue(w.hang_the.isVisibleTo(w))                      # quay về danh sách hộ: thẻ số hiện lại
        for b in w.nut_ds.values():
            self.assertLessEqual(b.maximumHeight(), 30)
            self.assertGreaterEqual(b.minimumHeight(), 28)
        from pabt import giao_dien
        tl = max(giao_dien.TY_LE[0], 1.0)                               # phóng to (bài khác để lại) nhân lề / khoảng cách
        the = w.the_so['so_ho'].parentWidget()
        m = the.layout().contentsMargins()
        self.assertLessEqual(m.top() + m.bottom(), 6 * tl + 1)
        from pabt.giao_dien import gian_cach
        gian_cach(w)                                                    # chạy khi cửa sổ hiện: không nâng thẻ lên 10 px
        self.assertEqual(w.hang_the.layout().spacing(), 4)        # 0.9.95: dải KPI một dòng, thẻ cách 4 px
        qss = giao_dien._qss_day_du()
        self.assertIn('QPushButton {{ border-radius: 5px; padding: 4px 10px;'.replace('{{', '{'), qss)


class TestKhongTieuDeTrang(CoSo):
    def test_moi_trang_khong_lap_tieu_de(self):
        """16/10/2026 (người dùng: trang Quyết định phê duyệt "bị trùng tiêu đề mục"): không trang nào hiện dòng tiêu đề trang -
        mục đang chọn đã đánh dấu ở menu trái, tiêu đề khung nằm trong trang."""
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        w.show()
        w.mo(str(_du_an(self.td, 3)))
        try:
            for i, t in enumerate(ud.TRANG):
                w.lenh[t].trigger()
                self.app.processEvents()
                self.assertFalse(w.lb_trang.isVisibleTo(w), t)
                self.assertTrue(w.lb_trang.text())                     # chữ vẫn giữ (tên trang hiện tại)
        finally:
            w.close()
            w.dong_du_an()
