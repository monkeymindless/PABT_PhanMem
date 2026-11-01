"""Phương án đột phá 5 (người dùng 30/10/2026): điện thoại gửi kết quả kiểm đếm thẳng về máy tính qua Wi-Fi nội bộ (nhan_wifi,
man_hinh_nhan_wifi) + mã QR (ma_qr - bản sao độc lập của di_dong/qr.py). Máy chủ chạy trên 127.0.0.1 (không cần mạng thật); dữ liệu
GIẢ LẬP."""
from __future__ import annotations

import http.client
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import ma_qr, nhan_wifi

GOC = Path(__file__).resolve().parents[1]


def _goi(may, phuong_thuc, duong, than=None, dau=None):
    c = http.client.HTTPConnection('127.0.0.1', may._may.server_address[1], timeout=10)
    try:
        c.request(phuong_thuc, duong, body=than, headers=dau or {})
        r = c.getresponse()
        return r.status, r.read()
    finally:
        c.close()


class TestMaQR(unittest.TestCase):
    def test_khop_ban_di_dong(self):
        sys.path.insert(0, str(GOC / 'di_dong'))
        try:
            import qr as qr_di_dong
        finally:
            sys.path.pop(0)
        for chu in ('http://192.168.1.15:8765/AbC123xy/', 'https://vi.du/ứng dụng', 'x' * 150):
            self.assertEqual(ma_qr.ma_qr(chu), qr_di_dong.ma_qr(chu), chu)
        with self.assertRaises(ma_qr.LoiQR):
            ma_qr.ma_qr('x' * 400)


