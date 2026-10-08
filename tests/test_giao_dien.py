"""Kiểm thử: màu giao diện, mẫu in không chứa dữ liệu cố định, giữ thông tin đơn vị, nạp danh mục, nâng cấp CSDL v3."""
from __future__ import annotations
import os
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
        gt.update(don_vi_cap_tren='Trung tâm X', don_vi_lap='Chi nhánh Y', ky_hieu_so='PA-ABC', nguoi_lap='Người Lập',
                  nguoi_kiem_tra='Người KT', chuc_vu_ky='Phó giám đốc', nguoi_ky='Người Ký')
        lap_pa.luu_du_an(con, gt)
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
        self.assertEqual(nut['Lập phương án hộ'], 'pa')
        self.assertEqual(nut['Thêm hộ'], 'them')
        self.assertEqual(nut['Cập nhật mẫu in'], 'nhap')
        self.assertEqual(w.lb_du_an.property('vai'), 'bang_ten')
        self.assertIn('QHeaderView::section', self.app.styleSheet())
        w.close()
        self.app.setStyleSheet('')
        self.app.removeEventFilter(self.app._bo_to_mau)

    def test_menu_trai_gon_va_bang_tieu_de(self):
        """Menu trái: "Dự án" là một nút xổ, nhóm đóng / mở bằng tiêu đề (nhớ lại); băng tiêu đề có Hoàn tác / Làm lại,
        không còn chữ "Tổ chức làm nhiệm vụ bồi thường"."""
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QLabel
        from pabt import app as ud, giao_dien
        cai = QSettings('PABT', 'PABT')
        cu = cai.value(giao_dien.KHOA_NHOM_DONG, None)              # máy thật: trả lại lựa chọn của người dùng sau khi thử
        cai.remove(giao_dien.KHOA_NHOM_DONG)
        try:
            w = ud.CuaSoChinh(menu_trai=True)
            m = w.khung_menu
            xo = m.nut_xo['Dự án']
            self.assertEqual([a.text() for a in xo.menu().actions()][:3], ['Dự án mới…', 'Mở dự án…', 'Lưu dự án thành…'])
            self.assertIn(w.lenh['Nhập phương án chi tiết…'], xo.menu().actions())
            self.assertEqual(m.nhom_dong, set(ud.NHOM_DONG_MAC_DINH))
            nut_in = next(b for b in m.findChildren(giao_dien.QToolButton) if b.defaultAction() is w.lenh['In / Xuất…'])
            self.assertTrue(nut_in.isHidden())                       # nhóm "In ấn, báo cáo" đóng sẵn
            m.tieu_de_nhom['In ấn, báo cáo'].bam()
            self.assertFalse(nut_in.isHidden())
            self.assertIn('▾', m.tieu_de_nhom['In ấn, báo cáo'].text())
            w.close()
            w2 = ud.CuaSoChinh(menu_trai=True)                       # nhớ nhóm đã mở
            self.assertNotIn('In ấn, báo cáo', w2.khung_menu.nhom_dong)
            chu = ' '.join(x.text() for x in w2.findChildren(QLabel))
            self.assertNotIn('Tổ chức làm nhiệm vụ', chu)
            bang = next(f for f in w2.findChildren(giao_dien.QFrame) if f.property('vai') == 'bang_to_chuc')
            self.assertIs(w2.nut_ht['lui'].parent(), bang)
            self.assertEqual(w2.nut_ht['lui'].property('vai'), 'nut_bang')
            self.assertFalse(w2.nut_ht['lui'].isEnabled())           # chưa mở dự án
            w2.close()
        finally:
            cai.remove(giao_dien.KHOA_NHOM_DONG)
            if cu is not None:
                cai.setValue(giao_dien.KHOA_NHOM_DONG, cu)


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
