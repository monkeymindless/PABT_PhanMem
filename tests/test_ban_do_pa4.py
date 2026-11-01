"""Phương án đột phá 4 (người dùng 30/10/2026): bản đồ làm trung tâm trên máy tính - tô màu theo đồng thuận / tiến độ theo hộ / lệch diện
tích (ban_do_cad.lech_dien_tich), nền ảnh vệ tinh (nen_ban_do: ô Web Mercator, lưu đệm, chỉ nhận JPEG / PNG; tải ở luồng phụ - NapNen),
menu chuột phải thửa. Bản đồ, hộ, ảnh nền: GIẢ LẬP; KHÔNG gọi mạng (tải ô thay bằng hàm giả)."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import ban_do_cad, ban_do_kml, csdl, nen_ban_do
from tests.test_ban_do_kml import _KhongFileBentley, _kml
from tests.test_toc_do import _du_an


def _png() -> bytes:
    """Ảnh PNG 2 x 2 hợp lệ (không cần Qt)."""
    import struct
    import zlib

    def khoi(loai, du):
        return struct.pack('>I', len(du)) + loai + du + struct.pack('>I', zlib.crc32(loai + du) & 0xFFFFFFFF)
    tho = b''.join(b'\x00' + b'\x40\x80\xc0' * 2 for _ in range(2))
    return (b'\x89PNG\r\n\x1a\n' + khoi(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0)) +
            khoi(b'IDAT', zlib.compress(tho)) + khoi(b'IEND', b''))


def _thua(**k) -> ban_do_cad.ThuaBanDo:
    d = {f: None for f in ban_do_cad.ThuaBanDo.__dataclass_fields__}
    d.update(so_to='1', so_thua='1', loai_dat='ONT', toa_do=[(0, 0), (1, 0), (1, 1)], dt_hinh='100', ma_ho=1, ho_ten='A',
             trang_thai='chua')
    d.update(k)
    return ban_do_cad.ThuaBanDo(**d)


class TestLechDienTich(unittest.TestCase):
    def test_cac_muc(self):
        f = ban_do_cad.lech_dien_tich
        self.assertEqual(f(_thua(ma_ho=None))[0], 'khong_gan')
        self.assertEqual(f(_thua(dt_thu_hoi=None))[0], 'chua_dt')
        self.assertEqual(f(_thua(dt_thu_hoi='0'))[0], 'chua_dt')
        self.assertEqual(f(_thua(dt_thu_hoi='101'))[0], 'khop')              # 1%
        self.assertEqual(f(_thua(dt_thu_hoi='95'))[0], 'lech_nhe')           # 5,3%
        self.assertEqual(f(_thua(dt_thu_hoi='80'))[0], 'lech_nhieu')         # 25%
        # có ranh thu hồi: so DT trong ranh với DT thu hồi (không so DT hình thửa)
        k, ty, bd, hs, cach = f(_thua(dt_hinh='500', dt_trong_ranh='100', dt_thu_hoi='100', dt_nguyen_thua='500'))
        self.assertEqual((k, ty, str(bd), str(hs)), ('khop', 0, '100', '100'))
        self.assertIn('trong ranh', cach)
        # không ranh: DT hình so với DT nguyên thửa (có) - thu hồi một phần thửa không bị báo lệch
        self.assertEqual(f(_thua(dt_hinh='500', dt_thu_hoi='100', dt_nguyen_thua='502'))[0], 'khop')
        self.assertEqual(f(_thua(dt_hinh='abc', dt_thu_hoi='100'))[0], 'chua_dt')    # số hỏng: không lỗi


class TestNenBanDo(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_nen_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        p = mock.patch.object(nen_ban_do, 'thu_muc_dem', lambda: self.td / 'esri')
        p.start()
        self.addCleanup(p.stop)

    def test_o_va_goc(self):
        for z in (10, 15, 17):
            x, y = nen_ban_do.o_tu_toa_do(11.1, 107.0, z)
            vd0, kd0 = nen_ban_do.goc_o(z, x, y)
            vd1, kd1 = nen_ban_do.goc_o(z, x + 1, y + 1)
            self.assertTrue(vd1 <= 11.1 <= vd0 and kd0 <= 107.0 <= kd1, z)     # điểm nằm trong ô của nó

    def test_ds_o(self):
        nho = (11.10, 11.101, 107.0, 107.001)                       # khu ~100 m: mức sâu nhất
        z, ds = nen_ban_do.ds_o(nho)
        self.assertEqual(z, nen_ban_do.Z_TOI_DA)
        self.assertTrue(1 <= len(ds) <= nen_ban_do.O_TOI_DA)
        lon = (10.5, 11.5, 106.5, 107.5)                            # khu 100 km: mức thấp, vẫn không quá số ô tối đa
        z2, ds2 = nen_ban_do.ds_o(lon)
        self.assertLess(z2, z)
        self.assertLessEqual(len(ds2), nen_ban_do.O_TOI_DA)
        self.assertTrue(nen_ban_do.trong_vn(nho))
        self.assertFalse(nen_ban_do.trong_vn((0.0, 0.001, 0.0, 0.001)))       # tọa độ giả định (không phải VN-2000)

    def test_tai_o_luu_dem_va_chi_nhan_anh(self):
        anh = _png()
        url = []
        self.assertEqual(nen_ban_do.tai_o(17, 1, 2, lay=lambda u: url.append(u) or anh), anh)
        self.assertEqual(url, [nen_ban_do.URL.format(z=17, x=1, y=2)])
        self.assertTrue((self.td / 'esri' / '17' / '1' / '2.png').is_file())

        def mat_mang(u):
            raise OSError('mất mạng')
        self.assertEqual(nen_ban_do.tai_o(17, 1, 2, lay=mat_mang), anh)       # đã lưu đệm: xem được khi mất mạng
        self.assertIsNone(nen_ban_do.tai_o(17, 9, 9, lay=mat_mang))
        self.assertIsNone(nen_ban_do.tai_o(17, 3, 3, lay=lambda u: b'MZ\x90\x00' + b'\x00' * 40))   # không phải ảnh
        self.assertIsNone(nen_ban_do.tai_o(17, 4, 4, lay=lambda u: b'<html>loi</html>'))
        self.assertIsNone(nen_ban_do.tai_o(17, 5, 5, lay=lambda u: anh + b'\x00' * nen_ban_do.KICH_TOI_DA))
        self.assertFalse((self.td / 'esri' / '17' / '3').exists())


class TestManHinhBanDo(_KhongFileBentley):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('không có Qt')
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.td = Path(tempfile.mkdtemp(prefix='pabt_pa4_'))
        self.addCleanup(shutil.rmtree, self.td, True)
        f = self.td / 'ban_do.kml'
        f.write_text(_kml(), encoding='utf-8')
        self.con = csdl.mo(_du_an(self.td, 4))
        self.addCleanup(self.con.close)
        with self.con:
            self.con.execute("UPDATE thua SET so_to = 'TK126-K6', so_thua = '34' WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua "
                             "WHERE ma_ho = 3)")
        ban_do_cad.luu(self.con, ban_do_kml.phan_tich_kml(f, kinh_tuyen=107.75))
        p = mock.patch.object(nen_ban_do, 'thu_muc_dem', lambda: self.td / 'nen')
        p.start()
        self.addCleanup(p.stop)

    def _hop(self, **k):
        from pabt.man_hinh_ban_do import HopBanDo
        h = HopBanDo(self.con, **k)
        h.im_lang = True

        def dong():
            h.done(0)
            h.deleteLater()
            self.app.processEvents()
        self.addCleanup(dong)
        return h

    def test_doi_cach_to_mau_va_chu_giai(self):
        h = self._hop()
        h.cb_to.setCurrentIndex(h.cb_to.findData(None))                       # tất cả các tờ
        self.assertFalse(h.o_nen.isChecked())                                  # nền vệ tinh mặc định TẮT
        self.assertEqual(len(h.view.thua), 2)
        self.assertEqual(set(h.lb_dem), set(ban_do_cad.TRANG_THAI))
        self.assertIn('đồng thuận', h.lb_tong.text())
        h.cb_mau.setCurrentIndex(h.cb_mau.findData('tien_do'))
        from pabt import pheu_tien_do
        self.assertEqual(list(h.lb_dem), [k for k, _ in pheu_tien_do.GIAI_DOAN_HO] + ['khong_gan'])
        gd = {x.ma_ho: x.giai_doan for x in pheu_tien_do.tinh(self.con).ho}
        self.assertEqual({it.t.ma_ho: it.khoa_mau for it in h.view.thua}, {m: gd[m] for m in (2, 3)})
        self.assertEqual(sum(int(lb.text().rsplit(': ', 1)[1]) for lb in h.lb_dem.values()), 2)   # chú giải đếm đủ số thửa
        self.assertIn('đã bàn giao', h.lb_tong.text())
        h.cb_mau.setCurrentIndex(h.cb_mau.findData('lech_dt'))
        self.assertEqual(list(h.lb_dem), list(ban_do_cad.LECH_DT))
        self.assertEqual({it.khoa_mau for it in h.view.thua} - set(ban_do_cad.LECH_DT), set())
        self.assertIn('lệch trên 10%', h.lb_tong.text())

    def test_nen_ve_tinh_tai_o_luong_phu(self):
        anh = _png()
        goi = []
        with mock.patch.object(nen_ban_do, 'tai_o', lambda z, x, y: goi.append((z, x, y)) or anh):
            h = self._hop()
            h.cb_nen.setCurrentIndex(h.cb_nen.findData('ve_tinh'))           # một lớp ảnh (mặc định "Vệ tinh + tên" có 3 lớp)
            h.o_nen.setChecked(True)
            self.assertTrue(h.nen.cho_xong(10))
        self.assertTrue(goi)
        self.assertEqual(len(h.view.o_nen), len(goi))                           # mọi ô đã đặt dưới các thửa
        self.assertTrue(all(o.zValue() < 0 for o in h.view.o_nen))
        self.assertTrue(h.lb_nguon.isVisibleTo(h))                              # ghi nguồn ảnh khi bật nền
        self.assertIn(f'{len(goi)}/{len(goi)}', h.lb.text())
        # ô ảnh nền không chặn bấm: bấm giữa thửa vẫn mở hộ
        mo = []
        h.mo_ho = mo.append
        h.resize(900, 600)
        h.view.resize(800, 500)
        h.view.vua()
        it = next(i for i in h.view.thua if i.t.ma_ho is not None)
        self.assertEqual(h.view.bam_diem(h.view.mapFromScene(it.sceneBoundingRect().center())), it.t.ma_ho)
        self.assertEqual(mo, [it.t.ma_ho])
        h.o_nen.setChecked(False)                                              # tắt: bỏ ảnh nền
        self.assertEqual(h.view.o_nen, [])
        self.assertFalse(h.lb_nguon.isVisibleTo(h))

    def test_nen_loi_mang_va_toa_do_gia_dinh(self):
        with mock.patch.object(nen_ban_do, 'tai_o', lambda z, x, y, **k: None):
            h = self._hop()
            h.o_nen.setChecked(True)
            self.assertTrue(h.nen.cho_xong(10))
        self.assertEqual(h.view.o_nen, [])
        self.assertIn('không tải được', h.lb.text())
        with mock.patch.object(nen_ban_do, 'trong_vn', return_value=False):
            self.assertFalse(h.nap_nen())
        self.assertIn('không phải VN-2000', h.lb.text())

    def test_menu_chuot_phai(self):
        mo = []
        h = self._hop(mo_ho=mo.append)
        it = next(i for i in h.view.thua if i.t.ma_ho is not None)
        m = h.menu_cho_thua(it.t)
        ten = [a.text() for a in m.actions()]
        self.assertTrue(ten[0].startswith('Mở phương án hộ'))
        m.actions()[0].trigger()
        self.assertEqual(mo, [it.t.ma_ho])
        m.actions()[1].trigger()
        from PySide6.QtWidgets import QApplication
        self.assertEqual(QApplication.clipboard().text(), f'Thửa {it.t.so_thua} tờ {it.t.so_to}')
        m.deleteLater()
        khong = ban_do_cad.ThuaBanDo(**{**it.t.__dict__, 'ma_ho': None})
        m2 = h.menu_cho_thua(khong)                                           # thửa chưa gắn hộ: không có mục mở phương án
        self.assertFalse(any(a.text().startswith('Mở phương án') for a in m2.actions()))
        m2.deleteLater()

    def test_khong_tao_cua_so_la(self):
        from PySide6.QtWidgets import QApplication, QDialog
        truoc = {id(w) for w in QApplication.topLevelWidgets()}
        h = self._hop()
        h.cb_mau.setCurrentIndex(2)
        h.cb_mau.setCurrentIndex(0)
        moi = [w for w in QApplication.topLevelWidgets() if id(w) not in truoc and w.isVisible() and not isinstance(w, QDialog)]
        self.assertEqual(moi, [])


if __name__ == '__main__':
    unittest.main()
