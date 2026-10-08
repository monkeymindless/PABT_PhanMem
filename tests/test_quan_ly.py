"""Kiểm thử phiên bản 0.9: đợt trình + thư mục hồ sơ, trạng thái xử lý, nhập quyết định từ file, báo cáo tổng hợp, kiểm tra lỗi,
dự toán / áp giá dự thảo, cây theo chu vi, mật độ, tài sản theo ranh thu hồi, đọc số tiền bằng chữ, nâng cấp CSDL v7."""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import cay_trong as ct
from pabt import csdl, du_toan, kiem_loi, quan_ly
from pabt.lap_pa import LoiNhap
from pabt.tien import D, tien_bang_chu
from tests.test_nghiep_vu import FILE_EXCEL

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestKhongCanDuAn(unittest.TestCase):
    def test_tien_bang_chu(self):
        self.assertEqual(tien_bang_chu(0), 'Không đồng')
        self.assertEqual(tien_bang_chu(1480500), 'Một triệu bốn trăm tám mươi nghìn năm trăm đồng')
        self.assertEqual(tien_bang_chu(1005), 'Một nghìn không trăm linh năm đồng')
        self.assertEqual(tien_bang_chu(21), 'Hai mươi mốt đồng')
        self.assertEqual(tien_bang_chu(2000000000), 'Hai tỷ đồng')
        self.assertEqual(tien_bang_chu(15), 'Mười lăm đồng')

    def test_duong_kinh_chu_vi(self):
        k = ct.khoang_duong_kinh('Sao đen (d >15-18 cm)')
        self.assertTrue(k.chua(D(16)) and k.chua(D(18)) and not k.chua(D(15)))
        self.assertEqual(ct.mo_ta_chu_vi('Sao đen (d >15-18 cm)'), 'chu vi > 47,1 đến ≤ 56,5 cm')
        self.assertEqual(ct.mo_ta_chu_vi('Bách (d <3 cm)'), 'chu vi < 9,4 cm')
        self.assertEqual(ct.mo_ta_chu_vi('Si cảnh - 10cm < Đk thân ≤ 20cm. đường kính tán > 1.5m'), 'chu vi > 31,4 đến ≤ 62,8 cm')
        self.assertIsNone(ct.khoang_duong_kinh('Hỗ trợ di dời chậu kiểng - Chậu có đường kính > 50 cm'))
        self.assertEqual(ct.ten_goc('Si cảnh - 10cm < Đk thân ≤ 20cm'), 'Si cảnh')
        self.assertEqual(ct.ten_goc('Sao đen (d >15-18 cm)'), 'Sao đen')
        self.assertEqual(ct.doc_ds_chu_vi('45, 52x3; 60*2\n130'), [(D(45), 1), (D(52), 3), (D(60), 2), (D(130), 1)])
        with self.assertRaises(ValueError):
            ct.doc_ds_chu_vi('45, abc')

    def test_mat_do_va_ranh(self):
        self.assertEqual(ct.mat_do_tu_danh_muc('cây cam - Năm thứ 1', 'Mật độ 1.111 cây/ha; Sửa đổi…'), D(1111))
        self.assertIsNone(ct.mat_do_tu_danh_muc('cây phượng', ''))
        self.assertEqual(ct.so_cay_toi_da(210, 1000), 21)
        self.assertEqual(ct.tach_mat_do(30, 1000, 210), (21, 9))
        self.assertEqual(ct.tach_mat_do(10, 1000, 210), (10, 0))
        r = ct.tach_ranh(120, 80)
        self.assertEqual((r['trong'], r['ngoai']), (D(80), D(40)))
        r = ct.tach_ranh(120, 80, anh_huong_ket_cau=True)
        self.assertEqual((r['trong'], r['ngoai']), (D(120), D(0)))
        with self.assertRaises(ValueError):
            ct.tach_ranh(100, 120)

    def test_font_va_ho_ten(self):
        self.assertEqual(kiem_loi.loi_font('Nguyễn Văn An'), '')
        self.assertIn('TCVN3', kiem_loi.loi_font('NguyÔn V¨n An'))
        self.assertIn('tổ hợp', kiem_loi.loi_font('Nguyễn'))
        self.assertEqual(kiem_loi.chuan_ho_ten('  nguyễn   văn  an '), 'Nguyễn Văn An')
        self.assertEqual(kiem_loi.loi_font('Giếng khoan (ống > Φ114 mm), ống Ø90'), '')
        self.assertTrue(kiem_loi.la_ho_ten_don('nguyễn văn an'))
        self.assertFalse(kiem_loi.la_ho_ten_don('Phạm Văn Thoa được cấp giấy - Bùi Văn Hữu (đã chết)'))

    def test_chuan_ngay(self):
        self.assertEqual(quan_ly.chuan_ngay('5/3/2026'), '05/03/2026')
        self.assertEqual(quan_ly.chuan_ngay('2026-03-05'), '05/03/2026')
        self.assertEqual(quan_ly.chuan_ngay(''), '')
        with self.assertRaises(LoiNhap):
            quan_ly.chuan_ngay('31/02/2026')
        with self.assertRaises(LoiNhap):
            quan_ly.chuan_ngay('abc')

    def test_nang_cap_v6_len_v7(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'cu.pabt'
            con = csdl.mo(p, tao=True)
            con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'A')")
            con.commit()
            con.close()
            c = sqlite3.connect(p)                      # giả file v6: bỏ cột / bảng mới
            c.execute('DROP TABLE dot_trinh')
            c.execute('DROP TABLE cai_dat')
            c.execute('DROP TABLE quy_chuan_mat_do')
            for cot in ('theo_doi', 'dot_id'):
                c.execute(f'ALTER TABLE ho DROP COLUMN {cot}')
            c.execute('PRAGMA user_version = 6')
            c.commit()
            c.close()
            con = csdl.mo(p)
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
            cot = [r[1] for r in con.execute('PRAGMA table_info(ho)')]
            self.assertIn('dot_id', cot)
            self.assertIn('theo_doi', cot)
            quan_ly.tao_dot(con)
            csdl.ghi_cai_dat(con, 'X', '1')
            self.assertEqual(csdl.doc_cai_dat(con, 'X'), '1')
            con.close()


