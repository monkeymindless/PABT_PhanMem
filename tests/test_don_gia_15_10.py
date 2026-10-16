"""Cập nhật đơn giá (người dùng 15/10/2026, phương án điều chỉnh của ma_tinh_chinh_don_gia.md): nhóm Vật nuôi riêng khi phân tích (ghi
vào bộ đơn giá vẫn là nhom 3 + phân loại vật nuôi), phân loại đúng chuỗi bộ đơn giá, dán bảng / chữ từ Clipboard, bảng xem trước sửa
được, Windows OCR + Tesseract. Số liệu GIẢ LẬP; ghi bộ đơn giá vào thư mục máy tạm (PABT_THU_MUC_MAY)."""
from __future__ import annotations
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import don_gia, ocr
from pabt import nhap_don_gia as ndg

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False

BANG = [['STT', 'Tên', 'ĐVT', 'Đơn giá (đồng)'],
        ['1', 'Nhà kho thử nghiệm khung thép', 'm²', '1.234.000'],
        ['2', 'Cá rô phi nuôi thử nghiệm', 'kg', '45.000'],
        ['3', 'Cây thử nghiệm ăn quả', 'cây', '99.000']]


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()


class TestNhom(unittest.TestCase):
    def test_nhom_theo_chu(self):
        self.assertEqual(ndg.nhom_theo_chu('Đơn giá bồi thường vật nuôi là thủy sản'), ndg.NHOM_VN)
        self.assertEqual(ndg.nhom_theo_chu('Cá nuôi lồng bè'), ndg.NHOM_VN)
        self.assertEqual(ndg.nhom_theo_chu('Nuôi tôm thâm canh'), ndg.NHOM_VN)
        self.assertEqual(ndg.nhom_theo_chu('Đơn giá bồi thường cây trồng, vật nuôi'), 3)      # cả hai: từng dòng tự phân
        self.assertEqual(ndg.nhom_theo_chu('Cây ăn quả lâu năm'), 3)
        self.assertEqual(ndg.nhom_theo_chu('Mồ mả xây đá'), 2)
        self.assertEqual(ndg.nhom_theo_chu('Hỗ trợ đào, bốc, di dời mồ mả'), 4)
        self.assertEqual(ndg.nhom_theo_chu('Vật kiến trúc, công trình'), 2)

    def test_nhom_theo_don_vi(self):
        self.assertEqual(ndg._nhom_dong('Rô phi', 'kg'), ndg.NHOM_VN)
        self.assertEqual(ndg._nhom_dong('Ao A', 'ha/vụ'), ndg.NHOM_VN)
        self.assertEqual(ndg._nhom_dong('Ao B', 'm² mặt nước'), ndg.NHOM_VN)
        self.assertEqual(ndg._nhom_dong('Bè C', '100m3/vụ'), ndg.NHOM_VN)
        self.assertEqual(ndg._nhom_dong('Mít', 'cây'), 3)
        self.assertEqual(ndg._nhom_dong('Lúa', 'ha'), 3)

    def test_dong_tu_chu(self):
        self.assertEqual(ndg.dong_tu_chu('Tên\tĐVT\tĐơn giá\r\nNhà tạm\tm²\t576.000\r\n\r\n'),
                         [['Tên', 'ĐVT', 'Đơn giá'], ['Nhà tạm', 'm²', '576.000']])
        self.assertEqual(ndg.dong_tu_chu('Giếng khoan   cái 3.500.ooo\n'), [['Giếng khoan cái 3.500.000']])   # chữ OCR: sửa "o"


