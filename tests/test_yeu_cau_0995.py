"""0.9.95 (người dùng 16/10/2026, đặc tả "Ultra-Compact Data-First" + Quét giấy tờ): hàng thẻ số chỉ ở Danh sách hộ, banner chỉ ở màn
hình chào, cửa sổ lập phương án gọn (một hàng nút, một hàng điều hướng + tổng), cột bảng mục gọn / giãn, tổng kinh phí dự án gần đây
chuẩn, Khái toán / Niêm yết gọn, Quét giấy tờ: xem trước toàn bộ trang file + bóc tách phương án chi tiết đã số hóa (số liệu GIẢ LẬP)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


def _chu_ban_in(con, ma_ho, td, tab=True) -> str:
    """Chữ của bản in chi tiết giả lập (in_an.lap_chi_tiet) - ô cách Tab như OCR (gom_dong) / lớp chữ PDF, hoặc cách dấu cách với
    "m²" tách "m" + "2" ở hai dòng như lấy chữ PDF Excel in ra."""
    import openpyxl
    from pabt import in_an
    ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, ma_ho, Path(td) / f'ct_{ma_ho}.xlsx')).active
    dong = []
    for r in ws.iter_rows():
        o = [str(c.value).strip() for c in r if c.value is not None and str(c.value).strip()]
        if o:
            dong.append('\t'.join(o) if tab else ' '.join(o).replace('m²', 'm\n2'))
    return '\n'.join(dong)


class Co0995(CoSo):
    w = None

    def tearDown(self):
        if self.w is not None:
            for k in [k for k in self.w.khung_tab.khoa if isinstance(k, tuple)]:
                self.w.khung_tab.widget[k].bo_thay_doi()
            self.w.close()
            if self.w.con is not None:
                self.w.dong_du_an()
        super().tearDown()

    def _cua_so(self, so_ho=3):
        from pabt import app as ud
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.w.show()
        self.w.mo(str(_du_an(self.td, so_ho)))
        self.app.processEvents()
        return ud, self.w


class TestToanCuc(Co0995):
    def test_hang_the_chi_o_danh_sach_ho_banner_chi_o_man_hinh_chao(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.w = w
        w.show()
        self.app.processEvents()
        self.assertTrue(w.banner_ten.isVisibleTo(w))                    # màn hình chào: banner chuẩn
        w.mo(str(_du_an(self.td, 3)))
        w.mo_trang(0)
        self.app.processEvents()
        self.assertTrue(w.hang_the.isVisibleTo(w))                      # Danh sách hộ
        self.assertFalse(w.banner_ten.isVisibleTo(w))                   # màn hình làm việc: nhường chỗ cho bảng
        for t in ud.TRANG[1:]:
            w.lenh[t].trigger()
            self.app.processEvents()
            self.assertFalse(w.hang_the.isVisibleTo(w), t)
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        w.mo_lap_pa(ma, cho=True)
        self.assertFalse(w.hang_the.isVisibleTo(w))                     # tab hộ: không hàng thẻ số
        w._sau_tai_lai(False)                                           # tải lại khi đang ở tab hộ: vẫn ẩn
        self.assertFalse(w.hang_the.isVisibleTo(w))
        w.mo_du_thao()
        self.assertFalse(w.hang_the.isVisibleTo(w))
        w.mo_trang(ud.TRANG_DS)
        self.assertTrue(w.hang_the.isVisibleTo(w))
        w.ve_trang_chu()
        self.assertTrue(w.banner_ten.isVisibleTo(w))
        self.assertFalse(w.hang_the.isVisibleTo(w))

    def test_the_so_mot_dong_va_menu_trai_gon(self):
        from pabt import giao_dien
        ud, w = self._cua_so()
        the = w.the_so['so_ho'].parentWidget()
        # 17/10/2026 (Hybrid Enterprise Navy - thay mức 0.9.95): thẻ 56 px (tên trên, số + chữ phụ dưới), cách 8 px; nút menu 32 px
        self.assertEqual(the.maximumHeight(), ud.CuaSoChinh.CAO_THE_SO)
        self.assertEqual(w.hang_the.layout().spacing(), 8)
        self.assertEqual(giao_dien.CAO_NUT_MENU, 32)
        km = w.khung_menu
        self.assertGreaterEqual(km.width(), giao_dien.RONG_MENU_TRAI)
        self.assertLessEqual(km.width(), giao_dien.RONG_MENU_TOI_DA)
        km._vua_rong.eventFilter(km, type('E', (), {'type': lambda s: giao_dien.QEvent.Type.Show})())
        from PySide6.QtWidgets import QToolButton
        rong = [b.sizeHint().width() for b in km.findChildren(QToolButton) if b.property('menu') == '1']
        self.assertLessEqual(min(max(rong) + 18, giao_dien.RONG_MENU_TOI_DA), km.width())   # chữ lệnh không bị cắt (tới mức tối đa)

    def test_tong_kinh_phi_du_an_gan_day_khop_danh_sach_ho(self):
        from pabt import app as ud, csdl, doi_chieu
        from pabt.tien import D, vn
        p = _du_an(self.td, 30)
        so_ho, tong, chu_tim, hien = ud._tom_tat_pabt(p)
        con = csdl.mo(str(p), chi_doc=True)
        try:
            kq = doi_chieu.doi_chieu(con)
            dung = sum((h['tong'] for h in kq.ho), D('0'))
            ten, dia_ban = con.execute('SELECT ten, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
        finally:
            con.close()
        self.assertEqual(so_ho, 30)
        self.assertEqual(tong, vn(dung))                                 # cả thưởng bàn giao mặt bằng, làm tròn như danh sách hộ
        self.assertEqual(hien, f'{ten} · {dia_ban} ({p.name})')
        self.assertEqual(ud._tom_tat_pabt(p)[1], tong)                   # lần sau: đọc từ bộ nhớ (cùng số)


class TestLapPhuongAn(Co0995):
    def test_hang_tren_mot_hang_va_dieu_huong_chung_tong(self):
        from PySide6.QtWidgets import QPushButton
        from pabt import hang_nhap_nhanh, man_hinh
        ud, w = self._cua_so()
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        c = w.mo_lap_pa(ma, cho=True)
        self.assertEqual(c.b_truoc.text(), '◀')
        self.assertEqual(c.b_sau.text(), '▶')
        self.assertIn('Ctrl+Left', c.b_truoc.toolTip())
        self.assertIn('Ctrl+Right', c.b_sau.toolTip())
        from pabt.man_hinh import RONG_O_HO                                  # 16/10/2026: ô rộng hơn, đủ tên hộ
        self.assertEqual((c.cb_ho.minimumWidth(), c.cb_ho.maximumWidth()), (150 if c.width() < c.RONG_THANH_TREN_GON else RONG_O_HO[0], RONG_O_HO[1]))
        for b in (c.b_dan, c.b_luu, c.btn_toggle_preview, c.b_dong):
            self.assertEqual(b.height() or b.minimumHeight(), man_hinh.CAO_NUT_TREN)
        # một hàng điều hướng chung với dải tổng cộng, thẻ mục không còn hàng nút riêng
        for bm in c.bang.values():
            chu = [b.text() for b in bm.findChildren(QPushButton)]
            self.assertFalse([t for t in chu if t.startswith(('◀ Trở lại', 'Tiếp theo'))], chu)
        lo = c.lb_tong.parentWidget().layout()
        self.assertIsNotNone(lo)
        c.tab.setCurrentIndex(0)
        self.assertFalse(c.b_tro_lai.isVisibleTo(c))
        self.assertEqual(c.b_tiep_theo.text(), 'Mục tiếp theo ▶')
        self.assertIn('1. Đất', c.b_tiep_theo.toolTip())
        c.b_tiep_theo.click()
        self.assertEqual(c.tab.currentIndex(), 1)
        self.assertTrue(c.b_tro_lai.isVisibleTo(c))
        # mục 1: nút thao tác dòng + "Cộng mục 1" cùng hàng chọn thửa
        b1 = c.bang[1]
        self.assertIs(b1.nut['▲ Lên'].parentWidget().parentWidget(), b1.cb_thua.parentWidget().parentWidget())
        # 20/10/2026 (ảnh mẫu): "CỘNG MỤC k" ở dải chân bảng (mọi mục), không còn trên hàng chọn thửa
        self.assertIs(b1.lb_tong.parentWidget(), b1.dai_cong)
        for ten in ('▲ Lên', '▼ Xuống'):                                 # Xóa dòng: thùng rác cột cuối (18/10/2026)
            self.assertEqual(c.bang[1].nut[ten].height() or c.bang[1].nut[ten].minimumHeight(), man_hinh.CAO_NUT_DONG)
            # 1.0.75: mục 2 trở đi nút lên cùng hàng nhập nhanh, cao bằng hàng
            self.assertEqual(c.bang[2].nut[ten].height() or c.bang[2].nut[ten].minimumHeight(), hang_nhap_nhanh.CAO_HANG)

    def test_cot_bang_muc_gon_va_gian(self):
        from PySide6.QtWidgets import QHeaderView
        from pabt import man_hinh
        ud, w = self._cua_so()
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        c = w.mo_lap_pa(ma, cho=True)
        bm = c.bang[2]
        khoa = [k[0] for k in bm.cot]
        hd = bm.bang.horizontalHeader()
        self.assertEqual(hd.sectionResizeMode(khoa.index('ten')), QHeaderView.ResizeMode.Stretch)
        for k in ('quy_cach', 'ghi_chu'):                   # 0.9.96: cột thường trống gọn, không giãn
            self.assertNotEqual(hd.sectionResizeMode(khoa.index(k)), QHeaderView.ResizeMode.Stretch, k)
        for k, rong in man_hinh.RONG_COT_GON.items():
            if k in khoa:
                self.assertGreaterEqual(bm.bang.columnWidth(khoa.index(k)), rong, k)    # >= (sàn tiêu đề có thể nới)
        self.assertFalse(hd.stretchLastSection())


class TestKhaiToanNiemYet(Co0995):
    def test_khai_toan_tong_va_nut_mot_hang(self):
        from pabt import man_hinh_du_toan as mdt
        ud, w = self._cua_so()
        k = w.du_toan(cho=False)
        from PySide6.QtWidgets import QHBoxLayout
        self.assertTrue(any(h.indexOf(k.lb_tong) >= 0 and h.indexOf(k.b_luu) >= 0 for h in k.findChildren(QHBoxLayout)))
        self.assertEqual(k.lb_tong.height() or k.lb_tong.minimumHeight(), mdt.CAO_THE_TONG_KT)   # 1.0.03: 2 dòng (tổng + cơ cấu)
        self.assertGreaterEqual(k.o_dt_dat.minimumWidth(), 90)          # 1.0.03: gọn để thanh nhập một hàng
        self.assertGreaterEqual(k.o_gia_dat.minimumWidth(), 95)
        k.an_thong_tin_chung(True)
        self.assertFalse(k._than_chuan_bi[0].isVisibleTo(k))
        self.assertEqual(k.b_an_tt.text(), 'Hiện thông tin chung')
        k.an_thong_tin_chung(False)
        self.assertTrue(k._than_chuan_bi[0].isVisibleTo(k))
        k.can_mot_hang()
        for b in (k.b_tra_nq28, k.b_dan, k.b_ocr, k.b_them):
            self.assertGreaterEqual(b.minimumWidth(), b.sizeHint().width())

    def test_niem_yet_kpi_mot_dong_nut_goc_va_tieu_de_khong_cat(self):
        from PySide6.QtGui import QFont, QFontMetrics
        from PySide6.QtWidgets import QHeaderView
        ud, w = self._cua_so()
        w.mo_du_thao()
        k = w.khung_tab.widget['du_thao']
        for t in k.the.values():
            self.assertLessEqual(t.maximumHeight(), 60)       # 1.0.03: thẻ KPI 2 tầng 54 px
        k.tabs.setCurrentIndex(3)
        self.assertTrue(k._nut['Xuất báo cáo tổng hợp ý kiến'].isVisibleTo(k))
        self.assertFalse(k._nut['Xuất biên bản đối thoại'].isVisibleTo(k))
        self.assertIsNone(k.tabs.cornerWidget())             # 06/11/2026: hàng nút riêng, không chiếm chỗ thanh thẻ
        self.assertIs(k._goc_nut, k._nut['Xuất báo cáo tổng hợp ý kiến'].parentWidget())
        k.tabs.setCurrentIndex(2)
        self.assertTrue(k._nut['Xuất biên bản đối thoại'].isVisibleTo(k))
        self.assertGreaterEqual(k.bang_th.columnWidth(0), 185)
        for b in (k.bang_ny, k.bang_yk, k.bang_dt, k.bang_th, k.bang_vm):
            hd = b.horizontalHeader()
            f = QFont(hd.font())
            f.setBold(True)
            fm = QFontMetrics(f)
            for c in range(b.columnCount()):
                if hd.sectionResizeMode(c) != QHeaderView.ResizeMode.Stretch:
                    self.assertGreaterEqual(b.columnWidth(c), fm.horizontalAdvance(b.horizontalHeaderItem(c).text()))


class TestQuetGiayTo(Co0995):

    def test_nguon_goc_cccd_ocr_va_tab_cot(self):
        from pabt import ocr, ocr_ho_so
        chu = ('Họ và tên:\tNguyễn Văn Thử\nSố CCCD:\t O75O92OO1234\nĐịa chỉ thường trú:\tẤp 1, xã Bàu Hàm\n'
               'II. Thông tin vị trí, nguồn gốc đất\n- Đất sử dụng ổn định từ năm 1990,\nkhông tranh chấp.\n'
               'III. Bảng tính toán bồi thường, hỗ trợ\nSTT\tTên tài sản\tĐVT\tSố lượng\nTỔNG CỘNG\t0\n'
               'IV\tTái định cư: Không đủ điều kiện.\nSố nhân khẩu: 4')
        kq = ocr_ho_so.boc_tach(chu)
        self.assertEqual(kq.ho_ten, 'Nguyễn Văn Thử')
        self.assertEqual(kq.so_cccd, '075092001234')                    # O -> 0
        self.assertEqual(kq.nguon_goc, '- Đất sử dụng ổn định từ năm 1990, không tranh chấp.')
        self.assertEqual(kq.tai_dinh_cu, 'Không đủ điều kiện')
        self.assertEqual(kq.nhan_khau, 4)
        tu = [(10, 100, 60, 20, 'Nhà'), (80, 100, 40, 20, 'tạm'), (300, 100, 30, 20, 'm²'), (400, 100, 30, 20, '46')]
        self.assertEqual(ocr.gom_dong(tu), ['Nhà tạm\tm²\t46'])

    def test_xem_truoc_mac_dinh_anh_va_pdf_nhieu_trang(self):
        from PySide6.QtGui import QColor, QImage, QPainter, QPdfWriter
        from pabt import csdl
        from pabt.man_hinh import CuaSoLapPA
        from pabt.man_hinh_ocr import HopQuetGiayTo
        td = Path(tempfile.mkdtemp(dir=self.td))
        anh = td / 'gcn.png'
        im = QImage(600, 800, QImage.Format.Format_RGB32)
        im.fill(QColor('#FFFFFF'))
        im.save(str(anh))
        pdf = td / 'pa.pdf'
        wr = QPdfWriter(str(pdf))
        p = QPainter(wr)
        for i in range(3):
            if i:
                wr.newPage()
            p.drawText(100, 100, f'Trang {i + 1}')
        p.end()
        con = csdl.mo(str(_du_an(self.td, 2)))
        try:
            ma = con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
            c = CuaSoLapPA(con, ma)
            h = HopQuetGiayTo(c, 'du_toan')                              # 0.9.96: hộp quét chỉ còn cho Khái toán
            h.im_lang = True
            self.assertEqual(h.ngan_trai.currentIndex(), 0)              # mặc định: xem trước file
            self.assertIs(h.ngan_trai.widget(0), h.khung_xem_file)
            self.assertIsNotNone(h.o_chu)
            self.assertEqual(h.khung_xem_file.nap([anh]), 1)
            try:
                from PySide6.QtPdf import QPdfDocument          # noqa: F401
                co_qtpdf = True
            except ImportError:
                co_qtpdf = False
            n = h.khung_xem_file.nap([anh, pdf])
            if co_qtpdf:
                self.assertEqual(n, 4)                                   # ảnh + 3 trang PDF xếp dọc
                self.assertEqual(h.lb_trang.text(), 'Trang 1 / 4')
                h.resize(1200, 700)
                h.show()
                self.app.processEvents()
                h.b_trang_sau.click()
                h.b_trang_sau.click()
                self.assertEqual(h.lb_trang.text(), 'Trang 3 / 4')
            goc = h.khung_xem_file.he_so
            h.b_phong_to.click()
            self.assertGreater(h.khung_xem_file.he_so, goc)
            h.b_xoay.click()
            self.assertEqual(h.khung_xem_file.goc, 90)
            h.b_doi_xem.setChecked(True)
            self.assertEqual(h.ngan_trai.currentIndex(), 1)
            self.assertFalse(hasattr(h, 'b_tron_bo') or hasattr(h, 'o_luu_dinh_kem'))
            c.bo_thay_doi()
            c.close()
        finally:
            con.close()


class TestChayKhongTreo(CoSo):
    def test_ket_qua_lon_khong_treo_ong_dan(self):
        """0.9.95: _chay đọc stdout song song - trước đây kết quả > ~64 KB (trang scan bảng giá nhiều chữ) làm đầy ống, tiến trình
        con chặn ghi, chờ tới hết giờ rồi báo "Nhận dạng chữ quá lâu" (Windows OCR 180 s / trang)."""
        import sys
        import time
        from pabt import ocr
        t = time.monotonic()
        r = ocr._chay([sys.executable, '-c', "import sys; sys.stdout.write('x' * 400000)"], gioi_han=30)
        self.assertEqual(len(r.stdout), 400000)
        self.assertLess(time.monotonic() - t, 20)
