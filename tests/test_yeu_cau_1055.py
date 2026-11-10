"""1.0.55 (người dùng 03/11/2026, 5 phương án): chuỗi băm nhật ký kiểm toán, dấu khởi động nhanh gắn máy, sao lưu / mốc nén (CHỈ NÉN -
người dùng chọn không DPAPI), mã hóa gói tin Wi-Fi (khóa trong mã QR), giải trình công thức từng dòng, dải lần PA gọn. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import http.client
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import an_toan, co_may_thoi_gian, csdl, kiem_toan, nghiep_vu, nhan_wifi  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1055_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')

    def tearDown(self):
        self.doCleanups()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)

    def _con(self, n=3):
        p = _du_an(self.td, n)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        return p, con


class TestChuoiBamKiemToan(_Co):
    def test_ky_moi_thao_tac_va_hop_le(self):
        from pabt import ho_so
        from pabt.lap_pa import BoSoan
        _, con = self._con(3)
        self.assertTrue(kiem_toan.gan(con))
        ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        with con:
            con.execute("UPDATE ho SET ho_ten = 'Tên mới', dia_chi = 'Ấp 9' WHERE ma_ho = ?", (ds[0],))   # 2 dòng trong 1 câu
            con.execute("UPDATE thua SET dt_thu_hoi = '77' WHERE ma_ho = ?", (ds[1],))
        ho_so.xoa_ho(con, ds[2])
        bo = BoSoan(con, ds[0])
        if bo.pa.dat:
            bo.sua_dat(0, 'dien_tich', '12,5')
            bo.luu()
        kq = kiem_toan.kiem_tra_toan_ven(con)
        self.assertTrue(kq['hop_le'], kq['loi'])
        self.assertGreaterEqual(kq['so_dong_da_ky'], 5)
        self.assertEqual(kq['so_chua_ky'], 0)
        so = con.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0]
        self.assertEqual(con.execute('SELECT COUNT(*) FROM audit_bam').fetchone()[0], so)
        bam = [r[0] for r in con.execute('SELECT bam FROM audit_bam ORDER BY id')]
        self.assertEqual(len(set(bam)), len(bam))                         # dòng cùng một câu UPDATE vẫn nối chuỗi riêng

    def _gia_mao(self, p, sql):
        b = self.td / 'gia_mao.larc'
        shutil.copy(p, b)
        c = sqlite3.connect(str(b))
        self.addCleanup(c.close)
        for t in ('audit_logs_khong_sua', 'audit_logs_khong_xoa', 'audit_bam_khong_xoa'):
            c.execute(f'DROP TRIGGER IF EXISTS {t}')
        c.execute(sql)
        c.commit()
        return kiem_toan.kiem_tra_toan_ven(c)

    def test_phat_hien_sua_xoa_ngoai_phan_mem(self):
        p, con = self._con(2)
        kiem_toan.gan(con)
        with con:
            con.execute("UPDATE ho SET ho_ten = 'A', dia_chi = 'B', dien_thoai = 'C' WHERE thu_tu = 1")
        con.close()
        kq = self._gia_mao(p, "UPDATE audit_logs SET moi = 'X' WHERE id = 2")
        self.assertFalse(kq['hop_le'])
        self.assertIn('số 2', kq['loi'][0])
        kq = self._gia_mao(p, 'DELETE FROM audit_logs WHERE id = 2')
        self.assertFalse(kq['hop_le'])
        kq = self._gia_mao(p, 'DELETE FROM audit_bam WHERE id = 3')       # xóa riêng mã băm: dòng thành "chưa ký" + chuỗi sau gãy
        self.assertTrue(kq['so_chua_ky'] == 1 or not kq['hop_le'])

    def test_dong_cu_chua_ky_la_moc_khoi_dau(self):
        p, con = self._con(2)
        with con:                                                         # kết nối không gắn ký (như bản <= 1.0.54)
            con.execute("""INSERT INTO audit_logs (luc, hanh_dong, bang) VALUES ('2026-10-01T08:00:00', 'sua', 'ho')""")
        kiem_toan.gan(con)
        with con:
            con.execute("UPDATE ho SET ho_ten = 'Mới' WHERE thu_tu = 1")
        kq = kiem_toan.kiem_tra_toan_ven(con)
        self.assertTrue(kq['hop_le'], kq['loi'])
        self.assertEqual(kq['so_chua_ky'], 1)

    def test_file_cu_duoc_them_bang_bam_va_hoan_tac_khong_vuong(self):
        from pabt import hoan_tac
        p, con = self._con(2)
        with con:
            con.execute('DROP TABLE audit_bam')
        con.close()
        con = csdl.mo(p)
        self.addCleanup(con.close)
        self.assertTrue(kiem_toan.co_bang_bam(con))
        ht = hoan_tac.HoanTac(con)
        kiem_toan.gan(con)
        with con:
            con.execute("UPDATE ho SET ho_ten = 'Hoàn tác thử' WHERE thu_tu = 1")
            csdl.ghi_nhat_ky(con, 'Sửa hộ')
        ht.chot()
        self.assertEqual(ht.hoan_tac(), 'Sửa hộ')                         # audit_bam (cấm xóa) không thuộc sổ hoàn tác
        self.assertNotEqual(con.execute('SELECT ho_ten FROM ho WHERE thu_tu = 1').fetchone()[0], 'Hoàn tác thử')

    def test_khoa_dau_khoi_dong_gan_may(self):
        import nap_cap_nhat
        k = nap_cap_nhat._khoa_may()
        self.assertEqual(len(k), 32)
        self.assertEqual(k, nap_cap_nhat._khoa_may())


class TestSaoLuuNenVaWifi(_Co):
    def test_sao_luu_va_moc_nen_mo_lai_khop(self):
        p, con = self._con(30)
        so = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        f = csdl.sao_luu_tu_dong(con, p)
        m = co_may_thoi_gian.chup_moc(con, p, 'tay', bat_buoc=True)
        for x in (f, m.file):
            self.assertTrue(an_toan.la_goi_sao_luu(x))
            self.assertLess(x.stat().st_size, p.stat().st_size / 2)
            c = csdl.mo(x, chi_doc=True)
            tam = c._file_tam
            self.assertEqual(c.execute('SELECT COUNT(*) FROM ho').fetchone()[0], so)
            c.close()
            self.assertFalse(tam.exists())
        with con:
            con.execute('DELETE FROM ct_dat')
        con.close()
        co_may_thoi_gian.khoi_phuc(p, m)
        c = csdl.mo(p)
        self.addCleanup(c.close)
        self.assertGreater(c.execute('SELECT COUNT(*) FROM ct_dat').fetchone()[0], 0)

    def test_file_sao_luu_hong_bao_ro(self):
        p, con = self._con(2)
        f = csdl.sao_luu_tu_dong(con, p)
        f.write_bytes(an_toan.DAU_SAO_LUU + b'\x00' + b'khong phai zlib')
        with self.assertRaises(an_toan.LoiAnToan):
            csdl.mo(f, chi_doc=True)

    def _goi(self, may, than, dau):
        c = http.client.HTTPConnection('127.0.0.1', may._may.server_address[1], timeout=10)
        try:
            c.request('POST', f'/{may.ma}/tai_len', body=than, headers=dau)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def test_wifi_ma_hoa_va_khong_ma_hoa(self):
        may = nhan_wifi.MayNhan(ip='127.0.0.1', thu_muc=self.td / 'nhan')
        may.bat_dau()
        self.addCleanup(may.dung)
        self.assertTrue(may.url_qr.startswith(may.url + '#k='))
        self.assertEqual(len(may.khoa_qr), 32)
        du = json.dumps({'phien_ban': 2, 'ket_qua': [], 'ghi_chu': 'Nguyễn Văn Thử ' * 200}, ensure_ascii=False).encode('utf-8')
        nonce = os.urandom(16)
        ct, kiem = nhan_wifi.ma_hoa(bytes.fromhex(may.khoa_qr), nonce, du)
        self.assertNotIn(b'phien_ban', ct)
        dau = {'X-Ten-File': 'a.json', 'X-Ma-Hoa': nhan_wifi.MA_HOA, 'X-Nonce': nonce.hex(), 'X-Ma-Kiem': kiem}
        st, _ = self._goi(may, ct, dau)
        self.assertEqual(st, 200)
        self.assertEqual((self.td / 'nhan' / 'a.json').read_bytes(), du)
        sai = bytearray(ct)
        sai[5] ^= 1
        st, than = self._goi(may, bytes(sai), {**dau, 'X-Ten-File': 'b.json'})
        self.assertEqual(st, 400)
        self.assertIn('mã kiểm', json.loads(than)['loi'])
        st, _ = self._goi(may, du, {'X-Ten-File': 'c.json'})            # gõ địa chỉ tay (không #k=): nhận như trước
        self.assertEqual(st, 200)

    def test_js_trang_dien_thoai_khop_python(self):
        from PySide6.QtCore import QCoreApplication
        try:
            from PySide6.QtQml import QJSEngine
        except ImportError:
            self.skipTest('Không có QtQml')
        QCoreApplication.instance() or QCoreApplication([])
        js = nhan_wifi.TRANG
        js = js[js.index('var K = ['):js.index('var KHOA')]
        e = QJSEngine()
        e.evaluate(js)
        import hashlib
        for n in (0, 55, 56, 64, 1000):
            du = bytes((i * 13 + 1) % 256 for i in range(n))
            self.assertEqual(e.evaluate(f'hexRa(new Sha().them(hexVao("{du.hex()}")).xong())').toString(),
                             hashlib.sha256(du).hexdigest())
        khoa, nonce, du = os.urandom(16), os.urandom(16), os.urandom(300)
        ct, kiem = nhan_wifi.ma_hoa(khoa, nonce, du)
        kq = e.evaluate(f'(function(){{ var g = maHoa(hexVao("{khoa.hex()}"), hexVao("{nonce.hex()}"), hexVao("{du.hex()}"));'
                        ' return hexRa(g.ct) + "|" + g.kiem; })()').toString()
        self.assertEqual(kq, ct.hex() + '|' + kiem)


class TestGiaiTrinhCongThuc(_Co):
    def test_dat_va_khoan_khop_thanh_tien(self):
        _, con = self._con(4)
        bc = nghiep_vu.BoiCanh.tu(con)
        dem = 0
        for (ma,) in con.execute('SELECT ma_ho FROM ho').fetchall():
            pa = nghiep_vu.doc_phuong_an(con, ma)
            kq = nghiep_vu.tinh_pa(pa, bc)
            dong_dat = [d for d in kq.dong if d.muc == 1]
            for i in range(len(pa.dat)):
                gt = nghiep_vu.giai_trinh_dong_pa(pa, bc, 1, i)
                self.assertEqual(gt['thanh_tien'], dong_dat[i].thanh_tien)
                self.assertIn('Hệ số K', gt['cong_thuc_chu'])
                self.assertTrue(any('Thành tiền' in x for x in gt['thay_so']))
                dem += 1
            for m in nghiep_vu.MUC_KHOAN:
                for i, d in enumerate(pa.khoan[m]):
                    gt = nghiep_vu.giai_trinh_dong_pa(pa, bc, m, i)
                    self.assertEqual(gt['thanh_tien'], nghiep_vu.thanh_tien_dong(d, bc))
                    self.assertIn('Số lượng × Đơn giá × Tỷ lệ', gt['cong_thuc_chu'])
                    dem += 1
        self.assertGreater(dem, 4)

    def test_cua_so_lap_pa_va_chi_tiet_ho(self):
        from PySide6.QtWidgets import QApplication
        from pabt.app import ChiTietHo
        from pabt.man_hinh import CuaSoLapPA
        QApplication.instance() or QApplication([])
        _, con = self._con(2)
        ma = con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu').fetchone()[0]
        w = CuaSoLapPA(con, ma)
        w.im_lang = True
        self.addCleanup(w.close)
        gt = w.xem_giai_trinh_dong(1, 0, cho=False)
        self.assertIsNotNone(gt)
        self.assertTrue(gt['dong'][0].startswith('Hạng mục:'))
        m = w.bang[1].menu_dong()
        self.assertTrue(any(a.text().startswith('Giải trình cách tính') for a in m.actions()))
        m.deleteLater()
        self.assertFalse(w.b_xoa_lan.isVisibleTo(w))                      # hộ một lần PA: nút Xóa lần ẩn
        self.assertEqual(w.b_lan_moi.property('bien_the'), 'secondary')
        h = ChiTietHo(con, ma)
        self.addCleanup(h.deleteLater)
        from PySide6.QtWidgets import QTreeWidget
        cay = h.findChild(QTreeWidget)
        dat = cay.topLevelItem(0)
        self.assertIn('Công thức', dat.child(0).toolTip(6))


class TestVaLoiFuzzing(_Co):
    """Phương án 6: hai lỗi do fuzzing tìm ra trên 1.0.54."""

    def test_ten_file_bo_ky_tu_dieu_khien(self):
        from pabt.du_lieu_in import ten_file_ho
        _, con = self._con(1)
        ma = con.execute('SELECT ma_ho FROM ho').fetchone()[0]
        with con:
            con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = ?', ('Nguyễn\x00Văn\x07 A\x1f.', ma))
        ten = ten_file_ho(con, ma)
        self.assertFalse(any(ord(c) < 32 or ord(c) == 127 for c in ten), repr(ten))
        (self.td / f'{ten}.docx').write_bytes(b'x')                       # trước: ValueError embedded null byte

    def test_an_danh_nhan_moi_va_so_quoc_te(self):
        from pabt.tro_ly import an_danh
        kq = an_danh('Người nhận tiền: Nguyễn Hoàng Trường Giang, ĐTDĐ (+84) 912 345 678')
        self.assertNotIn('Giang', kq)
        self.assertNotIn('912', kq)
        for s in ('Họ và tên: Trần Thị Bích, SĐT +84 912.345.678', 'Chủ sở hữu Lê Văn Tám', 'Người được ủy quyền: Phạm Minh Đức'):
            kq = an_danh(s)
            self.assertIn('[HO_TEN]', kq, s)
        self.assertEqual(an_danh('(+84)912345678'), '[SĐT]')
        for s in ('bà con nhân dân', 'Tổng 120.000.000 đồng', 'Họ tên chủ hộ ghi trong sổ'):
            self.assertEqual(an_danh(s), s)                               # không che nhầm


if __name__ == '__main__':
    unittest.main()
