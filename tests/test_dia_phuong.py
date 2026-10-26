"""Kiểm thử 1.0.29 (chỉ thị Giai đoạn 2, người dùng 26/10/2026): đa tỉnh xuyên suốt - mã chính sách hỗ trợ theo hồ sơ địa phương
(hợp với mã chuẩn, ưu tiên mã), mô hình vị trí bảng giá đất ở tra cứu / ô Vị trí, hồ sơ mẫu cho tỉnh mới; A+ / A− gộp; tách in_excel.
Mã chính sách / mã vị trí của "tỉnh khác" là GIẢ LẬP."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import chinh_sach, dia_phuong, gia_dat_nq28, nghiep_vu


class _HoSoMay(unittest.TestCase):
    """Mỗi bài một thư mục máy riêng (file hồ sơ máy ghi ở đó); xong thì nạp lại hồ sơ của lượt kiểm thử."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': self.td.name})
        self._env.start()
        dia_phuong.nap_lai()

    def tearDown(self):
        self._env.stop()
        dia_phuong.nap_lai()
        self.td.cleanup()


class TestMaChinhSach(_HoSoMay):
    def test_tap_ma_mac_dinh_nhu_cu(self):
        self.assertEqual(nghiep_vu.tap_ma_on_dinh(), nghiep_vu.MA_ON_DINH)
        self.assertEqual(nghiep_vu.tap_ma_theo_nk(), tuple(nghiep_vu.MA_THEO_NK))
        self.assertEqual(nghiep_vu.tap_ma_tdc(), nghiep_vu.MA_TDC)
        self.assertIs(chinh_sach.tap_ma_on_dinh, nghiep_vu.tap_ma_on_dinh)          # chinh_sach xuất lại

    def test_hop_nhat_va_uu_tien_ma(self):
        # tỉnh khác: OD01 ổn định, TN01 thuê nhà, TDC01 tái định cư; OD02 khai báo NHẦM ở cả ổn định lẫn TĐC -> vẫn là ổn định
        dia_phuong.dat_muc_may(('chinh_sach_ho_tro',), dict(ma_on_dinh=['OD01', 'OD02'], ma_theo_nk=['TN01'],
                                                            ma_tdc=['TDC01', 'OD02', 'TN01']))
        self.assertEqual(nghiep_vu.tap_ma_on_dinh()[-2:], ('OD01', 'OD02'))
        self.assertIn('CS1', nghiep_vu.tap_ma_on_dinh())                         # hợp với mã chuẩn, không thay
        self.assertIn('TN01', nghiep_vu.tap_ma_theo_nk())
        self.assertIn('CS11', nghiep_vu.tap_ma_tdc())
        self.assertIn('TDC01', nghiep_vu.tap_ma_tdc())
        self.assertNotIn('OD02', nghiep_vu.tap_ma_tdc())
        self.assertNotIn('TN01', nghiep_vu.tap_ma_tdc())
        # mã thắng tên: tên có "tái định cư" nhưng mã là ổn định / thuê nhà
        self.assertEqual(chinh_sach.loai('OD02', 'Hỗ trợ ổn định đời sống khi tái định cư'), 'od')
        self.assertEqual(chinh_sach.loai('TN01', 'Hỗ trợ thuê nhà chờ tái định cư'), 'tn')
        self.assertEqual(chinh_sach.loai('TDC01'), 'tdc')

    def test_nghiep_vu_dung_ma_ho_so(self):
        from pabt.nghiep_vu import DongKhoan, PhuongAn, ThongTinHo, kiem_tra_pa
        dia_phuong.dat_muc_may(('chinh_sach_ho_tro',), dict(ma_on_dinh=['OD01'], ma_tdc=['TDC01']))
        pa = PhuongAn(ho=ThongTinHo(ma_ho=1, thu_tu=1, ho_ten='Hộ thử', nhan_khau=None, phai_di_chuyen=False, dt_nn_dang_dung=None,
                                    trang_thai=''))
        pa.khoan[4].append(DongKhoan(muc=4, ma='OD01', ten='Ổn định đời sống (tỉnh khác)', dvt='khẩu', so_luong=nghiep_vu.D(5),
                                     don_gia=nghiep_vu.D(100)))
        self.assertEqual(pa.nhan_khau, 5)                       # nhân khẩu lấy từ dòng ổn định mã tỉnh khác
        pa.khoan[4].append(DongKhoan(muc=4, ma='TDC01', ten='Bố trí tái định cư', dvt='suất', so_luong=nghiep_vu.KHONG,
                                     don_gia=nghiep_vu.KHONG))
        ct = kiem_tra_pa(pa, None)
        self.assertFalse(any('Bố trí tái định cư' in x for x in ct))            # TĐC tỉnh khác: không phải dòng tiền

    def test_ho_so_sai_kieu_bi_chan(self):
        with self.assertRaises(dia_phuong.LoiHoSo):
            dia_phuong.dat_muc_may(('chinh_sach_ho_tro',), dict(ma_on_dinh='OD01'))


