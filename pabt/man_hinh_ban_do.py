"""Màn hình bản đồ thửa đất (0.9.87): HopNhapCad (nhập bản vẽ .dxf - ban_do_cad) và HopBanDo (bản đồ vẽ bằng QGraphicsView: phóng to bằng
con lăn, kéo để di chuyển, tô màu theo đồng thuận - xanh đã đồng thuận, đỏ chưa đồng thuận, vàng chưa lấy ý kiến, xám chưa gắn hộ;
BẤM thửa -> mở hồ sơ, phương án của hộ). Vẽ bằng Qt có sẵn (người dùng chọn 14/10/2026 thay Leaflet / QWebEngine: bộ cài không tăng
~300 MB, chạy cả Win 7 32-bit, không cần mạng)."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGraphicsPolygonItem,
                               QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import ban_do_cad
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, chu_loi
from .tien import so_vn

KHONG_LOP = '(không có)'


# ---------------------------------------------------------------- nhập bản vẽ
class HopNhapCad(QDialog):
    """Chọn file .dxf, lớp ranh thửa / ranh thu hồi, số tờ -> xem trước -> lưu vào dự án (tùy chọn cập nhật DT thu hồi)."""
    im_lang = False

    def __init__(self, con, parent=None, file=None):
        super().__init__(parent)
        self.con, self.kq, self.file = con, None, None
        self.setWindowTitle('Nhập bản vẽ địa chính CAD (.dxf)')
        self.resize(1100, 680)
        self.o_file = QLineEdit()
        self.o_file.setReadOnly(True)
        b_chon = QPushButton('Chọn file .dxf…')
        b_chon.clicked.connect(lambda: self.chon_file())
        self.cb_thua, self.cb_ranh = QComboBox(), QComboBox()
        self.o_to = QLineEdit()
        self.o_to.setPlaceholderText('tự tìm trong bản vẽ / tên file')
        self.o_to.setMaximumWidth(160)
        b_phan_tich = QPushButton('Phân tích')
        b_phan_tich.clicked.connect(lambda: self.phan_tich())
        h = QHBoxLayout()
        h.addWidget(self.o_file, 1)
        h.addWidget(b_chon)
        f = QFormLayout()
        f.addRow('File bản vẽ:', h)
        h2 = QHBoxLayout()
        for nhan, w in (('Lớp ranh thửa:', self.cb_thua), ('Lớp ranh thu hồi:', self.cb_ranh), ('Số tờ:', self.o_to)):
            h2.addWidget(QLabel(nhan))
            h2.addWidget(w, 1 if w is not self.o_to else 0)
        h2.addWidget(b_phan_tich)
        f.addRow('', h2)
        self.bang = QTableWidget(0, 9)
        self.bang.setHorizontalHeaderLabels(['Cập nhật DT\nthu hồi', 'Tờ', 'Thửa', 'Loại đất', 'DT nhãn\n(m²)', 'DT hình\n(m²)',
                                             'DT trong ranh\n(m²)', 'Hồ sơ hiện tại', 'Nhãn trên bản vẽ'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.lb = QLabel('Ranh thửa phải là hình khép kín (polyline đóng); nhãn số thửa / diện tích / loại đất đặt bên trong thửa.')
        self.lb.setWordWrap(True)
        self.o_loai = QCheckBox('Cập nhật cả loại đất theo bản vẽ (thửa được đánh dấu)')
        b_luu = QPushButton('Lưu vào dự án')
        b_luu.clicked.connect(lambda: self.luu())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addWidget(self.o_loai)
        hn.addStretch(1)
        hn.addWidget(b_luu)
        hn.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addLayout(f)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb)
        lo.addLayout(hn)
        if file:
            self.chon_file(file)

    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            self.lb.setText(chu)
        else:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def chon_file(self, file=None) -> bool:
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn bản vẽ địa chính', '', 'Bản vẽ CAD (*.dxf *.dwg)')
            if not file:
                return False
        try:
            with con_tro_cho():
                lop = ban_do_cad.doc_lop(file)
        except ban_do_cad.LoiCad as e:
            self._bao(str(e), True)
            return False
        self.file = Path(file)
        self.o_file.setText(str(file))
        for cb in (self.cb_thua, self.cb_ranh):
            cb.clear()
        self.cb_ranh.addItem(KHONG_LOP, None)
        for ten, so_hinh, so_chu in lop:
            if so_hinh:
                self.cb_thua.addItem(f'{ten} ({so_hinh} hình)', ten)
                self.cb_ranh.addItem(f'{ten} ({so_hinh} hình)', ten)
        goi_y = next((i for i in range(self.cb_ranh.count()) if 'THU HOI' in str(self.cb_ranh.itemData(i) or '').upper()
                      or 'QUY HOACH' in str(self.cb_ranh.itemData(i) or '').upper() or 'RANH GPMB' in str(self.cb_ranh.itemData(i) or '').upper()), 0)
        self.cb_ranh.setCurrentIndex(goi_y)
        return self.phan_tich()

    def phan_tich(self) -> bool:
        if self.file is None:
            return False
        try:
            with con_tro_cho():
                self.kq = ban_do_cad.phan_tich(self.file, self.cb_thua.currentData(), self.cb_ranh.currentData(),
                                               self.o_to.text().strip() or None)
        except ban_do_cad.LoiCad as e:
            self._bao(str(e), True)
            return False
        if not self.o_to.text().strip():
            self.o_to.setPlaceholderText(f'tự tìm: {self.kq.so_to or "?"}')
        i = self.cb_thua.findData(self.kq.lop_thua)
        if i >= 0 and i != self.cb_thua.currentIndex():
            self.cb_thua.blockSignals(True)
            self.cb_thua.setCurrentIndex(i)
            self.cb_thua.blockSignals(False)
        cm = ban_do_cad.chi_muc_thua(self.con)
        self.bang.setRowCount(len(self.kq.thua))
        so_khop = 0
        for r, t in enumerate(self.kq.thua):
            k = cm.get((ban_do_cad._khoa(t.so_to), ban_do_cad._khoa(t.so_thua)))
            chk = QTableWidgetItem()
            moi = t.dt_trong_ranh if t.dt_trong_ranh is not None else (t.dt_ban_ve or t.dt_hinh)
            if k:
                so_khop += 1
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                chk.setCheckState(Qt.CheckState.Unchecked)
                hien = f'Hộ {k[1]}: DT thu hồi {so_vn(k[2]) if k[2] not in (None, "") else "?"} m², {k[3] or "?"}'
                if str(k[2] or '') and abs(float(k[2]) - float(moi)) > 0.05:
                    hien += f' → bản vẽ {so_vn(moi)}'
            else:
                chk.setFlags(Qt.ItemFlag.ItemIsEnabled)
                hien = 'Chưa có trong hồ sơ kiểm kê'
            self.bang.setItem(r, 0, chk)
            for c, v in enumerate((t.so_to, t.so_thua, t.loai_dat, '' if t.dt_ban_ve is None else so_vn(t.dt_ban_ve),
                                   so_vn(t.dt_hinh), '' if t.dt_trong_ranh is None else so_vn(t.dt_trong_ranh), hien,
                                   t.nhan.replace('\n', ' | ')), start=1):
                it = QTableWidgetItem(str(v))
                if c in (4, 5, 6):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(r, c, it)
        self.bang.resizeColumnsToContents()
        self.lb.setText(f'{len(self.kq.thua)} thửa tờ {self.kq.so_to} (lớp "{self.kq.lop_thua}"), {so_khop} thửa khớp hồ sơ. '
                        'Đánh dấu cột đầu để cập nhật DT thu hồi theo bản vẽ (DT trong ranh nếu có lớp ranh thu hồi).' +
                        ('\n' + '\n'.join(self.kq.canh_bao[:6]) if self.kq.canh_bao else ''))
        return True

    def luu(self) -> dict | None:
        if not self.kq or not self.kq.thua:
            self._bao('Chưa có thửa nào để lưu: chọn file và bấm Phân tích.', True)
            return None
        cap = {(ban_do_cad._khoa(t.so_to), ban_do_cad._khoa(t.so_thua)) for r, t in enumerate(self.kq.thua)
               if self.bang.item(r, 0).checkState() == Qt.CheckState.Checked}
        try:
            with con_tro_cho():
                kq = ban_do_cad.luu(self.con, self.kq, cap, self.o_loai.isChecked())
        except (ban_do_cad.LoiCad, OSError) as e:
            self._bao(chu_loi('Không lưu được bản đồ', e), True)
            return None
        self._bao(f'Đã lưu {kq["luu"]} thửa vào bản đồ dự án ({kq["khop"]} thửa khớp hồ sơ, cập nhật DT thu hồi {kq["cap_nhat"]} thửa).')
        self.accept()
        return kq


# ---------------------------------------------------------------- bản đồ
class _Thua(QGraphicsPolygonItem):
    def __init__(self, t: ban_do_cad.ThuaBanDo, poly: QPolygonF):
        super().__init__(poly)
        self.t = t
        mau = QColor(ban_do_cad.TRANG_THAI[t.trang_thai][1])
        nen = QColor(mau)
        nen.setAlpha(110)
        self.setBrush(QBrush(nen))
        but = QPen(mau.darker(140))
        but.setCosmetic(True)                            # nét 1 px mọi mức phóng
        self.setPen(but)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor if t.ma_ho is not None else Qt.CursorShape.ArrowCursor)
        ten = ban_do_cad.TRANG_THAI[t.trang_thai][0]
        dt = f'{so_vn(t.dt_hinh)} m²' + (f' (trong ranh {so_vn(t.dt_trong_ranh)} m²)' if t.dt_trong_ranh not in (None, '') else '')
        self.setToolTip(f'Thửa {t.so_thua} tờ {t.so_to} {t.loai_dat}\n{dt}\n' +
                        (f'Hộ {t.ma_ho}: {t.ho_ten}\n{ten} - bấm để mở hồ sơ' if t.ma_ho is not None else ten))

    def hoverEnterEvent(self, e):
        p = QPen(self.pen())
        p.setWidth(3)
        self.setPen(p)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        p = QPen(self.pen())
        p.setWidth(1)
        self.setPen(p)
        super().hoverLeaveEvent(e)


class KhungBanDo(QGraphicsView):
    """Khung vẽ thửa. Tọa độ bản vẽ (y hướng lên) -> cảnh Qt (y hướng xuống): lật y. Bấm thửa có hộ -> tín hiệu bam_ho(mã hộ)."""
    bam_ho = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor('#F8FAFC')))
        self.thua = []                                  # [_Thua]
        self._nhan = []
        self._diem_bam = None

    def ve(self, ds: list) -> None:
        sc = self.scene()
        sc.clear()
        self.thua, self._nhan = [], []
        font = QFont('Segoe UI', 8)
        for t in ds:
            poly = QPolygonF([QPointF(x, -y) for x, y in t.toa_do])
            it = _Thua(t, poly)
            sc.addItem(it)
            self.thua.append(it)
            tam = poly.boundingRect().center()
            nhan = QGraphicsSimpleTextItem(str(t.so_thua), it)
            nhan.setFont(font)
            nhan.setFlag(QGraphicsSimpleTextItem.GraphicsItemFlag.ItemIgnoresTransformations, True)   # chữ cỡ cố định trên màn hình
            nhan.setPos(tam)
            br = nhan.boundingRect()                     # canh giữa thửa (chữ không đổi cỡ khi phóng: dời theo điểm ảnh)
            nhan.setTransform(QTransform.fromTranslate(-br.width() / 2, -br.height() / 2))
            nhan.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._nhan.append(nhan)
        self.vua()

    def vua(self) -> None:
        r = self.scene().itemsBoundingRect()
        if not r.isEmpty():
            self.fitInView(r.adjusted(-r.width() * .03, -r.height() * .03, r.width() * .03, r.height() * .03),
                           Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, e):
        k = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.scale(k, k)

    @staticmethod
    def _diem(e):
        return e.position().toPoint() if hasattr(e, 'position') else e.pos()      # Qt5: pos()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        p = self._diem(e)
        if e.button() == Qt.MouseButton.LeftButton and self._diem_bam is not None and (p - self._diem_bam).manhattanLength() < 5:
            self.bam_diem(p)                              # bấm (không kéo) vào thửa

    def mousePressEvent(self, e):
        self._diem_bam = self._diem(e)
        super().mousePressEvent(e)

    def bam_diem(self, diem) -> int | None:
        """Thửa tại điểm màn hình: phát bam_ho nếu thửa có hộ. Trả mã hộ."""
        for it in self.items(diem):
            if isinstance(it, _Thua) and it.t.ma_ho is not None:
                self.bam_ho.emit(it.t.ma_ho)
                return it.t.ma_ho
        return None

    def tim(self, so_thua: str) -> bool:
        """Phóng tới thửa số so_thua (tờ đang xem)."""
        for it in self.thua:
            if it.t.so_thua == str(so_thua).strip().lstrip('0'):
                self.fitInView(it.boundingRect().adjusted(-30, -30, 30, 30), Qt.AspectRatioMode.KeepAspectRatio)
                it.setSelected(True)
                return True
        return False


class HopBanDo(QDialog):
    """Cửa sổ bản đồ thửa đất (không chặn cửa sổ chính): lọc tờ, tìm thửa, chú giải màu, bấm thửa mở hồ sơ hộ (mo_ho(mã hộ))."""

    def __init__(self, con, parent=None, mo_ho=None, nhap=None):
        super().__init__(parent)
        self.con, self.mo_ho, self.nhap = con, mo_ho, nhap
        self.setWindowTitle('Bản đồ thửa đất - tình trạng đồng thuận')
        self.resize(1150, 760)
        self.cb_to = QComboBox()
        self.cb_to.currentIndexChanged.connect(lambda _: self.nap())
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Số thửa → Enter')
        self.o_tim.setMaximumWidth(150)
        self.o_tim.returnPressed.connect(lambda: self.view.tim(self.o_tim.text()) or self.lb.setText(
            f'Không có thửa {self.o_tim.text()} trên tờ đang xem.'))
        b_vua = QPushButton('Vừa khung')
        b_vua.clicked.connect(lambda: self.view.vua())
        b_nhap = QPushButton('Nhập bản vẽ CAD (.dxf)…')
        b_nhap.clicked.connect(lambda: self._nhap())
        h = QHBoxLayout()
        h.addWidget(QLabel('Tờ bản đồ:'))
        h.addWidget(self.cb_to)
        h.addWidget(QLabel('Tìm thửa:'))
        h.addWidget(self.o_tim)
        h.addWidget(b_vua)
        h.addStretch(1)
        h.addWidget(b_nhap)
        chu_giai = QHBoxLayout()
        self.lb_dem = {}
        for k, (ten, mau) in ban_do_cad.TRANG_THAI.items():
            o = QLabel()
            o.setFixedSize(14, 14)
            o.setStyleSheet(f'QLabel {{ background: {mau}; border-radius: 3px; }}')
            lb = QLabel(ten)
            self.lb_dem[k] = lb
            chu_giai.addWidget(o)
            chu_giai.addWidget(lb)
            chu_giai.addSpacing(14)
        chu_giai.addStretch(1)
        self.view = KhungBanDo(self)
        self.view.bam_ho.connect(self._bam_ho)
        self.lb = QLabel('Lăn chuột để phóng to / thu nhỏ, kéo để di chuyển, bấm vào thửa để mở hồ sơ hộ.')
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        b_nhap.setVisible(nhap is not None)      # SAU khi bố cục đã gắn vào hộp (1.0.16: nút chưa có cha hiện thành cửa sổ rỗng)
        lo.addLayout(chu_giai)
        lo.addWidget(self.view, 1)
        lo.addWidget(self.lb)
        self.nap_to()

    def nap_to(self) -> None:
        self.cb_to.blockSignals(True)
        self.cb_to.clear()
        for t in ban_do_cad.ds_to(self.con):
            self.cb_to.addItem(f'Tờ {t}', t)
        if self.cb_to.count() > 1:
            self.cb_to.addItem('Tất cả các tờ', None)
        self.cb_to.blockSignals(False)
        self.nap()

    def nap(self) -> None:
        ds = ban_do_cad.doc_ban_do(self.con, self.cb_to.currentData()) if self.cb_to.count() else []
        self.view.ve(ds)
        dem = {k: 0 for k in ban_do_cad.TRANG_THAI}
        for t in ds:
            dem[t.trang_thai] += 1
        for k, lb in self.lb_dem.items():
            lb.setText(f'{ban_do_cad.TRANG_THAI[k][0]}: {dem[k]}')
        if not ds:
            self.lb.setText('Dự án chưa có bản đồ: bấm "Nhập bản vẽ CAD (.dxf)…" (hoặc menu Dữ liệu) để nhập ranh thửa từ bản vẽ địa chính.')

    def _bam_ho(self, ma: int) -> None:
        if self.mo_ho is not None:
            self.mo_ho(ma)

    def _nhap(self) -> None:
        if self.nhap is not None and self.nhap():
            self.nap_to()
