"""Thành phần dùng chung (0.9.17): thông báo lỗi 3 phần (thong_bao.chu_loi), bảng ảo cho danh sách lớn (bang_ao.BangAo),
con trỏ chờ luôn được trả lại (giao_dien.con_tro_cho)."""
from __future__ import annotations
import errno
import os
import sqlite3
import unittest
import zipfile

from pabt import thong_bao
from pabt.lap_pa import LoiNhap

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestChuLoi(unittest.TestCase):
    def test_loi_ky_thuat_thanh_cau_de_hieu(self):
        e = PermissionError(errno.EACCES, 'Permission denied', r'D:\DuAn\a.pabt')
        chu = thong_bao.chu_loi('Không mở được dự án:', e)
        dong = chu.split('\n')
        self.assertEqual(dong[0], 'Không mở được dự án.')                    # bỏ dấu ":" thừa, kết thúc bằng dấu chấm
        self.assertIn('Lý do: File đang được chương trình khác mở', chu)
        self.assertIn('Cách xử lý: Đóng file đó', chu)
        self.assertTrue(dong[-1].startswith('Chi tiết kỹ thuật: PermissionError'))   # chi tiết kỹ thuật ở cuối
        for e, cau in ((FileNotFoundError(2, 'x'), 'Không tìm thấy file'),
                       (OSError(errno.ENOSPC, 'No space'), 'Ổ đĩa đã đầy'),
                       (sqlite3.OperationalError('database is locked'), 'đang được máy khác'),
                       (sqlite3.DatabaseError('file is not a database'), 'bị hỏng'),
                       (zipfile.BadZipFile('File is not a zip file'), 'không đúng định dạng Excel / Word')):
            self.assertIn(cau, thong_bao.chu_loi('Không làm được', e), type(e).__name__)

    def test_loi_nghiep_vu_giu_nguyen_khong_lap(self):
        chu = thong_bao.chu_loi('Không lưu được', LoiNhap('Diện tích: "abc" không phải là số.'))
        self.assertEqual(chu, 'Không lưu được.\n\nLý do: Diện tích: "abc" không phải là số.')   # không thêm dòng kỹ thuật lặp lại

    def test_ten_ung_dung_mot_nguon(self):
        from pabt import app, man_hinh, man_hinh_ho_so
        for m in (app, man_hinh, man_hinh_ho_so):
            self.assertIs(m.TEN_UD, thong_bao.TEN_UD)


@unittest.skipUnless(CO_QT, 'cần PySide6 / PySide2')
class TestBangAo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        import pabt  # noqa: F401
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_du_lieu_kieu_gop_va_api_cu(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from pabt.bang_ao import BangAo, GOI_Y_TU
        b = BangAo(['STT', 'Họ tên', 'Tiền'], can_phai=(0, 2))
        dai = 'Nguyễn Văn Thử có họ tên rất dài'
        b.dat_du_lieu([['1', dai, '1.000'], ['', '', '']], du_lieu=[7, 7],
                      kieu={(0, 2): dict(nen=QColor('#E2EFDA'), dam=True, goi_y='QĐ 1')}, gop=[(0, 2, [0, 1, 2])])
        self.assertEqual((b.rowCount(), b.columnCount()), (2, 3))
        self.assertEqual(b.item(0, 1).text(), dai)
        self.assertEqual(b.item(1, 0).data(Qt.ItemDataRole.UserRole), 7)    # mã hộ của dòng (nhấp đúp mở hộ)
        self.assertIsNone(b.item(5, 0))
        mh = b.model()
        self.assertEqual(mh.data(mh.index(0, 1), Qt.ItemDataRole.ToolTipRole), dai if len(dai) > GOI_Y_TU else None)
        self.assertEqual(mh.data(mh.index(0, 2), Qt.ItemDataRole.ToolTipRole), 'QĐ 1')
        self.assertTrue(mh.data(mh.index(0, 2), Qt.ItemDataRole.FontRole).bold())
        self.assertIsNone(mh.data(mh.index(0, 1), Qt.ItemDataRole.BackgroundRole))
        self.assertEqual(b.rowSpan(0, 1), 2)                                    # ô thông tin hộ gộp trên các dòng thửa
        nhan = []
        b.cellDoubleClicked.connect(lambda r, c: nhan.append((r, c)))
        b.doubleClicked.emit(mh.index(1, 2))
        self.assertEqual(nhan, [(1, 2)])

    def test_con_tro_cho_luon_tra_lai(self):
        from PySide6.QtWidgets import QApplication
        from pabt.giao_dien import con_tro_cho
        truoc = QApplication.overrideCursor()
        with self.assertRaises(RuntimeError):
            with con_tro_cho():
                raise RuntimeError('lỗi bất ngờ giữa chừng')
        self.assertIs(QApplication.overrideCursor(), truoc)                    # không kẹt đồng hồ cát


if __name__ == '__main__':
    unittest.main()
