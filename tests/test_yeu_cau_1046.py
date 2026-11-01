"""1.0.46: Dán tài sản OCR, Phiếu kiểm đếm nối lập PA, giá đất lời văn, đơn giá thay cả nhóm, Ctrl+Shift+V."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_toc_do import _du_an


def _app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class CoSo(unittest.TestCase):
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


class TestDanTaiSanOcr(CoSo):
    def test_nut_mo_anh_va_dan_anh(self):
        from pabt import csdl
        from pabt.lap_pa import BoSoan, DanhMuc
        from pabt.man_hinh_phan_loai import HopDanTaiSan
        from pabt.nhap_tai_san import DichPhuongAn
        con = csdl.mo(str(_du_an(self.td, 1)))
        self.addCleanup(con.close)
        hop = HopDanTaiSan(None, '', dich=DichPhuongAn(BoSoan(con, 1, DanhMuc(con))))
        hop.im_lang = True
        self.addCleanup(hop.deleteLater)
        self.assertEqual(hop.b_anh.text(), 'Mở ảnh / PDF…')
        self.assertEqual(hop.b_clip.text(), 'Dán ảnh clipboard')
        self.assertEqual(hop.mo_anh_pdf(), [])

    def test_ocr_do_chu_roi_phan_loai(self):
        from pabt import csdl
        from pabt.lap_pa import BoSoan, DanhMuc
        from pabt.man_hinh_phan_loai import HopDanTaiSan
        from pabt.nhap_tai_san import DichPhuongAn
        con = csdl.mo(str(_du_an(self.td, 1)))
        self.addCleanup(con.close)
        hop = HopDanTaiSan(None, '', dich=DichPhuongAn(BoSoan(con, 1, DanhMuc(con))))
        hop.im_lang = True
        self.addCleanup(hop.deleteLater)
        with mock.patch('pabt.ocr.san_sang', return_value=''), mock.patch('pabt.ocr.doc_chu', return_value=['Xoài: 16 cây']):
            ds = hop.mo_anh_pdf(self.td / 'a.png')
        self.assertTrue(ds)
        self.assertIn('Xoài', hop.o_chu.toPlainText())


class TestPhieuDanTaiSan(CoSo):
    def test_nut_va_bam_kep(self):
        from pabt import csdl
        from pabt.man_hinh_kiem_dem import HopKiemDem
        p = _du_an(self.td, 2)
        con = csdl.mo(str(p))
        self.addCleanup(con.close)
        h = HopKiemDem(None, con, p, im_lang=True)
        self.addCleanup(h.close)
        self.assertTrue(h.b_dan.isEnabled())
        self.assertTrue(h.b_pa.isEnabled())
        h.bang.selectRow(0)
        self.assertIsNotNone(h._ma_hang())
        self.assertIsNone(h.mo_lap_pa(cho=False))


class TestDonGiaThayNhom(CoSo):
    def test_menu_va_hop_thay_the(self):
        from pabt.man_hinh_don_gia import HopBoDonGia
        from pabt.man_hinh_nhap_don_gia import CACH_CAP_NHAT, HopNhapDonGia
        d = HopBoDonGia(None, None, False)
        d.im_lang = True
        self.addCleanup(d.close)
        chu = [a.text() for a in d.b_cap.menu().actions() if a.text()]
        self.assertIn('Nạp từ file — thay cả nhóm theo văn bản mới…', chu)
        self.assertTrue(CACH_CAP_NHAT[1][1])
        self.assertIn('Thay cả nhóm', CACH_CAP_NHAT[1][0])
        hop = HopNhapDonGia(None, d, 'thử', dong=[['Tên', 'ĐVT', 'Đơn giá'], ['Nhà tạm', 'm2', '1000000']],
                            thay_the=True)
        hop.im_lang = True
        self.addCleanup(hop.close)
        self.assertTrue(hop.thay_the())


class TestGiaDatLoiVan(unittest.TestCase):
    def test_gia_tu_loi_van(self):
        from pabt import gia_dat_nq28 as nq
        from pabt.cap_nhat_gia_dat import _dong_tu_o, _gia_tu_loi_van
        dong = [
            ['Xã Thử'],
            ['Tên đường', 'Đất ở'],
            ['1', 'Đường tỉnh 769', '15.300'],
        ]
        with self.assertRaises(nq.LoiBangGia):
            _dong_tu_o([['Xã Thử'], ['1', 'Đường tỉnh 769', '15.300']], 'a.txt', 'Xã Thử')
        ra = _gia_tu_loi_van(dong, 'Xã Thử')
        self.assertTrue(ra)
        self.assertTrue(any('769' in (r.get('ten_duong') or '') for r in ra))


class TestPhimVaTroLy(CoSo):
    def test_ctrl_shift_v_va_tro_ly_chua_mo(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeySequence, QShortcut
        from pabt import __version__, lich_su_cap_nhat
        from pabt.app import LENH_CAN_DU_AN, CuaSoChinh
        w = CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        self.assertNotIn('Trợ lý (giải thích, soạn nháp)…', LENH_CAN_DU_AN)
        self.assertTrue(w.lenh['Trợ lý (giải thích, soạn nháp)…'].isEnabled())
        w.mo(str(_du_an(self.td, 1)))
        hop = w.mo_lap_pa(cho=False)
        phim = [s for s in hop.findChildren(QShortcut) if s.key() == QKeySequence('Ctrl+Shift+V')]
        self.assertEqual(len(phim), 1)
        self.assertEqual(phim[0].context(), Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.assertEqual(__version__, '1.0.47')
        self.assertEqual(lich_su_cap_nhat.MUC[0][0], '1.0.47')
