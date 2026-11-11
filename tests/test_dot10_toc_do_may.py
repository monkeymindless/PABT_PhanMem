"""Đợt 10 (1.1.01): đo tốc độ máy người dùng (do_toc_do + lệnh do-toc-do), nhật ký khởi động, chế độ máy yếu chọn tay, nạp trước lúc rảnh."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, do_toc_do as dtd


class TestNhatKyKhoiDong(unittest.TestCase):
    def test_ghi_doc_giu_toi_da(self):
        td = Path(tempfile.mkdtemp())
        for i in range(dtd.GIU_KHOI_DONG + 5):
            dtd.ghi_khoi_dong(1000 + i, td)
        ds = dtd.doc_khoi_dong(td)
        self.assertEqual(len(ds), dtd.GIU_KHOI_DONG)
        self.assertEqual(ds[-1]['ms'], 1000 + dtd.GIU_KHOI_DONG + 4)
        dtd.ghi_khoi_dong(None, td)                     # không đo được: không ghi
        self.assertEqual(len(dtd.doc_khoi_dong(td)), dtd.GIU_KHOI_DONG)

    def test_file_hong_khong_lam_hong(self):
        td = Path(tempfile.mkdtemp())
        (td / dtd.TEN_NHAT_KY).write_text('{không phải json', encoding='utf-8')
        self.assertEqual(dtd.doc_khoi_dong(td), [])
        dtd.ghi_khoi_dong(1500, td)
        self.assertEqual([x['ms'] for x in dtd.doc_khoi_dong(td)], [1500])

    def test_ms_tu_luc_chay(self):
        ms = dtd.ms_tu_luc_chay()
        if os.name == 'nt':
            self.assertIsNotNone(ms)
            self.assertGreater(ms, 0)


class TestMayVaDia(unittest.TestCase):
    def test_thong_tin(self):
        tt = dtd.thong_tin()
        for k in ('cpu', 'so_luong', 'ram_mb', 'o_cai', 'o_tam', 'bit', 'may_yeu'):
            self.assertIn(k, tt)
        self.assertIn(tt['o_tam'], ('SSD', 'HDD', 'ổ mạng', 'USB / thẻ nhớ', 'không rõ'))
        self.assertEqual(dtd.loai_o_dia('\\\\may_chu\\chia_se\\a.pabt'), 'ổ mạng')

    def test_do_dia(self):
        kq = dtd.do_dia(tempfile.mkdtemp())
        self.assertGreater(kq['ghi_dia_mb_giay'], 0)
        self.assertGreater(kq['luu_sqlite'], 0)

    def test_bao_cao_va_nhan_xet(self):
        tt = dict(phan_mem='1.1.01', cpu='CPU thử', so_luong=2, ram_mb=3800, may_yeu=True, o_cai='HDD', o_tam='HDD', bit=32,
                  he_dieu_hanh='Windows-7', python='3.8.10', dong_goi=True)
        dia = dict(ghi_dia_mb_giay=40.0, luu_sqlite=120.0)
        gd = dict(so_ho=1000, mo_du_an=900.0, luu_1_ho=20.0, xuat_danh_sach=5000.0)
        kd = [dict(luc='2026-11-11T08:00:00', ms=14000, phien_ban='1.1.01'), dict(luc='2026-11-11T09:00:00', ms=2100, phien_ban='1.1.01')]
        bc = dtd.bao_cao(tt, dia, gd, kd)
        self.assertIn('Xuất danh sách hộ ra Excel | 5.000', bc)
        self.assertIn('CHẬM', bc)
        nx = ' '.join(dtd.ket_luan(tt, dia, gd, kd))
        for chu in ('HDD', 'SSD', 'diệt virus', 'RAM', '14,0 giây'.replace(',', '.')):
            self.assertIn(chu, nx)
        self.assertEqual(dtd.ket_luan(dict(o_cai='SSD', o_tam='SSD', ram_mb=16000), dict(luu_sqlite=5.0), dict(mo_du_an=500.0), []),
                         ['Máy đáp ứng tốt: mọi thao tác đo được đều trong ngưỡng.'])


class TestDoGiaoDien(unittest.TestCase):
    def test_do_giao_dien_du_an_gia_lap(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        td = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(Path(td) / 'may')}):
            kq = dtd.do_giao_dien(td, so_ho=60)
        for k in ('mo_cua_so_chinh', 'mo_du_an', 'lap_pa_lan_dau', 'chuyen_ho', 'luu_1_ho', 'man_hinh_chinh', 'kiem_tra_loi',
                  'kiem_tra_loi_lan_sau', 'xuat_danh_sach', 'hop_500_widget'):
            self.assertGreater(kq[k], 0, k)
        self.assertTrue((Path(td) / 'danh_sach.xlsx').is_file())


class TestCheDoMayYeu(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': self.td})
        self.env.start()
        os.environ.pop('PABT_MAY_YEU', None)
        csdl._MAY_YEU.clear()

    def tearDown(self):
        self.env.stop()
        csdl._MAY_YEU.clear()

    def test_bat_tat_tu_dong(self):
        self.assertEqual(csdl.che_do_may_yeu(), 'tu_dong')
        csdl.dat_che_do_may_yeu('bat')
        self.assertTrue(csdl.la_may_yeu())
        csdl.dat_che_do_may_yeu('tat')
        self.assertFalse(csdl.la_may_yeu())
        csdl.dat_che_do_may_yeu('tu_dong')
        self.assertFalse((Path(self.td) / csdl.FILE_MAY_YEU).exists())
        self.assertEqual(csdl.dat_che_do_may_yeu('linh_tinh'), 'tu_dong')

    def test_bien_moi_truong_thang(self):
        csdl.dat_che_do_may_yeu('tat')
        with mock.patch.dict(os.environ, {'PABT_MAY_YEU': '1'}):
            self.assertTrue(csdl.la_may_yeu())


class TestNapTruoc(unittest.TestCase):
    def test_tat_bang_bien_moi_truong(self):
        from PySide6.QtCore import QTimer
        from pabt import app as ud
        with mock.patch.dict(os.environ, {'PABT_NAP_TRUOC': '0'}), mock.patch.object(QTimer, 'singleShot') as hen:
            ud.nap_truoc_luc_ranh()
        hen.assert_not_called()

    def test_nap_du_module(self):
        import time
        from PySide6.QtWidgets import QApplication
        from pabt import app as ud
        qa = QApplication.instance() or QApplication([])
        with mock.patch.dict(os.environ, {'PABT_NAP_TRUOC': '1'}):
            ud.nap_truoc_luc_ranh(0)
        han = time.time() + 15
        while time.time() < han and not all(m in sys.modules for m in ud.NAP_TRUOC_GIAO_DIEN):
            qa.processEvents()
            time.sleep(0.02)
        for m in ud.NAP_TRUOC_GIAO_DIEN:
            self.assertIn(m, sys.modules)


class TestNutDoTocDo(unittest.TestCase):
    def test_nut_chay_tien_trinh_con_va_doc_bao_cao(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_chan_doan import HopChanDoanHeThong
        tm = Path(tempfile.mkdtemp())
        dtd.ghi_khoi_dong(2345, tm)
        with mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(tm)}):
            h = HopChanDoanHeThong(im_lang=True)
            ra = h.do_toc_do(tm / 'bc.md', so_ho=60, cho=False)
        self.assertIsNotNone(ra)
        bc = ra.read_text(encoding='utf-8')
        self.assertIn('Mở dự án', bc)
        self.assertIn('2.345 ms', bc)                     # nhật ký khởi động THẬT của máy được đọc trước khi chuyển thư mục tạm
        self.assertTrue(h.nhan_xet_toc_do)
        self.assertEqual(sorted(p.name for p in tm.iterdir()), ['bc.json', 'bc.md', dtd.TEN_NHAT_KY])   # không ghi gì khác vào máy
        h.close()


class TestGoiChanDoan(unittest.TestCase):
    def test_kem_khoi_dong_va_bao_cao_toc_do(self):
        import zipfile
        from pabt import chua_benh_csdl
        tm = Path(tempfile.mkdtemp())
        dtd.ghi_khoi_dong(1800, tm)
        (tm / 'bao_cao_toc_do').mkdir()
        (tm / 'bao_cao_toc_do' / 'TocDo_20261111_080000.md').write_text('# cũ', encoding='utf-8')
        (tm / 'bao_cao_toc_do' / 'TocDo_20261111_090000.md').write_text('# mới nhất', encoding='utf-8')
        z = chua_benh_csdl.dong_goi_chan_doan(Path(tempfile.mkdtemp()) / 'g.zip', thu_muc_may=tm)
        with zipfile.ZipFile(z) as f:
            self.assertIn('khoi_dong.json', f.namelist())
            self.assertEqual(f.read('bao_cao_toc_do.md').decode('utf-8'), '# mới nhất')


if __name__ == '__main__':
    unittest.main()
