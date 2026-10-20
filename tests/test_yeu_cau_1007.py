"""1.0.07 (người dùng 20/10/2026): bộ mẫu in nhúng trong mã (máy trắng), bảng tổng hợp A3 ngang 55% chữ 14 / 16 pt, phương án chi
tiết (tiêu đề 16 pt đậm, mục I không viền, CCCD / điện thoại dạng chữ, nguồn gốc 8 NBSP, "II. …:"), tổng quan dự án ở Màn hình chính,
cuộn mượt / Enter xuống / Ctrl+D trên bảng, thân hộp thoại cuộn khi cao hơn màn hình, thông báo nổi."""
from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl  # noqa: E402

from tests.test_toc_do import _du_an  # noqa: E402


class _Co(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))

    def tearDown(self):
        self.doCleanups()
        self.tmp.cleanup()

    def _con(self, n: int = 6):
        from pabt import csdl
        con = csdl.mo(_du_an(self.td, n))
        self.addCleanup(con.close)
        return con


class TestMauNhung(_Co):
    def test_ban_nhung_khop_file_mau(self):
        """Bản nhúng = đúng các file trong mau_in\\ (sửa mẫu chuẩn thì chạy lại tao_mau_nhung.py)."""
        import hashlib
        from pabt import mau_in_nhung
        goc = Path(__file__).resolve().parents[1] / 'mau_in'
        for ten_hang, f, _ in __import__('tao_mau_nhung').DS:
            self.assertEqual(mau_in_nhung.SHA256[ten_hang], hashlib.sha256((goc / f).read_bytes()).hexdigest(),
                             f'{f} đã đổi - chạy tao_mau_nhung.py')
        self.assertEqual(mau_in_nhung.lay_bytes_mau('IN_CHITIET.xlsx'), (goc / 'IN_CHITIET.xlsx').read_bytes())
        self.assertTrue(mau_in_nhung.lay_duong_ke('IN_BANGTONGHOP'))

    def test_may_trang_in_duoc_tu_ram(self):
        from pabt import in_an
        con = self._con(4)
        with mock.patch.dict(os.environ, {'PABT_CHI_MAU_NHUNG': '1'}):
            self.assertEqual(in_an.thu_muc_mau(), in_an.THU_MUC_NHUNG)
            self.assertFalse(in_an.THU_MUC_NHUNG.exists())          # thư mục ảo: không bao giờ tạo trên đĩa
            p1 = in_an.lap_chi_tiet(con, 1, self.td / 'ct.xlsx')
            p2 = in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx')
            self.assertFalse(in_an.THU_MUC_NHUNG.exists())
            sua = in_an.mau_de_sua()                                 # mở mẫu sửa trên máy trắng: chép mẫu nhúng ra thư mục ghi
            self.assertTrue(sua.exists())
        for p in (p1, p2):
            with zipfile.ZipFile(p) as z:
                self.assertTrue(any(n.startswith('xl/drawings/') for n in z.namelist()), p)     # đường kẻ nhúng đã chèn


