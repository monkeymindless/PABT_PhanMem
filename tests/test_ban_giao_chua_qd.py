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


class TestPhanTichTienDo(TestBanGiaoChuaQD):
    """Thanh 4 nấc tự động, tuần tự (theo_doi.phan_tich_tien_do): phê duyệt theo quyết định, chi trả khi mọi QĐ đã nhận tiền, bàn
    giao khi có NGÀY biên bản (biên bản không có số; file scan không bắt buộc); tích tay thiếu bước / thiếu ngày không tăng nấc mà ghi
    điểm cần xem lại."""

    def _x(self, ma):
        return next(x for x in theo_doi.tong_hop(self.con, tinh_pa=False) if x.ma_ho == ma)

    def test_tung_buoc(self):
        a, b = self.ma[:2]
        theo_doi.ghi_ban_giao(self.con, [a], dict(da_ban_giao=True))                   # tích, không ngày biên bản
        td = self._x(a).tien_do
        self.assertEqual((td.nac, td.da_pd, td.da_bg), (1, False, False))              # tích tay khi chưa phê duyệt: nấc lập PA
        self.assertIn('chưa phê duyệt', td.canh_bao)
        self.assertIn('chưa có ngày biên bản', td.canh_bao)
        theo_doi.ghi_ban_giao(self.con, [b], dict(da_ban_giao=True, ban_giao_ngay='16/10/2026'))   # có ngày nhưng chưa phê duyệt
        self.assertEqual(self._x(b).tien_do.nac, 1)
        self.assertEqual(self._x(b).tien_do.canh_bao, 'đã tích bàn giao, chưa phê duyệt')
        theo_doi.ghi_ban_giao(self.con, [b], dict(da_ban_giao=False))
        self.assertIn('đã tích bàn giao', self._x(a).trang_thai)
        q = theo_doi.luu_qd(self.con, None, '9/QĐ-UBND', '01/10/2026', 'Phê duyệt thử')
        theo_doi.them_ho_theo_pa(self.con, q, [a, b])
        self.assertEqual(self._x(b).tien_do.nac, 4)                                     # có quyết định -> nấc phê duyệt (B9–11)
        self.assertTrue(self._x(b).trang_thai.startswith('Đã phê duyệt'))
        theo_doi.ghi_chi_tra(self.con, [(q, a), (q, b)], '05/10/2026', '')
        self.assertEqual(self._x(b).tien_do.nac, 5)                                     # nhận đủ tiền -> nấc chi trả (B12–14)
        td = self._x(a).tien_do
        self.assertEqual(td.nac, 5)                                                     # đã tích nhưng chưa có ngày biên bản
        self.assertEqual(td.canh_bao, 'đã tích bàn giao, chưa có ngày biên bản')
        theo_doi.ghi_ban_giao(self.con, [a], dict(da_ban_giao=True, ban_giao_ngay='16/10/2026'))   # ngày biên bản, không file
        td = self._x(a).tien_do
        self.assertEqual((td.nac, td.da_bg, td.canh_bao), (6, True, ''))
        self.assertEqual(self._x(a).trang_thai, 'Đã bàn giao MB')

    def test_bien_ban_chung_nhieu_ho(self):
        _qt()
        from pabt.man_hinh_theo_doi import HopBanGiao
        d = HopBanGiao(None, 3)
        self.addCleanup(d.deleteLater)
        self.assertTrue(d.nhieu_ho)
        self.assertFalse(d.lb_chung.isHidden())                                        # nhắc: một file cho cả 3 hộ
        self.assertNotIn('bien_ban_ban_giao', d.gia_tri())                               # để trống: giữ file riêng từng hộ
        self.assertEqual(d.o_ngay.text(), '')                                           # không điền sẵn ngày hôm nay
        d.o_da.setChecked(True)
        d.accept()                                                                      # tích mà chưa có ngày biên bản: không đóng
        self.assertIn('ngày biên bản', d.lb_canh_bao.text())
        self.assertNotEqual(d.result(), 1)
        a, b = self.ma[:2]
        theo_doi.ghi_ban_giao(self.con, [a], dict(bien_ban_ban_giao='C:/BB/ho_a.pdf'))
        theo_doi.ghi_ban_giao(self.con, [a, b], d.gia_tri())
        self.assertEqual(self._x(a).bien_ban_ban_giao, 'C:/BB/ho_a.pdf')
        d.o_file.setText('C:/BB/bien_ban_chung.pdf')
        theo_doi.ghi_ban_giao(self.con, [a, b], d.gia_tri())                             # một đường dẫn cho mọi hộ, không chép file
        self.assertEqual({self._x(m).bien_ban_ban_giao for m in (a, b)}, {'C:/BB/bien_ban_chung.pdf'})
        d1 = HopBanGiao(None, 1)
        self.addCleanup(d1.deleteLater)
        self.assertFalse(d1.nhieu_ho)
        self.assertIn('bien_ban_ban_giao', d1.gia_tri())


if __name__ == '__main__':
    unittest.main()
