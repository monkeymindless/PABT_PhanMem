"""Đối chiếu kết quả tính của phần mềm với số liệu file Excel và xuất báo cáo ra Excel."""
from __future__ import annotations
from dataclasses import dataclass, field

from . import nghiep_vu
from .tien import D

# openpyxl (~0,2 giây) chỉ nạp khi xuất báo cáo: màn hình chính gọi doi_chieu() mỗi lần mở / tải lại dự án


@dataclass
class KetQuaDoiChieu:
    ho: list = field(default_factory=list)          # mỗi phần tử: dict một hộ
    dong_lech: list = field(default_factory=list)   # dòng chi tiết có thành tiền khác Excel
    canh_bao: list = field(default_factory=list)    # (mã hộ, họ tên, nội dung)

    @property
    def so_ho_sua(self) -> int:
        return sum(1 for h in self.ho if h.get('sua'))

    @property
    def so_ho_lech(self) -> int:
        return sum(1 for h in self.ho if h['lech'])

    @property
    def khop_het(self) -> bool:
        return self.so_ho_lech == 0 and not self.dong_lech


def tong_excel_da_luu(con) -> dict:
    """Tổng từng hộ của file Excel đã lưu trong file dự án lúc nhập."""
    kq = {}
    for r in con.execute('SELECT * FROM tong_excel'):
        kq[r['ma_ho']] = {1: r['dat'], 2: r['nha'], 3: r['cay'], 4: r['ho_tro'], 5: r['thuong'], 'tong': r['tong']}
        kq[r['ma_ho']] = {k: (D(v) if v is not None else None) for k, v in kq[r['ma_ho']].items()}
    return kq


MOI_HO_TOI_DA = 50          # tính lại ít hộ: đọc riêng từng hộ (3 câu / hộ) thay vì quét cả bảng phương án


def doi_chieu(con, tong_excel: dict | None = None, ds_ma_ho: list | None = None) -> KetQuaDoiChieu:
    """So kết quả tính của phần mềm với số Excel (mặc định: số đã lưu lúc nhập). ds_ma_ho: chỉ các hộ này (màn hình chính tính
    lại các hộ vừa đổi - csdl.DauVetHo); None = cả dự án."""
    if tong_excel is None:
        tong_excel = tong_excel_da_luu(con)
    kq = KetQuaDoiChieu()
    sua = {r[0]: r[1] for r in con.execute('SELECT ma_ho, luu_luc FROM ho WHERE luu_luc IS NOT NULL')}
    # kết quả tính + kiểm tra mỗi hộ: dùng chung trên kết nối (nghiep_vu.ket_qua_ho; lưu một hộ chỉ tính lại hộ đó). Chỉ vài hộ
    # (DauVetHo) mà bảng nhớ đã cũ: tính riêng các hộ đó, không tính lại cả dự án
    kqh = nghiep_vu.ket_qua_ho(con) if ds_ma_ho is None else nghiep_vu.ket_qua_ho_san(con)
    if kqh is not None:
        chon = None if ds_ma_ho is None else set(ds_ma_ho)
        ds_kq = [x for m, x in kqh.items() if chon is None or m in chon]
    else:
        bc = nghiep_vu.BoiCanh.tu(con)
        if len(ds_ma_ho) <= MOI_HO_TOI_DA:
            ds_pa = []
            for m in ds_ma_ho:
                try:
                    ds_pa.append(nghiep_vu.doc_phuong_an(con, m))
                except KeyError:                                       # hộ không còn
                    pass
        else:
            ds_pa = nghiep_vu.doc_tat_ca_phuong_an(con, ds_ma_ho).values()
        ds_kq = [(nghiep_vu.tinh_pa(pa, bc), nghiep_vu.kiem_tra_pa(pa, bc)) for pa in ds_pa]   # đọc mỗi hộ MỘT lần
    for k, ds_canh_bao in ds_kq:
        ex = tong_excel.get(k.ma_ho)
        # hộ đã lưu lại trong phần mềm: phương án đã khác bản Excel lúc nhập, không tính là lệch
        dong = dict(ma_ho=k.ma_ho, ho_ten=k.ho_ten, muc=dict(k.muc), tong=k.tong, excel=ex, lech=False,
                    co_excel=ex is not None, sua=sua.get(k.ma_ho))
        if ex is not None and not dong['sua']:
            for m in (1, 2, 3, 4, 5):
                if ex.get(m) is not None and D(ex[m]) != k.muc[m]:
                    dong['lech'] = True
            if ex.get('tong') is not None and D(ex['tong']) != k.tong:
                dong['lech'] = True
        kq.ho.append(dong)
        for d in k.dong:
            if d.thanh_tien_excel is not None and d.thanh_tien_excel != d.thanh_tien:
                kq.dong_lech.append((k.ma_ho, k.ho_ten, d))
        for ct in ds_canh_bao:
            kq.canh_bao.append((k.ma_ho, k.ho_ten, ct))
    return kq


_SO = '#,##0'


