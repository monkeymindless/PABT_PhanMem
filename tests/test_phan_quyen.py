"""1.0.57 (đề án LARC V2.0 của người dùng, Gói 2): 6 vai trò tài khoản máy chủ LAN - hàm ghi, trigger CSDL, lưu phương án, xóa hộ,
lệnh giao diện. Dự án GIẢ LẬP."""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, ho_so, lan_pa, may_chu, nhap_tai_san, phan_quyen as pq, theo_doi
from pabt.lap_pa import BoSoan, DanhMuc
from tests.test_toc_do import _du_an


class _Nen(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_pq_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.p = _du_an(self.td, 4)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        may_chu.dang_xuat()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)

    def bo(self, i=0):
        return BoSoan(self.con, self.ma[i], DanhMuc(self.con))

    def them_danh_muc(self, bo, muc=2):
        m = next(x for x in bo.dm.muc[muc] if x.don_gia)
        nhap_tai_san.them_mot(nhap_tai_san.DichPhuongAn(bo), muc, m, so_luong='3')
        return m


class TestVaiTro(_Nen):
    def test_may_don_khong_gioi_han(self):
        self.assertIsNone(pq.vai_tro_cua(self.con))
        bo = self.bo()
        self.them_danh_muc(bo)
        bo.luu()                                                       # không vai trò: như trước
        self.assertEqual(pq.quyen_cua(None), pq.TAT_CA)
        self.assertFalse(pq.chi_xem(None))

    def test_kiem_dem_vien(self):
        pq.gan(self.con, pq.KIEM_DEM)
        bo = self.bo()
        self.them_danh_muc(bo)
        bo.luu()                                                       # dòng mới đúng giá bộ đơn giá: lưu được
        bo = self.bo()
        i = len(bo.pa.khoan[2]) - 1
        bo.pa.khoan[2][i].don_gia = bo.pa.khoan[2][i].don_gia + 1000
        with self.assertRaises(pq.LoiQuyen):
            bo.luu()                                                   # sửa đơn giá
        bo = self.bo()
        self.them_danh_muc(bo, 4) if bo.dm.muc[4] and any(x.don_gia for x in bo.dm.muc[4]) else None
        if any(d for d in bo.pa.khoan[4]):
            with self.assertRaises(pq.LoiQuyen):
                bo.luu()                                               # áp chính sách hỗ trợ
        with self.assertRaises(pq.LoiQuyen):
            theo_doi.ghi_qd_ho(self.con, 1, self.ma[0], {})
        with self.assertRaises(sqlite3.IntegrityError):               # lớp cuối: trigger tạm
            self.con.execute("INSERT INTO quyet_dinh (so, ngay) VALUES ('1/QĐ', '01/11/2026')")
        self.assertEqual(pq.quyen_bang(pq.KIEM_DEM, 2), dict(khoi_luong=True, gia=False, them_xoa=True))
        self.assertEqual(pq.quyen_bang(pq.KIEM_DEM, 4), dict(khoi_luong=False, gia=False, them_xoa=False))

    def test_ke_toan_khong_sua_phuong_an(self):
        pq.gan(self.con, pq.KE_TOAN)
        bo = self.bo()
        self.them_danh_muc(bo)
        with self.assertRaises(pq.LoiQuyen):
            bo.luu()
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute('DELETE FROM ct_dat WHERE ma_ho = ?', (self.ma[0],))
        with self.assertRaises(pq.LoiQuyen):
            ho_so.luu_ho(self.con, None, dict(ho_ten='Hộ mới'), [])
        with self.assertRaises(pq.LoiQuyen):
            lan_pa.tao_lan_moi(self.con, self.ma[0])

    def test_tham_dinh_khoa_lan_lanh_dao_mo_khoa(self):
        pq.gan(self.con, pq.THAM_DINH)
        lan_pa.khoa_lai(self.con, self.ma[0], 1)                       # thẩm định: khóa được
        with self.assertRaises(pq.LoiQuyen):
            lan_pa.mo_khoa_lan(self.con, self.ma[0], 1, 'thử')
        pq.gan(self.con, pq.LANH_DAO)
        lan_pa.mo_khoa_lan(self.con, self.ma[0], 1, 'sửa số liệu')    # lãnh đạo: mở khóa

    def test_xoa_ho(self):
        pq.gan(self.con, pq.CHUYEN_VIEN)
        with self.assertRaises(pq.LoiQuyen):                          # hộ đã lập phương án (Dự án mới tự lập)
            ho_so.xoa_nhieu_ho(self.con, [self.ma[0]])
        moi = ho_so.luu_ho(self.con, None, dict(ho_ten='Hộ chưa lập'), [])
        ho_so.xoa_nhieu_ho(self.con, [moi])                            # hộ chưa lập: xóa được
        with csdl.giao_dich(self.con):
            self.con.execute('DROP TRIGGER IF EXISTS temp._pq_x')
        pq.gan(self.con, pq.LANH_DAO)
        self.con.execute('UPDATE ho SET da_phe_duyet = 1 WHERE ma_ho = ?', (self.ma[1],))
        with self.assertRaises(pq.LoiQuyen):
            ho_so.xoa_nhieu_ho(self.con, [self.ma[1]])
        with self.assertRaises(sqlite3.IntegrityError):               # cả khi xóa thẳng bằng SQL
            self.con.execute('DELETE FROM ho WHERE ma_ho = ?', (self.ma[1],))

    def test_lenh_va_chi_xem(self):
        self.assertTrue(pq.chi_xem(pq.THANH_TRA))
        self.assertFalse(pq.chi_xem(pq.KE_TOAN))
        tat = pq.lenh_bi_tat(pq.KIEM_DEM, ['Thêm hộ…', 'Xóa hộ…', 'Trạng thái hộ…', 'Dự thảo PABT…', 'Lập phương án hộ…'])
        self.assertEqual(tat, ['Xóa hộ…', 'Trạng thái hộ…', 'Dự thảo PABT…'])
        self.assertEqual(pq.lenh_bi_tat(pq.NGUOI_DUNG_CU, list(pq.LENH_QUYEN)), ['Quản lý tài khoản…'])
        self.assertEqual(pq.lenh_bi_tat(None, list(pq.LENH_QUYEN)), [])
        self.assertEqual(pq.quyen_cua('vai_tro_la'), frozenset())      # máy chủ bản mới hơn: chỉ xem
        mt = pq.ma_tran()
        self.assertEqual(len(mt[0][1]), 6)


