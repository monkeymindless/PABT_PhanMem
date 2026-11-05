"""Tự dựng thửa từ bản vẽ đường CAD (05/11/2026): ghép lưới -> vùng, chọn lớp theo diện tích, ranh thu hồi qua mốc, số tờ, đối chiếu với nhãn. Đo đạc, định vị (do_dac), ô ảnh giữ chỗ.

Số liệu GIẢ LẬP theo cấu trúc file MicroStation / gCadas (không chép bản vẽ thật): lưới 3 x 2 thửa 100 x 100 m, hành lang thu hồi y từ 40 tới 160."""
from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from pabt import ban_do_cad, ban_do_ghep, ban_do_kml, csdl, do_dac, nen_ban_do, toa_do

KT = 107.75
GOC = (410000.0, 1219000.0)


def td(x, y) -> str:
    vd, kd = toa_do.vn2000_sang_wgs84(GOC[0] + x, GOC[1] + y, KT)
    return f'{kd:.10f},{vd:.10f},0'


def duong(lop, *diem, ban='ve1', ten='Polyline_001') -> str:
    return (f'<Placemark><name>{ten}</name><description>{ban}|{lop}</description><LineString><coordinates>'
            + ' '.join(td(*p) for p in diem) + '</coordinates></LineString></Placemark>')


def nhan(chu, x, y, lop='Level 3', ban='ve1') -> str:
    return f'<Placemark><name>{chu}</name><description>{ban}|{lop}</description><Point><coordinates>{td(x, y)}</coordinates></Point></Placemark>'


def vong_moc(x, y, ten) -> str:
    q = ' '.join(td(x + 0.6 * math.cos(i * math.pi / 24), y + 0.6 * math.sin(i * math.pi / 24)) for i in range(49))
    return (f'<Placemark><name>Polygon_001</name><description>Level 11</description><Polygon><outerBoundaryIs><LinearRing><coordinates>{q}</coordinates>'
            f'</LinearRing></outerBoundaryIs></Polygon></Placemark>' + nhan(ten, x + 3, y + 3, 'Level 45'))


