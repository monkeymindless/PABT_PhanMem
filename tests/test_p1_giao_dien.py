"""Nhóm P1 (03/11/2026): token màu, thang cỡ chữ, nhãn trợ năng, chiều cao dòng bảng.

Bài kiểm "mốc" (ratchet): số mã màu viết thẳng (#RRGGBB) của từng file không được TĂNG so với MOC_MAU - màu mới dùng TOKEN /
dat_kieu_theo_tong / mau_o_theo_tong của giao_dien. Giảm được thì hạ mốc xuống cho khỏi tăng lại."""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

GOC = Path(__file__).resolve().parent.parent / 'pabt'
RE_HEX = re.compile(r'#[0-9A-Fa-f]{6}\b')
# file được viết màu thẳng: hệ màu (giao_dien, chu_de), vẽ biểu tượng / bản đồ, trang web điện thoại, xem trước giấy in
TU_DO = {'giao_dien.py', 'chu_de.py', 've_bieu_tuong.py', 'nhan_wifi.py', 'phieu_kiem_dem.py'}
MOC_MAU = {
    'man_hinh_phien_ban.py': 4, 'man_hinh_the_muc.py': 14, 'man_hinh_ap_gia_nhanh.py': 2,
    'app.py': 39, 'ban_do_cad.py': 16, 'ban_do_kml.py': 1, 'lich_su_cap_nhat.py': 1, 'man_hinh.py': 54,
    'man_hinh_ban_do.py': 19, 'man_hinh_bao_cao.py': 19, 'man_hinh_cap_nhat.py': 2, 'man_hinh_cay.py': 24,
    'man_hinh_chan_doan.py': 5, 'man_hinh_don_gia.py': 4, 'man_hinh_don_gia_rieng.py': 2, 'man_hinh_du_an_moi.py': 2,
    'man_hinh_du_thao.py': 25, 'man_hinh_du_toan.py': 25, 'man_hinh_ghep_cot.py': 4, 'man_hinh_gia_dat.py': 2,
    'man_hinh_goi_don_vi.py': 2, 'man_hinh_ho_so.py': 26, 'man_hinh_kiem_toan.py': 3, 'man_hinh_may_chu.py': 3,
    'man_hinh_nhan_wifi.py': 6, 'man_hinh_nhap_don_gia.py': 9, 'man_hinh_ocr.py': 5, 'man_hinh_quan_ly.py': 8,
    'man_hinh_quy_trinh.py': 1, 'man_hinh_theo_doi.py': 38, 'man_hinh_thong_ke.py': 6, 'man_hinh_tiep_nhan.py': 8,
    'man_hinh_tim_nhanh.py': 1, 'man_hinh_tong_quan.py': 63, 'man_hinh_xuat_ban.py': 11, 'pdf_du_phong.py': 3,
    'thanh_tieu_de.py': 12, 'xem_truoc_tai_lieu.py': 23,
}
# setStyleSheet riêng có màu viết thẳng (không đổi theo tông nền) chỉ được ở các file này: khung tiêu đề tự đổi màu theo tông,
# ô xem trước các tông (phải hiện ĐÚNG màu của từng tông), khung xem ảnh / trang giấy (nền tối cố định, trang luôn trắng)
KIEU_THANG_DUOC = {'giao_dien.py', 'thanh_tieu_de.py', 'man_hinh_giao_dien.py', 'nhan_wifi.py', 'man_hinh_ocr.py'}
RE_GOI_KIEU = re.compile(r'\.setStyleSheet\(')


def _doc(p: Path) -> str:
    return p.read_text(encoding='utf-8')


def _doi_so(s: str, i: int) -> str:
    """Chữ đối số của lời gọi có ngoặc mở tại s[i]."""
    sau, nhay, j = 0, None, i
    while j < len(s):
        ch = s[j]
        if nhay:
            if ch == '\\':
                j += 2
                continue
            if ch == nhay:
                nhay = None
        elif ch in '\'"':
            nhay = ch
        elif ch == '(':
            sau += 1
        elif ch == ')':
            sau -= 1
            if sau == 0:
                return s[i + 1:j]
        j += 1
    return s[i + 1:]


