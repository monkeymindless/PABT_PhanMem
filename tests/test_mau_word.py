"""1.0.16 (người dùng 22/10/2026): ba mẫu Word phương án chi tiết / bổ sung / điều chỉnh NHÚNG trong phần mềm (bố cục do mã dựng,
thông số ở hồ sơ địa phương ban_in.mau_word); đổi quy cách khi có quy định mới bằng file thông số / gói .pabtcfg - không cần bản cập nhật
phần mềm, không thư mục mẫu nào đi kèm bản cài."""
from __future__ import annotations

import json
import os
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import dia_phuong, in_word  # noqa: E402
from tests.test_giao_dien_navy_con import _Co  # noqa: E402

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _xml(p):
    with zipfile.ZipFile(p) as z:
        return ET.fromstring(z.read('word/document.xml'))


class TestThongSoMauWord(_Co):
    def tearDown(self):
        dia_phuong.khoi_phuc_mac_dinh()                 # file máy nằm trong thư mục máy tạm của bài; nạp lại mặc định cho bài sau
        super().tearDown()

    def test_mac_dinh_theo_yeu_cau(self):
        self.assertEqual(in_word.LE_MM, dict(trai=9, phai=7, tren=10, duoi=10))
        c = dia_phuong.lay('ban_in.mau_word.co_chu')
        # mẫu PDF "MAU IN CHI TIET WORD" (23/10/2026): chữ thân 10,5 pt, bảng 10 pt, ghi chú 7,5 pt
        self.assertEqual((c['co_quan'], c['quoc_hieu'], c['tieu_ngu']), (10.5, 10.5, 10.5))
        self.assertEqual((c['so_ngay'], c['du_thao']), (10.5, 10.5))                     # "Số:", ngày, "(DỰ THẢO)" cùng cỡ
        self.assertEqual((c['ten_loai'], c['trich_yeu'], c['du_an']), (10.5, 10.5, 10.5))
        self.assertEqual((c['thong_tin'], c['de_muc'], c['nguon_goc']), (10.5, 10.5, 10.5))
        self.assertEqual((c['bang'], c['ghi_chu'], c['chu_ky']), (10, 7.5, 10.5))
        self.assertEqual(in_word.trang_thai_thong_so(), 'Nhúng chuẩn')

    def test_xuat_sua_nhap_khoi_phuc(self):
        f = in_word.xuat_thong_so(self.td / 'mau_word.json')
        x = json.loads(f.read_text(encoding='utf-8'))
        self.assertEqual(x['loai'], in_word.LOAI_THONG_SO)
        x['mau_word']['co_chu']['bang'] = 12
        x['mau_word']['le_mm']['trai'] = 20
        f.write_text(json.dumps(x, ensure_ascii=False), encoding='utf-8')
        doi = in_word.nhap_thong_so(f)
        self.assertEqual(sorted(doi), ['co_chu', 'le_mm'])
        self.assertEqual((in_word.CO_BANG, in_word.LE_MM['trai']), (12, 20))                # áp dụng ngay, không khởi động lại
        self.assertEqual(in_word.trang_thai_thong_so(), 'Tùy chỉnh')
        may = json.loads(dia_phuong.file_may().read_text(encoding='utf-8'))
        self.assertEqual(may['ban_in']['mau_word'], {'co_chu': {'bang': 12}, 'le_mm': {'trai': 20}})   # chỉ ghi phần KHÁC mặc định
        p = in_word.xuat_chi_tiet_docx(self.con, 1, self.td / 'ct.docx')
        d = _xml(p)
        mar = d.find(f'.//{W}sectPr/{W}pgMar')
        self.assertEqual(round(int(mar.get(W + 'left')) / 1440 * 25.4), 20)
        stt = next(r for r in d.iter(W + 'r') if ''.join(t.text or '' for t in r.iter(W + 't')) == 'STT')
        self.assertEqual(stt.find(f'{W}rPr/{W}sz').get(W + 'val'), '24')                    # 12 pt
        in_word.khoi_phuc_thong_so()
        self.assertEqual((in_word.CO_BANG, in_word.LE_MM['trai']), (10, 9))
        self.assertEqual(in_word.trang_thai_thong_so(), 'Nhúng chuẩn')
        self.assertFalse(dia_phuong.file_may().exists())

    def test_thong_so_sai_khong_ghi(self):
        f = self.td / 'sai.json'
        for sai in ({'co_chu': {'bang': 99}}, {'le_mm': {'trai': -1}}, {'trich_yeu': ''}, {'gach_chan_ho_pt': 'x'}):
            f.write_text(json.dumps({'loai': in_word.LOAI_THONG_SO, 'mau_word': sai}), encoding='utf-8')
            with self.assertRaises(dia_phuong.LoiHoSo):
                in_word.nhap_thong_so(f)
            self.assertFalse(dia_phuong.file_may().exists())
        f.write_text('{"loai": "khac"}', encoding='utf-8')
        with self.assertRaises(dia_phuong.LoiHoSo):
            in_word.nhap_thong_so(f)

    def test_goi_pabtcfg_mang_thong_so(self):
        """Kênh cập nhật thứ hai: gói .pabtcfg (hồ sơ đầy đủ) mang cả thông số mẫu Word sang máy khác."""
        from pabt import goi_mau
        in_word.nhap_thong_so(self._file({'co_chu': {'ghi_chu': 10}}))
        goi_mau.tao_goi(self.td / 'g.pabtcfg', co_mau=False)
        with zipfile.ZipFile(self.td / 'g.pabtcfg') as z:
            hs = json.loads(z.read(dia_phuong.TEN_FILE))
        self.assertEqual(hs['ban_in']['mau_word']['co_chu']['ghi_chu'], 10)

    def _file(self, mau_word):
        f = self.td / 'tam.json'
        f.write_text(json.dumps({'loai': in_word.LOAI_THONG_SO, 'mau_word': mau_word}), encoding='utf-8')
        return f


