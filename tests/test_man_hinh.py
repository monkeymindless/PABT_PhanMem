"""Kiểm thử màn hình giai đoạn 2 bằng PySide6 thật (chế độ không hiển thị). Máy không có PySide6 thì bỏ qua."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_nghiep_vu import FILE_EXCEL

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


@unittest.skipUnless(CO_QT and FILE_EXCEL.exists(), 'cần PySide6 và file Excel mẫu')
class TestManHinhLapPA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        from pabt import nhap_excel
        cls.tmp = tempfile.TemporaryDirectory()
        cls.goc = Path(cls.tmp.name) / 'goc.pabt'
        nhap_excel.nhap(FILE_EXCEL, cls.goc)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        from PySide6.QtWidgets import QMessageBox
        from pabt import csdl
        self.p = Path(self.tmp.name) / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)
        self.con = csdl.mo(self.p)
        self.thong_bao = []
        # hộp thông báo: ghi lại thay vì chờ bấm
        self.va_tam = [mock.patch.object(QMessageBox, 'warning', side_effect=lambda *a, **k: self.thong_bao.append(a[2])),
                   mock.patch.object(QMessageBox, 'information', side_effect=lambda *a, **k: self.thong_bao.append(a[2]))]
        for v in self.va_tam:
            v.start()

    def tearDown(self):
        for v in self.va_tam:
            v.stop()
        self.con.close()

    def _cot(self, w, muc, khoa):
        from pabt.man_hinh import COT_GD
        return [c[0] for c in COT_GD[muc]].index(khoa)

    def test_mo_sua_o_luu(self):
        from pabt import nghiep_vu
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        self.assertEqual(w.tab.count(), 5)                       # thông tin hộ, thửa + 4 mục
        self.assertEqual(w.bang[2].bang.rowCount(), 9)
        self.assertIn('812.506.000', w.lb_tong.text())
        self.assertFalse(w.b_luu.isEnabled())
        # sửa số lượng dòng 2.1 ngay trên lưới
        c = self._cot(w, 2, 'so_luong')
        w.bang[2].bang.item(0, c).setText('130')
        self.assertEqual(w.bo.pa.khoan[2][0].so_luong, 130)
        self.assertTrue(w.windowTitle().startswith('*'))
        self.assertTrue(w.b_luu.isEnabled())
        tt = w.bang[2].bang.item(0, self._cot(w, 2, 'thanh_tien')).text()
        self.assertEqual(tt, '397.020.000')                      # 130 x 3.054.000
        # gõ sai: báo lỗi, ô trở lại giá trị cũ
        w.bang[2].bang.item(0, c).setText('abc')
        self.assertTrue(self.thong_bao and 'không phải là số' in self.thong_bao[-1])
        self.assertEqual(w.bang[2].bang.item(0, c).text(), '130')
        self.assertTrue(w.luu())
        self.assertFalse(w.windowTitle().startswith('*'))
        self.assertEqual(nghiep_vu.tinh_ho(self.con, 1).muc[2], w.bo.ket_qua.muc[2])
        w.close()

    def test_hang_muc_khac_tuong_duong_va_goi_y(self):
        from pabt.man_hinh import ChonDanhMuc, CuaSoLapPA, HopGoiY
        w = CuaSoLapPA(self.con, 1)
        dlg = ChonDanhMuc(w.bo.dm, 2, w, tuong_duong=True, tu_khoa='mái che')
        self.assertGreater(dlg.bang.rowCount(), 0)
        m = dlg.chon_hien_tai()
        self.assertIsNotNone(m)
        i = w.them_hang_muc_khac(2, 'Mái che khung sắt lợp tôn', m_tuong_duong=m)
        self.assertEqual(w.bang[2].bang.rowCount(), 10)
        self.assertEqual(w.bang[2].bang.item(i, self._cot(w, 2, 'nguon')).text(), f'tương đương: {m.ma}')
        w.bang[2].bang.item(i, self._cot(w, 2, 'so_luong')).setText('10')
        self.assertEqual(w.bo.pa.khoan[2][i].so_luong, 10)
        # thêm từ danh mục (cây trồng)
        dlg3 = ChonDanhMuc(w.bo.dm, 3, w)
        dlg3.o_tim.setText('xoai 11-15')
        self.assertGreater(dlg3.bang.rowCount(), 0)
        j = w.them_tu_danh_muc(3, dlg3.chon_hien_tai())
        self.assertEqual(w.bang[3].bang.rowCount(), 4)
        self.assertEqual(j, 3)
        # gợi ý hỗ trợ: HT09 sửa theo quy tắc
        dx, tu = w.bo.goi_y()
        hop = HopGoiY(dx, tu, w)
        self.assertEqual(len(hop.da_chon()), len(dx))
        chon = w.goi_y(tu_dong=True)
        self.assertIn('HT09', [x.ma for x in chon])
        self.assertEqual(w.bo.pa.dong_ho_tro('HT09')[0].don_gia, 135000)
        self.assertTrue(w.luu())
        w.close()

    def test_them_thua_xoa_va_chuyen_ho(self):
        from PySide6.QtWidgets import QMessageBox
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        w.bang[1].bang.setCurrentCell(1, 1)
        w.xoa_dong(1)
        self.assertEqual(w.bang[1].bang.rowCount(), 1)
        mt = next(x[0] for x in w.bo.thua_cua_ho() if '80' in x[1])
        i = w.them_thua(mt)
        w.bang[1].bang.item(i, self._cot(w, 1, 'vi_tri')).setText('1')
        self.assertIn('153.108.000', w.lb_tong.text())
        # chuyển hộ khi còn thay đổi: chọn "Không lưu"
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Discard):
            self.assertTrue(w.chuyen_ho(2))
        self.assertEqual(w.bo.ma_ho, 2)
        self.assertEqual(w.cb_ho.currentData(), 2)
        self.assertEqual(w.bang[1].bang.rowCount(), 2)
        # sửa rồi chuyển hộ, chọn "Hủy": ở lại hộ 2
        w.o_nk.setValue(6)
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(w.chuyen_ho(1))
        self.assertEqual(w.bo.ma_ho, 2)
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Save):
            w.sang_ho(-1)
        self.assertEqual(w.bo.ma_ho, 1)
        self.assertEqual(self.con.execute('SELECT nhan_khau FROM ho WHERE ma_ho = 2').fetchone()[0], 6)
        w.close()

    def test_cua_so_chinh_du_an_ra_soat(self):
        from pabt import app as ud
        w = ud.CuaSoChinh()
        w.mo(str(self.p))
        for ten in ('Lập phương án hộ…', 'Thông tin dự án…', 'Rà soát giá…'):
            self.assertIn(ten, w.lenh)
        lp = w.mo_lap_pa(1, cho=False)
        lp.bang[2].bang.item(0, self._cot(lp, 2, 'so_luong')).setText('5')     # đơn giá danh mục cố định: sửa số lượng
        i = lp.bo.them_hang_muc_khac(2, 'Mái che tạm')                          # giá thực tế khác: hạng mục khác, nhập tay
        lp.bo.sua_khoan(2, i, 'don_gia', '150.000')
        self.assertTrue(lp.luu())
        lp.close()
        w.tai_lai()
        self.assertIn('trừ 1 hộ đã sửa', w.lb_ket_qua.text())
        self.assertEqual(w.bang_tong_hop.tien.dong()[0][13], 'Sửa trong phần mềm')
        rs = w.ra_soat_gia(cho=False)
        self.assertEqual(rs.bang.rowCount(), 1)
        da = w.sua_du_an(cho=False)
        da.o['so_phuong_an'].setText('01/PA-2026')
        da.accept()
        from pabt import lap_pa
        self.assertEqual(lap_pa.doc_du_an(w.con)['so_phuong_an'], '01/PA-2026')
        da2 = w.sua_du_an(cho=False)
        da2.o['ten'].setText('')
        da2.accept()                                     # tên trống: báo lỗi, không lưu
        self.assertTrue(any('Tên dự án' in t for t in self.thong_bao))
        w.close()

    def test_hop_in(self):
        import sys
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        dlg = w.in_xuat(cho=False)
        self.assertEqual(dlg.ds_ho(), [1])
        dlg.o_thu_muc.setText(str(Path(self.tmp.name) / 'in_gui'))
        dlg.r_excel.setChecked(True)
        kq = dlg.thuc_hien(xac_nhan=False)
        self.assertEqual(len(kq['excel']), 1)
        if sys.platform == 'win32' and os.environ.get('PABT_THU_EXCEL', '1') != '0':
            dlg.o_bth.setChecked(True)
            dlg.r_pdf.setChecked(True)
            kq = dlg.thuc_hien(xac_nhan=False)
            self.assertEqual(kq['loi'], [])
            self.assertEqual(len(kq['pdf']), 2)
        dlg.cb_pham_vi.setCurrentIndex(1)
        self.assertEqual(len(dlg.ds_ho()), 2)                       # các hộ đã lập phương án
        # tự chọn: bỏ đánh dấu một hộ -> phạm vi thành "Tự chọn"; lọc + chọn các hộ đang hiện; bỏ chọn tất cả
        from PySide6.QtCore import Qt
        hang = next(i for i in range(dlg.bang_ho.rowCount()) if dlg.bang_ho.item(i, 0).checkState() == Qt.CheckState.Checked)
        dlg.bang_ho.item(hang, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertEqual(dlg.cb_pham_vi.currentData(), 'tu_chon')
        self.assertEqual(len(dlg.ds_ho()), 1)
        self.assertIn('Đã chọn 1 hộ', dlg.lb_chon.text())
        dlg._danh_dau([])
        self.assertEqual(dlg.ds_ho(), [])
        ten = dlg.bang_ho.item(0, 1).text().split('. ', 1)[1]
        dlg.o_tim.setText(ten)
        dlg._danh_dau(dlg._dang_hien(), giu=True)
        self.assertIn(dlg.bang_ho.item(0, 0).data(Qt.ItemDataRole.UserRole), dlg.ds_ho())
        self.assertFalse(dlg.o_so_ban.isEnabled())                 # số bản chỉ dùng khi in ra máy in
        dlg.r_in.setChecked(True)
        self.assertTrue(dlg.o_so_ban.isEnabled() and not dlg.o_gop.isEnabled())
        w.close()


if __name__ == '__main__':
    unittest.main()
