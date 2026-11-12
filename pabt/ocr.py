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

DUOI_ANH = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp')
DPI = 300
CANH_DAI_TOI_DA = 3508      # cạnh dài A4 @ 300 dpi: ảnh điện thoại / PDF scan lớn thu về cỡ này trước khi Tesseract (1.0.48)


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
        ds.append(Path(sys.executable).parent.parent / 'x64' / 'tesseract' / exe)      # zip Universal chạy ngay x86\PABT.exe: một bản Tesseract ở x64\
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


# 1.1.05 (máy mới Windows 11, người dùng 12/11/2026): Windows chặn nạp thư viện Tesseract đóng kèm (không có chữ ký số) - Smart App
# Control / chính sách kiểm soát ứng dụng (WDAC) - thì trình nạp của Windows hiện hộp "tesseract.exe - Bad Image ... Error status
# 0xc0e90002" (đứng giữa lúc cài: bước tự kiểm tra hỏi danh sách ngôn ngữ). Mã thoát của tesseract.exe khi trình nạp thất bại:
MA_BI_CHAN = 0xC0E90002        # STATUS_SYSTEM_INTEGRITY_POLICY_VIOLATION: chính sách toàn vẹn của Windows chặn file (chưa ký số)
MA_NAP_LOI = {0xC0E90002: 'chan', 0xC0E90003: 'chan', 0xC0000428: 'chan',     # chặn theo chính sách / chữ ký số
              0xC000007B: 'hong', 0xC0000135: 'hong', 0xC0000139: 'hong', 0xC0000142: 'hong',   # sai kiến trúc / thiếu / hỏng DLL
              0xC000012F: 'hong', 0xC0000130: 'hong', 0xC0000131: 'hong'}                      # file DLL không phải ảnh nạp được
SEM_FAILCRITICALERRORS, SEM_NOOPENFILEERRORBOX = 0x0001, 0x8000
_LOI_NAP = {}                  # đường dẫn tesseract.exe -> mã thoát lỗi nạp lần chạy gần nhất (san_sang dùng để báo đúng lý do)


def _tat_hop_loi_he_thong():
    """Tiến trình con thừa hưởng chế độ lỗi của tiến trình cha (SetErrorMode): bật SEM_FAILCRITICALERRORS trước khi chạy tesseract.exe
    để trình nạp KHÔNG hiện hộp lỗi hệ thống (tiến trình con thoát với mã lỗi, phần mềm báo bằng lời). Trả chế độ cũ (None: không
    phải Windows / không đặt được) để _tra_hop_loi_he_thong khôi phục ngay sau khi tạo tiến trình."""
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        cu = k32.SetErrorMode(0)                        # đọc chế độ hiện tại (SetErrorMode trả chế độ cũ)
        k32.SetErrorMode(cu | SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX)
        return cu
    except (AttributeError, OSError, ImportError):
        return None


def _tra_hop_loi_he_thong(cu) -> None:
    if cu is None:
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(cu)
    except (AttributeError, OSError, ImportError):
        pass


def loai_loi_nap(ma) -> str:
    """'chan' (Windows chặn theo chính sách / chữ ký số), 'hong' (thiếu / hỏng / sai kiến trúc DLL) hoặc '' theo mã thoát tiến trình."""
    try:
        return MA_NAP_LOI.get(int(ma) & 0xFFFFFFFF, '')
    except (TypeError, ValueError):
        return ''


def chu_loi_nap(ma, tess=None) -> str:
    """Câu giải thích khi tesseract.exe không nạp được (theo mã thoát), '' nếu không phải lỗi nạp."""
    loai = loai_loi_nap(ma)
    if loai == 'chan':
        return ('Windows đã chặn thư viện của bộ nhận dạng chữ Tesseract đóng kèm (Smart App Control hoặc chính sách kiểm soát ứng dụng '
                f'của máy chặn file chưa có chữ ký số, mã {int(ma) & 0xFFFFFFFF:#010x}). Phần mềm vẫn dùng bình thường; chỉ đọc bản scan là '
                'không được trên máy này')
    if loai == 'hong':
        return (f'không nạp được bộ nhận dạng chữ Tesseract ({tess or "tesseract.exe"}, mã {int(ma) & 0xFFFFFFFF:#010x}: thiếu hoặc hỏng '
                'file thư viện) - cài lại phần mềm')
    return ''


