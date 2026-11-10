"""1.0.50: chín phương án tinh chỉnh (xem trước OCR, psm 4, Tesseract nền, QSS_TOI, TOKEN, vua_dong, log tải lại, LENH, AI bỏ qua)."""
from __future__ import annotations

import inspect
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


def _app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestPhienBan1050(unittest.TestCase):
    def test_phien_ban(self):
        from pabt import __version__, lich_su_cap_nhat
        self.assertGreaterEqual(tuple(int(x) for x in __version__.split('.')), (1, 0, 50))
        self.assertEqual(lich_su_cap_nhat.MUC[0][0], __version__)              # mục mới nhất = phiên bản hiện hành
        self.assertIn('1.0.50', [m[0] for m in lich_su_cap_nhat.MUC])


class TestXemTruocThuAnh(unittest.TestCase):
    def test_anh_cac_trang_dung_doc_qimage(self):
        from pabt import man_hinh_ocr
        src = inspect.getsource(man_hinh_ocr.anh_cac_trang)
        self.assertIn('_doc_qimage', src)
        self.assertNotIn('QImage(str(f))', src)
        self.assertIn('rmtree', src)


class TestPsm4GioiHan(unittest.TestCase):
    def test_gcn_khong_psm4(self):
        from pabt.ocr_ho_so import can_psm4, doc_va_phan_tich
        chu = 'GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nHọ và tên: Nguyễn Văn A\nThửa đất số: 12'
        self.assertFalse(can_psm4(Path('a.png'), chu))
        with mock.patch('pabt.quan_ly.doc_van_ban', return_value=([[chu]], True)), \
                mock.patch('pabt.ocr.doc_chu') as m_ocr:
            loc, _c, da = doc_va_phan_tich(Path('a.png'), dung_ai=False)
        self.assertTrue(da)
        self.assertFalse(loc.giu)
        m_ocr.assert_not_called()

    def test_nhieu_trang_khong_psm4(self):
        from pabt.ocr_ho_so import can_psm4, doc_va_phan_tich
        chu = '||||\naE#@$%'
        with mock.patch('pabt.ocr.so_trang', return_value=20):
            self.assertFalse(can_psm4(Path('a.pdf'), chu))
            with mock.patch('pabt.quan_ly.doc_van_ban', return_value=([[chu]], True)), \
                    mock.patch('pabt.ocr.doc_chu') as m_ocr:
                loc, _c, da = doc_va_phan_tich(Path('a.pdf'), dung_ai=False)
        self.assertTrue(da)
        self.assertFalse(loc.giu)
        m_ocr.assert_not_called()

    def test_bien_ban_it_trang_van_psm4(self):
        from pabt.ocr_ho_so import can_psm4, doc_va_phan_tich

        def fake_ocr(file, bao_tien_do=None, cho=None, psm=6):
            if psm == 4:
                return ['Xoài: 16 cây']
            return ['||||']

        chu = 'BIÊN BẢN KIỂM ĐẾM\n||||'
        with mock.patch('pabt.ocr.so_trang', return_value=2):
            self.assertTrue(can_psm4(Path('a.png'), chu))
            with mock.patch('pabt.quan_ly.doc_van_ban', side_effect=lambda f, *a, **k: (
                    [[x] for x in fake_ocr(f)], True)), \
                    mock.patch('pabt.ocr.doc_chu', side_effect=fake_ocr):
                loc, _c, da = doc_va_phan_tich(Path('a.png'), dung_ai=False)
        self.assertTrue(da)
        self.assertTrue(any('xoài' in x.lower() for x in loc.giu))


class TestTesseractNen(unittest.TestCase):
    def test_chay_nen_tien_do_luong_khac(self):
        _app()
        from PySide6.QtWidgets import QProgressDialog
        from pabt.giao_dien import chay_nen_tien_do
        chinh = threading.get_ident()
        ids = []

        def ham(bao, cho):
            ids.append(threading.get_ident())
            bao(1, 1)
            return 42

        tien = QProgressDialog('Đang đọc…', 'Dừng', 0, 1)
        tien.show()
        try:
            kq = chay_nen_tien_do(None, ham, tien)
        finally:
            tien.close()
        self.assertEqual(kq, 42)
        self.assertEqual(len(ids), 1)
        self.assertNotEqual(ids[0], chinh)

    def test_im_lang_cung_luong(self):
        from pabt.giao_dien import chay_nen_tien_do
        chinh = threading.get_ident()
        ids = []

        def ham(bao, cho):
            ids.append(threading.get_ident())
            return 1

        self.assertEqual(chay_nen_tien_do(None, ham, None), 1)
        self.assertEqual(ids[0], chinh)


