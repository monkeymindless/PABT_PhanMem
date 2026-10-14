"""Người dùng 11/10/2026: (1) thẻ Vật nuôi không xổ danh sách, gõ không tìm được - dự án lập trước khi bộ đơn giá có vật
nuôi (QĐ 31/2025, 0.9.17) không có dòng vật nuôi nào trong danh mục -> nút "Bổ sung vật nuôi từ bộ đơn giá"
(`don_gia.bo_sung_vat_nuoi`, chỉ thêm mục thiếu); (2) ô Nhân khẩu: bấm vào chữ "chưa nhập" chữ không mất, gõ số dính vào
chữ ("ch1ưa nhập") -> `giao_dien.OSoChuaNhap`. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, don_gia, du_an_moi
from pabt.lap_pa import DanhMuc
from pabt.nghiep_vu import MUC_VN, la_vat_nuoi


def _du_an_khong_vat_nuoi(p: Path):
    dong = [dict(ho_ten='Nguyễn Văn Thử', dia_chi='Ấp 1', so_to='10', so_thua='100', loai_dat='CLN', dt_thu_hoi='120',
                 vi_tri='1')]
    du_an_moi.tao_du_an(p, dict(ten='Dự án thử', cap_dia_ban='Xã', ten_dia_ban='Thử', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    con = csdl.mo(p)
    vn = [r['ma'] for r in con.execute('SELECT ma, phan_loai FROM dm_taisan WHERE nhom = 3') if la_vat_nuoi(r['phan_loai'])]
    with con, csdl.mo_khoa_danh_muc(con):                 # như dự án lập trước 0.9.17
        for ma in vn:
            con.execute('DELETE FROM dm_taisan WHERE ma = ?', (ma,))
    return con, len(vn)


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self.con, self.so_vn = _du_an_khong_vat_nuoi(Path(self.tmp.name) / 'thu.pabt')
        self.addCleanup(self.con.close)


class TestBoSungVatNuoi(CoSo):
    def test_chi_them_muc_thieu(self):
        self.assertGreater(self.so_vn, 0)
        self.assertEqual(DanhMuc(self.con).muc[MUC_VN], [])
        truoc = {r['ma']: tuple(r) for r in self.con.execute('SELECT * FROM dm_taisan')}
        self.assertEqual(don_gia.bo_sung_vat_nuoi(self.con), self.so_vn)
        self.assertEqual(len(DanhMuc(self.con).muc[MUC_VN]), self.so_vn)
        sau = {r['ma']: tuple(r) for r in self.con.execute('SELECT * FROM dm_taisan')}
        self.assertEqual({k: sau[k] for k in truoc}, truoc)              # dòng cũ giữ nguyên
        self.assertEqual(don_gia.bo_sung_vat_nuoi(self.con), 0)          # lần hai: không thêm trùng


class TestManHinh(CoSo):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])

    def test_the_vat_nuoi_trong_co_nut_bo_sung(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        try:
            b = w.bang[MUC_VN]
            self.assertFalse(b.khung_thieu_vn.isHidden())
            self.assertEqual(w.bo_sung_vat_nuoi(), self.so_vn)
            self.assertTrue(b.khung_thieu_vn.isHidden())
            self.assertEqual(len(w.bo.dm.muc[MUC_VN]), self.so_vn)
            self.assertTrue(b.o_chon.loc('ao nuoi'))                     # gõ không dấu tìm được
        finally:
            w.bo_thay_doi()
            w.close()

    def test_o_nhan_khau_bam_vao_chu_mat(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from pabt.giao_dien import OSoChuaNhap
        o = OSoChuaNhap('chưa nhập')
        o.setRange(0, 200)
        o.show()
        self.assertEqual(o.text(), 'chưa nhập')
        QTest.mouseClick(o.lineEdit(), Qt.MouseButton.LeftButton, pos=o.lineEdit().rect().center())
        self.assertEqual(o.lineEdit().text(), '')
        QTest.keyClicks(o, '5')
        self.assertEqual(o.value(), 5)
        self.assertEqual(o.text(), '5')
        o.setValue(0)                                                    # hộ khác chưa nhập: hiện lại chữ
        self.assertEqual(o.text(), 'chưa nhập')
        o.clearFocus()
        o.close()


if __name__ == '__main__':
    unittest.main()
