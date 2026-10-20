"""1.0.05 - nhiều lần lập phương án chi tiết cho một hộ (lần đầu + bổ sung), mỗi lần một quyết định; lần đã duyệt khóa; tổng hộ cộng
dồn. Số liệu GIẢ LẬP."""
from __future__ import annotations

import sqlite3
import unittest

import openpyxl

from pabt import csdl, in_an, kinh_phi_du_an, lan_pa, nghiep_vu, theo_doi
from pabt.lap_pa import BoSoan, LoiNhap
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

    def _them(self, bo, muc, sl):
        m = bo.dm.muc[muc][0]
        bo.them_tu_danh_muc(muc, m)
        bo.pa.khoan[muc][-1].so_luong = D(sl)


class TestNhieuLan(_Co):
    def test_csdl_v17(self):
        con = self._con()
        self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        self.assertGreaterEqual(csdl.PHIEN_BAN_CSDL, 17)
        for bang in ('ct_dat', 'ct_khoan', 'qd_ho'):
            self.assertIn('lan', [r[1] for r in con.execute(f'PRAGMA table_info({bang})')])
        self.assertTrue(lan_pa.co_bang(con))
        b = sqlite3.connect(str(csdl.Path(nghiep_vu.__file__).with_name('bo_don_gia.sqlite')))
        self.assertEqual(b.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)   # bộ đơn giá đóng gói cùng lược đồ
        b.close()

    def test_bon_lan_bon_quyet_dinh_cong_don(self):
        con = self._con()
        ma = 1
        tong_lan = []
        for i in range(4):
            bo = BoSoan(con, ma)
            if i:
                self.assertTrue(BoSoan(con, ma, lan=i).khoa)               # lần trước đã duyệt: khóa
                self.assertEqual(bo.lan, i)                                # mặc định mở lần cuối (khóa) -> lập bổ sung
                bo.lap_bo_sung(f'Bổ sung {i}')
            self.assertEqual(bo.lan, i + 1)
            self.assertFalse(bo.khoa)
            self._them(bo, 2 if i % 2 == 0 else 3, 2 + i)
            bo.luu()
            tong_lan.append(nghiep_vu.tinh_lan(con, ma, i + 1).tong)
            qd = theo_doi.luu_qd(con, None, f'{i + 1:02d}/QĐ-UBND', f'0{i + 1}/10/2026')
            theo_doi.them_ho_theo_pa(con, qd, [ma])
            r = con.execute('SELECT so_tien, lan FROM qd_ho WHERE qd_id = ? AND ma_ho = ?', (qd, ma)).fetchone()
            self.assertEqual((D(r['so_tien']), r['lan']), (tong_lan[-1], i + 1))   # QĐ lần k = đúng tiền lần k
        ds = lan_pa.ds_lan(con, ma)
        self.assertEqual([x.lan for x in ds], [1, 2, 3, 4])
        self.assertTrue(all(x.khoa and x.qd for x in ds))
        self.assertEqual(sum(tong_lan, D(0)), nghiep_vu.tinh_ho(con, ma).tong)     # cộng dồn = tổng của hộ
        th = lan_pa.tong_hop_ho(con, ma)
        self.assertEqual((th['so_lan'], th['so_da_duyet'], th['chua_duyet']), (4, 4, []))
        x = theo_doi.tong_hop(con, [ma])[0]
        self.assertEqual((x.so_lan, len(x.qd)), (4, 4))
        self.assertEqual(x.tong_phe_duyet, x.tong_pa)
        cc = kinh_phi_du_an.co_cau(con)
        cong = next(d for d in cc['dong'] if d['loai'] == 'cong')
        self.assertEqual(cong['chenh'], 0)                                  # hộ đã duyệt hết: không lệch PA - QĐ

    def test_khoa_khong_mat_du_lieu_lan_cu(self):
        con = self._con()
        ma = 1
        bo = BoSoan(con, ma)
        self._them(bo, 2, 5)
        bo.luu()
        dong_1 = [tuple(r) for r in con.execute('SELECT * FROM ct_khoan WHERE ma_ho = ? AND lan = 1 ORDER BY id', (ma,))]
        qd = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, [ma])
        bo = BoSoan(con, ma)
        self.assertTrue(bo.khoa)
        bo.pa.khoan[2].clear()
        with self.assertRaises(LoiNhap):
            bo.luu()                                                       # lần đã duyệt: không lưu được
        bo.mo(ma)
        bo.lap_bo_sung()
        self._them(bo, 3, 4)
        bo.luu()
        self.assertEqual([tuple(r) for r in con.execute('SELECT * FROM ct_khoan WHERE ma_ho = ? AND lan = 1 ORDER BY id', (ma,))],
                         dong_1)                                           # dòng lần 1 nguyên vẹn
        # chưa duyệt lần 2: tiến độ cảnh báo, kinh phí "chưa phê duyệt" đúng phần lần 2
        x = theo_doi.tong_hop(con, [ma])[0]
        self.assertEqual(x.lan_chua_duyet, [2])
        self.assertIn('bổ sung lần 2', x.trang_thai)
        cc = kinh_phi_du_an.co_cau(con)
        cong = next(d for d in cc['dong'] if d['loai'] == 'cong')
        self.assertEqual(cong['chenh'], 0)
        self.assertGreaterEqual(cong['chua_pd'], nghiep_vu.tinh_lan(con, ma, 2).tong)
        # bỏ hộ khỏi quyết định: lần 1 mở khóa lại
        theo_doi.bo_ho_khoi_qd(con, qd, ma)
        self.assertFalse(lan_pa.dang_khoa(con, ma, 1))

    def test_mo_khoa_va_xoa_lan(self):
        con = self._con()
        ma = 2
        bo = BoSoan(con, ma)
        qd = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, [ma])
        lan_pa.mo_khoa_sua(con, ma, 1)
        bo = BoSoan(con, ma, lan=1)
        self.assertFalse(bo.khoa)
        self._them(bo, 2, 1)
        bo.luu()                                                           # điều chỉnh lần đã duyệt
        lan = lan_pa.tao_lan_moi(con, ma)
        with self.assertRaises(LoiNhap):
            lan_pa.xoa_lan(con, ma, 1)
        lan_pa.xoa_lan(con, ma, lan)
        self.assertEqual([x.lan for x in lan_pa.ds_lan(con, ma)], [1])

    def test_thuong_tinh_mot_lan(self):
        con = self._con()
        ma = 1
        bo = BoSoan(con, ma)
        bo.luu()
        bo.lap_bo_sung()
        self._them(bo, 2, 3)
        bo.luu()
        k1, k2 = nghiep_vu.tinh_lan(con, ma, 1), nghiep_vu.tinh_lan(con, ma, 2)
        tong = nghiep_vu.tinh_ho(con, ma)
        self.assertEqual(k1.muc[5] + k2.muc[5], tong.muc[5])

    def test_ban_in_lan_bo_sung(self):
        con = self._con()
        ma = 1
        bo = BoSoan(con, ma)
        bo.luu()
        lan_pa.sua_lan(con, ma, 1, so_pa='05', ngay_pa='01/10/2026')
        bo.lap_bo_sung('Bổ sung nhà')
        self._them(bo, 2, 2)
        bo.luu()
        lan_pa.sua_lan(con, ma, 2, so_pa='77')
        ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, ma, self.td / 'bs.xlsx')).active
        chu = ' | '.join(str(c.value) for r in ws.iter_rows(max_row=8) for c in r if c.value)
        self.assertIn('BỔ SUNG (LẦN 2)', chu)
        self.assertIn('77/', chu)
        dong, kq = in_an.dong_chi_tiet(con, ma, pa=nghiep_vu.doc_phuong_an(con, ma, lan=2),
                                       pa_truoc=nghiep_vu.doc_phuong_an(con, ma, den_lan=1))
        self.assertEqual(kq.muc[1], 0)                                     # bổ sung không lặp tiền đất của lần đầu
        ws1 = openpyxl.load_workbook(in_an.lap_chi_tiet(con, ma, self.td / 'l1.xlsx', lan=1)).active
        self.assertNotIn('BỔ SUNG', ' '.join(str(c.value) for r in ws1.iter_rows(max_row=8) for c in r if c.value))
        bth = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx', [ma], lan='moi_nhat')).active
        tong_bth = next(bth.cell(r, 22).value for r in range(13, 30) if isinstance(bth.cell(r, 22).value, (int, float)))
        self.assertEqual(D(tong_bth), nghiep_vu.tinh_lan(con, ma, 2).tong)

    def test_nang_cap_tu_v16(self):
        """File v16 có hộ đã có quyết định: lần 1 khóa, mọi dòng cũ là lần 1."""
        con = self._con()
        qd = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        theo_doi.ghi_qd_ho(con, qd, 1, {'so_tien': '100'})
        with con:
            con.execute('DELETE FROM pa_lan')
            con.execute('UPDATE qd_ho SET lan = 0')
        with con:
            csdl._tao_pa_lan(con)
        self.assertTrue(lan_pa.dang_khoa(con, 1, 1))
        self.assertFalse(lan_pa.dang_khoa(con, 2, 1))


