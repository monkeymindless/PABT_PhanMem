"""Bản cài: %APPDATA%\\PABT\\mau_in chỉ có MỘT trong hai mẫu (Cập nhật mẫu in từ file một sheet) - mẫu còn lại lấy từ bộ mẫu NHÚNG
(1.0.16: bản cài không còn thư mục mau_in đóng gói kèm). Trước đây thư mục chọn theo IN_CHITIET -> bảng tổng hợp FileNotFoundError (tu-kiem "Lập và in thử" LOI), mẫu
bảng tổng hợp đã sửa (thư mục không có IN_CHITIET) bị bỏ qua. Số liệu GIẢ LẬP."""
from __future__ import annotations
import shutil
import sys
import tempfile
import os
import unittest
from pathlib import Path
from unittest import mock

from pabt import in_an

GOC = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.environ.get('PABT_CHI_MAU_NHUNG') == '1',
                 'giả lập máy trắng (1.0.07): bài này giả lập bản cài CÓ thư mục mau_in cạnh PABT.exe')
class TestMauInMotLoai(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ghi = Path(self.tmp.name) / 'mau_in'
        self.ghi.mkdir()
        for p in (mock.patch.object(sys, 'frozen', True, create=True),
                  mock.patch.object(in_an, 'thu_muc_mau_ghi', lambda: self.ghi)):
            p.start()
            self.addCleanup(p.stop)

    def test_chi_co_mau_chi_tiet(self):
        shutil.copy(GOC / 'mau_in' / 'IN_CHITIET.xlsx', self.ghi)
        self.assertEqual(in_an.file_mau(None, in_an.TEN_CT).parent, self.ghi)
        self.assertTrue(in_an.la_mau_nhung(in_an.file_mau(None, in_an.TEN_BTH)))    # 1.0.16: bản cài không đóng mau_in - mẫu còn lại là mẫu NHÚNG
        self.assertNotEqual(in_an.file_mau(None, in_an.TEN_BTH).parent, self.ghi)

    def test_chi_co_mau_bang_tong_hop(self):
        shutil.copy(GOC / 'mau_in' / 'IN_BANGTONGHOP.xlsx', self.ghi)
        self.assertEqual(in_an.file_mau(None, in_an.TEN_BTH).parent, self.ghi)       # mẫu đã sửa được dùng
        self.assertTrue(in_an.la_mau_nhung(in_an.file_mau(None, in_an.TEN_CT)))
        self.assertEqual([t for t, _ in in_an.ds_mau(in_an.TEN_BTH)][:1], ['Mẫu chính'])

    def test_mau_de_sua_chep_mau_con_thieu(self):
        shutil.copy(GOC / 'mau_in' / 'IN_CHITIET.xlsx', self.ghi)
        self.assertEqual(in_an.mau_de_sua(in_an.TEN_BTH), self.ghi / 'IN_BANGTONGHOP.xlsx')
        self.assertTrue((self.ghi / 'IN_BANGTONGHOP.xlsx').exists())


if __name__ == '__main__':
    unittest.main()
