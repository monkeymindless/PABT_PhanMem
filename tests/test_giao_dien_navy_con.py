"""1.0.02 (người dùng 17/10/2026): cửa sổ con / trang nhúng theo chuẩn "Hybrid Enterprise Navy" của màn hình chính - màu nút theo
vai trò (chính / lưu navy, xóa viền đỏ nhạt, phụ nền trắng viền slate; không còn nền cam / tím / xanh lá), thẻ / khung nhóm / thanh
chia chung, thẻ KPI có vạch trái + trạng thái đang lọc, nút chế độ kiểu viên thuốc, dòng nổi bảng cơ cấu kinh phí, cột Hệ số K
(số liệu GIẢ LẬP - tests.test_toc_do._du_an)."""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, giao_dien  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402

NAVY = '#0F3866'
CAM_TIM_XANH_LA = ('#6950A1', '#594389', '#B8651F', '#9C551A', '#D83B01', '#B83201', '#107C41', '#0D6B37', '#1D7A6C', '#2F7A4F')


def _qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _quy_tac(qss: str, bo_chon: str) -> str:
    """Thân quy tắc QSS đầu tiên có đúng bộ chọn (bỏ khoảng trắng thừa)."""
    m = re.search(re.escape(bo_chon) + r'(?:\s*,[^{]*)?\s*\{([^}]*)\}', qss)     # có thể là bộ chọn đầu của nhóm 'a, b {…}'
    return ' '.join(m.group(1).split()) if m else ''


class TestQssChung(unittest.TestCase):
    def test_mau_nut_theo_vai_tro(self):
        for chu in ('Lưu', 'Lưu thay đổi', 'Áp dụng', 'Thực hiện', 'Tạo dự án', 'Xuất bản hồ sơ đợt này  →'):
            self.assertEqual(giao_dien.nhom_nut(chu), 'luu', chu)
        self.assertEqual(giao_dien.nhom_nut('Xóa đợt'), 'xoa')
        qss = giao_dien._qss_day_du()
        for mau in CAM_TIM_XANH_LA:                                    # bỏ nền / biểu tượng cam, tím, xanh lá
            self.assertNotIn(mau, qss)
            self.assertNotIn(mau, [m[0] for m in giao_dien.MAU.values()])
        luu = _quy_tac(qss, 'QPushButton[nhom="luu"]')
        self.assertIn(f'background: {NAVY}', luu)
        self.assertIn('color: #FFFFFF', luu)
        xoa = _quy_tac(qss, 'QPushButton[nhom="xoa"]')
        self.assertIn('background: #FFFFFF', xoa)
        self.assertIn('#FECACA', xoa)
        self.assertIn('#B91C1C', xoa)
        phu = _quy_tac(qss, 'QPushButton[nhom="in"]')                  # nút phụ: trắng, viền slate, chữ #0F172A
        for x in ('background: #FFFFFF', '#CBD5E1', 'color: #0F172A'):
            self.assertIn(x, phu)
        self.assertIn('#F1F5F9', _quy_tac(qss, 'QPushButton[nhom="in"]:hover'))
        self.assertIn(f'background: {NAVY}', _quy_tac(qss, 'QPushButton[bien_the="success"]'))   # KieuNut.LUU = navy
        self.assertIn(f'background: {NAVY}', _quy_tac(qss, 'QToolButton[nhom="luu"]'))

    def test_the_khung_nhom_thanh_chia(self):
        qss = giao_dien._qss_day_du()
        tab = _quy_tac(qss, 'QTabBar::tab')
        for x in ('background: #F1F5F9', 'color: #475569', 'padding: 5px 14px', 'border-top-left-radius: 5px', 'margin-right: 2px'):
            self.assertIn(x, tab)
        chon = _quy_tac(qss, 'QTabBar::tab:selected')
        self.assertIn('background: #FFFFFF', chon)
        self.assertIn(f'color: {NAVY}', chon)
        self.assertIn('font-weight: 700', chon)
        self.assertIn(f'border-top: 2px solid {NAVY}', chon)
        self.assertIn('background: #E2E8F0', _quy_tac(qss, 'QTabBar::tab:hover:!selected'))
        nhom = _quy_tac(qss, 'QGroupBox')
        self.assertIn('border: 1px solid #E2E8F0', nhom)
        self.assertIn('border-radius: 6px', nhom)
        self.assertIn('margin-top: 22px', nhom)                          # chỗ cho tiêu đề (0.9.38: không bị khung cắt)
        self.assertIn('subcontrol-origin: margin', _quy_tac(qss, 'QGroupBox::title'))
        self.assertIn('#E2E8F0', _quy_tac(qss, 'QSplitter::handle'))
        self.assertIn('#94A3B8', _quy_tac(qss, 'QSplitter::handle:hover'))

    def test_qss_ap_khong_loi(self):
        from PySide6.QtCore import qInstallMessageHandler
        from PySide6.QtWidgets import QPushButton
        app = _qt()
        loi = []
        cu = qInstallMessageHandler(lambda t, c, m: loi.append(m))
        try:
            b = QPushButton('Lưu')
            b.setStyleSheet(giao_dien._qss_day_du())
            b.ensurePolished()
            app.processEvents()
        finally:
            qInstallMessageHandler(cu)
        self.assertFalse([m for m in loi if 'style' in m.lower()])


