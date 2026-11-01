"""Đường kẻ khung bảng + gạch dưới chữ trên máy khác (WPS / nét 0,5 pt / viền không màu).

Số liệu GIẢ LẬP. 1.0.45: viền từng ô Word 1 pt màu đen; Excel viền RGB + DrawingML 1 pt."""
from __future__ import annotations

import os
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, in_an, in_duong_ke, in_word, openxml_word as ox  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


def _xml(p: Path, ten: str) -> str:
    with zipfile.ZipFile(p) as z:
        return z.read(ten).decode('utf-8')


class TestDuongKeMayKhac(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else
                        os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        self.con = csdl.mo(_du_an(self.td, 2))
        self.addCleanup(self.con.close)
        with self.con:
            self.con.execute(
                "UPDATE du_an SET ten=?, don_vi_cap_tren=?, don_vi_tieu_de=?, don_vi_lap=? WHERE id=1",
                ('Đường mẫu', 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT', 'THÀNH PHỐ ĐỒNG NAI', 'CHI NHÁNH QUỸ ĐẤT'))

    def test_hang_so_vien_word(self):
        self.assertEqual(ox.SZ_VIEN, 8)
        self.assertEqual(ox.MAU_VIEN, '000000')
        self.assertIn('w:sz="8"', ox.xml_tbl_borders())
        self.assertIn('w:color="000000"', ox.xml_tc_borders())
        self.assertIn('w:sz="8"', ox.xml_p_bdr_duoi())

    def test_chi_tiet_word_vien_o_va_gach_duoi(self):
        ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        f = in_word.xuat_chi_tiet_docx(self.con, ma, self.td / 'ct.docx')
        doc = _xml(f, 'word/document.xml')
        self.assertGreaterEqual(doc.count('<w:tblBorders>'), 1)
        self.assertGreaterEqual(doc.count('<w:tcBorders>'), 30)          # từng ô — WPS không dựa tblBorders
        self.assertGreaterEqual(doc.count('<w:pBdr>'), 2)
        self.assertIn('w:sz="8"', doc)
        self.assertIn('w:color="000000"', doc)
        self.assertTrue(any('w:sz="8"' in doc[i:j] for i, j in
                            ((m.start(), doc.find('</w:tblBorders>', m.start()))
                             for m in re.finditer(r'<w:tblBorders>', doc))))

    def test_bang_tong_hop_vien_den_va_drawing(self):
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        neo = in_duong_ke.doc_duong_ke(f)
        self.assertGreaterEqual(len(re.findall(r'<xdr:twoCellAnchor', neo)), 2)
        self.assertIn('w="12700"', neo)                                  # 1 pt
        styles = _xml(f, 'xl/styles.xml')
        self.assertGreaterEqual(styles.count('rgb="FF000000"') + styles.count('rgb="000000"'), 8)
        self.assertGreaterEqual(len(re.findall(r'<left style=', styles)), 10)


if __name__ == '__main__':
    unittest.main()
