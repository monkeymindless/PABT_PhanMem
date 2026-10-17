"""Màn hình theo dõi (0.9.12): Bảng tổng hợp kinh phí (0.9.76: 3 thẻ - cơ cấu kinh phí dự án, bảng kinh phí chi tiết từng hộ, đối
soát với bảng khái toán Pre-F/S), Quyết định phê duyệt (trang riêng: danh sách quyết định + các hộ của quyết định), Theo dõi
tiến độ (chi trả theo từng quyết định, bàn giao mặt bằng, lý do chưa nhận / chưa bàn giao, biên lai; 0.9.76: mốc thu hồi đất
60 / 120 ngày, sổ nhật ký vận động 10 ngày, cưỡng chế Điều 89), hộp thoại quyết định của một hộ. Logic ở theo_doi.py,
kinh_phi_du_an.py, van_dong.py, thoi_han.py; các hàm thao tác nhận tham số để kiểm thử (im_lang = True: không hiện hộp thông báo
/ hộp hỏi).

Bốn trang danh sách dùng bảng ảo (bang_ao.BangAo) - 0.9.22: thẻ Quyết định và Tổng hợp tiền chuyển từ QTableWidget (3.000 hộ:
nạp 1,7 s / 0,6 s). Mã dùng chung của các trang ở _Khung (mở hộ khi nhấp đúp, hộ đang chọn, ghi xong -> nạp lại + báo cửa sổ chính,
xuất Excel có bắt lỗi ghi file).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
                               QButtonGroup, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import ho_so_scan, kinh_phi_du_an, thoi_han, theo_doi, van_dong
from .bang_ao import BangAo
from .giao_dien import XepDong, dat_trang_thai, vua_dong, loc_khi_ngung_go
from .lap_pa import LoiNhap, bo_dau
from .thong_bao import THE_TONG_HOP, chu_loi
from .tien import D, KHONG, so_vn, vn

TIEU_DE = 'Theo dõi phê duyệt, chi trả, bàn giao'
XANH, VANG, DO, XAM = QColor('#E2EFDA'), QColor('#FFF2CC'), QColor('#F8CBAD'), QColor('#F2F4F7')
MAU_LIEN_KET = QColor('#0B5CAD')                          # chữ ô bấm đúp mở được file (biên lai, chứng từ)
CHO_GO_MS = 200                                           # ô tìm: chờ ngừng gõ bấy nhiêu ms mới lọc (như OTimKiemThongMinh)
DO_MAU = 300                                              # số dòng Qt đo khi tự canh bề rộng cột (bảng QTableWidget của hộp thoại)
THUA_TRONG = dict(so_to='', so_thua='', dt_thu_hoi='', loai_dat='')     # hộ chưa có thửa: vẫn một dòng
# 1.0.02 (Hybrid Enterprise Navy): dòng nổi của Cơ cấu kinh phí / Đối soát - (nền, chữ). Cộng bồi thường = slate; kinh phí tổ chức
# thực hiện = hổ phách nhạt; TỔNG KINH PHÍ = xanh băng chữ navy đậm (như dải cộng danh sách hộ)
DONG_NOI = {'cong': (QColor('#F1F5F9'), QColor('#0F172A')), 'kinh_phi': (QColor('#FFFBEB'), QColor('#92400E')),
            'tong': (QColor('#F0F6FF'), QColor('#0F3866'))}
CAO_O_CONG_CU = 30                                       # ô tìm / nút Xuất / Mốc pháp lý của các trang theo dõi
_DAM = dict(dam=True)                                     # kiểu ô chữ đậm (bảng ảo, dùng chung - chỉ đọc)


def _tien(v) -> str:
    s = str(v if v is not None else '').strip()
    return vn(s) if s else ''


def _so(v):
    s = str(v or '').strip()
    return D(s) if s else KHONG


def _so_hoac_trong(v):
    """Số của ô lưu TEXT; ô trống / NULL -> None (hiện trống, khác 0)."""
    return D(str(v).strip()) if v is not None and str(v).strip() else None


def mo_file(p) -> None:
    from .in_an import mo_file as _mo
    if p and Path(p).exists():
        _mo(p)


def _bao(self, chu: str, loi: bool = True) -> None:
    if not self.im_lang:
        (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)


def _hoi(self, chu: str) -> bool:
    return self.im_lang or QMessageBox.question(self, TIEU_DE, chu) == QMessageBox.StandardButton.Yes


class _Hop(QDialog):
    im_lang = False
    bao, hoi = _bao, _hoi


class _Khung(QWidget):
    """Khung nhúng trong cửa sổ chính; da_doi phát ra khi đã ghi CSDL (cửa sổ chính tải lại danh sách hộ); mo_ho(mã) khi nhấp đúp
    một hộ (cửa sổ chính mở quyết định, chi trả, bàn giao của hộ)."""
    da_doi = Signal()
    mo_ho = Signal(int)
    im_lang = False
    bao, hoi = _bao, _hoi

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc = con, chi_doc

    def dat_du_an(self, con, chi_doc: bool = False):
        self.con, self.chi_doc = con, chi_doc
        self.nap()

    def nap(self):
        pass

    def ma_da_chon(self) -> list:
        """Mã hộ các dòng đang chọn trên bảng của trang. Cửa sổ chính dùng khi đang xem trang này: lệnh menu trái (Lập phương án,
        Trạng thái hộ, Đợt trình, In / Xuất, Xóa hộ) tác động đúng hộ đang chọn trên màn hình."""
        b = getattr(self, 'bang', None)
        return b.ma_da_chon() if b is not None else []

    def _mo_ho_dong(self, r: int, c: int = 0):
        ma = self.bang.ma_dong(r)
        if ma is not None:
            self.mo_ho.emit(int(ma))

    def _da_ghi(self, kq=None):
        """Sau khi ghi CSDL: nạp lại trang, báo cửa sổ chính tải lại; trả kq."""
        self.nap()
        self.da_doi.emit()
        return kq

    def _ten_du_an(self) -> str:
        r = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        return (r[0] or '') if r else ''

    def _xuat(self, file, tieu_de_hop: str, ten_file: str, ghi):
        """Hỏi nơi lưu (file None) rồi ghi(file) -> đường dẫn; lỗi ghi file (đang mở trong Excel, không có quyền) báo dễ hiểu
        (trước 0.9.22 trang Tổng hợp tiền / Tiến độ chưa bắt lỗi này); xong mở file."""
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, tieu_de_hop, ten_file, 'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            p = ghi(file)
        except OSError as e:
            self.bao(chu_loi('Không ghi được file', e))
            return None
        if not self.im_lang:
            mo_file(p)
        return p

    def _tim_khi_go(self):
        """Ô tìm: chờ ngừng gõ ~0,3 giây mới lọc / vẽ lại (3.000 hộ: gõ từng phím mà vẽ lại ngay thì giật)."""
        if self.im_lang:
            self.ve()
            return
        t = getattr(self, '_hen_tim', None)
        if t is None:
            t = self._hen_tim = QTimer(self)
            t.setSingleShot(True)
            t.setInterval(CHO_GO_MS)
            t.timeout.connect(self.ve)
        t.start()

    def _loc_nho(self, khoa, ham) -> list:
        """Kết quả lọc nhớ theo (danh sách đang có, điều kiện lọc): ve() / dong() / đếm gọi nhiều lần chỉ lọc một lần."""
        cu = getattr(self, '_kq_loc', None)
        # so chính đối tượng danh sách (is), không so id(): danh sách nạp lại có thể trùng id với danh sách cũ đã bị hủy
        if cu is not None and cu[0] is self.ds and cu[1] == khoa:
            return cu[2]
        kq = ham()
        self._kq_loc = (self.ds, khoa, kq)
        return kq


def _o_tim(chu: str, khung: _Khung) -> QLineEdit:
    o = QLineEdit()
    o.setPlaceholderText(chu)
    o.setClearButtonEnabled(True)
    o.setMinimumHeight(CAO_O_CONG_CU)
    o.textChanged.connect(lambda *_: khung._tim_khi_go())
    return o


def _nut(ds: list, lo, nut: dict) -> None:
    """Thêm các nút (chữ, hàm) vào lo, ghi vào nut[chữ]."""
    for ten, ham in ds:
        b = QPushButton(ten)
        b.clicked.connect(ham)
        b.setMinimumHeight(CAO_O_CONG_CU)
        lo.addWidget(b)
        nut[ten] = b


def _chuoi_tim(x, loai: str, cac_phan) -> str:
    """Chuỗi không dấu để tìm của một hộ (TongHopHo), tính một lần rồi nhớ trên đối tượng (danh sách nạp lại = đối tượng mới)."""
    k = '_tim_' + loai
    v = x.__dict__.get(k)
    if v is None:
        v = bo_dau(' '.join(str(p or '') for p in cac_phan()))
        x.__dict__[k] = v
    return v


def _bang(cot: list) -> QTableWidget:
    """Bảng nhỏ có sửa / hoàn tác (hộp thoại một hộ) - danh sách lớn dùng BangAo."""
    b = QTableWidget(0, len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    b.setWordWrap(True)
    b.verticalHeader().setVisible(False)
    dau = b.horizontalHeader()
    dau.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    dau.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    dau.setStretchLastSection(True)
    dau.setMinimumHeight(46)                                 # tiêu đề 2 dòng
    dau.setResizeContentsPrecision(DO_MAU)
    return b


_CANH_PHAI = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_CANH_TRAI = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
_CHU_DAM = []


def _o(b: QTableWidget, r: int, c: int, v, so: bool = False, nen=None, dam: bool = False, du_lieu=None, goi_y: str = ''):
    t = '' if v is None else str(v)
    it = QTableWidgetItem(t)
    it.setTextAlignment(_CANH_PHAI if so else _CANH_TRAI)
    if nen is not None:
        it.setBackground(QBrush(nen))
    if dam:
        if not _CHU_DAM:
            f = QFont()
            f.setBold(True)
            _CHU_DAM.append(f)
        it.setFont(_CHU_DAM[0])
    if du_lieu is not None:
        it.setData(Qt.ItemDataRole.UserRole, du_lieu)
    if goi_y or len(t) > 25 or '\n' in t:              # chữ ngắn hiện đủ trong ô: không gắn gợi ý
        it.setToolTip(goi_y or t)
    b.setItem(r, c, it)
    return it


def mo_ta_ban_giao(x) -> tuple:
    if x.da_ban_giao:
        return 'Đã bàn giao' + (f' {x.ban_giao_ngay}' if x.ban_giao_ngay else ''), XANH
    if x.ly_do_ban_giao:
        return f'Chưa: {x.ly_do_ban_giao}', VANG
    return '', None


def _chu(gt: list, so: tuple = (), tien: tuple = ()) -> list:
    """Chuỗi hiển thị một dòng: cột trong `so` = diện tích (so_vn), trong `tien` = số tiền (vn), None = ô trống."""
    return [('' if v is None else so_vn(v) if c in so else vn(v) if c in tien else str(v)) for c, v in enumerate(gt)]


# ---------------------------------------------------------------- Quyết định phê duyệt (trang riêng, Nhóm 6)
class KhungQuyetDinh(_Khung):
    """Màn hình DUY NHẤT quản lý quyết định phê duyệt (0.9.76 - trước nằm trong Bảng tổng hợp). Master-Detail: trái danh sách
    quyết định (bấm vào một quyết định); phải: thanh khớp số liệu "Đã duyệt: X/N hộ · Tổng tiền: Y đ" và các hộ của quyết định,
    mỗi thửa một dòng."""
    COT = ['STT', 'Họ và tên', 'Địa chỉ', 'Phương án\nchi tiết số', 'Ngày PA', 'QĐ chi tiết\nsố', 'Ngày ban\nhành', 'Tờ', 'Thửa',
           'DT thu hồi\n(m²)', 'Loại đất', 'Tiền đất', 'Tiền tài sản', 'Tiền cây\ntrồng', 'Các chính\nsách hỗ trợ', 'Tổng\nphê duyệt',
           'Chi trả', 'Bàn giao MB']
    COT_HO = (0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17)
    COT_TIEN = (11, 12, 13, 14, 15)
    TIEN_QD = ('tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'so_tien')     # cột 11-15
    LUON_BAT = ('Thêm…', 'Nhập từ file…', 'Xuất Excel…')                            # các nút khác cần một quyết định đang chọn

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.ds_qd = []
        self.qd_id = None
        self._can_nap = False
        self.ds_qd_w = QListWidget()
        self.ds_qd_w.setMinimumWidth(260)
        self.ds_qd_w.currentRowChanged.connect(lambda i: self.chon(self.ds_qd[i].id if 0 <= i < len(self.ds_qd) else None))
        self.ds_qd_w.setStyleSheet('QListWidget::item { padding: 6px 4px; color: #0B5CAD; } '
                                   'QListWidget::item:selected { background: #DCEBFA; color: #08345F; }')
        self.nut = {}
        cot_trai = QVBoxLayout()
        nhan = QLabel('CÁC QUYẾT ĐỊNH PHÊ DUYỆT')
        nhan.setProperty('vai', 'tieu_de')
        cot_trai.addWidget(nhan)
        cot_trai.addWidget(self.ds_qd_w, 1)
        h_qd = QHBoxLayout()
        _nut([('Thêm…', lambda: self.sua_qd(None)), ('Nhập từ file…', lambda: self.nhap_file()),
              ('Sửa…', lambda: self.sua_qd(self.qd_id)), ('Xóa', lambda: self.xoa_qd())], h_qd, self.nut)
        cot_trai.addLayout(h_qd)
        trai = QWidget()
        trai.setLayout(cot_trai)
        self.lb_qd = QLabel('Chọn một quyết định bên trái.')
        self.lb_qd.setWordWrap(True)
        self.lb_qd.setTextFormat(Qt.TextFormat.RichText)
        self.lb_qd.setOpenExternalLinks(False)
        self.lb_qd.linkActivated.connect(lambda *_: self.mo_file_qd())
        self.lb_khop = QLabel('')                          # thanh khớp số liệu: số hộ đã duyệt / tổng hộ, tổng tiền, khớp tổng ghi trong QĐ
        self.lb_khop.setWordWrap(True)
        self.bang = BangAo(self.COT, can_phai=(0, 9, *self.COT_TIEN))     # 1.000 hộ x 3 thửa x 18 cột: bảng ảo
        for c, w in enumerate((44, 190, 190, 110, 86, 110, 86, 56, 56, 92, 70, 110, 110, 100, 110, 120, 200, 130)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(lambda r, c: self.sua_ho(self.bang.ma_dong(r)))
        from .giao_dien import XepDong
        h_ho = XepDong(cach=6)          # hết chỗ thì xuống dòng (trước 0.9.18: một hàng 932 px ép cửa sổ rộng hơn màn hình 1366)
        _nut([('Thêm hộ vào quyết định…', lambda: self.them_ho()), ('Sửa hộ đang chọn…', lambda: self.sua_ho()),
              ('Ghi nhận đã nhận tiền…', lambda: self.ghi_chi_tra()), ('Bỏ hộ khỏi quyết định', lambda: self.bo_ho()),
              ('Xuất Excel…', lambda: self.xuat())], h_ho, self.nut)
        phai = QWidget()
        lp = QVBoxLayout(phai)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.addWidget(self.lb_qd)
        lp.addWidget(self.lb_khop)
        lp.addWidget(self.bang, 1)
        lp.addLayout(h_ho)
        tach = QSplitter()
        tach.addWidget(trai)
        tach.addWidget(phai)
        tach.setStretchFactor(1, 1)
        tach.setSizes([300, 1100])
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(tach)

    def showEvent(self, e):
        super().showEvent(e)
        if self._can_nap:
            self.nap()

    def _qd(self, qd_id):
        return next((x for x in self.ds_qd if x.id == qd_id), None)

    def nap(self, giu: bool = True):
        """Nạp lại danh sách quyết định; trang đang ẩn thì chỉ đánh dấu, nạp khi hiện (showEvent) - lưu một hộ ở trang khác không
        phải dựng lại bảng của trang không ai đang xem."""
        if not self.isVisible() and not self.im_lang:
            self._can_nap = True
            return
        self._can_nap = False
        cu = self.qd_id if giu else None
        self.ds_qd = theo_doi.ds_quyet_dinh(self.con) if self.con is not None else []
        w = self.ds_qd_w
        w.blockSignals(True)
        w.clear()
        for q in self.ds_qd:
            it = QListWidgetItem(f'Quyết định số {q.so}' + (f'\nngày {q.ngay}' if q.ngay else '') +
                                 f'  ·  {q.so_ho} hộ  ·  {vn(q.tong_ho)} đ' + (f'\nđã nhận tiền {q.so_ho_da_nhan}/{q.so_ho} hộ'
                                                                               if q.so_ho else ''))
            it.setToolTip(q.trich_yeu or q.nhan)
            w.addItem(it)
        i = next((k for k, q in enumerate(self.ds_qd) if q.id == cu), 0 if self.ds_qd else -1)
        w.setCurrentRow(i)
        # chọn lại khi tín hiệu đang chặn: chon() chạy MỘT lần (trước 0.9.22 currentRowChanged + gọi thẳng = dựng bảng 2 lần)
        w.blockSignals(False)
        self.chon(self.ds_qd[i].id if i >= 0 else None)
        sua = self.con is not None and not self.chi_doc
        for ten, b in self.nut.items():
            if ten != 'Xuất Excel…':
                b.setEnabled(sua and (ten in self.LUON_BAT or i >= 0))

    def chon(self, qd_id):
        self.qd_id = qd_id
        q = self._qd(qd_id)
        if q is None:
            self.lb_qd.setText('Chưa có quyết định nào. Bấm "Nhập từ file…" (quyết định có danh sách hộ đính kèm) hoặc "Thêm…".'
                               if self.con is not None else '')
            self.bang.dat_du_lieu([])
            self._cap_khop(None)
            return
        tep = ' · <a href="mo">mở file quyết định</a>' if q.file else ''
        self.lb_qd.setText(f'<b>Quyết định số {q.so}</b>' + (f' ngày {q.ngay}' if q.ngay else '') +
                           (f' - {q.trich_yeu}' if q.trich_yeu else '') + tep)
        self._cap_khop(q)
        self.ve()

    def _cap_khop(self, q):
        """Thanh khớp số liệu của quyết định đang chọn: "Đã duyệt: X/N hộ · Tổng tiền: Y đ" (X = hộ của quyết định, N = tổng số hộ
        của dự án), khớp / lệch với tổng tiền ghi trong quyết định, số hộ đã nhận tiền, số hộ đã có quyết định của cả dự án."""
        if self.con is None:
            self.lb_khop.setText('')
            self.lb_khop.setStyleSheet('')
            return
        n = self.con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        da = self.con.execute('SELECT COUNT(DISTINCT ma_ho) FROM qd_ho').fetchone()[0]
        toan = f'Toàn dự án: {da}/{n} hộ đã có quyết định phê duyệt'
        if q is None:
            dat_trang_thai(self.lb_khop, 'tin', f'Đã duyệt: 0/{n} hộ · Tổng tiền: 0 đ  ·  {toan}')
            return
        muc, khop = 'dat', ''
        if str(q.tong_tien).strip():
            if D(q.tong_tien) == q.tong_ho:
                khop = '  ·  KHỚP với tổng tiền ghi trong quyết định'
            else:
                muc, khop = 'canh_bao', f'  ·  LỆCH: quyết định ghi tổng {vn(q.tong_tien)} đ, cộng các hộ {vn(q.tong_ho)} đ'
        else:
            muc, khop = 'tin', '  ·  quyết định chưa ghi tổng tiền để đối chiếu (bấm "Sửa…" để nhập)'
        dat_trang_thai(self.lb_khop, muc, f'Đã duyệt: {q.so_ho}/{n} hộ · Tổng tiền: {vn(q.tong_ho)} đ{khop}  ·  Đã nhận tiền '
                                          f'{q.so_ho_da_nhan}/{q.so_ho} hộ ({vn(q.da_chi)} đ)  ·  {toan}')

    def dong(self) -> list:
        """[(hộ, dòng quyết định của hộ, [giá trị 18 cột], số dòng thửa)]."""
        if self.qd_id is None:
            return []
        kq = []
        ds = theo_doi.tong_hop(self.con, theo_doi.ho_cua_qd(self.con, self.qd_id), tinh_pa=False)
        for stt, x in enumerate(ds, start=1):
            q = next(y for y in x.qd if y['qd_id'] == self.qd_id)
            if q['da_chi_tra']:
                ct = 'Đã nhận' + (f' {q["chi_tra_ngay"]}' if q['chi_tra_ngay'] else '') + \
                     (f' · {_tien(q["chi_tra_so_tien"])} đ' if q['chi_tra_so_tien'] else '')
            else:
                ct = 'Chưa nhận' + (f': {q["ly_do_chua_nhan"]}' if q['ly_do_chua_nhan'] else '')
            bg, _ = mo_ta_ban_giao(x)
            ho = [stt, x.ho_ten, x.dia_chi, q['so_pa'], q['ngay_pa'], q['qd_ct_so'], q['qd_ct_ngay']]
            tien = [_so_hoac_trong(q[k]) for k in self.TIEN_QD]
            thua = x.thua or [THUA_TRONG]
            for i, t in enumerate(thua):
                dau = i == 0
                kq.append((x, q, [*(ho if dau else [None] * 7), t['so_to'], t['so_thua'], _so_hoac_trong(t['dt_thu_hoi']),
                                  t['loai_dat'], *(tien if dau else [None] * 5), ct if dau else None, bg if dau else None],
                           len(thua) if dau else 0))
        return kq

    def ve(self):
        hien, ma, kieu, gop = [], [], {}, []
        for r, (x, q, gt, n) in enumerate(self.dong()):
            hien.append(_chu(gt, so=(9,), tien=self.COT_TIEN))
            ma.append(x.ma_ho)
            if n:
                kieu[(r, 15)] = _DAM
                kieu[(r, 16)] = dict(nen=XANH if q['da_chi_tra'] else DO)
                gop.append((r, n, self.COT_HO))
        self.bang.dat_du_lieu(hien, ma, kieu, gop)

    # ---- thao tác
    def sua_qd(self, qd_id, gia_tri: dict | None = None):
        if self.con is None or self.chi_doc:
            return None
        if gia_tri is None:
            dlg = HopQuyetDinh(self, self._qd(qd_id))
            if not dlg.exec():
                return None
            gia_tri = dlg.gia_tri()
        try:
            self.qd_id = theo_doi.luu_qd(self.con, qd_id, **gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        return self._da_ghi(self.qd_id)

    def xoa_qd(self, xac_nhan: bool | None = None):
        q = self._qd(self.qd_id)
        if q is None:
            return None
        if xac_nhan is None:
            xac_nhan = self.hoi(f'Xóa quyết định số {q.so} cùng {q.so_ho} dòng hộ của quyết định (chi trả theo quyết định này '
                                'cũng bị xóa)?\nHồ sơ hộ, phương án giữ nguyên.')
        if not xac_nhan:
            return None
        n = theo_doi.xoa_qd(self.con, q.id)
        self.qd_id = None                                # nạp lại: chọn quyết định đầu danh sách
        return self._da_ghi(n)

    def nhap_file(self, file=None):
        """Nhập quyết định tổng / bổ sung có danh sách hộ đính kèm: dùng hộp "Nhập quyết định" (khớp hộ theo danh sách).
        Từ 0.9.18 là lối DUY NHẤT nhập quyết định (bỏ mục "Nhập quyết định…" trùng ở menu trái): truyền thư mục hồ sơ như lệnh
        cũ của cửa sổ chính - ô "chép file quyết định vào thư mục hồ sơ" có sẵn."""
        from . import quan_ly
        from .man_hinh_quan_ly import HopNhapQD
        from .nghiep_vu import tinh_tat_ca
        tong = {k.ma_ho: k.tong for k in tinh_tat_ca(self.con)}
        file_du_an = self.con.execute('PRAGMA database_list').fetchone()[2] or None     # đường dẫn file .pabt đang mở
        dlg = HopNhapQD(self.con, self, tong, quan_ly.thu_muc_ho_so(self.con, file_du_an), None)
        dlg.im_lang = self.im_lang
        if file is not None:
            dlg.doc(file)
        if self.im_lang:
            return dlg                               # kiểm thử: gọi dlg.accept() rồi self.sau_nhap(dlg)
        if dlg.exec():
            self.sau_nhap(dlg)
        return dlg

    def sau_nhap(self, dlg):
        self.qd_id = (getattr(dlg, 'ket_qua', None) or {}).get('qd_id') or self.qd_id
        self._da_ghi()

    def them_ho(self, ds_ma: list | None = None):
        if self.qd_id is None:
            return 0
        if ds_ma is None:
            dlg = HopChonHo(self.con, self, loai_tru=theo_doi.ho_cua_qd(self.con, self.qd_id))
            if not dlg.exec():
                return 0
            ds_ma = dlg.chon()
        theo_doi.them_ho_theo_pa(self.con, self.qd_id, ds_ma)
        return self._da_ghi(len(ds_ma))

    def sua_ho(self, ma=None, gia_tri: dict | None = None):
        ma = self.bang.ma_dong(self.bang.currentRow()) if ma is None else ma
        if ma is None or self.qd_id is None or self.chi_doc:
            return None
        if gia_tri is None:
            dong = next((x for x in theo_doi.doc_qd_ho(self.con, ma) if x['qd_id'] == self.qd_id), None)
            dlg = HopQDHo(self.con, ma, self.qd_id, dong, self)
            if not dlg.exec():
                return None
            gia_tri = dlg.gia_tri()
        try:
            theo_doi.ghi_qd_ho(self.con, self.qd_id, ma, gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        return self._da_ghi(ma)

    def ghi_chi_tra(self, ds_ma: list | None = None, ngay: str | None = None, chung_tu: str = ''):
        ds_ma = self.ma_da_chon() if ds_ma is None else ds_ma
        if not ds_ma or self.qd_id is None:
            self.bao('Chọn các hộ đã nhận tiền trong bảng (giữ Ctrl / Shift để chọn nhiều).', loi=False)
            return 0
        if ngay is None:
            dlg = HopNgayChiTra(self, len(ds_ma))
            if not dlg.exec():
                return 0
            ngay, chung_tu = dlg.o_ngay.text(), dlg.o_file.text()
        try:
            n = theo_doi.ghi_chi_tra(self.con, [(self.qd_id, m) for m in ds_ma], ngay, chung_tu)
        except LoiNhap as e:
            self.bao(str(e))
            return 0
        return self._da_ghi(n)

    def bo_ho(self, xac_nhan: bool | None = None):
        ds = self.ma_da_chon()
        if not ds or self.qd_id is None:
            return 0
        if xac_nhan is None:
            xac_nhan = self.hoi(f'Bỏ {len(ds)} hộ khỏi quyết định này?')
        if not xac_nhan:
            return 0
        theo_doi.bo_cac_ho_khoi_qd(self.con, self.qd_id, ds)
        return self._da_ghi(len(ds))

    def mo_file_qd(self):
        q = self._qd(self.qd_id)
        if q and q.file:
            if Path(q.file).exists():
                mo_file(q.file)
            else:
                self.bao(f'Không thấy file:\n{q.file}')

    def xuat(self, file=None):
        q = self._qd(self.qd_id)
        if q is None:
            return None

        def ghi(f):
            dong = self.dong()
            gop = [(i, c, i + n - 1, c) for i, (_, _, _, n) in enumerate(dong) if n > 1 for c in self.COT_HO]
            return theo_doi.xuat_excel(f, f'DANH SÁCH HỘ THEO QUYẾT ĐỊNH SỐ {q.so}' + (f' NGÀY {q.ngay}' if q.ngay else ''),
                                       self.COT, [d for _, _, d, _ in dong],
                                       [5, 24, 24, 13, 11, 13, 11, 7, 7, 11, 9, 14, 14, 13, 14, 15, 24, 16], gop, q.trich_yeu)
        ten = ''.join(ch if ch.isalnum() else '_' for ch in q.so)
        return self._xuat(file, 'Lưu danh sách hộ của quyết định', f'QD_{ten}.xlsx', ghi)


# ---------------------------------------------------------------- Bảng tổng hợp: tiền theo phương án
class KhungTongHopTien(_Khung):
    """Tổng hợp tiền theo phương án hiện tại (từng hạng mục), so với phê duyệt và file Excel; bấm tiêu đề cột để sắp xếp."""
    # hạng mục KHÔNG đánh số: bản in đánh 1 Đất, 2 Nhà, 3 Cây, 4 Vật nuôi, 5 Hỗ trợ, 6 Thưởng - bảng 5 cột gộp cây + vật nuôi
    # (nghiep_vu.muc_5_cot) nên số "4. Hỗ trợ" cũ lệch với bản in
    COT = ['STT', 'Mã hộ', 'Họ và tên', 'Số thửa', 'DT thu hồi (m²)', 'Đất', 'Nhà, công trình', 'Cây trồng, vật nuôi', 'Hỗ trợ',
           'Thưởng', 'TỔNG PHƯƠNG ÁN', 'Tổng phê duyệt', 'Chênh lệch PA - phê duyệt', 'Đối chiếu Excel']

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.nut = {}
        # sắp theo giá trị số (QTableWidget cũ sắp cột tiền theo chữ); không chữ xuống dòng: không đo chiều cao dòng
        self.bang = BangAo(self.COT, can_phai=(0, 1, *range(3, 13)), sap_xep=True, tu_cao=False)
        self.bang.cellDoubleClicked.connect(self._mo_ho_dong)
        self.lb = QLabel('')
        h = QHBoxLayout()
        h.addWidget(self.lb, 1)
        _nut([('Xuất Excel…', lambda: self.xuat())], h, self.nut)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h)
        lo.addWidget(self.bang, 1)

    def dong(self) -> list:
        if self.con is None:
            return []
        from .doi_chieu import doi_chieu
        dc = {h['ma_ho']: h for h in doi_chieu(self.con).ho}
        kq = []
        for stt, x in enumerate(theo_doi.tong_hop(self.con), start=1):
            pd = x.tong_phe_duyet if x.qd else None
            h = dc.get(x.ma_ho, {})
            doi = ('Sửa trong phần mềm' if h.get('sua') else 'LỆCH' if h.get('lech') else 'Khớp') \
                if h.get('co_excel') and (h.get('tong', KHONG) > 0 or h.get('sua')) else ''
            kq.append([stt, x.ma_ho, x.ho_ten, len(x.thua), x.dt, *(x.muc_pa.get(m, KHONG) for m in (1, 2, 3, 4, 5)), x.tong_pa,
                       pd, (x.tong_pa - pd) if pd is not None else None, doi])
        return kq

    def nap(self):
        ds = self.dong()
        hien, ma, kieu = [], [], {}
        for r, d in enumerate(ds):
            hien.append(_chu(d, so=(4,), tien=tuple(range(5, 13))))
            ma.append(d[1])
            kieu[(r, 10)] = _DAM
            if d[12] is not None:
                kieu[(r, 12)] = dict(nen=DO if d[12] else XANH)
            if d[13]:
                kieu[(r, 13)] = dict(nen=DO if d[13] == 'LỆCH' else XANH)
        b = self.bang
        b.dat_du_lieu(hien, ma, kieu, khoa=ds)
        b.resizeColumnsToContents()
        b.setColumnWidth(2, min(max(b.columnWidth(2), 200), 300))
        self.lb.setText(f'{len(ds)} hộ · tổng phương án {vn(sum((d[10] for d in ds), KHONG))} đ · tổng phê duyệt '
                        f'{vn(sum((d[11] or KHONG for d in ds), KHONG))} đ')

    def xuat(self, file=None):
        if self.con is None:
            return None
        return self._xuat(file, 'Lưu tổng hợp tiền theo phương án', 'TongHopTien.xlsx', lambda f: theo_doi.xuat_excel(
            f, 'TỔNG HỢP TIỀN BỒI THƯỜNG, HỖ TRỢ THEO PHƯƠNG ÁN', self.COT, self.dong(),
            [6, 8, 26, 8, 12, 15, 15, 15, 15, 13, 17, 17, 17, 16], None, self._ten_du_an()))


def _ty_le(x: float) -> str:
    """Tỷ lệ %: một chữ số lẻ, hai khi cần (2,5 / 3,5 / 100,0 / 102,5 / 2,25) - không làm tròn 2,5 thành 2,4."""
    s = f'{x:.2f}'
    return (s[:-1] if s.endswith('0') else s).replace('.', ',')


# ---------------------------------------------------------------- Bảng tổng hợp kinh phí: cơ cấu kinh phí dự án
LE_THE = 8                  # lề trong mỗi thẻ của Bảng tổng hợp kinh phí (px)


class KhungCoCau(_Khung):
    """Thẻ 1 - Cơ cấu kinh phí dự án: tiền đất, tài sản (nhà, công trình), cây trồng - vật nuôi, hỗ trợ, thưởng; cộng bồi thường,
    hỗ trợ, tái định cư; kinh phí tổ chức thực hiện bồi thường (QĐ 08/2025/QĐ-UBND); tổng kinh phí. Số theo phương án, đối chiếu số
    đã phê duyệt trong các quyết định (kinh_phi_du_an.co_cau)."""
    COT = ['Nhóm khoản', 'Số hộ', 'Theo phương án\ncả dự án (đ)', 'Đã phê duyệt\ntrong quyết định (đ)',
           'Chưa phê duyệt\n(hộ chưa có QĐ) (đ)', 'Lệch PA - QĐ (đ)\n(hộ đã có QĐ)', 'Tỷ lệ (%)\ngốc 100% = cộng BT', 'Ghi chú']

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.cc = None
        self.nut = {}
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.bang = BangAo(self.COT, can_phai=(1, 2, 3, 4, 5, 6), tu_cao=True)
        for c, w in enumerate((240, 50, 125, 130, 125, 120, 95, 320)):
            self.bang.setColumnWidth(c, w)
        h = QHBoxLayout()
        h.addWidget(self.lb, 1)
        _nut([('Xuất Excel…', lambda: self.xuat())], h, self.nut)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h)
        lo.addWidget(self.bang, 1)

    def nap(self):
        self.cc = kinh_phi_du_an.co_cau(self.con) if self.con is not None else None
        self.ve()

    def dong(self) -> list:
        """[(loại dòng, [giá trị 8 cột])] - loại: nhom / cong / kinh_phi / tong."""
        if self.cc is None:
            return []
        return [(d['loai'], [d['ten'], d['so_ho'], d['tien_pa'], d['tien_pd'], d['chua_pd'], d['chenh'],
                             _ty_le(d['ty_trong']), d['ghi_chu']]) for d in self.cc['dong']]

    def ve(self):
        dong = self.dong()
        kieu = {}
        co_qd = bool(self.cc and self.cc['so_ho_phe_duyet'])
        for r, (loai, gt) in enumerate(dong):
            if loai in DONG_NOI:
                nen, chu = DONG_NOI[loai]
                for c in range(len(self.COT)):
                    kieu[(r, c)] = dict(nen=nen, mau_chu=chu, dam=True)
            if loai in ('nhom', 'cong') and co_qd and gt[5] is not None:        # có quyết định: lệch số phương án so với phê duyệt
                kieu[(r, 5)] = dict(nen=DO if gt[5] else XANH, dam=loai == 'cong')
        self.bang.dat_du_lieu([_chu(gt, tien=(2, 3, 4, 5)) for _, gt in dong], [], kieu)
        if dong:                                         # cột Nhóm khoản vừa chữ dài nhất (chữ đậm) - không xuống dòng, không quá rộng
            from PySide6.QtGui import QFont, QFontMetrics
            f = QFont(self.bang.font())
            f.setBold(True)
            rong = max(QFontMetrics(f).horizontalAdvance(str(gt[0])) for _, gt in dong) + 2 * LE_THE + 8
            self.bang.setColumnWidth(0, max(240, min(rong, 420)))
        if self.cc is None:
            self.lb.setText('')
            return
        c = self.cc
        self.lb.setText(f'<b>{c["so_ho"]} hộ</b> · đã lập phương án {c["so_ho_da_lap"]} · đã có quyết định phê duyệt '
                        f'{c["so_ho_phe_duyet"]} · tổng kinh phí <b>{vn(c["tong"])} đ</b> (gồm kinh phí tổ chức thực hiện '
                        f'{vn(c["kinh_phi"])} đ)')

    def xuat(self, file=None):
        if self.con is None or self.cc is None:
            return None
        return self._xuat(file, 'Lưu cơ cấu kinh phí dự án', 'CoCauKinhPhi.xlsx', lambda f: theo_doi.xuat_excel(
            f, 'CƠ CẤU KINH PHÍ DỰ ÁN', [x.replace('\n', ' ') for x in self.COT], [gt for _, gt in self.dong()],
            [42, 8, 20, 22, 22, 20, 14, 60], None, self._ten_du_an()))


# ---------------------------------------------------------------- Bảng tổng hợp kinh phí: đối soát khái toán Pre-F/S
class KhungDoiSoat(_Khung):
    """Thẻ 3 - Đối soát dự toán Pre-F/S: so hạn mức kinh phí THỰC TẾ (áp giá của dự án) với Bảng khái toán ban đầu (file .pabtdt
    hoặc bảng khái toán đang mở ở Nhóm 1) theo từng mục (kinh_phi_du_an.doi_soat / du_toan.so_sanh)."""
    COT = ['Mục', 'Hạng mục', 'Khái toán\n(Pre-F/S) (đ)', 'Thực tế\náp giá (đ)', 'Chênh lệch\n(thực tế - khái toán) (đ)', 'Tỷ lệ (%)']

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.goc = None                    # du_toan.DuToan dùng làm khái toán ban đầu
        self.nguon = ''                    # chữ mô tả nguồn (tên file / "bảng khái toán đang mở")
        self.ss = None                     # kết quả du_toan.so_sanh gần nhất
        self.nguon_dang_mo = None          # hàm () -> DuToan | None: cửa sổ chính gắn (bảng khái toán đang mở ở Nhóm 1)
        self.nut = {}
        self.lb_nguon = QLabel('')
        self.lb_nguon.setWordWrap(True)
        self.lb_kq = QLabel('')
        self.lb_kq.setWordWrap(True)
        self.bang = BangAo(self.COT, can_phai=(0, 2, 3, 4, 5), tu_cao=False)
        for c, w in enumerate((50, 320, 180, 180, 210, 90)):
            self.bang.setColumnWidth(c, w)
        h = QHBoxLayout()
        h.addWidget(self.lb_nguon, 1)
        _nut([('Dùng bảng khái toán đang mở', lambda: self.dung_dang_mo()), ('Chọn file khái toán…', lambda: self.chon_file()),
              ('Xuất Excel…', lambda: self.xuat())], h, self.nut)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h)
        lo.addWidget(self.lb_kq)
        lo.addWidget(self.bang, 1)

    def nap(self):
        if self.goc is None and self.con is not None:                # nhớ file khái toán đã chọn của dự án
            f = kinh_phi_du_an.file_khai_toan(self.con)
            if f and Path(f).exists():
                try:
                    self.goc, self.nguon = kinh_phi_du_an.mo_khai_toan(f), f'file {Path(f).name}'
                except LoiNhap:
                    pass
        self.ve()

    def dung_dang_mo(self, dt=None):
        """Lấy bảng khái toán đang mở ở Nhóm 1 (hoặc dt) làm khái toán ban đầu. Trả kết quả so sánh, None nếu chưa có bảng."""
        dt = dt if dt is not None else (self.nguon_dang_mo() if self.nguon_dang_mo else None)
        if dt is None or not dt.dong:
            self.bao('Chưa có bảng khái toán nào đang mở ở Nhóm 1 (Lập khái toán & Dự toán). Mở hoặc lập bảng khái toán, '
                     'hoặc bấm "Chọn file khái toán…".', loi=False)
            return None
        self.goc, self.nguon = dt, f'bảng khái toán đang mở ở Nhóm 1 ({dt.ten or "chưa đặt tên"})'
        self.ve()
        return self.ss

    def chon_file(self, file=None):
        if self.con is None:
            return None
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file khái toán', '', 'Bảng khái toán LARC (*.pabtdt)')
            if not file:
                return None
        try:
            dt = kinh_phi_du_an.mo_khai_toan(file)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.goc, self.nguon = dt, f'file {Path(file).name}'
        if not self.chi_doc:
            kinh_phi_du_an.dat_file_khai_toan(self.con, file)
        self.ve()
        return self.ss

    def dong(self) -> list:
        if self.ss is None:
            return []
        kq = [[m, ten, a, b, c, None if t is None else f'{t:.1f}'.replace('.', ',')] for m, ten, a, b, c, t in self.ss['dong']]
        a, b, c, t = self.ss['tong']
        kq.append([None, 'TỔNG CỘNG', a, b, c, None if t is None else f'{t:.1f}'.replace('.', ',')])
        return kq

    def ve(self):
        self.ss = kinh_phi_du_an.doi_soat(self.con, self.goc) if self.con is not None and self.goc is not None else None
        self.lb_nguon.setText(f'Bảng khái toán ban đầu: <b>{self.nguon}</b>' if self.goc is not None else
                              'Chưa chọn bảng khái toán ban đầu: bấm "Dùng bảng khái toán đang mở" hoặc "Chọn file khái toán…".')
        self.nut['Dùng bảng khái toán đang mở'].setEnabled(self.nguon_dang_mo is not None)
        dong = self.dong()
        kieu = {}
        for r, d in enumerate(dong):
            if r == len(dong) - 1:                     # TỔNG CỘNG: như dòng tổng kinh phí của thẻ Cơ cấu
                nen, chu = DONG_NOI['tong']
                kieu.update({(r, c): dict(nen=nen, mau_chu=chu, dam=True) for c in range(len(self.COT))})
            elif d[4] is not None and d[4] > 0:
                kieu[(r, 4)] = dict(nen=DO)
        self.bang.dat_du_lieu([_chu(d, tien=(2, 3, 4)) for d in dong], [], kieu)
        if self.ss is None:
            dat_trang_thai(self.lb_kq, 'tin', 'So sánh hạn mức kinh phí thực tế (áp giá của dự án) với Bảng khái toán ban đầu '
                                              '(Pre-F/S) theo từng mục.')
            return
        a, b, c, t = self.ss['tong']
        if not a:
            dat_trang_thai(self.lb_kq, 'canh_bao', 'Bảng khái toán ban đầu chưa có số tiền nào - không có hạn mức để đối soát.')
        elif self.ss['vuot']:
            dat_trang_thai(self.lb_kq, 'loi', f'Thực tế VƯỢT khái toán {vn(c)} đ ({f"{t:.1f}".replace(".", ",")}%): '
                                              f'{vn(b)} đ so với hạn mức {vn(a)} đ. Cần điều chỉnh khái toán / báo cáo cấp quyết định.')
        else:
            dat_trang_thai(self.lb_kq, 'dat', f'Thực tế nằm trong khái toán: {vn(b)} đ / hạn mức {vn(a)} đ, còn dư {vn(-c)} đ.')

    def xuat(self, file=None):
        if self.con is None or self.ss is None:
            return None
        return self._xuat(file, 'Lưu đối soát khái toán', 'DoiSoatKhaiToan.xlsx', lambda f: theo_doi.xuat_excel(
            f, 'ĐỐI SOÁT KINH PHÍ THỰC TẾ VỚI BẢNG KHÁI TOÁN BAN ĐẦU (PRE-F/S)', [x.replace('\n', ' ') for x in self.COT], self.dong(),
            [6, 40, 22, 22, 26, 10], None, self._ten_du_an()))


class KhungBangTongHop(_Khung):
    """Bảng tổng hợp kinh phí (Nhóm 5, Bước 8): 3 thẻ - cơ cấu kinh phí dự án, bảng kinh phí chi tiết từng hộ, đối soát với bảng
    khái toán Pre-F/S. Quyết định phê duyệt là trang riêng của Nhóm 6 (nút "Đi đến Phân hệ Phê duyệt")."""
    THE = THE_TONG_HOP
    KY_HIEU_THE = (0xE9F9, 0xE716, 0xE8AB)                  # biểu tượng Segoe Fluent / MDL2 (máy không có phông: chỉ chữ)
    # thẻ vừa chuyển tới (bấm thẳng thẻ hoặc mo_the)
    the_da_doi = Signal(int)
    di_den_phe_duyet = Signal()                             # nút "Đi đến Phân hệ Phê duyệt": cửa sổ chính mở trang Quyết định

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.co_cau = KhungCoCau(con, self, chi_doc)
        self.tien = KhungTongHopTien(con, self, chi_doc)
        self.doi_soat = KhungDoiSoat(con, self, chi_doc)
        self.tab = QTabWidget()
        from .giao_dien import TOKEN, icon_ky_hieu
        for w, t, ma in zip(self.cac_the, self.THE, self.KY_HIEU_THE):
            ic = icon_ky_hieu(ma, TOKEN['chinh'], 16)
            self.tab.addTab(w, ic if ic is not None else QIcon(), t)
            # 16/10/2026 (người dùng): chữ tóm tắt / bảng không sát mép khung thẻ - lề vừa đủ
            if w.layout() is not None:
                w.layout().setContentsMargins(LE_THE, LE_THE - 2, LE_THE, LE_THE - 2)
            w.da_doi.connect(self._doi)
            w.mo_ho.connect(self.mo_ho.emit)
        self.b_phe_duyet = QPushButton('Xem Quyết định phê duyệt  →')
        self.b_phe_duyet.setToolTip('Mở Nhóm 6: Quyết định phê duyệt (danh sách quyết định, hộ của quyết định, khớp số liệu)')
        self.b_phe_duyet.clicked.connect(self.di_den_phe_duyet.emit)
        self.tab.setCornerWidget(self.b_phe_duyet, Qt.Corner.TopRightCorner)
        self.tab.currentChanged.connect(self._doi_the)
        self._can_nap = set(range(3))
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(self.tab)

    @property
    def cac_the(self) -> tuple:
        return self.co_cau, self.tien, self.doi_soat

    def _doi(self):
        self._can_nap = set(range(3)) - {self.tab.currentIndex()}
        self.da_doi.emit()

    def dat_du_an(self, con, chi_doc: bool = False):
        for w in (self, *self.cac_the):
            w.con, w.chi_doc = con, chi_doc
        self.doi_soat.goc, self.doi_soat.nguon = None, ''  # khái toán đối soát là của từng dự án: mở / đóng dự án thì bỏ
        self.nap()

    def nap(self):
        """Đánh dấu cần nạp lại; chỉ nạp thẻ đang xem (thẻ khác nạp khi chuyển sang - đỡ chậm)."""
        self._can_nap = set(range(3))
        if self.isVisible() or self.im_lang:
            self._nap_the(self.tab.currentIndex())

    def showEvent(self, e):
        super().showEvent(e)
        self._nap_the(self.tab.currentIndex())

    def _nap_the(self, i: int):
        if i in self._can_nap:
            self._can_nap.discard(i)
            self.cac_the[i].nap()
            if i == 1:                                      # tên thẻ ghi số hộ thật của dự án (không gán cứng)
                n = len(self.tien.bang.mo_hinh.du_lieu)
                self.tab.setTabText(1, f'{self.THE[1]} ({n} hộ)' if self.con is not None else self.THE[1])

    def _doi_the(self, i: int):
        self._nap_the(i)
        self.the_da_doi.emit(i)

    def mo_the(self, i: int):
        """Chuyển tới thẻ i; thẻ đang là i thì không có currentChanged: nạp + báo thẳng."""
        if self.tab.currentIndex() == i:
            self._doi_the(i)
        else:
            self.tab.setCurrentIndex(i)                     # -> currentChanged -> _doi_the


# ---------------------------------------------------------------- Theo dõi tiến độ
# hai nút chế độ xem ghép đôi (Theo hộ | Thửa còn vướng) kiểu "viên thuốc" (segmented pill, 1.0.02): khung ngoài nền slate bo 6,
# nút đang chọn nền navy chữ trắng đậm, nút không chọn trong suốt chữ slate. Kiểu cục bộ thắng kiểu tô theo chữ của giao_dien
QSS_CHE_DO = ('QPushButton { border: 0; background: transparent; color: #475569; padding: 0 14px; border-radius: 5px; '
              'font-weight: 600; }'
              'QPushButton:hover:!checked { background: #CBD5E1; color: #0F172A; }'
              'QPushButton:checked { background: #0F3866; color: #FFFFFF; font-weight: 700; }')
QSS_KHUNG_CHE_DO = 'QFrame#khung_che_do { background: #E2E8F0; border: 0; border-radius: 6px; }'
QSS_MOC = ('QLabel#lb_moc { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; padding: 0 8px; '
           'color: #334155; }')


class KhungTienDo(_Khung):
    """Tiến độ chi trả & Bàn giao (Bước 13-16 Mục IV QĐ 18/2026/QĐ-UBND) - MỘT trang từ 1.0.00 (người dùng 16/10/2026: gộp trang
    "Báo cáo tiến độ GPMB" - trùng ~70% dữ liệu và 3 nút trùng lệnh với trang này):
      - dải 4 thẻ chỉ số (man_hinh_bao_cao.DaiKPI): giải ngân, mặt bằng sạch, thửa chưa bàn giao, hộ đủ ĐK cưỡng chế - bấm thẻ = lọc;
      - hai chế độ xem: "Theo hộ" (nhập liệu: quyết định, chi trả, bàn giao, biên lai, vận động, HS đính kèm - bấm đúp dòng mở
        Trạng thái hộ) và "Thửa còn vướng" (thửa của hộ đã phê duyệt mà chưa bàn giao, xếp Gấp / Cao / Theo dõi);
      - dòng "Mốc pháp lý" một dòng + nút "Mốc pháp lý…" (ngày thông báo thu hồi đất, số ngày các mốc - việc làm một lần của dự án);
      - MỘT nút "Xuất" (menu): bảng theo dõi, báo cáo tiến độ GPMB, DS đề nghị cưỡng chế.
    Số liệu tính MỘT lần (theo_doi.tong_hop + van_dong + thoi_han) cho cả bảng lẫn thẻ / bảng thửa (bao_cao_gpmb.tong_quan nhận sẵn)."""
    COT = ['STT', 'Mã hộ', 'Họ và tên', 'Địa chỉ', 'Mốc thu hồi đất\n(Bước 13)', 'Vận động / cưỡng chế\n(Bước 14, 15)',
           'Quyết định phê duyệt', 'Tổng phê\nduyệt (đ)', 'Đã nhận (đ)', 'Ngày nhận\ntiền', 'Chưa nhận - lý do',
           'Biên lai / biên\nbản chi trả', 'Bàn giao\nmặt bằng', 'Lý do chưa\nbàn giao', 'Ghi chú theo dõi',
           'Hoàn tất CTBT\n(theo đợt)', 'HS đính kèm']
    # chỉ số cột (hai cột mốc / vận động đặt ngay sau Địa chỉ: cột quyết định, không phải cuộn ngang mới thấy)
    C_MOC, C_VD, C_QD, C_TONG, C_NHAN, C_NGAY, C_CHUA, C_BIEN_LAI, C_BG = 4, 5, 6, 7, 8, 9, 10, 11, 12
    C_HOAN_TAT, C_SCAN = 15, 16                         # 0.9.96: hoàn tất CTBT = có QĐ + đã bàn giao; số file hồ sơ scan
    LOC_VAN_DONG = [('dang_vd', 'Đang vận động'), ('du_cuong_che', 'Đủ điều kiện cưỡng chế (Điều 89)')]
    TEN_LOC = dict(theo_doi.LOC_TIEN_DO + LOC_VAN_DONG)
    CHE_DO = (('ho', 'Theo hộ'), ('thua', 'Thửa còn vướng'))
    # bấm thẻ chỉ số: (chế độ xem, bộ lọc của chế độ Theo hộ)
    KPI_LOC = dict(giai_ngan=('ho', 'chua_nhan'), mat_bang=('ho', 'chua_bg'), con_vuong=('thua', None),
                   cuong_che=('ho', 'du_cuong_che'))
    # nút "Xuất" (menu): chữ mục -> tên hàm
    XUAT = (('Bảng theo dõi chi trả & bàn giao (Excel)…', 'xuat'), ('Báo cáo tiến độ GPMB (Excel)…', 'xuat_bao_cao'),
            ('Danh sách đề nghị cưỡng chế (Excel)…', 'xuat_cuong_che'))
    QD_CAO_DONG = 22                                     # px mỗi quyết định trong ô danh sách quyết định (cao theo số quyết định)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        from .man_hinh_bao_cao import BangThuaVuong, DaiKPI
        self.ds = []
        self.dang_hien = []
        self.tq = None                                      # bao_cao_gpmb.tong_quan (thẻ chỉ số + thửa còn vướng)
        self._can_nap = False
        self.vd, self.moc = {}, {}                          # trạng thái vận động {mã hộ: [TinhTrang]}, mốc thu hồi {mã hộ: dict}
        self.dot_ho, self.scan = {}, {}                     # {mã hộ: 'Đợt N'}, {mã hộ: số file hồ sơ scan}
        self.kpi = DaiKPI(self)
        self.kpi.bam.connect(self.bam_kpi)
        # chế độ xem: hai nút bật / tắt liền nhau (một nhóm)
        self.nut_che_do = {}
        self.nhom_che_do = QButtonGroup(self)
        self.nhom_che_do.setExclusive(True)
        h_dk = QHBoxLayout()
        h_dk.setSpacing(6)
        self.khung_che_do = QFrame()                        # khung "viên thuốc" chứa hai nút chế độ
        self.khung_che_do.setObjectName('khung_che_do')
        self.khung_che_do.setStyleSheet(QSS_KHUNG_CHE_DO)
        h_pill = QHBoxLayout(self.khung_che_do)
        h_pill.setContentsMargins(3, 3, 3, 3)
        h_pill.setSpacing(2)
        self.khung_che_do.setFixedHeight(CAO_O_CONG_CU + 2)
        for i, (k, chu) in enumerate(self.CHE_DO):
            b = QPushButton(chu)
            b.setCheckable(True)
            b.setProperty('che_do', k)
            b.setProperty('khong_icon', True)
            b.setFixedHeight(CAO_O_CONG_CU - 4)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip('Từng hộ: quyết định, chi trả, bàn giao, vận động (bấm đúp dòng để cập nhật)' if k == 'ho' else
                         'Thửa của hộ đã phê duyệt mà chưa bàn giao mặt bằng, xếp theo mức ưu tiên giải tỏa')
            b.setStyleSheet(QSS_CHE_DO)
            self.nhom_che_do.addButton(b, i)
            self.nut_che_do[k] = b
            h_pill.addWidget(b)
        h_dk.addWidget(self.khung_che_do)
        self.nut_che_do['ho'].setChecked(True)
        self.nhom_che_do.idClicked.connect(lambda i: self.dat_che_do(self.CHE_DO[i][0]))
        self.lb_moc = QLabel('')
        self.lb_moc.setWordWrap(True)
        self.lb_moc.setObjectName('lb_moc')
        self.lb_moc.setStyleSheet(QSS_MOC)
        self.lb_moc.setMinimumHeight(CAO_O_CONG_CU)
        h_dk.addSpacing(8)
        h_dk.addWidget(self.lb_moc, 1)
        self.nut = {}
        _nut([('Mốc pháp lý…', lambda: self.mo_moc())], h_dk, self.nut)
        self.nut['Mốc pháp lý…'].setToolTip('Ngày thông báo thu hồi đất và số ngày các mốc pháp lý (thẩm định, thu hồi đất nông '
                                            'nghiệp / phi nông nghiệp, vận động) của dự án')
        # ---- chế độ Theo hộ
        self.cb_loc = QComboBox()
        for k, t in theo_doi.LOC_TIEN_DO + self.LOC_VAN_DONG:
            self.cb_loc.addItem(t, k)
        self.cb_loc.setToolTip('Số trong ngoặc: số hộ thỏa điều kiện (theo các quyết định đang đánh dấu)')
        self.cb_loc.currentIndexChanged.connect(lambda *_: self.ve())
        self.cb_loc.setMinimumHeight(CAO_O_CONG_CU)
        self.ds_qd_w = QListWidget()
        self.ds_qd_w.setMaximumHeight(72)
        self.ds_qd_w.setToolTip('Đánh dấu một hoặc nhiều quyết định; bỏ trống = tất cả')
        self.ds_qd_w.itemChanged.connect(lambda *_: self._doi_qd())
        self.o_tim = _o_tim('Tìm họ tên, mã hộ, lý do… (không cần dấu)', self)
        self.bang = BangAo(self.COT, can_phai=(0, 1, self.C_TONG, self.C_NHAN))     # 5.000 hộ x 15 cột -> bảng ảo
        for c, w in enumerate((40, 50, 160, 120, 230, 250, 190, 115, 115, 100, 220, 140, 130, 170, 170, 150, 80)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(self._nhap_dup)
        h_loc = QHBoxLayout()
        h_loc.setContentsMargins(0, 0, 0, 0)
        h_loc.addWidget(QLabel('Lọc:'))
        h_loc.addWidget(self.cb_loc)
        h_loc.addWidget(QLabel('Tìm:'))
        h_loc.addWidget(self.o_tim, 1)
        self.w_qd = QWidget()                               # chưa có quyết định nào: ẩn (không chiếm chỗ của bảng)
        h_qd = QHBoxLayout(self.w_qd)
        h_qd.setContentsMargins(0, 0, 0, 0)
        h_qd.addWidget(QLabel('Quyết định:'), 0, Qt.AlignmentFlag.AlignTop)
        h_qd.addWidget(self.ds_qd_w, 1)
        self.w_ho = QWidget()
        lo_ho = QVBoxLayout(self.w_ho)
        lo_ho.setContentsMargins(0, 0, 0, 0)
        lo_ho.addLayout(h_loc)
        lo_ho.addWidget(self.w_qd)
        lo_ho.addWidget(self.bang, 1)
        # ---- chế độ Thửa còn vướng
        self.thua = BangThuaVuong(self)
        self.thua.mo_ho.connect(self.mo_ho.emit)
        self.ngan_xem = QStackedWidget()
        self.ngan_xem.addWidget(self.w_ho)
        self.ngan_xem.addWidget(self.thua)
        # ---- nút thao tác + MỘT nút Xuất (menu)
        h_nut = XepDong(cach=6)                              # hẹp thì xuống dòng (cửa sổ 1366)
        # quyết định, chi trả, bàn giao của MỘT hộ: bấm đúp dòng, hoặc "Trạng thái hộ…" (menu Dữ liệu / chuột phải)
        _nut([('Bàn giao mặt bằng các hộ đã chọn…', lambda: self.ban_giao()),
              ('Sổ nhật ký vận động…', lambda: self.so_van_dong()),
              ('Hộ hoàn tất CTBT…', lambda: self.hoan_tat_ctbt()), ('Xuất', lambda: None)], h_nut, self.nut)
        self.menu_xuat = QMenu(self.nut['Xuất'])
        self.hanh_dong_xuat = {}
        for chu, ham in self.XUAT:
            a = self.menu_xuat.addAction(chu)
            a.triggered.connect(lambda _=False, ham=ham: getattr(self, ham)())
            self.hanh_dong_xuat[chu] = a
        self.nut['Xuất'].setMenu(self.menu_xuat)
        self.nut['Xuất'].setToolTip('Bảng theo dõi chi trả & bàn giao, báo cáo tiến độ GPMB, danh sách đề nghị cưỡng chế (Excel)')
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(self.kpi)
        lo.addLayout(h_dk)
        lo.addWidget(self.ngan_xem, 1)
        lo.addLayout(h_nut)

    def che_do(self) -> str:
        return self.CHE_DO[self.ngan_xem.currentIndex()][0]

    def dat_che_do(self, k: str):
        """'ho' / 'thua': đổi chế độ xem (nút chế độ đổi theo)."""
        i = next(i for i, (x, _) in enumerate(self.CHE_DO) if x == k)
        self.ngan_xem.setCurrentIndex(i)
        self.nut_che_do[k].setChecked(True)
        self._danh_dau_kpi()

    def the_kpi_dang_loc(self) -> str | None:
        """Thẻ chỉ số khớp chế độ xem + bộ lọc đang dùng (KPI_LOC), None nếu không thẻ nào."""
        che_do, loc = self.che_do(), self.cb_loc.currentData()
        return next((k for k, (cd, lc) in self.KPI_LOC.items() if cd == che_do and (lc is None or lc == loc)), None)

    def _danh_dau_kpi(self):
        self.kpi.dat_loc(self.the_kpi_dang_loc())

    def bam_kpi(self, k: str):
        """Bấm thẻ chỉ số: chuyển chế độ xem + lọc (KPI_LOC)."""
        che_do, loc = self.KPI_LOC[k]
        self.dat_che_do(che_do)
        if loc is not None:
            self.dat_loc(loc)

    def ma_da_chon(self) -> list:
        """Hộ đang chọn trên bảng của chế độ đang xem (lệnh Trạng thái hộ, Lập phương án… của cửa sổ chính, Bàn giao, Sổ vận động)."""
        return self.thua.ma_da_chon() if self.che_do() == 'thua' else self.bang.ma_da_chon()

    def nap(self):
        """Nạp lại; trang đang ẩn thì chỉ đánh dấu, nạp khi hiện (showEvent) - lưu một hộ không phải dựng lại bảng của trang
        không ai đang xem."""
        if not self.isVisible() and not self.im_lang:
            self._can_nap = True
            return
        self._can_nap = False
        self.ds = theo_doi.tong_hop(self.con, tinh_pa=False) if self.con is not None else []
        self._nap_van_dong()
        chon = self.qd_chon()
        w = self.ds_qd_w
        w.blockSignals(True)
        w.clear()
        for q in theo_doi.ds_quyet_dinh(self.con) if self.con is not None else []:
            it = QListWidgetItem(f'QĐ {q.so}' + (f' ngày {q.ngay}' if q.ngay else '') + f' - {q.so_ho} hộ, đã nhận '
                                 f'{q.so_ho_da_nhan}/{q.so_ho}')
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if q.id in chon else Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, q.id)
            w.addItem(it)
        w.blockSignals(False)
        w.setFixedHeight(min(72, w.count() * self.QD_CAO_DONG + 6))
        self.w_qd.setVisible(w.count() > 0)
        self._doi_qd()

    def showEvent(self, e):
        super().showEvent(e)
        if self._can_nap:
            self.nap()

    def _nap_van_dong(self):
        """Trạng thái vận động, mốc thu hồi đất từng hộ, thẻ chỉ số + thửa còn vướng (chỉ đọc lại khi nạp trang)."""
        self.nut['Mốc pháp lý…'].setEnabled(self.con is not None and not self.chi_doc)
        self.nut['Sổ nhật ký vận động…'].setEnabled(self.con is not None)
        self.nut['Hộ hoàn tất CTBT…'].setEnabled(self.con is not None)
        self.nut['Xuất'].setEnabled(self.con is not None)
        if self.con is None:
            self.vd, self.moc, self.dot_ho, self.scan, self.tq = {}, {}, {}, {}, None
            self.lb_moc.setText('')
            self.kpi.dat(None)
            self.thua.dat(None)
            return
        self.dot_ho, self.scan = ho_so_scan.ten_dot_theo_ho(self.con), ho_so_scan.dem_theo_ho(self.con)
        self.vd = van_dong.tinh_trang_tat_ca(self.con, self.ds)
        self.moc = thoi_han.moc_thu_hoi_tat_ca(self.con)
        self._ve_tong_quan()
        self._ve_moc()

    def _ve_tong_quan(self):
        """Thẻ chỉ số + bảng thửa còn vướng: tính từ số liệu đã nạp (không đọc lại CSDL lần hai)."""
        from . import bao_cao_gpmb
        self.tq = bao_cao_gpmb.tong_quan(self.con, ds=self.ds, tt=self.vd, moc=self.moc)
        self.kpi.dat(self.tq, thoi_han.so_ngay(self.con, 'van_dong'))
        self.thua.dat(self.tq)

    def _ve_moc(self):
        n = thoi_han.tat_ca_so_ngay(self.con)
        co_qd = [x for x in self.ds if x.qd]
        du = sum(1 for x in co_qd if self.moc.get(x.ma_ho, {}).get('du'))
        ngay = thoi_han.ngay_thong_bao(self.con)
        tb = f'thông báo thu hồi đất {thoi_han.hien_ngay(ngay)}' if ngay else \
            '<span style="color:#A12A1F;">chưa nhập ngày thông báo</span>'
        # một dòng (vừa màn hình 1366): chữ đầy đủ ở chú thích
        self.lb_moc.setText(f'<b>Mốc pháp lý:</b> {tb} · đất NN ≥ {n["thu_hoi_nn"]} ngày, PNN ≥ {n["thu_hoi_pnn"]} ngày · vận động '
                            f'{n["van_dong"]} ngày · đủ mốc <b>{du}/{len(co_qd)}</b> hộ')
        self.lb_moc.setToolTip(f'Ngày thông báo thu hồi đất: {thoi_han.hien_ngay(ngay) if ngay else "chưa nhập (chưa kiểm tra được mốc)"}'
                               f'\nThu hồi đất nông nghiệp sau ít nhất {n["thu_hoi_nn"]} ngày, đất phi nông nghiệp sau ít nhất '
                               f'{n["thu_hoi_pnn"]} ngày kể từ ngày thông báo\nThời hạn vận động: {n["van_dong"]} ngày\n'
                               f'Hộ đã có quyết định đủ mốc thu hồi: {du}/{len(co_qd)}\nSửa ở nút "Mốc pháp lý…"')

    def _vd(self, x) -> tuple:
        return van_dong.trang_thai_chung(self.vd.get(x.ma_ho, []))

    def _doi_qd(self):
        """Đổi danh sách hộ / quyết định đánh dấu: đếm lại số hộ từng điều kiện lọc (đổi ô Lọc, gõ tìm thì không đếm lại)."""
        dem = theo_doi.dem_loc(self.ds, self.qd_chon())
        ma_vd = [van_dong.trang_thai_chung(tt)[0] for tt in self.vd.values()]
        dem['dang_vd'], dem['du_cuong_che'] = ma_vd.count('dang_van_dong'), ma_vd.count('du_dk_cuong_che')
        for i in range(self.cb_loc.count()):
            k = self.cb_loc.itemData(i)
            self.cb_loc.setItemText(i, f'{self.TEN_LOC[k]} ({dem.get(k, 0)})' if self.ds else self.TEN_LOC[k])
        self.ve()

    def qd_chon(self) -> set:
        return {self.ds_qd_w.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.ds_qd_w.count())
                if self.ds_qd_w.item(i).checkState() == Qt.CheckState.Checked}

    def dat_loc(self, khoa: str = '', ds_qd: set | None = None, tu_khoa: str | None = None):
        self.cb_loc.blockSignals(True)
        self.cb_loc.setCurrentIndex(max(0, self.cb_loc.findData(khoa)))
        self.cb_loc.blockSignals(False)
        if ds_qd is not None:
            self.ds_qd_w.blockSignals(True)
            for i in range(self.ds_qd_w.count()):
                it = self.ds_qd_w.item(i)
                it.setCheckState(Qt.CheckState.Checked if it.data(Qt.ItemDataRole.UserRole) in ds_qd else Qt.CheckState.Unchecked)
            self.ds_qd_w.blockSignals(False)
        if tu_khoa is not None:
            self.o_tim.blockSignals(True)
            self.o_tim.setText(tu_khoa)
            self.o_tim.blockSignals(False)
        if ds_qd is not None:
            self._doi_qd()
        else:
            self.ve()

    def loc(self) -> list:
        k, qd = self.cb_loc.currentData() or '', self.qd_chon()
        tk = bo_dau(self.o_tim.text()).split()
        vd = {'dang_vd': 'dang_van_dong', 'du_cuong_che': 'du_dk_cuong_che'}.get(k, '')      # lọc theo vận động (ngoài LOC_TIEN_DO)

        def tim():
            kq = []
            for x in self.ds:
                if vd:
                    if self._vd(x)[0] != vd:
                        continue
                elif not theo_doi.hop_loc(x, k, qd):
                    continue
                if tk and not all(t in _chuoi_tim(x, 'td', lambda: (
                        str(x.ma_ho), x.ho_ten, x.dia_chi, x.theo_doi, x.ly_do_ban_giao,
                        *(f'{q["so_qd"]} {q["ly_do_chua_nhan"]}' for q in x.qd))) for t in tk):
                    continue
                kq.append(x)
            return kq
        return self._loc_nho((k, tuple(sorted(qd, key=str)), tuple(tk)), tim)

    def dong(self) -> list:
        qd_loc = self.qd_chon()
        kq = []
        for stt, x in enumerate(self.loc(), start=1):
            qd = [q for q in x.qd if not qd_loc or q['qd_id'] in qd_loc]
            nhan = [q for q in qd if q['da_chi_tra']]
            chua = [q for q in qd if not q['da_chi_tra']]
            kq.append((x, qd, [
                stt, x.ma_ho, x.ho_ten, x.dia_chi, self.moc.get(x.ma_ho, {}).get('chu', '') if x.qd else '', self._vd(x)[1],
                '\n'.join(f'{q["so_qd"]}' + (f' ({q["ngay_qd"]})' if q['ngay_qd'] else '') for q in qd),
                sum((_so(q['so_tien']) for q in qd), KHONG) if qd else None,
                sum((_so(q['chi_tra_so_tien']) or _so(q['so_tien']) for q in nhan), KHONG) if nhan else None,
                '\n'.join(f'{q["chi_tra_ngay"]} (QĐ {q["so_qd"]})' if len(qd) > 1 else q['chi_tra_ngay'] for q in nhan
                          if q['chi_tra_ngay']),
                '\n'.join(f'QĐ {q["so_qd"]}' + (f': {q["ly_do_chua_nhan"]}' if q['ly_do_chua_nhan'] else '') for q in chua),
                '\n'.join(Path(q['chung_tu']).name for q in nhan if q['chung_tu']),
                ('Đã bàn giao' + (f' {x.ban_giao_ngay}' if x.ban_giao_ngay else '')
                 + ('' if theo_doi.co_bien_ban_ban_giao(x) else ' (chưa có ngày biên bản)')) if x.da_ban_giao else 'Chưa',
                x.ly_do_ban_giao if not x.da_ban_giao else '', x.theo_doi,
                ho_so_scan.chu_hoan_tat(x, self.dot_ho.get(x.ma_ho, '')),
                f'{self.scan[x.ma_ho]} file' if self.scan.get(x.ma_ho) else '']))
        return kq

    def ve(self):
        self._danh_dau_kpi()
        # chuỗi hiển thị + kiểu riêng của các ô cần tô (bảng ảo: chỉ vẽ ô đang hiện, không dựng 65.000 QTableWidgetItem)
        hien, ma, kieu = [], [], {}
        for r, (x, qd, gt) in enumerate(self.dong()):
            hien.append(_chu(gt, tien=(self.C_TONG, self.C_NHAN)))
            ma.append(x.ma_ho)
            if gt[self.C_CHUA]:
                kieu[(r, self.C_CHUA)] = dict(nen=DO)
            if gt[self.C_NGAY]:
                kieu[(r, self.C_NGAY)] = dict(nen=XANH)
            # xanh: bàn giao có ngày biên bản (nấc bàn giao danh sách hộ); tích thiếu ngày / chưa bàn giao mà có QĐ: vàng
            nen_bg = XANH if theo_doi.co_bien_ban_ban_giao(x) else VANG if qd or x.da_ban_giao else None
            if nen_bg is not None:
                kieu[(r, self.C_BG)] = dict(nen=nen_bg)
            if gt[self.C_BIEN_LAI]:
                kieu[(r, self.C_BIEN_LAI)] = dict(mau_chu=MAU_LIEN_KET, goi_y='Nhấp đúp để mở biên lai / biên bản chi trả:\n' +
                                                  '\n'.join(q['chung_tu'] for q in qd if q['chung_tu']))
            if gt[self.C_MOC]:                            # mốc thu hồi đất: xanh đủ mốc, vàng chưa đủ, xám chưa có ngày thông báo
                du = self.moc.get(x.ma_ho, {}).get('du')
                kieu[(r, self.C_MOC)] = dict(nen=XAM if du is None else XANH if du else VANG)
            if gt[self.C_HOAN_TAT]:
                kieu[(r, self.C_HOAN_TAT)] = dict(nen=XANH, dam=True)
            if gt[self.C_SCAN]:
                kieu[(r, self.C_SCAN)] = dict(mau_chu=MAU_LIEN_KET, goi_y='Nhấp đúp để mở hồ sơ đính kèm của hộ')
            ma_vd = self._vd(x)[0]
            if ma_vd:
                kieu[(r, self.C_VD)] = dict(nen={'du_dk_cuong_che': DO, 'dang_van_dong': VANG}.get(ma_vd, XANH),
                                            dam=ma_vd == 'du_dk_cuong_che')
        self.bang.dat_du_lieu(hien, ma, kieu)
        self.dang_hien = ma

    def _nhap_dup(self, r, c):
        ma = self.bang.ma_dong(r)
        if ma is None:
            return
        if c == self.C_SCAN:                             # cột hồ sơ scan: một file mở luôn, nhiều file / chưa có -> menu
            from .man_hinh_ho_so_scan import mo_nhanh
            mo_nhanh(self, self.con, int(ma), self.chi_doc, sau=self.nap)
            return
        if c == self.C_BIEN_LAI:                         # cột biên lai: mở file chứng từ
            x = next((y for y in self.ds if y.ma_ho == ma), None)
            for q in x.qd if x else []:
                if q['chung_tu']:
                    mo_file(q['chung_tu'])
            return
        self.mo_ho.emit(int(ma))

    def hoan_tat_ctbt(self):
        """Hộ hoàn tất công tác bồi thường theo đợt (có QĐ + đã bàn giao) - hộp xem + xuất Excel. im_lang: trả hộp, không hiện."""
        if self.con is None:
            return None
        from .man_hinh_ho_so_scan import HopHoanTatCTBT
        dlg = HopHoanTatCTBT(self.con, self, self.ds, self._thu_muc_ho_so(), self._ten_du_an())
        dlg.im_lang = self.im_lang
        if not self.im_lang:
            dlg.exec()
        return dlg

    def _thu_muc_ho_so(self) -> str:
        try:
            from .csdl import doc_cai_dat
            return doc_cai_dat(self.con, 'THU_MUC_HO_SO', '')
        except Exception:                                # noqa: BLE001 - chỉ là thư mục gợi ý
            return ''

    def ban_giao(self, ds_ma: list | None = None, gia_tri: dict | None = None):
        ds_ma = self.ma_da_chon() if ds_ma is None else ds_ma
        if not ds_ma or self.chi_doc:
            self.bao('Chọn các hộ trong bảng (giữ Ctrl / Shift để chọn nhiều).', loi=False)
            return 0
        if gia_tri is None:
            dlg = HopBanGiao(self, len(ds_ma), so_chua_qd=len(theo_doi.ho_chua_phe_duyet(self.con, ds_ma)))
            if not dlg.exec():
                return 0
            gia_tri = dlg.gia_tri()
        try:
            n = theo_doi.ghi_ban_giao(self.con, ds_ma, gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return 0
        return self._da_ghi(n)

    def so_van_dong(self, ma_ho=None):
        """Mở sổ nhật ký vận động (Bước 14, 15) của hộ ma_ho; không truyền thì hộ đang chọn trên bảng (không chọn: hộ cần vận động
        đầu tiên). im_lang: trả hộp thoại, không hiện (kiểm thử)."""
        if self.con is None:
            return None
        ma = ma_ho if ma_ho is not None else (self.ma_da_chon() or [None])[0]
        dlg = HopNhatKyVanDong(self.con, ma, self, self.chi_doc)
        dlg.im_lang = self.im_lang
        if self.im_lang:
            return dlg
        dlg.exec()
        if dlg.thay_doi:
            self._da_ghi()                                   # trạng thái vận động đổi: nạp lại + báo cửa sổ chính (báo cáo tiến độ)
        return dlg

    def xuat_cuong_che(self, file=None):
        """Excel danh sách đề nghị ban hành quyết định cưỡng chế thu hồi đất (hộ đủ điều kiện theo Điều 89)."""
        if self.con is None:
            return None
        if not van_dong.ds_cuong_che(self.con, ds_tong_hop=self.ds):
            self.bao('Chưa có hộ nào đủ điều kiện cưỡng chế: cần vận động quá '
                     f'{thoi_han.so_ngay(self.con, "van_dong")} ngày mà hộ vẫn chưa nhận tiền / chưa bàn giao mặt bằng '
                     '(ghi các buổi vận động ở "Sổ nhật ký vận động…").', loi=False)
            return None
        return self._xuat(file, 'Lưu danh sách đề nghị cưỡng chế', 'DS_DeNghi_CuongChe.xlsx',
                          lambda f: van_dong.xuat_ds_cuong_che(self.con, f))

    def xuat_bao_cao(self, file=None):
        """Excel báo cáo tiến độ GPMB (Bước 16): chỉ số điều hành + danh sách thửa còn vướng - văn bản báo cáo định kỳ."""
        if self.con is None:
            return None
        from . import bao_cao_gpmb
        return self._xuat(file, 'Lưu báo cáo tiến độ GPMB', 'BaoCaoTienDoGPMB.xlsx', lambda f: bao_cao_gpmb.xuat_excel(self.con, f))

    def luu_ngay_thong_bao(self, chu: str):
        """Ghi ngày thông báo thu hồi đất của dự án (trống = xóa) rồi vẽ lại mốc thu hồi, thẻ chỉ số. Trả chuỗi ngày đã chuẩn hóa.
        Ô nhập nằm trong hộp "Mốc pháp lý…" (1.0.00 - trước đây chiếm hàng trên cùng của trang)."""
        if self.con is None or self.chi_doc:
            return None
        try:
            moi = thoi_han.dat_ngay_thong_bao(self.con, chu)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.moc = thoi_han.moc_thu_hoi_tat_ca(self.con)
        self._ve_tong_quan()
        self._ve_moc()
        self.ve()
        return moi

    def mo_moc(self, gia_tri: dict | None = None, ngay: str | None = None):
        """Hộp "Mốc pháp lý…": ngày thông báo thu hồi đất + số ngày thẩm định, mốc thu hồi đất nông nghiệp / phi nông nghiệp, vận
        động. gia_tri / ngay: truyền thẳng (kiểm thử, không hiện hộp). True nếu có đổi."""
        if self.con is None or self.chi_doc:
            return False
        if gia_tri is None and ngay is None:
            dlg = HopMocThoiHan(self.con, self, ngay_thong_bao=True)
            if not dlg.exec():
                return False
            gia_tri, ngay = dlg.gia_tri(), dlg.ngay_thong_bao()
        doi = False
        if ngay is not None and ngay.strip() != thoi_han.hien_ngay(thoi_han.ngay_thong_bao(self.con)):
            if self.luu_ngay_thong_bao(ngay) is None:
                return False
            doi = True
        if gia_tri:
            try:
                doi = bool(thoi_han.dat_so_ngay(self.con, gia_tri)) or doi
            except LoiNhap as e:
                self.bao(str(e))
                return doi
        if doi:
            self._da_ghi()
        return doi

    def xuat(self, file=None):
        if self.con is None:
            return None
        k = self.cb_loc.currentData()
        tieu = 'THEO DÕI TIẾN ĐỘ CHI TRẢ, BÀN GIAO MẶT BẰNG' + (f' - {self.TEN_LOC[k].upper()}' if k else '')
        return self._xuat(file, 'Lưu danh sách theo dõi tiến độ', 'TheoDoiTienDo.xlsx', lambda f: theo_doi.xuat_excel(
            f, tieu, self.COT, [d for _, _, d in self.dong()], [5, 7, 24, 24, 40, 44, 22, 15, 15, 14, 28, 22, 16, 22, 22], None,
            self._ten_du_an()))


# ---------------------------------------------------------------- hộp thoại
def _o_chon_file(o: QLineEdit, cha, tieu_de: str) -> QHBoxLayout:
    h = QHBoxLayout()
    h.addWidget(o, 1)
    b = QPushButton('Chọn file…')
    b.clicked.connect(lambda: _chon_file(o, cha, tieu_de))
    h.addWidget(b)
    b2 = QPushButton('Mở')
    b2.clicked.connect(lambda: mo_file(o.text().strip()))
    h.addWidget(b2)
    return h


def _chon_file(o: QLineEdit, cha, tieu_de: str):
    p, _ = QFileDialog.getOpenFileName(cha, tieu_de, o.text(), 'Văn bản, ảnh scan (*.pdf *.docx *.doc *.xlsx *.xls *.jpg *.jpeg *.png);;'
                                                              'Tất cả (*.*)')
    if p:
        o.setText(p)


def _nut_luu(hop: QDialog) -> QDialogButtonBox:
    nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
    nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
    nut.accepted.connect(hop.accept)
    nut.rejected.connect(hop.reject)
    return nut


class HopQuyetDinh(_Hop):
    """Thêm / sửa thông tin một quyết định (số, ngày, trích yếu, tổng kinh phí, file)."""

    def __init__(self, parent=None, q: theo_doi.QuyetDinh | None = None):
        super().__init__(parent)
        self.setWindowTitle('Sửa quyết định' if q else 'Thêm quyết định phê duyệt')
        self.resize(640, 300)
        self.o = dict(so=QLineEdit(q.so if q else ''), ngay=QLineEdit(q.ngay if q else ''),
                      trich_yeu=QLineEdit(q.trich_yeu if q else ''),
                      tong_tien=QLineEdit(_tien(q.tong_tien) if q else ''), file=QLineEdit(q.file if q else ''),
                      ghi_chu=QLineEdit(q.ghi_chu if q else ''))
        self.o['so'].setPlaceholderText('ví dụ 1234/QĐ-UBND')
        self.o['ngay'].setPlaceholderText('ngày/tháng/năm')
        self.o['trich_yeu'].setPlaceholderText('ví dụ: Phê duyệt PA đợt 2 / Phê duyệt bổ sung')
        self.o['tong_tien'].setPlaceholderText('tổng kinh phí ghi trong quyết định (để đối chiếu, có thể bỏ trống)')
        f = QFormLayout(self)
        f.addRow('Số quyết định:', self.o['so'])
        f.addRow('Ngày ban hành:', self.o['ngay'])
        f.addRow('Trích yếu:', self.o['trich_yeu'])
        f.addRow('Tổng kinh phí (đ):', self.o['tong_tien'])
        f.addRow('File quyết định:', _o_chon_file(self.o['file'], self, 'Chọn file quyết định'))
        f.addRow('Ghi chú:', self.o['ghi_chu'])
        f.addRow(_nut_luu(self))

    def gia_tri(self) -> dict:
        return {k: w.text().strip() for k, w in self.o.items()}


class HopQDHo(_Hop):
    """Số liệu của một hộ trong một quyết định: số tiền (theo hạng mục), phương án / quyết định chi tiết, chi trả."""

    def __init__(self, con, ma_ho: int, qd_id: int | None, dong: dict | None = None, parent=None, chon_qd: bool = False):
        super().__init__(parent)
        self.con, self.ma_ho = con, ma_ho
        dong = dong or {}
        ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
        self.setWindowTitle(f'Quyết định phê duyệt - {ten[0] if ten else ""}')
        self.resize(720, 640)
        self.cb_qd = QComboBox()
        self.cb_qd.setEditable(False)
        for q in theo_doi.ds_quyet_dinh(con):
            self.cb_qd.addItem(q.nhan, q.id)
        self.cb_qd.addItem('+ Quyết định mới (nhập số, ngày bên dưới)', None)
        if qd_id is not None:
            self.cb_qd.setCurrentIndex(max(0, self.cb_qd.findData(qd_id)))
        else:
            self.cb_qd.setCurrentIndex(self.cb_qd.count() - 1)
        self.cb_qd.setEnabled(chon_qd)
        self.o_so_qd, self.o_ngay_qd = QLineEdit(), QLineEdit()
        self.o_so_qd.setPlaceholderText('số quyết định mới, ví dụ 3334/QĐ-UBND')
        self.o_ngay_qd.setPlaceholderText('ngày/tháng/năm')
        self.o_file_qd = QLineEdit()
        self.cb_qd.currentIndexChanged.connect(lambda *_: self._doi_qd())
        self.o = {}
        for k in theo_doi.TRUONG_QD_HO:
            if k == 'da_chi_tra':
                w = QCheckBox('Đã nhận tiền theo quyết định này')
                w.setChecked(bool(dong.get(k)))
            elif k in ('ly_do_chua_nhan', 'ghi_chu'):
                w = QPlainTextEdit(str(dong.get(k) or ''))
                w.setMaximumHeight(56)
            else:
                v = dong.get(k) or ''
                w = QLineEdit(_tien(v) if k in theo_doi.TIEN_QD else str(v))
                if k in theo_doi.NGAY_QD:
                    w.setPlaceholderText('ngày/tháng/năm')
                if k in theo_doi.TIEN_QD:
                    w.setPlaceholderText('đồng')
            self.o[k] = w
        self.o['da_chi_tra'].toggled.connect(lambda *_: self._doi_chi_tra())
        b_pa = QPushButton('Lấy số tiền theo phương án hiện tại')
        b_pa.clicked.connect(lambda: self.lay_theo_pa())
        b_file = QPushButton('Đọc từ file quyết định…')
        b_file.setToolTip('Chọn file quyết định (PDF, Word, Excel, ảnh scan): tự đọc số, ngày quyết định và số tiền của hộ')
        b_file.clicked.connect(lambda: self.doc_file())
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        g0 = QGroupBox('Quyết định')
        f0 = QFormLayout(g0)
        f0.addRow('Quyết định:', self.cb_qd)
        f0.addRow('Số quyết định mới:', self.o_so_qd)
        f0.addRow('Ngày ban hành:', self.o_ngay_qd)
        f0.addRow('File quyết định:', _o_chon_file(self.o_file_qd, self, 'Chọn file quyết định'))
        g1 = QGroupBox('Số tiền phê duyệt của hộ trong quyết định')
        f1 = QFormLayout(g1)
        for k in ('so_tien', 'tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'tien_thuong'):
            f1.addRow(theo_doi.TEN_TRUONG[k] + ':', self.o[k])
        h = QHBoxLayout()
        h.addWidget(b_pa)
        h.addWidget(b_file)
        h.addStretch(1)
        f1.addRow(h)
        f1.addRow(self.lb)
        g2 = QGroupBox('Phương án chi tiết, quyết định chi tiết')
        f2 = QFormLayout(g2)
        for k in ('so_pa', 'ngay_pa', 'qd_ct_so', 'qd_ct_ngay'):
            f2.addRow(theo_doi.TEN_TRUONG[k] + ':', self.o[k])
        g3 = QGroupBox('Chi trả theo quyết định này')
        f3 = QFormLayout(g3)
        f3.addRow(self.o['da_chi_tra'])
        f3.addRow('Ngày nhận tiền:', self.o['chi_tra_ngay'])
        f3.addRow('Số tiền đã nhận (đ):', self.o['chi_tra_so_tien'])
        f3.addRow('Biên lai / biên bản:', _o_chon_file(self.o['chung_tu'], self, 'Chọn biên lai / biên bản chi trả'))
        f3.addRow('Lý do chưa nhận:', self.o['ly_do_chua_nhan'])
        f3.addRow('Ghi chú:', self.o['ghi_chu'])
        lo = QVBoxLayout(self)
        for g in (g0, g1, g2, g3):
            lo.addWidget(g)
        lo.addWidget(_nut_luu(self))
        self._doi_qd()
        self._doi_chi_tra()

    def _doi_qd(self):
        moi = self.cb_qd.currentData() is None
        for w in (self.o_so_qd, self.o_ngay_qd, self.o_file_qd):
            w.setEnabled(moi)

    def _doi_chi_tra(self):
        da = self.o['da_chi_tra'].isChecked()
        for k in ('chi_tra_ngay', 'chi_tra_so_tien', 'chung_tu'):
            self.o[k].setEnabled(da)
        self.o['ly_do_chua_nhan'].setEnabled(not da)

    def lay_theo_pa(self):
        for k, v in theo_doi.chi_tiet_tu_phuong_an(self.con, self.ma_ho).items():
            self.o[k].setText(_tien(v))

    def doc_file(self, file=None):
        """Đọc số, ngày quyết định và số tiền của hộ từ file quyết định (quan_ly.doc_qd_mot_ho, bản scan: OCR)."""
        from . import ocr, quan_ly
        if file is None:
            file, _ = QFileDialog.getOpenFileNames(self, 'Chọn file quyết định (và bảng tổng hợp kèm theo - chọn được nhiều file)',
                                                   '', 'Quyết định (*.pdf *.docx *.xlsx *.jpg *.jpeg *.png)')
            if not file:
                return None
        from .man_hinh_quan_ly import doc_co_tien_do
        try:
            kq = doc_co_tien_do(self, quan_ly.doc_qd_mot_ho, self.con, file, self.ma_ho)
        except ocr.DaHuy:
            return None
        except (LoiNhap, ocr.LoiOCR, OSError, ValueError) as e:
            self.lb.setText(f'Không tự đọc được: {e}')
            return None
        if kq.so_qd:
            qd = theo_doi.tim_qd(self.con, kq.so_qd, kq.ngay)
            if qd is not None and self.cb_qd.isEnabled():
                self.cb_qd.setCurrentIndex(self.cb_qd.findData(qd))
            elif qd is None and self.cb_qd.isEnabled():
                self.cb_qd.setCurrentIndex(self.cb_qd.count() - 1)
                self.o_so_qd.setText(kq.so_qd)
                self.o_ngay_qd.setText(kq.ngay)
                self.o_file_qd.setText(str(file if isinstance(file, (str, Path)) else file[0]))
        if kq.so_tien is not None:
            self.o['so_tien'].setText(vn(kq.so_tien))
            for k in ('tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'tien_thuong'):
                if kq.chi_tiet:                          # bảng kèm theo có cột từng hạng mục: lấy đúng theo quyết định
                    self.o[k].setText(vn(kq.chi_tiet[k]) if k in kq.chi_tiet else '')
        self.lb.setText(('Đọc được: ' + ', '.join(x for x in (f'QĐ {kq.so_qd}' if kq.so_qd else '', kq.ngay,
                                                             f'{vn(kq.so_tien)} đ' if kq.so_tien is not None else '') if x) +
                         (f' ({kq.cach})' if kq.cach else '') + ('. ' + ' '.join(kq.ghi_chu) if kq.ghi_chu else '')))
        self.lb.setStyleSheet(f'QLabel {{ background: {(XANH if kq.chac_chan and not kq.ghi_chu else VANG).name()}; '
                              'padding: 5px; border-radius: 4px; }')
        return kq

    def qd_id(self):
        """id quyết định đã chọn, hoặc tạo quyết định mới theo số / ngày đã nhập."""
        q = self.cb_qd.currentData()
        if q is not None:
            return q
        so = self.o_so_qd.text().strip()
        cu = theo_doi.tim_qd(self.con, so, self.o_ngay_qd.text())
        if cu is not None:
            return cu
        return theo_doi.luu_qd(self.con, None, so, self.o_ngay_qd.text(), file=self.o_file_qd.text().strip())

    def gia_tri(self) -> dict:
        kq = {}
        for k, w in self.o.items():
            kq[k] = w.isChecked() if isinstance(w, QCheckBox) else (w.toPlainText() if isinstance(w, QPlainTextEdit) else w.text())
        return kq


class HopChonHo(_Hop):
    """Chọn hộ (nhiều) để đưa vào quyết định."""

    def __init__(self, con, parent=None, loai_tru: list | None = None):
        super().__init__(parent)
        self.setWindowTitle('Chọn hộ đưa vào quyết định')
        self.resize(520, 600)
        bo = set(loai_tru or [])
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm (không cần dấu)…')
        self.ds = QListWidget()
        for r in con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu, ma_ho'):
            if r[0] in bo:
                continue
            it = QListWidgetItem(f'{r[1]}. {r[2]}')
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, r[0])
            self.ds.addItem(it)
        loc_khi_ngung_go(self.o_tim, self._loc)
        lo = QVBoxLayout(self)
        lo.addWidget(self.o_tim)
        lo.addWidget(self.ds, 1)
        lo.addWidget(QLabel('Số tiền của hộ điền sẵn theo phương án hiện tại (sửa lại được).'))
        lo.addWidget(_nut_luu(self))

    def _loc(self, t):
        tk = bo_dau(t).split()
        for i in range(self.ds.count()):
            it = self.ds.item(i)
            it.setHidden(bool(tk) and not all(x in bo_dau(it.text()) for x in tk))

    def chon(self) -> list:
        return [self.ds.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.ds.count())
                if self.ds.item(i).checkState() == Qt.CheckState.Checked]


class HopNgayChiTra(_Hop):
    def __init__(self, parent=None, so_ho: int = 1):
        super().__init__(parent)
        self.setWindowTitle(f'Ghi nhận đã nhận tiền - {so_ho} hộ')
        from datetime import date
        self.o_ngay = QLineEdit(date.today().strftime('%d/%m/%Y'))
        self.o_file = QLineEdit()
        f = QFormLayout(self)
        f.addRow('Ngày nhận tiền:', self.o_ngay)
        f.addRow('Biên lai / biên bản:', _o_chon_file(self.o_file, self, 'Chọn biên lai / biên bản chi trả'))
        f.addRow(QLabel('Số tiền đã nhận = số tiền phê duyệt của hộ trong quyết định (sửa riêng từng hộ nếu khác).'))
        f.addRow(_nut_luu(self))


class HopBanGiao(_Hop):
    """so_chua_qd: số hộ (trong so_ho hộ đang chọn) chưa có quyết định phê duyệt. Có hộ như vậy thì hộp KHÔNG tích sẵn "Đã bàn giao
    mặt bằng" và hiện cảnh báo (bàn giao trước khi phê duyệt là trường hợp riêng - người dùng tự tích)."""

    def __init__(self, parent=None, so_ho: int = 1, x=None, so_chua_qd: int = 0):
        super().__init__(parent)
        self.setWindowTitle(f'Bàn giao mặt bằng - {so_ho} hộ')
        self.resize(560, 260)
        self.o_da = QCheckBox('Đã bàn giao mặt bằng')
        self.o_da.setChecked(not so_chua_qd if x is None else x.da_ban_giao)
        self.lb_canh_bao = QLabel('')
        self.lb_canh_bao.setWordWrap(True)
        self.lb_canh_bao.setVisible(bool(so_chua_qd))
        if so_chua_qd:
            dat_trang_thai(self.lb_canh_bao, 'canh_bao',
                           f'{so_chua_qd}/{so_ho} hộ chưa có quyết định phê duyệt (chưa chi trả). Chỉ tích "Đã bàn giao mặt bằng" khi '
                           'các hộ này đã bàn giao thật (bàn giao trước khi phê duyệt); bỏ tích = ghi "chưa bàn giao".')
        # biên bản bàn giao KHÔNG có số, chỉ có ngày (người dùng 17/10/2026): ngày ký biên bản là chứng cứ bàn giao - KHÔNG điền sẵn
        # ngày hôm nay (trước đây điền sẵn: một lần bấm Lưu cả bảng thành "đã bàn giao" đúng ngày bấm)
        self.o_ngay = QLineEdit(x.ban_giao_ngay if x is not None else '')
        self.o_ngay.setPlaceholderText('dd/mm/yyyy - ngày ký biên bản bàn giao')
        self.o_ly_do = QPlainTextEdit(x.ly_do_ban_giao if x is not None else '')
        self.o_ly_do.setMaximumHeight(60)
        self.o_file = QLineEdit(x.bien_ban_ban_giao if x is not None else '')
        # file scan biên bản: KHÔNG bắt buộc; một biên bản cho nhiều hộ (người dùng 17/10/2026): chỉ ghi ĐƯỜNG DẪN cho mọi hộ đang
        # chọn - KHÔNG chép file vào từng hộ; để trống khi chọn nhiều hộ = giữ file đã ghi của từng hộ (gia_tri bỏ trường này)
        self.nhieu_ho = so_ho > 1 and x is None
        self.o_file.setPlaceholderText('File scan biên bản (không bắt buộc)' +
                                       (' - dùng chung cho các hộ đang chọn' if self.nhieu_ho else ''))
        self.lb_chung = QLabel(f'Một biên bản cho nhiều hộ: nhập ngày biên bản và (nếu có) chọn file scan MỘT lần cho cả {so_ho} hộ - '
                               'phần mềm chỉ ghi đường dẫn, không chép file. Ô file để trống: giữ file đã ghi của từng hộ.')
        self.lb_chung.setWordWrap(True)
        self.lb_chung.setProperty('vai', 'phu')
        self.lb_chung.setVisible(self.nhieu_ho)
        self.o_da.toggled.connect(lambda d: (self.o_ngay.setEnabled(d), self.o_ly_do.setEnabled(not d)))
        f = QFormLayout(self)
        f.addRow(self.lb_canh_bao)
        f.addRow(self.o_da)
        f.addRow('Ngày biên bản bàn giao:', self.o_ngay)
        f.addRow('File biên bản:', _o_chon_file(self.o_file, self, 'Chọn file scan biên bản bàn giao'))
        f.addRow('', self.lb_chung)
        f.addRow('Lý do chưa bàn giao:', self.o_ly_do)
        f.addRow(_nut_luu(self))
        self.o_ngay.setEnabled(self.o_da.isChecked())
        self.o_ly_do.setEnabled(not self.o_da.isChecked())

    def accept(self):
        if self.o_da.isChecked() and not self.o_ngay.text().strip():   # bàn giao phải có ngày biên bản (chứng cứ của nấc bàn giao)
            dat_trang_thai(self.lb_canh_bao, 'loi', 'Nhập ngày biên bản bàn giao (dd/mm/yyyy) - hoặc bỏ tích "Đã bàn giao mặt bằng".')
            self.lb_canh_bao.setVisible(True)
            self.o_ngay.setFocus()
            return
        super().accept()

    def gia_tri(self) -> dict:
        da = self.o_da.isChecked()
        gt = dict(da_ban_giao=da, ban_giao_ngay=self.o_ngay.text() if da else '', ly_do_ban_giao=self.o_ly_do.toPlainText(),
                  bien_ban_ban_giao=self.o_file.text().strip())
        if self.nhieu_ho and not gt['bien_ban_ban_giao']:
            del gt['bien_ban_ban_giao']                 # nhiều hộ, ô trống: không xóa biên bản riêng đã ghi của từng hộ
        return gt


