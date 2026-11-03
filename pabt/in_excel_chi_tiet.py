"""Phương án chi tiết nhiều hộ trong MỘT file Excel, mỗi hộ một sheet (người dùng 30/10/2026: "trong mục in chi tiết bản Word, thêm cả
Excel - xuất một lúc nhiều phương án chi tiết ra Excel, 01 hộ là 1 sheet, tất cả trong 1 file").

Cùng số liệu, chữ với bản Word (in_word.du_lieu_chi_tiet: thông tin dự án / hộ, nguồn gốc, các dòng bảng mục III của du_lieu_in,
mẫu bổ sung / điều chỉnh, dự thảo). Bố cục dựng bằng mã (không file mẫu): A4 dọc, vừa bề ngang một trang, hàng tiêu đề bảng lặp mỗi
trang. Số tiền / số lượng / tỷ lệ là SỐ (cộng, lọc được trong Excel); chiều cao dòng tính theo chữ (in_an.so_dong_o)."""
from __future__ import annotations

import re
from pathlib import Path

from . import du_lieu_in

PHONG = 'Times New Roman'
CO_CHU = 12                 # thông tin hộ, nguồn gốc
CO_DAU = 12                 # cơ quan, quốc hiệu, số, ngày
CO_TEN = 14                 # tên văn bản
CO_BANG = 11                # bảng mục III
CO_GHI_CHU = 10             # cột ghi chú
RONG_COT = (6, 34, 8, 11, 13, 8, 15, 22)            # A..H (ký tự): STT, tên, ĐVT, SL, ĐG, tỷ lệ, thành tiền, ghi chú
SO_COT = len(RONG_COT)
CAO_DOAN_TOI_DA = 300       # pt: đoạn nguồn gốc dài hơn chia nhiều dòng Excel (Excel không cao quá 409 pt)
TEN_FILE = 'PHUONG_AN_CHI_TIET.xlsx'
TEN_SHEET_TOI_DA = 31       # Excel: tên sheet <= 31 ký tự, không có : \ / ? * [ ]


def ten_sheet(stt, ho_ten: str, da_dung: set) -> str:
    """Tên sheet "<STT>. <họ tên>" hợp lệ, không trùng (thêm " (2)"...)."""
    goc = re.sub(r'[:\\/?*\[\]]+', ' ', f'{stt}. {ho_ten}' if stt not in (None, '') else str(ho_ten or 'Hộ'))
    goc = ' '.join(goc.split()).strip("' ") or 'Hộ'
    ten, i = goc[:TEN_SHEET_TOI_DA], 2
    while ten.lower() in da_dung:
        hau = f' ({i})'
        ten, i = goc[:TEN_SHEET_TOI_DA - len(hau)] + hau, i + 1
    da_dung.add(ten.lower())
    return ten


def _so(v):
    """Giá trị ô số: Decimal -> int (không lẻ) / float; chữ giữ nguyên; trống -> None."""
    from decimal import Decimal
    if v is None or v == '':
        return None
    if isinstance(v, str):
        return v
    d = Decimal(str(v))
    return int(d) if d == d.to_integral_value() else float(d)


def _dinh_dang_ty_le(v) -> str:
    from decimal import Decimal
    try:
        d = Decimal(str(v)) * 100
    except Exception:                                   # noqa: BLE001
        return '0%'
    return '0%' if d == d.to_integral_value() else '0.0#%'


class _Ve:
    """Ghi một sheet: con trỏ dòng, ô gộp, kiểu chữ, viền, chiều cao theo chữ."""

    def __init__(self, ws):
        from openpyxl.styles import Alignment, Border, Font, Side
        from openpyxl.utils import get_column_letter
        self.ws, self.r = ws, 1
        self.Font, self.Alignment = Font, Alignment
        mong = Side(style='thin', color='000000')   # RGB đen: WPS / máy khác không nuốt nét như Side không màu
        self.vien = Border(left=mong, right=mong, top=mong, bottom=mong)
        for i, w in enumerate(RONG_COT, start=1):
            cd = ws.column_dimensions[get_column_letter(i)]
            cd.width, cd.min, cd.max = w, i, i          # min = max: in_an._px_cot đọc bề rộng theo dải cột
        from . import in_an
        self.in_an = in_an
        self.do = in_an._ham_do_chu()

    def rong(self, c1: int, c2: int) -> float:
        return self.in_an._rong_vung(self.ws, c1, c2)

    def so_dong(self, chu, c1: int, c2: int, co: float, dam: bool = False) -> int:
        if not isinstance(chu, str):
            return 1
        return sum(self.in_an.so_dong_o(d or ' ', self.rong(c1, c2), PHONG, co, dam, self.do) for d in chu.split('\n'))

    def o(self, c1: int, c2: int, chu, co: float = CO_CHU, dam: bool = False, nghieng: bool = False, can: str = 'left',
          doc: str = 'center', vien: bool = False, gach: bool = False, so=None, r: int | None = None):
        r = self.r if r is None else r
        x = self.ws.cell(r, c1, chu)
        x.font = self.Font(name=PHONG, size=co, bold=dam, italic=nghieng, underline='single' if gach else None)
        x.alignment = self.Alignment(horizontal=can, vertical=doc, wrap_text=True)
        if so:
            x.number_format = so
        if c2 > c1:
            self.ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
        if vien:
            for c in range(c1, c2 + 1):
                self.ws.cell(r, c).border = self.vien
        return x

    def cao(self, so_dong: int, co: float, them: float = 4, r: int | None = None):
        r = self.r if r is None else r
        h = max(so_dong, 1) * co * 1.25 + them
        cu = self.ws.row_dimensions[r].height or 0
        self.ws.row_dimensions[r].height = min(409, max(cu, h))

    def xuong(self, n: int = 1):
        self.r += n


