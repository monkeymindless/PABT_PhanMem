"""Hồ sơ hộ: thông tin hộ và danh sách thửa, thêm hộ, gộp hộ, chuyển thửa, xóa hộ.

KhungHoSo là khung nhúng được (thẻ đầu tiên của cửa sổ Lập phương án - hồ sơ và phương án trong một cửa sổ); HopHoSo là hộp
thoại riêng dùng khung này. Quy tắc nằm trong ho_so; các hàm thao tác nhận tham số tùy chọn để kiểm thử không cần bấm hộp thoại.
"""
from __future__ import annotations
from PySide6.QtCore import QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen, QTextLayout, QTextOption
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QStyle,
                               QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import ho_so
from .giao_dien import MAU_CANH_BAO_CHU, MAU_CANH_BAO_NEN, ChonXoXuong
from .lap_pa import LoiNhap
from .tien import so_vn
from .thong_bao import TEN_UD

# 20/10/2026 bảng thửa 11 cột (+ cột ẩn vị trí mô tả): khóa trường, tiêu đề hiển thị. Khóa của ho_so.TRUONG_THUA là dữ liệu lưu; stt,
# dt_con_lai, vi_tri_gia (vị trí giá đất của thửa ở mục 1), thao_tac là ô tính / nút - không lưu
COT_THUA = [('stt', 'STT'), ('so_to', 'Tờ BĐ'), ('so_thua', 'Số thửa'), ('loai_dat', 'Loại đất'),
            ('dt_nguyen_thua', 'DT nguyên thửa (m²)'), ('dt_thu_hoi', 'DT thu hồi (m²)'), ('dt_con_lai', 'DT còn lại'),
            ('vi_tri_gia', 'Vị trí đất'), ('so_gcn', 'Giấy chứng nhận'), ('nguon_goc', 'Nguồn gốc & Vị trí đất'),
            ('thao_tac', 'Thao tác'), ('vi_tri', 'Vị trí (mô tả)')]
# tiêu đề hai dòng (chữ dài trong cột hẹp); chữ đầy đủ ở chú thích tiêu đề
TIEU_DE_HAI_DONG = {'dt_nguyen_thua': 'DT nguyên\nthửa (m²)', 'dt_thu_hoi': 'DT thu hồi\n(m²)', 'dt_con_lai': 'DT còn lại\n(m²)',
                    'so_gcn': 'Giấy chứng\nnhận'}
COT_AN = ('vi_tri',)                    # mô tả vị trí: cột ẩn - hiện ở dòng 1 ô "Nguồn gốc & Vị trí đất", sửa trong HopNguonGoc
COT_GIUA = ('stt', 'so_to', 'so_thua', 'loai_dat', 'vi_tri_gia', 'so_gcn')
COT_PHAI = ('dt_nguyen_thua', 'dt_thu_hoi', 'dt_con_lai')
COT_KHONG_SUA = ('stt', 'dt_con_lai', 'vi_tri_gia', 'thao_tac')
RONG_COT_THUA = {'stt': 44, 'so_to': 60, 'so_thua': 66, 'loai_dat': 86, 'dt_nguyen_thua': 104, 'dt_thu_hoi': 96, 'dt_con_lai': 96,
                 'vi_tri_gia': 132, 'so_gcn': 116, 'thao_tac': 96}
CAO_DONG_THUA = 44                      # cao_chuan: mọi dòng thửa cao bằng nhau (nguồn gốc rút gọn 2 dòng, xem đủ ở HopNguonGoc)
CAO_DONG_TOI_DA = 104                   # (giữ tên cũ) dòng thửa không cao quá mức này
CO_CHU_NHO_NHAT = 0.78
LIEN_KET_XEM = '[Xem/Sửa đủ ↗]'
MAU_LIEN_KET = '#2563EB'
CAN_GIUA = Qt.AlignmentFlag.AlignCenter
CAN_PHAI = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
# viên màu loại đất (nền, chữ) theo nhóm ký hiệu TT 08/2024 - mã đầu của loại ghép
MAU_LOAI_DAT = (
    (('ONT', 'ODT'), ('#FEF3C7', '#92400E')),
    (('LUC', 'LUK', 'LUN'), ('#ECFCCB', '#3F6212')),
    (('CLN', 'HNK', 'BHK', 'NHK', 'LNK', 'LNC', 'LNQ'), ('#DCFCE7', '#166534')),
    (('RSX', 'RPH', 'RDD', 'RST', 'RTS'), ('#D1FAE5', '#065F46')),
    (('NTS', 'NKH', 'LMU'), ('#E0F2FE', '#075985')),
)
MAU_LOAI_KHAC = ('#F1F5F9', '#334155')
MAU_VI_TRI_GIA = ('#EFF6FF', '#1D4ED8', '#BFDBFE')
# thẻ cơ cấu loại đất ở dải tổng hợp chân bảng (tên, các mã)
NHOM_THE_LOAI = (('ONT (Đất ở)', ('ONT', 'ODT')), ('LUK (Đất lúa)', ('LUC', 'LUK', 'LUN')),
                 ('CLN / HNK', ('CLN', 'HNK', 'BHK', 'NHK', 'LNK')))


def ma_dau(loai: str) -> str:
    """Mã đầu của loại đất (ghép 'ONT+CLN' -> 'ONT')."""
    return (' '.join(str(loai or '').split()).upper().replace(',', '+').split('+')[0]).strip()


def mau_loai_dat(loai: str) -> tuple:
    m = ma_dau(loai)
    for ds, mau in MAU_LOAI_DAT:
        if m in ds:
            return mau
    return MAU_LOAI_KHAC


def _ve_vien(p, vung: QRectF, chu: str, nen: str, mau_chu: str, vien: str | None = None, font: QFont | None = None) -> None:
    """Viên thuốc (chữ trong khung bo tròn) giữa vùng; chữ dài rút gọn "…"."""
    if not chu:
        return
    p.save()
    f = QFont(font) if font is not None else QFont(p.font())
    f.setBold(True)
    p.setFont(f)
    fm = QFontMetricsF(f)
    toi_da = max(10.0, vung.width() - 8)
    chu = fm.elidedText(chu, Qt.TextElideMode.ElideRight, toi_da - 14)
    rong = min(toi_da, fm.horizontalAdvance(chu) + 14)
    cao = min(vung.height() - 4, fm.height() + 6)
    r = QRectF(vung.center().x() - rong / 2, vung.center().y() - cao / 2, rong, cao)
    p.setRenderHint(p.RenderHint.Antialiasing, True)
    p.setPen(QPen(QColor(vien)) if vien else Qt.PenStyle.NoPen)
    p.setBrush(QColor(nen))
    p.drawRoundedRect(r, cao / 2, cao / 2)
    p.setPen(QColor(mau_chu))
    p.drawText(r, CAN_GIUA, chu)
    p.restore()


def _ve_nen_o(dg, option, index, p) -> QStyleOptionViewItem:
    """Vẽ nền ô (chọn / dòng xen kẽ) theo kiểu của bảng, không vẽ chữ. dg: delegate gọi. Trả QStyleOptionViewItem đã khởi tạo."""
    op = QStyleOptionViewItem(option)
    dg.initStyleOption(op, index)
    op.text = ''
    w = op.widget
    if w is not None:
        w.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, op, p, w)
    return op


def _bo_tri_chu(chu: str, font: QFont, rong: float) -> tuple:
    """Ngắt dòng chữ theo bề rộng: [(QTextLayout, chiều cao)] và tổng chiều cao. Đoạn bắt đầu bằng gạch đầu dòng ("- ",
    "+ ", "a) "…): các dòng tràn thụt vào thẳng chữ sau ký hiệu (ho_so.dau_dong)."""
    ds, tong = [], 0.0
    fm = QFontMetricsF(font)
    # chữ hiển thị của ô (QStyledItemDelegate.initStyleOption) đã đổi '\n' thành U+2028 (QChar::LineSeparator): tách cả hai,
    # không thì cả ô là một đoạn và gạch đầu dòng bên trong không được nhận ra
    for doan in chu.replace('\u2028', '\n').split('\n'):
        tl = QTextLayout(doan, font)
        op = QTextOption()
        op.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        tl.setTextOption(op)
        ky = ho_so.dau_dong(doan)
        thut = min(fm.horizontalAdvance(ky), rong / 3) if ky else 0.0
        tl.beginLayout()
        h = 0.0
        while True:
            dong = tl.createLine()
            if not dong.isValid():
                break
            x = thut if h > 0 else 0.0                     # dòng đầu đoạn sát lề, dòng tràn thụt vào
            dong.setLineWidth(rong - x)
            dong.setPosition(QRectF(x, h, 0, 0).topLeft())
            h += dong.height()
        tl.endLayout()
        ds.append((tl, h))
        tong += h
    return ds, tong


