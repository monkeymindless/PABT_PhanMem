"""0.9.77 (người dùng 13/10/2026, đặc tả ARCH-PABT-2026-DEFINITIVE-MASTER-V10): cửa sổ con đủ Thu nhỏ / Phóng to / Đóng + nhớ kích thước,
cửa sổ chính 1024 x 680 / Restore 1200 x 740, Xóa đợt + In PA Dự thảo (Niêm yết & Lấy ý kiến), Trung tâm Xuất bản duy nhất (HopIn:
chế độ Dự thảo / Chính thức), số PA 01, 02…, tỷ lệ kinh phí đúng gốc 100%. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import du_thao, quan_ly
from tests.test_yeu_cau_0976 import _Co, _hn, _qt


class TestCuaSoCon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _qt()
        from pabt import giao_dien
        giao_dien.ap_dung(cls.app)                          # cài bộ lọc sự kiện toàn ứng dụng (như khi chạy thật)

    def test_cua_so_con_du_nut_thu_nho_phong_to_dong(self):
        from PySide6.QtCore import Qt
        from pabt.man_hinh_quan_ly import HopDanhSo
        d = HopDanhSo(None, 3, 1)
        self.addCleanup(d.close)
        d.show()
        self.app.processEvents()
        co, W = d.windowFlags(), Qt.WindowType
        for ten in ('WindowMinimizeButtonHint', 'WindowMaximizeButtonHint', 'WindowCloseButtonHint', 'WindowTitleHint'):
            self.assertTrue(co & getattr(W, ten), ten)
        self.assertFalse(co & W.WindowContextHelpButtonHint)
        self.assertTrue(d.isSizeGripEnabled())              # tay nắm co giãn ở góc dưới phải
        self.assertTrue(d.isVisible())

    def test_hop_thoai_cua_qt_va_co_dinh_khong_doi(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QMessageBox
        from pabt import giao_dien
        m = QMessageBox()
        self.addCleanup(m.close)
        self.assertFalse(giao_dien.la_cua_so_con_pabt(m))   # hộp thoại của Qt: không đụng
        Co = type('HopCoDinh', (QDialog,), {'__module__': 'pabt.thu'})
        c = Co()
        self.addCleanup(c.close)
        c.setFixedSize(320, 200)
        self.assertTrue(giao_dien.la_cua_so_con_pabt(c))
        c.show()
        self.app.processEvents()
        self.assertFalse(c.isSizeGripEnabled())             # hộp cố định kích thước: giữ nguyên
        self.assertFalse(c.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint)

    def test_nho_kich_thuoc_qua_qsettings(self):
        from PySide6.QtCore import QSettings
        from pabt import giao_dien
        from pabt.man_hinh_quan_ly import HopDanhSo
        with tempfile.TemporaryDirectory() as td:
            cai = QSettings(str(Path(td) / 'cs.ini'), QSettings.Format.IniFormat)
            d1 = HopDanhSo(None, 3, 1)
            self.addCleanup(d1.close)
            d1.resize(600, 420)
            self.assertTrue(giao_dien.nho_kich_thuoc(d1, cai))
            self.assertEqual(giao_dien.khoa_kich_thuoc(d1), 'cua_so/HopDanhSo')
            cai.sync()
            d2 = HopDanhSo(None, 3, 1)
            self.addCleanup(d2.close)
            d2.resize(300, 200)
            self.assertTrue(giao_dien.khoi_phuc_kich_thuoc(d2, cai))
            self.assertEqual((d2.width(), d2.height()), (600, 420))
            self.assertFalse(giao_dien.khoi_phuc_kich_thuoc(HopDialogKhac := _Khac(), cai))        # chưa có bản nhớ của lớp khác
            self.assertIsNotNone(HopDialogKhac)

    def test_chay_khong_man_hinh_khong_ghi_qsettings(self):
        from pabt import giao_dien
        self.assertIsNone(giao_dien._cai_dat_cua_so())      # offscreen (kiểm thử): không đọc / ghi QSettings thật của người dùng


def _Khac():
    from PySide6.QtWidgets import QDialog
    Co = type('HopKhac', (QDialog,), {'__module__': 'pabt.thu'})
    return Co()


class TestCuaSoChinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _qt()

    def test_kich_thuoc_thuong_canh_giua(self):
        from PySide6.QtWidgets import QWidget
        from pabt import giao_dien
        w = QWidget()
        self.addCleanup(w.close)
        vung = (w.screen() or self.app.primaryScreen()).availableGeometry()
        r = giao_dien.kich_thuoc_thuong(w)
        self.assertEqual((r.width(), r.height()), (min(1200, vung.width()), min(740, vung.height())))
        self.assertTrue(vung.contains(r))
        self.assertLessEqual(abs(r.center().x() - vung.center().x()), 1)
        self.assertLessEqual(abs(r.center().y() - vung.center().y()), 1)
        giao_dien.dat_toi_thieu_cua_so(w)
        self.assertEqual((w.minimumWidth(), w.minimumHeight()), (min(1024, vung.width()), min(680, vung.height())))

    def test_thu_ve_tu_phong_to_ve_kich_thuoc_chuan(self):
        """Kích thước thường bằng cả màn hình (không có gì để "thu về") -> 1200 x 740 canh giữa; người dùng đã tự đặt nhỏ hơn thì giữ."""
        from PySide6.QtWidgets import QMainWindow
        from pabt import giao_dien
        from pabt.thanh_tieu_de import ThanhTieuDe

        class Gia:
            pass
        g = Gia()
        g.cua = QMainWindow()
        self.addCleanup(g.cua.close)
        vung = (g.cua.screen() or self.app.primaryScreen()).availableGeometry()
        g.cua.setGeometry(vung)
        ThanhTieuDe._ve_kich_thuoc_thuong(g)
        self.assertEqual(g.cua.geometry(), giao_dien.kich_thuoc_thuong(g.cua))
        g.cua.setGeometry(vung.x() + 20, vung.y() + 20, min(640, vung.width() - 60), min(480, vung.height() - 60))
        truoc = g.cua.geometry()
        ThanhTieuDe._ve_kich_thuoc_thuong(g)
        self.assertEqual(g.cua.geometry(), truoc)


class TestXoaDotVaInDuThao(_Co):
    def _dot(self):
        for m in self.ma[:3]:
            du_thao.ghi_phap_ly(self.con, m, 1, '', '')
        d1 = du_thao.tao_dot(self.con, 'Niêm yết 1', _hn(-5), 'Nhà văn hóa')
        d2 = du_thao.tao_dot(self.con, 'Niêm yết 2', _hn(-2), 'Nhà văn hóa')
        du_thao.dua_ho_vao_dot(self.con, d1, self.ma[:3])
        du_thao.dua_ho_vao_dot(self.con, d2, self.ma[:1])
        du_thao.ghi_y_kien(self.con, d1, self.ma[1], 'khong_dong_y', 'gia_dat', 'Giá thấp')
        du_thao.ghi_doi_thoai(self.con, d1, self.ma[1], _hn(-1), 'UBND xã', 'Đã giải thích')
        return d1, d2

    def test_xoa_dot_logic(self):
        d1, d2 = self._dot()
        tt = du_thao.thong_tin_xoa_dot(self.con, d1)
        self.assertEqual((tt['ten'], tt['so_ho'], tt['co_y_kien'], tt['so_doi_thoai']), ('Niêm yết 1', 3, 1, 1))
        so_dong_pa = self.con.execute('SELECT (SELECT COUNT(*) FROM ct_dat) + (SELECT COUNT(*) FROM ct_khoan)').fetchone()[0]
        self.assertEqual(du_thao.xoa_dot(self.con, d1)['so_ho'], 3)
        self.assertEqual([d['id'] for d in du_thao.ds_dot(self.con)], [d2])
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM y_kien_du_thao WHERE dot_id = ?', (d1,)).fetchone()[0], 0)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM doi_thoai_ho').fetchone()[0], 0)
        # hộ chỉ ở đợt 1 -> về danh sách chờ (vẫn đủ điều kiện); hộ còn ở đợt 2 -> trỏ về đợt 2; phương án nguyên vẹn
        tro = {r[0]: r[1] for r in self.con.execute('SELECT ma_ho, dot_du_thao_id FROM ho')}
        self.assertEqual((tro[self.ma[0]], tro[self.ma[1]], tro[self.ma[2]]), (d2, None, None))
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ho WHERE du_dieu_kien = 1').fetchone()[0], 3)
        self.assertEqual(self.con.execute('SELECT (SELECT COUNT(*) FROM ct_dat) + (SELECT COUNT(*) FROM ct_khoan)').fetchone()[0],
                         so_dong_pa)
        with self.assertRaises(du_thao.LoiNhap):
            du_thao.xoa_dot(self.con, d1)                   # đã xóa
        # đưa lại vào danh sách chờ: hộ 2 vào được đợt 2
        self.assertEqual(du_thao.dua_ho_vao_dot(self.con, d2, [self.ma[1]]), (1, 0))

    def test_nut_xoa_dot_tren_giao_dien(self):
        from PySide6.QtWidgets import QMessageBox
        from pabt.man_hinh_du_thao import KhungDuThao
        d1, d2 = self._dot()
        k = KhungDuThao(self.con)
        self.addCleanup(k.close)
        self.assertEqual(k.cb.currentData(), None)          # "Lũy kế": nút mờ
        self.assertFalse(k.b_xoa_dot.isEnabled())
        self.assertFalse(k.b_in_du_thao.isEnabled())
        with mock.patch.object(QMessageBox, 'information') as tb:
            self.assertIsNone(k._xoa_dot())
            tb.assert_called_once()
        k.cb.setCurrentIndex(k.cb.findData(d1))
        self.assertTrue(k.b_xoa_dot.isEnabled())
        self.assertTrue(k.b_in_du_thao.isEnabled())
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No) as hoi:
            self.assertIsNone(k._xoa_dot())
            chu = hoi.call_args[0][2]
            self.assertIn('3 hộ của đợt trở về danh sách chờ', chu)
            self.assertIn('Mất 1 ý kiến', chu)              # nói rõ điều mất
            self.assertIn('Hoàn tác', chu)
        self.assertEqual(len(du_thao.ds_dot(self.con)), 2)
        self.assertEqual(k._xoa_dot(xac_nhan=True)['so_ho'], 3)
        self.assertEqual(len(du_thao.ds_dot(self.con)), 1)
        self.assertEqual(k.cb.currentData(), None)          # đợt đã xóa: về "Lũy kế", nút mờ lại
        self.assertFalse(k.b_xoa_dot.isEnabled())
        self.assertTrue(k.thay_doi_csdl)

    def test_xoa_dot_chi_xem(self):
        from pabt.man_hinh_du_thao import KhungDuThao
        d1, _ = self._dot()
        k = KhungDuThao(self.con, chi_doc=True)
        self.addCleanup(k.close)
        k.cb.setCurrentIndex(k.cb.findData(d1))
        self.assertFalse(k.b_xoa_dot.isEnabled())           # mở chỉ xem: không xóa được

    def test_in_pa_du_thao_mo_trung_tam_xuat_ban_che_do_du_thao(self):
        from PySide6.QtWidgets import QWidget
        from pabt.man_hinh_du_thao import KhungDuThao
        d1, _ = self._dot()
        cha = QWidget()
        self.addCleanup(cha.close)
        cha.in_xuat = mock.Mock(return_value='hop_in')
        k = KhungDuThao(self.con, cha)
        k.cb.setCurrentIndex(k.cb.findData(d1))
        self.assertEqual(k._in_du_thao(cho=False), 'hop_in')
        cha.in_xuat.assert_called_once_with(cho=False, ma_ho=self.ma[:3], che_do='du_thao')

    def test_in_xuat_cua_so_chinh_nhan_ho_va_che_do(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.mo(str(self.p))
        h = w.in_xuat(cho=False, ma_ho=self.ma[:2], che_do='du_thao')
        self.addCleanup(h.close)
        self.assertEqual(h.che_do(), 'du_thao')
        self.assertEqual(h.ds_ho(), self.ma[:2])

    def test_dot_trinh_chuyen_sang_xuat_ban(self):
        from pabt import app as ud
        from pabt.man_hinh_quan_ly import HopDotTrinh
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.mo(str(self.p))
        # 30/10/2026 (phương án đột phá 6): nút "Xuất bản hồ sơ đợt này" mở trình hướng dẫn xuất bản 4 bước (khâu xuất vẫn là
        # HopIn.thuc_hien) thay vì mở thẳng Trung tâm Xuất bản
        with mock.patch.object(HopDotTrinh, 'exec', lambda self: setattr(self, 'mo_xuat_dot', 7) or 0), \
                mock.patch.object(w, 'xuat_ban_dot') as xb:
            w.dot_trinh()
        xb.assert_called_once_with(dot_id=7, che_do='chinh_thuc')


def _chu_word(f) -> str:
    import re
    import zipfile
    with zipfile.ZipFile(f) as z:
        return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', z.read('word/document.xml').decode('utf-8')))


class TestHopInCheDo(_Co):
    def _hop(self, **kw):
        _qt()
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p, **kw)
        self.addCleanup(h.close)
        return h

    def test_mac_dinh_giu_nguyen_khi_khong_chon_che_do(self):
        h = self._hop()
        self.assertTrue(h.r_du_thao.isChecked())            # 05/11/2026: mở bảng in mặc định ở Dự thảo
        self.assertFalse(h.o_tt.isChecked())                # như trước 0.9.77: không tự chọn mẫu khi chưa chọn đợt / chế độ
        # 16/10/2026: bỏ ô chọn mẫu từng bản in, dòng ghi chú chế độ (chữ DỰ THẢO do Chế độ phát hành); 20/10/2026: ô Báo cáo
        # tiếp thu ý kiến trở lại (chỉ chế độ chính thức - "trọn bộ 4 tài liệu"), chưa chọn sẵn khi chưa chọn đợt / chế độ
        for ten in ('cb_mau_ct', 'cb_mau_bth', 'lb_che_do'):
            self.assertFalse(hasattr(h, ten), ten)
        self.assertFalse(h.o_bc.isEnabled())
        self.assertFalse(h.o_bc.isChecked())

    def test_che_do_du_thao(self):
        h = self._hop(che_do='du_thao', ma_ho_chon=self.ma[:2])
        self.assertTrue(h.r_du_thao.isChecked())
        self.assertFalse(h.o_che_cccd.isChecked())                               # 1.0.04: không che CCCD
        self.assertTrue(h.o_ct.isChecked() and h.o_bth.isChecked())
        self.assertFalse(h.o_tt.isChecked())                                     # dự thảo: chưa tờ trình
        self.assertIn('DỰ THẢO', h.r_du_thao.toolTip())
        self.assertEqual(h.ds_ho(), self.ma[:2])

    def test_che_do_chinh_thuc_va_chuyen_qua_lai(self):
        h = self._hop(che_do='du_thao')
        h.r_chinh_thuc.setChecked(True)                                          # bấm radio: tự áp bộ cài đặt đi kèm
        self.assertTrue(all(o.isChecked() for o in (h.o_ct, h.o_bth, h.o_tt)))     # trọn bộ
        self.assertIsNone(h.khoa_xem_truoc()[2])                                 # mẫu chính
        h.r_du_thao.setChecked(True)
        self.assertEqual(h.che_do(), 'du_thao')

    def test_xuat_du_thao_khong_theo_dot_va_chinh_thuc_theo_dot(self):
        import openpyxl
        h = self._hop(che_do='du_thao', ma_ho_chon=self.ma[:2])
        h.r_excel.setChecked(True)
        h.o_thu_muc.setText(str(self.td / 'dt'))
        kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual(len(kq['excel']), 1)                                    # bảng tổng hợp; không tờ trình / báo cáo
        # Word chỉ có bản phương án chi tiết từng hộ (22/10/2026: luôn Word) - dự thảo không tờ trình / báo cáo
        self.assertEqual(len(kq['word']), 2)
        self.assertTrue(all(p.name.startswith('PA_') for p in kq['word']))
        self.assertTrue(all('(DỰ THẢO)' in _chu_word(p) for p in kq['word']))
        chu = ' '.join(str(c.value) for f in kq['excel'] for ws in openpyxl.load_workbook(f).worksheets for r in ws.iter_rows()
                       for c in r if isinstance(c.value, str))
        self.assertIn('DỰ THẢO', chu.upper())
        # bản chính thức theo đợt: thư mục "<đợt> - k hộ" trong thư mục hồ sơ, ghi nhớ vào đợt
        d = quan_ly.tao_dot(self.con, 'Đợt A', _hn(-1), '5/TTr')
        quan_ly.gan_dot(self.con, self.ma[:2], d)
        quan_ly.dat_thu_muc_ho_so(self.con, self.td / 'hso')
        h2 = self._hop(che_do='chinh_thuc', dot_id=d)
        self.assertEqual(h2.ds_ho(), self.ma[:2])
        self.assertEqual(h2.o_thu_muc.text(), str(self.td / 'hso' / 'Đợt A - 2 hộ'))
        h2.r_excel.setChecked(True)
        kq = h2.thuc_hien(xac_nhan=False)
        self.assertEqual(sorted(p.name for p in kq['word'] if not p.name.startswith('PA_')),
                         ['BAO_CAO_TIEP_THU_Y_KIEN.docx', 'TO_TRINH.docx'])   # trọn bộ 4
        self.assertEqual(quan_ly.lay_dot(self.con, d).thu_muc, str(self.td / 'hso' / 'Đợt A - 2 hộ'))

    def test_doi_ten_thu_muc_dot_khi_so_ho_doi(self):
        d = quan_ly.tao_dot(self.con, 'Đợt B', _hn(-1), '6/TTr')
        quan_ly.gan_dot(self.con, self.ma[:2], d)
        quan_ly.dat_thu_muc_ho_so(self.con, self.td / 'hso')
        h = self._hop(che_do='chinh_thuc', dot_id=d)
        h.r_excel.setChecked(True)
        h.o_ct.setChecked(False)
        h.thuc_hien(xac_nhan=False)
        self.assertTrue((self.td / 'hso' / 'Đợt B - 2 hộ').is_dir())
        quan_ly.gan_dot(self.con, [self.ma[2]], d)                               # đợt thêm 1 hộ: thư mục cũ đổi tên theo số hộ mới
        h2 = self._hop(che_do='chinh_thuc', dot_id=d)
        h2.r_excel.setChecked(True)
        h2.o_ct.setChecked(False)
        h2.thuc_hien(xac_nhan=False)
        self.assertTrue((self.td / 'hso' / 'Đợt B - 3 hộ').is_dir())
        self.assertFalse((self.td / 'hso' / 'Đợt B - 2 hộ').exists())


class TestSoPA2ChuSo(_Co):
    def test_hop_danh_so_mac_dinh_2_chu_so(self):
        _qt()
        from pabt.man_hinh_quan_ly import HopDanhSo
        h = HopDanhSo(None, 3, 1)
        self.addCleanup(h.close)
        self.assertEqual(h.o_chu_so.value(), 2)

    def test_danh_so_01_02_03(self):
        _qt()
        from PySide6.QtWidgets import QDialog
        from pabt.man_hinh_quan_ly import HopDanhSo, HopDotTrinh
        d = HopDotTrinh(self.con, None, self.ma[:3], self.p)
        d.im_lang = True
        self.addCleanup(d.close)
        d.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        d.dua_vao()
        with mock.patch.object(HopDanhSo, 'exec', return_value=QDialog.DialogCode.Accepted):
            kq = d.danh_so()                                                     # hộp hỏi: mặc định 2 chữ số
        self.assertEqual([s for _, s, _ in kq], ['01', '02', '03'])
        self.assertEqual([s for _, s, _ in d.danh_so(5, '')], ['5', '6', '7'])  # gọi từ mã (kiểm thử): không thêm số 0 như trước
        self.assertEqual([s for _, s, _ in d.danh_so(9, '', so_chu_so=2)], ['09', '10', '11'])


class TestTyLe(unittest.TestCase):
    def test_dinh_dang_ty_le(self):
        from pabt.man_hinh_theo_doi import _ty_le
        self.assertEqual([_ty_le(x) for x in (2.5, 3.5, 100.0, 102.5, 103.5, 2.25, 0.0)],
                         ['2,5', '3,5', '100,0', '102,5', '103,5', '2,25', '0,0'])      # không bao giờ ra 2,4% / 3,4%


if __name__ == '__main__':
    unittest.main()
