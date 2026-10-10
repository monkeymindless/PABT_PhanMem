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
import subprocess
import sys
import tempfile
import threading
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
from .tien import D, KHONG

TEN_CT, TEN_BTH = 'IN_CHITIET', 'IN_BANGTONGHOP'
COT_KIND = 30          # cột AD (ngoài vùng in): loại dòng H / I / R / T cho định dạng có điều kiện của mẫu
DONG_DAU_CT = 18       # IN_CHITIET: dòng đầu bảng (dưới hàng tiêu đề STT)
DONG_DAU_BTH = 13      # IN_BANGTONGHOP: dòng dữ liệu đầu
TEN_CAO = 'PABT_TU_GIAN_DONG'   # tên vùng các dòng cần Excel tự giãn chiều cao khi xuất PDF


class LoiIn(RuntimeError):
    pass


# ---------------------------------------------------------------- thư mục mẫu in
def thu_muc_mau() -> Path:
    """mau_in cạnh PABT.exe (người dùng sửa được) > mau_in đóng gói kèm > mau_in của mã nguồn."""
    ung_vien = []
    if getattr(sys, 'frozen', False):
        ung_vien.append(thu_muc_mau_ghi())
        ung_vien.append(Path(sys.executable).parent / 'mau_in')
        ung_vien.append(Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / 'mau_in')
    ung_vien.append(Path(__file__).resolve().parents[1] / 'mau_in')
    for p in ung_vien:
        if (p / f'{TEN_CT}.xlsx').exists():
            return p
    raise LoiIn('Không tìm thấy thư mục mẫu in (mau_in\\IN_CHITIET.xlsx). Dùng lệnh "Mẫu in" (nhóm In, báo cáo).')


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


def luu_duong_ke(file_excel, thu_muc) -> list:
    """Lưu đường kẻ của 2 sheet mẫu in thành mau_in/<mẫu>.duong_ke.xml."""
    tao = []
    for ten in (TEN_CT, TEN_BTH):
        x = doc_duong_ke(file_excel, ten)
        p = Path(thu_muc) / f'{ten}.duong_ke.xml'
        if x:
            p.write_text(x, encoding='utf-8')
            tao.append(p)
        elif p.exists():
            p.unlink()
    return tao


def chen_duong_ke(file_xlsx, file_duong_ke) -> bool:
    """Chèn các đường kẻ (XML) vào sheet đầu của file .xlsx do openpyxl lưu. Trả True nếu đã chèn."""
    import zipfile
    p, dk = Path(file_xlsx), Path(file_duong_ke)
    if not dk.exists() or not dk.read_text(encoding='utf-8').strip():
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
                                          f'xmlns:a="{_DS_A}">' + dk.read_text(encoding='utf-8') + '</xdr:wsDr>').encode('utf-8')
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


def file_mau(mau, ten: str) -> Path:
    """mau: thư mục mẫu (None = thu_muc_mau()) hoặc chính file mẫu .xlsx (mẫu riêng chọn khi In / Xuất)."""
    if mau is not None and str(mau).lower().endswith('.xlsx'):
        return Path(mau)
    return Path(mau or thu_muc_mau()) / f'{ten}.xlsx'


def ds_mau(ten: str) -> list:
    """[(tên hiển thị, file)] các mẫu của loại ten: mẫu chính trước, rồi các mẫu riêng (thư mục mẫu đang dùng + thư mục ghi)."""
    try:
        chinh = thu_muc_mau() / f'{ten}.xlsx'
    except LoiIn:
        return []
    kq, da = [('Mẫu chính', chinh)], set()
    for d in dict.fromkeys([chinh.parent, thu_muc_mau_ghi()]):
        for f in sorted(Path(d).glob(f'{ten}{TACH_MAU}*.xlsx')):
            t = f.stem[len(ten) + len(TACH_MAU):]
            if t and t.lower() not in da and not f.name.startswith('~$'):
                da.add(t.lower())
                kq.append((t, f))
    return kq


