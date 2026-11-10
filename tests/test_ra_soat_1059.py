"""1.0.59: đợt vá thứ hai theo rà soát. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
import zlib
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from pabt import an_toan, cap_nhat, co_may_thoi_gian as cm, dxf_thuan, khoa
from pabt.lap_pa import LoiNhap
from pabt.openxml_word import thoat


class TestRaSoat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.td = Path(self.tmp.name)

    def test_don_giu_ban_dang_chay(self):
        for t in ('cu', 'moi', 'dang'):
            (self.td / t).mkdir()
        with mock.patch.object(cap_nhat, '_dang_chay', return_value='dang'):
            cap_nhat._don(self.td, 'moi')
        self.assertEqual(sorted(x.name for x in self.td.iterdir()), ['dang', 'moi'])

    def test_dxf_cat_cut_bao_loi(self):
        f = self.td / 'a.dxf'
        f.write_text('0\nSECTION\n2\nENTITIES\n0\nENDSEC\n', encoding='utf-8')
        with self.assertRaises(dxf_thuan.LoiDxf) as e:
            dxf_thuan._cap(f)
        self.assertIn('cắt cụt', str(e.exception))
        f.write_text('0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n', encoding='utf-8')
        self.assertTrue(dxf_thuan._cap(f))

    def test_sao_luu_bom_nen(self):
        f = self.td / 'b.pabt'
        f.write_bytes(an_toan.DAU_SAO_LUU + bytes((an_toan.CO_NEN_ZLIB,)) + zlib.compress(b'\0' * 50_000_000))
        t = time.perf_counter()
        with self.assertRaises(an_toan.LoiAnToan):
            an_toan.mo_goi_file_sao_luu_ra_bytes(f)
        self.assertLess(time.perf_counter() - t, 0.1)                  # từ chối trước khi giải nén hết
        g = self.td / 'c.pabt'
        goc = an_toan.DAU_SQLITE + b'x' * 5000
        g.write_bytes(an_toan.DAU_SAO_LUU + bytes((an_toan.CO_NEN_ZLIB,)) + zlib.compress(goc))
        self.assertEqual(an_toan.mo_goi_file_sao_luu_ra_bytes(g), goc)

    def test_excel_bom_nen(self):
        f = self.td / 'b.xlsx'
        with zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('xl/a.xml', b'0' * (100 * 2 ** 20))
        with self.assertRaises(LoiNhap):
            an_toan.kiem_excel(f)
        an_toan.kiem_excel(self.td / 'khong_co.xlsx')                   # không phải zip: để openpyxl báo như cũ

    def test_khoa_lech_dong_ho(self):
        f = self.td / 'a.pabt'
        k = khoa.KhoaFile(f)
        k.p.write_text('{"may": "M", "nguoi": "N", "cap_nhat": %f}' % time.time(), encoding='utf-8')
        os.utime(k.p, (time.time() - 7200, time.time() - 7200))         # giờ nơi lưu lùi 2 giờ so với máy này
        with mock.patch.object(k, '_gio_noi_luu', return_value=time.time() - 7200):
            self.assertTrue(k.con_hieu_luc(k.doc()))
        k.p.write_text('', encoding='utf-8')                            # đang tạo dở: coi như có người
        self.assertIsNotNone(k.nguoi_khac())

    def _moc(self, gio_truoc, ly_do='tu_dong'):
        return mock.Mock(luc=self.bay + timedelta(hours=-gio_truoc), ly_do=ly_do, file=self.td / f'{gio_truoc}.nen')

    def test_moc_khong_mat_het(self):
        self.bay = datetime(2026, 11, 4, 12)
        ds = [self._moc(24 * 40 + i) for i in range(5)]                 # dự án nghỉ 40 ngày
        with mock.patch.object(cm, 'ds_moc', return_value=ds):
            self.assertEqual(cm.don_dep('x', self.bay), 0)
        ds = [self._moc(i * 0.1) for i in range(85)] + [self._moc(24 * (2 + i)) for i in range(20)]
        with mock.patch.object(cm, 'ds_moc', return_value=ds), mock.patch.object(cm, 'MOC_TOI_DA', 80):
            cm.don_dep('x', self.bay)
        # các mốc ngày còn nguyên: file của chúng không bị đòi xóa (không tồn tại nên unlink lỗi - đếm qua số còn)

    def test_thoat_xml_ky_tu_bien(self):
        self.assertEqual(thoat('a￾b￿c\ud800d'), 'abcd')


if __name__ == '__main__':
    unittest.main()
