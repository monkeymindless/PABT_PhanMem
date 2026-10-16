"""Kiểm thử bản in / giao diện (người dùng 16/10/2026): hộp chọn máy in như Word / Excel (xem_truoc_tai_lieu.in_co_hop_thoai), bảng
tổng hợp (bỏ "(theo Quyết định số 08…)", cột số đủ rộng - không "#####", ngắt trang ở ranh giới hộ), phương án chi tiết (tiêu đề bảng
III không nằm trơ cuối trang, dòng thưởng ngắt dòng như mục 2-5), nút "HS đính kèm", đổi tỷ lệ giao diện trả lại con trỏ.
Dữ liệu giả lập (tests.test_toc_do._du_an); máy in = QPrinter ghi ra file PDF (không gửi máy in thật)."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import openpyxl
from PySide6.QtWidgets import QApplication

from pabt import csdl, giao_dien, in_an, xem_truoc_tai_lieu as xt
from tests.test_toc_do import _du_an

APP = QApplication.instance() or QApplication([])


def _pdf_trang(p: Path, ds_co: list) -> Path:
    """PDF giả lập: mỗi phần tử ds_co = (rộng, cao) pt của một trang."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter
    w = QPdfWriter(str(p))

    def bo(co):
        return QPageLayout(QPageSize(QSizeF(*co), QPageSize.Unit.Point), QPageLayout.Orientation.Portrait, QMarginsF())
    w.setPageLayout(bo(ds_co[0]))
    pt = QPainter(w)
    for i, co in enumerate(ds_co):
        if i:
            w.setPageLayout(bo(co))
            w.newPage()
        pt.drawText(200, 200, f'Trang {i + 1}')
    pt.end()
    return p


def _so_trang(p: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(str(p)).pages)


@unittest.skipUnless(xt.co_hop_in(), 'Qt5 (Win 7): không có QtPdf - chỉ "In nhanh" qua Excel')
class TestHopIn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        self.doc = QPdfDocument(None)
        p = _pdf_trang(self.td / 'nguon.pdf', [(595, 842), (842, 595), (595, 842)])
        self.buf = QBuffer()                                    # nạp từ bộ nhớ: load(đường dẫn) giữ khóa file
        self.buf.setData(QByteArray(p.read_bytes()))
        self.buf.open(QIODevice.OpenModeFlag.ReadOnly)
        self.doc.load(self.buf)

    def tearDown(self):
        self.doc.close()
        self.tmp.cleanup()

    def may_in(self, ten: str):
        from PySide6.QtPrintSupport import QPrinter
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        pr.setOutputFileName(str(self.td / ten))
        pr.setResolution(150)
        return pr

    def test_in_ca_tai_lieu_va_khoang_trang(self):
        self.assertEqual(xt.in_tai_lieu(self.doc, self.may_in('ca.pdf')), 3)
        self.assertEqual(_so_trang(self.td / 'ca.pdf'), 3)
        from pypdf import PdfReader
        trang = PdfReader(str(self.td / 'ca.pdf')).pages
        self.assertGreater(float(trang[1].mediabox.width), float(trang[1].mediabox.height))     # trang ngang in giấy ngang
        self.assertLess(float(trang[0].mediabox.width), float(trang[0].mediabox.height))
        self.assertEqual(xt.in_tai_lieu(self.doc, self.may_in('k.pdf'), 2, 3), 2)
        self.assertEqual(_so_trang(self.td / 'k.pdf'), 2)
        self.assertEqual(xt.in_tai_lieu(self.doc, self.may_in('x.pdf'), 3, 2), 0)

    def test_hop_thoai_khoang_trang_va_so_ban(self):
        from PySide6.QtPrintSupport import QPrinter
        pr = self.may_in('hop.pdf')
        pr.setPrintRange(QPrinter.PrintRange.PageRange)
        pr.setFromTo(1, 2)
        pr.setCopyCount(2)
        n = xt.in_co_hop_thoai(None, self.doc, 'Phương án hộ 1', pr, hoi=False)
        ban = 1 if pr.supportsMultipleCopies() else 2
        self.assertEqual(n, 2 * ban)
        self.assertEqual(_so_trang(self.td / 'hop.pdf'), 2 * ban)
        self.assertEqual(pr.docName(), 'Phương án hộ 1')

    def test_nut_in_tren_khung_xem_truoc(self):
        import shutil
        k = xt.KhungXemTruocTaiLieu(ham_in=lambda pdf, xlsx: None)
        self.assertEqual(k.b_in_hop.text(), 'In…')
        self.assertTrue(k.b_in_hop.isVisibleTo(k))
        self.assertFalse(k.b_in_hop.isEnabled())                # chưa có bản xem
        f = self.td / 'xem.pdf'
        shutil.copy2(self.td / 'nguon.pdf', f)
        k.nap_tai_lieu(f)
        self.assertTrue(k.b_in_hop.isEnabled())
        self.assertEqual(k.in_hop_thoai(self.may_in('khung.pdf'), hoi=False), 3)
        self.assertEqual(_so_trang(self.td / 'khung.pdf'), 3)
        k.don_dep()