class TestBangTongHopA3(_Co):
    def test_a3_55_chu_14_16(self):
        from pabt import in_an
        con = self._con(8)
        p = in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx')
        wb = openpyxl.load_workbook(p)
        ws = wb.active
        self.assertEqual(ws.page_setup.paperSize, in_an.KHO_GIAY_BTH)
        self.assertEqual(ws.page_setup.orientation, 'landscape')
        self.assertFalse(ws.sheet_properties.pageSetUpPr.fitToPage)
        self.assertLessEqual(int(ws.page_setup.scale), in_an.TI_LE_BTH)
        self.assertIn(in_an.TEN_GIU_TI_LE, wb.defined_names)
        co = {(o.row < in_an.DONG_DAU_BTH, bool(o.font.b), float(o.font.sz)) for o in ws._cells.values()
              if isinstance(o.value, str) and o.value.strip()}
        self.assertNotIn(20.0, {c for *_, c in co})
        for tren, dam, c in co:
            if tren and dam:
                self.assertEqual(c, in_an.CO_TIEU_DE)
            elif not tren:
                self.assertEqual(c, in_an.CO_NOI_DUNG)

    def test_vua_ngang_a3(self):
        """Cột chữ chia lại cho tổng bề rộng vừa khổ A3 ở 55% (số liệu thường không làm tỷ lệ in nhỏ hơn 55%)."""
        from pabt import in_an
        wb = openpyxl.Workbook()
        ws = wb.active
        in_an.dat_kho_a3(ws)
        in_an.chuan_le_trang(ws, 'tong_hop')
        for c, w in zip('ABCDE', (6, 60, 80, 20, 20)):
            ws.column_dimensions[c].width = w
            ws.column_dimensions[c].reindex()             # khai báo cột mới tạo chưa có min / max (file nạp từ đĩa thì có)
        tong = in_an.vua_ngang_a3_bth(ws, 5, (2, 3))
        self.assertAlmostEqual(tong, in_an.rong_in_a3(ws) * 0.99, delta=12)
        self.assertEqual(in_an.dat_ti_le_co_dinh(ws, 5), in_an.TI_LE_BTH)
        for c in 'ADE':                                    # bảng quá rộng (cột không thu được): in nhỏ hơn, không tách cột
            ws.column_dimensions[c].width = 200
        self.assertLess(in_an.dat_ti_le_co_dinh(ws, 5), in_an.TI_LE_BTH)


class TestChiTiet(_Co):
    def _in(self, con, **sua):
        from pabt import in_an
        with con:
            for k, v in sua.items():
                bang = 'thua' if k == 'nguon_goc' else 'ho'
                con.execute(f'UPDATE {bang} SET {k} = ? WHERE ma_ho = 1', (v,))
        p = in_an.lap_chi_tiet(con, 1, self.td / 'ct.xlsx')
        return p, openpyxl.load_workbook(p).active

    def test_muc_i_khong_vien_va_so_dang_chu(self):
        from pabt import in_an
        con = self._con(2)
        p, ws = self._in(con, dien_thoai='0912345678', so_cccd='075092001234')
        r_i = next(o.row for o in in_an._o_chu(ws) if o.value.startswith('I. '))
        r_ii = next(o.row for o in in_an._o_chu(ws) if o.value.startswith('II.'))
        for (r, c), o in ws._cells.items():
            if r_i <= r < r_ii:
                self.assertFalse(any(getattr(o.border, k).style for k in ('left', 'right', 'top', 'bottom')), o.coordinate)
        sdt = next(o for o in ws._cells.values() if o.value == '0912345678')
        self.assertEqual(sdt.number_format, '@')
        with zipfile.ZipFile(p) as z:
            x = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
        self.assertIn('numberStoredAsText="1"', x)
        self.assertIn(sdt.coordinate, x[x.index('<ignoredErrors'):])
        self.assertEqual(ws.cell(r_ii, 1).value, in_an.TIEU_DE_MUC_II)
        self.assertTrue(in_an.TIEU_DE_MUC_II.endswith(':'))

    def test_co_chu_tieu_de_16_noi_dung_14(self):
        from pabt import in_an
        con = self._con(2)
        _, ws = self._in(con)
        hang_td = next(o.row for o in ws._cells.values() if str(o.value or '').strip().upper() == 'STT')
        for o in ws._cells.values():
            if not (isinstance(o.value, str) and o.value.strip()) or o.column > 8:     # cột loại dòng (AD) ẩn: bỏ qua
                continue
            v = o.value.strip()
            if o.row == hang_td or in_an._RE_TIEU_DE_MUC.match(v) or v.startswith('CỘNG HÒA') or v.startswith('DỰ ÁN'):
                self.assertEqual((float(o.font.sz), bool(o.font.b)), (in_an.CO_TIEU_DE, True), v[:30])
        o_ten = next(o for o in ws._cells.values() if o.value == 'Họ và tên:')
        self.assertEqual(float(o_ten.font.sz), in_an.CO_NOI_DUNG)

    def test_nguon_goc_8_nbsp_bo_cach_thua(self):
        from pabt import in_an
        con = self._con(2)
        _, ws = self._in(con, nguon_goc='Đất do ông bà để lại sử dụng ổn định.\n    -   Phần đất ở: 300 m2.')
        dong = [o.value for o in ws._cells.values() if isinstance(o.value, str) and o.value.startswith(in_an.NBSP)]
        self.assertTrue(dong)
        for x in dong:
            self.assertTrue(x.startswith(in_an.NBSP * 8) and not x.startswith(in_an.NBSP * 9), repr(x[:12]))
        self.assertTrue(any(x.lstrip(in_an.NBSP).startswith('- Phần đất ở') for x in dong), dong)


