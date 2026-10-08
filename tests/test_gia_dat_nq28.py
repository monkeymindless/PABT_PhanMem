"""Kiểm thử bảng giá đất NQ 28/2025/NQ-HĐND (4 địa bàn) và tra giá khi lập dự án."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import gia_dat_nq28 as nq

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestBangGia(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
