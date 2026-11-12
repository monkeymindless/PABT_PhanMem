"""1.1.07 (đợt D) - nhập gói cài ở chế độ "Mở để sửa và kiểm định trước khi lưu": KHÔNG ghi gì; đơn giá đất của xã đã chọn lên bảng
xem trước của thẻ con Đọc văn bản (kiểm định tô dòng), hệ số K lên thẻ Hệ số K (chưa lưu), bộ quy tắc thành gói nháp. Lưu bằng đúng các
nút sẵn có."""
from __future__ import annotations

from pathlib import Path

from pabt import gia_dat_nq28 as nq
from pabt import goi_gia_dat as gg
from pabt import he_so_k
from tests import test_1106_goi_cai as _c                     # nhập module (nhập tên lớp test thì discover chạy lại lớp đó)
from tests import test_goi_gia_dat as _g


class TestSuaGoiCai(_g.CoMay):
    _dong_gia = _g.TestGoiCaiGiaDat._dong_gia
    _dong_k = _g.TestGoiCaiGiaDat._dong_k
    _nap_cap = _g.TestGoiCaiGiaDat._nap_cap
    _goi_ba_xa = _c.TestNhapTheoXa._goi_ba_xa
    _may_moi = _c.TestNhapTheoXa._may_moi

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _hop(self):
        from pabt.man_hinh_du_toan import HopTraNQ28
        h = HopTraNQ28(None, '', xem=True, the=2)
        for w in (h.khung_goi, h.khung_cn, h.khung_k):
            w.im_lang = True
        self.addCleanup(h.deleteLater)
        return h

    def test_khong_ghi_gi_cho_toi_khi_luu(self):
        ra = self._goi_ba_xa()
        self._may_moi('may_sua')
        self._nap_cap('Phường B Gói', gia=999, k='1.9')
        gia_truoc = [dict(r) for r in nq.tat_ca()]
        k_truoc = [dict(r) for r in he_so_k.tat_ca()]
        ds_goi_truoc = [g.get('ma') for g in gg.ds_goi()]
        h = self._hop()
        k = h.khung_goi
        self.assertTrue(k.nhap_goi_cai(ra, chi_xa=['Phường A Gói', 'Phường B Gói'], sua=True))
        # chưa ghi gì vào máy
        self.assertEqual([dict(r) for r in nq.tat_ca()], gia_truoc)
        self.assertEqual([dict(r) for r in he_so_k.tat_ca()], k_truoc)
        self.assertEqual([g.get('ma') for g in gg.ds_goi()], ds_goi_truoc)
        # đơn giá: bảng xem trước của thẻ con Đọc văn bản, chỉ xã đã chọn, có kiểm định
        self.assertIs(k.the.currentWidget(), h.khung_cn)
        self.assertEqual({r['xa'] for r in h.khung_cn.dong}, {'Phường A Gói', 'Phường B Gói'})
        self.assertTrue(h.khung_cn.b_ghi.isEnabled())
        self.assertIsNotNone(getattr(h.khung_cn, 'kiem_dinh', None))
        self.assertIn('CHƯA GHI', h.khung_cn.lb.text())
        # hệ số K: thẻ Hệ số K chưa lưu, xã chọn lấy số của gói, xã khác giữ
        self.assertTrue(h.khung_k.chua_luu)
        dk = h.khung_k.lay_dong()
        self.assertEqual({r['he_so'] for r in dk if r['dia_ban'] == 'Phường B Gói'}, {'1.4'})
        self.assertTrue(any(r['dia_ban'] == 'Phường A Gói' for r in dk))
        self.assertFalse(any(r['dia_ban'] == 'Phường C Gói' for r in dk))
        # bộ quy tắc: gói nháp
        self.assertIsNotNone(k._nhap)
        self.assertTrue(k.ds.item(0, 0).text().startswith('Nháp - chưa lưu'))
        # lưu bằng đúng các nút sẵn có
        h.khung_cn.xac_nhan_kiem_dinh = True
        self.assertIsNotNone(h.khung_cn.ghi())
        gia_b = [r['dat_o'] for r in nq.tat_ca() if nq.khop_xa('Phường B Gói', r['xa'])]
        self.assertEqual(gia_b, [2000, 1000])                              # xã trùng thay sạch (Bổ sung)
        self.assertTrue(h.khung_k.luu())
        self.assertEqual({r['he_so'] for r in he_so_k.tat_ca() if r.get('dia_ban') == 'Phường B Gói'}, {'1.4'})
        k.the.setCurrentIndex(k.the_doc + 1)
        self.assertTrue(k.luu())
        self.assertIsNone(k._nhap)

    def test_goi_trung_khong_tao_nhap(self):
        ra = self._goi_ba_xa()
        h = self._hop()
        k = h.khung_goi
        xem = gg.doc_goi_cai(ra)
        gg.nhap_goi_cai(ra)                                                # bộ quy tắc của gói đã có trên máy
        self.assertTrue(k.sua_goi_cai(gg.doc_goi_cai(ra), None, Path(ra).name))
        self.assertIsNone(k._nhap)
        self.assertEqual({r['xa'] for r in h.khung_cn.dong}, {x['ten'] for x in gg.thong_ke_goi_cai(xem)})

    def test_hop_co_lua_chon_sua(self):
        from pabt.man_hinh_goi_gia_dat import _tao_hop_nhap_goi_cai
        ra = self._goi_ba_xa()
        xem = gg.doc_goi_cai(ra)
        h = _tao_hop_nhap_goi_cai(None, xem, ra.name)
        self.assertIsNone(h.r_sua)                                         # hộp Bộ quy tắc đứng riêng: không có chế độ sửa
        self.assertEqual(h.che_do, 'bo_sung')
        h.deleteLater()
        h = _tao_hop_nhap_goi_cai(None, xem, ra.name, co_sua=True)
        h.r_sua.setChecked(True)
        self.assertEqual(h.che_do, 'sua')
        self.assertEqual(h.b_ok.text(), 'Mở để sửa')
        h.r_thay.setChecked(True)
        self.assertEqual(h.che_do, 'thay')
        self.assertFalse(h.bo_sung)
        h.deleteLater()

    def test_gop_dong_giu_nguyen_dong_goi(self):
        """Ghi qua khung đọc văn bản đi qua cap_nhat_gia_dat._gop_dong: dòng của gói (đã chuẩn) không bị gộp mất."""
        from pabt.cap_nhat_gia_dat import _gop_dong
        dong = [dict(r) for r in nq.tat_ca()]
        self.assertEqual(len(_gop_dong(dong)), len(dong))
