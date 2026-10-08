"""Kiểm thử giai đoạn 4: sửa hồ sơ kiểm kê (hộ, thửa, gộp, chuyển, xóa), khóa file, mở chỉ xem."""
from __future__ import annotations
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from pabt import csdl, ho_so, khoa, nhap_tho
from pabt.lap_pa import LoiNhap
from tests.test_nhap_tho import _don_gian, _ghi

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        self.p = self.td / 'da.pabt'
        nhap_tho.nhap(xl, self.p, 'Dự án thử, xã Bàu Hàm')
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def dem(self, bang, dk='1', *ts):
        return self.con.execute(f'SELECT COUNT(*) FROM {bang} WHERE {dk}', ts).fetchone()[0]


class TestHoSo(CoSo):
    def test_them_ho(self):
        ma = ho_so.luu_ho(self.con, None, dict(ho_ten='  Trần   Văn Mới ', so_cccd='0123 456', dia_chi='ấp 1'),
                          [dict(so_to='71', so_thua='5', loai_dat=' ont + cln', dt_thu_hoi='1.070'),
                           dict(so_to='71', so_thua='6', loai_dat='CLN', dt_thu_hoi='143,8'), dict()])
        self.assertEqual(ma, 6)
        ho = ho_so.doc_ho(self.con, ma)
        self.assertEqual((ho['ho_ten'], ho['so_cccd'], ho['thu_tu'], ho['trang_thai']), ('Trần Văn Mới', '0123456', 6, 'Chưa lập phương án'))
        self.assertEqual([(t['loai_dat'], t['dt_thu_hoi'], t['thu_tu']) for t in ho['thua']],
                         [('ONT+CLN', '1070', 1), ('CLN', '143.8', 2)])
        self.assertEqual(self.dem('nhat_ky', "viec = 'Thêm hộ'"), 1)

    def test_sua_ho_them_sua_xoa_thua(self):
        ho = ho_so.doc_ho(self.con, 1)                       # Nguyễn Văn A: 2 thửa
        self.assertEqual(len(ho['thua']), 2)
        t1, t2 = ho['thua']
        self.con.execute("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, dien_tich) VALUES (1, ?, 'LUK', '50')", (t2['ma_thua'],))
        self.con.commit()
        ds = [dict(t1, dt_thu_hoi='200,5'), dict(so_to='40', so_thua='9', loai_dat='BHK', dt_thu_hoi='10')]
        ho_so.luu_ho(self.con, 1, dict(ho, dien_thoai='0909'), ds)
        ho = ho_so.doc_ho(self.con, 1)
        self.assertEqual([(t['so_to'], t['so_thua'], t['dt_thu_hoi']) for t in ho['thua']], [('35', '394', '200.5'), ('40', '9', '10')])
        self.assertEqual(ho['thua'][0]['ma_thua'], t1['ma_thua'])             # giữ mã thửa khi sửa
        self.assertEqual(ho['dien_thoai'], '0909')
        self.assertIsNone(self.con.execute('SELECT ma_thua FROM ct_dat WHERE ma_ho = 1').fetchone()[0])

    def test_kiem_tra_loi(self):
        for tt, ds, chu in ((dict(ho_ten=' '), [], 'Họ và tên'),
                            (dict(ho_ten='A', so_cccd='12a'), [], 'CCCD'),
                            (dict(ho_ten='A'), [dict(so_to='1', so_thua='2', dt_thu_hoi='abc')], 'không phải là số'),
                            (dict(ho_ten='A'), [dict(so_to='1', so_thua='2', dt_thu_hoi='-3')], 'nhỏ hơn'),
                            (dict(ho_ten='A'), [dict(loai_dat='ONT', dt_thu_hoi='3')], 'số tờ'),
                            (dict(ho_ten='A'), [dict(so_to='1', so_thua='2', loai_dat='ONT')] * 2, 'hai lần')):
            with self.assertRaises(LoiNhap) as cm:
                ho_so.luu_ho(self.con, None, tt, ds)
            self.assertIn(chu, str(cm.exception))
        self.assertEqual(self.dem('ho'), 5)
        # cùng tờ, thửa nhưng khác loại đất (đã tách) thì được
        ho_so.luu_ho(self.con, None, dict(ho_ten='A'), [dict(so_to='1', so_thua='2', loai_dat='ONT', dt_thu_hoi='100'),
                                                        dict(so_to='1', so_thua='2', loai_dat='CLN', dt_thu_hoi='50')])

    def test_gop_ho(self):
        # hộ 3 (Lê C) và 4 (Phạm D) cùng thửa 99 tờ 72; hộ 4 có phương án
        self.assertIn('hộ 4 - Phạm D', ho_so.thua_trung_ho_khac(self.con, 3)[0])
        self.con.execute("UPDATE ho SET so_cccd = '' , dien_thoai = '' WHERE ma_ho = 3")
        self.con.execute("UPDATE ho SET dien_thoai = '0988', ghi_chu = 'hộ D' WHERE ma_ho = 4")
        self.con.execute("INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ten) VALUES (2, 3, 1, 'Nhà C'), (2, 4, 1, 'Nhà D')")
        self.con.execute("INSERT INTO tong_excel (ma_ho, tong) VALUES (4, '100')")
        self.con.commit()
        tb = ho_so.gop_ho(self.con, 3, 4)
        self.assertIn('vào hộ 3', tb)
        self.assertEqual(self.dem('ho', 'ma_ho = 4'), 0)
        self.assertEqual(self.dem('thua', 'ma_ho = 3'), 2)
        self.assertEqual([tuple(r) for r in self.con.execute('SELECT ten, thu_tu FROM ct_khoan WHERE ma_ho = 3 ORDER BY thu_tu')],
                         [('Nhà C', 1), ('Nhà D', 2)])
        ho = ho_so.doc_ho(self.con, 3)
        self.assertEqual((ho['dien_thoai'], ho['ghi_chu']), ('0988', 'hộ D'))
        self.assertIsNotNone(ho['luu_luc'])
        self.assertEqual(self.dem('tong_excel'), 0)
        self.assertEqual([r[0] for r in self.con.execute('SELECT thu_tu FROM ho ORDER BY thu_tu')], [1, 2, 3, 4])
        self.assertEqual(ho_so.thua_trung_ho_khac(self.con, 3), [])
        with self.assertRaises(LoiNhap):
            ho_so.gop_ho(self.con, 3, 3)

    def test_chuyen_thua_va_xoa_ho(self):
        mt = self.con.execute("SELECT ma_thua FROM thua WHERE ma_ho = 1 AND so_thua = '12'").fetchone()[0]
        self.con.execute("INSERT INTO ct_dat (ma_ho, ma_thua, dien_tich) VALUES (1, ?, '50')", (mt,))
        self.con.commit()
        tb = ho_so.chuyen_thua(self.con, mt, 2)
        self.assertIn('kèm 1 dòng', tb)
        self.assertEqual(self.dem('thua', 'ma_ho = 2'), 2)
        self.assertEqual(self.dem('ct_dat', 'ma_ho = 2'), 1)
        with self.assertRaises(LoiNhap):
            ho_so.chuyen_thua(self.con, mt, 2)
        ho_so.xoa_ho(self.con, 2)
        self.assertEqual((self.dem('ho'), self.dem('thua', 'ma_ho = 2'), self.dem('ct_dat')), (4, 0, 0))
        self.assertEqual(ho_so.goi_y_gop(self.con, 1)[0][0], 3)


