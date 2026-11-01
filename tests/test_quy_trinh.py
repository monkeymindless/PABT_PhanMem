"""Mô hình 16 bước quy trình QĐ 18 (pabt/quy_trinh.py, đại tu giao diện 30/10/2026): trạng thái từng bước tính từ dữ liệu, bước hiện tại,
việc nên làm tiếp, mốc ngày của các bước không có bảng riêng (cai_dat). Dự án GIẢ LẬP tests.test_toc_do._du_an."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, quy_trinh as qt, theo_doi  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class CoSo(unittest.TestCase):
    N = 6

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.con = csdl.mo(_du_an(self.td, self.N))
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def tinh(self, lap=None, **k):
        if lap is None:
            lap = {m: 'da_lap' for m in self.ma}
        return qt.tinh(self.con, lap=lap, hom_nay=date(2026, 10, 30), **k)


class TestCauTruc(unittest.TestCase):
    def test_16_buoc_5_giai_doan(self):
        tat_ca = [b for _, _, ds in qt.GIAI_DOAN for b in ds]
        self.assertEqual(tat_ca, list(range(1, 17)))
        self.assertEqual(set(qt.TEN_NGAN), set(range(1, 17)))
        self.assertEqual(set(qt.LENH_BUOC), set(range(1, 17)))
        self.assertEqual(qt.giai_doan_cua(5)[0], 'C')

    def test_lenh_buoc_co_trong_cua_so_chinh(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as td:
            cu = os.environ.get('PABT_THU_MUC_MAY')
            os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
            try:
                from pabt import app as ud
                w = ud.CuaSoChinh(menu_trai=True)
                try:
                    for b, lenh in qt.LENH_BUOC.items():
                        if lenh:
                            self.assertIn(lenh, w.lenh, b)
                finally:
                    w.close()
                    w.deleteLater()
            finally:
                if cu is None:
                    os.environ.pop('PABT_THU_MUC_MAY', None)
                else:
                    os.environ['PABT_THU_MUC_MAY'] = cu


class TestTrangThai(CoSo):
    def test_du_an_moi_lap_xong_dang_o_niem_yet(self):
        kq = self.tinh()
        self.assertEqual(kq.so_ho, self.N)
        self.assertEqual(kq.buoc[4].trang_thai, qt.XONG)
        self.assertEqual(kq.buoc[5].trang_thai, qt.XONG)
        self.assertEqual(kq.buoc[5].mo_ta, f'{self.N} / {self.N} hộ đã lập phương án')
        self.assertEqual(kq.buoc[6].trang_thai, qt.CHUA)
        self.assertEqual(kq.buoc[9].trang_thai, qt.CHUA)
        self.assertEqual(kq.hien_tai, 6)                    # bước đầu tiên chưa làm sau bước xong cuối cùng (bỏ qua bước 1-3)
        self.assertTrue(any(v.buoc == 6 and v.muc == 'can' for v in kq.viec))

    def test_chua_lap_va_tu_lap(self):
        lap = {m: 'da_lap' for m in self.ma[:2]}
        lap.update({m: 'tu_lap' for m in self.ma[2:4]})
        kq = self.tinh(lap=lap)
        t = kq.buoc[5]
        self.assertEqual((t.trang_thai, t.xong, t.tong), (qt.DANG, 2, self.N))
        self.assertEqual(kq.hien_tai, 5)
        chu = [v.chu for v in kq.viec]
        self.assertIn('2 hộ chưa lập phương án', chu)
        self.assertIn('2 hộ phần mềm tự lập, chưa soát lại', chu)

    def test_phe_duyet_chi_tra_ban_giao(self):
        q = theo_doi.luu_qd(self.con, None, '1/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(self.con, q, self.ma[:4])
        theo_doi.ghi_chi_tra(self.con, [(q, m) for m in self.ma[:2]], '05/10/2026')
        theo_doi.ghi_ban_giao(self.con, self.ma[:1], dict(da_ban_giao=1, ban_giao_ngay='10/10/2026'))
        kq = self.tinh()
        self.assertEqual((kq.buoc[9].xong, kq.buoc[9].tong, kq.buoc[9].trang_thai), (4, self.N, qt.DANG))
        self.assertEqual((kq.buoc[12].xong, kq.buoc[12].tong), (2, 4))
        self.assertEqual((kq.buoc[16].xong, kq.buoc[16].trang_thai), (1, qt.DANG))
        self.assertEqual(kq.buoc[15].mo_ta, '1 hộ đã nhận tiền chưa bàn giao mặt bằng')
        self.assertEqual(kq.buoc[10].trang_thai, qt.DANG)   # đã có quyết định mà chưa ghi ngày công khai
        self.assertTrue(any(v.buoc == 14 for v in kq.viec))

    def test_viec_xep_uu_tien_va_gioi_han(self):
        kq = self.tinh(lap={})
        muc = [qt.MUC_VIEC.index(v.muc) for v in kq.viec]
        self.assertEqual(muc, sorted(muc))
        self.assertLessEqual(len(kq.viec), qt.VIEC_TOI_DA)

    def test_dong_tu_csdl_khop_so_ho(self):
        dong = qt.dong_tu_csdl(self.con)
        self.assertEqual([d['ma_ho'] for d in dong], self.ma)
        self.assertTrue(all(d['o'][3] >= 0 for d in dong))

    def test_giai_doan(self):
        kq = self.tinh()
        self.assertEqual(kq.trang_thai_giai_doan('B'), qt.XONG)
        self.assertEqual(kq.trang_thai_giai_doan('E'), qt.CHUA)
        self.assertEqual([g[0] for g in kq.theo_giai_doan()], ['A', 'B', 'C', 'D', 'E'])


class TestMocNgay(CoSo):
    def test_ghi_doc_xoa_moc_va_hoan_tac_duoc(self):
        self.assertIsNone(qt.doc_moc(self.con, 2))
        qt.ghi_moc(self.con, 2, '05/03/2026')
        self.assertEqual(qt.doc_moc(self.con, 2), date(2026, 3, 5))
        kq = self.tinh()
        self.assertEqual(kq.buoc[2].trang_thai, qt.XONG)
        self.assertEqual(kq.buoc[2].mo_ta, 'Đã ghi ngày 05/03/2026')
        nk = self.con.execute("SELECT viec FROM nhat_ky ORDER BY rowid DESC LIMIT 1").fetchone()[0]
        self.assertIn('Họp dân', nk)
        qt.ghi_moc(self.con, 2, '')
        self.assertIsNone(qt.doc_moc(self.con, 2))

    def test_buoc_3_dung_chung_ngay_thong_bao_thu_hoi(self):
        from pabt import thoi_han
        self.assertEqual(qt.MOC_BUOC[3], thoi_han.KHOA_NGAY_THONG_BAO)

    def test_ngay_sai_bao_loi_nhap(self):
        from pabt.lap_pa import LoiNhap
        with self.assertRaises(LoiNhap):
            qt.ghi_moc(self.con, 10, 'abc')
        with self.assertRaises(KeyError):
            qt.ghi_moc(self.con, 5, '01/01/2026')


class TestBuongLai(unittest.TestCase):
    """Buồng lái dự án (Màn hình chính khi đã mở dự án): thanh 16 bước, việc nên làm tiếp, bấm bước / ghi ngày."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        from pabt import app as ud
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.w.show()
        self.w.mo(str(_du_an(self.td, 5)))
        self.w.ve_trang_chu()
        self.app.processEvents()

    def tearDown(self):
        self.w.dong_du_an()
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def test_pheu_theo_ho_va_viec(self):
        tq = self.w.tong_quan
        self.assertIsNotNone(tq)
        self.assertTrue(tq.pheu.isVisible())
        kq = tq.ket_qua_pheu
        self.assertTrue(kq.doi_soat())
        self.assertEqual(kq.so_ho, 5)
        self.assertEqual(tq.pheu.chu_giai['da_lap'].text(), 'Đã lập  5')
        self.assertIn('5 hộ', tq.pheu.lb_tom_tat.text())
        self.assertTrue(tq.pheu.nut_co['tu_lap'].isVisible())
        self.assertTrue(tq.viec.dong)
        h = tq.mo_danh_sach('Đã lập', kq.theo_giai_doan('da_lap'))
        self.addCleanup(h.close)
        self.assertEqual(h.bang.rowCount(), 5)
        self.assertEqual(tq.pheu.cb_pham_vi.itemText(0), 'Cả dự án')

    def test_ghi_ngay_buoc_va_bam_buoc(self):
        self.assertTrue(self.w.ghi_ngay_buoc(2, '05/03/2026'))
        self.assertEqual(self.w.tong_quan.quy_trinh.buoc[2].trang_thai, qt.XONG)
        self.assertIn('05/03/2026', self.w.tong_quan.pheu.nut_du_an[2].text())
        self.assertEqual(self.w.mo_buoc_quy_trinh(4), 'Danh sách hộ')
        self.app.processEvents()
        self.assertEqual(self.w._i_trang, 0)                # bước 4 mở trang Danh sách hộ

    def test_dong_du_an_roi_doi_che_do_khong_loi(self):
        """kiem_tra_giao_dien 30/10/2026: đóng dự án rồi đổi ô "Lần PA" -> phễu tính trên kết nối đã đóng, nút "Xem hộ" AttributeError."""
        tq = self.w.tong_quan
        self.w.dong_du_an()
        self.app.processEvents()
        tq.pheu.cb_lan.setCurrentIndex(1)
        self.assertIsNotNone(tq.ket_qua_pheu)
        for _lb, nut in tq.viec.dong:
            if nut is not None:
                nut.click()
        from PySide6.QtWidgets import QDialog
        h = tq.mo_danh_sach('x', [])
        self.addCleanup(h.close)
        self.assertIsInstance(h, QDialog)

    def test_chi_xem_khong_ghi_ngay(self):
        self.w.chi_doc = True
        from unittest import mock
        with mock.patch('pabt.app.QMessageBox.information'):
            self.assertFalse(self.w.ghi_ngay_buoc(10, '01/10/2026'))
        self.w.chi_doc = False


if __name__ == '__main__':
    unittest.main()
