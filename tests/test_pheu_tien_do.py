"""Phễu tiến độ theo hộ / lần phương án (pabt/pheu_tien_do.py, 30/10/2026) và nâng cấp lược đồ an toàn (pa_lan.dot_trinh_id,
y_kien_du_thao.lan). Kiểm: mỗi hộ đúng một giai đoạn (tổng = số hộ) ở MỌI bước của quy trình, hộ có phương án bổ sung xét theo lần đang
mở, đợt trình cũ của hộ không bị gán nhầm cho lần bổ sung, cờ bất thường, file cũ thiếu cột. Dự án GIẢ LẬP tests.test_toc_do._du_an."""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, du_thao, pheu_tien_do as ph, quan_ly, theo_doi  # noqa: E402
from pabt.lap_pa import BoSoan  # noqa: E402
from pabt.tien import D  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class _Co(unittest.TestCase):
    N = 8

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.file = _du_an(self.td, self.N)
        self.con = csdl.mo(self.file)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def pheu(self, **k) -> ph.KetQuaPheu:
        kq = ph.tinh(self.con, **k)
        self.assertTrue(kq.doi_soat(), kq.dem())
        self.assertEqual(kq.so_ho, self.N)
        return kq

    def gd(self, kq, ma) -> ph.HoPheu:
        return next(x for x in kq.ho if x.ma_ho == ma)

    def them_dong(self, bo, muc=2, sl=3):
        m = bo.dm.muc[muc][0]
        bo.them_tu_danh_muc(muc, m)
        bo.pa.khoan[muc][-1].so_luong = D(sl)


