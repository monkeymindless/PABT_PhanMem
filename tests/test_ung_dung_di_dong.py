"""Ứng dụng điện thoại cài đặt được (người dùng 26/10/2026: "bộ cài .apk cho Android và bản PWA cho iOS"): vỏ ứng dụng KHÔNG chứa dữ liệu
(pabt/phieu_kiem_dem.html chế độ 'pwa' / 'android'), dữ liệu dự án gửi sang bằng file .json "larc_field_du_lieu"; dựng .apk bằng
bo_cai_win/dung_di_dong.py (aapt2 + javac + d8 + apksigner - bài dựng thật bỏ qua khi máy không có công cụ Android). Dữ liệu GIẢ LẬP."""
from __future__ import annotations
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pabt import csdl
from pabt import phieu_kiem_dem as pk
from pabt.lap_pa import LoiNhap
from tests.test_toc_do import _du_an

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / 'bo_cai_win'))
import dung_di_dong  # noqa: E402

app = QApplication.instance() or QApplication([])


class TestVoUngDung(unittest.TestCase):
    def test_vo_pwa_khong_du_lieu_co_manifest(self):
        s = pk.html_ung_dung('pwa')
        self.assertNotIn('@@', s)
        self.assertIn('const CHE_DO = "pwa"', s)
        self.assertIn('<script type="text/plain" id="ma_chinh">', s)       # mã chính chạy sau khi vỏ nạp dữ liệu
        self.assertIn('window.LARC_DU_LIEU || null', s)
        self.assertIn('rel="manifest"', s)
        self.assertIn('apple-mobile-web-app-capable', s)
        self.assertIn('src="icon-180.png"', s)

    def test_vo_android_khong_manifest(self):
        s = pk.html_ung_dung('android')
        self.assertIn('const CHE_DO = "android"', s)
        self.assertNotIn('rel="manifest"', s)
        self.assertIn('window.LARCAndroid', s)                             # lưu / gửi file qua cầu nối của bản cài
        with self.assertRaises(ValueError):
            pk.html_ung_dung('tep')

    def test_tep_pwa_va_service_worker(self):
        tep = pk.tep_ung_dung('pwa')
        self.assertEqual(set(tep), {'index.html', 'manifest.webmanifest', 'sw.js', 'icon-180.png', 'icon-192.png', 'icon-512.png',
                                    'icon-maskable-512.png'})
        for ten, du in tep.items():
            if ten.endswith('.png'):
                self.assertTrue(du.startswith(b'\x89PNG'), ten)
        mf = json.loads(tep['manifest.webmanifest'])
        self.assertEqual((mf['display'], mf['start_url'], mf['theme_color']), ('standalone', './', '#2F5F9E'))
        self.assertEqual({i['sizes'] for i in mf['icons']}, {'192x192', '512x512'})
        self.assertIn('maskable', {i['purpose'] for i in mf['icons']})
        sw = tep['sw.js'].decode('utf-8')
        from pabt import __version__
        self.assertIn(f'larc-field-{__version__}', sw)                     # bản mới -> bộ nhớ đệm mới
        for ten in tep:
            if ten != 'sw.js':
                self.assertIn(f'"{ten}"', sw)

    def test_tep_android_gon(self):
        self.assertEqual(set(pk.tep_ung_dung('android')), {'index.html', 'icon-180.png'})

    def test_bieu_tuong_co_va_nen(self):
        from PySide6.QtGui import QImage
        a = QImage.fromData(pk.anh_bieu_tuong(512, 0.12, '#FFFFFF'))
        self.assertEqual((a.width(), a.height()), (512, 512))
        self.assertEqual(a.pixelColor(2, 2).name(), '#ffffff')            # maskable: nền kín, hình trong vùng an toàn

    def test_phieu_mot_file_khong_doi(self):
        with tempfile.TemporaryDirectory() as td:
            con = csdl.mo(_du_an(Path(td), 2))
            try:
                s = pk.xuat_phieu_kiem_dem_html(con, Path(td) / 'p.html').read_text(encoding='utf-8')
            finally:
                con.close()
        self.assertNotIn('@@', s)
        self.assertIn('const CHE_DO = "tep"', s)
        self.assertIn('<script id="ma_chinh">', s)
        self.assertNotIn('rel="manifest"', s)
        self.assertIsNone(re.search(r'const DU = window\.LARC_DU_LIEU \|\| null;', s))


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
        self.assertEqual(g['loai'], pk.LOAI_GOI_DU_LIEU)
        self.assertEqual(len(g['du_lieu']['ho']), 3)
        self.assertIn('kinh_tuyen', g['du_lieu'])
        self.assertRegex(pk.ten_file_du_lieu(self.con), r'^LARC_DuLieu_[A-Za-z0-9_]+\.json$')

    def test_nhap_nham_file_du_lieu_bao_ro(self):
        f = pk.xuat_du_lieu_di_dong(self.con, Path(self.td.name) / 'dl.json')
        with self.assertRaises(LoiNhap) as e:
            pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertIn('DỮ LIỆU DỰ ÁN', str(e.exception))

    def test_nut_xuat_du_lieu(self):
        from pabt.man_hinh_kiem_dem import HopKiemDem
        h = HopKiemDem(None, self.con, self.p, im_lang=True)
        try:
            self.assertIsNone(h.xuat_du_lieu())                           # im_lặng, không chọn file: không làm gì
            ra = h.xuat_du_lieu(Path(self.td.name) / 'a.json')
            self.assertTrue(ra.exists())
            self.assertIn('Xuất dữ liệu', h.b_du_lieu.text())
        finally:
            h.deleteLater()


