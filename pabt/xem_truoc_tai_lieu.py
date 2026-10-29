"""Khung xem trước tài liệu A4 nằm ngay trong cửa sổ (0.9.84, người dùng 14/10/2026): HopIn (luôn hiện, nửa phải) và CuaSoLapPA
(bật / tắt bằng F4).

Bản xem trước là ĐÚNG bản in: phần mềm lập file Excel theo mẫu (in_an.lap_chi_tiet - luồng giao diện, đo chữ bằng Qt) rồi nhờ
Microsoft Excel xuất PDF (in_an.chay_excel - chỉ là tiến trình con, chạy ở LUỒNG NỀN, giao diện không đứng). Excel mất vài giây
mỗi lần: yêu cầu mới trong lúc đang xuất thì chỉ giữ yêu cầu MỚI NHẤT; bấm liên tục (mũi tên lên / xuống trong danh sách) chờ
ngừng tay CHO_MS mới lập. Kết quả nhớ theo khóa (hộ, chế độ, mẫu…) trong phiên.
Từ 22/10/2026 (1.0.14) phương án chi tiết là bản WORD (in_word.xuat_chi_tiet_docx - mẫu chuẩn duy nhất): hàm lập trả file .docx,
Microsoft Word xuất PDF (van_ban_trinh.chay_word, luồng nền); máy không dùng được Word -> bản gần đúng bằng Qt từ file Excel do
tao_du_phong lập (pdf_du_phong, lề NĐ 30). Bảng tổng hợp vẫn là file Excel.

Hiển thị: QPdfView (PySide6.QtPdfWidgets) trên nền tối; máy không có QtPdfWidgets thì vẽ từng trang bằng QPdfDocument (ảnh trang
trắng giữa nền tối, có bóng đổ); bản Qt5 (Win 7/8, không có QtPdf) chỉ báo và mở PDF bằng trình xem của Windows.
File tạm ở %TEMP%\\pabt_preview\\<pid>_<n>\\ - xóa khi cửa sổ đóng (don_dep / khung bị hủy), còn sót thì xóa lúc thoát phần mềm
và lần mở sau (thư mục cũ hơn 12 giờ).
"""
from __future__ import annotations
import atexit
import itertools
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QStackedWidget, QVBoxLayout, QWidget)

THU_MUC_GOC = Path(tempfile.gettempdir()) / 'pabt_preview'
MAU_NEN = '#334155'             # vùng trang (1.0.02: slate 700 - trước #1E293B quá tối cạnh giao diện sáng)
MAU_THANH = '#F8FAFC'           # thanh công cụ xem trước (nền slate nhạt, vạch dưới #CBD5E1)
MAU_ICON_XT = '#1E3A8A'         # biểu tượng nút thanh công cụ
CAO_NUT_XT = 28
MAU_GIAY = '#FFFFFF'
CHO_MS = 250                    # chờ ngừng bấm (đổi hộ bằng phím mũi tên) rồi mới lập bản xem trước
NHIP_MS = 150                   # nhịp kiểm tra luồng nền đã xuất PDF xong chưa
CHO_EXCEL_GIAY = 90             # một file xem trước Excel không xuất xong trong chừng này (cộng thời gian khởi động): báo lỗi
PHONG_TO = (0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0)
GIU_GIO = 12                    # thư mục xem trước (của lần chạy khác) cũ hơn chừng này thì xóa

_dem = itertools.count(1)
_PHIEN: set = set()             # thư mục tạm của lần chạy này (xóa lúc thoát nếu còn)


def _xoa(p) -> None:
    shutil.rmtree(str(p), ignore_errors=True)
    _PHIEN.discard(str(p))


@atexit.register
def _xoa_het_phien() -> None:
    for p in list(_PHIEN):
        _xoa(p)


def don_thu_muc_cu(gio: float = GIU_GIO) -> None:
    """Xóa thư mục xem trước của những lần chạy trước (máy tắt đột ngột, phần mềm bị dừng) cũ hơn gio giờ."""
    if not THU_MUC_GOC.is_dir():
        return
    moc = time.time() - gio * 3600
    for d in THU_MUC_GOC.iterdir():
        try:
            if d.is_dir() and str(d) not in _PHIEN and d.stat().st_mtime < moc:
                shutil.rmtree(str(d), ignore_errors=True)
        except OSError:
            pass


def thu_muc_moi() -> Path:
    don_thu_muc_cu()
    p = THU_MUC_GOC / f'{os.getpid()}_{next(_dem)}'
    p.mkdir(parents=True, exist_ok=True)
    _PHIEN.add(str(p))
    return p


def co_qpdfview() -> bool:
    try:
        from PySide6.QtPdfWidgets import QPdfView  # noqa: F401
        return True
    except ImportError:
        return False


def co_hop_in() -> bool:
    """Hộp chọn máy in (QPrintDialog) + vẽ trang PDF bằng QtPdf: bản Qt 6. Bản Qt 5 (Win 7) không có QtPdf -> chỉ "In nhanh"."""
    if not co_qtpdf():
        return False
    try:
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter  # noqa: F401
        return True
    except ImportError:
        return False


DPI_XEM_MAY_YEU = 120           # 1.0.08: máy cấu hình yếu - ảnh trang xem trước tối đa 120 dpi (in thật vẫn DPI_IN_TOI_DA)
DPI_IN_TOI_DA = 300             # ảnh trang gửi máy in: đủ nét cho chữ, không dựng ảnh 600 dpi (A4 ngang ~140 MB)


def la_may_yeu() -> bool:
    from .csdl import la_may_yeu as f
    return f()


def he_so_xem_toi_da() -> float:
    """Hệ số phóng tối đa của khung xem trước: máy yếu = ảnh trang <= DPI_XEM_MAY_YEU (QPdfView: hệ số 1 = dpi logic màn hình)."""
    if not la_may_yeu():
        return 100.0
    man = QGuiApplication.primaryScreen()
    dpi = man.logicalDotsPerInch() if man is not None else 96
    return max(0.25, DPI_XEM_MAY_YEU / max(1.0, dpi))



