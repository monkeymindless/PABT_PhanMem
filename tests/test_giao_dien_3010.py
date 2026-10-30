"""30/10/2026 (người dùng, ảnh màn hình): ô xổ xuống hiện đủ mục / đủ chữ, màu chọn dịu mắt; không lặp tên đơn vị lập trên tiêu đề bản in;
bảng tổng hợp luôn đủ khung kẻ ô; xem trước bản Excel nhiều hộ; Hộ vướng đổi trạng thái một chạm; hàng Tái định cư giãn hết chỗ trống.
Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QWidget

from pabt import csdl, du_thao, giao_dien
from tests.test_toc_do import _du_an
from tests.test_yeu_cau_0984 import CoSoXem, _pdf_nhieu_trang
from tests.test_yeu_cau_2411 import _gia_nhieu

N = chr(10)


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
        self.p = _du_an(self.td, so_ho=4)
        self.con = csdl.mo(self.p)
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]


class TestTenCoQuanKhongLap(unittest.TestCase):
    def test_bo_dong_trung_chi_nhanh(self):
        from pabt.in_word import dong_co_quan
        tt = 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT'
        lap = tt + ' CHI NHÁNH VĨNH CỬU'
        for cap, tieu in ((f'SỞ X{N}{tt}', lap),                 # ô dòng 2 trống -> lấy đơn vị lập
                          ('SỞ X', lap),                           # ô dòng 2 ghi cả tên đơn vị lập
                          (f'SỞ X{N}{lap}', 'CHI NHÁNH VĨNH CỬU'),  # ô cấp trên ghi cả tên đơn vị lập
                          (f'SỞ X{N}{tt}', 'CHI NHÁNH VĨNH CỬU')):
            self.assertEqual(dong_co_quan(dict(DON_VI_CAP_TREN_2DONG=cap, DON_VI_TIEU_DE=tieu, DON_VI_LAP=lap)),
                             (f'SỞ X{N}{tt}', 'CHI NHÁNH VĨNH CỬU'), (cap, tieu))


class TestKhungBangTongHop(_Co):
    def test_dam_bao_khung(self):
        from openpyxl import load_workbook
        from openpyxl.styles.borders import Border

        from pabt import in_an
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx', None)
        ws = load_workbook(f).active
        self.assertEqual(in_an.dam_bao_khung_bth(ws, 25), 0)            # bảng vừa lập đã đủ khung
        for r in range(13, 18):
            for c in range(1, 26):
                ws.cell(r, c).border = Border()
        self.assertGreater(in_an.dam_bao_khung_bth(ws, 25), 0)
        self.assertEqual(in_an.dam_bao_khung_bth(ws, 25), 0)

        def net(r, c, canh):
            return bool(getattr(getattr(ws.cell(r, c).border, canh), 'style', None))

        def cung_gop(a, b):
            return any(a in m and b in m for m in ws.merged_cells.ranges)
        for r in range(13, 18):                                          # mọi cạnh giữa hai ô hiện đều có nét (ô này hoặc ô kề),
            for c in range(2, 12):                                       # trừ cạnh bên trong một vùng gộp
                if not cung_gop(ws.cell(r, c).coordinate, ws.cell(r, c - 1).coordinate):
                    self.assertTrue(net(r, c, 'left') or net(r, c - 1, 'right'), (r, c))
                if not cung_gop(ws.cell(r, c).coordinate, ws.cell(r - 1, c).coordinate):
                    self.assertTrue(net(r, c, 'top') or net(r - 1, c, 'bottom'), (r, c))


class TestOChon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_qss_danh_sach_xo_va_mau_diu(self):
        qss = giao_dien._qss_day_du()
        self.assertIn('combobox-popup: 0', qss)                          # danh sách dưới ô, không kiểu menu đè lên ô
        self.assertIn(giao_dien.MAU_CHON_DIU[0], qss)
        self.assertNotIn('selection-background-color: #2563EB', qss)
        from PySide6.QtGui import QPalette
        p = giao_dien.bang_mau_ung_dung()
        self.assertEqual(p.color(QPalette.ColorRole.Highlight).name().upper(), giao_dien.MAU_CHON_DIU[0].upper())

    def test_danh_sach_xo_rong_du_chu(self):
        w = QWidget()
        self.addCleanup(w.deleteLater)
        cb = QComboBox(w)
        cb.addItems(['Ngắn', 'Đủ điều kiện theo khoản 4 Điều 111 Luật Đất đai năm 2024 (hộ có nhiều thế hệ cùng chung sống)'])
        cb.setFixedWidth(120)
        w.show()
        cb.showPopup()
        self.app.processEvents()
        khung = cb.view().parentWidget()
        self.assertEqual(khung.metaObject().className(), 'QComboBoxPrivateContainer')
        giao_dien.vua_danh_sach_xo(khung)
        self.assertGreaterEqual(khung.width(), min(cb.view().sizeHintForColumn(0), khung.screen().availableGeometry().width() - 16))
        self.assertGreater(khung.width(), cb.width())
        cb.hidePopup()


class TestXepDongGian(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_khoi_gian_nhan_phan_du(self):
        w = QWidget()
        self.addCleanup(w.deleteLater)
        xd = giao_dien.XepDong(w, 10)
        a, b, c = QLabel('Nhân khẩu: 4'), QLabel('DT: 120'), QComboBox()
        for x in (a, b, c):
            xd.addWidget(x)
        xd.gian(c)
        xd.setGeometry(QRect(0, 0, 1200, 30))
        self.assertEqual(a.width(), a.sizeHint().width())
        self.assertEqual(b.width(), b.sizeHint().width())
        self.assertEqual(c.geometry().right(), 1199 - xd.contentsMargins().right())   # khối giãn tới hết dòng


class TestHoVuongMotCham(_Co):
    def test_vong_trang_thai(self):
        ma = self.ma[0]
        self.con.execute('UPDATE ho SET du_dieu_kien = 0, ma_vuong = "", ghi_chu_phap_ly = "giữ ghi chú" WHERE ma_ho = ?', (ma,))
        self.con.commit()
        thay = [du_thao.doi_vuong_nhanh(self.con, ma) for _ in range(len(du_thao.VONG_VUONG))]
        self.assertEqual(thay, list(du_thao.VONG_VUONG[1:]) + ['chua'])
        r = self.con.execute('SELECT du_dieu_kien, ma_vuong, ghi_chu_phap_ly FROM ho WHERE ma_ho = ?', (ma,)).fetchone()
        self.assertEqual(tuple(r), (0, '', 'giữ ghi chú'))
        du_thao.doi_vuong_nhanh(self.con, ma)                                     # -> Đủ điều kiện
        self.assertNotIn(ma, [h['ma_ho'] for h in du_thao.ds_vuong(self.con)])
        giu = [h for h in du_thao.ds_vuong(self.con, {ma}) if h['ma_ho'] == ma]
        self.assertEqual(giu[0]['ten_vuong'], du_thao.TEN_DU_DIEU_KIEN)

    def test_bam_o_nhom_vuong(self):
        self.con.execute('UPDATE ho SET du_dieu_kien = 0, ma_vuong = ""')
        self.con.commit()
        from pabt.man_hinh_du_thao import KhungDuThao
        k = KhungDuThao(self.con)
        self.addCleanup(k.close)
        k.show()
        self.app.processEvents()
        b = k.bang_vm
        self.assertEqual(b.rowCount(), len(self.ma))
        ma = b.item(0, 0).data(0x0100)
        b.cellClicked.emit(0, 3)                                                  # một chạm -> Đủ điều kiện, dòng vẫn còn
        self.assertEqual(self.con.execute('SELECT du_dieu_kien FROM ho WHERE ma_ho = ?', (ma,)).fetchone()[0], 1)
        r = next(i for i in range(b.rowCount()) if b.item(i, 0).data(0x0100) == ma)
        self.assertEqual(b.item(r, 3).text(), du_thao.TEN_DU_DIEU_KIEN)
        b.cellClicked.emit(r, 3)                                                  # -> V1
        self.assertEqual(self.con.execute('SELECT ma_vuong FROM ho WHERE ma_ho = ?', (ma,)).fetchone()[0], 'V1')
        b.cellClicked.emit(r, 1)                                                  # cột khác: không đổi
        self.assertEqual(self.con.execute('SELECT ma_vuong FROM ho WHERE ma_ho = ?', (ma,)).fetchone()[0], 'V1')


class TestThemHoVaoDot(_Co):
    def test_loc_sap_xep_va_them_ho_chua_du(self):
        m1, m2, m3, m4 = self.ma
        self.con.execute('UPDATE ho SET du_dieu_kien = 1, ma_vuong = ""')
        self.con.execute('UPDATE ho SET du_dieu_kien = 0, ma_vuong = "V2" WHERE ma_ho = ?', (m3,))
        self.con.execute('UPDATE ho SET du_dieu_kien = 0, ma_vuong = "" WHERE ma_ho = ?', (m4,))
        self.con.commit()
        dot1 = du_thao.tao_dot(self.con, 'Đợt 1', '01/10/2026', 'UBND xã')
        du_thao.them_thu_cong(self.con, dot1, [m1])
        dot2 = du_thao.tao_dot(self.con, 'Đợt 2', '15/10/2026', 'UBND xã')
        ds = du_thao.ds_ho_cho_dot(self.con, dot2)
        theo = {h['ma_ho']: h for h in ds}
        self.assertEqual(set(theo), set(self.ma))                       # mọi hộ chưa ở đợt 2, kể cả hộ chưa đủ điều kiện
        self.assertEqual((theo[m1]['dot_hien'], theo[m1]['ten_y_kien']), ('Đợt 1', 'Chưa lấy ý kiến'))
        self.assertEqual(theo[m2]['ten_y_kien'], 'Chưa vào đợt nào')
        self.assertEqual((theo[m3]['dieu_kien'], theo[m4]['dieu_kien']), ('V2', 'chua'))
        from pabt.man_hinh_du_thao import HopThemHo
        h = HopThemHo(None, self.con, dot2)
        self.addCleanup(h.deleteLater)
        self.assertEqual(h.ma_chon(), [m1, m2])                         # đủ điều kiện, không vướng: đánh dấu sẵn
        h.cb_dk.setCurrentIndex(h.cb_dk.findData('vuong'))
        self.assertEqual([h._h(r)['ma_ho'] for r in range(h.bang.rowCount()) if not h.bang.isRowHidden(r)], [m3])
        h.cb_dk.setCurrentIndex(0)
        h.cb_dot.setCurrentIndex(h.cb_dot.findData(0))                  # chưa thuộc đợt nào
        self.assertNotIn(m1, [h._h(r)['ma_ho'] for r in range(h.bang.rowCount()) if not h.bang.isRowHidden(r)])
        h.cb_dot.setCurrentIndex(0)
        h.bang.sortByColumn(1, h.bang.horizontalHeader().sortIndicatorOrder().DescendingOrder)   # sắp xếp: thứ tự ngược
        self.assertEqual(h._h(0)['ma_ho'], max(self.ma, key=lambda m: dict((x['ma_ho'], x['thu_tu']) for x in ds)[m]))
        self.assertEqual(h.ma_chon(), [m1, m2])                         # ma_chon không đổi theo cách sắp
        r3 = next(r for r in range(h.bang.rowCount()) if h._h(r)['ma_ho'] == m3)
        self.assertFalse(h.ca_chua())
        h.bang.item(r3, 0).setCheckState(h.bang.item(r3, 0).checkState().Checked)
        self.assertTrue(h.ca_chua())                                    # đánh dấu hộ vướng: tự bật ô cho phép
        them, bo = du_thao.them_thu_cong(self.con, dot2, h.ma_chon(), ca_vuong=h.ca_chua())
        self.assertEqual((them, bo), (3, 0))
        self.assertEqual(du_thao.them_thu_cong(self.con, dot1, [m3]), (0, 1))   # mặc định vẫn bỏ qua hộ vướng


class TestTaiDinhCuGian(_Co):
    def test_o_tdc_gian(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma[0])
        self.addCleanup(w.close)
        self.addCleanup(w.bo_thay_doi)
        cb = w.bang[4].cb_tdc
        self.assertEqual(cb.sizePolicy().horizontalPolicy(), cb.sizePolicy().horizontalPolicy().Expanding)
        self.assertGreaterEqual(cb.minimumWidth(), 280)


class TestXemTruocExcel(CoSoXem):
    def setUp(self):
        super().setUp()
        self.mau2 = _pdf_nhieu_trang(self.td / 'mau2.pdf', 2)
        from pabt import xem_truoc_tai_lieu as xt
        v = mock.patch.object(xt, 'chuyen_pdf_nhieu', _gia_nhieu(self.mau2))
        v.start()
        self.addCleanup(v.stop)

    def test_xem_truoc_excel_cac_ho(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p)
        h.im_lang = True
        self.addCleanup(h.w_preview.don_dep)
        self.assertTrue(h.b_xem_excel.text().startswith('Xem trước bản Excel'))
        h._danh_dau([r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')][:2])
        khoa = h.xem_truoc_excel_chi_tiet(ngay=True)
        self.assertEqual(khoa[0], 'excel_ct')
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertEqual(len(h.w_preview.muc_luc), 2)
        h._danh_dau([])
        self.assertIsNone(h.xem_truoc_excel_chi_tiet(ngay=True))


if __name__ == '__main__':
    unittest.main()
