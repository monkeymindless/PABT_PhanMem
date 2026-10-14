"""Bộ dựng PDF dự phòng bằng Qt (0.9.87): máy không có Microsoft Excel, hoặc Excel lỗi / treo khi xuất PDF, thì Xem trước A4
(F4, Trung tâm xuất bản) vẫn hiện được bản in.

Đọc CHÍNH file .xlsx bản in phần mềm vừa điền (cùng mẫu, cùng số liệu - không dựng lại nội dung riêng), chuyển vùng in thành
bảng HTML (rộng cột, ô gộp, cột / dòng ẩn, chữ đậm / nghiêng / cỡ chữ, căn lề, khung ô) rồi QTextDocument in ra QPdfWriter khổ
A4 theo hướng giấy của mẫu. Là bản GẦN ĐÚNG: đường kẻ vẽ (hình), định dạng có điều kiện, ngắt trang của Excel không có; công thức
chỉ tính SUM đơn giản. Bản in / PDF chính thức vẫn qua Excel (in_an.chay_excel).
Chạy ở LUỒNG GIAO DIỆN (QTextDocument dùng phông chữ của Qt)."""
from __future__ import annotations
import html
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

NHAN_GAN_DUNG = 'Bản xem trước gần đúng (máy không dùng được Microsoft Excel)'
_RE_SUM = re.compile(r'^=\s*SUM\(\s*([A-Z]+)(\d+)\s*:\s*([A-Z]+)(\d+)\s*\)\s*$', re.I)


_RE_DK = re.compile(r'^\[(=|<>|<=|>=|<|>)(-?[\d.]+)\]')


def _chon_phan(d: Decimal, dinh_dang: str) -> str:
    """Phần định dạng Excel áp cho số d ("[=0]0;#,##0.0#", "#,##0;-#,##0")."""
    phan = (dinh_dang or 'General').split(';')
    tu_do = []
    for x in phan:
        m = _RE_DK.match(x)
        if m is None:
            tu_do.append(x)
            continue
        so = Decimal(m.group(2))
        if {'=': d == so, '<>': d != so, '<': d < so, '>': d > so, '<=': d <= so, '>=': d >= so}[m.group(1)]:
            return x[m.end():]
    if not tu_do:
        return 'General'
    return tu_do[1] if d < 0 and len(tu_do) > 1 else tu_do[0]


def _so_vn(v, dinh_dang: str) -> str:
    """Số theo định dạng của ô, kiểu Việt Nam (nghìn '.', thập phân ','); có % thì nhân 100."""
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        return str(v)
    f = re.sub(r'\[[^\]]*\]|"[^"]*"|_.|\\.|\*.', '', _chon_phan(d, dinh_dang)).strip()
    if f in ('@', ''):
        return str(v)
    phan_tram = '%' in f
    if phan_tram:
        d *= 100
    if f.lower() == 'general':
        toi_thieu, toi_da, nghin = 0, (0 if d == d.to_integral_value() else min(4, -d.normalize().as_tuple().exponent)), False
    else:
        nguyen, _, le = f.replace('%', '').partition('.')
        toi_thieu, toi_da, nghin = le.count('0'), len(re.findall(r'[0#?]', le)), ',' in nguyen
    s = f'{abs(d):,.{toi_da}f}' if nghin else f'{abs(d):.{toi_da}f}'
    if toi_da > toi_thieu and '.' in s:
        nguyen_s, le_s = s.split('.')
        le_s = le_s.rstrip('0').ljust(toi_thieu, '0')
        s = nguyen_s + ('.' + le_s if le_s else '')
    s = s.replace(',', ' ').replace('.', ',').replace(' ', '.')
    return ('-' if d < 0 else '') + s + ('%' if phan_tram else '')


def _gia_tri(ws, o) -> str:
    v = o.value
    if v is None:
        return ''
    if isinstance(v, str):
        if v.startswith('='):
            m = _RE_SUM.match(v)
            if not m:
                return ''
            from openpyxl.utils import column_index_from_string as cs
            tong = Decimal(0)
            for r in range(int(m.group(2)), int(m.group(4)) + 1):
                for c in range(cs(m.group(1)), cs(m.group(3)) + 1):
                    x = ws._cells.get((r, c))
                    if x is not None and isinstance(x.value, (int, float, Decimal)) and not isinstance(x.value, bool):
                        tong += Decimal(str(x.value))
            return _so_vn(tong, o.number_format)
        return v
    if isinstance(v, bool):
        return 'Có' if v else ''
    if isinstance(v, (int, float, Decimal)):
        return _so_vn(v, o.number_format)
    if hasattr(v, 'strftime'):
        return v.strftime('%d/%m/%Y')
    return str(v)