def _ve_sheet(ws, x, du_thao: bool) -> None:
    """Một hộ: phần đầu, mục I, II, bảng mục III, IV, chữ ký."""
    from .in_word import nhom_ghi_chu_dat
    from .tien import dinh_dang_so_luong
    v = _Ve(ws)
    da, ttho = x.da, x.ttho
    # ---- cơ quan (A:C) | quốc hiệu (D:H)
    tren = [d for d in str(x.cap_tren or '').split('\n') if d.strip()]
    trai = [(d.strip().upper(), False, False) for d in tren] + [(x.ten_cq, True, True)]
    phai = [('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', True, False), ('Độc lập - Tự do - Hạnh phúc', True, True)]
    for i in range(max(len(trai), len(phai))):
        if i < len(trai):
            v.o(1, 3, trai[i][0], CO_DAU, dam=trai[i][1], gach=trai[i][2], can='center')
        if i < len(phai):
            v.o(4, 8, phai[i][0], CO_DAU, dam=phai[i][1], gach=phai[i][2], can='center')
        v.cao(max(v.so_dong(trai[i][0] if i < len(trai) else '', 1, 3, CO_DAU, True),
                  v.so_dong(phai[i][0] if i < len(phai) else '', 4, 8, CO_DAU, True)), CO_DAU)
        v.xuong()
    v.o(1, 3, x.so, CO_DAU, can='center')
    v.o(4, 8, x.ngay, CO_DAU, nghieng=True, can='center')
    v.cao(1, CO_DAU, 6)
    v.xuong()
    if du_thao:
        v.o(1, 3, '(DỰ THẢO)', CO_DAU, dam=True, can='center')
        v.xuong()
    v.xuong()
    # ---- tên văn bản, trích yếu, dự án
    from . import in_word
    for chu, co in ((x.ten_van_ban, CO_TEN), *((t, CO_CHU + 1) for t in (in_word.TRICH_YEU_DONG or (in_word.TRICH_YEU,)) if t),
                    (x.dong_du_an, CO_CHU + 1)):
        v.o(1, SO_COT, chu, co, dam=True, can='center')
        v.cao(v.so_dong(chu, 1, SO_COT, co, True), co)
        v.xuong()
    v.xuong()
    # ---- I. chủ sử dụng
    v.o(1, SO_COT, du_lieu_in.tieu_de_muc_i(x.to_chuc), CO_CHU, dam=True)
    v.cao(1, CO_CHU)
    v.xuong()
    for k, (nhan, gt) in enumerate(x.hang_i):
        v.o(1, 2, nhan, CO_CHU, can='left')
        v.o(3, SO_COT, gt or '', CO_CHU, dam=k == 0, can='left')
        v.ws.cell(v.r, 3).number_format = '@'           # số CCCD, điện thoại: chữ (không mất số 0 đầu, không thành 1,23E+11)
        v.cao(max(v.so_dong(nhan, 1, 2, CO_CHU), v.so_dong(str(gt or ''), 3, SO_COT, CO_CHU, k == 0)), CO_CHU)
        v.xuong()
    # ---- II. nguồn gốc: mỗi đoạn một dòng Excel (đoạn rất dài chia theo câu)
    v.o(1, SO_COT, du_lieu_in.TIEU_DE_MUC_II, CO_CHU, dam=True)
    v.cao(1, CO_CHU)
    v.xuong()
    for doan in (d.strip() for d in str(ttho['nguon_goc'] or '').split('\n') if d.strip()):
        for phan in _chia_doan(v, doan):
            v.o(1, SO_COT, phan, CO_CHU, can='justify', doc='top')
            v.ws.cell(v.r, 1).alignment = v.Alignment(horizontal='justify', vertical='top', wrap_text=True, indent=2)
            v.cao(v.so_dong(phan, 1, SO_COT, CO_CHU) + (1 if len(phan) > 60 else 0), CO_CHU)
            v.xuong()
    # ---- III. bảng
    if x.dieu_chinh and str(x.x_lan.ghi_chu or '').strip():
        chu = 'Lý do điều chỉnh: ' + ' '.join(x.x_lan.ghi_chu.split())
        v.o(1, SO_COT, chu, CO_CHU, can='justify')
        v.cao(v.so_dong(chu, 1, SO_COT, CO_CHU), CO_CHU)
        v.xuong()
    v.o(1, SO_COT, 'III. Bảng tính toán bồi thường, hỗ trợ', CO_CHU, dam=True)
    v.cao(1, CO_CHU)
    v.xuong()
    r_tieu_de = v.r
    for c, t in enumerate(x.tieu_de_cot, start=1):
        v.o(c, c, t, CO_BANG, dam=True, can='center', vien=True)
    v.cao(max(v.so_dong(t, c, c, CO_BANG, True) for c, t in enumerate(x.tieu_de_cot, start=1)), CO_BANG, 6)
    v.ws.print_title_rows = f'{r_tieu_de}:{r_tieu_de}'
    v.xuong()
    dong = x.dong
    gop_gc = nhom_ghi_chu_dat(dong)
    muc_sl = None
    dau_gop = None
    for i, d in enumerate(dong):
        loai, gt = d[0], d[1]
        cach_tinh = d[2] if len(d) > 2 and isinstance(d[2], str) else ''
        if loai == 'H':
            muc_sl = 2 if du_lieu_in.la_muc_nha(gt) else None
        if loai == 'G' and len(d) > 2 and isinstance(d[2], int):
            muc_sl = 2 if d[2] == 2 else None
        dam = loai in ('H', 'T', 'G', 'R')             # 1.0.57: dòng thưởng in đậm
        if loai in ('G', 'S'):
            v.o(1, 1, '' if gt[0] is None else str(gt[0]), CO_BANG, dam=dam, can='center', vien=True)
            v.o(2, 6, gt[1] or '', CO_BANG, dam=dam, vien=True)
            v.o(7, 7, _so(gt[6]) if gt[6] else '-', CO_BANG, dam=dam, can='right', vien=True, so='#,##0')
            v.o(8, 8, gt[7] or '', CO_GHI_CHU, can='center', vien=True)
            if loai == 'G':
                from openpyxl.styles import PatternFill
                for c in range(1, SO_COT + 1):
                    v.ws.cell(v.r, c).fill = PatternFill('solid', fgColor='D9D9D9')
            v.cao(max(v.so_dong(gt[1] or '', 2, 6, CO_BANG, dam), v.so_dong(gt[7] or '', 8, 8, CO_GHI_CHU)), CO_BANG, 6)
            v.xuong()
            continue
        if loai == 'T':
            v.o(1, 6, gt[1], CO_BANG, dam=True, can='center', vien=True)
            v.o(7, 7, _so(gt[6]), CO_BANG, dam=True, can='right', vien=True, so='#,##0')
            v.o(8, 8, '', CO_BANG, vien=True)
            v.cao(1, CO_BANG, 8)
            v.xuong()
            continue
        v.o(1, 1, '' if gt[0] is None else str(gt[0]), CO_BANG, dam=dam, can='center', vien=True)   # STT căn giữa (1.0.57)
        v.o(2, 2, gt[1] or '', CO_BANG, dam=dam, vien=True)
        if cach_tinh:
            v.o(3, 6, cach_tinh, CO_BANG, dam=dam, can='center', vien=True)
        else:
            v.o(3, 3, gt[2] or '', CO_BANG, dam=dam, can='center', vien=True)
            sl = _so(gt[3])
            v.o(4, 4, sl, CO_BANG, dam=dam, can='right', vien=True, so=dinh_dang_so_luong(muc_sl) if not isinstance(sl, str) else None)
            v.o(5, 5, _so(gt[4]), CO_BANG, dam=dam, can='right', vien=True, so='#,##0')
            tl = _so(gt[5])
            v.o(6, 6, tl, CO_BANG, dam=dam, can='center', vien=True,
                so=_dinh_dang_ty_le(gt[5]) if tl is not None and not isinstance(tl, str) else None)
        v.o(7, 7, _so(gt[6]), CO_BANG, dam=dam or loai == 'R', can='right', vien=True, so='#,##0')
        gd = gop_gc.get(i)
        if gd == 'restart':
            dau_gop = v.r
        v.o(8, 8, (gt[7] or '') if gd != 'continue' else None, CO_GHI_CHU, can='left', vien=True)
        if gd == 'continue' and dau_gop is not None and (i + 1 >= len(dong) or gop_gc.get(i + 1) != 'continue'):
            v.ws.merge_cells(start_row=dau_gop, start_column=8, end_row=v.r, end_column=8)
            v.ws.cell(dau_gop, 8).alignment = v.Alignment(horizontal='center', vertical='center', wrap_text=True)
        so_dong = max(v.so_dong(gt[1] or '', 2, 2, CO_BANG, dam), v.so_dong(cach_tinh, 3, 6, CO_BANG, dam) if cach_tinh else 1,
                      v.so_dong(gt[7] or '', 8, 8, CO_GHI_CHU) if gd is None else 1)
        v.cao(so_dong, CO_BANG, 6)
        v.xuong()
    # ---- IV. tái định cư
    chu = du_lieu_in.NHAN_TDC + ' ' + str(ttho['tai_dinh_cu'] or '').strip()
    v.o(1, 1, x.nhan_tdc, CO_BANG, dam=True, can='center', vien=True)
    v.o(2, SO_COT, chu.strip(), CO_BANG, can='justify', vien=True)
    v.cao(v.so_dong(chu, 2, SO_COT, CO_BANG), CO_BANG, 6)
    v.xuong()
    # ---- chữ ký (bản dự thảo không có)
    if not du_thao:
        v.xuong()
        for c1, c2, chuc, ten in ((1, 2, 'LẬP BIỂU', da['nguoi_lap']), (3, 5, 'KIỂM TRA', da['nguoi_kiem_tra']),
                                  (6, 8, da['CHUC_VU_KY'], da['nguoi_ky'])):
            v.o(c1, c2, chuc, CO_CHU, dam=True, can='center')
            v.o(c1, c2, ten or '', CO_CHU, dam=True, can='center', r=v.r + 5)
        v.cao(max(v.so_dong(da['CHUC_VU_KY'] or '', 6, 8, CO_CHU, True), 1), CO_CHU)
        v.xuong(6)
    # ---- in: A4 dọc, vừa một trang bề ngang, lề theo bản Word
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = 'portrait'
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    le = in_word.LE_MM or {}
    for k, ten in (('left', 'trai'), ('right', 'phai'), ('top', 'tren'), ('bottom', 'duoi')):
        setattr(ws.page_margins, k, round(float(le.get(ten, 15)) / 25.4, 3))
    ws.sheet_view.showGridLines = False


