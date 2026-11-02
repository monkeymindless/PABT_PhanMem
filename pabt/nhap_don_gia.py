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
from .tien import D, chuoi, lam_tron

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
_DVT_GOC = (r'm²\s*sàn|m2\s*sàn|(?:m|mét)\s*/\s*sợi|m²|m2|m³|m3|md|mét|met|m|cây|cay|bụi|bui|khóm|hố|ha|kg|cái|chiếc|bộ|hộ|'
            r'khẩu|nhân khẩu|tháng|ngôi|mộ|con|đơn vị|lần|ô|gốc|trụ|cánh|sợi|lít|tấm|bồn')
# ĐVT trong dòng chữ (bản scan đọc theo dòng): "mét", "trụ", "cánh", "Đồng/m2" (bảng ghi đơn giá kèm "đồng/<đơn vị>") - 02/11/2026
DVT = rf'(?:(?:đồng|đ)\s*/\s*)?(?:{_DVT_GOC})'


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
    ghi_chu: str = ''             # quy cách văn bản ghi kèm (mật độ của loài cây: "Mật độ 1.111 cây/ha")
    ten_cu: str = ''              # tên / ghi chú mục đang khớp trong bộ đơn giá (so_khop)
    ghi_chu_cu: str = ''
    ten_thay: str = ''            # chế độ thay thế: tên / ghi chú sẽ ghi vào mục cũ theo cách ghi của văn bản mới ('' = không đổi)
    ghi_chu_thay: str = ''
    bo_cu: bool = False           # dòng do so_khop thêm: mục cũ cùng nhóm không còn trong văn bản (chế độ thay thế)
    nhom_loai: str = ''           # cây lâm nghiệp: khóa nhóm loài của bảng giá theo nhóm ('quy hiem', '1'…'8'; khoa_nhom_loai)
    duong_kinh: str = ''          # "(d >6-9 cm)" - cỡ đường kính của dòng bảng giá theo nhóm / dòng đã tách theo loài
    ten_loai: str = ''            # dòng đã tách theo loài: tên loài (không tên khác) - so khớp với bộ đơn giá
    ma_moi: str = ''              # mã sẽ cấp cho mục mới (so_khop; ap_dung dùng đúng mã này)
    cha: str = ''                 # dòng cha (không giá) của dòng con "- …" - nhận dòng chung nhiều tài sản (chu_the_chung)
    muc_gia: str = ''             # ô giá ghi khoảng "a - b": 'thap' / 'cao' (hai mục cùng tên, mục cao có dấu chấm cuối tên)
    khoang: str = ''              # chữ khoảng giá gốc "259.000 - 720.000"
    cach_khop: str = ''           # cách so_khop đã khớp ngoài tên: 'đặc trưng', 'dòng chung', 'khoảng giá: mức thấp' / 'mức cao'
    phu: bool = False             # dòng so_khop thêm cho dòng chung (một giá cho nhiều mục) - so lại thì bỏ


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


def chuyen_office(p, loai: str = '', thu_muc=None) -> Path:
    """File Word / Excel 97-2003 (.doc / .xls) -> .docx / .xlsx cạnh file gốc (hoặc trong thu_muc), nhờ Microsoft Word / Excel trên
    máy. Excel mở xong lưu lại nên công thức được tính lại (file .xlsx tạo bằng công cụ khác chưa có giá trị đã lưu)."""
    p = Path(p).resolve()
    loai = loai or loai_that(p) or p.suffix.lower()
    dich = (Path(thu_muc) if thu_muc else p.parent) / (p.stem + ('_chuyen.docx' if loai == '.doc' else '_chuyen.xlsx'))
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
    """Như doc_bang; PDF ảnh scan thì nhận dạng chữ bằng Tesseract đóng kèm - cột bảng (khoảng trống rộng, ocr.gom_dong nối bằng
    Tab) tách thành ô như bảng Excel (16/10/2026: trước đây mỗi dòng một ô - STT dính vào tên, dòng ĐVT đọc lệch bị bỏ); dòng không
    có cột (đoạn văn) một ô, đọc theo mẫu '<tên> <ĐVT> <đơn giá>'. bao_tien_do(trang, tổng), cho() -> True để hủy (ocr.DaHuy)."""
    try:
        return doc_bang(file)
    except LoiPdfScan as e:
        from . import ocr
        thieu = ocr.san_sang()
        if thieu:
            raise LoiPdfScan(f'{e}\n\n{thieu}') from None
        try:
            return dong_tu_chu('\n'.join(ocr.doc_chu(file, bao_tien_do, cho)))
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
    return int(g) if g > 0 and g == int(g) else (int(lam_tron(g)) if g >= 1000 else None)


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


def chuan_dvt(d: str) -> str:
    """ĐVT theo cách ghi của bộ đơn giá: "Đồng/m2" -> "m²", "mét" -> "m", "mét/sợi" -> "m/sợi", "m3" -> "m³"."""
    d = ' '.join(str(d or '').split())
    d = re.sub(r'(?i)^(?:đồng|đ)\s*/\s*', '', d)
    d = re.sub(r'(?i)^m[ée]t\b', 'm', d)
    d = re.sub(r'(?i)\bm2\b', 'm²', re.sub(r'(?i)\bm3\b', 'm³', d))
    return re.sub(r'\s*/\s*', '/', d)


def _dvt_khoa(d: str) -> str:
    return bo_dau(chuan_dvt(d)).replace(' ', '')


def doc_khoang_gia(o) -> tuple | None:
    """Ô giá ghi khoảng "259.000 - 720.000" -> (259000, 720000) (thấp < cao); không phải khoảng giá -> None."""
    m = re.fullmatch(r'\s*(\d[\d.,]*)\s*(?:đồng|đ)?\s*[-–—]\s*(\d[\d.,]*)\s*(?:đồng|đ)?\s*', str(o or ''))
    if not m:
        return None
    a, b = doc_gia(m.group(1)), doc_gia(m.group(2))
    return (a, b) if a and b and a < b and a >= GIA_TOI_THIEU else None


GIA_TOI_THIEU = 500      # đơn giá đọc theo dòng chữ nhỏ hơn mức này là số khác ("ngày 25 tháng 10") - không phải tiền
_RE_QUY_TAC = re.compile(r'\d\s*%|phan tram|tinh them|duoc tinh|tinh bang|xac dinh (?:theo|nhu sau)|bang \d+ ?%|'
                         r'tro di duoc|duoc ap dung|ap dung (?:muc|don gia)|khong (?:vuot qua|tinh)')


def la_quy_tac(chu: str) -> bool:
    """Dòng không có đơn giá là QUY ĐỊNH CÁCH TÍNH ("Giếng sâu từ 10m trở lên thì mét thứ 10 trở đi được tính thêm 50% mức giá trên",
    "Đơn giá gác lửng bằng 40% đơn giá…", "xác định theo loại kết cấu nhà có…") - không phải dòng cha / mục đơn giá."""
    return bool(_RE_QUY_TAC.search(bo_dau(chu)))


_RE_MAT_DO_TEN = re.compile(r'(?i)\s*\(\s*(?:m[ậa]t\s*[đd][ộo](?:\s+chu[ẩa]n)?\s*:?\s*)?(?:(\d[\d.,]*)\s*(cây|cay|khóm|khom|bụi|bui|'
                            r'hố|ho|gốc|goc)\s*/\s*ha|[^)]*)\s*\)')
_LA_MA_SO = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}


def khoa_nhom_loai(chu: str) -> str:
    """Khóa nhóm loài cây lâm nghiệp trong bảng giá / danh sách loài: "Nhóm quý hiếm gồm 45 loài", "Bảng 1: Nhóm loài cây quý hiếm"
    -> 'quy hiem'; "Nhóm I gồm 13 loài", "Bảng 4: Loài cây nhóm III", "nhóm 4" -> '1' / '3' / '4'. Không nhận ra: ''."""
    k = ' '.join(bo_dau(chu or '').lower().split())
    if 'quy hiem' in k:
        return 'quy hiem'
    m = re.search(r'\bnhom\s+(?:loai\s+)?([ivx]+|\d+)\b', k)
    if not m:
        # bản scan: số La Mã đọc sai ("nhóm IJI", "nhóm Il", "nhóm 1V") - j / l / 1 / | thay chữ I
        m = re.search(r'\bnhom\s+(?:loai\s+)?([ivxjl1|]+)(?![\w])', k)
        if not m or not re.search(r'[ivx]', m.group(1)):
            return ''
        g = re.sub(r'[jl1|]', 'i', m.group(1))
        return str(_LA_MA_SO[g]) if g in _LA_MA_SO else ''
    g = m.group(1)
    return str(int(g)) if g.isdigit() else str(_LA_MA_SO.get(g, '')) if g in _LA_MA_SO else ''


def chuan_duong_kinh(chu: str) -> str:
    """Ô cỡ đường kính thân -> phần tên như bộ đơn giá: "≤3" -> "(d ≤3 cm)", ">3 - 6" -> "(d >3-6 cm)", "> 42" -> "(d >42 cm)"; ô
    không có số: ''."""
    s = ' '.join(str(chu or '').replace('–', '-').split())
    m = re.search(r'(<=|>=|[<>≤≥])?\s*(\d+(?:[.,]\d+)?)\s*(?:cm)?\s*(?:-\s*(\d+(?:[.,]\d+)?))?', s)
    if not m:
        return ''
    dau = {'<=': '≤', '>=': '≥'}.get(m.group(1), m.group(1) or '')
    return f'(d {dau}{m.group(2)}{"-" + m.group(3) if m.group(3) else ""} cm)'


