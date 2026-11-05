"""1.0.68: áp đơn giá đất vào dòng đất: bảng bên phải có mọi hộ, áp hàng loạt, bảo vệ V1, thêm / tự tạo dòng đất, thanh áp giá nhanh ở mục 1. Đất, đồng bộ cửa sổ lập phương án."""
from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from pabt import ap_gia_dat as ap
from pabt import csdl, du_an_moi
from pabt import gia_dat_qd03 as g
from pabt import phien_ban_pa as pb
from pabt import van_ban_can_cu as vb
from pabt.lap_pa import BoSoan, LoiNhap
from pabt.nghiep_vu import DongKhoan, thanh_tien_dat
from pabt.tien import vn

from tests import APP

CHECK = 10                         # Qt.ItemDataRole.CheckStateRole

D = Decimal
XA = 'Tân An'


def _du_an(td: Path, so_ho: int = 3) -> Path:
    dong = [dict(ho_ten=f'Nguyễn Văn Thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i), loai_dat='CLN', dt_thu_hoi=str(100 + i), vi_tri='1') for i in range(so_ho)]
    p = td / 'a.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban=XA, nam='2026'), dong, [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    return p


class CoSo(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.con = csdl.mo(_du_an(Path(self.td.name)))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def xoa_dong_dat(self, ma):
        bo = BoSoan(self.con, ma)
        bo.pa.dat[:] = []
        bo.pa.khoan[4] = []
        bo.luu()


class TestLogic(CoSo):
    def test_doc_dong_ca_du_an_co_ca_ho_chua_co_dong(self):
        self.xoa_dong_dat(self.ma[1])
        hang = ap.doc_dong(self.con)
        self.assertEqual({x.ma_ho for x in hang}, set(self.ma))
        trong = [x for x in hang if x.ma_ho == self.ma[1]]
        self.assertEqual([x.chi_so for x in trong], [ap.CO_CHUA_DONG])
        self.assertIn('Chưa có dòng đất', trong[0].ten_thua)
        self.assertIn('nguyen van thu 0', next(x.tim for x in hang if x.ma_ho == self.ma[0]))

    def test_ap_v0_ghi_chu_du_k_va_tong_tinh_lai(self):
        cu = BoSoan(self.con, self.ma[0]).ket_qua.tong
        hang = [x for x in ap.doc_dong(self.con) if x.ma_ho == self.ma[0]]
        v = g.DauVao(dia_ban='Bảng 54. Xã Tân An', don_gia_bang_gia=D(230000), he_so_k1=D('1.45'), cot_gia='nn_cay')
        kq = g.tinh_don_gia(v)
        self.assertEqual(kq.don_gia_ap_dung, D(333500))
        gc = g.ghi_chu_ap_gia(kq, None, XA)
        r = ap.ap_hang_loat(self.con, hang, kq.don_gia_ap_dung, gc)
        self.assertEqual((r.so_dong, r.so_ho, r.bi_chan), (1, 1, []))
        bo = BoSoan(self.con, self.ma[0])
        d = bo.pa.dat[0]
        self.assertEqual((d.gia_bang_gia, d.he_so_k), (D(333500), D(1)))
        for chu in ('230.000', '1,45 (K1)', '1 (K2)', '1 (K3)', '333.500'):
            self.assertIn(chu, d.ghi_chu)
        self.assertEqual(bo.ket_qua.muc[1], thanh_tien_dat(d.dien_tich, D(333500), 1, d.ty_le, bo.bc.lamtron))
        self.assertNotEqual(bo.ket_qua.tong, cu)
        from pabt import du_lieu_in
        chu_in = str(du_lieu_in.dong_chi_tiet(self.con, self.ma[0])[0])
        self.assertIn('1,45 (K1)', chu_in)                            # thuyết minh đơn giá ra bản in, cột ghi chú

    def test_v1_khong_doi_ap_vao_nhanh_v2(self):
        m = self.ma[0]
        pb.khoa_v1(self.con, m)
        v1_cu = pb.lay(self.con, m, pb.V1)['du_lieu']
        v0_cu = BoSoan(self.con, m).pa.dat[0].gia_bang_gia
        hang = [x for x in ap.doc_dong(self.con) if x.ma_ho == m]
        self.assertEqual(hang[0].dich, ap.V2_MOI)
        r = ap.ap_hang_loat(self.con, hang, D(500000), 'gc')
        self.assertEqual(r.nhanh, {m: 'V2.1'})
        self.assertEqual(pb.lay(self.con, m, pb.V1)['du_lieu'], v1_cu)
        self.assertEqual(BoSoan(self.con, m).pa.dat[0].gia_bang_gia, v0_cu)
        self.assertEqual(pb.doc_pa(self.con, m, 'V2.1').dat[0].gia_bang_gia, D(500000))
        self.assertGreater(pb.tong(self.con, m, 'V2.1'), pb.tong(self.con, m, pb.V1))
        # lần sau: cùng nhánh đang mở, không sinh thêm
        hang = [x for x in ap.doc_dong(self.con) if x.ma_ho == m]
        self.assertEqual(hang[0].dich, 'V2.1')
        ap.ap_hang_loat(self.con, hang, D(600000), 'gc')
        self.assertEqual(pb.v2_moi_nhat(self.con, m), 'V2.1')
        # nhánh đang khóa: nhánh mới, nhánh khóa giữ nguyên
        pb.dat_khoa(self.con, m, 'V2.1', True)
        hang = [x for x in ap.doc_dong(self.con) if x.ma_ho == m]
        self.assertEqual(hang[0].dich, ap.V2_MOI)
        r = ap.ap_hang_loat(self.con, hang, D(700000), 'gc')
        self.assertEqual(r.nhanh, {m: 'V2.2'})
        self.assertEqual(pb.doc_pa(self.con, m, 'V2.1').dat[0].gia_bang_gia, D(600000))

    def test_hang_loat_ho_bi_chan_khong_dung_ho_khac(self):
        hang = ap.doc_dong(self.con)
        that = BoSoan.luu

        def luu(bo, *a, **k):
            if bo.ma_ho == self.ma[1]:
                raise LoiNhap('giả lập: không có quyền')
            return that(bo, *a, **k)
        with mock.patch.object(BoSoan, 'luu', luu):
            r = ap.ap_hang_loat(self.con, hang, D(500000), 'gc')
        self.assertEqual(r.so_ho, 2)
        self.assertEqual(len(r.bi_chan), 1)
        self.assertIn(f'Hộ {self.ma[1]}', r.bi_chan[0])
        self.assertNotEqual(BoSoan(self.con, self.ma[1]).pa.dat[0].gia_bang_gia, D(500000))
        self.assertEqual(BoSoan(self.con, self.ma[2]).pa.dat[0].gia_bang_gia, D(500000))

    def test_dung_giua_chung_giu_ho_da_ap(self):
        hang = ap.doc_dong(self.con)
        r = ap.ap_hang_loat(self.con, hang, D(500000), 'gc', bao_tien_do=lambda k, n: k >= 1)
        self.assertEqual(r.so_ho, 1)
        self.assertIn('còn 2 hộ', r.canh_bao[0])
        self.assertEqual(BoSoan(self.con, self.ma[0]).pa.dat[0].gia_bang_gia, D(500000))
        self.assertNotEqual(BoSoan(self.con, self.ma[1]).pa.dat[0].gia_bang_gia, D(500000))

    def test_lan_da_phe_duyet_khong_sinh_nhanh(self):
        m = self.ma[0]
        pb.khoa_v1(self.con, m)
        with mock.patch('pabt.lan_pa.dang_khoa', return_value=True), mock.patch('pabt.lap_pa._mot_lan_chua_duyet', return_value=False):
            r = ap.ap_hang_loat(self.con, [x for x in ap.doc_dong(self.con) if x.ma_ho == m], D(500000), 'gc')
        self.assertEqual(r.so_dong, 0)
        self.assertIn('quyết định phê duyệt', r.bi_chan[0])
        self.assertEqual(pb.v2_moi_nhat(self.con, m), '')

    def test_dong_doi_tu_may_khac_khong_ap_nham(self):
        hang = [x for x in ap.doc_dong(self.con) if x.ma_ho == self.ma[0]]
        self.xoa_dong_dat(self.ma[0])
        r = ap.ap_hang_loat(self.con, hang, D(500000), 'gc')
        self.assertEqual(r.so_dong, 0)
        self.assertIn('đã đổi', r.bi_chan[0])

    def test_tu_tao_dong_tu_thua(self):
        self.xoa_dong_dat(self.ma[0])
        self.xoa_dong_dat(self.ma[1])
        so_ho, so_dong, cb = ap.tao_dong_tu_thua(self.con, [self.ma[0], self.ma[1], self.ma[2]])
        self.assertEqual((so_ho, so_dong), (2, 2))                  # hộ 3 đã có dòng: không tạo thêm
        d = BoSoan(self.con, self.ma[0]).pa.dat
        self.assertEqual((len(d), d[0].dien_tich, d[0].loai_dat), (1, D(100), 'CLN'))
        self.assertEqual(len(BoSoan(self.con, self.ma[2]).pa.dat), 1)

    def test_tu_tao_dong_ho_co_v1_ghi_nhanh(self):
        m = self.ma[0]
        self.xoa_dong_dat(m)
        pb.khoa_v1(self.con, m)
        self.assertEqual(ap.tao_dong_tu_thua(self.con, [m])[:2], (1, 1))
        self.assertEqual(pb.doc_pa(self.con, m, pb.V1).dat, [])
        self.assertEqual(len(pb.doc_pa(self.con, m, 'V2.1').dat), 1)

    def test_them_dong_thua_moi_va_thua_co_san(self):
        m = self.ma[0]
        d, _ = ap.them_dong_dat(self.con, m, '77', '88', 'CLN', '45,5')
        self.assertEqual((d.dien_tich, d.ten_thua), (D('45.5'), 'Thửa 88 tờ 77'))
        self.assertTrue(self.con.execute('SELECT 1 FROM thua WHERE ma_ho = ? AND so_to = ? AND so_thua = ?', (m, '77', '88')).fetchone())
        bo = BoSoan(self.con, m)
        self.assertEqual(len(bo.pa.dat), 2)
        self.assertEqual(bo.pa.dat[1].dien_tich, D('45.5'))
        n = self.con.execute('SELECT COUNT(*) FROM thua').fetchone()[0]
        ap.them_dong_dat(self.con, m, '77', '88', 'CLN', '10')          # thửa đã có: không tạo thửa trùng
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM thua').fetchone()[0], n)
        for sai in (('', '1', 'CLN', '5'), ('1', '1', '', '5'), ('1', '1', 'CLN', '0'), ('1', '1', 'CLN', 'abc')):
            with self.assertRaises(LoiNhap):
                ap.them_dong_dat(self.con, m, *sai)

    def test_can_cu_gop_khu_trung_13_bac(self):
        goi = g.gg._gan_san()
        self.assertEqual(ap.gop_can_cu(self.con, goi), '')
        so = [x.so_hieu for x in vb.gop_va_sap_xep([vb.doc_can_cu_du_an(self.con)])[1]]
        self.assertIn('03/2026/QĐ-UBND', so)
        self.assertEqual(len(so), len(set(so)))
        chu = vb.doc_can_cu_du_an(self.con)
        ap.gop_can_cu(self.con, goi)
        self.assertEqual(vb.doc_can_cu_du_an(self.con), chu)

    def _dm_dao_tao(self):
        return next(m for m in BoSoan(self.con, self.ma[0]).dm.muc[4] if m.ma == 'CS9')

    def test_dao_tao_theo_thua_tinh_lai_theo_gia_moi(self):
        from pabt import chinh_sach as cs
        m = self.ma[0]
        bo = BoSoan(self.con, m)
        bo.pa.khoan[4] = []
        x = cs.ds_thua_nn(bo, 'CS9')[0]
        bo.pa.khoan[4].append(cs.dong_dao_tao(self._dm_dao_tao(), x['mo_ta'], x['dien_tich'], x['don_gia'], D('1.5')))
        bo.luu()
        bo = BoSoan(self.con, m)
        cu = bo.ket_qua.tong
        bo.ap_don_gia_qd03([0], D(400000), 'gc', 'Mặt tiền Đường A (đoạn từ B đến C)')
        k = bo.pa.dong_ho_tro('CS9')[0]
        self.assertEqual(k.don_gia, D(400000))
        self.assertIn('Đường A', k.ten)                               # mô tả thửa theo vị trí mới
        self.assertTrue(bo.ho_tro_doi)
        self.assertGreater(bo.ket_qua.tong, cu)

    def test_dao_tao_gop_tinh_lai_on_dinh_khong_bi_thay_khi_chi_doi_gia(self):
        m = self.ma[0]
        bo = BoSoan(self.con, m)
        bo.pa.khoan[4] = []
        dm = self._dm_dao_tao()
        bo.pa.khoan[4].append(DongKhoan(muc=4, ma='CS9', ten=dm.ten, dvt='m²', so_luong=D(100), don_gia=D(1), ty_le=None))
        bo.pa.khoan[4].append(DongKhoan(muc=4, ma='CS3', ten='Ổn định đời sống do người lập chọn', dvt='khẩu', so_luong=D(9), don_gia=D(1000)))
        bo.pa.ho.nhan_khau = 4
        bo.luu()
        bo = BoSoan(self.con, m)
        bo.ap_don_gia_qd03([0], D(400000), 'gc')
        self.assertEqual(bo.pa.dong_ho_tro('CS9')[0].don_gia, D(600000))    # 1,5 x giá đất NN
        self.assertEqual(bo.pa.dong_ho_tro('CS3')[0].so_luong, D(9))        # diện tích không đổi: giữ nguyên
        self.assertTrue(bo.tinh_lai_ho_tro())                               # thêm / đổi diện tích thì tính cả ổn định đời sống
        self.assertEqual(bo.pa.dong_ho_tro('CS3') and bo.pa.dong_ho_tro('CS3')[0].so_luong or D(4), D(4))

    def test_nhom_theo_loai_dat(self):
        goi = g.gg._gan_san()
        self.assertEqual(g.nhom_theo_loai_dat('HNK', goi)['cot_gia'], 'nn_cay')
        self.assertEqual(g.nhom_theo_loai_dat('ONT', goi)['ma'], 'DAT_O')
        self.assertEqual(g.nhom_theo_loai_dat('RSX', goi)['cot_gia'], 'nn_rung_nts')
        self.assertIsNone(g.nhom_theo_loai_dat('ZZZ', goi))
        self.assertIsNone(g.nhom_theo_loai_dat('', goi))


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestBangTinh(CoSo):
    def _hop(self, ds=(), **kw):
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        h = HopTinhGiaDat(None, self.con, list(ds), XA, False, **kw)
        h.im_lang = True
        self.addCleanup(h.close)
        return h

    @staticmethod
    def _o(h, r, c):
        return h.mo_hinh.data(h.mo_hinh.index(r, c))

    def test_chua_chon_ho_van_co_du_dong_de_tich(self):
        from pabt.man_hinh_tinh_gia_dat import TAT_CA
        h = self._hop()
        self.assertEqual(h.cb_pham_vi.currentData(), TAT_CA)
        self.assertEqual(h.bang.rowCount(), 3)
        self.assertNotIn('Chưa chọn hộ', h.lb_ho.text())
        self.assertFalse(h.nut_ap.isEnabled())                       # không tích sẵn cả dự án
        self.assertEqual(h.dong_da_chon(), [])
        h.mo_hinh.setData(h.mo_hinh.index(1, 0), 2, CHECK)
        self.assertTrue(h.nut_ap.isEnabled())
        self.assertIn('1 dòng', h.nut_ap.text())

    def test_pham_vi_va_loc_khong_dau(self):
        from pabt.man_hinh_tinh_gia_dat import DANG_CHON
        h = self._hop(self.ma[:2])
        self.assertEqual(h.cb_pham_vi.currentData(), DANG_CHON)
        self.assertEqual(h.bang.rowCount(), 2)
        self.assertEqual(len(h.dong_da_chon()), 2)
        h.cb_pham_vi.setCurrentIndex(h.cb_pham_vi.findData(self.ma[2]))
        self.assertEqual(h.bang.rowCount(), 1)
        self.assertEqual(h.dong_da_chon(), [])
        self.assertIn('2 dòng đã tích đang bị che', h.lb_ho.text())
        h.cb_pham_vi.setCurrentIndex(0)
        self.assertEqual(h.bang.rowCount(), 3)
        for tu, n in (('nguyen', 3), ('NGUYỄN', 3), ('thử', 3), ('101', 1), ('11 101', 1), ('cln', 3), ('khong co', 0)):
            h.o_loc.setText(tu)
            self.assertEqual(h.bang.rowCount(), n, tu)
        h.o_loc.setText('102')
        h.chon_het(True)
        self.assertEqual(len(h.dong_da_chon()), 1)
        self.assertEqual(len(h.mo_hinh.tich), 3)
        h.chon_het(False)
        self.assertEqual(h.dong_da_chon(), [])
        self.assertEqual(len(h.mo_hinh.tich), 2)                     # bỏ chọn chỉ dòng đang hiện

    def test_gia_moi_cap_nhat_ngay_o_dong_tich(self):
        from pabt.man_hinh_tinh_gia_dat import C_MOI, C_TIEN
        h = self._hop(self.ma[:1])
        h.cb_pham_vi.setCurrentIndex(0)
        h.o_loc.setText('')
        h.cb_ket_cau.setCurrentIndex(0)
        tich = next(r for r in range(h.bang.rowCount()) if h.mo_hinh.dong[r].ma_ho == self.ma[0])
        khac = next(r for r in range(h.bang.rowCount()) if h.mo_hinh.dong[r].ma_ho != self.ma[0])
        h.o_g.setText('230000')
        gia = h.kq.don_gia_ap_dung
        self.assertEqual(self._o(h, tich, C_MOI), vn(gia))
        x = h.mo_hinh.dong[tich]
        self.assertEqual(self._o(h, tich, C_TIEN), vn(thanh_tien_dat(x.dien_tich, gia, 1, x.ty_le, h.mo_hinh.lamtron)))
        self.assertEqual(self._o(h, khac, C_MOI), '')                 # dòng chưa tích: trống
        h.o_g.setText('300000')
        self.assertNotEqual(h.kq.don_gia_ap_dung, gia)
        self.assertEqual(self._o(h, tich, C_MOI), vn(h.kq.don_gia_ap_dung))
        h.cb_ket_cau.setCurrentIndex(1)                               # đổi mặt đường: đất NN K3 = 0,90, cột đổi theo
        self.assertEqual(self._o(h, tich, C_MOI), vn(h.kq.don_gia_ap_dung))
        h.o_g.setText('abc')
        self.assertFalse(h.nut_ap.isEnabled())
        self.assertEqual(self._o(h, tich, C_MOI), '')                 # ô sai: không để số cũ

    def test_ap_hang_loat_o_lai_doc_lai_gop_can_cu(self):
        h = self._hop()
        h.chon_het(True)
        h.o_g.setText('400000')
        gia = h.kq.don_gia_ap_dung
        self.assertEqual(h.ap_gia(xac_nhan=True), (3, 3, []))
        self.assertEqual(h.ket_qua_ap, (3, 3))
        self.assertFalse(h.result())                                  # vẫn mở để áp tiếp đoạn đường khác
        self.assertEqual(h.dong_da_chon(), [])                        # bỏ tích dòng vừa áp
        self.assertEqual(h.mo_hinh.dong[0].gia_hien_tai, gia)
        self.assertEqual(BoSoan(self.con, self.ma[2]).pa.dat[0].gia_bang_gia, gia)
        self.assertIn('03/2026/QĐ-UBND', vb.doc_can_cu_du_an(self.con))
        self.assertIn('Đã áp', h.lb_ap_ket_qua.text())

    def test_v1_bao_chuyen_nhanh_bang_hop_ket_qua(self):
        pb.khoa_v1(self.con, self.ma[0])
        v1 = pb.lay(self.con, self.ma[0], pb.V1)['du_lieu']
        h = self._hop(self.ma[:2])
        h.o_g.setText('400000')
        with mock.patch('pabt.man_hinh_tinh_gia_dat.hop_ket_qua') as hop:
            h.im_lang = False
            h.ap_gia(xac_nhan=True)
            h.im_lang = True
        hop.assert_called_once()
        self.assertTrue(any('V1 đã niêm yết giữ nguyên' in c and 'V2.1' in c for c in hop.call_args[0][2]))
        self.assertEqual(pb.lay(self.con, self.ma[0], pb.V1)['du_lieu'], v1)
        self.assertEqual(json.loads(pb.lay(self.con, self.ma[0], 'V2.1')['du_lieu'])['dat'][0]['gia_bang_gia'], str(h.kq.don_gia_ap_dung))

    def test_hop_tien_do_chi_khi_nhieu_ho(self):
        from PySide6.QtWidgets import QProgressDialog
        h = self._hop()
        h.im_lang = False
        self.assertIsNone(h._hop_tien_do(3))
        bao = h._hop_tien_do(60)
        self.assertFalse(bao(1, 60))
        hop = h.findChild(QProgressDialog)
        hop.cancel()
        self.assertTrue(bao(2, 60))
        hop.deleteLater()
        h.im_lang = True

    def test_nhan_lech_nhom_dat(self):
        h = self._hop(self.ma[:1])
        h.cb_nhom.setCurrentIndex(h.cb_nhom.findData('DAT_O|dat_o'))
        self.assertIn('khác nhóm đất', h.lb_ho.text())
        h.cb_nhom.setCurrentIndex(0)
        self.assertNotIn('khác nhóm đất', h.lb_ho.text())

    def test_tu_chon_nhom_theo_dong_tich_san(self):
        ap.them_dong_dat(self.con, self.ma[0], '5', '6', 'ONT', '10')
        h = self._hop(self.ma[:1], bo_mo=BoSoan(self.con, self.ma[0]), dong_tich=[1])
        self.assertEqual(h.nhom_cot(), ('DAT_O', 'dat_o'))
        self.assertEqual(len(h.dong_da_chon()), 1)
        self.assertEqual(h.cb_pham_vi.currentData(), self.ma[0])

    def test_nut_them_va_tu_tao(self):
        self.xoa_dong_dat(self.ma[0])
        h = self._hop()
        self.assertIn('hộ chưa có dòng đất', h.lb_ho.text())
        self.assertEqual(h.tu_tao_dong(xac_nhan=True)[:2], (1, 1))
        self.assertEqual(len(h.dong_da_chon()), 1)
        self.assertEqual(h.tu_tao_dong(xac_nhan=True)[:2], (0, 0))     # không còn hộ trống
        d = h.them_dong((self.ma[1], '9', '9', 'CLN', '12'))
        self.assertIsNotNone(d)
        self.assertEqual(len(h.dong_da_chon()), 2)
        self.assertIsNone(h.them_dong((self.ma[1], '9', '9', 'CLN', 'abc')))
        self.assertIn('Diện tích', h.lb_ap_ket_qua.text())
        hop = h.them_dong()                                           # im_lang: trả hộp nhập
        self.addCleanup(hop.close)
        hop.o_to.setText('3')
        self.assertEqual(hop.gia_tri()[1], '3')
        self.assertEqual(hop.gia_tri()[3], 'CLN')

    def test_chi_xem_tat_nut_ghi(self):
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        h = HopTinhGiaDat(None, self.con, list(self.ma), XA, True)
        h.im_lang = True
        self.addCleanup(h.close)
        self.assertGreater(h.bang.rowCount(), 0)
        for b in (h.nut_ap, h.nut_them_dong, h.nut_tu_tao):
            self.assertFalse(b.isEnabled())


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestThanhNhanhVaCuaSo(CoSo):
    def _cua_so(self, ma=None):
        from pabt.man_hinh import CuaSoLapPA, the_cua
        w = CuaSoLapPA(self.con, ma or self.ma[0])
        w.im_lang = True
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        w.tab.setCurrentIndex(the_cua(1))
        w.bang[1].thanh_gia.nap()
        w.bang[1].bang.selectRow(0)
        return w

    def _chon_doan(self, t, chu='Cầu Chùm Bao → Cầu Bà Giá'):
        t.cb_doan.setCurrentIndex(next(k for k in range(t.cb_doan.count()) if chu in t.cb_doan.itemText(k)))

    def test_doan_duong_theo_xa_du_an_va_cong_thuc(self):
        w = self._cua_so()
        t = w.bang[1].thanh_gia
        self.assertEqual(t.cb_doan.count(), 26)                      # chỉ đoạn của Xã Tân An
        self._chon_doan(t)
        self.assertEqual(t.kq.k1, D('1.32'))                         # đất CLN: K1 nông nghiệp
        self.assertIn('× 1,32 =', t.lb_ct.text())
        self.assertIn('đ/m²', t.lb_ct.text())
        self.assertEqual(D(t.o_g.text().replace('.', '')), t.kq.don_gia_nq28)
        cu = t.kq.don_gia_ap_dung
        t.cb_ket_cau.setCurrentIndex(1)                               # đường đất, sỏi: K3 = 0,90
        self.assertEqual(t.kq.k3, D('0.90'))
        self.assertLess(t.kq.don_gia_ap_dung, cu)
        t.cb_vi_tri.setCurrentIndex(2)
        self.assertNotEqual(t.kq.don_gia_nq28, D(0))

    def test_tuyen_co_quy_dinh_rieng_k3_tu_khoa(self):
        import copy
        w = self._cua_so()
        t = w.bang[1].thanh_gia
        t.goi = copy.deepcopy(t.goi)                                  # dữ liệu gắn sẵn chưa có tuyến nào đánh dấu: đặt trên bản sao
        self._chon_doan(t)
        t._doan()[1]['co_quy_dinh_rieng_duong_dat_tai_pl1'] = True
        t.cb_ket_cau.setCurrentIndex(1)                               # đường đất, nhưng tuyến có quy định riêng ở PL I.2
        self.assertEqual(t.kq.k3, 1)
        self.assertTrue(t.kq.canh_bao)
        self.assertIn('(!)', t.lb_ct.text())
        self.assertIn('!', t.lb_ct.toolTip())

    def test_ap_vao_dong_chon_cap_nhat_bang_khong_mo_lai(self):
        w = self._cua_so()
        t = w.bang[1].thanh_gia
        self._chon_doan(t)
        bo = w.bo
        self.assertEqual(t.ap_dong_chon(), 1)
        self.assertIs(w.bo, bo)
        d = bo.pa.dat[0]
        self.assertEqual(d.gia_bang_gia, t.kq.don_gia_ap_dung)
        self.assertIn('Cầu Chùm Bao', d.vi_tri)
        c = [x[0] for x in w.bang[1].cot].index('gia_bang_gia')
        self.assertEqual(w.bang[1].bang.item(0, c).text(), vn(d.gia_bang_gia))
        self.assertTrue(bo.co_thay_doi)
        w.luu()
        self.assertEqual(BoSoan(self.con, self.ma[0]).pa.dat[0].gia_bang_gia, d.gia_bang_gia)
        self.assertIn('03/2026/QĐ-UBND', vb.doc_can_cu_du_an(self.con))

    def test_gia_go_tay_va_dong_nhieu_nhom(self):
        ap.them_dong_dat(self.con, self.ma[0], '5', '6', 'ONT', '10')
        w = self._cua_so()
        t = w.bang[1].thanh_gia
        self._chon_doan(t)
        self.assertEqual(t.ap_dong_chon([0, 1]), 2)
        d0, d1 = w.bo.pa.dat
        self.assertNotEqual(d0.gia_bang_gia, d1.gia_bang_gia)         # mỗi dòng theo nhóm đất của nó
        t.o_g.setText('100000')
        t._go_gia()
        self.assertEqual(t.kq.don_gia_nq28, D(100000))
        t.o_g.setText('abc')
        t._go_gia()
        self.assertIsNone(t.kq)
        self.assertFalse(t.b_ap.isEnabled())

    def test_them_thanh_dong_moi(self):
        ap.them_dong_dat(self.con, self.ma[0], '5', '6', 'CLN', '10')
        w = self._cua_so()
        t = w.bang[1].thanh_gia
        self._chon_doan(t)
        n = len(w.bo.pa.dat)
        i = t.them_dong_moi(w.bo.pa.dat[0].ma_thua)
        self.assertEqual((i, len(w.bo.pa.dat)), (n, n + 1))
        self.assertEqual(w.bo.pa.dat[i].gia_bang_gia, t.kq.don_gia_ap_dung)
        self.assertEqual(w.bang[1].bang.rowCount(), n + 1)

    def test_dang_xem_v1_khoa_ap_thi_chuyen_v2(self):
        m = self.ma[0]
        pb.khoa_v1(self.con, m)
        v1 = pb.lay(self.con, m, pb.V1)['du_lieu']
        w = self._cua_so()
        w.thanh_pb.chon(pb.V1)
        self.assertTrue(w.bo.khoa)
        t = w.bang[1].thanh_gia
        self.assertTrue(t.b_ap.isEnabled() or not t.kq)
        self._chon_doan(t)
        self.assertTrue(t.b_ap.isEnabled())
        self.assertEqual(t.ap_dong_chon([0]), 1)
        self.assertEqual(w.bo.phien_ban, 'V2.1')
        self.assertFalse(w.bo.khoa)
        w.luu()
        self.assertEqual(pb.lay(self.con, m, pb.V1)['du_lieu'], v1)
        self.assertEqual(pb.doc_pa(self.con, m, 'V2.1').dat[0].gia_bang_gia, t.kq.don_gia_ap_dung)

    def test_lan_da_phe_duyet_tat_thanh(self):
        w = self._cua_so()
        w.bo.khoa = True
        self.assertFalse(w.co_the_ap_gia_dat())
        w.bang[1].thanh_gia.cap_nhat_khoa()
        self.assertFalse(w.bang[1].thanh_gia.b_ap.isEnabled())
        self.assertFalse(w.dam_bao_sua_dat())
        w.bo.khoa = False

    def test_mo_bang_day_du_chon_san_ho_dong_va_ap_ve_cua_so(self):
        from pabt.man_hinh import CHU_BANG_TINH_DAT
        ap.them_dong_dat(self.con, self.ma[0], '5', '6', 'CLN', '10')
        w = self._cua_so()
        self.assertIn(CHU_BANG_TINH_DAT, w.bang[1].nut)
        self.assertEqual(w.bang[1].nut[CHU_BANG_TINH_DAT].text(), 'Mở bảng tính đầy đủ (NQ 28 && QĐ 03)')     # "&" hiện đúng, không thành phím tắt
        self.assertIn('Mở bảng tính đầy đủ (NQ 28 && QĐ 03)…', [a.text() for a in w.bang[1].menu_dong().actions()])
        t = w.bang[1].thanh_gia
        self._chon_doan(t)
        w.bang[1].bang.selectRow(1)
        bo = w.bo
        h = w.mo_bang_tinh_dat(cho=False)
        self.addCleanup(h.close)
        self.assertEqual(h.cb_pham_vi.currentData(), self.ma[0])
        self.assertEqual([x.chi_so for x in h.dong_da_chon()], [1])    # dòng đang thao tác
        self.assertEqual(h.cb_doan.currentData(), t._doan()[1]['ma_doan_duong'])   # thông số thanh nhanh sang theo
        h.o_g.setText('555000')
        gia = h.kq.don_gia_ap_dung
        gia_0 = bo.pa.dat[0].gia_bang_gia
        self.assertEqual(h.ap_gia(xac_nhan=True)[:2], (1, 1))
        self.assertIs(w.bo, bo)
        self.assertEqual(bo.pa.dat[1].gia_bang_gia, gia)               # ghi vào bộ soạn của cửa sổ
        self.assertEqual(bo.pa.dat[0].gia_bang_gia, gia_0)
        c = [x[0] for x in w.bang[1].cot].index('gia_bang_gia')
        self.assertEqual(w.bang[1].bang.item(1, c).text(), vn(gia))
        self.assertEqual(h.result(), 1)                                # áp xong trở về bảng Đất

    def test_mo_tu_v1_khoa_ap_vao_nhanh(self):
        m = self.ma[0]
        pb.khoa_v1(self.con, m)
        v1 = pb.lay(self.con, m, pb.V1)['du_lieu']
        w = self._cua_so()
        w.thanh_pb.chon(pb.V1)
        w.bang[1].bang.selectRow(0)
        h = w.mo_bang_tinh_dat(cho=False)
        self.addCleanup(h.close)
        h.o_g.setText('555000')
        self.assertEqual(h.ap_gia(xac_nhan=True)[:2], (1, 1))
        self.assertEqual(w.bo.phien_ban, 'V2.1')
        w.luu()
        self.assertEqual(pb.lay(self.con, m, pb.V1)['du_lieu'], v1)


if __name__ == '__main__':
    unittest.main()