def _chia_doan(v: _Ve, doan: str) -> list:
    """Đoạn quá cao cho một dòng Excel (CAO_DOAN_TOI_DA) -> nhiều phần, cắt sau dấu hết câu."""
    cau = re.split(r'(?<=[.!?;])\s+', doan)
    kq, cur = [], ''
    for c in cau:
        thu = f'{cur} {c}'.strip()
        if cur and v.so_dong(thu, 1, SO_COT, CO_CHU) * CO_CHU * 1.25 > CAO_DOAN_TOI_DA:
            kq.append(cur)
            cur = c
        else:
            cur = thu
    if cur:
        kq.append(cur)
    return kq


def xuat_chi_tiet_xlsx(con, ds_ma_ho: list, file_ra, bc=None, du_thao: bool = False, lan='moi_nhat', bao_tien_do=None) -> Path:
    """Một file .xlsx: mỗi hộ của ds_ma_ho một sheet (theo thứ tự danh sách). bao_tien_do(i, n) trả True = dừng (ghi các hộ đã xong).
    Trả đường dẫn file."""
    from openpyxl import Workbook

    from . import an_toan, in_word
    from .nghiep_vu import BoiCanh
    bc = bc or BoiCanh.tu(con)
    wb = Workbook()
    wb.remove(wb.active)
    da_dung = set()
    for i, ma in enumerate(ds_ma_ho, start=1):
        x = in_word.du_lieu_chi_tiet(con, ma, bc, du_thao=du_thao, lan=lan)
        r = con.execute('SELECT thu_tu FROM ho WHERE ma_ho = ?', (ma,)).fetchone()
        ws = wb.create_sheet(ten_sheet(r[0] if r else i, x.ttho['ho_ten'], da_dung))
        _ve_sheet(ws, x, du_thao)
        if bao_tien_do and bao_tien_do(i, len(ds_ma_ho)):
            break
    if not wb.worksheets:
        wb.create_sheet('Trống')
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    an_toan.luu_xlsx(wb, file_ra)
    return file_ra
