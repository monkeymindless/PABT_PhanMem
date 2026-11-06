"""Cửa sổ Bản đồ thửa đất (05/11/2026): nhập bản đồ gộp vào cửa sổ, bấm thửa hiện thông tin, đo đạc, la bàn, thu phóng, định vị, gắn hộ, tô màu, "Không nền"."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import ban_do_cad, ban_do_luu, csdl, nen_ban_do
from tests.test_ban_do_ghep import GOC, ban_ve_mau, nhan_thua
from tests.test_toc_do import _du_an

try:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication, QDialog, QPushButton, QTabWidget
    CO_QT = True
except ImportError:
    CO_QT = False


@unittest.skipUnless(CO_QT, 'không có Qt')
class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_bd_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.kml = self.td / 'ban_ve.kml'
        self.kml.write_text(ban_ve_mau(), encoding='utf-8')
        p = mock.patch.object(nen_ban_do, 'thu_muc_dem', lambda: self.td / 'nen')
        p.start()
        self.addCleanup(p.stop)
        q = mock.patch('pabt.giao_dien.cai_dat_nho', lambda: None)          # không ghi vào cài đặt thật của máy
        q.start()
        self.addCleanup(q.stop)
        self.con = csdl.mo(_du_an(self.td, 4))
        self.addCleanup(self.con.close)

    def _hop(self, con=..., **k):
        from pabt.man_hinh_ban_do import HopBanDo
        h = HopBanDo(self.con if con is ... else con, **k)
        h.im_lang = True

        def dong():
            h.done(0)
            h.deleteLater()
            self.app.processEvents()
        self.addCleanup(dong)
        h.resize(1100, 800)
        h.show()
        self.app.processEvents()
        return h

    def _mo(self, **k):
        h = self._hop(**k)
        h.mo_ban_do([self.kml])
        h.view.vua()
        return h

    def _it(self, h, so):
        return next(i for i in h.view.thua if i.t.so_thua == so)

    def _tam(self, h, so):
        x, y = h._tam_thua(self._it(h, so).t)
        return h.view.mapFromScene(QPointF(x, -y))

    def _gan_thua_ho(self, so_to, so_thua, ma_ho):
        with self.con:
            self.con.execute('UPDATE thua SET so_to = ?, so_thua = ? WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua WHERE ma_ho = ?)', (so_to, so_thua, ma_ho))


class TestGopNhap(_Co):
    def test_mo_kmz_duong_thanh_o_thua_ngay(self):
        """Yêu cầu 1: file bản vẽ đường trước đây "0 thửa": mở một lần, ô thửa lên bản đồ, chưa ghi gì vào dự án."""
        h = self._mo()
        self.assertEqual(sorted(i.t.so_thua for i in h.view.thua), list('123456'))
        self.assertTrue(all(i.t.tam for i in h.view.thua))
        self.assertEqual(ban_do_cad.ds_to(self.con), [])
        self.assertIn('nhận diện 6 ô thửa', h.lb.text())
        self.assertIn('chưa lưu', h.lb_tong.text())
        self.assertFalse(h.b_xuat.isEnabled())                              # chưa lưu: xuất KML của dự án chưa có gì
        self.assertEqual(h.cb_to.currentData(), None)                       # nhiều tờ: xem cả tuyến

    def test_the_nhap_trong_cua_so_luu_cap_nhat_ho_so(self):
        self._gan_thua_ho('5', '1', 2)
        goi = []
        h = self._mo(sau_luu=lambda: goi.append(1))
        self.assertIsNone(h.parent())
        n = h.tab_duoi
        self.assertIsInstance(n, QTabWidget)
        self.assertEqual(n.tabText(1), 'Nhập vào dự án')
        kn = h.khung_nhap
        self.assertEqual(kn.bang.rowCount(), 6)
        self.assertEqual(kn.danh_dau_khop(), 1)                             # chỉ thửa khớp hồ sơ, đối chiếu khớp
        kq = kn.luu()
        self.assertEqual((kq['luu'], kq['cap_nhat']), (6, 1))
        self.assertEqual(goi, [1])
        self.assertEqual(float(self.con.execute("SELECT dt_thu_hoi FROM thua WHERE so_to = '5' AND so_thua = '1'").fetchone()[0]), 6000)
        self.assertFalse(any(i.t.tam for i in h.view.thua))                 # thửa đọc lại từ dự án
        self.assertEqual([t for t, _x in ban_do_luu.ds_lop(self.con)], ['ban_ve.kml'])     # lớp bản vẽ lưu theo: nhãn, mốc không mất
        self.assertTrue(h.b_xuat.isEnabled())
        self.assertEqual(sum(1 for i in h.view.thua if i.t.ma_ho == 2), 1)
        # mở lại: ô thửa + nhãn đầy đủ, không phân tích lại
        h2 = self._hop()
        h2.cb_to.setCurrentIndex(h2.cb_to.findData(None))
        self.assertEqual(len(h2.view.thua), 6)
        self.assertFalse(h2._can_phan_tich)
        self.assertTrue(h2.view.kml)

    def test_thua_lech_khong_tu_danh_dau(self):
        for so, ho in (('3', 2), ('1', 3)):
            self._gan_thua_ho('6' if so == '3' else '5', so, ho)
        h = self._mo()
        self.assertEqual(h.khung_nhap.danh_dau_khop(), 1)                   # thửa 3 lệch nhãn: người dùng tự quyết
        r = next(r for r, t in enumerate(h.khung_nhap.kq.thua) if t.so_thua == '3')
        self.assertEqual(h.khung_nhap.bang.item(r, 0).checkState(), Qt.CheckState.Unchecked)
        self.assertIn('Cần xem lại', h.khung_nhap.bang.item(r, 8).text())

    def test_bam_dong_bang_nhap_bay_toi_thua(self):
        h = self._mo()
        h.khung_nhap._bam_dong(0, 1)
        self.assertEqual(h.thua_chon.so_thua, h.khung_nhap.kq.thua[0].so_thua)

    def test_bo_kml_bo_ca_thua_tam(self):
        h = self._mo()
        h.bo_kml()
        self.assertEqual(h.view.thua, [])
        self.assertIsNone(h.khung_nhap.kq)

    def test_lop_da_luu_chua_co_thua_phan_tich_khi_hien(self):
        h = self._mo()
        h.luu_vao_du_an(tai=lambda *a: None)
        with self.con:
            self.con.execute('DELETE FROM thua_ban_do')
        with mock.patch('pabt.man_hinh_ban_do.HopBanDo.showEvent', lambda s, e: None):
            h2 = self._hop()
        self.assertTrue(h2._can_phan_tich)
        h2._phan_tich_lop()
        self.assertEqual(len(h2.view.thua), 6)

    def test_lenh_menu_mo_cua_so_ban_do_khong_mo_hop_rieng(self):
        from pabt.app import CuaSoChinh
        from pabt.man_hinh_ban_do import HopBanDo
        w = CuaSoChinh()
        self.addCleanup(w.close)
        w.con = self.con
        w.chi_doc = False
        d = w.nhap_ban_ve_cad(self.kml, cho=False)
        self.addCleanup(d.done, 0)
        self.assertIsInstance(d, HopBanDo)
        self.assertIs(d.tab_duoi.currentWidget(), d.khung_nhap)
        w.con = None                                                        # đóng cửa sổ chính không đụng kết nối của test

    def test_khong_du_an_van_xem_duoc(self):
        h = self._hop(con=None)
        h.mo_ban_do([self.kml])
        self.assertEqual(len(h.view.thua), 6)
        self.assertFalse(h.tab_duoi.isTabVisible(1))
        h._bam_thua(self._it(h, '1').t)
        self.assertFalse(h.khung_tt.b_gan.isEnabled())
        self.assertIsNone(h.khung_nhap.luu())

    def test_nhap_dxf_qua_nut_mo_ban_do(self):
        from tests.test_yeu_cau_1033 import _ban_ve
        h = self._hop()
        h.mo_ban_do([_ban_ve(self.td / 'To_3.dxf')])
        self.assertIs(h.tab_duoi.currentWidget(), h.khung_nhap)
        h.khung_nhap.cb_thua.setCurrentIndex(h.khung_nhap.cb_thua.findData('RANH THUA'))
        self.assertTrue(h.khung_nhap.phan_tich())
        self.assertGreater(len(h.view.thua), 0)
        self.assertTrue(all(i.t.tam for i in h.view.thua))


class TestBamThua(_Co):
    def test_bam_hien_thong_tin_nhap_dup_mo_phuong_an(self):
        """Yêu cầu 3: bấm ô thửa -> số tờ, số thửa, DT thửa, DT thu hồi ở dưới."""
        self._gan_thua_ho('5', '1', 2)
        mo = []
        h = self._mo(mo_ho=mo.append)
        p = self._tam(h, '1')
        self.assertEqual(h.view.bam_diem(p), 2)
        self.assertEqual(mo, [])
        gt = h.khung_tt.gt
        self.assertEqual(gt['so_to'].text(), '5')
        self.assertEqual(gt['so_thua'].text(), '1')
        self.assertIn('10.000 m²', gt['dt_thua'].text())
        self.assertIn('6.000 m²', gt['dt_thu_hoi'].text())
        self.assertIn('khớp nhãn', gt['dt_thu_hoi'].text())
        self.assertIn('mã 2', gt['ho'].text())
        self.assertIn('DN.T700', gt['moc'].text())
        self.assertEqual(gt['ghi_chu'].text(), 'Đường đất')
        self.assertIn('VN-2000', gt['toa_do'].text())
        self.assertTrue(h.khung_tt.b_mo.isEnabled())
        self.assertEqual(h.view.mo_diem(p), 2)
        self.assertEqual(mo, [2])
        h.khung_tt.b_mo.click()
        self.assertEqual(mo, [2, 2])

    def test_thua_chua_gan_ho_van_bam_duoc(self):
        h = self._mo(mo_ho=lambda m: None)
        self.assertIsNone(h.view.bam_diem(self._tam(h, '2')))
        self.assertEqual(h.khung_tt.gt['ho'].text(), 'Chưa gắn hộ')
        self.assertFalse(h.khung_tt.b_mo.isEnabled())
        self.assertTrue(h.khung_tt.b_gan.isEnabled())

    def test_thua_lech_hien_can_xem_lai(self):
        h = self._mo()
        h.view.bam_diem(self._tam(h, '3'))
        self.assertIn('CẦN XEM LẠI', h.khung_tt.gt['doi_chieu'].text())
        self.assertIn('LỆCH', h.khung_tt.gt['dt_thu_hoi'].text())

    def test_bam_moc_uu_tien_tren_thua(self):
        h = self._mo()
        rec = next(r for r in h.view.kml_cad if r['tt'].get('loai') == 'moc')
        h.view.phong_toi_khung(rec['it'].sceneBoundingRect(), 8)
        tam = h.view.mapFromScene(rec['it'].sceneBoundingRect().center())
        h.view.bam_diem(tam)
        self.assertIn('Mốc ranh', h.khung_tt.gt['ghi_chu'].text())

    def test_nhan_hien_du_khi_ban_ve_nhieu_duong(self):
        """Sự cố: tính cả đường vào giới hạn nhãn - file CAD thật (hơn 3.000 đối tượng) mất hết số thửa, DT trên bản đồ."""
        from tests.test_ban_do_ghep import duong, kml, luoi
        them = ''.join(duong('Level 77', (1000 + i, 0), (1000 + i, 1)) for i in range(3100))
        self.kml.write_text(kml(luoi() + nhan_thua('1', 50, 25) + them), encoding='utf-8')
        h = self._mo()
        self.assertTrue(any(r['tt'].get('loai') == 'thua' for r in h.view.kml_cad))
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        self.assertTrue(any(isinstance(i, QGraphicsSimpleTextItem) and i.text() == '1' for i in h.view.kml))

    def test_bang_tra_cuu_khong_goi_nhan_phan_la_thu_hoi(self):
        h = self._mo()
        h.cb_the_kml.setCurrentIndex(h.cb_the_kml.findData('thua'))
        chu = [h.bang_kml.item(r, 2).text() for r in range(h.bang_kml.rowCount())]
        self.assertEqual(len(chu), 6)
        self.assertTrue(any('thu hồi 6.000 m²' in x for x in chu))
        self.assertFalse(any('thu hồi 4.000' in x for x in chu))
        h.bang_kml.setCurrentCell(0, 0)
        self.assertEqual(h.xem_dong_kml(), 1)
        self.assertIsNotNone(h.thua_chon)

    def test_sao_chep_co_toa_do_dinh(self):
        h = self._mo()
        h._bam_thua(self._it(h, '1').t)
        chu = h.sao_chep_thua()
        self.assertIn('Thửa 1 tờ 5', chu)
        self.assertIn('X = 1.219.', chu)
        self.assertEqual(QApplication.clipboard().text(), chu)


class TestDo(_Co):
    def test_do_duong_vung_toa_do(self):
        h = self._mo()
        x0, y0 = GOC
        h.b_do['duong'].click()
        self.assertEqual(h.view.thuoc.che_do, 'duong')
        self.assertTrue(h.khung_do.isVisibleTo(h))
        t = h.view.thuoc
        t.them(x0, -y0)
        t.them(x0 + 300, -y0)
        t.them(x0 + 300, -(y0 + 100))
        self.assertIn('tổng 400,00 m', h.lb_do.text())
        self.assertTrue(t.ket_thuc())
        self.assertFalse(t.ket_thuc())
        t.them(x0, -y0)                                                     # bấm tiếp: đo mới
        self.assertEqual(len(t.diem), 1)
        h.b_do['vung'].click()
        self.assertFalse(h.b_do['duong'].isChecked())
        for p in ((0, 0), (100, 0), (100, 100), (0, 100)):
            t.them(x0 + p[0], -(y0 + p[1]))
        t.ket_thuc()
        self.assertIn('10.000,0 m²', h.lb_do.text())
        self.assertIn('chu vi 400,00 m', h.lb_do.text())
        self.assertTrue(t._hinh)
        h.b_do['diem'].click()
        t.them(x0, -y0)
        self.assertIn('X 1.219.000,000', h.lb_do.text())
        self.assertIn('Y 410.000,000', h.lb_do.text())
        h.b_xoa_do.click()
        self.assertEqual(t.diem, [])
        self.assertEqual(t._hinh, [])
        h.b_do['diem'].click()
        self.assertIsNone(t.che_do)

    def test_do_vung_dung_bang_dien_tich_thua(self):
        """Chấm theo các đỉnh của thửa: diện tích đo = diện tích hình thửa."""
        h = self._mo()
        it = self._it(h, '1')
        h.bat_do('vung')
        pg = it.polygon()
        for i in range(pg.count()):
            h.view.thuoc.them(pg.at(i).x(), pg.at(i).y())
        h.view.thuoc.ket_thuc()
        self.assertIn('10.000,', h.lb_do.text())

    def test_bat_dinh_thua(self):
        h = self._mo()
        x0, y0 = GOC
        h.view.phong_toi_m(0.5)
        p = h.view.mapFromScene(QPointF(x0 + 100.5, -(y0 + 100.5)))         # lệch 0,7 m < 9 điểm x 0,5 m: bắt vào đỉnh
        self.assertEqual(tuple(round(v, 1) for v in h.view.bat_dinh(p)), (x0 + 100, -(y0 + 100)))
        q = h.view.mapFromScene(QPointF(x0 + 150, -(y0 + 50)))              # xa mọi đỉnh: giữ nguyên
        kq = h.view.bat_dinh(q)
        self.assertLess(abs(kq[0] - (x0 + 150)), 1)

    def test_phim_va_chuot_khi_do(self):
        h = self._mo()
        x0, y0 = GOC
        h.bat_do('duong')
        t = h.view.thuoc
        t.them(x0, -y0)
        t.them(x0 + 10, -y0)
        h.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
        self.assertEqual(len(t.diem), 1)
        t.them(x0 + 10, -y0)
        h.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
        self.assertTrue(t.xong)
        h.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))    # đã xong: Esc thôi đo, không đóng cửa sổ
        self.assertIsNone(t.che_do)
        self.assertFalse(h.b_do['duong'].isChecked())

    def test_ve_lai_khong_hong_thuoc(self):
        """Cảnh bị xóa cả loạt khi vẽ lại: thước quên hình cũ, vẽ lại đường đo (giữ tham chiếu hình đã hủy là sập)."""
        h = self._mo()
        x0, y0 = GOC
        h.bat_do('duong')
        h.view.thuoc.them(x0, -y0)
        h.view.thuoc.them(x0 + 50, -y0)
        h.view.dat_ghim(x0, -y0, 'A')
        h.nap(giu_khung=True)
        self.assertTrue(h.view.thuoc._hinh)
        self.assertTrue(all(i.scene() is h.view.scene() for i in h.view.thuoc._hinh))
        self.assertTrue(all(i.scene() is h.view.scene() for i in h.view._ghim_hinh))
        h.bat_do(None)
        h.xoa_do()


class TestBangBen(_Co):
    def test_thong_tin_o_ben_phai_keo_duoc(self):
        """Người dùng 05/11/2026: thông tin thửa sang bên phải, bản đồ cao hết cửa sổ, kéo thanh chia chỉnh to nhỏ hai bên."""
        h = self._mo()
        self.assertEqual(h.chia.orientation(), Qt.Orientation.Horizontal)
        self.assertIs(h.chia.widget(0), h.view)
        self.assertTrue(h.ben_phai.isAncestorOf(h.khung_tt))
        self.assertTrue(h.ben_phai.isAncestorOf(h.tab_duoi))
        trai, phai = h.chia.sizes()
        self.assertGreater(trai, phai)
        self.assertGreater(h.view.height(), h.ben_phai.height() - 5)
        h.chia.setSizes([trai - 100, phai + 100])                           # kéo: hai bên đổi cỡ, bản đồ vẫn dùng được
        self.assertEqual(h.chia.sizes()[1], phai + 100)
        self.assertGreater(h.chia.handleWidth(), 4)

    def test_an_hien_bang_nho_do_rong(self):
        h = self._mo()
        _t, phai = h.chia.sizes()
        self.assertFalse(h.an_hien_ben())
        self.assertEqual(h.chia.sizes()[1], 0)
        self.assertEqual(h.b_an_ben.text(), 'Hiện bảng')
        self.assertGreater(h.chia.sizes()[0], 0)
        self.assertTrue(h.an_hien_ben())
        self.assertEqual(h.chia.sizes()[1], phai)
        self.assertEqual(h.b_an_ben.text(), 'Ẩn bảng')

    def test_bam_thua_khi_bang_dang_an_tu_mo(self):
        h = self._mo()
        h.an_hien_ben()
        h.view.bam_diem(self._tam(h, '1'))
        self.assertGreater(h.chia.sizes()[1], 0)
        h.an_hien_ben()
        h.bat_do('duong')
        self.assertGreater(h.chia.sizes()[1], 0)
        h.bat_do(None)

    def test_nho_do_rong_qua_cai_dat(self):
        kho = {}

        class CaiDat:
            def value(self, k, md=None):
                return kho.get(k, md)

            def setValue(self, k, v):
                kho[k] = v
        with mock.patch('pabt.giao_dien.cai_dat_nho', lambda: CaiDat()):
            h = self._mo()
            trai, phai = h.chia.sizes()
            h.chia.setSizes([trai - 77, phai + 77])
            h._nho_chia()
            self.assertEqual(kho['ban_do/rong_bang_ben'], phai + 77)
            h2 = self._hop()
            self.assertEqual(h2.chia.sizes()[1], phai + 77)

    def test_the_nhap_gon_trong_bang_ben(self):
        h = self._mo()
        kn = h.khung_nhap
        self.assertFalse(kn.khoi_lop_thua.isVisibleTo(kn))                  # KML tự nhận diện: khỏi hai ô chọn lớp
        phai = h.chia.sizes()[1]
        h.tab_duoi.setCurrentWidget(kn)
        self.assertGreater(h.chia.sizes()[1], phai)                         # bảng nhiều cột: nới bảng bên một lần
        self.assertTrue(kn.lb.toolTip())
        h.tab_duoi.setCurrentWidget(h.khung_tc)
        h.ve_bang_kml()
        self.assertLessEqual(h.bang_kml.columnWidth(1), h.RONG_COT_TEN)
        from tests.test_yeu_cau_1033 import _ban_ve
        h.mo_ban_do([_ban_ve(self.td / 'To_3.dxf')])
        self.assertTrue(kn.khoi_lop_thua.isVisibleTo(kn))                   # DXF: chọn lớp

    def test_khong_ep_cua_so_rong_ra(self):
        """Chữ dài trong bảng phải tự xuống dòng, không đẩy bảng / cửa sổ rộng ra ngoài màn hình."""
        h = self._mo()
        rong = h.khung_tt.minimumSizeHint().width()
        h._bam_thua(self._it(h, '3').t)
        self.assertEqual(h.khung_tt.minimumSizeHint().width(), rong)
        self.assertLess(h.ben_phai.minimumSizeHint().width(), 420)


class TestDieuHuong(_Co):
    def test_la_ban_xoay_giu_tam_va_ty_le(self):
        h = self._mo()
        v = h.view
        v.phong_toi_m(0.1)                                                  # phóng gần: cảnh rộng hơn khung, xoay mới giữ được tâm
        m = v.m_moi_diem()
        tam = v.mapToScene(v.viewport().rect().center())
        v.dat_goc(30)
        self.assertEqual(v.goc, 30)
        self.assertAlmostEqual(v.m_moi_diem(), m, places=6)                 # tỷ lệ tính đúng khi xoay
        moi = v.mapToScene(v.viewport().rect().center())
        self.assertLess(abs(moi.x() - tam.x()) + abs(moi.y() - tam.y()), 3 * m + 1)
        v.dat_goc(0)
        self.assertEqual(v.goc, 0)
        self.assertAlmostEqual(v.transform().m12(), 0, places=9)

    def test_la_ban_chuot(self):
        from PySide6.QtGui import QMouseEvent
        h = self._mo()
        lb = h.view.la_ban
        c = lb.rect().center()

        def ev(loai, p):
            return QMouseEvent(loai, QPointF(p), QPointF(lb.mapToGlobal(p)), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        h.view.phong_toi_m(0.1)
        tren = QPoint(c.x(), c.y() - 18)                                    # mũi tên lên: di chuyển bản đồ
        truoc = h.view.mapToScene(h.view.viewport().rect().center())
        lb.mousePressEvent(ev(QEvent.Type.MouseButtonPress, tren))
        sau = h.view.mapToScene(h.view.viewport().rect().center())
        self.assertLess(sau.y(), truoc.y())
        h.view.dat_goc(40)                                                  # kéo vòng ngoài: xoay; bấm chữ N: về Bắc
        vong = QPoint(c.x() + 34, c.y())
        lb.mousePressEvent(ev(QEvent.Type.MouseButtonPress, vong))
        lb.mouseMoveEvent(ev(QEvent.Type.MouseMove, QPoint(c.x(), c.y() + 34)))
        self.assertAlmostEqual(h.view.goc, 130, delta=2)
        lb.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, QPoint(c.x(), c.y() + 34)))
        h.view.dat_goc(0)
        n = QPoint(c.x(), c.y() - 32)
        h.view.dat_goc(5)
        lb.mousePressEvent(ev(QEvent.Type.MouseButtonPress, n))
        lb.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, n))
        self.assertEqual(h.view.goc, 0)
        lb.grab()                                                           # paintEvent chạy được

    def test_thanh_thu_phong(self):
        h = self._mo()
        v = h.view
        v.phong_toi_m(1.0)
        self.assertAlmostEqual(v.m_moi_diem(), 1.0, places=6)
        self.assertEqual(v.sl_phong.value(), 50)
        v.sl_phong.setValue(75)
        self.assertAlmostEqual(v.m_moi_diem(), 0.1, delta=0.001)
        v.phong()
        self.assertGreater(v.sl_phong.value(), 75)
        self.assertTrue(v.hop_nut.isVisibleTo(v))

    def test_dinh_vi_thua_va_toa_do(self):
        h = self._mo()
        self.assertFalse(h.dinh_vi_thua())
        self.assertIn('Bấm chọn', h.lb.text())
        h._bam_thua(self._it(h, '1').t)
        self.assertTrue(h.dinh_vi_thua())
        self.assertIn('VN-2000', h.lb.text())
        self.assertTrue(h.view._ghim_hinh)
        self.assertLess(h.view.m_moi_diem(), 1.0)
        x0, y0 = GOC
        h.thua_chon = None
        self.assertTrue(h.di_toi_toa_do(f'X {y0 + 50:.0f} Y {x0 + 150:.0f}'))         # giữa thửa 2
        self.assertEqual(h.thua_chon.so_thua, '2')
        self.assertIn('trong thửa 2', h.lb.text())
        self.assertFalse(h.di_toi_toa_do('sai'))
        self.assertIn('Không đọc được', h.lb.text())

    def test_vi_tri_may(self):
        h = self._mo()
        from pabt import toa_do
        vd, kd = toa_do.vn2000_sang_wgs84(GOC[0] + 50, GOC[1] + 50, h.kt)
        self.assertTrue(h.dat_vi_tri_may(dict(vd=vd, kd=kd, sai=80.0)))
        self.assertIn('CHỈ THAM KHẢO', h.lb.text())                         # sai số lớn: báo rõ
        self.assertEqual(len(h.view._ghim_hinh), 3)                         # vòng sai số + dấu + chữ
        self.assertTrue(h.dat_vi_tri_may(dict(vd=vd, kd=kd, sai=3.0)))
        self.assertNotIn('THAM KHẢO', h.lb.text())
        self.assertFalse(h.dat_vi_tri_may(dict(loi='Windows chưa cho phép')))
        self.assertIn('chưa cho phép', h.lb.text())
        h.view.bo_ghim()
        self.assertEqual(h.view._ghim_hinh, [])


class TestGanHo(_Co):
    def test_gan_ho_co_san_them_thua_khong_dung_thua_khac(self):
        h = self._mo()
        t = self._it(h, '2').t
        truoc = self.con.execute('SELECT COUNT(*) FROM thua WHERE ma_ho = 3').fetchone()[0]
        self.assertTrue(h.gan_ho(t, ma_ho=3))
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM thua WHERE ma_ho = 3').fetchone()[0], truoc + 1)
        r = self.con.execute("SELECT * FROM thua WHERE so_to = '5' AND so_thua = '2'").fetchone()
        self.assertEqual(r['ma_ho'], 3)
        self.assertEqual(float(r['dt_thu_hoi']), 6000)
        self.assertEqual(float(r['dt_nguyen_thua']), 10000)
        self.assertEqual(r['loai_dat'], 'LUK')
        self.assertEqual(self._it(h, '2').t.ma_ho, 3)                       # tô màu lại theo hộ
        self.assertNotEqual(self._it(h, '2').khoa_mau, 'khong_gan')
        self.assertIsNotNone(self._it(h, '2').nhan_ten)                     # tên hộ lên ô thửa
        self.assertTrue(any('Thêm thửa từ bản đồ' in str(tuple(r)) for r in self.con.execute('SELECT * FROM nhat_ky ORDER BY rowid DESC LIMIT 3')))

    def test_tao_ho_moi_theo_ten(self):
        goi = []
        h = self._mo(sau_luu=lambda: goi.append(1))
        n0 = self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        self.assertTrue(h.gan_ho(self._it(h, '6').t, ho_ten='  Hộ  Mẫu  Mới '))
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], n0 + 1)
        t = self._it(h, '6').t
        self.assertEqual(t.ho_ten, 'Hộ Mẫu Mới')
        self.assertEqual(goi, [1])

    def test_chuyen_tu_ho_khac(self):
        self._gan_thua_ho('5', '1', 2)
        h = self._mo()
        t = self._it(h, '1').t
        self.assertEqual(t.ma_ho, 2)
        self.assertTrue(h.gan_ho(t, ma_ho=3))
        self.assertEqual(self._it(h, '1').t.ma_ho, 3)
        self.assertFalse(h.gan_ho(self._it(h, '1').t, ma_ho=3))             # đã thuộc hộ này: báo, không ghi
        self.assertIn('đã thuộc', h.lb.text())

    def test_hop_gan_ho_loc_va_dong_y(self):
        from pabt.man_hinh_ban_do_cong_cu import HopGanHo
        h = self._mo()
        d = h.gan_ho(self._it(h, '4').t, cho=False)
        self.assertIsInstance(d, HopGanHo)
        d.im_lang = True
        tong = d.ds.count()
        self.assertEqual(tong, 4)
        ten = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0]
        d.o_tim.setText(ten)
        self.assertGreaterEqual(d.ds.count(), 1)
        d.o_tim.setText('khong co ai ten nay')
        self.assertEqual(d.ds.count(), 0)
        d.o_tim.setText('')
        d._dong_y()                                                         # chưa chọn: báo, không ghi
        self.assertIn('Chọn một hộ', d.lb.text())
        d.ds.setCurrentRow(0)
        d._dong_y()
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)
        d.deleteLater()

    def test_chi_doc_khong_gan(self):
        h = self._mo(chi_doc=True)
        self.assertFalse(h.tab_duoi.isTabVisible(1))
        h._bam_thua(self._it(h, '1').t)
        self.assertFalse(h.khung_tt.b_gan.isEnabled())
        self.assertFalse(h.khung_tt.b_sua.isEnabled())
        self.assertIsNone(h.gan_ho(ma_ho=2))

    def test_sua_so_thua(self):
        h = self._mo()
        t = self._it(h, '1').t
        self.assertTrue(h.sua_thua(t, dict(so_to='5', so_thua='101', loai_dat='cln')))      # chưa lưu: sửa trong kết quả phân tích
        self.assertEqual(self._it(h, '101').t.loai_dat, 'CLN')
        self.assertEqual(h.thua_chon.so_thua, '101')
        self.assertFalse(h.sua_thua(self._it(h, '2').t, dict(so_to='5', so_thua='101')))    # trùng: báo
        self.assertIn('đã có', h.lb.text())
        h.khung_nhap.luu()
        self.assertTrue(h.sua_thua(self._it(h, '101').t, dict(so_to='5', so_thua='102')))   # đã lưu: sửa trong dự án
        self.assertTrue(self.con.execute("SELECT 1 FROM thua_ban_do WHERE so_thua = '102'").fetchone())
        d = h.sua_thua(self._it(h, '102').t, cho=False)
        self.assertEqual(d.gia_tri()['so_thua'], '102')
        d.deleteLater()

    def test_ben_phai_khong_bi_che_va_cuon_duoc(self):
        from PySide6.QtWidgets import QApplication, QScrollArea, QSplitter
        h = self._mo()
        h.resize(1200, 620)
        h.show()
        h.bat_do('duong')                                             # đang đo: thêm khung kết quả đo ở trên, ảnh người dùng gửi
        h.tab_duoi.setVisible(True)
        h.tab_duoi.setCurrentWidget(h.khung_nhap)
        QApplication.processEvents()
        self.addCleanup(lambda: h.bat_do(None))
        self.assertIsInstance(h.chia_doc, QSplitter)
        self.assertIs(h.chia_doc.widget(0), h.cuon_tt)
        self.assertIs(h.chia_doc.widget(1), h.tab_duoi)
        self.assertIsInstance(h.cuon_tt, QScrollArea)
        # phần thông tin không bị ép: khung giữ đủ cao, thừa thì cuộn
        self.assertGreaterEqual(h.khung_tt.height(), h.khung_tt.minimumSizeHint().height())
        k = h.khung_nhap
        self.assertGreaterEqual(k.bang.height(), 170)
        # hàng tham số đủ chỗ cho mọi dòng (Kinh tuyến trục không bị che)
        self.assertGreaterEqual(k._hang.height(), k._xep_hang.heightForWidth(k._hang.width()))
        # nút Lưu luôn thấy: nằm ngoài vùng cuộn
        self.assertFalse(k.cuon_than.widget().isAncestorOf(k.b_luu_thua))
        self.assertTrue(k.b_luu_thua.isVisible())
        self.assertLessEqual(k.b_luu_thua.mapTo(k, k.b_luu_thua.rect().bottomLeft()).y(), k.height())
        # kéo được, không thu mất phần nào
        tren, duoi = h.chia_doc.sizes()
        h.chia_doc.setSizes([tren - 60, duoi + 60])
        self.assertLess(h.chia_doc.sizes()[0], tren)
        self.assertFalse(h.chia_doc.childrenCollapsible())

    def test_to_mau_o_thua(self):
        h = self._mo()
        t = self._it(h, '1').t
        self.assertTrue(t.tam)
        m = h.menu_cho_thua(t)
        con = m.menu_to_mau
        self.assertIn('Tô màu ô thửa', [a.text() for a in m.actions()])
        chu = [a.text() for a in con.actions() if a.text()]
        self.assertEqual(chu[0], 'Đỏ')
        self.assertIn('Màu khác…', chu)
        bo = next(a for a in con.actions() if a.text() == 'Bỏ màu đã tô')
        self.assertFalse(bo.isEnabled())
        m.deleteLater()
        # thửa chưa lưu: giữ trong bộ nhớ, thấy ngay, lưu bản đồ thì vào dự án
        h.o_to_mau.setChecked(False)
        self.assertTrue(h.to_mau_thua(t, '#dc2626'))
        self.assertEqual(t.mau, '#DC2626')
        self.assertTrue(h.o_to_mau.isChecked())
        it = self._it(h, '1')
        self.assertEqual(it.brush().color().rgb() & 0xFFFFFF, 0xDC2626)
        self.assertEqual(it.khoa_mau, t.trang_thai)                   # chú giải, % đồng thuận vẫn theo trạng thái
        self.assertIn('1 thửa tô tay', h.lb_tong.text())
        self.assertEqual(t.chi_tiet.get('mau'), None)
        h.khung_nhap.luu()
        t = self._it(h, '1').t
        self.assertFalse(t.tam)
        self.assertEqual(t.mau, '#DC2626')
        self.assertEqual(self._it(h, '1').brush().color().rgb() & 0xFFFFFF, 0xDC2626)
        self.assertNotIn('mau', t.chi_tiet)                           # chi_tiet vẫn chỉ là dữ liệu đối chiếu bản vẽ
        # đã lưu: ghi ngay, đổi cách tô không mất, mở lại còn
        self.assertTrue(h.to_mau_thua(t, '#2563EB'))
        from pabt import ban_do_cad
        doc = {x.so_thua: x for x in ban_do_cad.doc_ban_do(self.con)}
        self.assertEqual(doc['1'].mau, '#2563EB')
        self.assertEqual(doc['2'].mau, '')
        h.cb_mau.setCurrentIndex(1)
        self.assertEqual(self._it(h, '1').brush().color().rgb() & 0xFFFFFF, 0x2563EB)
        # bỏ màu: về màu theo cách tô; nạp lại file không mất màu đã tô
        ban_do_cad.dat_mau_thua(self.con, t.so_to, t.so_thua, '#16A34A')
        kq = ban_do_cad.KetQuaCad(thua=[ban_do_cad.ThuaCad(t.so_to, t.so_thua, 'CLN', None, ban_do_cad.D('1'), None, t.toa_do)], nguon='x')
        ban_do_cad.luu(self.con, kq)
        self.assertEqual({x.so_thua: x.mau for x in ban_do_cad.doc_ban_do(self.con)}['1'], '#16A34A')
        ban_do_cad.dat_mau_thua(self.con, t.so_to, t.so_thua, '')
        self.assertEqual({x.so_thua: x.mau for x in ban_do_cad.doc_ban_do(self.con)}['1'], '')
        with self.assertRaises(ValueError):
            ban_do_cad.dat_mau_thua(self.con, t.so_to, t.so_thua, 'do')
        d = h.chon_mau_thua(self._it(h, '2').t, cho=False)
        self.assertEqual(d.currentColor().name().upper(), ban_do_cad.MAU_TO_TAY[0][1])
        d.deleteLater()

    def test_menu_chuot_phai(self):
        h = self._mo()
        m = h.menu_cho_thua(self._it(h, '1').t)
        ten = [a.text() for a in m.actions()]
        self.assertIn('Gắn hộ vào thửa…', ten)
        self.assertIn('Định vị thửa này', ten)
        m.deleteLater()

    def test_to_mau_tat_bat_va_ten_ho(self):
        self._gan_thua_ho('5', '1', 2)
        h = self._mo()
        it = self._it(h, '1')
        self.assertGreater(it.brush().color().alpha(), 0)
        h.o_to_mau.setChecked(False)
        self.assertEqual(it.brush().color().alpha(), 0)
        h.o_to_mau.setChecked(True)
        self.assertGreater(it.brush().color().alpha(), 0)
        h.view.phong_toi_m(0.3)
        self.assertTrue(it.nhan_ten.isVisible())
        h.o_ten_ho.setChecked(False)
        self.assertFalse(it.nhan_ten.isVisible())
        h.o_ten_ho.setChecked(True)
        self.assertTrue(it.nhan_ten.isVisible())
        h.view.phong_toi_m(5)                                               # nhìn xa: không ghi tên
        self.assertFalse(it.nhan_ten.isVisible())

    def test_doi_cach_to_khong_dung_lai_canh(self):
        h = self._mo()
        it = self._it(h, '1')
        with mock.patch.object(h.view, 've', side_effect=AssertionError('không được dựng lại cảnh')):
            h.cb_mau.setCurrentIndex(h.cb_mau.findData('thu_hoi'))
        self.assertIs(self._it(h, '1'), it)
        self.assertEqual(it.khoa_mau, 'mot_phan')
        self.assertIn('trong ranh', h.lb_tong.text())
        self.assertEqual(list(h.lb_dem), list(ban_do_cad.THU_HOI))


class TestKhongNen(_Co):
    def test_khong_nen_khong_tai_anh(self):
        """Yêu cầu 4."""
        goi = []
        with mock.patch.object(nen_ban_do, 'tai_o', lambda z, x, y, **k: goi.append(1)):
            h = self._mo()
            i = h.cb_nen.findData(nen_ban_do.KHONG_NEN)
            self.assertEqual(h.cb_nen.itemText(i), 'Không nền')
            self.assertEqual(i, h.cb_nen.count() - 1)
            h.o_nen.setChecked(True)
            h.nen.cho_xong(5)
            goi.clear()
            self.assertTrue(h.view._co_nen_ve)
            h.cb_nen.setCurrentIndex(i)
            self.assertFalse(h._co_nen())
            self.assertFalse(h.view._co_nen_ve)
            self.assertFalse(h.nap_nen())
            h._khung_doi()
            self.assertFalse(h.hen_nen.isActive())
            self.assertFalse(h.nen.dang)
            self.assertEqual(h.view.o_nen, [])
            self.assertFalse(h.lb_nguon.isVisibleTo(h))
            self.assertEqual(goi, [])
            self.assertIn('Không nền', h.lb.text())
            h.b_luu.click()                                                 # lưu: chỉ thửa + lớp bản vẽ
            self.assertIn('Không nền', h.lb.text())
            self.assertEqual(goi, [])

    def test_tro_lai_co_nen(self):
        from tests.test_ban_do_pa4 import _png
        anh = _png()
        with mock.patch.object(nen_ban_do, 'tai_o', lambda z, x, y, **k: anh):
            h = self._mo()
            h.cb_nen.setCurrentIndex(h.cb_nen.findData(nen_ban_do.KHONG_NEN))
            h.o_nen.setChecked(True)
            self.assertEqual(h.view.o_nen, [])
            h.cb_nen.setCurrentIndex(h.cb_nen.findData('ve_tinh'))
            self.assertTrue(h.view._co_nen_ve)
            self.assertTrue(h.nen.cho_xong(10))
            self.assertTrue(h.view.o_nen)
            self.assertTrue(h.lb_nguon.isVisibleTo(h))

    def test_o_giu_cho_khong_bao_loi_mang(self):
        with mock.patch.object(nen_ban_do, 'tai_o', lambda z, x, y, **k: nen_ban_do.KHONG_CO_ANH):
            h = self._mo()
            h.cb_nen.setCurrentIndex(h.cb_nen.findData('ve_tinh'))
            h.o_nen.setChecked(True)
            self.assertTrue(h.nen.cho_xong(10))
        self.assertEqual(h.view.o_nen, [])
        self.assertNotIn('không tải được', h.lb.text())

    def test_khong_tao_cua_so_la(self):
        truoc = {id(w) for w in QApplication.topLevelWidgets()}
        h = self._mo()
        h.bat_do('vung')
        h.tab_duoi.setCurrentIndex(1)
        h._bam_thua(self._it(h, '1').t)
        moi = [w for w in QApplication.topLevelWidgets() if id(w) not in truoc and w.isVisible() and not isinstance(w, QDialog)]
        self.assertEqual(moi, [])

    def test_nut_co_cha(self):
        h = self._hop()
        self.assertTrue(all(b.parent() is not None for b in h.findChildren(QPushButton)))


if __name__ == '__main__':
    unittest.main()
