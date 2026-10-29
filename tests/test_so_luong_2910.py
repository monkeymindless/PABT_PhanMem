"""29/10/2026 (người dùng): số lượng / diện tích gõ 28,35 bị làm tròn thành 28,4 -> sai thành tiền. Số gõ trực tiếp giữ nguyên (tối
đa 4 chữ số lẻ), kết quả công thức làm tròn 2 chữ số (ĐVT ha 4). Dữ liệu giả lập."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import chinh_sach, csdl, lan_pa, lap_pa, nghiep_vu
from pabt.tien import D, so_luong_vn


class TestDocSoLuong(unittest.TestCase):
    def test_so_go_truc_tiep_giu_nguyen(self):
        for chu, dvt, kq in (('28,35', 'm²', '28.35'), ('28,35', 'm2', '28.35'), ('1.250,75', 'm²', '1250.75'),
                             ('35,155', 'm3', '35.155'), ('0,0325', 'ha', '0.0325'), ('12', 'cái', '12'),
                             ('2,123456', 'm²', '2.1235')):
            self.assertEqual(lap_pa.doc_so_luong(chu, dvt), D(kq), chu)

    def test_cong_thuc_lam_tron_hai_chu_so(self):
        self.assertEqual(lap_pa.doc_so_luong('=4,5*6,3', 'm²'), D('28.35'))     # trước đây 28,4
        self.assertEqual(lap_pa.doc_so_luong('10/3', 'm²'), D('3.33'))
        self.assertEqual(lap_pa.doc_so_luong('=1,25*1,25', 'ha'), D('1.5625'))  # ha: 4 chữ số

    def test_thanh_tien_dung_so_luong_da_go(self):
        sl = lap_pa.doc_so_luong('28,35', 'm²')
        self.assertEqual(nghiep_vu.thanh_tien_khoan(sl, D(4_150_000), lamtron=0), D(117_652_500))
        self.assertEqual(nghiep_vu.thanh_tien_dat(lap_pa.doc_so_luong('28,35', 'm²', 'Diện tích'), D(2_000_000), lamtron=0),
                         D(56_700_000))

    def test_hien_thi(self):
        self.assertEqual(so_luong_vn(D('28.35'), 2), '28,35')
        self.assertEqual(so_luong_vn(D('28.35'), 1), '28,35')                     # mục khác: không cắt chữ số đã nhập
        self.assertEqual(so_luong_vn(D('28'), 2), '28,00')

    def test_dao_tao_khong_lam_tron_dien_tich(self):
        class _M:
            ma, ten, can_cu = 'CS9', 'Hỗ trợ đào tạo, chuyển đổi nghề', ''
        d = chinh_sach.dong_dao_tao(_M(), 'Thửa đất số 5', D('128.35'), D(100_000), D('1.5'))
        self.assertEqual(d.so_luong, D('128.35'))


class TestTinhLaiKhiMoDuAn(unittest.TestCase):
    """Mở dự án: dòng nhập bằng công thức tính lại theo 2 chữ số lẻ; dòng gõ số thường giữ nguyên; lần đã phê duyệt giữ nguyên."""
    def setUp(self):
        from tests.test_toc_do import _du_an
        self.td = tempfile.TemporaryDirectory()
        self.con = csdl.mo(_du_an(Path(self.td.name), 3))
        c = self.con
        self.ma = [r[0] for r in c.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        with c:
            them = "INSERT INTO ct_khoan (muc, ma_ho, ten, dvt, so_luong, don_gia, cong_thuc) VALUES (2, ?, ?, ?, ?, '4150000', ?)"
            c.execute(them, (self.ma[0], 'Nhà A', 'm²', '28.4', '=4,5*6,3'))      # lưu cũ: làm tròn 1 chữ số
            c.execute(them, (self.ma[0], 'Sân', 'm²', '12.3', '=3*4,1'))          # công thức ra đúng 12,3: không đổi
            c.execute(them, (self.ma[0], 'Nhà B', 'm²', '28.4', ''))              # gõ số: không đổi
            c.execute(them, (self.ma[1], 'Ao', 'ha', '0.2469', '=0,12345*2'))     # ha 4 chữ số: không đổi
            c.execute(them, (self.ma[2], 'Nhà C', 'm²', '28.4', '=4,5*6,3'))      # hộ có lần đã phê duyệt
            c.execute("UPDATE ct_dat SET dien_tich = '12.8', cong_thuc = '=4,25*3' WHERE id = (SELECT MIN(id) FROM ct_dat WHERE ma_ho = ?)",
                      (self.ma[0],))

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def _sl(self, ten):
        return self.con.execute('SELECT so_luong FROM ct_khoan WHERE ten = ?', (ten,)).fetchone()[0]

    def test_tinh_lai(self):
        goc = lan_pa.ds_lan

        def ds_lan(con, ma_ho):
            kq = goc(con, ma_ho)
            for x in kq:
                x.khoa = x.khoa or ma_ho == self.ma[2]
            return kq
        truoc = nghiep_vu.ket_qua_ho(self.con)[self.ma[0]][0].tong
        with mock.patch.object(lan_pa, 'ds_lan', side_effect=ds_lan):
            kq = lap_pa.tinh_lai_cong_thuc(self.con)
        self.assertEqual(kq, dict(so_dong=2, so_ho=1, bo_qua_khoa=1))
        self.assertEqual((self._sl('Nhà A'), self._sl('Sân'), self._sl('Nhà B'), self._sl('Ao'), self._sl('Nhà C')),
                         ('28.35', '12.3', '28.4', '0.2469', '28.4'))
        dt = self.con.execute("SELECT dien_tich FROM ct_dat WHERE cong_thuc <> ''").fetchone()[0]
        self.assertEqual(dt, '12.75')
        sau = nghiep_vu.ket_qua_ho(self.con)[self.ma[0]][0].tong
        self.assertNotEqual(sau, truoc)                                             # thành tiền tính lại theo số mới
        self.assertIn('công thức', self.con.execute('SELECT viec FROM nhat_ky ORDER BY rowid DESC').fetchone()[0])
        with mock.patch.object(lan_pa, 'ds_lan', side_effect=ds_lan):
            self.assertEqual(lap_pa.tinh_lai_cong_thuc(self.con)['so_dong'], 0)     # mở lần sau: không đổi thêm

    def test_ho_khong_nhan_viec_bo_qua(self):
        self.con._ho_nhan_viec = frozenset({self.ma[1]})
        self.assertEqual(lap_pa.tinh_lai_cong_thuc(self.con)['so_dong'], 0)
        self.assertEqual(self._sl('Nhà A'), '28.4')

    def test_cau_bao(self):
        from pabt.app import chu_tinh_lai_cong_thuc
        chu = chu_tinh_lai_cong_thuc(dict(so_dong=3, so_ho=2, bo_qua_khoa=1))
        self.assertIn('3 số lượng', chu)
        self.assertIn('đã phê duyệt', chu)


if __name__ == '__main__':
    unittest.main()
