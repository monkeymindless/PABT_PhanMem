"""Màn hình theo dõi (0.9.12): Bảng tổng hợp (thông tin tổng quát hộ - mỗi thửa một dòng; quyết định phê duyệt - danh sách quyết
định, bấm vào xem các hộ của quyết định), Theo dõi tiến độ (chi trả theo từng quyết định, bàn giao mặt bằng, lý do chưa nhận /
chưa bàn giao, biên lai), hộp thoại quyết định của một hộ. Logic ở theo_doi.py; các hàm thao tác nhận tham số để kiểm thử
(im_lang = True: không hiện hộp thông báo / hộp hỏi).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout,
                               QWidget)

from . import theo_doi
from .lap_pa import LoiNhap, bo_dau
from .tien import D, KHONG, so_vn, vn

TIEU_DE = 'Theo dõi phê duyệt, chi trả, bàn giao'
XANH, VANG, DO, XAM = QColor('#E2EFDA'), QColor('#FFF2CC'), QColor('#F8CBAD'), QColor('#F2F4F7')


def _tien(v) -> str:
    s = str(v if v is not None else '').strip()
    return vn(s) if s else ''


def _so(v):
    s = str(v or '').strip()
    return D(s) if s else KHONG


def mo_file(p) -> None:
    from .in_an import mo_file as _mo
    if p and Path(p).exists():
        _mo(p)


class _Hop(QDialog):
    im_lang = False

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def hoi(self, chu: str) -> bool:
        return self.im_lang or QMessageBox.question(self, TIEU_DE, chu) == QMessageBox.StandardButton.Yes


class _Khung(QWidget):
    """Khung nhúng trong cửa sổ chính; da_doi phát ra khi đã ghi CSDL (cửa sổ chính tải lại danh sách hộ)."""
    da_doi = Signal()
    im_lang = False

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc = con, chi_doc

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def hoi(self, chu: str) -> bool:
        return self.im_lang or QMessageBox.question(self, TIEU_DE, chu) == QMessageBox.StandardButton.Yes

    def dat_du_an(self, con, chi_doc: bool = False):
        self.con, self.chi_doc = con, chi_doc
        self.nap()

    def nap(self):
        pass

    def _tim_khi_go(self):
        """Ô tìm: chờ ngừng gõ ~0,3 giây mới lọc / vẽ lại (3.000 hộ: mỗi lần vẽ hàng chục nghìn ô - gõ từng phím thì giật)."""
        if self.im_lang:
            self.ve()
            return
        t = getattr(self, '_hen_tim', None)
        if t is None:
            from PySide6.QtCore import QTimer
            t = self._hen_tim = QTimer(self)
            t.setSingleShot(True)
            t.setInterval(CHO_GO_MS)
            t.timeout.connect(self.ve)
        t.start()

    def _loc_nho(self, khoa, ham) -> list:
        """Kết quả lọc nhớ theo (danh sách đang có, điều kiện lọc): ve() / dong() / đếm gọi nhiều lần chỉ lọc một lần."""
        k = (id(self.ds), len(self.ds), khoa)
        cu = getattr(self, '_kq_loc', None)
        if cu is not None and cu[0] == k:
            return cu[1]
        kq = ham()
        self._kq_loc = (k, kq)
        return kq


CHO_GO_MS = 300                                              # ô tìm: chờ ngừng gõ bấy nhiêu ms mới lọc


def _chuoi_tim(x, loai: str, cac_phan) -> str:
    """Chuỗi không dấu để tìm của một hộ (TongHopHo), tính một lần rồi nhớ trên đối tượng (danh sách nạp lại = đối tượng mới)."""
    k = '_tim_' + loai
    v = x.__dict__.get(k)
    if v is None:
        v = bo_dau(' '.join(str(p or '') for p in cac_phan()))
        x.__dict__[k] = v
    return v


def _bang(cot: list) -> QTableWidget:
    b = QTableWidget(0, len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    b.setAlternatingRowColors(False)
    b.setWordWrap(True)
    b.verticalHeader().setVisible(False)
    b.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    b.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    b.horizontalHeader().setStretchLastSection(True)
    b.horizontalHeader().setMinimumHeight(46)                # tiêu đề 2 dòng
    b.horizontalHeader().setResizeContentsPrecision(DO_MAU)  # tự canh cột: đo mẫu, không đo hết hàng nghìn dòng
    return b


DO_MAU = 300                                                 # số dòng Qt đo khi tự canh bề rộng cột (bảng lớn)
_CANH_PHAI = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter     # tính sẵn: _o gọi cho hàng chục nghìn ô
_CANH_TRAI = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
_CHU_DAM = []


def _o(b: QTableWidget, r: int, c: int, v, so: bool = False, nen=None, dam: bool = False, du_lieu=None, goi_y: str = ''):
    it = QTableWidgetItem('' if v is None else str(v))
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
    it.setToolTip(goi_y or ('' if v is None else str(v)))
    b.setItem(r, c, it)
    return it


def _gop(b: QTableWidget, r: int, n: int, cot: list) -> None:
    """Gộp các ô thông tin hộ trên n dòng thửa của một hộ."""
    if n > 1:
        for c in cot:
            b.setSpan(r, c, n, 1)


def mo_ta_chi_tra(qd: list) -> tuple:
    """(chữ, màu nền) tình trạng nhận tiền của hộ theo các quyết định."""
    if not qd:
        return '', None
    nhan = [x for x in qd if x['da_chi_tra']]
    chua = [x for x in qd if not x['da_chi_tra']]
    if not chua:
        ngay = sorted({x['chi_tra_ngay'] for x in nhan if x['chi_tra_ngay']}, key=theo_doi._khoa_ngay)
        return ('Đã nhận' + (f' {len(nhan)}/{len(qd)} QĐ' if len(qd) > 1 else '') + (f' ({", ".join(ngay)})' if ngay else '')), XANH
    chu = '; '.join(f'Chưa nhận QĐ {x["so_qd"]}' + (f' - {x["ly_do_chua_nhan"]}' if x['ly_do_chua_nhan'] else '') for x in chua)
    if nhan:
        chu = f'Đã nhận {len(nhan)}/{len(qd)} QĐ. ' + chu
    return chu, VANG if nhan else DO


def mo_ta_ban_giao(x) -> tuple:
    if x.da_ban_giao:
        return 'Đã bàn giao' + (f' {x.ban_giao_ngay}' if x.ban_giao_ngay else ''), XANH
    if x.ly_do_ban_giao:
        return f'Chưa: {x.ly_do_ban_giao}', VANG
    return '', None


# ---------------------------------------------------------------- Bảng tổng hợp: thông tin tổng quát hộ
class KhungTongQuat(_Khung):
    """STT | Mã hộ | Họ tên | Tờ | Thửa | DT thu hồi | Loại đất | Tổng tiền phê duyệt | Chi trả | Bàn giao MB | Ghi chú.
    Mỗi thửa một dòng; ô thông tin hộ gộp theo số thửa. Nhấp đúp: quyết định, chi trả, bàn giao của hộ."""
    COT = ['STT', 'Mã hộ', 'Họ và tên', 'Tờ bản đồ', 'Thửa đất', 'DT thu hồi (m²)', 'Loại đất', 'Tổng tiền\nphê duyệt (đ)',
           'Chi trả', 'Bàn giao mặt bằng', 'Ghi chú']
    COT_HO = (0, 1, 2, 7, 8, 9, 10)
    mo_ho = Signal(int)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.ds = []
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm họ tên, mã hộ, tờ, thửa, số quyết định, ghi chú (không cần dấu)…')
        self.o_tim.setClearButtonEnabled(True)
        self.o_tim.textChanged.connect(lambda *_: self._tim_khi_go())
        self.lb = QLabel('')
        b_xuat = QPushButton('Xuất Excel…')
        b_xuat.clicked.connect(lambda: self.xuat())
        self.bang = _bang(self.COT)
        for c, w in enumerate((50, 60, 210, 80, 80, 110, 90, 150, 260, 170, 220)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(self._nhap_dup)
        h = QHBoxLayout()
        h.addWidget(QLabel('Tìm:'))
        h.addWidget(self.o_tim, 1)
        h.addWidget(self.lb)
        h.addWidget(b_xuat)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h)
        lo.addWidget(self.bang, 1)

    def nap(self):
        self.ds = theo_doi.tong_hop(self.con, tinh_pa=False) if self.con is not None else []
        self.ve()

    def loc(self) -> list:
        tk = bo_dau(self.o_tim.text()).split()
        if not tk:
            return self.ds
        return self._loc_nho(tuple(tk), lambda: [x for x in self.ds if all(t in _chuoi_tim(x, 'tq', lambda: (
            str(x.ma_ho), x.ho_ten, x.dia_chi, x.theo_doi, *(f'{t["so_to"]} {t["so_thua"]}' for t in x.thua),
            *(q['so_qd'] for q in x.qd))) for t in tk)])

    def dong(self) -> list:
        """Các dòng hiển thị / xuất: [(hộ, [giá trị 11 cột], số dòng thửa)]."""
        kq = []
        for stt, x in enumerate(self.loc(), start=1):
            ct, _ = mo_ta_chi_tra(x.qd)
            bg, _ = mo_ta_ban_giao(x)
            tong = x.tong_phe_duyet if x.qd else None
            thua = x.thua or [dict(so_to='', so_thua='', dt_thu_hoi='', loai_dat='')]
            for i, t in enumerate(thua):
                kq.append((x, [stt if i == 0 else None, x.ma_ho if i == 0 else None, x.ho_ten if i == 0 else None, t['so_to'],
                               t['so_thua'], _so(t['dt_thu_hoi']) if str(t['dt_thu_hoi']).strip() else None, t['loai_dat'],
                               tong if i == 0 else None, ct if i == 0 else None, bg if i == 0 else None,
                               x.theo_doi if i == 0 else None], len(thua) if i == 0 else 0))
        return kq

    def ve(self):
        dong = self.dong()
        b = self.bang
        b.setUpdatesEnabled(False)
        b.clearSpans()
        b.setRowCount(len(dong))
        for r, (x, gt, n) in enumerate(dong):
            ct, mau_ct = mo_ta_chi_tra(x.qd)
            bg, mau_bg = mo_ta_ban_giao(x)
            for c, v in enumerate(gt):
                if c == 5:
                    _o(b, r, c, so_vn(v) if v is not None else '', so=True)
                elif c == 7:
                    _o(b, r, c, vn(v) if v is not None else '', so=True, dam=True,
                       goi_y='\n'.join(f'QĐ {q["so_qd"]} ({q["ngay_qd"]}): {_tien(q["so_tien"])} đ' for q in x.qd))
                elif c in (0, 1):
                    _o(b, r, c, v, so=True, du_lieu=x.ma_ho)
                else:
                    _o(b, r, c, v, nen=mau_ct if c == 8 and n else mau_bg if c == 9 and n else None, du_lieu=x.ma_ho)
            if n:
                _gop(b, r, n, self.COT_HO)
        b.setUpdatesEnabled(True)
        b.resizeRowsToContents()
        tong = sum((x.tong_phe_duyet for x in self.loc()), KHONG)
        self.lb.setText(f'{len(self.loc())}/{len(self.ds)} hộ · tổng phê duyệt {vn(tong)} đ')

    def _nhap_dup(self, r, c):
        it = self.bang.item(r, 2) or self.bang.item(r, 0)
        ma = it.data(Qt.ItemDataRole.UserRole) if it else None
        if ma is not None:
            self.mo_ho.emit(int(ma))

    def xuat(self, file=None):
        if self.con is None:
            return None
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu bảng thông tin tổng quát hộ', 'TongQuatHo.xlsx', 'File Excel (*.xlsx)')
            if not file:
                return None
        dong = self.dong()
        gop = [(i, c, i + n - 1, c) for i, (_, _, n) in enumerate(dong) if n > 1 for c in self.COT_HO]
        ten = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        try:
            p = theo_doi.xuat_excel(file, 'THÔNG TIN TỔNG QUÁT HỘ', self.COT, [d for _, d, _ in dong],
                                    [6, 8, 26, 9, 9, 12, 10, 16, 34, 20, 28], gop, ten[0] if ten else '')
        except OSError as e:
            self.bao(f'Không ghi được file (đang mở trong Excel?):\n{e}')
            return None
        if not self.im_lang:
            mo_file(p)
        return p


# ---------------------------------------------------------------- Bảng tổng hợp: quyết định phê duyệt
class KhungQuyetDinh(_Khung):
    """Trái: danh sách quyết định (bấm vào một quyết định); phải: các hộ của quyết định, mỗi thửa một dòng."""
    COT = ['STT', 'Họ và tên', 'Địa chỉ', 'Phương án\nchi tiết số', 'Ngày PA', 'QĐ chi tiết\nsố', 'Ngày ban\nhành', 'Tờ', 'Thửa',
           'DT thu hồi\n(m²)', 'Loại đất', 'Tiền đất', 'Tiền tài sản', 'Tiền cây\ntrồng', 'Các chính\nsách hỗ trợ', 'Tổng\nphê duyệt',
           'Chi trả', 'Bàn giao MB']
    COT_HO = (0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.ds_qd = []
        self.qd_id = None
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
        for ten, ham in (('Thêm…', lambda: self.sua_qd(None)), ('Nhập từ file…', lambda: self.nhap_file()),
                         ('Sửa…', lambda: self.sua_qd(self.qd_id)), ('Xóa', lambda: self.xoa_qd())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h_qd.addWidget(b)
            self.nut[ten] = b
        cot_trai.addLayout(h_qd)
        trai = QWidget()
        trai.setLayout(cot_trai)
        self.lb_qd = QLabel('Chọn một quyết định bên trái.')
        self.lb_qd.setWordWrap(True)
        self.lb_qd.setTextFormat(Qt.TextFormat.RichText)
        self.lb_qd.setOpenExternalLinks(False)
        self.lb_qd.linkActivated.connect(lambda *_: self.mo_file_qd())
        self.bang = _bang(self.COT)
        for c, w in enumerate((44, 190, 190, 110, 86, 110, 86, 56, 56, 92, 70, 110, 110, 100, 110, 120, 200, 130)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(lambda r, c: self.sua_ho(self._ma_dong(r)))
        h_ho = QHBoxLayout()
        for ten, ham in (('Thêm hộ vào quyết định…', lambda: self.them_ho()), ('Sửa hộ đang chọn…', lambda: self.sua_ho()),
                         ('Ghi nhận đã nhận tiền…', lambda: self.ghi_chi_tra()), ('Bỏ hộ khỏi quyết định', lambda: self.bo_ho()),
                         ('Xuất Excel…', lambda: self.xuat())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h_ho.addWidget(b)
            self.nut[ten] = b
        h_ho.addStretch(1)
        phai = QWidget()
        lp = QVBoxLayout(phai)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.addWidget(self.lb_qd)
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

    def nap(self, giu: bool = True):
        cu = self.qd_id if giu else None
        self.ds_qd = theo_doi.ds_quyet_dinh(self.con) if self.con is not None else []
        self.ds_qd_w.blockSignals(True)
        self.ds_qd_w.clear()
        for q in self.ds_qd:
            it = QListWidgetItem(f'Quyết định số {q.so}' + (f'\nngày {q.ngay}' if q.ngay else '') +
                                 f'  ·  {q.so_ho} hộ  ·  {vn(q.tong_ho)} đ' + (f'\nđã nhận tiền {q.so_ho_da_nhan}/{q.so_ho} hộ'
                                                                               if q.so_ho else ''))
            it.setToolTip(q.trich_yeu or q.nhan)
            self.ds_qd_w.addItem(it)
        self.ds_qd_w.blockSignals(False)
        i = next((k for k, q in enumerate(self.ds_qd) if q.id == cu), 0 if self.ds_qd else -1)
        self.ds_qd_w.setCurrentRow(i)
        self.chon(self.ds_qd[i].id if i >= 0 else None)
        for ten in ('Thêm…', 'Nhập từ file…', 'Sửa…', 'Xóa', 'Thêm hộ vào quyết định…', 'Sửa hộ đang chọn…',
                    'Ghi nhận đã nhận tiền…', 'Bỏ hộ khỏi quyết định'):
            self.nut[ten].setEnabled(self.con is not None and not self.chi_doc and (ten in ('Thêm…', 'Nhập từ file…') or i >= 0))

    def chon(self, qd_id):
        self.qd_id = qd_id
        if qd_id is None:
            self.lb_qd.setText('Chưa có quyết định nào. Bấm "Nhập từ file…" (quyết định có danh sách hộ đính kèm) hoặc "Thêm…".'
                               if self.con is not None else '')
            self.bang.setRowCount(0)
            return
        q = next(x for x in self.ds_qd if x.id == qd_id)
        lech = ''
        if str(q.tong_tien).strip() and D(q.tong_tien) != q.tong_ho:
            lech = f' <span style="color:#A12A1F">(tổng ghi trong quyết định {vn(q.tong_tien)} đ)</span>'
        tep = ' · <a href="mo">mở file quyết định</a>' if q.file else ''
        self.lb_qd.setText(f'<b>Quyết định số {q.so}</b>' + (f' ngày {q.ngay}' if q.ngay else '') +
                           (f' - {q.trich_yeu}' if q.trich_yeu else '') +
                           f'<br>{q.so_ho} hộ · tổng phê duyệt <b>{vn(q.tong_ho)} đ</b>{lech} · đã nhận tiền '
                           f'{q.so_ho_da_nhan}/{q.so_ho} hộ ({vn(q.da_chi)} đ){tep}')
        self.ve()

    def dong(self) -> list:
        if self.qd_id is None:
            return []
        ds = [x for x in theo_doi.tong_hop(self.con, theo_doi.ho_cua_qd(self.con, self.qd_id), tinh_pa=False)]
        kq = []
        for stt, x in enumerate(ds, start=1):
            q = next(y for y in x.qd if y['qd_id'] == self.qd_id)
            if q['da_chi_tra']:
                ct = 'Đã nhận' + (f' {q["chi_tra_ngay"]}' if q['chi_tra_ngay'] else '') + \
                     (f' · {_tien(q["chi_tra_so_tien"])} đ' if q['chi_tra_so_tien'] else '')
            else:
                ct = 'Chưa nhận' + (f': {q["ly_do_chua_nhan"]}' if q['ly_do_chua_nhan'] else '')
            bg, _ = mo_ta_ban_giao(x)
            thua = x.thua or [dict(so_to='', so_thua='', dt_thu_hoi='', loai_dat='')]
            for i, t in enumerate(thua):
                dau = i == 0
                kq.append((x, q, [stt if dau else None, x.ho_ten if dau else None, x.dia_chi if dau else None,
                                  q['so_pa'] if dau else None, q['ngay_pa'] if dau else None, q['qd_ct_so'] if dau else None,
                                  q['qd_ct_ngay'] if dau else None, t['so_to'], t['so_thua'],
                                  _so(t['dt_thu_hoi']) if str(t['dt_thu_hoi']).strip() else None, t['loai_dat'],
                                  *((_so(q[k]) if str(q[k]).strip() else None) if dau else None
                                    for k in ('tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'so_tien')),
                                  ct if dau else None, bg if dau else None], len(thua) if dau else 0))
        return kq

    def ve(self):
        dong = self.dong()
        b = self.bang
        b.setUpdatesEnabled(False)
        b.clearSpans()
        b.setRowCount(len(dong))
        for r, (x, q, gt, n) in enumerate(dong):
            for c, v in enumerate(gt):
                if c == 9:
                    _o(b, r, c, so_vn(v) if v is not None else '', so=True, du_lieu=x.ma_ho)
                elif 11 <= c <= 15:
                    _o(b, r, c, vn(v) if v is not None else '', so=True, dam=c == 15, du_lieu=x.ma_ho)
                elif c == 16:
                    _o(b, r, c, v, nen=(XANH if q['da_chi_tra'] else DO) if n else None, du_lieu=x.ma_ho)
                else:
                    _o(b, r, c, v, so=c == 0, du_lieu=x.ma_ho)
            if n:
                _gop(b, r, n, self.COT_HO)
        b.setUpdatesEnabled(True)
        b.resizeRowsToContents()

    def _ma_dong(self, r=None):
        r = self.bang.currentRow() if r is None else r
        it = self.bang.item(r, 1) if r is not None and r >= 0 else None
        if it is None and r is not None and r >= 0:
            it = self.bang.item(r, 7)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def ma_da_chon(self) -> list:
        ds = []
        for i in self.bang.selectionModel().selectedRows() if self.bang.selectionModel() else []:
            m = self._ma_dong(i.row())
            if m is not None and m not in ds:
                ds.append(m)
        return ds

    # ---- thao tác
    def sua_qd(self, qd_id, gia_tri: dict | None = None):
        if self.con is None or self.chi_doc:
            return None
        q = next((x for x in self.ds_qd if x.id == qd_id), None)
        dlg = HopQuyetDinh(self, q)
        if gia_tri is None:
            if not dlg.exec():
                return None
            gia_tri = dlg.gia_tri()
        try:
            moi = theo_doi.luu_qd(self.con, qd_id, **gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.qd_id = moi
        self.nap()
        self.da_doi.emit()
        return moi

    def xoa_qd(self, xac_nhan: bool | None = None):
        if self.qd_id is None:
            return None
        q = next(x for x in self.ds_qd if x.id == self.qd_id)
        if xac_nhan is None:
            xac_nhan = self.hoi(f'Xóa quyết định số {q.so} cùng {q.so_ho} dòng hộ của quyết định (chi trả theo quyết định này '
                                'cũng bị xóa)?\nHồ sơ hộ, phương án giữ nguyên.')
        if not xac_nhan:
            return None
        n = theo_doi.xoa_qd(self.con, self.qd_id)
        self.qd_id = None
        self.nap(giu=False)
        self.da_doi.emit()
        return n

    def nhap_file(self, file=None):
        """Nhập quyết định tổng / bổ sung có danh sách hộ đính kèm: dùng hộp "Nhập quyết định" (khớp hộ theo danh sách)."""
        from .man_hinh_quan_ly import HopNhapQD
        from .nghiep_vu import tinh_tat_ca
        tong = {k.ma_ho: k.tong for k in tinh_tat_ca(self.con)}
        dlg = HopNhapQD(self.con, self, tong, None, None)
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
        self.nap()
        self.da_doi.emit()

    def them_ho(self, ds_ma: list | None = None):
        if self.qd_id is None:
            return 0
        if ds_ma is None:
            dlg = HopChonHo(self.con, self, loai_tru=theo_doi.ho_cua_qd(self.con, self.qd_id))
            if not dlg.exec():
                return 0
            ds_ma = dlg.chon()
        from .nghiep_vu import BoiCanh
        bc = BoiCanh.tu(self.con)
        with self.con:
            for m in ds_ma:
                theo_doi.ghi_qd_ho(self.con, self.qd_id, m, theo_doi.chi_tiet_tu_phuong_an(self.con, m, bc), ghi_nhat_ky=False)
        self.nap()
        self.da_doi.emit()
        return len(ds_ma)

    def sua_ho(self, ma=None, gia_tri: dict | None = None):
        ma = self._ma_dong() if ma is None else ma
        if ma is None or self.qd_id is None or self.chi_doc:
            return None
        dong = next((x for x in theo_doi.doc_qd_ho(self.con, ma) if x['qd_id'] == self.qd_id), None)
        dlg = HopQDHo(self.con, ma, self.qd_id, dong, self)
        if gia_tri is None:
            if not dlg.exec():
                return None
            gia_tri = dlg.gia_tri()
        try:
            theo_doi.ghi_qd_ho(self.con, self.qd_id, ma, gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.nap()
        self.da_doi.emit()
        return ma

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
        self.nap()
        self.da_doi.emit()
        return n

    def bo_ho(self, xac_nhan: bool | None = None):
        ds = self.ma_da_chon()
        if not ds or self.qd_id is None:
            return 0
        if xac_nhan is None:
            xac_nhan = self.hoi(f'Bỏ {len(ds)} hộ khỏi quyết định này?')
        if not xac_nhan:
            return 0
        for m in ds:
            theo_doi.bo_ho_khoi_qd(self.con, self.qd_id, m)
        self.nap()
        self.da_doi.emit()
        return len(ds)

    def mo_file_qd(self):
        q = next((x for x in self.ds_qd if x.id == self.qd_id), None)
        if q and q.file:
            if Path(q.file).exists():
                mo_file(q.file)
            else:
                self.bao(f'Không thấy file:\n{q.file}')

    def xuat(self, file=None):
        if self.qd_id is None:
            return None
        q = next(x for x in self.ds_qd if x.id == self.qd_id)
        if file is None:
            ten = ''.join(ch if ch.isalnum() else '_' for ch in q.so)
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu danh sách hộ của quyết định', f'QD_{ten}.xlsx', 'File Excel (*.xlsx)')
            if not file:
                return None
        dong = self.dong()
        gop = [(i, c, i + n - 1, c) for i, (_, _, _, n) in enumerate(dong) if n > 1 for c in self.COT_HO]
        try:
            p = theo_doi.xuat_excel(file, f'DANH SÁCH HỘ THEO QUYẾT ĐỊNH SỐ {q.so}' + (f' NGÀY {q.ngay}' if q.ngay else ''),
                                    self.COT, [d for _, _, d, _ in dong],
                                    [5, 24, 24, 13, 11, 13, 11, 7, 7, 11, 9, 14, 14, 13, 14, 15, 24, 16], gop, q.trich_yeu)
        except OSError as e:
            self.bao(f'Không ghi được file (đang mở trong Excel?):\n{e}')
            return None
        if not self.im_lang:
            mo_file(p)
        return p


class KhungTongHopTien(_Khung):
    """Tổng hợp tiền theo phương án hiện tại (từng mục) - bảng "Tổng hợp sau áp giá" cũ."""
    COT = ['STT', 'Mã hộ', 'Họ và tên', 'Số thửa', 'DT thu hồi (m²)', '1. Đất', '2. Nhà, CT', '3. Cây trồng', '4. Hỗ trợ',
           '5. Thưởng', 'TỔNG PHƯƠNG ÁN', 'Tổng phê duyệt', 'Chênh lệch PA - phê duyệt', 'Đối chiếu Excel']
    mo_ho = Signal(int)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.bang = _bang(self.COT)
        self.bang.setSortingEnabled(True)
        self.bang.cellDoubleClicked.connect(lambda r, c: self.mo_ho.emit(int(self.bang.item(r, 1).data(Qt.ItemDataRole.UserRole))))
        self.lb = QLabel('')
        b = QPushButton('Xuất Excel…')
        b.clicked.connect(lambda: self.xuat())
        h = QHBoxLayout()
        h.addWidget(self.lb, 1)
        h.addWidget(b)
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
        b = self.bang
        b.setSortingEnabled(False)
        b.setUpdatesEnabled(False)
        b.setRowCount(len(ds))
        for r, d in enumerate(ds):
            for c, v in enumerate(d):
                if c in (0, 1, 3):
                    it = _o(b, r, c, v, so=True, du_lieu=d[1])
                    it.setData(Qt.ItemDataRole.DisplayRole, v)
                elif c in (2, 13):
                    _o(b, r, c, v, du_lieu=d[1], nen=(DO if v == 'LỆCH' else XANH if v else None) if c == 13 else None)
                else:
                    nen = (DO if v else XANH) if c == 12 and v is not None else None
                    _o(b, r, c, (so_vn(v) if c == 4 else vn(v)) if v is not None else '', so=True, dam=c == 10, nen=nen)
        b.setUpdatesEnabled(True)
        b.setSortingEnabled(True)
        b.resizeColumnsToContents()
        b.setColumnWidth(2, min(max(b.columnWidth(2), 200), 300))
        tong = sum((d[10] for d in ds), KHONG)
        self.lb.setText(f'{len(ds)} hộ · tổng phương án {vn(tong)} đ · tổng phê duyệt '
                        f'{vn(sum((d[11] or KHONG for d in ds), KHONG))} đ')

    def xuat(self, file=None):
        if self.con is None:
            return None
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu tổng hợp tiền theo phương án', 'TongHopTien.xlsx', 'File Excel (*.xlsx)')
            if not file:
                return None
        p = theo_doi.xuat_excel(file, 'TỔNG HỢP TIỀN BỒI THƯỜNG, HỖ TRỢ THEO PHƯƠNG ÁN', self.COT, self.dong(),
                                [6, 8, 26, 8, 12, 15, 15, 15, 15, 13, 17, 17, 17, 16])
        if not self.im_lang:
            mo_file(p)
        return p


class KhungBangTongHop(_Khung):
    """Bảng tổng hợp theo dõi toàn bộ dự án: 3 mục (thông tin tổng quát hộ, quyết định phê duyệt, tiền theo phương án)."""
    THE = ['Thông tin tổng quát hộ', 'Quyết định phê duyệt', 'Tổng hợp tiền theo phương án']
    mo_ho = Signal(int)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.tong_quat = KhungTongQuat(con, self, chi_doc)
        self.quyet_dinh = KhungQuyetDinh(con, self, chi_doc)
        self.tien = KhungTongHopTien(con, self, chi_doc)
        self.tab = QTabWidget()
        for w, t in zip((self.tong_quat, self.quyet_dinh, self.tien), self.THE):
            self.tab.addTab(w, t)
            w.da_doi.connect(self._doi)
        for w in (self.tong_quat, self.tien):
            w.mo_ho.connect(self.mo_ho.emit)
        self.tab.currentChanged.connect(lambda i: self._nap_the(i))
        self._can_nap = set(range(3))
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(self.tab)

    def _doi(self):
        self._can_nap = set(range(3)) - {self.tab.currentIndex()}
        self.da_doi.emit()

    def dat_du_an(self, con, chi_doc: bool = False):
        self.con, self.chi_doc = con, chi_doc
        for w in (self.tong_quat, self.quyet_dinh, self.tien):
            w.con, w.chi_doc = con, chi_doc
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
            (self.tong_quat, self.quyet_dinh, self.tien)[i].nap()

    def mo_the(self, i: int):
        self.tab.setCurrentIndex(i)
        self._nap_the(i)


# ---------------------------------------------------------------- Theo dõi tiến độ
class KhungTienDo(_Khung):
    """Hộ đã / chưa nhận tiền (theo từng quyết định hoặc nhiều quyết định), đã / chưa bàn giao, lý do, ngày nhận, biên lai."""
    COT = ['STT', 'Mã hộ', 'Họ và tên', 'Địa chỉ', 'Quyết định phê duyệt', 'Tổng phê\nduyệt (đ)', 'Đã nhận (đ)', 'Ngày nhận\ntiền',
           'Chưa nhận - lý do', 'Biên lai / biên\nbản chi trả', 'Bàn giao\nmặt bằng', 'Lý do chưa\nbàn giao', 'Ghi chú theo dõi']
    mo_ho = Signal(int)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.ds = []
        self.cb_loc = QComboBox()
        for k, t in theo_doi.LOC_TIEN_DO:
            self.cb_loc.addItem(t, k)
        self.cb_loc.currentIndexChanged.connect(lambda *_: self.ve())
        self.ds_qd_w = QListWidget()
        self.ds_qd_w.setMaximumHeight(72)
        self.ds_qd_w.itemChanged.connect(lambda *_: self.ve())
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm họ tên, mã hộ, lý do… (không cần dấu)')
        self.o_tim.setClearButtonEnabled(True)
        self.o_tim.textChanged.connect(lambda *_: self._tim_khi_go())
        self.the = {}
        h_the = QHBoxLayout()
        for k, t, mau in (('tong', 'Số hộ', '#2D64A6'), ('pd', 'Đã có QĐ phê duyệt', '#1F7A86'), ('nhan', 'Đã nhận đủ tiền', '#2F7A4F'),
                          ('chua', 'Còn QĐ chưa nhận', '#B8651F'), ('bg', 'Đã bàn giao MB', '#4E5D6C'),
                          ('chua_bg', 'Chưa bàn giao', '#A12A1F')):
            o = QLabel('–')
            o.setStyleSheet(f'QLabel {{ background: #FFFFFF; border: 1px solid #DCE3EA; border-left: 4px solid {mau}; '
                            f'border-radius: 7px; padding: 5px 10px; color: {mau}; font-weight: 600; }}')
            o.setToolTip(t)
            self.the[k] = (o, t)
            h_the.addWidget(o, 1)
        self.bang = _bang(self.COT)
        for c, w in enumerate((44, 56, 190, 190, 200, 120, 120, 110, 230, 150, 140, 180, 180)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(self._nhap_dup)
        self.nut = {}
        h_nut = QHBoxLayout()
        for ten, ham in (('Quyết định, chi trả, bàn giao của hộ…', lambda: self._mo_ho_chon()),
                         ('Bàn giao mặt bằng các hộ đã chọn…', lambda: self.ban_giao()), ('Xuất Excel…', lambda: self.xuat())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h_nut.addWidget(b)
            self.nut[ten] = b
        h_nut.addStretch(1)
        h_loc = QHBoxLayout()
        h_loc.addWidget(QLabel('Lọc:'))
        h_loc.addWidget(self.cb_loc)
        h_loc.addWidget(QLabel('Tìm:'))
        h_loc.addWidget(self.o_tim, 1)
        h_qd = QHBoxLayout()
        nhan = QLabel('Theo quyết định\n(đánh dấu một\nhoặc nhiều; bỏ\ntrống = tất cả):')
        h_qd.addWidget(nhan)
        h_qd.addWidget(self.ds_qd_w, 1)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h_the)
        lo.addLayout(h_loc)
        lo.addLayout(h_qd)
        lo.addWidget(self.bang, 1)
        lo.addLayout(h_nut)

    def nap(self):
        """Nạp lại; trang đang ẩn thì chỉ đánh dấu, nạp khi hiện (showEvent) - lưu một hộ không phải dựng lại bảng
        hàng chục nghìn ô của trang không ai đang xem (3.000 hộ: ~1 giây mỗi lần lưu)."""
        if not self.isVisible() and not getattr(self, 'im_lang', False):
            self._can_nap = True
            return
        self._can_nap = False
        if self.con is None:
            self.ds = []
            self.ds_qd_w.clear()
            self.ve()
            return
        self.ds = theo_doi.tong_hop(self.con, tinh_pa=False)
        chon = self.qd_chon()
        self.ds_qd_w.blockSignals(True)
        self.ds_qd_w.clear()
        for q in theo_doi.ds_quyet_dinh(self.con):
            it = QListWidgetItem(f'QĐ {q.so}' + (f' ngày {q.ngay}' if q.ngay else '') + f' - {q.so_ho} hộ, đã nhận '
                                 f'{q.so_ho_da_nhan}/{q.so_ho}')
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if q.id in chon else Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, q.id)
            self.ds_qd_w.addItem(it)
        self.ds_qd_w.blockSignals(False)
        self.ve()

    def showEvent(self, e):
        super().showEvent(e)
        if getattr(self, '_can_nap', False):
            self.nap()

    def qd_chon(self) -> set:
        return {self.ds_qd_w.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.ds_qd_w.count())
                if self.ds_qd_w.item(i).checkState() == Qt.CheckState.Checked}

    def dat_loc(self, khoa: str = '', ds_qd: set | None = None, tu_khoa: str | None = None):
        self.cb_loc.setCurrentIndex(max(0, self.cb_loc.findData(khoa)))
        if ds_qd is not None:
            self.ds_qd_w.blockSignals(True)
            for i in range(self.ds_qd_w.count()):
                it = self.ds_qd_w.item(i)
                it.setCheckState(Qt.CheckState.Checked if it.data(Qt.ItemDataRole.UserRole) in ds_qd else Qt.CheckState.Unchecked)
            self.ds_qd_w.blockSignals(False)
        if tu_khoa is not None:
            self.o_tim.setText(tu_khoa)
        self.ve()

    def loc(self) -> list:
        k, qd = self.cb_loc.currentData() or '', self.qd_chon()
        tk = bo_dau(self.o_tim.text()).split()

        def tim():
            kq = []
            for x in self.ds:
                if not theo_doi.hop_loc(x, k, qd):
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
                stt, x.ma_ho, x.ho_ten, x.dia_chi,
                '\n'.join(f'{q["so_qd"]}' + (f' ({q["ngay_qd"]})' if q['ngay_qd'] else '') for q in qd),
                sum((_so(q['so_tien']) for q in qd), KHONG) if qd else None,
                sum((_so(q['chi_tra_so_tien']) or _so(q['so_tien']) for q in nhan), KHONG) if nhan else None,
                '\n'.join(f'{q["chi_tra_ngay"]} (QĐ {q["so_qd"]})' if len(qd) > 1 else q['chi_tra_ngay'] for q in nhan
                          if q['chi_tra_ngay']),
                '\n'.join(f'QĐ {q["so_qd"]}' + (f': {q["ly_do_chua_nhan"]}' if q['ly_do_chua_nhan'] else '') for q in chua),
                '\n'.join(Path(q['chung_tu']).name for q in nhan if q['chung_tu']),
                ('Đã bàn giao' + (f' {x.ban_giao_ngay}' if x.ban_giao_ngay else '')) if x.da_ban_giao else 'Chưa',
                x.ly_do_ban_giao if not x.da_ban_giao else '', x.theo_doi]))
        return kq

    def ve(self):
        dong = self.dong()
        b = self.bang
        b.setUpdatesEnabled(False)
        b.setRowCount(len(dong))
        for r, (x, qd, gt) in enumerate(dong):
            for c, v in enumerate(gt):
                nen = None
                if c == 8 and v:
                    nen = DO
                elif c == 7 and v:
                    nen = XANH
                elif c == 10:
                    nen = XANH if x.da_ban_giao else VANG if qd else None
                it = _o(b, r, c, vn(v) if c in (5, 6) and v is not None else ('' if v is None else v), so=c in (0, 1, 5, 6),
                        nen=nen, du_lieu=x.ma_ho)
                if c == 9 and v:
                    it.setForeground(QBrush(QColor('#0B5CAD')))
                    it.setToolTip('Nhấp đúp để mở biên lai / biên bản chi trả:\n' +
                                  '\n'.join(q['chung_tu'] for q in qd if q['chung_tu']))
        b.setUpdatesEnabled(True)
        b.resizeRowsToContents()
        ds = self.loc()
        n_pd = sum(1 for x in self.ds if x.qd)
        dem = dict(tong=len(self.ds), pd=n_pd, nhan=sum(1 for x in self.ds if x.qd and not x.qd_chua_nhan),
                   chua=sum(1 for x in self.ds if x.qd_chua_nhan), bg=sum(1 for x in self.ds if x.da_ban_giao),
                   chua_bg=sum(1 for x in self.ds if not x.da_ban_giao))
        for k, (o, t) in self.the.items():
            o.setText(f'{t}: {dem[k]}' + (f' / {len(self.ds)}' if k != 'tong' else '') if self.ds else f'{t}: –')
        self.dang_hien = [x.ma_ho for x in ds]

    def _ma(self, r) -> int | None:
        it = self.bang.item(r, 1)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def ma_da_chon(self) -> list:
        return sorted({self._ma(i.row()) for i in self.bang.selectionModel().selectedRows()} - {None}) \
            if self.bang.selectionModel() else []

    def _nhap_dup(self, r, c):
        ma = self._ma(r)
        if ma is None:
            return
        if c == 9:
            x = next((y for y in self.ds if y.ma_ho == ma), None)
            for q in x.qd if x else []:
                if q['chung_tu']:
                    mo_file(q['chung_tu'])
            return
        self.mo_ho.emit(int(ma))

    def _mo_ho_chon(self):
        ds = self.ma_da_chon()
        if ds:
            self.mo_ho.emit(ds[0])

    def ban_giao(self, ds_ma: list | None = None, gia_tri: dict | None = None):
        ds_ma = self.ma_da_chon() if ds_ma is None else ds_ma
        if not ds_ma or self.chi_doc:
            self.bao('Chọn các hộ trong bảng (giữ Ctrl / Shift để chọn nhiều).', loi=False)
            return 0
        if gia_tri is None:
            dlg = HopBanGiao(self, len(ds_ma))
            if not dlg.exec():
                return 0
            gia_tri = dlg.gia_tri()
        try:
            n = theo_doi.ghi_ban_giao(self.con, ds_ma, gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return 0
        self.nap()
        self.da_doi.emit()
        return n

    def xuat(self, file=None):
        if self.con is None:
            return None
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu danh sách theo dõi tiến độ', 'TheoDoiTienDo.xlsx', 'File Excel (*.xlsx)')
            if not file:
                return None
        ten = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        tieu = 'THEO DÕI TIẾN ĐỘ CHI TRẢ, BÀN GIAO MẶT BẰNG'
        if self.cb_loc.currentData():
            tieu += f' - {self.cb_loc.currentText().upper()}'
        p = theo_doi.xuat_excel(file, tieu, self.COT, [d for _, _, d in self.dong()],
                                [5, 7, 24, 24, 22, 15, 15, 14, 28, 22, 16, 22, 22], None, ten[0] if ten else '')
        if not self.im_lang:
            mo_file(p)
        return p


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
        self.setWindowTitle(f'Quyết định phê duyệt - {ten[0] if ten else ""} (mã {ma_ho})')
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
            it = QListWidgetItem(f'{r[1]}. {r[2]} (mã {r[0]})')
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, r[0])
            self.ds.addItem(it)
        self.o_tim.textChanged.connect(self._loc)
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
    def __init__(self, parent=None, so_ho: int = 1, x=None):
        super().__init__(parent)
        self.setWindowTitle(f'Bàn giao mặt bằng - {so_ho} hộ')
        self.resize(560, 260)
        self.o_da = QCheckBox('Đã bàn giao mặt bằng')
        self.o_da.setChecked(True if x is None else x.da_ban_giao)
        from datetime import date
        self.o_ngay = QLineEdit(x.ban_giao_ngay if x is not None else date.today().strftime('%d/%m/%Y'))
        self.o_ly_do = QPlainTextEdit(x.ly_do_ban_giao if x is not None else '')
        self.o_ly_do.setMaximumHeight(60)
        self.o_file = QLineEdit(x.bien_ban_ban_giao if x is not None else '')
        self.o_da.toggled.connect(lambda d: (self.o_ngay.setEnabled(d), self.o_ly_do.setEnabled(not d)))
        f = QFormLayout(self)
        f.addRow(self.o_da)
        f.addRow('Ngày bàn giao:', self.o_ngay)
        f.addRow('Biên bản bàn giao:', _o_chon_file(self.o_file, self, 'Chọn biên bản bàn giao'))
        f.addRow('Lý do chưa bàn giao:', self.o_ly_do)
        f.addRow(_nut_luu(self))
        self.o_ngay.setEnabled(self.o_da.isChecked())
        self.o_ly_do.setEnabled(not self.o_da.isChecked())

    def gia_tri(self) -> dict:
        da = self.o_da.isChecked()
        return dict(da_ban_giao=da, ban_giao_ngay=self.o_ngay.text() if da else '', ly_do_ban_giao=self.o_ly_do.toPlainText(),
                    bien_ban_ban_giao=self.o_file.text().strip())


class HopHoTheoDoi(_Hop):
    """Quyết định phê duyệt, chi trả, bàn giao mặt bằng, ghi chú theo dõi của MỘT hộ (Trạng thái hộ)."""
    COT = ['Quyết định số', 'Ngày', 'Số tiền phê duyệt (đ)', 'PA chi tiết số', 'QĐ chi tiết số', 'Chi trả', 'Biên lai']

    def __init__(self, con, ma_ho: int, parent=None, tong_pa=None):
        super().__init__(parent)
        self.con, self.ma_ho, self.tong_pa = con, ma_ho, tong_pa
        self.da_doi = False
        ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()[0]
        self.setWindowTitle(f'Trạng thái hộ - {ten} (mã {ma_ho})')
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
        b.resizeRowsToContents()
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
