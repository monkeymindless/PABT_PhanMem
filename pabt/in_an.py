"""Bản in (giai đoạn 3): bảng tổng hợp kinh phí (A3 ngang, Excel) và các hàm dùng chung cho xuất PDF / in qua Excel.

Từ 1.0.20 KHÔNG còn file mẫu Excel nào: bảng tổng hợp dựng hoàn toàn bằng mã (mau_bang_tong_hop.tao_workbook), phương án chi tiết là
bản Word (in_word). Ô có {ten} trong bảng được thay bằng dữ liệu (tên dự án, xã/phường...) ở lap_bang_tong_hop; đổi quy cách in bằng hồ sơ
địa phương (dia_phuong), không đọc lệnh từ file Excel bên ngoài.

Bảng tính được điền bằng openpyxl (số liệu từ nghiep_vu, cùng hàm tính với màn hình); PDF và in ra máy in nhờ
Microsoft Excel trên máy (VBScript gọi Excel, không cần cài thêm thư viện).
"""
from __future__ import annotations
import math
import re
import unicodedata
from copy import copy
from pathlib import Path

from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.styles import Alignment
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange

from . import an_toan as _an_toan
from . import nghiep_vu
from .du_lieu_in import (nhan_du_an, _thong_tin_du_an, bo_lap_mo_dau, chon_lan_in, ghi_chu_in, ky_hieu_cua_ho, tieu_de_muc_i, ten_file_ho)  # noqa: F401 - tên cũ của in_an (mã gọi cũ, test)
from .nghiep_vu import BoiCanh, doc_phuong_an, tinh_pa
from .tien import D, KHONG

TEN_BTH = 'IN_BANGTONGHOP'
DONG_DAU_BTH = 13      # IN_BANGTONGHOP: dòng dữ liệu đầu (mặc định hồ sơ: mau_in.IN_BANGTONGHOP.dong_du_lieu_dau)
from .in_excel import LoiIn  # noqa: E402,F401 - lớp lỗi in qua Excel (in_excel.py), tên cũ in_an.LoiIn


# ---------------------------------------------------------------- đường kẻ (hình vẽ) của mẫu
# openpyxl làm mất hình vẽ khi đọc / ghi: đường kẻ dưới tên cơ quan, dưới quốc hiệu, dưới tên dự án được lưu riêng
# (mau_in/<mẫu>.duong_ke.xml, lấy từ file PABT Excel) và chèn lại vào file bản in sau khi lưu.
# 1.0.28: phần ghi đường kẻ vào file .xlsx tách sang in_duong_ke.py - nhập lại ở đây cho mã gọi cũ (in_an.chen_duong_ke…)
from .in_duong_ke import (_DS_A, _DS_DR, _DS_R, _NET, _ghi_zip, _them_bo_qua_loi, chen_duong_ke,  # noqa: E402,F401
                          doc_duong_ke, ghi_zip_nguyen_tu)


