"""1.0.58: lỗi do hội đồng rà soát phát hiện, đã đối chiếu trên mã. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import APP  # noqa: F401
from pabt import __init__ as _  # noqa: F401
from pabt import ban_do_cad, csdl, exe_he_thong, hoan_tac, khoa, thong_bao, tro_ly


class TestThuanPython(unittest.TestCase):
    def test_tam_giac_hoa_ranh_nhieu_dinh(self):
        # răng lược lõm 40 đỉnh: tổng tam giác phải đúng diện tích (trần vòng cũ thoát sớm từ 30 đỉnh)
        p = [(float(i), 0.0) for i in range(20)]
        p += [(19.0 - i, 10.0 if i % 2 else 5.0) for i in range(20)]
        tong = sum(abs(ban_do_cad.dien_tich_co_dau(t)) for t in ban_do_cad.tam_giac_hoa(p))
        self.assertAlmostEqual(tong, abs(ban_do_cad.dien_tich_co_dau(p)), places=6)

    def test_giai_thich_loi(self):
        for e, co in ((sqlite3.OperationalError('no such column: ho.abc'), 'cấu trúc'), (sqlite3.IntegrityError('UNIQUE constraint failed: ho.ma_ho'), 'trùng'),
                      (sqlite3.OperationalError('disk I/O error'), 'mất kết nối'), (OSError(5, 'x'), 'file'), (ValueError('Chu vi phải lớn hơn 0.'), 'Chu vi'),
                      (sqlite3.IntegrityError('Nhật ký kiểm toán không được sửa.'), 'Nhật ký'), (ValueError('could not convert'), 'không đọc được')):
            self.assertIn(co, thong_bao.giai_thich(e)[0], repr(e))

    def test_exe_tuyet_doi(self):
        self.assertTrue(os.path.isabs(exe_he_thong('cscript.exe')))

    def test_an_danh(self):
        con = sqlite3.connect(':memory:')
        con.execute('CREATE TABLE ho (ma_ho INTEGER, ho_ten TEXT)')
        con.executemany('INSERT INTO ho VALUES (?,?)', [(1, 'Nguyễn Văn An'), (2, 'Trần Thị Bình và Lê Văn Cường')])
        for chu in ('hộ Nguyen Van An', 'Nguyễn  Văn An', 'Trần Thị Bình', 'Lê Văn Cường'):
            self.assertIn('Hộ #', tro_ly.an_danh(chu, con), chu)
        self.assertNotIn('2345', tro_ly.an_danh('số 0791 2345 6789'))
        self.assertNotIn('gmail', tro_ly.an_danh('an@gmail.com'))
        self.assertNotIn('Hoàng', tro_ly.an_danh('anh Hoàng Văn Em'))
        self.assertIn('bà con nhân dân', tro_ly.an_danh('bà con nhân dân'))
        self.assertIn('1.234.567.890', tro_ly.an_danh('tổng 1.234.567.890 đồng'))

    def test_khoa_json_la(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'a.pabt'
            k = khoa.KhoaFile(f)
            k.p.write_text('[1]', encoding='utf-8')
            self.assertIsNone(k.doc())


class TestCsdl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(Path(self.tmp.name) / 'may')})
        p.start()
        self.addCleanup(p.stop)
        self.con = csdl.tao_moi(Path(self.tmp.name) / 'a.pabt')
        self.addCleanup(self.con.close)
        with self.con:
            self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'A')")

    def tearDown(self):
        self.doCleanups()
        self.tmp.cleanup()

    def test_hoan_tac_loi_khong_mat_buoc(self):
        ht = hoan_tac.HoanTac(self.con)
        for t in ('b1', 'b2'):
            with csdl.giao_dich(self.con):
                self.con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = 1', (t,))
                csdl.ghi_nhat_ky(self.con, f'sua {t}')
            ht.chot()
        n = len(ht.hoan_tac_ds)
        with mock.patch.object(ht, '_ap', side_effect=sqlite3.OperationalError('database is locked')), self.assertRaises(sqlite3.OperationalError):
            ht.hoan_tac()
        self.assertEqual(len(ht.hoan_tac_ds), n)
        ht.hoan_tac()
        self.assertEqual(self.con.execute('SELECT ho_ten FROM ho').fetchone()[0], 'b1')

    def test_go_trigger_la(self):
        with self.con:
            self.con.execute("CREATE TRIGGER la_doi_tien AFTER INSERT ON ct_khoan BEGIN UPDATE ct_khoan SET don_gia = 1; END")
        self.assertEqual(csdl.go_trigger_la(self.con), ['la_doi_tien'])
        self.assertEqual(csdl.go_trigger_la(self.con), [])              # trigger của phần mềm giữ nguyên
        self.assertTrue(self.con.execute("SELECT 1 FROM sqlite_master WHERE name = 'audit_logs_khong_xoa'").fetchone())

    def test_go_trigger_gia_ten_phan_mem(self):
        """Tên giống trigger của phần mềm nhưng thân đổi tiền: vẫn gỡ; trigger khóa thật (có WHEN) giữ nguyên."""
        with self.con:
            self.con.execute("CREATE TRIGGER khoa_ct_khoan_INSERT AFTER INSERT ON ct_khoan "
                             "BEGIN UPDATE ct_khoan SET don_gia = 1; END")
        self.assertEqual(csdl.go_trigger_la(self.con), ['khoa_ct_khoan_INSERT'])
        co_khoa = self.con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'khoa\\_%' ESCAPE '\\'").fetchone()[0]
        self.assertGreater(co_khoa, 0)
        self.assertEqual(csdl.go_trigger_la(self.con), [])

    def test_cad_thua_nhieu_dong_khong_ghi_nham(self):
        with self.con:
            self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (2, 2, 'B')")
            self.con.executemany('INSERT INTO thua (ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi) VALUES (?,?,?,?,?)',
                                 [(1, '5', '12', 'ONT', '100'), (1, '5', '12', 'CLN', '400'), (2, '5', '12', 'CLN', '0')])
        cm = ban_do_cad.chi_muc_thua(self.con)
        self.assertEqual(cm[(ban_do_cad._khoa('5'), ban_do_cad._khoa('12'))][1], 1)     # gắn hộ chủ đất
        kq = ban_do_cad.KetQuaCad.__new__(ban_do_cad.KetQuaCad)
        t = mock.Mock(so_to='5', so_thua='12', loai_dat='CLN', dt_ban_ve=None, dt_hinh=450, dt_trong_ranh=450, toa_do=[], nhan='', lop='', chi_tiet={})
        kq.thua, kq.nguon, kq.so_to = [t], 'x', '5'
        r = ban_do_cad.luu(self.con, kq, {(ban_do_cad._khoa('5'), ban_do_cad._khoa('12'))})
        self.assertEqual((r['cap_nhat'], len(r['nhieu_dong'])), (0, 1))
        self.assertEqual(sorted(x[0] for x in self.con.execute('SELECT dt_thu_hoi FROM thua')), ['0', '100', '400'])

    def test_pheu_khong_tich_khoa(self):
        from pabt import pheu_tien_do as p
        for i in range(4):
            p.tinh(self.con, {1: f'k{i}'})
        self.assertLessEqual(sum(1 for k in self.con.bo_nho if isinstance(k, tuple) and k and k[0] == 'pheu_tien_do.tinh'), 2)


class TestDongCuaSo(unittest.TestCase):
    def test_khai_toan_chua_luu_hoi_truoc_khi_roi(self):
        from PySide6.QtWidgets import QApplication, QMessageBox
        from pabt.man_hinh_du_toan import KhungDuToan
        k = KhungDuToan.__new__(KhungDuToan)
        k.file, k.im_lang, k.dt = None, False, mock.Mock(dong=[1])
        k._doc_dau = lambda: None
        self.assertTrue(k.hoi_luu())                                    # offscreen: không chặn kiểm thử
        with mock.patch.object(QApplication, 'platformName', return_value='windows'), \
                mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel) as q:
            self.assertFalse(k.hoi_luu())
        q.assert_called_once()

    def test_huy_luu_khong_dong(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        self.addCleanup(w.deleteLater)
        with mock.patch.object(w, 'dong_du_an', return_value=False):
            self.assertFalse(w.close())
        with mock.patch.object(w, 'dong_du_an', return_value=True):
            self.assertTrue(w.close())


if __name__ == '__main__':
    unittest.main()
