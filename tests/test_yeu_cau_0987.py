"""Kiểm thử 0.9.87 (người dùng 14/10/2026 + master_prompt_pabt_0987): cấu hình nghiệp vụ / SLA, bỏ chữ "xôi đỗ", bản vẽ CAD + bản đồ
thửa, OCR giấy tờ, CSDL v16, bản in (nhãn Tổ chức, gộp ghi chú đất, tiêu đề mục II, đệm mẫu RAM), PDF dự phòng bằng Qt, chẩn đoán /
sửa file / gói ẩn danh, phiếu kiểm đếm thực địa, kiểm tra tĩnh (tao_ban_do_ma). Dữ liệu giả lập."""
from __future__ import annotations
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

import openpyxl

from pabt import csdl, dia_phuong, in_an
from tests.test_in_vua_chu import CoSo

GOC = Path(__file__).resolve().parent.parent
try:
    import ezdxf
except ImportError:                                     # máy chưa cài (requirements): bỏ qua bài đọc bản vẽ
    ezdxf = None


def _app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from pabt import giao_dien
    app = QApplication.instance() or QApplication([])
    giao_dien.ap_dung(app)
    return app


class CoSoMay(CoSo):
    """Dự án giả lập (CoSo: 3 hộ) + thư mục máy riêng (không đụng %APPDATA%\\PABT)."""

    def setUp(self):
        super().setUp()
        self.may = self.td / 'may'
        self.may.mkdir()
        self._env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.may)})
        self._env.start()
        dia_phuong.nap_lai()

    def tearDown(self):
        self._env.stop()
        dia_phuong.nap_lai()
        super().tearDown()


# ---------------------------------------------------------------- yêu cầu 14/10 (trước master prompt)
class TestXoiDo(unittest.TestCase):
    def test_khong_con_chu_xoi_do(self):
        from pabt.lap_pa import bo_dau
        for p in list((GOC / 'pabt').glob('*.py')) + [GOC / 'HUONG_DAN.md']:
            s = bo_dau(p.read_text(encoding='utf-8'))
            for tu in ('xoi do', 'xoi dau'):
                self.assertNotIn(tu, s, f'{p.name} còn chữ "{tu}"')


class TestCauHinhNghiepVu(CoSoMay):
    def test_sla_theo_ho_so_va_luu_khoi_phuc(self):
        from pabt import quy_trinh_qd18 as qt
        self.assertEqual(qt.sla_buoc(6), f'{dia_phuong.lay("thoi_han.niem_yet.so_ngay")} ngày')
        self.assertIn('NN', qt.sla_buoc(13))
        self.assertEqual(qt.sla_buoc(1), '')
        hs = dia_phuong.mac_dinh()
        hs['thoi_han']['niem_yet']['so_ngay'] = 15
        f = dia_phuong.luu_cau_hinh(hs)
        self.assertTrue(f and Path(f).is_file())
        dia_phuong.nap_lai()
        self.assertEqual(qt.sla_buoc(6), '15 ngày')
        from pabt import du_thao
        self.assertEqual(du_thao.SO_NGAY_NIEM_YET, 15)      # module đăng ký nhận giá trị mới
        dia_phuong.khoi_phuc_mac_dinh()
        dia_phuong.nap_lai()
        self.assertNotEqual(qt.sla_buoc(6), '15 ngày')

    def test_hop_cau_hinh(self):
        _app()
        from pabt.man_hinh_cau_hinh import HopCauHinhNghiepVu
        h = HopCauHinhNghiepVu()
        h.im_lang = True
        h.o_ngay['van_dong'].setValue(12)
        self.assertEqual(h.gia_tri()['thoi_han']['van_dong']['so_ngay'], 12)
        self.assertTrue(h.luu())
        self.assertEqual(dia_phuong.lay('thoi_han.van_dong.so_ngay'), 12)


