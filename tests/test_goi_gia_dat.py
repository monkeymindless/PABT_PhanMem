"""Bộ quy tắc giá đất (1.0.64): gói dữ liệu thay cho quy tắc viết trong mã. Đáp án vàng chụp từ bản viết cố định (3.061 ca trên lưới 254.016 tổ hợp, gồm cả câu giải trình): gói gắn sẵn phải ra y hệt.
Quy định đổi -> gói mới: đổi hệ số, thêm hệ số, đổi làm tròn, hiệu lực, thêm xã; số cũ không tự đổi; một nguồn K."""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

from pabt import csdl
from pabt import dong_bo_don_gia as db
from pabt import gia_dat_qd03 as g
from pabt import goi_gia_dat as gg
from pabt import he_so_k, may_chu, phien_ban_pa as pb, quan_tri_bo
from pabt.lap_pa import BoSoan
from pabt.nghiep_vu import doc_phuong_an
from pabt.quan_tri_bo import LoiQuyenBoDonGia

from tests import APP

DOAN_TRI_AN = 'Bảng 53. Phường Trị An'


def cac_ca(buoc=83):
    doan = []
    for k in g.ds_dia_ban():
        ds = g.ds_doan(k)
        doan += [(k, ds[0]['ma_doan_duong']), (k, ds[len(ds) // 2]['ma_doan_duong'])]
    doan.append(('', ''))
    luoi = itertools.product(doan, ('0', '1', '999', '1001', '470000', '730000', '1234567', '10000000', '33333.33'), ('DAT_NONG_NGHIEP', 'DAT_O', 'DAT_TMDV', 'DAT_SXKD_KHOANGSAN'),
                             ('NHUA_BETONG', 'DAT_SOI_DA_CAPPHOI'),
                             ((), ('PNN_TTTM_200M',), ('PNN_NGHIATRANG_100M',), ('PNN_HANHLANG_50M',), ('PNN_TTTM_200M', 'PNN_NGHIATRANG_100M', 'PNN_HANHLANG_50M'), ('NN_DUONG_DAT_SOI_DA',), ('PNN_TTTM_200M', 'NN_DUONG_DAT_SOI_DA')),
                             ((False, '1'), (False, '1.5'), (True, '1.05'), (True, '0')), ('1', '1.1', '0'), ('0', '500000', '1000000'), (False, True))
    for i, x in enumerate(luoi):
        if i % buoc == 0:
            yield x


def ket_qua(x):
    (dia, ma_d), gia, nhom, kc, yt, (ap, k2), kh, ct, rieng = x
    doan = g.tim_doan(dia, ma_d) if ma_d else None
    v = g.DauVao(dia_ban=dia, nhom_dat=nhom, ma_doan_duong=ma_d, ket_cau_mat_duong=kc, don_gia_bang_gia=D(gia), he_so_k1=None if ma_d else D('1.3'),
                 ap_dung_quy_hoach_pl2=ap, he_so_quy_hoach_k2=D(k2), yeu_to_pl3=list(yt), he_so_khac=D(kh), gia_dat_cu_the=D(ct), co_quy_dinh_rieng_duong_dat_pl1=rieng)
    r = g.tinh_don_gia(v, doan)
    chu = '\n'.join(r.buoc_lap_luan + ['#'] + r.canh_bao + ['#', r.cong_thuc, g.ghi_chu_ap_gia(r, doan, g.ten_ngan(dia))])
    return r, hashlib.md5(chu.encode('utf-8')).hexdigest()[:10]


class CoMay(unittest.TestCase):
    """Thư mục máy riêng: không đụng %APPDATA%\\PABT, bảng hệ số K gắn sẵn."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_goi_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        quan_tri_bo.khoa_lai_phien()
        may_chu.dang_xuat()
        gg._quen()
        he_so_k._quen()
        self.addCleanup(self._don)

    def _don(self):
        may_chu.dang_xuat()
        quan_tri_bo.khoa_lai_phien()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        gg._quen()
        he_so_k._quen()
        shutil.rmtree(self.td, ignore_errors=True)

    def goi_moi(self, ma='QD15_2027', ten='QĐ 15/2027/QĐ-UBND', tu='01/01/2027'):
        return gg.tao_goi_tu(gg._gan_san(), ma, ten, tu)

    def tinh(self, goi=None, gia='1000000', nhom='DAT_NONG_NGHIEP', kc='NHUA_BETONG', **them):
        doan = g.ds_doan(DOAN_TRI_AN, goi)[0] if goi is None or DOAN_TRI_AN in goi['dia_ban'] else next(iter(goi['dia_ban'].values()))[0]
        return g.tinh_don_gia(g.DauVao(dia_ban=DOAN_TRI_AN, nhom_dat=nhom, ket_cau_mat_duong=kc, don_gia_bang_gia=D(gia), **them), doan, goi)


class TestDapAnVang(CoMay):
    def test_goi_gan_san_ra_dung_ban_viet_co_dinh(self):
        """Mọi trường số VÀ băm toàn bộ câu chữ (giải trình, cảnh báo, công thức, ghi chú dòng đất)."""
        vang = json.loads((Path(__file__).parent / 'vang_gia_dat_qd03.json').read_text(encoding='utf-8'))
        ca = list(cac_ca())
        self.assertEqual(len(ca), len(vang))
        self.assertGreater(len(ca), 3000)
        for x, dung in zip(ca, vang):
            r, bam = ket_qua(x)
            k = dung.split('|')
            self.assertEqual((r.k1, r.k2, r.k3, r.tong_he_so, r.don_gia_chua_lam_tron, r.don_gia_da_lam_tron, r.don_gia_ap_dung), tuple(D(s) for s in k[:7]), x)
            self.assertEqual(int(r.ap_dung_chuyen_tiep), int(k[7]), x)
            self.assertEqual(bam, k[8], x)

    def test_goi_gan_san_hop_le_va_khop_phu_luc(self):
        self.assertEqual(gg.kiem_goi(gg._gan_san()), [])
        pl3 = g.du_lieu()['phu_luc_III_yeu_to_anh_huong']
        dung = {r['ma']: D(str(r['he_so_k3'])) for r in pl3['dat_phi_nong_nghiep'] + pl3['dat_nong_nghiep']}
        self.assertEqual({y['ma']: D(y['he_so']) for y in gg._gan_san()['yeu_to']}, dung)

    def test_mau_cau_du_khoa(self):
        self.assertEqual(set(gg._gan_san()['cau_chu']), {k for k, _ in gg.CAU_CHU})


class TestQuyDinhDoi(CoMay):
    def test_doi_he_so_k3_chi_gia_tri_trong_goi_moi(self):
        moi = self.goi_moi()
        next(y for y in moi['yeu_to'] if y['ma'] == 'NN_DUONG_DAT_SOI_DA')['he_so'] = '0.85'
        k_goc = self.tinh(kc='DAT_SOI_DA_CAPPHOI')
        k_moi = self.tinh(moi, kc='DAT_SOI_DA_CAPPHOI')
        self.assertEqual((k_goc.k3, k_moi.k3), (D('0.90'), D('0.85')))
        self.assertEqual(k_moi.don_gia_chua_lam_tron / k_goc.don_gia_chua_lam_tron, D('0.85') / D('0.90'))
        self.assertIn('QĐ 15/2027/QĐ-UBND', g.ghi_chu_ap_gia(k_moi))
        self.assertNotIn('QĐ 03', g.ghi_chu_ap_gia(k_moi))
        self.assertEqual(next(y for y in gg._gan_san()['yeu_to'] if y['ma'] == 'NN_DUONG_DAT_SOI_DA')['he_so'], '0.90')      # chép sâu: gói gốc không bị đổi

    def test_them_he_so_k4_va_doi_lam_tron(self):
        moi = self.goi_moi()
        moi['he_so_them'] = [dict(ma='K4', ten='Hệ số vùng', mac_dinh='1.1', can_cu='Điều 5')]
        moi['cong_thuc']['he_so'].append('K4')
        moi['cong_thuc']['lam_tron'] = -3
        self.assertEqual(gg.kiem_goi(moi), [])
        goc = self.tinh(gia='1234567')
        k = self.tinh(moi, gia='1234567')
        self.assertEqual(k.don_gia_da_lam_tron % 1000, 0)
        self.assertEqual(k.don_gia_da_lam_tron, ((goc.don_gia_chua_lam_tron * D('1.1')) / 1000).quantize(D(1)) * 1000)
        self.assertIn('K4', k.cong_thuc)
        self.assertTrue(any('Hệ số vùng' in c for c in k.buoc_lap_luan))
        self.assertEqual(self.tinh(moi, gia='1234567', he_so_them={'K4': D('1.2')}).he_so_them['K4'], D('1.2'))

    def test_tat_chuyen_tiep(self):
        moi = self.goi_moi()
        moi['chuyen_tiep']['bat'] = False
        self.assertTrue(self.tinh(gia='1', gia_dat_cu_the=D(500000)).ap_dung_chuyen_tiep)
        self.assertFalse(self.tinh(moi, gia='1', gia_dat_cu_the=D(500000)).ap_dung_chuyen_tiep)

    def test_yeu_to_cho_ca_hai_nhom(self):
        moi = self.goi_moi()
        moi['yeu_to'].append(dict(ma='CA_MOI', ten='Yếu tố chung', he_so='1.2', ap_cho='ca'))
        self.assertEqual(self.tinh(moi, yeu_to_pl3=['CA_MOI']).k3, D('1.2'))
        self.assertEqual(self.tinh(moi, nhom='DAT_O', yeu_to_pl3=['CA_MOI']).k3, D('1.2'))

    def test_cau_giai_trinh_theo_so_hieu_va_khong_chay_ma(self):
        moi = self.goi_moi()
        self.assertTrue(any('QĐ 15/2027/QĐ-UBND' in c for c in self.tinh(moi).buoc_lap_luan))
        moi['cau_chu']['k2_khong'] = '{0.__class__} {so_hieu.__class__} {so_hieu}'
        self.assertIn('{0.__class__} {so_hieu.__class__} QĐ 15/2027/QĐ-UBND', self.tinh(moi).buoc_lap_luan)

    def test_doan_thieu_cot_k1_thi_canh_bao(self):
        moi = self.goi_moi()
        d = moi['dia_ban'][DOAN_TRI_AN][0]
        del d['k1_dat_o']
        k = g.tinh_don_gia(g.DauVao(dia_ban=DOAN_TRI_AN, nhom_dat='DAT_O', don_gia_bang_gia=D(1000)), d, moi)
        self.assertEqual(k.k1, 1)
        self.assertTrue(any('chưa có hệ số K1' in c for c in k.canh_bao))


class TestChonGoi(CoMay):
    def test_theo_ngay_hieu_luc(self):
        moi = self.goi_moi(tu='01/01/2027')
        gg.ghi_goi(moi)
        self.assertEqual(gg.chon_goi('2026-12-31')['ma'], gg.MA_GAN_SAN)
        self.assertEqual(gg.chon_goi('2027-01-01')['ma'], moi['ma'])
        moi = dict(moi, hieu_luc_den='2027-06-30')
        gg.ghi_goi(moi)
        self.assertEqual(gg.chon_goi('2027-07-01')['ma'], gg.MA_GAN_SAN)

    def test_du_an_giu_goi_da_ap_khi_co_goi_moi(self):
        con = csdl.tao_moi(self.td / 'a.pabt')
        self.addCleanup(con.close)
        gg.nho_goi_du_an(con, gg.MA_GAN_SAN)
        gg.ghi_goi(self.goi_moi(tu='01/06/2026'))                    # gói mới hơn gói gắn sẵn, đang hiệu lực
        self.assertEqual(gg.chon_goi()['ma'], 'QD15_2027')
        self.assertEqual(gg.goi_du_an(con)['ma'], gg.MA_GAN_SAN)
        self.assertTrue(any('gói đang hiệu lực' in c for c in gg.canh_bao_goi(gg.goi_du_an(con))))

    def test_xa_goi_chua_co_thi_canh_bao(self):
        self.assertTrue(any('chưa có địa bàn' in c for c in gg.canh_bao_goi(gg._gan_san(), 'Xã Long Thành')))
        self.assertEqual(gg.canh_bao_goi(gg._gan_san(), 'Xã Tân An'), [])


class TestKiemTraVaLuu(CoMay):
    def test_tu_choi_goi_sai(self):
        cach = {
            'he_so_am': lambda x: x['yeu_to'][0].update(he_so='-1'),
            'he_so_chu': lambda x: x['yeu_to'][0].update(he_so='abc'),
            'he_so_vo_cuc': lambda x: x['yeu_to'][0].update(he_so='Infinity'),
            'nhom_la': lambda x: x['yeu_to'][0].update(ap_cho='xyz'),
            'cong_thuc_la': lambda x: x['cong_thuc'].update(he_so=['K1', 'import os']),
            'thieu_k1': lambda x: x['cong_thuc'].update(he_so=['K2']),
            'lam_tron_la': lambda x: x['cong_thuc'].update(lam_tron='0'),
            'ma_la': lambda x: x.update(ma='../../x'),
            'ngay_la': lambda x: x.update(hieu_luc_tu='hôm nay'),
            'k1_am': lambda x: next(iter(x['dia_ban'].values()))[0].update(k1_dat_o=-2),
            'khai_ma_khong_dung': lambda x: x.update(he_so_them=[dict(ma='K9', mac_dinh='1')]),
        }
        for ten, sua in cach.items():
            moi = self.goi_moi()
            sua(moi)
            self.assertTrue(gg.kiem_goi(moi), ten)
            with self.assertRaises(gg.LoiGoi):
                gg.ghi_goi(moi)
        self.assertEqual(len(gg.ds_goi()), 1)

    def test_goi_gan_san_khong_sua_xoa_duoc(self):
        with self.assertRaises(gg.LoiGoi):
            gg.ghi_goi(copy.deepcopy(gg._gan_san()))
        with self.assertRaises(gg.LoiGoi):
            gg.xoa_goi(gg.MA_GAN_SAN)

    def test_can_quyen_quan_tri(self):
        quan_tri_bo.dat('matkhau1')
        quan_tri_bo.khoa_lai_phien()
        with self.assertRaises(LoiQuyenBoDonGia):
            gg.ghi_goi(self.goi_moi())
        self.assertEqual(len(gg.ds_goi()), 1)
        quan_tri_bo.mo_khoa_phien()
        gg.ghi_goi(self.goi_moi())
        self.assertEqual(len(gg.ds_goi()), 2)
        quan_tri_bo.khoa_lai_phien()
        with self.assertRaises(LoiQuyenBoDonGia):
            gg.xoa_goi('QD15_2027')

    def test_file_hong_van_chay_goi_gan_san(self):
        gg.file_may().parent.mkdir(parents=True, exist_ok=True)
        gg.file_may().write_text('{hỏng', encoding='utf-8')
        self.assertEqual([x['ma'] for x in gg.ds_goi()], [gg.MA_GAN_SAN])
        gg._quen()
        gg.file_may().write_text(json.dumps({'goi': [{'ma': 'x'}, 5]}), encoding='utf-8')
        self.assertEqual([x['ma'] for x in gg.ds_goi()], [gg.MA_GAN_SAN])

    def test_xuat_nhap_file_giu_nguyen(self):
        moi = self.goi_moi()
        p = self.td / 'g.json'
        gg.xuat_file_goi(moi, p)
        self.assertEqual(gg.doc_file_goi(p), moi)
        p.write_text('không phải json', encoding='utf-8')
        with self.assertRaises(gg.LoiGoi):
            gg.doc_file_goi(p)
        p.write_text(json.dumps({'ma': 'A'}), encoding='utf-8')
        with self.assertRaises(gg.LoiGoi):
            gg.doc_file_goi(p)

    def test_so_sanh_noi_ro_khac_gi(self):
        moi = self.goi_moi()
        next(y for y in moi['yeu_to'] if y['ma'] == 'PNN_TTTM_200M')['he_so'] = '1.08'
        moi['dia_ban'][DOAN_TRI_AN][0]['k1_dat_o'] = 1.99
        moi['cong_thuc']['lam_tron'] = -3
        chu = '\n'.join(gg.so_sanh(gg._gan_san(), moi))
        self.assertIn('×1,05 -> ×1,08', chu)
        self.assertIn('đổi K1 1 chỗ', chu)
        self.assertIn('Làm tròn đơn giá: 0 -> -3', chu)
        self.assertEqual(gg.so_sanh(gg._gan_san(), gg._gan_san()), [])


class TestMotNguonHeSoK(CoMay):
    def _thay_bang(self, xa='Phường Trị An', k='1.77'):
        d = g.ds_doan(DOAN_TRI_AN)[0]
        dong = [dict(dia_ban=xa, tt=d['tt_bat_dau'] + i, loai_dat=n, vi_tri=vt, tuyen_duong=d['ten_duong'], diem_dau=d['diem_dau'], diem_cuoi=d['diem_cuoi'], he_so=k, ghi_chu='')
                for i, vt in enumerate(('MT', 'T1', 'T2', 'T3', 'K1', 'K2', 'K3')) for n in ('dat_o', 'tmdv', 'sxkd', 'nn_cay', 'nn_rung_nts')]
        he_so_k.ghi(dong, 'Quyết định số 15/2027/QĐ-UBND')
        return d

    def test_bang_da_nhap_thang_du_lieu_goi_gan_san_va_ghi_ro(self):
        d = self._thay_bang()
        k = self.tinh()
        self.assertEqual(k.k1, D('1.77'))
        self.assertEqual(k.nguon_k1, 'QĐ 15/2027/QĐ-UBND')
        self.assertTrue(any('15/2027' in c and '1,77' in c for c in k.buoc_lap_luan))
        # đoạn không có trong bảng đã nhập: giữ K1 của gói, cảnh báo, không âm thầm
        d2 = g.ds_doan(DOAN_TRI_AN)[1]
        k2 = g.tinh_don_gia(g.DauVao(dia_ban=DOAN_TRI_AN, nhom_dat='DAT_O', don_gia_bang_gia=D(1000)), d2)
        self.assertEqual(k2.k1, D(str(d2['k1_dat_o'])))
        self.assertTrue(any('không có dòng khớp' in c for c in k2.canh_bao))
        self.assertNotEqual(d2['tt_bat_dau'], d['tt_bat_dau'])

    def test_goi_rieng_khong_bi_bang_nhap_doi(self):
        moi = self.goi_moi()
        self._thay_bang()
        self.assertEqual(self.tinh(moi).k1, D(str(moi['dia_ban'][DOAN_TRI_AN][0]['k1_nong_nghiep'])))

    def test_tao_goi_tu_bang_he_so_k_co_xa_moi(self):
        self._thay_bang(xa='Xã Tân Triều Mới', k='1.5')
        moi = gg.tao_goi_tu_he_so_k(gg._gan_san(), 'K_MOI', 'QĐ 15/2027/QĐ-UBND', '01/01/2027')
        self.assertEqual(gg.kiem_goi(moi), [])
        self.assertEqual(list(moi['dia_ban']), ['Xã Tân Triều Mới'])
        k = g.tinh_don_gia(g.DauVao(dia_ban='Xã Tân Triều Mới', nhom_dat='DAT_NONG_NGHIEP', cot_gia='nn_rung_nts', don_gia_bang_gia=D(1000)), moi['dia_ban']['Xã Tân Triều Mới'][0], moi)
        self.assertEqual(k.k1, D('1.5'))
        self.assertTrue(gg.co_dia_ban(moi, 'Tân Triều Mới'))

    def test_dong_chung_nhom_nn_ap_cho_ca_cay_va_rung(self):
        d = g.ds_doan(DOAN_TRI_AN)[0]
        he_so_k.ghi([dict(dia_ban='Xã A', tt=1, loai_dat='nn', vi_tri='MT', tuyen_duong=d['ten_duong'], diem_dau='a', diem_cuoi='b', he_so='1.3', ghi_chu='')], 'Quyết định số 15/2027/QĐ-UBND')
        moi = gg.tao_goi_tu_he_so_k(gg._gan_san(), 'K_MOI', 'QĐ 15', '01/01/2027')
        r = moi['dia_ban']['Xã A'][0]
        self.assertEqual((r['k1_nn_cay'], r['k1_nn_rung_nts']), ('1.3', '1.3'))

    def test_k_doi_theo_vi_tri_trong_doan_thi_tu_choi(self):
        d = g.ds_doan(DOAN_TRI_AN)[0]
        he_so_k.ghi([dict(dia_ban='Xã A', tt=i + 1, loai_dat='dat_o', vi_tri=vt, tuyen_duong=d['ten_duong'], diem_dau='a', diem_cuoi='b', he_so=k, ghi_chu='') for i, (vt, k) in enumerate((('MT', '1.3'), ('T1', '1.4')))],
                    'Quyết định số 15/2027/QĐ-UBND')
        with self.assertRaises(gg.LoiGoi):
            gg.tao_goi_tu_he_so_k(gg._gan_san(), 'K_MOI', 'QĐ 15', '01/01/2027')


class TestDongBoMayChu(CoMay):
    def test_quan_tri_phat_hanh_may_khac_nhan_goi(self):
        goc = self.td / 'MayChu'
        may_chu.khoi_tao(goc, 'QuanTri', 'matkhau1', 'Quản trị')
        qt = may_chu.dang_nhap(goc, 'quantri', 'matkhau1')
        may_chu.them_nguoi_dung(qt, 'nv1', 'Nhân viên', 'abc123')
        gg.ghi_goi(self.goi_moi())                                  # sau_khi_sua tự phát hành
        self.assertEqual(quan_tri_bo.LOI_PHAT_HANH, '')
        self.assertIsNotNone(db.doc_phien_ban(goc)['tep'][db.FILE_QUY_TAC])
        may_chu.dang_xuat()
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may_b')
        gg._quen()
        self.assertEqual(len(gg.ds_goi()), 1)
        may_chu.dang_nhap(goc, 'nv1', 'abc123')
        self.assertIsNotNone(db.nhan())
        self.assertEqual([x['ma'] for x in gg.ds_goi()], [gg.MA_GAN_SAN, 'QD15_2027'])
        with self.assertRaises(LoiQuyenBoDonGia):                   # nhân viên không tự sửa gói
            gg.xoa_goi('QD15_2027')


def _su_kien_chuot():
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    return QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(1, 1), QPointF(1, 1), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestManHinh(CoMay):
    def _hop_tinh(self, con=None, ds=(), xa='Tân An'):
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        h = HopTinhGiaDat(None, con, list(ds), xa)
        h.im_lang = True
        self.addCleanup(h.close)
        return h

    def _hop_goi(self, ma=''):
        from pabt.man_hinh_goi_gia_dat import HopGoiGiaDat
        h = HopGoiGiaDat.__new__(HopGoiGiaDat)
        HopGoiGiaDat.im_lang = True
        self.addCleanup(lambda: setattr(HopGoiGiaDat, 'im_lang', False))
        HopGoiGiaDat.__init__(h, None, ma)
        self.addCleanup(h.close)
        return h

    def test_doi_goi_dung_lai_o_chon_va_tinh_theo_goi(self):
        moi = self.goi_moi()
        next(y for y in moi['yeu_to'] if y['ma'] == 'NN_DUONG_DAT_SOI_DA')['he_so'] = '0.85'
        moi['yeu_to'].append(dict(ma='NN_MOI', ten='Yếu tố mới của văn bản mới', he_so='1.1', ap_cho='nn'))
        moi['he_so_them'] = [dict(ma='K4', ten='Hệ số vùng', mac_dinh='1.2', can_cu='Điều 5')]
        moi['cong_thuc']['he_so'].append('K4')
        gg.ghi_goi(moi)
        h = self._hop_tinh(xa='Trị An')
        self.assertEqual(h.goi['ma'], gg.MA_GAN_SAN)                 # gói mới chưa tới ngày hiệu lực: chưa tự chọn
        self.assertNotIn('NN_MOI', h.ck_pl3)
        self.assertEqual(h.o_he_so, {})
        h.cb_nhom.setCurrentIndex(0)
        h.cb_ket_cau.setCurrentIndex(1)
        self.assertEqual(h.kq.k3, D('0.90'))
        h.cb_goi.setCurrentIndex(h.cb_goi.findData('QD15_2027'))
        self.assertEqual(h.kq.k3, D('0.85'))                         # giữ mặt đường đã chọn, tính theo hệ số mới
        self.assertIn('NN_MOI', h.ck_pl3)
        self.assertEqual(h.kq.he_so_them['K4'], D('1.2'))
        self.assertIn('QĐ 15/2027', h.lb_tieu_de.text())
        h.o_he_so['K4'].setText('1,5')
        self.assertEqual(h.kq.he_so_them['K4'], D('1.5'))
        h.ck_pl3['NN_MOI'].setChecked(True)
        self.assertEqual(h.kq.k3, D('0.935000'))

    def test_du_an_o_xa_goi_chua_co_thi_bao(self):
        h = self._hop_tinh(xa='Xã Long Thành')
        self.assertIn('chưa có địa bàn', h.lb_canh_bao.text())

    def test_hop_goi_gan_san_chi_xem_tao_goi_moi_sua_luu_xoa(self):
        h = self._hop_goi()
        self.assertFalse(h.b_luu.isEnabled())
        self.assertFalse(h.b_xoa.isEnabled())
        self.assertTrue(h.o_cong_thuc.isReadOnly())
        self.assertFalse(h.luu())
        self.assertEqual(h.bang_yt.rowCount(), 4)
        self.assertTrue(h.tao_tu_goi())
        self.assertTrue(h.b_luu.isEnabled())
        h.o_so_hieu.setText('QĐ 15/2027/QĐ-UBND')
        h.o_tu.setText('01/01/2027')
        r = next(i for i in range(h.bang_yt.rowCount()) if h.bang_yt.item(i, 0).text() == 'PNN_TTTM_200M')
        h.bang_yt.item(r, 2).setText('1,08')
        h.b_them_hs.click()
        h.o_cong_thuc.setText('K1, K2, K3, K_KHAC, K4')
        h.kiem()
        self.assertIn('×1,05 -> ×1,08', h.o_khac.toPlainText())
        self.assertIn('K4', h.o_khac.toPlainText())
        self.assertTrue(h.luu())
        self.assertTrue(h.da_doi)
        self.assertEqual(len(gg.ds_goi()), 2)
        x = gg.ds_goi()[1]
        self.assertEqual(x['hieu_luc_tu'], '2027-01-01')
        self.assertEqual(next(y for y in x['yeu_to'] if y['ma'] == 'PNN_TTTM_200M')['he_so'], '1.08')
        self.assertTrue(next(y for y in x['yeu_to'] if y['ma'] == 'NN_DUONG_DAT_SOI_DA')['khoa_neu_quy_dinh_rieng'])
        self.assertEqual(x['cau_chu'], gg._gan_san()['cau_chu'])
        self.assertEqual(h.g['ma'], x['ma'])
        self.assertTrue(h.xoa(hoi=False))
        self.assertEqual(len(gg.ds_goi()), 1)

    def test_chu_dai_cua_o_danh_dau_khong_day_cot_trai(self):
        h = self._hop_tinh()
        c = h.ck_pl3['NN_DUONG_DAT_SOI_DA']
        self.assertEqual(c.text(), '')                               # chữ ở nhãn tự xuống dòng
        nhan = h.hang_pl3['NN_DUONG_DAT_SOI_DA'].findChild(type(h.lb_k2))
        self.assertIn('đường đất', nhan.text())
        h.cb_nhom.setCurrentIndex(0)
        was = c.isChecked()
        nhan.mouseReleaseEvent(_su_kien_chuot())                     # bấm vào chữ cũng đổi ô
        self.assertNotEqual(c.isChecked(), was)
        c.setChecked(False)
        h.cb_nhom.setCurrentIndex(1)                                 # đất ở: cả dòng tắt, bấm chữ không đổi
        self.assertFalse(c.isEnabled())
        nhan.mouseReleaseEvent(_su_kien_chuot())
        self.assertFalse(c.isChecked())

    def test_bo_goi_chua_luu_thi_biet(self):
        h = self._hop_goi()
        self.assertFalse(h.chua_luu())                               # gói gắn sẵn chỉ xem
        h.tao_tu_goi()
        self.assertTrue(h.chua_luu())
        h.o_tu.setText('01/01/2027')
        h.o_so_hieu.setText('QĐ 15/2027/QĐ-UBND')
        self.assertTrue(h.luu())
        self.assertFalse(h.chua_luu())
        h.bang_yt.item(0, 2).setText('1,2')
        self.assertTrue(h.chua_luu())

    def test_goi_rieng_gop_van_ban_can_cu_khi_mo_va_khi_chon(self):
        moi = self.goi_moi(tu='01/06/2026')
        self.assertEqual(moi['van_ban_can_cu'], [])                  # căn cứ của gói cũ không theo sang
        moi['van_ban_can_cu'] = ['Quyết định số 15/2027/QĐ-UBND ngày 01/6/2026 của UBND thành phố Đồng Nai']
        gg.ghi_goi(moi)
        h = self._hop_tinh()
        self.assertIn('15/2027/QĐ-UBND', h.o_can_cu.toPlainText())
        h.cb_goi.setCurrentIndex(h.cb_goi.findData(gg.MA_GAN_SAN))
        h.cb_goi.setCurrentIndex(h.cb_goi.findData(moi['ma']))
        self.assertEqual(h.o_can_cu.toPlainText().count('15/2027/QĐ-UBND'), 1)

    def test_hop_goi_nhap_sai_khong_luu(self):
        h = self._hop_goi()
        h.tao_tu_goi()
        h.bang_yt.item(0, 2).setText('abc')
        self.assertFalse(h.luu())
        self.assertIn('CHƯA HỢP LỆ', h.o_khac.toPlainText())
        self.assertEqual(len(gg.ds_goi()), 1)
        p = self.td / 'x.json'
        p.write_text('{}', encoding='utf-8')
        self.assertFalse(h.nhap_file(p))

    def test_hop_goi_tu_bang_he_so_k_khi_chua_nhap_van_co_gan_san(self):
        h = self._hop_goi()
        self.assertTrue(h.tao_tu_he_so_k())                          # bảng K gắn sẵn: 3 xã
        self.assertEqual(gg.kiem_goi(h.gia_tri()), [])

    def test_ap_gia_ghi_ten_van_ban_du_an_nho_goi_so_cu_khong_doi(self):
        from tests.test_tinh_gia_dat_ui import _du_an as tao
        p = tao(self.td)
        con = csdl.mo(str(p))
        self.addCleanup(con.close)
        ma = con.execute('SELECT ma_ho FROM ho LIMIT 1').fetchone()[0]
        gg.ghi_goi(self.goi_moi(tu='01/06/2026'))                    # gói mới, hôm nay đang hiệu lực
        h = self._hop_tinh(con, [ma])
        self.assertEqual(h.goi['ma'], 'QD15_2027')
        h.o_g.setText('1000000')
        so_dong, so_ho, loi = h.ap_gia(xac_nhan=True)
        self.assertEqual((so_ho, loi), (1, []))
        self.assertGreater(so_dong, 0)
        self.assertEqual(gg.goi_du_an(con)['ma'], 'QD15_2027')
        d = BoSoan(con, ma).pa.dat[0]
        self.assertIn('Đơn giá đất theo NQ 28/2025/NQ-HĐND × QĐ 15/2027/QĐ-UBND', d.ghi_chu)
        gia = d.gia_bang_gia
        self.assertTrue(pb.khoa_v1(con, ma))
        tong_v1 = pb.tong(con, ma, pb.V1)
        # có gói mới hơn, đổi hệ số: số đã áp, V1 giữ nguyên, ghi chú cũ được thay khi áp lại
        moi = self.goi_moi('QD99', 'QĐ 99/2028/QĐ-UBND', '01/07/2026')
        moi['cong_thuc']['he_so'] = ['K1']
        gg.ghi_goi(moi)
        self.assertEqual(BoSoan(con, ma).pa.dat[0].gia_bang_gia, gia)
        self.assertEqual(pb.tong(con, ma, pb.V1), tong_v1)
        self.assertEqual(gg.goi_du_an(con)['ma'], 'QD15_2027')
        bs = BoSoan(con, ma)
        bs.ap_don_gia_qd03([0], D(5000), 'Đơn giá đất theo NQ 28/2025/NQ-HĐND × QĐ 99/2028/QĐ-UBND: x')
        self.assertEqual(bs.pa.dat[0].ghi_chu.count('Đơn giá đất theo'), 1)
        self.assertIn('QĐ 99', bs.pa.dat[0].ghi_chu)
        self.assertEqual(doc_phuong_an(con, ma).dat[0].gia_bang_gia, gia)


if __name__ == '__main__':
    unittest.main()
