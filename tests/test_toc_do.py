"""Kiểm thử tối ưu tốc độ: bối cảnh tính toán nhớ trên kết nối (csdl.nho), chỉ mục thửa theo hộ, gộp ô bản in nhanh, hoàn tác
không giữ giao dịch mở. Mọi tối ưu phải cho kết quả như cách cũ."""
from __future__ import annotations
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import openpyxl
from openpyxl.styles import Border, Protection, Side

from pabt import csdl, du_an_moi, hoan_tac, in_an, nghiep_vu
from pabt.lap_pa import BoSoan


def _du_an(td: Path, so_ho: int = 12) -> Path:
    random.seed(3)
    dong = []
    for i in range(so_ho):
        for j in range(1 + i % 3):
            dong.append(dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i * 3 + j),
                             loai_dat=('ONT', 'CLN', 'LUC')[(i + j) % 3], dt_thu_hoi=str(50 + 10 * i + j), vi_tri='1'))
    gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
    p = td / 'a.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'), dong, gia)
    return p


class TestBoNhoBoiCanh(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name))
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_dung_lai_toi_khi_du_lieu_doi(self):
        a = nghiep_vu.BoiCanh.tu(self.con)
        self.assertIs(nghiep_vu.BoiCanh.tu(self.con), a)                  # chưa đổi gì: dùng lại, không đọc lại
        with self.con:
            self.con.execute("UPDATE thua SET dt_thu_hoi = '999' WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua)")
        b = nghiep_vu.BoiCanh.tu(self.con)
        self.assertIsNot(b, a)
        self.assertIn('999', [t['dt_thu_hoi'] for t in b.thua.values()])

    def test_may_khac_ghi_vao_file(self):
        a = nghiep_vu.BoiCanh.tu(self.con)
        khac = sqlite3.connect(str(self.p))                                # máy / kết nối khác sửa file (data_version đổi)
        with khac:
            khac.execute("UPDATE thua SET dt_thu_hoi = '555'")
        khac.close()
        self.assertIsNot(nghiep_vu.BoiCanh.tu(self.con), a)

    def test_khong_nho_giua_giao_dich_va_sau_rollback(self):
        a = nghiep_vu.BoiCanh.tu(self.con)
        self.con.execute("UPDATE thua SET dt_thu_hoi = '777'")             # giao dịch chưa ghi
        self.assertTrue(self.con.in_transaction)
        giua = nghiep_vu.BoiCanh.tu(self.con)
        self.assertIsNot(giua, a)
        self.con.rollback()
        sau = nghiep_vu.BoiCanh.tu(self.con)                               # không giữ số liệu đã hủy
        self.assertNotIn('777', [t['dt_thu_hoi'] for t in sau.thua.values()])

    def test_luu_phuong_an_giu_bo_nho(self):
        ma = self.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        bo = BoSoan(self.con, ma)
        a = bo.bc
        bo.luu()                                                           # chỉ ghi ho / ct_*: bối cảnh vẫn đúng, không đọc lại
        self.assertIs(bo.bc, a)
        with self.con, csdl.mo_khoa_danh_muc(self.con):
            self.con.execute("UPDATE dm_hotro SET ten = ten || ' ' WHERE rowid = (SELECT MIN(rowid) FROM dm_hotro)")
        self.assertIsNot(nghiep_vu.BoiCanh.tu(self.con), a)                # danh mục đổi: đọc lại

    def test_ket_noi_ngoai_csdl_mo(self):
        c = sqlite3.connect(str(self.p))                                   # không phải csdl.KetNoi: luôn đọc mới
        c.row_factory = sqlite3.Row
        try:
            self.assertIsNot(nghiep_vu.BoiCanh.tu(c), nghiep_vu.BoiCanh.tu(c))
        finally:
            c.close()

    def test_thua_cua_ho_nhu_cach_cu(self):
        bc = nghiep_vu.BoiCanh.tu(self.con)
        for (ma,) in self.con.execute('SELECT ma_ho FROM ho'):
            cu = sorted((t for t in bc.thua.values() if t['ma_ho'] == ma), key=lambda t: (t['thu_tu'], t['ma_thua']))
            self.assertEqual(bc.thua_cua(ma), cu)
        self.assertEqual(bc.thua_cua(-1), [])

    def test_hoan_tac_khong_giu_giao_dich_mo(self):
        ht = hoan_tac.HoanTac(self.con)
        self.assertFalse(self.con.in_transaction)
        self.assertEqual(ht.ten_hoan_tac(), '')


