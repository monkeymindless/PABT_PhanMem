"""1.0.80 (người dùng 07/11/2026, rà 23 điểm màu cứng ở tông Tối): 1.0.79 lấy màu phương án Navy vào hằng CHINH lúc nạp mã, nhãn ở tông Tối tối mờ
(tương phản 1,9-2,5). Màu viết trong bảng kiểu phải là màu GỐC để bảng đổi màu ánh xạ theo tông."""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pabt  # noqa: E402,F401
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication, QTableWidgetItem  # noqa: E402
from pabt import chu_de, giao_dien as g  # noqa: E402
from pabt.app import BangHo  # noqa: E402

qa = QApplication.instance() or QApplication([])
GOC = Path(g.__file__).parent
NEN_TOI = '#1E293B'


def tuong_phan(a: str, b: str) -> float:
    def lum(h):
        c = QColor(h)
        f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
        return 0.2126 * f(c.redF()) + 0.7152 * f(c.greenF()) + 0.0722 * f(c.blueF())
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class _TongToi(unittest.TestCase):
    def setUp(self):
        self.addCleanup(g.dat_tong_nen, g.TONG_NEN[0], False, False)
        self.addCleanup(chu_de.dat_phuong_an, chu_de.phuong_an_hien())
        g.dat_tong_nen('toi', ap_lai=False)


class TestBangKieu(_TongToi):
    def test_hang_mau_la_mau_goc(self):
        self.assertEqual((g.CHINH, g.CHINH_RE, g.MAU_GIA_K), (g.CHINH_GOC[0], g.CHINH_GOC[1], g.CHINH_GOC[0]))

    def test_nhan_sang_ro_o_moi_phuong_an(self):
        for ma in chu_de.PHUONG_AN_NAVY:
            chu_de.dat_phuong_an(ma)
            q = g._qss_day_du()
            mau = re.search(r'QLabel\[vai="nhan"\] \{ color: (#[0-9A-Fa-f]{6})', q).group(1)
            self.assertGreaterEqual(tuong_phan(mau, NEN_TOI), 4.5, ma)
            self.assertNotIn(chu_de.PHUONG_AN_NAVY[ma]['chinh'].upper(), q.upper().replace('#1E3A5F', ''), ma)

    def test_doi_phuong_an_doi_mau_nhan_tong_sang(self):
        g.dat_tong_nen('sang', ap_lai=False)
        ds = set()
        for ma in chu_de.PHUONG_AN_NAVY:
            chu_de.dat_phuong_an(ma)
            ds.add(re.search(r'QLabel\[vai="nhan"\] \{ color: (#[0-9A-Fa-f]{6})', g._qss_day_du()).group(1))
        self.assertGreater(len(ds), 1)          # hằng cũ giữ màu lúc nạp mã: đổi phương án nhãn không đổi


class TestOBang(_TongToi):
    def test_bang_ho_stt_trang_thai_theo_tong(self):
        m = BangHo([dict(ma_ho=1, o=[1, 'An', 'Ấp 1', 1, '1', 'Đã lập', '', *[''] * 11], tim='', nac=2, phu_ten='', ten_gon='An')])
        for c in (0, 1, 5):
            mau = m.data(m.index(0, c), Qt.ItemDataRole.ForegroundRole).color().name()
            self.assertGreaterEqual(tuong_phan(mau, NEN_TOI), 4.5, c)

    def test_o_gia_k_theo_tong(self):
        it = QTableWidgetItem('1')
        g._o_dam(it, g.MAU_GIA_K, Qt.AlignmentFlag.AlignRight)
        self.assertGreaterEqual(tuong_phan(it.foreground().color().name(), NEN_TOI), 4.5)

    def test_mau_moi_co_trong_bang_doi(self):
        for h in ('#1B5E20', '#B3261E', '#5F6368', '#107C41', '#BE123C', '#008000', '#800000', '#1F5FA0', '#3F6212', '#7C4A12', '#276348'):
            self.assertGreaterEqual(tuong_phan(g.mau_theo_tong(h, 'chu'), NEN_TOI), 4.5, h)
        for h in ('#FFF1F2', '#ECFCCB', '#FEF3C7', '#DCFCE7', '#FEE2E2', '#EFF6FF', '#EAF6EC'):
            self.assertLess(tuong_phan(g.mau_theo_tong(h, 'nen'), NEN_TOI), 2, h)     # nền sẫm, không còn mảng sáng


class TestTheKpi(_TongToi):
    def test_the_bao_cao_nen_theo_tong(self):
        from pabt.man_hinh_bao_cao import _QSS_THE
        q = g.ap_tong_nen(_QSS_THE.format(m='#1E3A5F'))
        self.assertNotIn('background: #FFFFFF', q)

    def test_tong_sang_khong_doi_thu_gi(self):
        g.dat_tong_nen('sang', ap_lai=False)
        self.assertEqual(g.mau_theo_tong('#A12A1F', 'chu'), '#A12A1F')
        self.assertEqual(g.mau_theo_tong('#008000', 'chu'), '#008000')
        self.assertEqual(g.mau_theo_tong('#FFF1F2', 'nen'), '#FFF1F2')


class TestKhongVietThangMau(unittest.TestCase):
    """Chặn tái phát: chữ HTML và màu ô bảng không viết thẳng mã màu (đọc mã nguồn; trang web điện thoại và bản in không theo tông)."""
    BO_QUA = {'nhan_wifi.py', 'pdf_du_phong.py', 'giao_dien.py', 'chu_de.py'}

    def _quet(self, mau):
        sai = []
        for p in sorted(GOC.glob('*.py')):
            if p.name in self.BO_QUA:
                continue
            for i, dong in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
                if re.search(mau, dong):
                    sai.append(f'{p.name}:{i}')
        return sai

    def test_chu_html(self):
        self.assertEqual(self._quet(r'<(?:span|b|td|div)[^>]*style="[^"]*(?<![-\w])color:\s*#[0-9A-Fa-f]{6}'), [])

    def test_o_bang(self):
        self.assertEqual(self._quet(r"set(?:Foreground|Background)\((?:QBrush\()?QColor\('#"), [])
        self.assertEqual(self._quet(r'setForeground\(Qt\.GlobalColor'), [])


class TestBienDich(unittest.TestCase):
    def test_moi_file_bien_dich_duoc(self):
        # f-string trùng loại dấu nháy: hợp lệ từ 3.12, lỗi cú pháp trên 3.8 của bản Windows 7; vermin không bắt. Lượt Qt5 chạy bài này bằng Python 3.8
        for p in sorted(GOC.glob('*.py')):
            compile(p.read_text(encoding='utf-8'), str(p), 'exec')


if __name__ == '__main__':
    unittest.main()