class TestViTri(_HoSoMay):
    def test_dong_nai_giu_nguyen(self):
        self.assertTrue(gia_dat_nq28.la_mo_hinh_mac_dinh())
        for m in gia_dat_nq28.MO_HINH_VI_TRI['DONG_NAI_NQ28']:
            self.assertEqual(gia_dat_nq28.ten_vi_tri(m), gia_dat_nq28.TEN_VT[m])
        ds = gia_dat_nq28.tim('', 'T1')
        self.assertTrue(ds)
        self.assertEqual(gia_dat_nq28.tim('', '', 'T1'), [r for r in gia_dat_nq28.tim() if r['vi_tri'] == 'T1'])

    def test_doc_ma_vi_tri_khu_vuc(self):
        c = gia_dat_nq28._chuan_vi_tri
        self.assertEqual([c(x) for x in ('KV1-VT2', 'khu vực 2 vị trí 3', 'kv3 vt1', 'VT2', '2', 'Vị trí 4', 'MT', 't1')],
                         ['KV1-VT2', 'KV2-VT3', 'KV3-VT1', 'VT2', 'VT2', 'VT4', 'MT', 'T1'])

    def test_o_vi_tri_theo_mo_hinh(self):
        try:
            from PySide6.QtWidgets import QApplication  # noqa: F401
        except ImportError:
            self.skipTest('không có Qt')
        from pabt.man_hinh_du_toan import HopTraNQ28
        h = HopTraNQ28()
        self.assertIsNone(h.cb_vt)                                               # Đồng Nai: như trước, không thêm ô
        h.close()
        dia_phuong.dat_muc_may(('bang_gia_dat',), dict(mo_hinh_vi_tri='VI_TRI_1_4'))
        self.assertFalse(gia_dat_nq28.la_mo_hinh_mac_dinh())
        h = HopTraNQ28()
        self.assertEqual([h.cb_vt.itemData(i) for i in range(h.cb_vt.count())], ['', 'VT1', 'VT2', 'VT3', 'VT4'])
        self.assertIn('Vị trí 2', h.cb_vt.itemText(2))
        h.close()

    def test_nhan_o_vi_tri_muc_1(self):
        from pabt import csdl
        from pabt.lap_pa import BoSoan
        from tests.test_toc_do import _du_an
        p = _du_an(Path(self.td.name), 2)
        con = csdl.mo(p)
        try:
            bo = BoSoan(con, 1)
            nhan_dn = bo.ds_vi_tri_nq28(0)[0][0]
            dia_phuong.dat_muc_may(('bang_gia_dat',), dict(mo_hinh_vi_tri='KHU_VUC_VI_TRI'))
            ds = bo.ds_vi_tri_nq28(0)
            self.assertEqual(len(ds), len(gia_dat_nq28.tat_ca()))
            r = ds[0][1]
            self.assertIn(gia_dat_nq28.ten_vi_tri(r['vi_tri']), ds[0][0])                # nhãn ghi TÊN vị trí
            self.assertIn(nhan_dn.split(' · ')[1], gia_dat_nq28.TEN_VT)                     # Đồng Nai: nhãn ghi MÃ như trước
            self.assertEqual(ds[0][0].split(' · ')[1], gia_dat_nq28.ten_vi_tri(r['vi_tri']))
        finally:
            con.close()


