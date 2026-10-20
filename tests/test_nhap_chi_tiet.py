"""Nhập phương án chi tiết từ Excel (mỗi sheet một hộ, kiểu bản in IN_CHITIET). Dữ liệu thử tự dựng, không dùng file thật."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, don_gia, doi_chieu, in_an, nhap_chi_tiet
from pabt.nghiep_vu import NGUON_DM, NGUON_TAY, thanh_tien_khoan
from pabt.tien import D

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False

GHI_CHU_DAT = 'Đất do Khu Bảo tồn quản lý, không tính toán bồi thường về đất theo Điều 101 Luật Đất đai năm 2024.'


def _dm_mau() -> tuple:
    """Hai mục nhà, công trình có giá trong bộ đơn giá tích hợp: (tên, ĐVT, đơn giá)."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        ds = con.execute("SELECT ten, dvt, don_gia FROM dm_taisan WHERE nhom = 2 AND COALESCE(don_gia, '') <> '' "
                         'ORDER BY rowid LIMIT 2').fetchall()
        return [(r['ten'], r['dvt'], D(r['don_gia'])) for r in ds]
    finally:
        con.close()


def _sheet(ws, ten, cccd, dong_bang, nguon_goc=('Căn cứ Giấy xác nhận nguồn gốc đất số 1/GXN ngày 1/8/2026:',
                                                '- Thửa đất số 5, tờ bản đồ số 7: hợp đồng giao khoán.'), tdc='Không có.'):
    ws['A1'] = 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT \nTHÀNH PHỐ ĐỒNG NAI'
    ws['E1'] = 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc'
    ws['A2'] = 'CHI NHÁNH THỬ'
    ws['A3'] = 'Số:            /PA-THU\n(DỰ THẢO)'
    ws['E3'] = 'Phú Lý, ngày       tháng        năm 2026'
    ws['A4'] = 'PHƯƠNG ÁN CHI TIẾT\nBỒI THƯỜNG, HỖ TRỢ & TÁI ĐỊNH CƯ KHI NHÀ NƯỚC THU HỒI ĐẤT\nDự án Đường thử nghiệm'
    ws['A6'] = 'I. Tổ chức và hộ gia đình, cá nhân bị thu hồi đất, tài sản gắn liền với đất'
    ws['B7'], ws['C7'] = 'Họ và tên:', f'{ten} là chủ sở hữu tài sản gắn liền với thửa đất số 5, tờ bản đồ số 7.' if ten else None
    ws['B8'], ws['C8'] = 'Số CCCD:', cccd
    ws['B9'], ws['C9'] = 'Địa chỉ thường trú:', 'ấp 1, xã Phú Lý, thành phố Đồng Nai.'
    ws['B10'], ws['C10'] = 'Số điện thoại:', '0900.000.001.'
    ws['A11'] = 'II. Thông tin nguồn gốc đất:'
    for i, s in enumerate(nguon_goc):
        ws.cell(12 + i, 1, '         ' + s)
    ws['A15'] = 'III. Bảng tính toán bồi thường, hỗ trợ '
    for c, s in enumerate(['STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ (%)', 'Thành tiền\n(đồng)', 'Ghi chú'], 1):
        ws.cell(16, c, s)
    r = 17
    for d in dong_bang:
        for c, v in enumerate(d, 1):
            if v is not None:
                ws.cell(r, c, v)
        r += 1
    ws.cell(r + 1, 1, 'IV')
    ws.cell(r + 1, 2, f'Phương án tái định cư: {tdc}')


