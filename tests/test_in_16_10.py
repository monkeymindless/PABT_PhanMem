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


NGUON_DAI = ('- Căn cứ Giấy xác nhận nguồn gốc đất số 01/UBND ngày 30/9/2026 của UBND xã Mẫu: thửa đất do hộ gia đình khai phá sử '
             'dụng ổn định từ năm 1990, không tranh chấp, không lấn chiếm; năm 2002 chuyển nhượng một phần, phần còn lại được thừa kế '
             'và sử dụng tới nay. ')


def _du_an_to_chuc(td: Path, so_thua: int, so_ho_khac: int = 3) -> Path:
    """Dự án giả lập: hộ đầu là một tổ chức có so_thua thửa (liên tiếp), sau đó so_ho_khac hộ 1-3 thửa."""
    from pabt import du_an_moi
    dong = [dict(ho_ten='UBND xã Mẫu quản lý', dia_chi='Ấp 1', so_to='5', so_thua=str(100 + j), loai_dat='CLN',
                 dt_thu_hoi=str(40 + j), vi_tri='1') for j in range(so_thua)]
    for i in range(so_ho_khac):
        for j in range(1 + i % 3):
            dong.append(dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 2', so_to=str(10 + i), so_thua=str(500 + i * 3 + j),
                             loai_dat='ONT', dt_thu_hoi=str(50 + i + j), vi_tri='1'))
    gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'))]
    p = td / 'tc.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong, gia)
    return p


def _trang(ws) -> list:
    """Các trang theo ngắt trang tay đã ghi: [(dòng đầu, dòng cuối)] - trang cuối hết ở dòng cuối VÙNG IN (20/10/2026: các dòng
    trống của khối chữ ký mẫu nằm ngoài vùng in, không in ra)."""
    import re
    ngat = sorted(b.id for b in ws.row_breaks.brk)
    dau, kq = 1, []
    for e in ngat:
        kq.append((dau, e))
        dau = e + 1
    m = re.search(r'\$?(\d+)$', str(ws.print_area or '').split(',')[0])
    kq.append((dau, int(m.group(1)) if m else ws.max_row))
    return kq