def chu_gon(chu: str) -> str:
    """Nguồn gốc / vị trí nhiều dòng -> một dòng (bỏ gạch đầu dòng, gộp khoảng trắng) để rút gọn trong ô."""
    ds = []
    for doan in str(chu or '').replace('\u2028', '\n').split('\n'):
        doan = doan.strip()
        ky = ho_so.dau_dong(doan)
        if ky:
            doan = doan[len(ky):].strip()
        if doan:
            ds.append(doan)
    return ' '.join(' '.join(ds).split())


class HopNguonGoc(QDialog):
    """Xem / sửa nguồn gốc đất (trích lục) của một thửa trong hộp riêng - bấm đúp ô Nguồn gốc (0.9.75): khung sửa tràn trong ô làm
    vỡ chiều cao dòng bảng thửa. Dòng "- " tự thụt lề treo như ô trong bảng (ho_so.chuan_nguon_goc). vi_tri (20/10/2026): mô tả
    vị trí của thửa (dòng 1 ô "Nguồn gốc & Vị trí đất") - None: không hiện ô vị trí."""

    def __init__(self, parent, chu: str, thua: str = '', vi_tri: str | None = None, im_lang: bool = False):
        super().__init__(parent)
        self.im_lang = im_lang
        self.setWindowTitle('Nguồn gốc & Vị trí đất' + (f' - {thua}' if thua else ''))
        self.resize(760, 420)
        lo = QVBoxLayout(self)
        self.o_vi_tri = None
        if vi_tri is not None:
            h = QHBoxLayout()
            nhan = QLabel('Vị trí (mô tả):')
            nhan.setProperty('vai', 'nhan')
            h.addWidget(nhan)
            self.o_vi_tri = QLineEdit(str(vi_tri or ''))
            self.o_vi_tri.setPlaceholderText('Ví dụ: mặt tiền đường số 9, cách ngã ba … khoảng … m')
            h.addWidget(self.o_vi_tri, 1)
            lo.addLayout(h)
        self.o = QPlainTextEdit(ho_so.chuan_nguon_goc(chu))
        self.o.setTabChangesFocus(True)
        self.o.setPlaceholderText('Nguồn gốc, quá trình sử dụng đất (trích lục). Mỗi ý một dòng, bắt đầu bằng "- ".')
        # 1.0.04: thanh chèn nhanh mẫu câu nguồn gốc (Thông tư 08/2024, Quyết định 18/2026) tại con trỏ
        h = QHBoxLayout()
        h.addWidget(QLabel('Chèn mẫu câu:'))
        self.cb_mau = QComboBox()
        self.cb_mau.addItem('— chọn mẫu câu để chèn tại con trỏ —', '')
        for ten, cau in MAU_CAU_NGUON_GOC:
            self.cb_mau.addItem(ten, cau)
            self.cb_mau.setItemData(self.cb_mau.count() - 1, cau, Qt.ItemDataRole.ToolTipRole)
        self.cb_mau.activated.connect(lambda i: self.chen_mau(self.cb_mau.itemData(i)))
        h.addWidget(self.cb_mau, 1)
        lo.addLayout(h)
        lo.addWidget(self.o, 1)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.o.setFocus()

    def chen_mau(self, cau: str) -> None:
        """Chèn mẫu câu tại con trỏ; câu bắt đầu "- " ở giữa dòng thì xuống dòng trước."""
        if not cau:
            return
        c = self.o.textCursor()
        if cau.startswith('- ') and c.positionInBlock() > 0:
            cau = '\n' + cau
        c.insertText(cau)
        self.o.setTextCursor(c)
        self.o.setFocus()
        self.cb_mau.setCurrentIndex(0)

    def chu(self) -> str:
        return ho_so.chuan_nguon_goc(self.o.toPlainText())

    def vi_tri(self) -> str | None:
        return ' '.join(self.o_vi_tri.text().split()) if self.o_vi_tri is not None else None


class ONguonGoc(QStyledItemDelegate):
    """Ô "Nguồn gốc & Vị trí đất" (20/10/2026): dòng cao cố định CAO_DONG_THUA, chữ rút gọn hai dòng
        • Vị trí: <mô tả vị trí>…
        • Nguồn gốc: <nguồn gốc>… [Xem/Sửa đủ ↗]
    Bấm đúp ô hoặc bấm "[Xem/Sửa đủ ↗]" (hoặc Enter): mở HopNguonGoc sửa đủ cả hai - không làm vỡ chiều cao dòng. Gõ phím: sửa
    nguồn gốc trong khung nhiều dòng (Enter ghi, Shift+Enter xuống dòng)."""

    LE = 4
    im_lang = False                      # kiểm thử: không mở hộp (trả về chữ mới qua `chu_moi`, `vi_tri_moi`)
    chu_moi = None
    vi_tri_moi = None
    cot_vi_tri = None                    # cột (ẩn) giữ mô tả vị trí - KhungHoSo đặt

    def _vi_tri(self, index) -> str:
        if self.cot_vi_tri is None:
            return ''
        return str(index.model().index(index.row(), self.cot_vi_tri).data() or '')

    def vung_lien_ket(self, rect, font) -> QRectF:
        """Vùng chữ "[Xem/Sửa đủ ↗]" (cuối dòng 2) trong ô."""
        fm = QFontMetricsF(font)
        vung = QRectF(rect).adjusted(self.LE + 2, self.LE, -self.LE - 2, -self.LE)
        rong = fm.horizontalAdvance(LIEN_KET_XEM)
        cao = fm.height()
        y = vung.top() + max(0.0, (vung.height() - 2 * cao) / 2) + cao
        return QRectF(vung.right() - rong, y, rong, cao)

    def mo_hop(self, model, index, w=None) -> bool:
        """Mở hộp xem / sửa đủ nguồn gốc + vị trí của dòng; ghi vào bảng khi Lưu. Trả True nếu có đổi."""
        if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
            return False
        if w is not None and w.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers:
            return False                                   # chỉ xem
        chu, vt = str(index.data() or ''), self._vi_tri(index)
        if self.im_lang:
            moi, vt_moi = self.chu_moi, self.vi_tri_moi
        else:
            thua = ' / '.join(str(model.index(index.row(), c).data() or '') for c in (1, 2)).strip(' /')
            d = HopNguonGoc(w.window() if w is not None else None, chu, f'tờ / thửa {thua}' if thua else '',
                            vi_tri=vt if self.cot_vi_tri is not None else None)
            if d.exec() != QDialog.DialogCode.Accepted:
                return False
            moi, vt_moi = d.chu(), d.vi_tri()
        doi = False
        if vt_moi is not None and vt_moi != vt and self.cot_vi_tri is not None:
            model.setData(model.index(index.row(), self.cot_vi_tri), vt_moi)
            doi = True
        if moi is not None and moi != chu:
            model.setData(index, moi)
            doi = True
        if doi:                                            # cột vị trí ẩn: vẽ lại ô
            model.dataChanged.emit(index, index)
        return doi

    def editorEvent(self, event, model, option, index):
        """Bấm đúp ô / bấm "[Xem/Sửa đủ ↗]": mở HopNguonGoc (không dùng khung sửa tràn trong ô)."""
        t = event.type()
        if t == QEvent.Type.MouseButtonDblClick and (index.flags() & Qt.ItemFlag.ItemIsEditable):
            w = option.widget
            if w is not None and w.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers:
                return False                                   # chỉ xem
            self.mo_hop(model, index, w)
            return True
        if t == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self.vung_lien_ket(option.rect, option.font).contains(event.position() if hasattr(event, 'position')
                                                                     else event.pos()):
                self.mo_hop(model, index, option.widget)
                return True
        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        o = QPlainTextEdit(parent)
        o.setTabChangesFocus(True)
        o.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        o.installEventFilter(self)
        return o

    def setEditorData(self, o, index):
        o.setPlainText(ho_so.chuan_nguon_goc(index.data()))
        o.moveCursor(o.textCursor().MoveOperation.End)

    def setModelData(self, o, model, index):
        model.setData(index, ho_so.chuan_nguon_goc(o.toPlainText()))

    def updateEditorGeometry(self, o, option, index):
        r = option.rect
        vp = o.parentWidget()
        cao = max(r.height(), 170)
        y = r.y()
        if vp is not None and y + cao > vp.height():          # dòng cuối bảng: khung sửa đẩy lên cho đủ chỗ
            y = max(0, vp.height() - cao)
        o.setGeometry(r.x(), y, r.width(), cao)

    def eventFilter(self, o, e):
        if e.type() == QEvent.Type.KeyPress and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.commitData.emit(o)
            self.closeEditor.emit(o)
            return True
        return super().eventFilter(o, e)

    def paint(self, p, option, index):
        op = _ve_nen_o(self, option, index, p)
        w = op.widget
        if w is None:
            return super().paint(p, option, index)
        chu, vt = chu_gon(index.data()), chu_gon(self._vi_tri(index))
        font = QFont(op.font)
        fm = QFontMetricsF(font)
        dam = QFont(font)
        dam.setBold(True)
        fmd = QFontMetricsF(dam)
        vung = QRectF(op.rect).adjusted(self.LE + 2, self.LE, -self.LE - 2, -self.LE)
        cao = fm.height()
        y = vung.top() + max(0.0, (vung.height() - 2 * cao) / 2)
        chon = bool(op.state & QStyle.StateFlag.State_Selected)
        mau = op.palette.highlightedText().color() if chon else op.palette.text().color()
        phu = mau if chon else QColor('#64748B')
        p.save()
        lk = self.vung_lien_ket(op.rect, font)
        for i, (nhan, gt) in enumerate((('• Vị trí: ', vt), ('• Nguồn gốc: ', chu))):
            yy = y + i * cao
            p.setFont(dam)
            p.setPen(phu)
            rn = fmd.horizontalAdvance(nhan)
            p.drawText(QRectF(vung.left(), yy, rn + 1, cao), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), nhan)
            p.setFont(font)
            con = vung.width() - rn - (lk.width() + 8 if i == 1 else 0)
            if gt:
                p.setPen(mau)
                hien = fm.elidedText(gt, Qt.TextElideMode.ElideRight, max(10.0, con))
            else:
                p.setPen(QColor('#94A3B8'))
                hien = '(chưa ghi)'
            p.drawText(QRectF(vung.left() + rn, yy, max(10.0, con), cao),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), hien)
        p.setPen(mau if chon else QColor(MAU_LIEN_KET))
        p.drawText(lk, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), LIEN_KET_XEM)
        p.restore()

    def sizeHint(self, option, index):
        kq = super().sizeHint(option, index)
        kq.setHeight(CAO_DONG_THUA)
        return kq


