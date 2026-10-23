"""Kiểm thử 0.9.84 (người dùng 14/10/2026): khung xem trước A4 trong cửa sổ - pabt/xem_truoc_tai_lieu.KhungXemTruocTaiLieu, HopIn (nửa
phải luôn hiện, bấm hộ / đổi chế độ thì lập lại), CuaSoLapPA (F4 bật / tắt, bản in của phương án ĐANG SOẠN). Không mở Excel: bước
Excel xuất PDF thay bằng hàm chép một PDF giả lập (dữ liệu giả)."""
from __future__ import annotations
import os
import re
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import openpyxl
from PySide6.QtWidgets import QApplication

from pabt import giao_dien, in_an, xem_truoc_tai_lieu as xt
from tests.test_in_vua_chu import CoSo
from tests.test_nhap_don_gia import _pdf

APP = QApplication.instance() or QApplication([])
# bản Qt5 (Win 7/8) không có QtPdf: khung không hiện trang, chỉ báo đã tạo bản xem trước + nút mở bằng trình xem PDF của Windows
TRANG = 3 if xt.co_qtpdf() else 0


def _pdf_nhieu_trang(p: Path, so: int = 3) -> Path:
    """PDF giả lập so trang (ghép các PDF một trang bằng pypdf)."""
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for i in range(so):
        mot = p.with_name(f'{p.stem}_{i}.pdf')
        _pdf(mot, [f'Trang {i + 1}'])
        w.add_page(PdfReader(str(mot)).pages[0])
    with open(p, 'wb') as f:
        w.write(f)
    return p


def _chu_docx(f) -> str:
    import zipfile
    with zipfile.ZipFile(f) as z:
        x = z.read('word/document.xml').decode('utf-8')
    return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x))


class GiaExcel:
    """Thay Excel: 'xuất PDF' = chép PDF mẫu sang chỗ PDF cần tạo; ghi lại các file Excel đã nhận."""

    def __init__(self, mau: Path, cho: float = 0.0):
        self.mau, self.cho, self.da_nhan = mau, cho, []

    def __call__(self, xlsx, pdf):
        self.da_nhan.append(Path(xlsx))
        time.sleep(self.cho)
        shutil.copy2(self.mau, pdf)
        return ''


class CoSoXem(CoSo):
    def setUp(self):
        super().setUp()
        giao_dien.ap_dung(APP)
        self.mau_pdf = _pdf_nhieu_trang(self.td / 'mau.pdf', 3)
        self.excel = GiaExcel(self.mau_pdf)
        self._vo = [mock.patch.object(xt, 'chuyen_pdf', self.excel), mock.patch.object(xt, 'dung_duoc_excel', lambda: ''),
                    mock.patch.object(xt, 'dung_duoc_word', lambda: '')]
        for v in self._vo:
            v.start()

    def tearDown(self):
        for v in self._vo:
            v.stop()
        super().tearDown()


