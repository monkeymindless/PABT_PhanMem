"""Kiểm thử 0.9.12: tự đọc số, ngày quyết định và số tiền phê duyệt của một hộ từ file quyết định (văn bản có chữ, bảng
Excel, bản scan đã nhận dạng chữ). Toàn bộ là dữ liệu GIẢ (tên, số tiền, số quyết định), chỉ giữ cách trình bày / lỗi nhận
dạng chữ thường gặp của văn bản thật."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, nhap_tho, ocr, quan_ly, theo_doi
from pabt.tien import D
from tests.test_nhap_tho import _don_gian, _ghi

QD_CHU = '''UỶ BAN NHÂN DÂN CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
XÃ MẪU Độc lập - Tự do - Hạnh phúc
Số: 8888 /QĐ-UBND Xã Mẫu, ngày 01 tháng 10 năm 2026
QUYẾT ĐỊNH
Về việc phê duyệt phương án bồi thường, hỗ trợ, tái định cư (Đợt 02 - 01 trường hợp/ 3 thửa đất/ 1.000,0 m2).
Căn cứ Luật Đất đai số 31/2024/QH15 ngày 18 tháng 01 năm 2024;
Căn cứ Quyết định số 10/2020/QĐ-UBND ngày 02 tháng 10 năm 2020 của UBND tỉnh Mẫu;
- Tổng số tiền bồi thường, hỗ trợ: 1.250.000 đồng.
1.10. Tổng cộng giá trị bồi thường, hỗ trợ là: 1.250.000 đồng.
(Viết bằng chữ: Một triệu hai trăm năm mươi nghìn đồng).
- Bồi thường, hỗ trợ về đất: 1.000.000 đồng;
- Bồi thường, hỗ trợ về cây trồng: 200.000 đồng;
- Chính sách hỗ trợ bằng tiền: 50.000 đồng;
Trong đó:
+ Kinh phí cho đơn vị thực hiện (85%): 0 đồng;
'''

# trang 1 (đầu bị dấu mộc che) + bảng danh sách đính kèm của bản scan, kiểu lỗi Tesseract thường đọc ra (dữ liệu giả)
QD_SCAN = '''UỶ BAN NHÂN DÂN CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Số: #7#1/QĐÐ-UBND Huyện Mẫu, ngày -25 tháng 4‡ năm 2024
Căn cứ Quyết định số 10/2020/QĐ-UBND ngày 19/12/2020 của UBND tỉnh Mẫu ban hành Quy định;
b) Tổng số 07 trường hợp, gồm: 04 hộ gia đình, cá nhân và 03 tổ chức.
g) Kinh phí bồi thường, hỗ trợ, tái định cư: 2.000.000.000 đồng (A⁄ười tỷ đông).
Bao gồm:
- Giá trị bồi thường về đất: 1.500.000.000 đồng:
Eo)
- Giá trị về cây trồng: 300.000.000 đồng;
- Giá trị về các chính sách hỗ trợ: 150.000.000 đồng;
- Thưởng bàn giao mặt bằng trước thời hạn: 20.000.000 đồng;
- Chi phí tổ chức thực hiện bồi thường 2%: 30.000.000 đồng; Bà
2. Phương án chỉ tiết bồi thường, hỗ trợ, tái định cư đối với 07 trường hà
Z Í (+ — `, thủ 1 €(jVèm theo Quyết định số 777/QĐ-UBND ngày 25 tháng 12 năm 2024 của Ủy ban nhân dân
2 |TrầnThỉ Í vnh Cmu(áp 1.1827| — 11827 đn ỜNg, 900.000.000 25.000.000 150.000.000| 28800.000|  12.000000| 1.115.800.000 trường
Hải 2, xã Hiểu nhóm còn lại hợp tái
3 Khi mi. Huyện Mẫu (ấp 300.000.000 40.000.000 60000000Ì  7200000| 12.000000 419.200.000 | trường
ấp 3, xã Mẫu Không
Đặng tà ng 1957| 19517 $2 Đuỳng 217750 | — 400.000.000 20.000.000 70000000Ì  4320000| 12.000000 506.320.000 xẻ
Minh Hải 2, xã Hiểu nhóm còn lại =
cũ) định cư
'''


class TestChuQuyetDinh(unittest.TestCase):
    def test_so_ngay(self):
        self.assertEqual(quan_ly.so_ngay_qd(QD_CHU), ('8888/QĐ-UBND', '01/10/2026'))
        # bản scan: dòng "Số:" bị dấu mộc che -> lấy ở tiêu đề danh sách kèm theo, không lấy số / ngày của văn bản căn cứ
        self.assertEqual(quan_ly.so_ngay_qd(QD_SCAN), ('777/QĐ-UBND', '25/12/2024'))
        self.assertEqual(quan_ly.so_ngay_qd('Căn cứ Quyết định số 10/2020/QĐ-UBND ngày 19/12/2020'), ('', ''))

    def test_tong_quyet_dinh(self):
        tong, nguon, khop = quan_ly._tong_quyet_dinh(QD_CHU)
        self.assertEqual((tong, khop), (D(1250000), True))
        self.assertIn('Tổng cộng giá trị', nguon)
        tong, _, khop = quan_ly._tong_quyet_dinh(QD_SCAN)
        self.assertEqual((tong, khop), (D(2000000000), True))          # 5 khoản cộng lại = tổng

    def test_dong_ho_ban_scan(self):
        dong = QD_SCAN.splitlines()
        vt, diem = quan_ly._tim_dong_ho(dong, 'Đặng Minh Hải')
        tien, chac, _ = quan_ly._tien_dong(dong, vt)
        self.assertEqual((tien, chac), (D(506320000), True))           # 400.000.000 + … + 12.000.000 = 506.320.000
        vt, _ = quan_ly._tim_dong_ho(dong, 'Trần Thị Hải')             # tên dính liền "TrầnThỉ"
        self.assertEqual(quan_ly._tien_dong(dong, vt)[:2], (D(1115800000), True))
        self.assertEqual(quan_ly._tim_dong_ho(dong, 'Nguyễn Văn Khải'), (None, 0))   # không nhầm sang "Hải"

    def test_cong_khop(self):
        self.assertTrue(quan_ly._cong_khop([D(5), D(1), D(2), D(3)]))
        self.assertFalse(quan_ly._cong_khop([D(1), D(2), D(4)]))
        self.assertEqual(quan_ly._cac_so_tien('a 12.000000 b 4320000| 99', True), [D(12000000), D(4320000)])


class TestDocQDMotHo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        self.p = self.td / 'da.pabt'
        nhap_tho.nhap(xl, self.p, 'Dự án thử')
        self.con = csdl.mo(self.p)
        self.ten = {r[0]: r[1] for r in self.con.execute('SELECT ma_ho, ho_ten FROM ho')}

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_quyet_dinh_mot_truong_hop(self):
        f = self.td / 'qd.txt'
        f.write_text(QD_CHU, encoding='utf-8')
        kq = quan_ly.doc_qd_mot_ho(self.con, f, 1, tong_pa=D(1250000))
        self.assertEqual((kq.so_qd, kq.ngay, kq.so_tien, kq.chac_chan, kq.ghi_chu), ('8888/QĐ-UBND', '01/10/2026', D(1250000), True, []))
        self.assertIn('1 trường hợp', kq.cach)
        kq = quan_ly.doc_qd_mot_ho(self.con, f, 1, tong_pa=D(999))
        self.assertTrue(any('khác tổng phương án' in x for x in kq.ghi_chu))

    def test_danh_sach_excel(self):
        f = self.td / 'qd.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['(Kèm theo Quyết định số 789/QĐ-UBND ngày 05 tháng 10 năm 2026 của UBND phường)'])
        ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Tổng cộng (đồng)'])
        ws.append([1, self.ten[1], 'ấp 1', 123456000])
        ws.append([2, self.ten[2], 'ấp 2', 98000000])
        wb.save(f)
        kq = quan_ly.doc_qd_mot_ho(self.con, f, 2)
        self.assertEqual((kq.so_qd, kq.ngay, kq.so_tien, kq.chac_chan), ('789/QĐ-UBND', '05/10/2026', D(98000000), True))
        self.assertIn('họ tên', kq.cach)
        kq = quan_ly.doc_qd_mot_ho(self.con, f, 3)                     # hộ không có trong danh sách
        self.assertIsNone(kq.so_tien)
        self.assertTrue(kq.ghi_chu)

    def test_ban_scan_da_nhan_dang(self):
        """Như PDF scan: các dòng do OCR đọc ra (thay doc_van_ban để không cần Tesseract)."""
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Đặng Minh Hải' WHERE ma_ho = 2")
        goc = quan_ly.doc_van_ban
        quan_ly.doc_van_ban = lambda f, *a, **k: ([[x] for x in QD_SCAN.splitlines()], True)
        try:
            kq = quan_ly.doc_qd_mot_ho(self.con, self.td / 'scan.pdf', 2)
            self.assertEqual((kq.so_qd, kq.ngay, kq.so_tien, kq.chac_chan, kq.ocr), ('777/QĐ-UBND', '25/12/2024', D(506320000), True, True))
            kq = quan_ly.doc_qd_mot_ho(self.con, self.td / 'scan.pdf', 1)    # 7 trường hợp, hộ không có trong bảng
            self.assertIsNone(kq.so_tien)
            self.assertEqual(kq.tong_qd, D(2000000000))
            self.assertIn('nhập số tiền của hộ bằng tay', kq.ghi_chu[0])
        finally:
            quan_ly.doc_van_ban = goc


class TestManHinhTrangThai(TestDocQDMotHo):
    def test_chon_file_tu_dien(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt.man_hinh_quan_ly import HopTrangThai
        f = self.td / 'qd.txt'
        f.write_text(QD_CHU, encoding='utf-8')
        d = HopTrangThai(self.con, [1], tong_pa={1: D(1250000)})
        d.im_lang = True
        kq = d.doc_quyet_dinh(f)
        self.assertEqual(kq.so_tien, D(1250000))
        self.assertEqual((d.o['qd_so'].text(), d.o['qd_ngay'].text(), d.o['qd_so_tien'].text()),
                         ('8888/QĐ-UBND', '01/10/2026', '1.250.000'))
        self.assertTrue(d.lb_qd.isVisibleTo(d))
        self.assertEqual(quan_ly.doc_trang_thai(self.con, 1)['qd_so'], '')     # chưa lưu khi chưa bấm Lưu
        d.luu()
        tt = quan_ly.doc_trang_thai(self.con, 1)
        self.assertEqual((tt['da_phe_duyet'], tt['qd_so'], D(tt['qd_so_tien'])), (1, '8888/QĐ-UBND', D(1250000)))
        # không đồng ý điền: các ô giữ nguyên
        d = HopTrangThai(self.con, [2])
        d.im_lang = True
        d.doc_quyet_dinh(f, dien=False)
        self.assertEqual(d.o['qd_so'].text(), '')


@unittest.skipIf(ocr.san_sang(), 'máy không có Tesseract OCR tiếng Việt')
class TestOCRThat(unittest.TestCase):
    def test_anh_scan(self):
        # ảnh vẽ bằng phông Windows trong tiến trình riêng: Qt offscreen không có phông (chỉ ra ô vuông - trước 16/10/2026 bài này
        # chỉ "đạt" vì máy kiểm thử chưa có Tesseract nên bị bỏ qua)
        import subprocess
        import sys
        ve = '\n'.join((
            'import sys',
            'import pabt  # noqa: F401',
            'from PySide6.QtCore import Qt',
            'from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter',
            'a = QGuiApplication([])',
            'im = QImage(2000, 700, QImage.Format.Format_RGB32)',
            "im.fill(QColor('white'))",
            'p = QPainter(im)',
            "f = QFont('Times New Roman')",
            'f.setPixelSize(40)',
            'p.setFont(f)',
            'p.setPen(Qt.GlobalColor.black)',
            "for i, x in enumerate(['Số: 25/QĐ-UBND        Xã Mẫu, ngày 03 tháng 10 năm 2026',",
            "                       'Về việc phê duyệt phương án bồi thường (01 trường hợp)',",
            "                       '1.10. Tổng cộng giá trị bồi thường, hỗ trợ là: 1.234.000 đồng.']):",
            '    p.drawText(60, 120 + i * 120, x)',
            'p.end()',
            'im.save(sys.argv[1])'))
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / 'qd.png'
            subprocess.run([sys.executable, '-c', ve, str(a)], env=dict(os.environ, QT_QPA_PLATFORM='windows'), check=True,
                           timeout=120, cwd=str(Path(__file__).resolve().parents[1]))
            dong = ocr.doc_chu(a)
        toan = '\n'.join(dong)
        self.assertEqual(quan_ly.so_ngay_qd(toan), ('25/QĐ-UBND', '03/10/2026'))
        self.assertEqual(quan_ly._tong_quyet_dinh(toan)[0], D(1234000))


if __name__ == '__main__':
    unittest.main()


# bảng kèm quyết định xuất PDF từ Excel, chữ giữ bố cục (pypdf layout): họ tên, địa chỉ xuống nhiều dòng quanh dòng số liệu,
# tiêu đề lặp lại ở trang sau, dòng tổng dưới bảng (dữ liệu giả, giữ bố cục cột của bảng thật)
BANG_PDF = '''                                                      BẢNG TỔNG HỢP THÔNG TIN VỀ BỒI THƯỜNG, HỖ TRỢ
                                       (Kèm theo Quyết định số:      /QĐ-UBND ngày 29  tháng  9  năm 2026 của UBND xã A)
                                                     Diện tích đất hỗ trợ (m2)             Giá trị bồi                          Hỗ trợ đào tạo,
ST                                                           Nông nghiệp                  thường, hỗ          Hỗ trợ ổn        chuyển đổi nghề         Thưởng di        Tổng cộng giá trị
T        Họ và tên                Địa chỉ                                                trợ nhà ở, vật     định đời sống      và tìm kiếm việc             dời           bồi thường, hỗ
                                                      Tổng       Đất CLN         Đất        kiến trúc                                  làm                                        trợ
1             2                      3                 4              5           6              7                  8                    9                   10                   11
                            Số 1, Khu phố
 1  Bà Lê Thị               2, Phường A,                  500,0          500,0                                                          351.000.000                        -          351.000.000
    Mai                    thành phố     
                           Mẫu    
    Ông Hà Văn             phường B,  
 2  Tâm                    thành phố                   5.000,0        5.000,0                                                        1.200.000.000                 5.000.000       1.205.000.000
                           Mẫu    
                                                        Diện tích đất hỗ trợ (m2)               Giá trị bồi                            Hỗ trợ đào tạo,
ST                                                               Nông nghiệp                    thường, hỗ           Hỗ trợ ổn         chuyển đổi nghề           Thưởng di         Tổng cộng giá trị
T         Họ và tên                 Địa chỉ                                                   trợ nhà ở, vật       định đời sống       và tìm kiếm việc               dời           bồi thường, hỗ
1              2                       3                   4              5            6               7                   8                     9                    10                     11
     Ông Đỗ    
     Minh Khoa và ông        Ấp Một,       
     Đỗ Minh                 xã Mẫu,   
 3   Quân (nhận thừa         tỉnh Thử                     4.000,0         4.000,0                                         6.000.000          1.500.000.000                           -       1.506.000.000
     kế của hộ ông           Mẫu.
     Đỗ Văn    
     Lộc) 
     Ông Phan An             ấp Hai,       
 4   Bình; bà Lý             xã Mẫu,                               -                               12.000.000                                                                       -            12.000.000
     Thị Hoa                 tỉnh Thử      
                             Mẫu
     Cộng (I+II):                                     12.000,0                                       12.000.000         6.000.000       3.051.000.000             5.000.000     3.074.000.000
 1. Tiền bồi thường, hỗ trợ                                                                                                                                                     3.074.000.000
'''


class TestBangPDF(unittest.TestCase):
    def test_loai_cot(self):
        from pabt.pdf_bang import loai_cot
        self.assertEqual([loai_cot(x) for x in (
            'Tổng cộng giá trị bồi thường, hỗ trợ', 'Thưởng di dời', 'Giá trị bồi thường, hỗ trợ nhà ở, vật kiến trúc',
            'Hỗ trợ ổn định đời sống', 'Giá trị bồi thường về đất', 'Giá trị bồi thường cây trồng', 'Diện tích đất hỗ trợ (m2)',
            'Họ và tên')], ['so_tien', 'tien_thuong', 'tien_tai_san', 'tien_ho_tro', 'tien_dat', 'tien_cay', 'dien_tich', ''])

    def test_tach_bang(self):
        from pabt.pdf_bang import tach_bang
        ds = tach_bang(BANG_PDF.splitlines())
        self.assertEqual([d.stt for d in ds], [1, 2, 3, 4])                       # dòng "Cộng", "1. Tiền…" không phải hộ
        self.assertEqual([d.ten for d in ds], ['Bà Lê Thị Mai', 'Ông Hà Văn Tâm',
                                               'Ông Đỗ Minh Khoa và ông Đỗ Minh Quân (nhận thừa kế của hộ ông Đỗ Văn Lộc)',
                                               'Ông Phan An Bình; bà Lý Thị Hoa'])
        self.assertEqual(ds[1].tien, {'tien_ho_tro': D(1200000000), 'tien_thuong': D(5000000), 'so_tien': D(1205000000)})
        self.assertEqual(ds[2].tien['tien_ho_tro'], D(6000000 + 1500000000))          # ổn định + đào tạo
        self.assertEqual(ds[3].tien, {'tien_tai_san': D(12000000), 'so_tien': D(12000000)})
        self.assertTrue(all(d.khop_tong for d in ds))
        self.assertIn('Ấp Một', ds[2].dia_chi)

    def test_khop_ho_va_so_ky(self):
        from unittest import mock
        from pabt import pdf_bang
        with tempfile.TemporaryDirectory() as td:
            xl = Path(td) / 'ds.xlsx'
            _ghi(xl, _don_gian)
            p = Path(td) / 'da.pabt'
            nhap_tho.nhap(xl, p, 'Thử')
            con = csdl.mo(p)
            for t in ('Lê Thị Mai', 'Hà Văn Tâm', 'Đỗ Văn Lộc', 'Phan An Bình'):
                con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES ((SELECT MAX(ma_ho) + 1 FROM ho), 99, ?)", (t,))
            con.commit()
            f = Path(td) / 'bth.pdf'
            f.write_bytes(b'%PDF-1.4')
            # chữ giữ bố cục + số văn bản đóng kèm chữ ký số (không có trong lớp chữ)
            with mock.patch.object(pdf_bang, 'dong_layout', return_value=BANG_PDF.splitlines()), \
                    mock.patch.object(pdf_bang, 'chu_chu_ky', return_value=[(0, 330.0, 497.0, 842.0, '555')]), \
                    mock.patch('pabt.nhap_don_gia.doc_bang', return_value=[[x] for x in BANG_PDF.splitlines()]):
                kq = quan_ly.doc_quyet_dinh_nhieu(con, [f])
            self.assertEqual((kq.so_qd, kq.ngay), ('555/QĐ-UBND', '29/09/2026'))
            ten = {d.ho_ten: d for d in kq.dong}
            self.assertEqual(sorted(ten), sorted(['Lê Thị Mai', 'Hà Văn Tâm', 'Đỗ Văn Lộc', 'Phan An Bình']))
            self.assertEqual(ten['Đỗ Văn Lộc'].so_tien, D(1506000000))
            self.assertIn('nhiều người', ten['Phan An Bình'].cach_khop)
            self.assertEqual(ten['Phan An Bình'].chi_tiet, {'tien_tai_san': D(12000000)})
            r = quan_ly.ap_quyet_dinh(con, 'pd', kq.dong, kq.so_qd, kq.ngay)
            x = theo_doi.doc_qd_ho(con, ten['Phan An Bình'].ma_ho)[0]
            self.assertEqual((x['so_tien'], x['tien_tai_san'], x['tien_ho_tro']), ('12000000', '12000000', ''))
            self.assertEqual(r['so_ho'], 4)
            con.close()

    def test_so_truong_hop(self):
        self.assertEqual(quan_ly.so_truong_hop('- Bồi thường bổ sung: 01 trường hợp.\n1. Tổng số trường hợp bồi thường, hỗ trợ bổ sung: '
                                               '20 hộ gia đình'), 20)
        self.assertEqual(quan_ly.so_truong_hop('b) Tổng số 07 trường hợp, gồm'), 7)
        self.assertEqual(quan_ly.so_truong_hop('(Đợt 02 - 01 trường hợp/ 37 thửa đất)'), 1)

    def test_excel_cot_tung_muc(self):
        with tempfile.TemporaryDirectory() as td:
            xl = Path(td) / 'ds.xlsx'
            _ghi(xl, _don_gian)
            p = Path(td) / 'da.pabt'
            nhap_tho.nhap(xl, p, 'Thử')
            con = csdl.mo(p)
            ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0]
            f = Path(td) / 'qd.xlsx'
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Giá trị bồi thường, hỗ trợ nhà ở, vật kiến trúc', 'Hỗ trợ ổn định đời sống',
                       'Thưởng di dời', 'Tổng cộng giá trị bồi thường, hỗ trợ'])
            ws.append([1, ten, 1000000, 200000, '-', 1200000])
            wb.save(f)
            d = quan_ly.doc_quyet_dinh(con, f).dong[0]
            self.assertEqual((d.so_tien, d.chi_tiet), (D(1200000), {'tien_tai_san': D(1000000), 'tien_ho_tro': D(200000)}))
            con.close()
