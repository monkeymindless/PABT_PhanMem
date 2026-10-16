"""Cửa sổ "Quét giấy tờ (OCR)" (0.9.87; 0.9.95 xem trước file + phương án chi tiết đã số hóa): chọn ảnh chụp / PDF của Giấy chứng
nhận QSDĐ, biên bản kiểm kê hoặc BẢNG PHƯƠNG ÁN CHI TIẾT của hộ đã scan -> nhận dạng chữ (ocr_ho_so) -> soát / sửa -> điền vào cửa sổ
đang mở. Bên trái: xem trước TOÀN BỘ các trang của file (ảnh / PDF nhiều trang) - chữ nhận dạng ở chế độ phụ ("Chữ OCR"). Dùng ở Lập
phương án hộ (CuaSoLapPA: thông tin hộ, thửa, nhân khẩu, nguồn gốc, tái định cư, tài sản) và Khái toán & dự toán (KhungDuToan: dòng
đất, tài sản). Không ghi gì vào phương án khi chưa bấm Lưu ở cửa sổ đích (trừ ô "Lưu đính kèm file vào hồ sơ hộ" - ghi ngay bảng
anh_hien_trang của hộ)."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QImage, QPixmap, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea, QSplitter,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import ocr_ho_so
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, chu_loi
from .tien import so_vn

COT_THUA = ['Lấy', 'Tờ', 'Thửa', 'Diện tích (m²)', 'Loại đất', 'Địa chỉ thửa']
DUOI_XEM = ('.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tif', '.tiff')
RONG_DUNG_TRANG = 1100            # bề rộng (px) dựng ảnh mỗi trang PDF - đủ nét khi phóng to 150%
TRANG_TOI_DA = 200                # file quá nhiều trang: chỉ dựng chừng này trang để xem (OCR vẫn đọc hết)


def anh_cac_trang(files) -> list:
    """[(tên file, số trang, QImage)] mọi trang của các file ảnh / PDF (PDF: QtPdf; Qt5 không có QtPdf: ảnh scan trong PDF qua pypdf).
    Trang không dựng được: bỏ qua."""
    kq = []
    for f in files:
        f = Path(f)
        if f.suffix.lower() != '.pdf':
            im = QImage(str(f))
            if not im.isNull():
                kq.append((f.name, 1, im))
            continue
        try:
            from PySide6.QtPdf import QPdfDocument
        except ImportError:
            QPdfDocument = None
        if QPdfDocument is not None:
            doc = QPdfDocument()
            try:
                doc.load(str(f))
                for i in range(min(doc.pageCount(), TRANG_TOI_DA)):
                    s = doc.pagePointSize(i)
                    if s.width() <= 0:
                        continue
                    from PySide6.QtCore import QSize
                    im = doc.render(i, QSize(RONG_DUNG_TRANG, int(RONG_DUNG_TRANG * s.height() / s.width())))
                    if not im.isNull():
                        kq.append((f.name, i + 1, im))
            finally:
                doc.close()
            continue
        import tempfile
        from . import ocr
        td = Path(tempfile.mkdtemp(prefix='PABT_xem_'))
        try:
            for i, _tong, p in ocr._anh_trang_pypdf(f, td):
                if i > TRANG_TOI_DA:
                    break
                im = QImage(str(p)) if p is not None else QImage()
                if not im.isNull():
                    kq.append((f.name, i, im))
        except Exception:                                # noqa: BLE001 - PDF không có ảnh (lớp chữ): không xem được trên Qt5
            pass
    return kq


class KhungXemFile(QScrollArea):
    """Xem trước toàn bộ nội dung file lưu: các trang xếp dọc liên tục trên nền xám, viền trang rõ; Ctrl + lăn chuột phóng to / thu nhỏ,
    kéo chuột để di chuyển, xoay 90°. lb_trang (nếu gắn) hiện "Trang k / N" theo vị trí cuộn."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('khung_xem_file')
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setStyleSheet('QScrollArea#khung_xem_file { background: #475569; border: 0; }')
        self.trong = QWidget()
        self.trong.setObjectName('trong_xem_file')
        self.trong.setStyleSheet('QWidget#trong_xem_file { background: #475569; }')
        self.lo = QVBoxLayout(self.trong)
        self.lo.setContentsMargins(12, 12, 12, 12)
        self.lo.setSpacing(12)
        self.lo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setWidget(self.trong)
        self.trang = []                                   # [(tên file, số trang, QImage)]
        self.nhan = []                                    # QLabel mỗi trang
        self.he_so = 0.6
        self.goc = 0
        self.lb_trang = None
        self._keo = None
        self.lb_trong = QLabel('Chọn ảnh chụp / PDF: các trang của file hiện ở đây để soát khi đọc.')
        self.lb_trong.setStyleSheet('QLabel { color: #E2E8F0; background: transparent; }')
        self.lo.addWidget(self.lb_trong)
        self.verticalScrollBar().valueChanged.connect(lambda *_: self._bao_trang())
        self.viewport().installEventFilter(self)

    # ---- nạp / vẽ
    def nap(self, files) -> int:
        self.nap_anh(anh_cac_trang(files))
        return len(self.trang)

    def nap_anh(self, trang: list) -> None:
        for lb in self.nhan:
            self.lo.removeWidget(lb)
            lb.deleteLater()
        self.nhan, self.trang, self.goc = [], list(trang), 0
        self.lb_trong.setVisible(not self.trang)
        for ten, so, _im in self.trang:
            lb = QLabel()
            lb.setObjectName('trang_file')
            lb.setStyleSheet('QLabel#trang_file { background: #FFFFFF; border: 1px solid #1E293B; }')
            lb.setToolTip(f'{ten} - trang {so}')
            self.lo.addWidget(lb, 0, Qt.AlignmentFlag.AlignHCenter)
            self.nhan.append(lb)
        self.vua_khung()

    def _ve(self) -> None:
        for (_ten, _so, im), lb in zip(self.trang, self.nhan):
            pm = QPixmap.fromImage(im)
            if self.goc:
                pm = pm.transformed(QTransform().rotate(self.goc), Qt.TransformationMode.SmoothTransformation)
            w = max(50, int(pm.width() * self.he_so))
            lb.setPixmap(pm.scaledToWidth(w, Qt.TransformationMode.SmoothTransformation))
            lb.setFixedSize(lb.pixmap().size())
        self._bao_trang()

    def _rong_trang(self) -> int:
        if not self.trang:
            return 1
        im = self.trang[0][2]
        return im.height() if self.goc % 180 else im.width()

    # ---- điều khiển
    def vua_khung(self) -> None:
        if self.trang:
            self.he_so = max(0.1, (self.viewport().width() - 40) / self._rong_trang())
            self._ve()

    def phong_to(self, buoc: float = 1.25) -> None:
        self.he_so = min(4.0, max(0.1, self.he_so * buoc))
        self._ve()

    def xoay(self) -> None:
        self.goc = (self.goc + 90) % 360
        self._ve()

    def trang_hien(self) -> int:
        """Chỉ số trang (0..N-1) đang ở giữa khung nhìn."""
        y = self.verticalScrollBar().value() + self.viewport().height() // 2
        for i, lb in enumerate(self.nhan):
            if lb.y() + lb.height() >= y:
                return i
        return max(0, len(self.nhan) - 1)

    def sang_trang(self, buoc: int) -> None:
        if not self.nhan:
            return
        # vừa nạp / phóng to: vị trí trang và chiều cao vùng cuộn chưa tính (thanh cuộn còn tối đa cũ -> setValue bị chặn)
        self.trong.layout().activate()
        self.trong.resize(max(self.viewport().width(), self.trong.sizeHint().width()), self.trong.sizeHint().height())
        i = min(max(self.trang_hien() + buoc, 0), len(self.nhan) - 1)
        self.verticalScrollBar().setValue(self.nhan[i].y() - 12)
        self._bao_trang()

    def _bao_trang(self) -> None:
        if self.lb_trang is not None:
            self.lb_trang.setText(f'Trang {self.trang_hien() + 1} / {len(self.nhan)}' if self.nhan else 'Trang 0 / 0')

    # ---- chuột: Ctrl + lăn = phóng to / thu nhỏ; kéo = di chuyển
    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.phong_to(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)
            e.accept()
            return
        super().wheelEvent(e)

    def eventFilter(self, o, e):
        t = e.type()
        if t == QEvent.Type.MouseButtonPress and e.button() == Qt.MouseButton.LeftButton:
            self._keo = (e.globalPosition().toPoint() if hasattr(e, 'globalPosition') else e.globalPos(),
                         self.horizontalScrollBar().value(), self.verticalScrollBar().value())
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        elif t == QEvent.Type.MouseMove and self._keo is not None:
            p = e.globalPosition().toPoint() if hasattr(e, 'globalPosition') else e.globalPos()
            d = p - self._keo[0]
            self.horizontalScrollBar().setValue(self._keo[1] - d.x())
            self.verticalScrollBar().setValue(self._keo[2] - d.y())
        elif t == QEvent.Type.MouseButtonRelease:
            self._keo = None
            self.viewport().unsetCursor()
        return super().eventFilter(o, e)


