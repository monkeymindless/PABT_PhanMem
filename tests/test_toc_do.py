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
        mau += ['Nhà cấp 4 - Tường gạch, mái tôn', 'ĐƯỜNG  ĐT762 đoạn', 'Cây Xoài (Đk thân > 20-30 cm)', 'Æsir ǼĲ ﬁ',
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


if __name__ == '__main__':
    unittest.main()
