"""Kiểm thử 0.9.83 (người dùng 14/10/2026, ảnh Format Cells và bảng tính dính sát viền): bản in - ô bảng căn giữa dọc, dòng
cao max(24, số dòng x 16,5 + 8), tiêu đề cột 28 pt, nguồn gốc đất quá 350 pt tách sang dòng mới ở chỗ hết câu / đoạn,
đường kẻ cách chân chữ 5 pt (mẫu in đóng gói kèm, dữ liệu giả)."""
from __future__ import annotations
import unittest

import openpyxl

from pabt import in_an
from tests.test_in_vua_chu import NGUON_GOC, CoSo, _vung


class TestHangSo(unittest.TestCase):
    def test_cao_dong_bang(self):
        self.assertEqual(in_an.DK_CACH, 5.0)
        self.assertEqual(in_an.cao_dong_bang(0), 24.0)
        # 16,5 pt / dòng ở cỡ 14 là mức sàn; khoảng dòng Excel đo ở màn hình 125% (~1,3 cỡ chữ) lớn hơn thì theo Excel
        self.assertEqual(in_an.dong_chu_bang(14), max(16.5, 14 * in_an.HE_SO_DONG_EXCEL))
        self.assertGreaterEqual(in_an.dong_chu_bang(14), 18.0)                # Excel: Times New Roman 14 = 18 pt / dòng
        self.assertGreaterEqual(in_an.dong_chu_bang(20), 25.2)                # Excel: Times New Roman 20 = 25,2 pt / dòng
        self.assertAlmostEqual(in_an.cao_dong_bang(1), max(24.0, in_an.dong_chu_bang(14) + 8))
        self.assertAlmostEqual(in_an.cao_dong_bang(3), 3 * in_an.dong_chu_bang(14) + 8)    # đệm 4 pt trên / dưới
        self.assertEqual(in_an.cao_dong_bang(30, 20, None), 30 * in_an.dong_chu_bang(20) + 8)  # không chặn: biết cần thêm dòng
        self.assertEqual(in_an.cao_dong_bang(100), in_an.CAO_TOI_DA)
        self.assertEqual(in_an.so_dong_o(1234567, 10), 1)                  # ô số không ngắt dòng

    def test_chia_doan_van_o_cho_het_cau(self):
        do = lambda s, *_: len(s) * 5.0                       # noqa: E731  mỗi ký tự 5 pt: 10 ký tự / dòng
        rong = 50 / 0.97
        chu = 'aa bb cc. dd ee ff gg hh ii kk ll'
        k = in_an._chia_doan_van(chu, rong, 'T', 14, False, do, 3)
        self.assertEqual([x for x, _ in k[0]], ['aa bb cc.'])    # khối 3 dòng sẽ cắt giữa câu: cắt ngay sau dấu chấm
        self.assertTrue(all(len(x) <= 3 for x in k))
        self.assertEqual(' '.join(x for kh in k for x, _ in kh).split(), chu.split())       # không mất chữ
        k = in_an._chia_doan_van('aa bb cc dd ee ff gg hh', rong, 'T', 14, False, do, 2)    # không có chỗ hết câu: đủ khối
        self.assertEqual([len(x) for x in k], [2, 1])
        self.assertEqual(in_an._chia_doan_van('ngắn', rong, 'T', 14, False, do, 3), [[('ngắn', True)]])


