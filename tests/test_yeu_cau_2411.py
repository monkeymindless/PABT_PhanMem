"""24/10/2026 (người dùng): xem trước NHIỀU HỘ trên cùng một bản (gộp PDF) ở hộp Xuất hồ sơ & Bản in. Word / Excel thật được thay bằng hàm
chép PDF giả lập (2 trang mỗi hộ); phần gộp, mục lục, ô "Nhảy tới hộ" chạy thật. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from unittest import mock

from pabt import xem_truoc_tai_lieu as xt
from tests.test_yeu_cau_0984 import CoSoXem, _pdf_nhieu_trang


def _gia_nhieu(mau: Path):
    """Thay chuyen_pdf_nhieu: mỗi file 'xuất' ra PDF 2 trang (chép mẫu), rồi gộp thật như hàm gốc."""
    def f(muc, pdf):
        co = []
        for file, nhan in muc:
            g = Path(file).with_suffix('.pdf')
            shutil.copy2(mau, g)
            co.append((g, nhan))
        return '', xt.gop_pdf_muc(co, Path(pdf))
    return f


class TestXemNhieuHo(CoSoXem):
    def setUp(self):
        super().setUp()
        self.mau2 = _pdf_nhieu_trang(self.td / 'mau2.pdf', 2)
        v = mock.patch.object(xt, 'chuyen_pdf_nhieu', _gia_nhieu(self.mau2))
        v.start()
        self.addCleanup(v.stop)

    def _hop(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, file_du_an=self.p)
        h.im_lang = True
        self.addCleanup(h.w_preview.don_dep)
        return h

    def test_gop_pdf_muc_luc(self):
        out = self.td / 'gop.pdf'
        ml = xt.gop_pdf_muc([(self.mau2, 'A'), (self.mau2, 'B'), (self.mau2, 'C')], out)
        self.assertEqual(ml, [('A', 0), ('B', 2), ('C', 4)])
        from pypdf import PdfReader
        self.assertEqual(len(PdfReader(str(out)).pages), 6)

    def test_xem_gop_cac_ho_da_chon(self):
        h = self._hop()
        h._danh_dau([r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')][:3])
        khoa = h.xem_truoc_nhieu_ho(ngay=True)
        self.assertEqual(khoa[0], 'nhieu')
        self.assertTrue(h.w_preview.cho_xong(30))
        k = h.w_preview
        self.assertEqual([t for _, t in k.muc_luc], [0, 2, 4][:len(k.muc_luc)])
        self.assertEqual(len(k.muc_luc), len(khoa[1]))
        self.assertEqual(k.cb_muc.count(), len(k.muc_luc))
        self.assertTrue(k.cb_muc.isVisibleTo(k))                    # ô "Nhảy tới hộ" hiện khi xem nhiều hộ
        self.assertFalse(k.b_in.isEnabled())                        # In nhanh (một file Word / Excel) tắt - dùng "In…" cho cả bản
        self.assertIsNone(k.xlsx)
        if xt.co_qtpdf():
            self.assertEqual(k.so_trang(), 2 * len(khoa[1]))
            k.den_muc(1)
            self.assertEqual(k.trang_hien_tai(), 2)
        for ten in (k.cb_muc.itemText(i) for i in range(k.cb_muc.count())):
            self.assertRegex(ten, r'^\d+\. ')                       # nhãn "STT. họ tên"

    def test_bam_mot_ho_thi_het_muc_luc(self):
        h = self._hop()
        h._danh_dau([r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')][:2])
        h.xem_truoc_nhieu_ho(ngay=True)
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertTrue(h.w_preview.muc_luc)
        h.bang_ho.setCurrentCell(0, 1)                              # xem riêng một hộ
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertEqual(h.w_preview.muc_luc, [])
        self.assertFalse(h.w_preview.cb_muc.isVisibleTo(h.w_preview))
        self.assertTrue(h.w_preview.b_in.isEnabled())

    def test_gioi_han_va_khong_chon_ho(self):
        h = self._hop()
        h._danh_dau([])
        self.assertIsNone(h.xem_truoc_nhieu_ho())                   # chưa đánh dấu hộ nào: không lập, không hộp thoại (im_lang)
        h._danh_dau([r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')])
        with mock.patch('pabt.man_hinh.XEM_NHIEU_TOI_DA', 1):
            khoa = h.xem_truoc_nhieu_ho(ngay=True)
        self.assertEqual(len(khoa[1]), 1)
        self.assertTrue(h.w_preview.cho_xong(30))
        self.assertEqual(len(h.w_preview.muc_luc), 1)

    def test_che_do_du_thao_doi_khoa(self):
        h = self._hop()
        h._danh_dau([r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')][:2])
        h.r_chinh_thuc.setChecked(True)
        k1 = h.xem_truoc_nhieu_ho(ngay=True)
        h.w_preview.cho_xong(30)
        h.r_du_thao.setChecked(True)
        k2 = h.xem_truoc_nhieu_ho(ngay=True)
        self.assertNotEqual(k1, k2)                                 # dự thảo / chính thức là hai bản khác nhau

    def test_ban_gan_dung_khi_khong_co_word(self):
        """Máy không dùng được Word: từng hộ dựng PDF gần đúng bằng Qt từ file .docx rồi gộp."""
        h = self._hop()
        h._danh_dau([r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')][:2])
        with mock.patch.object(xt, 'dung_duoc_word', lambda: 'Máy chưa có Microsoft Word.'):
            h.xem_truoc_nhieu_ho(ngay=True)
            self.assertTrue(h.w_preview.cho_xong(60))
        k = h.w_preview
        self.assertTrue(k.gan_dung)
        self.assertEqual(len(k.muc_luc), 2)
        self.assertLess(k.muc_luc[0][1], k.muc_luc[1][1])           # hộ sau bắt đầu ở trang sau


if __name__ == '__main__':
    unittest.main()
