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
from pabt.lap_pa import BoSoan
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
        cls.mau = cls.td / 'mau_in'
        in_an.tao_mau_tu_excel(FILE_EXCEL, cls.mau)
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

    def test_mau_tach_tu_excel(self):
        ws = openpyxl.load_workbook(self.mau / 'IN_CHITIET.xlsx').active
        self.assertEqual(ws['A17'].value, 'STT')
        self.assertEqual(ws['A19'].value, 'IV')                       # khung bảng còn 1 dòng mẫu
        self.assertEqual(ws['C8'].value, '{ho_ten}')
        self.assertEqual(ws.page_setup.orientation, 'portrait')
        self.assertFalse(any(str(v).startswith('=') for v in _o_chu(ws)))
        ws2 = openpyxl.load_workbook(self.mau / 'IN_BANGTONGHOP.xlsx').active
        self.assertEqual(ws2['A14'].value, 'TỔNG CỘNG')
        self.assertEqual(ws2.page_setup.orientation, 'landscape')
        self.assertIn('{ten_dia_ban}', ' '.join(_o_chu(ws2)))

    def test_chi_tiet_ho_1(self):
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'ct1.xlsx', self.mau)
        ws = openpyxl.load_workbook(f).active
        kq = nghiep_vu.tinh_ho(self.con, 1)
        loai = [ws.cell(r, in_an.COT_KIND).value for r in range(18, 60)]
        n = loai.index(None)
        self.assertEqual(''.join(loai[:n]), 'HII' + 'H' + 'I' * 9 + 'H' + 'III' + 'H' + 'II' + 'RT')
        tong_r = 18 + n - 1
        self.assertEqual(ws.cell(tong_r, 2).value, 'TỔNG CỘNG')
        self.assertEqual(ws.cell(tong_r, 7).value, 812506000)
        self.assertEqual(ws['G18'].value, 153108000)                    # dòng mục 1: tổng thành tiền
        self.assertEqual(ws['D18'].value, 625.7)                        # và tổng diện tích
        self.assertEqual(ws['A19'].value, '1.1')
        self.assertTrue(ws['B19'].value.startswith('Thửa đất số 394, tờ bản đồ số 35, loại đất ODT, phường Trị An'), ws['B19'].value)
        self.assertEqual(ws.cell(tong_r - 1, 7).value, int(kq.muc[5]))  # thưởng
        self.assertEqual(ws['C8'].value, 'Nguyễn Văn Tiệp')
        self.assertTrue(ws['A5'].value.startswith('Dự án: Xây dựng đường Quang Trung'))
        self.assertTrue(ws['E3'].value.startswith('Trị An, ngày'))
        self.assertFalse([v for v in _o_chu(ws) if '{' in v])          # không còn chỗ trống chưa điền
        # phần cuối dời xuống đúng chỗ, vùng in và định dạng có điều kiện phủ đủ dòng
        iv = tong_r + 1
        self.assertEqual(ws.cell(iv, 1).value, 'IV')
        self.assertEqual(_gop(ws, f'B{iv}'), f'B{iv}:H{iv}')
        r_ky = next(r for r in range(iv, iv + 12) if ws.cell(r, 1).value == 'Phan Tuấn Vĩnh')
        self.assertEqual(_gop(ws, f'A{r_ky}'), f'A{r_ky}:B{r_ky}')
        self.assertEqual(ws.print_area, f"'IN_CHITIET'!$A$1:$H${r_ky + 1}")
        self.assertIn(f'A18:H{tong_r}', ' '.join(str(cf.sqref) for cf in ws.conditional_formatting))
        self.assertIn(in_an.TEN_CAO, openpyxl.load_workbook(f).defined_names)

    def test_ho_chua_lap_gia_liet_ke_thua(self):
        f = in_an.lap_chi_tiet(self.con, 3, self.td / 'ct3.xlsx', self.mau)
        ws = openpyxl.load_workbook(f).active
        self.assertEqual(ws['A19'].value, '1.1')
        self.assertTrue(ws['B19'].value.startswith('Thửa đất số'))
        self.assertEqual(ws['D18'].value, 186.5)
        tong_r = next(r for r in range(18, 40) if ws.cell(r, 2).value == 'TỔNG CỘNG')
        self.assertEqual(ws.cell(tong_r, 7).value, 0)
        self.assertEqual(ws.cell(tong_r - 1, 4).value, 0)               # không có đất: không thưởng

    def test_ho_nhieu_dong(self):
        bo = BoSoan(self.con, 1)
        m = bo.dm.tim(3, 'xoai')[0]
        for _ in range(150):
            i, _ = bo.them_tu_danh_muc(3, m)
            bo.sua_khoan(3, i, 'so_luong', '1')
        bo.luu()
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'nhieu.xlsx', self.mau)
        ws = openpyxl.load_workbook(f).active
        tong_r = next(r for r in range(18, 400) if ws.cell(r, 2).value == 'TỔNG CỘNG')
        self.assertEqual(tong_r, 18 + 22 + 150 - 1)
        self.assertEqual(ws.cell(tong_r, 7).value, int(nghiep_vu.tinh_ho(self.con, 1).tong))
        self.assertEqual(ws.cell(tong_r + 1, 1).value, 'IV')

    def test_bang_tong_hop(self):
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx', mau=self.mau)
        ws = openpyxl.load_workbook(f).active
        self.assertEqual([ws.cell(r, 5).value for r in range(13, 17)], ['394', '80', '395', '396'])
        self.assertEqual(_gop(ws, 'A13'), 'A13:A14')
        self.assertEqual(_gop(ws, 'V15'), 'V15:V16')
        self.assertEqual(ws['P13'].value, 153108000)
        self.assertEqual(ws['V13'].value, 812506000)
        self.assertEqual(ws['V15'].value, 474130000)
        self.assertEqual(ws['S13'].value, 36954000)                     # đào tạo HT09
        self.assertEqual(ws['T13'].value, 7403000)                      # ổn định đời sống
        self.assertEqual(ws['H13'].value, 0)                            # thửa 394 ở mục 1 là ODT
        self.assertEqual(ws['J13'].value, 215.1)
        self.assertEqual(ws['A17'].value, 'TỔNG CỘNG')
        self.assertEqual(ws['V17'].value, '=SUM(V13:V16)')
        self.assertEqual(ws['V18'].value, '=ROUND(V17*2.5%, -3)')
        self.assertEqual(ws['V19'].value, '=ROUND(V18*85%, -3)')
        self.assertEqual(ws['V21'].value, '=V17+V18')
        chu = ' '.join(_o_chu(ws))
        self.assertIn('UBND phường Trị An 15%', chu)
        self.assertNotIn('{', chu)

    def test_xuat_hang_loat_excel(self):
        kq = in_an.xuat_hang_loat(self.con, [1, 2], self.td / 'loat', bang_tong_hop=True)
        self.assertEqual(len(kq['excel']), 3)
        self.assertTrue(all(p.exists() for p in kq['excel']))
        self.assertTrue(kq['excel'][0].name.startswith('PA_001_ma1_Nguyễn Văn Tiệp'))

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
