"""Người dùng 16/10/2026 (sau 0.9.96): bấm lại "Lập phương án chi tiết" sau khi mở Niêm yết hiện đúng cửa sổ lập phương án; menu chuột
phải bảng các mục; bản in: dòng ngày "Trị An, ngày ...... tháng ..... năm", tổ chức ẩn dòng CCCD, "DỰ ÁN <tên>"; Trung tâm in xem trước
bảng tổng hợp. Số liệu GIẢ LẬP."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an
from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an
from tests.test_yeu_cau_0984 import CoSoXem


class _Co(CoSo):
    def tearDown(self):
        self.doCleanups()
        super().tearDown()


class TestMoLaiLapPhuongAn(_Co):
    def test_niem_yet_roi_lap_phuong_an(self):
        from pabt import app as ud
        from pabt.man_hinh import CuaSoLapPA
        from pabt.man_hinh_du_thao import KhungDuThao
        w = ud.CuaSoChinh(menu_trai=True)
        w.show()
        w.mo(str(_du_an(self.td, 3)))
        self.app.processEvents()

        def don():
            for k in [k for k in w.khung_tab.khoa if isinstance(k, tuple)]:
                w.khung_tab.widget[k].bo_thay_doi()
            w.close()
            w.dong_du_an()
        self.addCleanup(don)
        L = w.lenh
        hien = lambda: w.khung_tab.stack_phu.currentWidget()        # noqa: E731
        L['Lập phương án hộ…'].trigger()
        self.assertIsInstance(hien(), CuaSoLapPA)
        L['Dự thảo PABT…'].trigger()
        self.assertIsInstance(hien(), KhungDuThao)
        L['Lập phương án hộ…'].trigger()                                  # trước: vẫn hiện Niêm yết
        self.assertIsInstance(hien(), CuaSoLapPA)
        self.assertIs(w.ngan_lv.currentWidget(), w.khung_tab.stack_phu)
        w.mo_trang(ud.TRANG_DS)
        L['Lập phương án hộ…'].trigger()
        self.assertIsInstance(hien(), CuaSoLapPA)
        self.assertEqual(L['Lập phương án hộ…'].statusTip(), '')          # đã mở dự án: không nhắc "Mở hoặc tạo dự án…"


class TestMenuChuotPhai(_Co):
    def test_menu_va_nhan_ban(self):
        from pabt.man_hinh import CuaSoLapPA, the_cua
        con = csdl.mo(str(_du_an(self.td, 3)))
        c = CuaSoLapPA(con, 3)
        c.im_lang = True

        def don():
            c.bo_thay_doi()
            c.close()
            con.close()
        self.addCleanup(don)
        chu = lambda m: [a.text() for a in m.actions() if a.text()]    # noqa: E731
        m1 = chu(c.bang[1].menu_dong())
        for t in ('Thêm thửa vào mục 1…', 'Thêm tất cả thửa', 'Chọn nhiều thửa…', 'Nhân bản dòng', 'Xóa dòng', '▲ Lên', '▼ Xuống',
                  'Chép nội dung ô', 'Chọn mọi dòng (Ctrl+A)', 'Tra giá đất NQ 28…'):
            self.assertIn(t, m1)
        self.assertIn('Kiểm tra DT xây dựng…', chu(c.bang[2].menu_dong()))
        self.assertIn('Tính mật độ…', chu(c.bang[3].menu_dong()))
        n = len(c.bo.pa.dat)
        self.assertGreater(n, 0)
        c.tab.setCurrentIndex(the_cua(1))
        c.bang[1].bang.selectRow(0)
        j = c.nhan_ban_dong(1)
        self.assertEqual((j, len(c.bo.pa.dat)), (1, n + 1))
        self.assertEqual(c.bo.pa.dat[1].ma_thua, c.bo.pa.dat[0].ma_thua)
        self.assertIsNone(c.bo.pa.dat[1].id)
        m = c.bang[1].menu_dong()
        xoa = next(a for a in m.actions() if a.text().startswith('Xóa'))
        c.bang[1].bang.selectRow(1)
        xoa.trigger()
        self.assertEqual(len(c.bo.pa.dat), n)
        i = c.bo.them_hang_muc_khac(2, 'Mái che tạm')
        c.bang[2].ve(chon=i)
        self.assertEqual(c.nhan_ban_dong(2), i + 1)
        self.assertEqual(c.bo.pa.khoan[2][i + 1].ten, 'Mái che tạm')
        c.bang[2].bang.setCurrentCell(i, 1)
        self.assertEqual(c.bang[2].chep_o(), c.bang[2].bang.item(i, 1).text())


class TestBanIn(_Co):
    def _con(self):
        con = csdl.mo(str(_du_an(self.td, 2)))
        self.addCleanup(con.close)
        return con

    def test_chi_tiet_to_chuc_ngay_du_an(self):
        con = self._con()
        with con:
            con.execute("UPDATE ho SET ho_ten = 'UBND xã Phú Lý quản lý.' WHERE ma_ho = 1")
        ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, 1, self.td / 'tc.xlsx')).active
        chu = {c.coordinate: c.value for r in ws.iter_rows(max_row=16) for c in r if isinstance(c.value, str)}
        ngay = next(v for v in chu.values() if 'ngày' in v and 'tháng' in v)
        self.assertEqual(ngay, f'Trị An, ngày ...... tháng ..... năm {__import__("datetime").date.today().year}'
                         if '2026' not in ngay else 'Trị An, ngày ...... tháng ..... năm 2026')
        self.assertTrue(any(v.startswith('DỰ ÁN Thử') for v in chu.values()))
        self.assertFalse(any(v.startswith('Dự án:') for v in chu.values()))
        hang_cccd = next(int(''.join(filter(str.isdigit, k))) for k, v in chu.items() if v.strip().startswith('Số CCCD'))
        self.assertTrue(ws.row_dimensions[hang_cccd].hidden)                     # tổ chức: ẩn dòng CCCD
        self.assertTrue(any(v.strip() == 'Tổ chức:' for v in chu.values()))

    def test_ho_gia_dinh_giu_cccd_va_ngay_da_dien(self):
        con = self._con()
        with con:
            con.execute("UPDATE ho SET so_pa = '12', ngay_pa = '05/10/2026' WHERE ma_ho = 2")
        ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, 2, self.td / 'ho.xlsx')).active
        chu = {c.coordinate: c.value for r in ws.iter_rows(max_row=16) for c in r if isinstance(c.value, str)}
        self.assertIn('Trị An, ngày 05 tháng 10 năm 2026', chu.values())
        hang_cccd = next(int(''.join(filter(str.isdigit, k))) for k, v in chu.items() if v.strip().startswith('Số CCCD'))
        self.assertFalse(ws.row_dimensions[hang_cccd].hidden)

    def test_bang_tong_hop_ngay(self):
        con = self._con()
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx')).active
        ngay = [c.value for r in ws.iter_rows() for c in r if isinstance(c.value, str) and ', ngày' in c.value]
        self.assertTrue(ngay)
        self.assertTrue(all(v.startswith('Trị An, ngày') for v in ngay), ngay)

    def test_ham_doc_lap(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'], ws['A2'], ws['A3'] = '{ten_dia_ban}, ngày       tháng        năm {nam}', 'Dự án:  Đường A', 'Phú Lý, ngày 1 tháng 2 năm 2026'
        self.assertEqual(in_an.chuan_dong_ngay(ws), 2)
        self.assertEqual(ws['A1'].value, 'Trị An, ngày ...... tháng ..... năm {nam}')
        self.assertEqual(ws['A3'].value, 'Trị An, ngày 1 tháng 2 năm 2026')
        self.assertEqual(in_an.viet_hoa_du_an(ws), 1)
        self.assertEqual(ws['A2'].value, 'DỰ ÁN Đường A')


class TestXemTruocBangTongHop(CoSoXem):
    def test_xem_truoc_bth(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p)
        h.im_lang = True
        self.assertEqual(h.b_xem_bth.text(), 'Xem trước bảng tổng hợp')
        from PySide6.QtCore import Qt
        for r in range(h.bang_ho.rowCount()):
            h.bang_ho.item(r, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertIsNone(h.xem_truoc_bang_tong_hop())                      # chưa đánh dấu hộ nào
        for r in range(min(2, h.bang_ho.rowCount())):
            h.bang_ho.item(r, 0).setCheckState(Qt.CheckState.Checked)
        khoa = h.xem_truoc_bang_tong_hop(ngay=True)
        self.assertEqual(khoa[0], 'bth')
        self.assertEqual(list(khoa[1]), h.ds_ho())
        self.assertTrue(h.w_preview.cho_xong(30))
        ws = openpyxl.load_workbook(self.excel.da_nhan[-1]).active
        self.assertEqual(ws.title, in_an.TEN_BTH)
        h.reject()


class TestDuoiGoiCapNhat(unittest.TestCase):
    def test_larcud_va_van_nhan_pabtcn(self):
        from pabt import cap_nhat
        self.assertEqual(cap_nhat.DUOI, '.larcud')
        self.assertIn('.pabtcn', cap_nhat.DUOI_NHAN)
        goc = Path(__file__).resolve().parents[1]
        self.assertIn("'.larcud'", (goc / 'chay.py').read_text(encoding='utf-8'))
        ps = (goc / 'bo_cai_win' / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('Classes\.larcud', ps)
        self.assertIn('Classes\.pabtcn', ps)                               # máy cài bản cũ: gói .pabtcn cũ vẫn bấm đúp được


class TestLeTheBangTongHop(_Co):
    def test_le_the(self):
        from pabt import man_hinh_theo_doi as mt
        k = mt.KhungBangTongHop()
        for w in k.cac_the:
            m = w.layout().contentsMargins()
            self.assertEqual((m.left(), m.right()), (mt.LE_THE, mt.LE_THE))
        k.deleteLater()


del tempfile

if __name__ == '__main__':
    unittest.main()