class TestTaiLon(unittest.TestCase):
    """Các tối ưu cho dự án lớn cho kết quả như cách cũ."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name), 30)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_doc_tat_ca_nhu_doc_tung_ho(self):
        tat_ca = nghiep_vu.doc_tat_ca_phuong_an(self.con)
        ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
        self.assertEqual(list(tat_ca), ma)
        for m in ma:
            self.assertEqual(tat_ca[m], nghiep_vu.doc_phuong_an(self.con, m))
        self.assertEqual(list(nghiep_vu.doc_tat_ca_phuong_an(self.con, ma[3:5])), ma[3:5])
        bc = nghiep_vu.BoiCanh.tu(self.con)
        self.assertEqual([k.tong for k in nghiep_vu.tinh_tat_ca(self.con)],
                         [nghiep_vu.tinh_ho(self.con, m, bc).tong for m in ma])

    def test_chi_muc_trung_nhu_ho_trung(self):
        from pabt import nhap_chi_tiet as nct
        with self.con:
            self.con.execute("UPDATE ho SET so_cccd = '079 1234' WHERE ma_ho = 3")
            self.con.execute("UPDATE ho SET ho_ten = 'Hộ thử 7 là chủ sử dụng đất' WHERE ma_ho = 9")
        ds = [nct.HoChiTiet('a', ho_ten=t, so_cccd=c) for t, c in (
            ('Hộ thử 1', ''), ('Ho thu 7', ''), ('Hộ thử 7.', ''), ('Không có', ''), ('X', '0791234'), ('X', '000'))]
        cm = nct.ChiMucTrung(self.con)
        for h in ds:
            self.assertEqual(cm.tim(h), nct.ho_trung(self.con, h), h)
        # hộ vừa thêm / thay trong cùng lần nhập cũng được nhận ra như truy vấn lại CSDL
        with self.con:
            self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd) VALUES (999, 999, 'Hộ mới Z', '555')")
            self.con.execute("UPDATE ho SET ho_ten = 'Tên đổi', so_cccd = '' WHERE ma_ho = 3")
        cm.ghi_nhan(999, 'Hộ mới Z', '555')
        cm.ghi_nhan(3, 'Tên đổi', '')
        for h in ds + [nct.HoChiTiet('b', ho_ten='Ho moi z'), nct.HoChiTiet('b', ho_ten='Q', so_cccd='555'),
                       nct.HoChiTiet('b', ho_ten='Tên đổi'), nct.HoChiTiet('b', ho_ten='Q', so_cccd='0791234')]:
            self.assertEqual(cm.tim(h), nct.ho_trung(self.con, h), h)

    def test_chay_nen(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest('không có Qt')
        QApplication.instance() or QApplication([])
        import time
        from pabt.giao_dien import chay_nen
        self.assertEqual(chay_nen(None, lambda: 7), 7)
        self.assertEqual(chay_nen(None, lambda: (time.sleep(0.6), 'xong')[1]), 'xong')       # qua mốc hiện hộp chờ
        with self.assertRaises(ZeroDivisionError):
            chay_nen(None, lambda: 1 / 0)


class TestGopONhanh(unittest.TestCase):
    @staticmethod
    def _bang(gop):
        wb = openpyxl.Workbook()
        ws = wb.active
        manh, mong = Side(style='medium', color='FF0000'), Side(style='thin')
        for r in range(1, 9):
            for c in range(1, 7):
                o = ws.cell(r, c, f'{r},{c}')
                if (r + c) % 3 == 0:
                    o.border = Border(left=mong, top=manh)
                elif (r + c) % 3 == 1:
                    o.border = Border(right=manh, bottom=mong)
                if r == 1:
                    o.protection = Protection(locked=False)
        for v in [(1, 1, 3, 1), (1, 2, 1, 4), (4, 3, 6, 5), (7, 1, 8, 6), (2, 6, 5, 6)]:
            gop(ws, *v)
        return ws

    @staticmethod
    def _o(ws):
        return [(o.coordinate, type(o).__name__, o.value, o.protection.locked,
                 tuple(TestGopONhanh._canh(getattr(o.border, s)) for s in ('left', 'right', 'top', 'bottom')))
                for hang in ws.iter_rows(min_row=1, max_row=8, max_col=6) for o in hang]

    @staticmethod
    def _canh(x):
        return (x.style, x.color.rgb if x.color is not None else None) if x is not None else (None, None)

    def test_giong_merge_cells_cua_openpyxl(self):
        cu = self._bang(lambda ws, r1, c1, r2, c2: ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2))
        with mock.patch.object(type(cu), '_clean_merge_range', side_effect=AssertionError('phải dùng đường nhanh')):
            moi = self._bang(in_an._gop_o)
        self.assertEqual(sorted(map(str, moi.merged_cells.ranges)), sorted(map(str, cu.merged_cells.ranges)))
        self.assertEqual(self._o(moi), self._o(cu))


class TestBoDauNhanh(unittest.TestCase):
    """lap_pa._bo_dau dùng bảng đổi ký tự (str.translate): kết quả phải giống hệt cách cũ (tách dấu NFD từng ký tự)."""

    @staticmethod
    def _cu(s: str) -> str:
        import unicodedata
        s = unicodedata.normalize('NFD', s).replace('đ', 'd').replace('Đ', 'D')
        return ' '.join(''.join(c for c in s if unicodedata.category(c) != 'Mn').lower().split())

    def test_giong_cach_cu(self):
        import unicodedata
        from pabt import don_gia
        from pabt.lap_pa import _bo_dau
        mau = [chr(i) for i in range(0x20, 0x3000)]                     # từng ký tự: Latin, dấu rời, khoảng trắng lạ...
        mau += ['Nhà cấp 4 - Tường gạch, mái tôn', 'ĐƯỜNG  SỐ 9 đoạn', 'Cây Xoài (Đk thân > 20-30 cm)', 'Æsir ǼĲ ﬁ',
                unicodedata.normalize('NFD', 'Bàu Hàm, Trảng Bom'), 'İstanbul ŉ ẞ', '  ', '',
                'Sân bê tông – 120 m² × 2 ≥ Ø 30 …', 'Cà phế ²̀', 'Ω Å K (ký hiệu dạng tách khác)']
        con = csdl.mo(don_gia.file_goc(), chi_doc=True)
        try:
            for b, cot in (('dm_taisan', 'ten'), ('dm_taisan', 'phan_loai'), ('dm_hotro', 'ten'), ('dm_loaidat', 'ten')):
                mau += [r[0] or '' for r in con.execute(f'SELECT {cot} FROM {b}')]
        finally:
            con.close()
        for s in mau:
            self.assertEqual(_bo_dau(s), self._cu(s), repr(s))


class TestKhongTruyVanTungHo(unittest.TestCase):
    """Kiểm tra lỗi, dự toán, quy chuẩn mật độ: số truy vấn KHÔNG tăng theo số hộ (trước: 3 truy vấn mỗi hộ - 5.000 hộ =
    15.000 truy vấn; quy chuẩn đọc lại cài đặt cho từng loại cây). Kết quả như đọc từng hộ."""

    @staticmethod
    def _dem(con, ham) -> int:
        n = [0]
        con.set_trace_callback(lambda s: n.__setitem__(0, n[0] + 1))
        try:
            ham()
        finally:
            con.set_trace_callback(None)
        return n[0]

    def test_so_truy_van_khong_doi_theo_so_ho(self):
        from pabt import cay_trong, du_toan, kiem_loi
        dem = {}
        for so_ho in (20, 80):
            with tempfile.TemporaryDirectory() as td:
                con = csdl.mo(_du_an(Path(td), so_ho=so_ho))
                try:
                    dem[so_ho] = [self._dem(con, lambda: kiem_loi.kiem_tra(con)), self._dem(con, lambda: du_toan.tu_du_an(con)),
                                  self._dem(con, lambda: cay_trong.ds_quy_chuan_mat_do(con))]
                    if so_ho == 80:                        # cùng kết quả như cách cũ (đọc phương án từng hộ)
                        moi = [(x.ma_ho, x.noi_dung) for x in kiem_loi.kiem_tra(con)]
                        with mock.patch.object(kiem_loi, 'doc_tat_ca_phuong_an', return_value={}):
                            cu = [(x.ma_ho, x.noi_dung) for x in kiem_loi.kiem_tra(con)]
                        self.assertEqual(moi, cu)
                finally:
                    con.close()
        self.assertEqual(dem[20], dem[80], 'số truy vấn tăng theo số hộ (truy vấn N+1)')


class TestRaSoatTaiLon(unittest.TestCase):
    """Rà soát tốc độ / đúng sai: kết quả dùng chung, giao dịch lồng, đọc hết dòng Excel, không ghi vào bộ đơn giá."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name), 15)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_ket_qua_dung_chung_va_tinh_lai_mot_ho(self):
        a = nghiep_vu.ket_qua_ho(self.con)
        self.assertIs(nghiep_vu.ket_qua_ho(self.con), a)                  # chưa đổi gì: không tính lại
        ma = list(a)[3]
        bo = BoSoan(self.con, ma)
        bo.pa.dat[0].ty_le = nghiep_vu.D('0.5')
        bo.luu()
        b = nghiep_vu.ket_qua_ho(self.con)
        self.assertIsNot(b, a)
        moi = {m: nghiep_vu.tinh_pa(pa, nghiep_vu.BoiCanh._doc(self.con))
               for m, pa in nghiep_vu.doc_tat_ca_phuong_an(self.con).items()}
        self.assertEqual({m: (k.tong, dict(k.muc)) for m, (k, _) in b.items()}, {m: (k.tong, dict(k.muc)) for m, k in moi.items()})
        self.assertNotEqual(b[ma][0].tong, a[ma][0].tong)
        self.assertTrue(all(b[m] is a[m] for m in a if m != ma))         # hộ khác: dùng lại, không tính lại
        with self.con:                                                    # ghi khác (thửa): tính lại cả dự án
            self.con.execute("UPDATE thua SET dt_thu_hoi = '1' WHERE ma_ho = ?", (list(a)[0],))
        self.assertIsNot(nghiep_vu.ket_qua_ho(self.con), b)

    def test_giao_dich_long_mot_lan_ghi(self):
        from pabt import theo_doi
        ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho')]
        qd = theo_doi.luu_qd(self.con, None, '9/QĐ-UBND', '01/09/2026')
        dem = []
        self.con.set_trace_callback(lambda s: dem.append(s) if s.strip().upper() == 'COMMIT' else None)
        try:
            theo_doi.them_ho_theo_pa(self.con, qd, ma)
        finally:
            self.con.set_trace_callback(None)
        self.assertEqual(len(dem), 1)                                     # trước đây mỗi hộ một COMMIT
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM qd_ho WHERE qd_id = ?', (qd,)).fetchone()[0], len(ma))
        # lỗi giữa chừng: hủy cả lô (không để lại hộ ghi dở)
        with self.assertRaises(KeyError):
            with csdl.giao_dich(self.con):
                theo_doi.bo_cac_ho_khoi_qd(self.con, qd, ma[:5])
                theo_doi.ghi_qd_ho(self.con, qd, ma[6], {'khong_co': 1})
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM qd_ho WHERE qd_id = ?', (qd,)).fetchone()[0], len(ma))

    def test_doc_het_dong_excel(self):
        from pabt import nhap_chi_tiet
        wb = openpyxl.Workbook()
        ws = wb.active
        for r in range(1, 900):
            ws.cell(r, 1, f'dòng {r}' if r % 7 else None)
        ws.cell(1000, 1, 'TỔNG CỘNG')                                    # sau dòng 600 (trước đây bị cắt), cách 100 dòng trống
        ws.cell(1001 + nhap_chi_tiet.TRONG_LIEN_TIEP + 5, 1, 'rác sau khoảng trống dài')
        hang = nhap_chi_tiet.doc_hang(ws)
        self.assertEqual(len(hang), 1000)
        self.assertEqual(hang[-1][0], 'TỔNG CỘNG')

    def test_khong_ghi_vao_bo_don_gia(self):
        import hashlib
        import shutil
        from pabt import don_gia
        goc = Path(self.td.name) / don_gia.TEN_FILE   # cùng tên bộ đóng gói: csdl.mo không ghi cờ phiên bản vào bộ đơn giá
        shutil.copy(don_gia.file_goc(), goc)
        truoc = hashlib.sha256(goc.read_bytes()).hexdigest()
        csdl.chep_danh_muc(self.con, goc, don_vi=False, bang=don_gia.BANG_BO)
        csdl.mo(goc).close()
        self.assertEqual(hashlib.sha256(goc.read_bytes()).hexdigest(), truoc)
        self.assertTrue(self.con.execute("SELECT 1 FROM sqlite_master WHERE name = 'ix_ctdat_thua'").fetchone())


