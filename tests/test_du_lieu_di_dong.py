"""Phần MÁY TÍNH của ứng dụng điện thoại LARC Field Mobile (người dùng 26/10/2026: tách ứng dụng thành dự án riêng ở di_dong/, "không liên
quan đến mã nguồn của LARC bản máy tính"): bản máy tính chỉ xuất file dữ liệu dự án .json "larc_field_du_lieu" và nhập kết quả .json;
không đóng gói, không đọc file nào của di_dong/. Kiểm thử của ứng dụng ở di_dong/tests. Dữ liệu GIẢ LẬP."""
from __future__ import annotations
import json
import re
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pabt import csdl
from pabt import phieu_kiem_dem as pk
from pabt.lap_pa import LoiNhap
from tests.test_toc_do import _du_an

GOC = Path(__file__).resolve().parent.parent
app = QApplication.instance() or QApplication([])


class TestDuLieuDuAn(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name), 3)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_goi_du_lieu(self):
        f = pk.xuat_du_lieu_di_dong(self.con, Path(self.td.name) / 'dl.json')
        g = json.loads(f.read_text(encoding='utf-8'))
        self.assertEqual((g['loai'], g['phien_ban']), (pk.LOAI_GOI_DU_LIEU, 1))
        self.assertEqual(len(g['du_lieu']['ho']), 3)
        self.assertTrue({'du_an', 'ho', 'nha', 'dm2', 'vat_nuoi', 'cay', 'goi_y', 'kinh_tuyen', 'datum', 'quy_uoc', 'ban_do',
                         'trang_thai_ho', 'mau_trang_thai'} <= set(g['du_lieu']))      # giao ước di_dong/README.md mục 1
        self.assertRegex(pk.ten_file_du_lieu(self.con), r'^LARC_DuLieu_[A-Za-z0-9_]+\.json$')

    def test_nhap_nham_file_du_lieu_bao_ro(self):
        f = pk.xuat_du_lieu_di_dong(self.con, Path(self.td.name) / 'dl.json')
        with self.assertRaises(LoiNhap) as e:
            pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertIn('DỮ LIỆU DỰ ÁN', str(e.exception))

    def test_hop_kiem_dem_chi_con_json(self):
        from PySide6.QtWidgets import QPushButton
        from pabt.man_hinh_kiem_dem import HopKiemDem
        h = HopKiemDem(None, self.con, self.p, im_lang=True)
        try:
            self.assertIsNone(h.xuat_du_lieu())                           # im lặng, không chọn file: không làm gì
            self.assertTrue(h.xuat_du_lieu(Path(self.td.name) / 'a.json').exists())
            chu = [b.text() for b in h.findChildren(QPushButton)]
            self.assertIn('Xuất dữ liệu cho ứng dụng điện thoại…', chu)
            self.assertFalse([c for c in chu if '.html' in c])             # không còn xuất phiếu .html
            self.assertFalse(hasattr(h, 'xuat'))
        finally:
            h.deleteLater()


class TestTachRieng(unittest.TestCase):
    def test_may_tinh_khong_dung_ma_di_dong(self):
        ds = list((GOC / 'pabt').glob('*.py')) + [GOC / 'PABT.spec', GOC / 'chay.py', GOC / 'bo_cai_win' / 'dung_exe38.py']
        mau = re.compile(r'ung_dung[/\\]+index\.html|phieu_kiem_dem\.html|^\s*(from\s+\S+\s+)?import\s+dung\b|di_dong[./\\]+dung', re.M)
        for f in ds:
            m = mau.search(f.read_text(encoding='utf-8'))
            self.assertIsNone(m, f'{f.name}: "{m.group(0) if m else ""}"')
        self.assertFalse((GOC / 'pabt' / 'phieu_kiem_dem.html').exists())
        for ten in ('xuat_phieu_kiem_dem_html', 'html_ung_dung', 'tep_ung_dung', 'anh_bieu_tuong'):
            self.assertFalse(hasattr(pk, ten), ten)


if __name__ == '__main__':
    unittest.main()
