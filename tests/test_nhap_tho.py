"""Nhập danh sách hộ, thửa từ file Excel bất kỳ (tự nhận cột)."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, nhap_tho


def _ghi(p, ws_ham):
    wb = openpyxl.Workbook()
    ws_ham(wb)
    wb.save(p)


def _don_gian(wb):
    ws = wb.active
    ws.title = 'danhsach'
    ws.append(['STT', 'Họ và tên hồ sơ kiểm đếm', 'Địa chỉ nơi cu trú', 'Số điện thoại', 'Số \ntờ', 'Số thửa ',
               'DT đất thu hồi', 'DT thu hồi bản đồ', 'Loại đất thu hồi', 'Ghi chú'])
    ws.append([1, 'Nguyễn Văn A', 'ấp 8, xã Trảng Bom', None, 35, 394, 215.1, None, 'ONT+CLN', None])
    ws.append([2, 'Trần Thị B', 'ấp 8, xã Trảng Bom', '0909', 35, 80, 410.6, 428, 'CLN', 'đã kiểm đếm'])
    ws.append([3, 'Nguyễn Văn A', 'ấp 8, xã Trảng Bom', None, 36, 12, 50, None, 'LUK', None])
    ws.append([4, 'Lê C', 'ấp 15', None, 72, '99 (thửa 33 cũ)', None, None, None, None])
    ws.append([5, 'Phạm D', 'ấp 15', None, 72, '99 (thửa 33 cũ)', 20, None, 'ONT', None])
    ws.append([6, 'Không Thửa', 'ấp 15', None, None, None, None, None, None, None])
    for _ in range(5):
        ws.append([None] * 10)


def _lon_xon(wb):
    """Tên bảng gộp ô, tiêu đề 2 dòng có ô gộp, dòng đánh số cột, họ tên gộp nhiều thửa, số kiểu VN, dòng cộng."""
    wb.create_sheet('Ghi chu').append(['File này lập ngày...'])
    ws = wb.active
    ws.title = 'Bang 1'
    ws['A1'] = 'DANH SÁCH CÁC HỘ BỊ THU HỒI ĐẤT DỰ ÁN ĐƯỜNG ABC'
    ws.merge_cells('A1:H1')
    ws['A2'] = '(Kèm theo Thông báo số 12/TB-UBND)'
    ws.merge_cells('A2:H2')
    ws['A4'], ws['B4'], ws['C4'], ws['D4'], ws['F4'], ws['G4'], ws['H4'] = (
        'TT', 'Tên chủ sử dụng', 'Thường trú', 'Thửa đất', 'Diện tích thu hồi (m2)', 'Mục đích sử dụng', 'Số CCCD')
    ws.merge_cells('D4:E4')
    for c in 'ABCFGH':
        ws.merge_cells(f'{c}4:{c}5')
    ws['D5'], ws['E5'] = 'Tờ BĐ', 'Số thửa'
    ws.append([f'({i})' for i in range(1, 9)])                       # dòng 6
    ws.append(['I', 'Ấp Bàu Hàm'])                                    # dòng nhóm
    ws.append([1, 'Tống Văn E', 'ấp Bàu Hàm', 71, 1, '1.070,5', 'ONT', '0123 456 789'])
    ws.append([None, None, None, 71, 2, '39,4 m2', 'CLN', None])      # dòng tiếp của hộ trên (ô trống)
    ws.append([2, 'Đỗ F', 'ấp Bàu Hàm', 72, 5, 12, 'BHK', None])
    ws.merge_cells('B10:B11')
    ws.append([None, None, 'ấp Bàu Hàm', 72, 6, 8, 'BHK', None])      # họ tên gộp ô với dòng trên
    ws.append(['', 'Tổng cộng', None, None, None, 1129.9, None, None])


class TestNhapTho(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nhan_cot_va_gom_ho(self):
        p = self.td / 'ds.xlsx'
        _ghi(p, _don_gian)
        self.assertFalse(nhap_tho.la_file_pabt(p))
        kq = nhap_tho.doc(p)
        self.assertEqual(kq.loi, [])
        c = kq.bo_cot.cot
        self.assertEqual((c['ho_ten'], c['dia_chi'], c['so_to'], c['so_thua'], c['dt_thu_hoi'], c['dt_ban_do'], c['loai_dat']),
                         (1, 2, 4, 5, 6, 7, 8))
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Nguyễn Văn A', 'Trần Thị B', 'Lê C', 'Phạm D', 'Không Thửa'])
        self.assertEqual(len(kq.thua), 5)
        self.assertEqual([t['ma_ho'] for t in kq.thua], [1, 2, 1, 3, 4])
        self.assertEqual(kq.thua[0]['dt_thu_hoi'], '215.1')
        self.assertEqual(kq.thua[3]['so_thua'], '99 (thửa 33 cũ)')
        self.assertEqual(kq.thua[3]['dt_thu_hoi'], '0')
        self.assertIn('DT thu hồi bản đồ 428', kq.ho[1]['ghi_chu'][1])
        cb = '\n'.join(kq.canh_bao)
        self.assertIn('chưa có diện tích', cb)
        self.assertIn('Tờ 72 thửa 99 (thửa 33 cũ) có 2 hộ', cb)
        self.assertIn('Không Thửa', cb)

    def test_cccd_o_so_mat_so_0_dau(self):
        def bang(wb):
            ws = wb.active
            ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Số CCCD', 'Tờ', 'Thửa', 'DT thu hồi', 'Loại đất'])
            ws.append([1, 'Nguyễn Văn A', 'ấp 1', 75092001234, 1, 1, 100, 'ONT'])      # ô SỐ: Excel bỏ số 0 đầu
            ws.append([2, 'Nguyễn Văn A', 'ấp 1', '075092001234', 1, 2, 50, 'CLN'])   # cùng người, ô chữ đủ 12 số
            ws.append([3, 'Trần B', 'ấp 1', 25123456, 1, 3, 30, 'LUC'])                 # CMND 9 số mất số 0
        p = self.td / 'cccd.xlsx'
        _ghi(p, bang)
        kq = nhap_tho.doc(p)
        self.assertEqual([(h['ho_ten'], h['so_cccd']) for h in kq.ho],
                         [('Nguyễn Văn A', '075092001234'), ('Trần B', '025123456')])

    def test_bang_lon_xon(self):
        p = self.td / 'lonxon.xlsx'
        _ghi(p, _lon_xon)
        kq = nhap_tho.doc(p)
        self.assertEqual(kq.loi, [])
        self.assertEqual(kq.bo_cot.sheet, 'Bang 1')
        self.assertEqual(kq.bo_cot.dong_tieu_de[-1], 5)                 # ô gộp dọc: dòng 5 đã đủ tên cột
        self.assertIn('DỰ ÁN ĐƯỜNG ABC', kq.tieu_de_bang)
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Tống Văn E', 'Đỗ F'])
        self.assertEqual(kq.ho[0]['so_cccd'], '0123456789')
        self.assertEqual([(t['ma_ho'], t['so_to'], t['so_thua'], t['dt_thu_hoi'], t['loai_dat']) for t in kq.thua],
                         [(1, '71', '1', '1070.5', 'ONT'), (1, '71', '2', '39.4', 'CLN'),
                          (2, '72', '5', '12', 'BHK'), (2, '72', '6', '8', 'BHK')])

    def test_dia_ban_tu_ten(self):
        self.assertEqual(nhap_tho.dia_ban_tu_ten('Dự án ĐT762 đoạn qua xã Bàu Hàm'), ('Xã', 'Bàu Hàm'))
        self.assertEqual(nhap_tho.dia_ban_tu_ten('Đường ABC, phường Hố Nai (giai đoạn 2)'), ('Phường', 'Hố Nai'))
        self.assertEqual(nhap_tho.dia_ban_tu_ten('Dự án X'), ('Phường', ''))

    def test_khong_co_bang(self):
        p = self.td / 'rong.xlsx'
        _ghi(p, lambda wb: wb.active.append(['Mã', 'Giá trị']))
        kq = nhap_tho.doc(p)
        self.assertTrue(kq.loi)
        bc = nhap_tho.nhap(p, self.td / 'x.pabt')
        self.assertTrue(bc.loi)
        self.assertFalse((self.td / 'x.pabt').exists())

    def test_xoa_trang_giu_danh_muc(self):
        pabt = self.td / 'cu.pabt'
        con = csdl.tao_moi(pabt)
        with con, csdl.mo_khoa_danh_muc(con):
            con.execute("DELETE FROM dm_hotro")
            con.execute("INSERT INTO dm_hotro (ma, ten) VALUES ('CS1', 'Ổn định đời sống')")
            con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (99, 1, 'Hộ cũ')")
            con.execute("INSERT INTO thua (ma_thua, ma_ho, so_to) VALUES (500, 99, '1')")
            con.execute("INSERT INTO ct_khoan (muc, ma_ho, ten) VALUES (2, 99, 'Nhà')")
            con.execute("INSERT INTO tong_excel (ma_ho, tong) VALUES (99, '1000')")
            con.execute("UPDATE du_an SET ten = 'Dự án cũ', so_phuong_an = '15' WHERE id = 1")
        con.close()
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        bc = nhap_tho.nhap(xl, pabt, 'Dự án mới')
        self.assertEqual((bc.loi, bc.so_ho, bc.so_thua), ([], 5, 5))
        self.assertIn('Họ tên = "Họ và tên hồ sơ kiểm đếm"', bc.nhan_cot)
        con = csdl.mo(pabt)
        try:
            dem = lambda b: con.execute(f'SELECT COUNT(*) FROM {b}').fetchone()[0]
            self.assertEqual((dem('ho'), dem('thua'), dem('ct_khoan'), dem('tong_excel'), dem('dm_hotro'), dem('nhat_ky')),
                             (5, 5, 0, 0, 1, 1))
            da = con.execute('SELECT ten, so_phuong_an, nguon_nhap FROM du_an').fetchone()
            self.assertEqual(tuple(da), ('Dự án mới', '', 'ds.xlsx'))
            self.assertIsNone(con.execute('SELECT 1 FROM ho WHERE ma_ho = 99').fetchone())
        finally:
            con.close()
        # tạo file mới, lấy danh mục từ file cũ
        moi = self.td / 'moi.pabt'
        nhap_tho.nhap(xl, moi, danh_muc=pabt)
        con = csdl.mo(moi)
        try:
            self.assertEqual(con.execute('SELECT ten FROM dm_hotro').fetchone()[0], 'Ổn định đời sống')
            self.assertEqual(con.execute('SELECT ten FROM du_an').fetchone()[0], 'ds')
        finally:
            con.close()


if __name__ == '__main__':
    unittest.main()
