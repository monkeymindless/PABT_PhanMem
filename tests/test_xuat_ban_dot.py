"""Xuất bản hồ sơ một chạm theo đợt trình (pabt/man_hinh_xuat_ban.HopXuatBanDot, phương án đột phá 6 - 30/10/2026): 4 bước, kiểm tra
đợt + cờ phễu của các hộ trong đợt, xem trước (danh sách file), xuất bản bằng HopIn.thuc_hien. Dự án GIẢ LẬP tests.test_toc_do._du_an;
xuất "Chỉ file Word / Excel" (không cần Microsoft Office)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, quan_ly  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class TestXuatBanDot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.p = _du_an(self.td, 4)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        self.dot = quan_ly.tao_dot(self.con, 'Đợt trình 1')
        quan_ly.gan_dot(self.con, self.ma[:3], self.dot)

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def hop(self, **k):
        from pabt.man_hinh_xuat_ban import HopXuatBanDot
        h = HopXuatBanDot(self.con, None, self.p, self.dot, **k)
        h.im_lang = True
        self.addCleanup(lambda: (h.done(0), h.deleteLater()))
        return h

    def test_buoc_va_chon_san_dot(self):
        h = self.hop()
        self.assertEqual(h.ngan.currentIndex(), 0)
        self.assertEqual(h.dot_chon().id, self.dot)
        self.assertEqual(h.ds_ho(), self.ma[:3])
        self.assertEqual(h.che_do(), 'chinh_thuc')
        self.assertEqual(h.nhan_buoc[0].property('dang'), '1')
        h.sang(1)
        self.assertEqual(h.nhan_buoc[0].property('xong'), '1')
        chu = [c for _m, c, _ho in h.kiem]
        self.assertIn('3 hộ trong đợt', chu)
        self.assertTrue(any('tự lập' in c for c in chu))              # cờ phễu của các hộ trong đợt
        self.assertTrue(h.b_tiep.isVisible() or not h.isVisible())

    def test_du_thao_khoa_to_trinh(self):
        h = self.hop(che_do='du_thao')
        h.sang(3)
        self.assertFalse(h.o_tt.isEnabled())
        self.assertFalse(h.o_bc.isChecked())
        self.assertIn(quan_ly.lay_dot(self.con, self.dot).ten_thu_muc, h.o_thu_muc.text())

    def test_xem_truoc_lap_du_file(self):
        h = self.hop()
        ds = h.tao_xem_truoc(self.td / 'xem')
        self.assertEqual(len(ds), 4)                                    # 3 phương án chi tiết + bảng tổng hợp
        self.assertTrue(all(Path(f).exists() for f, _ in ds))
        self.assertEqual(ds[-1][1], 'Bảng tổng hợp')

    def test_xuat_ban_chi_file(self):
        h = self.hop()
        h.sang(3)
        h.r_file.setChecked(True)
        h.o_thu_muc.setText(str(self.td / 'ho_so'))
        h.o_tt.setChecked(False)
        h.o_bc.setChecked(False)
        kq = h.xuat_ban(xac_nhan=False)
        self.assertIsNotNone(kq)
        self.assertEqual(len(kq['word']), 3)
        self.assertTrue(kq['excel'])
        self.assertFalse(kq['pdf'])
        self.assertTrue(h.lb_ket_qua.text().startswith('Đã xuất bản'))

    def test_chua_co_dot(self):
        quan_ly.xoa_dot(self.con, self.dot)
        h = self.hop()
        self.assertIsNone(h.dot_chon())
        h.sang(2)
        self.assertEqual(h.ngan.currentIndex(), 0)                      # chưa có đợt: không sang bước sau
        self.assertIsNone(h.xuat_ban(xac_nhan=False))


if __name__ == '__main__':
    unittest.main()
