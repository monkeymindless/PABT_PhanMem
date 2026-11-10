"""Rà soát 06/11/2026: hộp "Lưu thành" gợi ý thư mục chứa file dự án (người dùng 05/11/2026); bản In báo kết quả."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl  # noqa: E402


class TestDuongGoiY(unittest.TestCase):
    def test_thu_muc_du_an(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'a.sqlite'
            con = sqlite3.connect(str(f))
            try:
                goc = Path(csdl.duong_goi_y(con))
                self.assertEqual(goc.resolve(), Path(td).resolve())
                self.assertEqual(Path(csdl.duong_goi_y(con, 'x.xlsx')).name, 'x.xlsx')
                self.assertEqual(Path(csdl.duong_goi_y(con, 'x.xlsx')).parent.resolve(), Path(td).resolve())
            finally:
                con.close()

    def test_bo_nho_va_ban_sao_luu_khong_goi_y_thu_muc(self):
        con = sqlite3.connect(':memory:')
        self.assertEqual(csdl.duong_goi_y(con, 'x.xlsx'), 'x.xlsx')
        con.close()

        class Gia:
            _file_tam = 'tam'

            def execute(self, *_):
                class K:
                    def fetchone(self):
                        return (0, 'main', r'C:\\Temp\\tam.pabt')
                return K()
        self.assertEqual(csdl.duong_goi_y(Gia(), 'x.xlsx'), 'x.xlsx')


class TestHopXuat(unittest.TestCase):
    def test_du_thao_goi_y_thu_muc_du_an(self):
        from pabt import man_hinh_du_thao as md
        lop = next(v for v in vars(md).values() if isinstance(v, type) and '_luu_file' in vars(v))
        with tempfile.TemporaryDirectory() as td:
            con = sqlite3.connect(str(Path(td) / 'a.sqlite'))
            gia = mock.Mock(con=con)
            gia._dot_id.return_value = 1
            with mock.patch.object(md.QFileDialog, 'getSaveFileName', return_value=('', '')) as hop:
                lop._luu_file(gia, 'Báo cáo', lambda d, p: p)
            con.close()
            p = Path(hop.call_args[0][2])
            self.assertEqual(p.name, 'Báo cáo.xlsx')
            self.assertEqual(p.parent.resolve(), Path(td).resolve())


if __name__ == '__main__':
    unittest.main()
