"""05/11/2026 (người dùng): bảng In / Xuất tối giản: Một hộ | Nhiều hộ | Xuất dữ liệu, mặc định Dự thảo, lưu vào thư mục chứa file dự án; định dạng Word / Excel / PDF độc lập."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl

from tests import APP


def _gia_pdf(viec, **kw):
    """Thay Word: viết file PDF giả đúng chỗ."""
    for _che_do, _nguon, dich in viec:
        if dich:
            Path(dich).write_bytes(b'%PDF-1.4 thu')
    return []


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestBangIn(unittest.TestCase):
    def setUp(self):
        from tests.test_phien_ban_pa import _du_an as tao
        self.td = Path(tempfile.mkdtemp(prefix='pabt_in_'))
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if self._cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', self._cu))
        (self.td / 'duan').mkdir()
        self.p = tao(self.td / 'duan', 3)
        self.con = csdl.mo(str(self.p))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def _hop(self, **kw):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=str(self.p), **kw)
        h.im_lang = True
        self.addCleanup(h.w_preview.don_dep)
        return h

    def test_mo_mac_dinh_du_thao_luu_vao_thu_muc_du_an(self):
        h = self._hop(ma_ho_chon=self.ma[:1])
        self.assertEqual(h.che_do(), 'du_thao')
        self.assertEqual(h.the_che_do.currentIndex(), 0)
        self.assertEqual(Path(h.o_thu_muc.text()).parent, self.p.parent)
        self.assertFalse(h.lb_luu.text().startswith(str(self.p.anchor)))             # hiện phần cuối đường dẫn, đủ ở chú thích
        self.assertEqual(h.lb_luu.toolTip(), h.o_thu_muc.text())

    def test_khong_nho_thu_muc_lan_truoc(self):
        class Cd(dict):
            def value(self, k, md=None):
                return self.get(k, md)
            setValue = dict.__setitem__
        cd = Cd({'in/thu_muc_cha': str(self.td)})
        with mock.patch('pabt.giao_dien.cai_dat_nho', lambda: cd):
            h = self._hop()
        self.assertEqual(Path(h.o_thu_muc.text()).parent, self.p.parent)

    def test_mot_ho_chi_co_phan_can_thiet(self):
        h = self._hop(ma_ho_chon=[self.ma[1]])
        self.assertEqual(h.pham_vi_in(), 'mot')
        self.assertEqual(h.ds_ho(), [self.ma[1]])
        self.assertTrue(h.bang_ho.isColumnHidden(0))
        for w in (h.khung_loc, h.khung_kem, h.o_gop, h.b_xem_nhieu, h.b_xem_bth, h.b_chon_het):
            self.assertTrue(w.isHidden())
        h.bang_ho.setCurrentCell(2, 1)                                               # đổi hộ bằng một lần bấm
        self.assertEqual(h.ds_ho(), [self.ma[2]])

    def test_mot_ho_chi_xuat_phuong_an_khong_chia_thu_muc(self):
        h = self._hop(ma_ho_chon=[self.ma[0]])
        h.o_bth.setChecked(True)                                                     # còn tích từ thẻ Nhiều hộ: thẻ Một hộ không xuất
        h.r_excel.setChecked(True)
        tm = self.p.parent / 'ra'
        h.o_thu_muc.setText(str(tm))
        kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual([f.parent for f in kq['word']], [tm])
        self.assertEqual(kq['excel'], [])
        self.assertFalse((tm / 'PA TONG').exists())

    def test_nhieu_ho_xem_truoc_du_bon_nut_va_kem_theo(self):
        h = self._hop()
        self.assertEqual(h.pham_vi_in(), 'nhieu')
        for w in (h.khung_loc, h.khung_kem, h.o_gop, h.b_xem_nhieu, h.b_xem_bth):
            self.assertFalse(w.isHidden())
        self.assertEqual([b.text() for b in (h.b_xem_word, h.b_xem_excel, h.b_xem_nhieu, h.b_xem_bth)], ['Word', 'Excel', 'PDF gộp', 'Bảng tổng hợp'])
        self.assertTrue(h.o_tt.isHidden())                                           # Dự thảo
        h.dat_che_do('chinh_thuc')
        self.assertFalse(h.o_tt.isHidden())
        h._danh_dau(self.ma[:2])
        self.assertIn('2 hộ', h.b_thuc_hien.text())

    def test_chi_tich_pdf_thi_khong_de_lai_word(self):
        h = self._hop()
        h._danh_dau(self.ma[:2])
        h.o_bth.setChecked(False)
        h.o_ct.setChecked(False)
        h.o_pdf.setChecked(True)
        self.assertTrue(h.r_pdf.isChecked())
        h.o_thu_muc.setText(str(self.p.parent / 'ra'))
        with mock.patch('pabt.van_ban_trinh.chay_word', _gia_pdf):
            kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual(kq['word'], [])
        self.assertEqual(len([f for f in kq['pdf'] if f.name.startswith('PA_')]), 2)
        self.assertEqual(list((self.p.parent / 'ra' / 'PA CHI TIET').glob('PA_*.docx')), [])
        self.assertEqual(len(list((self.p.parent / 'ra' / 'PA CHI TIET').glob('PA_*.pdf'))), 2)

    def test_word_va_pdf_doc_lap_o_pdf_khop_dau_ra(self):
        h = self._hop()
        h.o_pdf.setChecked(False)
        self.assertTrue(h.r_excel.isChecked())
        h.r_pdf.setChecked(True)
        self.assertTrue(h.o_pdf.isChecked())
        h._danh_dau(self.ma[:1])
        h.o_bth.setChecked(False)
        h.o_ct.setChecked(False)
        h.o_pdf.setChecked(False)
        with mock.patch('PySide6.QtWidgets.QMessageBox.information') as bao:
            self.assertIsNone(h.thuc_hien(xac_nhan=False))                           # không tích gì: báo, không xuất
        bao.assert_called_once()

    def test_in_ra_may_tra_lai_dinh_dang(self):
        h = self._hop()
        h._danh_dau(self.ma[:1])
        h.o_bth.setChecked(False)
        h.o_thu_muc.setText(str(self.p.parent / 'ra'))
        with mock.patch('pabt.van_ban_trinh.chay_word', side_effect=_gia_pdf) as w:
            self.assertIsNotNone(h.in_ra_may(xac_nhan=False))
        self.assertTrue(w.called)
        self.assertTrue(h.r_pdf.isChecked() and h.o_pdf.isChecked())

    def test_the_xuat_du_lieu_dung_lai_lenh_cua_so_chinh(self):
        from pabt import app as ud
        from pabt.man_hinh import HopIn
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(self.p))
        APP.processEvents()
        d = HopIn(w.con, w, file_du_an=w.file)
        d.im_lang = True
        self.addCleanup(d.w_preview.don_dep)
        d.dat_pham_vi('du_lieu')
        self.assertFalse(d.khung_du_lieu.isHidden())
        self.assertTrue(d.khung_chon_ho.isHidden() and d.phai.isHidden() and d.b_thuc_hien.isHidden())
        self.assertEqual(set(d.nut_du_lieu), {'Xuất danh sách hộ…', 'Xuất báo cáo đối chiếu…'})
        for ten in d.nut_du_lieu:                                                    # một chỗ: không còn trên menu
            self.assertNotIn(w.lenh[ten], w.menu_tren['Dữ liệu'].actions())
        with mock.patch('pabt.app.QMessageBox.question', return_value=None), mock.patch('pabt.app.QFileDialog.getSaveFileName', side_effect=AssertionError('không hỏi nơi lưu')):
            d.nut_du_lieu['Xuất danh sách hộ…'].click()
            APP.processEvents()
        self.assertTrue(list(Path(w.file).parent.rglob('DanhSachHo_*.xlsx')))

    def test_bang_in_mo_tu_lap_phuong_an_khong_co_the_du_lieu(self):
        h = self._hop(ma_ho_chon=self.ma[:1])
        self.assertEqual(h.the_pham_vi.count(), 2)


if __name__ == '__main__':
    unittest.main()
