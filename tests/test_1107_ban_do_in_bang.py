"""1.1.07 - bản đồ: bỏ nhãn tên CAD tự sinh ("Style14"), bỏ gắn hộ / đặt lại / xóa ô thửa; cây trồng: bậc đầu "(d <3 cm)" = ≤3; bản in
Word: khoảng trống ký tên, quốc hiệu / tiêu ngữ một dòng, cột nhãn mục I; bảng: lọc nhanh, xóa nội dung ô."""
from __future__ import annotations

import unittest
from decimal import Decimal as D

from pabt import ban_do_cad, ban_do_kml, cay_trong as ct, ho_so
from pabt.lap_pa import LoiNhap
from pabt.nhap_don_gia import chuan_duong_kinh
from tests import test_ban_do_cong_cu as _bd                   # nhập module (nhập tên lớp test thì discover chạy lại lớp đó)


class TestDuongKinhBacDau(unittest.TestCase):
    def test_bang_bien_thuoc_bac_dau(self):
        k = ct.khoang_duong_kinh('Dó bầu (Trầm hương) (d <3 cm)')
        self.assertTrue(k.chua(D(3)))                                       # trước: d = 3 cm lọt khe giữa hai bậc
        self.assertFalse(ct.khoang_duong_kinh('Dó bầu (Trầm hương) (d >3-6 cm)').chua(D(3)))
        self.assertTrue(ct.khoang_duong_kinh('Keo lai (d ≤5 cm)').chua(D(5)))
        self.assertEqual(ct.mo_ta_chu_vi('Keo lai (d <5 cm)'), 'chu vi ≤ 15,7 cm')
        self.assertEqual(chuan_duong_kinh('<3'), '(d ≤3 cm)')               # bản scan mất nét gạch của ≤
        self.assertEqual(chuan_duong_kinh('≤ 5'), '(d ≤5 cm)')
        self.assertEqual(chuan_duong_kinh('>3 - 6'), '(d >3-6 cm)')

    def test_bo_don_gia_tich_hop(self):
        import sqlite3
        from pabt import don_gia
        c = sqlite3.connect(f'file:{don_gia.file_goc().as_posix()}?mode=ro', uri=True)
        try:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM dm_taisan WHERE ten LIKE '%(d <%'").fetchone()[0], 0)
            self.assertEqual(c.execute("SELECT ten FROM dm_taisan WHERE ma = 'CT629'").fetchone()[0], 'Dó bầu (Trầm hương) (d ≤3 cm)')
        finally:
            c.close()


class TestNhanTuSinh(unittest.TestCase):
    def test_ten_style(self):
        for x in ('Style1', 'Style14', 'style 15', 'Placemark 3', 'Polygon_001', 'Cell-2'):
            self.assertEqual(ban_do_kml.loai_nhan(x), 'ky_hieu', x)
        self.assertEqual(ban_do_kml.loai_nhan('12'), 'thua')
        self.assertEqual(ban_do_kml.loai_nhan('Đường bê tông'), 'ghi_chu')


class TestBoGanHo(_bd._Co):
    def test_bo_gan_ho_va_dat_lai(self):
        h = self._mo()
        self.assertTrue(h.gan_ho(self._it(h, '2').t, ma_ho=3))
        t = self._it(h, '2').t
        self.assertEqual(t.ma_ho, 3)
        self.assertTrue(h.bo_gan_ho(t, xac_nhan=True))
        self.assertIsNone(self._it(h, '2').t.ma_ho)                         # về "Chưa gắn hộ"
        self.assertIsNone(self.con.execute("SELECT 1 FROM thua WHERE so_to = '5' AND so_thua = '2'").fetchone())
        self.assertTrue(any('Bỏ gắn hộ' in str(tuple(r)) for r in self.con.execute('SELECT * FROM nhat_ky ORDER BY rowid DESC LIMIT 3')))

    def test_luu_roi_dat_lai_xoa_o(self):
        h = self._mo()
        h.khung_nhap.luu()
        h.nap(doc_lai=True)
        ds = {(t.so_to, t.so_thua) for t in ban_do_cad.doc_ban_do(self.con)}
        self.assertIn(('5', '4'), ds)
        ban_do_cad.dat_mau_thua(self.con, '5', '4', '#DC2626')
        ban_do_cad.sua_thua_ban_do(self.con, '5', '4', dict(ghi_chu='Ranh tạm; chờ đo lại'))
        t = next(x for x in ban_do_cad.doc_ban_do(self.con) if x.so_thua == '4')
        self.assertEqual((t.mau, t.chi_tiet.get('ghi_chu')), ('#DC2626', ['Ranh tạm', 'chờ đo lại']))
        ban_do_cad.dat_lai_thua_ban_do(self.con, '5', '4')
        t = next(x for x in ban_do_cad.doc_ban_do(self.con) if x.so_thua == '4')
        self.assertEqual((t.mau, t.chi_tiet.get('ghi_chu')), ('', None))
        ban_do_cad.xoa_thua_ban_do(self.con, '5', '4')
        self.assertNotIn(('5', '4'), {(t.so_to, t.so_thua) for t in ban_do_cad.doc_ban_do(self.con)})
        with self.assertRaises(LoiNhap):
            ban_do_cad.xoa_thua_ban_do(self.con, '5', '4')

    def test_thua_co_dong_boi_thuong_khong_bo(self):
        r = self.con.execute('SELECT t.ma_thua FROM thua t WHERE t.ma_thua IN (SELECT ma_thua FROM ct_dat WHERE ma_thua IS NOT NULL) '
                             'LIMIT 1').fetchone()
        if r is None:
            self.skipTest('dự án mẫu không có dòng bồi thường đất gắn thửa')
        with self.assertRaises(LoiNhap):
            ho_so.bo_thua(self.con, r[0])
        self.assertIsNotNone(self.con.execute('SELECT 1 FROM thua WHERE ma_thua = ?', (r[0],)).fetchone())

    def test_menu_va_nut(self):
        h = self._mo()
        h.gan_ho(self._it(h, '2').t, ma_ho=3)
        t = self._it(h, '2').t
        chu = [a.text() for a in h.menu_cho_thua(t).actions()]
        for x in ('Bỏ gắn hộ (về Chưa gắn hộ)…', 'Đặt lại thửa (bỏ hộ, màu, ghi chú)…', 'Xóa ô thửa khỏi bản đồ…'):
            self.assertIn(x, chu)
        h._bam_thua(t)
        self.assertTrue(h.khung_tt.b_xoa_gan.isEnabled())
        self.assertTrue(h.khung_tt.b_xoa_o.isEnabled())
        from pabt.man_hinh_ban_do_cong_cu import HopSuaThua
        d = HopSuaThua(t, h)
        d.cb_mau.setCurrentIndex(d.cb_mau.findData('#16A34A'))
        d.o_bo_ho.setChecked(True)
        g = d.gia_tri()
        self.assertEqual((g['mau'], g.get('xoa_gan_ho')), ('#16A34A', True))
        d.deleteLater()


