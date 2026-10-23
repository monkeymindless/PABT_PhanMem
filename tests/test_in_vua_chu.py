"""Kiểm thử 0.9.12: bản in phương án chi tiết - nguồn gốc đất dài / ngắn hiện đủ chữ, dòng "Dự án:" cao vừa tên dự án
(dùng mẫu in mau_in/ đóng gói kèm, không cần file Excel thật; dữ liệu giả)."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, in_an, nhap_tho
from tests.test_nhap_tho import _don_gian, _ghi

MAU = Path(__file__).resolve().parents[1] / 'mau_in'

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
            v = ws.cell(rr, 1).value
            if isinstance(v, str):                                  # bỏ thụt đầu dòng (NBSP, 16/10/2026) - so nội dung chữ
                v = '\n'.join(x.lstrip(in_an.NBSP) for x in v.split('\n'))
            kq.append((rr, v, ws.row_dimensions[rr].height))
        return kq


class TestNgatDong(unittest.TestCase):
    def test_ngat_dong_va_chieu_cao(self):
        do = lambda s, *_: len(s) * 5.0                       # noqa: E731  mỗi ký tự 5 pt
        self.assertEqual(in_an.ngat_dong('aaa bbb ccc', 40 / 0.97, do=do), ['aaa bbb', 'ccc'])
        self.assertEqual(in_an.ngat_dong('một\nhai', 1000, do=do), ['một', 'hai'])
        self.assertEqual(len(in_an.ngat_dong('x' * 25, 50 / 0.97, do=do)), 3)    # từ dài hơn dòng: cắt ngang
        self.assertAlmostEqual(in_an.cao_dong_chu(2, 14), 33.6)

    def test_gach_dau_dong_thut_le_dong_tran(self):
        # dòng tràn của đoạn bắt đầu bằng "- " thụt vào thẳng chữ sau ký hiệu (khoảng trắng + xuống dòng cứng), đoạn thường
        # giữ như cũ (người dùng yêu cầu 10/10/2026)
        do = lambda s, *_: len(s) * 5.0                       # noqa: E731  mỗi ký tự 5 pt
        kq = in_an._ngat('Căn cứ:\n- aaa bbb ccc ddd\nxx yy zz', 45 / 0.97, 'T', 14, False, do)
        self.assertEqual(kq, [('Căn cứ:', True), ('- aaa bbb', True), ('  ccc ddd', in_an.TREO), ('xx yy zz', True)])
        kq = in_an._ngat('a) mot hai ba bon', 50 / 0.97, 'T', 14, False, do)       # 10 ký tự / dòng
        self.assertEqual(kq, [('a) mot hai', True), ('   ba bon', in_an.TREO)])
        self.assertEqual(in_an._ngat('aaa bbb ccc', 40 / 0.97, 'T', 14, False, do), [('aaa bbb', True), ('ccc', False)])

    def test_nhan_ky_hieu_dau_dong(self):
        from pabt.ho_so import dau_dong
        for doan, ky in (('- Thửa 11', '- '), ('+ Tài sản', '+ '), ('• x', '• '), ('a) Đất', 'a) '), ('2. Thửa', '2. '),
                         ('Căn cứ Giấy - số 1', ''), ('-Liền', ''), ('2026 năm', ''), ('', '')):
            self.assertEqual(dau_dong(doan), ky, doan)


class TestDuongKe(CoSo):
    """Đường kẻ dưới tên đơn vị / tiêu ngữ / Dự án: sát dưới chân chữ (có khe hở, không che dấu), căn giữa theo chữ
    (người dùng yêu cầu 10/10/2026). Bảng tổng hợp có cột ẩn (L, M, O): vị trí cột phải trừ cột ẩn."""

    def duong_ke(self, file_xlsx):
        import re
        import zipfile
        with zipfile.ZipFile(file_xlsx) as z:
            x = z.read(next(n for n in z.namelist() if n.startswith('xl/drawings/drawing'))).decode('utf-8')
        ws = openpyxl.load_workbook(file_xlsx).active
        bc, bd = in_an._bien_cot(ws), in_an._bien_dong(ws)
        kq = []
        for a in re.findall(r'<xdr:twoCellAnchor.*?</xdr:twoCellAnchor>', x, re.S):
            n = {m.group(1): tuple(int(v) for v in m.group(2, 3, 4, 5)) for m in in_an._RE_NEO.finditer(a)}
            x1, x2 = bc[n['from'][0]] + n['from'][1], bc[n['to'][0]] + n['to'][1]
            kq.append(((x1 + x2) / 2, x2 - x1, bd[n['from'][2]] + n['from'][3]))
        return ws, bc, bd, kq

    def setUp(self):
        super().setUp()
        # đo chữ cố định (Times New Roman ~0,47 / 0,52 cỡ chữ): không phụ thuộc phông của máy chạy test (offscreen không có
        # phông Windows, chữ rộng gần gấp đôi - "Độc lập…" bị ngắt dòng)
        from unittest import mock
        do = lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47)      # noqa: E731
        self._vo = mock.patch.object(in_an, '_ham_do_chu', lambda: do)
        self._vo.start()
        self.do = do

    def tearDown(self):
        self._vo.stop()
        super().tearDown()

    def kiem(self, file_xlsx, o_chu):
        ws, bc, bd, kq = self.duong_ke(file_xlsx)
        self.assertEqual(len(kq), len(o_chu))
        for o in o_chu:
            c = ws[o]
            t = in_an._dong_chu_o(ws, c.row, c.column, bc, bd, self.do)
            giua, dai, y = min(kq, key=lambda k: abs(k[2] - t['chan'][-1]) + abs(k[0] - (t['x1'] + t['x2']) / 2))
            self.assertAlmostEqual(giua, (t['x1'] + t['x2']) / 2, delta=2 * in_an.EMU_PX, msg=o)       # căn giữa theo chữ
            khe = (y - t['chan'][-1]) / in_an.EMU_PT
            cach = in_an.DK_CACH_DU_AN if o == 'A6' else in_an.DK_CACH                        # dòng Dự án: gần chữ hơn (24/10/2026)
            self.assertTrue(cach - 0.01 <= khe <= max(cach, t['co'] * in_an.DK_CO_DAU_DUOI) + 0.01,
                            (o, khe))                    # hở >= DK_CACH (5 pt): không chạm chân chữ / dấu nặng
            self.assertGreater(dai, 0)


    def test_bang_tong_hop_cot_an(self):
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        ws = openpyxl.load_workbook(f).active
        self.assertEqual(in_an._px_cot(ws)[11], 0)          # cột L ẩn: rộng 0
        self.kiem(f, ['A2', 'S2', 'A6'])

    def test_bang_tong_hop_khong_co_file_duong_ke(self):
        # 1.0.20: bảng tổng hợp dựng bằng mã, không file .duong_ke.xml -> luôn tự tạo 3 đường kẻ mặc định
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth3.xlsx')
        self.kiem(f, ['A2', 'S2', 'A6'])


if __name__ == '__main__':
    unittest.main()
