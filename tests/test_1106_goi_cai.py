"""1.1.06 - nhập gói cài .larcgia: chọn xã cần cài + cách ghi (Bổ sung / Thay toàn bộ) thay câu hỏi Có / Không. Hàm gg.nhap_goi_cai
(chi_xa=) chỉ ghi đơn giá, hệ số K và đoạn đường riêng của các xã đã chọn; xã không chọn giữ nguyên số trên máy."""
from __future__ import annotations

import os
from pathlib import Path

from pabt import gia_dat_nq28 as nq
from pabt import goi_gia_dat as gg
from pabt import he_so_k
from tests import test_goi_gia_dat as _g                      # nhập module (nhập tên lớp test thì discover chạy lại lớp đó)


class TestNhapTheoXa(_g.CoMay):
    _dong_gia = _g.TestGoiCaiGiaDat._dong_gia
    _dong_k = _g.TestGoiCaiGiaDat._dong_k
    _nap_cap = _g.TestGoiCaiGiaDat._nap_cap

    def _goi_ba_xa(self) -> Path:
        self._nap_cap('Phường A Gói')
        self._nap_cap('Phường B Gói', gia=2000, k='1.4')
        self._nap_cap('Phường C Gói', gia=3000, k='1.1')
        return Path(gg.xuat_goi_cai(self.td / 'ba_xa.larcgia', ['Phường A Gói', 'Phường B Gói', 'Phường C Gói']))

    def _may_moi(self, ten: str) -> None:
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / ten)
        gg._quen()
        he_so_k._quen()
        nq._quen()

    def test_thong_ke_va_chi_cai_xa_chon(self):
        ra = self._goi_ba_xa()
        self._may_moi('may_khac')
        self._nap_cap('Phường B Gói', gia=999, k='1.9')                    # máy nhận đã có B (số cũ)
        tk = {x['ten']: x for x in gg.thong_ke_goi_cai(gg.doc_goi_cai(ra))}
        self.assertEqual(set(tk), {'Phường A Gói', 'Phường B Gói', 'Phường C Gói'})
        self.assertEqual((tk['Phường A Gói']['so_gia'], tk['Phường A Gói']['so_k']), (2, 10))
        self.assertEqual(tk['Phường A Gói']['gia_may'], 0)                 # chưa có -> thêm
        self.assertEqual(tk['Phường B Gói']['gia_may'], 2)                 # đã có -> thay sạch
        kq = gg.nhap_goi_cai(ra, bo_sung=True, chi_xa=['Phường A Gói'])
        self.assertEqual(kq['xa'], ['Phường A Gói'])
        self.assertEqual(kq['so_gia'], 2)
        xa = nq.ds_xa()
        self.assertTrue(any(nq.khop_xa('Phường A Gói', x) for x in xa))
        self.assertFalse(any(nq.khop_xa('Phường C Gói', x) for x in xa))  # không chọn: không cài
        gia_b = [r['dat_o'] for r in nq.tat_ca() if nq.khop_xa('Phường B Gói', r['xa'])]
        self.assertEqual(gia_b, [999, 999 // 2])                           # xã không chọn: giữ số cũ của máy
        k_b = {r['he_so'] for r in he_so_k.tat_ca() if (r.get('dia_ban') or '') == 'Phường B Gói'}
        self.assertEqual(k_b, {'1.9'})
        self.assertTrue(any((r.get('dia_ban') or '') == 'Phường A Gói' for r in he_so_k.tat_ca()))

    def test_bo_sung_thay_sach_xa_trung(self):
        ra = self._goi_ba_xa()
        self._may_moi('may_trung')
        self._nap_cap('Phường B Gói', gia=999, k='1.9')
        gg.nhap_goi_cai(ra, bo_sung=True, chi_xa=['Phường B Gói'])
        gia_b = [r['dat_o'] for r in nq.tat_ca() if nq.khop_xa('Phường B Gói', r['xa'])]
        self.assertEqual(gia_b, [2000, 1000])                              # không chồng dòng cũ / mới
        k_b = {r['he_so'] for r in he_so_k.tat_ca() if (r.get('dia_ban') or '') == 'Phường B Gói'}
        self.assertEqual(k_b, {'1.4'})

    def test_thay_toan_bo_chi_con_xa_chon(self):
        ra = self._goi_ba_xa()
        self._may_moi('may_thay')
        gg.nhap_goi_cai(ra, bo_sung=False, chi_xa=['Phường C Gói'])
        self.assertEqual({r['xa'] for r in nq.tat_ca()}, {'Phường C Gói'})
        self.assertEqual({r.get('dia_ban') for r in he_so_k.tat_ca()}, {'Phường C Gói'})

    def test_khong_chon_xa_nao(self):
        ra = self._goi_ba_xa()
        with self.assertRaises(gg.LoiGoi):
            gg.nhap_goi_cai(ra, chi_xa=[])

    def test_hop_nhap(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_goi_gia_dat import _tao_hop_nhap_goi_cai
        ra = self._goi_ba_xa()
        self._may_moi('may_hop')
        self._nap_cap('Phường B Gói', gia=999, k='1.9')
        h = _tao_hop_nhap_goi_cai(None, gg.doc_goi_cai(ra), ra.name)
        self.assertEqual(len(h.da_chon()), 3)                              # gói: tích sẵn mọi xã
        self.assertTrue(h.bo_sung)                                         # mặc định Bổ sung
        chu = {h.bang.item(r, 1).text(): h.bang.item(r, 3).text() for r in range(h.bang.rowCount())}
        self.assertIn('thay sạch', chu['Phường B Gói'])
        self.assertIn('thêm mới', chu['Phường A Gói'])
        h.dat_chon(['Phường A Gói'])
        h.r_thay.setChecked(True)
        self.assertFalse(h.bo_sung)
        h.accept()
        self.assertEqual(h.chon, ['Phường A Gói'])
        h.deleteLater()
