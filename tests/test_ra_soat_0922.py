"""Kiểm thử rà soát 0.9.22: bảng ảo sắp xếp theo giá trị, đếm bộ lọc tiến độ, dò ô bản in không tạo ô rỗng, lưu phương án không đọc
lại CSDL, Dự án mới ghi nhật ký giao dịch trong RAM. Mọi tối ưu phải cho kết quả như cách cũ."""
from __future__ import annotations
import os
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import openpyxl

from pabt import csdl, in_an, nghiep_vu, theo_doi
from pabt.lap_pa import BoSoan
from tests.test_toc_do import _du_an


class CoSo(unittest.TestCase):
    SO_HO = 12

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.p = _du_an(self.td, self.SO_HO)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()


class TestDuAnMoi(CoSo):
    def test_file_tao_xong_dung_che_do_delete_va_nguyen_ven(self):
        # tạo dự án dùng journal_mode = MEMORY (không lưu vào file): mở lại là DELETE, không sót file -journal, CSDL nguyên vẹn
        self.assertFalse(Path(str(self.p) + '-journal').exists())
        self.assertEqual(self.con.execute('PRAGMA journal_mode').fetchone()[0].lower(), 'delete')
        self.assertEqual(self.con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(self.con.execute('SELECT COUNT(DISTINCT ma_ho) FROM ct_dat').fetchone()[0], self.SO_HO)


class TestLuuKhongDocLai(CoSo):
    def test_tong_cu_trong_nhat_ky_dung(self):
        self.con.bo_nho.clear()                                       # không có kết quả dùng chung: tính tổng cũ trên bản lúc mở
        bo = BoSoan(self.con, self.ma[2])
        tong = nghiep_vu.tinh_pa(nghiep_vu.doc_phuong_an(self.con, self.ma[2]), bo.bc).tong
        bo.pa.dat[0].dien_tich = bo.pa.dat[0].dien_tich + 1
        bo.luu()
        ct = self.con.execute("SELECT chi_tiet FROM nhat_ky WHERE viec = 'Lưu phương án hộ' ORDER BY rowid DESC").fetchone()[0]
        from pabt.tien import vn
        self.assertIn(f'tổng {vn(tong)} ->', ct)
        self.assertFalse(bo.co_thay_doi)                              # mo_lai mặc định: đọc lại, không còn "thay đổi"

    def test_khong_mo_lai(self):
        bo = BoSoan(self.con, self.ma[1])
        bo.pa.dat[0].dien_tich = bo.pa.dat[0].dien_tich + 1
        bo.luu(mo_lai=False)
        self.assertEqual(nghiep_vu.doc_phuong_an(self.con, self.ma[1]).dat[0].dien_tich, bo.pa.dat[0].dien_tich)


class TestInKhongTaoORong(CoSo):
    def test_do_cho_trong_khong_them_o(self):
        wb = openpyxl.load_workbook(in_an.file_mau(None, in_an.TEN_CT))
        ws = wb.worksheets[0]
        n = len(ws._cells)
        self.assertIsNotNone(in_an.vi_tri_cho(ws, '{du_an}'))
        in_an.dien_so_ngay(ws, '12', '01/02/2026')
        in_an._thay_cho_trong(ws, {'ho_ten': 'A'})
        in_an.o_tieu_ngu(ws)
        self.assertEqual(len(ws._cells), n)                          # ws.iter_rows cũ tạo ô rỗng cho mọi vị trí trong vùng sheet

    def test_vung_tron_chi_muc_nhu_duyet_het(self):
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        ws = openpyxl.load_workbook(f).worksheets[0]
        cm = in_an._chi_muc_gop(ws)
        for r in range(1, ws.max_row + 1):
            for c in range(1, 26):
                self.assertIs(in_an._vung_tron(ws, r, c, cm), in_an._vung_tron(ws, r, c))


class TestDemLoc(CoSo):
    def test_dem_loc_nhu_hop_loc(self):
        q1 = theo_doi.luu_qd(self.con, None, '1/QĐ-UBND', '01/01/2026', '', '', '')
        q2 = theo_doi.luu_qd(self.con, None, '2/QĐ-UBND', '02/01/2026', '', '', '')
        theo_doi.them_ho_theo_pa(self.con, q1, self.ma[:6])
        theo_doi.them_ho_theo_pa(self.con, q2, self.ma[4:9])
        theo_doi.ghi_chi_tra(self.con, [(q1, m) for m in self.ma[:3]], '05/01/2026', '')
        ds = theo_doi.tong_hop(self.con, tinh_pa=False)
        for qd in (None, set(), {q1}, {q2}, {q1, q2}):
            dem = theo_doi.dem_loc(ds, qd)
            for k, _ in theo_doi.LOC_TIEN_DO:
                self.assertEqual(dem[k], sum(1 for x in ds if theo_doi.hop_loc(x, k, qd)), (k, qd))


class TestBangAo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_sap_xep_theo_gia_tri(self):
        from PySide6.QtCore import Qt
        from pabt.bang_ao import BangAo
        b = BangAo(['Tên', 'Tiền'], can_phai=(1,), sap_xep=True)
        khoa = [['b', Decimal('9000')], ['A', Decimal('10000000')], ['c', None], ['á', Decimal('500')]]
        b.dat_du_lieu([[k[0], str(k[1] or '')] for k in khoa], [1, 2, 3, 4], {(1, 1): dict(dam=True)}, khoa=khoa)
        self.assertEqual([b.ma_dong(r) for r in range(4)], [1, 2, 3, 4])          # chưa bấm tiêu đề: giữ thứ tự gốc
        b.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        self.assertEqual([b.ma_dong(r) for r in range(4)], [2, 1, 4, 3])          # số thật (không theo chữ), ô trống cuối
        self.assertTrue(b.mo_hinh.kieu.get((0, 1), {}).get('dam'))              # kiểu ô đi theo dòng
        b.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.assertEqual([b.ma_dong(r) for r in range(4)], [4, 1, 2, 3])
        b.dat_du_lieu([[k[0], str(k[1] or '')] for k in khoa], [1, 2, 3, 4], khoa=khoa)   # nạp lại: giữ cách sắp đã chọn
        self.assertEqual([b.ma_dong(r) for r in range(4)], [4, 1, 2, 3])
        b.selectRow(1)
        self.assertEqual(b.ma_da_chon(), [1])

    def test_chieu_cao_dong_theo_chu(self):
        from pabt.bang_ao import BangAo
        b = BangAo(['A', 'B'])
        b.setColumnWidth(0, 80)
        b.dat_du_lieu([['ngắn', ''], ['dòng 1\ndòng 2\ndòng 3', ''], ['x' * 200, '']])
        mac_dinh = b.verticalHeader().defaultSectionSize()
        self.assertEqual(b.rowHeight(0), mac_dinh)
        self.assertGreater(b.rowHeight(1), mac_dinh)
        self.assertGreater(b.rowHeight(2), mac_dinh)


if __name__ == '__main__':
    unittest.main()
