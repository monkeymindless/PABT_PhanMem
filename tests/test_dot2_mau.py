"""Đợt 2 (kiểm toán 09/11/2026): màu chữ đạt AA ở hai tông; không thêm QColor('#hex') cố định (lớp lỗi ô Thành tiền)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

PABT = Path(__file__).resolve().parent.parent / 'pabt'

# mốc 10/11/2026: chỉ được GIẢM (màu vẽ bản đồ / biểu tượng / PDF cố định có chủ ý). Thêm màu cho mô hình bảng / delegate / QPainter:
# dùng qmau_theo_tong(màu gốc, 'nen' | 'chu') đọc lúc vẽ, không QColor('#…')
MOC_QCOLOR_HEX = {'giao_dien.py': 2, 'man_hinh.py': 3, 'man_hinh_ban_do.py': 5, 'man_hinh_may_chu.py': 1, 'man_hinh_nhan_wifi.py': 2,
                  'man_hinh_theo_doi.py': 6, 'man_hinh_tiep_nhan.py': 1, 'man_hinh_tim_nhanh.py': 1, 'pdf_du_phong.py': 1,
                  've_bieu_tuong.py': 10}
NEN_TOI = ('#1E293B', '#162033', '#0F172A')          # bảng / ô không sửa / nền cửa sổ tông Tối
NEN_SANG = ('#FFFFFF', '#F4F6F8')


def _do_sang(hex_):
    h = hex_.lstrip('#')
    kq = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        kq.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kq[0] + 0.7152 * kq[1] + 0.0722 * kq[2]


def tuong_phan(a, b):
    la, lb = sorted((_do_sang(a), _do_sang(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TestMauDot2(unittest.TestCase):
    def test_khong_them_qcolor_hex(self):
        vuot = {}
        for f in sorted(PABT.glob('*.py')):
            n = len(re.findall(r"QColor\(\s*['\"]#[0-9A-Fa-f]{3,8}['\"]", f.read_text(encoding='utf-8')))
            if n > MOC_QCOLOR_HEX.get(f.name, 0):
                vuot[f.name] = (n, MOC_QCOLOR_HEX.get(f.name, 0))
        self.assertEqual(vuot, {}, "QColor('#…') cố định không đổi theo tông: dùng qmau_theo_tong (tên file: (hiện có, mốc))")

    def test_bang_doi_chu_toi_dat_aa(self):
        from pabt.giao_dien import TOI_CHU
        kem = {k: (v, round(min(tuong_phan(v, n) for n in NEN_TOI), 2)) for k, v in TOI_CHU.items()
               if min(tuong_phan(v, n) for n in NEN_TOI) < 4.5}
        self.assertEqual(kem, {}, 'màu chữ tông Tối dưới 4,5:1 trên nền tối')

    def test_token_chu_trang_thai_dat_aa_ca_hai_tong(self):
        from pabt.giao_dien import TOI_CHU, TOKEN
        for k in ('canh_bao_chu', 'thanh_cong_chu', 'nguy_hiem_chu', 'chu', 'chu_phu'):
            mau = TOKEN[k]
            for n in NEN_SANG:
                self.assertGreaterEqual(tuong_phan(mau, n), 4.5, f'{k} {mau} trên {n}')
            if k.endswith('_chu'):
                toi = TOI_CHU[mau.upper()]
                for n in NEN_TOI:
                    self.assertGreaterEqual(tuong_phan(toi, n), 4.5, f'{k} tông Tối {toi} trên {n}')

    def test_mau_da_sua_co_anh_xa_toi(self):
        """Nền / chữ của các màn hình đã sửa (M1-M8) đổi thật sang màu tối, không giữ màu sáng."""
        from pabt import giao_dien as g
        cu = g.TONG_NEN[0]
        g.TONG_NEN[0] = 'toi'
        try:
            for m in ('#F1F5F9', '#FFF6D6', '#ECFDF5', '#FFFBEB', '#EEF3FA', '#FFEBEE', '#F4F6F8'):
                self.assertLess(_do_sang(g.mau_theo_tong(m)), 0.05, f'nền {m} ở tông Tối')
            for m in ('#64748B', '#1D4ED8', '#B71C1C', '#B45309', '#475569', '#166534', '#B91C1C', '#1E3A5F', '#B83A3A'):
                self.assertGreaterEqual(tuong_phan(g.mau_theo_tong(m, 'chu'), '#1E293B'), 4.5, f'chữ {m} ở tông Tối')
        finally:
            g.TONG_NEN[0] = cu


if __name__ == '__main__':
    unittest.main()
