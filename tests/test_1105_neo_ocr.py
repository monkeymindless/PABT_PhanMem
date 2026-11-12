"""1.1.05 - kiểm định đơn giá tầng 3 (tài liệu 1.1.03 Phần 1): khi đọc bảng giá đất từ bản scan, mỗi con số dạng giá giữ độ tin cậy
nhận dạng của Tesseract + ảnh cắt đúng chỗ đó; phép soi dùng độ tin cậy, màn hình đặt ảnh cắt vào chú thích dòng bị nghi.
Đường OCR khác (không truyền neo) không đổi. Bài đọc ảnh thật cần Tesseract (bo_cai_win/tesseract) - không có thì bỏ qua."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import kiem_dinh_don_gia as kd
from pabt import ocr

TSV = '\n'.join([
    'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext',
    '5\t1\t1\t1\t1\t1\t10\t20\t60\t18\t96.5\tĐường',
    '5\t1\t1\t1\t1\t2\t200\t20\t50\t18\t91.0\t1.200',
    '5\t1\t1\t1\t1\t3\t300\t20\t40\t18\t62.25\t850',
    '5\t1\t1\t1\t1\t4\t380\t20\t20\t18\t88\t12',
    '5\t1\t1\t1\t1\t5\t420\t20\t80\t18\t-1\t2.500.000',
    '5\t1\t1\t1\t1\t6\t520\t20\t80\t18\t70\t3.4O0',
])


def _dong(ten, vt, **gia):
    r = dict(xa='Xã Thử', tt=1, ten_duong=ten, diem_dau='Đầu', diem_cuoi='Cuối', vi_tri=vt, dat_o=0, tmdv=0, sxkd=0, nn_cay=0,
             nn_rung_nts=0)
    r.update(gia)
    return r


class TestTsv(unittest.TestCase):
    def test_chi_con_so_dang_gia(self):
        kq = ocr.so_tin_cay_tsv(TSV)
        self.assertEqual([(t, tc) for *_, t, tc in kq], [('1.200', 91.0), ('850', 62.25)])
        self.assertEqual(kq[0][:4], (200, 20, 50, 18))
        self.assertEqual(ocr.chu_so('1.200'), '1200')

    def test_tu_tsv_khong_doi(self):
        self.assertEqual(len(ocr.tu_tsv(TSV)), 6)


class TestGanTinCay(unittest.TestCase):
    def setUp(self):
        self.neo = [{'so': '1200', 'chu': '1.200', 'tin_cay': 91.0, 'trang': 1, 'anh': ''},
                    {'so': '850', 'chu': '850', 'tin_cay': 62.25, 'trang': 1, 'anh': ''},
                    {'so': '1200', 'chu': '1.200', 'tin_cay': 97.0, 'trang': 2, 'anh': ''}]

    def test_dong_goc_khong_doi(self):
        ds = [_dong('Đường A', 'VT1', dat_o=1200), _dong('Đường A', 'VT2', dat_o=850), _dong('Đường A', 'VT3', dat_o=500)]
        moi = kd.gan_tin_cay_ocr(ds, self.neo)
        self.assertTrue(all('ocr_tin_cay' not in r for r in ds))           # dòng gốc (ghi vào bảng giá) không có khóa lạ
        self.assertEqual(moi[0]['ocr_tin_cay'], Decimal(91))               # cùng số hai chỗ: lấy chỗ tin cậy thấp
        self.assertEqual(moi[1]['ocr_tin_cay'], Decimal(62))
        self.assertNotIn('ocr_tin_cay', moi[2])                            # số không có trên ảnh: không đánh dấu

    def test_kiem_dinh_dung_tin_cay(self):
        ds = [_dong('Đường A', 'VT1', dat_o=1200), _dong('Đường A', 'VT2', dat_o=850)]
        kq = kd.kiem_dinh_bang_gia_dat(kd.gan_tin_cay_ocr(ds, self.neo))
        co = {x['i']: x['co'] for x in kq['dong']}
        self.assertNotIn(kd.OCR_KEM_TIN_CAY, co[0])
        self.assertIn(kd.OCR_KEM_TIN_CAY, co[1])
        self.assertEqual(kd.kiem_dinh_bang_gia_dat(ds)['can_xac_nhan'], [])  # không có ảnh: như trước

    def test_khop_ca_gia_x1000(self):
        neo = [{'so': '1200000', 'chu': '1.200.000', 'tin_cay': 80, 'trang': 1, 'anh': ''}]
        self.assertEqual(len(kd.neo_cua_dong(_dong('Đường A', 'VT1', dat_o=1200), neo)), 1)
        self.assertEqual(kd.neo_cua_dong(_dong('Đường A', 'VT1', dat_o=1300), neo), [])


def _anh_bang(f: Path) -> None:
    from PySide6.QtGui import QColor, QFont, QImage, QPainter
    im = QImage(1600, 500, QImage.Format.Format_RGB32)
    im.fill(QColor(255, 255, 255))
    p = QPainter(im)
    p.setPen(QColor(0, 0, 0))
    p.setFont(QFont('Arial', 30))
    for i, (ten, gia) in enumerate((('Duong Mot', '1.250'), ('Duong Hai', '3.400'), ('Duong Ba', '875'))):
        p.drawText(80, 120 + i * 110, ten)
        p.drawText(900, 120 + i * 110, gia)
    p.end()
    im.save(str(f))


@unittest.skipUnless(ocr.tim_tesseract() and not ocr.san_sang(), 'cần Tesseract (bo_cai_win/tesseract) có tiếng Việt')
class TestDocAnhThat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1105_ocr_'))

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_neo_co_anh_va_tin_cay(self):
        f = self.td / 'bang.png'
        _anh_bang(f)
        neo = []
        chu = '\n'.join(ocr.tung_trang(f, neo=neo))
        self.assertIn('1.250', chu)
        so = {n['so'] for n in neo}
        self.assertTrue({'1250', '3400', '875'} <= so, so)
        for n in neo:
            self.assertTrue(os.path.isfile(n['anh']))
            self.assertEqual(n['trang'], 1)
            self.assertTrue(0 <= n['tin_cay'] <= 100)
        from PySide6.QtGui import QImage
        im = QImage(next(n['anh'] for n in neo if n['so'] == '1250'))
        self.assertFalse(im.isNull())
        self.assertLess(im.width(), 400)                                    # ảnh CẮT một con số, không phải cả trang

    def test_khong_neo_thi_nhu_cu(self):
        f = self.td / 'bang.png'
        _anh_bang(f)
        self.assertEqual(list(ocr.tung_trang(f)), list(ocr.tung_trang(f, neo=[])))


class TestManHinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_chu_thich_co_anh_goc(self):
        from PySide6.QtGui import QColor, QImage
        from pabt.man_hinh_gia_dat import KhungCapNhatGiaDat
        td = Path(tempfile.mkdtemp(prefix='pabt_1105_mh_'))
        try:
            anh = td / 'so.png'
            im = QImage(60, 24, QImage.Format.Format_RGB32)
            im.fill(QColor(255, 255, 255))
            im.save(str(anh))
            k = KhungCapNhatGiaDat(None, 'Xã Thử')
            k.im_lang = True
            ds = [_dong('Đường A', 'VT1', dat_o=1200), _dong('Đường A', 'VT2', dat_o=850)]
            k.kq = {'dong_goc': ds, 'quy_tac': [], 'van_ban': 'Thử', 'chu': '', 'neo_so': [
                {'so': '1200', 'chu': '1.200', 'tin_cay': 95.0, 'trang': 1, 'anh': str(anh)},
                {'so': '850', 'chu': '850', 'tin_cay': 41.0, 'trang': 2, 'anh': str(anh)}]}
            k._hien(ds, 'Thử', '', 'thu.pdf')
            dau = k.bang.item(0, 0).toolTip()
            sau = k.bang.item(1, 0).toolTip()
            self.assertFalse(dau.startswith('Cần xem lại'))                 # dòng tin cậy cao: không tô, không ảnh
            self.assertTrue(sau.startswith('Cần xem lại:'))
            self.assertIn('<img', sau)
            self.assertIn('Trang 2', sau)
            self.assertIn('41%', sau)
            self.assertTrue(all('ocr_tin_cay' not in r for r in k.dong))    # dòng sẽ ghi vào bảng giá không mang khóa lạ
            k.kq = {'dong_goc': ds, 'quy_tac': [], 'van_ban': 'Thử', 'chu': ''}     # file không phải scan: như trước
            k._hien(ds, 'Thử', '', 'thu.xlsx')
            self.assertFalse(k.bang.item(1, 0).toolTip().startswith('Cần xem lại'))
            k.deleteLater()
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
