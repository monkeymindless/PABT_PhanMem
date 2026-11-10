"""Màu theo tông nền (1.0.96 - tách khỏi giao_dien.py): bảng đổi màu GỐC -> màu của tông đang dùng (Sáng / Tối / phương án Navy).

Module lá về màu: chỉ cần QColor và chu_de (nạp trễ trong hàm), KHÔNG nhập giao_dien - màn hình / mô hình bảng / delegate vẽ màu
theo tông nhập thẳng từ đây được. giao_dien nhập lại mọi tên (cùng đối tượng: TONG_NEN, TOKEN... đổi tại chỗ, không gán lại).
"""
from __future__ import annotations

import re

from PySide6.QtGui import QColor

CHINH_GOC = ('#1E3A5F', '#152C48')     # màu chính GỐC viết thẳng trong bảng kiểu (1.0.35) -> chu_de.MAU_TONG[tông]['chinh' / 'chinh_re']

TONG_NEN = ['sang']            # 1.0.33: tông nền bề mặt đang dùng (chu_de.TONG_NEN) - dat_tong_nen()
_KHOA_MAU_NEN = ('nen', 'khung', 'vach', 'chu', 'chu_phu')
# màu GỐC mà bảng kiểu chung viết thẳng (#F8FAFC, #E2E8F0…): bảng kiểu dựng bằng màu này rồi đổi theo tông (ap_tong_nen). Từ 1.0.34
# tông mặc định 'sang' (Sáng Sapphire) KHÁC màu gốc: nền #F1F5F9, viền #CBD5E1 - mở phần mềm là thấy giao diện mới
_TOKEN_GOC = dict(nen='#F8FAFC', khung='#FFFFFF', vach='#E2E8F0', chu='#0F172A', chu_phu='#475569')
# 1.0.79: màu GIỮ CHỖ trong bảng kiểu chung, chỉ dùng ở các khai báo này; _bang_doi_mau thay theo tông + phương án Navy
TD_GOC = dict(nen='#1E3A5D', chu='#FFFFFE', vach='#1E3A5C', day='#1E3A5B', re='#1E3A5A')     # tiêu đề bảng ngang
DAU_GOC = dict(nen='#EAF1F8', chu='#1E3A5E', vien='#CBD9E8')                                  # đầu khung Sổ nhật ký vận động
TOKEN_NHAN_GOC = '#2563EB'
_NHO_BANG_DOI_MAU: dict = {}                                                                   # (tông, phương án) -> bảng đổi màu; xem _bang_doi_mau
_RE_KHAI_BAO = re.compile(r'([A-Za-z-]+)(\s*:\s*)([^;{}]+)')
_RE_MAU_HEX = re.compile(r'#[0-9A-Fa-f]{6}\b')
# tông Tối chuyên gia (Dark Studio): ngoài 5 màu tông, các màu sáng viết thẳng khác trong bảng kiểu cũng đổi sang màu tối tương ứng
# (nền nhạt, viền, chữ đậm, chữ navy trên nền trắng) - màu nền nút xanh / chữ trắng / huy hiệu ngữ nghĩa (vàng, đỏ nhạt) giữ nguyên
TOI_NEN = {'#F1F3F4': '#1E293B', '#CBD5E1': '#334155', '#FFF1F2': '#3A1414', '#ECFCCB': '#1F2E0F', '#EEF3FA': '#24324A', '#E5A93A': '#854D0E', '#FFEBEE': '#3A1414', '#F4F6F8': '#162033', '#FFF6D6': '#3B2F12', '#FDEBDD': '#3A2414', '#F1F4F7': '#162033', '#F0FDF4': '#0F2A1F', '#ECFDF5': '#0F2A1F', '#DCFCE7': '#14532D', '#FFFBEB': '#2A2210', '#FEF3C7': '#3B2F12',
           '#FEF2F2': '#3A1414', '#FEE2E2': '#4C1D1D', '#F0FDFA': '#0F2A28', '#FFFDE7': '#2A2210', '#F5F3FF': '#2A1F4A',
           '#F1F5F9': '#162033', '#EEF2F7': '#24324A', '#E2E8F0': '#2A3A52', '#EFF6FF': '#1E3A5F', '#F0F6FF': '#1E3A5F',
            '#DBEAFE': '#1E40AF', '#F0F9FF': '#0C2A3F', '#EEF5FC': '#24324A', '#DCEBFA': '#1E40AF', '#FAFBFC': '#0F172A', '#F8F9FA': '#0B1120',
           '#F8F8F8': '#0B1120', '#F3F6FA': '#0B1120', '#FFF2CC': '#2A2210',
           '#EAF6EC': '#062E1E', '#FFF4DB': '#332407', '#FCEDEB': '#3B1219',          # 1.0.51: nền dat_trang_thai
           # P1: nền ô trạng thái của các bảng (xanh = khớp / đã xong, cam đỏ = lệch, vàng = cần xem, xám = chỉ đọc) - mau_o_theo_tong
           '#E2EFDA': '#14331F', '#F8CBAD': '#4A2414', '#F2F2F2': '#1E293B', '#DDEBF7': '#1E3A5F', '#E8F5E9': '#14331F',
           '#E3F2FD': '#1E3A5F', '#FCE4D6': '#3A2414', '#EEF1F4': '#1E293B', '#EEF6FF': '#1E3A5F', '#FFF3C4': '#3B2F12',
           '#DFF0D8': '#14331F', '#FFF4D6': '#3B2F12', '#FFF8E1': '#2A2210', '#F5F5F5': '#1E293B', '#F2F4F7': '#1E293B'}
