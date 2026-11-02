"""Kiểm thử cập nhật bộ đơn giá từ Excel / Word / CSV / PDF / trang web."""
from __future__ import annotations
import http.server
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from functools import partial
from pathlib import Path

import openpyxl

from pabt import csdl, don_gia
from pabt import cap_nhat_web as cw
from pabt import nhap_don_gia as ndg
from pabt.lap_pa import LoiNhap

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


def _mot_cay():
    """Một cây trồng có sẵn trong bộ đơn giá tích hợp: (mã, tên, ĐVT, giá)."""
    c = sqlite3.connect(don_gia.file_goc())
    r = c.execute("SELECT ma, ten, dvt, don_gia FROM dm_taisan WHERE nhom = 3 AND don_gia > 1000 LIMIT 1").fetchone()
    c.close()
    return r[0], r[1], r[2], int(float(r[3]))


def _docx(p, dong):
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    hang = ''.join('<w:tr>' + ''.join(f'<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>' for c in r) + '</w:tr>' for r in dong)
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr('word/document.xml', f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body><w:tbl>{hang}</w:tbl></w:body></w:document>')


def _pdf(p, dong):
    """PDF tối giản có lớp chữ (font Helvetica chuẩn), mỗi phần tử một dòng."""
    nd = ''.join(f'BT /F1 12 Tf 50 {780 - 24 * i} Td ({l}) Tj ET\n' for i, l in enumerate(dong)).encode('latin-1')
    obj = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
           b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
           b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
           b'<< /Length ' + str(len(nd)).encode() + b' >>\nstream\n' + nd + b'endstream']
    out, off = b'%PDF-1.4\n', []
    for i, o in enumerate(obj, start=1):
        off.append(len(out))
        out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
    x = len(out)
    out += f'xref\n0 {len(obj) + 1}\n0000000000 65535 f \n'.encode() + b''.join(f'{o:010d} 00000 n \n'.encode() for o in off)
    out += f'trailer << /Size {len(obj) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF'.encode()
    Path(p).write_bytes(out)


class _Im(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):                          # máy chủ thử: không in nhật ký truy cập
        pass


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.ma, self.ten, self.dvt, self.gia = _mot_cay()
        self.dong = [['STT', 'Tên cây trồng', 'ĐVT', 'Đơn giá (đồng)'],
                     ['1', self.ten, self.dvt, f'{self.gia + 5000:,}'.replace(',', '.')],
                     ['2', 'Cây sầu riêng ghép mới trồng thử', 'cây', '250.000'],
                     ['', 'Cộng', '', ''],
                     ['3', 'Cây chưa có giá', 'cây', 'thỏa thuận']]

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def _kiem_muc(self, ds):
        self.assertEqual([(m.ten, m.don_gia) for m in ds],
                         [(self.ten, self.gia + 5000), ('Cây sầu riêng ghép mới trồng thử', 250000)])


class TestDoc(CoSo):
    def test_excel(self):
        p = self.td / 'dg.xlsx'
        wb = openpyxl.Workbook()
        wb.active.append(['BẢNG ĐƠN GIÁ CÂY TRỒNG'])
        for r in self.dong:
            wb.active.append(r)
        wb.save(p)
        self._kiem_muc(ndg.nhan_muc(ndg.doc_bang(p)))

    def test_word(self):
        p = self.td / 'dg.docx'
        _docx(p, self.dong)
        self._kiem_muc(ndg.nhan_muc(ndg.doc_bang(p)))

    def test_csv_nghin_dong(self):
        p = self.td / 'dg.csv'
        p.write_text('Tên;ĐVT;Đơn giá (nghìn đồng)\nCây xoài ghép 3 năm;cây;450\n', encoding='utf-8')
        ds = ndg.nhan_muc(ndg.doc_bang(p))
        self.assertEqual([(m.ten, m.don_gia) for m in ds], [('Cây xoài ghép 3 năm', 450000)])

    @unittest.skipUnless(CO_QT, 'không có PySide6')
    def test_pdf_co_chu(self):
        p = self.td / 'dg.pdf'
        _pdf(p, ['BANG DON GIA', 'TS9001 Mai che khung thep lop ton m2 350.000', '2 Hang rao luoi B40 m 120.000'])
        ds = ndg.nhan_muc(ndg.doc_bang(p))
        self.assertEqual([(m.ma, m.ten, m.dvt, m.don_gia) for m in ds],
                         [('TS9001', 'Mai che khung thep lop ton', 'm²', 350000), ('', 'Hang rao luoi B40', 'm', 120000)])
        anh = self.td / 'scan.pdf'
        _pdf(anh, [])
        with self.assertRaises(LoiNhap):                                    # PDF không có chữ (ảnh scan)
            ndg.doc_bang(anh)

    def test_noi_dung_khac_duoi(self):
        # trang web (đăng nhập / báo lỗi) tải về mang đuôi .pdf: báo đúng là trang web, không báo nhầm "ảnh scan"
        p = self.td / 'bang_gia.pdf'
        p.write_text('<!DOCTYPE html><html><body>Đăng nhập</body></html>', encoding='utf-8')
        with self.assertRaises(LoiNhap) as kq:
            ndg.doc_bang(p)
        self.assertNotIsInstance(kq.exception, ndg.LoiPdfScan)
        self.assertIn('trang web', str(kq.exception))
        # file hỏng / tải dở
        p.write_bytes(b'\x00\x01rac')
        with self.assertRaisesRegex(LoiNhap, 'hỏng'):
            ndg.doc_bang(p)
        # Excel thật mang đuôi .pdf: đọc theo nội dung
        x = self.td / 'gia.xlsx'
        wb = openpyxl.Workbook()
        for r in self.dong:
            wb.active.append(r)
        wb.save(x)
        p.write_bytes(x.read_bytes())
        self.assertEqual(ndg.loai_that(p), '.xlsx')
        self._kiem_muc(ndg.nhan_muc(ndg.doc_bang(p)))

    @unittest.skipUnless(CO_QT, 'không có PySide6')
    def test_pdf_scan_ocr(self):
        from unittest import mock
        from pabt import ocr
        anh = self.td / 'scan.pdf'
        _pdf(anh, [])
        with self.assertRaises(ndg.LoiPdfScan):
            ndg.doc_bang(anh)
        with mock.patch.object(ocr, 'san_sang', return_value='Máy chưa có Tesseract.'):
            with self.assertRaisesRegex(ndg.LoiPdfScan, 'Tesseract'):
                ndg.doc_bang_ocr(anh)
        # có Tesseract: đọc chữ nhận dạng được theo mẫu "<tên> <ĐVT> <đơn giá>"
        with mock.patch.object(ocr, 'san_sang', return_value=''), \
                mock.patch.object(ocr, 'doc_chu', return_value=['BANG DON GIA', 'Hang rao luoi B40 m 120.000']):
            ds = ndg.nhan_muc(ndg.doc_bang_ocr(anh))
        self.assertEqual([(m.ten, m.dvt, m.don_gia) for m in ds], [('Hang rao luoi B40', 'm', 120000)])

    def test_dinh_dang_khong_ho_tro(self):
        for duoi in ('.xls', '.doc', '.jpg'):
            p = self.td / f'x{duoi}'
            p.write_bytes(b'0')
            with self.assertRaises(LoiNhap):
                ndg.doc_bang(p)

    def test_doc_gia(self):
        self.assertEqual([ndg.doc_gia(x) for x in ('1.480.500', '9.445', '250000', 1480500.0, '12,5', 'abc', '')],
                         [1480500, 9445, 250000, 1480500, None, None, None])