def xuat_bao_cao(kq: KetQuaDoiChieu, duong_dan, ten_du_an: str = '', nguon: str = '', ra_soat: list | None = None) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    _manh = Side(style='thin', color='999999')
    _VIEN = Border(left=_manh, right=_manh, top=_manh, bottom=_manh)
    _DO = PatternFill('solid', fgColor='F8CBAD')
    _XANH = PatternFill('solid', fgColor='E2EFDA')

    def _tieu_de(ws, hang, cot_rong):
        for i, (t, w) in enumerate(cot_rong, start=1):
            c = ws.cell(hang, i, t)
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1F4E78')
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            c.border = _VIEN
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.row_dimensions[hang].height = 32
        ws.freeze_panes = ws.cell(hang + 1, 1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'TONG_HO'
    ws['A1'] = 'BÁO CÁO ĐỐI CHIẾU PHẦN MỀM PABT VỚI FILE EXCEL'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f'Dự án: {ten_du_an}'
    ws['A3'] = (f'Nguồn: {nguon}  |  {len(kq.ho)} hộ, {sum(1 for h in kq.ho if h["tong"] > 0)} hộ có phương án  |  '
                f'{"KHỚP 100%" if kq.khop_het else f"LỆCH {kq.so_ho_lech} hộ, {len(kq.dong_lech)} dòng"}'
                f'{f" (trừ {kq.so_ho_sua} hộ đã sửa trong phần mềm)" if kq.so_ho_sua else ""}  |  '
                f'{len(kq.canh_bao)} điểm cần xem lại')
    ws['A3'].font = Font(bold=True, color='006100' if kq.khop_het else 'C00000')
    cot = [('Mã hộ', 8), ('Họ và tên', 28), ('1. Đất', 14), ('2. Nhà, CT', 14), ('3. Cây trồng', 14), ('4. Hỗ trợ', 14),
           ('5. Thưởng', 13), ('TỔNG (phần mềm)', 16), ('TỔNG (Excel)', 16), ('Chênh lệch', 13), ('Kết quả', 12)]
    _tieu_de(ws, 5, cot)
    r = 6
    for h in kq.ho:
        ex = h['excel'] or {}
        tong_ex = ex.get('tong')
        vals = [h['ma_ho'], h['ho_ten']] + [float(h['muc'][m]) for m in (1, 2, 3, 4, 5)] + [
            float(h['tong']), float(tong_ex) if tong_ex is not None else None,
            float(h['tong'] - tong_ex) if tong_ex is not None else None,
            'Không có số Excel' if not h['co_excel'] else 'Sửa trong phần mềm' if h.get('sua') else ('LỆCH' if h['lech'] else 'Khớp')]
        for i, v in enumerate(vals, start=1):
            c = ws.cell(r, i, v)
            c.border = _VIEN
            if 3 <= i <= 10:
                c.number_format = _SO
        ws.cell(r, 11).fill = _DO if h['lech'] else _XANH
        r += 1
    ws.cell(r, 2, 'TỔNG CỘNG').font = Font(bold=True)
    for i in range(3, 11):
        if i == 10:
            continue
        col = get_column_letter(i)
        c = ws.cell(r, i, f'=SUM({col}6:{col}{r - 1})')
        c.number_format = _SO
        c.font = Font(bold=True)

    ws2 = wb.create_sheet('DONG_LECH')
    _tieu_de(ws2, 1, [('Mã hộ', 8), ('Họ và tên', 26), ('STT', 7), ('Tên', 46), ('SL', 10), ('Đơn giá', 14),
                      ('Thành tiền phần mềm', 16), ('Thành tiền Excel', 16)])
    for i, (ma, ten, d) in enumerate(kq.dong_lech, start=2):
        for j, v in enumerate([ma, ten, d.stt, d.ten, float(d.so_luong), float(d.don_gia), float(d.thanh_tien),
                               float(d.thanh_tien_excel)], start=1):
            c = ws2.cell(i, j, v)
            c.border = _VIEN
            if j >= 5:
                c.number_format = _SO if j != 5 else '#,##0.0##'
    if not kq.dong_lech:
        ws2.cell(2, 1, 'Không có dòng nào lệch: mọi thành tiền phần mềm tính lại đều bằng thành tiền trong file Excel.')

    ws3 = wb.create_sheet('CAN_XEM_LAI')
    _tieu_de(ws3, 1, [('Mã hộ', 8), ('Họ và tên', 26), ('Nội dung cần xem lại', 110)])
    for i, (ma, ten, ct) in enumerate(kq.canh_bao, start=2):
        for j, v in enumerate([ma, ten, ct], start=1):
            c = ws3.cell(i, j, v)
            c.border = _VIEN
            c.alignment = Alignment(wrap_text=True, vertical='top')

    if ra_soat is not None:
        ws4 = wb.create_sheet('RA_SOAT_GIA')
        _tieu_de(ws4, 1, [('Mã hộ', 8), ('Họ và tên', 24), ('STT', 7), ('Tên tài sản, khoản', 46), ('ĐVT', 8), ('Đơn giá', 14),
                          ('Nguồn giá', 13), ('Mã tương đương', 12), ('Căn cứ giá', 50), ('Cần rà soát', 34)])
        for i, x in enumerate(ra_soat, start=2):
            for j, v in enumerate([x['ma_ho'], x['ho_ten'], x['stt'], x['ten'], x['dvt'], float(x['don_gia']), x['nguon'],
                                   x['ma_tuong_duong'], x['can_cu_gia'], x['ghi_chu_ra_soat']], start=1):
                c = ws4.cell(i, j, v)
                c.border = _VIEN
                c.alignment = Alignment(wrap_text=True, vertical='top')
                if j == 6:
                    c.number_format = _SO
            if 'chưa ghi căn cứ' in x['ghi_chu_ra_soat']:
                ws4.cell(i, 10).fill = _DO
        if not ra_soat:
            ws4.cell(2, 1, 'Không có dòng áp giá tương đương, nhập tay hoặc đơn giá khác danh mục.')
    wb.save(str(duong_dan))