class TestKichBan210(_Co):
    """Kịch bản người dùng (19/10/2026): hộ A lần 1 = đất 100tr + nhà 50tr (QĐ 01), lần 2 = cây 30tr + hỗ trợ 20tr (QĐ 02), lần 3 =
    10tr (QĐ 03) -> cộng dồn 210 triệu, vẫn MỘT hộ. Biểu thưởng để trống (thưởng tính tự động theo bậc, không phải dòng nhập)."""

    def _ghi(self, bo, dat=None, khoan=()):
        from pabt.nghiep_vu import NGUON_TAY, DongDat, DongKhoan
        bo.pa.dat.clear()
        for m in bo.pa.khoan:
            bo.pa.khoan[m].clear()
        if dat:
            mt, dt, gia = dat
            bo.pa.dat.append(DongDat(ma_thua=mt, loai_dat='ONT', nhom_dat='Đất ở', dien_tich=D(dt), gia_bang_gia=D(gia)))
        for muc, ten, tien in khoan:
            bo.pa.khoan[muc].append(DongKhoan(muc=muc, ten=ten, dvt='đồng', so_luong=D(1), don_gia=D(tien), nguon_gia=NGUON_TAY))
        bo.luu()

    def test_ba_lan_ba_quyet_dinh_210_trieu(self):
        con = self._con(3)
        with con, csdl.mo_khoa_danh_muc(con):
            con.execute('DELETE FROM bieu_thuong')
        ma = con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        mt = con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ? LIMIT 1', (ma,)).fetchone()[0]
        so_ho = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        TR = 1000000
        # lần 1: đất 100tr + nhà 50tr -> QĐ 01
        bo = BoSoan(con, ma)
        self._ghi(bo, (mt, '100', str(TR)), [(2, 'Nhà ở', 50 * TR)])
        q1 = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        self.assertEqual(theo_doi.them_ho_theo_pa(con, q1, [ma], lan=1), 1)
        self.assertTrue(lan_pa.dang_khoa(con, ma, 1))
        # lần 2: cây 30tr + hỗ trợ 20tr -> QĐ 02
        bo = BoSoan(con, ma)
        bo.lap_bo_sung('Bổ sung cây trồng, hỗ trợ')
        self._ghi(bo, None, [(3, 'Cây ăn quả', 30 * TR), (4, 'Hỗ trợ khác', 20 * TR)])
        self.assertEqual(nghiep_vu.tinh_lan(con, ma, 1).tong, D(150 * TR))         # lần 1 nguyên vẹn
        self.assertEqual(nghiep_vu.tinh_pa_lan(con, ma, 2).tong, D(50 * TR))       # cách gọi (con, ma_ho, lan, bc)
        q2 = theo_doi.luu_qd(con, None, '02/QĐ-UBND', '05/10/2026')
        theo_doi.them_ho_theo_pa(con, q2, [ma], lan=2)
        self.assertTrue(lan_pa.dang_khoa(con, ma, 2))
        # lần 3: 10tr -> QĐ 03
        bo = BoSoan(con, ma)
        bo.lap_bo_sung()
        self._ghi(bo, None, [(4, 'Hỗ trợ bổ sung', 10 * TR)])
        q3 = theo_doi.luu_qd(con, None, '03/QĐ-UBND', '10/10/2026')
        theo_doi.them_ho_theo_pa(con, q3, [ma], lan=3)
        self.assertTrue(lan_pa.dang_khoa(con, ma, 3))
        # cộng dồn 210 triệu, vẫn một hộ
        self.assertEqual(nghiep_vu.tinh_pa(nghiep_vu.doc_phuong_an(con, ma), nghiep_vu.BoiCanh.tu(con)).tong, D(210 * TR))
        self.assertEqual(nghiep_vu.ket_qua_ho(con)[ma][0].tong, D(210 * TR))
        self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], so_ho)
        tien = [D(r[0]) for r in con.execute('SELECT so_tien FROM qd_ho WHERE ma_ho = ? ORDER BY lan', (ma,))]
        self.assertEqual(tien, [D(150 * TR), D(50 * TR), D(10 * TR)])
        th = lan_pa.tong_hop_cac_lan(con, ma)
        self.assertEqual((th['so_lan'], th['so_da_duyet'], th['tong_cong_don']), (3, 3, D(210 * TR)))
        self.assertEqual(th['tien_tung_lan'], {1: D(150 * TR), 2: D(50 * TR), 3: D(10 * TR)})
        # cố ý sửa lần 1 đã khóa -> LoiNhap
        bo = BoSoan(con, ma, lan=1)
        bo.pa.khoan[2][0].don_gia = D(1)
        with self.assertRaises(LoiNhap):
            bo.luu()
        self.assertEqual(nghiep_vu.tinh_lan(con, ma, 1).tong, D(150 * TR))
        # thêm hộ vào QĐ với lần đã có quyết định khác: bỏ qua (không trùng tiền)
        q4 = theo_doi.luu_qd(con, None, '04/QĐ-UBND', '11/10/2026')
        self.assertEqual(theo_doi.them_ho_theo_pa(con, q4, [ma], lan=1), 0)
        self.assertEqual(lan_pa.lan_hien_tai(con, ma).lan, 3)
        self.assertEqual(lan_pa.ds_lan(con, ma)[0].ten, lan_pa.TEN_LAN_GOC)

    def test_mo_khoa_co_ly_do(self):
        con = self._con(2)
        ma = 1
        q = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, q, [ma])
        lan_pa.mo_khoa_lan(con, ma, 1, 'Điều chỉnh diện tích theo trích đo')
        self.assertFalse(lan_pa.dang_khoa(con, ma, 1))
        nk = con.execute("SELECT viec || ' ' || chi_tiet FROM nhat_ky ORDER BY id DESC").fetchone()[0]
        self.assertIn('Điều chỉnh diện tích', nk)
        lan_pa.khoa_lai(con, ma, 1)
        self.assertTrue(lan_pa.dang_khoa(con, ma, 1))


