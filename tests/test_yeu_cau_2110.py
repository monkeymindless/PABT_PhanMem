"""Yêu cầu người dùng 21/10/2026 (kèm ảnh mẫu): bôi đen vùng ô kiểu Excel trên mọi bảng (chọn 1 ô của 3 hộ = 3 hộ), bộ đếm Trung
bình / Tổng số đếm / Tổng (thanh trạng thái cửa sổ chính, hộp thoại), thẻ KPI có số thửa + diện tích, huy hiệu Lọc, dải cộng, hộp
Thống kê Hộ · Thửa · Diện tích (Ctrl+Shift+T). Số liệu GIẢ LẬP."""
from __future__ import annotations

import unittest
from decimal import Decimal

from tests.test_giao_dien_navy import CoNavy


def _chon_o(bang, o: list, them: bool = False):
    """Chọn các ô [(dòng, cột)] (giữ vùng chọn cũ nếu them)."""
    from PySide6.QtCore import QItemSelectionModel
    sm, m = bang.selectionModel(), bang.model()
    F = QItemSelectionModel.SelectionFlag
    if not them:
        sm.clearSelection()
    for r, c in o:
        sm.select(m.index(r, c), F.Select)


class TestHamThuan(unittest.TestCase):
    def test_doc_so_o_va_cot_dinh_danh(self):
        from pabt.giao_dien import chu_thong_ke, doc_so_o, so_bo_dem
        self.assertEqual(doc_so_o('1.480.500 đ'), (Decimal('1480500'), 0))
        self.assertEqual(doc_so_o('28.450,2 m²')[0], Decimal('28450.2'))
        self.assertEqual(doc_so_o('2,85 ha')[0], Decimal('2.85'))
        self.assertEqual(doc_so_o('34 hộ')[0], 34)
        self.assertEqual(doc_so_o('19,9%')[0], Decimal('19.9'))
        self.assertEqual(doc_so_o('-'), (Decimal(0), 0))
        for chu in ('12/45', 'Nguyễn Văn A', '■■□□  Đã lập PA', '05/03/2026', 'Đợt 1'):
            self.assertIsNone(doc_so_o(chu), chu)
        self.assertEqual(so_bo_dem(Decimal('1128.0'), 1), '1.128,0')       # dữ liệu có số lẻ: giữ số lẻ như ảnh mẫu
        self.assertEqual(so_bo_dem(Decimal('7') / 2, 0), '3,5')
        self.assertEqual(chu_thong_ke(dict(so_dem=1, so_so=1, tong=Decimal(5), trung_binh=Decimal(5), so_le=0)), '')
        self.assertEqual(chu_thong_ke(dict(so_dem=3, so_so=0, tong=Decimal(0), trung_binh=None, so_le=0)), 'Tổng số đếm: 3')

    def test_bang_thong_ke_decimal(self):
        from pabt import man_hinh_thong_ke as tk
        dong = [dict(ma_ho=1, dt=Decimal('0.1'), tong=Decimal(100), so_thua=2, da_phe_duyet=1, dot_id=7),
                dict(ma_ho=2, dt=Decimal('0.2'), tong=Decimal(0), so_thua=1, da_ban_giao=1),
                dict(ma_ho=3, dt=Decimal('0.3'), tong=Decimal(50), o=[3, 'x', 'y', 4, 0, '', ''])]
        tt = tk.thong_ke_trang_thai(dong, {1: 'da_lap', 3: 'tu_lap'})
        self.assertEqual(len(tt), 7)
        self.assertEqual(tt[0][1], dict(so_ho=3, so_thua=7, dt=Decimal('0.6'), tong=Decimal(150)))
        self.assertEqual(tt[1][1]['so_ho'], 1)                          # tự lập chưa soát = chưa lập
        self.assertEqual(tt[2][1]['so_ho'], 2)
        self.assertEqual(tt[6][1]['so_thua'], 6)                       # chưa bàn giao: hộ 1 + hộ 3
        dot = tk.thong_ke_dot(dong, {7: 'Đợt 1'})
        self.assertEqual([x[0] for x in dot], ['Đợt 1', tk.CHUA_XEP_DOT])
        self.assertEqual(dot[1][1]['so_ho'], 2)
        self.assertEqual(dot[1][2]['so_ho'], 1)
        self.assertEqual(tk.ty_le(34, 171), '19,9%')
        self.assertEqual(tk.ty_le(0, 0), '0,0%')


