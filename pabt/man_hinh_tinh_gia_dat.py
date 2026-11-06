"""Cửa sổ "Tính đơn giá đất bồi thường" - thay cửa sổ tính giá nội bộ cũ. Nhóm đất, vị trí, mặt đường, yếu tố, hệ số thêm dựng theo gói quy tắc đang chọn (goi_gia_dat.py), gói gắn sẵn: NQ 28/2025/NQ-HĐND x QĐ 03/2026/QĐ-UBND.

Logic ở gia_dat_qd03.py, van_ban_can_cu.py (13 bậc pháp lý), quet_chung.py (bộ quét dùng chung); file này
chỉ hiển thị. Ba khối: Văn bản căn cứ (tự khử trùng + sắp xếp mỗi khi quét thêm / sửa xong) | Thông số đầu vào (địa bàn, nhóm đất, tuyến đường
& đoạn đường điểm đầu -> điểm cuối từ 106 đoạn, vị trí kết nối cụm 7 dòng NQ 27 / NQ 28, mặt đường, G_NQ28, K2, Phụ lục III, K khác, giá đất
cụ thể chuyển tiếp) và kết quả tức thì | Các dòng đất của mọi hộ trong dự án để áp giá (1.0.68: phạm vi, lọc nhanh, thêm / tự tạo dòng đất; bảng ảo, đổi thông số chỉ tính dòng đang thấy).
Áp giá = ap_gia_dat.ap_hang_loat (BoSoan.ap_don_gia_qd03 + luu: khóa hộ nhận việc, phân quyền, nhật ký, hoàn tác như mọi thao tác lưu phương án; hộ có V1 ghi vào nhánh V2)."""
from __future__ import annotations


from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea, QFrame, QSizePolicy, QTableView, QVBoxLayout, QWidget)

from . import ap_gia_dat as ap
from . import gia_dat_qd03 as g
from . import goi_gia_dat as gg
from . import quet_chung as qc
from . import van_ban_can_cu as vb
from .giao_dien import TOKEN, XepDong, gan_dinh_dang_nghin, hop_ket_qua
from .lap_pa import LoiNhap, doc_so
from .man_hinh_quet_chung import NutQuetChung
from .nghiep_vu import BoiCanh, thanh_tien_dat
from .tien import D, vn

TIEU_DE = 'LARC - Tính đơn giá đất bồi thường'
TOI_DA_COT_HO = 135
TAT_CA, DANG_CHON = 'tat_ca', 'dang_chon'
HO_CAN_TIEN_DO = 50
COT_DONG = ('Chọn', 'Hộ', 'Tờ, thửa', 'Loại đất', 'DT (m²)', 'Giá hiện tại', 'Đơn giá mới', 'Thành tiền mới', 'Ghi vào')
C_CHON, C_HO, C_THUA, C_LOAI, C_DT, C_GIA, C_MOI, C_TIEN, C_DICH = range(len(COT_DONG))
RONG_MAU = {C_CHON: 'Chọn', C_THUA: 'Thửa 1234 tờ 123', C_LOAI: 'Loại đất', C_DT: '12.345,6', C_GIA: 'Giá hiện tại', C_MOI: 'Đơn giá mới', C_TIEN: 'Thành tiền mới'}


