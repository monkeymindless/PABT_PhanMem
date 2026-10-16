"""Kiểm thử 0.9.84 (người dùng 14/10/2026): khung xem trước A4 trong cửa sổ - pabt/xem_truoc_tai_lieu.KhungXemTruocTaiLieu, HopIn (nửa
phải luôn hiện, bấm hộ / đổi chế độ thì lập lại), CuaSoLapPA (F4 bật / tắt, bản in của phương án ĐANG SOẠN). Không mở Excel: bước
Excel xuất PDF thay bằng hàm chép một PDF giả lập (dữ liệu giả)."""
from __future__ import annotations
import os
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
        self._vo = [mock.patch.object(xt, 'chuyen_pdf', self.excel), mock.patch.object(xt, 'dung_duoc_excel', lambda: '')]
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


class TestLapChiTietBanDangSoan(CoSoXem):
    def test_pa_trong_bo_nho_va_che_cccd(self):
        from pabt.lap_pa import BoSoan
        with self.con:
            self.con.execute("UPDATE ho SET so_cccd = '075092001234' WHERE ma_ho = 1")
        bo = BoSoan(self.con, 1)
        m = next(x for x in bo.dm.muc[2])
        bo.them_tu_danh_muc(2, m)
        self.assertTrue(bo.co_thay_doi)
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'dang_soan.xlsx', bc=bo.bc, pa=bo.pa, che_cccd=True)
        chu = ' '.join(str(c.value) for r in openpyxl.load_workbook(f).active.iter_rows() for c in r if c.value is not None)
        self.assertIn(m.ten, chu)                               # dòng chưa lưu có trong bản in
        self.assertIn('075092******', chu)
        self.assertNotIn('075092001234', chu)
        f2 = in_an.lap_chi_tiet(self.con, 1, self.td / 'da_luu.xlsx', che_cccd=False)    # số liệu đã lưu, không che
        chu2 = ' '.join(str(c.value) for r in openpyxl.load_workbook(f2).active.iter_rows() for c in r if c.value is not None)
        self.assertIn('075092001234', chu2)


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
        xlsx = self.excel.da_nhan[-1]
        ws = openpyxl.load_workbook(xlsx).active
        self.assertFalse(in_an.co_dau_du_thao(ws))              # chính thức
        h.r_du_thao.setChecked(True)                             # đổi chế độ -> lập lại bản dự thảo, che CCCD
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertEqual(h.khoa_xem_truoc()[1:2] + h.khoa_xem_truoc()[3:], (True, True))
        self.assertNotEqual(self.excel.da_nhan[-1], xlsx)
        self.assertTrue(in_an.co_dau_du_thao(openpyxl.load_workbook(self.excel.da_nhan[-1]).active))
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
        self.assertEqual(b.text(), 'Xem trước A4 (F4)')
        self.assertIn('#0F3866', b.styleSheet())
        self.assertIn('#2563EB', b.styleSheet())
        self.assertIs(w.tach.widget(1), w.w_preview)
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
        cac_khoi = [w.thanh_tren.layout().itemAt(i).widget() for i in range(w.thanh_tren.layout().count())]
        # 0.9.95: 4 khối [Hộ ◀ ▶] [Dán, Quét, Gợi ý] [Lưu, Bỏ thay đổi] [Xem trước A4, In, Đóng] - hẹp thì xuống dòng ít hơn
        self.assertEqual(len(cac_khoi), 4)
        self.assertIn(w.btn_toggle_preview, cac_khoi[3].findChildren(type(w.btn_toggle_preview)))
        mot_hang = sum(k.sizeHint().width() for k in cac_khoi)
        self.assertLess(w.thanh_tren.minimumSizeHint().width(), mot_hang)    # không ép cửa sổ rộng bằng cả hàng
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
