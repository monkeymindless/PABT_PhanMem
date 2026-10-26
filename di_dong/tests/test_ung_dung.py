"""Kiểm thử ứng dụng điện thoại LARC Field Mobile (dự án riêng - không nhập module nào của LARC bản máy tính):

    .venv\\Scripts\\python -m unittest discover -s di_dong\\tests

Đặt LARC_THU_DUNG_APK=1 để dựng .apk thật (cần công cụ Android, ~20 s)."""
from __future__ import annotations
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
DAY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DAY))
import dung  # noqa: E402

THE = ('0. Hồ sơ & Đất', '1. Nhà ở (QĐ 42)', '2. Vật KT', '3. Cây trồng', '4. Ảnh biên bản', '5. Bản đồ KML/GPS', '6. Xuất .JSON')


class TestDocLap(unittest.TestCase):
    def test_khong_dung_ma_may_tinh(self):
        for f in [DAY / 'dung.py', *DAY.joinpath('tests').glob('*.py')]:
            s = f.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'^\s*(from|import)\s+pabt\b', s, re.M), f.name)
        self.assertNotIn('pabt/', dung.MAU.read_text(encoding='utf-8'))
        self.assertTrue(dung.BIEU_TUONG.read_bytes().startswith(b'\x89PNG'))    # biểu tượng của riêng ứng dụng


class TestMau(unittest.TestCase):
    def test_cho_trong_va_the(self):
        s = dung.MAU.read_text(encoding='utf-8')
        self.assertEqual(set(re.findall(r'@@[A-Z_]+@@', s)), {'@@CHE_DO@@', '@@PHIEN_BAN@@', '@@DAU_PWA@@', '@@DU_LIEU_MAC_DINH@@'})
        for t in THE:
            self.assertIn(t, s)
        self.assertNotIn('arguments.callee', s)                         # "use strict": arguments.callee là lỗi
        self.assertIn('<script type="text/plain" id="ma_chinh">', s)    # mã chính chạy sau khi vỏ nạp dữ liệu dự án
        self.assertIn('const DU = window.LARC_DU_LIEU;', s)
        self.assertIn('"larc_field_du_lieu"', s)                        # giao ước README mục 1

    def test_pwa(self):
        s = dung.html_ung_dung('pwa')
        self.assertNotIn('@@', s)
        self.assertIn('const CHE_DO = "pwa"', s)
        self.assertIn('rel="manifest"', s)
        self.assertIn('apple-mobile-web-app-capable', s)
        self.assertIn(f'v{dung.PHIEN_BAN}', s)

    def test_android(self):
        s = dung.html_ung_dung('android')
        self.assertIn('const CHE_DO = "android"', s)
        self.assertNotIn('rel="manifest"', s)
        self.assertIn('window.LARCAndroid', s)                           # lưu / gửi file qua cầu nối của bản cài
        with self.assertRaises(ValueError):
            dung.html_ung_dung('tep')

    def test_danh_muc_nhung_san_va_kiem_dem_doc_lap(self):
        md = dung.du_lieu_mac_dinh()
        self.assertIsNotNone(md, 'thiếu di_dong/danh_muc_mac_dinh.json (chạy chay.py xuat-danh-muc-di-dong)')
        for k in ('nha', 'dm2', 'vat_nuoi'):
            self.assertTrue(md[k] and all(len(m) >= 4 and isinstance(m[3], int) for m in md[k]), k)   # [mã, tên, ĐVT, đơn giá]
        self.assertTrue(md['cay'] and md['cay_chi_tiet'])
        self.assertTrue(any(v['dk'] for v in md['cay_chi_tiet'].values()) and any(v['tuoi'] for v in md['cay_chi_tiet'].values()))
        self.assertEqual((md['ho'], md['du_an']), ([], ''))
        for che_do in ('pwa', 'android'):
            s = dung.html_ung_dung(che_do)
            m = re.search(r'const MAC_DINH = (\{.*?\});\n', s, re.S)
            self.assertTrue(m, che_do)
            self.assertEqual(json.loads(m.group(1))['nha'], md['nha'])
            self.assertIn('id="c_bat_dau"', s)                                         # nút "Bắt đầu kiểm đếm ngay"
            self.assertIn('id="c_quay_lai"', s)                                        # quay lại dự án đang mở
        cu = dung.DANH_MUC_MAC_DINH
        dung.DANH_MUC_MAC_DINH = cu.with_name('khong_co.json')
        try:
            self.assertIn('const MAC_DINH = null;', dung.html_ung_dung('pwa'))
        finally:
            dung.DANH_MUC_MAC_DINH = cu

    def test_cac_hang_muc_giao_dien_thuc_dia(self):
        s = dung.MAU.read_text(encoding='utf-8')
        self.assertRegex(s, r'<input id="n_dt" inputmode="text"')                     # bàn phím đủ phím toán (không chỉ bàn phím số)
        self.assertRegex(s, r'<input id="v_sl" inputmode="text"')
        self.assertEqual(s.count('class="phim_tat_ct"'), 2)
        for chu in ('function goiYLoaiNhaTheoKetCau', 'id="bang_bb"', 'text: "Sửa"', 'function phanTichDongNhanhJS', 'id="m_nen"',
                    'World_Imagery', 'tile.openstreetmap.org', 'id="b_thua_ho"', 'id="b_tam_gps"', 'id="m_tim"', 'id="hop_xem_anh"',
                    'window.LARC_nhanAnhAndroid', 'window.LARC_quayLai', 'id="o_loc_ho"', 'xoaHo(k)', 'await new Promise(r => setTimeout(r, 40))',
                    'id="c_chip"', 'id="n_tam_tinh"', 'id="v_tam_tinh"'):
            self.assertIn(chu, s, chu)
        self.assertNotIn('SpeechRecognition', s)            # không gửi giọng đọc (họ tên, CCCD) lên máy chủ nhận dạng