@unittest.skipIf(ezdxf is None, 'chưa cài ezdxf')
class TestBanVeCad(CoSoMay):
    def _dxf(self, ten='To_15.dxf'):
        doc = ezdxf.new()
        msp = doc.modelspace()
        so = [r['so_thua'] for r in self.con.execute('SELECT so_thua FROM thua ORDER BY ma_thua')]
        for i, s in enumerate(so):
            x = i * 30
            msp.add_lwpolyline([(x, 0), (x + 20, 0), (x + 20, 10), (x, 10)], close=True, dxfattribs={'layer': 'RANH THUA'})
            msp.add_mtext(f'{s}\\P200,0\\PONT', dxfattribs={'layer': 'NHAN', 'insert': (x + 5, 5)})    # nhãn nhiều dòng
        msp.add_lwpolyline([(10, -5), (200, -5), (200, 20), (10, 20)], close=True, dxfattribs={'layer': 'RANH THU HOI'})
        f = self.td / ten
        doc.saveas(f)
        return f

    def test_hinh_hoc_va_nhan(self):
        from pabt import ban_do_cad as b
        vuong = [(0, 0), (10, 0), (10, 10), (0, 10)]
        self.assertEqual(b.dien_tich(vuong), 100.0)
        self.assertAlmostEqual(b.dien_tich_giao(vuong, [(5, -1), (20, -1), (20, 20), (5, 20)]), 50.0, places=6)
        self.assertTrue(b.chua_diem(vuong, 5, 5))
        self.assertEqual(b.boc_nhan('12\n245,6\nONT', {'ONT', 'CLN'}), ('12', Decimal('245.6'), 'ONT'))

    def test_phan_tich_luu_va_ban_do(self):
        from pabt import ban_do_cad as b
        with self.con:
            self.con.execute("UPDATE thua SET so_to = '15', so_thua = CAST(100 + ma_thua AS TEXT)")
        kq = b.phan_tich(self._dxf(), 'RANH THUA', 'RANH THU HOI')
        self.assertEqual(kq.so_to, '15')
        self.assertEqual(len(kq.thua), self.con.execute('SELECT COUNT(*) FROM thua').fetchone()[0])
        t0 = kq.thua[0]
        self.assertEqual(float(t0.dt_hinh), 200.0)
        self.assertAlmostEqual(float(t0.dt_trong_ranh), 100.0, places=3)
        r = b.luu(self.con, kq, cap_nhat_dt={('15', t0.so_thua)})
        self.assertEqual((r['luu'], r['khop'], r['cap_nhat']), (len(kq.thua), len(kq.thua), 1))
        ds = b.doc_ban_do(self.con, '15')
        self.assertEqual(len(ds), len(kq.thua))
        self.assertTrue(all(x.ma_ho is not None for x in ds))
        self.assertEqual(b.ds_to(self.con), ['15'])

    def test_khung_ban_do_bam_thua(self):
        _app()
        from pabt import ban_do_cad as b
        from pabt.man_hinh_ban_do import HopBanDo
        with self.con:
            self.con.execute("UPDATE thua SET so_to = '15', so_thua = CAST(100 + ma_thua AS TEXT)")
        b.luu(self.con, b.phan_tich(self._dxf(), 'RANH THUA', 'RANH THU HOI'))
        mo = []
        h = HopBanDo(self.con, mo_ho=mo.append)
        self.assertGreater(len(h.view.scene().items()), 0)
        so = self.con.execute('SELECT so_thua FROM thua ORDER BY ma_thua').fetchone()[0]
        self.assertTrue(h.view.tim(so))
        h.close()


class TestOcrBocTach(unittest.TestCase):
    CHU = ('GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN GẮN LIỀN VỚI ĐẤT\n'
           'Ông: NGUYỄN VĂN MẪU, năm sinh 1970\nCCCD số: 075070000123\nĐịa chỉ thường trú: Ấp 1, xã Mẫu\n'
           'Thửa đất số: 45; Tờ bản đồ số: 12\nDiện tích: 250,5 m2\nMục đích sử dụng: Đất ở tại nông thôn\n')

    def test_boc_tach_gcn(self):
        from pabt import ocr_ho_so
        kq = ocr_ho_so.boc_tach(self.CHU)
        self.assertEqual(kq.loai, 'gcn')
        self.assertEqual(kq.ho_ten, 'Nguyễn Văn Mẫu')
        self.assertEqual(kq.so_cccd, '075070000123')
        self.assertEqual(len(kq.thua), 1)
        t = kq.thua[0]
        self.assertEqual((t['so_to'], t['so_thua'], t['loai_dat']), ('12', '45', 'ONT'))
        self.assertEqual(t['dt_thu_hoi'], Decimal('250.5'))

    def test_dien_vao_khai_toan(self):
        _app()
        from pabt import ocr_ho_so
        from pabt.man_hinh_du_toan import KhungDuToan
        from pabt.man_hinh_ocr import HopQuetGiayTo
        k = KhungDuToan()
        h = HopQuetGiayTo(k, 'du_toan')
        h.im_lang = True
        h.hien(ocr_ho_so.boc_tach(self.CHU))
        self.assertEqual(h.dien_ho_thua(), 1)
        d = [x for x in k.dt.dong if x.muc == 1]
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0].khoi_luong, Decimal('250.5'))