class TestKhung(CoSoXem):
    @unittest.skipIf(xt.co_qtpdf(), 'máy có QtPdf: hiện trang')
    def test_qt5_khong_qtpdf_bao_va_mo_ngoai(self):
        k = xt.KhungXemTruocTaiLieu()
        f = self.td / 'xem.pdf'
        shutil.copy2(self.mau_pdf, f)
        self.assertTrue(k.nap_tai_lieu(f))
        self.assertIn('Đã tạo bản xem trước', k.thong_bao())
        self.assertTrue(k.b_mo_ngoai.isVisibleTo(k))
        k.don_dep()

    @unittest.skipUnless(xt.co_qtpdf(), 'Qt5: không có QtPdf')
    def test_nap_trang_phong_to_va_khong_khoa_file(self):
        k = xt.KhungXemTruocTaiLieu(ham_in=lambda pdf, xlsx: None)
        k.resize(600, 800)
        k.show()
        APP.processEvents()
        self.assertEqual(k.lb_trang.text(), '0 / 0')
        self.assertFalse(k.b_phong.isEnabled())
        f = self.td / 'xem.pdf'
        shutil.copy2(self.mau_pdf, f)
        self.assertTrue(k.nap_tai_lieu(f))
        self.assertEqual((k.so_trang(), k.trang_hien_tai()), (3, 0))
        self.assertEqual(k.lb_trang.text(), '1 / 3')
        k.sang_trang(1)
        self.assertEqual(k.trang_hien_tai(), 1)
        self.assertTrue(k.b_truoc.isEnabled())
        vua = k.he_so()
        k.phong_to(1)
        self.assertGreater(k.he_so(), vua)
        k.vua_trang()
        k.nap_tai_lieu(f)                                       # nạp lại: về trang 1
        self.assertEqual(k.trang_hien_tai(), 0)
        os.remove(f)                                            # nạp từ bộ nhớ: không giữ khóa file PDF (thư mục tạm xóa được)
        self.assertFalse(f.exists())
        k.don_dep()
        self.assertEqual(k.so_trang(), 0)

    def test_thanh_cong_cu_khong_emoji(self):
        k = xt.KhungXemTruocTaiLieu(ham_in=lambda pdf, xlsx: None)
        for b in (k.b_phong, k.b_thu, k.b_vua, k.b_truoc, k.b_sau, k.b_in):
            self.assertFalse(any(ord(c) > 0x2FFF and not 0x1E00 <= ord(c) <= 0x1EFF for c in b.text()), b.text())
        self.assertEqual(k.b_vua.text(), 'Vừa trang')
        self.assertEqual(k.b_in.text(), 'In nhanh')
        self.assertFalse(xt.KhungXemTruocTaiLieu().b_in.isVisibleTo(k))   # không có hàm in: không hiện nút In nhanh

    def test_yeu_cau_chi_giu_moi_nhat_va_nho_theo_khoa(self):
        self.excel.cho = 0.3
        k = xt.KhungXemTruocTaiLieu()
        tao = []

        def ham(ten):
            def t(d):
                f = Path(d) / f'{ten}.xlsx'
                openpyxl.Workbook().save(f)
                tao.append(ten)
                return f
            return t
        k.yeu_cau('a', ham('a'), ngay=True)                    # đang xuất 'a' ở nền
        k.yeu_cau('b', ham('b'))
        k.yeu_cau('c', ham('c'))                                # 'b' bị thay bởi 'c' trước khi kịp lập
        self.assertTrue(k.cho_xong(30))
        self.assertEqual(tao, ['a', 'c'])
        self.assertEqual(k.pdf.parent.name, k.xlsx.parent.name)
        self.assertEqual(k.xlsx.stem, 'c')
        self.assertEqual(k.so_trang(), TRANG)
        k.yeu_cau('a', ham('a'))                                # đã lập trong phiên: dùng lại, không gọi Excel
        self.assertFalse(k.dang_lap())
        self.assertEqual((tao, k.xlsx.stem), (['a', 'c'], 'a'))
        d = k.thu_muc
        self.assertTrue(str(d).startswith(str(xt.THU_MUC_GOC)))
        k.don_dep()
        self.assertFalse(d.exists())                           # file tạm xóa khi đóng

    @unittest.skipUnless(xt.co_qtpdf(), 'Qt5: không có QtPdf')
    def test_ban_word_khong_co_word_dung_ban_gan_dung(self):
        """Xem trước phương án chi tiết = file .docx; máy không dùng được Word -> PDF gần đúng dựng bằng Qt từ chính file .docx
        (docx_sang_pdf - không gọi Word / Excel, không lập bản Excel)."""
        from pabt import in_word
        k = xt.KhungXemTruocTaiLieu()
        self.addCleanup(k.don_dep)
        with mock.patch.object(xt, 'dung_duoc_word', lambda: 'Máy chưa có Microsoft Word.'):
            k.yeu_cau(('w', 1), lambda d: in_word.xuat_chi_tiet_docx(self.con, 1, Path(d) / 'ct.docx'), 'thử', ngay=True)
        self.assertTrue(k.cho_xong(30))
        self.assertEqual(self.excel.da_nhan, [])                # không nhờ Excel / Word
        self.assertTrue(k.gan_dung)
        self.assertEqual(k.xlsx.suffix, '.docx')                # In nhanh / mở ngoài vẫn theo bản Word
        self.assertGreaterEqual(k.so_trang(), 1)
        self.assertEqual(k.ly_do_gan_dung, 'Máy chưa có Microsoft Word.')

    def test_loi_lap_bao_trong_khung(self):
        k = xt.KhungXemTruocTaiLieu()

        def hong(d):
            raise in_an.LoiIn('Thiếu mẫu in')
        k.yeu_cau(None, hong, ngay=True)
        self.assertIn('Thiếu mẫu in', k.thong_bao())
        k.don_dep()

    def test_khong_man_hinh_khong_mo_excel(self):
        for v in self._vo:
            v.stop()
        try:
            if in_an.co_excel() and APP.platformName() == 'offscreen':
                with mock.patch.dict(os.environ, {'PABT_XEM_TRUOC_EXCEL': ''}):
                    self.assertIn('không có màn hình', xt.dung_duoc_excel())
        finally:
            for v in self._vo:
                v.start()


