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


# ---------------------------------------------------------------- hạng mục 2: dàn trang cân đối, giữ nguyên lề
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CAU = 'Đất giả lập do hộ sử dụng ổn định từ năm 1995, không tranh chấp, phù hợp quy hoạch sử dụng đất. '


def _du_an_n_thua(td: Path, n: int, k: int = 1) -> Path:
    """Một hộ giả lập có n thửa (n dòng mục 1 của bảng mục III), nguồn gốc mỗi thửa k câu."""
    from pabt import csdl, du_an_moi
    dong = [dict(ho_ten='Nguyễn Văn Thử', dia_chi='Ấp 1, xã Mẫu', so_to='3', so_thua=str(200 + i), loai_dat='CLN',
                 dt_thu_hoi=str(100 + i * 7), vi_tri='1') for i in range(n)]
    p = td / f'dt_{n}_{k}.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Dự án thử dàn trang', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    con = csdl.mo(p)
    try:
        with con:
            con.execute('UPDATE thua SET nguon_goc = ?', (CAU * k,))
    finally:
        con.close()
    return p


class TestMayDanTrang(unittest.TestCase):
    """dan_trang: mô phỏng ngắt trang + chọn thông số, trên các khối giả lập (không Qt)."""

    def _van_ban(self, so_hang: int, cao_hang: float = 30.0, dau: float = 200.0, cuoi: float = 150.0):
        from pabt import dan_trang as dt

        def dung(ts):
            tru = (28 - ts.dem_doc) / 20 * 2
            kh = [dt.Khoi('d', dau - (120 - ts.sau_doan) / 20, vai='muc2', sau=ts.sau_doan / 20),
                  dt.Khoi('h', 30, phu=2.8, trong_bang=True, vai='tieu_de')]
            for i in range(so_hang):
                kh.append(dt.Khoi('h', max(cao_hang - tru, ts.cao_hang.get(i, 0) / 20 + ts.dem_doc / 10), phu=ts.dem_doc / 10,
                                  trong_bang=True, chi_so=i, gian=True, vai='so_lieu'))
            kh.append(dt.Khoi('h', 20, giu_sau=True, trong_bang=True, vai='bang'))
            kh.append(dt.Khoi('h', cuoi - (4 - ts.dong_ky) * 15, trong_bang=True, vai='ky'))
            return kh
        return dung

    def test_mot_trang_khong_dieu_tiet(self):
        from pabt import dan_trang as dt
        ts = dt.dieu_tiet(self._van_ban(5), 785.2)
        self.assertEqual((ts.so_trang, ts.che_do, ts.cao_hang, ts.dem_doc, ts.sau_doan), (1, '', {}, 28, 120))
        self.assertTrue(ts.la_chuan())

    def test_tran_it_thi_thu_gon_ve_mot_trang(self):
        from pabt import dan_trang as dt
        dung = self._van_ban(13)                           # 200 + 31 + 13 x 31 + 21 + 151 = 806 > 785,2: thừa ~21 pt
        self.assertEqual(len(dt.chia_trang(dung(dt.ThongSo()), 785.2, 31)), 2)
        ts = dt.dieu_tiet(dung, 785.2)
        self.assertEqual((ts.so_trang, ts.che_do), (1, 'thu_gon'))
        self.assertLess(ts.dem_doc, 28)
        self.assertEqual(ts.cao_hang, {})
        self.assertGreaterEqual(ts.ho[0], dt.AN_TOAN_THU)

    def test_nhieu_trang_thi_gian_deu_trang_truoc(self):
        from pabt import dan_trang as dt
        dung = self._van_ban(30)
        truoc = dt.chia_trang(dung(dt.ThongSo()), 785.2, 31)
        self.assertEqual(len(truoc), 2)
        self.assertGreater(785.2 - truoc[0].dung, dt.HO_TOI_THIEU)
        ts = dt.dieu_tiet(dung, 785.2)
        self.assertEqual((ts.so_trang, ts.che_do), (2, 'gian'))
        self.assertLessEqual(ts.ho[0], dt.AN_TOAN_DAU + 1)                 # trang 1 chỉ còn hở phần chừa an toàn
        self.assertIn('tieu_de', ts.cao_hang)
        sau = dt.chia_trang(dung(ts), 785.2, 31)
        self.assertEqual(dt._trang_cua(sau), dt._trang_cua(truoc))         # không dòng nào đổi trang
        them = [ts.cao_hang[i] / 20 + 2.8 - 30 for i in ts.cao_hang if i != 'tieu_de']
        self.assertTrue(all(0 < x <= dt.GIAN_TOI_DA + 0.1 for x in them))

    def test_khoi_di_lien_va_cat_dong(self):
        from pabt import dan_trang as dt
        kh = [dt.Khoi('d', 700), dt.Khoi('h', 40, giu_sau=True), dt.Khoi('h', 60)]
        tr = dt.chia_trang(kh, 785.2)
        self.assertEqual([[v for v, _ in t.khoi] for t in tr], [[0], [1, 2]])      # 40 vừa nhưng đi liền khối 60: cả hai sang trang
        kh = [dt.Khoi('d', 700), dt.Khoi('d', 120, tach=True, so_dong=10, cao_dong=12)]
        tr = dt.chia_trang(kh, 785.2)
        self.assertEqual([round(t.dung, 1) for t in tr], [784.0, 36.0])             # 7 dòng ở trang 1, 3 dòng sang trang 2
        self.assertEqual(dt.dem_dong('a b c d', 25, 10, False, lambda s, f, c, d: len(s) * 10.0), 4)
        self.assertEqual(dt.dem_dong('', 25, 10, False, lambda s, f, c, d: 1.0), 1)

    def test_hai_doan_lien_nhau_lay_khoang_cach_lon_hon(self):
        from pabt import dan_trang as dt
        kh = dt.gop_khoang_cach([dt.Khoi('d', 20, sau=6), dt.Khoi('d', 30, truoc=10), dt.Khoi('h', 5), dt.Khoi('d', 30, truoc=10)])
        self.assertEqual([k.cao for k in kh], [20, 24, 5, 30])


