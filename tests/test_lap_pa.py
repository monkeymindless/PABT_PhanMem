"""Kiểm thử giai đoạn 2: lập / sửa phương án trong phần mềm (không cần cửa sổ)."""
from __future__ import annotations
import shutil
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import csdl, doi_chieu, lap_pa, nghiep_vu, nhap_excel
from pabt.lap_pa import BoSoan, DanhMuc, LoiNhap
from pabt.tien import D, vn
from tests.test_nghiep_vu import FILE_EXCEL


@unittest.skipUnless(FILE_EXCEL.exists(), f'không có file Excel mẫu {FILE_EXCEL}')
class TestLapPA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.goc = Path(cls.tmp.name) / 'goc.pabt'
        bc = nhap_excel.nhap(FILE_EXCEL, cls.goc)
        assert not bc.loi, bc.loi

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.p = Path(self.tmp.name) / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)
        self.con = csdl.mo(self.p)
        self.dm = DanhMuc(self.con)

    def tearDown(self):
        self.con.close()

    # ------------------------------------------------------------ lưu lại không đổi số liệu
    def test_luu_lai_ca_116_ho_khong_doi_tong(self):
        truoc = {k.ma_ho: (k.tong, dict(k.muc)) for k in nghiep_vu.tinh_tat_ca(self.con)}
        bo = BoSoan(self.con, 1, self.dm)
        for ma in list(truoc):
            bo.mo(ma)
            self.assertFalse(bo.co_thay_doi)
            bo.luu()
        sau = {k.ma_ho: (k.tong, dict(k.muc)) for k in nghiep_vu.tinh_tat_ca(self.con)}
        self.assertEqual(truoc, sau)
        kq = doi_chieu.doi_chieu(self.con)
        self.assertEqual(kq.dong_lech, [])          # dòng không sửa vẫn giữ thành tiền Excel và khớp
        self.assertEqual(kq.so_ho_sua, 116)
        self.assertTrue(kq.khop_het)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM nhat_ky WHERE viec = 'Lưu phương án hộ'").fetchone()[0], 116)

    def test_co_thay_doi_va_hoan_tac(self):
        bo = BoSoan(self.con, 1, self.dm)
        bo.sua_khoan(2, 0, 'so_luong', '130')
        self.assertTrue(bo.co_thay_doi)
        bo.mo(1)                                     # bỏ thay đổi
        self.assertFalse(bo.co_thay_doi)
        self.assertEqual(bo.pa.khoan[2][0].so_luong, D('124.7'))

    # ------------------------------------------------------------ gợi ý hỗ trợ
    def test_goi_y_sua_ht09_ho_1(self):
        bo = BoSoan(self.con, 1, self.dm)
        dx, _ = bo.goi_y()
        ht09 = [x for x in dx if x.ma == 'CS9']
        self.assertEqual(len(ht09), 1)
        self.assertEqual((ht09[0].viec, ht09[0].so_luong, ht09[0].don_gia), ('sửa', D('410.6'), 135000))
        tong_cu = bo.ket_qua.tong
        bo.ap_dung_goi_y(ht09)
        d = bo.pa.dong_ho_tro('CS9')[0]
        self.assertEqual((d.so_luong, d.don_gia), (D('410.6'), 135000))
        self.assertEqual(bo.ket_qua.muc[4], D('44357000') - D('36954000') + D('55431000'))
        self.assertGreater(bo.ket_qua.tong, tong_cu)
        self.assertFalse(any(x.startswith('CS9') for x in bo.canh_bao))
        bo.luu()
        kq = doi_chieu.doi_chieu(self.con)
        self.assertTrue(kq.khop_het)                 # hộ 1 đã sửa trong phần mềm: không tính là lệch
        self.assertEqual(kq.so_ho_sua, 1)
        h1 = next(h for h in kq.ho if h['ma_ho'] == 1)
        self.assertEqual(h1['tong'], nghiep_vu.tinh_ho(self.con, 1).tong)

    def test_goi_y_on_dinh_doi_song_va_di_chuyen(self):
        bo = BoSoan(self.con, 2, self.dm)
        bo.dat_nhan_khau('6')                        # dòng ổn định đời sống tự cập nhật số lượng = số nhân khẩu
        self.assertEqual(bo.pa.dong_ho_tro('CS1')[0].so_luong, 6)
        bo.dat_dt_nn_dang_dung('1.000')              # thu hồi 123,2 / 1000 = 12,3% < 30%
        dx, _ = bo.goi_y()
        od = [x for x in dx if x.ma in nghiep_vu.MA_ON_DINH]
        self.assertEqual(od, [])
        bo.dat_phai_di_chuyen(True)
        dx, tu = bo.goi_y()
        self.assertIn(('CS2', 'thay'), [(x.ma, x.viec) for x in dx])
        self.assertIn('CS14', [x.ma for x in dx])
        self.assertTrue(any('CS17' in t for t in tu))
        bo.ap_dung_goi_y([x for x in dx if x.ma in ('CS2', 'CS14')])
        ma = [d.ma for d in bo.pa.khoan[4]]
        self.assertIn('CS2', ma)
        self.assertNotIn('CS1', ma)
        ht02 = bo.pa.dong_ho_tro('CS2')[0]
        # theo cách tính: 6 nhân khẩu × (30 kg × 12 tháng × 16.450 đ) × 50% = 6 × 2.961.000
        self.assertEqual((ht02.so_luong, ht02.don_gia, ht02.ty_le), (6, 5922000, D('0.5')))
        self.assertEqual(ht02.ten, 'Hỗ trợ ổn định đời sống')
        self.assertEqual(ht02.cach_tinh, '6 nhân khẩu x 30kg gạo x 12 tháng x 16.450 đồng x 50%')
        self.assertEqual(nghiep_vu.thanh_tien_dong(ht02, bo.bc), D('17766000'))
        ht14 = bo.pa.dong_ho_tro('CS14')[0]
        self.assertEqual((ht14.so_luong, ht14.don_gia), (1, 10000000))
        bo.luu()
        h = self.con.execute('SELECT nhan_khau, phai_di_chuyen, dt_nn_dang_dung FROM ho WHERE ma_ho = 2').fetchone()
        self.assertEqual(tuple(h), (6, 1, '1000'))

    def test_them_khoan_ho_tro_tu_goi_y(self):
        bo = BoSoan(self.con, 2, self.dm)                   # phường Trị An: dùng mã phường
        bo.dat_nhan_khau('7')
        i, tb = bo.them_tu_danh_muc(4, self.dm.lay('CS18'))
        d = bo.pa.khoan[4][i]
        # một dòng: 6 tháng × (8.000.000 mức hộ đến 4 khẩu + (7 - 4) × 2.000.000) = 84.000.000
        self.assertEqual((d.so_luong, d.don_gia), (6, 14000000))
        self.assertEqual(d.cach_tinh, '(1 hộ (4 nhân khẩu) * 6 tháng * 8.000.000 đồng) + '
                                      '(3 nhân khẩu tăng thêm * 2.000.000 đồng * 6 tháng)')
        self.assertEqual(d.ten, 'Hỗ trợ tự lo chỗ ở')
        dx, _ = bo.goi_y()
        self.assertFalse([x for x in dx if x.ma in ('CS18', 'CS22')])
        bo.dat_nhan_khau('4')                                    # đổi nhân khẩu: đơn giá tháng tính lại
        self.assertEqual(d.don_gia, 8000000)
        with self.assertRaises(LoiNhap):                         # tái định cư: chọn ở ô Tái định cư, không thêm dòng tiền
            bo.them_tu_danh_muc(4, self.dm.lay('CS11'))
        bo.dat_tai_dinh_cu(lap_pa.TAI_DINH_CU[1])
        self.assertTrue(bo.co_thay_doi)
        i, tb = bo.them_tu_danh_muc(4, self.dm.lay('CS10'))
        self.assertIn('giao khoán', tb)                     # chưa có thửa giao khoán
        i, tb = bo.them_tu_danh_muc(4, self.dm.lay('CS31'))
        self.assertIn('báo giá', tb)

    # ------------------------------------------------------------ hạng mục ngoài danh mục
    def test_hang_muc_khac_ap_gia_tuong_duong(self):
        bo = BoSoan(self.con, 1, self.dm)
        i = bo.them_hang_muc_khac(2, '  Mái che khung sắt   lợp tôn ')
        ds = self.dm.tim(2, 'mai che')
        self.assertTrue(ds and 'mái che' in ds[0].ten.lower())
        bo.ap_gia_tuong_duong(2, i, ds[0])
        bo.sua_khoan(2, i, 'so_luong', '12,5')
        d = bo.pa.khoan[2][i]
        self.assertEqual(d.ten, 'Mái che khung sắt lợp tôn')
        self.assertEqual((d.nguon_gia, d.ma_tuong_duong, d.don_gia), ('tương đương', ds[0].ma, ds[0].don_gia))
        self.assertIn('Áp giá tương đương', d.can_cu_gia)
        bo.luu()
        bo2 = BoSoan(self.con, 1, self.dm)
        d2 = bo2.pa.khoan[2][-1]
        self.assertEqual((d2.ten, d2.nguon_gia, d2.ma_tuong_duong, d2.so_luong), (d.ten, 'tương đương', ds[0].ma, D('12.5')))
        rs = lap_pa.ra_soat_gia(self.con, self.dm)
        self.assertTrue(any(x['ten'] == d.ten and x['nguon'] == 'tương đương' for x in rs))

    def test_nhap_tay_can_can_cu(self):
        bo = BoSoan(self.con, 1, self.dm)
        i = bo.them_hang_muc_khac(3, 'Cây cóc ăn quả (5 năm)')
        bo.sua_khoan(3, i, 'so_luong', '3')
        bo.sua_khoan(3, i, 'don_gia', '150.000')
        self.assertTrue(any('chưa ghi căn cứ' in x for x in bo.canh_bao))
        bo.sua_khoan(3, i, 'can_cu_gia', 'Chứng thư thẩm định giá số 12/2026')
        self.assertFalse(any('chưa ghi căn cứ' in x for x in bo.canh_bao))
        self.assertEqual(bo.ket_qua.muc[3], D('52210000') + D('450000'))

    def test_don_gia_danh_muc_sua_tay(self):
        bo = BoSoan(self.con, 1, self.dm)
        d = bo.pa.khoan[2][0]
        cu, ma = d.don_gia, d.ma
        bo.sua_khoan(2, 0, 'don_gia', vn(cu))              # gõ lại đúng giá: vẫn là dòng danh mục
        self.assertEqual((d.nguon_gia, d.ma), ('danh mục', ma))
        tb = bo.sua_khoan(2, 0, 'don_gia', '3.100.000')    # giá thực tế khác: dòng nhập tay, ghi giá danh mục để rà soát
        self.assertIn('nhập tay', tb)
        self.assertEqual((d.don_gia, d.nguon_gia, d.ma, d.ma_tuong_duong), (3100000, 'nhập tay', '', ma))
        self.assertIn(vn(cu), d.can_cu_gia)
        bo.sua_khoan(2, 0, 'so_luong', '5')                 # số lượng (dữ liệu nhập) vẫn sửa được
        with self.assertRaises(sqlite3.IntegrityError):
            with self.con:
                self.con.execute("UPDATE dm_taisan SET don_gia = '1' WHERE ma = ?", (ma,))

    def test_doi_ten_tai_san_giu_don_gia(self):
        bo = BoSoan(self.con, 1, self.dm)
        d = bo.pa.khoan[2][0]
        ma, gia = d.ma, d.don_gia
        tb = bo.sua_khoan(2, 0, 'ten', 'Mái che khung thép lợp tôn (không có trong đơn giá)')
        self.assertIn('giá tương đương', tb)
        self.assertEqual((d.ten, d.ma, d.ma_tuong_duong, d.nguon_gia, d.don_gia),
                         ('Mái che khung thép lợp tôn (không có trong đơn giá)', '', ma, 'tương đương', gia))
        self.assertIn(ma, d.can_cu_gia)
        bo.sua_khoan(2, 0, 'ten', 'Mái che tôn')             # đổi tên tiếp: vẫn giữ giá
        self.assertEqual((d.ten, d.don_gia, d.ma_tuong_duong), ('Mái che tôn', gia, ma))
        bo.luu()
        self.assertTrue(any(x['ten'] == 'Mái che tôn' for x in lap_pa.ra_soat_gia(self.con, self.dm)))

    def test_quy_uoc_tuong_duong(self):
        # 16/10/2026: nhập Excel không còn chép sheet quy ước mẫu - dự án không có quy ước nào; người dùng tự thêm (Đơn giá đặc biệt)
        from pabt import don_gia_rieng
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM quy_uoc').fetchone()[0], 0)
        don_gia_rieng.luu(self.con, [dict(id=None, ten_thuc_te='Gác lửng khung sắt ván ép',
                                          ten_tuong_duong='Gác để ở của nhà chính (Nhà bán kiên cố)', dvt='m²', don_gia='1854000',
                                          can_cu='Áp giá tương đương theo Nhà bán kiên cố (TS17)')])
        self.dm = DanhMuc(self.con)
        bo = BoSoan(self.con, 1, self.dm)
        i = bo.them_hang_muc_khac(2, 'Gác lửng khung sắt ván ép')
        qu = self.dm.tim(9, 'gac lung')
        self.assertTrue(qu)
        bo.ap_gia_tuong_duong(2, i, qu[0])
        d = bo.pa.khoan[2][i]
        self.assertEqual((d.nguon_gia, d.don_gia), ('tương đương', D('1854000')))
        self.assertIn('Nhà bán kiên cố', d.can_cu_gia)

    # ------------------------------------------------------------ mục 1
    def test_muc_1_them_thua_va_gia(self):
        bo = BoSoan(self.con, 1, self.dm)
        self.assertEqual(lap_pa.tra_gia_dat(self.con, bo.bc, 'CLN', '1')[:2], (D('90000'), D(1)))
        bo.xoa(1, 1)                                         # bỏ dòng CLN thửa 80 rồi thêm lại từ hồ sơ kiểm kê
        mt = next(x[0] for x in bo.thua_cua_ho() if '80' in x[1])
        i, tb = bo.them_thua(mt)
        d = bo.pa.dat[i]
        self.assertEqual((d.loai_dat, d.nhom_dat, d.dien_tich), ('CLN', 'Nông nghiệp', D('410.6')))
        self.assertEqual(d.gia_bang_gia, 0)                  # kiểm kê chưa ghi vị trí: chưa tra được giá
        bo.sua_dat(i, 'vi_tri', '1')
        self.assertEqual(d.gia_bang_gia, 90000)
        self.assertEqual(bo.ket_qua.muc[1], D('153108000'))
        with self.assertRaises(LoiNhap):
            bo.sua_dat(i, 'loai_dat', 'XYZ')
        with self.assertRaises(LoiNhap):
            bo.sua_dat(i, 'ty_le', '600')                # tỷ lệ được vượt 100% (đào tạo 150%) nhưng tối đa 500%
        bo.sua_dat(i, 'ty_le', '70%')
        self.assertEqual(d.ty_le, D('0.7'))

    def test_loi_chan_luu_khong_ghi_gi(self):
        bo = BoSoan(self.con, 1, self.dm)
        mt = next(x[0] for x in bo.thua_cua_ho() if '394' in x[1])
        bo.them_thua(mt)                                     # thửa 394 đã đưa hết DT vào mục 1 -> DT còn 0
        bo.pa.dat[-1].dien_tich = D('-1')                    # 0.9.21: DT 0 cho lưu (tài sản trên đất người khác), âm thì chặn
        bo.sua_khoan(2, 0, 'so_luong', '1')
        with self.assertRaises(LoiNhap) as e:
            bo.luu()
        self.assertIn('diện tích', str(e.exception))
        self.assertEqual(self.con.execute('SELECT so_luong FROM ct_khoan WHERE id = 5').fetchone()[0], '124.7')
        with self.assertRaises(LoiNhap):
            bo.sua_khoan(2, 0, 'so_luong', 'abc')
        with self.assertRaises(LoiNhap):
            bo.sua_khoan(2, 0, 'so_luong', '-1')
        with self.assertRaises(LoiNhap):
            bo.sua_khoan(2, 0, 'thanh_tien', '1')

    def test_xoa_het_van_la_da_lap(self):
        # 0.9.21: người dùng lưu phương án không còn dòng nào = đã lập, mọi mục 0 đồng (trước: về "Chưa lập phương án")
        bo = BoSoan(self.con, 2, self.dm)
        for m in (1, 2, 3, nghiep_vu.MUC_VN, 4):
            while bo.ds(m):
                bo.xoa(m, 0)
        bo.luu()
        self.assertTrue(self.con.execute('SELECT trang_thai FROM ho WHERE ma_ho = 2').fetchone()[0].startswith(
            nghiep_vu.DA_LAP_LUU))
        k = nghiep_vu.tinh_ho(self.con, 2)
        self.assertEqual(k.tong, 0)
        self.assertTrue(k.co_phuong_an)

    def test_di_chuyen_dong_va_ho_ke(self):
        bo = BoSoan(self.con, 1, self.dm)
        a, b = bo.pa.khoan[3][0].ten, bo.pa.khoan[3][1].ten
        self.assertEqual(bo.di_chuyen(3, 0, 1), 1)
        self.assertEqual([d.ten for d in bo.pa.khoan[3][:2]], [b, a])
        self.assertEqual(bo.ho_ke(1), 2)
        self.assertIsNone(bo.ho_ke(-1))

    # ------------------------------------------------------------ danh mục, dự án
    def test_tim_danh_muc_khong_dau(self):
        ds = self.dm.tim(3, 'xoai nam thu hoach 11')
        self.assertTrue(ds)
        self.assertTrue(all('xoài' in m.ten.lower() for m in ds))
        self.assertEqual([m.ma for m in self.dm.tim(4, 'tu lo cho o')][:2], ['CS17', 'CS18'])
        self.assertEqual(len(self.dm.tim(2, '')), 139)

    def test_sua_thong_tin_du_an(self):
        gt = lap_pa.doc_du_an(self.con)
        gt['chu_dau_tu'] = 'Ban QLDA thử'                       # 0.9.72: bỏ Số phương án (theo đợt trình)
        gt['nam'] = '2026'
        lap_pa.luu_du_an(self.con, gt)
        self.assertEqual(lap_pa.doc_du_an(self.con)['chu_dau_tu'], 'Ban QLDA thử')
        gt['cap_dia_ban'] = 'Huyện'
        with self.assertRaises(LoiNhap):
            lap_pa.luu_du_an(self.con, gt)
        gt['cap_dia_ban'], gt['nam'] = 'Phường', '26'
        with self.assertRaises(LoiNhap):
            lap_pa.luu_du_an(self.con, gt)