class TestHopIn(CoSoXem):
    def test_chia_doi_bam_ho_va_doi_che_do(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p)
        self.assertEqual(h.tach.count(), 2)
        self.assertIs(h.tach.widget(1), h.w_preview)
        self.assertEqual(h.w_preview.minimumWidth(), 520)
        h.show()
        APP.processEvents()
        APP.processEvents()
        a, b = h.tach.sizes()
        if a + b >= 2 * 520:
            self.assertLessEqual(abs(a - b), 2)                 # 50/50
        else:                                                    # màn hình nhỏ (offscreen): khung xem trước giữ tối thiểu 520
            self.assertEqual(b, 520)
        h.bang_ho.setCurrentCell(0, 1)                           # bấm hộ -> lập bản xem trước của hộ
        self.assertTrue(h.w_preview.cho_xong(30))
        ma = h.bang_ho.item(0, 0).data(256)
        self.assertEqual(h.khoa_xem_truoc()[:2], (ma, False))
        self.assertEqual(h.w_preview.so_trang(), TRANG)
        self.assertTrue(h.w_preview.b_in.isEnabled())
        docx = self.excel.da_nhan[-1]
        self.assertEqual(docx.suffix, '.docx')                  # 22/10/2026: xem trước = bản Word (mẫu chuẩn duy nhất)
        self.assertNotIn('(DỰ THẢO)', _chu_docx(docx))          # chính thức
        h.r_du_thao.setChecked(True)                             # đổi chế độ -> lập lại bản dự thảo
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertEqual(h.khoa_xem_truoc()[1:2] + h.khoa_xem_truoc()[3:4], (True, False))     # 1.0.04: không che CCCD
        self.assertNotEqual(self.excel.da_nhan[-1], docx)
        self.assertIn('(DỰ THẢO)', _chu_docx(self.excel.da_nhan[-1]))
        d = h.w_preview.thu_muc
        h.reject()                                               # đóng: xóa thư mục tạm
        self.assertFalse(d.exists())

    def test_mo_tu_ho_dang_chon_xem_ngay(self):
        from pabt.man_hinh import HopIn
        ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu DESC LIMIT 1').fetchone()[0]
        h = HopIn(self.con, None, ma_ho_chon=[ma])
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertEqual(h.khoa_xem_truoc()[0], ma)
        self.assertEqual(h.w_preview.so_trang(), TRANG)
        self.assertFalse(any(b.text().startswith('Xem trước bản in') for b in h.findChildren(type(h.w_preview.b_in))))
        h.reject()


