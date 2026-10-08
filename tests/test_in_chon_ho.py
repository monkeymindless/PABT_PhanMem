"""Kiểm thử chọn hộ in: phân biệt hộ đã lập phương án với phương án phần mềm tự lập (Dự án mới) chưa soát."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, in_an
from pabt.lap_pa import TU_LAP


class TestPhanLoaiLap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.con = csdl.tao_moi(Path(self.tmp.name) / 'a.pabt')
        self.addCleanup(self.con.close)

    def _ho(self, ds):
        with self.con:
            for ma, trang_thai, luu_luc in ds:
                self.con.execute('INSERT INTO ho (ma_ho, thu_tu, ho_ten, trang_thai, luu_luc) VALUES (?,?,?,?,?)',
                                 (ma, ma, f'Hộ {ma}', trang_thai, luu_luc))

    def test_phan_loai(self):
        da_lap = 'Đã lập phương án (lưu 07/10/2026 10:00)'
        ds = []
        # file cũ (trước 0.9.13): Dự án mới tự lập 8 hộ, lưu hàng loạt cách nhau 1 giây, trạng thái vẫn "Đã lập"
        ds += [(m, da_lap, f'2026-10-07T09:00:{m:02d}') for m in range(1, 9)]
        # người dùng mở soát và lưu lại 2 hộ trong số đó, rời rạc
        ds[1] = (2, da_lap, '2026-10-07T10:15:00')
        ds[4] = (5, da_lap, '2026-10-07T11:40:30')
        # file mới: phương án tự lập mang trạng thái riêng
        ds += [(9, TU_LAP, '2026-10-07T12:00:00')]
        # hộ nhập từ Excel (chưa sửa trong phần mềm: luu_luc trống) có phương án: đã lập
        ds += [(10, 'Đã lập', None)]
        # hộ chưa có dòng phương án nào
        ds += [(11, 'Chưa lập phương án', None)]
        self._ho(ds)
        co_pa = {m: m != 11 for m in range(1, 12)}
        kq = in_an.phan_loai_lap(self.con, co_pa)
        self.assertEqual(sorted(m for m, v in kq.items() if v == 'da_lap'), [2, 5, 10])
        self.assertEqual(sorted(m for m, v in kq.items() if v == 'tu_lap'), [1, 3, 4, 6, 7, 8, 9])
        self.assertEqual(kq[11], 'chua')

    def test_hop_in_chon_ho(self):
        """Hộp In / xuất: "Các hộ đã lập phương án" chỉ gồm hộ đã lập (không gồm phương án tự lập chưa soát); tự chọn hộ."""
        import os
        from unittest import mock
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt import nghiep_vu
        from pabt.man_hinh import HopIn
        from pabt.tien import D
        # 142 hộ: Dự án mới tự lập hàng loạt, người dùng soát và lưu 3 hộ
        ds = [(m, 'Đã lập phương án (lưu 07/10/2026 09:00)', f'2026-10-07T09:{m // 60:02d}:{m % 60:02d}') for m in range(1, 143)]
        for m, gio in ((7, '10:05:00'), (40, '11:20:00'), (99, '14:45:10')):
            ds[m - 1] = (m, 'Đã lập phương án (lưu 07/10/2026)', f'2026-10-07T{gio}')
        self._ho(ds)
        gia = []
        for m in range(1, 143):
            k = nghiep_vu.KetQuaHo(m, f'Hộ {m}', dong=[mock.Mock(muc=1)])
            k.muc[1] = D(1000000)
            gia.append(k)
        with mock.patch.object(nghiep_vu, 'tinh_tat_ca', return_value=gia):
            dlg = HopIn(self.con)
        self.assertEqual(dlg.cb_pham_vi.currentData(), 'pa')
        self.assertIn('(3 hộ)', dlg.cb_pham_vi.currentText())
        self.assertEqual(dlg.ds_ho(), [7, 40, 99])
        self.assertIn('Đã chọn 3 hộ, tổng 3.000.000', dlg.lb_chon.text())
        dlg.cb_pham_vi.setCurrentIndex(dlg.cb_pham_vi.findData('tu_lap'))
        self.assertEqual(len(dlg.ds_ho()), 139)
        self.assertIn('139 hộ phương án tự lập CHƯA SOÁT', dlg.lb_chon.text())
        dlg.cb_pham_vi.setCurrentIndex(dlg.cb_pham_vi.findData('pa'))
        dlg.bang_ho.item(39, 0).setCheckState(Qt.CheckState.Unchecked)           # bỏ hộ 40
        self.assertEqual((dlg.cb_pham_vi.currentData(), dlg.ds_ho()), ('tu_chon', [7, 99]))
        dlg.o_tim.setText('Hộ 12')
        dlg._danh_dau(dlg._dang_hien(), giu=True)                                 # thêm hộ 12, 120..129 đang hiện
        self.assertEqual(dlg.ds_ho()[:3], [7, 12, 99])
        dlg.close()

    def test_luu_rieng_khong_tinh_hang_loat(self):
        # 4 hộ lưu liền nhau (dưới ngưỡng 5 hộ) vẫn là người dùng lập
        self._ho([(m, 'Đã lập phương án', f'2026-10-07T09:00:0{m}') for m in range(1, 5)])
        kq = in_an.phan_loai_lap(self.con, {m: True for m in range(1, 5)})
        self.assertEqual(set(kq.values()), {'da_lap'})


if __name__ == '__main__':
    unittest.main()
