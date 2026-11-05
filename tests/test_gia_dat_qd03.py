"""05/11/2026: bộ tính đơn giá đất NQ 28/2025 x QĐ 03/2026 (port từ HeThongDinhGiaVaScanThongMinh_V2.tsx), văn bản căn cứ 13 bậc, bộ quét dùng chung.
Không Qt (lõi). Số liệu kiểm chứng: ví dụ của VB 1201/SNNMT-ĐĐ (thửa 200 m2, 10.000.000 đ/m2, K1 1,1, K2 1,05, K3 0,95 = 2.194.500.000 đ)."""
from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import gia_dat_qd03 as g
from pabt import quet_chung as qc
from pabt import van_ban_can_cu as vb

D = Decimal


def _kq(**kw):
    doan = kw.pop('doan', None)
    return g.tinh_don_gia(g.DauVao(**kw), doan)


class TestDuLieu(unittest.TestCase):
    def test_106_doan_3_dia_ban(self):
        self.assertEqual(g.so_doan(), 106)
        self.assertEqual([len(g.ds_doan(k)) for k in g.ds_dia_ban()], [61, 26, 19])
        for k in g.ds_dia_ban():
            tt = 1
            for r in g.ds_doan(k):                       # cụm 7 dòng / đoạn, liên tiếp
                self.assertEqual((r['tt_bat_dau'], r['tt_ket_thuc']), (tt, tt + 6))
                tt += 7

    def test_hang_so_k3_khop_json(self):
        pl3 = g.du_lieu()['phu_luc_III_yeu_to_anh_huong']
        json_k3 = {r['ma']: D(str(r['he_so_k3'])) for r in pl3['dat_phi_nong_nghiep'] + pl3['dat_nong_nghiep']}
        for y in g.gg._gan_san()['yeu_to']:
            self.assertEqual(json_k3[y['ma']], D(y['he_so']), y['ma'])
        self.assertEqual(pl3['yeu_to_khac_mac_dinh'], 1.0)

    def test_k1_khop_bang_he_so_k_gan_san(self):
        """Hai nguồn K1 (gia_dat_qd03.json và he_so_k_qd03.json gắn sẵn từ trước) không được lệch nhau."""
        from pabt import he_so_k, tai_nguyen
        goc = json.load(open(str(tai_nguyen(he_so_k.FILE_GAN_SAN)), encoding='utf-8'))['dong']
        theo = {(r['dia_ban'], r['tt']): r['k'] for r in goc}
        sai = []
        for k in g.ds_dia_ban():
            ten = g.ten_ngan(k)
            for r in g.ds_doan(k):
                x = theo.get((ten, r['tt_bat_dau']))
                if x is None:
                    continue
                if D(str(x['dat_o'])) != D(str(r['k1_dat_o'])) or D(str(x['nn'])) != D(str(r['k1_nong_nghiep'])):
                    sai.append((ten, r['tt_bat_dau']))
        self.assertEqual(sai, [])

    def test_tra_gia_nq28_cum_7_dong(self):
        from pabt import gia_dat_nq28 as nq
        k = 'Bảng 54. Xã Tân An'
        d = g.ds_doan(k)[0]
        for i, x in enumerate(g.gg._gan_san()['vi_tri']):
            ma, vt = x['ma'], x['vi_tri']
            gia = g.gia_bang_gia(k, d, 'DAT_O', ma)
            r = next(x for x in nq.tat_ca() if x['xa'] == 'Xã Tân An' and x['tt'] == d['tt_bat_dau'] + i)
            self.assertEqual(r['vi_tri'], vt)
            self.assertEqual(gia, D(nq.gia_dong(r, 'dat_o')))
        self.assertIsNone(g.gia_bang_gia(k, None, 'DAT_O', 'MAT_TIEN_VT1'))

    def test_dia_ban_theo_ten(self):
        self.assertEqual(g.dia_ban_theo_ten('Xã Tân An'), 'Bảng 54. Xã Tân An')
        self.assertEqual(g.dia_ban_theo_ten('phường Trị An'), 'Bảng 53. Phường Trị An')
        self.assertEqual(g.dia_ban_theo_ten('Phú Lý'), 'Bảng 55. Xã Phú Lý')
        self.assertEqual(g.dia_ban_theo_ten('Tân Triều'), '')


