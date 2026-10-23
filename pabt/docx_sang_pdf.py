"""PDF dự phòng của bản Word (1.0.19): dựng PDF từ file .docx do in_word tạo, bằng Qt (QTextDocument + QPdfWriter) - dùng khi máy không có
Microsoft Word hoặc Word lỗi. KHÔNG đọc Excel: chỉ hiểu phần OpenXML mà in_word / van_ban_trinh tự sinh (đoạn, chạy chữ đậm / nghiêng /
gạch chân / cỡ chữ, ngắt dòng, bảng có gộp ô, viền ô, viền dưới đoạn), nên gần đúng bản Word nhưng không thay thế Word.

Đổi đơn vị: twip (1/20 pt) -> pt; QTextDocument bố cục theo điểm ảnh 96 dpi nên px = pt x 96 / 72 (khổ trang cũng đặt như vậy, xem
pdf_du_phong.xuat_pdf_du_phong_qt)."""
from __future__ import annotations

import zipfile
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from . import an_toan

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PX = 96 / 72                                   # điểm ảnh trên một pt
CAN = {'both': 'justify', 'center': 'center', 'right': 'right', 'left': 'left'}


def _g(e, ten, mac_dinh=None):
    """Giá trị thuộc tính w:val của phần tử con `ten` (hoặc mac_dinh)."""
    c = e.find(W + ten) if e is not None else None
    return c.get(W + 'val', mac_dinh) if c is not None else mac_dinh


def _tw(v, mac_dinh=0) -> float:
    try:
        return float(v) / 20
    except (TypeError, ValueError):
        return mac_dinh


def _chay(r) -> str:
    pr = r.find(W + 'rPr')
    kieu = []
    if pr is not None:
        if pr.find(W + 'b') is not None:
            kieu.append('font-weight:bold')
        if pr.find(W + 'i') is not None:
            kieu.append('font-style:italic')
        if _g(pr, 'u') in ('single', 'thick', 'double'):
            kieu.append('text-decoration:underline')
        sz = _g(pr, 'sz')
        if sz:
            kieu.append(f'font-size:{int(sz) / 2:g}pt')
    ra = []
    for c in r:
        if c.tag == W + 't':
            ra.append(escape(c.text or '').replace('  ', '&nbsp; '))
        elif c.tag == W + 'br':
            ra.append('<br/>')
        elif c.tag == W + 'tab':
            ra.append('&nbsp;&nbsp;&nbsp;&nbsp;')
    return f'<span style="{";".join(kieu)}">{"".join(ra)}</span>' if kieu else ''.join(ra)


def _doan(p, rong_pt: float) -> str:
    """Một w:p -> HTML. rong_pt = bề rộng vùng chữ của đoạn (trang hoặc ô) để dựng đường viền dưới."""
    pr = p.find(W + 'pPr')
    cs, sp, ind = [], (pr.find(W + 'spacing') if pr is not None else None), (pr.find(W + 'ind') if pr is not None else None)
    jc = _g(pr, 'jc', 'left')
    cs.append(f'text-align:{CAN.get(jc, "left")}')
    truoc = _tw(sp.get(W + 'before')) if sp is not None else 0
    sau = _tw(sp.get(W + 'after')) if sp is not None else 0
    cs.append(f'margin-top:{truoc * PX:g}px;margin-bottom:{sau * PX:g}px')
    dong = sp.get(W + 'line') if sp is not None else None
    if dong and sp.get(W + 'lineRule', 'auto') == 'auto':
        cs.append(f'line-height:{int(dong) * 100 // 240}%')
    trai = phai = 0.0
    if ind is not None:
        trai, phai = _tw(ind.get(W + 'left')), _tw(ind.get(W + 'right'))
        dau, treo = _tw(ind.get(W + 'firstLine')), _tw(ind.get(W + 'hanging'))
        if dau:
            cs.append(f'text-indent:{dau * PX:g}px')
        if treo:
            cs.append(f'text-indent:{-treo * PX:g}px')
    ben = pr.find(W + 'pBdr') if pr is not None else None
    chu = ''.join(_chay(r) for r in p.findall(W + 'r'))
    if not chu:
        co = 2
        rpr = pr.find(W + 'rPr') if pr is not None else None
        if rpr is not None and _g(rpr, 'sz'):
            co = int(_g(rpr, 'sz')) / 2
        chu = f'<span style="font-size:{co:g}pt">&nbsp;</span>'
    if ben is not None and ben.find(W + 'bottom') is not None:
        # Qt không vẽ viền khối của đoạn: đoạn có viền dưới = bảng một ô chỉ có cạnh dưới, bề rộng theo thụt hai bên
        khe = float(ben.find(W + 'bottom').get(W + 'space', '1')) * PX          # w:space của viền đoạn tính bằng pt
        rong = max(10.0, (rong_pt - trai - phai) * PX)
        cs2 = [c for c in cs if not c.startswith('text-indent')]
        return (f'<table cellspacing="0" cellpadding="0" width="{rong:g}" align="center" style="margin-left:{trai * PX:g}px"><tr>'
                f'<td style="border-bottom:1px solid #000;padding-bottom:{khe:g}px;{";".join(cs2)}">{chu}</td></tr></table>')
    if trai:
        cs.append(f'margin-left:{trai * PX:g}px')
    if phai:
        cs.append(f'margin-right:{phai * PX:g}px')
    return f'<p style="{";".join(cs)}">{chu}</p>'