@unittest.skipUnless(FILE_EXCEL.exists(), 'cần file Excel mẫu')
class TestQuanLyDuAn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pabt import nhap_excel
        cls.tmp = tempfile.TemporaryDirectory()
        cls.goc = Path(cls.tmp.name) / 'goc.pabt'
        nhap_excel.nhap(FILE_EXCEL, cls.goc)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.p = Path(self.tmp.name) / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        from pabt.nghiep_vu import tinh_tat_ca
        self.tong = {k.ma_ho: k.tong for k in tinh_tat_ca(self.con)}

    def tearDown(self):
        self.con.close()

    def test_dot_trinh_va_thu_muc(self):
        d1 = quan_ly.tao_dot(self.con)
        d2 = quan_ly.tao_dot(self.con, ngay_trinh='7/10/2026', so_to_trinh='12/TTr')
        with self.assertRaises(LoiNhap):
            quan_ly.tao_dot(self.con, ten='Đợt 1')
        quan_ly.gan_dot(self.con, self.ma[:2], d1)
        quan_ly.gan_dot(self.con, self.ma[2:3], d2)
        ds = quan_ly.ds_dot(self.con)
        self.assertEqual([(d.ten, d.so_ho) for d in ds], [('Đợt 1', 2), ('Đợt 2', 1)])
        self.assertEqual(ds[1].ngay_trinh, '07/10/2026')
        goc = Path(self.tmp.name) / f'hs_{self._testMethodName}'
        quan_ly.dat_thu_muc_ho_so(self.con, goc)
        self.assertEqual(quan_ly.thu_muc_ho_so(self.con, self.p), goc)
        kq = quan_ly.xuat_dot(self.con, d1, goc)
        self.assertEqual(kq['thu_muc'].name, 'Đợt 1 - 2 hộ')
        self.assertEqual(len(kq['excel']), 3)                    # 2 PA chi tiết + bảng tổng hợp
        self.assertTrue((kq['thu_muc'] / 'PA TONG' / 'BANG_TONG_HOP.xlsx').exists())     # 0.9.16: PA CHI TIET / PA TONG
        quan_ly.gan_dot(self.con, self.ma[2:3], d1)              # chuyển thêm 1 hộ: thư mục đổi tên theo số hộ
        kq = quan_ly.xuat_dot(self.con, d1, goc)
        self.assertEqual(sorted(p.name for p in goc.iterdir()), ['Đợt 1 - 3 hộ'])
        self.assertEqual(len(kq['excel']), 4)
        with self.assertRaises(LoiNhap):
            quan_ly.xuat_dot(self.con, d2, goc)                  # đợt 2 không còn hộ
        self.assertEqual(quan_ly.xoa_dot(self.con, d1), 3)
        self.assertEqual(len(quan_ly.ho_cua_dot(self.con, None)), len(self.ma))
        dich = quan_ly.luu_thanh(self.con, goc / 'ban_sao')
        self.assertEqual(dich.suffix, '.pabt')
        c2 = csdl.mo(dich)
        self.assertEqual(c2.execute('SELECT COUNT(*) FROM ho').fetchone()[0], len(self.ma))
        c2.close()

    def test_trang_thai_quyet_dinh_bao_cao(self):
        import openpyxl
        dem = {}
        for r in self.con.execute('SELECT ho_ten FROM ho'):
            dem[quan_ly._ten_chuan(r[0])] = dem.get(quan_ly._ten_chuan(r[0]), 0) + 1
        duy_nhat = [r[0] for r in self.con.execute('SELECT ma_ho, ho_ten FROM ho ORDER BY thu_tu')
                    if dem[quan_ly._ten_chuan(r[1])] == 1 and len(r[1].split()) <= 5]
        m0, m1 = duy_nhat[0], duy_nhat[1]
        quan_ly.cap_nhat_trang_thai(self.con, [m0], dict(da_phe_duyet=True, qd_so='1/QĐ-UBND', qd_ngay='1/10/2026',
                                                         qd_so_tien=self.tong[m0], theo_doi='Hẹn ký'))
        tt = quan_ly.doc_trang_thai(self.con, m0)
        self.assertEqual((tt['da_phe_duyet'], tt['qd_ngay'], D(tt['qd_so_tien'])), (1, '01/10/2026', self.tong[m0]))
        self.assertTrue(quan_ly.hop_trang_thai(dict(tt, tong=self.tong[m0]), 'chua_ct'))
        with self.assertRaises(LoiNhap):
            quan_ly.cap_nhat_trang_thai(self.con, [m0], dict(chi_tra_ngay='99/99/2026'))
        # quyết định dạng bảng Excel: khớp theo họ tên (có "Ông/Bà", chữ thường), số tiền theo cột
        f = Path(self.tmp.name) / f'qd_{self._testMethodName}.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Kèm theo Quyết định số 789/QĐ-UBND ngày 05 tháng 10 năm 2026'])
        ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Tổng kinh phí (đồng)'])
        ten = {r[0]: r[1] for r in self.con.execute('SELECT ma_ho, ho_ten FROM ho')}
        ws.append([1, 'Ông ' + ten[m0].lower(), '', float(self.tong[m0])])
        ws.append([2, ten[m1], '', float(self.tong[m1]) + 1000])
        ws.append([3, 'Người Không Có Trong Dự Án', '', 5000000])
        wb.save(f)
        r = quan_ly.doc_quyet_dinh(self.con, f, self.tong)
        self.assertEqual((r.so_qd, r.ngay), ('789/QĐ-UBND', '05/10/2026'))
        self.assertEqual([d.ma_ho for d in r.dong], [m0, m1])
        self.assertFalse(r.dong[0].lech_tien)
        self.assertTrue(r.dong[1].lech_tien)
        goc = Path(self.tmp.name) / f'hs_{self._testMethodName}'
        kq = quan_ly.ap_quyet_dinh(self.con, 'ct', r.dong, ngay='06/10/2026', file_goc=f, thu_muc_luu=goc)
        self.assertEqual(kq['so_ho'], 2)
        self.assertTrue(Path(kq['file_luu']).exists())
        self.assertEqual(quan_ly.doc_trang_thai(self.con, m1)['chi_tra_ngay'], '05/10/2026')   # ngày theo văn bản
        # kiểm tra lỗi: hộ 2 đã chi trả mà chưa phê duyệt
        ds = kiem_loi.kiem_tra(self.con)
        self.assertTrue(any(x.ma_ho == m1 and x.nhom == 'Tiến độ' and x.muc_do == kiem_loi.LOI for x in ds))
        p = quan_ly.xuat_bao_cao_tong_hop(self.con, Path(self.tmp.name) / 'bc.xlsx', [m0, m1], dieu_kien='thử')
        ws = openpyxl.load_workbook(p).active
        self.assertEqual(ws.cell(6, 3).value, ten[m0])
        self.assertEqual(ws.cell(6, 19).value, 'Hẹn ký')
        self.assertIn('Bằng chữ', ws.cell(9, 3).value)

    def test_kiem_tra_va_sua_tu_dong(self):
        m0, m1 = self.ma[0], self.ma[1]
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = '  nguyễn   văn  thử ', so_cccd = '0123 4567 8901' WHERE ma_ho = ?", (m0,))
            self.con.execute("UPDATE ho SET so_cccd = '012345678901', dia_chi = 'Ph­êng Tr¶ng Dµi' WHERE ma_ho = ?", (m1,))
        ds = kiem_loi.kiem_tra(self.con)
        noi = [(x.ma_ho, x.noi_dung) for x in ds]
        self.assertTrue(any(m == m0 and 'khoảng trắng' in n for m, n in noi))
        self.assertTrue(any(m == m0 and 'Trùng số CCCD' in n for m, n in noi))
        self.assertTrue(any(m == m1 and 'TCVN3' in n for m, n in noi))
        n = kiem_loi.sua_tu_dong(self.con)
        self.assertGreater(n, 0)
        h = self.con.execute('SELECT ho_ten, so_cccd FROM ho WHERE ma_ho = ?', (m0,)).fetchone()
        self.assertEqual((h[0], h[1]), ('Nguyễn Văn Thử', '012345678901'))
        f = Path(self.tmp.name) / 'kt.xlsx'
        kiem_loi.xuat_excel(kiem_loi.kiem_tra(self.con), f, 'thử')
        self.assertTrue(f.exists())

    def test_du_toan(self):
        dt = du_toan.tu_du_an(self.con)
        # gom đủ khối lượng; làm tròn theo dòng dự toán nên chỉ chênh vài nghìn đồng so với tổng các phương án
        self.assertLessEqual(abs(dt.tong - sum(self.tong.values(), D(0))), 1000 * len(dt.dong))
        self.assertTrue(any(d.muc == 1 for d in dt.dong))
        dt.them_chi_phi_mac_dinh()
        cp = [d for d in dt.dong if d.muc == 6]
        self.assertEqual(len(cp), 2)
        from pabt.tien import lam_tron
        self.assertEqual(dt.thanh_tien(cp[1]), lam_tron(dt.co_so_phan_tram() * 10 / 100, dt.lamtron))
        f = dt.luu(Path(self.tmp.name) / 'thu')
        dt2 = du_toan.DuToan.mo(f)
        self.assertEqual(dt2.tong, dt.tong)
        self.assertTrue(du_toan.xuat_excel(dt2, Path(self.tmp.name) / 'dt.xlsx').exists())
        from pabt.lap_pa import DanhMuc
        d = next(x for x in dt2.dong if x.muc == 2 and x.ma)
        d.don_gia += 1
        doi = du_toan.ap_don_gia_hien_hanh(dt2, DanhMuc(self.con))
        self.assertTrue(any(t == d.ten for t, _, _ in doi))

    def test_cay_theo_chu_vi_danh_muc(self):
        from pabt.lap_pa import DanhMuc
        b = ct.BangCayDK(DanhMuc(self.con).muc[3])
        if not b.loai:
            self.skipTest('danh mục mẫu không có cây ghi đường kính')
        for ten, ds in b.loai.items():
            for k, m in ds:
                if k.tu is not None and k.den is not None:
                    d = (k.tu + k.den) / 2
                elif k.den is not None:
                    d = k.den - D('0.5')
                else:
                    d = k.tu + D('0.5')
                self.assertEqual(b.tim(ten, d * ct.PI).ma, m.ma, f'{ten} d={d}')