# ---------------------------------------------------------------- CSDL v16
class TestCsdlV16(CoSoMay):
    def test_phien_ban_va_bang_phu(self):
        self.assertEqual(csdl.PHIEN_BAN_CSDL, 16)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], 16)
        bang = {r[0] for r in self.con.execute("SELECT name FROM sqlite_master")}
        for t in ('nhat_ky_van_dong', 'audit_logs', 'thua_ban_do', 'anh_hien_trang', 'ix_ctdat_thua', 'audit_logs_khong_sua',
                  'audit_logs_khong_xoa'):
            self.assertIn(t, bang)

    def test_nang_cap_tu_v15(self):
        with self.con:
            for t in ('nhat_ky_van_dong', 'thua_ban_do', 'anh_hien_trang'):
                self.con.execute(f'DROP TABLE {t}')
            self.con.execute('DROP TRIGGER audit_logs_khong_sua')
            self.con.execute('DROP TRIGGER audit_logs_khong_xoa')
            self.con.execute('DROP TABLE audit_logs')
            self.con.execute('DROP INDEX IF EXISTS ix_ctdat_thua')
            self.con.execute('PRAGMA user_version = 15')
        self.con.close()
        self.con = csdl.mo(self.p)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], 16)
        bang = {r[0] for r in self.con.execute("SELECT name FROM sqlite_master")}
        self.assertTrue({'nhat_ky_van_dong', 'audit_logs', 'thua_ban_do', 'anh_hien_trang', 'ix_ctdat_thua'} <= bang)
        with self.con:
            self.con.execute("INSERT INTO audit_logs (luc, hanh_dong, bang) VALUES ('2026-10-14T08:00:00', 'sua', 'ho')")
        with self.assertRaises(sqlite3.DatabaseError):                 # trigger chặn xóa có trong file nâng cấp
            with self.con:
                self.con.execute('DELETE FROM audit_logs')

    def test_bo_don_gia_dong_goi_khong_bi_ghi(self):
        import hashlib
        from pabt import don_gia
        f = don_gia.file_goc()
        truoc = hashlib.sha256(f.read_bytes()).hexdigest()
        con = csdl.mo(f)
        try:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], 16)
            self.assertIsNone(con.execute("SELECT 1 FROM sqlite_master WHERE name = 'audit_logs'").fetchone())
        finally:
            con.close()
        self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), truoc)

    def test_file_moi_hon_bao_loi(self):
        with self.con:
            self.con.execute('PRAGMA user_version = 99')
        self.con.close()
        with self.assertRaisesRegex(RuntimeError, 'mới hơn'):
            csdl.mo(self.p)
        c = sqlite3.connect(str(self.p))
        c.execute('PRAGMA user_version = 16')
        c.commit()
        c.close()
        self.con = csdl.mo(self.p)


