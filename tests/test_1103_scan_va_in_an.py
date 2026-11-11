"""1.1.03 - cổng nghiệm thu: kiểm định đơn giá sau khi quét, dàn trang cân đối giữ nguyên lề, hộp Thiết lập trang, xem trước ngay.
Số liệu GIẢ LẬP (không có giá / tên thật)."""
from __future__ import annotations

import ast
import os
import py_compile
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl                                                                  # noqa: E402

from pabt import gia_dat_nq28 as nq                                              # noqa: E402
from pabt import kiem_dinh_don_gia as kd                                         # noqa: E402

GOC = Path(__file__).resolve().parent.parent / 'pabt'


def _dong(ten, vt, **gia):
    r = dict(xa='Xã Thử', tt=1, ten_duong=ten, diem_dau='Đầu', diem_cuoi='Cuối', vi_tri=vt, dat_o=0, tmdv=0, sxkd=0, nn_cay=0,
             nn_rung_nts=0)
    r.update(gia)
    return r


class TestBienDich(unittest.TestCase):
    def test_ca_goi_pabt_bien_dich_duoc(self):
        """ast.parse (cú pháp Python 3.8) + py_compile mọi file pabt/."""
        loi = []
        with tempfile.TemporaryDirectory() as td:
            for p in sorted(GOC.glob('*.py')):
                try:
                    ast.parse(p.read_text(encoding='utf-8'), feature_version=(3, 8))
                    py_compile.compile(str(p), cfile=str(Path(td) / (p.stem + '.pyc')), doraise=True)
                except (SyntaxError, py_compile.PyCompileError) as e:
                    loi.append(f'{p.name}: {e}')
        self.assertEqual(loi, [])

    def test_phien_ban(self):
        import pabt
        from pabt import lich_su_cap_nhat
        self.assertEqual(pabt.__version__, '1.1.03')
        self.assertIn('1.1.03', Path(lich_su_cap_nhat.__file__).read_text(encoding='utf-8'))