@unittest.skipUnless(CO_QT and FILE_EXCEL.exists(), 'cần PySide6 và file Excel mẫu')
class TestManHinhQuanLy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        from pabt import nhap_excel
        cls.tmp = tempfile.TemporaryDirectory()
        cls.goc = Path(cls.tmp.name) / 'goc.pabt'
        nhap_excel.nhap(FILE_EXCEL, cls.goc)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        from PySide6.QtWidgets import QMessageBox
        self.p = Path(self.tmp.name) / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)
        self.thong_bao = []
        self.va = [mock.patch.object(QMessageBox, n, side_effect=lambda *a, **k: self.thong_bao.append(a[2]))
                   for n in ('warning', 'information')]
        self.va.append(mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No))
        for v in self.va:
            v.start()

    def tearDown(self):
        for v in self.va:
            v.stop()

    def _cua_so(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        w.mo(self.p, chi_doc=False)
        self.addCleanup(w.dong_du_an)                   # đóng file dự án cả khi bài kiểm thử lỗi giữa chừng
        return w

    def test_loc_ghi_chu_va_lenh(self):
        from pabt.app import COT
        w = self._cua_so()
        n = len(w.mo_hinh.dong)
        self.assertEqual(w.mo_hinh.columnCount(), len(COT))
        # ghi chú theo dõi (từ 0.9.12 sửa trong Trạng thái hộ): tìm, lọc được trên danh sách
        from PySide6.QtCore import Qt
        ma0 = w.mo_hinh.dong[0]['ma_ho']
        quan_ly.cap_nhat_trang_thai(w.con, [ma0], dict(theo_doi='Chờ ký biên bản'))
        w.tai_lai()
        self.assertEqual(quan_ly.doc_trang_thai(w.con, ma0)['theo_doi'], 'Chờ ký biên bản')
        w.cb_tt.setCurrentIndex(w.cb_tt.findData('co_ghi_chu'))
        self.assertEqual(w.ho_dang_loc(), [ma0])
        w.cb_tt.setCurrentIndex(0)
        w.o_tim.setText('ky bien ban')                          # tìm không dấu trong ghi chú
        self.assertEqual(w.ho_dang_loc(), [ma0])
        w.o_tim.setText('')
        self.assertEqual(len(w.ho_dang_loc()), n)
        # đợt trình
        dlg = w.dot_trinh(cho=False)
        dlg.im_lang = True
        dlg.ma_ho_chon = [ma0]
        i = dlg.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        self.assertEqual(dlg.dua_vao(), 1)
        goc = Path(self.tmp.name) / f'hs_{self._testMethodName}'
        dlg.chon_thu_muc(goc)
        kq = dlg.xuat(pdf=False)
        self.assertTrue((goc / 'Đợt 1 - 1 hộ').is_dir() and kq)
        w.tai_lai()
        w.cb_dot.setCurrentIndex(w.cb_dot.findData(i))
        self.assertEqual(w.ho_dang_loc(), [ma0])
        self.assertEqual(w.mo_hinh.dong[0]['dot_id'], i)
        w.cb_dot.setCurrentIndex(w.cb_dot.findData('chua'))
        self.assertEqual(len(w.ho_dang_loc()), n - 1)
        w.cb_dot.setCurrentIndex(0)
        # trạng thái nhiều hộ
        ds = [x['ma_ho'] for x in w.mo_hinh.dong[:3]]
        t = w.trang_thai_ho(ds, cho=False)
        t.im_lang = True
        t.o['da_phe_duyet'].setCheckState(Qt.CheckState.Checked)
        t.o['qd_so'].setText('55/QĐ-UBND')
        t.o_theo_pa.setChecked(True)
        self.assertEqual(t.luu(), 3)
        for m in ds:
            x = quan_ly.doc_trang_thai(w.con, m)
            self.assertEqual((x['da_phe_duyet'], x['qd_so']), (1, '55/QĐ-UBND'))
            self.assertEqual(D(x['qd_so_tien']), w._tong_pa()[m])
        self.assertEqual(quan_ly.doc_trang_thai(w.con, ma0)['theo_doi'], 'Chờ ký biên bản')   # trường không đổi: giữ nguyên
        # báo cáo tổng hợp theo bộ lọc
        w.tai_lai()
        w.cb_tt.setCurrentIndex(w.cb_tt.findData('da_pd'))
        f = w.bao_cao_tong_hop(Path(self.tmp.name) / 'bc_loc.xlsx')
        import openpyxl
        self.assertEqual(openpyxl.load_workbook(f).active.cell(3, 1).value.count('Đã phê duyệt'), 1)
        # kiểm tra lỗi, dự toán, quy chuẩn
        k = w.kiem_tra_loi(cho=False)
        k.im_lang = True
        self.assertIsInstance(k.ds, list)
        dt = w.du_toan(cho=False)
        dt.im_lang = True
        dt.lay('du_an')
        self.assertLessEqual(abs(dt.dt.tong - sum(w._tong_pa().values(), D(0))), 1000 * len(dt.dt.dong))
        dt.them_chi_phi()
        self.assertGreater(dt.bang.rowCount(), 2)
        q = w.quy_chuan(cho=False)
        q.im_lang = True
        q.o_md.setText('50')
        q.luu()
        self.assertEqual(csdl.doc_cai_dat(w.con, 'TL_NGOAI_MAT_DO'), '0.5')
        p2 = w.luu_du_an_thanh(Path(self.tmp.name) / 'luu_thanh' / 'moi.pabt', mo_ban_moi=True)
        self.assertEqual(w.file, p2)
        w.dong_du_an()
        w.close()

    def test_tien_ich_cay_tai_san(self):
        from pabt.man_hinh import CuaSoLapPA
        con = csdl.mo(self.p)
        try:
            w = CuaSoLapPA(con, 1)
            # cây theo chu vi
            loai = ct.BangCayDK(w.bo.dm.muc[3])
            if loai.loai:
                ten = next(iter(loai.loai))
                dlg = w.them_cay_chu_vi(ten, '30, 30x2, 400', cho=False)
                dlg.im_lang = True
                nhom, loi = dlg.xem()
                self.assertTrue(nhom)
                truoc = len(w.bo.pa.khoan[3])
                moi = dlg.them()
                self.assertEqual(len(w.bo.pa.khoan[3]), truoc + len(moi))
                self.assertIn('Chu vi đo', w.bo.pa.khoan[3][moi[0]].quy_cach)
            # mật độ: dòng cây đầu tiên tính theo cây
            i = next((k for k, d in enumerate(w.bo.pa.khoan[3]) if d.dvt == 'cây'), None)
            if i is not None:
                md = w.tinh_mat_do(i, cho=False)
                md.im_lang = True
                md.o_dt.setText('1000')
                md.o_so.setText('30')
                md.o_md.setText('210')
                md.o_tl.setText('50')
                trong, ngoai, j = md.ap_dung()
                self.assertEqual((trong, ngoai), (21, 9))
                self.assertEqual(w.bo.pa.khoan[3][j].so_luong, 9)
                self.assertEqual(w.bo.pa.khoan[3][j].ty_le, D('0.5'))
            # tài sản theo ranh: dòng mục 2 đầu tiên
            if w.bo.pa.khoan[2]:
                r = w.tach_ranh(0, cho=False)
                r.im_lang = True
                r.o_tong.setText('120')
                r.o_trong.setText('80')
                r.o_tl.setText('0')
                kq, j = r.ap_dung()
                self.assertEqual(w.bo.pa.khoan[2][0].so_luong, 80)
                self.assertEqual(w.bo.pa.khoan[2][j].ty_le, 0)
                self.assertIn('trong ranh thu hồi 80', w.bo.pa.khoan[2][0].quy_cach)
            self.assertTrue(w.luu())
            w.close()
        finally:
            con.close()


if __name__ == '__main__':
    unittest.main()