def doc_nhom_loai(dong: list) -> dict:
    """Danh sách loài theo nhóm (Phụ lục VI của văn bản cây lâm nghiệp): dòng "Bảng k: Loài cây nhóm III" / "Bảng 1: Nhóm loài cây quý
    hiếm" rồi bảng có cột "Tên Việt Nam" (+ "Tên Việt Nam khác") -> {khóa nhóm: [(tên loài, (tên khác…))]}."""
    kq, khoa, ten_c, khac_c = {}, '', None, None
    for r in dong:
        o = [' '.join(bo_dau(c).lower().split()) for c in r]
        chu = ' '.join(x for x in o if x)
        if re.search(r'\bbang\s*\d+\b', chu) and 'nhom' in chu and sum(1 for x in o if x) <= 2:
            khoa, ten_c, khac_c = khoa_nhom_loai(chu), None, None
            continue
        if not khoa:
            continue
        tc = _cot(o, r'^ten viet nam$', r'^ten (loai|cay|viet)(?! nam khac)')
        if tc is not None and not any(re.fullmatch(r'\d+', x) for x in o):
            ten_c, khac_c = tc, _cot(o, r'^ten (viet nam )?khac', r'ten viet nam khac')
            continue
        if ten_c is None or ten_c >= len(r):
            continue
        ten = ' '.join(r[ten_c].split()).strip(' .;')
        if not ten or re.fullmatch(r'[\d\W]+', ten):
            continue
        khac = r[khac_c] if khac_c is not None and khac_c < len(r) else ''
        ds_khac = tuple(x.strip() for x in re.split(r'[.;,]\s*', khac) if x.strip())
        kq.setdefault(khoa, []).append((ten, ds_khac))
    return kq


def _loai_trong_bo(dm_nhom3: list) -> dict:
    """Bộ đơn giá đang dùng: {tên loài (không tên khác): {khóa cỡ đường kính: dòng}} của các dòng "Loài (…) (d …)"."""
    from .ten_cay_lam_nghiep import bo_ten_khac
    kq = {}
    for x in dm_nhom3:
        m = re.search(r'\(\s*d\b[^)]*\)\s*$', x['ten'])
        if not m:
            continue
        loai = bo_ten_khac(x['ten'])[:].rsplit('(', 1)[0].strip()
        kq.setdefault(loai, {})[_khoa(m.group(0))] = x
    return kq


NGUONG_SUA_TEN_LOAI = 0.72         # độ giống (bỏ dấu, SequenceMatcher) tối thiểu để sửa tên loài đọc sai về tên loài đã biết


def sua_ten_loai(ten: str, khac: tuple, biet: dict) -> tuple:
    """Tên loài đọc từ bản scan (OCR hay sai dấu / sai chữ: "Câmlai", "Bò'i lời giấy") -> (tên đúng, tên khác). biet = {tên loài đã
    biết: (tên khác)} - danh sách Phụ lục VI gắn sẵn (ten_cay_lam_nghiep.TEN_KHAC) + loài trong bộ đơn giá đang dùng. Tên trùng hẳn
    (bỏ dấu) giữ nguyên; giống >= NGUONG_SUA_TEN_LOAI (cộng điểm tên khác giống nhau) thì lấy tên đã biết; không thì giữ chữ đọc được."""
    from difflib import SequenceMatcher

    def k(x):
        return ' '.join(re.sub(r"[^\w ]+", ' ', bo_dau(x).lower()).split())
    kt = k(ten)
    if not kt:
        return ten, khac
    for t in biet:
        if k(t) == kt:
            return t, biet[t] or khac
    kk = k(' '.join(khac))
    tot, diem = None, 0.0
    for t, tk in biet.items():
        d = SequenceMatcher(None, kt, k(t)).ratio()
        if kk and tk:
            d = max(d, 0.6 * d + 0.4 * SequenceMatcher(None, kk, k(' '.join(tk))).ratio())
        if d > diem:
            tot, diem = t, d
    if tot is not None and diem >= NGUONG_SUA_TEN_LOAI:
        return tot, biet[tot]
    return ten, khac