class _MoHinhDong(QAbstractTableModel):
    """Bảng dòng đất: dong = các hàng đang hiện (DongGia), tich = khóa các dòng đã tích (giữ qua lọc / đổi phạm vi). Đơn giá mới, Thành tiền mới chỉ hiện ở dòng đang tích, tính khi vẽ."""

    def __init__(self, parent=None, khi_doi=None):
        super().__init__(parent)
        self.dong, self.tich = [], set()
        self.gia = None
        self.lamtron = 0
        self.khi_doi = khi_doi

    def dat_dong(self, ds: list) -> None:
        self.beginResetModel()
        self.dong = ds
        self.endResetModel()

    def dat_gia(self, gia) -> None:
        self.gia = gia
        if self.dong:
            self.dataChanged.emit(self.index(0, C_MOI), self.index(len(self.dong) - 1, C_TIEN))

    def doi_tich(self, ds: list, bat: bool) -> None:
        for x in ds:
            if x.chi_so != ap.CO_CHUA_DONG:
                (self.tich.add if bat else self.tich.discard)(x.khoa)
        if self.dong:
            self.dataChanged.emit(self.index(0, C_CHON), self.index(len(self.dong) - 1, C_TIEN))
        if self.khi_doi is not None:
            self.khi_doi()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.dong)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COT_DONG)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COT_DONG[section]
        return None

    def flags(self, idx):
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if idx.isValid() and idx.column() == C_CHON and self.dong[idx.row()].chi_so != ap.CO_CHUA_DONG:
            f |= Qt.ItemFlag.ItemIsUserCheckable
        return f

    def _chu(self, x, c: int) -> str:
        if c == C_HO:
            return f'{x.ma_ho} - {x.ho_ten}'.strip(' -')
        if c == C_THUA:
            return x.ten_thua
        if c == C_DICH:
            return x.dich
        if x.chi_so == ap.CO_CHUA_DONG:
            return ''
        if c == C_LOAI:
            return x.loai_dat
        if c == C_DT:
            return vn(x.dien_tich, 1)
        if c == C_GIA:
            return vn(x.gia_hien_tai)
        if self.gia is None or x.khoa not in self.tich or c not in (C_MOI, C_TIEN):
            return ''
        return vn(self.gia) if c == C_MOI else vn(thanh_tien_dat(x.dien_tich, self.gia, 1, x.ty_le, self.lamtron))     # cùng làm tròn với phương án thật

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        x, c = self.dong[idx.row()], idx.column()
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:
            return self._chu(x, c) if c != C_CHON else None
        if role == Qt.ItemDataRole.CheckStateRole and c == C_CHON and x.chi_so != ap.CO_CHUA_DONG:
            return 2 if x.khoa in self.tich else 0           # số nguyên: enum trả qua QVariant khác nhau giữa Qt5 và Qt6
        if role == Qt.ItemDataRole.TextAlignmentRole and C_DT <= c <= C_TIEN:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole and x.chi_so == ap.CO_CHUA_DONG:
            return QColor(TOKEN['chu_phu'])
        return None

    def setData(self, idx, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.CheckStateRole or idx.column() != C_CHON:
            return False
        self.doi_tich([self.dong[idx.row()]], int(getattr(value, 'value', value)) == 2)
        return True


class _BangDong(QTableView):
    def rowCount(self) -> int:
        return self.model().rowCount()


class HopThemDongDat(QDialog):
    """+ Thêm dòng đất cho hộ: chọn hộ, nhập Tờ, Thửa, Loại đất, Diện tích."""
    im_lang = False

    def __init__(self, parent, ds_ho: list, ma_mac_dinh=None, ds_loai=()):
        super().__init__(parent)
        self.setWindowTitle('Thêm dòng đất cho hộ')
        f = QFormLayout(self)
        self.cb_ho = QComboBox()
        self.cb_ho.setEditable(True)
        self.cb_ho.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cb_ho.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.cb_ho.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        for ma, ten in ds_ho:
            self.cb_ho.addItem(f'{ma} - {ten}', ma)
        self.cb_ho.setCurrentIndex(max(0, self.cb_ho.findData(ma_mac_dinh)))
        self.o_to, self.o_thua, self.o_dt = QLineEdit(), QLineEdit(), QLineEdit()
        self.cb_loai = QComboBox()
        self.cb_loai.setEditable(True)
        self.cb_loai.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for ma, chu in ds_loai:
            self.cb_loai.addItem(chu, ma)
        self.cb_loai.setCurrentIndex(max(0, self.cb_loai.findData('CLN')))
        f.addRow('Hộ:', self.cb_ho)
        f.addRow('Tờ:', self.o_to)
        f.addRow('Thửa:', self.o_thua)
        f.addRow('Loại đất:', self.cb_loai)
        f.addRow('Diện tích (m²):', self.o_dt)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        f.addRow(nut)

    def gia_tri(self) -> tuple:
        chu = self.cb_loai.currentText().strip()
        return self.cb_ho.currentData(), self.o_to.text(), self.o_thua.text(), chu.split()[0] if chu else '', self.o_dt.text()


class _NhanTich(QLabel):
    """Chữ của ô đánh dấu: tự xuống dòng, bấm vào chữ cũng đổi ô. QCheckBox không xuống dòng: chữ dài đẩy cột trái vượt khung, mất nút bên phải."""

    def __init__(self, chu: str, ck: QCheckBox):
        super().__init__(chu)
        self.ck = ck
        self.setWordWrap(True)

    def mouseReleaseEvent(self, e):
        if self.ck.isEnabled():
            self.ck.toggle()
        super().mouseReleaseEvent(e)


def _hang_tich(ck: QCheckBox, chu: str) -> tuple:
    """(widget một dòng: ô đánh dấu + chữ tự xuống dòng, nhãn). Tắt cả dòng bằng widget.setEnabled."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    nhan = _NhanTich(chu, ck)
    ck.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    h.addWidget(ck, 0, Qt.AlignmentFlag.AlignTop)
    h.addWidget(nhan, 1)
    return w, nhan


def _hang_o(*w):
    """Hàng ngang không lề; ô chọn, ô nhập giãn."""
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    for x in w:
        h.addWidget(x, 1 if isinstance(x, (QComboBox, QLineEdit)) else 0)
    return h


class HopTinhGiaDat(QDialog):
    """con: kết nối dự án (None: chỉ tính, không áp). Bảng bên phải luôn có mọi hộ của dự án; ds_ma_ho: hộ đang chọn (phạm vi mặc định, dòng tích sẵn). xa_mac_dinh: tên địa bàn dự án.
    bo_mo: bộ soạn của cửa sổ lập phương án đang mở, hộ đó đọc / ghi qua bộ soạn; dong_tich: chỉ tích sẵn các dòng này của hộ đó; truoc_ap(): False thì hộ đó không ghi được; sau_ap(): cửa sổ vẽ lại;
    thong_so: dict cho dat_thong_so."""
    im_lang = False

    def __init__(self, parent=None, con=None, ds_ma_ho=(), xa_mac_dinh: str = '', chi_doc: bool = False, bo_mo=None, dong_tich=None, truoc_ap=None, sau_ap=None, thong_so=None):
        super().__init__(parent)
        self.con, self.chi_doc = con, bool(chi_doc)
        self.bo_mo, self.truoc_ap, self.sau_ap = bo_mo, truoc_ap, sau_ap
        self.bao_cao = None                      # (tóm tắt, chi tiết) của lần áp gần nhất khi có hộ chuyển nhánh / bị chặn
        self.setWindowTitle(TIEU_DE)
        self.resize(1440, 760)
        self.kq = None
        self.doan = None
        self._tat_ca = None                      # mọi hàng của dự án (đọc lần đầu cần, đọc lại sau khi ghi)
        self._ds_chon = []                       # hộ đang chọn lúc mở
        self._cot_loai = {}                      # loại đất -> cột bảng giá (đếm dòng lệch nhóm đất)
        self.ket_qua_ap = None                   # (số dòng, số hộ) cộng dồn các lần áp trong cửa sổ này
        self.xa_du_an = xa_mac_dinh or ''
        self.goi = gg.goi_du_an(con, self.xa_du_an)
        self._dang_dung = False                  # đang dựng lại theo gói: chưa tính
        lo = QVBoxLayout(self)
        self.lb_tieu_de = QLabel('')
        self.lb_tieu_de.setProperty('vai', 'tieu_de')
        self.lb_tieu_de.setWordWrap(True)
        lo.addWidget(self.lb_tieu_de)
        self._tao_o_nhap(con)
        # ---- hai cột: trái thông số; phải kết quả + các dòng đất (luôn thấy, không phải cuộn)
        hai = QHBoxLayout()
        hai.addWidget(self._dung_cot_thong_so(), 8)    # bảng dòng đất cần đủ 9 cột, thấy Đơn giá mới, Thành tiền mới không phải cuộn ngang
        hai.addLayout(self._dung_cot_ket_qua(), 12)
        lo.addLayout(hai, 1)
        self._dung_khung_can_cu(lo)
        lo.addLayout(self._dung_hang_nut())
        self._noi_tin_hieu()

        self._nap_ds_goi()
        self._dung_theo_goi()
        if not self.goi.get('gan_san'):
            self._gop_can_cu_goi()
        self.nap_dong_dat(list(ds_ma_ho), dong_tich)
        if thong_so:
            self.dat_thong_so(**thong_so)
        self.tra_gia(False)
        self.tinh()

    def _tao_o_nhap(self, con) -> None:
        """Các ô nhập thông số."""
        self.o_can_cu = QPlainTextEdit()
        self.o_can_cu.setPlainText(vb.doc_can_cu_du_an(con))
        self.nut_quet_cc = NutQuetChung('Quét file văn bản căn cứ…', qc.CAN_CU, self)
        self.nut_quet_cc.da_quet.connect(self.sau_khi_quet)
        self.nut_sap = QPushButton('Sắp xếp lại (13 bậc)')
        self.nut_sap.clicked.connect(self.sap_xep_can_cu)
        self.cb_goi = QComboBox()
        self.cb_goi.setToolTip('Văn bản, quy tắc dùng để tính. Có văn bản mới: bấm Bộ quy tắc để nhập, không phải cài lại phần mềm.')
        self.nut_quy_tac = QPushButton('Bộ quy tắc…')
        self.nut_quy_tac.setToolTip('Xem, tạo, nhập gói quy tắc khi có văn bản mới: hệ số, yếu tố ảnh hưởng, công thức, hiệu lực')
        self.nut_quy_tac.clicked.connect(lambda: self.mo_bo_quy_tac())
        self.cb_dia_ban = QComboBox()
        self.cb_nhom = QComboBox()
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm tuyến đường, điểm đầu, điểm cuối (không cần dấu)…')
        self.o_tim.setClearButtonEnabled(True)
        self.cb_doan = QComboBox()
        self.cb_doan.setMaxVisibleItems(18)
        self.cb_vi_tri = QComboBox()
        self.cb_ket_cau = QComboBox()
        for cb in (self.cb_goi, self.cb_dia_ban, self.cb_nhom, self.cb_doan, self.cb_vi_tri, self.cb_ket_cau):   # chữ dài không đẩy cột trái rộng ra; danh sách xổ vẫn rộng đủ chữ
            cb.setMinimumContentsLength(20)
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            cb.currentIndexChanged.connect(lambda *_, c=cb: c.setToolTip(c.currentText()))
        self.o_g = QLineEdit('0')
        self.o_g.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lb_g = QLabel('')
        self.nut_tra = QPushButton('Tra giá')
        self.nut_tra.setToolTip('Điền giá từ bảng giá đất đang dùng: dòng thứ tự vị trí kết nối trong cụm dòng của đoạn đường đã chọn')
        self.nut_tra.clicked.connect(lambda: self.tra_gia(True))
        self.ck_k2 = QCheckBox('')
        self.hang_k2, self.lb_k2 = _hang_tich(self.ck_k2, '')
        self.o_k2 = QLineEdit('1,00')
        self.o_k2.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_k2.setEnabled(False)
        self.ck_pl3 = {}
        self.o_he_so = {}                        # hệ số gói khai báo thêm: mã -> ô nhập
        self.khung_yt = QWidget()                # yếu tố + hệ số thêm của gói, dựng lại khi đổi gói
        self.lo_yt = QVBoxLayout(self.khung_yt)
        self.lo_yt.setContentsMargins(0, 0, 0, 0)
        self._yt_con = None
        self.ck_rieng = QCheckBox('')
        self.hang_rieng, self.lb_rieng = _hang_tich(self.ck_rieng, '')
        self.hang_pl3 = {}
        self.o_khac = QLineEdit('1,00')
        self.o_khac.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_cu_the = QLineEdit('')
        self.o_cu_the.setAlignment(Qt.AlignmentFlag.AlignRight)
        gan_dinh_dang_nghin(self.o_g)
        gan_dinh_dang_nghin(self.o_cu_the)
        self.nut_quet_gd = NutQuetChung('Quét bảng giá', qc.GIA_DAT, self)
        self.nut_quet_gd.setToolTip('Quét văn bản, bảng giá (PDF, ảnh, Word, Excel) để lấy dữ liệu và văn bản căn cứ')
        self.nut_quet_gd.da_quet.connect(self.sau_khi_quet)

    def _dung_cot_thong_so(self) -> QScrollArea:
        """Cột trái: nhóm Thông số trong vùng cuộn."""
        tp = QGroupBox('Thông số')
        f = QFormLayout(tp)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        f.addRow('Văn bản, quy tắc:', _hang_o(self.cb_goi, self.nut_quy_tac))
        # 1.0.69: trường ngắn chung một hàng, hệ số + yếu tố luôn thấy (không còn phần thu gọn)
        def nhan_ngan(chu):
            w = QLabel(chu)
            return w

        def hang_doi(*cap):
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            for nhan, w, gian in cap:
                if nhan:
                    h.addWidget(nhan_ngan(nhan))
                h.addWidget(w, gian)
            return h
        f.addRow('Xã, phường:', hang_doi(('', self.cb_dia_ban, 1), ('Nhóm đất:', self.cb_nhom, 1)))
        f.addRow('Tìm đoạn đường:', self.o_tim)
        f.addRow('Đoạn đường:', self.cb_doan)
        f.addRow('Vị trí kết nối:', hang_doi(('', self.cb_vi_tri, 1), ('Mặt đường:', self.cb_ket_cau, 1)))
        f.addRow('Giá NQ 28 (đ/m²):', hang_doi(('', self.o_g, 1), ('', self.nut_tra, 0), ('', self.nut_quet_gd, 0)))
        f.addRow('', self.lb_g)
        f.addRow('Hệ số K2:', hang_doi(('', self.o_k2, 1), ('K khác:', self.o_khac, 1), ('Giá cụ thể:', self.o_cu_the, 2)))
        luoi_ck = QGridLayout()
        luoi_ck.setContentsMargins(0, 0, 0, 0)
        luoi_ck.addWidget(self.hang_k2, 0, 0)
        luoi_ck.addWidget(self.hang_rieng, 0, 1)
        f.addRow(luoi_ck)
        f.addRow(self.khung_yt)
        self.lb_ap_dung = QLabel('')                      # phần đã thu gọn vẫn phải thấy đang áp gì, vì đổi số tiền
        self.lb_ap_dung.setWordWrap(True)
        f.addRow(self.lb_ap_dung)
        # cột trái cuộn riêng: mở phần "Mở thêm" trên màn hình thấp không đẩy hộp cao hơn màn hình, đơn giá bên phải vẫn thấy
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.Shape.NoFrame)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cuon.setWidget(tp)
        return cuon

    def _dung_cot_ket_qua(self) -> QVBoxLayout:
        """Cột phải: đơn giá kết quả + bảng các dòng đất."""
        phai = QVBoxLayout()
        kqg = QGroupBox('Đơn giá đất bồi thường')
        vq = QVBoxLayout(kqg)
        self.lb_gia = QLabel('')
        f_gia = QFont(self.lb_gia.font())
        f_gia.setPointSizeF(f_gia.pointSizeF() * 1.8)
        f_gia.setBold(True)
        self.lb_gia.setFont(f_gia)
        self.o_can_cu.setMinimumWidth(100)
        self.lb_ct = QLabel('')
        self.lb_ct.setWordWrap(True)
        self.lb_canh_bao = QLabel('')
        self.lb_canh_bao.setWordWrap(True)
        self.o_giai_trinh = QPlainTextEdit()
        self.o_giai_trinh.setReadOnly(True)
        self.o_giai_trinh.setMaximumHeight(120)
        for w in (self.lb_gia, self.lb_ct, self.lb_canh_bao, self.o_giai_trinh):
            vq.addWidget(w)
        self.o_giai_trinh.hide()
        phai.addWidget(kqg)
        self.lb_ho = QLabel('')
        self.lb_ho.setWordWrap(True)
        self.cb_pham_vi = QComboBox()
        self.cb_pham_vi.setMaxVisibleItems(18)
        self.cb_pham_vi.setMinimumContentsLength(20)
        self.cb_pham_vi.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_pham_vi.setToolTip('Hộ hiện trong bảng: cả dự án để áp hàng loạt, các hộ đang chọn ở danh sách hộ, hoặc một hộ')
        self.o_loc = QLineEdit()
        self.o_loc.setPlaceholderText('Lọc: tên chủ hộ, số tờ, số thửa, loại đất (không cần dấu)…')
        self.o_loc.setClearButtonEnabled(True)
        self.nut_chon_het = QPushButton('Chọn tất cả')
        self.nut_chon_het.setToolTip('Tích mọi dòng đang hiện trong bảng')
        self.nut_chon_het.clicked.connect(lambda: self.chon_het(True))
        self.nut_bo_chon = QPushButton('Bỏ chọn')
        self.nut_bo_chon.setToolTip('Bỏ tích các dòng đang hiện')
        self.nut_bo_chon.clicked.connect(lambda: self.chon_het(False))
        self.nut_them_dong = QPushButton('+ Thêm dòng đất cho hộ…')
        self.nut_them_dong.setToolTip('Chọn hộ, nhập Tờ, Thửa, Loại đất, Diện tích: dòng mới được tích sẵn. Thửa chưa có trong hồ sơ hộ thì thêm vào hồ sơ.')
        self.nut_them_dong.clicked.connect(lambda: self.them_dong())
        self.nut_tu_tao = QPushButton('Tự tạo dòng đất từ thông tin Thửa của hộ')
        self.nut_tu_tao.setToolTip('Các hộ trong phạm vi đã có thửa mà mục 1 còn trống: tạo một dòng đất cho mỗi thửa còn DT thu hồi')
        self.nut_tu_tao.clicked.connect(lambda: self.tu_tao_dong())
        self.mo_hinh = _MoHinhDong(self, lambda: self._dat_nut_ap())
        self.bang = _BangDong()
        self.bang.setModel(self.mo_hinh)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setAlternatingRowColors(True)
        self.bang.setWordWrap(False)             # tên dài xem ở chú thích; không để dòng cao thấp khác nhau
        self.bang.setMinimumHeight(90)
        hh = self.bang.horizontalHeader()
        hh.setStretchLastSection(True)
        do = self.bang.fontMetrics()
        for c, mau in RONG_MAU.items():
            self.bang.setColumnWidth(c, do.boundingRect(mau).width() + 22)
        self.bang.setColumnWidth(C_HO, TOI_DA_COT_HO)
        gh = QGroupBox('Các dòng đất của hộ để áp giá')
        vh = QVBoxLayout(gh)
        h_loc = QHBoxLayout()
        h_loc.addWidget(self.cb_pham_vi, 1)
        h_loc.addWidget(self.o_loc, 1)
        vh.addLayout(h_loc)
        xd = XepDong(None, 6)
        for w in (self.nut_chon_het, self.nut_bo_chon, self.nut_them_dong, self.nut_tu_tao):
            xd.addWidget(w)
        vh.addLayout(xd)
        vh.addWidget(self.lb_ho)
        vh.addWidget(self.bang, 1)
        phai.addWidget(gh, 1)
        return phai

    def _dung_khung_can_cu(self, lo) -> None:
        """Phần thu gọn: văn bản căn cứ (mở ra phía trên hàng nút)."""
        self.khung_can_cu = QGroupBox('Văn bản căn cứ (tự sắp theo 13 bậc hiệu lực)')
        vk = QVBoxLayout(self.khung_can_cu)
        vk.addWidget(self.o_can_cu)
        vk.addLayout(_hang_o(self.nut_quet_cc, self.nut_sap))
        vk.itemAt(1).layout().addStretch(1)
        self.o_can_cu.setMaximumHeight(170)
        lo.addWidget(self.khung_can_cu)
        self.khung_can_cu.hide()

    def _dung_hang_nut(self) -> QHBoxLayout:
        """Hàng nút (cố định ở đáy)."""
        def nut_mo(chu):
            b = QPushButton('▸  ' + chu)
            b.setCheckable(True)
            b.toggled.connect(lambda bat, b=b, chu=chu: b.setText(('▾  ' if bat else '▸  ') + chu))
            return b

        hn = QHBoxLayout()
        self.nut_mo_cc = QPushButton('')
        self.nut_mo_cc.setCheckable(True)
        self.nut_mo_cc.toggled.connect(self.khung_can_cu.setVisible)
        self.nut_mo_cc.toggled.connect(lambda *_: self._chu_nut_can_cu())
        self.nut_mo_gt = nut_mo('Nhật ký giải trình')
        self.nut_mo_gt.toggled.connect(self.o_giai_trinh.setVisible)
        hn.addWidget(self.nut_mo_cc)
        hn.addWidget(self.nut_mo_gt)
        self.lb_ap_ket_qua = QLabel('')
        self.lb_ap_ket_qua.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        hn.addWidget(self.lb_ap_ket_qua, 1)
        nut_dong = QPushButton('Đóng')
        nut_dong.clicked.connect(self.reject)
        self.nut_ap = QPushButton('Áp đơn giá vào các dòng đã chọn')
        self.nut_ap.clicked.connect(lambda: self.ap_gia())
        hn.addWidget(nut_dong)
        hn.addWidget(self.nut_ap)
        return hn

    def _noi_tin_hieu(self) -> None:
        self.cb_goi.currentIndexChanged.connect(lambda *_: self.doi_goi(self.cb_goi.currentData()))
        self.cb_dia_ban.currentIndexChanged.connect(lambda *_: self._nap_doan())
        self.o_tim.textChanged.connect(lambda *_: self._nap_doan(giu=True))
        for cb in (self.cb_doan, self.cb_vi_tri, self.cb_nhom):
            cb.currentIndexChanged.connect(lambda *_: self.tra_gia(False))
        for cb in (self.cb_dia_ban, self.cb_doan, self.cb_nhom, self.cb_vi_tri, self.cb_ket_cau):
            cb.currentIndexChanged.connect(lambda *_: self.tinh())
        for e in (self.o_g, self.o_k2, self.o_khac, self.o_cu_the):
            e.textChanged.connect(lambda *_: self.tinh())
        for c in (self.ck_k2, self.ck_rieng):
            c.toggled.connect(lambda *_: self.tinh())
        self.ck_k2.toggled.connect(self.o_k2.setEnabled)
        self.cb_nhom.currentIndexChanged.connect(lambda *_: self._dong_bo_yeu_to())
        self.o_can_cu.installEventFilter(self)
        self._chu_nut_can_cu()
        self.cb_pham_vi.currentIndexChanged.connect(lambda *_: self._doi_pham_vi())
        self.o_loc.textChanged.connect(lambda *_: self._loc())

    # ---------------------------------------------------------------- gói quy tắc
    def _nap_ds_goi(self) -> None:
        self.cb_goi.blockSignals(True)
        self.cb_goi.clear()
        for x in gg.ds_goi():
            self.cb_goi.addItem(gg.nhan_goi(x), x['ma'])
        self.cb_goi.setCurrentIndex(max(0, self.cb_goi.findData(self.goi.get('ma'))))
        self.cb_goi.setToolTip(self.cb_goi.currentText())
        self.cb_goi.blockSignals(False)

    def _dung_theo_goi(self) -> None:
        """Dựng lại ô chọn, yếu tố, nhãn theo gói đang chọn; giữ lựa chọn cũ nếu gói mới vẫn có."""
        goi = self.goi
        mau = dict(gg._gan_san()['cau_chu'], **(goi.get('cau_chu') or {}))
        self._dang_dung = True
        self.lb_tieu_de.setText(f'Bảng tính đơn giá đất bồi thường - {goi["bang_gia"]} và {goi["so_hieu"]}')

        def nap(cb, ds, cu):
            cb.blockSignals(True)
            cb.clear()
            for chu, gt in ds:
                cb.addItem(chu, gt)
            cb.setCurrentIndex(max(0, cb.findData(cu)))
            cb.setToolTip(cb.currentText())
            cb.blockSignals(False)

        xa_cu = g.ten_ngan(self.cb_dia_ban.currentData() or '') or self.xa_du_an
        k = g.dia_ban_theo_ten(xa_cu, goi)
        nap(self.cb_dia_ban, [(g.ten_ngan(x), x) for x in g.ds_dia_ban(goi)], k)
        nap(self.cb_nhom, [(x['ten'], f'{x["ma"]}|{x["cot_gia"]}') for x in goi['nhom_dat']], self.cb_nhom.currentData())
        nap(self.cb_vi_tri, [(x['ten'], x['ma']) for x in goi['vi_tri']], self.cb_vi_tri.currentData())
        nap(self.cb_ket_cau, [(x['ten'], x['ma']) for x in goi['ket_cau']], self.cb_ket_cau.currentData())
        self.lb_k2.setText(mau['nhan_k2'])
        self.lb_rieng.setText(mau['nhan_rieng'])
        co_ct = bool((goi.get('chuyen_tiep') or {}).get('bat'))
        self.o_cu_the.setEnabled(co_ct)
        self.o_cu_the.setPlaceholderText(mau['nhan_cu_the'] if co_ct else 'Văn bản này không có quy định chuyển tiếp')

        moi = QWidget()                                   # thay cả khung chứa, không gỡ từng dòng khỏi bố cục
        ngoai = QVBoxLayout(moi)
        ngoai.setContentsMargins(0, 0, 0, 0)
        luoi = QGridLayout()
        luoi.setContentsMargins(0, 0, 0, 0)
        ngoai.addLayout(luoi)
        lo = QFormLayout()
        ngoai.addLayout(lo)
        cu_chon = {m for m, c in self.ck_pl3.items() if c.isChecked()}
        self.ck_pl3, self.o_he_so, self.hang_pl3 = {}, {}, {}
        for vt_y, y in enumerate(goi.get('yeu_to', ())):
            c = QCheckBox('')
            c.setChecked(y['ma'] in cu_chon)
            c.toggled.connect(lambda *_: self.tinh())
            hang_y, _ = _hang_tich(c, y['ten'])
            luoi.addWidget(hang_y, vt_y // 2, vt_y % 2)
            self.ck_pl3[y['ma']] = c
            self.hang_pl3[y['ma']] = hang_y
        for x in goi.get('he_so_them') or ():
            e = QLineEdit(str(x.get('mac_dinh', 1)).replace('.', ','))
            e.setAlignment(Qt.AlignmentFlag.AlignRight)
            e.setToolTip(x.get('can_cu', ''))
            e.textChanged.connect(lambda *_: self.tinh())
            lo.addRow(f'{x.get("ten") or x["ma"]} ({x["ma"]}):', e)
            self.o_he_so[x['ma']] = e
        if self._yt_con is not None:
            self.lo_yt.removeWidget(self._yt_con)
            self._yt_con.hide()
            self._yt_con.deleteLater()
        self.lo_yt.addWidget(moi)
        self._yt_con = moi
        self._dang_dung = False
        self._dong_bo_yeu_to()
        self._nap_doan()

    def doi_goi(self, ma) -> None:
        """Người dùng chọn gói khác: dựng lại, gộp văn bản căn cứ của gói vào danh sách."""
        x = gg.lay_goi(ma or '')
        if x is None or x.get('ma') == self.goi.get('ma'):
            return
        self.goi = x
        self._gop_can_cu_goi()
        self._dung_theo_goi()

    def _gop_can_cu_goi(self) -> None:
        if self.goi.get('van_ban_can_cu'):
            self.o_can_cu.setPlainText(vb.gop_va_sap_xep([self.o_can_cu.toPlainText()], list(self.goi['van_ban_can_cu']))[0])
            self._chu_nut_can_cu()

    def mo_bo_quy_tac(self):
        from .man_hinh_goi_gia_dat import HopGoiGiaDat
        h = HopGoiGiaDat(self, self.goi.get('ma', ''))
        h.im_lang = self.im_lang
        if self.im_lang:
            return h
        h.exec()
        if h.da_doi:
            self.lam_moi_goi()
        return h

    def lam_moi_goi(self) -> None:
        """Sau khi sửa bộ quy tắc: đọc lại danh sách; gói đang dùng đã bị xóa thì về gói theo ngày."""
        x = gg.lay_goi(self.goi.get('ma', '')) or gg.chon_goi(None, self.xa_du_an)
        self.goi = x
        self._nap_ds_goi()
        self._dung_theo_goi()

    # ---------------------------------------------------------------- văn bản căn cứ
    def eventFilter(self, obj, e):
        from PySide6.QtCore import QEvent
        if obj is self.o_can_cu and e.type() == QEvent.Type.FocusOut:
            self.sap_xep_can_cu()
        return False

    def sap_xep_can_cu(self) -> None:
        self.o_can_cu.setPlainText(vb.gop_va_sap_xep([self.o_can_cu.toPlainText()])[0])
        self._chu_nut_can_cu()

    def _chu_nut_can_cu(self) -> None:
        n = len(vb.gop_va_sap_xep([self.o_can_cu.toPlainText()])[1])
        self.nut_mo_cc.setText(('▾' if self.nut_mo_cc.isChecked() else '▸') + f'  Văn bản căn cứ ({n} văn bản, đã sắp 13 bậc)')

    # ---------------------------------------------------------------- chọn đoạn đường / nhóm đất
    def _nap_doan(self, giu: bool = False) -> None:
        ma_cu = self.cb_doan.currentData() if giu else None
        from .lap_pa import bo_dau
        khoa = bo_dau(self.o_tim.text()).split()
        ds = [r for r in g.ds_doan(self.cb_dia_ban.currentData() or '', self.goi)
              if all(k in bo_dau(f'{r["ten_duong"]} {r["diem_dau"]} {r["diem_cuoi"]}') for k in khoa)]
        self.cb_doan.blockSignals(True)
        self.cb_doan.clear()
        for r in ds:
            self.cb_doan.addItem(g.nhan_doan(r), r['ma_doan_duong'])
        k = self.cb_doan.findData(ma_cu) if ma_cu else 0
        self.cb_doan.setCurrentIndex(max(0, k))
        self.cb_doan.blockSignals(False)
        self.tra_gia(False)
        self.tinh()

    def _dong_bo_yeu_to(self) -> None:
        """Yếu tố ảnh hưởng chỉ chọn được đúng nhóm đất của gói (ap_cho: nn / pnn / ca)."""
        n = g.nhom_cua(self.goi, *self.nhom_cot())
        nhom_nay = 'nn' if n and n.get('la_nong_nghiep') else 'pnn'
        for y in self.goi.get('yeu_to', ()):
            c = self.ck_pl3[y['ma']]
            dung = y['ap_cho'] in (nhom_nay, 'ca')
            self.hang_pl3[y['ma']].setEnabled(dung)
            if not dung:
                c.setChecked(False)

    def nhom_cot(self) -> tuple:
        """(nhóm đất QĐ 03, cột bảng giá NQ 28) của mục đang chọn - dữ liệu mục là chuỗi 'nhóm|cột' (tuple không qua được QVariant của Qt5)."""
        return tuple((self.cb_nhom.currentData() or 'DAT_NONG_NGHIEP|nn_cay').split('|'))

    def doan_hien_tai(self):
        return g.tim_doan(self.cb_dia_ban.currentData() or '', self.cb_doan.currentData() or '', self.goi)

    def tra_gia(self, thong_bao: bool = False) -> None:
        """Điền giá từ bảng giá đất đang dùng; không có dòng khớp thì giữ số người dùng nhập."""
        if self._dang_dung:
            return
        nhom, cot = self.nhom_cot()
        gia = g.gia_bang_gia(self.cb_dia_ban.currentData() or '', self.doan_hien_tai(), nhom, self.cb_vi_tri.currentData() or '', cot, self.goi)
        if gia is not None:
            self.o_g.setText(vn(gia))
            self.lb_g.setText(f'Tự tra từ bảng giá {self.goi["bang_gia"]}')
        else:
            self.lb_g.setText('Nhập tay: bảng giá không có dòng khớp')
            if thong_bao and not self.im_lang:
                QMessageBox.information(self, TIEU_DE, 'Bảng giá đất đang dùng không có dòng khớp đoạn đường / vị trí này: nhập đơn giá bằng tay.')

    # ---------------------------------------------------------------- tính
    def dau_vao(self) -> g.DauVao:
        nhom, cot = self.nhom_cot()
        cu_the = self.o_cu_the.text().strip()
        return g.DauVao(
            dia_ban=self.cb_dia_ban.currentData() or '', nhom_dat=nhom, ma_doan_duong=self.cb_doan.currentData() or '',
            loai_ket_noi_vi_tri=self.cb_vi_tri.currentData() or 'MAT_TIEN_VT1', ket_cau_mat_duong=self.cb_ket_cau.currentData() or 'NHUA_BETONG',
            don_gia_bang_gia=doc_so(self.o_g.text(), 'Đơn giá bảng giá'), cot_gia=cot,
            ap_dung_quy_hoach_pl2=self.ck_k2.isChecked(), he_so_quy_hoach_k2=doc_so(self.o_k2.text(), 'Hệ số K2') or D(1),
            yeu_to_pl3=[m for m, c in self.ck_pl3.items() if c.isChecked() and c.isEnabled()],
            he_so_khac=doc_so(self.o_khac.text(), 'Hệ số khác') or D(1),
            gia_dat_cu_the=doc_so(cu_the, 'Giá đất cụ thể') if cu_the else D(0),
            co_quy_dinh_rieng_duong_dat_pl1=self.ck_rieng.isChecked(),
            he_so_them={m: doc_so(e.text(), m) for m, e in self.o_he_so.items() if e.text().strip()})

    def tinh(self):
        if self._dang_dung:
            return None
        try:
            v = self.dau_vao()
        except LoiNhap as e:
            self.kq = None
            self.lb_gia.setText('Chưa tính được')
            self.lb_ap_dung.setText('')
            self.lb_ct.setText(str(e))
            self._ve_gia_moi()                       # không để số cũ ở cột Đơn giá mới khi ô nhập đang sai
            self._dat_nut_ap()
            return None
        self.doan = self.doan_hien_tai()
        self.kq = g.tinh_don_gia(v, self.doan, self.goi)
        k = self.kq
        self.lb_gia.setText(f'{vn(k.don_gia_ap_dung)} đ/m²')
        cu_the = self.o_cu_the.text().strip()
        self.lb_ap_dung.setText(f'Đang áp dụng: K1 = {g.he_hien(k.k1)} · K2 = {g.he_hien(k.k2)} · K3 = {g.he_hien(k.k3)} · K khác = {g.he_hien(k.k_khac)}'
                                + ''.join(f' · {m} = {g.he_hien(x)}' for m, x in k.he_so_them.items())
                                + (f' · K1 theo bảng đã nhập ({k.nguon_k1})' if k.nguon_k1 else '')
                                + (f' · giá cụ thể {vn(D(v.gia_dat_cu_the))} đ/m²' + (' (đang dùng)' if k.ap_dung_chuyen_tiep else ' (thấp hơn, không dùng)') if cu_the else ''))
        self.lb_gia.setToolTip('\n'.join(k.buoc_lap_luan))
        self.lb_ct.setText('Công thức: ' + k.cong_thuc)
        self.lb_canh_bao.setText('\n'.join('! ' + c for c in gg.canh_bao_goi(self.goi, self.xa_du_an) + k.canh_bao))
        self.o_giai_trinh.setPlainText('\n'.join(k.buoc_lap_luan))
        self._ve_gia_moi()
        self._dat_nut_ap()
        return k

    # ---------------------------------------------------------------- quét
    def sau_khi_quet(self, kq: qc.KetQuaQuet) -> None:
        """Kết quả quét: văn bản căn cứ gộp + sắp 13 bậc; thông số (địa bàn, mặt đường, yếu tố Phụ lục III) điền vào ô."""
        if kq.can_cu:
            self.o_can_cu.setPlainText(vb.gop_va_sap_xep([self.o_can_cu.toPlainText()], kq.can_cu)[0])
            self._chu_nut_can_cu()
        ts = kq.tham_so or {}
        k_xa = g.dia_ban_theo_ten(g.ten_ngan(ts.get('dia_ban') or ''), self.goi)
        if k_xa:
            self.cb_dia_ban.setCurrentIndex(self.cb_dia_ban.findData(k_xa))
        if ts.get('ket_cau_mat_duong'):
            self.cb_ket_cau.setCurrentIndex(max(0, self.cb_ket_cau.findData(ts['ket_cau_mat_duong'])))
        for m in ts.get('yeu_to_pl3', ()):
            if m in self.ck_pl3 and self.ck_pl3[m].isEnabled():
                self.ck_pl3[m].setChecked(True)
        self.tinh()

    # ---------------------------------------------------------------- dòng đất của hộ
    def dat_thong_so(self, dia_ban=None, ma_doan=None, vi_tri=None, ket_cau=None, loai_dat=None) -> None:
        """Điền sẵn thông số (mở từ thanh áp giá nhanh, theo dòng đất đang thao tác). Giá trị gói không có thì bỏ qua."""
        for cb, gt in ((self.cb_dia_ban, dia_ban), (self.cb_doan, ma_doan), (self.cb_vi_tri, vi_tri), (self.cb_ket_cau, ket_cau)):
            k = cb.findData(gt) if gt else -1
            if k >= 0:
                cb.setCurrentIndex(k)
        n = g.nhom_theo_loai_dat(loai_dat, self.goi) if loai_dat else None
        if n is not None:
            self.cb_nhom.setCurrentIndex(max(0, self.cb_nhom.findData(f'{n["ma"]}|{n["cot_gia"]}')))

    def nap_dong_dat(self, ds_ma_ho: list, dong_tich=None) -> None:
        """Nạp bảng theo hộ đang chọn: chưa chọn hộ thì phạm vi cả dự án (không tích sẵn dòng nào: áp nhầm cả dự án sẽ khó sửa), có thì tích sẵn dòng của các hộ đó."""
        self._ds_chon = [int(m) for m in ds_ma_ho]
        co = self.con is not None
        for w in (self.cb_pham_vi, self.o_loc, self.nut_chon_het, self.nut_bo_chon):
            w.setEnabled(co)
        for w in (self.nut_them_dong, self.nut_tu_tao):
            w.setEnabled(co and not self.chi_doc)
        self.mo_hinh.tich = set()
        if not co:
            self.lb_ho.setText('Chưa mở dự án: bảng chỉ để tính. Mở dự án để áp đơn giá vào dòng đất của các hộ.')
            return
        self.mo_hinh.lamtron = BoiCanh.tu(self.con).lamtron
        self.cb_pham_vi.blockSignals(True)
        self.cb_pham_vi.clear()
        self.cb_pham_vi.addItem('Tất cả hộ trong dự án (áp giá hàng loạt)', TAT_CA)
        if self._ds_chon:
            self.cb_pham_vi.addItem(f'Chỉ hộ đang chọn ({len(self._ds_chon)} hộ)', DANG_CHON)
        self._ds_ho = [(r[0], r[1] or '') for r in self.con.execute('SELECT ma_ho, ho_ten FROM ho ORDER BY thu_tu, ma_ho')]
        for ma, ten in self._ds_ho:
            self.cb_pham_vi.addItem(f'{ma} - {ten}', ma)
        mac_dinh = self._ds_chon[0] if self.bo_mo is not None and len(self._ds_chon) == 1 else (DANG_CHON if self._ds_chon else TAT_CA)
        self.cb_pham_vi.setCurrentIndex(max(0, self.cb_pham_vi.findData(mac_dinh)))
        self.cb_pham_vi.blockSignals(False)
        self._tat_ca = None
        hang = self._hang_pham_vi()
        tich = None if dong_tich is None else set(dong_tich)
        self.mo_hinh.tich = {x.khoa for x in hang if x.chi_so != ap.CO_CHUA_DONG and x.ma_ho in self._ds_chon and (tich is None or x.chi_so in tich)}
        self._loc()
        loai = next((x.loai_dat for x in hang if x.khoa in self.mo_hinh.tich), '')
        if loai:
            self.dat_thong_so(loai_dat=loai)

    def _hang_pham_vi(self) -> list:
        """Các hàng của phạm vi đang chọn; phạm vi nhỏ không đọc cả dự án."""
        pv = self.cb_pham_vi.currentData()
        if pv == TAT_CA and self._tat_ca is None:
            self._tat_ca = ap.doc_dong(self.con, None, self.bo_mo)
        if pv == TAT_CA:
            return self._tat_ca
        ds = set(self._ds_chon) if pv == DANG_CHON else {pv}
        if self._tat_ca is not None:
            return [x for x in self._tat_ca if x.ma_ho in ds]
        return ap.doc_dong(self.con, ds, self.bo_mo)

    def _doi_pham_vi(self) -> None:
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            self._loc()
        finally:
            self.unsetCursor()

    def _loc(self) -> None:
        """Hiện các hàng của phạm vi khớp ô lọc (mọi từ, không dấu)."""
        if self.con is None or self.cb_pham_vi.count() == 0:
            return
        from .lap_pa import bo_dau
        khoa = bo_dau(self.o_loc.text()).split()
        hang = self._hang_pham_vi()
        ds = [x for x in hang if all(k in x.tim for k in khoa)] if khoa else list(hang)
        self.mo_hinh.dat_dong(ds)
        self.bang.setColumnHidden(C_HO, len({x.ma_ho for x in ds}) <= 1)
        self._ve_gia_moi()
        self._dat_nut_ap()

    def _lam_moi_dong(self) -> None:
        """Đọc lại sau khi ghi: giá hiện tại, phiên bản ghi vào, dòng mới."""
        self._tat_ca = None
        self._loc()

    def chon_het(self, bat: bool) -> None:
        self.mo_hinh.doi_tich(self.mo_hinh.dong, bat)

    def _ve_gia_moi(self) -> None:
        self.mo_hinh.dat_gia(self.kq.don_gia_ap_dung if self.kq is not None else None)

    def dong_da_chon(self) -> list:
        """Các hàng đang HIỆN và đã tích: dòng bị ô lọc che không áp (thấy gì áp nấy)."""
        t = self.mo_hinh.tich
        return [x for x in self.mo_hinh.dong if x.khoa in t]

    def _lech_nhom(self, ds: list) -> list:
        """Dòng đã tích có loại đất thuộc nhóm khác nhóm đang tính (đơn giá theo nhóm đất: áp nhầm là sai số tiền)."""
        from . import gia_dat_nq28 as nq
        cot = self.nhom_cot()[1]
        kq = []
        for x in ds:
            if x.loai_dat not in self._cot_loai:
                self._cot_loai[x.loai_dat] = nq.cot_cua_loai(x.loai_dat)
            c = self._cot_loai[x.loai_dat]
            if c and c != cot:
                kq.append(x)
        return kq

    def _dat_nut_ap(self) -> None:
        chon = self.dong_da_chon()
        n = len(chon)
        ok = self.kq is not None and self.con is not None and not self.chi_doc and n > 0 and self.kq.don_gia_ap_dung > 0
        self.nut_ap.setEnabled(ok)
        self.nut_ap.setText(f'Áp đơn giá vào {n} dòng đã chọn' if n else 'Áp đơn giá vào các dòng đã chọn')
        self.nut_ap.setToolTip('' if ok else 'Cần: mở dự án (không ở chế độ chỉ xem), tích ít nhất một dòng đất và đơn giá lớn hơn 0.')
        if self.con is None:
            return
        hien = self.mo_hinh.dong
        so_ho = len({x.ma_ho for x in hien})
        so_dong = sum(1 for x in hien if x.chi_so != ap.CO_CHUA_DONG)
        chu = f'{so_ho} hộ, {so_dong} dòng đất đang hiện, đã tích {n} dòng.'
        an = len(self.mo_hinh.tich) - n
        if an > 0:
            chu += f' {an} dòng đã tích đang bị che, không áp.'
        trong = so_ho - len({x.ma_ho for x in hien if x.chi_so != ap.CO_CHUA_DONG})
        if trong:
            chu += f' {trong} hộ chưa có dòng đất.'
        lech = len(self._lech_nhom(chon))
        if lech:
            chu += f' ! {lech} dòng có loại đất khác nhóm đất đang tính.'
        self.lb_ho.setText(chu)

    def ap_gia(self, xac_nhan: bool | None = None) -> tuple:
        """Áp đơn giá vào các dòng đã tích: mỗi hộ một lần lưu; hộ có V1 ghi vào nhánh V2. Trả (số dòng, số hộ, danh sách lỗi). xac_nhan=True: không hỏi."""
        if self.kq is None or self.con is None:
            return 0, 0, []
        chon = self.dong_da_chon()
        if not chon:
            return 0, 0, []
        if xac_nhan is None and not self.im_lang:
            lech = len(self._lech_nhom(chon))
            hoi = f'Áp đơn giá {vn(self.kq.don_gia_ap_dung)} đ/m² vào {len(chon)} dòng đất của {len({x.ma_ho for x in chon})} hộ?'
            if lech:
                hoi += f'\n\n{lech} dòng có loại đất khác nhóm đất đang tính ({self.cb_nhom.currentText()}).'
            if QMessageBox.question(self, TIEU_DE, hoi) != QMessageBox.StandardButton.Yes:
                return 0, 0, []
        gc = g.ghi_chu_ap_gia(self.kq, self.doan, g.ten_ngan(self.cb_dia_ban.currentData() or ''))
        vt = g.mo_ta_vi_tri(self.doan, self.cb_vi_tri.currentData() or '', self.goi)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        tien_do = self._hop_tien_do(len({x.ma_ho for x in chon}))
        try:
            kq = ap.ap_hang_loat(self.con, chon, self.kq.don_gia_ap_dung, gc, vt, self.bo_mo, self.truoc_ap, tien_do, g.chi_tiet_ap_gia(self.kq))
            if kq.so_dong:
                cb = ap.gop_can_cu(self.con, self.goi, self.o_can_cu.toPlainText())
                if cb:
                    kq.canh_bao.append(cb)
                self.o_can_cu.setPlainText(vb.doc_can_cu_du_an(self.con))
                self._chu_nut_can_cu()
        finally:
            QApplication.restoreOverrideCursor()
            if tien_do is not None:
                self.findChild(QProgressDialog).deleteLater()
        cu = self.ket_qua_ap or (0, 0)
        self.ket_qua_ap = (cu[0] + kq.so_dong, cu[1] + kq.so_ho)
        if kq.so_dong and self.sau_ap is not None and self.bo_mo is not None and any(x.ma_ho == self.bo_mo.ma_ho for x in chon):
            self.sau_ap()
        self._bao_ket_qua(kq)
        if self.bo_mo is not None and kq.so_dong and not kq.bi_chan:
            self.accept()                                                # mở từ phương án một hộ: trở về bảng Đất vừa cập nhật
        else:
            self.mo_hinh.tich -= {x.khoa for x in chon if not any(c.startswith(f'Hộ {x.ma_ho} ') for c in kq.bi_chan)}
            self._lam_moi_dong()
        return kq.so_dong, kq.so_ho, kq.bi_chan

    def _hop_tien_do(self, so_ho: int):
        """Áp nhiều hộ (mỗi hộ một lần ghi file): hộp tiến độ có nút Dừng, cửa sổ không bị báo Không phản hồi. Ít hộ: không cần."""
        if so_ho < HO_CAN_TIEN_DO or self.im_lang:
            return None
        hop = QProgressDialog('Đang áp đơn giá vào dòng đất của các hộ…', 'Dừng', 0, so_ho, self)
        hop.setWindowTitle(TIEU_DE)
        hop.setWindowModality(Qt.WindowModality.WindowModal)
        hop.setMinimumDuration(400)

        def bao(k, n):
            hop.setValue(k)                                              # setValue của hộp modal tự xử lý sự kiện
            return hop.wasCanceled()
        return bao

    def _bao_ket_qua(self, kq) -> None:
        """Mọi hộ ghi bình thường: một câu ở nhãn. Có hộ chuyển nhánh V2 / bị chặn: danh sách đầy đủ trong hop_ket_qua (không ghép vào QMessageBox)."""
        tom_tat = f'Đã áp đơn giá {vn(self.kq.don_gia_ap_dung)} đ/m² cho {kq.so_dong} dòng đất của {kq.so_ho} hộ.'
        self.lb_ap_ket_qua.setText(tom_tat)
        ct = [f'Hộ {m}: V1 đã niêm yết giữ nguyên, ghi vào nhánh {v}.' for m, v in kq.nhanh.items()] + [f'Không áp được: {c}' for c in kq.bi_chan] + kq.canh_bao + \
             [f'Tính lại hỗ trợ: {c}' for c in kq.ho_tro]
        self.bao_cao = (tom_tat, ct) if kq.nhanh or kq.bi_chan or kq.canh_bao or kq.ho_tro else None
        if self.bao_cao and not self.im_lang:
            hop_ket_qua(self, tom_tat, ct, 'Chi tiết', canh_bao=bool(kq.bi_chan), tieu_de=TIEU_DE)

    # ---------------------------------------------------------------- thêm / tự tạo dòng đất
    def _ma_ho_goi_y(self):
        chi_so = self.bang.currentIndex()
        if chi_so.isValid() and chi_so.row() < len(self.mo_hinh.dong):
            return self.mo_hinh.dong[chi_so.row()].ma_ho
        pv = self.cb_pham_vi.currentData()
        return pv if isinstance(pv, int) else (self._ds_chon[0] if self._ds_chon else None)

    def them_dong(self, gia_tri=None):
        """gia_tri: (mã hộ, tờ, thửa, loại đất, DT) cho sẵn (kiểm thử), không thì hỏi. Trả DongGia vừa thêm hoặc None."""
        if self.con is None or self.chi_doc:
            return None
        if gia_tri is None:
            from .loai_dat import ds_chon
            h = HopThemDongDat(self, self._ds_ho, self._ma_ho_goi_y(), ds_chon(self.con))
            h.im_lang = self.im_lang
            if self.im_lang:
                return h
            ok = h.exec() == QDialog.DialogCode.Accepted
            gia_tri = h.gia_tri()
            h.deleteLater()
            if not ok:
                return None
        try:
            dong, nhanh = ap.them_dong_dat(self.con, *gia_tri, bo_mo=self.bo_mo)
        except LoiNhap as e:
            self._bao_loi(str(e))
            return None
        self.mo_hinh.tich.add(dong.khoa)
        pv = self.cb_pham_vi.currentData()
        if pv != TAT_CA and pv != dong.ma_ho and not (pv == DANG_CHON and dong.ma_ho in self._ds_chon):
            self.cb_pham_vi.setCurrentIndex(max(0, self.cb_pham_vi.findData(dong.ma_ho)))
        self.o_loc.blockSignals(True)
        self.o_loc.clear()
        self.o_loc.blockSignals(False)
        self._lam_moi_dong()
        if self.bo_mo is not None and dong.ma_ho == self.bo_mo.ma_ho and self.sau_ap is not None:
            self.sau_ap()
        self.lb_ap_ket_qua.setText(f'Đã thêm {dong.ten_thua} cho hộ {dong.ma_ho}' + (f', ghi vào {nhanh} (V1 giữ nguyên).' if nhanh else '.'))
        return dong

    def _bao_loi(self, chu: str) -> None:
        self.lb_ap_ket_qua.setText(chu)
        if not self.im_lang:
            QMessageBox.warning(self, TIEU_DE, chu)

    def tu_tao_dong(self, xac_nhan: bool | None = None) -> tuple:
        """Hộ trong phạm vi có thửa mà mục 1 còn trống: tạo dòng đất, tích sẵn. Trả (số hộ, số dòng, [cảnh báo])."""
        if self.con is None or self.chi_doc:
            return 0, 0, []
        trong = sorted({x.ma_ho for x in self._hang_pham_vi() if x.chi_so == ap.CO_CHUA_DONG and x.so_thua_ho})
        if not trong:
            self.lb_ap_ket_qua.setText('Trong phạm vi này không có hộ nào có thửa mà mục 1 còn trống.')
            return 0, 0, []
        if xac_nhan is None and not self.im_lang and len(trong) > 1:
            if QMessageBox.question(self, TIEU_DE, f'Tạo dòng đất từ thông tin thửa cho {len(trong)} hộ chưa có dòng đất?') != QMessageBox.StandardButton.Yes:
                return 0, 0, []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            so_ho, so_dong, cb = ap.tao_dong_tu_thua(self.con, trong, self.bo_mo)
        finally:
            QApplication.restoreOverrideCursor()
        self._lam_moi_dong()
        tao = set(trong)
        self.mo_hinh.doi_tich([x for x in self.mo_hinh.dong if x.ma_ho in tao], True)
        if self.bo_mo is not None and self.bo_mo.ma_ho in tao and self.sau_ap is not None:
            self.sau_ap()
        tom_tat = f'Đã tạo {so_dong} dòng đất cho {so_ho} hộ.'
        self.lb_ap_ket_qua.setText(tom_tat)
        if cb and not self.im_lang:
            hop_ket_qua(self, tom_tat, cb, 'Cần xem lại', canh_bao=True, tieu_de=TIEU_DE)
        return so_ho, so_dong, cb