class TestApDung(CoSo):
    def test_so_khop_va_ap_dung(self):
        p = self.td / 'dg.xlsx'
        wb = openpyxl.Workbook()
        for r in self.dong:
            wb.active.append(r)
        wb.save(p)
        ds = ndg.so_khop(ndg.nhan_muc(ndg.doc_bang(p)), 3)
        self.assertEqual([(m.trang_thai, m.ma_khop) for m in ds], [('cập nhật', self.ma), ('mới', '')])
        cu = don_gia.thong_tin()['phien_ban']
        tt = ndg.ap_dung(ds, 3, 'dg.xlsx')
        self.assertEqual((tt['so_moi'], tt['so_cap_nhat']), (1, 1))
        self.assertGreater(tt['phien_ban'], cu)
        self.assertEqual(don_gia.file_dang_dung(), don_gia.file_cap_nhat())
        c = sqlite3.connect(don_gia.file_dang_dung())
        self.assertEqual(c.execute('SELECT don_gia FROM dm_taisan WHERE ma = ?', (self.ma,)).fetchone()[0], str(self.gia + 5000))
        self.assertEqual(c.execute("SELECT nhom, don_gia FROM dm_taisan WHERE ten LIKE 'Cây sầu riêng ghép mới%'").fetchone(), (3, '250000'))
        c.close()
        # bộ gốc đóng gói không bị sửa
        c = sqlite3.connect(don_gia.file_goc())
        self.assertEqual(int(float(c.execute('SELECT don_gia FROM dm_taisan WHERE ma = ?', (self.ma,)).fetchone()[0])), self.gia)
        c.close()
        # lần 2: không còn gì mới
        ds = ndg.so_khop(ndg.nhan_muc(ndg.doc_bang(p)), 3)
        self.assertEqual({m.trang_thai for m in ds}, {'giữ nguyên'})
        with self.assertRaises(LoiNhap):
            ndg.ap_dung(ds, 3, 'dg.xlsx')

    def test_tai_tu_trang_web(self):
        web = self.td / 'web'
        web.mkdir()
        wb = openpyxl.Workbook()
        for r in self.dong:
            wb.active.append(r)
        wb.save(web / 'don_gia_cay.xlsx')
        (web / 'index.html').write_text('<html><body><a href="tin.html">Tin</a> '
                                        '<a href="don_gia_cay.xlsx">Bảng đơn giá cây trồng</a></body></html>', encoding='utf-8')
        sv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(web)))
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        try:
            goc = f'http://127.0.0.1:{sv.server_address[1]}'
            kq = cw.tai_ve(goc + '/index.html', self.td)
            self.assertEqual(kq['lien_ket'], [('Bảng đơn giá cây trồng', goc + '/don_gia_cay.xlsx')])
            kq = cw.tai_ve(kq['lien_ket'][0][1], self.td)
            self._kiem_muc(ndg.nhan_muc(ndg.doc_bang(kq['file'])))
            with self.assertRaises(LoiNhap):
                cw.tai_ve('ftp://x', self.td)
        finally:
            sv.shutdown()
            sv.server_close()

    def test_lien_ket_tren_trang(self):
        html = ('<a href="tin.html">Tin tức</a>'
                '<a href="/Download.aspx?file=QD_don_gia.pdf">Quyết định</a>'
                '<a href="/van-ban/tai?id=12"><i class="icon"></i> Tải về</a>'
                '<a href="https://drive.google.com/file/d/AbC_123-x/view?usp=sharing">Bảng giá cây</a>'
                '<iframe src="/viewer/bang_gia.pdf"></iframe>'
                '<script>var tep = "\\/files\\/gia_nha.xlsx"; window.open(\'/tep/khac.docx\')</script>'
                '<a href="javascript:void(0)">Tải về</a><a href="#top">Lên đầu</a>')
        ds = cw.lien_ket_file(html, 'https://so.gov.vn/tin/123.html')
        self.assertEqual([u for _, u in ds], [
            'https://so.gov.vn/Download.aspx?file=QD_don_gia.pdf', 'https://so.gov.vn/van-ban/tai?id=12',
            'https://drive.google.com/file/d/AbC_123-x/view?usp=sharing', 'https://so.gov.vn/viewer/bang_gia.pdf',
            'https://so.gov.vn/files/gia_nha.xlsx', 'https://so.gov.vn/tep/khac.docx'])
        self.assertEqual(ds[0][0], 'Quyết định')
        self.assertEqual(cw._google('https://docs.google.com/spreadsheets/d/XyZ_9/edit#gid=0'),
                         'https://docs.google.com/spreadsheets/d/XyZ_9/export?format=xlsx')
        self.assertEqual(cw._google('https://drive.google.com/drive/u/0/folders/F01d3r'),
                         'https://drive.google.com/embeddedfolderview?id=F01d3r#list')
        self.assertIn('id=AbC', cw._google('https://drive.google.com/open?id=AbC'))

    def test_tai_trang_web_kho(self):
        """Trang trả HTML cho đường dẫn .pdf, nút "Tải về" không có đuôi file, đường dẫn trong JavaScript."""
        web = self.td / 'web'
        (web / 'files').mkdir(parents=True)
        wb = openpyxl.Workbook()
        for r in self.dong:
            wb.active.append(r)
        wb.save(web / 'files' / 'js_gia.xlsx')
        (web / 'tai_ve').write_bytes((web / 'files' / 'js_gia.xlsx').read_bytes())         # không đuôi, application/octet-stream
        (web / 'bang_gia.pdf').write_text('<html><body><a href="tai_ve">Tải về</a>'
                                          '<script>var f = "files/js_gia.xlsx";</script></body></html>', encoding='utf-8')
        (web / 'trong.html').write_text('<html><body><a href="tin.html">Tin</a></body></html>', encoding='utf-8')
        sv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(web)))
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        try:
            goc = f'http://127.0.0.1:{sv.server_address[1]}'
            kq = cw.tai_ve(goc + '/bang_gia.pdf', self.td)                    # "PDF" thực ra là trang web
            self.assertEqual([u for _, u in kq['lien_ket']], [goc + '/tai_ve', goc + '/files/js_gia.xlsx'])
            kq = cw.tai_ve(goc + '/tai_ve', self.td)
            self.assertTrue(kq['file'].endswith('.xlsx'))                       # đặt đuôi theo nội dung
            self._kiem_muc(ndg.nhan_muc(ndg.doc_bang(kq['file'])))
            with self.assertRaisesRegex(LoiNhap, 'Sao chép địa chỉ liên kết'):
                cw.tai_ve(goc + '/trong.html', self.td)
            with self.assertRaisesRegex(LoiNhap, '404'):
                cw.tai_ve(goc + '/khong_co.xlsx', self.td)
        finally:
            sv.shutdown()
            sv.server_close()

    def test_bang_phan_cap_van_ban_ubnd(self):
        """Bảng như phụ lục QĐ 48/2025, 66/2025 của UBND tỉnh Đồng Nai: nhóm La Mã, ô giá có nhãn vụ, dòng tiếp tục,
        dòng con STT trống / '-' / 'a' dưới dòng cha không giá, mật độ trong tên cha, ĐVT 'đồng/bụi', đơn vị ở tiêu đề."""
        dong = [['Số: 48/2025/QĐ-UBND', '', 'Đồng Nai, ngày 23 tháng 10 năm 2025'],
                ['STT', 'Tên cây trồng', 'Đơn vị tính', 'Đơn giá bồi thường (đồng)'],
                ['I', 'Nhóm cây lương thực', '', ''],
                ['1', 'Cây lúa', 'Ha', 'Đông Xuân: 24.880.000'],
                ['', '', 'Ha', 'Hè Thu, Mùa: 24.237.000'],
                ['2', 'Cây khoai lang', 'Ha', '72.477.000'],
                ['3', 'Cây bưởi (Mật độ 210 cây/ha)', '', ''],
                ['', 'Năm thứ 1', 'Cây', '313.119'],
                ['4', 'Hỗ trợ di dời chậu kiểng', '', ''],
                ['*', 'Trường hợp dưới 100 chậu/hộ', '', ''],
                ['-', 'Chậu có đường kính < 10 cm', 'chậu', '2.600'],
                ['Phụ lục II'],
                ['STT', 'Tên cây trồng', 'Đơn giá bồi thường(đồng/ha)'],
                ['1', 'Cây bắp', 'Đông Xuân: 40.000.000'],
                ['2', 'Tre tàu, gai (mật độ 200 bụi/ha)'],
                ['a', 'Cây mới trồng dưới 1 năm tuổi', '34.000']]
        ds = ndg.nhan_muc(dong)
        self.assertEqual([(m.ten, m.dvt, m.don_gia, m.nhom) for m in ds], [
            ('Cây lúa (Đông Xuân)', 'Ha', 24880000, 3), ('Cây lúa (Hè Thu, Mùa)', 'Ha', 24237000, 3),
            ('Cây khoai lang', 'Ha', 72477000, 3), ('Cây bưởi - Năm thứ 1', 'Cây', 313119, 3),
            ('Hỗ trợ di dời chậu kiểng - Trường hợp dưới 100 chậu/hộ - Chậu có đường kính < 10 cm', 'chậu', 2600, 3),
            ('Cây bắp (Đông Xuân)', 'ha', 40000000, 3), ('Tre tàu, gai - Cây mới trồng dưới 1 năm tuổi', 'ha', 34000, 3)])
        # so khớp: tên trong ngoặc / dấu câu khác vẫn nhận ra mục có sẵn
        c = sqlite3.connect(don_gia.file_goc())
        r = c.execute("SELECT ma, ten, dvt, don_gia FROM dm_taisan WHERE ten = 'Cây bưởi - Năm thu hoạch thứ 1 - 5'").fetchone()
        c.close()
        m = ndg.so_khop([ndg.Muc('Cây bưởi - Năm thu hoạch thứ 1 - 5', r[2], int(float(r[3])), nhom=3)])[0]
        self.assertEqual((m.ma_khop, m.trang_thai), (r[0], 'giữ nguyên'))

    def test_phan_tich_van_ban(self):
        dong = [['ỦY BAN NHÂN DÂN THÀNH PHỐ ĐỒNG NAI', '', 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'],
                ['Số: 12/2026/QĐ-UBND', '', 'Đồng Nai, ngày 5 tháng 3 năm 2026'], ['QUYẾT ĐỊNH'],
                ['Sửa đổi, bổ sung đơn giá bồi thường nhà, công trình xây dựng khi Nhà nước thu hồi đất'],
                ['Căn cứ Luật Đất đai ngày 18 tháng 01 năm 2024;'], ['Điều 1. ...'],
                ['2. Bãi bỏ mục 14, 89, 90 bảng 5 Phụ lục VI.']]
        vb = ndg.phan_tich_van_ban(dong)
        self.assertEqual((vb['so_hieu'], vb['ngay'], vb['co_quan'], vb['loai_vb'], vb['nhom'], vb['dong_nai'], vb['sua_doi']),
                         ('12/2026/QĐ-UBND', '05/03/2026', 'Ủy ban nhân dân thành phố Đồng Nai', 'Quyết định', 2, True, True))
        self.assertTrue(vb['trich_yeu'].startswith('Sửa đổi, bổ sung đơn giá'))
        self.assertEqual(vb['can_xem'], ['2. Bãi bỏ mục 14, 89, 90 bảng 5 Phụ lục VI.'])
        # "khi Nhà nước thu hồi đất" không làm văn bản chính sách thành nhóm nhà
        self.assertEqual(ndg.nhom_theo_chu('Quy định bồi thường, hỗ trợ, tái định cư khi Nhà nước thu hồi đất'), 4)
        # văn bản đã có trong danh mục văn bản căn cứ của bộ đơn giá tích hợp (QĐ 48/2025, sửa đổi bởi QĐ 66/2025)
        co = ndg.van_ban_da_co()
        self.assertTrue(ndg.da_co('48/2025/QĐ-UBND', co) and ndg.da_co('66 / 2025 / QĐ-UBND', co))
        self.assertFalse(ndg.da_co('8/2025/QĐ-UBND', co) or ndg.da_co('99/2026/QĐ-UBND', co))

    def _cong_bao(self):
        """Máy chủ giả kiểu Công báo Đồng Nai: trang tìm kiếm -> trang chi tiết -> nút "Tải tập tin" (?download=1&id=0)."""
        web = self.td / 'web'
        web.mkdir()
        _docx(web / 'qd99.docx', [['STT', 'Tên cây trồng', 'Đơn vị tính', 'Đơn giá bồi thường (đồng)'],
                                  ['1', self.ten, self.dvt, f'{self.gia + 5000:,}'.replace(',', '.')],
                                  ['2', 'Cây sầu riêng ghép mới trồng thử', 'cây', '250.000']])
        dong_dau = ('<w:p><w:r><w:t>Số: 99/2026/QĐ-UBND</w:t></w:r></w:p><w:p><w:r><w:t>Đồng Nai, ngày 01 tháng 9 năm 2026'
                    '</w:t></w:r></w:p><w:p><w:r><w:t>QUYẾT ĐỊNH</w:t></w:r></w:p><w:p><w:r><w:t>Ban hành đơn giá bồi thường '
                    'cây trồng trên địa bàn thành phố Đồng Nai</w:t></w:r></w:p>')
        with zipfile.ZipFile(web / 'qd99.docx') as z:
            xml = z.read('word/document.xml').decode('utf-8').replace('<w:body>', '<w:body>' + dong_dau)
        with zipfile.ZipFile(web / 'qd99.docx', 'w') as z:
            z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
            z.writestr('word/document.xml', xml)
        (web / 'tep').mkdir()
        (web / 'tep' / 'tai99').write_bytes((web / 'qd99.docx').read_bytes())
        (web / 'ct99.html').write_text('<html><head><title>Quyết định số 99/2026/QĐ-UBND ban hành đơn giá bồi thường cây '
                                       'trồng</title></head><body><a href="tep/tai99">Tải tập tin 99-2026-qd.docx</a></body></html>',
                                       encoding='utf-8')
        (web / 'tep' / 'tai48').write_bytes((web / 'qd99.docx').read_bytes())
        (web / 'ct48.html').write_text('<html><head><title>Quyết định số 48/2025/QĐ-UBND ban hành Quy định đơn giá bồi '
                                       'thường thiệt hại về cây trồng</title></head><body><a href="tep/tai48">Tải tập tin '
                                       '48-2025-qd.doc</a></body></html>', encoding='utf-8')
        (web / 'tim.html').write_text('<html><body><a href="tin.html">Tin tức sự kiện</a>'
                                      '<a href="ct99.html">Quyết định số 99/2026/QĐ-UBND ban hành đơn giá bồi thường cây trồng</a>'
                                      '<a href="ct48.html">Quyết định số 48/2025/QĐ-UBND ban hành Quy định đơn giá bồi thường '
                                      'thiệt hại về cây trồng</a><a href="ct77.html">Quyết định số 77/2026/QĐ-UBND hỗ trợ kinh '
                                      'phí vận tải hành khách</a></body></html>', encoding='utf-8')
        sv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(_Im, directory=str(web)))
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        self.addCleanup(sv.server_close)
        self.addCleanup(sv.shutdown)
        return f'http://127.0.0.1:{sv.server_address[1]}'

    def test_quet_web(self):
        goc = self._cong_bao()
        ds = cw.quet(goc + '/tim.html')
        self.assertEqual([(t.so_hieu, t.tep, t.da_co, t.chon, t.nhom) for t in ds],
                         [('99/2026/QĐ-UBND', '99-2026-qd.docx', False, True, 3),
                          ('48/2025/QĐ-UBND', '48-2025-qd.doc', True, False, 3)])      # QĐ 77 (vận tải) không liên quan
        kq = cw.tai_ve(ds[0].url, self.td)
        self.assertTrue(kq['file'].endswith('.docx'))
        vb = ndg.phan_tich_van_ban(ndg.doc_bang(kq['file']), ds[0].ten)
        self.assertEqual((vb['so_hieu'], vb['ngay'], vb['nhom']), ('99/2026/QĐ-UBND', '01/09/2026', 3))

    def test_nguon_trung_uong(self):
        # nơi tìm, nguồn gợi ý: Công báo Đồng Nai, CSDL quốc gia văn bản pháp luật, Chính phủ, Thư viện pháp luật
        goi_y = dict((v, t) for t, v in cw.nguon_goi_y())
        for nguon in ('vbpl|bồi thường, hỗ trợ, tái định cư', 'https://vanban.chinhphu.vn/', 'https://congbao.chinhphu.vn/',
                      'tvpl|thu hồi đất', 'giá đất'):
            self.assertIn(nguon, goi_y)
        self.assertTrue(cw.duong_dan('vbpl|thu hồi đất').startswith('https://vbpl.vn/') )
        self.assertIn('thu+h%E1%BB%93i', cw.duong_dan('vbpl|thu hồi đất'))
        self.assertTrue(cw.duong_dan('giá đất').startswith(cw.CONG_BAO_DONG_NAI))
        self.assertTrue(cw.duong_dan('giá đất', 'tvpl').startswith('https://thuvienphapluat.vn/'))
        self.assertEqual(cw.duong_dan('https://x.vn/a?b=1'), 'https://x.vn/a?b=1')
        # trang đổi cấu trúc: sửa / thêm nơi tìm, nguồn bằng nguon_web.json (mẫu phải https và có {q})
        may = Path(os.environ['PABT_THU_MUC_MAY'])
        may.mkdir(parents=True, exist_ok=True)
        (may / 'nguon_web.json').write_text(json.dumps({
            'tim': {'vbpl': ['VBPL mới', 'https://vbpl.vn/tim?tu={q}'], 'xau': ['Không an toàn', 'http://x.vn/?q={q}']},
            'goi_y': [['Bộ Nông nghiệp và Môi trường: văn bản mới', 'https://example.gov.vn/van-ban']]}), encoding='utf-8')
        self.assertEqual(cw.duong_dan('vbpl|đất'), 'https://vbpl.vn/tim?tu=%C4%91%E1%BA%A5t')
        self.assertNotIn('xau', cw.noi_tim())
        self.assertIn(('Bộ Nông nghiệp và Môi trường: văn bản mới', 'https://example.gov.vn/van-ban'), cw.nguon_goi_y())
        # văn bản Trung ương: số hiệu NĐ / TT / QH, cơ quan, loại, trích yếu; chấm điểm -> nhóm chính sách, tự chọn
        vb = ndg.phan_tich_van_ban([['CHÍNH PHỦ'], ['Số: 88/2024/NĐ-CP'], ['Hà Nội, ngày 15 tháng 7 năm 2024'], ['NGHỊ ĐỊNH'],
                                    ['Quy định về bồi thường, hỗ trợ, tái định cư khi Nhà nước thu hồi đất'], ['Căn cứ Luật']])
        self.assertEqual((vb['so_hieu'], vb['ngay'], vb['co_quan'], vb['loai_vb']),
                         ('88/2024/NĐ-CP', '15/07/2024', 'Chính phủ', 'Nghị định'))
        self.assertTrue(vb['trich_yeu'].startswith('Quy định về bồi thường'))
        vb = ndg.phan_tich_van_ban([['QUỐC HỘI'], ['Luật số: 31/2024/QH15'], ['LUẬT ĐẤT ĐAI'], ['Căn cứ Hiến pháp']])
        self.assertEqual((vb['so_hieu'], vb['co_quan'], vb['loai_vb'], vb['trich_yeu']),
                         ('31/2024/QH15', 'Quốc hội', 'Luật', 'LUẬT ĐẤT ĐAI'))
        vb = ndg.phan_tich_van_ban([['BỘ NÔNG NGHIỆP VÀ MÔI TRƯỜNG'], ['Số: 10/2026/TT-BNNMT'], ['THÔNG TƯ'], ['Hướng dẫn …']])
        self.assertEqual((vb['so_hieu'], vb['co_quan'], vb['loai_vb']), ('10/2026/TT-BNNMT', 'Bộ Nông nghiệp và môi trường', 'Thông tư'))
        web = self.td / 'tw'
        web.mkdir()
        # NĐ 88/2024 đã có trong danh mục văn bản của bộ đơn giá; NĐ 999/2026 (số GIẢ LẬP) là văn bản mới -> tự chọn
        (web / 'moi.html').write_text('<html><body><a href="nd88.docx">Nghị định số 88/2024/NĐ-CP quy định về bồi thường, hỗ '
                                      'trợ, tái định cư khi Nhà nước thu hồi đất</a><a href="nd999.pdf">Nghị định số '
                                      '999/2026/NĐ-CP sửa đổi quy định bồi thường, hỗ trợ, tái định cư</a><a href="tt9.pdf">'
                                      'Thông tư số 9/2026/TT-BYT về y tế học đường</a></body></html>', encoding='utf-8')
        sv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(_Im, directory=str(web)))
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        self.addCleanup(sv.server_close)
        self.addCleanup(sv.shutdown)
        ds = cw.quet(f'http://127.0.0.1:{sv.server_address[1]}/moi.html')
        self.assertEqual([(t.so_hieu, t.nhom, t.da_co, t.chon) for t in ds if t.diem > 0],
                         [('999/2026/NĐ-CP', 4, False, True), ('88/2024/NĐ-CP', 4, True, False)])

    @unittest.skipUnless(CO_QT, 'không có PySide6')
    def test_man_hinh(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from PySide6.QtCore import Qt
        from pabt.man_hinh_nhap_don_gia import HopNhapDonGia
        p = self.td / 'dg.docx'
        _docx(p, self.dong)
        d = HopNhapDonGia(p)
        d.im_lang = True
        # tự động: dòng cây trồng tự vào nhóm 3, khớp mục có sẵn
        self.assertEqual(d.o_nhom.currentData(), 0)
        self.assertEqual([(m.nhom, m.trang_thai) for m in d.ds], [(3, 'cập nhật'), (3, 'mới')])
        d.o_nhom.setCurrentIndex(d.o_nhom.findData(3))
        self.assertEqual(d.bang.rowCount(), 2)
        d.bang.item(1, 0).setCheckState(Qt.CheckState.Unchecked)           # bỏ mục mới
        d.accept()
        self.assertEqual((d.ket_qua['so_moi'], d.ket_qua['so_cap_nhat']), (0, 1))


# văn bản GIẢ LẬP kiểu QĐ 31/2025/QĐ-UBND (đơn giá vật nuôi viết trong điều khoản, không có bảng) - số liệu không phải giá thật
LOI_VAN = [
    'ỦY BAN NHÂN DÂN TỈNH ĐỒNG NAI', 'Số: 31/2025/QĐ-UBND', 'Đồng Nai, ngày 29 tháng 8 năm 2025', 'QUYẾT ĐỊNH',
    'Ban hành Quy định đơn giá bồi thường thiệt hại về vật nuôi là thủy sản khi Nhà nước thu hồi đất',
    'Căn cứ Luật Đất đai số 31/2024/QH15;', 'Điều 3. Đơn giá bồi thường đối với vật nuôi là thủy sản', '1. Đối với ao nuôi cá:',
    'a) Cá giống: 30.000 đồng/m² mặt nước;', 'b) Cá thịt nuôi thâm canh: 45.000', 'đồng/m² mặt nước;',
    'c) Cá thịt nuôi quảng canh là 18.000 đồng/m² mặt nước.',
    '2. Đối với nuôi tôm: tôm thẻ chân trắng 60.000 đồng/m²; tôm càng xanh 52.000 đồng/m².',
    '3. Nuôi cá lồng, bè được bồi thường 1,5 triệu đồng/lồng.', '4. Đơn giá hỗ trợ chi phí di chuyển vật nuôi là 3.000.000 đồng/hộ.',
    '5. Ba ba, lươn nuôi: từ 20.000 đến 40.000 đồng/kg tùy kích cỡ.', 'Điều 4. Tổ chức thực hiện',
    'Mức bồi thường bằng 30% giá trị sản lượng thu hoạch.']


# văn bản GIẢ LẬP theo đúng cách viết của QĐ 31/2025/QĐ-UBND bản thật (đoạn Word): tiêu đề khoản không có ":", điều kiện đứng SAU
# số tiền ("… là A đồng/ha/vụ đối với …, B đồng/ha/vụ đối với …"), câu "Đối với các hình thức nuôi như: …", giá trần - số liệu giả
DIEU_KIEN = [
    'Điều 4. Đơn giá bồi thường vật nuôi là thủy sản',
    '1. Bồi thường thiệt hại ngừng sản xuất đối với ao nuôi tôm nước lợ',
    'a) Nuôi quảng canh là 10.000.000 đồng/ha/vụ đối với thủy sản nuôi dưới 50% định mức kinh tế kỹ thuật thời gian nuôi trồng '
    'thủy sản, 7.000.000 đồng/ha/vụ đối với thủy sản nuôi từ 50% đến 80% định mức kinh tế kỹ thuật thời gian nuôi trồng thủy '
    'sản. Đối với các hình thức nuôi như: nuôi cua là 9.000.000 đồng/ha/vụ đối với thủy sản nuôi dưới 50% định mức kinh tế kỹ '
    'thuật thời gian nuôi trồng thủy sản.',
    '2. Bồi thường thiệt hại ngừng sản xuất đối với cá nuôi lồng bè',
    'Đối với cá nuôi lồng bè là 50.000.000 đồng/100m3/vụ đối với thủy sản nuôi dưới 50% định mức kinh tế kỹ thuật thời gian '
    'nuôi trồng thủy sản.',
    'Điều 6. Giá trị và đơn giá bồi thường đối với chim yến',
    '1. Giá trị bồi thường đối với chim yến được tính bằng tổng sản lượng tổ yến trong một năm.',
    '2. Đơn giá bồi thường đối với chim yến theo giá thị trường nhưng không quá 9.000.000 đồng/kg yến thô.']
DK1, DK2 = 'nuôi dưới 50% định mức KT-KT thời gian nuôi', 'nuôi từ 50% đến 80% định mức KT-KT thời gian nuôi'


class TestLoiVan(CoSo):
    def test_dieu_kien_sau_so_tien(self):
        mong = [(f'Ao nuôi tôm nước lợ - Nuôi quảng canh ({DK1})', 'ha/vụ', 10000000),
                (f'Ao nuôi tôm nước lợ - Nuôi quảng canh ({DK2})', 'ha/vụ', 7000000),
                (f'Ao nuôi tôm nước lợ - Nuôi cua ({DK1})', 'ha/vụ', 9000000),
                (f'Cá nuôi lồng bè ({DK1})', '100m3/vụ', 50000000),
                ('Chim yến (theo giá thị trường, tối đa)', 'kg yến thô', 9000000)]
        ds, _ = ndg.muc_tu_loi_van([[x] for x in DIEU_KIEN], 3)
        self.assertEqual([(m.ten, m.dvt, m.don_gia) for m in ds], mong)
        # PDF: dòng tiêu đề khoản dính với câu ghi giá, câu bị ngắt dòng giữa chừng - cùng kết quả
        pdf = DIEU_KIEN[:3] + ['2. Bồi thường thiệt hại ngừng sản xuất đối với cá nuôi lồng bè Đối với cá nuôi lồng bè là',
                               '50.000.000 đồng/100m3/vụ đối với thủy sản nuôi dưới 50% định mức kinh tế kỹ thuật thời gian',
                               'nuôi trồng thủy sản.'] + DIEU_KIEN[5:]
        ds, _ = ndg.muc_tu_loi_van([[x] for x in pdf], 3)
        self.assertEqual([(m.ten, m.dvt, m.don_gia) for m in ds], mong)
        # áp dụng: vật nuôi ghi phân loại riêng (thẻ "Vật nuôi" trên màn hình Bộ đơn giá)
        ds, _ = ndg.muc_tu_loi_van([[x] for x in DIEU_KIEN], 3)
        ndg.so_khop(ds, 3)
        # "Ao nuôi tôm nước lợ - Nuôi quảng canh (nuôi dưới 50%…)" giống 93% "Ao nuôi tôm nước ngọt - Nuôi thâm canh (nuôi dưới
        # 50%…)" (VN9) chỉ nhờ phần trong ngoặc: không được ghép "gần đúng" (sẽ ghi đè giá mục khác)
        self.assertEqual([(m.trang_thai, m.ma_khop) for m in ds],
                         [('mới', ''), ('mới', ''), ('mới', ''), ('cập nhật', 'VN15'), ('cập nhật', 'VN17')])
        ndg.ap_dung(ds, 3, 'thử', van_ban={'so_hieu': '999/2026/QĐ-UBND', 'trich_yeu': 'Đơn giá bồi thường vật nuôi là thủy sản'})
        con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
        try:
            pl = {r[0] for r in con.execute("SELECT phan_loai FROM dm_taisan WHERE ghi_chu = 'Cập nhật từ thử'")}
            cu = {r[0] for r in con.execute("SELECT phan_loai FROM dm_taisan WHERE ma IN ('VN1', 'VN15')")}
        finally:
            con.close()
        # 15/10/2026: mục mới mang ĐÚNG chuỗi phân loại vật nuôi bộ đơn giá đang dùng (không tách nhóm lạ trên thẻ / bản in)
        self.assertEqual(pl, cu)
        self.assertTrue(next(iter(pl)).startswith(don_gia.PHAN_LOAI_VAT_NUOI))

    def test_tim_theo_so_hieu(self):
        """Gõ số hiệu ("31/2025"): trang văn bản mang đúng số đó được mở dù tiêu đề chung chung (Công báo Đồng Nai trả
        "Quyết định số 31/2025/QĐ-UBND của Ủy ban nhân dân tỉnh") - trước đây 0 kết quả."""
        from unittest import mock
        web = self.td / 'so'
        web.mkdir()
        (web / 'tim.html').write_text('<html><body><a href="ct31.html">Quyết định số 31/2025/QĐ-UBND của Ủy ban nhân dân tỉnh</a>'
                                      '<a href="ct131.html">Quyết định số 131/2025/QĐ-UBND của Ủy ban nhân dân tỉnh</a>'
                                      '</body></html>', encoding='utf-8')
        for so in ('31', '131'):
            (web / f'ct{so}.html').write_text(f'<html><head><title>Quyết định số {so}/2025/QĐ-UBND ban hành đơn giá bồi '
                                              f'thường vật nuôi</title></head><body><a href="tep{so}.docx">Tải tập tin '
                                              f'{so}-2025-qd.doc</a></body></html>', encoding='utf-8')
        sv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(_Im, directory=str(web)))
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        self.addCleanup(sv.server_close)
        self.addCleanup(sv.shutdown)
        mau = f'http://127.0.0.1:{sv.server_address[1]}/tim.html?q={{q}}'
        with mock.patch.dict(cw.NOI_TIM, {'thu': ('Thử', mau)}):
            self.assertEqual([t.so_hieu for t in cw.quet('31/2025', noi='thu')], ['31/2025/QĐ-UBND'])   # không lấy nhầm 131
            self.assertEqual(cw.quet('đơn giá', noi='thu'), [])        # không có số hiệu: tiêu đề chung chung không mở

    def test_don_gia_trong_loi_van(self):
        dong = [[x] for x in LOI_VAN]
        self.assertEqual(ndg.nhan_muc(dong, 3), [])                     # không có bảng
        ds, xem = ndg.muc_tu_loi_van(dong, 3)
        self.assertEqual([(m.ten, m.dvt, m.don_gia) for m in ds], [
            ('Ao nuôi cá - Cá giống', 'm² mặt nước', 30000), ('Ao nuôi cá - Cá thịt nuôi thâm canh', 'm² mặt nước', 45000),
            ('Ao nuôi cá - Cá thịt nuôi quảng canh', 'm² mặt nước', 18000), ('Nuôi tôm - Tôm thẻ chân trắng', 'm²', 60000),
            ('Nuôi tôm - Tôm càng xanh', 'm²', 52000), ('Vật nuôi là thủy sản - Nuôi cá lồng, bè', 'lồng', 1500000),
            ('Vật nuôi là thủy sản - Chi phí di chuyển vật nuôi', 'hộ', 3000000)])
        self.assertTrue(all(m.nhom == 3 and m.nguon_dong for m in ds))
        self.assertEqual(len(xem), 2)                                   # khoảng giá, tỷ lệ %: không tự lấy
        self.assertTrue(xem[0].startswith('Khoảng giá') and 'Ba ba' in xem[0])
        self.assertIn('30%', xem[1])
        self.assertEqual(ndg.muc_tu_loi_van([['Căn cứ Luật Đất đai số 31/2024/QH15;'], ['Điều 1. Phạm vi']], 3), ([], []))

    @unittest.skipUnless(CO_QT, 'không có PySide6')
    def test_hop_nhap_loi_van(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from PySide6.QtCore import Qt
        from pabt.man_hinh_nhap_don_gia import HopNhapDonGia
        dong = [[x] for x in LOI_VAN]
        vb = ndg.phan_tich_van_ban(dong)
        d = HopNhapDonGia('qd31.docx', None, 'QĐ 31/2025', dong=dong, van_ban=vb)
        d.im_lang = True
        self.assertTrue(d.tu_loi_van)
        self.assertTrue(d.da_co)                                        # bộ đơn giá tích hợp đã ghi tên QĐ 31/2025
        # văn bản "đã có" nhưng các mục đều MỚI: vẫn chọn sẵn (trước đây bỏ chọn hết -> không áp dụng được)
        self.assertTrue(all(d.bang.item(i, 0).checkState() == Qt.CheckState.Checked for i in range(d.bang.rowCount())))
        d.bang.item(5, 2).setText('Cá nuôi lồng, bè')                  # sửa tên trước khi áp dụng
        self.assertEqual(d.ds[5].ten, 'Cá nuôi lồng, bè')
        d.accept()
        self.assertEqual((d.ket_qua['so_moi'], d.ket_qua['so_cap_nhat']), (7, 0))
        con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
        try:
            self.assertEqual(con.execute("SELECT dvt, don_gia, nhom FROM dm_taisan WHERE ten = 'Cá nuôi lồng, bè'").fetchone()[:],
                             ('lồng', '1500000', 3))
            self.assertEqual(con.execute("SELECT COUNT(*) FROM van_ban WHERE so_hieu LIKE '%31/2025%'").fetchone()[0], 1)
        finally:
            con.close()
        with self.assertRaises(LoiNhap):                                # không bảng, không câu ghi giá
            HopNhapDonGia('x.docx', None, 'x', dong=[['Điều 1. Phạm vi điều chỉnh']], van_ban={})


if __name__ == '__main__':
    unittest.main()