class TestTyLeTrongVaDaLap(unittest.TestCase):
    """Ô tỷ lệ đất xóa trống thì không hiện lại 100; hộ lưu không có dòng tiền vẫn là đã lập; nguồn gốc có gạch đầu dòng."""

    def test_xoa_ty_le_va_ho_trong_van_da_lap(self):
        with tempfile.TemporaryDirectory() as td:
            con = csdl.tao_moi(Path(td) / 'a.pabt')
            try:
                self._xoa_ty_le(con)
            finally:
                con.close()

    def _xoa_ty_le(self, con):
        from pabt import ho_so, kiem_loi, theo_doi
        from pabt.du_toan import tu_du_an
        from pabt.nghiep_vu import thanh_tien_dong_dat
        ma = ho_so.luu_ho(con, None, {'ho_ten': 'Nguyen Van A'}, [{
            'so_to': '1', 'so_thua': '2', 'loai_dat': 'ONT', 'dt_thu_hoi': '100',
            'nguon_goc': 'Dat o lau nam - dat trong lua - dat vuon', 'vi_tri': ''}])
        goc = con.execute('SELECT nguon_goc FROM thua WHERE ma_ho = ?', (ma,)).fetchone()[0]
        self.assertEqual(goc, 'Dat o lau nam\n- dat trong lua\n- dat vuon')
        with con, csdl.mo_khoa_danh_muc(con):
            con.execute("INSERT OR REPLACE INTO dm_loaidat (ma, ten, nhom) VALUES ('ONT', 'Dat o', 'Dat o')")
        bo = BoSoan(con, ma)
        i, _ = bo.them_thua(con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ?', (ma,)).fetchone()[0])
        bo.sua_dat(i, 'loai_dat', 'ONT')
        bo.sua_dat(i, 'gia_bang_gia', '1000000')
        bo.sua_dat(i, 'he_so_k', '1')
        self.assertEqual(bo.o_dat(i)['ty_le'], '100')
        bo.sua_dat(i, 'ty_le', '')
        self.assertEqual(bo.o_dat(i)['ty_le'], '')
        self.assertIsNone(bo.pa.dat[i].ty_le)
        self.assertEqual(thanh_tien_dong_dat(bo.pa.dat[i], bo.bc), D(100) * D(1000000))
        bo.luu()
        bo.mo(ma)
        self.assertIsNone(bo.pa.dat[0].ty_le)
        self.assertEqual(bo.o_dat(0)['ty_le'], '')
        self.assertEqual(con.execute('SELECT ty_le FROM ct_dat').fetchone()[0], '')
        tt = theo_doi.tong_hop(con, tinh_pa=False)[0].trang_thai
        self.assertEqual(tt, 'Đã lập phương án')
        self.assertEqual(lap_pa.phan_loai_lap(con)[ma], 'da_lap')
        dt = tu_du_an(con)
        self.assertEqual(dt.dong[0].he_so, D(1))
        kiem_loi.kiem_tra(con)
        while bo.ds(1):
            bo.xoa(1, 0)
        bo.luu()
        self.assertEqual(theo_doi.tong_hop(con, tinh_pa=False)[0].trang_thai, 'Đã lập phương án')
        self.assertEqual(lap_pa.phan_loai_lap(con)[ma], 'da_lap')

    def test_nguon_goc_va_mau_in_khong_loi(self):
        from pabt import ho_so, in_an
        self.assertEqual(ho_so.chuan_nguon_goc('a: - b. – c'), 'a:\n- b.\n- c')
        # 0.9.88: gạch nối giữa tên (không sau dấu kết câu) giữ trên cùng dòng
        self.assertEqual(ho_so.chuan_nguon_goc('Khu Bảo tồn thiên nhiên - Văn hoá Đồng Nai; ông A (con bà B - đại diện) sử dụng'),
                         'Khu Bảo tồn thiên nhiên - Văn hoá Đồng Nai; ông A (con bà B - đại diện) sử dụng')
        self.assertEqual(ho_so.chuan_nguon_goc('như sau: - Thửa 1 - Văn hoá. - Thửa 2'), 'như sau:\n- Thửa 1 - Văn hoá.\n- Thửa 2')
        # khoảng năm "1975 - 1990" không phải gạch đầu dòng (trước đây hai khoảng năm trên một dòng bị tách thành danh sách)
        self.assertEqual(ho_so.chuan_nguon_goc('Ông A sử dụng 1975 - 1990, bà B 1990 - 2005 - nay'),
                         'Ông A sử dụng 1975 - 1990, bà B 1990 - 2005 - nay')
        self.assertEqual(ho_so.chuan_nguon_goc('đất ở - đất lúa - đất vườn'), 'đất ở\n- đất lúa\n- đất vườn')
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            import openpyxl
            wb = openpyxl.Workbook()
            wb.active['A1'] = 'Mau tuy y'
            p = td / 'mau.xlsx'
            wb.save(p)
            ds, chu = in_an.nap_mau_in(p, td / 'ra')
            self.assertTrue(ds)
            self.assertIn('mẫu in', chu)
            ds2, chu2 = in_an.nap_mau_in(td / 'khong_co.pdf', td / 'ra2')
            self.assertTrue(chu2)


class TestDocSo(unittest.TestCase):
    def test_kieu_viet_nam(self):
        self.assertEqual(lap_pa.doc_so('1.000', 'x'), 1000)
        self.assertEqual(lap_pa.doc_so('1.480.500', 'x'), 1480500)
        self.assertEqual(lap_pa.doc_so('143,8', 'x'), Decimal('143.8'))
        self.assertEqual(lap_pa.doc_so('2,125', 'x'), Decimal('2.125'))
        self.assertEqual(lap_pa.doc_so('', 'x'), 0)
        self.assertIsNone(lap_pa.doc_ty_le(''))
        self.assertEqual(lap_pa.hien_ty_le(None), '')
        self.assertEqual(lap_pa.hien_ty_le(1), '100')
        self.assertEqual(lap_pa.doc_ty_le('50'), Decimal('0.5'))
        with self.assertRaises(LoiNhap):
            lap_pa.doc_so('1,2,3', 'x')


class TestNangCapCSDL(unittest.TestCase):
    def test_file_phien_ban_1_duoc_nang_cap(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'cu.pabt'
            sql = (Path(nghiep_vu.__file__).with_name('schema.sql')).read_text(encoding='utf-8')
            sql = sql.replace("    dt_nn_dang_dung TEXT,", "    dt_nn_dang_dung TEXT").replace(
                "    luu_luc         TEXT                              -- lần lưu phương án gần nhất trong phần mềm (trống = số liệu nhập từ Excel)\n", "")
            sql = sql.replace("    can_cu_gia   TEXT NOT NULL DEFAULT '',             -- căn cứ đơn giá khi áp giá tương đương / nhập tay\n", "")
            c = sqlite3.connect(p)
            c.executescript(sql)
            c.execute('PRAGMA user_version = 1')
            c.execute("INSERT INTO du_an (id) VALUES (1)")
            c.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'A')")
            c.commit()
            cot = [r[1] for r in c.execute('PRAGMA table_info(ho)')]
            self.assertNotIn('luu_luc', cot)
            c.close()
            con = csdl.mo(p)
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
            self.assertIn('luu_luc', [r[1] for r in con.execute('PRAGMA table_info(ho)')])
            self.assertIn('can_cu_gia', [r[1] for r in con.execute('PRAGMA table_info(ct_khoan)')])
            bo = BoSoan(con, 1)
            bo.them_hang_muc_khac(2, 'Chuồng heo')
            bo.sua_khoan(2, 0, 'so_luong', '10')
            bo.luu()
            self.assertEqual(nghiep_vu.tinh_ho(con, 1).muc[2], 0)
            con.close()


if __name__ == '__main__':
    unittest.main()
