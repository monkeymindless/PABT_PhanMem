"""Ghi file .xlsx nhanh cho bảng lớn (phương án đột phá 7 - tốc độ, người dùng 30/10/2026). Không Qt.

openpyxl ghi từng ô qua bộ ghi XML tăng dần (mỗi ô vài lớp đối tượng) - bảng tổng hợp 3.000 hộ ~150.000 ô mất ~1,2 s chỉ để ghi. Ở đây
openpyxl VẪN ghi mọi thứ khác (kiểu, ô gộp, cột, thiết lập in, tên vùng in, định dạng có điều kiện...) với trang tính tạm RỖNG ô; phần
<sheetData> (các ô) dựng bằng chuỗi theo ĐÚNG quy tắc của openpyxl.cell._writer (inlineStr, safe_string, xml:space, mã kiểu style_id)
rồi chèn vào file. tests/test_ghi_xlsx_nhanh so từng ô / kiểu / ô gộp / dòng / cột với wb.save thường.

Chỉ dùng cho trang tính >= NGUONG_O ô và không có ô ngày giờ, chữ nhiều định dạng, công thức mảng, siêu liên kết, chú thích (gặp thì
trang đó ghi kiểu thường). Gọi qua an_toan.luu_xlsx (một cổng lưu file Excel xuất ra)."""
from __future__ import annotations

import io
import re
import zipfile

NGUONG_O = 20000                     # trang tính nhỏ hơn: wb.save thường (khác biệt thời gian không đáng kể)
MUC_NEN = 5                          # mức nén zlib của trang tính lớn (6 = mặc định: chậm hơn, file nhỏ hơn rất ít)
_THAY_CHU = str.maketrans({'&': '&amp;', '<': '&lt;', '>': '&gt;'})
_THAY_THUOC_TINH = str.maketrans({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\n': '&#10;', '\r': '&#13;',
                                  '\t': '&#09;'})


def _dung_duoc(ws) -> bool:
    """Trang tính ghi nhanh được: đủ lớn và mọi ô thuộc loại bộ ghi này dựng giống openpyxl."""
    if len(ws._cells) < NGUONG_O:
        return False
    for c in ws._cells.values():
        if c.data_type not in ('n', 's', 'f', 'b', 'e') or c.hyperlink is not None or c._comment is not None:
            return False
        v = c._value
        if c.data_type == 's' and v is not None and not isinstance(v, str):
            return False                                    # CellRichText
        if c.data_type == 'f' and not isinstance(v, str):
            return False                                    # ArrayFormula / DataTableFormula
    return True


def _sheet_data(ws) -> str:
    """<sheetData>…</sheetData> của trang tính - cùng nội dung openpyxl.worksheet._writer.write_rows ghi."""
    from openpyxl.compat import safe_string
    from openpyxl.utils import get_column_letter
    hang = {}
    for (r, cot), c in sorted(ws._cells.items()):
        hang.setdefault(r, []).append((cot, c))
    for r in ws.row_dimensions.keys():
        hang.setdefault(r, [])
    chu_cot = {}
    ra = ['<sheetData>']
    them = ra.append
    for r in sorted(hang):
        tt = ''.join(f' {k}="{str(v).translate(_THAY_THUOC_TINH)}"' for k, v in ws.row_dimensions.get(r, {}))
        o = hang[r]
        if not o:
            them(f'<row r="{r}"{tt}/>')
            continue
        them(f'<row r="{r}"{tt}>')
        for cot, c in o:
            v = c._value
            co_kieu = c.has_style
            if v is None and not co_kieu:
                continue
            ten = chu_cot.get(cot)
            if ten is None:
                ten = chu_cot[cot] = get_column_letter(cot)
            loai = c.data_type
            dau = f'<c r="{ten}{r}"' + (f' s="{c.style_id}"' if co_kieu else '')
            if loai == 's':
                dau += ' t="inlineStr"'
            elif loai != 'f':
                dau += f' t="{loai}"'
            if v is None or v == '':
                them(dau + '/>')
            elif loai == 'f':
                them(f'{dau}><f>{v[1:].translate(_THAY_CHU)}</f><v/></c>')
            elif loai == 's':
                gon = v.strip()
                kg = ' xml:space="preserve"' if gon and gon != v else ''
                them(f'{dau}><is><t{kg}>{v.translate(_THAY_CHU)}</t></is></c>')
            else:
                them(f'{dau}><v>{safe_string(v).translate(_THAY_CHU)}</v></c>')
        them('</row>')
    ra.append('</sheetData>')
    return ''.join(ra)