def tao_file(p: Path) -> dict:
    """File thử: sheet 1 (đất không tính tiền, nhà khớp danh mục, khác giá, ngoài danh mục, cây thiếu đơn giá),
    sheet 2 (đất có giá, dòng con), sheet mẫu, sheet lỗi #N/A, sheet tổng hợp (không phải phương án)."""
    (t1, dvt1, g1), (t2, dvt2, g2) = _dm_mau()
    tl = D('0.8')
    k1, k2, k3 = thanh_tien_khoan(10, g1, tl), thanh_tien_khoan(3, g2 + 1000, tl), thanh_tien_khoan(2, 500000, 1)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '1'
    _sheet(ws, 'Nguyễn Văn A', '092075012345 - ngày 29/9/2021 - Nơi cấp: Cục CS QLHC về TTXH.', [
        (1, 'Bồi thường đất', None, 150.5),
        ('1.1', 'Thửa đất số 5, tờ bản đồ số 7, loại đất RPD, xã Phú Lý', 'm²', 100.5, None, None, None, GHI_CHU_DAT),
        ('1.2', 'Một phần thửa đất số 6, tờ bản đồ số 7, xã Phú Lý', 'm²', 50),
        (2, 'Hỗ trợ về nhà và công trình xây dựng', None, None, None, None, int(k1 + k2 + k3)),
        ('2.1', t1, dvt1, 10, float(g1), 0.8, int(k1), 'Thửa 5'),
        ('2.2', t2, dvt2, 2.9999999999999996, float(g2 + 1000), 0.8, int(k2)),
        ('2.3', 'Chuồng nuôi chim yến kiểu lạ', 'cái', 2, 500000, None, int(k3)),
        (3, 'Hỗ trợ về cây trồng', None, None, None, None, 0),
        ('3.1', 'Sung (xác định đường kính)', 'Cây', 1, None, 0.8),
        (4, 'Hỗ trợ các loại', None, None, None, None, 0),
        ('4.1', 'Hỗ trợ ổn định đời sống', None, None, None, None, None, 'Tính bổ sung sau.'),
        (5, 'Thưởng chấp hành bàn giao mặt bằng trước thời hạn'),
        ('TỔNG CỘNG', None, None, None, None, None, int(k1 + k2 + k3)),
    ], tdc='Sau khi UBND xã xác nhận điều kiện tái định cư (nếu có).')
    dat = thanh_tien_khoan(D('120'), 2000000, 1)
    con1, con2 = thanh_tien_khoan(4, 100000, 1), thanh_tien_khoan(6, 100000, 1)
    _sheet(wb.create_sheet('2'), 'Trần Thị B', '079 001 000002', [
        (1, 'Bồi thường đất', None, 120, None, None, int(dat)),
        ('1.1', 'Thửa đất số 9, tờ bản đồ số 7, loại đất CLN, xã Phú Lý', 'm²', 120, 2000000, 1, int(dat)),
        (2, 'Hỗ trợ về nhà và công trình xây dựng', None, None, None, None, int(con1 + con2)),
        ('2.1', 'Hàng rào tạm', None, None, None, None, int(con1 + con2)),
        ('-', 'Đoạn phía trước', 'm', 4, 100000, 1, int(con1)),
        ('-', 'Đoạn phía sau', 'm', 6, 100000, 1, int(con2)),
        ('TỔNG CỘNG', None, None, None, None, None, int(dat + con1 + con2)),
    ])
    _sheet(wb.create_sheet('mẫu áp'), 'Mẫu Tổ Chức', None, [('1.1', 'Thửa đất số 1, tờ bản đồ số 1', 'm²', 1)])
    _sheet(wb.create_sheet('KIEMTRA'), 'Lỗi C', None, [(2, 'Nhà'), ('2.1', '#N/A', 'm²', '#N/A')])
    tong = wb.create_sheet('BANG TONG HOP')
    tong.append(['STT', 'Họ và tên', 'Địa chỉ', 'Tổng'])
    wb.save(p)
    return dict(k1=k1, k2=k2, k3=k3, dat=dat, t1=t1, g1=g1, t2=t2, g2=g2)


