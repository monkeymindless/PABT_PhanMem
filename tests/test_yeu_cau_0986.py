"""Kiểm thử 0.9.86 (người dùng 14/10/2026 - Cụm 1, Cụm 2): nhật ký kiểm toán audit_logs (kiem_toan), "Bác sĩ hồ sơ" trong Kiểm tra lỗi
(kiem_loi.BAC_SI), nhập hàng loạt vào file tạm không fsync từng giao dịch (csdl.tao_moi_tam). Dữ liệu giả."""
from __future__ import annotations
import json
import os
import sqlite3
import unittest
from decimal import Decimal
from unittest import mock

import openpyxl

from pabt import csdl, dia_phuong, kiem_loi, kiem_toan
from pabt.lap_pa import BoSoan
from tests.test_in_vua_chu import CoSo


class CoSoKt(CoSo):
    def setUp(self):
        super().setUp()
        self.may = self.td / 'may'
        self.may.mkdir()
        self._env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.may)})
        self._env.start()
        dia_phuong.nap_lai()

    def tearDown(self):
        self._env.stop()
        dia_phuong.nap_lai()
        super().tearDown()

    def nk(self, **dk):
        return [d for d in kiem_toan.doc(self.con) if all(d[k] == v for k, v in dk.items())]


class TestBangNhatKy(CoSoKt):
    def test_file_moi_co_bang_va_khong_sua_xoa_duoc(self):
        self.assertTrue(kiem_toan.co_bang(self.con))
        with self.con:
            self.con.execute("INSERT INTO audit_logs (luc, hanh_dong, bang) VALUES ('2026-10-14T08:00:00', 'sua', 'ho')")
        for cau in ("UPDATE audit_logs SET moi = 'x'", 'DELETE FROM audit_logs'):
            with self.assertRaisesRegex(sqlite3.DatabaseError, 'không được'):
                with self.con:
                    self.con.execute(cau)

    def test_file_cu_chua_co_bang_tao_khi_mo(self):
        with self.con:
            self.con.execute('DROP TRIGGER audit_logs_khong_xoa')
            self.con.execute('DROP TRIGGER audit_logs_khong_sua')
            self.con.execute('DROP TABLE audit_logs')
            self.con.execute('PRAGMA user_version = 15')                # file của bản 0.9.86 (v15): v16 tạo bảng khi nâng cấp
        self.con.close()
        self.con = csdl.mo(self.p, chi_doc=True)                        # chỉ xem: không ghi vào file
        self.assertFalse(kiem_toan.co_bang(self.con))
        self.con.close()
        self.con = csdl.mo(self.p)
        self.assertTrue(kiem_toan.co_bang(self.con))
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)   # nâng lên v16


