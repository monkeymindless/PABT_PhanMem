"""Kiểm thử cửa sổ: dùng PySide6 thật (chế độ không hiển thị) nếu có, không thì dùng bản giả lập
để chạy hết phần logic của cửa sổ (đọc dữ liệu, định dạng, mở chi tiết hộ)."""
from __future__ import annotations
import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from pabt.tien import D, vn

from tests.test_nghiep_vu import FILE_EXCEL

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


def _gia_lap_pyside6():
    class _Meta(type):
        def __getattr__(cls, ten):
            return mock.MagicMock(name=ten)

    class _Q(metaclass=_Meta):
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, ten):
            return mock.MagicMock(name=ten)

    class _Model(_Q):
        def beginResetModel(self):
            pass

        def endResetModel(self):
            pass

    goc = types.ModuleType('PySide6')
    core, gui, w = (types.ModuleType('PySide6.' + n) for n in ('QtCore', 'QtGui', 'QtWidgets'))
    core.Qt = mock.MagicMock()
    core.QAbstractTableModel = _Model
    core.QModelIndex = lambda: mock.MagicMock(isValid=lambda: False)
    core.QSortFilterProxyModel = _Q
    core.QTimer = _Q
    for n in ('QAction', 'QBrush', 'QColor', 'QFont'):
        setattr(gui, n, type(n, (_Q,), {}))
    for n in ('QAbstractItemView', 'QApplication', 'QDialog', 'QFileDialog', 'QHBoxLayout', 'QHeaderView', 'QLabel', 'QLineEdit', 'QMainWindow',
              'QMessageBox', 'QPlainTextEdit', 'QTableView', 'QToolBar', 'QTreeWidget', 'QTreeWidgetItem', 'QVBoxLayout', 'QWidget'):
        setattr(w, n, type(n, (_Q,), {}))
    goc.QtCore, goc.QtGui, goc.QtWidgets = core, gui, w
    return {'PySide6': goc, 'PySide6.QtCore': core, 'PySide6.QtGui': gui, 'PySide6.QtWidgets': w}


@unittest.skipUnless(FILE_EXCEL.exists(), 'không có file Excel mẫu')
class TestCuaSo(unittest.TestCase):
    def test_mo_du_an_va_chi_tiet(self):
        from pabt import nhap_excel
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.pabt'
            nhap_excel.nhap(FILE_EXCEL, p)
            if CO_QT:
                os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance() or QApplication([])
                from pabt import app as ud
                w = ud.CuaSoChinh()
                w.mo(str(p))
                self.assertEqual(w.mo_hinh.rowCount(), 116)
                self.assertEqual(w.mo_hinh.dong[0]['tong'], D('812506000'))
                self.assertEqual(vn(w.bang_tong_hop.tien.dong()[0][10]), '812.506.000')     # tiền từng mục: Bảng tổng hợp
                ud.ChiTietHo(w.con, 1, w)
                w.close()
            else:
                with mock.patch.dict(sys.modules, _gia_lap_pyside6()):
                    sys.modules.pop('pabt.app', None)
                    ud = importlib.import_module('pabt.app')
                    w = ud.CuaSoChinh()
                    w.mo(str(p))
                    m = w.mo_hinh
                    self.assertEqual(len(m.dong), 116)
                    o = mock.MagicMock()
                    o.isValid.return_value = True
                    o.row.return_value, o.column.return_value = 0, 4
                    self.assertEqual(m.data(o, ud.Qt.ItemDataRole.DisplayRole), '625,7')
                    for c in range(len(ud.COT)):
                        o.column.return_value = c
                        m.data(o, ud.Qt.ItemDataRole.DisplayRole)
                        m.data(o, ud.Qt.ItemDataRole.UserRole)
                    ud.ChiTietHo(w.con, 1, w)
                    ud.ChiTietHo(w.con, 2, w)
                    w.dong_du_an()
                    sys.modules.pop('pabt.app', None)


if __name__ == '__main__':
    unittest.main()
