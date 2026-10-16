"""1.0.00 (người dùng 16/10/2026, Hội đồng chuyên gia UI/UX - nghiệp vụ GPMB - kiến trúc - QA): trang "Báo cáo tiến độ GPMB" gộp
vào trang "Tiến độ chi trả & Bàn giao" (man_hinh_theo_doi.KhungTienDo): thẻ chỉ số bấm được, hai chế độ xem (Theo hộ / Thửa còn
vướng), MỘT nút Xuất (menu), mốc pháp lý một dòng + hộp "Mốc pháp lý…", số liệu tính một lần; không còn nút trùng lệnh giữa các
trang. Dữ liệu GIẢ LẬP (tests.test_toc_do._du_an)."""
from __future__ import annotations
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, theo_doi, thoi_han, van_dong  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


def _qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _hn(n: int) -> str:
    return (date.today() + timedelta(days=n)).strftime('%d/%m/%Y')


class _Co(unittest.TestCase):
    def setUp(self):
        _qt()
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.p = _du_an(self.td, 6)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.doCleanups()                               # đóng cửa sổ / kết nối trước khi xóa thư mục tạm (Windows giữ khóa file)
        self.con.close()
        self.tmp.cleanup()

    def qd(self, so_ho: int = 4) -> int:
        q = theo_doi.luu_qd(self.con, None, '9/QĐ-UBND', _hn(-30), 'Phê duyệt thử')
        theo_doi.them_ho_theo_pa(self.con, q, self.ma[:so_ho])
        return q

    def khung(self):
        from pabt.man_hinh_theo_doi import KhungTienDo
        k = KhungTienDo(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        return k


class TestTrangGop(_Co):
    def test_bo_cuc_mot_trang(self):
        k = self.khung()
        self.assertEqual(list(k.kpi.the), ['giai_ngan', 'mat_bang', 'con_vuong', 'cuong_che'])
        self.assertEqual(list(k.nut_che_do), ['ho', 'thua'])
        self.assertEqual(k.che_do(), 'ho')
        # nút: không còn các nút trùng lệnh của trang Báo cáo cũ; xuất gom vào MỘT nút có menu
        self.assertEqual(set(k.nut), {'Mốc pháp lý…', 'Bàn giao mặt bằng các hộ đã chọn…', 'Sổ nhật ký vận động…',
                                      'Hộ hoàn tất CTBT…', 'Xuất'})
        self.assertEqual([a.text() for a in k.menu_xuat.actions()], [x[0] for x in k.XUAT])
        self.assertIs(k.nut['Xuất'].menu(), k.menu_xuat)
        self.assertFalse(hasattr(k, 'o_ngay_tb'))                         # ô ngày thông báo nằm trong hộp Mốc pháp lý
        self.assertFalse(k.w_qd.isVisibleTo(k))                            # chưa có quyết định: ô danh sách QĐ ẩn
        self.qd()
        k.nap()
        self.assertTrue(k.w_qd.isVisibleTo(k))
        self.assertLessEqual(k.ds_qd_w.height(), k.QD_CAO_DONG + 6)        # một quyết định: cao một dòng

    def test_bam_the_chi_so_loc_bang(self):
        self.qd()
        k = self.khung()
        for the, (che_do, loc) in k.KPI_LOC.items():
            k.dat_che_do('ho' if che_do == 'thua' else 'thua')
            k.kpi.the[the].bam.emit()
            self.assertEqual(k.che_do(), che_do, the)
            self.assertTrue(k.nut_che_do[che_do].isChecked())
            if loc is not None:
                self.assertEqual(k.cb_loc.currentData(), loc, the)
        k.bam_kpi('giai_ngan')
        self.assertEqual(sorted(k.dang_hien), sorted(self.ma[:4]))        # 4 hộ có QĐ chưa nhận tiền

    def test_the_khi_chua_co_quyet_dinh(self):
        from pabt.man_hinh_bao_cao import KHONG_SO
        k = self.khung()
        self.assertEqual(k.kpi.the['giai_ngan'].lb_so.text(), KHONG_SO)
        self.assertEqual(k.kpi.the['con_vuong'].lb_so.text(), KHONG_SO)
        self.assertFalse(k.kpi.the['giai_ngan'].thanh.isVisibleTo(k))     # không có thanh tiến độ 0% gây hiểu nhầm
        k.dat_che_do('thua')
        self.assertIs(k.thua.ngan.currentWidget(), k.thua.lb_trong)
        self.assertIn('6 hộ chưa có quyết định', k.thua.chu_trong())

    def test_thua_con_vuong_chon_ho(self):
        q = self.qd()
        theo_doi.ghi_chi_tra(self.con, [(q, self.ma[0])], _hn(-1))
        k = self.khung()
        k.dat_che_do('thua')
        b = k.thua.bang
        self.assertGreater(b.rowCount(), 0)
        b.selectAll()
        ds = k.ma_da_chon()                                                # hộ nhiều thửa: một lần
        self.assertEqual(len(ds), len(set(ds)))
        self.assertEqual(set(ds), set(self.ma[:4]))
        mo = []
        k.mo_ho.connect(mo.append)                                         # bấm đúp dòng thửa: mở Trạng thái hộ như bảng theo hộ
        b.cellDoubleClicked.emit(0, 2)
        self.assertEqual(mo, [b.ma_dong(0)])
        k.dat_che_do('ho')
        k.bang.clearSelection()
        self.assertEqual(k.ma_da_chon(), [])

    def test_so_lieu_tinh_mot_lan(self):
        """nap(): tổng hợp hộ, vận động, mốc thu hồi đọc MỘT lần cho cả bảng theo hộ và thẻ / bảng thửa (trước đây hai trang mỗi
        trang tự tính)."""
        self.qd()
        k = self.khung()
        with mock.patch.object(theo_doi, 'tong_hop', wraps=theo_doi.tong_hop) as th, \
                mock.patch.object(van_dong, 'tinh_trang_tat_ca', wraps=van_dong.tinh_trang_tat_ca) as vd:
            k.nap()
        self.assertEqual((th.call_count, vd.call_count), (1, 1))
        self.assertEqual(k.tq['so_ho_phe_duyet'], 4)

    def test_moc_phap_ly(self):
        self.qd()
        k = self.khung()
        self.assertIn('chưa nhập ngày thông báo', k.lb_moc.text())
        self.assertTrue(k.mo_moc(ngay=_hn(-130)))                           # chỉ ngày thông báo
        self.assertEqual(thoi_han.hien_ngay(thoi_han.ngay_thong_bao(self.con)), _hn(-130))
        self.assertIn(f'thông báo thu hồi đất {_hn(-130)}', k.lb_moc.text())
        self.assertIn('4/4', k.lb_moc.text())
        self.assertFalse(k.mo_moc(ngay=_hn(-130)))                          # không đổi gì
        self.assertFalse(k.mo_moc(ngay='31/02/2026'))                       # sai ngày: báo, không ghi
        self.assertEqual(thoi_han.hien_ngay(thoi_han.ngay_thong_bao(self.con)), _hn(-130))
        self.assertTrue(k.mo_moc(dict(thu_hoi_pnn=200), ngay=_hn(-130)))
        self.assertNotIn('4/4', k.lb_moc.text())
        from pabt.man_hinh_theo_doi import HopMocThoiHan
        h = HopMocThoiHan(self.con, ngay_thong_bao=True)
        self.addCleanup(h.deleteLater)
        self.assertEqual(h.ngay_thong_bao(), _hn(-130))
        self.assertIsNone(HopMocThoiHan(self.con).ngay_thong_bao())       # nơi khác mở hộp: không có ô ngày

    def test_xuat_menu(self):
        q = self.qd()
        van_dong.ghi_buoi(self.con, self.ma[2], 'tien', _hn(-20))
        theo_doi.ghi_chi_tra(self.con, [(q, self.ma[0])], _hn(-1))
        k = self.khung()
        self.assertTrue(k.xuat(self.td / 'td.xlsx').exists())
        self.assertTrue(k.xuat_bao_cao(self.td / 'bc.xlsx').exists())
        self.assertTrue(k.xuat_cuong_che(self.td / 'cc.xlsx').exists())
        with mock.patch.object(k, 'xuat_bao_cao') as x:
            k.hanh_dong_xuat['Báo cáo tiến độ GPMB (Excel)…'].trigger()
        x.assert_called_once()


class TestCuaSoChinh(_Co):
    def _cua_so(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(self.p))
        return ud, w

    def test_menu_mot_muc_va_khong_nut_trung_giua_trang(self):
        ud, w = self._cua_so()
        self.assertEqual(w.lenh['Theo dõi tiến độ'].text().replace('&&', '&'), 'Tiến độ chi trả & Bàn giao')
        self.assertNotIn('Báo cáo tổng hợp…', w.lenh)
        self.assertNotIn('Báo cáo tiến độ GPMB', [a.text() for a in w.findChildren(type(w.lenh['Danh sách hộ']))])
        from PySide6.QtWidgets import QPushButton
        for i in range(len(ud.TRANG)):
            w.mo_trang(i)
            _qt().processEvents()
        # cùng chữ nút ở hai trang trở lên = lệnh trùng (0.9.66 "mỗi lệnh một chỗ"); "Xuất Excel…" của từng trang xuất bảng RIÊNG
        # của trang đó nên được phép
        cho_phep = {'Xuất Excel…'}
        o = {}
        for i, k in w.khung_trang.items():
            for b in k.findChildren(QPushButton):
                if b.text().strip() and b.window() is w:
                    o.setdefault(b.text().strip(), set()).add(i)
        trung = {t: sorted(ds) for t, ds in o.items() if len(ds) > 1 and t not in cho_phep}
        self.assertEqual(trung, {})

    def test_mo_trang_tien_do(self):
        ud, w = self._cua_so()
        self.qd()
        w.lenh['Theo dõi tiến độ'].trigger()
        _qt().processEvents()
        self.assertEqual(w.trang.currentIndex(), ud.STACK_THEO_DOI)
        self.assertEqual(w.tien_do.tq['so_ho_phe_duyet'], 4)
        w.tien_do.dat_che_do('thua')
        w.tien_do.thua.bang.selectRow(0)
        self.assertEqual(w.ho_da_chon(), [w.tien_do.thua.bang.ma_dong(0)])   # lệnh menu (Trạng thái hộ…) theo hộ đang chọn ở bảng thửa


if __name__ == '__main__':
    unittest.main()