class TestGhiVet(CoSoKt):
    def test_ho_thua_cu_moi_va_nguoi(self):
        self.assertTrue(kiem_toan.gan(self.con, 'can_bo_a'))
        with self.con:
            self.con.execute("UPDATE ho SET nhan_khau = 5, ho_ten = 'Nguyễn Văn Sửa' WHERE ma_ho = 1")
            self.con.execute("UPDATE ho SET trang_thai = 'x' WHERE ma_ho = 1")            # trường không theo dõi: không ghi
            t = self.con.execute('SELECT ma_thua, dt_thu_hoi FROM thua WHERE ma_ho = 1 LIMIT 1').fetchone()
            self.con.execute("UPDATE thua SET dt_thu_hoi = '777.5' WHERE ma_thua = ?", (t['ma_thua'],))
        d = {x['truong']: x for x in self.nk(bang='ho', hanh_dong='sua')}
        self.assertEqual(set(d), {'nhan_khau', 'ho_ten'})
        self.assertEqual((d['ho_ten']['moi'], d['ho_ten']['nguoi'], d['ho_ten']['ma_ho']), ('Nguyễn Văn Sửa', 'can_bo_a', 1))
        x = self.nk(bang='thua', truong='dt_thu_hoi')[0]
        self.assertEqual((x['cu'], x['moi'], x['ma_thua'], x['ma_ho']), (str(t['dt_thu_hoi']), '777.5', t['ma_thua'], 1))
        self.assertTrue(x['doi_tuong'].startswith('Thửa '))
        kiem_toan.dat_phien(self.con, 'can_bo_b')                       # đăng nhập LAN người khác
        from pabt import ho_so
        ho_so.xoa_ho(self.con, 2)
        x = self.nk(bang='ho', hanh_dong='xoa')[0]
        self.assertEqual((x['ma_ho'], x['nguoi']), (2, 'can_bo_b'))
        self.assertTrue(self.nk(bang='thua', hanh_dong='xoa'))

    def test_luu_phuong_an_tung_truong(self):
        kiem_toan.gan(self.con, 'can_bo_a')
        bo = BoSoan(self.con, 1)
        m = bo.dm.muc[2][0]
        bo.them_tu_danh_muc(2, m)
        bo.pa.khoan[2][-1].so_luong = Decimal('10')
        bo.luu()
        them = self.nk(bang='ct_khoan', hanh_dong='them')
        self.assertEqual(len(them), 1)
        self.assertIn(m.ten, them[0]['doi_tuong'])
        self.assertEqual(them[0]['thao_tac'], 'Lưu phương án hộ')
        bo = BoSoan(self.con, 1)
        bo.pa.khoan[2][-1].so_luong = Decimal('12.5')
        bo.pa.khoan[2][-1].don_gia = Decimal('1000')
        bo.luu()
        sua = {x['truong']: (x['cu'], x['moi']) for x in self.nk(bang='ct_khoan', hanh_dong='sua')}
        self.assertEqual(sua['so_luong'], ('10', '12.5'))
        self.assertEqual(sua['don_gia'][1], '1000')
        bo = BoSoan(self.con, 1)
        bo.pa.khoan[2].clear()
        bo.luu()
        self.assertEqual(len(self.nk(bang='ct_khoan', hanh_dong='xoa')), 1)
        truoc = len(self.nk(bang='ct_khoan'))
        BoSoan(self.con, 1).luu()                                        # lưu không đổi gì: không thêm dòng phương án
        self.assertEqual(len(self.nk(bang='ct_khoan')), truoc)

    def test_tu_lap_khong_ghi(self):
        kiem_toan.gan(self.con)
        bo = BoSoan(self.con, 1)
        bo.them_tu_danh_muc(2, bo.dm.muc[2][0])
        bo.luu(tu_dong=True)
        self.assertEqual(self.nk(bang='ct_khoan'), [])

    def test_hoan_tac_van_dung_va_duoc_ghi_vet(self):
        from pabt import hoan_tac
        ht = hoan_tac.HoanTac(self.con)
        kiem_toan.gan(self.con, 'a')
        goc = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0]
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Tên mới' WHERE ma_ho = 1")
            csdl.ghi_nhat_ky(self.con, 'Sửa hộ')
        ht.chot()
        ht.hoan_tac()
        self.assertEqual(self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0], goc)
        ds = self.nk(truong='ho_ten')                                    # mới nhất trước: hoàn tác, rồi sửa
        self.assertEqual([(x['cu'], x['moi']) for x in ds], [('Tên mới', goc), (goc, 'Tên mới')])

    def test_xuat_excel(self):
        kiem_toan.gan(self.con, 'a')
        with self.con:
            self.con.execute("UPDATE ho SET dia_chi = 'Ấp mới' WHERE ma_ho = 1")
        f = self.td / 'kt.xlsx'
        kiem_toan.xuat_excel(kiem_toan.doc(self.con), f, 'Dự án thử')
        ws = openpyxl.load_workbook(f).active
        self.assertEqual(ws['H6'].value, 'Địa chỉ')
        self.assertEqual(ws['J6'].value, 'Ấp mới')

    def test_cua_so_va_menu(self):
        from PySide6.QtWidgets import QApplication
        from pabt import giao_dien
        from pabt.app import CuaSoChinh
        from pabt.man_hinh_kiem_toan import HopKiemToan
        app = QApplication.instance() or QApplication([])
        giao_dien.ap_dung(app)
        kiem_toan.gan(self.con, 'a')
        with self.con:
            self.con.execute("UPDATE ho SET dia_chi = 'Ấp 1 mới' WHERE ma_ho = 1")
            self.con.execute("UPDATE ho SET dia_chi = 'Ấp 2 mới' WHERE ma_ho = 2")
        h = HopKiemToan(self.con, None, ma_ho=2)
        self.assertEqual(h.bang.rowCount(), 1)
        h.cb_ho.setCurrentIndex(0)
        self.assertEqual(h.bang.rowCount(), 2)
        self.assertTrue(h.xuat(self.td / 'x.xlsx').exists())
        w = CuaSoChinh()
        try:
            self.assertIn('Nhật ký kiểm toán…', [a.text() for a in w.menu_tren['Dữ liệu'].actions()])
            self.assertFalse(w.lenh['Nhật ký kiểm toán…'].isEnabled())     # chưa mở dự án
        finally:
            w.close()