class TestGiaoDien(_Co):
    def test_cua_so_lap_pa_dai_lan(self):
        from pabt.man_hinh import CuaSoLapPA
        con = self._con()
        c = CuaSoLapPA(con, 1)
        c.im_lang = True

        def don():
            c.bo_thay_doi()
            c.close()
        self.addCleanup(don)
        self.assertEqual(c.cb_lan.count(), 1)
        qd = theo_doi.luu_qd(con, None, '01/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, [1])
        c.bo.mo(1)
        c.nap_ho()
        self.assertTrue(c.bo.khoa)
        self.assertFalse(c.b_luu.isEnabled())
        self.assertFalse(c.bang[2].hang.o_sl.isEnabled())
        self.assertIn('CHỈ XEM', c.lb_trang_thai_lan.text())
        self.assertIn('ĐÃ PHÊ DUYỆT', c.lb_trang_thai_lan.text())
        self.assertEqual(c.lap_bo_sung('Bổ sung cây'), 2)
        self.assertEqual(c.cb_lan.count(), 2)
        self.assertTrue(c.bang[2].hang.o_sl.isEnabled())
        self._them(c.bo, 2, 3)
        c.cap_nhat()
        self.assertTrue(c.luu())
        self.assertIn('TỔNG CỘNG DỒN CẢ HỘ (2 LẦN)', c.lb_tong_cong_don.text())
        self.assertIn('ĐANG LẬP DỰ THẢO', c.lb_trang_thai_lan.text())
        self.assertEqual(c.bo.tinh_cong_don().tong, c.bo.ket_qua_cong_don.tong)
        self.assertTrue(c.chuyen_lan(1))   # tên trong đặc tả = chon_lan
        self.assertTrue(c.bo.khoa)
        c._ap_trang_thai_khoa()
        self.assertFalse(c.b_luu.isEnabled())
        self.assertTrue(c.sua_lan(dict(ten='Lần đầu', so_pa='01')))
        self.assertEqual(lan_pa.lan_cua(con, 1, 1).so_pa, '01')

    def test_hop_in_chon_lan(self):
        from pabt.man_hinh import HopIn
        con = self._con()
        bo = BoSoan(con, 1)
        bo.lap_bo_sung()
        self._them(bo, 2, 1)
        bo.luu()
        h = HopIn(con, None, [1])
        self.addCleanup(h.close)
        self.assertEqual(h.so_ho_nhieu_lan, 1)
        self.assertEqual(h.lan_in(), 'moi_nhat')


if __name__ == '__main__':
    unittest.main()
