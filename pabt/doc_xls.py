"""Đọc file Excel 97-2003 (.xls, BIFF8) bằng Python thuần - không cần Microsoft Excel, xlrd hay pandas (25/10/2026).

Chỉ đọc GIÁ TRỊ ô (chữ, số, ngày, kết quả công thức đã lưu) và ô gộp của các sheet - đủ cho danh sách hộ / thửa. Không đọc định
dạng, hình, macro. Chạy được trên Python 3.8 (bản Win 7). Không hỗ trợ: file có mật khẩu, Excel 5.0 / 95 (BIFF5) -> LoiXls (nơi gọi
dùng Excel để chuyển sang .xlsx).
"""
from __future__ import annotations

import datetime
import re
import struct
from pathlib import Path

MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
_HET = 0xFFFFFFFA                      # từ giá trị này trở lên là mã đặc biệt (kết chuỗi, trống, FAT, DIFAT)
TOI_DA_MB = 120                        # không đọc file lớn hơn (bản Win 7 32-bit)


class LoiXls(Exception):
    """File .xls không đọc được bằng bộ đọc thuần Python (hỏng, có mật khẩu, quá cũ)."""


# ---------------------------------------------------------------- vùng chứa OLE2 (compound file)
class _Cfb:
    def __init__(self, du: bytes):
        if du[:8] != MAGIC or len(du) < 512:
            raise LoiXls('không phải file Excel 97-2003')
        self.du = du
        self.ss = 1 << struct.unpack_from('<H', du, 0x1E)[0]
        self.mss = 1 << struct.unpack_from('<H', du, 0x20)[0]
        if self.ss not in (512, 4096) or self.mss > self.ss:
            raise LoiXls('cấu trúc file lạ')
        n_fat, dir_dau, self.cat, minifat_dau, n_minifat, difat_dau, n_difat = (
            struct.unpack_from('<I', du, 0x2C)[0], struct.unpack_from('<I', du, 0x30)[0], struct.unpack_from('<I', du, 0x38)[0],
            struct.unpack_from('<I', du, 0x3C)[0], struct.unpack_from('<I', du, 0x40)[0], struct.unpack_from('<I', du, 0x44)[0],
            struct.unpack_from('<I', du, 0x48)[0])
        difat = list(struct.unpack_from('<109I', du, 0x4C))
        n = self.ss // 4
        s = difat_dau
        for _ in range(min(n_difat, 100000)):
            if s >= _HET:
                break
            v = struct.unpack_from(f'<{n}I', du, self._vt(s))
            difat += v[:-1]
            s = v[-1]
        self.fat = []
        for sec in [x for x in difat if x < _HET][:n_fat]:
            self.fat += struct.unpack_from(f'<{n}I', du, self._vt(sec))
        dong = self._doc_chuoi_sector(dir_dau)
        self.muc = []
        for i in range(0, len(dong) - 127, 128):
            ln = struct.unpack_from('<H', dong, i + 64)[0]
            ten = dong[i:i + max(0, min(ln, 64) - 2)].decode('utf-16-le', 'replace')
            loai = dong[i + 66]
            dau = struct.unpack_from('<I', dong, i + 116)[0]
            co = struct.unpack_from('<I', dong, i + 120)[0]
            self.muc.append((ten, loai, dau, co))
        goc = next((m for m in self.muc if m[1] == 5), None)
        self.mini = self._doc_chuoi_sector(goc[2])[:goc[3]] if goc and goc[2] < _HET else b''
        self.minifat = []
        if minifat_dau < _HET and n_minifat:
            raw = self._doc_chuoi_sector(minifat_dau)
            self.minifat = list(struct.unpack_from(f'<{len(raw) // 4}I', raw, 0))

    def _vt(self, sec: int) -> int:
        vt = (sec + 1) * self.ss
        if vt + self.ss > len(self.du):
            raise LoiXls('file bị cắt cụt')
        return vt

    def _day(self, dau: int) -> list:
        ds, s = [], dau
        while s < _HET and len(ds) <= len(self.fat):
            ds.append(s)
            s = self.fat[s] if s < len(self.fat) else 0xFFFFFFFE
        return ds

    def _doc_chuoi_sector(self, dau: int) -> bytes:
        return b''.join(self.du[self._vt(s):self._vt(s) + self.ss] for s in self._day(dau))

    def luong(self, ten_chap: tuple) -> bytes | None:
        m = next((m for m in self.muc if m[1] == 2 and m[0] in ten_chap), None)
        if m is None:
            return None
        _, _, dau, co = m
        if co < self.cat:                                       # luồng nhỏ nằm trong mini stream
            kq, s, dem = [], dau, 0
            while s < _HET and dem <= len(self.minifat):
                kq.append(self.mini[s * self.mss:(s + 1) * self.mss])
                s = self.minifat[s] if s < len(self.minifat) else 0xFFFFFFFE
                dem += 1
            return b''.join(kq)[:co]
        return self._doc_chuoi_sector(dau)[:co]


