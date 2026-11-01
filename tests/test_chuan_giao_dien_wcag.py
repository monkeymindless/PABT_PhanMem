"""Chuẩn giao diện đo được (đợt rà soát 30/10/2026, theo WCAG 2.2 AA): tỷ lệ tương phản chữ / nền >= 4,5:1 cho mọi quy tắc QSS
và mọi cặp màu chữ khai trong giao_dien (bỏ qua trạng thái :disabled - WCAG miễn); thành phần phi chữ (vòng focus, thanh tỷ lệ)
>= 3:1; cửa sổ chính không có nút chỉ biểu tượng mà thiếu tên (chữ / gợi ý / accessibleName) và không có nút quá nhỏ để bấm.
1.0.42: số 0, STT dọc và viền ô nhập đã đạt AA — không còn expectedFailure cho ba cặp đó."""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import giao_dien  # noqa: E402

AA_CHU = 4.5            # WCAG 1.4.3: chữ thường
AA_PHI_CHU = 3.0        # WCAG 1.4.11: viền / vạch / biểu tượng cần để nhận ra thành phần
NUT_TOI_THIEU = 18      # px (96 DPI): nút thấp nhất hiện có là nút A− / A+ / 100% thanh trạng thái (19 px); WCAG 2.2 khuyên 24


