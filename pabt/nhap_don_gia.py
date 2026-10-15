"""Cập nhật bộ đơn giá từ file bất kỳ (Excel .xlsx/.xlsm/.xls, Word .docx/.doc, PDF có chữ / scan, CSV). Phần tải từ trang
web nằm ở cap_nhat_web.py (phát hành riêng bằng gói cập nhật).

Quy trình: đọc bảng -> nhận các dòng (tên, ĐVT, đơn giá, mã nếu có) -> so khớp với bộ đơn giá đang dùng
(theo mã, rồi theo tên không dấu) -> người dùng xem / bỏ chọn -> áp dụng: tạo phiên bản bộ đơn giá mới và cài
(bộ cũ không bị sửa; dự án đã lập giữ đơn giá cũ cho tới khi "Áp bộ đơn giá vào dự án").
"""
from __future__ import annotations
import csv
import os
import io
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from . import csdl, don_gia
from .lap_pa import LoiNhap, bo_dau
from .tien import D, chuoi

DUOI_HO_TRO = ('.xlsx', '.xlsm', '.docx', '.pdf', '.csv', '.txt', '.sqlite')
DUOI_LIEN_KET = DUOI_HO_TRO + ('.xls', '.doc')     # liên kết trên trang web đáng đưa vào danh sách chọn
# nhóm danh mục khi cập nhật đơn giá. 7 = vật nuôi (= nghiep_vu.MUC_VN) CHỈ dùng khi phân tích / chọn trên màn hình - ghi vào bộ
# đơn giá là nhom 3 + phân loại vật nuôi + mã VN (cấu trúc CSDL không đổi: dm_taisan.nhom 2 / 3, chính sách ở bảng dm_hotro)
NHOM_VN = 7
NHOM = {2: 'Nhà, công trình, vật kiến trúc (mã TS)', 3: 'Cây trồng, hoa màu (mã CT)', NHOM_VN: 'Vật nuôi, thủy sản (mã VN)',
        4: 'Chính sách hỗ trợ (mã CS)'}
TIEN_TO = {2: 'TS', 3: 'CT', NHOM_VN: 'VN', 4: 'CS'}
# phân loại mặc định khi bộ đơn giá chưa có dòng nào của nhóm (bình thường lấy đúng chuỗi đang dùng trong bộ - _phan_loai)
PHAN_LOAI_MAC_DINH = {2: '2. Bồi thường, hỗ trợ về nhà và công trình xây dựng', 3: '3. Bồi thường, hỗ trợ về cây trồng'}
DVT = (r'm²|m2|m³|m3|md|m|cây|cay|bụi|bui|khóm|hố|ha|kg|cái|chiếc|bộ|hộ|khẩu|nhân khẩu|tháng|ngôi|mộ|con|đơn vị|'
       r'lần|đồng/m²|đ/m²|ô|gốc|bụi|m²sàn|m2 sàn')


@dataclass
class Muc:
    ten: str
    dvt: str
    don_gia: int
    ma: str = ''
    nguon_dong: str = ''          # dòng gốc (để người dùng đối chiếu)
    chon: bool = True
    trang_thai: str = ''          # mới / cập nhật / giữ nguyên
    ma_khop: str = ''
    gia_cu: int | None = None
    nhom: int = 0                 # 2 nhà, công trình / 3 cây trồng / 7 vật nuôi / 4 hỗ trợ (0: chưa xác định)
    khop_gan: float = 0.0         # so khớp tên gần đúng (tỷ lệ giống); 0 = khớp đúng mã / tên


class LoiPdfScan(LoiNhap):
    """PDF không có lớp chữ (ảnh scan): chỉ đọc được bằng nhận dạng chữ (OCR)."""


class LoiKhongCoGia(LoiNhap):
    """Văn bản đọc được nhưng không có đơn giá (không bảng giá, không câu "<số> đồng/<ĐVT>"): văn bản quy định chính sách.
    Tách khỏi LoiNhap khác để màn hình không báo nhầm lỗi đọc / so khớp thành "không có đơn giá"."""


def loai_that(p) -> str:
    """Loại file theo nội dung (vài byte đầu), không theo đuôi: '.pdf', '.xlsx', '.docx', '.sqlite', '.html', '.xls'
    (Office cũ) hoặc '' nếu không nhận ra. File tải từ web hay bị đặt sai đuôi (trang HTML báo lỗi / đăng nhập mang đuôi .pdf)."""
    try:
        with open(p, 'rb') as f:
            dau = f.read(512)
    except OSError:
        return ''
    if dau.startswith(b'%PDF') or b'%PDF-' in dau[:256]:
        return '.pdf'
    if dau.startswith(b'SQLite format 3'):
        return '.sqlite'
    if dau.startswith(b'\xd0\xcf\x11\xe0'):            # Office 97-2003: Word / Excel theo tên luồng dữ liệu bên trong
        try:
            with open(p, 'rb') as f:
                toan = f.read(30 * 2 ** 20)
        except OSError:
            return ''
        if 'WordDocument'.encode('utf-16-le') in toan:
            return '.doc'
        if 'Workbook'.encode('utf-16-le') in toan or 'Book'.encode('utf-16-le') in toan:
            return '.xls'
        return ''
    if dau.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(p) as z:
                ten = set(z.namelist())
        except (zipfile.BadZipFile, OSError):
            return ''
        return '.docx' if 'word/document.xml' in ten else '.xlsx' if 'xl/workbook.xml' in ten else ''
    chu = dau.lstrip(b'\xef\xbb\xbf \t\r\n').lower()
    if chu.startswith((b'<!doctype html', b'<html', b'<head', b'<!--', b'<script', b'<meta')):
        return '.html'
    return ''


# ---------------------------------------------------------------- đọc bảng từ các loại file
def doc_bang(file) -> list:
    """Các dòng (danh sách ô chữ) của mọi bảng trong file."""
    p = Path(file)
    duoi = p.suffix.lower()
    if duoi in ('.xlsx', '.xlsm', '.docx', '.pdf', '.xls', '.doc'):
        that = loai_that(p)
        if that == '.html':
            raise LoiNhap(f'File "{p.name}" thực chất là một trang web (HTML), không phải file {duoi}: thường do trang tải về '
                          'yêu cầu đăng nhập / xác nhận, hoặc liên kết đã hết hạn. Mở đường dẫn bằng trình duyệt, tải file về '
                          'máy rồi dùng "Cập nhật bộ đơn giá từ file…".')
        if that in ('.xls', '.doc'):                    # Office 97-2003 (văn bản trên Công báo hay là .doc): nhờ Word / Excel
            return doc_bang(chuyen_office(p, that))
        if that in ('.pdf', '.docx') and that != duoi or that == '.xlsx' and duoi not in ('.xlsx', '.xlsm'):
            duoi = that                                 # đúng nội dung nhưng sai đuôi: đọc theo nội dung
        elif not that:
            raise LoiNhap(f'File "{p.name}" bị hỏng hoặc chưa tải xong (nội dung không phải {duoi}).')
        if that in ('.xlsx', '.docx'):                  # file Office là file nén: chặn "bom nén", đường dẫn nguy hiểm
            from . import an_toan
            try:
                an_toan.kiem_tra_zip(p)
            except an_toan.LoiAnToan as e:
                raise LoiNhap(str(e)) from None
    if duoi in ('.xlsx', '.xlsm'):
        import openpyxl
        with open(p, 'rb') as f:                        # mở bằng file: openpyxl từ chối đường dẫn sai đuôi
            wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
            try:
                return [[('' if v is None else str(v)).strip() for v in r] for ws in wb.worksheets
                        for r in ws.iter_rows(values_only=True)]
            finally:
                wb.close()
    if duoi == '.docx':
        return _doc_docx(p)
    if duoi == '.pdf':
        return [[l] for l in _doc_pdf(p)]
    if duoi in ('.csv', '.txt'):
        txt = p.read_text(encoding='utf-8-sig', errors='replace')
        try:
            mau = csv.Sniffer().sniff(txt[:4000], delimiters=',;\t') if txt.strip() else csv.excel
        except csv.Error:                               # văn bản thường (không có cột): mỗi dòng một ô
            return [[l.strip()] for l in txt.splitlines()]
        return [[c.strip() for c in r] for r in csv.reader(txt.splitlines(), mau)]
    raise LoiNhap(f'Chưa hỗ trợ file {duoi or "(không có đuôi)"}. Hỗ trợ: Excel, Word (.docx), PDF có chữ, CSV.')


