"""Quy ước tương đương để trống (người dùng 16/10/2026: "xóa toàn bộ quy ước tương đương, để máy trắng - khi nào có tài sản thì
nhập bổ sung sau"): dòng mẫu của bộ đơn giá cũ / file Excel PABT (id < ID_RIENG) bỏ khi mở dự án để sửa, dòng riêng của dự án
giữ; nhập / nạp danh mục từ Excel không chép quy ước mẫu và không làm mất dòng riêng. Dữ liệu GIẢ LẬP."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, don_gia_rieng  # noqa: E402
from pabt.don_gia_rieng import ID_RIENG  # noqa: E402
from tests.test_nghiep_vu import FILE_EXCEL  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402

MAU = [(1, 'Gác lửng khung sắt ván ép', 'Gác để ở của nhà chính (Nhà bán kiên cố)', 'm²', '1854000', 'Áp giá tương đương'),
       (2, 'Mái tôn hiên phụ che nắng', 'Mái che, mái hiên', 'm²', '259000', 'Áp giá tương đương'),
       (ID_RIENG, 'Mái che riêng của dự án', 'Mái che, mái hiên', 'm²', '300000', 'Nhập tay')]


def _ghi_mau(con):
    with con, csdl.mo_khoa_danh_muc(con):
        con.execute('DELETE FROM quy_uoc')
        con.executemany('INSERT INTO quy_uoc (id, ten_thuc_te, ten_tuong_duong, dvt, don_gia, can_cu) VALUES (?,?,?,?,?,?)', MAU)


def _dong(con) -> list:
    return [tuple(r) for r in con.execute('SELECT id, ten_thuc_te FROM quy_uoc ORDER BY id')]


class TestBoQuyUocCu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.tmp.name), 3)
        self.con = csdl.mo(self.p)
        _ghi_mau(self.con)

    def tearDown(self):
        self.doCleanups()
        self.con.close()
        self.tmp.cleanup()

    def test_bo_dong_mau_giu_dong_rieng(self):
        self.assertEqual(don_gia_rieng.bo_quy_uoc_cu(self.con), 2)
        self.assertEqual(_dong(self.con), [(ID_RIENG, 'Mái che riêng của dự án')])
        nk = self.con.execute("SELECT chi_tiet FROM nhat_ky WHERE viec = 'Bỏ quy ước tương đương mẫu'").fetchall()
        self.assertEqual(len(nk), 1)
        self.assertIn('2 dòng', nk[0][0])
        self.assertEqual(don_gia_rieng.bo_quy_uoc_cu(self.con), 0)          # chạy lại: không còn gì, không ghi nhật ký thêm

    def test_mo_du_an_de_sua_thi_bo_chi_xem_thi_khong(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import app as ud
        self.con.close()
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.mo(str(self.p), chi_doc=True)                                     # chỉ xem: không ghi file
        self.assertEqual(len(_dong(w.con)), 3)
        w.dong_du_an()
        w.mo(str(self.p), chi_doc=False)
        self.assertEqual(_dong(w.con), [(ID_RIENG, 'Mái che riêng của dự án')])
        self.assertEqual([m.ten for m in w.dm.muc[9]], ['Mái che riêng của dự án'])     # chọn nhanh mục 2, 3: chỉ dòng riêng
        w.dong_du_an()
        self.con = csdl.mo(self.p)


@unittest.skipUnless(FILE_EXCEL.exists(), f'không có file Excel mẫu {FILE_EXCEL}')
class TestExcelKhongChepQuyUoc(unittest.TestCase):
    def test_nhap_va_nap_danh_muc(self):
        from pabt import nhap_excel, nhap_tho
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.pabt'
            bc = nhap_excel.nhap(FILE_EXCEL, p)
            self.assertFalse(bc.loi, bc.loi)
            self.assertNotIn('quy ước tương đương', bc.so_danh_muc)
            con = csdl.mo(p)
            try:
                self.assertEqual(_dong(con), [])                            # file Excel có sheet quy ước mẫu: không chép
                _ghi_mau(con)
            finally:
                con.close()
            nhap_tho.nap_danh_muc(p, FILE_EXCEL)                            # nạp lại danh mục: dòng riêng của dự án còn
            con = csdl.mo(p)
            try:
                self.assertEqual(_dong(con), [(ID_RIENG, 'Mái che riêng của dự án')])
            finally:
                con.close()


if __name__ == '__main__':
    unittest.main()
