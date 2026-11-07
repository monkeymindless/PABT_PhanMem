"""1.0.34 (người dùng 29/10/2026) "Flagship Sapphire": bảng màu mới mặc định, tông Tối chuyên gia / Ấm áp, menu trái tối dạng viên, banner đồ
họa + nút đổi nhanh Sáng / Tối, thẻ chào mỗi thẻ một màu (huy hiệu biểu tượng, phím tắt), thẻ KPI có thanh tiến độ, hình minh họa khi bảng
trống, hoạt ảnh chuyển trang / thu gọn menu (tắt khi không màn hình). Bài kiểm KHÔNG áp lại bảng kiểu cho QApplication thật (_UngDungGia)."""
from __future__ import annotations
import os
import unittest
from unittest import mock

from pabt import chu_de, giao_dien
from tests import APP
from tests.test_yeu_cau_1033 import _UngDungGia

CO_QT = APP is not None


class TestBangMau(unittest.TestCase):
    def tearDown(self):
        giao_dien.dat_tong_nen('sang', ap_lai=False)

    def test_token_flagship(self):
        t = giao_dien.TOKEN
        self.assertEqual((t['chinh'], t['chinh_re'], t['nhan'], t['thanh_cong'], t['canh_bao'], t['nguy_hiem']),
                         ('#345678', '#284460', '#2563EB', '#059669', '#D97706', '#DC2626'))
        self.assertEqual((t['nen'], t['nen_the'], t['vien']), ('#F3F6FA', '#FFFFFF', '#D5DEE8'))      # 1.0.35: PA1 Slate-Navy
        qss = giao_dien._qss_day_du()
        for cu in ('#2F5F9E', '#3B6FCE', '#264E83'):
            self.assertNotIn(cu, qss.upper())
        self.assertIn('background: #F3F6FA', qss)                       # mặc định khác màu gốc (#F8FAFC)
        self.assertNotIn('#1E3A8A', qss.upper())                         # 1.0.35: màu chính gốc #1E3A5F

    def test_tong_nen_bon_che_do_va_toi(self):
        self.assertTrue({'sang', 'titan', 'am', 'ngoc', 'toi', 'diu', 'trang'} == set(chu_de.TONG_NEN) == set(chu_de.MAU_TONG))
        self.assertEqual(chu_de.TONG_NEN['toi'][1:], ('#0B1120', '#1E293B', '#334155', '#F1F5F9', '#CBD5E1'))
        giao_dien.TONG_NEN[0] = 'toi'
        try:
            day_du = giao_dien._qss_day_du()                             # dựng từ màu gốc rồi đổi theo tông Tối
            self.assertIn('background: #0B1120', day_du)
            self.assertIn('background: #1E293B', day_du)
            self.assertNotRegex(day_du, r'(?<![\w-])color: #0F172A')     # chữ chính sáng (dòng xen kẽ nền tối thì được)
            self.assertTrue(day_du.endswith(giao_dien.QSS_TOI + giao_dien._qss_menu_trai('toi')))   # khối Tối + menu đặt cuối
            self.assertIn('QFrame[vai="menu_trai"] { background: #0F172A;', day_du)
            self.assertIn('background: #2563EB', day_du)                 # màu chính tông Tối (nút đặc)
        finally:
            giao_dien.TONG_NEN[0] = 'sang'

    def test_dao_nhanh(self):
        self.assertEqual(chu_de.dao_nhanh_tong_nen('sang'), 'toi')
        self.assertEqual(chu_de.dao_nhanh_tong_nen('am'), 'toi')
        self.assertEqual(chu_de.dao_nhanh_tong_nen('toi'), 'sang')

    def test_menu_trai_theo_tong(self):
        # 1.0.35: PA1 mặc định menu SÁNG liền mạch; Titan / Tối menu tối
        q = giao_dien._qss_menu_trai()
        for chu in ('QFrame[vai="menu_trai"] { background: #E8EEF5', 'border-right: 1px solid #D5DEE8', 'border-radius: 8px',
                    'background: #DBEAFE; color: #1E3A5F', 'border-left: 4px solid #2563EB', 'color: #1E3A5F; font-size: 11px',
                    'letter-spacing: 0'):
            self.assertIn(chu, q)
        t = giao_dien._qss_menu_trai('titan')
        self.assertIn('QFrame[vai="menu_trai"] { background: #1E293B', t)
        self.assertIn('border-left: 4px solid #60A5FA', t)
        self.assertEqual((giao_dien.mau_menu()['icon'], giao_dien.mau_menu()['icon_chon']), ('#475569', '#1E3A5F'))
        for ten in chu_de.MAU_TONG:                                      # màu chính khác nhau theo tông, map đúng
            giao_dien.TONG_NEN[0] = ten
            try:
                self.assertEqual(giao_dien.mau_theo_tong('#1E3A5F', 'nen'), chu_de.mau_tong(ten)['chinh'])
            finally:
                giao_dien.TONG_NEN[0] = 'sang'

    def test_mau_mo_hinh_theo_tong(self):
        # 1.0.35: màu đặt trong mô hình bảng (ô chỉ đọc, 3 dòng Cộng / Kinh phí / Tổng, dòng con, số tiền) đổi theo tông Tối
        from pabt.man_hinh_theo_doi import dong_noi
        self.assertEqual(giao_dien.mau_theo_tong('#F4F6F8'), '#F4F6F8')
        giao_dien.TONG_NEN[0] = 'toi'
        try:
            self.assertEqual(giao_dien.mau_theo_tong('#F4F6F8'), '#162033')
            self.assertEqual(giao_dien.mau_theo_tong('#475569', 'chu'), '#CBD5E1')
            self.assertEqual(giao_dien.mau_so('150.000.000', tien=True), '#93C5FD')
            for k in ('cong', 'kinh_phi', 'tong'):
                nen, chu = dong_noi(k)
                self.assertLess(nen.lightness(), 80, k)                    # nền tối
                self.assertGreater(chu.lightness(), 150, k)                # chữ sáng
        finally:
            giao_dien.TONG_NEN[0] = 'sang'

    def test_mau_the_chao_bon_mau(self):
        nhan = [v[3] for v in giao_dien.MAU_THE_CHAO.values()]
        self.assertEqual(nhan, ['#2563EB', '#059669', '#D97706', '#7C3AED'])
        self.assertEqual(len(set(v[2] for v in giao_dien.MAU_THE_CHAO.values())), 4)
        for k, v in giao_dien.MAU_THE_CHAO.items():
            self.assertIn(f'QFrame[vai="the_chao"][loai="{k}"] {{ background: qlineargradient', giao_dien.QSS_THE_CHAO)
            self.assertIn(f'border-top: 4px solid {v[3]}', giao_dien.QSS_THE_CHAO)

    def test_bong_do_va_hoat_anh_tat_khi_khong_man_hinh(self):
        with mock.patch.dict(os.environ, {'QT_QPA_PLATFORM': 'offscreen'}):
            self.assertFalse(giao_dien.co_bong_do())
            self.assertFalse(giao_dien.co_hoat_anh())
        with mock.patch.dict(os.environ, {'QT_QPA_PLATFORM': 'windows', 'PABT_HIEU_UNG_BONG': '0', 'PABT_HOAT_ANH': '0'}):
            self.assertFalse(giao_dien.co_bong_do())
            self.assertFalse(giao_dien.co_hoat_anh())


