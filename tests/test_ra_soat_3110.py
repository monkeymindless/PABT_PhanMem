"""Rà soát 31/10/2026 (10 agent): làm tròn giá như Excel, số PA lần 1 đồng bộ ho / pa_lan, số biên bản niêm yết, timeout máy nhận
Wi-Fi. Số liệu GIẢ LẬP."""
from __future__ import annotations

import unittest
from pathlib import Path

from pabt import csdl, du_thao, gia_dat_nq28, lan_pa, nhan_wifi, nhap_don_gia, quan_ly
from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class TestLamTronNhuExcel(unittest.TestCase):
    def test_nua_len(self):
        self.assertEqual(gia_dat_nq28._so_gia(2.5), 3)          # round() của Python: 2
        self.assertEqual(gia_dat_nq28._so_gia(1234.5), 1235)
        self.assertEqual(gia_dat_nq28._so_gia('1.234,5'), 1235)
        self.assertEqual(gia_dat_nq28._so_gia(''), 0)
        self.assertEqual(nhap_don_gia.doc_gia('1.000,5'), 1001)
        self.assertEqual(nhap_don_gia.doc_gia('1.480.500'), 1480500)


class _Co(CoSo):
    def tearDown(self):
        self.doCleanups()
        super().tearDown()

    def _con(self, so_ho=2):
        con = csdl.mo(str(_du_an(self.td, so_ho)))
        self.addCleanup(con.close)
        return con


class TestSoPaHaiNoi(_Co):
    def test_dat_so_pa_ghi_ca_lan_1(self):
        con = self._con()
        lan_pa.sua_lan(con, 1, 1, so_pa='01')                   # tạo dòng pa_lan lần 1
        quan_ly.dat_so_pa(con, [(1, '05', '20/10/2026')])
        r = con.execute('SELECT so_pa, ngay_pa FROM pa_lan WHERE ma_ho = 1 AND lan = 1').fetchone()
        h = con.execute('SELECT so_pa, ngay_pa FROM ho WHERE ma_ho = 1').fetchone()
        self.assertEqual(tuple(r), tuple(h))
        self.assertEqual(r[0], '05')
        self.assertEqual(lan_pa.ds_lan(con, 1)[0].so_pa, '05')


class TestSoBienBan(_Co):
    def test_ghi_va_doc(self):
        con = self._con()
        dot = du_thao.tao_dot(con, 'Đợt 1', '01/10/2026', 'Nhà văn hóa')
        self.assertEqual(du_thao.so_bien_ban(con, dot), ('', '', ''))
        du_thao.dat_ngay_hop(con, dot, '15/10/2026', ' 12/BB ', '13/BB')
        bd, kt, hop = du_thao.so_bien_ban(con, dot)
        self.assertEqual((bd, kt), ('12/BB', '13/BB'))
        self.assertTrue(hop)
        du_thao.dat_ngay_hop(con, dot, '16/10/2026')            # không truyền số biên bản: giữ nguyên
        self.assertEqual(du_thao.so_bien_ban(con, dot)[:2], ('12/BB', '13/BB'))


class TestSuaTuDongTonTrongKhoa(_Co):
    """A1: Sửa tự động (Kiểm tra lỗi) không đổi chữ của lần PA đã phê duyệt / hộ không nhận việc."""

    def test_khong_sua_lan_khoa_va_ho_khong_nhan(self):
        from pabt import kiem_loi, theo_doi
        from pabt.lap_pa import BoSoan
        con = self._con(3)
        for ma in (1, 2, 3):
            bo = BoSoan(con, ma)
            bo.them_tu_danh_muc(2, bo.dm.muc[2][0])
            bo.luu()
        with con:
            con.execute("UPDATE ct_khoan SET ten = '  nhà   tạm  ', ghi_chu = 'a  b'")
            con.execute("UPDATE ho SET dia_chi = 'Ấp  1'")
        qd = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, [1])                      # hộ 1: lần 1 đã phê duyệt -> khóa
        self.assertTrue(lan_pa.dang_khoa(con, 1, 1))
        con._ho_nhan_viec = frozenset({1, 2})                      # bản offline theo hộ: hộ 3 không nhận
        try:
            kiem_loi.sua_tu_dong(con)
        finally:
            con._ho_nhan_viec = None
        ten = dict(con.execute('SELECT ma_ho, ten FROM ct_khoan').fetchall())
        self.assertEqual(ten[1], '  nhà   tạm  ')                 # lần đã duyệt: giữ nguyên
        self.assertEqual(ten[2], 'Nhà tạm')                         # hộ đang làm, lần chưa khóa: sửa
        self.assertEqual(ten[3], '  nhà   tạm  ')                 # hộ không nhận: không đụng
        dc = dict(con.execute('SELECT ma_ho, dia_chi FROM ho').fetchall())
        self.assertEqual((dc[2], dc[3]), ('Ấp 1', 'Ấp  1'))


