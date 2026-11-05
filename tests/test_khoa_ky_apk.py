"""Dựng LARC Mobile không tự sinh khóa ký mới: bản 1.0.60 từng bị ký nhầm khóa tự sinh khi thư mục khóa không ở chỗ mặc định, điện thoại đã cài không cài đè được."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'di_dong'))
import dung  # noqa: E402


class TestKhoaKy(unittest.TestCase):
    def test_khong_thay_khoa_thi_dung_khong_tu_tao(self):
        with tempfile.TemporaryDirectory() as td:
            k = Path(td) / 'khoa' / 'x.jks'
            env = {a: b for a, b in os.environ.items() if a != 'LARC_TAO_KHOA_MOI'}
            with mock.patch.object(dung, 'KHOA', k), mock.patch.dict(os.environ, env, clear=True), mock.patch.object(dung, '_chay') as chay:
                with self.assertRaises(SystemExit) as e:
                    dung.khoa_ky({'keytool': 'keytool'})
            self.assertIn('LARC_KHOA_APK', str(e.exception))
            chay.assert_not_called()
            self.assertFalse(k.parent.exists())

    def test_co_khoa_thi_dung_khoa_do(self):
        with tempfile.TemporaryDirectory() as td:
            k = Path(td) / 'x.jks'
            k.write_bytes(b'k')
            k.with_name('matkhau.txt').write_text('mk\n', encoding='utf-8')
            with mock.patch.object(dung, 'KHOA', k), mock.patch.object(dung, '_chay') as chay:
                self.assertEqual(dung.khoa_ky({'keytool': 'keytool'}), (k, 'mk'))
            chay.assert_not_called()

    def test_tim_ca_trong_repo(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / 'repo'
            (repo / 'khoa_android').mkdir(parents=True)
            with mock.patch.object(dung, 'REPO', repo):
                self.assertEqual(dung._noi_mac_dinh('khoa_android'), repo / 'khoa_android')
                (Path(td) / 'khoa_android').mkdir()
                self.assertEqual(dung._noi_mac_dinh('khoa_android'), Path(td) / 'khoa_android')     # cha repo được ưu tiên như trước
                self.assertEqual(dung._noi_mac_dinh('khong_co'), Path(td) / 'khong_co')


if __name__ == '__main__':
    unittest.main()