class TestKiemDinhGiaDat(unittest.TestCase):
    def test_vi_tri_sau_cao_hon_vi_tri_truoc(self):
        ds = [_dong('Đường A', 'VT1', dat_o=5000), _dong('Đường A', 'VT2', dat_o=5800), _dong('Đường A', 'VT3', dat_o=2000),
              _dong('Đường B', 'VT1', dat_o=4000), _dong('Đường B', 'VT2', dat_o=3000)]
        kq = kd.kiem_dinh_bang_gia_dat(ds)
        co = {x['i']: x['co'] for x in kq['dong']}
        self.assertIn(kd.LOI_THU_TU_VI_TRI, co[0])
        self.assertIn(kd.LOI_THU_TU_VI_TRI, co[1])
        self.assertEqual(co[2], [])
        self.assertEqual(co[3], co[4], [])
        self.assertEqual([x['i'] for x in kq['can_xac_nhan']], [0, 1])
        self.assertTrue(kq['chan_ap_dung'])
        self.assertEqual(kq['dong'][1]['muc'], 'do')
        self.assertEqual(kq['dong'][3]['diem_tin_cay'], 100)

    def test_mo_hinh_mat_tien_dau_noi(self):
        """MT >= T1 >= T2 >= T3, MT >= K1 >= K2 >= K3, T >= K cùng mức; K1 cao hơn T3 là bình thường (bảng NQ 28 thật)."""
        tot = [_dong('Đường A', v, dat_o=g) for v, g in zip(('MT', 'T1', 'T2', 'T3', 'K1', 'K2', 'K3'), (1000, 700, 600, 500, 700, 600, 500))]
        self.assertEqual(kd.kiem_dinh_bang_gia_dat(tot)['can_xac_nhan'], [])
        sai = [dict(r) for r in tot]
        sai[5]['dat_o'] = 650                           # K2 650 > T2 600
        kq = kd.kiem_dinh_bang_gia_dat(sai)
        self.assertEqual(sorted(x['i'] for x in kq['can_xac_nhan']), [2, 5])

    def test_hai_doan_trung_chu_khong_tron(self):
        ds = [_dong('Đường A', 'VT1', dat_o=3000), _dong('Đường A', 'VT2', dat_o=2000),
              _dong('Đường A', 'VT1', dat_o=9000), _dong('Đường A', 'VT2', dat_o=7000)]
        self.assertEqual(kd.kiem_dinh_bang_gia_dat(ds)['can_xac_nhan'], [])

    def test_nong_nghiep_cao_hon_dat_o(self):
        ds = [_dong('Đường A', 'VT1', dat_o=800, nn_cay=900), _dong('Đường B', 'VT1', dat_o=800, tmdv=600, sxkd=500, nn_cay=120)]
        kq = kd.kiem_dinh_bang_gia_dat(ds)
        self.assertEqual(kq['dong'][0]['co'], [kd.LOI_CHEO_COT_LOAI_DAT])
        self.assertEqual(kq['dong'][1]['co'], [])
        self.assertIn('lệch cột', kq['dong'][0]['ly_do'][0])

    def test_bac_do_lon_va_le_dong(self):
        kq = kd.kiem_dinh_bang_gia_dat([_dong('A', 'VT1', dat_o=128443), _dong('B', 'VT1', dat_o=5000),
                                        _dong('C', 'VT1', dat_o=600_000_000), _dong('D', 'VT1', dat_o=500000)], don_vi='dong')
        self.assertEqual([x['co'] for x in kq['dong']], [[kd.NGHI_NGO_DON_VI_HOAC_OCR]] * 3 + [[]])
        self.assertEqual(kq['dong'][0]['muc'], 'vang')
        kq = kd.kiem_dinh_bang_gia_dat([_dong('A', 'VT1', dat_o=5)])               # 5 nghìn đồng/m² đất ở
        self.assertEqual(kq['dong'][0]['co'], [kd.NGHI_NGO_DON_VI_HOAC_OCR])
        kq = kd.kiem_dinh_bang_gia_dat([_dong('A', 'VT1', dat_o=3000), _dong('A', 'VT2', dat_o=120)])   # mất một chữ số
        self.assertEqual(kq['dong'][1]['co'], [kd.NGHI_NGO_DON_VI_HOAC_OCR])

    def test_so_voi_bang_dang_dung_va_do_tin_cay_nhan_dang(self):
        goc = [_dong('Đường A', 'VT1', dat_o=1000)]
        kq = kd.kiem_dinh_bang_gia_dat([_dong('Đường A', 'VT1', dat_o=1600)], goc=goc)
        self.assertEqual((kq['dong'][0]['co'], kq['dong'][0]['diem_tin_cay'], kq['dong'][0]['muc']), ([kd.LECH_SO_VOI_GOC], 80, 'vang'))
        self.assertFalse(kq['chan_ap_dung'])
        r = _dong('Đường A', 'VT1', dat_o=1000)
        r['ocr_tin_cay'] = 70
        self.assertEqual(kd.kiem_dinh_bang_gia_dat([r])['dong'][0]['co'], [kd.OCR_KEM_TIN_CAY])
        kq = kd.kiem_dinh_bang_gia_dat([_dong('Đường A', 'VT1', dat_o=1000)], don_vi_chac=False)
        self.assertLessEqual(kq['diem_tin_cay'], 90)
        self.assertIn('đơn vị', kq['tom_tat'])

    def test_bang_gan_san_khong_bi_danh_dau_tran_lan(self):
        """Bảng NQ 28 gắn sẵn (1.127 dòng): phép soi không được báo tràn lan - chỉ đoạn có giá mặt tiền thấp hơn đấu nối trong văn bản."""
        ds = nq.tat_ca() if not nq.dang_thay() else []
        if len(ds) < 1000:
            self.skipTest('bảng gắn sẵn đang bị thay')
        kq = kd.kiem_dinh_bang_gia_dat(ds)
        self.assertLessEqual(len(kq['can_xac_nhan']), 5)
        self.assertGreaterEqual(kq['diem_tin_cay'], 99)


