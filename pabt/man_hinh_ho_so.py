"""Hồ sơ hộ: thông tin hộ và danh sách thửa, thêm hộ, gộp hộ, chuyển thửa, xóa hộ.

KhungHoSo là khung nhúng được (thẻ đầu tiên của cửa sổ Lập phương án - hồ sơ và phương án trong một cửa sổ); HopHoSo là hộp
thoại riêng dùng khung này. Quy tắc nằm trong ho_so; các hàm thao tác nhận tham số tùy chọn để kiểm thử không cần bấm hộp thoại.
"""
from __future__ import annotations
from PySide6.QtCore import QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetricsF, QTextLayout, QTextOption
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QStyle,
                               QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import ho_so
from .lap_pa import LoiNhap
from .tien import so_vn

TEN_UD = 'PABT - Lập phương án bồi thường, hỗ trợ'
COT_AN = ('vi_tri',)                    # vị trí nhập ở mục 1 (Đất): cột ẩn, dữ liệu cũ vẫn giữ khi lưu
COT_GIUA = ('so_to', 'so_thua', 'loai_dat', 'dt_thu_hoi')
CAO_DONG_TOI_DA = 104                   # dòng thửa không cao quá mức này: nguồn gốc dài thì thu nhỏ chữ / cắt "…" (xem đủ ở tooltip)
CO_CHU_NHO_NHAT = 0.78                  # nguồn gốc dài: thu nhỏ chữ tới 78% cỡ chữ của bảng trước khi cắt


def _bo_tri_chu(chu: str, font: QFont, rong: float) -> tuple:
    """Ngắt dòng chữ theo bề rộng: [(QTextLayout, chiều cao)] và tổng chiều cao."""
    ds, tong = [], 0.0
    for doan in chu.split('\n'):
        tl = QTextLayout(doan, font)
        op = QTextOption()
        op.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        tl.setTextOption(op)
        tl.beginLayout()
        h = 0.0
        while True:
            dong = tl.createLine()
            if not dong.isValid():
                break
            dong.setLineWidth(rong)
            dong.setPosition(QRectF(0, h, 0, 0).topLeft())
            h += dong.height()
        tl.endLayout()
        ds.append((tl, h))
        tong += h
    return ds, tong


class ONguonGoc(QStyledItemDelegate):
    """Ô nguồn gốc đất: sửa trong khung nhiều dòng rộng (Enter ghi, Shift+Enter xuống dòng). Chữ dài hơn chiều cao dòng
    thì tự thu nhỏ chữ cho vừa; vẫn không vừa thì cắt bớt, cuối ô hiện "…" (xem đủ nội dung ở tooltip hoặc khi sửa)."""

    LE = 4

    def createEditor(self, parent, option, index):
        o = QPlainTextEdit(parent)
        o.setTabChangesFocus(True)
        o.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        o.installEventFilter(self)
        return o

    def setEditorData(self, o, index):
        o.setPlainText(str(index.data() or ''))
        o.moveCursor(o.textCursor().MoveOperation.End)

    def setModelData(self, o, model, index):
        dong = [' '.join(x.split()) for x in o.toPlainText().split('\n')]
        model.setData(index, '\n'.join(x for x in dong if x))

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
        op = QStyleOptionViewItem(option)
        self.initStyleOption(op, index)
        chu = op.text
        op.text = ''
        w = op.widget
        st = w.style() if w is not None else None
        if st is None:
            return super().paint(p, option, index)
        st.drawControl(QStyle.ControlElement.CE_ItemViewItem, op, p, w)
        if not chu:
            return
        vung = QRectF(op.rect).adjusted(self.LE + 2, self.LE, -self.LE - 2, -self.LE)
        font = QFont(op.font)
        goc = font.pointSizeF() if font.pointSizeF() > 0 else 9.5
        co = goc
        while True:
            font.setPointSizeF(co)
            ds, tong = _bo_tri_chu(chu, font, vung.width())
            if tong <= vung.height() or co <= goc * CO_CHU_NHO_NHAT:
                break
            co = max(goc * CO_CHU_NHO_NHAT, co - 0.5)
        p.save()
        p.setFont(font)
        mau = op.palette.highlightedText() if op.state & QStyle.StateFlag.State_Selected else op.palette.text()
        p.setPen(mau.color())
        y = vung.top() + max(0.0, (vung.height() - tong) / 2)       # canh giữa theo chiều dọc
        fm = QFontMetricsF(font)
        het = False
        for tl, h in ds:
            for i in range(tl.lineCount()):
                dong = tl.lineAt(i)
                if y + dong.height() * 2 > vung.bottom() + 0.5 and tong > vung.height():
                    # dòng cuối còn chỗ: in phần còn lại rút gọn bằng "…"
                    con = tl.text()[dong.textStart():]
                    p.drawText(QRectF(vung.left(), y, vung.width(), dong.height()), Qt.AlignmentFlag.AlignLeft,
                               fm.elidedText(' '.join(con.split()), Qt.TextElideMode.ElideRight, vung.width()))
                    het = True
                    break
                dong.draw(p, QRectF(vung.left(), y - dong.y(), 0, 0).topLeft())   # draw() cộng sẵn vị trí dòng
                y += dong.height()
            if het:
                break
        p.restore()

    def sizeHint(self, option, index):
        kq = super().sizeHint(option, index)
        chu = str(index.data() or '')
        w = option.widget
        rong = w.columnWidth(index.column()) if w is not None and hasattr(w, 'columnWidth') else option.rect.width()
        if chu and rong > 2 * (self.LE + 2):
            _, tong = _bo_tri_chu(chu, QFont(option.font), rong - 2 * (self.LE + 2))
            kq.setHeight(int(tong + 2 * self.LE + 2))
        return kq


