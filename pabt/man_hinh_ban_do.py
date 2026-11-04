"""Màn hình bản đồ thửa đất (0.9.87): HopNhapCad (nhập bản vẽ .dxf - ban_do_cad; 1.0.32: cả bản đồ .kml / .kmz - ban_do_kml, tọa độ
WGS84 đổi sang VN-2000 theo kinh tuyến trục) và HopBanDo (bản đồ vẽ bằng QGraphicsView: phóng to bằng
con lăn, kéo để di chuyển, tô màu theo đồng thuận - xanh đã đồng thuận, đỏ chưa đồng thuận, vàng chưa lấy ý kiến, xám chưa gắn hộ;
BẤM thửa -> mở hồ sơ, phương án của hộ). Vẽ bằng Qt có sẵn (người dùng chọn 14/10/2026 thay Leaflet / QWebEngine: bộ cài không tăng
~300 MB, chạy cả Win 7 32-bit, không cần mạng). 30/10/2026 (phương án đột phá 4 - bản đồ làm trung tâm): tô màu theo đồng thuận / tiến
độ theo hộ (8 giai đoạn của pheu_tien_do) / lệch diện tích bản đồ - hồ sơ; nền ảnh vệ tinh tùy chọn (nen_ban_do, tải ở luồng phụ - NapNen,
mặc định tắt, chỉ gửi tọa độ ô ảnh); chuột phải thửa. 1.0.43: KML CAD (LineString = lưới/ranh Level, Point = nhãn) + 4 lớp + nút +/−/Vừa
+ tra cứu — cùng pipeline với LARC Mobile."""
from __future__ import annotations
from pathlib import Path

import math
import queue
import re
import threading

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
                               QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsPolygonItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QMessageBox, QPushButton, QSlider, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import ban_do_cad, ban_do_kml, nen_ban_do, toa_do
from .giao_dien import XepDong, chan_tin_hieu, chu_hien, con_tro_cho
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (kiểu riêng đổi theo tông nền)
from .lap_pa import LoiNhap
from .thong_bao import TEN_UD, chu_loi
from .tien import so_vn, vn

KHONG_LOP = '(không có)'