def _chay(lenh: list, cho=None, gioi_han: float = 300) -> subprocess.CompletedProcess:
    """Chạy lệnh; trong lúc chờ gọi cho() (giữ giao diện không treo, trả True = người dùng hủy)."""
    import threading
    cu = _tat_hop_loi_he_thong()
    try:
        pr = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=moi_truong_ocr(),
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    finally:
        _tra_hop_loi_he_thong(cu)
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
        if loai_loi_nap(r.returncode):                  # 1.1.05: Windows chặn / thiếu DLL - nhớ mã để san_sang báo đúng lý do
            _LOI_NAP[str(tess)] = r.returncode
            return []
        _LOI_NAP.pop(str(tess), None)
        _NGON_NGU[khoa] = [x.strip() for x in (r.stdout + r.stderr).decode('utf-8', 'replace').splitlines()[1:] if x.strip()]
    return _NGON_NGU[khoa]


def _tesseract_san_sang() -> str:
    tess = tim_tesseract()
    if tess is None:
        return 'chưa có Tesseract OCR (thư mục "tesseract" cạnh PABT.exe - cài lại phần mềm bằng bộ cài mới)'
    ds = ngon_ngu(tess)
    if not ds:
        nap = chu_loi_nap(_LOI_NAP.get(str(tess)), tess)
        if nap:
            return nap
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


def windows_chan() -> bool:
    """Lần chạy tesseract.exe gần nhất bị Windows chặn theo chính sách (Smart App Control / WDAC) - máy chặn, KHÔNG phải cài hỏng
    (tự kiểm tra sau khi cài coi là lưu ý, không phải lỗi)."""
    tess = tim_tesseract()
    return tess is not None and loai_loi_nap(_LOI_NAP.get(str(tess))) == 'chan'


def san_sang() -> str:
    """'' nếu nhận dạng được bản scan tiếng Việt, không thì câu giải thích còn thiếu gì và cách khắc phục."""
    ly_do = _tesseract_san_sang()
    if not ly_do:
        return ''
    return ('Máy chưa nhận dạng được chữ trên bản scan: ' + ly_do + '. Có thể dán chữ (Snipping Tool, Zalo…) hoặc chọn file '
            'Excel, Word thay bản scan.')


def gom_hang(tu: list, he_so: float = 0.6) -> list:
    """[(x, y, rộng, cao, chữ)] các từ -> các hàng ngang (từ trên xuống): mỗi hàng [(x, x cuối, cao, chữ)] xếp theo x. Từ có tâm dọc
    cách tâm hàng < he_so x chiều cao chữ là cùng hàng (bảng giá nhiều cột). Dùng cho nhập danh sách hộ từ bản scan (vị trí từng từ
    để chia cột bảng)."""
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
    return [[(x, x + w, h, t) for x, w, h, t in sorted(hg[2])] for hg in sorted(hang, key=lambda a: a[0])]


def gom_dong(tu: list, he_so: float = 0.6) -> list:
    """[(x, y, rộng, cao, chữ)] các từ -> dòng chữ (gom_hang), trong hàng xếp theo x."""
    kq = []
    for hg in gom_hang(tu, he_so):
        # 0.9.95: khoảng trống ngang > CACH_COT x chiều cao chữ = sang cột kế của bảng -> nối bằng Tab (giữ cấu trúc cột "Tên \t ĐVT
        # \t Số lượng \t Đơn giá \t Tỷ lệ \t Thành tiền" cho bóc tách bảng phương án chi tiết / bảng giá)
        chu, cuoi = '', None
        for x, x_cuoi, h, t in hg:
            if cuoi is not None:
                chu += '\t' if x - cuoi > CACH_COT * max(h, 1) else ' '
            chu += t
            cuoi = x_cuoi
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


