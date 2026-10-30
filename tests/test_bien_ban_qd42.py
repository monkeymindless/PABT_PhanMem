"""1.0.32 Đợt 1 (người dùng 26/10/2026, đặc tả "LARC Mobile Pro" / biên bản kiểm đếm mẫu QĐ 42): kiểm tra chữ ký đầu tệp, bộ hiểu
biên bản viết tay (kích thước nhiều cụm / 3 chiều, dòng gộp nhiều cỡ ống, ống / giếng theo đường kính, năm trồng -> năm tuổi,
"35c/15cm", "ĐK 10-15cm"), nhập file .json của phiếu khớp hộ 4 tầng + tạo hộ mới. Họ tên, CCCD, lô rừng, số liệu đều GIẢ LẬP."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import an_toan, csdl, hieu_tai_san as h
from pabt.lap_pa import DanhMuc, LoiNhap
from pabt.phan_loai_tai_san import BoPhanLoai, doc_danh_sach
from tests.test_toc_do import _du_an

JPEG, PNG = b'\xff\xd8\xff\xe0\x00\x10JFIF', b'\x89PNG\r\n\x1a\n\x00'
MZ = b'MZ\x90\x00\x03\x00\x00\x00'


class TestDauTep(unittest.TestCase):
    def test_nhan_dang(self):
        for dau, loai in ((JPEG, 'jpeg'), (PNG, 'png'), (b'RIFF\x10\x00\x00\x00WEBPVP8 ', 'webp'), (b'%PDF-1.7', 'pdf'),
                          (b'PK\x03\x04\x14\x00', 'zip'), (b'\xef\xbb\xbf  {"a": 1}', 'json'), (b'\n[1, 2]', 'json'),
                          (b'<?xml version="1.0"?><kml>', 'xml'), (b'<kml xmlns="x">', 'xml'), (MZ, 'thuc_thi'),
                          (b'\x00\x00\x00\x18ftypheic', 'heic'), (b'xin chao', '')):
            self.assertEqual(an_toan.nhan_dang_dau_tep(dau), loai, dau)

    def test_chan_chuong_trinh_doi_duoi(self):
        with tempfile.TemporaryDirectory() as td:
            gia = Path(td) / 'anh_bien_ban.jpg'
            gia.write_bytes(MZ + b'\x00' * 100)
            with self.assertRaises(an_toan.LoiAnToan):
                an_toan.kiem_tra_magic_bytes(gia)
            with self.assertRaises(an_toan.LoiAnToan):
                an_toan.kiem_tra_magic_bytes(JPEG, ten='cai_dat.exe')          # đuôi chương trình
            with self.assertRaises(an_toan.LoiAnToan):
                an_toan.kiem_tra_magic_bytes(b'%PDF-1.4', {'json'}, ten='ket_qua.json')
            self.assertEqual(an_toan.kiem_tra_magic_bytes(b'\xef\xbb\xbf{"ket_qua": {}}', {'json'}), 'json')

    def test_dinh_kem_va_nhap_json(self):
        from pabt import ho_so_scan, phieu_kiem_dem as pk
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            con = csdl.mo(_du_an(td, 2))
            try:
                gia = td / 'gcn.pdf'
                gia.write_bytes(MZ)
                with self.assertRaises(LoiNhap):
                    ho_so_scan.them_file(con, 1, [gia])
                with self.assertRaises(LoiNhap):
                    ho_so_scan.them_file(con, 1, [td / 'chay.bat'])
                f = td / 'ket_qua.json'
                f.write_bytes(MZ)
                with self.assertRaises(LoiNhap):
                    pk.nhap_ket_qua_kiem_dem(con, f)
            finally:
                con.close()


class TestBieuThuc(unittest.TestCase):
    def test_nhieu_cum_va_ba_chieu(self):
        from pabt.tien import tinh_cong_thuc
        for chu, ct, dvt, gt in (('(11m x 3,8m) + (1,3 x 18m) + (16,5 x 1,5m) + (7m x 2m x 2)', '(11x3,8)+(1,3x18)+(16,5x1,5)+(7x2x2)',
                                  'm2', '117.95'),
                                 ('kt (3,4m x 18m) + (4,2 x 5m)', '(3,4x18)+(4,2x5)', 'm2', '82.2'),
                                 ('1,5m x 2,4m x 1,2m', '1,5x2,4x1,2', 'm3', '4.32'),
                                 ('Bể nước 2,0 x 2,0 x 1,2m', '2,0x2,0x1,2', 'm3', '4.8'),
                                 ('2x3x1,5 m3', '2x3x1,5', 'm3', '9')):
            kt = h.tinh_bieu_thuc_kich_thuoc(chu)
            self.assertEqual((kt['cong_thuc'], kt['dvt']), (ct, dvt), chu)
            self.assertEqual(tinh_cong_thuc(kt['cong_thuc']), Decimal(gt), chu)
        self.assertIsNone(h.tinh_bieu_thuc_kich_thuoc('35cm x 20cm x 10cm'))          # cm: không tự đổi đơn vị
        self.assertIsNone(h.tinh_bieu_thuc_kich_thuoc('(2m x 3m) + (1m x 1m x 1m)'))    # lẫn diện tích với thể tích

    def test_tach_dong_gop_nhieu_co(self):
        ds = h.tach_dong_qd42('Ống nhựa: ϕ 114: 3300m; ϕ 90: 3400m; ϕ 49: 3500m; ϕ 21: 3300m; ϕ 200: 40m')
        self.assertEqual(ds, ['Ống nhựa Φ114: 3300m', 'Ống nhựa Φ90: 3400m', 'Ống nhựa Φ49: 3500m', 'Ống nhựa Φ21: 3300m',
                              'Ống nhựa Φ200: 40m'])
        self.assertEqual(h.tach_dong_qd42('Nhà tạm\t42m2'), ['Nhà tạm\t42m2'])              # dòng thường giữ nguyên (cả Tab)
        self.assertEqual(len(doc_danh_sach('Ống nhựa: ϕ 114: 3300m; ϕ 90: 3400m')), 2)

    def test_dong_bien_ban(self):
        def d(s):
            k = h.tach_dong(s, nam=2026)
            return k['ten'], k['so_luong'], k['dvt'], k['so_do'], k['tuoi']
        self.assertEqual(d('Hồ nước xây gạch có tô kt 1,5m x 2,4m x 1,2m'), ('Hồ nước xây gạch có tô', '1,5x2,4x1,2', 'm3', '', ''))
        self.assertEqual(d('Mái che kt: (11m x 3,8m) + (7m x 2m x 2)'), ('Mái che', '(11x3,8)+(7x2x2)', 'm2', '', ''))
        self.assertEqual(d('Xoài trồng năm 2012: 650 cây'), ('Xoài', '650', 'cây', '', '14'))
        self.assertEqual(d('Cây ăn trái trồng năm 2026: 3 cây')[4], '1')                  # trồng năm nay: ít nhất 1 năm tuổi
        self.assertEqual(d('Tràm trồng năm 2023 ĐK gốc 10-15cm: 2700 cây'), ('Tràm', '2700', 'cây', '15', '3'))
        self.assertEqual(d('Tràm 35c/15cm'), ('Tràm', '35', 'cây', '15', ''))
        self.assertEqual(d('Xà cừ 04c/25'), ('Xà cừ', '4', 'cây', '25', ''))
        self.assertEqual(d('Giếng đào ϕ 1m sâu 8m'), ('Giếng đào ϕ 1m', '8', 'm', '', ''))
        self.assertEqual(d('Giếng khoan CN: ϕ 140 sâu 85m'), ('Giếng khoan CN ϕ 140', '85', 'm', '', ''))
        self.assertIn('ĐK gốc 10-15 cm', h.tach_dong('Tràm trồng năm 2023 ĐK gốc 10-15cm: 2700 cây', 2026)['ghi_chu'])
        self.assertIsNone(h.tach_dong('Tràm trồng 2000 cây', 2026)['tuoi'] or None)       # "trồng 2000 cây" không phải năm trồng


class TestKhopBoDonGia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        con = csdl.mo(_du_an(Path(cls.td.name), 1))
        cls.dm = DanhMuc(con)
        con.close()
        cls.bo = BoPhanLoai(cls.dm)

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def k(self, dong):
        d = doc_danh_sach(dong)[0]
        return h.bo_sung(self.bo, self.dm, d, self.bo.phan_loai(d['ten'], d['dvt']))

    def test_ong_theo_co(self):
        for co in ('114', '90', '49', '21'):
            k = self.k(f'Ống nhựa Bình Minh Φ{co}: 300m')
            self.assertTrue(k.khop is not None and k.khop.ten.endswith(f'D{co}'), (co, k.khop))
            self.assertGreaterEqual(k.do_tin, 0.9)
        k = self.k('Ống nhựa Φ200: 40m')                    # không có cỡ 200: cỡ lớn kế tiếp, nhắc xem lại
        self.assertTrue(k.khop.ten.endswith('D220'))
        self.assertLess(k.do_tin, 0.6)
        self.assertIn('Thực tế', k.ghi_them)

    def test_gieng(self):
        self.assertIn('Φ0,8 - 1m', self.k('Giếng đào ϕ 1m sâu 8m').khop.ten)
        self.assertIn('> Φ114', self.k('Giếng khoan CN: ϕ 140 sâu 85m').khop.ten)
        self.assertIsNone(self.k('Giếng đào ϕ 1m sâu 12m').khop)                       # sâu >= 10 m: không có mục -> chọn tay

    def test_cay_va_tu_hiem(self):
        k = h.bo_sung(self.bo, self.dm, dict(ten='Xoài', dvt='cây', tuoi='14'), self.bo.phan_loai('Xoài', 'cây'))
        self.assertEqual(h.tuoi_cua_muc(k.khop.ten, [m.ten for m in self.dm.muc[3]]), (14, 18))       # 30/10/2026: năm tuổi theo năm kiến thiết
        k = self.k('Cọ dầu: 450 cây')
        self.assertFalse(k.khop is not None and 'đậu' in k.khop.ten.lower())           # có dấu thì so có dấu
        self.assertIn('Terrazzo', self.k('Sân gạch Terrazzo kt (3,4m x 18m) + (4,2 x 5m)').khop.ten)


class TestNhapPhieu(unittest.TestCase):
    """Phiếu phiên bản 2: khớp hộ theo CCCD (mã hộ trong phiếu sai) / tờ thửa / họ tên tên file / hộ mới lô rừng."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name), 4)
        self.con = csdl.mo(self.p)
        with self.con:
            self.con.execute("UPDATE ho SET so_cccd = '075090000111' WHERE ma_ho = 1")
        self.addCleanup(self.con.close)

    def tearDown(self):
        self.doCleanups()
        self.td.cleanup()

    def phieu(self, ten, du):
        f = Path(self.td.name) / ten
        f.write_text(json.dumps(du, ensure_ascii=False), encoding='utf-8')
        return f

    def dong(self, ma):
        return [(r[0], r[1], r[2]) for r in self.con.execute('SELECT ten, so_luong, ma FROM ct_khoan WHERE ma_ho = ? ORDER BY id', (ma,))]

    def test_khop_bon_tang_va_tao_ho_moi(self):
        from pabt import phieu_kiem_dem as pk
        ma_ong = DanhMuc(self.con).tim(2, 'upvc D90')[0].ma
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Phạm Văn Thử' WHERE ma_ho = 3")
        du = dict(phien_ban=2, du_an='Thử', luc='2026-10-26T08:00:00', ket_qua={
            '3': [dict(muc=2, ten='Ống nhựa: ϕ 114: 30m; ϕ 21: 12m')],                          # mã 3 sai - CCCD là hộ 1
            'moi_1': [dict(muc=2, ma_dm=ma_ong, ten='Ống nước nhà bếp', so_luong='15')],         # tờ / thửa của hộ 2
            'moi_3': [dict(muc=3, ten='Tràm 35c/15cm')]},                                       # lô rừng: chưa có
            ho_dan={'3': dict(ma_ho=3, ho_ten='Ai đó', so_cccd='75090000111'),
                    'moi_1': dict(ho_ten='Chủ khác'),
                    'moi_3': dict(ho_ten='Nguyễn Văn Giả Lập', nguoi_su_dung='Trần Thị Thử', so_cccd='075080000999')},
            dat_dai={'moi_1': [dict(so_to='011', so_thua='103')],
                     'moi_3': [dict(tieu_khu='126', khoanh='6', lo='34', dt_ha='1,56', loai_dat='RSX')]})
        f = self.phieu('Pham_Van_Thu.json', du)                                                  # nhiều hộ: tên file không dùng
        cm = pk.ChiMucHo(self.con)
        self.assertEqual(pk.tim_ho_khop_json(self.con, dict(ma_ho=3, thong_tin=du['ho_dan']['3']), chi_muc=cm)[:2], (1, 'cccd'))
        kq = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual({k: (m, t) for k, m, t in kq['khop']}, {'3': (1, 'cccd'), 'moi_1': (2, 'thua')})
        self.assertEqual([x['khoa'] for x in kq['chua_khop']], ['moi_3'])
        self.assertEqual([(t, s) for t, s, _ in self.dong(1)], [('Ống dẫn nước nhựa uPVC D114', '30'), ('Ống dẫn nước nhựa uPVC D21', '12')])
        self.assertEqual(self.dong(2)[0][2], ma_ong)                                             # mã đơn giá có sẵn: áp thẳng
        # một hộ / file, không họ tên, không CCCD: tên file "Pham_Van_Thu.json" là tên hộ
        f1 = self.phieu('Pham_Van_Thu_1.json', dict(phien_ban=2, luc='2026-10-26T08:00:00', ket_qua={
            'moi_9': [dict(muc=3, ten='Xoài trồng năm 2012: 6 cây')]}))
        k1 = pk.nhap_ket_qua_kiem_dem(self.con, f1)
        self.assertEqual(k1['khop'], [('moi_9', 3, 'ho_ten')])                                   # "pham van thu 1" giống >= 0,88
        self.assertEqual(self.dong(3)[0][0], 'Cây xoài - Năm thu hoạch 11 - 15')                                          # năm kiểm đếm theo "luc" của phiếu
        k2 = pk.nhap_ket_qua_kiem_dem(self.con, f, tao_ho_moi=True, chi={'moi_3'})
        self.assertEqual(k2['tao_moi'], 1)
        ma = k2['khop'][0][1]
        h = self.con.execute('SELECT ho_ten, so_cccd, ghi_chu FROM ho WHERE ma_ho = ?', (ma,)).fetchone()
        self.assertEqual((h[0], h[1]), ('Nguyễn Văn Giả Lập', '075080000999'))
        self.assertIn('Người sử dụng: Trần Thị Thử', h[2])
        t = self.con.execute('SELECT so_to, so_thua, dt_thu_hoi FROM thua WHERE ma_ho = ?', (ma,)).fetchone()
        self.assertEqual((t[0], t[1], Decimal(t[2])), ('TK126/K6', '34', Decimal('15600')))
        self.assertTrue(self.dong(ma))                                                           # dòng tràm đã vào phương án
        # nhập lại cùng phiếu: hộ lô rừng nay khớp theo CCCD / lô
        self.assertEqual(pk.tim_ho_khop_json(self.con, dict(thong_tin=du['ho_dan']['moi_3']))[0], ma)
        self.assertEqual(pk.tim_ho_khop_json(self.con, dict(thong_tin={}, thua=du['dat_dai']['moi_3']))[:2], (ma, 'thua'))

    def test_phieu_cu_van_doc(self):
        from pabt import phieu_kiem_dem as pk
        f = self.phieu('ket_qua_kiem_dem.json', dict(phien_ban=1, du_an='Thử', ket_qua={'2': [dict(muc=2, ten='Nhà tạm: 20m2')]}))
        kq = pk.nhap_ket_qua_kiem_dem(self.con, f)
        self.assertEqual((kq['so_ho'], kq['so_dong'], kq['khop'][0][2]), (1, 1, 'ma_ho'))

    def test_hop_hoi_tao_ho_moi(self):
        try:
            import PySide6  # noqa: F401
        except ImportError:
            self.skipTest('không có Qt')
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_kiem_dem import HopKiemDem
        f = self.phieu('Nguyen_Moi.json', dict(phien_ban=2, du_an='Thử', ket_qua={'moi_1': [dict(muc=2, ten='Nhà tạm: 12m2')]},
                                                ho_dan={'moi_1': dict(ho_ten='Lê Văn Mới')}))
        hop = HopKiemDem(None, self.con, im_lang=True)
        kq = hop.nhap(f, tao_ho_moi=True)
        self.assertEqual((kq['tao_moi'], kq['so_dong']), (1, 1))
        self.assertTrue(self.con.execute("SELECT 1 FROM ho WHERE ho_ten = 'Lê Văn Mới'").fetchone())
        hop.close()


if __name__ == '__main__':
    unittest.main()
