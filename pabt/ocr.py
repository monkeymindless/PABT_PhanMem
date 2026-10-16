"""Nhận dạng chữ (OCR) cho văn bản scan: PDF dạng ảnh, file ảnh JPG / PNG. Hai bộ nhận dạng (15/10/2026):

1. Windows OCR (Windows 10 / 11, có sẵn trong Windows - không cài thêm phần mềm): gọi Windows.Media.Ocr qua PowerShell 5.1
   (-Command như bộ cài: không vướng ExecutionPolicy). CẦN gói nhận dạng tiếng Việt của Windows ("Language.OCR~~~vi-VN") - máy
   Windows tiếng Anh thường chỉ có en-US: trang_thai_windows() báo 'thieu_tieng_viet', cai_tieng_viet_windows() mở lệnh cài
   (Windows hỏi quyền quản trị, tải vài MB). Kết quả là từng từ kèm toạ độ - gom các từ cùng hàng ngang thành một dòng.
2. Tesseract OCR (dự phòng, kể cả Windows 7 / 8): không đóng gói trong mã nguồn; tìm theo thứ tự biến môi trường PABT_TESSERACT,
   thư mục `tesseract\\` cạnh PABT.exe, `%APPDATA%\\PABT\\tesseract\\`, nơi cài mặc định (`C:\\Program Files\\Tesseract-OCR`),
   rồi PATH. Cần `vie.traineddata` (và `osd.traineddata` để tự xoay trang ngang).
Chọn bộ: Windows OCR có tiếng Việt -> Windows; không thì Tesseract có tiếng Việt; biến PABT_OCR = windows / tesseract để ép (kiểm
thử). Không có bộ nào: PDF có chữ, Word, Excel vẫn đọc bình thường, chỉ bản scan là không đọc được (dán chữ từ Clipboard thay thế).
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DUOI_ANH = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')
DPI = 300


class LoiOCR(RuntimeError):
    pass


class DaHuy(LoiOCR):
    pass


def _ung_vien() -> list:
    ds = []
    if os.environ.get('PABT_TESSERACT'):
        ds.append(Path(os.environ['PABT_TESSERACT']))
    exe = 'tesseract.exe' if sys.platform == 'win32' else 'tesseract'
    if getattr(sys, 'frozen', False):
        ds.append(Path(sys.executable).parent / 'tesseract' / exe)
    ds.append(Path(__file__).resolve().parents[1] / 'tesseract' / exe)
    ds.append(Path(os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT') /
              'tesseract' / exe)
    for bien in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        if os.environ.get(bien):
            ds.append(Path(os.environ[bien]) / 'Tesseract-OCR' / exe)
            ds.append(Path(os.environ[bien]) / 'Programs' / 'Tesseract-OCR' / exe)
    w = shutil.which('tesseract')
    if w:
        ds.append(Path(w))
    return ds


def tim_tesseract() -> Path | None:
    for p in _ung_vien():
        if p.is_file():
            return p
    return None


def _chay(lenh: list, cho=None, gioi_han: float = 300) -> subprocess.CompletedProcess:
    """Chạy lệnh; trong lúc chờ gọi cho() (giữ giao diện không treo, trả True = người dùng hủy)."""
    import threading
    pr = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    # đọc stdout / stderr SONG SONG (0.9.95): trước đây chỉ chờ tiến trình kết thúc rồi mới đọc - trang scan nhiều chữ (bảng giá,
    # bảng phương án: > ~64 KB kết quả) làm đầy ống, PowerShell / Tesseract chặn ghi, hai bên chờ nhau tới hết giờ ("quá lâu")
    ra, loi = [], []
    doc = [threading.Thread(target=lambda: ra.append(pr.stdout.read()), daemon=True),
           threading.Thread(target=lambda: loi.append(pr.stderr.read()), daemon=True)]
    for t in doc:
        t.start()
    bat_dau = time.monotonic()
    while pr.poll() is None:
        if cho is not None and cho():
            pr.kill()
            pr.wait()
            raise DaHuy('Đã hủy nhận dạng chữ.')
        if time.monotonic() - bat_dau > gioi_han:
            pr.kill()
            pr.wait()
            raise LoiOCR('Nhận dạng chữ quá lâu, đã dừng.')
        time.sleep(0.05)
    for t in doc:
        t.join(10)
    return subprocess.CompletedProcess(lenh, pr.returncode, b''.join(ra), b''.join(loi))


def ngon_ngu(tess: Path | None = None) -> list:
    tess = tess or tim_tesseract()
    if tess is None:
        return []
    try:
        r = _chay([str(tess), '--list-langs'], gioi_han=30)
    except (OSError, LoiOCR):
        return []
    return [x.strip() for x in (r.stdout + r.stderr).decode('utf-8', 'replace').splitlines()[1:] if x.strip()]


def _tesseract_san_sang() -> str:
    tess = tim_tesseract()
    if tess is None:
        return 'chưa có Tesseract OCR'
    if 'vie' not in ngon_ngu(tess):
        return f'Tesseract ({tess}) chưa có dữ liệu tiếng Việt (vie.traineddata)'
    return ''


HUONG_DAN_TIENG_VIET = ('Cài gói nhận dạng chữ tiếng Việt của Windows: Cài đặt (Settings) > Thời gian và ngôn ngữ > Ngôn ngữ > Thêm '
                        'ngôn ngữ > Tiếng Việt (chọn "Nhận dạng chữ viết tay / OCR"), hoặc bấm "Cài gói tiếng Việt" - Windows hỏi '
                        'quyền quản trị rồi tải vài MB. Cài xong không cần khởi động lại.')


def may_doc() -> tuple:
    """Bộ nhận dạng sẽ dùng: ('windows', None) / ('tesseract', đường dẫn) / ('', None)."""
    ep = os.environ.get('PABT_OCR', '').lower()
    if ep != 'tesseract' and trang_thai_windows() == 'san_sang':
        return 'windows', None
    if ep != 'windows' and not _tesseract_san_sang():
        return 'tesseract', tim_tesseract()
    return '', None


def san_sang() -> str:
    """'' nếu nhận dạng được bản scan tiếng Việt, không thì câu giải thích còn thiếu gì và cách khắc phục."""
    if may_doc()[0]:
        return ''
    tt = trang_thai_windows()
    if tt == 'thieu_tieng_viet':
        return ('Máy có bộ nhận dạng chữ của Windows nhưng CHƯA có gói tiếng Việt. ' + HUONG_DAN_TIENG_VIET +
                ' Hoặc dán chữ / chọn file Excel, Word thay bản scan.')
    return ('Máy chưa có bộ nhận dạng chữ tiếng Việt (Windows 7 / 8 không có Windows OCR; ' + _tesseract_san_sang() + '). Cài '
            'Tesseract OCR kèm tiếng Việt hoặc chép thư mục "tesseract" cạnh PABT.exe; hoặc dán chữ (Snipping Tool, Zalo…) / chọn '
            'file Excel, Word thay bản scan.')


# ---------------------------------------------------------------- Windows OCR (Windows.Media.Ocr qua PowerShell)
_PS_OCR = r'''
param([string]$Anh = '', [string]$NgonNgu = 'vi')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]
} catch { Write-Output '##KHONG_CO##'; exit 2 }
$lang = New-Object Windows.Globalization.Language($NgonNgu)
if (-not [Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($lang)) { Write-Output '##THIEU_NGON_NGU##'; exit 3 }
if (-not $Anh) { Write-Output '##SAN_SANG##'; exit 0 }
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$asTask = @([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Cho($op, [Type]$t) { $k = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $null = $k.Wait(-1); $k.Result }
$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$f = Cho ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Anh)) ([Windows.Storage.StorageFile])
$st = Cho ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$dec = Cho ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($st)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Cho ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$bmp = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert($bmp, [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8)
$kq = Cho ($eng.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
foreach ($d in $kq.Lines) { foreach ($w in $d.Words) {
    $r = $w.BoundingRect
    Write-Output ("{0}`t{1}`t{2}`t{3}`t{4}" -f [int]$r.X, [int]$r.Y, [int]$r.Width, [int]$r.Height, $w.Text) } }
$st.Dispose()
'''
_TRANG_THAI_WIN = {}


def _powershell() -> str:
    """powershell.exe 5.1 (WinRT; PowerShell 7 không nạp được kiểu Windows Runtime). Tiến trình 32-bit trên Windows 64-bit vẫn gọi được."""
    goc = os.environ.get('SystemRoot', r'C:\Windows')
    p = Path(goc) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    return str(p) if p.is_file() else 'powershell.exe'


def _chay_ps(td: Path, *thamso, cho=None, gioi_han: float = 120) -> subprocess.CompletedProcess:
    kb = td / 'pabt_ocr.ps1'
    if not kb.is_file():
        kb.write_text(_PS_OCR, encoding='utf-8-sig')
    ts = ' '.join("'" + str(x).replace("'", "''") + "'" for x in thamso)
    lenh = (f"& ([scriptblock]::Create([IO.File]::ReadAllText('{str(kb).replace(chr(39), chr(39) * 2)}', "
            f"[Text.Encoding]::UTF8))) {ts}")
    return _chay([_powershell(), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', lenh], cho, gioi_han)


def trang_thai_windows(ngon_ngu: str = 'vi') -> str:
    """'san_sang' / 'thieu_tieng_viet' (có Windows OCR, thiếu gói ngôn ngữ) / 'khong_co' (Windows 7 / 8, không chạy được).
    Nhớ trong tiến trình (gọi PowerShell ~1 giây); xoa_nho_windows() sau khi cài gói."""
    if sys.platform != 'win32':
        return 'khong_co'
    if ngon_ngu in _TRANG_THAI_WIN:
        return _TRANG_THAI_WIN[ngon_ngu]
    tt = 'khong_co'
    td = Path(tempfile.mkdtemp(prefix='PABT_ocr_'))
    try:
        r = _chay_ps(td, '', ngon_ngu, gioi_han=60)
        ra = r.stdout.decode('utf-8', 'replace')
        tt = 'san_sang' if '##SAN_SANG##' in ra else 'thieu_tieng_viet' if '##THIEU_NGON_NGU##' in ra else 'khong_co'
    except (OSError, LoiOCR):
        pass
    finally:
        shutil.rmtree(td, ignore_errors=True)
    _TRANG_THAI_WIN[ngon_ngu] = tt
    return tt


def xoa_nho_windows() -> None:
    _TRANG_THAI_WIN.clear()


def cai_tieng_viet_windows():
    """Mở lệnh cài gói nhận dạng chữ tiếng Việt của Windows (Windows hỏi quyền quản trị - UAC). Trả tiến trình (không chờ).
    Chỉ gọi khi người dùng bấm "Cài gói tiếng Việt"."""
    lenh = ("Add-WindowsCapability -Online -Name 'Language.OCR~~~vi-VN~0.0.1.0'; "
            "Write-Host 'Xong. Đóng cửa sổ này rồi đọc lại bản scan trong LARC.'; Start-Sleep 5")
    return subprocess.Popen([_powershell(), '-NoProfile', '-Command',
                             f"Start-Process '{_powershell()}' -Verb RunAs -ArgumentList '-NoProfile','-Command',\"{lenh}\""],
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def gom_dong(tu: list, he_so: float = 0.6) -> list:
    """[(x, y, rộng, cao, chữ)] các từ -> dòng chữ: từ có tâm dọc cách tâm hàng < he_so x chiều cao chữ là cùng hàng (bảng giá nhiều
    cột: Windows OCR trả các cột thành các dòng riêng), trong hàng xếp theo x."""
    hang = []                                           # [[tâm y, cao, [từ]]]
    for x, y, w, h, t in sorted(tu, key=lambda a: (a[1] + a[3] / 2, a[0])):
        tam = y + h / 2
        for hg in hang:
            if abs(tam - hg[0]) < he_so * max(h, hg[1]):
                hg[2].append((x, w, h, t))
                hg[0] = (hg[0] * (len(hg[2]) - 1) + tam) / len(hg[2])
                break
        else:
            hang.append([tam, h, [(x, w, h, t)]])
    kq = []
    for hg in sorted(hang, key=lambda a: a[0]):
        # 0.9.95: khoảng trống ngang > CACH_COT x chiều cao chữ = sang cột kế của bảng -> nối bằng Tab (giữ cấu trúc cột "Tên \t ĐVT
        # \t Số lượng \t Đơn giá \t Tỷ lệ \t Thành tiền" cho bóc tách bảng phương án chi tiết / bảng giá)
        chu, cuoi = '', None
        for x, w, h, t in sorted(hg[2]):
            if cuoi is not None:
                chu += '\t' if x - cuoi > CACH_COT * max(h, 1) else ' '
            chu += t
            cuoi = x + w
        kq.append(chu)
    return kq


CACH_COT = 2.2                                          # gom_dong: khoảng trống (x chiều cao chữ) coi là sang cột mới


_RE_CUM_SO = re.compile(r'(?<![^\W\d_])[\doO][\doO.,]*[\doO](?![^\W\d_])')


def sua_so(dong: str) -> str:
    """Lỗi nhận dạng hay gặp trong số tiền: chữ o / O thay số 0 ("3.500.ooo" -> "3.500.000") - chỉ sửa cụm có >= 2 chữ số và
    toàn chữ số / o / dấu ngăn (không đụng chữ "Ô", "o" trong từ)."""
    def sua(m):
        t = m.group(0)
        return t.replace('o', '0').replace('O', '0') if sum(c.isdigit() for c in t) >= 2 else t
    return _RE_CUM_SO.sub(sua, dong)


def doc_anh_windows(anh: Path, cho=None, td: Path | None = None, ngon_ngu: str = 'vi') -> str:
    """Chữ trên một ảnh bằng Windows OCR (mỗi hàng ngang một dòng)."""
    tam = td or Path(tempfile.mkdtemp(prefix='PABT_ocr_'))
    try:
        r = _chay_ps(tam, str(Path(anh).resolve()), ngon_ngu, cho=cho, gioi_han=180)
        ra = r.stdout.decode('utf-8', 'replace')
        if '##THIEU_NGON_NGU##' in ra:
            raise LoiOCR('Windows chưa có gói nhận dạng chữ tiếng Việt. ' + HUONG_DAN_TIENG_VIET)
        if r.returncode != 0 or '##KHONG_CO##' in ra:
            raise LoiOCR('Windows OCR báo lỗi: ' + (r.stderr.decode('utf-8', 'replace').strip() or ra.strip())[:300])
        tu = []
        for d in ra.splitlines():
            p = d.split('\t', 4)
            if len(p) == 5 and all(x.lstrip('-').isdigit() for x in p[:4]):
                tu.append((int(p[0]), int(p[1]), int(p[2]), int(p[3]), p[4]))
        return '\n'.join(gom_dong(tu))
    finally:
        if td is None:
            shutil.rmtree(tam, ignore_errors=True)


# ---------------------------------------------------------------- ảnh từng trang
def _anh_trang_pypdf(file: Path, td: Path):
    """Qt5 (bản Win 7/8, không có QtPdf): ảnh scan lớn nhất của TỪNG trang bằng pypdf - yield (số trang, tổng, ảnh | None) ngay khi
    lấy xong một trang (không dựng hết file trước khi đọc / báo tiến độ)."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise LoiOCR('Máy này thiếu bộ đọc PDF.') from e
    trang_ds = PdfReader(str(file)).pages
    tong = len(trang_ds)
    for i, trang in enumerate(trang_ds):
        p = _anh_jpeg(trang, td / f'trang_{i + 1:04d}')
        if p is None:
            try:                                        # ảnh nén kiểu khác: pypdf cần thư viện Pillow
                anh = sorted(trang.images, key=lambda a: len(a.data), reverse=True)
            except ImportError as e:
                raise LoiOCR('PDF scan có ảnh không phải JPEG: máy này (Windows 7/8) chưa đọc được, chuyển file sang ảnh '
                             'JPG rồi chọn lại.') from e
            if anh:
                p = td / f'trang_{i + 1:04d}{Path(anh[0].name).suffix or ".png"}'
                p.write_bytes(anh[0].data)
        yield i + 1, tong, p