def mau_de_sua(ten: str = TEN_CT) -> Path:
    """File mẫu in để mở bằng Excel sửa trực tiếp (chữ, phông, lề, độ rộng cột, đường kẻ...). Bản cài: chép mẫu đang dùng
    sang %APPDATA%\\PABT\\mau_in (thư mục cài không ghi được) - từ đó phần mềm in theo mẫu đã sửa."""
    import shutil
    goc, ghi = thu_muc_mau(), thu_muc_mau_ghi()
    if goc.resolve() != ghi.resolve():
        ghi.mkdir(parents=True, exist_ok=True)
        for f in (f'{TEN_CT}.xlsx', f'{TEN_BTH}.xlsx', f'{TEN_CT}.duong_ke.xml', f'{TEN_BTH}.duong_ke.xml'):
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


def xem_truoc(con, ma_ho: int, thu_muc=None, mau=None) -> Path:
    """Bản in thử phương án chi tiết của một hộ (PDF nếu máy có Excel, không thì .xlsx) trong thư mục tạm. Trả file.
    mau: file mẫu riêng (None = mẫu chính)."""
    if thu_muc is None:
        _don_xem_truoc_cu()
    td = Path(thu_muc or tempfile.mkdtemp(prefix='PABT_xem_truoc_'))
    f = lap_chi_tiet(con, ma_ho, td / f'{ten_file_ho(con, ma_ho)}.xlsx', mau)
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
            vung.append(cr.coord)
        for rule in cf.rules:
            cf_moi.add(' '.join(vung), rule)
    ws.conditional_formatting = cf_moi


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
    for row in ws.iter_rows(max_row=den_dong):
        for o in row:
            v = o.value
            if not isinstance(v, str):
                continue
            s = v
            if so:
                s = re_so.sub(lambda m: f'{nhan_so} {so}/', s)
            if m_ngay:
                s = re_ngay.sub(f'ngày {int(m_ngay.group(1)):02d} tháng {int(m_ngay.group(2)):02d} năm {m_ngay.group(3)}', s)
            if s != v:
                o.value = s
                n += 1
    return n


def _thay_cho_trong(ws, gia_tri: dict):
    """Thay {ten} trong mọi ô chữ của sheet."""
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and '{' in c.value:
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


def _rong_vung(ws, c1: int, c2: int) -> float:
    """Bề rộng (pt) chỗ viết chữ trong vùng cột c1..c2 (trừ lề trong ô)."""
    from openpyxl.utils import get_column_letter
    mdw = _mdw(ws.parent)
    px = sum(int((ws.column_dimensions[get_column_letter(c)].width or 8.43) * mdw + 0.5) for c in range(c1, c2 + 1))
    return px * 0.75 - 6


def _ngat(chu: str, rong: float, ten: str, co: float, dam: bool, do=None) -> list:
    """Ngắt chữ thành các dòng như Excel (theo từ; '\\n' là xuống đoạn). Trả [(dòng, là đầu đoạn)]."""
    do = do or _ham_do_chu()
    if do is None:                               # ước: bề rộng trung bình một ký tự Times New Roman ~ 0,47 cỡ chữ (đậm 0,52)
        tb = co * (0.52 if dam else 0.47)
        do = lambda s, *_: len(s) * tb          # noqa: E731
    rong = rong * 0.97                          # chừa 3%: phông máy in / PDF có thể rộng hơn chút
    kq = []
    for doan in str(chu or '').split('\n'):
        dau = True
        dong = ''
        for tu in doan.split():
            thu = f'{dong} {tu}' if dong else tu
            if do(thu, ten, co, dam) <= rong or not dong:
                dong = thu
                while do(dong, ten, co, dam) > rong and len(dong) > 1:    # một từ dài hơn cả dòng: cắt ngang
                    n = len(dong)
                    while n > 1 and do(dong[:n], ten, co, dam) > rong:
                        n -= 1
                    kq.append((dong[:n], dau))
                    dau = False
                    dong = dong[n:]
            else:
                kq.append((dong, dau))
                dau = False
                dong = tu
        kq.append((dong, dau))
    return kq


def ngat_dong(chu: str, rong: float, ten: str = 'Times New Roman', co: float = 14, dam: bool = False, do=None) -> list:
    """Các dòng chữ sau khi ngắt theo bề rộng rong (pt)."""
    return [x for x, _ in _ngat(chu, rong, ten, co, dam, do)]


