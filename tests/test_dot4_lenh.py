"""Đợt 4 (kiểm toán 09/11/2026): siêu dữ liệu lệnh (phím, cần dự án, chữ ngắn, quyền) trỏ đúng tên lệnh thật; Tìm nhanh Ctrl+K."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def _ten_lenh_that() -> set:
    from pabt import lenh
    return {t for t, _ in lenh.ds_lenh(object())}          # ds_lenh chỉ dựng lambda, không gọi cửa sổ


class TestSieuDuLieuLenh(unittest.TestCase):
    """Khóa lệch tên lệnh = thuộc tính âm thầm mất tác dụng (1.0.91: LENH_QUYEN ghi tên cũ, nút không tắt theo vai trò)."""

    def test_moi_khoa_la_ten_lenh_that(self):
        from pabt import app, phan_quyen
        that = _ten_lenh_that()
        ngoai = {'Quản lý tài khoản…'}                    # mục menu riêng (app._menu_tai_khoan), không thuộc bảng lệnh
        nguon = {
            'PHIM_NHANH': [t for t, _ in app.PHIM_NHANH],
            'PHIM_LENH': [t for t, _ in app.PHIM_LENH],
            'LENH_CAN_DU_AN': list(app.LENH_CAN_DU_AN),
            'NHAN_MENU': list(app.NHAN_MENU),
            'LENH_DANH_DAU_PHU': list(app.LENH_DANH_DAU_PHU),
            'LENH_QUYEN': list(phan_quyen.LENH_QUYEN),
        }
        lech = {ten: [k for k in ds if k not in that and k not in ngoai] for ten, ds in nguon.items()}
        self.assertEqual({k: v for k, v in lech.items() if v}, {})

    def test_phim_khong_trung(self):
        from pabt import app
        phim = [p for _, p in (*app.PHIM_NHANH, *app.PHIM_LENH)]
        self.assertEqual(len(phim), len(set(phim)), 'phím tắt trùng nhau: Qt không chạy cái nào')
        for p in phim:                                      # F2 sửa ô bảng; Ctrl+Z / Y do xu_ly_hoan_tac (CLAUDE.md)
            self.assertNotIn(p, ('F2', 'Ctrl+Z', 'Ctrl+Y', 'Ctrl+Shift+V', 'Ctrl+Shift+C'))


class TestTimNhanh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.qa = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        os.environ['PABT_THU_MUC_MAY'] = self.td.name
        from pabt import app as ud
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(self.w.deleteLater)

    def tearDown(self):
        try:
            self.td.cleanup()
        except OSError:
            pass

    def test_ly_do_tat_khi_chua_mo_du_an(self):
        from pabt.man_hinh_tim_nhanh import ds_muc
        m = {x.khoa: x for x in ds_muc(self.w) if x.loai == 'lenh'}
        self.assertFalse(m['Lập phương án hộ…'].bat)
        self.assertIn('dự án trước', m['Lập phương án hộ…'].ly_do.lower())
        self.assertIn('tắt:', m['Lập phương án hộ…'].phu)                  # lý do hiện ngay trên dòng, không chỉ ở chú thích

    def test_tien_to_va_gan_day(self):
        from pabt.man_hinh_tim_nhanh import HopTimKiemNhanh, ghi_gan_day
        ghi_gan_day(self.w, 'Bộ đơn giá…')
        h = HopTimKiemNhanh(self.w, im_lang=True)
        self.addCleanup(h.deleteLater)
        h.o.setText('')
        dau = h.dong_hien()[0]
        self.assertEqual(dau, ('lenh', 'Bộ đơn giá…'))             # chưa gõ: lệnh dùng gần đây đứng đầu
        h.o.setText('> don gia')
        self.assertTrue(h.dong_hien())
        self.assertTrue(all(lo == 'lenh' for lo, _ in h.dong_hien()))   # ">" chỉ lệnh
        h.o.setText('@ ')
        self.assertTrue(all(lo == 'ho' for lo, _ in h.dong_hien()))     # "@" chỉ hộ (chưa mở dự án: rỗng)

    def test_phim_moi_gan_vao_lenh(self):
        from PySide6.QtGui import QKeySequence
        for ten, phim in (('Thêm hộ…', 'Ctrl+Shift+H'), ('Tính đơn giá đất…', 'Ctrl+Shift+G'), ('Xuất danh sách hộ…', 'Ctrl+Shift+E')):
            self.assertEqual(self.w.lenh[ten].shortcut(), QKeySequence(phim), ten)


if __name__ == '__main__':
    unittest.main()