class TestBacSiHoSo(CoSoKt):
    def bac_si(self) -> list:
        return [x.noi_dung for x in kiem_loi.kiem_tra(self.con) if x.nhom == kiem_loi.BAC_SI and x.ma_ho == 1]

    def test_dt_boi_thuong_lon_hon_thu_hoi(self):
        bo = BoSoan(self.con, 1)
        t = next(iter(bo.bc.thua_cua(1)))
        bo.them_thua(t['ma_thua'])
        bo.pa.dat[-1].dien_tich = Decimal(str(t['dt_thu_hoi'])) + 10
        bo.luu()
        loi = [x for x in kiem_loi.kiem_tra(self.con) if x.nhom == kiem_loi.BAC_SI]
        self.assertTrue(any('LỚN HƠN' in x.noi_dung and x.muc_do == kiem_loi.LOI for x in loi), loi)

    def test_ty_le_vuot_100_va_nhan_khau(self):
        bo = BoSoan(self.con, 1)
        bo.them_tu_danh_muc(2, bo.dm.muc[2][0])
        bo.pa.khoan[2][-1].ty_le = Decimal('1.2')
        bo.them_tu_danh_muc(4, next(m for m in bo.dm.muc[4] if m.ma == 'CS1'))     # ổn định đời sống (theo nhân khẩu)
        bo.luu()
        ds = self.bac_si()
        self.assertTrue(any('120%' in x for x in ds), ds)
        self.assertTrue(any('chưa nhập số nhân khẩu' in x for x in ds), ds)
        with self.con:
            self.con.execute('UPDATE ho SET nhan_khau = 25 WHERE ma_ho = 1')
        ds = self.bac_si()
        self.assertTrue(any('lớn bất thường' in x for x in ds), ds)
        self.assertTrue(any('ổn định đời sống tính' in x for x in ds), ds)      # dòng hỗ trợ khác số nhân khẩu của hộ

    def test_han_muc_dat_o_theo_ho_so(self):
        with self.con:
            self.con.execute("UPDATE du_an SET cap_dia_ban = 'Xã' WHERE id = 1")
        bo = BoSoan(self.con, 1)
        t = next(iter(bo.bc.thua_cua(1)))
        bo.them_thua(t['ma_thua'])
        bo.pa.dat[-1].nhom_dat = 'Đất ở'
        bo.pa.dat[-1].dien_tich = Decimal('300')
        bo.luu()
        self.assertFalse(any('hạn mức đất ở' in x for x in self.bac_si()))       # mặc định chưa cấu hình: không kiểm tra
        dia_phuong.file_may().write_text(json.dumps({'quy_tac_kiem_tra': {'han_muc_dat_o_m2': {'xa': 200}}}), encoding='utf-8')
        dia_phuong.nap_lai()
        self.assertTrue(any('vượt hạn mức đất ở 200' in x for x in self.bac_si()), self.bac_si())

    def test_ho_tro_150_phan_tram_khong_bao(self):
        bo = BoSoan(self.con, 1)
        m = next(x for x in bo.dm.muc[4] if x.ma not in ('CS1',))
        bo.them_tu_danh_muc(4, m)
        bo.pa.khoan[4][-1].ty_le = Decimal('1.5')
        bo.luu()
        self.assertFalse(any('vượt 100%' in x for x in self.bac_si()))


class TestNhapHangLoat(unittest.TestCase):
    def test_file_tam_khong_fsync_tung_giao_dich(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            con, tam = csdl.tao_moi_tam(Path(td) / 'a.pabt')
            self.assertEqual(con.execute('PRAGMA synchronous').fetchone()[0], 0)
            self.assertEqual(con.execute('PRAGMA journal_mode').fetchone()[0], 'memory')
            con.close()
            p = csdl.hoan_tat_tao_moi(tam, Path(td) / 'a.pabt')
            c2 = csdl.mo(p)
            try:
                self.assertEqual(c2.execute('PRAGMA journal_mode').fetchone()[0], 'delete')   # file thật: như cũ (1.0.90 thử TRUNCATE - lỗi khi máy khác ghi)
            finally:
                c2.close()

    def test_chuan_hoa_nho_giong_cu(self):
        from pabt.nhap_excel import chuan_hoa
        self.assertEqual(chuan_hoa('Diện tích\nthu hồi'), 'dien tich thu hoi')
        self.assertEqual(chuan_hoa(None), '')
        self.assertEqual(chuan_hoa(12.5), '12.5')
        self.assertEqual(chuan_hoa('ĐẤT Ở'), 'dat o')


if __name__ == '__main__':
    unittest.main()
