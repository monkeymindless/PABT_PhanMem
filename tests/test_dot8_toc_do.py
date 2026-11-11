"""Đợt 8 (1.0.99) - tốc độ: kết quả GIỐNG HỆT trước khi tối ưu.
T1 tô màu nút lúc Polish (không unpolish / polish lại), nhớ nhom_nut / ky_hieu_nut; T2 kiểu ô Excel dựng một lần; T3 Màn hình chính không vẽ
lại khi số liệu không đổi; T4 bảng mô hình; T5 Kiểm tra lỗi chạy nền, nhớ dòng giá đất."""
from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QPushButton

from pabt import giao_dien

CHU_NUT = ['Lưu', 'Xóa', 'In / Xuất…', 'Đóng', 'Thêm hộ…', 'Đối chiếu', 'Chốt V1', 'Hủy', 'Mở file…', 'Xuất Excel']


class TestT1ToMau(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qa = QApplication.instance() or QApplication([])
        cls.tu_ap = getattr(cls.qa, '_bo_to_mau', None) is None
        giao_dien.ap_dung(cls.qa)                       # gọi lại không làm gì (đã áp ở bài khác)

    @classmethod
    def tearDownClass(cls):
        if cls.tu_ap:                                   # bài này tự áp bảng kiểu: gỡ, không để lại cho bài sau (đo bố cục / tốc độ)
            giao_dien.bo_ap_dung(cls.qa)

    def test_nho_nhom_nut_dung_nhu_khong_nho(self):
        for chu in CHU_NUT + ['', 'Lập phương án hộ', '&Lưu']:
            self.assertEqual(giao_dien.nhom_nut(chu), giao_dien.nhom_nut.__wrapped__(chu), chu)
            self.assertEqual(giao_dien.ky_hieu_nut(chu), giao_dien.ky_hieu_nut.__wrapped__(chu), chu)

    def test_mau_nut_giong_ep_ap_kieu_lai(self):
        """Ảnh hộp sau khi hiện == ảnh sau khi ép unpolish / polish từng nút (cách cũ): nhóm màu áp đúng, không sót nút nào."""
        h = QDialog()
        lo = QGridLayout(h)
        for i, chu in enumerate(CHU_NUT * 2):
            lo.addWidget(QPushButton(chu), i // 4, i % 4)
        h.show()
        self.qa.processEvents()
        for b in h.findChildren(QPushButton):
            self.assertEqual(b.property('nhom'), giao_dien.nhom_nut(b.text()), b.text())
        truoc = h.grab().toImage()
        for b in h.findChildren(QPushButton):
            b.style().unpolish(b)
            b.style().polish(b)
            b.update()
        self.qa.processEvents()
        sau = h.grab().toImage()
        self.assertEqual(truoc, sau)
        h.close()
        h.deleteLater()


class TestT2KieuO(unittest.TestCase):
    def test_kieu_o_giong_gan_tung_o(self):
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from pabt.ghi_xlsx_nhanh import KieuO
        wb = openpyxl.Workbook()
        ws = wb.active
        s = Side(style='thin', color='808080')
        tt = dict(border=Border(left=s, right=s, top=s, bottom=s), number_format='#,##0.0#', font=Font(bold=True, color='C00000'),
                  fill=PatternFill('solid', fgColor='E2EFDA'), alignment=Alignment(wrap_text=True, vertical='top'))
        a = ws.cell(1, 1, 5.5)
        for k, v in tt.items():
            setattr(a, k, v)
        k = KieuO(ws, **tt)
        b = k.ap(ws.cell(2, 1, 5.5))
        c = k.ap(ws.cell(3, 1, 7))
        for o in (b, c):
            self.assertEqual(o._style, a._style)
            for ten in tt:
                self.assertEqual(repr(getattr(o, ten)), repr(getattr(a, ten)), ten)
        self.assertEqual(len(ws._cells), 3)                    # ô mẫu của KieuO không nằm trong trang tính
        b.number_format = '0'                                   # sửa một ô không đổi ô khác (mảng kiểu là bản chép)
        self.assertEqual(c.number_format, '#,##0.0#')

    def test_bao_cao_tong_hop_kieu_o_du_lieu(self):
        import tempfile
        from pathlib import Path

        import openpyxl
        from pabt import csdl, du_an_moi, quan_ly
        td = Path(tempfile.mkdtemp())
        dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to='10', so_thua=str(100 + i), loai_dat='ONT', dt_thu_hoi='120,5',
                     vi_tri='1', nhan_khau='4') for i in range(2)]
        du_an_moi.tao_du_an(str(td / 'a.pabt'), dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'), dong,
                            [dict(loai_dat='ONT', vi_tri='1', gia='3000000')])
        con = csdl.mo(str(td / 'a.pabt'))
        try:
            sl = quan_ly.du_lieu_bao_cao(con)
        finally:
            con.close()
        p = td / 'bc.xlsx'
        quan_ly.ghi_bao_cao_tong_hop(sl, p)
        ws = openpyxl.load_workbook(p)['Danh sach']
        for r in (6, 7):
            for c in range(1, len(quan_ly.COT_BAO_CAO) + 1):
                o = ws.cell(r, c)
                self.assertEqual(o.border.left.style, 'thin', o.coordinate)
                self.assertEqual(bool(o.alignment.wrap_text), c in (3, 4, 14, 19), o.coordinate)
                if isinstance(o.value, (int, float)) and c not in (1, 2, 6):
                    self.assertEqual(o.number_format, '#,##0.0#' if c == 7 else '#,##0', o.coordinate)
        self.assertEqual(ws['G6'].value, 120.5)


