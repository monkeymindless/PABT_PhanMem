"""1.0.83: thanh trạng thái 6 nấc (0/6..6/6) theo 16 bước QĐ 18/2026/QĐ-UBND, và liên kết ô Vị trí với bảng tính NQ 28 & QĐ 03.
Giữ tim_nhom / chu_truong_hop của 1.0.82. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import app as ud  # noqa: E402
from pabt import gia_dat_qd03 as gd  # noqa: E402
from pabt import giao_dien  # noqa: E402
from pabt import theo_doi  # noqa: E402
from pabt.tien import D  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


def _qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _ho(**kw):
    goc = dict(ma_ho=1, thu_tu=1, ho_ten='Hộ thử', dia_chi='', thua=[], qd=[])
    goc.update(kw)
    return theo_doi.TongHopHo(**goc)


def _qd(da_chi_tra=False):
    return dict(da_chi_tra=da_chi_tra, so_tien='1000', chi_tra_so_tien='1000' if da_chi_tra else '')


class TestThangSauNac(unittest.TestCase):
    def test_hang_so_va_thanh(self):
        self.assertEqual(theo_doi.SO_NAC_QD18, 6)
        self.assertEqual(len(ud.THANH_NAC), 7)
        self.assertEqual(len(ud.NHAN_NAC), 7)
        self.assertEqual(len(ud.MAU_NAC), 7)
        self.assertEqual(ud.RONG_COT_DS[5], (225, 285))
        for i, t in enumerate(ud.THANH_NAC):
            self.assertEqual(len(t), 6)
            self.assertEqual(t.count('■'), i)
            self.assertTrue(set(t) <= set('■□'))
        self.assertIn('Bước 5', ud.NHAN_NAC[1])
        self.assertIn('Bước 15–16', ud.NHAN_NAC[6])
        self.assertEqual(ud.chi_so_nac(9), 6)
        self.assertEqual(ud.chi_so_nac(-1), 0)
        self.assertEqual(ud.chi_so_nac('x'), 0)

    def test_phan_tich_tuan_tu_0_den_6(self):
        self.assertEqual(_ho().tien_do.nac, 0)
        self.assertEqual(_ho().trang_thai, 'Chưa lập phương án')
        td = _ho(da_lap=True).tien_do
        self.assertEqual((td.nac, td.da_lap, td.da_ny, td.da_tr), (1, True, False, False))
        self.assertEqual(_ho(da_lap=True).trang_thai, 'Đã lập phương án (B5)')
        td = _ho(da_lap=True, da_niem_yet=True).tien_do
        self.assertEqual((td.nac, td.da_ny, td.da_lap), (2, True, True))
        self.assertIn('niêm yết', _ho(da_lap=True, da_niem_yet=True).trang_thai.lower())
        td = _ho(da_lap=True, da_trinh=True).tien_do
        self.assertEqual((td.nac, td.da_tr, td.da_ny), (3, True, True))
        self.assertTrue(_ho(da_lap=True, da_trinh=True).trang_thai.startswith('Đã trình thẩm định'))
        # 1.0.90 (người dùng 09/11/2026): gắn đợt mà CHƯA lập phương án không nhảy nấc, có cảnh báo
        for kw in (dict(da_niem_yet=True), dict(da_trinh=True)):
            td = _ho(**kw).tien_do
            self.assertEqual((td.nac, td.da_lap), (0, False))
            self.assertIn('chưa lập phương án', td.canh_bao)
        td = _ho(qd=[_qd(False)]).tien_do
        self.assertEqual((td.nac, td.da_pd, td.da_ct), (4, True, False))
        self.assertTrue(_ho(qd=[_qd(False)]).trang_thai.startswith('Đã phê duyệt'))
        hai = [_qd(True), _qd(False)]
        self.assertIn('1/2', _ho(qd=hai).trang_thai)
        td = _ho(qd=[_qd(True)]).tien_do
        self.assertEqual((td.nac, td.da_ct, td.da_bg), (5, True, False))
        self.assertEqual(_ho(qd=[_qd(True)]).trang_thai, 'Đã nhận tiền, chưa bàn giao')
        x = _ho(qd=[_qd(True)], da_ban_giao=True)
        self.assertEqual(x.tien_do.nac, 5)
        self.assertIn('chưa có ngày biên bản', x.tien_do.canh_bao)
        x = _ho(qd=[_qd(True)], da_ban_giao=True, ban_giao_ngay='08/11/2026')
        self.assertEqual((x.tien_do.nac, x.tien_do.da_bg, x.tien_do.canh_bao), (6, True, ''))
        self.assertEqual(x.trang_thai, 'Đã bàn giao MB')

    def test_dot_tren_ho_doc_vao_tong_hop(self):
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(td, ignore_errors=True))
        from pabt import csdl
        con = csdl.mo(_du_an(td, 2))
        self.addCleanup(con.close)
        ma = con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        with con:
            con.execute('UPDATE ho SET dot_du_thao_id = 9 WHERE ma_ho = ?', (ma,))
        x = next(h for h in theo_doi.tong_hop(con, [ma], tinh_pa=False) if h.ma_ho == ma)
        self.assertTrue(x.da_niem_yet)
        self.assertFalse(x.da_trinh)
        self.assertEqual(x.tien_do.nac, 2)
        with con:
            con.execute('UPDATE ho SET dot_id = 4 WHERE ma_ho = ?', (ma,))
        x = next(h for h in theo_doi.tong_hop(con, [ma], tinh_pa=False) if h.ma_ho == ma)
        self.assertTrue(x.da_trinh)
        self.assertEqual(x.tien_do.nac, 3)
        self.assertTrue(x.trang_thai.startswith('Đã trình thẩm định'))

    def test_chu_thich_va_vien_thuoc(self):
        _qt()
        from PySide6.QtCore import Qt
        m = ud.BangHo([dict(ma_ho=1, o=[1, 'An', 'Ấp', 1, 0, 'Đã lập phương án (B5)', ''], nac=1, ten_gon='An', phu_ten='')])
        hien = m.data(m.index(0, 5), Qt.ItemDataRole.DisplayRole)
        self.assertTrue(hien.startswith(ud.THANH_NAC[1]))
        tip = m.data(m.index(0, 5), Qt.ItemDataRole.ToolTipRole)
        self.assertIn(ud.NHAN_NAC[1], tip)
        self.assertIn('(1/6)', tip)
        self.assertEqual(giao_dien.mau_vien_thuoc('Đã niêm yết & Lấy ý kiến (B6–7)')[:3], ('#E0F2FE', '#BAE6FD', '#0369A1'))
        self.assertEqual(giao_dien.mau_vien_thuoc('Đã trình thẩm định (B8)')[:3], ('#EEF2FF', '#C7D2FE', '#4338CA'))
        self.assertEqual(giao_dien.mau_vien_thuoc('Đã lập phương án (B5)')[2], '#2F5DB5')
        self.assertEqual(giao_dien.mau_vien_thuoc('Chưa lấy ý kiến')[0], '#F1F5F9')

    def test_du_phong_khong_co_tong_hop(self):
        h = dict(ma_ho=1, tong=0, lech=False, ho_ten='A', ghi_chu_dc='')
        d = ud.CuaSoChinh._dong_ho(1, h, ({}, {1: dict(dot_du_thao_id=8)}, {}, {}, ''))
        self.assertEqual(d['nac'], 2)
        d = ud.CuaSoChinh._dong_ho(1, h, ({}, {1: dict(dot_id=3, dot_du_thao_id=8)}, {}, {}, ''))
        self.assertEqual(d['nac'], 3)
        d = ud.CuaSoChinh._dong_ho(1, h, ({}, {1: dict(da_ban_giao=1)}, {}, {}, ''))
        self.assertEqual(d['nac'], 6)


class TestLienKetViTri(unittest.TestCase):
    def test_lam_sach_va_chi_tiet_nho_thuoc_tinh(self):
        self.assertEqual(gd.lam_sach_vi_tri('Mặt tiền đường AKhông'), 'Mặt tiền đường A')
        self.assertEqual(gd.lam_sach_vi_tri('Không'), 'Không')
        db = gd.ds_dia_ban()[0]
        doan = gd.ds_doan(db)[0]
        ma = gd._goi()['vi_tri'][0]['ma']
        chu = gd.mo_ta_vi_tri(doan, ma)
        self.assertTrue(chu)
        self.assertFalse(chu.endswith('Không'))
        self.assertEqual(gd.lam_sach_vi_tri(chu + 'Không'), chu)
        k = gd.KetQua(D(230000), D('1.1'), D(1), D(1), D(1), D('1.1'), D(253000), D(253000), D(0), False, '230.000 × 1,10', [], [])
        v = gd.DauVao(dia_ban=db, nhom_dat='DAT_O', ma_doan_duong=doan['ma_doan_duong'], loai_ket_noi_vi_tri=ma,
                      ket_cau_mat_duong='NHUA_BETONG', ma_vi_tri_dat='VT1_PV1', truong_hop_nq28='', yeu_to_pl3=['yt'],
                      ap_dung_quy_hoach_pl2=True)
        ct = gd.chi_tiet_ap_gia(k, v, chu + 'Không')
        self.assertEqual(ct['dia_ban'], db)
        self.assertEqual(ct['ma_doan_duong'], doan['ma_doan_duong'])
        self.assertEqual(ct['loai_ket_noi_vi_tri'], ma)
        self.assertEqual(ct['pham_vi_vi_tri'], 'VT1_PV1')
        self.assertEqual(ct['yeu_to_pl3'], ['yt'])
        self.assertTrue(ct['ap_dung_quy_hoach_pl2'])
        self.assertEqual(ct['mo_ta_vi_tri'], chu)
        self.assertEqual(ct['don_gia'], '0')
        gon = gd.chi_tiet_ap_gia(k)
        self.assertNotIn('dia_ban', gon)
        self.assertIn('he_so_k1', gon)

    def test_giu_tim_nhom_va_chu_truong_hop(self):
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        src = inspect.getsource(HopTinhGiaDat.dat_thong_so)
        self.assertIn("self.tim_nhom(n['ma'], n['cot_gia'], loai_dat)", src)
        self.assertIn('chu_truong_hop', inspect.getsource(HopTinhGiaDat.tinh))
        self.assertIn('loai_nn_cua_ma', inspect.getsource(HopTinhGiaDat.tim_nhom))

    def test_cap_nhat_vi_tri_khi_don_gia_0(self):
        _qt()
        from pabt.man_hinh import CuaSoLapPA
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(td, ignore_errors=True))
        from pabt import csdl
        con = csdl.mo(_du_an(td, 1))
        self.addCleanup(con.close)
        ma = con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        w = CuaSoLapPA(con, ma)
        w.im_lang = True
        self.addCleanup(w.close)
        ds = w.ds_vi_tri_dong(0)
        self.assertEqual(ds[0][1], ('mo_bang_nq28', 0))
        hop = w.mo_bang_tinh_dat(cho=False, dong_chon=[0])
        self.addCleanup(hop.deleteLater)
        hop.o_g.setText('0')
        hop.tinh()
        self.assertFalse(hop.nut_ap.isEnabled())
        self.assertTrue(hop.nut_vi_tri.isEnabled())
        n = hop.cap_nhat_vi_tri_dong()
        self.assertGreater(n, 0)
        dong = w.bo.pa.dat[0]
        self.assertTrue(dong.ap_gia)
        js = json.loads(dong.ap_gia)
        self.assertIn('dia_ban', js)
        self.assertIn('he_so_k1', js)
        self.assertFalse(str(dong.vi_tri).endswith('Không'))
        self.assertGreater(D(dong.he_so_k), 0)
        ts = w._thong_so_dong_dat(0)
        self.assertEqual(ts.get('dia_ban'), js.get('dia_ban'))
        self.assertEqual(ts.get('loai_dat'), dong.loai_dat)
        self.assertTrue(w.luu(tu_dong=True))
        hop.close()
        w.close()
