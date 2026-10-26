"""1.0.19 Đợt 3 - bộ kiểm KHUÔN bản Word phương án chi tiết bằng Microsoft Word THẬT (bỏ qua khi máy không có Word):
xuất .docx -> Word xuất PDF -> đo vị trí chữ trong PDF (pypdf) và đối chiếu khuôn mẫu PA_01:
  - khổ A4, mọi chữ nằm trong lề (trái 15 / phải 10 / trên 10 / dưới 10 mm);
  - "Số: …" và "địa danh, ngày …" CÙNG MỘT HÀNG (lệch dọc < 1 pt) - hai dòng ngang nhau;
  - có dòng "CHI NHÁNH …" khi dự án có đơn vị lập thuộc chi nhánh;
  - không có trang CHỈ chứa khối chữ ký: trang cuối có chữ ký thì phải có cả dòng TỔNG CỘNG hoặc dòng bảng;
  - không mất chữ: các cụm đặc trưng của dữ liệu (họ tên, cuối nguồn gốc, TỔNG CỘNG) đều có trong PDF.
Bộ dữ liệu cực đoan: nguồn gốc rất dài, 40 thửa, họ tên rất dài, tổ chức (không CCCD), dự thảo. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication                                       # noqa: E402

from pabt import csdl, du_an_moi, in_word                                        # noqa: E402
from pabt import van_ban_trinh as vb                                             # noqa: E402
from tests.test_van_ban_trinh import _co_word                                    # noqa: E402

MM = 72 / 25.4
LE_TRAI, LE_PHAI, LE_TREN, LE_DUOI = 9, 7, 10, 10             # mm, mẫu PDF 23/10/2026
DUNG_SAI = 1.5                                  # pt
CUOI_NGUON = 'CUỐI-NGUỒN-GỐC-ĐỦ-CHỮ'
NGUON = ('Thửa đất giả lập do hộ gia đình khai phá, sử dụng ổn định từ năm 1990, không tranh chấp, đã kê khai đăng ký, '
         'được UBND xã xác nhận nguồn gốc theo biên bản kiểm tra thực địa. ')


_DON_VI = (1, 0, 0, 1, 0, 0)


def _chu_co_vi_tri(trang) -> list:
    """[(chữ, x, y)] của một trang PDF (y tính từ đáy trang): vị trí = ma trận chữ tm nhân ma trận biến đổi cm.
    pypdf < 6 (bản cuối cho Python 3.8 - môi trường Qt5 / Win7 là 5.9) gọi visitor cho mẩu chữ cuối khối (" ng ", "…kiểm tra") với
    CẢ cm lẫn tm là ma trận đơn vị - không có vị trí, không phải chữ in ở góc (0, 0): bỏ qua (pypdf 6 báo đúng vị trí các mẩu đó)."""
    ra = []

    def dem(text, cm, tm, fd, fs):
        if not text or not text.strip():
            return
        if tuple(round(float(v), 6) for v in cm) == _DON_VI and tuple(round(float(v), 6) for v in tm) == _DON_VI:
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        ra.append((text, x, y))
    trang.extract_text(visitor_text=dem)
    return ra


def tao_du_an(td: Path, kieu: str) -> Path:
    n_thua = 40 if kieu == 'nhieu_thua' else 1
    ho_ten = {'ten_dai': 'Nguyễn Văn Thử Có Họ Tên Rất Dài Để Kiểm Tra Việc Ngắt Dòng Trong Ô Thông Tin Chủ Sử Dụng',
              'to_chuc': 'Công ty TNHH Một Thành Viên Thử Nghiệm'}.get(kieu, 'Nguyễn Văn Thử')
    dong = [dict(ho_ten=ho_ten, dia_chi='Ấp 1', so_to='5', so_thua=str(100 + j), loai_dat='CLN', dt_thu_hoi=str(50 + j), vi_tri='1')
            for j in range(n_thua)]
    p = td / f'{kieu}.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Dự án thử khuôn', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    con = csdl.mo(p)
    try:
        with con:
            if kieu == 'nguon_dai':
                con.execute('UPDATE thua SET nguon_goc = ?', ((NGUON * 25) + CUOI_NGUON,))
            else:
                con.execute('UPDATE thua SET nguon_goc = ?', (NGUON + CUOI_NGUON,))
            con.execute("UPDATE du_an SET don_vi_lap = 'Trung tâm Phát triển quỹ đất Chi nhánh Vĩnh Cửu', don_vi_tieu_de = ''")
    finally:
        con.close()
    return p


@unittest.skipUnless(_co_word(), 'cần Microsoft Word (đặt PABT_THU_WORD=0 để bỏ qua)')
class TestKhuonWord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)                   # chạy SAU các addCleanup đăng ký sau (đóng kết nối trước)

    def xuat(self, kieu: str, du_thao: bool = False):
        """(trang PDF [danh sách (chữ, x, y)], kích thước trang [(w, h)], toàn văn)."""
        from pypdf import PdfReader
        con = csdl.mo(tao_du_an(self.td, kieu))
        self.addCleanup(con.close)
        ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        docx = in_word.xuat_chi_tiet_docx(con, ma, self.td / f'{kieu}.docx', du_thao=du_thao)
        pdf = docx.with_suffix('.pdf')
        loi = vb.chay_word([('pdf', docx, pdf)], cho_moi_file=120)
        self.assertEqual(loi, [])
        r = PdfReader(str(pdf))
        trang = [_chu_co_vi_tri(p) for p in r.pages]
        kich = [(float(p.mediabox.width), float(p.mediabox.height)) for p in r.pages]
        return trang, kich, '\n'.join(p.extract_text() for p in r.pages)

    def kiem_chung(self, kieu: str, du_thao: bool = False):
        trang, kich, toan = self.xuat(kieu, du_thao)
        self.assertGreaterEqual(len(trang), 1)
        for (w, h), chu in zip(kich, trang):
            self.assertEqual((round(w), round(h)), (595, 842))                       # A4 dọc
            for t, x, y in chu:
                self.assertGreaterEqual(x, LE_TRAI * MM - DUNG_SAI, f'{kieu}: "{t[:20]}" tràn lề trái (x={x:.1f})')
                self.assertLessEqual(x, w - LE_PHAI * MM + DUNG_SAI, f'{kieu}: "{t[:20]}" tràn lề phải (x={x:.1f})')
                self.assertGreaterEqual(y, LE_DUOI * MM - DUNG_SAI - 14, f'{kieu}: "{t[:20]}" tràn lề dưới (y={y:.1f})')
                self.assertLessEqual(y, h - LE_TREN * MM + DUNG_SAI, f'{kieu}: "{t[:20]}" tràn lề trên (y={y:.1f})')
        # dòng "Số:" và "ngày" cùng hàng
        t1 = trang[0]
        so = [y for t, x, y in t1 if t.strip().startswith('Số:')]
        ngay = [y for t, x, y in t1 if 'ngày' in t and 'tháng' in t or t.strip().startswith('Trị An')]
        self.assertTrue(so and ngay, f'{kieu}: không thấy dòng Số / ngày trang 1')
        self.assertLess(abs(so[0] - ngay[0]), 1.0, f'{kieu}: "Số" và "ngày" lệch hàng {abs(so[0] - ngay[0]):.2f} pt')
        # đủ chữ
        self.assertIn('CHI NHÁNH', toan)
        self.assertIn('TỔNG CỘNG', toan)
        if kieu != 'nhieu_thua':
            gon = ''.join(toan.replace('-', '').split())
            self.assertIn(''.join(CUOI_NGUON.replace('-', '').split()), gon)
        # không có trang chỉ chứa khối chữ ký
        if not du_thao:
            cuoi = '\n'.join(t for t, _, _ in trang[-1])
            if 'LẬP BIỂU' in cuoi or 'KIỂM TRA' in cuoi:
                self.assertTrue('TỔNG CỘNG' in cuoi or len(trang[-1]) > 12,
                                f'{kieu}: trang cuối chỉ có khối chữ ký ({len(trang[-1])} khối chữ)')
        return trang

    def test_binh_thuong(self):
        self.kiem_chung('binh_thuong')

    def test_du_thao(self):
        self.kiem_chung('binh_thuong', du_thao=True)

    def test_nguon_goc_rat_dai(self):
        self.kiem_chung('nguon_dai')

    def test_nhieu_thua(self):
        trang = self.kiem_chung('nhieu_thua')
        self.assertGreaterEqual(len(trang), 2)

    def test_ho_ten_rat_dai(self):
        self.kiem_chung('ten_dai')

    def test_to_chuc(self):
        _, _, toan = self.xuat('to_chuc')
        self.assertIn('Tổ chức', toan)
        self.assertNotIn('Số CCCD', toan)                                           # tổ chức không có CCCD / điện thoại


if __name__ == '__main__':
    unittest.main()
