"""1.1.05 - máy mới Windows 11 (người dùng 12/11/2026): cài xong hiện hộp "tesseract.exe - Bad Image ... libtesseract-5.dll ... Error
status 0xc0e90002" - Windows (Smart App Control / chính sách kiểm soát ứng dụng) chặn thư viện Tesseract đóng kèm chưa ký số, bước tự
kiểm tra sau khi cài gọi tesseract.exe và trình nạp hiện hộp lỗi hệ thống. Sửa: chạy tesseract.exe với SEM_FAILCRITICALERRORS (không
hộp lỗi), nhận mã thoát lỗi nạp để báo bằng lời; tự kiểm tra coi "Windows chặn" là lưu ý, không phải cài hỏng."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from pabt import ocr

GOC = Path(__file__).resolve().parent.parent


class TestMaLoiNap(unittest.TestCase):
    def test_loai(self):
        self.assertEqual(ocr.loai_loi_nap(0xC0E90002), 'chan')
        self.assertEqual(ocr.loai_loi_nap(-1058471934), 'chan')            # cùng mã dạng số âm (mã thoát có dấu)
        self.assertEqual(ocr.loai_loi_nap(0xC000007B), 'hong')
        self.assertEqual(ocr.loai_loi_nap(1), '')
        self.assertEqual(ocr.loai_loi_nap(None), '')
        self.assertIn('Windows đã chặn', ocr.chu_loi_nap(0xC0E90002))
        self.assertIn('0xc0e90002', ocr.chu_loi_nap(0xC0E90002))
        self.assertEqual(ocr.chu_loi_nap(0), '')

    def test_san_sang_bao_dung_ly_do(self):
        tess = ocr.tim_tesseract() or Path('tesseract.exe')
        bi_chan = subprocess.CompletedProcess([], 0xC0E90002, b'', b'')
        cu = dict(ocr._NGON_NGU)
        ocr._NGON_NGU.clear()
        try:
            with mock.patch.object(ocr, 'tim_tesseract', return_value=tess), \
                    mock.patch.object(ocr, '_chay', return_value=bi_chan), \
                    mock.patch.object(Path, 'stat', return_value=os.stat(__file__)):
                ly_do = ocr.san_sang()
                self.assertIn('Windows đã chặn', ly_do)
                self.assertNotIn('diệt virus', ly_do)
                self.assertTrue(ocr.windows_chan())
        finally:
            ocr._NGON_NGU.update(cu)
            ocr._LOI_NAP.clear()

    def test_doc_tsv_bao_bang_loi(self):
        bi_chan = subprocess.CompletedProcess([], 0xC0E90002, b'', b'')
        with mock.patch.object(ocr, '_chay', return_value=bi_chan):
            with self.assertRaises(ocr.LoiOCR) as e:
                ocr._doc_tsv(Path('tesseract.exe'), Path('a.png'), [])
        self.assertIn('Windows đã chặn', str(e.exception))

    def test_tu_kiem_coi_la_luu_y(self):
        """Tự kiểm tra sau khi cài: Windows chặn -> dòng DAT kèm lời giải thích (bộ cài báo cài xong), không phải LOI."""
        src = (GOC / 'chay.py').read_text(encoding='utf-8')
        i = src.index('def nhan_dang_chu')
        than = src[i:src.index('def huong_dan', i)]
        self.assertIn('ocr.windows_chan()', than)
        self.assertLess(than.index('ocr.windows_chan()'), than.index('raise RuntimeError(ly_do)'))


@unittest.skipUnless(sys.platform == 'win32' and (GOC / 'bo_cai_win' / 'tesseract' / 'tesseract.exe').is_file(),
                     'cần Windows + Tesseract đóng kèm (bo_cai_win/tesseract)')
class TestKhongHienHopLoi(unittest.TestCase):
    def test_dll_hong_khong_treo_hop_loi(self):
        """Chế độ lỗi mặc định (như PABT.exe do bộ cài chạy): trước đây trình nạp hiện hộp "Bad Image" và tesseract.exe đứng chờ người
        bấm OK; nay tesseract.exe thoát ngay với mã lỗi nạp, chế độ lỗi của phần mềm trả lại như cũ."""
        import ctypes
        k32 = ctypes.windll.kernel32
        td = Path(tempfile.mkdtemp(prefix='pabt_1105_bad_'))
        cu = k32.SetErrorMode(0)
        try:
            dich = td / 'tesseract'
            shutil.copytree(GOC / 'bo_cai_win' / 'tesseract', dich, ignore=shutil.ignore_patterns('tessdata'))
            (dich / 'libtesseract-5.dll').write_bytes(b'MZ' + b'\x00' * 4096)
            t = time.monotonic()
            r = ocr._chay([str(dich / 'tesseract.exe'), '--list-langs'], gioi_han=20)
            self.assertLess(time.monotonic() - t, 10)
            self.assertEqual(ocr.loai_loi_nap(r.returncode), 'hong', hex(r.returncode & 0xFFFFFFFF))
            self.assertEqual(k32.GetErrorMode(), 0)
        finally:
            k32.SetErrorMode(cu)
            shutil.rmtree(td, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
