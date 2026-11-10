"""1.0.16 (người dùng 22/10/2026: đang lập phương án chi tiết thì một cửa sổ rỗng - chỉ có biểu tượng, nút thu nhỏ / phóng to / đóng,
tiêu đề "PABT" - nhấp nháy mà không biết lệnh nào gây ra): NGUYÊN NHÂN là khung xem trước F4 gọi setVisible(True) lên nút "In…" /
"In nhanh" trước khi đặt vào bố cục - widget chưa có cha hiện thành cửa sổ cấp cao riêng. Kiểm tra: mở lập phương án, bật / tắt xem
trước, đổi thẻ, đổi hộ -> không widget thường (không phải hộp thoại / menu / cửa sổ chính) nào hiện thành cửa sổ cấp cao."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from tests.test_giao_dien_navy_con import _Co, _qt  # noqa: E402


class _BatCuaSo:
    """Bộ lọc sự kiện toàn ứng dụng: ghi lại mọi widget THƯỜNG hiện thành cửa sổ cấp cao."""

    def __init__(self):
        from PySide6.QtCore import QEvent, QObject, Qt
        from PySide6.QtWidgets import QDialog, QMainWindow, QWidget
        ds = self.ds = []

        class Loc(QObject):
            def eventFilter(self, o, e):
                if e.type() == QEvent.Type.Show and isinstance(o, QWidget) and o.isWindow() \
                        and not isinstance(o, (QDialog, QMainWindow)) and o.windowType() == Qt.WindowType.Window:
                    ds.append((type(o).__name__, o.objectName(), o.windowTitle()))
                return False
        self.loc = Loc()

    def gan(self):
        _qt().installEventFilter(self.loc)

    def go(self):
        _qt().removeEventFilter(self.loc)


class TestKhongCuaSoLa(_Co):
    def test_mo_lap_pa_va_xem_truoc_khong_hien_cua_so_la(self):
        from pabt import man_hinh as mh
        bat = _BatCuaSo()
        bat.gan()
        self.addCleanup(bat.go)
        w = mh.CuaSoLapPA(self.con, 1)
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        w.show()
        app = _qt()
        app.processEvents()
        for i in range(w.tab.count()):
            w.tab.setCurrentIndex(i)
            app.processEvents()
        for _ in range(2):                              # bật rồi tắt xem trước A4 (F4): tạo khung xem trước lần đầu
            w.bat_tat_xem_truoc()
            app.processEvents()
        w.sang_ho(1)
        w.sang_ho(-1)
        app.processEvents()
        self.assertEqual(bat.ds, [])

    def test_chon_chinh_sach_ho_tro_khong_hien_hop_trong(self):
        """Người dùng 05/11/2026: chọn chính sách hỗ trợ hiện hộp thoại trống (nhãn không cha, setVisible(True) khi đổi loại chính sách)."""
        from pabt import man_hinh as mh
        bat = _BatCuaSo()
        bat.gan()
        self.addCleanup(bat.go)
        w = mh.CuaSoLapPA(self.con, 1)
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        w.show()
        app = _qt()
        i = next(k for k in range(w.tab.count()) if 'Hỗ trợ' in w.tab.tabText(k))
        w.tab.setCurrentIndex(i)
        app.processEvents()
        ds = w.bo.dm.muc[4]
        self.assertTrue(ds)
        for m in ds:
            w.bang[4]._da_chon(m)
            app.processEvents()
        self.assertEqual(bat.ds, [])

    def test_chon_danh_muc_moi_muc_khong_hien_cua_so_la(self):
        """Rà soát 06/11/2026: hàng nhập nhanh của mọi mục (nhà, cây, vật nuôi, hỗ trợ) đều đổi nhãn theo dòng chọn."""
        from pabt import man_hinh as mh
        bat = _BatCuaSo()
        bat.gan()
        self.addCleanup(bat.go)
        w = mh.CuaSoLapPA(self.con, 1)
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        w.show()
        app = _qt()
        da_thu = 0
        for muc, ds in w.bo.dm.muc.items():
            try:
                bang = w.bang[muc]
            except KeyError:                            # danh mục không có bảng riêng (chỉ để tra)
                continue
            if not hasattr(bang, '_da_chon'):
                continue
            for m in list(ds)[:8]:
                bang._da_chon(m)
                app.processEvents()
                da_thu += 1
        self.assertGreater(da_thu, 0)
        self.assertEqual(bat.ds, [])

    def test_khung_xem_truoc_nut_in_chi_hien_sau_khi_co_cha(self):
        from pabt import xem_truoc_tai_lieu as xt
        bat = _BatCuaSo()
        bat.gan()
        self.addCleanup(bat.go)
        k = xt.KhungXemTruocTaiLieu(ham_in=lambda *a: None) if 'ham_in' in xt.KhungXemTruocTaiLieu.__init__.__code__.co_varnames \
            else xt.KhungXemTruocTaiLieu()
        self.addCleanup(k.deleteLater)
        _qt().processEvents()
        self.assertEqual(bat.ds, [])
        self.assertIsNotNone(k.b_in.parentWidget())
        self.assertIsNotNone(k.b_in_hop.parentWidget())


if __name__ == '__main__':
    unittest.main()
