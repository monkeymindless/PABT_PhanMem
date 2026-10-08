"""Kiểm thử lớp an toàn (pabt/an_toan.py): chữ ký số, file nén / XML độc, toàn vẹn bản cài, TLS, quét file, màn hình."""
from __future__ import annotations
import os
import ssl
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from pabt import an_toan


class TestChuKy(unittest.TestCase):
    def test_ky_xac_minh(self):
        k = an_toan.tao_khoa(1024)
        cong = dict(n=k['n'], e=k['e'])
        ck = an_toan.ky(b'noi dung goi', k)
        self.assertTrue(an_toan.xac_minh(b'noi dung goi', ck, cong))
        self.assertFalse(an_toan.xac_minh(b'noi dung goi!', ck, cong))                # nội dung bị sửa
        self.assertFalse(an_toan.xac_minh(b'noi dung goi', ck[:-1] + ('0' if ck[-1] != '0' else '1'), cong))
        self.assertFalse(an_toan.xac_minh(b'noi dung goi', '', cong))
        self.assertFalse(an_toan.xac_minh(b'noi dung goi', 'zz', cong))
        k2 = an_toan.tao_khoa(1024)
        self.assertFalse(an_toan.xac_minh(b'noi dung goi', an_toan.ky(b'noi dung goi', k2), cong))   # khóa khác
        self.assertEqual(int(k['n'], 16).bit_length(), 1024)

    def test_khoa_cong_khai_dong_goi(self):
        # phần mềm phát hành có khóa công khai RSA-3072
        self.assertEqual(int(an_toan.KHOA_CONG_KHAI['n'], 16).bit_length(), 3072)
        self.assertEqual(an_toan.KHOA_CONG_KHAI['e'], 65537)


