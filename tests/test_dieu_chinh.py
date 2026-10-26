"""1.0.15 - phương án ĐIỀU CHỈNH: sửa sai phương án đã phê duyệt bằng một lần mới THAY lần cũ (lần cũ + quyết định giữ nguyên, không cộng
vào tổng hộ); quyết định điều chỉnh ghi CHÊNH LỆCH; mẫu in theo loại lần. Số liệu GIẢ LẬP."""
from __future__ import annotations

import unittest

from pabt import lan_pa, nghiep_vu, theo_doi
from pabt.lap_pa import BoSoan, LoiNhap
from pabt.tien import D
from tests.test_nhieu_lan_pa import _Co


class TestDuLieuDieuChinh(_Co):
    def _duyet_lan_1(self, con, ma=1, sl_cay=10):
        bo = BoSoan(con, ma)
        self._them(bo, 3, sl_cay)
        self._them(bo, 2, 3)
        bo.luu()
        qd = theo_doi.luu_qd(con, None, '10/QĐ-UBND', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, [ma])
        return qd, nghiep_vu.tinh_lan(con, ma, 1).tong

    def test_chua_duyet_van_lap_du_thao_dieu_chinh(self):
        """26/10/2026 (người dùng): lần gốc CHƯA có quyết định phê duyệt vẫn lập được dự thảo phương án điều chỉnh."""
        con = self._con()
        bo = BoSoan(con, 1)
        self._them(bo, 3, 5)
        bo.luu()
        tong1 = nghiep_vu.tinh_lan(con, 1, 1).tong
        lan = lan_pa.tao_lan_dieu_chinh(con, 1)
        self.assertEqual(lan, 2)
        ds = lan_pa.ds_lan(con, 1)
        self.assertEqual((ds[0].bi_thay_boi, ds[0].khoa, ds[1].la_dieu_chinh, ds[1].khoa), (2, True, True, False))
        self.assertIn('ĐIỀU CHỈNH LẦN 2', ds[0].nhan_trang_thai)
        self.assertEqual(ds[1].nhan_trang_thai, 'ĐANG LẬP DỰ THẢO PHƯƠNG ÁN ĐIỀU CHỈNH')
        with self.assertRaises(LoiNhap) as e:                                              # lần gốc bị thay: chỉ xem
            BoSoan(con, 1, lan=1).luu()
        self.assertIn('sửa ở lần 2', str(e.exception))
        bo = BoSoan(con, 1, lan=2)
        bo.pa.khoan[3][0].so_luong = D('30')
        bo.luu()
        moi = nghiep_vu.tinh_lan(con, 1, 2).tong
        self.assertNotEqual(moi, tong1)
        self.assertEqual(nghiep_vu.tinh_ho(con, 1).tong, moi)                               # tổng hộ = lần điều chỉnh
        self.assertEqual(lan_pa.lan_duyet_bi_thay(con, 1, 2), 0)
        self.assertEqual(nghiep_vu.tinh_chenh_lech_lan(con, 1, 2).tong, moi)                # chưa gì được duyệt: TOÀN BỘ, không trừ
        self.assertEqual(lan_pa.lan_chua_duyet(con, 1), 2)                                  # quyết định gắn lần điều chỉnh, không gắn lần 1
        self.assertEqual(lan_pa.tong_hop_ho(con, 1)['chua_duyet'], [2])
        qd = theo_doi.luu_qd(con, None, '20/QĐ-UBND', '05/11/2026')
        theo_doi.them_ho_theo_pa(con, qd, [1])
        r = con.execute('SELECT lan, so_tien FROM qd_ho WHERE qd_id = ? AND ma_ho = 1', (qd,)).fetchone()
        self.assertEqual((r[0], D(r[1])), (2, moi))
        self.assertEqual(lan_pa.tong_hop_ho(con, 1)['chua_duyet'], [])
        # bản in: A = phương án đã lập (chưa phê duyệt), không ghi quyết định
        from pabt import du_lieu_in, in_word
        dong, kq = du_lieu_in.dong_chi_tiet(con, 1, None, nghiep_vu.doc_phuong_an(con, 1, lan=2),
                                            nghiep_vu.doc_phuong_an(con, 1, den_lan=1))
        out, _ = in_word.dong_dieu_chinh(con, 1, None, lan_pa.lan_cua(con, 1, 2), dong, kq, du_lieu_in._thong_tin_du_an(con))
        self.assertEqual(out[0][1][1], 'PHƯƠNG ÁN ĐÃ LẬP (LẦN 1, CHƯA PHÊ DUYỆT)')
        self.assertFalse(any('Quyết định số' in str(x[1][1]) for x in out))

    def test_dieu_chinh_tiep_ban_dieu_chinh_chua_duyet_tru_lan_da_duyet(self):
        """Chuỗi: lần 1 đã duyệt -> lần 2 điều chỉnh (chưa duyệt) -> lần 3 điều chỉnh lần 2: chênh lệch so với lần 1 (lần đã duyệt)."""
        con = self._con()
        qd, tong1 = self._duyet_lan_1(con)
        lan_pa.tao_lan_dieu_chinh(con, 1)
        lan3 = lan_pa.tao_lan_dieu_chinh(con, 1, 2)
        bo = BoSoan(con, 1, lan=lan3)
        bo.pa.khoan[3][0].so_luong = D('40')
        bo.luu()
        self.assertEqual(lan_pa.lan_duyet_bi_thay(con, 1, lan3), 1)
        moi = nghiep_vu.tinh_lan(con, 1, lan3).tong
        self.assertEqual(nghiep_vu.tinh_chenh_lech_lan(con, 1, lan3).tong, moi - tong1)

    def test_lan_dieu_chinh_thay_lan_cu_trong_tong(self):
        con = self._con()
        qd, tong1 = self._duyet_lan_1(con)
        n_cu = len(nghiep_vu.doc_phuong_an(con, 1, lan=1).khoan[3])
        lan = lan_pa.tao_lan_dieu_chinh(con, 1, ten='Điều chỉnh cây trồng')
        self.assertEqual(lan, 2)
        ds = lan_pa.ds_lan(con, 1)
        x = ds[1]
        self.assertEqual((x.loai, x.thay_the, x.la_dieu_chinh, x.khoa), (lan_pa.DIEU_CHINH, 1, True, False))
        self.assertEqual(ds[0].bi_thay_boi, 2)
        self.assertEqual(len(nghiep_vu.doc_phuong_an(con, 1, lan=2).khoan[3]), n_cu)       # sao chép đủ dòng lần cũ
        self.assertEqual(nghiep_vu.tinh_ho(con, 1).tong, tong1)                             # chưa sửa: tổng không đổi (không cộng đôi)
        bo = BoSoan(con, 1, lan=2)
        bo.pa.khoan[3][0].so_luong = D('30')                                                # sửa sai số lượng cây
        bo.luu()
        moi = nghiep_vu.tinh_lan(con, 1, 2).tong
        self.assertNotEqual(moi, tong1)
        self.assertEqual(nghiep_vu.tinh_ho(con, 1).tong, moi)                               # tổng hộ = lần điều chỉnh, KHÔNG cộng lần cũ
        self.assertEqual(nghiep_vu.tinh_lan(con, 1, 1).tong, tong1)                         # lần cũ giữ nguyên số liệu
        self.assertEqual(nghiep_vu.tinh_chenh_lech_lan(con, 1, 2).tong, moi - tong1)
        self.assertTrue(BoSoan(con, 1, lan=1).khoa)                                         # lần cũ vẫn khóa

    def test_quyet_dinh_dieu_chinh_ghi_chenh_lech(self):
        con = self._con()
        qd, tong1 = self._duyet_lan_1(con)
        lan_pa.tao_lan_dieu_chinh(con, 1)
        bo = BoSoan(con, 1, lan=2)
        bo.pa.khoan[3][0].so_luong = D('30')
        bo.luu()
        moi = nghiep_vu.tinh_lan(con, 1, 2).tong
        qd2 = theo_doi.luu_qd(con, None, '20/QĐ-UBND', '05/11/2026')
        theo_doi.them_ho_theo_pa(con, qd2, [1])
        r = con.execute('SELECT so_tien, lan FROM qd_ho WHERE qd_id = ? AND ma_ho = 1', (qd2,)).fetchone()
        self.assertEqual((D(r['so_tien']), r['lan']), (moi - tong1, 2))
        x = theo_doi.tong_hop(con, [1])[0]
        self.assertEqual(x.tong_phe_duyet, x.tong_pa)                                        # QĐ cũ + QĐ điều chỉnh = phương án mới
        self.assertTrue(BoSoan(con, 1, lan=2).khoa)                                          # đã phê duyệt: khóa

    def test_xoa_lan_dieu_chinh_tra_lai_lan_cu(self):
        con = self._con()
        qd, tong1 = self._duyet_lan_1(con)
        lan_pa.tao_lan_dieu_chinh(con, 1)
        lan_pa.xoa_lan(con, 1, 2)
        self.assertEqual(nghiep_vu.tinh_ho(con, 1).tong, tong1)
        self.assertEqual(lan_pa.ds_lan(con, 1)[0].bi_thay_boi, 0)
        self.assertEqual(lan_pa.loai_lan(con, 1, 1), lan_pa.CHINH)

    def test_khong_dieu_chinh_hai_lan_cung_goc_va_loai_lan(self):
        con = self._con()
        self._duyet_lan_1(con)
        lan_pa.tao_lan_dieu_chinh(con, 1)
        with self.assertRaises(LoiNhap):
            lan_pa.tao_lan_dieu_chinh(con, 1, lan_goc=1)
        self.assertEqual(lan_pa.loai_lan(con, 1, 2), lan_pa.DIEU_CHINH)
        bo = BoSoan(con, 1)
        self.assertEqual(bo.lan, 2)