def kml(than: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>{than}</Document></kml>'


def luoi() -> str:
    """Lưới thửa Level 10: đoạn rời, mỗi cạnh một đoạn (nút chữ T ở giữa cạnh dài)."""
    pm = []
    for y in (0, 100, 200):
        pm.append(duong('Level 10', (0, y), (300, y)))
    for x in (0, 100, 200, 300):
        pm.append(duong('Level 10', (x, 0), (x, 200)))
    pm.append(duong('Level 10', (300, 50), (340, 50)))         # nhánh cụt: không tạo vùng
    return ''.join(pm)


def ranh() -> str:
    """Hai đường ray của hành lang (đi qua vòng mốc), không đóng đầu: ranh dừng ở mép bản vẽ."""
    pm = [duong('Level 24', (-50, 40), (350, 40)), duong('Level 24', (-50, 160), (350, 160))]
    for i, x in enumerate((0, 150, 300)):
        pm.append(vong_moc(x, 40, f'DN.T{700 + i}'))
        pm.append(vong_moc(x, 160, f'DN.P{700 + i}'))
    return ''.join(pm)


def nhan_thua(so, cx, cy, ld='LUK', dt='10000.0') -> str:
    return nhan(so, cx, cy + 10, 'Level 3') + nhan(ld, cx - 15, cy + 10, 'Level 5') + (nhan(dt, cx, cy + 2, 'Level 4') if dt else '')


def ban_ve_mau() -> str:
    pm = [luoi(), ranh()]
    for so, cx, cy in (('1', 50, 25), ('2', 150, 25), ('3', 250, 25), ('4', 50, 175), ('5', 150, 175), ('6', 250, 175)):
        pm.append(nhan_thua(so, cx, cy))
    # hàng dưới: phần trong ranh (y 40-100) 6000 m², ngoài ranh 4000 m²
    pm += [nhan('(6000.0)', 50, 70, 'Level 34'), nhan('(4000.0)', 50, 15, 'Level 51')]         # thửa 1: khớp cộng nhãn
    pm += [nhan('(4000.0)', 150, 15, 'Level 51')]                                               # thửa 2: chỉ nhãn phần ngoài ranh -> DT thửa trừ đi
    pm += [nhan('(5000.0)', 250, 70, 'Level 34'), nhan('(5000.0)', 250, 15, 'Level 51')]        # thửa 3: nhãn sai -> lệch, báo
    pm += [nhan('(6000.0)', 150, 203, 'Level 34')]                                              # thửa 5: nhãn phần đặt lệch ra ngoài thửa
    pm += [nhan('Tờ số 5', 195, 90), nhan('Tờ số 6', 205, 90), nhan('Tờ số 5', 195, 110), nhan('Tờ số 6', 205, 110)]
    pm.append(duong('Level 15', (200, -10), (200, 210)))                                        # ranh tờ
    pm.append(nhan('Đường đất', 60, 60, 'Level 28'))
    return kml(''.join(pm))


class TestGhepVung(unittest.TestCase):
    def test_chu_T_nhanh_cut_va_lo(self):
        ds = [((0, 0), (100, 0)), ((100, 0), (100, 100)), ((100, 100), (0, 100)), ((0, 100), (0, 0)),   # vuông 100 x 100
              ((50, 0), (50, 100)),                                                                     # đoạn chia đôi đặt chữ T lên hai cạnh
              ((100, 50), (130, 50)),                                                                   # nhánh cụt
              ((10, 10), (20, 10)), ((20, 10), (20, 20)), ((20, 20), (10, 20)), ((10, 20), (10, 10))]   # cụm nằm trong, không nối lưới
        vung = sorted(ban_do_ghep.ghep_vung(ds), key=lambda f: f.dt)
        self.assertEqual([round(f.dt, 3) for f in vung], [100.0, 4900.0, 5000.0])      # trừ lỗ 100 m²
        self.assertEqual(len(vung[1].lo), 1)

    def test_doan_gan_trung_va_ho_nho(self):
        """Đầu đoạn hở 1 cm tới cạnh: vẫn nối (chữ T hở); đoạn trùng một phần: tách tại đầu mút."""
        ds = [((0, 0), (100, 0)), ((100, 0), (100, 100)), ((100, 100), (0, 100)), ((0, 100), (0, 0)),
              ((50, 0.01), (50, 99.99)), ((0, 0), (40, 0))]
        vung = sorted(ban_do_ghep.ghep_vung(ds), key=lambda f: f.dt)
        self.assertEqual(len(vung), 2)
        self.assertAlmostEqual(vung[0].dt, 5000, delta=2)
        self.assertAlmostEqual(vung[1].dt, 5000, delta=2)

    def test_khong_khep(self):
        self.assertEqual(ban_do_ghep.ghep_vung([((0, 0), (100, 0)), ((100, 0), (100, 100))]), [])

    def test_loai_nhan_ghep(self):
        self.assertEqual(ban_do_ghep.loai_nhan_ghep('1230A'), 'thua')
        self.assertEqual(ban_do_ghep.loai_nhan_ghep('231a'), 'thua')
        self.assertEqual(ban_do_ghep.loai_nhan_ghep('ONT+CLN +LUK'), 'ld')
        self.assertEqual(ban_do_ghep.loai_nhan_ghep('Đường đất'), 'ghi_chu')
        self.assertEqual(ban_do_ghep.so_thua_chuan('0231a /'), '231A')
        self.assertEqual(ban_do_ghep.so_nhan('(1.331,3)'), 1331.3)
        self.assertEqual(ban_do_ghep.so_nhan('1331.3'), 1331.3)
        self.assertIsNone(ban_do_ghep.so_nhan('abc'))


class _CoFile(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.f = Path(self.td.name) / 'ban_ve.kml'
        self.f.write_text(ban_ve_mau(), encoding='utf-8')

    def _phan_tich(self, than=None):
        if than is not None:
            self.f.write_text(kml(than), encoding='utf-8')
        return ban_do_kml.phan_tich_kml(self.f, kinh_tuyen=KT)


class TestGhepThua(_CoFile):
    def test_lop_luoi_khong_nham_ranh(self):
        """Đường ranh cắt thửa làm vùng khớp nhãn "(xxx)": chỉ nhãn DT nguyên thửa mới được chọn lưới."""
        bv = ban_do_ghep.doc_ban_ve(ban_do_kml.doc_kml(self.f), KT)
        lop, vung = ban_do_ghep.chon_lop_luoi(bv)
        self.assertEqual(lop, {('ve1', 'Level 10')})
        self.assertEqual(len(vung), 6)
        self.assertEqual(len(bv.vong_moc), 6)

    def test_thua_va_dien_tich(self):
        kq = self._phan_tich()
        self.assertEqual(sorted(t.so_thua for t in kq.thua), list('123456'))
        for t in kq.thua:
            self.assertAlmostEqual(float(t.dt_hinh), 10000, delta=0.5)
            self.assertEqual(float(t.dt_ban_ve), 10000)
            self.assertEqual(t.chi_tiet['doi_chieu']['dt'], 'khop')
            self.assertEqual(t.loai_dat, 'LUK')

    def test_dt_thu_hoi_doi_chieu_nhan(self):
        kq = self._phan_tich()
        self.assertEqual(kq.lop_ranh, 'đường qua mốc ranh')
        self.assertEqual(len(kq.ranh_dong), 2)                                       # hai đầu tuyến tự đóng
        t = {x.so_thua: x for x in kq.thua}
        self.assertEqual(float(t['1'].dt_trong_ranh), 6000)                          # cộng nhãn trong thửa
        self.assertEqual(t['1'].chi_tiet['doi_chieu']['thu_hoi'], 'khop')
        self.assertEqual(t['1'].chi_tiet['ly_do'], [])
        self.assertEqual(float(t['2'].dt_trong_ranh), 6000)                          # DT thửa trừ phần ngoài ranh
        self.assertEqual(t['2'].chi_tiet['doi_chieu']['thu_hoi'], 'khop')
        self.assertEqual(float(t['5'].dt_trong_ranh), 6000)                          # nhãn đặt lệch ra ngoài thửa
        self.assertEqual(t['5'].chi_tiet['doi_chieu']['thu_hoi'], 'khop')
        self.assertEqual(t['3'].chi_tiet['doi_chieu']['thu_hoi'], 'lech')            # nhãn sai: không tin, báo
        self.assertAlmostEqual(float(t['3'].dt_trong_ranh), 6000, delta=1)           # lấy hình học
        self.assertTrue(any('không khớp' in x for x in t['3'].chi_tiet['ly_do']))
        self.assertEqual(t['4'].chi_tiet['doi_chieu']['thu_hoi'], 'chi_hinh')        # không có nhãn nào: chỉ hình học, báo
        self.assertTrue(t['4'].chi_tiet['ly_do'])
        self.assertTrue(any('cần xem lại' in c for c in kq.canh_bao))

    def test_nhan_phan_ngoai_ranh_khong_phai_dt_thu_hoi(self):
        """Nhãn "(xxx)" gần số thửa nhất có thể là phần NGOÀI ranh (sự cố trên file thật: 2.407 m² ngoài ranh hiện thành thu hồi)."""
        t = next(x for x in self._phan_tich().thua if x.so_thua == '2')
        self.assertNotEqual(float(t.dt_trong_ranh), 4000)

    def test_so_to_theo_ranh_to(self):
        t = {x.so_thua: x for x in self._phan_tich().thua}
        self.assertEqual({t[k].so_to for k in ('1', '2', '4', '5')}, {'5'})
        self.assertEqual({t[k].so_to for k in ('3', '6')}, {'6'})                    # cùng khoảng cách tới nhãn: ranh tờ quyết định

    def test_so_to_nhap_tay_thang(self):
        kq = ban_do_kml.phan_tich_kml(self.f, '77', KT)
        self.assertEqual({t.so_to for t in kq.thua}, {'77'})

    def test_moc_va_ghi_chu_cua_thua(self):
        t = {x.so_thua: x for x in self._phan_tich().thua}
        self.assertIn('DN.T700', t['1'].chi_tiet['moc'])
        self.assertIn('DN.P702', t['6'].chi_tiet['moc'])
        self.assertEqual(t['1'].chi_tiet['ghi_chu'], ['Đường đất'])

    def test_nhan_lech_sang_thua_ben_va_chua_tach(self):
        """Thửa hẹp (mương): nhãn đặt trong thửa bên, số nào có DT khớp vùng là chủ, số kia về vùng không số có DT khớp. Không có bằng chứng DT: không đoán."""
        pm = [duong('Level 10', (0, 0), (100, 0), (100, 100), (0, 100), (0, 0)),
              duong('Level 10', (100, 0), (102, 0), (102, 60), (100, 60)),           # mương 2 x 60 = 120 m², không số
              nhan('10', 50, 60), nhan('10000.0', 50, 52, 'Level 4'),
              nhan('11', 85, 30), nhan('DTL', 75, 30, 'Level 5'), nhan('120.0', 85, 22, 'Level 4'),
              duong('Level 10', (200, 0), (300, 0), (300, 100), (200, 100), (200, 0)),
              nhan('20', 230, 50), nhan('21', 270, 50)]
        kq = self._phan_tich(''.join(pm))
        t = {x.so_thua: x for x in kq.thua}
        self.assertAlmostEqual(float(t['10'].dt_hinh), 10000, delta=1)
        self.assertEqual(t['10'].chi_tiet['doi_chieu']['dt'], 'khop')
        self.assertAlmostEqual(float(t['11'].dt_hinh), 120, delta=0.5)
        self.assertEqual(t['11'].loai_dat, 'DTL')
        self.assertNotIn('20', t)
        self.assertEqual([x['so_thua'] for x in kq.chua_tach], [['20', '21']])
        self.assertTrue(any('nhiều số thửa' in c for c in kq.canh_bao))

    def test_da_giac_van_uu_tien(self):
        """File có đa giác thửa: đi đường cũ, không ghép đường."""
        q = ' '.join(td(*p) for p in ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)))
        kq = self._phan_tich(f'<Placemark><name>Thửa 5 tờ 3</name><Polygon><outerBoundaryIs><LinearRing><coordinates>{q}</coordinates></LinearRing>'
                             '</outerBoundaryIs></Polygon></Placemark>' + duong('Level 10', (0, 0), (50, 50)))
        self.assertEqual([(t.so_to, t.so_thua) for t in kq.thua], [('3', '5')])
        self.assertEqual(kq.thua[0].chi_tiet, {})

    def test_luu_doc_lai_giu_chi_tiet(self):
        from tests.test_toc_do import _du_an
        con = csdl.mo(_du_an(Path(self.td.name), 3))
        self.addCleanup(con.close)
        with con:
            con.execute("UPDATE thua SET so_to = '5', so_thua = '1', dt_thu_hoi = '100' WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua)")
        kq = self._phan_tich()
        self.assertEqual(ban_do_cad.luu(con, kq)['luu'], 6)
        ds = {t.so_thua: t for t in ban_do_cad.doc_ban_do(con)}
        self.assertEqual(ds['1'].chi_tiet['doi_chieu']['thu_hoi'], 'khop')
        self.assertIsNotNone(ds['1'].ma_ho)
        self.assertEqual(float(ds['1'].dt_ban_ve), 10000)
        self.assertEqual(ban_do_cad.muc_thu_hoi(ds['1']), 'mot_phan')
        self.assertFalse(ds['1'].tam)
        # sửa số thửa trên bản đồ: không đụng hồ sơ; trùng thửa khác thì báo
        self.assertEqual(ban_do_cad.sua_thua_ban_do(con, '5', '4', dict(so_to='9', so_thua='44', loai_dat='cln')), ('9', '44'))
        self.assertEqual(next(t.loai_dat for t in ban_do_cad.doc_ban_do(con, '9')), 'CLN')
        from pabt.lap_pa import LoiNhap
        with self.assertRaises(LoiNhap):
            ban_do_cad.sua_thua_ban_do(con, '5', '1', dict(so_to='5', so_thua='2'))

    def test_file_cu_them_cot_chi_tiet(self):
        from tests.test_toc_do import _du_an
        p = _du_an(Path(self.td.name), 2)
        con = csdl.mo(p)
        with con:
            con.execute('DROP TABLE thua_ban_do')
            con.execute(ban_do_cad.SQL_BANG.replace("chi_tiet TEXT NOT NULL DEFAULT '',", ''))
        self.assertIn('cot_ban_do', csdl.thieu_mo_rong(con))
        self.assertEqual(ban_do_cad.doc_ban_do(con), [])
        con.close()
        con = csdl.mo(p)                                                             # mở lại: tự thêm cột
        self.addCleanup(con.close)
        self.assertTrue(ban_do_cad.co_cot_chi_tiet(con))
        self.assertEqual(csdl.thieu_mo_rong(con), [])

    def test_gop_ket_qua(self):
        a = self._phan_tich()
        b = ban_do_kml.phan_tich_kml(self.f, kinh_tuyen=KT)
        g = ban_do_cad.gop_ket_qua([a, b])
        self.assertEqual(len(g.thua), len(a.thua))
        self.assertTrue(any('nhiều file' in c for c in g.canh_bao))
        self.assertIs(ban_do_cad.gop_ket_qua([a]), a)


