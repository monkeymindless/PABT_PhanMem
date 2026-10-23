"""1.0.19 (Đợt 1 - an toàn dữ liệu in): file Excel xuất ra không chứa công thức do dữ liệu người dùng gõ ("=HYPERLINK(...)"), chữ
{trường} nằm TRONG dữ liệu không bị thay tiếp, mọi file Excel xuất ra đi qua một cổng lưu (an_toan.luu_xlsx)."""
from __future__ import annotations
import re
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import an_toan, csdl, doi_chieu, in_an, theo_doi
from tests.test_toc_do import _du_an

DOC = '=HYPERLINK("http://x.example/","Bấm vào đây")'
DOC2 = "=cmd|' /C calc'!A0"


def cong_thuc_la(file) -> list:
    """Công thức KHÔNG an toàn còn trong file .xlsx đã lưu (đọc lại bằng openpyxl)."""
    wb = openpyxl.load_workbook(file)
    ra = []
    for ws in wb.worksheets:
        for c in ws._cells.values():
            if c.data_type == 'f' and not an_toan.la_cong_thuc_an_toan(c.value):
                ra.append((ws.title, c.coordinate, str(c.value)[:50]))
    return ra


class TestKhuCongThuc(unittest.TestCase):
    def test_cong_thuc_phan_mem_tu_ghi_van_con(self):
        for s in ('=SUM(G6:G99)', '=ROUND(V10*2.5%, 0)', '=ROUND(V10*3,5%, 0)', '=SUM($A$1:$A$9)', '=A1', '=1+1'):    # phép tính / tham chiếu thuần: vô hại
            self.assertTrue(an_toan.la_cong_thuc_an_toan(s), s)

    def test_cong_thuc_la_bi_chan(self):
        for s in (DOC, DOC2, '=WEBSERVICE("http://x")', '=SUM(A1:A3)&"x"', "=SUM('Sheet 2'!A1)", '=IF(A1>0,1,2)',
                  '=SUM(A1:A3);1', '=' + 'A1+' * 100, '@SUM(A1)', 'SUM(A1)'):
            self.assertFalse(an_toan.la_cong_thuc_an_toan(s), s)

    def test_luu_xlsx_ep_thanh_chu(self):
        with tempfile.TemporaryDirectory() as td:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws['A1'] = DOC
            ws['A2'] = '=SUM(B1:B3)'
            ws['A3'] = 'Nguyễn Văn A'
            self.assertEqual(an_toan.luu_xlsx(wb, Path(td) / 'a.xlsx'), 1)
            doc = openpyxl.load_workbook(Path(td) / 'a.xlsx').active
            self.assertEqual((doc['A1'].data_type, doc['A1'].value), ('s', DOC))        # còn nguyên chữ, không là công thức
            self.assertEqual((doc['A2'].data_type, doc['A2'].value), ('f', '=SUM(B1:B3)'))
            self.assertTrue(doc['A1'].quotePrefix)


class TestXuatDuLieuDoc(unittest.TestCase):
    """Họ tên / địa chỉ / ghi chú độc đi qua mọi đường xuất: không ra ô công thức nào."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.p = _du_an(self.t, 4)
        self.con = csdl.mo(self.p)
        with self.con:
            self.con.execute('UPDATE ho SET ho_ten = ?, dia_chi = ?, ghi_chu = ? WHERE ma_ho = (SELECT MIN(ma_ho) FROM ho)',
                             (DOC, DOC2, '{ho_ten} =SUM(1)'))
            self.con.execute('UPDATE thua SET nguon_goc = ? WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua)', (DOC,))

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_bang_tong_hop(self):
        self.assertEqual(cong_thuc_la(in_an.lap_bang_tong_hop(self.con, self.t / 'b.xlsx')), [])

    def test_chi_tiet_excel_du_phong(self):
        ma = self.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        self.assertEqual(cong_thuc_la(in_an.lap_chi_tiet(self.con, ma, self.t / 'c.xlsx')), [])

    def test_doi_chieu(self):
        kq = doi_chieu.doi_chieu(self.con)
        doi_chieu.xuat_bao_cao(kq, self.t / 'dc.xlsx', ten_du_an=DOC)
        self.assertEqual(cong_thuc_la(self.t / 'dc.xlsx'), [])

    def test_xuat_excel_theo_doi(self):
        theo_doi.xuat_excel(self.t / 'td.xlsx', DOC, [DOC, DOC2], [[DOC, DOC2], ['x', '=1+1']])
        self.assertEqual(cong_thuc_la(self.t / 'td.xlsx'), [])

    def test_cho_trong_khong_thay_tiep(self):
        """Giá trị chứa {truong} của trường khác không bị thay ở lượt sau."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'] = 'Họ tên: {ho_ten} - Địa chỉ: {dia_chi}'
        in_an._thay_cho_trong(ws, {'ho_ten': 'A {dia_chi}', 'dia_chi': 'Ấp 1'})
        self.assertEqual(ws['A1'].value, 'Họ tên: A {dia_chi} - Địa chỉ: Ấp 1')


class TestMotCongLuu(unittest.TestCase):
    """Không nơi nào xuất file Excel cho người dùng bằng wb.save trực tiếp (chỉ cho phép các nơi xử lý MẪU in)."""

    # nơi lưu lại chính file MẪU (không có chữ người dùng gõ): ap_chuan_trang_mau / tao_mau_tu_excel trong in_an, tờ trình xlsx
    CHO_PHEP = {'in_an.py': 3, 'an_toan.py': 1}

    def test_khong_wb_save_truc_tiep(self):
        goc = Path(__file__).resolve().parent.parent / 'pabt'
        loi = []
        for f in sorted(goc.glob('*.py')):
            so = len(re.findall(r'\bwb\.save\(', f.read_text(encoding='utf-8')))
            if so > self.CHO_PHEP.get(f.name, 0):
                loi.append((f.name, so))
        self.assertEqual(loi, [], 'xuất Excel phải đi qua an_toan.luu_xlsx')


if __name__ == '__main__':
    unittest.main()
