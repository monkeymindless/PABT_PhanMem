"""Kiểm thử bảng giá đất NQ 28/2025/NQ-HĐND (4 địa bàn) và tra giá khi lập dự án."""
from __future__ import annotations
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import openpyxl

from pabt import gia_dat_nq28 as nq

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestBangGia(unittest.TestCase):
    def setUp(self):
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        self._td = tempfile.TemporaryDirectory()
        os.environ['PABT_THU_MUC_MAY'] = self._td.name

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self._td.cleanup()

    def test_nho_giay_va_ghi_thay_co_hieu_luc_ngay(self):
        """1.0.31: _da_doc nhớ NHO_GIAY giây (không stat file mỗi lần tra); ghi_thay / xoa_thay có hiệu lực ngay."""
        from unittest import mock
        nq._quen()
        goc = nq._nguon
        dem = []
        with mock.patch.object(nq, '_nguon', lambda: dem.append(1) or goc()):
            for _ in range(50):
                nq.tat_ca()
                nq.dang_thay()
                nq.tim('Trị An', 'duong')
        self.assertEqual(len(dem), 1)
        self.assertFalse(nq.dang_thay())
        nq.ghi_thay([dict(nq.tat_ca()[0], xa='Xã Thử')], 'Bảng thử')
        self.assertTrue(nq.dang_thay())
        self.assertEqual(nq.ds_xa(), ['Xã Thử'])
        self.assertTrue(nq.xoa_thay())
        self.assertFalse(nq.dang_thay())

    def test_du_lieu_day_du(self):
        ds = nq.tat_ca()
        self.assertEqual(nq.ds_xa(), ['Xã Trị An', 'Xã Tân An', 'Xã Phú Lý', 'Phường Tân Triều'])
        so = {x: sum(1 for r in ds if r['xa'] == x) for x in nq.ds_xa()}
        self.assertEqual(so, {'Xã Trị An': 427, 'Xã Tân An': 182, 'Xã Phú Lý': 133, 'Phường Tân Triều': 385})
        for r in ds:
            for k, _ in nq.COT:
                self.assertIsInstance(r[k], int, (r['xa'], r['tt'], k))
            self.assertTrue(r['sxkd'] <= r['tmdv'] <= r['dat_o'], (r['xa'], r['tt']))
            self.assertLessEqual(r['nn_rung_nts'], r['nn_cay'], (r['xa'], r['tt']))
        # mỗi đoạn: MT, T1-T3, K1-K3
        for x in nq.ds_xa():
            vt = [r['vi_tri'] for r in ds if r['xa'] == x]
            self.assertEqual(vt, ['MT', 'T1', 'T2', 'T3', 'K1', 'K2', 'K3'] * (len(vt) // 7))

    def test_mot_so_dong_doi_chieu_van_ban(self):
        g = {(r['xa'], r['tt']): r for r in nq.tat_ca()}
        r = g[('Phường Tân Triều', 1)]
        self.assertEqual((r['ten_duong'], r['dat_o'], r['tmdv'], r['sxkd'], r['nn_cay'], r['nn_rung_nts']),
                         ('Đường Nguyễn Ái Quốc', 40600, 28400, 24400, 1200, 770))
        r = g[('Xã Trị An', 1)]
        self.assertEqual((r['ten_duong'], r['diem_dau'], r['dat_o'], r['nn_cay']), ('Đường Xóm Huế', 'Đường tỉnh 768', 2000, 470))
        r = g[('Xã Tân An', 1)]
        self.assertEqual((r['ten_duong'], r['dat_o'], r['nn_cay'], r['nn_rung_nts']), ('Đường tỉnh 768', 5600, 730, 530))
        r = g[('Xã Phú Lý', 133)]
        self.assertEqual((r['vi_tri'], r['dat_o'], r['nn_cay']), ('K3', 180, 60))
        self.assertEqual(g[('Xã Trị An', 184)]['nguong'], [600, 400])          # Lạc Long Quân: 600m / 400m
        self.assertEqual(g[('Xã Trị An', 2)]['nguong'], [1000, 500])

    def test_tra_cuu(self):
        self.assertEqual(nq.cot_cua_loai('ONT+CLN'), 'dat_o')
        self.assertEqual(nq.cot_cua_loai('LUK'), 'nn_cay')
        self.assertEqual(nq.cot_cua_loai('NTS'), 'nn_rung_nts')
        self.assertIsNone(nq.cot_cua_loai('XYZ'))
        ds = nq.tim('Xã Tân Triều', 'huong lo 15 MT')                   # gõ sai cấp xã/phường vẫn khớp
        self.assertTrue(ds and all(r['xa'] == 'Phường Tân Triều' and r['vi_tri'] == 'MT' for r in ds))
        self.assertEqual(nq.gia_dong(ds[0], 'dat_o'), ds[0]['dat_o'] * 1000)
        self.assertIn('NQ 28/2025/NQ-HĐND', nq.can_cu(ds[0], 'dat_o'))
        r = nq.tim('Trị An', 'xom hue')[1]
        self.assertIn('≤1.000m', nq.mo_ta_vi_tri(r))

    def test_xuat_excel(self):
        with tempfile.TemporaryDirectory() as td:
            f = nq.xuat_excel(Path(td) / 'bg.xlsx')
            wb = openpyxl.load_workbook(f)
            self.assertEqual(wb.sheetnames, nq.ds_xa())
            ws = wb['Phường Tân Triều']
            self.assertEqual(ws.max_row, 4 + 385)
            self.assertEqual(ws['G5'].value, 40600000)

    def test_thay_bang_dia_ban_khac_roi_khoi_phuc(self):
        """File Excel một phường thay cả 4 địa bàn gắn sẵn; xóa file thì trở lại bảng cũ."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Phường Trảng Bom'
        ws['A1'] = 'Quyết định giá đất Phường Trảng Bom'
        ws['A2'] = 'Đơn vị: đồng/m².'
        ws.append(['Tên đường', 'Điểm đầu', 'Điểm cuối', 'Vị trí', 'Đất ở', 'Đất thương mại, dịch vụ'])
        ws.append(['Đường Quốc lộ 1', 'Ngã tư', 'Cầu', 'MT', 12_500_000, 8_000_000])
        ws.append(['Đường Quốc lộ 1', 'Ngã tư', 'Cầu', 'Vị trí 1', 6_000_000, 4_000_000])
        p = Path(self._td.name) / 'trang_bom.xlsx'
        wb.save(p)
        dong, vb, chu = nq.doc_excel(p)
        self.assertIn('đồng/m²', chu)
        self.assertIn('Trảng Bom', vb)
        nq.ghi_thay(dong, vb, p)
        self.assertTrue(nq.dang_thay())
        self.assertEqual(nq.ds_xa(), ['Phường Trảng Bom'])
        self.assertEqual(len(nq.tat_ca()), 2)
        r = nq.tat_ca()[0]
        self.assertEqual((r['dat_o'], r['tmdv'], r['vi_tri']), (12500, 8000, 'MT'))
        self.assertEqual(nq.gia_dong(r, 'dat_o'), 12_500_000)
        self.assertEqual(nq.tat_ca()[1]['vi_tri'], 'VT1')
        self.assertEqual(nq.mo_ta_vi_tri(nq.tat_ca()[1]), 'VT1')
        self.assertIn('Trảng Bom', nq.can_cu(r, 'dat_o'))
        self.assertTrue(nq.xoa_thay())
        self.assertFalse(nq.dang_thay())
        self.assertEqual(nq.ds_xa(), ['Xã Trị An', 'Xã Tân An', 'Xã Phú Lý', 'Phường Tân Triều'])

    def test_doc_lai_file_xuat(self):
        f = nq.xuat_excel(Path(self._td.name) / 'bg.xlsx')
        dong, vb, _ = nq.doc_excel(f)
        self.assertIn('28/2025', vb)
        self.assertEqual(len(dong), len(nq.tat_ca()))
        goc = {(r['xa'], r['tt'], r['vi_tri']): r['dat_o'] for r in nq.tat_ca()}
        doc = {(r['xa'], r['tt'], r['vi_tri']): r['dat_o'] for r in dong}
        self.assertEqual(doc[('Phường Tân Triều', 1, 'MT')], goc[('Phường Tân Triều', 1, 'MT')])


@unittest.skipUnless(CO_QT, 'không có PySide6')
class TestManHinhGiaDat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_hop_tra_va_lay_gia_trong_du_an_moi(self):
        from pabt.man_hinh_gia_dat import HopTraGiaDat
        from pabt.man_hinh_du_an_moi import HopDuAnMoi
        h = HopTraGiaDat(None, 'Trị An', 'LUK')
        self.assertEqual(h.o_cot.currentData(), 'nn_cay')
        self.assertEqual(h.bang.rowCount(), 427)
        h.o_tim.setText('kim lien MT')
        self.assertEqual(h.bang.rowCount(), 1)
        h.bang.selectRow(0)
        h.accept()
        dong, cot = h.chon
        self.assertEqual((dong['ten_duong'], cot), ('Đường Kim Liên', 'nn_cay'))
        d = HopDuAnMoi(luu_cai_dat=False)
        d.im_lang = True
        d.o['ten'].setText('X')
        d.o['ten_dia_ban'].setText('Trị An')
        d.sang(1)
        d.them_dong(dict(ho_ten='A', so_to='1', so_thua='2', loai_dat='LUK', dt_thu_hoi='100', vi_tri='1'))
        d.sang(2)
        self.assertEqual(d.tra_gia_nq28(0, chon=(dong, cot)), 470000)
        g = d.gia_dat()[0]
        self.assertEqual(g['gia'], '470000')
        self.assertIn('Đường Kim Liên', g['ghi_chu'])
        d.sang(1)
        d.sang(2)                                                         # quay lại: giữ giá và căn cứ
        self.assertIn('Đường Kim Liên', d.gia_dat()[0]['ghi_chu'])
        with tempfile.TemporaryDirectory() as td:
            kq = d.tao(str(Path(td) / 'a.pabt'), xuat=False)
            from pabt import csdl
            con = csdl.mo(kq['file'])
            try:
                r = con.execute('SELECT gia, can_cu FROM gia_dat').fetchone()
                self.assertEqual(r[0], '470000')
                self.assertIn('NQ 28/2025', r[1])
            finally:
                con.close()


class TestCapNhatGiaDat(unittest.TestCase):
    """Web không ra giá thì không ghi; file Excel/CSV thay bốn địa bàn gắn sẵn rồi khôi phục được."""

    def setUp(self):
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        self._td = tempfile.TemporaryDirectory()
        os.environ['PABT_THU_MUC_MAY'] = self._td.name

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self._td.cleanup()

    def test_ten_gon_khong_can_xa_phuong(self):
        from pabt.cap_nhat_gia_dat import ten_gon
        self.assertEqual(ten_gon('Xã Trị An'), 'Trị An')
        self.assertEqual(ten_gon('Trảng Bom'), 'Trảng Bom')
        self.assertEqual(ten_gon('Thành phố Hồ Chí Minh'), 'Hồ Chí Minh')
        self.assertEqual(ten_gon('TP. Vũng Tàu'), 'Vũng Tàu')
        self.assertEqual(ten_gon('Tỉnh Lâm Đồng'), 'Lâm Đồng')
        self.assertEqual(ten_gon('TP.HCM'), 'Hồ Chí Minh')
        self.assertEqual(ten_gon('TP HCM'), 'Hồ Chí Minh')

    def test_boc_nghi_quyet_bay_muc_vi_tri(self):
        from pabt.cap_nhat_gia_dat import loc_xa, phan_tich_nghi_quyet
        rows = [
            ['Xã Trảng Bom'],
            ['TT', 'Tên đường giao thông', 'Điểm đầu', 'Điểm cuối', 'Giá đất ở',
             'Giá đất thương mại, dịch vụ', 'Giá đất sản xuất phi nông nghiệp'],
            ['1', 'Đường A', '15.300', '10.700', '9.200'],
            ['2', 'Các tuyến đường giao thông đấu nối trực tiếp ra Đường A', '5.900', '4.100', '3.500'],
            ['5', 'Các tuyến đường giao thông không đấu nối trực tiếp và thông ra Đường A', '5.300', '3.700', '3.200'],
        ]
        dong = loc_xa(phan_tich_nghi_quyet(rows), 'Trảng Bom')
        self.assertEqual([r['vi_tri'] for r in dong], ['MT', 'T1', 'K1'])
        self.assertEqual(dong[0]['ten_duong'], 'Đường A')
        self.assertEqual(dong[1]['ten_duong'], 'Đường A')
        self.assertEqual((dong[0]['dat_o'], dong[0]['tmdv'], dong[0]['sxkd']), (15300, 10700, 9200))
        self.assertEqual(nq.gia_dong(dong[0], 'dat_o'), 15_300_000)
        self.assertEqual(dong[0]['diem_dau'], '')

    def test_doc_diem_dau_cuoi_va_nhom_dat(self):
        from pabt.cap_nhat_gia_dat import phan_tich_nghi_quyet
        rows = [
            ['1. Phường Biên Hòa'],
            ['TT', 'Tên đường giao thông', 'Điểm đầu', 'Điểm cuối',
             'Giá đất trồng cây lâu năm, đất trồng cây hằng năm',
             'Giá đất trồng rừng sản xuất và nuôi trồng thủy sản'],
            ['1', 'Đường Bùi Hữu Nghĩa', 'Giáp ranh giới thành phố Hồ Chí Minh', 'Đường Nguyễn Tri Phương', '1.500', '970'],
            ['2', 'Các tuyến đường giao thông đấu nối trực tiếp ra Đường Bùi Hữu Nghĩa', '1.030', '680'],
        ]
        dong = phan_tich_nghi_quyet(rows)
        self.assertEqual(dong[0]['ten_duong'], 'Đường Bùi Hữu Nghĩa')
        self.assertEqual(dong[0]['diem_dau'], 'Giáp ranh giới thành phố Hồ Chí Minh')
        self.assertEqual(dong[0]['diem_cuoi'], 'Đường Nguyễn Tri Phương')
        self.assertEqual(dong[0]['vi_tri'], 'MT')
        self.assertEqual((dong[0]['nn_cln'], dong[0]['nn_chn'], dong[0]['nn_cay']), (1500, 1500, 1500))
        self.assertEqual((dong[0]['nn_rsx'], dong[0]['nn_nts'], dong[0]['nn_rung_nts']), (970, 970, 970))
        self.assertEqual(dong[1]['ten_duong'], 'Đường Bùi Hữu Nghĩa')
        self.assertEqual(dong[1]['vi_tri'], 'T1')
        self.assertEqual(dong[1]['diem_dau'], dong[0]['diem_dau'])
        self.assertEqual(dong[1]['diem_cuoi'], dong[0]['diem_cuoi'])
        self.assertEqual(dong[1]['nn_chn'], 1030)

    def test_gop_hai_phu_luc_khong_trung_xa(self):
        """Phụ lục đất ở và nông nghiệp cùng một đoạn: một dòng, đủ cả hai nhóm giá. Dấu phẩy và dấu chấm ở điểm cuối vẫn khớp."""
        from pabt.cap_nhat_gia_dat import phan_tich_nghi_quyet
        rows = [
            ['Phường Biên Hòa'],
            ['TT', 'Tên đường giao thông', 'Điểm đầu', 'Điểm cuối',
             'Giá đất trồng cây lâu năm, đất trồng cây hằng năm',
             'Giá đất trồng rừng sản xuất và nuôi trồng thủy sản'],
            ['1', 'Đường Trần Văn Ơn', 'Đường Bùi Hữu Nghĩa',
             'Chạm tới giữa ranh thửa đất số 9. tờ BĐĐC số 124', '1.430', '970'],
            ['Phường Biên Hòa'],
            ['TT', 'Tên đường giao thông', 'Điểm đầu', 'Điểm cuối', 'Giá đất ở',
             'Giá đất thương mại, dịch vụ', 'Giá đất sản xuất phi nông nghiệp'],
            ['1', 'Đường Trần Văn Ơn', 'Đường Bùi Hữu Nghĩa',
             'Chạm tới giữa ranh thửa đất số 9, tờ BĐĐC số 124', '15.400', '10.800', '9.200'],
        ]
        dong = phan_tich_nghi_quyet(rows)
        self.assertEqual(len(dong), 1)
        self.assertEqual(dong[0]['nn_cay'], 1430)
        self.assertEqual(dong[0]['dat_o'], 15400)
        self.assertEqual(dong[0]['tmdv'], 10800)

    def test_tra_gia_theo_diem_va_nhom(self):
        from unittest import mock
        from pabt import gia_dat_qd03 as gd
        doan = dict(ten_duong='Đường tỉnh 761', diem_dau='Giáp ranh xã Trị An', diem_cuoi='Cầu suối Kộp', tt_bat_dau=99)
        dong = [dict(xa='Xã Phú Lý', tt=1, ten_duong='Đường tỉnh 761', diem_dau='Giáp ranh xã Trị An',
                     diem_cuoi='Cầu suối Kộp', vi_tri='MT', dat_o=0, tmdv=0, sxkd=0, nn_cay=1500,
                     nn_cln=1800, nn_chn=230, nn_rung_nts=970, nn_rsx=970, nn_nts=400)]
        with mock.patch('pabt.gia_dat_nq28.dong_cua_xa', return_value=dong):      # 1.0.90: tra theo chỉ mục xã

            hang = gd.gia_bang_gia('Bảng 55. Xã Phú Lý', doan, 'DAT_NONG_NGHIEP', 'MAT_TIEN_VT1', 'nn_chn')
            lau = gd.gia_bang_gia('Bảng 55. Xã Phú Lý', doan, 'DAT_NONG_NGHIEP', 'MAT_TIEN_VT1', 'nn_cln')
        self.assertEqual(hang, Decimal(230000))
        self.assertEqual(lau, Decimal(1800000))

    def test_thieu_module_web_ra_loi_tieng_viet(self):
        import sys
        from unittest import mock
        from pabt.cap_nhat_gia_dat import LoiWeb, _module_web
        import pabt
        # bài khác đã nạp module: `from . import cap_nhat_web` lấy thuộc tính của gói pabt trước sys.modules -> gỡ tạm cả hai
        cu = pabt.__dict__.pop('cap_nhat_web', None)
        try:
            with mock.patch.dict(sys.modules, {'pabt.cap_nhat_web': None}):
                with self.assertRaises(LoiWeb) as ctx:
                    _module_web()
        finally:
            if cu is not None:
                pabt.cap_nhat_web = cu
        self.assertNotIn('cannot import', str(ctx.exception))
        self.assertIn('Excel', str(ctx.exception))
        self.assertFalse(nq.dang_thay())

    def test_web_khong_co_gia_khong_ghi(self):
        from unittest import mock
        from pabt.cap_nhat_gia_dat import LoiWeb, tim_tren_web
        from pabt.lap_pa import LoiNhap
        # không truy cập mạng (trước 0.9.65 bài này gọi vbpl.vn thật): trang tìm lỗi, nguồn tham khảo không có xã này
        with mock.patch('pabt.cap_nhat_web.quet', return_value=[]), \
                mock.patch('pabt.cap_nhat_web._lay', side_effect=LoiNhap('không có mạng (test)')), \
                mock.patch('pabt.nguon_gia_dat.doc_guland', return_value=[]):
            with self.assertRaises(LoiWeb):
                tim_tren_web('Bình Dương', 'Phường Thử')
        self.assertFalse(nq.dang_thay())
        self.assertEqual(nq.ds_xa(), ['Xã Trị An', 'Xã Tân An', 'Xã Phú Lý', 'Phường Tân Triều'])

    def test_tim_web_chi_can_ten_tinh(self):
        from unittest import mock
        from pabt.cap_nhat_gia_dat import LoiWeb, tim_tren_web
        with self.assertRaises(LoiWeb) as ctx:
            tim_tren_web('', '')
        self.assertIn('tỉnh', str(ctx.exception).lower())
        mau = ([{'xa': 'Xã A', 'ten_duong': 'Đường 1'}], 'VB', 'chu', 'https://vi-du')
        with mock.patch('pabt.cap_nhat_gia_dat._tim_va_boc', return_value=mau):
            dong, vb, _chu, _nguon = tim_tren_web('Đồng Nai', '')
        self.assertEqual(dong[0]['xa'], 'Xã A')
        self.assertEqual(vb, 'VB')

    def test_csv_va_excel_thay_bon_xa(self):
        from pabt.cap_nhat_gia_dat import ap_dung, doc_file
        p = Path(self._td.name) / 'gia.csv'
        p.write_text(
            'Quyết định thử, không phải giá thật\n'
            'Tên đường,Điểm đầu,Điểm cuối,Vị trí,Đất ở\n'
            'Đường Thử,Đầu,Cuối,MT,"15.000.000"\n',
            encoding='utf-8')
        dong, vb, chu = doc_file(p, 'Tỉnh Thử', 'Phường Thử')
        self.assertIn('đồng/m²', chu)
        self.assertEqual(dong[0]['xa'], 'Phường Thử')
        self.assertEqual(nq.gia_dong(dong[0], 'dat_o'), 15_000_000)
        ap_dung(dong, vb, p)
        self.assertEqual(nq.ds_xa(), ['Phường Thử'])
        self.assertNotIn('Xã Trị An', nq.ds_xa())
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Xã Khác'
        ws['A1'] = 'Đơn vị: đồng/m².'
        ws.append(['Tên đường', 'Vị trí', 'Đơn giá'])
        ws.append(['Đường B', 'VT 2', 8_000_000])
        xp = Path(self._td.name) / 'khac.xlsx'
        wb.save(xp)
        dong2, _, _ = doc_file(xp, 'Tỉnh Thử', '')
        self.assertEqual(dong2[0]['xa'], 'Xã Khác')
        self.assertEqual(dong2[0]['vi_tri'], 'VT2')
        ap_dung(dong2, 'VB thử', xp)
        self.assertEqual(nq.ds_xa(), ['Xã Khác'])
        self.assertTrue(nq.xoa_thay())
        self.assertEqual(nq.ds_xa()[0], 'Xã Trị An')

    @unittest.skipUnless(CO_QT, 'không có PySide6')
    def test_hop_va_menu(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from pabt.app import CuaSoChinh
        from pabt.man_hinh_du_toan import HopTraNQ28
        from pabt.man_hinh_gia_dat import KhungCapNhatGiaDat
        app = QApplication.instance() or QApplication([])  # noqa: F841
        w = CuaSoChinh(menu_trai=True)
        self.assertIn('Cập nhật bảng giá đất…', w.lenh)
        self.assertNotIn('Thay bảng giá đất…', w.lenh)
        self.assertNotIn('Dùng lại bảng giá gắn sẵn', w.lenh)
        # 30/10/2026: công cụ cập nhật là thẻ của cửa sổ Bảng giá đất (không còn cửa sổ riêng)
        hop = w.cap_nhat_bang_gia_dat(cho=False)
        self.assertIsInstance(hop, HopTraNQ28)
        self.assertEqual(hop.tabs.currentIndex(), HopTraNQ28.THE_CAP_NHAT)
        self.assertEqual(hop.tabs.tabText(HopTraNQ28.THE_QUY_TAC), 'Bộ quy tắc giá đất')
        self.assertFalse(hop.khung_goi.isWindow())
        d = hop.khung_cn
        self.assertIsInstance(d, KhungCapNhatGiaDat)
        p = Path(self._td.name) / 'gia.csv'
        p.write_text('Tên đường,Vị trí,Đất ở\nĐường C,MT,9000000\n', encoding='utf-8')
        d.im_lang = True
        d.o_xa.setText('Xã Mới')
        self.assertIsNotNone(d.nap_file(str(p)))
        # mặc định BỔ SUNG: giữ bốn địa bàn gắn sẵn, thêm Xã Mới; thẻ Bảng giá nạp lại danh sách địa bàn
        self.assertEqual(d.ghi(), ['Xã Trị An', 'Xã Tân An', 'Xã Phú Lý', 'Phường Tân Triều', 'Xã Mới'])
        self.assertGreaterEqual(hop.cb_xa.findData('Xã Mới'), 0)
        self.assertIn('gắn sẵn + bổ sung', nq.tom_tat())
        self.assertIn('NQ 28/2025', nq.can_cu(nq.tim('Trị An')[0], 'dat_o'))     # dòng gắn sẵn giữ căn cứ của mình
        d.cb_cach.setCurrentIndex(d.cb_cach.findData('thay'))
        self.assertEqual(d.ghi(), ['Xã Mới'])
        self.assertEqual(nq.ds_xa(), ['Xã Mới'])
        d.khoi_phuc()
        self.assertEqual(nq.ds_xa(), ['Xã Trị An', 'Xã Tân An', 'Xã Phú Lý', 'Phường Tân Triều'])
        self.assertEqual(d.b_thay.text(), 'Thay cả bảng')
        self.assertTrue(d.b_thay.isEnabled())
        self.assertEqual(d.ghi(thay=True), ['Xã Mới'])
        self.assertEqual(nq.ds_xa(), ['Xã Mới'])
        hop.close()
        w.close()


if __name__ == '__main__':
    unittest.main()
