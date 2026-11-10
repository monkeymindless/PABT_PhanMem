"""Đợt 1 (kiểm toán 09/11/2026): trigger lạ không lọt qua kiểm thân; gỡ ngay khi mở file (mọi đường, kể cả CLI)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl

# thân làm việc thật + chú thích giả giống thân hợp lệ: bản 1.0.90 coi là hợp lệ (regex .search) và không gỡ
THAN_LACH = ("CREATE TRIGGER khoa_ho_INSERT BEFORE INSERT ON ho BEGIN UPDATE ho SET ho_ten = 'x'; "
             "-- BEGIN SELECT RAISE(ABORT,'x');\nEND")


class TestTriggerNguyenVan(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.f = Path(self.td.name) / 'a.pabt'
        con = csdl.tao_moi(self.f)
        with con:
            con.execute("INSERT INTO ho (ma_ho, ho_ten, thu_tu) VALUES (1, 'A', 1)")
        con.close()

    def tearDown(self):
        try:
            self.td.cleanup()
        except OSError:
            pass

    def _chen(self, *sql):
        c = sqlite3.connect(str(self.f))
        for s in sql:
            c.execute(s)
        c.commit()
        c.close()

    def test_than_lach_bang_chu_thich_bi_go(self):
        con = csdl.mo(self.f)
        try:
            with con:
                con.execute('DROP TRIGGER khoa_dm_taisan_INSERT')
                con.execute(THAN_LACH.replace('khoa_ho_INSERT', 'khoa_dm_taisan_INSERT').replace('ON ho ', 'ON dm_taisan '))
            self.assertEqual(csdl.go_trigger_la(con), ['khoa_dm_taisan_INSERT'])
        finally:
            con.close()

    def test_ten_khoa_nhung_bang_khong_phai_danh_muc(self):
        """Tên khoa_ho_INSERT (ho không thuộc DANH_MUC) dù thân đúng mẫu vẫn là lạ."""
        self.assertFalse(csdl.trigger_hop_le(
            'khoa_ho_INSERT', "CREATE TRIGGER khoa_ho_INSERT BEFORE INSERT ON ho WHEN (SELECT mo FROM khoa_dm WHERE id = 1) = 0 "
                              "BEGIN SELECT RAISE(ABORT, 'x'); END"))

    def test_when_lech_va_bien_co_lech(self):
        ok = ("CREATE TRIGGER khoa_dm_taisan_INSERT BEFORE INSERT ON dm_taisan WHEN (SELECT mo FROM khoa_dm WHERE id = 1) = 0 "
              "BEGIN SELECT RAISE(ABORT, 'x'); END")
        self.assertTrue(csdl.trigger_hop_le('khoa_dm_taisan_INSERT', ok))
        self.assertFalse(csdl.trigger_hop_le('khoa_dm_taisan_INSERT', ok.replace('= 0', '= 1')))          # WHEN đổi nghĩa
        self.assertFalse(csdl.trigger_hop_le('khoa_dm_taisan_UPDATE', ok))                                # tên UPDATE, thân INSERT
        self.assertFalse(csdl.trigger_hop_le('khoa_dm_taisan_INSERT', ok.replace('BEFORE', 'AFTER')))
        self.assertFalse(csdl.trigger_hop_le('khoa_dm_taisan_INSERT', ok.replace("'x'", "'x'); UPDATE ho SET ho_ten = 'q'; SELECT ('")))

    def test_mo_go_trigger_lach_ngay_khi_mo(self):
        """Đường CLI / máy chủ (csdl.mo, không qua app.py): trigger lạ bị gỡ TRƯỚC mọi lần ghi và có nhật ký."""
        self._chen("CREATE TRIGGER doi_ten AFTER UPDATE ON ho BEGIN UPDATE ho SET ho_ten = 'Z'; END")
        con = csdl.mo(self.f)
        try:
            self.assertEqual(csdl.trigger_la(con), [])
            nk = con.execute("SELECT chi_tiet FROM nhat_ky WHERE viec LIKE 'Gỡ trigger lạ%'").fetchall()
            self.assertEqual([r[0] for r in nk], ['doi_ten'])
            con.execute("UPDATE ho SET ho_ten = 'B' WHERE ma_ho = 1")      # trigger đã gỡ: tên không bị đổi ngầm
            self.assertEqual(con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0], 'B')
        finally:
            con.close()

    def test_trigger_cua_phan_mem_giu_nguyen(self):
        con = csdl.mo(self.f)
        try:
            n = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger'").fetchone()[0]
            self.assertGreater(n, 0)
            self.assertEqual(csdl.trigger_la(con), [])
            self.assertEqual(csdl.go_trigger_la(con), [])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger'").fetchone()[0], n)
        finally:
            con.close()

    def test_mo_chi_xem_khong_ghi(self):
        self._chen("CREATE TRIGGER doi_ten AFTER UPDATE ON ho BEGIN UPDATE ho SET ho_ten = 'Z'; END")
        con = csdl.mo(self.f, chi_doc=True)
        try:
            self.assertEqual(csdl.trigger_la(con), ['doi_ten'])             # chỉ xem: không gỡ được (và không có lần ghi nào để nổ)
        finally:
            con.close()


if __name__ == '__main__':
    unittest.main()


class TestQuyenDot1(unittest.TestCase):
    """1.3 / 1.4: khóa LENH_QUYEN đúng tên lệnh thật; hàm ghi kiểm quyền / hộ nhận việc."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.con = csdl.tao_moi(Path(self.td.name) / 'q.pabt')
        with self.con:
            self.con.execute("INSERT INTO ho (ma_ho, ho_ten, thu_tu, luu_luc) VALUES (1, 'A', 1, 'x'), (2, 'B', 2, 'x')")
            for m in (1, 2):
                self.con.execute("INSERT INTO thua (ma_ho, so_to, so_thua, nguon_goc) VALUES (?, '1', ?, 'Nguồn gốc')", (m, str(m)))

    def tearDown(self):
        self.con.close()
        try:
            self.td.cleanup()
        except OSError:
            pass

    def test_lenh_quyen_trung_ten_lenh_that(self):
        import re
        from pabt import phan_quyen as pq
        nguon = (Path(__file__).resolve().parent.parent / 'pabt' / 'lenh.py').read_text(encoding='utf-8')
        that = set(re.findall(r"\('([^']+…?)',\s*lambda", nguon))
        ngoai_ds = {'Quản lý tài khoản…'}              # mục menu riêng (app.py), không nằm trong bảng lệnh
        lech = [k for k in pq.LENH_QUYEN if k not in that and k not in ngoai_ds]
        self.assertEqual(lech, [], 'LENH_QUYEN có tên lệnh không tồn tại: nút không bị tắt theo vai trò')

    def test_luu_du_an_kiem_quyen(self):
        from pabt import lap_pa, phan_quyen as pq
        gt = {k: '' for k, _ in lap_pa.TRUONG_DU_AN}
        gt.update(ten='Dự án thử', cap_dia_ban='Xã')
        self.con._vai_tro = pq.KE_TOAN                          # không có sửa hồ sơ, không có quản trị
        with self.assertRaises(pq.LoiQuyen):
            lap_pa.luu_du_an(self.con, gt)
        self.con._vai_tro = pq.CHUYEN_VIEN                      # có sửa hồ sơ
        lap_pa.luu_du_an(self.con, gt)
        self.con._vai_tro = pq.LANH_DAO                         # có quản trị
        lap_pa.luu_du_an(self.con, gt)
        del self.con._vai_tro                                   # máy đơn
        lap_pa.luu_du_an(self.con, gt)

    def test_goi_y_du_dieu_kien_quyen_va_ho_nhan_viec(self):
        from pabt import du_thao, phan_quyen as pq
        self.con._vai_tro = pq.THANH_TRA                        # chỉ xem
        with self.assertRaises(pq.LoiQuyen):
            du_thao.goi_y_du_dieu_kien(self.con)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ho WHERE du_dieu_kien = 1').fetchone()[0], 0)
        self.con._vai_tro = pq.CHUYEN_VIEN
        self.con._ho_nhan_viec = frozenset({1})                 # offline theo hộ: chỉ hộ 1
        self.assertEqual(du_thao.goi_y_du_dieu_kien(self.con), 1)
        self.assertEqual([r[0] for r in self.con.execute('SELECT ma_ho FROM ho WHERE du_dieu_kien = 1')], [1])