TOI_VIEN = {'#FECDD3': '#7F1D1D', '#BBF7D0': '#166534', '#86EFAC': '#15803D', '#A7F3D0': '#047857', '#FDE68A': '#854D0E', '#FECACA': '#7F1D1D',
            '#99F6E4': '#0F766E', '#BAE6FD': '#075985', '#CBD5E1': '#475569', '#DCE3EA': '#334155', '#94A3B8': '#64748B', '#BFDBFE': '#1E40AF',
            '#8696AB': '#64748B', '#E5E5E5': '#334155', '#E35D5D': '#F87171',
            '#CDE8D2': '#166534', '#F1D9A0': '#854D0E', '#F3CFCA': '#7F1D1D'}
TOI_CHU = {'#0F3A63': '#93C5FD', '#991B1B': '#FCA5A5', '#1F76A6': '#7DD3FC', '#4A6785': '#A5B4C8', '#1F4E79': '#93C5FD',
           '#4A5B6C': '#CBD5E1', '#2F7A4F': '#86EFAC', '#7A1B12': '#FCA5A5', '#1E5E2F': '#86EFAC', '#5B6B7A': '#CBD5E1',
           '#08345F': '#BFDBFE', '#14532D': '#86EFAC', '#075985': '#7DD3FC', '#4A5866': '#CBD5E1', '#276348': '#86EFAC', '#2F7D54': '#86EFAC', '#065F46': '#6EE7B7', '#047857': '#6EE7B7', '#7C4A12': '#FCD34D',
           '#9A5A12': '#FCD34D', '#78350F': '#FCD34D', '#B83A3A': '#FCA5A5', '#1F6F66': '#5EEAD4', '#2F5DB5': '#93C5FD',
           '#1A5C85': '#7DD3FC', '#0284C7': '#7DD3FC', '#1E293B': '#E2E8F0', '#334155': '#CBD5E1', '#64748B': '#94A3B8', '#1E3A5F': '#93C5FD', '#2563EB': '#60A5FA',
           '#3B3B3B': '#E2E8F0', '#8B8B8B': '#94A3B8',
           '#152C48': '#BFDBFE', '#202124': '#F1F5F9', '#1A1A1A': '#F1F5F9', '#0B2E4F': '#E2E8F0', '#5B6B82': '#A5B4C8',
           '#8A5A00': '#FCD34D', '#1F4E78': '#93C5FD', '#D97706': '#FCD34D',
           # 1.0.51: chữ dat_trang_thai (tin 1,57:1 trên nền tối trước đây), đỏ / cam đậm
           '#0C4A6E': '#7DD3FC', '#1E6B34': '#86EFAC', '#7A4B00': '#FCD34D', '#A12A1F': '#FCA5A5', '#7C2D12': '#FDBA74',
           '#7F1D1D': '#FCA5A5',
           # 1.0.80: chữ bảng / thanh trạng thái viết màu tối chưa có trong bảng đổi
           '#1B5E20': '#86EFAC', '#B3261E': '#FCA5A5', '#5F6368': '#CBD5E1', '#107C41': '#86EFAC', '#BE123C': '#FDA4AF', '#008000': '#86EFAC', '#800000': '#FCA5A5',
           '#1F5FA0': '#93C5FD', '#3F6212': '#BEF264',
           '#B8433A': '#FCA5A5', '#2E7D32': '#86EFAC', '#1F5FA0': '#93C5FD',      # P1: chữ ô bảng (mau_o_theo_tong 'chu')
           # 1.0.93: chữ tối chưa có trong bảng đổi (Tối 1,9 - 2,9:1 trước đây)
           '#1D4ED8': '#93C5FD', '#B71C1C': '#FCA5A5', '#B45309': '#FCD34D', '#B91C1C': '#FCA5A5', '#166534': '#86EFAC',
           '#475569': '#CBD5E1', '#0F6E56': '#6EE7B7'}


