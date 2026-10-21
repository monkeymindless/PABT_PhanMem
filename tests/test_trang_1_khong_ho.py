"""Bản in phương án chi tiết - trang 1 không hở (người dùng 21/10/2026: ngắt trang ngay sau dòng 1.1, mục 2-6 dồn sang trang 2).
Dòng mục không có dòng con là dòng tự do; cụm cuối chỉ từ TỔNG CỘNG; cân bằng 2 trang không làm trang 1 dưới 85%; gom 1 trang kết hợp
nén đệm dòng bảng + tỷ lệ >= 70%. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl                                                                  # noqa: E402
from PySide6.QtWidgets import QApplication                                       # noqa: E402

from pabt import canh_trang_in_an, csdl, in_an                                   # noqa: E402
from pabt.canh_trang_in_an import BoCanhTrangInAn                                # noqa: E402

GHI_CHU = ('Thửa đất giả lập do hộ gia đình sử dụng ổn định, không tranh chấp, phù hợp quy hoạch, được bồi thường theo quy định '
           'hiện hành; chữ ghi chú dài khoảng năm dòng trên bản in để dòng 1.1 cao như trường hợp thật.')
NGUON = 'Đất giả lập do hộ gia đình khai phá, sử dụng ổn định, không tranh chấp, đã kê khai đăng ký. '


def _du_an(td: Path) -> Path:
    """Một hộ, một thửa (ghi chú dài), mục 2, 3, 4 bằng 0 (không dòng con), mục 5 một dòng 5.1, thưởng."""
    from pabt import du_an_moi
    p = td / 'th.pabt'
    dong = [dict(ho_ten='Nguyễn Văn Thử', dia_chi='Ấp 1', so_to='5', so_thua='101', loai_dat='CLN', dt_thu_hoi='120',
                 vi_tri='1')]
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    con = csdl.mo(p)
    try:
        with con:
            con.execute('UPDATE ct_dat SET ghi_chu = ?', (GHI_CHU,))
            con.execute('DELETE FROM ct_khoan')
            con.execute("INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ma, ten, dvt, so_luong, don_gia, ty_le, cach_tinh) "
                        "VALUES (4, 1, 1, 'CS3', 'Hỗ trợ ổn định đời sống', 'nhân khẩu', '4', '1500000', '1', "
                        "'4 nhân khẩu x 30 kg gạo x 6 tháng x 15.000 đ')")
    finally:
        con.close()
    return p


def _cuoi_vung_in(ws) -> int:
    return int(re.search(r'(\d+)$', str(ws.print_area).split(',')[0]).group(1))


def _dong(ws) -> dict:
    """{loại / STT: dòng} của bảng mục III (cột loại dòng ẩn 30)."""
    kq = {}
    for r in range(1, ws.max_row + 1):
        stt = str(ws.cell(r, 1).value or '').strip()
        loai = ws.cell(r, 30).value
        if loai in ('H', 'I'):
            kq[stt] = r
        elif loai in ('R', 'T'):
            kq[loai] = r
    return kq


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.con = csdl.mo(_du_an(self.td))
        # đo chữ cố định (Times New Roman ~0,47 / 0,52 cỡ chữ - như test_in_vua_chu): offscreen không có phông Windows, chữ rộng gần
        # gấp đôi - phần đầu văn bản cao gấp rưỡi, không ra được trường hợp của người dùng
        do = lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47)      # noqa: E731
        self._vo = mock.patch.object(in_an, '_ham_do_chu', lambda: do)
        self._vo.start()

    def tearDown(self):
        self._vo.stop()
        self.con.close()
        self.tmp.cleanup()

    def lap(self, k: int, du_thao: bool, ten: str = ''):
        with self.con:
            self.con.execute('UPDATE thua SET nguon_goc = ?', (NGUON * k,))
        f = in_an.lap_chi_tiet(self.con, 1, self.td / f'{ten}{k}_{du_thao}.xlsx', du_thao=du_thao)
        return openpyxl.load_workbook(f).active


class TestCumDong(_Co):
    def test_muc_khong_dong_con_la_dong_tu_do_cum_cuoi_tu_tong_cong(self):
        ghi = {}
        goc = in_an.co_gian_vua_trang

        def bat(ws, khoi, *a, **k):
            ghi['khoi'] = khoi
            return goc(ws, khoi, *a, **k)
        with mock.patch.object(in_an, 'co_gian_vua_trang', bat):
            ws = self.lap(0, False)
        d = _dong(ws)
        kieu = {}
        for loai, doan in ghi['khoi']:
            for a, b in doan:
                for r in range(a, b + 1):
                    kieu[r] = (loai, doan[0][0], doan[-1][1])
        for stt in ('2', '3', '4'):                     # mục 2, 3, 4 (vật nuôi) không có dòng con: tự do, không dính mục kế
            self.assertEqual(kieu[d[stt]], ('tu_do', d[stt], d[stt]), stt)
        self.assertEqual(kieu[d['5']], ('lien', d['5'], d['5.1']))      # mục 5 dính dòng con 5.1
        self.assertEqual(kieu[d['R']][0], 'tu_do')                      # dòng thưởng không bị kéo vào cụm cuối
        self.assertEqual(kieu[d['T']][:2], ('lien', d['T']))            # cụm cuối bắt đầu từ TỔNG CỘNG
        self.assertEqual(kieu[d['T']][2], _cuoi_vung_in(ws))            # … tới hết vùng in


class TestTrang1(_Co):
    def _kiem(self, ws, nhan):
        """Nhiều trang: trang 1 lấp >= 85% vùng in; không ngắt ngay sau 1.1 khi dòng kế còn vừa trang 1; TỔNG CỘNG không mồ côi."""
        ngat = sorted(b.id for b in ws.row_breaks.brk)
        if not ngat:
            return 1
        cao = in_an._ham_cao(ws)
        cap = in_an.cao_trang_in(ws)
        d = _dong(ws)
        tren = sum(cao(r) for r in range(1, ngat[0] + 1))
        if ngat[0] >= d['1.1']:                         # ngắt trong bảng (không phải trước cụm "III." - ngoài phạm vi lỗi này)
            self.assertGreaterEqual(tren, 0.85 * cap, nhan)
            self.assertFalse(ngat[0] == d['1.1'] and tren + cao(d['1.1'] + 1) <= cap, nhan)
        self.assertNotEqual(ngat[-1] + 1, d['T'], nhan)
        return len(ngat) + 1

    def test_chinh_thuc_muc_2_den_5_1_lien_duoi_1_1(self):
        gap_hai_trang = 0
        for k in range(0, 40, 2):
            ws = self.lap(k, False)
            if self._kiem(ws, f'k={k}') > 1:
                gap_hai_trang += 1
        self.assertGreater(gap_hai_trang, 0)
        ws = self.lap(0, False, 'ngan')                 # nguồn gốc ngắn: cả mục 2 - 5.1 cùng trang với 1.1
        d = _dong(ws)
        self.assertFalse([b.id for b in ws.row_breaks.brk if d['1.1'] <= b.id < d['5.1']])

    def test_du_thao_an_chu_ky_va_gom_mot_trang(self):
        gom_nen = 0
        for k in range(0, 40, 2):
            ws = self.lap(k, True)
            self._kiem(ws, f'k={k}')
            r_ky = next((r for r in range(1, ws.max_row + 1)
                         if str(ws.cell(r, 2).value or ws.cell(r, 1).value or '').strip().upper() == 'LẬP BIỂU'), None)
            if r_ky is not None:
                self.assertTrue(ws.row_dimensions[r_ky].hidden, k)        # khối chữ ký bản dự thảo ẩn
            if not ws.row_breaks.brk and ws.parent.defined_names.get(in_an.TEN_DEM) is not None:
                # đã gom 1 trang nhờ nén đệm: chỉ thu tỷ lệ thì không vừa (2 trang)
                with mock.patch.object(BoCanhTrangInAn, 'thay_nen_gom', staticmethod(lambda *a, **kw: {})):
                    ws0 = self.lap(k, True, 'khong_nen')
                if ws0.row_breaks.brk:
                    gom_nen += 1
                    self.assertGreaterEqual(int(ws.page_setup.scale), in_an.TI_LE_CT_MIN)
                    self.assertEqual(ws.parent.defined_names[in_an.TEN_DEM].attr_text,
                                     str(int(round(canh_trang_in_an.DEM_GOM * 10))))
                    cao = in_an._ham_cao(ws)
                    self.assertLessEqual(sum(cao(r) for r in range(1, _cuoi_vung_in(ws) + 1)), in_an.cao_trang_in(ws) + 0.5)
        self.assertGreater(gom_nen, 0)


class TestCanhTrang(unittest.TestCase):
    def _ws(self, cao_dong):
        ws = openpyxl.Workbook().active
        ws.page_setup.paperSize, ws.page_setup.orientation = 9, 'portrait'
        in_an.chuan_le_trang(ws, 'chi_tiet')
        ws.page_setup.scale = 72
        for r, h in enumerate(cao_dong, start=1):
            ws.cell(r, 1).value = f'dòng {r}'
            ws.row_dimensions[r].height = h
        return ws

    def test_can_bang_khong_lam_trang_1_duoi_85(self):
        ws = self._ws([20])
        cap = in_an.cao_trang_in(ws)
        n = int(cap * 1.3 // 20)
        ws = self._ws([20] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        dau2 = trang[1][0]
        lui = int(0.2 * cap // 20) + 1                  # đầu mục cách ranh > 15% trang: không lùi (trước 21/10/2026: lùi tới 50%)
        self.assertIs(BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, [dau2 - lui]), trang)
        moi = BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, [dau2 - 2])
        self.assertEqual(moi[1][0], dau2 - 2)

    def test_gom_ket_hop_nen_dem_va_ti_le(self):
        ws = self._ws([20])
        cap = in_an.cao_trang_in(ws)
        n = int(cap // 30) + 4                          # dòng 30 pt (chữ 18,2 + đệm), tràn ~ 100 pt: thu tỷ lệ 72 -> 70% không đủ
        ws = self._ws([30.0] * n)
        trang = in_an.xep_trang(ws, [('tu_do', [(r, r) for r in range(1, n + 1)])], cap)
        self.assertEqual(len(trang), 2)
        san = {r: 18.2 + in_an.DEM_DONG - in_an.NEN_DEM for r in range(1, n + 1)}
        self.assertFalse(BoCanhTrangInAn.gom_mot_trang(self._ws([30.0] * n), trang, cap))     # không nén: giữ 2 trang
        self.assertTrue(BoCanhTrangInAn.gom_mot_trang(ws, trang, cap, None, list(range(1, n + 1)), san))
        self.assertAlmostEqual(ws.row_dimensions[1].height, 18.2 + canh_trang_in_an.DEM_GOM, places=1)
        self.assertGreaterEqual(int(ws.page_setup.scale), in_an.TI_LE_CT_MIN)
        self.assertEqual(ws.row_breaks.brk, [])
        self.assertEqual(ws.parent.defined_names[in_an.TEN_DEM].attr_text, '25')


if __name__ == '__main__':
    unittest.main()
