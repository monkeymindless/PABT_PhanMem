"""Bàn giao mặt bằng khi hộ chưa có quyết định phê duyệt (người dùng 17/10/2026: dự án 170 hộ hiện "Đã bàn giao MB" cả loạt dù chưa
hộ nào được phê duyệt - một lần chọn cả bảng, hộp Bàn giao tích sẵn). Hộp không tích sẵn + cảnh báo; Kiểm tra lỗi báo dữ liệu cũ.
Dữ liệu GIẢ LẬP (tests.test_toc_do._du_an)."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, kiem_loi, theo_doi  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


def _qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestBanGiaoChuaQD(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 4))
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.doCleanups()
        self.con.close()
        self.tmp.cleanup()

    def test_ho_chua_phe_duyet(self):
        self.assertEqual(theo_doi.ho_chua_phe_duyet(self.con, self.ma), self.ma)
        q = theo_doi.luu_qd(self.con, None, '9/QĐ-UBND', (date.today() - timedelta(days=5)).strftime('%d/%m/%Y'), 'Phê duyệt thử')
        theo_doi.them_ho_theo_pa(self.con, q, self.ma[:1])
        self.assertEqual(theo_doi.ho_chua_phe_duyet(self.con, self.ma), self.ma[1:])

    def test_kiem_tra_loi_bao_ban_giao_khi_chua_phe_duyet(self):
        theo_doi.ghi_ban_giao(self.con, self.ma, dict(da_ban_giao=True, ban_giao_ngay='16/10/2026'))
        loi = [x for x in kiem_loi.kiem_tra(self.con) if x.nhom == 'Tiến độ' and 'bàn giao' in x.noi_dung]
        self.assertEqual(sorted(x.ma_ho for x in loi), sorted(self.ma))
        self.assertTrue(all('chưa có quyết định phê duyệt' in x.noi_dung for x in loi))
        theo_doi.ghi_ban_giao(self.con, self.ma, dict(da_ban_giao=False))            # bỏ tích: về "chưa bàn giao"
        self.assertEqual(self.con.execute('SELECT SUM(da_ban_giao) FROM ho').fetchone()[0], 0)

    def test_hop_khong_tich_san_khi_chua_phe_duyet(self):
        _qt()
        from pabt.man_hinh_theo_doi import HopBanGiao, KhungTienDo
        d = HopBanGiao(None, 4, so_chua_qd=4)
        self.addCleanup(d.deleteLater)
        self.assertFalse(d.o_da.isChecked())
        self.assertFalse(d.lb_canh_bao.isHidden())
        self.assertIn('4/4 hộ chưa có quyết định phê duyệt', d.lb_canh_bao.text())
        self.assertFalse(d.gia_tri()['da_ban_giao'])
        d2 = HopBanGiao(None, 2)                                                     # hộ đã phê duyệt: tích sẵn như cũ
        self.addCleanup(d2.deleteLater)
        self.assertTrue(d2.o_da.isChecked())
        self.assertTrue(d2.lb_canh_bao.isHidden())
        k = KhungTienDo(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        nhan = {}

        class Gia:
            def __init__(self, cha, so_ho, so_chua_qd=0):
                nhan.update(so_ho=so_ho, so_chua_qd=so_chua_qd)

            def exec(self):
                return 0
        with mock.patch('pabt.man_hinh_theo_doi.HopBanGiao', Gia):
            self.assertEqual(k.ban_giao(self.ma), 0)
        self.assertEqual(nhan, dict(so_ho=4, so_chua_qd=4))


if __name__ == '__main__':
    unittest.main()
