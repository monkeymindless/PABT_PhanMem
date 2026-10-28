"""Tạo gói cấu hình .pabtcfg hàng loạt cho nhiều đơn vị (goi_don_vi, man_hinh_goi_don_vi, chay.py tao-goi-don-vi - 28/10/2026).
Thư mục máy tạm, tên đơn vị GIẢ LẬP."""
from __future__ import annotations
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import openpyxl

from pabt import dia_phuong, goi_don_vi as gd, goi_mau, to_chuc

DV_A = dict(ten='BAN BỒI THƯỜNG THỬ NGHIỆM A', truc_thuoc='SỞ THỬ NGHIỆM', dia_chi='Số 1 đường Thử', don_vi_cap_tren='Sở Thử nghiệm',
            don_vi_tieu_de='Chi nhánh Thử A', dia_danh='Thị trấn Thử', ky_hieu_so='PA-BTA', chuc_vu_ky='Giám đốc',
            nguoi_ky='Nguyễn Văn Thử', nguoi_lap='Trần Thị Lập', nguoi_kiem_tra='Lê Văn Kiểm')
DV_B = dict(ten='BAN BỒI THƯỜNG THỬ NGHIỆM B', don_vi_tieu_de='Chi nhánh Thử B')


class CoSo(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_goi_dv_'))
        self.may = self.td / 'may'
        self.may.mkdir()
        self._env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.may)})
        self._env.start()
        dia_phuong.nap_lai()

    def tearDown(self):
        self._env.stop()
        dia_phuong.nap_lai()
        shutil.rmtree(self.td, ignore_errors=True)

    def excel(self, *dong) -> Path:
        """File Excel mẫu của phần mềm + các dòng đơn vị (dict theo khóa cột)."""
        p = gd.tao_file_mau(self.td / 'ds.xlsx')
        wb = openpyxl.load_workbook(p)
        ws = wb[gd.TEN_SHEET]
        for i, d in enumerate(dong, 2):
            for j, k in enumerate(gd.KHOA_COT, 1):
                ws.cell(i, j, d.get(k))
        wb.save(p)
        return p

    @staticmethod
    def ho_so_goi(f) -> dict:
        return goi_mau.doc_goi(f)['ho_so_moi']


