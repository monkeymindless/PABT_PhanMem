"""Quản lý bộ quy tắc giá đất (1.0.64): xem các gói, tạo gói mới khi có văn bản mới, sửa hệ số / yếu tố / công thức / câu giải trình trên bảng, xem khác gì gói gốc rồi mới lưu. Logic ở goi_gia_dat.py."""
from __future__ import annotations

import copy
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)
from PySide6.QtWidgets import QFrame, QGridLayout, QScrollArea

from . import goi_gia_dat as gg

TIEU_DE = 'LARC - Bộ quy tắc giá đất'
COT_YT = ('Mã', 'Yếu tố ảnh hưởng', 'Hệ số', 'Áp cho', 'Mặt đường', 'Khóa', 'Căn cứ')
CHU_COT_YT = ('Mã không dấu, không trùng', 'Tên hiện ở bảng tính', '', 'nn: đất nông nghiệp; pnn: đất phi nông nghiệp; ca: cả hai', 'Tự áp khi chọn mặt đường có mã này', 'Ghi "có": tuyến đã có quy định riêng thì không nhân (chống nhân trùng)', '')
COT_THEM = ('Mã (K4…)', 'Tên hệ số', 'Mặc định', 'Căn cứ')
SUA_BANG = QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.AnyKeyPressed


def _o(x) -> QTableWidgetItem:
    return QTableWidgetItem('' if x is None else str(x))


class _CuonThan(QScrollArea):
    """Vùng cuộn chỉ cuộn dọc cho thân thẻ Bộ quy tắc (1.1.06): rộng = nội dung (không cuộn ngang), cao tối thiểu nhỏ - màn thấp thì
    cuộn dọc, màn đủ cao thì nội dung giãn hết (widgetResizable)."""
    CAO_TOI_THIEU = 260

    def __init__(self):
        super().__init__()
        # 1.1.07: TỰ đặt cỡ nội dung (không widgetResizable): Qt đặt nội dung cao theo heightForWidth (cỡ ƯA THÍCH của nhãn xuống dòng
        # - 729 px) thay vì cỡ tối thiểu (560 px) -> màn 1536 x 864 vẫn phải cuộn mới thấy cụm "Gói cài và trao đổi"
        self.setWidgetResizable(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def setWidget(self, w) -> None:
        super().setWidget(w)
        w.installEventFilter(self)
        self._vua()

    def _vua(self) -> None:
        w = self.widget()
        if w is None:
            return
        vp = self.viewport().size()
        cao = max(vp.height(), w.minimumSizeHint().height())
        rong = vp.width()
        if cao > vp.height():                           # sắp hiện thanh cuộn dọc: chừa bề rộng của nó
            rong = max(w.minimumSizeHint().width(), self.width() - self.verticalScrollBar().sizeHint().width())
        if (w.width(), w.height()) != (rong, cao):
            w.resize(rong, cao)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._vua()

    def _rong(self) -> int:
        w = self.widget()
        return (w.minimumSizeHint().width() if w is not None else 0) + self.verticalScrollBar().sizeHint().width()

    def minimumSizeHint(self):
        s = super().minimumSizeHint()
        s.setWidth(self._rong())
        s.setHeight(self.CAO_TOI_THIEU)
        return s

    def sizeHint(self):
        w = self.widget()
        s = super().sizeHint()
        if w is not None:
            s.setWidth(max(self._rong(), w.sizeHint().width()))
            s.setHeight(w.sizeHint().height())
        return s

    def eventFilter(self, o, e):
        from PySide6.QtCore import QEvent
        if o is self.widget() and e.type() == QEvent.Type.LayoutRequest:      # nội dung đổi: bố cục ngoài đọc lại bề rộng
            self.updateGeometry()
            self._vua()
        return super().eventFilter(o, e)


def _tao_hop_nhap_goi_cai(cha, xem: dict, ten_file: str = '', co_sua: bool = False):
    """1.1.06 - hộp nhập gói cài (.larcgia): bảng từng xã (trong gói / đang có trên máy, sẽ thêm / thay), tích chọn xã, Chọn tất cả,
    Bỏ chọn; chọn cách ghi: Bổ sung (mặc định - xã chưa có thêm mới, xã trùng thay sạch, xã khác giữ) hoặc Thay toàn bộ.
    co_sua (1.1.07, đợt D - chỉ ở thẻ gộp có khung đọc văn bản): lựa chọn thứ ba "Mở để sửa và kiểm định trước khi lưu"."""
    from PySide6.QtWidgets import QButtonGroup, QRadioButton
    from .man_hinh_chon_dia_ban import HopChonDiaBan, _so

    tk = gg.thong_ke_goi_cai(xem)

    class HopNhapGoiCai(HopChonDiaBan):
        def __init__(self):
            super().__init__(cha, [(x['ten'], x['so_gia'] + x['so_k']) for x in tk], lambda x: True, None, 'giá đất và hệ số K')
            self.setWindowTitle('Nhập gói cài đơn giá đất và hệ số K' + (f' - {ten_file}' if ten_file else ''))
            self.resize(720, 600)
            mo = xem['mo_ta']
            self.lb.setText(f'Gói có {len(tk)} xã / phường: {_so(mo.get("so_gia", 0))} dòng đơn giá đất, {_so(mo.get("so_k", 0))} dòng hệ số K'
                            + (f', bộ quy tắc "{mo.get("goi_ten")}"' if mo.get('goi_ten') else '') +
                            '. Tích các xã cần cài; xã không tích giữ nguyên số liệu đang có trên máy.')
            self.bang.setHorizontalHeaderLabels(['Chọn', 'Xã / phường', 'Trong gói: giá / K', 'Trên máy: giá / K  ->  sẽ'])
            for r, x in enumerate(tk):
                self.bang.item(r, 2).setText(f'{_so(x["so_gia"])} / {_so(x["so_k"])} dòng')
                co = x['gia_may'] or x['k_may']
                self.bang.item(r, 3).setText((f'{_so(x["gia_may"])} / {_so(x["k_may"])} dòng -> thay sạch' if co else 'chưa có -> thêm mới'))
            self.r_bo_sung = QRadioButton('Bổ sung (khuyên dùng)')
            self.r_thay = QRadioButton('Thay toàn bộ')
            mo_ta = ((self.r_bo_sung, 'Xã chưa có thì thêm; xã trùng tên thì xóa sạch số cũ của xã đó rồi ghi số trong gói; các xã '
                                      'khác trên máy giữ nguyên.'),
                     (self.r_thay, 'Bảng giá đất và hệ số K của máy CHỈ còn các xã đã chọn: mọi xã khác, kể cả 4 địa bàn gắn sẵn, bị bỏ '
                                   '(lấy lại bằng "Dùng lại bảng gắn sẵn").'))
            self.r_sua = None
            if co_sua:
                self.r_sua = QRadioButton('Mở để sửa và kiểm định trước khi lưu')
                mo_ta += ((self.r_sua, 'Chưa ghi gì: đơn giá đất của các xã đã chọn hiện ở thẻ con "Đọc văn bản" (tô đỏ / vàng dòng cần '
                                       'đối chiếu), hệ số K hiện ở thẻ Hệ số K, bộ quy tắc thành gói nháp. Sửa xong bấm lần lượt "Ghi '
                                       'vào bảng giá đất", "Lưu" (hệ số K), "Lưu gói".'),)
            self.nhom = QButtonGroup(self)
            khung = QGroupBox('Cách ghi')
            v = QVBoxLayout(khung)
            for b, chu in mo_ta:
                self.nhom.addButton(b)
                b.setToolTip(chu)
                lb = QLabel(chu)
                lb.setWordWrap(True)
                lb.setContentsMargins(22, 0, 0, 4)
                v.addWidget(b)
                v.addWidget(lb)
            self.r_bo_sung.setChecked(True)
            lo = self.layout()
            lo.insertWidget(lo.count() - 1, khung)
            self.b_ok.setText('Cài các xã đã chọn')

            self.nhom.buttonToggled.connect(lambda *_: self.b_ok.setText(
                'Mở để sửa' if self.che_do == 'sua' else 'Cài các xã đã chọn'))

        @property
        def bo_sung(self) -> bool:
            return not self.r_thay.isChecked()

        @property
        def che_do(self) -> str:
            """'bo_sung' | 'thay' | 'sua' (1.1.07)."""
            if self.r_sua is not None and self.r_sua.isChecked():
                return 'sua'
            return 'thay' if self.r_thay.isChecked() else 'bo_sung'

    return HopNhapGoiCai()


class HopChonXaGoiCai(QDialog):
    """Chọn xã / phường để đóng gói cài: đơn giá đất và hệ số K luôn đi cùng; bộ quy tắc kèm theo."""
    im_lang = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Chọn xã / phường đóng gói cài giá đất')
        self.resize(720, 520)
        self.chon = []
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel('Mỗi địa bàn trong gói cài gồm đủ đơn giá đất và hệ số K. Bộ quy tắc giá đất đi kèm gói.'))
        hang = QHBoxLayout()
        self.b_het = QPushButton('Chọn tất cả đủ cặp')
        self.b_bo = QPushButton('Bỏ chọn')
        hang.addWidget(self.b_het)
        hang.addWidget(self.b_bo)
        hang.addStretch(1)
        lo.addLayout(hang)
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(['Chọn', 'Địa bàn', 'Dòng đơn giá', 'Dòng hệ số K'])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lo.addWidget(self.bang, 1)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        lo.addWidget(self.lb)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Xuất gói cài…')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.b_het.clicked.connect(self._chon_het)
        self.b_bo.clicked.connect(self._bo_het)
        self._nap()

    def _nap(self) -> None:
        self._ds = gg.ds_xa_cho_goi_cai()
        self.bang.setRowCount(len(self._ds))
        du = thieu = 0
        for i, x in enumerate(self._ds):
            ck = QTableWidgetItem()
            ck.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled if x['du']
                        else Qt.ItemFlag.ItemIsUserCheckable)
            ck.setCheckState(Qt.CheckState.Unchecked)
            if not x['du']:
                ck.setFlags(Qt.ItemFlag.NoItemFlags)
            self.bang.setItem(i, 0, ck)
            self.bang.setItem(i, 1, _o(x['ten'] + ('' if x['du'] else ' (thiếu một bên)')))
            self.bang.setItem(i, 2, _o(x['so_gia']))
            self.bang.setItem(i, 3, _o(x['so_k']))
            du += 1 if x['du'] else 0
            thieu += 0 if x['du'] else 1
        self.lb.setText(f'{du} địa bàn đủ cặp đơn giá + hệ số K; {thieu} địa bàn thiếu một bên (không chọn được).')

    def _chon_het(self) -> None:
        for i, x in enumerate(self._ds):
            if x['du']:
                self.bang.item(i, 0).setCheckState(Qt.CheckState.Checked)

    def _bo_het(self) -> None:
        for i in range(self.bang.rowCount()):
            it = self.bang.item(i, 0)
            if it is not None and it.flags() & Qt.ItemFlag.ItemIsEnabled:
                it.setCheckState(Qt.CheckState.Unchecked)

    def accept(self) -> None:
        self.chon = [self._ds[i]['ten'] for i in range(self.bang.rowCount())
                     if self.bang.item(i, 0) and self.bang.item(i, 0).checkState() == Qt.CheckState.Checked]
        if not self.chon:
            if not self.im_lang:
                QMessageBox.warning(self, TIEU_DE, 'Chọn ít nhất một xã / phường đủ cặp đơn giá đất và hệ số K.')
            return
        super().accept()