class OLoaiDat(ChonXoXuong):
    """Ô loại đất: viên màu theo nhóm (đất ở, lúa, cây lâu năm / hằng năm, rừng, thủy sản); sửa = danh sách xổ xuống như cũ."""

    def paint(self, p, option, index):
        _ve_nen_o(self, option, index, p)
        chu = str(index.data() or '').strip()
        nen, mau = mau_loai_dat(chu)
        _ve_vien(p, QRectF(option.rect), chu, nen, mau, font=option.font)


class OVienThuoc(QStyledItemDelegate):
    """Ô chỉ xem dạng viên màu (vị trí giá đất của thửa ở mục 1)."""

    def __init__(self, mau: tuple, parent=None):
        super().__init__(parent)
        self.mau = mau

    def paint(self, p, option, index):
        _ve_nen_o(self, option, index, p)
        nen, chu_mau, vien = self.mau
        _ve_vien(p, QRectF(option.rect), str(index.data() or '').strip(), nen, chu_mau, vien, font=option.font)


class OThaoTac(QStyledItemDelegate):
    """Cột Thao tác: nút "Sửa" (xem / sửa đủ nguồn gốc & vị trí) + thùng rác (xóa thửa). Bấm gọi khung.sua_dong(r) / xoa_dong(r)."""

    RONG_SUA = 44

    def __init__(self, khung, parent=None):
        super().__init__(parent)
        self.khung = khung

    def vung(self, rect) -> tuple:
        r = QRectF(rect).adjusted(4, 8, -4, -8)
        sua = QRectF(r.left(), r.top(), min(self.RONG_SUA, r.width() * 0.6), r.height())
        xoa = QRectF(sua.right() + 6, r.top(), max(0.0, r.right() - sua.right() - 6), r.height())
        return sua, xoa

    def paint(self, p, option, index):
        _ve_nen_o(self, option, index, p)
        sua, xoa = self.vung(option.rect)
        tat = getattr(self.khung, 'chi_doc', False)
        p.save()
        p.setRenderHint(p.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor('#CBD5E1')))
        p.setBrush(QColor('#FFFFFF'))
        p.drawRoundedRect(sua, 4, 4)
        f = QFont(option.font)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor('#94A3B8' if tat else '#0F294A'))
        p.drawText(sua, CAN_GIUA, 'Sửa')
        from .giao_dien import icon_ky_hieu
        ic = icon_ky_hieu(0xE74D, '#94A3B8' if tat else '#B91C1C', 16)
        if ic is not None:
            p.drawPixmap(int(xoa.center().x() - 8), int(xoa.center().y() - 8), ic.pixmap(16, 16))
        else:
            p.setPen(QColor('#94A3B8' if tat else '#B91C1C'))
            p.drawText(xoa, CAN_GIUA, '×')
        p.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if getattr(self.khung, 'chi_doc', False):
                return True
            pos = event.position() if hasattr(event, 'position') else event.pos()
            sua, xoa = self.vung(option.rect)
            if sua.contains(pos):
                self.khung.sua_dong(index.row())
                return True
            if xoa.contains(pos):
                self.khung.xoa_dong(index.row())
                return True
        return super().editorEvent(event, model, option, index)


CAO_TOM_TAT_THUA = 34
# nhãn ô thông tin chủ sử dụng (tổ chức: "Tổ chức" / "Địa chỉ", ẩn các ô AN_KHI_TO_CHUC - 1.0.04)
NHAN_HO = {'ho_ten': 'Họ và tên', 'so_cccd': 'Số CCCD/Định danh', 'ngay_cap': 'Ngày cấp / Nơi cấp', 'dia_chi': 'Địa chỉ thường trú',
           'dien_thoai': 'Số điện thoại', 'phap_ly': 'Tình trạng pháp lý', 'ghi_chu': 'Ghi chú hồ sơ hộ', 'tranh_chap': 'Tranh chấp',
           'tai_dinh_cu': 'Tái định cư', 'trang_thai': 'Trạng thái'}
AN_KHI_TO_CHUC = ('so_cccd', 'ngay_cap', 'noi_cap', 'dien_thoai')
# lưới 3 cột khối I (20/10/2026, theo ảnh người dùng): khóa -> (hàng, cột). Ngày cấp + nơi cấp chung một ô; "Hồ sơ đính kèm" (nút
# NutHoSoScan) ở hàng 2 cột 2. Trường không có ở đây (an=) không hiện
O_LUOI_HO = {'ho_ten': (0, 0), 'so_cccd': (0, 1), 'ngay_cap': (0, 2), 'dia_chi': (1, 0), 'dien_thoai': (1, 1), 'phap_ly': (1, 2),
             'ghi_chu': (2, 0), 'tranh_chap': (2, 1), 'tai_dinh_cu': (3, 0), 'trang_thai': (3, 1)}
O_HO_SO_DINH_KEM = (2, 2)
# tên thuộc tính theo đặc tả (bí danh của self.o / self.nhan_o)
BI_DANH_O = {'ho_ten': ('lb_ten', 'o_ten'), 'so_cccd': ('lb_cccd', 'o_cccd'), 'ngay_cap': ('lb_ngay_cap', 'o_ngay_cap'),
             'dia_chi': ('lb_dia_chi', 'o_dia_chi'), 'dien_thoai': ('lb_sdt', 'o_sdt'), 'ghi_chu': ('lb_ghi_chu', 'o_ghi_chu'),
             'phap_ly': ('lb_tinh_trang', 'o_phap_ly')}
GOI_Y_SAO_CHEP = 'Ctrl+C: sao chép ô'
# mẫu câu nguồn gốc đất (HopNguonGoc - chèn tại con trỏ; '…' là chỗ điền). Không ghi số liệu thật.
MAU_CAU_NGUON_GOC = (
    ('Mở đầu thửa', 'Thửa đất số …, tờ bản đồ số …, xã …: '),
    ('Khai phá, sử dụng ổn định', '- Đất do ông (bà) … khai phá, sử dụng ổn định, liên tục từ năm …, không tranh chấp.'),
    ('Đã cấp Giấy chứng nhận', '- Đất đã được cấp Giấy chứng nhận quyền sử dụng đất số … ngày … do … cấp.'),
    ('Nhận chuyển nhượng', '- Nhận chuyển nhượng quyền sử dụng đất của ông (bà) … năm … (… ).'),
    ('Nhận thừa kế, tặng cho', '- Nhận thừa kế / tặng cho từ ông (bà) … năm ….'),
    ('Đất UBND xã quản lý', '- Đất do UBND xã … quản lý; hộ chỉ có tài sản, cây trồng trên đất.'),
    ('Giao khoán', '- Đất nhận giao khoán theo Hợp đồng số … ngày … của …; hộ là chủ sở hữu tài sản gắn liền với đất.'),
    ('Thuê, mượn đất', '- Đất thuê / mượn của … từ năm …; hộ tạo lập tài sản trên đất.'),
    ('Loại đất TT 08/2024', '- Loại đất theo hiện trạng sử dụng: … (ký hiệu theo Thông tư 08/2024/TT-BTNMT).'),
    ('Xác nhận của UBND xã (QĐ 18/2026)', '- Căn cứ Giấy xác nhận nguồn gốc đất số … ngày … của UBND xã … (trình tự Quyết định '
                                         '18/2026/QĐ-UBND).'),
    ('Không tranh chấp, lấn chiếm', '- Không tranh chấp, khiếu nại; không thuộc trường hợp lấn, chiếm đất.'),
)
# kiểu khối chủ hộ / thẻ nhỏ / dải tổng hợp thửa: ở QSS chung (giao_dien.QSS_HO_SO_HO) - setStyleSheet trên khung chứa bắt Qt tính
# lại kiểu cả cây con (mở cửa sổ lập PA chậm 20%, đo 1.0.03)