def in_tai_lieu(doc, printer, tu: int = 0, den: int = 0) -> int:
    """Vẽ các trang của QPdfDocument lên máy in (trang tu..den, đánh số từ 1; 0 = cả tài liệu). Bản PDF đã có sẵn lề của mẫu ->
    in cả tờ giấy (fullPage), giữ tỉ lệ, canh giữa; hướng giấy theo từng trang. Máy in không tự in nhiều bản thì in lặp. Trả số
    trang đã in."""
    from PySide6.QtCore import QRectF, QSize
    from PySide6.QtGui import QPageLayout, QPainter
    n = doc.pageCount()
    if n <= 0:
        return 0
    tu = max(1, tu or 1)
    den = min(n, den or n)
    if tu > den:
        return 0
    ban = 1 if printer.supportsMultipleCopies() else max(1, printer.copyCount())
    printer.setFullPage(True)

    def huong(i):
        co = doc.pagePointSize(i)
        return QPageLayout.Orientation.Landscape if co.width() > co.height() else QPageLayout.Orientation.Portrait
    printer.setPageOrientation(huong(tu - 1))
    p = QPainter()
    if not p.begin(printer):
        raise OSError('Không mở được máy in ' + (printer.printerName() or ''))
    da_in = 0
    try:
        dpi = min(DPI_IN_TOI_DA, printer.resolution() or DPI_IN_TOI_DA)
        dau = True
        for _ in range(ban):
            for i in range(tu - 1, den):
                if not dau:
                    printer.setPageOrientation(huong(i))
                    printer.newPage()
                dau = False
                co = doc.pagePointSize(i)
                anh = doc.render(i, QSize(max(1, round(co.width() / 72 * dpi)), max(1, round(co.height() / 72 * dpi))))
                vp = p.viewport()
                p.setWindow(vp)
                k = min(vp.width() / anh.width(), vp.height() / anh.height())
                w, h = anh.width() * k, anh.height() * k
                p.drawImage(QRectF(vp.x() + (vp.width() - w) / 2, vp.y() + (vp.height() - h) / 2, w, h), anh)
                da_in += 1
    finally:
        p.end()
    return da_in


def in_co_hop_thoai(cha, doc, ten: str = '', printer=None, hoi: bool = True) -> int:
    """Nút "In…": hộp in của Windows như Word / Excel - chọn máy in, số bản, trang in, thuộc tính máy in; bấm In thì gửi bản
    đang xem. hoi=False (kiểm thử): dùng printer đưa vào, không hiện hộp. Trả số trang đã in (0 = hủy / không in)."""
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
    from .giao_dien import con_tro_cho
    from .thong_bao import TEN_UD, chu_loi
    n = doc.pageCount() if doc is not None else 0
    if n <= 0:
        return 0
    if printer is None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setDocName(ten or TEN_UD)
    if hoi:
        hop = QPrintDialog(printer, cha)
        hop.setWindowTitle('In – ' + (ten or TEN_UD))
        hop.setMinMax(1, n)
        hop.setFromTo(1, n)
        hop.setOption(QAbstractPrintDialog.PrintDialogOption.PrintPageRange, True)
        hop.setOption(QAbstractPrintDialog.PrintDialogOption.PrintCurrentPage, False)
        hop.setOption(QAbstractPrintDialog.PrintDialogOption.PrintSelection, False)
        if hop.exec() != QPrintDialog.DialogCode.Accepted:
            return 0
    tu, den = (printer.fromPage(), printer.toPage()) if printer.printRange() == QPrinter.PrintRange.PageRange else (0, 0)
    try:
        with con_tro_cho():
            return in_tai_lieu(doc, printer, tu, den)
    except Exception as e:
        if hoi:
            QMessageBox.warning(cha, TEN_UD, chu_loi('Chưa in được', e))
            return 0
        raise


def co_qtpdf() -> bool:
    try:
        from PySide6.QtPdf import QPdfDocument  # noqa: F401
        return True
    except ImportError:
        return False


def dung_duoc_excel() -> str:
    """'' nếu tạo được bản xem trước bằng Excel, không thì lý do. Môi trường không màn hình (kiểm thử offscreen) không tự mở
    Excel - đặt PABT_XEM_TRUOC_EXCEL=1 để cho phép. Gọi ở luồng giao diện."""
    from . import in_an
    if not in_an.co_excel():
        return 'Xem trước A4 cần Microsoft Excel trên máy Windows.'
    if QGuiApplication.platformName() in ('offscreen', 'minimal') and os.environ.get('PABT_XEM_TRUOC_EXCEL') != '1':
        return 'Xem trước A4 không mở Excel khi chạy không có màn hình (kiểm thử).'
    return ''


def dung_duoc_word() -> str:
    """'' nếu tạo được bản xem trước bằng Microsoft Word, không thì lý do (như dung_duoc_excel: không màn hình thì không tự mở
    Word - PABT_XEM_TRUOC_EXCEL=1 cho phép cả Word). Gọi ở luồng giao diện."""
    from .van_ban_trinh import co_word
    if not co_word():
        return 'Xem trước A4 cần Microsoft Word trên máy Windows.'
    if QGuiApplication.platformName() in ('offscreen', 'minimal') and os.environ.get('PABT_XEM_TRUOC_EXCEL') != '1':
        return 'Xem trước A4 không mở Word khi chạy không có màn hình (kiểm thử).'
    return ''


def la_word(f) -> bool:
    return f is not None and Path(f).suffix.lower() == '.docx'


def chuyen_pdf(xlsx: Path, pdf: Path) -> str:
    """Excel (file .xlsx) / Word (file .docx) xuất PDF - CHẠY Ở LUỒNG NỀN (chỉ gọi tiến trình con, không đụng Qt). Trả '' khi đã
    có PDF, không thì lý do."""
    from . import in_an
    if la_word(xlsx):
        from .van_ban_trinh import LoiNhap, chay_word
        try:
            loi = chay_word([('pdf', Path(xlsx), Path(pdf))], cho_moi_file=CHO_EXCEL_GIAY)
        except LoiNhap as e:
            return str(e)
        except OSError as e:
            return f'Không chạy được Microsoft Word: {e}'
        if Path(pdf).exists():
            return ''
        return 'Word không xuất được PDF: ' + ('; '.join(x.replace('\t', ' – ') for x in loi[:2]) or 'không rõ lý do')
    try:
        loi = in_an.chay_excel([(xlsx, pdf)], 'pdf', cho_moi_file=CHO_EXCEL_GIAY)
    except in_an.LoiIn as e:
        return str(e)
    except OSError as e:
        return f'Không chạy được Microsoft Excel: {e}'
    if Path(pdf).exists():
        return ''
    if any('KHONG_CO_EXCEL' in x for x in loi):
        return 'Máy chưa cài Microsoft Excel: không tạo được bản xem trước A4.'
    return 'Excel không xuất được PDF: ' + ('; '.join(x.replace('\t', ' – ') for x in loi[:2]) or 'không rõ lý do')