class TestDonViNghinDong(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _excel(self, ten, dau, hang, tieu_de=('Tên đường', 'Vị trí', 'Đơn giá')):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Xã Thử'
        ws['A1'] = dau
        ws.append(list(tieu_de))
        for h in hang:
            ws.append(list(h))
        p = self.td / ten
        wb.save(p)
        wb.close()
        return p

    def test_doan_don_vi(self):
        self.assertEqual(kd.doan_don_vi([500000, 300000]), ('dong', False))
        self.assertEqual(kd.doan_don_vi([12_500_000, 300000]), ('dong', True))
        self.assertEqual(kd.doan_don_vi([15300, 7200]), ('nghin', True))
        self.assertEqual(kd.doan_don_vi([15300, 12500]), ('nghin', False))
        self.assertEqual(kd.doan_don_vi([]), ('nghin', False))

    def test_excel_gia_duoi_mot_trieu_khong_nhan_1000(self):
        """Bảng không ghi đơn vị, giá 500.000 / 300.000: trước 1.1.03 thành 500 triệu đồng/m²."""
        dong, _vb, chu = nq.doc_excel(self._excel('a.xlsx', 'Bảng giá đất ở xã Thử', [('Đường A', 'VT1', 500000), ('Đường A', 'VT2', 300000)]))
        self.assertEqual([nq.gia_dong(r, 'dat_o') for r in dong], [500_000, 300_000])
        self.assertIn('CHƯA RÕ ĐƠN VỊ', chu)
        self.assertIn('đồng/m²', chu)

    def test_excel_nghin_dong_nhu_van_ban_giu_nguyen(self):
        dong, _vb, chu = nq.doc_excel(self._excel('b.xlsx', 'Bảng giá đất ở xã Thử', [('Đường A', 'VT1', 15300), ('Đường A', 'VT2', 7200)]))
        self.assertEqual([r['dat_o'] for r in dong], [15300, 7200])
        self.assertNotIn('CHƯA RÕ', chu)
        dong, _vb, chu = nq.doc_excel(self._excel('c.xlsx', 'Bảng giá đất ở. Đơn vị: nghìn đồng/m²', [('Đường A', 'VT1', 20000)]))
        self.assertEqual(dong[0]['dat_o'], 20000)       # ghi rõ "nghìn": không đoán
        self.assertNotIn('CHƯA RÕ', chu)

    def test_bang_chu_gia_duoi_mot_trieu(self):
        from pabt.cap_nhat_gia_dat import _dong_tu_o
        dong, chu = _dong_tu_o([['Tên đường', 'Vị trí', 'Đơn giá'], ['Đường A', 'VT1', '500.000'], ['Đường A', 'VT2', '300.000']],
                               'x.csv', 'Xã Thử')
        self.assertEqual([r['dat_o'] for r in dong], [500, 300])
        self.assertIn('CHƯA RÕ ĐƠN VỊ', chu)
        dong, chu = _dong_tu_o([['Đơn vị: đồng/m²'], ['Tên đường', 'Vị trí', 'Đơn giá'], ['Đường A', 'VT1', '500.000'],
                                ['Đường A', 'VT2', '128.443']], 'y.csv', 'Xã Thử')
        self.assertIn('lẻ dưới 100 đồng', chu)

    def test_nghi_quyet_ghi_dong_khong_lan_hai_don_vi(self):
        """Cùng một bảng: 1.200.000 và 500.000 đều là đồng/m² (trước: 1.200 nghìn và 500.000 nghìn)."""
        from pabt.cap_nhat_gia_dat import phan_tich_nghi_quyet
        bang = [['Xã Thử'], ['TT', 'Tên đường', 'Điểm đầu', 'Điểm cuối', 'Đất ở', 'Đất thương mại, dịch vụ'],
                ['1', 'Đường A', 'Đầu', 'Cuối', '1.200.000', '900.000'], ['2', 'Đường B', 'Đầu', 'Cuối', '500.000', '350.000']]
        self.assertEqual([(r['dat_o'], r['tmdv']) for r in phan_tich_nghi_quyet(bang)], [(1200, 900), (500, 350)])
        bang = [['Xã Thử'], ['TT', 'Tên đường', 'Điểm đầu', 'Điểm cuối', 'Đất ở', 'Đất thương mại, dịch vụ'],
                ['1', 'Đường A', 'Đầu', 'Cuối', '15.300', '7.200']]
        self.assertEqual([(r['dat_o'], r['tmdv']) for r in phan_tich_nghi_quyet(bang)], [(15300, 7200)])

    def test_cot_don_gia_cua_bang_nong_nghiep_khong_vao_dat_o(self):
        p = self._excel('d.xlsx', 'Bảng giá đất nông nghiệp xã Thử', [('Đường A', 'VT1', 85000)])
        with self.assertRaises(nq.LoiBangGia) as c:
            nq.doc_excel(p)
        self.assertIn('nông nghiệp', str(c.exception))
        from pabt.cap_nhat_gia_dat import _dong_tu_o
        with self.assertRaises(nq.LoiBangGia):
            _dong_tu_o([['Bảng giá đất trồng cây lâu năm'], ['Tên đường', 'Vị trí', 'Đơn giá'], ['Đường A', 'VT1', '85.000']], 'z.csv', 'Xã Thử')
        # bảng đất ở, hoặc cột ghi rõ loại đất: vẫn đọc
        dong, _vb, _chu = nq.doc_excel(self._excel('e.xlsx', 'Bảng giá đất nông nghiệp', [('Đường A', 'VT1', 85000)],
                                                   ('Tên đường', 'Vị trí', 'Đất trồng cây lâu năm')))
        self.assertEqual((dong[0]['dat_o'], nq.gia_dong(dong[0], 'nn_cay')), (0, 85000))
        self.assertFalse(kd.tieu_de_la_dat_nong_nghiep('Bảng giá đất phi nông nghiệp Xã Rừng Thông'))
        self.assertFalse(kd.tieu_de_la_dat_nong_nghiep('Bảng giá đất ở và đất nông nghiệp'))
        self.assertTrue(kd.tieu_de_la_dat_nong_nghiep('Giá đất rừng sản xuất'))


class TestKiemDinhTaiSanCay(unittest.TestCase):
    def test_duong_kinh_lon_hon_gia_thap_hon(self):
        ds = [dict(ten='Cây thử (d <5 cm)', don_gia='40000'), dict(ten='Cây thử (d >5-10 cm)', don_gia='90000'),
              dict(ten='Cây thử (d >10-15 cm)', don_gia='60000'), dict(ten='Cây thử (d >15-20 cm)', don_gia='150000'),
              dict(ten='Cây khác (d <5 cm)', don_gia='10000'), dict(ten='Cây khác (d >5-10 cm)', don_gia='20000')]
        kq = kd.kiem_dinh_don_gia_tai_san_cay(ds, goc={})
        self.assertEqual(sorted(x['i'] for x in kq['can_xac_nhan']), [1, 2])
        self.assertEqual(kq['dong'][2]['co'], [kd.LOI_THU_TU_KICH_THUOC])
        self.assertTrue(kq['chan_ap_dung'])

    def test_nam_tuoi_va_ten_giu_dau(self):
        ds = [dict(ten='Cây ăn quả thử - Năm thứ 1', don_gia=300000), dict(ten='Cây ăn quả thử - Năm thứ 2', don_gia=250000),
              dict(ten='Sụ thử (d >9-12 cm)', don_gia=400000), dict(ten='Sú thử (d >10-12 cm)', don_gia=170000)]
        kq = kd.kiem_dinh_don_gia_tai_san_cay(ds, goc={})
        self.assertEqual(sorted(x['i'] for x in kq['can_xac_nhan']), [0, 1])     # "Sụ" và "Sú" là hai loại cây: không so với nhau

    def test_lech_so_voi_goc_va_gia_le(self):
        ds = [dict(ten='Nhà thử loại 1', don_gia=Decimal('5000000')), dict(ten='Nhà thử loại 2', don_gia='4000000'),
              dict(ten='Cây lẻ', don_gia='313119'), dict(ten='Rau thử', don_gia='1.5'), dict(ten='Trống', don_gia='')]
        kq = kd.kiem_dinh_don_gia_tai_san_cay(ds, goc={'Nhà thử loại 1': '1000000', 'Nhà thử loại 2': ['3900000', '9000000']})
        co = [x['co'] for x in kq['dong']]
        self.assertEqual(co, [[kd.CAN_DOI_CHIEU_BAN_GOC], [], [], [kd.CAN_DOI_CHIEU_BAN_GOC], [kd.CAN_DOI_CHIEU_BAN_GOC]])
        self.assertIn('300%', kq['dong'][0]['ly_do'][0])

    def test_bo_don_gia_dong_kem_khong_bao_tran_lan(self):
        import sqlite3
        from pabt import tai_nguyen
        p = tai_nguyen('bo_don_gia.sqlite')
        truoc = p.read_bytes()
        con = sqlite3.connect('file:' + str(p).replace('\\', '/') + '?mode=ro', uri=True)
        try:
            ds = [dict(ten=t, don_gia=g) for t, g in con.execute('SELECT ten, don_gia FROM dm_taisan')]
        finally:
            con.close()
        kq = kd.kiem_dinh_don_gia_tai_san_cay(ds)
        self.assertLess(len(kq['can_xac_nhan']), len(ds) // 100)
        self.assertEqual(p.read_bytes(), truoc)          # bộ đóng kèm không bị ghi


class TestNiemPhong(unittest.TestCase):
    def test_ma_bam(self):
        self.assertEqual(kd.niemphong_sha256(b'abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertTrue(kd.kiem_niem_phong(b'abc', ' BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD\n'))
        self.assertFalse(kd.kiem_niem_phong(b'abd', kd.niemphong_sha256(b'abc')))
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'g.bin'
            f.write_bytes(b'abc')
            self.assertEqual(kd.niem_phong_file(f), kd.niemphong_sha256(b'abc'))

    def test_goi_larcgia_bi_sua_thi_tu_choi(self):
        from pabt import goi_gia_dat as gg
        xa = [x['ten'] for x in gg.ds_xa_cho_goi_cai() if x['du']]
        if not xa:
            self.skipTest('máy thử không có địa bàn đủ giá + hệ số K')
        with tempfile.TemporaryDirectory() as td:
            f = gg.xuat_goi_cai(Path(td) / 'g.larcgia', xa[:1])
            goi = gg.doc_goi_cai(f)
            self.assertTrue(goi['mo_ta'].get('niem_phong_khop'))
            self.assertEqual(sorted(goi['mo_ta']['niem_phong']), ['bang_gia_dat.json', 'goi.json', 'he_so_k.json'])
            # sửa một giá trong gói mà không tính lại mã băm
            sua = Path(td) / 'sua.larcgia'
            with zipfile.ZipFile(f) as z, zipfile.ZipFile(sua, 'w') as z2:
                for n in z.namelist():
                    du = z.read(n)
                    if n == 'bang_gia_dat.json':
                        du = du.replace(b'"dat_o": ', b'"dat_o": 1', 1)
                    z2.writestr(n, du)
            with self.assertRaises(gg.LoiGoi) as c:
                gg.doc_goi_cai(sua)
            self.assertIn('SHA-256', str(c.exception))
            # gói cũ không có mã băm: vẫn đọc
            cu = Path(td) / 'cu.larcgia'
            import json
            with zipfile.ZipFile(f) as z, zipfile.ZipFile(cu, 'w') as z2:
                for n in z.namelist():
                    du = z.read(n)
                    if n == 'mo_ta.json':
                        mo = json.loads(du.decode('utf-8'))
                        mo.pop('niem_phong')
                        du = json.dumps(mo, ensure_ascii=False).encode('utf-8')
                    z2.writestr(n, du)
            self.assertFalse(gg.doc_goi_cai(cu)['mo_ta'].get('niem_phong_khop'))


if __name__ == '__main__':
    unittest.main()
