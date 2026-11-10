"""Đọc bảng đơn giá từ file (1.0.96 - tách khỏi nhap_don_gia.py, không Qt): Excel (.xlsx / .xlsm / .xls qua chuyen_office), Word
(.docx / .doc), PDF có lớp chữ (QtPdf / pypdf), CSV, ảnh / PDF scan (OCR Tesseract trên máy). Trả danh sách dòng (mỗi dòng một
list ô chữ). nhap_don_gia nhập lại mọi tên (nhap_don_gia.doc_bang, LoiPdfScan, chuyen_office... không đổi); kiểm thử vá
chuyen_office ở ĐÂY (pabt.nhap_don_gia_doc.chuyen_office) - doc_bang gọi nó trong module này.
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .loi import LoiNhap


class LoiPdfScan(LoiNhap):
    """PDF không có lớp chữ (ảnh scan): chỉ đọc được bằng nhận dạng chữ (OCR)."""


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
        if that in ('.xls', '.doc'):                    # Office 97-2003: Word / Excel, rồi LibreOffice, rồi bộ đọc .doc thuần Python
            try:
                return doc_bang(chuyen_office(p, that))
            except LoiNhap:
                if that != '.doc':
                    raise
                from .doc_doc import LoiDoc, doc_dong
                try:
                    return doc_dong(p)
                except LoiDoc as e:
                    raise LoiNhap(f'File "{p.name}" là Word 97-2003 (.doc) nhưng không đọc được chữ. {e}') from None
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
        from .chuan_chu import giai_ma_byte
        txt = giai_ma_byte(p.read_bytes())[0]          # 1.0.98: CSV / TXT ANSI (TCVN3, VNI, Windows-1258) không còn thành "�"
        txt = txt.replace('\r\n', '\n').replace('\r', '\n')    # như read_text: csv.Sniffer của Python 3.8 đoán sai khi còn \r\n
        try:
            mau = csv.Sniffer().sniff(txt[:4000], delimiters=',;\t|') if txt.strip() else csv.excel
        except csv.Error:                               # văn bản thường (không có cột): mỗi dòng một ô
            return [[l.strip()] for l in txt.splitlines()]
        return [[c.strip() for c in r] for r in csv.reader(txt.splitlines(), mau)]
    raise LoiNhap(f'Chưa hỗ trợ file {duoi or "(không có đuôi)"}. Hỗ trợ: Excel, Word (.doc, .docx), PDF có chữ, CSV.')


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
            kq = subprocess.run([__import__('pabt').exe_he_thong('cscript.exe'), '//nologo', str(vbs), str(ds)], capture_output=True, timeout=180,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.TimeoutExpired) as e:
            raise LoiNhap(f'{thay}\n({e})') from None
    loi = kq.stderr.decode('oem', 'replace').strip()
    if not dich.exists() and loai == '.doc' and _chuyen_libreoffice(p, dich, 'docx'):
        return dich
    if not dich.exists():
        if 'KHONG_CO_OFFICE' in loi:
            raise LoiNhap(f'Máy chưa có Microsoft {ten} để đọc file cũ. {thay}')
        raise LoiNhap(f'{thay}\n({loi[:300]})')
    return dich


def _chuyen_libreoffice(p: Path, dich: Path, muc: str) -> bool:
    """Chuyển .doc sang .docx bằng LibreOffice nếu máy có. False: không có hoặc không tạo được file."""
    import shutil
    from .van_ban_trinh import tim_libreoffice
    soffice = tim_libreoffice()
    if soffice is None:
        return False
    with tempfile.TemporaryDirectory(prefix='pabt_doc_') as td:
        td = Path(td)
        ho_so = td / 'hs'
        ra = td / 'ra'
        ra.mkdir()
        lenh = [str(soffice), f'-env:UserInstallation={ho_so.resolve().as_uri()}', '--headless', '--invisible',
                '--norestore', '--nologo', '--nodefault', '--nolockcheck', '--convert-to', muc, '--outdir', str(ra), str(p)]
        try:
            subprocess.run(lenh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.SubprocessError):
            return False
        tao = ra / (p.stem + '.' + muc)
        if not tao.is_file() or tao.stat().st_size <= 0:
            return False
        shutil.copyfile(str(tao), str(dich))
    return dich.is_file()


_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
_RE_PHONG_CU = re.compile(rb'(?i)w:(?:ascii|hAnsi)="(?:\.vn|vni[- ])')


def _phong_cua(rpr) -> str:
    """Tên phông (ascii, không có thì hAnsi) trong w:rPr."""
    if rpr is None:
        return ''
    f = rpr.find(_W + 'rFonts')
    if f is None:
        return ''
    return f.get(_W + 'ascii') or f.get(_W + 'hAnsi') or ''


class _KieuDocx:
    """Phông mặc định, phông + đánh số theo kiểu đoạn (styles.xml), định dạng đánh số (numbering.xml) của một file Word."""

    def __init__(self, z, an_toan, ten: str, can_so: bool):
        self.phong_md, self.phong_kieu, self.so_kieu = '', {}, {}
        self.num, self.abs, self.dem = {}, {}, {}
        du = self._doc(z, 'word/styles.xml', an_toan, ten)
        if du is not None:
            goc = ET.fromstring(du)
            d = goc.find(f'{_W}docDefaults/{_W}rPrDefault/{_W}rPr')
            self.phong_md = _phong_cua(d)
            cha, phong = {}, {}
            for s in goc.iter(_W + 'style'):
                sid = s.get(_W + 'styleId') or ''
                b = s.find(_W + 'basedOn')
                cha[sid] = b.get(_W + 'val') if b is not None else ''
                phong[sid] = _phong_cua(s.find(_W + 'rPr'))
                np_ = s.find(f'{_W}pPr/{_W}numPr')
                if np_ is not None:
                    n = np_.find(_W + 'numId')
                    lv = np_.find(_W + 'ilvl')
                    self.so_kieu[sid] = (n.get(_W + 'val') if n is not None else '', int(lv.get(_W + 'val')) if lv is not None else 0)
            for sid in phong:                            # phông kế thừa theo basedOn
                x, da = sid, set()
                while x and not phong.get(x) and x not in da:
                    da.add(x)
                    x = cha.get(x, '')
                self.phong_kieu[sid] = phong.get(x, '') if x else ''
        if can_so:
            du = self._doc(z, 'word/numbering.xml', an_toan, ten)
            if du is not None:
                goc = ET.fromstring(du)
                for a in goc.iter(_W + 'abstractNum'):
                    lv = {}
                    for l in a.findall(_W + 'lvl'):
                        g = {k: (l.find(_W + k).get(_W + 'val') if l.find(_W + k) is not None else '') for k in ('start', 'numFmt', 'lvlText')}
                        lv[int(l.get(_W + 'ilvl') or 0)] = g
                    self.abs[a.get(_W + 'abstractNumId')] = lv
                for n in goc.iter(_W + 'num'):
                    a = n.find(_W + 'abstractNumId')
                    bd = {}
                    for o in n.findall(_W + 'lvlOverride'):
                        s = o.find(_W + 'startOverride')
                        if s is not None:
                            bd[int(o.get(_W + 'ilvl') or 0)] = int(s.get(_W + 'val') or 1)
                    self.num[n.get(_W + 'numId')] = (a.get(_W + 'val') if a is not None else '', bd)

    @staticmethod
    def _doc(z, ten_trong, an_toan, ten):
        try:
            du = z.read(ten_trong)
        except KeyError:
            return None
        try:
            an_toan.kiem_tra_xml(du, ten)
        except an_toan.LoiAnToan:
            return None
        return du

    @staticmethod
    def _dang(n: int, fmt: str) -> str:
        if fmt in ('lowerLetter', 'upperLetter'):
            s = ''
            while n > 0:
                n, r = divmod(n - 1, 26)
                s = chr(97 + r) + s
            return s.upper() if fmt == 'upperLetter' else s
        if fmt in ('lowerRoman', 'upperRoman'):
            s = ''
            for v, k in ((1000, 'm'), (900, 'cm'), (500, 'd'), (400, 'cd'), (100, 'c'), (90, 'xc'), (50, 'l'), (40, 'xl'), (10, 'x'),
                         (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')):
                while n >= v:
                    s, n = s + k, n - v
            return s.upper() if fmt == 'upperRoman' else s
        if fmt == 'decimalZero':
            return f'{n:02d}'
        return str(n)

    def so(self, ppr) -> str:
        """Chữ đánh số tự động của đoạn ("Điều 5.", "a)", "-"), '' nếu không có."""
        num_id, ilvl = '', 0
        np_ = ppr.find(_W + 'numPr') if ppr is not None else None
        if np_ is not None:
            n, lv = np_.find(_W + 'numId'), np_.find(_W + 'ilvl')
            num_id = n.get(_W + 'val') if n is not None else ''
            ilvl = int(lv.get(_W + 'val')) if lv is not None else 0
        elif ppr is not None and ppr.find(_W + 'pStyle') is not None:
            num_id, ilvl = self.so_kieu.get(ppr.find(_W + 'pStyle').get(_W + 'val'), ('', 0))
        if not num_id or num_id == '0' or num_id not in self.num:
            return ''
        a, bd = self.num[num_id]
        lv = self.abs.get(a) or {}
        g = lv.get(ilvl)
        if g is None:
            return ''
        if g['numFmt'] == 'bullet':
            t = g['lvlText'] or '-'
            return '-' if not t.strip() or any('' <= c <= '' for c in t) else t.strip()
        if g['numFmt'] == 'none':
            return g['lvlText'].strip()
        dem = self.dem.setdefault(a, {})
        if (a, num_id) not in self.dem:                  # danh sách mới bắt đầu lại số (startOverride)
            self.dem[(a, num_id)] = True
            for k, v in bd.items():
                dem[k] = v - 1
        dem[ilvl] = dem.get(ilvl, int(lv[ilvl]['start'] or 1) - 1) + 1
        for k in [k for k in dem if k > ilvl]:           # cấp dưới bắt đầu lại
            del dem[k]
        t = g['lvlText'] or f'%{ilvl + 1}.'
        for k in range(ilvl + 1):
            gk = lv.get(k) or {}
            t = t.replace(f'%{k + 1}', self._dang(dem.get(k, int(gk.get('start') or 1)), gk.get('numFmt') or 'decimal'))
        return t.strip()


def _doc_docx(p: Path, day_du: bool = False) -> list:
    """Dòng (danh sách ô) của file Word. Chữ phông cũ TCVN3 / VNI (theo phông của từng đoạn, kể cả phông kiểu đoạn / mặc định) đổi sang Unicode
    (1.0.90 - mọi đường đọc). day_du=True (bộ quét file): thêm số / gạch đầu dòng tự động của Word ("Điều 5.", "a)", "-"), Tab giữ là Tab,
    ngắt dòng mềm tách dòng, bỏ chữ ẩn."""
    W = _W
    from . import an_toan
    with zipfile.ZipFile(p) as z:
        du = z.read('word/document.xml')
        try:
            an_toan.kiem_tra_xml(du, p.name)            # XML có DOCTYPE / ENTITY: không phân tích
        except an_toan.LoiAnToan as e:
            raise LoiNhap(str(e)) from None
        try:
            kieu_du = z.read('word/styles.xml')
        except KeyError:
            kieu_du = b''
        phong_cu = bool(_RE_PHONG_CU.search(du) or _RE_PHONG_CU.search(kieu_du))
        kieu = _KieuDocx(z, an_toan, p.name, day_du) if (phong_cu or day_du) else None
    from .chuan_chu import chuyen_theo_phong

    def chu_giau(par, trong_o: bool) -> str:
        """Đọc từng đoạn chữ (w:r) theo phông của nó; Tab, ngắt dòng, ký hiệu; số tự động ở đầu đoạn."""
        ppr = par.find(W + 'pPr')
        sid = ''
        if ppr is not None and ppr.find(W + 'pStyle') is not None:
            sid = ppr.find(W + 'pStyle').get(W + 'val') or ''
        phong_doan = kieu.phong_kieu.get(sid, '') or kieu.phong_md
        ra = []
        for r in par.iter(W + 'r'):
            rpr = r.find(W + 'rPr')
            if day_du and rpr is not None and rpr.find(W + 'vanish') is not None:
                continue
            phong = _phong_cua(rpr) or phong_doan
            for x in r:
                if x.tag == W + 't':
                    ra.append(chuyen_theo_phong(x.text or '', phong) if phong_cu else (x.text or ''))
                elif x.tag == W + 'tab':
                    ra.append('\t' if day_du and not trong_o else ' ')
                elif x.tag in (W + 'br', W + 'cr'):
                    ra.append('\n' if day_du and not trong_o else ' ')
                elif x.tag == W + 'noBreakHyphen':
                    ra.append('-')
                elif x.tag == W + 'sym':
                    ma = x.get(W + 'char') or ''
                    ra.append('-' if ma.upper().startswith('F0') else ' ')
        so = kieu.so(ppr) if day_du else ''
        dong = []
        for d in ''.join(ra).split('\n'):
            d = '\t'.join(' '.join(x.split()) for x in d.split('\t')).strip('\t ')
            if d:
                dong.append(d)
        if so and dong:
            dong[0] = f'{so} {dong[0]}'
        return '\n'.join(dong)

    def chu(par, trong_o: bool = False) -> str:
        if kieu is None:
            return ' '.join(''.join(t.text or '' for t in par.iter(W + 't')).split())
        return chu_giau(par, trong_o)

    def o(tc) -> str:                                   # các đoạn trong một ô cách nhau dấu cách ("ỦY BAN NHÂN DÂN TỈNH ...")
        return ' '.join(x for x in (chu(par, True) for par in tc.iter(W + 'p')) if x)

    def doan(el) -> list:
        ra = []
        for t in (chu(par) for par in ([el] if el.tag == W + 'p' else el.iter(W + 'p'))):
            ra += [[d] for d in t.split('\n') if d]
        return ra
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
                dong += doan(el)
            el.clear()
            cha.remove(el)
    if not dong and b'body>' not in du:                 # XML lạ không có <w:body>: đọc các phần tử con của gốc như trước
        for el in ET.fromstring(du):
            if el.tag == W + 'tbl':
                dong += [[o(tc) for tc in tr.findall(W + 'tc')] for tr in el.iter(W + 'tr')]
            else:
                dong += doan(el)
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


class DongScan(list):
    """Các dòng đọc bằng nhận dạng chữ (bản scan): so_khop chặn giá nghi đọc sai chữ số."""
    scan = True


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
            return DongScan(dong_tu_chu('\n'.join(ocr.doc_chu(file, bao_tien_do, cho))))
        except ocr.DaHuy:
            raise
        except ocr.LoiOCR as l:
            raise LoiPdfScan(f'{e}\n\nNhận dạng chữ không được: {l}') from None