class TestCongThuc(unittest.TestCase):
    def test_vi_du_vb_1201(self):
        kq = _kq(nhom_dat='DAT_O', don_gia_bang_gia=D(10000000), he_so_k1=D('1.1'), ap_dung_quy_hoach_pl2=True,
                 he_so_quy_hoach_k2=D('1.05'), yeu_to_pl3=['PNN_NGHIATRANG_100M'])
        self.assertEqual(kq.don_gia_ap_dung, D(10972500))
        self.assertEqual(kq.don_gia_ap_dung * 200, D(2194500000))
        self.assertEqual((kq.k1, kq.k2, kq.k3), (D('1.1'), D('1.05'), D('0.95')))

    def test_k2_mac_dinh_khoa_1(self):
        kq = _kq(nhom_dat='DAT_O', don_gia_bang_gia=D(1000000), he_so_k1=D('1.2'), ap_dung_quy_hoach_pl2=False,
                 he_so_quy_hoach_k2=D('1.5'))
        self.assertEqual(kq.k2, 1)
        self.assertEqual(kq.don_gia_ap_dung, D(1200000))

    def test_lam_tron_nua_len(self):
        kq = _kq(nhom_dat='DAT_O', don_gia_bang_gia=D(1001), he_so_k1=D('1.5'))      # 1501,5 -> 1502
        self.assertEqual(kq.don_gia_da_lam_tron, D(1502))

    def test_doan_duong_k1_theo_nhom(self):
        k = 'Bảng 54. Xã Tân An'
        d = next(r for r in g.ds_doan(k) if r['ten_duong'] == 'Đường tỉnh 768' and r['diem_dau'] == 'Cầu Chùm Bao')
        self.assertEqual(_kq(dia_ban=k, nhom_dat='DAT_O', don_gia_bang_gia=D(1000), doan=d).k1, D('1.39'))
        self.assertEqual(_kq(dia_ban=k, nhom_dat='DAT_NONG_NGHIEP', don_gia_bang_gia=D(1000), doan=d).k1, D('1.32'))

    def test_nong_nghiep_duong_dat_k3_090(self):
        k = 'Bảng 54. Xã Tân An'
        d = g.ds_doan(k)[0]                                                    # NN K1 1,45
        kq = _kq(dia_ban=k, nhom_dat='DAT_NONG_NGHIEP', don_gia_bang_gia=D(500000), ket_cau_mat_duong='DAT_SOI_DA_CAPPHOI', doan=d)
        self.assertEqual(kq.k3, D('0.90'))
        self.assertEqual(kq.don_gia_ap_dung, D(500000) * D('1.45') * D('0.90'))
        self.assertEqual(kq.canh_bao, [])
        kq2 = _kq(dia_ban=k, nhom_dat='DAT_NONG_NGHIEP', don_gia_bang_gia=D(500000), ket_cau_mat_duong='NHUA_BETONG', doan=d)
        self.assertEqual(kq2.k3, 1)

    def test_chot_chan_khong_nhan_trung(self):
        k = 'Bảng 54. Xã Tân An'
        d = dict(g.ds_doan(k)[0], co_quy_dinh_rieng_duong_dat_tai_pl1=True)
        kq = _kq(dia_ban=k, nhom_dat='DAT_NONG_NGHIEP', don_gia_bang_gia=D(500000), ket_cau_mat_duong='DAT_SOI_DA_CAPPHOI', doan=d)
        self.assertEqual(kq.k3, 1)
        self.assertTrue(any('chống nhân trùng' in c for c in kq.canh_bao))
        kq2 = _kq(nhom_dat='DAT_NONG_NGHIEP', don_gia_bang_gia=D(500000), he_so_k1=D('1.45'), ket_cau_mat_duong='DAT_SOI_DA_CAPPHOI',
                  co_quy_dinh_rieng_duong_dat_pl1=True)                        # cờ nhập tay, không có đoạn
        self.assertEqual(kq2.k3, 1)

    def test_loai_tru_yeu_to_khong_dung_nhom(self):
        nn = _kq(nhom_dat='DAT_NONG_NGHIEP', don_gia_bang_gia=D(1000), he_so_k1=D(1), yeu_to_pl3=['PNN_TTTM_200M', 'PNN_HANHLANG_50M'])
        self.assertEqual(nn.k3, 1)
        self.assertTrue(nn.canh_bao)
        pnn = _kq(nhom_dat='DAT_O', don_gia_bang_gia=D(1000), he_so_k1=D(1), yeu_to_pl3=['NN_DUONG_DAT_SOI_DA'],
                  ket_cau_mat_duong='DAT_SOI_DA_CAPPHOI')
        self.assertEqual(pnn.k3, 1)
        self.assertTrue(pnn.canh_bao)

    def test_pnn_nhan_nhieu_yeu_to(self):
        kq = _kq(nhom_dat='DAT_O', don_gia_bang_gia=D(10000000), he_so_k1=D(1),
                 yeu_to_pl3=['PNN_TTTM_200M', 'PNN_NGHIATRANG_100M', 'PNN_HANHLANG_50M'])
        self.assertEqual(kq.k3, D('1.05') * D('0.95') * D('0.95'))             # 0,947625

    def test_chuyen_tiep_dieu_4(self):
        kw = dict(nhom_dat='DAT_O', don_gia_bang_gia=D(1000000), he_so_k1=D('1.2'))      # giá tính 1.200.000
        cao = _kq(gia_dat_cu_the=D(1300000), **kw)
        self.assertEqual((cao.don_gia_ap_dung, cao.ap_dung_chuyen_tiep), (D(1300000), True))
        bang = _kq(gia_dat_cu_the=D(1200000), **kw)
        self.assertEqual((bang.don_gia_ap_dung, bang.ap_dung_chuyen_tiep), (D(1200000), True))
        thap = _kq(gia_dat_cu_the=D(1100000), **kw)
        self.assertEqual((thap.don_gia_ap_dung, thap.ap_dung_chuyen_tiep), (D(1200000), False))
        self.assertEqual(_kq(**kw).ap_dung_chuyen_tiep, False)

    def test_nhat_ky_giai_trinh_du_buoc(self):
        kq = _kq(nhom_dat='DAT_O', don_gia_bang_gia=D(1000000), he_so_k1=D('1.2'), gia_dat_cu_the=D(900000))
        self.assertEqual([x.split(' ')[1] for x in kq.buoc_lap_luan], ['1', '2', '3', '4', '5'])
        self.assertIn('K1', kq.cong_thuc)

    def test_ghi_chu_ap_gia(self):
        k = 'Bảng 54. Xã Tân An'
        d = g.ds_doan(k)[0]
        kq = _kq(dia_ban=k, nhom_dat='DAT_O', don_gia_bang_gia=D(2000000), doan=d)
        ct = g.ghi_chu_ap_gia(kq, d, g.ten_ngan(k))
        self.assertIn('QĐ 03/2026/QĐ-UBND', ct)
        self.assertIn(d['ten_duong'], ct)


