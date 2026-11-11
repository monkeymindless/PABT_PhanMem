"""Đợt 7 (1.0.98): nhập danh sách hộ / thửa từ phần mềm địa chính - bảng thuộc tính .dbf (gCadas / ArcGIS / MapInfo / Famis), tên trường
viết liền (SHBANDO, SHTHUA, DIENTICH, KHMDSD, TENCHU), chữ phông cũ TCVN3 / VNI, CSV ANSI Windows-1258, ô diện tích ghi phép tính."""
from __future__ import annotations

import struct
import tempfile
import unicodedata
import unittest
from pathlib import Path

from pabt import chuan_chu, nguon_luoi, nhap_tho

_NGUOC_TCVN3 = {v: chr(k) for k, v in chuan_chu._TCVN3.items()}


def tcvn3(u: str) -> str:
    """Chữ Unicode -> mã TCVN3 (như file .VnTime đọc thẳng)."""
    return ''.join(_NGUOC_TCVN3.get(c, c) for c in u)


def ghi_dbf(p: Path, truong: list, dong: list, ma: str = 'latin-1', xoa: tuple = ()) -> None:
    dai_dau = 32 + 32 * len(truong) + 1
    dai_bg = 1 + sum(t[2] for t in truong)
    b = bytearray(struct.pack('<BBBBIHH20x', 0x03, 126, 1, 1, len(dong), dai_dau, dai_bg))
    for ten, kieu, dai, le in truong:
        b += ten.encode('ascii').ljust(11, b'\0') + kieu.encode() + b'\0' * 4 + bytes([dai, le]) + b'\0' * 14
    b += b'\r'
    for i, r in enumerate(dong):
        b += b'*' if i in xoa else b' '
        for (_ten, kieu, dai, _le), v in zip(truong, r):
            s = (str(v).rjust(dai) if kieu == 'N' else str(v).ljust(dai)).encode(ma)
            b += s[:dai].ljust(dai, b' ')
    b += b'\x1a'
    p.write_bytes(bytes(b))


def ma_1258(u: str) -> bytes:
    """Unicode -> Windows-1258 như Excel lưu CSV: nguyên âm mũ / móc dựng sẵn (â ơ ư), dấu thanh là dấu kết hợp."""
    ra = []
    for c in unicodedata.normalize('NFC', u):
        try:
            ra.append(c.encode('cp1258'))
            continue
        except UnicodeEncodeError:
            pass
        d = unicodedata.normalize('NFD', c)
        mu = ''.join(x for x in d[1:] if x in '̛̂̆')          # mũ, trăng, móc: gộp vào chữ gốc
        thanh = ''.join(x for x in d[1:] if x not in mu)
        ra.append((unicodedata.normalize('NFC', d[0] + mu) + thanh).encode('cp1258'))
    return b''.join(ra)


TRUONG = [('SHBANDO', 'N', 4, 0), ('SHTHUA', 'N', 5, 0), ('DIENTICH', 'N', 10, 1), ('KHMDSD', 'C', 6, 0), ('TENCHU', 'C', 40, 0),
          ('DIACHI', 'C', 50, 0), ('NGAYCAP', 'D', 8, 0)]


class TestDbf(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='dot7_'))

    def test_dbf_tcvn3_ten_truong_liền(self):
        p = self.td / 'thua.dbf'
        ghi_dbf(p, TRUONG, [
            (12, 105, '1250.5', 'ONT', tcvn3('Nguyễn Văn Bình'), tcvn3('ấp Trung Hưng, xã Bàu Hàm'), '20240115'),
            (12, 106, '300.0', 'CLN', tcvn3('Trần Thị Đào'), tcvn3('ấp Trung Hưng, xã Bàu Hàm'), ''),
            (99, 999, '1', 'ONT', 'Ban ghi da xoa', 'x', ''),
            (13, 7, '88.25', 'LUC', tcvn3('Lê Văn Ước'), tcvn3('ấp 3, xã Bàu Hàm'), '')], xoa=(2,))
        kq = nhap_tho.doc(p)
        self.assertEqual({k: kq.bo_cot.cot[k] for k in ('so_to', 'so_thua', 'dt_thu_hoi', 'loai_dat', 'ho_ten', 'dia_chi')},
                         dict(so_to=0, so_thua=1, dt_thu_hoi=2, loai_dat=3, ho_ten=4, dia_chi=5))
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Nguyễn Văn Bình', 'Trần Thị Đào', 'Lê Văn Ước'])
        self.assertEqual(kq.ho[0]['dia_chi'], 'ấp Trung Hưng, xã Bàu Hàm')
        # số DBF dấu chấm thập phân -> đúng giá trị (không đọc 1250.5 thành 12.505), bản ghi đã xóa bị bỏ
        self.assertEqual([(t['so_to'], t['so_thua'], t['dt_thu_hoi']) for t in kq.thua],
                         [('12', '105', '1250.5'), ('12', '106', '300'), ('13', '7', '88.25')])
        self.assertTrue(any('TCVN3' in t for t in kq.thong_bao))

    def test_dbf_utf8_khong_doi_chu(self):
        p = self.td / 'u.dbf'
        ghi_dbf(p, TRUONG, [(1, 2, '50', 'ONT', 'Phạm Thị Hường', 'ấp 1', '')], ma='utf-8')
        kq = nhap_tho.doc(p)
        self.assertEqual(kq.ho[0]['ho_ten'], 'Phạm Thị Hường')
        self.assertFalse(any('TCVN3' in t or 'VNI' in t for t in kq.thong_bao))

    def test_dbf_hong_bao_loi_tieng_viet(self):
        p = self.td / 'hong.dbf'
        p.write_bytes(b'khong phai dbf')
        with self.assertRaises(nhap_tho.LoiNhap):
            nguon_luoi.lay_nguon(p)

    def test_o_dbf_ngay_so(self):
        giai = lambda b: b.decode('latin-1')      # noqa: E731
        self.assertEqual(nguon_luoi._o_dbf('D', b'20240115', 0, giai), '15/01/2024')
        self.assertEqual(nguon_luoi._o_dbf('N', b'  1070.50', 2, giai), '1070,5')
        self.assertEqual(nguon_luoi._o_dbf('N', b'    35', 0, giai), 35)
        self.assertIsNone(nguon_luoi._o_dbf('N', b'   ***', 0, giai))