def gop_pdf_muc(ds_pdf: list, pdf: Path) -> list:
    """Gộp các PDF (theo thứ tự [(file pdf, nhãn)]) thành một file; trả mục lục [(nhãn, trang đầu - 0 là trang 1)]. Không đụng Qt."""
    from pypdf import PdfReader, PdfWriter
    w, muc_luc, trang = PdfWriter(), [], 0
    for f, nhan in ds_pdf:
        n = len(PdfReader(str(f)).pages)
        w.append(str(f))
        muc_luc.append((nhan, trang))
        trang += n
    with open(pdf, 'wb') as h:
        w.write(h)
    return muc_luc


def chuyen_pdf_nhieu(muc: list, pdf: Path) -> tuple:
    """Xem trước NHIỀU HỘ trên một bản (24/10/2026): muc = [(file .docx / .xlsx, nhãn)] -> (lý do lỗi hoặc '', mục lục [(nhãn, trang đầu)]).
    Word / Excel xuất PDF từng file trong MỘT lần mở ứng dụng, rồi gộp theo thứ tự. Một số file lỗi: vẫn gộp phần còn lại, báo số file thiếu.
    CHẠY Ở LUỒNG NỀN (không đụng Qt)."""
    from . import in_an
    from .van_ban_trinh import LoiNhap, chay_word
    word = [(Path(f), t) for f, t in muc if la_word(f)]
    excel = [(Path(f), t) for f, t in muc if not la_word(f)]
    loi = []
    try:
        if word:
            loi += chay_word([('pdf', f, f.with_suffix('.pdf')) for f, _ in word], cho_moi_file=CHO_EXCEL_GIAY)
        if excel:
            loi += in_an.chay_excel([(f, f.with_suffix('.pdf')) for f, _ in excel], 'pdf', cho_moi_file=CHO_EXCEL_GIAY)
    except (LoiNhap, in_an.LoiIn) as e:
        return str(e), []
    except OSError as e:
        return f'Không chạy được Microsoft Word / Excel: {e}', []
    co = [(Path(f).with_suffix('.pdf'), t) for f, t in muc if Path(f).with_suffix('.pdf').exists()]
    if not co:
        return 'Word / Excel không xuất được PDF: ' + ('; '.join(x.replace('\t', ' - ') for x in loi[:2]) or 'không rõ lý do'), []
    try:
        muc_luc = gop_pdf_muc(co, Path(pdf))
    except Exception as e:                              # noqa: BLE001 - pypdf báo nhiều loại lỗi
        return f'Không gộp được các bản xem trước: {e}', []
    return '', muc_luc


def in_qua_excel(cha, pdf, xlsx, hoi: bool = True) -> bool:
    """Nút "In nhanh": gửi bản đang xem (file của bản in - .xlsx: Excel in, .docx: Word in - đúng lề / khổ giấy) tới máy in
    mặc định. Hỏi trước (gửi máy in là việc không rút lại được). True nếu đã gửi."""
    from PySide6.QtWidgets import QMessageBox
    from . import in_an
    from .giao_dien import chay_nen
    from .lap_pa import LoiNhap
    from .thong_bao import TEN_UD
    if xlsx is None or not Path(xlsx).exists():
        return False
    if hoi and QMessageBox.question(cha, TEN_UD, f'Gửi bản đang xem trước ({Path(xlsx).stem}) tới máy in mặc định của Windows?') \
            != QMessageBox.StandardButton.Yes:
        return False
    try:
        if la_word(xlsx):
            from .van_ban_trinh import chay_word
            loi = chay_nen(cha, lambda: chay_word([('in:1', Path(xlsx), None)], cho_moi_file=CHO_EXCEL_GIAY),
                           'Microsoft Word đang gửi bản in tới máy in…')
        else:
            loi = chay_nen(cha, lambda: in_an.chay_excel([(Path(xlsx), '')], 'in'), 'Microsoft Excel đang gửi bản in tới máy in…')
    except (in_an.LoiIn, LoiNhap) as e:
        QMessageBox.warning(cha, TEN_UD, str(e))
        return False
    if loi:
        QMessageBox.warning(cha, TEN_UD, 'Chưa in được:\n' + '\n'.join(x.replace('\t', ' – ') for x in loi[:5]))
        return False
    return True


# ---------------------------------------------------------------- hiển thị dự phòng: vẽ trang bằng QPdfDocument
class _TrangAnh(QScrollArea):
    """Thay QPdfView khi máy không có QtPdfWidgets: mỗi trang một ảnh, giấy trắng giữa nền tối, bóng đổ."""
    LE = 24
    BONG = 6

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.he_so = 1.0
        self.vua_trang = True
        self.trang = 0
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb = QLabel()
        self.lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb.setStyleSheet(f'QLabel {{ background: {MAU_NEN}; }}')
        self.setWidget(self.lb)
        self.setStyleSheet(f'QScrollArea {{ background: {MAU_NEN}; border: none; }}')

    def ve(self):
        if self.doc is None or self.doc.pageCount() <= 0:
            self.lb.clear()
            return
        co = self.doc.pagePointSize(self.trang)
        if self.vua_trang:
            vung = self.viewport().size()
            k = max(0.1, min((vung.width() - 2 * self.LE) / max(1.0, co.width()),
                             (vung.height() - 2 * self.LE) / max(1.0, co.height())))
        else:
            k = self.he_so * self.logicalDpiX() / 72
        if la_may_yeu():                                 # máy yếu: ảnh trang không quá DPI_XEM_MAY_YEU (tiết kiệm RAM đồ họa)
            k = min(k, DPI_XEM_MAY_YEU / 72)
        rong, cao = max(1, int(co.width() * k)), max(1, int(co.height() * k))
        anh = self.doc.render(self.trang, QSize(rong, cao))
        pm = QPixmap(rong + 2 * self.LE, cao + 2 * self.LE)
        pm.fill(QColor(MAU_NEN))
        p = QPainter(pm)
        for i in range(self.BONG, 0, -1):                # bóng đổ: các lớp mờ dần lệch xuống / phải
            p.fillRect(self.LE + i, self.LE + i, rong, cao, QColor(0, 0, 0, 18 + 6 * (self.BONG - i)))
        p.fillRect(self.LE, self.LE, rong, cao, QColor(MAU_GIAY))
        p.drawImage(self.LE, self.LE, anh)
        p.end()
        self.lb.setPixmap(pm)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.vua_trang:
            self.ve()