def _vung_in(ws):
    """(dòng đầu, cột đầu, dòng cuối, cột cuối) của vùng in (không có: vùng có chữ)."""
    from openpyxl.utils.cell import range_boundaries
    try:
        pa = ws.print_area
    except (AttributeError, ValueError):
        pa = None
    if pa:
        chu = pa[0] if isinstance(pa, (list, tuple)) else str(pa).split(',')[0]
        c1, r1, c2, r2 = range_boundaries(chu.split('!')[-1].replace('$', ''))
        return r1, c1, r2, c2
    return 1, 1, ws.max_row, ws.max_column


KHO_GIAY = {8: ('A3', 297.0, 420.0), 9: ('A4', 210.0, 297.0)}        # mã khổ giấy Excel -> (tên, rộng, cao mm)


def html_tu_xlsx(xlsx) -> tuple:
    """(html, trang) của sheet đầu file bản in. trang: dict(kho 'A4' / 'A3', ngang, le (trái, trên, phải, dưới) mm, he_so) -
    he_so < 1: thu nhỏ cho vừa bề ngang giấy như "Fit to width" / tỷ lệ in của Excel (bảng tổng hợp 25 cột)."""
    import openpyxl
    from openpyxl.utils import get_column_letter
    wb = openpyxl.load_workbook(xlsx)
    ws = wb.worksheets[0]
    r1, c1, r2, c2 = _vung_in(ws)
    cot_an = set()
    rong = {}
    for c in range(c1, c2 + 1):
        cd = ws.column_dimensions.get(get_column_letter(c))
        w = None
        if cd is not None:
            if cd.hidden:
                cot_an.add(c)
                continue
            w = cd.width
        rong[c] = float(w or 8.43)
    tong_rong = sum(rong.values()) or 1.0
    ps = ws.page_setup
    kho, rong_mm, cao_mm = KHO_GIAY.get(int(ps.paperSize or 9), KHO_GIAY[9])
    giay_ngang = (ps.orientation or '') == 'landscape'
    if giay_ngang:
        rong_mm, cao_mm = cao_mm, rong_mm
    pm = ws.page_margins
    le = tuple(round(float(x if x is not None else 0.5) * 25.4, 1) for x in (pm.left, pm.top, pm.right, pm.bottom))
    rong_in = (rong_mm - le[0] - le[2]) / 25.4 * 96          # điểm ảnh 96 dpi
    tu_nhien = sum(w * 7 + 5 for w in rong.values())         # bề rộng cột Excel (ký tự) -> điểm ảnh
    if ws.sheet_properties.pageSetUpPr is not None and ws.sheet_properties.pageSetUpPr.fitToPage:
        he_so = min(1.0, rong_in / tu_nhien) if tu_nhien else 1.0          # "vừa một trang bề ngang"
    else:
        he_so = float(ps.scale or 100) / 100                               # tỷ lệ in của mẫu (chi tiết: 78%)
    dong_an = {r for r in range(r1, r2 + 1) if ws.row_dimensions[r].hidden} if ws.row_dimensions else set()
    # ô gộp: ô đầu -> (số dòng, số cột HIỆN), các ô bị phủ bỏ qua
    gop, phu = {}, set()
    for m in ws.merged_cells.ranges:
        if m.max_row < r1 or m.min_row > r2:
            continue
        cot = [c for c in range(m.min_col, m.max_col + 1) if c not in cot_an and c1 <= c <= c2]
        dong = [r for r in range(m.min_row, m.max_row + 1) if r not in dong_an and r1 <= r <= r2]
        if not cot or not dong:
            continue
        gop[(dong[0], cot[0])] = (len(dong), cot)
        for r in dong:
            for c in cot:
                if (r, c) != (dong[0], cot[0]):
                    phu.add((r, c))
    # cột loại dòng (ẩn / ngoài vùng in) của mẫu chi tiết (H mục / T tổng): in đậm cả dòng (định dạng có điều kiện của Excel không đọc được)
    dam_dong = {r for (r, c), o in ws._cells.items() if (c in cot_an or c > c2) and r1 <= r <= r2 and o.value in ('H', 'T')}
    ds = ['<table width="100%" cellspacing="0" cellpadding="2" style="border-collapse: collapse;">']
    # hàng định cỡ (cao 0): Qt chỉ lấy bề rộng cột từ ô KHÔNG gộp - phần đầu mẫu toàn ô gộp nên thiếu hàng này cột chia đều
    ds.append('<tr>' + ''.join(f'<td width="{max(1, round(rong[c] / tong_rong * 100))}%" style="font-size: 1pt;"></td>'
                               for c in range(c1, c2 + 1) if c in rong) + '</tr>')
    for r in range(r1, r2 + 1):
        if r in dong_an:
            continue
        cao = ws.row_dimensions[r].height
        ds.append(f'<tr style="height: {float(cao or 15) * he_so:.0f}pt;">')
        for c in range(c1, c2 + 1):
            if c in cot_an or (r, c) in phu:
                continue
            o = ws._cells.get((r, c))
            nd, cac_cot = gop.get((r, c), (1, [c]))
            nc = len(cac_cot)
            w = sum(rong.get(x, 8.43) for x in cac_cot)
            the = [f'width="{max(1, round(w / tong_rong * 100))}%"']           # Qt chỉ nhận % số nguyên
            if nd > 1:
                the.append(f'rowspan="{nd}"')
            if nc > 1:
                the.append(f'colspan="{nc}"')
            kieu, chu = [], ''
            if o is not None:
                chu = _gia_tri(ws, o)
                f, a, b = o.font, o.alignment, o.border
                kieu.append(f'font-size: {float(f.sz or 12) * he_so:.1f}pt')
                if f.b or r in dam_dong:
                    kieu.append('font-weight: bold')
                if f.i:
                    kieu.append('font-style: italic')
                if f.u:
                    kieu.append('text-decoration: underline')
                ngang = a.horizontal or ('right' if isinstance(o.value, (int, float, Decimal)) else 'left')
                ngang = {'centerContinuous': 'center', 'distributed': 'left', 'general': 'left', 'fill': 'left'}.get(ngang, ngang)
                the.append(f'align="{ngang}"')
                the.append(f'valign="{ {"center": "middle", "top": "top"}.get(a.vertical or "bottom", "bottom") }"')
                for canh, ten in ((b.left, 'left'), (b.right, 'right'), (b.top, 'top'), (b.bottom, 'bottom')):
                    if canh is not None and canh.style:
                        kieu.append(f'border-{ten}: {"2" if canh.style in ("medium", "thick") else "1"}px solid black')
            noi = html.escape(chu).replace('\n', '<br/>')
            ds.append(f'<td {" ".join(the)} style="{"; ".join(kieu)}">{noi}</td>')
        ds.append('</tr>')
    ds.append('</table>')
    noi_dung = ('<html><head><meta charset="utf-8"/></head><body style="font-family: \'Times New Roman\', serif;">'
                + ''.join(ds) + '</body></html>')
    return noi_dung, dict(kho=kho, ngang=giay_ngang, le=le, he_so=he_so)