def _gop_rieng(ws) -> bool:
    """Ô gộp ghi bằng chuỗi được khi ngay sau <sheetData> không có phần tử nào openpyxl ghi trước <mergeCells> (bảo vệ trang tính,
    kịch bản, lọc tự động) - vị trí chèn chắc chắn đúng thứ tự lược đồ."""
    return bool(ws.merged_cells) and not ws.protection.sheet and not ws.scenarios and not ws.auto_filter


def _merge_cells(ws) -> str:
    ds = [str(r) for r in ws.merged_cells.ranges]
    return f'<mergeCells count="{len(ds)}">' + ''.join(f'<mergeCell ref="{r}"/>' for r in ds) + '</mergeCells>'


_RE_SHEET_DATA = re.compile(r'<sheetData\s*/>|<sheetData>\s*</sheetData>')
_RE_DIMENSION = re.compile(r'<dimension ref="[^"]*"\s*/>')


def luu(wb, duong_dan) -> int:
    """wb.save với các trang tính lớn ghi nhanh. Trả số trang tính đã ghi nhanh (0 = ghi thường toàn bộ)."""
    lon = [ws for ws in wb.worksheets if _dung_duoc(ws)]
    if not lon:
        wb.save(str(duong_dan))
        return 0
    from openpyxl.worksheet.cell_range import MultiCellRange
    phan = {}
    giu = {}
    for ws in lon:                                          # dựng ô TRƯỚC wb.save: style_id thêm kiểu vào bảng kiểu sẽ được ghi
        sd = _sheet_data(ws)
        gop = _gop_rieng(ws)
        if gop:
            sd += _merge_cells(ws)
        phan[ws.title] = (sd, ws.calculate_dimension())
        giu[ws.title] = (ws._cells, ws.row_dimensions, ws.merged_cells, gop)
    tam = io.BytesIO()
    try:
        for ws in lon:
            ws._cells, ws.row_dimensions = {}, {}
            if giu[ws.title][3]:
                ws.merged_cells = MultiCellRange()
        wb.save(tam)
    finally:
        for ws in lon:
            ws._cells, ws.row_dimensions, ws.merged_cells = giu[ws.title][:3]
    duong = {ws.path.lstrip('/'): ws.title for ws in lon}
    ra = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(tam.getvalue())) as z, zipfile.ZipFile(ra, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as d:
        for info in z.infolist():
            du = z.read(info.filename)
            if info.filename in duong:
                sd, dim = phan[duong[info.filename]]
                xml = du.decode('utf-8')
                xml, n = _RE_SHEET_DATA.subn(lambda _m: sd, xml, count=1)
                if n != 1:
                    raise RuntimeError(f'Không tìm thấy <sheetData> trong {info.filename}')
                xml = _RE_DIMENSION.sub(f'<dimension ref="{dim}"/>', xml, count=1)
                d.writestr(info.filename, xml.encode('utf-8'), compress_type=zipfile.ZIP_DEFLATED, compresslevel=MUC_NEN)
            else:
                d.writestr(info, du)
    tmp = f'{duong_dan}.dang_ghi'
    with open(tmp, 'wb') as f:
        f.write(ra.getvalue())
    import os
    os.replace(tmp, str(duong_dan))
    return len(lon)