def cao_dong_chu(so_dong: int, co: float) -> float:
    """Chiều cao (pt) của so_dong dòng chữ cỡ co: Times New Roman giãn dòng ~1,15 cỡ chữ; lấy 1,2 cho dư một chút
    (Excel làm tròn chiều cao theo điểm ảnh màn hình)."""
    return so_dong * co * 1.2


def _vung_tron(ws, r: int, c: int):
    for m in ws.merged_cells.ranges:
        if m.min_row <= r <= m.max_row and m.min_col <= c <= m.max_col:
            return m
    return None


def vi_tri_cho(ws, cho: str, den_dong: int = 80):
    """(dòng, cột đầu, cột cuối, dòng cuối) của ô có chỗ trống cho (tính cả vùng gộp), hoặc None."""
    for row in ws.iter_rows(min_row=1, max_row=min(den_dong, ws.max_row)):
        for o in row:
            if isinstance(o.value, str) and cho in o.value:
                m = _vung_tron(ws, o.row, o.column)
                return (o.row, m.min_col, m.max_col, m.max_row) if m else (o.row, o.column, o.column, o.row)
    return None


def _phong(o) -> tuple:
    f = o.font
    return (f.name if f is not None and f.name else 'Times New Roman'), float(f.sz if f is not None and f.sz else 14), \
        bool(f is not None and f.b)