class TestFileDoc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_bom_nen(self):
        p = self.td / 'bom.xlsx'
        with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('xl/a.xml', b'0' * (60 * 2 ** 20))                           # 60 MB nén còn vài chục KB
        with self.assertRaisesRegex(an_toan.LoiAnToan, 'bom nén'):
            an_toan.kiem_tra_zip(p)
        p2 = self.td / 'vuot.zip'
        with zipfile.ZipFile(p2, 'w') as z:
            z.writestr('../../Windows/x.dll', b'x')
        with self.assertRaisesRegex(an_toan.LoiAnToan, 'đường dẫn nguy hiểm'):
            an_toan.kiem_tra_zip(p2)
        p3 = self.td / 'tot.docx'
        with zipfile.ZipFile(p3, 'w') as z:
            z.writestr('word/document.xml', b'<w:document/>')
        an_toan.kiem_tra_zip(p3)

    def test_xml_thuc_the(self):
        with self.assertRaises(an_toan.LoiAnToan):
            an_toan.kiem_tra_xml(b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "xx">]><a>&x;</a>')
        an_toan.kiem_tra_xml(b'<?xml version="1.0"?><w:document/>')

    def test_docx_doc_bi_chan(self):
        from pabt import nhap_don_gia as ndg
        from pabt.lap_pa import LoiNhap
        p = self.td / 'doc.docx'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types/>')
            z.writestr('word/document.xml', '<!DOCTYPE d [<!ENTITY a "a"><!ENTITY b "&a;&a;">]><d>&b;</d>')
        with self.assertRaisesRegex(LoiNhap, 'DOCTYPE'):
            ndg.doc_bang(p)

    def test_toan_ven(self):
        g = self.td / 'cai'
        (g / '_internal').mkdir(parents=True)
        (g / 'PABT.exe').write_bytes(b'MZ exe')
        (g / '_internal' / 'python3.dll').write_bytes(b'dll')
        (g / '_internal' / 'du_lieu.json').write_text('{}', encoding='utf-8')
        an_toan.tao_toan_ven(g)
        kq = an_toan.kiem_tra_toan_ven(g)
        self.assertEqual((kq['co_ban_ghi'], kq['so_file'], kq['sai'], kq['thieu'], kq['la']), (True, 3, [], [], []))
        self.assertTrue(an_toan.mo_ta_toan_ven(kq)[0])
        (g / '_internal' / 'python3.dll').write_bytes(b'dll bi sua')                  # file bị sửa
        (g / '_internal' / 'du_lieu.json').unlink()                                   # file bị xóa
        (g / 'version.dll').write_bytes(b'dll la')                                     # DLL lạ chèn vào (DLL hijacking)
        (g / 'ghi_chu.txt').write_text('x', encoding='utf-8')                          # file thường: không tính
        kq = an_toan.kiem_tra_toan_ven(g)
        self.assertEqual((kq['sai'], kq['thieu'], kq['la']), (['_internal/python3.dll'], ['_internal/du_lieu.json'], ['version.dll']))
        dat, mt = an_toan.mo_ta_toan_ven(kq)
        self.assertFalse(dat)
        self.assertIn('CẢNH BÁO', mt)
        self.assertFalse(an_toan.kiem_tra_toan_ven(self.td)['co_ban_ghi'])

    def test_tls(self):
        ctx = an_toan.ngu_canh_tls()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertGreaterEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_chan_ma_doc(self):
        p = self.td / 'tai_ve.xlsx'
        p.write_bytes(b'x')
        with mock.patch.object(an_toan, 'quet_file', return_value=an_toan.KetQuaQuet('doc', 'Phát hiện Trojan.', 'thử')):
            with self.assertRaisesRegex(an_toan.LoiAnToan, 'ĐÃ CHẶN'):
                an_toan.chan_ma_doc(p)
        self.assertFalse(p.exists())                                                  # file độc bị xóa
        p.write_bytes(b'x')
        with mock.patch.object(an_toan, 'quet_file', return_value=an_toan.KetQuaQuet('khong_ro', 'Không có bộ quét.')):
            self.assertEqual(an_toan.chan_ma_doc(p).ket_luan, 'khong_ro')            # không quét được: vẫn cho mở
        self.assertTrue(p.exists())

    def test_doc_bao_cao_defender(self):
        """Mã thoát 2 của MpCmdRun dùng chung cho "có mối đe dọa" và lỗi: chỉ báo mã độc khi báo cáo liệt kê mối đe dọa."""
        import subprocess
        p = self.td / 'a.txt'
        p.write_text('x', encoding='utf-8')
        mau = {
            'loi': (2, b'Scan starting...\nCmdTool: Failed with hr = 0x80508023.\n'),
            'sach': (0, b'Scan starting...\nScan finished.\nScanning a.txt found no threats.\n'),
            'doc': (2, b'Scanning a.txt found 1 threats.\n<===LIST OF DETECTED THREATS===>\nThreat   : Virus:DOS/EICAR_Test_File\n'),
        }
        for ten, (ma, ra) in mau.items():
            with self.subTest(ten), mock.patch.object(an_toan, '_mpcmdrun', return_value=Path('MpCmdRun.exe')), \
                    mock.patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], ma, ra, b'')):
                kq = an_toan._quet_defender(p)
                self.assertEqual(kq and kq.ket_luan, {'loi': None, 'sach': 'sach', 'doc': 'doc'}[ten])
        self.assertIn('EICAR', kq.mo_ta)

    @unittest.skipUnless(os.name == 'nt', 'chỉ Windows')
    def test_quet_that(self):
        """Quét file sạch bằng bộ quét thật của máy (Defender / AMSI) - máy không có bộ quét thì 'khong_ro'."""
        p = self.td / 'sach.txt'
        p.write_text('Bảng đơn giá cây trồng', encoding='utf-8')
        self.assertIn(an_toan.quet_file(p).ket_luan, ('sach', 'khong_ro'))
        ma = an_toan.quet_bo_nho(b'noi dung sach', 'thu')
        self.assertTrue(ma is None or ma < an_toan.AMSI_PHAT_HIEN)


class TestManHinh(unittest.TestCase):
    def test_hop_an_toan(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt.man_hinh_an_toan import HopAnToan
        with mock.patch.object(an_toan, 'tinh_trang_diet_virus', return_value=[('Microsoft Defender Antivirus', True, True)]):
            h = HopAnToan()
        h.im_lang = True
        muc = [m for m, _, _ in h.ds]
        self.assertIn('Toàn vẹn bản cài đặt', muc)
        self.assertEqual(h.bang.item(0, 1).text(), 'ĐẠT')
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.txt'
            p.write_text('x', encoding='utf-8')
            with mock.patch.object(an_toan, 'quet_file', return_value=an_toan.KetQuaQuet('sach', 'Không phát hiện.')):
                self.assertFalse(h.quet_file(str(p)).co_ma_doc)
        h.close()


if __name__ == '__main__':
    unittest.main()
