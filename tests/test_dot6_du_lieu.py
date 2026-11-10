"""Đợt 6 (kiểm toán dữ liệu 09/11/2026): điểm neo nhật ký kiểm toán, sao lưu / khôi phục có kiểm toàn vẹn, tải bộ đơn giá an toàn,
kiểm thử thuộc tính số Decimal, mở file .pabt hỏng không treo."""
from __future__ import annotations

import os
import random
import sqlite3
import tempfile
import unittest
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pabt import csdl


class _CoThuMuc(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.goc = Path(self.td.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.goc / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        try:
            self.td.cleanup()
        except OSError:
            pass

    def _du_an(self, ten='a.pabt'):
        f = self.goc / ten
        con = csdl.tao_moi(f)
        with con:
            con.execute("INSERT INTO ho (ma_ho, ho_ten, thu_tu) VALUES (1, 'A', 1)")
        con.close()
        return f


class TestNeoKiemToan(_CoThuMuc):
    def _mo_co_ky(self, f, so_dong=3):
        from pabt import kiem_toan
        con = csdl.mo(f)
        kiem_toan.gan(con)
        for i in range(so_dong):
            with csdl.giao_dich(con):
                con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = 1', (f'B{i}',))
        return con

    def test_cat_duoi_bi_phat_hien(self):
        from pabt import kiem_toan
        f = self._du_an()
        con = self._mo_co_ky(f)
        self.assertTrue(kiem_toan.ghi_neo(con))
        self.assertEqual(kiem_toan.kiem_tra_neo(con), [])
        con.close()
        c = sqlite3.connect(str(f))                       # công cụ ngoài: gỡ trigger chặn, xóa 2 dòng cuối + băm
        c.execute('DROP TRIGGER audit_logs_khong_xoa')
        c.execute('DROP TRIGGER audit_bam_khong_xoa')
        cuoi = c.execute('SELECT MAX(id) FROM audit_bam').fetchone()[0]
        c.execute('DELETE FROM audit_bam WHERE id >= ?', (cuoi - 1,))
        c.execute('DELETE FROM audit_logs WHERE id >= ?', (cuoi - 1,))
        c.commit()
        c.close()
        con = csdl.mo(f, chi_doc=True)
        try:
            loi = kiem_toan.kiem_tra_neo(con)
            self.assertTrue(loi and 'CẮT ĐUÔI' in loi[0], loi)
            self.assertFalse(kiem_toan.kiem_tra_toan_ven(con)['hop_le'])   # chuỗi bên trong vẫn "khớp", chỉ neo bắt được
            self.assertFalse(kiem_toan.ghi_neo(con))                        # không ghi đè neo cũ (giữ dấu vết)
        finally:
            con.close()

    def test_tinh_lai_bi_phat_hien(self):
        from pabt import kiem_toan
        f = self._du_an()
        con = self._mo_co_ky(f)
        kiem_toan.ghi_neo(con)
        con.close()
        c = sqlite3.connect(str(f))
        c.execute('DROP TRIGGER audit_bam_khong_sua')
        cuoi = c.execute('SELECT MAX(id) FROM audit_bam').fetchone()[0]
        c.execute("UPDATE audit_bam SET bam = 'x' WHERE id = ?", (cuoi,))
        c.commit()
        c.close()
        con = csdl.mo(f, chi_doc=True)
        try:
            self.assertIn('TÍNH LẠI', ' '.join(kiem_toan.kiem_tra_neo(con)))
        finally:
            con.close()


class TestSaoLuuKhoiPhuc(_CoThuMuc):
    def test_khoi_phuc_moc_hong_khong_de_file(self):
        from pabt import co_may_thoi_gian as cm
        f = self._du_an()
        goc = f.read_bytes()
        hong = self.goc / 'moc_hong.pabt'
        hong.write_bytes(b'SQLite format 3\x00' + os.urandom(8192))
        with self.assertRaises(sqlite3.DatabaseError):
            cm.khoi_phuc(f, cm.Moc(file=hong, luc=datetime.now()))
        self.assertEqual(f.read_bytes()[:100], goc[:100])                 # file dự án không bị chép đè
        self.assertFalse(f.with_name(f.name + '.khoi_phuc').exists())

    def test_kiem_tra_file(self):
        from pabt import co_may_thoi_gian as cm
        f = self._du_an()
        self.assertEqual(cm.kiem_tra_file(f), '')
        rac = self.goc / 'rac.pabt'
        rac.write_bytes(os.urandom(4096))
        self.assertTrue(cm.kiem_tra_file(rac))

    def test_sao_luu_tu_dong_van_chay(self):
        f = self._du_an()
        con = csdl.mo(f)
        try:
            p = csdl.sao_luu_tu_dong(con, f)
        finally:
            con.close()
        self.assertTrue(p is not None and p.exists())


class TestTaiBoDonGia(unittest.TestCase):
    def test_chan_http_va_thieu_bam(self):
        from pabt import don_gia
        from pabt.loi import LoiNhap
        with self.assertRaisesRegex(LoiNhap, 'https'):
            don_gia.kiem_tra_mang('http://vi-du.vn/tb.json')
        with self.assertRaisesRegex(LoiNhap, 'SHA-256'):
            don_gia.tai_va_cai(dict(phien_ban='2099', tai_ve='https://vi-du.vn/bo.sqlite'))
        with self.assertRaisesRegex(LoiNhap, 'https'):
            don_gia.tai_va_cai(dict(phien_ban='2099', tai_ve='http://vi-du.vn/bo.sqlite', sha256='a' * 64))


class TestThuocTinhSo(unittest.TestCase):
    """Kiểm thử thuộc tính (hạt giống cố định - lặp lại được): đọc / ghi / làm tròn tiền không lệch, chữ lạ chỉ ném lỗi."""

    def setUp(self):
        self.ng = random.Random(20261109)

    def test_chuoi_doc_lai_dung_gia_tri(self):
        from pabt.tien import D, chuoi, doc_so_vn, vn
        for _ in range(3000):
            x = Decimal(self.ng.randint(-10 ** 12, 10 ** 12)) / (10 ** self.ng.randint(0, 4))
            self.assertEqual(D(chuoi(x)), x)                              # lưu CSDL rồi đọc lại
            so_le = self.ng.randint(0, 2)
            hien = vn(x, so_le)
            self.assertEqual(doc_so_vn(hien), x.quantize(Decimal(1).scaleb(-so_le), rounding=ROUND_HALF_UP))   # hiển thị VN đọc lại

    def test_lam_tron_nhu_excel(self):
        from pabt.tien import lam_tron
        for _ in range(3000):
            x = Decimal(self.ng.randint(-10 ** 9, 10 ** 9)) / 1000
            n = self.ng.randint(-3, 2)
            mau = Decimal(1).scaleb(-n)
            mong = (abs(x) / mau).quantize(Decimal(1), rounding=ROUND_HALF_UP) * mau
            mong = mong if x >= 0 else -mong
            self.assertEqual(lam_tron(x, n), mong, (x, n))
        self.assertEqual(lam_tron(Decimal('2.5')), 3)                     # nửa xa số 0 (không làm tròn ngân hàng)
        self.assertEqual(lam_tron(Decimal('-2.5')), -3)

    def test_chu_la_chi_nem_value_error(self):
        from pabt.tien import doc_so_vn
        ky = '0123456789.,-+eE ()%$đĐ\t\nabc@#/\\ '
        for _ in range(3000):
            chu = ''.join(self.ng.choice(ky) for _ in range(self.ng.randint(0, 12)))
            try:
                kq = doc_so_vn(chu)
            except ValueError:
                continue
            self.assertIsInstance(kq, Decimal, chu)
            self.assertTrue(kq.is_finite(), chu)                          # không nhận NaN / vô cực


class TestFileDuAnHong(_CoThuMuc):
    def test_mo_file_hong_chi_bao_loi(self):
        f = self._du_an()
        goc = f.read_bytes()
        ng = random.Random(7)
        for lan in range(25):
            du = bytearray(goc)
            for _ in range(ng.randint(1, 40)):                            # đổi ngẫu nhiên vài byte (trừ đầu SQLite: vẫn nhận là SQLite)
                i = ng.randrange(100, len(du))
                du[i] = ng.randrange(256)
            p = self.goc / f'hong_{lan}.pabt'
            p.write_bytes(bytes(du))
            try:
                con = csdl.mo(p, chi_doc=True)
            except (sqlite3.Error, RuntimeError, ValueError, OSError):
                continue
            try:
                con.execute('SELECT COUNT(*) FROM ho').fetchone()
            except sqlite3.Error:                    # trang dữ liệu hỏng: lỗi CSDL (bắt được), không UnicodeDecodeError
                pass
            finally:
                con.close()


if __name__ == '__main__':
    unittest.main()
