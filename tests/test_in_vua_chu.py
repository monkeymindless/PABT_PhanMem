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
            kq.append((rr, ws.cell(rr, 1).value, ws.row_dimensions[rr].height))
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
            self.assertTrue(in_an.DK_CACH - 0.01 <= khe <= t['co'] * in_an.DK_CO_DAU_DUOI + 0.01, (o, khe))  # sát, có khe
            self.assertGreater(dai, 0)

    def test_chi_tiet(self):
        with self.con:
            self.con.execute("UPDATE du_an SET ten = 'Xây dựng đường liên xã đoạn qua xã Mẫu' WHERE id = 1")
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'ct.xlsx')
        self.kiem(f, ['E1', 'A2', 'A5'])                     # tiêu ngữ (dòng 1), tên đơn vị (dòng 2), Dự án

    def test_bang_tong_hop_cot_an(self):
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        ws = openpyxl.load_workbook(f).active
        self.assertEqual(in_an._px_cot(ws)[11], 0)          # cột L ẩn: rộng 0
        self.kiem(f, ['A2', 'S2', 'A6'])

    def test_bang_tong_hop_khong_co_file_duong_ke(self):
        # máy cập nhật bằng gói .pabtcn (không mang mau_in): mẫu không có .duong_ke.xml -> tự tạo 3 đường kẻ mặc định
        import shutil
        mau = self.td / 'mau'
        mau.mkdir()
        shutil.copy2(MAU / 'IN_BANGTONGHOP.xlsx', mau / 'IN_BANGTONGHOP.xlsx')
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth3.xlsx', mau=mau / 'IN_BANGTONGHOP.xlsx')
        self.kiem(f, ['A2', 'S2', 'A6'])

    def test_tieu_ngu_dai_bang_chu(self):
        ws, bc, bd, kq = self.duong_ke(in_an.lap_chi_tiet(self.con, 1, self.td / 'ct2.xlsx'))
        e1 = in_an._dong_chu_o(ws, 1, 5, bc, bd, self.do)
        giua, dai, y = min(kq, key=lambda k: abs(k[0] - (e1['x1'] + e1['x2']) / 2))     # đường dưới "Độc lập - Tự do - Hạnh phúc"
        rong = self.do('Độc lập - Tự do - Hạnh phúc', 'Times New Roman', 14, True) * in_an.EMU_PT
        self.assertAlmostEqual(dai, rong, delta=2 * in_an.EMU_PX)


class TestNguonGoc(CoSo):
    def test_gach_dau_dong_in_thut_le(self):
        ng = ('Căn cứ các Giấy xác nhận nguồn gốc đất số 01/UBND ngày 24/8/2026 của UBND phường Mẫu, cụ thể như sau:\n'
              '- Một phần thửa đất số 11, tờ bản đồ số 159, phường Mẫu: Bưu điện Văn hóa Thử (thuộc Bưu điện phường Mẫu) là '
              'chủ sở hữu tài sản trên một phần thửa đất do Khu Bảo tồn Thử quản lý.\n'
              '- Bưu điện Văn hóa Thử đang sử dụng đất, là chủ sở hữu tài sản: Phòng giao dịch, mái che, cửa cổng.')
        ws = self.in_ho(ng)
        chu = next(x for _, x, _ in self.dong_nguon_goc(ws) if x)
        dong = chu.split('\n')
        self.assertTrue(dong[0].startswith('Căn cứ'))
        dau = [i for i, d in enumerate(dong) if d.startswith('- ')]
        self.assertEqual(len(dau), 2)
        tran = [d for d in dong[dau[0] + 1:dau[1]]]                  # dòng tràn của gạch đầu dòng thứ nhất
        self.assertTrue(tran and all(d.startswith(' ') and not d.startswith('-') for d in tran), dong)
        self.assertEqual(' '.join(chu.split()), ' '.join(ng.split()))       # không mất chữ

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
