"""Kiểm thử quy tắc tính: đơn vị (không cần file Excel) + so khớp với file PABT thật (nếu có)."""
from __future__ import annotations
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import csdl, doi_chieu, nghiep_vu, nhap_excel

BIEU = [('0', '2000000'), ('20000000', '4000000'), ('50000000', '8000000'),
        ('100000000', '12000000'), ('200000000', '16000000'), ('500000000', '20000000')]
# file PABT Excel dùng để so khớp: biến môi trường PABT_EXCEL, hoặc du_lieu/PABT.xlsm trong thư mục phần mềm (hoặc thư mục cha)
_GOC = Path(__file__).resolve().parents[1]
FILE_EXCEL = Path(os.environ.get('PABT_EXCEL') or next(
    (p for p in (_GOC / 'du_lieu' / 'PABT.xlsm', _GOC.parent / 'du_lieu' / 'PABT.xlsm') if p.exists()),
    _GOC / 'du_lieu' / 'PABT.xlsm'))


class TestQuyTac(unittest.TestCase):
    def test_thanh_tien(self):
        self.assertEqual(nghiep_vu.thanh_tien_dat('143.8', 330000, 1, 1), 47454000)
        self.assertEqual(nghiep_vu.thanh_tien_dat('100', 300000, '1.2', '0.5'), 18000000)
        self.assertEqual(nghiep_vu.thanh_tien_khoan('3.8', 576000), 2189000)
        self.assertEqual(nghiep_vu.thanh_tien_khoan('12', 2491232, ''), 29895000)   # tỷ lệ trống = 100%

    def test_bieu_thuong(self):
        self.assertEqual(nghiep_vu.muc_thuong(19999999, BIEU), 2000000)
        self.assertEqual(nghiep_vu.muc_thuong(20000000, BIEU), 4000000)
        self.assertEqual(nghiep_vu.muc_thuong(458130000, BIEU), 16000000)
        self.assertEqual(nghiep_vu.muc_thuong(500000000, BIEU), 20000000)
        self.assertEqual(nghiep_vu.muc_thuong(-1, BIEU), 0)

    def test_on_dinh_doi_song(self):
        # 30 kg x 16.450 đ x 6 tháng x 50% (thu hồi dưới 30%, không di chuyển) = 1.480.500 đ/nhân khẩu
        self.assertEqual(nghiep_vu.don_gia_on_dinh(30, 16450, 6, '0.5'), 1480500)
        self.assertEqual(nghiep_vu.don_gia_on_dinh(30, 16450, 24), 11844000)

    def test_mo_ta_thua(self):
        s = nghiep_vu.mo_ta_thua('3', '12', 'ODT', 'Phường', 'Trị An', 'ONT/VT 2: Đường A,\n đoạn B')
        self.assertEqual(s, 'Thửa đất số 12, tờ bản đồ số 3, loại đất ODT, phường Trị An (Vị trí: ONT/VT 2: Đường A, đoạn B)')
        self.assertEqual(nghiep_vu.mo_ta_thua('35', '10', 'CLN', 'Xã', 'Bàu Hàm', '2'),
                         'Thửa đất số 10, tờ bản đồ số 35, loại đất CLN, xã Bàu Hàm (Vị trí 2)')
        self.assertEqual(nghiep_vu.mo_ta_thua('35', '10', 'CLN', '', '', 'VT1'),
                         'Thửa đất số 10, tờ bản đồ số 35, loại đất CLN, xã (phường) …… (Vị trí 1)')


