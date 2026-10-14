"""Nhận dạng chữ (OCR) cho văn bản scan: PDF dạng ảnh, file ảnh JPG / PNG. Dùng Tesseract OCR (miễn phí, có gói tiếng Việt).

Tesseract không đóng gói trong mã nguồn; phần mềm tìm theo thứ tự: biến môi trường PABT_TESSERACT, thư mục `tesseract\\`
cạnh PABT.exe, `%APPDATA%\\PABT\\tesseract\\`, nơi cài mặc định (`C:\\Program Files\\Tesseract-OCR`), rồi PATH. Cần dữ liệu
tiếng Việt `vie.traineddata` (và `osd.traineddata` để tự xoay trang ngang). Không có Tesseract: PDF có chữ, Word, Excel vẫn
đọc bình thường, chỉ bản scan là không đọc được.
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
    pr = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    bat_dau = time.monotonic()
    while pr.poll() is None:
        if cho is not None and cho():
            pr.kill()
            pr.communicate()
            raise DaHuy('Đã hủy nhận dạng chữ.')
        if time.monotonic() - bat_dau > gioi_han:
            pr.kill()
            pr.communicate()
            raise LoiOCR('Nhận dạng chữ quá lâu, đã dừng.')
        time.sleep(0.05)
    out, err = pr.communicate()
    return subprocess.CompletedProcess(lenh, pr.returncode, out, err)


def ngon_ngu(tess: Path | None = None) -> list:
    tess = tess or tim_tesseract()
    if tess is None:
        return []
    try:
        r = _chay([str(tess), '--list-langs'], gioi_han=30)
    except (OSError, LoiOCR):
        return []
    return [x.strip() for x in (r.stdout + r.stderr).decode('utf-8', 'replace').splitlines()[1:] if x.strip()]


def san_sang() -> str:
    """'' nếu nhận dạng được bản scan tiếng Việt, không thì câu giải thích còn thiếu gì."""
    tess = tim_tesseract()
    if tess is None:
        return ('Máy chưa có bộ nhận dạng chữ Tesseract OCR (để đọc bản scan). Cài Tesseract (kèm tiếng Việt) hoặc chép '
                'thư mục "tesseract" cạnh PABT.exe; hoặc nhập số tiền bằng tay.')
    if 'vie' not in ngon_ngu(tess):
        return f'Tesseract ({tess}) chưa có dữ liệu tiếng Việt (vie.traineddata).'
    return ''


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
def doc_anh(anh: Path, tess: Path | None = None, cho=None, td: Path | None = None) -> str:
    """Chữ trên một ảnh trang; trang nằm ngang (bảng danh sách đính kèm) tự xoay lại trước khi đọc."""
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
    loi = san_sang()
    if loi:
        raise LoiOCR(loi)
    tess = tim_tesseract()
    file = Path(file)
    td = Path(tempfile.mkdtemp(prefix='PABT_ocr_'))
    try:
        if file.suffix.lower() in DUOI_ANH:
            if bao_tien_do:
                bao_tien_do(1, 1)
            if cho and cho():
                raise DaHuy()
            yield doc_anh(file, tess, cho, td)
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
                        yield doc_anh(p, tess, cho)
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
                yield doc_anh(p, tess, cho)
            finally:
                try:
                    p.unlink()
                except OSError:
                    pass
    finally:
        shutil.rmtree(td, ignore_errors=True)


def doc_chu(file, bao_tien_do=None, cho=None) -> list:
    """Các dòng chữ của bản scan (PDF ảnh hoặc file ảnh). bao_tien_do(trang, tổng số trang); cho() trả True để hủy."""
    loi = san_sang()
    if loi:
        raise LoiOCR(loi)
    dong = []
    for chu in tung_trang(file, bao_tien_do, cho):
        dong += [x.strip() for x in chu.splitlines() if x.strip()]
    return dong