class TestPheu(_Co):
    def test_du_an_moi_tu_lap(self):
        kq = self.pheu()
        self.assertEqual(kq.dem()['da_lap'], self.N)
        self.assertEqual(kq.dem_co().get('tu_lap'), self.N)       # Dự án mới: phương án phần mềm tự lập, chưa soát

    def test_di_qua_moi_giai_doan_va_luon_doi_soat(self):
        a, b, c, d = self.ma[:4]
        ny = du_thao.tao_dot(self.con, 'Đợt 1', '01/10/2026', 'UBND xã')
        du_thao.them_thu_cong(self.con, ny, [a, b, c, d], ca_vuong=True)
        kq = self.pheu()
        self.assertEqual(kq.dem()['niem_yet'], 4)
        self.assertEqual(self.gd(kq, a).dot_niem_yet, ny)
        for m in (a, b, c):
            du_thao.doi_y_kien_nhanh(self.con, ny, m)                   # chua -> dong_y
        self.assertEqual(self.pheu().dem()['cho_trinh'], 3)
        dt = quan_ly.tao_dot(self.con, 'Đợt trình 1')
        quan_ly.gan_dot(self.con, [a, b, d], dt)                        # d chưa có ý kiến
        kq = self.pheu()
        self.assertEqual(kq.dem()['cho_phe_duyet'], 3)
        self.assertEqual([x.ma_ho for x in kq.theo_co('trinh_thieu_y_kien')], [d])
        self.assertEqual(self.con.execute('SELECT dot_trinh_id FROM pa_lan WHERE ma_ho = ? AND lan = 1', (a,)).fetchone()[0], dt)
        self.assertEqual(len(kq.loc_dot(dot_trinh=dt)), 3)
        q = theo_doi.luu_qd(self.con, None, '1/QĐ-UBND', '05/10/2026')
        theo_doi.them_ho_theo_pa(self.con, q, [a, b])
        self.assertEqual(self.pheu().dem()['cho_chi_tra'], 2)
        theo_doi.ghi_chi_tra(self.con, [(q, a), (q, b)], '06/10/2026')
        self.assertEqual(self.pheu().dem()['cho_ban_giao'], 2)
        theo_doi.ghi_ban_giao(self.con, [a], dict(da_ban_giao=1, ban_giao_ngay='07/10/2026'))
        kq = self.pheu()
        self.assertEqual((kq.dem()['hoan_tat'], kq.dem()['cho_ban_giao']), (1, 1))
        self.assertEqual(sum(kq.dem().values()), self.N)

    def test_phuong_an_bo_sung_xet_theo_lan_dang_mo(self):
        a = self.ma[0]
        dt = quan_ly.tao_dot(self.con, 'Đợt trình 1')
        quan_ly.gan_dot(self.con, [a], dt)
        q = theo_doi.luu_qd(self.con, None, '1/QĐ-UBND', '05/10/2026')
        theo_doi.them_ho_theo_pa(self.con, q, [a])
        theo_doi.ghi_chi_tra(self.con, [(q, a)], '06/10/2026')
        theo_doi.ghi_ban_giao(self.con, [a], dict(da_ban_giao=1, ban_giao_ngay='07/10/2026'))
        self.assertEqual(self.gd(self.pheu(), a).giai_doan, 'hoan_tat')
        bo = BoSoan(self.con, a)
        bo.lap_bo_sung('Bổ sung cây trồng')
        self.them_dong(bo, 3, 4)
        bo.luu()
        h = self.gd(self.pheu(), a)
        # lần 2 mới lập: KHÔNG được coi là "chờ phê duyệt" theo đợt trình cũ của hộ (ho.dot_id thuộc lần 1)
        self.assertEqual((h.lan, h.giai_doan), (2, 'da_lap'))
        self.assertIn('pa_bo_sung', h.co)
        self.assertEqual(self.gd(self.pheu(che_do='goc'), a).giai_doan, 'hoan_tat')       # xem theo phương án gốc
        ny = du_thao.tao_dot(self.con, 'Đợt 2', '10/10/2026', 'UBND xã')
        du_thao.them_thu_cong(self.con, ny, [a], ca_vuong=True)
        self.assertEqual(self.con.execute('SELECT lan FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (ny, a)).fetchone()[0], 2)
        self.assertEqual(self.gd(self.pheu(), a).giai_doan, 'niem_yet')
        du_thao.doi_y_kien_nhanh(self.con, ny, a)
        dt2 = quan_ly.tao_dot(self.con, 'Đợt trình 2')
        quan_ly.gan_dot(self.con, [a], dt2)
        h = self.gd(self.pheu(), a)
        self.assertEqual((h.giai_doan, h.dot_trinh), ('cho_phe_duyet', dt2))
        self.assertEqual(self.con.execute('SELECT dot_trinh_id FROM pa_lan WHERE ma_ho = ? AND lan = 1', (a,)).fetchone()[0], dt)
        q2 = theo_doi.luu_qd(self.con, None, '2/QĐ-UBND', '15/10/2026')
        theo_doi.them_ho_theo_pa(self.con, q2, [a])
        self.assertEqual(self.gd(self.pheu(), a).giai_doan, 'cho_chi_tra')

    def test_xoa_dot_trinh_xoa_theo_lan(self):
        a = self.ma[0]
        dt = quan_ly.tao_dot(self.con, 'Đợt trình 1')
        quan_ly.gan_dot(self.con, [a], dt)
        quan_ly.xoa_dot(self.con, dt)
        self.assertIsNone(self.con.execute('SELECT dot_trinh_id FROM pa_lan WHERE ma_ho = ? AND lan = 1', (a,)).fetchone()[0])
        self.assertEqual(self.gd(self.pheu(), a).giai_doan, 'da_lap')

    def test_co_bat_thuong(self):
        a, b = self.ma[:2]
        self.con.execute("UPDATE ho SET ban_giao_ngay = '01/10/2026' WHERE ma_ho = ?", (a,))
        self.con.execute("UPDATE ho SET ma_vuong = 'V1' WHERE ma_ho = ?", (b,))
        self.con.commit()
        kq = self.pheu()
        self.assertIn('ngay_bg_chua_qd', self.gd(kq, a).co)
        self.assertEqual(self.gd(kq, a).giai_doan, 'da_lap')            # ngày từ Excel không làm hộ "hoàn tất"
        self.assertIn('vuong', self.gd(kq, b).co)


class TestLuocDo(_Co):
    N = 3

    def test_cot_moi_co_san_va_bo_don_gia_khong_bi_ghi(self):
        self.assertIn('dot_trinh_id', {r[1] for r in self.con.execute('PRAGMA table_info(pa_lan)')})
        self.assertIn('lan', {r[1] for r in self.con.execute('PRAGMA table_info(y_kien_du_thao)')})

    def test_chep_dot_cu_chi_khi_khong_nham(self):
        """Nâng cấp file cũ: hộ có đúng một lần nhận đợt trình của hộ; hộ nhiều lần để trống (không đoán)."""
        c = sqlite3.connect(':memory:')
        c.execute('CREATE TABLE ho (ma_ho INTEGER PRIMARY KEY, dot_id INTEGER)')
        c.execute('''CREATE TABLE pa_lan (id INTEGER PRIMARY KEY, ma_ho INTEGER, lan INTEGER, loai TEXT NOT NULL DEFAULT 'bo_sung',
                     thay_the INTEGER NOT NULL DEFAULT 0)''')
        c.executemany('INSERT INTO ho VALUES (?, ?)', [(1, 7), (2, 7), (3, None)])
        c.executemany('INSERT INTO pa_lan (ma_ho, lan) VALUES (?, ?)', [(1, 1), (2, 1), (2, 2), (3, 1)])
        csdl.dam_bao_cot_pa_lan(c)
        r = {(m, n): d for m, n, d in c.execute('SELECT ma_ho, lan, dot_trinh_id FROM pa_lan')}
        self.assertEqual(r, {(1, 1): 7, (2, 1): None, (2, 2): None, (3, 1): None})

    def test_file_cu_thieu_cot_mo_chi_xem(self):
        self.con.close()
        cu = self.td / 'cu.pabt'
        shutil.copy2(self.file, cu)
        c = sqlite3.connect(cu)
        c.execute('ALTER TABLE y_kien_du_thao DROP COLUMN lan')
        c.execute('ALTER TABLE pa_lan DROP COLUMN dot_trinh_id')
        c.commit()
        c.close()
        con = csdl.mo(str(cu), chi_doc=True)
        try:
            kq = ph.tinh(con)
            self.assertTrue(kq.doi_soat())
            self.assertEqual(kq.so_ho, self.N)
        finally:
            con.close()
        self.con = csdl.mo(self.file)


if __name__ == '__main__':
    unittest.main()