_VBS_CHUYEN = r'''
On Error Resume Next
Set f = CreateObject("Scripting.FileSystemObject").OpenTextFile(WScript.Arguments(0), 1, False, -1)
loai = f.ReadLine
nguon = f.ReadLine
dich = f.ReadLine
f.Close
If loai = "doc" Then
    Set w = CreateObject("Word.Application")
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "KHONG_CO_OFFICE"
        WScript.Quit 3
    End If
    w.Visible = False
    w.DisplayAlerts = 0
    w.AutomationSecurity = 3
    Set d = w.Documents.Open(nguon, False, True, False)
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "LOI_MO" & vbTab & Err.Description
        w.Quit 0
        WScript.Quit 4
    End If
    d.SaveAs2 dich, 16
    If Err.Number <> 0 Then
        Err.Clear
        d.SaveAs dich, 12
    End If
    If Err.Number <> 0 Then WScript.StdErr.WriteLine "LOI_LUU" & vbTab & Err.Description
    d.Close 0
    w.Quit 0
Else
    Set x = CreateObject("Excel.Application")
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "KHONG_CO_OFFICE"
        WScript.Quit 3
    End If
    x.Visible = False
    x.DisplayAlerts = False
    x.AutomationSecurity = 3
    x.EnableEvents = False
    Set b = x.Workbooks.Open(nguon, 0, True)
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "LOI_MO" & vbTab & Err.Description
        x.Quit
        WScript.Quit 4
    End If
    b.SaveAs dich, 51
    If Err.Number <> 0 Then WScript.StdErr.WriteLine "LOI_LUU" & vbTab & Err.Description
    b.Close False
    x.Quit
End If
'''


def chuyen_office(p, loai: str = '') -> Path:
    """File Word / Excel 97-2003 (.doc / .xls) -> .docx / .xlsx cạnh file gốc, nhờ Microsoft Word / Excel trên máy."""
    p = Path(p).resolve()
    loai = loai or loai_that(p) or p.suffix.lower()
    dich = p.with_name(p.stem + ('_chuyen.docx' if loai == '.doc' else '_chuyen.xlsx'))
    if dich.exists() and dich.stat().st_mtime >= p.stat().st_mtime:
        return dich
    ten = 'Word' if loai == '.doc' else 'Excel'
    thay = (f'File "{p.name}" là định dạng {ten} 97-2003 ({loai}): mở bằng {ten}, lưu lại dạng {loai}x rồi chọn lại.')
    if sys.platform != 'win32':
        raise LoiNhap(thay)
    with tempfile.TemporaryDirectory() as td:
        vbs = Path(td) / 'chuyen.vbs'
        vbs.write_text(_VBS_CHUYEN, encoding='utf-16')
        ds = Path(td) / 'ds.txt'
        ds.write_text('\n'.join(('doc' if loai == '.doc' else 'xls', str(p), str(dich))), encoding='utf-16')
        try:
            kq = subprocess.run(['cscript', '//nologo', str(vbs), str(ds)], capture_output=True, timeout=180,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.TimeoutExpired) as e:
            raise LoiNhap(f'{thay}\n({e})') from None
    loi = kq.stderr.decode('oem', 'replace').strip()
    if not dich.exists():
        if 'KHONG_CO_OFFICE' in loi:
            raise LoiNhap(f'Máy chưa có Microsoft {ten} để đọc file cũ. {thay}')
        raise LoiNhap(f'{thay}\n({loi[:300]})')
    return dich


def _doc_docx(p: Path) -> list:
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    from . import an_toan
    with zipfile.ZipFile(p) as z:
        du = z.read('word/document.xml')
    try:
        an_toan.kiem_tra_xml(du, p.name)                # XML có DOCTYPE / ENTITY: không phân tích
    except an_toan.LoiAnToan as e:
        raise LoiNhap(str(e)) from None

    def chu(par) -> str:
        return ' '.join(''.join(t.text or '' for t in par.iter(W + 't')).split())

    def o(tc) -> str:                                   # các đoạn trong một ô cách nhau dấu cách ("ỦY BAN NHÂN DÂN TỈNH ...")
        return ' '.join(x for x in (chu(par) for par in tc.iter(W + 'p')) if x)
    # theo thứ tự trong văn bản: đoạn văn (số, ngày, trích yếu ở đầu quyết định) mỗi đoạn một dòng; bảng mỗi hàng một dòng.
    # Đọc dòng chảy (iterparse, 0.9.87): đọc xong một hàng của bảng cấp ngoài / một đoạn văn thì xử lý rồi xóa khỏi cây - không
    # giữ cả cây XML của văn bản lớn trong RAM (bản 32-bit Windows 7). Thứ tự và kết quả như dựng cả cây (kể cả hàng của bảng lồng
    # trong ô: xếp ngay sau hàng chứa nó, như tbl.iter('tr')).
    dong = []
    ngan = []                                           # các phần tử đang mở (gốc -> phần tử hiện tại)
    for su_kien, el in ET.iterparse(io.BytesIO(du), events=('start', 'end')):
        if su_kien == 'start':
            ngan.append(el)
            continue
        ngan.pop()
        if not ngan:
            break
        cha = ngan[-1]
        tang_ngoai = len(ngan) == 2 and ngan[1].tag == W + 'body'          # phần tử con của <w:body>
        if el.tag == W + 'tr' and len(ngan) == 3 and ngan[1].tag == W + 'body' and cha.tag == W + 'tbl':
            dong += [[o(tc) for tc in tr.findall(W + 'tc')] for tr in el.iter(W + 'tr')]      # hàng của bảng cấp ngoài
            el.clear()
            cha.remove(el)
        elif tang_ngoai:
            if el.tag == W + 'tbl':
                dong += [[o(tc) for tc in tr.findall(W + 'tc')] for tr in el.iter(W + 'tr')]  # (hàng đã xử lý ở trên)
            else:
                dong += [[t] for t in (chu(par) for par in ([el] if el.tag == W + 'p' else el.iter(W + 'p'))) if t]
            el.clear()
            cha.remove(el)
    if not dong and b'body>' not in du:                 # XML lạ không có <w:body>: đọc các phần tử con của gốc như trước
        for el in ET.fromstring(du):
            if el.tag == W + 'tbl':
                dong += [[o(tc) for tc in tr.findall(W + 'tc')] for tr in el.iter(W + 'tr')]
            else:
                dong += [[t] for t in (chu(par) for par in ([el] if el.tag == W + 'p' else el.iter(W + 'p'))) if t]
    return dong


def _doc_pdf(p: Path) -> list:
    """Chữ từng dòng của PDF (PDF có lớp chữ; PDF ảnh scan không đọc được). Qt6 dùng QtPdf, Qt5 (bản Win 7/8) dùng pypdf."""
    dong = []
    try:
        from PySide6.QtPdf import QPdfDocument
    except ImportError:
        QPdfDocument = None
    if QPdfDocument is not None:
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841
        d = QPdfDocument()
        loi = d.load(str(p))
        if loi == QPdfDocument.Error.IncorrectPassword:
            raise LoiNhap(f'PDF "{p.name}" có mật khẩu: mở bằng trình đọc PDF, in / lưu lại bản không mật khẩu rồi chọn lại.')
        if loi != QPdfDocument.Error.None_ or d.pageCount() == 0:
            raise LoiNhap(f'Không đọc được PDF "{p.name}" (file hỏng hoặc chưa tải xong).')
        for i in range(d.pageCount()):
            dong += [l.strip() for l in d.getAllText(i).text().splitlines() if l.strip()]
    else:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise LoiNhap('Máy này thiếu bộ đọc PDF: chuyển file sang Excel / Word rồi cập nhật.') from e
        try:
            for trang in PdfReader(str(p)).pages:
                dong += [l.strip() for l in (trang.extract_text() or '').splitlines() if l.strip()]
        except Exception as e:  # pypdf báo nhiều loại lỗi khác nhau với file hỏng
            raise LoiNhap(f'Không đọc được PDF: {e}') from e
    if not dong:
        raise LoiPdfScan('PDF là ảnh scan (không có lớp chữ): cần nhận dạng chữ (OCR) hoặc chuyển sang Excel / Word trước khi '
                         'cập nhật.')
    return dong