class TestHoTuTao(unittest.TestCase):
    """Một hộ dựng tay trong file .pabt tạm: thưởng chỉ khi có bồi thường đất, căn cứ tổng mục 1-4."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = csdl.tao_moi(Path(self.tmp.name) / 'thu.pabt')
        c = self.con
        with c, csdl.mo_khoa_danh_muc(c):
            c.executemany('INSERT INTO bieu_thuong VALUES (?,?)', BIEU)
            c.executemany('INSERT INTO tham_so (ma, gia_tri) VALUES (?,?)',
                          [('LAMTRON', '-3'), ('HS_DAOTAO', '1.5'), ('HS_DAOTAO_2', '0.5'), ('HM_CHN', '30000'), ('HM_CLN', '100000')])
        c.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'Hộ thử')")
        c.execute("INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi) VALUES (1, 1, '35', '10', 'CLN', '400')")
        c.execute("INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc) VALUES (2, 1, '35', '11', 'LUC', '100', 'Đất giao khoán, HĐ chưa thanh lý')")
        c.commit()

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_khong_thuong_khi_khong_co_dat(self):
        c = self.con
        c.execute("INSERT INTO ct_khoan (muc, ma_ho, ma, ten, so_luong, don_gia) VALUES (2, 1, 'TS1', 'Nhà', '100', '3000000')")
        k = nghiep_vu.tinh_ho(c, 1)
        self.assertEqual(k.muc[2], 300000000)
        self.assertEqual(k.muc[5], 0)

    def test_thuong_tinh_ca_ho_tro(self):
        c = self.con
        c.execute("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, nhom_dat, dien_tich, gia_bang_gia) VALUES (1, 1, 'CLN', 'Nông nghiệp', '400', '100000')")
        c.execute("INSERT INTO ct_khoan (muc, ma_ho, ma, ten, so_luong, don_gia) VALUES (4, 1, 'CS14', 'Di chuyển', '1', '10000000')")
        k = nghiep_vu.tinh_ho(c, 1)
        # đất 40 tr + hỗ trợ 10 tr = 50 tr -> nấc 50-100 tr = 8 tr (nếu chỉ tính đất thì 4 tr)
        self.assertEqual(k.muc[5], 8000000)
        self.assertEqual(k.tong, 58000000)

    def test_dao_tao_tach_giao_khoan(self):
        c = self.con
        c.execute("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, nhom_dat, dien_tich, gia_bang_gia) VALUES (1, 1, 'CLN', 'Nông nghiệp', '400', '100000')")
        c.execute("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, nhom_dat, dien_tich, gia_bang_gia) VALUES (1, 2, 'LUC', 'Nông nghiệp', '100', '200000')")
        c.execute("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, nhom_dat, dien_tich, gia_bang_gia) VALUES (1, 1, 'ONT', 'Đất ở', '50', '900000')")
        self.assertEqual(nghiep_vu.de_xuat_dao_tao(c, 1, False), (Decimal('400'), 150000))   # chỉ CLN, không tính đất ở
        self.assertEqual(nghiep_vu.de_xuat_dao_tao(c, 1, True), (Decimal('100'), 100000))    # LUC giao khoán x 0,5

    def test_han_muc(self):
        c = self.con
        with c, csdl.mo_khoa_danh_muc(c):
            c.execute("UPDATE tham_so SET gia_tri = '300' WHERE ma = 'HM_CLN'")
        c.execute("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, nhom_dat, dien_tich, gia_bang_gia) VALUES (1, 1, 'CLN', 'Nông nghiệp', '400', '100000')")
        self.assertEqual(nghiep_vu.de_xuat_dao_tao(c, 1, False), (Decimal('300'), 150000))


@unittest.skipUnless(FILE_EXCEL.exists(), f'không có file Excel mẫu {FILE_EXCEL}')
class TestKhopExcel(unittest.TestCase):
    """Nhập file PABT thật và so từng hộ, từng dòng với số liệu Excel đã tính."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pabt = Path(cls.tmp.name) / 'du_an.pabt'
        cls.bc = nhap_excel.nhap(FILE_EXCEL, cls.pabt)
        cls.con = csdl.mo(cls.pabt)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def test_nhap_du(self):
        self.assertEqual(self.bc.loi, [])
        self.assertGreater(self.bc.so_ho, 0)
        n_ho = self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        n_thua = self.con.execute('SELECT COUNT(*) FROM thua').fetchone()[0]
        self.assertEqual((n_ho, n_thua), (self.bc.so_ho, self.bc.so_thua))
        self.assertEqual(self.con.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_tong_tung_ho_khop_excel(self):
        kq = doi_chieu.doi_chieu(self.con, self.bc.tong_excel)
        lech = [(h['ma_ho'], str(h['tong']), h['excel']) for h in kq.ho if h['lech']]
        self.assertEqual(lech, [])
        self.assertEqual([(m, d.stt, str(d.thanh_tien), str(d.thanh_tien_excel)) for m, _, d in kq.dong_lech], [])

    def test_moi_ho_co_so_excel(self):
        thieu = [h for h in (r['ma_ho'] for r in self.con.execute('SELECT ma_ho FROM ho')) if h not in self.bc.tong_excel]
        self.assertEqual(thieu, [], 'THEO_DOI của Excel thiếu hộ (file chưa được Excel tính / lưu?)')


if __name__ == '__main__':
    unittest.main()


@unittest.skipUnless(FILE_EXCEL.exists(), f'không có file Excel mẫu {FILE_EXCEL}')
class TestNhapLoi(unittest.TestCase):
    def test_ma_ho_trung_bi_chan(self):
        import openpyxl
        with tempfile.TemporaryDirectory() as td:
            wb = openpyxl.load_workbook(FILE_EXCEL)
            ws = wb['DB_HO']
            ws.cell(3, 1).value = ws.cell(2, 1).value          # hộ thứ 2 mang trùng mã hộ thứ 1
            # đảo thứ tự hai cột (lệnh nhập phải đọc theo tên tiêu đề)
            for r in range(1, ws.max_row + 1):
                a, b = ws.cell(r, 2).value, ws.cell(r, 6).value
                ws.cell(r, 2).value, ws.cell(r, 6).value = b, a
            p = Path(td) / 'loi.xlsx'
            wb.save(p)
            bc = nhap_excel.nhap(p, Path(td) / 'loi.pabt')
            self.assertTrue(any('trùng' in x for x in bc.loi), bc.loi)
            self.assertFalse((Path(td) / 'loi.pabt').exists())


@unittest.skipUnless(FILE_EXCEL.exists(), f'không có file Excel mẫu {FILE_EXCEL}')
class TestMoLai(unittest.TestCase):
    def test_mo_lai_van_doi_chieu_duoc(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.pabt'
            nhap_excel.nhap(FILE_EXCEL, p)
            con = csdl.mo(p)
            kq = doi_chieu.doi_chieu(con)          # không truyền số Excel: lấy số đã lưu lúc nhập
            self.assertTrue(all(h['co_excel'] for h in kq.ho))
            self.assertTrue(kq.khop_het)
            con.close()