def _the_nho(chu: str = '', loai: str = 'xam') -> QLabel:
    """Thẻ nhỏ (badge) - màu theo property the_nho (QSS_HO_SO_HO): vang / xanh / do / lam / xam."""
    lb = QLabel(chu)
    lb.setProperty('the_nho', loai)
    return lb


def _dat_loai_the(lb: QLabel, loai: str) -> None:
    from .giao_dien import dat_the_nho
    dat_the_nho(lb, loai)


class KhungHoSo(QWidget):
    """Thông tin hộ + bảng thửa + các thao tác gộp / chuyển / xóa. an: các trường thông tin hộ không hiện (giữ nguyên khi lưu).
    Gọi lại: khi_thay_doi_csdl() sau khi ghi CSDL (lưu, gộp, chuyển); khi_xoa_ho(thông báo) sau khi xóa hộ.
    20/10/2026: khối I "Định danh chủ sử dụng đất" lưới 3 cột + thẻ nhỏ (loại đối tượng, kiểm tra CCCD); khối II bảng thửa 11 cột
    (COT_THUA), nguồn gốc rút gọn 2 dòng, dải tổng hợp địa chính chân bảng (#thanh_tom_tat_thua)."""

    def __init__(self, con, ma_ho=None, parent=None, an=(), khi_thay_doi_csdl=None, khi_xoa_ho=None):
        super().__init__(parent)
        self.con = con
        self.ma_ho = ma_ho
        self.thay_doi_csdl = False          # đã gộp / chuyển / xóa (cửa sổ chính cần tải lại)
        self.canh_bao = []
        self.khi_thay_doi_csdl, self.khi_xoa_ho = khi_thay_doi_csdl, khi_xoa_ho
        self.o = {}
        self.nhan_o = {}                    # nhãn từng ô (đổi "Họ và tên" -> "Tổ chức" khi chủ sử dụng là tổ chức)
        from .man_hinh_ho_so_scan import NutHoSoScan
        self.nut_scan = NutHoSoScan()                   # 0.9.96: hồ sơ scan (PDF / ảnh) của hộ - đính kèm, mở nhanh
        lo = QVBoxLayout(self)
        lo.setSpacing(8)
        lo.addWidget(self._khoi_chu_ho([k for k, _ in ho_so.TRUONG_HO if k not in an]))
        lo.addLayout(self._hang_tieu_de_thua())
        khoi = QVBoxLayout()
        khoi.setSpacing(0)
        khoi.addWidget(self._tao_bang(), 1)
        khoi.addWidget(self._thanh_tom_tat())
        lo.addLayout(khoi, 1)
        from .giao_dien import gan_chu_khi_trong
        gan_chu_khi_trong(self.bang, 'Hộ chưa có thửa đất thu hồi', 'Bấm "+ Thêm thửa" để nhập tờ, thửa, loại đất, diện tích.')
        self._hen_tom_tat = QTimer(self)
        self._hen_tom_tat.setSingleShot(True)
        self._hen_tom_tat.setInterval(0)
        self._hen_tom_tat.timeout.connect(self.cap_nhat_tom_tat_thua)
        m = self.bang.model()
        for tin in (m.rowsInserted, m.rowsRemoved, m.modelReset, m.dataChanged):
            tin.connect(lambda *_: self._hen_tom_tat.start())
        from .giao_dien import BangHoanTac
        self._ht_bang = None
        self.nap()
        self._ht_bang = BangHoanTac(self.bang)                  # Ctrl+Z / Ctrl+Y: sửa ô trong bảng thửa

    # ---------------------------------------------- dựng khối I
    def _khoi_chu_ho(self, ds_truong: list) -> QFrame:
        """Khối I: tiêu đề + thẻ nhỏ, lưới 3 cột (nhãn | ô) x 3 hàng (O_LUOI_HO)."""
        khung = QFrame()
        khung.setObjectName('khung_chu_ho')
        khung.setProperty('vai', 'the_form')
        self.the_chu_ho = khung
        lo = QVBoxLayout(khung)
        lo.setContentsMargins(12, 8, 12, 10)
        lo.setSpacing(6)
        h = QHBoxLayout()
        h.setSpacing(6)
        td = QLabel('I. Chủ sử dụng đất, chủ sở hữu tài sản')
        td.setProperty('vai', 'tieu_de')
        h.addWidget(td)
        h.addStretch(1)
        self.the_loai_doi_tuong = _the_nho('', 'vang')
        self.the_cccd = _the_nho('', 'xanh')
        self.the_sao_chep = _the_nho(GOI_Y_SAO_CHEP, 'lam')
        self.the_sao_chep.setToolTip('Bảng thửa: nhấp một lần chọn ô, Ctrl+C chép giá trị ô, Ctrl+Shift+C chép cả dòng thửa.')
        for t in (self.the_loai_doi_tuong, self.the_cccd, self.the_sao_chep):
            h.addWidget(t)
        lo.addLayout(h)
        luoi = QGridLayout()
        luoi.setHorizontalSpacing(8)
        luoi.setVerticalSpacing(6)
        self.luoi_ho = luoi
        for k in ds_truong:
            w = QLineEdit()
            w.setObjectName({'ho_ten': 'o_ten', 'so_cccd': 'o_cccd', 'phap_ly': 'o_phap_ly'}.get(k, f'o_{k}'))
            self.o[k] = w
        for k, w in self.o.items():
            if k == 'noi_cap':
                continue
            vt = O_LUOI_HO.get(k)
            if vt is None:                                     # trường mới chưa có chỗ: hàng cuối
                vt = (4 + len(self.nhan_o), 0)
            hang, cot = vt
            nhan = QLabel(NHAN_HO.get(k, dict(ho_so.TRUONG_HO).get(k, k)) + ':')
            nhan.setProperty('vai', 'nhan')
            self.nhan_o[k] = nhan
            luoi.addWidget(nhan, hang, cot * 2)
            if k == 'ngay_cap' and 'noi_cap' in self.o:        # ngày cấp + nơi cấp chung một ô
                hh = QHBoxLayout()
                hh.setSpacing(4)
                w.setPlaceholderText('dd/mm/yyyy')
                w.setMaximumWidth(110)
                hh.addWidget(w)
                self.o['noi_cap'].setPlaceholderText('Nơi cấp')
                hh.addWidget(self.o['noi_cap'], 1)
                luoi.addLayout(hh, hang, cot * 2 + 1)
            else:
                luoi.addWidget(w, hang, cot * 2 + 1)
        nhan = QLabel('Hồ sơ đính kèm:')
        nhan.setProperty('vai', 'nhan')
        self.lb_dinh_kem = nhan
        luoi.addWidget(nhan, O_HO_SO_DINH_KEM[0], O_HO_SO_DINH_KEM[1] * 2)
        luoi.addWidget(self.nut_scan, O_HO_SO_DINH_KEM[0], O_HO_SO_DINH_KEM[1] * 2 + 1)
        for c in (1, 3, 5):
            luoi.setColumnStretch(c, 1)
        lo.addLayout(luoi)
        for k, (ten_nhan, ten_o) in BI_DANH_O.items():
            if k in self.o:
                setattr(self, ten_nhan, self.nhan_o[k])
                setattr(self, ten_o, self.o[k])
        if 'phap_ly' in self.o:
            self.o['phap_ly'].setPlaceholderText('Ví dụ: GCN QSDĐ - Không tranh chấp')
        for w in self.o.values():                   # Enter ở ô thông tin hộ: sang ô kế tiếp
            w.returnPressed.connect(self.focusNextChild)
        if 'ho_ten' in self.o:
            self.o['ho_ten'].textChanged.connect(lambda _=None: self.cap_nhat_nhan_to_chuc())
        if 'so_cccd' in self.o:
            self.o['so_cccd'].textChanged.connect(lambda _=None: self.kiem_cccd())
        return khung

    # ---------------------------------------------- dựng khối II
    def _hang_tieu_de_thua(self) -> QHBoxLayout:
        self.nut = {}
        from .giao_dien import KieuNut, ap_kieu_nut
        b_them = QPushButton('+ Thêm thửa')
        ap_kieu_nut(b_them, KieuNut.CHINH)
        b_them.clicked.connect(lambda: self.them_dong())
        self.nut['Thêm thửa'] = b_them
        menu = QMenu(self)
        for x in (('Tách theo loại đất', lambda: self.tach_dong()), ('Xóa thửa', lambda: self.xoa_dong()), None,
                  ('Chuyển thửa sang hộ khác…', lambda: self.chuyen_thua()),
                  ('Gộp hộ khác vào hộ này…', lambda: self.gop_ho()), None, ('Xóa hộ…', lambda: self.xoa_ho())):
            if x is None:
                menu.addSeparator()
                continue
            ten, ham = x
            a = menu.addAction(ten)
            a.triggered.connect(ham)
            self.nut[ten] = a
        self.b_thao_tac = QPushButton('Tách / Chuyển thửa')
        self.b_thao_tac.setMenu(menu)
        self.b_thao_tac.setToolTip('Tách thửa theo loại đất, xóa thửa, chuyển thửa sang hộ khác, gộp hộ, xóa hộ')
        from .giao_dien import NhanRutGon
        self.lb = NhanRutGon('')                    # một dòng, rút "…" (chữ đủ ở chú thích) - trước: xuống dòng dựng đứng từng chữ
        h = QHBoxLayout()
        h.setSpacing(8)
        self.lb_tieu_de_thua = QLabel('')
        self.lb_tieu_de_thua.setProperty('vai', 'tieu_de')
        h.addWidget(self.lb_tieu_de_thua)
        h.addWidget(self.lb, 1)
        self.the_goi_y_bang = _the_nho('Bấm đúp Nguồn gốc: xem / sửa đủ', 'lam')
        h.addWidget(self.the_goi_y_bang)
        h.addWidget(b_them)
        h.addWidget(self.b_thao_tac)
        return h

    def _tao_bang(self) -> QTableWidget:
        self.cot = [k for k, _ in COT_THUA]
        b = QTableWidget(0, len(COT_THUA))
        self.bang = b
        for c, (k, ten) in enumerate(COT_THUA):
            it = QTableWidgetItem(TIEU_DE_HAI_DONG.get(k, ten))
            it.setToolTip(ten)
            b.setHorizontalHeaderItem(c, it)
        # chọn TỪNG Ô (nhấp một lần -> Ctrl+C chép ô); Shift / Ctrl chọn nhiều ô - xóa thửa lấy mọi dòng có ô được chọn
        b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        b.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        b.setProperty('cot_dinh_danh', [self.cot.index('so_thua')])   # "Số thửa" ở đây là số hiệu thửa: bộ đếm không cộng
        b.setAlternatingRowColors(True)
        b.setWordWrap(False)
        b.setMinimumHeight(170)
        tieu = b.horizontalHeader()
        tieu.setStretchLastSection(False)
        tieu.setHighlightSections(False)                    # không tô tiêu đề cột của ô đang chọn (chọn từng ô)
        for k, w in RONG_COT_THUA.items():
            b.setColumnWidth(self.cot.index(k), w)
        tieu.setSectionResizeMode(self.cot.index('nguon_goc'), QHeaderView.ResizeMode.Stretch)   # hết bề rộng còn lại
        for k in COT_AN:
            b.setColumnHidden(self.cot.index(k), True)
        from .giao_dien import giu_cot_gian
        self._giu_gian = giu_cot_gian(b, [self.cot.index('nguon_goc')], 220)   # 22/10/2026: không bóp nát cột Nguồn gốc
        from .giao_dien import cho_phep_sao_chep_bang, nhap_bang_phim
        from .loai_dat import ds_chon
        # loại đất: danh mục theo Luật Đất đai 2024, ký hiệu TT 08/2024 (gõ tay được loại ghép, vd ONT+CLN); hiện viên màu theo nhóm
        self._ld = OLoaiDat(ds_chon(self.con), b)
        b.setItemDelegateForColumn(self.cot.index('loai_dat'), self._ld)
        self._ng = ONguonGoc(b)
        self._ng.cot_vi_tri = self.cot.index('vi_tri')
        b.setItemDelegateForColumn(self.cot.index('nguon_goc'), self._ng)
        self._vtg = OVienThuoc(MAU_VI_TRI_GIA, b)
        b.setItemDelegateForColumn(self.cot.index('vi_tri_gia'), self._vtg)
        self._tt = OThaoTac(self, b)
        b.setItemDelegateForColumn(self.cot.index('thao_tac'), self._tt)
        nhap_bang_phim(b)
        vh = b.verticalHeader()
        vh.setMinimumSectionSize(CAO_DONG_THUA)
        vh.setDefaultSectionSize(CAO_DONG_THUA)
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setVisible(False)                                # cột STT thay số dòng
        b.itemChanged.connect(self._doi_o)
        b.installEventFilter(self)                          # Enter ở ô nguồn gốc: mở hộp xem / sửa đủ (chạy trước _PhimBang)
        b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        b.customContextMenuRequested.connect(lambda pos: self.menu_bang(pos))
        cho_phep_sao_chep_bang(b)
        return b

    def _thanh_tom_tat(self) -> QFrame:
        """Dải tổng hợp địa chính chân bảng: chữ tóm tắt (trái) + thẻ cơ cấu loại đất (phải)."""
        f = QFrame()
        f.setObjectName('thanh_tom_tat_thua')
        f.setMinimumHeight(CAO_TOM_TAT_THUA)
        h = QHBoxLayout(f)
        h.setContentsMargins(10, 4, 10, 4)
        h.setSpacing(6)
        self.thanh_tom_tat_thua = f
        self.lb_tom_tat_thua = QLabel('')
        self.lb_tom_tat_thua.setObjectName('tom_tat_thua')
        self.lb_tom_tat_thua.setWordWrap(True)
        h.addWidget(self.lb_tom_tat_thua, 1)
        self.khoi_the_loai = QHBoxLayout()
        self.khoi_the_loai.setSpacing(6)
        h.addLayout(self.khoi_the_loai)
        self.the_loai = []
        return f

    # ---------------------------------------------- nạp / thu thập
    def nap(self, ma_ho=None):
        if ma_ho is not None:
            self.ma_ho = ma_ho
        if self.ma_ho is None:
            ho = {k: '' for k, _ in ho_so.TRUONG_HO}
            ho.update(thua=[], so_dong_pa=0)
            vt_gia = {}
        else:
            ho = ho_so.doc_ho(self.con, self.ma_ho)
            vt_gia = self._vi_tri_gia()
        self.ho_ten = ho['ho_ten']
        for k, w in self.o.items():
            w.setText(str(ho.get(k) or ''))
            w.setCursorPosition(0)
        self.bang.setRowCount(0)
        for t in ho['thua']:
            self.them_dong(dict(t, vi_tri_gia=vt_gia.get(t.get('ma_thua'), '')))
        for ten in ('Chuyển thửa sang hộ khác…', 'Gộp hộ khác vào hộ này…', 'Xóa hộ…'):    # QAction trong menu
            self.nut[ten].setEnabled(self.ma_ho is not None)
        self.nut_scan.dat(self.con, self.ma_ho, bool(getattr(self, 'chi_doc', False)))
        self.lb.setText(f'Hộ đã có {ho["so_dong_pa"]} dòng phương án. ' if ho['so_dong_pa'] else '')
        self.chinh_cao_dong()
        self.cap_nhat_tom_tat_thua()
        self.cap_nhat_nhan_to_chuc()
        self.ban_dau = self.thu_thap()
        if getattr(self, '_ht_bang', None) is not None:
            self._ht_bang.ghi_nho()

    def _vi_tri_gia(self) -> dict:
        """{mã thửa: vị trí giá đất ở mục 1 (mọi lần lập phương án, không trùng)} - cột "Vị trí đất" chỉ xem."""
        kq = {}
        for r in self.con.execute('SELECT ma_thua, vi_tri FROM ct_dat WHERE ma_ho = ? AND ma_thua IS NOT NULL ORDER BY thu_tu',
                                  (self.ma_ho,)):
            v = ' '.join(str(r['vi_tri'] or '').split())
            if v and v not in kq.setdefault(r['ma_thua'], []):
                kq[r['ma_thua']].append(v)
        return {k: '; '.join(v) for k, v in kq.items()}

    def _so(self, r: int, k: str):
        """Số ở ô (Decimal) - trống / công thức / chữ lạ: None."""
        from .tien import D, doc_so_vn
        it = self.bang.item(r, self.cot.index(k))
        chu = it.text().strip() if it is not None else ''
        if not chu:
            return None
        try:
            return D(doc_so_vn(chu))
        except Exception:                                # công thức / chữ lạ: tính khi lưu
            return None

    def _chu(self, r: int, k: str) -> str:
        it = self.bang.item(r, self.cot.index(k))
        return it.text().strip() if it is not None else ''

    def tom_tat_thua(self) -> tuple:
        """(số thửa, số tờ, tổng DT thu hồi Decimal) theo các dòng đang có trên bảng (kể cả chưa lưu). Ô diện tích là công thức /
        chữ lạ: không cộng."""
        from .tien import D
        tong, to = D(0), set()
        n = self.bang.rowCount()
        for r in range(n):
            if self._chu(r, 'so_to'):
                to.add(self._chu(r, 'so_to'))
            v = self._so(r, 'dt_thu_hoi')
            if v is not None:
                tong += v
        return n, len(to), tong

    def tom_tat_dia_chinh(self) -> dict:
        """Tổng hợp địa chính hộ: số thửa, số tờ, tổng DT nguyên thửa / thu hồi / còn lại (Decimal; nguyên thửa / còn lại None khi chưa
        nhập DT nguyên thửa thửa nào). Một thửa tách nhiều dòng loại đất: DT nguyên thửa tính một lần (lớn nhất các dòng)."""
        from .tien import D
        n, so_to, tong_th = self.tom_tat_thua()
        nguyen, th_cua = {}, {}
        for r in range(self.bang.rowCount()):
            khoa = (self._chu(r, 'so_to'), self._chu(r, 'so_thua'))
            v = self._so(r, 'dt_nguyen_thua')
            if v is not None:
                nguyen[khoa] = max(nguyen.get(khoa, D(0)), v)
            th_cua[khoa] = th_cua.get(khoa, D(0)) + (self._so(r, 'dt_thu_hoi') or D(0))
        tong_ng = sum(nguyen.values(), D(0)) if nguyen else None
        con = sum((nguyen[k] - th_cua.get(k, D(0)) for k in nguyen), D(0)) if nguyen else None
        return dict(so_thua=n, so_to=so_to, dt_nguyen_thua=tong_ng, dt_thu_hoi=tong_th, dt_con_lai=con)

    def dt_theo_loai(self) -> dict:
        """{loại đất: tổng DT thu hồi Decimal} theo các dòng đang có (1.0.04 - dải tóm tắt chân bảng thửa)."""
        from .tien import D
        kq = {}
        for r in range(self.bang.rowCount()):
            ld = ' '.join(self._chu(r, 'loai_dat').split()).upper() or '(chưa ghi)'
            kq[ld] = kq.get(ld, D(0)) + (self._so(r, 'dt_thu_hoi') or D(0))
        return kq

    def co_cau_loai(self) -> list:
        """Thẻ cơ cấu loại đất: [(tên nhóm, DT thu hồi Decimal, số thửa, mã đầu)] - nhóm NHOM_THE_LOAI có thửa, rồi "Khác"."""
        from .tien import D
        nhom = {ten: [D(0), set(), ds[0]] for ten, ds in NHOM_THE_LOAI}
        khac = [D(0), set(), '']
        for r in range(self.bang.rowCount()):
            m = ma_dau(self._chu(r, 'loai_dat'))
            o = next((nhom[ten] for ten, ds in NHOM_THE_LOAI if m in ds), khac)
            o[0] += self._so(r, 'dt_thu_hoi') or D(0)
            o[1].add((self._chu(r, 'so_to'), self._chu(r, 'so_thua')))
        kq = [(ten, v[0], len(v[1]), v[2]) for ten, v in nhom.items() if v[1]]
        if khac[1]:
            kq.append(('Loại khác', khac[0], len(khac[1]), ''))
        return kq

    def _cap_nhat_o_tinh(self) -> None:
        """STT (1..n) và DT còn lại của từng dòng (= DT nguyên thửa - tổng DT thu hồi các dòng cùng tờ / thửa). Không phát
        itemChanged (không vào lịch sử Hoàn tác, không tính là thay đổi)."""
        from .tien import D
        th_cua = {}
        for r in range(self.bang.rowCount()):
            khoa = (self._chu(r, 'so_to'), self._chu(r, 'so_thua'))
            th_cua[khoa] = th_cua.get(khoa, D(0)) + (self._so(r, 'dt_thu_hoi') or D(0))
        c_stt, c_con = self.cot.index('stt'), self.cot.index('dt_con_lai')
        cu = self.bang.blockSignals(True)
        try:
            for r in range(self.bang.rowCount()):
                it = self.bang.item(r, c_stt)
                if it is not None and it.text() != str(r + 1):
                    it.setText(str(r + 1))
                it = self.bang.item(r, c_con)
                if it is None:
                    continue
                ng = self._so(r, 'dt_nguyen_thua')
                if ng is None:
                    chu, tip, mau = '', 'Nhập DT nguyên thửa để tính DT còn lại.', None
                else:
                    con = ng - th_cua[(self._chu(r, 'so_to'), self._chu(r, 'so_thua'))]
                    chu = so_vn(con)
                    tip = 'DT nguyên thửa - tổng DT thu hồi các dòng cùng tờ / thửa'
                    mau = QColor(MAU_CANH_BAO_CHU) if con < 0 else None       # 20/10/2026: cảnh báo = hổ phách (một màu)
                    if con < 0:
                        tip = 'DT thu hồi lớn hơn DT nguyên thửa - kiểm tra lại số liệu.'
                # chỉ đặt khi đổi: mỗi lần đặt phát dataChanged -> hẹn tính lại tóm tắt (đặt mãi thì vòng lặp khi rảnh)
                if it.text() != chu:
                    it.setText(chu)
                if it.toolTip() != tip:
                    it.setToolTip(tip)
                do = mau is not None
                if bool(it.data(Qt.ItemDataRole.UserRole + 1)) != do:
                    it.setData(Qt.ItemDataRole.UserRole + 1, do)
                    if do:
                        it.setForeground(mau)
                        it.setBackground(QColor(MAU_CANH_BAO_NEN))
                    else:
                        it.setData(Qt.ItemDataRole.ForegroundRole, None)
                        it.setData(Qt.ItemDataRole.BackgroundRole, None)
        finally:
            self.bang.blockSignals(cu)

    def cap_nhat_tom_tat_thua(self) -> None:
        self._cap_nhat_o_tinh()
        tt = self.tom_tat_dia_chinh()

        def m2(v):
            return '—' if v is None else f'{so_vn(v)} m²'
        self.lb_tieu_de_thua.setText(f'II. Thửa đất thu hồi & nguồn gốc ({tt["so_thua"]} thửa)')
        self.lb_tom_tat_thua.setText(
            f'<b>Tổng hợp địa chính hộ:</b> Tổng số thửa: <b>{tt["so_thua"]}</b> thửa  ·  Số tờ bản đồ: <b>{tt["so_to"]}</b> tờ  ·  '
            f'Tổng DT nguyên thửa: <b>{m2(tt["dt_nguyen_thua"])}</b>  ·  Tổng DT thu hồi: <b>{m2(tt["dt_thu_hoi"])}</b>  ·  '
            f'Tổng DT còn lại: <b>{m2(tt["dt_con_lai"])}</b>')
        loai = self.dt_theo_loai()
        self.lb_tom_tat_thua.setToolTip('Diện tích thu hồi theo loại đất:\n' + '\n'.join(f'{k}: {so_vn(v)} m²'
                                                                                          for k, v in sorted(loai.items()))
                                        if loai else '')
        for t in self.the_loai:                           # thẻ cơ cấu loại đất (dựng lại - vài thẻ)
            self.khoi_the_loai.removeWidget(t)
            t.deleteLater()
        self.the_loai = []
        for ten, dt, n, ma in self.co_cau_loai():
            t = QLabel(f'{ten}: {so_vn(dt)} m² ({n} thửa)')
            nen, mau = mau_loai_dat(ma) if ma else MAU_LOAI_KHAC
            t.setProperty('the_nho', 'loai')
            t.setStyleSheet(f'background: {nen}; color: {mau};')      # màu theo nhóm - nhãn lá, không phải khung chứa
            self.khoi_the_loai.addWidget(t)
            self.the_loai.append(t)

    def la_to_chuc(self) -> bool:
        w = self.o.get('ho_ten')
        return bool(w is not None and ho_so.la_to_chuc(w.text()))

    def cap_nhat_nhan_to_chuc(self) -> None:
        """Chủ sử dụng là tổ chức (1.0.04): "Họ và tên" -> "Tổ chức", "Địa chỉ thường trú" -> "Địa chỉ"; ẩn CCCD, ngày / nơi cấp,
        điện thoại (dữ liệu giữ nguyên khi lưu). Thẻ nhỏ "Loại đối tượng" đổi theo."""
        tc = self.la_to_chuc()
        for k, nhan in self.nhan_o.items():
            if k == 'ho_ten':
                nhan.setText(('Tổ chức' if tc else NHAN_HO['ho_ten']) + ':')
            elif k == 'dia_chi':
                nhan.setText(('Địa chỉ' if tc else NHAN_HO['dia_chi']) + ':')
            elif k in AN_KHI_TO_CHUC:
                nhan.setVisible(not tc)
        for k in AN_KHI_TO_CHUC:
            if k in self.o:
                self.o[k].setVisible(not tc)
        self.the_loai_doi_tuong.setText('Loại đối tượng: Tổ chức' if tc else 'Loại đối tượng: Hộ gia đình, cá nhân')
        self.the_loai_doi_tuong.setToolTip('Tên bắt đầu bằng loại tổ chức (UBND, Công ty, Trường…): nhãn đổi thành "Tổ chức", ẩn CCCD, '
                                           'ngày / nơi cấp, điện thoại; bản in ghi "Tổ chức:".')
        self.kiem_cccd()

    def kiem_cccd(self) -> str:
        """Kiểm số CCCD (12 số, không trùng hộ khác; 9 số = CMND cũ) -> thẻ nhỏ + viền ô. Trả mã: '' / 'du' / 'cmnd' / 'thieu' / 'trung'."""
        w = self.o.get('so_cccd')
        if w is None or self.la_to_chuc():
            self.the_cccd.setVisible(False)
            return ''
        so = ''.join(ch for ch in w.text() if not ch.isspace())
        self.the_cccd.setVisible(True)
        if not so:
            kq, chu, loai = '', 'Chưa có số CCCD', 'xam'
        elif not so.isdigit() or len(so) not in (9, 12):
            kq, chu, loai = 'thieu', f'CCCD chưa đủ 12 số ({len(so)} ký tự)', 'do'
        elif len(so) == 9:
            kq, chu, loai = 'cmnd', 'Số CMND cũ (9 số)', 'vang'
        else:
            trung = self.con.execute('SELECT ma_ho, ho_ten FROM ho WHERE so_cccd = ? AND ma_ho IS NOT ? LIMIT 1',
                                     (so, self.ma_ho)).fetchone()
            if trung:
                kq, chu, loai = 'trung', f'CCCD trùng hộ {trung["ho_ten"]}', 'do'
            else:
                kq, chu, loai = 'du', 'CCCD đủ 12 số - Không trùng', 'xanh'
        self.the_cccd.setText(chu)
        _dat_loai_the(self.the_cccd, loai)
        hop_le = '0' if kq in ('thieu', 'trung') else '1'
        if w.property('hop_le') != hop_le:
            w.setProperty('hop_le', hop_le)
            w.style().unpolish(w)
            w.style().polish(w)
        return kq

    def hoan_tac_phim(self, lam_lai: bool) -> bool:
        """Ô đang chọn trong bảng thửa: hoàn tác sửa ô; hết bước thì để cửa sổ cha xử lý."""
        if self._ht_bang is None or not self.bang.hasFocus():
            return False
        return self._ht_bang.lam_lai() if lam_lai else self._ht_bang.hoan_tac()

    def chinh_cao_dong(self):
        """Mọi dòng thửa cao CAO_DONG_THUA (nguồn gốc rút gọn hai dòng - xem / sửa đủ ở HopNguonGoc)."""
        for r in range(self.bang.rowCount()):
            if self.bang.rowHeight(r) != CAO_DONG_THUA:
                self.bang.setRowHeight(r, CAO_DONG_THUA)

    def _doi_o(self, it):
        k = self.cot[it.column()]
        if k == 'nguon_goc' or k == 'vi_tri':
            ng = self.bang.item(it.row(), self.cot.index('nguon_goc'))
            if ng is not None:
                vt = self._chu(it.row(), 'vi_tri')
                tip = ('Vị trí: ' + vt + '\n' if vt else '') + 'Nguồn gốc:\n' + ng.text()
                if ng.toolTip() != tip:
                    cu = self.bang.blockSignals(True)
                    ng.setToolTip(tip)
                    self.bang.blockSignals(cu)

    def vua_tieu_de(self) -> int:
        """Hàng tiêu đề cột đủ hai dòng chữ (TIEU_DE_HAI_DONG) theo cỡ chữ hiện tại (đổi khi Phóng to / Thu nhỏ). Trả chiều cao."""
        from PySide6.QtGui import QFontMetrics
        tieu = self.bang.horizontalHeader()
        f = QFont(tieu.font())
        f.setBold(True)
        cao = QFontMetrics(f).lineSpacing() * 2 + 14
        if tieu.minimumHeight() != cao:
            tieu.setMinimumHeight(cao)
        return cao

    def showEvent(self, e):
        self.vua_tieu_de()
        super().showEvent(e)

    def changeEvent(self, e):
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.vua_tieu_de()
        super().changeEvent(e)

    def eventFilter(self, o, e):
        """Enter ở ô "Nguồn gốc & Vị trí đất" (không đang sửa): mở hộp xem / sửa đủ."""
        if o is self.bang and e.type() == QEvent.Type.KeyPress and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and self.bang.state() != QAbstractItemView.State.EditingState \
                and self.bang.currentColumn() == self.cot.index('nguon_goc') and self.bang.currentRow() >= 0:
            self.sua_dong(self.bang.currentRow())
            return True
        return super().eventFilter(o, e)

    def sua_dong(self, r: int) -> bool:
        """Mở hộp xem / sửa đủ nguồn gốc & vị trí của dòng r (nút "Sửa", "[Xem/Sửa đủ ↗]", Enter)."""
        if not (0 <= r < self.bang.rowCount()):
            return False
        idx = self.bang.model().index(r, self.cot.index('nguon_goc'))
        return self._ng.mo_hop(self.bang.model(), idx, self.bang)

    def menu_bang(self, pos=None, hien: bool = True):
        """Menu chuột phải bảng thửa: sao chép ô / cả dòng thửa, mở hộp nguồn gốc, thêm / tách / xóa thửa."""
        from .giao_dien import them_muc_sao_chep
        menu = QMenu(self.bang)
        ds = them_muc_sao_chep(menu, self.bang, pos)
        if len(ds) > 1:
            ds[1].setText('Sao chép cả dòng thửa\tCtrl+Shift+C')
        r = self.bang.currentRow()
        sua = self.bang.editTriggers() != QAbstractItemView.EditTrigger.NoEditTriggers
        menu.addSeparator()
        a = menu.addAction('Mở hộp soạn Nguồn gốc & Vị trí đầy đủ…\tEnter')
        a.setEnabled(r >= 0 and sua)
        a.triggered.connect(lambda _=False, r=r: self.sua_dong(r))
        menu.addSeparator()
        for chu, ham, bat in (('+ Thêm thửa', lambda: self.them_dong(), sua), ('Tách theo loại đất', lambda: self.tach_dong(), sua and r >= 0),
                              ('Xóa thửa', lambda: self.xoa_dong(), sua and r >= 0)):
            a = menu.addAction(chu)
            a.setEnabled(bat)
            a.triggered.connect(ham)
        if hien and pos is not None:
            menu.exec(self.bang.viewport().mapToGlobal(pos))
            menu.deleteLater()
        return menu

    def them_dong(self, t=None, vi_tri=None):
        t = t or {}
        r = self.bang.rowCount() if vi_tri is None else vi_tri
        self.bang.insertRow(r)
        cu = self.bang.blockSignals(True)
        try:
            for c, k in enumerate(self.cot):
                v = t.get(k, '')
                chu = str(v if v is not None else '')
                if k in ('dt_thu_hoi', 'dt_nguyen_thua') and chu.strip():
                    try:
                        chu = so_vn(v)
                    except ValueError:
                        pass                                # công thức (=12,5*8): tính khi lưu
                elif k == 'stt':
                    chu = str(r + 1)
                it = QTableWidgetItem(chu)
                if k in COT_GIUA:
                    it.setTextAlignment(CAN_GIUA)
                elif k in COT_PHAI:
                    it.setTextAlignment(CAN_PHAI)
                if k in COT_KHONG_SUA:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if k == 'stt':
                    it.setData(Qt.ItemDataRole.UserRole, t.get('ma_thua'))
                    if t.get('so_dong_pa'):
                        it.setToolTip(f'{t["so_dong_pa"]} dòng bồi thường đất đang gắn với thửa này')
                elif k == 'vi_tri_gia':
                    it.setToolTip((chu + '\n' if chu else '') + 'Vị trí giá đất chọn ở thẻ "1. Đất" của phương án.')
                elif k == 'thao_tac':
                    it.setToolTip('Sửa: xem / sửa đủ nguồn gốc & vị trí · Thùng rác: xóa thửa')
                elif k in ('so_gcn', 'loai_dat') and chu:
                    it.setToolTip(chu)
                self.bang.setItem(r, c, it)
        finally:
            self.bang.blockSignals(cu)
        self._doi_o(self.bang.item(r, self.cot.index('nguon_goc')))
        self.bang.setRowHeight(r, CAO_DONG_THUA)
        if not t:
            self.bang.setCurrentCell(r, self.cot.index('so_to'))
        self._hen_tom_tat.start()
        return r

    def thu_thap(self):
        tt = {k: w.text() for k, w in self.o.items()}
        ds = []
        for r in range(self.bang.rowCount()):
            g = {k: self._chu_goc(r, k) for k, _ in ho_so.TRUONG_THUA}
            it = self.bang.item(r, self.cot.index('stt'))
            g['ma_thua'] = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
            ds.append(g)
        return tt, ds

    def _chu_goc(self, r: int, k: str) -> str:
        it = self.bang.item(r, self.cot.index(k))
        return it.text() if it is not None else ''

    def co_thay_doi(self) -> bool:
        return self.thu_thap() != self.ban_dau

    def _dong_chon(self, r):
        r = self.bang.currentRow() if r is None else r
        return r if 0 <= r < self.bang.rowCount() else None

    def _bao(self, chu: str):
        QMessageBox.warning(self, TEN_UD, chu)

    # ---------------------------------------------- thửa
    def tach_dong(self, r=None):
        """Thửa 'ONT+CLN' -> một dòng ONT (giữ diện tích) và một dòng CLN (diện tích 0) để chia lại."""
        r = self._dong_chon(r)
        if r is None:
            return 0
        ld = ho_so.chuan_loai_dat(self._chu(r, 'loai_dat'))
        phan = ld.split('+')
        if len(phan) < 2:
            QMessageBox.information(self, TEN_UD, 'Chọn một thửa có loại đất ghép (ví dụ ONT+CLN) để tách.')
            return 0
        self.bang.item(r, self.cot.index('loai_dat')).setText(phan[0])
        giu = {k: self._chu_goc(r, k) for k in ('so_to', 'so_thua', 'nguon_goc', 'vi_tri', 'dt_nguyen_thua', 'so_gcn')}
        for i, p in enumerate(phan[1:], start=1):
            self.them_dong(dict(giu, loai_dat=p, dt_thu_hoi='0'), vi_tri=r + i)
        self.lb.setText(f'Đã tách thành {len(phan)} dòng {", ".join(phan)}: chia lại diện tích thu hồi cho từng loại đất rồi Lưu.')
        if self._ht_bang is not None:
            self._ht_bang.ghi_nho()                     # thêm / bớt dòng: vị trí ô trong lịch sử không còn đúng
        return len(phan)

    def xoa_dong(self, r=None, xac_nhan=None):
        if r is None:                                   # 0.9.96: chọn nhiều thửa (Shift / Ctrl) -> xóa cả loạt
            # chọn từng ô (20/10/2026): mọi dòng có ô được chọn
            ds = sorted({i.row() for i in self.bang.selectionModel().selectedIndexes()}, reverse=True)
            if len(ds) > 1:
                co_pa = [self.bang.item(i, 0).toolTip() for i in ds if self.bang.item(i, 0) and self.bang.item(i, 0).toolTip()]
                if co_pa and xac_nhan is None:
                    xac_nhan = QMessageBox.question(self, TEN_UD, f'{len(co_pa)} / {len(ds)} thửa đã có dòng phương án. Xóa cả '
                                                    f'{len(ds)} thửa (các dòng đó còn lại, không gắn thửa)?') == QMessageBox.StandardButton.Yes
                if co_pa and not xac_nhan:
                    return False
                for i in ds:
                    self.bang.removeRow(i)
                if self._ht_bang is not None:
                    self._ht_bang.ghi_nho()
                return True
        r = self._dong_chon(r)
        if r is None:
            return False
        tip = self.bang.item(r, 0).toolTip() if self.bang.item(r, 0) else ''
        if tip and xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, f'Thửa này có {tip}. Xóa thửa (các dòng đó còn lại, không gắn thửa)?') \
                == QMessageBox.StandardButton.Yes
        if tip and not xac_nhan:
            return False
        self.bang.removeRow(r)
        if self._ht_bang is not None:
            self._ht_bang.ghi_nho()
        return True

    # ---------------------------------------------- lưu
    def luu(self) -> bool:
        tt, ds = self.thu_thap()
        try:
            self.ma_ho = ho_so.luu_ho(self.con, self.ma_ho, tt, ds)
        except LoiNhap as e:
            self._bao(str(e))
            return False
        self.canh_bao = ho_so.thua_trung_ho_khac(self.con, self.ma_ho)
        self._da_ghi()
        if self.canh_bao:
            self.lb.setText('Đã lưu. Lưu ý: ' + '; '.join(self.canh_bao))
        return True

    def _da_ghi(self):
        self.thay_doi_csdl = True
        self.nap()
        if self.khi_thay_doi_csdl:
            self.khi_thay_doi_csdl()

    def luu_truoc(self) -> bool:
        """Thao tác ghi thẳng CSDL (gộp, chuyển, xóa) cần lưu các sửa đổi trên màn hình trước."""
        return not self.co_thay_doi() or self.luu()

    # ---------------------------------------------- gộp / chuyển / xóa hộ
    def _chon_ho(self, tieu_de, nhan) -> int | None:
        ds = ho_so.goi_y_gop(self.con, self.ma_ho)
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Dự án không có hộ nào khác.')
            return None
        nhan_ds = [('★ ' if cung else '') + mt for _, mt, cung in ds]
        chon, ok = QInputDialog.getItem(self, tieu_de, nhan + '\n(★ = cùng họ tên)', nhan_ds, 0, False)
        return ds[nhan_ds.index(chon)][0] if ok else None

    def gop_ho(self, ma_ho_bo=None, xac_nhan=None) -> str | None:
        if self.ma_ho is None or not self.luu_truoc():
            return None
        if ma_ho_bo is None:
            ma_ho_bo = self._chon_ho('Gộp hộ', f'Chọn hộ sẽ gộp VÀO hộ {self.ma_ho} (hộ được chọn bị xóa sau khi gộp):')
            if ma_ho_bo is None:
                return None
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, f'Gộp hộ {ma_ho_bo} vào hộ {self.ma_ho}? Thửa và phương án của hộ '
                                            f'{ma_ho_bo} chuyển sang hộ {self.ma_ho}, hộ {ma_ho_bo} bị xóa.') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        try:
            tb = ho_so.gop_ho(self.con, self.ma_ho, ma_ho_bo)
        except LoiNhap as e:
            self._bao(str(e))
            return None
        self._da_ghi()
        self.lb.setText(tb)
        return tb

    def chuyen_thua(self, r=None, ma_ho_moi=None) -> str | None:
        r = self._dong_chon(r)
        if self.ma_ho is None or r is None:
            QMessageBox.information(self, TEN_UD, 'Chọn một thửa để chuyển.')
            return None
        if not self.luu_truoc():
            return None
        ma_thua = self.bang.item(r, 0).data(Qt.ItemDataRole.UserRole)
        if ma_ho_moi is None:
            ma_ho_moi = self._chon_ho('Chuyển thửa', f'Chuyển thửa {self._chu(r, "so_thua")} tờ {self._chu(r, "so_to")} '
                                                    'sang hộ:')
            if ma_ho_moi is None:
                return None
        try:
            tb = ho_so.chuyen_thua(self.con, ma_thua, ma_ho_moi)
        except LoiNhap as e:
            self._bao(str(e))
            return None
        self._da_ghi()
        self.lb.setText(tb)
        return tb

    def xoa_ho(self, xac_nhan=None) -> str | None:
        if self.ma_ho is None:
            return None
        if xac_nhan is None:
            ho = ho_so.doc_ho(self.con, self.ma_ho)
            xac_nhan = QMessageBox.warning(
                self, TEN_UD, f'XÓA hộ {self.ma_ho} - {ho["ho_ten"]} cùng {len(ho["thua"])} thửa và {ho["so_dong_pa"]} dòng phương án?\n'
                              'Xóa nhầm: bấm "Hoàn tác" (Ctrl+Z) ở cửa sổ chính để lấy lại.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        tb = ho_so.xoa_ho(self.con, self.ma_ho)
        self.thay_doi_csdl = True
        self.ban_dau = self.thu_thap()      # không hỏi lưu khi đóng
        self.lb.setText(tb)
        if self.khi_xoa_ho:
            self.khi_xoa_ho(tb)
        return tb


class HopHoSo(QDialog):
    """Hộp thoại hồ sơ hộ (thêm hộ mới hoặc sửa riêng hồ sơ). Thuộc tính / thao tác lấy từ KhungHoSo."""

    def __init__(self, con, ma_ho=None, parent=None):
        super().__init__(parent)
        self.resize(1000, 640)
        self.khung = KhungHoSo(con, ma_ho, self, khi_xoa_ho=lambda tb: QDialog.accept(self))
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Đóng')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addWidget(self.khung)
        lo.addWidget(nut)
        self._tieu_de()

    def __getattr__(self, ten):
        if ten == 'khung':
            raise AttributeError(ten)
        return getattr(self.khung, ten)

    def _tieu_de(self):
        k = self.khung
        self.setWindowTitle('Thêm hộ mới' if k.ma_ho is None else f'Hồ sơ hộ {k.ma_ho} - {k.ho_ten}')

    def nap(self):
        self.khung.nap()
        self._tieu_de()

    def luu(self) -> bool:
        ok = self.khung.luu()
        self._tieu_de()
        return ok

    def accept(self):
        if self.luu():
            super().accept()

    def reject(self):
        if self.khung.co_thay_doi():
            tl = QMessageBox.question(self, TEN_UD, 'Hồ sơ hộ có thay đổi chưa lưu. Lưu trước khi đóng?',
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                      QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
            if tl == QMessageBox.StandardButton.Cancel or (tl == QMessageBox.StandardButton.Save and not self.luu()):
                return
        super().reject()
