"""1.0.62: bộ quét chung định tuyến từng file tới màn hình chuyên trách; thửa, tài sản quét được đưa vào phương án của hộ (chưa lưu)."""
from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

import openpyxl

from pabt import csdl, du_an_moi, ocr
from pabt import quet_chung as qc
from pabt.lap_pa import BoSoan

from tests import APP

BIEN_BAN = ('BIÊN BẢN KIỂM KÊ HIỆN TRẠNG\nHọ và tên chủ hộ: Hộ thử 1\nThửa đất số 101, tờ bản đồ số 11, diện tích 55,5 m2, tiếp giáp đường cấp phối\n'
            'Tên tài sản\tĐVT\tSố lượng\nCây xoài\tcây\t16\nNhà tạm\tm2\t20\nĐại diện ký tên\n')


def _du_an(td: Path) -> Path:
    dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_cccd=f'07520000000{i}', so_to=str(10 + i), so_thua=str(100 + i), loai_dat='CLN',
                 dt_thu_hoi=str(100 + i), vi_tri='1') for i in range(3)]
    p = td / 'a.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Tân An', nam='2026'), dong, [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    return p


class TestNhanLoai(unittest.TestCase):
    def test_tung_loai(self):
        self.assertEqual(qc.nhan_loai('a.pdf', 'Bảng 54. Xã Tân An\nHệ số điều chỉnh\n1 Đường A 1,2'), qc.D_HE_SO_K)
        self.assertEqual(qc.nhan_loai('a.xlsx', 'BẢNG GIÁ ĐẤT - XÃ TÂN AN\nTT\tTên đường\tĐiểm đầu\tĐiểm cuối\tVị trí'), qc.D_BANG_GIA)
        self.assertEqual(qc.nhan_loai('a.xlsx', 'STT\tHọ và tên\tTờ\tThửa\tDiện tích\n1\tA\t1\t2\t3'), qc.D_DU_AN)
        self.assertEqual(qc.nhan_loai('a.pdf', BIEN_BAN), qc.D_HO_SO)
        self.assertEqual(qc.nhan_loai('a.txt', 'Căn cứ Luật Đất đai số 31/2024/QH15;\nNội dung khác'), qc.D_CAN_CU)
        self.assertEqual(qc.nhan_loai('a.txt', 'Một đoạn chữ không liên quan'), qc.D_KHAC)

    def test_khong_nhan_nham_tai_lieu_co_nhac_tu_khoa(self):
        # đã gặp trên file thật: cẩm nang, báo cáo, văn bản thẩm định nhắc "biên bản kiểm kê" / "phương án bồi thường" -> không được đổ vào hộ
        cam_nang = 'CẨM NANG SỬ DỤNG\nGiới thiệu phần mềm\n' + 'dòng chữ\n' * 40 + 'Biên bản kiểm kê: thửa đất số 1, tờ bản đồ số 2, 30 m2\nXoài 16 cây\n' + 'x' * 25000
        self.assertNotEqual(qc.nhan_loai('cam_nang.pdf', cam_nang), qc.D_HO_SO)
        bao_cao = 'BÁO CÁO SÁNG KIẾN\nHọ và tên tác giả: A\nGiải pháp phần mềm lập phương án bồi thường\nMô tả chủ sử dụng đất\n' + 'dòng\n' * 40
        self.assertNotEqual(qc.nhan_loai('bao_cao.docx', bao_cao), qc.D_HO_SO)
        self.assertEqual(qc.nhan_loai('pa.pdf', 'PHƯƠNG ÁN BỒI THƯỜNG\nHọ và tên chủ hộ: A\nThửa đất số 1\nTên tài sản\tĐVT\tSố lượng'), qc.D_HO_SO)
        doi_chieu = 'Hộ\tĐơn giá\tTiền\n' + '\n'.join(f'{i}\tNhà {i}\tm2\t{i}.000.000' for i in range(1, 7))
        self.assertNotEqual(qc.nhan_loai('Dự án_DoiChieu.xlsx', doi_chieu), qc.D_DON_GIA)

    def test_bang_don_gia(self):
        nd = 'STT\tTên\tĐVT\tĐơn giá\n' + '\n'.join(f'{i}\tNhà loại {i}\tm2\t{i}.000.000' for i in range(1, 7))
        self.assertEqual(qc.nhan_loai('a.xlsx', nd), qc.D_DON_GIA)

    def test_ngu_canh(self):
        self.assertEqual(qc.nhan_loai('a.pdf', BIEN_BAN, qc.CAN_CU), qc.D_CAN_CU)        # quét căn cứ: không rẽ sang việc khác
        self.assertEqual(qc.nhan_loai('a.pdf', 'chữ lạ', qc.GIA_TAI_SAN), qc.D_DON_GIA)   # không nhận ra: theo nút đã bấm
        self.assertEqual(qc.nhan_loai('a.pdf', 'chữ lạ', qc.HO_SO_HO), qc.D_HO_SO)
        self.assertEqual(qc.nhan_loai('a.pdf', 'chữ lạ', qc.GIA_DAT), qc.D_BANG_GIA)

    def test_excel_du_an_khong_doc_het(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'pabt.xlsx'
            wb = openpyxl.Workbook()
            for s in ('DB_HO', 'DB_THUA', 'DB_DATCT'):
                wb.create_sheet(s)
            wb.save(p)
            wb.close()
            with mock.patch.object(qc, 'doc_noi_dung', side_effect=AssertionError('không được đọc')):
                kq = qc.quet([p])
            self.assertEqual(kq.tung_file[0]['loai'], qc.D_DU_AN)
            self.assertEqual(kq.loi, [])

    def test_quet_bien_ban(self):
        kq = qc.quet(['bb.pdf'], doc=lambda p: BIEN_BAN)
        self.assertEqual(kq.tung_file[0]['loai'], qc.D_HO_SO)
        self.assertEqual([(d.to_ban_do, d.so_thua, d.ket_cau_mat_duong) for d in kq.dong_dat], [('11', '101', 'DAT_SOI_DA_CAPPHOI')])
        self.assertEqual(kq.dong_dat[0].dien_tich_thu_hoi, Decimal('55.5'))
        self.assertTrue(any('xoài' in x.lower() for x in kq.dong_dan))
        self.assertFalse(any('ký tên' in x.lower() for x in kq.dong_dan))
        self.assertTrue(kq.co_du_lieu_ho())


class TestOcrMotLan(unittest.TestCase):
    def test_nho_trong_bo_nho(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.png'
            p.write_bytes(b'x')
            ocr._DA_DOC.clear()
            with mock.patch.object(ocr, 'may_doc', return_value=(True, None)), \
                    mock.patch.object(ocr, 'tung_trang', return_value=['dòng 1']) as t:
                a = ocr.doc_chu(p)
                b = ocr.doc_chu(p)
                self.assertEqual(a, b)
                self.assertEqual(t.call_count, 1)
                a.append('sửa ngoài')                                      # không sửa được bản nhớ
                self.assertEqual(ocr.doc_chu(p), ['dòng 1'])
                ocr.doc_chu(p, psm=4)                                       # chế độ khác: đọc lại
                self.assertEqual(t.call_count, 2)
                p.write_bytes(b'xy')                                        # file đổi: đọc lại
                ocr.doc_chu(p)
                self.assertEqual(t.call_count, 3)
            ocr._DA_DOC.clear()

    def test_huy_giua_chung_khong_nho(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.png'
            p.write_bytes(b'x')
            ocr._DA_DOC.clear()
            with mock.patch.object(ocr, 'may_doc', return_value=(True, None)), mock.patch.object(ocr, 'tung_trang', side_effect=ocr.DaHuy()):
                with self.assertRaises(ocr.DaHuy):
                    ocr.doc_chu(p)
            self.assertEqual(ocr._DA_DOC, {})


class TestGhiVaoHo(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.con = csdl.mo(_du_an(Path(self.td.name)))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def test_tim_ho(self):
        cccd = self.con.execute('SELECT so_cccd FROM ho WHERE ma_ho = ?', (self.ma[1],)).fetchone()[0]
        if cccd:
            self.assertEqual(qc.tim_ho(self.con, qc.KetQuaQuet(so_cccd=cccd)), self.ma[1])
        self.assertEqual(qc.tim_ho(self.con, qc.KetQuaQuet(ho_ten='hộ thử 2')), self.ma[2])
        self.assertIsNone(qc.tim_ho(self.con, qc.KetQuaQuet(ho_ten='Không có')))
        self.assertIsNone(qc.tim_ho(self.con, qc.KetQuaQuet()))

    def test_ghi_thua_khop_to_thua(self):
        bo = BoSoan(self.con, self.ma[1])
        t = self.con.execute('SELECT so_to, so_thua FROM thua WHERE ma_ho = ?', (self.ma[1],)).fetchone()
        bo.pa.dat[:] = []                                                  # hộ chưa có dòng đất
        ds = [qc.DongDat(t[0], t[1], 'CLN', 'DAT_NONG_NGHIEP', Decimal('55.5'), ket_cau_mat_duong='DAT_SOI_DA_CAPPHOI'),
              qc.DongDat('99', '999', 'CLN', 'DAT_NONG_NGHIEP', Decimal(1))]
        them, thieu, trung = qc.ghi_thua_vao_ho(bo, ds)
        self.assertEqual((them, thieu, trung), (1, ['tờ 99 thửa 999'], []))
        self.assertEqual(bo.pa.dat[0].dien_tich, Decimal('55.5'))
        self.assertIn('đường đất', bo.pa.dat[0].ghi_chu)
        self.assertEqual(qc.ghi_thua_vao_ho(bo, ds[:1])[2], [f'tờ {t[0]} thửa {t[1]}'])          # quét lại: không thêm trùng
        self.assertEqual(len(bo.pa.dat), 1)
        # chưa lưu: file dự án không đổi cho tới khi người dùng bấm Lưu
        self.assertEqual(BoSoan(self.con, self.ma[1]).pa.dat[0].dien_tich, Decimal(101))


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestManHinh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')

    def _cua_so(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(_du_an(Path(self.tmp.name))))
        APP.processEvents()
        return w

    def test_hop_goi_y_ho_va_nut_theo_loai(self):
        w = self._cua_so()
        ma = w.con.execute("SELECT ma_ho FROM ho WHERE ho_ten = 'Hộ thử 1'").fetchone()[0]
        h = w.quet_thong_minh(files=['bb.pdf'], cho=False, doc=lambda p: BIEN_BAN)
        self.addCleanup(h.close)
        self.assertEqual(h.ho_chon(), ma)                                  # gợi ý đúng hộ theo họ tên trên giấy tờ
        self.assertEqual(h.nut_mo[0].text(), 'Đưa vào phương án của hộ')
        self.assertTrue(h.nut_mo[0].isEnabled())
        self.assertTrue(h.b_dua.isEnabled())
        h.o_loai[0].setCurrentIndex(h.o_loai[0].findData(qc.D_KHAC))        # người dùng đổi loại: nút đổi theo
        self.assertFalse(h.nut_mo[0].isEnabled())
        h.o_loai[0].setCurrentIndex(h.o_loai[0].findData(qc.D_DON_GIA))
        h.nut_mo[0].click()
        self.assertEqual((h.hanh_dong, h.loai_chon), ('mo_file', qc.D_DON_GIA))

    def test_chi_xem_khong_dua_vao_ho(self):
        from pabt.man_hinh_quet_chung import HopKetQuaQuet
        kq = qc.quet(['bb.pdf'], doc=lambda p: BIEN_BAN)
        h = HopKetQuaQuet(None, kq, True, True, [(1, 'A')], 1)
        self.addCleanup(h.close)
        self.assertFalse(h.b_dua.isEnabled())
        self.assertFalse(h.nut_mo[0].isEnabled())
        self.assertTrue(h.nut_mo[0].toolTip())

    def test_dua_vao_ho_chua_luu(self):
        w = self._cua_so()
        ma = w.con.execute("SELECT ma_ho FROM ho WHERE ho_ten = 'Hộ thử 1'").fetchone()[0]
        kq = qc.quet(['bb.pdf'], doc=lambda p: BIEN_BAN)
        cua, hop, (them, thieu, trung) = w.dua_ket_qua_quet_vao_ho(kq, ma, cho=False)
        self.addCleanup(cua.close)
        self.addCleanup(hop.close)
        self.assertEqual(them, 0)                                          # tự lập đã có dòng thửa này: không thêm trùng
        self.assertEqual(trung, ['tờ 11 thửa 101'])
        self.assertIn('xoài', hop.o_chu.toPlainText().lower())
        self.assertNotIn('ký tên', hop.o_chu.toPlainText().lower())

    def test_dua_vao_ho_them_dong_dat_len_cua_so(self):
        w = self._cua_so()
        ma = w.con.execute("SELECT ma_ho FROM ho WHERE ho_ten = 'Hộ thử 1'").fetchone()[0]
        bo = BoSoan(w.con, ma)
        bo.pa.dat[:] = []
        bo.luu()
        kq = qc.quet(['bb.pdf'], doc=lambda p: BIEN_BAN)
        cua, hop, (them, thieu, trung) = w.dua_ket_qua_quet_vao_ho(kq, ma, cho=False)
        cua.hoi_luu = lambda: True                                         # đóng khi còn thay đổi: không hiện hộp hỏi
        self.addCleanup(cua.close)
        self.addCleanup(hop.close)
        self.assertEqual((them, thieu, trung), (1, [], []))
        self.assertEqual(cua.bang[1].bang.rowCount(), 1)                        # hiện ngay trên bảng mục 1
        self.assertTrue(cua.bo.co_thay_doi)                                # chờ người dùng soát, bấm Lưu
        self.assertEqual(BoSoan(w.con, ma).pa.dat, [])                     # file chưa đổi
        cua.bo.luu()
        d = BoSoan(w.con, ma).pa.dat[0]
        self.assertEqual(d.dien_tich, Decimal('55.5'))
        self.assertIn('đường đất', d.ghi_chu)

    def test_dinh_tuyen_mo_dung_man_hinh(self):
        w = self._cua_so()
        with mock.patch.object(w, 'nhap_excel') as nx, mock.patch.object(w, 'nhap_chi_tiet') as nc:
            w.mo_file_quet('a.xlsx', qc.D_DU_AN)
            w.mo_file_quet('b.xlsx', qc.D_CHI_TIET)
        nx.assert_called_once_with('a.xlsx')
        nc.assert_called_once_with('b.xlsx')
        d = w.mo_file_quet('c.pdf', qc.D_HE_SO_K, cho=False)
        self.addCleanup(d.close)
        self.assertEqual(d.tabs.currentIndex(), 1)
        d2 = w.mo_file_quet('c.pdf', qc.D_BANG_GIA, cho=False)
        self.addCleanup(d2.close)
        self.assertEqual(d2.tabs.currentIndex(), d2.THE_CAP_NHAT)
        self.assertIsNone(w.mo_file_quet('c.pdf', qc.D_KHAC))


if __name__ == '__main__':
    unittest.main()
