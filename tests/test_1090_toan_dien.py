"""1.0.90 - nghiệm thu: gói cài .larcgia nhập lại được, tên xã giữ dấu, bảng giá phân loại theo phụ lục, tốc độ bảng giá toàn tỉnh,
chống "database is locked", tiến độ 6 nấc, hộp con kéo giãn được. Dữ liệu tổng hợp trong thư mục máy tạm (không đụng %APPDATA%)."""
from __future__ import annotations

import ast
import json
import os
import py_compile
import shutil
import tempfile
import time
import unittest
import zipfile
from decimal import Decimal as D
from pathlib import Path

from pabt import csdl
from pabt import gia_dat_nq28 as nq
from pabt import gia_dat_qd03 as g
from pabt import goi_gia_dat as gg
from pabt import he_so_k, may_chu, quan_tri_bo, theo_doi
from pabt.cap_nhat_gia_dat import phan_tich_nghi_quyet
from pabt.lap_pa import cung_dia_ban, trung_dia_ban

GOC = Path(__file__).resolve().parents[1]
VT = ('MT', 'T1', 'T2', 'T3', 'K1', 'K2', 'K3')
TT_BH = [26100, 11800, 8300, 6000, 10200, 7400, 5300]          # NQ 28 PL III, Phường Biên Hòa, Đường Bùi Hữu Nghĩa TT 1-7 (nghìn đồng/m²)


