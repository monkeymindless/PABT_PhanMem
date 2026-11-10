"""1.0.56 (người dùng 03/11/2026): khóa bảo mật bộ đơn giá - chỉ tài khoản quản trị máy chủ (máy dùng LAN) hoặc quản trị máy đơn (mật
khẩu) sửa được bộ đơn giá đất, tài sản, cây trồng, vật nuôi, chính sách hỗ trợ; khóa ở TẦNG GHI; quản trị sửa xong tự phát hành lên máy chủ,
máy khác nhận khi đăng nhập (dong_bo_don_gia). Thư mục máy / máy chủ đều là thư mục tạm (không đụng %APPDATA% thật)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pabt import dong_bo_don_gia as db
from pabt import don_gia, gia_dat_nq28, he_so_k, may_chu, quan_tri_bo
from pabt.quan_tri_bo import LoiQuyenBoDonGia

DONG_GIA = [dict(xa='Xã Thử', tt='1', tuyen_duong='Đường A', diem_dau='', diem_cuoi='', loai_dat='ODT', mt='1000')]


class _Nen(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_khoa_bo_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        self.dat_may('may_a')
        quan_tri_bo.khoa_lai_phien()
        may_chu.dang_xuat()

    def tearDown(self):
        may_chu.dang_xuat()
        quan_tri_bo.khoa_lai_phien()
        gia_dat_nq28._quen()
        he_so_k._quen()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)

    def dat_may(self, ten):
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / ten)
        gia_dat_nq28._quen()
        he_so_k._quen()

    def ghi_gia_dat(self):
        return gia_dat_nq28.ghi_thay([dict(r) for r in DONG_GIA], 'NQ thử', 'thử')


class TestMayDon(_Nen):
    def test_chua_dat_mat_khau_thi_sua_duoc(self):
        self.assertTrue(quan_tri_bo.co_quyen_sua())
        don_gia.cai_bo(don_gia.file_goc())
        self.assertTrue(don_gia.file_cap_nhat().exists())
        self.ghi_gia_dat()
        self.assertTrue(gia_dat_nq28.file_thay().exists())

    def test_da_dat_mat_khau_phai_mo_khoa(self):
        quan_tri_bo.dat('matkhau1')
        self.assertFalse(quan_tri_bo.co_quyen_sua())
        for viec in (lambda: don_gia.cai_bo(don_gia.file_goc()), self.ghi_gia_dat, gia_dat_nq28.xoa_thay, he_so_k.xoa,
                     lambda: don_gia.them_dong('tham_so', dict(ma='THU1', ten='Thử', gia_tri='1')),
                     don_gia.khoi_phuc_bo_goc):
            with self.assertRaises(LoiQuyenBoDonGia):
                viec()
        self.assertFalse(don_gia.file_cap_nhat().exists())          # chưa ghi gì
        self.assertFalse(gia_dat_nq28.file_thay().exists())
        quan_tri_bo.mo_khoa_phien()
        self.ghi_gia_dat()
        self.assertTrue(gia_dat_nq28.file_thay().exists())

    def test_hop_bo_don_gia_sai_mat_khau_khong_mo_khoa(self):
        from tests import APP  # noqa: F401
        from pabt import csdl
        from pabt.man_hinh_don_gia import HopBoDonGia
        quan_tri_bo.dat('matkhau1')
        con = csdl.tao_moi(self.td / 'c.pabt')
        try:
            d = HopBoDonGia(None, con)
            d.im_lang = False                                      # đường có hộp HopXacThucBo (truyền mật khẩu, không exec)
            self.assertFalse(d.mo_khoa_quan_tri('sai_mat_khau'))   # trước 1.0.56: sai mật khẩu vẫn mở khóa
            self.assertFalse(d._da_mo_khoa)
            self.assertFalse(quan_tri_bo.co_quyen_sua())
            self.assertTrue(d.mo_khoa_quan_tri('matkhau1'))
            self.assertTrue(quan_tri_bo.co_quyen_sua())            # mở khóa cả phiên (giá đất, hệ số K cũng sửa được)
            d.close()
            d.deleteLater()
        finally:
            con.close()


class TestMayChu(_Nen):
    def setUp(self):
        super().setUp()
        self.goc = self.td / 'MayChu'
        may_chu.khoi_tao(self.goc, 'QuanTri', 'matkhau1', 'Quản trị')
        qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        may_chu.them_nguoi_dung(qt, 'nv1', 'Nhân viên', 'abc12345')
        may_chu.dang_xuat()

    def test_may_dung_may_chu_chi_quan_tri_sua(self):
        quan_tri_bo.dat('matkhau1')                                # mật khẩu máy KHÔNG thay được quyền quản trị máy chủ
        quan_tri_bo.mo_khoa_phien()
        self.assertTrue(quan_tri_bo.may_duoc_quan_ly())          # dang_nhap đã ghi may_chu.json
        self.assertFalse(quan_tri_bo.co_quyen_sua())             # chưa đăng nhập (offline): không sửa
        with self.assertRaises(LoiQuyenBoDonGia) as e:
            self.ghi_gia_dat()
        self.assertIn('quản trị máy chủ', str(e.exception))
        may_chu.dang_nhap(self.goc, 'nv1', 'abc12345')
        self.assertFalse(quan_tri_bo.co_quyen_sua())
        with self.assertRaises(LoiQuyenBoDonGia):
            don_gia.cai_bo(don_gia.file_goc())
        with self.assertRaises(LoiQuyenBoDonGia):
            he_so_k.xoa()
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        self.assertTrue(quan_tri_bo.co_quyen_sua())

    def test_quan_tri_sua_thi_phat_hanh_may_khac_nhan(self):
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        don_gia.them_dong('tham_so', dict(ma='THU1', ten='Tham số thử', gia_tri='7'))
        self.assertEqual(quan_tri_bo.LOI_PHAT_HANH, '')
        pb = db.doc_phien_ban(self.goc)
        self.assertIsNotNone(pb)
        self.assertTrue((self.goc / db.THU_MUC / db.FILE_BO).is_file())
        self.assertIsNone(pb['tep'][db.FILE_GIA_DAT])             # quản trị dùng bảng giá gắn sẵn
        self.ghi_gia_dat()                                         # sửa giá đất -> phát hành lại (mã mới)
        pb2 = db.doc_phien_ban(self.goc)
        self.assertNotEqual(pb['ma'], pb2['ma'])
        self.assertIsNone(db.can_nhan(self.goc))                  # máy quản trị không tải lại bản của chính mình
        may_chu.dang_xuat()
        # máy khác (thư mục máy riêng), nhân viên đăng nhập -> nhận đúng bộ của quản trị
        self.dat_may('may_b')
        may_chu.dang_nhap(self.goc, 'nv1', 'abc12345')
        self.assertIsNotNone(db.can_nhan())
        kq = db.nhan()
        self.assertIsNotNone(kq)
        self.assertEqual(don_gia.doc_dong('tham_so', 'THU1')['gia_tri'], '7')
        self.assertEqual([r['tuyen_duong'] for r in gia_dat_nq28.tat_ca()], ['Đường A'])
        self.assertIsNone(db.nhan())                              # lần sau: đã mới nhất
        with self.assertRaises(LoiQuyenBoDonGia):                 # máy nhân viên vẫn không sửa được
            don_gia.them_dong('tham_so', dict(ma='THU2', ten='X', gia_tri='1'))
        # quản trị dùng lại bảng giá gắn sẵn -> máy nhân viên cũng bỏ bảng đã nhận
        may_chu.dang_xuat()
        self.dat_may('may_a')
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        self.assertTrue(gia_dat_nq28.xoa_thay())
        may_chu.dang_xuat()
        self.dat_may('may_b')
        may_chu.dang_nhap(self.goc, 'nv1', 'abc12345')
        db.nhan()
        self.assertFalse(gia_dat_nq28.file_thay().exists())

    def test_file_may_chu_bi_sua_khong_cai(self):
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        db.phat_hanh()
        may_chu.dang_xuat()
        f = self.goc / db.THU_MUC / db.FILE_BO
        with open(f, 'ab') as x:
            x.write(b'hong')
        self.dat_may('may_b')
        may_chu.dang_nhap(self.goc, 'nv1', 'abc12345')
        with self.assertRaises(db.LoiDongBo):
            db.nhan()
        self.assertFalse(don_gia.file_cap_nhat().exists())        # máy giữ bộ cũ (bản đóng gói)
        self.assertEqual(db.ma_da_nhan(), '')

    def test_nhan_vien_khong_phat_hanh(self):
        may_chu.dang_nhap(self.goc, 'nv1', 'abc12345')
        with self.assertRaises(db.LoiDongBo):
            db.phat_hanh()
        self.assertIsNone(db.doc_phien_ban(self.goc))

    def test_phien_ban_json(self):
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        pb = db.phat_hanh()
        d = json.loads((self.goc / db.THU_MUC / db.FILE_PHIEN_BAN).read_text(encoding='utf-8'))
        self.assertEqual(d['ma'], pb['ma'])
        self.assertIn('quantri', d['nguoi'])
        self.assertIn('bộ đơn giá', db.mo_ta(d))


if __name__ == '__main__':
    unittest.main()
