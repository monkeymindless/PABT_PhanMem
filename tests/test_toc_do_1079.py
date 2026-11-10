"""1.0.79 (người dùng 07/11/2026: gọi lệnh nhanh, không đơ, kể cả máy yếu): các chỗ đã tăng tốc phải cho kết quả GIỐNG HỆT cách cũ."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pabt  # noqa: E402,F401
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QComboBox, QCompleter, QVBoxLayout, QWidget  # noqa: E402
from pabt import csdl, giao_dien, theo_doi  # noqa: E402
from pabt.app import BangHo  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402

qa = QApplication.instance() or QApplication([])


class TestNapOChon(unittest.TestCase):
    def _o(self, sua=True):
        o = QComboBox()
        self.addCleanup(o.deleteLater)
        o.setEditable(sua)
        return o

    def test_giong_addItem(self):
        ds = [('Mọi hộ', None, ''), ('1. An', 11, '1. An là chủ sở hữu'), ('2. Bình', 12, '')]
        moi, cu = self._o(), self._o()
        giao_dien.nap_o_chon(moi, ds)
        for chu, ma, chu_thich in ds:
            cu.addItem(chu, ma)
            if chu_thich:
                cu.setItemData(cu.count() - 1, chu_thich, Qt.ItemDataRole.ToolTipRole)
        self.assertEqual(moi.count(), cu.count())
        self.assertEqual(moi.currentIndex(), 0)
        self.assertEqual(moi.currentText(), 'Mọi hộ')
        for i in range(cu.count()):
            self.assertEqual(moi.itemText(i), cu.itemText(i))
            self.assertEqual(moi.itemData(i), cu.itemData(i))
            self.assertEqual(moi.itemData(i, Qt.ItemDataRole.ToolTipRole), cu.itemData(i, Qt.ItemDataRole.ToolTipRole))
        self.assertEqual(moi.findData(12), 2)
        self.assertEqual(moi.findData(99), -1)

    def test_nap_lai_thay_het_va_o_dung_duoc(self):
        o = self._o()
        giao_dien.nap_o_chon(o, [('A', 1, ''), ('B', 2, '')])
        giao_dien.nap_o_chon(o, [('C', 3, '')])
        self.assertEqual((o.count(), o.itemText(0), o.itemData(0)), (1, 'C', 3))
        giao_dien.nap_o_chon(o, [])
        self.assertEqual(o.count(), 0)
        o.addItem('D', 4)                       # sau khi thay mô hình vẫn thêm mục theo cách thường được
        self.assertEqual(o.itemData(0), 4)

    def test_chon_bang_chu_trong_o_sua_duoc_van_theo_mo_hinh_moi(self):
        o = self._o()
        o.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        o.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        giao_dien.nap_o_chon(o, [('1. Nguyễn An', 1, ''), ('2. Trần Bình', 2, '')])
        c = o.completer()
        self.assertIs(c.model().__class__, o.model().__class__)
        self.assertEqual(c.filterMode(), Qt.MatchFlag.MatchContains)    # tìm theo chữ giữa tên (màn hình giá đất) không mất
        c.setCompletionPrefix('Bình')
        self.assertEqual(c.currentCompletion(), '2. Trần Bình')

    def test_tin_hieu_doi_muc_van_chay_khi_chon(self):
        o = self._o(False)
        giao_dien.nap_o_chon(o, [('A', 1, ''), ('B', 2, '')])
        nhan = []
        o.currentIndexChanged.connect(nhan.append)
        o.setCurrentIndex(1)
        self.assertEqual(nhan, [1])

    def test_mo_danh_sach_xo_khong_loi(self):
        cha = QWidget()
        self.addCleanup(cha.deleteLater)
        o = QComboBox(cha)
        QVBoxLayout(cha).addWidget(o)
        giao_dien.nap_o_chon(o, [(f'{i}. Hộ', i, '') for i in range(50)])
        cha.show()
        o.showPopup()
        qa.processEvents()
        self.assertTrue(o.view().isVisible())
        o.hidePopup()
        cha.hide()


class TestBangHo(unittest.TestCase):
    def setUp(self):
        self.m = BangHo([dict(ma_ho=7, o=[7, 'An', 'Ấp 1', 2, '12,5', 'Đã lập', 'ghi', *[''] * 11], tim='', nac=1, phu_ten='', ten_gon='An')])

    def test_vai_tro_khong_dung_tra_none_ngay(self):
        i = self.m.index(0, 1)
        for vai in (Qt.ItemDataRole.DecorationRole, Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.SizeHintRole, Qt.ItemDataRole.StatusTipRole):
            self.assertIsNone(self.m.data(i, vai), vai)

    def test_vai_tro_dung_van_tra_du(self):
        i = self.m.index(0, 1)
        self.assertEqual(self.m.data(i), 'An')                                         # mặc định: chữ hiện
        self.assertEqual(self.m.data(i, Qt.ItemDataRole.DisplayRole), 'An')           # enum cũng được (test, mã khác gọi thẳng)
        self.assertEqual(self.m.data(i, int(Qt.ItemDataRole.DisplayRole)), 'An')      # Qt gọi bằng số
        self.assertIn('Mã hộ 7', self.m.data(i, Qt.ItemDataRole.ToolTipRole))
        self.assertEqual(self.m.data(self.m.index(0, 0), Qt.ItemDataRole.UserRole), 7.0)
        self.assertIsNotNone(self.m.data(i, Qt.ItemDataRole.FontRole))
        self.assertIsNotNone(self.m.data(i, Qt.ItemDataRole.ForegroundRole))
        self.assertIsNotNone(self.m.data(i, Qt.ItemDataRole.TextAlignmentRole))
        self.assertIsNone(self.m.data(self.m.index(0, 2), Qt.ItemDataRole.FontRole))
        self.assertIn('Đã lập', self.m.data(self.m.index(0, 5)))


class TestTongHop(unittest.TestCase):
    def test_ban_co_tien_giong_tinh_rieng_va_khong_sua_ban_nho(self):
        with tempfile.TemporaryDirectory() as td:
            con = csdl.mo(str(_du_an(Path(td), 30)))
            try:
                khong = theo_doi.tong_hop(con, tinh_pa=False)
                co = theo_doi.tong_hop(con, tinh_pa=True)
                rieng = theo_doi._tong_hop(con, None, True)
                self.assertEqual([x.__dict__ for x in co], [x.__dict__ for x in rieng])
                self.assertEqual([x.__dict__ for x in theo_doi.tong_hop(con, tinh_pa=False)], [x.__dict__ for x in theo_doi._tong_hop(con, None, False)])
                self.assertEqual(len(khong), 30)
                self.assertTrue(any(x.tong_pa for x in co))
                self.assertFalse(any(x.tong_pa for x in khong))       # đối tượng đang nhớ của bản không tiền không bị ghi đè
            finally:
                con.close()


class TestCotThongSoGiaDat(unittest.TestCase):
    def test_man_hinh_thap_khong_cat_chu(self):
        from PySide6.QtWidgets import QScrollArea
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        from pabt import giao_dien                   # 1.0.93: đo trong trạng thái sạch - bài khác để lại bảng kiểu + bộ tô màu (thêm biểu
        if getattr(qa, '_bo_to_mau', None) is not None:  # tượng vào nút) làm số đo đổi theo thứ tự chạy; trả lại sau bài
            giao_dien.bo_ap_dung(qa)
            self.addCleanup(giao_dien.ap_dung, qa)
        elif qa.styleSheet():
            cu = qa.styleSheet()
            qa.setStyleSheet('')
            self.addCleanup(qa.setStyleSheet, cu)
        h = HopTinhGiaDat()
        self.addCleanup(h.deleteLater)
        h.show()
        h.setMinimumSize(1093, 614)
        h.resize(1093, 614)
        qa.processEvents()
        qa.processEvents()
        cuon = h.findChildren(QScrollArea)[0]
        self.assertGreaterEqual(cuon.viewport().width(), cuon.widget().minimumSizeHint().width())
        self.assertLess(cuon.width(), h.width() * 0.48)            # bảng dòng đất bên phải vẫn rộng hơn
        h.hide()


if __name__ == '__main__':
    unittest.main()