class _Co(unittest.TestCase):
    def setUp(self):
        _qt()
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.con = csdl.mo(_du_an(self.td, 6))

    def tearDown(self):
        self.doCleanups()
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestCuaSoLapPA(_Co):
    def test_thanh_tren_va_dai_dieu_huong(self):
        from PySide6.QtWidgets import QPushButton
        from pabt import man_hinh as mh
        w = mh.CuaSoLapPA(self.con, 1)
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        self.assertEqual(w.thanh_tren.objectName(), 'thanh_tren_lap_pa')
        self.assertIn('#F8FAFC', w.thanh_tren.styleSheet())
        self.assertEqual(w.cb_ho.objectName(), 'o_chon_ho')
        self.assertEqual(w.cb_ho.minimumHeight(), mh.CAO_NUT_TREN)
        for b in (w.b_truoc, w.b_sau):
            self.assertEqual(b.minimumHeight(), 28)
        self.assertEqual(w.b_luu.property('bien_the'), giao_dien.KieuNut.LUU.value)          # Lưu: navy đặc
        self.assertIn('#EFF6FF', _quy_tac(w.btn_toggle_preview.styleSheet(), 'QPushButton#btn_toggle_preview:checked'))
        self.assertIn('background: #FFFFFF', _quy_tac(w.btn_toggle_preview.styleSheet(), 'QPushButton#btn_toggle_preview'))
        self.assertTrue(w.tab.documentMode())
        self.assertIn(f'border-bottom: 2px solid {NAVY}', _quy_tac(w.tab.styleSheet(), 'QTabBar::tab:selected'))
        d = w.dai_dieu_huong
        self.assertIs(w.lb_tong.parentWidget(), d)
        self.assertIs(w.b_tiep_theo.parentWidget(), d)
        self.assertIn('border-top: 2px solid #CBD5E1', d.styleSheet())
        lo = d.layout()                                                  # tổng bên trái, nút điều hướng góc phải
        self.assertLess(lo.indexOf(w.lb_tong), lo.indexOf(w.b_tro_lai))
        # hàng nhập nhanh: ô / nút cao 30, nút Thêm vào bảng navy
        h = w.bang[2].hang
        from pabt.hang_nhap_nhanh import CAO_HANG
        for o in (h.o_chon.o, h.o_sl, h.o_tl, h.o_gc, h.nut_them):
            self.assertEqual(o.maximumHeight(), CAO_HANG)
        self.assertEqual(h.nut_them.property('bien_the'), giao_dien.KieuNut.CHINH.value)
        self.assertIn(NAVY, h.styleSheet())                               # ô đang gõ viền navy
        b1 = w.bang[1].nut['Thêm thửa…']
        self.assertIsInstance(b1, QPushButton)
        self.assertEqual(b1.property('bien_the'), giao_dien.KieuNut.CHINH.value)

    def test_xem_truoc_thanh_sang_nen_slate(self):
        from pabt import xem_truoc_tai_lieu as xt
        k = xt.KhungXemTruocTaiLieu()
        self.addCleanup(k.deleteLater)
        self.assertEqual(xt.MAU_NEN, '#334155')
        self.assertEqual(k.thanh.objectName(), 'xt_thanh')
        self.assertIn('#F8FAFC', _quy_tac(k.styleSheet(), 'QWidget#xt_thanh'))
        self.assertIn('#CBD5E1', _quy_tac(k.styleSheet(), 'QWidget#xt_thanh'))
        for b in (k.b_phong, k.b_thu, k.b_vua):
            self.assertEqual(b.maximumHeight(), xt.CAO_NUT_XT)