class TestKhoaNhieuMay(unittest.TestCase):
    """A2: khóa file - đồng hồ hai máy lệch, hai máy lấy khóa cùng lúc."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.f = Path(self.td.name) / 'DA.larc'
        self.f.write_bytes(b'x')

    def _may(self, ten):
        from pabt import khoa
        k = khoa.KhoaFile(self.f)
        k.cua_toi = dict(may=ten, nguoi='u', pid=1)
        return k

    def test_dong_ho_lech(self):
        import json
        import os
        import time
        from pabt import khoa
        a, b = self._may('A'), self._may('B')
        self.assertEqual(a.lay(), (True, None))
        k = a.doc()
        k['cap_nhat'] = time.time() - 10 * khoa.HET_HAN          # đồng hồ máy A chậm: giờ ghi trong khóa đã "cũ"
        a.p.write_text(json.dumps(k), encoding='utf-8')
        self.assertIsNotNone(b.nguoi_khac())                       # file khóa vừa được sửa: vẫn còn hiệu lực
        k['cap_nhat'] = time.time() + 10 * khoa.HET_HAN          # đồng hồ máy A nhanh: giờ ở tương lai
        a.p.write_text(json.dumps(k), encoding='utf-8')
        cu = time.time() - 4 * khoa.HET_HAN
        os.utime(a.p, (cu, cu))                                  # nhưng file khóa không ai sửa đã lâu: máy A đã tắt
        self.assertIsNone(b.nguoi_khac())

    def test_hai_may_khong_cung_lay(self):
        a, b = self._may('A'), self._may('B')
        self.assertEqual(a.lay(), (True, None))
        ok, k = b.lay()
        self.assertFalse(ok)
        self.assertEqual(k['may'], 'A')
        ok, _ = b.lay(ep=True)                                      # "Vẫn mở để sửa"
        self.assertTrue(ok)
        self.assertFalse(a.lam_moi())                               # máy A mất khóa -> app chuyển chỉ xem


class TestKiemToanQuyetDinh(_Co):
    """A4: nhật ký kiểm toán ghi thay đổi tiền quyết định / chi trả của hộ."""

    def test_ghi_vet_qd_ho(self):
        from pabt import kiem_toan, theo_doi
        con = self._con(2)
        self.assertTrue(kiem_toan.gan(con))
        qd = theo_doi.luu_qd(con, None, '05/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, [1])
        with con:
            con.execute("UPDATE qd_ho SET da_chi_tra = 1, chi_tra_so_tien = '1000' WHERE ma_ho = 1")
        r = con.execute("SELECT hanh_dong, truong, moi, doi_tuong FROM audit_logs WHERE bang = 'qd_ho' ORDER BY id").fetchall()
        self.assertEqual(r[0][0], 'them')
        sua = {x[1]: x[2] for x in r if x[0] == 'sua'}
        self.assertEqual(sua.get('chi_tra_so_tien'), '1000')
        self.assertIn('05/QĐ-UBND', r[-1][3])


class TestBanSaoBoAnhBanDo(_Co):
    """A5: sao lưu tự động / mốc khôi phục không chép ảnh nền bản đồ đã lưu trong dự án."""

    def test_sao_luu_va_moc(self):
        from pabt import ban_do_luu, co_may_thoi_gian
        from tests.test_ban_do_pa4 import _png
        con = self._con(2)
        anh = _png() + b'\x00' * 20000
        ban_do_luu.luu_o(con, [('esri', 17, x, 1, anh) for x in range(30)])
        ban_do_luu.luu_lop(con, [('a.kml', b'<kml/>')])
        f = con.execute('PRAGMA database_list').fetchone()[2]
        for p in (csdl.sao_luu_tu_dong(con, f), co_may_thoi_gian.chup_moc(con, f, bat_buoc=True).file):
            c = csdl.mo(p, chi_doc=True)                    # 1.0.55: bản sao lưu / mốc nén - mở trong suốt
            try:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM ban_do_o').fetchone()[0], 0)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM ban_do_lop').fetchone()[0], 1)     # lớp KML (nhỏ) giữ
            finally:
                c.close()
        self.assertEqual(ban_do_luu.tom_tat(con)['o'], 30)                                          # file dự án không đổi


class TestChanHoNhanViecCSDL(_Co):
    """Trigger tạm chặn ghi hộ không nhận việc (bản offline theo hộ) - lớp chặn cuối ở tầng CSDL."""

    def test_chan(self):
        import sqlite3
        from pabt.lap_pa import TB_HO_KHONG_NHAN, gan_chan_ho_nhan_viec
        con = self._con(3)
        self.assertGreater(gan_chan_ho_nhan_viec(con, [1]), 0)
        with con:
            con.execute("UPDATE ho SET ghi_chu = 'được' WHERE ma_ho = 1")
        for cau in ("UPDATE ho SET ghi_chu = 'x' WHERE ma_ho = 2", 'DELETE FROM thua WHERE ma_ho = 2',
                    'UPDATE thua SET ma_ho = 2 WHERE ma_ho = 1',                  # chuyển thửa sang hộ không nhận
                    "INSERT INTO ho (ma_ho, ho_ten) VALUES (99, 'Hộ mới')"):
            with self.assertRaises(sqlite3.IntegrityError) as e, con:
                con.execute(cau)
            self.assertIn('không nằm trong danh sách nhận việc', str(e.exception))
        self.assertTrue(TB_HO_KHONG_NHAN)
        self.assertEqual(con.execute("SELECT ghi_chu FROM ho WHERE ma_ho = 1").fetchone()[0], 'được')
        self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 3)
        with con:                                                              # bảng không có ma_ho vẫn ghi được
            con.execute("INSERT INTO nhat_ky (thoi_gian, may, nguoi_dung, viec, chi_tiet) VALUES ('t','m','n','v','')")
        self.assertEqual(con.execute('SELECT COUNT(*) FROM nhat_ky WHERE viec = ?', ('v',)).fetchone()[0], 1)


class TestGhiToiThieu(_Co):
    """Cờ phiên bản phần mềm tối thiểu được ghi file dự án."""

    def test_csdl(self):
        self.assertEqual(csdl.so_phien_ban('1.0.40'), (1, 0, 40))
        self.assertEqual(csdl.so_phien_ban(''), ())
        con = self._con(2)                                                 # csdl.mo đã ghi cờ
        self.assertEqual(csdl.phan_mem_ghi_toi_thieu(con), csdl.GHI_TOI_THIEU)
        self.assertFalse(csdl.dat_ghi_toi_thieu(con))                       # đã có: không ghi lại
        self.assertEqual(csdl.qua_cu_de_ghi(con, csdl.GHI_TOI_THIEU), '')
        self.assertEqual(csdl.qua_cu_de_ghi(con, '1.0.40'), csdl.GHI_TOI_THIEU)
        self.assertEqual(csdl.qua_cu_de_ghi(con, '9.9.9'), '')
        with con:
            con.execute('DELETE FROM cai_dat WHERE ma = ?', (csdl.KHOA_GHI_TOI_THIEU,))
        self.assertTrue(csdl.dat_ghi_toi_thieu(con))                        # chưa có: ghi
        self.assertEqual(csdl.phan_mem_ghi_toi_thieu(con), csdl.GHI_TOI_THIEU)
        with con:
            csdl.ghi_cai_dat(con, csdl.KHOA_GHI_TOI_THIEU, '9.0.0')
        self.assertFalse(csdl.dat_ghi_toi_thieu(con))                       # không hạ số của bản mới hơn

    def test_khong_ghi_bo_don_gia(self):
        import shutil
        import sqlite3
        from pabt import tai_nguyen
        goc = tai_nguyen('bo_don_gia.sqlite')
        if not goc.is_file():
            self.skipTest('không có bộ đơn giá đóng gói')
        p = Path(self.td) / 'bo_don_gia.sqlite'
        shutil.copy2(goc, p)
        con = sqlite3.connect(str(p))
        self.addCleanup(con.close)
        self.assertFalse(csdl.dat_ghi_toi_thieu(con))
        self.assertEqual(csdl.phan_mem_ghi_toi_thieu(con), '')

    def test_ban_cu_mo_chi_xem(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest('không có Qt')
        QApplication.instance() or QApplication([])
        from pabt import app as ud
        f = str(_du_an(self.td, 2))
        c = csdl.mo(f)
        with c:
            csdl.ghi_cai_dat(c, csdl.KHOA_GHI_TOI_THIEU, '9.0.0')
        c.close()
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(lambda: (w.dong_du_an(), w.close(), w.deleteLater()))
        w.mo(f)
        self.assertTrue(w.chi_doc)
        self.assertIsNone(w.khoa)


class TestTimeoutWifi(unittest.TestCase):
    def test_co_timeout(self):
        xl = nhan_wifi._tao_xu_ly(object.__new__(nhan_wifi.MayNhan))
        self.assertTrue(xl.timeout and xl.timeout > 0)


if __name__ == '__main__':
    unittest.main()