class TestDanTrangWord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from unittest import mock
        from pabt import in_an
        self._td = tempfile.TemporaryDirectory()
        self.td = Path(self._td.name)
        do = lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47)      # noqa: E731 - đo chữ cố định: kết quả không theo phông máy
        self._vo = mock.patch.object(in_an, '_ham_do_chu', lambda: do)
        self._vo.start()

    def tearDown(self):
        self._vo.stop()
        self._td.cleanup()

    def _xml(self, n: int, k: int = 1, du_thao: bool = False):
        from pabt import csdl, in_word
        from xml.etree import ElementTree as ET
        con = csdl.mo(_du_an_n_thua(self.td, n, k))
        try:
            ma = con.execute('SELECT ma_ho FROM ho').fetchone()[0]
            ts, truoc = in_word.du_doan_dan_trang(con, ma, du_thao=du_thao)
            f = in_word.xuat_chi_tiet_docx(con, ma, self.td / f'pa_{n}.docx', du_thao=du_thao)
        finally:
            con.close()
        with zipfile.ZipFile(f) as z:
            goc = ET.fromstring(z.read('word/document.xml'))
        return goc, ts, truoc, f

    def _tim(self, che_do: str):
        """Hộ nhỏ nhất (số thửa) mà bộ dàn trang chọn chế độ này."""
        for n in range(6, 26):
            goc, ts, truoc, f = self._xml(n)
            if ts.che_do == che_do:
                return n, goc, ts, truoc, f
        self.fail(f'không hộ nào từ 6 đến 25 thửa vào chế độ {che_do}')

    def _le_va_rong(self, goc):
        from pabt import in_word
        sp = goc.find(f'{W}body/{W}sectPr')
        le = sp.find(W + 'pgMar')
        kho = sp.find(W + 'pgSz')
        bang = [t for t in goc.iter(W + 'tbl') if any(r.find(f'{W}trPr/{W}tblHeader') is not None for r in t.findall(W + 'tr'))][0]
        self.assertEqual({k: int(le.get(W + v)) for k, v in (('trai', 'left'), ('phai', 'right'), ('tren', 'top'), ('duoi', 'bottom'))},
                         {k: in_word.twip(v) for k, v in in_word.LE_MM.items()})
        self.assertEqual((int(kho.get(W + 'w')), int(kho.get(W + 'h'))), in_word.KHO_A4)
        self.assertEqual(int(bang.find(f'{W}tblPr/{W}tblW').get(W + 'w')), in_word.rong_trang())
        self.assertEqual(sum(int(c.get(W + 'w')) for c in bang.find(W + 'tblGrid')), in_word.rong_trang())
        return bang

    def test_mot_trang_giu_bo_cuc_chuan(self):
        goc, ts, truoc, _f = self._xml(3)
        bang = self._le_va_rong(goc)
        self.assertEqual((ts.so_trang, ts.che_do, len(truoc)), (1, '', 1))
        self.assertEqual(list(bang.iter(W + 'trHeight')), [])
        self.assertEqual(bang.find(f'{W}tblPr/{W}tblCellMar/{W}top').get(W + 'w'), '28')

    def test_mo_coi_tu_thu_gon_ve_mot_trang(self):
        """Khối cuối (thưởng + tổng cộng + mục IV + chữ ký) chỉ thừa vài dòng: thu khoảng cách, không đổi lề, về đúng một trang."""
        _n, goc, ts, truoc, _f = self._tim('thu_gon')
        bang = self._le_va_rong(goc)
        self.assertEqual((len(truoc), ts.so_trang), (2, 1))
        dem = int(bang.find(f'{W}tblPr/{W}tblCellMar/{W}top').get(W + 'w'))
        self.assertEqual(dem, ts.dem_doc)
        self.assertTrue(ts.sau_doan < 120 or ts.dem_doc < 28 or ts.dong_ky < 4)
        self.assertEqual(list(bang.iter(W + 'trHeight')), [])
        self.assertEqual(bang.find(f'{W}tblPr/{W}tblCellMar/{W}left').get(W + 'w'), '40')      # đệm trái / phải không đổi

    def test_hai_trang_tu_gian_khong_ho_chan_trang(self):
        _n, goc, ts, truoc, _f = self._tim('gian')
        bang = self._le_va_rong(goc)
        self.assertEqual((len(truoc), ts.so_trang), (2, 2))
        self.assertGreater(truoc[0], ts.ho[0])                                 # khoảng hở cuối trang 1 giảm
        self.assertLessEqual(ts.ho[0], 9)
        cao = list(bang.iter(W + 'trHeight'))
        self.assertGreaterEqual(len(cao), 5)
        self.assertTrue(all(h.get(W + 'hRule') == 'atLeast' for h in cao))
        # thứ tự thuộc tính dòng đúng lược đồ, dòng tiêu đề vẫn lặp đầu trang
        dau = bang.findall(W + 'tr')[0].find(W + 'trPr')
        self.assertEqual([c.tag[len(W):] for c in dau], ['cantSplit', 'trHeight', 'tblHeader'])

    def test_tat_tu_co_gian_o_ho_so(self):
        from pabt import in_word
        n = self._tim('gian')[0]
        cu = in_word.TU_CO_GIAN
        in_word.TU_CO_GIAN = False
        try:
            goc, ts, _truoc, _f = self._xml(n)
        finally:
            in_word.TU_CO_GIAN = cu
        self.assertEqual((ts.che_do, list(goc.iter(W + 'trHeight'))), ('', []))

    def test_van_ban_ket_thuc_bang_doan_1_pt(self):
        """Word tự thêm đoạn trống 13 pt sau bảng cuối văn bản (bảng sát đáy trang thì thành một trang trắng): đã đặt đoạn 1 pt."""
        goc = self._xml(3)[0]
        than = [c for c in goc.find(W + 'body') if c.tag != W + 'sectPr']
        self.assertEqual(than[-1].tag, W + 'p')
        sp = than[-1].find(f'{W}pPr/{W}spacing')
        self.assertEqual((sp.get(W + 'line'), sp.get(W + 'lineRule')), ('20', 'exact'))
        self.assertEqual(than[-2].tag, W + 'tbl')

    def test_openxml_hang_va_bang(self):
        from pabt import openxml_word as ox
        h = ox.hang([ox.o(ox.doan(ox.chay('a')), 1000)], cao_twip=500)
        self.assertIn('<w:trHeight w:val="500" w:hRule="atLeast"/>', h)
        self.assertIn('w:hRule="exact"', ox.hang([ox.o('', 1000)], cao_twip=300, quy_tac_cao='exact'))
        self.assertNotIn('trHeight', ox.hang([ox.o('', 1000)]))
        b = ox.bang([h], [1000], dem_doc_twip=10)
        self.assertIn('<w:top w:w="10" w:type="dxa"/>', b)
        self.assertIn('<w:bottom w:w="10" w:type="dxa"/>', b)
        self.assertIn('<w:top w:w="28" w:type="dxa"/>', ox.bang([h], [1000]))