class KhungHoSo(QWidget):
    """Thông tin hộ + bảng thửa + các thao tác gộp / chuyển / xóa. an: các trường thông tin hộ không hiện (giữ nguyên khi lưu).
    Gọi lại: khi_thay_doi_csdl() sau khi ghi CSDL (lưu, gộp, chuyển); khi_xoa_ho(thông báo) sau khi xóa hộ."""

    def __init__(self, con, ma_ho=None, parent=None, an=(), khi_thay_doi_csdl=None, khi_xoa_ho=None):
        super().__init__(parent)
        self.con = con
        self.ma_ho = ma_ho
        self.thay_doi_csdl = False          # đã gộp / chuyển / xóa (cửa sổ chính cần tải lại)
        self.canh_bao = []
        self.khi_thay_doi_csdl, self.khi_xoa_ho = khi_thay_doi_csdl, khi_xoa_ho
        self.o = {}
        luoi = QGridLayout()
        luoi.setHorizontalSpacing(10)
        luoi.setVerticalSpacing(8)
        rong = ('dia_chi', 'ghi_chu')                    # ô rộng: hết dòng, xếp sau các ô hẹp (2 ô một dòng)
        ds_truong = [x for x in ho_so.TRUONG_HO if x[0] not in an]
        for i, (k, ten) in enumerate([x for x in ds_truong if x[0] not in rong] + [x for x in ds_truong if x[0] in rong]):
            w = QLineEdit()
            self.o[k] = w
            hang, cot = (100 + i, 0) if k in rong else divmod(i, 2)
            nhan = QLabel(ten + ':')
            nhan.setProperty('vai', 'nhan')
            luoi.addWidget(nhan, hang, cot * 2)
            luoi.addWidget(w, hang, cot * 2 + 1, 1, 3 if k in rong else 1)
        self.bang = QTableWidget(0, len(ho_so.TRUONG_THUA))
        self.bang.setHorizontalHeaderLabels([t for _, t in ho_so.TRUONG_THUA])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setAlternatingRowColors(True)
        self.bang.setWordWrap(True)
        self.bang.setMinimumHeight(170)
        cot = [k for k, _ in ho_so.TRUONG_THUA]
        self.cot = cot
        for k, w in (('so_to', 70), ('so_thua', 80), ('loai_dat', 120), ('dt_thu_hoi', 130)):
            self.bang.setColumnWidth(cot.index(k), w)
        tieu = self.bang.horizontalHeader()
        tieu.setStretchLastSection(False)
        tieu.setSectionResizeMode(cot.index('nguon_goc'), QHeaderView.ResizeMode.Stretch)   # nguồn gốc: hết bề rộng còn lại
        for k in COT_AN:
            self.bang.setColumnHidden(cot.index(k), True)
        from .giao_dien import ChonXoXuong, nhap_bang_phim
        from .loai_dat import ds_chon
        # loại đất: danh mục theo Luật Đất đai 2024, ký hiệu TT 08/2024 (gõ tay được loại ghép, vd ONT+CLN)
        self._ld = ChonXoXuong(ds_chon(con), self.bang)
        self.bang.setItemDelegateForColumn(cot.index('loai_dat'), self._ld)
        self._ng = ONguonGoc(self.bang)
        self.bang.setItemDelegateForColumn(cot.index('nguon_goc'), self._ng)
        nhap_bang_phim(self.bang)
        self.bang.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.bang.itemChanged.connect(self._doi_o)
        self._hen_cao = QTimer(self)
        self._hen_cao.setSingleShot(True)
        self._hen_cao.setInterval(60)
        self._hen_cao.timeout.connect(self.chinh_cao_dong)
        tieu.sectionResized.connect(lambda *_: self._hen_cao.start())
        for w in self.o.values():                   # Enter ở ô thông tin hộ: sang ô kế tiếp
            w.returnPressed.connect(self.focusNextChild)
        # thao tác thửa / hộ: một nút "+ Thêm thửa" và menu "Thao tác khác" cạnh tiêu đề bảng (không chiếm một hàng nút riêng)
        self.nut = {}
        b_them = QPushButton('+ Thêm thửa')
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
        self.b_thao_tac = QPushButton('Thao tác khác')
        self.b_thao_tac.setMenu(menu)
        self.b_thao_tac.setToolTip('Tách thửa theo loại đất, xóa thửa, chuyển thửa sang hộ khác, gộp hộ, xóa hộ')
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.setSpacing(8)
        lo.addLayout(luoi)
        hang_td = QHBoxLayout()
        hang_td.setSpacing(8)
        tieu_de = QLabel('CÁC THỬA ĐẤT THU HỒI')
        tieu_de.setProperty('vai', 'tieu_de')
        hang_td.addWidget(tieu_de)
        hang_td.addWidget(self.lb, 1)
        hang_td.addWidget(b_them)
        hang_td.addWidget(self.b_thao_tac)
        lo.addLayout(hang_td)
        lo.addWidget(self.bang, 1)
        from .giao_dien import BangHoanTac
        self._ht_bang = None
        self.nap()
        self._ht_bang = BangHoanTac(self.bang)                  # Ctrl+Z / Ctrl+Y: sửa ô trong bảng thửa

    # ---------------------------------------------- nạp / thu thập
    def nap(self, ma_ho=None):
        if ma_ho is not None:
            self.ma_ho = ma_ho
        if self.ma_ho is None:
            ho = {k: '' for k, _ in ho_so.TRUONG_HO}
            ho.update(thua=[], so_dong_pa=0)
        else:
            ho = ho_so.doc_ho(self.con, self.ma_ho)
        self.ho_ten = ho['ho_ten']
        for k, w in self.o.items():
            w.setText(str(ho.get(k) or ''))
            w.setCursorPosition(0)
        self.bang.setRowCount(0)
        for t in ho['thua']:
            self.them_dong(t)
        for ten in ('Chuyển thửa sang hộ khác…', 'Gộp hộ khác vào hộ này…', 'Xóa hộ…'):    # QAction trong menu
            self.nut[ten].setEnabled(self.ma_ho is not None)
        self.lb.setText(f'Hộ đã có {ho["so_dong_pa"]} dòng phương án. ' if ho['so_dong_pa'] else '')
        self.chinh_cao_dong()
        self.ban_dau = self.thu_thap()
        if getattr(self, '_ht_bang', None) is not None:
            self._ht_bang.ghi_nho()

    def hoan_tac_phim(self, lam_lai: bool) -> bool:
        """Ô đang chọn trong bảng thửa: hoàn tác sửa ô; hết bước thì để cửa sổ cha xử lý."""
        if self._ht_bang is None or not self.bang.hasFocus():
            return False
        return self._ht_bang.lam_lai() if lam_lai else self._ht_bang.hoan_tac()

    def chinh_cao_dong(self):
        """Dòng thửa cao vừa nội dung nhưng không quá CAO_DONG_TOI_DA (nguồn gốc dài: ô tự thu nhỏ chữ / cắt "…"),
        để số tờ, số thửa, loại đất, diện tích luôn thấy ở giữa dòng."""
        vh = self.bang.verticalHeader()
        thap = vh.minimumSectionSize()
        for r in range(self.bang.rowCount()):
            self.bang.resizeRowToContents(r)
            self.bang.setRowHeight(r, max(thap, min(CAO_DONG_TOI_DA, self.bang.rowHeight(r))))

    def _doi_o(self, it):
        if it.column() == self.cot.index('nguon_goc'):
            if it.toolTip() != it.text():
                it.setToolTip(it.text())
            self._hen_cao.start()

    def them_dong(self, t=None, vi_tri=None):
        t = t or {}
        r = self.bang.rowCount() if vi_tri is None else vi_tri
        self.bang.insertRow(r)
        for c, (k, _) in enumerate(ho_so.TRUONG_THUA):
            v = t.get(k, '')
            chu = str(v if v is not None else '')
            if k == 'dt_thu_hoi' and chu.strip():
                try:
                    chu = so_vn(v)
                except ValueError:
                    pass                                # công thức (=12,5*8): tính khi lưu
            it = QTableWidgetItem(chu)
            if k in COT_GIUA:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if c == 0:
                it.setData(Qt.ItemDataRole.UserRole, t.get('ma_thua'))
                if t.get('so_dong_pa'):
                    it.setToolTip(f'{t["so_dong_pa"]} dòng bồi thường đất đang gắn với thửa này')
            elif k in ('nguon_goc', 'vi_tri'):
                it.setToolTip(str(v or ''))
            self.bang.setItem(r, c, it)
        if not t:
            self.bang.setCurrentCell(r, 0)
        self._hen_cao.start()
        return r

    def thu_thap(self):
        tt = {k: w.text() for k, w in self.o.items()}
        ds = []
        for r in range(self.bang.rowCount()):
            g = {k: (self.bang.item(r, c).text() if self.bang.item(r, c) else '') for c, (k, _) in enumerate(ho_so.TRUONG_THUA)}
            g['ma_thua'] = self.bang.item(r, 0).data(Qt.ItemDataRole.UserRole) if self.bang.item(r, 0) else None
            ds.append(g)
        return tt, ds

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
        ld = ho_so.chuan_loai_dat(self.bang.item(r, 2).text() if self.bang.item(r, 2) else '')
        phan = ld.split('+')
        if len(phan) < 2:
            QMessageBox.information(self, TEN_UD, 'Chọn một thửa có loại đất ghép (ví dụ ONT+CLN) để tách.')
            return 0
        self.bang.item(r, 2).setText(phan[0])
        for i, p in enumerate(phan[1:], start=1):
            self.them_dong(dict(so_to=self.bang.item(r, 0).text(), so_thua=self.bang.item(r, 1).text(), loai_dat=p,
                                dt_thu_hoi='0', nguon_goc=self.bang.item(r, 4).text() if self.bang.item(r, 4) else '',
                                vi_tri=self.bang.item(r, 5).text() if self.bang.item(r, 5) else ''), vi_tri=r + i)
        self.lb.setText(f'Đã tách thành {len(phan)} dòng {", ".join(phan)}: chia lại diện tích thu hồi cho từng loại đất rồi Lưu.')
        if self._ht_bang is not None:
            self._ht_bang.ghi_nho()                     # thêm / bớt dòng: vị trí ô trong lịch sử không còn đúng
        return len(phan)

    def xoa_dong(self, r=None, xac_nhan=None):
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
            ma_ho_moi = self._chon_ho('Chuyển thửa', f'Chuyển thửa {self.bang.item(r, 1).text()} tờ {self.bang.item(r, 0).text()} '
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
                              'Không hoàn tác được.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
