"""0.9.76 (người dùng 13/10/2026, Mục IV QĐ 18/2026/QĐ-UBND): nâng cấp Nhóm 5 (Tổng hợp & Trình duyệt) và Nhóm 6 (Phê duyệt & Bàn
giao) - mốc thời hạn (thoi_han), sổ nhật ký vận động và cưỡng chế (van_dong), cơ cấu kinh phí / đối soát khái toán
(kinh_phi_du_an), báo cáo tiến độ GPMB (bao_cao_gpmb), hộ đã niêm yết xong, báo cáo tiếp thu ý kiến (bao_cao_y_kien).
Số liệu GIẢ LẬP. Phần giao diện ở các lớp Test...Giao dien cuối file."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import bao_cao_gpmb, bao_cao_y_kien, csdl, du_thao, kinh_phi_du_an, quan_ly, theo_doi, thoi_han, van_dong
from pabt.lap_pa import LoiNhap
from pabt.tien import D, KHONG
from tests.test_toc_do import _du_an

HOM_NAY = date(2026, 10, 13)


def _ngay(n: int) -> str:
    """Ngày cách HOM_NAY n ngày (n âm = quá khứ), dạng dd/mm/yyyy."""
    return (HOM_NAY + timedelta(days=n)).strftime('%d/%m/%Y')


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)
        self.p = _du_an(self.td, 6)
        self.con = csdl.mo(self.p)
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]

    def qd(self, so='101/QĐ-UBND', ngay='01/09/2026', ds=None) -> int:
        q = theo_doi.luu_qd(self.con, None, so, ngay, 'Phê duyệt phương án')
        theo_doi.them_ho_theo_pa(self.con, q, list(self.ma[:4] if ds is None else ds))
        return q


class TestThoiHan(_Co):
    def test_mac_dinh_va_sua(self):
        self.assertEqual(thoi_han.tat_ca_so_ngay(self.con), dict(tham_dinh=15, thu_hoi_nn=60, thu_hoi_pnn=120, van_dong=10))
        self.assertTrue(thoi_han.dat_so_ngay(self.con, dict(tham_dinh=20, van_dong=7)))
        self.assertEqual((thoi_han.so_ngay(self.con, 'tham_dinh'), thoi_han.so_ngay(self.con, 'van_dong')), (20, 7))
        self.assertFalse(thoi_han.dat_so_ngay(self.con, dict(tham_dinh=20)))             # không đổi: không ghi
        for sai in ('abc', 0, -3, 99999, ''):
            with self.assertRaises(LoiNhap):
                thoi_han.dat_so_ngay(self.con, dict(tham_dinh=sai))
        self.assertEqual(thoi_han.so_ngay(self.con, 'tham_dinh'), 20)                    # lỗi không ghi gì
        with self.assertRaises(KeyError):
            thoi_han.dat_so_ngay(self.con, dict(khong_co=1))

    def test_han_tham_dinh(self):
        d = quan_ly.lay_dot(self.con, quan_ly.tao_dot(self.con, 'Đợt 1'))
        self.assertEqual(thoi_han.han_tham_dinh(self.con, d, HOM_NAY)['muc'], 'chua_trinh')
        for lui, muc, con_lai in ((0, 'con_han', 15), (5, 'con_han', 10), (12, 'sap_het', 3), (15, 'sap_het', 0), (16, 'qua_han', -1),
                                  (-4, 'con_han', 15)):
            d.ngay_trinh = _ngay(-lui)
            kq = thoi_han.han_tham_dinh(self.con, d, HOM_NAY)
            self.assertEqual((kq['muc'], kq['con_lai']), (muc, con_lai), f'lùi {lui} ngày')
        d.ngay_trinh = _ngay(-5)
        self.assertIn('Còn 10 / 15 ngày', thoi_han.han_tham_dinh(self.con, d, HOM_NAY)['chu'])
        self.assertIn('Khoản 8 Mục IV QĐ 18', thoi_han.han_tham_dinh(self.con, d, HOM_NAY)['chu'])
        d.ngay_trinh = _ngay(-20)
        self.assertIn('QUÁ HẠN 5 ngày', thoi_han.han_tham_dinh(self.con, d, HOM_NAY)['chu'])
        self.assertEqual(thoi_han.han_tham_dinh(self.con, d, HOM_NAY, da_phe_duyet=True)['muc'], 'da_xong')
        thoi_han.dat_so_ngay(self.con, dict(tham_dinh=30))                                # số ngày lấy từ cài đặt, không gán cứng
        self.assertEqual(thoi_han.han_tham_dinh(self.con, d, HOM_NAY)['con_lai'], 10)

    def test_phan_nhom_dat(self):
        for loai, nhom in (('LUC', 'nn'), ('cln', 'nn'), ('CLN+LUK', 'nn'), ('ONT', 'pnn'), ('ONT+CLN', 'pnn'), ('CLN, OTC', 'pnn'),
                           ('ODT', 'pnn'), ('SKC', 'pnn'), ('', 'khong_ro'), ('XXX', 'khong_ro'), ('CLN+XXX', 'khong_ro')):
            self.assertEqual(thoi_han.phan_nhom_dat(loai), nhom, loai)
        self.assertEqual(thoi_han.nhom_dat_ho(['CLN', 'LUC']), 'nn')
        self.assertEqual(thoi_han.nhom_dat_ho(['CLN', 'ONT']), 'pnn')
        self.assertEqual(thoi_han.nhom_dat_ho([]), 'khong_ro')

    def test_moc_thu_hoi(self):
        nn, pnn = 60, 120
        self.assertIsNone(thoi_han.moc_thu_hoi_ho('nn', None, nn, pnn, HOM_NAY)['du'])
        self.assertIn('Chưa có ngày thông báo', thoi_han.moc_thu_hoi_ho('nn', None, nn, pnn, HOM_NAY)['chu'])
        for nhom, qua, du in (('nn', 59, False), ('nn', 60, True), ('nn', 90, True), ('pnn', 119, False), ('pnn', 120, True),
                              ('khong_ro', 100, False), ('khong_ro', 120, True)):
            kq = thoi_han.moc_thu_hoi_ho(nhom, HOM_NAY - timedelta(days=qua), nn, pnn, HOM_NAY)
            self.assertEqual(kq['du'], du, f'{nhom} {qua}')
        self.assertEqual(thoi_han.moc_thu_hoi_ho('nn', HOM_NAY - timedelta(days=45), nn, pnn, HOM_NAY)['con_lai'], 15)

    def test_moc_thu_hoi_theo_thua_cua_ho(self):
        """Hộ có thửa ONT (hộ 1: 1 thửa ONT) -> đất phi nông nghiệp 120 ngày; hộ chỉ có LUC -> 60 ngày."""
        thoi_han.dat_ngay_thong_bao(self.con, _ngay(-70))
        moc = thoi_han.moc_thu_hoi_tat_ca(self.con, hom_nay=HOM_NAY)
        for m in self.ma:
            loai = [r[0] for r in self.con.execute('SELECT loai_dat FROM thua WHERE ma_ho = ?', (m,))]
            nhom = thoi_han.nhom_dat_ho(loai)
            self.assertEqual(moc[m]['nhom'], nhom)
            self.assertEqual(moc[m]['du'], 70 >= (60 if nhom == 'nn' else 120))
        self.assertTrue(any(v['du'] for v in moc.values()) and not all(v['du'] for v in moc.values()))

    def test_ngay_thong_bao(self):
        self.assertEqual(thoi_han.dat_ngay_thong_bao(self.con, '5/3/2026'), '05/03/2026')
        self.assertEqual(thoi_han.ngay_thong_bao(self.con), date(2026, 3, 5))
        for sai in ('abc', '31/02/2026', '2026'):
            with self.assertRaises(LoiNhap):
                thoi_han.dat_ngay_thong_bao(self.con, sai)
        self.assertEqual(thoi_han.dat_ngay_thong_bao(self.con, ''), '')
        self.assertIsNone(thoi_han.ngay_thong_bao(self.con))


class TestVanDong(_Co):
    def test_bang_tao_khi_can(self):
        self.assertTrue(van_dong.co_bang(self.con))                                      # dự án có hộ: có ngay khi mở
        with self.con:
            self.con.execute(f'DROP TABLE {van_dong.BANG}')                              # file cũ: chưa có bảng
        self.assertEqual(van_dong.ds_buoi(self.con), [])
        self.assertEqual(van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY), {})
        self.qd()
        van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _ngay(-3))                       # ghi buổi đầu: tự tạo bảng
        self.assertTrue(van_dong.co_bang(self.con))
        self.assertEqual(csdl.mo(self.p).execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)

    def test_kiem_tra_dau_vao(self):
        for loi in (dict(viec='x', ngay=_ngay(0)), dict(viec='tien', ngay=''), dict(viec='tien', ngay='32/13/2026'),
                    dict(viec='tien', ngay=_ngay(0), ket_qua='khac')):
            with self.assertRaises(LoiNhap):
                van_dong.ghi_buoi(self.con, self.ma[0], **loi)
        with self.assertRaises(LoiNhap):
            van_dong.ghi_buoi(self.con, 99999, 'tien', _ngay(0))
        self.assertEqual(van_dong.ds_buoi(self.con), [])

    def test_ghi_sua_xoa_va_thu_tu(self):
        a = van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _ngay(-2), 'Họp tổ', 'Tổ vận động', 'Mời hộ nhận tiền', 'vang_mat')
        b = van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _ngay(-9), ket_qua='chua_dong_y')
        ds = van_dong.ds_buoi(self.con, self.ma[0])
        self.assertEqual([x['id'] for x in ds], [b, a])                                  # theo ngày, cũ trước
        van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _ngay(-1), buoi_id=a, ket_qua='dong_y')
        self.assertEqual([x for x in van_dong.ds_buoi(self.con, self.ma[0]) if x['id'] == a][0]['ket_qua'], 'dong_y')
        with self.assertRaises(LoiNhap):
            van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _ngay(-1), buoi_id=99999)
        self.assertEqual(van_dong.xoa_buoi(self.con, b), 1)
        self.assertEqual(van_dong.xoa_buoi(self.con, b), 0)
        self.assertEqual(len(van_dong.ds_buoi(self.con, viec='mat_bang')), 0)

    def test_quy_tac_10_ngay_chuyen_cuong_che(self):
        self.qd()
        m = self.ma[0]
        van_dong.ghi_buoi(self.con, m, 'tien', _ngay(-10), 'Gặp trực tiếp', ket_qua='chua_dong_y')     # buổi đầu cách 10 ngày
        van_dong.ghi_buoi(self.con, m, 'tien', _ngay(-4), ket_qua='chua_dong_y')

        def tt(ngay_nay):
            return van_dong.tinh_trang_tat_ca(self.con, hom_nay=ngay_nay)[m][0]
        t = tt(HOM_NAY)
        self.assertEqual((t.ma, t.da_qua, t.con_lai, t.so_buoi), ('dang_van_dong', 10, 0, 2))   # đúng ngày thứ 10: chưa "quá"
        self.assertIn('hôm nay hết hạn 10 ngày', t.chu)                                  # trước đây "ngày 11/10, còn 0 ngày"
        self.assertIn('ngày 5/10, còn 6 ngày', tt(HOM_NAY - timedelta(days=6)).chu)
        t = tt(HOM_NAY + timedelta(days=1))
        self.assertEqual(t.ma, 'du_dk_cuong_che')                                        # ngày 11: quá 10 ngày
        self.assertEqual(t.chu, van_dong.CHU_CUONG_CHE)
        self.assertIn('Điều 89', t.chu)
        theo_doi.ghi_chi_tra(self.con, [(self.con.execute('SELECT qd_id FROM qd_ho WHERE ma_ho = ?', (m,)).fetchone()[0], m)],
                             _ngay(0))
        self.assertEqual(tt(HOM_NAY + timedelta(days=30)).ma, 'hoan_thanh')              # đã nhận tiền: hết áp dụng

    def test_so_ngay_van_dong_tu_cai_dat(self):
        self.qd()
        m = self.ma[1]
        van_dong.ghi_buoi(self.con, m, 'tien', _ngay(-6))
        self.assertEqual(van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)[m][0].ma, 'dang_van_dong')
        thoi_han.dat_so_ngay(self.con, dict(van_dong=5))                                 # rút còn 5 ngày: 6 > 5
        self.assertEqual(van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)[m][0].ma, 'du_dk_cuong_che')

    def test_dong_y_cho_thuc_hien_van_chuyen_neu_het_han(self):
        self.qd()
        m = self.ma[0]
        van_dong.ghi_buoi(self.con, m, 'tien', _ngay(-3), ket_qua='dong_y')
        t = van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)[m][0]
        self.assertEqual(t.ma, 'dang_van_dong')
        self.assertIn('đã đồng ý', t.chu)
        self.assertEqual(van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY + timedelta(days=20))[m][0].ma, 'du_dk_cuong_che')

    def test_viec_ap_dung_theo_trang_thai_ho(self):
        """Hộ chưa có quyết định: chưa áp dụng (buổi ghi trước vẫn hiện hoàn tất). Mặt bằng: chỉ khi chưa bàn giao."""
        m = self.ma[0]
        van_dong.ghi_buoi(self.con, m, 'mat_bang', _ngay(-20))
        t = van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)[m][0]
        self.assertEqual(t.ma, 'chua_ap_dung')                                           # chưa có QĐ -> không phải đối tượng cưỡng chế
        self.qd(ds=[m])
        self.assertEqual(van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)[m][0].ma, 'du_dk_cuong_che')
        theo_doi.ghi_ban_giao(self.con, [m], dict(da_ban_giao=1, ban_giao_ngay=_ngay(-1)))
        self.assertEqual(van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)[m][0].ma, 'hoan_thanh')

    def test_trang_thai_chung_va_danh_sach_cuong_che(self):
        self.qd()
        a, b = self.ma[0], self.ma[1]
        van_dong.ghi_buoi(self.con, a, 'tien', _ngay(-15), 'Họp tổ', ket_qua='vang_mat')
        van_dong.ghi_buoi(self.con, a, 'mat_bang', _ngay(-2))
        van_dong.ghi_buoi(self.con, b, 'tien', _ngay(-5))
        tt = van_dong.tinh_trang_tat_ca(self.con, hom_nay=HOM_NAY)
        ma, chu = van_dong.trang_thai_chung(tt[a])
        self.assertEqual(ma, 'du_dk_cuong_che')
        self.assertIn('không nhận tiền', chu)
        self.assertEqual(van_dong.trang_thai_chung(tt[b])[0], 'dang_van_dong')
        self.assertEqual(van_dong.trang_thai_chung([]), ('', ''))
        thoi_han.dat_ngay_thong_bao(self.con, _ngay(-70))
        ds = van_dong.ds_cuong_che(self.con, HOM_NAY)
        self.assertEqual([(d['ma_ho'], d['viec']) for d in ds], [(a, 'Không nhận tiền bồi thường')])
        self.assertEqual(ds[0]['qua_han'], 5)
        self.assertTrue(ds[0]['moc_thu_hoi'])
        f = van_dong.xuat_ds_cuong_che(self.con, self.td / 'cc.xlsx', HOM_NAY)
        import openpyxl
        ws = openpyxl.load_workbook(f).active
        tieu = [c.value for c in ws[4]]
        self.assertEqual(tieu, van_dong.COT_CUONG_CHE)
        self.assertEqual(ws.cell(5, 2).value, a)
        self.assertIn('CƯỠNG CHẾ', ws['A1'].value)

    def test_khong_co_ho_du_dieu_kien(self):
        with self.assertRaises(LoiNhap) as e:
            van_dong.xuat_ds_cuong_che(self.con, self.td / 'x.xlsx', HOM_NAY)
        self.assertIn('10 ngày', str(e.exception))
        self.assertFalse((self.td / 'x.xlsx').exists())

    def test_xoa_ho_xoa_nhat_ky_va_xoa_trang(self):
        self.qd()
        van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _ngay(-1))
        van_dong.ghi_buoi(self.con, self.ma[1], 'tien', _ngay(-1))
        from pabt import ho_so
        ho_so.xoa_nhieu_ho(self.con, [self.ma[0]])
        self.assertEqual({b['ma_ho'] for b in van_dong.ds_buoi(self.con)}, {self.ma[1]})      # xóa hộ: nhật ký đi theo (CASCADE)
        from pabt import nhap_tho
        with self.con:
            nhap_tho.xoa_trang(self.con)
        self.assertEqual(van_dong.ds_buoi(self.con), [])


class TestKinhPhi(_Co):
    def test_co_cau(self):
        self.qd()
        cc = kinh_phi_du_an.co_cau(self.con)
        dong = {d['loai'] + str(d['ma']): d for d in cc['dong']}
        self.assertEqual([d['loai'] for d in cc['dong']], ['nhom'] * 5 + ['cong', 'kinh_phi', 'phan_bo', 'phan_bo', 'tong'])   # 1.0.04: 85% / 15%
        ds = theo_doi.tong_hop(self.con)
        for m in range(1, 6):
            self.assertEqual(dong[f'nhom{m}']['tien_pa'], sum((x.muc_pa.get(m, KHONG) for x in ds), KHONG))
        cong = sum((d['tien_pa'] for d in cc['dong'] if d['loai'] == 'nhom'), KHONG)
        self.assertEqual(dong['cong0']['tien_pa'], cong)
        self.assertGreater(cong, 0)
        from pabt.lap_pa import kinh_phi_to_chuc
        from pabt.tien import lam_tron
        _, tl, _ = kinh_phi_to_chuc(self.con)
        self.assertEqual(dong['kinh_phi-1']['tien_pa'], lam_tron(cong * tl / 100, -3))
        self.assertEqual(dong['tong-2']['tien_pa'], cong + dong['kinh_phi-1']['tien_pa'])
        # V10: gốc 100% = cộng bồi thường (không phải tổng kinh phí): 5 nhóm cộng lại 100%, kinh phí tổ chức ĐÚNG 2,5% / 3,5%
        self.assertAlmostEqual(sum(d['ty_trong'] for d in cc['dong'] if d['loai'] == 'nhom'), 100.0, places=6)
        self.assertEqual(dong['cong0']['ty_trong'], 100.0)
        self.assertEqual(dong['kinh_phi-1']['ty_trong'], float(tl))
        self.assertEqual(dong['tong-2']['ty_trong'], 100.0 + float(tl))
        self.assertEqual(cc['so_ho'], 6)
        self.assertEqual(cc['so_ho_phe_duyet'], 4)
        # tiền phê duyệt từng nhóm = cộng qd_ho; chênh lệch = PA - phê duyệt (QĐ lập theo phương án hiện tại -> 0)
        self.assertEqual(dong['cong0']['tien_pd'], sum((D(x) for r in self.con.execute(
            'SELECT tien_dat, tien_tai_san, tien_cay, tien_ho_tro, tien_thuong FROM qd_ho') for x in r if str(x).strip()), KHONG))
        self.assertIsNone(dong['tong-2']['tien_pd'])
        # 4 hộ đã có quyết định lập theo phương án -> lệch 0; phương án của 2 hộ còn lại nằm ở "chưa phê duyệt"
        chua = [x for x in ds if not x.qd]
        self.assertEqual(len(chua), 2)
        for m in range(1, 6):
            self.assertEqual(dong[f'nhom{m}']['chenh'], KHONG)
            self.assertEqual(dong[f'nhom{m}']['chua_pd'], sum((x.muc_pa.get(m, KHONG) for x in chua), KHONG))
            self.assertEqual(dong[f'nhom{m}']['tien_pa'] - dong[f'nhom{m}']['chua_pd'], dong[f'nhom{m}']['tien_pd'])
        self.assertEqual(dong['cong0']['chua_pd'], sum((x.tong_pa for x in chua), KHONG))

    def test_kinh_phi_theo_loai_du_an(self):
        from pabt.lap_pa import luu_kinh_phi_to_chuc
        luu_kinh_phi_to_chuc(self.con, 'tuyen', '3.5')
        a = kinh_phi_du_an.co_cau(self.con)
        luu_kinh_phi_to_chuc(self.con, 'khac', '2.5')
        b = kinh_phi_du_an.co_cau(self.con)
        self.assertEqual(a['cong'], b['cong'])
        self.assertEqual((a['tl_kp'], b['tl_kp']), (D('3.5'), D('2.5')))
        self.assertGreater(a['kinh_phi'], b['kinh_phi'])
        self.assertIn('2,5%', b['dong'][6]['ten'])

    def test_doi_soat_khai_toan(self):
        from pabt import du_toan
        thuc = du_toan.tu_du_an(self.con)
        goc = du_toan.DuToan(ten='Khái toán', dong=[du_toan.DongDT(d.muc, d.ten, d.dvt, d.khoi_luong, d.don_gia, d.he_so, d.ma)
                                                    for d in thuc.dong])
        ss = kinh_phi_du_an.doi_soat(self.con, goc)
        self.assertFalse(ss['vuot'])
        self.assertEqual(ss['tong'][2], KHONG)
        goc.dong = [du_toan.DongDT(d.muc, d.ten, d.dvt, d.khoi_luong, d.don_gia / 2, d.he_so) for d in goc.dong]    # khái toán thấp
        ss = kinh_phi_du_an.doi_soat(self.con, goc)
        self.assertTrue(ss['vuot'])
        self.assertGreater(ss['tong'][2], 0)
        f = goc.luu(self.td / 'kt')
        kinh_phi_du_an.dat_file_khai_toan(self.con, f)
        self.assertEqual(kinh_phi_du_an.file_khai_toan(self.con), str(f))
        self.assertEqual(kinh_phi_du_an.mo_khai_toan(f).ten, 'Khái toán')
        with self.assertRaises(LoiNhap):
            kinh_phi_du_an.mo_khai_toan(self.td / 'khong_co.pabtdt')
        (self.td / 'hong.pabtdt').write_text('không phải json', encoding='utf-8')
        with self.assertRaises(LoiNhap):
            kinh_phi_du_an.mo_khai_toan(self.td / 'hong.pabtdt')


class TestBaoCaoGPMB(_Co):
    def test_chi_so_giai_ngan_va_mat_bang(self):
        q = self.qd()
        tq = bao_cao_gpmb.tong_quan(self.con, HOM_NAY)
        self.assertEqual((tq['so_ho'], tq['so_ho_phe_duyet'], tq['so_ho_chua_pd']), (6, 4, 2))
        self.assertEqual(tq['pt_giai_ngan'], 0.0)
        self.assertGreater(tq['tong_pd'], 0)
        theo_doi.ghi_chi_tra(self.con, [(q, self.ma[0]), (q, self.ma[1])], _ngay(-1))
        theo_doi.ghi_ban_giao(self.con, [self.ma[0]], dict(da_ban_giao=1, ban_giao_ngay=_ngay(-1)))
        tq = bao_cao_gpmb.tong_quan(self.con, HOM_NAY)
        tong = sum((D(r[0]) for r in self.con.execute('SELECT so_tien FROM qd_ho')), KHONG)
        da = sum((D(r[0]) for r in self.con.execute('SELECT so_tien FROM qd_ho WHERE da_chi_tra = 1')), KHONG)
        self.assertEqual((tq['tong_pd'], tq['da_chi']), (tong, da))
        self.assertAlmostEqual(tq['pt_giai_ngan'], float(da * 100 / tong), places=6)
        dt_tong = sum((D(r[0]) for r in self.con.execute('SELECT dt_thu_hoi FROM thua')), KHONG)
        dt_bg = sum((D(r[0]) for r in self.con.execute('SELECT dt_thu_hoi FROM thua WHERE ma_ho = ?', (self.ma[0],))), KHONG)
        self.assertEqual((tq['dt_tong'], tq['dt_ban_giao']), (dt_tong, dt_bg))
        self.assertAlmostEqual(tq['pt_mat_bang'], float(dt_bg * 100 / dt_tong), places=6)
        self.assertEqual(tq['so_ho_nhan_du'], 2)
        self.assertEqual(tq['so_ho_ban_giao'], 1)

    def test_thua_chua_ban_giao_va_muc_uu_tien(self):
        q = self.qd()                                                                    # 4 hộ đã phê duyệt
        a, b, c = self.ma[0], self.ma[1], self.ma[2]
        theo_doi.ghi_chi_tra(self.con, [(q, a), (q, b)], _ngay(-1))                      # a, b nhận đủ tiền
        theo_doi.ghi_ban_giao(self.con, [a], dict(da_ban_giao=1, ban_giao_ngay=_ngay(-1)))   # a đã bàn giao (có ngày biên bản)
        van_dong.ghi_buoi(self.con, c, 'tien', _ngay(-12))                               # c: vận động quá 10 ngày
        with self.con:                                                                   # b cùng tờ bản đồ với a (thửa bị bao quanh)
            self.con.execute('UPDATE thua SET so_to = (SELECT so_to FROM thua WHERE ma_ho = ? LIMIT 1) WHERE ma_ho = ?', (a, b))
        tq = bao_cao_gpmb.tong_quan(self.con, HOM_NAY)
        thua = {(r['ma_ho']): r for r in tq['thua']}
        self.assertNotIn(a, thua)                                                        # đã bàn giao: không còn vướng
        self.assertNotIn(self.ma[4], thua)                                               # chưa phê duyệt: chưa tính
        self.assertEqual(thua[b]['muc'], 'gap')                                          # nhận đủ tiền, cùng tờ đã giải tỏa
        self.assertIn('thửa đã giải tỏa', thua[b]['cung_to'])
        self.assertEqual((thua[c]['muc'], thua[c]['ma_van_dong']), ('gap', 'du_dk_cuong_che'))
        self.assertEqual(thua[self.ma[3]]['muc'], 'theo_doi')
        thu_tu = [r['muc'] for r in tq['thua']]
        self.assertEqual(thu_tu, sorted(thu_tu, key=bao_cao_gpmb.MUC.index))             # gấp trước, theo dõi sau
        self.assertEqual(tq['so_ho_cuong_che'], 1)
        self.assertEqual(sum(tq['dem'].values()), len(tq['thua']))
        f = bao_cao_gpmb.xuat_excel(self.con, self.td / 'bc.xlsx', HOM_NAY)
        import openpyxl
        ws = openpyxl.load_workbook(f).active
        self.assertIn('giải ngân', ws['A1'].value)
        self.assertEqual(ws.cell(5, 2).value, 'Gấp')


class TestNiemYetXong(_Co):
    def _dot_niem_yet(self, bat_dau_lui: int, ds=None, ten='Niêm yết 1'):
        for m in ds or self.ma[:3]:
            du_thao.ghi_phap_ly(self.con, m, 1, '', '')
        d = du_thao.tao_dot(self.con, ten, _ngay(-bat_dau_lui), 'Nhà văn hóa ấp')
        du_thao.dua_ho_vao_dot(self.con, d, ds or self.ma[:3])
        return d

    def test_chi_lay_ho_het_han_niem_yet(self):
        d = self._dot_niem_yet(4)                                                        # mới niêm yết 4 ngày (10 ngày mới xong)
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, HOM_NAY), [])
        self.assertEqual(du_thao.dot_niem_yet_xong(self.con, HOM_NAY), [])
        nay = HOM_NAY + timedelta(days=6)                                                # đúng ngày kết thúc
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, nay), self.ma[:3])
        ds = du_thao.dot_niem_yet_xong(self.con, nay)
        self.assertEqual((ds[0]['id'], ds[0]['so_ho'], ds[0]['so_dong_y']), (d, 3, 0))
        du_thao.ghi_y_kien(self.con, d, self.ma[0], 'dong_y', '', '')
        du_thao.ghi_y_kien(self.con, d, self.ma[1], 'khong_dong_y', 'gia_dat', 'Giá thấp')
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, nay, chi_dong_y=True), [self.ma[0]])
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, nay, dot_id=d), self.ma[:3])
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, nay, dot_id=d + 99), [])
        self.assertEqual(du_thao.dot_niem_yet_xong(self.con, nay)[0]['so_dong_y'], 1)

    def test_bo_ho_vuong_phap_ly(self):
        d = self._dot_niem_yet(20)
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, HOM_NAY), self.ma[:3])
        with self.con:
            self.con.execute("UPDATE ho SET ma_vuong = 'V2' WHERE ma_ho = ?", (self.ma[1],))
        self.assertEqual(du_thao.ho_niem_yet_xong(self.con, HOM_NAY), [self.ma[0], self.ma[2]])
        self.assertEqual(du_thao.dot_niem_yet_xong(self.con, HOM_NAY)[0]['so_ho'], 2)
        self.assertIsNotNone(d)


class TestBaoCaoYKien(_Co):
    def _chuan_bi(self):
        for m in self.ma[:3]:
            du_thao.ghi_phap_ly(self.con, m, 1, '', '')
        d = du_thao.tao_dot(self.con, 'Niêm yết đợt 1', _ngay(-20), 'Nhà văn hóa ấp 1')
        du_thao.dua_ho_vao_dot(self.con, d, self.ma[:3])
        du_thao.ghi_y_kien(self.con, d, self.ma[0], 'dong_y', '', '')
        du_thao.ghi_y_kien(self.con, d, self.ma[1], 'khong_dong_y', 'gia_dat', 'Đề nghị tăng đơn giá đất ở', huong='Giải trình theo bảng giá')
        du_thao.ghi_doi_thoai(self.con, d, self.ma[1], _ngay(-8), 'UBND xã', 'Đã giải thích căn cứ bảng giá, hộ đồng ý')
        du_thao.ghi_y_kien(self.con, d, self.ma[1], 'dong_y', 'gia_dat', 'Đề nghị tăng đơn giá đất ở', huong='Giải trình theo bảng giá',
                           ket_qua='Đã giải thích căn cứ bảng giá, hộ đồng ý')
        du_thao.ghi_y_kien(self.con, d, self.ma[2], 'y_kien_khac', 'cay', 'Kê khai thiếu cây ăn trái')
        return d

    def test_thu_thap(self):
        self._chuan_bi()
        tt = bao_cao_y_kien.thu_thap(self.con, self.ma[:4])
        self.assertEqual(tt['so_ho'], 4)
        self.assertEqual(tt['dem'], dict(chua=1, dong_y=2, y_kien_khac=1, khong_dong_y=0))
        self.assertEqual(tt['so_ho_co_y_kien'], 3)
        self.assertEqual([k['ma_ho'] for k in tt['kien_nghi']], [self.ma[1], self.ma[2]])
        self.assertTrue(tt['kien_nghi'][0]['da_dong_thuan'])
        self.assertFalse(tt['kien_nghi'][1]['da_dong_thuan'])
        self.assertEqual(tt['nhom'], {'Đơn giá đất': [1, 1], 'Cây trồng, mật độ': [1, 0]})
        self.assertEqual(len(tt['dot_ny']), 1)

    def test_ghi_docx(self):
        self._chuan_bi()
        f = bao_cao_y_kien.ghi_docx(self.con, self.ma[:4], self.td / 'bc.docx')
        with zipfile.ZipFile(f) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        for chu in ('BÁO CÁO', 'Kết quả niêm yết công khai', 'Niêm yết đợt 1', 'Nhà văn hóa ấp 1', 'Kết quả lấy ý kiến',
                    'Đồng ý với dự thảo phương án', 'Đề nghị tăng đơn giá đất ở', 'Kê khai thiếu cây ăn trái', 'Đã đồng thuận',
                    'Chưa đồng thuận', 'Kết luận, đề nghị', '50,0'):                    # 2/4 hộ đồng ý
            self.assertIn(chu, xml)
        self.assertNotRegex(xml, r'\{[A-Za-z_]+\}')                                      # mọi chỗ trống đã điền
        self.assertIn('Thử', xml)                                                        # tên dự án

    def test_khong_co_y_kien(self):
        f = bao_cao_y_kien.ghi_docx(self.con, self.ma[:2], self.td / 'bc2.docx')
        xml = zipfile.ZipFile(f).read('word/document.xml').decode('utf-8')
        self.assertIn('chưa được đưa vào đợt niêm yết', xml)
        self.assertIn('Không có hộ nào kiến nghị', xml)

    def test_xuat_dot_kem_bao_cao(self):
        self._chuan_bi()
        dot = quan_ly.tao_dot(self.con, 'Đợt trình 1', _ngay(-3), '77/TTr')
        quan_ly.gan_dot(self.con, self.ma[:3], dot)
        kq = quan_ly.xuat_dot(self.con, dot, self.td / 'hs', chi_tiet=False, bang_tong_hop=False, to_trinh=False, bao_cao_y_kien=True)
        f = Path(kq['thu_muc']) / 'PA TONG' / bao_cao_y_kien.TEN_FILE
        self.assertTrue(f.exists())
        self.assertIn(f, kq['word'])
        kq = quan_ly.xuat_dot(self.con, dot, self.td / 'hs2', chi_tiet=False, bang_tong_hop=False)
        self.assertFalse((Path(kq['thu_muc']) / 'PA TONG' / bao_cao_y_kien.TEN_FILE).exists())      # không chọn: không tạo

    def test_kiem_tra_xuat_dot(self):
        self._chuan_bi()
        dot = quan_ly.tao_dot(self.con, 'Đợt trình 2')
        self.assertFalse(quan_ly.kiem_tra_xuat_dot(self.con, dot)[0][0])                 # chưa có hộ
        quan_ly.gan_dot(self.con, self.ma[:4], dot)
        kt = quan_ly.kiem_tra_xuat_dot(self.con, dot)
        self.assertTrue(kt[0][0])
        self.assertEqual([x[0] for x in kt[1:]], [None, None, None, None])               # chưa số PA, tờ trình, PA tổng; ý kiến 3/4
        self.assertIn('3/4', kt[4][1])
        quan_ly.danh_so_pa(self.con, self.ma[:4], 1)
        quan_ly.sua_dot(self.con, dot, 'Đợt trình 2', '01/10/2026', '55/TTr', so_pa_tong='9')
        kt = quan_ly.kiem_tra_xuat_dot(self.con, dot)
        self.assertEqual([x[0] for x in kt[:4]], [True, True, True, True])


def _qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _hn(n: int) -> str:
    """Ngày cách NGÀY THẬT hôm nay n ngày (giao diện tính theo ngày thật, không có tham số hom_nay)."""
    return (date.today() + timedelta(days=n)).strftime('%d/%m/%Y')


class TestTheoDoiVanDongGiaoDien(_Co):
    def _khung(self):
        _qt()
        from pabt.man_hinh_theo_doi import KhungTienDo
        k = KhungTienDo(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        return k

    def test_cot_moc_thu_hoi_va_van_dong(self):
        self.qd()
        thoi_han.dat_ngay_thong_bao(self.con, _hn(-70))
        van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _hn(-12))
        van_dong.ghi_buoi(self.con, self.ma[1], 'tien', _hn(-3))
        k = self._khung()
        self.assertEqual(len(k.COT), 17)                                    # 0.9.96: + Hoàn tất CTBT, Hồ sơ scan (cuối bảng)
        self.assertIn('Mốc thu hồi đất', k.COT[k.C_MOC])
        self.assertEqual(k.C_MOC, 4)                                        # ngay sau Địa chỉ: thấy được không cần cuộn ngang
        self.assertIn('Vận động', k.COT[k.C_VD])
        hang = {k.bang.ma_dong(r): r for r in range(k.bang.rowCount())}
        loai = {m: thoi_han.nhom_dat_ho([r[0] for r in self.con.execute('SELECT loai_dat FROM thua WHERE ma_ho = ?', (m,))])
                for m in self.ma}
        for m in self.ma[:4]:                                              # hộ có quyết định: có chữ mốc đủ / chưa đủ
            chu = k.bang.item(hang[m], k.C_MOC).text()
            self.assertTrue(chu.startswith('Đủ mốc' if loai[m] == 'nn' else 'Chưa đủ mốc'), (m, loai[m], chu))
        for m in self.ma[4:]:
            self.assertEqual(k.bang.item(hang[m], k.C_MOC).text(), '')      # hộ chưa có quyết định: để trống
        self.assertEqual(k.bang.item(hang[self.ma[0]], k.C_VD).text().split(' (')[0], van_dong.CHU_CUONG_CHE)
        self.assertIn('Đang vận động', k.bang.item(hang[self.ma[1]], k.C_VD).text())
        self.assertEqual(k.bang.item(hang[self.ma[2]], k.C_VD).text(), '')
        # lọc theo vận động; ô Lọc ghi số hộ từng điều kiện
        k.dat_loc('du_cuong_che')
        self.assertEqual(k.dang_hien, [self.ma[0]])
        k.dat_loc('dang_vd')
        self.assertEqual(k.dang_hien, [self.ma[1]])
        ten = [k.cb_loc.itemText(i) for i in range(k.cb_loc.count())]
        self.assertTrue(any(t.startswith('Đủ điều kiện cưỡng chế') and t.endswith('(1)') for t in ten), ten)
        k.dat_loc('')
        self.assertEqual(len(k.dang_hien), 6)
        f = k.xuat(self.td / 'td.xlsx')
        ws = __import__('openpyxl').load_workbook(f).active
        self.assertEqual(ws.cell(4, k.C_MOC + 1).value.replace('\n', ' '), k.COT[k.C_MOC].replace('\n', ' '))

    def test_ngay_thong_bao_va_moc_thoi_han(self):
        self.qd()
        k = self._khung()
        self.assertIn('chưa nhập ngày thông báo', k.lb_moc.text())
        self.assertIsNone(k.luu_ngay_thong_bao('31/02/2026'))               # sai ngày: báo, không ghi
        self.assertIsNone(thoi_han.ngay_thong_bao(self.con))
        self.assertEqual(k.luu_ngay_thong_bao(_hn(-130)), _hn(-130))
        self.assertNotIn('chưa nhập ngày thông báo', k.lb_moc.text())
        self.assertIn(f'{thoi_han.so_ngay(self.con, "thu_hoi_nn")} ngày', k.lb_moc.text())
        self.assertIn('4/4', k.lb_moc.text())                              # 130 ngày: mọi hộ có quyết định đều đủ mốc 60 / 120
        self.assertTrue(k.mo_moc(dict(thu_hoi_pnn=200)))
        self.assertNotIn('4/4', k.lb_moc.text())
        van_dong.ghi_buoi(self.con, self.ma[1], 'tien', _hn(-3))
        self.assertTrue(k.mo_moc(dict(van_dong=2)))                         # rút thời hạn vận động: hộ vận động 3 ngày thành cưỡng chế
        k.dat_loc('du_cuong_che')
        self.assertEqual(k.dang_hien, [self.ma[1]])
        k.chi_doc = True
        self.assertIsNone(k.luu_ngay_thong_bao(_hn(0)))                     # chỉ xem: không ghi
        self.assertFalse(k.mo_moc(dict(van_dong=9)))

    def test_xuat_ds_cuong_che(self):
        self.qd()
        k = self._khung()
        self.assertIsNone(k.xuat_cuong_che(self.td / 'cc0.xlsx'))           # chưa hộ nào đủ điều kiện: báo, không tạo file
        self.assertFalse((self.td / 'cc0.xlsx').exists())
        van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _hn(-15))
        k.nap()
        f = k.xuat_cuong_che(self.td / 'cc1.xlsx')
        ws = __import__('openpyxl').load_workbook(f).active
        self.assertEqual(ws.cell(5, 2).value, self.ma[0])

    def test_so_nhat_ky_van_dong(self):
        from pabt.man_hinh_theo_doi import HopNhatKyVanDong
        self.qd()
        k = self._khung()
        d = k.so_van_dong(self.ma[0])
        self.addCleanup(d.close)
        self.assertEqual(d.ma_ho(), self.ma[0])
        self.assertEqual(d.bang.rowCount(), 0)
        self.assertIn('chưa có buổi', d.lb_tt.text())
        d.o_ngay.setText(_hn(-14))
        d.o_noi_dung.setPlainText('Mời hộ nhận tiền, hộ chưa đồng ý')
        i = d.them()
        self.assertEqual(d.bang.rowCount(), 1)
        self.assertEqual(d.bang.item(0, 5).text(), 'Chưa đồng ý')
        self.assertIn('Điều 89', d.lb_tt.text())                            # 14 ngày > 10: đủ điều kiện cưỡng chế
        self.assertTrue(d.thay_doi)
        d.o_ngay.setText('')
        self.assertIsNone(d.them())                                         # thiếu ngày: báo, không ghi
        self.assertEqual(len(van_dong.ds_buoi(self.con, self.ma[0])), 1)
        d.o_ngay.setText(_hn(-2))
        d.cb_viec.setCurrentIndex(d.cb_viec.findData('mat_bang'))
        j = d.them()
        self.assertEqual(d.bang.rowCount(), 2)
        d.bang.selectRow(0)                                                 # chọn buổi: đưa lên biểu mẫu
        self.assertEqual(d.o_ngay.text(), _hn(-14))
        d.cb_ket_qua.setCurrentIndex(d.cb_ket_qua.findData('dong_y'))
        self.assertEqual(d.sua(), i)
        self.assertEqual([b['ket_qua'] for b in van_dong.ds_buoi(self.con, self.ma[0], 'tien')], ['dong_y'])
        self.assertEqual(d.xoa(xac_nhan=False, buoi_id=j), 0)
        self.assertEqual(d.xoa(xac_nhan=True, buoi_id=j), 1)
        self.assertEqual(d.bang.rowCount(), 1)
        d.chon_ho(self.ma[5])                                               # hộ chưa có quyết định
        self.assertEqual(d.bang.rowCount(), 0)
        self.assertIn('không cần vận động', d.lb_tt.text())
        d2 = HopNhatKyVanDong(self.con, self.ma[0], None, chi_doc=True)
        self.addCleanup(d2.close)
        self.assertFalse(any(b.isEnabled() for b in d2.nut.values()))      # chỉ xem: không ghi nhật ký

    def test_hop_moc_thoi_han(self):
        _qt()
        from pabt.man_hinh_theo_doi import HopMocThoiHan
        h = HopMocThoiHan(self.con)
        self.addCleanup(h.close)
        self.assertEqual(h.gia_tri(), dict(tham_dinh=15, thu_hoi_nn=60, thu_hoi_pnn=120, van_dong=10))
        h.o['tham_dinh'].setValue(21)
        thoi_han.dat_so_ngay(self.con, h.gia_tri())
        self.assertEqual(HopMocThoiHan(self.con).gia_tri()['tham_dinh'], 21)


class TestBangTongHopVaBaoCaoGiaoDien(_Co):
    def test_doi_soat_khai_toan(self):
        _qt()
        from pabt import du_toan
        from pabt.man_hinh_theo_doi import KhungDoiSoat
        k = KhungDoiSoat(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        self.assertIsNone(k.ss)
        self.assertEqual(k.bang.rowCount(), 0)
        self.assertFalse(k.nut['Dùng bảng khái toán đang mở'].isEnabled())    # chưa gắn bảng khái toán đang mở
        self.assertIsNone(k.dung_dang_mo())
        thuc = du_toan.tu_du_an(self.con)
        goc = du_toan.DuToan(ten='KT', dong=[du_toan.DongDT(d.muc, d.ten, d.dvt, d.khoi_luong, d.don_gia / 2, d.he_so)
                                              for d in thuc.dong])
        k.nguon_dang_mo = lambda: goc
        self.assertIsNotNone(k.dung_dang_mo())
        self.assertTrue(k.ss['vuot'])
        self.assertEqual(k.bang.rowCount(), len(k.ss['dong']) + 1)         # từng mục + dòng tổng
        self.assertIn('VƯỢT', k.lb_kq.text())
        f = k.xuat(self.td / 'ds.xlsx')
        self.assertIn('ĐỐI SOÁT', __import__('openpyxl').load_workbook(f).active['A1'].value)
        goc.luu(self.td / 'g')
        k2 = KhungDoiSoat(self.con)
        k2.im_lang = True
        self.addCleanup(k2.close)
        self.assertIsNotNone(k2.chon_file(self.td / 'g.pabtdt'))           # chọn file: nhớ cho dự án
        k3 = KhungDoiSoat(self.con)
        k3.im_lang = True
        self.addCleanup(k3.close)
        k3.nap()                                                            # mở lại: tự nạp file đã chọn
        self.assertIsNotNone(k3.ss)
        self.assertIn('g.pabtdt', k3.lb_nguon.text())
        self.assertIsNone(k3.chon_file(self.td / 'khong_co.pabtdt'))        # file hỏng: báo, giữ nguồn cũ
        self.assertIn('g.pabtdt', k3.lb_nguon.text())

    def test_tien_do_tong_quan_the_va_thua_con_vuong(self):
        """1.0.00: bảng điều hành (thẻ chỉ số + thửa còn vướng) nằm trong trang Tiến độ chi trả & Bàn giao (KhungTienDo)."""
        _qt()
        from pabt.man_hinh_bao_cao import KHONG_SO
        from pabt.man_hinh_theo_doi import KhungTienDo
        k = KhungTienDo(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        self.assertEqual(k.kpi.the['giai_ngan'].lb_so.text(), KHONG_SO)      # chưa có quyết định: "—", không phải "0,0%"
        self.assertIn('Chưa có hộ nào được phê duyệt', k.thua.chu_trong())
        self.assertIs(k.thua.ngan.currentWidget(), k.thua.lb_trong)         # bảng trống: lời giải thích thay chỗ bảng
        q = self.qd()
        k.nap()
        self.assertEqual(k.kpi.the['giai_ngan'].lb_so.text(), '0 hộ (0,0%)')     # 20/10/2026: "n hộ (x%)" trên tổng số hộ
        b = k.thua.bang
        so_thua_4_ho = sum(self.con.execute('SELECT COUNT(*) FROM thua WHERE ma_ho = ?', (m,)).fetchone()[0] for m in self.ma[:4])
        self.assertEqual(b.rowCount(), so_thua_4_ho)                        # mỗi THỬA một dòng: 4 hộ đã phê duyệt, chưa nhận tiền
        self.assertEqual(k.tq['dem'], dict(gap=0, cao=0, theo_doi=so_thua_4_ho))        # đều "theo dõi"
        self.assertIsNone(k.xuat_cuong_che(self.td / 'x.xlsx'))             # chưa hộ nào đủ điều kiện cưỡng chế
        theo_doi.ghi_chi_tra(self.con, [(q, self.ma[0]), (q, self.ma[1])], _hn(-1))
        theo_doi.ghi_ban_giao(self.con, [self.ma[0]], dict(da_ban_giao=1, ban_giao_ngay=_hn(-1)))
        van_dong.ghi_buoi(self.con, self.ma[2], 'tien', _hn(-20))
        k.nap()
        self.assertTrue(k.kpi.the['giai_ngan'].lb_so.text().endswith('%)'))
        self.assertNotEqual(k.kpi.the['giai_ngan'].lb_so.text(), '0 hộ (0,0%)')
        self.assertNotEqual(k.kpi.the['mat_bang'].lb_so.text(), '0 hộ (0,0%)')
        self.assertTrue(k.kpi.the['cuong_che'].lb_so.text().startswith('1 hộ'))
        self.assertIn('Giải ngân', k.kpi.the['giai_ngan'].lb_phu.text())
        self.assertEqual(k.kpi.the['giai_ngan'].thanh.value(), int(k.tq['so_ho_nhan_du'] * 100 / k.tq['so_ho'] * 10))
        tong_thua = len(k.tq['thua'])
        self.assertEqual(b.rowCount(), tong_thua)
        self.assertEqual(b.item(0, 0).text(), 'Gấp')                        # gấp lên đầu
        k.thua.cb_muc.setCurrentIndex(k.thua.cb_muc.findData('theo_doi'))
        self.assertEqual(b.rowCount(), k.tq['dem']['theo_doi'])
        self.assertIn(f'/{tong_thua} thửa', k.thua.lb_dem.text())
        self.assertTrue(k.xuat_bao_cao(self.td / 'bc.xlsx').exists())
        f2 = k.xuat_cuong_che(self.td / 'cc.xlsx')
        self.assertEqual(__import__('openpyxl').load_workbook(f2).active.cell(5, 2).value, self.ma[2])
        k.con = None
        k.nap()
        self.assertEqual(k.thua.bang.rowCount(), 0)


class TestDotTrinhGiaoDien(_Co):
    def _hop(self):
        _qt()
        from pabt.man_hinh_quan_ly import HopDotTrinh
        d = HopDotTrinh(self.con, None, self.ma[:3], self.p)
        d.im_lang = True
        self.addCleanup(d.close)
        return d

    def test_bo_cuc_hai_cot_va_mot_nut_xuat_ban(self):
        from PySide6.QtWidgets import QSplitter
        d = self._hop()
        tach = d.findChildren(QSplitter)[0]
        self.assertEqual(tach.count(), 2)
        self.assertTrue(tach.widget(0).isAncestorOf(d.bang_dot) and tach.widget(0).isAncestorOf(d.lb_mau['to_trinh']))
        self.assertTrue(tach.widget(0).isAncestorOf(d.lb_han))
        self.assertTrue(tach.widget(1).isAncestorOf(d.bang_ho) and tach.widget(1).isAncestorOf(d.b_so))
        self.assertTrue(tach.widget(1).isAncestorOf(d.b_niem_yet))
        # V10: bỏ khối xuất file dưới đáy; chân trang chỉ có MỘT nút mở Trung tâm Xuất bản (ngoài hai cột)
        for ten in ('o_tt', 'o_bth', 'o_ct', 'o_bc', 'o_pdf'):
            self.assertFalse(hasattr(d, ten), ten)
        self.assertFalse(tach.isAncestorOf(d.b_xuat))
        self.assertEqual(d.b_xuat.text(), 'Xuất bản hồ sơ đợt này  →')
        from PySide6.QtWidgets import QGroupBox
        self.assertEqual([g.title() for g in d.findChildren(QGroupBox)], ['Tờ trình thẩm định (mẫu Word / Excel)'])

    def test_dem_nguoc_tham_dinh(self):
        d = self._hop()
        d.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        self.assertIn('chưa có ngày trình', d.lb_han.text())
        self.assertEqual(d.han['muc'], 'chua_trinh')
        for lui, muc, chu in ((5, 'con_han', 'Còn 10 / 15 ngày'), (13, 'sap_het', 'Còn 2 / 15 ngày'), (20, 'qua_han', 'QUÁ HẠN 5 ngày')):
            d.sua_dot(dict(ten='Đợt 1', ngay_trinh=_hn(-lui), so_to_trinh='1/TTr', ghi_chu='', loai_van_ban='Tờ trình',
                           so_pa_tong='', ngay_pa_tong=''))
            self.assertEqual((d.han['muc'], chu in d.lb_han.text()), (muc, True), (lui, d.lb_han.text()))
            self.assertIn('Khoản 8 Mục IV QĐ 18', d.lb_han.text())
        d.bang_dot.selectRow(d.bang_dot.rowCount() - 1)                     # dòng "(Chưa xếp đợt)": không có hạn
        self.assertIn('Chọn một đợt', d.lb_han.text())

    def test_lay_ho_da_niem_yet_xong(self):
        d = self._hop()
        self.assertEqual(d.lay_ho_niem_yet(), 0)                            # chưa chọn đợt trình: báo
        d.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        d._dung_menu_niem_yet()
        self.assertEqual([a.isEnabled() for a in d.menu_ny.actions()], [False])      # chưa có đợt niêm yết nào hết hạn
        self.assertEqual(d.lay_ho_niem_yet(), 0)
        for m in self.ma[:3]:
            du_thao.ghi_phap_ly(self.con, m, 1, '', '')
        ny = du_thao.tao_dot(self.con, 'Niêm yết 1', _hn(-20), 'Nhà văn hóa')
        du_thao.dua_ho_vao_dot(self.con, ny, self.ma[:3])
        du_thao.ghi_y_kien(self.con, ny, self.ma[0], 'dong_y', '', '')
        d._dung_menu_niem_yet()
        chu = [a.text() for a in d.menu_ny.actions() if not a.isSeparator()]
        self.assertEqual(chu[0], 'Tất cả hộ đã niêm yết xong (3 hộ)')
        self.assertEqual(chu[1], 'Chỉ hộ đã đồng thuận (1 hộ)')
        self.assertIn('Niêm yết 1', chu[2])
        self.assertEqual(d.lay_ho_niem_yet('dong_y'), 1)
        self.assertEqual(d.ho_hien, [self.ma[0]])
        self.assertEqual(d.lay_ho_niem_yet('tat_ca'), 2)                    # bỏ qua hộ đã ở trong đợt
        self.assertEqual(sorted(d.ho_hien), sorted(self.ma[:3]))
        self.assertEqual(d.lay_ho_niem_yet('tat_ca'), 0)
        self.assertEqual(d.lay_ho_niem_yet('dot', ny), 0)

    def test_kiem_tra_ho_so_va_chuyen_sang_trung_tam_xuat_ban(self):
        d = self._hop()
        d.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        d.dua_vao()
        self.assertEqual(len(d.kiem), 5)
        self.assertIsNone(d.kiem[1][0])
        self.assertIn('đạt 1/5', d.lb_kiem.text())
        self.assertIn('[Xem lại]', d.lb_kiem.toolTip())
        d.danh_so(1, _hn(0))
        d.sua_dot(dict(ten='Đợt 1', ngay_trinh=_hn(-1), so_to_trinh='9/TTr', ghi_chu='', loai_van_ban='Tờ trình', so_pa_tong='3',
                       ngay_pa_tong=_hn(-1)))
        self.assertEqual([x[0] for x in d.kiem[:4]], [True, True, True, True])
        self.assertIn('đạt 4/5', d.lb_kiem.text())
        self.assertIsNone(d.mo_xuat_dot)
        dot = d.dot_chon()
        self.assertEqual(d.xuat_ban(), dot)                                 # đóng hộp, cửa sổ chính mở Trung tâm Xuất bản
        self.assertEqual(d.mo_xuat_dot, dot)

    def test_xuat_ban_chua_chon_dot(self):
        d = self._hop()
        d.bang_dot.selectRow(d.bang_dot.rowCount() - 1)                     # dòng "(Chưa xếp đợt)"
        self.assertIsNone(d.xuat_ban())
        self.assertIsNone(d.mo_xuat_dot)


class TestCuaSoChinhNhom56(_Co):
    def _cua_so(self):
        _qt()
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(self.p))
        return ud, w

    def test_cau_truc_trang(self):
        ud, w = self._cua_so()
        # 1.0.00: "Báo cáo tiến độ GPMB" gộp vào "Tiến độ chi trả & Bàn giao" - 5 trang, Ctrl+1..5
        self.assertEqual(ud.TRANG, ['Danh sách hộ', 'Tổng hợp tiền theo phương án', 'Quyết định phê duyệt', 'Theo dõi tiến độ',
                                    'Dự toán & khái toán'])
        self.assertEqual(ud.TRANG_DU_TOAN, 4)
        self.assertEqual(w.trang.count(), 6)
        self.assertNotIn('Báo cáo tổng hợp…', w.lenh)
        self.assertFalse(hasattr(w, 'bao_cao'))
        for i, t in enumerate(ud.TRANG[:4]):
            w.lenh[t].trigger()
            _qt().processEvents()
            self.assertEqual(w.trang.currentIndex(), ud.STACK_CUA_TRANG[i], t)
            self.assertEqual([k for k, x in enumerate(ud.TRANG) if w.lenh[x].isChecked()], [i])
            # 20/10/2026: phím số theo PHIM_NHANH (Tổng hợp tiền / Quyết định không có phím số)
            self.assertEqual(w.lenh[t].shortcut().toString(), dict(ud.PHIM_NHANH).get(t, ''))
        self.assertIs(w._khung_dang_xem(), w.tien_do)
        self.assertEqual(w.lb_trang.text(), 'Tiến độ chi trả && Bàn giao')  # 1.0.42 Title Case, hiện &
        from pabt.man_hinh_bao_cao import KHONG_SO
        self.assertEqual(w.tien_do.kpi.the['giai_ngan'].lb_so.text(), KHONG_SO)

    def test_lien_ket_giua_cac_trang_va_dong_du_an(self):
        ud, w = self._cua_so()
        w.mo_trang(ud.TRANG_THEO_DOI)
        w.tien_do.dat_che_do('thua')                                        # nút chế độ "Thửa còn vướng"
        self.assertEqual(w.tien_do.che_do(), 'thua')
        w.tien_do.bam_kpi('cuong_che')                                      # thẻ cưỡng chế: về Theo hộ, lọc hộ đủ điều kiện
        self.assertEqual((w.tien_do.che_do(), w.tien_do.cb_loc.currentData()), ('ho', 'du_cuong_che'))
        self.assertIsNone(w.bang_tong_hop.doi_soat.nguon_dang_mo())         # chưa mở trang khái toán: chưa có bảng đang mở
        k = w.du_toan(cho=False)
        from pabt import du_toan
        k.dt = du_toan.tu_du_an(self.con)
        self.assertIs(w._khai_toan_dang_mo(), k.dt)
        w.mo_trang(ud.TRANG_TONG_HOP)
        w.bang_tong_hop.tab.setCurrentIndex(2)
        self.assertIsNotNone(w.bang_tong_hop.doi_soat.dung_dang_mo())
        self.assertFalse(w.bang_tong_hop.doi_soat.ss['vuot'])               # khái toán = thực tế: không vượt
        w.dong_du_an()
        for kh in w.khung_trang.values():
            self.assertIsNone(kh.con)
        self.assertIsNone(w.bang_tong_hop.doi_soat.goc)                     # đóng dự án: bỏ khái toán đối soát của dự án

    def test_ghi_o_trang_khac_nap_lai_cac_trang(self):
        """Ghi chi trả ở trang Quyết định thì trang Tiến độ chi trả & Bàn giao (bảng + thẻ chỉ số) nạp lại khi xem."""
        ud, w = self._cua_so()
        self.qd()
        w.mo_trang(ud.TRANG_QUYET_DINH)
        _qt().processEvents()
        w.quyet_dinh.im_lang = True
        w.quyet_dinh.ds_qd_w.setCurrentRow(0)
        self.assertEqual(w.quyet_dinh.ghi_chi_tra(self.ma[:2], _hn(-1)), 2)
        w.mo_trang(ud.TRANG_THEO_DOI)
        _qt().processEvents()
        self.assertEqual(w.tien_do.tq['so_ho_nhan_du'], 2)                 # thẻ chỉ số nạp lại cùng bảng
        self.assertEqual(sum(1 for r in range(w.tien_do.bang.rowCount()) if w.tien_do.bang.item(r, w.tien_do.C_NHAN).text()), 2)


if __name__ == '__main__':
    unittest.main()