class TestDanTrangThichUng(unittest.TestCase):
    """Dàn trang thích ứng (người dùng 16/10/2026): lề, tỷ lệ vừa ngang, cụm không tách, nén khít, tách hộ nhiều thửa qua trang."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)

    def tearDown(self):
        self.doCleanups()                                   # đóng kết nối trước khi xóa thư mục tạm
        self.tmp.cleanup()

    def _mo(self, p):
        con = csdl.mo(p)
        self.addCleanup(con.close)
        return con


    def test_co_gian_vua_trang_keo_35_pt(self):
        # bảng đúng một trang + 35 pt: nén khít về một trang; trang hở 8-22% (trừ trang cuối) được giãn đều
        ws = openpyxl.Workbook().active
        ws.page_setup.paperSize, ws.page_setup.orientation = 9, 'portrait'
        in_an.chuan_le_trang(ws, 'chi_tiet')
        ws.page_setup.scale = 100
        cap = in_an.cao_trang_in(ws)
        n = int((cap + 35) // 26) + 1
        for r in range(1, n + 1):
            ws.row_dimensions[r].height = 26
        while sum(26 for _ in range(n)) <= cap + 35 - 26:
            n += 1
        khoi = [('tu_do', [(r, r) for r in range(1, n + 1)])]
        trang, nen = in_an.co_gian_vua_trang(ws, khoi, cap, None, list(range(1, n + 1)), {r: 22.0 for r in range(1, n + 1)})
        self.assertTrue(nen)
        self.assertEqual(len(trang), 1)
        self.assertTrue(all(ws.row_dimensions[r].height >= 22.0 for r in range(1, n + 1)))

    def test_bth_nhieu_ho_it_thua(self):
        con = self._mo(_du_an(self.td, 40))
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'b.xlsx')).active
        self.assertFalse(ws.sheet_properties.pageSetUpPr.fitToPage)
        self.assertAlmostEqual(ws.page_margins.top, in_an.LE_TRANG['tong_hop']['top'])
        trang = _trang(ws)
        self.assertGreater(len(trang), 1)
        tong = next(r for r in range(13, ws.max_row + 1) if ws.cell(r, 1).value == 'TỔNG CỘNG')
        self.assertGreater(trang[0][1], 13)                                         # trang 1 có hộ
        for e in [c for _, c in trang[:-1]]:
            self.assertIsNotNone(ws.cell(e + 1, 1).value, e)                       # ngắt ở ranh giới hộ (ô STT có số)
        self.assertLess(trang[-1][0], tong)                                         # tổng + chữ ký không đứng trơ
        self.assertEqual(ws.cell(tong, 22).value, f'=SUM(V13:V{tong - 1})')

    def test_bth_to_chuc_nhieu_thua(self):
        # bảng tổng hợp in tỷ lệ ~26% (mẫu rộng): một trang ~55 dòng thửa - tổ chức 90 thửa chắc chắn vắt qua trang
        con = self._mo(_du_an_to_chuc(self.td, 90, 3))
        f = in_an.lap_bang_tong_hop(con, self.td / 'b40.xlsx')
        ws = openpyxl.load_workbook(f).active
        tong = next(r for r in range(13, ws.max_row + 1) if ws.cell(r, 1).value == 'TỔNG CỘNG')
        trang = _trang(ws)
        ngat = [c for _, c in trang[:-1]]
        self.assertTrue(any(13 <= e < 102 for e in ngat))                            # tổ chức 40 thửa vắt qua trang
        self.assertGreater(ngat[0], 13 + 2)                                         # không đẩy trống trang 1
        for m in ws.merged_cells.ranges:                                            # không vùng gộp nào vắt qua ranh trang
            if m.min_row >= 13:
                self.assertFalse(any(m.min_row <= e < m.max_row for e in ngat), str(m))
        for e in [x for x in ngat if 13 <= x < 102]:                                 # phần sau lặp STT, họ tên
            self.assertEqual(ws.cell(e + 1, 1).value, 1)
            self.assertEqual(ws.cell(e + 1, 2).value, 'UBND xã Mẫu quản lý')
        tien = [ws.cell(r, 22).value for r in range(13, tong) if isinstance(ws.cell(r, 22).value, (int, float))]
        kq = in_an.nghiep_vu.ket_qua_ho(con)
        self.assertEqual(sum(tien), sum(int(k.tong) for k, _ in kq.values() if k.co_phuong_an))   # tiền không nhân đôi
        self.assertEqual(ws.cell(tong, 22).value, f'=SUM(V13:V{tong - 1})')
        self.assertLess(trang[-1][0], tong)

    def test_bth_nen_khit_bot_trang(self):
        # 21/10/2026 (người dùng: không ngắt khi trang chưa đầy 85%): bảng xếp theo từng dòng Excel nên các trang đã lấp sát; phần cuối
        # nhỏ nhất (TỔNG CỘNG + chữ ký) lớn hơn ngưỡng nén khít (NEN_TOI_DA) - nén khít không còn bớt trang. Kiểm thay bằng: mọi trang
        # trừ trang cuối lấp >= TRANG_DAY (dòng tiêu đề cột lặp tính vào trang sau). Nén khít ở mức hàm: test_co_gian_vua_trang_keo_35_pt
        con = self._mo(_du_an(self.td, 80))
        ma = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
        nhieu_trang = 0
        for n in range(4, 80, 5):
            ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / f'b{n}.xlsx', ma[:n])).active
            cao = in_an._ham_cao(ws)
            cap = in_an.cao_trang_in(ws)
            td = sum(cao(r) for r in range(9, 13))
            trang = _trang(ws)
            nhieu_trang += len(trang) > 1
            for a, b in trang[:-1]:
                self.assertGreaterEqual(sum(cao(r) for r in range(a, b + 1)) + (td if a > 12 else 0), in_an.TRANG_DAY * cap - 0.5,
                                        (n, a, b))
        self.assertGreater(nhieu_trang, 0)


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