class TestChonVungVaBoDem(CoNavy):
    def _cua_so_dt(self):
        """Dự án 3 hộ, DT thu hồi từng hộ 215,1 / 459,4 / 143,8 m²."""
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        p = _du_an(self.td, 3)
        from pabt import csdl
        con = csdl.mo(p)
        with con:
            ho = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
            for m, dt in zip(ho, ('215.1', '459.4', '143.8')):
                thua = [r[0] for r in con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ? ORDER BY ma_thua', (m,))]
                con.execute("UPDATE thua SET dt_thu_hoi = '0' WHERE ma_ho = ?", (m,))
                con.execute('UPDATE thua SET dt_thu_hoi = ? WHERE ma_thua = ?', (dt, thua[0]))
        con.close()
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.w.show()
        self.w.mo(str(p))
        self.app.processEvents()
        return ud, self.w

    def test_moi_bang_chon_tung_o(self):
        from PySide6.QtWidgets import QAbstractItemView as V
        from pabt.bang_ao import BangAo
        ud, w = self._cua_so_dt()
        bang = [w.bang, BangAo(['A', 'B'])]
        w.mo_trang(ud.TRANG_DU_TOAN)
        self.app.processEvents()
        bang.append(w.khung_du_toan.bang)
        hop = w.mo_lap_pa(w.mo_hinh.dong[0]['ma_ho'], cho=False)
        bang.append(hop.bang[1].bang)                                    # bảng của BangMuc mục 1 (đất)
        for b in bang:
            self.assertEqual(b.selectionBehavior(), V.SelectionBehavior.SelectItems, b)
            self.assertEqual(b.selectionMode(), V.SelectionMode.ExtendedSelection, b)
        hop.bo_thay_doi()
        hop.close()

    def test_bo_dem_3_o(self):
        _ud, w = self._cua_so_dt()
        w.mo_trang(0)
        dong = {}
        for r in range(w.loc.rowCount()):
            dong[w.loc.index(r, 4).data()] = r
        self.assertEqual(set(dong), {'215,1', '459,4', '143,8'})
        _chon_o(w.bang, [(r, 4) for r in dong.values()])
        from pabt.giao_dien import thong_ke_vung_chon
        tk = thong_ke_vung_chon(w.bang)
        self.assertEqual(tk['so_dem'], 3)
        self.assertEqual(tk['tong'], Decimal('818.3'))
        self.assertEqual(tk['trung_binh'], Decimal('818.3') / 3)
        chu = 'Trung bình: 272,8     Tổng số đếm: 3     Tổng: 818,3'
        self.assertEqual(tk['chuoi'], chu)
        self.assertEqual(w.lb_bo_dem_excel.text(), chu)
        self.assertTrue(w.lb_bo_dem_excel.isVisibleTo(w))
        self.assertEqual(w.lb_bo_dem_excel.objectName(), 'lb_bo_dem_excel')
        sb = w.statusBar()                                              # ngay trái cụm A− / A+
        self.assertLess(w.lb_bo_dem_excel.mapTo(sb, w.lb_bo_dem_excel.rect().topLeft()).x(),
                        w.nut_ty_le['nho'].mapTo(sb, w.nut_ty_le['nho'].rect().topLeft()).x())
        self.assertEqual(w.lb_bo_dem_excel.sao_chep_tong(), '818,3')       # bấm = chép Tổng
        from PySide6.QtWidgets import QApplication
        self.assertEqual(QApplication.clipboard().text(), '818,3')
        # thêm ô STT (định danh: đếm, không cộng) và ô họ tên (chữ)
        _chon_o(w.bang, [(0, 0), (0, 1)], them=True)
        tk = thong_ke_vung_chon(w.bang)
        self.assertEqual((tk['so_dem'], tk['so_so'], tk['tong']), (5, 3, Decimal('818.3')))
        # chỉ chữ
        _chon_o(w.bang, [(0, 1), (1, 1)])
        self.assertEqual(w.lb_bo_dem_excel.text(), 'Tổng số đếm: 2')
        w.bang.selectionModel().clearSelection()
        self.assertFalse(w.lb_bo_dem_excel.isVisibleTo(w))

    def test_chon_mot_o_moi_ho_ra_dung_ho(self):
        from pabt.bang_ao import BangAo
        _ud, w = self._cua_so_dt()
        w.mo_trang(0)
        _chon_o(w.bang, [(0, 1), (2, 1)])                                 # 1 ô cột Họ tên của 2 hộ
        ma = sorted(w.mo_hinh.dong[w.loc.mapToSource(w.loc.index(r, 0)).row()]['ma_ho'] for r in (0, 2))
        self.assertEqual(w.ho_da_chon(), ma)
        self.assertTrue(w.lenh['Xóa hộ…'].isEnabled())
        self.assertIn('Đang chọn: 2 hộ', w.lb_tom_tat.text())
        b = BangAo(['STT', 'Họ và tên', 'DT'])
        b.dat_du_lieu([['1', 'A', '1'], ['2', 'B', '2'], ['3', 'C', '3']], ['h1', 'h2', 'h3'])
        _chon_o(b, [(0, 1), (2, 1)])
        self.assertEqual(b.ma_da_chon(), ['h1', 'h3'])
        # bấm ô STT: chọn cả dòng
        from pabt.giao_dien import cac_dong_da_chon, gan_bo_dem
        gan_bo_dem(b)
        bo = next(x for x in b.children() if type(x).__name__ == '_BoChonVung')
        b.selectionModel().clearSelection()
        bo.bam(b.model().index(1, 0))
        self.assertEqual(len(b.selectionModel().selectedIndexes()), 3)
        self.assertEqual(cac_dong_da_chon(b), [1])

    def test_the_kpi_dia_chinh_va_dai_cong(self):
        from pabt.tien import vn
        ud, w = self._cua_so_dt()
        ds = w.mo_hinh.dong
        self.assertEqual(w.the_so['so_ho'].text(), '3')                   # vẫn CHỈ là số
        n_thua = sum(d['so_thua'] for d in ds)
        self.assertEqual(n_thua, 6)                                      # hộ 1, 2, 3 có 1, 2, 3 thửa
        dc = w.the_dia_chinh['so_ho'].text()
        self.assertEqual(dc, '6 thửa')                               # 1.0.44: sổ địa chính 2 dòng, không ghép "/"
        self.assertEqual(w.the_dt['so_ho'].text(), '818,3 m²')
        self.assertNotIn('/', dc)
        self.assertNotIn('<br', dc.lower())
        self.assertNotIn('/', w.the_dt['so_ho'].text())
        self.assertEqual(w.the_don_vi['so_ho'].text(), 'hộ')
        self.assertEqual(w.the_phu['so_ho'].text(), '100%')
        self.assertEqual(w.the_phu['tong'].text(), '0,0818 ha')            # thẻ Tổng kinh phí: tổng ha
        self.assertEqual(w.the_khung['so_ho'].height(), w.CAO_THE_SO)
        self.assertIn('0 thửa', w.the_dia_chinh['da_pd'].text())
        khung, o_thua, o_dt = w.the_khung['so_ho'], w.the_dia_chinh['so_ho'], w.the_dt['so_ho']
        self.assertGreater(o_thua.height(), 8)
        self.assertGreater(o_dt.height(), 8)
        day_thua = o_thua.mapTo(khung, o_thua.rect().bottomLeft()).y()
        dinh_dt = o_dt.mapTo(khung, o_dt.rect().topLeft()).y()
        day_dt = o_dt.mapTo(khung, o_dt.rect().bottomLeft()).y()
        self.assertLessEqual(day_thua, dinh_dt)                           # diện tích nằm dưới số thửa
        self.assertLessEqual(day_dt, khung.height() - 6)                  # trên bo góc 6 px, không nới chiều cao thẻ
        chu = w.dai_cong_ds.chu
        self.assertEqual(chu['so_ho'][0], 'CỘNG (3 HỘ · 6 THỬA)')
        self.assertEqual(chu['dt'][0], 'Tổng DT: 818,3 m² (0,0818 ha)')
        self.assertTrue(chu['dat'][0].startswith('Đất: '))
        self.assertTrue(chu['ho_tro'][0].startswith('HT & Thưởng: '))
        self.assertIn('Lọc: <b style="color:#1E3A5F">3</b>/3 hộ · <b style="color:#1E3A5F">6</b> thửa', w.lb_loc.text())
        self.assertIn(f'Dự án: 3 hộ · 6 thửa · {vn(Decimal("818.3"), 1)} m²', w.lb_tom_tat.text())

    def test_hop_thong_ke(self):
        ud, w = self._cua_so_dt()
        a = w.lenh[ud.LENH_THONG_KE]
        self.assertIn(ud.LENH_THONG_KE, ud.LENH_CAN_DU_AN)
        self.assertEqual(a.shortcut().toString(), 'Ctrl+Shift+T')
        self.assertIn(a, w.menu_tren['Dữ liệu'].actions())
        hop = w.thong_ke_dia_chinh(cho=False)
        self.addCleanup(hop.close)
        self.assertEqual(hop.bang_tt.rowCount(), 7)
        self.assertEqual(hop.bang_tt.item(0, 1).text(), '3')
        self.assertEqual(hop.bang_tt.item(0, 3).text(), '6')
        self.assertEqual(hop.bang_tt.item(0, 5).text(), '818,3')
        self.assertEqual(hop.bang_dot.item(0, 0).text(), 'Chưa xếp đợt trình')
        self.assertEqual(hop.bang_dot.item(0, 1).text(), '3 hộ')
        # bôi đen trong hộp: bộ đếm của hộp (góc dưới trái)
        _chon_o(hop.bang_tt, [(0, 5), (1, 5)])
        self.assertTrue(hop.lb_bo_dem_excel.text().startswith('Trung bình: '))
        self.assertIn('Tổng số đếm: 2', hop.lb_bo_dem_excel.text())
        tt = hop.sao_chep_tom_tat()
        self.assertIn('3 hộ', tt)
        self.assertIn('1. Tổng quy mô toàn dự án', tt)
        # huy hiệu Lọc gọi lại QAction của lệnh (không gọi thẳng hàm): thay hàm để khỏi mở hộp (exec chặn kiểm thử)
        goi = []
        w.thong_ke_dia_chinh = lambda cho=True: goi.append(1)
        w.lb_loc.bam()
        self.assertEqual(goi, [1])

    def test_hop_thoai_roi_co_nhan_dem_noi(self):
        from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout
        from pabt.giao_dien import cho_phep_sao_chep_bang
        d = QDialog()
        self.addCleanup(d.close)
        b = QTableWidget(2, 2)
        b.setHorizontalHeaderLabels(['Tên', 'Thành tiền'])
        for r, (t, v) in enumerate((('A', '1.000'), ('B', '2.500'))):
            b.setItem(r, 0, QTableWidgetItem(t))
            b.setItem(r, 1, QTableWidgetItem(v))
        QVBoxLayout(d).addWidget(b)
        cho_phep_sao_chep_bang(b)
        d.show()
        _chon_o(b, [(0, 1), (1, 1)])
        from pabt.giao_dien import NhanBoDem
        n = b.findChild(NhanBoDem)
        self.assertIsNotNone(n)
        self.assertEqual(n.text(), 'Trung bình: 1.750     Tổng số đếm: 2     Tổng: 3.500')


if __name__ == '__main__':
    unittest.main()
