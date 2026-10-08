"""Bảng giá đất theo Nghị quyết 28/2025/NQ-HĐND của HĐND tỉnh Đồng Nai (áp dụng từ 01/01/2026) - trích các địa bàn
Xã Trị An, Xã Tân An, Xã Phú Lý, Phường Tân Triều; đất phi nông nghiệp (Phụ lục III) và nông nghiệp (Phụ lục I).

Dữ liệu (pabt/bang_gia_nq28.json): mỗi đoạn đường 7 dòng - mặt tiền (MT); T1-T3: đường đấu nối trực tiếp ra đường;
K1-K3: đường không đấu nối trực tiếp và thông ra đường. Giá lưu theo nghìn đồng/m² như văn bản; hàm trả đồng/m².
Chép từ bản PDF đóng dấu của Nghị quyết, kiểm tra chéo bằng nhận dạng chữ; khi dùng chính thức cần đối chiếu văn bản gốc.
"""
from __future__ import annotations
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from .lap_pa import bo_dau

VAN_BAN = 'Nghị quyết 28/2025/NQ-HĐND ngày 10/12/2025 của HĐND tỉnh Đồng Nai (bảng giá đất áp dụng từ 01/01/2026)'
COT = [('dat_o', 'Đất ở'), ('tmdv', 'Đất thương mại, dịch vụ'), ('sxkd', 'Đất SX-KD phi NN, khoáng sản'),
       ('nn_cay', 'Đất trồng cây lâu năm, cây hằng năm'), ('nn_rung_nts', 'Đất rừng sản xuất, nuôi trồng thủy sản')]
TEN_VT = {'MT': 'Mặt tiền đường', 'T1': 'Đường đấu nối trực tiếp - mức 1', 'T2': 'Đường đấu nối trực tiếp - mức 2',
          'T3': 'Đường đấu nối trực tiếp - mức 3', 'K1': 'Đường không đấu nối trực tiếp - mức 1',
          'K2': 'Đường không đấu nối trực tiếp - mức 2', 'K3': 'Đường không đấu nối trực tiếp - mức 3'}
# mã loại đất -> cột giá
COT_LOAI = {'ONT': 'dat_o', 'ODT': 'dat_o', 'TMD': 'tmdv', 'SKC': 'sxkd', 'SKS': 'sxkd', 'SKN': 'sxkd',
            'CLN': 'nn_cay', 'HNK': 'nn_cay', 'BHK': 'nn_cay', 'LUC': 'nn_cay', 'LUK': 'nn_cay', 'LUA': 'nn_cay', 'CHN': 'nn_cay',
            'NHK': 'nn_cay', 'RSX': 'nn_rung_nts', 'NTS': 'nn_rung_nts'}


def _file() -> Path:
    from . import tai_nguyen
    return tai_nguyen('bang_gia_nq28.json')


@lru_cache(maxsize=1)
def tat_ca() -> list:
    try:
        return json.loads(_file().read_text(encoding='utf-8'))
    except OSError:
        return []


def ds_xa() -> list:
    return list(dict.fromkeys(r['xa'] for r in tat_ca()))


def mo_ta_vi_tri(r: dict) -> str:
    """Điều kiện của dòng (bề rộng, khoảng cách tới đường giao thông) theo văn bản."""
    vt = r['vi_tri']
    a, b = r['nguong']
    if vt == 'MT':
        return f'Mặt tiền {r["ten_duong"]}'
    loai = 'đấu nối trực tiếp ra' if vt[0] == 'T' else 'không đấu nối trực tiếp và thông ra'
    dk = {'1': f'rộng ≥5m cách đường ≤{a:,}m; rộng 3-<5m cách ≤{b:,}m',
          '2': f'rộng ≥5m cách >{a:,}m; rộng 3-<5m cách >{b:,}m đến ≤{a:,}m; rộng <3m cách ≤200m',
          '3': f'rộng 3-<5m cách >{a:,}m; rộng <3m cách >200m'}[vt[1]]
    return f'Đường nhựa, BTXM {loai} {r["ten_duong"]}: {dk}'.replace(',', '.')