class TestBangChiTiet(CoSo):
    def setUp(self):
        super().setUp()
        # đo chữ cố định (Times New Roman ~0,47 / 0,52 cỡ chữ) như test_in_vua_chu.TestDuongKe: phông offscreen rộng gần gấp đôi
        from unittest import mock
        self._vo = mock.patch.object(in_an, '_ham_do_chu', lambda: lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47))
        self._vo.start()

    def tearDown(self):
        self._vo.stop()
        super().tearDown()

    def _bang(self, ws):
        stt = next(r for r in range(1, 200) if str(ws.cell(r, 1).value or '').strip().upper() == 'STT')
        cuoi = next(r for r in range(stt + 1, 300) if 'TỔNG CỘNG' in (ws.cell(r, 1).value, ws.cell(r, 2).value))   # 0.9.88: gộp từ cột STT
        return stt, cuoi

    def test_can_giua_doc_va_chieu_cao(self):
        ws = self.in_ho('Đất khai phá năm 1995.')
        stt, cuoi = self._bang(ws)
        for r in range(stt, cuoi + 1):
            for c in range(1, 9):
                if type(ws.cell(r, c)).__name__ == 'MergedCell':      # ô bị gộp (thưởng, tổng cộng - 0.9.88): kiểu ở ô đầu vùng
                    continue
                al = ws.cell(r, c).alignment
                self.assertEqual(al.vertical, 'center', (r, c))
                self.assertTrue(al.wrap_text, (r, c))
        # tiêu đề "Thành tiền\n(đồng)" hai dòng: >= 28 pt, đủ cho hai dòng chữ
        self.assertGreaterEqual(ws.row_dimensions[stt].height, in_an.CAO_TIEU_DE_BANG)
        self.assertGreaterEqual(ws.row_dimensions[stt].height, in_an.cao_dong_bang(2))
        px = in_an._px_cot(ws, 9)
        for r in range(stt + 1, cuoi + 1):
            h = ws.row_dimensions[r].height
            self.assertGreaterEqual(h, in_an.CAO_DONG_BANG_TOI_THIEU, r)
            dam = ws.cell(r, in_an.COT_KIND).value != 'I'                     # dòng mục / tổng in đậm
            gop = next((m for m in ws.merged_cells.ranges if m.min_row == r and m.min_col <= 2 <= m.max_col), None)
            c1, c2 = (gop.min_col, gop.max_col) if gop else (2, 2)          # thưởng / tổng cộng gộp ô (0.9.88): đo cả vùng
            chu = ws.cell(r, c1).value
            so = in_an.so_dong_o(chu, sum(px[c1 - 1:c2]) * 0.75 - 6, dam=dam)
            self.assertGreaterEqual(h, in_an.cao_dong_bang(so) - 0.01, r)     # đủ chỗ cho mọi dòng chữ + đệm

    def test_tieu_de_mot_dong_28pt(self):
        import shutil
        mau = self.td / 'mau'
        mau.mkdir()
        wb = openpyxl.load_workbook(in_an.file_mau(None, in_an.TEN_CT))
        ws = wb.worksheets[0]
        stt = next(r for r in range(1, 200) if str(ws.cell(r, 1).value or '').strip().upper() == 'STT')
        for c in range(1, 9):
            if isinstance(ws.cell(stt, c).value, str):
                ws.cell(stt, c).value = ws.cell(stt, c).value.split('\n')[0].split()[0]   # mỗi tiêu đề một từ
        wb.save(mau / 'IN_CHITIET.xlsx')
        shutil.copy2(in_an.duong_ke_cua_mau(in_an.file_mau(None, in_an.TEN_CT), in_an.TEN_CT), mau / 'IN_CHITIET.duong_ke.xml')
        f = in_an.lap_chi_tiet(self.con, 1, self.td / 'ct1.xlsx', mau=mau / 'IN_CHITIET.xlsx')
        ws = openpyxl.load_workbook(f).active
        stt, _ = self._bang(ws)
        self.assertEqual(ws.row_dimensions[stt].height, in_an.CAO_TIEU_DE_BANG)

    def test_nguon_goc_qua_350pt_tach_o_cho_het_cau(self):
        dai = ' '.join([NGUON_GOC] * 6)                                    # một đoạn rất dài: vượt 350 pt
        ws = self.in_ho(dai)
        ds = [d for d in self.dong_nguon_goc(ws) if d[1]]
        self.assertGreater(len(ds), 1)
        self.assertTrue(all(h <= in_an.CAO_DOAN_TOI_DA for _, _, h in ds))
        self.assertEqual(' '.join(' '.join(x for _, x, _ in ds).split()), ' '.join(dai.split()))   # không mất chữ
        toi_da = int((in_an.CAO_DOAN_TOI_DA - in_an.DEM_DONG) // in_an.dong_chu_bang(14))
        rong = in_an._rong_vung(ws, 1, 8)
        for (r, x, _), (_, sau, _) in zip(ds, ds[1:]):
            # 16/10/2026: tách ở ranh giới dòng đã ngắt - hết đoạn (chuan_nguon_goc đưa " - " thành đoạn "- " mới), dòng kết thúc
            # bằng dấu hết câu, hoặc đủ khối toi_da dòng (không xuống dòng sớm giữa đoạn)
            self.assertTrue(x.rstrip().endswith(('.', ';', ':')) or sau.startswith('- ')
                            or len(in_an.ngat_dong(x, rong)) == toi_da, (x[-40:], sau[:20]))
        for r, _, _ in ds:
            m = _vung(ws, r, 1)
            self.assertEqual((m.min_row, m.max_row, m.min_col, m.max_col), (r, r, 1, 8))    # dòng mới gộp cùng dải cột
            al = ws.cell(r, 1).alignment
            self.assertEqual((al.horizontal, al.vertical, al.wrap_text), ('justify', 'top', True))   # 0.9.85: canh trên (hồ sơ)
            for c in range(1, 9):                                           # dòng mới chép kiểu (viền ô) của dòng đầu
                vien = [tuple(getattr(ws.cell(rr, c).border, k).style for k in ('left', 'right', 'top', 'bottom'))
                        for rr in (r, ds[0][0])]
                self.assertEqual(vien[0], vien[1], (r, c))


class TestBangTongHop(CoSo):
    def test_can_giua_doc_va_toi_thieu_24pt(self):
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')
        ws = openpyxl.load_workbook(f).active
        tong = next(r for r in range(in_an.DONG_DAU_BTH, 400) if ws.cell(r, 1).value == 'TỔNG CỘNG')
        self.assertGreater(tong, in_an.DONG_DAU_BTH)
        for r in range(in_an.DONG_DAU_BTH, tong + 1):
            self.assertGreaterEqual(ws.row_dimensions[r].height, in_an.CAO_DONG_BANG_TOI_THIEU)
            for c in range(1, 26):
                if r == tong and ws.cell(r, c).value is None:
                    continue                                    # dòng tổng: ô bị gộp không có chữ
                al = ws.cell(r, c).alignment
                self.assertEqual(al.vertical, 'center', (r, c))
                self.assertTrue(al.wrap_text, (r, c))

    def test_ho_ten_dai_du_cao(self):
        ten = 'Nguyễn Văn Một và bà Trần Thị Hai cùng các đồng thừa kế theo pháp luật của ông Nguyễn Văn Ba'
        with self.con:
            self.con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = 1', (ten,))
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth2.xlsx', ds_ma_ho=[1])
        ws = openpyxl.load_workbook(f).active
        r0 = in_an.DONG_DAU_BTH
        m = _vung(ws, r0, 2)
        r1 = m.max_row if m else r0
        tong = sum(ws.row_dimensions[r].height for r in range(r0, r1 + 1))
        ten_p, co, dam = in_an._phong(ws.cell(r0, 2))
        so = in_an.so_dong_o(ten, in_an._px_cot(ws, 26)[1] * 0.75 - 6, ten_p, co, dam)
        self.assertGreater(so, 1)
        self.assertGreaterEqual(tong, in_an.cao_dong_bang(so, co) - 0.01)


    def test_nguon_goc_qua_409pt_them_dong_cho_ho(self):
        # hộ một thửa, nguồn gốc rất dài: ô gộp theo hộ cần cao hơn 409 pt (trần Excel) -> thêm dòng cho hộ, không cắt chữ
        dai = ' '.join([NGUON_GOC] * 8)
        with self.con:
            self.con.execute('UPDATE thua SET nguon_goc = ? WHERE ma_ho = 1', (dai,))
        f = in_an.lap_bang_tong_hop(self.con, self.td / 'bth3.xlsx', ds_ma_ho=[1])
        ws = openpyxl.load_workbook(f).active
        r0 = in_an.DONG_DAU_BTH
        tong = next(r for r in range(r0, ws.max_row + 1) if ws.cell(r, 1).value == 'TỔNG CỘNG')
        # 16/10/2026: hộ cao hơn một trang được tách ở ranh trang - mỗi phần là một vùng gộp riêng, chữ nguồn gốc chia theo phần,
        # mỗi phần đủ cao cho chữ của nó
        px = in_an._px_cot(ws, 26)
        r, phan = r0, []
        while r < tong:
            m = _vung(ws, r, 23)
            r2 = m.max_row if m else r
            phan.append((r, r2))
            r = r2 + 1
        chu = ' '.join(str(ws.cell(a, 23).value or '') for a, _ in phan)
        self.assertEqual(' '.join(chu.split()), ' '.join(dai.split()))           # không mất chữ
        for a, b in phan:
            cao = [ws.row_dimensions[x].height for x in range(a, b + 1)]
            self.assertTrue(all(h <= in_an.CAO_TOI_DA for h in cao), cao)
            ten_p, co, dam = in_an._phong(ws.cell(a, 23))
            so = in_an.so_dong_o(ws.cell(a, 23).value, px[22] * 0.75 - 6, ten_p, co, dam)
            self.assertGreaterEqual(sum(cao), in_an.cao_dong_bang(so, co, None) - 0.01)
            self.assertEqual(ws.cell(a, 2).value, ws.cell(r0, 2).value)             # họ tên lặp ở mỗi phần
        self.assertIn(f'{tong - 1}', str(ws.cell(tong, 22).value))                 # công thức tổng tính tới dòng thêm cuối
        ngat = {b.id for b in ws.row_breaks.brk}
        self.assertTrue(all(b in ngat for _, b in phan[:-1]))                     # ranh các phần = ngắt trang


if __name__ == '__main__':
    unittest.main()