def xuat_pdf_du_phong_qt(xlsx, pdf) -> Path:
    """Dựng PDF (khổ giấy của mẫu) từ file bản in .xlsx bằng Qt (QTextDocument + QPdfWriter). Trả đường dẫn PDF. Lỗi -> ném lại (nơi gọi báo)."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument
    noi_dung, trang = html_tu_xlsx(xlsx)
    pdf = Path(pdf)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    w = QPdfWriter(str(pdf))
    w.setResolution(300)
    w.setTitle(Path(xlsx).stem)
    w.setCreator('PABT')
    kho = QPageSize.PageSizeId.A3 if trang['kho'] == 'A3' else QPageSize.PageSizeId.A4
    hl = QPageLayout(QPageSize(kho), QPageLayout.Orientation.Landscape if trang['ngang'] else QPageLayout.Orientation.Portrait,
                     QMarginsF(*trang['le']), QPageLayout.Unit.Millimeter)
    w.setPageLayout(hl)
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setHtml(noi_dung)
    # khổ giấy theo điểm ảnh 96 dpi (đơn vị bố cục của QTextDocument); print_ phóng theo độ phân giải của QPdfWriter
    vung = hl.paintRect(QPageLayout.Unit.Point)
    doc.setPageSize(QSizeF(vung.width() * 96 / 72, vung.height() * 96 / 72))
    doc.print_(w)
    del w                                               # đóng file PDF (QPdfWriter ghi xong khi bị hủy)
    return pdf