class TestApDung(CoSo):
    def test_ghi_dung_nhom_va_phan_loai(self):
        ds = ndg.nhan_muc(BANG)
        self.assertEqual([m.nhom for m in ds], [2, ndg.NHOM_VN, 3])
        ndg.so_khop(ds)
        self.assertTrue(all(m.trang_thai == 'mới' for m in ds))
        kq = ndg.ap_dung(ds, None, 'thử 15/10')
        self.assertEqual(set(kq['theo_nhom']), {2, 3, ndg.NHOM_VN})
        con = sqlite3.connect(don_gia.file_dang_dung())
        try:
            r = {t: (ma, nhom, pl) for ma, nhom, pl, t in con.execute(
                "SELECT ma, nhom, phan_loai, ten FROM dm_taisan WHERE ghi_chu = 'Cập nhật từ thử 15/10'")}
            pl_nha = con.execute("SELECT phan_loai FROM dm_taisan WHERE ma = 'TS1'").fetchone()[0]
            pl_vn = con.execute("SELECT phan_loai FROM dm_taisan WHERE ma = 'VN1'").fetchone()[0]
            pl_cay = con.execute("SELECT phan_loai FROM dm_taisan WHERE ma = 'CT1'").fetchone()[0]
        finally:
            con.close()
        ma, nhom, pl = r['Nhà kho thử nghiệm khung thép']
        self.assertEqual((ma[:2], nhom, pl), ('TS', 2, pl_nha))          # đúng chuỗi phân loại của bộ (trước: "2. Nhà, công trình…")
        ma, nhom, pl = r['Cá rô phi nuôi thử nghiệm']
        self.assertEqual((ma[:2], nhom, pl), ('VN', 3, pl_vn))          # vật nuôi: CSDL vẫn nhom 3 + phân loại vật nuôi
        ma, nhom, pl = r['Cây thử nghiệm ăn quả']
        self.assertEqual((ma[:2], nhom, pl), ('CT', 3, pl_cay))

    def test_ca_bang_la_chinh_sach(self):
        ds = ndg.nhan_muc([['STT', 'Tên', 'ĐVT', 'Đơn giá'], ['1', 'Hỗ trợ thử nghiệm di chuyển', 'hộ', '3.000.000']])
        ndg.so_khop(ds, 4)
        ndg.ap_dung(ds, 4, 'thử CS')
        con = sqlite3.connect(don_gia.file_dang_dung())
        try:
            ma = con.execute("SELECT ma FROM dm_hotro WHERE ten = 'Hỗ trợ thử nghiệm di chuyển'").fetchone()[0]
        finally:
            con.close()
        self.assertTrue(ma.startswith('CS'))


@unittest.skipUnless(CO_QT, 'không có PySide6')
class TestManHinh(CoSo):
    def setUp(self):
        super().setUp()
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])

    def test_xem_truoc_ma_du_kien_va_sua_gia(self):
        from pabt.man_hinh_nhap_don_gia import C_GIA, C_MA, HopNhapDonGia
        d = HopNhapDonGia(None, None, 'thử', dong=BANG)
        d.im_lang = True
        self.assertEqual([d.bang.item(r, C_MA).text() for r in range(3)], ['TS… (mới)', 'VN… (mới)', 'CT… (mới)'])
        self.assertEqual([d.o_nhom.itemData(i) for i in range(d.o_nhom.count())], [0, 2, 3, ndg.NHOM_VN, 4])
        d.bang.item(0, C_GIA).setText('1.500.000')                     # sửa đơn giá trên bảng trước khi áp dụng
        self.assertEqual(d.ds[0].don_gia, 1500000)
        d.bang.item(0, C_GIA).setText('abc')                           # sai: giữ giá cũ
        self.assertEqual(d.ds[0].don_gia, 1500000)
        d.deleteLater()

    def _hop(self):
        from pabt.man_hinh_don_gia import HopBoDonGia
        d = HopBoDonGia(None, None)
        d.im_lang = True
        d._da_mo_khoa = True
        return d

    def test_dan_tu_clipboard_nhom_the_dang_xem(self):
        d = self._hop()
        d.the.setCurrentIndex(2)                                        # thẻ Vật nuôi: bảng dán không ghi nhóm -> vật nuôi
        h = d.dan_don_gia('Tên\tĐVT\tĐơn giá\nLươn nuôi thử nghiệm\tkg\t120.000', cho=False)
        self.assertEqual([m.nhom for m in h.ds], [ndg.NHOM_VN])
        h.accept()
        d.sau_cap_nhat(h.ket_qua)
        self.assertEqual(d.the.currentIndex(), 2)                       # áp dụng xong: về thẻ Vật nuôi
        vn = d.the.widget(2)
        self.assertIn('Lươn nuôi thử nghiệm', [vn.item(r, c).text() for r in range(vn.rowCount()) for c in range(vn.columnCount())
                                              if vn.item(r, c) is not None])
        self.assertIsNone(d.dan_don_gia('   '))                          # Clipboard trống: báo, không mở hộp
        self.assertIn('Clipboard chưa có', d.thong_bao_cuoi)
        d.deleteLater()

    def test_pdf_scan_khong_doc_duoc(self):
        d = self._hop()
        self.assertIsNone(d.xu_ly_pdf_scan('thiếu OCR'))                # im_lang: không hỏi, ghi lý do
        self.assertEqual(d.thong_bao_cuoi, 'thiếu OCR')
        with mock.patch.object(ocr, 'trang_thai_windows', return_value='thieu_tieng_viet'), \
                mock.patch.object(ocr, 'cai_tieng_viet_windows') as cai:
            d.xu_ly_pdf_scan('thiếu OCR', chon='cai')                    # bấm "Cài gói tiếng Việt": mở lệnh cài (không chạy thật)
            cai.assert_called_once()
        d.deleteLater()


