"""1.0.84: Phường Tân Triều trong bảng tính giá; Word 97-2003 và trích quy tắc của công cụ quét."""
from __future__ import annotations

import struct
import unittest

from pabt import gia_dat_qd03 as gd
from pabt import quet_chung as qc
from pabt.doc_doc import chu_tu_luong


def _word(chu: str) -> tuple:
    word = bytearray(4096)
    struct.pack_into('<H', word, 0, 0xA5EC)
    tho = (chu + '\r').encode('utf-16-le')
    fc = 0x400
    word[fc:fc + len(tho)] = tho
    n = len(tho) // 2
    plc = struct.pack('<II', 0, n) + struct.pack('<HIH', 0, fc, 0)
    clx = bytes([2]) + struct.pack('<I', len(plc)) + plc
    struct.pack_into('<II', word, 0x01A2, 0, len(clx))
    return bytes(word), clx


class TestDocWord97(unittest.TestCase):
    def test_doc_chu_tieng_viet(self):
        chu = chu_tu_luong(*_word('Điều 1. Bồi thường khi Nhà nước thu hồi đất, hệ số 1,05.'))
        self.assertIn('Bồi thường khi Nhà nước thu hồi đất', chu)
        self.assertIn('1,05', chu)
        self.assertNotIn('\x00', chu)


class TestQuetToanVan(unittest.TestCase):
    def test_nhan_phuong_tan_trieu(self):
        self.assertEqual(qc.nhan_dien_tham_so('Thửa tại Phường Tân Triều, mặt đường nhựa.')['dia_ban'], 'Bảng 8. Phường Tân Triều')
        self.assertEqual(gd.dia_ban_theo_ten('Phường Tân Triều'), 'Bảng 8. Phường Tân Triều')
        self.assertEqual(len(gd.ds_doan('Bảng 8. Phường Tân Triều')), 55)

    def test_trich_nghi_quyet_va_toan_van(self):
        dong = ['Nghị quyết về bảng giá đất'] + [
            f'Điều {i}. Bồi thường khi Nhà nước thu hồi đất, hệ số 0,90.' for i in range(1, 6)]
        nd = '\n'.join(dong)
        kq = qc.quet(['nq.doc'], doc=lambda p: nd)
        self.assertTrue(kq.nq_chu)
        self.assertIn('Bồi thường khi Nhà nước thu hồi đất', kq.toan_van)
        self.assertTrue(any(c.startswith('Điều 1') for c in kq.quy_tac))
        self.assertEqual(kq.tung_file[0]['loai'], qc.D_CAN_CU)

    def test_hop_co_the_noi_dung(self):
        from pabt.man_hinh_quet_chung import HopKetQuaQuet
        kq = qc.KetQuaQuet(toan_van='Nội dung file', nq_chu='Nghị quyết giá đất', quy_tac=['Điều 1. Hệ số 0,9'])
        h = HopKetQuaQuet(None, kq)
        self.addCleanup(h.close)
        self.assertTrue(h.b_luu_qt.isEnabled())
        self.assertTrue(any('Nội dung' in h.tab.tabText(i) for i in range(h.tab.count())))
        self.assertIn('Điều 1', h.o_toan_van.toPlainText())
