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

    def test_bang_gan_day_gian_het_va_hien_nhieu_du_an(self):
        """26/10/2026 (người dùng): màn hình chào sát lên trên, bảng dự án gần đây giãn hết phần dưới (không còn tối đa 220 px) và
        hiện tới GAN_DAY_TOI_DA (30) dự án (trước: 8)."""
        from pabt import app as ud
        self.assertGreaterEqual(ud.GAN_DAY_TOI_DA, 30)
        ds = []
        for i in range(12):
            p = self.td / f'da_{i}.larc'
            p.write_bytes(b'x')
            ds.append(str(p))
        f = ud._file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds), encoding='utf-8')
        w = ud.CuaSoChinh(menu_trai=True)
        try:
            w._nap_gan_day()
            self.assertEqual(w.ds_gan_day.rowCount(), 12)
            self.assertGreater(w.ngan_gan_day.maximumHeight(), 10000)               # không giới hạn chiều cao
            self.assertGreater(w.ds_gan_day.maximumHeight(), 10000)
            lo = w.ngan_gan_day.parentWidget().layout()
            self.assertEqual(lo.stretch(lo.indexOf(w.ngan_gan_day)), 1)             # vùng duy nhất giãn theo chiều cao
            self.assertEqual([lo.stretch(i) for i in range(lo.count()) if lo.itemAt(i).spacerItem() is not None
                              and lo.stretch(i) > 0], [])                           # không còn khoảng trống giãn đầu / cuối trang
        finally:
            w.close()

    def test_mo_file_hong_khong_giu_khoa(self):
        """csdl.mo file không phải CSDL (màn hình chào đọc tóm tắt dự án gần đây) - cả mở chỉ xem: đóng kết nối, Windows không giữ khóa file."""
        from pabt import csdl
        for chi_doc in (True, False):
            p = self.td / f'hong_{chi_doc}.larc'
            p.write_bytes(b'khong phai sqlite')
            with self.assertRaises(Exception):
                csdl.mo(p, chi_doc=chi_doc)
            p.unlink()                                                   # còn kết nối mở: PermissionError trên Windows

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
        trang1 = k.trang_ny
        self.assertFalse([x for x in trang1.findChildren(QPushButton)])  # thẻ 1: bảng sát thanh thẻ
        qss_the = k.tabs.tabBar().styleSheet()
        self.assertIn('padding: 4px 12px', qss_the)
        self.assertIn('font-size: 12px', qss_the)
        for t in k.the.values():                                         # KPI: nhãn + (số | chữ phụ) - 2 hàng thay 3
            self.assertIs(t.gia.parentWidget(), t)
            self.assertEqual(t.layout().count(), 2)

    def test_be_rong_cot_va_san_tieu_de(self):
        from PySide6.QtWidgets import QHeaderView
        w, k = self._khung()
        hd = k.bang_ny.horizontalHeader()
        self.assertEqual(hd.sectionResizeMode(1), QHeaderView.ResizeMode.Stretch)     # 1.0.69: Họ và tên giãn, Địa điểm vừa đủ
        self.assertEqual(hd.sectionResizeMode(4), QHeaderView.ResizeMode.Interactive)
        self.assertGreaterEqual(k.bang_ny.columnWidth(4), 135)                        # Tổng tiền dự thảo
        self.assertGreaterEqual(k.bang_vm.columnWidth(3), 175)                        # Nhóm vướng
        self.assertEqual(k.bang_vm.horizontalHeader().sectionResizeMode(4), QHeaderView.ResizeMode.Stretch)
        for b in (k.bang_ny, k.bang_yk, k.bang_dt, k.bang_th, k.bang_vm):
            h = b.horizontalHeader()
            self.assertGreaterEqual(h.minimumSectionSize(), 48 if b is k.bang_ny else 60)
            fm = h.fontMetrics()
            for c in range(b.columnCount()):
                if h.sectionResizeMode(c) in (QHeaderView.ResizeMode.Stretch, QHeaderView.ResizeMode.Fixed):
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
        from pabt import app as ud
        for b in w.nut_ds.values():                                     # 17/10/2026: nút cùng cao dải công cụ 32 px (ô lọc, ô tìm)
            self.assertEqual((b.minimumHeight(), b.maximumHeight()), (ud.CAO_DAI_CONG_CU, ud.CAO_DAI_CONG_CU))
        from pabt import giao_dien
        tl = max(giao_dien.TY_LE[0], 1.0)                               # phóng to (bài khác để lại) nhân lề / khoảng cách
        the = w.the_so['so_ho'].parentWidget()
        m = the.layout().contentsMargins()
        self.assertLessEqual(m.top() + m.bottom(), 12 * tl + 1)
        from pabt.giao_dien import gian_cach
        gian_cach(w)                                                    # chạy khi cửa sổ hiện: không nâng thẻ lên 10 px
        self.assertEqual(w.hang_the.layout().spacing(), 8)        # 17/10/2026: thẻ KPI cách 8 px (0.9.95: 4 px)
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
