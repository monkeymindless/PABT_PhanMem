"""0.9.70 - đặc tả ARCH-PABT-2026-V7 (người dùng 12/10/2026): menu trái "Màn hình chính" độc lập + 6 nhóm, khối 7 trường thông
tin chuẩn bị đầu tư của Khái toán (lưu trong .pabtdt, không phụ thuộc .pabt), Niêm yết & Lấy ý kiến 4 thẻ. Số liệu GIẢ LẬP."""
from __future__ import annotations
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QToolButton

from pabt import csdl, du_toan
from tests.test_toc_do import _du_an


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)


class TestThongTinChuanBi(_Co):
    def test_luu_mo_pabtdt(self):
        dt = du_toan.DuToan(ten='Đường giả lập', chu_dau_tu='Ban QLDA thử', nguon_von=du_toan.NGUON_VON[0],
                            dia_ban='Xã Thử', quy_mo_dt='15,5 ha', so_thua_dk='120', so_ho_dk='85')
        p = dt.luu(self.td / 'kt')
        self.assertEqual(p.suffix, du_toan.DUOI)
        du = json.loads(p.read_text(encoding='utf-8'))
        for k in du_toan.TRUONG_CHUAN_BI:
            self.assertEqual(du[k], getattr(dt, k))
        x = du_toan.DuToan.mo(p)
        self.assertEqual([getattr(x, k) for k in du_toan.TRUONG_CHUAN_BI],
                         ['Đường giả lập', 'Ban QLDA thử', 'Vốn đầu tư công', 'Xã Thử', '15,5 ha', '120', '85'])
        cu = self.td / 'cu.pabtdt'                                     # file dự toán trước 0.9.70: chưa có các trường mới
        cu.write_text(json.dumps(dict(phien_ban=1, ten='Cũ', dong=[])), encoding='utf-8')
        x = du_toan.DuToan.mo(cu)
        self.assertEqual((x.ten, x.chu_dau_tu, x.nguon_von, x.so_ho_dk), ('Cũ', '', '', ''))

    def test_khung_du_toan_doc_lap_voi_du_an(self):
        from pabt.man_hinh_du_toan import KhungDuToan
        p = _du_an(self.td, so_ho=3)
        k = KhungDuToan()
        k.im_lang = True
        self.addCleanup(k.close)
        self.assertEqual(list(k.o_cb), list(du_toan.TRUONG_CHUAN_BI))     # đủ 7 ô, đúng thứ tự đặc tả
        k.o_ten.setText('Khái toán riêng')
        k.o_chu_dau_tu.setText('Chủ đầu tư thử')
        k.cb_nguon_von.setCurrentIndex(k.cb_nguon_von.findData(du_toan.NGUON_VON[1]))
        k.o_so_ho.setText('85')
        self.assertEqual((k.dt.ten, k.dt.nguon_von), ('Khái toán riêng', du_toan.NGUON_VON[1]))
        # lấy khối lượng từ file .pabt: thông tin đã gõ giữ nguyên, ô trống (địa bàn) mới lấy theo file
        k.lay('pabt', p)
        self.assertTrue(k.dt.dong)
        self.assertEqual((k.o_ten.text(), k.o_chu_dau_tu.text(), k.o_so_ho.text()),
                         ('Khái toán riêng', 'Chủ đầu tư thử', '85'))
        self.assertEqual(k.cb_nguon_von.currentData(), du_toan.NGUON_VON[1])
        self.assertIn('Bàu Hàm', k.o_dia_ban.text())
        f = k.luu(self.td / 'kt.pabtdt')
        k2 = KhungDuToan()                                              # mở lại không cần dự án .pabt nào
        k2.im_lang = True
        self.addCleanup(k2.close)
        k2.mo(str(f))
        self.assertEqual(k2.o_chu_dau_tu.text(), 'Chủ đầu tư thử')
        self.assertEqual(k2.cb_nguon_von.currentText(), du_toan.NGUON_VON[1])
        self.assertEqual(len(k2.dt.dong), len(k.dt.dong))               # bảng dự toán giữ nguyên


