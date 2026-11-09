"""05/11/2026: cửa sổ Tính đơn giá đất bồi thường (NQ 28 x QĐ 03), nút Quét dùng chung, lệnh ở cửa sổ chính, hộp con canh giữa màn hình."""
from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import csdl, du_an_moi
from pabt import quet_chung as qc
from pabt import van_ban_can_cu as vb
from pabt.lap_pa import BoSoan

from tests import APP

D = Decimal


def _du_an(td: Path, xa: str = 'Tân An') -> Path:
    dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i), loai_dat='CLN', dt_thu_hoi=str(100 + i),
                 vi_tri='1') for i in range(3)]
    gia = [dict(loai_dat='CLN', vi_tri='1', gia='250000')]
    p = td / 'a.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban=xa, nam='2026'), dong, gia)
    return p


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestHopTinhGiaDat(unittest.TestCase):
    def setUp(self):
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        self.Hop = HopTinhGiaDat
        self.HopTinhGiaDat = HopTinhGiaDat
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.con = None

    def _hop(self, con=None, ds=(), xa='Tân An', chi_doc=False):
        h = self.Hop(None, con, list(ds), xa, chi_doc)
        h.im_lang = True
        self.addCleanup(h.close)
        return h

    def test_mo_chon_dia_ban_va_tinh(self):
        h = self._hop(xa='Xã Tân An')
        self.assertEqual(h.cb_dia_ban.currentData(), 'Bảng 54. Xã Tân An')
        self.assertEqual(h.cb_doan.count(), 26)
        self.assertIn('→', h.cb_doan.itemText(0))
        self.assertIsNotNone(h.kq)
        # G tự tra từ bảng giá NQ 28 theo cụm 7 dòng; đổi vị trí kết nối -> G đổi
        g_mt = D(h.o_g.text().replace('.', ''))
        h.cb_vi_tri.setCurrentIndex(3)                                  # T3
        self.assertNotEqual(D(h.o_g.text().replace('.', '')), g_mt)
        self.assertLess(D(h.o_g.text().replace('.', '')), g_mt)
        self.assertIn('Tự tra', h.lb_g.text())

    def test_gia_theo_doan_va_nhom(self):
        h = self._hop(xa='Tân An')
        i = next(k for k in range(h.cb_doan.count()) if 'Cầu Chùm Bao → Cầu Bà Giá' in h.cb_doan.itemText(k))
        h.cb_doan.setCurrentIndex(i)
        h.cb_nhom.setCurrentIndex(h.cb_nhom.findData('DAT_O|dat_o'))
        self.assertEqual(h.kq.k1, D('1.39'))
        h.cb_nhom.setCurrentIndex(0)                                    # đất nông nghiệp: K1 NN
        self.assertEqual(h.kq.k1, D('1.32'))

    def test_phu_luc_3_theo_nhom_dat(self):
        h = self._hop()
        h.cb_nhom.setCurrentIndex(0)
        self.assertFalse(h.ck_pl3['PNN_TTTM_200M'].isEnabled())
        self.assertTrue(h.ck_pl3['NN_DUONG_DAT_SOI_DA'].isEnabled())
        h.cb_ket_cau.setCurrentIndex(1)                                 # đường đất / sỏi
        self.assertEqual(h.kq.k3, D('0.90'))
        h.ck_rieng.setChecked(True)
        self.assertEqual(h.kq.k3, 1)
        self.assertTrue(h.lb_canh_bao.text())
        h.cb_nhom.setCurrentIndex(h.cb_nhom.findData('DAT_O|dat_o'))    # đất ở: yếu tố NN bị loại, tích PNN được
        self.assertFalse(h.ck_pl3['NN_DUONG_DAT_SOI_DA'].isEnabled())
        h.ck_pl3['PNN_NGHIATRANG_100M'].setChecked(True)
        self.assertEqual(h.kq.k3, D('0.95'))

    def test_loc_doan_theo_tu_khoa_khong_dau(self):
        h = self._hop(xa='Tân An')
        h.o_tim.setText('cau chum bao')
        self.assertGreaterEqual(h.cb_doan.count(), 1)
        self.assertTrue(all('Cầu Chùm Bao' in h.cb_doan.itemText(k) for k in range(h.cb_doan.count())))
        h.o_tim.setText('')
        self.assertEqual(h.cb_doan.count(), 26)

    def test_nhap_sai_khong_sap(self):
        h = self._hop()
        h.o_g.setText('abc')
        self.assertIsNone(h.tinh())
        self.assertFalse(h.nut_ap.isEnabled())
        h.o_g.setText('1.000.000')
        self.assertIsNotNone(h.tinh())

    def test_quet_dien_thong_so_va_sap_van_ban_can_cu(self):
        h = self._hop(xa='Trị An')
        nd = ('Phường Trị An. Đất trồng cây lâu năm tiếp giáp đường cấp phối.\nCăn cứ Nghị định số 78/2025/NĐ-CP của Chính phủ về bồi thường\n'
              'Quyết định 03/2026/QĐ-UBND')
        kq = qc.quet(['x.txt'], qc.GIA_DAT, doc=lambda p: nd.replace('Phường Trị An', 'Xã Phú Lý'))
        h.sau_khi_quet(kq)
        self.assertEqual(h.cb_dia_ban.currentData(), 'Bảng 55. Xã Phú Lý')
        self.assertEqual(h.cb_ket_cau.currentData(), 'DAT_SOI_DA_CAPPHOI')
        self.assertTrue(h.ck_pl3['NN_DUONG_DAT_SOI_DA'].isChecked())
        so = [x.so_hieu for x in vb.gop_va_sap_xep([h.o_can_cu.toPlainText()])[1]]
        self.assertLess(so.index('78/2025/NĐ-CP'), so.index('27/2025/NQ-HĐND'))
        self.assertEqual(h.o_can_cu.toPlainText(), vb.gop_va_sap_xep([h.o_can_cu.toPlainText()])[0])      # đã sắp, ổn định

    def test_ap_gia_vao_dong_dat_cua_ho(self):
        p = _du_an(Path(self.td.name))
        con = csdl.mo(p)
        self.addCleanup(con.close)
        ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY ma_ho')][:2]
        h = self._hop(con, ds, 'Tân An')
        n_dong = sum(len(BoSoan(con, m).pa.dat) for m in ds)
        self.assertGreaterEqual(n_dong, 2)
        self.assertEqual(h.bang.rowCount(), n_dong)
        h.cb_nhom.setCurrentIndex(0)
        h.o_g.setText('400000')
        h.cb_doan.setCurrentIndex(0)
        h.o_g.setText('400000')
        gia = h.kq.don_gia_ap_dung
        self.assertEqual(gia, D(400000) * h.kq.k1 * h.kq.k3)
        r = h.ap_gia(xac_nhan=True)
        self.assertEqual((r[0], r[1], r[2]), (n_dong, 2, []))
        for ma in ds:
            b = BoSoan(con, ma)
            for d in b.pa.dat:
                self.assertEqual(d.gia_bang_gia, gia)
                self.assertEqual(d.he_so_k, 1)
                self.assertIn('QĐ 03/2026/QĐ-UBND', d.ghi_chu)
        ho_khac = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY ma_ho')][2]
        self.assertNotEqual(BoSoan(con, ho_khac).pa.dat[0].gia_bang_gia, gia)                          # hộ không chọn: giữ nguyên
        self.assertTrue(vb.doc_can_cu_du_an(con).startswith('1. '))                                       # căn cứ lưu theo dự án
        # áp lần hai: ghi chú căn cứ không lặp
        h2 = self._hop(con, ds, 'Tân An')
        h2.o_g.setText('500000')
        h2.ap_gia(xac_nhan=True)
        gc = BoSoan(con, ds[0]).pa.dat[0].ghi_chu
        self.assertEqual(gc.count('QĐ 03/2026/QĐ-UBND'), 1)

    def test_chi_xem_khong_ap(self):
        p = _du_an(Path(self.td.name))
        con = csdl.mo(p)
        self.addCleanup(con.close)
        ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        h = self._hop(con, [ma], 'Tân An', chi_doc=True)
        self.assertFalse(h.nut_ap.isEnabled())

    def test_khong_co_ho_chi_tinh(self):
        h = self._hop()
        self.assertFalse(h.nut_ap.isEnabled())
        self.assertEqual(h.ap_gia(xac_nhan=True), (0, 0, []))


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestLenhVaCanGiua(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')

    def _cua_so(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(_du_an(Path(self.tmp.name))))
        APP.processEvents()
        return w

    def test_lenh_moi_co_o_dung_mot_cho(self):
        w = self._cua_so()
        for t in ('Tính đơn giá đất…', 'Quét file thông minh…'):
            self.assertIn(t, w.lenh)
        from PySide6.QtWidgets import QToolButton
        trai = [b.defaultAction().text() for b in w.khung_menu.findChildren(QToolButton) if b.defaultAction() is not None]
        self.assertIn(w.lenh['Tính đơn giá đất…'].text(), trai)
        tren = [a.text() for a in w.menu_tren['Dữ liệu'].actions()]
        self.assertIn(w.lenh['Quét file thông minh…'].text(), tren)

    def test_tinh_don_gia_dat_mo_hop_voi_ho_chon(self):
        w = self._cua_so()
        ma = w.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        h = w.tinh_don_gia_dat(cho=False, ds_ma_ho=[ma])
        h.im_lang = True
        self.addCleanup(h.close)
        self.assertEqual(h.cb_dia_ban.currentData(), 'Bảng 54. Xã Tân An')
        self.assertGreater(h.bang.rowCount(), 0)

    def test_quet_thong_minh_hop_ket_qua(self):
        w = self._cua_so()
        nd = 'Căn cứ Luật Đất đai số 31/2024/QH15\nXã Tân An, tờ bản đồ số 12, thửa đất số 205, diện tích 256,8 m2'
        h = w.quet_thong_minh(files=['x.txt'], cho=False, doc=lambda p: nd)
        self.addCleanup(h.close)
        self.assertEqual(len(h.kq.dong_dat), 1)
        self.assertTrue(h.b_ghi.isEnabled())
        self.assertEqual(h.b_dat.rowCount(), 1)
        h._chon('ghi_can_cu')
        self.assertEqual(h.hanh_dong, 'ghi_can_cu')

    def test_nut_quet_the_niem_yet_goi_bo_quet_chung(self):
        w = self._cua_so()
        k = w.mo_du_thao(cho=False)
        k = k or w.khung_tab.widget['du_thao']
        self.assertEqual(set(k.nut_quet), {'DETAILED_HOUSEHOLD_DOSSIER', 'LAND_PRICE_TABLE', 'ASSET_CROP_PRICE_TABLE'})
        nd = 'Cây bưởi\tcây\t35\t1.450.000\nNhà cấp 4\tm2\t65\t3.850.000\n'
        h = k.quet_chung('ASSET_CROP_PRICE_TABLE', files=['x.txt'], doc=lambda p: nd, cho=False)
        self.addCleanup(h.close)
        self.assertEqual(len(h.kq.dong_tai_san), 2)
        self.assertEqual(h.kq.ngu_canh, 'ASSET_CROP_PRICE_TABLE')
        self.assertEqual(h.b_ts.rowCount(), 2)

    def test_hop_con_luon_giua_man_hinh_va_khong_cao_qua(self):
        from pabt.giao_dien import BIEN_MAN_HINH, vua_man_hinh
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        h = HopTinhGiaDat(None)
        h.im_lang = True
        self.addCleanup(h.close)
        h.resize(3000, 3000)
        h.show()
        h.nut_mo_cc.setChecked(True)
        h.nut_mo_gt.setChecked(True)
        APP.processEvents()
        from pabt.giao_dien import cuon_than_hop
        cuon_than_hop(h)
        vua_man_hinh(h)
        APP.processEvents()
        self.assertTrue(h.nut_ap.isVisible())
        self.assertLessEqual(h.nut_ap.mapTo(h, h.nut_ap.rect().bottomLeft()).y(), h.height())
        vung = (h.screen() or APP.primaryScreen()).availableGeometry()
        self.assertLessEqual(h.height(), vung.height() - BIEN_MAN_HINH)
        tam = h.frameGeometry().center()
        if h.width() <= vung.width():                                       # màn hình ảo 800 x 600 đo chữ rộng gấp đôi: hộp có thể rộng hơn
            self.assertLessEqual(abs(tam.x() - vung.center().x()), 40)
        self.assertLessEqual(abs(tam.y() - vung.center().y()), 40)
        khung = h.frameGeometry()
        self.assertGreaterEqual(khung.left(), vung.left() - 2)
        self.assertGreaterEqual(khung.top(), vung.top() - 2)
        self.assertLessEqual(khung.right(), vung.right() + 2)
        self.assertLessEqual(khung.bottom(), vung.bottom() + 2)

    def test_mo_hop_tu_can_giua_khong_can_goi_tay(self):
        """Mở hộp con: bộ lọc hiện cửa sổ tự kéo về giữa, không cần gọi tay vua_man_hinh."""
        from pabt.giao_dien import _BoToMau
        from pabt.man_hinh_du_toan import HopTraNQ28
        if getattr(APP, '_bo_to_mau', None) is None:
            APP._bo_to_mau = _BoToMau(APP)
            APP.installEventFilter(APP._bo_to_mau)
        h = HopTraNQ28(None, xem=True)
        self.addCleanup(h.close)
        h.resize(2400, 1600)
        h.move(0, 0)
        h.show()
        APP.processEvents()
        vung = (h.screen() or APP.primaryScreen()).availableGeometry()
        khung = h.frameGeometry()
        self.assertLessEqual(khung.width(), vung.width())
        self.assertLessEqual(khung.height(), vung.height())
        self.assertLessEqual(abs(khung.center().x() - vung.center().x()), 48)
        self.assertLessEqual(abs(khung.center().y() - vung.center().y()), 48)


if __name__ == '__main__':
    unittest.main()
