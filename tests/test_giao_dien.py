"""Kiểm thử: màu giao diện, mẫu in không chứa dữ liệu cố định, giữ thông tin đơn vị, nạp danh mục, nâng cấp CSDL v3."""
from __future__ import annotations
import os
import sys
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an, lap_pa, nhap_tho
from tests.test_nghiep_vu import FILE_EXCEL
from tests.test_nhap_tho import _don_gian, _ghi

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestMauIn(unittest.TestCase):
    def test_mau_khong_chua_du_lieu_co_dinh(self):
        for ten in ('IN_CHITIET', 'IN_BANGTONGHOP'):
            ws = openpyxl.load_workbook(in_an.thu_muc_mau() / f'{ten}.xlsx').active
            chu = '\n'.join(c.value for r in ws.iter_rows() for c in r if isinstance(c.value, str))
            self.assertIsNone(re.search(r'Vĩnh Cửu|Đồng Nai|Phan Tuấn|Đinh Công|Phạm Xuân|CNVC', chu), ten)
            for k in ('{DON_VI_CAP_TREN', '{DON_VI_TIEU_DE}', '{nguoi_lap}', '{nguoi_ky}', '{CHUC_VU_KY}'):
                self.assertIn(k, chu, ten)


class TestBanInMau(unittest.TestCase):
    def test_duong_ke_va_thong_tin_mac_dinh(self):
        import zipfile
        from pabt import du_an_moi, to_chuc
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / 'a.pabt'
            du_an_moi.tao_du_an(p, dict(ten='Dự án X', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'),
                                [dict(ho_ten='A', so_to='74', so_thua='362', loai_dat='ONT', dt_thu_hoi='43,7', vi_tri='1')],
                                [dict(loai_dat='ONT', vi_tri='1', gia='1000000')])
            con = csdl.mo(p)
            try:
                with con:
                    con.execute("UPDATE du_an SET don_vi_cap_tren = '', don_vi_tieu_de = '', chuc_vu_ky = ''")
                da = in_an._thong_tin_du_an(con)              # ô trống: dùng thông tin tổ chức mặc định
                self.assertEqual(da['DON_VI_CAP_TREN_2DONG'], 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT\nTHÀNH PHỐ ĐỒNG NAI')
                self.assertEqual((da['DON_VI_TIEU_DE'], da['CHUC_VU_KY']), ('CHI NHÁNH VĨNH CỬU', 'PHÓ GIÁM ĐỐC'))
                f = in_an.lap_chi_tiet(con, 1, td / 'ct.xlsx')
            finally:
                con.close()
            ws = openpyxl.load_workbook(f).active                 # file vẫn mở được sau khi chèn hình
            self.assertEqual((ws['A2'].value, ws['B19'].value),
                             ('CHI NHÁNH VĨNH CỬU', 'Thửa đất số 362, tờ bản đồ số 74, loại đất ONT, xã Bàu Hàm (Vị trí 1)'))
            self.assertIn('PHÓ GIÁM ĐỐC', [c.value for r in ws.iter_rows() for c in r])
            with zipfile.ZipFile(f) as z:
                dr = [n for n in z.namelist() if n.startswith('xl/drawings/drawing')]
                self.assertEqual(len(dr), 1)
                self.assertEqual(z.read(dr[0]).decode('utf-8').count('prst="line"'), 3)
                self.assertIn('<drawing r:id=', z.read('xl/worksheets/sheet1.xml').decode('utf-8'))
            self.assertFalse(in_an.chen_duong_ke(f, in_an.thu_muc_mau() / 'IN_CHITIET.duong_ke.xml'))   # không chèn 2 lần
            self.assertEqual(to_chuc.MAC_DINH['chuc_vu_ky'], 'Phó Giám đốc')


class TestDonVi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.xl = self.td / 'ds.xlsx'
        _ghi(self.xl, _don_gian)
        self.p = self.td / 'a.pabt'
        nhap_tho.nhap(self.xl, self.p, 'Dự án A')

    def tearDown(self):
        self.tmp.cleanup()

    def test_thong_tin_in_va_giu_khi_xoa_trang(self):
        con = csdl.mo(self.p)
        gt = lap_pa.doc_du_an(con)
        gt.update(don_vi_cap_tren='Trung tâm X', don_vi_lap='Chi nhánh Y', nguoi_lap='Người Lập',
                  nguoi_kiem_tra='Người KT', chuc_vu_ky='Phó giám đốc', nguoi_ky='Người Ký')
        lap_pa.luu_du_an(con, gt)
        with con:                                                # 0.9.72: ký hiệu theo đợt; cột cũ của dự án vẫn là dự phòng
            con.execute("UPDATE du_an SET ky_hieu_so = 'PA-ABC'")
        da = in_an._thong_tin_du_an(con)
        self.assertEqual((da['DON_VI_CAP_TREN'], da['DON_VI_LAP'], da['CHUC_VU_KY'], da['nguoi_ky'], da['ky_hieu_so']),
                         ('TRUNG TÂM X', 'CHI NHÁNH Y', 'PHÓ GIÁM ĐỐC', 'Người Ký', 'PA-ABC'))
        con.close()
        nhap_tho.nhap(self.xl, self.p, 'Dự án B')                 # xóa trắng, nhập dự án mới
        moi = self.td / 'b.pabt'
        nhap_tho.nhap(self.xl, moi, danh_muc=self.p)             # dự án mới chép từ dự án cũ
        for f, ten in ((self.p, 'Dự án B'), (moi, 'ds')):
            con = csdl.mo(f)
            gt = lap_pa.doc_du_an(con)
            self.assertEqual((gt['ten'], gt['don_vi_lap'], gt['nguoi_ky']), (ten, 'Chi nhánh Y', 'Người Ký'))
            con.close()

    def test_nang_cap_v2(self):
        sql = Path(csdl.__file__).with_name('schema.sql').read_text(encoding='utf-8')
        sql = re.sub(r"(ngay_nhap +TEXT NOT NULL DEFAULT '')\s*,\s*-- in trên bản in.*?\n\);", r"\1\n);", sql, count=1, flags=re.S)
        self.assertNotIn('nguoi_ky', sql.split('CREATE TABLE IF NOT EXISTS ho')[0])
        self.p = self.td / 'v2.pabt'
        con = sqlite3.connect(self.p)
        con.executescript(sql)
        con.execute('PRAGMA user_version = 2')
        con.execute('INSERT INTO du_an (id) VALUES (1)')
        con.commit()
        con.close()
        with self.assertRaises(RuntimeError):
            csdl.mo(self.p, chi_doc=True)
        con = csdl.mo(self.p)
        self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        self.assertEqual(lap_pa.doc_du_an(con)['nguoi_ky'], '')
        con.close()

    @unittest.skipUnless(FILE_EXCEL.exists(), 'không có file Excel mẫu')
    def test_nap_danh_muc(self):
        dem = nhap_tho.nap_danh_muc(self.p, FILE_EXCEL)
        self.assertGreater(dem['dm_taisan'], 1000)
        con = csdl.mo(self.p)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 5)       # hồ sơ giữ nguyên
        con.close()
        with self.assertRaises(lap_pa.LoiNhap):
            nhap_tho.nap_danh_muc(self.p, self.xl)


@unittest.skipUnless(CO_QT, 'không có PySide6')
class TestMau(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_nhom_nut(self):
        from pabt.giao_dien import nhom_nut
        for chu, nhom in (('Lưu (Ctrl+S)', 'luu'), ('Thêm thửa', 'them'), ('Xóa hộ…', 'xoa'), ('Gộp hộ khác vào hộ này…', 'sua'),
                          ('In / Xuất…', 'in'), ('Nhập file Excel…', 'nhap'), ('Hồ sơ hộ…', 'hoso'),
                          ('Lập phương án hộ…', 'pa'), ('Rà soát giá…', 'tra'), ('◀ Hộ trước', 'tra'), ('Đóng', 'nhat'),
                          ('Nạp danh mục đơn giá…', 'nhap'), ('Tách theo loại đất', 'sua'), ('Mở chỉ xem', None),
                          ('Dự án mới…', 'pa'), ('Bộ đơn giá…', 'nhap'), ('Lưu: tạo dự án và lập phương án', 'luu'),
                          ('Tiếp ▶', 'tra'), ('◀ Quay lại', 'tra'), ('Áp bộ đơn giá vào dự án đang mở', 'sua'),
                          ('Kiểm tra cập nhật qua Internet', 'nhap'), ('Tra cứu văn bản mới…', 'tra')):
            self.assertEqual(nhom_nut(chu), nhom, chu)

    def test_cua_so_duoc_to_mau(self):
        from pabt import app as ud
        from pabt.giao_dien import ap_dung
        ap_dung(self.app)
        w = ud.CuaSoChinh()
        w.show()
        self.app.processEvents()
        from PySide6.QtWidgets import QToolButton
        nut = {b.text().rstrip('…'): b.property('nhom') for b in w.findChildren(QToolButton)}
        self.assertEqual(nut['Nhập file Excel'], 'nhap')            # Qt bỏ dấu … trên nút thanh lệnh
        self.assertEqual(nut['Lập phương án chi tiết'], 'pa')       # chữ trên menu (app.NHAN_MENU, 0.9.70)
        self.assertEqual(nut['Thêm hộ'], 'them')
        self.assertEqual(nut['Xuất hồ sơ && Bản in'], 'in')         # Mẫu in: thanh menu Công cụ (0.9.23)
        self.assertEqual(w.lb_du_an.property('vai'), 'bang_ten')
        self.assertIn('QHeaderView::section', self.app.styleSheet())
        w.close()
        from pabt.giao_dien import bo_ap_dung
        bo_ap_dung(self.app)

    def test_menu_trai_gon_va_bang_tieu_de(self):
        """0.9.23 (lộ trình người dùng): thao tác file ở thanh menu Tệp tin (không còn nút xổ "DỰ ÁN ▾" đè lên menu trái); menu
        trái 5 nhóm theo vòng đời, nhóm đóng / mở bằng tiêu đề (nhớ lại); băng tiêu đề có Hoàn tác / Làm lại."""
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QLabel
        from pabt import app as ud, giao_dien
        cai = QSettings('PABT', 'PABT')
        cu = cai.value(giao_dien.KHOA_NHOM_DONG, None)              # máy thật: trả lại lựa chọn của người dùng sau khi thử
        cai.remove(giao_dien.KHOA_NHOM_DONG)
        try:
            w = ud.CuaSoChinh(menu_trai=True)
            m = w.khung_menu
            self.assertFalse(getattr(m, 'nut_xo', {}))               # không còn nút xổ trong menu trái
            menu = {a.text().replace('&', ''): a.menu() for a in w.menuBar().actions() if a.menu() is not None}
            self.assertEqual(list(menu), ['Tệp tin', 'Chỉnh sửa', 'Dữ liệu', 'Công cụ', 'Cài đặt', 'Trợ giúp'])
            self.assertEqual(menu['Tệp tin'].actions()[:2], [w.lenh['Dự án mới…'], w.lenh['Mở dự án…']])
            self.assertIn(w.lenh['Nhập phương án chi tiết…'], menu['Dữ liệu'].actions())
            self.assertEqual(w.lenh['Dự án mới…'].shortcut().toString(), 'Ctrl+N')
            # 0.9.70 (đặc tả ARCH-PABT-2026-V7): Màn hình chính độc lập trên cùng + 6 nhóm
            self.assertEqual(list(m.tieu_de_nhom), ['1. Khái toán & dự toán', '2. Dự án triển khai', '3. Đơn giá & bảng giá',
                                                    '4. Lập phương án', '5. Tổng hợp & trình duyệt',
                                                    '6. Phê duyệt & bàn giao'])
            nut = {b.defaultAction(): b for b in m.findChildren(giao_dien.QToolButton) if b.defaultAction() is not None}
            for ten in ('Thêm hộ…', 'Xóa hộ…', 'Nhập file Excel…', 'Dự án mới…'):   # không phải màn hình điều hướng
                self.assertNotIn(w.lenh[ten], nut, ten)
            self.assertIn(w.lenh['Dự toán & khái toán'], nut)       # nhóm 1 Khái toán & dự toán
            self.assertIn(w.lenh['Màn hình chính'], nut)
            self.assertIn(w.lenh['So sánh với thực tế'], nut)
            self.assertEqual(m.nhom_dong, set(ud.NHOM_DONG_MAC_DINH))
            nut_bc = nut[w.lenh['Báo cáo tổng hợp…']]
            self.assertTrue(nut_bc.isHidden())                       # nhóm "Phê duyệt & bàn giao" đóng sẵn
            self.assertFalse(nut[w.lenh['Màn hình chính']].isHidden())   # nút độc lập: không thuộc nhóm nào, luôn hiện
            m.tieu_de_nhom['6. Phê duyệt & bàn giao'].bam()
            self.assertFalse(nut_bc.isHidden())
            self.assertIn('▾', m.tieu_de_nhom['6. Phê duyệt & bàn giao'].text())
            w.close()
            w2 = ud.CuaSoChinh(menu_trai=True)                       # nhớ nhóm đã mở
            self.assertNotIn('6. Phê duyệt & bàn giao', w2.khung_menu.nhom_dong)
            chu = ' '.join(x.text() for x in w2.findChildren(QLabel))
            self.assertNotIn('Tổ chức làm nhiệm vụ', chu)
            bang = next(f for f in w2.findChildren(giao_dien.QFrame) if f.property('vai') == 'bang_to_chuc')
            # 11/10/2026: Hoàn tác / Làm lại ở menu Chỉnh sửa trên thanh menu (không còn nút trên băng tiêu đề)
            self.assertEqual(list(w2.menu_tren)[:2], ['Tệp tin', 'Chỉnh sửa'])
            self.assertEqual(w2.menu_tren['Chỉnh sửa'].actions(), [w2.nut_ht['lui'], w2.nut_ht['toi']])
            self.assertFalse([b for b in bang.findChildren(giao_dien.QToolButton) if b.property('vai') == 'nut_bang'])
            self.assertTrue(w2.nut_ht['lui'].shortcut().isEmpty())   # Ctrl+Z do xu_ly_hoan_tac (theo khung đang làm việc)
            self.assertIn('\tCtrl+Z', w2.nut_ht['lui'].text())
            self.assertFalse(w2.nut_ht['lui'].isEnabled())           # chưa mở dự án
            import pabt                                              # nhãn "BẢN THỬ NGHIỆM" trên băng tiêu đề, tiêu đề cửa sổ
            tn = [x for x in bang.findChildren(QLabel) if x.property('vai') == 'thu_nghiem']
            self.assertEqual([x.text() for x in tn], ['BẢN THỬ NGHIỆM'] if pabt.BAN_THU_NGHIEM else [])
            self.assertEqual('BẢN THỬ NGHIỆM' in w2.windowTitle(), pabt.BAN_THU_NGHIEM)
            w2.close()
        finally:
            cai.remove(giao_dien.KHOA_NHOM_DONG)
            if cu is not None:
                cai.setValue(giao_dien.KHOA_NHOM_DONG, cu)


    def test_bo_cuc_gon_man_hinh_1366(self):
        """0.9.18: băng tiêu đề gọn (112 -> ~63 px, giữ đủ tên đơn vị / địa chỉ / Hoàn tác / BẢN THỬ NGHIỆM), nhãn dự án một
        dòng, không còn nút Bảng tổng hợp / Theo dõi tiến độ trùng menu trái, cửa sổ vừa màn hình 1366 (trước: tối thiểu 1449)."""
        # số px phụ thuộc phông (môi trường test offscreen dùng phông dự phòng rộng gần gấp đôi): kiểm tra cấu trúc. Đo thật
        # bằng phông Windows (1366x728, 110%): băng 63 px, bảng hộ 12 dòng (trước 8), rộng tối thiểu 1020 px (trước 1449).
        from PySide6.QtWidgets import QLabel, QPushButton
        from pabt import app as ud, giao_dien, to_chuc
        from pabt.man_hinh_theo_doi import KhungQuyetDinh
        giao_dien.ap_dung(self.app)
        try:
            w = ud.CuaSoChinh(menu_trai=True)
            w.resize(1366, 728)
            w.show()
            self.app.processEvents()
            bang = w.findChildren(giao_dien.BangToChuc)[0]
            from PySide6.QtWidgets import QWidget
            logo = next(x for x in bang.findChildren(QWidget) if x.property('vai') == 'logo')
            self.assertEqual(logo.height(), 32)
            # chữ dài trên băng: một dòng, rút gọn "…" khi hẹp - không xuống dòng (băng cao lên), không ép cửa sổ rộng ra
            self.assertFalse(any(x.wordWrap() for x in bang.findChildren(QLabel)))
            self.assertEqual({x.property('vai') for x in bang.findChildren(giao_dien.NhanRutGon)}, {'ten_phan_mem', 'dong_phu'})
            # hàng nút trang Quyết định phê duyệt tự xuống dòng (trước: một hàng 932 px)
            kq = w.findChildren(KhungQuyetDinh)[0]
            xep = kq.findChildren(giao_dien.XepDong)
            self.assertTrue(any(lo.indexOf(kq.nut['Xuất Excel…']) >= 0 for lo in xep))
            chu = ' '.join(x.text() for x in bang.findChildren(QLabel))         # chữ đầy đủ kể cả khi đang rút gọn "…"
            for k in (giao_dien.TEN_PHAN_MEM, to_chuc.TEN, to_chuc.DIA_CHI):
                self.assertIn(k, chu)
            # không nút nào trên màn hình chính lặp lệnh của menu trái (trước: Lập phương án hộ đang chọn, Thêm hộ…, Bảng tổng
            # hợp, Theo dõi tiến độ - nút trùng còn bỏ qua trạng thái tắt khi chỉ xem)
            def gon(s):
                return s.replace('…', '').replace(' đang chọn', '').strip().lower()
            lenh = {gon(t) for t in w.lenh}
            self.assertFalse({b.text() for b in w.findChildren(QPushButton) if gon(b.text()) in lenh})
            self.assertNotIn('Hồ sơ hộ…', w.lenh)                              # lệnh ẩn trùng thẻ "Thông tin hộ" của lập PA
            phu = next(x for x in bang.findChildren(giao_dien.NhanRutGon) if x.property('vai') == 'dong_phu')
            phu.resize(120, phu.height())
            self.assertTrue(QLabel.text(phu).endswith('…'))                     # hẹp: hiện rút gọn, tooltip đủ
            self.assertEqual(phu.toolTip(), phu.text())
            w.close()
        finally:
            giao_dien.bo_ap_dung(self.app)

    def test_lenh_menu_trai_theo_trang_dang_xem(self):
        """0.9.18: lệnh menu trái (Trạng thái hộ, Lập phương án…) lấy hộ đang chọn TRÊN TRANG ĐANG XEM - trước đây luôn lấy ở
        danh sách hộ (đang ẩn khi xem trang Tiến độ). Trang Tiến độ không còn nút riêng trùng "Trạng thái hộ…"."""
        from PySide6.QtWidgets import QPushButton
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        with tempfile.TemporaryDirectory() as td:
            os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
            try:
                p = _du_an(Path(td), 6)
                w = ud.CuaSoChinh(menu_trai=True)
                w.show()
                w.mo(str(p))
                w.bang.selectRow(0)
                ma_ds = w.ho_dang_chon()
                w.mo_trang(ud.TRANG_THEO_DOI)
                self.app.processEvents()
                b = w.tien_do.bang
                b.selectRow(b.rowCount() - 1)
                ma = w.tien_do.ma_da_chon()
                self.assertTrue(ma and ma[0] != ma_ds)
                self.assertEqual(w.ho_da_chon(), ma)
                self.assertEqual(w.trang_thai_ho(cho=False).ma_ho, ma[0])
                self.assertNotIn('Quyết định, chi trả, bàn giao của hộ…', {x.text() for x in w.tien_do.findChildren(QPushButton)})
                # 0.9.19: nhập quyết định chỉ còn ở trang Quyết định phê duyệt (nhóm Trình, theo dõi tiến độ), giữ ô chép file
                # quyết định vào thư mục hồ sơ như mục "Nhập quyết định…" cũ của menu trái
                self.assertNotIn('Nhập quyết định…', w.lenh)
                qd = w.quyet_dinh
                qd.im_lang = True
                d = qd.nhap_file()
                self.assertIsNotNone(d.thu_muc_ho_so)
                self.assertTrue(d.o_chep.isChecked())
                from PySide6.QtWidgets import QToolButton
                self.assertNotIn('Quy chuẩn cây, tài sản…', w.lenh)
                self.assertFalse(any('Quy chuẩn cây' in b.text() for b in w.khung_menu.findChildren(QToolButton)))
                w.mo_trang(0)
                self.assertEqual(w.ho_dang_chon(), ma_ds)                      # về danh sách hộ: lại lấy ở danh sách
                w.close()
            finally:
                os.environ.pop('PABT_THU_MUC_MAY', None)

    def test_mo_phong_to_va_khong_ep_rong(self):
        """11/10/2026 (lỗi hình góc phải khi mở): showMaximized ngay lúc tạo -> kiểu áp lúc Show làm bề rộng tối thiểu tăng, Qt ép
        lại kích thước sau khi phóng to (cửa sổ "phóng to" 1414 x 760, phần còn lại hiện cửa sổ phía sau). Kích thước thường đặt
        trước bằng vùng làm việc của màn hình rồi mới phóng to; hàng công cụ danh sách hộ xuống dòng được (XepDong), nhãn đối chiếu
        xuống dòng - không ép cửa sổ rộng hơn màn hình 1366 (kiểm cấu trúc: offscreen không có phông Windows, đo điểm ảnh không
        đúng)."""
        from unittest import mock
        from PySide6.QtWidgets import QApplication
        from pabt import app as ud, giao_dien
        with tempfile.TemporaryDirectory() as td:
            os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
            try:
                w = ud.CuaSoChinh(menu_trai=True)
                with mock.patch.object(w, 'showMaximized') as phong_to:
                    ud.hien_cua_so(w)
                    phong_to.assert_called_once()
                # 0.9.77 (đặc tả V10): kích thước THƯỜNG 1200 x 740 canh giữa (Restore Down trả về đây), không phải cả màn hình
                self.assertEqual(w.geometry(), giao_dien.kich_thuoc_thuong(w))
                vung = (w.screen() or QApplication.primaryScreen()).availableGeometry()
                self.assertEqual(w.geometry().size().width(), min(1200, vung.width()))
                self.assertEqual(w.geometry().size().height(), min(740, vung.height()))
                self.assertEqual((w.minimumWidth(), w.minimumHeight()), (min(1024, vung.width()), min(680, vung.height())))
                xep = [x for x in w.findChildren(giao_dien.XepDong)
                       if x.indexOf(w.nut_ds['Thêm hộ…'].parentWidget()) >= 0]
                self.assertEqual(len(xep), 1)                        # nút | bộ lọc: hai khối của một bố cục xuống dòng
                self.assertGreaterEqual(xep[0].indexOf(w.o_tim.parentWidget()), 0)
                self.assertTrue(w.lb_ket_qua.wordWrap())
                w.close()
            finally:
                os.environ.pop('PABT_THU_MUC_MAY', None)

    def test_trang_chu_va_bieu_tuong_menu(self):
        """Nút "Màn hình chính" đầu menu trái (về màn hình bắt đầu, dự án vẫn mở); mọi nút menu trái có biểu tượng (lệnh
        chưa có ký hiệu: biểu tượng trống - trước đây "Bảng giá đất" không biểu tượng, chữ bị căn ra giữa)."""
        from pabt import app as ud, giao_dien
        from tests.test_toc_do import _du_an
        with tempfile.TemporaryDirectory() as td:
            os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
            try:
                w = ud.CuaSoChinh(menu_trai=True)
                w.show()
                nut = [b for b in w.khung_menu.findChildren(giao_dien.QToolButton) if b.property('menu') == '1']
                self.assertTrue(nut)
                self.assertFalse([b.text() for b in nut if b.icon().isNull()])
                self.assertIsNotNone(giao_dien.ky_hieu_nut(w.lenh['Bảng giá đất NQ 28…'].text()))
                self.assertIsNotNone(giao_dien.ky_hieu_nut('Màn hình chính'))
                dau = next(b for b in nut if b.defaultAction() is w.lenh['Màn hình chính'])
                self.assertEqual(nut.index(dau), 0)                          # đầu nhóm "Dự án & dự toán"
                w.mo(str(_du_an(Path(td), 3)))
                self.assertEqual(w.trang.currentIndex(), 0)
                w.lenh['Màn hình chính'].trigger()
                self.assertEqual(w.trang.currentIndex(), ud.TRANG_CHAO)
                self.assertIsNotNone(w.con)                                  # dự án vẫn mở
                self.assertTrue(w.lenh['Màn hình chính'].isChecked())
                self.assertFalse(any(w.lenh[t].isChecked() for t in ud.TRANG))
                w.lenh[ud.TRANG[0]].trigger()                                # quay lại danh sách hộ
                self.assertEqual(w.trang.currentIndex(), 0)
                self.assertFalse(w.lenh['Màn hình chính'].isChecked())
                w.dong_du_an()
                w.close()
            finally:
                os.environ.pop('PABT_THU_MUC_MAY', None)

    def test_bieu_tuong_duy_nhat_co_vien(self):
        """0.9.74 (PABT Fluent Isometric 3D): biểu tượng cắt từ ảnh thiết kế - squircle navy, mái nhà vàng kim, khối thửa đất ngọc
        lục bảo; pabt/bieu_tuong.png 512 trong suốt ngoài góc bo, bieu_tuong.ico đủ cỡ; QIcon của phần mềm nhiều cỡ."""
        import struct
        from PySide6.QtGui import QImage
        from pabt import ve_bieu_tuong as vbt
        goc = Path(__file__).resolve().parents[1]
        self.assertFalse((goc / 'logo_PABT.png').exists())                   # bỏ bản nền xanh cũ
        anh = QImage(str(goc / 'pabt' / 'bieu_tuong.png'))
        self.assertEqual(anh.width(), 512)
        self.assertEqual(anh.pixelColor(3, 3).alpha(), 0)                    # ngoài góc bo: trong suốt
        self.assertGreater(anh.pixelColor(256, 256).alpha(), 250)

        def mau(x, y):
            c = anh.pixelColor(x, y)
            return c.red(), c.green(), c.blue()
        r, g, b = mau(40, 300)                                               # nền squircle: xanh dương (0.9.81: xanh hoàng gia sáng hơn)
        self.assertTrue(b > 100 and b > r + 60 and b > g + 30, (r, g, b))
        co_vang = any(c.red() > 170 and c.green() > 120 and c.blue() < 110
                      for c in (anh.pixelColor(x, y) for x in range(150, 360, 6) for y in range(110, 250, 6)))
        co_xanh = any(c.green() > 120 and c.green() > c.red() + 30 and c.green() > c.blue()
                      for c in (anh.pixelColor(x, y) for x in range(150, 360, 6) for y in range(230, 380, 6)))
        self.assertTrue(co_vang, 'thiếu mái nhà vàng kim')
        self.assertTrue(co_xanh, 'thiếu khối thửa đất xanh ngọc')
        du = (goc / 'pabt' / 'bieu_tuong.ico').read_bytes()
        n = struct.unpack('<HHH', du[:6])[2]
        self.assertEqual(n, len(vbt.CO_ICO))
        cos = [struct.unpack('<BBBBHHII', du[6 + 16 * k: 22 + 16 * k])[0] or 256 for k in range(n)]
        for s in (16, 24, 32, 48, 64, 128, 256):
            self.assertIn(s, cos)
        from pabt.giao_dien import bieu_tuong
        ds = sorted(z.width() for z in bieu_tuong().availableSizes())
        self.assertIn(16, ds)
        self.assertIn(256, ds)
        self.assertEqual(vbt.ve(32).width(), 32)

    def test_app_user_model_id(self):
        """Taskbar Windows nhận đúng biểu tượng PABT (không gộp vào python.exe): đặt AppUserModelID trước QApplication."""
        from pabt import app as ud
        self.assertEqual(ud.APP_USER_MODEL_ID, 'gov.pabt.boithuong.enterprise.2026')
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            self.assertTrue(ud.dat_app_user_model_id())
            p = wintypes.LPWSTR()
            ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(p))
            self.assertEqual(p.value, ud.APP_USER_MODEL_ID)
            ctypes.windll.ole32.CoTaskMemFree(p)
        import inspect
        nguon = inspect.getsource(ud.main)
        self.assertLess(nguon.index('dat_app_user_model_id()'), nguon.index('QApplication('))
        # 0.9.81: lối tắt Desktop / Start Menu của bộ cài mang CÙNG định danh (System.AppUserModel.ID) - lệch là taskbar tách hai nút
        import re
        ps1 = (Path(__file__).resolve().parents[1] / 'bo_cai_win' / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertEqual(re.search(r"\$APP_ID = '([^']+)'", ps1).group(1), ud.APP_USER_MODEL_ID)
        self.assertIn('9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3', ps1)               # PKEY_AppUserModel_ID
        self.assertIn('[PabtLoiTat]::Tao($lnk, $exe, $thu, $ico, $TEN, $APP_ID)', ps1)

    def test_xuat_danh_sach_ho(self):
        """Nút "Xuất" trên thanh công cụ danh sách hộ (11/10/2026): Excel các hộ đang lọc, hoặc các hộ đang chọn (từ 2 hộ); một
        QAction dùng chung với menu Dữ liệu, bật cả khi chỉ xem (chỉ đọc dự án)."""
        import openpyxl
        from PySide6.QtCore import QItemSelectionModel
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        with tempfile.TemporaryDirectory() as td:
            os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
            try:
                w = ud.CuaSoChinh(menu_trai=True)
                w.show()
                w.mo(str(_du_an(Path(td), 6)), chi_doc=True)
                a = w.lenh['Xuất danh sách hộ…']
                self.assertNotIn('Xuất danh sách hộ…', w.nut_ds)            # 0.9.66: chỉ ở menu Dữ liệu (bỏ nút trùng)
                self.assertIn(a, w.menu_tren['Dữ liệu'].actions())
                self.assertTrue(a.isEnabled())
                ten = {h['ma_ho']: h['o'][1] for h in w.mo_hinh.dong}
                w.o_tim.setText('Hộ thử 3')
                w.o_tim.phat_ngay()
                f = w.xuat_danh_sach(Path(td) / 'loc.xlsx', hoi=False)
                ws = openpyxl.load_workbook(f).active
                self.assertEqual(ws.cell(1, 1).value, 'DANH SÁCH HỘ BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ')
                self.assertIn('tìm "Hộ thử 3"', ws.cell(3, 1).value)
                loc = w.ho_dang_loc()
                self.assertTrue(0 < len(loc) < len(ten))
                self.assertTrue(ws.cell(3, 1).value.endswith(f' {len(loc)} hộ'), ws.cell(3, 1).value)
                self.assertEqual([ws.cell(6 + i, 2).value for i in range(len(loc))], loc)        # đúng hộ, đúng thứ tự đang hiện
                w.o_tim.setText('')
                w.o_tim.phat_ngay()
                sm = w.bang.selectionModel()
                for r in (1, 4):
                    sm.select(w.loc.index(r, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
                chon = w.ho_da_chon()
                self.assertEqual(len(chon), 2)
                f = w.xuat_danh_sach(Path(td) / 'chon.xlsx', hoi=False)
                ws = openpyxl.load_workbook(f).active
                self.assertTrue(ws.cell(3, 1).value.startswith('Điều kiện lọc: 2 hộ đang chọn'))
                self.assertEqual({ws.cell(6, 2).value, ws.cell(7, 2).value}, set(chon))
                self.assertEqual({ws.cell(6, 3).value, ws.cell(7, 3).value}, {ten[m] for m in chon})
                w.dong_du_an()
                w.close()
            finally:
                os.environ.pop('PABT_THU_MUC_MAY', None)

    def test_bang_tong_hop_3_the_va_lien_ket_phe_duyet(self):
        """0.9.76 (Nhóm 5 - 6): "Bảng tổng hợp kinh phí" là MỘT trang 3 thẻ (cơ cấu, chi tiết hộ, đối soát khái toán), không còn thẻ
        Quyết định phê duyệt; nút "Đi đến Phân hệ Phê duyệt" mở trang Quyết định phê duyệt (trang riêng, Nhóm 6). Tiêu đề trang
        không còn dòng nhắc "◀ bấm Danh sách hộ và Thửa…"."""
        from pabt import app as ud
        from tests.test_toc_do import _du_an
        with tempfile.TemporaryDirectory() as td:
            os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
            try:
                w = ud.CuaSoChinh(menu_trai=True)
                w.show()
                w.mo(str(_du_an(Path(td), 4)))
                self.assertTrue(w.lenh[ud.TRANG[0]].isChecked())                 # mở: đánh dấu Danh sách hộ
                self.assertEqual(list(w.bang_tong_hop.THE), ['Cơ cấu kinh phí dự án', 'Bảng kinh phí chi tiết',
                                                             'Đối soát dự toán Pre-F/S'])
                self.assertEqual(w.bang_tong_hop.tab.count(), 3)
                w.mo_trang(ud.TRANG_TONG_HOP)
                self.assertEqual(w.trang.currentIndex(), ud.STACK_TONG_HOP)
                self.assertTrue(w.lb_trang.text().startswith('BẢNG TỔNG HỢP KINH PHÍ'))
                for the in (2, 1, 0):
                    w.bang_tong_hop.tab.setCurrentIndex(the)                     # như người dùng bấm thẻ
                    self.app.processEvents()
                    self.assertEqual([k for k, t in enumerate(ud.TRANG) if w.lenh[t].isChecked()], [ud.TRANG_TONG_HOP])
                    self.assertIs(w._khung_dang_xem(), w.bang_tong_hop.tab.currentWidget())
                self.assertGreater(w.bang_tong_hop.co_cau.bang.rowCount(), 0)
                self.assertGreater(w.bang_tong_hop.tien.bang.rowCount(), 0)
                w.bang_tong_hop.b_phe_duyet.click()                              # liên kết sang Nhóm 6
                self.app.processEvents()
                self.assertEqual(w.trang.currentIndex(), ud.STACK_QUYET_DINH)
                self.assertEqual([k for k, t in enumerate(ud.TRANG) if w.lenh[t].isChecked()], [ud.TRANG_QUYET_DINH])
                self.assertEqual(w.lb_trang.text(), 'QUYẾT ĐỊNH PHÊ DUYỆT')       # không dòng nhắc "◀ bấm Danh sách hộ…"
                self.assertIs(w._khung_dang_xem(), w.quyet_dinh)
                for t in ud.TRANG[1:]:
                    w.lenh[t].trigger()
                    self.app.processEvents()
                    self.assertNotIn('◀', w.lb_trang.text())
                w.mo_trang(ud.TRANG_DS)
                self.assertFalse(w.lb_trang.isVisible())
                self.assertEqual([k for k, t in enumerate(ud.TRANG) if w.lenh[t].isChecked()], [0])
                w.close()
            finally:
                os.environ.pop('PABT_THU_MUC_MAY', None)

    def test_hop_ket_qua_vua_man_hinh(self):
        """Danh sách cần xem lại dài: hộp không cao quá màn hình, đủ mọi dòng trong ô cuộn (QMessageBox đẩy nút OK ra ngoài)."""
        from pabt.giao_dien import hop_ket_qua
        ds = [f'Sheet "{i}": dòng 2.{i} chưa có đơn giá trong file, lấy theo bộ đơn giá, tỷ lệ trống tính 100%.' for i in range(300)]
        d = hop_ket_qua(None, 'Đã nhập 25 hộ.', ds, hien=False)
        cao = self.app.primaryScreen().availableGeometry().height()
        self.assertLessEqual(d.height(), cao)
        self.assertEqual(d.o_ds.blockCount(), 300)
        d.close()
        self.assertIsNone(hop_ket_qua(None, 'Không có lưu ý.', [], hien=False).o_ds)


if __name__ == '__main__':
    unittest.main()


@unittest.skipUnless(CO_QT, 'cần PySide6 / PySide2')
class TestMenuBatLen(unittest.TestCase):
    def test_menu_exec_khong_sap(self):
        """Menu bật lên (chuột phải danh sách hộ, Tra cứu văn bản mới) mở / đóng được. Bản Win7 (PySide2): bí danh
        `QMenu.exec = QMenu.exec_` từng làm phần mềm SẬP (0xC0000005) - pabt._qt5_lam_qt6 gọi qua đối tượng."""
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        import pabt  # noqa: F401
        from PySide6.QtCore import QPoint, QTimer
        from PySide6.QtWidgets import QApplication, QMenu, QWidget
        app = QApplication.instance() or QApplication([])  # noqa: F841
        w = QWidget()
        m = QMenu(w)
        da = []
        a = m.addAction('Mục thử')
        a.triggered.connect(lambda: da.append(1))
        QTimer.singleShot(0, lambda: (a.trigger(), m.close()))
        m.exec(QPoint(0, 0))
        self.assertEqual(da, [1])
        w.close()
