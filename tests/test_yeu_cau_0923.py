"""0.9.23 theo lộ trình người dùng (11/10/2026): thanh công cụ danh sách hộ (Xóa hộ theo hộ đang chọn), màn hình chào + dự án
gần đây, thẻ số liệu bấm để lọc, trang Dự toán trong cửa sổ chính (sửa ô chỉ vẽ lại dòng, so sánh khái toán - thực tế), băng
tiêu đề theo đơn vị của dự án, bảng giá đất / hướng dẫn trên menu. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from pabt import du_toan
from pabt.du_toan import DongDT, DuToan
from pabt.tien import D, vn_gon


class TestTienGon(unittest.TestCase):
    def test_vn_gon(self):
        self.assertEqual(vn_gon(D('185412000000')), '185,4 tỷ')
        self.assertEqual(vn_gon(D('23500000')), '23,5 triệu')
        self.assertEqual(vn_gon(D('950000')), '950.000')
        self.assertEqual(vn_gon(D('-2000000000')), '-2,0 tỷ')
        # làm tròn lên ngưỡng tỷ: không hiện "1.000,0 triệu"
        self.assertEqual(vn_gon(D('999960000')), '1,0 tỷ')
        self.assertEqual(vn_gon(D('999949999')), '999,9 triệu')

    def test_khong_nhan_so_vo_cuc(self):
        from pabt.lap_pa import LoiNhap, doc_so
        for s in ('nan', 'inf', 'Infinity', '1_000'):     # Decimal nhận các chữ này - trước đây NaN ném InvalidOperation
            with self.assertRaises(LoiNhap):
                doc_so(s, 'Số lượng')


class TestSoSanh(unittest.TestCase):
    def test_vuot_va_muc_6_theo_khai_toan(self):
        goc = DuToan(dong=[DongDT(1, 'Đất', 'm²', D(100), D(1000)), DongDT(2, 'Nhà', 'm²', D(10), D(5000)),
                           DongDT(6, 'Chi phí thực hiện', '%', phan_tram='2.5')])
        tt = DuToan(dong=[DongDT(1, 'Đất', 'm²', D(120), D(1000)), DongDT(2, 'Nhà', 'm²', D(10), D(5000))])
        kq = du_toan.so_sanh(goc, tt)
        m = {x[0]: x for x in kq['dong']}
        self.assertEqual((m[1][2], m[1][3], m[1][4]), (D(100000), D(120000), D(20000)))
        self.assertEqual(m[1][5], D(20))                                      # +20%
        # mục 6 của thực tế tính theo tỷ lệ 2,5% của khái toán (cùng cơ sở): 2,5% x 170.000 (làm tròn nghìn)
        self.assertEqual(m[6][3], D(4000))
        self.assertTrue(kq['vuot'])
        self.assertEqual(kq['tong'][1] - kq['tong'][0], kq['tong'][2])
        self.assertFalse(du_toan.so_sanh(tt, goc)['vuot'] and goc.tong <= tt.tong)
        self.assertEqual(len(tt.dong), 2)                                     # không sửa dự toán thực tế truyền vào


class CoSoCuaSo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')            # dự án gần đây ghi vào thư mục máy giả

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestCuaSoChinh(CoSoCuaSo):
    def test_man_hinh_chao_va_du_an_gan_day(self):
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)              # đóng (nhả file dự án) cả khi kiểm thử hỏng giữa chừng
        w.show()
        self.assertEqual(w.trang.currentIndex(), ud.TRANG_CHAO)             # chưa mở dự án: màn hình chào
        self.assertFalse(w.hang_the.isVisible())
        self.assertEqual(set(w.nut_chao), {'Dự án mới…', 'Mở dự án…', 'Nhập file Excel…', 'Tiếp nhận & Kiểm tra pháp lý dự án…'})
        self.assertEqual(w.lk_huong_dan.text(), 'Lịch sử cập nhật phần mềm')
        from PySide6.QtWidgets import QAbstractButton
        self.assertNotIn(w.lk_huong_dan, w.findChildren(QAbstractButton))   # liên kết chữ, không phải nút cạnh 3 lệnh
        from PySide6.QtCore import QPoint
        self.assertGreater(w.lk_huong_dan.mapTo(w, QPoint(0, 0)).y(),
                           w.ngan_gan_day.mapTo(w, QPoint(0, 0)).y())       # chân trang, dưới lưới dự án gần đây (0.9.80: trong ngăn xếp)
        self.assertEqual(w.ds_gan_day.rowCount(), 0)                        # chưa có dự án gần đây
        w.mo_trang(2)                                                       # trang cần dự án: vẫn màn hình chào
        self.assertEqual(w.trang.currentIndex(), ud.TRANG_CHAO)
        w.mo_trang(0)
        p = _du_an(self.td, 5)
        w.mo(str(p))
        self.assertEqual(w.trang.currentIndex(), 0)                         # mở dự án: về danh sách hộ
        self.assertTrue(w.hang_the.isVisible())
        self.assertEqual(ud.doc_gan_day()[0], str(p.resolve()))
        w.dong_du_an_lenh()
        self.assertIsNone(w.file)
        self.assertEqual(w.trang.currentIndex(), ud.TRANG_CHAO)
        self.assertEqual(w.ds_gan_day.item(0, 0).data(ud.Qt.ItemDataRole.UserRole), str(p.resolve()))
        w.ds_gan_day.cellDoubleClicked.emit(0, 0)                          # nhấp đúp dự án gần đây: mở
        self.assertEqual(w.file, Path(str(p.resolve())))
        w.close()

    def test_xoa_ho_theo_ho_dang_chon_va_the_so_loc(self):
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)              # đóng (nhả file dự án) cả khi kiểm thử hỏng giữa chừng
        w.show()
        w.mo(str(_du_an(self.td, 6)))
        self.assertFalse(w.lenh['Xóa hộ…'].isEnabled())                    # chưa chọn hộ
        self.assertFalse(hasattr(w, 'hang_chon'))                           # 0.9.66: hàng "Đã chọn N hộ" trùng menu trái: bỏ
        w.bang.selectRow(0)
        self.assertTrue(w.lenh['Xóa hộ…'].isEnabled())
        from PySide6.QtCore import QItemSelectionModel
        w.bang.selectionModel().select(w.loc.index(1, 0), QItemSelectionModel.SelectionFlag.Select |
                                       QItemSelectionModel.SelectionFlag.Rows)
        self.assertIn('Đã chọn: 2 hộ', w.lb_tom_tat.text())                 # số hộ chọn ở thanh trạng thái
        # thẻ số liệu bấm để lọc; Số hộ = bỏ lọc
        n = w.loc.rowCount()
        w.mo_trang(4)
        w.bam_the_so('da_pd')
        self.assertEqual(w.trang.currentIndex(), 0)
        self.assertEqual(w.cb_tt.currentData(), 'da_pd')
        self.assertEqual(w.loc.rowCount(), 0)                               # chưa hộ nào phê duyệt
        w.o_tim.setText('abc')
        w.bam_the_so('so_ho')
        self.assertEqual((w.cb_tt.currentData(), w.o_tim.text(), w.loc.rowCount()), ('', '', n))
        self.assertRegex(w.the_so['tong'].text(), r'^[0-9.,]+ (tỷ|triệu)$')   # tiền dạng gọn, đủ số ở chú thích
        self.assertTrue(w.the_so['tong'].toolTip().endswith('đồng'))
        w.close()

    def test_bang_tieu_de_theo_don_vi_du_an(self):
        from pabt import app as ud, to_chuc
        from tests.test_toc_do import _du_an
        p = _du_an(self.td, 3)
        from pabt import csdl
        con = csdl.mo(p)
        with con:
            con.execute("UPDATE du_an SET don_vi_lap = 'Ban Quản lý dự án thử', don_vi_cap_tren = 'UBND huyện Thử' WHERE id = 1")
        con.close()
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)              # đóng (nhả file dự án) cả khi kiểm thử hỏng giữa chừng
        self.assertEqual(w.bang_tieu_de.nhan_to_chuc.text(), to_chuc.TEN)  # chưa mở dự án: đơn vị mặc định của máy
        w.mo(str(p))
        self.assertEqual(w.bang_tieu_de.nhan_to_chuc.text(), 'BAN QUẢN LÝ DỰ ÁN THỬ')
        self.assertIn('UBND huyện Thử', w.bang_tieu_de.nhan_phu.text())
        w.dong_du_an_lenh()
        self.assertEqual(w.bang_tieu_de.nhan_to_chuc.text(), to_chuc.TEN)
        w.close()

    def test_trang_du_toan_va_so_sanh(self):
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)              # đóng (nhả file dự án) cả khi kiểm thử hỏng giữa chừng
        w.show()
        k = w.du_toan(cho=False)                                            # dùng được khi chưa mở dự án
        self.assertEqual(w.trang.currentIndex(), 3)
        self.assertTrue(w.lenh['Dự toán & khái toán'].isChecked())
        self.assertFalse(k.b_tu_du_an.isEnabled())
        k.im_lang = True
        w.mo(str(_du_an(self.td, 6)))
        self.assertEqual(w.trang.currentIndex(), 0)                         # 0.9.69: mở dự án -> Danh sách hộ
        w.mo_trang(ud.TRANG_DU_TOAN)
        self.assertTrue(k.b_tu_du_an.isEnabled())
        dt = k.lay('du_an')
        self.assertGreater(len(dt.dong), 0)
        k.them_chi_phi()
        # sửa một ô khối lượng: chỉ vẽ lại dòng đó + dòng % + tổng (không dựng lại các ô dòng khác)
        r = next(i for i, d in enumerate(k.dt.dong) if d.muc != 6)
        khac = next(i for i, d in enumerate(k.dt.dong) if d.muc != 6 and i != r) if len(k.dt.dong) > 3 else None
        o_khac = k.bang.item(khac, 1) if khac is not None else None
        c_kl = [c for c, (ten, _, _) in enumerate(__import__('pabt.man_hinh_du_toan', fromlist=['COT']).COT)
                if ten == 'khoi_luong'][0]
        tong_cu = k.dt.tong
        k.bang.item(r, c_kl).setText('=2*' + str(k.dt.dong[r].khoi_luong).replace('.', ','))
        self.assertGreater(k.dt.tong, tong_cu)
        if o_khac is not None:
            self.assertIs(k.bang.item(khac, 1), o_khac)                     # dòng khác giữ nguyên ô
        # so sánh: khái toán = bảng vừa sửa (lớn hơn thực tế) -> không vượt
        k.tab.setCurrentIndex(1)
        self.assertIsNotNone(k.ss)
        self.assertFalse(k.ss['vuot'])
        self.assertEqual(k.bang_ss.rowCount(), 7)                           # 6 mục + tổng
        self.assertIn('trong phạm vi', k.lb_ss.text())
        # khái toán đã duyệt nhỏ hơn thực tế: cảnh báo vượt
        f = DuToan(dong=[DongDT(1, 'Đất', 'm²', D(1), D(1000))]).luu(self.td / 'kt.pabtdt')
        kq = k.mo_khai_toan_goc(f)
        self.assertTrue(kq['vuot'])
        self.assertIn('VƯỢT', k.lb_ss.text())
        w.dong_du_an_lenh()
        self.assertFalse(k.b_tu_du_an.isEnabled())
        self.assertEqual(w.trang.currentIndex(), 3)                         # đóng dự án: trang dự toán vẫn dùng được
        w.close()

    def test_bang_gia_dat_va_huong_dan(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)              # đóng (nhả file dự án) cả khi kiểm thử hỏng giữa chừng
        d = w.bang_gia_dat(cho=False)
        self.assertGreater(d.bang.rowCount() if hasattr(d, 'bang') else 1, 0)
        d.close()
        self.assertIsNotNone(ud.file_huong_dan())
        h = w.huong_dan(cho=False)
        from PySide6.QtWidgets import QTextBrowser
        self.assertIn('LARC', h.findChild(QTextBrowser).toPlainText()[:500])   # 0.9.94: tên hiển thị LARC
        h.close()
        self.assertEqual(w.lenh['Hướng dẫn sử dụng'].shortcut().toString(), 'F1')
        w.close()


if __name__ == '__main__':
    unittest.main()
