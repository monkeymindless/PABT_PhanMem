"""PDF dựng TRỰC TIẾP từ bản Word của phần mềm (1.0.19; 1.1.03: bản xem ngay của khung xem trước): đọc file .docx do in_word tạo, dựng
PDF bằng Qt (QTextDocument + QPdfWriter) - không cần Microsoft Word, chừng 0,1 giây một hộ. Dùng (a) làm bản xem NGAY trong lúc Word
dựng bản chính xác, (b) khi máy không có Word hoặc Word lỗi. KHÔNG đọc Excel: chỉ hiểu phần OpenXML mà in_word / van_ban_trinh tự sinh
(đoạn, chạy chữ đậm / nghiêng / gạch chân / cỡ chữ, ngắt dòng, bảng có gộp ô, viền ô, viền dưới đoạn, đệm ô, chiều cao dòng tối thiểu
w:trHeight, dòng tiêu đề lặp đầu trang), nên GẦN đúng bản Word (chỗ ngắt dòng, ngắt trang có thể lệch) - không thay thế Word.

1.1.03: khổ giấy + hướng giấy đọc từ w:sectPr (trước ép A4 dọc); khối chữ ký ba cột nằm trong dòng cuối của bảng như bản Word (trước tách
thành bảng riêng sau bảng); cụm cuối bảng đi liền nhau (dòng thưởng, TỔNG CỘNG, mục IV, chữ ký - w:keepNext) không vừa phần còn lại
của trang thì sang trang mới cả cụm kèm dòng tiêu đề; đoạn rỗng cao theo cỡ chữ mặc định của tài liệu như Word.

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
CO_MAC_DINH = 13.0                             # cỡ chữ mặc định của tài liệu phần mềm tạo (van_ban_trinh._goi_docx): dấu đoạn của đoạn rỗng
LE_O_NGANG = 1.5                               # pt đệm trái / phải của ô (bản dựng trực tiếp giữ hẹp như trước 1.1.03: 2 px)
KHO_CHUAN = {'A4': (210.0, 297.0), 'A3': (297.0, 420.0)}


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
    quy_tac = sp.get(W + 'lineRule', 'auto') if sp is not None else 'auto'
    if dong and quy_tac == 'auto':
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
        # đoạn rỗng: Word cho cao bằng dấu đoạn - cỡ chữ ghi ở pPr/rPr, không ghi thì cỡ mặc định của tài liệu (dòng trống chỗ ký,
        # ô trống của bảng); đoạn giãn dòng "exact" (đường kẻ ngắn, đoạn 1 pt đóng ô) cao đúng chừng đó (trước 1.1.03 mọi đoạn rỗng 2 pt)
        rpr = pr.find(W + 'rPr') if pr is not None else None
        if dong and quy_tac == 'exact':
            co = max(1.0, min(CO_MAC_DINH, int(dong) / 20 / 1.15))
        elif rpr is not None and _g(rpr, 'sz'):
            co = int(_g(rpr, 'sz')) / 2
        else:
            co = CO_MAC_DINH
        chu = f'<span style="font-size:{co:g}pt">&nbsp;</span>'
    if ben is not None and ben.find(W + 'bottom') is not None:
        # Qt không vẽ viền khối của đoạn: đoạn có viền dưới = bảng một ô chỉ có cạnh dưới, bề rộng theo thụt hai bên
        khe = float(ben.find(W + 'bottom').get(W + 'space', '1')) * PX          # w:space của viền đoạn tính bằng pt
        rong = max(10.0, (rong_pt - trai - phai) * PX)
        cs2 = [c for c in cs if not c.startswith('text-indent')]
        can_bang = abs(trai - phai) < 1
        kieu_bang = '' if can_bang else f' style="margin-left:{trai * PX:g}px"'
        return (f'<table cellspacing="0" cellpadding="0" width="{rong:g}" align="{"center" if can_bang else "left"}"{kieu_bang}><tr>'
                f'<td style="border-bottom:1px solid #000;padding-bottom:{khe:g}px;{";".join(cs2)}">{chu}</td></tr></table>')
    if trai:
        cs.append(f'margin-left:{trai * PX:g}px')
    if phai:
        cs.append(f'margin-right:{phai * PX:g}px')
    return f'<p style="{";".join(cs)}">{chu}</p>'


def _giu_sau(tr) -> bool:
    """Dòng bảng đi liền dòng sau: đoạn đầu của ô đầu có w:keepNext (cách in_word đánh dấu cụm cuối bảng)."""
    tc = tr.find(W + 'tc')
    p = tc.find(W + 'p') if tc is not None else None
    pr = p.find(W + 'pPr') if p is not None else None
    return pr is not None and pr.find(W + 'keepNext') is not None


def _moi_ngu_canh() -> dict:
    """Ngữ cảnh một lượt dựng HTML: bang = số QTextTable đã phát (theo thứ tự tài liệu, kể cả bảng viền đoạn và bảng lồng); cao =
    {(thứ tự bảng, dòng): chiều cao phần chữ tối thiểu pt} từ w:trHeight; cum = (thứ tự bảng, dòng đầu cụm cuối, số dòng tiêu đề) của
    bảng chính (bảng có dòng tiêu đề lặp) + thứ tự bảng chữ ký dựng sau nó (đáy của cụm); cat = True: phát cụm cuối thành bảng riêng
    bắt đầu trang mới."""
    return {'bang': 0, 'cao': {}, 'cum': None, 'cat': False}


def _dem_bang_vien(html: str) -> int:
    return html.count('<table')


def _bang(t, rong_pt: float, nc: dict | None = None) -> str:
    nc = _moi_ngu_canh() if nc is None else nc
    luoi = [_tw(c.get(W + 'w')) for c in t.find(W + 'tblGrid')]
    tbpr = t.find(W + 'tblPr')
    vien_bang = tbpr.find(W + 'tblBorders') if tbpr is not None else None
    co_vien = vien_bang is not None and _g(vien_bang, 'insideH', 'nil') == 'single' or \
        (vien_bang is not None and _g(vien_bang, 'top', 'nil') == 'single')
    le = tbpr.find(W + 'tblCellMar') if tbpr is not None else None
    dem_tren = _tw(le.find(W + 'top').get(W + 'w')) if le is not None and le.find(W + 'top') is not None else 0.0
    dem_duoi = _tw(le.find(W + 'bottom').get(W + 'w')) if le is not None and le.find(W + 'bottom') is not None else 0.0
    hang = t.findall(W + 'tr')
    # dòng chỉ có MỘT ô chứa bảng lồng (khối chữ ký ba cột đều nhau): Qt nới đều mọi cột của bảng ngoài khi gặp bảng lồng cỡ cả bề rộng
    # (thử lại 1.1.03: cột Ghi chú bị đẩy khỏi trang) -> dựng bảng lồng thành bảng ngay SAU bảng ngoài, sát đáy bảng như bản Word; khối
    # này vẫn thuộc cụm cuối: cụm sang trang mới thì nó đi cùng (xem _cum_vat_trang)
    long_sau, giu = [], []
    for tr in hang:
        o_ = tr.findall(W + 'tc')
        if len(o_) == 1 and o_[0].find(W + 'tbl') is not None:
            long_sau += o_[0].findall(W + 'tbl')
        else:
            giu.append(tr)
    hang = giu
    so_tieu_de = 0
    for tr in hang:
        trpr = tr.find(W + 'trPr')
        if trpr is None or trpr.find(W + 'tblHeader') is None:
            break
        so_tieu_de += 1
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
    he_so = min(1.0, max(10.0, rong_pt - 8) / (sum(luoi) or 1))                  # vừa vùng chứa, chừa lề ô
    luoi = [x * he_so for x in luoi]
    # cụm cuối đi liền nhau của bảng chính (bảng có dòng tiêu đề lặp): các dòng cuối nối nhau bằng keepNext
    dau_cum = len(hang)
    if so_tieu_de and len(hang) > so_tieu_de:
        dau_cum = len(hang) - 1
        while dau_cum > so_tieu_de and _giu_sau(hang[dau_cum - 1]):
            dau_cum -= 1
        if dau_cum == len(hang) - 1 and not long_sau and not _giu_sau(hang[-1]):
            dau_cum = len(hang)                          # dòng cuối không nối với gì: không có cụm
    cat_tai = dau_cum if (so_tieu_de and nc['cat'] and so_tieu_de < dau_cum < len(hang)) else None
    mo_bang = f'<table cellspacing="0" cellpadding="0" width="{sum(luoi) * PX:g}" align="center"'

    def phat_hang(i: int) -> str:
        dong, rs = ma_tran[i]
        ra = ['<tr>']
        for tc, c0, nhap, tiep in dong:
            if tiep:
                continue
            tpr = tc.find(W + 'tcPr')
            rong = sum(luoi[c0:c0 + nhap])
            cs = [f'vertical-align:{ {"center": "middle", "top": "top", "bottom": "bottom"}.get(_g(tpr, "vAlign", "center"), "middle") }',
                  f'padding:{dem_tren * PX:g}px {LE_O_NGANG * PX:g}px {dem_duoi * PX:g}px {LE_O_NGANG * PX:g}px']
            vien_o = tpr.find(W + 'tcBorders') if tpr is not None else None
            if co_vien:
                cs.append('border:1px solid #000')
            for ben, tenw in (('top', 'top'), ('left', 'left'), ('bottom', 'bottom'), ('right', 'right')):
                if vien_o is not None and _g(vien_o, tenw) == 'nil':
                    cs.append(f'border-{ben}:0px solid #fff')
            shd = tpr.find(W + 'shd') if tpr is not None else None
            if shd is not None and shd.get(W + 'fill', 'auto') not in ('auto', 'FFFFFF'):
                cs.append(f'background-color:#{shd.get(W + "fill")}')
            noi = []
            for p in tc:
                if p.tag == W + 'p':
                    x = _doan(p, rong - 4)
                    nc['bang'] += _dem_bang_vien(x)
                    noi.append(x)
                elif p.tag == W + 'tbl':
                    noi.append(_bang(p, rong - 20, nc))          # bảng lồng: chừa lề ô + viền (Qt nới cột đều nếu vượt)
            ra.append(f'<td width="{rong * PX:g}" colspan="{nhap}" rowspan="{rs.get(c0, 1)}" style="{";".join(cs)}">{"".join(noi)}</td>')
        ra.append('</tr>')
        return ''.join(ra)

    def ghi_cao(thu_tu: int, i: int, vi_tri: int) -> None:
        trpr = hang[i].find(W + 'trPr')
        h = trpr.find(W + 'trHeight') if trpr is not None else None
        if h is not None and h.get(W + 'hRule', 'atLeast') != 'auto':
            nc['cao'][(thu_tu, vi_tri)] = _tw(h.get(W + 'val'))

    def phat_phan(tu: int, den: int, ngat_truoc: bool) -> str:
        thu_tu = nc['bang']
        nc['bang'] += 1
        ra = [mo_bang + (' style="page-break-before:always"' if ngat_truoc else '') + '>']
        vi_tri = 0
        # dòng tiêu đề: dòng thường ở đầu từng phần (KHÔNG dùng <thead> lặp đầu trang của Qt: dòng bị Qt cắt đôi qua trang thì chữ dòng
        # đó in đè lên dòng tiêu đề lặp - đã thử 1.1.03). Trang ngắt tự nhiên giữa bảng vì vậy không có dòng tiêu đề (bản Word thì có)
        for i in list(range(so_tieu_de)) + list(range(max(tu, so_tieu_de), den)):
            ghi_cao(thu_tu, i, vi_tri)
            ra.append(phat_hang(i))
            vi_tri += 1
        ra.append('</table>')
        if so_tieu_de and not ngat_truoc and nc['cum'] is None and so_tieu_de < dau_cum < len(hang):
            nc['cum'] = [thu_tu, dau_cum, so_tieu_de, None]
        return ''.join(ra)

    if cat_tai is None:
        than_bang = phat_phan(0, len(hang), False)
    else:
        than_bang = phat_phan(0, cat_tai, False) + phat_phan(cat_tai, len(hang), True)
    sau = ''.join(_bang(x, rong_pt, nc) for x in long_sau)
    if long_sau and so_tieu_de:
        if nc['cum'] is None and not nc['cat']:          # cụm chỉ gồm khối chữ ký: tính từ dòng cuối của bảng
            nc['cum'] = [nc['bang'] - len(long_sau) - 1, max(so_tieu_de, len(hang) - 1), so_tieu_de, None]
        if nc['cum'] is not None:
            nc['cum'][3] = nc['bang'] - 1                # bảng cuối cùng vừa phát = đáy của cụm
    return than_bang + sau


def _than_html(than, vung_pt: float, nc: dict) -> str:
    phan = []
    for e in than:
        if e.tag == W + 'p':
            x = _doan(e, vung_pt)
            nc['bang'] += _dem_bang_vien(x)
            phan.append(x)
        elif e.tag == W + 'tbl':
            phan.append(_bang(e, vung_pt, nc))
    return ('<html><head><style>body{font-family:"Times New Roman",serif;font-size:13pt}</style></head><body>'
            + ''.join(phan) + '</body></html>')


def _doc_docx(docx):
    docx = Path(docx)
    an_toan.kiem_tra_zip(docx)
    with zipfile.ZipFile(docx) as z:
        du = z.read('word/document.xml')
    an_toan.kiem_tra_xml(du, 'word/document.xml')
    than = ET.fromstring(du).find(W + 'body')
    sp = than.find(W + 'sectPr')
    kho, le = sp.find(W + 'pgSz'), sp.find(W + 'pgMar')
    rong_tw, cao_tw = float(kho.get(W + 'w')), float(kho.get(W + 'h'))
    le_tw = [float(le.get(W + k, 0)) for k in ('left', 'top', 'right', 'bottom')]
    mm = 25.4 / 1440
    trang = {'rong_mm': rong_tw * mm, 'cao_mm': cao_tw * mm, 'le': tuple(x * mm for x in le_tw)}
    trang['ngang'] = trang['rong_mm'] > trang['cao_mm']
    trang['kho'] = ten_kho_giay(trang['rong_mm'], trang['cao_mm'])
    return than, (rong_tw - le_tw[0] - le_tw[2]) / 20, trang


def ten_kho_giay(rong_mm: float, cao_mm: float) -> str:
    """'A4' / 'A3' khi kích thước (không kể hướng) khớp khổ chuẩn trong 2 mm; khổ khác: ''."""
    ngan, dai = sorted((float(rong_mm), float(cao_mm)))
    for ten, (a, b) in KHO_CHUAN.items():
        if abs(ngan - a) <= 2 and abs(dai - b) <= 2:
            return ten
    return ''


def html_tu_docx(docx, cat_cum_cuoi: bool = False) -> tuple:
    """(HTML, thông tin trang {'rong_mm', 'cao_mm', 'le': (trái, trên, phải, dưới) mm, 'ngang', 'kho'}) từ file .docx của phần mềm.
    cat_cum_cuoi: phát cụm cuối bảng chính thành bảng riêng bắt đầu trang mới (xuat_pdf_tu_docx dùng khi cụm vắt qua hai trang)."""
    than, vung_pt, trang = _doc_docx(docx)
    nc = _moi_ngu_canh()
    nc['cat'] = bool(cat_cum_cuoi)
    html = _than_html(than, vung_pt, nc)
    trang['_ngu_canh'] = nc
    return html, trang


def bo_cuc_trang(trang: dict):
    """QPageLayout theo khổ + hướng giấy + lề đọc từ w:sectPr (A4 / A3 chuẩn, khổ khác theo đúng mm)."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize
    ngang = bool(trang.get('ngang'))
    kho = trang.get('kho') or ten_kho_giay(trang['rong_mm'], trang['cao_mm'])
    if kho == 'A3':
        co = QPageSize(QPageSize.PageSizeId.A3)
    elif kho == 'A4':
        co = QPageSize(QPageSize.PageSizeId.A4)
    else:
        ngan, dai = sorted((trang['rong_mm'], trang['cao_mm']))
        co = QPageSize(QSizeF(ngan, dai), QPageSize.Unit.Millimeter)
    return QPageLayout(co, QPageLayout.Orientation.Landscape if ngang else QPageLayout.Orientation.Portrait,
                       QMarginsF(*trang['le']), QPageLayout.Unit.Millimeter)


