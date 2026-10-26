"""Mã QR (ISO/IEC 18004) bằng Python thuần - cho trang cài đặt LARC Field Mobile (quét bằng camera để mở địa chỉ ứng dụng).

Chế độ byte (UTF-8), mức sửa lỗi M (~15%), phiên bản 1-10 (tới 213 byte - đủ cho địa chỉ trang web), chọn mặt nạ theo điểm phạt
chuẩn. Cách dựng theo thư viện QR Code generator của Project Nayuki (MIT). `ma_qr(chu)` -> lưới [hàng][cột] bool (True = ô đen, chưa
có lề); `svg(chu)` -> ảnh SVG có lề 4 ô. Không dùng Qt / thư viện ngoài.
"""
from __future__ import annotations

# mức M: (số khối, số byte sửa lỗi mỗi khối) theo phiên bản 1-10
_KHOI_M = {1: (1, 10), 2: (1, 16), 3: (1, 26), 4: (2, 18), 5: (2, 24), 6: (4, 16), 7: (4, 18), 8: (4, 22), 9: (5, 22), 10: (5, 26)}
_BIT_MUC_M = 0          # bit mức sửa lỗi trong thông tin định dạng: L 1, M 0, Q 3, H 2
PHIEN_BAN_TOI_DA = 10


class LoiQR(ValueError):
    pass


def _bit(x: int, i: int) -> bool:
    return (x >> i) & 1 != 0


def _nhan(x: int, y: int) -> int:
    """Nhân trong GF(2^8), đa thức 0x11D."""
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _uoc_rs(bac: int) -> list:
    kq = [0] * (bac - 1) + [1]
    goc = 1
    for _ in range(bac):
        for j in range(len(kq)):
            kq[j] = _nhan(kq[j], goc)
            if j + 1 < len(kq):
                kq[j] ^= kq[j + 1]
        goc = _nhan(goc, 0x02)
    return kq


def _du_rs(du: list, uoc: list) -> list:
    kq = [0] * len(uoc)
    for b in du:
        f = b ^ kq.pop(0)
        kq.append(0)
        for i, c in enumerate(uoc):
            kq[i] ^= _nhan(c, f)
    return kq


def so_o_du_lieu(pb: int) -> int:
    """Số ô (bit) dùng cho dữ liệu + sửa lỗi của phiên bản pb."""
    kq = (16 * pb + 128) * pb + 64
    if pb >= 2:
        n = pb // 7 + 2
        kq -= (25 * n - 10) * n - 55
        if pb >= 7:
            kq -= 36
    return kq


def so_byte_du_lieu(pb: int) -> int:
    so_khoi, ec = _KHOI_M[pb]
    return so_o_du_lieu(pb) // 8 - so_khoi * ec


def vi_tri_can_chinh(pb: int) -> list:
    if pb == 1:
        return []
    n = pb // 7 + 2
    buoc = (pb * 8 + n * 3 + 5) // (n * 4 - 4) * 2
    kq = [6]
    vt = pb * 4 + 17 - 7
    while len(kq) < n:
        kq.insert(1, vt)
        vt -= buoc
    return kq


def _dong_bit(du: bytes, pb: int) -> list:
    bit = []

    def them(v, n):
        bit.extend((v >> i) & 1 for i in reversed(range(n)))
    them(0b0100, 4)                                     # chế độ byte
    them(len(du), 8 if pb <= 9 else 16)
    for b in du:
        them(b, 8)
    suc = so_byte_du_lieu(pb) * 8
    them(0, min(4, suc - len(bit)))                     # kết thúc
    them(0, (-len(bit)) % 8)
    kq = [int(''.join(map(str, bit[i:i + 8])), 2) for i in range(0, len(bit), 8)]
    dem = 0xEC
    while len(kq) < suc // 8:
        kq.append(dem)
        dem ^= 0xEC ^ 0x11
    return kq


def _chen_sua_loi(du: list, pb: int) -> list:
    so_khoi, ec = _KHOI_M[pb]
    tong = so_o_du_lieu(pb) // 8
    ngan = so_khoi - tong % so_khoi
    dai_ngan = tong // so_khoi
    uoc = _uoc_rs(ec)
    khoi, k = [], 0
    for i in range(so_khoi):
        n = dai_ngan - ec + (0 if i < ngan else 1)
        d = du[k:k + n]
        k += n
        e = _du_rs(d, uoc)
        if i < ngan:
            d = d + [0]
        khoi.append(d + e)
    kq = []
    for i in range(len(khoi[0])):
        for j, b in enumerate(khoi):
            if i != dai_ngan - ec or j >= ngan:
                kq.append(b[i])
    return kq


