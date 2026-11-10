"""1.0.52 (người dùng 02/11/2026, xem lại các mục 1.0.51 bỏ qua): che CCCD tùy chọn trên bản niêm yết công khai, nút Lưu xanh lục,
định danh ứng dụng mới, luôn ẩn danh khi gửi AI, 7 chỉ mục, phông số thẻ KPI, ghi nhiều bước một giao dịch. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class _CoDuAn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 4))
        self.addCleanup(self.con.close)

    def tearDown(self):
        self.doCleanups()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestCheCccd(_CoDuAn):
    def test_che_cccd(self):
        from pabt.an_toan import che_cccd
        self.assertEqual(che_cccd('075092123456'), '075092123456')                # mặc định: in đủ (văn bản nội bộ)
        self.assertEqual(che_cccd('075092123456', True), '075092***456')
        self.assertEqual(che_cccd('075 092 123 456', True), '075092***456')
        self.assertEqual(che_cccd('271234567', True), '271***567')
        self.assertEqual(che_cccd('Chưa có', True), 'Chưa có')
        self.assertEqual(che_cccd('', True), '')

    def test_tuy_chon_du_an_va_ban_in_du_thao(self):
        from pabt import an_toan, du_lieu_in, in_word
        ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        with csdl.giao_dich(self.con):
            self.con.execute("UPDATE ho SET so_cccd = '075092123456', ngay_cap = '01/01/2021' WHERE ma_ho = ?", (ma,))
        self.assertFalse(an_toan.che_cccd_niem_yet(self.con))                     # mặc định tắt
        da = du_lieu_in._thong_tin_du_an(self.con)
        self.assertIn('075092123456', du_lieu_in._thong_tin_ho(self.con, ma, da)['cccd'])
        an_toan.dat_che_cccd_niem_yet(self.con, True)
        self.assertTrue(an_toan.che_cccd_niem_yet(self.con))
        dt = in_word.du_lieu_chi_tiet(self.con, ma, du_thao=True)
        ct = in_word.du_lieu_chi_tiet(self.con, ma, du_thao=False)
        x_dt = str(dt)
        self.assertIn('075092***456', x_dt)
        self.assertNotIn('075092123456', x_dt)
        self.assertNotIn('01/01/2021', x_dt)                                      # bỏ ngày cấp trên bản niêm yết
        self.assertIn('075092123456', str(ct))                                     # bản chính thức in đủ
        an_toan.dat_che_cccd_niem_yet(self.con, False)
        self.assertFalse(an_toan.che_cccd_niem_yet(self.con))

    def test_hop_in_hien_o_che_o_du_thao(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import man_hinh
        h = man_hinh.HopIn(self.con, che_do='du_thao')
        self.addCleanup(h.deleteLater)
        self.assertTrue(h.o_che_cccd.isVisibleTo(h))
        h.o_che_cccd.setChecked(True)
        from pabt.an_toan import che_cccd_niem_yet
        self.assertTrue(che_cccd_niem_yet(self.con))
        h.dat_che_do('chinh_thuc')
        self.assertFalse(h.o_che_cccd.isVisibleTo(h))


class TestChiMucVaGiaoDich(_CoDuAn):
    def test_chi_muc(self):
        ten = {r[0] for r in self.con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        for k, _sql in csdl.CHI_MUC_THEM:
            self.assertIn(k, ten)
        ke = self.con.execute("EXPLAIN QUERY PLAN SELECT id FROM ct_khoan WHERE cong_thuc <> ''").fetchall()
        self.assertIn('ix_ct_khoan_cong_thuc', str([tuple(r) for r in ke]))

    def test_bo_don_gia_khong_bi_ghi_chi_muc(self):
        from pabt import don_gia
        c = csdl.mo(don_gia.file_goc(), chi_doc=True)
        try:
            ten = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        finally:
            c.close()
        self.assertNotIn('ix_ho_thutu', ten)

    def test_giao_dich_long_chi_ghi_mot_lan(self):
        from pabt import lap_pa
        with self.assertRaises(RuntimeError):
            with csdl.giao_dich(self.con):
                da = lap_pa.doc_du_an(self.con)
                da['ten'] = 'Thử giao dịch lồng'
                lap_pa.luu_du_an(self.con, da)
                raise RuntimeError('lỗi giữa chừng')
        ten = self.con.execute('SELECT ten FROM du_an').fetchone()[0]
        self.assertNotEqual(ten, 'Thử giao dịch lồng')                             # tầng trong không commit riêng


class TestGiaoDien(unittest.TestCase):
    def test_nut_luu_xanh_luc_va_phong_so(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import giao_dien
        qss = giao_dien._qss_day_du()
        self.assertIn(f'background: {giao_dien.MAU_LUU[0]}', qss)
        self.assertIn('QLabel[vai="so_the"] { font-family: "Segoe UI"', qss)

    def test_the_so_thanh_tien_do_khong_de_chu(self):
        """Ảnh người dùng 02/11/2026: thanh tiến độ đè dòng diện tích ở cỡ chữ 125% - thanh nổi ở đáy, thẻ cao theo nội dung."""
        from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout
        QApplication.instance() or QApplication([])
        from pabt import app
        from pabt.giao_dien import tao_thanh_tien_do
        t = app.TheSo()
        self.addCleanup(t.deleteLater)
        lo = QVBoxLayout(t)
        lo.setContentsMargins(10, 3, 10, 4)
        chu = QLabel('42.914,0 m²')
        chu.setMinimumHeight(80)                                                   # giả lập chữ to (A+)
        lo.addWidget(chu)
        lo.addStretch(1)                                                           # như thẻ thật: chữ xếp trên, chỗ thừa ở đáy
        thanh = tao_thanh_tien_do('#2563EB')
        thanh.setParent(t)
        t.thanh = thanh
        t.resize(300, 62)
        t.vua_cao()
        self.assertGreaterEqual(t.height(), 80 + 7 + 8)
        t.show()
        QApplication.processEvents()
        self.assertGreaterEqual(thanh.geometry().top(), chu.geometry().bottom())    # thanh dưới chữ, không đè
        self.assertIsNone(lo.indexOf(thanh) if lo.indexOf(thanh) >= 0 else None)   # không nằm trong bố cục
        t.close()

    def test_dinh_danh_ung_dung(self):
        from pabt import app
        self.assertEqual(app.APP_USER_MODEL_ID, 'vn.larc.desktop.enterprise')
        self.assertEqual(app.dinh_danh_ung_dung(), app.APP_USER_MODEL_ID)

    def test_luon_an_danh(self):
        from pabt import tro_ly
        self.assertFalse(tro_ly.doc_cai_dat()['gui_ca_nhan'])


if __name__ == '__main__':
    unittest.main()