class TestHoSoTinhMoi(_HoSoMay):
    def test_mau_tinh_moi(self):
        for mh in dia_phuong.MO_HINH_VI_TRI:
            hs = dia_phuong.mau_tinh_moi(mh, 'Tỉnh Thử')
            self.assertEqual(hs['bang_gia_dat']['mo_hinh_vi_tri'], mh)
            self.assertEqual(hs['co_quan']['ten'], '')
            self.assertEqual(hs['chinh_sach_ho_tro'], dict(ma_on_dinh=[], ma_dao_tao=[], ma_theo_nk=[], ma_tdc=[]))
            self.assertEqual(dia_phuong.kiem_tra(hs), [])
        with self.assertRaises(dia_phuong.LoiHoSo):
            dia_phuong.mau_tinh_moi('KHONG_CO')

    def test_nut_cau_hinh_xuat_file_khong_doi_ho_so_dang_dung(self):
        try:
            from pabt.man_hinh_cau_hinh import HopCauHinhNghiepVu
        except ImportError:
            self.skipTest('không có Qt')
        truoc = dia_phuong.ten_ho_so()
        h = HopCauHinhNghiepVu()
        h.im_lang = True
        f = Path(self.td.name) / 'ra' / 'pabt_profile.json'
        self.assertEqual(h.tao_mau_tinh_moi(f, 'VI_TRI_1_4', 'Tỉnh Thử'), f)
        hs = json.loads(f.read_text(encoding='utf-8'))
        self.assertEqual((hs['ten_ho_so'], hs['bang_gia_dat']['mo_hinh_vi_tri']), ('Hồ sơ Tỉnh Thử', 'VI_TRI_1_4'))
        self.assertEqual(dia_phuong.kiem_tra_file(f)['bang_gia_dat']['mo_hinh_vi_tri'], 'VI_TRI_1_4')
        self.assertEqual(dia_phuong.ten_ho_so(), truoc)
        h.close()