# ---------------------------------------------------------------- chữ Unicode của BIFF8
class _DocChuoi:
    """Đọc chuỗi Unicode của bảng SST: chuỗi có thể kéo dài qua các bản ghi CONTINUE (đầu mỗi đoạn tiếp có 1 byte cờ mã hóa)."""

    def __init__(self, doan: list):
        self.doan = doan
        self.i = 0
        self.p = 0

    def het(self) -> bool:
        while self.i < len(self.doan) and self.p >= len(self.doan[self.i]):
            self.i += 1
            self.p = 0
        return self.i >= len(self.doan)

    def byte(self) -> int:
        if self.het():
            raise LoiXls('bảng chuỗi bị cắt cụt')
        v = self.doan[self.i][self.p]
        self.p += 1
        return v

    def bo_qua(self, n: int) -> None:
        while n > 0 and not self.het():
            lay = min(n, len(self.doan[self.i]) - self.p)
            self.p += lay
            n -= lay

    def chuoi(self) -> str:
        cch = self.byte() | (self.byte() << 8)
        co = self.byte()
        rong = co & 1
        so_run = (self.byte() | (self.byte() << 8)) if co & 8 else 0
        ext = 0
        if co & 4:
            ext = self.byte() | (self.byte() << 8) | (self.byte() << 16) | (self.byte() << 24)
        kq = []
        con = cch
        while con > 0:
            if self.i >= len(self.doan):
                raise LoiXls('bảng chuỗi bị cắt cụt')
            don_vi = 2 if rong else 1
            co_san = (len(self.doan[self.i]) - self.p) // don_vi
            if co_san <= 0:                                     # sang đoạn CONTINUE: byte đầu là cờ mã hóa của phần còn lại
                self.i += 1
                self.p = 0
                if self.i >= len(self.doan) or not self.doan[self.i]:
                    raise LoiXls('bảng chuỗi bị cắt cụt')
                rong = self.byte() & 1
                continue
            lay = min(con, co_san)
            b = self.doan[self.i][self.p:self.p + lay * don_vi]
            kq.append(b.decode('utf-16-le', 'replace') if rong else b.decode('latin-1'))
            self.p += lay * don_vi
            con -= lay
        self.bo_qua(4 * so_run + ext)
        return ''.join(kq)


def _chuoi_ban_ghi(du: bytes, vt: int, cch_byte: int = 2) -> tuple:
    """Chuỗi Unicode trong MỘT bản ghi (LABEL, FORMAT, STRING, tên sheet): (chữ, vị trí sau chuỗi)."""
    cch = du[vt] if cch_byte == 1 else struct.unpack_from('<H', du, vt)[0]
    vt += cch_byte
    co = du[vt]
    vt += 1
    so_run = ext = 0
    if co & 8:
        so_run = struct.unpack_from('<H', du, vt)[0]
        vt += 2
    if co & 4:
        ext = struct.unpack_from('<I', du, vt)[0]
        vt += 4
    if co & 1:
        chu = du[vt:vt + 2 * cch].decode('utf-16-le', 'replace')
        vt += 2 * cch
    else:
        chu = du[vt:vt + cch].decode('latin-1')
        vt += cch
    return chu, vt + 4 * so_run + ext


