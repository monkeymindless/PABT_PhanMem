"""1.1.06 - hộp chọn xã / phường sau khi đọc / scan văn bản (người dùng 12/11/2026): danh sách tích chọn từng xã, Chọn tất cả, Bỏ chọn;
chỉ xã được tích lên bảng xem trước (bảng giá đất, hệ số K). Chế độ im lặng không truyền chon_xa: như trước (không lọc)."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pabt import gia_dat_nq28 as nq
from pabt import he_so_k as hk


class _May(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1106_xa_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)


class TestHop(_May):
    def _hop(self, chon_san=None):
        from pabt.man_hinh_chon_dia_ban import HopChonDiaBan
        return HopChonDiaBan(None, [('Xã Trị An', 30), ('Phường Tân Triều', 12), ('Xã Phú Lý', 7), ('Xã Tân An', 5)],
                             chon_san, lambda x: 9 if x == 'Xã Trị An' else 0)

    def test_chon_tat_ca_bo_chon_va_loc(self):
        h = self._hop(lambda x: x == 'Xã Trị An')
        self.assertEqual(h.da_chon(), ['Xã Trị An'])
        self.assertIn('1 / 4', h.lb_dem.text())
        h.dat_tat_ca(True)
        self.assertEqual(len(h.da_chon()), 4)
        h.dat_tat_ca(False)
        self.assertEqual(h.da_chon(), [])
        self.assertFalse(h.b_ok.isEnabled())                              # không chọn xã nào: không cho xác nhận
        h.loc('tan')                                                       # lọc bỏ dấu: Tân Triều, Tân An
        h.dat_tat_ca(True)                                                 # chọn tất cả chỉ các dòng đang hiện
        self.assertEqual(sorted(h.da_chon()), ['Phường Tân Triều', 'Xã Tân An'])
        self.assertIn('17 dòng', h.lb_dem.text())
        self.assertEqual(h.bang.item(0, 3).text(), '9 dòng')
        self.assertEqual(h.bang.item(1, 3).text(), 'chưa có')
        h.deleteLater()

    def test_ham_loc(self):
        from pabt.man_hinh_chon_dia_ban import chon_dia_ban, loc_theo_dia_ban

        class _Cha:
            im_lang = True
        dong = [dict(xa='A', i=1), dict(xa='B', i=2), dict(xa='A', i=3), dict(xa='C', i=4)]
        self.assertEqual([r['i'] for r in loc_theo_dia_ban(dong, 'xa', ['A', 'C'])], [1, 3, 4])
        self.assertIs(chon_dia_ban(_Cha(), dong, 'xa'), dong)              # im lặng, không chọn: như trước
        self.assertEqual([r['i'] for r in chon_dia_ban(_Cha(), dong, 'xa', chon=['B'])], [2])
        mot = [dict(xa='A'), dict(xa='A')]
        self.assertIs(chon_dia_ban(_Cha(), mot, 'xa', chon=['Z']), mot)    # một xã: không hỏi, giữ nguyên


class TestBangGiaDat(_May):
    def test_doc_file_chi_giu_xa_da_chon(self):
        from pabt.man_hinh_gia_dat import KhungCapNhatGiaDat
        f = nq.xuat_excel(self.td / 'bang_gia.xlsx')                       # 4 địa bàn gắn sẵn, mỗi địa bàn một sheet
        xa = nq.ds_xa()
        self.assertGreaterEqual(len(xa), 2)
        k = KhungCapNhatGiaDat(None, '')
        k.im_lang = True
        tat_ca = k.nap_file(f)
        self.assertEqual({r['xa'] for r in tat_ca}, set(xa))               # im lặng, không chọn: đủ xã như trước
        chi = k.nap_file(f, chon_xa=[xa[1]])
        self.assertEqual({r['xa'] for r in chi}, {xa[1]})
        self.assertEqual({r['xa'] for r in k.dong}, {xa[1]})                # bảng xem trước (sẽ ghi) chỉ có xã đã chọn
        self.assertEqual({r['xa'] for r in k.kq['dong_goc']}, {xa[1]})
        self.assertIn('Đã chọn 1 xã', k.lb.text())
        k.deleteLater()


class TestHeSoK(_May):
    def _file(self) -> Path:
        import openpyxl
        f = self.td / 'k.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        for r in (['Quyết định số 03/2026/QĐ-UBND'], ['STT', 'Xã, phường', 'Loại đất', 'Vị trí', 'Hệ số K'],
                  [1, 'Xã Mẫu A', 'Đất ở', 'Vị trí 1', 1.2], [2, 'Xã Mẫu B', 'Đất ở', 'Vị trí 1', 1.3],
                  [3, 'Xã Mẫu C', 'Đất ở', 'Vị trí 1', 1.1], [4, 'Xã Mẫu B', 'Đất rừng sản xuất', '', '1,05']):
            ws.append(r)
        wb.save(f)
        return f

    def test_doc_moi_xa_roi_chon(self):
        from pabt.man_hinh_he_so_k import KhungHeSoK
        f = self._file()
        d, _, _ = hk.doc_file(f, '*')                                       # '*': mọi xã của file
        self.assertEqual({r['dia_ban'] for r in d}, {'Xã Mẫu A', 'Xã Mẫu B', 'Xã Mẫu C'})
        k = KhungHeSoK(None, '')
        k.im_lang = True
        dong = k.nap_file(f, chon_xa=['Xã Mẫu B'])
        self.assertEqual([(r['dia_ban'], r['he_so']) for r in dong], [('Xã Mẫu B', '1.3'), ('Xã Mẫu B', '1.05')])
        self.assertEqual(k.bang.rowCount(), 2)
        self.assertTrue(k.chua_luu)
        k.deleteLater()


if __name__ == '__main__':
    unittest.main()
