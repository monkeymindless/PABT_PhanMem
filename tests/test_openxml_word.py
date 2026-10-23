"""Bộ công cụ OpenXML Word (pabt/openxml_word.py): XML hợp lệ, thoát ký tự, chỗ trống {ten} điền một lượt, bảng gộp ô, gói .docx đọc lại
được, mẫu khung dựng được và đọc bằng docx_sang_pdf; Word thật mở được (bỏ qua khi máy không có Word). Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import openxml_word as ox                                              # noqa: E402

W = '{%s}' % ox.W


def _x(than: str):
    return ET.fromstring(f'<w:body xmlns:w="{ox.W}">{than}</w:body>')


class TestOpenXmlWord(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.td = Path(self.tmp.name)

    def test_thoat_ky_tu_va_xuong_dong(self):
        than = ox.doan(ox.chay('A & B <c>\nDòng 2\x07'))
        x = _x(than)                                                                # phân tích được = XML hợp lệ
        chu = ''.join(t.text or '' for t in x.iter(W + 't'))
        self.assertEqual(chu, 'A & B <c>Dòng 2')                                    # ký tự điều khiển bị bỏ
        self.assertEqual(len(list(x.iter(W + 'br'))), 1)

    def test_cho_trong_mot_luot_va_thoat(self):
        than = ox.doan(ox.chay('Tên: {ho_ten} - {dia_chi} - {khong_co}'))
        self.assertEqual(ox.cho_trong(than), ['ho_ten', 'dia_chi', 'khong_co'])
        ra = ox.dien_cho_trong(than, {'ho_ten': 'A {dia_chi} & <B>', 'dia_chi': 'Ấp 1'})
        chu = ''.join(t.text or '' for t in _x(ra).iter(W + 't'))
        self.assertEqual(chu, 'Tên: A {dia_chi} & <B> - Ấp 1 - {khong_co}')       # giá trị chứa {khác} không bị thay tiếp

    def test_bang_gop_o(self):
        cot = [1000, 2000, 3000]
        b = ox.bang([ox.hang([ox.o(ox.doan(ox.chay('a')), 1000, gop_doc='bat_dau'), ox.o(ox.doan(ox.chay('b')), 5000, nhap=2)]),
                     ox.hang([ox.o(ox.doan(), 1000, gop_doc='tiep'), ox.o(ox.doan(ox.chay('c')), 2000), ox.o(ox.doan(ox.chay('d')), 3000)])],
                    cot)
        x = _x(b)
        self.assertEqual([c.get(W + 'w') for c in x.iter(W + 'gridCol')], ['1000', '2000', '3000'])
        self.assertEqual(len(list(x.iter(W + 'tr'))), 2)
        self.assertEqual(next(x.iter(W + 'gridSpan')).get(W + 'val'), '2')
        self.assertEqual(len(list(x.iter(W + 'vMerge'))), 2)

    def test_goi_docx_doc_lai_duoc(self):
        than = ox.doan(ox.chay('Xin chào', dam=True, co=14), can='center') + ox.doan_gach_ho('CHI NHÁNH', 90, 4000)
        f = ox.luu(self.td / 'a.docx', than, ox.sect_pr(le_mm=(15, 10, 10, 10)))
        with zipfile.ZipFile(f) as z:
            self.assertIn('word/document.xml', z.namelist())
            ET.fromstring(z.read('word/document.xml'))
        self.assertEqual(ox.doc_than(f), than)
        self.assertEqual(ox.goi_docx(than), ox.goi_docx(than))                      # byte ổn định
        self.assertFalse(list(self.td.glob('*.tmp')))

    def test_cu_phap_python_3_8(self):
        import ast
        ast.parse(Path(ox.__file__).read_text(encoding='utf-8'), feature_version=(3, 8))

    def test_mau_khung_va_pdf_du_phong(self):
        from pabt import docx_sang_pdf
        than, sect = ox.mau_khung()
        self.assertIn('ho_ten', ox.cho_trong(than))
        f = ox.luu(self.td / 'mau.docx', ox.dien_cho_trong(than, {'ho_ten': 'Nguyễn Văn Thử', 'du_an': 'Dự án thử'}), sect)
        html, trang = docx_sang_pdf.html_tu_docx(f)
        self.assertIn('Nguyễn Văn Thử', html)
        self.assertAlmostEqual(trang['rong_mm'], 210, delta=1)
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        pdf = docx_sang_pdf.xuat_pdf_tu_docx(f, self.td / 'mau.pdf')
        self.assertTrue(pdf.read_bytes().startswith(b'%PDF'))

    def test_ngang_a3(self):
        s = ox.sect_pr(ox.A3, ngang=True, le_mm=(20, 15, 10, 15))
        pg = ET.fromstring(f'<w:r xmlns:w="{ox.W}">{s}</w:r>').find(W + 'sectPr/' + W + 'pgSz')
        self.assertEqual((pg.get(W + 'w'), pg.get(W + 'h'), pg.get(W + 'orient')), ('23811', '16838', 'landscape'))
        self.assertEqual(ox.rong_vung(ox.A3, True, (20, 10 + 5, 10, 15)), 23811 - ox.twip(20) - ox.twip(10))


@unittest.skipUnless(os.name == 'nt' and os.environ.get('PABT_THU_WORD') != '0', 'cần Microsoft Word')
class TestWordMoDuoc(unittest.TestCase):
    def test_word_that_mo_va_xuat_pdf(self):
        from pabt import van_ban_trinh as vb
        from tests.test_van_ban_trinh import _co_word
        if not _co_word():
            self.skipTest('máy không có Word')
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            than, sect = ox.mau_khung()
            f = ox.luu(td / 'mau.docx', ox.dien_cho_trong(than, {'ho_ten': 'Nguyễn Văn Thử'}), sect)
            self.assertEqual(vb.chay_word([('pdf', f, f.with_suffix('.pdf'))], cho_moi_file=120), [])
            self.assertTrue(f.with_suffix('.pdf').read_bytes().startswith(b'%PDF'))


if __name__ == '__main__':
    unittest.main()