# ---------------------------------------------------------------- số, ngày
_DINH_DANG_NGAY = frozenset(list(range(14, 23)) + [45, 46, 47])


def _rk(v: int) -> float:
    if v & 2:
        x = struct.unpack('<i', struct.pack('<I', v))[0] >> 2
    else:
        x = struct.unpack('<d', struct.pack('<Q', (v & 0xFFFFFFFC) << 32))[0]
    return x / 100 if v & 1 else x


_RE_BO_QUA = re.compile(r'"[^"]*"|\[[^\]]*\]|\\.|_.|\*.')


def _la_dinh_dang_ngay(ma: str) -> bool:
    ma = _RE_BO_QUA.sub('', ma.split(';')[0])
    return bool(re.search(r'[ymdhs]', ma, re.I)) and 'general' not in ma.lower()


def _so(x: float):
    return int(x) if x == int(x) and abs(x) < 1e15 else x


def _ngay(x: float, he_1904: bool):
    goc = datetime.datetime(1904, 1, 1) if he_1904 else datetime.datetime(1899, 12, 30)
    try:
        return goc + datetime.timedelta(days=x)
    except (OverflowError, ValueError):
        return _so(x)


# ---------------------------------------------------------------- bản ghi BIFF8
def doc(file) -> list:
    """Các sheet đang hiện của file .xls: [{'ten', 'dong': [[giá trị...]], 'gop': [(dòng1, cột1, dòng2, cột2)] (1-based)}]."""
    p = Path(file)
    if p.stat().st_size > TOI_DA_MB * 2 ** 20:
        raise LoiXls('file quá lớn')
    cfb = _Cfb(p.read_bytes())
    wb = cfb.luong(('Workbook', 'Book'))
    if not wb:
        raise LoiXls('không thấy dữ liệu bảng tính')
    try:
        return _doc_workbook(wb)
    except (struct.error, IndexError, ValueError) as e:
        raise LoiXls(f'cấu trúc file lạ ({e})') from None


def _doc_workbook(wb: bytes) -> list:
    sst_doan, sst_dang, sst_tong = None, False, 0
    dinh_dang, xf_dd = {}, []
    ds_sheet = []                                   # (tên, vị trí, ẩn, loại)
    he_1904 = False
    n_bof = 0
    vt = 0
    while vt + 4 <= len(wb):                        # phần toàn cục của workbook, tới bản ghi EOF đầu tiên
        rid, ln = struct.unpack_from('<HH', wb, vt)
        d = wb[vt + 4:vt + 4 + ln]
        vt += 4 + ln
        if rid == 0x0809:
            n_bof += 1
            if n_bof == 1 and struct.unpack_from('<H', d, 0)[0] != 0x0600:
                raise LoiXls('Excel 5.0 / 95 (BIFF5)')
        elif rid == 0x002F:
            raise LoiXls('file có mật khẩu')
        elif rid == 0x0022:
            he_1904 = bool(struct.unpack_from('<H', d, 0)[0])
        elif rid == 0x041E:
            dinh_dang[struct.unpack_from('<H', d, 0)[0]] = _chuoi_ban_ghi(d, 2)[0]
        elif rid == 0x00E0:
            xf_dd.append(struct.unpack_from('<H', d, 2)[0])
        elif rid == 0x0085:
            vi_tri, an = struct.unpack_from('<IB', d, 0)
            ds_sheet.append((_chuoi_ban_ghi(d, 6, 1)[0], vi_tri, an, d[5]))
        elif rid == 0x00FC:
            sst_tong = struct.unpack_from('<I', d, 4)[0]
            sst_doan, sst_dang = [d[8:]], True
            continue
        elif rid == 0x003C and sst_dang:
            sst_doan.append(d)
            continue
        elif rid == 0x000A:
            break
        sst_dang = False
    sst = []
    if sst_doan:
        doc_c = _DocChuoi(sst_doan)
        for _ in range(sst_tong):
            try:
                sst.append(doc_c.chuoi())
            except LoiXls:
                break
    ngay = {i for i, f in enumerate(xf_dd)
            if f in _DINH_DANG_NGAY or (f in dinh_dang and _la_dinh_dang_ngay(dinh_dang[f]))}
    kq = []
    for ten, vi_tri, an, loai in ds_sheet:
        if loai != 0:                               # 0 = bảng tính; biểu đồ / macro bỏ qua
            continue
        o, gop = _doc_sheet(wb, vi_tri, sst, ngay, he_1904)
        if o is None:
            continue
        kq.append(dict(ten=ten, an=an != 0, dong=o, gop=gop))
    return kq


