"""Bản in (giai đoạn 3): phương án chi tiết từng hộ (mẫu IN_CHITIET, A4 dọc) và bảng tổng hợp (mẫu IN_BANGTONGHOP, A3 ngang).

Mẫu in là chính hai sheet IN_CHITIET / IN_BANGTONGHOP của file PABT Excel, tách thành hai file .xlsx trong thư mục mau_in
(lệnh tao_mau_tu_excel). Ô có {ten} trong mẫu được thay bằng dữ liệu (tên dự án, xã/phường, họ tên...), nên sửa chữ,
người ký, cơ quan... chỉ cần mở file mẫu bằng Excel sửa rồi lưu, không cần sửa phần mềm.

Bảng tính được điền bằng openpyxl (số liệu từ nghiep_vu, cùng hàm tính với màn hình); PDF và in ra máy in nhờ
Microsoft Excel trên máy (VBScript gọi Excel, không cần cài thêm thư viện).
"""
from __future__ import annotations
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unicodedata
import time
from copy import copy
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.styles import Alignment
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange

from . import nghiep_vu
from .nghiep_vu import MA_ON_DINH, BoiCanh, doc_phuong_an, tinh_pa
from .tien import D, KHONG, dinh_dang_so_luong

TEN_CT, TEN_BTH = 'IN_CHITIET', 'IN_BANGTONGHOP'
COT_KIND = 30          # cột AD (ngoài vùng in): loại dòng H / I / R / T cho định dạng có điều kiện của mẫu (mặc định hồ sơ)
DONG_DAU_CT = 18       # IN_CHITIET: dòng đầu bảng (dưới hàng tiêu đề STT)
DONG_DAU_BTH = 13      # IN_BANGTONGHOP: dòng dữ liệu đầu (mặc định hồ sơ: mau_in.IN_BANGTONGHOP.dong_du_lieu_dau)
# 0.9.85: vị trí cột của hai mẫu đọc từ hồ sơ địa phương (pabt_profile.json mục mau_in - dia_phuong.cot_mau), mặc định đúng mẫu
# Đồng Nai; mẫu địa phương khác sắp cột khác thì sửa hồ sơ, không sửa mã. Thứ tự giá trị một dòng bảng chi tiết (dong_chi_tiet):
TRUONG_CT = ('stt', 'ten', 'dvt', 'so_luong', 'don_gia', 'ty_le', 'thanh_tien', 'ghi_chu')


def _cot_ct() -> tuple:
    """(số cột của từng trường TRUONG_CT, cột loại dòng, chữ ô đầu hàng tiêu đề bảng) theo hồ sơ địa phương."""
    from . import dia_phuong
    cot = dia_phuong.cot_mau(TEN_CT)
    return ([cot[k] for k in TRUONG_CT], dia_phuong.so_cot(dia_phuong.lay('mau_in.IN_CHITIET.cot_loai_dong')),
            str(dia_phuong.lay('mau_in.IN_CHITIET.chu_dau_bang')).strip().upper())
TEN_CAO = 'PABT_TU_GIAN_DONG'   # tên vùng các dòng cần Excel tự giãn chiều cao khi xuất PDF


class LoiIn(RuntimeError):
    pass


# ---------------------------------------------------------------- thư mục mẫu in
def thu_muc_mau(ten: str = TEN_CT) -> Path:
    """Thư mục có mẫu ten: mau_in cạnh PABT.exe (người dùng sửa được) > mau_in đóng gói kèm > mau_in của mã nguồn.
    Tìm theo từng mẫu: thư mục ghi có thể chỉ có một trong hai mẫu (Cập nhật mẫu in từ file một sheet)."""
    ung_vien = []
    if getattr(sys, 'frozen', False):
        ung_vien.append(thu_muc_mau_ghi())
        ung_vien.append(Path(sys.executable).parent / 'mau_in')
        ung_vien.append(Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / 'mau_in')
    ung_vien.append(Path(__file__).resolve().parents[1] / 'mau_in')
    for p in ung_vien:
        if (p / f'{ten}.xlsx').exists():
            return p
    raise LoiIn(f'Không tìm thấy thư mục mẫu in (mau_in\\{ten}.xlsx). Dùng lệnh "Công cụ → Mẫu in" trên thanh menu.')


def thu_muc_mau_ghi() -> Path:
    """Nơi ghi mẫu in khi cập nhật từ file Excel: %APPDATA%\\PABT\\mau_in (bản cài: thư mục cài không ghi được)
    hoặc mau_in của mã nguồn."""
    if getattr(sys, 'frozen', False):
        return Path(os.environ.get('APPDATA') or Path.home()) / 'PABT' / 'mau_in'
    return Path(__file__).resolve().parents[1] / 'mau_in'


# ---------------------------------------------------------------- đường kẻ (hình vẽ) của mẫu
# openpyxl làm mất hình vẽ khi đọc / ghi: đường kẻ dưới tên cơ quan, dưới quốc hiệu, dưới tên dự án được lưu riêng
# (mau_in/<mẫu>.duong_ke.xml, lấy từ file PABT Excel) và chèn lại vào file bản in sau khi lưu.
_DS_DR = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
_DS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_DS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_NET = '<a:ln w="9525"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln>'


def doc_duong_ke(file_excel, ten_sheet: str) -> str:
    """Các đường kẻ thẳng (twoCellAnchor có prstGeom line) trên một sheet của file Excel -> chuỗi XML."""
    import zipfile
    with zipfile.ZipFile(file_excel) as z:
        wbx = z.read('xl/workbook.xml').decode('utf-8')
        m = re.search(r'<sheet [^>]*name="%s"[^>]*r:id="([^"]+)"' % re.escape(ten_sheet), wbx)
        if not m:
            return ''
        rels = z.read('xl/_rels/workbook.xml.rels').decode('utf-8')
        t = re.search(r'<Relationship [^>]*Id="%s"[^>]*>' % m.group(1), rels)
        sheet = 'xl/' + re.search(r'Target="([^"]+)"', t.group(0)).group(1).replace('/xl/', '').lstrip('/')
        srel = sheet.replace('worksheets/', 'worksheets/_rels/') + '.rels'
        if srel not in z.namelist():
            return ''
        kq = []
        for d in re.findall(r'Target="([^"]*drawings/[^"]+)"', z.read(srel).decode('utf-8')):
            x = z.read('xl/drawings/' + d.split('/')[-1]).decode('utf-8')
            kq += [a for a in re.findall(r'<xdr:twoCellAnchor.*?</xdr:twoCellAnchor>', x, re.S) if 'prst="line"' in a]
    # nét đen mảnh rõ ràng, không phụ thuộc theme của file đích
    return ''.join(re.sub(r'(<a:prstGeom prst="line">.*?</a:prstGeom>)(?!<a:ln)', r'\1' + _NET, a, flags=re.S) for a in kq)


def chen_duong_ke(file_xlsx, file_duong_ke, xml: str | None = None) -> bool:
    """Chèn các đường kẻ (XML) vào sheet đầu của file .xlsx do openpyxl lưu. Trả True nếu đã chèn. xml: nội dung đã canh lại
    (can_duong_ke) thay cho nội dung file."""
    import zipfile
    p, dk = Path(file_xlsx), Path(file_duong_ke)
    if xml is None:
        xml = dk.read_text(encoding='utf-8') if dk.exists() else ''
    if not xml.strip():
        return False
    with zipfile.ZipFile(p) as zi:
        ten = zi.namelist()
        tep = {n: zi.read(n) for n in ten}
    sheet = 'xl/worksheets/sheet1.xml'
    sx = tep[sheet].decode('utf-8')
    if '<drawing ' in sx:
        return False
    n = 1
    while f'xl/drawings/drawing{n}.xml' in tep:
        n += 1
    rid = 'rIdDuongKe1'
    srel = 'xl/worksheets/_rels/sheet1.xml.rels'
    rels = tep[srel].decode('utf-8') if srel in tep else \
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    rels = rels.replace('</Relationships>', f'<Relationship Id="{rid}" Type="{_DS_R}/drawing" Target="../drawings/drawing{n}.xml"/></Relationships>')
    if 'xmlns:r=' not in sx[:1000]:
        sx = sx.replace('<worksheet ', f'<worksheet xmlns:r="{_DS_R}" ', 1)
    vi = min((i for i in (sx.find(t) for t in ('<legacyDrawing', '<picture', '<oleObjects', '<controls', '<tableParts', '<extLst',
                                                '</worksheet>')) if i >= 0))
    sx = sx[:vi] + f'<drawing r:id="{rid}"/>' + sx[vi:]
    ct = tep['[Content_Types].xml'].decode('utf-8').replace(
        '</Types>', f'<Override PartName="/xl/drawings/drawing{n}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>')
    tep[sheet], tep[srel], tep['[Content_Types].xml'] = sx.encode('utf-8'), rels.encode('utf-8'), ct.encode('utf-8')
    tep[f'xl/drawings/drawing{n}.xml'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<xdr:wsDr xmlns:xdr="{_DS_DR}" '
                                          f'xmlns:a="{_DS_A}">' + xml + '</xdr:wsDr>').encode('utf-8')
    tam = p.with_name(p.name + '.tmp')
    try:
        with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as zo:
            for k in ['[Content_Types].xml'] + [x for x in tep if x != '[Content_Types].xml']:
                zo.writestr(k, tep[k])
        os.replace(tam, p)
    except BaseException:
        if tam.exists():                                # ghi lỗi (đầy đĩa, file đang mở): không để lại file .tmp cạnh file in
            tam.unlink()
        raise
    return True


# ---- canh đường kẻ theo chữ phía trên (người dùng yêu cầu 10/10/2026: "đường ngang dưới chữ gần sát, nằm giữa từng nội dung")
EMU_PX, EMU_PT = 9525, 12700
# khoảng từ chân dòng chữ (tính theo phông) tới đường kẻ, theo cỡ chữ - đo trên bản PDF Excel in ra: dòng có dấu nặng / chữ có
# chân (ạ, ộ, ị, g, p, y…) cần xa hơn để đường kẻ không che dấu (người dùng: "hở chữ 1 chút xíu để không che dấu chữ")
DK_CO_DAU_DUOI = 0.20
DK_KHONG_DAU_DUOI = 0.08
DK_DU_AN_CM = 7.0             # đường kẻ dưới dòng "Dự án: …": dài 7 cm, căn giữa dòng chữ (người dùng 12/10/2026)
EMU_CM = 360000
DK_CACH = 5.0                  # tối thiểu (pt) từ chân dòng chữ tới đường kẻ: không chạm chân chữ / dấu nặng (người dùng 14/10/2026)
_DAU_DUOI = set('gjpqyạặậẹệịọộợụựỵẠẶẬẸỆỊỌỘỢỤỰỴ,;')
DK_LE_TREN = 1.0               # Excel chừa phía trên chữ (pt) khi canh trên
_RE_NEO = re.compile(r'<xdr:(from|to)><xdr:col>(\d+)</xdr:col><xdr:colOff>(-?\d+)</xdr:colOff>'
                     r'<xdr:row>(\d+)</xdr:row><xdr:rowOff>(-?\d+)</xdr:rowOff></xdr:\1>')
_TIEU_NGU = 'doc lap - tu do - hanh phuc'


def _bien_cot(ws) -> list:
    """Mép trái (EMU) của cột 1..61 (phần tử 0 = cột A) theo độ rộng cột như Excel (_px_cot: cột ẩn, dải cột)."""
    x, kq = 0, []
    for px in _px_cot(ws, 61):
        kq.append(x)
        x += px * EMU_PX
    kq.append(x)
    return kq


def _bien_dong(ws, den: int = 60) -> list:
    """Mép trên (EMU) của dòng 1..den (phần tử 0 = dòng 1)."""
    mac_dinh = float(ws.sheet_format.defaultRowHeight or 15)
    y, kq = 0, []
    for r in range(1, den + 2):
        kq.append(y)
        y += int(round(float(ws.row_dimensions[r].height or mac_dinh) * EMU_PT))
    return kq


def _neo(gia: int, bien: list) -> tuple:
    """Vị trí tuyệt đối (EMU) -> (chỉ số cột / dòng từ 0, độ lệch). Chỉ neo vào cột / dòng có bề rộng (cột ẩn rộng 0: Excel
    không đặt được điểm neo bên trong)."""
    for k in range(len(bien) - 1):
        if bien[k] <= gia < bien[k + 1]:
            return k, gia - bien[k]
    k = len(bien) - 2 if gia >= bien[-1] else 0
    return k, max(0, gia - bien[k])


def _dong_chu_o(ws, r: int, c: int, bc: list, bd: list, do, chi_muc: dict | None = None) -> dict | None:
    """Bố trí chữ trong ô (r, c) (tính cả vùng gộp): x trái / phải (EMU), canh ngang, các dòng chữ và y chân từng dòng."""
    o = ws.cell(r, c)
    if not isinstance(o.value, str) or not o.value.strip():
        return None
    m = _vung_tron(ws, r, c, chi_muc)
    r1, c1, r2, c2 = (m.min_row, m.min_col, m.max_row, m.max_col) if m else (r, c, r, c)
    ten, co, dam = _phong(o)
    dong = ngat_dong(o.value.rstrip('\n'), _rong_vung(ws, c1, c2), ten, co, dam, do)
    dong = [x for x in dong] or ['']
    cao = co * 1.107 * EMU_PT                 # Times New Roman: ascent 0,891 + descent 0,216 cỡ chữ (khoảng cách dòng của Excel)
    tren, duoi = bd[r1 - 1], bd[r2]
    doc = (o.alignment.vertical or 'bottom') if o.alignment is not None else 'bottom'
    if doc == 'top':
        y0 = tren + DK_LE_TREN * EMU_PT
    elif doc in ('center', 'justify', 'distributed'):
        y0 = tren + ((duoi - tren) - cao * len(dong)) / 2
    else:                                     # canh dưới: Excel đặt chữ sát đáy ô (đo trên bản in)
        y0 = duoi - cao * len(dong)
    ngang = (o.alignment.horizontal or 'general') if o.alignment is not None else 'general'
    return dict(x1=bc[c1 - 1], x2=bc[c2], ngang=ngang, dong=dong, chan=[y0 + cao * (i + 1) for i in range(len(dong))],
                ten=ten, co=co, dam=dam, doan_cuoi=o.value.rstrip('\n').split('\n')[-1].strip())


def can_duong_ke(ws, xml: str, do=None) -> str:
    """Canh lại các đường kẻ ngang (XML của mẫu) theo chữ ngay phía trên, sau khi đã điền nội dung: đường kẻ nằm sát chân dòng
    chữ cuối của ô phía trên (hở theo cỡ chữ, xa hơn khi có dấu nặng - DK_*) và căn giữa theo dòng chữ đó. Độ dài: dưới "Độc lập - Tự do - Hạnh phúc" bằng
    đúng dòng chữ (thể thức văn bản); đường khác giữ độ dài trong mẫu nhưng không dài quá dòng chữ. Không tìm được chữ phía
    trên thì giữ nguyên đường kẻ."""
    if not xml.strip():
        return xml
    do = do or _ham_do_chu()
    if do is None:
        do = lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47)      # noqa: E731
    bc, bd = _bien_cot(ws), _bien_dong(ws)
    cm = _chi_muc_gop(ws)
    from .lap_pa import bo_dau

    def mot(a: str) -> str:
        neo = {m.group(1): tuple(int(v) for v in m.group(2, 3, 4, 5)) for m in _RE_NEO.finditer(a)}
        if 'from' not in neo or 'to' not in neo:
            return a
        (c1, o1, r1, q1), (c2, o2, r2, q2) = neo['from'], neo['to']
        if r1 + 1 >= len(bd) or r2 + 1 >= len(bd):
            return a
        x1, x2 = bc[c1] + o1, bc[c2] + o2
        y = (bd[r1] + q1 + bd[r2] + q2) / 2
        if x2 < x1:
            x1, x2 = x2, x1
        xg = (x1 + x2) / 2
        # chữ phía trên: ô (dòng của đường kẻ hoặc 1-2 dòng trên) phủ điểm giữa đường kẻ, chân dòng chữ cuối gần đường kẻ nhất
        tot, kc, da = None, None, set()
        for r in range(max(1, r1 - 1), r1 + 2):            # dòng Excel phía trên, dòng chứa đường kẻ, dòng kế
            for c in range(1, 26):
                m = _vung_tron(ws, r, c, cm)
                rr, cc, cuoi = (m.min_row, m.min_col, m.max_col) if m else (r, c, c)
                if (rr, cc) in da or not (bc[cc - 1] <= xg < bc[cuoi]):
                    continue
                da.add((rr, cc))
                t = _dong_chu_o(ws, rr, cc, bc, bd, do, cm)
                if t is None:
                    continue
                d = abs(t['chan'][-1] - y)
                if kc is None or d < kc:
                    tot, kc = t, d
        if tot is None or kc > 40 * EMU_PT:
            return a
        chu = tot['dong'][-1].strip()
        rong = do(chu, tot['ten'], tot['co'], tot['dam']) * EMU_PT
        if bo_dau(tot['doan_cuoi']).lower() == _TIEU_NGU:     # tiêu ngữ: đường kẻ dài bằng cả dòng tiêu ngữ (thể thức văn bản)
            dai = min(do(tot['doan_cuoi'], tot['ten'], tot['co'], tot['dam']) * EMU_PT, tot['x2'] - tot['x1'])
        elif bo_dau(chu).lower().startswith('du an'):     # "Dự án: …": 7 cm (không dài hơn chữ), giữa dòng chữ
            dai = min(DK_DU_AN_CM * EMU_CM, rong, tot['x2'] - tot['x1'])
        elif ':' not in chu and len(chu) <= 40:
            dai = rong * 0.72                                 # tên đơn vị (CHI NHÁNH…): ngắn hơn chữ, căn giữa
        else:
            dai = min(x2 - x1, rong)
        if tot['ngang'] in ('left', 'general', 'justify'):
            giua = tot['x1'] + 2 * EMU_PX + rong / 2
        elif tot['ngang'] == 'right':
            giua = tot['x2'] - 2 * EMU_PX - rong / 2
        else:
            giua = (tot['x1'] + tot['x2']) / 2
        nx1, nx2, ny = int(giua - dai / 2), int(giua + dai / 2), int(tot['chan'][-1] + max(DK_CACH, tot['co'] * (
            DK_CO_DAU_DUOI if _DAU_DUOI & set(unicodedata.normalize('NFC', chu)) else DK_KHONG_DAU_DUOI)) * EMU_PT)
        (ca, oa), (cb, ob), (ra, qa) = _neo(nx1, bc), _neo(nx2, bc), _neo(ny, bd)
        a = _RE_NEO.sub(lambda m: (f'<xdr:{m.group(1)}><xdr:col>{ca if m.group(1) == "from" else cb}</xdr:col><xdr:colOff>'
                                   f'{oa if m.group(1) == "from" else ob}</xdr:colOff><xdr:row>{ra}</xdr:row><xdr:rowOff>{qa}'
                                   f'</xdr:rowOff></xdr:{m.group(1)}>'), a)
        a = re.sub(r'<a:off x="-?\d+" y="-?\d+"/>', f'<a:off x="{nx1}" y="{ny}"/>', a)
        return re.sub(r'<a:ext cx="\d+" cy="\d+"/>', f'<a:ext cx="{nx2 - nx1}" cy="0"/>', a)

    return re.sub(r'<xdr:twoCellAnchor.*?</xdr:twoCellAnchor>', lambda m: mot(m.group(0)), xml, flags=re.S)


def _mot_duong(so: int, x1: int, x2: int, y: int, bc: list, bd: list) -> str:
    """XML một đường kẻ ngang (twoCellAnchor, nét đen mảnh) từ x1 tới x2 (EMU) ở độ cao y."""
    (ca, oa), (cb, ob), (r, q) = _neo(x1, bc), _neo(x2, bc), _neo(y, bd)
    return (f'<xdr:twoCellAnchor><xdr:from><xdr:col>{ca}</xdr:col><xdr:colOff>{oa}</xdr:colOff><xdr:row>{r}</xdr:row>'
            f'<xdr:rowOff>{q}</xdr:rowOff></xdr:from><xdr:to><xdr:col>{cb}</xdr:col><xdr:colOff>{ob}</xdr:colOff><xdr:row>{r}'
            f'</xdr:row><xdr:rowOff>{q}</xdr:rowOff></xdr:to><xdr:cxnSp macro=""><xdr:nvCxnSpPr><xdr:cNvPr id="{so}" '
            f'name="Đường kẻ {so}"/><xdr:cNvCxnSpPr/></xdr:nvCxnSpPr><xdr:spPr><a:xfrm><a:off x="{x1}" y="{y}"/>'
            f'<a:ext cx="{x2 - x1}" cy="0"/></a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom>{_NET}</xdr:spPr>'
            f'</xdr:cxnSp><xdr:clientData/></xdr:twoCellAnchor>')


def dk_mac_dinh(ws, ds: list, do=None) -> str:
    """Đường kẻ mặc định khi mẫu không có file .duong_ke.xml (máy cập nhật bằng gói .pabtcn - gói không mang mau_in):
    ds = [(vị trí ô (vi_tri_cho), tỷ lệ độ dài so với dòng chữ cuối)]; vị trí dọc / ngang canh lại bằng can_duong_ke."""
    do = do or _ham_do_chu() or (lambda s, ten, co, dam: len(s) * co * (0.52 if dam else 0.47))
    bc, bd = _bien_cot(ws), _bien_dong(ws)
    kq = []
    for vt, ty_le in ds:
        if not vt:
            continue
        r, c1, c2, r2 = vt
        t = _dong_chu_o(ws, r, c1, bc, bd, do)
        if t is None:
            continue
        rong = do(t['dong'][-1].strip(), t['ten'], t['co'], t['dam']) * EMU_PT * ty_le
        giua = (t['x1'] + t['x2']) / 2
        kq.append(_mot_duong(len(kq) + 2, int(giua - rong / 2), int(giua + rong / 2), int(t['chan'][-1]), bc, bd))
    return ''.join(kq)


def o_tieu_ngu(ws, den_dong: int = 8):
    """Vị trí (như vi_tri_cho) ô có dòng "Độc lập - Tự do - Hạnh phúc", hoặc None."""
    from .lap_pa import bo_dau
    for o in _o_chu(ws, den_dong):
        if bo_dau(o.value.rstrip('\n').split('\n')[-1].strip()).lower() == _TIEU_NGU:
            m = _vung_tron(ws, o.row, o.column)
            return (o.row, m.min_col, m.max_col, m.max_row) if m else (o.row, o.column, o.column, o.row)
    return None


def _doc_dk(file_dk) -> str:
    try:
        return Path(file_dk).read_text(encoding='utf-8')
    except OSError:
        return ''