class TestTienDoKPI(_Co):
    def _khung(self):
        from pabt.man_hinh_theo_doi import KhungTienDo
        k = KhungTienDo(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        return k

    def test_the_kpi_vach_trai_va_dang_loc(self):
        from pabt import man_hinh_bao_cao as bc
        k = self._khung()
        for khoa, t in k.kpi.the.items():
            self.assertEqual(t.maximumHeight(), bc.CAO_THE_KPI)
            self.assertIn(f'border-left: 3px solid {bc.MAU_THE[khoa]}', t.styleSheet())
            self.assertIn('[dang_loc="1"]', t.styleSheet())
        self.assertEqual(set(bc.MAU_THE.values()), {NAVY, '#0F766E', '#475569', '#B91C1C'})
        self.assertIsNone(k.the_kpi_dang_loc())                          # tất cả hộ: không thẻ nào đang lọc
        self.assertFalse(any(t.dang_loc() for t in k.kpi.the.values()))
        k.bam_kpi('mat_bang')
        self.assertEqual(k.the_kpi_dang_loc(), 'mat_bang')
        self.assertEqual([x for x, t in k.kpi.the.items() if t.dang_loc()], ['mat_bang'])
        k.dat_che_do('thua')
        self.assertEqual([x for x, t in k.kpi.the.items() if t.dang_loc()], ['con_vuong'])
        k.dat_che_do('ho')
        k.cb_loc.setCurrentIndex(0)                                      # mục đầu: tất cả hộ
        self.assertFalse(any(t.dang_loc() for t in k.kpi.the.values()))

    def test_nut_che_do_vien_thuoc_va_hang_moc(self):
        from pabt import man_hinh_theo_doi as td
        k = self._khung()
        for b in k.nut_che_do.values():
            self.assertIs(b.parentWidget(), k.khung_che_do)              # hai nút trong một khung "viên thuốc"
        self.assertIn('#E2E8F0', k.khung_che_do.styleSheet())
        self.assertIn(f'background: {NAVY}', _quy_tac(td.QSS_CHE_DO, 'QPushButton:checked'))
        self.assertIn('transparent', _quy_tac(td.QSS_CHE_DO, 'QPushButton'))
        self.assertTrue(k.nut_che_do['ho'].isChecked())
        self.assertEqual(k.lb_moc.objectName(), 'lb_moc')
        self.assertIn('#F8FAFC', k.lb_moc.styleSheet())
        for w in (k.lb_moc, k.nut['Mốc pháp lý…'], k.nut['Xuất'], k.cb_loc, k.o_tim):
            self.assertGreaterEqual(w.minimumHeight(), td.CAO_O_CONG_CU)


class TestTongHopVaNiemYet(_Co):
    def test_dong_noi_co_cau_kinh_phi(self):
        from pabt import man_hinh_theo_doi as td
        k = td.KhungCoCau(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        dong = k.dong()
        mh = k.bang.mo_hinh
        for loai in ('cong', 'kinh_phi', 'tong'):
            r = next(i for i, (x, _) in enumerate(dong) if x == loai)
            ki = mh.kieu[(r, 0)]
            self.assertEqual((ki['nen'], ki['mau_chu']), td.DONG_NOI[loai])
            self.assertTrue(ki['dam'])
        self.assertEqual(td.DONG_NOI['tong'][0].name().upper(), '#F0F6FF')
        self.assertEqual(td.DONG_NOI['tong'][1].name().upper(), NAVY)

    def test_the_niem_yet_vach_trai(self):
        from pabt import man_hinh_du_thao as dt
        k = dt.KhungDuThao(self.con)
        self.addCleanup(k.close)
        for khoa, t in k.the.items():
            self.assertEqual(t.property('vai'), 'the_ny')
            self.assertIn(f'border-left: 3px solid {dt.MAU_THE_NY[khoa]}', t.styleSheet())
            self.assertEqual(t.gia.objectName(), 'the_ny_so')
        from PySide6.QtWidgets import QFrame
        self.assertIn('border-radius: 5px', k.findChild(QFrame, 'dai_tien_do_ny').styleSheet())

    def test_cot_he_so_k(self):
        from PySide6.QtCore import Qt
        from pabt import gia_dat_nq28 as nq
        from pabt.man_hinh_du_toan import HopTraNQ28
        d = HopTraNQ28(None, nq.ds_xa()[0], xem=True)
        self.addCleanup(d.deleteLater)
        d.cb_cot.setCurrentIndex(0)
        d.loc()
        it = d.bang.item(0, 6)
        if not it.text():
            self.skipTest('bảng hệ số K gắn sẵn không có dòng đầu')
        self.assertTrue(it.font().bold())
        self.assertEqual(it.foreground().color().name().upper(), giao_dien.MAU_HE_SO_K)
        self.assertTrue(int(it.textAlignment()) & int(Qt.AlignmentFlag.AlignHCenter))
        g = d.bang.item(0, 7)
        self.assertTrue(g.font().bold())
        self.assertEqual(g.foreground().color().name().upper(), NAVY)
        self.assertTrue(int(g.textAlignment()) & int(Qt.AlignmentFlag.AlignRight))


if __name__ == '__main__':
    unittest.main()