class HopMocThoiHan(_Hop):
    """Các mốc thời hạn pháp lý (Mục IV QĐ 18/2026/QĐ-UBND) của dự án: số ngày KHÔNG gán cứng - sửa khi quy định đổi."""

    def __init__(self, con, parent=None, ngay_thong_bao: bool = False):
        super().__init__(parent)
        self.setWindowTitle('Mốc pháp lý của dự án')
        self.resize(600, 340)
        self.o = {}
        f = QFormLayout(self)
        self.o_ngay = None
        if ngay_thong_bao:                              # 1.0.00: ô ngày thông báo chuyển từ trang Tiến độ chi trả & Bàn giao vào đây
            self.o_ngay = QLineEdit(thoi_han.hien_ngay(thoi_han.ngay_thong_bao(con)))
            self.o_ngay.setPlaceholderText('dd/mm/yyyy')
            self.o_ngay.setMaximumWidth(140)
            self.o_ngay.setToolTip('Ngày thông báo thu hồi đất (Bước 3) - mốc tính thời hạn thu hồi đất nông nghiệp / phi nông '
                                   'nghiệp. Để trống = chưa có thông báo.')
            f.addRow('Ngày thông báo thu hồi đất:', self.o_ngay)
        f.addRow(QLabel('Số ngày tính theo ngày dương lịch. Giá trị mặc định theo đặc tả ARCH-PABT-2026-V7 (Mục IV QĐ 18/2026/QĐ-UBND);\n'
                        'đối chiếu văn bản gốc khi áp dụng cho dự án.'))
        for k, (_, mac_dinh, nhan, can_cu) in thoi_han.MOC.items():
            o = QSpinBox()
            o.setRange(1, 3650)
            o.setSuffix(' ngày')
            o.setValue(thoi_han.so_ngay(con, k))
            o.setToolTip(f'{can_cu}. Mặc định {mac_dinh} ngày.')
            self.o[k] = o
            f.addRow(f'{nhan}:', o)
        f.addRow(_nut_luu(self))

    def gia_tri(self) -> dict:
        return {k: o.value() for k, o in self.o.items()}

    def ngay_thong_bao(self) -> str | None:
        """Chữ ô ngày thông báo (None khi hộp không có ô này)."""
        return None if self.o_ngay is None else self.o_ngay.text().strip()