def _khoi(ds) -> QWidget:
    """Một khối của hàng XepDong: các widget xếp ngang sát nhau (không tách rời khi xuống dòng)."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    for x in ds:
        h.addWidget(x)
    return w


# ---------------------------------------------------------------- nhập bản vẽ
class HopNhapCad(QDialog):
    """Chọn file .dxf / .kml / .kmz, lớp ranh thửa / ranh thu hồi (DXF) hoặc kinh tuyến trục (KML), số tờ -> xem trước -> lưu vào dự án
    (tùy chọn cập nhật DT thu hồi)."""
    im_lang = False

    def __init__(self, con, parent=None, file=None):
        super().__init__(parent)
        self.con, self.kq, self.file = con, None, None
        self.setWindowTitle('Nhập bản đồ thửa đất (.dxf, .kml, .kmz)')
        self.resize(1100, 680)
        self.o_file = QLineEdit()
        self.o_file.setReadOnly(True)
        b_chon = QPushButton('Chọn file .dxf / .kml / .kmz…')
        b_chon.clicked.connect(lambda: self.chon_file())
        self.cb_thua, self.cb_ranh = QComboBox(), QComboBox()
        self.o_to = QLineEdit()
        self.o_to.setPlaceholderText('tự tìm trong bản vẽ / tên file')
        self.o_to.setMaximumWidth(160)
        # kinh tuyến trục VN-2000 để đổi tọa độ GPS của file KML (bản vẽ .dxf vốn là VN-2000: không dùng)
        self.cb_kt = QComboBox()
        self.cb_kt.setEditable(True)
        for v in toa_do.DS_KINH_TUYEN:
            self.cb_kt.addItem(toa_do.chu_kinh_tuyen(v), v)
        kt = toa_do.kinh_tuyen_truc()
        i = self.cb_kt.findData(kt)
        if i < 0:
            self.cb_kt.addItem(toa_do.chu_kinh_tuyen(kt), kt)
            i = self.cb_kt.count() - 1
        self.cb_kt.setCurrentIndex(i)
        self.cb_kt.setToolTip('Kinh tuyến trục VN-2000 của tỉnh (Đồng Nai 107°45\') - dùng khi đổi tọa độ GPS của file .kml / .kmz')
        self.cb_kt.setEnabled(False)
        b_phan_tich = QPushButton('Phân tích')
        b_phan_tich.clicked.connect(lambda: self.phan_tich())
        h = QHBoxLayout()
        h.addWidget(self.o_file, 1)
        h.addWidget(b_chon)
        f = QFormLayout()
        f.addRow('File bản vẽ:', h)
        h2 = QHBoxLayout()
        for nhan, w in (('Lớp ranh thửa:', self.cb_thua), ('Lớp ranh thu hồi:', self.cb_ranh), ('Số tờ:', self.o_to),
                        ('Kinh tuyến trục:', self.cb_kt)):
            h2.addWidget(QLabel(nhan))
            h2.addWidget(w, 1 if w in (self.cb_thua, self.cb_ranh) else 0)
        h2.addWidget(b_phan_tich)
        f.addRow('', h2)
        self.bang = QTableWidget(0, 9)
        self.bang.setHorizontalHeaderLabels(['Cập nhật DT\nthu hồi', 'Tờ', 'Thửa', 'Loại đất', 'DT nhãn\n(m²)', 'DT hình\n(m²)',
                                             'DT trong ranh\n(m²)', 'Hồ sơ hiện tại', 'Nhãn trên bản vẽ'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.lb = QLabel('Bản vẽ .dxf: ranh thửa là hình khép kín (polyline đóng), nhãn số thửa / diện tích / loại đất đặt bên trong thửa. '
                         'Bản đồ .kml / .kmz: mỗi đa giác một thửa, số thửa / tờ (hoặc tiểu khu, khoảnh, lô) ở tên hay dữ liệu kèm; '
                         'đa giác tên "ranh…" là ranh thu hồi.')
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

    def la_kml(self) -> bool:
        return self.file is not None and self.file.suffix.lower() in ban_do_kml.DUOI_KML

    def chon_file(self, file=None) -> bool:
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn bản đồ thửa đất', '',
                                                  'Bản đồ (*.dxf *.dwg *.kml *.kmz);;Bản vẽ CAD (*.dxf *.dwg);;Google Earth (*.kml *.kmz)')
            if not file:
                return False
        if Path(file).suffix.lower() in ban_do_kml.DUOI_KML:          # KML / KMZ: không có lớp; đổi tọa độ theo kinh tuyến trục
            self.file = Path(file)
            self.o_file.setText(str(file))
            for cb in (self.cb_thua, self.cb_ranh):
                with chan_tin_hieu(cb):
                    cb.clear()
                    cb.addItem('(KML: đa giác)', None)
                cb.setEnabled(False)
            self.cb_kt.setEnabled(True)
            return self.phan_tich()
        for cb in (self.cb_thua, self.cb_ranh):
            cb.setEnabled(True)
        self.cb_kt.setEnabled(False)
        try:
            with con_tro_cho():
                lop = ban_do_cad.doc_lop(file)
        except ban_do_cad.LoiCad as e:
            self._bao(str(e), True)
            return False
        self.file = Path(file)
        self.o_file.setText(str(file))
        with chan_tin_hieu(self.cb_thua), chan_tin_hieu(self.cb_ranh):     # nạp ô chọn một lượt, không phát tín hiệu từng mục
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

    def _khoa_tham_so(self) -> tuple:
        """Tham số của một lần phân tích (file + mtime, lớp, số tờ, kinh tuyến trục) - trùng lần trước thì không phân tích lại."""
        try:
            mt = self.file.stat().st_mtime_ns
        except OSError:
            mt = None
        return (str(self.file), mt, self.cb_thua.currentData(), self.cb_ranh.currentData(), self.o_to.text().strip(),
                self.cb_kt.currentText() if self.la_kml() else '')

    def phan_tich(self) -> bool:
        if self.file is None:
            return False
        khoa = self._khoa_tham_so()
        if self.kq is not None and khoa == getattr(self, '_khoa_ts_cu', None):     # 1.0.33: bấm Phân tích lại với cùng tham số
            return True
        try:
            with con_tro_cho():
                if self.la_kml():
                    self.kq = ban_do_kml.phan_tich_kml(self.file, self.o_to.text().strip() or None, self.kinh_tuyen())
                else:
                    self.kq = ban_do_cad.phan_tich(self.file, self.cb_thua.currentData(), self.cb_ranh.currentData(),
                                                   self.o_to.text().strip() or None)
        except (ban_do_cad.LoiCad, ValueError) as e:
            self._bao(str(e), True)
            return False
        if not self.o_to.text().strip():
            self.o_to.setPlaceholderText(f'tự tìm: {self.kq.so_to or "?"}')
        i = self.cb_thua.findData(self.kq.lop_thua)
        if i >= 0 and i != self.cb_thua.currentIndex():
            self.cb_thua.blockSignals(True)
            self.cb_thua.setCurrentIndex(i)
            self.cb_thua.blockSignals(False)
        self._khoa_ts_cu = khoa
        cm = ban_do_cad.chi_muc_thua(self.con)
        self.bang.setUpdatesEnabled(False)                     # đổ cả bảng rồi vẽ một lần
        try:
            self._do_bang(cm)
        finally:
            self.bang.setUpdatesEnabled(True)
        return True

    def _do_bang(self, cm: dict) -> None:
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
        self.lb.setText(f'{len(self.kq.thua)} thửa (tờ {self.kq.so_to or "?"} - {self.kq.lop_thua}), {so_khop} thửa khớp hồ sơ. '
                        'Đánh dấu cột đầu để cập nhật DT thu hồi theo bản vẽ (DT trong ranh nếu có lớp ranh thu hồi).' +
                        ('\n' + '\n'.join(self.kq.canh_bao[:6]) if self.kq.canh_bao else ''))

    def kinh_tuyen(self) -> float:
        """Kinh tuyến trục đang chọn / gõ ("107°45'", "107.75"). Sai -> ValueError (thông báo tiếng Việt)."""
        i = self.cb_kt.currentIndex()
        if i >= 0 and self.cb_kt.currentText() == self.cb_kt.itemText(i) and self.cb_kt.itemData(i) is not None:
            return float(self.cb_kt.itemData(i))
        return toa_do.doc_kinh_tuyen(self.cb_kt.currentText())

    def luu(self) -> dict | None:
        if not self.kq or not self.kq.thua:
            self._bao('Chưa có thửa nào để lưu: chọn file và bấm Phân tích.', True)
            return None
        cap = {(ban_do_cad._khoa(t.so_to), ban_do_cad._khoa(t.so_thua)) for r, t in enumerate(self.kq.thua)
               if self.bang.item(r, 0).checkState() == Qt.CheckState.Checked}
        try:
            with con_tro_cho():
                kq = ban_do_cad.luu(self.con, self.kq, cap, self.o_loai.isChecked())
        except (ban_do_cad.LoiCad, OSError, LoiNhap) as e:
            self._bao(chu_loi('Không lưu được bản đồ', e), True)
            return None
        self._bao(f'Đã lưu {kq["luu"]} thửa vào bản đồ dự án ({kq["khop"]} thửa khớp hồ sơ, cập nhật DT thu hồi {kq["cap_nhat"]} thửa).')
        if kq.get('nhieu_dong') or kq.get('vuot'):
            self._bao('Chưa cập nhật DT thu hồi của ' + '; '.join(x for x in (f'{len(kq["nhieu_dong"])} thửa có nhiều dòng hồ sơ ({", ".join(kq["nhieu_dong"][:10])}): sửa tay ở hồ sơ hộ' if kq['nhieu_dong'] else '', f'{len(kq["vuot"])} thửa có DT vượt DT nguyên thửa ({", ".join(kq["vuot"][:10])})' if kq['vuot'] else '') if x) + '.', True)
        self.accept()
        return kq


# ---------------------------------------------------------------- bản đồ
def mau_dong_thuan(t: ban_do_cad.ThuaBanDo) -> tuple:
    """(khóa, tên, màu) theo đồng thuận - cách tô mặc định (như trước 30/10/2026)."""
    ten, mau = ban_do_cad.TRANG_THAI[t.trang_thai]
    return t.trang_thai, ten, mau


class _Thua(QGraphicsPolygonItem):
    def __init__(self, t: ban_do_cad.ThuaBanDo, poly: QPolygonF, mau_cua=None, co_nen: bool = False, do_dam: int | None = None):
        super().__init__(poly)
        self.t = t
        self.khoa_mau, ten, mau_hex = (mau_cua or mau_dong_thuan)(t)
        mau = QColor(mau_hex)
        nen = QColor(mau)
        nen.setAlpha(do_dam if do_dam is not None else (80 if co_nen else 110))   # có ảnh vệ tinh: tô nhạt hơn để thấy ảnh
        self.setBrush(QBrush(nen))
        but = QPen(QColor('#FFFFFF') if co_nen else mau.darker(140))
        but.setCosmetic(True)                            # nét 1 px mọi mức phóng
        self.setPen(but)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor if t.ma_ho is not None else Qt.CursorShape.ArrowCursor)
        dt = f'{so_vn(t.dt_hinh)} m²' + (f' (trong ranh {so_vn(t.dt_trong_ranh)} m²)' if t.dt_trong_ranh not in (None, '') else '')
        lech = ''
        k, ty, bd, hs, cach = ban_do_cad.lech_dien_tich(t)
        if ty is not None:
            lech = f'\nBản đồ {so_vn(bd)} m² / hồ sơ {so_vn(hs)} m² - lệch {vn(ty * 100, 1)}% ({cach})'
        self.setToolTip(f'Thửa {t.so_thua} tờ {t.so_to} {t.loai_dat}\n{dt}{lech}\n' +
                        (f'Hộ {t.ma_ho}: {t.ho_ten}\n{ten} - bấm để mở phương án, chuột phải xem thêm' if t.ma_ho is not None else ten))

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


# lớp KML / KMZ mở để XEM (31/10/2026 - như LARC Mobile): không ghi vào dự án; vẽ trên thửa của dự án, dưới chuột không chặn bấm thửa
# 1.0.43: vẽ đúng bản CAD (LineString = lưới / ranh Level, Point = nhãn chứ không phải chấm) + 4 lớp + nút +/−/Vừa trên bản đồ
MAU_KML_VUNG, MAU_KML_DUONG, MAU_KML_DIEM = '#FACC15', '#38BDF8', '#FF3B30'
MAU_DANH_DAU = '#22D3EE'                 # viền thửa tìm được / thửa của hộ đang xem
KML_NHAN_TOI_DA = 3000                   # quá số đối tượng này: không ghi tên lên từng vùng (rối, chậm) - tên vẫn ở chú thích khi rê chuột
LOP_BD = (('duong', 'Lưới thửa & ranh'), ('nhan', 'Số thửa, loại đất, DT'), ('moc', 'Ranh mốc'),
          ('ghi_chu', 'Ghi chú quy hoạch'))
THE_KML = (('tat_ca', 'Tất cả'), ('thua', 'Thửa & DT'), ('moc', 'Mốc ranh'), ('ghi_chu', 'Ghi chú'), ('duong', 'Đường ranh'))
_RE_THE_HTML = re.compile(r'<[^>]+>')


def _do_sang(hex_rgb: str) -> float:
    h = (hex_rgb or '').lstrip('#')
    if len(h) != 6:
        return 0.5
    n = int(h, 16)
    return (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255.0


def mau_ve(mau: str, co_nen: bool) -> str:
    """Màu đường / nhãn CAD: trắng trên nền lưới hoặc xám đậm trên ảnh vệ tinh thì đổi cho đọc được (cùng mauVe điện thoại)."""
    if not mau:
        return MAU_KML_DUONG if co_nen else '#2563EB'
    s = _do_sang(mau)
    if not co_nen and s > 0.82:
        return '#475569'
    if co_nen and s < 0.3:
        return '#CBD5E1'
    return mau


def _chu_thich_kml(pm, ten_file: str) -> str:
    dong = [pm.ten or '(không tên)']
    if pm.thu_muc:
        dong.append(f'Thư mục: {pm.thu_muc}')
    lop = ' · '.join(x for x in (getattr(pm, 'lop_cad', ''), ('bản vẽ ' + pm.ban_ve) if getattr(pm, 'ban_ve', '') else '') if x)
    if lop:
        dong.append(f'Lớp CAD: {lop}')
    mo_ta = ' '.join(_RE_THE_HTML.sub(' ', pm.mo_ta or '').split())
    if mo_ta:
        dong.append(mo_ta[:300])
    dong += [f'{k}: {v}' for k, v in list(pm.du_lieu.items())[:10] if str(v).strip()]
    dong.append(f'(lớp {ten_file} - chỉ xem, chưa nhập vào dự án)')
    return '\n'.join(dong)


class KhungBanDo(QGraphicsView):
    """Khung vẽ thửa. Tọa độ bản vẽ (y hướng lên) -> cảnh Qt (y hướng xuống): lật y. Bấm thửa có hộ -> tín hiệu bam_ho(mã hộ); chuột
    phải thửa -> tín hiệu menu_thua(ThuaBanDo, điểm màn hình toàn cục). Ảnh nền (dat_o_nen) nằm dưới thửa (z âm); lớp KML chỉ xem
    (ve_kml) trên thửa. khung_doi: vùng đang xem đổi (kéo, phóng, đổi cỡ) - nơi nghe nạp ô nền của vùng mới."""
    bam_ho = Signal(int)
    bam_cad = Signal(object)                             # 1.0.43: bấm đường / nhãn / mốc KML CAD -> dict thuộc tính
    toa_do_chuot = Signal(float, float)                  # (đông, bắc) VN-2000 dưới con trỏ (1.0.32)
    menu_thua = Signal(object, object)
    khung_doi = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor('#F8FAFC')))
        self.thua = []                                  # [_Thua]
        self._nhan = []
        self.o_nen = []                                 # [QGraphicsPixmapItem] ảnh nền
        self.o_khoa = {}                                # {(lớp, z, x, y): QGraphicsPixmapItem}
        self.kml = []                                   # [QGraphicsItem] lớp KML chỉ xem
        self.kml_thua = []                              # [((tờ, thửa) chuẩn, QGraphicsPathItem, mã hộ khớp | None)]
        self.kml_cad = []                               # [{'lop', 'it', 'tt', 'loai', 'an_xa'}] — 1.0.43 lớp CAD
        self.nhan_thua_cad = []                         # cụm số thửa + loại đất + DT (gom_cum_nhan_thua)
        self.lop_hien = {k for k, _t in LOP_BD}
        self.ho_ten = {}                                # {mã hộ: họ tên} - chú thích vùng KML khớp hồ sơ
        self._danh_dau = []                             # [(đối tượng, bút cũ)]
        self._vong_chon = []                            # hình nổi thêm (nhãn chữ không có bút)
        self.do_dam = None                             # độ đậm tô thửa (alpha 0-255); None = mặc định theo có / không nền
        self._diem_bam = None
        self._can_vua = False                           # vừa khung lại khi khung đổi cỡ, tới lúc người dùng tự phóng / kéo
        self._tl_kml = None
        self._tao_nut_phong()
        # kéo / cuộn: nghe TÍN HIỆU thanh cuộn (Qt tự ngắt khi hủy) - KHÔNG ghi đè scrollContentsBy: Qt gọi hàm ảo đó cả lúc đang hủy khung
        # (cảnh bị xóa -> thanh cuộn đổi) -> mã Python chạy trên đối tượng hủy dở -> sập (kiểm tra giao diện 31/10/2026)
        self._song = True                               # False: cửa sổ đã đóng / đang hủy - thôi phát khung_doi
        self.horizontalScrollBar().valueChanged.connect(self._cuon)
        self.verticalScrollBar().valueChanged.connect(self._cuon)

    def _tao_nut_phong(self) -> None:
        """Nút + / − / Vừa góc trên phải bản đồ (cùng bộ với LARC Mobile)."""
        hop = QWidget(self)
        hop.setObjectName('nut_phong_bd')
        dat_kieu_theo_tong(hop,
            'QWidget#nut_phong_bd { background: rgba(255,255,255,230); border: 1px solid #CBD5E1; border-radius: 8px; }'
            'QToolButton { min-width: 32px; min-height: 28px; font: 14px "Segoe UI"; border: 0; border-radius: 6px; }'
            'QToolButton:hover { background: #EFF6FF; }')
        v = QVBoxLayout(hop)
        v.setContentsMargins(3, 3, 3, 3)
        v.setSpacing(1)
        for chu, fn, tt in (('+', lambda: self.phong(), 'Phóng to'), ('−', lambda: self.thu(), 'Thu nhỏ'),
                            ('Vừa', lambda: self.vua(), 'Vừa khung')):
            b = QToolButton(hop)
            b.setText(chu)
            b.setToolTip(tt)
            b.clicked.connect(fn)
            v.addWidget(b)
        hop.adjustSize()
        hop.raise_()
        hop.show()
        self.hop_nut = hop

    def _dat_nut_phong(self) -> None:
        hop = getattr(self, 'hop_nut', None)
        if hop is None:
            return
        vp = self.viewport()
        hop.move(max(8, vp.width() - hop.width() - 12), 12)
        hop.raise_()

    def phong(self, k: float = 1.25) -> None:
        self._can_vua = False
        self.scale(k, k)
        self.khung_doi.emit()

    def thu(self) -> None:
        self.phong(0.8)

    def _cuon(self, *_):
        if self._song:
            self.khung_doi.emit()

    def tat(self) -> None:
        """Cửa sổ đóng: thôi phát tín hiệu, bỏ tham chiếu tới hình trong cảnh (cảnh hủy các hình khi cửa sổ bị hủy - giữ tham chiếu
        Python tới hình đã hủy rồi chạm vào là sập)."""
        self._song = False
        for sb in (self.horizontalScrollBar(), self.verticalScrollBar()):
            try:
                sb.valueChanged.disconnect(self._cuon)
            except (RuntimeError, TypeError):
                pass
        self._danh_dau, self.kml_thua = [], []

    def ve(self, ds: list, mau_cua=None, co_nen: bool = False, giu_khung: bool = False) -> None:
        """Vẽ lại thửa (xóa cả ảnh nền và lớp KML - nơi gọi vẽ lại nếu cần). mau_cua(t) -> (khóa, tên, màu); giu_khung: không về vừa
        khung (chỉ đổi cách tô màu)."""
        tf, tam_cu = self.transform(), self.mapToScene(self.viewport().rect().center())
        sc = self.scene()
        sc.clear()
        self.thua, self._nhan, self.o_nen, self.o_khoa, self.kml = [], [], [], {}, []
        self.kml_thua, self.kml_cad, self.nhan_thua_cad, self._danh_dau, self._vong_chon = [], [], [], [], []
        self._tl_kml = None
        font = QFont('Segoe UI', 8)
        font_nen = QFont('Segoe UI', 9)
        font_nen.setBold(True)
        for t in ds:
            poly = QPolygonF([QPointF(x, -y) for x, y in t.toa_do])
            it = _Thua(t, poly, mau_cua, co_nen, self.do_dam)
            sc.addItem(it)
            self.thua.append(it)
            tam = poly.boundingRect().center()
            nhan = QGraphicsSimpleTextItem(str(t.so_thua), it)
            nhan.setFont(font)
            if co_nen:                                   # chữ trắng đậm, viền tối mờ: đọc được trên ảnh vệ tinh
                nhan.setFont(font_nen)
                nhan.setBrush(QBrush(QColor('#FFFFFF')))
                nhan.setPen(QPen(QColor(15, 23, 42, 110), 0))
            nhan.setFlag(QGraphicsSimpleTextItem.GraphicsItemFlag.ItemIgnoresTransformations, True)   # chữ cỡ cố định trên màn hình
            nhan.setPos(tam)
            br = nhan.boundingRect()                     # canh giữa thửa (chữ không đổi cỡ khi phóng: dời theo điểm ảnh)
            nhan.setTransform(QTransform.fromTranslate(-br.width() / 2, -br.height() / 2))
            nhan.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._nhan.append(nhan)
        if giu_khung:
            self.setTransform(tf)
            self.centerOn(tam_cu)
        else:
            self._can_vua = True                        # vẽ trước khi cửa sổ hiện: khung chưa đúng cỡ - vừa lại ở resizeEvent
            self.vua()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._dat_nut_phong()
        if self._can_vua:
            self.vua()
        if getattr(self, '_song', False):
            self.khung_doi.emit()

    def khung_thua(self) -> QRectF:
        """Khung bao các thửa và lớp KML (không tính ảnh nền)."""
        r = QRectF()
        for it in (*self.thua, *self.kml):
            r = r.united(it.sceneBoundingRect())
        return r

    def khung_dang_xem(self) -> QRectF:
        """Vùng cảnh đang hiện trên khung."""
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def m_moi_diem(self) -> float:
        """Mét (đơn vị cảnh = mét VN-2000) trên một điểm màn hình ở mức phóng hiện tại."""
        k = abs(self.transform().m11())
        return 1.0 / k if k else 1.0

    def dat_do_dam(self, alpha: int) -> None:
        """Độ đậm tô thửa (alpha 0-255) - không vẽ lại cảnh."""
        self.do_dam = max(0, min(255, int(alpha)))
        for it in self.thua:
            c = QColor(it.brush().color())
            c.setAlpha(self.do_dam)
            it.setBrush(QBrush(c))

    # ---- lớp KML chỉ xem
    def ve_kml(self, lop: list, kt: float, chi_muc: dict | None = None, co_nen: bool = False) -> int:
        """Vẽ các lớp KML: lop = [(tên file, [PlacemarkKml])], tọa độ WGS84 đổi sang VN-2000 theo kinh tuyến trục kt.

        Bản CAD (MicroStation / gCadas): LineString = lưới thửa & ranh (màu Style, lớp Level), Point = nhãn (số thửa / loại đất /
        DT / mốc / ghi chú) — không vẽ chấm 8 px cho mọi điểm. Vùng đa giác thửa vẫn vẽ như trước. chi_muc {(tờ, thửa) chuẩn:
        (mã thửa, mã hộ, DT thu hồi, loại đất)} + ho_ten: chú thích khớp hồ sơ. Trả số đối tượng."""
        self.xoa_kml()
        chi_muc = chi_muc or {}

        def diem(kd, vd):
            d, b = toa_do.wgs84_sang_vn2000(vd, kd, kt)
            return QPointF(d, -b)

        def but(mau, rong=1.6):
            p = QPen(QColor(mau_ve(mau, co_nen)), max(1.2, min(4.0, float(rong or 1) * 1.4)))
            p.setCosmetic(True)
            p.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            return p

        tong = sum(len(pm.da_giac) + len(pm.duong) + len(pm.diem) for _, ds in lop for pm in ds)
        ghi_ten = tong <= KML_NHAN_TOI_DA
        font = QFont('Segoe UI', 8)
        font.setBold(True)
        font_nhan = QFont('Segoe UI', 9)
        font_nhan.setBold(True)
        font_phu = QFont('Segoe UI', 8)
        nen_vung = QColor(MAU_KML_VUNG)
        nen_vung.setAlpha(28)
        diem_cad = []
        for ten_file, ds in lop:
            for pm in ds:
                chu = _chu_thich_kml(pm, ten_file)
                to, thua = ban_do_kml.so_hieu(pm)[:2]
                khoa = (ban_do_cad._khoa(to), ban_do_cad._khoa(thua)) if thua else None
                hs = chi_muc.get(khoa) if khoa else None
                if thua:
                    chu = f'Thửa {thua}' + (f' tờ {to}' if to else '') + '\n' + chu
                if hs is not None:
                    chu += (f'\nKhớp hồ sơ dự án: hộ {self.ho_ten.get(hs[1], hs[1])}' +
                            (f', thu hồi {so_vn(hs[2])} m²' if hs[2] not in (None, '') else ''))
                try:
                    for ngoai, lo in pm.da_giac:
                        xs = [p[0] for p in ngoai]
                        ys = [p[1] for p in ngoai]
                        lat0 = ngoai[0][1] if ngoai else 0
                        kx = 111320.0 * max(0.2, abs(math.cos(math.radians(lat0))))
                        co_m = max((max(xs) - min(xs)) * kx, (max(ys) - min(ys)) * 110540.0) if ngoai else 999
                        if co_m < ban_do_kml.CO_VONG_MOC and len(ngoai) >= ban_do_kml.SO_DINH_VONG_MOC:
                            tam = diem((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
                            it = QGraphicsEllipseItem(-5, -5, 10, 10)
                            it.setPos(tam)
                            it.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                            it.setPen(but('#FF3B30', 1.5))
                            it.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                            tt = dict(kieu='vong_moc', lop='moc', chu=pm.ten, lop_cad=pm.lop_cad, ban_ve=pm.ban_ve,
                                      lat=ngoai[0][1], lon=ngoai[0][0])
                            self._them_kml(it, chu, 4, 'moc', tt, an_xa=True)
                            continue
                        p = QPainterPath()
                        p.setFillRule(Qt.FillRule.OddEvenFill)
                        for vong in (ngoai, *lo):
                            p.addPolygon(QPolygonF([diem(kd, vd) for kd, vd in vong]))
                            p.closeSubpath()
                        it = QGraphicsPathItem(p)
                        it.setPen(but(MAU_KML_VUNG, 1.6))
                        it.setBrush(QBrush(nen_vung))
                        self._them_kml(it, chu, 2, 'duong', dict(kieu='vung', lop='duong', ten=pm.ten, lop_cad=pm.lop_cad,
                                                                ban_ve=pm.ban_ve, so_to=to, so_thua=thua))
                        if khoa is not None:
                            self.kml_thua.append((khoa, it, hs[1] if hs else None))
                        nhan = thua or pm.ten
                        if ghi_ten and nhan and len(nhan) <= 24:
                            self._nhan_kml(nhan, p.boundingRect().center(), font, '#FFFFFF')
                    mau_d = pm.mau_duong or MAU_KML_DUONG
                    for d in pm.duong:
                        p = QPainterPath(diem(*d[0]))
                        pts = [diem(*d[0])]
                        for kd, vd in d[1:]:
                            q = diem(kd, vd)
                            p.lineTo(q)
                            pts.append(q)
                        it = QGraphicsPathItem(p)
                        it.setPen(but(mau_d, pm.rong_duong or 1))
                        tt = dict(kieu='duong', lop='duong', ten=pm.ten, mo_ta=pm.mo_ta, lop_cad=pm.lop_cad, ban_ve=pm.ban_ve,
                                  mau=mau_d, so_dinh=len(d), lat=d[0][1], lon=d[0][0], du_lieu=pm.du_lieu, pts=pts)
                        self._them_kml(it, chu, 3, 'duong', tt)
                    for kd, vd in pm.diem:
                        loai = ban_do_kml.loai_nhan(pm.ten, pm.lop_cad)
                        if loai == 'ky_hieu':
                            continue
                        tam = diem(kd, vd)
                        tt = dict(kieu='diem', lop='moc' if loai == 'moc' else ('ghi_chu' if loai == 'ghi_chu' else 'nhan'),
                                  loai=loai, chu=pm.ten, lop_cad=pm.lop_cad, ban_ve=pm.ban_ve, lat=vd, lon=kd,
                                  du_lieu=pm.du_lieu, x=tam.x(), y=tam.y())
                        diem_cad.append(tt)
                        if loai == 'moc':
                            it = QGraphicsPolygonItem(QPolygonF([QPointF(0, -6), QPointF(5, 0), QPointF(0, 6), QPointF(-5, 0)]))
                            it.setPos(tam)
                            it.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                            it.setBrush(QBrush(QColor('#FF3B30')))
                            it.setPen(QPen(QColor('#FACC15'), 1.5))
                            self._them_kml(it, chu, 4, 'moc', tt)
                            if ghi_ten and pm.ten:
                                nh = self._nhan_kml(pm.ten, tam, font_nhan, '#FDE68A', lech=(8, -14))
                                self._gan_cad(nh, 'moc', tt, an_xa=True)
                        else:
                            if not ghi_ten or not pm.ten:
                                continue
                            dam = loai == 'thua'
                            f = font_nhan if dam else font_phu
                            mau = mau_ve(pm.mau_nhan or ('#FACC15' if loai != 'ghi_chu' else '#E2E8F0'), co_nen)
                            nh = self._nhan_kml(pm.ten, tam, f, mau)
                            self._gan_cad(nh, tt['lop'], tt, an_xa=True)
                            if khoa is not None and loai == 'thua':
                                self.kml_thua.append((khoa, nh, hs[1] if hs else None))
                except (ValueError, ZeroDivisionError, OverflowError):
                    continue
        self.nhan_thua_cad = ban_do_kml.gom_cum_nhan_thua(diem_cad)
        for c in self.nhan_thua_cad:
            to, th = c.get('so_to') or '', c.get('so_thua') or ''
            if not th:
                continue
            khoa = (ban_do_cad._khoa(to), ban_do_cad._khoa(th))
            if any(k == khoa for k, _it, _m in self.kml_thua):
                continue
            hs = chi_muc.get(khoa)
            it = QGraphicsEllipseItem(-2, -2, 4, 4)
            it.setPos(QPointF(c['x'], c['y']))
            it.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            it.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            it.setPen(QPen(Qt.PenStyle.NoPen))
            chu = f'Thửa {th}' + (f' tờ {to}' if to else '') + (f' {c.get("chu_ld") or ""}' if c.get('chu_ld') else '')
            self._them_kml(it, chu, 1, 'nhan', dict(c, kieu='nhan_thua', lop='nhan'), an_xa=True)
            self.kml_thua.append((khoa, it, hs[1] if hs else None))
        self.cap_nhat_hien_kml(ep=True)
        return len(self.kml)

    def _gan_cad(self, it, lop: str, tt: dict | None, an_xa: bool = False) -> None:
        it.setData(0, lop)
        it.setData(2, tt or {})
        self.kml_cad.append({'lop': lop, 'it': it, 'tt': tt or {}, 'an_xa': an_xa, 'loai': (tt or {}).get('loai', '')})

    def _them_kml(self, it, chu: str, z: float, lop: str = '', tt=None, an_xa: bool = False) -> None:
        it.setZValue(z)
        it.setToolTip(chu)
        it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)     # không chặn kéo / bấm thửa của dự án
        self.scene().addItem(it)
        self.kml.append(it)
        if lop:
            self._gan_cad(it, lop, tt, an_xa)

    def _nhan_kml(self, ten: str, tam: QPointF, font: QFont, mau: str, lech=None):
        nhan = QGraphicsSimpleTextItem(ten)
        nhan.setFont(font)
        nhan.setBrush(QBrush(QColor(mau)))
        nhan.setPen(QPen(QColor(15, 23, 42, 140), 0))
        nhan.setFlag(QGraphicsSimpleTextItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        nhan.setPos(tam)
        br = nhan.boundingRect()
        dx, dy = lech if lech else (-br.width() / 2, -br.height() / 2)
        nhan.setTransform(QTransform.fromTranslate(dx, dy))
        nhan.setZValue(5)
        nhan.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.scene().addItem(nhan)
        self.kml.append(nhan)
        return nhan

    def dat_lop_hien(self, lop_hien) -> None:
        self.lop_hien = set(lop_hien)
        self.cap_nhat_hien_kml(ep=True)

    def cap_nhat_hien_kml(self, ep: bool = False) -> None:
        """Ẩn nhãn khi nhìn xa (còn đường ranh); bật / tắt 4 lớp CAD. Không vẽ chấm đè kín lưới thửa."""
        if not self.kml_cad:
            return
        k = abs(self.transform().m11())
        if not ep and self._tl_kml is not None:
            a, b = k + 1e-9, self._tl_kml + 1e-9
            if abs(math.log(a / b)) < 0.08:
                return
        self._tl_kml = k
        m = self.m_moi_diem()
        hien = self.lop_hien
        for rec in self.kml_cad:
            it, lop, an_xa, loai = rec['it'], rec['lop'], rec['an_xa'], rec['loai']
            if it.scene() is None:
                continue
            if lop not in hien:
                it.setVisible(False)
                continue
            if lop == 'duong':
                it.setVisible(True)
            elif lop == 'moc':
                it.setVisible(True if not an_xa else m < 4.0)
            elif lop == 'nhan':
                it.setVisible((not an_xa) or m < (2.2 if loai == 'thua' else 2.8))
            else:
                it.setVisible((not an_xa) or m < 3.5)

    def xoa_kml(self) -> None:
        for it in self.kml:
            if it.scene() is not None:
                self.scene().removeItem(it)
        self.kml, self.kml_thua, self.kml_cad, self.nhan_thua_cad = [], [], [], []
        self._tl_kml = None
        self._vong_chon = []
        self.danh_dau([])

    # ---- đánh dấu, phóng tới thửa tìm được (máy không có GPS: tìm theo số tờ / thửa)
    def danh_dau(self, ds_it: list, phong: bool = True) -> int:
        """Viền nổi các đối tượng (thửa dự án / vùng KML) và phóng tới chúng; ds_it rỗng = bỏ đánh dấu cũ. Trả số đối tượng."""
        for it, but in self._danh_dau:
            if it.scene() is not None:
                it.setPen(but)
                it.setZValue(it.data(1) if it.data(1) is not None else it.zValue())
        self._danh_dau = []
        for it in self._vong_chon:
            if it.scene() is not None:
                self.scene().removeItem(it)
        self._vong_chon = []
        r = QRectF()
        for it in ds_it:
            try:
                but_cu = QPen(it.pen())
            except (AttributeError, RuntimeError):
                but_cu = None
            if but_cu is not None and but_cu.style() != Qt.PenStyle.NoPen:
                self._danh_dau.append((it, but_cu))
                it.setData(1, it.zValue())
                p = QPen(QColor(MAU_DANH_DAU), 4)
                p.setCosmetic(True)
                it.setPen(p)
                it.setZValue(8)
            else:
                br = it.sceneBoundingRect()
                v = QGraphicsEllipseItem(br.adjusted(-12, -12, 12, 12))
                p = QPen(QColor(MAU_DANH_DAU), 3)
                p.setCosmetic(True)
                v.setPen(p)
                v.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                v.setZValue(9)
                v.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self.scene().addItem(v)
                self._vong_chon.append(v)
            r = r.united(it.sceneBoundingRect())
        if ds_it and phong and not r.isEmpty():
            self._can_vua = False
            le = max(r.width(), r.height()) * 0.6 + 20             # để thấy cả xung quanh thửa trên ảnh vệ tinh
            self.fitInView(r.adjusted(-le, -le, le, le), Qt.AspectRatioMode.KeepAspectRatio)
            self.khung_doi.emit()
        return len(ds_it)

    def vua(self) -> None:
        r = self.khung_thua()
        if not r.isEmpty():
            self.fitInView(r.adjusted(-r.width() * .03, -r.height() * .03, r.width() * .03, r.height() * .03),
                           Qt.AspectRatioMode.KeepAspectRatio)
            self.khung_doi.emit()

    def dat_o_nen(self, anh: bytes, goc: tuple, khoa: tuple | None = None, z_ve: float = -10) -> bool:
        """Đặt một ô ảnh nền: goc = (điểm cảnh trên-trái, trên-phải, dưới-trái) của ô - phép biến đổi affine (ô nhỏ: sai khác của
        phép chiếu VN-2000 so với Web Mercator không đáng kể). khoa (lớp, z, x, y): ô đã có thì thay. False: ảnh hỏng."""
        pm = QPixmap()
        if not pm.loadFromData(anh) or pm.isNull():
            return False
        tl, tr, bl = goc
        w, h = pm.width(), pm.height()
        it = QGraphicsPixmapItem(pm)
        it.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        it.setTransform(QTransform((tr.x() - tl.x()) / w, (tr.y() - tl.y()) / w, (bl.x() - tl.x()) / h, (bl.y() - tl.y()) / h,
                                   tl.x(), tl.y()))
        it.setZValue(z_ve)
        it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        if khoa is not None and khoa in self.o_khoa:
            self.bo_o([khoa])
        self.scene().addItem(it)
        self.o_nen.append(it)
        if khoa is not None:
            self.o_khoa[khoa] = it
        return True

    def bo_o(self, ds_khoa) -> None:
        """Bỏ các ô nền theo khóa (lớp, z, x, y)."""
        for k in list(ds_khoa):
            it = self.o_khoa.pop(k, None)
            if it is None:
                continue
            if it.scene() is not None:
                self.scene().removeItem(it)
            try:
                self.o_nen.remove(it)
            except ValueError:
                pass

    def bo_het_nen(self) -> None:
        for it in self.o_nen:
            if it.scene() is not None:
                self.scene().removeItem(it)
        self.o_nen, self.o_khoa = [], {}

    def contextMenuEvent(self, e):
        for it in self.items(e.pos()):
            if isinstance(it, _Thua):
                self.menu_thua.emit(it.t, e.globalPos())
                return
        super().contextMenuEvent(e)

    def wheelEvent(self, e):
        self._can_vua = False
        k = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.scale(k, k)
        self.khung_doi.emit()
        self.cap_nhat_hien_kml()

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
        self._can_vua = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if self.thua or self.kml:
            p = self.mapToScene(self._diem(e))
            self.toa_do_chuot.emit(p.x(), -p.y())

    def bam_diem(self, diem) -> int | None:
        """Thửa tại điểm màn hình: phát bam_ho nếu thửa có hộ. Trả mã hộ. Bấm nhãn / đường CAD -> bam_cad."""
        cad = self._cad_tai(diem)
        if cad is not None:
            self.bam_cad.emit(cad)
            return None
        for it in self.items(diem):
            if isinstance(it, _Thua) and it.t.ma_ho is not None:
                self.bam_ho.emit(it.t.ma_ho)
                return it.t.ma_ho
        return None

    def _cad_tai(self, diem) -> dict | None:
        """Đối tượng CAD gần điểm bấm (nhãn / mốc ≤ 16 px, đường ≤ 8 px) — cùng thứ tự ưu tiên với điện thoại."""
        if not self.kml_cad:
            return None
        tot, dm = None, 16.0
        for rec in self.kml_cad:
            it, lop, tt = rec['it'], rec['lop'], rec['tt']
            if not it.isVisible() or it.scene() is None or lop == 'duong':
                continue
            sp = self.mapFromScene(it.sceneBoundingRect().center())
            m = math.hypot(sp.x() - diem.x(), sp.y() - diem.y())
            if lop == 'moc':
                m -= 4
            if m < dm:
                dm, tot = m, tt
        if tot is not None:
            if tot.get('kieu') == 'diem' and tot.get('loai') in ('ld', 'dt', 'dt_th'):
                for c in self.nhan_thua_cad:
                    for k in ('ld', 'dt', 'dt_th'):
                        cap = c.get(k)
                        if cap and cap[0] is tot:
                            return c
            return tot
        if 'duong' not in self.lop_hien:
            return None
        dd, chon = 8.0, None
        canh = self.mapToScene(diem)
        for rec in self.kml_cad:
            if rec['lop'] != 'duong' or not rec['it'].isVisible():
                continue
            tt = rec['tt']
            pts = tt.get('pts') or []
            if len(pts) < 2:
                br = rec['it'].sceneBoundingRect()
                if br.contains(canh):
                    return tt
                continue
            for i in range(len(pts) - 1):
                a, b = self.mapFromScene(pts[i]), self.mapFromScene(pts[i + 1])
                ax, ay = a.x() - diem.x(), a.y() - diem.y()
                dx, dy = b.x() - a.x(), b.y() - a.y()
                L = dx * dx + dy * dy
                u = max(0.0, min(1.0, -(ax * dx + ay * dy) / L)) if L else 0.0
                m = math.hypot(ax + u * dx, ay + u * dy)
                if m < dd:
                    dd, chon = m, tt
        return chon

    def tim(self, so_thua: str) -> bool:
        """Phóng tới thửa số so_thua (tờ đang xem)."""
        for it in self.thua:
            if it.t.so_thua == str(so_thua).strip().lstrip('0'):
                self._can_vua = False
                self.fitInView(it.boundingRect().adjusted(-30, -30, 30, 30), Qt.AspectRatioMode.KeepAspectRatio)
                it.setSelected(True)
                return True
        return False


class NapNen:
    """Tải ảnh nền vệ tinh ở LUỒNG PHỤ (chỉ nen_ban_do.tai_o - không đụng Qt), luồng giao diện lấy kết quả qua hàng đợi mỗi NHIP_MS
    và đặt ô lên KhungBanDo. bat_dau() lần mới / huy(): kết quả của lần cũ (the_he khác) bị bỏ. bao(self) sau mỗi lượt lấy."""
    NHIP_MS = 80
    SO_LUONG = 4

    def __init__(self, view: KhungBanDo, bao=None):
        self.view, self.bao = view, bao
        self.hang = queue.Queue()
        self.the_he = 0
        self.dung = threading.Event()
        self.nhip = QTimer(view)
        self.nhip.setInterval(self.NHIP_MS)
        self.nhip.timeout.connect(self._lay)
        self.tong = self.xong = self.loi = 0
        self.z, self.kt, self.thu_tu = 0, None, {}

    @property
    def dang(self) -> bool:
        return self.nhip.isActive()

    def bat_dau(self, z: int, ds: list, kt, thu_tu: dict | None = None) -> None:
        """ds = [(x, y)] (lớp ảnh vệ tinh 'esri') hoặc [(lớp, x, y)]; thu_tu {lớp: thứ tự xếp chồng} - lớp sau nằm trên."""
        self.huy()
        self.the_he += 1
        th, dung = self.the_he, threading.Event()
        self.dung = dung
        ds = [(nen_ban_do.NGUON, *o) if len(o) == 2 else tuple(o) for o in ds]
        self.thu_tu = thu_tu or {}
        self.tong, self.xong, self.loi, self.z, self.kt = len(ds), 0, 0, z, kt
        if not ds:
            return
        chia = [ds[i::self.SO_LUONG] for i in range(self.SO_LUONG)]

        def chay(phan):
            for lop, x, y in phan:
                if dung.is_set():
                    return
                try:
                    du = nen_ban_do.tai_o(z, x, y) if lop == nen_ban_do.NGUON else nen_ban_do.tai_o(z, x, y, lop=lop)
                except Exception:                          # noqa: BLE001 - một ô lỗi không dừng luồng (đếm là không tải được)
                    du = None
                self.hang.put((th, lop, x, y, du))
        for phan in chia:
            if phan:
                threading.Thread(target=chay, args=(phan,), daemon=True).start()
        self.nhip.start()

    def huy(self) -> None:
        self.dung.set()
        self.nhip.stop()
        while True:
            try:
                self.hang.get_nowait()
            except queue.Empty:
                break

    def _goc(self, x: int, y: int) -> tuple:
        def diem(vd, kd):
            d, b = toa_do.wgs84_sang_vn2000(vd, kd, self.kt)
            return QPointF(d, -b)
        z = self.z
        return diem(*nen_ban_do.goc_o(z, x, y)), diem(*nen_ban_do.goc_o(z, x + 1, y)), diem(*nen_ban_do.goc_o(z, x, y + 1))

    def _lay(self) -> None:
        while True:
            try:
                th, lop, x, y, du = self.hang.get_nowait()
            except queue.Empty:
                break
            if th != self.the_he:
                continue
            # lớp sau luôn trên lớp trước (20 bậc mỗi lớp), cùng lớp mức phóng sâu trên mức nông: ô cũ làm nền chờ ô mới
            z_ve = -100 + self.thu_tu.get(lop, 0) * 20 + self.z
            if du is not None and self.view.dat_o_nen(du, self._goc(x, y), (lop, self.z, x, y), z_ve):
                self.xong += 1
            else:
                self.loi += 1
        if self.xong + self.loi >= self.tong:
            self.nhip.stop()
        if self.bao is not None:
            self.bao(self)

    def cho_xong(self, giay: float = 10.0) -> bool:
        """Chờ tải xong (kiểm thử / chụp ảnh): xử lý sự kiện tới khi hết ô hoặc hết giờ."""
        import time
        het = time.time() + giay
        while self.dang and time.time() < het:
            QApplication.processEvents()
            time.sleep(0.02)
        return not self.dang


class HopBanDo(QDialog):
    """Cửa sổ bản đồ thửa đất (không chặn cửa sổ chính): lọc tờ, tìm thửa, tô màu theo đồng thuận / tiến độ theo hộ / lệch diện tích
    (ban_do_cad.CHE_DO_MAU), nền ảnh vệ tinh (nen_ban_do - mặc định tắt), chú giải đếm thửa, bấm thửa mở phương án hộ (mo_ho(mã hộ)),
    chuột phải thửa (menu_cho_thua), tọa độ con trỏ (VN-2000 + GPS), xuất bản đồ ra .kml / .kmz (Google Earth, điện thoại)."""
    im_lang = False
    KHOA_NEN = 'ban_do/nen_ve_tinh'
    KHOA_LOAI_NEN = 'ban_do/loai_nen'
    KHOA_DO_DAM = 'ban_do/do_dam'
    DO_DAM_MAC_DINH = 35                                 # % độ đậm tô thửa
    CHO_NAP_NEN_MS = 250                                 # kéo / phóng xong mới nạp ô nền của vùng mới
    O_GIU_TOI_DA = 400                                   # số ô nền giữ trong cảnh - quá thì bỏ ô ngoài vùng đang xem

    def __init__(self, con, parent=None, mo_ho=None, nhap=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.mo_ho, self.nhap, self.chi_doc = con, mo_ho, nhap, chi_doc
        self.xml_kml = {}                                # {tên lớp: XML KML} - để lưu vào dự án
        self.setWindowTitle('Bản đồ thửa đất')
        self.resize(1150, 760)
        self._gd = None                                  # {mã hộ: giai đoạn phễu} - tính khi cần (chế độ tiến độ)
        self.ds = []
        self.lop_kml = []                                # [(tên file, [PlacemarkKml])] - mở để xem, không ghi vào dự án
        self.cb_to = QComboBox()
        self.cb_to.currentIndexChanged.connect(lambda _: self.nap())
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tờ/thửa (5/12) → Enter')
        self.o_tim.setToolTip('Tìm thửa theo số (máy không có GPS): "12" = thửa 12 tờ đang xem, "5/12" hoặc "thửa 12 tờ 5" = tìm trên mọi '
                              'tờ, cả trong lớp KML / KMZ đang mở')
        self.o_tim.setMaximumWidth(170)
        self.o_tim.returnPressed.connect(lambda: self.tim_thua(self.o_tim.text()))
        b_vua = QPushButton('Vừa khung')
        b_vua.clicked.connect(lambda: self.view.vua())
        b_nhap = QPushButton('Nhập bản đồ (.dxf, .kml, .kmz)…')
        b_nhap.clicked.connect(lambda: self._nhap())
        self.b_xuat = QPushButton('Xuất KML / KMZ…')
        self.b_xuat.setToolTip('Ghi bản đồ thửa (tờ đang xem) ra file .kml / .kmz: mở bằng Google Earth hoặc điện thoại, màu theo đồng thuận')
        self.b_xuat.clicked.connect(lambda: self.xuat_kml())
        self.cb_mau = QComboBox()
        for k, ten in ban_do_cad.CHE_DO_MAU:
            self.cb_mau.addItem(ten, k)
        self.cb_mau.setToolTip('Đồng thuận: ý kiến ở đợt niêm yết gần nhất · Tiến độ theo hộ: 8 giai đoạn của phễu tiến độ (màn hình chính) '
                               '· Lệch diện tích: diện tích bản đồ so với hồ sơ (khớp / lệch 2-10% / trên 10%)')
        self.cb_mau.currentIndexChanged.connect(lambda _: self.nap(giu_khung=True))
        self.o_nen = QCheckBox('Nền bản đồ:')
        self.o_nen.setToolTip('Hiện ảnh vệ tinh / bản đồ nền dưới các thửa (như LARC Mobile) - cần mạng lần đầu, ô đã tải được lưu để xem '
                              'lại khi mất mạng.\nChỉ gửi tọa độ ô ảnh của vùng đang xem tới máy chủ bản đồ, KHÔNG gửi số liệu hộ.')
        self.cb_nen = QComboBox()
        for k, (ten, *_x) in nen_ban_do.NEN.items():
            self.cb_nen.addItem(ten, k)
        self.cb_nen.setToolTip('Loại nền: ảnh vệ tinh, ảnh vệ tinh kèm tên đường và địa danh, bản đồ đường phố (OpenStreetMap), địa hình')
        self.sl_dam = QSlider(Qt.Orientation.Horizontal)
        self.sl_dam.setRange(0, 100)
        self.sl_dam.setFixedWidth(110)
        self.sl_dam.setToolTip('Độ đậm màu tô thửa - kéo nhạt để thấy rõ ảnh nền')
        self.b_mo_kml = QPushButton('Mở KML / KMZ để xem…')
        self.b_mo_kml.setToolTip('Đặt bản đồ Google Earth (.kml / .kmz: thửa, đường, điểm mốc) lên bản đồ để XEM trên nền vệ tinh - không ghi '
                                 'vào dự án (muốn đưa ranh thửa vào dự án: "Nhập bản đồ…")')
        self.b_mo_kml.clicked.connect(lambda: self.mo_kml())
        self.b_bo_kml = QPushButton('Bỏ lớp KML')
        self.b_bo_kml.clicked.connect(lambda: self.bo_kml())
        self.b_luu = QPushButton('Lưu bản đồ vào dự án')
        self.b_luu.setToolTip('Ghi các lớp KML / KMZ đang mở và ảnh nền của vùng dự án (loại nền đang chọn) vào file dự án: lần sau mở bản '
                              'đồ là có sẵn, không phải mở / tải lại; gửi file dự án sang máy khác vẫn xem được khi mất mạng')
        self.b_luu.clicked.connect(lambda: self.luu_vao_du_an())
        self.b_bo_luu = QPushButton('Bỏ bản đồ đã lưu')
        self.b_bo_luu.setToolTip('Xóa ảnh nền và các lớp KML đã lưu trong file dự án - file dự án nhỏ lại (bản đồ dự án nhập từ .dxf / .kml '
                                 'không đổi)')
        self.b_bo_luu.clicked.connect(lambda: self.bo_ban_do_da_luu())
        # hàng công cụ: hẹp (1366 @125%) thì xuống dòng, không ép cửa sổ rộng hơn màn hình
        self.khung_cc = QWidget()
        h = XepDong(self.khung_cc, 16)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(_khoi((QLabel('Tờ bản đồ:'), self.cb_to, QLabel('Tìm thửa:'), self.o_tim, b_vua)))
        h.addWidget(_khoi((QLabel('Màu theo:'), self.cb_mau, QLabel('Độ đậm:'), self.sl_dam)))
        h.addWidget(_khoi((self.o_nen, self.cb_nen)))
        dem = QWidget()                                  # khoảng giãn: nút Xuất / Nhập về sát phải, các khối khác giữ đúng cỡ
        h.addWidget(dem)
        h.gian(dem)
        h.addWidget(_khoi((self.b_mo_kml, self.b_bo_kml, self.b_luu, self.b_bo_luu)))
        h.addWidget(_khoi((self.b_xuat, b_nhap)))
        self.khung_cg = QWidget()                        # chú giải - dựng lại theo cách tô màu (_ve_chu_giai)
        self.cg = XepDong(self.khung_cg, 12)
        self.cg.setContentsMargins(0, 0, 0, 0)
        self.lb_dem = {}
        self.lb_tong = QLabel('')                       # 1.0.33: tổng số thửa + tỷ lệ đồng thuận (thửa đã gắn hộ)
        self.lb_tong.setProperty('vai', 'nhan')
        self.cg.gian(self.lb_tong)                       # dòng tổng nhận phần rộng thừa: các ô chú giải đứng sát nhau
        self.view = KhungBanDo(self)
        self.view.bam_ho.connect(self._bam_ho)
        self.view.bam_cad.connect(self._hien_doi_tuong)
        self.view.menu_thua.connect(lambda t, p: self.menu_cho_thua(t, p))
        self.khung_lop = QWidget()
        hlop = QHBoxLayout(self.khung_lop)
        hlop.setContentsMargins(0, 0, 0, 0)
        hlop.setSpacing(10)
        hlop.addWidget(QLabel('Lớp CAD:'))
        self.o_lop = {}
        for k, ten in LOP_BD:
            o = QCheckBox(chu_hien(ten))             # 1.0.51: "&" không bị Qt lấy làm phím tắt
            o.setChecked(True)
            o.setToolTip('Bật / tắt lớp như trên LARC Mobile: lưới thửa & ranh Level, số thửa / loại đất / DT, mốc ranh, ghi chú.')
            o.toggled.connect(lambda _=False: self._doi_lop_cad())
            self.o_lop[k] = o
            hlop.addWidget(o)
        hlop.addStretch(1)
        self.khung_lop.setVisible(False)
        self.khung_tc = QWidget()
        vtc = QVBoxLayout(self.khung_tc)
        vtc.setContentsMargins(0, 4, 0, 0)
        vtc.setSpacing(4)
        hang_tc = QHBoxLayout()
        hang_tc.addWidget(QLabel('Tra cứu:'))
        self.cb_the_kml = QComboBox()
        for k, ten in THE_KML:
            self.cb_the_kml.addItem(ten, k)
        self.cb_the_kml.currentIndexChanged.connect(lambda _: self.ve_bang_kml())
        hang_tc.addWidget(self.cb_the_kml)
        self.o_tim_kml = QLineEdit()
        self.o_tim_kml.setPlaceholderText('Lọc thửa, mốc, ghi chú, đường…')
        self.o_tim_kml.textChanged.connect(lambda _: self.ve_bang_kml())
        hang_tc.addWidget(self.o_tim_kml, 1)
        self.b_xem_kml = QPushButton('Xem')
        self.b_xem_kml.setToolTip('Bay tới đối tượng đang chọn trên bảng tra cứu')
        self.b_xem_kml.clicked.connect(lambda: self.xem_dong_kml())
        hang_tc.addWidget(self.b_xem_kml)
        vtc.addLayout(hang_tc)
        self.bang_kml = QTableWidget(0, 3)
        self.bang_kml.setHorizontalHeaderLabels(['Loại', 'Tên', 'Chi tiết'])
        self.bang_kml.verticalHeader().setVisible(False)
        self.bang_kml.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang_kml.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang_kml.setMaximumHeight(160)
        self.bang_kml.horizontalHeader().setStretchLastSection(True)
        self.bang_kml.cellDoubleClicked.connect(lambda *_: self.xem_dong_kml())
        vtc.addWidget(self.bang_kml)
        self.khung_tc.setVisible(False)
        self.kt = toa_do.kinh_tuyen_truc()
        self.nen = NapNen(self.view, self._bao_nen)
        self.hen_nen = QTimer(self)
        self.hen_nen.setSingleShot(True)
        self.hen_nen.setInterval(self.CHO_NAP_NEN_MS)
        self.hen_nen.timeout.connect(lambda: self.nap_nen(tu_dong=True))
        self.view.khung_doi.connect(self._khung_doi)
        self.lb_toa_do = QLabel('')
        self.view.toa_do_chuot.connect(self._hien_toa_do)
        self.lb = QLabel('Lăn chuột hoặc nút +/− để phóng, kéo để di chuyển, bấm thửa mở phương án hộ, bấm đường / nhãn / mốc để xem thuộc tính.')
        self.lb_nguon = QLabel(nen_ban_do.GHI_NGUON)
        self.lb_nguon.setProperty('vai', 'nhan')
        lo = QVBoxLayout(self)
        lo.addWidget(self.khung_cc)          # nút ẩn / hiện SAU khi bố cục đã gắn vào hộp (1.0.16: nút chưa có cha thành cửa sổ rỗng)
        lo.addWidget(self.khung_cg)
        lo.addWidget(self.khung_lop)
        lo.addWidget(self.view, 1)
        lo.addWidget(self.khung_tc)
        hd = QHBoxLayout()
        hd.addWidget(self.lb, 1)
        hd.addWidget(self.lb_nguon)
        hd.addWidget(self.lb_toa_do)
        lo.addLayout(hd)
        self.lb_nguon.setVisible(False)
        self.b_bo_kml.setEnabled(False)
        b_nhap.setVisible(nhap is not None and con is not None)
        self.b_luu.setVisible(con is not None)
        self.b_luu.setEnabled(not chi_doc)
        self._nap_lop_da_luu()
        self._cap_nhat_nut_luu()
        from .giao_dien import cai_dat_nho
        cd = cai_dat_nho()
        self.o_nen.setChecked(cd is not None and str(cd.value(self.KHOA_NEN, 'false')).lower() == 'true')
        loai = str(cd.value(self.KHOA_LOAI_NEN, nen_ban_do.NEN_MAC_DINH)) if cd is not None else nen_ban_do.NEN_MAC_DINH
        self.cb_nen.setCurrentIndex(max(0, self.cb_nen.findData(loai)))
        try:
            dam = int(cd.value(self.KHOA_DO_DAM, self.DO_DAM_MAC_DINH)) if cd is not None else self.DO_DAM_MAC_DINH
        except (TypeError, ValueError):
            dam = self.DO_DAM_MAC_DINH
        self.sl_dam.setValue(dam)
        self.view.do_dam = round(dam * 255 / 100)
        self.o_nen.toggled.connect(self._doi_nen)
        self.cb_nen.currentIndexChanged.connect(lambda _: self._doi_loai_nen())
        self.sl_dam.valueChanged.connect(self._doi_do_dam)
        self.nap_to()

    def nap_to(self) -> None:
        self.cb_to.blockSignals(True)
        self.cb_to.clear()
        for t in (ban_do_cad.ds_to(self.con) if self.con is not None else []):
            self.cb_to.addItem(f'Tờ {t}', t)
        if self.cb_to.count() > 1:
            self.cb_to.addItem('Tất cả các tờ', None)
        self.cb_to.blockSignals(False)
        self.nap()

    # ---- cách tô màu
    def che_do_mau(self) -> str:
        return self.cb_mau.currentData() or 'dong_thuan'

    def _giai_doan(self) -> dict:
        if self._gd is None:
            from . import pheu_tien_do
            try:
                self._gd = {x.ma_ho: x.giai_doan for x in pheu_tien_do.tinh(self.con).ho}
            except Exception:                           # noqa: BLE001 - phễu lỗi (file cũ thiếu bảng): không tô theo tiến độ
                self._gd = {}
        return self._gd

    def bang_mau(self) -> list:
        """[(khóa, tên, màu)] của cách tô đang chọn (thứ tự chú giải)."""
        m = self.che_do_mau()
        khong = ('khong_gan', *ban_do_cad.TRANG_THAI['khong_gan'])
        if m == 'tien_do':
            from . import pheu_tien_do
            from .man_hinh_tong_quan import MAU_GIAI_DOAN
            return [(k, pheu_tien_do.TEN_NGAN_GIAI_DOAN[k], MAU_GIAI_DOAN[k]) for k, _ in pheu_tien_do.GIAI_DOAN_HO] + [khong]
        if m == 'lech_dt':
            return [(k, ten, mau) for k, (ten, mau) in ban_do_cad.LECH_DT.items()]
        return [(k, ten, mau) for k, (ten, mau) in ban_do_cad.TRANG_THAI.items()]

    def mau_cua(self, t) -> tuple:
        """(khóa, tên, màu) của thửa theo cách tô đang chọn."""
        m = self.che_do_mau()
        bang = {k: (ten, mau) for k, ten, mau in self.bang_mau()}
        if m == 'tien_do':
            k = self._giai_doan().get(t.ma_ho) if t.ma_ho is not None else None
            k = k if k in bang else 'khong_gan'
        elif m == 'lech_dt':
            k = ban_do_cad.lech_dien_tich(t)[0]
        else:
            k = t.trang_thai
        return (k, *bang[k])

    def _ve_chu_giai(self, dem: dict) -> None:
        while self.cg.count():
            it = self.cg.takeAt(0)
            w = it.widget()
            if w is not None and w is not self.lb_tong:
                w.hide()
                w.deleteLater()
        self.lb_dem = {}
        for k, ten, mau in self.bang_mau():
            o = QLabel()
            o.setFixedSize(14, 14)
            o.setStyleSheet(f'QLabel {{ background: {mau}; border-radius: 3px; }}')
            ngan = ten.split(' (')[0] if k == 'khong_gan' else ten          # "Chưa gắn hộ (không có trong hồ sơ)": đủ ở chú thích
            lb = QLabel(f'{ngan}: {dem.get(k, 0)}')
            lb.setToolTip(ten)
            self.lb_dem[k] = lb
            self.cg.addWidget(_khoi((o, lb)))
        self.cg.addWidget(self.lb_tong)

    def nap(self, giu_khung: bool = False) -> None:
        if self.con is not None:
            self._con_song()                            # dự án đã đóng trong lúc cửa sổ còn mở: con -> None
        if not giu_khung:
            self.ds = ban_do_cad.doc_ban_do(self.con, self.cb_to.currentData()) if self.cb_to.count() and self.con is not None else []
            self._gd = None
        ds = self.ds
        self.nen.huy()
        co_nen = self.o_nen.isChecked()
        self.view.ve(ds, self.mau_cua, co_nen, giu_khung)
        if self.lop_kml:
            cm = {}
            if self.con is not None:
                cm = ban_do_cad.chi_muc_thua(self.con)
                self.view.ho_ten = {r[0]: r[1] for r in self.con.execute('SELECT ma_ho, ho_ten FROM ho')}
            self.view.ve_kml(self.lop_kml, self.kt, cm, co_nen)
            if not giu_khung:
                self.view.vua()
        self._hien_cong_cu_cad()
        dem = {}
        for it in self.view.thua:
            dem[it.khoa_mau] = dem.get(it.khoa_mau, 0) + 1
        self._ve_chu_giai(dem)
        gan = len(ds) - dem.get('khong_gan', 0)
        m = self.che_do_mau()
        if m == 'tien_do':
            them = f' · đã bàn giao {dem.get("hoan_tat", 0) * 100 / gan:.1f}%' if gan else ''
        elif m == 'lech_dt':
            them = f' · lệch trên 10%: {dem.get("lech_nhieu", 0)} thửa'
        else:
            them = f' · đồng thuận {dem.get("dong_y", 0) * 100 / gan:.1f}%' if gan else ''
        self.lb_tong.setText(f'Tổng {len(ds)} thửa' + them.replace('.', ','))
        self.b_xuat.setEnabled(bool(ds))
        self.khung_cg.setVisible(bool(ds))              # chú giải màu đồng thuận / tiến độ chỉ có nghĩa với thửa của dự án
        if not ds and not self.lop_kml:
            self.lb.setText(('Dự án chưa có bản đồ: bấm "Nhập bản đồ (.dxf, .kml, .kmz)…" (hoặc menu Dữ liệu) để nhập ranh thửa từ bản vẽ '
                             'địa chính hoặc file Google Earth, hoặc "Mở KML / KMZ để xem…" để xem trên nền vệ tinh.')
                            if self.con is not None else 'Bấm "Mở KML / KMZ để xem…" để xem bản đồ Google Earth trên nền vệ tinh.')
        elif co_nen:
            self.nap_nen()

    # ---- nền bản đồ (ảnh vệ tinh, đường phố, địa hình) - tải theo VÙNG ĐANG XEM như LARC Mobile
    def loai_nen(self) -> str:
        return self.cb_nen.currentData() or nen_ban_do.NEN_MAC_DINH

    @staticmethod
    def _wgs84_cua(r: QRectF, kt: float) -> tuple | None:
        try:
            ds = [toa_do.vn2000_sang_wgs84(x, -y, kt) for x, y in
                  ((r.left(), r.top()), (r.right(), r.top()), (r.left(), r.bottom()), (r.right(), r.bottom()))]
        except (ValueError, ZeroDivisionError, OverflowError):
            return None
        return min(v for v, _ in ds), max(v for v, _ in ds), min(k for _, k in ds), max(k for _, k in ds)

    def khung_wgs84(self) -> tuple | None:
        """(vĩ độ min, max, kinh độ min, max) của khung thửa / lớp KML đang vẽ; None: không có / tọa độ không đổi được."""
        r = self.view.khung_thua()
        return None if r.isEmpty() else self._wgs84_cua(r, self.kt)

    def _khung_doi(self) -> None:
        try:
            self.view.cap_nhat_hien_kml()
            if self.isVisible() and self.o_nen.isChecked() and (self.view.thua or self.view.kml):
                self.hen_nen.start()
        except RuntimeError:                            # đang hủy cửa sổ
            pass

    def nap_nen(self, tu_dong: bool = False) -> bool:
        """Tải ô nền của vùng đang xem ở mức phóng hợp với màn hình (như LARC Mobile: phóng sâu thì ảnh nét hơn). False: không đặt
        được nền (tọa độ không phải VN-2000 của tỉnh). tu_dong: gọi sau khi kéo / phóng - không báo lỗi lặp lại."""
        k_du_an = self.khung_wgs84()
        if k_du_an is None or not nen_ban_do.trong_vn(k_du_an):
            if not tu_dong:
                self.lb.setText(f'Không đặt được nền bản đồ: tọa độ bản vẽ không phải VN-2000 theo kinh tuyến trục '
                                f'{toa_do.chu_kinh_tuyen(self.kt)} (bản vẽ hệ tọa độ giả định / kinh tuyến khác).')
            return False
        ten, lop, z_max, nguon = nen_ban_do.NEN[self.loai_nen()]
        xem = self._wgs84_cua(self.view.khung_dang_xem(), self.kt) if self.view.isVisible() else None
        if xem is None or not nen_ban_do.trong_vn(xem):  # khung chưa hiện / thu nhỏ quá Việt Nam: theo khung dự án như trước
            z, ds_xy = nen_ban_do.ds_o(k_du_an, z_toi_da=z_max)
        else:
            z = nen_ban_do.z_cho_khung(self.view.m_moi_diem(), (xem[0] + xem[1]) / 2, z_max)
            z, ds_xy = nen_ban_do.o_cua_khung(xem, z)
        # nhãn đường / địa danh của mức khác không trùng khớp chữ của mức mới: bỏ ngay (ảnh nền mức cũ giữ làm nền chờ ô mới)
        self.view.bo_o([k for k in self.view.o_khoa if k[0] != lop[0] and k[1] != z])
        if len(self.view.o_khoa) > self.O_GIU_TOI_DA:
            self.view.bo_o([k for k in self.view.o_khoa if k[1] != z])
        co = self._dat_o_da_luu(z, lop, ds_xy)              # ô đã lưu trong file dự án: đặt ngay, không tải
        ds = [(lp, x, y) for lp in lop for x, y in ds_xy if (lp, z, x, y) not in self.view.o_khoa and (lp, x, y) not in co]
        self.lb_nguon.setText(nguon)
        self.lb_nguon.setVisible(True)
        self.nen.bat_dau(z, ds, self.kt, {lp: i for i, lp in enumerate(lop)})
        if not ds:
            self.lb.setText(f'Ảnh nền: đủ ô cho vùng đang xem' + (f' ({len(co)} ô lấy từ bản đồ đã lưu trong dự án).' if co else '.') +
                            ' Lăn chuột để phóng, kéo để di chuyển.')
        return True

    def _bao_nen(self, n: NapNen) -> None:
        if n.dang:
            self.lb.setText(f'Đang tải ảnh nền {n.xong + n.loi}/{n.tong} ô…')
        else:
            self.lb.setText(f'Ảnh nền: {n.xong}/{n.tong} ô' + (f' - {n.loi} ô không tải được (mất mạng?).' if n.loi else '.') +
                            ' Lăn chuột để phóng (ảnh nét dần), kéo để di chuyển, bấm vào thửa để mở phương án hộ.')

    def _luu(self, khoa: str, gt) -> None:
        from .giao_dien import cai_dat_nho
        cd = cai_dat_nho()
        if cd is not None:
            cd.setValue(khoa, gt)

    def _doi_nen(self, bat: bool) -> None:
        self._luu(self.KHOA_NEN, 'true' if bat else 'false')
        self.lb_nguon.setVisible(bat)
        self.nap(giu_khung=True)
        if not bat:
            self.lb.setText('Đã tắt nền bản đồ.')

    def _doi_loai_nen(self) -> None:
        self._luu(self.KHOA_LOAI_NEN, self.loai_nen())
        if self.o_nen.isChecked():
            self.nen.huy()
            self.view.bo_het_nen()
            self.nap_nen()
        else:
            self.o_nen.setChecked(True)                    # chọn loại nền = muốn xem nền

    def _doi_do_dam(self, pt: int) -> None:
        self.view.dat_do_dam(round(pt * 255 / 100))
        self._luu(self.KHOA_DO_DAM, int(pt))

    # ---- lớp KML / KMZ chỉ xem (không ghi vào dự án)
    def mo_kml(self, files=None) -> int:
        """Mở một hoặc nhiều file .kml / .kmz lên bản đồ để xem. Trả số đối tượng vẽ được."""
        if files is None:
            if self.im_lang:
                return 0
            files, _ = QFileDialog.getOpenFileNames(self, 'Mở bản đồ Google Earth để xem', '', 'Google Earth (*.kml *.kmz)')
            if not files:
                return 0
        loi, them = [], []
        with con_tro_cho():
            for f in ([files] if isinstance(files, (str, Path)) else files):
                try:
                    xml = ban_do_kml.doc_byte_kml(f)
                    ds = ban_do_kml.doc_kml_xml(xml, Path(f).name)
                except ban_do_cad.LoiCad as e:
                    loi.append(str(e))
                    continue
                if ds:
                    them.append((Path(f).name, ds))
                    self.xml_kml[Path(f).name] = xml
                else:
                    loi.append(f'{Path(f).name}: không có thửa, đường hay điểm nào.')
            ten_co = {t for t, _ in them}
            self.lop_kml = [x for x in self.lop_kml if x[0] not in ten_co] + them
            self.nap(giu_khung=False)
        n = len(self.view.kml)
        self.b_bo_kml.setEnabled(bool(self.lop_kml))
        so_dt = sum(len(pm.da_giac) + len(pm.duong) + len(pm.diem) for _, ds in them for pm in ds)
        tat = []
        for _ten, ds in them:
            t = ban_do_kml.tom_tat_cad(ds)
            if t:
                tat.append(t)
        chu = (f'Đã mở {len(them)} lớp KML ({"; ".join(tat) if tat else str(so_dt) + " đối tượng"}) - chỉ xem, chưa ghi vào dự án. '
               'Bật/tắt lớp CAD, nút +/−/Vừa trên bản đồ; bấm đường, số thửa, mốc hay ghi chú để xem thuộc tính.'
               if them else '')
        if loi:
            chu = (chu + ' ' if chu else '') + 'Không mở được: ' + '; '.join(loi)
            if not self.im_lang and not them:
                from .giao_dien import hop_ket_qua
                hop_ket_qua(self, 'Không mở được lớp KML.', loi, tieu_de_ds='File lỗi', canh_bao=True, tieu_de=TEN_UD)
        if chu:
            self.lb.setText(chu)
        return n

    def _doi_lop_cad(self) -> None:
        self.view.dat_lop_hien({k for k, o in self.o_lop.items() if o.isChecked()})

    def _hien_cong_cu_cad(self) -> None:
        co = bool(self.lop_kml)
        self.khung_lop.setVisible(co)
        self.khung_tc.setVisible(co)
        if co:
            self.ve_bang_kml()

    def _hien_doi_tuong(self, o: dict) -> None:
        """Bấm đường / nhãn / mốc trên bản đồ: hiện thuộc tính (kèm VN-2000), viền nổi nếu có hình."""
        if not o:
            return
        kieu = o.get('kieu') or ''
        if kieu == 'nhan_thua':
            th, to = o.get('so_thua') or '', o.get('so_to') or ''
            dong = [f'Thửa {th}' + (f' tờ {to}' if to else ''),
                    f'Loại đất: {o.get("chu_ld") or "(chưa có nhãn)"}',
                    f'DT nguyên thửa: {o.get("chu_dt") + " m²" if o.get("chu_dt") else "(chưa có)"}']
            if o.get('chu_dt_th'):
                dong.append(f'DT thu hồi: {o.get("chu_dt_th")} m²')
            if o.get('lop_cad'):
                dong.append('Lớp CAD: ' + ' · '.join(x for x in (o.get('lop_cad'), o.get('ban_ve') and ('bản vẽ ' + o['ban_ve'])) if x))
            self.lb.setText(' · '.join(dong))
            if th:
                self.tim_thua((f'{to}/{th}' if to else th))
            return
        if kieu == 'duong':
            pts = o.get('pts') or []
            dai = 0.0
            for i in range(len(pts) - 1):
                dai += math.hypot(pts[i + 1].x() - pts[i].x(), pts[i + 1].y() - pts[i].y())
            cad = ' · '.join(x for x in (o.get('lop_cad'), o.get('ban_ve') and ('bản vẽ ' + o['ban_ve'])) if x)
            self.lb.setText(f'Đường {"ranh" if "ranh" in (o.get("ten") or "").lower() else "lưới thửa / ranh giới"}'
                            + (f' · {cad}' if cad else '') + f' · {o.get("so_dinh") or len(pts)} đỉnh · dài {vn(dai, 1)} m'
                            + (f' · {o.get("ten")}' if o.get('ten') else ''))
            it = next((r['it'] for r in self.view.kml_cad if r['tt'] is o), None)
            if it is not None:
                self.view.danh_dau([it], phong=False)
            return
        ten_loai = {'moc': 'Mốc ranh', 'ghi_chu': 'Ghi chú', 'ld': 'Loại đất', 'dt': 'Diện tích',
                    'dt_th': 'Diện tích thu hồi', 'to': 'Số tờ', 'thua': 'Số thửa', 'vong_moc': 'Vòng mốc'}.get(o.get('loai') or kieu, 'Nhãn')
        cad = ' · '.join(x for x in (o.get('lop_cad'), o.get('ban_ve') and ('bản vẽ ' + o['ban_ve'])) if x)
        td = ''
        if o.get('lat') is not None and o.get('lon') is not None:
            try:
                d, b = toa_do.wgs84_sang_vn2000(o['lat'], o['lon'], self.kt)
                td = f' · VN-2000 X {b:,.2f} Y {d:,.2f}'.replace(',', ' ')
            except (ValueError, ZeroDivisionError, OverflowError):
                td = ''
        self.lb.setText(f'{ten_loai}: {o.get("chu") or ""}' + (f' · {cad}' if cad else '') + td)
        it = next((r['it'] for r in self.view.kml_cad if r['tt'] is o), None)
        if it is not None:
            self.view.danh_dau([it], phong=False)

    def ve_bang_kml(self) -> None:
        """Bảng tra cứu đối tượng CAD đã nạp (thửa, mốc, ghi chú, đường)."""
        from .lap_pa import bo_dau
        the = self.cb_the_kml.currentData() or 'tat_ca'
        q = bo_dau(self.o_tim_kml.text().strip())
        ds = []
        if the in ('tat_ca', 'thua'):
            for c in self.view.nhan_thua_cad:
                ds.append((c, 'Thửa', f'Thửa {c.get("so_thua") or ""}' + (f' · tờ {c["so_to"]}' if c.get('so_to') else ''),
                           ' · '.join(x for x in (c.get('chu_ld'), c.get('chu_dt') and (c['chu_dt'] + ' m²'),
                                                 c.get('chu_dt_th') and ('thu hồi ' + c['chu_dt_th'] + ' m²')) if x)))
        if the in ('tat_ca', 'moc'):
            for rec in self.view.kml_cad:
                tt = rec['tt']
                if tt.get('loai') == 'moc' or tt.get('kieu') == 'vong_moc':
                    ds.append((tt, 'Mốc', 'Mốc ' + (tt.get('chu') or ''), tt.get('lop_cad') or ''))
        if the in ('tat_ca', 'ghi_chu'):
            for rec in self.view.kml_cad:
                tt = rec['tt']
                if tt.get('loai') == 'ghi_chu':
                    ds.append((tt, 'Ghi chú', tt.get('chu') or '', tt.get('lop_cad') or ''))
        if the == 'duong':
            for rec in self.view.kml_cad:
                tt = rec['tt']
                if tt.get('kieu') == 'duong':
                    ds.append((tt, 'Đường', 'Đường ' + (tt.get('lop_cad') or ''),
                               f'{tt.get("so_dinh") or 0} đỉnh · {tt.get("mau") or ""}'))
        if q:
            ds = [x for x in ds if q in bo_dau(' '.join(x[1:]))]
        self.bang_kml.setRowCount(len(ds))
        self._ds_bang_kml = ds
        for r, (_o, loai, ten, ct) in enumerate(ds):
            for c, v in enumerate((loai, ten, ct)):
                self.bang_kml.setItem(r, c, QTableWidgetItem(v))
        self.bang_kml.resizeColumnsToContents()

    def xem_dong_kml(self) -> int:
        """Bay tới dòng đang chọn trên bảng tra cứu. Trả 1 nếu có."""
        r = self.bang_kml.currentRow()
        ds = getattr(self, '_ds_bang_kml', [])
        if r < 0 or r >= len(ds):
            return 0
        o = ds[r][0]
        if o.get('kieu') == 'nhan_thua' and o.get('so_thua'):
            return 1 if self.tim_thua((f'{o["so_to"]}/{o["so_thua"]}' if o.get('so_to') else o['so_thua'])) else 0
        it = next((rec['it'] for rec in self.view.kml_cad if rec['tt'] is o), None)
        if it is None:
            self._hien_doi_tuong(o)
            return 0
        self.view.danh_dau([it])
        self._hien_doi_tuong(o)
        return 1

    # ---- tìm thửa theo số / xem thửa của một hộ (máy tính bàn không có GPS)
    @staticmethod
    def doc_chu_tim(chu: str) -> tuple:
        """'5/12', 'thửa 12 tờ 5', 'tờ 5 thửa 12' -> ('5', '12'); '12' -> ('', '12'); không đọc được -> ('', '')."""
        s = ' '.join(str(chu or '').split())
        for mau, thu_tu in ((ban_do_kml._RE_THUA_TO, (2, 1)), (ban_do_kml._RE_TO_THUA, (1, 2))):
            m = mau.search(s)
            if m:
                return m.group(thu_tu[0]), m.group(thu_tu[1])
        m = re.fullmatch(r'(\S+?)\s*[/-]\s*(\d{1,5})', s)
        if m:
            return m.group(1), m.group(2)
        m = re.fullmatch(r'(?:thửa\s*(?:số)?\s*)?(\d{1,5})', s, re.I)
        return ('', m.group(1)) if m else ('', '')

    def _chon_to(self, to) -> None:
        """Chuyển ô Tờ bản đồ sang tờ to (None = tất cả các tờ) nếu có và chưa chọn."""
        i = self.cb_to.findData(to)
        if i >= 0 and i != self.cb_to.currentIndex():
            self.cb_to.setCurrentIndex(i)                 # nap() qua tín hiệu

    def tim_thua(self, chu: str) -> int:
        """Tìm thửa theo số tờ / thửa trên bản đồ dự án và các lớp KML đang mở; tìm được thì viền nổi + phóng tới. Trả số đối tượng."""
        to, thua = self.doc_chu_tim(chu)
        if not thua:
            self.lb.setText('Gõ số thửa ("12"), hoặc tờ/thửa ("5/12", "thửa 12 tờ 5").')
            return 0
        k_to, k_thua = ban_do_cad._khoa(to), ban_do_cad._khoa(thua)
        if to:
            ds_to_co = {ban_do_cad._khoa(self.cb_to.itemData(i)): self.cb_to.itemData(i) for i in range(self.cb_to.count())
                        if self.cb_to.itemData(i) is not None}
            if self.cb_to.currentData() is not None and ban_do_cad._khoa(self.cb_to.currentData()) != k_to and k_to in ds_to_co:
                self._chon_to(ds_to_co[k_to])

        def khop(t_to, t_thua):
            return ban_do_cad._khoa(t_thua) == k_thua and (not to or ban_do_cad._khoa(t_to) == k_to)
        ds = [it for it in self.view.thua if khop(it.t.so_to, it.t.so_thua)]
        ds += [it for (kt_, kh), it, _m in self.view.kml_thua if kh == k_thua and (not to or kt_ == k_to)]
        if not ds:
            self.view.danh_dau([])
            self.lb.setText(f'Không thấy thửa {thua}' + (f' tờ {to}' if to else ' trên tờ đang xem') +
                            ' trên bản đồ dự án và các lớp KML đang mở.')
            return 0
        n = self.view.danh_dau(ds)
        self.lb.setText(f'Thửa {thua}' + (f' tờ {to}' if to else '') + (f': {n} vị trí (viền xanh).' if n > 1 else ': viền xanh trên bản đồ.'))
        return n

    def xem_ho(self, ma_ho: int) -> int:
        """Viền nổi + phóng tới mọi thửa thu hồi của hộ (thửa đã nhập bản đồ, hoặc vùng KML đang mở khớp số tờ / thửa của hộ)."""
        if not self._con_song():
            return 0
        r = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
        ten = r[0] if r else str(ma_ho)
        khoa = {(ban_do_cad._khoa(a), ban_do_cad._khoa(b)) for a, b in
                self.con.execute('SELECT so_to, so_thua FROM thua WHERE ma_ho = ?', (ma_ho,))}
        if self.cb_to.findData(None) >= 0:               # nhiều tờ: thửa của hộ có thể ở tờ khác tờ đang xem
            self._chon_to(None)
        ds = [it for it in self.view.thua if it.t.ma_ho == ma_ho or (ban_do_cad._khoa(it.t.so_to), ban_do_cad._khoa(it.t.so_thua)) in khoa]
        ds += [it for k, it, m in self.view.kml_thua if m == ma_ho or k in khoa]
        if not ds:
            self.view.danh_dau([])
            thua = ', '.join(f'{a}/{b}' for a, b in sorted(khoa)) if khoa else 'chưa có'
            self.lb.setText(f'Hộ {ten}: chưa thấy thửa trên bản đồ (tờ/thửa: {thua}). Nhập bản đồ (.dxf, .kml, .kmz) vào dự án hoặc '
                            '"Mở KML / KMZ để xem…" file có số tờ, số thửa.')
            return 0
        n = self.view.danh_dau(ds)
        self.lb.setText(f'Hộ {ten}: {n} thửa thu hồi - viền xanh trên bản đồ.' + ('' if self.o_nen.isChecked() else
                        ' Bật "Nền bản đồ" để xem vị trí trên ảnh vệ tinh.'))
        return n

    def bo_kml(self) -> None:
        """Bỏ các lớp KML khỏi bản đồ (cả bản đã lưu trong dự án, nếu có)."""
        from . import ban_do_luu
        da_luu = bool(self._con_song() and ban_do_luu.ds_lop(self.con))
        if da_luu and not self.chi_doc:
            if not self.im_lang and QMessageBox.question(
                    self, TEN_UD, 'Các lớp KML đã lưu trong file dự án. Bỏ khỏi bản đồ và xóa bản đã lưu?') != \
                    QMessageBox.StandardButton.Yes:
                return
            ban_do_luu.xoa_lop(self.con)
        self.lop_kml, self.xml_kml = [], {}
        self.view.xoa_kml()
        self.b_bo_kml.setEnabled(False)
        self._hien_cong_cu_cad()
        self.nap(giu_khung=bool(self.ds))

    # ---- lưu bản đồ trong file dự án (mở lại có sẵn, không tải lại)
    def _con_song(self) -> bool:
        """Kết nối dự án còn mở (cửa sổ bản đồ không chặn: người dùng có thể đóng / đổi dự án trong lúc cửa sổ còn mở)."""
        if self.con is None:
            return False
        try:
            self.con.execute('SELECT 1')
            return True
        except Exception:                               # noqa: BLE001 - sqlite3.ProgrammingError: đã đóng
            self.con = None
            self.b_luu.setEnabled(False)
            self.b_bo_luu.setEnabled(False)
            self.lb.setText('Dự án đã đóng: mở lại "Bản đồ thửa đất" sau khi mở dự án để lưu / bỏ bản đồ đã lưu.')
            return False

    def _cap_nhat_nut_luu(self) -> None:
        from . import ban_do_luu
        if self.con is not None and not self._con_song():
            return
        tt = ban_do_luu.tom_tat(self.con)
        self.b_bo_luu.setVisible(self.con is not None and bool(tt['lop'] or tt['o']))
        self.b_bo_luu.setEnabled(not self.chi_doc)
        if tt['lop'] or tt['o']:
            self.b_bo_luu.setToolTip(f'Đang lưu trong file dự án: {tt["lop"]} lớp KML, {tt["o"]} ô ảnh nền ({tt["kich"] / 2 ** 20:.1f} MB). '
                                     'Bấm để xóa - file dự án nhỏ lại.')

    def bo_ban_do_da_luu(self) -> dict | None:
        """Xóa lớp KML + ô ảnh nền đã lưu trong file dự án (VACUUM - file nhỏ lại). Lớp đang hiện vẫn xem tiếp tới khi đóng."""
        from . import ban_do_luu
        if not self._con_song() or self.chi_doc:
            return None
        tt = ban_do_luu.tom_tat(self.con)
        if not self.im_lang and QMessageBox.question(
                self, TEN_UD, f'Xóa bản đồ đã lưu trong file dự án ({tt["lop"]} lớp KML, {tt["o"]} ô ảnh nền, '
                f'{tt["kich"] / 2 ** 20:.1f} MB)?') != QMessageBox.StandardButton.Yes:
            return None
        kq = {'lop': ban_do_luu.xoa_lop(self.con), 'o': ban_do_luu.xoa_o(self.con)}
        self.lb.setText(f'Đã xóa bản đồ đã lưu: {kq["lop"]} lớp KML, {kq["o"]} ô ảnh nền - file dự án đã thu gọn.')
        self._cap_nhat_nut_luu()
        return kq

    def _nap_lop_da_luu(self) -> None:
        if self.con is None:
            return
        from . import ban_do_luu
        for ten, xml in ban_do_luu.ds_lop(self.con):
            try:
                ds = ban_do_kml.doc_kml_xml(xml, ten)
            except ban_do_cad.LoiCad:
                continue
            if ds:
                self.lop_kml.append((ten, ds))
                self.xml_kml[ten] = xml
        self.b_bo_kml.setEnabled(bool(self.lop_kml))

    def _dat_o_da_luu(self, z: int, lop: tuple, ds_xy: list) -> set:
        """Đặt ngay các ô ảnh nền đã lưu trong dự án; trả {(lớp, x, y)} đã đặt (khỏi tải)."""
        from . import ban_do_luu
        co = set()
        if not self._con_song():
            return co
        self.nen.z, self.nen.kt = z, self.kt
        for i, lp in enumerate(lop):
            for (x, y), anh in ban_do_luu.doc_o(self.con, lp, z, [(x, y) for x, y in ds_xy if (lp, z, x, y) not in self.view.o_khoa]).items():
                if self.view.dat_o_nen(anh, self.nen._goc(x, y), (lp, z, x, y), -100 + i * 20 + z):
                    co.add((lp, x, y))
        return co

    def luu_vao_du_an(self, tai=None) -> dict | None:
        """Ghi lớp KML đang mở + ảnh nền vùng dự án (loại nền đang chọn) vào file dự án. tai(z, x, y, lớp) -> bytes (kiểm thử; mặc
        định nen_ban_do.tai_o: đệm máy trước, không có mới tải mạng). Trả {'lop', 'o', 'loi'} hoặc None."""
        from . import ban_do_luu
        if not self._con_song() or self.chi_doc:
            return None
        kq = {'lop': 0, 'o': 0, 'loi': 0}
        try:
            kq['lop'] = ban_do_luu.luu_lop(self.con, list(self.xml_kml.items()))
        except Exception as e:                          # noqa: BLE001 - file chỉ đọc / khóa
            self.lb.setText(chu_loi('Không lưu được bản đồ vào dự án', e))
            return None
        k = self.khung_wgs84()
        if k is not None and nen_ban_do.trong_vn(k):
            _ten, lop, z_max, _ng = nen_ban_do.NEN[self.loai_nen()]
            if lop == ('osm',):                          # OpenStreetMap cấm tải hàng loạt để lưu sẵn: chỉ xem khi có mạng
                self.lb.setText(f'Đã lưu {kq["lop"]} lớp KML. Nền "Bản đồ đường phố" không lưu sẵn được (chính sách OpenStreetMap) - '
                                'chọn Vệ tinh / Địa hình rồi lưu lại.')
                return kq
            o = ban_do_luu.o_vung_du_an(k, z_max)
            lop = lop[:1]                                # chỉ lớp ẢNH (chữ đường / địa danh nhỏ, tải khi có mạng): file dự án không phình
            viec = [(lp, z, x, y) for lp in lop for z, x, y in o]
            mb = len(viec) * ban_do_luu.KB_MOI_O / 1024
            if not self.im_lang and QMessageBox.question(
                    self, TEN_UD, f'Lưu {len(viec)} ô ảnh nền vùng dự án vào file dự án (khoảng {mb:.0f} MB)?\n\nFile dự án lớn thêm '
                    'tương ứng; sao lưu tự động, mốc khôi phục và đồng bộ Google Drive / máy chủ LAN cũng chép theo. Chọn "No" để chỉ '
                    'lưu các lớp KML (rất nhỏ).') != QMessageBox.StandardButton.Yes:
                viec = []
            tai = tai or (lambda z, x, y, lp: nen_ban_do.tai_o(z, x, y) if lp == nen_ban_do.NGUON else nen_ban_do.tai_o(z, x, y, lop=lp))

            def chay():                                  # luồng nền: chỉ tải ô (file đệm / mạng), không đụng Qt / CSDL
                ra = []
                for lp, z, x, y in viec:
                    try:
                        ra.append((lp, z, x, y, tai(z, x, y, lp)))
                    except Exception:                    # noqa: BLE001 - mất mạng một ô: đếm lỗi
                        ra.append((lp, z, x, y, None))
                return ra
            if self.im_lang:
                ra = chay()
            else:
                from .giao_dien import chay_nen
                ra = chay_nen(self, chay, f'Đang lưu ảnh nền vùng dự án ({len(viec)} ô) vào file dự án…')
            kq['loi'] = sum(1 for *_x, a in ra if not a)
            try:
                kq['o'] = ban_do_luu.luu_o(self.con, [r for r in ra if r[4]])
            except Exception as e:                      # noqa: BLE001
                self.lb.setText(chu_loi('Không lưu được ảnh nền vào dự án', e))
                return kq
        tt = ban_do_luu.tom_tat(self.con)
        self._cap_nhat_nut_luu()
        self.lb.setText(f'Đã lưu vào file dự án:{kq["lop"]} lớp KML, {kq["o"]} ô ảnh nền' +
                        (f' ({kq["loi"]} ô không tải được - mất mạng?)' if kq['loi'] else '') +
                        f'. Bản đồ trong dự án: {tt["lop"]} lớp, {tt["o"]} ô, {tt["kich"] / 2 ** 20:.1f} MB - lần sau mở là có sẵn.')
        return kq

    # ---- chuột phải một thửa
    def menu_cho_thua(self, t, diem=None):
        """Menu của thửa t: mở phương án hộ, sao chép số tờ / thửa, phóng tới thửa. diem None: chỉ dựng menu (kiểm thử), trả QMenu."""
        m = QMenu(self)
        if t.ma_ho is not None and self.mo_ho is not None:
            m.addAction(f'Mở phương án hộ: {t.ho_ten or t.ma_ho}', lambda: self._bam_ho(t.ma_ho))
        m.addAction(f'Sao chép "Thửa {t.so_thua} tờ {t.so_to}"',
                    lambda: QApplication.clipboard().setText(f'Thửa {t.so_thua} tờ {t.so_to}'))
        m.addAction('Phóng tới thửa này', lambda: self.view.tim(t.so_thua))
        if diem is None:
            return m
        m.exec(diem)
        m.deleteLater()
        return None

    def done(self, r):
        self._dung()
        super().done(r)

    def closeEvent(self, e):
        self._dung()
        super().closeEvent(e)

    def hideEvent(self, e):                             # đóng bằng nút X / bị ẩn trước khi hủy (deleteLater): dừng hẹn giờ, tải nền
        self._dung(chi_tam=True)
        super().hideEvent(e)

    def showEvent(self, e):
        self.view._song = True
        super().showEvent(e)

    def _dung(self, chi_tam: bool = False) -> None:
        self.hen_nen.stop()
        self.nen.huy()
        self.view._song = False
        if not chi_tam:
            self.view.tat()

    def _bam_ho(self, ma: int) -> None:
        if self.mo_ho is not None:
            self.mo_ho(ma)

    def _hien_toa_do(self, dong: float, bac: float) -> None:
        try:
            vd, kd = toa_do.vn2000_sang_wgs84(dong, bac, self.kt)
        except (ValueError, ZeroDivisionError, OverflowError):
            self.lb_toa_do.setText('')
            return
        self.lb_toa_do.setText(f'VN-2000 ({toa_do.chu_kinh_tuyen(self.kt)}): X {bac:,.2f}  Y {dong:,.2f}   ·   GPS {vd:.6f}, {kd:.6f}'
                               .replace(',', ' '))

    def xuat_kml(self, file=None):
        """Bản đồ thửa (tờ đang xem; "Tất cả các tờ" = cả dự án) -> .kml / .kmz. Trả đường dẫn hoặc None."""
        if file is None:
            if self.im_lang:
                return None
            to = self.cb_to.currentData()
            file, _ = QFileDialog.getSaveFileName(self, 'Xuất bản đồ thửa đất', f'BanDo_{"to_" + str(to) if to else "du_an"}.kmz',
                                                  'Google Earth nén (*.kmz);;Google Earth (*.kml)')
            if not file:
                return None
        try:
            with con_tro_cho():
                kq = ban_do_kml.xuat_kml(self.con, file, self.cb_to.currentData(), self.kt)
        except (ban_do_cad.LoiCad, OSError) as e:
            self.lb.setText(chu_loi('Không xuất được bản đồ', e))
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, chu_loi('Không xuất được bản đồ', e))
            return None
        self.lb.setText(f'Đã xuất {kq["so_thua"]} thửa ra {kq["file"]}')
        return kq['file']

    def _nhap(self) -> None:
        if self.nhap is not None and self.nhap():
            self.nap_to()