def kich_thuoc_ocr(rong: int, cao: int, gioi: int = CANH_DAI_TOI_DA) -> tuple:
    """Kích thước đọc OCR: không vượt `gioi` ở cạnh dài (giữ tỉ lệ). Ảnh 8000×6000 → 3508×2631."""
    rong, cao = int(rong or 0), int(cao or 0)
    m = max(rong, cao)
    if m <= gioi or m <= 0:
        return max(1, rong or 1), max(1, cao or 1)
    k = gioi / m
    return max(1, int(rong * k)), max(1, int(cao * k))


def so_trang(file) -> int:
    """Số trang PDF (QtPdf / pypdf); ảnh / file khác = 1. Không mở được -> 1."""
    p = Path(file)
    duoi = p.suffix.lower()
    if duoi in DUOI_ANH or duoi != '.pdf':
        return 1
    try:
        from PySide6.QtPdf import QPdfDocument
    except ImportError:
        QPdfDocument = None
    if QPdfDocument is not None:
        d = QPdfDocument()
        try:
            d.load(str(p))
            n = int(d.pageCount() or 0)
            if n > 0:
                return n
        except Exception:                               # noqa: BLE001 - PDF hỏng: thử pypdf
            pass
        finally:
            try:
                d.close()
            except Exception:                           # noqa: BLE001
                pass
    try:
        from pypdf import PdfReader
        return max(1, len(PdfReader(str(p)).pages))
    except Exception:                                   # noqa: BLE001
        return 1