class TestSuaDot(unittest.TestCase):
    """Sửa / xóa đợt khi đang đứng ở dòng "(Chưa xếp đợt)": trước đây bấm không có phản hồi."""

    def test_sua_dot_khi_dung_dong_chua_xep(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt import man_hinh_quan_ly as M, quan_ly
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        con = csdl.mo(_du_an(Path(td.name), 4))
        self.addCleanup(con.close)
        d = M.HopDotTrinh(con, None)
        thong_bao = []
        with mock.patch.object(QMessageBox, 'information', side_effect=lambda *a, **k: thong_bao.append(a[2])):
            i = d.them_dot(dict(ten='Đợt 1', ngay_trinh='10/10/2026', so_to_trinh='113', ghi_chu=''))
            d.bang_dot.selectRow(1)                                       # dòng "(Chưa xếp đợt)"
            self.assertIsNone(d.dot_chon())
            self.assertEqual(d.sua_dot(dict(ten='Đợt 1', ngay_trinh='10/10/2026', so_to_trinh='114', ghi_chu='')), i)
            self.assertEqual(quan_ly.lay_dot(con, i).so_to_trinh, '114')  # chỉ một đợt: lấy đợt đó
            j = d.them_dot(dict(ten='Đợt 2', ngay_trinh='', so_to_trinh='', ghi_chu=''))
            d.bang_dot.selectRow(2)
            self.assertIsNone(d.sua_dot(dict(ten='X', ngay_trinh='', so_to_trinh='', ghi_chu='')))
            self.assertTrue(thong_bao and 'Chọn một đợt' in thong_bao[-1])         # nhiều đợt: báo chọn đợt
            self.assertEqual(quan_ly.lay_dot(con, j).ten, 'Đợt 2')


if __name__ == '__main__':
    unittest.main()
