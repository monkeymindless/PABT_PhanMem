"""1.0.63: đa phiên bản phương án V0 -> V1 -> V2.n -> V3. Kịch bản của người dùng: niêm yết 10.000 đ, dân đề nghị 50.000 đ, duyệt lại 10.000 đ - không nhập tay lại."""
from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import csdl, du_an_moi
from pabt import phien_ban_pa as pb
from pabt.lap_pa import BoSoan, LoiNhap
from pabt.nghiep_vu import DongKhoan, tinh_ho

D = Decimal


def _du_an(td: Path, so_ho: int = 3) -> Path:
    dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i), loai_dat='CLN', dt_thu_hoi='100', vi_tri='1') for i in range(so_ho)]
    p = td / 'a.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Tân An', nam='2026'), dong, [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    return p


def dat_cay(con, ma, gia=10000, so=100):
    """Hộ có một dòng cây: số lượng so, đơn giá gia (số dễ kiểm)."""
    bo = BoSoan(con, ma)
    bo.pa.dat[:] = []
    bo.pa.khoan[3] = [DongKhoan(muc=3, ten='Cây thử', dvt='cây', so_luong=D(so), don_gia=D(gia))]
    bo.pa.khoan[4] = []
    bo.luu()


def doi_gia(con, ma, ma_v, gia):
    bo = BoSoan(con, ma)
    bo.mo_phien_ban(ma_v)
    bo.pa.khoan[3][0].don_gia = D(gia)
    bo.luu()


class CoSo(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.con = csdl.mo(_du_an(Path(self.td.name)))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        dat_cay(self.con, self.ma[0])


class TestKichBan(CoSo):
    def test_10000_50000_ve_10000(self):
        con, m = self.con, self.ma[0]
        self.assertTrue(pb.khoa_v1(con, m, 'Đợt 1'))
        v2 = pb.tao_v2(con, m, 'Dân đề nghị 50.000 đ')
        self.assertEqual(v2, 'V2.1')
        doi_gia(con, m, v2, 50000)
        dc = pb.doi_chieu_ho(con, m)
        d = next(x for x in dc['dong'] if x['ten'] == 'Cây thử')
        self.assertEqual((d['dg1'], d['dg2'], d['dg_d1']), (D(10000), D(50000), D(40000)))     # +40.000 đ / đơn vị
        self.assertEqual(d['d1'], D(4000000))
        self.assertEqual(dc['tong']['d1'] >= D(4000000), True)
        # chấp nhận V2 làm số trình: V3 = 50.000, hiện hành theo V3
        pb.dat_v3(con, m, v2, 'Thử chấp nhận')
        self.assertEqual(BoSoan(con, m).pa.khoan[3][0].don_gia, D(50000))
        # thẩm định bác: một chạm về V1, không nhập tay
        pb.dat_v3(con, m, pb.V1, 'Phòng Kinh tế không chấp thuận')
        self.assertEqual(BoSoan(con, m).pa.khoan[3][0].don_gia, D(10000))
        for ma_v, gia in ((pb.V1, 10000), (v2, 50000), (pb.V3, 10000)):            # cả ba còn nguyên
            self.assertEqual(pb.doc_pa(con, m, ma_v).khoan[3][0].don_gia, D(gia), ma_v)
        dc = pb.doi_chieu_ho(con, m)
        self.assertEqual(dc['tong']['d2'], 0)
        self.assertEqual(next(x for x in dc['dong'] if x['ten'] == 'Cây thử')['trang_thai'], 'Có ý kiến nhưng giữ theo V1')
        self.assertEqual(dc['ly_do'], 'Phòng Kinh tế không chấp thuận')
        self.assertEqual(tinh_ho(con, m).tong, pb.tong(con, m, pb.V3))             # tổng hiện hành = tổng V3

    def test_v1_khong_bao_gio_bi_ghi_de(self):
        con, m = self.con, self.ma[0]
        pb.khoa_v1(con, m)
        dat_cay(con, m, gia=77777)                                                 # sửa số hiện hành sau niêm yết
        self.assertFalse(pb.khoa_v1(con, m))                                       # bấm in lại: giữ V1 cũ
        self.assertEqual(pb.doc_pa(con, m, pb.V1).khoan[3][0].don_gia, D(10000))
        with self.assertRaises(LoiNhap):
            pb.sua(con, m, pb.V1, pb.doc_pa(con, m, pb.V1))
        bo = BoSoan(con, m)
        bo.mo_phien_ban(pb.V1)
        self.assertTrue(bo.khoa)
        with self.assertRaises(LoiNhap):
            bo.luu()

    def test_v2_khong_dung_so_hien_hanh(self):
        con, m = self.con, self.ma[0]
        pb.khoa_v1(con, m)
        v2 = pb.tao_v2(con, m)
        doi_gia(con, m, v2, 50000)
        self.assertEqual(BoSoan(con, m).pa.khoan[3][0].don_gia, D(10000))          # V0 không đổi
        self.assertEqual(pb.doc_pa(con, m, pb.V1).khoan[3][0].don_gia, D(10000))
        self.assertEqual(pb.tao_v2(con, m, nguon=v2), 'V2.2')
        self.assertEqual(pb.doc_pa(con, m, 'V2.2').khoan[3][0].don_gia, D(50000))
        self.assertEqual([x['ma'] for x in pb.ds_phien_ban(con, m)], ['V1', 'V2.1', 'V2.2', 'V3'])

    def test_sua_v3_ghi_luon_hien_hanh(self):
        con, m = self.con, self.ma[0]
        pb.khoa_v1(con, m)
        doi_gia(con, m, pb.V3, 20000)
        self.assertEqual(BoSoan(con, m).pa.khoan[3][0].don_gia, D(20000))
        self.assertEqual(pb.doc_pa(con, m, pb.V1).khoan[3][0].don_gia, D(10000))

    def test_tu_y_kien_khong_tao_trung(self):
        con, m = self.con, self.ma[0]
        self.assertEqual(pb.tao_v2_tu_y_kien(con, m, 'Xin nâng giá'), 'V2.1')       # chưa có V1: tự chốt
        self.assertIsNotNone(pb.lay(con, m, pb.V1))
        self.assertEqual(pb.tao_v2_tu_y_kien(con, m, 'Xin nâng giá'), '')           # đọc lại file
        self.assertEqual(pb.tao_v2_tu_y_kien(con, m, 'Ý kiến khác'), 'V2.2')


class TestGhep(CoSo):
    def test_ghep_tung_nhom(self):
        con, m = self.con, self.ma[0]
        bo = BoSoan(con, m)
        bo.pa.khoan[2] = [DongKhoan(muc=2, ten='Nhà thử', dvt='m2', so_luong=D(10), don_gia=D(1000))]
        bo.luu()
        pb.khoa_v1(con, m)
        v2 = pb.tao_v2(con, m)
        b2 = BoSoan(con, m)
        b2.mo_phien_ban(v2)
        b2.pa.khoan[2][0].don_gia = D(2000)
        b2.pa.khoan[3][0].don_gia = D(50000)
        b2.luu()
        pb.ghep_v3(con, m, {pb.DAT: pb.V1, pb.NHA: v2, pb.CAY: pb.V1, pb.HO_TRO: pb.V1})
        p3 = pb.doc_pa(con, m, pb.V3)
        self.assertEqual((p3.khoan[2][0].don_gia, p3.khoan[3][0].don_gia), (D(2000), D(10000)))
        self.assertEqual(BoSoan(con, m).pa.khoan[2][0].don_gia, D(2000))
        self.assertIn('NHA_VKT', pb.lay(con, m, pb.V3)['nguon_nhom'])

    def test_ghep_tinh_lai_ho_tro_khong_loi(self):
        con, m = self.con, self.ma[0]
        pb.khoa_v1(con, m)
        pb.ghep_v3(con, m, {pb.HO_TRO: pb.TINH_LAI})
        self.assertIsNotNone(pb.lay(con, m, pb.V3))

    def test_ap_dong_loat(self):
        con = self.con
        for m in self.ma:
            dat_cay(con, m)
            pb.khoa_v1(con, m)
            doi_gia(con, m, pb.tao_v2(con, m), 50000)
            pb.dat_v3(con, m, 'V2.1')
        n, loi = pb.ap_dong_loat(con, self.ma + [99999], pb.V1, 'Bác ý kiến')
        self.assertEqual(n, 3)
        self.assertEqual(len(loi), 1)                                              # hộ không có V1: báo riêng, hộ khác vẫn áp
        for m in self.ma:
            self.assertEqual(BoSoan(con, m).pa.khoan[3][0].don_gia, D(10000))
            self.assertEqual(pb.doc_pa(con, m, 'V2.1').khoan[3][0].don_gia, D(50000))
        ds = pb.doi_chieu_dot(con, self.ma)
        self.assertEqual([x['d2'] for x in ds], [0, 0, 0])


class TestTuongThich(unittest.TestCase):
    def test_file_cu_chua_co_bang(self):
        with tempfile.TemporaryDirectory() as td:
            p = _du_an(Path(td))
            con = csdl.mo(p)
            ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
            con.close()
            import sqlite3
            c = sqlite3.connect(str(p))
            c.execute('DROP TABLE IF EXISTS pa_phien_ban')
            c.execute('DROP TABLE IF EXISTS ho_uuid')
            c.commit()
            c.close()
            xem = csdl.mo(p, chi_doc=True)                                       # mở chỉ xem: không tạo bảng, không lỗi
            self.assertEqual(pb.ds_phien_ban(xem, ma), [])
            self.assertEqual(pb.khoa_v1_nhieu(xem, [ma]), 0)
            self.assertEqual(pb.uuid_ho(xem, ma), '')
            self.assertFalse(pb.doi_chieu_ho(xem, ma)['co_v1'])
            xem.close()
            con = csdl.mo(p)                                                      # mở để ghi: tự có bảng, dữ liệu giữ nguyên
            self.assertTrue(pb.co_bang(con))
            self.assertTrue(pb.khoa_v1(con, ma))
            con.close()

    def test_xoa_ho_xoa_phien_ban_va_uuid(self):
        with tempfile.TemporaryDirectory() as td:
            con = csdl.mo(_du_an(Path(td)))
            ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
            pb.khoa_v1(con, ma)
            u = pb.uuid_ho(con, ma)
            self.assertEqual(pb.uuid_ho(con, ma), u)
            self.assertEqual(pb.bang_uuid(con)[u], ma)
            from pabt import ho_so
            ho_so.xoa_ho(con, ma)
            self.assertEqual(pb.ds_phien_ban(con, ma), [])
            self.assertNotIn(u, pb.bang_uuid(con))
            con.close()

    def test_lan_da_duyet_khong_ap_duoc(self):
        with tempfile.TemporaryDirectory() as td:
            con = csdl.mo(_du_an(Path(td)))
            ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
            dat_cay(con, ma)
            pb.khoa_v1(con, ma)
            v2 = pb.tao_v2(con, ma)
            doi_gia(con, ma, v2, 50000)
            from pabt import lan_pa
            lan_pa._dam_bao_dong(con, ma, 1)
            with con:
                con.execute('UPDATE pa_lan SET khoa = 1 WHERE ma_ho = ? AND lan = 1', (ma,))
            with self.assertRaises(LoiNhap):
                pb.dat_v3(con, ma, v2)
            self.assertEqual(BoSoan(con, ma).pa.khoan[3][0].don_gia, D(10000))
            self.assertEqual(pb.doc_pa(con, ma, pb.V3).khoan[3][0].don_gia, D(10000))     # lỗi: V3 cũng không đổi (một giao dịch)
            con.close()


if __name__ == '__main__':
    unittest.main()
