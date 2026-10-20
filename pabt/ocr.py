"""Nhận dạng chữ (OCR) cho văn bản scan: PDF dạng ảnh, file ảnh JPG / PNG - bằng Tesseract OCR (người dùng 16/10/2026: thay
Windows OCR - Windows tiếng Anh thiếu gói tiếng Việt, phải cài thêm có quyền quản trị).

Tesseract 5 (64-bit, Apache 2.0) ĐÓNG KÈM bộ cài: thư mục `tesseract\\` cạnh PABT.exe (tesseract.exe + DLL, tessdata\\vie - tiếng
Việt, osd - tự xoay trang ngang; dựng bằng bo_cai_win\\chuan_bi_tesseract.py). Tìm theo thứ tự: biến môi trường PABT_TESSERACT,
`tesseract\\` cạnh PABT.exe, bo_cai_win\\tesseract (chạy từ mã nguồn), `%APPDATA%\\PABT\\tesseract\\`, nơi cài riêng
(`C:\\Program Files\\Tesseract-OCR`), rồi PATH. Đầu ra TSV (toạ độ từng từ) -> gom_dong: các từ cùng hàng một dòng, cột cách xa nối
bằng Tab (giữ cấu trúc bảng giá / bảng phương án). Windows 32-bit không chạy được bản 64-bit: PDF có chữ, Word, Excel vẫn đọc bình
thường, chỉ bản scan là không đọc được (dán chữ từ Clipboard thay thế).
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
    goc = Path(__file__).resolve().parents[1]
    ds += [goc / 'tesseract' / exe, goc / 'bo_cai_win' / 'tesseract' / exe]      # chạy từ mã nguồn
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


def _thu_muc_du_lieu(tess: Path) -> list:
    """--tessdata-dir khi tessdata nằm cạnh tesseract.exe (bản đóng kèm): biến TESSDATA_PREFIX của bản Tesseract khác cài trên máy
    không làm lạc sang thư mục thiếu tiếng Việt."""
    td = Path(tess).parent / 'tessdata'
    return ['--tessdata-dir', str(td)] if td.is_dir() else []


def windows_64bit() -> bool:
    if sys.platform != 'win32':
        return True
    return (os.environ.get('PROCESSOR_ARCHITECTURE', '').upper().endswith('64')
            or bool(os.environ.get('PROCESSOR_ARCHITEW6432')))      # tiến trình 32-bit (bản Win7) trên Windows 64-bit


LUONG_OCR_MAY_YEU = '1'         # máy yếu (CPU 2 nhân): Tesseract chỉ dùng 1 luồng - chuột / giao diện vẫn mượt khi quét


def moi_truong_ocr() -> dict:
    """Biến môi trường cho tiến trình Tesseract: máy cấu hình yếu (csdl.la_may_yeu) giới hạn OMP_THREAD_LIMIT."""
    env = dict(os.environ)
    from .csdl import la_may_yeu
    if la_may_yeu():
        env['OMP_THREAD_LIMIT'] = LUONG_OCR_MAY_YEU
    return env


def _chay(lenh: list, cho=None, gioi_han: float = 300) -> subprocess.CompletedProcess:
    """Chạy lệnh; trong lúc chờ gọi cho() (giữ giao diện không treo, trả True = người dùng hủy)."""
    import threading
    pr = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=moi_truong_ocr(),
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    # đọc stdout / stderr SONG SONG (0.9.95): trước đây chỉ chờ tiến trình kết thúc rồi mới đọc - trang scan nhiều chữ (bảng giá,
    # bảng phương án: > ~64 KB kết quả) làm đầy ống, Tesseract chặn ghi, hai bên chờ nhau tới hết giờ ("quá lâu")
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


_NGON_NGU = {}                                          # (đường dẫn, mtime) -> ngôn ngữ: không chạy lại tesseract mỗi lần hỏi


def ngon_ngu(tess: Path | None = None) -> list:
    tess = tess or tim_tesseract()
    if tess is None:
        return []
    try:
        khoa = (str(tess), Path(tess).stat().st_mtime_ns)
    except OSError:
        return []
    if khoa not in _NGON_NGU:
        try:
            r = _chay([str(tess), *_thu_muc_du_lieu(tess), '--list-langs'], gioi_han=30)
        except (OSError, LoiOCR):
            return []                                   # không chạy được (Windows 32-bit, bị diệt virus chặn): không nhớ
        _NGON_NGU[khoa] = [x.strip() for x in (r.stdout + r.stderr).decode('utf-8', 'replace').splitlines()[1:] if x.strip()]
    return _NGON_NGU[khoa]


def _tesseract_san_sang() -> str:
    tess = tim_tesseract()
    if tess is None:
        return 'chưa có Tesseract OCR (thư mục "tesseract" cạnh PABT.exe - cài lại phần mềm bằng bộ cài mới)'
    ds = ngon_ngu(tess)
    if not ds:
        if not windows_64bit():
            return 'Windows 32-bit không chạy được bộ nhận dạng chữ Tesseract 64-bit đóng kèm'
        return f'không chạy được Tesseract ({tess}) - phần mềm diệt virus chặn hoặc thiếu file, cài lại phần mềm'
    if 'vie' not in ds:
        return f'Tesseract ({tess}) chưa có dữ liệu tiếng Việt (vie.traineddata)'
    return ''


def may_doc() -> tuple:
    """Bộ nhận dạng sẽ dùng: ('tesseract', đường dẫn) / ('', None) khi chưa đọc được bản scan tiếng Việt."""
    if not _tesseract_san_sang():
        return 'tesseract', tim_tesseract()
    return '', None


def san_sang() -> str:
    """'' nếu nhận dạng được bản scan tiếng Việt, không thì câu giải thích còn thiếu gì và cách khắc phục."""
    ly_do = _tesseract_san_sang()
    if not ly_do:
        return ''
    return ('Máy chưa nhận dạng được chữ trên bản scan: ' + ly_do + '. Có thể dán chữ (Snipping Tool, Zalo…) hoặc chọn file '
            'Excel, Word thay bản scan.')


def gom_dong(tu: list, he_so: float = 0.6) -> list:
    """[(x, y, rộng, cao, chữ)] các từ -> dòng chữ: từ có tâm dọc cách tâm hàng < he_so x chiều cao chữ là cùng hàng (bảng giá nhiều
    cột), trong hàng xếp theo x."""
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


def tu_tsv(tsv: str) -> list:
    """Đầu ra TSV của Tesseract -> [(x, y, rộng, cao, chữ)] các từ (dòng level 5, bỏ từ trống)."""
    tu = []
    for d in tsv.splitlines()[1:]:
        p = d.split('\t')
        if len(p) >= 12 and p[0] == '5' and p[11].strip():
            try:
                tu.append((int(p[6]), int(p[7]), int(p[8]), int(p[9]), p[11].strip()))
            except ValueError:
                continue
    return tu


_RE_CUM_SO = re.compile(r'(?<![^\W\d_])[\doO][\doO.,]*[\doO](?![^\W\d_])')


def sua_so(dong: str) -> str:
    """Lỗi nhận dạng hay gặp trong số tiền: chữ o / O thay số 0 ("3.500.ooo" -> "3.500.000") - chỉ sửa cụm có >= 2 chữ số và
    toàn chữ số / o / dấu ngăn (không đụng chữ "Ô", "o" trong từ)."""
    def sua(m):
        t = m.group(0)
        return t.replace('o', '0').replace('O', '0') if sum(c.isdigit() for c in t) >= 2 else t
    return _RE_CUM_SO.sub(sua, dong)


# chỉ số trên của m² trong ô ĐVT bảng scan: Tesseract đọc thành dấu độ / nháy ("m°", 'm"', "mˆ")
_RE_DVT_MU = re.compile(r'm\s*(?:[°º˚ˆ"\'’`*?²]|\^2)', re.I)


def sua_dvt(o: str) -> str:
    """Ô chỉ có ĐVT diện tích đọc lệch ("m°", 'm"', "m^2") -> "m²". Chữ khác giữ nguyên."""
    return 'm²' if len(o.strip()) <= 4 and _RE_DVT_MU.fullmatch(o.strip()) else o


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


CAO_CHU_TOI_THIEU = 24        # px: chiều cao trung vị các từ (khung chữ TSV) dưới mức này thì phóng ảnh rồi đọc lại
CAO_CHU_MUC_TIEU = 36         # px: phóng tới cỡ này (Tesseract đọc tốt chữ cao ~30-40 px; PHÓNG chữ đã đủ lớn lại đọc SAI hơn - đo
PHONG_TOI_DA = 4.0            # 16/10/2026: ảnh 42 px phóng x3 thì "Giếng" -> "Giêng", "1" -> "J")


def _chuan_bi(anh: Path, td: Path | None = None, he_so: float = 1.0) -> Path:
    """Ảnh xám (1 byte / điểm ảnh - Tesseract đọc ổn định hơn ảnh màu), phóng he_so lần khi > 1. Trả file PNG đã xử lý (hoặc ảnh
    gốc khi không xử lý được)."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
    except ImportError:
        return anh
    im = QImage(str(anh))
    if im.isNull():
        return anh
    im = im.convertToFormat(QImage.Format.Format_Grayscale8)     # xám TRƯỚC khi phóng: 1 byte / điểm ảnh thay 4 (nhanh ~3 lần)
    if he_so > 1:
        im = im.scaled(int(im.width() * he_so), int(im.height() * he_so), Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    ra = (td or anh.parent) / (anh.stem + (f'_x{he_so:g}' if he_so > 1 else '') + '_xl.png')   # td: thư mục tạm, không ghi cạnh ảnh gốc
    return ra if im.save(str(ra)) else anh


def _canh_ngan(anh: Path) -> int:
    try:
        from PySide6.QtGui import QImageReader
    except ImportError:
        return 0
    kt = QImageReader(str(anh)).size()
    return min(kt.width(), kt.height()) if kt.isValid() else 0


def he_so_phong(tu: list, canh_ngan: int = 0) -> float:
    """Hệ số phóng ảnh theo chiều cao chữ thật (trung vị khung các từ): chữ nhỏ (scan 150 dpi, ảnh chụp màn hình) phóng tới
    CAO_CHU_MUC_TIEU; không thấy chữ nào mà ảnh nhỏ (chữ quá bé, Tesseract không tách được) thì phóng như trang A4 300 dpi."""
    cao = sorted(t[3] for t in tu if t[3] > 0)
    if cao:
        h = cao[len(cao) // 2]
        return min(PHONG_TOI_DA, CAO_CHU_MUC_TIEU / h) if h < CAO_CHU_TOI_THIEU else 1.0
    if 0 < canh_ngan < 2000:                            # cạnh ngắn A4 ở 300 dpi ~ 2480 px
        return min(PHONG_TOI_DA, 2480 / canh_ngan)
    return 1.0


def _xoay(anh: Path, do: int) -> None:
    from PySide6.QtGui import QImage, QTransform
    im = QImage(str(anh))
    if not im.isNull():
        im.transformed(QTransform().rotate(do)).save(str(anh))


# ---------------------------------------------------------------- nhận dạng
def _doc_tsv(tess: Path, anh: Path, du_lieu: list, cho=None) -> list:
    try:
        r = _chay([str(tess), str(anh), '-', *du_lieu, '-l', 'vie', '--psm', '6', 'tsv'], cho)
    except OSError as e:
        raise LoiOCR(san_sang() or f'Không chạy được Tesseract: {e}') from e
    if r.returncode != 0:
        raise LoiOCR('Tesseract báo lỗi: ' + r.stderr.decode('utf-8', 'replace').strip()[:300])
    return tu_tsv(r.stdout.decode('utf-8', 'replace'))


def doc_anh(anh: Path, tess: Path | None = None, cho=None, td: Path | None = None) -> str:
    """Chữ trên một ảnh trang bằng Tesseract (trang nằm ngang tự xoay lại trước khi đọc): mỗi hàng ngang một dòng, cột cách Tab.
    Đọc ảnh xám nguyên cỡ; chữ nhỏ thì phóng theo chiều cao chữ đo được (he_so_phong) rồi đọc lại."""
    tess = tess or tim_tesseract()
    if tess is None:
        raise LoiOCR(san_sang())
    du_lieu = _thu_muc_du_lieu(tess)
    goc = Path(anh)
    anh = _chuan_bi(goc, td)
    xoay = 0
    try:
        r = _chay([str(tess), str(anh), '-', *du_lieu, '--psm', '0'], cho, 60)
        m = re.search(rb'Rotate:\s*(\d+)', r.stdout)
        if m and int(m.group(1)) in (90, 180, 270) and anh != goc:    # chỉ xoay bản đã xử lý, không ghi đè ảnh gốc
            xoay = int(m.group(1))
            _xoay(anh, xoay)
    except LoiOCR:
        raise
    except OSError:
        pass                                            # thiếu osd.traineddata: đọc nguyên chiều
    tu = _doc_tsv(tess, anh, du_lieu, cho)
    k = he_so_phong(tu, _canh_ngan(anh))
    if k > 1.15 and anh != goc:
        lon = _chuan_bi(anh, td, k)
        if lon != anh:
            tu_lon = _doc_tsv(tess, lon, du_lieu, cho)
            if len(''.join(t[4] for t in tu_lon)) >= len(''.join(t[4] for t in tu)) * 0.8:   # phóng mà đọc được ít hơn hẳn: giữ lần đầu
                tu = tu_lon
    return '\n'.join(gom_dong(tu))


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
                        yield doc_anh(p, tess, cho, td)
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
                yield doc_anh(p, tess, cho, td)
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
        dong += ['\t'.join(sua_dvt(o) for o in sua_so(x.strip()).split('\t')) for x in chu.splitlines() if x.strip()]
    return dong
