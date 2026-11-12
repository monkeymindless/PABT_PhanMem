"""1.1.07 (kiểm định tầng 4) - quy tắc toàn văn nghị quyết làm ĐỔI hệ số tính giá: so quy tắc cũ / mới + tính thử trên 1 m² mẫu, hỏi
trước khi lưu (màn hình); không truyền hoi_toan_van (kiểm thử cũ, dòng lệnh) thì lưu ngay như trước."""
from __future__ import annotations

import unittest
from decimal import Decimal as D

from tests import test_nq28_dot_1081 as _t                     # nhập module (nhập tên lớp test thì discover chạy lại lớp đó)

VB_MOI = _t.TOAN_VAN.replace('3. Thửa đất có từ 2 mặt tiền trong phạm vi 50 m nhân hệ số 1,20.',
                             '6. Đất trong khu công nghiệp mới tính bằng hệ số 0,85.')


class TestSoSanhToanVan(_t._MayTrong):
    def test_so_sanh_va_khong_luu_khi_tu_choi(self):
        from pabt.cap_nhat_gia_dat import _luu_toan_van
        from pabt.quy_tac_vi_tri import doc_toan_van_nghi_quyet, quy_tac_nq28, so_dieu_toan_van_da_luu, so_sanh_toan_van
        hs_cu = next(x['he_so'] for x in quy_tac_nq28()['truong_hop'] if x['ma'] == 'kcn_moi')
        ss = so_sanh_toan_van(doc_toan_van_nghi_quyet(VB_MOI)['quy_tac'])
        kcn = [x for x in ss if x['moi'] == '0.85']
        self.assertEqual(len(kcn), 1)
        self.assertEqual(kcn[0]['cu'], str(hs_cu))
        self.assertEqual(kcn[0]['tien_moi'], D(8500000))                   # 1 m² x 10.000.000 x 0,85
        self.assertIn('0,85', kcn[0]['nguon'])
        hoi = []
        kq = _luu_toan_van(VB_MOI, lambda ds: hoi.append(ds) or False)
        self.assertTrue(kq['khong_luu'])
        self.assertEqual(len(hoi), 1)
        self.assertEqual(so_dieu_toan_van_da_luu(), 0)                     # từ chối: không ghi file
        self.assertEqual(next(x['he_so'] for x in quy_tac_nq28()['truong_hop'] if x['ma'] == 'kcn_moi'), hs_cu)
        kq = _luu_toan_van(VB_MOI, lambda ds: True)
        self.assertFalse(kq.get('khong_luu'))
        self.assertEqual(next(x['he_so'] for x in quy_tac_nq28()['truong_hop'] if x['ma'] == 'kcn_moi'), '0.85')
        # đọc lại đúng văn bản đó: không còn gì đổi -> không hỏi
        hoi.clear()
        _luu_toan_van(VB_MOI, lambda ds: hoi.append(ds) or False)
        self.assertEqual(hoi, [])

    def test_khong_hoi_thi_luu_ngay(self):
        from pabt.cap_nhat_gia_dat import _luu_toan_van
        from pabt.quy_tac_vi_tri import so_dieu_toan_van_da_luu
        _luu_toan_van(VB_MOI, None)
        self.assertGreater(so_dieu_toan_van_da_luu(), 0)


@unittest.skipUnless(_t.CO_QT, 'cần PySide6')
class TestHopSoSanh(_t._MayTrong):
    def test_hop(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_gia_dat import KhungCapNhatGiaDat
        from pabt.quy_tac_vi_tri import doc_toan_van_nghi_quyet, so_sanh_toan_van
        k = KhungCapNhatGiaDat(None, 'Trị An')
        self.addCleanup(k.deleteLater)
        d = k._hoi_toan_van(so_sanh_toan_van(doc_toan_van_nghi_quyet(VB_MOI)['quy_tac']), hien=False)
        self.addCleanup(d.deleteLater)
        self.assertIn('0.85', d.o_ds.toPlainText())
        self.assertIn('8.500.000', d.o_ds.toPlainText())
        self.assertIn('Lưu quy tắc mới', d.nut_them)


if __name__ == '__main__':
    unittest.main()