class TestTokenMau(unittest.TestCase):
    def test_khong_tang_mau_viet_thang(self):
        tang = []
        for p in sorted(GOC.glob('*.py')):
            if p.name in TU_DO:
                continue
            n = len(RE_HEX.findall(_doc(p)))
            if n > MOC_MAU.get(p.name, 0):
                tang.append(f'{p.name}: {n} mã màu (mốc {MOC_MAU.get(p.name, 0)})')
        self.assertEqual(tang, [], 'Màu mới: dùng giao_dien.TOKEN / dat_kieu_theo_tong / mau_o_theo_tong thay vì viết #RRGGBB')

    def test_kieu_rieng_co_mau_doi_theo_tong(self):
        sai = []
        for p in sorted(GOC.glob('*.py')):
            if p.name in KIEU_THANG_DUOC:
                continue
            s = _doc(p)
            for m in RE_GOI_KIEU.finditer(s):
                if RE_HEX.search(_doi_so(s, m.end() - 1)):
                    sai.append(f'{p.name} dòng {s.count(chr(10), 0, m.start()) + 1}')
        self.assertEqual(sai, [], 'setStyleSheet có màu viết thẳng không đổi theo tông nền: dùng giao_dien.dat_kieu_theo_tong(w, qss)')

    def test_mau_o_doi_theo_tong(self):
        from pabt import giao_dien as g
        from pabt import man_hinh_theo_doi as td
        cu = g.TONG_NEN[0]
        try:
            g.dat_tong_nen('sang', ap_lai=False)
            self.assertEqual(td.XANH.name().upper(), '#E2EFDA')
            g.dat_tong_nen('toi', ap_lai=False)
            self.assertEqual(td.XANH.name().upper(), g.TOI_NEN['#E2EFDA'])
            self.assertNotEqual(td.MAU_LIEN_KET.name().upper(), '#2F5DB5')     # chữ liên kết sáng lên trên nền tối
        finally:
            g.dat_tong_nen(cu, ap_lai=False)

    def test_kieu_theo_tong_moi_widget_mot_muc_va_giu_ty_le(self):
        from PySide6.QtWidgets import QApplication, QLabel
        from pabt import giao_dien as g
        QApplication.instance() or QApplication([])
        lb = QLabel('x')
        cu = g.TY_LE[0]
        try:
            g.TY_LE[0] = 1.2
            for nen in ('#FFFFFF', '#F1F5F9', '#E2EFDA'):
                g.dat_kieu_theo_tong(lb, f'QLabel {{ background: {nen}; font-size: 10px; }}')
            self.assertEqual(sum(1 for r, _ in g._KIEU_THEO_TONG if r() is lb), 1)
            self.assertIn('12px', lb.styleSheet())                         # 10 px x 1,2: không mất co giãn khi đặt sau lúc hiện
            g._ap_lai_kieu_theo_tong()                                      # nhãn chưa hiện: hoãn tới lúc hiện
            self.assertTrue(lb.property('qss_cho_tong'))
            g._ap_kieu_cho(lb)
            self.assertFalse(lb.property('qss_cho_tong'))
            self.assertIn('12px', lb.styleSheet())                         # đổi tông: vẫn giữ tỷ lệ chữ
            g.TY_LE[0] = 1.5
            lb.setProperty('qss_cho_ty_le', True)                           # A+ lúc nhãn đang ẩn
            g._ap_kieu_cho(lb)
            self.assertIn('15px', lb.styleSheet())
        finally:
            g.TY_LE[0] = cu
            lb.deleteLater()


class TestThangCoChu(unittest.TestCase):
    def test_co_chu_qss_theo_thang(self):
        from pabt.giao_dien import THANG_CO_CHU
        ngoai = []
        for p in sorted(GOC.glob('*.py')):
            if p.name == 'nhan_wifi.py':                                     # trang web trên điện thoại: chữ to cho ngón tay
                continue
            for m in re.finditer(r'font-size: ?(\d+(?:\.\d+)?)px', _doc(p)):
                if float(m.group(1)) not in THANG_CO_CHU:
                    ngoai.append(f'{p.name}: {m.group(1)}px')
        self.assertEqual(ngoai, [], f'Cỡ chữ ngoài thang {THANG_CO_CHU}')


class TestChieuCaoDong(unittest.TestCase):
    def test_khong_con_resize_rows_to_contents(self):
        sai = []
        for p in sorted(GOC.glob('*.py')):
            for i, d in enumerate(_doc(p).split('\n'), 1):
                if 'resizeRowsToContents()' in d and not d.lstrip().startswith('#') and p.name != 'giao_dien.py':
                    sai.append(f'{p.name}:{i}')
        self.assertEqual(sai, [], 'Dùng giao_dien.vua_dong(bang, None, None) - đo chữ thật, không hỏi sizeHint mọi ô')


class TestNhanTroNang(unittest.TestCase):
    def test_o_nhap_lay_ten_theo_nhan_canh(self):
        from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                                       QSpinBox, QVBoxLayout)
        from pabt import giao_dien as g
        QApplication.instance() or QApplication([])
        d = QDialog()
        v = QVBoxLayout(d)
        f = QFormLayout()
        a = QLineEdit()
        f.addRow('Họ và tên:', a)
        v.addLayout(f)
        h = QHBoxLayout()
        lb = QLabel('Số &CCCD:')
        b = QLineEdit()
        b.setPlaceholderText('12 chữ số')
        h.addWidget(lb)
        h.addWidget(b)
        k = QComboBox()
        k.setAccessibleName('đặt tay')
        h.addWidget(QLabel('Loại đất'))
        h.addWidget(k)
        v.addLayout(h)
        gr = QGridLayout()
        gr.addWidget(QLabel('<b>Số hộ</b>'), 0, 0)
        c = QSpinBox()
        gr.addWidget(c, 0, 1)
        v.addLayout(gr)
        g.dat_ten_truy_cap(d)
        self.assertEqual(a.accessibleName(), 'Họ và tên')
        self.assertEqual(b.accessibleName(), 'Số CCCD')
        self.assertEqual(b.accessibleDescription(), '12 chữ số')
        self.assertIs(lb.buddy(), b)                                          # Alt+C nhảy tới ô CCCD
        self.assertEqual(c.accessibleName(), 'Số hộ')
        self.assertEqual(k.accessibleName(), 'đặt tay')                       # không ghi đè tên đã đặt
        d.deleteLater()


if __name__ == '__main__':
    unittest.main()