def dat_doan_van(ws, cho: str, chu: str, do=None) -> int:
    """Ô có chỗ trống cho (vd '{nguon_goc}', gộp ngang hết bảng, có thể gộp vài dòng): điền chữ, chiều cao vừa đủ số dòng
    chữ. Chữ dài quá một dòng Excel (409 pt) thì chia sang các dòng kế tiếp (thiếu thì chèn thêm); dòng thừa của vùng
    gộp cũ thu nhỏ thành khoảng cách. Trả số dòng đã chèn thêm."""
    vt = vi_tri_cho(ws, cho)
    if vt is None:
        return 0
    r, c1, c2, r2 = vt
    o = ws.cell(r, c1)
    chu = o.value.replace(cho, str(chu or ''))
    ten, co, dam = _phong(o)
    dong = _ngat(chu, _rong_vung(ws, c1, c2), ten, co, dam, do)
    toi_da = max(1, int((CAO_TOI_DA - 8) // (co * 1.2)))
    khoi = [dong[i:i + toi_da] for i in range(0, len(dong), toi_da)] or [[('', True)]]
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
            ws.row_dimensions[rr].height = 4         # dòng thừa của vùng gộp cũ: chỉ còn là khoảng cách nhỏ
            continue
        oo = ws.cell(rr, c1)
        oo._style = copy(kieu)
        # nối lại các dòng đã ngắt (Excel ngắt lại đúng chỗ cũ vì cùng bề rộng): đầu đoạn thì xuống dòng
        oo.value = ''.join(('\n' if dau and j else ' ' if j else '') + x for j, (x, dau) in enumerate(khoi[i])) or None
        al = copy(oo.alignment)
        al.wrap_text = True
        al.vertical = 'top' if len(khoi) > 1 else (al.vertical or 'center')
        oo.alignment = al
        if c2 > c1:
            _gop_o(ws, rr, c1, rr, c2)
        ws.row_dimensions[rr].height = max(20, cao_dong_chu(len(khoi[i]), co) + 5)
    return chen


def vua_chu(ws, vt, do=None, them: float = 3) -> None:
    """Dòng vt (từ vi_tri_cho) cao vừa đủ các dòng chữ (sau khi đã điền), chữ canh trên: sát dòng phía trên. Dùng cho
    'Dự án: …' (tên ngắn 1 dòng, dài tự xuống dòng); đường kẻ dưới tên dự án neo ở dòng kế tiếp nên kéo sát lên theo."""
    if not vt:
        return
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
                raise LoiChuaRoMau('Không nhận ra file này là mẫu phương án chi tiết hay bảng tổng hợp (không có sheet '
                                   f'{TEN_CT} / {TEN_BTH}, không có chỗ trống {{ho_ten}}… hay chữ "BẢNG TỔNG HỢP").')
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


def _xml_attr(s: str) -> str:
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def _lam_mau_ct(ws):
    dau = next((r for r in range(1, 300) if str(ws.cell(r, 1).value or '').strip().upper() == 'STT'), 17) + 1
    iv = next((r for r in range(dau, dau + 5000) if str(ws.cell(r, 1).value or '').strip() == 'IV'), None)
    if iv is None:
        raise LoiIn('Mẫu IN_CHITIET: không tìm thấy dòng "IV" (phương án tái định cư) ở cột A.')
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
        for rule in cf.rules:
            vung = []
            for cr in cf.sqref.ranges:
                cr = CellRange(cr.coord)
                if cr.min_row >= dau - 1 and cr.min_row <= dau + 200:
                    cr = CellRange(min_col=cr.min_col, max_col=cr.max_col, min_row=dau, max_row=cuoi)
                vung.append(cr.coord)
            cf_moi.add(' '.join(vung), rule)
    ws.conditional_formatting = cf_moi


def _lam_mau_bth(ws):
    tong = next((r for r in range(DONG_DAU_BTH, DONG_DAU_BTH + 3000) if str(ws.cell(r, 1).value or '').strip() == 'TỔNG CỘNG'), None)
    if tong is None:
        raise LoiIn('Mẫu IN_BANGTONGHOP: không tìm thấy dòng TỔNG CỘNG ở cột A.')
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


def dong_chi_tiet(con, ma_ho: int, bc: BoiCanh | None = None) -> tuple:
    """Các dòng bảng in của một hộ: (danh sách (loại, [A..H]), KetQuaHo). Loại: H mục, I dòng, R thưởng, T tổng."""
    bc = bc or BoiCanh.tu(con)
    pa = doc_phuong_an(con, ma_ho)
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
    # 2, 3
    for muc in (2, 3):
        dong.append(['H', [str(muc), nghiep_vu.TEN_MUC[muc], None, None, None, None, kq.muc[muc], None]])
        for d in (x for x in kq.dong if x.muc == muc):
            dong.append(['I', [d.stt, d.ten, d.dvt, d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, d.ma, d.ghi_chu)]])
    # 4: dòng có cách tính in gộp ô ĐVT..tỷ lệ; hỗ trợ đào tạo nhập theo từng thửa có dòng tên chính sách đứng đầu nhóm
    from .chinh_sach import ten_ngan
    dong.append(['H', ['4', nghiep_vu.TEN_MUC[4], None, None, None, None, kq.muc[4], None]])
    ds4 = [x for x in kq.dong if x.muc == 4]
    k = i = 0
    while i < len(ds4):
        d = ds4[i]
        k += 1
        if d.ma in ('HT09', 'HT10') and d.ten.startswith('Thửa đất'):
            j = i
            while j < len(ds4) and ds4[j].ma == d.ma and ds4[j].ten.startswith('Thửa đất'):
                j += 1
            nhom = ds4[i:j]
            ten = ten_ngan((bc.hotro.get(d.ma) or {}).get('ten', ''), d.ma) or 'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm'
            dt = sum((x.so_luong for x in nhom), KHONG)
            dong.append(['I', [f'4.{k}', ten, 'm²', dt, None, None, sum((x.thanh_tien for x in nhom), KHONG),
                               ghi_chu_in(con, d.ma, d.ghi_chu)]])
            for x in nhom:
                dong.append(['I', ['-', x.ten, x.dvt, x.so_luong, x.don_gia, x.ty_le, x.thanh_tien, None]])
            i = j
            continue
        gt = [f'4.{k}', d.ten, d.dvt, d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, d.ma, d.ghi_chu)]
        dong.append(['I', gt, d.cach_tinh] if d.cach_tinh else ['I', gt])
        i += 1
    # 5. thưởng (chỉ khi có bồi thường về đất), tổng
    co = kq.muc[1] > 0
    dong.append(['R', ['5', nghiep_vu.TEN_MUC[5], 'Hộ', D(1) if co else KHONG, kq.muc[5], D(1), kq.muc[5], None]])
    dong.append(['T', [None, 'TỔNG CỘNG', None, None, None, None, kq.tong, None]])
    return dong, kq


