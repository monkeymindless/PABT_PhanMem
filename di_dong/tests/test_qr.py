"""Kiểm bộ tạo mã QR (di_dong/qr.py): số liệu mẫu đã công bố của chuẩn + một bộ ĐỌC NGƯỢC viết riêng ở đây (đọc định dạng, bỏ mặt nạ,
đọc ô theo đường zíc zắc, tách khối, kiểm hội chứng Reed-Solomon bằng cách thế α^i - khác cách tính lúc tạo - rồi giải ra chữ)."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import qr  # noqa: E402

# ví dụ "HELLO WORLD" 1-M (chế độ chữ số-chữ cái) trong tài liệu hướng dẫn chuẩn QR: 16 byte dữ liệu -> 10 byte sửa lỗi
DU_MAU = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
EC_MAU = [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


def _mu():
    """Bảng lũy thừa / logarit của α trong GF(2^8) (đa thức 0x11D) - dựng riêng, không dùng qr._nhan."""
    mu, log, x = [0] * 512, [0] * 256, 1
    for i in range(255):
        mu[i], log[x] = x, i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        mu[i] = mu[i - 255]
    return mu, log


MU, LOG = _mu()


def _nhan(a, b):
    return 0 if a == 0 or b == 0 else MU[LOG[a] + LOG[b]]


def hoi_chung_bang_0(khoi, so_ec):
    """Mọi hội chứng S_i = khối(α^i), i = 0..so_ec-1 bằng 0 <=> không lỗi."""
    for i in range(so_ec):
        s = 0
        for b in khoi:
            s = _nhan(s, MU[i]) ^ b
        if s:
            return False
    return True


def doc_nguoc(luoi):
    n = len(luoi)
    pb = (n - 17) // 4
    # bit định dạng bản thứ nhất quanh ô dò góc trên trái: luoi[hàng][cột]
    bit_dd = [luoi[i][8] for i in range(6)] + [luoi[7][8], luoi[8][8], luoi[8][7]] + [luoi[8][14 - i] for i in range(9, 15)]
    so = sum(1 << i for i, v in enumerate(bit_dd) if v) ^ 0x5412
    muc, mat_na = so >> 13, (so >> 10) & 7
    assert muc == 0, 'mức sửa lỗi phải là M'
    mau = qr._Luoi(pb)
    mau.mau_co_dinh()                       # biết ô nào là ô chức năng
    ds_bit = []
    cot = n - 1
    while cot > 0:
        if cot == 6:
            cot -= 1
        hang_lan = range(n - 1, -1, -1) if ((n - 1 - cot) // 2) % 2 == 0 else range(n)
        for y in hang_lan:
            for x in (cot, cot - 1):
                if not mau.ham[y][x]:
                    v = luoi[y][x] ^ qr.DIEU_KIEN_MAT_NA[mat_na](x, y)
                    ds_bit.append(1 if v else 0)
        cot -= 2
    tong = qr.so_o_du_lieu(pb) // 8
    tu = [int(''.join(map(str, ds_bit[i * 8:i * 8 + 8])), 2) for i in range(tong)]
    so_khoi, ec = qr._KHOI_M[pb]
    ngan = so_khoi - tong % so_khoi
    dai = tong // so_khoi
    do_dai = [dai - ec + (0 if i < ngan else 1) for i in range(so_khoi)]
    khoi = [[] for _ in range(so_khoi)]
    k = 0
    for i in range(max(do_dai)):
        for j in range(so_khoi):
            if i < do_dai[j]:
                khoi[j].append(tu[k])
                k += 1
    for i in range(ec):
        for j in range(so_khoi):
            khoi[j].append(tu[k])
            k += 1
    for j in range(so_khoi):
        assert hoi_chung_bang_0(khoi[j], ec), f'khối {j} sai mã sửa lỗi'
    du = [b for j in range(so_khoi) for b in khoi[j][:do_dai[j]]]
    bit = ''.join(f'{b:08b}' for b in du)
    assert bit[:4] == '0100', 'phải là chế độ byte'
    dai_dl = 8 if pb <= 9 else 16
    so_byte = int(bit[4:4 + dai_dl], 2)
    p = 4 + dai_dl
    return bytes(int(bit[p + 8 * i:p + 8 * i + 8], 2) for i in range(so_byte)).decode('utf-8'), mat_na


class TestSoLieuMau(unittest.TestCase):
    def test_reed_solomon_vi_du_chuan(self):
        self.assertEqual(qr._du_rs(DU_MAU, qr._uoc_rs(10)), EC_MAU)
        self.assertTrue(hoi_chung_bang_0(DU_MAU + EC_MAU, 10))

    def test_chuoi_dinh_dang_va_phien_ban(self):
        g = qr._Luoi(7)
        g.dinh_dang(0)
        bit = [g.o[i][8] for i in range(6)] + [g.o[7][8], g.o[8][8], g.o[8][7]] + [g.o[8][14 - i] for i in range(9, 15)]
        self.assertEqual(''.join('1' if v else '0' for v in reversed(bit)), '101010000010010')     # M, mặt nạ 0
        g.phien_ban()
        bit = [g.o[g.co - 11 + i % 3][i // 3] for i in range(18)]                                 # khối dưới trái
        self.assertEqual(''.join('1' if v else '0' for v in reversed(bit)), '000111110010010100')  # phiên bản 7

    def test_suc_chua_va_can_chinh(self):
        self.assertEqual([qr.so_o_du_lieu(v) // 8 for v in (1, 2, 7, 10)], [26, 44, 196, 346])
        self.assertEqual([qr.so_byte_du_lieu(v) for v in (1, 4, 10)], [16, 64, 216])
        self.assertEqual(qr.vi_tri_can_chinh(7), [6, 22, 38])
        self.assertEqual(qr.vi_tri_can_chinh(10), [6, 28, 50])


class TestDocNguoc(unittest.TestCase):
    def test_doc_lai_dung_chu_moi_co(self):
        for chu in ('https://vd.github.io/larc-field/', 'https://ten-nguoi-dung.github.io/larc-field-mobile/index.html',
                    'Kiểm đếm thực địa', 'x' * 120, 'https://a.b/' + 'y' * 190):
            for m in (None, 0, 3, 5, 7):
                with self.subTest(chu=chu[:30], m=m):
                    g = qr.ma_qr(chu, m)
                    self.assertEqual(len(g), len(g[0]))
                    kq, mat_na = doc_nguoc(g)
                    self.assertEqual(kq, chu)
                    if m is not None:
                        self.assertEqual(mat_na, m)

    def test_qua_dai(self):
        with self.assertRaises(qr.LoiQR):
            qr.ma_qr('z' * 300)

    def test_svg(self):
        s = qr.svg('https://vd.github.io/larc-field/')
        self.assertTrue(s.startswith('<svg') and 'path d="M' in s)


if __name__ == '__main__':
    unittest.main()