def _bang_doi_mau(ten: str) -> dict:
    """{'nen': {màu gốc: màu mới}, 'vien': {…}, 'chu': {…}} của một tông (màu gốc của bảng kiểu -> màu tông). Nền đổi cả nền cửa sổ
    lẫn nền khung; viền đổi vạch ngăn; chữ chỉ đổi chữ chính / chữ phụ - chữ trắng trên nút xanh giữ nguyên. Tông 'toi' thêm
    TOI_NEN / TOI_VIEN / TOI_CHU."""
    from . import chu_de
    # 1.0.79: nhớ theo (tông, phương án): mau_theo_tong gọi cho từng ô khi vẽ bảng, không dựng lại từ điển mỗi lần. KHÔNG sửa bảng trả về
    khoa = (ten, chu_de.phuong_an_hien())
    kq = _NHO_BANG_DOI_MAU.get(khoa)
    if kq is not None:
        return kq
    _, nen, khung, vach, chu, chu_phu = chu_de.TONG_NEN.get(ten, chu_de.TONG_NEN[chu_de.MAC_DINH_TONG_NEN])
    g = _TOKEN_GOC
    loc = lambda d: {k.upper(): v.upper() for k, v in d.items() if k.upper() != v.upper()}   # noqa: E731
    them = ten == 'toi'
    mt = chu_de.mau_tong(ten)
    pa = chu_de.mau_phuong_an(ten)
    chinh = {CHINH_GOC[0]: mt['chinh'], CHINH_GOC[1]: mt['chinh_re']}       # mọi thuộc tính; riêng từng loại (nền / viền / chữ) thắng
    # tiêu đề bảng, đầu khung: tông không theo phương án giữ cách cũ (nền màu chính, chữ trắng, vạch màu chính đậm, viền đáy màu nhấn)
    td = dict(nen=pa['td_nen'], chu=pa['td_chu'], vach=pa['td_vach'], day=pa['td_day'], re=pa['td_re']) if pa else \
        dict(nen=mt['chinh'], chu='#FFFFFF', vach=mt['chinh_re'], day=TOKEN_NHAN_GOC, re=mt['chinh_re'])
    dau = dict(nen=pa['dau_nen'], chu=pa['dau_chu'], vien=pa['dau_vien']) if pa else \
        (dict(nen='#24324A', chu='#93C5FD', vien='#334155') if them else dict(nen=DAU_GOC['nen'], chu=mt['chinh'], vien=DAU_GOC['vien']))
    kq = {'nen': loc({**chinh, **(TOI_NEN if them else {}), g['nen']: nen, g['khung']: khung, TD_GOC['nen']: td['nen'], TD_GOC['re']: td['re'], DAU_GOC['nen']: dau['nen']}),
          'vien': loc({**chinh, **(TOI_VIEN if them else {}), g['vach']: vach, TD_GOC['vach']: td['vach'], TD_GOC['day']: td['day'], DAU_GOC['vien']: dau['vien']}),
          'chu': loc({**chinh, **(TOI_CHU if them else {}), g['chu']: chu, g['chu_phu']: chu_phu, TD_GOC['chu']: td['chu'], DAU_GOC['chu']: dau['chu']})}
    _NHO_BANG_DOI_MAU[khoa] = kq
    return kq


def mau_theo_tong(mau: str, loai: str = 'nen') -> str:
    """Một màu GỐC (viết theo tông mặc định) -> màu của tông đang dùng. loai: 'nen' / 'vien' / 'chu'. Dùng cho màu đặt trong MÔ HÌNH
    bảng / rich text (BackgroundRole, ForegroundRole, <span style>) mà bảng kiểu không đổi được (1.0.35)."""
    return _bang_doi_mau(TONG_NEN[0]).get(loai, {}).get(mau.upper(), mau)


def qmau_theo_tong(mau: str, loai: str = 'nen') -> QColor:
    return QColor(mau_theo_tong(mau, loai))
