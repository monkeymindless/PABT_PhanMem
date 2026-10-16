"""Đọc bản vẽ DXF dạng chữ (ASCII) bằng Python thuần - không cần numpy / ezdxf (máy yếu, 16/10/2026: bản cài bỏ numpy + thư
viện ezdxf ~30 MB). Chỉ lấy đúng phần nhập bản đồ thửa (ban_do_cad) cần, trong không gian mô hình (model space):
- LWPOLYLINE, POLYLINE 2D (+ VERTEX … SEQEND): các đỉnh (x, y), có khép kín không (cờ 70 bit 1);
- TEXT, MTEXT (chữ trơn, bỏ mã định dạng), ATTRIB của INSERT; INSERT không thuộc tính: chữ TEXT / MTEXT trong khối, đặt theo điểm
  chèn, tỷ lệ, góc xoay của khối.
Mã hóa chữ: DXF 2007 trở lên (AC1021+) UTF-8; cũ hơn theo $DWGCODEPAGE (ANSI_1258 -> cp1258…); \\U+XXXX được giải mã.
DXF dạng nhị phân (binary): báo lỗi để lưu lại dạng ASCII."""
from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path


class LoiDxf(Exception):
    """Lỗi đọc file DXF (thông báo tiếng Việt)."""


class ThucThe:
    """Một thực thể đã đọc: loai ('LWPOLYLINE' / 'POLYLINE' / 'TEXT' / 'MTEXT' / 'INSERT'), lop (tên lớp), diem [(x, y)] + kin
    (đường đa tuyến), chu [(chữ, x, y)] (chữ / thuộc tính / chữ trong khối)."""
    __slots__ = ('loai', 'lop', 'diem', 'kin', 'chu')

    def __init__(self, loai: str, lop: str, diem=None, kin: bool = False, chu=None):
        self.loai, self.lop = loai, lop
        self.diem = diem or []
        self.kin = kin
        self.chu = chu or []


_NHI_PHAN = b'AutoCAD Binary DXF'
_RE_U = re.compile(r'\\U\+([0-9A-Fa-f]{4})')


def _ma_hoa(du_lieu: bytes) -> str:
    """Bảng mã của file theo $ACADVER / $DWGCODEPAGE trong HEADER."""
    dau = du_lieu[:200000].decode('latin-1', 'replace')
    m = re.search(r'\$ACADVER\s*\r?\n\s*1\s*\r?\n\s*AC(\d{4})', dau)
    if m and int(m.group(1)) >= 1021:
        return 'utf-8'
    m = re.search(r'\$DWGCODEPAGE\s*\r?\n\s*3\s*\r?\n\s*ANSI_(\d+)', dau)
    if m:
        ma = f'cp{m.group(1)}'
        try:
            ''.encode(ma)
            return ma
        except LookupError:
            pass
    return 'cp1252'


def _cap(file) -> list:
    """[(mã nhóm, giá trị)] của cả file."""
    p = Path(file)
    try:
        du_lieu = p.read_bytes()
    except OSError as e:
        raise LoiDxf(f'Không mở được {p.name}: {e}') from None
    if du_lieu.startswith(_NHI_PHAN):
        raise LoiDxf(f'{p.name} là DXF dạng nhị phân: mở bằng AutoCAD / MicroStation, Lưu thành (Save As) DXF dạng chữ (ASCII) rồi nhập.')
    ma = _ma_hoa(du_lieu)
    if du_lieu.startswith(b'\xef\xbb\xbf'):
        du_lieu = du_lieu[3:]
    # bản vẽ cũ cp1258 ghi dấu thanh tiếng Việt tách rời (a + dấu sắc): dựng sẵn (NFC) để so khớp / hiện như chữ thường
    dong = unicodedata.normalize('NFC', du_lieu.decode(ma, 'replace')).splitlines()
    if len(dong) < 2:
        raise LoiDxf(f'{p.name} không phải bản vẽ DXF.')
    kq = []
    for i in range(0, len(dong) - 1, 2):
        try:
            kq.append((int(dong[i].strip()), dong[i + 1].strip('\r\n')))
        except ValueError:
            raise LoiDxf(f'{p.name} hỏng cấu trúc DXF (dòng {i + 1}: "{dong[i].strip()[:20]}" không phải mã nhóm).') from None
    if not any(c == 0 and v.strip() == 'SECTION' for c, v in kq[:50]):
        raise LoiDxf(f'{p.name} không phải bản vẽ DXF.')
    return kq


