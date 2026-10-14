"""0.9.65 nguồn bảng giá đất 34 tỉnh (pabt/nguon_gia_dat.py): tên tỉnh sau sắp xếp, danh bạ đường dẫn văn bản, giá tham khảo
guland.vn. Không truy cập mạng: trang web GIẢ LẬP (cấu trúc bảng như guland.vn đo 12/10/2026, số liệu không phải giá thật)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TRANG_TINH = '<a href="/bang-gia-dat/tp-ho-chi-minh/phuong-sai-gon">Sài Gòn</a>'
HANG = ('<tr><td>TP. Hồ Chí Minh Phường Thử</td><td>ĐƯỜNG A TRỌN ĐƯỜNG</td><td>{loai}</td>'
        '<td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>')


def _trang_xa(*dong):
    tr = ''.join(HANG.format(loai=l, a=a, b=b, c=c, d=d) for l, a, b, c, d in dong)
    return ('<table><tr><th>Tỉnh</th><th>Đường</th><th>Loại</th><th>Vị trí 1</th><th>Vị trí 2</th><th>Vị trí 3</th>'
            '<th>Vị trí 4</th></tr>' + tr + '</table>')


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = self.tmp.name

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestTinh(unittest.TestCase):
    def test_34_tinh_va_ten_cu(self):
        from pabt import nguon_gia_dat as ng
        self.assertEqual(len(ng.TINH), 34)
        self.assertEqual(len({t for t, _ in ng.TINH}), 34)
        for go, mong in (('Bình Phước', 'Đồng Nai'), ('binh duong', 'Hồ Chí Minh'), ('TP.HCM', 'Hồ Chí Minh'),
                         ('Tỉnh Bà Rịa - Vũng Tàu', 'Hồ Chí Minh'), ('Thừa Thiên Huế', 'Huế'), ('Kiên Giang', 'An Giang'),
                         ('Đồng Nai', 'Đồng Nai'), ('thành phố Hải Phòng', 'Hải Phòng'), ('Hải Dương', 'Hải Phòng')):
            self.assertEqual(ng.chuan_tinh(go), mong, go)
        self.assertEqual(ng.chuan_tinh('Không có'), '')
        self.assertIn('Bình Phước', ng.tinh_cu('Đồng Nai'))
        self.assertTrue(set(ng.GULAND) <= {t for t, _ in ng.TINH})


class TestDanhBa(CoSo):
    def test_gan_san_va_ghi_nho(self):
        from pabt import nguon_gia_dat as ng
        vb, ds = ng.url_danh_ba('Bình Phước')                    # tỉnh cũ -> Đồng Nai: có nghị quyết gắn sẵn
        self.assertIn('28/2025', vb)
        self.assertTrue(ds and ds[0].startswith('https://congbao.dongnai.gov.vn/'))
        self.assertEqual(ng.url_danh_ba('Lạng Sơn'), ('', []))
        ng.ghi_danh_ba('Lạng Sơn', 'https://vi.du/phu-luc.docx', 'NQ thử')
        ng.ghi_danh_ba('Lạng Sơn', 'http://khong-an-toan/x.docx')   # chỉ https
        ng.ghi_danh_ba('Lạng Sơn', 'https://vi.du/trang-van-ban')
        vb, ds = ng.url_danh_ba('lang son')
        self.assertEqual(ds, ['https://vi.du/trang-van-ban', 'https://vi.du/phu-luc.docx'])
        self.assertEqual(vb, 'NQ thử')
        du = json.loads(ng.file_danh_ba().read_text(encoding='utf-8'))
        self.assertIn('Lạng Sơn', du)
        ng.file_danh_ba().write_text('{hỏng', encoding='utf-8')     # file hỏng: vẫn còn danh bạ gắn sẵn
        self.assertIn('Đồng Nai', ng.doc_danh_ba())


class TestGuland(CoSo):
    def test_phan_tich_va_gop_loai_dat(self):
        from pabt import nguon_gia_dat as ng, gia_dat_nq28 as nq
        trang = {
            ng.GULAND_GOC + 'tp-ho-chi-minh': TRANG_TINH,
            ng.GULAND_GOC + 'tp-ho-chi-minh/phuong-thu': _trang_xa(
                ('Đất ở Nhóm đất phi nông nghiệp', '51.800.000', '25.900.000', '20.720.000', '16.576.000'),
                ('Đất thương mại, dịch vụ', '31.100.000', '15.550.000', '0', '0'),
                ('Đất sản xuất, kinh doanh phi nông nghiệp', '25.900.000', '12.950.000', '10.360.000', '8.288.000')),
            ng.GULAND_GOC + 'tp-ho-chi-minh/phuong-thu?page=2': _trang_xa(
                ('Đất ở Nhóm đất phi nông nghiệp', '51.800.000', '25.900.000', '20.720.000', '16.576.000')),  # trùng: dừng
        }
        lay = mock.Mock(side_effect=lambda u: trang[u] if u in trang else (_ for _ in ()).throw(OSError('404')))
        d = ng.doc_guland('Bình Dương', 'Phường Thử', lay=lay, nghi=0)
        self.assertEqual([r['vi_tri'] for r in d], ['VT1', 'VT2', 'VT3', 'VT4'])
        self.assertEqual((d[0]['dat_o'], d[0]['tmdv'], d[0]['sxkd']), (51800, 31100, 25900))
        self.assertEqual((d[3]['dat_o'], d[3]['tmdv'], d[3]['sxkd']), (16576, 0, 8288))
        self.assertEqual(nq.gia_dong(d[0], 'dat_o'), 51_800_000)
        self.assertEqual(d[0]['xa'], 'Phường Thử')
        self.assertTrue(all(r['tham_khao'] for r in d))
        self.assertEqual(d[0]['ten_duong'], 'Đường A Trọn Đường')
        self.assertNotIn(ng.GULAND_GOC + 'tp-ho-chi-minh/phuong-thu?page=3', [c.args[0] for c in lay.call_args_list])

    def test_tinh_khong_co_tren_guland(self):
        from pabt import nguon_gia_dat as ng
        lay = mock.Mock()
        self.assertEqual(ng.doc_guland('Lạng Sơn', 'Xã Thử', lay=lay, nghi=0), [])
        lay.assert_not_called()


class TestTimTrenWeb(CoSo):
    def _khong_mang(self):
        from pabt import cap_nhat_web
        from pabt.lap_pa import LoiNhap
        return mock.patch.object(cap_nhat_web, '_lay', side_effect=LoiNhap('không có mạng (test)'))

    def test_tham_khao_khi_nguon_chinh_thuc_khong_ra(self):
        from pabt import nguon_gia_dat as ng
        from pabt.cap_nhat_gia_dat import tim_tren_web
        gia = [dict(xa='Phường Thử', tt=1, ten_duong='Đường A', diem_dau='', diem_cuoi='', vi_tri='VT1', dieu_kien='',
                    nguong=[1000, 500], trang={}, tham_khao=True, nguon_url='https://guland.vn/x', dat_o=100, tmdv=0, sxkd=0,
                    nn_cay=0, nn_rung_nts=0)]
        with self._khong_mang(), mock.patch.object(ng, 'doc_guland', return_value=gia) as g:
            dong, vb, chu, nguon = tim_tren_web('Bình Dương', 'Phường Thử')
        g.assert_called_once_with('Hồ Chí Minh', 'Thử')
        self.assertEqual(vb, ng.NHAN_THAM_KHAO)
        self.assertIn('tham khảo', chu.lower())
        self.assertEqual(nguon, 'https://guland.vn/x')

    def test_tat_tham_khao_va_url_khong_an_toan(self):
        from pabt import nguon_gia_dat as ng
        from pabt.cap_nhat_gia_dat import LoiWeb, tim_tren_web
        with self._khong_mang(), mock.patch.object(ng, 'doc_guland') as g:
            with self.assertRaises(LoiWeb):
                tim_tren_web('Hồ Chí Minh', 'Phường Thử', tham_khao=False)
            g.assert_not_called()
            with self.assertRaises(LoiWeb):
                tim_tren_web('Hồ Chí Minh', 'Phường Thử', url='http://khong-ma-hoa/x.docx')

    def test_url_dan_doc_duoc_thi_nho_vao_danh_ba(self):
        from pabt import cap_nhat_gia_dat as cg, nguon_gia_dat as ng
        dong = [dict(xa='Xã Thử', ten_duong='Đường A', vi_tri='MT', dat_o=1000)]
        url = 'https://cong-bao.vi.du/phu-luc-bang-gia.docx'
        with mock.patch.object(cg, '_tim_va_boc', return_value=(dong, 'NQ 99/2025/NQ-HĐND (giả lập)', 'x', url)) as t:
            kq = cg.tim_tren_web('Lạng Sơn', 'Xã Thử', url=url)
        self.assertEqual(kq[0], dong)
        self.assertEqual(t.call_args.args[1:3], ('Lạng Sơn', 'Thử'))
        self.assertEqual(ng.url_danh_ba('Lạng Sơn'), ('NQ 99/2025/NQ-HĐND (giả lập)', [url]))

    def test_danh_ba_bo_qua_tim_kiem_va_tai_thang_file(self):
        """Tỉnh có file phụ lục trong danh bạ: không gọi trang tìm kiếm, tải thẳng file (cả file nhỏ < 80 KB)."""
        from pabt import cap_nhat_gia_dat as cg, cap_nhat_web, nguon_gia_dat as ng
        url = 'https://cong-bao.vi.du/bang-gia.csv'
        ng.ghi_danh_ba('Lạng Sơn', url, 'NQ giả lập')
        d = Path(self.tmp.name) / 'tai'
        d.mkdir()
        f = d / 'bang-gia.csv'
        f.write_text('Xã Thử\nSTT,Tên đường,Đất ở\n1,Đường A,1.500\n', encoding='utf-8')
        doc = [dict(xa='Xã Thử', tt=1, ten_duong='Đường A', diem_dau='', diem_cuoi='', vi_tri='MT', dieu_kien='',
                    nguong=[1000, 500], trang={}, dat_o=1500, tmdv=0, sxkd=0, nn_cay=0, nn_rung_nts=0)]
        with mock.patch.object(cap_nhat_web, '_lay') as lay, \
                mock.patch.object(cap_nhat_web, 'tai_ve', return_value={'file': str(f)}) as tai, \
                mock.patch.object(cg, 'doc_file', return_value=(doc, '', '')):
            dong, vb, _chu, nguon = cg.tim_tren_web('Lạng Sơn', 'Xã Thử', thu_muc=d)
        lay.assert_not_called()
        tai.assert_called_once()
        self.assertEqual(vb, 'NQ giả lập')
        self.assertEqual(nguon, url)
        self.assertEqual(dong[0]['dat_o'], 1500)


class TestTlsGocWindows(unittest.TestCase):
    def test_nhan_loi_chung_chi_va_chan_chen_lenh(self):
        import ssl
        import urllib.error
        from pabt import an_toan
        self.assertTrue(an_toan.la_loi_chung_chi(urllib.error.URLError(ssl.SSLCertVerificationError('x'))))
        self.assertTrue(an_toan.la_loi_chung_chi(urllib.error.URLError('[SSL: CERTIFICATE_VERIFY_FAILED] ...')))
        self.assertFalse(an_toan.la_loi_chung_chi(urllib.error.URLError('timed out')))
        with mock.patch('subprocess.run') as chay:
            self.assertFalse(an_toan.nap_goc_ca_windows("https://a.vn';calc;'/"))   # tên máy chủ lạ: không chạy lệnh
            chay.assert_not_called()

    def test_thu_lai_mot_lan_sau_khi_nap_goc(self):
        import ssl
        import urllib.error
        from pabt import an_toan, cap_nhat_web
        loi = urllib.error.URLError(ssl.SSLCertVerificationError('CERTIFICATE_VERIFY_FAILED'))
        with mock.patch('urllib.request.urlopen', side_effect=[loi, 'ok']) as mo, \
                mock.patch.object(an_toan, 'nap_goc_ca_windows', return_value=True) as nap:
            self.assertEqual(cap_nhat_web._mo('https://vbpl.vn/'), 'ok')
        self.assertEqual(mo.call_count, 2)
        nap.assert_called_once()
        with mock.patch('urllib.request.urlopen', side_effect=[loi]), \
                mock.patch.object(an_toan, 'nap_goc_ca_windows', return_value=False):
            with self.assertRaises(urllib.error.URLError):              # Windows cũng không tin: vẫn báo lỗi, KHÔNG bỏ kiểm tra
                cap_nhat_web._mo('https://gia.vi.du/')


if __name__ == '__main__':
    unittest.main()