class TestMayChu(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_pq_mc_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.goc = self.td / 'MayChu'
        may_chu.khoi_tao(self.goc, 'QuanTri', 'matkhau1', 'Quản trị')

    def tearDown(self):
        may_chu.dang_xuat()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)

    def test_vai_tro_tai_khoan_va_file(self):
        qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        for vt in pq.TEN_VAI_TRO:
            may_chu.them_nguoi_dung(qt, vt.replace('_', ''), f'Người {vt}', 'abc123', vai_tro=vt)
        ld = may_chu.dang_nhap(self.goc, 'lanhdao', 'abc123')
        self.assertTrue(ld.la_quan_tri)                                # lãnh đạo = quản trị (tài khoản, bộ đơn giá)
        f = may_chu.thu_muc_du_an(self.goc) / 'DA.pabt'
        csdl.tao_moi(f).close()
        kd = may_chu.dang_nhap(self.goc, 'kiemdem', 'abc123')
        self.assertFalse(kd.la_quan_tri)
        self.assertEqual(pq.vai_tro_cho_file(f), pq.KIEM_DEM)
        self.assertIsNone(pq.vai_tro_cho_file(self.td / 'rieng.pabt'))  # file riêng trên máy: không giới hạn
        from pabt import quan_tri_bo
        self.assertFalse(quan_tri_bo.co_quyen_sua())                    # kiểm đếm viên không sửa bộ đơn giá
        may_chu.sua_nguoi_dung(may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1'), 'kiemdem', vai_tro=pq.CHUYEN_VIEN)
        self.assertEqual(may_chu.dang_nhap(self.goc, 'kiemdem', 'abc123').vai_tro, pq.CHUYEN_VIEN)


if __name__ == '__main__':
    unittest.main()