class TestDungAndroid(unittest.TestCase):
    def test_ma_phien_ban(self):
        self.assertEqual(dung_di_dong.ma_phien_ban('1.0.31'), 10031)
        self.assertLess(dung_di_dong.ma_phien_ban('1.9.99'), dung_di_dong.ma_phien_ban('2.0.0'))

    def test_nguon_android_khop(self):
        mf = (GOC / 'bo_cai_win' / 'android' / 'AndroidManifest.xml').read_text(encoding='utf-8')
        java = (GOC / 'bo_cai_win' / 'android' / 'src' / 'vn' / 'larc' / 'field' / 'CungCapTep.java').read_text(encoding='utf-8')
        m = re.search(r'android:authorities="([^"]+)"', mf)
        self.assertIn(f'AUTHORITY = "{m.group(1)}"', java)
        self.assertNotIn('android.permission.CAMERA', mf)                  # có quyền CAMERA thì ACTION_IMAGE_CAPTURE đòi xin quyền
        ma = (GOC / 'bo_cai_win' / 'android' / 'src' / 'vn' / 'larc' / 'field' / 'MainActivity.java').read_text(encoding='utf-8')
        self.assertIn('"LARCAndroid"', ma)
        self.assertIn('luuFile', ma)

    @unittest.skipUnless((dung_di_dong.CONG_CU / 'jdk17').exists() and os.environ.get('PABT_THU_DUNG_APK') == '1',
                         'Dựng .apk thật: đặt PABT_THU_DUNG_APK=1 (cần công cụ Android, ~20 s)')
    def test_dung_apk_that(self):
        with tempfile.TemporaryDirectory() as td:
            cu = dung_di_dong.RA
            dung_di_dong.RA = Path(td)
            try:
                ra = dung_di_dong.dung_apk('1.0.31')
            finally:
                dung_di_dong.RA = cu
            with zipfile.ZipFile(ra) as z:
                ten = set(z.namelist())
            self.assertTrue({'classes.dex', 'AndroidManifest.xml', 'assets/index.html', 'assets/icon-180.png'} <= ten)


if __name__ == '__main__':
    unittest.main()