def _nhom_thuc_the(cap: list) -> dict:
    """{tên mục (ENTITIES, BLOCKS…): [[(mã, giá trị)] từng thực thể]}."""
    muc, dang, the = {}, None, None
    for c, v in cap:
        if c == 0:
            v = v.strip()
            if v == 'SECTION':
                dang, the = '?', None
                continue
            if v == 'ENDSEC':
                dang, the = None, None
                continue
            if v == 'EOF':
                break
            if dang:
                the = [(0, v)]
                muc.setdefault(dang, []).append(the)
            continue
        if dang == '?' and c == 2:
            dang = v.strip()
            muc.setdefault(dang, [])
            continue
        if the is not None:
            the.append((c, v))
    return muc


def _so(v, mac_dinh: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return mac_dinh


def _lay(the: list, ma: int, mac_dinh=None):
    return next((v for c, v in the if c == ma), mac_dinh)


def _chu_dxf(s: str) -> str:
    """Chữ TEXT / ATTRIB: \\U+XXXX và mã %%d, %%p, %%c, %%%; bỏ %%u / %%o (gạch chân / gạch trên)."""
    s = _RE_U.sub(lambda m: chr(int(m.group(1), 16)), s)
    for a, b in (('%%d', '°'), ('%%D', '°'), ('%%p', '±'), ('%%P', '±'), ('%%c', 'Ø'), ('%%C', 'Ø'), ('%%u', ''), ('%%U', ''),
                 ('%%o', ''), ('%%O', ''), ('%%%', '%')):
        s = s.replace(a, b)
    return s


_RE_MTEXT_LENH = re.compile(r'\\[ACFHQTWfcfhqtw][^;\\{}]*;')
_RE_MTEXT_BAT = re.compile(r'\\[LlOoKk]')
_RE_MTEXT_XEP = re.compile(r'\\S([^;]*);')


def chu_mtext(s: str) -> str:
    """Chữ trơn của MTEXT (như ezdxf plain_text): \\P xuống dòng, bỏ mã phông / màu / cỡ, phân số xếp chồng -> a/b."""
    s = _RE_U.sub(lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace('\\\\', '\x00').replace('\\{', '\x01').replace('\\}', '\x02')
    s = s.replace('\\P', '\n').replace('\\p', '').replace('\\~', ' ').replace('\\N', '\n')
    s = _RE_MTEXT_XEP.sub(lambda m: re.sub(r'[\^#]', '/', m.group(1)), s)
    s = _RE_MTEXT_LENH.sub('', s)
    s = _RE_MTEXT_BAT.sub('', s)
    s = s.replace('{', '').replace('}', '')
    s = re.sub(r'\\pi?[-\d.,;a-z]*;', '', s)
    return s.replace('\x00', '\\').replace('\x01', '{').replace('\x02', '}')


def _chu_text(the: list):
    """(chữ, x, y) của TEXT / ATTRIB: điểm canh (11, 21) khi có canh lề, không thì điểm chèn (10, 20)."""
    can = int(_so(_lay(the, 72, 0))) or int(_so(_lay(the, 73, 0))) or int(_so(_lay(the, 74, 0)))
    if can and _lay(the, 11) is not None:
        x, y = _so(_lay(the, 11)), _so(_lay(the, 21))
    else:
        x, y = _so(_lay(the, 10)), _so(_lay(the, 20))
    return _chu_dxf(_lay(the, 1, '')), x, y


def _chu_mtext_the(the: list):
    phan = [v for c, v in the if c == 3] + [v for c, v in the if c == 1]
    return chu_mtext(''.join(phan)), _so(_lay(the, 10)), _so(_lay(the, 20))


def _diem_lw(the: list) -> list:
    xs = [_so(v) for c, v in the if c == 10]
    ys = [_so(v) for c, v in the if c == 20]
    return list(zip(xs, ys))


def _khoi(blocks: list) -> dict:
    """{tên khối: (điểm gốc, [(chữ, x, y)])} - chữ TEXT / MTEXT trong định nghĩa khối."""
    kq, ten = {}, None
    for the in blocks:
        loai = the[0][1]
        if loai == 'BLOCK':
            ten = _lay(the, 2, '')
            kq[ten] = ((_so(_lay(the, 10)), _so(_lay(the, 20))), [])
        elif loai == 'ENDBLK':
            ten = None
        elif ten is not None and loai == 'TEXT':
            kq[ten][1].append(_chu_text(the))
        elif ten is not None and loai == 'MTEXT':
            kq[ten][1].append(_chu_mtext_the(the))
    return kq


def doc(file) -> list:
    """[ThucThe] trong không gian mô hình (bỏ thực thể ở paper space - mã 67 = 1)."""
    muc = _nhom_thuc_the(_cap(file))
    khoi = _khoi(muc.get('BLOCKS', []))
    ds = muc.get('ENTITIES', [])
    kq = []
    i = 0
    while i < len(ds):
        the = ds[i]
        loai = the[0][1]
        i += 1
        if _lay(the, 67) is not None and _lay(the, 67).strip() == '1':
            while loai in ('POLYLINE', 'INSERT') and i < len(ds) and ds[i][0][1] in ('VERTEX', 'ATTRIB'):
                i += 1
            if i < len(ds) and ds[i][0][1] == 'SEQEND' and loai in ('POLYLINE', 'INSERT'):
                i += 1
            continue
        lop = _lay(the, 8, '0').strip() or '0'
        if loai == 'LWPOLYLINE':
            kq.append(ThucThe(loai, lop, _diem_lw(the), bool(int(_so(_lay(the, 70, 0))) & 1)))
        elif loai == 'POLYLINE':
            co = int(_so(_lay(the, 70, 0)))
            dinh = []
            while i < len(ds) and ds[i][0][1] == 'VERTEX':
                v = ds[i]
                if not int(_so(_lay(v, 70, 0))) & 128:                  # bản ghi mặt của lưới đa diện: không phải đỉnh
                    dinh.append((_so(_lay(v, 10)), _so(_lay(v, 20))))
                i += 1
            if i < len(ds) and ds[i][0][1] == 'SEQEND':
                i += 1
            if not co & (8 | 16 | 64):                                   # 3D, lưới đa giác, lưới đa diện: không phải ranh 2D
                kq.append(ThucThe(loai, lop, dinh, bool(co & 1)))
        elif loai == 'TEXT':
            kq.append(ThucThe(loai, lop, chu=[_chu_text(the)]))
        elif loai == 'MTEXT':
            kq.append(ThucThe(loai, lop, chu=[_chu_mtext_the(the)]))
        elif loai == 'INSERT':
            chu = []
            while i < len(ds) and ds[i][0][1] == 'ATTRIB':
                a = ds[i]
                chu.append((_chu_dxf(_lay(a, 1, '')), _so(_lay(a, 10)), _so(_lay(a, 20))))
                i += 1
            if i < len(ds) and ds[i][0][1] == 'SEQEND':
                i += 1
            if not chu:                                                  # khối nhãn không thuộc tính: chữ bên trong khối
                goc, chu_khoi = khoi.get(_lay(the, 2, ''), ((0.0, 0.0), []))
                x0, y0 = _so(_lay(the, 10)), _so(_lay(the, 20))
                sx, sy = _so(_lay(the, 41), 1.0), _so(_lay(the, 42), 1.0)
                g = math.radians(_so(_lay(the, 50)))
                cg, sg = math.cos(g), math.sin(g)
                for c, x, y in chu_khoi:
                    dx, dy = (x - goc[0]) * sx, (y - goc[1]) * sy
                    chu.append((c, x0 + dx * cg - dy * sg, y0 + dx * sg + dy * cg))
            kq.append(ThucThe(loai, lop, chu=chu))
    return kq



def viet(file, hinh: list = (), chu: list = (), ma_hoa: str = 'utf-8') -> Path:
    """Ghi bản vẽ DXF R12 dạng chữ tối thiểu (tự kiểm tra bản cài, kiểm thử): hinh [(lớp, [(x, y)…])] = POLYLINE khép kín,
    chu [(lớp, chữ, x, y)] = TEXT. ma_hoa khác utf-8 (vd cp1258): ghi $DWGCODEPAGE tương ứng (bản vẽ cũ)."""
    dong = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1009']
    if ma_hoa.lower().startswith('cp'):
        dong += ['9', '$DWGCODEPAGE', '3', f'ANSI_{ma_hoa[2:]}']
    dong += ['0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    for lop, diem in hinh:
        dong += ['0', 'POLYLINE', '8', lop, '66', '1', '70', '1']
        for x, y in diem:
            dong += ['0', 'VERTEX', '8', lop, '10', f'{x}', '20', f'{y}']
        dong += ['0', 'SEQEND', '8', lop]
    for lop, c, x, y in chu:
        dong += ['0', 'TEXT', '8', lop, '10', f'{x}', '20', f'{y}', '40', '2.5', '1', c]
    dong += ['0', 'ENDSEC', '0', 'EOF']
    p = Path(file)
    p.write_bytes(('\r\n'.join(dong) + '\r\n').encode(ma_hoa if ma_hoa.lower() != 'utf-8' else 'utf-8'))
    return p