@unittest.skipUnless(CO_QT, 'không có Qt')
class TestThanhPhan(unittest.TestCase):
    def tearDown(self):
        giao_dien.dat_tong_nen('sang', ap_lai=False)

    def test_the_kpi_co_thanh_tien_do(self):
        from PySide6.QtWidgets import QProgressBar
        t = giao_dien.TheKpiGon('Tiến độ phê duyệt', '#059669')
        self.assertIsInstance(t.thanh_tien_do, QProgressBar)
        self.assertEqual(t.height(), giao_dien.CAO_THE_KPI_GON)
        t.dat('3/6 hộ', '50%', tien_do=50)
        self.assertEqual(t.thanh_tien_do.value(), 50)
        self.assertFalse(t.thanh_tien_do.isHidden())
        t.dat('—')
        self.assertTrue(t.thanh_tien_do.isHidden())
        t.dat('x', tien_do=140)
        self.assertEqual(t.thanh_tien_do.value(), 100)
        self.assertEqual(t.thanh_tien_do.property('mau'), '#059669')
        self.assertIn('QProgressBar[vai="thanh_tien_do"][mau="#059669"]::chunk', giao_dien._qss_day_du())
        t.deleteLater()

    def test_the_so_cua_so_chinh(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        try:
            self.assertEqual(set(w.the_tien_do), set(w.the_so))
            self.assertTrue(all(t.isHidden() for t in w.the_tien_do.values()))       # chưa mở dự án
            self.assertEqual(w.the_tien_do['tong'].property('mau'), giao_dien.MAU_NHOM_KPI['tien'])
            banner = w.banner_ten
            self.assertIsInstance(banner, giao_dien.KhungBanner)
            self.assertIsInstance(banner.btn_doi_giao_dien, giao_dien.NutDoiGiaoDien)
            self.assertEqual(banner.btn_doi_giao_dien.text(), 'Tối')
            anh = banner.grab().toImage()                                              # vẽ được (lưới, vòng cung, viền đáy)
            self.assertFalse(anh.isNull())
            ud = _UngDungGia()
            with mock.patch.object(giao_dien.QApplication, 'instance', return_value=ud), \
                    mock.patch.object(giao_dien, 'cai_dat_nho', return_value=None):
                banner.btn_doi_giao_dien.click()
                self.assertEqual(giao_dien.TONG_NEN[0], 'toi')
                self.assertEqual(banner.btn_doi_giao_dien.text(), 'Sáng')
                self.assertIn('#0B1120', ud.kieu)
                banner.btn_doi_giao_dien.click()
                self.assertEqual(giao_dien.TONG_NEN[0], 'sang')
                self.assertEqual(banner.btn_doi_giao_dien.text(), 'Tối')
            the = w.the_chao['Dự án mới…']
            b = w.nut_chao['Dự án mới…']
            self.assertEqual((b.iconSize().width(), b.iconSize().height()), (44, 44))
            if the.lb_phim is not None:                                                # phím tắt THẬT của lệnh
                self.assertEqual(the.lb_phim.text(), w.lenh['Dự án mới…'].shortcut().toString())
                self.assertIs(the.lb_phim.parentWidget(), the)
        finally:
            w.close()
            w.deleteLater()
            APP.processEvents()

    def test_chuyen_trang_muot_va_rong_muot(self):
        from PySide6.QtWidgets import QLabel, QStackedWidget, QWidget
        st = QStackedWidget()
        for i in range(3):
            st.addWidget(QLabel(str(i)))
        giao_dien.chuyen_trang_muot(st, 2)
        self.assertEqual(st.currentIndex(), 2)                                         # không màn hình: đổi ngay
        giao_dien.chuyen_trang_muot(st, 2)
        self.assertEqual(st.currentIndex(), 2)
        self.assertIsNone(getattr(st, '_hoat_anh_trang', None))                        # 1.0.44: không còn QVariantAnimation trượt
        w = QWidget()
        giao_dien.dat_rong_muot(w, 120)
        self.assertEqual((w.minimumWidth(), w.maximumWidth()), (120, 120))
        st.deleteLater()
        w.deleteLater()

    def test_minh_hoa_trong(self):
        from pabt.ve_bieu_tuong import LOAI_MINH_HOA, ve_minh_hoa_trong
        for loai in LOAI_MINH_HOA + ('la',):
            pm = ve_minh_hoa_trong(loai, 96)
            self.assertEqual((pm.width(), pm.height()), (96, 96))
            anh = pm.toImage()
            self.assertGreater(anh.pixelColor(48, 48).alpha(), 0)                      # nền tròn mờ
            self.assertEqual(anh.pixelColor(1, 1).alpha(), 0)                           # góc trong suốt

    def test_hop_giao_dien_co_xem_truoc(self):
        from pabt.man_hinh_giao_dien import HopGiaoDien
        h = HopGiaoDien(im_lang=True)
        self.assertEqual(set(h.mau_xem), set(chu_de.TONG_NEN))
        self.assertIn('#0B1120', h.mau_xem['toi'].styleSheet())
        h.close()
        h.deleteLater()


if __name__ == '__main__':
    unittest.main()