def cot_cua_loai(loai_dat: str) -> str | None:
    for p in re.split(r'[+,;/ ]+', (loai_dat or '').upper()):
        if p in COT_LOAI:
            return COT_LOAI[p]
    return None


def khop_xa(ten: str, r_xa: str) -> bool:
    t = bo_dau(ten or '')
    t = re.sub(r'^(xa|phuong|thi tran)\s+', '', t)
    return bool(t) and t in bo_dau(r_xa)


def tim(xa: str = '', tu_khoa: str = '') -> list:
    """Lọc theo địa bàn (bỏ qua nếu không khớp địa bàn nào) và từ khóa không dấu (tên đường, điểm đầu / cuối, mã vị trí)."""
    ds = tat_ca()
    theo_xa = [r for r in ds if khop_xa(xa, r['xa'])]
    if theo_xa:
        ds = theo_xa
    k = bo_dau(tu_khoa).split()
    if k:
        ds = [r for r in ds if all(x in bo_dau(' '.join((r['ten_duong'], r['diem_dau'], r['diem_cuoi'], r['vi_tri'])))
                                   for x in k)]
    return ds


def gia_dong(r: dict, cot: str) -> int:
    """Giá đồng/m² của một dòng theo cột (văn bản ghi nghìn đồng)."""
    return int(r[cot]) * 1000


def can_cu(r: dict, cot: str) -> str:
    return (f'NQ 28/2025/NQ-HĐND: {r["xa"]}, {r["ten_duong"]} (từ {r["diem_dau"]} đến {r["diem_cuoi"]}), '
            f'{TEN_VT[r["vi_tri"]]}, TT {r["tt"]}, {dict(COT)[cot]}')


def xuat_excel(file_ra) -> Path:
    """Xuất bảng giá ra Excel: mỗi địa bàn một sheet, giá đồng/m²."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ke = Side(style='thin', color='999999')
    for xa in ds_xa():
        ws = wb.create_sheet(re.sub(r'[\\/*?:\[\]]', '', xa)[:31])
        ws['A1'] = f'BẢNG GIÁ ĐẤT - {xa.upper()}'
        ws['A1'].font = Font(bold=True, size=13, color='1F4E79')
        ws['A2'] = VAN_BAN + '. Đơn vị: đồng/m².'
        ws['A2'].font = Font(italic=True)
        tieu_de = ['TT', 'Tên đường', 'Điểm đầu', 'Điểm cuối', 'Vị trí', 'Điều kiện vị trí'] + [t for _, t in COT] + ['Trang PL III / PL I']
        ws.append([])
        ws.append(tieu_de)
        for c in ws[4]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1F4E79')
            c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
            c.border = Border(left=ke, right=ke, top=ke, bottom=ke)
        for r in [r for r in tat_ca() if r['xa'] == xa]:
            ws.append([r['tt'], r['ten_duong'], r['diem_dau'], r['diem_cuoi'], r['vi_tri'], mo_ta_vi_tri(r)]
                      + [gia_dong(r, k) for k, _ in COT] + [f'{r["trang"]["pl3"]} / {r["trang"]["pl1"]}'])
            dong = ws.max_row
            for c in ws[dong]:
                c.border = Border(left=ke, right=ke, top=ke, bottom=ke)
                c.alignment = Alignment(wrap_text=True, vertical='top')
            for c in ws[dong][6:11]:
                c.number_format = '#,##0'
            if r['vi_tri'] == 'MT':
                for c in ws[dong]:
                    c.font = Font(bold=True)
                    c.fill = PatternFill('solid', fgColor='DDEBF7')
        for col, w in zip('ABCDEFGHIJKL', (6, 26, 26, 30, 7, 48, 12, 12, 12, 13, 13, 14)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = 'C5'
    file_ra = Path(file_ra)
    wb.save(file_ra)
    return file_ra