class TestVanBanCanCu(unittest.TestCase):
    def test_tam_bac_mac_dinh_dung_thu_tu(self):
        _, ds = vb.gop_va_sap_xep(vb.CAN_CU_MAC_DINH)
        self.assertEqual([x.so_hieu for x in ds if not x.so_hieu.startswith('VB-')],
                         ['31/2024/QH15', '254/2025/QH15', '49/2026/NĐ-CP', '27/2025/NQ-HĐND', '28/2025/NQ-HĐND', '03/2026/QĐ-UBND',
                          '1201/SNNMT-ĐĐ'])
        self.assertEqual([x.bac for x in ds], [2, 3, 6, 11, 11, 12, 13, 13])
        self.assertEqual(len(ds), 8)                                         # VB 29/5/2026 không đè mất NQ 28 (lỗi bản TSX)

    def test_13_bac_dung(self):
        mau = [(1, 'Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam năm 2013'),
               (2, 'Luật Tổ chức chính quyền địa phương số 72/2025/QH15'),
               (3, 'Nghị quyết số 254/2025/QH15 của Quốc hội quy định ... thi hành Luật Đất đai'),
               (4, 'Pháp lệnh số 01/2020/UBTVQH14 của Ủy ban Thường vụ Quốc hội'),
               (5, 'Quyết định số 10/2020/QĐ-CTN của Chủ tịch nước'),
               (6, 'Nghị định số 78/2025/NĐ-CP của Chính phủ'),
               (7, 'Quyết định số 20/2025/QĐ-TTg của Thủ tướng Chính phủ'),
               (8, 'Thông tư số 08/2024/TT-BTNMT của Bộ Tài nguyên và Môi trường'),
               (9, 'Văn bản hợp nhất số 01/VBHN-BTNMT'),
               (10, 'Công văn số 123/BNNMT-ĐĐ của Bộ Nông nghiệp và Môi trường hướng dẫn'),
               (11, 'Nghị quyết số 28/2025/NQ-HĐND ngày 10/5/2025 của HĐND tỉnh Đồng Nai'),
               (12, 'Quyết định số 03/2026/QĐ-UBND ngày 11/5/2026 của UBND thành phố Đồng Nai'),
               (13, 'Văn bản số 1201/SNNMT-ĐĐ ngày 20/5/2026 của Sở Nông nghiệp và Môi trường'),
               (13, 'Quyết định số 12/2026/QĐ-UBND của UBND xã Tân An về thu hồi đất')]
        for bac, chu in mau:
            self.assertEqual(vb.phan_loai(chu).bac, bac, chu)

    def test_quet_them_khu_trung_va_chen_dung_bac(self):
        t, _ = vb.gop_va_sap_xep(vb.CAN_CU_MAC_DINH)
        moi = ['Nghị định số 78/2025/NĐ-CP của Chính phủ về bồi thường', vb.CAN_CU_MAC_DINH[0], '1. ' + vb.CAN_CU_MAC_DINH[5] + ';']
        t2, ds = vb.gop_va_sap_xep([t], moi)
        self.assertEqual(len(ds), 9)                                          # chỉ thêm NĐ 78; Luật 31, QĐ 03 không lặp
        so = [x.so_hieu for x in ds]
        self.assertLess(so.index('78/2025/NĐ-CP'), so.index('49/2026/NĐ-CP'))      # cùng bậc 6: năm 2025 trước 2026
        self.assertLess(so.index('254/2025/QH15'), so.index('78/2025/NĐ-CP'))
        self.assertTrue(t2.startswith('1. Luật Đất đai'))
        # gộp lại kết quả đã đánh số: ổn định (không đổi)
        self.assertEqual(vb.gop_va_sap_xep([t2])[0], t2)

    def test_giu_ban_dai_hon(self):
        ngan = 'Nghị quyết số 28/2025/NQ-HĐND của HĐND tỉnh Đồng Nai'
        dai = vb.CAN_CU_MAC_DINH[4]
        _, ds = vb.gop_va_sap_xep([ngan], [dai])
        self.assertEqual([x.chu for x in ds], [dai])


