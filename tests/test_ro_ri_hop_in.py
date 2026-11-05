"""Bảng In không để sót widget sau khi đóng (06/11/2026): 12 ô / nút không vào bố cục, không có cha, tín hiệu nối lambda giữ self - hộp đã đóng
không bao giờ được giải phóng. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import gc
import unittest

from tests.test_yeu_cau_0984 import CoSoXem


class TestHopInKhongSotWidget(CoSoXem):
    def _mo_dong(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QApplication

        from pabt.man_hinh import HopIn
        app = QApplication.instance()
        h = HopIn(self.con, None, file_du_an=self.p)
        h.im_lang = True
        h.show()
        app.processEvents()
        h.w_preview.don_dep()
        h.close()
        h.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        del h
        gc.collect()

    def test_mo_dong_khong_sot_cua_so_cap_cao(self):
        from PySide6.QtWidgets import QApplication
        self._mo_dong()                                 # lần đầu nạp phần dùng chung
        truoc = len(QApplication.topLevelWidgets())
        for _ in range(3):
            self._mo_dong()
        self.assertEqual(len(QApplication.topLevelWidgets()), truoc)

    def test_o_trang_thai_an_va_co_cha(self):
        from PySide6.QtWidgets import QApplication

        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p)
        h.im_lang = True
        self.addCleanup(h.w_preview.don_dep)
        h.show()
        QApplication.instance().processEvents()
        for w in (h.cb_pham_vi, h.cb_dot, h.o_chia, h.o_mo, h.r_excel, h.r_pdf, h.r_in, h.r_du_thao, h.r_chinh_thuc,
                  h.w_preview.b_ngang, h.w_preview.b_in, h.w_preview.b_in_hop):
            self.assertIsNotNone(w.parent())
            self.assertFalse(w.isVisible())             # không vào bố cục: không được nổi lên góc hộp thoại
        h.close()


if __name__ == '__main__':
    unittest.main()
