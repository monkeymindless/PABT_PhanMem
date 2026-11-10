"""Thẻ Niêm yết công khai (06/11/2026, người dùng): hai bảng con thay thanh ngăn kéo, mỗi bảng trọn chiều cao; nút theo bảng đang mở; thẻ KPI mở đúng bảng; bề rộng cột. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import unittest

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QHeaderView, QSplitter

from pabt import du_thao
from tests.test_giao_dien_navy import CoNavy

CO_PHONG = os.path.isdir(r'C:\Windows\Fonts')
NUT_NY = ('b_van_ban', 'b_doc_kq', 'b_quet_ny')
NUT_VM = ('Đánh dấu pháp lý hộ đang chọn', 'Xuất danh sách đôn đốc V1, V2')


@unittest.skipUnless(CO_PHONG, 'cần phông Windows để đo bề rộng chữ thật')
class TestBangCon(CoNavy):
    def _khung(self, rong=1366):
        ud, w = self._cua_so()
        w.resize(rong, 760)
        w.mo_du_thao()
        self.app.processEvents()
        k = w.khung_tab.widget['du_thao']
        self.app.processEvents()
        return k

    def _hien(self, k, ds):
        return [x.isVisibleTo(k) for x in ds]

    def _du_nut(self, k):
        return [getattr(k, t) for t in NUT_NY], [k._nut[t] for t in NUT_VM]

    def test_khong_con_thanh_ngan_mac_dinh_bang_1(self):
        k = self._khung()
        self.assertFalse(k.tabs.widget(0).findChildren(QSplitter))
        self.assertFalse(hasattr(k, 'tach'))
        self.assertIs(k.ngan_ny.currentWidget(), k.trang_ny)
        self.assertTrue(k.nut_bang_con[0].isChecked())
        self.assertIn('DS hộ niêm yết trong đợt', k.nut_bang_con[0].toolTip())
        from PySide6.QtWidgets import QLabel
        self.assertFalse([x for x in k.findChildren(QLabel) if 'thanh ngăn' in x.text()])

    def test_bang_trong_chiem_tron_chieu_cao(self):
        k = self._khung()
        bao = k.tabs.currentWidget()
        for i, bang in enumerate((k.bang_ny, k.bang_vm)):
            k.nut_bang_con[i].click()
            self.app.processEvents()
            self.assertGreater(bang.height(), bao.height() - k._goc_nut.height() - 16)

    def test_nut_theo_bang_dang_mo(self):
        k = self._khung()
        ny, vm = self._du_nut(k)
        self.assertEqual(self._hien(k, ny + vm), [True] * 3 + [False] * 2)
        k.nut_bang_con[1].click()
        self.app.processEvents()
        self.assertIs(k.ngan_ny.currentWidget(), k.trang_vm)
        self.assertEqual(self._hien(k, ny + vm), [False] * 3 + [True] * 2)
        k.tabs.setCurrentIndex(1)                                       # thẻ khác: không có nút bảng con, Văn bản hiện lại
        self.app.processEvents()
        self.assertFalse(k.khoi_bang_con.isVisibleTo(k))
        self.assertTrue(k.b_van_ban.isVisibleTo(k))
        self.assertEqual(self._hien(k, vm), [False, False])
        k.tabs.setCurrentIndex(0)                                       # về thẻ 1: vẫn ở bảng con đang mở
        self.app.processEvents()
        self.assertEqual(self._hien(k, ny + vm), [False] * 3 + [True] * 2)

    def test_the_kpi_mo_dung_bang(self):
        k = self._khung()
        k.tabs.setCurrentIndex(2)
        k.the['vuong']._bam()
        self.app.processEvents()
        self.assertEqual(k.tabs.currentIndex(), 0)
        self.assertIs(k.ngan_ny.currentWidget(), k.trang_vm)
        self.assertTrue(k.nut_bang_con[1].isChecked())
        for ten in ('dt', 'du'):
            k.nut_bang_con[1].click()
            k.tabs.setCurrentIndex(3)
            k.the[ten]._bam()
            self.app.processEvents()
            self.assertEqual(k.tabs.currentIndex(), 0)
            self.assertIs(k.ngan_ny.currentWidget(), k.trang_ny, ten)
            self.assertTrue(k.nut_bang_con[0].isChecked())

    def test_so_ho_va_canh_bao(self):
        k = self._khung()
        k.bang_vm.setRowCount(0)
        k._ve_nut_bang_con()
        self.assertIn('(0)', k.nut_bang_con[1].text())
        self.assertEqual(k.nut_bang_con[1].property('canh_bao'), '0')
        k.bang_vm.setRowCount(2)
        k._ve_nut_bang_con()
        self.assertIn('(2)', k.nut_bang_con[1].text())
        self.assertEqual(k.nut_bang_con[1].property('canh_bao'), '1')

    def test_cot_bang_ho_niem_yet(self):
        k = self._khung(1600)
        dot = du_thao.tao_dot(k.con, 'Đợt thử', '01/11/2026', 'Trụ sở UBND xã rất dài để cần chú thích đầy đủ')
        du_thao.them_thu_cong(k.con, dot, [r[0] for r in k.con.execute('SELECT ma_ho FROM ho LIMIT 3')], ca_vuong=True)
        k.nap()
        k.cb.setCurrentIndex(k.cb.findData(dot))
        self.app.processEvents()
        b, hd = k.bang_ny, k.bang_ny.horizontalHeader()
        self.assertEqual(b.columnWidth(0), 48)
        self.assertEqual(hd.sectionResizeMode(0), QHeaderView.ResizeMode.Fixed)
        self.assertEqual(hd.sectionResizeMode(1), QHeaderView.ResizeMode.Stretch)
        self.assertEqual((b.columnWidth(2), b.columnWidth(3), b.columnWidth(5)), (125, 130, 240))
        self.assertGreaterEqual(b.columnWidth(4), 135)
        self.assertGreater(b.rowCount(), 0)
        for c in (0, 2, 3):
            self.assertTrue(b.item(0, c).textAlignment() & int(Qt.AlignmentFlag.AlignHCenter), c)
        self.assertTrue(b.item(0, 4).textAlignment() & int(Qt.AlignmentFlag.AlignRight))
        self.assertTrue(b.item(0, 4).font().bold())
        for c in (1, 3, 5):
            self.assertEqual(b.item(0, c).toolTip(), b.item(0, c).text())
        self.assertIn(f'({b.rowCount()})', k.nut_bang_con[0].text())

    def test_hang_nut_khong_tran_o_cua_so_hep(self):
        k = self._khung(1920)
        cua = k.window()
        for rong in (1024, 1093, 1366, 1920):
            cua.resize(rong, 700)
            self.app.processEvents()
            for i in range(2):
                k.nut_bang_con[i].click()
                self.app.processEvents()
                self.assertLessEqual(k._goc_nut.minimumSizeHint().width(), k.tabs.currentWidget().width(), f'{rong}, bảng con {i}')
                for b in k.nut_bang_con:                                # chữ đậm của nút đang chọn không bị cắt (ký tự cuối ")")
                    f = QFont(b.font())
                    f.setPixelSize(12)
                    f.setBold(True)
                    self.assertGreaterEqual(b.width(), QFontMetrics(f).horizontalAdvance(b.text()) + 40, f'{rong}: {b.text()}')

    def test_chi_doc_tat_nut_danh_dau(self):
        k = self._khung()
        from pabt.man_hinh_du_thao import KhungDuThao
        c = KhungDuThao(k.con, None, chi_doc=True)
        self.addCleanup(c.deleteLater)
        self.assertFalse(c._nut[NUT_VM[0]].isEnabled())
        self.assertTrue(c._nut[NUT_VM[1]].isEnabled())
