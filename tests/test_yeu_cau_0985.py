"""Kiểm thử 0.9.85 (người dùng 14/10/2026): hồ sơ địa phương pabt_profile.json (dia_phuong) điều khiển cơ quan, căn cứ, mốc thời hạn,
kinh phí tổ chức thực hiện (tỷ lệ, làm tròn, phân bổ 85 / 15), quy tắc bản in, vị trí cột mẫu; gói mẫu in & cấu hình .pabtcfg
(goi_mau). Thư mục máy tạm (PABT_THU_MUC_MAY), dữ liệu giả."""
from __future__ import annotations
import io
import json
import os
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

import openpyxl

from pabt import dia_phuong, du_thao, goi_mau, in_an, lap_pa, thoi_han, to_chuc
from pabt.tien import tien_bang_chu
from tests.test_in_vua_chu import CoSo

GOC = Path(__file__).resolve().parents[1]


class CoSoMay(CoSo):
    """Dự án giả + thư mục máy tạm; hồ sơ địa phương về mặc định trước / sau mỗi bài."""

    def setUp(self):
        super().setUp()
        self.may = self.td / 'may'
        self.may.mkdir()
        self._env = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.may)})
        self._env.start()
        dia_phuong.nap_lai()

    def tearDown(self):
        self._env.stop()
        dia_phuong.nap_lai()
        super().tearDown()

    def ghi_ho_so(self, them: dict) -> None:
        dia_phuong.file_may().write_text(json.dumps(them, ensure_ascii=False), encoding='utf-8')
        dia_phuong.nap_lai()