class TestDiaDanhNgay(_HoSoMay):
    """Người dùng 26/10/2026: địa danh đầu dòng ngày tháng của bản in là NƠI ĐƠN VỊ CÔNG TÁC, không phải xã có đất của dự án."""

    def setUp(self):
        super().setUp()
        from pabt import csdl
        from tests.test_toc_do import _du_an
        self.p = _du_an(Path(self.td.name), 2)                                 # dự án ở xã Bàu Hàm
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        super().tearDown()

    def _dong_ngay_word(self) -> str:
        import re
        import zipfile
        from pabt import in_word
        f = in_word.xuat_chi_tiet_docx(self.con, 1, Path(self.td.name) / 'pa.docx')
        chu = re.sub('<[^>]+>', '', zipfile.ZipFile(f).read('word/document.xml').decode('utf-8'))
        i = chu.index(', ngày')
        return chu[max(0, i - 20):i]

    def test_khong_lay_xa_co_dat(self):
        from pabt import du_lieu_in
        dia_phuong.dat_muc_may(('ban_in', 'dia_danh_ngay'), '')                 # hồ sơ chưa ghi địa danh
        self.assertTrue(self._dong_ngay_word().endswith(du_lieu_in.DIA_DANH_TRONG))
        self.assertNotIn('Bàu Hàm', self._dong_ngay_word())

    def test_dia_danh_cua_du_an_cho_moi_ban_in(self):
        import openpyxl
        from pabt import in_an, lap_pa, van_ban_trinh
        gt = lap_pa.doc_du_an(self.con)
        self.assertEqual(gt['dia_danh_don_vi'], '')
        gt['dia_danh_don_vi'] = 'Vĩnh An'
        lap_pa.luu_du_an(self.con, gt)
        self.assertEqual(lap_pa.doc_du_an(self.con)['dia_danh_don_vi'], 'Vĩnh An')
        self.assertTrue(self._dong_ngay_word().endswith('Vĩnh An'))           # phương án chi tiết (Word)
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(self.con, Path(self.td.name) / 'bth.xlsx')).active
        dong = [c.value for r in ws.iter_rows() for c in r if isinstance(c.value, str) and ', ngày' in c.value]
        self.assertTrue(dong and dong[0].startswith('Vĩnh An, ngày'), dong)    # bảng tổng hợp
        chung, _ = van_ban_trinh.du_lieu(self.con, [1, 2])
        self.assertEqual(chung['dia_danh_ngay'], 'Vĩnh An')                     # tờ trình: chỗ trống {dia_danh_ngay}
        self.assertIn('{dia_danh_ngay}, ', van_ban_trinh._dau_trang('Số: …', 'ngày …'))

    def test_file_cu_thieu_cot(self):
        import sqlite3
        from pabt import csdl, lap_pa
        con = sqlite3.connect(':memory:')
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE du_an (id INTEGER PRIMARY KEY, ten TEXT NOT NULL DEFAULT '')")
        con.execute("INSERT INTO du_an (id, ten) VALUES (1, 'Cũ')")
        self.assertEqual(lap_pa.doc_du_an(con)['dia_danh_don_vi'], '')         # đọc file cũ: trống, không lỗi
        csdl.dam_bao_cot_du_an(con)
        self.assertIn('dia_danh_don_vi', [r[1] for r in con.execute('PRAGMA table_info(du_an)')])
        con.close()

    def test_o_thong_tin_du_an(self):
        try:
            from pabt.man_hinh import HopDuAn
        except ImportError:
            self.skipTest('không có Qt')
        from pabt import csdl
        self.assertIn('dia_danh_don_vi', csdl.TRUONG_DON_VI)                  # thuộc đơn vị: giữ khi xóa trắng, điền sẵn dự án mới
        h = HopDuAn(self.con)
        self.assertIn('dia_danh_don_vi', h.o)
        h.close()


class TestPhongToGop(unittest.TestCase):
    def test_bam_lien_tiep_chi_ap_kieu_mot_lan(self):
        try:
            from PySide6.QtCore import QCoreApplication, QElapsedTimer
        except ImportError:
            self.skipTest('không có Qt')
        from pabt import giao_dien
        goi = []
        try:
            with mock.patch.object(giao_dien, 'dat_ty_le', lambda t, *a, **k: goi.append(t)), \
                    mock.patch.object(giao_dien, '_bao_ty_le', lambda t: None):
                for _ in range(5):
                    giao_dien.phong_to(1, cho_ms=60)
                d = QElapsedTimer()
                d.start()
                while d.elapsed() < 400:
                    QCoreApplication.processEvents()
            self.assertEqual(len(goi), 1)                                       # 5 lần bấm -> áp kiểu MỘT lần
        finally:
            giao_dien._CHO[0] = None


class TestTachInExcel(unittest.TestCase):
    def test_in_an_xuat_lai_ten(self):
        from pabt import in_an, in_excel
        for ten in ('LoiIn', 'chay_excel', 'co_excel', 'mo_file', '_doc_luong', '_tat_excel_tu_dong', '_VBS', 'CHO_MOI_FILE',
                    'CHO_KHOI_DONG'):
            self.assertIs(getattr(in_an, ten), getattr(in_excel, ten), ten)
        self.assertIn('AutomationSecurity = 3', in_excel._VBS)                  # macro tắt - bắt buộc giữ


if __name__ == '__main__':
    unittest.main()
