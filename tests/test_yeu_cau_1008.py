"""1.0.08 (người dùng 20/10/2026): máy cấu hình yếu (nhận diện, OCR 1 luồng, xem trước <= 120 dpi, gc sau khi đóng / xuất), đổi cỡ
chữ nhanh (bỏ trang ẩn), kéo thả file vào cửa sổ, sao lưu tự động khi mở dự án, bộ lọc mẫu áp cả cỡ chữ."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl  # noqa: E402

from tests.test_toc_do import _du_an  # noqa: E402


class _Co(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))

    def tearDown(self):
        self.doCleanups()
        self.tmp.cleanup()


class TestMayYeu(_Co):
    def test_nhan_dien_va_ep(self):
        from pabt import csdl
        ram = csdl.ram_vat_ly_mb()
        if os.name == 'nt':
            self.assertGreater(ram, 0)
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '1'}):
            self.assertTrue(csdl.la_may_yeu())
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '0'}):
            self.assertFalse(csdl.la_may_yeu())
        csdl._MAY_YEU.clear()
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': ''}), mock.patch.object(csdl, 'ram_vat_ly_mb', lambda: 2048):
            self.assertTrue(csdl.la_may_yeu())                       # RAM 2 GB
        csdl._MAY_YEU.clear()
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': ''}), mock.patch.object(csdl, 'ram_vat_ly_mb', lambda: 16384), \
                mock.patch.object(os, 'cpu_count', lambda: 2):
            self.assertTrue(csdl.la_may_yeu())                       # CPU 2 nhân
        csdl._MAY_YEU.clear()

    def test_ocr_mot_luong_va_xem_truoc_120dpi(self):
        from pabt import ocr
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '1'}):
            self.assertEqual(ocr.moi_truong_ocr()['OMP_THREAD_LIMIT'], ocr.LUONG_OCR_MAY_YEU)
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '0'}):
            self.assertEqual(ocr.moi_truong_ocr().get('OMP_THREAD_LIMIT'), os.environ.get('OMP_THREAD_LIMIT'))
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import xem_truoc_tai_lieu as xt
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '1'}):
            man = QApplication.primaryScreen()
            self.assertAlmostEqual(xt.he_so_xem_toi_da(), xt.DPI_XEM_MAY_YEU / man.logicalDotsPerInch(), places=3)
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '0'}):
            self.assertGreater(xt.he_so_xem_toi_da(), 10)

    def test_giai_phong_bo_nho_chi_may_yeu(self):
        from pabt import csdl
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '0'}), mock.patch('gc.collect') as gc:
            csdl.giai_phong_bo_nho()
            gc.assert_not_called()
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '1'}), mock.patch('gc.collect', return_value=3) as gc:
            self.assertEqual(csdl.giai_phong_bo_nho(), 3)
            gc.assert_called_once()

    def test_bong_do_tat_tren_may_yeu(self):
        from PySide6.QtWidgets import QApplication, QFrame
        QApplication.instance() or QApplication([])
        from pabt import giao_dien
        import pabt
        f = QFrame()
        with mock.patch.dict(os.environ, {'PABT_HIEU_UNG_BONG': '1', 'PABT_MAY_YEU': '1'}):
            giao_dien.do_bong(f)
        self.assertIsNone(f.graphicsEffect())
        if not getattr(pabt, 'QT5', False):
            with mock.patch.dict(os.environ, {'PABT_HIEU_UNG_BONG': '1', 'PABT_MAY_YEU': '0'}):
                giao_dien.do_bong(f)
            self.assertIsNotNone(f.graphicsEffect())


class TestSaoLuuTuDong(_Co):
    def test_giu_5_ban_moi_nhat(self):
        from pabt import csdl
        f = _du_an(self.td, 3)
        con = csdl.mo(f)
        self.addCleanup(con.close)
        ra = []
        for i in range(7):
            with mock.patch.object(csdl, 'datetime') as dt:
                dt.now.return_value = __import__('datetime').datetime(2026, 10, 20, 10, 0, i)
                ra.append(csdl.sao_luu_tu_dong(con, f))
        ds = csdl.ds_sao_luu_tu_dong(f)
        self.assertEqual(len(ds), csdl.SAO_LUU_GIU)
        self.assertEqual(ds[0], ra[-1])                                 # mới nhất trước
        import sqlite3
        c2 = sqlite3.connect(str(ds[0]))
        self.assertEqual(c2.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 3)
        c2.close()
        self.assertFalse(list(csdl.thu_muc_sao_luu_tu_dong().glob('*.tmp')))

    def test_mo_du_an_tao_sao_luu_khong_khi_chi_xem(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from pabt import app as ud, csdl
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        f = _du_an(self.td, 2)
        with mock.patch.object(ud, 'SAO_LUU_SAU_MS', 0):
            w.mo(str(f))
            for _ in range(5):
                app.processEvents()
        self.assertEqual(len(csdl.ds_sao_luu_tu_dong(f)), 1)
        w.dong_du_an_lenh()
        with mock.patch.object(ud, 'SAO_LUU_SAU_MS', 0):
            w.mo(str(f), chi_doc=True)
            for _ in range(5):
                app.processEvents()
        self.assertEqual(len(csdl.ds_sao_luu_tu_dong(f)), 1)            # mở chỉ xem: không sao lưu


class TestKeoTha(_Co):
    def test_nhan_file_va_chuyen_lenh(self):
        from PySide6.QtCore import QMimeData, QUrl
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        self.assertTrue(w.acceptDrops())
        md = QMimeData()
        md.setUrls([QUrl.fromLocalFile(str(self.td / 'a.txt')), QUrl.fromLocalFile(str(self.td / 'b.larc'))])
        ev = mock.Mock()
        ev.mimeData.return_value = md
        self.assertEqual([Path(x).name for x in w._file_keo(ev)], ['b.larc'])
        goi = []
        with mock.patch.object(w, 'mo', lambda p: goi.append(('mo', p))), \
                mock.patch.object(w, 'cap_nhat_phan_mem', lambda p: goi.append(('cn', p))), \
                mock.patch.object(w, 'nhap_goi_mau', lambda p: goi.append(('gm', p))), \
                mock.patch.object(w, 'nhap_excel', lambda p: goi.append(('xl', p))):
            for ten, loai in (('d.larc', 'du_an'), ('d.PABT', 'du_an'), ('g.larcud', 'cap_nhat'), ('m.pabtcfg', 'goi_mau'),
                              ('x.xlsx', 'excel'), ('k.docx', '')):
                self.assertEqual(w.mo_file_keo(str(self.td / ten)), loai)
        self.assertEqual([g[0] for g in goi], ['mo', 'mo', 'cn', 'gm', 'xl'])


class TestDoiTyLeNhanh(_Co):
    def test_bo_trang_an_truoc_khi_doi_co(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from pabt import app as ud, giao_dien
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(_du_an(self.td, 4)))
        for i in range(len(ud.TRANG)):
            w.mo_trang(i)
        w.mo_trang(ud.TRANG_THEO_DOI)
        app.processEvents()
        self.assertGreaterEqual(len(w.khung_trang), 2)
        cu = giao_dien.TY_LE[0]
        self.addCleanup(lambda: giao_dien.dat_ty_le(cu, luu=False))
        giao_dien.dat_ty_le(round(cu + 0.1, 2), luu=False)
        self.assertEqual(set(w.khung_trang), {ud.STACK_CUA_TRANG[ud.TRANG_THEO_DOI]})   # chỉ giữ trang đang xem
        w.mo_trang(ud.TRANG_TONG_HOP)                                   # mở lại: dựng lại trang
        self.assertIn(ud.STACK_CUA_TRANG[ud.TRANG_TONG_HOP], w.khung_trang)


class TestBoLocMau(_Co):
    def test_ap_chuan_co_chu(self):
        from pabt import in_an, mau_in_nhung
        f = self.td / 'BTH.xlsx'
        f.write_bytes(mau_in_nhung.lay_bytes_mau('IN_BANGTONGHOP'))      # mẫu chuẩn cũ: chữ 20 pt
        in_an.ap_chuan_trang_mau(f, 'tong_hop')
        ws = openpyxl.load_workbook(f).active
        co = {float(o.font.sz) for o in ws._cells.values() if isinstance(o.value, str) and o.value.strip()}
        self.assertEqual(co, {in_an.CO_NOI_DUNG, in_an.CO_TIEU_DE})
        self.assertEqual((ws.page_setup.paperSize, int(ws.page_setup.scale)), (8, in_an.TI_LE_BTH))


if __name__ == '__main__':
    unittest.main()
