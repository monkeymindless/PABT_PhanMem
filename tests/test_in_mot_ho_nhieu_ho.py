"""05/11/2026 (người dùng): bảng In theo cấu trúc bảng In của Word: cột trái In | Xuất | Xuất dữ liệu; nút In + Số bản sao; Máy in; Thiết đặt. Mặc định Dự thảo, lưu vào thư mục chứa file dự án; định dạng Word / Excel / PDF độc lập."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl
from pabt.lap_pa import LoiNhap

from tests import APP


def _gia_pdf(viec, **kw):
    """Thay Word: viết file PDF giả đúng chỗ."""
    for _che_do, _nguon, dich in viec:
        if dich:
            Path(dich).write_bytes(b'%PDF-1.4 thu')
    return []


class TestDaySo(unittest.TestCase):
    def test_doc_day_so(self):
        from pabt.thanh_phan_in import chu_day_so, doc_day_so
        self.assertEqual(doc_day_so(''), [])
        self.assertEqual(doc_day_so('1-3, 5'), [1, 2, 3, 5])
        self.assertEqual(doc_day_so('5; 2 - 3, 2'), [5, 2, 3])
        for sai in ('a', '3-1', '1-', '0'):
            with self.assertRaises(LoiNhap):
                doc_day_so(sai)
        self.assertEqual(chu_day_so([5, 1, 2, 3]), '1-3, 5')
        self.assertEqual(chu_day_so([]), '')


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestBangIn(unittest.TestCase):
    def setUp(self):
        from tests.test_phien_ban_pa import _du_an as tao
        self.td = Path(tempfile.mkdtemp(prefix='pabt_in_'))
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if self._cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', self._cu))
        (self.td / 'duan').mkdir()
        self.p = tao(self.td / 'duan', 3)
        self.con = csdl.mo(str(self.p))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def _hop(self, **kw):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=str(self.p), **kw)
        h.im_lang = True
        self.addCleanup(h.w_preview.don_dep)
        return h

    def test_mo_mac_dinh_du_thao_o_muc_in_luu_vao_thu_muc_du_an(self):
        h = self._hop(ma_ho_chon=self.ma[:1])
        self.assertEqual(h.che_do(), 'du_thao')
        self.assertEqual(h.hang_che_do.gia_tri(), 'du_thao')
        self.assertEqual(h._rail, 'in')
        self.assertEqual(Path(h.o_thu_muc.text()).parent, self.p.parent)
        self.assertEqual(h.lb_luu.toolTip(), h.o_thu_muc.text())
        self.assertFalse(h.khung_nut_in.isHidden() or h.khung_may_in.isHidden())
        self.assertTrue(h.khung_nut_xuat.isHidden() and h.khung_xuat_them.isHidden())
        h.dat_pham_vi('xuat')
        self.assertTrue(h.khung_nut_in.isHidden() and h.khung_may_in.isHidden())
        self.assertFalse(h.khung_nut_xuat.isHidden() or h.khung_xuat_them.isHidden())

    def test_khong_nho_thu_muc_lan_truoc(self):
        class Cd(dict):
            def value(self, k, md=None):
                return self.get(k, md)
            setValue = dict.__setitem__
        cd = Cd({'in/thu_muc_cha': str(self.td)})
        with mock.patch('pabt.giao_dien.cai_dat_nho', lambda: cd):
            h = self._hop()
        self.assertEqual(Path(h.o_thu_muc.text()).parent, self.p.parent)

    def test_mot_ho_chi_co_phan_can_thiet(self):
        h = self._hop(ma_ho_chon=[self.ma[1]])
        self.assertEqual(h.pham_vi_in(), 'mot')
        self.assertEqual(h.ds_ho(), [self.ma[1]])
        self.assertTrue(h.bang_ho.isColumnHidden(0))
        for w in (h.khung_kem, h.o_gop, h.b_chon_het):
            self.assertTrue(w.isHidden())
        self.assertEqual([x[0] for x in h.hang_tai_lieu._ds], ['ct', 'ct_excel'])
        self.assertTrue(h.o_ho.text().startswith('2.'))
        h.sang_ho(1)                                                                 # hộ sau
        self.assertEqual(h.ds_ho(), [self.ma[2]])
        h.o_ho.setText('1')                                                          # gõ STT
        h._nhap_o_ho()
        self.assertEqual(h.ds_ho(), [self.ma[0]])

    def test_mot_ho_chi_xuat_phuong_an_khong_chia_thu_muc(self):
        h = self._hop(ma_ho_chon=[self.ma[0]])
        h.o_bth.setChecked(True)                                                     # còn tích từ nhiều hộ: một hộ không xuất
        h.r_excel.setChecked(True)
        tm = self.p.parent / 'ra'
        h.o_thu_muc.setText(str(tm))
        kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual([f.parent for f in kq['word']], [tm])
        self.assertEqual(kq['excel'], [])
        self.assertFalse((tm / 'PA TONG').exists())

    def test_nhieu_ho_tai_lieu_theo_che_do_o_ho_nhu_o_trang(self):
        h = self._hop()
        self.assertEqual(h.pham_vi_in(), 'nhieu')
        self.assertEqual([x[0] for x in h.hang_tai_lieu._ds], ['ct', 'ct_gop', 'ct_excel', 'bth'])
        self.assertFalse(h.khung_kem.isHidden() or h.o_gop.isHidden())
        self.assertTrue(h.o_tt.isHidden())                                           # Dự thảo
        h.hang_che_do.dat('chinh_thuc')
        self.assertEqual(h.che_do(), 'chinh_thuc')
        self.assertFalse(h.o_tt.isHidden())
        self.assertIn('tt', [x[0] for x in h.hang_tai_lieu._ds])
        h.hang_tai_lieu.dat('tt', im=True)
        h.hang_che_do.dat('du_thao')
        self.assertEqual(h.tai_lieu(), 'ct')                                         # tờ trình không có ở Dự thảo: về phương án chi tiết
        h.o_ho.setText('1-2')                                                        # như ô Trang của Word
        h._nhap_o_ho()
        self.assertEqual(h.ds_ho(), self.ma[:2])
        self.assertEqual(h.hang_pham_vi.gia_tri(), 'tu_chon')
        self.assertIn('2 hộ', h.b_thuc_hien.text())
        self.assertEqual(h.o_ho.text(), '1-2')
        h.o_ho.setText('Hộ thử')                                                     # gõ chữ: mở danh sách để tìm
        h._nhap_o_ho()
        self.assertTrue(h.b_chon_ho.isChecked())
        self.assertFalse(h.khung_chon_ho.isHidden())

    def test_chon_pham_vi_theo_dong(self):
        h = self._hop()
        h.hang_pham_vi.dat('tat_ca')
        self.assertEqual(h.ds_ho(), self.ma)
        h.hang_pham_vi.dat('mot')
        self.assertEqual(len(h.ds_ho()), 1)
        self.assertEqual(h.pham_vi_in(), 'mot')

    def test_chi_tich_pdf_thi_khong_de_lai_word(self):
        h = self._hop()
        h._danh_dau(self.ma[:2])
        h.o_bth.setChecked(False)
        h.o_ct.setChecked(False)
        h.o_pdf.setChecked(True)
        self.assertTrue(h.r_pdf.isChecked())
        h.o_thu_muc.setText(str(self.p.parent / 'ra'))
        with mock.patch('pabt.van_ban_trinh.chay_word', _gia_pdf):
            kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual(kq['word'], [])
        self.assertEqual(len([f for f in kq['pdf'] if f.name.startswith('PA_')]), 2)
        self.assertEqual(list((self.p.parent / 'ra' / 'PA CHI TIET').glob('PA_*.docx')), [])
        self.assertEqual(len(list((self.p.parent / 'ra' / 'PA CHI TIET').glob('PA_*.pdf'))), 2)

    def test_word_va_pdf_doc_lap_khong_tich_gi_thi_bao(self):
        h = self._hop()
        h.o_pdf.setChecked(False)
        self.assertTrue(h.r_excel.isChecked())
        h.r_pdf.setChecked(True)
        self.assertTrue(h.o_pdf.isChecked())
        h._danh_dau(self.ma[:1])
        h.o_bth.setChecked(False)
        h.o_ct.setChecked(False)
        h.o_pdf.setChecked(False)
        with mock.patch('PySide6.QtWidgets.QMessageBox.information') as bao:
            self.assertIsNone(h.thuc_hien(xac_nhan=False))
        bao.assert_called_once()

    def test_in_qua_office_khi_khong_co_qtpdf_tra_lai_dinh_dang(self):
        h = self._hop()
        h._in_pdf = False
        h._danh_dau(self.ma[:1])
        h.o_thu_muc.setText(str(self.p.parent / 'ra'))
        with mock.patch('pabt.van_ban_trinh.chay_word', side_effect=_gia_pdf) as w:
            kq = h.in_ra_may(xac_nhan=False)
        self.assertIsNotNone(kq)
        self.assertTrue(w.called)
        self.assertEqual(kq['excel'], [])                                            # đúng tài liệu đang xem: phương án chi tiết
        self.assertTrue(h.r_pdf.isChecked() and h.o_pdf.isChecked())

    def test_nut_in_gui_ban_dang_xem_toi_may_in_da_chon(self):
        from pabt import xem_truoc_tai_lieu as xt
        if not xt.co_hop_in():
            self.skipTest('cần QtPdf (bản Qt 6); bản Win 7 in qua Word / Excel')
        h = self._hop(ma_ho_chon=[self.ma[0]])
        h.o_so_ban.setValue(2)
        h.hang_mat.dat('dai', im=True)
        h.hang_xep_bo.dat(False, im=True)
        h.hang_kho.dat('A4', im=True)
        h.o_trang.setText('1-2')
        with mock.patch.object(h.w_preview, 'cho_xong', return_value=True), mock.patch.object(h.w_preview, 'so_trang', return_value=3), \
                mock.patch.object(xt, 'in_theo_tuy_chon', return_value=2) as may:
            self.assertEqual(h.in_ra_may(xac_nhan=False), 2)
        a = may.call_args[0]
        self.assertEqual((a[2], a[3], a[4], a[5], a[6]), (2, False, 'dai', 'A4', [1, 2]))
        h.o_trang.setText('abc')
        with mock.patch('PySide6.QtWidgets.QMessageBox.warning') as bao, mock.patch.object(xt, 'in_theo_tuy_chon') as may:
            self.assertIsNone(h.in_ra_may(xac_nhan=False))
        bao.assert_called_once()
        may.assert_not_called()

    def test_muc_xuat_du_lieu_dung_lai_lenh_cua_so_chinh(self):
        from pabt import app as ud
        from pabt.man_hinh import HopIn
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(self.p))
        APP.processEvents()
        d = HopIn(w.con, w, file_du_an=w.file)
        d.im_lang = True
        self.addCleanup(d.w_preview.don_dep)
        d.dat_pham_vi('du_lieu')
        self.assertFalse(d.khung_du_lieu.isHidden())
        self.assertTrue(d.khung_thiet_dat.isHidden() and d.phai.isHidden() and d.khung_nut_in.isHidden())
        self.assertEqual(set(d.nut_du_lieu), {'Xuất danh sách hộ…', 'Xuất báo cáo đối chiếu…'})
        for ten in d.nut_du_lieu:                                                    # một chỗ: không còn trên menu
            self.assertNotIn(w.lenh[ten], w.menu_tren['Dữ liệu'].actions())
        with mock.patch('pabt.app.QMessageBox.question', return_value=None), mock.patch('pabt.app.QFileDialog.getSaveFileName', side_effect=AssertionError('không hỏi nơi lưu')):
            d.nut_du_lieu['Xuất danh sách hộ…'].click()
            APP.processEvents()
        self.assertTrue(list(Path(w.file).parent.rglob('DanhSachHo_*.xlsx')))

    def test_mo_tu_lap_phuong_an_khong_co_muc_du_lieu(self):
        h = self._hop(ma_ho_chon=self.ma[:1])
        self.assertNotIn('du_lieu', h.nut_rail)


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestInTheoTuyChon(unittest.TestCase):
    def setUp(self):
        from pabt import xem_truoc_tai_lieu as xt
        if not xt.co_hop_in():
            self.skipTest('cần QtPdf (bản Qt 6)')
        from PySide6.QtCore import QMarginsF, QSizeF
        from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter
        from PySide6.QtPdf import QPdfDocument
        self.td = Path(tempfile.mkdtemp(prefix='pabt_may_in_'))
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        f = self.td / 'nguon.pdf'
        v = QPdfWriter(str(f))
        v.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        p = QPainter(v)
        for i in range(3):
            if i:
                v.newPage()
            p.drawText(100, 100, f'Trang {i + 1}')
        p.end()
        self.doc = QPdfDocument(None)
        self.doc.load(str(f))
        self.assertEqual(self.doc.pageCount(), 3)
        _ = (QMarginsF, QSizeF, QPageLayout)

    def _may_pdf(self, ten='ra.pdf'):
        from PySide6.QtPrintSupport import QPrinter
        pr = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        pr.setOutputFileName(str(self.td / ten))
        return pr

    def _so_trang(self, ten='ra.pdf'):
        from pypdf import PdfReader
        return PdfReader(str(self.td / ten))

    def test_in_dung_cac_trang_da_chon(self):
        from pabt import xem_truoc_tai_lieu as xt
        self.assertEqual(xt.in_tai_lieu(self.doc, self._may_pdf(), ds_trang=[1, 3]), 2)
        self.assertEqual(len(self._so_trang().pages), 2)

    def test_kho_a3_va_theo_ban_in(self):
        from pabt import xem_truoc_tai_lieu as xt
        self.assertEqual(xt.in_tai_lieu(self.doc, self._may_pdf('a3.pdf'), kho='A3'), 3)
        tr = self._so_trang('a3.pdf').pages[0]
        self.assertGreater(float(tr.mediabox.width), 800)                            # A3 rộng 842 pt
        self.assertEqual(xt.in_tai_lieu(self.doc, self._may_pdf('goc.pdf'), kho=''), 3)
        self.assertLess(float(self._so_trang('goc.pdf').pages[0].mediabox.width), 600)  # theo bản in: A4

    def test_xep_bo_khi_may_khong_tu_in_nhieu_ban(self):
        from pabt import xem_truoc_tai_lieu as xt
        pr = self._may_pdf('ban.pdf')
        pr.setCopyCount(2)
        pr.setCollateCopies(True)
        n = xt.in_tai_lieu(self.doc, pr, ds_trang=[1, 2])
        self.assertEqual(n, 4 if not pr.supportsMultipleCopies() else 2)

    def test_tuy_chon_dat_dung_may_in(self):
        from PySide6.QtPrintSupport import QPrinter
        from pabt import xem_truoc_tai_lieu as xt
        nhan = {}

        def gia(doc, printer, **k):
            nhan.update(ban=printer.copyCount(), xep=printer.collateCopies(), mat=printer.duplex(), k=k)
            return 1
        with mock.patch.object(xt, 'in_tai_lieu', gia):
            self.assertEqual(xt.in_theo_tuy_chon(self.doc, '', 3, False, 'ngan', 'A4', [2], 'x'), 1)
        self.assertEqual((nhan['ban'], nhan['xep'], nhan['mat']), (3, False, QPrinter.DuplexMode.DuplexShortSide))
        self.assertEqual(nhan['k'], dict(ds_trang=[2], kho='A4'))


if __name__ == '__main__':
    unittest.main()
