"""1.0.48–1.0.49: Dán tài sản chỉ lấy dòng viết tay / tài sản từ PDF scan / Word / Excel —
không đổ mẫu in hành chính và rác OCR. Trợ lý AI (tùy chọn) chỉ nhận dòng đã lọc, không gửi file ảnh / PDF. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tests.test_toc_do import _du_an


MAU_SCAN = """
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
UBND XÃ MẪU
BIÊN BẢN KIỂM ĐẾM TÀI SẢN TRÊN ĐẤT
Người có đất thu hồi: Nguyễn Văn A
Họ và tên: Nguyễn Văn A
CCCD: 075092001234
Địa chỉ: Ấp 1, xã Mẫu
Thửa đất số: 12
Tờ bản đồ số: 5
Diện tích: 250,5 m2
Mục đích sử dụng: Đất ở tại nông thôn
STT  Tên tài sản  ĐVT  Số lượng  Ghi chú
1  Nhà tạm  m2  46
2  Xoài  cây  16
I. NHÀ, CÔNG TRÌNH
Đại diện UBND
Chủ hộ ký
Người lập biểu
Ngày 30 tháng 10 năm 2026
||||
aE#@$%
~~ ~~
"""


def _app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestLocDongVietTay(unittest.TestCase):
    def test_bo_mau_in_giu_tai_san(self):
        from pabt.ocr_ho_so import dong_dua_vao_dan, loc_dong_viet_tay
        loc = loc_dong_viet_tay(MAU_SCAN)
        chu = '\n'.join(loc.giu).lower()
        self.assertNotIn('cộng hòa', chu)
        self.assertNotIn('độc lập', chu)
        self.assertNotIn('biên bản', chu)
        self.assertNotIn('nguyễn văn a', chu)
        self.assertNotIn('075092001234', chu)
        self.assertTrue(any('nhà tạm' in x.lower() for x in loc.giu))
        self.assertTrue(any('xoài' in x.lower() for x in loc.giu))
        self.assertLess(len(loc.giu), 8)
        self.assertGreater(len(loc.bo), 10)
        dan = dong_dua_vao_dan(MAU_SCAN)
        self.assertTrue(any('nhà tạm' in x.lower() for x in dan.giu))
        self.assertTrue(any('xoài' in x.lower() for x in dan.giu))
        self.assertFalse(any('cộng hòa' in x.lower() for x in dan.giu))

    def test_doc_danh_sach_bo_mau_in(self):
        from pabt.phan_loai_tai_san import doc_danh_sach
        ds = doc_danh_sach(MAU_SCAN)
        ten = ' '.join(d['ten'].lower() for d in ds)
        self.assertNotIn('cộng hòa', ten)
        self.assertNotIn('biên bản', ten)
        self.assertLess(len(ds), 8)
        self.assertTrue(any('nhà tạm' in d['ten'].lower() for d in ds))
        self.assertTrue(any('xoài' in d['ten'].lower() for d in ds))

    def test_boc_tach_khong_nhan_mau_in_la_tai_san(self):
        from pabt.ocr_ho_so import boc_tach
        kq = boc_tach(MAU_SCAN)
        self.assertEqual(kq.loai, 'bien_ban')
        self.assertTrue(kq.dong_tai_san)
        self.assertFalse(any('cộng hòa' in x.lower() for x in kq.dong_tai_san))
        self.assertGreater(len(kq.dong_bo), 5)


class TestDanTaiSanLocOcr(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(self.tmp.cleanup)
        _app()

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu

    def _hop(self):
        from pabt import csdl
        from pabt.lap_pa import BoSoan, DanhMuc
        from pabt.man_hinh_phan_loai import HopDanTaiSan
        from pabt.nhap_tai_san import DichPhuongAn
        con = csdl.mo(str(_du_an(self.td, 1)))
        self.addCleanup(con.close)
        hop = HopDanTaiSan(None, '', dich=DichPhuongAn(BoSoan(con, 1, DanhMuc(con))))
        hop.im_lang = True
        self.addCleanup(hop.deleteLater)
        return hop

    def test_mo_pdf_khong_do_mau_in_vao_o(self):
        hop = self._hop()
        self.assertEqual(hop.b_goc.text(), 'Chữ OCR gốc…')
        self.assertEqual(hop.b_ai.text(), 'Trợ lý AI viết lại…')
        self.assertFalse(hop.b_ai.isEnabled())
        with mock.patch('pabt.ocr.san_sang', return_value=''), \
                mock.patch('pabt.ocr.doc_chu', return_value=MAU_SCAN.strip().splitlines()):
            ds = hop.mo_anh_pdf(self.td / 'a.png')
        chu = hop.o_chu.toPlainText().lower()
        self.assertNotIn('cộng hòa', chu)
        self.assertNotIn('độc lập', chu)
        self.assertNotIn('biên bản kiểm', chu)
        self.assertIn('xoài', chu)
        self.assertIn('nhà tạm', chu)
        self.assertTrue(hop.b_goc.isEnabled())
        self.assertIn('cộng hòa', hop._chu_ocr.lower())
        self.assertTrue(ds)
        self.assertLess(len(ds), 8)

    def test_ai_chi_nhan_dong_da_loc(self):
        from pabt import ocr_ho_so, tro_ly
        tro_ly.ghi_cai_dat(bat=True)
        hop = self._hop()
        hop.o_chu.setPlainText('Xoài: 16 cây\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM')
        khach = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
            create=lambda **k: SimpleNamespace(
                stop_reason='end_turn',
                content=[SimpleNamespace(type='text', text='Xoài: 16 cây')]))))
        ra = hop.chinh_bang_ai(khach=khach)
        self.assertTrue(ra)
        self.assertIn('Xoài', hop.o_chu.toPlainText())
        self.assertNotIn('CỘNG HÒA', hop.o_chu.toPlainText())
        dong = ocr_ho_so.chinh_dong_ocr_ai(['Xoài: 16 cây'], khach=khach)
        self.assertEqual(dong, ['Xoài: 16 cây'])

    def test_mo_excel_loc_tai_san(self):
        import openpyxl
        hop = self._hop()
        p = self.td / 'bb.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'])
        ws.append(['STT', 'Tên tài sản', 'ĐVT', 'Số lượng'])
        ws.append([1, 'Nhà tạm', 'm2', 46])
        ws.append([2, 'Xoài', 'cây', 16])
        ws.append(['Đại diện UBND'])
        wb.save(p)
        ds = hop.mo_anh_pdf(p)
        chu = hop.o_chu.toPlainText().lower()
        self.assertNotIn('cộng hòa', chu)
        self.assertIn('xoài', chu)
        self.assertIn('nhà tạm', chu)
        self.assertTrue(ds)
        self.assertLess(len(ds), 8)


class TestDocFileScan(unittest.TestCase):
    def test_chu_tu_bang_va_loc(self):
        from pabt.ocr_ho_so import chu_tu_bang, loc_dong_viet_tay, LOC_FILE
        chu = chu_tu_bang([['CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'],
                           ['Nhà tạm', 'm2', '46'],
                           ['Xoài', 'cây', '16']])
        loc = loc_dong_viet_tay(chu)
        self.assertTrue(any('nhà tạm' in x.lower() for x in loc.giu))
        self.assertTrue(any('xoài' in x.lower() for x in loc.giu))
        self.assertFalse(any('cộng hòa' in x.lower() for x in loc.giu))
        self.assertIn('xlsx', LOC_FILE)
        self.assertIn('docx', LOC_FILE)
        self.assertIn('pdf', LOC_FILE)

    def test_pdf_lop_chu_thua_ocr_lai(self):
        from pabt import ocr_ho_so
        with mock.patch('pabt.quan_ly.doc_van_ban', return_value=([['xyz']], False)), \
                mock.patch('pabt.ocr.doc_chu', return_value=['Xoài: 16 cây']):
            chu, da = ocr_ho_so.doc_chu(Path('a.pdf'))
        self.assertTrue(da)
        self.assertIn('Xoài', chu)

    def test_phan_tich_tu_dong_ai(self):
        from pabt import tro_ly
        from pabt.ocr_ho_so import phan_tich_tu_dong
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = td.name
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        tro_ly.ghi_cai_dat(bat=True)
        khach = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
            create=lambda **k: SimpleNamespace(
                stop_reason='end_turn',
                content=[SimpleNamespace(type='text', text='Xoài: 16 cây\nNhà tạm: 46 m2')]))))
        loc = phan_tich_tu_dong(MAU_SCAN, khach=khach, dung_ai=True)
        self.assertTrue(loc.da_ai)
        chu = '\n'.join(loc.giu).lower()
        self.assertIn('xoài', chu)
        self.assertNotIn('cộng hòa', chu)

    def test_ocr_psm4_khi_lan_dau_khong_co_tai_san(self):
        from pabt import ocr_ho_so

        def fake_ocr(file, bao_tien_do=None, cho=None, psm=6):
            if psm == 4:
                return ['Xoài: 16 cây']
            return ['||||', 'aE#@$%']

        with mock.patch('pabt.quan_ly.doc_van_ban', side_effect=lambda f, *a, **k: (
                [[x] for x in fake_ocr(f)], True)), \
                mock.patch('pabt.ocr.doc_chu', side_effect=fake_ocr):
            loc, chu, da = ocr_ho_so.doc_va_phan_tich(Path('a.png'), dung_ai=False)
        self.assertTrue(da)
        self.assertTrue(any('xoài' in x.lower() for x in loc.giu))
        self.assertIn('cột thưa', loc.ly_do)

    def test_phien_ban(self):
        from pabt import __version__, lich_su_cap_nhat
        self.assertGreaterEqual(tuple(int(x) for x in __version__.split('.')), (1, 0, 50))
        self.assertEqual(lich_su_cap_nhat.MUC[0][0], __version__)              # mục mới nhất = phiên bản hiện hành
        self.assertIn('1.0.50', [m[0] for m in lich_su_cap_nhat.MUC])


if __name__ == '__main__':
    unittest.main()