class TestKhoa(CoSo):
    def test_hai_may(self):
        a, b = khoa.KhoaFile(self.p), khoa.KhoaFile(self.p)
        b.cua_toi = dict(b.cua_toi, may='MAY-KHAC')
        self.assertEqual(a.lay(), (True, None))
        self.assertTrue(a.p.exists())
        ok, k = b.lay()
        self.assertFalse(ok)
        self.assertIn('máy "', khoa.mo_ta(k))
        self.assertTrue(a.lam_moi())
        self.assertTrue(b.lay(ep=True)[0])                  # máy kia vẫn mở để sửa
        self.assertFalse(a.lam_moi())                       # máy này được báo
        a.nha()
        self.assertTrue(b.p.exists())                       # không xóa khóa của người khác
        b.nha()
        self.assertFalse(b.p.exists())

    def test_khoa_het_han(self):
        a, b = khoa.KhoaFile(self.p), khoa.KhoaFile(self.p)
        b.cua_toi = dict(b.cua_toi, pid=-1)
        b.lay()
        self.assertIsNotNone(a.nguoi_khac())
        os.utime(b.p)
        k = b.doc()
        k['cap_nhat'] = time.time() - khoa.HET_HAN - 5
        b.p.write_text(__import__('json').dumps(k), encoding='utf-8')
        self.assertIsNone(a.nguoi_khac())

    def test_mo_chi_xem(self):
        con = csdl.mo(self.p, chi_doc=True)
        try:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 5)
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("UPDATE ho SET ho_ten = 'x'")
        finally:
            con.close()


