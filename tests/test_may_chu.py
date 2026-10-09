"""Kiểm thử máy chủ LAN (thư mục dùng chung): khởi tạo, đăng nhập / khóa tài khoản, quản lý tài khoản, dự án gần đây (nối tiếp ở
máy bất kỳ), danh sách dự án, mang về làm offline / đưa lên / xung đột / hủy, và các hộp thoại (im_lang)."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from pabt import csdl, khoa, may_chu
from pabt.may_chu import LoiMayChu

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class _Nen(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_mc_'))
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

    def du_an(self, ten='DA1') -> Path:
        f = may_chu.thu_muc_du_an(self.goc) / f'{ten}.pabt'
        con = csdl.tao_moi(f)
        with con:
            con.execute('UPDATE du_an SET ten = ? WHERE id = 1', (f'Dự án {ten}',))
        con.close()
        return f


class TestMayChu(_Nen):
    def test_khoi_tao_dang_nhap(self):
        self.assertTrue((self.goc / 'DuAn').is_dir() and (self.goc / 'SaoLuu').is_dir())
        self.assertTrue(may_chu.ket_noi_duoc(self.goc))
        self.assertFalse(may_chu.ket_noi_duoc(self.td / 'khong_co'))
        with self.assertRaises(LoiMayChu):
            may_chu.khoi_tao(self.goc, 'abc', 'matkhau1')            # đã là máy chủ
        p = may_chu.dang_nhap(self.goc, ' quantri ', 'matkhau1')     # không phân biệt hoa thường, khoảng trắng
        self.assertTrue(p.la_quan_tri)
        self.assertIs(may_chu.PHIEN, p)
        self.assertEqual(csdl.NGUOI_DUNG, 'Quản trị (quantri)')
        self.assertEqual(khoa.NGUOI_DUNG, 'Quản trị (quantri)')
        ch = may_chu.doc_cau_hinh()
        self.assertEqual((ch['may_chu'], ch['tai_khoan']), (str(self.goc), 'quantri'))
        may_chu.dang_xuat()
        self.assertIsNone(may_chu.PHIEN)
        self.assertIsNone(csdl.NGUOI_DUNG)

    def test_sai_mat_khau_khoa_tai_khoan(self):
        qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        may_chu.them_nguoi_dung(qt, 'vinh.pt', 'Phan Tuấn Vinh', 'abc123')
        for _ in range(4):
            with self.assertRaises(LoiMayChu):
                may_chu.dang_nhap(self.goc, 'vinh.pt', 'sai')
        may_chu.dang_nhap(self.goc, 'vinh.pt', 'abc123')               # đúng trước lần 5: đếm lại từ đầu
        for _ in range(5):
            with self.assertRaises(LoiMayChu):
                may_chu.dang_nhap(self.goc, 'vinh.pt', 'sai')
        with self.assertRaisesRegex(LoiMayChu, 'khóa'):
            may_chu.dang_nhap(self.goc, 'vinh.pt', 'abc123')
        may_chu.sua_nguoi_dung(qt, 'vinh.pt', khoa=False)              # quản trị mở khóa
        self.assertEqual(may_chu.dang_nhap(self.goc, 'vinh.pt', 'abc123').tai_khoan, 'vinh.pt')
        with self.assertRaises(LoiMayChu):
            may_chu.dang_nhap(self.goc, 'khongco', 'abc123')

    def test_quan_ly_tai_khoan(self):
        qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        may_chu.them_nguoi_dung(qt, 'nv1', 'Nhân viên 1', 'abc123', chuc_vu='Chuyên viên')
        for tk, ten, mk in (('a', 'X', 'abc123'), ('Có dấu', 'X', 'abc123'), ('nv2', 'X', '123'), ('nv2', '', 'abc123'),
                            ('nv1', 'Trùng', 'abc123')):
            with self.assertRaises(LoiMayChu):
                may_chu.them_nguoi_dung(qt, tk, ten, mk)
        with self.assertRaises(LoiMayChu):
            may_chu.sua_nguoi_dung(qt, 'quantri', khoa=True)           # không tự khóa mình
        with self.assertRaises(LoiMayChu):
            may_chu.sua_nguoi_dung(qt, 'quantri', vai_tro=may_chu.NGUOI_DUNG)
        nv = may_chu.dang_nhap(self.goc, 'nv1', 'abc123')
        self.assertFalse(nv.la_quan_tri)
        with self.assertRaises(LoiMayChu):
            may_chu.them_nguoi_dung(nv, 'nv3', 'X', 'abc123')          # người dùng thường không thêm được
        with self.assertRaises(LoiMayChu):
            may_chu.doi_mat_khau(nv, 'sai', 'moi12345')
        may_chu.doi_mat_khau(nv, 'abc123', 'moi12345')
        may_chu.dang_nhap(self.goc, 'nv1', 'moi12345')
        may_chu.dat_lai_mat_khau(qt, 'nv1', 'reset123')
        may_chu.dang_nhap(self.goc, 'nv1', 'reset123')
        ds = {u['tai_khoan']: u for u in may_chu.ds_nguoi_dung(self.goc)}
        self.assertEqual(ds['nv1']['chuc_vu'], 'Chuyên viên')
        self.assertTrue(ds['nv1']['dang_nhap_cuoi'])
        self.assertTrue(any(x['viec'] == 'Đặt lại mật khẩu' for x in may_chu.nhat_ky_may_chu(self.goc)))

    def test_noi_tiep_du_an_o_may_khac(self):
        f1, f2 = self.du_an('DA1'), self.du_an('DA2')
        p = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        self.assertEqual(may_chu.thu_muc_mac_dinh(), may_chu.thu_muc_du_an())
        may_chu.ghi_mo_du_an(f1)
        time.sleep(1.1)
        may_chu.ghi_mo_du_an(f2)
        may_chu.ghi_mo_du_an(self.td / 'rieng_may_nay.pabt')             # file trên ổ máy này: không ghi
        self.assertEqual(len(may_chu.ds_gan_day(p)), 2)
        may_chu.dang_xuat()
        self.assertIsNone(may_chu.du_an_cuoi())
        # "máy khác": cùng thư mục máy chủ, đăng nhập lại -> dự án cuối là DA2 (đường dẫn tương đối với máy chủ)
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        self.assertEqual(may_chu.du_an_cuoi(), f2)
        f2.unlink()
        self.assertEqual(may_chu.du_an_cuoi(), f1)                    # file đã xóa: lấy dự án kế tiếp
        ds = may_chu.ds_du_an()
        self.assertEqual([x['ten'] for x in ds], ['Dự án DA1'])
        self.assertEqual(ds[0]['dang_mo'], '')

    def test_mang_ve_dua_len(self):
        f = self.du_an('DA1')
        qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        may_chu.them_nguoi_dung(qt, 'nv1', 'Nhân viên 1', 'abc123')
        bs = may_chu.lay_ve(f)
        self.assertTrue(bs.exists() and bs.parent == may_chu.thu_muc_offline())
        self.assertEqual(may_chu.ds_du_an()[0]['lay_ve']['tai_khoan'], 'quantri')
        nv = may_chu.dang_nhap(self.goc, 'nv1', 'abc123')
        with self.assertRaisesRegex(LoiMayChu, 'mang về'):
            may_chu.lay_ve(f, nv)                                         # người khác đang mang về
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        con = csdl.mo(bs)                                                 # sửa offline
        with con:
            con.execute("UPDATE du_an SET ten = 'Đã sửa offline' WHERE id = 1")
        con.close()
        may_chu.dua_len(bs)
        self.assertFalse(bs.exists())
        self.assertEqual(may_chu.ds_lay_ve_cuc_bo(), [])
        con = csdl.mo(f, chi_doc=True)
        self.assertEqual(con.execute('SELECT ten FROM du_an').fetchone()[0], 'Đã sửa offline')
        con.close()
        self.assertEqual(len(list((self.goc / 'SaoLuu').glob('DA1_*.pabt'))), 1)
        self.assertIsNone(may_chu.ds_du_an()[0]['lay_ve'])

    def test_xung_dot_va_huy(self):
        f = self.du_an('DA1')
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        bs = may_chu.lay_ve(f)
        st = f.stat()
        os.utime(f, (st.st_atime, st.st_mtime + 100))                    # bản trên máy chủ bị sửa sau lúc mang về
        with self.assertRaisesRegex(LoiMayChu, 'XUNG ĐỘT'):
            may_chu.dua_len(bs)
        self.assertTrue(bs.exists())
        may_chu.dua_len(bs, ep=True)
        self.assertEqual(len(list((self.goc / 'SaoLuu').glob('*.pabt'))), 1)
        bs = may_chu.lay_ve(f)
        may_chu.huy_lay_ve(bs)
        self.assertFalse(bs.exists())
        self.assertIsNone(may_chu.ds_du_an()[0]['lay_ve'])
        with self.assertRaises(LoiMayChu):
            may_chu.huy_lay_ve(bs)

    def test_lay_ve_khi_dang_mo(self):
        f = self.du_an('DA1')
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        k = khoa.KhoaFile(f)
        k._ghi()
        k.p.write_text(k.p.read_text(encoding='utf-8').replace(f'"pid": {os.getpid()}', '"pid": 1'), encoding='utf-8')
        self.assertTrue(may_chu.ds_du_an()[0]['dang_mo'])
        with self.assertRaisesRegex(LoiMayChu, 'đang được sửa'):
            may_chu.lay_ve(f)


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestHopMayChu(_Nen):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_dang_nhap_thiet_lap(self):
        from pabt.man_hinh_may_chu import HopDangNhap, HopThietLap
        may_chu.ghi_cau_hinh(may_chu=str(self.goc))
        h = HopDangNhap()
        h.im_lang = True
        self.assertIsNone(h.dang_nhap('quantri', 'sai123'))
        self.assertIn('Sai', h.lb.text())
        self.assertIsNotNone(h.dang_nhap('quantri', 'matkhau1'))
        h2 = HopDangNhap()
        self.assertEqual(h2.o_tk.text(), 'quantri')                       # nhớ tài khoản lần trước
        h2.lam_offline()
        self.assertTrue(h2.offline)
        # thiết lập máy chủ mới ở thư mục khác
        moi = self.td / 'MayChu2'
        moi.mkdir()
        t = HopThietLap(None, str(moi))
        t.im_lang = True
        self.assertEqual(t.kiem_tra(), 'moi')
        t.o_qt_tk.setText('admin')
        t.o_qt_mk.setText('abcdef')
        t.o_qt_mk2.setText('abcdeX')
        self.assertFalse(t.khoi_tao())                                     # nhập lại không khớp
        t.o_qt_mk2.setText('abcdef')
        self.assertTrue(t.khoi_tao())
        self.assertEqual(may_chu.doc_cau_hinh()['may_chu'], str(moi))
        t2 = HopThietLap(None, str(self.goc))
        t2.im_lang = True
        self.assertEqual(t2.kiem_tra(), 'co')
        self.assertTrue(t2.ket_noi())
        self.assertTrue(t2.bo_may_chu())
        self.assertNotIn('may_chu', may_chu.doc_cau_hinh())

    def test_tai_khoan_du_an(self):
        from pabt.man_hinh_may_chu import HopDuAnMayChu, HopTaiKhoan
        f = self.du_an('DA1')
        may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        h = HopTaiKhoan()
        h.im_lang = True
        self.assertTrue(h.them('nv1', 'Nhân viên', 'abc123', may_chu.NGUOI_DUNG, ''))
        self.assertFalse(h.them('nv1', 'Trùng', 'abc123', may_chu.NGUOI_DUNG, ''))
        self.assertEqual(h.bang.rowCount(), 2)
        r = next(i for i, u in enumerate(h.ds) if u['tai_khoan'] == 'nv1')
        h.bang.selectRow(r)
        self.assertTrue(h.khoa_mo())
        self.assertTrue(next(u for u in h.ds if u['tai_khoan'] == 'nv1')['khoa'])
        h.bang.selectRow(next(i for i, u in enumerate(h.ds) if u['tai_khoan'] == 'nv1'))
        self.assertTrue(h.dat_lai('moimk1'))
        may_chu.dang_nhap(self.goc, 'nv1', 'moimk1')
        d = HopDuAnMayChu()
        d.im_lang = True
        self.assertEqual(d.bang.rowCount(), 1)
        bs = d.mang_ve(d.ds[0])
        self.assertEqual(d.mo_file, bs)
        d2 = HopDuAnMayChu()
        d2.im_lang = True
        self.assertEqual(d2.bang_off.rowCount(), 1)
        self.assertEqual(d2.dua_len(d2.ds_off[0]), f)
        self.assertEqual(d2.bang_off.rowCount(), 0)

    def test_cua_so_chinh(self):
        from pabt.app import CuaSoChinh
        f = self.du_an('DA1')
        may_chu.ghi_cau_hinh(may_chu=str(self.td / 'khong_co'))
        w = CuaSoChinh()
        self.assertEqual(w.khoi_dong_may_chu(mo_lai=False), 'mat_ket_noi')   # không có máy chủ: vẫn làm offline
        self.assertIn('Offline', w.nut_tk.text())
        may_chu.ghi_cau_hinh(may_chu='')
        self.assertEqual(w.khoi_dong_may_chu(), 'khong_dung')
        # máy chủ trả lời chậm (mạng chập chờn): kiểm tra chạy ở luồng nền, cửa sổ vẫn xử lý sự kiện trong lúc chờ
        import time
        from unittest import mock
        from PySide6.QtCore import QTimer
        may_chu.ghi_cau_hinh(may_chu=str(self.td / 'cham'))
        da_ve = []
        QTimer.singleShot(100, lambda: da_ve.append(True))
        with mock.patch.object(may_chu, 'ket_noi_duoc', side_effect=lambda goc, cho=4.0: time.sleep(0.6) or False):
            self.assertEqual(w.khoi_dong_may_chu(mo_lai=False), 'mat_ket_noi')
        self.assertEqual(da_ve, [True])
        may_chu.ghi_cau_hinh(may_chu='')
        p = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        may_chu.ghi_mo_du_an(f)
        self.assertEqual(w.sau_dang_nhap(), f)                           # đăng nhập: tự mở lại dự án đang làm
        self.assertEqual(w.file, f)
        self.assertIn(p.ten_hien, w.windowTitle())
        self.assertIn('Tài khoản', w.nut_tk.text())
        w._menu_tai_khoan()
        self.assertTrue(any('Quản lý tài khoản' in a.text() for a in w.nut_tk.menu().actions()))
        w.dang_xuat(xac_nhan=True)
        self.assertIsNone(may_chu.PHIEN)
        self.assertIsNone(w.con)
        w.close()
        w2 = CuaSoChinh(menu_trai=True)                               # 0.9.3: menu dọc bên trái là giao diện chính
        import pabt                                                     # chỉ nhãn bản thử nghiệm, không còn "menu thử nghiệm"
        self.assertEqual(w2.windowTitle().count('THỬ NGHIỆM'), 1 if pabt.BAN_THU_NGHIEM else 0)
        w2.close()


if __name__ == '__main__':
    unittest.main()
