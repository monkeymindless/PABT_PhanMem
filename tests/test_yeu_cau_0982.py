"""0.9.82 (người dùng 14/10/2026): MỘT bộ mẫu in cho hai chế độ phát hành - chữ DỰ THẢO do chế độ quyết định, không do tên file mẫu.
Bản DỰ THẢO: mẫu đã có dòng DỰ THẢO thì giữ, chưa có thì tự thêm (dưới "Số:" / cuối tiêu đề bảng tổng hợp), chưa ghi số phương án.
Bản CHÍNH THỨC: xóa chữ DỰ THẢO của mẫu. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an
from tests.test_toc_do import _du_an

MAU = Path(__file__).resolve().parents[1] / 'mau_in'


def _chu(p) -> str:
    ws = openpyxl.load_workbook(p).worksheets[0]
    return ' '.join(str(c.value) for r in ws.iter_rows(max_row=12) for c in r if isinstance(c.value, str))


class TestMotBoMau(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])          # in_an đo chữ bằng Qt

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.con = csdl.mo(_du_an(self.d, 3))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
        with self.con:
            self.con.execute("UPDATE ho SET so_pa = '07' WHERE ma_ho = ?", (self.ma[0],))

    def _mau_co_dong_du_thao(self) -> Path:
        """Mẫu chính kiểu của người dùng: có sẵn dòng "(DỰ THẢO)" dưới "Số:" (tên file là mẫu chính, không phải mẫu dự thảo)."""
        d = self.d / 'mau_nguoi_dung'
        d.mkdir()
        wb = openpyxl.load_workbook(MAU / 'IN_CHITIET.xlsx')
        wb.worksheets[0]['A3'] = 'Số:            /{ky_hieu_so}\n(DỰ THẢO)'
        f = d / 'IN_CHITIET.xlsx'
        wb.save(f)
        self.assertFalse(in_an.la_mau_du_thao(f))
        return f


    def test_hop_in_khong_con_bao_thieu_mau_du_thao(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, che_do='du_thao', ma_ho_chon=self.ma[:1])
        self.addCleanup(h.close)
        self.assertIsNone(h.khoa_xem_truoc()[2])                               # mẫu chính cho cả hai chế độ
        self.assertIn('(DỰ THẢO)', h.r_du_thao.toolTip())                      # mô tả chế độ ở chú thích (16/10/2026)
        h.r_chinh_thuc.setChecked(True)
        self.assertIn('KHÔNG có chữ', h.r_chinh_thuc.toolTip())
        self.assertIsNone(h.khoa_xem_truoc()[2])


class TestLocKhiNgungGo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_slot_co_va_khong_tham_so_dat_bang_ma_loc_ngay(self):
        from PySide6.QtWidgets import QLineEdit
        from pabt.giao_dien import loc_khi_ngung_go
        nhan, khong = [], []
        o1, o2 = QLineEdit(), QLineEdit()
        loc_khi_ngung_go(o1, lambda chu: nhan.append(chu))
        loc_khi_ngung_go(o2, lambda: khong.append(1))                     # như HopTraGiaDat.ve(self): không tham số
        o1.setText('bau ham')
        o2.setText('x')
        self.assertEqual((nhan, khong), (['bau ham'], [1]))              # không có con trỏ (đặt bằng mã): lọc ngay
        self.assertTrue(o1.isClearButtonEnabled())

    def test_dang_go_thi_cho(self):
        from unittest import mock
        from PySide6.QtWidgets import QLineEdit
        from pabt.giao_dien import loc_khi_ngung_go
        nhan = []
        o = QLineEdit()
        hen = loc_khi_ngung_go(o, nhan.append)
        with mock.patch.object(o, 'hasFocus', return_value=True):         # người dùng đang gõ trong ô
            o.setText('d')
            o.setText('dư')
        self.assertEqual(nhan, [])                                       # chưa lọc
        self.assertTrue(hen.isActive())
        hen.timeout.emit()                                               # ngừng gõ 200 ms
        self.assertEqual(nhan, ['dư'])


if __name__ == '__main__':
    unittest.main()
