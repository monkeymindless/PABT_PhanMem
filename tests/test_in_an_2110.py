"""Bản in 21/10/2026 (người dùng: "bảng tổng hợp A3 / phương án chi tiết tràn trang, trang trước còn trống nhiều"). Số liệu GIẢ LẬP.
- Bảng tổng hợp: cột số toàn 0 thu hẹp nhường cột nguồn gốc; dòng thửa cao chia nhiều dòng Excel; xếp trang theo từng dòng - mọi trang
  trừ trang cuối lấp >= 85%; tổ chức có Thửa 16 + 17 nguồn gốc dài.
- Phương án chi tiết bản Word (in_word): lề NĐ 30, hàng tiêu đề lặp (tblHeader), dòng dài được cắt qua trang, khối cuối không tách.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl                                                                  # noqa: E402
from PySide6.QtWidgets import QApplication                                       # noqa: E402

from pabt import du_lieu_in
from pabt import csdl, dia_phuong, in_an, in_word                                # noqa: E402

CAU = 'Đất giả lập do Ủy ban nhân dân xã quản lý, sử dụng ổn định từ năm 1995, không tranh chấp, phù hợp quy hoạch sử dụng đất. '
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _du_an(td: Path, n_truoc: int, k: int, n_sau: int = 6) -> Path:
    """n_truoc hộ một thửa, tổ chức "UBND xã Mẫu" có Thửa 16 và 17 (nguồn gốc riêng từng thửa, k câu), n_sau hộ."""
    from pabt import du_an_moi
    dong = [dict(ho_ten=f'Hộ trước {i}', dia_chi='Ấp 1', so_to='3', so_thua=str(200 + i), loai_dat='CLN', dt_thu_hoi=str(100 + i),
                 vi_tri='1') for i in range(n_truoc)]
    dong += [dict(ho_ten='UBND xã Mẫu', dia_chi='Ấp 2', so_to='9', so_thua=so, loai_dat='CLN', dt_thu_hoi='350', vi_tri='1')
             for so in ('16', '17')]
    dong += [dict(ho_ten=f'Hộ sau {i}', dia_chi='Ấp 3', so_to='4', so_thua=str(300 + i), loai_dat='CLN', dt_thu_hoi=str(80 + i),
                  vi_tri='1') for i in range(n_sau)]
    p = td / f'bth_{n_truoc}_{k}.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    con = csdl.mo(p)
    try:
        with con:
            for so in ('16', '17'):
                con.execute('UPDATE thua SET nguon_goc = ? WHERE so_thua = ?', (f'Thửa {so}: ' + CAU * k, so))
    finally:
        con.close()
    return p


def _trang(ws) -> list:
    ngat = sorted(b.id for b in ws.row_breaks.brk)
    m = re.search(r'\$?(\d+)$', str(ws.print_area or '').split(',')[0])
    dau, kq = 1, []
    for e in ngat + [int(m.group(1)) if m else ws.max_row]:
        kq.append((dau, e))
        dau = e + 1
    return kq


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        # đo chữ cố định (như test_in_vua_chu): offscreen không có phông Windows
        do = lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47)      # noqa: E731
        self._vo = mock.patch.object(in_an, '_ham_do_chu', lambda: do)
        self._vo.start()

    def tearDown(self):
        self._vo.stop()
        self.doCleanups()
        self.tmp.cleanup()

    def mo(self, p):
        con = csdl.mo(p)
        self.addCleanup(con.close)
        return con


class TestBangTongHopA3(_Co):
    def test_cot_khong_nhuong_cho_nguon_goc(self):
        con = self.mo(_du_an(self.td, 10, 14))
        from openpyxl.utils import get_column_letter as g
        K = dia_phuong.cot_mau(in_an.TEN_BTH)
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'moi.xlsx')).active
        with mock.patch.object(in_an, 'thu_cot_khong_bth', lambda *a, **k: 0.0):
            ws0 = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'cu.xlsx')).active

        def rong(w, k):
            return float(w.column_dimensions[g(K[k])].width)
        # dự án chỉ có đất: tài sản, cây trồng, ổn định đời sống, diện tích đất ở... toàn 0 -> thu hẹp
        for k in ('tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_on_dinh', 'dt_o'):
            self.assertLess(rong(ws, k), rong(ws0, k), k)
            self.assertGreaterEqual(rong(ws, k), in_an.RONG_COT_KHONG_BTH - 0.01, k)
        self.assertGreater(rong(ws, 'nguon_goc'), rong(ws0, 'nguon_goc') * 1.3)        # nguồn gốc rộng hơn rõ rệt
        self.assertEqual(int(ws.page_setup.scale), int(ws0.page_setup.scale))          # tổng bề rộng (tỷ lệ in) không đổi
        self.assertFalse(ws.sheet_properties.pageSetUpPr.fitToPage)                     # ngắt tay giữ hiệu lực
        chu_16 = con.execute("SELECT nguon_goc FROM thua WHERE so_thua = '16'").fetchone()[0]

        def so_dong_16(w):                              # số dòng chữ nguồn gốc Thửa 16 ở bề rộng cột nguồn gốc của bảng
            r = next(r for r in range(13, w.max_row + 1) if str(w.cell(r, K['so_thua']).value) == '16')
            ten, co, dam = in_an._phong(w.cell(r, K['nguon_goc']))
            return in_an.so_dong_o(chu_16, in_an._rong_vung(w, K['nguon_goc'], K['nguon_goc']), ten, co, dam)
        self.assertLess(so_dong_16(ws), so_dong_16(ws0) * 0.8)                           # ít dòng chữ hơn rõ rệt
        # chữ dài hơn 409 pt: chia nhiều dòng Excel gộp ô, đủ cao cho chữ (trước đây một dòng bị chặn 409 pt - mất chữ)
        cao = in_an._ham_cao(ws)
        r16 = next(r for r in range(13, ws.max_row + 1) if str(ws.cell(r, K['so_thua']).value) == '16')
        r17 = next(r for r in range(r16 + 1, ws.max_row + 1) if ws.cell(r, K['so_thua']).value)
        self.assertGreaterEqual(sum(cao(r) for r in range(r16, r17)),
                                in_an.cao_dong_bang(so_dong_16(ws), in_an._phong(ws.cell(r16, K['nguon_goc']))[1], None) - 0.5)

    def test_trang_lap_85_va_khong_dong_qua_409(self):
        gap_tach = 0
        for n in range(4, 40, 3):
            con = csdl.mo(_du_an(self.td, n, 18))
            ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / f'b{n}.xlsx')).active
            con.close()
            cao = in_an._ham_cao(ws)
            cap = in_an.cao_trang_in(ws)
            td = sum(cao(r) for r in range(9, 13))                 # hàng tiêu đề cột lặp đầu các trang sau
            trang = _trang(ws)
            for i, (a, b) in enumerate(trang[:-1]):
                dung = sum(cao(r) for r in range(a, b + 1)) + (td if a > 12 else 0)
                self.assertGreaterEqual(dung, 0.85 * cap, f'n={n} trang {i + 1}: {dung / cap:.0%}')
            self.assertTrue(all(cao(r) <= in_an.CAO_TOI_DA for r in range(13, ws.max_row + 1)), n)
            for a, b in trang[1:]:                                   # trang sau bắt đầu giữa hộ: lặp STT, họ tên
                if ws.cell(a, 2).value is None and a < trang[-1][1]:
                    continue
                if ws.cell(a, 2).value == 'UBND xã Mẫu':
                    gap_tach += 1
                    self.assertIsNotNone(ws.cell(a, 1).value)
            for m in ws.merged_cells.ranges:                         # không vùng gộp nào vắt qua ranh trang
                if m.min_row >= 13:
                    self.assertFalse(any(m.min_row <= e < m.max_row for _, e in trang[:-1]), f'n={n} {m}')
        self.assertGreater(gap_tach, 0)

    def test_hai_thua_cung_trang_khi_vua(self):
        # còn đủ chỗ: Thửa 16 và 17 cùng trang 1 với các hộ trước (không đẩy cả tổ chức sang trang sau)
        con = self.mo(_du_an(self.td, 3, 6, 2))
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'b.xlsx')).active
        K = dia_phuong.cot_mau(in_an.TEN_BTH)
        r16 = next(r for r in range(13, ws.max_row + 1) if str(ws.cell(r, K['so_thua']).value) == '16')
        r17 = next(r for r in range(13, ws.max_row + 1) if str(ws.cell(r, K['so_thua']).value) == '17')
        t = _trang(ws)
        trang_cua = lambda r: next(i for i, (a, b) in enumerate(t) if a <= r <= b)      # noqa: E731
        self.assertEqual(trang_cua(r16), 0)
        self.assertEqual(trang_cua(r17), 0)


def _xml(p: Path) -> ET.Element:
    with zipfile.ZipFile(p) as z:
        return ET.fromstring(z.read('word/document.xml'))


class TestWordNghiDinh30(_Co):
    def setUp(self):
        super().setUp()
        from tests.test_trang_1_khong_ho import _du_an as du_an_1_ho, GHI_CHU, NGUON
        self.con = self.mo(du_an_1_ho(self.td))
        with self.con:
            self.con.execute('UPDATE thua SET nguon_goc = ?', (NGUON * 20,))
            self.con.execute('UPDATE ct_dat SET ghi_chu = ?', (GHI_CHU * 2,))

    def test_khung_suon_mau_pa_01(self):
        """22/10/2026 (PDF mẫu PA_01): "Số: …" và "địa danh, ngày …" CÙNG MỘT HÀNG bảng đầu, cùng cỡ chữ và khoảng cách (hai dòng
        ngang nhau); dòng 3 tên đơn vị gạch chân thật (không còn "____"); đường kẻ ngắn căn giữa ngay dưới tên dự án."""
        x = _xml(in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx'))
        dau = next(iter(x.iter(W + 'tbl')))
        hang = list(dau.iter(W + 'tr'))
        self.assertEqual(len(hang), 2)
        o_so, o_ngay = [''.join(t.text or '' for t in c.iter(W + 't')) for c in hang[1].iter(W + 'tc')]
        self.assertTrue(o_so.startswith('Số:'))
        self.assertIn(' tháng ', o_ngay)
        cao = []
        for c in hang[1].iter(W + 'tc'):
            p0 = next(c.iter(W + 'p'))
            sp = p0.find(f'{W}pPr/{W}spacing')
            cao.append((sp.get(W + 'before'), sp.get(W + 'line'), p0.find(f'{W}r/{W}rPr/{W}sz').get(W + 'val')))
        self.assertEqual(cao[0], cao[1])                                             # cùng giãn, cùng cỡ chữ
        chu = ''.join(t.text or '' for t in x.iter(W + 't'))
        self.assertNotIn('____', chu)
        ps = list(x.iter(W + 'p'))
        i = next(k for k, p in enumerate(ps) if ''.join(t.text or '' for t in p.iter(W + 't')).startswith('Dự án'))
        vien = ps[i + 1].find(f'{W}pPr/{W}pBdr/{W}bottom')
        self.assertIsNotNone(vien)                                                   # GIỮ đường kẻ dưới tên dự án (23/10/2026)
        self.assertEqual(ps[i + 1].find(f'{W}pPr/{W}spacing').get(W + 'line'), str(in_word.DK_DU_AN_KHE_PT * 20))   # đoạn rỗng: đường kẻ CÁCH chữ một khe nhỏ
        ind = ps[i + 1].find(f'{W}pPr/{W}ind')
        self.assertEqual(ind.get(W + 'left'), ind.get(W + 'right'))                  # căn giữa
        self.assertAlmostEqual((in_word.rong_trang() - 2 * int(ind.get(W + 'left'))) / in_word.twip(10), in_word.DK_DU_AN_MM / 10, delta=0.05)

    def test_le_va_bang(self):
        p = in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx')
        x = _xml(p)
        mar = x.find(f'.//{W}sectPr/{W}pgMar')
        mm = {k: round(int(mar.get(W + k)) / 1440 * 25.4) for k in ('left', 'right', 'top', 'bottom')}
        self.assertEqual(mm, dict(left=9, right=7, top=10, bottom=10))
        sz = x.find(f'.//{W}sectPr/{W}pgSz')
        self.assertEqual((sz.get(W + 'w'), sz.get(W + 'h')), ('11906', '16838'))          # A4 dọc
        bang = [t for t in x.iter(W + 'tbl') if any(r.find(f'{W}trPr/{W}tblHeader') is not None for r in t.iter(W + 'tr'))]
        self.assertEqual(len(bang), 1)                                                    # bảng mục III
        hang = bang[0].findall(W + 'tr')                          # chỉ dòng của chính bảng (chữ ký là bảng LỒNG trong dòng cuối)
        self.assertIsNotNone(hang[0].find(f'{W}trPr/{W}tblHeader'))                      # hàng tiêu đề cột lặp mỗi trang
        self.assertTrue(all(h.find(f'{W}trPr/{W}tblHeader') is None for h in hang[1:]))

        def chu(h):
            return ''.join(t.text or '' for t in h.iter(W + 't'))

        def tach(h):
            return h.find(f'{W}trPr/{W}cantSplit').get(W + 'val')
        dong_11 = next(h for h in hang if chu(h).startswith('1.1'))
        self.assertEqual(tach(dong_11), '0')                    # ghi chú dài: Word được cắt qua trang
        tong = next(h for h in hang if 'TỔNG CỘNG' in chu(h))
        self.assertEqual(tach(tong), '1')
        self.assertIn('LẬP BIỂU', chu(x))
        # 22/10/2026: chữ ký là dòng cuối của bảng mục III (Word giữ liền TỔNG CỘNG + IV + chữ ký - bảng chữ ký riêng thì Word bỏ
        # qua keepNext, chữ ký trơ một trang); dòng không tách, ẩn viền trái / phải / dưới
        ky = hang[-1]
        self.assertIn('LẬP BIỂU', chu(ky))
        self.assertEqual(tach(ky), '1')
        iv = hang[-2]
        self.assertTrue(chu(iv).startswith('IV'))
        self.assertTrue(all(p.find(f'{W}pPr/{W}keepNext') is not None for p in iv.iter(W + 'p')))   # IV đi liền chữ ký
        o_ky = ky.findall(W + 'tc')
        self.assertEqual(len(o_ky), 1)                                              # MỘT ô gộp cả lưới, chứa bảng chữ ký ba cột
        self.assertEqual({e.tag.split('}')[1] for e in o_ky[0].find(f'{W}tcPr/{W}tcBorders')}, {'left', 'bottom', 'right'})
        ba = o_ky[0].find(W + 'tbl')                                                # LẬP BIỂU - KIỂM TRA - chức vụ ký (24/10/2026: dịch sang trái)
        cot = [int(c.get(W + 'w')) for c in ba.find(W + 'tblGrid')]
        self.assertEqual(len(cot), 4)                                               # ba phần + cột đệm bên phải
        self.assertEqual(sum(cot), in_word.rong_trang())
        tam = [cot[0] / 2, cot[0] + cot[1] / 2, cot[0] + cot[1] + cot[2] / 2]
        self.assertAlmostEqual(tam[1] - tam[0], tam[2] - tam[1], delta=2)           # ba tâm vẫn CÁCH ĐỀU nhau
        self.assertAlmostEqual(tam[2] - tam[1], in_word.rong_trang() / 3, delta=2)
        self.assertLess(tam[0], in_word.rong_trang() / 6)                           # và lệch về bên trái so với chia ba đều
        for tc in ba.iter(W + 'tc'):
            self.assertEqual({p.find(f'{W}pPr/{W}jc').get(W + 'val') for p in tc.iter(W + 'p')}, {'center'})   # chữ nằm giữa từng phần
        self.assertIn('120,0', chu(dong_11))
        self.assertIn('40.000.000', chu(tong))                 # đất 30 triệu + thưởng + hỗ trợ
        self.assertNotIn('DỰ THẢO', chu(x))

    def test_du_thao_khong_chu_ky(self):
        x = _xml(in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'dt.docx', du_thao=True))
        s = ''.join(t.text or '' for t in x.iter(W + 't'))
        self.assertIn('(DỰ THẢO)', s)
        self.assertNotIn('LẬP BIỂU', s)

    def test_xuat_bo_ho_so_va_hop_in(self):
        from pabt import van_ban_trinh as vb
        kq = vb.xuat_bo_ho_so(self.con, [1], self.td / 'hs', bang_tong_hop=False)
        self.assertEqual([p.suffix for p in kq['word']], ['.docx'])                    # 22/10/2026: mặc định bản Word
        self.assertEqual(kq['excel'], [])                                              # không còn bản Excel chi tiết
        self.assertEqual(list((self.td / 'hs').rglob('*.xlsx')), [])
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, ma_ho_chon=[1], file_du_an=str(self.td / 'x.pabt'), che_do='chinh_thuc')
        self.addCleanup(h.close)
        self.assertTrue(h.o_word.isChecked())                                           # luôn Word, ô ẩn
        self.assertFalse(h.o_word.isVisibleTo(h))
        self.assertIn('Word', h.o_ct.text())
        for o in (h.o_bth, h.o_tt, h.o_bc):
            o.setChecked(False)
        h.r_excel.setChecked(True)
        h.o_thu_muc.setText(str(self.td / 'hop'))
        kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual(len(kq['word']), 1)
        self.assertTrue(kq['word'][0].exists())

    def test_1000_ho_nhanh(self):
        # 1.000 file .docx: chỉ dựng chuỗi XML (không Word) - mỗi hộ vài ms
        import time
        t = time.perf_counter()
        for i in range(50):
            in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'nhieu' / f'{i}.docx')
        self.assertLess((time.perf_counter() - t) / 50 * 1000, 60.0)                 # < 60 s cho 1.000 hộ


class TestLamSachDoanVan(unittest.TestCase):
    """Xuống dòng cứng giữa câu (ô Excel nhập vào: "Đoàn / Thanh niên", "chủ hợp / đồng") nối lại; đoạn mới chỉ ở gạch đầu dòng /
    hết câu / dòng trống."""

    def test_noi_giua_cau_giu_doan(self):
        from pabt.ho_so import lam_sach_doan_van
        chu = ('Căn cứ Giấy xác nhận của Đoàn\nThanh niên xã, đất do ông A nhận chuyển nhượng theo chủ hợp\nđồng năm 1995 được UBND '
               'tỉnh\r\nĐồng Nai công nhận.\nĐất sử dụng gồm:\n- đất ở\n- đất trồng cây\nlâu năm\n\nGhi chú khác\u2028tiếp theo.')
        self.assertEqual(lam_sach_doan_van(chu), [
            'Căn cứ Giấy xác nhận của Đoàn Thanh niên xã, đất do ông A nhận chuyển nhượng theo chủ hợp đồng năm 1995 được UBND tỉnh '
            'Đồng Nai công nhận.',
            'Đất sử dụng gồm:', '- đất ở', '- đất trồng cây lâu năm', 'Ghi chú khác tiếp theo.'])
        self.assertEqual(lam_sach_doan_van(''), [])


class TestNghiDinh30CoChu(_Co):
    """Phương án chi tiết bản Word: Mục II không cụt chữ giữa câu; trích yếu "VÀ"; cỡ chữ Phụ lục I NĐ 30 (w:sz = 2 x pt)."""

    def setUp(self):
        super().setUp()
        from tests.test_trang_1_khong_ho import _du_an as du_an_1_ho
        self.con = self.mo(du_an_1_ho(self.td))
        with self.con:
            self.con.execute('UPDATE thua SET nguon_goc = ?', (
                'Căn cứ Giấy xác nhận của Đoàn\nThanh niên xã giả lập, đất do hộ nhận chuyển nhượng theo chủ hợp\nđồng năm 1995, '
                'được UBND tỉnh\nĐồng Nai công nhận.\nĐất sử dụng gồm:\n- đất ở\n- đất trồng cây lâu năm',))

    def _cac_doan(self, x) -> list:
        """[(chữ, w:p)] các đoạn ngoài bảng."""
        than = x.find(f'{W}body')
        return [(''.join(t.text or '' for t in p.iter(W + 't')), p) for p in than.findall(f'{W}p')]

    def _co_gach_ho(self, x, chu) -> bool:
        """Đoạn chứa đúng chữ chu có viền dưới cách chữ >= 1 pt (w:space) - gạch chân hở, không dùng gạch chân sát chữ của Word."""
        for p in x.iter(W + 'p'):
            if ''.join(t.text or '' for t in p.iter(W + 't')) == chu:
                b = p.find(f'{W}pPr/{W}pBdr/{W}bottom')
                return b is not None and int(b.get(W + 'space')) >= 1
        return False

    def _co_gach_ngan(self, x, chu) -> bool:
        """24/10/2026: đường gạch dưới chữ chu là ĐOẠN RỖNG liền sau (viền dưới), thụt hai bên cho NGẮN hơn chữ (không làm chữ bẻ dòng)."""
        ps = list(x.iter(W + 'p'))
        for i, p in enumerate(ps[:-1]):
            if ''.join(t.text or '' for t in p.iter(W + 't')) == chu:
                q = ps[i + 1]
                return (q.find(f'{W}pPr/{W}pBdr/{W}bottom') is not None and not any(True for _ in q.iter(W + 't'))
                        and int(q.find(f'{W}pPr/{W}ind').get(W + 'left')) > 0)
        return False

    def _sz(self, x, chu) -> tuple:
        """(cỡ w:sz, đậm, nghiêng, gạch chân) của w:r đầu tiên có chữ đúng bằng chu."""
        for r in x.iter(W + 'r'):
            if ''.join(t.text or '' for t in r.iter(W + 't')) == chu:
                pr = r.find(W + 'rPr')
                return (pr.find(W + 'sz').get(W + 'val'), pr.find(W + 'b') is not None, pr.find(W + 'i') is not None,
                        pr.find(W + 'u') is not None)
        self.fail(f'không thấy "{chu}"')

    def test_muc_ii_khong_cut_giua_cau(self):
        p = in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx')
        x = _xml(p)
        self.assertEqual(list(x.iter(W + 'br')), [])                                 # không ngắt dòng cứng nào
        doan = self._cac_doan(x)
        i = next(k for k, (c, _) in enumerate(doan) if c.startswith('II.'))
        ii = [(c, p) for c, p in doan[i + 1:i + 4]]
        self.assertEqual([c for c, _ in ii], [
            'Căn cứ Giấy xác nhận của Đoàn Thanh niên xã giả lập, đất do hộ nhận chuyển nhượng theo chủ hợp đồng năm 1995, được '
            'UBND tỉnh Đồng Nai công nhận.', 'Đất sử dụng gồm:', '- đất ở'])
        for c, pp in ii:
            self.assertNotIn('\n', c)
            pr = pp.find(W + 'pPr')
            self.assertEqual(pr.find(W + 'jc').get(W + 'val'), 'both')
            sp = pr.find(W + 'spacing')
            self.assertEqual((sp.get(W + 'before'), sp.get(W + 'line'), sp.get(W + 'after')), ('0', '240', '120'))  # đơn, cách 6 pt
            ind = pr.find(W + 'ind')
            # 22/10/2026 (PDF mẫu PA_01): MỌI đoạn, kể cả gạch đầu dòng, thụt dòng đầu 1 cm, dòng sau về sát lề trái
            self.assertEqual((ind.get(W + 'firstLine'), ind.get(W + 'left'), ind.get(W + 'hanging')), (str(in_word.THUT_DAU), None, None))

    def test_dau_van_ban_lan_le_va_cot_theo_noi_dung(self):
        """22/10/2026 (xuất thử dự án thật so với mẫu PA_01): bảng đầu văn bản lấn lề để "TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT" 13 pt một dòng
        (trước bẻ 3 dòng); cột bảng mục III theo nội dung - ghi chú dài được rộng hơn tỷ lệ cố định 14%, cột số vừa số dài nhất."""
        x = _xml(in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx'))
        dau = next(iter(x.iter(W + 'tbl')))
        self.assertEqual(in_word.LAN_LE_DAU_MM, (0, 0))                              # lề 1,5 / 1 cm đã hẹp: không lấn nữa
        rong = sum(int(c.get(W + 'w')) for c in dau.iter(W + 'gridCol'))
        self.assertEqual(rong, in_word.rong_trang())
        r1 = in_word.rong_cot_dau()[0]
        self.assertGreaterEqual((r1 - 2 * 57) / 20, in_word._rong_uoc('TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT', 13))
        # cột theo nội dung
        co_dinh = in_word.rong_cot()
        chu = {0: [('1', True), ('1.1', False)], 1: [('Bồi thường đất', True), ('Thửa đất số 17, tờ bản đồ số 39', False)],
               2: [('m²', False)], 3: [('120,0', False)], 4: [('250.000', False)], 5: [('100%', False)],
               6: [('30.000.000', False), ('40.000.000', True)], 7: [('', True), ('Đất do UBND xã quản lý theo nội dung xác nhận '
                                                                            'nguồn gốc đất, không tính bồi thường về đất ' * 2, False)]}
        ds = in_word.rong_cot(chu)
        self.assertEqual(sum(ds), in_word.rong_trang())
        self.assertGreater(ds[7], co_dinh[7])
        for k, (c, d) in ((6, ('40.000.000', True)), (4, ('250.000', False)), (3, ('120,0', False))):
            self.assertGreaterEqual(ds[k] / 20 - 2 * in_word.LE_O / 20, in_word._rong_chu(c, in_word.CO_BANG, d))
        bang = [t for t in x.iter(W + 'tbl') if any(r.find(f'{W}trPr/{W}tblHeader') is not None for r in t.iter(W + 'tr'))][0]
        luoi = [int(c.get(W + 'w')) for c in bang.find(W + 'tblGrid')]
        self.assertEqual(sum(luoi), in_word.rong_trang())
        self.assertNotEqual(luoi, co_dinh)                                           # bản in thật dùng bề rộng theo nội dung

    def test_trich_yeu_va_va_co_chu(self):
        x = _xml(in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx', du_thao=True))
        chu = ''.join(t.text or '' for t in x.iter(W + 't'))
        self.assertEqual(' '.join(in_word.TRICH_YEU_DONG), in_word.TRICH_YEU)
        self.assertEqual(len(in_word.TRICH_YEU_DONG), 1)                             # PDF mẫu PA_01: một dòng, chữ "&"
        self.assertIn('HỖ TRỢ & TÁI ĐỊNH CƯ', chu)
        da = du_lieu_in._thong_tin_du_an(self.con)
        cq = str(da['DON_VI_TIEU_DE']).upper()
        # 22/10/2026 (người dùng): cơ quan, quốc hiệu, số 13; tiêu ngữ, ngày, trích yếu, dự án, nội dung, bảng 14; tên loại 15
        self.assertEqual(self._sz(x, 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'), ('21', True, False, False))   # 10,5 pt đậm (mẫu PDF 23/10/2026)
        self.assertEqual(self._sz(x, 'Độc lập - Tự do - Hạnh phúc'), ('21', True, False, False))      # 10,5 pt đậm
        self.assertTrue(self._co_gach_ho(x, 'Độc lập - Tự do - Hạnh phúc'))                          # gạch chân HỞ (viền đoạn), không sát chữ
        self.assertEqual(self._sz(x, cq), ('21', True, False, False))                                   # dòng 3 đậm
        self.assertTrue(self._co_gach_ngan(x, cq))                                                   # gạch dưới CHI NHÁNH: đoạn riêng, ngắn hơn chữ 1 cm
        vua = (in_word.rong_cot_dau()[0] - 2 * 57) / 20
        for d in (da['DON_VI_CAP_TREN_2DONG'] or '').split('\n'):
            for p in in_word._ngat_can_bang(d.strip().upper(), vua, in_word.CO_CO_QUAN) if d.strip() else ():
                self.assertEqual(self._sz(x, p), ('21', False, False, False))                           # cơ quan chủ quản
        self.assertEqual(self._sz(x, '(DỰ THẢO)'), ('21', True, False, False))                          # đậm, cùng cỡ dòng Số / ngày
        ngay = next(t.text for t in x.iter(W + 't') if (t.text or '').find(' tháng ') > 0)
        self.assertEqual(self._sz(x, ngay), ('21', False, True, False))                                # địa danh, ngày nghiêng
        self.assertEqual(self._sz(x, 'PHƯƠNG ÁN CHI TIẾT'), ('21', True, False, False))
        for d in in_word.TRICH_YEU_DONG:
            self.assertEqual(self._sz(x, d), ('21', True, False, False))
        self.assertEqual(in_word._ngat_can_bang('TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT', 176, 13),
                         ['TRUNG TÂM PHÁT', 'TRIỂN QUỸ ĐẤT'])                         # không để "ĐẤT" trơ một dòng
        self.assertEqual(in_word._ngat_can_bang('CHI NHÁNH VĨNH CỬU', 176, 13, True), ['CHI NHÁNH VĨNH CỬU'])
        self.assertEqual(self._sz(x, f'Dự án {str(da["du_an"])}'), ('21', True, False, False))
        for tieu_de in (du_lieu_in.TIEU_DE_MUC_I_HO, du_lieu_in.TIEU_DE_MUC_II,
                        'III. Bảng tính toán bồi thường, hỗ trợ'):
            self.assertEqual(self._sz(x, tieu_de)[:2], ('21', True))
        self.assertEqual(self._sz(x, 'STT'), ('20', True, False, False))                              # bảng 10 pt
        so_r = next(t.text for t in x.iter(W + 't') if (t.text or '').startswith('Số:'))
        self.assertEqual(self._sz(x, so_r), ('21', False, False, False))                              # số ký hiệu 13 pt, cùng cỡ dòng ngày

    def test_noi_dung_va_chu_ky_14_khong_doan_rong(self):
        x = _xml(in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx'))
        self.assertEqual(self._sz(x, 'LẬP BIỂU'), ('21', True, False, False))                         # khối chữ ký
        self.assertEqual(self._sz(x, 'Đất sử dụng gồm:'), ('21', False, False, False))               # nguồn gốc mục II
        self.assertEqual(self._sz(x, 'Họ và tên:')[:2], ('21', False))                                 # mục I, nhãn thường
        ten = du_lieu_in._thong_tin_ho(self.con, 1, du_lieu_in._thong_tin_du_an(self.con))['ho_ten']
        self.assertEqual(self._sz(x, ten)[:2], ('21', True))                                         # tên chủ hộ đậm
        self.assertEqual(self._sz(x, 'Địa chỉ thường trú:')[:2], ('21', False))
        doan = self._cac_doan(x)
        i2 = next(k for k, (c, _) in enumerate(doan) if c.startswith('II.'))
        i3 = next(k for k, (c, _) in enumerate(doan) if c.startswith('III.'))
        self.assertTrue(all(c.strip() for c, _ in doan[i2:i3]))                                      # không đoạn rỗng giữa mục II
        p3 = doan[i3][1].find(W + 'pPr')
        self.assertIsNone(p3.find(W + 'keepNext'))                                                   # mục III in tiếp ngay dưới II
        self.assertIsNone(p3.find(W + 'pageBreakBefore'))
        self.assertEqual(list(x.iter(W + 'pageBreakBefore')), [])


class TestLeA3VaLapDayNgang(_Co):
    """22/10/2026: bảng tổng hợp A3 lề trái 2,0 cm / phải 1,0 cm / trên, dưới 1,5 cm; cột lấp sát lề phải (phần hụt 70% nguồn gốc,
    15% họ tên, 15% địa chỉ); trích yếu "VÀ"; lam_sach_doan_van nối sau ; :; PDF dự phòng chi tiết lề NĐ 30."""

    def test_le_va_lap_day_ngang(self):
        con = self.mo(_du_an(self.td, 10, 3))
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx')).active
        m = ws.page_margins
        cm = {k: round(getattr(m, k) * 2.54, 2) for k in ('left', 'right', 'top', 'bottom')}
        self.assertEqual(cm, dict(left=2.0, right=1.0, top=1.5, bottom=1.5))
        self.assertAlmostEqual(cm['left'] - cm['right'], 1.0)                    # lề phải nhỏ hơn lề trái đúng 1 cm
        n_cot = max(dia_phuong.cot_mau(in_an.TEN_BTH).values())
        tong = sum(in_an._px_cot(ws, n_cot + 1)[:n_cot]) * 0.75              # cột hiện (cột ẩn = 0)
        ti_le = int(ws.page_setup.scale)
        vung = in_an.rong_in_a3(ws, ti_le, in_an.RONG_DU_PHONG_BTH)
        self.assertLessEqual(tong, vung + 0.5)                                    # không vượt khổ (Excel không tách cột)
        self.assertGreaterEqual(tong, vung - in_an.CHUA_SAU_BTH - 6)            # sát lề phải (trước: ~95% bề ngang)

    def test_ho_nhieu_thua_gop_doc(self):
        """Hộ 2 thửa (tổ chức "UBND xã Mẫu", Thửa 16 + 17): STT, họ tên, địa chỉ, tổng cộng, TĐC, ghi chú MỘT ô gộp dọc cả hộ (không
        lặp từng dòng); tờ, thửa, diện tích, tiền đất, nguồn gốc riêng từng dòng thửa."""
        con = self.mo(_du_an(self.td, 2, 1, 2))
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(con, self.td / 'bth.xlsx')).active
        K = dia_phuong.cot_mau(in_an.TEN_BTH)
        d0 = in_an.DONG_DAU_BTH
        r = [x for x in range(d0, d0 + 20) if str(ws.cell(x, K['so_thua']).value) in ('16', '17')]
        self.assertEqual(len(r), 2)
        r_dau, r_cuoi = r[0], r[-1]

        def vung(c):
            return next((m for m in ws.merged_cells.ranges if m.min_col == m.max_col == c and m.min_row <= r_dau <= m.max_row), None)
        for k in ('stt', 'ho_ten', 'dia_chi', 'tong', 'tai_dinh_cu', 'ghi_chu'):
            m = vung(K[k])
            self.assertIsNotNone(m, k)
            self.assertEqual((m.min_row, m.max_row), (r_dau, r_cuoi), k)
        self.assertEqual(ws.cell(r_dau, K['ho_ten']).value, 'UBND xã Mẫu')
        self.assertEqual(ws.cell(r_dau, K['stt']).alignment.horizontal, 'center')
        for k in ('stt', 'ho_ten', 'dia_chi', 'tong'):
            self.assertEqual(ws.cell(r_dau, K[k]).alignment.vertical, 'center', k)
        for k in ('so_to', 'so_thua', 'loai_dat', 'dt_thu_hoi', 'dt_nong_nghiep', 'tien_dat', 'nguon_goc'):
            self.assertIsNone(vung(K[k]), k)                                       # riêng từng thửa
        self.assertTrue(str(ws.cell(r_dau, K['nguon_goc']).value).startswith('Thửa 16'))
        self.assertTrue(str(ws.cell(r_cuoi, K['nguon_goc']).value).startswith('Thửa 17'))
        tien = [ws.cell(x, K['tien_dat']).value for x in (r_dau, r_cuoi)]
        self.assertEqual(tien, [350 * 250000, 350 * 250000])                     # tiền đất từng thửa
        self.assertGreaterEqual(ws.cell(r_dau, K['tong']).value, sum(tien))        # tổng cả hộ (đất + hỗ trợ, thưởng)

    def test_chia_phan_hut_70_15_15(self):
        from openpyxl import Workbook
        from openpyxl.utils import get_column_letter as g
        ws = Workbook().active
        ws.page_setup.paperSize, ws.page_setup.orientation = in_an.KHO_GIAY_BTH, 'landscape'
        in_an.chuan_le_trang(ws, 'tong_hop')
        K = dict(stt=1, ho_ten=2, dia_chi=3, nguon_goc=4)
        for c in range(1, 5):
            ws.column_dimensions[g(c)].width = 20
        ws.parent.save(self.td / 'a3.xlsx')                                       # đọc lại như bản in (khai báo cột có min / max)
        ws = openpyxl.load_workbook(self.td / 'a3.xlsx').active
        cong = in_an.lap_day_ngang_a3_bth(ws, 4, K)
        self.assertGreater(cong, 0)
        w = [float(ws.column_dimensions[g(c)].width) - 20 for c in range(1, 5)]
        self.assertEqual(w[0], 0)                                                 # STT không đổi
        self.assertAlmostEqual(w[3] / sum(w[1:]), 0.70, places=2)
        self.assertAlmostEqual(w[1] / sum(w[1:]), 0.15, places=2)
        self.assertAlmostEqual(w[2] / sum(w[1:]), 0.15, places=2)
        tong = sum(in_an._px_cot(ws, 5)[:4]) * 0.75
        self.assertAlmostEqual(tong, in_an.rong_in_a3(ws, in_an.TI_LE_BTH, in_an.RONG_DU_PHONG_BTH) - in_an.CHUA_SAU_BTH, delta=3)

    def test_trich_yeu_va_bang_tong_hop(self):
        from openpyxl import Workbook
        ws = Workbook().active
        ws['A5'] = 'BẢNG TỔNG HỢP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ & TÁI ĐỊNH CƯ'
        self.assertEqual(in_an.chuan_trich_yeu(ws), 1)
        self.assertEqual(ws['A5'].value, 'BẢNG TỔNG HỢP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ VÀ TÁI ĐỊNH CƯ')

    def test_noi_sau_cham_phay_hai_cham(self):
        from pabt.ho_so import lam_sach_doan_van
        self.assertEqual(lam_sach_doan_van('Đất nhận chuyển nhượng theo hợp đồng;\nsau đó tặng cho con là:\nông A  sử dụng   tới nay.'),
                         ['Đất nhận chuyển nhượng theo hợp đồng; sau đó tặng cho con là: ông A sử dụng tới nay.'])
        self.assertEqual(lam_sach_doan_van('Gồm các loại đất:\n- đất ở;\n- đất lúa.'), ['Gồm các loại đất:', '- đất ở;', '- đất lúa.'])


class TestDocxSangPdf(_Co):
    """1.0.19: PDF dự phòng (máy không có Word) dựng bằng Qt từ CHÍNH file .docx - không đọc Excel."""

    def test_pdf_du_phong_tu_chinh_file_docx(self):
        from pabt import van_ban_trinh as vb
        from tests.test_trang_1_khong_ho import _du_an as du_an_1_ho
        con = self.mo(du_an_1_ho(self.td))
        a = in_word.xuat_chi_tiet_docx(con, 1, self.td / 'PA_001.docx')
        loi, du = vb.pdf_du_phong_chi_tiet([('pdf', a, a.with_suffix('.pdf'))], [])
        self.assertEqual(du, [a.with_suffix('.pdf')])
        self.assertTrue(du[0].read_bytes().startswith(b'%PDF'))
        self.assertEqual(loi, [])
        self.assertEqual(list(self.td.rglob('*.xlsx')), [])                      # không lập file Excel nào

    def test_html_tu_docx_co_dong_chi_nhanh_va_bang(self):
        from pabt import docx_sang_pdf
        from tests.test_trang_1_khong_ho import _du_an as du_an_1_ho
        con = self.mo(du_an_1_ho(self.td))
        html, trang = docx_sang_pdf.html_tu_docx(in_word.xuat_chi_tiet_docx(con, 1, self.td / 'ct.docx'))
        self.assertIn('CHI NHÁNH', html)
        self.assertIn('<table', html)
        self.assertAlmostEqual(trang['rong_mm'], 210, delta=1)
        self.assertEqual(tuple(round(x) for x in trang['le']), (9, 10, 7, 10))                    # (trái, trên, phải, dưới) mm theo mẫu PDF 23/10/2026


class TestTieuDeMucI(_Co):
    """22/10/2026 (Phương án 2): tiêu đề mục I theo chủ sử dụng - hộ / cá nhân "I. Thông tin hộ gia đình, cá nhân" với Họ và tên,
    Số CCCD (kèm ngày cấp, nơi cấp), Địa chỉ thường trú, Số điện thoại; tổ chức "I. Thông tin tổ chức" chỉ Tổ chức + Địa chỉ (không
    CCCD / điện thoại). Cả bản .xlsx lẫn .docx. Tên, số GIẢ LẬP."""

    def _con(self, ho_ten: str):
        from tests.test_trang_1_khong_ho import _du_an as du_an_1_ho
        self._n = getattr(self, '_n', 0) + 1
        (self.td / f'd{self._n}').mkdir()
        con = self.mo(du_an_1_ho(self.td / f'd{self._n}'))
        with con:
            con.execute("UPDATE ho SET ho_ten = ?, so_cccd = '075000000001', ngay_cap = '01/01/2021', noi_cap = 'Cục CS QLHC', "
                        "dien_thoai = '0900000001', dia_chi = 'Ấp 1, xã Mẫu'", (ho_ten,))
        return con

    def _word(self, con) -> tuple:
        """(tiêu đề mục I (w:p), [chữ từng dòng bảng mục I])."""
        x = _xml(in_word.xuat_chi_tiet_docx(con, 1, self.td / 'ct.docx'))
        than = x.find(f'{W}body')
        con_cua = list(than)
        i = next(k for k, e in enumerate(con_cua)
                 if e.tag == W + 'p' and ''.join(t.text or '' for t in e.iter(W + 't')).startswith('I.'))
        bang = con_cua[i + 1]
        self.assertEqual(bang.tag, W + 'tbl')
        return con_cua[i], [''.join(t.text or '' for t in h.iter(W + 't')) for h in bang.iter(W + 'tr')]

    def test_tieu_de_theo_chu_su_dung(self):
        """24/10/2026: hộ gia đình, cá nhân -> "I. Thông tin về hộ gia đình, cá nhân"; tổ chức -> "I. Thông tin về tổ chức"."""
        for ho_ten, tieu_de in (('Nguyễn Văn Mẫu', 'I. Thông tin về hộ gia đình, cá nhân'),
                                ('Công ty TNHH Mẫu', 'I. Thông tin về tổ chức')):
            p, hang = self._word(self._con(ho_ten))
            self.assertEqual(''.join(t.text or '' for t in p.iter(W + 't')), tieu_de)
            self.assertIsNotNone(p.find(f'{W}r/{W}rPr').find(W + 'b'))
            if 'tổ chức' in tieu_de:
                self.assertTrue(hang[0].startswith('Tổ chức:'))
                self.assertFalse(any('CCCD' in x or 'điện thoại' in x for x in hang))
            else:
                self.assertTrue(any('CCCD' in x for x in hang))
        self.assertNotIn('thu hồi đất, tài sản', du_lieu_in.TIEU_DE_MUC_I_HO)


if __name__ == '__main__':
    unittest.main()