class TestAnDanhVaLamTron(unittest.TestCase):
    """1.5 / 1.6: che họ tên khi không có kết nối; số diện tích làm tròn kiểu Excel."""

    def setUp(self):
        from pabt import tro_ly
        self.tro_ly = tro_ly
        self.cu = list(tro_ly._TEN_CHUP)

    def tearDown(self):
        self.tro_ly._TEN_CHUP[:] = self.cu

    def test_an_danh_khong_ket_noi_dung_anh_chup(self):
        self.tro_ly._TEN_CHUP[:] = [('Nguyễn Văn Khải', 7)]
        out = self.tro_ly.an_danh('Hộ nguyễn văn khải có 3 cây xoài, SĐT 0912345678')
        self.assertNotIn('Khải', out)
        self.assertIn('Hộ #7', out)
        self.assertNotIn('0912345678', out)

    def test_chup_ten_che_tu_du_an(self):
        with tempfile.TemporaryDirectory() as td:
            con = csdl.tao_moi(Path(td) / 'c.pabt')
            try:
                with con:
                    con.execute("INSERT INTO ho (ma_ho, ho_ten, thu_tu) VALUES (5, 'Trần Thị Mai', 1), (6, 'Lê', 2)")
                self.tro_ly.chup_ten_che(con)
                self.assertEqual(self.tro_ly._TEN_CHUP, [('Trần Thị Mai', 5)])   # tên < 4 ký tự không che (tránh che nhầm chữ thường)
            finally:
                con.close()

    def test_goi_ai_don_gia_che_noi_dung(self):
        from pabt import phan_tich_ai_don_gia as p

        class KhachGia:
            def __init__(self):
                self.gui = None

            class beta:                      # noqa: N801 - mô phỏng khach.beta.messages.stream
                pass
        gui = {}

        class Stream:
            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False

            def get_final_message(s):
                raise RuntimeError('dừng sau khi bắt nội dung')

        class Messages:
            def stream(s, **kw):
                gui.update(kw)
                return Stream()

        class Beta:
            messages = Messages()
        k = KhachGia()
        k.beta = Beta()
        try:
            p.goi_ai('Chủ hộ CCCD 075092001234 gọi 0912345678', khach=k)
        except Exception:                                    # noqa: BLE001 - chỉ cần bắt nội dung gửi đi
            pass
        nd = gui['messages'][0]['content']
        self.assertNotIn('075092001234', nd)
        self.assertNotIn('0912345678', nd)

    def test_dien_tich_lam_tron_nua_xa_so_khong(self):
        from decimal import Decimal
        from pabt.tien import vn
        self.assertEqual(vn(Decimal('0.25'), 1), '0,3')            # format(float, ",.1f") cho "0,2"
        self.assertEqual(vn(Decimal('1926.05'), 1), '1.926,1')