def _bang(t, rong_pt: float) -> str:
    luoi = [_tw(c.get(W + 'w')) for c in t.find(W + 'tblGrid')]
    tbpr = t.find(W + 'tblPr')
    vien_bang = tbpr.find(W + 'tblBorders') if tbpr is not None else None
    co_vien = vien_bang is not None and _g(vien_bang, 'insideH', 'nil') == 'single' or \
        (vien_bang is not None and _g(vien_bang, 'top', 'nil') == 'single')
    hang = t.findall(W + 'tr')
    # vị trí cột lưới của từng ô, rồi gộp dọc: rowspan = số hàng liên tiếp có vMerge ở cùng cột bắt đầu
    ma_tran, goc = [], {}
    for i, tr in enumerate(hang):
        c0, dong = 0, []
        for tc in tr.findall(W + 'tc'):
            tpr = tc.find(W + 'tcPr')
            nhap = int(_g(tpr, 'gridSpan', '1'))
            vm = tpr.find(W + 'vMerge') if tpr is not None else None
            if vm is not None and vm.get(W + 'val') != 'restart':
                goc[c0] = goc.get(c0, (i, None))
                a = goc[c0][0]
                ma_tran[a][1][c0] += 1                           # tăng rowspan của ô gốc
                dong.append((tc, c0, nhap, True))
            else:
                if vm is not None:
                    goc[c0] = (i, None)
                dong.append((tc, c0, nhap, False))
            c0 += nhap
        ma_tran.append((dong, {x[1]: 1 for x in dong if not x[3]}))
    ra = [f'<table cellspacing="0" cellpadding="2" width="{sum(luoi) * PX:g}" align="center">']
    for i, (dong, rs) in enumerate(ma_tran):
        ra.append('<tr>')
        for tc, c0, nhap, tiep in dong:
            if tiep:
                continue
            tpr = tc.find(W + 'tcPr')
            rong = sum(luoi[c0:c0 + nhap])
            cs = [f'vertical-align:{ {"center": "middle", "top": "top", "bottom": "bottom"}.get(_g(tpr, "vAlign", "center"), "middle") }']
            vien_o = tpr.find(W + 'tcBorders') if tpr is not None else None
            if co_vien:
                cs.append('border:1px solid #000')
            for ben, tenw in (('top', 'top'), ('left', 'left'), ('bottom', 'bottom'), ('right', 'right')):
                if vien_o is not None and _g(vien_o, tenw) == 'nil':
                    cs.append(f'border-{ben}:0px solid #fff')
            shd = tpr.find(W + 'shd') if tpr is not None else None
            if shd is not None and shd.get(W + 'fill', 'auto') not in ('auto', 'FFFFFF'):
                cs.append(f'background-color:#{shd.get(W + "fill")}')
            noi = ''.join(_doan(p, rong - 4) if p.tag == W + 'p' else _bang(p, rong - 4)
                          for p in tc if p.tag in (W + 'p', W + 'tbl'))
            ra.append(f'<td width="{rong * PX:g}" colspan="{nhap}" rowspan="{rs.get(c0, 1)}" style="{";".join(cs)}">{noi}</td>')
        ra.append('</tr>')
    ra.append('</table>')
    return ''.join(ra)


def html_tu_docx(docx) -> tuple:
    """(HTML, thông tin trang {'rong_mm', 'cao_mm', 'le': (trái, trên, phải, dưới) mm}) từ file .docx của phần mềm."""
    docx = Path(docx)
    an_toan.kiem_tra_zip(docx)
    with zipfile.ZipFile(docx) as z:
        du = z.read('word/document.xml')
    an_toan.kiem_tra_xml(du, 'word/document.xml')
    goc = ET.fromstring(du)
    than = goc.find(W + 'body')
    sp = than.find(W + 'sectPr')
    kho, le = sp.find(W + 'pgSz'), sp.find(W + 'pgMar')
    rong_tw, cao_tw = float(kho.get(W + 'w')), float(kho.get(W + 'h'))
    le_tw = [float(le.get(W + k, 0)) for k in ('left', 'top', 'right', 'bottom')]
    vung_pt = (rong_tw - le_tw[0] - le_tw[2]) / 20
    phan = []
    for e in than:
        if e.tag == W + 'p':
            phan.append(_doan(e, vung_pt))
        elif e.tag == W + 'tbl':
            phan.append(_bang(e, vung_pt))
    html = ('<html><head><style>body{font-family:"Times New Roman",serif;font-size:13pt} td{padding:0}</style></head><body>'
            + ''.join(phan) + '</body></html>')
    mm = 25.4 / 1440
    return html, {'rong_mm': rong_tw * mm, 'cao_mm': cao_tw * mm, 'le': tuple(x * mm for x in le_tw)}


def xuat_pdf_tu_docx(docx, pdf) -> Path:
    """Dựng PDF khổ A4 (khổ / lề theo sectPr của .docx) từ bản Word của phần mềm bằng Qt. Lỗi -> ném lại (nơi gọi báo)."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

    from .pdf_du_phong import _chuan_bang_qt
    html, trang = html_tu_docx(docx)
    pdf = Path(pdf)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    w = QPdfWriter(str(pdf))
    w.setResolution(300)
    w.setTitle(Path(docx).stem)
    w.setCreator('LARC')
    hl = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(*trang['le']),
                     QPageLayout.Unit.Millimeter)
    w.setPageLayout(hl)
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setHtml(html)
    _chuan_bang_qt(doc)
    vung = hl.paintRect(QPageLayout.Unit.Point)
    doc.setPageSize(QSizeF(vung.width() * PX, vung.height() * PX))
    doc.print_(w)
    del w
    return pdf
