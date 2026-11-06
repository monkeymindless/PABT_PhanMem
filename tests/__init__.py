from __future__ import annotations
import pabt  # noqa: F401  (Qt5: đặt bí danh PySide6 -> PySide2 trước khi các bài kiểm thử nạp Qt)

# Một QApplication dùng chung, giữ tới khi tiến trình kết thúc. Các bài kiểm thử viết `app = QApplication.instance() or
# QApplication([])` trong hàm: biến cục bộ mất thì QApplication có thể bị hủy trước các cửa sổ còn sống -> Qt lỗi khi tắt
# tiến trình (0xC0000409, không ổn định). Lúc thoát: đóng, hủy mọi cửa sổ trước rồi mới tới QApplication.
import atexit
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Thư mục dữ liệu máy RIÊNG cho cả lượt kiểm thử (0.9.87): trước đây bài mở dự án ghi đường dẫn tệp tạm vào danh sách "Dự án
# gần đây" (%APPDATA%\PABT\du_an_gan_day.json) của người dùng, đẩy các dự án thật ra khỏi danh sách. Bài nào cần thư mục riêng
# vẫn tự đặt PABT_THU_MUC_MAY (mock.patch.dict).
if not os.environ.get('PABT_THU_MUC_MAY'):
    import tempfile
    os.environ['PABT_THU_MUC_MAY'] = tempfile.mkdtemp(prefix='pabt_test_may_')
# hồ sơ mặc định đóng kèm phần mềm KHÔNG có tên đơn vị / địa phương nào (bản thương mại): phần lớn bài kiểm thử đã viết theo hồ sơ Đồng Nai -> trong
# lượt kiểm thử, "hồ sơ đóng kèm" (dia_phuong.file_goc) trỏ tới ho_so_don_vi/pabt_profile_dong_nai_vinh_cuu.json. Bài kiểm hồ sơ mặc định thật
# (test_yeu_cau_2413) đọc thẳng pabt/pabt_profile.json hoặc đặt file máy đầy đủ riêng.
from pathlib import Path as _Path

from pabt import dia_phuong as _dp
_HO_SO_DONG_NAI = _Path(__file__).resolve().parents[1] / 'ho_so_don_vi' / 'pabt_profile_dong_nai_vinh_cuu.json'
_dp.file_goc = lambda: _HO_SO_DONG_NAI
try:
    from PySide6.QtWidgets import QApplication
except ImportError:                                     # máy không có Qt: các bài giao diện tự bỏ qua
    APP = None
else:
    APP = QApplication.instance() or QApplication([])
    # phông như phần mềm thật (giao_dien.ap_dung). Không đặt thì Qt5 offscreen dùng Helvetica 12 pt: chạy riêng module, dòng bảng 46 px thay vì 30,
    # thẻ số liệu 63 px thay vì 62 (kết quả test phụ thuộc thứ tự chạy). Chỉ đặt phông, không áp cả bảng kiểu (chậm).
    from PySide6.QtGui import QFont
    _phong = QFont('Segoe UI')
    _phong.setPointSizeF(9.5)
    APP.setFont(_phong)

    # Bản Qt5 là tiến trình 32-bit (trần khoảng 1,8 GB): test không có vòng sự kiện nên deleteLater không chạy, cửa sổ đã đóng chất dần; đo 06/11/2026
    # cả lượt lên 1.771 MB rồi sập 0xC0000374 / access violation ở vị trí bất kỳ (lần cấp phát hụt), không ổn định. Sau mỗi bài: hủy các widget đã
    # deleteLater; hết mỗi module (trước setUpClass của module sau): hủy nốt cửa sổ cấp cao còn lại.
    import gc
    import unittest

    from PySide6.QtCore import QCoreApplication, QEvent

    _chay_goc = unittest.TestCase.run

    def _chay_roi_don(self, result=None):
        kq = _chay_goc(self, result)
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return kq

    unittest.TestCase.run = _chay_roi_don
    _het_module_goc = unittest.TestSuite._handleModuleTearDown

    def _het_module_roi_don(self, result):
        _het_module_goc(self, result)
        for w in QApplication.topLevelWidgets():
            w.close()
            w.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    unittest.TestSuite._handleModuleTearDown = _het_module_roi_don

    @atexit.register
    def _dong_qt():
        for w in QApplication.topLevelWidgets():
            w.close()
            w.deleteLater()
        APP.processEvents()