class TestTaoHangLoat(CoSo):
    def test_file_mau_co_cot_va_huong_dan(self):
        p = gd.tao_file_mau(self.td / 'mau')
        self.assertEqual(p.suffix, '.xlsx')
        wb = openpyxl.load_workbook(p)
        self.assertEqual(wb.sheetnames, [gd.TEN_SHEET, gd.TEN_SHEET_HD])
        tieu_de = [c.value for c in wb[gd.TEN_SHEET][1]]
        self.assertEqual(len(tieu_de), len(gd.COT))
        self.assertTrue(tieu_de[0].endswith(' *'))
        self.assertIsNone(wb[gd.TEN_SHEET].cell(2, 1).value)            # không có dòng ví dụ (quên xóa thành một gói)
        self.assertEqual(gd.doc_danh_sach(p), [])

    def test_moi_dong_mot_goi_khong_doi_may(self):
        p = self.excel(DV_A, {}, dict(truc_thuoc='Thiếu tên'), DV_B)
        ra = self.td / 'ra'
        kq = gd.tao_hang_loat(p, ra)
        self.assertEqual(len(kq), 3)                                    # dòng trống bỏ qua
        self.assertEqual([bool(x['file']) for x in kq], [True, False, True])
        self.assertIn('Thiếu', kq[1]['loi'])
        self.assertEqual(kq[1]['dong'], 4)                              # số dòng Excel thật
        self.assertFalse(dia_phuong.file_may().exists())                # cấu hình máy này không đổi
        hs = self.ho_so_goi(kq[0]['file'])
        cq, bm = hs['co_quan'], hs['co_quan']['ban_in_mac_dinh']
        self.assertEqual((cq['ten'], cq['truc_thuoc'], cq['dia_chi']), (DV_A['ten'], DV_A['truc_thuoc'], DV_A['dia_chi']))
        for k in ('don_vi_cap_tren', 'don_vi_tieu_de', 'ky_hieu_so', 'chuc_vu_ky', 'nguoi_ky', 'nguoi_lap', 'nguoi_kiem_tra'):
            self.assertEqual(bm[k], DV_A[k], k)
        self.assertEqual((bm['dia_danh_don_vi'], hs['ban_in']['dia_danh_ngay']), ('Thị trấn Thử', 'Thị trấn Thử'))
        self.assertEqual(bm['don_vi_lap'], DV_A['ten'])                 # để trống: lấy tên tổ chức
        self.assertEqual(hs['ten_ho_so'], DV_A['ten'])
        self.assertEqual(kq[0]['file'].name, 'LARC_CauHinh_Chi_nhanh_Thu_A.pabtcfg')
        hs_b = self.ho_so_goi(kq[2]['file'])
        self.assertEqual(hs_b['co_quan']['truc_thuoc'], '')
        self.assertEqual(hs_b['co_quan']['ban_in_mac_dinh']['nguoi_ky'], '')

    def test_o_trong_khong_mang_ten_don_vi_cua_may(self):
        dia_phuong.file_may().write_text(json.dumps({'co_quan': {'ten': 'ĐƠN VỊ CỦA MÁY', 'dia_chi': 'Địa chỉ máy',
                                                                 'ban_in_mac_dinh': {'nguoi_ky': 'Người ký máy'}},
                                                     'thoi_han': {'niem_yet': {'so_ngay': 12, 'can_cu': 'Căn cứ máy'}}},
                                                    ensure_ascii=False), encoding='utf-8')
        dia_phuong.nap_lai()
        truoc = dia_phuong.file_may().read_bytes()
        kq = gd.tao_hang_loat(self.excel(DV_B), self.td / 'ra')
        hs = self.ho_so_goi(kq[0]['file'])
        self.assertEqual(hs['co_quan']['dia_chi'], '')
        self.assertEqual(hs['co_quan']['ban_in_mac_dinh']['nguoi_ky'], '')
        self.assertEqual(hs['thoi_han']['niem_yet']['so_ngay'], 12)       # nền = máy này: căn cứ, thời hạn giữ
        self.assertEqual(dia_phuong.file_may().read_bytes(), truoc)
        hs2 = self.ho_so_goi(gd.tao_hang_loat(self.excel(DV_B), self.td / 'ra2', nen=gd.NEN_MAC_DINH)[0]['file'])
        self.assertEqual(hs2['thoi_han']['niem_yet']['so_ngay'], dia_phuong.mac_dinh()['thoi_han']['niem_yet']['so_ngay'])

    def test_ten_file_trung_va_ten_file_rieng(self):
        kq = gd.tao_hang_loat(self.excel(DV_B, DV_B, dict(DV_A, ten_file='goi_rieng')), self.td / 'ra')
        self.assertEqual([x['file'].name for x in kq],
                         ['LARC_CauHinh_Chi_nhanh_Thu_B.pabtcfg', 'LARC_CauHinh_Chi_nhanh_Thu_B_2.pabtcfg', 'goi_rieng.pabtcfg'])

    def test_json_danh_sach_ho_so_va_nen_tinh_khac(self):
        ds = self.td / 'ds.json'
        ds.write_text(json.dumps({'don_vi': [dict(DV_A), {'Tên tổ chức làm nhiệm vụ bồi thường': 'BAN THEO TIÊU ĐỀ'}]},
                                 ensure_ascii=False), encoding='utf-8')
        hs1 = self.td / 'mot.json'
        hs1.write_text(json.dumps({'loai': dia_phuong.LOAI, 'co_quan': {'ten': 'BAN TỪ HỒ SƠ'}}, ensure_ascii=False), encoding='utf-8')
        nen = self.td / 'tinh.json'
        nen.write_text(json.dumps({'loai': dia_phuong.LOAI, 'co_quan': {'ten': 'KHÔNG ĐƯỢC LỌT'},
                                   'thoi_han': {'doi_thoai': {'so_ngay': 45, 'can_cu': 'Căn cứ tỉnh khác'}}},
                                  ensure_ascii=False), encoding='utf-8')
        kq = gd.tao_hang_loat([ds, hs1], self.td / 'ra', nen=str(nen))
        self.assertTrue(all(x['file'] for x in kq), kq)
        ten = [self.ho_so_goi(x['file'])['co_quan']['ten'] for x in kq]
        self.assertEqual(ten, [DV_A['ten'], 'BAN THEO TIÊU ĐỀ', 'BAN TỪ HỒ SƠ'])
        self.assertTrue(all(self.ho_so_goi(x['file'])['thoi_han']['doi_thoai']['so_ngay'] == 45 for x in kq))
        with self.assertRaises(gd.LoiDonVi):
            gd.tao_hang_loat(ds, self.td / 'ra2', nen=str(self.td / 'khong_co.json'))

    def test_goi_cai_vao_may_khac_co_ten_don_vi(self):
        f = gd.tao_hang_loat(self.excel(DV_A), self.td / 'ra')[0]['file']
        may2 = self.td / 'may2'
        may2.mkdir()
        with mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(may2)}):
            dia_phuong.nap_lai()
            kq = goi_mau.cai(f)
            self.assertTrue(kq['ho_so'])
            self.assertEqual(to_chuc.TEN, DV_A['ten'])
            self.assertEqual(to_chuc.MAC_DINH['nguoi_ky'], DV_A['nguoi_ky'])
        dia_phuong.nap_lai()
        self.assertNotEqual(to_chuc.TEN, DV_A['ten'])

    def test_dong_lenh(self):
        import chay
        p = self.excel(DV_A, DV_B)
        with mock.patch('builtins.print'):
            self.assertEqual(chay.main(['tao-goi-don-vi', str(p), '--nen', 'mac_dinh', '--kem-mau']), 0)
            self.assertEqual(len(list((self.td / 'Goi_cau_hinh').glob('*.pabtcfg'))), 2)
            self.assertEqual(chay.main(['mau-goi-don-vi', str(self.td / 'mau2.xlsx')]), 0)
            self.assertEqual(chay.main(['tao-goi-don-vi', str(self.excel(dict(dia_chi='x')))]), 1)    # có đơn vị lỗi
            self.assertEqual(chay.main(['tao-goi-don-vi']), 2)


class TestHop(CoSo):
    def test_xem_truoc_va_tao(self):
        from tests import APP
        if APP is None:
            self.skipTest('không có Qt')
        from pabt.man_hinh_goi_don_vi import HopGoiDonVi
        d = HopGoiDonVi()
        d.im_lang = True
        d.chon_file(self.excel(DV_A, dict(dia_chi='thiếu tên')))
        self.assertEqual(d.bang.rowCount(), 2)
        self.assertEqual(d.bang.item(0, 1).text(), DV_A['ten'])
        self.assertIn('Thiếu', d.bang.item(1, 5).text())
        self.assertTrue(d.b_tao.isEnabled())
        self.assertEqual(Path(d.o_ra.text()), self.td / 'Goi_cau_hinh')
        kq = d.tao(hien=False)
        self.assertEqual([bool(x['file']) for x in kq], [True, False])
        self.assertTrue(d.b_mo.isEnabled())
        d.o_file.setText(str(self.td / 'khong_co.xlsx'))
        d.nap()
        self.assertEqual(d.bang.rowCount(), 0)
        self.assertFalse(d.b_tao.isEnabled())
        d.close()
        d.deleteLater()


if __name__ == '__main__':
    unittest.main()