# ---- canh đường kẻ theo chữ phía trên (người dùng yêu cầu 10/10/2026: "đường ngang dưới chữ gần sát, nằm giữa từng nội dung")
EMU_PX, EMU_PT = 9525, 12700
# khoảng từ chân dòng chữ (tính theo phông) tới đường kẻ, theo cỡ chữ - đo trên bản PDF Excel in ra: dòng có dấu nặng / chữ có
# chân (ạ, ộ, ị, g, p, y…) cần xa hơn để đường kẻ không che dấu (người dùng: "hở chữ 1 chút xíu để không che dấu chữ")
DK_CO_DAU_DUOI = 0.20
DK_KHONG_DAU_DUOI = 0.08
DK_DU_AN_CM = 7.0             # đường kẻ dưới dòng "Dự án: …": dài 7 cm, căn giữa dòng chữ (người dùng 12/10/2026)
EMU_CM = 360000
DK_CACH_DU_AN = 3.0              # riêng đường kẻ dưới tên dự án: gần chữ hơn nhưng vẫn hở nhỏ (người dùng 24/10/2026)
DK_CHI_NHANH_NGAN_CM = 1.0     # đường kẻ dưới "CHI NHÁNH …" ngắn hơn chữ 1 cm (người dùng 24/10/2026)
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
            dai = max(rong * 0.3, rong - DK_CHI_NHANH_NGAN_CM * EMU_CM)     # tên đơn vị (CHI NHÁNH…): ngắn hơn chữ 1 cm, căn giữa
        else:
            dai = min(x2 - x1, rong)
        if tot['ngang'] in ('left', 'general', 'justify'):
            giua = tot['x1'] + 2 * EMU_PX + rong / 2
        elif tot['ngang'] == 'right':
            giua = tot['x2'] - 2 * EMU_PX - rong / 2
        else:
            giua = (tot['x1'] + tot['x2']) / 2
        cach = DK_CACH_DU_AN if bo_dau(chu).lower().startswith('du an') else DK_CACH
        nx1, nx2, ny = int(giua - dai / 2), int(giua + dai / 2), int(tot['chan'][-1] + max(cach, tot['co'] * (
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


DAU_DU_THAO = '(DỰ THẢO)'
_RE_DU_THAO = re.compile(r'DỰ\s*THẢO', re.I)


def co_dau_du_thao(ws) -> bool:
    """Mẫu đã có chữ DỰ THẢO ở ô nào đó (người dùng tự đặt vị trí, cỡ chữ trong mẫu chính)."""
    return any(isinstance(o.value, str) and _RE_DU_THAO.search(o.value) for o in getattr(ws, '_cells', {}).values())


def dat_dau_du_thao(ws, ten: str = TEN_BTH) -> None:
    """Bản DỰ THẢO in bằng MẪU CHÍNH (0.9.82 - người dùng 14/10/2026: một mẫu cho cả hai chế độ, không phải giữ hai bộ mẫu):
    mẫu đã có chữ DỰ THẢO -> giữ nguyên; chưa có -> thêm "(DỰ THẢO)" đúng chỗ của mẫu dự thảo gốc: phương án chi tiết = dòng dưới
    "Số: …/…" (cùng ô, như IN_CHITIET_DT); bảng tổng hợp = cuối tiêu đề "BẢNG TỔNG HỢP …". Không tìm được chỗ -> ô "Số:"."""
    o_list = sorted((o for o in getattr(ws, '_cells', {}).values() if isinstance(o.value, str) and o.row <= 12),
                    key=lambda o: (o.row, o.column))
    if ten == TEN_BTH:
        # 1.0.04 (người dùng 19/10/2026): ẩn dòng "(Đính kèm Phương án số …)" - bản dự thảo chưa có số phương án
        for o in o_list:
            if 'đính kèm phương án' in o.value.lower():
                ws.row_dimensions[o.row].hidden = True
    if co_dau_du_thao(ws):
        return
    if ten == TEN_BTH:
        # 1.0.04: "(DỰ THẢO)" ngay dưới đường kẻ chân tên đơn vị (góc trái trên)
        dv =[o for o in o_list if o.column == 1 and o.row <= 4]
        if dv:
            goc = dv[-1]
            r = goc.row + 1
            m = _vung_tron(ws, goc.row, goc.column)
            c1, c2 = (m.min_col, m.max_col) if m else (goc.column, goc.column)
            if all(ws.cell(r, c).value in (None, '') for c in range(c1, c2 + 1)) and _vung_tron(ws, r, c1) is None:
                o = ws.cell(r, c1)
                o.value = DAU_DU_THAO
                o.font = copy(goc.font)
                o.alignment = Alignment(horizontal='center', vertical='bottom', wrap_text=False)
                if c2 > c1:
                    _gop_o(ws, r, c1, r, c2)
                rd = ws.row_dimensions[r]
                rd.height = max(float(rd.height or 15), _phong(goc)[1] * 1.4)
                return
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


def ap_che_do_du_thao(ws, du_thao: bool, ten: str = TEN_BTH) -> None:
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


def _dat_duong_ke(ws, vt_dk) -> str:
    """Đường kẻ dưới tên đơn vị, tiêu ngữ và dòng dự án: sát chân dòng chữ cuối, căn giữa đoạn chữ đó."""
    dk = dk_mac_dinh(ws, vt_dk)
    return can_duong_ke(ws, dk) if (dk or '').strip() else ''


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


def _bo_gop(ws, m) -> None:
    """Bỏ vùng gộp m (lấy từ ws.merged_cells.ranges) như ws.unmerge_cells nhưng không dò lại vùng trong mọi vùng gộp (openpyxl kiểm
    "đã gộp chưa" bằng cách duyệt hết: bảng tổng hợp 3.000 hộ ~20.000 vùng, tách hộ qua trang 1.250 lần = 18 giây)."""
    ds = getattr(ws.merged_cells, 'ranges', None)
    if not isinstance(ds, set) or m not in ds or not hasattr(ws, '_cells'):   # openpyxl khác cấu trúc: cách của openpyxl
        ws.unmerge_cells(m.coord)
        return
    ds.discard(m)
    for r in range(m.min_row, m.max_row + 1):
        for c in range(m.min_col, m.max_col + 1):
            if (r, c) != (m.min_row, m.min_col):
                ws._cells.pop((r, c), None)


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


_RE_CHO_TRONG = re.compile(r'\{([^{}]+)\}')


def _thay_cho_trong(ws, gia_tri: dict):
    """Thay {ten} trong mọi ô chữ của sheet."""
    for c in _o_chu(ws):
        if '{' in c.value:
            c.value = _RE_CHO_TRONG.sub(lambda m: str(gia_tri[m.group(1)]) if m.group(1) in gia_tri else m.group(0), c.value)


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
                    nho: dict | None = None, cot_ho: tuple = COT_CHU_HO_BTH, cot_thua: tuple = COT_CHU_THUA_BTH,
                    nhom: list | None = None) -> None:
    """Bảng tổng hợp: ô họ tên / địa chỉ / nguồn gốc gộp theo số thửa. Excel không tự giãn ô gộp — tăng cao các dòng
    của hộ cho vừa chữ (số dòng chữ đo theo phông, cao_dong_bang: đệm 4 pt trên / dưới), mỗi dòng thửa vẫn đủ chỗ cho
    vị trí; không thấp hơn dòng mẫu và 24 pt; phần thiếu chia đều các dòng, mỗi dòng không quá 409 pt (lap_bang_tong_hop
    đã thêm dòng cho hộ cần cao hơn). nhom [(dòng đầu, dòng cuối)]: các dòng Excel của từng thửa (chữ của thửa ở dòng đầu, ô gộp
    xuống - 21/10/2026); None = mỗi dòng một thửa."""
    n = r - r0
    if n <= 0:
        return
    px = px or _px_cot(ws, 26)
    co = float(ws.cell(r0, cot_ho[0]).font.sz or 14)
    if can is None:
        can = cao_can_ho_bth(ws, r0, px, do, nho, cot_ho)
    mac = max(float(ws.row_dimensions[r0].height or 36), cao_dong_bang(1, co))
    ds = [mac] * n
    for a, b in nhom or [(r0 + i, r0 + i) for i in range(n)]:
        can_t = cao_dong_bang(max(_so_dong_bth(ws, a, c, px, do, nho) for c in cot_thua), co, None)
        for i in range(a - r0, b - r0 + 1):
            ds[i] = max(ds[i], min(CAO_TOI_DA, can_t / (b - a + 1)))
    for _ in range(n):                                  # chia phần thiếu cho các dòng còn dưới trần 409 pt
        thieu = can - sum(ds)
        con = [i for i, c in enumerate(ds) if c < CAO_TOI_DA]
        if thieu <= 0.01 or not con:
            break
        for i in con:
            ds[i] = min(CAO_TOI_DA, ds[i] + thieu / len(con))
    for i, cao in enumerate(ds):
        ws.row_dimensions[r0 + i].height = cao


# ---------------------------------------------------------------- đo chữ để đặt chiều cao dòng vừa khít
# Excel không tự giãn chiều cao ô gộp nhiều cột (tên dự án, nguồn gốc đất) nên phần mềm tự tính: đo bề rộng chữ bằng phông thật
# (Qt, khi đang chạy giao diện) rồi ngắt dòng như Excel; không có Qt thì ước theo số ký tự (dư một chút để không mất chữ).
_MDW = {('Calibri', 11): 7, ('Arial', 10): 7, ('Arial', 11): 8, ('Times New Roman', 11): 7, ('Times New Roman', 12): 8,
        ('Times New Roman', 13): 9, ('Times New Roman', 14): 9}
CAO_TOI_DA = 409                                # chiều cao dòng lớn nhất Excel cho phép (pt)


_DO_CHU_NHANH = {'co_qt': True, 'app': None, 'ham': None}


def _ham_do_chu():
    """Hàm (chữ, tên phông, cỡ pt, đậm) -> bề rộng (pt), hoặc None khi không có giao diện Qt. Nhớ hàm (và các QFontMetricsF của
    nó) theo đối tượng QGuiApplication đang chạy: in hàng loạt gọi hàng nghìn lần không nạp lại / dựng lại phông."""
    if not _DO_CHU_NHANH['co_qt']:
        return None
    try:
        from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication
    except ImportError:
        _DO_CHU_NHANH['co_qt'] = False
        return None
    app = QGuiApplication.instance()
    if not isinstance(app, QGuiApplication):
        return None
    if _DO_CHU_NHANH['ham'] is not None and _DO_CHU_NHANH['app'] is app:
        return _DO_CHU_NHANH['ham']
    bo_dem = {}

    def do(chu: str, ten: str, co: float, dam: bool) -> float:
        k = (ten, co, dam)
        if k not in bo_dem:
            f = QFont(ten)
            f.setPixelSize(max(1, int(round(co * 10))))     # 1 px = 0,1 pt: đo theo pt, không phụ thuộc DPI màn hình
            f.setBold(dam)
            bo_dem[k] = QFontMetricsF(f)
        return bo_dem[k].horizontalAdvance(chu) / 10
    _DO_CHU_NHANH['app'], _DO_CHU_NHANH['ham'] = app, do
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
          noi_tiep: bool = False, so_nbsp: int = 0) -> list:
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
    if so_nbsp > 0:                              # 1.0.04: số NBSP cố định (nguồn gốc đất: 4)
        dau_doan = NBSP * so_nbsp
    elif thut_dau > 0:
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
# 20/10/2026 (người dùng - lỗi "trang 2 mồ côi"): đệm 8 -> 4.0 pt, tối thiểu 24 -> 20 pt (đổi cùng mặc định của VBS xuất PDF)
CAO_DONG_BANG_TOI_THIEU = 20.0
DONG_CHU_14 = 16.5
HE_SO_DONG_EXCEL = 1.3
DEM_DONG = 4.0


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


def _dong_cuoi(ws, so_cot: int) -> int:
    for r in range(ws.max_row, 0, -1):
        if any(ws.cell(r, c).value not in (None, '', ' ') for c in range(1, so_cot + 1)):
            return r
    return 1


# ---------------------------------------------------------------- dữ liệu chung


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


_RE_VA_TRICH_YEU = re.compile(r'(HỖ\s+TRỢ)\s*&\s*(TÁI\s+ĐỊNH\s+CƯ)', re.I)


def chuan_trich_yeu(ws, den_dong: int | None = None) -> int:
    """Trích yếu "BỒI THƯỜNG, HỖ TRỢ & TÁI ĐỊNH CƯ…" -> "… HỖ TRỢ VÀ TÁI ĐỊNH CƯ…" (thể thức NĐ 30 không dùng ký tự "&" - người dùng
    21/10/2026; mẫu chuẩn và mẫu người dùng thay đều có chữ "&"). Trả số ô đã sửa."""
    n = 0
    for o in list(_o_chu(ws, den_dong)):
        moi = _RE_VA_TRICH_YEU.sub(lambda m: m.group(1) + (' VÀ ' if m.group(1).isupper() else ' và ') + m.group(2), o.value)
        if moi != o.value:
            o.value = moi
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
        # số tổng chỉ đo khi dòng TỔNG CỘNG có số / công thức ở cột này (22/10/2026: cột STT bị nới theo tổng các số thứ tự - ô đó
        # là chữ "TỔNG CỘNG" / trống)
        v_tong = getattr(o_co.get((tong, c)), 'value', None)
        co_tong = (isinstance(v_tong, (int, float)) and not isinstance(v_tong, bool)) or str(v_tong or '').startswith('=')
        ds = [(_chu_so_excel(v, fmt), ws.cell(d0, c)) for v in {max(so), min(so)}] + \
            ([(_chu_so_excel(sum(so), fmt), ws.cell(tong, c))] if co_tong else [])
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


# ---------------------------------------------------------------- dàn trang thích ứng (người dùng 16/10/2026)
# Cả hai bản in: lề trang cân đối, tỷ lệ in vừa bề ngang (tắt "vừa N trang" - Excel bỏ qua ngắt trang tay khi bật), xếp trang theo
# cụm không được tách (tiêu đề bảng + dòng đầu, dòng mục + dòng con, hộ ít thửa, cụm tổng cộng + chữ ký), nén khít khi trang cuối
# chỉ tràn ít, giãn đều khi đáy trang hở vừa phải, rồi GHI ngắt trang tay ở cuối MỌI trang (Excel in đúng như phần mềm đã xếp).
# Đo bằng Excel thật (16/10/2026): sức chứa một trang = đúng chiều cao vùng in (38 dòng x 20 pt = 760 pt trên 762,8 pt A4 dọc, lề
# 0,55"); dòng tiêu đề lặp (print_title_rows) chỉ in ở đầu các trang BẮT ĐẦU SAU dòng tiêu đề.
# 1.0.07 (người dùng 20/10/2026): phương án chi tiết A4 dọc lề trái 0,8 cm, phải 0,3 cm, trên 1,0 cm, dưới 0,8 cm (inch = cm / 2,54);
# tỷ lệ in cố định TI_LE_CT (72%, được thu tới TI_LE_CT_MIN 70% khi chỉ tràn ít - canh_trang_in_an.gom_mot_trang)
CM = 1 / 2.54
LE_TRANG = {'chi_tiet': dict(top=round(1.0 * CM, 3), bottom=round(0.8 * CM, 3), left=round(0.8 * CM, 3), right=round(0.3 * CM, 3),
                             header=0.2, footer=0.2),
            # 22/10/2026 (người dùng): bảng tổng hợp A3 ngang lề trái 2,0 cm, phải 1,0 cm (nhỏ hơn lề trái 1 cm), trên / dưới 1,5 cm
            'tong_hop': dict(top=round(1.5 * CM, 4), bottom=round(1.5 * CM, 4), left=round(2.0 * CM, 4), right=round(1.0 * CM, 4),
                             header=0.20, footer=0.20)}
GIAY_DOC = {8: (842.0, 1191.0), 9: (595.0, 842.0)}     # A3, A4 dọc (pt); mã paperSize của Excel
RONG_DU_PHONG = 0.96            # bề rộng vùng in dùng được khi tính tỷ lệ vừa ngang (dat_ti_le_vua_ngang)
DU_PHONG_TRANG = 0.98           # chừa 2% chiều cao trang (Excel làm tròn chiều cao dòng; AutoFit khi xuất PDF có thể nhích dòng)
NEN_DEM = min(3.5, DEM_DONG * 0.5)   # nén khít: bớt đệm dòng bảng (20/10/2026: đệm 2 pt -> 1 pt)
CAO_NEN_TOI_THIEU = 19.0        # nén khít: dòng một dòng chữ không thấp hơn (20/10/2026: 20,5 -> 19)
NEN_TOI_DA = 0.14               # chỉ nén khi phần tràn sang trang cuối <= 14% chiều cao trang
GIAN_TU, GIAN_DEN = 0.08, 0.22  # giãn cân đối khi đáy trang hở 8% - 22%
GIAN_MOI_DONG = 3.0             # giãn tối đa mỗi dòng (pt)
CON_CHO_HO_LON = 85.0           # hộ nhiều thửa: trang còn >= 85 pt (~3 dòng thửa) thì bắt đầu ngay, không đẩy cả hộ sang trang
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


def dat_ti_le_vua_ngang(ws, n_cot: int, du_phong: float = RONG_DU_PHONG) -> int:
    """Tỷ lệ in (scale %) vừa khít tổng bề rộng các cột hiện (1..n_cot) trên khổ giấy của mẫu; TẮT fitToPage (Excel bỏ qua ngắt trang
    tay khi in "vừa N trang"). Trả tỷ lệ."""
    from openpyxl.worksheet.properties import PageSetupProperties
    rong_pt = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75
    w, _ = _kho_giay(ws)
    m = ws.page_margins
    in_rong = w - ((m.left or 0) + (m.right or 0)) * 72
    # Excel (đo 16/10/2026 bằng xuất PDF): bảng 683 pt ở 75% = 512 pt vẫn bị tách cột Ghi chú sang trang riêng trên khổ in 523 pt,
    # 73% thì không - bề rộng dùng được thấp hơn lý thuyết ~3%: chừa RONG_DU_PHONG
    ty_le = max(10, min(100, int(in_rong * du_phong / rong_pt * 100))) if rong_pt > 0 else 100
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


def _tach_gop_doc(ws, c: int, e: int, chi_muc: dict | None = None):
    """Vùng gộp dọc ở cột c phủ hai dòng e và e + 1: tách thành [đầu..e] và [e + 1..cuối] (gộp lại nếu > 1 dòng). Trả (đầu, cuối)
    của vùng cũ hoặc None."""
    m = _vung_tron(ws, e, c, chi_muc)
    if m is None or m.max_row <= e or m.min_col != m.max_col:
        return None
    a, b = m.min_row, m.max_row
    kieu = copy(ws.cell(a, c)._style)
    _bo_gop(ws, m)
    ws.cell(e + 1, c)._style = copy(kieu)
    for r1, r2 in ((a, e), (e + 1, b)):
        if r2 > r1:
            _gop_o(ws, r1, c, r2, c)
        else:
            ws.cell(r1, c)._style = copy(kieu)
    return a, b


def ngat_trang_bth(ws, khoi_ho: list, tong: int, n_cot: int, cuoi: int | None = None, dong_tieu_de: tuple = (9, 12),
                   san: dict | None = None, san_khoi: tuple = (), cam: set | None = None, tach_ho=None,
                   ti_le: int | None = None) -> list:
    """Dàn trang bảng tổng hợp (người dùng 16/10/2026). Lề chuẩn, tỷ lệ vừa ngang, hàng tiêu đề (dong_tieu_de) lặp đầu trang. 21/10/2026
    (người dùng: trang trước còn trống nhiều đã ngắt): MỖI DÒNG EXCEL (dòng thửa; chữ cao chia nhiều dòng - lap_bang_tong_hop,
    CAO_KHOI_BTH) là một đơn vị tự do - chỉ sang trang khi dòng kế không vừa chỗ còn lại; cam: dòng KHÔNG được ngắt sau. Ngắt giữa một
    hộ: tach_ho(r0, r1, e) tách các vùng gộp của hộ ở ranh trang (lặp STT / họ tên, chia chữ nguồn gốc). Chữ ký đi liền dòng TỔNG
    CỘNG cuối; trang cuối luôn có ít nhất một dòng của hộ (không để dòng tổng + chữ ký đứng trơ). Nén khít / giãn cân đối
    (co_gian_vua_trang). ti_le: tỷ lệ in cố định (1.0.07: 55% A3 - dat_ti_le_co_dinh); None = vừa bề ngang. Trả các dòng đã ngắt
    (ngắt SAU dòng)."""
    chuan_le_trang(ws, 'tong_hop')
    if ti_le:                                       # 22/10/2026: cùng dự phòng với lap_day_ngang_a3_bth (bảng sát lề phải)
        dat_ti_le_co_dinh(ws, n_cot, ti_le, RONG_DU_PHONG_BTH)
    else:
        dat_ti_le_vua_ngang(ws, n_cot)
    cap = cao_trang_in(ws)
    cuoi = cuoi or _dong_cuoi(ws, n_cot)
    cam = cam or set()
    d0 = khoi_ho[0][0] if khoi_ho else tong

    doan_dl = []                                        # đoạn không tách của phần dữ liệu (mỗi dòng; dòng trong cam dính dòng sau)
    for r0, r1 in khoi_ho:
        a = r0
        for r in range(r0, r1 + 1):
            if r not in cam or r == r1:
                doan_dl.append((a, r))
                a = r + 1
    # dòng TỔNG CỘNG cuối (dưới các dòng kinh phí / phân bổ) - chữ ký đi liền nó; các dòng tổng / kinh phí phía trên là dòng tự do
    r_tc = max((r for r in range(tong, min(tong + 8, cuoi) + 1)
                if any('TỔNG CỘNG' in str(ws.cell(r, c).value or '').upper() for c in range(1, n_cot + 1))), default=tong)
    doan_dl += [(r, r) for r in range(tong, r_tc)]

    def lap_khoi(lien_tu):
        return [('tu_do', [(r, r) for r in range(1, d0)]), ('tu_do', [x for x in doan_dl if x[1] < lien_tu]),
                ('lien', [(lien_tu, cuoi)])]
    # trang cuối nên có ít nhất một dòng của hộ (kéo thêm dòng trước vào cụm cuối) - nhưng chỉ khi trang trước vẫn lấp >= TRANG_DAY
    # (người dùng 21/10/2026: không ngắt khi trang chưa đầy 85%); không được thì trang cuối bắt đầu từ dòng TỔNG CỘNG cuối + chữ ký
    lien_tu, ung = r_tc, r_tc
    for _ in range(40):
        t = xep_trang(ws, lap_khoi(ung), cap, dong_tieu_de)
        if len(t) == 1 or not khoi_ho:
            lien_tu = ung
            break
        day = t[-2][2] >= TRANG_DAY * cap
        if t[-1][0] < tong and day:
            lien_tu = ung
            break
        truoc = [x[0] for x in doan_dl if x[0] < ung]
        if not truoc or t[-1][0] < tong:                # đã có dòng hộ mà trang trước hở: giữ cụm cuối từ dòng TỔNG CỘNG
            break
        ung = max(truoc)
    khoi = lap_khoi(lien_tu)
    dong_du_lieu = list(range(d0, tong))
    trang, da_nen = co_gian_vua_trang(ws, khoi, cap, dong_tieu_de, dong_du_lieu, san, san_khoi, set(dong_du_lieu))
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


RONG_COT_TIEN_BTH = 14.0        # 1.0.04: cột tiền 12..18 của bảng tổng hợp rộng tối thiểu (tiêu đề không rớt chữ dọc)
COT_TIEN_BTH = ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong', 'tong')


# ---------------------------------------------------------------- bảng tổng hợp A3 ngang 55% (người dùng 20/10/2026, 1.0.07)
# Mẫu cũ: A4 ngang, chữ 20 pt, "vừa bề ngang" -> in ra ~20-27% (chữ ~5 pt). Nay: A3 ngang, tỷ lệ CỐ ĐỊNH 55%, nội dung 14 pt, tiêu đề
# (quốc hiệu, tiêu ngữ, tên cơ quan, tên bảng, dự án, hàng tiêu đề cột) 16 pt đậm; mẫu chữ to hơn thì thu cột / dòng theo tỷ lệ chữ,
# rồi chia lại bề rộng cột chữ cho vừa đúng khổ A3 ở 55%. Chỉ khi cột số vẫn không vừa (số tiền rất lớn) mới in nhỏ hơn 55%.
KHO_GIAY_BTH = 8                # mã paperSize Excel: 8 = A3 (297 x 420 mm)
TI_LE_BTH = 55                  # tỷ lệ in (%)
TI_LE_BTH_MIN = 50              # VBS xuất PDF / in được thu tỷ lệ tới mức này khi Excel tự ngắt trang (dải 50 - 55%)
CO_NOI_DUNG = 14.0              # cỡ chữ nội dung
CO_TIEU_DE = 16.0               # cỡ chữ tiêu đề (đậm)
TEN_GIU_TI_LE = 'PABT_GIU_TI_LE'     # VBS xuất PDF / in: không thu tỷ lệ in khi Excel tự ngắt trang
RONG_CHU_TOI_THIEU_BTH = 8.0    # cột chữ (họ tên, địa chỉ, nguồn gốc…) không hẹp hơn khi thu cho vừa khổ


def dat_kho_a3(ws, ti_le: int = TI_LE_BTH) -> None:
    """A3 ngang, tắt mọi chế độ "vừa N trang" của Excel, tỷ lệ in cố định ti_le."""
    from openpyxl.worksheet.properties import PageSetupProperties
    ws.page_setup.paperSize = KHO_GIAY_BTH
    ws.page_setup.orientation = 'landscape'
    if ws.sheet_properties.pageSetUpPr is None:
        ws.sheet_properties.pageSetUpPr = PageSetupProperties()
    ws.sheet_properties.pageSetUpPr.fitToPage = False
    ws.page_setup.fitToWidth = None
    ws.page_setup.fitToHeight = None
    ws.page_setup.scale = int(ti_le)


def gian_dong_dau_bth(ws) -> None:
    """Giãn dòng phần đầu bảng tổng hợp (người dùng 24/10/2026: "kiểm tra lại độ giãn dòng"): dòng 1 (cơ quan chủ quản) sát chữ,
    dòng 2 ("CHI NHÁNH …" + đường kẻ cách chữ DK_CACH) vừa đủ chỗ kẻ - trước đây cả hai cao ~1,9 lần cỡ chữ."""
    co = _phong(ws.cell(1, 1))[1]
    ws.row_dimensions[1].height = round(cao_dong_chu(1, co) + 2, 1)
    ws.row_dimensions[2].height = round(cao_dong_chu(1, co) + DK_CACH + 5, 1)       # +5: đường kẻ + khe trước dòng "(DỰ THẢO)" / dòng kế


def chuan_co_chu_bth(ws, d0: int) -> float:
    """Cỡ chữ bảng tổng hợp: phía trên dòng dữ liệu đầu d0 (tiêu đề văn bản + hàng tiêu đề cột) ô đậm 16 pt, ô thường 14 pt; từ d0 trở
    xuống 14 pt (giữ đậm / nghiêng). Mẫu chữ to (mẫu cũ 20 pt): thu bề rộng cột và chiều cao dòng theo cùng tỷ lệ 14 / cỡ cũ. Trả tỷ lệ."""
    from openpyxl.utils import get_column_letter
    co_goc = float(ws.cell(d0, 2).font.sz or 0) or max((float(o.font.sz or 0) for o in ws._cells.values() if o.row >= d0),
                                                      default=CO_NOI_DUNG)
    he = CO_NOI_DUNG / co_goc if co_goc > CO_NOI_DUNG + 0.5 else 1.0
    for o in list(ws._cells.values()):
        if not o.has_style or not o.font or not o.font.sz:
            continue
        moi = (CO_TIEU_DE if o.font.b else CO_NOI_DUNG) if o.row < d0 else CO_NOI_DUNG
        if float(o.font.sz) != moi:
            f = copy(o.font)
            f.sz = moi
            o.font = f
    if he < 1:
        for c in range(1, 200):
            cd = ws.column_dimensions.get(get_column_letter(c))
            if cd is not None and cd.width and not cd.hidden:
                cd.width = round(float(cd.width) * he, 2)
        for rd in ws.row_dimensions.values():
            if rd.height:
                rd.height = round(float(rd.height) * he, 2)
        if ws.sheet_format.defaultRowHeight:
            ws.sheet_format.defaultRowHeight = round(float(ws.sheet_format.defaultRowHeight) * he, 2)
    return he


def rong_in_a3(ws, ti_le: int = TI_LE_BTH, du_phong: float = RONG_DU_PHONG) -> float:
    """Tổng bề rộng cột (pt theo sheet) vừa khổ in ở tỷ lệ ti_le (lề trang của sheet, chừa du_phong)."""
    w, _ = _kho_giay(ws)
    m = ws.page_margins
    return (w - ((m.left or 0) + (m.right or 0)) * 72) * du_phong / (ti_le / 100)


# 22/10/2026 (người dùng: bảng tổng hợp A3 còn khoảng trắng rộng bên phải): bảng kéo sát lề phải - phần bề rộng còn hụt so với vùng in
# chia cho cột nguồn gốc / họ tên / địa chỉ. Chừa RONG_DU_PHONG_BTH (không 100%): Excel đo cột lúc in theo điểm ảnh làm tròn, vừa khít
# thì cột cuối bị đẩy sang trang riêng. Đo 22/10/2026 bằng Excel xuất PDF (A3 ngang 55%, lề 2 / 1 cm, 51 hộ): 0,99 và 0,98 -> Excel
# tách cột (4 trang thay 2); 0,975 vừa đủ; chọn 0,97 có biên an toàn (viền phải bảng cách lề phải ~3,7 mm)
RONG_DU_PHONG_BTH = 0.97
CHIA_BU_NGANG_BTH = (('nguon_goc', 0.70), ('ho_ten', 0.15), ('dia_chi', 0.15))
CHUA_SAU_BTH = 3.0              # pt chừa cho cột số nhích thêm sau khi điền (vua_cot_so_bth)


def lap_day_ngang_a3_bth(ws, n_cot: int, cot: dict, ti_le: int = TI_LE_BTH) -> float:
    """Sau khi chia / thu cột (vua_ngang_a3_bth, thu_cot_khong_bth): tổng bề rộng các cột hiện còn hụt so với vùng in A3 ở ti_le thì
    cộng bù theo CHIA_BU_NGANG_BTH (cot {khóa: số cột}) - viền phải cột cuối sát lề phải. Không thu cột (thừa thì dat_ti_le_co_dinh
    in nhỏ hơn). Trả bề rộng đã cộng (pt)."""
    from openpyxl.utils import get_column_letter
    tong = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75
    # tỷ lệ in sẽ dùng (dat_ti_le_co_dinh): ti_le, hoặc nhỏ hơn khi bảng vốn rộng hơn khổ ở ti_le (cột số / tiêu đề) - lấp theo tỷ lệ đó
    ti_le = min(int(ti_le), max(10, int(rong_in_a3(ws, 100, RONG_DU_PHONG_BTH) / tong * 100))) if tong > 0 else int(ti_le)
    # chừa CHUA_SAU_BTH pt: vua_cot_so_bth (sau khi điền số) có thể nhích cột số dòng TỔNG CỘNG; tỷ lệ vừa ngang làm tròn xuống
    thieu = rong_in_a3(ws, ti_le, RONG_DU_PHONG_BTH) - CHUA_SAU_BTH - tong
    if thieu < 1:
        return 0.0
    mdw = _mdw(ws.parent)
    nhan = [(ws.column_dimensions.get(get_column_letter(cot[k])), ty) for k, ty in CHIA_BU_NGANG_BTH if k in cot]
    nhan = [(cd, ty) for cd, ty in nhan if cd is not None and not cd.hidden and cd.width]
    tong_ty = sum(ty for _, ty in nhan)
    for cd, ty in nhan:
        cd.width = round(float(cd.width) + thieu * ty / tong_ty / 0.75 / mdw, 2)
    return sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75 - tong


def vua_ngang_a3_bth(ws, n_cot: int, cot_chu: tuple, cot_so: dict | None = None, d0: int | None = None, do=None,
                     toi_thieu: dict | None = None) -> float:
    """Chia bề rộng cột cho vừa đúng khổ A3 ở TI_LE_BTH: cột số (cot_so {cột: số lớn nhất}) nới cho đủ số trước, rồi các cột chữ
    cot_chu co / giãn theo tỷ lệ bề rộng của chúng (không dưới RONG_CHU_TOI_THIEU_BTH, không dưới toi_thieu {cột: rộng} - từ dài nhất
    của tiêu đề cột). Gọi TRƯỚC khi tính chiều cao dòng. Trả tổng bề rộng (pt) sau khi chia."""
    toi_thieu = toi_thieu or {}
    from openpyxl.utils import get_column_letter
    for c, v in (cot_so or {}).items():
        cd = ws.column_dimensions.get(get_column_letter(c))
        if cd is None or cd.hidden or v is None or d0 is None:
            continue
        can = _rong_can_so(ws.cell(d0, c), v, do, dam=True)
        if float(cd.width or 0) < can:
            cd.width = can
    mdw = _mdw(ws.parent)
    tong = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75
    muc_tieu = rong_in_a3(ws) * 0.99                    # dư 1%: tỷ lệ vừa ngang làm tròn xuống không dưới 55
    chu = []
    for c in cot_chu:
        cd = ws.column_dimensions.get(get_column_letter(c))
        if cd is not None and not cd.hidden and cd.width and not (cd.min and cd.max and cd.min != cd.max):
            # không thu cột chữ dưới một nửa bề rộng hiện có (chữ vỡ từng từ): số quá lớn thì thà in nhỏ hơn 55% (dat_ti_le_co_dinh)
            chu.append((cd, max(RONG_CHU_TOI_THIEU_BTH, float(toi_thieu.get(c, 0)), float(cd.width) * 0.5)))
    if not chu:
        return tong
    for _ in range(4):                                  # cột chạm mức tối thiểu: chia lại phần còn thiếu cho các cột khác
        lech_pt = muc_tieu - tong
        if abs(lech_pt) < 1:
            break
        co_the = [(cd, m) for cd, m in chu if lech_pt > 0 or float(cd.width) > m + 0.05]
        tong_rong = sum(float(cd.width) for cd, _ in co_the)
        if not co_the or tong_rong <= 0:
            break
        lech_don_vi = lech_pt / 0.75 / mdw
        for cd, m in co_the:
            cd.width = round(max(m, float(cd.width) + lech_don_vi * float(cd.width) / tong_rong), 2)
        tong = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75
    return tong


def vua_cao_chu(ws, r1: int, r2: int, n_cot: int, do=None, dem: float = 6.0) -> int:
    """Các dòng r1..r2 (tiêu đề văn bản, hàng tiêu đề cột) đủ cao cho chữ (đo theo phông, bề rộng vùng gộp): chỉ NỚI. Vùng gộp nhiều
    dòng thiếu cao thì nới dòng cuối của vùng. Trả số dòng đã nới."""
    cao = _ham_cao(ws)
    gop = {(m.min_row, m.min_col): m for m in ws.merged_cells.ranges if r1 <= m.min_row <= r2}
    vung = []
    for o in _o_chu(ws, r2):
        if o.row < r1 or o.column > n_cot or not o.value.strip():
            continue
        m = gop.get((o.row, o.column))
        a, b = (m.min_row, m.max_row) if m else (o.row, o.row)
        c1, c2 = (m.min_col, m.max_col) if m else (o.column, o.column)
        ten, co, dam = _phong(o)
        n = so_dong_o(o.value.rstrip('\n'), _rong_vung(ws, c1, min(c2, n_cot)), ten, co, dam, do)
        vung.append((b - a, a, b, n * dong_chu_bang(co) + dem))
    da = set()
    for _, a, b, can in sorted(vung):                   # vùng một dòng trước, vùng gộp nhiều dòng sau
        co_san = sum(cao(r) for r in range(a, b + 1))
        if co_san + 0.1 < can:
            ws.row_dimensions[b].height = min(CAO_TOI_DA, round(cao(b) + can - co_san, 1))
            da.add(b)
    return len(da)


def vua_cot_theo_tieu_de(ws, r1: int, r2: int, n_cot: int, do=None, lay_tu: int | None = None) -> dict:
    """Cột hẹp hơn TỪ dài nhất của chữ tiêu đề (ô một cột trong dòng r1..r2 - "STT", "Phương án…") thì nới cho từ không bị cắt đôi
    (chữ tiêu đề 16 pt, 1.0.07); phần nới lấy bớt ở cột lay_tu (cột rộng nhất - Ghi chú) để tổng bề rộng không đổi. Trả {cột: bề rộng
    tối thiểu theo tiêu đề} của mọi cột đã đo (để bước chia bề rộng sau không thu nhỏ hơn)."""
    from openpyxl.utils import get_column_letter
    do = do or _ham_do_chu() or (lambda t, ten, co, dam: len(t) * co * (0.6 if dam else 0.52))
    mdw = _mdw(ws.parent)
    gop = {(m.min_row, m.min_col) for m in ws.merged_cells.ranges if m.min_col != m.max_col}
    can = {}
    for o in _o_chu(ws, r2):
        if o.row < r1 or o.column > n_cot or (o.row, o.column) in gop or not o.value.strip():
            continue
        ten, co, dam = _phong(o)
        w = max(do(t, ten, co, dam) for t in o.value.split())
        can[o.column] = max(can.get(o.column, 0), round((w * 1.05 + 6) / 0.75 / mdw + 0.2, 2))
    them = 0.0
    for c, rong in can.items():
        cd = ws.column_dimensions[get_column_letter(c)]
        if cd.hidden or c == lay_tu or float(cd.width or 0) >= rong:
            continue
        them += rong - float(cd.width or 0)
        cd.width = rong
    if lay_tu and them > 0:
        cd = ws.column_dimensions[get_column_letter(lay_tu)]
        if cd.width:
            cd.width = round(max(float(cd.width) * 0.5, float(cd.width) - them), 2)
    return can


def dat_ti_le_co_dinh(ws, n_cot: int, ti_le: int = TI_LE_BTH, du_phong: float = RONG_DU_PHONG) -> int:
    """Tỷ lệ in cố định ti_le (tắt "vừa N trang"); bảng vẫn rộng hơn khổ in ở ti_le (số rất lớn) thì lấy tỷ lệ vừa bề ngang - không để
    Excel tách cột sang trang riêng. Trả tỷ lệ đã đặt."""
    vua = dat_ti_le_vua_ngang(ws, n_cot, du_phong)
    ws.page_setup.scale = min(int(ti_le), vua)
    return int(ws.page_setup.scale)


def tien_dat_theo_thua_bth(pa, thua: list, kq, bc) -> dict | None:
    """{mã thửa: tiền đất} của hộ nhiều thửa - cột tiền đất in riêng từng dòng thửa (22/10/2026). None khi không chia được đúng:
    có dòng đất không thuộc thửa nào của hộ, hoặc cộng các thửa khác tiền đất của hộ (cột giữ một ô gộp theo hộ như cũ)."""
    ma = {t['ma_thua'] for t in thua}
    tien = {m: KHONG for m in ma}
    for d in pa.dat:
        if d.ma_thua not in ma:
            return None
        tien[d.ma_thua] += nghiep_vu.thanh_tien_dong_dat(d, bc)
    return tien if sum(tien.values(), KHONG) == kq.muc[1] else None


def _chia_dinh_dang(fmt: str) -> list:
    """Tách định dạng số Excel theo ';' (bỏ qua ';' trong ngoặc kép / sau dấu '\\')."""
    phan, cur, trong_nhay, i = [], '', False, 0
    while i < len(fmt):
        ch = fmt[i]
        if ch == '\\' and i + 1 < len(fmt):
            cur += fmt[i:i + 2]
            i += 2
            continue
        if ch == '"':
            trong_nhay = not trong_nhay
        if ch == ';' and not trong_nhay:
            phan.append(cur)
            cur = ''
        else:
            cur += ch
        i += 1
    phan.append(cur)
    return phan


def dinh_dang_so_gach(fmt: str) -> str:
    """Định dạng số: phần số 0 hiện "-" (dòng hộ của bảng tổng hợp - 1.0.04). Định dạng kế toán đã có phần 0 dạng gạch: giữ."""
    fmt = fmt or 'General'
    if fmt == 'General':
        return '#,##0.0##;-#,##0.0##;"-"'
    p = _chia_dinh_dang(fmt)
    if len(p) >= 3:
        if '-' in p[2] and '0' not in p[2].replace('\\-', ''):
            return fmt
        p[2] = '"-"'
        return ';'.join(p)
    am = p[1] if len(p) > 1 else '-' + p[0]
    return ';'.join([p[0], am, '"-"'])


def dinh_dang_so_khong(fmt: str) -> str:
    """Định dạng số: phần số 0 hiện "0" (dòng tổng cộng - 1.0.04)."""
    fmt = fmt or 'General'
    if fmt == 'General':
        return fmt
    p = _chia_dinh_dang(fmt)
    if len(p) < 3:
        return fmt
    p[2] = re.sub(r'#,##0(\.[0#]+)?', '0', p[0]) if re.search(r'#,##0', p[0]) else '0'
    return ';'.join(p)


def rut_gon_don_vi(ten: str) -> str:
    """Tên đơn vị dài có "Chi nhánh" -> chữ đầu phần trước + "Chi nhánh …" ("Tên Đơn Vị Tỉnh X - Chi nhánh Y"
    -> "TĐV Chi nhánh Y"); không có "Chi nhánh" thì giữ nguyên. Không ghi cố định tên đơn vị nào (1.0.04)."""
    s = ' '.join(str(ten or '').split())
    m = re.search(r'(?i)\bchi nhánh\b', s)
    if not m or m.start() == 0:
        return s
    truoc = s[:m.start()].strip(' -–,')
    truoc = re.split(r'(?i)\s(?:tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s', ' ' + truoc + ' ')[0].strip()
    tat = ''.join(w[0].upper() for w in truoc.split() if w[0].isalpha())
    return f'{tat} {s[m.start():]}'.strip() if len(tat) >= 2 else s


def nguon_goc_cua_thua(chu: str, so_thua, so_to='') -> str:
    """Đoạn nguồn gốc của MỘT thửa (bảng tổng hợp, hộ nhiều thửa - 1.0.04): chữ có nhiều đoạn, mỗi đoạn nói về thửa nào ("Thửa
    16…", "Thửa đất số 17, tờ …") -> chỉ các đoạn nói về thửa so_thua (+ đoạn chung không nhắc thửa nào đứng đầu); chữ không chia
    theo thửa thì giữ nguyên. Khử lặp cụm mở đầu (bo_lap_mo_dau)."""
    doan = [bo_lap_mo_dau(x.strip()) for x in str(chu or '').replace(' ', '\n').split('\n') if x.strip()]
    if not doan:
        return ''
    so = str(so_thua or '').strip()
    re_thua = re.compile(r'(?i)thửa(?:\s+đất)?(?:\s+số)?\s*([0-9]+[a-z]?)')

    def thua_cua(d):
        return {x.lower() for x in re_thua.findall(d)}
    co_thua = [thua_cua(d) for d in doan]
    if not so or not any(co_thua):
        return '\n'.join(doan)
    rieng = [d for d, t in zip(doan, co_thua) if so.lower() in t]
    if not rieng:
        return '\n'.join(d for d, t in zip(doan, co_thua) if not t) or '\n'.join(doan)
    chung = []
    for d, t in zip(doan, co_thua):             # đoạn chung (không nhắc thửa) đứng trước đoạn riêng đầu tiên
        if t:
            break
        chung.append(d)
    return '\n'.join(chung + rieng)


def tach_nguon_goc_theo_thua(ds: list) -> list | None:
    """ds [(nguồn gốc đã chuẩn, số thửa, số tờ)] các thửa của một hộ -> [nguồn gốc riêng từng thửa] hoặc None (không tách: in một
    ô gộp như trước). Tách khi các thửa ghi nguồn gốc khác nhau, hoặc cùng một chữ chung mà mọi thửa đều có đoạn riêng nhắc số
    thửa của nó ("Thửa 16: …", "Thửa đất số 17, tờ …: …")."""
    if len(ds) < 2:
        return None
    chu = [x[0] or '' for x in ds]
    if len({c for c in chu if c.strip()}) > 1:
        return [nguon_goc_cua_thua(c, so, to) for c, so, to in ds]
    re_thua = re.compile(r'(?i)thửa(?:\s+đất)?(?:\s+số)?\s*([0-9]+[a-z]?)')
    doan = [d for d in (chu[0] or '').replace(' ', '\n').split('\n') if d.strip()]
    co = [{x.lower() for x in re_thua.findall(d)} for d in doan]
    if all(any(str(so).strip().lower() in s for s in co) for _, so, _ in ds if str(so).strip()) and \
            all(str(so).strip() for _, so, _ in ds):
        return [nguon_goc_cua_thua(c, so, to) for c, so, to in ds]
    return None


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


# 21/10/2026 (người dùng - bảng tổng hợp tràn trang, trang trước còn trống nhiều): cột số toàn 0 / "-" thu hẹp nhường cho cột nguồn gốc;
# chữ riêng một thửa / chữ gộp theo hộ cao hơn CAO_KHOI_BTH chia thành nhiều dòng Excel (gộp ô - trông vẫn một dòng) để xếp trang theo
# từng dòng (dòng Excel không cắt đôi qua hai trang được: trước đây dòng thửa 415 pt nhảy cả sang trang sau, trang trước còn 23%)
COT_THU_BTH = ('dt_nong_nghiep', 'dt_lua', 'dt_phi_nong_nghiep', 'dt_o', 'tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi',
               'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong')
RONG_COT_KHONG_BTH = 7.0        # cột số toàn 0 thu tới chừng này (đơn vị độ rộng Excel) - không làm chữ tiêu đề cột thêm dòng
CAO_KHOI_BTH = 180.0            # một dòng Excel của bảng tổng hợp không cao hơn (pt): ~13% trang A3 ở 55% - trang lấp >= 85%
TRANG_DAY = 0.85                # trang (trừ trang cuối) phải lấp ít nhất chừng này chiều cao vùng in
HE_SO_TU_TIEU_DE = 1.1          # cột thu hẹp: rộng hơn từ dài nhất của tiêu đề 10% (Excel vẽ chữ đậm rộng hơn khi đo)


def _dt_thua_bth(pa, ma_thua) -> tuple:
    """Diện tích (nông nghiệp, trong đó lúa, đất ở, phi nông nghiệp khác) các dòng mục 1 của một thửa."""
    dat = [d for d in pa.dat if d.ma_thua == ma_thua]
    nn = sum((d.dien_tich for d in dat if d.nhom_dat == 'Nông nghiệp'), KHONG)
    lua = sum((d.dien_tich for d in dat if d.nhom_dat == 'Nông nghiệp' and d.loai_dat.upper() in ('LUC', 'LUK')), KHONG)
    o = sum((d.dien_tich for d in dat if d.nhom_dat == 'Đất ở'), KHONG)
    pnn = sum((d.dien_tich for d in dat if d.nhom_dat == 'Phi nông nghiệp'), KHONG)
    return nn, lua, o, pnn


def _tien_ho_bth(pa, kq, bc) -> dict:
    """Số tiền từng cột của một hộ trên bảng tổng hợp + 'khac' (hỗ trợ khác ngoài đào tạo / ổn định - ghi chú)."""
    dao_tao = sum((nghiep_vu.thanh_tien_dong(d, bc) for d in pa.dong_ho_tro('CS9', 'CS10')), KHONG)
    on_dinh = sum((nghiep_vu.thanh_tien_dong(d, bc) for d in pa.dong_ho_tro(*nghiep_vu.tap_ma_on_dinh())), KHONG)
    return dict(tien_dat=kq.muc[1], tien_tai_san=kq.muc[2], tien_cay_vat_nuoi=kq.muc[3] + kq.muc[nghiep_vu.MUC_VN],
                ho_tro_dao_tao=dao_tao, ho_tro_on_dinh=on_dinh, thuong=kq.muc[5], tong=kq.tong,
                khac=kq.muc[4] - dao_tao - on_dinh)


def tong_cot_bth(khoi: list, bc) -> dict:
    """{trường cột số: tổng trị tuyệt đối cả bảng} - khoi [(mã hộ, phương án, kết quả, thửa)] như lap_bang_tong_hop."""
    tong = {k: KHONG for k in COT_THU_BTH}
    for _, pa, kq, thua in khoi:
        for k, v in _tien_ho_bth(pa, kq, bc).items():
            if k in tong:
                tong[k] += abs(v)
        for t in thua:
            nn, lua, o, pnn = _dt_thua_bth(pa, t['ma_thua'])
            for k, v in (('dt_nong_nghiep', nn), ('dt_lua', lua), ('dt_phi_nong_nghiep', o + pnn), ('dt_o', o)):
                tong[k] += abs(v)
    return tong


def thu_cot_khong_bth(ws, cot_khong, cot_nhan: int, r1: int, r2: int, n_cot: int, do=None,
                      toi_thieu: dict | None = None) -> float:
    """Cột số toàn 0 (cot_khong) thu hẹp tới RONG_COT_KHONG_BTH - nhưng chữ tiêu đề cột (ô dòng r1..r2 phủ cột đó, kể cả ô gộp
    ngang) không được nhiều dòng hơn hiện có / hơn chỗ của dòng tiêu đề; phần bề rộng thu được cộng HẾT vào cột cot_nhan (nguồn gốc
    đất - chữ dài nhất bảng, ít dòng hơn). Tổng bề rộng (tỷ lệ in) không đổi. toi_thieu {cột: bề rộng}: từ dài nhất của chữ tiêu đề
    cột (vua_cot_theo_tieu_de) - không bẻ đôi một từ. Trả bề rộng đã chuyển (đơn vị Excel)."""
    from openpyxl.utils import get_column_letter
    cao = _ham_cao(ws)
    gop = {(m.min_row, m.min_col): m for m in ws.merged_cells.ranges if r1 <= m.min_row <= r2}
    o_td = []
    for o in _o_chu(ws, r2):
        if o.row < r1 or o.column > n_cot or not o.value.strip():
            continue
        m = gop.get((o.row, o.column))
        c1, c2 = (m.min_col, min(m.max_col, n_cot)) if m else (o.column, o.column)
        a, b = (m.min_row, m.max_row) if m else (o.row, o.row)
        ten, co, dam = _phong(o)
        chu = o.value.rstrip('\n')

        def so_dong(chu=chu, c1=c1, c2=c2, ten=ten, co=co, dam=dam):
            return so_dong_o(chu, _rong_vung(ws, c1, c2), ten, co, dam, do)
        cho = int((sum(cao(r) for r in range(a, b + 1)) - 6) // dong_chu_bang(co))
        o_td.append((c1, c2, so_dong, max(so_dong(), cho)))
    tong_truoc = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75
    cdn = ws.column_dimensions.get(get_column_letter(cot_nhan))
    rong_nhan = float(cdn.width or 0) if cdn is not None else 0.0
    thu = 0.0
    for c in cot_khong:
        cd = ws.column_dimensions.get(get_column_letter(c))
        if cd is None or cd.hidden or not cd.width or (cd.min and cd.max and cd.min != cd.max):
            continue
        goc = float(cd.width)
        # không hẹp hơn chỗ cho số 0 của dòng TỔNG CỘNG (vua_cot_so_bth đo theo định dạng số của dòng dữ liệu đầu r2 + 1)
        san_c = max(RONG_COT_KHONG_BTH, _rong_can_so(ws.cell(r2 + 1, c), 0, do, dam=True),
                    float((toi_thieu or {}).get(c, 0)) * HE_SO_TU_TIEU_DE)
        if goc <= san_c:
            continue
        lien = [x for x in o_td if x[0] <= c <= x[1]]

        def vua(w):
            cd.width = w
            return all(dem() <= toi_da for _, _, dem, toi_da in lien)
        if vua(san_c):
            moi = san_c
        else:
            lo, hi = san_c, goc                                 # tìm nhị phân bề rộng nhỏ nhất giữ số dòng tiêu đề
            for _ in range(10):
                giua = (lo + hi) / 2
                if vua(giua):
                    hi = giua
                else:
                    lo = giua
            moi = math.ceil(hi * 10) / 10
        cd.width = min(goc, moi)
        thu += goc - float(cd.width)
    if thu > 0 and cdn is not None and cdn.width:
        cdn.width = round(float(cdn.width) + thu, 2)
        # bề rộng cột làm tròn theo điểm ảnh: tổng có thể nhích hơn trước - cột nhận trả lại phần nhích (giữ tỷ lệ in)
        du = sum(_px_cot(ws, n_cot + 1)[:n_cot]) * 0.75 - tong_truoc
        if du > 0:
            cdn.width = round(max(rong_nhan, float(cdn.width) - du / 0.75 / _mdw(ws.parent) - 0.05), 2)
    return thu


def lap_bang_tong_hop(con, file_ra, ds_ma_ho: list | None = None, so_pa_tong: str = '',
                      ngay_pa_tong: str = '', bao_tien_do=None, ky_hieu_so: str = '', du_thao: bool | None = None,
                      lan='cong_don') -> Path:
    """Bảng tổng hợp các hộ. so_pa_tong / ngay_pa_tong (phương án tổng của đợt trình): điền vào "(Đính kèm Phương án số …/…
    ngày … tháng … năm …)" và ngày ký của mẫu (chỗ trống {so_pa_tong}, {ngay_pa_tong} cũng dùng được).
    bao_tien_do(i, n): gọi mỗi 100 hộ để hộp tiến trình vẽ lại (bảng nhiều hộ, không "Không phản hồi"); không dừng giữa chừng.
    Vị trí cột, dòng dữ liệu đầu, cột cộng SUM, làm tròn và phân bổ kinh phí tổ chức thực hiện: hồ sơ địa phương (0.9.85)."""
    from . import dia_phuong
    from openpyxl.utils import get_column_letter
    du_thao = bool(du_thao)                                             # chế độ phát hành: dự thảo (chữ DỰ THẢO, không số) / chính thức
    if du_thao:
        so_pa_tong, ngay_pa_tong = '', ''
    from . import mau_bang_tong_hop              # 1.0.20: mẫu dựng hoàn toàn bằng mã (không còn file IN_BANGTONGHOP.xlsx)
    wb = mau_bang_tong_hop.tao_workbook()
    ws = wb.worksheets[0]
    K = dia_phuong.cot_mau(TEN_BTH)                                     # trường -> số cột
    d0 = int(dia_phuong.lay('mau_in.IN_BANGTONGHOP.dong_du_lieu_dau', DONG_DAU_BTH))
    n_cot = dia_phuong.so_cot(dia_phuong.lay('mau_in.IN_BANGTONGHOP.cot_cuoi', 'Y'))
    # 1.0.07: A3 ngang, tỷ lệ cố định 55%, chữ 14 / tiêu đề 16 pt đậm (mẫu chữ 20 pt thu cột / dòng theo tỷ lệ chữ)
    chuan_le_trang(ws, 'tong_hop')
    dat_kho_a3(ws)
    chuan_co_chu_bth(ws, d0)
    gian_dong_dau_bth(ws)
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
    from .in_word import dong_co_quan                              # 24/10/2026: cùng cách chia dòng cơ quan với bản Word chi tiết
    cap, chi_nhanh = dong_co_quan(da)
    da['DON_VI_CAP_TREN'] = ' '.join(cap.split())                  # dòng 1: cơ quan chủ quản (một dòng, ô gộp rộng)
    da['DON_VI_TIEU_DE'] = chi_nhanh                               # dòng 2: "CHI NHÁNH …" đậm, gạch chân
    da['du_an'] = re.sub(r'^\s*dự\s+án\s+', '', da['du_an'], flags=re.I)
    da['nhan_du_an'] = nhan_du_an(da['du_an'])                     # tên dự án in hoa -> "DỰ ÁN", còn lại "Dự án"
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
    from .lan_pa import co_bang, ho_nhieu_lan
    nhieu_lan = ho_nhieu_lan(con) if lan != 'cong_don' and co_bang(con) else set()
    khoi = []
    for ma in ds_ma_ho:
        pa = tat_ca.get(ma) or doc_phuong_an(con, ma)
        kq = kqh[ma][0] if ma in kqh else tinh_pa(pa, bc)
        thua = list(bc.thua_cua(ma))
        # 1.0.05: hộ nhiều lần lập phương án - lan 'moi_nhat' / số: chỉ dòng + tiền của lần đó (đợt trình phương án bổ sung),
        # thửa: các thửa có dòng đất trong lần; 'cong_don' (mặc định): cộng dồn mọi lần như trước
        if lan != 'cong_don' and ma in nhieu_lan:
            ln = chon_lan_in(con, ma, lan)
            pa = doc_phuong_an(con, ma, lan=ln)
            kq = nghiep_vu.tinh_pa_lan(pa, doc_phuong_an(con, ma, den_lan=ln - 1), bc)
            co_thua = {d.ma_thua for d in pa.dat}
            thua = [t for t in thua if t['ma_thua'] in co_thua]
        khoi.append((ma, pa, kq, thua))
    for c in range(1, n_cot + 1):               # mọi ô dữ liệu (chữ và số tiền): căn giữa dọc, tự xuống dòng - chép theo dòng mẫu
        _can_giua_doc(ws.cell(d0, c))
    # 1.0.04 (người dùng 19/10/2026): căn lề từng cột - nguồn gốc căn đều; họ tên, địa chỉ, TĐC, ghi chú căn giữa; số 0 hiện "-"
    for k in ('stt', 'ho_ten', 'dia_chi', 'tai_dinh_cu', 'ghi_chu'):
        ws.cell(d0, K[k]).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.cell(d0, K['nguon_goc']).alignment = Alignment(horizontal='justify', vertical='center', wrap_text=True)
    cot_so_cong = [dia_phuong.so_cot(cl) for cl in dia_phuong.lay('mau_in.IN_BANGTONGHOP.cot_cong')]
    for c in cot_so_cong:
        ws.cell(d0, c).number_format = dinh_dang_so_gach(ws.cell(d0, c).number_format)
    # ẩn cột "Vị trí đất" (số cột 11): dải số chạy 1..10 rồi 12..21; cột tiền rộng tối thiểu RONG_COT_TIEN_BTH
    cd_vt = ws.column_dimensions[get_column_letter(K['vi_tri'])]
    cd_vt.hidden = True
    cao = max(float(ws.row_dimensions[d0].height or 36), cao_dong_bang(1, ws.cell(d0, K['ho_ten']).font.sz or 14))
    do = _ham_do_chu()
    # cột số còn dư chỗ nhường cho họ tên / địa chỉ / vị trí (16/10/2026): số lớn nhất dự kiến = tổng cả bảng (tiền: tổng các hộ;
    # diện tích: tổng diện tích thu hồi) - không cột nào nhỏ hơn số của dòng TỔNG CỘNG
    tong_tien = sum((k.tong for _, _, k, _ in khoi), KHONG)
    tong_dt_du_kien = sum((D(t['dt_thu_hoi']) for _, _, _, ts in khoi for t in ts), KHONG)
    cot_so = {K[k]: _so(tong_tien) for k in ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh',
                                             'thuong', 'tong') if k in K}
    cot_so.update({K[k]: _so(tong_dt_du_kien) for k in ('dt_thu_hoi', 'dt_nong_nghiep', 'dt_lua', 'dt_phi_nong_nghiep', 'dt_o')
                   if k in K})
    for k in ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong', 'tong'):
        cd = ws.column_dimensions[get_column_letter(K[k])]
        if not cd.hidden and float(cd.width or 0) < RONG_COT_TIEN_BTH:
            cd.width = RONG_COT_TIEN_BTH
    can_bang_cot_bth(ws, {c: v for c, v in cot_so.items() if c not in {K[k] for k in COT_TIEN_BTH}},
                     (K['ho_ten'], K['dia_chi']), d0, do)
    # 1.0.07: cột chữ co / giãn cho bảng vừa đúng khổ A3 ở 55%; tiêu đề văn bản + hàng tiêu đề cột đủ cao cho chữ 16 pt
    r_td = next((r for r in range(1, d0) if str(ws.cell(r, K['stt']).value or '').strip().upper() == 'STT'), max(1, d0 - 4))
    rong_td = vua_cot_theo_tieu_de(ws, r_td, d0 - 1, n_cot, do)
    vua_ngang_a3_bth(ws, n_cot, tuple(K[k] for k in ('ho_ten', 'dia_chi', 'nguon_goc', 'tai_dinh_cu', 'ghi_chu')),
                     {**cot_so, **{K[k]: _so(tong_tien) for k in COT_TIEN_BTH if k in K}}, d0, do, rong_td)
    # 21/10/2026: cột số toàn 0 / "-" (nhà, cây, hỗ trợ… của dự án chỉ có đất) thu hẹp, nhường hết cho cột nguồn gốc đất
    tong_cot = tong_cot_bth(khoi, bc)
    thu_cot_khong_bth(ws, [K[k] for k in COT_THU_BTH if k in K and tong_cot[k] == 0], K['nguon_goc'], r_td, d0 - 1, n_cot, do,
                      rong_td)
    lap_day_ngang_a3_bth(ws, n_cot, K)                                  # 22/10/2026: bảng sát lề phải, không hở bên phải
    vua_cao_chu(ws, 1, d0 - 1, n_cot, do)
    px, nho = _px_cot(ws, n_cot + 1), {}
    khoi_ho = []                                                        # [(dòng đầu, dòng cuối)] từng hộ - ngắt trang giữa các hộ
    san, san_khoi, cam = {}, [], set()                                  # nén khít: chiều cao tối thiểu; dòng không được ngắt sau
    tong_thua, tong_dt = 0, KHONG
    co_vat_nuoi = False                                                 # có hộ có vật nuôi: tiêu đề cột cây trồng ghi cả vật nuôi
    ho = {r['ma_ho']: r for r in con.execute('SELECT * FROM ho')}       # một câu thay vì một câu mỗi hộ
    from .ho_so import chuan_nguon_goc
    co_ho = float(ws.cell(d0, cot_ho[0]).font.sz or 14)
    phong_d0 = {}

    def so_dong(chu, c) -> int:                         # như _so_dong_bth nhưng trên chữ chưa ghi (phông của dòng mẫu d0)
        if not isinstance(chu, str) or not px[c - 1]:
            return 1
        if c not in phong_d0:
            phong_d0[c] = _phong(ws.cell(d0, c))
        k = (chu, c) + phong_d0[c]
        if k not in nho:
            nho[k] = so_dong_o(chu, px[c - 1] * 0.75 - 6, *phong_d0[c], do)
        return nho[k]
    # KẾ HOẠCH DÒNG (21/10/2026): nội dung từng hộ / thửa và số dòng Excel mỗi thửa (chữ riêng của thửa cao hơn CAO_KHOI_BTH ->
    # nhiều dòng gộp ô), dòng thêm cho chữ gộp theo hộ - rồi cấp phát dòng MỘT lần (chèn dòng từng hộ dời mọi dòng phía dưới: O(n²))
    ke_hoach = []
    for stt, (ma, pa, kq, thua) in enumerate(khoi, start=1):
        if bao_tien_do and stt % 100 == 0:
            bao_tien_do(stt, len(khoi))
        h = ho[ma]
        nhieu_thua = len(thua) > 1
        # hộ nhiều thửa (22/10/2026 - thay cách lặp mỗi dòng của 1.0.04): STT, họ tên, địa chỉ, tổng cộng, TĐC, ghi chú GỘP DỌC một
        # ô cho cả hộ (tach_ho lặp lại ở đầu trang sau khi hộ vắt qua ranh trang); mỗi thửa một dòng: tờ, thửa, loại đất, diện tích,
        # tiền đất của thửa (khi chia được - tien_dat_theo_thua_bth), nguồn gốc riêng từng thửa khi tách được
        # (tach_nguon_goc_theo_thua: các thửa ghi khác nhau, hoặc chữ chung có đoạn riêng cho MỌI thửa) - không thì gộp như cũ.
        # Tài sản, cây trồng, hỗ trợ, thưởng không gắn với thửa (ct_khoan không có mã thửa): một ô gộp theo hộ
        ng_thua = tach_nguon_goc_theo_thua([(chuan_nguon_goc(t['nguon_goc']), t['so_thua'], t['so_to']) for t in thua]) \
            if nhieu_thua else None
        tien_thua = tien_dat_theo_thua_bth(pa, thua, kq, bc) if nhieu_thua else None
        lap = set()
        if ng_thua is not None:
            lap.add(K['nguon_goc'])
        if tien_thua is not None:
            lap.add(K['tien_dat'])
        gop = gop_ho - lap
        c_ho = tuple(c for c in cot_ho if c in gop) or (K['tai_dinh_cu'],)
        c_thua = cot_thua + tuple(c for c in cot_ho if c not in gop)
        tien = _tien_ho_bth(pa, kq, bc)
        o_ho = {K['stt']: stt, K['ho_ten']: h['ho_ten'], K['dia_chi']: h['dia_chi'], K['tai_dinh_cu']: h['tai_dinh_cu'] or None,
                K['ghi_chu']: f'Hỗ trợ khác: {format(int(tien["khac"]), ",").replace(",", ".")} đ' if tien['khac'] > 0 else None}
        for k in COT_TIEN_BTH:
            if K[k] not in lap:
                o_ho[K[k]] = _so(tien[k])
        if ng_thua is None:
            t_ng = next((t for t in thua if t['nguon_goc']), None)
            o_ho[K['nguon_goc']] = '\n'.join(bo_lap_mo_dau(x) for x in chuan_nguon_goc(t_ng['nguon_goc']).split('\n')) \
                if t_ng else None
        dong_thua = []
        for i_t, t in enumerate(thua):
            o = {}
            if ng_thua is not None:
                o[K['nguon_goc']] = ng_thua[i_t] or None
            if tien_thua is not None:
                o[K['tien_dat']] = _so(tien_thua[t['ma_thua']])
            nn, lua, dat_o, pnn = _dt_thua_bth(pa, t['ma_thua'])
            dat_thua = [d for d in pa.dat if d.ma_thua == t['ma_thua']]
            o.update({K['so_to']: t['so_to'], K['so_thua']: t['so_thua'], K['loai_dat']: t['loai_dat'],
                      K['dt_thu_hoi']: _so(t['dt_thu_hoi']), K['dt_nong_nghiep']: _so(nn),
                      K['dt_lua']: _so(lua),                    # 1.0.04: 0 hiện "-" (dinh_dang_so_gach)
                      K['dt_phi_nong_nghiep']: _so(dat_o + pnn), K['dt_o']: _so(dat_o),
                      K['vi_tri']: dat_thua[0].vi_tri if dat_thua else None})
            # chữ riêng của thửa (loại đất, vị trí, nguồn gốc riêng) cao hơn CAO_KHOI_BTH: thửa chiếm nhiều dòng Excel
            can_t = cao_dong_bang(max(so_dong(o.get(c), c) for c in c_thua), co_ho, None)
            dong_thua.append((o, max(1, math.ceil(can_t / CAO_KHOI_BTH))))
        can_ho = max(cao_dong_bang(so_dong(o_ho.get(c), c), co_ho, None) for c in c_ho)
        so = sum(n for _, n in dong_thua) or 1
        # chữ gộp theo hộ (nguồn gốc dài, hộ ít thửa) cao hơn: thêm dòng cho hộ, ô thửa cuối gộp xuống - không mất chữ, có chỗ ngắt
        them = max(0, math.ceil(can_ho / CAO_KHOI_BTH) - so)
        ke_hoach.append((ma, pa, kq, thua, h, o_ho, dong_thua, gop, c_ho, c_thua, so + them, them))
    tong_dong = sum(x[10] for x in ke_hoach) or 1
    _doi_dong(ws, d0 + 1, tong_dong - 1)
    for r in range(d0 + 1, d0 + tong_dong):
        _chep_kieu_dong(ws, d0, r, n_cot)
    for r in range(d0, d0 + tong_dong):
        ws.row_dimensions[r].height = cao
    r = d0
    for ma, pa, kq, thua, h, o_ho, dong_thua, gop, c_ho, c_thua, so, them in ke_hoach:
        r0 = r
        for c, v in o_ho.items():
            ws.cell(r0, c).value = v
        nhom = []                                       # [(dòng đầu, dòng cuối)] các dòng Excel của từng thửa
        for o, n_t in dong_thua:
            for c, v in o.items():
                ws.cell(r, c).value = v
            nhom.append((r, r + n_t - 1))
            r += n_t
        if not nhom:
            nhom.append((r, r))
            r += 1
        if them:
            nhom[-1] = (nhom[-1][0], nhom[-1][1] + them)
            r += them
        for a, b in nhom:                               # ô của thửa gộp xuống các dòng của thửa
            if b > a:
                for c in range(1, n_cot + 1):
                    if c not in gop:
                        _gop_o(ws, a, c, b, c)
        if r - 1 > r0:
            for c in sorted(gop):
                _gop_o(ws, r0, c, r - 1, c)
        can_ho = cao_can_ho_bth(ws, r0, px, do, nho, c_ho)
        _vua_cao_ho_bth(ws, r0, r, px, do, can_ho, nho, c_ho, c_thua, nhom)
        khoi_ho.append((r0, r - 1))
        for a, b in nhom:
            n_thua = max(_so_dong_bth(ws, a, c, px, do, nho) for c in c_thua)
            can_t = n_thua * dong_chu_bang(co_ho) + DEM_DONG - NEN_DEM
            if a == b:
                san[a] = max(CAO_NEN_TOI_THIEU, can_t)
            else:
                for rr in range(a, b + 1):
                    san[rr] = CAO_NEN_TOI_THIEU
                san_khoi.append((a, b, can_t))
        san_khoi.append((r0, r - 1, can_ho - NEN_DEM))
        co_vat_nuoi = co_vat_nuoi or kq.muc[nghiep_vu.MUC_VN] != 0
        tong_thua += len(thua)
        tong_dt += sum((D(t['dt_thu_hoi']) for t in thua), KHONG)
    tong = d0 + tong_dong
    for rr in range(tong, tong + 5):            # dòng tổng cộng, kinh phí tổ chức thực hiện, tổng cộng cuối: căn giữa dọc
        for c in range(1, n_cot + 1):
            if ws.cell(rr, c).has_style or ws.cell(rr, c).value is not None:
                _can_giua_doc(ws.cell(rr, c))
        for c in cot_so_cong:                   # 1.0.04: dòng tổng cộng / kinh phí - số 0 hiện "0" (dòng hộ hiện "-")
            o = ws.cell(rr, c)
            o.number_format = dinh_dang_so_khong(o.number_format)
    if co_vat_nuoi:                                                    # cột cây trồng + vật nuôi (mục 4 của bản chi tiết)
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
                if '{don_vi_lap}' in v:             # 1.0.04: tên đơn vị trong ngoặc viết gọn ("TTPTQĐ Chi nhánh …") - vừa một hàng
                    v = v.replace('{don_vi_lap}', rut_gon_don_vi(da.get('don_vi_lap') or ''))
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
    chuan_trich_yeu(ws, d0)                                      # "HỖ TRỢ & TÁI ĐỊNH CƯ" -> "VÀ" (mẫu người dùng có thể ghi "&")
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
        # vùng gộp phủ dòng e dò MỘT lượt cho mọi cột (trước: mỗi cột duyệt hết ~20.000 vùng gộp của bảng 3.000 hộ)
        cm = {e: [m for m in ws.merged_cells.ranges if m.min_row <= e <= m.max_row]}
        for c in range(1, n_cot + 1):                                   # cả ô thửa gộp xuống dòng thêm (chữ dài)
            tach = _tach_gop_doc(ws, c, e, cm)
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
    ngat_trang_bth(ws, khoi_ho, tong, n_cot, cuoi, (9, 12), san, tuple(san_khoi), cam, tach_ho, ti_le=TI_LE_BTH)
    wb.defined_names[TEN_GIU_TI_LE] = DefinedName(TEN_GIU_TI_LE, attr_text=str(TI_LE_BTH_MIN))   # VBS: không thu dưới 50%

    _thay_cho_trong(ws, dict(da, so_pa_tong=so_pa_tong or '', ngay_pa_tong=ngay_pa_tong or '',
                             ky_hieu_so=ky_hieu_so or da.get('ky_hieu_so') or ''))       # ký hiệu theo đợt trình (0.9.72)
    ws.print_area = f'A1:{get_column_letter(n_cot)}{_dong_cuoi(ws, n_cot) + 1}'
    wb.calculation.fullCalcOnLoad = True
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    dk = _dat_duong_ke(ws, vt_dk)                 # sát chân chữ, căn giữa (tên đơn vị, tiêu ngữ, dòng dự án)
    # dự thảo: "(DỰ THẢO)" dưới đường kẻ tên đơn vị; chính thức: xóa. SAU đường kẻ (1.0.04): chữ mới dưới tên đơn vị không làm
    # đường kẻ neo nhầm vào nó
    ap_che_do_du_thao(ws, du_thao, TEN_BTH)
    _an_toan.luu_xlsx(wb, file_ra)
    chen_duong_ke(file_ra, dk)                    # đường kẻ (openpyxl không giữ hình vẽ)
    return file_ra


# ---------------------------------------------------------------- PDF / máy in qua Microsoft Excel: in_excel.py (1.0.29)
from .in_excel import (CHO_KHOI_DONG, CHO_MOI_FILE, _VBS, _doc_luong, _tat_excel_tu_dong, chay_excel,  # noqa: E402,F401
                       co_excel, mo_file)


# ---------------------------------------------------------------- in hàng loạt


def xuat_hang_loat(con, ds_ma_ho: list, thu_muc, pdf: bool = False, in_may: bool = False, bang_tong_hop: bool = False,
                   bao_tien_do=None, bao_excel=None, so_ban: int = 1, word: bool = True) -> dict:
    """Xuất phương án chi tiết từng hộ (+ bảng tổng hợp) ra MỘT thư mục. Trả dict(word=[...], excel=[...], pdf=[...], loi=[...]).
    bao_tien_do(i, n) sau mỗi file, bao_excel(i, n) trong lúc Word / Excel xuất PDF / in: trả True = dừng.
    word (22/10/2026 - bản Word là mẫu chuẩn duy nhất của phương án chi tiết): phương án chi tiết = bản Word NĐ 30 (in_word), PDF /
    in qua Word, Word lỗi thì PDF gần đúng (van_ban_trinh.xuat_bo_ho_so - cùng đường với Xuất hồ sơ & Bản in); False: bản Excel."""
    from . import van_ban_trinh
    return van_ban_trinh.xuat_bo_ho_so(con, ds_ma_ho, thu_muc, chi_tiet=True, bang_tong_hop=bang_tong_hop, pdf=pdf,
                                       in_may=in_may, so_ban=so_ban, chia_thu_muc=False, bao_tien_do=bao_tien_do,
                                       bao_excel=bao_excel, lan=None)