class TestCoDinhDatum(unittest.TestCase):
    def test_mot_lan_doc_trong_lo_cung_ket_qua(self):
        from unittest import mock
        ngoai = toa_do.wgs84_sang_vn2000(11.02, 106.95, KT)
        goi = []
        goc = toa_do.os.stat if hasattr(toa_do, 'os') else None
        self.assertIsNone(goc)
        import os
        with mock.patch.object(os, 'stat', side_effect=lambda *a, **k: goi.append(1) or (_ for _ in ()).throw(OSError())):
            toa_do.wgs84_sang_vn2000(11.02, 106.95, KT)
            n_le = len(goi)
            self.assertGreater(n_le, 0)
            goi.clear()
            with toa_do.co_dinh_datum():
                n_dau = len(goi)
                with toa_do.co_dinh_datum():                                 # lồng được
                    for _ in range(50):
                        trong = toa_do.wgs84_sang_vn2000(11.02, 106.95, KT)
                self.assertEqual(len(goi), n_dau)                            # không stat thêm
        self.assertEqual(trong, ngoai)
        self.assertEqual(toa_do._CO_DINH, [0, None])                         # ra khỏi lô: đọc lại bình thường


class TestDoDac(unittest.TestCase):
    def test_chieu_dai_dien_tich(self):
        self.assertEqual(do_dac.do_dai([(0, 0), (3, 4), (3, 10)]), 11)
        self.assertEqual(do_dac.cac_doan([(0, 0), (3, 4)]), [5])
        self.assertEqual(do_dac.dien_tich([(0, 0), (100, 0), (100, 100), (0, 100)]), 10000)
        self.assertEqual(do_dac.chu_vi([(0, 0), (100, 0), (100, 100), (0, 100)]), 400)
        self.assertEqual(do_dac.chu_do_dai(1234.5), '1.234,50 m (1,235 km)')
        self.assertEqual(do_dac.chu_dien_tich(12345.6), '12.345,6 m² (1,2346 ha)')

    def test_ket_qua_chu(self):
        self.assertIn('tổng 11,00 m', do_dac.ket_qua_do('duong', [(0, 0), (3, 4), (3, 10)], KT))
        self.assertIn('5,00 + 6,00', do_dac.ket_qua_do('duong', [(0, 0), (3, 4), (3, 10)], KT))
        c = do_dac.ket_qua_do('vung', [(0, 0), (100, 0), (100, 100), (0, 100)], KT)
        self.assertIn('10.000,0 m² (1,0000 ha)', c)
        self.assertIn('chu vi 400,00 m', c)
        self.assertIn('CẢNH BÁO', do_dac.ket_qua_do('vung', [(0, 0), (100, 100), (100, 0), (0, 100)], KT))     # cạnh cắt nhau
        c = do_dac.ket_qua_do('diem', [(410596.125, 1219655.5)], KT)
        self.assertIn('X 1.219.655,500', c)
        self.assertIn('Y 410.596,125', c)
        self.assertIn('GPS 11.', c)
        self.assertIn('Đ', c)

    def test_doc_toa_do(self):
        d, b = do_dac.doc_toa_do('X 1219655 Y 410596', KT)
        self.assertEqual((d, b), (410596.0, 1219655.0))
        self.assertEqual(do_dac.doc_toa_do('y=410.596,5 x=1.219.655,25', KT), (410596.5, 1219655.25))
        self.assertEqual(do_dac.doc_toa_do('1219655 410596', KT), (410596.0, 1219655.0))    # số lớn hơn là Bắc
        vd, kd = toa_do.vn2000_sang_wgs84(410596.0, 1219655.0, KT)
        for chu in (f'{vd:.7f}, {kd:.7f}', f'{vd:.7f} {kd:.7f}', f'{vd:.7f},{kd:.7f}', f'{vd:.7f} ; {kd:.7f}', f'{vd:.7f}'.replace('.', ',') + ' ' + f'{kd:.7f}'.replace('.', ',')):
            d, b = do_dac.doc_toa_do(chu, KT)
            self.assertAlmostEqual(d, 410596.0, delta=0.1, msg=chu)
            self.assertAlmostEqual(b, 1219655.0, delta=0.1, msg=chu)
        for sai in ('', 'abc', '1 2 3'):
            with self.assertRaises(ValueError):
                do_dac.doc_toa_do(sai, KT)

    def test_vi_tri_may(self):
        self.assertEqual(do_dac.vi_tri_may(lambda lenh, han: '{"vd":11.02,"kd":106.95,"sai":35.5}'), dict(vd=11.02, kd=106.95, sai=35.5))
        self.assertIn('Quyền riêng tư', do_dac.vi_tri_may(lambda lenh, han: '{"loi":"khong_co","quyen":"Denied"}')['loi'])
        self.assertIn('Đến tọa độ', do_dac.vi_tri_may(lambda lenh, han: '{"loi":"khong_co","quyen":"Granted"}')['loi'])
        self.assertIn('không trả', do_dac.vi_tri_may(lambda lenh, han: 'rác')['loi'])

        def hong(lenh, han):
            raise OSError('không có')
        self.assertIn('Không gọi được', do_dac.vi_tri_may(hong)['loi'])