class HopNhatKyVanDong(_Hop):
    """Sổ nhật ký vận động của một hộ (Bước 14, 15 Mục IV QĐ 18/2026): các buổi vận động hộ không nhận tiền bồi thường / không
    bàn giao mặt bằng. Hết thời hạn vận động (mặc định 10 ngày kể từ buổi đầu) mà hộ vẫn chưa nhận tiền / chưa bàn giao: hộ chuyển
    sang "Đủ điều kiện cưỡng chế thu hồi đất theo Điều 89"."""
    COT = ['Ngày', 'Việc vận động', 'Hình thức', 'Thành phần', 'Nội dung', 'Kết quả', 'Biên bản']

    def __init__(self, con, ma_ho=None, parent=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc, self.thay_doi = con, chi_doc, False
        self.setWindowTitle('Sổ nhật ký vận động - Bước 14, 15 Mục IV QĐ 18/2026/QĐ-UBND')
        self.resize(1000, 640)                             # 1.0.02: không vượt 1024 x 680 (màn hình 1366 @125%)
        self.ds = theo_doi.tong_hop(con, tinh_pa=False)
        self.cb_ho = QComboBox()
        self.cb_ho.setMinimumWidth(360)
        buoi = {b['ma_ho'] for b in van_dong.ds_buoi(con)}
        # hộ có buổi vận động / cần vận động lên đầu danh sách
        for x in sorted(self.ds, key=lambda x: (not (x.ma_ho in buoi or van_dong.viec_ap_dung(x)), x.thu_tu, x.ma_ho)):
            dau = '● ' if (x.ma_ho in buoi or van_dong.viec_ap_dung(x)) else ''
            self.cb_ho.addItem(f'{dau}{x.ho_ten}', x.ma_ho)
        if ma_ho is not None:
            self.cb_ho.setCurrentIndex(max(0, self.cb_ho.findData(ma_ho)))
        self.cb_ho.currentIndexChanged.connect(lambda *_: self.nap())
        self.lb_tt = QLabel('')
        self.lb_tt.setWordWrap(True)
        self.bang = _bang(self.COT)
        for c, w in enumerate((90, 190, 150, 170, 280, 150, 120)):
            self.bang.setColumnWidth(c, w)
        self.bang.itemSelectionChanged.connect(self._chon_dong)
        # ---- biểu mẫu thêm / sửa một buổi
        from datetime import date
        self.cb_viec = QComboBox()
        for k, t in van_dong.VIEC.items():
            self.cb_viec.addItem(t, k)
        self.o_ngay = QLineEdit(date.today().strftime('%d/%m/%Y'))
        self.o_ngay.setMaximumWidth(130)
        self.cb_hinh_thuc = QComboBox()
        self.cb_hinh_thuc.setEditable(True)
        self.cb_hinh_thuc.addItems(van_dong.HINH_THUC)
        self.o_thanh_phan = QLineEdit()
        self.o_thanh_phan.setPlaceholderText('Tổ vận động, đại diện UBND xã, trưởng ấp…')
        self.o_noi_dung = QPlainTextEdit()
        self.o_noi_dung.setMaximumHeight(64)
        self.o_noi_dung.setPlaceholderText('Nội dung vận động, ý kiến của hộ')
        self.cb_ket_qua = QComboBox()
        for k, t in van_dong.KET_QUA:
            self.cb_ket_qua.addItem(t, k)
        self.o_bien_ban = QLineEdit()
        form = QGroupBox('Ghi buổi vận động')
        f = QFormLayout(form)
        h1 = QHBoxLayout()
        h1.addWidget(self.cb_viec, 1)
        h1.addWidget(QLabel('Ngày:'))
        h1.addWidget(self.o_ngay)
        h1.addWidget(QLabel('Kết quả:'))
        h1.addWidget(self.cb_ket_qua, 1)
        f.addRow('Việc vận động:', h1)
        h2 = QHBoxLayout()
        h2.addWidget(self.cb_hinh_thuc, 1)
        h2.addWidget(QLabel('Thành phần:'))
        h2.addWidget(self.o_thanh_phan, 2)
        f.addRow('Hình thức:', h2)
        f.addRow('Nội dung:', self.o_noi_dung)
        f.addRow('Biên bản vận động:', _o_chon_file(self.o_bien_ban, self, 'Chọn biên bản vận động'))
        self.nut = {}
        h_nut = QHBoxLayout()
        _nut([('Thêm buổi vận động', lambda: self.them()), ('Cập nhật buổi đang chọn', lambda: self.sua()),
              ('Xóa buổi đang chọn', lambda: self.xoa())], h_nut, self.nut)
        h_nut.addStretch(1)
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.accept)
        h_nut.addWidget(b_dong)
        h_ho = QHBoxLayout()
        h_ho.addWidget(QLabel('Hộ:'))
        h_ho.addWidget(self.cb_ho)
        h_ho.addStretch(1)
        lo = QVBoxLayout(self)
        lo.addLayout(h_ho)
        lo.addWidget(self.lb_tt)
        lo.addWidget(self.bang, 1)
        lo.addWidget(form)
        lo.addLayout(h_nut)
        for b in self.nut.values():
            b.setEnabled(not chi_doc)
        form.setEnabled(not chi_doc)
        self.nap()

    def ma_ho(self):
        return self.cb_ho.currentData()

    def chon_ho(self, ma_ho):
        self.cb_ho.setCurrentIndex(max(0, self.cb_ho.findData(ma_ho)))

    def _x(self):
        return next((x for x in self.ds if x.ma_ho == self.ma_ho()), None)

    def nap(self, chon_id=None):
        """Bảng các buổi của hộ đang chọn + dòng trạng thái (đang vận động, còn bao nhiêu ngày / đủ điều kiện cưỡng chế)."""
        ma = self.ma_ho()
        self.ds_buoi = van_dong.ds_buoi(self.con, ma) if ma is not None else []
        self.bang.blockSignals(True)
        self.bang.setRowCount(len(self.ds_buoi))
        for r, b in enumerate(self.ds_buoi):
            gt = (b['ngay'], van_dong.VIEC.get(b['viec'], b['viec']), b['hinh_thuc'], b['thanh_phan'], b['noi_dung'],
                  van_dong.TEN_KET_QUA.get(b['ket_qua'], b['ket_qua']), Path(b['bien_ban']).name if b['bien_ban'] else '')
            for c, v in enumerate(gt):
                _o(self.bang, r, c, v, du_lieu=b['id'] if c == 0 else None)
        self.bang.blockSignals(False)
        if chon_id is not None:
            for r, b in enumerate(self.ds_buoi):
                if b['id'] == chon_id:
                    self.bang.selectRow(r)
        x = self._x()
        n = thoi_han.so_ngay(self.con, 'van_dong')
        if x is None:
            self.lb_tt.setText('')
            return
        tt = van_dong.tinh_trang_ho(x, self.ds_buoi, n, thoi_han.hom_nay_hoac(None))
        ap = van_dong.viec_ap_dung(x)
        if tt:
            ma_tt, chu = van_dong.trang_thai_chung(tt)
            muc = {'du_dk_cuong_che': 'loi', 'dang_van_dong': 'canh_bao'}.get(ma_tt, 'dat' if ma_tt == 'hoan_thanh' else 'tin')
            if ma_tt == '':
                chu = '; '.join(f'{van_dong.VIEC[t.viec]}: {t.chu}' for t in tt)
            dat_trang_thai(self.lb_tt, muc, chu + f'  (thời hạn vận động {n} ngày kể từ buổi đầu tiên)')
        elif ap:
            dat_trang_thai(self.lb_tt, 'tin', f'Hộ cần vận động ({"; ".join(van_dong.VIEC[v].lower() for v in ap)}) nhưng chưa có buổi '
                                              f'nào. Thời hạn {n} ngày bắt đầu tính từ buổi vận động đầu tiên ghi ở đây.')
        else:
            dat_trang_thai(self.lb_tt, 'tin', 'Hộ chưa có quyết định phê duyệt, hoặc đã nhận đủ tiền và đã bàn giao mặt bằng: '
                                              'không cần vận động.')

    def _chon_dong(self):
        """Chọn một buổi trong bảng: đưa lên biểu mẫu để sửa."""
        r = self.bang.currentRow()
        if not 0 <= r < len(getattr(self, 'ds_buoi', [])):
            return
        b = self.ds_buoi[r]
        self.cb_viec.setCurrentIndex(max(0, self.cb_viec.findData(b['viec'])))
        self.o_ngay.setText(b['ngay'])
        self.cb_hinh_thuc.setCurrentText(b['hinh_thuc'])
        self.o_thanh_phan.setText(b['thanh_phan'])
        self.o_noi_dung.setPlainText(b['noi_dung'])
        self.cb_ket_qua.setCurrentIndex(max(0, self.cb_ket_qua.findData(b['ket_qua'])))
        self.o_bien_ban.setText(b['bien_ban'])

    def _doc_form(self) -> dict:
        return dict(viec=self.cb_viec.currentData(), ngay=self.o_ngay.text(), hinh_thuc=self.cb_hinh_thuc.currentText(),
                    thanh_phan=self.o_thanh_phan.text(), noi_dung=self.o_noi_dung.toPlainText(),
                    ket_qua=self.cb_ket_qua.currentData(), bien_ban=self.o_bien_ban.text().strip())

    def them(self, gia_tri: dict | None = None):
        """Ghi một buổi vận động mới cho hộ đang chọn. Trả id buổi, None nếu lỗi (đã báo)."""
        if self.chi_doc or self.ma_ho() is None:
            return None
        try:
            i = van_dong.ghi_buoi(self.con, self.ma_ho(), **(gia_tri or self._doc_form()))
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.thay_doi = True
        self.o_noi_dung.clear()
        self.nap(i)
        return i

    def sua(self, gia_tri: dict | None = None, buoi_id: int | None = None):
        """Cập nhật buổi đang chọn trong bảng (hoặc buoi_id) theo biểu mẫu."""
        if buoi_id is None:
            r = self.bang.currentRow()
            if not 0 <= r < len(self.ds_buoi):
                self.bao('Chọn một buổi vận động trong bảng để cập nhật.', loi=False)
                return None
            buoi_id = self.ds_buoi[r]['id']
        try:
            i = van_dong.ghi_buoi(self.con, self.ma_ho(), **(gia_tri or self._doc_form()), buoi_id=buoi_id)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.thay_doi = True
        self.nap(i)
        return i

    def xoa(self, xac_nhan: bool | None = None, buoi_id: int | None = None):
        if buoi_id is None:
            r = self.bang.currentRow()
            if not 0 <= r < len(self.ds_buoi):
                self.bao('Chọn một buổi vận động trong bảng để xóa.', loi=False)
                return 0
            buoi_id = self.ds_buoi[r]['id']
        if not (self.hoi('Xóa buổi vận động đã chọn khỏi sổ nhật ký?') if xac_nhan is None else xac_nhan):
            return 0
        n = van_dong.xoa_buoi(self.con, buoi_id)
        self.thay_doi = self.thay_doi or bool(n)
        self.nap()
        return n