def duong_ke_cua_mau(mau_xlsx, ten: str) -> Path:
    """File đường kẻ dùng khi in. Mẫu đã mở sửa trong Excel (còn hình vẽ, có thể đã kéo đường kẻ) thì lấy đường kẻ ngay
    trong mẫu và ghi lại <mẫu>.duong_ke.xml; không thì dùng file .duong_ke.xml sẵn có."""
    import zipfile
    mau_xlsx = Path(mau_xlsx)
    p = mau_xlsx.with_name(f'{mau_xlsx.stem}.duong_ke.xml')      # mẫu riêng (IN_CHITIET__Duthao) có đường kẻ riêng
    if mau_xlsx.stem != ten and not p.exists():
        p = mau_xlsx.with_name(f'{ten}.duong_ke.xml')             # chưa có: dùng đường kẻ của mẫu chính
    try:
        x = doc_duong_ke(mau_xlsx, ten)
    except (KeyError, OSError, AttributeError, zipfile.BadZipFile):
        x = ''
    if x:
        p = mau_xlsx.with_name(f'{mau_xlsx.stem}.duong_ke.xml')
        try:
            if not p.exists() or p.read_text(encoding='utf-8') != x:
                p.write_text(x, encoding='utf-8')
        except OSError:                             # thư mục mẫu chỉ đọc: dùng bản tạm
            p = Path(tempfile.gettempdir()) / f'PABT_{ten}.duong_ke.xml'
            p.write_text(x, encoding='utf-8')
    return p


TACH_MAU = '__'                 # mẫu riêng: <TEN>__<tên mẫu>.xlsx (vd. IN_CHITIET__Duthao.xlsx) cạnh mẫu chính


MAU_DU_THAO = {TEN_CT: 'IN_CHITIET_DT', TEN_BTH: 'IN_TONGHOP_DT'}


def la_mau_du_thao(mau) -> bool:
    """Mẫu dự thảo (IN_CHITIET_DT, IN_TONGHOP_DT, hoặc mẫu riêng tên có 'duthao' - kể cả có dấu "IN_CHITIET__Dự thảo": trước
    0.9.65 không bỏ dấu nên mẫu riêng người dùng đặt tên tiếng Việt bị coi là bản chính thức, chữ DỰ THẢO bị xóa khi in)."""
    from .lap_pa import bo_dau
    s = bo_dau(Path(mau).stem).upper().replace(' ', '').replace('_', '')
    return s.endswith('DT') and ('CHITIET' in s or 'TONGHOP' in s or 'BANGTONGHOP' in s) or 'DUTHAO' in s


DAU_DU_THAO = '(DỰ THẢO)'
_RE_DU_THAO = re.compile(r'DỰ\s*THẢO', re.I)


def co_dau_du_thao(ws) -> bool:
    """Mẫu đã có chữ DỰ THẢO ở ô nào đó (người dùng tự đặt vị trí, cỡ chữ trong mẫu chính)."""
    return any(isinstance(o.value, str) and _RE_DU_THAO.search(o.value) for o in getattr(ws, '_cells', {}).values())


def dat_dau_du_thao(ws, ten: str = TEN_CT) -> None:
    """Bản DỰ THẢO in bằng MẪU CHÍNH (0.9.82 - người dùng 14/10/2026: một mẫu cho cả hai chế độ, không phải giữ hai bộ mẫu):
    mẫu đã có chữ DỰ THẢO -> giữ nguyên; chưa có -> thêm "(DỰ THẢO)" đúng chỗ của mẫu dự thảo gốc: phương án chi tiết = dòng dưới
    "Số: …/…" (cùng ô, như IN_CHITIET_DT); bảng tổng hợp = cuối tiêu đề "BẢNG TỔNG HỢP …". Không tìm được chỗ -> ô "Số:"."""
    if co_dau_du_thao(ws):
        return
    o_list = sorted((o for o in getattr(ws, '_cells', {}).values() if isinstance(o.value, str) and o.row <= 12),
                    key=lambda o: (o.row, o.column))
    if ten == TEN_BTH:
        tieu = next((o for o in o_list if 'BẢNG TỔNG HỢP' in o.value.upper()), None)
        if tieu is not None:
            # 16/10/2026 (người dùng: "bảng tổng hợp không có chữ dự thảo"): trước đây nối cuối tiêu đề dài -> khó thấy trên A3;
            # nay DÒNG RIÊNG dưới tiêu đề (cùng ô, như phương án chi tiết dưới "Số:"), dòng cao đủ số dòng chữ
            tieu.value = f'{tieu.value.rstrip()}\n{DAU_DU_THAO}'
            a = copy(tieu.alignment)
            a.wrap_text = True
            tieu.alignment = a
            m = _vung_tron(ws, tieu.row, tieu.column)
            ten_f, co, dam = _phong(tieu)
            rong = _rong_vung(ws, m.min_col, m.max_col) if m else _rong_vung(ws, tieu.column, tieu.column)
            n = len(ngat_dong(tieu.value, rong, ten_f, co, dam))
            rd = ws.row_dimensions[tieu.row]
            rd.height = max(float(rd.height or 0), cao_dong_chu(n, co) + 2)
            return
    so = next((o for o in o_list if re.match(r'\s*Số\s*:', o.value)), None)
    if so is not None:
        so.value = f'{so.value.rstrip()}\n{DAU_DU_THAO}'
        a = copy(so.alignment)
        a.wrap_text = True
        so.alignment = a


def ap_che_do_du_thao(ws, du_thao: bool, ten: str = TEN_CT) -> None:
    """Chế độ phát hành quyết định chữ DỰ THẢO (không phụ thuộc tên file mẫu): dự thảo -> giữ / thêm; chính thức -> xóa."""
    if du_thao:
        dat_dau_du_thao(ws, ten)
    else:
        _an_du_thao(ws)


def _an_du_thao(ws) -> None:
    """Bản in chính thức (đã có số phương án): bỏ dòng chữ DỰ THẢO còn sót trong mẫu."""
    for o in list(getattr(ws, '_cells', {}).values()):
        if not isinstance(o.value, str) or not re.search(r'DỰ\s*THẢO', o.value, re.I):
            continue
        v = re.sub(r'[ \t]*\(?\s*DỰ\s*THẢO\s*\)?[ \t]*', '', o.value, flags=re.I)
        v = re.sub(r'\n{2,}', '\n', v).strip('\n')
        o.value = v or None


def _dat_duong_ke(ws, vt_dk, file_dk) -> str:
    """Đường kẻ dưới tên đơn vị, tiêu ngữ và dòng dự án: sát chân dòng chữ cuối, căn giữa đoạn chữ đó."""
    dk = dk_mac_dinh(ws, vt_dk)
    if not (dk or '').strip():
        dk = _doc_dk(file_dk)
    return can_duong_ke(ws, dk) if dk else ''


def file_mau(mau, ten: str) -> Path:
    """mau: thư mục mẫu (None = thu_muc_mau()) hoặc chính file mẫu .xlsx (mẫu riêng chọn khi In / Xuất)."""
    if mau is not None and str(mau).lower().endswith('.xlsx'):
        return Path(mau)
    return Path(mau or thu_muc_mau(ten)) / f'{ten}.xlsx'


def ds_mau(ten: str) -> list:
    """[(tên hiển thị, file)] các mẫu của loại ten: mẫu chính trước, rồi các mẫu riêng (thư mục mẫu đang dùng + thư mục ghi)."""
    try:
        chinh = thu_muc_mau(ten) / f'{ten}.xlsx'
    except LoiIn:
        return []
    kq, da = [('Mẫu chính', chinh)], set()
    for d in dict.fromkeys([chinh.parent, thu_muc_mau_ghi()]):
        for f in sorted(Path(d).glob(f'{ten}{TACH_MAU}*.xlsx')):
            t = f.stem[len(ten) + len(TACH_MAU):]
            if t and t.lower() not in da and not f.name.startswith('~$'):
                da.add(t.lower())
                kq.append((t, f))
    ten_dt = MAU_DU_THAO.get(ten)
    if ten_dt:
        for d in dict.fromkeys([chinh.parent, thu_muc_mau_ghi()]):
            f = Path(d) / f'{ten_dt}.xlsx'
            if f.exists() and f.resolve() not in {x.resolve() for _, x in kq}:
                kq.append(('Dự thảo (áp giá trước niêm yết)', f))
                break
    return kq


def mau_de_sua(ten: str = TEN_CT) -> Path:
    """File mẫu in để mở bằng Excel sửa trực tiếp (chữ, phông, lề, độ rộng cột, đường kẻ...). Bản cài: chép mẫu đang dùng
    sang %APPDATA%\\PABT\\mau_in (thư mục cài không ghi được) - từ đó phần mềm in theo mẫu đã sửa."""
    import shutil
    ghi = thu_muc_mau_ghi()
    for t in (TEN_CT, TEN_BTH):
        try:
            goc = thu_muc_mau(t)
        except LoiIn:
            continue
        if goc.resolve() != ghi.resolve():
            ghi.mkdir(parents=True, exist_ok=True)
            for f in (f'{t}.xlsx', f'{t}.duong_ke.xml', 'IN_CHITIET_DT.xlsx', 'IN_TONGHOP_DT.xlsx',
                      'IN_CHITIET_DT.duong_ke.xml', 'IN_TONGHOP_DT.duong_ke.xml'):
                if (goc / f).exists() and not (ghi / f).exists():
                    shutil.copy2(goc / f, ghi / f)
    return ghi / f'{ten}.xlsx'


def _don_xem_truoc_cu(giu_gio: float = 12) -> None:
    """Xóa các thư mục in thử cũ (quá giu_gio giờ) trong %TEMP% - mỗi lần xem trước để lại một file xlsx / pdf."""
    han = time.time() - giu_gio * 3600
    try:
        for d in Path(tempfile.gettempdir()).glob('PABT_xem_truoc_*'):
            try:
                if d.is_dir() and d.stat().st_mtime < han:
                    shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass
    except OSError:
        pass


def xem_truoc(con, ma_ho: int, thu_muc=None, mau=None, du_thao: bool | None = None) -> Path:
    """Bản in thử phương án chi tiết của một hộ (PDF nếu máy có Excel, không thì .xlsx) trong thư mục tạm. Trả file.
    mau: file mẫu riêng (None = mẫu chính); du_thao: chế độ phát hành (lap_chi_tiet)."""
    if thu_muc is None:
        _don_xem_truoc_cu()
    td = Path(thu_muc or tempfile.mkdtemp(prefix='PABT_xem_truoc_'))
    f = lap_chi_tiet(con, ma_ho, td / f'{ten_file_ho(con, ma_ho)}.xlsx', mau, du_thao=du_thao)
    if co_excel():
        pdf = f.with_suffix('.pdf')
        if not chay_excel([(f, pdf)], 'pdf') and pdf.exists():
            return pdf
    return f


# ---------------------------------------------------------------- chèn / xóa dòng giữ định dạng
def _doi_dong(ws, idx: int, so: int):
    """Chèn (so > 0) hoặc xóa (so < 0) dòng tại idx, dời theo các vùng trộn ô, chiều cao dòng, định dạng có điều kiện."""
    if so == 0:
        return
    if so > 0:
        ws.insert_rows(idx, so)
    else:
        ws.delete_rows(idx, -so)
    cuoi_xoa = idx - so - 1 if so < 0 else None
    giu = []
    for m in list(ws.merged_cells.ranges):
        if so < 0 and m.min_row >= idx and m.max_row <= cuoi_xoa:
            continue                                    # vùng trộn nằm trong phần bị xóa
        if m.min_row >= idx:
            m.shift(row_shift=so)
        giu.append(m)
    ws.merged_cells = MultiCellRange(giu)
    cao = {r: (d.height, d.hidden) for r, d in ws.row_dimensions.items()}
    for r in list(ws.row_dimensions.keys()):
        del ws.row_dimensions[r]
    for r, (h, an) in cao.items():
        if so < 0 and idx <= r <= cuoi_xoa:
            continue
        r2 = r + so if r >= idx else r
        if r2 < 1:
            continue
        if h is not None:
            ws.row_dimensions[r2].height = h
        if an:
            ws.row_dimensions[r2].hidden = True
    cf_cu = ws.conditional_formatting
    cf_moi = ConditionalFormattingList()
    for cf in cf_cu:
        vung = []
        for cr in cf.sqref.ranges:
            cr = CellRange(cr.coord)
            if cr.min_row >= idx:
                cr.shift(row_shift=so)
            elif cr.max_row >= idx and so > 0:
                cr.expand(down=so)
            vung.append(cr)
        _them_cf(cf_moi, cf, vung)
    ws.conditional_formatting = cf_moi


def _goc_vung(ds) -> tuple:
    """Ô trên cùng bên trái của danh sách vùng (CellRange)."""
    return min((cr.min_row, cr.min_col) for cr in ds)


def _them_cf(cf_moi, cf, vung: list):
    """Thêm các quy tắc của cf vào cf_moi với vùng mới. Công thức của định dạng có điều kiện tính THEO Ô TRÊN CÙNG BÊN TRÁI của
    vùng ("$AD18" = cột AD của dòng đang xét): vùng dời mà công thức giữ nguyên thì so nhầm dòng (người dùng 16/10/2026: nguồn gốc
    đất dài chèn thêm dòng phía trên bảng -> dòng đề mục mất đậm, dòng tài sản lại đậm). Dời tham chiếu tương đối theo vùng."""
    from openpyxl.formula.translate import Translator
    from openpyxl.utils import get_column_letter
    if not vung:
        return
    r0, c0 = _goc_vung(cf.sqref.ranges)
    r1, c1 = _goc_vung(vung)
    cu, moi = f'{get_column_letter(c0)}{r0}', f'{get_column_letter(c1)}{r1}'
    for rule in cf.rules:
        if cu != moi and rule.formula:
            rule = copy(rule)
            rule.formula = [Translator(f if f.startswith('=') else '=' + f, cu).translate_formula(moi)[1:]
                            for f in rule.formula]
        cf_moi.add(' '.join(cr.coord for cr in vung), rule)


def _chep_kieu_dong(ws, nguon: int, dich: int, so_cot: int):
    for c in range(1, so_cot + 1):
        ws.cell(dich, c)._style = copy(ws.cell(nguon, c)._style)


def _so(v):
    """Decimal -> int / float để Excel nhận là số."""
    if v is None or v == '':
        return None
    v = D(v)
    return int(v) if v == v.to_integral_value() else float(v)


try:
    from openpyxl.styles.cell_style import StyleArray as _StyleArray
except ImportError:                                     # openpyxl khác: _gop_o dùng ws.merge_cells
    _StyleArray = None


def _kieu(x):
    """Bảng chỉ số kiểu của ô (openpyxl tạo khi gán kiểu lần đầu - StyleDescriptor)."""
    if not x._style:
        x._style = _StyleArray()
    return x._style


def _gop_o(ws, r1: int, c1: int, r2: int, c2: int) -> None:
    """Gộp ô như ws.merge_cells nhưng không so vùng mới với TẤT CẢ vùng gộp đã có (openpyxl duyệt hết mỗi lần gộp: bảng tổng hợp
    300 hộ ~2.000 vùng gộp = ~2 triệu phép so, 9 giây). Vùng gộp của bản in không chồng nhau. openpyxl khác cấu trúc: dùng merge_cells."""
    from openpyxl.utils import get_column_letter
    vung = f'{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}'
    ds = getattr(ws.merged_cells, 'ranges', None)
    if not isinstance(ds, set) or not hasattr(ws, '_cells') or _StyleArray is None:   # openpyxl khác cấu trúc: cách của openpyxl
        ws.merge_cells(vung)
        return
    m = _vung_gop(ws, vung)
    ds.add(m)
    _dinh_dang_gop(ws, m)


def _vung_gop(ws, vung: str):
    """Như MergedCellRange(ws, vung) (openpyxl 3.1: __init__ -> _get_borders: ô đầu nhận viền phải / dưới của ô cuối) nhưng nhớ kết quả
    cộng viền theo (viền ô đầu, viền ô cuối) - openpyxl băm lại đối tượng viền mỗi vùng (3.000 hộ ~19.000 vùng, ~3 giây)."""
    from openpyxl.styles.borders import Border
    from openpyxl.worksheet.cell_range import CellRange
    from openpyxl.worksheet.merge import MergedCellRange
    m = MergedCellRange.__new__(MergedCellRange)
    m.ws = ws
    CellRange.__init__(m, range_string=vung)
    dau = ws._cells.get((m.min_row, m.min_col))
    if dau is None:
        dau = ws.cell(row=m.min_row, column=m.min_col)
    m.start_cell = dau
    cuoi = ws._cells.get((m.max_row, m.max_col))
    if cuoi is not None:
        nho = ws.parent.__dict__.setdefault('_pabt_vien_dau', {})
        k = (_kieu(dau).borderId, _kieu(cuoi).borderId)
        moi = nho.get(k)
        if moi is None:
            dau.border += Border(right=cuoi.border.right, bottom=cuoi.border.bottom)
            nho[k] = _kieu(dau).borderId
        else:
            _kieu(dau).borderId = moi
    return m


def _dinh_dang_gop(ws, m) -> None:
    """Như openpyxl Worksheet._clean_merge_range + MergedCellRange.format (3.1): ô trừ ô đầu thành MergedCell; ô mép nhận viền
    cạnh tương ứng của ô đầu; mọi ô nhận protection của ô đầu. Khác: nhớ kết quả cộng viền theo (viền ô, viền ô đầu, cạnh) cho cả
    workbook - openpyxl băm lại đối tượng viền ở MỖI ô (4 giây / 300 hộ), kết quả giống hệt nhau."""
    from openpyxl.cell.cell import MergedCell
    from openpyxl.styles.borders import Border
    nho = ws.parent.__dict__.setdefault('_pabt_vien_gop', {})
    o = ws._cells
    cac_o = m.cells
    next(cac_o)
    for r, c in cac_o:
        o[r, c] = MergedCell(ws, row=r, column=c)
    dau = m.start_cell
    vien_dau = dau.border
    id_dau = _kieu(dau).borderId
    for ten in ('top', 'left', 'right', 'bottom'):
        canh = getattr(vien_dau, ten)
        if canh and canh.style is None:
            continue
        them = None
        for toa_do in getattr(m, ten):
            x = o.get(toa_do)
            if x is None:
                x = o[toa_do] = MergedCell(ws, row=toa_do[0], column=toa_do[1])
            k = (_kieu(x).borderId, id_dau, ten)
            moi = nho.get(k)
            if moi is None:
                if them is None:
                    them = Border(**{ten: canh})
                x.border += them
                nho[k] = _kieu(x).borderId
            else:
                _kieu(x).borderId = moi
    id_kh = _kieu(dau).protectionId                     # openpyxl: chép protection của ô đầu -> cùng mã trong bảng kiểu
    for toa_do in m.cells:
        x = o.get(toa_do)
        if x is None:
            x = o[toa_do] = MergedCell(ws, row=toa_do[0], column=toa_do[1])
        _kieu(x).protectionId = id_kh


_CHO_VIET = r'[\s….,_]*'                         # khoảng chấm / cách chừa để viết tay số, ngày


def dien_so_ngay(ws, so: str = '', ngay: str = '', nhan_so: str = 'Số:', den_dong: int | None = None) -> int:
    """Điền số / ngày văn bản vào chỗ chừa trống của mẫu (mẫu không cần sửa): '<nhan_so>      /ký hiệu' -> '<nhan_so> 125/ký hiệu';
    'ngày …… tháng …… năm {nam}' -> 'ngày 10 tháng 10 năm 2026' (ngay = dd/mm/yyyy). Trả số ô đã điền."""
    m_ngay = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(ngay or '').strip())
    if not so and not m_ngay:
        return 0
    re_so = re.compile(re.escape(nhan_so) + _CHO_VIET + '/')
    re_ngay = re.compile(r'ngày' + _CHO_VIET + r'tháng' + _CHO_VIET + r'năm\s*(?:\{nam\}|\d{4}|[….]+)')
    n = 0
    for o in _o_chu(ws, den_dong):
        v = s = o.value
        if so:
            s = re_so.sub(lambda m: f'{nhan_so} {so}/', s)
        if m_ngay:
            s = re_ngay.sub(f'ngày {int(m_ngay.group(1)):02d} tháng {int(m_ngay.group(2)):02d} năm {m_ngay.group(3)}', s)
        if s != v:
            o.value = s
            n += 1
    return n


CHO_NGUOI_KY = ('{nguoi_lap}', '{nguoi_kiem_tra}', '{nguoi_ky}')


def can_khoi_ky(ws, tim_tren: int = 12) -> int:
    """Khối chữ ký (LẬP BIỂU / KIỂM TRA / chức vụ ký - họ tên phía dưới): họ tên căn GIỮA ngay dưới chức danh. Gọi TRƯỚC
    _thay_cho_trong (nhận ô họ tên theo chỗ trống {nguoi_lap}, {nguoi_kiem_tra}, {nguoi_ky}). Mỗi ô họ tên: tìm ô chức danh gần nhất
    phía trên (tối đa tim_tren dòng) phủ cột giữa của ô họ tên; bỏ dấu cách thừa đầu / cuối chức danh (mẫu "   KIỂM TRA     " - Excel
    căn giữa tính cả dấu cách nên chữ lệch khỏi họ tên), ô họ tên gộp ĐÚNG các cột của ô chức danh, cả hai căn giữa không thụt lề.
    Mẫu người dùng tự sửa lệch cột cũng được căn lại. Trả số ô họ tên đã căn."""
    from copy import copy
    chu_dong = {}                                       # {dòng: [ô có chữ]} - một lượt duyệt (không gọi ws.cell từng cột: chậm,
    o_ten = []                                          # còn tạo ô rỗng thừa trong file in ra)
    for c in _o_chu(ws):
        v = c.value.strip()
        if v in CHO_NGUOI_KY:
            o_ten.append(c)
        elif v:
            chu_dong.setdefault(c.row, []).append(c)
    if not o_ten:
        return 0
    dong_can = {rr for o in o_ten for rr in range(max(1, o.row - tim_tren), o.row + 1)}
    chi_muc = {}                                        # vùng gộp chỉ của các dòng quanh khối chữ ký (bảng tổng hợp: 40.000 vùng)
    for m in ws.merged_cells.ranges:
        if m.min_row == m.max_row and m.min_row in dong_can:
            chi_muc.setdefault(m.min_row, []).append(m)

    def vung(r, c):
        m = _vung_tron(ws, r, c, chi_muc)
        return (m.min_col, m.max_col, m) if m is not None and m.min_row == m.max_row == r else (c, c, m)

    def can_giua(o):
        a = copy(o.alignment)
        a.horizontal, a.indent = 'center', 0
        o.alignment = a
    so = 0
    for o in o_ten:
        r = o.row
        n1, n2, mn = vung(r, o.column)
        giua = (n1 + n2) / 2
        td = None
        for rr in range(r - 1, max(0, r - tim_tren), -1):
            for x in chu_dong.get(rr, ()):
                c = x.column
                t1, t2, mt = vung(rr, c)
                if t1 <= giua <= t2 and (mt is None or mt.min_col == c):
                    td = (x, t1, t2)
                    break
            if td is not None:
                break
        if td is None:
            continue
        x, t1, t2 = td
        x.value = x.value.strip()
        can_giua(x)
        o.value = o.value.strip()
        if (t1, t2) != (n1, n2):
            # ô khác trên dòng họ tên nằm trong vùng chức danh (họ tên người khác) -> không gộp lại, chỉ căn giữa
            if all(ws.cell(r, c).value in (None, '') or n1 <= c <= n2 for c in range(t1, t2 + 1)):
                if mn is not None and mn.min_row == mn.max_row == r:
                    ws.unmerge_cells(mn.coord)
                gia_tri, kieu = o.value, o._style
                for c in range(n1, n2 + 1):
                    ws.cell(r, c).value = None
                moi = ws.cell(r, t1)
                moi.value, moi._style = gia_tri, copy(kieu)
                if t2 > t1:
                    _gop_o(ws, r, t1, r, t2)
                chi_muc[r] = [m for m in ws.merged_cells.ranges if m.min_row == m.max_row == r]
                o = moi
        can_giua(o)
        so += 1
    return so


