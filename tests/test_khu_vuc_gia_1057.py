"""1.0.57 (người dùng 04/11/2026, file Word "TRINH QD HỢP NHẤT GIA BT NHA, CONG TRINH XAY DUNG"): đọc bảng Word đơn giá nhà (ô tên lẫn
mô tả kết cấu, bảng "Loại | Quy mô, kết cấu | Đơn giá", tên trùng của nhà loại 4…8), nhập CẢ HAI phụ lục (Phụ lục I khu vực 1, Phụ lục
II khu vực 2) tách theo khu vực, dự án chỉ dùng phụ lục của khu vực có xã dự án (phụ lục kia khóa ẩn). Bảng / tên xã / đơn giá GIẢ LẬP
theo đúng cấu trúc văn bản (không phải số thật)."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, don_gia, khu_vuc_gia
from pabt import nhap_don_gia as ndg
from pabt.lap_pa import LoiNhap

DONG = [
    ['Phụ lục I'],
    ['ĐƠN GIÁ BỒI THƯỜNG THIỆT HẠI THỰC TẾ VỀ NHÀ, NHÀ Ở, CÔNG TRÌNH XÂY DỰNG KHU VỰC 1 TRÊN ĐỊA BÀN TỈNH THỬ'],
    ['Ghi chú:'],
    ['1. Khu vực I bao gồm các phường, xã sau:'],
    ['- Các phường: Biên Thử, Tam Thử.'],
    ['- Các xã: An Thử, Nhơn Trạch, Long'],
    ['Thành.'],
    ['2. Đơn giá nhà được tính bình quân cho 01 m2 sàn xây dựng.'],
    ['STT', 'Nhà từ 05 tầng trở lên', 'Đơn vị tính', 'Đơn giá'],
    ['1.1', '* Kết cấu loại 1: - Khung cột: Bê tông cốt thép chịu lực - Tường: sơn nước + ốp gạch', 'Đồng/m² sàn', '9.100.000'],
    ['1.2', '* Kết cấu loại 2: - Khung cột: Bê tông cốt thép - Tường: sơn nước', 'Đồng/m² sàn', '8.100.000'],
    ['5', 'Nhà bán kiên cố', '', ''],
    ['', 'Kết cấu: - Khung cột: Sắt, gạch- Tường: Gạch xây không tô', 'Đồng/m² sàn', '1.800.000'],
    ['STT', 'Loại biệt thự', 'Đơn giá (đồng/m2 sàn)'],
    ['1', 'Song lập', '8.000.000'],
    ['STT', 'Tên tài sản', 'ĐVT', 'Đơn giá (đồng)'],
    ['34', 'Ống cống bê tông', '', ''],
    ['', 'Φ0,3m', 'mét', '96.000'],
    ['35', 'Di dời bồn nước', '', ''],
    ['', 'a) Bồn nhựa', '', ''],
    ['', '- Dưới 1.000 lít', 'cái', '170.000'],
    ['', 'b) Bồn inox', '', ''],
    ['', '- Dưới 1.000 lít', 'cái', '250.000'],
    ['STT', 'Kết cấu', 'Tỷ lệ còn lại'],
    ['', '1', '2', '3', '4', '5', '6', '7'],
    ['Phụ lục II'],
    ['ĐƠN GIÁ BỒI THƯỜNG THIỆT HẠI THỰC TẾ VỀ NHÀ, NHÀ Ở, CÔNG TRÌNH XÂY DỰNG KHU VỰC 2 TRÊN ĐỊA BÀN TỈNH THỬ'],
    ['1. Khu vực 2 bao gồm các phường, xã:'],
    ['- Các phường: Bình Thử, Đồng Thử.'],
    ['- Các xã: Bù Đăng, Phú Thử.'],
    ['Loại', 'Quy mô, kết cấu công trình', 'Đơn giá bồi thường (đồng/m2 sàn xây dựng)'],
    ['1', '2', '3'],
    ['A. Nhà, nhà ở', '', ''],
    ['1', 'Nhà 6 đến 8 tầng', ''],
    ['', 'Kết cấu: Móng, khung chịu lực bằng BTCT; mái bằng bê tông cốt thép.', '7.000.000'],
    ['', 'Vật liệu hoàn thiện: Tường xây gạch, sơn nước có bả mastic.', ''],
    ['4', 'Nhà 01 tầng, chiều cao từ 3m đến 4m (không tính chiều cao tường thu hồi).', '4.900.000'],
    ['', 'Kết cấu: Móng, khung chịu lực bằng BTCT; mái lợp tôn.', ''],
    ['5', 'Nhà 01 tầng, chiều cao từ 3m đến 4m (không tính chiều cao tường thu hồi).', '3.600.000'],
    ['', 'Kết cấu: Móng xây bằng đá hoặc bằng gạch; mái lợp tôn.', ''],
    ['Nhà bán kiên cố', 'Kết cấu: Cột gỗ vuông hoặc tròn hoặc xây gạch; mái tôn.', '1.600.000'],
    ['Nhà nuôi yến kết hợp ở', 'Phần diện tích để ở được áp giá theo đơn giá nhà ở.', ''],
    ['B. Nhà xưởng', '', ''],
    ['1', 'Nhà xưởng 01 tầng, nhịp kết cấu < 12m', '1.500.000'],
    ['STT', 'Danh mục', 'Đơn vị tính', 'Đơn giá'],
    ['1', 'Ống bi bê tông đường kính < 1m', 'đồng/m dài', '280.000'],
    ['2', 'Ống bi bê tông đường kính ≥ 1m', 'đồng/m dài', '370.000'],
    ['3', 'Chuồng trại tạm: nền láng xi măng', 'dông/m2', '390.000'],
]

BO = [('TS1', 'Nhà từ 05 tầng trở lên - Kết cấu loại 1', 'm²', 9100000), ('TS2', 'Nhà từ 05 tầng trở lên - Kết cấu loại 2', 'm²', 8100000),
      ('TS3', 'Nhà bán kiên cố', 'm²', 1800000), ('TS4', 'Biệt thự Song lập', 'm²', 8000000),
      ('TS5', 'Ống cống bê tông - Φ0,3m', 'm', 96000), ('TS6', 'Di dời bồn nhựa < 1.000 lít', 'cái', 170000),
      ('TS7', 'Di dời bồn Inox < 1.000 lít', 'cái', 250000), ('TS8', 'Gác lửng nhà chính', 'm²', 1000000)]


class TestDocWord(unittest.TestCase):
    def setUp(self):
        self.ds = ndg.nhan_muc(DONG, 2, [])
        self.theo = {(m.ten, m.khu_vuc): m for m in self.ds}

    def test_ket_cau_va_mo_ta(self):
        m = self.theo[('Nhà từ 05 tầng trở lên - Kết cấu loại 1', '1')]
        self.assertEqual((m.dvt, m.don_gia), ('m²', 9100000))
        self.assertIn('Khung cột: Bê tông cốt thép chịu lực', m.ghi_chu)          # mô tả kết cấu -> ghi chú, không vào tên
        self.assertEqual(self.theo[('Nhà bán kiên cố', '1')].don_gia, 1800000)
        self.assertEqual(self.theo[('Biệt thự Song lập', '1')].dvt, 'm²')
        self.assertIn(('Di dời bồn nước - Bồn nhựa - Dưới 1.000 lít', '1'), self.theo)
        self.assertIn(('Di dời bồn nước - Bồn inox - Dưới 1.000 lít', '1'), self.theo)
        self.assertEqual(self.theo[('Ống cống bê tông - Φ0,3m', '1')].don_gia, 96000)  # "a) Bồn nhựa" không nối vào dòng trên
        self.assertFalse([m for m in self.ds if m.ten.startswith('Kết cấu')])      # bảng tỷ lệ còn lại không thành mục

    def test_bang_loai_quy_mo(self):
        m = self.theo[('Nhà 6 đến 8 tầng', '2')]
        self.assertEqual((m.dvt, m.don_gia), ('m²', 7000000))
        self.assertIn('Vật liệu hoàn thiện', m.ghi_chu)                            # dòng mô tả không giá -> ghi chú mục trên
        ten4 = 'Nhà 01 tầng, chiều cao từ 3m đến 4m (không tính chiều cao tường thu hồi) (nhà loại 4)'
        self.assertEqual(self.theo[(ten4, '2')].don_gia, 4900000)
        self.assertEqual(self.theo[(ten4.replace('loại 4', 'loại 5'), '2')].don_gia, 3600000)
        self.assertEqual(self.theo[('Nhà bán kiên cố', '2')].don_gia, 1600000)       # tên ở cột Loại
        self.assertEqual(self.theo[('Nhà xưởng 01 tầng, nhịp kết cấu < 12m', '2')].don_gia, 1500000)
        self.assertFalse([m for m in self.ds if m.ten.startswith(('B. ', '9 - ', 'A. '))])
        self.assertEqual(self.theo[('Chuồng trại tạm: nền láng xi măng', '2')].dvt, 'm²')   # "dông/m2" gõ sai

    def test_xa_va_phu_luc(self):
        xa = khu_vuc_gia.doc_ds_xa(DONG)
        self.assertEqual(xa['1'], ['Biên Thử', 'Tam Thử', 'An Thử', 'Nhơn Trạch', 'Long Thành'])
        self.assertEqual(xa['2'], ['Bình Thử', 'Đồng Thử', 'Bù Đăng', 'Phú Thử'])
        self.assertEqual(khu_vuc_gia.ten_phu_luc_kv(DONG), {'1': 'Phụ lục I', '2': 'Phụ lục II'})


class TestHaiPhuLuc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        p = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        p.start()
        self.addCleanup(p.stop)
        self.bo = self.td / 'bo.sqlite'
        shutil.copyfile(don_gia.file_goc(), self.bo)
        con = csdl.mo(self.bo)
        try:
            with csdl.giao_dich(con), csdl.mo_khoa_danh_muc(con):
                pl = con.execute('SELECT phan_loai FROM dm_taisan WHERE nhom = 2 LIMIT 1').fetchone()[0]
                con.execute('DELETE FROM dm_taisan WHERE nhom = 2')
                con.executemany('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia) VALUES (?,2,?,?,?,?)',
                                [(ma, pl, t, d, str(g)) for ma, t, d, g in BO])
        finally:
            con.close()
        p = mock.patch.object(don_gia, 'file_goc', return_value=self.bo)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.doCleanups()
        self.tmp.cleanup()

    def _nhap(self):
        ds = ndg.nhan_muc(DONG, 2, [])
        ndg.so_khop_khu_vuc(ds, 2)
        return ds

    def test_so_khop_tung_khu_vuc_va_ap_dung(self):
        ds = self._nhap()
        kv1 = [m for m in ds if m.khu_vuc == '1']
        self.assertTrue(kv1 and all(m.trang_thai == 'giữ nguyên' for m in kv1), [(m.ten, m.trang_thai) for m in kv1])
        kv2 = [m for m in ds if m.khu_vuc == '2']
        self.assertTrue(kv2 and all(m.trang_thai == 'mới' for m in kv2))           # khu vực 2 không đè giá khu vực 1
        self.assertEqual(next(m for m in kv1 if m.ten == 'Nhà bán kiên cố').ma_khop, 'TS3')
        ma_moi = [m.ma_moi for m in kv2]
        self.assertEqual(len(set(ma_moi)), len(ma_moi))
        self.assertEqual(ma_moi[0], 'TS9')                                          # số tiếp theo của cả bộ
        for m in ds:
            m.chon = m.trang_thai in ndg.TRANG_THAI_GHI
        kq = ndg.ap_dung(ds, 2, 'thu.doc', khu_vuc=dict(xa=khu_vuc_gia.doc_ds_xa(DONG), ten=khu_vuc_gia.ten_phu_luc_kv(DONG)))
        self.assertEqual(kq['so_moi'], len(kv2))
        self.assertGreater(kq['so_khu_vuc'], len(ds))
        con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
        try:
            kvd = khu_vuc_gia.doc(con)
        finally:
            con.close()
        self.assertEqual(kvd['muc']['TS3'], '1')
        self.assertNotIn('TS8', kvd['muc'])                                         # mục văn bản không có: dùng chung
        self.assertEqual(khu_vuc_gia.khu_vuc_cua_xa(kvd, 'xã Bù Đăng, tỉnh Thử'), '2')
        self.assertEqual(khu_vuc_gia.khu_vuc_cua_xa(kvd, 'Nhơn Trạch'), '1')
        self.assertEqual(kvd['ten']['2'], 'Phụ lục II')
        # nhập lại cùng văn bản: hai khu vực đều khớp mục của khu vực mình
        ds2 = self._nhap()
        self.assertEqual({m.trang_thai for m in ds2}, {'giữ nguyên'})
        # dự án: chỉ dùng phụ lục của khu vực có xã dự án
        from pabt import lap_pa
        da = csdl.tao_moi(self.td / 'da.pabt')
        try:
            don_gia.ap_vao_du_an(da)
            with da:
                da.execute("UPDATE du_an SET ten_dia_ban = 'Xã Bù Đăng' WHERE id = 1")
            dm = lap_pa.DanhMuc(da)
            self.assertEqual(dm.kv, '2')
            ten = [m.ten for m in dm.muc[2]]
            self.assertIn('Nhà 6 đến 8 tầng', ten)
            self.assertIn('Gác lửng nhà chính', ten)                                # mục chung: mọi khu vực
            self.assertNotIn('TS3', [m.ma for m in dm.muc[2]])                      # Phụ lục I khóa ẩn
            self.assertIsNotNone(dm.lay('TS3'))                                     # dòng cũ vẫn đọc được giá
            self.assertIn('khóa', dm.bi_khoa('TS3'))
            with da:
                da.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'Hộ thử')")
            bo = lap_pa.BoSoan(da, 1, danh_muc=dm)
            with self.assertRaises(LoiNhap):
                bo.them_tu_danh_muc(2, dm.lay('TS3'))
            khu_vuc_gia.dat_khu_vuc_du_an(da, '1')                                  # người dùng chọn tay
            dm1 = lap_pa.DanhMuc(da)
            self.assertIn('TS3', [m.ma for m in dm1.muc[2]])
            self.assertNotIn('Nhà 6 đến 8 tầng', [m.ten for m in dm1.muc[2]])
        finally:
            da.close()

    def test_hop_thoai_hai_phan_va_bo_don_gia(self):
        from tests import APP  # noqa: F401
        from pabt.man_hinh_nhap_don_gia import (C_GIA, C_GIA_CU, C_KV, C_MA, C_MA_CU, C_TEN, C_TEN_CU, COT, HopNhapDonGia)
        HopNhapDonGia.im_lang = True
        try:
            h = HopNhapDonGia(None, dong=DONG, van_ban={}, nhom_uu_tien=2, nguon='thu.doc')
            self.assertEqual(h.bang.columnCount(), len(COT))
            self.assertEqual(h.cb_kv.currentData(), ndg.KV_CA_HAI)                  # mặc định nhập cả hai phụ lục
            r = next(i for i, m in enumerate(h.ds) if m.ten == 'Nhà bán kiên cố' and m.khu_vuc == '1')
            self.assertEqual(h.bang.item(r, C_MA_CU).text(), 'TS3')
            self.assertEqual(h.bang.item(r, C_TEN_CU).text(), 'Nhà bán kiên cố')
            self.assertEqual(h.bang.item(r, C_GIA_CU).text(), h.bang.item(r, C_GIA).text())
            self.assertIn('Phụ lục I', h.bang.item(r, C_KV).text())
            r2 = next(i for i, m in enumerate(h.ds) if m.ten == 'Nhà bán kiên cố' and m.khu_vuc == '2')
            self.assertEqual(h.bang.item(r2, C_MA_CU).text(), '')                   # mục mới: phần hiện hành trống
            self.assertRegex(h.bang.item(r2, C_MA).text(), r'^TS\d+ \(mới\)$')
            self.assertEqual(h.bang.item(r2, C_TEN).text(), 'Nhà bán kiên cố')
            h.cb_kv.setCurrentIndex(h.cb_kv.findData('1'))                           # chỉ một khu vực: như trước
            self.assertEqual({m.khu_vuc for m in h.ds}, {'1'})
            h.cb_kv.setCurrentIndex(0)
            h.accept()
            self.assertIsNotNone(h.ket_qua)
            self.assertTrue(h.ket_qua['so_khu_vuc'])
            h.close()
        finally:
            HopNhapDonGia.im_lang = False
        from pabt.man_hinh_don_gia import HopBoDonGia
        da = csdl.tao_moi(self.td / 'db.pabt')
        try:
            don_gia.ap_vao_du_an(da)
            with da:
                da.execute("UPDATE du_an SET ten_dia_ban = 'Nhơn Trạch' WHERE id = 1")
            d = HopBoDonGia(None, da)
            d.im_lang = True
            self.assertIsNotNone(d.kv_dl)
            self.assertEqual(d.kv_xem, '1')                                           # theo xã dự án
            self.assertEqual(sorted(d.nut_pl), ['1', '2'])
            self.assertIn('khóa', d.nut_pl['2'].text())
            self.assertFalse(d.nut_pl['2'].isEnabled())                               # phụ lục khu vực khác khóa
            ma0 = {str(r[0]) for r in d._ds_the[0]}
            self.assertIn('TS3', ma0)
            self.assertIn('TS8', ma0)                                                 # mục chung hiện ở cả hai bảng
            self.assertIn('Phụ lục I', d.the.tabText(0))
            self.assertFalse(any(str(r[0]).startswith('KV') for r in d._ds_the[4]))  # thẻ Tham số không lẫn khu vực
            d.chon_phu_luc('2')                                                       # quản trị / máy không dự án xem được
            self.assertEqual(d.kv_xem, '2')
            self.assertNotIn('TS3', {str(r[0]) for r in d._ds_the[0]})
            self.assertTrue(d.doi_khu_vuc_du_an('2'))
            self.assertEqual(d.khu_vuc_du_an(), '2')
            self.assertTrue(d.da_ap)
            hop = d.xem_xa_khu_vuc(hien=False)
            self.assertIsNotNone(hop)
            hop.deleteLater()
            d.close()
            d.deleteLater()
        finally:
            da.close()


if __name__ == '__main__':
    unittest.main()
