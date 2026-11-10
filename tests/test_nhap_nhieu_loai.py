"""25/10/2026: nhập danh sách hộ, thửa từ file BẤT KỲ ở "Dự án mới" - Excel .xlsx / .xls (đọc Python thuần), PDF có chữ, PDF / ảnh scan; tự
nhận cột theo tên và theo nội dung; cột file không có thì bỏ qua; hộp Chỉnh cột khi không tự nhận được. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import openpyxl

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import doc_xls, nguon_luoi, nhap_tho  # noqa: E402
from pabt.lap_pa import LoiNhap  # noqa: E402
from tests import mau_xls, pdf_tay  # noqa: E402

TEN = ['Lê Văn An', 'Trần Thị Bình', 'Phạm Quốc Cường', 'Nguyễn Thu Dung', 'Võ Minh Em', 'Đặng Hoài Phương', 'Bùi Gia Huy',
       'Hồ Ngọc Lan']
DC = ['ấp 1, xã Thử Nghiệm', 'ấp 2, xã Thử Nghiệm', 'khu phố 3, phường Mẫu', 'tổ 4, ấp 5, xã Thử Nghiệm']
LOAI = ['ONT+CLN', 'CLN', 'LUC', 'ONT', 'BHK', 'RSX']


def _du_lieu(n=16):
    kq = []
    for i in range(n):
        for k in range(2 if i % 3 == 0 else 1):
            kq.append((i + 1 if k == 0 else None, TEN[i % 8] + (f' {chr(65 + i // 8)}' if i >= 8 else '') if k == 0 else None,
                       DC[i % 4] if k == 0 else None, f'0750920{i:05d}' if k == 0 else None, 30 + i % 5, 100 + i * 3 + k,
                       round(50 + i * 7.35 + k, 1), LOAI[(i + k) % 6]))
    return kq


class _Co(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def xlsx(self, ten, ham):
        wb = openpyxl.Workbook()
        ham(wb)
        p = self.td / ten
        wb.save(p)
        return p


class TestDocXls(_Co):
    def test_doc_thuan_python(self):
        p = self.td / 'mau.xls'
        p.write_bytes(mau_xls.bytes_xls())
        ds = doc_xls.doc(p)
        self.assertEqual([s['ten'] for s in ds], ['Danh sách', 'Thống kê'])
        d = ds[0]['dong']
        self.assertEqual(d[2][1], 'Họ và tên')
        self.assertEqual(d[4][:3], [1, 'Lê Văn An', 'ấp 1, xã Thử Nghiệm'])
        self.assertEqual(d[4][3], 75092001234)                          # ô số: Excel mất số 0 đầu
        self.assertEqual((d[4][4].year, d[4][4].month, d[4][4].day), (2021, 3, 5))      # ô ngày
        self.assertEqual(d[6][7], 120.25)
        self.assertIn((3, 6, 3, 7), ds[0]['gop'])                      # ô gộp ngang "Thửa đất"
        self.assertEqual(ds[1]['dong'][1], ['Tổng số hộ', 4])

    def test_nhap_tho_doc_xls(self):
        p = self.td / 'mau.xls'
        p.write_bytes(mau_xls.bytes_xls())
        kq = nhap_tho.doc(p)
        self.assertEqual(kq.loi, [])
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Lê Văn An', 'Trần Thị Bình', 'Phạm Quốc Cường', 'Nguyễn Thu Dung'])
        self.assertEqual([h['so_cccd'] for h in kq.ho], ['075092001234', '075092005678', '', '075092009999'])
        self.assertEqual(kq.ho[0]['ngay_cap'], '05/03/2021')
        self.assertEqual([(t['ma_ho'], t['so_to'], t['so_thua'], t['dt_thu_hoi'], t['loai_dat']) for t in kq.thua],
                         [(1, '30', '100', '215.5', 'ONT+CLN'), (1, '30', '101', '40', 'CLN'), (2, '31', '55', '120.25', 'LUC'),
                          (3, '31', '56', '1070.5', 'RSX'), (4, '32', '7', '88', 'ONT'), (4, '32', '8', '12', 'BHK')])
        self.assertEqual(kq.bo_cot.sheet, 'Danh sách')
        self.assertEqual(kq.loai, 'excel')
        self.assertIn('Thống kê', ' '.join(kq.thong_bao) + ' ' + str([n.ten for n in kq.nguons]))

    def test_dung_duoi_sai_van_doc_theo_noi_dung(self):
        p = self.td / 'sai_duoi.xlsx'                                   # nội dung .xls nhưng đặt đuôi .xlsx
        p.write_bytes(mau_xls.bytes_xls())
        self.assertEqual(len(nhap_tho.doc(p).ho), 4)
        self.assertEqual(nguon_luoi.loai_file(p), 'xls')

    def test_file_hong(self):
        p = self.td / 'hong.xls'
        b = mau_xls.bytes_xls()
        p.write_bytes(b[:3000])
        with mock.patch('pabt.nhap_don_gia_doc.chuyen_office', side_effect=LoiNhap('không có Excel')):
            with self.assertRaises(LoiNhap):
                nhap_tho.doc(p)
        with self.assertRaises(doc_xls.LoiXls):
            doc_xls.doc(p)


class TestTuNhanCot(_Co):
    def test_cot_to_thua_chung_mot_o(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Tờ / Thửa', 'Diện tích (m2)', 'Loại đất'])
            ws.append([1, 'Lê Văn An', 'ấp 1', '35/394', 215.1, 'ONT'])
            ws.append([2, 'Trần Thị Bình', 'ấp 2', 'Tờ 36, thửa 12', 50, 'CLN'])
            ws.append([3, 'Phạm Quốc Cường', 'ấp 3', '37 - 99', 20, 'LUC'])
        kq = nhap_tho.doc(self.xlsx('tt.xlsx', bang))
        self.assertEqual(kq.loi, [])
        self.assertEqual([(t['so_to'], t['so_thua'], t['dt_thu_hoi']) for t in kq.thua], [('35', '394', '215.1'), ('36', '12', '50'),
                                                                                         ('37', '99', '20')])

    def test_khong_co_cot_ho_ten_thi_ho_tam(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Số tờ', 'Số thửa', 'Diện tích thu hồi (m2)', 'Mục đích sử dụng'])
            for i in range(1, 6):
                ws.append([i, 30 + i % 2, 100 + i, 50 + i, 'CLN'])
        kq = nhap_tho.doc(self.xlsx('khong_ten.xlsx', bang))
        self.assertEqual(kq.loi, [])
        self.assertEqual((len(kq.ho), len(kq.thua)), (5, 5))
        self.assertEqual(kq.ho[0]['ho_ten'], 'Hộ tờ 31 thửa 101')
        self.assertIn('không có cột họ tên', kq.canh_bao[0])

    def test_chi_co_mot_vai_cot(self):
        def bang(wb):
            ws = wb.active
            ws.append(['Họ tên', 'Diện tích thu hồi'])
            ws.append(['Lê Văn An', 100])
            ws.append(['Trần Thị Bình', 55.5])
        kq = nhap_tho.doc(self.xlsx('it_cot.xlsx', bang))
        self.assertEqual(kq.loi, [])
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Lê Văn An', 'Trần Thị Bình'])

    def test_cot_ho_ten_trong_dung_cot_cung_ten_co_du_lieu(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Chủ sử dụng đất', 'Số tờ', 'Số thửa', 'DT thu hồi'])
            for i in range(1, 6):
                ws.append([i, None, TEN[i], 30, 100 + i, 10 * i])
        kq = nhap_tho.doc(self.xlsx('cot_trong.xlsx', bang))
        self.assertEqual(kq.loi, [])
        self.assertEqual(kq.ho[0]['ho_ten'], TEN[1])
        self.assertEqual(len(kq.ho), 5)

    def test_cot_khong_tieu_de_doan_theo_noi_dung(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Số tờ', 'Số thửa', 'Diện tích', 'x1', 'x2'])
            for i, (stt, ten, dc, cccd, to, thua, dt, loai) in enumerate(_du_lieu(12), start=2):
                ws.append([stt, ten, dc, to, thua, dt, cccd, loai])
        kq = nhap_tho.doc(self.xlsx('doan.xlsx', bang))
        self.assertEqual(kq.loi, [])
        self.assertEqual(kq.bo_cot.suy, {'so_cccd', 'loai_dat'})
        self.assertTrue(all(h['so_cccd'].startswith('0750920') for h in kq.ho))
        self.assertEqual(kq.thua[0]['loai_dat'], 'ONT+CLN')
        self.assertIn('đoán', nhap_tho.mo_ta_cot(kq.bo_cot))

    def test_file_khong_co_dong_tieu_de(self):
        def bang(wb):
            ws = wb.active
            for stt, ten, dc, cccd, to, thua, dt, loai in _du_lieu(14):
                ws.append([stt, ten, dc, cccd, to, thua, dt, loai])
        kq = nhap_tho.doc(self.xlsx('khong_tieu_de.xlsx', bang))
        self.assertEqual(kq.loi, [])
        self.assertEqual(kq.bo_cot.dong_tieu_de, [0])
        self.assertEqual(len(kq.ho), 14)
        self.assertEqual(len(kq.thua), len(_du_lieu(14)))
        self.assertEqual((kq.thua[0]['so_to'], kq.thua[0]['so_thua'], kq.thua[0]['dt_thu_hoi']), ('30', '100', '50'))
        self.assertTrue(any('không có dòng tiêu đề' in x for x in kq.thong_bao))

    def test_khong_nhan_ra_bang_thi_bao_cach_xu_ly(self):
        kq = nhap_tho.doc(self.xlsx('la.xlsx', lambda wb: wb.active.append(['Mã', 'Giá trị'])))
        self.assertTrue(kq.loi)
        self.assertIn('Chỉnh cột', kq.loi[0])
        self.assertTrue(kq.nguons)                                      # còn nguồn để ghép cột bằng tay

    def test_giai_thich_khi_khong_ra_ho(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Số tờ', 'Số thửa'])        # chỉ có dòng tiêu đề
        kq = nhap_tho.doc(self.xlsx('khong_ho.xlsx', bang))
        self.assertTrue(kq.loi)
        self.assertIn('không còn dòng dữ liệu nào', kq.loi[0])
        self.assertIn('Chỉnh cột', kq.loi[0])

    def test_cot_ho_ten_trong_ca_cot_thi_ho_tam_theo_to_thua(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Số tờ', 'Số thửa'])
            ws.append([1, None, 30, 5])
            ws.append([2, None, 31, 6])
        kq = nhap_tho.doc(self.xlsx('trong_ten.xlsx', bang))
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Hộ tờ 30 thửa 5', 'Hộ tờ 31 thửa 6'])

    def test_nhieu_sheet_chon_dung_bang_va_bao_sheet_khac(self):
        def bang(wb):
            wb.active.title = 'Ghi chú'
            wb.active.append(['Mã', 'Giá trị'])
            ws = wb.create_sheet('Danh sách')
            ws.append(['STT', 'Họ và tên', 'Số tờ', 'Số thửa', 'Diện tích thu hồi'])
            ws.append([1, 'Lê Văn An', 30, 5, 100])
            ws.append([2, 'Trần Thị Bình', 30, 6, 60])
        kq = nhap_tho.doc(self.xlsx('nhieu_sheet.xlsx', bang))
        self.assertEqual(kq.bo_cot.sheet, 'Danh sách')
        self.assertEqual(len(kq.ho), 2)

    def test_nhap_vao_du_an(self):
        p = self.td / 'mau.xls'
        p.write_bytes(mau_xls.bytes_xls())
        bc = nhap_tho.nhap(p, self.td / 'x.pabt', 'Dự án thử')
        self.assertEqual((bc.loi, bc.so_ho, bc.so_thua), ([], 4, 6))


class TestCongThucChuaTinh(_Co):
    def _bang(self, wb):
        ws = wb.active
        ws.title = 'NGUON'
        ws.append(['STT', 'Họ và tên', 'Số tờ', 'Số thửa', 'Diện tích thu hồi'])
        ws.append([1, 'Lê Văn An', 30, 5, 100])
        ws.append([2, 'Trần Thị Bình', 31, 6, 60])
        ws2 = wb.create_sheet('TỔNG CẬP NHẬT')
        ws2.append(['STT', 'Họ và tên', 'Số tờ', 'Số thửa', 'Diện tích thu hồi'])
        for r in (2, 3):
            ws2.append([r - 1] + [f"=NGUON!{c}{r}" for c in 'BCDE'])

    def test_tham_chieu_don_gian_duoc_giai(self):
        p = self.xlsx('cong_thuc.xlsx', self._bang)                    # openpyxl không lưu giá trị đã tính của công thức
        with mock.patch('pabt.nhap_don_gia_doc.chuyen_office', side_effect=AssertionError('không cần Excel')):
            ds = nguon_luoi.lay_nguon(p)
        tong = next(n for n in ds if n.ten == 'TỔNG CẬP NHẬT')
        self.assertEqual(tong.luoi[1][:3], [1, 'Lê Văn An', 30])

    def test_cong_thuc_phuc_tap_bao_mo_excel_luu_lai(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Số tờ', 'Số thửa'])
            ws.append([1, '=UPPER("Lê Văn An")&" "', 30, 5])
            ws.append([2, '=UPPER("Trần Thị Bình")&" "', 31, 6])
        p = self.xlsx('cong_thuc2.xlsx', bang)
        with mock.patch('pabt.nhap_don_gia_doc.chuyen_office', side_effect=LoiNhap('máy không có Excel')):
            kq = nhap_tho.doc(p)
        self.assertTrue(any('công thức chưa có giá trị đã lưu' in x for x in kq.thong_bao))
        self.assertTrue(any('Ctrl+S' in x for x in kq.thong_bao))


class TestChiaCotTuViTri(unittest.TestCase):
    def test_layout_pdf_chu(self):
        dong = ['            DANH SÁCH HỘ',
                'STT   Họ và tên           Địa chỉ              Số tờ    Số thửa    Diện tích',
                '(1)       (2)                (3)                 (4)       (5)         (6)',
                '  1   Lê Văn An            ấp 1, xã Thử           30       100       215,5',
                '                           Nghiệm                 30       101        40,0',
                '  2   Trần Thị Bình        ấp 2, xã Thử           31        55       120,3',
                '  3   Phạm Quốc Cường      ấp 3                   32         7        88,0']
        luoi, rong = nguon_luoi.luoi_tu_layout(dong)
        self.assertEqual(rong, 6)
        self.assertEqual(luoi[3], ['1', 'Lê Văn An', 'ấp 1, xã Thử', '30', '100', '215,5'])
        self.assertEqual(luoi[4][2], 'Nghiệm')                           # dòng gãy: cùng cột địa chỉ

    def test_hang_tu_scan_nhan_net_ke_khung(self):
        # (x đầu, x cuối, cao, chữ): nét kẻ dọc "|" dính vào từ / đứng riêng / đọc thành chữ J
        def hang(y, *tu):
            return [(x0, x1, 10, t) for x0, x1, t in tu]
        cac = [hang(0, (100, 110, 'STT'), (140, 200, 'Họ'), (210, 250, 'tên'), (800, 860, 'Số'), (870, 900, 'tờ')),
               hang(1, (100, 200, '1|Lê'), (205, 245, 'Văn'), (250, 290, 'An'), (800, 840, '30')),
               hang(2, (100, 240, '2|Trần'), (245, 285, 'Thị'), (290, 340, 'Bình'), (800, 840, '31')),
               hang(3, (100, 110, '3'), (112, 115, '|'), (140, 190, 'Phạm'), (195, 250, 'Cường'), (800, 840, '32')),
               hang(4, (100, 200, '4|Võ'), (205, 235, 'Em'), (800, 840, '33')),
               hang(5, (100, 200, '5|Hồ'), (205, 235, 'Lan'), (800, 840, '34'))]
        luoi, rong = nguon_luoi.luoi_tu_hang(cac)
        self.assertEqual(rong, 3)
        self.assertEqual([r[0] for r in luoi[1:4]], ['1', '2', '3'])
        self.assertEqual([r[1] for r in luoi[1:4]], ['Lê Văn An', 'Trần Thị Bình', 'Phạm Cường'])
        self.assertEqual(luoi[0], ['STT', 'Họ tên', 'Số tờ'])

    def test_ranh_cot_khong_cat_giua_o_chu_thua(self):
        # cột ghi chú thưa: chữ "Đã kiểm đếm" không bị cắt thành ba cột
        hang = []
        for i in range(12):
            r = [(0, 10, str(i + 1)), (20, 100, 'Họ tên ' + str(i)), (200, 230, str(30 + i)), (260, 290, str(100 + i))]
            if i in (2, 3, 7):
                r.append((320, 340, 'Đã'))
                r.append((350, 380 + 5 * i, 'kiểm đếm'))
            hang.append(r)
        luoi, rong = nguon_luoi.luoi_tu_doan(hang, 6, 0.03, 20, 4)
        self.assertEqual(rong, 5)
        self.assertEqual(luoi[2][4], 'Đã kiểm đếm')


XS_PDF = [40, 75, 270, 450, 505, 565, 665]
TD_PDF = ['STT', 'Ho va ten', 'Dia chi', 'So to', 'So thua', 'Dien tich (m2)', 'Loai dat']
HANG_PDF = [
    ['1', 'Le Van An', ['ap 1, xa', 'Thu Nghiem'], ['30', '30'], ['100', '101'], ['215,5', '40'], ['ONT+CLN', 'CLN']],
    ['2', 'Tran Thi Binh', 'ap 2, xa Thu Nghiem', '31', '55', '120,3', 'LUC'],
    ['3', ['Pham Quoc', 'Cuong'], ['ap 2, xa', 'Thu Nghiem', '(chu su dung)'], '31', '56', '1.070,5', 'RSX'],
    ['4', 'Nguyen Thu Dung', 'khu pho 3, phuong Mau', ['32', '32'], ['7', '8'], ['88', '12'], ['ONT', 'BHK']],
    ['5', 'Vo Minh Em', 'ap 5, xa Thu Nghiem', '33', '71', '64,2', 'CLN'],
    ['6', 'Dang Hoai Phuong', 'ap 5, xa Thu Nghiem', '34', '72', '73', 'LUC'],
]
TEN_PDF = ['Le Van An', 'Tran Thi Binh', 'Pham Quoc Cuong', 'Nguyen Thu Dung', 'Vo Minh Em', 'Dang Hoai Phuong']


def _co_tesseract() -> bool:
    from pabt import ocr
    return not ocr.san_sang()


def _kiem_pdf(tc, kq):
    tc.assertEqual(kq.loi, [])
    tc.assertEqual([h['ho_ten'] for h in kq.ho], TEN_PDF)
    tc.assertEqual([(t['ma_ho'], t['so_to'], t['so_thua'], t['dt_thu_hoi'], t['loai_dat']) for t in kq.thua],
                   [(1, '30', '100', '215.5', 'ONT+CLN'), (1, '30', '101', '40', 'CLN'), (2, '31', '55', '120.3', 'LUC'),
                    (3, '31', '56', '1070.5', 'RSX'), (4, '32', '7', '88', 'ONT'), (4, '32', '8', '12', 'BHK'),
                    (5, '33', '71', '64.2', 'CLN'), (6, '34', '72', '73', 'LUC')])
    tc.assertEqual(kq.ho[0]['dia_chi'], 'ap 1, xa Thu Nghiem')                    # ô địa chỉ xuống 2 dòng nối lại
    tc.assertEqual(kq.ho[2]['dia_chi'], 'ap 2, xa Thu Nghiem (chu su dung)')


class TestPdfCoChu(_Co):
    """PDF có lớp chữ (văn bản ký hoặc chưa ký): chia cột theo vị trí từng ô chữ (QtPdf), ô xuống nhiều dòng nối về hộ, tiêu đề lặp
    ở trang sau và chữ ký cuối bảng bị bỏ."""

    def setUp(self):
        super().setUp()
        try:
            from PySide6.QtCore import QCoreApplication
            from PySide6.QtPdf import QPdfDocument  # noqa: F401
            QCoreApplication.instance() or QCoreApplication([])
        except ImportError:
            self.skipTest('bản Qt 5 không có QtPdf')

    def pdf(self, **kw):
        p = self.td / 'ds.pdf'
        p.write_bytes(pdf_tay.bang_pdf(TD_PDF, HANG_PDF, XS_PDF, **kw))
        return p

    def test_o_can_giua_theo_chieu_doc(self):
        kq = nhap_tho.doc(self.pdf(can_giua=True))
        _kiem_pdf(self, kq)
        self.assertEqual(kq.loai, 'pdf')
        self.assertEqual(kq.bo_cot.sheet, 'Văn bản PDF')

    def test_o_can_tren(self):
        _kiem_pdf(self, nhap_tho.doc(self.pdf(can_giua=False)))

    def test_nhieu_trang_tieu_de_lap_va_chu_ky(self):
        kq = nhap_tho.doc(self.pdf(can_giua=True, so_dong_moi_trang=5))
        _kiem_pdf(self, kq)
        self.assertGreaterEqual(kq.da_bo.get('dòng tiêu đề lặp lại (trang sau)', 0), 1)
        self.assertGreaterEqual(kq.da_bo.get('dòng chữ ký / ghi chú cuối bảng', 0), 1)

    def test_pdf_khong_co_lop_chu_la_ban_scan(self):
        p = self.td / 'rong.pdf'
        p.write_bytes(pdf_tay.tao_pdf([[]]))
        self.assertEqual(nguon_luoi._tu_pdf_chu(p), [])
        self.assertTrue(nguon_luoi.la_ban_scan(p))

    def test_file_pdf_hong_bao_loi_tieng_viet(self):
        p = self.td / 'hong.pdf'
        p.write_bytes(b'%PDF-1.4\nkhong phai pdf that\n')
        with self.assertRaises(LoiNhap):
            nguon_luoi.lay_nguon(p)


@unittest.skipUnless(_co_tesseract(), 'máy chưa có Tesseract tiếng Việt')
class TestScan(_Co):
    """Bản scan / ảnh: nhận dạng chữ (Tesseract đóng kèm), chia cột theo vị trí từng từ, nét kẻ khung bảng không thành chữ."""

    def anh(self, ten='ds.png', dinh_dang=None):
        try:
            from PySide6.QtPdf import QPdfDocument  # noqa: F401
        except ImportError:
            self.skipTest('bản Qt 5 không có QtPdf để dựng ảnh thử')
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen
        from PySide6.QtPdf import QPdfDocument
        QGuiApplication.instance() or QGuiApplication([])
        pdf = self.td / 'goc.pdf'
        pdf.write_bytes(pdf_tay.bang_pdf(TD_PDF, HANG_PDF, XS_PDF, so_dong_moi_trang=40, co=11, cach=22, can_giua=True))
        d = QPdfDocument()
        d.load(str(pdf))
        kt = d.pagePointSize(0)
        im = d.render(0, QSize(int(kt.width() * 300 / 72), int(kt.height() * 300 / 72)))
        nen = QImage(im.size(), QImage.Format.Format_RGB32)
        nen.fill(QColor('white'))
        pt = QPainter(nen)
        pt.drawImage(0, 0, im)
        pt.setPen(QPen(QColor('black'), 3))
        he = 300 / 72
        for x in [x - 6 for x in XS_PDF] + [XS_PDF[-1] + 100]:             # nét kẻ dọc của khung bảng
            pt.drawLine(int(x * he), int(40 * he), int(x * he), int(560 * he))
        pt.end()
        p = self.td / ten
        if dinh_dang:
            nen.save(str(p), dinh_dang)
        else:
            nen.save(str(p))
        return p

    def kiem(self, kq):
        self.assertEqual(kq.loai, 'scan')
        self.assertEqual(kq.loi, [])
        self.assertEqual(len(kq.ho), 6)
        self.assertEqual([t['so_thua'] for t in kq.thua], ['100', '101', '55', '56', '7', '8', '71', '72'])
        self.assertEqual([t['loai_dat'] for t in kq.thua], ['ONT+CLN', 'CLN', 'LUC', 'RSX', 'ONT', 'BHK', 'CLN', 'LUC'])
        self.assertTrue(any('nhận dạng' in x for x in kq.thong_bao))

    def test_anh_png(self):
        self.kiem(nhap_tho.doc(self.anh('ds.png')))

    def test_anh_jpg(self):
        self.kiem(nhap_tho.doc(self.anh('ds.jpg', 'JPG')))

    def test_huy_giua_chung(self):
        from pabt import ocr
        with self.assertRaises(ocr.DaHuy):
            nhap_tho.doc(self.anh('ds.png'), cho=lambda: True)


class TestGiaoDien(_Co):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication
        from pabt import giao_dien
        self.app = QApplication.instance() or QApplication([])
        if getattr(self.app, '_bo_to_mau', None) is None:     # 1.0.92: gỡ bảng kiểu đã áp sau bài (để lại làm test_toc_do_1079 đo bố cục sai)
            self.addCleanup(giao_dien.bo_ap_dung, self.app)
        giao_dien.ap_dung(self.app)
        os.environ.setdefault('PABT_THU_MUC_MAY', str(self.td))

    def hop(self):
        from pabt.man_hinh_du_an_moi import HopDuAnMoi
        h = HopDuAnMoi(luu_cai_dat=False)
        h.im_lang = True
        self.addCleanup(h.deleteLater)
        return h

    def test_nhap_xls_va_chinh_cot(self):
        p = self.td / 'mau.xls'
        p.write_bytes(mau_xls.bytes_xls())
        h = self.hop()
        self.assertFalse(h.b_chinh_cot.isEnabled())
        dong = h.nap_excel(str(p))
        self.assertEqual(len(dong), 6)
        self.assertTrue(h.b_chinh_cot.isEnabled())
        self.assertEqual(h.bang_tho.rowCount(), 6)
        self.assertEqual(h.bang_tho.item(0, 0).text(), 'Lê Văn An')
        from pabt.man_hinh_ghep_cot import HopGhepCot
        kq = h._nguon_doc[1]
        hop = HopGhepCot(h, 'mau.xls', kq.nguons, kq.bo_cot)
        hop.im_lang = True
        self.addCleanup(hop.deleteLater)
        self.assertEqual(hop.ket_qua.ho[0]['ho_ten'], 'Lê Văn An')
        hop.dat_cot('dia_chi', None)                                   # bỏ cột địa chỉ: vẫn đọc được, địa chỉ trống
        self.assertEqual(hop.ket_qua.ho[0]['dia_chi'], '')
        hop.dat_cot('ho_ten', None)
        hop.dat_cot('so_to', None)
        hop.dat_cot('so_thua', None)
        hop.dat_cot('dt_thu_hoi', None)
        self.assertTrue(hop.ket_qua is None or not hop.ket_qua.ho or hop.ket_qua.ho[0]['ho_ten'].startswith('Hộ'))

    def test_khong_nhan_duoc_thi_bao_ly_do(self):
        p = self.xlsx('la.xlsx', lambda wb: wb.active.append(['Mã', 'Giá trị']))
        h = self.hop()
        self.assertIsNone(h.nap_excel(str(p)))
        self.assertIn('Chỉnh cột', h.thong_bao_cuoi)

    def test_ghep_cot_bang_tay_cho_bang_khong_co_tieu_de_nhan_ra(self):
        def bang(wb):
            ws = wb.active
            ws.append(['Gia chu', 'Noi o', 'A', 'B', 'C'])                # tiêu đề tiếng không dấu lạ
            for i, (stt, ten, dc, cccd, to, thua, dt, loai) in enumerate(_du_lieu(6)):
                ws.append([ten or '', dc or '', to, thua, dt])
        p = self.xlsx('la2.xlsx', bang)
        kq = nhap_tho.doc(p)
        self.assertTrue(kq.loi or kq.ho)
        from pabt.man_hinh_ghep_cot import HopGhepCot
        hop = HopGhepCot(None, 'la2.xlsx', kq.nguons, None)
        hop.im_lang = True
        self.addCleanup(hop.deleteLater)
        hop.o_dong.setValue(2)
        hop.dat_cot('ho_ten', 0)
        hop.dat_cot('dia_chi', 1)
        hop.dat_cot('so_to', 2)
        hop.dat_cot('so_thua', 3)
        hop.dat_cot('dt_thu_hoi', 4)
        self.assertIsNotNone(hop.ket_qua)
        self.assertEqual(len(hop.ket_qua.thua), len([x for x in _du_lieu(6)]))
        self.assertTrue(hop.bo_cot().thu_cong)
        self.assertEqual(hop.bo_cot().cot['so_thua'], 3)


if __name__ == '__main__':
    unittest.main()
