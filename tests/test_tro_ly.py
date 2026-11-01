"""Phương án đột phá 9 (30/10/2026): trợ lý - giải thích số tiền hộ, nháp tờ trình (ngoại tuyến), hỏi Claude (tùy chọn, mặc định tắt;
che dữ liệu cá nhân). KHÔNG gọi mạng: client Anthropic GIẢ LẬP (_Khach). Dự án GIẢ LẬP."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from pabt import csdl, tro_ly
from tests.test_toc_do import _du_an


class _Khach:
    """Client giả: ghi lại tham số gọi, trả lời một khối chữ (hoặc từ chối)."""

    def __init__(self, tra='Trả lời thử', stop='end_turn'):
        self.goi = []
        self.tra, self.stop = tra, stop
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **k):
        self.goi.append(k)
        return SimpleNamespace(stop_reason=self.stop, content=[SimpleNamespace(type='thinking', thinking=''),
                                                                SimpleNamespace(type='text', text=self.tra)])


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_trl_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.con = csdl.mo(_du_an(self.td, 4))

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)


class TestNgoaiTuyen(_Co):
    def test_giai_thich_chenh_quyet_dinh(self):
        from pabt import theo_doi
        g = tro_ly.giai_thich_ho(self.con, 1)
        self.assertIn('chưa có quyết định', g.chu)
        qd = theo_doi.luu_qd(self.con, None, '12/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(self.con, qd, [1])
        self.assertIn('Khớp', tro_ly.giai_thich_ho(self.con, 1).chu)
        with self.con:                                  # số tiền quyết định khác phương án (sửa phương án sau khi duyệt / nhập tay)
            self.con.execute("UPDATE qd_ho SET so_tien = '150000000', tien_dat = '150000000', tien_thuong = '0' WHERE ma_ho = 1")
        g = tro_ly.giai_thich_ho(self.con, 1)
        self.assertIn('CAO HƠN quyết định 12.000.000', g.chu)
        self.assertIn('Thưởng: phương án 12.000.000 - quyết định 0', g.chu)    # chỉ ra đúng hạng mục chênh
        self.assertIn('quyet_dinh', g.so_lieu)
        self.assertNotIn(g.ho_ten, str(g.so_lieu))      # số liệu gửi kèm không có họ tên
        with self.assertRaises(tro_ly.LoiTroLy):
            tro_ly.giai_thich_ho(self.con, 9999)

    def test_nhap_to_trinh(self):
        chu = tro_ly.nhap_to_trinh(self.con)
        self.assertIn('4 hộ', chu)
        self.assertIn('Bằng chữ', chu)

    def test_an_danh(self):
        ten = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 2').fetchone()[0]
        s = tro_ly.an_danh(f'Hộ ông {ten}, CCCD 075092000123, ĐT 0912345678, CMND 271234567, tiền 1.234.567', self.con)
        self.assertNotIn(ten, s)
        self.assertIn('Hộ #2', s)
        self.assertNotIn('075092000123', s)
        self.assertNotIn('0912345678', s)
        self.assertNotIn('271234567', s)
        self.assertIn('1.234.567', s)                   # số tiền có dấu chấm không bị che


class TestTrucTuyen(_Co):
    def test_mac_dinh_tat_va_goi_dung_tham_so(self):
        self.assertFalse(tro_ly.doc_cai_dat()['bat'])
        with self.assertRaises(tro_ly.LoiTroLy):
            tro_ly.hoi_claude('x', khach=_Khach())
        tro_ly.ghi_cai_dat(bat=True)
        ten = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0]
        k = _Khach('Giải thích')
        self.assertEqual(tro_ly.hoi_claude('Vì sao?', f'{ten} CCCD 075092000123', self.con, k), 'Giải thích')
        g = k.goi[0]
        self.assertEqual(g['model'], 'claude-opus-5-5')
        self.assertEqual(g['fallbacks'], [{'model': tro_ly.DU_PHONG}])
        self.assertEqual(g['betas'], ['server-side-fallback-2026-06-01'])
        self.assertEqual(g['output_config'], {'effort': 'medium'})
        self.assertNotIn('thinking', g)
        gui = g['messages'][0]['content']
        self.assertNotIn(ten, gui)
        self.assertNotIn('075092000123', gui)
        tro_ly.ghi_cai_dat(gui_ca_nhan=True, mo_hinh='claude-sonnet-5-5')    # người dùng cho phép: gửi nguyên
        k = _Khach()
        tro_ly.hoi_claude('Vì sao?', ten, self.con, k)
        self.assertIn(ten, k.goi[0]['messages'][0]['content'])
        self.assertEqual(k.goi[0]['model'], 'claude-sonnet-5-5')
        with self.assertRaises(tro_ly.LoiTroLy):
            tro_ly.hoi_claude('x', khach=_Khach(stop='refusal'))
        with self.assertRaises(tro_ly.LoiTroLy):
            tro_ly.ghi_cai_dat(mo_hinh='gpt-x')

    @unittest.skipUnless(sys.platform == 'win32', 'DPAPI chỉ có trên Windows')
    def test_khoa_ma_hoa(self):
        tro_ly.ghi_cai_dat(khoa='sk-ant-GIA-LAP-123')
        self.assertTrue(tro_ly.doc_cai_dat()['co_khoa'])
        self.assertNotIn('GIA-LAP', (self.td / 'may' / tro_ly.FILE_CAI_DAT).read_text(encoding='utf-8'))
        self.assertEqual(tro_ly._khoa_da_luu(), 'sk-ant-GIA-LAP-123')
        tro_ly.ghi_cai_dat(xoa_khoa=True)
        self.assertIsNone(tro_ly._khoa_da_luu())


class TestManHinh(_Co):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('không có Qt')
        cls.app = QApplication.instance() or QApplication([])

    def test_hop(self):
        from pabt.man_hinh_tro_ly import HopTroLy
        h = HopTroLy(self.con, None, 2, im_lang=True)
        self.addCleanup(h.deleteLater)
        self.assertFalse(h.b_ai_gt.isEnabled())         # mặc định tắt
        self.assertIsNotNone(h.giai_thich())
        self.assertIn('Phương án hiện tại', h.o_gt.toPlainText())
        self.assertIn('4 hộ', h.tao_nhap())
        tro_ly.ghi_cai_dat(bat=True)
        k = _Khach('Bản viết lại')
        self.assertEqual(h._hoi('Viết lại', h.o_tt.toPlainText(), k), 'Bản viết lại')
        self.assertIsNone(h._hoi('x', 'y', _Khach(stop='refusal')))
        self.assertIn('từ chối', h.o_gt.toPlainText() + h.o_tt.toPlainText() + h.o_tl.toPlainText())
        h.o_khoa.setText('')
        self.assertFalse(h.luu_khoa())


if __name__ == '__main__':
    unittest.main()