class TestQuetChung(unittest.TestCase):
    def test_trich_can_cu_trong_noi_dung(self):
        nd = 'Căn cứ Luật Đất đai số 31/2024/QH15;\nCăn cứ Nghị định số 88/2024/NĐ-CP của Chính phủ;\nNội dung khác 28/2025/NQ-HĐND'
        kq = vb.trich_can_cu(nd, 'x.txt')
        self.assertIn('Luật Đất đai số 31/2024/QH15', kq)
        self.assertTrue(any('Bảng giá đất lần đầu' in c for c in kq))
        self.assertIn('Nghị định số 88/2024/NĐ-CP của Chính phủ', kq)

    def test_quet_gia_dat_tai_san_thua(self):
        nd = ('Xã Tân An - đất trồng cây lâu năm tiếp giáp đường cấp phối rộng 4m\n'
              'Theo QĐ 03/2026/QĐ-UBND, tờ bản đồ số 12, thửa đất số 205, diện tích 256,8 m2\n'
              'Cây bưởi\tcây\t35\t1.450.000\nNhà cấp 4\tm2\t65\t3.850.000\n')
        kq = qc.quet(['a.txt'], qc.AUTO, doc=lambda p: nd)
        self.assertEqual(kq.tham_so['dia_ban'], 'Bảng 54. Xã Tân An')
        self.assertEqual(kq.tham_so['ket_cau_mat_duong'], 'DAT_SOI_DA_CAPPHOI')
        self.assertEqual([(d.to_ban_do, d.so_thua, d.dien_tich_thu_hoi, d.ket_cau_mat_duong) for d in kq.dong_dat],
                         [('12', '205', D('256.8'), 'DAT_SOI_DA_CAPPHOI')])
        self.assertEqual([(t.danh_muc, t.thanh_tien) for t in kq.dong_tai_san],
                         [('CAY_TRONG_HOA_MAU', D(50750000)), ('NHA_VAT_KIEN_TRUC', D(250250000))])
        self.assertTrue(any('03/2026/QĐ-UBND' in c for c in kq.can_cu))
        self.assertIn(qc.CAN_CU, kq.loai_phat_hien)

    def test_ngu_canh_gioi_han(self):
        nd = 'Cây bưởi\tcây\t35\t1.450.000\n'
        kq = qc.quet(['a.txt'], qc.CAN_CU, doc=lambda p: 'Văn bản ' + nd.replace('Cây', 'Dòng'))
        self.assertEqual(kq.dong_tai_san, [])                      # ngữ cảnh chỉ văn bản căn cứ: không bóc đơn giá tài sản
        kq2 = qc.quet(['a.txt'], qc.GIA_TAI_SAN, doc=lambda p: nd)
        self.assertEqual(len(kq2.dong_tai_san), 1)
        with self.assertRaises(ValueError):
            qc.quet([], 'KHAC')

    def test_loi_mot_file_khong_dung_ca_loat(self):
        def doc(p):
            if p.name == 'hong.pdf':
                raise RuntimeError('file hỏng')
            return 'Căn cứ Luật Đất đai số 31/2024/QH15'
        kq = qc.quet(['hong.pdf', 'tot.txt'], qc.AUTO, doc=doc)
        self.assertEqual(len(kq.loi), 1)
        self.assertIn('hong.pdf', kq.loi[0])
        self.assertTrue(kq.can_cu)
        self.assertEqual(kq.so_file, 2)

    def test_doc_file_txt_that(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'vb.txt'
            p.write_text('Căn cứ Nghị quyết số 27/2025/NQ-HĐND của HĐND tỉnh Đồng Nai', encoding='utf-8')
            kq = qc.quet([p], qc.CAN_CU)
            self.assertEqual(kq.loi, [])
            self.assertTrue(kq.can_cu)


if __name__ == '__main__':
    unittest.main()
