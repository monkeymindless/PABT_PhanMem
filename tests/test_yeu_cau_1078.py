"""1.0.78 (người dùng 07/11/2026): hộp in Windows, Ctrl+V / X trên ô, sang hộ về thẻ Hồ sơ & Thửa, Bảng kinh phí chi tiết. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pabt  # noqa: E402,F401
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem  # noqa: E402
from pabt import csdl, giao_dien as g  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class TestCatDanChung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def bang(self):
        from PySide6.QtCore import Qt
        b = QTableWidget(4, 3)
        for r in range(4):
            for c in range(3):
                it = QTableWidgetItem(f'{r}{c}')
                if c == 2:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                b.setItem(r, c, it)
        self.addCleanup(b.deleteLater)
        return b

    def test_doc_clipboard(self):
        self.assertEqual(g.doc_o_clipboard('a\tb\r\nc\td\r\n'), [['a', 'b'], ['c', 'd']])
        self.assertEqual(g.doc_o_clipboard('"x\ny"\tz'), [['x\ny', 'z']])
        self.assertEqual(g.doc_o_clipboard(''), [])

    def test_dan_khoi_bo_o_khong_sua_duoc(self):
        b = self.bang()
        b.setCurrentCell(1, 1)
        kq = g.dan_vao_bang(b, 'A\tB\nC\tD\n')
        self.assertEqual((b.item(1, 1).text(), b.item(2, 1).text()), ('A', 'C'))
        self.assertEqual(b.item(1, 2).text(), '12')                     # cột không sửa được giữ nguyên
        self.assertEqual((kq['da_ghi'], kq['bo_qua']), (2, 2))

    def test_mot_gia_tri_dien_moi_o_chon(self):
        b = self.bang()
        b.setRangeSelected(__import__('PySide6.QtWidgets', fromlist=['x']).QTableWidgetSelectionRange(0, 0, 2, 0), True)
        self.assertEqual(g.dan_vao_bang(b, '9')['da_ghi'], 3)
        self.assertEqual([b.item(r, 0).text() for r in range(4)], ['9', '9', '9', '30'])
        self.assertEqual(len(b.selectionModel().selectedIndexes()), 3)  # vùng chọn còn nguyên

    def test_tran_ngoai_bang_va_cot_an(self):
        b = self.bang()
        b.setColumnHidden(1, True)
        b.setCurrentCell(3, 0)
        kq = g.dan_vao_bang(b, 'x\ty\nz')
        self.assertEqual(b.item(3, 0).text(), 'x')
        self.assertEqual(b.item(3, 1).text(), '31')                     # cột ẩn không bị ghi
        self.assertEqual(kq['bo_qua'], 2)                               # y vào cột không sửa, z tràn

    def test_cat_va_chi_doc(self):
        from PySide6.QtWidgets import QAbstractItemView
        b = self.bang()
        b.setCurrentCell(0, 0)
        g.cat_khoi_bang(b)
        self.assertEqual(b.item(0, 0).text(), '')
        self.assertEqual(QApplication.clipboard().text(), '00')
        b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.assertEqual(g.dan_vao_bang(b, 'k')['da_ghi'], 0)
        b.setCurrentCell(1, 0)
        g.cat_khoi_bang(b)
        self.assertEqual(b.item(1, 0).text(), '10')                     # chỉ xem: chỉ chép


class _Nen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1078_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.p = _du_an(self.td, 4)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)


class TestLapPA(_Nen):
    def cua_so(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma[0])
        w.hoi_luu = lambda: True
        self.addCleanup(w.close)
        return w

    def test_sang_ho_ve_the_ho_so(self):
        w = self.cua_so()
        w.show()
        for lam in (lambda: w.sang_ho(1), lambda: w._chon_ho_tu_hop(w.cb_ho.findData(self.ma[2]))):
            w.tab.setCurrentIndex(1)
            lam()
            self.assertEqual(w.tab.currentIndex(), 0)
        self.assertEqual(w.bo.ma_ho, self.ma[2])

    def test_dan_vao_dong_dat_mot_buoc_hoan_tac(self):
        w = self.cua_so()
        w.tab.setCurrentIndex(1)
        bm = w.bang[1]
        c = [x[0] for x in bm.cot].index('dien_tich')
        bm.bang.setCurrentCell(0, c)
        n = len(w._lich_su)
        kq = bm.dan_o('12,5')
        self.assertEqual(kq['loi'], [])
        self.assertEqual(str(w.bo.pa.dat[0].dien_tich), '12.5')
        self.assertEqual(len(w._lich_su), n + 1)

    def test_o_sai_gom_mot_bao_khong_hien_hop(self):
        w = self.cua_so()
        w.tab.setCurrentIndex(1)
        bm = w.bang[1]
        c = [x[0] for x in bm.cot].index('dien_tich')
        cu = str(w.bo.pa.dat[0].dien_tich)
        bm.bang.setCurrentCell(0, c)
        with mock.patch('PySide6.QtWidgets.QMessageBox.warning') as hop:
            kq = bm.dan_o('abc')
        hop.assert_not_called()
        self.assertEqual(len(kq['loi']), 1)
        self.assertEqual(str(w.bo.pa.dat[0].dien_tich), cu)
        self.assertEqual(bm.bang.item(0, c).text() != 'abc', True)      # ô vẽ lại giá trị đúng
        self.assertIsNone(w._gom_loi)

    def test_cot_thua_khong_nhan_chu_dan(self):
        w = self.cua_so()
        w.tab.setCurrentIndex(1)
        bm = w.bang[1]
        c = [x[0] for x in bm.cot].index('thua')
        ma = w.bo.pa.dat[0].ma_thua
        bm.bang.setCurrentCell(0, c)
        self.assertEqual(bm.dan_o('rác')['da_ghi'], 0)
        self.assertEqual(w.bo.pa.dat[0].ma_thua, ma)

    def test_menu_co_cat_dan(self):
        w = self.cua_so()
        w.tab.setCurrentIndex(1)
        chu = [a.text() for a in w.bang[1].menu_dong().actions()]
        self.assertIn('Cắt\tCtrl+X', chu)
        self.assertIn('Dán\tCtrl+V', chu)


class TestBangChiTiet(_Nen):
    def khung(self):
        from pabt.man_hinh_theo_doi import KhungTongHopTien
        k = KhungTongHopTien(self.con)
        self.addCleanup(k.deleteLater)
        k.resize(1500, 600)
        k.show()
        k.nap()
        self.app.processEvents()
        return k

    def test_khong_con_khoang_trong_cot_an(self):
        k = self.khung()
        b = k.bang
        hop = (k.C_MA, k.C_TEN)
        self.assertEqual(b.columnViewportPosition(hop[1]), b.columnViewportPosition(0) + b.columnWidth(0))
        self.assertEqual(b.horizontalHeader().length(), b.viewport().width())
        b.sortByColumn(3, __import__('PySide6.QtCore', fromlist=['Qt']).Qt.SortOrder.DescendingOrder)   # sắp xếp = đặt lại mô hình
        self.app.processEvents()
        self.assertEqual(b.columnViewportPosition(hop[1]), b.columnViewportPosition(0) + b.columnWidth(0))
        self.assertTrue(b.isColumnHidden(k.C_MA))

    def test_ho_ten_dai_xuong_dong_du_chu(self):
        dai = 'Nguyễn Văn ' + 'Rất Dài ' * 60
        with self.con:
            self.con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = ?', (dai.strip(), self.ma[1]))
        k = self.khung()
        b = k.bang
        r = next(i for i in range(b.model().rowCount()) if str(b.model().index(i, k.C_TEN).data()).startswith('Nguyễn Văn Rất'))
        ngan = next(i for i in range(b.model().rowCount()) if i != r)
        self.assertGreater(b.rowHeight(r), b.rowHeight(ngan))
        cao = b.rowHeight(r)
        b.setColumnWidth(k.C_TEN, k.RONG_TEN_TOI_THIEU)
        k._vua_cao_ten()
        self.assertGreaterEqual(b.rowHeight(r), cao)                    # hẹp đi: cao thêm
        self.assertFalse(b.grab().isNull())


CHU_SO_HUU = 'Là chủ sở hữu tài sản trên thửa đất số 16, tờ bản đồ số 39, xã Phú Lý do UBND xã Phú Lý quản lý.'


class TestDongDuoiTen(_Nen):
    def dat(self):
        with self.con:
            self.con.execute('UPDATE ho SET phap_ly = ? WHERE ma_ho = ?', (f'Đất do UBND xã quản lý.; {CHU_SO_HUU}', self.ma[1]))

    def test_tach(self):
        from pabt.ho_so import dong_duoi_ten
        self.assertEqual(dong_duoi_ten('Phan Văn Minh', f'Đất do UBND xã quản lý.; {CHU_SO_HUU}'), CHU_SO_HUU)
        self.assertEqual(dong_duoi_ten('Phan Văn Minh', 'Đất do UBND xã quản lý.'), '')
        self.assertEqual(dong_duoi_ten('Phan Văn Minh là chủ sở hữu nhà', 'là chủ sở hữu nhà'), 'Là chủ sở hữu nhà')  # không lặp
        self.assertEqual(dong_duoi_ten('', None), '')

    def test_bang_kinh_phi(self):
        self.dat()
        from pabt.man_hinh_theo_doi import KhungTongHopTien
        k = KhungTongHopTien(self.con)
        self.addCleanup(k.deleteLater)
        k.resize(1500, 600)
        k.show()
        k.nap()
        b = k.bang
        chu = [str(b.model().index(r, k.C_TEN).data()) for r in range(b.model().rowCount())]
        self.assertEqual(sum(CHU_SO_HUU in x for x in chu), 1)

    def test_danh_sach_ho_cao_theo_chu(self):
        self.dat()
        self.con.close()
        self.con = csdl.mo(self.p)
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        w.hoi_luu = lambda: True
        self.addCleanup(w.close)
        w.resize(1400, 800)
        w.show()
        with self.con:
            pass
        self.con.close()
        w.mo(str(self.p))
        self.con = csdl.mo(self.p, chi_doc=True)
        w.mo_trang(ud.TRANG_DS)
        for _ in range(3):
            self.app.processEvents()
        nguon = w.loc.sourceModel()
        co = [r for r in range(w.loc.rowCount()) if w.loc.index(r, 1).data(g.VAI_PHU_TEN)]
        self.assertEqual(len(co), 1)
        r = co[0]
        self.assertEqual(w.loc.index(r, 1).data(), 'Hộ thử 1')          # chữ ô vẫn là tên
        khac = next(x for x in range(w.loc.rowCount()) if x != r)
        self.assertGreater(w.bang.rowHeight(r), w.bang.rowHeight(khac))
        self.assertIsNotNone(nguon)
        self.assertFalse(w.bang.grab().isNull())


class TestChuanChungTachTen(unittest.TestCase):
    def test_tach_duoc(self):
        from pabt.ho_so import tach_ho_ten
        for vao, ten, dg in (
                ('Phan Văn Minh xây dựng trên một phần thửa đất số 5, tờ bản đồ số 3 của ông bà Lê Văn A',
                 'Phan Văn Minh', 'Xây dựng trên một phần thửa đất số 5, tờ bản đồ số 3 của ông bà Lê Văn A'),
                ('Nguyễn Thị Hoa có nhà tạm trên đất công', 'Nguyễn Thị Hoa', 'Có nhà tạm trên đất công'),
                ('Trần Văn Nam thuê đất của xã', 'Trần Văn Nam', 'Thuê đất của xã'),
                ('Phan Văn Minh là chủ sở hữu tài sản', 'Phan Văn Minh', 'Là chủ sở hữu tài sản')):
            self.assertEqual(tach_ho_ten(vao), (ten, dg), vao)

    def test_khong_tach_khi_khong_chac(self):
        from pabt.ho_so import tach_ho_ten
        for s in ('UBND xã Phú Lý quản lý đất công', 'Công ty TNHH Một thành viên Xây dựng số 5', 'Hợp tác xã Nông nghiệp Trị An quản lý chung',
                  'Nguyễn Văn An và bà Lê Thị Bình cùng sử dụng', 'Nguyễn Văn An, Lê Thị Bình cùng sử dụng', 'Lê Thị Mỹ dung',
                  'Hộ ông Nguyễn Văn A xây nhà trên đất', 'phan văn minh xây dựng trên đất', 'Trường Tiểu học Phú Lý quản lý sân chơi', 'Nguyễn Văn An'):
            self.assertEqual(tach_ho_ten(s)[1], '', s)

    def test_ban_in_ghi_lien(self):
        from pabt.ho_so import ten_day_du_in
        self.assertEqual(ten_day_du_in('Phan Văn Minh', 'Đất do UBND.; Là chủ sở hữu tài sản'), 'Phan Văn Minh là chủ sở hữu tài sản')
        self.assertEqual(ten_day_du_in('Phan Văn Minh', '', 'Xây dựng trên đất ông A'), 'Phan Văn Minh xây dựng trên đất ông A')
        self.assertEqual(ten_day_du_in('Phan Văn Minh xây dựng trên đất ông A'), 'Phan Văn Minh xây dựng trên đất ông A')
        self.assertEqual(ten_day_du_in('Phan Văn Minh'), 'Phan Văn Minh')


class TestOGhiChuDuoiTen(_Nen):
    def test_luu_va_hien(self):
        from pabt import ho_so
        d = ho_so.doc_ho(self.con, self.ma[0])
        ho_so.luu_ho(self.con, self.ma[0], dict(ho_ten=d['ho_ten'], ghi_chu_ten='Xây dựng trên đất của ông A'), d['thua'])
        self.assertEqual(ho_so.doc_ho(self.con, self.ma[0])['ghi_chu_ten'], 'Xây dựng trên đất của ông A')
        self.assertEqual(ho_so.dong_duoi_ten('Nguyễn A', 'Là chủ sở hữu nhà', 'Ghi khác'), 'Ghi khác; Là chủ sở hữu nhà')

    def test_ban_in_word_va_tong_hop(self):
        from pabt import du_lieu_in, ho_so, in_an
        d = ho_so.doc_ho(self.con, self.ma[0])
        ho_so.luu_ho(self.con, self.ma[0], dict(ho_ten=d['ho_ten'], ghi_chu_ten='Xây dựng trên đất của ông A'), d['thua'])
        tt = du_lieu_in._thong_tin_ho(self.con, self.ma[0], du_lieu_in._thong_tin_du_an(self.con))
        self.assertEqual(tt['ho_ten'], d['ho_ten'])                     # tên sheet, nhận tổ chức: chỉ tên
        self.assertEqual(tt['ho_ten_in'], f'{d["ho_ten"]} xây dựng trên đất của ông A')
        import openpyxl
        f = self.td / 'bth.xlsx'
        in_an.lap_bang_tong_hop(self.con, str(f))
        chu = [str(o.value) for ws in openpyxl.load_workbook(f).worksheets for hang in ws.iter_rows() for o in hang if o.value]
        self.assertTrue(any('xây dựng trên đất của ông A' in x and d['ho_ten'] in x for x in chu))

    def test_file_cu_chua_co_cot(self):
        import sqlite3
        if sqlite3.sqlite_version_info < (3, 35):
            self.skipTest('SQLite cũ không xóa được cột')
        with self.con:
            if csdl.co_cot_ghi_chu_ten(self.con):
                self.con.execute('ALTER TABLE ho DROP COLUMN ghi_chu_ten')
        self.assertEqual(csdl.sql_ghi_chu_ten(self.con), "'' AS ghi_chu_ten")
        from pabt import ho_so
        d = ho_so.doc_ho(self.con, self.ma[0])
        self.assertEqual(d['ghi_chu_ten'], '')
        self.assertIn('cot_ghi_chu_ten', csdl.thieu_mo_rong(self.con))
        ho_so.luu_ho(self.con, self.ma[0], dict(ho_ten=d['ho_ten'], ghi_chu_ten='X y z'), d['thua'])
        self.assertTrue(csdl.co_cot_ghi_chu_ten(self.con))

    def test_them_cot_khong_doi_dau_vet_ho(self):
        """Máy khác mở file làm thêm cột không được báo XUNG ĐỘT giả cho hộ đang nhận về; có nội dung thì mới tính là đã sửa."""
        import sqlite3
        from pabt import may_chu
        if sqlite3.sqlite_version_info < (3, 35):
            self.skipTest('SQLite cũ không xóa được cột')
        with self.con:
            if csdl.co_cot_ghi_chu_ten(self.con):
                self.con.execute('ALTER TABLE ho DROP COLUMN ghi_chu_ten')
        truoc = may_chu.dau_vet_ho(self.con, self.ma)
        with self.con:
            csdl.dam_bao_cot_ghi_chu_ten(self.con)
        self.assertEqual(may_chu.dau_vet_ho(self.con, self.ma), truoc)
        with self.con:
            self.con.execute("UPDATE ho SET ghi_chu_ten = 'Ghi chú' WHERE ma_ho = ?", (self.ma[0],))
        sau = may_chu.dau_vet_ho(self.con, self.ma)
        self.assertNotEqual(sau[self.ma[0]], truoc[self.ma[0]])
        self.assertEqual(sau[self.ma[1]], truoc[self.ma[1]])

    def test_them_ho_moi(self):
        from pabt import ho_so
        ma = ho_so.luu_ho(self.con, None, dict(ho_ten='Hộ Mới', ghi_chu_ten='Ghi chú A'), [])
        self.assertEqual(ho_so.doc_ho(self.con, ma)['ghi_chu_ten'], 'Ghi chú A')


class TestHopInWindows(_Nen):
    def test_may_in_theo_tuy_chon(self):
        from pabt import xem_truoc_tai_lieu as xt
        if not xt.co_hop_in():
            self.skipTest('bản Qt5 không có hộp in')
        from PySide6.QtPrintSupport import QPrinter
        from tests.test_in_mot_ho_nhieu_ho import may_in_gia     # 1.0.98: không phụ thuộc máy in thật có in hai mặt hay không
        with may_in_gia():
            p = xt.may_in_theo_tuy_chon('', 3, False, 'dai', 'Thử')
        self.assertEqual((p.copyCount(), p.collateCopies(), p.duplex(), p.docName()), (3, False, QPrinter.DuplexMode.DuplexLongSide, 'Thử'))


if __name__ == '__main__':
    unittest.main()