class TestTep(unittest.TestCase):
    def test_tep_pwa_va_service_worker(self):
        tep = dung.tep_ung_dung('pwa')
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
        self.assertIn(f'larc-field-{dung.PHIEN_BAN}', sw)                # bản mới -> bộ nhớ đệm mới
        for ten in tep:
            if ten != 'sw.js':
                self.assertIn(f'"{ten}"', sw)

    def test_tep_android_gon(self):
        self.assertEqual(set(dung.tep_ung_dung('android')), {'index.html', 'icon-180.png'})

    def test_bieu_tuong_co_va_nen(self):
        from PySide6.QtGui import QImage
        a = QImage.fromData(dung.anh_bieu_tuong(512, 0.12, '#FFFFFF'))
        self.assertEqual((a.width(), a.height()), (512, 512))
        self.assertEqual(a.pixelColor(2, 2).name(), '#ffffff')            # maskable: nền kín, hình trong vùng an toàn


class TestTrangWeb(unittest.TestCase):
    def test_chuan_dia_chi(self):
        self.assertEqual(dung.chuan_dia_chi('https://vd.github.io/larc-field'), 'https://vd.github.io/larc-field/')
        self.assertEqual(dung.chuan_dia_chi(' https://vd.github.io/larc-field/cai-dat.html '), 'https://vd.github.io/larc-field/')
        self.assertEqual(dung.chuan_dia_chi(''), '')
        with self.assertRaises(SystemExit):
            dung.chuan_dia_chi('http://vd.github.io/larc-field/')      # iPhone chỉ cài / định vị trên HTTPS

    def test_trang_cai_dat_co_qr_dung_dia_chi(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_qr import doc_nguoc
        import qr
        s = dung.trang_cai_dat('https://vd.github.io/larc-field/')
        self.assertIn('<svg', s)
        self.assertIn('https://vd.github.io/larc-field/cai-dat.html', s)
        self.assertIn(f'href="{dung.TEP_APK_WEB}"', s)
        self.assertEqual(doc_nguoc(qr.ma_qr('https://vd.github.io/larc-field/cai-dat.html'))[0],
                         'https://vd.github.io/larc-field/cai-dat.html')
        s = dung.trang_cai_dat('', co_apk=False)
        self.assertNotIn('<svg', s)
        self.assertIn('--url', s)
        self.assertNotIn('.apk"', s)

    def test_goi_web(self):
        with tempfile.TemporaryDirectory() as td:
            cu = dung.RA
            dung.RA = Path(td)
            try:
                apk = Path(td) / 'x.apk'
                apk.write_bytes(b'PK\x03\x04')
                goc = dung.dung_web(url='https://vd.github.io/larc-field/', apk=apk)
            finally:
                dung.RA = cu
            ten = {p.name for p in (goc / 'tai_len').iterdir()}
            self.assertTrue({'index.html', 'manifest.webmanifest', 'sw.js', 'cai-dat.html', dung.TEP_APK_WEB} <= ten)
            self.assertTrue((goc / 'HUONG_DAN.txt').exists())
            self.assertTrue(goc.with_name(f'LARC_FieldMobile_Web_{dung.PHIEN_BAN}.zip').exists())


class TestAndroid(unittest.TestCase):
    def test_ma_phien_ban(self):
        self.assertEqual(dung.ma_phien_ban('1.0.31'), 10031)
        self.assertGreater(dung.ma_phien_ban(dung.PHIEN_BAN), 10031)     # lớn hơn bản .apk đầu tiên (dựng theo số 1.0.31)
        self.assertLess(dung.ma_phien_ban('1.9.99'), dung.ma_phien_ban('2.0.0'))

    def test_nguon_khop(self):
        mf = (dung.NGUON_ANDROID / 'AndroidManifest.xml').read_text(encoding='utf-8')
        java = (dung.NGUON_ANDROID / 'src' / 'vn' / 'larc' / 'field' / 'CungCapTep.java').read_text(encoding='utf-8')
        m = re.search(r'android:authorities="([^"]+)"', mf)
        self.assertIn(f'AUTHORITY = "{m.group(1)}"', java)
        self.assertNotIn('android.permission.CAMERA', mf)                  # có quyền CAMERA thì ACTION_IMAGE_CAPTURE đòi xin quyền
        ma = (dung.NGUON_ANDROID / 'src' / 'vn' / 'larc' / 'field' / 'MainActivity.java').read_text(encoding='utf-8')
        self.assertIn('"LARCAndroid"', ma)
        self.assertIn('luuFile', ma)
        # Android 11+: thiếu <queries> thì hộp chọn không thấy ứng dụng máy ảnh
        self.assertRegex(mf, r'<queries>\s*<intent>\s*<action android:name="android.media.action.IMAGE_CAPTURE"/>')
        self.assertIn('public void chupAnhNgay()', ma)
        self.assertIn('LARC_nhanAnhAndroid', ma)
        self.assertIn('LARC_quayLai', ma)
        self.assertNotIn('.restoreState(', ma)              # khôi phục WebView làm mất dữ liệu JS của dự án
        self.assertNotIn('resolveActivity', ma)

    @unittest.skipUnless((dung.CONG_CU / 'jdk17').exists() and os.environ.get('LARC_THU_DUNG_APK') == '1',
                         'Dựng .apk thật: đặt LARC_THU_DUNG_APK=1 (cần công cụ Android)')
    def test_dung_apk_that(self):
        with tempfile.TemporaryDirectory() as td:
            cu = dung.RA
            dung.RA = Path(td)
            try:
                ra = dung.dung_apk()
            finally:
                dung.RA = cu
            with zipfile.ZipFile(ra) as z:
                ten = set(z.namelist())
            self.assertTrue({'classes.dex', 'AndroidManifest.xml', 'assets/index.html', 'assets/icon-180.png'} <= ten)


if __name__ == '__main__':
    unittest.main()