def dong_tu_chu(chu: str) -> list:
    """Chữ dán từ Clipboard -> dòng bảng như doc_bang: dòng có Tab (chép từ Excel / bảng Word) tách thành ô, không có Tab thì cả dòng
    là một ô (chữ Snipping Tool, Zalo OCR - đọc theo mẫu '<tên> <ĐVT> <đơn giá>'). Dòng trống bỏ."""
    from .ocr import sua_so
    kq = []
    for d in str(chu or '').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if not d.strip():
            continue
        o = [' '.join(x.split()) for x in d.split('\t')] if '\t' in d else [sua_so(' '.join(d.split()))]
        if any(o):
            kq.append(o)
    return kq


def doc_bang_ocr(file, bao_tien_do=None, cho=None) -> list:
    """Như doc_bang; PDF ảnh scan thì nhận dạng chữ bằng Tesseract (nếu máy có) - mỗi dòng chữ một ô, đọc theo mẫu
    '<tên> <ĐVT> <đơn giá>'. bao_tien_do(trang, tổng), cho() -> True để hủy (ocr.DaHuy)."""
    try:
        return doc_bang(file)
    except LoiPdfScan as e:
        from . import ocr
        thieu = ocr.san_sang()
        if thieu:
            raise LoiPdfScan(f'{e}\n\n{thieu}') from None
        try:
            return [[x] for x in ocr.doc_chu(file, bao_tien_do, cho)]
        except ocr.DaHuy:
            raise
        except ocr.LoiOCR as l:
            raise LoiPdfScan(f'{e}\n\nNhận dạng chữ không được: {l}') from None


# ---------------------------------------------------------------- nhận biết văn bản: số, ngày, cơ quan ban hành, trích yếu
# loại văn bản trong số hiệu: QĐ, NQ, CT (địa phương); NĐ (nghị định), TT / TTLT (thông tư), QH15 (luật, nghị quyết Quốc hội)
_RE_SO_VB = re.compile(r'(?i)\bs[ốo]\s*:?\s*(\d+[a-z]?\s*/\s*(?:\d{4}\s*/\s*)?(?:QĐ|QD|NQ|CT|NĐ|ND|TTLT|TT|QH)[\w.Đđ-]*)')
_RE_SO_TRONG = re.compile(r'(?i)\b(\d+[a-z]?\s*/\s*(?:\d{4}\s*/\s*)?(?:(?:QĐ|QD|NQ|NĐ|ND|TTLT|TT)-[\wĐđ.]+|QH\d+))')
_TIEU_DE_LOAI = ('quyet dinh', 'nghi quyet', 'nghi dinh', 'thong tu', 'thong tu lien tich', 'luat')
_RE_NGAY_VB = re.compile(r'(?i)ngày\s*(\d{1,2})\s*(?:/|-|tháng)\s*(\d{1,2})\s*(?:/|-|năm)\s*(\d{4})')


def chuan_so_hieu(s: str) -> str:
    """'48 / 2025 / QĐ-UBND' -> '48/2025/QD-UBND' (so sánh số hiệu văn bản)."""
    return re.sub(r'\s+', '', bo_dau(s or '')).upper()


def phan_tich_van_ban(dong: list, ten_goi: str = '') -> dict:
    """Số hiệu, ngày ban hành, cơ quan, loại, trích yếu của văn bản (các dòng đầu đọc từ Word / PDF / OCR) và tên gọi trên
    trang web (nếu có); nhom: nhóm danh mục đoán theo trích yếu (3 cây trồng, vật nuôi / 2 nhà, công trình / 4 hỗ trợ);
    dong_nai: văn bản của Đồng Nai; sua_doi: văn bản sửa đổi, bổ sung."""
    dau = [' '.join(' '.join(c for c in r if c).split()) for r in dong[:150]]
    toan = '\n'.join(x for x in dau if x)
    so = ngay = ''
    m = _RE_SO_VB.search(toan) or _RE_SO_TRONG.search(ten_goi or '')
    if m:
        so = re.sub(r'\s+', '', m.group(1)).strip('.,;')
        mn = _RE_NGAY_VB.search(toan[m.end(): m.end() + 300]) if m.re is _RE_SO_VB else None
        mn = mn or _RE_NGAY_VB.search(toan) or _RE_NGAY_VB.search(ten_goi or '')
        if mn:
            ngay = f'{int(mn.group(1)):02d}/{int(mn.group(2)):02d}/{mn.group(3)}'
    kd = bo_dau(toan[:1500])
    co_quan = ''
    mc = re.search(r'(uy ban nhan dan|hoi dong nhan dan)\s+(tinh|thanh pho)\s+dong nai', kd)
    if mc:
        co_quan = ('Ủy ban nhân dân ' if mc.group(1).startswith('uy') else 'Hội đồng nhân dân ') + \
            ('tỉnh' if mc.group(2) == 'tinh' else 'thành phố') + ' Đồng Nai'
    else:                                               # văn bản Trung ương: cơ quan ở các dòng đầu
        for x in dau[:8]:
            k = bo_dau(x)
            if k in ('quoc hoi', 'chinh phu', 'thu tuong chinh phu'):
                co_quan = {'quoc hoi': 'Quốc hội', 'chinh phu': 'Chính phủ', 'thu tuong chinh phu': 'Thủ tướng Chính phủ'}[k]
                break
            if re.fullmatch(r'bo [a-z ,]{4,60}', k):     # "BỘ NÔNG NGHIỆP VÀ MÔI TRƯỜNG" -> "Bộ Nông nghiệp và môi trường"
                ten = x[3:].strip().lower()
                co_quan = 'Bộ ' + ten[:1].upper() + ten[1:]
                break
    su = bo_dau(so).upper()
    loai = ('Nghị quyết' if 'NQ' in su else 'Quyết định' if re.search(r'Q[D]', su) else 'Nghị định' if re.search(r'/N[D]', su)
            else 'Thông tư liên tịch' if 'TTLT' in su else 'Thông tư' if re.search(r'/TT', su) else '')
    trich = []
    for i, x in enumerate(dau):
        k = bo_dau(x)
        if not loai and 'QH' in su and re.match(r'(luat|nghi quyet)\b', k):
            loai = 'Luật' if k.startswith('luat') else 'Nghị quyết'
        if k.startswith('luat ') and len(x) <= 120 and 'QH' in su and not re.search(r'\d', x):
            trich = [x]                                 # "LUẬT ĐẤT ĐAI": tên luật trên cùng dòng
            break
        if k in _TIEU_DE_LOAI:
            for y in dau[i + 1: i + 5]:
                if not y or re.match(r'(can cu|uy ban nhan dan|hoi dong nhan dan|chu tich|quyet dinh:|quyet nghi|chinh phu ban hanh|'
                                     r'bo truong|quoc hoi ban hanh)', bo_dau(y)):
                    break
                trich.append(y)
            if trich:
                break
    if 'QH' in su and not loai:
        loai = 'Luật'
    trich_yeu = ' '.join(trich)
    if not trich_yeu and ten_goi:                       # tên trên trang web: "Quyết định số 48/2025/QĐ-UBND ban hành ..."
        trich_yeu = re.sub(r'(?i)^.*?\b(q[uđ]y[ếe]t\s+[đd][ịi]nh|ngh[ịi]\s+quy[ếe]t|ngh[ịi]\s+[đd][ịi]nh|th[ôo]ng\s+t[ưu](?:\s+li[êe]n\s+t[ịi]ch)?|'
                           r'lu[ậa]t)\s+s[ốo]\s*\S+\s*', '', ten_goi).strip()
    goc = bo_dau(trich_yeu + ' ' + (ten_goi or ''))
    # câu sửa đổi / bãi bỏ trong thân văn bản: phần mềm chỉ áp dụng bảng giá, các nội dung này người dùng tự xem
    can_xem = []
    for r in dong:
        x = ' '.join(' '.join(c for c in r if c).split())
        if len(r) == 1 and x not in trich and \
                re.match(r'(\d+\.\s*|[a-zđ]\)\s*)?(bai bo|sua doi|bo sung|thay the|ngung ap dung)\b', bo_dau(x)):
            can_xem.append(x[:300])
    return dict(so_hieu=so, ngay=ngay, co_quan=co_quan, loai_vb=loai, trich_yeu=trich_yeu,
                dong_nai='dong nai' in kd or 'dong nai' in bo_dau(ten_goi or ''),
                nhom=nhom_theo_chu(trich_yeu or ten_goi or ''),
                sua_doi=bool(re.search(r'sua doi|bo sung|thay the|bai bo', goc)), can_xem=can_xem[:30])


