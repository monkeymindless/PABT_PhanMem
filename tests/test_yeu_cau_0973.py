"""0.9.73 (người dùng 13/10/2026): Đơn giá bồi thường gọn (dải thông tin 28 px, Cập nhật = nạp file / sao lưu, Quản trị bảo mật,
thêm / sửa / xóa ở chuột phải trên bảng, khôi phục bộ gốc); Đơn giá đặc biệt gọn (Lưu thay đổi, lưới 2 cột, nút trên cùng)."""
from __future__ import annotations
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from pabt import csdl, don_gia
from tests.test_toc_do import _du_an


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)


class _MenuGia:
    """QMenu giả: ghi các mục (chữ, bật) thay vì hiện menu thật (exec chặn kiểm thử)."""
    lan_cuoi = None

    def __init__(self, *_):
        self.muc = []
        _MenuGia.lan_cuoi = self

    def addAction(self, chu, ham=None):
        me = self

        class _A:
            def setEnabled(self, bat):
                me.muc[-1] = (chu, bat)
        self.muc.append((chu, True))
        return _A()

    def addSeparator(self):
        pass

    def exec(self, *_):
        pass

    def deleteLater(self):
        pass


class TestBoDonGia(_Co):
    def _hop(self):
        from pabt.man_hinh_don_gia import HopBoDonGia
        d = HopBoDonGia()
        d.im_lang = True
        self.addCleanup(d.close)
        return d

    def test_nut_va_dai_thong_tin(self):
        d = self._hop()
        self.assertEqual(d.lb.maximumHeight(), 28)
        self.assertIn('QĐ 42/2025', d.lb.text())                     # căn cứ của bộ đơn giá (số hiệu QĐ của UBND tỉnh)
        self.assertNotIn('Dự thảo', d.lb.text())
        self.assertIn('Khóa quản trị', d.lb.text())
        self.assertEqual([a.text() for a in d.b_qt.menu().actions() if a.text()],
                         ['Mở khóa quản trị (cho phép sửa / xóa)…', 'Đổi mật khẩu quản trị…',
                          'Khôi phục bộ đơn giá chuẩn gốc của Tỉnh…'])
        for ten in ('b_gia_dat', 'b_don', 'cap_nhat_web', 'xem_gia_dat', 'don_gia_rieng'):
            self.assertFalse(hasattr(d, ten), ten)                     # lệnh trùng menu trái / web không dùng được: bỏ

    def test_chuot_phai_tren_bang(self):
        d = self._hop()
        b = d.the.widget(0)
        with mock.patch('pabt.man_hinh_don_gia.QMenu', _MenuGia):
            d._menu_bang(b, QPoint(5, b.rowViewportPosition(0) + 3))
        muc = dict(_MenuGia.lan_cuoi.muc)
        self.assertEqual(list(muc)[:4], ['Thêm mục…', 'Sửa dòng đang chọn…', 'Thay thế dòng đang chọn…', 'Xóa dòng đang chọn…'])
        self.assertTrue(all(muc[k] for k in list(muc)[:4]))           # bấm trên một dòng: cả 4 mục bật
        self.assertIn('Mở khóa quản trị…', muc)
        # bấm chỗ không có dòng (rowAt = -1; chiều cao dòng tùy kiểu chữ đang áp nên không dựa vào hình học)
        with mock.patch('pabt.man_hinh_don_gia.QMenu', _MenuGia), mock.patch.object(b, 'rowAt', return_value=-1):
            d._menu_bang(b, QPoint(5, 5))                               # chỗ trống: chỉ Thêm mục bật
        muc = dict(_MenuGia.lan_cuoi.muc)
        self.assertTrue(muc['Thêm mục…'])
        self.assertFalse(muc['Xóa dòng đang chọn…'])

    def test_sao_luu_va_khoi_phuc(self):
        d = self._hop()
        f = d.sao_luu(self.td / 'sl.sqlite')
        con = sqlite3.connect(f)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM dm_taisan').fetchone()[0],
                         sqlite3.connect(don_gia.file_goc()).execute('SELECT COUNT(*) FROM dm_taisan').fetchone()[0])
        con.close()
        x = d.sao_luu(self.td / 'sl.xlsx')
        wb = openpyxl.load_workbook(x, read_only=True)
        self.assertIn('dm_taisan', wb.sheetnames)
        wb.close()
        # có bản máy (đã cập nhật / sửa) -> khôi phục bộ gốc: bản máy được cất lại, không xóa
        don_gia.dam_bao_ban_sua()
        self.assertTrue(don_gia.file_cap_nhat().exists())
        tt = d.khoi_phuc_goc(xac_nhan=True, mat_khau='matkhau123')
        self.assertIsNotNone(tt)
        self.assertFalse(don_gia.file_cap_nhat().exists())
        self.assertTrue(Path(tt['cat']).exists())
        self.assertEqual(don_gia.file_dang_dung().resolve(), don_gia.file_goc().resolve())


class TestDonGiaDacBiet(_Co):
    def test_bo_cuc_gon(self):
        from pabt.man_hinh_don_gia_rieng import HopDonGiaRieng
        p = _du_an(self.td, so_ho=2)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        h = HopDonGiaRieng(con, the=1)
        h.im_lang = True
        self.addCleanup(h.close)
        self.assertEqual(h.b_luu.text(), 'Lưu thay đổi')
        from pabt.giao_dien import KieuNut
        self.assertEqual(h.b_luu.property('bien_the'), KieuNut.LUU.value)       # xanh lá (nút lưu)
        self.assertFalse(h.b_luu.isEnabled())                         # chưa có thay đổi
        h.them_dong('Tài sản thử', dvt='cái', don_gia='1000')
        self.assertTrue(h.b_luu.isEnabled())
        # thẻ thẩm định: 6 trường lưới 2 cột; Chọn file + Đưa vào cùng hàng trên cùng (trên mọi ô nhập)
        tab = h.tab.widget(1)
        hang = lambda w: w.mapTo(tab, w.rect().center()).y()           # noqa: E731
        self.assertEqual(hang(h.o_so), hang(h.o_qd))
        self.assertEqual(hang(h.o_ngay), hang(h.o_can_cu))
        self.assertEqual(hang(h.o_don_vi), hang(h.o_ap_dung))
        self.assertLess(abs(hang(h.b_file) - hang(h.b_dua)), 4)
        self.assertLess(hang(h.b_dua), hang(h.o_so))
        h.bo_thay = None
        h.b_luu.setEnabled(False)                                       # đóng không hỏi lưu


if __name__ == '__main__':
    unittest.main()
