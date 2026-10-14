from __future__ import annotations
import pabt  # noqa: F401  (Qt5: đặt bí danh PySide6 -> PySide2 trước khi các bài kiểm thử nạp Qt)

# Một QApplication dùng chung, giữ tới khi tiến trình kết thúc. Các bài kiểm thử viết `app = QApplication.instance() or
# QApplication([])` trong hàm: biến cục bộ mất thì QApplication có thể bị hủy trước các cửa sổ còn sống -> Qt lỗi khi tắt
# tiến trình (0xC0000409, không ổn định). Lúc thoát: đóng, hủy mọi cửa sổ trước rồi mới tới QApplication.
import atexit
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication
except ImportError:                                     # máy không có Qt: các bài giao diện tự bỏ qua
    APP = None
else:
    APP = QApplication.instance() or QApplication([])

    @atexit.register
    def _dong_qt():
        for w in QApplication.topLevelWidgets():
            w.close()
            w.deleteLater()
        APP.processEvents()