class TestCsvMaCu(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='dot7c_'))

    def test_csv_vni_cong_thuc(self):
        p = self.td / 'vni.csv'
        p.write_bytes('STT;Ho ten;Dia chi;To;Thua;DT thu hoi\n1;Nguyeãn Vaên Bình;aáp 1;5;20;=12*3,5\n'
                      '2;Traàn Thò Ñaøo;aáp 1;5;21;120+35,5\n3;Leâ Thò Hoa;aáp 2;5;22;10/3\n'.encode('latin-1'))
        kq = nhap_tho.doc(p)
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Nguyễn Văn Bình', 'Trần Thị Đào', 'Lê Thị Hoa'])
        self.assertEqual(kq.ho[0]['dia_chi'], 'ấp 1')
        # phép tính trong ô diện tích: làm tròn như ô số lượng phương án (2 chữ số)
        self.assertEqual([t['dt_thu_hoi'] for t in kq.thua], ['42', '155.5', '3.33'])
        self.assertTrue(any('VNI' in t for t in kq.thong_bao))

    def test_csv_windows_1258(self):
        p = self.td / 'w.csv'
        chu = 'Họ và tên,Địa chỉ,Tờ,Thửa,Diện tích thu hồi\nPhạm Thị Hường,ấp 2,3,4,"55,5"\n'
        p.write_bytes(ma_1258(chu))
        kq = nhap_tho.doc(p)
        self.assertEqual(kq.ho[0]['ho_ten'], 'Phạm Thị Hường')
        self.assertEqual(kq.thua[0]['dt_thu_hoi'], '55.5')

    def test_csv_utf8_unicode_giu_nguyen(self):
        p = self.td / 'u.csv'
        p.write_text('Họ và tên,Địa chỉ,Tờ,Thửa,Diện tích thu hồi\nĐỗ Văn Lâm,"ấp Hà Tây",3,4,120\n', encoding='utf-8')
        kq = nhap_tho.doc(p)
        self.assertEqual((kq.ho[0]['ho_ten'], kq.ho[0]['dia_chi']), ('Đỗ Văn Lâm', 'ấp Hà Tây'))
        self.assertFalse(kq.thong_bao and any('phông' in t for t in kq.thong_bao))


class TestDoanMaCu(unittest.TestCase):
    def test_unicode_that_khong_doi(self):
        luoi = [['Họ và tên', 'Địa chỉ'], ['Lê Hà', 'Bà Rịa'], ['Hà Lâm', 'ấp Tân Hòa']]
        self.assertEqual(chuan_chu.sua_cac_o(luoi), (luoi, ''))

    def test_latin1_le_te_khong_doi(self):
        # vài ô Latin-1 có dấu ("Hà", "Lâm") trong bảng Unicode: không đủ chắc để đổi
        self.assertEqual(chuan_chu.doan_ma_cu_cac_o(['Hà', 'Lâm', 'Đồng Nai', 'Bàu Hàm', 'Trảng Bom']), '')

    def test_ten_truong_gon(self):
        for ten, truong in (('SoTo', 'so_to'), ('SH_THUA', 'so_thua'), ('Dien_Tich', 'dt_thu_hoi'), ('MDSD', 'loai_dat'),
                            ('TenChu', 'ho_ten'), ('DiaChi', 'dia_chi'), ('SoCMND', 'so_cccd'), ('DTThuHoi', 'dt_thu_hoi')):
            d = nhap_tho._diem_cot(nhap_tho.chuan_hoa(ten))
            self.assertEqual(max(d, key=d.get), truong, ten)


if __name__ == '__main__':
    unittest.main()
