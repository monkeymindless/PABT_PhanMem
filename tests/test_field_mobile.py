"""1.0.32 Đợt 3 (người dùng 26/10/2026): ứng dụng di động LARC Field Mobile (phiếu kiểm đếm .html 7 thẻ) - dữ liệu nhúng (hộ, danh mục
có mã, loài cây, bản đồ thửa WGS84, tham số VN-2000) và nhập file .json phiên bản 2 về máy tính: dòng ghi lại biên bản (mục 0, tự phân
loại), ảnh gửi kèm (lưu cạnh file dự án, chặn chương trình giả ảnh), GPS (ghi chú hộ). Họ tên, CCCD, bản đồ, ảnh đều GIẢ LẬP."""
from __future__ import annotations
import base64
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import ban_do_cad, ban_do_kml, csdl, toa_do
from pabt import phieu_kiem_dem as pk
from tests.test_ban_do_kml import _kml
from tests.test_toc_do import _du_an

PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
MZ = b'MZ\x90\x00\x03\x00\x00\x00'


def _anh(du: bytes, kieu='image/png') -> str:
    return f'data:{kieu};base64,' + base64.b64encode(du).decode('ascii')


class _CoDuAn(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.goc = Path(self.td.name)
        self.p = _du_an(self.goc, 4)
        self.con = csdl.mo(self.p)
        p = mock.patch.object(toa_do, 'FILE_DATUM_BENTLEY', ())     # máy có Bentley hay không: tham số gắn sẵn
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.con.close()
        self.doCleanups()
        self.td.cleanup()

    def phieu(self, ten, du) -> Path:
        f = self.goc / ten
        f.write_text(json.dumps(du, ensure_ascii=False), encoding='utf-8')
        return f


class TestXuatPhieu(_CoDuAn):
    def _du_nhung(self, s: str) -> dict:
        m = re.search(r'const DU = window\.LARC_DU_LIEU \|\| (.*?);\nconst PHIEN_BAN_PHIEU', s, re.S)
        return json.loads(m.group(1))

    def test_html_7_the_va_du_lieu(self):
        kml = self.goc / 'bd.kml'
        kml.write_text(_kml(), encoding='utf-8')
        ban_do_cad.luu(self.con, ban_do_kml.phan_tich_kml(kml, kinh_tuyen=107.75))
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Tên </script><b>' WHERE ma_ho = 1")
        f = pk.xuat_phieu_kiem_dem_html(self.con, self.goc / 'phieu.html')
        s = f.read_text(encoding='utf-8')
        self.assertNotIn('@@', s)                                       # mọi chỗ trống của mẫu đã điền
        self.assertEqual(s.count('</script>'), 2)
        self.assertIn('LARC Field Mobile', s)
        for the in ('0. Hồ sơ & Đất', '1. Nhà ở (QĐ 42)', '2. Vật KT', '3. Cây trồng', '4. Ảnh biên bản', '5. Bản đồ KML/GPS',
                    '6. Xuất .JSON'):
            self.assertIn(the, s)
        self.assertNotIn('arguments.callee', s)                         # "use strict": arguments.callee là lỗi
        du = self._du_nhung(s)
        self.assertEqual(du, json.loads(json.dumps(pk.du_lieu_phieu(self.con))))
        self.assertEqual(len(du['ho']), 4)
        self.assertTrue(du['nha'] and du['dm2'] and du['vat_nuoi'] and du['cay'])
        self.assertTrue(all(m[0] for m in du['nha'] + du['dm2'] + du['vat_nuoi']))      # mọi mục có mã đơn giá
        self.assertTrue(all(m[1].lower().startswith(('nhà', 'biệt thự', 'gác lửng')) for m in du['nha']))
        self.assertEqual(len(du['cay']), len({x.lower() for x in du['cay']}))
        self.assertEqual((len(du['datum']), du['quy_uoc'], du['kinh_tuyen']), (7, 'coordinate_frame', 107.75))
        # bản đồ: thửa 103 tờ 11 (hộ 2) đổi lại WGS84 trùng tọa độ KML gốc (sai < 0,01 m)
        t = next(x for x in du['ban_do'] if x['so_thua'] == '103')
        self.assertEqual((t['ma_ho'], t['trang_thai']), (2, 'chua'))
        vd, kd = toa_do.vn2000_sang_wgs84(420000.0, 1220000.0, 107.75)
        self.assertLess(toa_do.khoang_cach_m(vd, kd, *t['vong'][0]), 0.02)
        self.assertEqual(set(du['mau_trang_thai']), set(ban_do_cad.TRANG_THAI))
        m = re.search(r'<img alt="LARC" src="data:image/png;base64,([^"]+)"', s)
        self.assertTrue(m)
        self.assertEqual(base64.b64decode(m.group(1))[:8], PNG[:8])


class TestNhapPhieuV2(_CoDuAn):
    def test_dong_bien_ban_anh_gps(self):
        g = dict(lat=10.95, lon=107.1, acc=4.6, luc='2026-10-26T09:00:00')
        du = dict(phien_ban=2, du_an='Thử', luc='2026-10-26T09:30:00', kinh_tuyen=107.75, ket_qua={'1': [
            dict(muc=0, ten='Tràm trồng năm 2023 ĐK gốc 10-15cm: 2700 cây', so_luong=''),
            dict(muc=0, ten='Mái che kt: (11m x 3,8m) + (1,3 x 18m)', so_luong=''),
            dict(muc=0, ten='Hỗ trợ ổn định đời sống: 4 khẩu', so_luong='')]},
            ho_dan={'1': dict(ma_ho=1, ho_ten='Hộ thử 0', gps=g)},
            anh={'1': [dict(ten='Biên bản trang 1.jpg', du_lieu=_anh(PNG + b'1')),
                       dict(ten='cai_dat.jpg', du_lieu=_anh(MZ + b'\x00' * 20, 'image/jpeg')),
                       dict(ten='hong', du_lieu='data:image/png;base64,@@@')]})
        f = self.phieu('ket_qua.json', du)
        kq = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual((kq['so_ho'], kq['so_dong'], kq['so_anh'], kq['so_gps']), (1, 2, 1, 1))
        self.assertTrue(any('chính sách hỗ trợ' in x for x in kq['loi']))
        self.assertTrue(any('chương trình' in x for x in kq['loi']))          # MZ đội lốt ảnh: không ghi
        self.assertTrue(any('"hong"' in x for x in kq['loi']))
        dong = {r['muc']: r for r in self.con.execute('SELECT muc, ten, so_luong FROM ct_khoan WHERE ma_ho = 1')}
        self.assertEqual(set(dong), {2, 3})                                    # tràm -> mục 3, mái che -> mục 2
        self.assertEqual(dong[2]['so_luong'], '65.2')                         # 11 x 3,8 + 1,3 x 18
        anh = pk.anh_cua_ho(self.con, 1)
        self.assertEqual([(a['ten_file'], a['khop_theo']) for a in anh], [('bien_ban_trang_1.png', 'kiem_dem')])
        self.assertEqual(Path(anh[0]['duong_dan']).parent, self.goc / pk.THU_MUC_ANH / '1')
        gc = self.con.execute('SELECT ghi_chu FROM ho WHERE ma_ho = 1').fetchone()[0]
        self.assertIn(pk.TIEN_TO_GPS + ' 10.9500000, 107.1000000 (±5 m), VN-2000 X 1.211.004,08 Y 428.761,84', gc)
        # nhập lại cùng file: không thêm ảnh, không lặp tọa độ
        k2 = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual((k2['so_anh'], k2['so_gps']), (0, 0))
        self.assertEqual(len(list((self.goc / pk.THU_MUC_ANH / '1').iterdir())), 1)
        self.assertEqual(self.con.execute('SELECT ghi_chu FROM ho WHERE ma_ho = 1').fetchone()[0].count(pk.TIEN_TO_GPS), 1)

    def test_chi_anh_va_ho_moi_co_gps(self):
        du = dict(phien_ban=2, du_an='Thử', luc='2026-10-26T09:30:00', ket_qua={'2': [], 'moi_1': [dict(muc=2, ten='Nhà tạm: 12m2')]},
                  ho_dan={'2': dict(ma_ho=2), 'moi_1': dict(ho_ten='Lê Văn Giả', nam_sinh='1970', gps=dict(lat=10.95, lon=107.1, acc=3))},
                  anh={'2': [dict(ten='nha.png', du_lieu=_anh(PNG + b'2'))]})
        f = self.phieu('ca_du_an.json', du)
        kq = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual((kq['so_dong'], kq['so_anh']), (0, 1))                 # hộ 2 chỉ có ảnh: vẫn nhận
        self.assertEqual([x['khoa'] for x in kq['chua_khop']], ['moi_1'])
        k2 = pk.nhap_ket_qua_kiem_dem(self.con, f, tao_ho_moi=True, chi={'moi_1'})
        ma = k2['khop'][0][1]
        gc = self.con.execute('SELECT ghi_chu FROM ho WHERE ma_ho = ?', (ma,)).fetchone()[0]
        self.assertIn('Năm sinh: 1970', gc)
        self.assertIn(pk.TIEN_TO_GPS, gc)

    def test_gps_sai_bo_qua(self):
        for g in (None, 'x', dict(lat='abc', lon=1), dict(lat=95, lon=107), dict(lat=float('nan'), lon=107)):
            self.assertIsNone(pk._gps(g), g)
        self.assertEqual(pk._gps(dict(lat='10.5', lon=106, acc=-3))['acc'], 0.0)

    def test_ho_khong_nhan_viec(self):
        """Bản offline theo hộ: ảnh / GPS của hộ không nhận -> báo, không ghi."""
        self.con._ho_nhan_viec = frozenset({2})
        f = self.phieu('k.json', dict(phien_ban=2, ket_qua={'1': []}, ho_dan={'1': dict(ma_ho=1, gps=dict(lat=10.9, lon=107))}))
        kq = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual(kq['so_gps'], 0)
        self.assertTrue(any('nhận việc' in x for x in kq['loi']))


if __name__ == '__main__':
    unittest.main()