def _cac_bang(doc) -> list:
    """Mọi QTextTable của tài liệu theo thứ tự xuất hiện (bảng lồng đứng sau bảng chứa nó)."""
    from PySide6.QtGui import QTextTable
    ra = []

    def di(khung):
        for f in khung.childFrames():
            if isinstance(f, QTextTable):
                ra.append(f)
            di(f)
    di(doc.rootFrame())
    return ra


def _vung_o(doc, o) -> tuple:
    """(đỉnh, đáy) px của phần chữ một ô theo bố cục hiện tại."""
    lo = doc.documentLayout()
    a = lo.blockBoundingRect(o.firstCursorPosition().block())
    b = lo.blockBoundingRect(o.lastCursorPosition().block())
    return a.top(), b.bottom()


def _ap_cao_hang(doc, bang: list, cao: dict) -> int:
    """w:trHeight (chiều cao phần chữ tối thiểu, pt): dòng thấp hơn thì chia phần thiếu vào đệm trên / dưới của mọi ô trong dòng
    (HTML của Qt không có chiều cao dòng). Trả số dòng đã nới."""
    from PySide6.QtGui import QTextCursor
    viec = []                                           # ĐO hết rồi mới sửa: mỗi lần đổi định dạng ô Qt bố cục lại cả tài liệu
    for (thu_tu, hang), toi_thieu in sorted(cao.items()):
        if thu_tu >= len(bang) or toi_thieu <= 0:
            continue
        t = bang[thu_tu]
        if hang >= t.rows():
            continue
        cao_hien, o_cua_hang = 0.0, []
        c = 0
        while c < t.columns():
            o = t.cellAt(hang, c)
            buoc = max(1, o.columnSpan())
            if o.row() == hang and o.column() == c:
                o_cua_hang.append(o)
                if o.rowSpan() == 1:
                    tren, duoi = _vung_o(doc, o)
                    cao_hien = max(cao_hien, duoi - tren)
            c += buoc
        thieu = toi_thieu * PX - cao_hien
        if thieu > 0.5 and o_cua_hang:
            viec.append((o_cua_hang, thieu))
    if not viec:
        return 0
    con_tro = QTextCursor(doc)
    con_tro.beginEditBlock()                            # gom mọi thay đổi: bố cục lại MỘT lần khi kết thúc
    try:
        for o_cua_hang, thieu in viec:
            for o in o_cua_hang:
                f = o.format().toTableCellFormat()
                f.setTopPadding(f.topPadding() + thieu / 2)
                f.setBottomPadding(f.bottomPadding() + thieu / 2)
                o.setFormat(f)
    finally:
        con_tro.endEditBlock()
    return len(viec)