class TestOAnh(unittest.TestCase):
    def test_o_giu_cho(self):
        self.assertFalse(nen_ban_do.la_o_giu_cho(b'x' * nen_ban_do.CO_O_GIU_CHO))
        self.assertFalse(nen_ban_do.la_o_giu_cho(b'x' * 100))
        with tempfile.TemporaryDirectory() as t:
            from unittest import mock
            with mock.patch.object(nen_ban_do, 'thu_muc_dem', lambda: Path(t) / 'esri'), mock.patch.object(nen_ban_do, 'la_o_giu_cho', lambda du: du == b'giu cho'):
                self.assertEqual(nen_ban_do.tai_o(19, 1, 2, lambda url: b'giu cho'), nen_ban_do.KHONG_CO_ANH)
                self.assertIsNone(nen_ban_do.file_dem(19, 1, 2))                     # không lưu đệm ô giữ chỗ

    def test_nen_khong_lan_vao_ds_cua_mobile(self):
        self.assertNotIn(nen_ban_do.KHONG_NEN, nen_ban_do.NEN)
        self.assertEqual(nen_ban_do.TEN_KHONG_NEN, 'Không nền')
        self.assertLessEqual(nen_ban_do.Z_TOI_DA, nen_ban_do.NEN['ve_tinh'][2])


if __name__ == '__main__':
    unittest.main()