class TestBangTongHop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.con = csdl.mo(_du_an(self.td, 8))

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_bo_can_cu_kinh_phi(self):
        chu = 'Kinh phí đảm bảo cho việc tổ chức thực hiện 2,5% (theo Quyết định số 08/2025/QĐ-UBND ngày 10/02/2025):'
        self.assertEqual(in_an.bo_can_cu_kinh_phi(chu), 'Kinh phí đảm bảo cho việc tổ chức thực hiện 2,5%:')
        self.assertEqual(in_an.bo_can_cu_kinh_phi('Không có căn cứ:'), 'Không có căn cứ:')

    def test_chu_so_excel(self):
        self.assertEqual(in_an._chu_so_excel(1234567, '#,##0'), '1.234.567')
        self.assertEqual(in_an._chu_so_excel(1234.5, '#,##0.0'), '1.234,5')
        self.assertEqual(in_an._chu_so_excel(-12, '#,##0'), '-12')

    def test_cot_so_rong_va_ngat_trang_giua_cac_ho(self):
        with self.con:
            self.con.execute("UPDATE ct_dat SET dien_tich = '21243', gia_bang_gia = '45000000'")
            self.con.execute('UPDATE thua SET nguon_goc = ?', ('- Nguồn gốc đất giả lập rất dài để dòng hộ cao. ' * 30,))
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        ws = openpyxl.load_workbook(f).active
        self.assertFalse(ws.sheet_properties.pageSetUpPr.fitToPage)             # Excel bỏ qua ngắt tay khi "vừa N trang"
        self.assertTrue(10 <= int(ws.page_setup.scale) <= 100)
        chu = [c.value for r in ws.iter_rows() for c in r if isinstance(c.value, str)]
        self.assertFalse(any('theo Quyết định số 08' in x for x in chu))
        self.assertTrue(any(x.startswith('DỰ ÁN') for x in chu))
        ngat = [b.id for b in ws.row_breaks.brk]
        self.assertTrue(ngat, 'dữ liệu nhiều trang phải có ngắt trang')
        for r in ngat:                                                          # ngắt ở ranh giới: dòng sau là đầu hộ (có STT)
            self.assertIsNotNone(ws.cell(r + 1, 1).value, f'ngắt sau dòng {r} cắt ngang một hộ')
        do = in_an._ham_do_chu()
        mdw = in_an._mdw(ws.parent)
        from openpyxl.utils import get_column_letter
        for c in range(1, ws.max_column + 1):                                   # cột số không "#####": đủ rộng cho số dài nhất
            cd = ws.column_dimensions.get(get_column_letter(c))
            if cd is None or cd.hidden:
                continue
            for r in range(1, ws.max_row + 1):
                o = ws.cell(r, c)
                if isinstance(o.value, (int, float)) and not isinstance(o.value, bool) and o.number_format.startswith('#,##0'):
                    ten, co, dam = in_an._phong(o)
                    can = do(in_an._chu_so_excel(o.value, o.number_format), ten, co, dam) / 0.75
                    self.assertLessEqual(can, (float(cd.width) * mdw + 5), f'{o.coordinate}: {o.value}')


class TestChiTiet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.con = csdl.mo(_du_an(self.td, 2))

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_tieu_de_bang_khong_tro_cuoi_trang(self):
        cau = ('- Căn cứ Giấy xác nhận nguồn gốc đất: thửa đất do Ủy ban nhân dân xã quản lý theo Quyết định giao đất năm 1998, '
               'sử dụng ổn định, không tranh chấp. ')
        for k in range(1, 60):
            with self.con:
                self.con.execute('UPDATE thua SET nguon_goc = ? WHERE ma_ho = 1', (cau * k,))
            ws = openpyxl.load_workbook(in_an.lap_chi_tiet(self.con, 1, self.td / f'ct{k}.xlsx')).active
            ngat = [b.id for b in ws.row_breaks.brk]
            if ngat:
                dong = ngat[0] + 1
                self.assertTrue(str(ws.cell(dong, 1).value or '').startswith('III'), f'ngắt trước dòng {dong}')
                return
        self.skipTest('không gặp trường hợp tiêu đề bảng rơi cuối trang')

    def test_ngat_trang_ct_bo_qua_khi_vua_trang(self):
        ws = openpyxl.Workbook().active
        ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
        self.assertIsNone(in_an.ngat_trang_ct(ws, 30, 31, 32))

    def test_dong_thuong_khong_gop_o(self):
        ws = openpyxl.load_workbook(in_an.lap_chi_tiet(self.con, 1, self.td / 'ct.xlsx')).active
        for r in range(1, ws.max_row + 1):
            chu = ' '.join(str(ws.cell(r, c).value) for c in range(1, 4) if ws.cell(r, c).value)
            if 'Thưởng' in chu and 'mặt bằng' in chu:
                for vung in ws.merged_cells.ranges:
                    self.assertFalse(vung.min_row <= r <= vung.max_row and vung.max_col > vung.min_col,
                                     f'dòng thưởng {r} bị gộp ô {vung}')


class TestGiaoDien(unittest.TestCase):
    def test_ten_nut_hs_dinh_kem(self):
        from pabt import man_hinh_ho_so_scan
        self.assertEqual(man_hinh_ho_so_scan.TEN_NUT, 'HS đính kèm')

    def test_doi_ty_le_tra_lai_con_tro(self):
        cu = giao_dien.ty_le() if hasattr(giao_dien, 'ty_le') else 1.0
        try:
            giao_dien.dat_ty_le(1.1, luu=False)
            self.assertIsNone(QApplication.overrideCursor())
        finally:
            giao_dien.dat_ty_le(cu, luu=False)


if __name__ == '__main__':
    unittest.main()