# ---------------------------------------------------------------- khung xem trước
class KhungXemTruocTaiLieu(QFrame):
    """Thanh công cụ (phóng to / thu nhỏ / vừa trang | trang ◀ k / N ▶ | In nhanh) + vùng xem PDF nền tối.

    nap_tai_lieu(pdf): mở PDF, về trang 1. yeu_cau(khoa, tao_xlsx, ten, tao_du_phong=): lập bản xem trước ở nền (tao_xlsx(thu_muc)
    -> file .xlsx / .docx, gọi ở luồng giao diện; Excel / Word xuất PDF ở luồng nền; tao_du_phong(thu_muc) -> .xlsx cho bản gần
    đúng khi file .docx mà Word không dùng được). self.xlsx = file bản in đang xem (.xlsx hoặc .docx). ham_in(pdf, xlsx): nút In
    nhanh (None: nút ẩn). don_dep(): đóng tài liệu, xóa file tạm."""

    def __init__(self, parent=None, ham_in=None):
        super().__init__(parent)
        self.setObjectName('khung_xem_truoc')
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f'QFrame#khung_xem_truoc {{ background: {MAU_NEN}; border: 1px solid #CBD5E1; border-radius: 6px; }}'
                           f'QWidget#xt_thanh {{ background: {MAU_THANH}; border: 0; border-bottom: 1px solid #CBD5E1; '
                           'border-top-left-radius: 6px; border-top-right-radius: 6px; }'
                           f'QLabel#xt_thong_bao {{ color: #E2E8F0; font-size: 13px; padding: 24px; }}'
                           'QLabel#xt_trang { color: #334155; font-weight: 600; padding: 0 6px; background: transparent; }'
                           'QLabel#xt_gan_dung { color: #78350F; background: #FEF3C7; border: 1px solid #FCD34D; border-radius: 4px; '
                           'padding: 1px 6px; }'
                           'QPushButton[xem_truoc="1"] { color: #0F172A; background: #FFFFFF; border: 1px solid #CBD5E1; '
                           'border-radius: 5px; padding: 0 8px; font-weight: 600; }'
                           'QPushButton[xem_truoc="1"]:hover { background: #F1F5F9; border-color: #94A3B8; }'
                           'QPushButton[xem_truoc="1"]:pressed { background: #E2E8F0; }'
                           'QPushButton[xem_truoc="1"]:disabled { color: #94A3B8; background: #F8FAFC; border-color: #E2E8F0; }'
                           # nút "Mở bằng trình xem PDF" nằm giữa vùng trang tối: nền trắng, chữ navy
                           'QPushButton#xt_mo_ngoai { color: #1E3A8A; }')
        self.ham_in = ham_in
        self._vua = True                       # đang ở chế độ vừa trang: đổi cỡ khung thì vừa lại
        self.pdf: Path | None = None
        self.xlsx: Path | None = None
        self.thu_muc: Path | None = None
        self._nho: dict = {}                   # khóa -> (pdf, xlsx) đã lập trong phiên (xem nhiều hộ: xlsx = None)
        self._nho_muc: dict = {}               # khóa -> mục lục [(nhãn hộ, trang đầu)] của bản xem nhiều hộ
        self.muc_luc: list = []                # mục lục của bản đang xem (rỗng: bản một hộ)
        self._cho = None                       # yêu cầu chờ lập: (khóa, tao_xlsx, tên)
        self._dang = None                      # đang xuất ở nền: dict(khoa, xlsx, pdf, ten, ket_qua)
        self._so = itertools.count(1)
        self._buf = None                       # QBuffer giữ nội dung PDF đang xem (không khóa file)
        # tab hộ đóng bằng deleteLater (không có closeEvent): khung bị hủy thì xóa thư mục tạm - lambda chỉ giữ danh sách, không giữ self
        self._thu_muc_tao: list = []
        self.destroyed.connect(lambda *_a, ds=self._thu_muc_tao: [_xoa(x) for x in ds])
        self.doc = None
        self.view = None
        self.kieu = 'thong_bao'                # qpdfview / anh / thong_bao (Qt5: không có QtPdf)
        # ---- thanh công cụ
        from .giao_dien import icon_ky_hieu

        def nut(chu, ma, goi_y, ham):
            b = QPushButton(chu)
            b.setProperty('xem_truoc', '1')
            b.setProperty('khong_icon', True)
            b.setToolTip(goi_y)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(CAO_NUT_XT)
            ic = icon_ky_hieu(ma, MAU_ICON_XT, 14)     # Segoe MDL2 (Win 7 không có phông: chỉ chữ, không emoji)
            if ic is not None:
                b.setIcon(ic)
                if chu in ('+', '−', '◀', '▶'):        # có biểu tượng: nút gọn chỉ biểu tượng (khung hẹp 520 điểm)
                    b.setText('')
            b.clicked.connect(ham)
            return b
        self.b_phong = nut('+', 0xE8A3, 'Phóng to', lambda: self.phong_to(1))
        self.b_thu = nut('−', 0xE71F, 'Thu nhỏ', lambda: self.phong_to(-1))
        self.b_vua = nut('Vừa trang', 0xE9A6, 'Hiện trọn một trang trong khung', lambda: self.vua_trang())
        self.b_ngang = nut('Vừa ngang', 0xE9A6, 'Hiện trang vừa bề ngang khung (chữ to, đọc được; cuộn xuống xem các trang sau)', lambda: self.vua_ngang())
        self.b_truoc = nut('◀', 0xE76B, 'Trang trước', lambda: self.sang_trang(-1))
        self.b_sau = nut('▶', 0xE76C, 'Trang sau', lambda: self.sang_trang(1))
        self.lb_trang = QLabel('0 / 0')
        self.lb_trang.setObjectName('xt_trang')
        from PySide6.QtWidgets import QComboBox
        self.cb_muc = QComboBox()                # xem nhiều hộ: nhảy tới hộ (trang đầu của hộ)
        self.cb_muc.setToolTip('Nhảy tới phương án của hộ trong bản xem trước gộp nhiều hộ')
        self.cb_muc.setMinimumWidth(180)
        self.cb_muc.activated.connect(lambda i: self.den_muc(i))
        # bản dựng dự phòng bằng Qt (không có Excel / Excel lỗi): nhắc là bản gần đúng
        from .pdf_du_phong import NHAN_GAN_DUNG
        self.lb_gan_dung = QLabel('Bản gần đúng')
        self.lb_gan_dung.setObjectName('xt_gan_dung')
        self.lb_gan_dung.setToolTip(NHAN_GAN_DUNG + ': dựng bằng phần mềm khi máy không dùng được Microsoft Word / Excel - ngắt '
                                    'trang có thể khác bản in chính thức. In / xuất PDF chính thức cần Microsoft Office.')
        self.lb_gan_dung.setVisible(False)
        self.gan_dung = False
        self.ly_do_gan_dung = ''
        self.b_in = nut('In nhanh', 0xE749, 'In bản đang xem ra máy in mặc định (qua Microsoft Word / Excel)',
                        lambda: self.in_nhanh())
        # 16/10/2026: hộp chọn máy in như Word / Excel (máy in, số bản, trang in) - bản Qt 6 (vẽ trang bằng QtPdf)
        self.b_in_hop = nut('In…', 0xE749, 'Chọn máy in, số bản, trang cần in rồi in bản đang xem (Ctrl+P)',
                            lambda: self.in_hop_thoai())
        from PySide6.QtGui import QKeySequence, QShortcut
        self._phim_in = QShortcut(QKeySequence('Ctrl+P'), self)
        self._phim_in.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._phim_in.activated.connect(lambda: self.b_in_hop.isEnabled() and self.in_hop_thoai())
        # thanh công cụ: 3 cụm trong XepDong - khung hẹp (màn hình nhỏ) thì cụm sau xuống dòng, không cắt chữ nút
        from .giao_dien import XepDong
        self.thanh = QWidget()
        self.thanh.setObjectName('xt_thanh')
        self.thanh.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        h = XepDong(self.thanh, 10)
        h.setContentsMargins(8, 4, 8, 4)
        nhan = QLabel('Trang')
        nhan.setObjectName('xt_trang')
        for nhom, phai in (((self.b_phong, self.b_thu, self.b_vua, self.b_ngang), False), ((nhan, self.b_truoc, self.lb_trang, self.b_sau, self.cb_muc), False),
                           ((self.lb_gan_dung, self.b_in_hop, self.b_in), True)):
            cum = QWidget()
            hc = QHBoxLayout(cum)
            hc.setContentsMargins(0, 0, 0, 0)
            hc.setSpacing(4)
            if phai:
                hc.addStretch(1)
            for w in nhom:
                hc.addWidget(w)
            if not phai:
                hc.addStretch(1)
            h.addWidget(cum)
        # 1.0.16: ẩn / hiện nút SAU khi đã đặt vào bố cục - setVisible(True) lên widget CHƯA có cha làm nó hiện thành cửa sổ riêng rỗng
        # (nút thu nhỏ / phóng to / đóng, tiêu đề "PABT") nhấp nháy mỗi lần mở khung xem trước F4
        self.b_in.setVisible(ham_in is not None)
        self.cb_muc.setVisible(False)
        self.b_in_hop.setVisible(co_hop_in())
        # ---- vùng xem
        self.lb_tb = QLabel('Chọn một hộ để xem trước bản in A4.')
        self.lb_tb.setObjectName('xt_thong_bao')
        self.lb_tb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_tb.setWordWrap(True)
        self.b_mo_ngoai = QPushButton('Mở bằng trình xem PDF của Windows')
        self.b_mo_ngoai.setProperty('xem_truoc', '1')
        self.b_mo_ngoai.setObjectName('xt_mo_ngoai')
        self.b_mo_ngoai.setMinimumHeight(CAO_NUT_XT)
        self.b_mo_ngoai.clicked.connect(lambda: self.mo_ngoai())
        self.b_mo_ngoai.setVisible(False)
        tb = QWidget()
        lo_tb = QVBoxLayout(tb)
        lo_tb.addStretch(1)
        lo_tb.addWidget(self.lb_tb)
        lo_tb.addWidget(self.b_mo_ngoai, 0, Qt.AlignmentFlag.AlignHCenter)
        lo_tb.addStretch(1)
        self.ngan = QStackedWidget()
        self.ngan.addWidget(tb)
        self._dung_vung_xem()
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        lo.addWidget(self.thanh)
        lo.addWidget(self.ngan, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._hen = QTimer(self)                  # chờ ngừng bấm
        self._hen.setSingleShot(True)
        self._hen.timeout.connect(self._bat_dau)
        self._nhip = QTimer(self)                 # kiểm tra luồng nền
        self._nhip.setInterval(NHIP_MS)
        self._nhip.timeout.connect(self._kiem_nen)
        self._bat_nut()

    def _dung_vung_xem(self):
        if not co_qtpdf():
            return
        from PySide6.QtPdf import QPdfDocument
        self.doc = QPdfDocument(self)
        if co_qpdfview():
            from PySide6.QtGui import QPalette
            from PySide6.QtPdfWidgets import QPdfView
            self.view = QPdfView()
            self.view.setDocument(self.doc)
            self.view.setPageMode(QPdfView.PageMode.MultiPage)
            self.view.setZoomMode(QPdfView.ZoomMode.Custom)     # FitInView của Qt chỉ vừa bề ngang: tự tính (_he_so_vua)
            self.view.setPageSpacing(16)
            self.view.setFrameShape(QFrame.Shape.NoFrame)
            pal = self.view.palette()
            for vai in (QPalette.ColorRole.Dark, QPalette.ColorRole.Window, QPalette.ColorRole.Base):
                pal.setColor(vai, QColor(MAU_NEN))
            self.view.setPalette(pal)
            self.view.viewport().setPalette(pal)
            self.view.setStyleSheet(f'QPdfView {{ background: {MAU_NEN}; border: none; }}')
            self.view.pageNavigator().currentPageChanged.connect(lambda _: self._doi_trang())
            self.view.installEventFilter(self)
            self.kieu = 'qpdfview'
        else:
            self.view = _TrangAnh(self.doc)
            self.kieu = 'anh'
        self.ngan.addWidget(self.view)

    # ---- tài liệu
    def so_trang(self) -> int:
        return self.doc.pageCount() if self.doc is not None and self.pdf is not None else 0

    def trang_hien_tai(self) -> int:
        """Trang đang xem (0 = trang đầu)."""
        if self.so_trang() == 0:
            return 0
        if self.kieu == 'qpdfview':
            return self.view.pageNavigator().currentPage()
        return self.view.trang

    def nap_tai_lieu(self, duong_dan_pdf) -> bool:
        """Mở PDF lên khung, về trang 1. False nếu không đọc được (đã báo trong khung)."""
        p = Path(duong_dan_pdf)
        self.pdf = p
        if self.doc is None:                                    # Qt5: không có QtPdf
            self.bao(f'Đã tạo bản xem trước:\n{p.name}', mo_ngoai=True)
            return True
        self.doc.close()
        # nạp từ bộ nhớ: doc.load(đường dẫn) giữ khóa file PDF tới khi tắt phần mềm (doc.close() không nhả - Windows báo "đang
        # được dùng", thư mục tạm không xóa được)
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        try:
            du_lieu = p.read_bytes()
        except OSError as e:
            self.pdf = None
            self.bao(f'Không đọc được file PDF:\n{p.name}\n{e}')
            return False
        self._tha_buf()
        self._buf = QBuffer(self)
        self._buf.setData(QByteArray(du_lieu))
        self._buf.open(QIODevice.OpenModeFlag.ReadOnly)
        self.doc.load(self._buf)
        if self.doc.pageCount() <= 0:
            self.pdf = None
            self.bao(f'Không đọc được file PDF:\n{p.name}', mo_ngoai=False)
            return False
        self.ngan.setCurrentWidget(self.view)
        if self.kieu == 'qpdfview':
            if self._vua:
                self.view.setZoomFactor(self._he_so_vua())
            self.view.pageNavigator().jump(0, QPointF(), self.view.zoomFactor())
        else:
            self.view.trang = 0
            self.view.ve()
        self._bat_nut()
        return True

    def _tha_buf(self) -> None:
        if self._buf is not None:
            self._buf.close()
            self._buf.deleteLater()
            self._buf = None

    def bao(self, chu: str, mo_ngoai: bool = False) -> None:
        """Hiện chữ giữa khung (đang lập, lỗi, chưa chọn hộ)."""
        self.lb_tb.setText(chu)
        self.b_mo_ngoai.setVisible(bool(mo_ngoai and (self.pdf or self.xlsx)))
        self.ngan.setCurrentIndex(0)
        self._bat_nut()

    def thong_bao(self) -> str:
        return self.lb_tb.text() if self.ngan.currentIndex() == 0 else ''

    def _doi_trang(self) -> None:
        try:
            self._bat_nut()
        except RuntimeError:                            # QPdfView báo đổi trang lúc đang hủy (tài liệu đã xóa)
            pass

    def _bat_nut(self) -> None:
        n = self.so_trang()
        dang_xem = n > 0 and self.ngan.currentIndex() != 0
        for b in (self.b_phong, self.b_thu, self.b_vua, self.b_ngang):
            b.setEnabled(dang_xem)
        i = self.trang_hien_tai()
        self.b_truoc.setEnabled(dang_xem and i > 0)
        self.b_sau.setEnabled(dang_xem and i < n - 1)
        self.lb_trang.setText(f'{i + 1 if n else 0} / {n}')
        if self.muc_luc and not self.cb_muc.view().isVisible():      # combo theo hộ đang ở trang i
            k = max((j for j, (_, t) in enumerate(self.muc_luc) if t <= i), default=0)
            if self.cb_muc.currentIndex() != k:
                self.cb_muc.blockSignals(True)
                self.cb_muc.setCurrentIndex(k)
                self.cb_muc.blockSignals(False)
        self.b_in.setEnabled(self.pdf is not None and self.xlsx is not None and self._dang is None)
        self.b_in_hop.setEnabled(self.pdf is not None and self.doc is not None and n > 0 and self._dang is None)

    # ---- phóng to / trang
    def he_so(self) -> float:
        if self.kieu == 'qpdfview':
            return float(self.view.zoomFactor())
        return float(self.view.he_so) if self.view is not None else 1.0

    def phong_to(self, buoc: int) -> None:
        if self.view is None or self.so_trang() == 0:
            return
        hien = self._he_so_vua() if self._vua else self.he_so()
        ds = [k for k in PHONG_TO if (k > hien + 1e-3 if buoc > 0 else k < hien - 1e-3)]
        moi = (min(ds) if buoc > 0 else max(ds)) if ds else hien
        moi = min(moi, he_so_xem_toi_da())
        self._vua = False
        if self.kieu == 'qpdfview':
            self.view.setZoomFactor(moi)
        else:
            self.view.vua_trang, self.view.he_so = False, moi
            self.view.ve()

    def _he_so_vua_goc(self) -> float:
        """Hệ số phóng để trọn MỘT trang nằm trong khung (cả bề ngang lẫn bề cao). QPdfView: hệ số 1 = cỡ giấy (pt) x dpi
        logic màn hình / 72; trừ lề tài liệu và chỗ thanh cuộn."""
        if self.doc is None or self.doc.pageCount() <= 0:
            return 1.0
        co = self.doc.pagePointSize(max(0, min(self.trang_hien_tai(), self.doc.pageCount() - 1)))
        vung = self.view.viewport().size()
        man = QGuiApplication.primaryScreen()
        dpi = (man.logicalDotsPerInch() if man is not None else 96) / 72
        le = 2 * 12 + 20
        return max(0.1, min((vung.width() - le) / max(1.0, co.width() * dpi), (vung.height() - le) / max(1.0, co.height() * dpi)))

    def _he_so_vua(self) -> float:
        return min(self._he_so_vua_goc(), he_so_xem_toi_da())

    def _he_so_ngang(self) -> float:
        """Hệ số phóng để bề ngang MỘT trang vừa bề ngang khung (như _he_so_vua_goc nhưng không xét bề cao)."""
        if self.doc is None or self.doc.pageCount() <= 0:
            return 1.0
        co = self.doc.pagePointSize(max(0, min(self.trang_hien_tai(), self.doc.pageCount() - 1)))
        man = QGuiApplication.primaryScreen()
        dpi = (man.logicalDotsPerInch() if man is not None else 96) / 72
        return max(0.1, min((self.view.viewport().size().width() - 2 * 12 - 20) / max(1.0, co.width() * dpi), he_so_xem_toi_da()))

    def vua_ngang(self) -> None:
        """Phóng trang vừa bề ngang khung (khung cao: chữ to hơn "Vừa trang"); đổi cỡ khung thì không tự vừa lại."""
        if self.view is None or self.so_trang() == 0:
            return
        self._vua = False
        if self.kieu == 'qpdfview':
            self.view.setZoomFactor(self._he_so_ngang())
        else:
            self.view.vua_trang, self.view.he_so = False, self._he_so_ngang()
            self.view.ve()

    def vua_trang(self) -> None:
        if self.view is None:
            return
        self._vua = True
        if self.kieu == 'qpdfview':
            self.view.setZoomFactor(self._he_so_vua())
        else:
            self.view.vua_trang = True
            self.view.ve()

    def eventFilter(self, o, e):
        from PySide6.QtCore import QEvent
        if o is self.view and e.type() == QEvent.Type.Resize and self._vua and self.so_trang():
            QTimer.singleShot(0, lambda: self._vua and self.so_trang() and self.view.setZoomFactor(self._he_so_vua()))
        return super().eventFilter(o, e)

    def den_muc(self, k: int) -> None:
        """Nhảy tới trang đầu của hộ thứ k trong mục lục (bản xem nhiều hộ)."""
        if 0 <= k < len(self.muc_luc):
            self.sang_trang(0, tuyet_doi=self.muc_luc[k][1])

    def _dat_muc_luc(self, ds: list) -> None:
        self.muc_luc = list(ds or [])
        self.cb_muc.blockSignals(True)
        self.cb_muc.clear()
        for nhan, trang in self.muc_luc:
            self.cb_muc.addItem(nhan, trang)
        self.cb_muc.blockSignals(False)
        self.cb_muc.setVisible(bool(self.muc_luc))

    def sang_trang(self, buoc: int, tuyet_doi: int | None = None) -> None:
        n = self.so_trang()
        if n == 0:
            return
        i = max(0, min(n - 1, self.trang_hien_tai() + buoc if tuyet_doi is None else tuyet_doi))
        if self.kieu == 'qpdfview':
            self.view.pageNavigator().jump(i, QPointF(), self.view.zoomFactor())
        else:
            self.view.trang = i
            self.view.ve()
        self._bat_nut()

    # ---- lập bản xem trước ở nền
    def yeu_cau(self, khoa, tao_xlsx, ten: str = '', ngay: bool = False) -> None:
        """Lập bản xem trước: tao_xlsx(thu_muc) -> file .xlsx / .docx (luồng giao diện), Excel / Word xuất PDF ở luồng nền. khoa:
        bản đã lập trong phiên dùng lại (None: luôn lập lại - phương án đang soạn). ngay: không chờ ngừng bấm. File .docx mà Word không
        dùng được / lỗi: bản gần đúng dựng bằng Qt từ chính file .docx (docx_sang_pdf)."""
        self._cho = (khoa, tao_xlsx, ten)
        if khoa is not None and khoa in self._nho and Path(self._nho[khoa][0]).exists():
            self._cho = None
            self._hen.stop()
            self.xlsx = Path(self._nho[khoa][1]) if self._nho[khoa][1] else None
            self._dat_gan_dung(Path(self._nho[khoa][0]).stem.endswith('_gan_dung'))
            self._dat_muc_luc(self._nho_muc.get(khoa, []))
            self.nap_tai_lieu(self._nho[khoa][0])
            return
        if self._dang is None:
            self.bao(f'Đang chuẩn bị bản xem trước A4{": " + ten if ten else ""}…')
        if ngay:
            self._hen.stop()
            self._bat_dau()
        else:
            self._hen.start(CHO_MS)

    def dang_lap(self) -> bool:
        return self._dang is not None or self._cho is not None

    def _bat_dau(self) -> None:
        if self._dang is not None or self._cho is None:
            return                                      # đang xuất: lập tiếp khi xong (_kiem_nen)
        khoa, tao, ten = self._cho
        self._cho = None
        if self.thu_muc is None:
            self.thu_muc = thu_muc_moi()
            self._thu_muc_tao.append(self.thu_muc)
        d = self.thu_muc / f'{next(self._so):03d}'      # mỗi lần một thư mục: không ghi đè PDF đang mở (Windows khóa file)
        try:
            d.mkdir(parents=True, exist_ok=True)
            tra = tao(d)
            muc = [(Path(f), t) for f, t in tra] if isinstance(tra, (list, tuple)) else None     # nhiều hộ: [(file, nhãn)]
            xlsx = None if muc is not None else Path(tra)
        except Exception as e:                          # noqa: BLE001 - lỗi mẫu in / dữ liệu: báo trong khung, không bật hộp
            from .thong_bao import chu_loi
            self.bao(chu_loi('Không lập được bản xem trước', e))
            return
        if muc is not None and not muc:
            self.bao('Chưa có hộ nào để xem trước.')
            return
        self.xlsx = xlsx                                # nhiều hộ: None (nút In nhanh qua Word / Excel tắt - dùng "In…")
        word = all(la_word(f) for f, _ in muc) if muc is not None else la_word(xlsx)
        ly_do = (dung_duoc_word() if word else dung_duoc_excel()) if muc is None else \
            (dung_duoc_word() if any(la_word(f) for f, _ in muc) else '') or \
            (dung_duoc_excel() if any(not la_word(f) for f, _ in muc) else '')
        if ly_do:
            self._du_phong(khoa, xlsx, ly_do, muc)
            return
        pdf = (d / 'xem_nhieu_ho.pdf') if muc is not None else xlsx.with_suffix('.pdf')
        viec = dict(khoa=khoa, xlsx=xlsx, pdf=pdf, ten=ten, ket_qua=None, muc=muc, muc_luc=[])

        def chay():
            if muc is not None:
                viec['ket_qua'], viec['muc_luc'] = chuyen_pdf_nhieu(muc, pdf)
            else:
                viec['ket_qua'] = chuyen_pdf(xlsx, pdf)
        self._dang = viec
        self.bao(f'Microsoft {"Word" if word else "Excel"} đang tạo bản xem trước A4{": " + ten if ten else ""}…\n(vài giây)')
        threading.Thread(target=chay, daemon=True).start()
        self._nhip.start()

    def _kiem_nen(self) -> None:
        viec = self._dang
        if viec is None or viec['ket_qua'] is None:
            return
        self._nhip.stop()
        self._dang = None
        if not viec['ket_qua'] and viec['khoa'] is not None:
            self._nho[viec['khoa']] = (viec['pdf'], viec['xlsx'])
            if viec.get('muc') is not None:
                self._nho_muc[viec['khoa']] = viec['muc_luc']
        if self._cho is not None:                       # đã có yêu cầu mới hơn: bỏ kết quả này, lập yêu cầu mới
            self._bat_dau()
            return
        self.xlsx = viec['xlsx']
        if viec['ket_qua']:                             # Excel / Word lỗi / treo: dựng bản gần đúng bằng Qt
            self._du_phong(viec['khoa'], viec['xlsx'], viec['ket_qua'], viec.get('muc'))
        else:
            self._dat_gan_dung(False)
            self._dat_muc_luc(viec['muc_luc'] if viec.get('muc') is not None else [])
            self.nap_tai_lieu(viec['pdf'])

    def _dat_gan_dung(self, co: bool) -> None:
        self.gan_dung = co
        self.lb_gan_dung.setVisible(co)

    def _du_phong(self, khoa, xlsx: Path | None, ly_do: str, muc: list | None = None) -> None:
        """Không dùng được Excel / Word: PDF gần đúng bằng Qt - file .docx dựng từ chính file Word (docx_sang_pdf), file Excel (bảng
        tổng hợp) từ bản Excel (pdf_du_phong). Lỗi nữa thì báo lý do + mở ngoài."""
        muc_luc: list = []
        if muc is not None:                              # nhiều hộ: PDF gần đúng từng file rồi gộp
            pdf = muc[0][0].with_name('xem_nhieu_ho_gan_dung.pdf')
            try:
                con_lai = []
                for f, t in muc:
                    g = f.with_name(f.stem + '_gan_dung.pdf')
                    if la_word(f):
                        from .docx_sang_pdf import xuat_pdf_tu_docx
                        xuat_pdf_tu_docx(f, g)
                    else:
                        from .pdf_du_phong import xuat_pdf_du_phong_qt
                        xuat_pdf_du_phong_qt(f, g)
                    con_lai.append((g, t))
                muc_luc = gop_pdf_muc(con_lai, pdf)
            except Exception as e:                      # noqa: BLE001 - báo trong khung
                from .thong_bao import chu_loi
                self._dat_gan_dung(False)
                self.bao(f'{ly_do}\n\n{chu_loi("Không dựng được bản xem trước gần đúng", e)}')
                return
            if khoa is not None:
                self._nho[khoa] = (pdf, None)
                self._nho_muc[khoa] = muc_luc
            self.ly_do_gan_dung = ly_do
            self._dat_gan_dung(True)
            self._dat_muc_luc(muc_luc)
            self.nap_tai_lieu(pdf)
            return
        pdf = xlsx.with_name(xlsx.stem + '_gan_dung.pdf')
        try:
            if la_word(xlsx):
                from .docx_sang_pdf import xuat_pdf_tu_docx
                xuat_pdf_tu_docx(xlsx, pdf)
            else:
                from .pdf_du_phong import xuat_pdf_du_phong_qt
                xuat_pdf_du_phong_qt(xlsx, pdf)
        except Exception as e:                          # noqa: BLE001 - báo trong khung
            from .thong_bao import chu_loi
            self._dat_gan_dung(False)
            self.bao(f'{ly_do}\n\n{chu_loi("Không dựng được bản xem trước gần đúng", e)}\n\nĐã lập file '
                     f'{"Word" if la_word(xlsx) else "Excel"} của bản in: {xlsx.name}', mo_ngoai=True)
            return
        if khoa is not None:
            self._nho[khoa] = (pdf, xlsx)
        self.ly_do_gan_dung = ly_do
        self._dat_gan_dung(True)
        self._dat_muc_luc([])
        self.nap_tai_lieu(pdf)

    def cho_xong(self, giay: float = 120) -> bool:
        """Chờ bản xem trước đang lập xong (kiểm thử). True nếu xong."""
        het = time.time() + giay
        while self.dang_lap() and time.time() < het:
            if self._cho is not None and self._dang is None:
                self._hen.stop()
                self._bat_dau()
            QApplication.processEvents()
            self._kiem_nen()
            time.sleep(0.01)
        return not self.dang_lap()

    # ---- in / mở ngoài / dọn
    def in_nhanh(self) -> None:
        if self.ham_in is not None and self.pdf is not None:
            self.ham_in(self.pdf, self.xlsx)

    def in_hop_thoai(self, printer=None, hoi: bool = True) -> int:
        """Hộp in của Windows (chọn máy in, số bản, trang) -> in bản đang xem. Trả số trang đã in."""
        if self.doc is None or self.pdf is None:
            return 0
        return in_co_hop_thoai(self, self.doc, Path(self.xlsx or self.pdf).stem, printer, hoi)

    def mo_ngoai(self) -> None:
        f = self.pdf if self.pdf is not None and Path(self.pdf).exists() else self.xlsx
        if f is not None:
            from .in_an import mo_file
            mo_file(f)

    def don_dep(self) -> None:
        """Đóng tài liệu, dừng hẹn giờ, xóa thư mục tạm (luồng nền đang chạy thì Excel ghi xong vào thư mục sẽ xóa lúc thoát)."""
        self._hen.stop()
        self._nhip.stop()
        self._cho = None
        if self.doc is not None:
            self.doc.close()
        self._tha_buf()
        self.pdf = self.xlsx = None
        self._nho.clear()
        self._nho_muc.clear()
        self._dat_muc_luc([])
        if self.thu_muc is not None:
            _xoa(self.thu_muc)
            if self._dang is not None:
                _PHIEN.add(str(self.thu_muc))           # Excel còn ghi: xóa lại lúc thoát
            self.thu_muc = None
        self.bao('Chọn một hộ để xem trước bản in A4.')