@unittest.skipUnless(CO_QT, 'không có PySide6')
class TestManHinhHoSo(CoSo):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_hop_ho_so(self):
        from pabt.man_hinh_ho_so import HopHoSo
        d = HopHoSo(self.con, None)
        d.o['ho_ten'].setText('Hộ thêm từ màn hình')
        r = d.them_dong(dict(so_to='75', so_thua='1', loai_dat='ONT+CLN', dt_thu_hoi='300'))
        self.assertEqual(d.tach_dong(r), 2)
        d.bang.item(1, 3).setText('120,5')
        self.assertTrue(d.co_thay_doi())
        self.assertTrue(d.luu())
        ho = ho_so.doc_ho(self.con, d.ma_ho)
        self.assertEqual([(t['loai_dat'], t['dt_thu_hoi']) for t in ho['thua']], [('ONT', '300'), ('CLN', '120.5')])
        self.assertFalse(d.co_thay_doi())
        self.assertIn('vào hộ', d.gop_ho(ma_ho_bo=5, xac_nhan=True))
        self.assertEqual(d.bang.rowCount(), 2)               # hộ 5 không có thửa
        self.assertIn('sang hộ 1', d.chuyen_thua(0, ma_ho_moi=1))
        self.assertIn('Đã xóa hộ', d.xoa_ho(xac_nhan=True))
        self.assertEqual(self.dem('ho'), 4)

    def test_bang_thua_gon(self):
        """0.9.12: cột vị trí ẩn (vẫn giữ dữ liệu khi lưu), nguồn gốc dài không làm dòng thửa cao quá mức,
        thao tác thửa / hộ trong nút "+ Thêm thửa" và menu "Thao tác khác"."""
        from pabt.man_hinh_ho_so import CAO_DONG_TOI_DA, HopHoSo
        with self.con:
            self.con.execute("UPDATE thua SET vi_tri = 'Vị trí 2', nguon_goc = ? WHERE ma_ho = 1", ('Giao khoán năm 2002. ' * 60,))
        d = HopHoSo(self.con, 1)
        d.resize(1000, 640)
        cot = [k for k, _ in ho_so.TRUONG_THUA]
        self.assertTrue(d.bang.isColumnHidden(cot.index('vi_tri')))
        self.assertFalse(d.bang.isColumnHidden(cot.index('nguon_goc')))
        self.assertTrue(all(d.bang.rowHeight(r) <= CAO_DONG_TOI_DA for r in range(d.bang.rowCount())))
        self.assertIn('Gộp hộ khác vào hộ này…', d.nut)
        self.assertNotIn('vi_tri', [d.bang.horizontalHeaderItem(c).text() for c in range(d.bang.columnCount())
                                     if not d.bang.isColumnHidden(c)])
        d.bang.item(0, cot.index('nguon_goc')).setText('Nguồn gốc mới')
        self.assertTrue(d.luu())
        t = ho_so.doc_ho(self.con, 1)['thua'][0]
        self.assertEqual((t['nguon_goc'], t['vi_tri']), ('Nguồn gốc mới', 'Vị trí 2'))
        d.them_dong()
        self.assertEqual(d.bang.rowCount(), 3)

    def test_cua_so_chi_xem_va_khoa(self):
        from pabt import app as ud
        self.con.close()
        k = khoa.KhoaFile(self.p)
        k.cua_toi = dict(k.cua_toi, may='MAY-KHAC')
        k.lay()
        w = ud.CuaSoChinh()
        w.mo(str(self.p), chi_doc=True)
        self.assertTrue(w.chi_doc)
        self.assertFalse(w.lenh['Hồ sơ hộ…'].isEnabled())
        self.assertIn('CHỈ XEM', w.windowTitle())
        self.assertEqual(w.mo_hinh.rowCount(), 5)
        w.mo(str(self.p), chi_doc=False)                     # vẫn mở để sửa: lấy khóa
        self.assertTrue(w.lenh['Hồ sơ hộ…'].isEnabled())
        self.assertTrue(w.khoa.la_cua_toi(w.khoa.doc()))
        self.assertIsNotNone(w.mo_ho_so(1, cho=False))
        w.close()
        self.assertFalse(k.p.exists())                       # đóng thì nhả khóa
        self.con = csdl.mo(self.p)


if __name__ == '__main__':
    unittest.main()