def du_an_gia_lap(td, n: int = 6):
    from pabt import du_an_moi
    dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to='10', so_thua=str(100 + i), loai_dat='ONT', dt_thu_hoi='120,5',
                 vi_tri='1', nhan_khau='4') for i in range(n)]
    p = str(td / 'a.pabt')
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'), dong,
                        [dict(loai_dat='ONT', vi_tri='1', gia='3000000')])
    return p


class TestT3ManHinhChinh(unittest.TestCase):
    def test_ve_lai_chi_khi_so_lieu_doi(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        QApplication.instance() or QApplication([])
        from pabt import app as ud
        p = du_an_gia_lap(Path(tempfile.mkdtemp()))
        w = ud.CuaSoChinh(menu_trai=True)
        try:
            w.mo(p, chi_doc=False)
            w.ve_trang_chu()
            self.assertIsNotNone(w.tong_quan)
            with mock.patch.object(w.tong_quan, 'nap', wraps=w.tong_quan.nap) as nap:
                w.ve_trang_chu()
                w.ve_trang_chu()
                self.assertEqual(nap.call_count, 0)                 # số liệu không đổi: không tính / vẽ lại
                with w.con:
                    w.con.execute("UPDATE ho SET ho_ten = 'Hộ đã đổi tên' WHERE ma_ho = (SELECT MIN(ma_ho) FROM ho)")
                w.ve_trang_chu()
                self.assertEqual(nap.call_count, 1)                 # dữ liệu đổi: nạp lại
                w.ve_trang_chu()
                self.assertEqual(nap.call_count, 1)
        finally:
            w.dong_du_an()
            w.close()
            w.deleteLater()


class TestT5KiemLoiNho(unittest.TestCase):
    def test_nho_dung_va_tinh_lai_khi_doi(self):
        import tempfile
        from pathlib import Path
        from pabt import csdl, kiem_loi
        con = csdl.mo(du_an_gia_lap(Path(tempfile.mkdtemp())))
        try:
            a = kiem_loi.kiem_tra_nho(con)
            self.assertIs(kiem_loi.kiem_tra_nho(con), a)            # chưa đổi: dùng lại
            self.assertEqual([vars(x) for x in a], [vars(x) for x in kiem_loi.kiem_tra(con)])   # giống hệt tính mới
            with con:
                con.execute("UPDATE ho SET so_cccd = 'abc' WHERE ma_ho = (SELECT MIN(ma_ho) FROM ho)")
            b = kiem_loi.kiem_tra_nho(con)
            self.assertIsNot(b, a)                                   # dữ liệu đổi: tính lại
            self.assertEqual([vars(x) for x in b], [vars(x) for x in kiem_loi.kiem_tra(con)])
        finally:
            con.close()


class TestDot9DungLaiLapPA(unittest.TestCase):
    """Đợt 9 (1.1.00): mở hộ khác khi cửa sổ Lập PA đang mở SẠCH -> chuyển hộ trong cửa sổ đó (không dựng lại); còn thay đổi chưa lưu -> giữ
    cửa sổ đó, mở cửa sổ mới như cũ."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        QApplication.instance() or QApplication([])
        from pabt import app as ud
        self.p = du_an_gia_lap(Path(tempfile.mkdtemp()))
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.w.mo(self.p, chi_doc=False)
        self.ma = [r[0] for r in self.w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]

    def tearDown(self):
        for k in list(self.w.khung_tab.khoa):
            ww = self.w.khung_tab.widget.get(k)
            if ww is not None and hasattr(ww, 'bo'):
                ww.bo.mo(ww.bo.ma_ho)                               # bỏ thay đổi chưa lưu: đóng dự án không hỏi lưu
        self.w.dong_du_an()
        self.w.close()
        self.w.deleteLater()

    def test_dung_lai_cua_so_sach(self):
        a = self.w.mo_lap_pa(self.ma[0])
        b = self.w.mo_lap_pa(self.ma[1])
        self.assertIs(b, a)                                         # cùng cửa sổ, không dựng lại
        self.assertEqual(b.bo.ma_ho, self.ma[1])
        self.assertIn(('ho', self.ma[1]), self.w.khung_tab.khoa)
        self.assertNotIn(('ho', self.ma[0]), self.w.khung_tab.khoa)
        self.assertEqual(b.tab.currentIndex(), 1 if b.bo.pa.dat else 0)   # như cửa sổ mới (hộ có dòng đất: thẻ mục 1)
        c = self.w.mo_lap_pa(self.ma[2], the=0)
        self.assertIs(c, a)
        self.assertEqual(c.tab.currentIndex(), 0)

    def test_khong_dung_lai_cua_so_con_thay_doi(self):
        a = self.w.mo_lap_pa(self.ma[0])
        a.bo.sua_dat(0, 'dien_tich', '77')                          # có thay đổi chưa lưu
        self.assertTrue(a.bo.co_thay_doi)
        b = self.w.mo_lap_pa(self.ma[1])
        self.assertIsNot(b, a)
        self.assertEqual(a.bo.ma_ho, self.ma[0])                    # hộ cũ vẫn giữ nguyên trong cửa sổ của nó
        self.assertIn(('ho', self.ma[0]), self.w.khung_tab.khoa)


if __name__ == '__main__':
    unittest.main()
