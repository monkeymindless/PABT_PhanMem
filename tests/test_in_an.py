"""Kiểm thử giai đoạn 3: bản in theo mẫu IN_CHITIET / IN_BANGTONGHOP (xuất PDF thật khi máy có Microsoft Excel)."""
from __future__ import annotations
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an, nghiep_vu, nhap_excel
from pabt.tien import D
from tests.test_nghiep_vu import FILE_EXCEL


def _o_chu(ws):
    return [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]


def _gop(ws, o):
    """Vùng trộn chứa ô o (hoặc None)."""
    return next((str(m) for m in ws.merged_cells.ranges if o in m), None)


@unittest.skipUnless(FILE_EXCEL.exists(), f'không có file Excel mẫu {FILE_EXCEL}')
class TestBanIn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.td = Path(cls.tmp.name)
        cls.goc = cls.td / 'goc.pabt'
        nhap_excel.nhap(FILE_EXCEL, cls.goc)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.p = self.td / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()

    def test_bang_tong_hop(self):
        # bài này kiểm nội dung / công thức theo vị trí ô (mỗi thửa một dòng): 21/10/2026 chữ cao hơn CAO_KHOI_BTH được chia nhiều dòng
        # Excel (phông offscreen chữ rộng gấp đôi) - tắt chia dòng ở đây; chia dòng kiểm ở tests/test_in_an_2110.py
        from unittest import mock
        with mock.patch.object(in_an, 'CAO_KHOI_BTH', 1e9):
            f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        ws = openpyxl.load_workbook(f).active
        pa1, pa2 = nghiep_vu.doc_phuong_an(self.con, 1), nghiep_vu.doc_phuong_an(self.con, 2)
        so_thua = [self.con.execute('SELECT so_thua FROM thua WHERE ma_thua = ?', (d.ma_thua,)).fetchone()[0]
                   for d in pa1.dat + pa2.dat]
        self.assertEqual([ws.cell(r, 5).value for r in range(13, 17)], so_thua)
        kq1, kq2 = nghiep_vu.tinh_ho(self.con, 1), nghiep_vu.tinh_ho(self.con, 2)
        for c in 'ABCV':                                                # 22/10/2026: STT / họ tên / địa chỉ / tổng gộp dọc theo hộ
            self.assertEqual(_gop(ws, f'{c}13'), f'{c}13:{c}14')
        self.assertEqual(_gop(ws, 'V15'), 'V15:V16')
        self.assertIsNone(_gop(ws, 'P13'))                              # tiền đất từng thửa (cộng lại = tiền đất của hộ)
        self.assertEqual(ws['P13'].value + ws['P14'].value, int(kq1.muc[1]))
        self.assertEqual(ws['V13'].value, int(kq1.tong))
        self.assertEqual(ws['V15'].value, int(kq2.tong))
        bc = nghiep_vu.BoiCanh.tu(self.con)
        self.assertEqual(ws['S13'].value, int(sum(nghiep_vu.thanh_tien_dong(d, bc) for d in pa1.dong_ho_tro('CS9'))))   # đào tạo CS9
        self.assertEqual(ws['T13'].value, int(sum(nghiep_vu.thanh_tien_dong(d, bc) for d in pa1.khoan[4]
                                                  if d.ma in nghiep_vu.MA_ON_DINH)))                 # ổn định đời sống
        self.assertEqual(ws['H13'].value, 0)                            # thửa đầu của hộ 1 ở mục 1 là ODT
        self.assertEqual(D(str(ws['J13'].value)), pa1.dat[0].dien_tich)
        self.assertEqual(ws['A17'].value, 'TỔNG CỘNG')
        self.assertEqual(ws['V17'].value, '=SUM(V13:V16)')
        self.assertEqual(ws['V18'].value, '=ROUND(V17*3.5%, -3)')       # dự án "Xây dựng đường…": theo tuyến 3,5% (QĐ 08/2025)
        self.assertEqual(ws['V19'].value, '=ROUND(V18*85%, -3)')
        self.assertEqual(ws['V21'].value, '=V17+V18')
        chu = ' '.join(_o_chu(ws))
        self.assertIn('UBND phường Trị An 15%', chu)
        self.assertNotIn('{', chu)

    def test_xuat_hang_loat_excel(self):
        kq = in_an.xuat_hang_loat(self.con, [1, 2], self.td / 'loat', bang_tong_hop=True)
        self.assertEqual(len(kq['excel']), 1)                          # 1.0.19+: phương án chi tiết là Word, chỉ bảng tổng hợp là Excel
        self.assertTrue(all(p.exists() for p in kq['excel']))
        self.assertEqual(len(kq['word']), 2)                           # mỗi hộ một bản Word
        self.assertTrue(all(p.exists() for p in kq['word']))
        ho_ten = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0]
        self.assertTrue(kq['word'][0].name.startswith('PA_001_ma1_' + ho_ten), [p.name for p in kq['word']])

    @unittest.skipUnless(sys.platform == 'win32' and os.environ.get('PABT_THU_EXCEL', '1') != '0', 'cần Microsoft Excel (Windows)')
    def test_xuat_pdf_bang_excel_that(self):
        kq = in_an.xuat_hang_loat(self.con, [1], self.td / 'pdf', pdf=True, bang_tong_hop=True)
        self.assertEqual(kq['loi'], [])
        self.assertEqual(len(kq['pdf']), 2)
        for p in kq['pdf']:
            self.assertGreater(p.stat().st_size, 5000)
            self.assertEqual(p.read_bytes()[:4], b'%PDF')


if __name__ == '__main__':
    unittest.main()
