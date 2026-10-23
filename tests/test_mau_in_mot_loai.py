"""Bản cài: %APPDATA%\\PABT\\mau_in chỉ có MỘT trong hai mẫu (Cập nhật mẫu in từ file một sheet) - mẫu còn lại lấy từ bộ mẫu NHÚNG
(1.0.16: bản cài không còn thư mục mau_in đóng gói kèm). Trước đây thư mục chọn theo IN_CHITIET -> bảng tổng hợp FileNotFoundError (tu-kiem "Lập và in thử" LOI), mẫu
bảng tổng hợp đã sửa (thư mục không có IN_CHITIET) bị bỏ qua. Số liệu GIẢ LẬP."""
from __future__ import annotations
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


if __name__ == '__main__':
    unittest.main()