# ---------------------------------------------------------------- bản in
class TestBanIn(CoSoMay):
    def _ws(self, ma_ho):
        f = in_an.lap_chi_tiet(self.con, ma_ho, self.td / f'ct_{ma_ho}.xlsx')
        return openpyxl.load_workbook(f).worksheets[0]

    def test_la_to_chuc(self):
        from pabt.ho_so import la_to_chuc
        for ten in ('Công ty TNHH MTV Mẫu', 'UBND xã Mẫu', 'Ủy ban nhân dân xã Mẫu', 'Ban quản lý dự án khu vực', 'Hợp tác xã Mẫu',
                    'Trung tâm Phát triển quỹ đất', 'Nhà thờ Giáo xứ Mẫu', 'Chùa Mẫu', 'Trường tiểu học Mẫu', 'Doanh nghiệp tư nhân A'):
            self.assertTrue(la_to_chuc(ten), ten)
        for ten in ('Nguyễn Văn Mẫu', 'Trương Văn Mẫu', 'Đinh Thị Mẫu', 'Ông Trung Tâm', 'Bà Chu Thị Mẫu', ''):
            self.assertFalse(la_to_chuc(ten), ten)
        self.assertTrue(la_to_chuc('Nguyễn Văn A', 'to_chuc'))

    def test_nhan_to_chuc_va_tieu_de_muc_ii(self):
        ma = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        chu = [str(o.value) for row in self._ws(ma).iter_rows(max_row=20) for o in row if isinstance(o.value, str)]
        self.assertIn(in_an.TIEU_DE_MUC_II, chu)
        self.assertIn('Họ và tên:', chu)
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Công ty TNHH Mẫu' WHERE ma_ho = ?", (ma,))
        chu = [str(o.value) for row in self._ws(ma).iter_rows(max_row=20) for o in row if isinstance(o.value, str)]
        self.assertIn('Tổ chức:', chu)
        self.assertNotIn('Họ và tên:', chu)

    def test_gop_ghi_chu_dat(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        dong = [['H', []], ['I', []], ['I', []], ['I', []], ['I', []], ['H', []], ['I', []]]
        for r, gc in zip(range(11, 18), (None, 'Đất đủ điều kiện', 'Đất đủ điều kiện', 'Hành lang', 'Hành lang', 'Mục 2', 'Mục 2')):
            ws.cell(r, 8, gc)
        self.assertEqual(in_an.gop_ghi_chu_dat(ws, dong, 11, 8), [(12, 13), (14, 15)])
        vung = {str(m) for m in ws.merged_cells.ranges}
        self.assertEqual(vung, {'H12:H13', 'H14:H15'})            # mục 2 (sau dòng H) không gộp
        self.assertEqual(ws.cell(12, 8).alignment.vertical, 'center')

    def test_ghi_chu_gop_khong_nhan_chieu_cao(self):
        # ghi chú đất trùng nhau gộp một ô: khối đủ cao cho chữ ghi chú, nhưng KHÔNG mỗi dòng cao bằng cả ghi chú (trước đây 3 x 299 pt)
        from tests.test_toc_do import _du_an
        (self.td / 'gc').mkdir()
        con = csdl.mo(_du_an(self.td / 'gc', 3))                         # hộ 3 có 3 thửa, mỗi thửa một dòng đất
        try:
            gc = ' '.join(['Đất nông nghiệp đủ điều kiện bồi thường theo Điều 95 Luật Đất đai năm 2024'] * 2)
            with con:
                con.execute('UPDATE ct_dat SET ghi_chu = ? WHERE ma_ho = 3', (gc,))
            ws = openpyxl.load_workbook(in_an.lap_chi_tiet(con, 3, self.td / 'gc.xlsx')).active
        finally:
            con.close()
        vung = next(m for m in ws.merged_cells.ranges if m.min_col == m.max_col == 8 and m.max_row > m.min_row)
        cao = [ws.row_dimensions[r].height for r in range(vung.min_row, vung.max_row + 1)]
        can = in_an.cao_dong_bang(in_an.so_dong_o(gc, in_an._px_cot(ws, 9)[7] * 0.75 - 6))
        self.assertGreaterEqual(sum(cao), can - 0.01)
        self.assertLess(min(cao), can)

    def test_dem_mau_trong_ram(self):
        in_an.xoa_bo_nho_mau()
        mau = in_an.file_mau(None, in_an.TEN_CT)
        a = in_an.mo_mau(mau)
        a.worksheets[0]['A1'] = 'đã sửa'
        a.worksheets[0].row_dimensions[40].height = 30
        b = in_an.mo_mau(mau)
        self.assertNotEqual(b.worksheets[0]['A1'].value, 'đã sửa')    # mỗi lần một workbook độc lập
        b.worksheets[0].row_dimensions[50].height = 31
        self.assertEqual(len(in_an._BO_NHO_MAU), 1)
        in_an.xoa_bo_nho_mau()
        self.assertEqual(len(in_an._BO_NHO_MAU), 0)


class TestPdfDuPhong(CoSoMay):
    def test_dinh_dang_so(self):
        from pabt.pdf_du_phong import _so_vn
        for v, f, kq in ((50, '[=0]0;#,##0.0#', '50,0'), (0, '[=0]0;#,##0.0#', '0'), (3000000, '[=0]0;[<10]0.0##;#,##0', '3.000.000'),
                         (1, '0%', '100%'), (-1234.5, '#,##0.00', '-1.234,50'), (1.25, 'General', '1,25')):
            self.assertEqual(_so_vn(v, f), kq)

    def test_chi_tiet_va_tong_hop(self):
        _app()
        from pabt import pdf_du_phong
        try:
            from PySide6.QtPdf import QPdfDocument
        except ImportError:                                         # Qt5 (bản Windows 7): không có QtPdf để đọc lại
            QPdfDocument = None
        ma = self.con.execute('SELECT ma_ho FROM ho LIMIT 1').fetchone()[0]
        for x in (in_an.lap_chi_tiet(self.con, ma, self.td / 'ct.xlsx'), in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')):
            h, trang = pdf_du_phong.html_tu_xlsx(x)
            self.assertIn('<table', h)
            self.assertGreater(trang['he_so'], 0)
            pdf = pdf_du_phong.xuat_pdf_du_phong_qt(x, x.with_suffix('.pdf'))
            self.assertTrue(pdf.read_bytes().startswith(b'%PDF'))
            if QPdfDocument is None:
                continue
            d = QPdfDocument()
            d.load(str(pdf))
            self.assertGreaterEqual(d.pageCount(), 1)
            d.close()

    def test_khung_xem_truoc_dung_ban_gan_dung(self):
        _app()
        from pabt.xem_truoc_tai_lieu import KhungXemTruocTaiLieu
        k = KhungXemTruocTaiLieu()
        ma = self.con.execute('SELECT ma_ho FROM ho LIMIT 1').fetchone()[0]
        k.yeu_cau(('t', ma), lambda d: in_an.lap_chi_tiet(self.con, ma, Path(d) / 'ct.xlsx'), 'thử', ngay=True)
        self.assertTrue(k.cho_xong(30))
        if k.doc is not None:                                       # Qt6 có QtPdf
            self.assertTrue(k.gan_dung)
            self.assertFalse(k.lb_gan_dung.isHidden())
            self.assertGreaterEqual(k.so_trang(), 1)
        k.don_dep()


# ---------------------------------------------------------------- chẩn đoán, sửa file, gói ẩn danh
class TestChuaBenh(CoSoMay):
    def test_kiem_tra_va_sua(self):
        from pabt import chua_benh_csdl as cb, khoa
        self.so_ho = self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        kt = cb.kiem_tra_tep_pabt(self.p)
        self.assertTrue(kt['hop_le'])
        self.assertEqual(kt['phien_ban'], 16)
        self.con.close()
        k = khoa.KhoaFile(self.p)
        k.p.write_text(json.dumps(dict(may='MAY_KHAC', nguoi='x', pid=1, mo_luc=1, cap_nhat=__import__('time').time())),
                       encoding='utf-8')
        with self.assertRaises(cb.LoiSuaTep):                       # máy khác đang sửa: không gỡ khóa
            cb.sua_tep_pabt(self.p)
        k.p.write_text(json.dumps(dict(may='MAY_KHAC', nguoi='x', pid=1, mo_luc=1, cap_nhat=1)), encoding='utf-8')   # khóa hết hạn
        kq = cb.sua_tep_pabt(self.p, self.td / 'sl')
        self.assertTrue(kq['thanh_cong'])
        self.assertFalse(k.p.exists())
        self.assertTrue(Path(kq['ban_sao_luu']).is_file())
        self.con = csdl.mo(self.p)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], self.so_ho)

    def test_cuu_du_lieu_trang_hong(self):
        from pabt import chua_benh_csdl as cb
        self.con.close()
        p = self.td / 'hong.pabt'
        p.write_bytes(self.p.read_bytes())
        n = self.p.stat().st_size
        with open(p, 'r+b') as f:                                    # ghi rác vào giữa file (trang dữ liệu)
            f.seek(n // 2)
            f.write(b'\xff' * 2048)
        kt = cb.kiem_tra_tep_pabt(p)
        if kt['hop_le']:
            self.skipTest('rác rơi vào trang trống - SQLite không thấy lỗi')
        kq = cb.sua_tep_pabt(p, self.td / 'sl')
        self.assertTrue(kq['thanh_cong'], kq)
        self.con = csdl.mo(self.p)

    def test_an_danh_va_goi(self):
        from pabt import chua_benh_csdl as cb
        with self.con:
            self.con.execute("UPDATE ho SET so_cccd = '075070000123', dien_thoai = '0909000000'")
            self.con.execute("UPDATE thua SET nguon_goc = 'Nhận chuyển nhượng của ông Nguyễn Văn Bán năm 2001'")
            self.con.execute("UPDATE du_an SET nguoi_ky = 'Người Ký Thật'")
        tong = [r[0] for r in self.con.execute('SELECT dt_thu_hoi FROM thua ORDER BY ma_thua')]
        (self.may / 'loi.log').write_text('Traceback giả lập', encoding='utf-8')
        z = cb.dong_goi_chan_doan(self.td / 'goi.zip', self.p, loi_text='lỗi thử')
        with zipfile.ZipFile(z) as f:
            ten = set(f.namelist())
            self.assertTrue({'thong_tin_may.json', 'loi_vua_gap.txt', 'loi.log', 'du_an_an_danh.pabt'} <= ten)
            tt = json.loads(f.read('thong_tin_may.json'))
            self.assertIn('kiem_tra_moi_truong', tt)
            f.extract('du_an_an_danh.pabt', self.td / 'ra')
        c = sqlite3.connect(str(self.td / 'ra' / 'du_an_an_danh.pabt'))
        try:
            for ten_ho, cccd, dt in c.execute('SELECT ho_ten, so_cccd, dien_thoai FROM ho'):
                self.assertTrue(ten_ho.startswith('Hộ kiểm thử'))
                self.assertEqual((cccd, dt), ('', ''))
            ng = [r[0] for r in c.execute('SELECT nguon_goc FROM thua')]
            self.assertTrue(all('Bán' not in x and len(x) > 10 for x in ng))
            self.assertEqual([r[0] for r in c.execute('SELECT dt_thu_hoi FROM thua ORDER BY ma_thua')], tong)   # số liệu giữ
            self.assertEqual(c.execute('SELECT nguoi_ky FROM du_an').fetchone()[0], '')
            self.assertEqual(c.execute('SELECT COUNT(*) FROM nhat_ky').fetchone()[0], 0)
        finally:
            c.close()
        # file gốc không đổi
        self.assertEqual(self.con.execute('SELECT so_cccd FROM ho LIMIT 1').fetchone()[0], '075070000123')

    def test_hop_chan_doan(self):
        _app()
        from pabt.man_hinh_chan_doan import HopChanDoanHeThong
        dong = []
        h = HopChanDoanHeThong(None, self.p, dong_du_an=lambda: dong.append(1) or self.con.close(), mo_lai=lambda f: dong.append(2),
                               im_lang=True)
        self.assertGreaterEqual(h.bang.rowCount(), 5)
        self.assertIn('File tốt', h.lb_tep.text())
        kq = h.sua_file()
        self.assertTrue(kq['thanh_cong'])
        self.assertEqual(dong, [1, 2])                              # đóng dự án trước khi sửa, mở lại sau
        self.con = csdl.mo(self.p)
        z = h.xuat_goi(self.td / 'g.zip')
        self.assertTrue(Path(z).is_file())

    def test_hop_bao_loi_co_nut_goi(self):
        _app()
        from pabt import giao_dien
        from pabt.man_hinh_chan_doan import NUT_GOI
        goi = []
        d = giao_dien.hop_ket_qua(None, 'lỗi', ['dòng'], hien=False, nut_them=[(NUT_GOI, goi.append)])
        d.nut_them[NUT_GOI].click()
        self.assertEqual(goi, [d])


# ---------------------------------------------------------------- phiếu kiểm đếm thực địa
class TestPhieuKiemDem(CoSoMay):
    def test_xuat_html(self):
        from pabt import phieu_kiem_dem as pk
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Tên </script><b>' WHERE thu_tu = 1")
        f = pk.xuat_phieu_kiem_dem_html(self.con, self.td / 'phieu.html')
        s = f.read_text(encoding='utf-8')
        self.assertIn('PHIẾU KIỂM ĐẾM', s)
        self.assertEqual(s.count('</script>'), 1)                    # tên hộ có "</script>" không đóng thẻ sớm
        du = pk.du_lieu_phieu(self.con)
        self.assertEqual(len(du['ho']), self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0])
        self.assertTrue(du['goi_y'][3])

    def test_nhap_ket_qua_vao_phuong_an(self):
        from pabt import phieu_kiem_dem as pk
        from pabt.lap_pa import BoSoan
        ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        cay = self.con.execute("SELECT ten, dvt FROM dm_taisan WHERE nhom = 3 AND ten NOT LIKE '%(%' LIMIT 1").fetchone()
        f = self.td / 'kq.json'
        f.write_text(json.dumps(dict(ket_qua={str(ma[0]): [dict(muc=3, ten=cay['ten'], dvt=cay['dvt'], so_luong='4x5'),
                                                           dict(muc=2, ten='Chuồng gà tự làm', dvt='m²', so_luong='6')],
                                              '999999': [dict(muc=2, ten='x', so_luong='1')]}), ensure_ascii=False),
                     encoding='utf-8')
        kq = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual((kq['so_ho'], kq['so_dong']), (1, 2))
        self.assertTrue(any('999999' in x for x in kq['loi']))
        bo = BoSoan(self.con, ma[0])
        d3 = next(d for d in bo.pa.khoan[3] if d.ten == cay['ten'])
        self.assertEqual(d3.so_luong, Decimal('20'))
        self.assertIn('Chuồng gà tự làm', [d.ten for d in bo.pa.khoan[2]])

    def test_gan_anh(self):
        from pabt import phieu_kiem_dem as pk
        r = self.con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu').fetchall()
        with self.con:
            self.con.execute("UPDATE ho SET so_cccd = '075070000123' WHERE ma_ho = ?", (r[0]['ma_ho'],))
        tm = self.td / 'anh'
        (tm / 'con').mkdir(parents=True)
        (tm / '075070000123_nha.jpg').write_bytes(b'1')
        (tm / 'con' / f'HO{r[1]["thu_tu"]:03d}_cay.png').write_bytes(b'2')
        (tm / 'khong_ro.jpg').write_bytes(b'3')
        (tm / 'ghi_chu.txt').write_text('x')
        kq = pk.gan_anh_hien_trang(self.con, tm)
        self.assertEqual((kq['so_anh'], kq['da_gan']), (3, 2))
        self.assertEqual(len(kq['chua_khop']), 1)
        self.assertEqual(pk.so_anh_theo_ho(self.con), {r[0]['ma_ho']: 1, r[1]['ma_ho']: 1})
        self.assertEqual(pk.gan_anh_hien_trang(self.con, tm)['da_gan'], 0)      # gắn lại không trùng

    def test_hop_kiem_dem(self):
        _app()
        from pabt.man_hinh_kiem_dem import HopKiemDem
        h = HopKiemDem(None, self.con, self.p, im_lang=True)
        self.assertEqual(h.bang.rowCount(), self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0])
        self.assertTrue(Path(h.xuat(self.td / 'p.html')).is_file())