def _anh_jpeg(trang, goc: Path) -> Path | None:
    """Ảnh scan JPEG lớn nhất của trang PDF: chép nguyên luồng dữ liệu (không cần Pillow). Không có thì None."""
    try:
        xo = trang['/Resources']['/XObject'].get_object()
    except (KeyError, TypeError, AttributeError):
        return None
    tot = None
    for k in xo:
        o = xo[k].get_object()
        if o.get('/Subtype') != '/Image':
            continue
        loc = o.get('/Filter')
        loc = list(loc) if isinstance(loc, list) else [loc]
        if loc and loc[-1] in ('/DCTDecode', '/JPXDecode') and all(x in ('/DCTDecode', '/JPXDecode') for x in loc):
            du_lieu = o.get_data() if len(loc) > 1 else o._data
            if tot is None or len(du_lieu) > len(tot[0]):
                tot = (du_lieu, '.jpg' if loc[-1] == '/DCTDecode' else '.jp2')
    if tot is None:
        return None
    p = goc.with_suffix(tot[1])
    p.write_bytes(tot[0])
    return p


def _chuan_bi(anh: Path, td: Path | None = None) -> Path:
    """Ảnh scan độ phân giải thấp (máy scan để 150 dpi): phóng lên ~300 dpi, chuyển ảnh xám - Tesseract đọc chính xác hơn
    hẳn. Trả file PNG đã xử lý (hoặc ảnh gốc khi không xử lý được)."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
    except ImportError:
        return anh
    im = QImage(str(anh))
    if im.isNull():
        return anh
    im = im.convertToFormat(QImage.Format.Format_Grayscale8)     # xám TRƯỚC khi phóng: 1 byte / điểm ảnh thay 4 (nhanh ~3 lần)
    canh = min(im.width(), im.height())
    if canh < 2000:                                     # cạnh ngắn A4 ở 300 dpi ~ 2480 px
        he_so = 2480 / canh
        im = im.scaled(int(im.width() * he_so), int(im.height() * he_so), Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    ra = (td or anh.parent) / (anh.stem + '_xl.png')         # td: thư mục tạm - không ghi cạnh ảnh của người dùng
    return ra if im.save(str(ra)) else anh


def _xoay(anh: Path, do: int) -> None:
    from PySide6.QtGui import QImage, QTransform
    im = QImage(str(anh))
    if not im.isNull():
        im.transformed(QTransform().rotate(do)).save(str(anh))


# ---------------------------------------------------------------- nhận dạng
def doc_anh(anh: Path, tess: Path | None = None, cho=None, td: Path | None = None, may: str = '') -> str:
    """Chữ trên một ảnh trang (may 'windows': Windows OCR; còn lại Tesseract - trang nằm ngang tự xoay lại trước khi đọc)."""
    if may == 'windows':                                # ảnh nhỏ (scan 150 dpi) phóng lên ~300 dpi như với Tesseract
        return doc_anh_windows(_chuan_bi(Path(anh), td), cho, td)
    tess = tess or tim_tesseract()
    if tess is None:
        raise LoiOCR(san_sang())
    goc = Path(anh)
    anh = _chuan_bi(goc, td)
    try:
        r = _chay([str(tess), str(anh), '-', '--psm', '0'], cho, 60)
        m = re.search(rb'Rotate:\s*(\d+)', r.stdout)
        if m and int(m.group(1)) in (90, 180, 270) and anh != goc:    # chỉ xoay bản đã xử lý, không ghi đè ảnh gốc
            _xoay(anh, int(m.group(1)))
    except LoiOCR:
        raise
    except OSError:
        pass                                            # thiếu osd.traineddata: đọc nguyên chiều
    r = _chay([str(tess), str(anh), '-', '-l', 'vie', '--psm', '6'], cho)
    if r.returncode != 0:
        raise LoiOCR('Tesseract báo lỗi: ' + r.stderr.decode('utf-8', 'replace').strip()[:300])
    return r.stdout.decode('utf-8', 'replace')


def tung_trang(file, bao_tien_do=None, cho=None, dpi: int = DPI):
    """Đọc từng trang rồi xóa ảnh trang (không dựng hết file trước — file lớn không chiếm bộ nhớ). Yield chữ từng trang."""
    may, tess = may_doc()
    if not may:
        raise LoiOCR(san_sang())
    file = Path(file)
    td = Path(tempfile.mkdtemp(prefix='PABT_ocr_'))
    try:
        if file.suffix.lower() in DUOI_ANH:
            if bao_tien_do:
                bao_tien_do(1, 1)
            if cho and cho():
                raise DaHuy()
            yield doc_anh(file, tess, cho, td, may)
            return
        try:
            from PySide6.QtPdf import QPdfDocument
        except ImportError:
            QPdfDocument = None
        if QPdfDocument is not None:
            from PySide6.QtCore import QSize
            d = QPdfDocument()
            try:
                d.load(str(file))
                tong = d.pageCount()
                if tong <= 0:
                    raise LoiOCR('Không mở được PDF hoặc file không có trang.')
                for i in range(tong):
                    if cho and cho():
                        raise DaHuy()
                    if bao_tien_do:
                        bao_tien_do(i + 1, tong)
                    kt = d.pagePointSize(i)
                    # Một trang một ảnh, xóa ngay sau khi đọc: file vài nghìn trang không giữ hết ảnh trong RAM.
                    anh = d.render(i, QSize(max(1, int(kt.width() * dpi / 72)), max(1, int(kt.height() * dpi / 72))))
                    p = td / f'trang_{i + 1:04d}.png'
                    if anh.isNull() or not anh.save(str(p)):
                        continue
                    try:
                        yield doc_anh(p, tess, cho, td, may)
                    finally:
                        try:
                            p.unlink()
                        except OSError:
                            pass
            finally:
                d.close()
            return
        for i, tong, p in _anh_trang_pypdf(file, td):
            if cho and cho():
                raise DaHuy()
            if bao_tien_do:
                bao_tien_do(i, tong)
            if p is None:
                continue
            try:
                yield doc_anh(p, tess, cho, td, may)
            finally:
                try:
                    p.unlink()
                except OSError:
                    pass
    finally:
        shutil.rmtree(td, ignore_errors=True)


def doc_chu(file, bao_tien_do=None, cho=None) -> list:
    """Các dòng chữ của bản scan (PDF ảnh hoặc file ảnh). bao_tien_do(trang, tổng số trang); cho() trả True để hủy."""
    if not may_doc()[0]:
        raise LoiOCR(san_sang())
    dong = []
    for chu in tung_trang(file, bao_tien_do, cho):
        dong += [sua_so(x.strip()) for x in chu.splitlines() if x.strip()]
    return dong