def _doc_sheet(wb: bytes, vt: int, sst: list, ngay: set, he_1904: bool):
    o = {}
    gop = []
    sau_cong_thuc = None
    if vt + 4 > len(wb) or struct.unpack_from('<H', wb, vt)[0] != 0x0809:
        return None, []
    cao = rong = 0

    def dat(r, c, v):
        nonlocal cao, rong
        o[(r, c)] = v
        cao = max(cao, r + 1)
        rong = max(rong, c + 1)

    def so_o(r, c, xf, x):
        dat(r, c, _ngay(x, he_1904) if xf in ngay else _so(x))
    sau = 0                                         # độ sâu BOF / EOF (biểu đồ nhúng trong sheet có BOF riêng)
    while vt + 4 <= len(wb):
        rid, ln = struct.unpack_from('<HH', wb, vt)
        d = wb[vt + 4:vt + 4 + ln]
        vt += 4 + ln
        if rid == 0x0809:
            sau += 1
        elif rid == 0x000A:
            sau -= 1
            if sau <= 0:
                break
        if sau != 1 and rid != 0x000A:
            continue
        if rid == 0x00FD:                               # LABELSST
            r, c, xf, i = struct.unpack_from('<HHHI', d, 0)
            if i < len(sst) and sst[i] != '':
                dat(r, c, sst[i])
        elif rid == 0x0203:                             # NUMBER
            r, c, xf = struct.unpack_from('<HHH', d, 0)
            so_o(r, c, xf, struct.unpack_from('<d', d, 6)[0])
        elif rid == 0x027E:                             # RK
            r, c, xf, v = struct.unpack_from('<HHHI', d, 0)
            so_o(r, c, xf, _rk(v))
        elif rid == 0x00BD:                             # MULRK
            r, c0 = struct.unpack_from('<HH', d, 0)
            n = (len(d) - 6) // 6
            for k in range(n):
                xf, v = struct.unpack_from('<HI', d, 4 + 6 * k)
                so_o(r, c0 + k, xf, _rk(v))
        elif rid == 0x0204:                             # LABEL (BIFF8 cũ)
            r, c, xf = struct.unpack_from('<HHH', d, 0)
            chu = _chuoi_ban_ghi(d, 6)[0]
            if chu != '':
                dat(r, c, chu)
        elif rid == 0x0006:                             # FORMULA: kết quả đã lưu
            r, c, xf = struct.unpack_from('<HHH', d, 0)
            kq8 = d[6:14]
            if kq8[6:8] == b'\xff\xff':
                loai = kq8[0]
                if loai == 0:
                    sau_cong_thuc = (r, c)
                elif loai == 1:
                    dat(r, c, bool(kq8[2]))
            else:
                so_o(r, c, xf, struct.unpack('<d', kq8)[0])
        elif rid == 0x0207 and sau_cong_thuc:           # STRING: chữ kết quả công thức ngay trước đó
            chu = _chuoi_ban_ghi(d, 0)[0]
            if chu != '':
                dat(*sau_cong_thuc, chu)
            sau_cong_thuc = None
        elif rid == 0x0205:                             # BOOLERR
            r, c, xf, v, loi = struct.unpack_from('<HHHBB', d, 0)
            if not loi:
                dat(r, c, bool(v))
        elif rid == 0x00E5:                             # MERGEDCELLS
            n = struct.unpack_from('<H', d, 0)[0]
            for k in range(n):
                r1, r2, c1, c2 = struct.unpack_from('<HHHH', d, 2 + 8 * k)
                gop.append((r1 + 1, c1 + 1, r2 + 1, c2 + 1))
    luoi = [[None] * rong for _ in range(cao)]
    for (r, c), v in o.items():
        luoi[r][c] = v
    return luoi, gop
