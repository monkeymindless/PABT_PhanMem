"""Hệ số K (QĐ 03/2026/QĐ-UBND): phân tích văn bản, tra cứu, lưu trên máy, liên kết mục Đất / hỗ trợ đào tạo, cửa sổ Bảng giá đất.
MỌI hệ số trong bài là số GIẢ LẬP (không phải số liệu của văn bản thật). Nhận dạng chữ giả lập bằng chữ (không cần Tesseract / mạng)."""
from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from pabt import he_so_k as hk


class _ThuMucMay(unittest.TestCase):
    """Thư mục máy riêng: file he_so_k.json không lọt sang bài kiểm thử khác (tự lập phương án sẽ nhân K)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)                                       # cleanup chạy ngược: đóng kết nối trước
        vao = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': self.td.name})
        vao.start()
        self.addCleanup(vao.stop)


class TestPhanTich(unittest.TestCase):
    def test_bang_moi_cot_mot_loai_dat(self):
        o = [['STT', 'Địa bàn', 'Vị trí', 'Đất ở', 'Đất thương mại, dịch vụ', 'Đất nông nghiệp'],
             ['1', 'Xã Mẫu A', 'Vị trí 1', '1,2', '1,1', '1,05'],
             ['2', 'Phường Mẫu B', 'K1', '1,15', '1,1', '1,0']]
        d = hk.phan_tich(o)
        self.assertEqual(len(d), 6)
        self.assertEqual(d[0], dict(dia_ban='Xã Mẫu A', tt='', loai_dat='dat_o', vi_tri='VT1', tuyen_duong='', diem_dau='', diem_cuoi='',
                                    he_so='1.2', ghi_chu=''))
        self.assertEqual((d[5]['dia_ban'], d[5]['loai_dat'], d[5]['vi_tri'], d[5]['he_so']), ('Phường Mẫu B', 'nn', 'K1', '1'))

    def test_tieu_de_hai_tang_va_tieu_de_xa(self):
        o = [['TT', 'Tuyến đường', 'Hệ số K', ''], ['', '', 'Đất ở', 'Đất nông nghiệp'],
             ['I', 'Xã Mẫu C', '', ''], ['1', 'Đường thử số 1', '1,3', '1,1'], ['2', 'Đường thử số 2', '1,25', '']]
        d = hk.phan_tich(o)
        self.assertEqual([(r['dia_ban'], r['tuyen_duong'], r['loai_dat'], r['he_so']) for r in d],
                         [('Xã Mẫu C', 'Đường thử số 1', 'dat_o', '1.3'), ('Xã Mẫu C', 'Đường thử số 1', 'nn', '1.1'),
                          ('Xã Mẫu C', 'Đường thử số 2', 'dat_o', '1.25')])

    def test_chu_thuong_ocr(self):
        chu = ('QUYẾT ĐỊNH Số: 03/2026/QĐ-UBND\n1. Xã Mẫu D\na) Đất ở\nVị trí 1: hệ số 1,25\nVị trí 2: hệ số 1.2\n'
               'b) Đất nông nghiệp: 1,1\nGiá bảng giá 1.500.000 đồng/m2\n2. Phường Mẫu E\nĐất ở  T1  1,4\n')
        d, vb = hk.doc_chu(chu)
        self.assertEqual(vb, 'Quyết định số 03/2026/QĐ-UBND')
        self.assertEqual([(r['dia_ban'], r['loai_dat'], r['vi_tri'], r['he_so']) for r in d],
                         [('Xã Mẫu D', 'dat_o', 'VT1', '1.25'), ('Xã Mẫu D', 'dat_o', 'VT2', '1.2'), ('Xã Mẫu D', 'nn', '', '1.1'),
                          ('Phường Mẫu E', 'dat_o', 'T1', '1.4')])

    def test_doc_he_so_va_chuan(self):
        self.assertEqual([hk.doc_he_so(x) for x in ('1,2', '1.20', '1,15 lần', '0', '2026', '1.500.000', '', 1.3)],
                         ['1.2', '1.2', '1.15', '', '', '', '', '1.3'])
        self.assertEqual(hk.chuan_vi_tri('Đường đấu nối trực tiếp - mức 2 Đường X (đoạn …)'), 'T2')
        self.assertEqual(hk.chuan_vi_tri('Mặt tiền Đường X'), 'MT')
        self.assertEqual(hk.chuan_vi_tri('1'), 'VT1')
        self.assertEqual(hk.chuan_loai_dat('ONT, ODT'), 'ONT,ODT')
        self.assertEqual(hk.nhom_tu_chu('Đất trồng cây lâu năm'), 'nn_cay')


class TestTraCuu(unittest.TestCase):
    DS = [hk.chuan_dong(r) for r in (
        dict(he_so='1.05'), dict(dia_ban='Xã Mẫu A', loai_dat='nn', he_so='1.1'),
        dict(dia_ban='Xã Mẫu A', loai_dat='dat_o', vi_tri='VT1', he_so='1.2'),
        dict(dia_ban='Xã Mẫu A', loai_dat='dat_o', vi_tri='MT', tuyen_duong='Đường thử', he_so='1.5'),
        dict(dia_ban='Xã Mẫu A', loai_dat='ONT', vi_tri='T1', he_so='1.3'),
        # dòng theo TT bảng giá (mẫu Phụ lục I): tra theo TT, hoặc theo chữ vị trí có đủ tên đường + đoạn
        dict(dia_ban='Phường Mẫu B', tt=7, loai_dat='dat_o', vi_tri='K1', tuyen_duong='Đường Một', diem_dau='Cầu A', diem_cuoi='Chợ B',
             he_so='1.33'),
        dict(dia_ban='Phường Mẫu B', tt=7, loai_dat='nn', vi_tri='K1', tuyen_duong='Đường Một', diem_dau='Cầu A', diem_cuoi='Chợ B',
             he_so='1.44'))]

    def test_dong_cu_the_nhat(self):
        self.assertEqual(hk.tra('Mẫu A', 'ONT', '1', ds=self.DS)[0], Decimal('1.2'))
        self.assertEqual(hk.tra('Xã Mẫu A', 'CLN', '2', ds=self.DS)[0], Decimal('1.1'))      # nhóm chung 'nn'
        self.assertEqual(hk.tra('Xã Mẫu A', 'ONT', 'Mặt tiền Đường thử (đoạn từ A đến B)', ds=self.DS)[0], Decimal('1.5'))
        self.assertEqual(hk.tra('Xã Mẫu A', 'ONT', 'T1', ds=self.DS)[0], Decimal('1.3'))       # mã loại đất
        self.assertEqual(hk.tra('Xã Khác', 'ONT', '1', ds=self.DS)[0], Decimal('1.05'))        # dòng toàn tỉnh
        self.assertEqual(hk.tra('Xã Mẫu A', 'ONT', '1', ds=[])[0], None)

    def test_dong_theo_tt(self):
        self.assertEqual(hk.tra('Xã Mẫu B', 'ODT', 'K1', 'Đường Một', ds=self.DS, tt=7)[0], Decimal('1.33'))
        self.assertEqual(hk.tra('Xã Mẫu B', 'RPH', '', ds=self.DS, tt='7')[0], Decimal('1.44'))   # rừng phòng hộ = nhóm NN
        mo_ta = 'Đường không đấu nối trực tiếp - mức 1 Đường Một (đoạn từ Cầu A đến Chợ B)'
        self.assertEqual(hk.tra('Mẫu B', 'CLN', mo_ta, ds=self.DS)[0], Decimal('1.44'))
        self.assertEqual(hk.tra('Xã Khác', 'ONT', mo_ta, ds=self.DS)[0], Decimal('1.33'))       # thửa ở xã khác của dự án
        self.assertEqual(hk.tra('Mẫu B', 'ONT', mo_ta.replace('Chợ B', 'Chợ C'), ds=self.DS)[0], Decimal('1.05'))   # khác đoạn
        self.assertEqual(hk.nhom_cho_ma('OTC'), 'dat_o')
        self.assertEqual(hk.nhom_cho_ma('DGD'), 'sxkd')                                          # PNN còn lại (Phụ lục I.3)
        self.assertEqual(hk.nhom_cho_ma('CQP'), '')


class TestPhuLuc(unittest.TestCase):
    # chữ GIẢ LẬP theo bố cục Phụ lục I (tên đường, hệ số không phải số liệu văn bản)
    PNN = ('12\n \nBảng 3. Phường Mẫu B \nTT Tên đường giao thông Điểm đầu Điểm cuối \nHệ số điều \nchỉnh mức \nthị trường \nđất ở \n'
           'Hệ số điều chỉnh \nđất thương \nmại dịch vụ \nđất cơ sở sản xuất \n'
           '1 Đường Một Khu tái định cư 3,8 \nha Chợ B 1,31 1,31 1,32 \n2 \nCác tuyến đường giao thông đấu nối trực tiếp ra Đường Một '
           'đoạn từ \nCầu A đến Chợ B có hiện trạng là đường nhựa: \n- Có bề rộng ≥5m, cách đường giao thông ≤1.000m. \n1,21 1,21 1,21 \n'
           '3 \nCác tuyến đường giao thông không đấu nối trực tiếp và thông ra Đường Một đoạn từ Cầu A đến Chợ B có hiện trạng: \n'
           '1,11 \n1,11 1,11 \nBảng 4. Xã Không Lấy \nTT Tên đường \nđất ở thương mại \n1 Đường X A B 1,99 1,99 1,99 \n')
    NN = ('Bảng 3. Phường Mẫu B \nHệ số điều chỉnh mức biến \nđộng thị trường đất nông \nnghiệp (đất trồng lâu năm) \n'
          '1 Đường Một A B 1,41 \n2 \nCác tuyến đường giao thông đấu nối trực tiếp ra Đường Một đoạn từ Cầu A đến Chợ B có hiện trạng \n'
          '1,42 \n3 \nCác tuyến đường giao thông không đấu nối trực tiếp và thông ra Đường Một đoạn từ Cầu A đến Chợ B có hiện trạng \n'
          '1,43 \n')

    def test_doc_va_noi_bang_gia(self):
        self.assertTrue(hk.la_phu_luc([self.PNN]))
        d, cb = hk.doc_phu_luc([self.PNN, self.NN], ['Mẫu B'])
        self.assertEqual(cb, [])
        k = {(r['tt'], r['loai_dat']): r['he_so'] for r in d}
        self.assertEqual(k, {(1, 'dat_o'): '1.31', (1, 'tmdv'): '1.31', (1, 'sxkd'): '1.32', (2, 'dat_o'): '1.21', (2, 'tmdv'): '1.21',
                             (2, 'sxkd'): '1.21', (3, 'dat_o'): '1.11', (3, 'tmdv'): '1.11', (3, 'sxkd'): '1.11', (1, 'nn'): '1.41',
                             (2, 'nn'): '1.42', (3, 'nn'): '1.43'})                # "3,8 ha" trong tên đoạn không phải hệ số
        self.assertEqual([r['vi_tri'] for r in d if r['loai_dat'] == 'nn'], ['MT', 'T1', 'K1'])
        self.assertEqual(d[0]['tuyen_duong'], 'Đường Một')                         # mặt tiền lấy tên đường theo dòng T1
        bg = [dict(xa='Xã Mẫu B', tt=t, vi_tri=v, ten_duong='Đường Một', diem_dau='Cầu A', diem_cuoi='Chợ B')
              for t, v in ((1, 'MT'), (2, 'T1'), (3, 'K1'), (4, 'K2'))]
        d, cb = hk.noi_bang_gia(d, bg)
        self.assertEqual({r['dia_ban'] for r in d}, {'Xã Mẫu B'})
        self.assertTrue(any('1 TT' in c and '(4)' in c for c in cb), cb)           # TT 4 của bảng giá chưa có hệ số

    def test_bang_gan_san_khop_bang_gia(self):
        from pabt import gia_dat_nq28 as nq
        with mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': tempfile.mkdtemp()}):
            ds = hk.tat_ca()
            self.assertFalse(hk.dang_thay())
        bg = {(r['xa'], r['tt']): r for r in nq.tat_ca()}
        nhom = {}
        for r in ds:
            g = bg[(r['dia_ban'], r['tt'])]                                         # mọi dòng ứng đúng một dòng bảng giá
            self.assertEqual((r['vi_tri'], r['tuyen_duong']), (g['vi_tri'], g['ten_duong']))
            nhom.setdefault((r['dia_ban'], r['tt']), set()).add(r['loai_dat'])
        self.assertEqual(set(nhom), set(bg))                                        # đủ mọi TT của 4 địa bàn
        self.assertEqual({frozenset(x) for x in nhom.values()}, {frozenset({'dat_o', 'tmdv', 'sxkd', 'nn'})})
        r = ds[0]
        self.assertEqual(hk.tra(r['dia_ban'], 'ONT', r['vi_tri'], r['tuyen_duong'], ds=ds, tt=r['tt'])[1]['tt'], r['tt'])


class TestLuuVaDocFile(_ThuMucMay):
    def test_ghi_doc_xoa(self):
        self.assertFalse(hk.dang_thay())                                       # bảng gắn sẵn
        p = hk.ghi([dict(dia_ban='Xã Mẫu A', loai_dat='Đất ở', vi_tri='Vị trí 1', he_so='1,2'), dict(he_so='abc')])
        self.assertTrue(p.is_file())
        self.assertEqual(len(hk.tat_ca()), 1)                                  # dòng hệ số sai bị bỏ
        self.assertEqual(hk.tra('Mẫu A', 'ODT', '1')[0], Decimal('1.2'))
        self.assertEqual(hk.can_cu(), 'Hệ số K theo QĐ 03/2026/QĐ-UBND')
        with self.assertRaises(hk.LoiHeSoK):
            hk.ghi([dict(he_so='0')])
        self.assertTrue(hk.xoa())
        self.assertFalse(hk.dang_thay())
        self.assertTrue(hk.co_du_lieu())                                       # xóa bảng đã nhập = dùng lại bảng gắn sẵn

    def test_doc_excel(self):
        import openpyxl
        f = Path(self.td.name) / 'k.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        for r in (['Quyết định số 03/2026/QĐ-UBND'], ['STT', 'Xã, phường', 'Loại đất', 'Vị trí', 'Hệ số K'],
                  [1, 'Xã Mẫu A', 'Đất ở', 'Vị trí 1', 1.2], [2, 'Xã Mẫu A', 'Đất rừng sản xuất', '', '1,1']):
            ws.append(r)
        wb.save(f)
        d, vb, _ = hk.doc_file(f)
        self.assertEqual(vb, 'Quyết định số 03/2026/QĐ-UBND')
        self.assertEqual([(r['loai_dat'], r['vi_tri'], r['he_so']) for r in d], [('dat_o', 'VT1', '1.2'), ('nn_rung_nts', '', '1.1')])

    def test_doc_anh_qua_ocr_gia_lap(self):
        f = Path(self.td.name) / 'qd.png'
        f.write_bytes(b'')
        trang = ['Số: 03/2026/QĐ-UBND\nXã Mẫu A\nĐất ở  Vị trí 1  1,2\n', 'Đất nông nghiệp  1,O5\n']
        with mock.patch('pabt.ocr.tung_trang', lambda *a, **k: iter(trang)):
            d, vb, cach = hk.doc_file(f, 'Mẫu A')
        self.assertIn('Nhận dạng', cach)
        self.assertEqual([(r['dia_ban'], r['loai_dat'], r['he_so']) for r in d], [('Xã Mẫu A', 'dat_o', '1.2'), ('Xã Mẫu A', 'nn', '1.05')])
        with mock.patch('pabt.ocr.tung_trang', lambda *a, **k: iter(['Không có bảng nào'])):
            with self.assertRaises(hk.LoiHeSoK):
                hk.doc_file(f)


class TestLienKetPhuongAn(_ThuMucMay):
    def test_muc_dat_va_ho_tro_dao_tao(self):
        from pabt import csdl, lap_pa, nghiep_vu
        from tests.test_toc_do import _du_an
        p = _du_an(Path(self.td.name), 3)                                     # tạo trước khi có hệ số K (tự lập K = 1)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        hk.ghi([dict(dia_ban='Bàu Hàm', loai_dat='dat_o', vi_tri='VT1', he_so='1,2'),
                dict(dia_ban='Bàu Hàm', loai_dat='nn', he_so='1,5')])
        ma_ho = con.execute("SELECT ma_ho FROM thua WHERE loai_dat = 'CLN' LIMIT 1").fetchone()[0]
        bo = lap_pa.BoSoan(con, ma_ho)
        bo.pa.dat.clear()
        for (ma_thua,) in con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ?', (ma_ho,)).fetchall():
            _, tb = bo.them_thua(ma_thua)
        cln = next(d for d in bo.pa.dat if d.loai_dat == 'CLN')
        self.assertEqual(cln.he_so_k, Decimal('1.5'))
        self.assertIn('Hệ số K theo QĐ 03/2026/QĐ-UBND', cln.ghi_chu)
        # hỗ trợ đào tạo: giá đất NN đã nhân K
        import copy
        sl, dg = nghiep_vu.de_xuat_dao_tao_pa(bo.pa, bo.bc)
        pa1 = copy.deepcopy(bo.pa)
        for d in pa1.dat:
            d.he_so_k = Decimal(1)
        sl1, dg1 = nghiep_vu.de_xuat_dao_tao_pa(pa1, bo.bc)
        self.assertEqual(sl, sl1)
        self.assertLessEqual(abs(dg - dg1 * Decimal('1.5')), 1)
        from pabt import chinh_sach
        self.assertEqual(chinh_sach.ds_thua_nn(bo)[0]['don_gia'], Decimal('375000'))
        # đổi sang loại đất không có hệ số: bỏ căn cứ, hệ số về 1
        i = bo.pa.dat.index(cln)
        hk.ghi([dict(dia_ban='Bàu Hàm', loai_dat='dat_o', vi_tri='VT1', he_so='1,2')])
        bo.sua_dat(i, 'vi_tri', '1')
        self.assertEqual(cln.he_so_k, Decimal(1))
        self.assertNotIn('Hệ số K', cln.ghi_chu)

    def test_chon_vi_tri_nq28(self):
        from pabt import csdl, gia_dat_nq28 as nq, lap_pa
        from tests.test_toc_do import _du_an
        p = _du_an(Path(self.td.name), 1)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        r = next(x for x in nq.tat_ca() if x['vi_tri'] == 'T1')
        hk.ghi([dict(dia_ban=r['xa'], loai_dat='dat_o', vi_tri='T1', tuyen_duong=r['ten_duong'], he_so='1,3')])
        bo = lap_pa.BoSoan(con, 1)
        i = next(k for k, d in enumerate(bo.pa.dat) if d.loai_dat == 'ONT')
        tb = bo.chon_vi_tri_nq28(i, r)
        self.assertEqual(bo.pa.dat[i].he_so_k, Decimal('1.3'))
        self.assertIn('Hệ số K = 1,3', tb)


class TestCuaSo(_ThuMucMay):
    def test_hai_the_va_nhap_chu(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest('không có Qt')
        QApplication.instance() or QApplication([])
        from pabt import gia_dat_nq28 as nq
        from pabt.man_hinh_du_toan import HopTraNQ28
        d = HopTraNQ28(None, nq.ds_xa()[0], xem=True, the=1)
        self.addCleanup(d.deleteLater)
        self.assertEqual([d.tabs.tabText(i) for i in range(2)], ['Bảng giá đất 2026', 'Hệ số K (QĐ 03/2026/QĐ-UBND)'])
        k = d.khung_k
        k.im_lang = True
        xa = nq.ds_xa()[0]
        d.cb_cot.setCurrentIndex(0)                                            # Đất ở
        d.loc()
        gan_san = d.bang.item(0, 6).text()
        self.assertTrue(gan_san, xa)                                           # bảng gắn sẵn có hệ số cho dòng đầu
        n = len(hk.tat_ca())
        self.assertTrue(k.dan_chu('Xã Mẫu Z\nĐất ở  1,2\n'))                  # dán: thêm vào bảng đang có
        self.assertEqual(k.bang.rowCount(), n + 1)
        self.assertTrue(k.chua_luu)
        self.assertTrue(k.luu())
        self.assertTrue(hk.dang_thay())
        self.assertEqual(hk.tra('Mẫu Z', 'ONT', '')[0], Decimal('1.2'))
        self.assertTrue(k.bo_het(True))
        self.assertFalse(hk.dang_thay())
        d.loc()
        self.assertEqual(d.bang.item(0, 6).text(), gan_san)
        d.close()


if __name__ == '__main__':
    unittest.main()
