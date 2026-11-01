"""22/10/2026 (người dùng): "Ultra-Compact v1.0.11 + UI/UX Pro Max" - đổi bảng màu TOKEN (WCAG AAA), vòng focus 2 px trên ô nhập,
tiêu đề bảng navy có vạch dưới xanh hoàng gia, thẻ gạch chân 3 px, huy hiệu tổng cộng dồn vàng hổ phách. BỐ CỤC GIỮ NGUYÊN."""
from __future__ import annotations

import os
import re
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import giao_dien  # noqa: E402


def _quy_tac(qss: str, bo_chon: str) -> str:
    m = re.search(re.escape(bo_chon) + r'(?:\s*,[^{]*)?\s*\{([^}]*)\}', qss)
    return ' '.join(m.group(1).split()) if m else ''


def _do_tuong_phan(a: str, b: str) -> float:
    def sang(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((sang(a), sang(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


class TestBangMau(unittest.TestCase):
    def test_token(self):
        t = giao_dien.TOKEN
        self.assertEqual((t['chinh'], t['chinh_nhat'], t['nhan'], t['phu'], t['nguy_hiem']),
                         ('#1E3A5F', '#EFF6FF', '#2563EB', '#059669', '#DC2626'))       # 1.0.34 Flagship Sapphire
        self.assertEqual((t['chu'], t['chu_phu'], t['nen'], t['khung'], t['vach']),
                         ('#0F172A', '#475569', '#F3F6FA', '#FFFFFF', '#D5DEE8'))     # 1.0.35: PA1 Slate-Navy
        self.assertEqual(giao_dien.MAU_SO_KHONG, '#64748B')          # 1.0.42: WCAG AA ≥ 4,5:1 trên trắng
        self.assertEqual(giao_dien.MAU_VIEN_CHON, '#059669')            # viền vùng chọn kiểu Excel: Emerald Teal
        for mau, toi_thieu in ((t['chinh'], 6), (t['chu'], 7)):         # chữ chính: AAA (>= 7:1); xanh cobalt dịu (1.0.16): >= 6:1 (AA là 4,5)
            self.assertGreaterEqual(_do_tuong_phan(mau, '#FFFFFF'), toi_thieu)
            self.assertGreaterEqual(_do_tuong_phan(mau, t['nen']), toi_thieu)
        self.assertGreaterEqual(_do_tuong_phan('#FFFFFF', t['chinh']), 6)   # chữ trắng trên tiêu đề bảng cobalt dịu
        self.assertNotIn('#0F3866', giao_dien._qss_day_du())              # không còn navy cũ

    def test_vong_focus_o_nhap(self):
        qss = giao_dien._qss_day_du()
        thuong = _quy_tac(qss, 'QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit')
        for chu in ('border: 1px solid #8696AB', 'border-radius: 6px', 'padding: 4px 8px', 'background: #FFFFFF', 'color: #0F172A'):
            self.assertIn(chu, thuong)
        focus = _quy_tac(qss, 'QLineEdit:focus')
        self.assertIn('border: 2px solid #2563EB', focus)
        self.assertIn('background: #FFFFFF', focus)
        self.assertIn('padding: 3px 7px', focus)                          # viền dày thêm 1 px: chữ không nhảy
        for bo_chon in ('QComboBox:focus', 'QSpinBox:focus', 'QPlainTextEdit:focus'):
            self.assertIn(bo_chon, qss)
        self.assertIn('2px solid #2563EB', _quy_tac(qss, 'QWidget[hang_nhap="1"] QLineEdit:focus'))
        self.assertIn('2px solid #2563EB', _quy_tac(qss, 'QComboBox[loc_ds="1"]:focus'))

    def test_tieu_de_bang(self):
        qss = giao_dien._qss_day_du()
        td = _quy_tac(qss, 'QHeaderView::section:horizontal')
        for chu in ('background: #1E3A5F', 'color: #FFFFFF', 'font-weight: 600', 'border-right: 1px solid #152C48',
                    'border-bottom: 2px solid #2563EB'):
            self.assertIn(chu, td)
        self.assertIn(f'min-height: {giao_dien.CAO_TIEU_DE_BANG - 10}px', td)    # chiều cao tiêu đề giữ nguyên
        chon = _quy_tac(qss, 'QTableView::item:selected')
        self.assertIn('background: #DBEAFE', chon)
        self.assertIn('color: #0F172A', chon)

    def test_the_gach_chan_va_tong_dinh_danh(self):
        qss = giao_dien._qss_day_du()
        self.assertIn('font-weight: 600; font-size: 13px', _quy_tac(qss, 'QTabBar[vai="gach_chan"]'))
        chon = _quy_tac(qss, 'QTabBar[vai="gach_chan"]::tab:selected')
        for chu in ('color: #2563EB', 'border-bottom: 3px solid #2563EB', 'background: #FFFFFF'):
            self.assertIn(chu, chon)
        self.assertNotIn('font', chon)                                    # phông chỉ ở mức QTabBar (Qt5 cắt chữ)
        self.assertIn('border-bottom: 3px solid transparent', _quy_tac(qss, 'QTabBar[vai="gach_chan"]::tab'))  # không đổi cao
        tong = _quy_tac(qss, 'QLabel#tong_dinh_danh')
        for chu in ('background: #FEF3C7', 'border: 1px solid #E5A93A', 'color: #7C4A12', 'Consolas', 'font-weight: 700',
                    'border-radius: 5px', 'padding: 2px 10px'):
            self.assertIn(chu, tong)

    def test_bo_cuc_giu_nguyen(self):
        from pabt import app, man_hinh
        self.assertEqual(app.CuaSoChinh.CAO_THE_SO, 62)                  # không nới thẻ (màn 21" chừa bảng hộ)
        self.assertEqual(app.CAO_DAI_CONG_CU, 32)
        self.assertEqual(man_hinh.CAO_DAI_DINH_DANH, 38)
        self.assertEqual(man_hinh.CAO_DONG_MUC, 36)
        self.assertEqual(giao_dien.CAO_DONG_BANG, 30)


if __name__ == '__main__':
    unittest.main()
