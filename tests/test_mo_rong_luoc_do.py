"""P2 (03/11/2026): sổ mở rộng lược đồ csdl.MO_RONG - file "cũ" (thiếu bảng phụ, cột thêm, chỉ mục) mở bằng bản mới được bổ sung đủ
trong MỘT giao dịch; mở chỉ xem / file không có hộ không bị ghi; số liệu hộ giữ nguyên."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl
from tests.test_toc_do import _du_an

DROP_COLUMN = sqlite3.sqlite_version_info >= (3, 35, 0)


def _lam_cu(p: Path) -> None:
    """Đưa file dự án về dạng "trước các phần mở rộng": bỏ bảng phụ, cột thêm, chỉ mục thêm (giữ PRAGMA user_version)."""
    con = sqlite3.connect(str(p))
    try:
        with con:
            for ten, _sql in csdl.CHI_MUC_THEM:
                con.execute(f'DROP INDEX IF EXISTS {ten}')
            con.execute('DROP TABLE IF EXISTS anh_hien_trang')
            # du_an: DDL có chú thích cuối dòng - SQLite không dựng lại được sau DROP COLUMN; cột du_an kiểm ở test_dia_danh_ngay
            for bang, cot in (('thua', csdl.COT_THUA_THEM), ('y_kien_du_thao', csdl.COT_Y_KIEN_THEM)):
                co = {r[1] for r in con.execute(f'PRAGMA table_info({bang})')}
                for k, _ in cot:
                    if k in co:
                        con.execute(f'ALTER TABLE {bang} DROP COLUMN {k}')
    finally:
        con.close()


@unittest.skipUnless(DROP_COLUMN, 'SQLite < 3.35 không có DROP COLUMN để dựng file cũ')
class TestMoRongLuocDo(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_mo_rong_'))
        self.p = _du_an(self.td, 5)
        con = csdl.mo(self.p)
        self.so_ho = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        self.tong_dt = con.execute('SELECT group_concat(dt_thu_hoi) FROM thua').fetchone()[0]
        con.close()
        _lam_cu(self.p)

    def test_mo_file_cu_bo_sung_du_mot_giao_dich(self):
        con = sqlite3.connect(str(self.p))
        thieu = csdl.thieu_mo_rong(con)
        con.close()
        self.assertIn('bang_phu', thieu)
        self.assertIn('cot_thua', thieu)
        self.assertIn('chi_muc', thieu)
        dem = []
        con = csdl.mo(self.p)
        self.addCleanup(con.close)
        self.assertEqual(csdl.thieu_mo_rong(con), [])
        self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], self.so_ho)
        self.assertEqual(con.execute('SELECT group_concat(dt_thu_hoi) FROM thua').fetchone()[0], self.tong_dt)
        self.assertEqual(con.execute("SELECT dt_nguyen_thua FROM thua LIMIT 1").fetchone()[0], '')
        con.set_trace_callback(dem.append)
        self.assertEqual(csdl.dam_bao_mo_rong(con), [])                       # đủ rồi: không ghi gì
        self.assertFalse([x for x in dem if x.upper().startswith(('ALTER', 'CREATE', 'BEGIN'))])

    def test_mot_lan_ghi_cho_moi_phan(self):
        con = sqlite3.connect(str(self.p))
        self.addCleanup(con.close)
        dem = []
        con.set_trace_callback(dem.append)
        da = csdl.dam_bao_mo_rong(con)
        self.assertGreaterEqual(len(da), 3)
        self.assertEqual(sum(1 for x in dem if x.strip().upper() == 'BEGIN'), 1)      # cả lô một giao dịch
        self.assertFalse(con.in_transaction)

    def test_chi_xem_khong_ghi(self):
        truoc = self.p.read_bytes()
        con = csdl.mo(self.p, chi_doc=True)
        con.close()
        self.assertEqual(self.p.read_bytes(), truoc)

    def test_file_khong_co_ho_khong_bi_ghi(self):
        con = sqlite3.connect(str(self.p))
        with con:
            for b in ('ct_dat', 'ct_khoan', 'thua', 'pa_lan', 'ho'):
                con.execute(f'DELETE FROM {b}')
        con.close()
        con = sqlite3.connect(str(self.p))
        self.assertEqual(csdl.dam_bao_mo_rong(con), [])
        self.assertIn('bang_phu', csdl.thieu_mo_rong(con))
        con.close()


if __name__ == '__main__':
    unittest.main()