def _cum_vat_trang(doc, bang: list, cum, cao_trang: float) -> bool:
    """Cụm cuối bảng chính (từ dòng `cum[1]` tới hết) có vắt qua hai trang không - và có vừa một trang không (không vừa thì để Qt tự ngắt)."""
    if not cum or cum[0] >= len(bang) or cao_trang <= 0:
        return False
    t = bang[cum[0]]
    if cum[1] >= t.rows():
        return False
    dinh = min(_vung_o(doc, t.cellAt(cum[1], c))[0] for c in range(t.columns()))
    cuoi = bang[cum[3]] if len(cum) > 3 and cum[3] is not None and cum[3] < len(bang) else t
    day = max(_vung_o(doc, cuoi.cellAt(cuoi.rows() - 1, c))[1] for c in range(cuoi.columns()))
    return int(dinh // cao_trang) != int(day // cao_trang) and (day - dinh) < cao_trang * 0.9


def tai_lieu_tu_docx(docx, bo_cuc=None):
    """(QTextDocument đã bố cục theo trang, QPageLayout, thông tin trang) của file .docx - dùng chung cho xuất PDF và in thẳng."""
    from PySide6.QtCore import QSizeF
    from PySide6.QtGui import QPageLayout, QTextDocument

    from .pdf_du_phong import _chuan_bang_qt
    than, vung_pt, trang = _doc_docx(docx)
    hl = bo_cuc or bo_cuc_trang(trang)
    vung = hl.paintRect(QPageLayout.Unit.Point)
    co = QSizeF(vung.width() * PX, vung.height() * PX)
    doc = None
    for cat in (False, True):
        nc = _moi_ngu_canh()
        nc['cat'] = cat
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setHtml(_than_html(than, vung_pt, nc))
        _chuan_bang_qt(doc)
        doc.setPageSize(co)
        bang = _cac_bang(doc)
        if nc['cao']:
            doc.documentLayout().documentSize()         # buộc bố cục xong rồi mới đo chiều cao dòng
            _ap_cao_hang(doc, bang, nc['cao'])
        if cat:
            break
        doc.documentLayout().documentSize()
        if not _cum_vat_trang(doc, bang, nc['cum'], co.height()):
            break
    return doc, hl, trang


def xuat_pdf_tu_docx(docx, pdf) -> Path:
    """Dựng PDF (khổ, hướng giấy, lề theo w:sectPr của .docx) từ bản Word của phần mềm bằng Qt. Lỗi -> ném lại (nơi gọi báo)."""
    from PySide6.QtGui import QPdfWriter
    doc, hl, _trang = tai_lieu_tu_docx(docx)
    pdf = Path(pdf)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    w = QPdfWriter(str(pdf))
    w.setResolution(300)
    w.setTitle(Path(docx).stem)
    w.setCreator('LARC')
    w.setPageLayout(hl)
    doc.print_(w)
    del w
    return pdf
