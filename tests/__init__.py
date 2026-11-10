from __future__ import annotations
import pabt  # noqa: F401  (Qt5: đặt bí danh PySide6 -> PySide2 trước khi các bài kiểm thử nạp Qt)

# Một QApplication dùng chung, giữ tới khi tiến trình kết thúc. Các bài kiểm thử viết `app = QApplication.instance() or
# QApplication([])` trong hàm: biến cục bộ mất thì QApplication có thể bị hủy trước các cửa sổ còn sống -> Qt lỗi khi tắt
# tiến trình (0xC0000409, không ổn định). Lúc thoát: đóng, hủy mọi cửa sổ trước rồi mới tới QApplication.
import atexit
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# offscreen không có phông: mọi ký tự thành ô vuông rộng gấp đôi, số đo bề rộng chữ sai. Dùng phông Windows thật để đo đúng như máy người dùng.
if os.path.isdir(r'C:\Windows\Fonts'):
    os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
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
    from PySide6.QtWidgets import QMessageBox

    _chay_goc = unittest.TestCase.run

    def _chay_roi_don(self, result=None):
        kq = _chay_goc(self, result)
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return kq

    unittest.TestCase.run = _chay_roi_don
    _het_module_goc = unittest.TestSuite._handleModuleTearDown

    def _het_module_roi_don(self, result):
        _het_module_goc(self, result)
        # cửa sổ sót của test có thể đang có thay đổi chưa lưu (form lập phương án tự điền khi nạp): không để hộp "Lưu lại?" hiện giữa lượt (treo / sập)
        hoi_goc = QMessageBox.question
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
        try:
            for w in QApplication.topLevelWidgets():
                w.close()
                w.deleteLater()
        finally:
            QMessageBox.question = hoi_goc
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    unittest.TestSuite._handleModuleTearDown = _het_module_roi_don

    # 07/11/2026 (2 lượt kiểm tra treo hơn 1 giờ không ai biết: bài test hỏng rồi khi dọn cửa sổ hiện hộp "Lưu thay đổi?"):
    # hộp thoại / menu chờ bấm quá GIAY_HOP_TOI_DA: báo tên hộp, tự đóng, test đi tiếp; cả lượt quá GIAY_LUOT_TOI_DA: in chồng gọi rồi thoát.
    # Đổi bằng PABT_TEST_GIAY_HOP / PABT_TEST_GIAY_LUOT (0 = tắt).
    import faulthandler
    import sys as _sys

    from PySide6.QtCore import QTimer

    GIAY_HOP_TOI_DA = int(os.environ.get('PABT_TEST_GIAY_HOP', 60))
    GIAY_LUOT_TOI_DA = int(os.environ.get('PABT_TEST_GIAY_LUOT', 2400))
    HOP_BI_KET = []                                     # tên các hộp phải tự đóng: lượt test có mục này là có lỗi cần xem

    if GIAY_LUOT_TOI_DA and _sys.stderr is not None:
        faulthandler.dump_traceback_later(GIAY_LUOT_TOI_DA, exit=True)

    if GIAY_HOP_TOI_DA:
        _dang_cho = {'hop': None, 'giay': 0}

        def _xet_hop_ket():
            hop = QApplication.activeModalWidget() or QApplication.activePopupWidget()
            if hop is None or hop is not _dang_cho['hop']:
                _dang_cho.update(hop=hop, giay=0)
                return
            _dang_cho['giay'] += 5
            if _dang_cho['giay'] < GIAY_HOP_TOI_DA:
                return
            ten = f'{type(hop).__name__}: {hop.windowTitle()} / {getattr(hop, "text", lambda: "")()}'[:200]
            HOP_BI_KET.append(ten)
            print(f'\n[CHONG TREO] hộp thoại chờ quá {GIAY_HOP_TOI_DA} giây, tự đóng: {ten}', file=_sys.stderr, flush=True)
            _dang_cho.update(hop=None, giay=0)
            hop.close()

        _gac_hop = QTimer(APP)
        _gac_hop.setInterval(5000)
        _gac_hop.timeout.connect(_xet_hop_ket)
        _gac_hop.start()

    @atexit.register
    def _dong_qt():
        for w in QApplication.topLevelWidgets():
            w.close()
            w.deleteLater()
        APP.processEvents()