class TestMenuTrai(_Co):
    def test_man_hinh_chinh_doc_lap_va_6_nhom(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        L = w.lenh
        m = w.khung_menu
        nut = [b.defaultAction() for b in m.findChildren(QToolButton) if b.defaultAction() is not None]
        self.assertIs(nut[0], L['Màn hình chính'])                      # đỉnh menu, trước mọi nhóm
        self.assertEqual(list(m.tieu_de_nhom), ['1. Khái toán & dự toán', '2. Dự án triển khai', '3. Đơn giá & bảng giá',
                                                '4. Lập phương án', '5. Tổng hợp & trình duyệt',
                                                '6. Phê duyệt & bàn giao'])
        self.assertEqual(nut[1:], [L[k] for k in (
            'Dự toán & khái toán', 'So sánh với thực tế', 'Thông tin dự án…', 'Danh sách hộ', 'Bộ đơn giá…',
            'Đơn giá riêng dự án…', 'Bảng giá đất NQ 28…', 'Lập phương án hộ…', 'Dự thảo PABT…', 'Bản đồ thửa đất', 'Kiểm tra lỗi…',
            'Xuất báo cáo đối chiếu…', 'Tổng hợp tiền theo phương án', 'Đợt trình…', 'In / Xuất…', 'Quyết định phê duyệt',
            'Theo dõi tiến độ', 'Báo cáo tổng hợp…')])
        nhan = {k: L[k].text().replace('&&', '&') for k in ('Dự toán & khái toán', 'Danh sách hộ', 'Lập phương án hộ…',
                                                            'Kiểm tra lỗi…', 'Xuất báo cáo đối chiếu…', 'Đợt trình…',
                                                            'In / Xuất…', 'Theo dõi tiến độ', 'Báo cáo tổng hợp…')}
        self.assertEqual(list(nhan.values()), ['Lập khái toán & Dự toán', 'Danh sách hộ và Thửa', 'Lập phương án chi tiết',
                                               'Kiểm tra lỗi pháp lý', 'Đối chiếu số liệu', 'Đợt trình thẩm định',
                                               'Xuất hồ sơ & Bản in', 'Theo dõi chi trả & Bàn giao', 'Báo cáo tiến độ GPMB'])
        # lệnh rời menu trái vẫn còn đúng một chỗ trên thanh menu
        self.assertIn(L['Cập nhật bảng giá đất…'], w.menu_tren['Công cụ'].actions())
        self.assertIn(L['Trạng thái hộ…'], w.menu_tren['Dữ liệu'].actions())
        for k in ('Cập nhật bảng giá đất…', 'Trạng thái hộ…'):
            self.assertNotIn(L[k], nut)
        # KPI ngoài cửa sổ chính giữ nguyên (6 thẻ)
        self.assertEqual(len(w.the_so), 6)
        # So sánh với thực tế: trang Khái toán, thẻ So sánh - dùng được khi chưa mở dự án
        k = w.so_sanh_du_toan()
        self.assertEqual(k.tab.currentIndex(), 1)
        self.assertEqual(w.trang.currentIndex(), 3)


class TestNiemYet(_Co):
    def test_bon_the_con(self):
        from pabt.man_hinh_du_thao import KhungDuThao
        p = _du_an(self.td, so_ho=3)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        k = KhungDuThao(con)
        self.addCleanup(k.close)
        self.assertEqual([k.tabs.tabText(i).replace('&&', '&') for i in range(k.tabs.count())],
                         ['1. Niêm yết công khai', '2. Lấy ý kiến nhân dân', '3. Đối thoại & Tiếp thu',
                          '4. Tổng hợp kết quả ý kiến'])
        self.assertTrue(k.tabs.widget(0).isAncestorOf(k.bang_vm))        # hộ vướng nằm trong thẻ Niêm yết công khai
        for i in range(k.tabs.count()):
            self.assertNotRegex(k.tabs.tabText(i), r'\d+ ngày')          # không ghi cứng số ngày trên tên thẻ


if __name__ == '__main__':
    unittest.main()