class TestBanInWord(unittest.TestCase):
    def test_tieu_ngu_khong_thut_doan_chu(self):
        from pabt import in_word
        x = in_word._p_gach('Độc lập - Tự do - Hạnh phúc', 14, True, 5000)
        doan_chu = x.split('</w:p>')[0]
        self.assertNotIn('w:ind', doan_chu)                                 # đoạn chữ dùng trọn bề rộng ô
        self.assertIn('w:ind', x.split('</w:p>')[1])                        # đường gạch ở đoạn rỗng riêng

    def test_cot_quoc_hieu_noi_khi_chu_lon(self):
        from pabt import in_word
        do = lambda chu, phong, co, dam: len(chu) * co * 0.62           # noqa: E731 - hàm đo giả
        self.assertEqual(in_word.rong_cot_dau()[1], in_word.RONG_QUOC_HIEU)
        cu = in_word.CO_QUOC_HIEU
        try:
            in_word.CO_QUOC_HIEU = 16
            r1, r2 = in_word.rong_cot_dau(do)
            self.assertGreater(r2, in_word.RONG_QUOC_HIEU)
            self.assertLessEqual(r2, int(in_word.rong_bang_dau() * in_word.QH_TOI_DA))
        finally:
            in_word.CO_QUOC_HIEU = cu
        w = in_word.rong_trang()
        self.assertLess(in_word.rong_nhan_muc_i([('Tổ chức:', 'UBND xã')], w), w * 28 // 100)

    def test_khoang_ky_ten(self):
        from pabt import dan_trang, dia_phuong, in_word
        self.assertEqual(in_word.DONG_KY_MAC_DINH, 5)
        mw = dict(dia_phuong.mac_dinh()['ban_in']['mau_word'], dong_ky=1)
        hs = dia_phuong.mac_dinh()
        hs['ban_in']['mau_word'] = mw
        self.assertTrue(any('dong_ky' in x for x in dia_phuong.kiem_tra(hs)))
        ts = dan_trang.ThongSo(dong_ky=8)
        self.assertEqual(ts.ban_sao().dong_ky, 8)


@unittest.skipUnless(_bd.CO_QT, 'không có Qt')
class TestBangOffice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_loc_nhanh_va_xoa_noi_dung(self):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        from pabt import giao_dien as gd
        b = QTableWidget(4, 2)
        self.addCleanup(b.deleteLater)
        for r, (a, c) in enumerate((('x', '1'), ('y', '2'), ('x', '3'), ('z', '4'))):
            b.setItem(r, 0, QTableWidgetItem(a))
            b.setItem(r, 1, QTableWidgetItem(c))
        b.setRowHidden(3, True)                                             # bộ lọc riêng của màn hình
        self.assertEqual(gd.loc_nhanh_theo_o(b, 0, 'x'), 2)
        self.assertTrue(b.isRowHidden(1))
        gd.bo_loc_nhanh(b)
        self.assertFalse(b.isRowHidden(1))
        self.assertTrue(b.isRowHidden(3))                                   # bỏ lọc nhanh không mở bộ lọc riêng
        self.assertFalse(gd.sap_xep_bang_theo_cot(b, 0))                    # bảng chưa bật sắp xếp: không đảo dòng
        b.setCurrentCell(1, 1)
        b.item(1, 1).setSelected(True)
        self.assertEqual(gd.xoa_noi_dung_bang(b)['da_ghi'], 1)
        self.assertEqual(b.item(1, 1).text(), '')
        self.assertEqual(b.rowCount(), 4)
        m = gd.menu_sao_chep(b, b.visualItemRect(b.item(0, 0)).center(), hien=False)
        self.addCleanup(m.deleteLater)
        self.assertIn('Lọc nhanh', [a.text() for a in m.actions()])


if __name__ == '__main__':
    unittest.main()
