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
                  'Sao chép cả dòng\tCtrl+Shift+C', 'Chọn mọi dòng (Ctrl+A)', 'Tra giá đất NQ 28…'):
            self.assertIn(t, m1)
        self.assertTrue(m1[0].startswith('Sao chép'))            # 1.0.04: sao chép ô / dòng đứng đầu menu
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
        self.assertIn(r'Classes\.larcud', ps)
        self.assertIn(r'Classes\.pabtcn', ps)                             # máy cài bản cũ: gói .pabtcn cũ vẫn bấm đúp được


class TestLeTheBangTongHop(_Co):
    def test_le_the(self):
        from pabt import man_hinh_theo_doi as mt
        k = mt.KhungBangTongHop()
        for w in k.cac_the:
            m = w.layout().contentsMargins()
            self.assertEqual((m.left(), m.right()), (mt.LE_THE, mt.LE_THE))
        k.deleteLater()


class TestHangNutLapPhuongAn(_Co):
    def test_chu_nut_va_ten_ho(self):
        from pabt.man_hinh import CuaSoLapPA
        con = csdl.mo(str(_du_an(self.td, 2)))
        dai = 'Khu Bảo tồn Thiên nhiên - Văn hóa Đồng Nai, đất do UBND xã Phú Lý quản lý.'
        with con:
            con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = 1', (dai,))
        c = CuaSoLapPA(con, 1)
        c.im_lang = True

        def don():
            c.bo_thay_doi()
            c.close()
            con.close()
        self.addCleanup(don)
        self.assertFalse(hasattr(c, 'b_goi_y'))                            # bỏ nút "Gợi ý hỗ trợ…"
        self.assertEqual((c.b_dan.text(), c.btn_toggle_preview.text()), ('Dán tài sản', 'Xem trước'))
        self.assertTrue(c.cb_ho.currentText().endswith(dai))
        self.assertEqual(c.cb_ho.lineEdit().cursorPosition(), 0)            # chữ hiện từ đầu tên
        self.assertEqual(c.cb_ho.toolTip(), c.cb_ho.currentText())


class TestToiUuKiemToan(_Co):
    """Đợt kiểm toán 16/10/2026: tối ưu phải cho kết quả như cũ."""

    def test_tong_hop_loc_sql_giong_loc_sau(self):
        from pabt import theo_doi
        con = csdl.mo(str(_du_an(self.td, 12)))
        self.addCleanup(con.close)
        ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        qd = theo_doi.luu_qd(con, None, '7/QĐ-THU', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, ds[2:5])
        tat_ca = {x.ma_ho: x for x in theo_doi.tong_hop(con, tinh_pa=False)}
        chon = [ds[3], ds[0], ds[7]]
        mot_phan = theo_doi.tong_hop(con, chon, tinh_pa=False)
        self.assertEqual([x.ma_ho for x in mot_phan], [m for m in ds if m in chon])        # thứ tự hộ như cũ
        for x in mot_phan:
            y = tat_ca[x.ma_ho]
            self.assertEqual((x.thua, x.qd, x.da_lap, x.da_ban_giao), (y.thua, y.qd, y.da_lap, y.da_ban_giao))
        self.assertEqual(theo_doi.tong_hop(con, [], tinh_pa=False), [])
        dai = list(range(1, theo_doi.LOC_SQL_TOI_DA + 10))                                 # danh sách dài: đọc cả bảng như cũ
        self.assertEqual(len(theo_doi.tong_hop(con, dai, tinh_pa=False)), len(ds))

    def test_he_so_k_ghi_xong_doc_ngay(self):
        from pabt import he_so_k
        truoc = he_so_k.tat_ca()
        he_so_k.ghi([dict(dia_ban='Xã Thử', loai_dat='ONT', vi_tri='VT1', he_so='1,5')])
        self.addCleanup(he_so_k.xoa)
        self.assertEqual(len(he_so_k.tat_ca()), 1)                      # không chờ hết NHO_GIAY
        he_so_k.xoa()
        self.assertEqual(len(he_so_k.tat_ca()), len(truoc))

    def test_bo_soan_boi_canh_chung(self):
        from pabt.lap_pa import BoSoan
        from pabt.nghiep_vu import BoiCanh
        con = csdl.mo(str(_du_an(self.td, 3)))
        self.addCleanup(con.close)
        bc = BoiCanh.tu(con)
        a, b = BoSoan(con, 1, None, bc), BoSoan(con, 1)
        self.assertIs(a.bc, bc)
        self.assertEqual(a.ket_qua.tong, b.ket_qua.tong)


del tempfile

if __name__ == '__main__':
    unittest.main()
