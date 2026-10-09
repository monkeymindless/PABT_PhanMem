"""Kiểm thử 0.9.4: nhập công thức ở ô số, chọn vị trí theo bảng giá NQ 28, đổi thửa của dòng mục 1, hàng nhập nhanh (chọn →
số lượng → thêm), cây theo đường kính / chu vi, thuê nhà gộp một dòng theo nhân khẩu, tái định cư là tình trạng của hộ,
hồ sơ và phương án chung một cửa sổ, mật độ cây, Bảng khái toán theo mẫu."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import cay_trong as ct
from pabt.lap_pa import LoiNhap, doc_so, doc_so_luong
from pabt.tien import D, la_cong_thuc, tinh_cong_thuc
from tests.test_nghiep_vu import FILE_EXCEL

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestCongThuc(unittest.TestCase):
    def test_tinh(self):
        self.assertEqual(tinh_cong_thuc('=4,2*5,7'), D('23.94'))
        self.assertEqual(tinh_cong_thuc('12x3 + 1,5'), D('37.5'))
        self.assertEqual(tinh_cong_thuc('(10 - 2) × 3 : 4'), D(6))
        self.assertEqual(tinh_cong_thuc('1.000 * 2,5'), D(2500))          # 1.000 = một nghìn
        self.assertEqual(tinh_cong_thuc('50%*200'), D(100))
        self.assertEqual(tinh_cong_thuc('-3+5'), D(2))
        for sai in ('=4,2*', '1/0', '2+(3', 'abc'):
            with self.assertRaises(ValueError, msg=sai):
                tinh_cong_thuc(sai)
        self.assertTrue(la_cong_thuc('=12'))
        self.assertTrue(la_cong_thuc('4,2*5,7'))
        self.assertFalse(la_cong_thuc('1.480.500'))
        self.assertFalse(la_cong_thuc('-5'))

    def test_doc_so(self):
        self.assertEqual(doc_so('=4,2*5,7', 'SL'), D('23.94'))
        self.assertEqual(doc_so('143,8', 'SL'), D('143.8'))
        self.assertEqual(doc_so_luong('=4,2*5,7'), D('23.9'))             # làm tròn 1 chữ số thập phân
        self.assertEqual(doc_so_luong('=0,12345*2', 'ha'), D('0.2469'))   # ha: 4 chữ số
        # vật nuôi QĐ 31/2025: ao 0,25 ha (ĐVT ha/vụ), lồng 25 m³ (ĐVT 100m3/vụ) - trước đây làm tròn thành 0,3 (trả thừa 20%)
        self.assertEqual(doc_so_luong('0,25', 'ha/vụ'), D('0.25'))
        self.assertEqual(doc_so_luong('0,25', '100m3/vụ'), D('0.25'))
        self.assertEqual(doc_so_luong('0,25', 'm²'), D('0.3'))
        with self.assertRaises(LoiNhap) as cm:
            doc_so('=4,2*', 'Số lượng')
        self.assertIn('công thức', str(cm.exception))

    def test_chinh_sach(self):
        from pabt import chinh_sach as cs
        from pabt.lap_pa import cau_tai_dinh_cu
        self.assertEqual(cs.ten_ngan('Hỗ trợ ổn định đời sống - Thu hồi dưới 30% đất NN (mức 50%): 6 tháng'), 'Hỗ trợ ổn định đời sống')
        self.assertEqual(cs.ten_ngan('Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm (hệ số 1,5)'),
                         'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm')
        self.assertEqual(cs.ten_ngan('Hỗ trợ di chuyển tài sản - trong phạm vi xã, phường'), 'Hỗ trợ di chuyển tài sản')
        self.assertEqual(cs.cach_tinh_on_dinh(4, 30, 6, 16000, D('0.5')), '4 nhân khẩu x 30kg gạo x 6 tháng x 16.000 đồng x 50%')
        self.assertEqual(cs.cach_tinh_thue_nha(5, 1, 6000000, 1500000, 4),
                         '(1 hộ (4 nhân khẩu) * 1 tháng * 6.000.000 đồng) + (1 nhân khẩu tăng thêm * 1.500.000 đồng * 1 tháng)')
        self.assertEqual(cau_tai_dinh_cu('Đủ điều kiện theo khoản 4 Điều 111 Luật Đất đai năm 2024'),
                         'Đủ điều kiện bố trí một (01) suất tái định cư theo quy định tại khoản 4 Điều 111 Luật Đất đai năm 2024.')
        self.assertEqual(cau_tai_dinh_cu('Không đủ điều kiện tái định cư'), 'Không đủ điều kiện tái định cư.')
        self.assertEqual(cau_tai_dinh_cu(''), '')

    def test_mat_do_va_duong_kinh(self):
        p = ct.phan_tich_mat_do(30, 1000, 200)           # 200 cây/ha: 50 m²/cây; 1.000 m² tối đa 20 cây
        self.assertEqual((p['toi_da'], p['trong'], p['ngoai'], p['dt_can'], p['dt_thieu'], p['m2_moi_cay']),
                         (20, 20, 10, D(1500), D(500), D(50)))

        class M:
            def __init__(self, ma, ten):
                self.ma, self.ten = ma, ten
        bang = ct.BangCayDK([M('A', 'Sao đen (d <15 cm)'), M('B', 'Sao đen (d >15-18 cm)')])
        nhom, loi = ct.gom_theo_kich_thuoc(bang, 'Sao đen', [(D(10), 2), (D(16), 3), (D(30), 1)], la_duong_kinh=True)
        self.assertEqual(sorted((m.ma, so) for m, so, _, _ in nhom), [('A', 2), ('B', 3)])
        self.assertEqual(loi, [D(30)])
        self.assertIn('Đường kính đo 16 cm', ct.mo_ta_do(D(16), D(16), True))


@unittest.skipUnless(FILE_EXCEL.exists(), 'cần file Excel mẫu')
class TestNhapLieuDuAn(unittest.TestCase):
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
        from pabt import csdl
        self.p = Path(self.tmp.name) / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()

    def test_vi_tri_nq28_doi_thua_gia_tay(self):
        from pabt.lap_pa import BoSoan
        bo = BoSoan(self.con, 1)
        ds = bo.ds_vi_tri_nq28(0)
        self.assertTrue(ds)
        nhan, r, g = ds[0]
        tb = bo.chon_vi_tri_nq28(0, r)
        d = bo.pa.dat[0]
        self.assertEqual(d.gia_bang_gia, g)
        self.assertIn(r['ten_duong'], d.vi_tri)
        self.assertIn('NQ 28', tb)
        bo.sua_dat(0, 'gia_bang_gia', '=150000*1,2')                      # đơn giá khác: nhập tay đè (công thức)
        self.assertEqual(d.gia_bang_gia, 180000)
        bo.sua_dat(0, 'dien_tich', '=20*10,55')
        self.assertEqual(d.dien_tich, D('211.0'))
        # đổi thửa của dòng: chọn thửa khác của hộ
        ds_thua = bo.thua_cua_ho()
        khac = next(mt for mt, _, _ in ds_thua if mt != d.ma_thua)
        bo.sua_dat(0, 'thua', khac)
        self.assertEqual(d.ma_thua, khac)
        bo.sua_dat(0, 'thua', bo.ten_thua(khac))                         # gõ đúng tên thửa đang gắn: không đổi
        with self.assertRaises(LoiNhap):
            bo.sua_dat(0, 'thua', 'Thửa 9999 tờ 1')
        bo.dat_tai_dinh_cu('Không đủ điều kiện tái định cư')
        bo.luu()
        self.assertEqual(self.con.execute('SELECT tai_dinh_cu FROM ho WHERE ma_ho = 1').fetchone()[0],
                         'Không đủ điều kiện tái định cư')

    def test_khai_toan(self):
        import openpyxl
        from pabt import du_toan
        dt = du_toan.tu_du_an(self.con)
        dt.dia_chi = 'Khu phố Bà Hào, phường Trị An'
        dt.them_chi_phi_mac_dinh()
        f = Path(self.tmp.name) / 'kt' / 'KhaiToan.xlsx'
        kq = du_toan.xuat_khai_toan(dt, f)
        self.assertTrue(kq['excel'].exists())
        ws = openpyxl.load_workbook(f).active
        cot2 = [ws.cell(r, 2).value for r in range(1, ws.max_row + 1)]
        self.assertEqual(ws['A5'].value, 'BẢNG KHÁI TOÁN')
        self.assertIn('Bồi thường về đất', cot2)
        self.assertIn('Tổng cộng', cot2)
        self.assertIn('Chi phí thực hiện công tác bồi thường 2,5%', cot2)
        self.assertIn('Phí dự phòng 10%', cot2)
        r = cot2.index('TỔNG DỰ ƯỚC KINH PHÍ') + 1
        self.assertEqual(D(ws.cell(r, 7).value), dt.tong)
        self.assertIn('Bà Hào', ws['A7'].value)
        self.assertEqual(ws['A8'].value, 'Theo chi tiết sau:')                 # 0.9.12: bỏ dòng "TỔNG DỰ ƯỚC KINH PHÍ: … đồng"
        self.assertFalse(any(str(ws.cell(r, 1).value or '').startswith('TỔNG DỰ ƯỚC') for r in range(1, ws.max_row + 1)))


@unittest.skipUnless(CO_QT and FILE_EXCEL.exists(), 'cần PySide6 và file Excel mẫu')
class TestManHinhNhapLieu(TestNhapLieuDuAn):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        super().setUpClass()

    def setUp(self):
        from PySide6.QtWidgets import QMessageBox
        super().setUp()
        self.thong_bao = []
        self.va = [mock.patch.object(QMessageBox, n, side_effect=lambda *a, **k: self.thong_bao.append(a[2]))
                   for n in ('warning', 'information')]
        # đóng cửa sổ còn thay đổi: "Không lưu" (không để hộp hỏi chờ bấm)
        self.va.append(mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Discard))
        for v in self.va:
            v.start()

    def tearDown(self):
        for v in self.va:
            v.stop()
        super().tearDown()

    def test_mot_cua_so_ho_so_va_nhap_nhanh(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        self.assertEqual(w.tab.count(), 5)
        # thẻ hồ sơ: sửa CCCD, "Tiếp theo" lưu hồ sơ
        w.tab.setCurrentIndex(0)
        w.ho_so.o['so_cccd'].setText('079 123 456 789')
        self.assertTrue(w.sang_the(1))
        self.assertEqual(self.con.execute('SELECT so_cccd FROM ho WHERE ma_ho = 1').fetchone()[0], '079123456789')
        self.assertFalse(w.ho_so.co_thay_doi())
        # mục 2: chọn từ danh mục + số lượng công thức
        b2 = w.bang[2]
        n2 = b2.bang.rowCount()
        m = w.bo.dm.tim(2, 'nha 1 tang')[0]
        self.assertTrue(b2.o_chon.chon_du_lieu(m))
        i = w.them_nhanh(2, so_luong='=4,2*5,7', ty_le='80')
        d = w.bo.pa.khoan[2][i]
        self.assertEqual((d.ma, d.so_luong, d.ty_le), (m.ma, D('23.9'), D('0.8')))
        self.assertEqual(b2.bang.rowCount(), n2 + 1)
        self.assertEqual(b2.o_chon.text(), '')                           # thêm xong: xóa ô nhập
        # gõ tên không có trong danh mục: dòng nhập tay, đơn giá gõ ngay
        b2.o_chon.setText('Mái che lưới B40 tự làm')
        j = w.them_nhanh(2, so_luong='12')
        self.assertEqual((w.bo.pa.khoan[2][j].ten, w.bo.pa.khoan[2][j].nguon_gia), ('Mái che lưới B40 tự làm', 'nhập tay'))
        w.bo.sua_khoan(2, j, 'don_gia', '150.000')
        # mục 3: cây theo đường kính
        b3 = w.bang[3]
        ten_loai = next(t for t in ct.BangCayDK(w.bo.dm.muc[3]).ten_loai('sao den') if 'cảnh' not in t)
        b3.o_chon.chon_du_lieu(('nhom', ten_loai))
        self.assertEqual(b3.cb_kieu.currentData(), 'dk')                # chọn nhóm theo đường kính: tự chuyển kiểu nhập
        n3 = len(w.bo.pa.khoan[3])
        w.them_nhanh(3, so_luong='10, 16x2, 20')
        moi = w.bo.pa.khoan[3][n3:]
        self.assertEqual(sum(x.so_luong for x in moi), 4)
        self.assertTrue(all('Đường kính đo' in x.quy_cach for x in moi))
        # mục 4: thuê nhà chờ TĐC (phường) - một dòng theo nhân khẩu
        w.o_nk.setValue(7)
        w.bang[4].o_chon.chon_du_lieu(w.bo.dm.lay('HT24'))
        k = w.them_nhanh(4, so_luong='3')
        d4 = w.bo.pa.khoan[4][k]
        self.assertEqual((d4.so_luong, d4.don_gia), (3, 14000000))
        w.o_nk.setValue(5)
        self.assertEqual(d4.don_gia, 10000000)
        # tái định cư: chọn tình trạng, không có trong danh sách chọn khoản tiền
        ds4 = list(w.bang[4].o_chon._theo_nhan.values())
        self.assertFalse(any(getattr(x, 'ma', '') in ('HT11', 'HT12', 'HT13') for x in ds4))
        w.bang[4].cb_tdc.setCurrentIndex(2)
        self.assertIn('khoản 4 Điều 111', w.bo.pa.ho.tai_dinh_cu)
        self.assertTrue(w.luu())
        self.assertIn('khoản 4 Điều 111', self.con.execute('SELECT tai_dinh_cu FROM ho WHERE ma_ho = 1').fetchone()[0])
        w.close()

    def test_ho_tro_theo_cach_tinh_va_ban_in(self):
        from pabt import in_an
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        b4 = w.bang[4]
        w.o_nk.setValue(4)
        n = len(w.bo.pa.khoan[4])
        # ổn định đời sống: nhân khẩu, giá gạo, kg, tháng, tỷ lệ
        b4.o_chon.chon_du_lieu(w.bo.dm.lay('HT01'))
        self.assertEqual(b4.cs_loai, 'od')
        b4.o_gao.setText('16.000')
        w.them_nhanh(4)
        d = w.bo.pa.khoan[4][n]
        self.assertEqual((d.ten, d.cach_tinh), ('Hỗ trợ ổn định đời sống', '4 nhân khẩu x 30kg gạo x 6 tháng x 16.000 đồng x 50%'))
        self.assertIn('Hỗ trợ theo', d.ghi_chu)
        # đào tạo, chuyển đổi nghề: mỗi thửa đất NN một dòng, giá đất × 150%
        b4.o_chon.chon_du_lieu(w.bo.dm.lay('HT09'))
        self.assertEqual(b4.cs_loai, 'dt')
        self.assertGreater(b4.bang_dt.rowCount(), 0)
        w.them_nhanh(4)
        dt = [x for x in w.bo.pa.khoan[4][n + 1:] if x.ma == 'HT09']
        self.assertTrue(dt and all(x.ty_le == D('1.5') and x.ten.startswith('Thửa đất') for x in dt))
        # chính sách không có trong đơn giá: nhập tên, số tiền
        b4.o_chon.chon_du_lieu(('ten', 'Hỗ trợ học phí'))
        k = w.them_nhanh(4, so_luong='1')
        self.assertEqual(w.bo.pa.khoan[4][k].ten, 'Hỗ trợ học phí')
        w.bo.sua_khoan(4, k, 'don_gia', '2.000.000')
        w.bang[4].cb_tdc.setCurrentIndex(2)
        self.assertTrue(w.luu())
        dong, _ = in_an.dong_chi_tiet(self.con, 1)
        gop = [x for x in dong if len(x) > 2]
        self.assertTrue(any('30kg gạo' in x[2] for x in gop))                    # cách tính in gộp ô
        self.assertTrue(any(x[1][0] == '-' and x[1][1].startswith('Thửa đất') for x in dong))   # dòng thửa dưới tên chính sách
        f = in_an.lap_chi_tiet(self.con, 1, Path(self.tmp.name) / 'in_cs' / 'pa.xlsx')
        import openpyxl
        ws = openpyxl.load_workbook(f).active
        chu = [str(ws.cell(r, 2).value or '') for r in range(1, ws.max_row + 1)]
        self.assertTrue(any(c.startswith('Tái định cư: Đủ điều kiện bố trí một (01) suất') for c in chu))
        w.close()

    def test_o_tim_chon_va_man_hinh_chinh(self):
        from pabt import app as ud
        from pabt.giao_dien import OTimChon
        o = OTimChon()
        o.dat_muc([('Cây xoài - Năm 1', 1), ('Cây sầu riêng', 2), ('Nhà 01 tầng', 3)])
        self.assertEqual(o.loc('xoai'), ['Cây xoài - Năm 1'])
        self.assertEqual(o.loc('cây'), ['Cây xoài - Năm 1', 'Cây sầu riêng'])          # gõ có dấu cũng khớp
        chon = []
        o.khi_chon = chon.append
        self.assertTrue(o.chon_du_lieu(2))
        self.assertEqual((o.text(), o.chon, chon), ('Cây sầu riêng', 2, [2]))
        cs = ud.CuaSoChinh()
        cs.mo(str(self.p))
        self.assertEqual(cs.the_so['so_ho'].text(), str(cs.mo_hinh.rowCount()))
        from PySide6.QtCore import Qt
        self.assertEqual([cs.mo_hinh.headerData(c, Qt.Orientation.Horizontal) for c in range(cs.mo_hinh.columnCount())],
                         ['STT', 'Họ và tên', 'Địa chỉ', 'Số thửa', 'DT thu hồi (m²)', 'Trạng thái'])     # danh sách gọn (0.9.12)
        cs.mo_trang(3)                                                              # tiền từng mục: Bảng tổng hợp
        self.assertEqual(cs.trang.currentIndex(), 1)
        self.assertEqual(cs.bang_tong_hop.tien.bang.rowCount(), cs.mo_hinh.rowCount())
        cs.mo_trang(4)
        self.assertEqual(cs.trang.currentIndex(), 2)
        self.assertTrue(cs.lenh['Theo dõi tiến độ'].isChecked())
        cs.close()

    def test_loai_dat_phim_va_co_giao_dien(self):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtWidgets import QApplication
        from pabt import giao_dien, loai_dat
        from pabt.man_hinh import CuaSoLapPA
        ma = [m for m, _ in loai_dat.ds_chon(self.con)]
        for x in ('ONT', 'ODT', 'CLN', 'LUC', 'HNK', 'BHK', 'RSX', 'NTS', 'TMD', 'SKC', 'BCS', 'DGT', 'TON', 'NTD'):
            self.assertIn(x, ma)
        self.assertEqual(len(ma), len(set(ma)))
        self.assertEqual({m for m, _ in loai_dat.ds_co_gia(self.con)},
                         {r[0].upper() for r in self.con.execute('SELECT ma FROM dm_loaidat')})
        w = CuaSoLapPA(self.con, 1)
        b = w.bang[2].bang
        self.assertGreaterEqual(b.verticalHeader().minimumSectionSize(), 34)
        c_sl = [k for k, _, _ in w.bang[2].cot].index('so_luong')
        b.setCurrentCell(0, c_sl)
        giao_dien.o_ke(b)                                                   # Enter sau khi sửa: sang ô sửa được kế tiếp
        self.assertEqual(b.currentColumn(), [k for k, _, _ in w.bang[2].cot].index('don_gia'))
        b.setCurrentCell(0, 0)                                              # ô Mã (tự điền): Enter sang ô kế, không mở sửa
        QApplication.sendEvent(b, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
        self.assertEqual(b.currentColumn(), 1)
        w.close()
        # cỡ giao diện: phóng to / thu nhỏ có giới hạn, về 100%
        app = QApplication.instance()
        co = app.font().pointSizeF()
        try:
            self.assertEqual(giao_dien.dat_ty_le(1.2, luu=False), 1.2)
            self.assertAlmostEqual(app.font().pointSizeF(), 9.5 * 1.2, places=2)
            self.assertIn('16px', giao_dien._co_gian('font-size: 13px;', 1.2))
            self.assertEqual(giao_dien.dat_ty_le(3, luu=False), 1.6)
            self.assertEqual(giao_dien.dat_ty_le(0.1, luu=False), 0.8)
        finally:
            giao_dien.dat_ty_le(1.0, luu=False)
            f = app.font()
            f.setPointSizeF(co)
            app.setFont(f)

    def test_cong_thuc_hien_lai_va_dt_xay_dung(self):
        from PySide6.QtCore import Qt
        from pabt import cay_trong as ct
        from pabt.lap_pa import BoSoan
        from pabt.man_hinh import CuaSoLapPA
        self.assertEqual(ct.nhom_xay_dung('Nhà 01 tầng - Kết cấu loại 4 (Nhà chính)')[0], 1)
        self.assertEqual(ct.nhom_xay_dung('Nhà vệ sinh xây gạch')[0], 4)
        self.assertEqual(ct.nhom_xay_dung('Mái che, mái hiên.')[0], 3)
        self.assertEqual(ct.nhom_xay_dung('Nền ciment đá dăm dày 10 cm')[0], 5)
        self.assertIsNone(ct.nhom_xay_dung('Tường rào móng đá chẻ/gạch'))
        self.assertIsNone(ct.nhom_xay_dung('Gác lửng nhà chính'))
        # công thức số lượng: lưu vào file, sửa ô hiện lại công thức
        bo = BoSoan(self.con, 1)
        bo.sua_khoan(2, 0, 'so_luong', '=4,2*5,7')
        self.assertEqual(bo.pa.khoan[2][0].cong_thuc, '=4,2*5,7')
        bo.sua_dat(0, 'dien_tich', '200,5+15')
        self.assertEqual(bo.pa.dat[0].cong_thuc, '=200,5+15')
        bo.luu()
        bo2 = BoSoan(self.con, 1)
        self.assertEqual((bo2.pa.khoan[2][0].cong_thuc, bo2.pa.khoan[2][0].so_luong), ('=4,2*5,7', D('23.9')))
        bo2.sua_khoan(2, 0, 'so_luong', '30')                              # gõ số thường: bỏ công thức
        self.assertEqual(bo2.pa.khoan[2][0].cong_thuc, '')
        w = CuaSoLapPA(self.con, 1)
        b2 = w.bang[2]
        c = [k for k, _, _ in b2.cot].index('so_luong')
        self.assertEqual(b2.bang.item(0, c).data(Qt.ItemDataRole.UserRole), '=4,2*5,7')
        b2.bang.setCurrentCell(0, c)
        self.assertIn('=4,2*5,7 = 23,9', w.lb_tb.text())
        # tổng diện tích xây dựng so với diện tích thu hồi
        dlg = w.kiem_tra_dt_xay_dung(cho=False)
        kq = dlg.kq
        thu_hoi = sum(D(t['dt_thu_hoi']) for t in w.bo.bc.thua.values() if t['ma_ho'] == 1)
        self.assertEqual(kq['thu_hoi'], thu_hoi)
        self.assertEqual(kq['tong'], sum(x['dien_tich'] for x in kq['dong']))
        self.assertEqual([x['nhom_so'] for x in kq['dong']], sorted(x['nhom_so'] for x in kq['dong']))
        self.assertTrue(any('rào' in x['ten'].lower() for x in kq['loai_tru']))
        dlg.bang.item(0, 0).setCheckState(Qt.CheckState.Unchecked)            # bỏ một dòng: tổng giảm
        self.assertEqual(dlg.kq['tong'], kq['tong'] - kq['dong'][0]['dien_tich'])
        w.close()

    def test_mat_do_va_thua(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, 1)
        dlg = w.tinh_mat_do(0, cho=False)
        dlg.o_dt.setText('1000')
        dlg.o_so.setText('300')
        dlg.o_md.setText('200')
        txt = dlg.lb.text()
        self.assertIn('VƯỢT mật độ 280 cây', txt)
        self.assertIn('Đảm bảo mật độ 20 cây', txt)
        self.assertIn('15.000', txt)                                     # 300 cây cần 15.000 m²
        # mục 1: danh sách thửa / vị trí theo dòng cho ô xổ xuống
        self.assertTrue(w.ds_thua_dong(0))
        self.assertTrue(w.ds_vi_tri_dong(0))
        nhan, gt = w.ds_vi_tri_dong(0)[0]
        w.doi_vi_tri_dong(0, gt)
        self.assertEqual(w.bo.pa.dat[0].gia_bang_gia, D(w.bo.ds_vi_tri_nq28(0)[0][2]))
        w.close()

    def test_them_ho_mo_the_ho_so(self):
        from pabt import app as ud
        cs = ud.CuaSoChinh()
        cs.mo(str(self.p))
        so = cs.mo_hinh.rowCount()
        w = cs.mo_ho_so(moi=True, cho=False, ho_ten='Nguyễn Văn Mới')
        self.assertEqual(w.tab.currentIndex(), 0)
        self.assertEqual(cs.mo_hinh.rowCount(), so + 1)
        w.ho_so.them_dong(dict(so_to='9', so_thua='99', loai_dat='CLN', dt_thu_hoi='=10*12,5'))
        self.assertTrue(w.sang_the(1))
        self.assertEqual(len(w.bo.thua_cua_ho()), 1)
        self.assertEqual(w.bo.thua_cua_ho()[0][2], 125)
        self.assertIsNotNone(w.them_thua(w.bang[1].cb_thua.currentData()))
        w.close()
        cs.close()


if __name__ == '__main__':
    unittest.main()