class TestKhongThuMucMau(unittest.TestCase):
    """Bản cài không đóng thư mục mau_in: mẫu in chuẩn nhúng trong mã, mẫu Word dựng bằng mã."""

    def test_spec_va_dung_exe38_khong_dong_mau_in(self):
        goc = Path(__file__).resolve().parents[1]
        spec = (goc / 'PABT.spec').read_text(encoding='utf-8')
        self.assertNotRegex(re.sub(r'#[^\n]*', '', spec), r"'mau_in'")
        dung = (goc / 'bo_cai_win' / 'dung_exe38.py').read_text(encoding='utf-8')
        self.assertNotRegex(re.sub(r'#[^\n]*', '', dung), r"'mau_in'|\"mau_in\"")


if __name__ == '__main__':
    unittest.main()


class TestDongCoQuan(unittest.TestCase):
    """23/10/2026: dự án cũ ghi 'Thành phố Đồng Nai' ở ô tên đơn vị trên tiêu đề -> mất dòng gạch chân 'CHI NHÁNH …'."""

    def test_o_tieu_de_la_ten_thanh_pho(self):
        from pabt import in_word
        cap, cn = in_word.dong_co_quan({'DON_VI_CAP_TREN_2DONG': 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT', 'DON_VI_TIEU_DE': 'THÀNH PHỐ ĐỒNG NAI',
                                        'DON_VI_LAP': 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT CHI NHÁNH VĨNH CỬU'})
        self.assertEqual(cn, 'CHI NHÁNH VĨNH CỬU')
        self.assertEqual(cap.split('\n'), ['TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT', 'THÀNH PHỐ ĐỒNG NAI'])

    def test_o_tieu_de_da_la_chi_nhanh_hoac_trung_voi_cap_tren(self):
        from pabt import in_word
        cap, cn = in_word.dong_co_quan({'DON_VI_CAP_TREN_2DONG': 'TRUNG TÂM\nTHÀNH PHỐ ĐỒNG NAI', 'DON_VI_TIEU_DE': 'CHI NHÁNH A', 'DON_VI_LAP': ''})
        self.assertEqual((cap, cn), ('TRUNG TÂM\nTHÀNH PHỐ ĐỒNG NAI', 'CHI NHÁNH A'))
        cap, cn = in_word.dong_co_quan({'DON_VI_CAP_TREN_2DONG': 'TRUNG TÂM\nTHÀNH PHỐ ĐỒNG NAI', 'DON_VI_TIEU_DE': 'THÀNH PHỐ ĐỒNG NAI',
                                        'DON_VI_LAP': ''})
        self.assertEqual(cn, 'CHI NHÁNH VĨNH CỬU')          # lấy từ hồ sơ địa phương
        self.assertEqual(cap, 'TRUNG TÂM\nTHÀNH PHỐ ĐỒNG NAI')