class HopGoiGiaDat(QDialog):
    """Trái: danh sách gói. Phải: nội dung gói đang chọn (gói gắn sẵn chỉ xem). self.da_doi: có lưu / xóa gói. im_lang: kiểm thử."""
    im_lang = False

    RONG_TRAI = 330

    def __init__(self, parent=None, ma_chon: str = '', nhung: bool = False, khung_cn=None, khung_k=None, mo_the_k=None):
        """khung_cn (1.1.06, thẻ gộp "Bộ quy tắc & cập nhật giá đất" của cửa sổ Bảng giá đất): KhungCapNhatGiaDat đặt làm thẻ con "Đọc
        văn bản, quy tắc vị trí" + lệnh bảng giá / quy tắc vị trí ở cột trái; đọc văn bản xong tự tạo GÓI NHÁP (chưa lưu). khung_k +
        mo_the_k(): lệnh hệ số K ở cột trái chạy trên thẻ Hệ số K (mở thẻ đó để xem, sửa, Lưu)."""
        super().__init__(parent)
        self._nhung = nhung
        if nhung:
            self.setWindowFlags(Qt.WindowType.Widget)
        self.setWindowTitle(TIEU_DE)
        self.resize(1240, 680)
        self.g = None
        self._luc_nap = None
        self.goc = None
        self.moi = False
        self.da_doi = False
        self._ds = []
        self._nhap = None                               # 1.1.06: gói nháp từ văn bản vừa đọc (dòng đầu danh sách, chưa lưu)
        self.khung_cn, self.khung_k, self._mo_the_k = khung_cn, khung_k, mo_the_k
        lo = QVBoxLayout(self)
        # 1.1.06: thân (cột trái + khung phải) trong vùng CUỘN DỌC - màn 1366 x 768 @125% (1093 x 614) thấp hơn chiều cao tối thiểu của
        # ba cụm nút + bảng (trước đó thẻ Bộ quy tắc đã cần 559 px, cửa sổ 650 px: bị ép, chồng chữ)
        than_w = QWidget()
        than = QHBoxLayout(than_w)
        than.setContentsMargins(0, 0, 0, 0)
        self.cuon = _CuonThan()
        self.cuon.setWidget(than_w)
        lo.addWidget(self.cuon, 1)

        # ---- trái: 3 cụm (1.1.06): gói văn bản & hiệu lực | quy tắc & bảng dữ liệu | gói cài & trao đổi
        trai = QVBoxLayout()
        self.ds = QTableWidget(0, 2)
        self.ds.setHorizontalHeaderLabels(['Gói (văn bản)', 'Hiệu lực từ'])
        self.ds.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ds.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ds.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ds.verticalHeader().setVisible(False)
        self.ds.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ds.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.ds.currentCellChanged.connect(lambda r, *_: self._chon_dong(r))

        def nut(ten, chu, tip, ham):
            b = QPushButton(chu)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, h=ham: h())
            setattr(self, ten, b)
            return b

        def luoi(ds):
            w = QWidget()
            g = QGridLayout(w)
            g.setContentsMargins(0, 0, 0, 0)
            g.setSpacing(6)
            for i, b in enumerate(ds):
                if b is not None:
                    g.addWidget(b, i // 2, i % 2)
            return w
        # cụm 1: gói văn bản & hiệu lực
        c1 = QGroupBox('Gói văn bản và hiệu lực')
        v = QVBoxLayout(c1)
        if khung_cn is not None:
            v.addWidget(nut('b_doc', 'Đọc thêm văn bản…', 'Đọc / scan văn bản giá đất (Excel, Word, PDF, ảnh): chọn xã cần dùng, '
                            'xem bảng, rồi phần mềm tạo sẵn một GÓI NHÁP theo số hiệu và ngày hiệu lực đọc được (lưu mới có hiệu lực)',
                            lambda: self.doc_them_van_ban()))
        v.addWidget(self.ds, 1)
        v.addWidget(luoi([nut('b_chep', 'Tạo gói từ gói này…', 'Văn bản mới chỉ đổi một phần: chép gói đang chọn rồi sửa',
                              lambda: self.tao_tu_goi()),
                          nut('b_tu_k', 'Tạo gói từ hệ số K…', 'Đoạn đường và K1 lấy từ thẻ Hệ số K (đã đọc từ văn bản), kể cả xã mới; '
                              'K3, công thức chép từ gói đang chọn', lambda: self.tao_tu_he_so_k())]))
        trai.addWidget(c1, 1)
        # cụm 2: quy tắc vị trí & bảng dữ liệu dùng chung của máy (chỉ khi là thẻ gộp có khung đọc văn bản)
        if khung_cn is not None:
            c2 = QGroupBox('Quy tắc vị trí và bảng dữ liệu của máy')
            v = QVBoxLayout(c2)
            v.addWidget(luoi([
                nut('b_them_qt', '+ Quy tắc vị trí', 'Thêm quy tắc vị trí 2-4 (tỷ lệ so vị trí 1) cho bảng giá vừa đọc - thẻ con Đọc văn bản',
                    lambda: self._lam_tren_cn(khung_cn.them_quy_tac)),
                nut('b_xoa_qt', 'Xóa quy tắc vị trí', 'Xóa quy tắc vị trí đang chọn ở bảng Quy tắc vị trí (thẻ con Đọc văn bản)',
                    lambda: self._lam_tren_cn(khung_cn.xoa_quy_tac)),
                nut('b_thay_gia', 'Thay cả bảng giá…', 'Xóa toàn bộ bảng giá đất đang dùng (mọi xã) rồi ghi đúng bảng vừa đọc - '
                    'không giữ xã cũ, không ghép trùng giá. Cần đọc văn bản trước', lambda: self._lam_tren_cn(lambda: khung_cn.ghi(thay=True))),
                nut('b_gia_gan_san', 'Bảng giá gắn sẵn', 'Bỏ mọi bảng giá đã thay / bổ sung trên máy, trở lại bốn địa bàn gắn sẵn',
                    lambda: khung_cn.khoi_phuc()),
                nut('b_doc_k', 'Đọc hệ số K…', 'Đọc / scan văn bản hệ số K (Phụ lục QĐ 03…): chọn xã, kiểm tra ở thẻ Hệ số K rồi Lưu',
                    lambda: self._lam_tren_k(lambda k: k.chon_file())),
                nut('b_k_gan_san', 'Hệ số K gắn sẵn', 'Bỏ bảng hệ số K đã nhập trên máy, dùng lại bảng gắn sẵn của QĐ 03/2026',
                    lambda: self._lam_tren_k(lambda k: k.bo_het()))]))
            for b in (self.b_xoa_qt, self.b_gia_gan_san, self.b_k_gan_san):
                b.setProperty('nhom_xoa', True)
            trai.addWidget(c2)
            khung_cn.an_lenh_trung()
            if khung_k is not None:
                khung_k.an_lenh_trung()
        # cụm 3: gói cài & trao đổi
        c3 = QGroupBox('Gói cài và trao đổi')
        v = QVBoxLayout(c3)
        # 1.1.07: lưới 2 cột (chữ ngắn, ý đầy đủ ở chú thích) - cụm thấp hơn, màn 1366 x 768 @125% thấy ngay
        v.addWidget(luoi([nut('b_xuat_cai', 'Tạo gói cài…', 'Tạo gói cài đơn giá đất + hệ số K (.larcgia): chọn xã / phường, đóng kèm '
                              'đơn giá đất + hệ số K (luôn đi cùng) và bộ quy tắc để cài máy khác hoặc đóng vào bản mới',
                              lambda: self.xuat_goi_cai()),
                          nut('b_nhap_cai', 'Nhập gói cài…', 'Nhập gói cài đơn giá đất + hệ số K (.larcgia): chọn xã cần cài và cách ghi '
                              '(bổ sung / thay toàn bộ / mở để sửa và kiểm định trước khi lưu)', lambda: self.nhap_goi_cai()),
                          nut('b_nhap', 'Nhập quy tắc…', 'File .json gói quy tắc do đơn vị khác hoặc đơn vị phát hành gửi; kiểm từng '
                              'trường, không chạy mã', lambda: self.nhap_file()),
                          nut('b_xuat', 'Xuất quy tắc…', 'Gửi gói quy tắc (không kèm bảng giá / hệ số K) cho đơn vị khác',
                              lambda: self.xuat_file()),
                          nut('b_xoa', 'Xóa gói', 'Xóa gói của máy; số đã áp vào hộ không đổi', lambda: self.xoa())]))
        trai.addWidget(c3)
        khung_trai = QWidget()
        khung_trai.setLayout(trai)
        khung_trai.setFixedWidth(self.RONG_TRAI + 24)
        trai.setContentsMargins(0, 0, 0, 0)
        than.addWidget(khung_trai)

        # ---- phải: nội dung gói (phần đầu ẩn khi đang ở thẻ con Đọc văn bản - dữ liệu dùng chung, không thuộc gói nào)
        phai = QVBoxLayout()
        self.dau_goi = QWidget()
        v_dau = QVBoxLayout(self.dau_goi)
        v_dau.setContentsMargins(0, 0, 0, 0)
        self.lb_trang_thai = QLabel('')
        self.lb_trang_thai.setWordWrap(True)
        v_dau.addWidget(self.lb_trang_thai)
        phai.addWidget(self.dau_goi)
        hang = QHBoxLayout()
        f1, f2 = QFormLayout(), QFormLayout()
        self.o_ma, self.o_ten, self.o_so_hieu, self.o_bang_gia, self.o_tu, self.o_den = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.o_so_hieu.setToolTip('Số hiệu ngắn, ghi vào giải trình và ô Ghi chú của dòng đất, ví dụ QĐ 03/2026/QĐ-UBND')
        self.o_tu.setPlaceholderText('dd/mm/yyyy')
        self.o_den.setPlaceholderText('Trống: còn hiệu lực')
        f1.addRow('Tên gói:', self.o_ten)
        f1.addRow('Số hiệu văn bản:', self.o_so_hieu)
        f1.addRow('Bảng giá đất:', self.o_bang_gia)
        f2.addRow('Mã gói:', self.o_ma)
        f2.addRow('Hiệu lực từ:', self.o_tu)
        f2.addRow('Hiệu lực đến:', self.o_den)
        hang.addLayout(f1, 2)
        hang.addLayout(f2, 1)
        v_dau.addLayout(hang)

        self.the = QTabWidget()
        # thẻ Quy tắc
        t1 = QWidget()
        v1 = QVBoxLayout(t1)
        g_ct = QGroupBox('Công thức: đơn giá = giá bảng giá nhân lần lượt các hệ số')
        h_ct = QHBoxLayout(g_ct)
        self.o_cong_thuc = QLineEdit()
        self.o_cong_thuc.setToolTip('Các hệ số nhân, cách nhau bằng dấu phẩy, ví dụ K1, K2, K3, K_KHAC, K4. Chỉ nhận dạng tích; công thức dạng khác cần cập nhật phần mềm.')
        self.sp_tron = QSpinBox()
        self.sp_tron.setRange(-6, 4)
        self.sp_tron.setToolTip('0: đến đồng; -3: đến nghìn đồng')
        self.ck_chuyen_tiep = QCheckBox('Có quy định chuyển tiếp')       # 1.1.06: chữ ngắn (1093 x 614), ý đầy đủ ở chú thích
        self.ck_chuyen_tiep.setToolTip('Có quy định chuyển tiếp: giữ giá đất cụ thể nếu cao hơn')
        for w, co in ((QLabel('Hệ số:'), 0), (self.o_cong_thuc, 1), (QLabel('Làm tròn đơn giá:'), 0), (self.sp_tron, 0), (self.ck_chuyen_tiep, 0)):
            h_ct.addWidget(w, co)
        v1.addWidget(g_ct)
        v1.addWidget(QLabel('Yếu tố ảnh hưởng (K3): sửa trực tiếp trên bảng'))
        self.bang_yt = QTableWidget(0, len(COT_YT))
        self.bang_yt.setHorizontalHeaderLabels(COT_YT)
        self.bang_yt.verticalHeader().setVisible(False)
        hh = self.bang_yt.horizontalHeader()
        for c, cho in enumerate(CHU_COT_YT):
            self.bang_yt.horizontalHeaderItem(c).setToolTip(cho)
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch if c == 1 else (QHeaderView.ResizeMode.Interactive if c in (0, 4, 6) else QHeaderView.ResizeMode.ResizeToContents))
        for c, rong in ((0, 130), (4, 120), (6, 130)):
            self.bang_yt.setColumnWidth(c, rong)
        v1.addWidget(self.bang_yt, 2)
        h_yt = QHBoxLayout()
        self.b_them_yt = QPushButton('+ Yếu tố')
        self.b_them_yt.clicked.connect(lambda: self.them_dong(self.bang_yt, ('K3_MOI', '', '1', 'pnn', '', '', '')))
        self.b_bo_yt = QPushButton('Bỏ yếu tố')
        self.b_bo_yt.clicked.connect(lambda: self.bang_yt.removeRow(self.bang_yt.currentRow()))
        self.b_them_hs = QPushButton('+ Hệ số mới')
        self.b_them_hs.setToolTip('Văn bản đặt thêm hệ số (K4…): khai ở bảng dưới rồi thêm mã vào ô công thức')
        self.b_them_hs.clicked.connect(lambda: self.them_dong(self.bang_them, ('K4', '', '1', '')))
        self.b_bo_hs = QPushButton('Bỏ hệ số')
        self.b_bo_hs.clicked.connect(lambda: self.bang_them.removeRow(self.bang_them.currentRow()))
        for b in (self.b_them_yt, self.b_bo_yt, self.b_them_hs, self.b_bo_hs):
            h_yt.addWidget(b)
        h_yt.addStretch(1)
        v1.addLayout(h_yt)
        self.bang_them = QTableWidget(0, len(COT_THEM))
        self.bang_them.setHorizontalHeaderLabels(COT_THEM)
        self.bang_them.verticalHeader().setVisible(False)
        self.bang_them.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang_them.setColumnWidth(3, 200)
        self.bang_them.setMaximumHeight(96)
        v1.addWidget(self.bang_them)
        self.lb_doan = QLabel('')
        self.lb_doan.setWordWrap(True)
        v1.addWidget(self.lb_doan)
        self.the.addTab(t1, 'Quy tắc')
        # thẻ Câu giải trình
        t2 = QWidget()
        v2 = QVBoxLayout(t2)
        lb_cau = QLabel('Câu ghi vào nhật ký giải trình. Văn bản mới đổi điều khoản thì sửa ở đây. {so_hieu}, {bang_gia} và các ô trong ngoặc tự điền khi tính.')
        lb_cau.setWordWrap(True)                        # 1.1.06: không ép cửa sổ rộng hơn màn 1093 px
        v2.addWidget(lb_cau)
        self.bang_cau = QTableWidget(len(gg.CAU_CHU), 2)
        self.bang_cau.setHorizontalHeaderLabels(['Dùng ở đâu', 'Mẫu câu'])
        self.bang_cau.verticalHeader().setVisible(False)
        self.bang_cau.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang_cau.setColumnWidth(0, 290)
        self.bang_cau.setWordWrap(True)
        self.bang_cau.verticalHeader().setDefaultSectionSize(3 * self.fontMetrics().height() + 10)     # câu dài nhất 3 dòng
        v2.addWidget(self.bang_cau, 2)
        v2.addWidget(QLabel('Văn bản căn cứ của gói (mỗi dòng một văn bản; tự gộp vào danh sách căn cứ khi chọn gói):'))
        self.o_can_cu = QPlainTextEdit()
        v2.addWidget(self.o_can_cu, 1)
        self.the.addTab(t2, 'Câu giải trình, căn cứ')
        # thẻ So sánh
        t3 = QWidget()
        v3 = QVBoxLayout(t3)
        self.o_khac = QPlainTextEdit()
        self.o_khac.setReadOnly(True)
        v3.addWidget(self.o_khac)
        self.the.addTab(t3, 'Khác gói gốc')
        self.the_doc = None
        if khung_cn is not None:                        # 1.1.06: thẻ "Cập nhật, bổ sung giá đất" cũ thành thẻ con đầu
            self.the_doc = self.the.insertTab(0, khung_cn, 'Đọc văn bản, quy tắc vị trí')
            khung_cn.da_doc.connect(self.tao_goi_nhap)
            self.the.setCurrentIndex(1)
            self.the.currentChanged.connect(self._doi_the_con)
        phai.addWidget(self.the, 1)
        than.addLayout(phai, 1)

        hn = QHBoxLayout()
        self.lb_luu_y = QLabel('Số đã áp vào hộ không tự đổi khi có gói mới: đơn giá và tên văn bản đã lưu ở dòng đất, V1 giữ nguyên.')
        self.lb_luu_y.setWordWrap(True)
        hn.addWidget(self.lb_luu_y, 1)
        self.b_kiem = QPushButton('Kiểm tra, so sánh')
        self.b_kiem.setToolTip('Kiểm các trường và liệt kê những điểm khác gói gốc, chưa lưu gì')
        self.b_kiem.clicked.connect(lambda: self.kiem(True))
        self.b_luu = QPushButton('Lưu gói')
        self.b_luu.clicked.connect(lambda: self.luu())
        d = QPushButton('Đóng')
        d.clicked.connect(self.reject)
        if nhung:
            d.hide()
        for b in (self.b_kiem, d, self.b_luu):
            hn.addWidget(b)
        lo.addLayout(hn)
        self.nap(ma_chon)
        from .quan_tri_bo import dang_ky_khi_doi
        dang_ky_khi_doi(self.lam_moi_khi_doi)           # 1.1.06: gói / bảng giá / hệ số K đổi ở nơi khác -> nạp lại danh sách

    # ------------------------------------------------ thẻ gộp (1.1.06)
    def _doi_the_con(self, i: int) -> None:
        """Thẻ con Đọc văn bản: ẩn phần đầu + nút Lưu gói (đang làm với bảng giá dùng chung của máy, không phải gói đang chọn)."""
        doc = self.the_doc is not None and i == self.the_doc
        for w in (self.dau_goi, self.lb_luu_y, self.b_kiem, self.b_luu):
            w.setVisible(not doc)

    def _lam_tren_cn(self, ham):
        """Lệnh cột trái chạy trên khung đọc văn bản: mở thẻ con đó trước để người dùng thấy kết quả."""
        if self.the_doc is not None:
            self.the.setCurrentIndex(self.the_doc)
        return ham()

    def _lam_tren_k(self, ham):
        """Lệnh hệ số K ở cột trái: mở thẻ Hệ số K (bảng xem / sửa / Lưu) rồi chạy."""
        if self.khung_k is None:
            return None
        if self._mo_the_k is not None:
            self._mo_the_k()
        return ham(self.khung_k)

    def doc_them_van_ban(self, file=None):
        return self._lam_tren_cn(lambda: self.khung_cn.chon_file(file))

    def lam_moi_khi_doi(self) -> None:
        """quan_tri_bo.bao_doi: dữ liệu giá đất trên máy đổi (gói lưu / xóa / cài ở nơi khác). Đang sửa gói chưa lưu thì không động."""
        if not self.chua_luu():
            self.nap((self.g or {}).get('ma', ''))

    def tao_goi_nhap(self, kq: dict) -> bool:
        """Đọc xong một văn bản (khung_cn.da_doc) -> GÓI NHÁP chép quy tắc gói đang chọn, tên / số hiệu / hiệu lực theo văn bản, dòng đầu
        danh sách "Nháp - chưa lưu". Không ghi gì: chỉ có hiệu lực khi người dùng bấm Lưu gói (vẫn qua quyền quản trị). Văn bản cùng
        số hiệu với gói đã có, hoặc đang sửa gói khác chưa lưu: không tạo, báo ở dòng trạng thái."""
        tt = (kq or {}).get('van_ban_doc') or {}
        so_hieu = (tt.get('so_hieu') or '').strip()
        if self.chua_luu() and self._nhap is None:
            self.lb_trang_thai.setText('Đã đọc văn bản. Gói đang sửa chưa lưu nên chưa tạo gói nháp - lưu hoặc bỏ thay đổi rồi bấm '
                                       '"Tạo gói từ gói này".')
            return False
        if so_hieu and any(gg.chuan_so_hieu(g.get('so_hieu')) == gg.chuan_so_hieu(so_hieu) for g in gg.ds_goi()):
            self.lb_trang_thai.setText(f'Văn bản {so_hieu} đã có gói trong danh sách - không tạo gói nháp mới.')
            return False
        ten = so_hieu or str((kq or {}).get('van_ban') or '').strip() or 'Văn bản mới'
        ngay = tt.get('ngay') or date.today().strftime('%d/%m/%Y')
        goc = next((g for g in self._ds if g is not self._nhap and g.get('ma') == (self.g or {}).get('ma')), None) or \
            next((g for g in self._ds if g is not self._nhap), None) or gg._gan_san()
        g = gg.tao_goi_tu(goc, self._ma_moi(), ten, ngay)
        g['so_hieu'] = so_hieu or ten
        self._nhap = g
        self.nap(g['ma'])
        ly_do = {'hieu_luc': f'ngày hiệu lực {ngay} đọc trong văn bản', 'ban_hanh': f'ngày {ngay} là ngày KÝ đọc ở đầu văn bản (chưa '
                 'thấy câu "có hiệu lực từ ngày")'}.get(tt.get('ngay_tu'), f'chưa đọc được ngày hiệu lực - tạm ghi hôm nay {ngay}')
        self.lb_trang_thai.setText(f'GÓI NHÁP từ văn bản vừa đọc - CHƯA LƯU, chưa ảnh hưởng cách tính giá. Số hiệu: '
                                   f'{so_hieu or "chưa đọc được (lấy tên văn bản)"}; {ly_do}. Kiểm tra số hiệu, ngày hiệu lực, quy '
                                   'tắc rồi bấm "Lưu gói"; không dùng thì chọn gói khác để bỏ nháp.')
        return True

    # ------------------------------------------------ danh sách
    def nap(self, ma_chon: str = '') -> None:
        from PySide6.QtGui import QFont
        self._ds = ([self._nhap] if self._nhap is not None else []) + gg.ds_goi()
        self.ds.blockSignals(True)
        self.ds.setRowCount(len(self._ds))
        for r, g in enumerate(self._ds):
            nhap = g is self._nhap
            o = _o(('Nháp - chưa lưu: ' if nhap else '') + g.get('ten', '') + (' (gắn sẵn)' if g.get('gan_san') else ''))
            if nhap:
                f = QFont(o.font())
                f.setItalic(True)
                o.setFont(f)
                o.setToolTip('Gói nháp tạo từ văn bản vừa đọc: chưa lưu, chưa có hiệu lực')
            self.ds.setItem(r, 0, o)
            self.ds.setItem(r, 1, _o(gg.ngay_vn(g.get('hieu_luc_tu'))))
        i = next((k for k, g in enumerate(self._ds) if g.get('ma') == ma_chon), 0)
        self.ds.setCurrentCell(i, 0)
        self.ds.blockSignals(False)
        self._chon_dong(i)

    def _chon_dong(self, r: int) -> None:
        if not 0 <= r < len(self._ds):
            return
        g = self._ds[r]
        if g is self._nhap:                             # 1.1.06: dòng gói nháp - hiện như gói mới chưa lưu
            if not (self.moi and self.g is not None and self.g.get('ma') == g.get('ma')):
                self.dat_goi(g, gg.lay_goi(g.get('goc', '')) or gg._gan_san(), True)
            return
        if self.g is not None and g.get('ma') == self.g.get('ma') and not self.moi:
            return
        if self.chua_luu() and not self._hoi_bo():
            i = next((k for k, x in enumerate(self._ds) if x.get('ma') == self.g.get('ma')), 0)
            self.ds.blockSignals(True)
            self.ds.setCurrentCell(i, 0)
            self.ds.blockSignals(False)
            return
        self.dat_goi(g, gg.lay_goi(g.get('goc', '')) or gg._gan_san(), False)
        if self._nhap is not None:                      # rời gói nháp (đã đồng ý bỏ): bỏ dòng nháp khỏi danh sách
            self._nhap = None
            self.nap(g.get('ma', ''))

    def chua_luu(self) -> bool:
        """Gói trên màn hình có gì chưa lưu (gói gắn sẵn chỉ xem: không)."""
        if self.g is None or self.g.get('gan_san'):
            return False
        return self.moi or self.gia_tri() != self._luc_nap

    def _hoi_bo(self) -> bool:
        if self.im_lang:
            return True
        return QMessageBox.question(self, TIEU_DE, 'Gói đang sửa chưa lưu. Bỏ các thay đổi?') == QMessageBox.StandardButton.Yes

    def reject(self) -> None:
        if not self.chua_luu() or self._hoi_bo():
            super().reject()

    def dat_goi(self, g: dict, goc: dict, moi: bool) -> None:
        """Hiện một gói. moi: gói chưa lưu (vừa tạo / vừa nhập)."""
        self.g, self.goc, self.moi = copy.deepcopy(g), goc, moi
        ro = bool(g.get('gan_san'))
        self.o_ma.setText(g.get('ma', ''))
        self.o_ten.setText(g.get('ten', ''))
        self.o_so_hieu.setText(g.get('so_hieu', ''))
        self.o_bang_gia.setText(g.get('bang_gia', ''))
        self.o_tu.setText(gg.ngay_vn(g.get('hieu_luc_tu')))
        self.o_den.setText(gg.ngay_vn(g.get('hieu_luc_den')))
        ct = g.get('cong_thuc', {})
        self.o_cong_thuc.setText(', '.join(ct.get('he_so', [])))
        self.sp_tron.setValue(int(ct.get('lam_tron', 0)))
        self.ck_chuyen_tiep.setChecked(bool((g.get('chuyen_tiep') or {}).get('bat')))
        self.bang_yt.setRowCount(0)
        for y in g.get('yeu_to', []):
            self.them_dong(self.bang_yt, (y['ma'], y['ten'], y['he_so'], y['ap_cho'], y.get('kich_hoat_ket_cau', ''), 'có' if y.get('khoa_neu_quy_dinh_rieng') else '', y.get('can_cu', '')))
        self.bang_them.setRowCount(0)
        for x in g.get('he_so_them') or []:
            self.them_dong(self.bang_them, (x['ma'], x.get('ten', ''), x.get('mac_dinh', 1), x.get('can_cu', '')))
        cau = g.get('cau_chu') or {}
        for r, (k, nhan) in enumerate(gg.CAU_CHU):
            o = _o(nhan)
            o.setToolTip(nhan)
            self.bang_cau.setItem(r, 0, o)
            self.bang_cau.setItem(r, 1, _o(cau.get(k, '')))
        self.o_can_cu.setPlainText('\n'.join(g.get('van_ban_can_cu') or []))
        n = sum(len(v) for v in g.get('dia_ban', {}).values())
        self.lb_doan.setText(f'Địa bàn: {", ".join(g.get("dia_ban", {}))} ({n} đoạn đường). Đoạn đường và K1 đổi bằng "Tạo gói từ bảng hệ số K" hoặc nhập file.')
        self.lb_trang_thai.setText('Gói gắn sẵn trong phần mềm: chỉ xem. Muốn đổi, bấm "Tạo gói mới từ gói này".' if ro else ('Gói mới, CHƯA LƯU.' if moi else 'Gói của máy, sửa được.'))
        for w in (self.o_ma, self.o_ten, self.o_so_hieu, self.o_bang_gia, self.o_tu, self.o_den, self.o_cong_thuc, self.o_can_cu):
            w.setReadOnly(ro)
        self.sp_tron.setEnabled(not ro)
        self.ck_chuyen_tiep.setEnabled(not ro)
        sua = QAbstractItemView.EditTrigger.NoEditTriggers if ro else SUA_BANG
        for b in (self.bang_yt, self.bang_them, self.bang_cau):
            b.setEditTriggers(sua)
        for b in (self.b_them_yt, self.b_bo_yt, self.b_them_hs, self.b_bo_hs, self.b_luu):
            b.setEnabled(not ro)
        self.b_xoa.setEnabled(not ro and not moi)
        self._luc_nap = self.gia_tri()
        self.kiem()

    @staticmethod
    def them_dong(bang, gt) -> None:
        r = bang.rowCount()
        bang.setRowCount(r + 1)
        for c, v in enumerate(gt):
            bang.setItem(r, c, _o(v))

    # ------------------------------------------------ đọc form
    @staticmethod
    def _chu(bang, r: int, c: int) -> str:
        it = bang.item(r, c)
        return it.text().strip() if it is not None else ''

    def gia_tri(self) -> dict:
        """Gói theo nội dung đang hiện trên màn hình."""
        g = copy.deepcopy(self.g)
        g.pop('gan_san', None)
        g.update(ma=self.o_ma.text().strip(), ten=self.o_ten.text().strip(), so_hieu=self.o_so_hieu.text().strip(), bang_gia=self.o_bang_gia.text().strip(),
                 hieu_luc_tu=gg._ngay(self.o_tu.text()), hieu_luc_den=gg._ngay(self.o_den.text()))
        g['cong_thuc'] = dict(g.get('cong_thuc', {}), he_so=[x.strip() for x in self.o_cong_thuc.text().replace('×', ',').split(',') if x.strip()], lam_tron=self.sp_tron.value())
        g['chuyen_tiep'] = dict(g.get('chuyen_tiep') or {}, bat=self.ck_chuyen_tiep.isChecked())
        g['van_ban_can_cu'] = [x.strip() for x in self.o_can_cu.toPlainText().splitlines() if x.strip()]
        cu = {y['ma']: y for y in g.get('yeu_to', [])}
        o = self._chu
        b = self.bang_yt
        g['yeu_to'] = [dict(cu.get(o(b, r, 0), {}), ma=o(b, r, 0), ten=o(b, r, 1), he_so=o(b, r, 2).replace(',', '.'), ap_cho=o(b, r, 3), kich_hoat_ket_cau=o(b, r, 4),
                            khoa_neu_quy_dinh_rieng=bool(o(b, r, 5)), can_cu=o(b, r, 6)) for r in range(b.rowCount())]
        b = self.bang_them
        g['he_so_them'] = [dict(ma=o(b, r, 0), ten=o(b, r, 1), mac_dinh=o(b, r, 2).replace(',', '.'), can_cu=o(b, r, 3)) for r in range(b.rowCount())]
        g['cau_chu'] = {k: self.bang_cau.item(r, 1).text() for r, (k, _) in enumerate(gg.CAU_CHU) if self.bang_cau.item(r, 1) is not None and self.bang_cau.item(r, 1).text().strip()}
        return g

    def kiem(self, mo_the: bool = False) -> list:
        """Hiện lỗi hoặc các điểm khác so với gói gốc. Trả danh sách lỗi."""
        g = self.gia_tri()
        loi = gg.kiem_goi(g)
        if loi:
            self.o_khac.setPlainText('CHƯA HỢP LỆ:\n' + '\n'.join(loi))
        else:
            self.o_khac.setPlainText('\n'.join(gg.so_sanh(self.goc or gg._gan_san(), g)) or '(Không khác gói gốc.)')
        if mo_the:
            self.the.setCurrentIndex(self.the.count() - 1)
        return loi

    def _bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def _ma_moi(self) -> str:
        n = 1
        while gg.lay_goi(f'GOI_{date.today():%Y%m%d}_{n}') is not None:
            n += 1
        return f'GOI_{date.today():%Y%m%d}_{n}'

    def _hoi_ten(self):
        """(mã, tên, hiệu lực từ) cho gói mới; im_lang dùng giá trị mặc định. None: bỏ."""
        hom_nay = date.today().strftime('%d/%m/%Y')
        if self.im_lang:
            return self._ma_moi(), 'Gói mới', hom_nay
        ten, ok = QInputDialog.getText(self, TIEU_DE, 'Số hiệu văn bản mới (ví dụ QĐ 15/2027/QĐ-UBND):')
        if not ok or not ten.strip():
            return None
        tu, ok = QInputDialog.getText(self, TIEU_DE, 'Hiệu lực từ ngày (dd/mm/yyyy):', text=hom_nay)
        if not ok:
            return None
        return self._ma_moi(), ten.strip(), tu.strip()

    def _goi_dang_chon(self) -> dict:
        return self._ds[max(0, self.ds.currentRow())]

    # ------------------------------------------------ tạo, nhập
    def tao_tu_goi(self) -> bool:
        goc = self._goi_dang_chon()
        t = self._hoi_ten()
        if not t:
            return False
        self.dat_goi(gg.tao_goi_tu(goc, *t), goc, True)
        return True

    def tao_tu_he_so_k(self) -> bool:
        goc = self._goi_dang_chon()
        t = self._hoi_ten()
        if not t:
            return False
        try:
            self.dat_goi(gg.tao_goi_tu_he_so_k(goc, *t), goc, True)
        except gg.LoiGoi as e:
            self._bao(str(e))
            return False
        return True

    def nhap_file(self, file=None) -> bool:
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file gói quy tắc', '', 'Gói quy tắc (*.json)')
            if not file:
                return False
        try:
            g = gg.doc_file_goi(file)
        except gg.LoiGoi as e:
            self._bao(str(e))
            return False
        if g.get('ma') == gg.MA_GAN_SAN:
            g['ma'] = self._ma_moi()
        self.dat_goi(g, gg.lay_goi(g.get('goc', '')) or gg._gan_san(), True)
        return True

    def xuat_file(self, file=None) -> bool:
        if self.g is None:
            return False
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu gói quy tắc', f'{self.g.get("ma", "goi")}.json', 'Gói quy tắc (*.json)')
            if not file:
                return False
        try:
            gg.xuat_file_goi(self.g if self.g.get('gan_san') else self.gia_tri(), file)
        except OSError as e:
            self._bao(f'Không ghi được file: {e}')
            return False
        return True

    def xuat_goi_cai(self, file=None, ds_xa=None) -> bool:
        """Chọn xã (đơn giá + hệ số K đi cùng) rồi xuất file .larcgia kèm bộ quy tắc."""
        if ds_xa is None:
            h = HopChonXaGoiCai(self)
            h.im_lang = self.im_lang
            if self.im_lang:
                h._chon_het()
                h.accept()
                ds_xa = h.chon
            else:
                if h.exec() != QDialog.DialogCode.Accepted:
                    return False
                ds_xa = h.chon
        if not ds_xa:
            self._bao('Chưa chọn xã / phường nào.')
            return False
        if file is None:
            mau = 'GoiCai_GiaDat_' + ('_'.join(x.replace(' ', '')[:12] for x in ds_xa[:2]) or 'DongNai')
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu gói cài giá đất', mau + gg.DUOI_GOI_CAI,
                                                  f'Gói cài giá đất (*{gg.DUOI_GOI_CAI})')
            if not file:
                return False
        try:
            goc = self.g if self.g and not self.moi else gg._gan_san()
            if goc and not goc.get('gan_san') and self.g is goc:
                goc = self.gia_tri()
            ra = gg.xuat_goi_cai(file, ds_xa, goc)
        except (gg.LoiGoi, OSError) as e:
            self._bao(str(e))
            return False
        self._bao(f'Đã xuất gói cài {len(ds_xa)} địa bàn (đơn giá + hệ số K + bộ quy tắc):\n{ra}', loi=False)
        return True

    def nhap_goi_cai(self, file=None, bo_sung: bool = True, chi_xa: list | None = None, sua: bool = False) -> bool:
        """1.1.06: hộp chọn xã + cách ghi (_tao_hop_nhap_goi_cai) thay câu hỏi Có / Không. Im lặng: dùng bo_sung / chi_xa truyền vào.
        sua (1.1.07, đợt D): không ghi gì - đưa gói lên các bảng để sửa, kiểm định rồi người dùng tự lưu (sua_goi_cai)."""
        from pathlib import Path
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn gói cài giá đất', '', f'Gói cài giá đất (*{gg.DUOI_GOI_CAI})')
            if not file:
                return False
        try:
            xem = gg.doc_goi_cai(file)
        except gg.LoiGoi as e:
            self._bao(str(e))
            return False
        if not self.im_lang:
            h = _tao_hop_nhap_goi_cai(self, xem, Path(file).name, co_sua=self.khung_cn is not None)
            try:
                if h.exec() != QDialog.DialogCode.Accepted:
                    return False
                bo_sung, chi_xa, sua = h.bo_sung, h.chon, h.che_do == 'sua'
            finally:
                h.deleteLater()
        if sua:
            return self.sua_goi_cai(xem, chi_xa, Path(file).name)
        if not self.im_lang:
            if not bo_sung and QMessageBox.question(
                    self, TIEU_DE, 'Thay TOÀN BỘ bảng giá đất và hệ số K của máy bằng ' + f'{len(chi_xa)} xã đã chọn? Mọi xã khác trên '
                    'máy (kể cả 4 địa bàn gắn sẵn) bị bỏ khỏi bảng đang dùng. Số đã áp vào hộ không đổi.') != QMessageBox.StandardButton.Yes:
                return False
        if not self._xin_quyen():
            return False
        try:
            kq = gg.nhap_goi_cai(file, bo_sung=bo_sung, chi_xa=chi_xa)
        except Exception as e:                                           # noqa: BLE001
            self._bao(str(e))
            return False
        self.da_doi = True
        self.nap(kq.get('goi_ma') or '')
        self._bao(f'Đã cài {len(kq.get("xa") or [])} địa bàn ({kq.get("so_gia", 0)} dòng giá, {kq.get("so_k", 0)} dòng hệ số K). '
                  'Cửa sổ Tính đơn giá đất bồi thường sẽ hiện đủ xã vừa cài.'
                  + (' Mã băm SHA-256 của gói khớp (nội dung đúng như lúc xuất).' if kq.get('niem_phong') else
                     ' Gói xuất từ bản trước 1.1.03, không có mã băm đối chiếu.'), loi=False)
        return True

    def sua_goi_cai(self, xem: dict, chi_xa: list | None = None, ten_file: str = '') -> bool:
        """1.1.07 (đợt D) - nhập gói cài ở chế độ "sửa và kiểm định trước khi lưu": KHÔNG ghi gì. Đơn giá đất các xã đã chọn lên bảng
        xem trước của thẻ con Đọc văn bản (kiem_dinh tô đỏ / vàng như khi đọc văn bản), hệ số K lên thẻ Hệ số K (xã trùng thay, xã
        khác giữ - như cách Bổ sung), bộ quy tắc của gói thành gói nháp. Người dùng sửa rồi tự ghi bằng ĐÚNG các nút sẵn có ("Ghi vào
        bảng giá đất", "Lưu" hệ số K, "Lưu gói") - cả ba đều hỏi quyền quản trị như cũ."""
        from . import he_so_k as hk
        if self.khung_cn is None:
            self._bao('Chế độ sửa trước khi lưu chỉ có ở thẻ "Bộ quy tắc & cập nhật giá đất" của cửa sổ Bảng giá đất.')
            return False
        chon = [str(x).strip() for x in (chi_xa if chi_xa is not None else [x['ten'] for x in gg.thong_ke_goi_cai(xem)])
                if str(x).strip()]
        dong_gia = [dict(r) for r in xem['bang_gia']['dong'] if gg._cua_xa(r.get('xa'), chon)]
        dong_k = [r for r in hk._mo_rong(xem['he_so_k'].get('dong')) if gg._cua_xa(r.get('dia_ban'), chon)]
        if not dong_gia and not dong_k:
            self._bao('Gói không có dòng đơn giá / hệ số K nào của các xã đã chọn.')
            return False
        k = self.khung_k
        if dong_k and k is not None and k.chua_luu and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, 'Thẻ Hệ số K đang có thay đổi chưa lưu. Bỏ các thay đổi đó để đưa hệ số K của gói lên?') \
                != QMessageBox.StandardButton.Yes:
            return False
        nguon = ('gói cài ' + ten_file).strip()
        phan = []
        if dong_k and k is not None:
            xa_moi = {gg._khoa_xa(r.get('dia_ban') or '') for r in dong_k}
            giu = [r for r in hk.tat_ca() if gg._khoa_xa(r.get('dia_ban') or '') not in xa_moi]
            k._nhan(giu + [dict(r) for r in dong_k], xem['he_so_k'].get('van_ban') or '', nguon,
                    f'Từ {nguon}: {len(dong_k)} dòng của {len(xa_moi)} xã đã chọn (xã khác giữ như trên máy). CHƯA LƯU - kiểm tra rồi '
                    'bấm Lưu.')
            phan.append(f'{len(dong_k)} dòng hệ số K ở thẻ Hệ số K (bấm Lưu ở thẻ đó)')
        if self._nhap_goi_tu_goi_cai(xem['goi'], chon):
            phan.append('bộ quy tắc của gói là gói nháp (thẻ con Quy tắc, bấm Lưu gói)')
        if dong_gia:
            kc = self.khung_cn
            vb = xem['bang_gia'].get('van_ban') or ''
            chu = (f'Từ {nguon}, CHƯA GHI.' + (' Đã đưa lên: ' + '; '.join(phan) + '.' if phan else ''))
            kc.kq = {'dong_goc': dong_gia, 'quy_tac': [], 'van_ban': vb, 'chu': chu}
            kc._ve_quy_tac([])
            i = kc.cb_cach.findData('bo_sung')
            if i >= 0:
                kc.cb_cach.setCurrentIndex(i)
            self._lam_tren_cn(lambda: kc._hien(dong_gia, vb, chu, nguon))
        elif dong_k:
            self._lam_tren_k(lambda _k: None)
        return True

    def _nhap_goi_tu_goi_cai(self, goi: dict, chon: list) -> bool:
        """Bộ quy tắc của gói cài -> gói nháp (chưa lưu). Trùng hẳn gói đã có trên máy: chọn gói đó, không tạo nháp. Đang sửa gói khác
        chưa lưu: không động (như tao_goi_nhap)."""
        if self.chua_luu() and self._nhap is None:
            self.lb_trang_thai.setText('Gói đang sửa chưa lưu nên chưa đưa bộ quy tắc của gói cài thành gói nháp.')
            return False
        g = copy.deepcopy({k: v for k, v in goi.items() if k != 'gan_san'})
        if isinstance(g.get('dia_ban'), dict):          # đoạn đường / K1 riêng: chỉ xã đã chọn (như gg.nhap_goi_cai)
            g['dia_ban'] = {x: v for x, v in g['dia_ban'].items() if gg._cua_xa(x, chon)}
        if not g.get('ma') or g.get('ma') == gg.MA_GAN_SAN:
            g['ma'] = (g.get('ma') or 'CAI') + '_MAY'
        co = gg.lay_goi(g['ma'])
        if co is not None and {x: v for x, v in co.items() if x != 'gan_san'} == g:
            self._nhap = None
            self.nap(g['ma'])
            self.lb_trang_thai.setText(f'Bộ quy tắc trong gói cài trùng gói "{co.get("ten", "")}" đã có trên máy - không tạo gói nháp.')
            return False
        self._nhap = g
        self.nap(g['ma'])
        self.lb_trang_thai.setText('GÓI NHÁP từ bộ quy tắc của gói cài - CHƯA LƯU, chưa ảnh hưởng cách tính giá.'
                                   + (f' Đã có gói mã {g["ma"]} trên máy: Lưu gói sẽ hỏi thay gói đó.' if co is not None else '')
                                   + ' Kiểm tra rồi bấm "Lưu gói"; không dùng thì chọn gói khác để bỏ nháp.')
        return True

    # ------------------------------------------------ lưu, xóa
    def _xin_quyen(self) -> bool:
        from .man_hinh_don_gia import xin_quyen_sua
        return xin_quyen_sua(self, im_lang=self.im_lang)

    def luu(self) -> bool:
        if self.g is None or self.g.get('gan_san'):
            return False
        loi = self.kiem(True)
        if loi:
            self._bao('Gói chưa hợp lệ:\n' + '\n'.join(loi[:12]))
            return False
        if not self._xin_quyen():
            return False
        g = self.gia_tri()
        if self.moi and gg.lay_goi(g['ma']) is not None and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, f'Đã có gói mã {g["ma"]}. Thay gói đó bằng gói này?') != QMessageBox.StandardButton.Yes:
            return False
        try:
            gg.ghi_goi(g)
        except Exception as e:                                           # noqa: BLE001 - LoiGoi, thiếu quyền, lỗi ghi: báo rõ, không sập
            self._bao(str(e))
            return False
        self.da_doi = True
        self.g, self.moi = None, False
        self._nhap = None                               # gói nháp đã thành gói thật
        self.nap(g['ma'])
        self._bao(f'Đã lưu gói {g["ten"]}. Áp dụng cho việc tính mới từ {gg.ngay_vn(g["hieu_luc_tu"])}; số đã áp vào hộ không đổi.', loi=False)
        return True

    def xoa(self, hoi: bool = True) -> bool:
        if self.g is None or self.g.get('gan_san') or self.moi:
            return False
        if hoi and not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Xóa gói {self.g.get("ten")}? Số đã áp vào hộ không đổi.') != QMessageBox.StandardButton.Yes:
            return False
        if not self._xin_quyen():
            return False
        try:
            gg.xoa_goi(self.g['ma'])
        except Exception as e:                                           # noqa: BLE001
            self._bao(str(e))
            return False
        self.da_doi = True
        self.g, self.moi = None, False
        self.nap()
        return True