def tach_theo_loai(ds: list, nhom_loai: dict | None = None) -> tuple:
    """Dòng bảng giá theo NHÓM loài cây lâm nghiệp ("Nhóm IV gồm … loài" x cỡ đường kính) -> mỗi loài trong nhóm một dòng mỗi cỡ:
    "Bồ đề (d >6-9 cm)", "Trường (…) (d >6-9 cm)"… (người dùng 30/10/2026: "tách từng loại cây"). Loài của nhóm: danh sách trong văn
    bản (doc_nhom_loai - Phụ lục VI); văn bản không có danh sách thì suy từ bộ đơn giá đang dùng: các loài có ĐÚNG bảng giá theo cỡ của
    nhóm (giá không đổi). Trả (ds mới, [nhóm không tách được])."""
    nhom_loai = nhom_loai or {}
    theo_nhom = {}
    for m in ds:
        if m.nhom_loai:
            theo_nhom.setdefault(m.nhom_loai, []).append(m)
    if not theo_nhom:
        return ds, []
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        bo = _loai_trong_bo([dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia FROM dm_taisan WHERE nhom = 3 ORDER BY rowid')])
    finally:
        con.close()
    from .ten_cay_lam_nghiep import TEN_KHAC, ten_khac
    biet = {t: ten_khac(t) for t in bo}
    biet.update(TEN_KHAC)
    loai_nhom, khong = {}, []
    for k, dong in theo_nhom.items():
        if nhom_loai.get(k):
            ds_loai = []
            for t, khac in nhom_loai[k]:
                t, khac = sua_ten_loai(t, khac, biet)       # 30/10/2026: tên loài bản scan đọc sai -> tên đã biết
                ds_loai.append((t, khac or ten_khac(t)))
            loai_nhom[k] = ds_loai
            continue
        gia = {_khoa(m.duong_kinh): m.don_gia for m in dong}
        cung = [loai for loai, co in (bo or {}).items()
                if set(co) == set(gia) and all(doc_gia(co[c]['don_gia']) == g for c, g in gia.items())]
        if cung:
            loai_nhom[k] = [(t, ten_khac(t)) for t in cung]
        else:
            khong.append(dong[0].ten.rsplit('(', 1)[0].strip())
    kq = []
    for m in ds:
        ds_loai = loai_nhom.get(m.nhom_loai) if m.nhom_loai else None
        if not ds_loai:
            kq.append(m)
            continue
        for t, khac in ds_loai:
            ten = f'{t} ({", ".join(khac)}) {m.duong_kinh}' if khac else f'{t} {m.duong_kinh}'
            kq.append(Muc(ten, m.dvt, m.don_gia, '', m.nguon_dong, nhom=m.nhom, ghi_chu=m.ghi_chu, duong_kinh=m.duong_kinh,
                          ten_loai=t))
    # thứ tự như bộ đơn giá: từng loài đủ các cỡ đường kính (văn bản ghi từng nhóm theo cỡ)
    vt = {id(m): i for i, m in enumerate(kq)}
    dau = {}
    for m in kq:
        if m.ten_loai:
            dau.setdefault(m.ten_loai, vt[id(m)])
    kq.sort(key=lambda m: (dau[m.ten_loai], vt[id(m)]) if m.ten_loai else (vt[id(m)], 0))
    return kq, khong


def tach_mat_do_ten(ten: str) -> tuple:
    """"Cây cam (Mật độ 1.111 cây/ha)" / "Cây vải thiều (330 cây/ha)" -> ("Cây cam", "Mật độ 1.111 cây/ha"). Ngoặc khác giữ trong
    tên ("Cây mận (roi) (Mật độ 493 cây/ha)" -> "Cây mận (roi)"). Không có mật độ: (tên, '')."""
    for m in _RE_MAT_DO_TEN.finditer(ten):
        if m.group(1) or re.match(r'(?i)\s*\(\s*m[ậa]t\s*[đd][ộo]', m.group(0)):
            so, dv = m.group(1), m.group(2)
            gc = f'Mật độ {so} {dv}/ha' if so else ' '.join(m.group(0).strip(' ()').split())
            return ' '.join((ten[:m.start()] + ' ' + ten[m.end():]).split()), gc
    return ten, ''


_RE_STT_DONG = re.compile(r'^(?:(?P<stt>\d{1,3}[a-z]?|[IVXL]{1,5})[.)]?\s+(?=\S)|(?P<chu>[a-zđ])[.)]\s+|(?P<ma>[A-Z]{1,3}\d+)\s+)')
_RE_GACH = re.compile(r'^[-–—+•*]+\s*')
# "<tên> <ĐVT> <giá>" / "<tên> <ĐVT> <giá thấp> - <giá cao>" (ĐVT có thể kèm "đồng/": "Đồng/m2 581.000")
_RE_DONG_GIA = re.compile(rf'^(?P<ten>.+?)\s+(?P<dvt>{DVT})\s+(?P<g1>\d[\d.,]*)(?:\s*[-–—]\s*(?P<g2>\d[\d.,]*))?\s*(?:đồng|đ)?\.?$',
                          re.I)
# không có ĐVT: giá phải có dấu ngăn nghìn ("Hồ chứa … 259.000 - 576.000")
_RE_DONG_GIA_TRON = re.compile(r'^(?P<ten>.+?)\s+(?P<g1>\d{1,3}(?:[.,]\d{3})+)(?:\s*[-–—]\s*(?P<g2>\d{1,3}(?:[.,]\d{3})+))?\s*'
                               r'(?:đồng|đ)?\.?$')
_RE_DVT_CUOI = re.compile(rf'\s+(?:{DVT})$', re.I)
_RE_TIEU_DE_VB = re.compile(r'^(?:\(?\s*ban hanh kem theo|phu luc\b|quyet dinh so|dieu \d|chuong\b|(?:stt|tt)\b.*(?:ten|don gia)|'
                            r'ten (?:tai san|cay|cong trinh).*don gia)')
_RE_TIEU_DE_NHOM = re.compile(r'^(?:nhom|phan|muc|phu luc)\b')


def _tieu_de_van_ban(chu: str) -> bool:
    """Dòng chữ ngoài bảng giá: tiêu đề phụ lục / điều / dòng tiêu đề cột / chữ IN HOA - không làm dòng cha của mục giá."""
    k = bo_dau(chu).strip()
    chu_cai = [c for c in chu if c.isalpha()]
    return bool(_RE_TIEU_DE_VB.match(k)) or (len(chu_cai) >= 6 and all(c.isupper() for c in chu_cai)) or len(chu) > 220


class _DocDong:
    """Đọc từng DÒNG CHỮ (bản scan đọc theo dòng, bảng dán không có tiêu đề cột, PDF có chữ không bảng) - 02/11/2026 (người dùng: văn
    bản hợp nhất đơn giá nhà, công trình; bản scan đọc mất tên dòng cha, khoảng giá "259.000 - 720.000", ĐVT "mét", "Đồng/m2").

    - Dòng không giá: dòng cha của các dòng con sau nó; dòng quy định cách tính ("…được tính thêm 50% mức giá trên") -> quy_tac;
      dòng chữ thường / bắt đầu bằng số đo ("2,2 m") nối vào dòng trước (ô tên xuống dòng).
    - Dòng con: bắt đầu "-", "+", "•" hoặc chữ thường -> "Cha - Con"; dòng cha chưa kết thúc (dấu phẩy, chưa có dòng con) mà dòng
      sau chữ thường có giá -> cùng một tên (ô tên xuống dòng, giá nằm giữa ô).
    - STT ô gộp dọc nằm giữa nhóm (bản scan đặt số vào dòng giữa): dòng có STT không cắt nhóm khi dòng cha không có STT và đứng sau
      STT gần nhất.
    - Khoảng giá "a - b": hai mục cùng tên - mức cao tên có dấu chấm cuối (quy ước của bộ đơn giá: "Mái che, mái hiên" / "Mái che,
      mái hiên.")."""

    def __init__(self, kq: list, nhom: int, quy_tac: list | None):
        self.kq, self.nhom, self.quy_tac = kq, nhom, quy_tac
        self.nhom_muc = 0
        self.cuoi = None                  # ('muc', [Muc]) / ('cha',) / ('th',) / ('qt', i)
        self.duoi = ''                    # dấu phẩy / chấm phẩy cuối tên mục vừa đọc (ô tên xuống dòng: nối giữ dấu)
        self._bo_cha()

    def _bo_cha(self):
        self.cha = self.th = self.cha_ket = self.kieu_con = self.mat_do = self.cha_ngu_canh = ''
        self.so_con = 0
        self.cha_sau_stt = False

    def _ghi_quy_tac(self, chu: str, ngu_canh: str = ''):
        if self.quy_tac is None:
            self.cuoi = None
            return
        self.quy_tac.append(f'{ngu_canh}: {chu}' if ngu_canh else chu)
        self.cuoi = ('qt', len(self.quy_tac) - 1)

    def doc(self, s: str):
        s = ' '.join(str(s or '').split())
        if not s:
            return
        stt = ma = ''
        m = _RE_STT_DONG.match(s)
        if m and len(s) > m.end():
            stt, ma = m.group('stt') or m.group('chu') or '', m.group('ma') or ''
            s = s[m.end():]
        gach = bool(_RE_GACH.match(s))
        than = _RE_GACH.sub('', s).strip()
        if not than:
            return
        mg = _RE_DONG_GIA.match(than) or _RE_DONG_GIA_TRON.match(than)
        g1 = g2 = None
        if mg:
            if mg.group('g2'):
                k = doc_khoang_gia(f"{mg.group('g1')} - {mg.group('g2')}")
                g1, g2 = k if k else (None, None)
            else:
                g1 = doc_gia(mg.group('g1'))
            if g1 is not None and g1 < GIA_TOI_THIEU:
                g1 = None
        if g1 and mg.group('ten').rstrip().endswith(':'):      # lời văn "Cá thịt: 45.000" (ĐVT ở dòng sau) - không phải dòng bảng
            g1 = None
        ten = mg.group('ten').strip(' -–:;,') if g1 else ''
        self.duoi = (re.search(r'[,;]\s*$', mg.group('ten')) or [''])[0].strip() if g1 else ''
        if not g1 or not ten or re.fullmatch(r'[\d\W]+', ten):
            self._khong_gia(than, stt, gach)
            return
        dvt = chuan_dvt(mg.groupdict().get('dvt') or '')
        thuong = ten[:1].islower()
        con = gach or thuong
        if self.cha:
            if stt and not self.cha_sau_stt:
                giu = False
            else:
                giu = con or self.so_con == 0 or self.kieu_con == 'tron'
            if not giu:
                self._bo_cha()
        if stt:
            self.cha_sau_stt = False
        cha_cua, gc = '', ''
        if self.cha:
            if thuong and not gach and self.so_con == 0 and self.cha_ket not in (':', ')'):
                ten = f'{self.cha} {ten}'                           # dòng cha xuống dòng: cùng một mục
                gc = self.mat_do
                self._bo_cha()
            else:
                cha_cua, gc = self.cha, self.mat_do
                ten = ' - '.join(x for x in (self.cha, self.th, ten) if x)
                self.so_con += 1
                self.kieu_con = self.kieu_con or ('gach' if con else 'tron')
        else:
            ten, gc = tach_mat_do_ten(ten)
        self._them(ten, dvt, g1, g2, ma, s, cha_cua, gc,
                   f"{mg.group('g1')} - {mg.group('g2')}" if g2 else '')

    def _them(self, ten, dvt, g1, g2, ma, nguon, cha, gc, khoang):
        nh = self.nhom or self.nhom_muc or _nhom_dong(ten, dvt)
        if g2:
            ds = [Muc(ten, dvt, g1, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha, muc_gia='thap', khoang=khoang),
                  Muc(ten + '.', dvt, g2, '', nguon, nhom=nh, ghi_chu=gc, cha=cha, muc_gia='cao', khoang=khoang)]
        else:
            ds = [Muc(ten, dvt, g1, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha)]
        self.kq.extend(ds)
        self.cuoi = ('muc', ds)

    def _khong_gia(self, than: str, stt: str, gach: bool):
        noi = not stt and not gach and (than[:1].islower() or re.match(r'\d+(?:[.,]\d+)?\s*(?:m|cm|mm|m²|m³|mét)\b', than))
        if not noi:
            than = _RE_DVT_CUOI.sub('', than).strip()      # dòng hướng dẫn ghi kèm ĐVT ("… mức giá trên mét")
        if not than:
            return
        k = bo_dau(than)
        if _tieu_de_van_ban(than) or _LA_MA.match(stt) or (not stt and _RE_TIEU_DE_NHOM.match(k)):
            if _LA_MA.match(stt) or _RE_TIEU_DE_NHOM.match(k):
                self.nhom_muc = nhom_theo_chu(than) or self.nhom_muc
            self._bo_cha()
            self.cuoi = None
            return
        if noi and self.cuoi:                               # ô tên xuống dòng: nối vào dòng trước
            loai = self.cuoi[0]
            if loai == 'muc':
                for x in self.cuoi[1]:
                    goc = x.ten[:-1] if x.muc_gia == 'cao' else x.ten
                    x.ten = f'{goc}{self.duoi} {than.rstrip(" .;:")}' + ('.' if x.muc_gia == 'cao' else '')
                    x.nguon_dong += ' ' + than
                self.duoi = ''
                return
            if loai == 'qt':
                self.quy_tac[self.cuoi[1]] += ' ' + than
                return
            if loai == 'th':
                self.th = f'{self.th} {than}'.strip(' .;:')
                return
            self.cha = f'{self.cha} {than}'
            self.cha_ket = than.rstrip()[-1:]
            self.cha, self.mat_do = tach_mat_do_ten(self.cha.rstrip(' .;:'))
            if la_quy_tac(self.cha):                        # câu hướng dẫn xuống dòng, không phải dòng cha
                c, ngu = self.cha, self.cha_ngu_canh
                self._bo_cha()
                self._ghi_quy_tac(c, ngu)
            return
        if re.fullmatch(r'[\d\W]+', than):                  # mẩu số / dấu lạc (STT, số trang)
            return
        muc_truoc = self.cuoi[1][0].ten if self.cuoi and self.cuoi[0] == 'muc' else ''
        if la_quy_tac(than):
            ngu = muc_truoc if gach else self.cha
            self._ghi_quy_tac(than.rstrip(' ;'), ngu)
            return
        if gach and self.cha:
            self.th = than.rstrip(' .;:')
            self.cuoi = ('th',)
            return
        self._bo_cha()
        self.cha, self.mat_do = tach_mat_do_ten(than.rstrip(' .;:'))
        self.cha_ket = than.rstrip()[-1:]
        self.cha_sau_stt = not stt
        self.cha_ngu_canh = muc_truoc if gach else ''      # dòng gạch đầu dòng sau mục: có thể là câu hướng dẫn của mục đó
        self.cuoi = ('cha',)


def nhan_muc(dong: list, nhom: int = 0, quy_tac: list | None = None) -> list:
    """Dòng bảng -> các mục đơn giá. Có dòng tiêu đề (Tên, ĐVT, Đơn giá) thì theo cột; không có thì đọc từng dòng chữ (_DocDong:
    '<mã> <tên> <ĐVT> <đơn giá>', dòng cha / dòng con, khoảng giá).

    Bảng phân cấp như văn bản UBND: dòng nhóm (I, II...) không có giá; dòng mục (1, 2...) không có giá là "cha" của các dòng
    con (-, +, a)...) -> tên "Cha - Con" như bộ đơn giá; dòng '*' là trường hợp chen giữa; ô giá có nhãn
    ("Đông Xuân: 24.880.000") -> "Tên (Đông Xuân)"; ô giá khoảng "a - b" -> hai mục (mức cao: tên có dấu chấm cuối); dòng tên trống
    tiếp tục mục ngay trên. nhom: nhóm mặc định (theo văn bản). quy_tac: danh sách nhận các dòng quy định cách tính không có giá."""
    kq, tieu_de, nhan = [], None, 1
    cha = truong_hop = truoc = dvt_mac_dinh = mat_do = mat_do_bang = nhom_dk = ''
    nhom_muc = 0
    doc_dong = _DocDong(kq, nhom, quy_tac)
    for r in dong:
        o = [bo_dau(c) for c in r]
        ten_c = _cot(o, r'^(ten|loai|noi dung|hang muc|danh muc|tai san|cay trong|nhom loai)', r'\bten (tai san|cay|cong trinh|khoan)')
        gia_c = _cot(o, r'^(don gia|gia|muc (ho tro|boi thuong)|muc gia)', r'don gia')
        if ten_c is not None and gia_c is not None and ten_c != gia_c:
            dvt_c = _cot(o, r'^(dvt|don vi)', r'don vi tinh')
            ma_c = _cot(o, r'^(ma|ma so|ma ts|ma ho tro|ky hieu)$')
            stt_c = _cot(o, r'^(stt|tt|so tt|so thu tu)$')
            # bảng giá cây lâm nghiệp theo nhóm loài x cỡ đường kính (bản scan hay dính chữ: "Đườngkính")
            dk_c = _cot(o, r'^duong ?kinh', r'^(d|dk|co)\s*\(?cm\)?$')
            if dk_c in (ten_c, gia_c):
                dk_c = None
            tieu_de = (ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c)
            nhan = 1000 if any(re.search(r'nghin|1\.?000 ?d', x) for x in o) else 1
            # bảng không có cột ĐVT, đơn vị ghi ở tiêu đề cột giá: "Đơn giá bồi thường (đồng/ha)"
            md = re.search(r'(?i)(?:đồng|đ)\s*/\s*([^)]+)\)', r[gia_c])
            dvt_mac_dinh = md.group(1).strip() if md else ''
            # mật độ ghi ở tiêu đề cột tên: "Nhóm loài cây gỗ trồng trên cạn (mật độ chuẩn 833 cây/ha)"
            mat_do_bang = tach_mat_do_ten(' '.join(r[ten_c].split()))[1]
            cha = truong_hop = truoc = nhom_dk = ''
            doc_dong._bo_cha()
            continue
        if tieu_de and len(r) >= 2:
            ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c = tieu_de
            r = list(r) + [''] * (max(c for c in tieu_de if c is not None) + 1 - len(r))   # ô gộp: hàng ít ô hơn tiêu đề
            stt = r[stt_c].strip() if stt_c is not None else ''
            ten = ' '.join(r[ten_c].split()).rstrip(' .;:')
            gach = bool(_RE_GACH.match(ten)) and not _CON.match(ten)
            if gach:                                        # dòng con ghi gạch đầu dòng trong ô tên ("- Ống 1 m Φ1m")
                ten = _RE_GACH.sub('', ten)
            g, nhan_gia = _tach_gia(r[gia_c])
            khoang = doc_khoang_gia(r[gia_c]) if not g else None
            dk = chuan_duong_kinh(r[dk_c]) if dk_c is not None else ''
            if dk_c is not None and (ten or dk):
                # bảng nhóm loài: ô nhóm gộp nhiều hàng (chỉ hàng đầu có chữ) - các hàng sau là cỡ đường kính của nhóm đó
                # bản scan: ô nhóm gộp vắt sang trang sau còn mẩu chữ đọc sai ("nem", "Ị") ở hàng cỡ tiếp theo (">27-30") - vẫn là
                # nhóm cũ; nhóm mới bắt đầu ở cỡ nhỏ nhất ("<3", "≤2") hoặc tên có chữ "Nhóm …"
                if ten and not re.fullmatch(r'[\d\W]+', ten) and \
                        (not nhom_dk or not dk or khoa_nhom_loai(ten) or re.match(r'\(d [<≤]', dk) or len(ten) > 12):
                    nhom_dk = ten
                if dk and g and nhom_dk:
                    ten_nhom = ' '.join(re.sub(r'\([^)]*(?:danh s[áa]ch|ph[ụu] l[ụu]c)[^)]*\)', ' ', nhom_dk).split())
                    dvt = (r[dvt_c].strip() if dvt_c is not None else '') or dvt_mac_dinh or 'cây'
                    dvt = chuan_dvt(dvt)
                    kq.append(Muc(f'{ten_nhom} {dk}', dvt, g * nhan, '', ' | '.join(c for c in r if c), nhom=nhom or 3,
                                  ghi_chu=mat_do_bang, nhom_loai=khoa_nhom_loai(nhom_dk), duong_kinh=dk))
                    continue
                if not g:
                    continue
            if not g and not khoang:
                if not ten:
                    continue
                if la_quy_tac(ten):                         # "- Giếng sâu từ 10m trở lên thì … tính thêm 50% mức giá trên"
                    if quy_tac is not None:
                        quy_tac.append(f'{truoc}: {ten}' if truoc and gach else ten)
                    continue
                if _LA_MA.match(stt) or (not stt and re.match(r'(?i)^(nhom|phan|muc|phu luc)\b', bo_dau(ten))):
                    nhom_muc = nhom_theo_chu(ten) or nhom_muc        # tiêu đề nhóm
                    cha = truong_hop = truoc = ''
                elif not stt and not gach and ten[:1].islower() and kq and truoc and kq[-1].ten.startswith(truoc):
                    for x in kq[-2 if kq[-1].muc_gia == 'cao' else -1:]:   # ô tên xuống dòng thành hàng riêng: nối vào mục trên
                        x.ten = f'{x.ten[:-1]} {ten}.' if x.muc_gia == 'cao' else f'{x.ten} {ten}'
                    truoc = f'{truoc} {ten}'
                elif stt.startswith('*'):
                    truong_hop = ten
                elif (_CON.match(stt) or gach) and cha:
                    truong_hop = ten                                # dòng con không giá: thêm một cấp
                else:
                    # mật độ ghi ở ghi chú danh mục, không ở tên: "Cây bưởi (Mật độ 210 cây/ha)" / "Cây vải thiều (330 cây/ha)"
                    # -> "Cây bưởi" + ghi chú "Mật độ 210 cây/ha" cho các dòng con
                    cha, mat_do = tach_mat_do_ten(ten)
                    truong_hop = ''
                continue
            gc, cha_cua = '', ''
            if not ten:                                             # tiếp tục mục ngay trên (ô tên gộp)
                ten, gc = truoc, mat_do if cha else ''
            elif _CON.match(stt) or stt.startswith('*') or (not stt and cha) or ((gach or ten[:1].islower()) and cha):
                # dòng con (STT -, a)... hoặc để trống; ô tên có gạch đầu dòng / chữ thường - kể cả khi bản scan đặt STT ô gộp vào dòng con)
                cha_cua = cha
                ten = ' - '.join(x for x in (cha, truong_hop, ten) if x)
                gc = mat_do if cha else ''
            else:
                cha = truong_hop = mat_do = ''
                ten, gc = tach_mat_do_ten(ten)
            truoc = ten
            if not ten or re.fullmatch(r'[\d\W]+', ten):
                continue
            ten_day = f'{ten} ({nhan_gia})' if nhan_gia else ten
            dvt = chuan_dvt((r[dvt_c].strip() if dvt_c is not None else '') or dvt_mac_dinh)    # "đồng/bụi" -> "bụi"
            ma = r[ma_c].strip() if ma_c is not None else ''
            nh = nhom or nhom_muc or _nhom_dong(ten_day, dvt)
            nguon = ' | '.join(c for c in r if c)
            if khoang:
                kq.append(Muc(ten_day, dvt, khoang[0] * nhan, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha_cua, muc_gia='thap',
                              khoang=' '.join(r[gia_c].split())))
                kq.append(Muc(ten_day + '.', dvt, khoang[1] * nhan, '', nguon, nhom=nh, ghi_chu=gc, cha=cha_cua, muc_gia='cao',
                              khoang=' '.join(r[gia_c].split())))
            else:
                kq.append(Muc(ten_day, dvt, g * nhan, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha_cua))
            continue
        if len(r) == 1 or not tieu_de:                    # dòng chữ (PDF / Word không bảng, bản scan đọc theo dòng, bảng dán)
            doc_dong.doc(' '.join(str(c) for c in r if str(c or '').strip()))
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


def _khoa_quy_cach(ten: str) -> str:
    """Khóa gọn thêm bỏ chữ "thứ" trước số: "Năm 1" (bộ đơn giá cũ) ~ "Năm thứ 1" (văn bản mới), "Năm thu hoạch thứ 1-3 (Năm thứ
    3,4,5)" ~ "Năm thu hoạch thứ 1 - 3"."""
    return ' '.join(re.sub(r'\bthu (?=\d)', '', _khoa_gon(ten)).split())


def ten_thay_the(ten_moi: str, ten_cu: str) -> str:
    """Tên ghi vào mục cũ khi thay thế: ĐÚNG cách ghi của văn bản mới. 30/10/2026 (người dùng: văn bản không có chú thích "(Năm thứ
    3, 4, 5)"): không còn giữ chú thích quy đổi tuổi của tên cũ - năm tuổi tính theo cấu trúc (hieu_tai_san.bang_tuoi)."""
    return ten_moi


_RE_GHI_CHU_VAN_BAN_CU = re.compile(r'quyet dinh|nghi quyet|\bqd\b|/qd|\bsua doi\b|\bbo sung\b|cap nhat tu')


def ghi_chu_thay_the(gc_cu: str, gc_moi: str, ten_moi: str) -> str:
    """Ghi chú mục cũ khi văn bản mới thay thế văn bản cũ: mật độ theo văn bản mới (bỏ mật độ cũ), bỏ ghi chú thuộc văn bản cũ ("Sửa
    đổi, bổ sung tại Quyết định số 66/2025…", "Cập nhật từ …") và đoạn trùng chữ trong ngoặc của tên mới (bộ cũ từng ghi "roi" của
    "Cây mận (roi)" vào ghi chú); ghi chú khác giữ."""
    ngoac = {_khoa(x) for x in re.findall(r'\(([^)]*)\)', ten_moi)}
    giu = []
    for d in (gc_cu or '').split(';'):
        d = d.strip()
        k = bo_dau(d)
        if not d or _khoa(d) in ngoac or (gc_moi and k.startswith('mat do')) or _RE_GHI_CHU_VAN_BAN_CU.search(k):
            continue
        giu.append(d)
    return '; '.join(([gc_moi] if gc_moi else []) + giu)


NHOM_PHAM_VI = {2: 'nhà, công trình, vật kiến trúc', 3: 'cây trồng', NHOM_VN: 'vật nuôi, thủy sản', 4: 'chính sách hỗ trợ'}
# từ khóa nhận văn bản cũ của nhóm trong danh sách văn bản căn cứ (đoán sẵn văn bản bị thay thế)
_TU_NHOM_VB = {2: r'nha, cong trinh|nha va cong trinh|cong trinh xay dung|vat kien truc', 3: r'cay trong|hoa mau',
               NHOM_VN: r'vat nuoi|thuy san', 4: r'ho tro|tai dinh cu'}


def van_ban_cu_cua_nhom(nhom_ds: set) -> list:
    """[(id, số hiệu, nội dung)] văn bản trong danh sách văn bản căn cứ của bộ đơn giá đang dùng có nội dung về nhóm (để chọn văn bản
    bị thay thế). Bỏ văn bản sửa đổi / dự thảo / đã hết hiệu lực."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        ds = con.execute('SELECT id, so_hieu, noi_dung, trang_thai FROM van_ban ORDER BY id').fetchall()
    finally:
        con.close()
    mau = '|'.join(_TU_NHOM_VB[n] for n in sorted(nhom_ds) if n in _TU_NHOM_VB)
    kq = []
    for i, sh, nd, tt in ds:
        k = bo_dau(f'{sh} {nd}')
        if mau and re.search(mau, k) and not re.search(r'du thao|het hieu luc|^sua doi', bo_dau(f'{nd} {tt}')) \
                and re.search(r'quyet dinh|\bqd\b', bo_dau(sh)):
            kq.append((i, sh, nd))
    return kq


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


NGUONG_KHOP_THEO_GIA = 0.55        # tên giống tối thiểu khi khớp theo đơn giá trùng (so_khop, bước sau cùng)

# ---------------------------------------------------------------- so khớp theo ĐẶC TRƯNG (02/11/2026)
# Văn bản ghi tên khác bộ đơn giá ("Giếng thả ống ciment (kể cả lắp đặt) - Ống 1 m Φ1,2 m" ~ "Giếng thả ống ciment Φ1,2m (ống 1m)" +
# ghi chú "Kể cả lắp đặt"): so cỡ Φ / D, số đo có đơn vị, vật liệu kết cấu chính, ĐVT và các từ - không so chuỗi tên.
_RE_PHI = re.compile(r'[φϕø∅®©]\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?(?![\w²³])')
_RE_D_ONG = re.compile(r'\bd\s?(\d{2,3})\b')
_TU_BO = frozenset('va cac loai co cua bang ke ca thi tu tro len duoc the khac tai san hoac mot cho theo tren duoi voi la gom ket '
                   'cau kem trong so m mm cm'.split())
NGUONG_PHU = 0.6        # tỷ lệ từ của tên văn bản có trong mục (tên + ghi chú) tối thiểu
NGUONG_PHU_MUC = 0.5    # tỷ lệ từ của tên mục có trong tên văn bản tối thiểu (0,3 khi cùng cỡ Φ)
CACH_DAC_TRUNG, CACH_DONG_CHUNG = 'đặc trưng', 'dòng chung'
CACH_THAP, CACH_CAO = 'khoảng giá: mức thấp', 'khoảng giá: mức cao'


def _chuoi_so(v) -> str:
    return str(int(v)) if v == int(v) else format(v.normalize(), 'f')


def _ket_cau_chinh(k: str) -> str:
    """Vật liệu kết cấu chính (chữ không dấu): 'kct' bê tông không cốt thép, 'ct' cốt thép / BTCT, 'xay' xây gạch, xây đá, 'bt' bê
    tông (không nói cốt thép); '' không rõ. Hai tên cùng có mà khác nhau -> hai mục khác nhau."""
    if re.search(r'khong (?:co )?cot thep', k):
        return 'kct'
    if re.search(r'cot thep|\bbtct\b', k):
        return 'ct'
    if re.search(r'xay gach|gach xay|xay da|\bxay\b', k):
        return 'xay'
    if 'be tong' in k:
        return 'bt'
    return ''


def dac_trung(ten: str) -> tuple:
    """(cỡ Φ / D quy về mm, số đo có đơn vị {'1m', '10cm'}, kết cấu chính, số trơn, các từ) của một tên."""
    return _dac_trung(str(ten or ''))


def _dac_trung_goc(ten: str) -> tuple:
    from decimal import Decimal, InvalidOperation
    k = re.sub(r'\bmet\b', 'm', bo_dau(ten))
    phi = set()

    def lay(mt):
        try:
            v = Decimal(mt.group(1).replace(',', '.'))
        except InvalidOperation:
            return ' '
        dv = mt.group(2) or ''
        if dv == 'm' or (not dv and v < 10):            # "Φ0,8" (không đơn vị, nhỏ hơn 10) là mét; "Φ60" là mm
            v *= 1000
        elif dv == 'cm':
            v *= 10
        phi.add(_chuoi_so(v))
        return ' '
    k = _RE_PHI.sub(lay, k)
    k = _RE_D_ONG.sub(lambda mt: phi.add(str(int(mt.group(1)))) or ' ', k)
    k = re.sub(r'(\d)\s+(mm|cm|m)\b', r'\1\2', k)
    so_do = frozenset(re.findall(r'\d+(?:,\d+)?(?:mm|cm|m)\b', k))
    tu = [re.sub(r'^0+(?=\d)', '', t) for t in re.findall(r'[a-z0-9][a-z0-9,]*', k)]
    tu = frozenset(t.rstrip(',') for t in tu if t not in _TU_BO)
    so = frozenset(t for t in tu if re.fullmatch(r'[\d,]+', t))
    return frozenset(phi), so_do, _ket_cau_chinh(k), so, tu


try:
    from functools import lru_cache as _lru
    _dac_trung = _lru(maxsize=50000)(_dac_trung_goc)
except ImportError:                                      # pragma: no cover
    _dac_trung = _dac_trung_goc


def _cung_dvt(a: str, b: str) -> bool:
    return not a or not b or _dvt_khoa(a) == _dvt_khoa(b)


def diem_dac_trung(ten: str, dvt: str, x: dict) -> float | None:
    """Độ giống theo đặc trưng giữa tên văn bản và một mục bộ đơn giá (dict ten, dvt, ghi_chu); None = khác mục (khác ĐVT, khác cỡ Φ,
    số đo mâu thuẫn, khác kết cấu chính, khác số năm / số trơn, quá ít từ chung)."""
    if not _cung_dvt(dvt, x.get('dvt') or ''):
        return None
    p1, s1, c1, n1, w1 = dac_trung(ten)
    p2, s2, c2, n2, w2 = dac_trung(x['ten'])
    if p1 != p2 or (c1 and c2 and c1 != c2) or (s1 and s2 and not (s1 <= s2 or s2 <= s1)) or (n1 and n2 and n1 != n2):
        return None
    if not w1 or not w2:
        return None
    wg = w2 | dac_trung(x.get('ghi_chu') or '')[4]
    phu = len(w1 & wg) / len(w1)
    phu_x = len(w1 & w2) / len(w2)
    if phu < NGUONG_PHU or (phu_x < NGUONG_PHU_MUC and not (p1 and phu_x >= 0.3)):
        return None
    return round((phu + phu_x) / 2, 3)


def chu_the_chung(cha: str) -> tuple | None:
    """Dòng cha nêu NHIỀU tài sản dùng chung các mức giá con ("Trụ cổng, bờ kè và các loại tài sản khác có kết cấu:" + "- Bằng bê
    tông cốt thép …") -> ([chủ thể không dấu: 'tru cong', 'bo ke'], có "các loại … khác"); không phải -> None."""
    k = ' '.join(bo_dau(cha or '').split())
    if not k:
        return None
    khac = bool(re.search(r'cac loai\b.{0,40}\bkhac\b|\bva cac\b', k))
    dau = re.split(r'\b(?:va cac|cac loai|co ket cau|ket cau|bang)\b|[(:]', k)[0]
    chu_the = [s.strip() for s in re.split(r',|\bva\b|/', dau) if len(s.strip()) >= 3]
    if len(chu_the) >= 2 or (khac and chu_the):
        return chu_the, khac
    return None


def so_khop(ds: list, nhom: int | None = None, thay_the: bool = False) -> list:
    """So với bộ đơn giá đang dùng: theo mã, tên (không dấu), tên bỏ ngoặc, quy cách ("Năm 1" ~ "Năm thứ 1"), rồi tên gần đúng cùng
    ĐVT, rồi theo ĐẶC TRƯNG (cỡ Φ, số đo, kết cấu, ĐVT, từ - diem_dac_trung), rồi theo đơn giá trùng. nhom None / 0: mỗi dòng theo
    nhóm của dòng (Muc.nhom); có nhom thì cả bảng theo nhóm đó.

    Khoảng giá (Muc.muc_gia thap / cao): cặp mục cùng tên trong bộ (mục cao có dấu chấm cuối tên - quy ước của bộ đơn giá) - thấp
    gán mục thấp, cao gán mục cao; bộ chưa có cặp thì đề xuất mục mới (không chọn sẵn).
    Dòng chung (dòng cha chu_the_chung + dòng con có kết cấu): mỗi giá con cập nhật MỌI mục của các tài sản nêu ở dòng cha cùng kết
    cấu, cùng ĐVT; "các loại tài sản khác" thêm các mục liền khối cùng ĐVT đang cùng giá với nhóm đó - thêm dòng phụ (phu), không
    thêm mục mới.

    thay_the (30/10/2026, người dùng: "thay thế toàn bộ văn bản cũ bằng văn bản mới, để đúng với toàn bộ nội dung theo văn bản mới"):
    danh mục các nhóm có trong văn bản (cây trồng / nhà, công trình / vật nuôi / hỗ trợ) theo đúng văn bản - mục khớp có tên / mật độ /
    ghi chú khác văn bản -> ten_thay / ghi_chu_thay (giá không đổi: trạng thái 'đổi quy cách'); mục cũ CÙNG NHÓM không còn trong văn
    bản -> thêm dòng 'bỏ' (bo_cu, chọn sẵn). Cây trồng và vật nuôi cùng nhom 3 trong CSDL: văn bản cây trồng không bỏ vật nuôi."""
    import difflib
    ds[:] = [m for m in ds if not m.bo_cu and not m.phu]
    f = don_gia.file_dang_dung()
    try:
        ban = (str(f), os.path.getmtime(f), os.path.getsize(f))   # bộ đơn giá đổi (cập nhật) -> khóa nhớ khác
    except OSError:
        ban = (str(f), 0, 0)
    con = csdl.mo(f, chi_doc=True)
    try:
        hien = {4: [dict(r) for r in con.execute("SELECT ma, ten, dvt, don_gia, '' AS ghi_chu FROM dm_hotro")]}
        for n in (2, 3):
            hien[n] = [dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia, phan_loai, ghi_chu FROM dm_taisan WHERE nhom = ? '
                                                    'ORDER BY rowid', (n,))]
        # vật nuôi (nhóm 7 khi phân tích): các dòng nhóm 3 có mã VN / phân loại vật nuôi - nhóm 3 vẫn gồm cả hai (giữ cách khớp cũ)
        from .nghiep_vu import la_vat_nuoi
        hien[NHOM_VN] = [x for x in hien[3] if str(x['ma']).upper().startswith('VN') or la_vat_nuoi(x['phan_loai'])]
    finally:
        con.close()
    from .ten_cay_lam_nghiep import bo_ten_khac
    bang = {}
    for n, ds_ in hien.items():
        theo_dvt, gon, qc = {}, {}, {}
        for x in ds_:
            theo_dvt.setdefault(_dvt_khoa(x['dvt'] or ''), {})[_khoa(x['ten'])] = x
            gon.setdefault(_khoa_gon(x['ten']), []).append(x)
            qc.setdefault(_khoa_quy_cach(x['ten']), []).append(x)
        gon = {k: v[0] for k, v in gon.items() if len(v) == 1}       # bỏ ngoặc mà trùng nhiều mục: không dùng
        qc = {k: v[0] for k, v in qc.items() if len(v) == 1}
        theo_ten = {_khoa(x['ten']): x for x in ds_}
        for x in ds_:                   # 26/10/2026: tên cây lâm nghiệp có tên khác ("Bách xanh (Tùng hương) (d …)") vẫn khớp tên văn bản
            theo_ten.setdefault(_khoa(bo_ten_khac(x['ten'])), x)
        bang[n] = ({x['ma'].upper(): x for x in ds_}, theo_ten, theo_dvt, gon, qc)
    da_khop = set()
    chi_muc = {}                        # nhóm -> {từ: [vị trí mục]} - lọc ứng viên so theo đặc trưng

    def ung_vien(ten, dvt, n, bo_khop=True):
        """[(điểm, mục)] theo đặc trưng, điểm giảm dần."""
        if n not in chi_muc:
            cm = {}
            for i, x in enumerate(hien[n]):
                for t in dac_trung(x['ten'])[4] | dac_trung(x['ghi_chu'] or '')[4]:
                    cm.setdefault(t, []).append(i)
            chi_muc[n] = cm
        w = dac_trung(ten)[4]
        dem = {}
        for t in w:
            for i in chi_muc[n].get(t, ()):
                dem[i] = dem.get(i, 0) + 1
        can = NGUONG_PHU * len(w)
        kq = []
        for i, c in dem.items():
            x = hien[n][i]
            if c < can or (bo_khop and (n, x['ma']) in da_khop):
                continue
            d = diem_dac_trung(ten, dvt, x)
            if d is not None:
                kq.append((d, i, x))
        kq.sort(key=lambda t: (-t[0], t[1]))
        return [(d, x) for d, _, x in kq]

    def ghi_khop(m, r, n):
        m.ten_thay = m.ghi_chu_thay = ''
        if r is None:
            m.trang_thai, m.ma_khop, m.gia_cu, m.ten_cu, m.ghi_chu_cu = 'mới', '', None, '', ''
            return
        m.ma_khop, m.ten_cu, m.ghi_chu_cu = r['ma'], r['ten'], r['ghi_chu'] or ''
        da_khop.add((n, r['ma']))
        m.gia_cu = doc_gia(r['don_gia']) if r['don_gia'] not in (None, '') else None
        m.trang_thai = 'giữ nguyên' if m.gia_cu == m.don_gia else 'cập nhật'
        if thay_the and m.cach_khop != CACH_DONG_CHUNG:   # dòng chung: tên văn bản là của cả nhóm tài sản - giữ tên từng mục
            ten = ten_thay_the(m.ten, r['ten'])
            gc = ghi_chu_thay_the(m.ghi_chu_cu, m.ghi_chu, ten) if n != 4 else ''
            if ten != r['ten'] or (n != 4 and gc != m.ghi_chu_cu):
                m.ten_thay, m.ghi_chu_thay = ten, gc
                if m.trang_thai == 'giữ nguyên':
                    m.trang_thai = 'đổi quy cách'
    xong = set()
    for m in ds:
        m.khop_gan, m.cach_khop = 0.0, ''
    # 1. khoảng giá "a - b": cặp mục cùng tên (mục cao có dấu chấm cuối tên)
    for i in range(len(ds) - 1):
        a, b = ds[i], ds[i + 1]
        if a.muc_gia != 'thap' or b.muc_gia != 'cao' or id(a) in xong:
            continue
        n = nhom or a.nhom or 3
        k = _khoa(a.ten)
        cap = [x for x in hien[n] if _khoa(x['ten']) == k and _cung_dvt(a.dvt, x['dvt'] or '') and (n, x['ma']) not in da_khop]
        diem = 0.0
        if not cap:
            uv = ung_vien(a.ten, a.dvt, n)
            if uv:
                diem, k0 = uv[0][0], _khoa(uv[0][1]['ten'])
                cap = [x for d, x in uv if _khoa(x['ten']) == k0 and d >= diem - 0.001]
        cap.sort(key=lambda x: (x['ten'].rstrip().endswith('.'), doc_gia(x['don_gia']) or 0))
        if len(cap) == 1 and cap[0]['ten'].rstrip().endswith('.'):
            cap = [None, cap[0]]
        for m, x, cach in ((a, cap[0] if cap else None, CACH_THAP), (b, cap[1] if len(cap) > 1 else None, CACH_CAO)):
            m.cach_khop = cach
            ghi_khop(m, x, n)
            m.khop_gan = diem if x is not None else 0.0
            m.chon = x is not None                          # mục mới của khoảng giá: đề xuất, không chọn sẵn
            if x is None:
                m.ghi_chu = (f'{"Mức cao" if m is b else "Mức thấp"} của khoảng giá {a.khoang or ""} '
                             f'(mức {"thấp" if m is b else "cao"}: {(a if m is b else b).ten})').replace('  ', ' ')
            xong.add(id(m))
    # 2. dòng chung: giá con của dòng cha nêu nhiều tài sản -> mọi mục cùng kết cấu của các tài sản đó
    them_sau = {}
    nhom_cha = {}
    for m in ds:
        if m.cha and id(m) not in xong and chu_the_chung(m.cha):
            nhom_cha.setdefault((m.cha, nhom or m.nhom or 3), []).append(m)
    for (cha, n), con_ in nhom_cha.items():
        chu_the, khac = chu_the_chung(cha)
        gan = {}
        for m in con_:
            kc = _ket_cau_chinh(bo_dau(m.ten[len(cha):] if m.ten.startswith(cha) else m.ten))
            if not kc:
                continue
            gan[id(m)] = [x for x in hien[n] if (n, x['ma']) not in da_khop and _cung_dvt(m.dvt, x['dvt'] or '')
                          and _ket_cau_chinh(bo_dau(x['ten'])) == kc and any(bo_dau(x['ten']).startswith(s) for s in chu_the)]
        if not any(gan.values()):
            continue
        vt = {id(x): i for i, x in enumerate(hien[n])}
        if khac:                    # "các loại tài sản khác": mục liền khối cùng ĐVT, đang cùng giá với nhóm của một giá con
            theo_gia = {}
            for m in con_:
                for x in gan.get(id(m), ()):
                    theo_gia.setdefault(doc_gia(x['don_gia']), set()).add(id(m))
            theo_gia = {g: next(iter(v)) for g, v in theo_gia.items() if g and len(v) == 1}
            co = sorted(vt[id(x)] for v in gan.values() for x in v)
            if co and theo_gia:
                da = {id(x) for v in gan.values() for x in v}
                for buoc, j in ((1, co[-1] + 1), (-1, co[0] - 1)):
                    while 0 <= j < len(hien[n]):
                        x = hien[n][j]
                        g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else None
                        if (n, x['ma']) in da_khop or g not in theo_gia:
                            break
                        mm = next(m for m in con_ if id(m) == theo_gia[g])
                        if id(x) not in da and _cung_dvt(mm.dvt, x['dvt'] or ''):
                            gan[theo_gia[g]].append(x)
                            da.add(id(x))
                        j += buoc
                    # khối giữa các mục chủ thể (thứ tự bộ đơn giá xen kẽ)
                for j in range(co[0], co[-1] + 1):
                    x = hien[n][j]
                    g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else None
                    if id(x) not in da and g in theo_gia and (n, x['ma']) not in da_khop:
                        gan[theo_gia[g]].append(x)
                        da.add(id(x))
        for m in con_:
            ds_x = sorted(gan.get(id(m), ()), key=lambda x: vt[id(x)])
            if not ds_x:
                continue
            m.cach_khop = CACH_DONG_CHUNG
            ghi_khop(m, ds_x[0], n)
            xong.add(id(m))
            phu = []
            for x in ds_x[1:]:
                p = Muc(m.ten, m.dvt, m.don_gia, '', m.nguon_dong, nhom=m.nhom, cha=m.cha, phu=True, cach_khop=CACH_DONG_CHUNG,
                        chon=m.chon)
                ghi_khop(p, x, n)
                xong.add(id(p))
                phu.append(p)
            them_sau[id(m)] = phu
    if them_sau:
        ds[:] = [y for m in ds for y in [m] + them_sau.get(id(m), [])]
    # 3. mã, tên, quy cách, tên gần đúng
    for m in ds:
        if id(m) in xong:
            continue
        n = nhom or m.nhom or 3
        theo_ma, theo_ten, theo_dvt, gon, qc = bang[n]
        r = theo_ma.get(m.ma.upper()) if m.ma else None
        r = r or theo_ten.get(_khoa(m.ten))
        if r is None and m.ten_loai:                    # dòng tách theo loài: tên khác của văn bản ghi khác bộ đơn giá
            r = theo_ten.get(_khoa(f'{m.ten_loai} {m.duong_kinh}'))
        for khoa_, bang_ in ((_khoa_gon, gon), (_khoa_quy_cach, qc)):
            if r is None:
                x = bang_.get(khoa_(m.ten))
                r = x if x is not None and _dvt_khoa(x['dvt'] or '') == _dvt_khoa(m.dvt) else None
        if r is None:
            k, dv = _khoa(m.ten), _dvt_khoa(m.dvt)
            cung = theo_dvt.get(dv, {})
            # khớp gần đúng (difflib, so với hàng nghìn tên): nhớ theo bộ đơn giá + nhóm + ĐVT + tên - đổi nhóm, sửa một ô rồi
            # so lại cả bảng không phải tính lại các dòng cũ
            kn = (ban, n, dv, m.ten)
            if kn not in _NHO_GAN:
                gan_ = None
                for g in difflib.get_close_matches(k, list(cung), n=3, cutoff=GAN_DUNG):
                    if _giong_tung_phan(m.ten, cung[g]['ten']):
                        gan_ = (g, difflib.SequenceMatcher(None, k, g).ratio())
                        break
                if len(_NHO_GAN) > 50000:
                    _NHO_GAN.clear()
                _NHO_GAN[kn] = gan_
            if _NHO_GAN[kn] is not None and _NHO_GAN[kn][0] in cung:
                r, m.khop_gan = cung[_NHO_GAN[kn][0]], _NHO_GAN[kn][1]
        ghi_khop(m, r, n)
    # 4. theo đặc trưng (02/11/2026): tên văn bản ghi khác bộ - cỡ Φ, số đo, kết cấu, ĐVT, từ; nhiều mục ngang điểm thì thôi (trừ khi
    # đơn giá trùng một mục)
    for m in ds:
        if id(m) in xong or m.trang_thai != 'mới':
            continue
        n = nhom or m.nhom or 3
        uv = ung_vien(m.ten, m.dvt, n)
        if not uv:
            continue
        cung_gia = [t for t in uv if t[0] >= uv[0][0] - 0.05 and doc_gia(t[1]['don_gia']) == m.don_gia]
        if len(uv) > 1 and uv[0][0] - uv[1][0] < 0.05:
            if len(cung_gia) != 1:
                continue
            uv = cung_gia
        m.cach_khop = CACH_DAC_TRUNG
        ghi_khop(m, uv[0][1], n)
        m.khop_gan = uv[0][0]
    # 30/10/2026 (công cụ scan): tên đọc từ bản scan sai chữ ("Cây sori" / "Cây Sơ ri", "Lekina" / "Lekima") nhưng ĐƠN GIÁ trùng một mục
    # cũ chưa khớp cùng nhóm và tên giống nhau một phần -> cùng mục (giá đúng từng đồng hiếm khi trùng ngẫu nhiên)
    for m in ds:
        if m.trang_thai != 'mới' or not m.don_gia or id(m) in xong:
            continue
        n = nhom or m.nhom or 3
        k = _khoa_quy_cach(m.ten)
        ung = []
        for x in hien[n]:
            if (n, x['ma']) in da_khop or x['don_gia'] in (None, '') or doc_gia(x['don_gia']) != m.don_gia:
                continue
            ung.append((difflib.SequenceMatcher(None, k, _khoa_quy_cach(x['ten'])).ratio(), x))
        ung.sort(key=lambda t: -t[0])
        if ung and ung[0][0] >= NGUONG_KHOP_THEO_GIA and (len(ung) == 1 or ung[0][0] - ung[1][0] >= 0.1):
            m.khop_gan = ung[0][0]
            ghi_khop(m, ung[0][1], n)
    # mã cho mục mới (người dùng 30/10/2026: "tự tạo mã cây trồng theo văn bản mới") - số tiếp theo của bộ đơn giá, theo thứ tự văn
    # bản; ap_dung cấp đúng mã này (mã của mục bị bỏ không dùng lại: dự án cũ còn ghi mã đó)
    from .ma_tai_san import tien_to
    lon = _so_lon_nhat(hien)
    for m in ds:
        m.ma_moi = ''
        if m.trang_thai == 'mới' and not m.ma:
            n = nhom or m.nhom or 3
            tt = 'CS' if n == 4 else tien_to(3 if n == NHOM_VN else n, n == NHOM_VN)
            lon[tt] = lon.get(tt, 0) + 1
            m.ma_moi = f'{tt}{lon[tt]}'
    if thay_the:
        khop_ma = {ma for _, ma in da_khop}
        vn_ma = {x['ma'] for x in hien[NHOM_VN]}
        for n in pham_vi_thay_the(ds, nhom):
            for x in hien[n]:
                if x['ma'] in khop_ma or (n == 3 and x['ma'] in vn_ma):
                    continue
                g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else 0
                ds.append(Muc(x['ten'], x['dvt'] or '', g or 0, trang_thai='bỏ', ma_khop=x['ma'], gia_cu=g, nhom=n,
                              ten_cu=x['ten'], ghi_chu_cu=x['ghi_chu'] or '', bo_cu=True,
                              nguon_dong=f'Mục {NHOM_PHAM_VI.get(n, "")} trong bộ đơn giá đang dùng nhưng văn bản mới không có'))
    return ds


def _so_lon_nhat(hien: dict) -> dict:
    """{tiền tố mã: số lớn nhất đang dùng} (TS / CT / VN / CS) trong các dòng danh mục đã đọc."""
    lon = {}
    for ds_ in hien.values():
        for x in ds_:
            m = re.fullmatch(r'([A-Za-z]+)(\d+)', str(x['ma'] or '').strip())
            if m:
                k = m.group(1).upper()
                lon[k] = max(lon.get(k, 0), int(m.group(2)))
    return lon


def pham_vi_thay_the(ds: list, nhom: int | None = None) -> list:
    """Các nhóm danh mục văn bản thay thế (nhóm của các dòng đọc được từ văn bản, không tính dòng 'bỏ')."""
    return sorted({nhom or m.nhom or 3 for m in ds if not m.bo_cu})


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


def _ma_cap(con, m, bang: str, tt: str, da_cap: dict, dung: set) -> str:
    """Mã của mục mới: mã đã hiện trên bảng (so_khop - Muc.ma_moi) khi còn trống, không thì số tiếp theo."""
    from .ma_tai_san import ma_tiep
    if m.ma_moi and m.ma_moi.upper().startswith(tt) and m.ma_moi not in dung:
        dung.add(m.ma_moi)
        so = int(m.ma_moi[len(tt):])
        da_cap[tt] = max(da_cap.get(tt, 0), so)
        return m.ma_moi
    while True:
        ma = ma_tiep(con, bang, tt, da_cap)
        if ma not in dung:
            dung.add(ma)
            return ma


TRANG_THAI_GHI = ('mới', 'cập nhật', 'đổi quy cách', 'bỏ')
CHU_TRANG_THAI = {'mới': 'mục mới', 'cập nhật': 'mục đổi giá', 'đổi quy cách': 'mục đổi tên / quy cách', 'bỏ': 'mục bỏ'}


def ap_dung(ds: list, nhom: int | None, nguon: str, phien_ban: str = '', van_ban: dict | None = None,
            van_ban_cu: list | tuple = ()) -> dict:
    """Tạo bộ đơn giá mới (bộ đang dùng + các mục được chọn) và cài. Trả thông tin bộ mới + số mục.
    nhom None / 0: mỗi dòng theo Muc.nhom. van_ban: kết quả phan_tich_van_ban (ghi vào danh mục văn bản căn cứ).
    van_ban_cu: id các dòng văn bản căn cứ bị văn bản này thay thế (chế độ thay thế) -> trạng thái "Hết hiệu lực - thay thế bởi …"."""
    chon = [m for m in ds if m.chon and m.trang_thai in TRANG_THAI_GHI]
    if not chon and not (van_ban and van_ban.get('so_hieu')):
        raise LoiNhap('Không có mục nào mới, đổi giá, đổi quy cách hoặc bỏ để cập nhật.')
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
            so = {k: 0 for k in TRANG_THAI_GHI}
            theo_nhom = {}
            with con, csdl.mo_khoa_danh_muc(con):
                # mã mục mới theo quy ước 0.9.69 (ma_tai_san): CS (hỗ trợ), TS (nhà), CT (cây), VN (vật nuôi) - số tiếp theo
                from .ma_tai_san import doi_ma, ma_tiep, tien_to
                from .nghiep_vu import la_vat_nuoi
                # số cuối từng tiền tố lấy TRƯỚC khi xóa dòng 'bỏ' - mã của mục bị bỏ không cấp lại cho mục khác
                da_cap = {tt: max(n - 1, 0) for tt, n in ((tt, int(ma_tiep(con, b, tt)[len(tt):])) for b, tt in
                          (('dm_hotro', 'CS'), ('dm_taisan', 'TS'), ('dm_taisan', 'CT'), ('dm_taisan', 'VN')))}
                dung = {r_[0] for b in ('dm_hotro', 'dm_taisan') for r_ in con.execute(f'SELECT ma FROM {b}')}
                for m in chon:
                    nm = nhom or m.nhom or 3
                    bang = 'dm_hotro' if nm == 4 else 'dm_taisan'
                    if m.trang_thai == 'bỏ':
                        con.execute(f'DELETE FROM {bang} WHERE ma = ?', (m.ma_khop,))
                    elif m.trang_thai in ('cập nhật', 'đổi quy cách'):
                        con.execute(f'UPDATE {bang} SET don_gia = ? WHERE ma = ?', (chuoi(m.don_gia), m.ma_khop))
                        if m.ten_thay:              # thay thế theo cách ghi của văn bản mới: tên, mật độ (mã giữ nguyên)
                            con.execute(f'UPDATE {bang} SET ten = ? WHERE ma = ?', (m.ten_thay, m.ma_khop))
                            if bang == 'dm_taisan':
                                con.execute('UPDATE dm_taisan SET ghi_chu = ? WHERE ma = ?', (m.ghi_chu_thay, m.ma_khop))
                    elif nm == 4:
                        ma = doi_ma(m.ma, 4) if m.ma else _ma_cap(con, m, 'dm_hotro', 'CS', da_cap, dung)
                        con.execute('INSERT INTO dm_hotro (ma, ten, dvt, don_gia, can_cu, trang_thai) VALUES (?,?,?,?,?,?)',
                                    (ma, m.ten, m.dvt, chuoi(m.don_gia), nguon, 'Cập nhật từ file'))
                    else:
                        nhom_db = 3 if nm == NHOM_VN else nm          # vật nuôi: nhom 3 + phân loại vật nuôi (CSDL không có nhom 7)
                        pl = _phan_loai(con, nm, m.ten, van_ban)
                        vn = nhom_db == 3 and la_vat_nuoi(pl)
                        ma = doi_ma(m.ma, nhom_db, vn) if m.ma else _ma_cap(con, m, 'dm_taisan', tien_to(nhom_db, vn), da_cap, dung)
                        con.execute('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) VALUES (?,?,?,?,?,?,?)',
                                    (ma, nhom_db, pl, m.ten, m.dvt, chuoi(m.don_gia),
                                     '; '.join(x for x in (m.ghi_chu, f'Cập nhật từ {nguon}') if x)))
                    so[m.trang_thai] += 1
                    theo_nhom.setdefault(nm, {k: 0 for k in TRANG_THAI_GHI})[m.trang_thai] += 1
                # mới / đổi giá luôn ghi (như trước); đổi quy cách / bỏ chỉ ghi khi có
                tom_tat = '; '.join(f'{NHOM[k]}: ' + ', '.join(f'{v[t]} {chu}' for t, chu in CHU_TRANG_THAI.items()
                                                               if v[t] or t in ('mới', 'cập nhật'))
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
                ten_moi = so_hieu or nguon
                for i in van_ban_cu:
                    if cu is None or i != cu[0]:
                        con.execute('UPDATE van_ban SET trang_thai = ? WHERE id = ?',
                                    (f'Hết hiệu lực - thay thế bởi {ten_moi} (cập nhật {datetime.now():%d/%m/%Y})', i))
                con.execute('UPDATE du_an SET phien_ban_gia = ?, nguon_nhap = ?, ngay_nhap = ? WHERE id = 1',
                            (pb, nguon, datetime.now().isoformat(timespec='seconds')))
        finally:
            con.close()
        tt = don_gia.cai_bo(moi)
    return dict(tt, so_moi=so['mới'], so_cap_nhat=so['cập nhật'], so_quy_cach=so['đổi quy cách'], so_bo=so['bỏ'],
                theo_nhom=theo_nhom)
