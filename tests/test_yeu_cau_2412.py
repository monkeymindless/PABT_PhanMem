"""24/10/2026 (người dùng): đợt cải thiện giao diện in - hộp Xuất hồ sơ & Bản in (bảng hộ sắp xếp được, cột Đợt / Địa chỉ, bộ đếm dưới bảng,
bỏ nút thừa, nhớ lựa chọn), xem trước "Vừa ngang", ô nhập lề bảng tổng hợp trong Cấu hình nghiệp vụ, giãn dòng đầu bảng tổng hợp. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

import openpyxl
from PySide6.QtCore import Qt

from pabt import in_an
from tests.test_yeu_cau_0984 import APP, CoSoXem


class FakeCaiDat:
    """Thay QSettings: từ điển trong bộ nhớ."""

    def __init__(self):
        self.d = {}

    def value(self, k, mac_dinh=None):
        return self.d.get(k, mac_dinh)

    def setValue(self, k, v):
        self.d[k] = v


class TestHopIn(CoSoXem):
    def _hop(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p)
        h.im_lang = True
        self.addCleanup(h.w_preview.don_dep)
        return h

    def test_bang_ho_sau_cot_va_bo_nut_thua(self):
        h = self._hop()
        self.assertEqual(h.bang_ho.columnCount(), 6)
        self.assertEqual([h.bang_ho.horizontalHeaderItem(c).text() for c in (4, 5)], ['Đợt', 'Địa chỉ'])
        tieu_de_nut = {b.text() for b in h.findChildren(type(h.b_chon_het))}
        self.assertNotIn('Chọn tất cả mẫu (in đồng loạt)', tieu_de_nut)           # bỏ: chế độ phát hành đã tự chọn mẫu
        self.assertNotIn('Bỏ chọn mẫu', tieu_de_nut)
        self.assertNotIn('Chọn hộ đã lập', tieu_de_nut)                            # trùng ô "Hộ cần in"
        self.assertNotIn('Sửa mẫu…', tieu_de_nut)                                  # 05/11/2026: sửa mẫu ở cửa sổ Trình phê duyệt
        self.assertIn('Gửi cả lô', h.r_in.text())                                  # phân biệt với "In…" / "In nhanh" bản đang xem

    def test_sap_xep_theo_tien_va_xuat_theo_thu_tu_du_an(self):
        h = self._hop()
        h._danh_dau([h.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(h.bang_ho.rowCount())])
        goc = h.ds_ho()
        h._sap_xep(3)                                                              # tăng dần theo TIỀN (số, không theo chữ)
        tien = [float(h.tong.get(h.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole), 0)) for i in range(h.bang_ho.rowCount())]
        self.assertEqual(tien, sorted(tien))
        h._sap_xep(3)                                                              # lần hai: giảm dần
        tien = [float(h.tong.get(h.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole), 0)) for i in range(h.bang_ho.rowCount())]
        self.assertEqual(tien, sorted(tien, reverse=True))
        self.assertEqual(h.ds_ho(), goc)                                           # danh sách xuất vẫn theo thứ tự dự án
        h._sap_xep(3)                                                              # lần ba: về thứ tự gốc
        self.assertEqual([h.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(h.bang_ho.rowCount())], goc)
        h._sap_xep(0)                                                              # cột Chọn: không sắp xếp
        self.assertIsNone(h._cot_sx)

    def test_loc_theo_dia_chi(self):
        h = self._hop()
        dia_chi = h.bang_ho.item(0, 5).text()
        self.assertTrue(dia_chi)
        h._loc(dia_chi.split()[0])
        self.assertFalse(h.bang_ho.isRowHidden(0))

    def test_bo_dem_duoi_bang_khong_noi(self):
        h = self._hop()
        h.cap_nhat_bo_dem(h.bang_ho, dict(chuoi='Tổng số đếm: 3'))
        self.assertEqual(h.lb_bo_dem.text(), 'Tổng số đếm: 3')
        self.assertNotIn(h.lb_bo_dem, h.bang_ho.findChildren(type(h.lb_bo_dem)))        # không phải nhãn nổi trên bảng

    def test_the_che_do_thu_gon_the_nho(self):
        h = self._hop()
        h.dat_che_do('du_thao')
        self.assertTrue(h.o_bc.isHidden() and h.o_tt.isHidden())                   # Dự thảo: không có tờ trình, báo cáo ý kiến
        h.dat_che_do('chinh_thuc')
        self.assertFalse(h.o_bc.isHidden() or h.o_tt.isHidden())

    def test_khong_tao_cua_so_la(self):
        """Widget chưa có cha mà setVisible -> hiện thành cửa sổ riêng (đã gặp ở khung "Đầu ra và nơi lưu" 1.0.23)."""
        truoc = {w for w in APP.topLevelWidgets() if w.isVisible()}
        h = self._hop()
        h.show()
        APP.processEvents()
        la = [w for w in APP.topLevelWidgets() if w.isVisible() and w is not h and w not in truoc]
        self.assertEqual(la, [])
        self.assertFalse(h.khung_xuat_them.isWindow())
        for k in ('mot', 'nhieu', 'xuat', 'in'):                                   # đổi mục: phần ẩn / hiện không thành cửa sổ riêng
            h.dat_pham_vi(k)
            APP.processEvents()
        h.b_chon_ho.setChecked(True)
        APP.processEvents()
        self.assertEqual([w for w in APP.topLevelWidgets() if w.isVisible() and w is not h and w not in truoc], [])
        h.reject()

    def test_nho_lua_chon(self):
        cd = FakeCaiDat()
        with mock.patch('pabt.giao_dien.cai_dat_nho', lambda: cd):
            h = self._hop()
            h.r_excel.setChecked(True)
            h.o_gop.setChecked(False)
            h.o_so_ban.setValue(3)
            h._luu_lua_chon(self.td / 'ra' / 'BanIn_x')
            self.assertEqual(cd.d['in/dau_ra'], 'excel')
            self.assertNotIn('in/thu_muc_cha', cd.d)                               # 05/11/2026: không nhớ thư mục, luôn theo file dự án
            (self.td / 'ra').mkdir()
            h2 = self._hop()                                                       # mở lại: nhớ đầu ra, gộp PDF, số bản, thư mục cha
            self.assertTrue(h2.r_excel.isChecked())
            self.assertFalse(h2.o_gop.isChecked())
            self.assertEqual(h2.o_so_ban.value(), 3)
            self.assertFalse(h2.o_thu_muc.text().startswith(str(self.td / 'ra')))
            cd.d['in/dau_ra'] = 'in'                                               # "in ra máy" KHÔNG được nhớ: tránh in nhầm
            h3 = self._hop()
            self.assertTrue(h3.r_pdf.isChecked() and not h3.r_in.isChecked())


class TestXemVuaNgang(CoSoXem):
    def test_vua_ngang_to_hon_vua_trang(self):
        from pabt import xem_truoc_tai_lieu as xt
        if not xt.co_qtpdf():
            self.skipTest('Qt5: không có QtPdf')
        k = xt.KhungXemTruocTaiLieu()
        self.addCleanup(k.don_dep)
        k.resize(520, 900)
        k.show()
        APP.processEvents()
        self.assertTrue(k.nap_tai_lieu(self.mau_pdf))
        APP.processEvents()
        self.assertTrue(k.b_ngang.isEnabled())
        vua_trang = k.he_so()
        k.vua_ngang()
        self.assertGreaterEqual(k.he_so(), vua_trang - 1e-6)                       # khung cao: vừa ngang >= vừa trang
        self.assertFalse(k._vua)


class TestLeVaGianDong(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))

    def test_o_nhap_le_ghi_ho_so_va_ap_vao_ban_in(self):
        from pabt import dia_phuong
        from pabt.man_hinh_cau_hinh import HopCauHinhNghiepVu
        d = HopCauHinhNghiepVu()
        d.im_lang = True
        self.addCleanup(d.deleteLater)
        # mặc định: trái 2,0 / phải 1,0 / trên 1,5 / dưới 1,5 cm
        self.assertEqual({k: o.value() for k, o in d.o_le.items()}, dict(left=2.0, right=1.0, top=1.5, bottom=1.5))
        d.o_le['left'].setValue(3.0)
        d.o_le['bottom'].setValue(2.0)
        hs = d.gia_tri()['ban_in']['le_trang']['tong_hop']
        self.assertAlmostEqual(hs['left'], 3.0 / 2.54, places=3)
        self.assertTrue(d.luu())
        ws = openpyxl.Workbook().active
        le = in_an.chuan_le_trang(ws, 'tong_hop')
        self.assertAlmostEqual(le['left'] * 2.54, 3.0, places=2)
        self.assertAlmostEqual(le['bottom'] * 2.54, 2.0, places=2)
        self.assertAlmostEqual(le['right'] * 2.54, 1.0, places=2)                  # lề không đổi: giữ mặc định
        d2 = HopCauHinhNghiepVu()                                                  # mở lại: hiện số đã lưu
        self.addCleanup(d2.deleteLater)
        self.assertAlmostEqual(d2.o_le['left'].value(), 3.0, places=2)
        dia_phuong.khoi_phuc_mac_dinh()

    def test_doi_ten_don_vi_hien_ngay_tren_bang_tieu_de(self):
        """Đổi tên tổ chức ở Cấu hình nghiệp vụ > Cơ quan khi CHƯA mở dự án: dòng đơn vị trên băng tiêu đề đổi ngay (trước: chờ mở dự án)."""
        from pabt import dia_phuong, giao_dien
        from pabt.app import CuaSoChinh
        giao_dien.ap_dung(APP)
        w = CuaSoChinh()
        self.addCleanup(w.close)
        dia_phuong.dat_muc_may(('co_quan', 'ten'), 'CÔNG TY MẪU - CHI NHÁNH THỬ')
        self.addCleanup(dia_phuong.khoi_phuc_mac_dinh)
        w._lam_moi_don_vi()
        self.assertEqual(w.lb_don_vi.text(), 'CÔNG TY MẪU - CHI NHÁNH THỬ')

    def test_gian_dong_dau_gon_hon(self):
        ws = openpyxl.Workbook().active
        ws['A1'].font = openpyxl.styles.Font(name='Times New Roman', sz=14)
        in_an.gian_dong_dau_bth(ws)
        h1, h2 = ws.row_dimensions[1].height, ws.row_dimensions[2].height
        self.assertLess(h1, 26.8)                                                  # trước: 26,8 pt (1,9 lần cỡ chữ)
        self.assertGreater(h2, h1)                                                 # dòng 2 chừa chỗ cho đường kẻ dưới "CHI NHÁNH"
        self.assertGreaterEqual(h2, 14 * 1.2 + in_an.DK_CACH)


if __name__ == '__main__':
    unittest.main()
