"""Dự thảo PABT: đợt niêm yết 10 ngày, ba tỷ lệ đồng thuận, hộ vướng không vào đợt."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, du_thao
from pabt.lap_pa import LoiNhap


class TestDuThao(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = Path(self.td.name) / 'a.pabt'
        self.con = csdl.tao_moi(self.p)
        self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd) VALUES (1, 1, 'Hộ thử một', '075092000001')")
        self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd) VALUES (2, 2, 'Hộ thử hai', '075092000002')")
        self.con.execute("INSERT INTO thua (ma_thua, ma_ho, so_thua, so_to, nguon_goc) VALUES (1, 1, '12', '5', 'Đất ở')")
        self.con.commit()

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_muoi_ngay_va_ba_ty_le(self):
        self.assertEqual(du_thao.ngay_ket_thuc('2026-10-01'), '2026-10-11')
        self.assertEqual(du_thao.han_doi_thoai('11/10/2026'), '2026-11-10')
        dot = du_thao.tao_dot(self.con, 'Đợt 1', '01/10/2026', 'UBND xã')
        them, bo = du_thao.dua_ho_vao_dot(self.con, dot)
        self.assertEqual((them, bo), (0, 2))                 # chưa đánh dấu đủ điều kiện
        du_thao.ghi_phap_ly(self.con, 1, 1, '', '')
        du_thao.ghi_phap_ly(self.con, 2, 0, 'V1', 'Chờ xã')
        them, bo = du_thao.dua_ho_vao_dot(self.con, dot)
        self.assertEqual(them, 1)
        self.assertEqual([h['ma_ho'] for h in du_thao.ds_ho_dot(self.con, dot)], [1])
        self.assertEqual(du_thao.ds_ho_dot(self.con, dot)[0]['cccd_che'], '075092******')
        du_thao.ghi_y_kien(self.con, dot, 1, 'dong_y', '', 'Đồng ý phương án')
        tk = du_thao.thong_ke_y_kien(self.con, dot)
        self.assertEqual((tk['dong_y'], tk['so_ho_dot'], tk['pt_dot']), (1, 1, 100.0))
        self.assertEqual(tk['pt_bao_phu'], 50.0)             # 1/2 hộ cả dự án, không phải 100%
        self.assertEqual(tk['pt_luy'], 100.0)                # 1/1 hộ đã niêm yết
        p = du_thao.thong_ke_phieu(self.con)
        self.assertEqual((p['tong'], p['du_dieu_kien'], p['vuong'], p['da_du_thao']), (2, 1, 1, 1))
        f = du_thao.xuat_niem_yet(self.con, dot, Path(self.td.name) / 'ny.xlsx')
        self.assertTrue(f.exists())
        with self.assertRaises(LoiNhap):
            du_thao.tao_dot(self.con, '', '01/10/2026', '')
        dot2 = du_thao.tao_dot(self.con, 'Đợt 2', '20/10/2026', 'Nhà văn hóa')
        du_thao.ghi_y_kien(self.con, dot, 1, 'khong_dong_y', 'gia_dat', 'Giá đất thấp')
        self.assertEqual([h['ma_ho'] for h in du_thao.ds_de_them(self.con, dot2, 'khong_dong_y')], [1])
        self.assertEqual([h['ma_ho'] for h in du_thao.ds_de_them(self.con, dot2, 'dot', dot)], [1])
        them, bo = du_thao.them_thu_cong(self.con, dot2, [1, 2])
        self.assertEqual((them, bo), (1, 1))          # hộ 2 đang vướng, không vào đợt
        self.assertEqual([h['ma_ho'] for h in du_thao.ds_de_them(self.con, dot2, 'chua')], [2])

    def test_nang_cap_tu_v12(self):
        import sqlite3
        self.con.execute('PRAGMA user_version = 12')
        try:
            for c in ('du_dieu_kien', 'ma_vuong', 'ghi_chu_phap_ly', 'dot_du_thao_id'):
                self.con.execute(f'ALTER TABLE ho DROP COLUMN {c}')
            self.con.execute('DROP TABLE IF EXISTS doi_thoai_ho')
            self.con.execute('DROP TABLE IF EXISTS y_kien_du_thao')
            self.con.execute('DROP TABLE IF EXISTS dot_du_thao')
        except sqlite3.OperationalError:
            self.skipTest('SQLite không hỗ trợ DROP COLUMN')
        self.con.commit()
        self.con.close()
        self.con = csdl.mo(self.p)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        cot = {r[1] for r in self.con.execute('PRAGMA table_info(ho)')}
        self.assertIn('du_dieu_kien', cot)
        self.assertIsNotNone(self.con.execute("SELECT name FROM sqlite_master WHERE name = 'dot_du_thao'").fetchone())


try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestManHinhDuThao(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        self.td = tempfile.TemporaryDirectory()
        self.p = Path(self.td.name) / 'a.pabt'
        self.con = csdl.tao_moi(self.p)
        self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'Hộ thử')")
        self.con.commit()

    def tearDown(self):
        if getattr(self, 'w', None) is not None:
            self.w.close()
        self.con.close()
        self.td.cleanup()

    def test_mo_tab_khong_so_lieu_gia(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh(menu_trai=True)
        self.w = w
        w.mo(str(self.p))
        self.assertIn('Dự thảo PABT…', w.lenh)
        k = w.mo_du_thao(cho=False)
        self.assertIsNotNone(k)
        self.assertEqual(k.the['tong'].gia.text(), '1 hộ')
        self.assertNotIn('500', k.lb_phu.text())