class TestInDieuChinh(TestDuLieuDieuChinh):
    def _dieu_chinh(self, con):
        qd, tong1 = self._duyet_lan_1(con)
        lan_pa.tao_lan_dieu_chinh(con, 1, ten='Điều chỉnh cây trồng')
        bo = BoSoan(con, 1, lan=2)
        bo.pa.khoan[3][0].so_luong = D('30')
        bo.luu()
        return tong1

    def _chu_docx(self, f):
        import zipfile
        return zipfile.ZipFile(f).read('word/document.xml').decode()

    def test_word_theo_loai_lan(self):
        from pabt import in_word
        con = self._con()
        self._dieu_chinh(con)
        dc = self._chu_docx(in_word.xuat_chi_tiet_docx(con, 1, self.td / 'dc.docx', lan=2))
        ch = self._chu_docx(in_word.xuat_chi_tiet_docx(con, 1, self.td / 'ch.docx', lan=1))
        self.assertIn('ĐIỀU CHỈNH', dc.upper())
        self.assertNotIn('ĐIỀU CHỈNH', ch.upper())

    def test_bang_tong_hop_dieu_chinh_va_xuat_ho_so(self):
        import openpyxl
        from pabt import bang_dieu_chinh as bdc
        con = self._con()
        self.assertFalse(bdc.co_dieu_chinh(con))
        self._dieu_chinh(con)
        self.assertTrue(bdc.co_dieu_chinh(con))
        self.assertEqual(bdc.ho_dieu_chinh(con, [1]), bdc.ho_dieu_chinh(con))
        self.assertEqual(bdc.ho_dieu_chinh(con, [2]), [])
        f = bdc.lap(con, self.td / 'bth_dc.xlsx', [1])
        ws = openpyxl.load_workbook(f).active
        chu = ' '.join(str(c.value) for r in ws.iter_rows() for c in r if c.value)
        self.assertIn('điều chỉnh', chu.lower())

    def test_nut_lap_dieu_chinh_tren_cua_so(self):
        from PySide6.QtWidgets import QApplication
        from pabt.man_hinh import CuaSoLapPA
        QApplication.instance() or QApplication([])
        con = self._con()
        self._duyet_lan_1(con)
        w = CuaSoLapPA(con, 1)
        w.im_lang = True
        self.addCleanup(w.close)
        lan = w.lap_dieu_chinh('Điều chỉnh thử')
        self.assertEqual(lan, 2)
        self.assertEqual(lan_pa.loai_lan(con, 1, 2), lan_pa.DIEU_CHINH)


if __name__ == '__main__':
    unittest.main()
