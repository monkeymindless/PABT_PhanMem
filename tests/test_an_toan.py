"""Kiểm thử pabt/an_toan.py (gọn từ 0.9.16): file nén / XML độc, HTTPS; các phần đã bỏ không còn."""
from __future__ import annotations
import os
import ssl
import tempfile
import unittest
import zipfile
from pathlib import Path

from pabt import an_toan


class TestDaBo(unittest.TestCase):
    def test_khong_con_chu_ky_quet_virus_toan_ven(self):
        # người dùng yêu cầu bỏ (0.9.16): chữ ký số gói cập nhật, màn hình "Kiểm tra an toàn", quét virus chủ động, toàn vẹn bản cài
        for ten in ('KHOA_CONG_KHAI', 'ky', 'xac_minh', 'tao_khoa', 'doc_khoa_bi_mat', 'quet_file', 'chan_ma_doc', 'quet_bo_nho',
                    'tinh_trang_diet_virus', 'tong_quan', 'kiem_tra_toan_ven', 'tao_toan_ven'):
            self.assertFalse(hasattr(an_toan, ten), ten)
        import importlib.util
        self.assertIsNone(importlib.util.find_spec('pabt.man_hinh_an_toan'))

    def test_khong_con_lenh_kiem_tra_an_toan(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.assertNotIn('Kiểm tra an toàn…', w.lenh)
        self.assertIn('Xóa hộ…', w.lenh)
        w.close()


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
        dem = b'<!--' + b'x' * 5000 + b'-->'            # DOCTYPE bị chú thích đẩy qua khỏi phần đầu file
        with self.assertRaises(an_toan.LoiAnToan):
            an_toan.kiem_tra_xml(b'<?xml version="1.0"?>' + dem + b'<!DOCTYPE a SYSTEM "file:///c:/x"><a/>')
        with self.assertRaises(an_toan.LoiAnToan):      # XML UTF-16
            an_toan.kiem_tra_xml('<?xml version="1.0"?><!DOCTYPE a><a/>'.encode('utf-16'))

    def test_mo_ta_file_khoa_hong(self):
        from pabt import khoa
        self.assertIn('?', khoa.mo_ta({'may': 'M', 'nguoi': 'N', 'mo_luc': 'hỏng', 'cap_nhat': 1e30}))

    def test_docx_doc_bi_chan(self):
        from pabt import nhap_don_gia as ndg
        from pabt.lap_pa import LoiNhap
        p = self.td / 'doc.docx'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types/>')
            z.writestr('word/document.xml', '<!DOCTYPE d [<!ENTITY a "a"><!ENTITY b "&a;&a;">]><d>&b;</d>')
        with self.assertRaisesRegex(LoiNhap, 'DOCTYPE'):
            ndg.doc_bang(p)

    def test_tls(self):
        ctx = an_toan.ngu_canh_tls()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertGreaterEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)

if __name__ == '__main__':
    unittest.main()