# ---------------------------------------------------------------- lệnh, kiểm tra tĩnh
class TestLenhVaKiemTraTinh(unittest.TestCase):
    def test_lenh_moi_dung_cho(self):
        _app()
        from pabt.app import LENH_CAN_DU_AN, CuaSoChinh
        w = CuaSoChinh()
        try:
            tg = [a.text() for a in w.menu_tren['Trợ giúp'].actions()]
            cc = [a.text() for a in w.menu_tren['Công cụ'].actions()]
            self.assertIn('Chẩn đoán & sửa lỗi hệ thống…', tg)
            self.assertIn('Phiếu kiểm đếm thực địa…', cc)
            # chưa mở dự án: VẪN bấm được (mục mờ bấm không phản ứng - người dùng tưởng hỏng), bấm thì báo mở dự án trước
            for t in ('Phiếu kiểm đếm thực địa…', 'Nhập bản vẽ CAD (.dxf)…', 'Chẩn đoán & sửa lỗi hệ thống…'):
                self.assertNotIn(t, LENH_CAN_DU_AN)
                self.assertTrue(w.lenh[t].isEnabled(), t)
            from unittest import mock as _m
            with _m.patch('pabt.app.QMessageBox.information') as bao:
                self.assertIsNone(w.phieu_kiem_dem(cho=False))
                self.assertFalse(w.nhap_ban_ve_cad(cho=False))
            self.assertEqual(bao.call_count, 2)
            d = w.chan_doan_he_thong(cho=False)
            self.assertIsNone(d.file_pabt)
        finally:
            w.close()

    def test_tao_ban_do_ma_khong_canh_bao(self):
        import tao_ban_do_ma
        kq = tao_ban_do_ma.kiem_tra()
        self.assertEqual(kq['canh_bao'], [])
        self.assertIn('to_chuc', kq['bien_dong'])
        self.assertIn('TEN', kq['bien_dong']['to_chuc'])

    def test_thu_tu_nhom_menu_trai_va_lenh_khi_chua_mo_du_an(self):
        """Người dùng 15/10/2026: Đơn giá & bảng giá xuống nhóm 6; đóng sẵn 1, 5, 6. Chưa mở dự án: Đơn giá bồi thường, Bảng giá đất
        vẫn bật (liên kết màn hình chào), Đơn giá đặc biệt và nhóm 3, 4, 5 tắt."""
        _app()
        from pabt import app as ud, giao_dien
        self.assertEqual(ud.NHOM_DONG_MAC_DINH, ('1. Khái toán & dự toán', '5. Phê duyệt & bàn giao', '6. Đơn giá & bảng giá'))
        self.assertEqual(giao_dien.TEN_NHOM_CU['3. Đơn giá & bảng giá'], '6. Đơn giá & bảng giá')
        self.assertEqual(giao_dien.TEN_NHOM_CU['6. Phê duyệt & bàn giao'], '5. Phê duyệt & bàn giao')
        w = ud.CuaSoChinh(menu_trai=True)
        try:
            self.assertEqual(list(w.khung_menu.tieu_de_nhom)[-1], '6. Đơn giá & bảng giá')
            for t in ('Bộ đơn giá…', 'Bảng giá đất NQ 28…', 'Dự toán & khái toán', 'Thông tin dự án…'):
                self.assertTrue(w.lenh[t].isEnabled(), t)
            for t in ('Đơn giá riêng dự án…', 'Lập phương án hộ…', 'Đợt trình…', 'Quyết định phê duyệt'):
                self.assertFalse(w.lenh[t].isEnabled(), t)
        finally:
            w.close()

    def test_hop_moi_vua_man_hinh_nho(self):
        _app()
        from pabt.man_hinh_chan_doan import HopChanDoanHeThong
        h = HopChanDoanHeThong(None, None, im_lang=True)
        for w in (h,):
            sz = w.minimumSizeHint()
            self.assertLessEqual(sz.width(), 1024, type(w).__name__)
            self.assertLessEqual(sz.height(), 680, type(w).__name__)
        with tempfile.TemporaryDirectory() as td:
            con = csdl.mo(Path(td) / 'a.pabt', tao=True)
            try:
                from pabt.man_hinh_kiem_dem import HopKiemDem
                k = HopKiemDem(None, con, Path(td) / 'a.pabt', im_lang=True)
                self.assertLessEqual(k.minimumSizeHint().width(), 1024)
                self.assertLessEqual(k.minimumSizeHint().height(), 680)
            finally:
                con.close()

    def test_khong_nap_thu_vien_nang_khi_khoi_dong(self):
        import subprocess
        import sys
        ma = ('import os, sys\nos.environ["QT_QPA_PLATFORM"] = "offscreen"\nimport pabt\nfrom PySide6.QtWidgets import QApplication\n'
              'app = QApplication([])\nfrom pabt import app as ud\nw = ud.CuaSoChinh()\n'
              'print(",".join(m for m in ("openpyxl", "pypdf", "urllib.request", "difflib", "ezdxf", "numpy") if m in sys.modules))\n')
        r = subprocess.run([sys.executable, '-c', ma], capture_output=True, text=True, cwd=str(GOC), timeout=120,
                           env=dict(os.environ, PYTHONPATH=str(GOC)))
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertEqual(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '', '')

    def test_tao_ban_do_ma_bat_loi(self):
        import ast
        import tao_ban_do_ma as t
        self.assertEqual(t._vong({'a': {'b'}, 'b': {'a'}, 'c': set()}), [['a', 'b', 'a']])
        cay = ast.parse('from .to_chuc import TEN\n')
        self.assertEqual(t._import_cap_module(cay, 'x'), {'to_chuc'})
        cay = ast.parse('def f():\n    from . import to_chuc\n')
        self.assertEqual(t._import_cap_module(cay, 'x'), set())          # import trong hàm không tính vòng


if __name__ == '__main__':
    unittest.main()