class HopHoTheoDoi(_Hop):
    """Quyết định phê duyệt, chi trả, bàn giao mặt bằng, ghi chú theo dõi của MỘT hộ (Trạng thái hộ)."""
    COT = ['Quyết định số', 'Ngày', 'Số tiền phê duyệt (đ)', 'PA chi tiết số', 'QĐ chi tiết số', 'Chi trả', 'Biên lai']

    def __init__(self, con, ma_ho: int, parent=None, tong_pa=None):
        super().__init__(parent)
        self.con, self.ma_ho, self.tong_pa = con, ma_ho, tong_pa
        self.da_doi = False
        ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()[0]
        self.setWindowTitle(f'Trạng thái hộ - {ten}')
        self.resize(980, 640)
        self.bang = _bang(self.COT)
        for c, w in enumerate((170, 90, 140, 110, 110, 220, 120)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(lambda r, c: self.sua(r))
        self.lb_tong = QLabel('')
        self.lb_tong.setWordWrap(True)
        self.nut = {}
        h = QHBoxLayout()
        for t, ham in (('Thêm quyết định…', lambda: self.them()), ('Thêm từ file quyết định…', lambda: self.them(tu_file=True)),
                       ('Sửa…', lambda: self.sua()), ('Bỏ khỏi quyết định', lambda: self.bo())):
            b = QPushButton(t)
            b.clicked.connect(ham)
            h.addWidget(b)
            self.nut[t] = b
        h.addStretch(1)
        from .man_hinh_ho_so_scan import NutHoSoScan
        self.nut_scan = NutHoSoScan()                   # 0.9.96: hồ sơ scan của hộ - đính kèm / mở nhanh
        self.nut_scan.dat(con, ma_ho)
        h.addWidget(self.nut_scan)
        g1 = QGroupBox('Quyết định phê duyệt và chi trả (một hộ có thể có nhiều quyết định - phê duyệt bổ sung)')
        l1 = QVBoxLayout(g1)
        l1.addWidget(self.bang, 1)
        l1.addLayout(h)
        l1.addWidget(self.lb_tong)
        h_ho = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
        self.o_bg = QCheckBox('Đã bàn giao mặt bằng')
        self.o_bg.setChecked(bool(h_ho['da_ban_giao']))
        self.o_bg_ngay = QLineEdit(h_ho['ban_giao_ngay'])
        self.o_bg_ngay.setPlaceholderText('ngày/tháng/năm')
        self.o_bg_ly_do = QLineEdit(h_ho['ly_do_ban_giao'])
        self.o_bg_ly_do.setPlaceholderText('lý do chưa bàn giao (nếu chưa)')
        self.o_bg_file = QLineEdit(h_ho['bien_ban_ban_giao'])
        g2 = QGroupBox('Bàn giao mặt bằng')
        f2 = QFormLayout(g2)
        f2.addRow(self.o_bg)
        f2.addRow('Ngày bàn giao:', self.o_bg_ngay)
        f2.addRow('Lý do chưa bàn giao:', self.o_bg_ly_do)
        f2.addRow('Biên bản bàn giao:', _o_chon_file(self.o_bg_file, self, 'Chọn biên bản bàn giao'))
        self.o_theo_doi = QPlainTextEdit(h_ho['theo_doi'])
        self.o_theo_doi.setPlaceholderText('Ghi chú theo dõi tiến độ (vướng mắc, hẹn làm việc…)')
        self.o_theo_doi.setMaximumHeight(70)
        self._goc = self._doc_ho()
        lo = QVBoxLayout(self)
        lo.addWidget(g1, 1)
        lo.addWidget(g2)
        lo.addWidget(QLabel('Ghi chú theo dõi:'))
        lo.addWidget(self.o_theo_doi)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu bàn giao, ghi chú')
        nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.nap()

    def nap(self):
        self.ds = theo_doi.doc_qd_ho(self.con, self.ma_ho)
        b = self.bang
        b.setRowCount(len(self.ds))
        for r, q in enumerate(self.ds):
            if q['da_chi_tra']:
                ct = 'Đã nhận' + (f' {q["chi_tra_ngay"]}' if q['chi_tra_ngay'] else '') + \
                     (f' · {_tien(q["chi_tra_so_tien"])} đ' if q['chi_tra_so_tien'] else '')
            else:
                ct = 'Chưa nhận' + (f': {q["ly_do_chua_nhan"]}' if q['ly_do_chua_nhan'] else '')
            for c, v in enumerate((q['so_qd'], q['ngay_qd'], _tien(q['so_tien']), q['so_pa'], q['qd_ct_so'], ct,
                                   Path(q['chung_tu']).name if q['chung_tu'] else '')):
                _o(b, r, c, v, so=c == 2, nen=(XANH if q['da_chi_tra'] else DO) if c == 5 else None)
        vua_dong(b, cao_chuan=None, cao_toi_da=None)    # chỉ đo dòng có chữ dài / nhiều dòng
        tong = sum((_so(q['so_tien']) for q in self.ds), KHONG)
        nhan = sum((_so(q['chi_tra_so_tien']) or _so(q['so_tien']) for q in self.ds if q['da_chi_tra']), KHONG)
        t = f'{len(self.ds)} quyết định · tổng phê duyệt <b>{vn(tong)} đ</b> · đã nhận {vn(nhan)} đ'
        if self.tong_pa is not None and self.ds and tong != D(self.tong_pa):
            t += f' · <span style="color:#A12A1F">khác tổng phương án hiện tại {vn(self.tong_pa)} đ</span>'
        self.lb_tong.setText(t if self.ds else 'Hộ chưa có quyết định phê duyệt nào.')
        for k in ('Sửa…', 'Bỏ khỏi quyết định'):
            self.nut[k].setEnabled(bool(self.ds))

    def _dong(self, r=None):
        r = self.bang.currentRow() if r is None else r
        return self.ds[r] if 0 <= r < len(self.ds) else None

    def hoan_tac_phim(self, lam_lai: bool) -> bool:
        """Ctrl+Z / Ctrl+Y: hoàn tác thao tác đã ghi (thêm / sửa / bỏ quyết định của hộ) rồi đọc lại."""
        from .hoan_tac import cua
        ht = cua(self.con)
        if ht is None:
            return False
        viec = ht.lam_lai() if lam_lai else ht.hoan_tac()
        if viec:
            self.da_doi = True
            self.nap()
            self.lb_tong.setText(f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"}: {viec}<br>' + self.lb_tong.text())
        return True

    def them(self, tu_file: bool = False, gia_tri: dict | None = None, qd_id=None, file=None):
        dlg = HopQDHo(self.con, self.ma_ho, qd_id, None, self, chon_qd=True)
        dlg.im_lang = self.im_lang
        if gia_tri is None:
            dlg.lay_theo_pa()
            if tu_file:
                dlg.doc_file(file)
            if not dlg.exec():
                return None
            gia_tri = dlg.gia_tri()
        try:
            q = dlg.qd_id()
            theo_doi.ghi_qd_ho(self.con, q, self.ma_ho, gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.da_doi = True
        self.nap()
        return q

    def sua(self, r=None, gia_tri: dict | None = None):
        q = self._dong(r)
        if q is None:
            return None
        dlg = HopQDHo(self.con, self.ma_ho, q['qd_id'], q, self)
        if gia_tri is None:
            if not dlg.exec():
                return None
            gia_tri = dlg.gia_tri()
        try:
            theo_doi.ghi_qd_ho(self.con, q['qd_id'], self.ma_ho, gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.da_doi = True
        self.nap()
        return q['qd_id']

    def bo(self, r=None, xac_nhan: bool | None = None):
        q = self._dong(r)
        if q is None:
            return False
        if xac_nhan is None:
            xac_nhan = self.hoi(f'Bỏ hộ khỏi quyết định số {q["so_qd"]} (xóa số tiền, chi trả của hộ theo quyết định này)?')
        if not xac_nhan:
            return False
        theo_doi.bo_ho_khoi_qd(self.con, q['qd_id'], self.ma_ho)
        self.da_doi = True
        self.nap()
        return True

    def _doc_ho(self) -> dict:
        return dict(da_ban_giao=self.o_bg.isChecked(), ban_giao_ngay=self.o_bg_ngay.text().strip(),
                    ly_do_ban_giao=self.o_bg_ly_do.text().strip(), bien_ban_ban_giao=self.o_bg_file.text().strip(),
                    theo_doi=self.o_theo_doi.toPlainText().strip())

    def luu(self) -> bool:
        moi = self._doc_ho()
        doi = {k: v for k, v in moi.items() if v != self._goc[k]}
        if not doi:
            return True
        from .quan_ly import cap_nhat_trang_thai
        try:
            bg = {k: v for k, v in doi.items() if k in theo_doi.TRUONG_BAN_GIAO}
            if bg:
                theo_doi.ghi_ban_giao(self.con, [self.ma_ho], bg)
            if 'theo_doi' in doi:
                cap_nhat_trang_thai(self.con, [self.ma_ho], dict(theo_doi=doi['theo_doi']))
        except LoiNhap as e:
            self.bao(str(e))
            return False
        self._goc = moi
        self.da_doi = True
        return True

    def accept(self):
        if self.luu():
            super().accept()

    def reject(self):
        if self._doc_ho() != self._goc and self.hoi('Bàn giao / ghi chú có thay đổi chưa lưu. Lưu trước khi đóng?'):
            if not self.luu():
                return
        if self.da_doi:
            super().accept()                 # đã ghi quyết định: cửa sổ chính tải lại
        else:
            super().reject()