def _do_sang(mau: str) -> float:
    h = mau.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    kenh = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kenh)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def tuong_phan(a: str, b: str) -> float:
    """Tỷ lệ tương phản WCAG giữa hai màu #RRGGBB (1 - 21)."""
    x, y = sorted((_do_sang(a), _do_sang(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def _cap_qss(qss: str):
    """(bộ chọn, màu chữ, màu nền) của mọi quy tắc QSS có cả color và background là màu đặc #hex."""
    for bo_chon, than in re.findall(r'([^{}]+)\{([^{}]*)\}', qss):
        c = re.search(r'(?<![-\w])color:\s*(#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3})\b', than)
        b = re.search(r'background(?:-color)?:\s*(#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3})\b', than)
        if c and b:
            yield ' '.join(bo_chon.split()), c.group(1), b.group(1)


class TestHamTuongPhan(unittest.TestCase):
    def test_gia_tri_chuan(self):
        self.assertAlmostEqual(tuong_phan('#000000', '#FFFFFF'), 21, places=2)
        self.assertAlmostEqual(tuong_phan('#FFFFFF', '#FFFFFF'), 1, places=2)
        self.assertAlmostEqual(tuong_phan('#767676', '#FFFFFF'), 4.54, places=2)     # mốc xám AA quen thuộc
        self.assertEqual(tuong_phan('#FFF', '#000'), tuong_phan('#FFFFFF', '#000000'))


class TestTuongPhanQss(unittest.TestCase):
    def test_moi_quy_tac_chu_tren_nen_dat_aa(self):
        qss = giao_dien._qss_day_du()
        cap = list(_cap_qss(qss))
        self.assertGreater(len(cap), 50)                                    # bộ đọc QSS còn bắt được quy tắc
        kem = [(round(tuong_phan(c, b), 2), c, b, s) for s, c, b in cap
               if ':disabled' not in s and s != 'QHeaderView::section:vertical' and tuong_phan(c, b) < AA_CHU]
        self.assertEqual(kem, [])

    def test_so_thu_tu_dong_dat_aa(self):
        """Cột số thứ tự dòng (QHeaderView dọc): TOKEN['chu_phu'] trên nền header (1.0.42)."""
        qss = giao_dien._qss_day_du()
        doc = [(c, b) for s, c, b in _cap_qss(qss) if s == 'QHeaderView::section:vertical']
        self.assertTrue(doc)
        for c, b in doc:
            self.assertGreaterEqual(tuong_phan(c, b), AA_CHU, (c, b))


class TestTuongPhanBangMau(unittest.TestCase):
    def test_cap_mau_chu_dat_aa(self):
        T = giao_dien.TOKEN
        cap = {
            'chữ chính / nền cửa sổ': (T['chu'], T['nen']), 'chữ phụ / nền cửa sổ': (T['chu_phu'], T['nen']),
            'chữ phụ / thẻ trắng': (T['chu_phu'], T['khung']), 'liên kết / trắng': (T['nhan'], '#FFFFFF'),
            'thẻ tab chưa chọn': (giao_dien.THE_TAB['chu'], giao_dien.THE_TAB['nen']),
            'nút phụ': (giao_dien.NUT_PHU[1], giao_dien.NUT_PHU[0]), 'nút xóa viền': (giao_dien.NUT_XOA[1], giao_dien.NUT_XOA[0]),
            'nút xóa viền, rê chuột': (giao_dien.NUT_XOA[1], giao_dien.NUT_XOA[3]),
            'số tiền': (giao_dien.MAU_SO_TIEN, '#FFFFFF'), 'số vượt': (giao_dien.MAU_SO_VUOT, '#FFFFFF'),
            'cảnh báo tức thời': (giao_dien.MAU_CANH_BAO_CHU, giao_dien.MAU_CANH_BAO_NEN),
            'hệ số K': (giao_dien.MAU_HE_SO_K, '#FFFFFF'), 'giá × K': (giao_dien.MAU_GIA_K, '#FFFFFF'),
            'mục đang chọn': (giao_dien.MAU_CHON_DIU[1], giao_dien.MAU_CHON_DIU[0]),
            'phụ đề banner': (giao_dien.MAU_PHU_DE, giao_dien.MAU_BANG[0]),
            'đơn vị trên banner': (giao_dien.MAU_DON_VI_BANNER, giao_dien.MAU_BANG[0]),
        }
        for nhom, (nen, chu, re_) in giao_dien.MAU.items():                 # nút nền đặc chữ trắng / nút 'nhat'
            cap[f'nút nhóm {nhom}'] = (chu, nen)
            cap[f'nút nhóm {nhom}, rê chuột'] = (chu, re_)
        for ten, (chu, nen, _vien) in giao_dien.MAU_TRANG_THAI.items():
            cap[f'băng trạng thái {ten}'] = (chu, nen)
        kem = {k: round(tuong_phan(*v), 2) for k, v in cap.items() if tuong_phan(*v) < AA_CHU}
        self.assertEqual(kem, {})

    def test_thanh_phan_phi_chu_dat_3_1(self):
        T = giao_dien.TOKEN
        for ten, (a, b) in {'vòng focus': (T['nhan'], '#FFFFFF'), 'thanh tỷ lệ': (giao_dien.MAU_THANH_TY_LE, giao_dien.MAU_RANH_TY_LE),
                            'viền chọn kiểu Excel': (giao_dien.MAU_VIEN_CHON, '#FFFFFF')}.items():
            self.assertGreaterEqual(tuong_phan(a, b), AA_PHI_CHU, ten)

    def test_so_0_trong_bang_dat_aa(self):
        """Số 0 trong bảng (MAU_SO_KHONG #64748B trên trắng ≥ 4,5:1, 1.0.42)."""
        self.assertGreaterEqual(tuong_phan(giao_dien.MAU_SO_KHONG, '#FFFFFF'), AA_CHU)

    def test_vien_o_nhap_dat_3_1(self):
        """Viền ô nhập lúc thường #8696AB trên trắng ≥ 3:1 (WCAG 1.4.11, 1.0.42)."""
        qss = giao_dien._qss_day_du()
        m = re.search(r'QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit \{[^}]*border: 1px solid '
                      r'(#[0-9A-Fa-f]{6})', qss)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(tuong_phan(m.group(1), '#FFFFFF'), AA_PHI_CHU)


class TestCuaSoChinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def _nut_hien(self):
        from PySide6.QtWidgets import QAbstractButton
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.resize(1366, 768)
        w.show()
        self.app.processEvents()
        return [b for b in w.findChildren(QAbstractButton) if b.isVisible() and b.window() is w]

    def test_nut_chi_bieu_tuong_co_ten(self):
        ds = self._nut_hien()
        self.assertTrue(ds)
        khong_ten = [(type(b).__name__, b.objectName()) for b in ds
                     if not (b.text().strip() or b.toolTip().strip() or b.accessibleName().strip())]
        self.assertEqual(khong_ten, [])

    def test_nut_du_lon_de_bam(self):
        nho = [(b.text() or b.toolTip() or b.objectName(), b.width(), b.height()) for b in self._nut_hien()
               if b.height() < NUT_TOI_THIEU or b.width() < NUT_TOI_THIEU]
        self.assertEqual(nho, [])


if __name__ == '__main__':
    unittest.main()