class TestQssToiVaToken(unittest.TestCase):
    def test_qss_toi_khong_qwidget_color(self):
        from pabt.giao_dien import QSS_TOI, TOKEN
        self.assertNotIn('QWidget { color:', QSS_TOI)
        self.assertIn('QToolTip', QSS_TOI)
        self.assertIn('canh_bao', TOKEN)
        self.assertIn('canh_bao_nhat', TOKEN)
        self.assertIn('chinh', TOKEN)

    def test_man_hinh_khong_hex_cu(self):
        from pabt import man_hinh, man_hinh_phan_loai, man_hinh_theo_doi, man_hinh_quan_ly
        for mod in (man_hinh, man_hinh_phan_loai, man_hinh_theo_doi, man_hinh_quan_ly):
            src = Path(mod.__file__).read_text(encoding='utf-8')
            self.assertNotIn('#8A5A00', src)
            self.assertNotIn('#1F4E78', src)
            self.assertNotIn('#FFF2CC', src)


class TestVuaDong(unittest.TestCase):
    def test_du_toan_va_don_gia_dung_vua_dong(self):
        from pabt import man_hinh_du_toan, man_hinh_nhap_don_gia
        s1 = Path(man_hinh_du_toan.__file__).read_text(encoding='utf-8')
        s2 = Path(man_hinh_nhap_don_gia.__file__).read_text(encoding='utf-8')
        self.assertIn('vua_dong', s1)
        self.assertNotIn('resizeRowsToContents', s1)
        self.assertIn('vua_dong', s2)
        self.assertNotIn('resizeRowsToContents', s2)


class TestLogTaiLai(unittest.TestCase):
    def test_tai_lai_ghi_loi_log(self):
        from pabt import app as ud
        from pabt.giao_dien import ghi_loi_log
        src = inspect.getsource(ud.CuaSoChinh.tai_lai)
        self.assertIn('ghi_loi_log', src)
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = td.name
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        ghi_loi_log('thử tải lại hộ')
        p = Path(td.name) / 'loi.log'
        self.assertTrue(p.is_file())
        self.assertIn('thử tải lại hộ', p.read_text(encoding='utf-8'))


class TestLenhModule(unittest.TestCase):
    def test_ds_lenh_du_ten(self):
        from pabt.app import LENH_THONG_KE, TRANG
        from pabt.lenh import ds_lenh

        class Gia:
            def __getattr__(self, ten):
                return lambda *a, **k: None

        ten = [t for t, _ in ds_lenh(Gia())]
        self.assertIn('Dự án mới…', ten)
        self.assertIn('Thoát', ten)
        self.assertIn(LENH_THONG_KE, ten)
        for t in TRANG:
            self.assertIn(t, ten)
        src = inspect.getsource(__import__('pabt.app', fromlist=['CuaSoChinh']).CuaSoChinh._tao_lenh)
        self.assertIn('ds_lenh', src)
        self.assertNotIn("'Dự án mới…', lambda", src)


class TestAiBoQuaTimeout(unittest.TestCase):
    def test_hoi_claude_co_gioi_han(self):
        from pabt.tro_ly import hoi_claude
        sig = inspect.signature(hoi_claude)
        self.assertIn('gioi_han', sig.parameters)

    def test_chay_nen_huy_het_gio(self):
        _app()
        from pabt.giao_dien import chay_nen_huy

        def ham():
            time.sleep(2)
            return 1

        kq = chay_nen_huy(None, ham, 'Đang nhờ trợ lý…', nut_huy='Bỏ qua', gioi_han=0.25)
        self.assertIsNone(kq)

    def test_chinh_dong_ocr_ai_timeout_mang_cat(self):
        from pabt import ocr_ho_so, tro_ly

        def treo():
            time.sleep(2)
            return 'Xoài: 1 cây'

        with mock.patch('pabt.tro_ly.hoi_claude', side_effect=lambda *a, **k: treo()):
            with self.assertRaises(tro_ly.LoiTroLy) as cm:
                ocr_ho_so.chinh_dong_ocr_ai(['Xoài: 16 cây'], gioi_han=0.2)
        self.assertIn('bỏ qua', str(cm.exception).lower())


if __name__ == '__main__':
    unittest.main()
