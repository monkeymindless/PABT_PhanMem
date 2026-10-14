"""Yêu cầu người dùng 12/10/2026 (0.9.69): mã tài sản TS / CT / VN / CS / TH, bỏ quy ước gắn sẵn, chủ đầu tư, kinh phí chỉ chọn
loại dự án, mẫu văn bản trình mới (bỏ phương án tổng), chọn hộ niêm yết, xóa số PA chi tiết, đổi tên menu. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import re
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, don_gia, du_thao, lap_pa, ma_tai_san, quan_ly, van_ban_trinh as vb
from tests.test_toc_do import _du_an

# tên, số hiệu của văn bản thật người dùng gửi làm mẫu - không được nằm trong mẫu mặc định (phần mềm phát hành không kèm dữ liệu)
_DU_LIEU_THAT = ('Vĩnh Cửu', 'Mã Đà', 'Bà Hào', 'Hoàng Phương', 'Đại Quang Minh', '1196', '432', '470.104', '1086/QĐ',
                 'KetnoiMaDa')


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)


class TestMaTaiSan(unittest.TestCase):
    def test_quy_tac(self):
        self.assertEqual(ma_tai_san.doi_ma('HT09', 4), 'CS9')
        self.assertEqual(ma_tai_san.doi_ma('VN01', 3, True), 'VN1')
        self.assertEqual(ma_tai_san.doi_ma('TH02', 5), 'TH2')
        self.assertEqual(ma_tai_san.doi_ma('TS17', 2), 'TS17')                    # nhà giữ số
        self.assertEqual(ma_tai_san.doi_ma('TS140', 3), 'CT1')                    # cây đầu tiên
        self.assertEqual(ma_tai_san.doi_ma('TS380', 7), 'CT241')                  # dòng phương án mục 3 / 7
        self.assertEqual(ma_tai_san.doi_ma('CT5', 3), 'CT5')                      # mã mới: không đổi lần nữa
        self.assertEqual(ma_tai_san.ma_thuong(3), 'TH3')

    def test_chuyen_csdl_mot_lan(self):
        td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, td, True)
        p = td / 'a.pabt'
        con = csdl.tao_moi(p)
        try:
            with con, csdl.mo_khoa_danh_muc(con):
                for ma, nhom, ten, pl in (('TS1', 2, 'Nhà', ''), ('TS140', 3, 'Cây A', ''), ('TS141', 3, 'Cây B', ''),
                                          ('VN01', 3, 'Heo', 'vật nuôi'), ('HT01', 4, 'Trùng hỗ trợ', ''),
                                          ('TH01', 5, 'Trùng thưởng', ''), ('TSN0001', 3, 'Cây cập nhật', '')):
                    con.execute('INSERT INTO dm_taisan (ma, nhom, ten, phan_loai) VALUES (?, ?, ?, ?)', (ma, nhom, ten, pl))
                con.execute("INSERT INTO dm_hotro (ma, ten) VALUES ('HT01', 'Ổn định đời sống')")
            kq = ma_tai_san.chuyen_csdl(con)
            self.assertEqual(kq['bo'], 2)                                         # dòng nhóm 4 / 5 trong dm_taisan bỏ
            ma = {r[0] for r in con.execute('SELECT ma FROM dm_taisan')}
            self.assertEqual(ma, {'TS1', 'CT1', 'CT2', 'VN1', 'CT3'})             # TSN… cấp số tiếp theo
            self.assertEqual([r[0] for r in con.execute('SELECT ma FROM dm_hotro')], ['CS1'])
            self.assertEqual(ma_tai_san.chuyen_csdl(con)['doi'], 0)               # chạy lại: không đổi thêm
        finally:
            con.close()

    def test_bo_don_gia_dong_goi(self):
        """Bộ đơn giá đóng gói: v14, mã mới, không quy ước gắn sẵn, không dòng hỗ trợ / thưởng lẫn trong dm_taisan."""
        con = sqlite3.connect(Path(don_gia.file_goc()).resolve().as_uri() + '?mode=ro', uri=True)
        try:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM quy_uoc').fetchone()[0], 0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM dm_taisan WHERE nhom IN (4, 5)').fetchone()[0], 0)
            for (ma,) in con.execute('SELECT ma FROM dm_taisan'):
                self.assertRegex(ma, r'^(TS|CT|VN)[1-9]\d*$')
            for (ma,) in con.execute('SELECT ma FROM dm_hotro'):
                self.assertRegex(ma, r'^CS[1-9]\d*$')
        finally:
            con.close()


class TestDuAn(_Co):
    def setUp(self):
        super().setUp()
        self.p = _du_an(self.td, so_ho=4)
        self.con = csdl.mo(self.p)
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def test_chu_dau_tu_va_kinh_phi(self):
        self.assertIn('chu_dau_tu', dict(lap_pa.TRUONG_DU_AN))
        gt = lap_pa.doc_du_an(self.con)
        gt['chu_dau_tu'] = 'Công ty Giả lập'
        lap_pa.luu_du_an(self.con, gt)
        self.assertEqual(lap_pa.doc_du_an(self.con)['chu_dau_tu'], 'Công ty Giả lập')
        lap_pa.luu_kinh_phi_to_chuc(self.con, 'khac', '')                         # chỉ chọn loại: tỷ lệ = mức của loại
        loai, tl, tu_nhan = lap_pa.kinh_phi_to_chuc(self.con)
        self.assertEqual((loai, str(tl), tu_nhan), ('khac', '2.5', False))
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh import HopDuAn
        h = HopDuAn(self.con)
        self.addCleanup(h.close)
        self.assertFalse(hasattr(h, 'o_tl_kp'))                                   # bỏ ô Tỷ lệ
        self.assertIn('chu_dau_tu', h.o)

    def test_mau_to_trinh_moi(self):
        self.assertEqual(set(vb.LOAI), {'to_trinh'})
        p = vb.file_mau('to_trinh')
        with zipfile.ZipFile(p) as z:
            x = z.read('word/document.xml').decode('utf-8')
        chu = re.sub(r'<[^>]+>', '', x)
        for t in _DU_LIEU_THAT:
            self.assertNotIn(t, chu)
        cho = vb.cho_trong_trong_file(p)
        self.assertLessEqual(set(cho), {k for k, _ in vb.DS_CHO_TRONG})          # mọi mã đều có trong danh sách hướng dẫn
        for k in ('du_an', 'chu_dau_tu', 'so_ho_02', 'so_pa_tong', 'KY_THAY', 'cap_dia_ban_thuong'):
            self.assertIn(k, cho)
        with self.con:
            self.con.execute("UPDATE du_an SET chuc_vu_ky = 'Phó Giám đốc', nguoi_ky = 'Người Ký Thử', "
                             "chu_dau_tu = 'Ban QLDA Giả lập' WHERE id = 1")
        d = quan_ly.tao_dot(self.con, ngay_trinh='12/10/2026', so_to_trinh='5/TTr', so_pa_tong='9', ngay_pa_tong='11/10/2026')
        chung, _ = vb.du_lieu(self.con, self.ma[:2], quan_ly.lay_dot(self.con, d))
        self.assertEqual(chung['KY_THAY'], 'KT. GIÁM ĐỐC')
        self.assertEqual(chung['so_ho_02'], '02')
        ra = vb.lap_van_ban(self.con, 'to_trinh', self.ma[:2], self.td / 'ra', quan_ly.lay_dot(self.con, d))
        with zipfile.ZipFile(ra) as z:
            chu = re.sub(r'<[^>]+>', '', z.read('word/document.xml').decode('utf-8'))
        for t in ('KT. GIÁM ĐỐC', 'Ban QLDA Giả lập', 'Phương án số 9/', 'Đối với 02 trường hợp', 'Người Ký Thử'):
            self.assertIn(t, chu)
        self.assertNotIn('{', chu)

    def test_chon_ho_niem_yet(self):
        ds = du_thao.danh_gia_niem_yet(self.con)
        self.assertEqual(len(ds), 4)
        # dự án giả lập: phương án tự lập, thửa chưa ghi nguồn gốc -> chưa đủ điều kiện
        self.assertTrue(all(not h['du'] for h in ds))
        with self.con:
            self.con.execute("UPDATE thua SET nguon_goc = 'Nhận chuyển nhượng'")
            self.con.execute("UPDATE ho SET luu_luc = '2026-10-12 08:00:00', trang_thai = 'Đã lập phương án (lưu)'"
                             " WHERE ma_ho = ?", (self.ma[0],))
            self.con.execute("UPDATE ho SET ma_vuong = 'V1' WHERE ma_ho = ?", (self.ma[1],))
        ds = {h['ma_ho']: h for h in du_thao.danh_gia_niem_yet(self.con)}
        self.assertTrue(ds[self.ma[0]]['du'], ds[self.ma[0]]['ly_do'])
        self.assertFalse(ds[self.ma[1]]['du'])
        self.assertTrue(any('V1' in x for x in ds[self.ma[1]]['ly_do']))
        # đánh dấu: hộ vướng không đánh dấu được
        self.assertEqual(du_thao.ghi_danh_dau(self.con, {self.ma[0]: True, self.ma[1]: True}), (1, 1))
        self.assertEqual(self.con.execute('SELECT du_dieu_kien FROM ho WHERE ma_ho = ?', (self.ma[0],)).fetchone()[0], 1)
        # hộp thoại: tích sẵn hộ đủ điều kiện, lưu + đưa vào đợt niêm yết
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_du_thao import HopChonNiemYet
        dot = du_thao.tao_dot(self.con, 'Đợt thử', '12/10/2026', 'Nhà văn hóa')
        h = HopChonNiemYet(None, self.con)
        h.im_lang = True
        self.addCleanup(h.close)
        self.assertEqual(h.ma_da_tich(), [self.ma[0]])
        h.cb_dot.setCurrentIndex(h.cb_dot.findData(dot))
        self.assertEqual(h.luu(), (0, 1))
        self.assertEqual([r['ma_ho'] for r in du_thao.ds_ho_dot(self.con, dot)], [self.ma[0]])

    def test_xoa_so_pa_chi_tiet(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_quan_ly import HopDotTrinh
        d = HopDotTrinh(self.con, None, self.ma[:3], self.p)
        d.im_lang = True
        self.addCleanup(d.close)
        i = d.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        self.assertEqual(d.dot_chon(), i)
        d.dua_vao()
        d.danh_so(5, '9/10/2026')
        self.assertEqual(quan_ly.so_pa_cua_ho(self.con, self.ma[:3])[self.ma[0]][0], '5')
        self.assertEqual(d.xoa_so(), 3)
        self.assertTrue(all(not s and not n for s, n in quan_ly.so_pa_cua_ho(self.con, self.ma[:3]).values()))
        self.assertEqual(d.xoa_so(), 0)                                           # không còn số: báo, không ghi

    def test_xoa_so_pa_hoi_xac_nhan_co_ten_dot(self):
        """Lỗi 13/10/2026: `dot_chon()` trả id (int) nhưng câu hỏi xác nhận viết `dot.ten` -> AttributeError khi bấm thật.
        Các test trên đặt im_lang (bỏ qua câu hỏi) nên không thấy: ở đây để hộp hiện thật (QMessageBox giả)."""
        from PySide6.QtWidgets import QApplication, QMessageBox
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_quan_ly import HopDotTrinh
        d = HopDotTrinh(self.con, None, self.ma[:3], self.p)
        self.addCleanup(d.close)
        d.im_lang = True                                                           # chuẩn bị dữ liệu không hiện hộp
        i = d.them_dot(dict(ten='Đợt thử xóa', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        d.dua_vao()
        d.danh_so(5, '9/10/2026')
        self.assertEqual(d.ten_dot(i), 'Đợt thử xóa')
        self.assertEqual(d.ten_dot(None), '(chưa xếp đợt)')
        d.im_lang = False
        Yes, No = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No
        with mock.patch.object(QMessageBox, 'question', return_value=No) as hoi, \
                mock.patch.object(QMessageBox, 'information') as tb:
            self.assertIsNone(d.xoa_so())                                          # không đồng ý: không xóa, không báo thành công
            self.assertIn('Đợt thử xóa', hoi.call_args[0][2])
            tb.assert_not_called()
            self.assertEqual(quan_ly.so_pa_cua_ho(self.con, self.ma[:3])[self.ma[0]][0], '5')
            hoi.return_value = Yes
            self.assertEqual(d.xoa_so(), 3)
            self.assertIn('Đợt thử xóa', tb.call_args[0][2])                       # báo thành công kèm tên đợt
        self.assertTrue(all(not s and not n for s, n in quan_ly.so_pa_cua_ho(self.con, self.ma[:3]).values()))


class TestMenu(_Co):
    def test_doi_ten_menu(self):
        from pabt import app
        self.assertEqual(app.NHAN_MENU['Dự thảo PABT…'], 'Niêm yết & Lấy ý kiến')
        self.assertEqual(app.NHAN_MENU['Đợt trình…'], 'Đợt trình thẩm định')     # 0.9.70 theo đặc tả V7
        self.assertEqual(app.NHAN_MENU['Bộ đơn giá…'], 'Đơn giá bồi thường')
        self.assertEqual(app.NHAN_MENU['Đơn giá riêng dự án…'], 'Đơn giá đặc biệt')


if __name__ == '__main__':
    unittest.main()