class TestOCR(unittest.TestCase):
    def test_gom_dong_va_sua_so(self):
        tu = [(10, 100, 50, 20, 'Nhà'), (70, 102, 40, 20, 'tạm'), (400, 99, 30, 20, 'm2'), (600, 101, 90, 20, '576.ooo'),
              (10, 140, 60, 20, 'Giếng'), (600, 141, 90, 20, '3.500.000')]
        # cột cùng hàng gộp một dòng; 0.9.95: khoảng trống > 2,2 x cao chữ (sang cột kế) nối bằng Tab
        self.assertEqual(ocr.gom_dong(tu), ['Nhà tạm\tm2\t576.ooo', 'Giếng\t3.500.000'])
        self.assertEqual(ocr.sua_so('Nhà tạm m2 576.ooo'), 'Nhà tạm m2 576.000')
        self.assertEqual(ocr.sua_so('Ô tô cũ'), 'Ô tô cũ')

    def test_bao_khi_thieu_tieng_viet(self):
        with mock.patch.object(ocr, 'trang_thai_windows', return_value='thieu_tieng_viet'), \
                mock.patch.object(ocr, '_tesseract_san_sang', return_value='chưa có Tesseract OCR'):
            self.assertEqual(ocr.may_doc()[0], '')
            self.assertIn('CHƯA có gói tiếng Việt', ocr.san_sang())
        with mock.patch.object(ocr, 'trang_thai_windows', return_value='san_sang'):
            self.assertEqual(ocr.may_doc(), ('windows', None))
        with mock.patch.object(ocr, 'trang_thai_windows', return_value='khong_co'), \
                mock.patch.object(ocr, '_tesseract_san_sang', return_value='chưa có Tesseract OCR'):
            self.assertIn('Windows 7 / 8', ocr.san_sang())

    @unittest.skipUnless(sys.platform == 'win32' and CO_QT, 'cần Windows + Qt')
    def test_windows_ocr_that(self):
        """Đọc thật bằng Windows OCR - nhận dạng tiếng Anh có sẵn trên Windows 10 / 11 (máy kiểm thử chưa chắc có gói tiếng Việt)."""
        if ocr.trang_thai_windows('en-US') != 'san_sang':
            self.skipTest('máy không có Windows OCR')
        # ảnh vẽ bằng phông Windows trong tiến trình riêng: Qt offscreen không có phông chữ (chỉ ra ô vuông, OCR không đọc được gì)
        import subprocess
        ve = '\n'.join((
            'import sys',
            'import pabt  # noqa: F401  (Qt5: bí danh PySide6 -> PySide2)',
            'from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter',
            'a = QGuiApplication([])',
            'im = QImage(1400, 260, QImage.Format.Format_RGB32)',
            "im.fill(QColor('white'))",
            'p = QPainter(im)',
            "p.setFont(QFont('Arial', 30))",
            "p.setPen(QColor('black'))",
            "for i, h in enumerate((('1', 'Nha tam', 'm2', '576000'), ('2', 'Gieng khoan', 'cai', '3500000'))):",
            '    for x, t in zip((40, 160, 800, 1050), h):',
            '        p.drawText(x, 90 + i * 110, t)',
            'p.end()',
            'im.save(sys.argv[1])'))
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'bang.png'
            subprocess.run([sys.executable, '-c', ve, str(f)], env=dict(os.environ, QT_QPA_PLATFORM='windows'), check=True,
                           timeout=120, cwd=str(Path(__file__).resolve().parents[1]))
            dong = ocr.doc_anh_windows(f, ngon_ngu='en-US').splitlines()
        self.assertEqual(len(dong), 2)
        # 0.9.95: cột cách xa -> Tab (gom_dong): "1\tNha tam\tm2\t576000"
        self.assertEqual(dong[0].split('\t'), ['1', 'Nha tam', 'm2', '576000'], dong)


if __name__ == '__main__':
    unittest.main()
