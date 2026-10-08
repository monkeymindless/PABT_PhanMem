"""Phần mềm lập phương án bồi thường, hỗ trợ (PABT): bộ đơn giá Đồng Nai tích hợp, dự án mới từ dữ liệu thô, bản in."""
from __future__ import annotations
__version__ = '0.9.16'

import sys as _sys
from pathlib import Path as _Path


def tai_nguyen(ten: str) -> _Path:
    """File dữ liệu của gói pabt: cạnh mã (mã nguồn, bản cập nhật .pabtcn), không có thì trong bản đóng gói."""
    p = _Path(__file__).with_name(ten)
    if p.exists() or not getattr(_sys, 'frozen', False):
        return p
    return _Path(getattr(_sys, '_MEIPASS', _Path(_sys.executable).parent)) / 'pabt' / ten


QT5 = False     # True: đang chạy Qt5 (PySide2) - bản phát hành chạy được cả Windows 7 / 8


def _qt5_lam_qt6() -> None:
    """Bản phát hành chạy Python 3.8 + Qt5 (PySide2) để dùng được trên Windows 7 / 8 / 10 / 11; mã viết theo PySide6.
    Máy không có PySide6 mà có PySide2: đặt bí danh PySide6 -> PySide2 và bổ sung vài API Qt6 khác tên. Có PySide6 thì bỏ qua."""
    global QT5
    import importlib.util
    if 'PySide6' in _sys.modules:              # đã nạp (bản cập nhật nạp lại gói pabt): nhận biết bí danh PySide2
        QT5 = getattr(_sys.modules['PySide6'], '__name__', '') == 'PySide2'
        return
    try:
        if importlib.util.find_spec('PySide6') is not None or importlib.util.find_spec('PySide2') is None:
            return
    except (ImportError, ValueError):
        return
    import PySide2
    from PySide2 import QtCore, QtGui, QtWidgets
    for ten, m in (('', PySide2), ('.QtCore', QtCore), ('.QtGui', QtGui), ('.QtWidgets', QtWidgets)):
        _sys.modules['PySide6' + ten] = m
    for ten in ('QAction', 'QActionGroup', 'QShortcut', 'QUndoStack', 'QUndoCommand', 'QFileSystemModel'):
        if not hasattr(QtGui, ten) and hasattr(QtWidgets, ten):
            setattr(QtGui, ten, getattr(QtWidgets, ten))
    for lop in (QtCore.QCoreApplication, QtCore.QEventLoop, QtWidgets.QDialog, QtWidgets.QMenu):
        if not hasattr(lop, 'exec'):
            lop.exec = lop.exec_
    # Qt5 đọc đường dẫn plugin / bản dịch theo bảng mã ANSI: thư mục có chữ Việt (tên người dùng có dấu, "Thư mục mới"...)
    # làm Qt không tìm được plugin nền tảng. Chỉ đường bằng API Unicode.
    goc = _Path(PySide2.__file__).parent
    if (goc / 'plugins').is_dir():
        QtCore.QCoreApplication.setLibraryPaths([str(goc / 'plugins')])
    li = QtCore.QLibraryInfo
    if not hasattr(li, 'path'):
        li.LibraryPath = li.LibraryLocation
        ban_dich = goc / 'translations'
        li.path = staticmethod(lambda k: str(ban_dich) if k == li.TranslationsPath and ban_dich.is_dir() else li.location(k))
    # màn hình phóng to 125% / 150%: Qt5 phải bật trước khi tạo QApplication (Qt6 bật sẵn)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(QtGui.QGuiApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QT5 = True


_qt5_lam_qt6()
