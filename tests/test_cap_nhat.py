"""Kiểm thử gói cập nhật .pabtcn: tạo, kiểm tra nguyên vẹn / phiên bản, cài, gỡ, nạp thay mã (chạy tiến trình riêng)."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from pabt import __version__, cap_nhat

GOC = Path(__file__).resolve().parents[1]


def _ma_nguon(td: Path, phien_ban: str, them=None) -> Path:
    """Bản chép mã nguồn với __version__ khác (và file thêm vào pabt/)."""
    g = td / 'nguon'
    shutil.copytree(GOC / 'pabt', g / 'pabt', ignore=shutil.ignore_patterns('__pycache__'))
    f = g / 'pabt' / '__init__.py'
    f.write_text(re.sub(r"__version__ = '[^']+'", f"__version__ = '{phien_ban}'", f.read_text(encoding='utf-8')),
                 encoding='utf-8')
    for ten, nd in (them or {}).items():
        (g / 'pabt' / ten).write_text(nd, encoding='utf-8')
    return g


class TestCapNhat(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')

    def tearDown(self):
        if self.cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self.cu
        shutil.rmtree(self.td, ignore_errors=True)

    def _goi(self, phien_ban='9.9.9', **kw):
        p = self.td / f'g_{phien_ban}.pabtcn'
        cap_nhat.tao_goi(_ma_nguon(self.td / phien_ban, phien_ban, kw.pop('them', None)), p, 'thử', **kw)
        return p

    def _chay(self, ma: str) -> str:
        r = subprocess.run([sys.executable, '-c', ma], cwd=GOC, capture_output=True, text=True, encoding='utf-8',
                           env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_tao_cai_go(self):
        p = self._goi()
        m = cap_nhat.doc_goi(p)
        self.assertEqual(m['phien_ban'], '9.9.9')
        self.assertIn('pabt/schema.sql', m['file'])
        self.assertFalse(any(f.endswith('.pabt') for f in m['file']))
        cap_nhat.cai(p)
        tt = cap_nhat.trang_thai()
        self.assertEqual((tt['da_cai'], tt['mo_ta'], tt['ban_goc']), ('9.9.9', 'thử', __version__))
        self.assertTrue(cap_nhat.go())
        self.assertIsNone(cap_nhat.trang_thai()['da_cai'])
        self.assertFalse(cap_nhat.go())

    def test_tu_choi(self):
        p = self._goi()
        hong = self.td / 'hong.pabtcn'
        with zipfile.ZipFile(p) as z, zipfile.ZipFile(hong, 'w') as w:
            for i in z.infolist():
                du = z.read(i)
                w.writestr(i, du + b'#' if i.filename == 'pabt/tien.py' else du)
        with self.assertRaisesRegex(cap_nhat.LoiCapNhat, 'bị hỏng'):
            cap_nhat.cai(hong)
        with self.assertRaisesRegex(cap_nhat.LoiCapNhat, 'không mới hơn'):
            cap_nhat.cai(self._goi('0.0.1'))
        with self.assertRaisesRegex(cap_nhat.LoiCapNhat, 'bộ cài đầy đủ'):
            cap_nhat.cai(self._goi('9.9.8', toi_thieu='99.0'))
        (self.td / 'x.pabtcn').write_text('abc')
        with self.assertRaisesRegex(cap_nhat.LoiCapNhat, 'không phải'):
            cap_nhat.doc_goi(self.td / 'x.pabtcn')
        self.assertIsNone(cap_nhat.trang_thai()['da_cai'])

    def test_khong_dong_goi_ma_loi_cu_phap(self):
        with self.assertRaisesRegex(cap_nhat.LoiCapNhat, 'cú pháp'):
            self._goi(them={'loi.py': 'def (:\n'})

    def test_nap_thay_ma(self):
        cap_nhat.cai(self._goi(them={'moi_them.py': 'CO = 1\n'}))
        ma = ('import nap_cap_nhat as n; n.nap(bat_buoc=True); import pabt, pabt.moi_them, pabt.csdl; '
              'print(pabt.__version__, n.BAN_GOC, n.DANG_DUNG, pabt.csdl.__file__)')
        pb, goc, dung, f = self._chay(ma).split(' ', 3)
        self.assertEqual((pb, goc, dung), ('9.9.9', __version__, '9.9.9'))
        self.assertIn('cap_nhat', f)
        self.assertTrue((cap_nhat.thu_muc() / 'dang_khoi_dong.txt').exists())
        # chưa khởi động tốt 2 lần liền -> tự tắt, chạy bản gốc
        (cap_nhat.thu_muc() / 'dang_khoi_dong.txt').write_text('2')
        self.assertEqual(self._chay(ma.replace(', pabt.moi_them', '').replace(', pabt.csdl.__file__', '')),
                         f'{__version__} {__version__} None')
        self.assertIn('không khởi động được', cap_nhat.trang_thai()['loi'])

    def test_nap_ban_loi_quay_ve_goc(self):
        cap_nhat.cai(self._goi(them={'loi_khi_nap.py': 'raise RuntimeError("hong")\n'}))   # gói đúng mã SHA-256 nhưng mã lỗi
        kq = self._chay('import nap_cap_nhat as n; n.nap(bat_buoc=True); import pabt, pabt.tien; '
                        'print(pabt.__version__, n.DANG_DUNG, hasattr(pabt.tien, "D"))')
        self.assertEqual(kq, f'{__version__} None True')
        self.assertIn('hong', cap_nhat.trang_thai()['loi'])

    def test_khong_chu_ky_so(self):
        """Không còn chữ ký số (người dùng yêu cầu bỏ hẳn từ 0.9.16): gói mới không có cap_nhat.sig; gói cũ có cap_nhat.sig
        (0.9.14, 0.9.15) vẫn đọc / cài / nạp được - file chữ ký bị bỏ qua; gói bị sửa mã vẫn bị từ chối (SHA-256)."""
        p = self._goi()
        with zipfile.ZipFile(p) as z:
            self.assertNotIn('cap_nhat.sig', z.namelist())
        cu = self.td / 'goi_cu_co_chu_ky.pabtcn'
        with zipfile.ZipFile(p) as z, zipfile.ZipFile(cu, 'w') as w:
            for i in z.infolist():
                w.writestr(i, z.read(i))
            w.writestr('cap_nhat.sig', 'ab' * 384)
        cap_nhat.cai(cu)
        self.assertEqual(cap_nhat.trang_thai()['da_cai'], '9.9.9')
        self.assertEqual(self._chay('import nap_cap_nhat as n; n.nap(bat_buoc=True); import pabt; print(pabt.__version__)'),
                         '9.9.9')
        cap_nhat.go()
        hong = self.td / 'hong_ma.pabtcn'
        with zipfile.ZipFile(p) as z, zipfile.ZipFile(hong, 'w') as w:
            for i in z.infolist():
                du = z.read(i)
                w.writestr(i, du + b'#' if i.filename == 'pabt/tien.py' else du)
        with self.assertRaisesRegex(cap_nhat.LoiCapNhat, 'bị hỏng'):
            cap_nhat.cai(hong)
        self.assertIsNone(cap_nhat.trang_thai()['da_cai'])

    def test_ban_da_cai_bi_sua_khong_nap(self):
        """Mã độc sửa / chèn file vào bản cập nhật đã cài (thư mục %APPDATA%): bộ nạp kiểm tra lại, không chạy mã đó."""
        ma = 'import nap_cap_nhat as n; n.nap(bat_buoc=True); import pabt; print(pabt.__version__)'
        goi = self._goi()
        for viec in ('sua', 'chen', 'pyc'):
            with self.subTest(viec):
                cap_nhat.cai(goi)
                d = cap_nhat.thu_muc()
                ban = d / (d / 'hien_hanh.txt').read_text(encoding='utf-8')
                if viec == 'sua':
                    f = ban / 'pabt' / 'tien.py'
                    f.write_text(f.read_text(encoding='utf-8') + '\nimport os  # chèn mã\n', encoding='utf-8')
                elif viec == 'chen':
                    (ban / 'pabt' / 'gian_diep.py').write_text('X = 1\n', encoding='utf-8')
                else:                                    # .pyc giả trong __pycache__: bị xóa trước khi nạp, bản vẫn chạy
                    (ban / 'pabt' / '__pycache__').mkdir()
                    (ban / 'pabt' / '__pycache__' / 'tien.cpython-38.pyc').write_bytes(b'gia')
                kq = self._chay(ma)
                if viec == 'pyc':
                    self.assertEqual(kq, '9.9.9')
                    self.assertFalse((ban / 'pabt' / '__pycache__').exists())
                else:
                    self.assertEqual(kq, __version__)
                    self.assertIn('đã bị sửa' if viec == 'sua' else 'file lạ', cap_nhat.trang_thai()['loi'])
                cap_nhat.go()

    def test_bo_cai_moi_hon_bo_qua_ban_cap_nhat(self):
        cap_nhat.cai(self._goi())
        d = cap_nhat.thu_muc()
        ten = (d / 'hien_hanh.txt').read_text(encoding='utf-8')
        f = d / ten / 'cap_nhat.json'
        f.write_text(f.read_text(encoding='utf-8').replace('"9.9.9"', '"0.0.2"'), encoding='utf-8')
        self.assertEqual(self._chay('import nap_cap_nhat as n; n.nap(bat_buoc=True); import pabt; print(pabt.__version__)'),
                         __version__)

    def test_hop_thoai(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from pabt.man_hinh_cap_nhat import HopCapNhat
        h = HopCapNhat()
        h.im_lang = True
        self.assertFalse(h.b_go.isEnabled())
        self.assertIsNone(h.cai_file(str(self.td / 'khong_co.pabtcn')))
        self.assertEqual(h.cai_file(str(self._goi()))['phien_ban'], '9.9.9')
        self.assertIn('9.9.9', h.lb.text())
        self.assertTrue(h.b_go.isEnabled())
        self.assertTrue(h.go_cap_nhat())
        self.assertIn('Chưa cài', h.lb.text())
        h.close()
        app.processEvents()


if __name__ == '__main__':
    unittest.main()