def _thay_cho_trong(ws, gia_tri: dict):
    """Thay {ten} trong mọi ô chữ của sheet."""
    for c in _o_chu(ws):
        if '{' in c.value:
            s = c.value
            for k, v in gia_tri.items():
                s = s.replace('{' + k + '}', str(v))
            c.value = s


def _uoc_cao(text, rong_cot: float, co_chu: float, toi_thieu: float = 26) -> float:
    """Ước chiều cao dòng cho ô tự ngắt dòng (Excel sẽ tự giãn lại khi xuất PDF)."""
    s = str(text or '')
    if not s:
        return toi_thieu
    # số ký tự / dòng ước theo bề rộng cột; nhân 0,9 để dư một chút (chữ đậm, chữ hoa rộng hơn) - thà cao dư hơn mất chữ
    ky_tu_dong = max(1, int(rong_cot * 1.2 * 11 / co_chu * 0.9))
    so_dong = sum(max(1, math.ceil(len(doan) / ky_tu_dong)) for doan in s.split('\n'))
    return min(409, max(toi_thieu, so_dong * co_chu * 1.32 + 8))


COT_CHU_HO_BTH = (2, 3, 23, 24, 25)     # bảng tổng hợp: họ tên, địa chỉ, nguồn gốc, tái định cư, ghi chú (gộp theo số thửa)
COT_CHU_THUA_BTH = (6, 14)              # loại đất, vị trí (mỗi thửa một dòng)


def _so_dong_bth(ws, rr: int, c: int, px: list, do=None, nho: dict | None = None) -> int:
    """Số dòng chữ ô (rr, c) của bảng tổng hợp; nho: {(chữ, cột, phông): số dòng} - địa chỉ, loại đất, vị trí lặp lại nhiều."""
    o = ws.cell(rr, c)
    if not isinstance(o.value, str) or not px[c - 1]:
        return 1
    ten, co, dam = _phong(o)
    k = (o.value, c, ten, co, dam)
    if nho is not None and k in nho:
        return nho[k]
    so = so_dong_o(o.value, px[c - 1] * 0.75 - 6, ten, co, dam, do)
    if nho is not None:
        nho[k] = so
    return so


def cao_can_ho_bth(ws, r0: int, px: list, do=None, nho: dict | None = None, cot_ho: tuple = COT_CHU_HO_BTH) -> float:
    """Chiều cao (pt, không chặn 409) các ô gộp theo hộ (họ tên, địa chỉ, nguồn gốc…) của hộ bắt đầu ở dòng r0 cần."""
    co = float(ws.cell(r0, cot_ho[0]).font.sz or 14)
    return max(cao_dong_bang(_so_dong_bth(ws, r0, c, px, do, nho), co, None) for c in cot_ho)


def _vua_cao_ho_bth(ws, r0: int, r: int, px: list | None = None, do=None, can: float | None = None,
                    nho: dict | None = None, cot_ho: tuple = COT_CHU_HO_BTH, cot_thua: tuple = COT_CHU_THUA_BTH) -> None:
    """Bảng tổng hợp: ô họ tên / địa chỉ / nguồn gốc gộp theo số thửa. Excel không tự giãn ô gộp — tăng cao các dòng
    của hộ cho vừa chữ (số dòng chữ đo theo phông, cao_dong_bang: đệm 4 pt trên / dưới), mỗi dòng thửa vẫn đủ chỗ cho
    vị trí; không thấp hơn dòng mẫu và 24 pt; phần thiếu chia đều các dòng, mỗi dòng không quá 409 pt (lap_bang_tong_hop
    đã thêm dòng cho hộ cần cao hơn)."""
    n = r - r0
    if n <= 0:
        return
    px = px or _px_cot(ws, 26)
    co = float(ws.cell(r0, cot_ho[0]).font.sz or 14)
    if can is None:
        can = cao_can_ho_bth(ws, r0, px, do, nho, cot_ho)
    mac = max(float(ws.row_dimensions[r0].height or 36), cao_dong_bang(1, co))
    ds = [max(mac, cao_dong_bang(max(_so_dong_bth(ws, r0 + i, c, px, do, nho) for c in cot_thua), co))
          for i in range(n)]
    for _ in range(n):                                  # chia phần thiếu cho các dòng còn dưới trần 409 pt
        thieu = can - sum(ds)
        con = [i for i, c in enumerate(ds) if c < CAO_TOI_DA]
        if thieu <= 0.01 or not con:
            break
        for i in con:
            ds[i] = min(CAO_TOI_DA, ds[i] + thieu / len(con))
    for i, cao in enumerate(ds):
        ws.row_dimensions[r0 + i].height = cao


NHAN_TDC = 'Tái định cư:'


def _nhan_dam(o, nhan: str) -> None:
    """Ô chữ "<nhãn> <nội dung>": nhãn in đậm, nội dung chữ thường (không đậm / nghiêng) - người dùng 15/10/2026 dòng IV "Tái định
    cư: Đủ điều kiện…" (mẫu cả dòng in đậm). Chữ nhiều định dạng trong một ô (openpyxl >= 3.1); thiếu thì giữ nguyên."""
    try:
        from openpyxl.cell.rich_text import CellRichText, TextBlock
        from openpyxl.cell.text import InlineFont
    except ImportError:
        return
    f = o.font
    kieu = dict(rFont=f.name, sz=f.sz, color=f.color, u=f.u)
    con_lai = str(o.value)[len(nhan):]
    o.value = CellRichText([TextBlock(InlineFont(b=True, **kieu), nhan)] +
                           ([TextBlock(InlineFont(b=False, i=False, **kieu), con_lai)] if con_lai else []))


def _gian_dong(ws, r: int, c: int, co_chu: float) -> None:
    """Ô chữ dài (kể cả ô gộp nhiều cột): bật xuống dòng và tăng chiều cao dòng cho đủ chữ."""
    from openpyxl.utils import get_column_letter
    o = ws.cell(r, c)
    c1, c2 = c, c
    for m in ws.merged_cells.ranges:
        if m.min_row <= r <= m.max_row and m.min_col <= c <= m.max_col:
            c1, c2 = m.min_col, m.max_col
            break
    rong = sum((ws.column_dimensions[get_column_letter(x)].width or 9) for x in range(c1, c2 + 1))
    co = (o.font.sz if o.font is not None and o.font.sz else co_chu) * (1.08 if o.font is not None and o.font.b else 1)
    al = copy(o.alignment)
    al.wrap_text = True
    al.vertical = al.vertical or 'center'
    o.alignment = al
    can = _uoc_cao(o.value, rong, co)
    if (ws.row_dimensions[r].height or 15) < can:
        ws.row_dimensions[r].height = can


# ---------------------------------------------------------------- đo chữ để đặt chiều cao dòng vừa khít
# Excel không tự giãn chiều cao ô gộp nhiều cột (tên dự án, nguồn gốc đất) nên phần mềm tự tính: đo bề rộng chữ bằng phông thật
# (Qt, khi đang chạy giao diện) rồi ngắt dòng như Excel; không có Qt thì ước theo số ký tự (dư một chút để không mất chữ).
_MDW = {('Calibri', 11): 7, ('Arial', 10): 7, ('Arial', 11): 8, ('Times New Roman', 11): 7, ('Times New Roman', 12): 8,
        ('Times New Roman', 13): 9, ('Times New Roman', 14): 9}
CAO_TOI_DA = 409                                # chiều cao dòng lớn nhất Excel cho phép (pt)


def _ham_do_chu():
    """Hàm (chữ, tên phông, cỡ pt, đậm) -> bề rộng (pt), hoặc None khi không có giao diện Qt."""
    try:
        from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication
    except ImportError:
        return None
    if not isinstance(QGuiApplication.instance(), QGuiApplication):
        return None
    bo_dem = {}

    def do(chu: str, ten: str, co: float, dam: bool) -> float:
        k = (ten, co, dam)
        if k not in bo_dem:
            f = QFont(ten)
            f.setPixelSize(max(1, int(round(co * 10))))     # 1 px = 0,1 pt: đo theo pt, không phụ thuộc DPI màn hình
            f.setBold(dam)
            bo_dem[k] = QFontMetricsF(f)
        return bo_dem[k].horizontalAdvance(chu) / 10
    return do


def _mdw(wb) -> int:
    """Bề rộng chữ số (px) của phông mặc định workbook: đơn vị độ rộng cột Excel."""
    try:
        f = wb._fonts[0]
        return _MDW.get((f.name, int(f.sz or 11)), 7)
    except (AttributeError, IndexError, TypeError):
        return 7


def _px_cot(ws, den: int = 61) -> list:
    """Bề rộng (px) cột 1..den (phần tử 0 = cột A) như Excel: cột ẩn = 0; khai báo theo dải cột (<col min max>) áp cho cả
    dải; không khai báo = độ rộng mặc định của sheet. (Trước 0.9.21 đọc theo chữ cột: cột ẩn vẫn tính, dải cột bị bỏ -
    bảng tổng hợp có cột L, M, O ẩn làm đường kẻ lệch.) Không tạo thêm khai báo cột như ws.column_dimensions[chữ]."""
    mdw = _mdw(ws.parent)
    mac_dinh = float(ws.sheet_format.defaultColWidth or 8.43)
    rong = [mac_dinh] * den
    for d in list(ws.column_dimensions.values()):
        a, b = (d.min or 0), (d.max or d.min or 0)
        for c in range(max(1, a), min(b, den) + 1):
            rong[c - 1] = 0.0 if d.hidden else float(d.width or mac_dinh)
    return [int(w * mdw + 0.5) if w > 0 else 0 for w in rong]


def _rong_vung(ws, c1: int, c2: int) -> float:
    """Bề rộng (pt) chỗ viết chữ trong vùng cột c1..c2 (trừ lề trong ô)."""
    px = sum(_px_cot(ws, max(c2, 1))[c1 - 1:c2])
    return px * 0.75 - 6


TREO = 'treo'           # dòng tràn của gạch đầu dòng: xuống dòng cứng + khoảng trắng thụt vào (Excel không có thụt lề treo)


NBSP = '\xa0'                   # khoảng trắng không ngắt: thụt đầu dòng - Excel căn đều không giãn / không ngắt ở đây


def _ngat(chu: str, rong: float, ten: str, co: float, dam: bool, do=None, treo: bool = True, thut_dau: float = 0,
          noi_tiep: bool = False) -> list:
    """Ngắt chữ thành các dòng như Excel (theo từ; '\\n' là xuống đoạn). Trả [(dòng, đầu đoạn)]: đầu đoạn True / False, hoặc
    TREO = dòng tràn của đoạn bắt đầu bằng gạch đầu dòng ("- ", "+ ", "a) "… - ho_so.dau_dong): dòng đó đã có sẵn khoảng trắng
    thụt vào thẳng chữ sau ký hiệu, khi ghi vào ô phải xuống dòng cứng (dat_doan_van). treo=False: không thụt lề treo - dòng tràn
    về sát lề như Excel tự ngắt (ô căn đều hai bên: dòng kết thúc bằng xuống dòng cứng Excel KHÔNG căn đều)."""
    from .ho_so import dau_dong
    do = do or _ham_do_chu()
    if do is None:                               # ước: bề rộng trung bình một ký tự Times New Roman ~ 0,47 cỡ chữ (đậm 0,52)
        tb = co * (0.52 if dam else 0.47)
        do = lambda s, *_: len(s) * tb          # noqa: E731
    rong = rong * 0.97                          # chừa 3%: phông máy in / PDF có thể rộng hơn chút
    # thụt đầu dòng (pt) mỗi đoạn: chuỗi NBSP đứng trước từ đầu đoạn (noi_tiep: đoạn đầu là phần tiếp của đoạn bị chia sang dòng
    # Excel trước - không thụt)
    dau_doan = ''
    if thut_dau > 0:
        mot = do(NBSP, ten, co, dam) or co * 0.25
        dau_doan = NBSP * max(1, int(round(thut_dau / mot)))
    kq = []
    for k, doan in enumerate(str(chu or '').split('\n')):
        ky = dau_dong(doan) if treo else ''
        thut = ''
        if ky:
            cach = do(' ', ten, co, dam) or co * 0.25
            thut = ' ' * max(1, int(round(do(ky.strip() + ' ', ten, co, dam) / cach)))
            if do(thut, ten, co, dam) > rong / 3:
                thut = ''
        dau = True
        dong = dau_doan if doan.strip() and not (noi_tiep and k == 0) else ''
        if dong and thut:
            thut = ' ' * len(dong) + thut

        def xong(d):
            nonlocal dau
            kq.append((d, dau if dau or not thut else TREO))
            dau = False
        for tu in doan.split():
            thu = f'{dong} {tu}' if dong.strip() else (dong + tu)
            if do(thu, ten, co, dam) <= rong or not dong.strip():
                dong = thu
                while do(dong, ten, co, dam) > rong and len(dong) > 1:    # một từ dài hơn cả dòng: cắt ngang
                    n = len(dong)
                    while n > 1 and do(dong[:n], ten, co, dam) > rong:
                        n -= 1
                    xong(dong[:n])
                    dong = thut + dong[n:]
            else:
                xong(dong)
                dong = thut + tu
        xong(dong)
    return kq


def ngat_dong(chu: str, rong: float, ten: str = 'Times New Roman', co: float = 14, dam: bool = False, do=None) -> list:
    """Các dòng chữ sau khi ngắt theo bề rộng rong (pt)."""
    return [x for x, _ in _ngat(chu, rong, ten, co, dam, do)]


def cao_dong_chu(so_dong: int, co: float) -> float:
    """Chiều cao (pt) của so_dong dòng chữ cỡ co: Times New Roman giãn dòng ~1,15 cỡ chữ; lấy 1,2 cho dư một chút
    (Excel làm tròn chiều cao theo điểm ảnh màn hình)."""
    return so_dong * co * 1.2


# chiều cao dòng bảng (người dùng 14/10/2026, ảnh bảng tính dính sát viền): mỗi dòng chữ 16,5 pt ở cỡ 14 (theo tỷ lệ cỡ chữ:
# bảng tổng hợp cỡ 20), cộng đệm 4 pt trên + 4 pt dưới để chân chữ (g, y, p) và dấu nặng / hỏi không chạm đường kẻ ô.
# 16,5 pt là khoảng dòng Excel ở màn hình 100%; đo Excel (AutoFit 10 dòng Times New Roman) ở màn hình 125%: cỡ 12 / 14 / 16 / 20
# = 15,6 / 18 / 21 / 25,2 pt mỗi dòng (~1,3 cỡ chữ) - ô gộp (Excel không tự giãn) theo 16,5 bị cắt dòng cuối -> lấy mức lớn hơn
CAO_DONG_BANG_TOI_THIEU = 24.0
DONG_CHU_14 = 16.5
HE_SO_DONG_EXCEL = 1.3
DEM_DONG = 8.0
CAO_TIEU_DE_BANG = 28.0         # hàng tiêu đề cột (STT, Tên tài sản, ĐVT…) một dòng chữ; tiêu đề nhiều dòng cao theo chữ
# nguồn gốc đất: một dòng Excel không cao quá chừng này - dư thì tách sang dòng kế ở chỗ hết câu. 16/10/2026: 350 -> 90 pt (4 - 5 dòng
# chữ): Excel không cắt đôi một dòng qua hai trang - khối nhỏ lấp sát đáy trang 1 thay vì đẩy cả khối 350 pt sang trang 2 (hở 1/3 trang)
CAO_DOAN_TOI_DA = 90
# nguồn gốc đất (đoạn văn, chữ canh trên): đệm dưới chữ nhỏ - người dùng 15/10/2026: khoảng hở tới dòng "III. Bảng tính toán…"
# quá xa (trước đây đệm 8 pt như ô bảng + 2 dòng thừa của vùng gộp mẫu A13:H15 cao 4 pt mỗi dòng)
DEM_DOAN_VAN = 1.5              # 16/10/2026: các dòng nguồn gốc nối tiếp sát nhau (trước 3 pt) - không khe trắng giữa đoạn
DEM_DOAN_CUOI = 4.0             # dòng nguồn gốc cuối (trước mục III) thêm chừng này


def cao_doan_van(so_dong: int, co: float = 14, cuoi: bool = False) -> float:
    """Chiều cao (pt) dòng Excel chứa so_dong dòng chữ của đoạn văn nguồn gốc đất: cùng khoảng dòng với ô bảng (dong_chu_bang - Excel
    125% không cắt dòng cuối), chỉ thêm DEM_DOAN_VAN cho chân chữ; không chặn tối thiểu 24 pt như ô bảng."""
    return min(CAO_TOI_DA, so_dong * dong_chu_bang(co) + DEM_DOAN_VAN + (DEM_DOAN_CUOI if cuoi else 0.0))


def dong_chu_bang(co: float = 14) -> float:
    """Chiều cao (pt) một dòng chữ cỡ co trong ô bảng: 16,5 pt ở cỡ 14 (theo tỷ lệ), không nhỏ hơn khoảng dòng Excel đo được."""
    return max(DONG_CHU_14 * co / 14, HE_SO_DONG_EXCEL * co)


def cao_dong_bang(so_dong: int, co: float = 14, tran: float = CAO_TOI_DA) -> float:
    """Chiều cao (pt) dòng bảng có so_dong dòng chữ cỡ co: max(24, so_dong x dòng chữ + 8). tran=None: không chặn ở 409 pt
    (để biết cần bao nhiêu dòng Excel)."""
    cao = max(CAO_DONG_BANG_TOI_THIEU, so_dong * dong_chu_bang(co) + DEM_DONG)
    return cao if tran is None else min(tran, cao)


def so_dong_o(chu, rong: float, ten: str = 'Times New Roman', co: float = 14, dam: bool = False, do=None) -> int:
    """Số dòng chữ Excel hiện trong ô rộng rong (pt) khi tự ngắt dòng. Ô số (không phải chữ) luôn một dòng."""
    if not isinstance(chu, str) or not chu.strip() or rong <= 0:
        return 1
    do = do or _ham_do_chu()
    if do is not None and '\n' not in chu and do(chu, ten, co, dam) <= rong * 0.97:     # vừa một dòng: đo một lần (như _ngat)
        return 1
    return max(1, len(_ngat(chu, rong, ten, co, dam, do)))




_RE_HET_CAU_CUOI = re.compile(r'[.;:!?]\s*$')