@unittest.skipUnless(os.name == 'nt' and os.environ.get('PABT_THU_WORD') != '0', 'cần Microsoft Word')
class TestDanTrangWordThat(unittest.TestCase):
    """Đối chiếu với Microsoft Word thật (đo chữ bằng phông thật): số trang và khoảng hở cuối trang trong file PDF Word xuất."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from pabt import van_ban_trinh
        cls.app = QApplication.instance() or QApplication([])
        if not van_ban_trinh.co_word():
            raise unittest.SkipTest('máy không có Microsoft Word')

    def _day_muc(self, pdf) -> list:
        """[(cao trang pt, y thấp nhất có mực pt)] từng trang."""
        from PySide6.QtCore import QSize
        from PySide6.QtPdf import QPdfDocument
        d = QPdfDocument()
        d.load(str(pdf))
        kq = []
        try:
            for i in range(d.pageCount()):
                sz = d.pagePointSize(i)
                anh = d.render(i, QSize(int(sz.width()), int(sz.height())))
                duoi = 0
                for y in range(anh.height() - 1, -1, -1):
                    if any(anh.pixelColor(x, y).alpha() > 40 and anh.pixelColor(x, y).lightness() < 200 for x in range(0, anh.width(), 2)):
                        duoi = y
                        break
                kq.append((sz.height(), duoi))
        finally:
            d.close()
        return kq

    def test_word_that(self):
        from pabt import csdl, in_word
        from pabt import xem_truoc_tai_lieu as xt
        if in_word._ham_do() is None:
            self.skipTest('không đo được chữ bằng Qt')
        thay = {}
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for n in range(8, 16):
                con = csdl.mo(_du_an_n_thua(td, n))
                try:
                    ma = con.execute('SELECT ma_ho FROM ho').fetchone()[0]
                    ts, truoc = in_word.du_doan_dan_trang(con, ma)
                    if ts.che_do in thay or not ts.che_do:
                        continue
                    f = in_word.xuat_chi_tiet_docx(con, ma, td / f'w_{n}.docx')
                finally:
                    con.close()
                loi = xt.chuyen_pdf(f, f.with_suffix('.pdf'))
                if loi:
                    self.skipTest(f'Word không xuất được PDF: {loi}')
                thay[ts.che_do] = (ts, truoc, self._day_muc(f.with_suffix('.pdf')))
                if len(thay) == 2:
                    break
        self.assertEqual(sorted(thay), ['gian', 'thu_gon'])
        ts, truoc, trang = thay['thu_gon']
        self.assertEqual((len(truoc), len(trang)), (2, 1))                     # trước 2 trang, Word thật còn 1 trang
        ts, truoc, trang = thay['gian']
        self.assertEqual(len(trang), 2)
        cao, duoi = trang[0]
        le_duoi = in_word.LE_MM['duoi'] / 25.4 * 72
        ho = cao - le_duoi - duoi
        self.assertGreaterEqual(ho, 0)                                          # không lấn lề dưới
        self.assertLess(ho, 16)                                                 # trước 1.1.03 hở 23 - 150 pt


class TestGianKhitTrangExcel(unittest.TestCase):
    """in_an.gian_khit_trang: bảng tổng hợp - chia khoảng hở cuối trang vào chiều cao dòng, không đổi lề / tỷ lệ in / chỗ ngắt."""

    def _sheet(self, cao: list, ti_le: int = 55):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.page_setup.scale = ti_le
        for r, h in enumerate(cao, start=1):
            ws.cell(r, 1, f'dòng {r}')
            ws.row_dimensions[r].height = h
        return wb, ws

    def test_chia_deu_khoang_ho_trang_truoc(self):
        from pabt import in_an
        cao = [40.0] * 30
        wb, ws = self._sheet(cao)
        khoi = [('tu_do', [(r, r) for r in range(1, 31)])]
        cap = 500.0                                     # 12 dòng một trang (480), hở 20 pt của sheet = 11 pt trên giấy
        truoc = in_an.xep_trang(ws, khoi, cap)
        self.assertEqual([(d, c) for d, c, _ in truoc], [(1, 12), (13, 24), (25, 30)])
        le = (ws.page_margins.top, ws.page_margins.bottom, ws.page_margins.left, ws.page_margins.right)
        sau = in_an.gian_khit_trang(ws, khoi, cap, None, set(range(1, 31)))
        self.assertEqual([(d, c) for d, c, _ in sau], [(d, c) for d, c, _ in truoc])       # không dòng nào đổi trang
        for d, c, dung in sau[:-1]:
            self.assertLessEqual(dung, cap)
            self.assertLessEqual(cap - dung, in_an.KHIT_CHUA + 0.2)                          # trang trước khít, chỉ chừa 2 pt
        self.assertEqual(ws.row_dimensions[30].height, 40.0)                                # trang cuối không giãn
        self.assertGreater(ws.row_dimensions[1].height, 41.0)
        self.assertEqual((ws.page_margins.top, ws.page_margins.bottom, ws.page_margins.left, ws.page_margins.right), le)
        self.assertEqual(ws.page_setup.scale, 55)
        wb.close()

    def test_ho_nho_hoac_khong_co_dong_gian_thi_giu_nguyen(self):
        from pabt import in_an
        wb, ws = self._sheet([40.0] * 30)
        khoi = [('tu_do', [(r, r) for r in range(1, 31)])]
        in_an.gian_khit_trang(ws, khoi, 490.0, None, set(range(1, 31)))                     # hở 10 pt sheet = 5,5 pt giấy: dưới ngưỡng
        self.assertEqual({ws.row_dimensions[r].height for r in range(1, 31)}, {40.0})
        in_an.gian_khit_trang(ws, khoi, 500.0, None, set())
        self.assertEqual({ws.row_dimensions[r].height for r in range(1, 31)}, {40.0})
        wb.close()

    def test_moi_dong_them_khong_qua_muc(self):
        from pabt import in_an
        wb, ws = self._sheet([100.0] * 3 + [300.0] + [100.0] * 4, ti_le=100)
        khoi = [('tu_do', [(r, r) for r in range(1, 9)])]
        sau = in_an.gian_khit_trang(ws, khoi, 400.0, None, {1, 2, 3})                       # trang 1: 3 dòng, hở 100 pt
        self.assertEqual([(d, c) for d, c, _ in sau][0], (1, 3))
        self.assertEqual({ws.row_dimensions[r].height for r in (1, 2, 3)}, {100.0 + in_an.KHIT_MOI_DONG})
        wb.close()

    def test_bang_tong_hop_giu_le_va_ty_le(self):
        from PySide6.QtWidgets import QApplication
        from pabt import csdl, du_an_moi, in_an
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to='3', so_thua=str(200 + i * 3 + j), loai_dat='CLN',
                         dt_thu_hoi=str(100 + i), vi_tri='1') for i in range(60) for j in range(1 + i % 3)]
            p = td / 'bth.pabt'
            du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                                [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
            con = csdl.mo(p)
            try:
                ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
                f = in_an.lap_bang_tong_hop(con, td / 'bth.xlsx', ds)
            finally:
                con.close()
            wb = openpyxl.load_workbook(f)
            try:
                ws = wb.worksheets[0]
                chuan = dict(in_an.LE_TRANG['tong_hop'])
                self.assertEqual({k: getattr(ws.page_margins, k) for k in ('top', 'bottom', 'left', 'right')},
                                 {k: chuan[k] for k in ('top', 'bottom', 'left', 'right')})
                self.assertEqual(ws.page_setup.scale, in_an.TI_LE_BTH)
                ngat = sorted(b.id for b in ws.row_breaks.brk)
                self.assertGreaterEqual(len(ngat), 2)
                cap, cao = in_an.cao_trang_in(ws), in_an._ham_cao(ws)
                t1, t2 = (int(x) for x in ws.print_title_rows.replace('$', '').split(':'))
                ctd = sum(cao(r) for r in range(t1, t2 + 1))
                dau = 1
                for e in ngat:                                                           # mọi trang trước trang cuối không tràn
                    dung = sum(cao(r) for r in range(dau, e + 1)) + (ctd if dau > t2 else 0)
                    self.assertLessEqual(dung, cap + 0.01)
                    dau = e + 1
            finally:
                wb.close()


if __name__ == '__main__':
    unittest.main()
