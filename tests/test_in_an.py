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
        # 0.9.21: mục 4 vật nuôi luôn in tiêu đề (hộ không có vật nuôi: tiêu đề trống) trước mục 5 hỗ trợ
        self.assertEqual(''.join(loai[:n]), 'HII' + 'H' + 'I' * 9 + 'H' + 'III' + 'H' + 'H' + 'II' + 'RT')
        tong_r = 18 + n - 1
        self.assertEqual(ws.cell(tong_r, 1).value, 'TỔNG CỘNG')                 # 0.9.88: ô gộp từ cột STT, căn giữa
        pa = nghiep_vu.doc_phuong_an(self.con, 1)
        self.assertEqual(ws.cell(tong_r, 7).value, int(kq.tong))
        self.assertEqual(ws['G18'].value, int(kq.muc[1]))               # dòng mục 1: tổng thành tiền
        self.assertEqual(D(str(ws['D18'].value)), sum(d.dien_tich for d in pa.dat))   # và tổng diện tích
        self.assertEqual(ws['A19'].value, '1.1')
        to, so = self.con.execute('SELECT so_to, so_thua FROM thua WHERE ma_thua = ?', (pa.dat[0].ma_thua,)).fetchone()
        self.assertTrue(ws['B19'].value.startswith(f'Thửa đất số {so}, tờ bản đồ số {to}, '), ws['B19'].value)
        self.assertEqual(ws.cell(tong_r - 1, 7).value, int(kq.muc[5]))  # thưởng
        ho_ten, ten_da = self.con.execute('SELECT ho.ho_ten, du_an.ten FROM ho, du_an WHERE ho.ma_ho = 1').fetchone()
        self.assertEqual(ws['C8'].value, ho_ten)
        self.assertTrue(ws['A5'].value.startswith('DỰ ÁN ' + ten_da))
        self.assertTrue(ws['E3'].value.startswith('Trị An, ngày'))
        self.assertFalse([v for v in _o_chu(ws) if '{' in v])          # không còn chỗ trống chưa điền
        # phần cuối dời xuống đúng chỗ, vùng in và định dạng có điều kiện phủ đủ dòng
        iv = tong_r + 1
        self.assertEqual(ws.cell(iv, 1).value, 'IV')
        self.assertEqual(_gop(ws, f'B{iv}'), f'B{iv}:H{iv}')
        r_cd = next(r for r in range(iv, iv + 12) if str(ws.cell(r, 1).value or '').strip() == 'LẬP BIỂU')   # dòng chức danh
        r_ky = next(r for r in range(r_cd + 1, r_cd + 12) if str(ws.cell(r, 1).value or '').strip())   # họ tên người lập (theo mẫu)
        self.assertEqual(_gop(ws, f'A{r_ky}'), f'A{r_ky}:B{r_ky}')
        self.assertEqual(ws.print_area, f"'IN_CHITIET'!$A$1:$H${r_ky + 1}")
        self.assertIn(f'A18:H{tong_r}', ' '.join(str(cf.sqref) for cf in ws.conditional_formatting))
        self.assertIn(in_an.TEN_CAO, openpyxl.load_workbook(f).defined_names)

    def test_ho_chua_lap_gia_liet_ke_thua(self):
        f = in_an.lap_chi_tiet(self.con, 3, self.td / 'ct3.xlsx', self.mau)
        ws = openpyxl.load_workbook(f).active
        self.assertEqual(ws['A19'].value, '1.1')
        self.assertTrue(ws['B19'].value.startswith('Thửa đất số'))
        # 1.0.04: diện tích > 0 luôn in số lượng (kể cả không có tiền đất)
        dt = sum(D(x) for (x,) in self.con.execute('SELECT dt_thu_hoi FROM thua WHERE ma_ho = 3'))   # hộ chưa lập: liệt kê thửa
        self.assertEqual(D(str(ws['D18'].value)), dt)
        tong_r = next(r for r in range(18, 40) if 'TỔNG CỘNG' in (ws.cell(r, 1).value, ws.cell(r, 2).value))   # 0.9.88: gộp từ cột STT
        self.assertEqual(ws.cell(tong_r, 7).value, 0)
        self.assertIsNone(ws.cell(tong_r - 1, 4).value)                # không có đất: không thưởng -> trống (0.9.69)
        self.assertEqual(ws.cell(tong_r - 1, 7).value, 0)

    def test_ho_nhieu_dong(self):
        bo = BoSoan(self.con, 1)
        m = bo.dm.tim(3, 'xoai')[0]
        for _ in range(150):
            i, _ = bo.them_tu_danh_muc(3, m)
            bo.sua_khoan(3, i, 'so_luong', '1')
        bo.luu()
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'nhieu.xlsx', self.mau)
        ws = openpyxl.load_workbook(f).active
        tong_r = next(r for r in range(18, 400) if 'TỔNG CỘNG' in (ws.cell(r, 1).value, ws.cell(r, 2).value))   # 0.9.88: gộp từ cột STT
        self.assertEqual(tong_r, 18 + 23 + 150 - 1)
        self.assertEqual(ws.cell(tong_r, 7).value, int(nghiep_vu.tinh_ho(self.con, 1).tong))
        self.assertEqual(ws.cell(tong_r + 1, 1).value, 'IV')

    def test_bang_tong_hop(self):
        # bài này kiểm nội dung / công thức theo vị trí ô (mỗi thửa một dòng): 21/10/2026 chữ cao hơn CAO_KHOI_BTH được chia nhiều dòng
        # Excel (phông offscreen chữ rộng gấp đôi) - tắt chia dòng ở đây; chia dòng kiểm ở tests/test_in_an_2110.py
        from unittest import mock
        with mock.patch.object(in_an, 'CAO_KHOI_BTH', 1e9):
            f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx', mau=self.mau)
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
        self.assertEqual(len(kq['excel']), 3)
        self.assertTrue(all(p.exists() for p in kq['excel']))
        ho_ten = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0]
        self.assertTrue(kq['excel'][0].name.startswith('PA_001_ma1_' + ho_ten))

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