class TestCuaSoLapPA(CoSoXem):
    def test_f4_bat_tat_va_xem_ban_dang_soan(self):
        from PySide6.QtGui import QKeySequence
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        b = w.btn_toggle_preview
        self.assertEqual(b.objectName(), 'btn_toggle_preview')
        self.assertEqual(b.text(), 'Xem trước')
        self.assertIn('#2F5F9E', b.styleSheet())
        self.assertIn('#3B6FCE', b.styleSheet())
        # 16/10/2026 (máy yếu): khung xem trước tạo khi bật lần đầu - mở cửa sổ chưa có khung
        self.assertIsNone(w._w_preview)
        self.assertEqual(w.tach.count(), 1)
        pv = w.w_preview
        self.assertIs(w.tach.widget(1), pv)
        self.assertTrue(w.w_preview.isHidden())                  # mặc định ẩn
        f4 = next(sc for sc in w._phim if sc.key() == QKeySequence('F4'))
        w.show()
        APP.processEvents()
        f4.activated.emit()
        self.assertTrue(w.w_preview.isVisible())
        self.assertTrue(b.isChecked())
        self.assertTrue(w.w_preview.cho_xong(30))
        self.assertEqual(w.w_preview.so_trang(), TRANG)
        # sửa phương án (chưa lưu): bản xem trước lập lại theo số liệu đang soạn
        n = len(self.excel.da_nhan)
        m = next(x for x in w.bo.dm.muc[2])
        w.bo.them_tu_danh_muc(2, m)
        w.cap_nhat()
        self.assertTrue(w._hen_xem.isActive())
        w.lam_moi_xem_truoc(ngay=True)
        self.assertTrue(w.w_preview.cho_xong(30))
        self.assertEqual(len(self.excel.da_nhan), n + 1)
        self.assertEqual(self.excel.da_nhan[-1].suffix, '.docx')
        self.assertIn(m.ten, _chu_docx(self.excel.da_nhan[-1]))   # dòng chưa lưu có trong bản Word đang xem
        self.assertEqual(len(w.bo.pa.khoan[2]), 1)
        d = w.w_preview.thu_muc
        b.click()                                                # nút bật / tắt
        self.assertTrue(w.w_preview.isHidden())
        self.assertFalse(b.isChecked())
        w.bo_thay_doi()
        w.close()
        self.assertFalse(d.exists())

    def test_hang_tren_xuong_dong_khi_hep(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        from PySide6.QtWidgets import QHBoxLayout
        from pabt.man_hinh import RONG_O_HO
        lo = w.thanh_tren.layout()
        # 16/10/2026 (người dùng): bỏ SCAN, mọi nút MỘT hàng; ô chọn hộ co / giãn (RONG_O_HO) thay cho xuống dòng
        self.assertIsInstance(lo, QHBoxLayout)
        cac = [lo.itemAt(i).widget() for i in range(lo.count()) if lo.itemAt(i).widget() is not None]
        for b in (w.cb_ho, w.b_dan, w.b_luu, w.b_bo, w.btn_toggle_preview, w.b_in, w.b_dong):
            self.assertIn(b, cac)
        self.assertEqual(w.cb_ho.minimumSizeHint().width() <= RONG_O_HO[0] or w.cb_ho.minimumWidth() == RONG_O_HO[0], True)
        self.assertLess(w.thanh_tren.minimumSizeHint().width(), w.thanh_tren.sizeHint().width() + 1)
        w.bo_thay_doi()
        w.close()


class TestDonThuMucCu(unittest.TestCase):
    def test_xoa_thu_muc_cu(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(xt, 'THU_MUC_GOC', Path(td)):
            cu, moi = Path(td) / '1_1', Path(td) / '2_1'
            cu.mkdir()
            moi.mkdir()
            t = time.time() - 13 * 3600
            os.utime(cu, (t, t))
            xt.don_thu_muc_cu()
            self.assertFalse(cu.exists())
            self.assertTrue(moi.exists())


if __name__ == '__main__':
    unittest.main()