class TestHoSoMacDinh(CoSoMay):
    def test_mac_dinh_dung_gia_tri_truoc_0985(self):
        self.assertEqual(dia_phuong.kiem_tra(dia_phuong.doc()), [])
        self.assertEqual(to_chuc.TEN, 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT CHI NHÁNH VĨNH CỬU')
        self.assertEqual(to_chuc.MAC_DINH['chuc_vu_ky'], 'Phó Giám đốc')
        self.assertEqual({k: v[1] for k, v in lap_pa.LOAI_KINH_PHI.items()}, {'tuyen': Decimal('3.5'), 'khac': Decimal('2.5')})
        self.assertTrue(lap_pa.CAN_CU_KINH_PHI.startswith('Quyết định số 08/2025/QĐ-UBND'))
        self.assertEqual({k: v[1] for k, v in thoi_han.MOC.items()}, {'tham_dinh': 15, 'thu_hoi_nn': 60, 'thu_hoi_pnn': 120, 'van_dong': 10})
        self.assertEqual((du_thao.SO_NGAY_NIEM_YET, du_thao.SO_NGAY_DOI_THOAI), (10, 30))
        self.assertEqual(dia_phuong.phan_bo_kinh_phi()[0][1] + dia_phuong.phan_bo_kinh_phi()[1][1], 100)
        self.assertEqual(dia_phuong.cot_mau('IN_BANGTONGHOP')['tong'], 22)          # V

    def test_file_may_ghi_de_tung_muc_va_nap_lai(self):
        self.ghi_ho_so({'ten_ho_so': 'Thử địa phương khác', 'co_quan': {'ten': 'BAN BỒI THƯỜNG THỬ'},
                        'kinh_phi_to_chuc': {'loai': {'khac': {'ten': 'Dự án khác', 'ty_le_toi_da': '2.0'}},
                                             'phan_bo': [{'ten': 'Đơn vị', 'ty_le': '80'}, {'ten': 'Xã', 'ty_le': '20'}]},
                        'thoi_han': {'niem_yet': {'so_ngay': 15, 'can_cu': 'thử'}}})
        self.assertEqual(dia_phuong.loi(), [])
        self.assertEqual(to_chuc.TEN, 'BAN BỒI THƯỜNG THỬ')
        self.assertEqual(to_chuc.TRUC_THUOC, 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT THÀNH PHỐ ĐỒNG NAI')     # mục không ghi: giữ mặc định
        self.assertEqual(lap_pa.LOAI_KINH_PHI['khac'][1], Decimal('2.0'))
        self.assertEqual(lap_pa.LOAI_KINH_PHI['tuyen'][1], Decimal('3.5'))
        self.assertEqual(du_thao.SO_NGAY_NIEM_YET, 15)
        self.assertEqual(du_thao.ngay_ket_thuc('2026-10-01'), '2026-10-16')         # niêm yết 15 ngày theo hồ sơ

    def test_file_may_sai_dung_mac_dinh_va_bao(self):
        self.ghi_ho_so({'kinh_phi_to_chuc': {'phan_bo': [{'ten': 'a', 'ty_le': '80'}, {'ten': 'b', 'ty_le': '30'}]},
                        'mau_in': {'IN_BANGTONGHOP': {'cot': {'tong': 'V1'}}}})
        loi = '\n'.join(dia_phuong.loi())
        self.assertIn('tổng tỷ lệ phải bằng 100%', loi)
        self.assertIn('chữ cột', loi)
        self.assertEqual(dia_phuong.phan_bo_kinh_phi()[0][1], 85)                   # đang dùng mặc định
        dia_phuong.file_may().write_text('{ hỏng', encoding='utf-8')
        dia_phuong.nap_lai()
        self.assertIn('sai cú pháp JSON', '\n'.join(dia_phuong.loi()))

    def test_ghi_may_tu_choi_ho_so_sai(self):
        with self.assertRaises(dia_phuong.LoiHoSo):
            dia_phuong.ghi_may({'thoi_han': {'tham_dinh': {'so_ngay': 0, 'can_cu': ''}}})
        self.assertFalse(dia_phuong.file_may().exists())


class TestBanInTheoHoSo(CoSoMay):
    def test_bang_tong_hop_kinh_phi_va_phan_bo_theo_ho_so(self):
        self.ghi_ho_so({'kinh_phi_to_chuc': {'lam_tron_den': 0,
                                             'phan_bo': [{'ten': 'Đơn vị', 'ty_le': '80'}, {'ten': 'Xã', 'ty_le': '20'}]}})
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')).active
        tong = next(r for r in range(13, 400) if ws.cell(r, 1).value == 'TỔNG CỘNG')
        self.assertTrue(str(ws[f'G{tong}'].value).startswith('=SUM(G13:'))
        self.assertTrue(str(ws[f'P{tong}'].value).startswith('=SUM(P13:'))
        self.assertIsNone(ws[f'N{tong}'].value)                                     # vị trí (chữ): không cộng
        self.assertIn(', 0)', ws[f'V{tong + 1}'].value)                             # làm tròn theo hồ sơ (0 = đến đồng)
        f = [ws[f'V{r}'].value for r in (tong + 2, tong + 3)]
        self.assertEqual(f, [f'=ROUND(V{tong + 1}*80%, 0)', f'=ROUND(V{tong + 1}*20%, 0)'])
        chu = ' '.join(str(ws.cell(r, 8).value) for r in (tong + 2, tong + 3))
        self.assertIn('80%', chu)
        self.assertIn('20%', chu)                                                    # chữ trong mẫu khớp công thức
        self.assertNotIn('85%', chu)

    def test_mac_dinh_giong_truoc(self):
        ws = openpyxl.load_workbook(in_an.lap_bang_tong_hop(self.con, self.td / 'bth.xlsx')).active
        tong = next(r for r in range(13, 400) if ws.cell(r, 1).value == 'TỔNG CỘNG')
        self.assertEqual([ws[f'V{r}'].value for r in (tong + 2, tong + 3)],
                         [f'=ROUND(V{tong + 1}*85%, -3)', f'=ROUND(V{tong + 1}*15%, -3)'])
        self.assertTrue(str(ws[f'V{tong + 1}'].value).endswith(', -3)'))


    def test_to_trinh_can_cu_theo_ho_so(self):
        from pabt import van_ban_trinh as vb
        self.assertIn('42/2025/QĐ-UBND', vb._noi_dung_to_trinh())
        self.ghi_ho_so({'can_cu_phap_ly': {'to_trinh': ['Căn cứ Quyết định số 99/2026/QĐ-UBND thử nghiệm;']}})
        nd = vb._noi_dung_to_trinh()
        self.assertIn('99/2026/QĐ-UBND', nd)
        self.assertNotIn('42/2025/QĐ-UBND', nd)

    def test_tien_bang_chu_van_ban_hanh_chinh(self):
        self.assertEqual(tien_bang_chu(Decimal('538569000'), cham=True),
                         'Năm trăm ba mươi tám triệu năm trăm sáu mươi chín nghìn đồng.')
        self.assertEqual(tien_bang_chu(1005), 'Một nghìn không trăm linh năm đồng')          # mặc định như cũ (nơi gọi thêm dấu chấm)


class TestGoiMau(CoSoMay):
    def _mau_rieng(self) -> Path:
        tm = goi_mau.thu_muc_mau_cai()
        tm.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()
        wb.active['A1'] = '{ho_ten}'
        f = tm / 'IN_CHITIET__Thu nghiem.xlsx'
        wb.save(f)
        return f


    def _goi_sua(self, sua) -> Path:
        ds = goi_mau.tao_goi(self.td / 'goc.pabtcfg')
        f = self.td / 'sua.pabtcfg'
        with zipfile.ZipFile(ds['file']) as z, zipfile.ZipFile(f, 'w') as zo:
            danh = json.loads(z.read('goi_mau.json'))
            for n in z.namelist():
                if n != 'goi_mau.json':
                    du = sua(n, z.read(n), danh, zo)
                    if du is not None:
                        zo.writestr(n, du)
            zo.writestr('goi_mau.json', json.dumps(danh))
        return f

    def test_tu_choi_goi_bi_sua_hoac_file_la(self):
        self._mau_rieng()                                                   # 1.0.20: không còn mẫu Excel đóng kèm - gói chỉ có mẫu riêng này
        def doi_noi_dung(n, du, danh, zo):
            return du + b' ' if n.startswith('mau_in/') else du
        with self.assertRaisesRegex(goi_mau.LoiGoiMau, 'SHA-256'):
            goi_mau.doc_goi(self._goi_sua(doi_noi_dung))

        def them_exe(n, du, danh, zo):
            if n == 'pabt_profile.json':
                import hashlib
                zo.writestr('mau_in/../x.exe', b'MZ')
                danh['tep'].append(dict(ten='mau_in/../x.exe', sha256=hashlib.sha256(b'MZ').hexdigest(), kich_thuoc=2))
            return du
        with self.assertRaises(goi_mau.LoiGoiMau):
            goi_mau.doc_goi(self._goi_sua(them_exe))

        def co_macro(n, du, danh, zo):
            if n == 'mau_in/IN_CHITIET__Thu nghiem.xlsx':
                import hashlib
                b = io.BytesIO()
                with zipfile.ZipFile(io.BytesIO(du)) as zi, zipfile.ZipFile(b, 'w') as zw:
                    for m in zi.namelist():
                        zw.writestr(m, zi.read(m))
                    zw.writestr('xl/vbaProject.bin', b'macro')
                du = b.getvalue()
                next(t for t in danh['tep'] if t['ten'] == n)['sha256'] = hashlib.sha256(du).hexdigest()
            return du
        with self.assertRaisesRegex(goi_mau.LoiGoiMau, 'macro'):
            goi_mau.doc_goi(self._goi_sua(co_macro))

    def test_ho_so_sai_trong_goi_khong_ghi_gi(self):
        def ho_so_sai(n, du, danh, zo):
            if n == 'pabt_profile.json':
                import hashlib
                hs = json.loads(du)
                hs['thoi_han']['tham_dinh']['so_ngay'] = -1
                du = json.dumps(hs).encode()
                next(t for t in danh['tep'] if t['ten'] == n)['sha256'] = hashlib.sha256(du).hexdigest()
            return du
        f = self._goi_sua(ho_so_sai)
        with self.assertRaisesRegex(goi_mau.LoiGoiMau, 'chưa hợp lệ'):
            goi_mau.cai(f)
        self.assertFalse(dia_phuong.file_may().exists())
        self.assertFalse(goi_mau.thu_muc_mau_cai().exists())

    def test_lenh_menu_cong_cu_va_nhap(self):
        from PySide6.QtWidgets import QApplication
        from pabt import giao_dien
        from pabt.app import CuaSoChinh
        app = QApplication.instance() or QApplication([])
        giao_dien.ap_dung(app)
        w = CuaSoChinh()
        try:
            ten = [a.text() for a in w.menu_tren['Công cụ'].actions()]
            self.assertIn('Xuất gói mẫu in && cấu hình…', ten)
            self.assertIn('Nhập gói mẫu in && cấu hình…', ten)
            ds = w.xuat_goi_mau(self.td / 'tu_app.pabtcfg', cho=False)
            kq = w.nhap_goi_mau(ds['file'], xac_nhan=False)
            self.assertTrue(kq['ho_so'])
        finally:
            w.close()


class TestDongGoi(unittest.TestCase):
    def test_dong_goi_ho_so_khong_dong_pdf(self):
        from pabt import cap_nhat
        self.assertIn('pabt_profile.json', cap_nhat.DU_LIEU)
        spec = (GOC / 'PABT.spec').read_text(encoding='utf-8')
        self.assertIn("HO_SO = 'pabt/pabt_profile.json'", spec)                    # 1.0.26: biến HO_SO (bản trung tính đổi sang file khác)
        self.assertIn("(HO_SO, 'pabt')", spec)
        self.assertNotIn("('mau_in', 'mau_in')", spec)                              # không đóng cả thư mục (PDF tham khảo)
        self.assertIn("'pabt/pabt_profile.json'", (GOC / 'bo_cai_win' / 'dung_exe38.py').read_text(encoding='utf-8'))
        ps = (GOC / 'bo_cai_win' / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn(r"HKCU:\Software\Classes\.pabtcfg", ps)
        self.assertIn('.pabtcfg', (GOC / 'bo_cai_win' / 'go_cai_dat.ps1').read_text(encoding='utf-8-sig'))

    def test_file_ho_so_dong_kem_hop_le(self):
        hs = json.loads((GOC / 'pabt' / 'pabt_profile.json').read_text(encoding='utf-8'))
        self.assertEqual(dia_phuong.kiem_tra(hs), [])
        with tempfile.TemporaryDirectory() as td:                # file máy chỉ ghi một mục: trộn với mặc định vẫn hợp lệ
            f = Path(td) / 'pabt_profile.json'
            f.write_text(json.dumps({'ten_ho_so': 'Một mục'}), encoding='utf-8')
            self.assertEqual(dia_phuong.kiem_tra_file(f)['co_quan']['ten'], dia_phuong.mac_dinh()['co_quan']['ten'])


if __name__ == '__main__':
    unittest.main()
