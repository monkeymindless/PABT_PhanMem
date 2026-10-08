"""Kiểm thử 0.9.12: bản in phương án chi tiết - nguồn gốc đất dài / ngắn hiện đủ chữ, dòng "Dự án:" cao vừa tên dự án
(dùng mẫu in mau_in/ đóng gói kèm, không cần file Excel thật; dữ liệu giả)."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an, nhap_tho
from tests.test_nhap_tho import _don_gian, _ghi

NGUON_GOC = ('Căn cứ Giấy xác nhận nguồn gốc đất số 01/GXN-UBND ngày 01/8/2026 của UBND xã Mẫu, tỉnh Thử Nghiệm nơi có '
             'đất thu hồi xác nhận nội dung, cụ thể như sau: - Thửa đất số 10; 11, tờ bản đồ số 5, xã Mẫu: Ngày 01/01/2000, '
             'Hợp đồng giao khoán sản xuất nông nghiệp và nuôi trồng thủy sản số 01/HĐGK giữa Lâm trường A và bà Nguyễn Thị '
             'Một. Bà Nguyễn Thị Một sử dụng đất theo hợp đồng giao khoán đất. Sau đó, bà Nguyễn Thị Một chết năm 2020. Hiện '
             'nay, ông Nguyễn Văn Hai (con của bà Nguyễn Thị Một - đại diện) là người đang quản lý, sử dụng đất.')


def _vung(ws, r, c):
    return next((m for m in ws.merged_cells.ranges if m.min_row <= r <= m.max_row and m.min_col <= c <= m.max_col), None)


class CoSo(unittest.TestCase):
    TEN = 'Xây dựng đường liên xã đoạn qua xã Mẫu'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        self.p = self.td / 'da.pabt'
        nhap_tho.nhap(xl, self.p, self.TEN)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def in_ho(self, nguon_goc: str, ten_du_an: str | None = None):
        with self.con:
            self.con.execute('UPDATE thua SET nguon_goc = ? WHERE ma_ho = 1', (nguon_goc,))
            if ten_du_an:
                self.con.execute('UPDATE du_an SET ten = ? WHERE id = 1', (ten_du_an,))
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'ct.xlsx')
        return openpyxl.load_workbook(f).active

    def dong_nguon_goc(self, ws):
        """Các dòng sau tiêu đề "II. Thông tin nguồn gốc đất" tới "III.": [(dòng, chữ, chiều cao)]."""
        r = next(r for r in range(1, 60) if str(ws.cell(r, 1).value or '').startswith('II.'))
        kq = []
        for rr in range(r + 1, r + 40):
            if str(ws.cell(rr, 1).value or '').startswith('III.'):
                break
            kq.append((rr, ws.cell(rr, 1).value, ws.row_dimensions[rr].height))
        return kq


class TestNgatDong(unittest.TestCase):
    def test_ngat_dong_va_chieu_cao(self):
        do = lambda s, *_: len(s) * 5.0                       # noqa: E731  mỗi ký tự 5 pt
        self.assertEqual(in_an.ngat_dong('aaa bbb ccc', 40 / 0.97, do=do), ['aaa bbb', 'ccc'])
        self.assertEqual(in_an.ngat_dong('một\nhai', 1000, do=do), ['một', 'hai'])
        self.assertEqual(len(in_an.ngat_dong('x' * 25, 50 / 0.97, do=do)), 3)    # từ dài hơn dòng: cắt ngang
        self.assertAlmostEqual(in_an.cao_dong_chu(2, 14), 33.6)


class TestNguonGoc(CoSo):
    def test_nguon_goc_dai_hien_du(self):
        ws = self.in_ho(NGUON_GOC)
        ds = self.dong_nguon_goc(ws)
        chu = [x for _, x, _ in ds if x]
        self.assertEqual(len(chu), 1)
        self.assertEqual(' '.join(chu[0].split()), ' '.join(NGUON_GOC.split()))     # không mất chữ
        r, _, cao = next(x for x in ds if x[1])
        so_dong = len(in_an.ngat_dong(NGUON_GOC, in_an._rong_vung(ws, 1, 8)))
        self.assertGreaterEqual(so_dong, 4)
        self.assertGreaterEqual(cao, in_an.cao_dong_chu(so_dong, 14))              # đủ cao cho mọi dòng chữ
        m = _vung(ws, r, 1)
        self.assertEqual((m.min_row, m.max_row, m.min_col, m.max_col), (r, r, 1, 8))  # gộp ngang 1 dòng (Excel ngắt dòng)
        self.assertTrue(ws.cell(r, 1).alignment.wrap_text)
        self.assertTrue(all(h <= 6 for _, x, h in ds if not x))                     # dòng thừa của vùng gộp cũ: khoảng cách nhỏ

    def test_nguon_goc_ngan_va_nhieu_thua(self):
        ws = self.in_ho('Đất khai phá năm 1995.')
        ds = self.dong_nguon_goc(ws)
        r, x, cao = next(d for d in ds if d[1])
        self.assertEqual(x, 'Đất khai phá năm 1995.')
        self.assertLess(cao, 30)
        # các thửa có nguồn gốc khác nhau: in đủ, mỗi nội dung một đoạn
        with self.con:
            t = [r[0] for r in self.con.execute('SELECT ma_thua FROM thua WHERE ma_ho = 1 ORDER BY thu_tu, ma_thua')]
            self.con.execute("UPDATE thua SET nguon_goc = 'Nhận chuyển nhượng năm 2001.' WHERE ma_thua = ?", (t[-1],))
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'ct2.xlsx')
        ws = openpyxl.load_workbook(f).active
        x = next(d[1] for d in self.dong_nguon_goc(ws) if d[1])
        self.assertEqual(x, 'Đất khai phá năm 1995.\nNhận chuyển nhượng năm 2001.')

    def test_nguon_goc_rat_dai_chia_nhieu_dong(self):
        dai = '\n'.join([NGUON_GOC] * 7)
        ws = self.in_ho(dai)
        ds = [d for d in self.dong_nguon_goc(ws) if d[1]]
        self.assertGreater(len(ds), 1)                                           # vượt 409 pt: sang dòng Excel kế tiếp
        self.assertTrue(all(h <= in_an.CAO_TOI_DA for _, _, h in ds))
        self.assertEqual(' '.join(' '.join(x for _, x, _ in ds).split()), ' '.join(dai.split()))
        self.assertEqual(ws.cell(next(r for r in range(1, 200) if ws.cell(r, 1).value == 'STT'), 2).value, 'Tên tài sản')


class TestTenDuAn(CoSo):
    def _dong_du_an(self, ws):
        r = next(r for r in range(1, 20) if str(ws.cell(r, 1).value or '').startswith('Dự án:'))
        return r, ws.row_dimensions[r].height, ws.cell(r, 1)

    def test_ten_ngan_mot_dong(self):
        r, cao, o = self._dong_du_an(self.in_ho('x'))
        self.assertEqual(o.value, f'Dự án: {self.TEN}')
        self.assertAlmostEqual(cao, in_an.cao_dong_chu(1, 14) + 3, places=1)    # sát chữ, không còn 38,4 pt cố định
        self.assertEqual(o.alignment.vertical, 'top')
        self.assertTrue(o.alignment.wrap_text)

    def test_ten_dai_xuong_dong(self):
        ten = ('Thành phần 1: Đầu tư xây dựng đoạn từ cầu A đến ngã ba B (giai đoạn 1) theo phương thức đối tác công tư (PPP), '
               'hợp đồng BOT, đợt 2')
        r, cao, o = self._dong_du_an(self.in_ho('x', ten))
        so = len(in_an.ngat_dong(o.value, in_an._rong_vung(self.in_ho('x', ten), 1, 8), dam=True))
        self.assertGreaterEqual(so, 2)
        self.assertAlmostEqual(cao, in_an.cao_dong_chu(so, 14) + 3, places=1)


class TestMauIn(CoSo):
    def test_xem_truoc_va_mau_de_sua(self):
        f = in_an.xem_truoc(self.con, 1, self.td / 'xem')
        self.assertTrue(f.exists())
        p = in_an.mau_de_sua()
        self.assertTrue(p.exists())
        self.assertEqual(p.name, 'IN_CHITIET.xlsx')

    def test_duong_ke_lay_tu_mau_da_sua(self):
        """Mẫu đã sửa trong Excel (còn hình vẽ đường kẻ): lấy đường kẻ ngay trong mẫu."""
        import shutil
        import zipfile
        tm = self.td / 'mau'
        shutil.copytree(in_an.thu_muc_mau(), tm)
        xml = (tm / 'IN_CHITIET.duong_ke.xml').read_text(encoding='utf-8')
        f = in_an.lap_chi_tiet(self.con, 1, tm / 'IN_CHITIET.xlsx', tm)        # file có hình vẽ (giống Excel lưu)
        (tm / 'IN_CHITIET.duong_ke.xml').write_text('', encoding='utf-8')
        self.assertTrue(zipfile.is_zipfile(f))
        p = in_an.duong_ke_cua_mau(f, 'IN_CHITIET')
        self.assertEqual(p.read_text(encoding='utf-8').count('prst="line"'), xml.count('prst="line"'))


if __name__ == '__main__':
    unittest.main()