class _Luoi:
    def __init__(self, pb: int):
        self.pb, self.co = pb, pb * 4 + 17
        self.o = [[False] * self.co for _ in range(self.co)]
        self.ham = [[False] * self.co for _ in range(self.co)]

    def dat(self, x, y, den):
        self.o[y][x] = den
        self.ham[y][x] = True

    def mau_co_dinh(self):
        n = self.co
        for i in range(n):
            self.dat(6, i, i % 2 == 0)
            self.dat(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < n and 0 <= y < n:
                        self.dat(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        vt = vi_tri_can_chinh(self.pb)
        m = len(vt)
        for i in range(m):
            for j in range(m):
                if (i, j) in ((0, 0), (0, m - 1), (m - 1, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.dat(vt[i] + dx, vt[j] + dy, max(abs(dx), abs(dy)) != 1)
        self.dinh_dang(0)
        self.phien_ban()

    def dinh_dang(self, mat_na: int):
        d = _BIT_MUC_M << 3 | mat_na
        r = d
        for _ in range(10):
            r = (r << 1) ^ ((r >> 9) * 0x537)
        b = (d << 10 | r) ^ 0x5412
        n = self.co
        for i in range(6):
            self.dat(8, i, _bit(b, i))
        self.dat(8, 7, _bit(b, 6))
        self.dat(8, 8, _bit(b, 7))
        self.dat(7, 8, _bit(b, 8))
        for i in range(9, 15):
            self.dat(14 - i, 8, _bit(b, i))
        for i in range(8):
            self.dat(n - 1 - i, 8, _bit(b, i))
        for i in range(8, 15):
            self.dat(8, n - 15 + i, _bit(b, i))
        self.dat(8, n - 8, True)                        # ô đen cố định

    def phien_ban(self):
        if self.pb < 7:
            return
        r = self.pb
        for _ in range(12):
            r = (r << 1) ^ ((r >> 11) * 0x1F25)
        b = self.pb << 12 | r
        for i in range(18):
            a, c = self.co - 11 + i % 3, i // 3
            self.dat(a, c, _bit(b, i))
            self.dat(c, a, _bit(b, i))

    def dat_du_lieu(self, du: list):
        i, n = 0, self.co
        phai = n - 1
        while phai >= 1:
            if phai == 6:
                phai = 5
            for doc in range(n):
                for j in range(2):
                    x = phai - j
                    len_tren = ((phai + 1) & 2) == 0
                    y = n - 1 - doc if len_tren else doc
                    if not self.ham[y][x] and i < len(du) * 8:
                        self.o[y][x] = _bit(du[i >> 3], 7 - (i & 7))
                        i += 1
            phai -= 2

    def ap_mat_na(self, m: int):
        for y in range(self.co):
            for x in range(self.co):
                if not self.ham[y][x] and DIEU_KIEN_MAT_NA[m](x, y):
                    self.o[y][x] = not self.o[y][x]

    def diem_phat(self) -> int:
        n, o, diem = self.co, self.o, 0
        hang = [[o[y][x] for x in range(n)] for y in range(n)]
        cot = [[o[y][x] for y in range(n)] for x in range(n)]
        for dong in hang + cot:
            chay = 1
            for k in range(1, n + 1):
                if k < n and dong[k] == dong[k - 1]:
                    chay += 1
                    continue
                if chay >= 5:
                    diem += 3 + chay - 5
                chay = 1
            s = ''.join('1' if v else '0' for v in dong)
            for mau in ('10111010000', '00001011101'):
                k = s.find(mau)
                while k >= 0:
                    diem += 40
                    k = s.find(mau, k + 1)
        for y in range(n - 1):
            for x in range(n - 1):
                if o[y][x] == o[y][x + 1] == o[y + 1][x] == o[y + 1][x + 1]:
                    diem += 3
        den = sum(sum(h) for h in o)
        diem += 10 * (abs(den * 100 // (n * n) - 50) // 5)
        return diem


DIEU_KIEN_MAT_NA = (lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
                    lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
                    lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
                    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0)


def ma_qr(chu: str, mat_na: int | None = None) -> list:
    """Lưới ô của mã QR cho chữ `chu` (mặt nạ tự chọn nếu None)."""
    du = chu.encode('utf-8')
    pb = next((v for v in range(1, PHIEN_BAN_TOI_DA + 1) if len(du) + 2 + (0 if v <= 9 else 1) <= so_byte_du_lieu(v)), None)
    if pb is None:
        raise LoiQR(f'Chữ quá dài cho mã QR ({len(du)} byte, tối đa {so_byte_du_lieu(PHIEN_BAN_TOI_DA) - 3}).')
    tu = _chen_sua_loi(_dong_bit(du, pb), pb)
    tot, tot_diem = None, None
    for m in (range(8) if mat_na is None else (mat_na,)):
        g = _Luoi(pb)
        g.mau_co_dinh()
        g.dat_du_lieu(tu)
        g.ap_mat_na(m)
        g.dinh_dang(m)
        d = g.diem_phat()
        if tot is None or d < tot_diem:
            tot, tot_diem = g, d
    return tot.o


def svg(chu: str, o_px: int = 8, le: int = 4, mau: str = '#0F172A') -> str:
    """Ảnh SVG của mã QR (nền trắng, lề `le` ô)."""
    g = ma_qr(chu)
    n = len(g) + 2 * le
    duong = ''.join(f'M{x + le},{y + le}h1v1h-1z' for y, h in enumerate(g) for x, v in enumerate(h) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n * o_px}" height="{n * o_px}" '
            f'shape-rendering="crispEdges"><rect width="{n}" height="{n}" fill="#FFFFFF"/><path d="{duong}" fill="{mau}"/></svg>')
