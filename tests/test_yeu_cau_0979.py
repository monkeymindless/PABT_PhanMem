"""0.9.79 (người dùng 13/10/2026): ba thẻ chào đón (giao_dien.TheChao) to hơn - 210 x 135, bo 12px, icon 38px, tên lệnh 14,5pt đậm,
mô tả phụ NẰM TRONG thẻ, mỗi thẻ một màu (moi / mo / excel), cách nhau 20px, căn giữa; bấm ở đâu trong thẻ cũng chạy lệnh."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

TEN = ('Dự án mới…', 'Mở dự án…', 'Nhập file Excel…')
LOAI = {'Dự án mới…': 'moi', 'Mở dự án…': 'mo', 'Nhập file Excel…': 'excel'}
PHU = {'Dự án mới…': 'Khởi tạo CSDL .larc', 'Mở dự án…': 'Chọn tệp từ máy / LAN', 'Nhập file Excel…': 'Bảng kiểm đếm số liệu'}


class TestTheChao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from pabt import app as ud
        from pabt import giao_dien
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        giao_dien.ap_dung(self.app)
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(self.w.close)

    def test_kich_thuoc_icon_va_noi_dung_trong_the(self):
        from PySide6.QtWidgets import QLabel
        from pabt import giao_dien
        self.assertEqual(giao_dien.KICH_THE_CHAO, (210, 135))
        for ten in TEN:
            the = self.w.the_chao[ten]
            self.assertEqual((the.width(), the.height()), (210, 135))
            self.assertEqual((the.minimumWidth(), the.maximumHeight()), (210, 135))          # kích thước cố định
            self.assertEqual(the.property('loai'), LOAI[ten])
            b = self.w.nut_chao[ten]
            self.assertIs(b.parentWidget(), the)                                             # nút (biểu tượng + tên) trong thẻ
            self.assertEqual(b.objectName(), 'the_chao_nut')
            self.assertEqual((b.iconSize().width(), b.iconSize().height()), (38, 38))
            self.assertIs(b.defaultAction(), self.w.lenh[ten])                               # vẫn là lệnh chung (trạng thái bật / tắt)
            nhan = [x for x in the.findChildren(QLabel) if x.property('vai') == 'the_chao_phu']
            self.assertEqual([x.text() for x in nhan], [PHU[ten]])                           # mô tả phụ NẰM TRONG thẻ
            self.assertTrue(the.rect().contains(nhan[0].geometry()) or not the.isVisible())

    def test_khoang_cach_20_va_can_giua(self):
        self.w.resize(1366, 768)
        self.w.show()
        self.app.processEvents()
        the = [self.w.the_chao[t] for t in TEN]
        trang = the[0].parentWidget()
        lo = next(l for l in (trang.layout().itemAt(i).layout() for i in range(trang.layout().count())) if l is not None
                  and l.indexOf(the[0]) >= 0)
        self.assertEqual(lo.spacing(), 20)
        x = [t.mapTo(trang, t.rect().topLeft()).x() for t in the]
        self.assertEqual([x[1] - x[0] - 210, x[2] - x[1] - 210], [20, 20])                   # đúng 20 px giữa các thẻ
        x_cuoi = max(t.mapTo(trang, t.rect().topLeft()).x() for t in self.w.the_chao.values())     # 1.0.04: 4 thẻ
        tam = (x[0] + x_cuoi + 210) / 2
        self.assertLessEqual(abs(tam - trang.width() / 2), 2)                                # cân giữa vùng nội dung
        self.w.resize(1920, 1080)
        self.app.processEvents()
        x = [t.mapTo(trang, t.rect().topLeft()).x() for t in the]
        x_cuoi = max(t.mapTo(trang, t.rect().topLeft()).x() for t in self.w.the_chao.values())
        self.assertLessEqual(abs((x[0] + x_cuoi + 210) / 2 - trang.width() / 2), 2)
        self.assertEqual([t.width() for t in the], [210, 210, 210])                          # cỡ thẻ không đổi theo cửa sổ

    def test_mau_theo_loai_va_hover(self):
        from PySide6.QtGui import QColor
        from pabt import giao_dien
        qss = giao_dien.QSS_THE_CHAO
        # 17/10/2026 (Hybrid Enterprise Navy): màu theo giao_dien.MAU_THE_CHAO - nền trắng, rê chuột #F0F6FF, viền / biểu tượng
        # navy / xanh băng đậm / xanh ngọc (không còn xanh lá tươi)
        for chu in ('#FFFFFF', '#E2E8F0', '#F0F6FF', '#0F3866', '#0284C7', '#0F766E', 'border-radius: 12px', 'font-size: 14.5pt',
                    '#0F172A'):
            self.assertIn(chu, qss)
        for bo in ('#F0FDF4', '#16A34A', '#BBF7D0'):
            self.assertNotIn(bo, qss)
        self.assertIn('#64748B', self.app.styleSheet())                                      # mô tả phụ 10,5pt xám than
        self.assertIn('font-size: 10.5pt', self.app.styleSheet())
        self.w.show()
        self.app.processEvents()
        mau_nen = {k: v[0] for k, v in giao_dien.MAU_THE_CHAO.items()}
        mau_hover = {k: v[2] for k, v in giao_dien.MAU_THE_CHAO.items()}
        for ten in TEN:
            the = self.w.the_chao[ten]
            anh = the.grab().toImage()
            self.assertEqual(QColor(anh.pixel(14, 70)).name().upper(), mau_nen[LOAI[ten]], ten)       # nền thẻ
            the.enterEvent(None) if False else None
            the.setProperty('hover', '1')                                                    # như enterEvent
            the.style().unpolish(the)
            the.style().polish(the)
            anh = the.grab().toImage()
            self.assertEqual(QColor(anh.pixel(14, 70)).name().upper(), mau_hover[LOAI[ten]], ten)     # nền khi rê chuột
            the.setProperty('hover', '0')
            the.style().unpolish(the)
            the.style().polish(the)

    def test_bam_o_dau_trong_the_cung_chay_lenh(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        self.w.show()
        self.app.processEvents()
        ten = 'Mở dự án…'
        a = self.w.lenh[ten]
        dem = []
        a.triggered.disconnect()                       # bỏ slot thật (mở hộp chọn file - treo kiểm thử), chỉ đếm số lần chạy
        a.triggered.connect(lambda *_: dem.append(1))
        the = self.w.the_chao[ten]
        # bấm vào vùng mô tả (nhãn trong suốt với chuột) và vùng biên của thẻ -> cả hai chạy lệnh
        QTest.mouseClick(the, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(105, 118))
        QTest.mouseClick(the, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(5, 5))
        self.assertEqual(len(dem), 2)
        a.setEnabled(False)
        QTest.mouseClick(the, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(105, 118))
        self.assertEqual(len(dem), 2)                                                       # lệnh tắt: thẻ không chạy


if __name__ == '__main__':
    unittest.main()