def _chia_doan_van(chu: str, rong: float, ten: str, co: float, dam: bool, do, toi_da: int, treo: bool = True,
                   thut_dau: float = 0) -> list:
    """Chia chữ thành các khối <= toi_da dòng (mỗi khối một dòng Excel), mỗi khối là các dòng đã ngắt (_ngat). 16/10/2026: cắt ở
    RANH GIỚI DÒNG đã ngắt (Excel ngắt lại đúng chỗ cũ vì cùng bề rộng - chữ chảy liền, không xuống dòng sớm giữa đoạn như khi cắt
    ngay sau dấu chấm giữa dòng): ưu tiên hết đoạn muộn nhất; không có thì dòng kết thúc bằng dấu hết câu (. ; : ! ?) muộn nhất mà
    khối không ngắn hơn nửa khối; không có thì đủ toi_da dòng. Phần tiếp của một đoạn (khối sau) không thụt đầu dòng. Không mất chữ."""
    do = do or _ham_do_chu()
    dong = _ngat(str(chu or ''), rong, ten, co, dam, do, treo, thut_dau)
    kq, i = [], 0
    while i < len(dong):
        j = i + toi_da
        if j < len(dong):
            doan = [k for k in range(i + 1, j + 1) if dong[k][1] is True]           # dòng k mở đoạn mới
            cau = [k for k in range(i + max(1, toi_da // 2), j + 1) if _RE_HET_CAU_CUOI.search(dong[k - 1][0])]
            j = doan[-1] if doan else (cau[-1] if cau else j)
        kq.append(dong[i:j])
        i = j
    return [k for k in kq if k] or [[('', True)]]


def _can_giua_doc(o) -> None:
    """Ô bảng: căn giữa theo chiều dọc, tự xuống dòng (giữ căn ngang của mẫu)."""
    al = o.alignment
    if al.vertical == 'center' and al.wrap_text:
        return
    al = copy(al)
    al.vertical = 'center'
    al.wrap_text = True
    o.alignment = al


def _chi_muc_gop(ws) -> dict:
    """{dòng: [vùng gộp phủ dòng đó]} - để dò nhiều ô trên sheet có hàng chục nghìn vùng gộp (bảng tổng hợp 3.000 hộ: 26.000
    vùng; can_duong_ke dò ~235 ô, mỗi lần duyệt hết danh sách vùng gộp)."""
    kq = {}
    for m in ws.merged_cells.ranges:
        for r in range(m.min_row, m.max_row + 1):
            kq.setdefault(r, []).append(m)
    return kq


def _vung_tron(ws, r: int, c: int, chi_muc: dict | None = None):
    for m in ws.merged_cells.ranges if chi_muc is None else chi_muc.get(r, ()):
        if m.min_row <= r <= m.max_row and m.min_col <= c <= m.max_col:
            return m
    return None


def _o_chu(ws, den_dong: int | None = None):
    """Các ô CÓ CHỮ của sheet theo thứ tự dòng, cột (tới dòng den_dong). Không dùng ws.iter_rows: nó TẠO ô rỗng cho mọi vị trí
    trong vùng sheet (mẫu chi tiết ~700 ô mỗi hộ) - dò chậm và file in ra ghi thêm hàng trăm ô rỗng."""
    for k in sorted(ws._cells):
        if den_dong is not None and k[0] > den_dong:
            break
        o = ws._cells[k]
        if isinstance(o.value, str):
            yield o


def vi_tri_cho(ws, cho: str, den_dong: int = 80):
    """(dòng, cột đầu, cột cuối, dòng cuối) của ô có chỗ trống cho (tính cả vùng gộp), hoặc None."""
    for o in _o_chu(ws, den_dong):
        if cho in o.value:
            m = _vung_tron(ws, o.row, o.column)
            return (o.row, m.min_col, m.max_col, m.max_row) if m else (o.row, o.column, o.column, o.row)
    return None


def _phong(o) -> tuple:
    f = o.font
    return (f.name if f is not None and f.name else 'Times New Roman'), float(f.sz if f is not None and f.sz else 14), \
        bool(f is not None and f.b)


THUT_DAU_CM = 1.0               # thụt đầu dòng mỗi đoạn nguồn gốc đất (người dùng 16/10/2026) - đổi ở ban_in.nguon_goc.thut_dau_cm


def thut_dau_nguon_goc() -> float:
    """Thụt đầu dòng đoạn nguồn gốc đất (pt) theo hồ sơ địa phương ban_in.nguon_goc.thut_dau_cm (0 = không thụt)."""
    from . import dia_phuong
    ng = dia_phuong.lay('ban_in.nguon_goc') or {}
    try:
        cm = float(ng.get('thut_dau_cm', THUT_DAU_CM))
    except (TypeError, ValueError):
        cm = THUT_DAU_CM
    return max(0.0, cm) * 72 / 2.54


def _can_nguon_goc() -> tuple:
    """(căn ngang, căn dọc) ô nguồn gốc đất theo hồ sơ địa phương (mặc định 'justify', 'top')."""
    from . import dia_phuong
    ng = dia_phuong.lay('ban_in.nguon_goc') or {}
    return ng.get('can_ngang', 'justify'), ng.get('can_doc', 'top')


def dat_doan_van(ws, cho: str, chu: str, do=None) -> int:
    """Ô có chỗ trống cho (vd '{nguon_goc}', gộp ngang hết bảng, có thể gộp vài dòng): điền chữ, chiều cao vừa đủ số dòng
    chữ (cao_dong_bang: đệm 4 pt trên / dưới). Chữ cao quá CAO_DOAN_TOI_DA (350 pt, trần Excel 409) thì chia sang các dòng kế
    tiếp, cắt ở chỗ hết đoạn / hết câu (_chia_doan_van; thiếu dòng thì chèn thêm, mỗi dòng mới gộp cùng dải cột, chép viền, căn
    đều + giữa); dòng thừa của vùng gộp cũ thu nhỏ thành khoảng cách. Trả số dòng đã chèn thêm."""
    vt = vi_tri_cho(ws, cho)
    if vt is None:
        return 0
    r, c1, c2, r2 = vt
    o = ws.cell(r, c1)
    chu = o.value.replace(cho, str(chu or ''))
    ten, co, dam = _phong(o)
    toi_da = max(1, int((CAO_DOAN_TOI_DA - DEM_DONG) // dong_chu_bang(co)))
    # căn đều hai bên (mặc định - người dùng 15/10/2026, như văn bản Word): KHÔNG thụt lề treo gạch đầu dòng - thụt lề treo cần
    # xuống dòng cứng mỗi dòng tràn, mà dòng kết thúc bằng xuống dòng cứng thì Excel canh trái (bên phải lởm chởm)
    ngang = _can_nguon_goc()[0]
    # mỗi đoạn thụt đầu dòng (người dùng 16/10/2026), căn chỉnh giữ nguyên
    khoi = _chia_doan_van(chu, _rong_vung(ws, c1, c2), ten, co, dam, do, toi_da, treo=ngang != 'justify',
                          thut_dau=thut_dau_nguon_goc())
    m = _vung_tron(ws, r, c1)
    if m:
        ws.unmerge_cells(m.coord)
    co_san = r2 - r + 1
    chen = max(0, len(khoi) - co_san)
    if chen:
        _doi_dong(ws, r2 + 1, chen)
        for rr in range(r2 + 1, r2 + 1 + chen):
            _chep_kieu_dong(ws, r, rr, max(c2, 8))
    kieu = copy(o._style)
    for i in range(max(co_san, len(khoi))):
        rr = r + i
        for cc in range(c1, c2 + 1):
            ws.cell(rr, cc).value = None
        if i >= len(khoi):
            # dòng thừa của vùng gộp mẫu: ẩn hẳn (trước 15/10/2026 cao 4 pt mỗi dòng - cộng vào khoảng hở trước mục III)
            ws.row_dimensions[rr].height = 1
            ws.row_dimensions[rr].hidden = True
            continue
        oo = ws.cell(rr, c1)
        oo._style = copy(kieu)
        # nối lại các dòng đã ngắt (Excel ngắt lại đúng chỗ cũ vì cùng bề rộng): đầu đoạn và dòng tràn của gạch đầu dòng
        # (TREO - đã có khoảng trắng thụt vào) thì xuống dòng cứng
        oo.value = ''.join(('\n' if dau and j else ' ' if j else '') + x for j, (x, dau) in enumerate(khoi[i])) or None
        al = copy(oo.alignment)
        al.wrap_text = True
        # nguồn gốc đất: ngang căn đều (NĐ 30/2020), dọc theo hồ sơ địa phương ban_in.nguon_goc - mặc định TRÊN (người dùng
        # 14/10/2026; 0.9.69 - 0.9.84: giữa) - mỗi dòng Excel cao vừa đúng số dòng chữ của nó
        al.horizontal, al.vertical = _can_nguon_goc()
        oo.alignment = al
        if c2 > c1:
            _gop_o(ws, rr, c1, rr, c2)
        ws.row_dimensions[rr].height = cao_doan_van(len(khoi[i]), co, cuoi=i == len(khoi) - 1)
    return chen


def vua_chu(ws, vt, do=None, them: float | None = None) -> None:
    """Dòng vt (từ vi_tri_cho) cao vừa đủ các dòng chữ (sau khi đã điền), chữ canh trên: sát dòng phía trên. Dùng cho
    'Dự án: …' (tên ngắn 1 dòng, dài tự xuống dòng); đường kẻ dưới tên dự án neo ở dòng kế tiếp nên kéo sát lên theo.
    them (mặc định DK_CACH + 3 pt): chỗ cho đường kẻ dưới chữ nằm trong dòng này, không lấn sang chữ của dòng kế."""
    if not vt:
        return
    if them is None:
        them = DK_CACH + 3
    r, c1, c2, _ = vt
    o = ws.cell(r, c1)
    ten, co, dam = _phong(o)
    dong = ngat_dong(str(o.value or ''), _rong_vung(ws, c1, c2), ten, co, dam, do)
    al = copy(o.alignment)
    al.wrap_text = True
    al.vertical = 'top'
    o.alignment = al
    ws.row_dimensions[r].height = cao_dong_chu(max(1, len(dong)), co) + them


# ---------------------------------------------------------------- tạo mẫu in từ file PABT Excel
_O_CT = {'E3': '{ten_dia_ban}, ngày       tháng        năm {nam}', 'A5': 'Dự án: {du_an}', 'C6': '{ma_ho}',
         'C8': '{ho_ten}', 'C9': '{cccd}', 'C10': '{dia_chi}', 'C11': '{dien_thoai}', 'A13': '{nguon_goc}'}


class LoiChuaRoMau(LoiIn):
    """File không có sheet IN_CHITIET / IN_BANGTONGHOP và không nhận ra theo nội dung: hỏi người dùng là mẫu loại nào."""


_CHO_CT = ('{ho_ten}', '{nguon_goc}', '{ma_ho}', '{cccd}', '{tai_dinh_cu}')
_CHO_BTH = ('BẢNG TỔNG HỢP', '{so_pa_tong}')


def _chu_sheet(ws, so_dong: int = 40) -> str:
    return '\n'.join(str(v) for r in ws.iter_rows(max_row=so_dong, max_col=30, values_only=True) for v in r
                     if isinstance(v, str))


def nhan_loai_mau(ws) -> str | None:
    """TEN_CT / TEN_BTH theo tên sheet, rồi theo nội dung (chỗ trống {ho_ten}… / chữ "BẢNG TỔNG HỢP"); không rõ: None."""
    if ws.title in (TEN_CT, TEN_BTH):
        return ws.title
    chu = _chu_sheet(ws)
    ct, bth = any(x in chu for x in _CHO_CT), any(x in chu.upper() for x in _CHO_BTH)
    return TEN_CT if ct and not bth else TEN_BTH if bth and not ct else None


def ten_mau_hop_le(ten: str) -> str:
    """Tên mẫu riêng dùng trong tên file: bỏ ký tự cấm, khoảng trắng gọn."""
    return re.sub(r'[\\/:*?"<>|]+', ' ', ' '.join(str(ten or '').split())).strip()[:40]


def tao_mau_tu_excel(file_excel, thu_muc, loai: str | None = None, ten_mau: str = '') -> list:
    """Lấy mẫu in từ file Excel. Trả danh sách file đã tạo.
    - File PABT Excel (.xlsm / .xlsx có sheet IN_CHITIET và / hoặc IN_BANGTONGHOP): sheet nào có thì lấy sheet đó (trước đây
      đòi đủ cả hai sheet -> file chỉ có một mẫu báo "không có sheet …").
    - File mẫu đã sửa sẵn (đã có chỗ trống {ho_ten}, {du_an}…, sheet tên bất kỳ): nhận loại theo tên sheet / nội dung, không
      rõ thì LoiChuaRoMau (gọi lại với loai=TEN_CT / TEN_BTH). Chép nguyên file (giữ đường kẻ, hình), chỉ đổi tên sheet.
    ten_mau: '' = thay mẫu chính; có tên = thêm mẫu riêng <TEN>__<tên>.xlsx (chọn khi In / Xuất). Mẫu cũ cùng tên được chép
    vào <thư mục mẫu>\\cu\\ trước khi ghi đè."""
    import shutil
    import zipfile
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    ten_mau = ten_mau_hop_le(ten_mau)
    duoi = f'{TACH_MAU}{ten_mau}' if ten_mau else ''
    wb0 = openpyxl.load_workbook(file_excel, read_only=True)
    try:
        ten_sheet = list(wb0.sheetnames)
        lay = {t: t for t in (TEN_CT, TEN_BTH) if t in ten_sheet}            # loại mẫu -> sheet trong file
        if not lay:
            hien = [s for s in ten_sheet if wb0[s].sheet_state == 'visible'] or ten_sheet
            for s in hien:
                k = nhan_loai_mau(wb0[s])
                if k and k not in lay:
                    lay[k] = s
            if loai in (TEN_CT, TEN_BTH):
                lay = {loai: lay.get(loai) or hien[0]}
            elif not lay:
                # không nhận ra loại: sheet rộng là bảng tổng hợp, sheet còn lại là phương án chi tiết — không chặn người dùng
                for s in hien:
                    try:
                        rong = wb0[s].max_column or 0
                    except Exception:
                        rong = 0
                    lay.setdefault(TEN_BTH if rong >= 12 else TEN_CT, s)
                if not lay and hien:
                    lay[TEN_CT] = hien[0]
        da_la_mau = {k: '{' in _chu_sheet(wb0[s], 60) and '}' in _chu_sheet(wb0[s], 60) for k, s in lay.items()}
    finally:
        wb0.close()
    tao = []
    for ten, s in lay.items():
        p = thu_muc / f'{ten}{duoi}.xlsx'
        if p.exists():                                  # giữ bản cũ (đổi mẫu nhầm thì lấy lại)
            cu = thu_muc / 'cu'
            cu.mkdir(exist_ok=True)
            shutil.copy2(p, cu / f'{p.stem}_{datetime.now():%Y%m%d_%H%M%S}.xlsx')
        if da_la_mau[ten] and len(ten_sheet) == 1 and str(file_excel).lower().endswith('.xlsx'):
            # mẫu đã sửa sẵn, một sheet: chép nguyên file (openpyxl làm mất hình vẽ / đường kẻ), đổi tên sheet trong workbook.xml
            tam = p.with_name(p.name + '.tmp')
            with zipfile.ZipFile(file_excel) as zi, zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as zo:
                for it in zi.infolist():
                    du = zi.read(it.filename)
                    if it.filename == 'xl/workbook.xml' and s != ten:
                        du = du.replace(f'name="{_xml_attr(s)}"'.encode('utf-8'), f'name="{ten}"'.encode('utf-8'), 1)
                    zo.writestr(it, du)
            os.replace(tam, p)
            tao.append(p)
            x = doc_duong_ke(p, ten)
            if x:
                (thu_muc / f'{p.stem}.duong_ke.xml').write_text(x, encoding='utf-8')
            continue
        wb = openpyxl.load_workbook(file_excel, keep_vba=False)
        for s2 in list(wb.sheetnames):
            if s2 != s:
                del wb[s2]
        for n in list(wb.defined_names):
            del wb.defined_names[n]
        ws = wb[s]
        ws.data_validations.dataValidation = []
        ws.title = ten
        if not da_la_mau[ten]:                          # sheet của file PABT Excel (công thức) -> chỗ trống {ten}
            (_lam_mau_ct if ten == TEN_CT else _lam_mau_bth)(ws)
        ws.sheet_view.selection[0].activeCell = 'A1'
        ws.sheet_view.selection[0].sqref = 'A1'
        wb.save(p)
        tao.append(p)
        x = doc_duong_ke(file_excel, s)
        dk = thu_muc / f'{p.stem}.duong_ke.xml'
        if x:
            dk.write_text(x, encoding='utf-8')
            tao.append(dk)
    return tao


def _xlsx_tu_pdf(p: Path) -> Path:
    """PDF không có lớp bảng: lấy chữ rồi dựng khung mẫu (chi tiết hoặc bảng tổng hợp) để vẫn in được."""
    chu = ''
    try:
        from pypdf import PdfReader
        chu = '\n'.join((page.extract_text() or '') for page in PdfReader(str(p)).pages[:6])
    except Exception:
        chu = ''
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = TEN_BTH if 'TỔNG HỢP' in chu.upper() else TEN_CT
    ws['A1'] = ((chu.split('\n') or [''])[0] or p.stem)[:120]
    ws['A5'] = 'Dự án: {du_an}'
    ws['C8'] = '{ho_ten}'
    ws['A13'] = '{nguon_goc}'
    ws['A17'] = 'STT'
    ws['A18'] = 'IV'
    ws['B18'] = 'Tái định cư: {tai_dinh_cu}'
    if ws.title == TEN_BTH:
        ws['A6'] = 'Dự án: {du_an}'
        ws.cell(DONG_DAU_BTH + 1, 1).value = 'TỔNG CỘNG'
    ra = p.with_name(p.stem + '_mau.xlsx')
    wb.save(ra)
    return ra


def _mau_thanh_xlsx(file) -> Path | None:
    p = Path(file)
    if not p.is_file():
        return None
    suf = p.suffix.lower()
    if suf in ('.xlsx', '.xlsm'):
        return p
    if suf == '.pdf':
        return _xlsx_tu_pdf(p)
    if suf in ('.xls', '.doc', '.docx'):
        try:
            from .nhap_don_gia import chuyen_office
            return chuyen_office(p)
        except Exception:
            return None
    return None


def _nhan_mau_mac_dinh(thu_muc, ten_mau: str = '') -> list:
    """Chép mẫu chuẩn đóng kèm — in vẫn chạy khi file người chọn không đọc được."""
    import shutil
    duoi = f'{TACH_MAU}{ten_mau_hop_le(ten_mau)}' if ten_mau else ''
    kq = []
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    for ten in (TEN_CT, TEN_BTH):
        try:
            src = file_mau(None, ten)
        except Exception:
            continue
        if not Path(src).is_file():
            continue
        dich = thu_muc / f'{ten}{duoi}.xlsx'
        shutil.copy2(src, dich)
        kq.append(dich)
    return kq


def nap_mau_in(file, thu_muc, ten_mau: str = '') -> tuple:
    """Đưa file Excel hoặc PDF vào mẫu in. Luôn trả (danh sách file, câu kết quả), không ném lỗi."""
    import shutil
    xoa_bo_nho_mau()
    file, thu_muc = Path(file), Path(thu_muc)
    try:
        thu_muc.mkdir(parents=True, exist_ok=True)
        (thu_muc / 'goc').mkdir(exist_ok=True)
        if file.is_file():
            shutil.copy2(file, thu_muc / 'goc' / file.name)
    except OSError:
        pass
    nguon = _mau_thanh_xlsx(file)
    if nguon is not None:
        try:
            ds = tao_mau_tu_excel(nguon, thu_muc, ten_mau=ten_mau)
            if ds:
                return ds, 'Đã phân tích cấu trúc file và đưa vào mẫu in.'
        except Exception:
            pass
    ds = _nhan_mau_mac_dinh(thu_muc, ten_mau)
    return ds, 'Đã lưu file gốc và dùng khung mẫu chuẩn của phần mềm để vẫn in được.'


def _xml_attr(s: str) -> str:
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def _lam_mau_ct(ws):
    dau = next((r for r in range(1, 300) if str(ws.cell(r, 1).value or '').strip().upper() == 'STT'), 17) + 1
    iv = next((r for r in range(dau, dau + 5000) if str(ws.cell(r, 1).value or '').strip() == 'IV'), None)
    if iv is None:
        iv = ws.max_row + 1
        ws.cell(iv, 1).value = 'IV'
        ws.cell(iv, 2).value = 'Tái định cư: {tai_dinh_cu}'
    # ô công thức / ô phụ -> chỗ trống {ten}
    for o, v in _O_CT.items():
        ws[o] = v
    for r in range(1, iv + 30):
        for c in range(9, ws.max_column + 1):
            if c != COT_KIND and ws.cell(r, c).value is not None:
                ws.cell(r, c).value = None
    # khung bảng chỉ giữ 1 dòng mẫu (định dạng), phần mềm chèn đủ dòng khi in
    for c in list(range(1, 9)) + [COT_KIND]:
        ws.cell(dau, c).value = None
    if iv - dau > 1:
        _doi_dong(ws, dau + 1, -(iv - dau - 1))
    iv = dau + 1
    ws.row_dimensions[dau].hidden = False
    ws.cell(iv, 2).value = 'Tái định cư: {tai_dinh_cu}'
    _vung_cf(ws, dau, dau)
    ws.print_area = f'A1:H{_dong_cuoi(ws, 8) + 1}'


def _dong_cuoi(ws, so_cot: int) -> int:
    for r in range(ws.max_row, 0, -1):
        if any(ws.cell(r, c).value not in (None, '', ' ') for c in range(1, so_cot + 1)):
            return r
    return 1


def _vung_cf(ws, dau: int, cuoi: int):
    """Định dạng có điều kiện của khung bảng (dòng tiêu đề mục / tổng in đậm) phủ đúng các dòng dữ liệu."""
    cf_moi = ConditionalFormattingList()
    for cf in ws.conditional_formatting:
        vung = []
        for cr in cf.sqref.ranges:
            cr = CellRange(cr.coord)
            if cr.min_row >= dau - 1 and cr.min_row <= dau + 200:
                cr = CellRange(min_col=cr.min_col, max_col=cr.max_col, min_row=dau, max_row=cuoi)
            vung.append(cr)
        _them_cf(cf_moi, cf, vung)
    ws.conditional_formatting = cf_moi


def _lam_mau_bth(ws):
    tong = next((r for r in range(DONG_DAU_BTH, DONG_DAU_BTH + 3000) if str(ws.cell(r, 1).value or '').strip() == 'TỔNG CỘNG'), None)
    if tong is None:
        tong = max(DONG_DAU_BTH + 1, ws.max_row + 1)
        ws.cell(tong, 1).value = 'TỔNG CỘNG'
    for m in list(ws.merged_cells.ranges):
        if DONG_DAU_BTH <= m.min_row < tong:
            ws.merged_cells.remove(m)
    for r in range(DONG_DAU_BTH, tong):
        for c in range(1, 26):
            o = ws.cell(r, c)
            if o.__class__.__name__ == 'MergedCell':
                ws._cells.pop((r, c), None)
                o = ws.cell(r, c)
            o.value = None
    if tong - DONG_DAU_BTH > 1:
        _doi_dong(ws, DONG_DAU_BTH + 1, -(tong - DONG_DAU_BTH - 1))
    ws['A6'] = 'Dự án: {du_an}'
    for row in ws.iter_rows(min_row=DONG_DAU_BTH + 1):
        for c in row:
            v = c.value
            if isinstance(v, str) and v.startswith('='):
                c.value = None                       # công thức tổng: phần mềm ghi lại theo số dòng thực tế
            elif isinstance(v, str):
                v = re.sub(r'UBND (xã|phường|thị trấn) [^0-9%]+? (\d+%)', r'UBND {cap_dia_ban_thuong} {ten_dia_ban} \2', v)
                v = re.sub(r'^[^,]+, ngày (…|\.)', r'{ten_dia_ban}, ngày \1', v)
                v = re.sub(r'năm 20\d\d', 'năm {nam}', v)
                c.value = v
    ws['A7'] = re.sub(r'năm 20\d\d', 'năm {nam}', str(ws['A7'].value or ''))
    ws.print_area = f'A1:Y{_dong_cuoi(ws, 25) + 1}'


# ---------------------------------------------------------------- dữ liệu chung
def _hai_dong(s: str) -> str:
    """'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT THÀNH PHỐ ĐỒNG NAI' -> xuống dòng trước 'THÀNH PHỐ' / 'TỈNH' (tiêu đề cơ quan 2 dòng)."""
    return re.sub(r'\s+((THÀNH PHỐ|TỈNH|HUYỆN|QUẬN|THỊ XÃ) .+)$', r'\n\1', s) if len(s) > 30 else s


def _thong_tin_du_an(con) -> dict:
    from .to_chuc import MAC_DINH
    goc = con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
    da = {k: goc[k] for k in goc.keys()}
    for k, v in MAC_DINH.items():                  # ô thông tin đơn vị còn trống: dùng thông tin tổ chức mặc định
        if not (da.get(k) or '').strip():
            da[k] = v
    cap = (da['cap_dia_ban'] or '').strip()
    return dict(du_an=' '.join(str(da['ten'] or '').split()), ten_day_du=da['ten_day_du'] or '', cap_dia_ban=cap,
                cap_dia_ban_thuong=cap.lower(), ten_dia_ban=(da['ten_dia_ban'] or '').strip(),
                nam=da['nam'] or date.today().year, so_phuong_an=da['so_phuong_an'] or '', don_vi_lap=da['don_vi_lap'] or '',
                don_vi_cap_tren=da['don_vi_cap_tren'] or '', DON_VI_CAP_TREN=(da['don_vi_cap_tren'] or '').upper(),
                DON_VI_CAP_TREN_2DONG=_hai_dong((da['don_vi_cap_tren'] or '').upper()),
                DON_VI_TIEU_DE=(da['don_vi_tieu_de'] or da['don_vi_lap'] or '').upper(),
                DON_VI_LAP=(da['don_vi_lap'] or '').upper(), ky_hieu_so=da['ky_hieu_so'] or '', nguoi_lap=da['nguoi_lap'] or '',
                nguoi_kiem_tra=da['nguoi_kiem_tra'] or '', nguoi_ky=da['nguoi_ky'] or '',
                CHUC_VU_KY=(da['chuc_vu_ky'] or '').upper())


def ky_hieu_cua_ho(con, ma_ho: int, mac_dinh: str = '') -> str:
    """Ký hiệu số phương án của hộ: theo đợt trình của hộ (v15), đợt chưa đặt / hộ chưa vào đợt -> mac_dinh (của dự án)."""
    try:
        r = con.execute('''SELECT d.ky_hieu_so FROM ho h JOIN dot_trinh d ON d.id = h.dot_id WHERE h.ma_ho = ?''',
                        (ma_ho,)).fetchone()
    except sqlite3.OperationalError:                     # file chỉ xem phiên bản cũ (< v15)
        return mac_dinh
    return ((r[0] or '').strip() if r else '') or mac_dinh


def ghi_chu_in(con, ma, gc) -> str:
    """Ghi chú in ra phương án: bỏ các câu giải thích tự động (giống bản Excel)."""
    s = str(gc or '').strip()
    if not s or s.startswith(('SL = ', 'ĐG = ', 'T = đ')) or 'chưa có dòng đất nông nghiệp' in s:
        return ''
    if ma:
        r = con.execute('SELECT cach_tinh FROM dm_hotro WHERE ma = ?', (ma,)).fetchone()
        if r and s == (r['cach_tinh'] or ''):
            return ''
    return s


def dong_chi_tiet(con, ma_ho: int, bc: BoiCanh | None = None, pa=None) -> tuple:
    """Các dòng bảng in của một hộ: (danh sách (loại, [A..H]), KetQuaHo). Loại: H mục, I dòng, R thưởng, T tổng.
    pa: phương án đang soạn trong bộ nhớ (BoSoan.pa - xem trước khi chưa lưu); None = đọc từ CSDL."""
    bc = bc or BoiCanh.tu(con)
    pa = pa if pa is not None else doc_phuong_an(con, ma_ho)
    kq = tinh_pa(pa, bc)
    dong = []
    # 1. đất
    d1 = [d for d in kq.dong if d.muc == 1]
    dong.append(['H', ['1', 'Bồi thường đất', None, None, None, None, None, None]])
    hdr = dong[-1][1]
    if d1:
        for d in d1:
            dong.append(['I', [d.stt, d.ten, 'm²', d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, '', d.ghi_chu)]])
        hdr[3] = sum((d.so_luong for d in d1), KHONG)
        hdr[6] = kq.muc[1]
    else:
        # hộ chưa lập giá đất: liệt kê các thửa thu hồi theo hồ sơ kiểm kê; dòng đầu ghi pháp lý của hộ (vd "Đất do … quản lý,
        # không tính toán bồi thường về đất…" khi nhập phương án chi tiết từ Excel)
        k = 0
        tong_dt = KHONG
        r = con.execute('SELECT phap_ly FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
        phap_ly = ' '.join(str(r['phap_ly'] or '').split()) if r else ''
        for t in bc.thua_cua(ma_ho):
            k += 1
            mo_ta = nghiep_vu.mo_ta_thua(t['so_to'], t['so_thua'], t['loai_dat'], bc.cap_dia_ban, bc.ten_dia_ban, t['vi_tri'])
            dong.append(['I', [f'1.{k}', mo_ta, 'm²', D(t['dt_thu_hoi']), KHONG, D(1), KHONG, phap_ly if k == 1 else '']])
            tong_dt += D(t['dt_thu_hoi'])
        hdr[3] = tong_dt
        hdr[6] = KHONG
    if kq.muc[1] == 0:
        # không có tiền bồi thường đất (người dùng 12/10/2026): bỏ số lượng, đơn giá, tỷ lệ ở các dòng đất (thành tiền 0 giữ)
        for x in dong[1:]:
            x[1][3] = x[1][4] = x[1][5] = None
        hdr[3] = None
    # 2 nhà, 3 cây trồng, 4 vật nuôi (0.9.20: mục riêng, in dưới cây trồng - mã bên trong MUC_VN)
    for muc in (2, 3, nghiep_vu.MUC_VN):
        dong.append(['H', [str(nghiep_vu.so_muc(muc)), nghiep_vu.TEN_MUC[muc], None, None, None, None, kq.muc[muc], None]])
        for d in (x for x in kq.dong if x.muc == muc):
            dong.append(['I', [d.stt, d.ten, d.dvt, d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, d.ma, d.ghi_chu)]])
    # 5 các chính sách hỗ trợ: dòng có cách tính in gộp ô ĐVT..tỷ lệ; hỗ trợ đào tạo nhập theo từng thửa có dòng tên chính sách
    # đứng đầu nhóm
    from .chinh_sach import ten_ngan
    s4 = nghiep_vu.so_muc(4)
    dong.append(['H', [str(s4), nghiep_vu.TEN_MUC[4], None, None, None, None, kq.muc[4], None]])
    ds4 = [x for x in kq.dong if x.muc == 4]
    k = i = 0
    while i < len(ds4):
        d = ds4[i]
        k += 1
        if d.ma in ('CS9', 'CS10') and d.ten.startswith('Thửa đất'):
            j = i
            while j < len(ds4) and ds4[j].ma == d.ma and ds4[j].ten.startswith('Thửa đất'):
                j += 1
            nhom = ds4[i:j]
            ten = ten_ngan((bc.hotro.get(d.ma) or {}).get('ten', ''), d.ma) or 'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm'
            # dòng tên chính sách chỉ ghi tên + căn cứ; diện tích, đơn giá, tỷ lệ, thành tiền ở các dòng thửa bên dưới (người dùng
            # 15/10/2026: trước đây dòng tên lặp lại diện tích + thành tiền của dòng thửa - một thửa thì hai ô trùng số)
            dong.append(['I', [f'{s4}.{k}', ten, None, None, None, None, None, ghi_chu_in(con, d.ma, d.ghi_chu)]])
            for x in nhom:
                dong.append(['I', ['-', x.ten, x.dvt, x.so_luong, x.don_gia, x.ty_le, x.thanh_tien, None]])
            i = j
            continue
        gt = [f'{s4}.{k}', d.ten, d.dvt, d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, d.ma, d.ghi_chu)]
        dong.append(['I', gt, d.cach_tinh] if d.cach_tinh else ['I', gt])
        i += 1
    # 6. thưởng (chỉ khi có bồi thường về đất): chỉ tên + thành tiền - bỏ ĐVT, số lượng, đơn giá, tỷ lệ (người dùng 15/10/2026: tên
    # gộp ô sang hết các cột đó trong lap_chi_tiet; trước đây "1,0 | 20.000.000 | 100%"); thành tiền in đậm
    dong.append(['R', [str(nghiep_vu.so_muc(5)), nghiep_vu.TEN_MUC[5], None, None, None, None, kq.muc[5], None]])
    dong.append(['T', [None, 'TỔNG CỘNG', None, None, None, None, kq.tong, None]])
    return dong, kq


def _thong_tin_ho(con, ma_ho: int, da: dict, che: bool | None = None) -> dict:
    h = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    ten = ' '.join(str(h['ho_ten'] or '').split())
    if ' là ' in ten:
        ten = ten.split(' là ')[0].strip()
    cccd = (h['so_cccd'] or '').strip()
    if (h['ngay_cap'] or '').strip() and h['ngay_cap'] != '0':
        cccd += f' - Ngày cấp: {h["ngay_cap"].strip()}'
    if (h['noi_cap'] or '').strip():
        cccd += f' - Nơi cấp: {h["noi_cap"].strip()}'
    from .an_toan import can_che_cccd, che_cccd
    if can_che_cccd(con) if che is None else che:   # bản niêm yết công khai: che số CCCD, bỏ ngày / nơi cấp (NĐ 13/2023)
        cccd = che_cccd((h['so_cccd'] or '').strip())
    from .ho_so import chuan_nguon_goc
    ng = []                                     # nguồn gốc các thửa (bỏ trùng, giữ thứ tự): mỗi nội dung một đoạn
    for r in con.execute("SELECT nguon_goc FROM thua WHERE ma_ho = ? AND TRIM(nguon_goc) <> '' ORDER BY thu_tu, ma_thua",
                         (ma_ho,)):
        chu = chuan_nguon_goc(r['nguon_goc'])
        if chu and chu not in ng:
            ng.append(chu)
    from .lap_pa import cau_tai_dinh_cu
    tdc = cau_tai_dinh_cu(h['tai_dinh_cu']) or \
        f'Sau khi UBND {da["cap_dia_ban_thuong"] or "xã, phường"} xác nhận điều kiện tái định cư (nếu có).'
    dt = (h['dien_thoai'] or '').strip()
    k = h.keys()
    return dict(ma_ho=ma_ho, ho_ten=ten, cccd=cccd.strip(' -'), dia_chi=(h['dia_chi'] or '').strip(),
                dien_thoai='' if dt == '0' else dt, nguon_goc='\n'.join(ng), tai_dinh_cu=tdc,
                so_pa=(h['so_pa'] or '').strip() if 'so_pa' in k else '', ngay_pa=(h['ngay_pa'] or '') if 'ngay_pa' in k else '')


# ---------------------------------------------------------------- phương án chi tiết (A4 dọc)
TIEU_DE_MUC_II = 'II. Thông tin vị trí, nguồn gốc đất'       # 0.9.87: tiêu đề mục II thống nhất (mẫu cũ: "II. Thông tin nguồn gốc đất:")
NHAN_TO_CHUC = 'Tổ chức:'                                  # chủ sử dụng là tổ chức: thay nhãn "Họ và tên:"


def chuan_tieu_de_muc_ii(ws, den_dong: int) -> int:
    """Ô tiêu đề "II. … nguồn gốc …" phía trên bảng -> TIEU_DE_MUC_II. Trả số ô đã đổi."""
    from .lap_pa import bo_dau
    n = 0
    for o in list(_o_chu(ws, den_dong)):
        chu = o.value.strip()
        s = bo_dau(chu).lower()
        if s.startswith('ii.') and 'nguon goc' in s and chu != TIEU_DE_MUC_II:
            o.value = TIEU_DE_MUC_II
            n += 1
    return n


def dat_nhan_chu_su_dung(ws, den_dong: int, to_chuc: bool) -> int:
    """Nhãn "Họ và tên:" (mục I) -> "Tổ chức:" khi chủ sử dụng là tổ chức (ho_so.la_to_chuc); tổ chức không có CCCD: ẨN dòng "Số
    CCCD:" (người dùng 16/10/2026 - ẩn, không xóa dòng: vị trí các ô phía dưới giữ nguyên). Trả số ô đã đổi."""
    if not to_chuc:
        return 0
    n = 0
    for o in list(_o_chu(ws, den_dong)):
        k = o.value.strip().rstrip(':').strip().lower()
        if k == 'họ và tên':
            o.value = NHAN_TO_CHUC
            n += 1
        elif k in ('số cccd', 'cccd', 'số cccd/cmnd', 'số cmnd'):
            ws.row_dimensions[o.row].hidden = True
    return n


DIA_DANH_NGAY_MAC_DINH = 'Trị An'
_RE_DONG_NGAY = re.compile(r'^\s*(\{ten_dia_ban\}|[^,{}\n]{1,40}),(\s*ngày)')
_RE_NGAY_TRONG = re.compile(r'ngày[\s….,_]*tháng[\s….,_]*năm')


def chuan_dong_ngay(ws, den_dong: int | None = None) -> int:
    """Dòng "<địa danh>, ngày … tháng … năm 2026" (người dùng 16/10/2026): địa danh CỐ ĐỊNH theo nơi đặt cơ quan (hồ sơ địa phương
    `ban_in.dia_danh_ngay`, mặc định "Trị An") - không theo xã của dự án; chỗ chưa có ngày ghi dấu chấm "ngày ...... tháng ..... năm".
    Gọi SAU dien_so_ngay (ngày đã điền giữ nguyên), TRƯỚC _thay_cho_trong. Trả số ô đã đổi."""
    from . import dia_phuong
    dia_danh = str(dia_phuong.lay('ban_in.dia_danh_ngay', DIA_DANH_NGAY_MAC_DINH) or '').strip()
    n = 0
    for o in list(_o_chu(ws, den_dong)):
        v = o.value
        if 'ngày' not in v or 'năm' not in v or not _RE_DONG_NGAY.match(v):
            continue
        s = _RE_DONG_NGAY.sub(lambda m: f'{dia_danh},{m.group(2)}', v, count=1) if dia_danh else v
        s = _RE_NGAY_TRONG.sub('ngày ...... tháng ..... năm', s)
        if s != v:
            o.value = s
            n += 1
    return n


def viet_hoa_du_an(ws, den_dong: int | None = None) -> int:
    """Tiêu đề phương án chi tiết: "Dự án: <tên>" -> "DỰ ÁN <tên>" (viết hoa, bỏ dấu hai chấm - người dùng 16/10/2026)."""
    n = 0
    for o in list(_o_chu(ws, den_dong)):
        m = re.match(r'^\s*dự án\s*:\s*', o.value, re.I)
        if m:
            o.value = 'DỰ ÁN ' + o.value[m.end():]
            n += 1
    return n


def gop_ghi_chu_dat(ws, dong: list, dau: int, cot_gc: int, toi_da: int | None = None) -> list:
    """Mục 1 (đất): gộp dọc ô Ghi chú của các dòng đất LIỀN NHAU cùng nội dung (khác trống) - ghi chú một lần, căn giữa dọc.
    dong: các dòng của dong_chi_tiet (dòng i ở hàng dau + i). Gộp bằng _gop_o (không ws.merge_cells - O(n²)). Trả [(r1, r2)].
    toi_da (mặc định GHI_CHU_TOI_DA = 12): nhóm dài hơn thì mở vùng gộp mới (16/10/2026 - tổ chức 15-180 thửa cùng ghi chú: một ô
    gộp dài hơn một trang giấy); ngat_trang_ct còn tách vùng gộp ở ranh trang."""
    toi_da = toi_da or GHI_CHU_TOI_DA
    kq = []
    i = 1 if dong and dong[0][0] == 'H' else 0               # bỏ dòng tiêu đề mục 1
    nhom = []                                               # [(hàng, chữ)] của nhóm đang xét

    def dong_nhom():
        if len(nhom) > 1:
            r1, r2 = nhom[0][0], nhom[-1][0]
            o = ws.cell(r1, cot_gc)
            o.alignment = Alignment(horizontal=o.alignment.horizontal or 'center', vertical='center', wrap_text=True)
            for r in range(r1 + 1, r2 + 1):
                ws.cell(r, cot_gc).value = None
            _gop_o(ws, r1, cot_gc, r2, cot_gc)
            kq.append((r1, r2))
        nhom.clear()

    while i < len(dong) and dong[i][0] != 'H':
        r = dau + i
        chu = ' '.join(str(ws.cell(r, cot_gc).value or '').split())
        if dong[i][0] != 'I' or not chu or (nhom and nhom[-1][1] != chu):
            dong_nhom()
        if dong[i][0] == 'I' and chu:
            if len(nhom) >= toi_da:
                dong_nhom()
            nhom.append((r, chu))
        i += 1
    dong_nhom()
    return kq


# đệm mẫu in trong RAM (0.9.87): bytes của file mẫu theo (đường dẫn, mtime_ns, cỡ) - in hàng loạt không đọc lại đĩa mỗi hộ (thư mục
# mẫu trên ổ mạng / %APPDATA% bị diệt virus quét). KHÔNG giữ Workbook đã nạp (pickle / deepcopy làm hỏng openpyxl - 0.9.22, 0.9.24):
# mỗi hộ vẫn load_workbook từ BytesIO, workbook độc lập.
_BO_NHO_MAU = {}


def nap_mau_bytes(duong_dan) -> bytes:
    p = Path(duong_dan)
    st = p.stat()
    k = str(p.resolve())
    cu = _BO_NHO_MAU.get(k)
    if cu is not None and cu[0] == (st.st_mtime_ns, st.st_size):
        return cu[1]
    du_lieu = p.read_bytes()
    if len(_BO_NHO_MAU) > 16:
        _BO_NHO_MAU.clear()
    _BO_NHO_MAU[k] = ((st.st_mtime_ns, st.st_size), du_lieu)
    return du_lieu


def xoa_bo_nho_mau() -> None:
    """Gọi khi mẫu in đổi (cập nhật mẫu in, cài gói .pabtcfg) - khóa mtime / cỡ đã tự nhận ra, gọi thêm cho chắc."""
    _BO_NHO_MAU.clear()


def mo_mau(duong_dan):
    """openpyxl.load_workbook(mẫu) qua đệm RAM."""
    import io
    return openpyxl.load_workbook(io.BytesIO(nap_mau_bytes(duong_dan)))


def lap_chi_tiet(con, ma_ho: int, file_ra, mau: Path | None = None, bc: BoiCanh | None = None,
                 du_thao: bool | None = None, pa=None, che_cccd: bool | None = None) -> Path:
    """Điền mẫu IN_CHITIET cho một hộ, lưu thành file .xlsx. Trả đường dẫn file. mau: thư mục mẫu hoặc file mẫu riêng.
    du_thao: True = bản DỰ THẢO (giữ / thêm chữ DỰ THẢO, chưa in số phương án), False = bản chính thức (xóa chữ DỰ THẢO của
    mẫu), None = theo tên file mẫu như trước 0.9.82 (la_mau_du_thao). pa: phương án trong bộ nhớ (xem trước bản đang soạn);
    che_cccd: che số CCCD (None = bản dự thảo che theo hồ sơ địa phương ban_in.che_cccd_ban_du_thao - Nghị định 13/2023/NĐ-CP,
    niêm yết công khai; bản chính thức theo cài đặt của dự án). Cột bảng: hồ sơ địa phương mau_in.IN_CHITIET (_cot_ct)."""
    from . import dia_phuong
    mau = file_mau(mau, TEN_CT)
    du_thao = la_mau_du_thao(mau) if du_thao is None else bool(du_thao)
    if che_cccd is None and du_thao and dia_phuong.lay('ban_in.che_cccd_ban_du_thao', True):
        che_cccd = True
    duong_ke = duong_ke_cua_mau(mau, TEN_CT)
    wb = mo_mau(mau)
    ws = wb.worksheets[0]
    da = _thong_tin_du_an(con)
    da['ky_hieu_so'] = ky_hieu_cua_ho(con, ma_ho, da['ky_hieu_so'])       # 0.9.72: theo đợt trình của hộ
    dong, kq = dong_chi_tiet(con, ma_ho, bc, pa)
    ttho = _thong_tin_ho(con, ma_ho, da, che_cccd)
    do = _ham_do_chu()
    dat_doan_van(ws, '{nguon_goc}', ttho['nguon_goc'], do)     # trước khi tìm dòng STT: có thể chèn thêm dòng
    vt_du_an = vi_tri_cho(ws, '{du_an}', 20)
    vt_dk = [(vi_tri_cho(ws, '{DON_VI_TIEU_DE}', 8), 1.0), (o_tieu_ngu(ws), 1.0), (vt_du_an, 1.0)]
    cot, cot_loai, chu_dau = _cot_ct()
    k_stt, k_ten, k_dvt, k_sl, k_dg, k_tl, k_tt, k_gc = cot
    cuoi_bang = max(cot)                                # cột cuối của bảng (H)
    dau = next((r for r in range(1, 300) if str(ws.cell(r, k_stt).value or '').strip().upper() == chu_dau), 17) + 1
    n = len(dong)
    # mục III (người dùng 14/10/2026): mọi cột STT … Ghi chú căn giữa theo chiều dọc - đặt ở dòng mẫu trước khi chép sang các dòng
    for c in range(1, cuoi_bang + 1):
        _can_giua_doc(ws.cell(dau, c))
    _doi_dong(ws, dau + 1, n - 1)
    for r in range(dau + 1, dau + n):
        _chep_kieu_dong(ws, dau, r, cuoi_bang)
        ws.cell(r, cot_loai)._style = copy(ws.cell(dau, cot_loai)._style)
    co = ws.cell(dau, k_ten).font.sz or 14
    px = _px_cot(ws, cuoi_bang + 1)

    def rong(c1: int, c2: int) -> float:                # bề rộng chỗ viết chữ (pt) của cột c1..c2
        return sum(px[c1 - 1:c2]) * 0.75 - 6

    # hàng tiêu đề cột (STT, Tên tài sản, ĐVT…): 28 pt; tiêu đề nhiều dòng ("Thành tiền\n(đồng)") cao theo số dòng chữ
    if dau > 1:
        so_td = 1
        for c in range(1, cuoi_bang + 1):
            o = ws.cell(dau - 1, c)
            _can_giua_doc(o)
            if isinstance(o.value, str) and o.value.strip():
                ten, co_td, dam = _phong(o)
                so_td = max(so_td, so_dong_o(o.value, rong(c, c), ten, co_td, dam, do))
        ws.row_dimensions[dau - 1].height = CAO_TIEU_DE_BANG if so_td <= 1 else max(CAO_TIEU_DE_BANG, cao_dong_bang(so_td, co))
    ten_b, _, _ = _phong(ws.cell(dau, k_ten))
    so_khac, so_gc = {}, {}                                      # hàng -> số dòng chữ (cột khác / cột ghi chú)
    so_dong_r = {}                                                # hàng -> số dòng chữ của cả dòng (nén khít không cắt chữ)
    muc_sl = None
    for i, x in enumerate(dong):
        loai, gt = x[0], x[1]
        cach_tinh = x[2] if len(x) > 2 else ''
        r = dau + i
        if loai == 'H':                                 # tiêu đề mục: số lượng các dòng dưới theo mục (tài sản *,00, khác *,0)
            muc_sl = 2 if str(gt[0]) == str(nghiep_vu.so_muc(2)) else None
        for c, v in zip(cot, gt):
            o = ws.cell(r, c)
            if c == k_stt:
                o.value = None if v is None else str(v)
            elif c in (k_sl, k_dg, k_tl, k_tt):
                o.value = _so(v)
                if c == k_sl and o.value is not None:   # số lượng kiểu kế toán: tài sản 46,00 / 35,80, khác 16,0 / 0,0325
                    o.number_format = dinh_dang_so_luong(muc_sl)
            else:
                o.value = v if v not in ('',) else None
        ws.cell(r, cot_loai).value = loai
        if loai == 'R':                                 # thành tiền thưởng bàn giao mặt bằng in đậm
            ot = ws.cell(r, k_tt)
            f = copy(ot.font)
            f.b = True
            ot.font = f
        gop_ten = None
        if loai == 'T':
            # TỔNG CỘNG: gộp từ cột STT tới cột Tỷ lệ, căn giữa (người dùng 15/10/2026) - chỉ khi các cột liền nhau. Thưởng ('R'): KHÔNG
            # gộp nữa (người dùng 16/10/2026) - tên xuống dòng trong cột Tên như các mục 2-5, ô ĐVT / SL / ĐG / tỷ lệ trống có kẻ ô
            c1 = k_stt
            c2 = max(k_dvt, k_sl, k_dg, k_tl)
            if c2 > c1 and set(range(c1, c2 + 1)) <= {k_stt, k_ten, k_dvt, k_sl, k_dg, k_tl}:
                chu_gop = ws.cell(r, k_ten).value
                for c in range(c1, c2 + 1):
                    ws.cell(r, c).value = None
                o1 = ws.cell(r, c1)
                o1.value = chu_gop
                o1.alignment = Alignment(horizontal='left' if loai == 'R' else 'center', vertical='center', wrap_text=True)
                if loai == 'T':
                    f = copy(o1.font)
                    f.b = True
                    o1.font = f
                _gop_o(ws, r, c1, r, c2)
                gop_ten = (c1, c2)
        # số dòng chữ đo theo phông thật (Excel ngắt dòng theo bề rộng cột): dòng mục / tổng in đậm (định dạng có điều kiện)
        dam = loai != 'I'
        so = 1
        for c in (k_stt, k_ten, k_dvt, k_gc):
            o = ws.cell(r, c)
            if gop_ten is not None and gop_ten[0] <= c <= gop_ten[1]:
                if c == gop_ten[0]:                     # ô gộp: đo trên bề rộng cả vùng
                    so = max(so, so_dong_o(o.value, rong(*gop_ten), ten_b, float(o.font.sz or co), True, do))
                continue
            n_o = so_dong_o(o.value, rong(c, c), ten_b, float(o.font.sz or co), dam or bool(o.font.b), do)
            if c == k_gc:
                so_gc[r] = n_o
            else:
                so_khac[r] = max(so_khac.get(r, 1), n_o)
            so = max(so, n_o)
        if cach_tinh:                                   # cách tính in gộp ô ĐVT..tỷ lệ (thay số lượng, đơn giá)
            c1, c2 = min(k_dvt, k_tl), max(k_dvt, k_tl)
            for c in range(c1 + 1, c2 + 1):
                ws.cell(r, c).value = None
            ws.cell(r, c1).value = cach_tinh
            ws.cell(r, c1).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            _gop_o(ws, r, c1, r, c2)
            n_ct = so_dong_o(cach_tinh, rong(c1, c2), ten_b, co, dam, do)
            so_khac[r] = max(so_khac.get(r, 1), n_ct)
            so = max(so, n_ct)
        ws.row_dimensions[r].height = cao_dong_bang(so, co)
        so_dong_r[r] = so
    # 0.9.87: ghi chú đất trùng nhau gộp một ô. Chiều cao: mỗi dòng theo chữ các cột khác, ô ghi chú gộp chỉ cần đủ cao CẢ KHỐI -
    # trước đây mỗi dòng vẫn cao theo chữ ghi chú lặp lại (3 dòng cùng ghi chú 4 dòng chữ = khối cao 12 dòng chữ)
    dong_chu = dong_chu_bang(co)
    nhom_gc = gop_ghi_chu_dat(ws, dong, dau, k_gc)
    san_khoi = [(r1, r2, so_gc.get(r1, 1) * dong_chu + DEM_DONG - NEN_DEM) for r1, r2 in nhom_gc]
    trong_nhom = {r for r1, r2 in nhom_gc for r in range(r1, r2 + 1)}
    san = {r: max(CAO_NEN_TOI_THIEU, (so_khac.get(r, 1) if r in trong_nhom else s) * dong_chu + DEM_DONG - NEN_DEM)
           for r, s in so_dong_r.items()}
    for r1, r2 in nhom_gc:
        cao = [cao_dong_bang(so_khac.get(r, 1), co) for r in range(r1, r2 + 1)]
        thieu = cao_dong_bang(so_gc.get(r1, 1), co) - sum(cao)
        if thieu > 0:
            cao = [h + thieu / len(cao) for h in cao]
        for r, h in zip(range(r1, r2 + 1), cao):
            ws.row_dimensions[r].height = min(409, h)
    from .ho_so import la_to_chuc
    dat_nhan_chu_su_dung(ws, dau - 1, la_to_chuc(ttho['ho_ten']))
    viet_hoa_du_an(ws, dau - 1)
    chuan_tieu_de_muc_ii(ws, dau - 1)
    _vung_cf(ws, dau, dau + n - 1)
    if du_thao:                                                  # dự thảo chưa có số phương án chính thức (để trống chỗ số / ngày)
        ttho['so_pa'], ttho['ngay_pa'] = '', ''
    gia_tri = dict(da, **ttho)
    dien_so_ngay(ws, ttho['so_pa'], ttho['ngay_pa'], 'Số:', dau - 1)      # số / ngày PA chi tiết (đợt trình) vào chỗ chừa trống
    chuan_dong_ngay(ws, dau - 1)                                 # "Trị An, ngày ...... tháng ..... năm 2026"
    can_khoi_ky(ws)                                              # họ tên người ký căn giữa dưới chức danh
    _thay_cho_trong(ws, gia_tri)
    ap_che_do_du_thao(ws, du_thao, TEN_CT)                       # dự thảo: giữ / thêm chữ DỰ THẢO; chính thức: xóa
    vua_chu(ws, vt_du_an, do)
    for r in range(dau + n, min(dau + n + 6, ws.max_row + 1)):          # dòng IV: "Tái định cư: …" (mẫu cũ ghi "Phương án …")
        o = ws.cell(r, k_ten)
        if isinstance(o.value, str) and o.value.startswith('Phương án tái định cư:'):
            o.value = 'Tái định cư:' + o.value[len('Phương án tái định cư:'):]
        if isinstance(o.value, str) and len(o.value) > 40:
            _gian_dong(ws, r, k_ten, co)
        if isinstance(o.value, str) and o.value.startswith(NHAN_TDC):
            _nhan_dam(o, NHAN_TDC)
    from openpyxl.utils import get_column_letter
    cl = get_column_letter(cuoi_bang)
    ws.print_area = f'A1:{cl}{_dong_cuoi(ws, cuoi_bang) + 1}'
    wb.defined_names[TEN_CAO] = DefinedName(TEN_CAO, attr_text=f"'{ws.title}'!$A${dau}:${cl}${dau + n - 1}")
    # dàn trang (16/10/2026): lề, tỷ lệ vừa ngang, cụm không tách, nén khít / giãn cân đối, ngắt trang tay, tách ô gộp ghi chú
    ngat_trang_ct(ws, dau, [x[0] for x in dong], cuoi_bang, san, san_khoi, nhom_gc, k_gc, co)
    wb.calculation.fullCalcOnLoad = True
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    dk = _dat_duong_ke(ws, vt_dk, duong_ke)       # sát chân chữ, căn giữa từng dòng (tên đơn vị, tiêu ngữ, dự án)
    wb.save(file_ra)
    chen_duong_ke(file_ra, duong_ke, dk)          # đường kẻ của mẫu (openpyxl không giữ hình vẽ)
    return file_ra


# ---------------------------------------------------------------- bảng tổng hợp (A3 ngang)
def ho_co_phuong_an(con) -> list:
    """Mọi hộ có dòng phương án (kể cả phương án phần mềm tự lập chưa soát)."""
    return [k.ma_ho for k in nghiep_vu.tinh_tat_ca(con) if k.co_phuong_an]


LAP = {'da_lap': 'Đã lập phương án', 'tu_lap': 'Tự lập, chưa soát', 'chua': 'Chưa có phương án'}
# phan_loai_lap chuyển sang lap_pa (màn hình chính gọi mỗi lần tải lại mà không phải nạp openpyxl); giữ tên cũ ở đây
from .lap_pa import phan_loai_lap  # noqa: E402,F401


def gop_pdf(ds: list, file_ra) -> Path:
    """Gộp các file PDF (theo thứ tự) thành một file."""
    from pypdf import PdfWriter
    w = PdfWriter()
    for f in ds:
        w.append(str(f))
    file_ra = Path(file_ra)
    with open(file_ra, 'wb') as f:
        w.write(f)
    return file_ra


_RE_THEO_CAN_CU = re.compile(r'\s*\(theo (?:Quyết định|QĐ|Nghị quyết|NQ)[^)]*\)', re.I)


def bo_can_cu_kinh_phi(chu: str) -> str:
    """Dòng "Kinh phí đảm bảo … 2,5%:" của bảng tổng hợp: bỏ "(theo Quyết định số 08/2025/QĐ-UBND …)" (người dùng 16/10/2026)."""
    return _RE_THEO_CAN_CU.sub('', chu)


def _chu_so_excel(v, fmt: str) -> str:
    """Số như Excel hiện theo định dạng ô (dấu chấm ngăn nghìn, phẩy thập phân; số chữ số lẻ theo phần đầu định dạng)."""
    phan = (fmt or '').split(';')[0]
    le = len(phan.split('.')[1].rstrip('#').replace('#', '')) if '.' in phan else (0 if isinstance(v, int) else 1)
    le = min(le, 4)
    s = f'{abs(v):,.{le}f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    return ('-' if v < 0 else '') + s


def vua_cot_so_bth(ws, d0: int, tong: int, n_cot: int, do=None) -> dict:
    """Cột số của bảng tổng hợp đủ rộng cho số dài nhất - kể cả dòng TỔNG CỘNG (=SUM, chữ đậm): trước đây cột hẹp của mẫu hiện
    "#####" (người dùng 16/10/2026). Chỉ NỚI, không thu hẹp. Trả {cột: độ rộng mới}."""
    from openpyxl.utils import get_column_letter
    mdw = _mdw(ws.parent)
    kq = {}
    for c in range(1, n_cot + 1):
        cd = ws.column_dimensions.get(get_column_letter(c))
        if cd is None or cd.hidden or (cd.min and cd.max and cd.min != cd.max):
            continue
        o_co = ws._cells                                # đọc thẳng ô đã có (ws.cell tạo ô rỗng + chậm khi 3.000 hộ)
        so = [v for v in (getattr(o_co.get((r, c)), 'value', None) for r in range(d0, tong))
              if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not so:
            continue
        fmt = ws.cell(d0, c).number_format
        # chữ số Times New Roman cùng bề rộng: chuỗi dài nhất là của số lớn nhất / âm nhỏ nhất - chỉ đo các số đó (trước: đo mọi ô,
        # bảng tổng hợp 3.000 hộ chậm thêm ~1 s)
        ds = [(_chu_so_excel(v, fmt), ws.cell(d0, c)) for v in {max(so), min(so)}] + \
            [(_chu_so_excel(sum(so), fmt), ws.cell(tong, c))]
        can_pt = 0.0
        for chu, o in ds:
            ten, co, dam = _phong(o)
            w = do(chu, ten, co, dam) if do is not None else len(chu) * co * 0.55
            # định dạng kế toán "_-* … _-": khoảng đệm bằng một dấu "-" mỗi bên; x1,1 dư cho Excel làm tròn phông khi vẽ / in
            can_pt = max(can_pt, w * 1.1 + (co * 0.8 if '_' in fmt else 0))
        can_px = can_pt / 0.75 + 12                     # lề trong ô + đường kẻ
        rong = round((can_px - 5) / mdw + 0.3, 1)
        if rong > float(cd.width or 0):
            cd.width = rong
            kq[c] = rong
    return kq


def vua_cot_chu_bth(ws, cot: int, ds_chu: list, o_mau, do=None, so_dong: int = 4, toi_da: float = 30) -> float | None:
    """Cột chữ của từng thửa (Vị trí đất): nới để chữ dài nhất không quá so_dong dòng (mẫu hẹp làm vị trí tuyến đường xuống 12 dòng,
    dòng hộ cao vọt). Gọi TRƯỚC khi tính chiều cao dòng. Tối đa toi_da (độ rộng Excel). Trả độ rộng mới hoặc None."""
    from openpyxl.utils import get_column_letter
    cd = ws.column_dimensions.get(get_column_letter(cot))
    ds_chu = [str(x) for x in ds_chu if x]
    if cd is None or cd.hidden or not ds_chu:
        return None
    ten, co, dam = _phong(o_mau)
    can_pt = max((do(s, ten, co, dam) if do is not None else len(s) * co * 0.5) for s in ds_chu) / so_dong
    rong = min(toi_da, round((can_pt / 0.75 + 14 - 5) / _mdw(ws.parent) + 0.5, 1))
    if rong > float(cd.width or 0):
        cd.width = rong
        return rong
    return None


# ---------------------------------------------------------------- dàn trang thích ứng (người dùng 16/10/2026)
# Cả hai bản in: lề trang cân đối, tỷ lệ in vừa bề ngang (tắt "vừa N trang" - Excel bỏ qua ngắt trang tay khi bật), xếp trang theo
# cụm không được tách (tiêu đề bảng + dòng đầu, dòng mục + dòng con, hộ ít thửa, cụm tổng cộng + chữ ký), nén khít khi trang cuối
# chỉ tràn ít, giãn đều khi đáy trang hở vừa phải, rồi GHI ngắt trang tay ở cuối MỌI trang (Excel in đúng như phần mềm đã xếp).
# Đo bằng Excel thật (16/10/2026): sức chứa một trang = đúng chiều cao vùng in (38 dòng x 20 pt = 760 pt trên 762,8 pt A4 dọc, lề
# 0,55"); dòng tiêu đề lặp (print_title_rows) chỉ in ở đầu các trang BẮT ĐẦU SAU dòng tiêu đề.
LE_TRANG = {'chi_tiet': dict(top=0.55, bottom=0.55, left=0.60, right=0.40, header=0.22, footer=0.22),
            'tong_hop': dict(top=0.50, bottom=0.50, left=0.45, right=0.40, header=0.20, footer=0.20)}
GIAY_DOC = {8: (842.0, 1191.0), 9: (595.0, 842.0)}     # A3, A4 dọc (pt); mã paperSize của Excel
RONG_DU_PHONG = 0.96            # bề rộng vùng in dùng được khi tính tỷ lệ vừa ngang (dat_ti_le_vua_ngang)
DU_PHONG_TRANG = 0.98           # chừa 2% chiều cao trang (Excel làm tròn chiều cao dòng; AutoFit khi xuất PDF có thể nhích dòng)
NEN_DEM = 3.5                   # nén khít: đệm dòng bảng 8 -> 4,5 pt
CAO_NEN_TOI_THIEU = 20.5        # nén khít: dòng một dòng chữ không thấp hơn (trước 24)
NEN_TOI_DA = 0.14               # chỉ nén khi phần tràn sang trang cuối <= 14% chiều cao trang
GIAN_TU, GIAN_DEN = 0.08, 0.22  # giãn cân đối khi đáy trang hở 8% - 22%
GIAN_MOI_DONG = 3.0             # giãn tối đa mỗi dòng (pt)
HO_LON = 0.45                   # bảng tổng hợp: hộ cao hơn 45% trang = hộ nhiều thửa, được tách qua trang
CON_CHO_HO_LON = 85.0           # hộ nhiều thửa: trang còn >= 85 pt (~3 dòng thửa) thì bắt đầu ngay, không đẩy cả hộ sang trang
GHI_CHU_TOI_DA = 12             # phương án chi tiết: vùng gộp ô ghi chú đất không quá 12 dòng
TEN_DEM = 'PABT_DEM_DONG'       # tên vùng báo VBS xuất PDF đệm dòng (phần mười pt) khi đã nén khít
TEN_CAO_MIN = 'PABT_CAO_MIN'    # … và chiều cao tối thiểu (phần mười pt)


def chuan_le_trang(ws, loai: str = 'chi_tiet') -> dict:
    """Lề trang cân đối trên - dưới (inch) cho 'chi_tiet' (A4 dọc) / 'tong_hop' (ngang); hồ sơ địa phương ban_in.le_trang.<loai>
    ghi đè từng lề. Trả lề đã đặt."""
    from . import dia_phuong
    le = dict(LE_TRANG.get(loai, LE_TRANG['chi_tiet']))
    rieng = (dia_phuong.lay('ban_in.le_trang') or {}).get(loai) or {}
    for k, v in rieng.items():
        if k in le and isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 3:
            le[k] = float(v)
    for k, v in le.items():
        setattr(ws.page_margins, k, v)
    return le


def _kho_giay(ws) -> tuple:
    w, h = GIAY_DOC.get(int(ws.page_setup.paperSize or 9), GIAY_DOC[9])
    return (h, w) if (ws.page_setup.orientation or 'portrait') == 'landscape' else (w, h)


def dat_ti_le_vua_ngang(ws, n_cot: int) -> int:
    """Tỷ lệ in (scale %) vừa khít tổng bề rộng các cột hiện (1..n_cot) trên khổ giấy của mẫu; TẮT fitToPage (Excel bỏ qua ngắt trang
    tay khi in "vừa N trang"). Trả tỷ lệ."""
    from openpyxl.worksheet.properties import PageSetupProperties
    rong_pt = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75
    w, _ = _kho_giay(ws)
    m = ws.page_margins
    in_rong = w - ((m.left or 0) + (m.right or 0)) * 72
    # Excel (đo 16/10/2026 bằng xuất PDF): bảng 683 pt ở 75% = 512 pt vẫn bị tách cột Ghi chú sang trang riêng trên khổ in 523 pt,
    # 73% thì không - bề rộng dùng được thấp hơn lý thuyết ~3%: chừa RONG_DU_PHONG
    ty_le = max(10, min(100, int(in_rong * RONG_DU_PHONG / rong_pt * 100))) if rong_pt > 0 else 100
    if ws.sheet_properties.pageSetUpPr is None:
        ws.sheet_properties.pageSetUpPr = PageSetupProperties()
    ws.sheet_properties.pageSetUpPr.fitToPage = False
    ws.page_setup.scale = ty_le
    ws.page_setup.fitToHeight = None
    ws.page_setup.fitToWidth = None
    return ty_le


def cao_trang_in(ws) -> float:
    """Chiều cao (pt theo đơn vị của sheet - đã chia tỷ lệ in) chỗ in một trang: khổ giấy theo hướng, trừ lề trên / dưới."""
    _, h = _kho_giay(ws)
    m = ws.page_margins
    in_cao = h - ((m.top or 0) + (m.bottom or 0)) * 72
    return in_cao / (int(ws.page_setup.scale or 100) / 100) * DU_PHONG_TRANG


def _ham_cao(ws, thay: dict | None = None):
    mac = float(ws.sheet_format.defaultRowHeight or 15)

    def cao(r: int) -> float:
        if thay and r in thay:
            return thay[r]
        d = ws.row_dimensions.get(r)
        if d is None:
            return mac
        return 0.0 if d.hidden else float(d.height if d.height is not None else mac)
    return cao


def xep_trang(ws, khoi: list, cap: float, tieu_de: tuple | None = None, thay: dict | None = None) -> list:
    """Xếp các cụm dòng vào trang như Excel. khoi: [(kiểu, [(a, b), …])] liền nhau từ dòng 1, mỗi (a, b) là một đoạn không tách;
    kiểu 'tu_do' (các đoạn đặt lần lượt), 'lien' (cả cụm một trang - không vừa chỗ còn lại thì sang trang mới; cao hơn một trang thì
    xếp theo đoạn), 'lon' (hộ nhiều thửa: trang còn >= CON_CHO_HO_LON thì bắt đầu ngay rồi tách theo đoạn). tieu_de: (t1, t2) dòng
    lặp đầu trang (chỉ trang bắt đầu sau t2). Trả [(dòng đầu, dòng cuối, chiều cao đã dùng)] từng trang."""
    cao = _ham_cao(ws, thay)
    t1, t2 = tieu_de or (0, 0)
    cao_td = sum(cao(r) for r in range(t1, t2 + 1)) if tieu_de else 0.0
    trang = []
    st = {'dau': None, 'dung': 0.0, 'nen': 0.0}

    def mo(r):
        if st['dau'] is not None:
            trang.append((st['dau'], r - 1, st['dung']))
        st['dau'] = r
        st['nen'] = cao_td if tieu_de and r > t2 else 0.0
        st['dung'] = st['nen']

    def co_noi_dung():
        return st['dung'] > st['nen'] + 0.01

    def dat(a, b):
        hh = sum(cao(r) for r in range(a, b + 1))
        if st['dung'] + hh > cap and co_noi_dung():
            mo(a)
        if st['dung'] + hh <= cap or a == b:
            st['dung'] += hh
            return
        for r in range(a, b + 1):                       # đoạn cao hơn một trang: theo từng dòng
            if st['dung'] + cao(r) > cap and co_noi_dung():
                mo(r)
            st['dung'] += cao(r)

    for kieu, doan in khoi:
        if not doan:
            continue
        if st['dau'] is None:
            mo(doan[0][0])
        tong_cum = sum(cao(r) for a, b in doan for r in range(a, b + 1))
        if kieu == 'tu_do' or st['dung'] + tong_cum <= cap:
            if kieu == 'tu_do':
                for a, b in doan:
                    dat(a, b)
            else:
                st['dung'] += tong_cum
            continue
        if kieu == 'lien':
            if co_noi_dung():
                mo(doan[0][0])
            if st['dung'] + tong_cum <= cap:
                st['dung'] += tong_cum
                continue
        elif kieu == 'lon' and cap - st['dung'] < CON_CHO_HO_LON and co_noi_dung():
            mo(doan[0][0])
        for a, b in doan:
            dat(a, b)
    if st['dau'] is not None:
        r_cuoi = khoi[-1][1][-1][1] if khoi and khoi[-1][1] else st['dau']
        trang.append((st['dau'], r_cuoi, st['dung']))
    return trang


def _nen_trang(trang: list, tieu_de: tuple | None, cao_td: float) -> float:
    return cao_td if tieu_de and trang[0] > tieu_de[1] else 0.0


def co_gian_vua_trang(ws, khoi: list, cap: float, tieu_de: tuple | None, dong_nen: list, san: dict | None = None,
                      san_khoi: tuple = (), dong_gian: set | None = None, nen: bool = True) -> tuple:
    """Co giãn thích ứng chiều cao dòng rồi xếp trang (xep_trang). NÉN KHÍT: nội dung trang cuối chỉ tràn khỏi trang áp chót
    <= NEN_TOI_DA chiều cao trang -> các dòng dong_nen thuộc hai trang cuối giảm đệm 8 -> 4,5 pt (không thấp hơn san[dòng] - chữ của dòng + 4,5 - và CAO_NEN_TOI_THIEU;
    vùng gộp (a, b, tổng tối thiểu) trong san_khoi giữ đủ cao), dùng khi bớt được trang. GIÃN CÂN ĐỐI: trang (trừ trang cuối) hở đáy
    GIAN_TU - GIAN_DEN chiều cao trang -> chia phần hở cho các dòng dong_gian của trang (<= GIAN_MOI_DONG mỗi dòng). Đổi chiều cao
    dòng trong ws. Trả (các trang, đã nén?)."""
    cao = _ham_cao(ws)
    cao_td = sum(cao(r) for r in range(tieu_de[0], tieu_de[1] + 1)) if tieu_de else 0.0
    trang = xep_trang(ws, khoi, cap, tieu_de)
    da_nen = False
    # phần tràn = trang áp chót phải chứa thêm bao nhiêu để nhận hết nội dung trang cuối (cụm tổng cộng + chữ ký, hộ cuối…)
    tran = (trang[-2][2] + trang[-1][2] - _nen_trang(trang[-1], tieu_de, cao_td) - cap) if len(trang) > 1 else 0.0
    if nen and len(trang) > 1 and tran <= NEN_TOI_DA * cap:
        tu = trang[-2][0]
        thay = {}
        for r in dong_nen:
            if r >= tu:
                thay[r] = max(min(cao(r), max(CAO_NEN_TOI_THIEU, (san or {}).get(r, 0.0))), cao(r) - NEN_DEM)
        for a, b, toi_thieu in san_khoi:
            if b < tu:
                continue
            tong = sum(thay.get(r, cao(r)) for r in range(a, b + 1))
            if tong < toi_thieu:
                for r in range(a, b + 1):
                    thay[r] = thay.get(r, cao(r)) + (toi_thieu - tong) / (b - a + 1)
        trang_nen = xep_trang(ws, khoi, cap, tieu_de, thay)
        if len(trang_nen) < len(trang):
            for r, h in thay.items():
                ws.row_dimensions[r].height = round(h, 2)
            trang, da_nen = trang_nen, True
    if dong_gian:
        for dau, cuoi, dung in trang[:-1]:
            ho = cap - dung
            ds = [r for r in range(dau, cuoi + 1) if r in dong_gian and cao(r) > 0]
            if ds and GIAN_TU * cap <= ho <= GIAN_DEN * cap:
                them = min(GIAN_MOI_DONG, (ho - 2) / len(ds))
                for r in ds:
                    ws.row_dimensions[r].height = round(cao(r) + them, 2)
        trang = [(d, c, d2) for d, c, d2 in xep_trang(ws, khoi, cap, tieu_de)]
    return trang, da_nen


def ghi_ngat_trang(ws, trang: list, tu_dong: int = 1) -> list:
    """Ngắt trang tay ở cuối mọi trang (trừ trang cuối) - Excel in đúng cách xếp của phần mềm. Trả các dòng đã ngắt (ngắt SAU dòng)."""
    from openpyxl.worksheet.pagebreak import Break
    ngat = [cuoi for _, cuoi, _ in trang[:-1]]
    ws.row_breaks.brk = [b for b in ws.row_breaks.brk if b.id < tu_dong]
    for r in ngat:
        ws.row_breaks.append(Break(id=r))
    return ngat


def _dat_ten_vbs(ws, da_nen: bool) -> None:
    """Đã nén khít: báo VBS xuất PDF (AutoFit vùng PABT_TU_GIAN_DONG) dùng đệm 4,5 pt / tối thiểu 20,5 pt thay vì 8 / 24 - không giãn
    lại các dòng vừa nén làm tràn trang."""
    wb = ws.parent
    for ten, gia_tri in ((TEN_DEM, int(round((DEM_DONG - NEN_DEM) * 10))), (TEN_CAO_MIN, int(round(CAO_NEN_TOI_THIEU * 10)))):
        if da_nen:
            wb.defined_names[ten] = DefinedName(ten, attr_text=str(gia_tri))
        elif ten in wb.defined_names:
            del wb.defined_names[ten]


def _tach_gop_doc(ws, c: int, e: int, chi_muc: dict | None = None):
    """Vùng gộp dọc ở cột c phủ hai dòng e và e + 1: tách thành [đầu..e] và [e + 1..cuối] (gộp lại nếu > 1 dòng). Trả (đầu, cuối)
    của vùng cũ hoặc None."""
    m = _vung_tron(ws, e, c, chi_muc)
    if m is None or m.max_row <= e or m.min_col != m.max_col:
        return None
    a, b = m.min_row, m.max_row
    kieu = copy(ws.cell(a, c)._style)
    ws.unmerge_cells(m.coord)
    ws.cell(e + 1, c)._style = copy(kieu)
    for r1, r2 in ((a, e), (e + 1, b)):
        if r2 > r1:
            _gop_o(ws, r1, c, r2, c)
        else:
            ws.cell(r1, c)._style = copy(kieu)
    return a, b


def ngat_trang_ct(ws, dau: int, loai: list, cuoi_bang: int, san: dict | None = None, san_khoi: tuple = (),
                  nhom_gc: list | None = None, cot_gc: int | None = None, co: float = 14) -> list:
    """Dàn trang phương án chi tiết (người dùng 16/10/2026). dau: dòng số liệu đầu của bảng III (dau - 1 hàng tiêu đề cột, dau - 2 dòng
    "III."); loai: loại từng dòng bảng (dong_chi_tiet: 'H' tiêu đề mục, 'T' tổng cộng…). Lề chuẩn, tỷ lệ vừa ngang, hàng tiêu đề cột
    lặp đầu trang; không tách: cụm "III." + tiêu đề cột + dòng mục 1. + dòng số liệu đầu (>= ~110 pt: còn chỗ thì bảng bắt đầu ngay
    trang 1), dòng mục + dòng con đầu, cụm cuối (dòng số liệu cuối + TỔNG CỘNG + IV + ngày + chữ ký). Nén khít / giãn cân đối
    (co_gian_vua_trang), ngắt trang tay mọi trang; vùng gộp ghi chú đất qua ranh trang tách đôi (chữ ghi chú lặp ở trang sau). Trả
    các dòng đã ngắt."""
    chuan_le_trang(ws, 'chi_tiet')
    dat_ti_le_vua_ngang(ws, cuoi_bang)
    ws.print_title_rows = f'{dau - 1}:{dau - 1}'        # _doi_dong (nguồn gốc dài chèn dòng) không dời dòng tiêu đề lặp của mẫu
    cap = cao_trang_in(ws)
    n = len(loai)
    r_iii = dau - 2
    cuoi = max(_dong_cuoi(ws, cuoi_bang), dau + n - 1)
    khoi = [('tu_do', [(r, r) for r in range(1, r_iii)])]
    j = 1 if n and loai[0] == 'H' else 0                # dòng số liệu đầu
    c_dau = dau + min(j, n - 1) if n else dau - 1
    khoi.append(('lien', [(r_iii, c_dau)]))
    i = c_dau - dau + 1
    while i < n:
        r = dau + i
        if loai[i] == 'H' and i + 1 < n:                # dòng mục luôn kèm ít nhất một dòng con
            khoi.append(('lien', [(r, r + 1)]))
            i += 2
        else:
            khoi.append(('tu_do', [(r, r)]))
            i += 1
    # cụm cuối: dòng số liệu cuối + TỔNG CỘNG + IV + ngày tháng + chữ ký
    i_t = next((k for k in range(n) if loai[k] == 'T'), n)
    bat_dau = dau + max(0, i_t - 1)
    while len(khoi) > 1 and khoi[-1][1] and khoi[-1][1][-1][1] >= bat_dau:
        bat_dau = min(bat_dau, khoi[-1][1][0][0])
        khoi.pop()
    if bat_dau <= cuoi:
        khoi.append(('lien', [(bat_dau, cuoi)]))
    dong_bang = [dau + k for k in range(n)]
    tieu_de = (dau - 1, dau - 1)
    trang, da_nen = co_gian_vua_trang(ws, khoi, cap, tieu_de, dong_bang, san, san_khoi,
                                      {dau + k for k in range(n) if loai[k] != 'T'})
    _dat_ten_vbs(ws, da_nen)
    # vùng gộp ghi chú đất qua ranh trang: tách ở ranh, lặp chữ ở đầu trang sau; phần nào thiếu cao cho chữ thì giãn rồi xếp lại
    nhom_gc = list(nhom_gc or ())
    for _ in range(3):
        doi = False
        ranh = sorted(c for _, c, _ in trang[:-1])
        con_tach = True
        while con_tach and cot_gc:
            con_tach = False
            for a, b in list(nhom_gc):
                e = next((x for x in ranh if a <= x < b), None)
                if e is None:
                    continue
                chu = ws.cell(a, cot_gc).value
                nhom_gc.remove((a, b))
                if _tach_gop_doc(ws, cot_gc, e) is None:
                    continue
                ws.cell(e + 1, cot_gc).value = chu
                nhom_gc.extend([(a, e), (e + 1, b)])
                for r1, r2 in ((a, e), (e + 1, b)):
                    ten, co_o, dam = _phong(ws.cell(r1, cot_gc))
                    can = cao_dong_bang(so_dong_o(chu, _rong_vung(ws, cot_gc, cot_gc), ten, co_o, dam), co_o)
                    cao = _ham_cao(ws)
                    co_san = sum(cao(r) for r in range(r1, r2 + 1))
                    if co_san + 0.01 < can:
                        for r in range(r1, r2 + 1):
                            ws.row_dimensions[r].height = min(CAO_TOI_DA, cao(r) + (can - co_san) / (r2 - r1 + 1))
                        doi = True
                con_tach = True
                break
        if not doi:
            break
        trang = xep_trang(ws, khoi, cap, tieu_de)
    return ghi_ngat_trang(ws, trang)


def ngat_trang_bth(ws, khoi_ho: list, tong: int, n_cot: int, cuoi: int | None = None, dong_tieu_de: tuple = (9, 12),
                   san: dict | None = None, san_khoi: tuple = (), cam: set | None = None, tach_ho=None) -> list:
    """Dàn trang bảng tổng hợp (người dùng 16/10/2026). Lề chuẩn, tỷ lệ vừa ngang, hàng tiêu đề (dong_tieu_de) lặp đầu trang. Hộ ít
    thửa (<= HO_LON trang) không tách qua trang; hộ / tổ chức nhiều thửa không đẩy cả hộ sang trang mới khi trang còn >=
    CON_CHO_HO_LON - tách ở ranh giới dòng thửa (cam: dòng KHÔNG được ngắt sau - phần nối dài của ô thửa), rồi tach_ho(r0, r1, e)
    tách các vùng gộp của hộ ở ranh trang. Cụm cuối (tổng cộng + kinh phí + chữ ký, tong..cuoi) không tách, luôn kèm ít nhất phần cuối
    của hộ cuối. Nén khít / giãn cân đối (co_gian_vua_trang). Trả các dòng đã ngắt (ngắt SAU dòng)."""
    chuan_le_trang(ws, 'tong_hop')
    dat_ti_le_vua_ngang(ws, n_cot)
    cap = cao_trang_in(ws)
    cuoi = cuoi or _dong_cuoi(ws, n_cot)
    cao = _ham_cao(ws)
    cam = cam or set()
    d0 = khoi_ho[0][0] if khoi_ho else tong

    def cum_ho(r0, r1, ghep_cuoi=None):
        doan, a = [], r0
        for r in range(r0, r1 + 1):
            if r not in cam or r == r1:
                doan.append((a, r))
                a = r + 1
        if ghep_cuoi is not None:                       # đoạn cuối của hộ ghép với cụm cuối bảng
            doan[-1] = (doan[-1][0], ghep_cuoi)
        lon = sum(cao(r) for r in range(r0, r1 + 1)) > HO_LON * cap
        return ('lon' if lon else 'lien', doan)

    def lap_khoi(ghep):
        k = [('tu_do', [(r, r) for r in range(1, d0)])]
        for i, (r0, r1) in enumerate(khoi_ho):
            if ghep and i == len(khoi_ho) - 1:
                kieu, doan = cum_ho(r0, r1, cuoi)
                if kieu == 'lien' and sum(cao(r) for r in range(r0, cuoi + 1)) > cap - sum(
                        cao(r) for r in range(dong_tieu_de[0], dong_tieu_de[1] + 1)):
                    kieu = 'lon'
                k.append((kieu, doan))
            else:
                k.append(cum_ho(r0, r1))
        if not ghep or not khoi_ho:
            k.append(('lien', [(tong, cuoi)]))
        return k
    khoi = lap_khoi(False)
    dong_du_lieu = list(range(d0, tong))
    trang, da_nen = co_gian_vua_trang(ws, khoi, cap, dong_tieu_de, dong_du_lieu, san, san_khoi, set(dong_du_lieu))
    if khoi_ho and any(dau == tong for dau, _, _ in trang):            # cụm tổng cộng + chữ ký đứng trơ một trang: kèm hộ cuối
        khoi = lap_khoi(True)
        trang, _ = co_gian_vua_trang(ws, khoi, cap, dong_tieu_de, dong_du_lieu, san, san_khoi, set(dong_du_lieu), nen=False)
    for _ in range(3 if tach_ho is not None else 0):
        ranh = [c for _, c, _ in trang[:-1]]
        doi = False
        for r0, r1 in khoi_ho:
            for e in [x for x in ranh if r0 <= x < r1]:
                doi = bool(tach_ho(r0, r1, e)) or doi
        if not doi:                                     # tách xong mà phần sau đủ cao: giữ cách xếp
            break
        trang = xep_trang(ws, khoi, cap, dong_tieu_de)
    return ghi_ngat_trang(ws, trang, d0)


def _rong_can_so(o, v, do=None, dam: bool | None = None) -> float:
    """Độ rộng cột (đơn vị Excel) để ô o hiện đủ số v theo định dạng của ô (kế toán: thêm đệm hai bên), không "#####"."""
    fmt = o.number_format
    ten, co, d = _phong(o)
    dam = d if dam is None else dam
    chu = _chu_so_excel(v, fmt)
    w = do(chu, ten, co, dam) if do is not None else len(chu) * co * 0.55
    can_pt = w * 1.1 + (co * 0.8 if '_' in (fmt or '') else 0)
    return round((can_pt / 0.75 + 12 - 5) / _mdw(o.parent.parent) + 0.3, 1)


def can_bang_cot_bth(ws, cot_so: dict, cot_chu: tuple, d0: int, do=None) -> float:
    """Bảng tổng hợp (người dùng 16/10/2026): cột số còn nhiều chỗ trống (rộng hơn 15% và >= 1 ký tự so với số lớn nhất dự kiến -
    cot_so {cột: số}) thu về vừa số đó (+5%), phần thu được chia đều cho các cột chữ cot_chu (họ tên, địa chỉ, vị trí) - tổng bề rộng
    (tỷ lệ in) không đổi, chữ ít xuống dòng hơn, bảng gọn. Gọi TRƯỚC khi tính chiều cao dòng. Trả độ rộng đã chuyển."""
    from openpyxl.utils import get_column_letter
    thu = 0.0
    for c, v in cot_so.items():
        cd = ws.column_dimensions.get(get_column_letter(c))
        if cd is None or cd.hidden or not cd.width or v is None or (cd.min and cd.max and cd.min != cd.max):
            continue
        can = _rong_can_so(ws.cell(d0, c), v, do, dam=True)
        if cd.width > can * 1.15 and cd.width - can >= 1:
            moi = round(can * 1.05, 1)
            thu += cd.width - moi
            cd.width = moi
    chu = [ws.column_dimensions.get(get_column_letter(c)) for c in cot_chu]
    chu = [cd for cd in chu if cd is not None and not cd.hidden and cd.width and not (cd.min and cd.max and cd.min != cd.max)]
    if not chu or thu <= 0:
        return 0.0
    for cd in chu:
        cd.width = round(cd.width + thu / len(chu), 1)
    return thu


def lap_bang_tong_hop(con, file_ra, ds_ma_ho: list | None = None, mau: Path | None = None, so_pa_tong: str = '',
                      ngay_pa_tong: str = '', bao_tien_do=None, ky_hieu_so: str = '', du_thao: bool | None = None) -> Path:
    """Bảng tổng hợp các hộ. so_pa_tong / ngay_pa_tong (phương án tổng của đợt trình): điền vào "(Đính kèm Phương án số …/…
    ngày … tháng … năm …)" và ngày ký của mẫu (chỗ trống {so_pa_tong}, {ngay_pa_tong} cũng dùng được).
    bao_tien_do(i, n): gọi mỗi 100 hộ để hộp tiến trình vẽ lại (bảng nhiều hộ, không "Không phản hồi"); không dừng giữa chừng.
    Vị trí cột, dòng dữ liệu đầu, cột cộng SUM, làm tròn và phân bổ kinh phí tổ chức thực hiện: hồ sơ địa phương (0.9.85)."""
    from . import dia_phuong
    from openpyxl.utils import get_column_letter
    mau = file_mau(mau, TEN_BTH)
    du_thao = la_mau_du_thao(mau) if du_thao is None else bool(du_thao)     # chế độ phát hành (xem lap_chi_tiet)
    if du_thao:
        so_pa_tong, ngay_pa_tong = '', ''
    duong_ke = duong_ke_cua_mau(mau, TEN_BTH)
    wb = mo_mau(mau)
    ws = wb.worksheets[0]
    K = dia_phuong.cot_mau(TEN_BTH)                                     # trường -> số cột
    d0 = int(dia_phuong.lay('mau_in.IN_BANGTONGHOP.dong_du_lieu_dau', DONG_DAU_BTH))
    n_cot = dia_phuong.so_cot(dia_phuong.lay('mau_in.IN_BANGTONGHOP.cot_cuoi', 'Y'))
    cot_ho = (K['ho_ten'], K['dia_chi'], K['nguon_goc'], K['tai_dinh_cu'], K['ghi_chu'])     # chữ gộp theo hộ
    cot_thua = (K['loai_dat'], K['vi_tri'])                                                   # chữ từng thửa
    gop_ho = {K[k] for k in ('stt', 'ho_ten', 'dia_chi', 'tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao',
                             'ho_tro_on_dinh', 'thuong', 'tong', 'nguon_goc', 'tai_dinh_cu', 'ghi_chu')}
    # ô cần đường kẻ dưới (tên đơn vị, tiêu ngữ, Dự án): tìm trước khi điền - dùng khi mẫu không có file đường kẻ
    vt_dk = [(vi_tri_cho(ws, '{DON_VI_TIEU_DE}'), 1.0), (o_tieu_ngu(ws), 1.0), (vi_tri_cho(ws, '{du_an}'), 1.0)]
    vt = vt_dk[2][0]
    if vt:                                        # dòng "Dự án" đủ cao cho đường kẻ dưới chữ (mẫu cũ 25,2 pt: đường kẻ chạm dòng dưới)
        ws.row_dimensions[vt[0]].height = max(float(ws.row_dimensions[vt[0]].height or 15), _phong(ws.cell(vt[0], vt[1]))[1] * 1.7)
    da = _thong_tin_du_an(con)
    bc = BoiCanh.tu(con)
    # phương án đọc MỘT lần (0.9.87): cả dự án -> đọc hết rồi tính kết quả dùng chung trên đó (trước: ho_co_phuong_an đọc cả dự
    # án trong ket_qua_ho rồi đọc lại các hộ có phương án); kết quả đã nhớ (ket_qua_ho_san) thì chỉ đọc các hộ cần in
    kqh = nghiep_vu.ket_qua_ho_san(con)
    if ds_ma_ho is None and kqh is None:
        tat_ca = nghiep_vu.doc_tat_ca_phuong_an(con)
        kqh = nghiep_vu.ket_qua_ho(con, tat_ca)
        ds_ma_ho = [m for m, (k, _) in kqh.items() if k.co_phuong_an]
    else:
        if ds_ma_ho is None:
            ds_ma_ho = [m for m, (k, _) in kqh.items() if k.co_phuong_an]
        tat_ca = nghiep_vu.doc_tat_ca_phuong_an(con, ds_ma_ho)          # 3 câu truy vấn thay vì 3 câu mỗi hộ
        kqh = kqh if kqh is not None else nghiep_vu.ket_qua_ho(con)
    thu_tu = {r['ma_ho']: (r['thu_tu'], r['ma_ho']) for r in con.execute('SELECT ma_ho, thu_tu FROM ho')}
    ds_ma_ho = sorted(ds_ma_ho, key=lambda m: thu_tu.get(m, (0, m)))
    khoi = []
    for ma in ds_ma_ho:
        pa = tat_ca.get(ma) or doc_phuong_an(con, ma)
        kq = kqh[ma][0] if ma in kqh else tinh_pa(pa, bc)
        thua = list(bc.thua_cua(ma))
        khoi.append((ma, pa, kq, thua))
    can = sum(max(1, len(t)) for _, _, _, t in khoi) or 1
    for c in range(1, n_cot + 1):               # mọi ô dữ liệu (chữ và số tiền): căn giữa dọc, tự xuống dòng - chép theo dòng mẫu
        _can_giua_doc(ws.cell(d0, c))
    _doi_dong(ws, d0 + 1, can - 1)
    for r in range(d0 + 1, d0 + can):
        _chep_kieu_dong(ws, d0, r, n_cot)
    cao = max(float(ws.row_dimensions[d0].height or 36), cao_dong_bang(1, ws.cell(d0, K['ho_ten']).font.sz or 14))
    for r in range(d0, d0 + can):
        ws.row_dimensions[r].height = cao
    do = _ham_do_chu()
    # cột số còn dư chỗ nhường cho họ tên / địa chỉ / vị trí (16/10/2026): số lớn nhất dự kiến = tổng cả bảng (tiền: tổng các hộ;
    # diện tích: tổng diện tích thu hồi) - không cột nào nhỏ hơn số của dòng TỔNG CỘNG
    tong_tien = sum((k.tong for _, _, k, _ in khoi), KHONG)
    tong_dt_du_kien = sum((D(t['dt_thu_hoi']) for _, _, _, ts in khoi for t in ts), KHONG)
    cot_so = {K[k]: _so(tong_tien) for k in ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh',
                                             'thuong', 'tong') if k in K}
    cot_so.update({K[k]: _so(tong_dt_du_kien) for k in ('dt_thu_hoi', 'dt_nong_nghiep', 'dt_lua', 'dt_phi_nong_nghiep', 'dt_o')
                   if k in K})
    can_bang_cot_bth(ws, cot_so, (K['ho_ten'], K['dia_chi'], K['vi_tri']), d0, do)
    vua_cot_chu_bth(ws, K['vi_tri'], [d.vi_tri for _, pa, _, _ in khoi for d in pa.dat], ws.cell(d0, K['vi_tri']), do)
    px, nho = _px_cot(ws, n_cot + 1), {}
    dong_them = 0                                                       # dòng thêm cho hộ có chữ quá 409 pt
    khoi_ho = []                                                        # [(dòng đầu, dòng cuối)] từng hộ - ngắt trang giữa các hộ
    san, san_khoi, cam = {}, [], set()                                  # nén khít: chiều cao tối thiểu; dòng không được ngắt sau
    r = d0
    tong_thua, tong_dt = 0, KHONG
    co_vat_nuoi = False                                                 # có hộ có vật nuôi: tiêu đề cột cây trồng ghi cả vật nuôi
    ho = {r['ma_ho']: r for r in con.execute('SELECT * FROM ho')}       # một câu thay vì một câu mỗi hộ
    from .ho_so import chuan_nguon_goc
    for stt, (ma, pa, kq, thua) in enumerate(khoi, start=1):
        if bao_tien_do and stt % 100 == 0:
            bao_tien_do(stt, len(khoi))
        h = ho[ma]
        r0 = r
        ws.cell(r0, K['stt']).value = stt
        ws.cell(r0, K['ho_ten']).value = h['ho_ten']
        ws.cell(r0, K['dia_chi']).value = h['dia_chi']
        for t in thua:
            dat_thua = [d for d in pa.dat if d.ma_thua == t['ma_thua']]
            ws.cell(r, K['so_to']).value = t['so_to']
            ws.cell(r, K['so_thua']).value = t['so_thua']
            ws.cell(r, K['loai_dat']).value = t['loai_dat']
            ws.cell(r, K['dt_thu_hoi']).value = _so(t['dt_thu_hoi'])
            nn = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Nông nghiệp'), KHONG)
            lua = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Nông nghiệp' and d.loai_dat.upper() in ('LUC', 'LUK')), KHONG)
            o = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Đất ở'), KHONG)
            pnn = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Phi nông nghiệp'), KHONG)
            ws.cell(r, K['dt_nong_nghiep']).value = _so(nn)
            ws.cell(r, K['dt_lua']).value = _so(lua) if lua else None
            ws.cell(r, K['dt_phi_nong_nghiep']).value = _so(o + pnn)
            ws.cell(r, K['dt_o']).value = _so(o)
            ws.cell(r, K['vi_tri']).value = dat_thua[0].vi_tri if dat_thua else None
            if ws.cell(r0, K['nguon_goc']).value in (None, '') and t['nguon_goc']:
                ws.cell(r0, K['nguon_goc']).value = chuan_nguon_goc(t['nguon_goc'])
            tong_thua += 1
            tong_dt += D(t['dt_thu_hoi'])
            r += 1
        if r == r0:
            r += 1
        ht = kq.muc[4]
        dao_tao = sum((nghiep_vu.thanh_tien_dong(d, bc) for d in pa.dong_ho_tro('CS9', 'CS10')), KHONG)
        on_dinh = sum((nghiep_vu.thanh_tien_dong(d, bc) for d in pa.dong_ho_tro(*MA_ON_DINH)), KHONG)
        co_vat_nuoi = co_vat_nuoi or kq.muc[nghiep_vu.MUC_VN] != 0
        for k, v in (('tien_dat', kq.muc[1]), ('tien_tai_san', kq.muc[2]), ('tien_cay_vat_nuoi', kq.muc[3] + kq.muc[nghiep_vu.MUC_VN]),
                     ('ho_tro_dao_tao', dao_tao), ('ho_tro_on_dinh', on_dinh), ('thuong', kq.muc[5]), ('tong', kq.tong)):
            ws.cell(r0, K[k]).value = _so(v)
        ws.cell(r0, K['tai_dinh_cu']).value = h['tai_dinh_cu'] or None
        khac = ht - dao_tao - on_dinh
        ws.cell(r0, K['ghi_chu']).value = f'Hỗ trợ khác: {format(int(khac), ",").replace(",", ".")} đ' if khac > 0 else None
        # chữ gộp theo hộ (nguồn gốc dài, hộ ít thửa) cao hơn số dòng x 409 pt (trần Excel): thêm dòng cho hộ, ô thửa cuối gộp
        # xuống các dòng thêm - không mất chữ
        can_ho = cao_can_ho_bth(ws, r0, px, do, nho, cot_ho)
        them_ho = math.ceil(can_ho / CAO_TOI_DA) - (r - r0)
        if them_ho > 0:
            # 16/10/2026: hộ cao hơn một trang sẽ bị tách ở ranh trang - mỗi dòng chừa một dòng chữ + đệm (dưới trần 409 pt) để phần
            # sau đủ chỗ cho đệm của ô gộp mới và dòng chữ bị làm tròn
            tran = CAO_TOI_DA - dong_chu_bang(float(ws.cell(r0, cot_ho[0]).font.sz or 14)) - DEM_DONG
            them_ho = math.ceil(can_ho / tran) - (r - r0)
        if them_ho > 0:
            cam.update(range(r - 1, r - 1 + them_ho))                       # ô thửa cuối gộp xuống dòng thêm
            _doi_dong(ws, r, them_ho)
            for rr in range(r, r + them_ho):
                _chep_kieu_dong(ws, r0, rr, n_cot)
                ws.row_dimensions[rr].height = cao
            for c in range(1, n_cot + 1):
                if c not in gop_ho:
                    _gop_o(ws, r - 1, c, r - 1 + them_ho, c)
            r += them_ho
            dong_them += them_ho
        if r - 1 > r0:
            for c in sorted(gop_ho):
                _gop_o(ws, r0, c, r - 1, c)
        _vua_cao_ho_bth(ws, r0, r, px, do, can_ho, nho, cot_ho, cot_thua)
        khoi_ho.append((r0, r - 1))
        co_ho = float(ws.cell(r0, cot_ho[0]).font.sz or 14)
        for rr in range(r0, r):
            n_thua = max(_so_dong_bth(ws, rr, c, px, do, nho) for c in cot_thua)
            san[rr] = max(CAO_NEN_TOI_THIEU, n_thua * dong_chu_bang(co_ho) + DEM_DONG - NEN_DEM)
        san_khoi.append((r0, r - 1, can_ho - NEN_DEM))
    tong = d0 + can + dong_them
    for rr in range(tong, tong + 5):            # dòng tổng cộng, kinh phí tổ chức thực hiện, tổng cộng cuối: căn giữa dọc
        for c in range(1, n_cot + 1):
            if ws.cell(rr, c).has_style or ws.cell(rr, c).value is not None:
                _can_giua_doc(ws.cell(rr, c))
    if co_vat_nuoi:                                                     # cột cây trồng + vật nuôi (mục 4 của bản chi tiết)
        for rr in range(1, d0):
            v = ws.cell(rr, K['tien_cay_vat_nuoi']).value
            if isinstance(v, str) and 'cây trồng' in v and 'vật nuôi' not in v:
                ws.cell(rr, K['tien_cay_vat_nuoi']).value = v.replace('cây trồng', 'cây trồng, vật nuôi')
    for cl in dia_phuong.lay('mau_in.IN_BANGTONGHOP.cot_cong'):          # cột diện tích, kinh phí: =SUM(…)
        ws[f'{cl}{tong}'] = f'=SUM({cl}{d0}:{cl}{tong - 1})'
    # các dòng kinh phí dưới dòng tổng: kinh phí tổ chức thực hiện theo loại dự án (mức tối đa theo hồ sơ địa phương - Đồng Nai QĐ
    # 08/2025/QĐ-UBND: theo tuyến 3,5%, cụm / vùng / khác 2,5% - lap_pa.kinh_phi_to_chuc) và phân bổ (85% / 15%) - tỷ lệ trong chữ
    # của mẫu thay theo hồ sơ, công thức làm tròn theo hồ sơ (-3 = đến nghìn đồng)
    from .lap_pa import kinh_phi_to_chuc
    from .tien import chuoi, so_vn
    _, tl_kp, _ = kinh_phi_to_chuc(con)
    lam_tron = int(dia_phuong.lay('kinh_phi_to_chuc.lam_tron_den', -3))
    phan_bo = dia_phuong.phan_bo_kinh_phi()
    V = get_column_letter(K['tong'])
    j = 0                                                               # dòng phân bổ thứ j
    for rr in range(tong + 1, tong + 5):
        chu_dong = [(c, ws.cell(rr, c).value) for c in range(1, n_cot + 1) if isinstance(ws.cell(rr, c).value, str)]
        a = ' '.join(v for _, v in chu_dong)
        if rr == tong + 1:
            c0, chu = chu_dong[0] if chu_dong else (1, '')
            if chu:
                chu = re.sub(r'[…\d,\.]+\s*%', f'{so_vn(tl_kp)}%', chu, count=1) if '%' in chu else \
                    chu.rstrip(': ') + f' {so_vn(tl_kp)}%:'
                chu = bo_can_cu_kinh_phi(chu)          # 16/10/2026: không ghi "(theo Quyết định số 08/2025/QĐ-UBND …)"
                ws.cell(rr, c0).value = chu
            ws[f'{V}{rr}'] = f'=ROUND({V}{tong}*{chuoi(tl_kp)}%, {lam_tron})'
        elif 'TỔNG CỘNG' in a:
            ws[f'{V}{rr}'] = f'={V}{tong}+{V}{tong + 1}'
        else:
            co_pt = [(c, v) for c, v in chu_dong if re.search(r'\d+(?:[,\.]\d+)?\s*%', v)]
            if co_pt and j < len(phan_bo):
                c, v = co_pt[-1]
                ty_le = phan_bo[j][1]
                ws.cell(rr, c).value = re.sub(r'\d+(?:[,\.]\d+)?\s*%', f'{so_vn(ty_le)}%', v, count=1)
                ws[f'{V}{rr}'] = f'=ROUND({V}{tong + 1}*{chuoi(ty_le)}%, {lam_tron})'
                j += 1
    a6 = str(ws['A6'].value or '')
    if '(Đối với ' in a6:
        ws['A6'] = re.sub(r'\(Đối với .*?m2\)', f'(Đối với {len(khoi):02d} trường hợp/ {tong_thua} thửa đất/ '
                          f'{format(float(tong_dt), ",.1f").replace(",", "#").replace(".", ",").replace("#", ".")}m2)', a6)
    dien_so_ngay(ws, so_pa_tong, ngay_pa_tong, 'Phương án số')
    chuan_dong_ngay(ws)
    viet_hoa_du_an(ws, d0)                                       # "DỰ ÁN <tên>" như phương án chi tiết
    can_khoi_ky(ws)
    # 16/10/2026: cột số đủ rộng (không "#####"), cột vị trí không quá 4 dòng chữ; rồi ngắt trang ở ranh giới hộ
    vua_cot_so_bth(ws, d0, tong, n_cot, do)
    cuoi = _dong_cuoi(ws, n_cot)
    lap_lai = (K['stt'], K['ho_ten'], K['dia_chi'])                     # hộ tách qua trang: lặp ở đầu phần sau

    def tach_ho(r0, r1, e):
        """Hộ nhiều thửa vắt qua ranh trang (ngắt sau dòng e): tách mọi vùng gộp theo hộ thành hai vùng; STT, họ tên, địa chỉ lặp ở
        phần sau; nguồn gốc chia theo số dòng chữ vừa phần trên (phần còn lại sang phần sau); số tiền giữ ở phần đầu (SUM không
        đổi). Phần sau thiếu cao cho chữ thì giãn. Trả True nếu đã giãn dòng."""
        gian = False
        cao = _ham_cao(ws)
        for c in range(1, n_cot + 1):                                   # cả ô thửa gộp xuống dòng thêm (chữ dài)
            tach = _tach_gop_doc(ws, c, e)
            if tach is None:
                continue
            a, b = tach
            chu = ws.cell(a, c).value
            if c not in gop_ho:
                continue
            if c in lap_lai:
                ws.cell(e + 1, c).value = chu
            elif c == K['nguon_goc'] and isinstance(chu, str) and chu.strip():
                ten, co_o, dam = _phong(ws.cell(a, c))
                dong_o = _ngat(chu, px[c - 1] * 0.75 - 6, ten, co_o, dam, do, treo=False)
                vua = max(1, int((sum(cao(rr) for rr in range(a, e + 1)) - DEM_DONG) // dong_chu_bang(co_o)))
                if len(dong_o) > vua:
                    def noi(ds):
                        return ''.join(('\n' if dau_d and j else ' ' if j else '') + x for j, (x, dau_d) in enumerate(ds))
                    # đo lại như các chỗ tính chiều cao (so_dong_o: gạch đầu dòng thụt lề treo có thể thêm dòng) - phần trên
                    # không được nhiều dòng hơn chỗ của nó
                    rong_o = px[c - 1] * 0.75 - 6
                    while vua > 1 and so_dong_o(noi(dong_o[:vua]), rong_o, ten, co_o, dam, do) > \
                            int((sum(cao(rr) for rr in range(a, e + 1)) - DEM_DONG) // dong_chu_bang(co_o)):
                        vua -= 1
                    ws.cell(a, c).value = noi(dong_o[:vua])
                    ws.cell(e + 1, c).value = noi(dong_o[vua:])
            else:
                continue
            v = ws.cell(e + 1, c).value
            if isinstance(v, str) and v.strip():
                ten, co_o, dam = _phong(ws.cell(e + 1, c))
                can_c = cao_dong_bang(so_dong_o(v, px[c - 1] * 0.75 - 6, ten, co_o, dam, do), co_o, None)
                co_san = sum(cao(rr) for rr in range(e + 1, b + 1))
                if co_san + 0.01 < can_c:
                    for rr in range(e + 1, b + 1):
                        ws.row_dimensions[rr].height = min(CAO_TOI_DA, cao(rr) + (can_c - co_san) / (b - e))
                    gian = True
        return gian
    # dàn trang (16/10/2026): hộ ít thửa không tách, hộ nhiều thửa tách qua trang, cụm tổng cộng + chữ ký kèm hộ cuối, nén / giãn
    ngat_trang_bth(ws, khoi_ho, tong, n_cot, cuoi, (9, 12), san, tuple(san_khoi), cam, tach_ho)

    _thay_cho_trong(ws, dict(da, so_pa_tong=so_pa_tong or '', ngay_pa_tong=ngay_pa_tong or '',
                             ky_hieu_so=ky_hieu_so or da.get('ky_hieu_so') or ''))       # ký hiệu theo đợt trình (0.9.72)
    ap_che_do_du_thao(ws, du_thao, TEN_BTH)                      # dự thảo: "(DỰ THẢO)" ở tiêu đề; chính thức: xóa
    ws.print_area = f'A1:{get_column_letter(n_cot)}{_dong_cuoi(ws, n_cot) + 1}'
    wb.calculation.fullCalcOnLoad = True
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    dk = _dat_duong_ke(ws, vt_dk, duong_ke)       # sát chân chữ, căn giữa (tên đơn vị, tiêu ngữ, dòng dự án)
    wb.save(file_ra)
    chen_duong_ke(file_ra, duong_ke, dk)          # đường kẻ của mẫu (openpyxl không giữ hình vẽ)
    return file_ra


# ---------------------------------------------------------------- PDF / máy in qua Microsoft Excel
_VBS = r'''
On Error Resume Next
Dim xl, wb, f, i, ds, che_do, r, h, h0, nm, fso, dung, so, dem, cmin, nm2
Set fso = CreateObject("Scripting.FileSystemObject")
Set f = fso.OpenTextFile(WScript.Arguments(0), 1, False, -1)
dung = ""
If WScript.Arguments.Count > 1 Then dung = WScript.Arguments(1)
che_do = f.ReadLine
ban = 1
If InStr(che_do, ":") > 0 Then
    ban = CInt(Split(che_do, ":")(1))
    che_do = Split(che_do, ":")(0)
End If
Set xl = CreateObject("Excel.Application")
If Err.Number <> 0 Then
    WScript.StdErr.WriteLine "KHONG_CO_EXCEL"
    WScript.Quit 3
End If
xl.Visible = False
xl.DisplayAlerts = False
xl.ScreenUpdating = False
xl.AutomationSecurity = 3
xl.EnableEvents = False
xl.AskToUpdateLinks = False
Err.Clear
so = 0
Do While Not f.AtEndOfStream
    If dung <> "" Then
        If fso.FileExists(dung) Then Exit Do
    End If
    so = so + 1
    ds = Split(f.ReadLine, vbTab)
    Err.Clear
    Set wb = xl.Workbooks.Open(ds(0), 0, True)
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "LOI_MO" & vbTab & ds(0) & vbTab & Err.Description
    Else
        Err.Clear
        dem = 8
        cmin = 24
        Set nm2 = wb.Names("PABT_DEM_DONG")
        If Err.Number = 0 Then dem = CInt(Mid(nm2.RefersTo, 2)) / 10
        Err.Clear
        Set nm2 = wb.Names("PABT_CAO_MIN")
        If Err.Number = 0 Then cmin = CInt(Mid(nm2.RefersTo, 2)) / 10
        Err.Clear
        Set nm = wb.Names("PABT_TU_GIAN_DONG")
        If Err.Number = 0 Then
            For Each r In nm.RefersToRange.Rows
                h0 = r.RowHeight
                r.AutoFit
                h = r.RowHeight + dem
                If h < h0 Then h = h0
                If h < cmin Then h = cmin
                If h > 409 Then h = 409
                r.RowHeight = h
            Next
        End If
        Err.Clear
        xl.Calculate
        If che_do = "in" Then
            wb.Worksheets(1).PrintOut , , ban
        Else
            wb.Worksheets(1).ExportAsFixedFormat 0, ds(1)
        End If
        If Err.Number <> 0 Then WScript.StdErr.WriteLine "LOI_XUAT" & vbTab & ds(0) & vbTab & Err.Description
        wb.Close False
    End If
    WScript.StdOut.WriteLine "XONG" & vbTab & so
Loop
f.Close
xl.Quit
'''


def co_excel() -> bool:
    return sys.platform == 'win32'


CHO_MOI_FILE = 180          # giây: một file không xuất xong trong chừng này (Excel kẹt hộp thoại ẩn / máy in) thì dừng
CHO_KHOI_DONG = 120         # giây cộng thêm cho file đầu (mở Excel lần đầu chậm)


def _doc_luong(luong, ra: list) -> None:
    for dong in iter(luong.readline, b''):
        ra.append(dong.decode('oem' if sys.platform == 'win32' else 'utf-8', 'replace').rstrip('\r\n'))
    luong.close()


def _tat_excel_tu_dong(tu_luc: float, ten_exe: str = 'EXCEL.EXE') -> int:
    """Tắt các EXCEL.EXE (WINWORD.EXE: ten_exe) chạy ngầm do tự động hóa (dòng lệnh -Embedding / /automation) khởi động từ thời
    điểm tu_luc - không đụng tới Excel / Word người dùng đang mở. Trả số tiến trình đã tắt."""
    import datetime as _dt
    if not re.fullmatch(r'[A-Za-z0-9_]+\.EXE', ten_exe, re.I):
        return 0
    lenh = (f"Get-WmiObject Win32_Process -Filter \"Name='{ten_exe}'\" | Where-Object {{ $_.CommandLine -match "
            "'(-Embedding|/automation)' } | ForEach-Object { [string]$_.ProcessId + ' ' + $_.CreationDate }")
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', lenh], capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        return 0
    da_tat = 0
    for dong in r.stdout.decode('ascii', 'replace').splitlines():
        m = re.match(r'\s*(\d+)\s+(\d{14})', dong)
        if not m:
            continue
        try:
            luc = _dt.datetime.strptime(m.group(2), '%Y%m%d%H%M%S').timestamp()
        except ValueError:
            continue
        if luc >= tu_luc - 5:
            try:
                os.kill(int(m.group(1)), 9)
                da_tat += 1
            except OSError:
                pass
    return da_tat


def chay_excel(cap_file: list, che_do: str = 'pdf', cho_moi_file: int = CHO_MOI_FILE, bao=None, so_ban: int = 1) -> list:
    """Nhờ Excel xuất PDF (che_do='pdf', cap_file = [(xlsx, pdf)]) hoặc in ra máy in mặc định (che_do='in').
    bao(i, n): gọi liên tục trong lúc chờ (i = số file đã xong) để giao diện không treo; trả True = dừng (Excel làm xong file
    đang dở rồi thoát). Một file quá cho_moi_file giây: dừng, tắt Excel chạy ngầm, báo lỗi. Trả danh sách lỗi (rỗng = thành công)."""
    if not cap_file:
        return []
    if not co_excel():
        raise LoiIn('Xuất PDF / in cần Microsoft Excel trên máy Windows.')
    n = len(cap_file)
    out, err, them = [], [], []
    with tempfile.TemporaryDirectory() as td:
        vbs = Path(td) / 'xuat.vbs'
        vbs.write_text(_VBS, encoding='utf-16')
        ds = Path(td) / 'ds.txt'
        dau = f'in:{max(1, min(int(so_ban), 50))}' if che_do == 'in' else che_do
        ds.write_text('\n'.join([dau] + [f'{Path(a).resolve()}\t{Path(b).resolve() if b else ""}' for a, b in cap_file]),
                      encoding='utf-16')
        dung = Path(td) / 'dung.txt'
        bat_dau = time.time()
        try:
            pr = subprocess.Popen(['cscript', '//nologo', str(vbs), str(ds), str(dung)], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as e:
            raise LoiIn(f'Không chạy được trình điều khiển Excel (cscript): {e}') from e
        for luong, ra in ((pr.stdout, out), (pr.stderr, err)):
            threading.Thread(target=_doc_luong, args=(luong, ra), daemon=True).start()
        xong, moc, xin_dung, treo = 0, time.time(), None, False
        while pr.poll() is None:
            so = sum(1 for x in out if x.startswith('XONG'))
            if so != xong:
                xong, moc = so, time.time()
            if bao is not None and bao(xong, n) and xin_dung is None:
                dung.write_text('1', encoding='ascii')
                xin_dung = time.time()
                them.append('DA_DUNG')                  # số file đã xong đếm lại khi Excel thoát (file đang dở vẫn làm nốt)
            gioi_han = cho_moi_file + (CHO_KHOI_DONG if xong == 0 else 0)
            if xin_dung is None and time.time() - moc > gioi_han:
                dung.write_text('1', encoding='ascii')
                xin_dung, treo = time.time(), True
                ten = Path(cap_file[min(xong, n - 1)][0]).name
                them.append(f'LOI_TREO\t{ten}\tExcel không xuất xong file sau {gioi_han} giây (kẹt hộp thoại ẩn / máy in?): '
                            f'đã dừng sau {xong}/{n} file')
            if xin_dung is not None and time.time() - xin_dung > (5 if treo else cho_moi_file):
                pr.kill()
                _tat_excel_tu_dong(bat_dau)
                break
            time.sleep(0.1)
        pr.wait()
    xong = sum(1 for x in out if x.startswith('XONG'))
    them = [f'DA_DUNG\t\tĐã dừng theo yêu cầu: xong {xong}/{n} file' if x == 'DA_DUNG' else x for x in them]
    loi_text = '\n'.join(err)
    if pr.returncode == 3 or 'KHONG_CO_EXCEL' in loi_text:
        raise LoiIn('Không mở được Microsoft Excel trên máy này: chỉ xuất được file Excel (.xlsx).')
    loi = [x for x in err if x.startswith(('LOI_MO', 'LOI_XUAT'))] + them
    if che_do == 'pdf' and not them:
        for a, b in cap_file:
            if not Path(b).exists() and not any(str(Path(a).resolve()) in x for x in loi):
                loi.append(f'LOI_XUAT\t{a}\tExcel không tạo được file PDF')
    return loi


# ---------------------------------------------------------------- in hàng loạt
def ten_file_ho(con, ma_ho: int) -> str:
    h = con.execute('SELECT thu_tu, ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    ten = ' '.join(str(h['ho_ten'] or '').split())
    # "Nguyễn Văn A là chủ sở hữu tài sản gắn liền với thửa đất số…" (họ tên nhập kèm diễn giải): tên file chỉ lấy phần họ tên
    ten = re.split(r'\s+là\s+(?:chủ|người|đại diện|đồng)\b', ten, maxsplit=1, flags=re.I)[0]
    ten = re.sub(r'[\\/:*?"<>|\r\n\t]+', ' ', ten)[:60].strip()
    return f'PA_{h["thu_tu"]:03d}_ma{ma_ho}_{ten}'


def xuat_hang_loat(con, ds_ma_ho: list, thu_muc, pdf: bool = False, in_may: bool = False, bang_tong_hop: bool = False,
                   bao_tien_do=None, bao_excel=None, so_ban: int = 1) -> dict:
    """Xuất phương án chi tiết từng hộ (+ bảng tổng hợp) ra thư mục. Trả dict(excel=[...], pdf=[...], loi=[...]).
    bao_tien_do(i, n) sau mỗi file Excel, bao_excel(i, n) trong lúc Excel xuất PDF / in: trả True = dừng."""
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    mau = thu_muc_mau()
    bc = BoiCanh.tu(con)
    kq = dict(excel=[], pdf=[], loi=[])
    for i, ma in enumerate(ds_ma_ho, start=1):
        p = lap_chi_tiet(con, ma, thu_muc / f'{ten_file_ho(con, ma)}.xlsx', mau, bc)
        kq['excel'].append(p)
        if bao_tien_do and bao_tien_do(i, len(ds_ma_ho) + (1 if bang_tong_hop else 0)):
            kq['loi'].append(f'DA_DUNG\t\tĐã dừng theo yêu cầu sau {i}/{len(ds_ma_ho)} hộ (chưa xuất PDF / in)')
            return kq
    if bang_tong_hop:
        n = len(ds_ma_ho) + 1
        p = lap_bang_tong_hop(con, thu_muc / 'BANG_TONG_HOP.xlsx', ds_ma_ho, None,
                              bao_tien_do=(lambda i, m: bao_tien_do(n - 1, n)) if bao_tien_do else None)
        kq['excel'].append(p)
    if pdf or in_may:
        cap = [(p, p.with_suffix('.pdf') if pdf else None) for p in kq['excel']]
        kq['loi'] = chay_excel(cap, 'in' if in_may else 'pdf', bao=bao_excel, so_ban=so_ban)
        if pdf:
            kq['pdf'] = [b for _, b in cap if b and Path(b).exists()]
    return kq


def mo_file(p) -> None:
    """Mở file / thư mục bằng chương trình mặc định của Windows."""
    if sys.platform == 'win32':
        os.startfile(str(p))   # noqa: S606

