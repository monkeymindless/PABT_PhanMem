"""1.0.04 (người dùng 19/10/2026, 7 nhóm): bỏ che CCCD; bản in chi tiết (tổ chức, nguồn gốc mỗi đoạn một dòng, mục 1 diện tích khi
đơn giá 0); bảng tổng hợp (dự thảo, ẩn cột vị trí, căn lề, hộ nhiều thửa, số 0 "-"); kiểm lỗi tài sản trên đất của tổ chức / hộ khác;
Thông tin dự án + dòng 85% / 15%; sao chép ô / dòng trên mọi bảng; thẻ hồ sơ hộ, bảng dữ liệu thô; Tiếp nhận & kiểm tra pháp lý
(máy trắng). Số liệu GIẢ LẬP."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import openpyxl

from pabt import du_lieu_in
from pabt import csdl, in_an, kiem_loi, tiep_nhan_phap_ly as tn
from pabt.tien import D
from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class _Co(CoSo):
    def tearDown(self):
        self.doCleanups()
        super().tearDown()

    def _con(self, so_ho=3):
        con = csdl.mo(str(_du_an(self.td, so_ho)))
        self.addCleanup(con.close)
        return con


def _chu(f) -> str:
    return ' | '.join(str(c.value) for r in openpyxl.load_workbook(f).active.iter_rows() for c in r if c.value is not None)


# ---------------------------------------------------------------- nhóm 1
class TestNhom1(_Co):


    def test_muc_1_dien_tich_khi_don_gia_0(self):
        con = self._con()
        with con:
            con.execute("UPDATE ct_dat SET gia_bang_gia = '0' WHERE ma_ho = 1")
        dong, _ = du_lieu_in.dong_chi_tiet(con, 1)
        dat = [x for x in dong[1:] if x[0] == 'I' and x[1][0].startswith('1.')]
        self.assertTrue(dat)
        for _, gt, *_ in dat:
            self.assertEqual(gt[2], 'm²')
            self.assertGreater(gt[3], 0)
            self.assertIsNone(gt[4])
            self.assertIsNone(gt[5])
            self.assertEqual(gt[6], 0)
            self.assertNotIn('Vị trí', gt[1])
        # tài sản trên đất người khác: diện tích 0 -> trống ĐVT, số lượng
        with con:
            con.execute("UPDATE ct_dat SET dien_tich = '0' WHERE ma_ho = 1")
            con.execute("UPDATE thua SET dt_thu_hoi = '0' WHERE ma_ho = 1")
        dong, _ = du_lieu_in.dong_chi_tiet(con, 1)
        gt = next(x[1] for x in dong[1:] if x[0] == 'I')
        self.assertEqual((gt[2], gt[3], gt[6]), (None, None, 0))

    def test_dien_tich_dong_dat_lay_theo_thua(self):
        self.assertEqual(du_lieu_in.dien_tich_dong_dat(D(0), {'dt_thu_hoi': '21243'}), D('21243'))
        self.assertEqual(du_lieu_in.dien_tich_dong_dat(D(5), {'dt_thu_hoi': '9'}), D(5))
        self.assertEqual(du_lieu_in.dien_tich_dong_dat(D(0), {'dt_boi_thuong': '7', 'dt_thu_hoi': '9'}), D(7))


# ---------------------------------------------------------------- nhóm 2
class TestNhom2(_Co):
    def test_bang_tong_hop_du_thao_cot_va_can_le(self):
        con = self._con(4)
        f = in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx', du_thao=True)
        ws = openpyxl.load_workbook(f).active
        self.assertEqual(str(ws['A3'].value or '').strip(), in_an.DAU_DU_THAO)                  # dưới tên đơn vị
        r7 = next(r for r in range(1, 12) if 'Đính kèm' in str(ws.cell(r, 1).value or ''))
        self.assertTrue(ws.row_dimensions[r7].hidden)
        self.assertTrue(ws.column_dimensions['N'].hidden)                                         # cột 11 Vị trí đất
        for c in 'PQRSTUV':
            self.assertGreaterEqual(float(ws.column_dimensions[c].width), in_an.RONG_COT_KHONG_BTH)    # cột toàn 0 cố ý thu theo tiêu đề (thu_cot_khong_bth)
        d0 = in_an.DONG_DAU_BTH
        self.assertEqual(ws.cell(d0, 23).alignment.horizontal, 'justify')
        for c in (2, 3, 24, 25):
            self.assertEqual(ws.cell(d0, c).alignment.horizontal, 'center')
        # hộ nhiều thửa (22/10/2026): STT / họ tên / địa chỉ một ô gộp dọc cho cả hộ, không lặp từng dòng
        gop = [m for m in ws.merged_cells.ranges if m.min_col == 1 and m.max_col == 1 and m.min_row >= d0 and m.max_row > m.min_row]
        self.assertTrue(gop)
        for m in gop:
            for c in (2, 3):
                self.assertTrue(any(x.min_col == x.max_col == c and x.min_row == m.min_row and x.max_row == m.max_row
                                    for x in ws.merged_cells.ranges))
        self.assertIn('"-"', ws.cell(d0, 16).number_format + ws.cell(d0, 8).number_format)

    def test_ham_phu(self):
        self.assertEqual(in_an.rut_gon_don_vi('Trung tâm Phát triển quỹ đất tỉnh Mẫu - Chi nhánh Thử'), 'TTPTQĐ Chi nhánh Thử')
        self.assertEqual(in_an.rut_gon_don_vi('Ban Bồi thường'), 'Ban Bồi thường')
        self.assertEqual(in_an.dinh_dang_so_gach('#,##0'), '#,##0;-#,##0;"-"')
        self.assertEqual(in_an.dinh_dang_so_khong('#,##0;-#,##0;"-"'), '#,##0;-#,##0;0')
        chu = 'Thửa 16: đất khai phá năm 1990.\nThửa 17: nhận chuyển nhượng năm 2005.'
        self.assertEqual(in_an.nguon_goc_cua_thua(chu, '16'), 'Thửa 16: đất khai phá năm 1990.')
        self.assertEqual(in_an.nguon_goc_cua_thua(chu, '17'), 'Thửa 17: nhận chuyển nhượng năm 2005.')
        self.assertEqual(in_an.tach_nguon_goc_theo_thua([(chu, '16', '1'), (chu, '17', '1')]),
                         ['Thửa 16: đất khai phá năm 1990.', 'Thửa 17: nhận chuyển nhượng năm 2005.'])
        self.assertIsNone(in_an.tach_nguon_goc_theo_thua([('Chung', '1', '1'), ('Chung', '2', '1')]))


# ---------------------------------------------------------------- nhóm 3
class TestNhom3(_Co):
    def test_ham_quy_tac(self):
        ds = {('39', '17'): [dict(ma_thua=1, ma_ho=1, so_to='39', so_thua='17', dt_thu_hoi='21243')]}
        t = dict(ma_thua=2, ma_ho=2, so_to='39', so_thua='17', dt_thu_hoi='0', nguon_goc='')
        self.assertTrue(kiem_loi.la_ho_tai_san_tren_dat({'ho_ten': 'Nguyễn Văn A'}, t, None, ds))     # (a)
        t2 = dict(t, so_to='1', so_thua='2')
        self.assertFalse(kiem_loi.la_ho_tai_san_tren_dat({'ho_ten': 'Nguyễn Văn A'}, t2, None, ds))
        self.assertTrue(kiem_loi.la_ho_tai_san_tren_dat({'ho_ten': 'B', 'phap_ly': 'Đất do UBND xã quản lý'}, t2, None, ds))  # (c)
        self.assertTrue(kiem_loi.la_quan_he_chu_dat_va_tai_san([dict(dt_thu_hoi='5', tien_dat=True), dict(dt_thu_hoi='0')]))
        self.assertFalse(kiem_loi.la_quan_he_chu_dat_va_tai_san([dict(dt_thu_hoi='5'), dict(dt_thu_hoi='3')]))

    def test_kiem_tra_khong_bao_loi_ho_tai_san(self):
        con = self._con(3)
        t = con.execute('SELECT so_to, so_thua FROM thua WHERE ma_ho = 1 ORDER BY ma_thua LIMIT 1').fetchone()
        with con:
            con.execute("INSERT INTO thua (ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, thu_tu) VALUES (2, ?, ?, 'CLN', '0', 9)",
                        (t['so_to'], t['so_thua']))
        nd = [x.noi_dung for x in kiem_loi.kiem_tra(con)]
        self.assertFalse(any('diện tích thu hồi bằng 0' in x for x in nd), nd)
        self.assertFalse(any('cũng có ở hộ khác' in x for x in nd))
        # hai hồ sơ cùng khai DT thu hồi > 0 trên một thửa: vẫn cảnh báo
        with con:
            con.execute("UPDATE thua SET dt_thu_hoi = '30' WHERE ma_ho = 2 AND thu_tu = 9")
        self.assertTrue(any('cũng có ở hộ khác' in x.noi_dung for x in kiem_loi.kiem_tra(con)))


# ---------------------------------------------------------------- nhóm 4
class TestNhom4(_Co):
    def test_dong_phan_bo_85_15(self):
        from pabt import kinh_phi_du_an
        con = self._con(3)
        cc = kinh_phi_du_an.co_cau(con)
        pb = [d for d in cc['dong'] if d['loai'] == 'phan_bo']
        kp = next(d for d in cc['dong'] if d['loai'] == 'kinh_phi')
        self.assertEqual(len(pb), 2)
        self.assertIn('85%', pb[0]['ten'])
        self.assertIn('15%', pb[1]['ten'])
        self.assertTrue(pb[0]['ten'].startswith('  - Tổ chức làm nhiệm vụ bồi thường'))
        self.assertTrue(pb[1]['ten'].startswith('  - Cơ quan phối hợp thực hiện'))
        self.assertGreater(pb[0]['tien_pa'], pb[1]['tien_pa'])
        for k in ('tien_pa', 'tien_pd', 'chua_pd'):
            self.assertIsNotNone(pb[0][k])
            self.assertLessEqual(abs(pb[0][k] + pb[1][k] - kp[k]), 1000)

    def test_hop_du_an_khong_bo_hep_co_khung_phap_ly(self):
        from pabt.man_hinh import HopDuAn
        con = self._con(3)
        h = HopDuAn(con)
        self.addCleanup(h.close)
        self.assertIn('3 hộ', h.lb_pl['quy_mo'].text())
        self.assertIn('Chưa tiếp nhận', h.lb_pl['trang_thai'].text())
        self.assertEqual(h.b_phap_ly.text(), 'Kiểm tra && Tiếp nhận hồ sơ pháp lý đầu vào…')
        d = h.mo_tiep_nhan(cho=False)
        self.addCleanup(d.close)
        self.assertIs(d.con, con)


# ---------------------------------------------------------------- nhóm 5
class TestNhom5SaoChep(_Co):
    def _bang(self):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        b = QTableWidget(3, 3)
        for r in range(3):
            for c in range(3):
                b.setItem(r, c, QTableWidgetItem(f'{r}{c}'))
        from pabt import giao_dien
        giao_dien.cho_phep_sao_chep_bang(b)
        self.addCleanup(b.deleteLater)
        return b

    def test_mot_o_nhieu_o_ca_dong(self):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtWidgets import QApplication, QMenu
        from pabt import giao_dien
        b = self._bang()
        b.setCurrentCell(1, 2)
        self.assertEqual(giao_dien.chu_sao_chep_bang(b), '12')
        QApplication.sendEvent(b, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier, 'c'))
        self.assertEqual(QApplication.clipboard().text(), '12')
        QApplication.sendEvent(b, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_C,
                                            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier, 'C'))
        self.assertEqual(QApplication.clipboard().text(), '10\t11\t12')
        from PySide6.QtWidgets import QTableWidgetSelectionRange
        b.clearSelection()
        b.setRangeSelected(QTableWidgetSelectionRange(0, 0, 1, 1), True)
        self.assertEqual(giao_dien.chu_sao_chep_bang(b), '00\t01\n10\t11')
        m = QMenu()
        m.addAction('Lệnh cũ')
        giao_dien.them_muc_sao_chep(m, b)
        chu = [a.text() for a in m.actions() if a.text()]
        self.assertTrue(chu[0].startswith('Sao chép'))
        self.assertTrue(chu[1].startswith('Sao chép cả dòng'))
        self.assertEqual(chu[-1], 'Lệnh cũ')
        self.assertEqual(b.contextMenuPolicy(), Qt.ContextMenuPolicy.CustomContextMenu)

    def test_moi_bang_cua_so_hien_deu_gan(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.mo(str(_du_an(self.td, 3)))
        from pabt import giao_dien
        giao_dien.ap_kieu_cay(w)
        self.assertTrue(w.bang.property('_co_sao_chep'))


# ---------------------------------------------------------------- nhóm 6
class TestNhom6(_Co):
    def test_khung_ho_so_to_chuc_va_loai_dat(self):
        from pabt.man_hinh_ho_so import KhungHoSo
        con = self._con(3)
        k = KhungHoSo(con, 3)
        self.addCleanup(k.deleteLater)
        self.assertEqual(k.nhan_o['ho_ten'].text(), 'Họ và tên:')
        k.o['ho_ten'].setText('UBND xã Mẫu')
        self.assertEqual(k.nhan_o['ho_ten'].text(), 'Tổ chức:')
        self.assertEqual(k.nhan_o['dia_chi'].text(), 'Địa chỉ:')
        self.assertTrue(k.o['so_cccd'].isHidden())
        loai = k.dt_theo_loai()
        self.assertGreaterEqual(len(loai), 2)
        self.assertEqual(sum(loai.values(), D(0)), k.tom_tat_thua()[2])
        self.assertIn('m²', k.lb_tom_tat_thua.text())

    def test_hop_nguon_goc_chen_mau(self):
        from pabt.man_hinh_ho_so import MAU_CAU_NGUON_GOC, HopNguonGoc
        d = HopNguonGoc(None, 'Đất khai phá.')
        self.addCleanup(d.deleteLater)
        self.assertEqual(d.cb_mau.count(), len(MAU_CAU_NGUON_GOC) + 1)
        d.o.moveCursor(d.o.textCursor().MoveOperation.End)
        d.chen_mau(MAU_CAU_NGUON_GOC[-1][1])
        self.assertIn('Không tranh chấp', d.chu())
        self.assertIn('\n- Không tranh chấp', d.o.toPlainText())

    def test_du_an_moi_to_dong_loi_va_loc(self):
        from pabt.man_hinh_du_an_moi import HopDuAnMoi
        h = HopDuAnMoi(None, luu_cai_dat=False)
        h.im_lang = True
        self.addCleanup(h.deleteLater)
        h.dat_dong([dict(ho_ten='Nguyễn Văn A', so_to='1', so_thua='2', loai_dat='ONT', dt_thu_hoi='50'),
                    dict(ho_ten='Trần B', so_to='', so_thua='3', loai_dat='XYZ', dt_thu_hoi='20')])
        self.assertEqual(h.loi_dong_tho(0), [])
        self.assertEqual(len(h.loi_dong_tho(1)), 2)
        self.assertEqual(h.kiem_tra_bang_tho(), 1)
        self.assertIn('1 dòng', h.lb_kiem_tho.text())
        from pabt.giao_dien import loc_dong_bang
        self.assertEqual(loc_dong_bang(h.bang_tho, 'tran'), 1)
        self.assertTrue(h.bang_tho.isRowHidden(0))
        h.dien_san(dict(ten='Dự án thử', dia_ban='Xã Mẫu', chu_dau_tu='Ban Thử'))
        self.assertEqual((h.o['ten'].text(), h.o['ten_dia_ban'].text(), h.o['cap_dia_ban'].currentText()),
                         ('Dự án thử', 'Mẫu', 'Xã'))


# ---------------------------------------------------------------- nhóm 7
class TestNhom7TiepNhan(_Co):
    def test_nghiep_vu(self):
        from datetime import date
        d = tn.moi()
        self.assertEqual(len(tn.MUC_HO_SO), 32)
        self.assertEqual(sum(len(ds) for _, ds in tn.NHOM_HO_SO), 32)
        self.assertEqual(len(tn.NHOM_HO_SO), 5)
        self.assertEqual(len(tn.KY_THUAT), 10)
        self.assertFalse(any(d['du_an'].values()))                         # máy trắng: không điền sẵn gì
        d['can_cu'] = ['d79']
        d['du_an']['ngay_nq_hdnd'] = '01/01/2024'
        th = tn.tong_hop(d, date(2026, 10, 19))
        self.assertFalse(th['du_dieu_kien_tu_dong'])
        self.assertTrue(any('quá 02 năm' in x for x in th['can_bo_sung']))
        self.assertFalse(th['dung_tien_do_tu_dong'])
        for m in tn.MUC_HO_SO:
            if tn.ap_dung(m, d):
                d['ho_so'][m[0]] = True
        d['du_an']['ngay_nq_hdnd'] = '01/06/2026'
        th = tn.tong_hop(d, date(2026, 10, 19))
        self.assertTrue(th['du_dieu_kien_tu_dong'])
        self.assertEqual(th['con_thieu'], [])
        # loại chủ đầu tư tự thỏa thuận: không cần NQ danh mục thu hồi / thông báo thu hồi
        d2 = tn.moi()
        d2['loai_cdt'] = 'tu_thoa_thuan'
        ma = {m[0] for m in tn.MUC_HO_SO if tn.ap_dung(m, d2)}
        self.assertNotIn('hs09', ma)
        self.assertIn('hs11', ma)
        self.assertTrue(any('KHÔNG thu hồi' in x for x in tn.trach_nhiem(d2)))

    def test_luu_mo_xuat(self):
        d = tn.moi()
        d['du_an']['ten'] = 'Dự án thử'
        d['ho_so']['hs01'] = True
        p = tn.luu_file(d, self.td / 'hs')
        self.assertEqual(p.suffix, tn.DUOI)
        self.assertEqual(tn.mo_file(p)['ho_so'], {'hs01': True})
        x = tn.xuat_phieu_xlsx(d, self.td / 'phieu.xlsx')
        self.assertIn('PHIẾU TIẾP NHẬN', _chu(x))
        c = tn.xuat_cong_van_docx(d, self.td / 'cv.docx')
        import zipfile
        with zipfile.ZipFile(c) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        self.assertIn('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', xml)
        self.assertIn('Đề nghị Chủ đầu tư cung cấp', xml)

    def test_quet_excel(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Số tờ', 'Số thửa', 'Diện tích thu hồi', 'Loại đất'])
        ws.append([1, 'Nguyễn Văn A', 'Ấp 1', 1, 2, 50, 'ONT'])
        ws.append([2, 'Trần B', 'Ấp 1', 1, 2, 30, 'XYZ'])
        f = self.td / 'ke.xlsx'
        wb.save(f)
        kq = tn.quet_excel(f)
        self.assertEqual(kq['so_dong'], 2)
        self.assertEqual(kq['trung'], 1)
        self.assertEqual(kq['sai_loai_dat'], 1)

    def test_lenh_may_trang_va_hop(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        ten = 'Tiếp nhận & Kiểm tra pháp lý dự án…'
        self.assertNotIn(ten, ud.LENH_CAN_DU_AN)
        a = w.lenh[ten]
        self.assertTrue(a.isEnabled())                                   # chưa mở dự án vẫn bật
        self.assertEqual(a.shortcut().toString(), 'Ctrl+Shift+L')
        self.assertEqual(ud.NHAN_MENU[ten], 'Tiếp nhận hồ sơ pháp lý')
        self.assertIs(w.nut_chao[ten].defaultAction(), a)                # nút màn hình chào dùng chung QAction
        d = w.tiep_nhan_phap_ly(cho=False)
        d.im_lang = True
        self.addCleanup(d.close)
        self.assertIsNone(d.con)
        self.assertEqual(d.tab.count(), 4)
        self.assertEqual(d.bang_hs.rowCount(), 32 + 5)
        self.assertFalse(any(o.text() for o in d.o_da.values()))
        d.o_da['ten'].setText('Dự án thử')
        p = d.luu_tep(str(self.td / 'x.pabtpl'))
        self.assertEqual(json.loads(Path(p).read_text(encoding='utf-8'))['du_an']['ten'], 'Dự án thử')
        mo = []
        d.khoi_tao = lambda x: mo.append(tn.du_lieu_du_an_moi(x))
        d.khoi_tao_du_an()
        self.assertEqual(mo[0]['ten'], 'Dự án thử')
        # có dự án: lưu vào dự án, Thông tin dự án hiện trạng thái
        w.mo(str(_du_an(self.td, 2)))
        d2 = w.tiep_nhan_phap_ly(cho=False)
        d2.im_lang = True
        self.addCleanup(d2.close)
        self.assertEqual(d2.o_da['so_ho_dk'].text(), '2')
        self.assertTrue(d2.luu_du_an())
        self.assertIsNotNone(tn.doc_du_an(w.con))


if __name__ == '__main__':
    unittest.main()