def _bang_gia(xa, tt0, duong, dau, cuoi, gia_o, nn=(1500, 1030, 860, 670, 1030, 860, 670), tach=False, cuoi_nn=None):
    """7 dòng một đoạn. tach=True: hai dòng mỗi TT như hai phụ lục chưa gộp (điểm cuối PL I ghi khác chữ)."""
    ra = []
    for i, vt in enumerate(VT):
        goc = dict(xa=xa, tt=tt0 + i, ten_duong=duong, diem_dau=dau, diem_cuoi=cuoi, vi_tri=vt, nguong=[1000, 500])
        o = dict(dat_o=gia_o[i], tmdv=gia_o[i] * 7 // 10, sxkd=gia_o[i] * 6 // 10)
        n = dict(nn_cay=nn[i], nn_rung_nts=nn[i] * 2 // 3)
        if tach:
            ra.append(dict(goc, phu_luc=['III'], nn_cay=0, nn_rung_nts=0, **o))
            ra.append(dict(goc, diem_cuoi=cuoi_nn or cuoi, phu_luc=['I'], dat_o=0, tmdv=0, sxkd=0, **n))
        else:
            ra.append(dict(goc, **o, **n))
    return ra


def _he_so(xa, tt0, duong, dau, cuoi, k_pnn='1.19', k_nn='1.45', cuoi_nn=None, k_t1=None):
    """Phụ lục I.1 (đất ở / TMDV / SXKD) và I.2 (nông nghiệp) của QĐ 03 - I.2 có thể ghi điểm cuối khác dấu câu."""
    ra = []
    for i, vt in enumerate(VT):
        for ld in ('dat_o', 'tmdv', 'sxkd'):
            k = k_t1 if (k_t1 and vt == 'T1') else k_pnn
            ra.append(dict(dia_ban=xa, tt=tt0 + i, loai_dat=ld, vi_tri=vt, tuyen_duong=duong, diem_dau=dau, diem_cuoi=cuoi, he_so=k, ghi_chu=''))
        ra.append(dict(dia_ban=xa, tt=tt0 + i, loai_dat='nn', vi_tri=vt, tuyen_duong=duong, diem_dau=dau, diem_cuoi=cuoi_nn or cuoi, he_so=k_nn, ghi_chu=''))
    return ra


class CoMay(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1090_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        quan_tri_bo.khoa_lai_phien()
        may_chu.dang_xuat()
        self._quen()
        self.addCleanup(self._don)

    @staticmethod
    def _quen():
        gg._quen()
        he_so_k._quen()
        nq._quen()

    def _don(self):
        may_chu.dang_xuat()
        quan_tri_bo.khoa_lai_phien()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self._quen()
        shutil.rmtree(self.td, ignore_errors=True)

    def nap_du_lieu(self):
        """Năm địa bàn kiểu dữ liệu thật: Phú Lý / Tân An / Trị An / Tân Triều (I.2 ghi điểm cuối có dấu chấm -> trước tách đôi đoạn),
        Biên Hòa (hai phụ lục chưa gộp được một dòng; K1 dòng T1 khác dòng mặt tiền)."""
        gia, k = [], []
        for xa, tt0 in (('Xã Phú Lý', 71), ('Xã Tân An', 183), ('Xã Trị An', 78), ('Phường Tân Triều', 99)):
            gia += _bang_gia(xa, tt0, 'Đường tỉnh 768', 'Cầu Bà Giá (cầu 19)', f'Chân dốc lớn {xa}', [2100, 970, 850, 730, 870, 770, 660])
            gia += _bang_gia(xa, tt0 + 7, 'Đường tỉnh 768', f'Chân dốc lớn {xa}', 'Trường Cây Gáo B', [2000, 970, 790, 610, 870, 710, 550])
            k += _he_so(xa, tt0, 'Đường tỉnh 768', 'Cầu Bà Giá (cầu 19)', f'Chân dốc lớn {xa}', '1.32', cuoi_nn=f'Chân dốc lớn {xa}.')
            k += _he_so(xa, tt0 + 7, 'Đường tỉnh 768', f'Chân dốc lớn {xa}', 'Trường Cây Gáo B', '1.19', cuoi_nn='Trường Cây Gáo B.')
        gia += _bang_gia('Phường Biên Hòa', 1, 'Đường Bùi Hữu Nghĩa', 'Giáp ranh giới thành phố Hồ Chí Minh', 'Đường Nguyễn Tri Phương', TT_BH,
                         tach=True, cuoi_nn='Đường Nguyễn Tri Phương (cũ)')
        k += _he_so('Phường Biên Hòa', 1, 'Đường Bùi Hữu Nghĩa', 'Giáp ranh giới thành phố Hồ Chí Minh', 'Đường Nguyễn Tri Phương', '1.19',
                    cuoi_nn='Đường Nguyễn Tri Phương.', k_t1='1.31')
        nq.ghi_thay(gia, 'NQ 28/2025/NQ-HĐND', 'thu.docx')
        he_so_k.ghi(k, 'Quyết định số 03/2026/QĐ-UBND')
        self._quen()


class TestBienDich(unittest.TestCase):
    def test_moi_file_pabt_ast_va_py_compile(self):
        loi = []
        tam = tempfile.mkdtemp(prefix='pabt_pyc_')
        try:
            for p in sorted((GOC / 'pabt').glob('*.py')):
                try:
                    ast.parse(p.read_text(encoding='utf-8'), str(p))
                    py_compile.compile(str(p), cfile=os.path.join(tam, p.stem + '.pyc'), doraise=True)
                except (SyntaxError, py_compile.PyCompileError) as e:
                    loi.append(f'{p.name}: {e}')
        finally:
            shutil.rmtree(tam, ignore_errors=True)
        self.assertEqual(loi, [])


class TestTenXa(unittest.TestCase):
    def test_nguyen_chu_va_giu_dau(self):
        self.assertFalse(cung_dia_ban('Phường An Lộc', 'Xã Xuân Lộc'))          # trước: "an loc" là chuỗi con của "xuan loc"
        self.assertFalse(nq.khop_xa('Phường An Lộc', 'Xã Xuân Lộc'))
        self.assertFalse(he_so_k.khop_dia_ban('Xã Lộc Thành', 'Xã Lộc Thạnh'))
        self.assertTrue(trung_dia_ban('Phường Trị An', 'Xã Trị An'))
        self.assertTrue(trung_dia_ban('tri an', 'Xã Trị An'))                     # gõ không dấu
        self.assertTrue(trung_dia_ban('Phường Biên Hoà', 'Phường Biên Hòa'))      # dấu thanh đặt khác chỗ
        self.assertTrue(cung_dia_ban('Trị An', 'Bảng 53. Phường Trị An'))
        self.assertFalse(cung_dia_ban('', 'Xã Trị An'))


class TestGoiCai(CoMay):
    def test_tao_goi_tu_he_so_k_khong_trung_tt(self):
        self.nap_du_lieu()
        goi = gg.tao_goi_tu_he_so_k(gg._gan_san(), 'THU_1090', 'Thử 1.0.90', '01/01/2026')
        self.assertEqual(gg.kiem_goi(goi), [])
        tri_an = goi['dia_ban']['Xã Trị An']
        self.assertEqual([(d['tt_bat_dau'], d['tt_ket_thuc']) for d in tri_an], [(78, 84), (85, 91)])   # trước: 4 đoạn, 2 cặp trùng TT
        self.assertEqual(tri_an[0]['k1_dat_o'], '1.32')
        self.assertEqual(tri_an[0]['k1_nn_cay'], '1.45')
        bh = goi['dia_ban']['Phường Biên Hòa'][0]
        self.assertEqual(bh['k1_dat_o'], '1.19')
        self.assertEqual(bh['k1_theo_vt'], {'T1': {'k1_dat_o': '1.31', 'k1_tmdv': '1.31', 'k1_sxkd': '1.31'}})   # trước: từ chối cả gói

    def test_k1_theo_vi_tri_vao_phep_tinh(self):
        self.nap_du_lieu()
        goi = gg.tao_goi_tu_he_so_k(gg._gan_san(), 'THU_1090', 'Thử 1.0.90', '01/01/2026')
        doan = goi['dia_ban']['Phường Biên Hòa'][0]
        vt = {x['vi_tri']: x['ma'] for x in goi['vi_tri']}

        def k1(ma_vt):
            return g.tinh_don_gia(g.DauVao(dia_ban='Phường Biên Hòa', nhom_dat='DAT_O', loai_ket_noi_vi_tri=ma_vt, don_gia_bang_gia=D(1000000),
                                           cot_gia='dat_o'), doan, goi).k1
        self.assertEqual(k1(vt['MT']), D('1.19'))
        self.assertEqual(k1(vt['T1']), D('1.31'))

    def test_xuat_nhap_goi_cai_nam_xa(self):
        self.nap_du_lieu()
        xa = ['Xã Phú Lý', 'Xã Tân An', 'Phường Biên Hòa', 'Phường Tân Triều', 'Xã Trị An']
        f = gg.xuat_goi_cai(self.td / 'nam_xa.larcgia', xa)
        kq = gg.doc_goi_cai(f)
        self.assertEqual(gg.kiem_goi(kq['goi']), [])
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may_khac')
        self._quen()
        cai = gg.nhap_goi_cai(f, bo_sung=True)
        self.assertEqual(sorted(cai['xa']), sorted(xa))

    def test_goi_cu_bi_tach_doi_tu_gop_khi_nhap(self):
        """Gói .larcgia xuất từ bản 1.0.89: một đoạn thành hai bản ghi cùng tt_bat_dau (nửa K1 phi NN, nửa K1 NN)."""
        self.nap_du_lieu()
        f = Path(gg.xuat_goi_cai(self.td / 'cu.larcgia', ['Xã Trị An']))
        with zipfile.ZipFile(f) as z:
            tep = {n: z.read(n) for n in z.namelist()}
        goi = json.loads(tep['goi.json'].decode('utf-8'))
        d = goi['dia_ban']['Xã Trị An'][0]
        nua_nn = {k: v for k, v in d.items() if not (k.startswith('k1_') and k not in ('k1_nn_cay', 'k1_nn_rung_nts'))}
        nua_pnn = {k: v for k, v in d.items() if k not in ('k1_nn_cay', 'k1_nn_rung_nts')}
        nua_nn['diem_cuoi'] += '.'
        nua_nn['ma_doan_duong'] = 'XA_TRI_AN_DOAN_02'
        goi['dia_ban']['Xã Trị An'] = [nua_pnn, nua_nn] + goi['dia_ban']['Xã Trị An'][1:]
        self.assertTrue(any('tăng dần' in x or 'tách đôi' in x for x in gg.kiem_goi(goi)))
        tep['goi.json'] = json.dumps(goi, ensure_ascii=False).encode('utf-8')
        mo = json.loads(tep['mo_ta.json'].decode('utf-8'))       # gói của bản 1.0.89 chưa có mã băm từng phần (thêm ở 1.1.03)
        mo.pop('niem_phong', None)
        tep['mo_ta.json'] = json.dumps(mo, ensure_ascii=False).encode('utf-8')
        cu = self.td / 'cu_1089.larcgia'
        with zipfile.ZipFile(cu, 'w') as z:
            for n, b in tep.items():
                z.writestr(n, b)
        kq = gg.doc_goi_cai(cu)                                   # trước: LoiGoi "số TT phải tăng dần"
        ds = kq['goi']['dia_ban']['Xã Trị An']
        self.assertEqual(len(ds), 2)
        self.assertEqual((ds[0]['k1_dat_o'], ds[0]['k1_nn_cay'], ds[0]['ma_doan_duong']), (d['k1_dat_o'], d['k1_nn_cay'], d['ma_doan_duong']))

    def test_hai_tuyen_cung_tt_van_hop_le(self):
        """Bảng con đánh số chồng nhau (Long Bình TT 99: Xa lộ Hà Nội và Điểu Xiển) là hai đoạn hợp lệ."""
        goi = gg.tao_goi_tu(gg._gan_san(), 'HAI_TUYEN', 'Hai tuyến', '01/01/2026')
        mau = next(iter(goi['dia_ban'].values()))[0]
        a = dict(mau, ma_doan_duong='LB_01', tt_bat_dau=99, tt_ket_thuc=105, ten_duong='Xa lộ Hà Nội')
        b = dict(mau, ma_doan_duong='LB_02', tt_bat_dau=99, tt_ket_thuc=105, ten_duong='Đường Điểu Xiển')
        goi['dia_ban'] = {'Phường Long Bình': [a, b]}
        self.assertEqual(gg.kiem_goi(goi), [])


class TestBangGiaTheoPhuLuc(CoMay):
    def test_gia_dat_o_bien_hoa_khong_ve_0(self):
        self.nap_du_lieu()
        doan = g.ds_doan('Phường Biên Hòa')
        self.assertEqual(len(doan), 1)                           # hai phụ lục cùng TT -> một đoạn, không hai đoạn trùng TT
        goi = gg._gan_san()
        mt = goi['vi_tri'][0]['ma']
        self.assertEqual(g.gia_bang_gia('Phường Biên Hòa', doan[0], 'DAT_O', mt, 'dat_o'), D(26100000))
        self.assertEqual(g.gia_bang_gia('Phường Biên Hòa', doan[0], 'DAT_NONG_NGHIEP', mt, 'nn_cay'), D(1500000))
        self.assertEqual(nq.phu_luc_cua_cot('dat_o'), 'III')
        self.assertEqual(nq.phu_luc_cua_cot('nn_cay'), 'I')

    def test_doc_nghi_quyet_phan_loai_phu_luc(self):
        hd_i = ['TT', 'Tên đường giao thông', 'Điểm đầu', 'Điểm cuối', 'Giá đất trồng cây lâu năm, đất trồng cây hằng năm',
                'Giá đất rừng sản xuất, đất nuôi trồng thủy sản']
        hd_iii = ['TT', 'Tên đường giao thông', 'Điểm đầu', 'Điểm cuối', 'Giá đất ở', 'Giá đất thương mại, dịch vụ',
                  'Giá đất cơ sở sản xuất phi nông nghiệp']
        t = 'Các tuyến đường giao thông đấu nối trực tiếp ra đường'
        kk = 'Các tuyến đường giao thông không đấu nối trực tiếp và thông ra đường'

        def doan(tt0, ten, dau, cuoi, gia, bo_mt=False):
            ra = [] if bo_mt else [[str(tt0), ten, dau, cuoi] + gia[0]]
            ra += [[str(tt0 + i), t if i <= 3 else kk] + gia[i] for i in range(1, 7)]
            return ra
        nn = [['1.500', '970']] + [['1.030', '680']] * 6
        o = [['26.100', '18.300', '15.700']] + [['11.800', '8.300', '7.100']] * 6
        rows = [['Phụ lục I'], ['1. Phường Thử'], hd_i]
        rows += doan(1, 'Đường A', 'Đầu A', 'Cuối A', nn)
        rows += doan(8, 'Đường B', 'Đầu B', 'Cuối B', nn)
        rows += doan(15, 'Đường C', 'Đầu C', 'Cuối C', nn, bo_mt=True)            # văn bản thiếu dòng mặt tiền TT 15 ở PL I
        rows += [['Phụ lục II'], ['TT', 'Tên các đảo, cù lao', 'Địa điểm', 'Giá đất'], ['2', 'Cù lao X', 'Phường Thử', '370', '2.000', '1.400', '1.200']]
        rows += [['Phụ lục III'], ['1. Phường Thử'], hd_iii]
        rows += doan(1, 'Đường A', 'Đầu A', 'Cuối A.', o)
        rows += [['8', '', 'Đầu B', 'Cuối B', '7,200', '5.000', '4,300']]        # ô Tên đường bỏ trống, phẩy ngăn nghìn
        rows += [[str(8 + i), t if i <= 3 else kk] + o[i] for i in range(1, 7)]
        rows += doan(15, 'Đường C', 'Đầu C', 'Cuối C', o)
        rows += [['22', 'Đường D', 'Đầu D', 'Cuối D', '5Io', '360', '310']]       # ô lỗi không đọc: để trống, không dồn cột
        ds = phan_tich_nghi_quyet(rows)
        theo = {(r['tt'], r['vi_tri']): r for r in ds}
        self.assertFalse(any('Cù lao' in r['ten_duong'] for r in ds))            # Phụ lục II không lẫn vào bảng đường
        self.assertEqual(len([r for r in ds if r['tt'] == 1]), 1)                 # PL I + PL III gộp một dòng
        self.assertEqual(theo[(1, 'MT')]['phu_luc'], ['I', 'III'])
        b = theo[(8, 'MT')]
        self.assertEqual((b['ten_duong'], b['dat_o'], b['tmdv'], b['sxkd'], b['nn_cay']), ('Đường B', 7200, 5000, 4300, 1500))
        c = theo[(16, 'T1')]
        self.assertEqual((c['ten_duong'], c['diem_dau'], c['nn_cay'], c['dat_o']), ('Đường C', 'Đầu C', 1030, 11800))
        d = theo[(22, 'MT')]
        self.assertEqual((d['dat_o'], d['tmdv'], d['sxkd']), (0, 360, 310))


class TestTocDo(CoMay):
    def test_bang_gia_toan_tinh_duoi_nua_giay(self):
        """94 xã x 25 đoạn x 7 vị trí (~16.450 dòng như bảng toàn tỉnh): 95 lần dựng đoạn + 200 lần tra giá < 0,5 giây."""
        gia = []
        for x in range(94):
            for s in range(25):
                gia += _bang_gia(f'Xã Thử Số {x:02d}', 1 + 7 * s, f'Đường {s}', f'Đầu {s}', f'Cuối {s}', [2100, 970, 850, 730, 870, 770, 660])
        gia += _bang_gia('Phường Biên Hòa', 1, 'Đường Bùi Hữu Nghĩa', 'Giáp ranh giới thành phố Hồ Chí Minh', 'Đường Nguyễn Tri Phương', TT_BH,
                         tach=True, cuoi_nn='Đường Nguyễn Tri Phương (cũ)')
        nq.ghi_thay(gia, 'NQ 28/2025/NQ-HĐND', 'toan_tinh.docx')
        self._quen()
        nq.tat_ca()                                              # đọc file JSON (không tính vào thời gian tra)
        goi = gg._gan_san()
        mt = goi['vi_tri'][0]['ma']
        t = time.perf_counter()
        xa = nq.ds_xa()
        for x in xa:
            g.doan_tu_bang_gia(x)
        doan_bh = g.ds_doan('Phường Biên Hòa')[0]
        for i in range(200):
            gia_bh = g.gia_bang_gia('Phường Biên Hòa', doan_bh, 'DAT_O', mt, 'dat_o')
        tong = time.perf_counter() - t
        self.assertEqual(len(xa), 95)
        self.assertEqual(gia_bh, D(26100000))
        self.assertLess(tong, 0.5, f'{tong:.3f} s')


class TestKhoaSqlite(unittest.TestCase):
    def test_truncate_cho_khoa_va_giai_phong(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.pabt'
            con = csdl.mo(p, tao=True)
            try:
                self.assertEqual(con.execute('PRAGMA journal_mode').fetchone()[0].lower(), 'delete')    # không TRUNCATE: xem test dưới
                self.assertEqual(con.execute('PRAGMA busy_timeout').fetchone()[0], 30000)
                con.execute("UPDATE du_an SET ten_dia_ban = 'Xã Trị An' WHERE id = 1")
                self.assertTrue(con.in_transaction)
                with csdl.giao_dich(con):                        # đang trong giao_dich: không đụng
                    csdl.giai_phong_khoa_treo(con)
                    self.assertTrue(con.in_transaction)
                csdl.giai_phong_khoa_treo(con)
                self.assertFalse(con.in_transaction)
                self.assertFalse(csdl.journal_do_dang(p))           # file -journal 0 byte không phải giao dịch dở
            finally:
                con.close()
            Path(str(p) + '-journal').write_bytes(b'x' * 512)
            self.assertTrue(csdl.journal_do_dang(p))

    def test_ket_noi_khac_ghi_khong_loi_dia(self):
        """Máy / kết nối khác (chế độ DELETE mặc định) ghi trong lúc dự án đang mở: không 'disk I/O error' (lỗi khi thử TRUNCATE)."""
        import sqlite3
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'b.pabt'
            con = csdl.mo(p, tao=True)
            try:
                with csdl.giao_dich(con):
                    con.execute("UPDATE du_an SET ten_dia_ban = 'A' WHERE id = 1")
                khac = sqlite3.connect(str(p))
                with khac:
                    khac.execute("UPDATE du_an SET ten_dia_ban = 'B' WHERE id = 1")
                khac.close()
                self.assertEqual(con.execute('SELECT ten_dia_ban FROM du_an').fetchone()[0], 'B')
            finally:
                con.close()


class TestTienDoVaHop(unittest.TestCase):
    def test_gan_dot_niem_yet_khi_chua_lap(self):
        x = theo_doi.TongHopHo(**{**_tong_hop_mac_dinh(), 'da_lap': False, 'tong_pa': 0, 'da_niem_yet': True})
        td = theo_doi.phan_tich_tien_do(x)
        self.assertFalse(td.da_lap)
        self.assertEqual(td.nac, 0)
        self.assertIn('chưa lập phương án', td.canh_bao)

    def test_vua_man_hinh_khong_khoa_co(self):
        from PySide6.QtWidgets import QDialog
        from pabt.giao_dien import vua_man_hinh
        w = QDialog()
        try:
            w.resize(320, 200)
            vua_man_hinh(w)
            self.assertGreater(w.maximumWidth(), w.width())
            self.assertGreater(w.maximumHeight(), w.height())
        finally:
            w.deleteLater()


def _tong_hop_mac_dinh() -> dict:
    return dict(ma_ho=1, thu_tu=1, ho_ten='Hộ thử', dia_chi='', thua=[], qd=[])


if __name__ == '__main__':
    unittest.main()
