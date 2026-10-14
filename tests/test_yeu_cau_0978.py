"""0.9.78 (người dùng 13/10/2026): nút "Dán danh sách tài sản… (Ctrl+Shift+V)" ở cửa sổ lập phương án hộ - nút nổi bật, phím tắt, tự điền
và Phân loại khi bộ nhớ đệm (clipboard) có bảng tài sản. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_toc_do import _du_an

BANG = 'Nhà cấp 4 mái tôn\tm2\t45\nGà ta\tcon\t40'


class TestDanTaiSanTuClipboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from pabt import app as ud
        from pabt import csdl
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        p = _du_an(Path(self.tmp.name), 3)
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(self.w.close)
        self.w.mo(str(p))
        self.lp = self.w.mo_lap_pa(cho=False)
        self.addCleanup(self.lp.bo_thay_doi)
        self.assertTrue(csdl is not None)

    def _hop(self, **kw):
        hop = self.lp.mo_dan_tai_san(cho=False, **kw)
        self.addCleanup(hop.deleteLater)
        hop.im_lang = True
        return hop

    def test_nut_noi_bat_va_phim_tat(self):
        from PySide6.QtGui import QKeySequence, QShortcut
        b = self.lp.b_dan
        self.assertIs(b, self.lp.btn_dan_ts)
        self.assertEqual(b.objectName(), 'btn_dan_ts')
        self.assertIn('Dán danh sách tài sản', b.text())
        self.assertIn('Ctrl+Shift+V', b.text())
        self.assertEqual(b.height() or b.minimumHeight(), 32)
        qss = b.styleSheet()
        for mau in ('#0284C7', '#0369A1', '#FFFFFF', 'border-radius: 6px', 'font-weight: 700'):
            self.assertIn(mau, qss)
        # phím tắt Ctrl+Shift+V gọi mo_dan_tai_san
        phim = [s for s in self.lp.findChildren(QShortcut) if s.key() == QKeySequence('Ctrl+Shift+V')]
        self.assertEqual(len(phim), 1)
        with mock.patch.object(self.lp, 'mo_dan_tai_san') as m:
            phim[0].activated.emit()
            b.click()
        self.assertEqual(m.call_count, 2)

    def test_dien_san_va_phan_loai_khi_clipboard_co_bang(self):
        hop = self._hop(clip=BANG)
        self.assertEqual(hop.o_chu.toPlainText(), BANG)
        self.assertEqual(len(hop.ds), 2)                    # đã tự bấm Phân loại
        self.assertEqual(hop.bang.rowCount(), 2)

    def test_clipboard_that_cua_windows(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText('  ' + BANG + '\n  ')
        hop = self._hop()                                   # không truyền clip: đọc QApplication.clipboard()
        self.assertEqual(len(hop.ds), 2)

    def test_clipboard_khong_phai_bang_thi_mo_hop_trong(self):
        for clip in ('', '   ', 'abc', 'Nhà cấp 4 mái tôn m2 45', 'x\ty', 'a' * 300):     # ngắn / một dòng không Tab
            hop = self._hop(clip=clip)
            self.assertEqual(hop.o_chu.toPlainText(), '', clip[:20])
            self.assertEqual(hop.ds, [])
        from pabt import man_hinh
        qua_dai = ('Nhà cấp 4\tm2\t1\n') * (man_hinh.CLIP_TOI_DA // 10)
        self.assertGreater(len(qua_dai), man_hinh.CLIP_TOI_DA)
        self.assertEqual(self._hop(clip=qua_dai).o_chu.toPlainText(), '')                  # cả một tài liệu: không tự điền

    def test_them_vao_phuong_an_va_tinh_lai_tong(self):
        from pabt.nghiep_vu import MUC_KHOAN
        hop = self._hop(clip=BANG)
        truoc = sum(len(self.lp.bo.pa.khoan[m]) for m in MUC_KHOAN)
        with mock.patch.object(self.lp, 'cap_nhat', wraps=self.lp.cap_nhat) as cn:
            n = hop.them()
        self.assertEqual(n, 2)
        self.assertEqual(sum(len(self.lp.bo.pa.khoan[m]) for m in MUC_KHOAN), truoc + 2)
        cn.assert_called()                                  # tổng tiền phương án tính lại ngay
        self.assertIn('Đã thêm 2 dòng', self.lp.lb_tb.text())


if __name__ == '__main__':
    unittest.main()