def van_ban_da_co() -> list:
    """Số hiệu (chuẩn hóa) các văn bản căn cứ đã có trong bộ đơn giá đang dùng (bảng van_ban)."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        return [chuan_so_hieu(r[0]) for r in con.execute('SELECT so_hieu FROM van_ban')]
    finally:
        con.close()


def da_co(so_hieu: str, ds_co: list | None = None) -> bool:
    k = chuan_so_hieu(so_hieu)
    if not k:
        return False
    ds_co = van_ban_da_co() if ds_co is None else ds_co
    # "48/2025/QD-UBND" nằm trong "QUYETDINH48/2025/QD-UBND(SUADOIBOIQD66/2025/QD-UBND)"; tránh 8/2025 khớp nhầm 48/2025
    return any(re.search(r'(?<!\d)' + re.escape(k), x) for x in ds_co)


# ---------------------------------------------------------------- nhận dòng đơn giá
def doc_gia(v) -> int | None:
    """'1.480.500' / '9.445' (nghìn kiểu VN) / '9445000' / 1480500.0 -> int đồng; không phải số tiền -> None."""
    s = str(v or '').strip().replace(' ', '').replace('đ', '').replace('đồng', '')
    if not s:
        return None
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', s) or re.fullmatch(r'\d{1,3}(,\d{3})+', s):
        s = re.sub(r'[.,]', '', s)
    try:
        g = D(s)
    except ValueError:
        return None
    return int(g) if g > 0 and g == int(g) else (int(round(g)) if g >= 1000 else None)


def _cot(tieu_de: list, *mau) -> int | None:
    for i, t in enumerate(tieu_de):
        if any(re.search(m, t) for m in mau):
            return i
    return None


_LA_MA = re.compile(r'^(?:[IVXL]+|[A-H])\.?$')          # STT tiêu đề nhóm: I, II, ... / A, B
_CON = re.compile(r'^(?:[-+–•*]+|[a-zđ][).]?|\d+\.\d+\.?)$', re.I)   # STT dòng con: -, +, *, a, a), 1.1


_RE_VAT_NUOI = re.compile(r'vat nuoi|thuy san|thuy hai san|chan nuoi|gia suc|gia cam|long be|long, be|tham canh|quang canh|'
                         r'ao nuoi|nuoi trong|chim yen|\bca (giong|thit)\b|\btom\b')
_RE_CAY = re.compile(r'cay trong|hoa mau|cay an qua|cay lau nam|cay hang nam|cay canh|\brau\b|\bcay\b')


def nhom_theo_chu(chu: str) -> int:
    """Nhóm danh mục theo chữ (tiêu đề văn bản / tiêu đề nhóm / tên mục): 3 cây trồng, hoa màu; 7 vật nuôi, thủy sản (chỉ khi
    không nói tới cây trồng - "cây trồng, vật nuôi" là 3, từng dòng tự phân); 2 nhà, công trình, vật kiến trúc, mồ mả; 4 chính sách
    hỗ trợ (kể cả di dời mồ mả); 0 không rõ."""
    k = re.sub(r'nha nuoc|uy ban nhan dan|nhan dan', ' ', bo_dau(chu))     # "khi Nhà nước thu hồi đất" không phải nhà ở
    co_vn, co_cay = _RE_VAT_NUOI.search(k), _RE_CAY.search(k)
    if co_vn and not co_cay:
        return NHOM_VN
    if co_cay or co_vn:
        return 3
    if re.search(r'(di doi|boc|cai tang|dao,? boc).{0,12}mo', k):        # "Hỗ trợ đào, bốc, di dời mồ mả": chính sách hỗ trợ
        return 4
    if re.search(r'\bnha\b|cong trinh|vat kien truc|nha o|xay dung|mo ma|\bmo (xay|dat|da)\b', k):
        return 2
    if re.search(r'ho tro|on dinh doi song|dao tao|chuyen doi nghe|tai dinh cu|thue nha', k):
        return 4
    return 0


def _nhom_dong(ten: str, dvt: str) -> int:
    """Nhóm của một dòng khi văn bản / tiêu đề nhóm không cho biết."""
    n = nhom_theo_chu(ten)
    if n:
        return n
    d = ' '.join(bo_dau(dvt).replace('/', ' / ').split())
    # vật nuôi: con, kg, m² mặt nước, ha/vụ, 100m³/vụ, lồng; cây trồng: cây, bụi, gốc, ha (hoa màu)
    if d in ('con', 'kg', 'kg yen tho', 'long', 'be', 'dan', 'o') or re.search(r'mat nuoc|/ vu$|100 ?m[3³]', d):
        return NHOM_VN
    if d in ('cay', 'bui', 'khom', 'goc', 'ha', 'chau', 'hoc'):
        return 3
    if d in ('nhan khau', 'khau', 'ho', 'thang', 'lan'):
        return 4
    return 2


def _tach_gia(o: str):
    """'24.880.000' -> (24880000, ''); 'Đông Xuân: 24.880.000' -> (24880000, 'Đông Xuân')."""
    g = doc_gia(o)
    if g:
        return g, ''
    m = re.match(r'^(.{1,40}?)\s*:\s*([\d][\d.,]*)\s*(?:đ|đồng)?$', ' '.join(str(o or '').split()))
    if m:
        g = doc_gia(m.group(2))
        if g:
            return g, m.group(1).strip()
    return None, ''


def nhan_muc(dong: list, nhom: int = 0) -> list:
    """Dòng bảng -> các mục đơn giá. Có dòng tiêu đề (Tên, ĐVT, Đơn giá) thì theo cột; không có thì đọc theo mẫu
    '<mã> <tên> <ĐVT> <đơn giá>' trên từng dòng chữ (PDF).

    Bảng phân cấp như văn bản UBND: dòng nhóm (I, II...) không có giá; dòng mục (1, 2...) không có giá là "cha" của các dòng
    con (-, +, a)...) -> tên "Cha - Con" như bộ đơn giá; dòng '*' là trường hợp chen giữa; ô giá có nhãn
    ("Đông Xuân: 24.880.000") -> "Tên (Đông Xuân)"; dòng tên trống tiếp tục mục ngay trên. nhom: nhóm mặc định (theo văn bản)."""
    kq, tieu_de, nhan = [], None, 1
    cha = truong_hop = truoc = dvt_mac_dinh = ''
    nhom_muc = 0
    for r in dong:
        o = [bo_dau(c) for c in r]
        ten_c = _cot(o, r'^(ten|loai|noi dung|hang muc|danh muc|tai san|cay trong)', r'\bten (tai san|cay|cong trinh|khoan)')
        gia_c = _cot(o, r'^(don gia|gia|muc (ho tro|boi thuong)|muc gia)', r'don gia')
        if ten_c is not None and gia_c is not None and ten_c != gia_c:
            dvt_c = _cot(o, r'^(dvt|don vi)', r'don vi tinh')
            ma_c = _cot(o, r'^(ma|ma so|ma ts|ma ho tro|ky hieu)$')
            stt_c = _cot(o, r'^(stt|tt|so tt|so thu tu)$')
            tieu_de = (ten_c, gia_c, dvt_c, ma_c, stt_c)
            nhan = 1000 if any(re.search(r'nghin|1\.?000 ?d', x) for x in o) else 1
            # bảng không có cột ĐVT, đơn vị ghi ở tiêu đề cột giá: "Đơn giá bồi thường (đồng/ha)"
            md = re.search(r'(?i)(?:đồng|đ)\s*/\s*([^)]+)\)', r[gia_c])
            dvt_mac_dinh = md.group(1).strip() if md else ''
            cha = truong_hop = truoc = ''
            continue
        if tieu_de and len(r) >= 2:
            ten_c, gia_c, dvt_c, ma_c, stt_c = tieu_de
            r = list(r) + [''] * (max(c for c in tieu_de if c is not None) + 1 - len(r))   # ô gộp: hàng ít ô hơn tiêu đề
            stt = r[stt_c].strip() if stt_c is not None else ''
            ten = ' '.join(r[ten_c].split()).rstrip(' .;:')
            g, nhan_gia = _tach_gia(r[gia_c])
            if not g:
                if not ten:
                    continue
                if _LA_MA.match(stt) or (not stt and re.match(r'(?i)^(nhom|phan|muc|phu luc)\b', bo_dau(ten))):
                    nhom_muc = nhom_theo_chu(ten) or nhom_muc        # tiêu đề nhóm
                    cha = truong_hop = truoc = ''
                elif stt.startswith('*'):
                    truong_hop = ten
                elif _CON.match(stt) and cha:
                    truong_hop = ten                                # dòng con không giá: thêm một cấp
                else:
                    # mật độ ghi ở ghi chú danh mục, không ở tên: "Cây bưởi (Mật độ 210 cây/ha)" -> "Cây bưởi"
                    cha, truong_hop = re.sub(r'(?i)\s*\(\s*m[ậa]t\s*[đd][ộo][^)]*\)', '', ten).strip(), ''
                continue
            if not ten:                                             # tiếp tục mục ngay trên (ô tên gộp)
                ten = truoc
            elif _CON.match(stt) or stt.startswith('*') or (not stt and cha):     # dòng con (STT -, a)... hoặc để trống)
                ten = ' - '.join(x for x in (cha, truong_hop, ten) if x)
            else:
                cha = truong_hop = ''
            truoc = ten
            if not ten or re.fullmatch(r'[\d\W]+', ten):
                continue
            ten_day = f'{ten} ({nhan_gia})' if nhan_gia else ten
            dvt = (r[dvt_c].strip() if dvt_c is not None else '') or dvt_mac_dinh
            dvt = re.sub(r'(?i)^(?:đồng|đ)\s*/\s*', '', dvt)          # "đồng/bụi" -> "bụi"
            kq.append(Muc(ten_day, dvt, g * nhan, r[ma_c].strip() if ma_c is not None else '',
                          ' | '.join(c for c in r if c), nhom=nhom or nhom_muc or _nhom_dong(ten_day, dvt)))
            continue
        if len(r) == 1:                                   # dòng chữ (PDF / Word không bảng)
            m = re.match(rf'^(?:(\d+|[A-Z]{{1,3}}\d+)\s+)?(.+?)\s+({DVT})\s+([\d][\d\.,]*)$', r[0], re.I)
            if m:
                g = doc_gia(m.group(4))
                if g:
                    ten = ' '.join(m.group(2).split())
                    kq.append(Muc(ten, m.group(3), g, m.group(1) if m.group(1) and not m.group(1).isdigit() else '', r[0],
                                  nhom=nhom or _nhom_dong(ten, m.group(3))))
    return kq


# ---------------------------------------------------------------- đơn giá ghi trong lời văn (văn bản không có bảng)
# "25.000 đồng/m² mặt nước", "1,5 triệu đồng/con", "30 nghìn đồng/kg", "3.000.000 đ/hộ"
_RE_GIA_VAN = re.compile(
    r'(?P<so>\d{1,3}(?:[.,]\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(?P<boi>triệu|trieu|nghìn|nghin|ngàn|ngan)?\s*(?:đồng|đ)(?![\w])'
    r'\s*(?:\([^)]{0,40}\)\s*)?/\s*(?:01\s+|1\s+)?(?P<dvt>[^\s;,.()]+'
    r'(?:\s+(?:mặt\s+nước|nuôi|thả\s+nuôi|ao|lồng|bè|sàn|năm|tháng|yến(?:\s+thô)?))?)',
    re.I)
_RE_KHOANG = re.compile(r'(?i)(?:từ|tu)\s+[\d.,]+\s*(?:triệu|nghìn|ngàn)?\s*(?:đồng|đ)?\s*(?:đến|tới|-|–)\s*$')
# "1." / "1.1." là ký hiệu khoản; "50.000.000 đồng…" (dòng PDF bắt đầu bằng số tiền) thì không: sau dấu chấm không được là chữ số
_RE_DAU_KHOAN = re.compile(r'^\s*(?:(?P<dieu>Điều\s+\d+[a-zđ]?\.?)|(?P<so>\d+(?:\.\d+)*\.)(?!\d)|(?P<chu>[a-zđ]\))|'
                           r'(?P<gach>[-+•–*]))\s*', re.I)
# cụm đầu / cuối tên không mang nghĩa: "Đơn giá bồi thường đối với ...", "Giá trị và đơn giá bồi thường đối với ...",
# "Bồi thường thiệt hại ngừng sản xuất đối với ...", "... là", "mức hỗ trợ bằng", "... nhưng không quá"
_RE_DAU_TEN = re.compile(r'(?i)^(?:(?:quy\s+định\s+)?(?:giá\s+trị\s+và\s+)?(?:đơn\s+giá|mức(?:\s+giá)?)'
                         r'(?:\s+(?:bồi\s+thường|hỗ\s+trợ|thiệt\s+hại))*(?:\s+(?:đối\s+với|cho|về|của))?\s+|'
                         r'(?:bồi\s+thường|hỗ\s+trợ)(?:\s+thiệt\s+hại)?(?:\s+(?:ngừng|ngưng)\s+sản\s+xuất)?\s+(?:đối\s+với|cho|về)\s+|'
                         r'(?:đối\s+với|trường\s+hợp|về)\s+)')
_RE_CUOI_TEN = re.compile(r'(?i)(?:\s*[:,]\s*|\s+(?:là|bằng|với\s+mức|ở\s+mức|tương\s+đương|được\s+bồi\s+thường|được\s+hỗ\s+trợ|'
                          r'được\s+tính|tính|mức|đơn\s+giá|(?:nhưng\s+)?không\s+(?:vượt\s+)?quá|tối\s+đa))+\s*$')
# giá trần: "theo giá thị trường nhưng không quá 18.500.000 đồng/kg" -> tên ghi "(theo giá thị trường, tối đa)"
_RE_TRAN = re.compile(r'(?i)(?:nhưng\s+)?(?:không\s+(?:vượt\s+)?quá|tối\s+đa)\s*$')
_RE_THI_TRUONG = re.compile(r'(?i)\s*theo\s+giá\s+thị\s+trường\s*$')
# điều kiện áp dụng đứng SAU số tiền: "… là 20.300.000 đồng/ha/vụ đối với thủy sản nuôi dưới 50% định mức…, 14.500.000 đồng/ha/vụ
# đối với thủy sản nuôi từ 50% đến 80%…" (QĐ 31/2025/QĐ-UBND) - mỗi mức giá một dòng "Tên (điều kiện)"
_RE_DIEU_KIEN = re.compile(r'(?i)^[\s,]*(?:đối\s+với|áp\s+dụng\s+(?:cho|đối\s+với)|khi|trường\s+hợp|nếu)\s+')
# câu mới bắt đầu giữa đoạn (Word / PDF ghép dòng tiêu đề khoản với câu ghi giá): "… cá nuôi lồng bè Đối với cá nuôi lồng bè là …"
_RE_CAU_MOI = re.compile(r'(?<=\S)\s+(?=(?:Đối\s+với|Trường\s+hợp|Riêng)\s)')
# chữ dẫn chung trước dấu ":" không làm tên nhóm: "Đối với các hình thức nuôi như: nuôi hàu…" (giữ tên nhóm của khoản)
_RE_DAN_CHUNG = re.compile(r'(?:\bnhu|\bgom|\bsau|\bbao gom)$')


def _bo_dau_khoan(x: str) -> tuple:
    """(cấp, chữ bỏ ký hiệu đầu khoản): Điều = 0, 1. = 1, 1.1. = 2, a) = 3, -/+ = 4; không có ký hiệu = 9."""
    m = _RE_DAU_KHOAN.match(x)
    if not m:
        return 9, x.strip()
    if m.group('dieu'):
        cap = 0
    elif m.group('so'):
        cap = m.group('so').count('.')
    elif m.group('chu'):
        cap = 3
    else:
        cap = 4
    return cap, x[m.end():].strip()


def _ten_gon(x: str) -> str:
    x = ' '.join(x.split()).strip(' ;:,.')
    for _ in range(3):
        x = _RE_CUOI_TEN.sub('', _RE_DAU_TEN.sub('', x)).strip(' ;:,.')
    return x[:1].upper() + x[1:] if x else ''


def _la_tieu_de(x: str) -> bool:
    """Khoản không ghi giá, ngắn, không có dấu kết câu: tiêu đề cho các khoản bên dưới (Word không có dấu ":" cuối tiêu đề -
    "1. Bồi thường thiệt hại ngừng sản xuất đối với ao nuôi cá")."""
    return len(x) <= 160 and not x.endswith(('.', ';', ',')) and not _RE_GIA_VAN.search(x)


def _ket_cau(s: str, tu: int = 0) -> int:
    """Vị trí ngay sau dấu kết câu đầu tiên của s (từ vị trí tu): dấu ; hoặc dấu . đứng trước chữ hoa / cuối chuỗi
    ("50.000" không phải kết câu). Không có -> len(s)."""
    for m in re.finditer(r'[;.]', s[tu:]):
        i = tu + m.end()
        sau = s[i:].lstrip()
        if m.group() == ';' or not sau or sau[0].isupper():
            return i
    return len(s)


def _cau_cuoi(s: str) -> str:
    """Vế câu cuối của s (sau dấu ; hoặc dấu . kết câu)."""
    tu = 0
    while True:
        i = _ket_cau(s, tu)
        if i >= len(s):
            return s[tu:]
        tu = i


def _dieu_kien(sau: str) -> tuple:
    """Điều kiện áp dụng đứng ngay sau số tiền ("đối với thủy sản nuôi dưới 50% định mức…") -> (điều kiện gọn, số ký tự của sau
    đã dùng). Hết điều kiện ở dấu kết câu, hoặc ở dấu phẩy mà phần sau là tên mục mới (", nuôi cua là …")."""
    m = _RE_DIEU_KIEN.match(sau)
    if not m:
        return '', 0
    het = _ket_cau(sau, m.end())
    for p in re.finditer(',', sau[m.end():het]):
        i = m.end() + p.start()
        if re.search(r'(?i)(?:\s(?:là|bằng)|:)\s*$', sau[i + 1:het]):
            het = i
            break
    dk = ' '.join(sau[m.end():het].split()).strip(' ,;.')
    dk = re.sub(r'(?i)định\s+mức\s+kinh\s+tế\s*-?\s*kỹ\s+thuật', 'định mức KT-KT', dk)
    dk = re.sub(r'(?i)thời\s+gian\s+nuôi\s+trồng\s+(?:thủy|thuỷ)\s+sản', 'thời gian nuôi', dk)
    dk = re.sub(r'(?i)^(?:thủy|thuỷ)\s+sản\s+(?=nuôi\b)', '', dk)          # "thủy sản nuôi dưới 50%…" -> "nuôi dưới 50%…"
    return dk, het


def _khoan_van(dong: list) -> list:
    """Dòng chữ (đoạn Word / dòng PDF bị ngắt giữa câu) -> các khoản: ghép dòng nối tiếp, tách ở đầu khoản (Điều, 1., a), -),
    sau dấu ; hoặc : cuối dòng, và sau dòng tiêu đề khoản khi dòng kế bắt đầu bằng chữ hoa (đoạn Word riêng)."""
    kq, dang = [], ''
    for r in dong:
        x = r if isinstance(r, str) else (r[0] if len(r) == 1 else '')
        x = ' '.join(str(x or '').split())
        if not x:
            continue
        if dang and (_RE_DAU_KHOAN.match(x) or dang.endswith((';', ':', '.')) or
                     (x[:1].isupper() and _RE_DAU_KHOAN.match(dang) and _la_tieu_de(dang))):
            kq.append(dang)
            dang = x
        else:
            dang = f'{dang} {x}'.strip()
    if dang:
        kq.append(dang)
    return kq


def muc_tu_loi_van(dong: list, nhom: int = 0) -> tuple:
    """Văn bản không có bảng giá (đơn giá viết trong điều khoản, như QĐ 31/2025/QĐ-UBND vật nuôi): tìm các cụm "<số> đồng/<ĐVT>"
    trong từng khoản; tên mục = chữ đứng trước số tiền (bỏ "Đơn giá bồi thường đối với…", "… là"), dòng tiêu đề khoản phía trên
    (không giá: kết thúc ":" hoặc khoản ngắn không dấu kết câu) làm tên nhóm "Tiêu đề - Mục"; điều kiện đứng sau số tiền
    ("… đối với thủy sản nuôi dưới 50%…") ghi trong ngoặc, các mức giá nối tiếp cùng câu dùng lại tên. Trả ([Muc], [câu cần xem
    lại: khoảng giá "từ… đến…", tỷ lệ %, không ra tên]). Người dùng đối chiếu từng dòng trên HopNhapDonGia trước khi áp dụng
    (câu gốc ở Muc.nguon_dong)."""
    ds, xem, tieu_de = [], [], {}
    for khoan in _khoan_van(dong):
        cap, than = _bo_dau_khoan(khoan)
        if cap == 0:
            tieu_de.clear()
        gia = list(_RE_GIA_VAN.finditer(than))
        if not gia and re.search(r'\d\s*%', than) and re.search(r'(?i)bồi\s+thường|hỗ\s+trợ', than):
            xem.append(f'Quy định theo tỷ lệ % (không phải đơn giá - phần mềm không tự đổi cách tính): {khoan[:250]}')
        if not gia:
            if than.endswith(':') or cap == 0 or (cap in (1, 2, 3) and _la_tieu_de(than)):   # tiêu đề cho các khoản bên dưới
                for k in [k for k in tieu_de if k >= cap]:
                    del tieu_de[k]
                t = _ten_gon(re.sub(r'(?i)^(?:quy\s+định\s+)?', '', than))
                if t and len(t) <= 160:
                    tieu_de[cap] = t
            continue
        cha = next((tieu_de[k] for k in sorted(tieu_de, reverse=True) if k < cap), '')
        pos, goc = 0, None            # goc: (tên nhóm, tên, ghi chú) của mức giá trước - mức giá nối tiếp dùng lại
        for j, m in enumerate(gia):
            truoc = than[pos:m.start()]
            dk, dung = _dieu_kien(than[m.end():gia[j + 1].start() if j + 1 < len(gia) else len(than)])
            pos = m.end() + dung      # điều kiện của mức giá này không làm tên cho mức giá sau
            if _RE_KHOANG.search(truoc):
                xem.append(f'Khoảng giá (không tự lấy): {khoan[:250]}')
                continue
            boi = (m.group('boi') or '').lower()
            so = m.group('so')
            if boi:
                g = D(so.replace('.', '').replace(',', '.')) * (1000000 if boi.startswith('tri') else 1000)
                g = int(g) if g == int(g) else None
            else:
                g = doc_gia(so)
            if not g:
                continue
            if goc and not re.sub(r'(?i)\b(?:và|hoặc)\b|[\s,;]', '', truoc):
                cha_m, ten, ghi = goc[0], goc[1], list(goc[2])   # "…, 14.500.000 đồng/ha/vụ đối với …": cùng tên, khác điều kiện
            else:
                # tên: phần chữ ngay trước số tiền trong cùng vế câu (sau dấu ; / dấu chấm kết câu). "Đối với nuôi tôm: tôm thẻ
                # 60.000 đồng/m²" - phần trước ":" là tiêu đề trong dòng, dùng cho cả các giá sau trong khoản
                ve = _bo_dau_khoan(_cau_cuoi(truoc))[1]
                moi = list(_RE_CAU_MOI.finditer(ve))
                if moi:                                 # "<tiêu đề khoản> Đối với cá nuôi lồng bè là …" (dòng PDF ghép)
                    cha = _ten_gon(ve[:moi[-1].start()]) or cha
                    ve = ve[moi[-1].end():]
                tran = bool(_RE_TRAN.search(ve.strip(' ,;:')))
                if ':' in ve:
                    trai, phai = ve.rsplit(':', 1)
                    if _ten_gon(phai):
                        t = _ten_gon(_bo_dau_khoan(trai)[1])
                        if t and not _RE_DAN_CHUNG.search(bo_dau(t)):    # "Đối với các hình thức nuôi như:" giữ tên nhóm
                            cha = t
                        ve = phai
                    else:
                        ve = trai
                ten, ghi = _ten_gon(ve), []
                if tran:                                # giá trần: "theo giá thị trường nhưng không quá …"
                    mt = _RE_THI_TRUONG.search(ten)
                    if mt:
                        ten = ten[:mt.start()]
                    ghi.append('theo giá thị trường, tối đa' if mt else 'tối đa')
                cha_m = cha
                if len(ten) < 2:
                    ten, cha_m = cha, ''
                if not ten:
                    xem.append(f'Có số tiền nhưng không rõ tên mục: {khoan[:250]}')
                    continue
                goc = (cha_m, ten, tuple(ghi))
            if dk:
                ghi.append(dk)
            ten_day = f'{cha_m} - {ten}' if cha_m and bo_dau(cha_m) not in bo_dau(ten) else ten
            if ghi:
                ten_day += f' ({"; ".join(ghi)})'
            dvt = ' '.join(m.group('dvt').split())
            ds.append(Muc(ten_day[:200], dvt, g, '', khoan[:300], nhom=nhom or _nhom_dong(ten_day, dvt)))
    return ds, xem


# ---------------------------------------------------------------- so khớp với bộ đơn giá đang dùng
def _khoa(ten: str) -> str:
    return ' '.join(re.sub(r'[^\w ]', ' ', bo_dau(ten)).split())


def _khoa_gon(ten: str) -> str:
    """Khóa tên bỏ phần trong ngoặc: "Năm thu hoạch thứ 1-5 (Năm thứ 4,5,6,7,8)" ~ "Năm thu hoạch thứ 1 - 5"."""
    return _khoa(re.sub(r'\([^)]*\)', ' ', ten))


GAN_DUNG = 0.9          # tên giống >= 90% (cùng ĐVT) thì coi là cùng mục; hiện "gần đúng" để người dùng xem lại


def _giong_tung_phan(a: str, b: str) -> bool:
    """Tên gần đúng phải giống cả phần ngoài ngoặc lẫn phần trong ngoặc (>= GAN_DUNG): điều kiện dài trong ngoặc giống hệt nhau
    làm cả tên giống 93% dù là mục khác ("Ao nuôi tôm nước lợ - Nuôi quảng canh (nuôi dưới 50% định mức…)" ~ "Ao nuôi tôm
    nước ngọt - Nuôi thâm canh (nuôi dưới 50% định mức…)") - ghép nhầm sẽ ghi đè giá của mục khác."""
    import difflib

    def ngoac(s):
        return _khoa(' '.join(re.findall(r'\(([^)]*)\)', s)))
    return all(difflib.SequenceMatcher(None, x, y).ratio() >= GAN_DUNG
               for x, y in ((_khoa_gon(a), _khoa_gon(b)), (ngoac(a), ngoac(b))))


_NHO_GAN = {}


def so_khop(ds: list, nhom: int | None = None) -> list:
    """So với bộ đơn giá đang dùng: theo mã, tên (không dấu), rồi tên gần đúng cùng ĐVT. nhom None / 0: mỗi dòng theo
    nhóm của dòng (Muc.nhom); có nhom thì cả bảng theo nhóm đó."""
    import difflib
    f = don_gia.file_dang_dung()
    try:
        ban = (str(f), os.path.getmtime(f), os.path.getsize(f))   # bộ đơn giá đổi (cập nhật) -> khóa nhớ khác
    except OSError:
        ban = (str(f), 0, 0)
    con = csdl.mo(f, chi_doc=True)
    try:
        hien = {4: [dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia FROM dm_hotro')]}
        for n in (2, 3):
            hien[n] = [dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia, phan_loai FROM dm_taisan WHERE nhom = ?', (n,))]
        # vật nuôi (nhóm 7 khi phân tích): các dòng nhóm 3 có mã VN / phân loại vật nuôi - nhóm 3 vẫn gồm cả hai (giữ cách khớp cũ)
        from .nghiep_vu import la_vat_nuoi
        hien[NHOM_VN] = [x for x in hien[3] if str(x['ma']).upper().startswith('VN') or la_vat_nuoi(x['phan_loai'])]
    finally:
        con.close()
    bang = {}
    for n, ds_ in hien.items():
        theo_dvt, gon = {}, {}
        for x in ds_:
            theo_dvt.setdefault(bo_dau(x['dvt'] or ''), {})[_khoa(x['ten'])] = x
            gon.setdefault(_khoa_gon(x['ten']), []).append(x)
        gon = {k: v[0] for k, v in gon.items() if len(v) == 1}       # bỏ ngoặc mà trùng nhiều mục: không dùng
        bang[n] = ({x['ma'].upper(): x for x in ds_}, {_khoa(x['ten']): x for x in ds_}, theo_dvt, gon)
    for m in ds:
        n = nhom or m.nhom or 3
        theo_ma, theo_ten, theo_dvt, gon = bang[n]
        r = theo_ma.get(m.ma.upper()) if m.ma else None
        r = r or theo_ten.get(_khoa(m.ten))
        if r is None:
            x = gon.get(_khoa_gon(m.ten))
            r = x if x is not None and bo_dau(x['dvt'] or '') == bo_dau(m.dvt) else None
        m.khop_gan = 0.0
        if r is None:
            k, dv = _khoa(m.ten), bo_dau(m.dvt)
            cung = theo_dvt.get(dv, {})
            # khớp gần đúng (difflib, so với hàng nghìn tên): nhớ theo bộ đơn giá + nhóm + ĐVT + tên - đổi nhóm, sửa một ô rồi
            # so lại cả bảng không phải tính lại các dòng cũ
            kn = (ban, n, dv, m.ten)
            if kn not in _NHO_GAN:
                gan = None
                for g in difflib.get_close_matches(k, list(cung), n=3, cutoff=GAN_DUNG):
                    if _giong_tung_phan(m.ten, cung[g]['ten']):
                        gan = (g, difflib.SequenceMatcher(None, k, g).ratio())
                        break
                if len(_NHO_GAN) > 50000:
                    _NHO_GAN.clear()
                _NHO_GAN[kn] = gan
            if _NHO_GAN[kn] is not None and _NHO_GAN[kn][0] in cung:
                r, m.khop_gan = cung[_NHO_GAN[kn][0]], _NHO_GAN[kn][1]
        if r is None:
            m.trang_thai, m.ma_khop, m.gia_cu = 'mới', '', None
        else:
            m.ma_khop = r['ma']
            m.gia_cu = doc_gia(r['don_gia']) if r['don_gia'] not in (None, '') else None
            m.trang_thai = 'giữ nguyên' if m.gia_cu == m.don_gia else 'cập nhật'
    return ds


def _phan_loai_dang_dung(con, vat_nuoi: bool, nhom: int) -> str:
    """Chuỗi phân loại bộ đơn giá đang dùng nhiều nhất cho nhóm (vật nuôi / không) - mục mới cùng phân loại với mục cũ, không tách
    thành nhóm lạ trên các thẻ / bảng in. Bộ chưa có dòng nào: mặc định."""
    from .nghiep_vu import la_vat_nuoi
    dem = {}
    for pl, n in con.execute('SELECT phan_loai, COUNT(*) FROM dm_taisan WHERE nhom = ? GROUP BY phan_loai', (nhom,)):
        if pl and bool(la_vat_nuoi(pl)) == vat_nuoi:
            dem[pl] = n
    if dem:
        return max(dem, key=dem.get)
    return don_gia.PHAN_LOAI_VAT_NUOI if vat_nuoi else PHAN_LOAI_MAC_DINH.get(nhom, '')


def _phan_loai(con, nm: int, ten: str, van_ban: dict | None) -> str:
    """Phân loại dòng mới của dm_taisan theo ĐÚNG chuỗi bộ đơn giá đang dùng (trước 15/10/2026 ghi "2. Nhà, công trình xây dựng" /
    "3. Cây trồng, vật nuôi" - lệch với phân loại của bộ). Nhóm 7 (vật nuôi) hoặc nhóm 3 mà tên / trích yếu văn bản chỉ nói vật
    nuôi, thủy sản -> phân loại vật nuôi (thẻ "Vật nuôi" của Bộ đơn giá)."""
    if nm == NHOM_VN:
        return _phan_loai_dang_dung(con, True, 3)
    if nm == 3:
        vb = bo_dau((van_ban or {}).get('trich_yeu', ''))
        if re.search(r'vat nuoi|thuy san|chan nuoi|chim yen', bo_dau(ten)) or \
                (re.search(r'vat nuoi|thuy san', vb) and not re.search(r'cay trong|hoa mau', vb)):
            return _phan_loai_dang_dung(con, True, 3)
    return _phan_loai_dang_dung(con, False, nm)


def ap_dung(ds: list, nhom: int | None, nguon: str, phien_ban: str = '', van_ban: dict | None = None) -> dict:
    """Tạo bộ đơn giá mới (bộ đang dùng + các mục được chọn) và cài. Trả thông tin bộ mới + số mục.
    nhom None / 0: mỗi dòng theo Muc.nhom. van_ban: kết quả phan_tich_van_ban (ghi vào danh mục văn bản căn cứ)."""
    chon = [m for m in ds if m.chon and m.trang_thai in ('mới', 'cập nhật')]
    if not chon and not (van_ban and van_ban.get('so_hieu')):
        raise LoiNhap('Không có mục nào mới hoặc đổi giá để cập nhật.')
    # không có dòng giá nhưng có văn bản (văn bản chính sách): chỉ ghi vào danh mục văn bản căn cứ để theo dõi
    goc = don_gia.file_dang_dung()
    tt_cu = don_gia.thong_tin(goc)
    with tempfile.TemporaryDirectory() as td:
        moi = Path(td) / don_gia.TEN_FILE
        shutil.copyfile(goc, moi)
        con = csdl.mo(moi)
        try:
            pb = phien_ban or datetime.now().strftime('%Y.%m.%d.%H%M')
            if pb <= tt_cu['phien_ban']:
                pb = tt_cu['phien_ban'] + '.1'
            so = {'mới': 0, 'cập nhật': 0}
            theo_nhom = {}
            with con, csdl.mo_khoa_danh_muc(con):
                # mã mục mới theo quy ước 0.9.69 (ma_tai_san): CS (hỗ trợ), TS (nhà), CT (cây), VN (vật nuôi) - số tiếp theo
                from .ma_tai_san import doi_ma, ma_tiep, tien_to
                from .nghiep_vu import la_vat_nuoi
                da_cap = {}
                for m in chon:
                    nm = nhom or m.nhom or 3
                    if m.trang_thai == 'cập nhật':
                        bang = 'dm_hotro' if nm == 4 else 'dm_taisan'
                        con.execute(f'UPDATE {bang} SET don_gia = ? WHERE ma = ?', (chuoi(m.don_gia), m.ma_khop))
                    elif nm == 4:
                        ma = doi_ma(m.ma, 4) if m.ma else ma_tiep(con, 'dm_hotro', 'CS', da_cap)
                        con.execute('INSERT INTO dm_hotro (ma, ten, dvt, don_gia, can_cu, trang_thai) VALUES (?,?,?,?,?,?)',
                                    (ma, m.ten, m.dvt, chuoi(m.don_gia), nguon, 'Cập nhật từ file'))
                    else:
                        nhom_db = 3 if nm == NHOM_VN else nm          # vật nuôi: nhom 3 + phân loại vật nuôi (CSDL không có nhom 7)
                        pl = _phan_loai(con, nm, m.ten, van_ban)
                        vn = nhom_db == 3 and la_vat_nuoi(pl)
                        ma = doi_ma(m.ma, nhom_db, vn) if m.ma else ma_tiep(con, 'dm_taisan', tien_to(nhom_db, vn), da_cap)
                        con.execute('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) VALUES (?,?,?,?,?,?,?)',
                                    (ma, nhom_db, pl, m.ten, m.dvt, chuoi(m.don_gia), f'Cập nhật từ {nguon}'))
                    so[m.trang_thai] += 1
                    theo_nhom.setdefault(nm, {'mới': 0, 'cập nhật': 0})[m.trang_thai] += 1
                tom_tat = '; '.join(f'{NHOM[k]}: {v["mới"]} mục mới, {v["cập nhật"]} mục đổi giá'
                                    for k, v in sorted(theo_nhom.items())) or 'Văn bản chính sách: cần đối chiếu quy tắc tính'
                vb = van_ban or {}
                so_hieu = vb.get('so_hieu') and ' '.join(x for x in (vb.get('loai_vb', ''), vb['so_hieu'],
                                                                      f'ngày {vb["ngay"]}' if vb.get('ngay') else '') if x)
                trang_thai = f'Cập nhật {datetime.now():%d/%m/%Y}' + (f' từ {nguon}' if so_hieu else '')
                k = chuan_so_hieu(vb.get('so_hieu', ''))
                cu = next((r for r in con.execute('SELECT id, noi_dung, so_hieu FROM van_ban').fetchall()
                           if k and re.search(r'(?<!\d)' + re.escape(k), chuan_so_hieu(r[2]))), None)
                if cu is not None:                      # văn bản đã có tên trong danh sách: cập nhật dòng đó, không thêm dòng trùng
                    con.execute('UPDATE van_ban SET noi_dung = ?, trang_thai = ? WHERE id = ?',
                                (' | '.join(x for x in (cu[1], tom_tat) if x), trang_thai, cu[0]))
                else:
                    con.execute('INSERT INTO van_ban (so_hieu, co_quan, noi_dung, trang_thai) VALUES (?,?,?,?)',
                                (so_hieu or f'Cập nhật đơn giá từ {nguon}', vb.get('co_quan', ''),
                                 (vb.get('trich_yeu', '') + ' - ' if vb.get('trich_yeu') else '') + tom_tat, trang_thai))
                con.execute('UPDATE du_an SET phien_ban_gia = ?, nguon_nhap = ?, ngay_nhap = ? WHERE id = 1',
                            (pb, nguon, datetime.now().isoformat(timespec='seconds')))
        finally:
            con.close()
        tt = don_gia.cai_bo(moi)
    return dict(tt, so_moi=so['mới'], so_cap_nhat=so['cập nhật'], theo_nhom=theo_nhom)