def _doc_qimage(anh: Path, gioi: int = CANH_DAI_TOI_DA):
    """Đọc ảnh; file lớn giải nén đã thu (không nạp bitmap 20–40 MP rồi mới thu — máy treo)."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QImage, QImageReader
    r = QImageReader(str(anh))
    kt = r.size()
    if kt.isValid() and max(kt.width(), kt.height()) > gioi:
        w, h = kich_thuoc_ocr(kt.width(), kt.height(), gioi)
        r.setScaledSize(QSize(w, h))
    im = r.read()
    if im is not None and not im.isNull():
        return im
    return QImage(str(anh))


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
    gốc khi không xử lý được). 1.0.48: cạnh dài không vượt CANH_DAI_TOI_DA (ảnh điện thoại / PDF scan lớn)."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
    except ImportError:
        return anh
    im = _doc_qimage(anh) if he_so <= 1 else QImage(str(anh))
    if im.isNull():
        return anh
    if im.hasAlphaChannel():                                     # PNG nền trong suốt (ảnh xuất từ phần mềm): đặt lên nền trắng, không thì chữ đen trên đen
        from PySide6.QtGui import QPainter
        nen = QImage(im.size(), QImage.Format.Format_RGB32)
        nen.fill(0xFFFFFFFF)
        pt = QPainter(nen)
        pt.drawImage(0, 0, im)
        pt.end()
        im = nen
    im = im.convertToFormat(QImage.Format.Format_Grayscale8)     # xám TRƯỚC khi phóng: 1 byte / điểm ảnh thay 4 (nhanh ~3 lần)
    if he_so > 1:
        w, h = kich_thuoc_ocr(int(im.width() * he_so), int(im.height() * he_so))
        if w > im.width() or h > im.height():
            im = im.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    elif max(im.width(), im.height()) > CANH_DAI_TOI_DA:
        w, h = kich_thuoc_ocr(im.width(), im.height())
        im = im.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
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
def _doc_tsv(tess: Path, anh: Path, du_lieu: list, cho=None, psm: int = 6, so: list | None = None) -> list:
    """Các từ (tu_tsv). so: danh sách nhận các con số dạng giá kèm độ tin cậy (so_tin_cay_tsv) - 1.1.05, chỉ khi nơi gọi cần."""
    try:
        r = _chay([str(tess), str(anh), '-', *du_lieu, '-l', 'vie', '--psm', str(psm), 'tsv'], cho)
    except OSError as e:
        raise LoiOCR(san_sang() or f'Không chạy được Tesseract: {e}') from e
    if r.returncode != 0:
        raise LoiOCR(chu_loi_nap(r.returncode, tess) or 'Tesseract báo lỗi: ' + r.stderr.decode('utf-8', 'replace').strip()[:300])
    tsv = r.stdout.decode('utf-8', 'replace')
    if so is not None:
        so[:] = so_tin_cay_tsv(tsv)
    return tu_tsv(tsv)


# ---------------------------------------------------------------- 1.1.05: neo ảnh gốc từng con số giá (kiểm định đơn giá tầng 3)
# Đọc bảng giá đất từ bản scan: mỗi con số dạng giá giữ độ tin cậy Tesseract (0-100) + ảnh cắt đúng chỗ đó trên trang đã đọc, để
# màn hình đối chiếu cho người dùng nhìn ngay số gốc của dòng bị nghi (không phải mở lại PDF). Ảnh cắt ở thư mục tạm của phiên chạy,
# xóa khi thoát; không gửi đi đâu. Chỉ chạy khi nơi gọi truyền `neo` (đọc bảng giá đất) - các đường OCR khác không đổi.
RE_SO_GIA = re.compile(r'^\(?\d{1,3}(?:[.,]\d{3})+\)?[.,;:]?$|^\(?\d{3,}\)?[.,;:]?$')
NEO_TOI_DA = 4000           # số ảnh cắt tối đa mỗi lần đọc một file
NEO_LE = 6                  # điểm ảnh lề quanh con số khi cắt
_THU_MUC_NEO = []
_DEM_NEO = [0]


def so_tin_cay_tsv(tsv: str) -> list:
    """Các từ dạng con số giá (từ 3 chữ số, có thể có dấu chấm / phẩy nghìn) trong đầu ra TSV của Tesseract:
    [(x, y, rộng, cao, chữ, độ tin cậy 0-100)]. Từ Tesseract báo -1 (không đánh giá) bỏ qua."""
    kq = []
    for d in tsv.splitlines()[1:]:
        p = d.split('\t')
        if len(p) >= 12 and p[0] == '5':
            t = p[11].strip()
            if t and RE_SO_GIA.match(t):
                try:
                    tc = float(p[10])
                    if tc >= 0:
                        kq.append((int(p[6]), int(p[7]), int(p[8]), int(p[9]), t, tc))
                except ValueError:
                    continue
    return kq


def chu_so(chu) -> str:
    """Chỉ các chữ số của một con số ('1.200' -> '1200'): khóa so con số trên ảnh với ô giá đã đọc."""
    return re.sub(r'\D', '', str(chu or ''))


def thu_muc_neo() -> Path:
    """Thư mục tạm chứa ảnh cắt của phiên chạy (tạo khi cần, xóa khi thoát phần mềm)."""
    if not _THU_MUC_NEO:
        import atexit
        _THU_MUC_NEO.append(Path(tempfile.mkdtemp(prefix='PABT_neo_')))
        atexit.register(shutil.rmtree, str(_THU_MUC_NEO[0]), True)
    return _THU_MUC_NEO[0]


def _cat_neo(anh: Path, so: list, neo: list, trang: int) -> None:
    """Cắt từng con số trong so (tọa độ trên đúng ảnh anh Tesseract vừa đọc) ra PNG nhỏ, ghi vào neo:
    {'so': chữ số, 'chu': chữ đọc được, 'tin_cay': 0-100, 'trang': số trang, 'anh': đường dẫn PNG}."""
    if not so or len(neo) >= NEO_TOI_DA:
        return
    from PySide6.QtGui import QImage
    im = QImage(str(anh))
    if im.isNull():
        return
    tm = thu_muc_neo()
    for x, y, w, h, t, tc in so:
        if len(neo) >= NEO_TOI_DA:
            break
        x0, y0 = max(0, x - NEO_LE), max(0, y - NEO_LE)
        cat = im.copy(x0, y0, min(im.width() - x0, w + 2 * NEO_LE), min(im.height() - y0, h + 2 * NEO_LE))
        _DEM_NEO[0] += 1
        f = tm / f'so_{_DEM_NEO[0]:06d}.png'
        if not cat.isNull() and cat.save(str(f)):
            neo.append({'so': chu_so(t), 'chu': t, 'tin_cay': tc, 'trang': trang, 'anh': str(f)})


def doc_anh(anh: Path, tess: Path | None = None, cho=None, td: Path | None = None, tra_ve: str = 'chu', psm: int = 6,
            neo: list | None = None, trang: int = 0):
    """Chữ trên một ảnh trang bằng Tesseract (trang nằm ngang tự xoay lại trước khi đọc): mỗi hàng ngang một dòng, cột cách Tab.
    Đọc ảnh xám nguyên cỡ; chữ nhỏ thì phóng theo chiều cao chữ đo được (he_so_phong) rồi đọc lại.
    neo (1.1.05): danh sách nhận ảnh cắt + độ tin cậy của các con số dạng giá (_cat_neo) - chỉ khi tra_ve = 'chu'."""
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
    # 30/10/2026: bảng có khung kẻ -> xóa nét kẻ trước khi đọc, chữ xếp vào ô theo khung (luoi_bang); không khung: như cũ
    luoi = None
    if tra_ve == 'chu' and anh != goc:
        sach, luoi = _xu_ly_khung(anh, td)
        if sach is not None:
            anh = sach
    so1 = [] if neo is not None and tra_ve == 'chu' else None
    tu = _doc_tsv(tess, anh, du_lieu, cho, psm, so1)
    k, he_so = he_so_phong(tu, _canh_ngan(anh)), 1.0
    lon = anh
    so_dung, anh_doc = so1, anh
    if k > 1.15 and anh != goc:
        lon = _chuan_bi(anh, td, k)
        if lon != anh:
            so2 = [] if so1 is not None else None
            tu_lon = _doc_tsv(tess, lon, du_lieu, cho, psm, so2)
            if len(''.join(t[4] for t in tu_lon)) >= len(''.join(t[4] for t in tu)) * 0.8:   # phóng mà đọc được ít hơn hẳn: giữ lần đầu
                tu, he_so = tu_lon, k
                so_dung, anh_doc = so2, lon
    if so_dung:
        _cat_neo(anh_doc, so_dung, neo, trang)
    if tra_ve == 'hang':                                # từng từ kèm vị trí (nhập danh sách hộ từ bản scan: chia cột bảng)
        return gom_hang(tu)
    if luoi is not None:
        from .luoi_bang import xep_vao_o
        tu = _doc_lai_o_gop(tess, lon, du_lieu, cho, luoi, he_so, tu, td)
        dong = []
        for loai, nd in xep_vao_o(tu, luoi, he_so):
            # chữ ngoài bảng (tiêu đề, chú thích cuối trang, số trang) MỘT ô: không bị đọc nhầm thành dòng đơn giá theo cột bảng
            dong += ['\t'.join(nd)] if loai == 'bang' else [x for x in (_bo_net(hg) for hg in gom_hang(nd)) if x]
        return '\n'.join(dong)
    return '\n'.join(gom_dong(tu))


LE_O_GOP = 12              # điểm ảnh: lề trắng thêm quanh ô / cột khi đọc lại riêng (Tesseract cần khoảng trống quanh chữ)


_RE_TU_SO = re.compile(r'^[\W\d_]*\d[\W\d_]*$')


def _cot_so(tu: list, vung: tuple, he_so: float) -> bool:
    """Cột bảng mà >= 60% số từ (đọc cả trang) là số."""
    x1, y1, x2, y2 = (v * he_so for v in vung)
    trong = [w[4] for w in tu if x1 <= w[0] + w[2] / 2 < x2 and y1 <= w[1] + w[3] / 2 < y2]
    return bool(trong) and sum(1 for t in trong if _RE_TU_SO.match(t)) >= 0.6 * len(trong)


def _bo_net(hang: list) -> str:
    """Một dòng chữ ngoài bảng bỏ mẩu nét kẻ / mép trang scan ("|", "[", "]") ở đầu, cuối dòng; dòng chỉ còn các mẩu đó: ''."""
    ds = [t for _, _, _, t in hang]
    while ds and ds[0].strip() in ('|', '||', '[', ']', '!', 'l', 'I', ')', '('):
        ds.pop(0)
    while ds and ds[-1].strip() in ('|', '||', '[', ']', '!', ')', '('):
        ds.pop()
    return ' '.join(ds)


def _doc_lai_o_gop(tess: Path, anh: Path, du_lieu: list, cho, luoi, he_so: float, tu: list, td: Path | None) -> list:
    """Đọc lại phần bảng theo khung (30/10/2026): đọc cả trang một lượt, Tesseract (chế độ khối chữ đều) hay lẫn dòng chữ của các cột
    có ô cao thấp khác nhau ("Cà ổi sapa" cạnh ô tên khác hai dòng đọc thành "Chín . map"; "Nhóm I gồm 13 loài…" giữa 14 hàng giá đọc
    thành "Ñ Ñ ii U"). Nay đọc riêng TỪNG CỘT của bảng (mỗi cột là một cột chữ đều), rồi riêng từng ô gộp nhiều hàng / nhiều cột
    (luoi_bang.vung_gop - chữ ô gộp ngang vắt qua ranh cột); từ của lượt sau thay từ của lượt trước trong cùng vùng. Lỗi một vùng: giữ
    kết quả cũ."""
    try:
        from PySide6.QtGui import QColor, QImage, QPainter
        from .luoi_bang import vung_gop
        im = QImage(str(anh))
        if im.isNull():
            return tu
        doc, ngang = luoi.doc, luoi.ngang
        cot = [(doc[j][0], ngang[0][0], doc[j + 1][0], ngang[-1][0]) for j in range(len(doc) - 1)]
        # cột SỐ (STT, đường kính, đơn giá): đọc cả trang chính xác hơn đọc riêng cột hẹp (đã thử: "313.119" đọc riêng thành
        # "313.116") - chỉ đọc riêng cột chữ
        cot = [v for v in cot if not _cot_so(tu, v, he_so)]
        vung = cot + vung_gop(luoi)
    except Exception:                                   # noqa: BLE001
        return tu
    for i, (x1, y1, x2, y2) in enumerate(vung):
        x1, y1, x2, y2 = (int(v * he_so) for v in (x1, y1, x2, y2))
        if x2 - x1 < 8 or y2 - y1 < 8:
            continue
        try:
            o = QImage(x2 - x1 + 2 * LE_O_GOP, y2 - y1 + 2 * LE_O_GOP, QImage.Format.Format_Grayscale8)
            o.fill(QColor(255, 255, 255))
            p = QPainter(o)
            p.drawImage(LE_O_GOP, LE_O_GOP, im.copy(x1, y1, x2 - x1, y2 - y1))
            p.end()
            f = (td or anh.parent) / f'{anh.stem}_o{i}.png'
            if not o.save(str(f)):
                continue
            moi = _doc_tsv(tess, f, du_lieu, cho, 6)
        except LoiOCR:
            raise
        except Exception:                               # noqa: BLE001
            continue
        moi = [(x + x1 - LE_O_GOP, y + y1 - LE_O_GOP, w, h, t) for x, y, w, h, t in moi]
        moi = [w for w in moi if x1 <= w[0] + w[2] / 2 < x2 and y1 <= w[1] + w[3] / 2 < y2]
        if not moi and i < len(cot):
            continue
        tu = [w for w in tu if not (x1 <= w[0] + w[2] / 2 < x2 and y1 <= w[1] + w[3] / 2 < y2)] + moi
    return tu


def _xu_ly_khung(anh: Path, td: Path | None):
    """(ảnh đã xoay thẳng + xóa nét kẻ, Luoi) khi trang có khung bảng; không có / lỗi: (None, None) - đọc như bảng không kẻ."""
    try:
        from PySide6.QtGui import QImage
        from .luoi_bang import nhan_khung
        im = QImage(str(anh))
        if im.isNull():
            return None, None
        sach, luoi = nhan_khung(im)
        if luoi is None:
            return None, None
        ra = (td or anh.parent) / (anh.stem + '_khung.png')
        return (ra, luoi) if sach.save(str(ra)) else (None, None)
    except Exception:                                   # noqa: BLE001
        return None, None


def tung_trang(file, bao_tien_do=None, cho=None, dpi: int = DPI, tra_ve: str = 'chu', psm: int = 6, neo: list | None = None):
    """Đọc từng trang rồi xóa ảnh trang (không dựng hết file trước — file lớn không chiếm bộ nhớ). Yield chữ từng trang.
    neo (1.1.05): danh sách nhận ảnh cắt + độ tin cậy các con số dạng giá (doc_anh) - đọc bảng giá đất."""
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
            yield doc_anh(file, tess, cho, td, tra_ve, psm, neo, 1)
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
                if bao_tien_do:
                    bao_tien_do(0, tong)                 # hiện hộp tiến độ trước khi render trang đầu (file nghìn trang)
                for i in range(tong):
                    if cho and cho():
                        raise DaHuy()
                    if bao_tien_do:
                        bao_tien_do(i + 1, tong)
                    kt = d.pagePointSize(i)
                    # PDF chụp điện thoại hay khai báo khổ trang = số điểm ảnh: 300 dpi bị phóng thành 8–20 MP → treo.
                    w, h = kich_thuoc_ocr(max(1, int(kt.width() * dpi / 72)), max(1, int(kt.height() * dpi / 72)))
                    anh = d.render(i, QSize(w, h))
                    p = td / f'trang_{i + 1:04d}.png'
                    if anh.isNull() or not anh.save(str(p)):
                        continue
                    try:
                        yield doc_anh(p, tess, cho, td, tra_ve, psm, neo, i + 1)
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
                yield doc_anh(p, tess, cho, td, tra_ve, psm, neo, i)
            finally:
                try:
                    p.unlink()
                except OSError:
                    pass
    finally:
        shutil.rmtree(td, ignore_errors=True)


_DA_DOC = {}                # (đường dẫn, mtime, cỡ, psm) -> các dòng; vừa đọc gần nhất ở cuối
_DA_DOC_TOI_DA = 6


def doc_chu(file, bao_tien_do=None, cho=None, psm: int = 6) -> list:
    """Các dòng chữ của bản scan (PDF ảnh hoặc file ảnh). bao_tien_do(trang, tổng số trang); cho() trả True để hủy.
    psm: chế độ Tesseract (6 = khối chữ; 4 = cột thưa — biên bản viết tay). Nhớ TRONG BỘ NHỚ vài file vừa đọc (theo đường dẫn, thời điểm sửa,
    cỡ): bộ quét chung nhận loại rồi màn hình chuyên trách đọc lại không phải nhận dạng lại. Không ghi đĩa."""
    if not may_doc()[0]:
        raise LoiOCR(san_sang())
    try:
        st = os.stat(str(file))
        khoa = (os.path.abspath(str(file)), st.st_mtime_ns, st.st_size, psm)
    except OSError:
        khoa = None
    if khoa in _DA_DOC:
        return list(_DA_DOC[khoa])
    dong = []
    for chu in tung_trang(file, bao_tien_do, cho, psm=psm):
        # strip chỉ dấu cách: ô trống đầu dòng bảng (Tab đầu) phải giữ, không thì lệch cột
        dong += ['\t'.join(sua_dvt(o.strip()) for o in sua_so(x.strip(' \r')).split('\t')) for x in chu.splitlines() if x.strip()]
    if khoa is not None:
        while len(_DA_DOC) >= _DA_DOC_TOI_DA:
            _DA_DOC.pop(next(iter(_DA_DOC)))
        _DA_DOC[khoa] = list(dong)
    return dong
