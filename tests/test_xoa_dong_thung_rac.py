"""Bảng mục cửa sổ lập phương án (người dùng 18/10/2026): nút "Xóa dòng" thay bằng biểu tượng thùng rác ở cột cuối MỖI dòng - bấm là
xóa đúng dòng đó; vẫn còn phím Delete và mục Xóa dòng ở menu chuột phải. Dữ liệu GIẢ LẬP (tests.test_toc_do._du_an)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class TestThungRac(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 4))
        ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1 OFFSET 2').fetchone()[0]   # hộ thứ 3: 3 thửa
        from pabt import man_hinh
        self.mh = man_hinh
        self.w = man_hinh.CuaSoLapPA(self.con, ma)

    def tearDown(self):
        self.w.bo_thay_doi()
        self.w.close()
        self.w.deleteLater()
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def test_cot_thung_rac_moi_bang(self):
        from PySide6.QtCore import Qt
        for m, b in self.w.bang.items():
            self.assertNotIn('Xóa dòng', b.nut)                                   # bỏ nút
            self.assertEqual(b.bang.columnCount(), len(b.cot) + 1)
            self.assertEqual(b.c_xoa, len(b.cot))
            self.assertEqual(b.bang.horizontalHeaderItem(b.c_xoa).text(), '')
            self.assertEqual(b.bang.columnWidth(b.c_xoa), self.mh.RONG_COT_XOA)
            self.assertIsInstance(b.bang.itemDelegateForColumn(b.c_xoa), self.mh.NutXoaDong)
            for r in range(b.bang.rowCount()):
                it = b.bang.item(r, b.c_xoa)
                self.assertFalse(it.flags() & Qt.ItemFlag.ItemIsEditable)           # không sửa được ô thùng rác
                self.assertIn('Xóa dòng', it.toolTip())

    def test_bam_thung_rac_xoa_dung_dong(self):
        b = self.w.bang[1]
        n = len(self.w.bo.pa.dat)
        self.assertGreaterEqual(n, 2)
        thua = [d.ma_thua for d in self.w.bo.pa.dat]
        b.bang.selectAll()                                                       # đang chọn nhiều dòng: chỉ xóa dòng bấm
        b._bam_o(1, b.c_xoa)
        self.assertEqual([d.ma_thua for d in self.w.bo.pa.dat], thua[:1] + thua[2:])
        self.assertEqual(b.bang.rowCount(), n - 1)
        b._bam_o(0, 0)                                                           # bấm ô khác: không xóa
        self.assertEqual(len(self.w.bo.pa.dat), n - 1)
        b.bang.clearSelection()
        b.bang.setCurrentCell(0, 1)
        b._phim_xoa.activated.emit()                                             # phím Delete: dòng đang chọn
        self.assertEqual(len(self.w.bo.pa.dat), n - 2)

    def test_sua_o_thung_rac_khong_loi(self):
        b = self.w.bang[1]
        b._doi_o(0, b.c_xoa)                                                     # ngoài self.cot: bỏ qua, không IndexError
        self.assertEqual(len(self.w.bo.pa.dat), b.bang.rowCount())


if __name__ == '__main__':
    unittest.main()
