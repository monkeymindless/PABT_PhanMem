"""1.1.04 (rà kiến trúc 11/11/2026, ket_qua_kiem_tra/DaiPhau_2026-11-11_1102): sao lưu một lần sau khi mở dự án, hai hàm nóng của
trang Tổng hợp tiền / Tiến độ, câu SQL bảng phụ ở module lá. Mọi thay đổi KHÔNG đổi kết quả - các bài dưới đây so với cách cũ.
Dự án GIẢ LẬP (tests.test_toc_do._du_an); thư mục máy tạm (PABT_THU_MUC_MAY)."""
from __future__ import annotations

import ast
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import co_may_thoi_gian as cm
from pabt import csdl, kinh_phi_du_an, loai_dat, sql_bang_phu, thoi_han
from tests.test_toc_do import _du_an

GOC = Path(__file__).resolve().parent.parent / 'pabt'


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1104_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.f = _du_an(self.td, 6)
        self.con = csdl.mo(self.f)

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)


class TestSaoLuuMotLan(_Co):
    def _ho(self, file) -> list:
        c = csdl.mo(file, chi_doc=True)
        try:
            return [tuple(r) for r in c.execute('SELECT ma_ho, ho_ten FROM ho ORDER BY ma_ho')]
        finally:
            c.close()

    def test_moc_tu_ban_sao_giong_moc_tu_chup(self):
        """Mốc chép từ bản sao lưu tự động = mốc tự sao chép: cùng nội dung file, cùng tóm tắt, mở lại đủ hộ."""
        ban_sao = csdl.sao_luu_tu_dong(self.con, self.f)
        a = cm.chup_moc(self.con, self.f, 'mo', tu_ban_sao=ban_sao)
        b = cm.chup_moc(self.con, self.f, 'tay', bat_buoc=True)
        self.assertEqual(a.file.read_bytes(), ban_sao.read_bytes())
        self.assertEqual((a.so_ho, a.tong, a.dau), (b.so_ho, b.tong, b.dau))
        self.assertEqual(self._ho(a.file), self._ho(b.file))
        self.assertEqual(len(self._ho(a.file)), 6)
        self.assertTrue(a.file.with_suffix('.json').is_file())
        self.assertFalse(list(a.file.parent.glob('*.tmp')))

    def test_khong_sao_chep_lan_hai(self):
        """Có bản sao sẵn thì chup_moc không gọi lại sao chép SQLite / nén."""
        ban_sao = csdl.sao_luu_tu_dong(self.con, self.f)
        with mock.patch('pabt.an_toan.dong_goi_file_sao_luu', side_effect=AssertionError('nén lần hai')), \
                mock.patch('pabt.csdl.bo_anh_ban_do_ban_sao', side_effect=AssertionError('sao chép lần hai')):
            self.assertIsNotNone(cm.chup_moc(self.con, self.f, 'mo', tu_ban_sao=ban_sao))

    def test_ban_sao_khong_co_thi_tu_chup(self):
        """Sao lưu tự động lỗi / bỏ qua (None, file đã mất): mốc vẫn được chụp theo cách cũ."""
        self.assertIsNotNone(cm.chup_moc(self.con, self.f, 'mo', tu_ban_sao=None))
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Đổi' WHERE ma_ho = 1")
        m = cm.chup_moc(self.con, self.f, tu_ban_sao=self.td / 'khong_co.larc')
        self.assertEqual(self._ho(m.file)[0][1], 'Đổi')

    def test_van_bo_qua_khi_chua_doi(self):
        ban_sao = csdl.sao_luu_tu_dong(self.con, self.f)
        self.assertIsNotNone(cm.chup_moc(self.con, self.f, 'mo', tu_ban_sao=ban_sao))
        self.assertIsNone(cm.chup_moc(self.con, self.f, 'mo', tu_ban_sao=ban_sao))      # chưa đổi từ mốc trước: không chụp

    def test_cua_so_chinh_mot_lan_sao_chep(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        try:
            w.mo(self.f, chi_doc=False)
            goc = csdl.bo_anh_ban_do_ban_sao
            dem = []
            with mock.patch('pabt.csdl.bo_anh_ban_do_ban_sao', side_effect=lambda dc: (dem.append(1), goc(dc))[1]):
                w._sao_luu_va_moc_khi_mo(w.con, w.file)
            self.assertEqual(len(dem), 1)
            self.assertEqual(len(csdl.ds_sao_luu_tu_dong(self.f)), 1)
            ds = cm.ds_moc(self.f)
            self.assertEqual([m.ly_do for m in ds], ['mo'])
            self.assertEqual(ds[0].file.read_bytes(), csdl.ds_sao_luu_tu_dong(self.f)[0].read_bytes())
        finally:
            w.dong_du_an()
            w.close()
            w.deleteLater()


class TestHamNong(_Co):
    def test_phan_nhom_dat_nhu_cach_cu(self):
        nhom = {ma: g for ma, _, g in loai_dat.LOAI_DAT}

        def cu(loai):
            ma_ds = [m for m in re.split(r'[\s+,;/&-]+', str(loai or '').upper()) if m]
            if not ma_ds:
                return 'khong_ro'
            g = [nhom.get(m) for m in ma_ds]
            if any(x == loai_dat.PHI_NONG_NGHIEP for x in g):
                return 'pnn'
            return 'nn' if all(x == loai_dat.NONG_NGHIEP for x in g) else 'khong_ro'
        mau = [None, '', ' ', 'ont', 'ONT+CLN', 'CLN, LUC', 'LUC;BHK/NTS', 'XYZ', 'CLN-XYZ', 'ONT & CLN', 'bcs', 'CLN+BCS', 'odt  cln']
        mau += [ma for ma, _, _ in loai_dat.LOAI_DAT]
        for x in mau:
            self.assertEqual(thoi_han.phan_nhom_dat(x), cu(x), x)

    def test_tien_dat_theo_nhom_nhu_cach_cu(self):
        from pabt.nghiep_vu import BoiCanh, doc_tat_ca_phuong_an, thanh_tien_dong_dat
        from pabt.tien import KHONG
        bc = BoiCanh.tu(self.con)
        tien = {k: KHONG for k, _ in kinh_phi_du_an.NHOM_DAT_CON}
        ho = {k: set() for k, _ in kinh_phi_du_an.NHOM_DAT_CON}
        for ma, pa in doc_tat_ca_phuong_an(self.con).items():
            for d in pa.dat:
                k = kinh_phi_du_an._nhom_dat_con(d.loai_dat, d.nhom_dat)
                v = thanh_tien_dong_dat(d, bc)
                tien[k] += v
                if v > 0:
                    ho[k].add(ma)
        cu = {k: (tien[k], len(ho[k])) for k in tien}
        moi = kinh_phi_du_an.tien_dat_theo_nhom(self.con)
        self.assertEqual(moi, cu)
        self.assertGreater(sum(v for v, _ in moi.values()), 0)


class TestSqlBangPhu(unittest.TestCase):
    def test_ten_cu_cung_doi_tuong(self):
        from pabt import ban_do_cad, phieu_kiem_dem, van_dong
        self.assertIs(van_dong._SQL_TAO, sql_bang_phu.SQL_VAN_DONG)
        self.assertIs(ban_do_cad.SQL_BANG, sql_bang_phu.SQL_BAN_DO)
        self.assertIs(phieu_kiem_dem.SQL_BANG_ANH, sql_bang_phu.SQL_ANH)
        self.assertEqual((van_dong.BANG, ban_do_cad.BANG, phieu_kiem_dem.BANG_ANH),
                         ('nhat_ky_van_dong', 'thua_ban_do', 'anh_hien_trang'))

    def _nhap(self, ten_file: str) -> set:
        kq = set()
        for n in ast.walk(ast.parse((GOC / ten_file).read_text(encoding='utf-8'))):
            if isinstance(n, ast.ImportFrom) and n.level >= 1:
                kq |= {n.module.split('.')[0]} if n.module else {a.name for a in n.names}
        return kq

    def test_module_la_va_csdl_khong_nhap_nguoc(self):
        self.assertEqual(self._nhap('sql_bang_phu.py'), set())
        self.assertFalse(self._nhap('csdl.py') & {'van_dong', 'ban_do_cad', 'phieu_kiem_dem'})

    def test_file_co_ho_du_bang_phu(self):
        td = Path(tempfile.mkdtemp(prefix='pabt_1104_sql_'))
        try:
            con = csdl.mo(_du_an(td, 2))
            try:
                co = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            finally:
                con.close()
            self.assertTrue({'nhat_ky_van_dong', 'thua_ban_do', 'anh_hien_trang'} <= co)
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