class TestNhapChiTiet(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.xl = Path(self.td.name) / 'PA chi tiết.xlsx'
        self.so = tao_file(self.xl)
        self.p = Path(self.td.name) / 'du_an.pabt'

    def tearDown(self):
        self.td.cleanup()

    def test_doc(self):
        self.assertTrue(nhap_chi_tiet.la_file_chi_tiet(self.xl))
        kq = nhap_chi_tiet.doc(self.xl)
        self.assertEqual([h.sheet for h in kq.ho], ['1', '2', 'mẫu áp', 'KIEMTRA'])
        self.assertEqual(kq.bo_qua, ['BANG TONG HOP'])
        self.assertEqual([h.chon for h in kq.ho], [True, True, False, False])
        h = kq.ho[0]
        self.assertEqual(h.ten_ngan, 'Nguyễn Văn A')
        self.assertEqual((h.so_cccd, h.ngay_cap, h.noi_cap), ('092075012345', '29/9/2021', 'Cục CS QLHC về TTXH'))
        self.assertEqual(h.dia_chi, 'ấp 1, xã Phú Lý, thành phố Đồng Nai')
        self.assertEqual(h.nguon_goc.split('\n')[1], '- Thửa đất số 5, tờ bản đồ số 7: hợp đồng giao khoán.')
        self.assertEqual(len(h.dat), 2)
        self.assertEqual([len(h.khoan[m]) for m in (2, 3, 4)], [3, 1, 1])
        self.assertEqual(h.khoan[2][1].so_luong, D(3))                  # 2,9999999999999996 -> 3
        self.assertEqual(h.khoan[2][2].ty_le, None)
        self.assertEqual(h.tong['tong'], self.so['k1'] + self.so['k2'] + self.so['k3'])
        self.assertEqual(kq.ho[1].so_cccd, '079001000002')
        self.assertEqual([d.ten for d in kq.ho[1].khoan[2]], ['Hàng rào tạm - Đoạn phía trước', 'Hàng rào tạm - Đoạn phía sau'])
        self.assertTrue(kq.ho[3].loi)
        self.assertEqual(kq.du_an['ten'], 'Đường thử nghiệm')
        self.assertEqual((kq.du_an['ten_dia_ban'], kq.du_an['nam'], kq.du_an['cap_dia_ban'], kq.du_an['ky_hieu_so']),
                         ('Phú Lý', '2026', 'Xã', 'PA-THU'))
        t = nhap_chi_tiet._thua_tu_ten('Một phần thửa đất số 6, tờ bản đồ số 7, loại đất ONT+CLN, xã Phú Lý (Vị trí 2)')
        self.assertEqual((t['so_thua'], t['so_to'], t['loai_dat'], t['vi_tri'], t['mot_phan']), ('6', '7', 'ONT+CLN', '2', True))

    def test_nhap_du_an_moi(self):
        bc = nhap_chi_tiet.nhap(self.xl, self.p)
        self.assertEqual(len(bc.them), 2)
        self.assertEqual({s for s, _ in bc.bo_qua}, {'mẫu áp', 'KIEMTRA'})
        self.assertEqual(bc.so_thua, 3)
        self.assertTrue(any('Sung' in x and 'chưa có đơn giá' in x for x in bc.canh_bao))
        con = csdl.mo(self.p)
        try:
            da = con.execute('SELECT * FROM du_an').fetchone()
            self.assertEqual((da['ten'], da['cap_dia_ban'], da['ten_dia_ban'], da['nam']), ('Đường thử nghiệm', 'Xã', 'Phú Lý', 2026))
            ho = con.execute('SELECT * FROM ho ORDER BY ma_ho').fetchall()
            self.assertEqual(ho[0]['trang_thai'], nhap_chi_tiet.TRANG_THAI)
            self.assertIsNone(ho[0]['luu_luc'])                         # số liệu từ Excel: tính là "đã lập"
            self.assertEqual(ho[0]['phap_ly'], GHI_CHU_DAT)             # đất không tính tiền: ghi chú vào pháp lý
            self.assertEqual(ho[0]['tai_dinh_cu'], '')                  # câu mặc định "Sau khi UBND…" không lưu
            self.assertEqual(ho[1]['tai_dinh_cu'], 'Không có.')
            # 0.9.96: mục 1 luôn có dòng cho mỗi thửa, kể cả đơn giá 0 (đất không bồi thường vẫn hiện trong phương án)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ct_dat WHERE ma_ho = 1').fetchone()[0], 2)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM ct_dat WHERE ma_ho = 1 AND gia_bang_gia != '0'").fetchone()[0], 0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ct_dat WHERE ma_ho = 2').fetchone()[0], 1)
            k = con.execute('SELECT * FROM ct_khoan WHERE ma_ho = 1 AND muc = 2 ORDER BY thu_tu').fetchall()
            self.assertEqual([x['nguon_gia'] for x in k], [NGUON_DM, NGUON_TAY, NGUON_TAY])
            self.assertTrue(k[0]['ma'])
            self.assertIn('Đơn giá nhập tay (đơn giá', k[1]['can_cu_gia'])
            self.assertTrue(k[1]['ma_tuong_duong'])
            self.assertIn('PA chi tiết.xlsx', k[2]['can_cu_gia'])
            self.assertEqual(D(k[0]['thanh_tien_excel']), self.so['k1'])
            kq = doi_chieu.doi_chieu(con)
            self.assertFalse(kq.ho[0]['lech'], kq.ho[0])
            self.assertFalse(kq.dong_lech)
            from pabt.nghiep_vu import tinh_ho
            thuong = tinh_ho(con, 2).muc[5]                             # có tiền đất: phần mềm tự tính thưởng (mục 5)
            self.assertEqual(kq.ho[1]['tong'], self.so['dat'] + D(1000000) + thuong)
            # bản in: hộ không tính tiền đất liệt kê thửa, dòng đầu ghi pháp lý
            dong, _ = in_an.dong_chi_tiet(con, 1)
            self.assertEqual(dong[1][1][7], GHI_CHU_DAT)
            self.assertEqual(dong[2][1][7], '')
            self.assertEqual(in_an.phan_loai_lap(con), {1: 'da_lap', 2: 'da_lap'})
        finally:
            con.close()

    def test_nhap_lai(self):
        nhap_chi_tiet.nhap(self.xl, self.p)
        bc = nhap_chi_tiet.nhap(self.xl, self.p)
        self.assertEqual((len(bc.them), len(bc.thay)), (0, 0))
        self.assertIn(('1', 'trùng hộ 1 đã có trong dự án'), bc.bo_qua)
        con = csdl.mo(self.p)
        with con:
            con.execute("UPDATE ct_khoan SET so_luong = '99' WHERE ma_ho = 1 AND muc = 2 AND thu_tu = 1")
            con.execute("UPDATE ho SET dot_id = NULL, theo_doi = 'giữ' WHERE ma_ho = 1")
        con.close()
        bc = nhap_chi_tiet.nhap(self.xl, self.p, trung='thay', ten_sheet=['1'])
        self.assertEqual(bc.thay, [(1, 'Nguyễn Văn A')])
        con = csdl.mo(self.p)
        try:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 2)
            self.assertEqual(con.execute("SELECT so_luong FROM ct_khoan WHERE ma_ho = 1 AND muc = 2 AND thu_tu = 1").fetchone()[0], '10')
            self.assertEqual(con.execute('SELECT theo_doi FROM ho WHERE ma_ho = 1').fetchone()[0], 'giữ')
            self.assertEqual(con.execute('SELECT COUNT(*) FROM thua WHERE ma_ho = 1').fetchone()[0], 2)
        finally:
            con.close()
        bc = nhap_chi_tiet.nhap(self.xl, self.p, trung='them', ten_sheet=['2'])
        self.assertEqual(bc.them, [(3, 'Trần Thị B')])

    def test_khong_co_sheet(self):
        wb = openpyxl.Workbook()
        wb.active.append(['Họ tên', 'Địa chỉ'])
        f = Path(self.td.name) / 'khac.xlsx'
        wb.save(f)
        self.assertFalse(nhap_chi_tiet.la_file_chi_tiet(f))
        with self.assertRaises(nhap_chi_tiet.LoiNhap):
            nhap_chi_tiet.nhap(f, self.p)

    @unittest.skipUnless(CO_QT, 'không có PySide6')
    def test_giao_dien(self):
        from PySide6.QtCore import Qt
        from pabt import app as ud
        from pabt.man_hinh_nhap_chi_tiet import HopNhapChiTiet
        w = ud.CuaSoChinh()
        try:
            bc = w.nhap_chi_tiet(str(self.xl), dich=str(self.p), cho=False)
            self.assertEqual(len(bc.them), 2)
            self.assertEqual(w.mo_hinh.rowCount(), 2)                  # mở dự án vừa tạo
            # dự án đang mở: nhập vào chính dự án đó; hộp thoại báo hộ trùng, chỉ chọn sheet 2
            kq = nhap_chi_tiet.doc(self.xl)
            hop = HopNhapChiTiet(kq, w.con, w, 'Đường thử nghiệm')
            self.assertEqual(hop.trung[0], 1)
            self.assertFalse(hop.bang.item(3, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable)    # sheet lỗi: không chọn được
            hop.chon_tat_ca(False)
            self.assertFalse(hop.b_nhap.isEnabled())
            hop.bang.item(1, 0).setCheckState(Qt.CheckState.Checked)
            hop.nut_trung['them'].setChecked(True)
            self.assertEqual(hop.ap_dung(), 'them')
            self.assertEqual([h.chon for h in kq.ho], [False, True, False, False])
            hop.close()
            bc = w.nhap_chi_tiet(str(self.xl), sheet=['2'], trung='them', cho=False)
            self.assertEqual(bc.them, [(3, 'Trần Thị B')])
            self.assertEqual(w.mo_hinh.rowCount(), 3)
            self.assertIn('Nhập phương án chi tiết…', w.lenh)
        finally:
            w.dong_du_an()
            w.close()


class TestKieuLaMa(unittest.TestCase):
    """Bảng kiểu "áp giá" (0.9.20): mục La Mã I-V theo tên, nhóm A / B, dòng đánh số 1, 2, 3; "Thửa 457 tờ 35 - đất LUK (VT 1…)";
    nhãn "Số định danh cá nhân/CCCD" có hai số. Số liệu GIẢ LẬP."""

    def _file(self, p: Path) -> None:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '1, Thử'
        for o, v in {'A1': 'TRUNG TÂM THỬ', 'A6': 'PHƯƠNG ÁN BỒI THƯỜNG… DỰ ÁN ĐƯỜNG THỬ',
                     'A8': 'I. Tổ chức và hộ gia đình, cá nhân bị thu hồi, tài sản gắn liền với đất:',
                     'A9': 'Họ và tên chủ hộ:', 'C9': 'Nguyễn Văn Thử - Trần Thị Mẫu', 'A10': 'Địa chỉ thường trú:',
                     'C10': 'Khu phố 1, phường Thử', 'A11': 'Số định danh cá nhân/CCCD:', 'C11': '001001000001\n001001000002',
                     'A12': 'Số điện thoại:', 'C12': '0900000000', 'A13': 'II. Thông tin vị trí, nguồn gốc đất:',
                     'A15': '* Nguồn gốc đất: đất khai hoang năm 1990.', 'A16': 'Theo chi tiết sau:'}.items():
            ws[o] = v
        for c, s in enumerate(['STT', 'Hạng mục', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ (%)', 'Thành Tiền\n(đồng)', 'Ghi chú'], 1):
            ws.cell(17, c, s)
        dong = [('A', 'Phương án bồi thường bằng tiền'), ('I', 'Bồi thường đất', None, 110, None, None, 73_370_000),
                (1, 'Thửa 457 tờ 35 - đất LUK (VT 1: phạm vi 2)', 'm2', 100, 667000, 1, 66_700_000),
                (2, 'Thửa 123 tờ 36 - đất NTS (VT 2)', 'm2', 10, 667000, 1, 6_670_000),
                ('II', 'Bồi thường, hỗ trợ vật kiến trúc', None, None, None, None, 606_000),
                (1, 'Hàng rào lưới B40', 'm2', 6, 101000, 1, 606_000),
                ('III', 'Hỗ trợ cây trồng', None, None, None, None, 1_617_000),
                (1, 'Dừa năm thứ 2', 'cây', 3, 673935, 0.8, 1_617_000),
                ('IV', 'Hỗ trợ các loại', None, None, None, None, 0),
                (1, 'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm bằng tiền', 'm2', 110, None, 1.5, 0),
                ('V', 'Thưởng cho người có đất thu hồi bàn giao đất trước thời hạn', None, None, None, None, 2_000_000),
                ('TỔNG CỘNG (I+II+III+IV+V)', None, None, None, None, None, 77_593_000),
                ('B', 'Phương án tái định cư: không đủ điều kiện bố trí TĐC')]
        for i, d in enumerate(dong):
            for c, v in enumerate(d, 1):
                if v is not None:
                    ws.cell(18 + i, c, v)
        wb.save(p)

    def test_doc_va_nhap(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'ap_gia.xlsx'
            self._file(f)
            h = nhap_chi_tiet.doc(f).ho[0]
            self.assertTrue(h.chon, h.ly_do)
            self.assertEqual((len(h.dat), len(h.khoan[2]), len(h.khoan[3]), len(h.khoan[4])), (2, 1, 1, 1))
            self.assertEqual((h.tong[1], h.tong[2], h.tong[3], h.tong[5], h.tong['tong']),
                             (73_370_000, 606_000, 1_617_000, 2_000_000, 77_593_000))
            self.assertEqual(h.so_cccd, '001001000001')                               # ô có 2 số: lấy số đầu, báo số kia
            self.assertTrue(any('001001000002' in x for x in h.canh_bao))
            self.assertNotIn('Theo chi tiết', h.nguon_goc)
            self.assertEqual(h.tai_dinh_cu, 'không đủ điều kiện bố trí TĐC')
            t = nhap_chi_tiet._thua_tu_ten(h.dat[0].ten)
            self.assertEqual((t['so_thua'], t['so_to'], t['loai_dat']), ('457', '35', 'LUK'))
            p = Path(td) / 'a.pabt'
            bc = nhap_chi_tiet.nhap(f, p)
            self.assertEqual((len(bc.them), bc.so_thua), (1, 2))
            con = csdl.mo(p)
            try:
                k = doi_chieu.doi_chieu(con).ho[0]
                for m in (1, 2, 3):
                    self.assertEqual(k['muc'][m], D(h.tong[m]), m)
            finally:
                con.close()

    def test_muc_theo_ten(self):
        for ten, m in (('Bồi thường đất', 1), ('Bồi thường, hỗ trợ vật kiến trúc', 2), ('Hỗ trợ cây trồng', 3),
                       ('Bồi thường cây trồng', 3), ('Hỗ trợ các loại', 4),
                       ('Thưởng cho người có đất thu hồi bàn giao đất trước thời hạn', 5), ('Phương án bồi thường bằng tiền', 0)):
            self.assertEqual(nhap_chi_tiet.muc_theo_ten(ten), m, ten)


if __name__ == '__main__':
    unittest.main()