def _thong_tin_ho(con, ma_ho: int, da: dict) -> dict:
    h = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    ten = ' '.join(str(h['ho_ten'] or '').split())
    if ' là ' in ten:
        ten = ten.split(' là ')[0].strip()
    cccd = (h['so_cccd'] or '').strip()
    if (h['ngay_cap'] or '').strip() and h['ngay_cap'] != '0':
        cccd += f' - Ngày cấp: {h["ngay_cap"].strip()}'
    if (h['noi_cap'] or '').strip():
        cccd += f' - Nơi cấp: {h["noi_cap"].strip()}'
    ng = []                                     # nguồn gốc các thửa (bỏ trùng, giữ thứ tự): mỗi nội dung một đoạn
    for r in con.execute("SELECT nguon_goc FROM thua WHERE ma_ho = ? AND TRIM(nguon_goc) <> '' ORDER BY thu_tu, ma_thua",
                         (ma_ho,)):
        if r['nguon_goc'].strip() not in ng:
            ng.append(r['nguon_goc'].strip())
    from .lap_pa import cau_tai_dinh_cu
    tdc = cau_tai_dinh_cu(h['tai_dinh_cu']) or \
        f'Sau khi UBND {da["cap_dia_ban_thuong"] or "xã, phường"} xác nhận điều kiện tái định cư (nếu có).'
    dt = (h['dien_thoai'] or '').strip()
    k = h.keys()
    return dict(ma_ho=ma_ho, ho_ten=ten, cccd=cccd.strip(' -'), dia_chi=(h['dia_chi'] or '').strip(),
                dien_thoai='' if dt == '0' else dt, nguon_goc='\n'.join(ng), tai_dinh_cu=tdc,
                so_pa=(h['so_pa'] or '').strip() if 'so_pa' in k else '', ngay_pa=(h['ngay_pa'] or '') if 'ngay_pa' in k else '')


# ---------------------------------------------------------------- phương án chi tiết (A4 dọc)
def lap_chi_tiet(con, ma_ho: int, file_ra, mau: Path | None = None, bc: BoiCanh | None = None) -> Path:
    """Điền mẫu IN_CHITIET cho một hộ, lưu thành file .xlsx. Trả đường dẫn file. mau: thư mục mẫu hoặc file mẫu riêng."""
    mau = file_mau(mau, TEN_CT)
    duong_ke = duong_ke_cua_mau(mau, TEN_CT)
    wb = openpyxl.load_workbook(mau)
    ws = wb.worksheets[0]
    da = _thong_tin_du_an(con)
    dong, kq = dong_chi_tiet(con, ma_ho, bc)
    ttho = _thong_tin_ho(con, ma_ho, da)
    do = _ham_do_chu()
    dat_doan_van(ws, '{nguon_goc}', ttho['nguon_goc'], do)     # trước khi tìm dòng STT: có thể chèn thêm dòng
    vt_du_an = vi_tri_cho(ws, '{du_an}', 20)
    dau = next((r for r in range(1, 300) if str(ws.cell(r, 1).value or '').strip().upper() == 'STT'), 17) + 1
    n = len(dong)
    _doi_dong(ws, dau + 1, n - 1)
    for r in range(dau + 1, dau + n):
        _chep_kieu_dong(ws, dau, r, 8)
        ws.cell(r, COT_KIND)._style = copy(ws.cell(dau, COT_KIND)._style)
    rong_b = ws.column_dimensions['B'].width or 28
    rong_h = ws.column_dimensions['H'].width or 28
    co = ws.cell(dau, 2).font.sz or 14
    rong_cf = sum((ws.column_dimensions[x].width or 12) for x in 'CDEF')
    for i, x in enumerate(dong):
        loai, gt = x[0], x[1]
        cach_tinh = x[2] if len(x) > 2 else ''
        r = dau + i
        for c, v in enumerate(gt, start=1):
            o = ws.cell(r, c)
            if c == 1:
                o.value = None if v is None else str(v)
            elif c in (4, 5, 6, 7):
                o.value = _so(v)
            else:
                o.value = v if v not in ('',) else None
        ws.cell(r, COT_KIND).value = loai
        cao = max(_uoc_cao(gt[1], rong_b, co), _uoc_cao(gt[7], rong_h, co))
        if cach_tinh:                                   # cách tính in gộp ô ĐVT..tỷ lệ (thay số lượng, đơn giá)
            for c in (4, 5, 6):
                ws.cell(r, c).value = None
            ws.cell(r, 3).value = cach_tinh
            ws.cell(r, 3).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            _gop_o(ws, r, 3, r, 6)
            cao = max(cao, _uoc_cao(cach_tinh, rong_cf, co))
        ws.row_dimensions[r].height = cao
    _vung_cf(ws, dau, dau + n - 1)
    gia_tri = dict(da, **ttho)
    dien_so_ngay(ws, ttho['so_pa'], ttho['ngay_pa'], 'Số:', dau - 1)      # số / ngày PA chi tiết (đợt trình) vào chỗ chừa trống
    _thay_cho_trong(ws, gia_tri)
    vua_chu(ws, vt_du_an, do)
    for r in range(dau + n, min(dau + n + 6, ws.max_row + 1)):          # dòng IV: "Tái định cư: …" (mẫu cũ ghi "Phương án …")
        o = ws.cell(r, 2)
        if isinstance(o.value, str) and o.value.startswith('Phương án tái định cư:'):
            o.value = 'Tái định cư:' + o.value[len('Phương án tái định cư:'):]
        if isinstance(o.value, str) and len(o.value) > 40:
            _gian_dong(ws, r, 2, co)
    ws.print_area = f'A1:H{_dong_cuoi(ws, 8) + 1}'
    wb.defined_names[TEN_CAO] = DefinedName(TEN_CAO, attr_text=f"'{ws.title}'!$A${dau}:$H${dau + n - 1}")
    wb.calculation.fullCalcOnLoad = True
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_ra)
    chen_duong_ke(file_ra, duong_ke)              # đường kẻ của mẫu (openpyxl không giữ hình vẽ)
    return file_ra


