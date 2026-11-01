"""Phương án đột phá 8 (30/10/2026): cỗ máy thời gian - mốc khôi phục theo giờ, so sánh, khôi phục, thử trước thao tác hàng loạt.
Dự án GIẢ LẬP (tests.test_toc_do._du_an); thư mục máy tạm (PABT_THU_MUC_MAY)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pabt import co_may_thoi_gian as cm
from pabt import csdl
from tests.test_toc_do import _du_an


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_cmtg_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.f = _du_an(self.td, 6)
        self.con = csdl.mo(self.f)

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)

    def _doi_ten(self, ma, ten):
        with self.con:
            self.con.execute('UPDATE ho SET ho_ten = ? WHERE ma_ho = ?', (ten, ma))


class TestMoc(_Co):
    def test_chup_chi_khi_doi(self):
        m = cm.chup_moc(self.con, self.f, 'mo')
        self.assertTrue(m.file.is_file() and m.file.with_suffix('.json').is_file())
        self.assertEqual(m.so_ho, 6)
        self.assertIsNotNone(m.tong)
        self.assertIsNone(cm.chup_moc(self.con, self.f))                     # chưa đổi gì: không chụp lại
        self._doi_ten(1, 'Đổi tên')
        self.assertIsNotNone(cm.chup_moc(self.con, self.f))
        self.assertIsNotNone(cm.chup_moc(self.con, self.f, 'tay', bat_buoc=True))
        ds = cm.ds_moc(self.f)
        self.assertEqual([x.ly_do for x in ds], ['tay', 'tu_dong', 'mo'])
        self.con.execute('BEGIN')
        self.assertIsNone(cm.chup_moc(self.con, self.f, bat_buoc=True))      # giữa giao dịch: không chụp
        self.con.rollback()
        # mốc là bản đọc được, đúng trạng thái lúc chụp
        c = csdl.mo(ds[-1].file, chi_doc=True)
        self.assertNotEqual(c.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0], 'Đổi tên')
        c.close()

    def test_lich_giu_moc(self):
        tm = cm.thu_muc_du_an(self.f)
        tm.mkdir(parents=True)
        bay_gio = datetime(2026, 10, 30, 12, 0, 0)
        for gio in range(0, 24 * 40, 6):                                    # mỗi 6 giờ một mốc, 40 ngày
            luc = bay_gio - timedelta(hours=gio)
            ten = f'{luc:%Y%m%d_%H%M%S}.larc'
            (tm / ten).write_bytes(b'x')
            (tm / ten).with_suffix('.json').write_text(json.dumps(dict(file=ten, luc=luc.isoformat(), ly_do='tu_dong')), 'utf-8')
        tay = bay_gio - timedelta(days=60)
        (tm / 'tay.larc').write_bytes(b'x')
        (tm / 'tay.json').write_text(json.dumps(dict(file='tay.larc', luc=tay.isoformat(), ly_do='tay')), 'utf-8')
        cm.don_dep(self.f, bay_gio)
        ds = cm.ds_moc(self.f)
        moi = [m for m in ds if bay_gio - m.luc <= timedelta(hours=cm.GIU_GIO)]
        self.assertEqual(len(moi), 5)                                       # 24 giờ: đủ mọi mốc (0, 6, 12, 18, 24)
        cu = [m for m in ds if timedelta(hours=cm.GIU_GIO) < bay_gio - m.luc and m.ly_do != 'tay']
        self.assertEqual(len({m.luc.date() for m in cu}), len(cu))          # sau đó mỗi ngày một mốc
        self.assertTrue(all(bay_gio - m.luc <= timedelta(days=cm.GIU_NGAY) for m in cu))
        self.assertIn('tay', [m.ly_do for m in ds])                         # mốc thủ công luôn giữ
        self.assertEqual(len(list(tm.glob('*.larc'))), len(ds))             # bỏ cả file dữ liệu lẫn mô tả

    def test_so_sanh_va_khoi_phuc(self):
        m = cm.chup_moc(self.con, self.f, 'tay', bat_buoc=True)
        self._doi_ten(2, 'Tên mới')
        with self.con:
            self.con.execute('UPDATE ct_khoan SET so_luong = so_luong * 3 WHERE ma_ho = 3')
        from pabt import ho_so
        ho_so.xoa_nhieu_ho(self.con, [5])
        k = cm.so_sanh_moc(self.con, m)
        self.assertEqual((k.so_ho_truoc, k.so_ho_sau), (6, 5))
        self.assertEqual([x[0] for x in k.bo], [5])
        self.assertIn(3, [x[0] for x in k.doi])
        self.assertIn(2, [x[0] for x in k.doi_thong_tin])
        chu = '\n'.join(cm.chu_khac_biet(k))
        self.assertIn('Hộ bị xóa: 1 hộ', chu)
        self.con.close()
        truoc = cm.khoi_phuc(self.f, m)
        self.assertEqual(truoc.ly_do, 'truoc_khoi_phuc')
        self.con = csdl.mo(self.f)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 6)
        self.assertTrue(cm.so_sanh_file(m.file, self.f).khong_doi)
        self.assertEqual(cm.so_sanh_file(truoc.file, self.f).so_ho_truoc, 5)    # quay lại được trạng thái trước khi khôi phục

    def test_thu_truoc(self):
        from pabt import ho_so
        thu = cm.thu_truoc(self.con, lambda c: ho_so.xoa_nhieu_ho(c, [1, 2]))
        self.assertIsNone(thu.loi)
        self.assertEqual(sorted(x[0] for x in thu.khac.bo), [1, 2])
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 6)       # dự án thật không đổi

        def loi(c):
            raise ValueError('hỏng')
        thu = cm.thu_truoc(self.con, loi)
        self.assertIsInstance(thu.loi, ValueError)
        self.assertTrue(thu.khac.khong_doi)


class TestManHinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('không có Qt')
        cls.app = QApplication.instance() or QApplication([])

    def test_cua_so_chinh(self):
        from pabt.app import CuaSoChinh
        td = Path(tempfile.mkdtemp(prefix='pabt_cmtg_mh_'))
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
        w = CuaSoChinh()
        try:
            f = _du_an(td, 4)
            w.mo(f, chi_doc=False)
            self.assertTrue(w.dong_ho_moc.isActive())
            self.assertTrue(w.lenh['Cỗ máy thời gian (mốc khôi phục)…'].isEnabled())
            m = w.chup_moc('tay', bat_buoc=True)
            with w.con:
                w.con.execute("UPDATE ho SET ho_ten = 'Sửa nhầm' WHERE ma_ho = 1")
            h = w.co_may_thoi_gian(cho=False)
            h.im_lang = True
            self.assertGreaterEqual(len(h.ds), 1)
            r = next(i for i, x in enumerate(h.ds) if x.file == m.file)
            h.bang.selectRow(r)
            k = h.xem_khac()
            self.assertEqual([x[0] for x in k.doi_thong_tin], [1])
            self.assertIn('Từ mốc', h.o_kq.toPlainText())
            self.assertTrue(h.khoi_phuc(xac_nhan=False))
            self.assertNotEqual(w.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = 1').fetchone()[0], 'Sửa nhầm')
            self.assertIn('truoc_khoi_phuc', [x.ly_do for x in cm.ds_moc(f)])
            from pabt import ho_so
            self.assertTrue(w.xem_truoc_thao_tac('Xóa thử', lambda c: ho_so.xoa_nhieu_ho(c, [2]), hoi=False))
            self.assertIn('truoc_thao_tac', [x.ly_do for x in cm.ds_moc(f)])
            self.assertEqual(w.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 4)
            h.deleteLater()
            w.dong_du_an()
            self.assertFalse(w.dong_ho_moc.isActive())
            self.assertFalse(w.lenh['Cỗ máy thời gian (mốc khôi phục)…'].isEnabled())
        finally:
            w.dong_du_an()
            w.close()
            if cu is None:
                os.environ.pop('PABT_THU_MUC_MAY', None)
            else:
                os.environ['PABT_THU_MUC_MAY'] = cu
            shutil.rmtree(td, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