class TestTongQuan(_Co):
    def test_so_lieu_khong_qt(self):
        from pabt import tong_quan_du_an as tq
        from pabt.tien import D
        dong = [dict(ma_ho=1, tong=D(100), muc={1: D(60)}, dt=D(5000), da_phe_duyet=True, da_ban_giao=True, da_lap=True,
                     o=[1, 'A', '', 2, 0, 'Đã bàn giao', '']),
                dict(ma_ho=2, tong=D(50), muc={1: D(10)}, dt=D(5000), da_phe_duyet=False, da_ban_giao=False, da_lap=False,
                     o=[2, 'B', '', 1, 0, '', ''])]
        self.assertEqual(tq.quy_mo(dong)['so_thua'], 3)
        self.assertEqual(tq.quy_mo(dong)['dt_ha'], D(1))
        self.assertEqual(tq.kinh_phi(dong), dict(tong=D(150), dat=D(70), con_lai=D(80)))
        td = tq.tien_do(dong)
        self.assertEqual((td['da_pd'], td['da_bg'], td['n']), (1, 1, 2))
        self.assertEqual([x['ma_ho'] for x in tq.ho_dang_lam(dong)], [2])

    def test_man_hinh_chinh_khi_mo_du_an(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        self.assertEqual(w.ngan_chao.currentIndex(), 0)                 # chưa mở dự án: màn hình chào
        d = self.td / 'd'
        d.mkdir()
        w.mo(str(_du_an(d, 5)))
        w.ve_trang_chu()
        app.processEvents()
        self.assertIs(w.ngan_chao.currentWidget(), w.tong_quan)
        tq = w.tong_quan
        self.assertEqual(set(tq.the_khoi_tao), {'Dự án mới…', 'Mở dự án…', 'Nhập file Excel…', 'Nhập phương án chi tiết…'})
        self.assertIn('5 hộ', tq.kpi.the['quy_mo'].lb_so.text())
        n = tq.so_lieu['so_ho_dang_lam']
        self.assertEqual(tq.bang.rowCount(), min(n, 200))
        mo = []
        with mock.patch.object(w, 'mo_lap_pa', lambda m, *a, **k: mo.append(m)):
            if tq.bang.rowCount():
                tq.bang.cellWidget(0, 4).click()
                self.assertEqual(mo, [tq.so_lieu['ho_dang_lam'][0]['ma_ho']])
        w.dong_du_an_lenh()
        self.assertEqual(w.ngan_chao.currentIndex(), 0)


class TestTuongTac(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _bang(self):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        from pabt import giao_dien
        b = QTableWidget(5, 2)
        for r in range(5):
            for c in range(2):
                b.setItem(r, c, QTableWidgetItem(f'{r}{c}'))
        giao_dien.cho_phep_sao_chep_bang(b)
        return b

    def test_cuon_muot(self):
        from PySide6.QtWidgets import QAbstractItemView as V
        b = self._bang()
        self.assertEqual(b.verticalScrollMode(), V.ScrollMode.ScrollPerPixel)
        self.assertEqual(b.horizontalScrollMode(), V.ScrollMode.ScrollPerPixel)
        self.assertEqual(b.verticalScrollBar().singleStep(), 20)

    def test_ctrl_d_chep_o_tren_xuong(self):
        from PySide6.QtCore import QItemSelectionModel
        from pabt import giao_dien
        b = self._bang()
        sm = b.selectionModel()
        for r in (1, 2, 3):
            sm.select(b.model().index(r, 0), QItemSelectionModel.SelectionFlag.Select)
        self.assertEqual(giao_dien.dien_xuong(b), 2)                   # ô trên cùng vùng chọn (1,0) chép xuống 2 ô
        self.assertEqual([b.item(r, 0).text() for r in range(5)], ['00', '10', '10', '10', '40'])
        sm.clearSelection()
        b.setCurrentCell(4, 1)
        self.assertEqual(giao_dien.dien_xuong(b), 1)                   # một ô: chép ô ngay trên
        self.assertEqual(b.item(4, 1).text(), '31')

    def test_enter_xuong_o_duoi(self):
        from pabt import giao_dien
        b = self._bang()
        b.setCurrentCell(1, 1)
        b.setRowHidden(2, True)
        self.assertTrue(giao_dien.o_duoi(b))
        self.assertEqual((b.currentRow(), b.currentColumn()), (3, 1))   # bỏ dòng ẩn
        b.setCurrentCell(4, 0)
        self.assertFalse(giao_dien.o_duoi(b))

    def test_than_hop_cuon_khi_cao_hon_man_hinh(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QScrollArea, QVBoxLayout
        from pabt import giao_dien
        d = QDialog()
        lo = QVBoxLayout(d)
        for i in range(30):
            o = QLabel(f'dòng {i}')
            o.setMinimumHeight(40)
            lo.addWidget(o)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        lo.addWidget(nut)
        self.assertTrue(giao_dien.cuon_than_hop(d, 500))
        self.assertIsInstance(lo.itemAt(0).widget(), QScrollArea)
        self.assertIs(lo.itemAt(1).widget(), nut)                      # hàng nút nằm ngoài vùng cuộn
        self.assertLessEqual(d.maximumHeight(), 500)
        self.assertFalse(giao_dien.cuon_than_hop(d, 500))              # không bọc hai lần
        d2 = QDialog()
        QVBoxLayout(d2).addWidget(QLabel('ngắn'))
        QVBoxLayout() and d2.layout().addWidget(QDialogButtonBox(QDialogButtonBox.StandardButton.Ok))
        self.assertFalse(giao_dien.cuon_than_hop(d2, 500))             # vừa màn hình: không đổi

    def test_thong_bao_noi(self):
        from PySide6.QtWidgets import QMainWindow
        from pabt import giao_dien
        w = QMainWindow()
        w.resize(800, 500)
        w.show()
        h = giao_dien.thong_bao_noi(w, 'Đã lưu dữ liệu an toàn', 'dat', ms=50)
        self.assertTrue(h.isVisible())
        self.assertIs(giao_dien.thong_bao_noi(w, 'Đã hoàn tác: x'), h)      # dùng lại một khung
        self.assertGreater(h.x() + h.width(), 700)                         # góc dưới phải
        self.assertGreater(h.y(), 300)
        w.close()


if __name__ == '__main__':
    unittest.main()


class TestQuanLyMau(_Co):
    def test_xuat_thay_khoi_phuc(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import in_an
        from pabt.man_hinh_quan_ly_mau import HopQuanLyMauIn
        hop = HopQuanLyMauIn(im_lang=True)
        self.addCleanup(hop.deleteLater)
        self.assertEqual(hop.bang.rowCount(), 3)
        self.assertEqual({hop.bang.item(r, 2).text() for r in range(3)}, {in_an.NHUNG})
        hop.bang.selectRow(2)                                           # bảng tổng hợp
        f = hop.xuat(self.td / 'xuat' / 'BTH.xlsx')
        wb = openpyxl.load_workbook(f)
        wb.active.page_setup.paperSize = 9                              # người dùng sửa: A4, tỷ lệ 20%
        wb.active.page_setup.scale = 20
        wb.active['A5'] = 'BẢNG TỔNG HỢP ĐÃ SỬA {du_an}'
        wb.save(f)
        p = hop.thay(f)
        self.assertEqual(p, in_an.thu_muc_mau_tuy_chinh() / 'IN_BANGTONGHOP.xlsx')
        self.assertEqual(hop.bang.item(2, 2).text(), in_an.TUY_CHINH)
        ws = openpyxl.load_workbook(p).active                           # bộ lọc áp chuẩn: A3 55%
        self.assertEqual((ws.page_setup.paperSize, int(ws.page_setup.scale)), (8, 55))
        self.assertEqual(in_an.thu_muc_mau(in_an.TEN_BTH), in_an.thu_muc_mau_tuy_chinh())     # in dùng ngay mẫu mới
        con = self._con(3)
        b = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'b.xlsx')).active
        self.assertTrue(any(isinstance(o.value, str) and 'ĐÃ SỬA' in o.value for o in b._cells.values()))
        self.assertTrue(hop.khoi_phuc(xac_nhan=True))
        self.assertEqual(hop.bang.item(2, 2).text(), in_an.NHUNG)
        self.assertTrue(list((in_an.thu_muc_mau_tuy_chinh() / 'cu').glob('*IN_BANGTONGHOP.xlsx')))   # mẫu cũ giữ bản sao

    def test_mau_du_thao_tuy_chinh_dung_cho_ban_du_thao(self):
        from pabt import in_an
        f = in_an.xuat_mau(in_an.TEN_DT_QL, self.td / 'dt.xlsx')
        wb = openpyxl.load_workbook(f)
        wb.active['J1'] = 'MẪU DỰ THẢO RIÊNG'
        wb.save(f)
        in_an.thay_mau(in_an.TEN_DT_QL, f)
        ws = openpyxl.load_workbook(in_an.thu_muc_mau_tuy_chinh() / f'{in_an.TEN_DT_QL}.xlsx').active
        self.assertEqual((ws.page_setup.paperSize, int(ws.page_setup.scale)), (9, in_an.TI_LE_CT))
        con = self._con(2)
        dt = openpyxl.load_workbook(in_an.lap_chi_tiet(con, 1, self.td / 'a.xlsx', du_thao=True)).active
        ct = openpyxl.load_workbook(in_an.lap_chi_tiet(con, 1, self.td / 'b.xlsx', du_thao=False)).active
        self.assertEqual(dt['J1'].value, 'MẪU DỰ THẢO RIÊNG')
        self.assertNotEqual(ct['J1'].value, 'MẪU DỰ THẢO RIÊNG')


class TestChiTietA4(_Co):
    def test_a4_72_le_cm_ghi_chu_115_chu_ky(self):
        from pabt import in_an
        con = self._con(2)
        for du_thao in (False, True):
            p = in_an.lap_chi_tiet(con, 1, self.td / f'ct{du_thao}.xlsx', du_thao=du_thao)
            wb = openpyxl.load_workbook(p)
            ws = wb.active
            self.assertEqual((ws.page_setup.paperSize, ws.page_setup.orientation), (9, 'portrait'))
            self.assertFalse(ws.sheet_properties.pageSetUpPr.fitToPage)
            self.assertTrue(in_an.TI_LE_CT_MIN <= int(ws.page_setup.scale) <= in_an.TI_LE_CT)
            m = ws.page_margins
            self.assertEqual([round(x * 2.54, 2) for x in (m.left, m.right, m.top, m.bottom)], [0.8, 0.3, 1.0, 0.8])
            dau = next(o.row for o in ws._cells.values() if str(o.value or '').strip().upper() == 'STT') + 1
            self.assertEqual(float(ws.cell(dau, 8).font.sz), in_an.CO_GHI_CHU_CT)
            self.assertEqual(float(ws.cell(dau, 2).font.sz), in_an.CO_NOI_DUNG)
            ky = [o for o in ws._cells.values() if isinstance(o.value, str) and o.value.strip() in ('LẬP BIỂU', 'KIỂM TRA')]
            self.assertTrue(ky)
            self.assertEqual(all(ws.row_dimensions[o.row].hidden for o in ky), du_thao)    # dự thảo: ẩn khối chữ ký
            nhan = next(o for o in ws._cells.values() if o.value == 'Họ và tên:')
            ten = ws.cell(nhan.row, 3)
            self.assertTrue(nhan.font.b)
            self.assertFalse(ten.font.b)                                     # mục I: nhãn đậm, nội dung thường
