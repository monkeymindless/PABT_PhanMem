"""24/10/2026: bản thương mại - tên phần mềm theo hồ sơ (co_quan.ten_phan_mem); từ 1.0.27 hồ sơ địa phương MẶC ĐỊNH (pabt/pabt_profile.json) là hồ sơ
TRUNG TÍNH: không có tên đơn vị / địa phương nào (hồ sơ Đồng Nai cũ ở ho_so_don_vi/). Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

GOC = Path(__file__).resolve().parents[1]
TRUNG_TINH = GOC / 'pabt' / 'pabt_profile.json'
RIENG = ('Vĩnh Cửu', 'Đồng Nai', 'Trị An', 'VĨNH CỬU', 'ĐỒNG NAI', 'TTPTQĐ', 'QĐ 18', 'QĐ-UBND')


class TestHoSoTrungTinh(unittest.TestCase):
    def test_hop_le_va_khong_con_ten_don_vi_dia_phuong(self):
        from pabt import dia_phuong
        hs = json.loads(TRUNG_TINH.read_text(encoding='utf-8-sig'))
        self.assertEqual(dia_phuong.kiem_tra(dia_phuong.tron(dia_phuong.mac_dinh(), hs)), [])
        chu = json.dumps(hs, ensure_ascii=False)
        for k in RIENG:
            self.assertNotIn(k, chu, f'hồ sơ trung tính còn "{k}"')
        self.assertEqual(hs['ban_in']['dia_danh_ngay'], '')
        self.assertEqual(hs['co_quan']['ban_in_mac_dinh']['ky_hieu_so'], '')

    def test_tien_to_o_cai_dat_trong_va_co_chu_goi_y(self):
        from pabt import dia_phuong
        hs = json.loads(TRUNG_TINH.read_text(encoding='utf-8-sig'))
        for k in ('ten', 'truc_thuoc', 'dia_chi'):
            self.assertEqual(hs['co_quan'][k], '', k)
        self.assertEqual(dia_phuong.kiem_tra(dia_phuong.tron(dia_phuong.mac_dinh(), hs)), [])


class TestBanTrungTinhChay(unittest.TestCase):
    """Chạy thật với hồ sơ trung tính làm hồ sơ máy: bản in Word / bảng tổng hợp không lỗi, không còn tên đơn vị cũ."""

    def setUp(self):
        from pabt import dia_phuong
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        (self.td / 'may').mkdir()
        (self.td / 'may' / 'pabt_profile.json').write_bytes(TRUNG_TINH.read_bytes())
        dia_phuong.nap_lai()

        def tra():
            if cu is None:
                os.environ.pop('PABT_THU_MUC_MAY', None)
            else:
                os.environ['PABT_THU_MUC_MAY'] = cu
            dia_phuong.nap_lai()
        self.addCleanup(tra)

    def test_tieu_de_va_ban_in(self):
        import openpyxl

        from pabt import csdl, in_an, in_word, to_chuc
        from tests.test_toc_do import _du_an
        self.assertEqual(to_chuc.TEN, '')
        self.assertEqual(to_chuc.dong_phu(), '')
        self.assertEqual(to_chuc.MAC_DINH['ky_hieu_so'], '')
        con = csdl.mo(_du_an(self.td, 2))
        self.addCleanup(con.close)
        with con:                                          # dự án giả lập ghi sẵn đơn vị cũ -> xóa để dùng mặc định trung tính
            con.execute("UPDATE du_an SET don_vi_cap_tren = '', don_vi_tieu_de = '', don_vi_lap = '', ky_hieu_so = ''")
        ma = con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        f = in_word.xuat_chi_tiet_docx(con, ma, self.td / 'ct.docx')
        with zipfile.ZipFile(f) as z:
            x = z.read('word/document.xml').decode('utf-8')
        chu = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x))
        for k in RIENG:
            self.assertNotIn(k, chu)
        b = in_an.lap_bang_tong_hop(con, self.td / 'b.xlsx')
        ws = openpyxl.load_workbook(b).active
        tat_ca = ' '.join(str(o.value) for o in ws._cells.values() if isinstance(o.value, str))
        for k in RIENG:
            self.assertNotIn(k, tat_ca)


class TestTenPhanMem(unittest.TestCase):
    def test_doi_ten_phan_mem_theo_ho_so_hien_tren_bang_tieu_de(self):
        from PySide6.QtWidgets import QApplication

        from pabt import dia_phuong, giao_dien
        from pabt.app import CuaSoChinh
        app = QApplication.instance() or QApplication([])
        giao_dien.ap_dung(app)
        with tempfile.TemporaryDirectory() as td:
            cu = os.environ.get('PABT_THU_MUC_MAY')
            os.environ['PABT_THU_MUC_MAY'] = td
            try:
                dia_phuong.nap_lai()
                w = CuaSoChinh()
                self.addCleanup(w.close)
                self.assertTrue(w.banner_ten.lb_ten.text().startswith('PHẦN MỀM LẬP PHƯƠNG ÁN'))        # mặc định
                dia_phuong.dat_muc_may(('co_quan', 'ten_phan_mem'), 'PHẦN MỀM QUẢN LÝ ĐỀN BÙ ABC')
                w._lam_moi_don_vi()
                self.assertEqual(w.banner_ten.lb_ten.text(), 'PHẦN MỀM QUẢN LÝ ĐỀN BÙ ABC')
            finally:
                if cu is None:
                    os.environ.pop('PABT_THU_MUC_MAY', None)
                else:
                    os.environ['PABT_THU_MUC_MAY'] = cu
                dia_phuong.nap_lai()

    def test_o_nhap_o_the_co_quan(self):
        from pabt.man_hinh_cau_hinh import CO_QUAN
        self.assertIn('ten_phan_mem', [k for k, _ in CO_QUAN])


if __name__ == '__main__':
    unittest.main()