class HopQuetGiayTo(QDialog):
    """Quét giấy tờ cho Khái toán (cua_so = KhungDuToan): thêm dòng đất, đưa tài sản vào khái toán. Cửa sổ lập phương án hộ KHÔNG
    còn dùng (0.9.96, người dùng: nút "Quét hồ sơ" chỉ báo "Tiện ích đang trong quá trình hoàn thiện")."""
    im_lang = False

    def __init__(self, cua_so, dich: str = 'du_toan', parent=None, files=None):
        super().__init__(parent or cua_so)
        self.cua_so, self.dich = cua_so, dich
        self.kq = ocr_ho_so.KetQuaOcr()
        self.files = []
        self.setWindowTitle('Quét giấy tờ (OCR) - Giấy chứng nhận QSDĐ, biên bản kiểm kê, phương án chi tiết đã số hóa')
        self.resize(1280, 760)
        b_chon = QPushButton('Chọn ảnh chụp / PDF…')
        b_chon.setToolTip('Ảnh chụp bằng điện thoại (.jpg, .png - chép qua Zalo / cáp), PDF scan hoặc PDF có chữ: giấy chứng nhận, biên '
                          'bản kiểm kê, bảng phương án chi tiết của hộ đã số hóa. Chọn được nhiều file (mặt trước, mặt sau, nhiều trang).')
        b_chon.clicked.connect(lambda: self.chon())
        self.lb_file = QLabel('Chưa chọn file.')
        self.lb_file.setWordWrap(True)
        h = QHBoxLayout()
        h.addWidget(b_chon)
        h.addWidget(self.lb_file, 1)
        # ---- trái: xem trước file (mặc định) | chữ OCR (chế độ phụ)
        self.khung_xem_file = KhungXemFile()
        self.o_chu = QPlainTextEdit()
        self.o_chu.setPlaceholderText('Chữ nhận dạng được hiện ở đây - sửa chỗ sai rồi bấm "Bóc tách lại từ chữ".')
        b_lai = QPushButton('Bóc tách lại từ chữ')
        b_lai.clicked.connect(lambda: self.boc_tach_lai())
        trang_chu = QWidget()
        lc = QVBoxLayout(trang_chu)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.addWidget(self.o_chu, 1)
        lc.addWidget(b_lai)
        self.ngan_trai = QStackedWidget()
        self.ngan_trai.addWidget(self.khung_xem_file)      # 0: xem trước toàn bộ trang file
        self.ngan_trai.addWidget(trang_chu)                # 1: chữ OCR
        cong_cu = QWidget()
        hc = QHBoxLayout(cong_cu)
        hc.setContentsMargins(0, 0, 0, 0)
        hc.setSpacing(4)

        def nut(chu, goi_y, ham, rong=None):
            b = QToolButton()
            b.setText(chu)
            b.setToolTip(goi_y)
            b.setFixedHeight(28)
            if rong:
                b.setFixedWidth(rong)
            b.clicked.connect(ham)
            hc.addWidget(b)
            return b
        self.b_trang_truoc = nut('◀', 'Trang trước', lambda: self.khung_xem_file.sang_trang(-1), 30)
        self.lb_trang = QLabel('Trang 0 / 0')
        self.lb_trang.setMinimumWidth(80)
        self.lb_trang.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hc.addWidget(self.lb_trang)
        self.b_trang_sau = nut('▶', 'Trang sau', lambda: self.khung_xem_file.sang_trang(1), 30)
        hc.addSpacing(8)
        self.b_thu_nho = nut('−', 'Thu nhỏ (Ctrl + lăn chuột)', lambda: self.khung_xem_file.phong_to(1 / 1.25), 30)
        self.b_vua_khung = nut('Vừa khung', 'Vừa bề rộng khung xem', lambda: self.khung_xem_file.vua_khung())
        self.b_phong_to = nut('+', 'Phóng to (Ctrl + lăn chuột)', lambda: self.khung_xem_file.phong_to(1.25), 30)
        self.b_xoay = nut('Xoay 90°', 'Xoay trang bị ngược / nằm ngang', lambda: self.khung_xem_file.xoay())
        from .giao_dien import KieuNut, ap_kieu_nut
        for b in (self.b_trang_truoc, self.b_trang_sau, self.b_thu_nho, self.b_vua_khung, self.b_phong_to, self.b_xoay):
            ap_kieu_nut(b, KieuNut.PHU)                 # "Xoay" chứa "xoa": không để luật màu theo chữ tô đỏ như nút Xóa
        hc.addStretch(1)
        self.b_doi_xem = QToolButton()
        self.b_doi_xem.setText('Chữ OCR')
        self.b_doi_xem.setCheckable(True)
        self.b_doi_xem.setFixedHeight(28)
        self.b_doi_xem.setToolTip('Xem / sửa chữ nhận dạng được (bóc tách lại sau khi sửa). Tắt: xem trước nội dung file.')
        self.b_doi_xem.toggled.connect(lambda bat: self.ngan_trai.setCurrentIndex(1 if bat else 0))
        hc.addWidget(self.b_doi_xem)
        self.khung_xem_file.lb_trang = self.lb_trang
        trai = QWidget()
        lt = QVBoxLayout(trai)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.setSpacing(4)
        lt.addWidget(cong_cu)
        lt.addWidget(self.ngan_trai, 1)
        # ---- phải: kết quả bóc tách
        self.o_ten, self.o_cccd, self.o_dc = QLineEdit(), QLineEdit(), QLineEdit()
        self.o_nk = QLineEdit()
        self.o_nk.setPlaceholderText('số người')
        self.o_nk.setMaximumWidth(100)
        self.o_tdc = QLineEdit()
        self.o_ng = QPlainTextEdit()
        self.o_ng.setPlaceholderText('Nguồn gốc đất (mục II của phương án chi tiết) - điền vào cột Nguồn gốc các thửa thêm mới.')
        self.o_ng.setMaximumHeight(90)
        f = QFormLayout()
        f.setContentsMargins(0, 0, 0, 0)
        f.setVerticalSpacing(4)
        f.addRow('Họ và tên:', self.o_ten)
        f.addRow('Số CCCD:', self.o_cccd)
        f.addRow('Nhân khẩu:', self.o_nk)
        f.addRow('Địa chỉ:', self.o_dc)
        f.addRow('Nguồn gốc đất:', self.o_ng)
        f.addRow('Tái định cư:', self.o_tdc)
        self.bang = QTableWidget(0, len(COT_THUA))
        self.bang.setHorizontalHeaderLabels(COT_THUA)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.o_ts = QPlainTextEdit()
        self.o_ts.setPlaceholderText('Tài sản, cây trồng, vật nuôi, hỗ trợ (mỗi dòng: Tên  ĐVT  Số lượng [Tỷ lệ %]) - sửa được, phân loại '
                                     'ở bước sau.')
        phai = QWidget()
        lp = QVBoxLayout(phai)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.setSpacing(4)
        lp.addLayout(f)
        lp.addWidget(QLabel('Thửa đất:'))
        lp.addWidget(self.bang, 2)
        lp.addWidget(QLabel('Tài sản, cây trồng, vật nuôi, hỗ trợ:'))
        lp.addWidget(self.o_ts, 1)
        tach = QSplitter(Qt.Orientation.Horizontal)
        tach.addWidget(trai)
        tach.addWidget(phai)
        tach.setStretchFactor(0, 3)
        tach.setStretchFactor(1, 2)
        tach.setSizes([720, 560])
        self.lb = QLabel('Nhận dạng chữ trên máy (Windows OCR / Tesseract - không gửi giấy tờ ra ngoài). Chữ viết tay đọc không được / '
                         'sai nhiều: soát lại trước khi điền.')
        self.lb.setWordWrap(True)
        self.b_ho = QPushButton('Thêm dòng đất')
        self.b_ho.clicked.connect(lambda: self.dien_ho_thua())
        self.b_ts = QPushButton('Đưa tài sản vào khái toán…')
        self.b_ts.clicked.connect(lambda: self.dua_tai_san())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addStretch(1)
        hn.addWidget(self.b_ho)
        hn.addWidget(self.b_ts)
        hn.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(8, 6, 8, 6)
        lo.setSpacing(4)
        lo.addLayout(h)
        lo.addWidget(tach, 1)
        lo.addWidget(self.lb)
        lo.addLayout(hn)
        self._bat_nut()
        if files:
            self.doc(files)

    # ---- đọc
    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            self.lb.setText(chu)
        else:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def chon(self) -> bool:
        ds, _ = QFileDialog.getOpenFileNames(self, 'Chọn ảnh chụp / PDF giấy tờ', str(Path.home() / 'Downloads'),
                                             'Ảnh, PDF (*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp *.pdf)')
        return self.doc(ds) if ds else False

    def doc(self, files) -> bool:
        files = [Path(f) for f in files]
        self.files = files
        self.lb_file.setText(', '.join(f.name for f in files))
        self.b_doi_xem.setChecked(False)
        with con_tro_cho():
            self.khung_xem_file.nap(files)                # xem trước ngay - đọc chữ (lâu) sau
        QApplication.processEvents()
        tien = None if self.im_lang else QProgressDialog('Đang nhận dạng chữ…', 'Dừng', 0, 0, self)
        if tien is not None:
            tien.setWindowTitle(TEN_UD)
            tien.setWindowModality(Qt.WindowModality.WindowModal)
            tien.setMinimumDuration(300)

        def bao(i, n):
            if tien is not None:
                tien.setMaximum(n)
                tien.setValue(i)
                QApplication.processEvents()

        def huy():
            QApplication.processEvents()
            return tien is not None and tien.wasCanceled()
        ds_kq, chu_all, loi = [], [], []
        from . import ocr
        try:
            with con_tro_cho():
                for f in files:
                    if tien is not None:
                        tien.setLabelText(f'Đang nhận dạng: {f.name}…')
                    try:
                        kq, chu, da_ocr = ocr_ho_so.doc_va_boc_tach(f, bao, huy)
                    except ocr.DaHuy:
                        raise
                    except Exception as e:                       # noqa: BLE001 - lỗi từng file: báo, đọc tiếp file khác
                        loi.append(chu_loi(f'{f.name}', e))
                        continue
                    ds_kq.append(kq)
                    chu_all.append(f'===== {f.name}{" (nhận dạng ảnh)" if da_ocr else ""} =====\n{chu}')
        except ocr.DaHuy:
            loi.append('Đã dừng nhận dạng.')
        finally:
            if tien is not None:
                tien.close()
                tien.deleteLater()
        if not ds_kq:
            self._bao('Không đọc được file nào:\n' + '\n'.join(loi), True)
            return False
        self.o_chu.setPlainText('\n\n'.join(chu_all))
        self.hien(ocr_ho_so.gop(ds_kq), loi)
        return True

    def boc_tach_lai(self) -> None:
        self.hien(ocr_ho_so.boc_tach(self.o_chu.toPlainText()))

    def hien(self, kq: ocr_ho_so.KetQuaOcr, loi: list | None = None) -> None:
        self.kq = kq
        self.o_ten.setText(kq.ho_ten)
        self.o_cccd.setText(kq.so_cccd)
        self.o_dc.setText(kq.dia_chi)
        self.o_nk.setText('' if kq.nhan_khau is None else str(kq.nhan_khau))
        self.o_ng.setPlainText(kq.nguon_goc)
        self.o_tdc.setText(kq.tai_dinh_cu)
        self.bang.setRowCount(len(kq.thua))
        for r, t in enumerate(kq.thua):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.bang.setItem(r, 0, chk)
            for c, v in enumerate((t['so_to'], t['so_thua'], '' if t['dt_thu_hoi'] is None else so_vn(t['dt_thu_hoi']),
                                   t['loai_dat'], t.get('dia_chi_thua', '')), start=1):
                self.bang.setItem(r, c, QTableWidgetItem(str(v)))
        self.o_ts.setPlainText('\n'.join(kq.dong_tai_san))
        ten = {'gcn': 'Giấy chứng nhận QSDĐ', 'bien_ban': 'Biên bản kiểm kê', 'pa_chi_tiet': 'Phương án chi tiết'}.get(kq.loai, 'Giấy tờ')
        self.lb.setText(f'{ten}: {len(kq.thua)} thửa, {len(kq.dong_tai_san)} dòng tài sản, hỗ trợ.' +
                        ('\n' + '\n'.join((loi or []) + kq.canh_bao) if (loi or kq.canh_bao) else ''))
        self._bat_nut()

    def _bat_nut(self) -> None:
        self.b_ho.setEnabled(self.bang.rowCount() > 0 or bool(self.o_ten.text().strip()))
        self.b_ts.setEnabled(bool(self.o_ts.toPlainText().strip()) or self.bang.rowCount() == 0)

    # ---- đọc bảng
    def thua_da_chon(self) -> list:
        from .lap_pa import LoiNhap, doc_so
        kq = []
        for r in range(self.bang.rowCount()):
            if self.bang.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            g = [self.bang.item(r, c).text().strip() if self.bang.item(r, c) else '' for c in range(1, len(COT_THUA))]
            try:
                dt = doc_so(g[2], 'Diện tích') if g[2] else None
            except LoiNhap:                                      # người dùng gõ sai ô diện tích: coi như chưa có
                dt = None
            kq.append(dict(so_to=g[0], so_thua=g[1], dt_thu_hoi=dt, loai_dat=g[3], dia_chi_thua=g[4]))
        return kq

    # ---- điền vào cửa sổ đích
    def dien_ho_thua(self, bao: bool = True) -> int:
        """Khái toán: thêm dòng đất (loại đất, diện tích) của các thửa đã chọn. Trả số dòng đã thêm."""
        n, bo = 0, []
        for t in self.thua_da_chon():
            ma = (t['loai_dat'] or '').split('+')[0]
            if not ma or t['dt_thu_hoi'] is None:
                bo.append(t['so_thua'])
                continue
            if self.cua_so.them_dat(ma, so_vn(t['dt_thu_hoi'])) is not None:
                n += 1
        if bao:
            self._bao(f'Đã thêm {n} dòng đất vào bảng khái toán (đơn giá: tra NQ 28 hoặc nhập).' +
                      (f'\nBỏ qua thửa thiếu loại đất / diện tích: {", ".join(bo)}' if bo else ''))
        return n

    def dua_tai_san(self):
        """Mở hộp "Dán danh sách tài sản" với các dòng tài sản (tự phân loại nhà / cây / vật nuôi / hỗ trợ)."""
        chu = self.o_ts.toPlainText().strip()
        if not chu:
            self._bao('Không có dòng tài sản nào.', True)
            return None
        self.accept()
        return self.cua_so.dan_tai_san(chu, cho=not self.im_lang)
