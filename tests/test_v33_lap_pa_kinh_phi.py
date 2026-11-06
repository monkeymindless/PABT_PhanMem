"""06/11/2026 (người dùng): gói V3.3 cửa sổ lập phương án và Bảng tổng hợp kinh phí "Zero-Truncation". Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QHeaderView, QLabel, QSplitter

from pabt import csdl, ho_so
from pabt.giao_dien import phong_so
from pabt.man_hinh import CuaSoLapPA, _so_luong_hien
from pabt.man_hinh_theo_doi import KhungBangTongHop, _ten_the_phan_bo
from pabt.nghiep_vu import MUC_VN
from pabt.tien import vn
from tests.test_toc_do import _du_an

CAU = 'Nguyễn Văn Thử là chủ sở hữu tài sản gắn liền với thửa đất số 17, tờ bản đồ số 39, xã Thử - Đất do UBND xã Thử quản lý.'


class TestTachHoTen(unittest.TestCase):
    def test_tach(self):
        ten, dg = ho_so.tach_ho_ten(CAU)
        self.assertEqual(ten, 'Nguyễn Văn Thử')
        self.assertTrue(dg.startswith('Là chủ sở hữu tài sản'))
        self.assertIn('Đất do UBND', dg)
        self.assertEqual(ho_so.tach_ho_ten('Phan Văn Thử - Đất do UBND xã quản lý')[0], 'Phan Văn Thử')

    def test_khong_doan(self):
        for s in ('UBND xã Thử quản lý.', 'Nguyễn Thị Thử', '', None, 'Đất do UBND xã quản lý', ' - Đất do UBND xã'):
            self.assertEqual(ho_so.tach_ho_ten(s)[1], '', s)

    def test_so_luong(self):
        self.assertEqual(_so_luong_hien('1.599,0', 'cây'), '1.599')
        self.assertEqual(_so_luong_hien('96,00', 'Cái'), '96')
        self.assertEqual(_so_luong_hien('2,5', 'cây'), '2,5')          # số lẻ thật: không làm mất số liệu
        self.assertEqual(_so_luong_hien('121,0', 'm²'), '121,0')
        self.assertEqual(_so_luong_hien('12,0', 'nhân khẩu'), '12')

    def test_ten_the_phan_bo(self):
        self.assertEqual(_ten_the_phan_bo(0, '- Tổ chức (Trung tâm Phát triển quỹ đất Chi nhánh A) 85%:', '85'), 'KP Tổ chức - TTPTQĐ (85%)')
        self.assertEqual(_ten_the_phan_bo(1, '- Cơ quan phối hợp (Xã A) 15%:', '15'), 'KP Phối hợp - Cấp xã (15%)')
        self.assertEqual(_ten_the_phan_bo(0, '- Ban bồi thường 90%:', '90'), 'KP Tổ chức (90%)')       # không gán cứng đơn vị


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='v33_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.con = csdl.mo(str(_du_an(self.td, 6)))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]


class TestLapPA(_Co):
    def _cs(self, ma=None, rong=1500):
        c = CuaSoLapPA(self.con, ma if ma is not None else self.ma[1])
        c.resize(rong, 800)
        c.show()
        self.addCleanup(c.deleteLater)
        self.addCleanup(lambda: setattr(c, 'hoi_luu', lambda: True))
        self.app.processEvents()
        return c

    def _dat_cau(self):
        with self.con:
            self.con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = ?', (CAU, self.ma[1]))

    def test_nut_phu_cung_hang_nhap(self):
        c = self._cs()
        for m, co in ((2, 'Kiểm tra DT xây dựng…'), (3, 'Tính mật độ…'), (MUC_VN, None), (4, 'Tự tính hỗ trợ')):
            bm = c.bang[m]
            c.tab.setCurrentIndex([0, 1, 2, 3, MUC_VN, 4].index(m))
            self.app.processEvents()
            self.assertEqual(bm._hang_nhap.indexOf(bm._khoi_nut), bm._hang_nhap.count() - 1)
            self.assertFalse(bm._khung_2.isVisibleTo(bm))
            self.assertEqual(bm.nut['Dán tài sản'].text(), 'Dán')
            self.assertEqual(bm.b_gon.text(), 'Gọn cột')
            self.assertTrue(bm.nut['▲ Lên'].isVisibleTo(bm))
            self.assertEqual(bm.hang.nut_them.text(), '+ Thêm')
            self.assertTrue(bm.hang.nut_them.icon().isNull())
            if co:
                self.assertIn(co, bm.nut)
                self.assertTrue(bm.nut[co].isVisibleTo(bm))
            self.assertEqual(bm.bang.horizontalHeaderItem(bm.c_xoa).text(), 'Xóa')
            self.assertEqual(bm.bang.columnWidth(bm.c_xoa), 44)

    def test_hep_cum_nut_xuong_hang(self):
        c = self._cs()
        c.tab.setCurrentIndex(3)
        self.app.processEvents()
        bm = c.bang[3]
        bm.resize(700, 400)
        bm._xep_cum_nut()
        self.assertGreaterEqual(bm._hang_2.indexOf(bm._khoi_nut), 0)
        self.assertTrue(bm._khung_2.isVisibleTo(bm))
        self.assertTrue(bm._khoi_nut.isVisibleTo(bm))
        bm.resize(1500, 400)
        bm._xep_cum_nut()
        self.assertGreaterEqual(bm._hang_nhap.indexOf(bm._khoi_nut), 0)
        self.assertFalse(bm._khung_2.isVisibleTo(bm))

    def test_ho_so_tach_ten_chi_tren_form_cho_toi_khi_luu(self):
        self._dat_cau()
        c = self._cs()
        hs = c.ho_so
        self.assertEqual(hs.o['ho_ten'].text(), 'Nguyễn Văn Thử')
        self.assertIn('Là chủ sở hữu', hs.o['phap_ly'].text())
        self.assertTrue(hs.co_thay_doi())
        self.assertIn('2. Nguyễn Văn Thử', c.cb_ho.currentText())
        self.assertNotIn('chủ sở hữu', c.cb_ho.currentText())
        self.assertEqual(self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (self.ma[1],)).fetchone()[0], CAU)    # chưa ghi
        self.assertTrue(hs.luu())
        r = self.con.execute('SELECT ho_ten, phap_ly FROM ho WHERE ma_ho = ?', (self.ma[1],)).fetchone()
        self.assertEqual(r[0], 'Nguyễn Văn Thử')
        self.assertIn('Là chủ sở hữu', r[1])
        hs.nap()
        self.assertFalse(hs.co_thay_doi())                              # lần sau không tách lại

    def test_chi_doc_khong_tinh_la_thay_doi(self):
        self._dat_cau()
        from pabt.man_hinh_ho_so import KhungHoSo
        hs = KhungHoSo(self.con, self.ma[1], None)
        self.addCleanup(hs.deleteLater)
        hs.chi_doc = True
        hs.nap()
        self.assertEqual(hs.o['ho_ten'].text(), 'Nguyễn Văn Thử')
        self.assertFalse(hs.co_thay_doi())

    def test_dien_dt_tu_muc_1(self):
        t = self.con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ? ORDER BY ma_thua LIMIT 1', (self.ma[1],)).fetchone()[0]
        dt = self.con.execute('SELECT dien_tich FROM ct_dat WHERE ma_thua = ?', (t,)).fetchone()[0]
        self.assertTrue(dt)
        with self.con:
            self.con.execute("UPDATE thua SET dt_thu_hoi = '0' WHERE ma_thua = ?", (t,))
        c = self._cs()
        hs = c.ho_so
        o = hs.bang.item(0, hs.cot.index('dt_thu_hoi'))
        self.assertNotIn(o.text().strip(), ('', '0'))
        self.assertTrue(hs.co_thay_doi())
        self.assertIn('điền DT thu hồi', hs.lb.text())
        self.assertEqual(self.con.execute('SELECT dt_thu_hoi FROM thua WHERE ma_thua = ?', (t,)).fetchone()[0], '0')    # chưa ghi

    def test_huy_hieu_va_tieu_de(self):
        c = self._cs()
        hs = c.ho_so
        self.assertFalse(hasattr(hs, 'the_sao_chep'))
        self.assertNotIn('&&', hs.lb_tieu_de_thua.text())
        self.assertIn('&', hs.lb_tieu_de_thua.text())
        self.assertIsInstance(hs.the_goi_y_bang, QLabel)
        self.assertTrue(hs.the_goi_y_bang.font().italic())
        self.assertEqual(hs.the_goi_y_bang.property('vai'), 'phu')

    def test_nut_luu_theo_trang_thai(self):
        c = self._cs(self.ma[0])
        c.b_luu.setEnabled(True)
        c._ve_nut_luu()
        self.assertIn('Lưu', c.b_luu.text())
        self.assertNotIn('Đã lưu', c.b_luu.text())
        c.b_luu.setEnabled(False)
        c._ve_nut_luu()
        self.assertEqual(c.b_luu.text(), '✓ Đã lưu')

    def test_tu_tinh_ho_tro_chua_ghi(self):
        c = self._cs()
        bm = c.bang[4]
        trc = self.con.execute('SELECT COUNT(*) FROM ct_khoan WHERE ma_ho = ? AND muc = 4', (self.ma[1],)).fetchone()[0]
        c.bo.pa.khoan[4].clear()
        bm.ve()
        chon = c.tu_tinh_ho_tro()
        self.assertTrue(chon)
        self.assertEqual(bm.bang.rowCount(), len(c.bo.pa.khoan[4]))
        self.assertGreater(bm.bang.rowCount(), 0)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ct_khoan WHERE ma_ho = ? AND muc = 4', (self.ma[1],)).fetchone()[0], trc)

    def test_chan_gop_mot_thanh(self):
        c = self._cs()
        self.assertFalse(c.dai_bo_dem.isVisibleTo(c))
        self.assertEqual(c.dai_dieu_huong.maximumHeight(), 34)
        c.tab.setCurrentIndex(2)
        self.app.processEvents()
        self.assertIn('Mẹo: Quét chọn nhiều ô', c.lb_chan.text())
        c.tab.setCurrentIndex(5)
        self.app.processEvents()
        b = c.bang[4].bang
        self.assertGreater(b.rowCount(), 0)
        cot = [b.horizontalHeaderItem(i).text() for i in range(b.columnCount())]
        sm = b.selectionModel()
        for ten in ('Số lượng', 'Đơn giá (đ)', 'Thành tiền (đ)'):
            sm.select(b.model().index(0, cot.index(ten)), QItemSelectionModel.SelectionFlag.Select)
        self.app.processEvents()
        c.cap_nhat_bo_dem(b, {})
        chu = c.lb_chan.text()
        self.assertIn('Đang chọn: 1 dòng (3 ô)', chu)
        self.assertIn('Tổng SL/DT', chu)
        self.assertIn('Đơn giá TB', chu)
        self.assertIn('Tổng Thành tiền vùng chọn', chu)
        sm.clearSelection()
        self.app.processEvents()
        c.cap_nhat_bo_dem(b, {})
        self.assertIn('TỔNG CỘNG PHƯƠNG ÁN', c.lb_chan.text())


class TestKinhPhi(_Co):
    def _khung(self):
        k = KhungBangTongHop(self.con)
        k.im_lang = True
        k.resize(1400, 760)
        k.show()
        self.addCleanup(k.deleteLater)
        self.app.processEvents()
        k.nap()
        self.app.processEvents()
        return k

    def test_the_1_rong_het_nut_sang_the_3(self):
        k = self._khung()
        self.assertFalse(k.findChildren(QSplitter))
        self.assertTrue(k.doi_soat.isAncestorOf(k.an_toan))
        self.assertFalse(k.an_toan.bang.isVisibleTo(k.an_toan))
        self.assertIn('Đối soát Pre-F/S: Chưa đối soát', k.co_cau.b_doi_soat.text())
        k.co_cau.b_doi_soat.click()
        self.app.processEvents()
        self.assertEqual(k.tab.currentIndex(), 2)

    def test_cot_the_1(self):
        k = self._khung()
        b, d = k.co_cau.bang, k.co_cau.bang.horizontalHeader()
        self.assertEqual(b.columnWidth(0), 50)
        self.assertEqual(b.columnWidth(2), 70)
        self.assertEqual(d.sectionResizeMode(1), QHeaderView.ResizeMode.Stretch)
        self.assertTrue(b.isColumnHidden(k.co_cau.C_CAN_CU))
        fm = QFontMetrics(phong_so(b.font(), True))
        for c in (3, 4, 5):
            self.assertGreaterEqual(b.columnWidth(c), 155)
            for r in range(b.model().rowCount()):
                self.assertGreater(b.columnWidth(c), fm.horizontalAdvance(str(b.model().index(r, c).data() or '')))
        self.assertTrue(any('Căn cứ:' in str(b.model().index(r, 1).data(3) or '') for r in range(b.model().rowCount())))   # 3 = ToolTipRole

    def _the_2(self):
        k = self._khung()
        k.mo_the(1)
        self.app.processEvents()
        return k, k.tien

    def test_the_2_khong_cat_so_va_cot(self):
        k, t = self._the_2()
        b = t.bang
        self.assertTrue(b.isColumnHidden(t.C_MA))
        self.assertEqual(b.model().headerData(0, Qt.Orientation.Horizontal), 'TT')
        self.assertEqual(b.model().headerData(t.C_THAO_TAC, Qt.Orientation.Horizontal), 'Thao tác')
        self.assertEqual(b.columnWidth(0), 44)
        self.assertEqual(b.columnWidth(t.C_THAO_TAC), 78)
        self.assertGreaterEqual(b.columnWidth(t.C_TEN), t.RONG_TEN_TOI_THIEU)
        fm = QFontMetrics(phong_so(b.font(), True))
        for c in range(3, 13):
            for r in range(b.model().rowCount()):
                self.assertGreater(b.columnWidth(c), fm.horizontalAdvance(str(b.model().index(r, c).data() or '')))
            self.assertGreater(b.columnWidth(c), fm.horizontalAdvance(t.hang_tong.item(0, c).text()))
        self.assertEqual(b.model().index(0, t.C_THAO_TAC).data(), '✎ Mở PA')
        self.assertEqual(t.COT[0], 'STT')                               # file Excel vẫn đủ STT, Mã hộ, Đối chiếu Excel
        self.assertEqual(t.COT[-1].replace('\n', ' '), 'Đối chiếu Excel')

    def test_hang_tong_thang_cot(self):
        k, t = self._the_2()
        ds = t.dong()
        ht = t.hang_tong
        self.assertTrue(ht.isVisibleTo(t))
        self.assertEqual(ht.item(0, t.C_TEN).text(), f'TỔNG CỘNG ({len(ds)} HỘ)')
        self.assertEqual(ht.item(0, 3).text(), str(sum(d[3] for d in ds)))
        self.assertEqual(ht.item(0, 10).text(), vn(sum(d[10] for d in ds)))
        for c in range(14):
            self.assertEqual(ht.columnWidth(c), t.bang.columnWidth(c), c)
            self.assertEqual(ht.isColumnHidden(c), t.bang.isColumnHidden(c), c)
        self.assertEqual(t.bang.model().rowCount(), len(ds))            # không lẫn vào dòng dữ liệu, không bị sắp xếp

    def test_an_cot_trong(self):
        k, t = self._the_2()
        ds = t.dong()
        trong = [c for c in t.C_TIEN_AN_DUOC if not any(d[c] for d in ds)]
        self.assertTrue(trong)
        self.assertFalse(t.bang.isColumnHidden(trong[0]))
        t.b_an_trong.setChecked(True)
        self.app.processEvents()
        for c in t.C_TIEN_AN_DUOC:
            self.assertEqual(t.bang.isColumnHidden(c), c in trong, c)
            self.assertEqual(t.hang_tong.isColumnHidden(c), c in trong, c)
        t.b_an_trong.setChecked(False)
        self.app.processEvents()
        self.assertFalse(any(t.bang.isColumnHidden(c) for c in t.C_TIEN_AN_DUOC))

    def test_mo_pa_bang_cot_thao_tac_va_nhap_dup(self):
        k, t = self._the_2()
        mo = []
        t.mo_ho.connect(mo.append)
        t.bang.cellClicked.emit(0, 5)
        self.assertEqual(mo, [])
        t.bang.cellClicked.emit(0, t.C_THAO_TAC)
        t.bang.cellDoubleClicked.emit(1, 5)
        self.assertEqual(len(mo), 2)

    def test_ten_hai_tang(self):
        with self.con:
            self.con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = ?', (CAU, self.ma[1]))
        k, t = self._the_2()
        b = t.bang
        self.assertEqual(b.verticalHeader().defaultSectionSize(), t.CAO_DONG_HAI_TANG)
        r = next(i for i in range(b.model().rowCount()) if 'chủ sở hữu' in str(b.model().index(i, t.C_TEN).data()))
        self.assertEqual(b.model().index(r, t.C_TEN).data(3), CAU)      # đủ câu ở chú thích
        self.assertFalse(b.grab().isNull())                             # vẽ ô hai tầng không lỗi

    def test_kpi(self):
        k = self._khung()
        self.assertTrue(k.hang_kpi.the['pb_0'].lb_ten.text().startswith('KP Tổ chức'))
        self.assertTrue(k.hang_kpi.the['pb_1'].lb_ten.text().startswith('KP Phối hợp'))
        self.assertNotIn('Phần', k.hang_kpi.the['pb_0'].lb_ten.text())