# ---------------------------------------------------------------- bảng tổng hợp (A3 ngang)
def ho_co_phuong_an(con) -> list:
    """Mọi hộ có dòng phương án (kể cả phương án phần mềm tự lập chưa soát)."""
    return [k.ma_ho for k in nghiep_vu.tinh_tat_ca(con) if k.co_phuong_an]


LAP = {'da_lap': 'Đã lập phương án', 'tu_lap': 'Tự lập, chưa soát', 'chua': 'Chưa có phương án'}
# phan_loai_lap chuyển sang lap_pa (màn hình chính gọi mỗi lần tải lại mà không phải nạp openpyxl); giữ tên cũ ở đây
from .lap_pa import HANG_LOAT_GIAY, HANG_LOAT_TOI_THIEU, phan_loai_lap  # noqa: E402,F401


def ho_da_lap(con) -> list:
    """Hộ người dùng đã lập phương án (không tính phương án tự lập chưa soát), theo thứ tự danh sách."""
    pl = phan_loai_lap(con)
    return [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho') if pl.get(r[0]) == 'da_lap']


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


def lap_bang_tong_hop(con, file_ra, ds_ma_ho: list | None = None, mau: Path | None = None, so_pa_tong: str = '',
                      ngay_pa_tong: str = '', bao_tien_do=None) -> Path:
    """Bảng tổng hợp các hộ. so_pa_tong / ngay_pa_tong (phương án tổng của đợt trình): điền vào "(Đính kèm Phương án số …/…
    ngày … tháng … năm …)" và ngày ký của mẫu (chỗ trống {so_pa_tong}, {ngay_pa_tong} cũng dùng được).
    bao_tien_do(i, n): gọi mỗi 100 hộ để hộp tiến trình vẽ lại (bảng nhiều hộ, không "Không phản hồi"); không dừng giữa chừng."""
    mau = file_mau(mau, TEN_BTH)
    duong_ke = duong_ke_cua_mau(mau, TEN_BTH)
    wb = openpyxl.load_workbook(mau)
    ws = wb.worksheets[0]
    da = _thong_tin_du_an(con)
    bc = BoiCanh.tu(con)
    if ds_ma_ho is None:
        ds_ma_ho = ho_co_phuong_an(con)
    thu_tu = {r['ma_ho']: (r['thu_tu'], r['ma_ho']) for r in con.execute('SELECT ma_ho, thu_tu FROM ho')}
    ds_ma_ho = sorted(ds_ma_ho, key=lambda m: thu_tu.get(m, (0, m)))
    khoi = []
    tat_ca = nghiep_vu.doc_tat_ca_phuong_an(con, ds_ma_ho)              # 3 câu truy vấn thay vì 3 câu mỗi hộ
    kqh = nghiep_vu.ket_qua_ho(con)                                     # kết quả đã tính dùng chung (cùng dữ liệu)
    for ma in ds_ma_ho:
        pa = tat_ca.get(ma) or doc_phuong_an(con, ma)
        kq = kqh[ma][0] if ma in kqh else tinh_pa(pa, bc)
        thua = list(bc.thua_cua(ma))
        khoi.append((ma, pa, kq, thua))
    can = sum(max(1, len(t)) for _, _, _, t in khoi) or 1
    _doi_dong(ws, DONG_DAU_BTH + 1, can - 1)
    for r in range(DONG_DAU_BTH + 1, DONG_DAU_BTH + can):
        _chep_kieu_dong(ws, DONG_DAU_BTH, r, 25)
    cao = ws.row_dimensions[DONG_DAU_BTH].height or 36
    for r in range(DONG_DAU_BTH, DONG_DAU_BTH + can):
        ws.row_dimensions[r].height = cao
    r = DONG_DAU_BTH
    tong_thua, tong_dt = 0, KHONG
    ho = {r['ma_ho']: r for r in con.execute('SELECT * FROM ho')}       # một câu thay vì một câu mỗi hộ
    for stt, (ma, pa, kq, thua) in enumerate(khoi, start=1):
        if bao_tien_do and stt % 100 == 0:
            bao_tien_do(stt, len(khoi))
        h = ho[ma]
        r0 = r
        ws.cell(r0, 1).value = stt
        ws.cell(r0, 2).value = h['ho_ten']
        ws.cell(r0, 3).value = h['dia_chi']
        for t in thua:
            dat_thua = [d for d in pa.dat if d.ma_thua == t['ma_thua']]
            ws.cell(r, 4).value = t['so_to']
            ws.cell(r, 5).value = t['so_thua']
            ws.cell(r, 6).value = t['loai_dat']
            ws.cell(r, 7).value = _so(t['dt_thu_hoi'])
            nn = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Nông nghiệp'), KHONG)
            lua = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Nông nghiệp' and d.loai_dat.upper() in ('LUC', 'LUK')), KHONG)
            o = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Đất ở'), KHONG)
            pnn = sum((d.dien_tich for d in dat_thua if d.nhom_dat == 'Phi nông nghiệp'), KHONG)
            ws.cell(r, 8).value = _so(nn)
            ws.cell(r, 9).value = _so(lua) if lua else None
            ws.cell(r, 10).value = _so(o + pnn)
            ws.cell(r, 11).value = _so(o)
            ws.cell(r, 14).value = dat_thua[0].vi_tri if dat_thua else None
            if ws.cell(r0, 23).value in (None, '') and t['nguon_goc']:
                ws.cell(r0, 23).value = t['nguon_goc']
            tong_thua += 1
            tong_dt += D(t['dt_thu_hoi'])
            r += 1
        if r == r0:
            r += 1
        ht = kq.muc[4]
        dao_tao = sum((nghiep_vu.thanh_tien_dong(d, bc) for d in pa.dong_ho_tro('HT09', 'HT10')), KHONG)
        on_dinh = sum((nghiep_vu.thanh_tien_dong(d, bc) for d in pa.dong_ho_tro(*MA_ON_DINH)), KHONG)
        for c, v in ((16, kq.muc[1]), (17, kq.muc[2]), (18, kq.muc[3]), (19, dao_tao), (20, on_dinh), (21, kq.muc[5]), (22, kq.tong)):
            ws.cell(r0, c).value = _so(v)
        ws.cell(r0, 24).value = h['tai_dinh_cu'] or None
        khac = ht - dao_tao - on_dinh
        ws.cell(r0, 25).value = f'Hỗ trợ khác: {format(int(khac), ",").replace(",", ".")} đ' if khac > 0 else None
        if r - 1 > r0:
            for c in (1, 2, 3, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25):
                _gop_o(ws, r0, c, r - 1, c)
    tong = DONG_DAU_BTH + can
    for c in range(7, 23):
        cl = openpyxl.utils.get_column_letter(c)
        if c in (12, 13, 15):
            continue
        ws.cell(tong, c).value = f'=SUM({cl}{DONG_DAU_BTH}:{cl}{tong - 1})'
    # các dòng kinh phí dưới dòng tổng: kinh phí tổ chức thực hiện theo loại dự án (QĐ 08/2025/QĐ-UBND: theo tuyến 3,5%, cụm /
    # vùng / khác 2,5% - lap_pa.kinh_phi_to_chuc), thay tỷ lệ trong chữ của mẫu; dòng chia (85% / 15%...) giữ tỷ lệ của mẫu
    from .lap_pa import CAN_CU_KINH_PHI, kinh_phi_to_chuc
    from .tien import chuoi, so_vn
    _, tl_kp, _ = kinh_phi_to_chuc(con)
    for rr in range(tong + 1, tong + 5):
        a = str(ws.cell(rr, 1).value or '') + ' ' + str(ws.cell(rr, 8).value or '')
        if rr == tong + 1:
            chu = str(ws.cell(rr, 1).value or '')
            if chu:
                chu = re.sub(r'[\d,\.]+\s*%', f'{so_vn(tl_kp)}%', chu, count=1) if '%' in chu else \
                    chu.rstrip(': ') + f' {so_vn(tl_kp)}%:'
                if '08/2025' not in chu:
                    chu = chu.rstrip(': ') + f' (theo {CAN_CU_KINH_PHI}):'
                ws.cell(rr, 1).value = chu
            ws.cell(rr, 22).value = f'=ROUND(V{tong}*{chuoi(tl_kp)}%, -3)'
        elif 'TỔNG CỘNG' in a:
            ws.cell(rr, 22).value = f'=V{tong}+V{tong + 1}'
        else:
            pt = re.search(r'(\d+)%', str(ws.cell(rr, 8).value or ''))
            if pt:
                ws.cell(rr, 22).value = f'=ROUND(V{tong + 1}*{pt.group(1)}%, -3)'
    a6 = str(ws['A6'].value or '')
    if '(Đối với ' in a6:
        ws['A6'] = re.sub(r'\(Đối với .*?m2\)', f'(Đối với {len(khoi):02d} trường hợp/ {tong_thua} thửa đất/ '
                          f'{format(float(tong_dt), ",.1f").replace(",", "#").replace(".", ",").replace("#", ".")}m2)', a6)
    dien_so_ngay(ws, so_pa_tong, ngay_pa_tong, 'Phương án số')
    _thay_cho_trong(ws, dict(da, so_pa_tong=so_pa_tong or '', ngay_pa_tong=ngay_pa_tong or ''))
    ws.print_area = f'A1:Y{_dong_cuoi(ws, 25) + 1}'
    wb.calculation.fullCalcOnLoad = True
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_ra)
    chen_duong_ke(file_ra, duong_ke)              # đường kẻ của mẫu (openpyxl không giữ hình vẽ)
    return file_ra


# ---------------------------------------------------------------- PDF / máy in qua Microsoft Excel
_VBS = r'''
On Error Resume Next
Dim xl, wb, f, i, ds, che_do, r, h, nm, fso, dung, so
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
        Set nm = wb.Names("PABT_TU_GIAN_DONG")
        If Err.Number = 0 Then
            For Each r In nm.RefersToRange.Rows
                r.AutoFit
                h = r.RowHeight + 8
                If h < 26 Then h = 26
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
        p = lap_bang_tong_hop(con, thu_muc / 'BANG_TONG_HOP.xlsx', ds_ma_ho, mau,
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