class TestMayNhan(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_wifi_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.may = nhan_wifi.MayNhan('127.0.0.1', self.td / 'hop_thu', 'MAY-THU')
        self.may.bat_dau()
        self.addCleanup(self.may.dung)

    def test_trang_va_ma_phien(self):
        url = self.may.url
        self.assertTrue(url.startswith('http://127.0.0.1:') and url.endswith(f'/{self.may.ma}/'))
        st, than = _goi(self.may, 'GET', f'/{self.may.ma}/')
        self.assertEqual(st, 200)
        self.assertIn('MAY-THU', than.decode('utf-8'))
        for sai in ('/', '/abc/', f'/{self.may.ma}x/', '/../pabt_may_chu.sqlite'):
            self.assertEqual(_goi(self.may, 'GET', sai)[0], 404, sai)
        self.assertEqual(_goi(self.may, 'POST', '/sai/tai_len', b'{}', {'Content-Length': '2'})[0], 404)

    def test_nhan_json_va_chan_file_la(self):
        du = json.dumps({'ket_qua': {'1': []}}, ensure_ascii=False).encode('utf-8')
        st, than = _goi(self.may, 'POST', f'/{self.may.ma}/tai_len', du,
                        {'X-Ten-File': 'K%E1%BA%BFt%20qu%E1%BA%A3%20h%E1%BB%99%201.json', 'Content-Length': str(len(du))})
        self.assertEqual(st, 200, than)
        x = self.may.hang.get_nowait()
        self.assertEqual(x['file'].name, 'Ket_qua_ho_1.json')
        self.assertEqual(x['file'].read_bytes(), du)
        self.assertEqual(x['file'].parent, self.td / 'hop_thu')
        _goi(self.may, 'POST', f'/{self.may.ma}/tai_len', du, {'X-Ten-File': 'Ket qua ho 1.json', 'Content-Length': str(len(du))})
        self.assertEqual(self.may.hang.get_nowait()['file'].name, 'Ket_qua_ho_1~2.json')     # trùng tên: không ghi đè
        # chương trình đổi đuôi .json, ảnh: không nhận, không để lại file
        for la in (b'MZ\x90\x00' + b'\x00' * 60, b'\xff\xd8\xff\xe0' + b'\x00' * 60):
            st, than = _goi(self.may, 'POST', f'/{self.may.ma}/tai_len', la, {'X-Ten-File': 'x.json', 'Content-Length': str(len(la))})
            self.assertEqual(st, 400)
            self.assertIn('loi', json.loads(than))
        self.assertEqual(sorted(p.name for p in (self.td / 'hop_thu').iterdir()), ['Ket_qua_ho_1.json', 'Ket_qua_ho_1~2.json'])
        self.assertEqual(len(self.may.ds_file()), 2)

    def test_qua_lon_va_qua_nhieu(self):
        c = http.client.HTTPConnection('127.0.0.1', self.may._may.server_address[1], timeout=10)
        c.putrequest('POST', f'/{self.may.ma}/tai_len')
        c.putheader('Content-Length', str(nhan_wifi.KICH_TOI_DA + 1))
        c.endheaders()
        r = c.getresponse()
        self.assertEqual(r.status, 413)
        c.close()
        with mock.patch.object(nhan_wifi, 'SO_FILE_TOI_DA', 1):
            du = b'{"ket_qua": {}}'
            dau = {'Content-Length': str(len(du))}
            self.assertEqual(_goi(self.may, 'POST', f'/{self.may.ma}/tai_len', du, dau)[0], 200)
            st, than = _goi(self.may, 'POST', f'/{self.may.ma}/tai_len', du, dau)
            self.assertEqual(st, 400)
            self.assertIn('Đã nhận đủ', json.loads(than)['loi'])

    def test_ten_an_toan_va_tat(self):
        self.assertEqual(nhan_wifi.ten_an_toan('..\\..\\Windows\\x.exe'), 'x.json')
        self.assertEqual(nhan_wifi.ten_an_toan('Đỗ Văn Ánh.json'), 'Do_Van_Anh.json')
        self.assertEqual(nhan_wifi.ten_an_toan(''), 'ket_qua.json')
        cong = self.may._may.server_address[1]
        self.may.dung()
        self.assertFalse(self.may.dang_chay)
        with self.assertRaises(OSError):
            http.client.HTTPConnection('127.0.0.1', cong, timeout=2).request('GET', '/')

    def test_dia_chi_noi_bo(self):
        for ip in nhan_wifi.dia_chi_noi_bo():
            self.assertFalse(ip.startswith('127.') or ip.startswith('169.254.'), ip)


class TestManHinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('không có Qt')
        cls.app = QApplication.instance() or QApplication([])

    def test_hop_nhan_va_nhap(self):
        from pabt.man_hinh_nhan_wifi import HopNhanWifi, anh_qr
        td = Path(tempfile.mkdtemp(prefix='pabt_wifi_mh_'))
        self.addCleanup(shutil.rmtree, td, True)
        da_nhap = []
        with mock.patch.object(nhan_wifi, 'dia_chi_noi_bo', return_value=['127.0.0.1']), \
                mock.patch('pabt.dia_phuong.thu_muc_may', return_value=td):
            h = HopNhanWifi(nhap=lambda f: da_nhap.append(f) or {'so_dong': 3, 'so_ho': 1}, im_lang=True)
        self.addCleanup(h.done, 0)
        self.assertIn(h.may.ma, h.lb_url.text())
        self.assertFalse(h.lb_qr.pixmap().isNull())
        self.assertGreater(anh_qr(h.may.url).width(), 100)
        du = b'{"ket_qua": {}}'
        st, _ = _goi(h.may, 'POST', f'/{h.may.ma}/tai_len', du, {'X-Ten-File': 'kq.json', 'Content-Length': str(len(du))})
        self.assertEqual(st, 200)
        self.assertEqual(h.lay_file_moi(), 1)
        self.assertEqual(h.bang.rowCount(), 1)
        self.assertEqual(h.nhap_dong([0]), 1)
        self.assertEqual(Path(da_nhap[0]).name, 'kq.json')
        self.assertIn('Đã nhập: 3 dòng', h.bang.item(0, 3).text())
        self.assertEqual(h.nhap_dong([0]), 0)                               # đã nhập: không nhập lại
        h.done(0)
        self.assertFalse(h.may.dang_chay)                                   # đóng hộp: tắt máy chủ


if __name__ == '__main__':
    unittest.main()
