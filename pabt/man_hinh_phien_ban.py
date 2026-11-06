"""Giao diện đa phiên bản phương án (1.0.63): các nút phiên bản trong dải lần phương án và bảng đối chiếu V1 | V2.n | V3. Logic ở phien_ban_pa.py, in_phien_ban.py."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import phien_ban_pa as pb
from .giao_dien import icon_ky_hieu
from .lap_pa import LoiNhap
from .tien import vn

TIEU_DE = 'LARC - Phiên bản phương án'


class ThanhPhienBan(QWidget):
    """Các nút V0 -> V1 -> V2.n -> V3 trong dải "Lần lập PA" của cửa sổ lập phương án. Bấm là đổi phiên bản; b_khoa: mở khóa / khóa lại phiên bản đang xem. man: CuaSoLapPA."""

    def __init__(self, man):
        super().__init__()
        self.man = man
        self.setObjectName('thanh_phien_ban')
        self.h = QHBoxLayout(self)
        self.h.setContentsMargins(0, 0, 0, 0)
        self.h.setSpacing(4)
        self._dau = None
        self.cb = QComboBox()
        self.cb.setObjectName('o_phien_ban')
        self.cb.setFixedHeight(26)
        self.cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb.setMinimumContentsLength(22)
        self.cb.view().setMinimumWidth(380)
        self.cb.activated.connect(self._chon_o)
        self.h.addWidget(self.cb)
        self.b_hd = QPushButton('Chốt V1')
        self.b_hd.setFixedHeight(26)
        self.b_hd.clicked.connect(lambda: self.bam_ngu_canh())
        self.h.addWidget(self.b_hd)
        self.b_dc = QPushButton('Đối chiếu…')
        self.b_dc.setToolTip('Bảng đối chiếu V1, V2, V3 của hộ: chênh lệch, trình theo V1 hoặc V2, ghép từng nhóm, 4 mẫu in')
        self.b_dc.setFixedHeight(26)
        self.b_dc.clicked.connect(lambda: self.doi_chieu())
        self.b_khoa = QPushButton('Mở khóa')
        self.b_khoa.setFixedHeight(26)
        self.b_khoa.clicked.connect(lambda: self.doi_khoa())

    def _bao(self, chu: str) -> None:
        if not getattr(self.man, 'im_lang', False):
            QMessageBox.warning(self, TIEU_DE, chu)

    def _icon(self, ma: str, khoa: bool):
        """Huy hiệu màu của mục trong ô chọn (hình vẽ, không dùng emoji: Win 7 không có phông)."""
        mau = {pb.V0: '#16a34a', pb.V1: '#64748b', pb.V3: '#1d4ed8'}.get(ma, '#ea580c')
        if khoa:
            ic = icon_ky_hieu(0xE72E, mau, 14)        # Lock
            if ic is not None:
                return ic
        anh = QPixmap(14, 14)
        anh.fill(QColor(0, 0, 0, 0))
        ve = QPainter(anh)
        ve.setRenderHint(QPainter.RenderHint.Antialiasing)
        ve.setBrush(QColor(mau))
        ve.setPen(QColor(mau))
        ve.drawEllipse(2, 2, 10, 10)
        ve.end()
        return QIcon(anh)

    def nap(self) -> None:
        """Nạp ô chọn theo hộ, phiên bản đang mở (không đổi gì thì giữ nguyên)."""
        bo = self.man.bo
        ds = pb.ds_phien_ban(bo.con, bo.ma_ho)
        hien = getattr(bo, 'phien_ban', None) or pb.V0
        co = {x['ma'] for x in ds}
        sua_duoc = not getattr(self.man, '_chi_xem', False)
        ghi = {x['ma']: x for x in ds}
        self._dat_nut_khoa(ghi.get(hien), sua_duoc)
        self.b_hd.setEnabled(sua_duoc)
        self.b_hd.setText('Chốt V1' if pb.V1 not in co else 'Tạo nhánh V2')
        if self.b_hd.minimumWidth():                    # cửa sổ hẹp (CuaSoLapPA.resizeEvent): giữ đủ chữ khi chữ đổi
            self.b_hd.setMinimumWidth(self.b_hd.fontMetrics().horizontalAdvance(self.b_hd.text()) + 18)
        self.b_hd.setToolTip('Chốt số hiện hành thành phương án niêm yết V1. In PA dự thảo, xuất bảng niêm yết cũng tự chốt.' if pb.V1 not in co
                             else 'Tạo nhánh dự thảo mới từ V1 để điều chỉnh theo ý kiến, V1 giữ nguyên')
        dau = (bo.ma_ho, hien, tuple(sorted((x['ma'], bool(x['khoa'])) for x in ds)))
        if dau == self._dau:
            return
        self._dau = dau
        self.cb.blockSignals(True)
        self.cb.clear()
        self.cb.addItem(self._icon(pb.V0, False), 'V0: Phương án gốc [Đang lập]', pb.V0)
        for x in ds:
            ma, k = x['ma'], bool(x['khoa'])
            if ma == pb.V1:
                chu = 'V1: PA Dự thảo Niêm yết ' + ('[Đã khóa]' if k else '[Đang mở]')
            elif ma == pb.V3:
                chu = 'V3: PA Chính thức Trình thẩm định / Phê duyệt' + (' [Đã khóa]' if k else '')
            else:
                chu = f'{ma}: PA Điều chỉnh sau Ý kiến / Đối thoại' + (' [Đã khóa]' if k else '')
            self.cb.addItem(self._icon(ma, k), chu, ma)
            self.cb.setItemData(self.cb.count() - 1, f'{x["nhan"]}. {x["ghi_chu"]}', Qt.ItemDataRole.ToolTipRole)
        self.cb.setCurrentIndex(max(0, self.cb.findData(hien)))
        self.cb.setToolTip(self.cb.currentText())
        self.cb.blockSignals(False)

    def bam_ngu_canh(self) -> str:
        """Nút cạnh ô chọn: chưa có V1 thì chốt V1, có rồi thì tạo nhánh V2."""
        bo = self.man.bo
        if pb.lay(bo.con, bo.ma_ho, pb.V1) is None:
            self.chot_v1()
            return pb.V1
        return self.tao_v2()

    def _chon_o(self, i: int) -> None:
        if not self.chon(self.cb.itemData(i)):       # không chuyển được (còn sửa chưa lưu, chọn Hủy): ô về đúng bản đang mở
            self._dau = None
            self.nap()

    def in_mau(self, ma: str, dich=None):
        """Menu In / Xuất: một trong 4 mẫu của hộ đang mở (dùng bảng đối chiếu, không viết đường in thứ hai)."""
        man = self.man
        d = HopDoiChieu(man, man.bo.con, [man.bo.ma_ho], man.bo.ma_ho, getattr(man, '_chi_xem', False))
        d.im_lang = getattr(man, 'im_lang', False)
        try:
            return d.in_mau(ma, dich)
        finally:
            d.deleteLater()

    def _dat_nut_khoa(self, r, sua_duoc: bool) -> None:
        """Nút mở khóa / khóa lại cho phiên bản đang xem. V0 và lần đã phê duyệt dùng nút Mở khóa của lần (b_mo_khoa)."""
        man = self.man
        co = r is not None and man.b_mo_khoa.isHidden()
        self.b_khoa.setVisible(co)
        if not co:
            return
        self.b_khoa.setText('Mở khóa' if r['khoa'] else 'Khóa lại')
        self.b_khoa.setToolTip(f'Mở khóa {r["ma"]} để sửa trực tiếp, Lưu ghi vào {r["ma"]}' if r['khoa'] else f'Khóa {r["ma"]}: chỉ xem, không sửa nhầm')
        self.b_khoa.setEnabled(sua_duoc and not man._ho_khong_nhan())

    def doi_khoa(self, xac_nhan: bool | None = None) -> bool:
        """Mở khóa / khóa lại phiên bản đang xem. Mở V1: hỏi một lần cho mỗi cửa sổ (V1 là số đã niêm yết), các hộ sau chỉ một lần bấm."""
        man, bo = self.man, self.man.bo
        ma = getattr(bo, 'phien_ban', None)
        r = pb.lay(bo.con, bo.ma_ho, ma) if ma else None
        if r is None:
            return False
        mo = bool(r['khoa'])
        if mo and ma == pb.V1 and xac_nhan is None and not getattr(man, 'im_lang', False) and not getattr(man, '_da_hoi_mo_v1', False):
            if QMessageBox.question(self, TIEU_DE, 'Mở khóa V1 để sửa trực tiếp số đã niêm yết? Bản đã chốt vẫn giữ riêng, trả về được ở nút "…".') != QMessageBox.StandardButton.Yes:
                return False
            man._da_hoi_mo_v1 = True
        if xac_nhan is False or (not mo and not man.hoi_luu()):
            return False
        try:
            pb.dat_khoa(bo.con, bo.ma_ho, ma, not mo)
        except (LoiNhap, sqlite3.OperationalError) as e:
            self._bao(str(e))
            return False
        self._lam_moi(ma)
        return True

    def _lam_moi(self, ma) -> None:
        man = self.man
        man.bo.mo_phien_ban(ma)
        man.nap_ho()
        man.lam_moi_xem_truoc()

    def them_menu(self, menu) -> None:
        """Mục thêm vào menu "…": trả V1 về bản đã chốt khi V1 đã sửa."""
        bo = self.man.bo
        if pb.v1_da_sua(bo.con, bo.ma_ho):
            a = menu.addAction('Trả V1 về bản đã chốt…', lambda: self.tra_v1_goc())
            a.setToolTip('V1 về đúng số lúc chốt niêm yết và khóa lại')
            a.setEnabled(not getattr(self.man, '_chi_xem', False) and not self.man._ho_khong_nhan())
        hien = getattr(bo, 'phien_ban', None)
        duoc = not getattr(self.man, '_chi_xem', False) and not self.man._ho_khong_nhan()
        menu.addSeparator()
        a = menu.addAction('Nhân bản phương án thành nhánh mới', lambda: self.nhan_ban())
        a.setEnabled(duoc and pb.lay(bo.con, bo.ma_ho, pb.V1) is not None)
        a = menu.addAction('Khôi phục số đang lập theo bản đang xem…', lambda: self.khoi_phuc())
        a.setEnabled(duoc and bool(hien))
        a = menu.addAction('Xóa nhánh nháp đang xem…', lambda: self.xoa_nhanh())
        a.setEnabled(duoc and bool(hien) and str(hien).startswith('V2.') and not bo.khoa)

    def nhan_ban(self) -> str:
        """Nhánh V2 mới từ bản đang xem (V2.n, V1); đang ở V0 / V3 thì từ V1."""
        man, bo = self.man, self.man.bo
        if not man.hoi_luu():
            return ''
        hien = getattr(bo, 'phien_ban', None)
        try:
            ma = pb.tao_v2(bo.con, bo.ma_ho, f'Nhân bản từ {hien or pb.V1}.', hien if hien and hien != pb.V3 else pb.V1)
        except LoiNhap as e:
            self._bao(str(e))
            return ''
        self._dau = None
        self.nap()
        self.chon(ma)
        return ma

    def khoi_phuc(self, xac_nhan: bool | None = None) -> bool:
        man, bo = self.man, self.man.bo
        hien = getattr(bo, 'phien_ban', None)
        if not hien:
            return False
        if xac_nhan is None and not getattr(man, 'im_lang', False):
            xac_nhan = QMessageBox.question(self, TIEU_DE, f'Ghi nội dung {hien} vào số đang lập V0? Số V0 hiện tại bị thay, {hien} giữ nguyên.') == QMessageBox.StandardButton.Yes
        if xac_nhan is False or not man.hoi_luu():
            return False
        try:
            pb.khoi_phuc_v0(bo.con, bo.ma_ho, hien)
        except (LoiNhap, sqlite3.OperationalError) as e:
            self._bao(str(e))
            return False
        self._dau = None
        self.chon(pb.V0)
        return True

    def xoa_nhanh(self, xac_nhan: bool | None = None) -> bool:
        man, bo = self.man, self.man.bo
        hien = getattr(bo, 'phien_ban', None)
        if not hien:
            return False
        if xac_nhan is None and not getattr(man, 'im_lang', False):
            xac_nhan = QMessageBox.question(self, TIEU_DE, f'Xóa nhánh nháp {hien}? Không khôi phục được.') == QMessageBox.StandardButton.Yes
        if xac_nhan is False:
            return False
        try:
            pb.xoa_v2(bo.con, bo.ma_ho, hien)
        except (LoiNhap, sqlite3.OperationalError) as e:
            self._bao(str(e))
            return False
        bo.mo_phien_ban(pb.V0)
        self._dau = None
        man.nap_ho()
        man.lam_moi_xem_truoc()
        return True

    def tra_v1_goc(self, xac_nhan: bool | None = None) -> bool:
        man, bo = self.man, self.man.bo
        if xac_nhan is None and not getattr(man, 'im_lang', False):
            xac_nhan = QMessageBox.question(self, TIEU_DE, 'Trả V1 về đúng số lúc chốt niêm yết và khóa lại? Phần đã sửa trong V1 sẽ bỏ.') == QMessageBox.StandardButton.Yes
        if xac_nhan is False or not man.hoi_luu():
            return False
        try:
            pb.tra_v1_ve_goc(bo.con, bo.ma_ho)
        except (LoiNhap, sqlite3.OperationalError) as e:
            self._bao(str(e))
            return False
        self._lam_moi(getattr(bo, 'phien_ban', None))
        return True

    def chu_trang_thai(self) -> str:
        """Câu giải thích hiện ở dòng thông báo: đang sửa gì, Lưu ghi vào đâu."""
        hien = getattr(self.man.bo, 'phien_ban', None) or pb.V0
        if hien != pb.V0 and self.man.bo.khoa:
            if not self.man.b_mo_khoa.isHidden():
                return f'{hien} thuộc lần đã có quyết định phê duyệt - chỉ xem. Bấm Mở khóa để sửa.'
            return 'V1 đang khóa làm chứng cứ niêm yết - chỉ xem. Bấm Mở khóa để sửa, hoặc "+" để tạo nhánh V2.' if hien == pb.V1 else f'{hien} đang khóa - chỉ xem. Bấm Mở khóa để sửa.'
        if hien == pb.V1:
            return 'Đang sửa V1 (đã mở khóa): Lưu ghi vào V1. Bản đã chốt vẫn giữ riêng, trả về được ở nút "…".'
        if hien == pb.V3:
            return 'Đang sửa V3: Lưu ghi vào V3 và ghi luôn vào số hiện hành; V1, V2 giữ nguyên.'
        if hien != pb.V0:
            return f'Đang sửa {hien}: Lưu ghi vào {hien}, số hiện hành không đổi.'
        if self.lech_v3():
            return 'Số đang lập khác V3: Mẫu 04 in theo V3, bản in thường in theo số đang lập.'
        return ''

    def lech_v3(self) -> bool:
        bo = self.man.bo
        try:
            return pb.lay(bo.con, bo.ma_ho, pb.V3) is not None and pb.tong(bo.con, bo.ma_ho, pb.V3, bo.bc) != pb.tong(bo.con, bo.ma_ho, pb.V0, bo.bc)
        except (LoiNhap, KeyError, ValueError):
            return False

    def chon(self, ma) -> bool:
        man = self.man
        if ma == (getattr(man.bo, 'phien_ban', None) or pb.V0):
            return True
        if not man.hoi_luu():
            return False
        try:
            man.bo.mo_phien_ban(ma)
        except LoiNhap as e:
            self._bao(str(e))
            return False
        man.nap_ho()
        man.lam_moi_xem_truoc()
        return True

    def chot_v1(self) -> None:
        man = self.man
        if not man.hoi_luu():
            return
        try:
            pb.khoa_v1(man.bo.con, man.bo.ma_ho)
        except LoiNhap as e:
            self._bao(str(e))
        self.nap()

    def tao_v2(self, ghi_chu: str | None = None) -> str:
        man = self.man
        if not man.hoi_luu():
            return ''
        if ghi_chu is None:
            if getattr(man, 'im_lang', False):
                ghi_chu = ''
            else:
                ghi_chu, ok = QInputDialog.getText(self, TIEU_DE, 'Lý do tạo nhánh (ý kiến của hộ, kết luận đối thoại):')
                if not ok:
                    return ''
        try:
            ma = pb.tao_v2(man.bo.con, man.bo.ma_ho, ghi_chu)
        except LoiNhap as e:
            self._bao(str(e))
            return ''
        self.nap()
        self.chon(ma)
        return ma

    def doi_chieu(self, cho: bool = True):
        man = self.man
        if not man.hoi_luu():
            return None
        d = HopDoiChieu(self.window(), man.bo.con, [man.bo.ma_ho], man.bo.ma_ho, chi_doc=getattr(man, '_chi_xem', False))
        if not cho:
            return d
        d.exec()
        xoa_hop_da_dong(d)                            # bấm từ thanh phiên bản không qua _chay_lenh: không tự xóa thì mỗi lần mở để lại một hộp ẩn giữ cả dữ liệu
        if d.da_doi:
            self._dau = None
            man.bo.mo_phien_ban(getattr(man.bo, 'phien_ban', None) or pb.V0)
            man.nap_ho()
        return d


NHOM_NGAN = {pb.DAT: 'Đất', pb.NHA: 'Nhà, VKT', pb.CAY: 'Cây trồng', pb.HO_TRO: 'Hỗ trợ', 'THUONG': 'Thưởng'}
# (tiêu đề, khóa dòng doi_chieu_ho, cột chênh lệch?)
COT_HO = (('Đơn giá V1', 'dg1', 0), ('Đơn giá V2', 'dg2', 0), ('V2 - V1', 'd1', 1), ('Thành tiền V3', 'tt3', 0), ('V3 - V1', 'd2', 1))


def _dau(x) -> str:
    return ('+' if x > 0 else '') + vn(x)


def _o_so(chu: str, dam: bool = False) -> QTableWidgetItem:
    o = QTableWidgetItem(chu)
    o.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    if dam:
        f = QFont(o.font())
        f.setBold(True)
        o.setFont(f)
    return o


def xoa_hop_da_dong(d) -> None:
    """Hộp đã đóng: chuyển khỏi cây cửa sổ chính rồi hẹn xóa (findChildren của don_hop_da_dong gặp hộp đang chờ xóa làm vỏ Python sống mãi, xem giao_dien._thung_cho_xoa)."""
    from .giao_dien import _thung_cho_xoa
    d.setParent(_thung_cho_xoa())
    d.deleteLater()


class HopDoiChieu(QDialog):
    """Đối chiếu V1 | V2.n | V3: bên trái các hộ (tích để áp dụng đồng loạt), bên phải chi tiết hộ đang chọn; chốt V3 một chạm, ghép từng nhóm, 4 mẫu in."""
    im_lang = False

    def __init__(self, parent, con, ds_ma_ho, ma_ho=None, chi_doc: bool = False, dot_id=None):
        super().__init__(parent)
        self.con, self.ds, self.chi_doc, self.dot_id = con, list(ds_ma_ho), chi_doc, dot_id
        self.da_doi = False
        self.d = None
        self.setWindowTitle('Đối chiếu phương án: V1 niêm yết, V2 sau ý kiến, V3 trình duyệt')
        self.resize(1320, 680)
        self.ten = {r[0]: r[1] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
        self.y_kien = {}
        if dot_id:
            self.y_kien = {r[0]: r[1] for r in con.execute('SELECT ma_ho, loai FROM y_kien_du_thao WHERE dot_id = ?', (dot_id,))}
        lo = QVBoxLayout(self)
        than = QHBoxLayout()
        lo.addLayout(than, 1)

        # ---- trái: các hộ
        trai = QVBoxLayout()
        self.bang_ho = QTableWidget(len(self.ds), 3)
        self.bang_ho.setHorizontalHeaderLabels(['', 'Hộ', 'V3 - V1'])
        self.bang_ho.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang_ho.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang_ho.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bang_ho.verticalHeader().setVisible(False)
        hh = self.bang_ho.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang_ho.setColumnWidth(0, 30)
        self.bang_ho.setColumnWidth(2, 96)
        self.bang_ho.setFixedWidth(330)
        trai.addWidget(self.bang_ho, 1)
        self.b_tich_bac = QPushButton('Tích hộ không đồng ý')
        self.b_tich_bac.clicked.connect(lambda: self.tich_khong_dong_y())
        self.b_dong_loat = QPushButton('Trả các hộ đã tích về V1')
        self.b_dong_loat.setToolTip('Áp dụng đồng loạt một lần bấm, không phải nhập lại. V1, V2 của từng hộ giữ nguyên. Hộ nào không áp được thì báo riêng.')
        self.b_dong_loat.clicked.connect(lambda: self.ap_dong_loat())
        trai.addWidget(self.b_tich_bac)
        trai.addWidget(self.b_dong_loat)
        than.addLayout(trai)

        # ---- phải: chi tiết hộ
        phai = QVBoxLayout()
        dau = QHBoxLayout()
        self.lb_ten = QLabel('')
        self.lb_ten.setProperty('vai', 'tieu_de')
        self.lb_tong = QLabel('')
        self.cb_v2 = QComboBox()
        self.cb_v2.activated.connect(lambda *_: self.ve_ho())
        n = QLabel('So với:')
        n.setProperty('vai', 'nhan')
        dau.addWidget(self.lb_ten)
        dau.addWidget(self.lb_tong, 1)
        dau.addWidget(n)
        dau.addWidget(self.cb_v2)
        phai.addLayout(dau)
        self.bang = QTableWidget(0, 4 + len(COT_HO))
        self.bang.setHorizontalHeaderLabels(['Nhóm', 'Nội dung', 'ĐVT'] + [c[0] for c in COT_HO] + ['Trạng thái'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.verticalHeader().setVisible(False)
        phai.addWidget(self.bang, 1)
        h2 = QHBoxLayout()
        n = QLabel('Lý do, căn cứ giải trình:')
        n.setProperty('vai', 'nhan')
        self.o_ly_do = QLineEdit()
        self.o_ly_do.setPlaceholderText('In ở Mẫu 03. Ví dụ: Phòng Kinh tế không chấp thuận, giữ theo phương án niêm yết')
        h2.addWidget(n)
        h2.addWidget(self.o_ly_do, 1)
        phai.addLayout(h2)
        than.addLayout(phai, 1)

        # ---- hàng nút (cố định ở đáy)
        hn = QHBoxLayout()
        self.b_v1 = QPushButton('Trình theo V1 (khôi phục)')
        self.b_v1.setToolTip('V3 lấy nguyên từ V1, số hiện hành theo V3; V1, V2 giữ nguyên. Không phải nhập lại.')
        self.b_v1.clicked.connect(lambda: self.dat_v3(pb.V1))
        self.b_v2 = QPushButton('Trình theo nhánh V2')
        self.b_v2.clicked.connect(lambda: self.dat_v3(self.cb_v2.currentData() or ''))
        self.b_ghep = QPushButton('Ghép từng nhóm…')
        self.b_ghep.setToolTip('V3 lấy đất từ phiên bản này, nhà, cây từ phiên bản khác; hỗ trợ giữ hoặc tính lại')
        self.b_ghep.clicked.connect(lambda: self.hop_ghep())
        self.b_in = QPushButton('In mẫu')
        m = QMenu(self.b_in)
        self.nut_mau = {}
        from . import in_phien_ban as ipb       # nạp khi mở bảng đối chiếu: kéo theo in_word (47 ms), cửa sổ lập phương án không cần
        for ma, chu in ipb.MAU:
            self.nut_mau[ma] = m.addAction(chu, lambda ma=ma: self.in_mau(ma))
        self.b_in.setMenu(m)
        d = QPushButton('Đóng')
        d.clicked.connect(self.reject)
        for b in (self.b_v1, self.b_v2, self.b_ghep):
            hn.addWidget(b)
        hn.addStretch(1)
        hn.addWidget(self.b_in)
        hn.addWidget(d)
        lo.addLayout(hn)

        for b in (self.b_v1, self.b_v2, self.b_ghep, self.b_dong_loat, self.b_tich_bac):
            b.setEnabled(not chi_doc)
        self.b_tich_bac.setVisible(bool(self.y_kien))
        self.ve_ds()
        self.bang_ho.currentCellChanged.connect(lambda r, *_: self.nap_ho())
        i = self.ds.index(ma_ho) if ma_ho in self.ds else 0
        if self.ds:
            self.bang_ho.selectRow(i)
            self.bang_ho.setCurrentCell(i, 1)
        self.nap_ho()

    # ------------------------------------------------ danh sách hộ
    def ve_ds(self) -> None:
        """Điền / cập nhật cột chênh lệch các hộ (giữ dấu tích). Tô đậm hộ có chênh lệch."""
        from .du_thao import TEN_LOAI
        for r, x in enumerate(pb.doi_chieu_dot(self.con, self.ds)):
            o = self.bang_ho.item(r, 0)
            if o is None:
                o = QTableWidgetItem()
                o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                o.setCheckState(Qt.CheckState.Unchecked)
                self.bang_ho.setItem(r, 0, o)
            t = QTableWidgetItem(x['ho_ten'])
            y = TEN_LOAI.get(self.y_kien.get(x['ma_ho']), '')
            t.setToolTip(f'Mã hộ {x["ma_ho"]}. ' + (f'Ý kiến: {y}. ' if y else '') + f'V1 {vn(x["tong_v1"])} | V2 {vn(x["tong_v2"])} | V3 {vn(x["tong_v3"])} đồng')
            self.bang_ho.setItem(r, 1, t)
            self.bang_ho.setItem(r, 2, _o_so(_dau(x['d2']), x['d2'] != 0))

    def ma_ho(self):
        r = self.bang_ho.currentRow()
        return self.ds[r] if 0 <= r < len(self.ds) else None

    def chon_ho(self, ma: int) -> None:
        self.bang_ho.setCurrentCell(self.ds.index(ma), 1)

    def tich_khong_dong_y(self) -> int:
        n = 0
        for r, ma in enumerate(self.ds):
            bac = self.y_kien.get(ma) == 'khong_dong_y'
            self.bang_ho.item(r, 0).setCheckState(Qt.CheckState.Checked if bac else Qt.CheckState.Unchecked)
            n += 1 if bac else 0
        return n

    def ma_da_tich(self) -> list:
        return [ma for r, ma in enumerate(self.ds) if self.bang_ho.item(r, 0).checkState() == Qt.CheckState.Checked]

    def ap_dong_loat(self, hoi: bool = True) -> tuple:
        ds = self.ma_da_tich()
        if not ds:
            self._bao('Chưa tích hộ nào.')
            return 0, []
        if hoi and not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Trả phương án trình duyệt của {len(ds)} hộ về V1? V1, V2 của các hộ giữ nguyên.') != QMessageBox.StandardButton.Yes:
            return 0, []
        n, loi = pb.ap_dong_loat(self.con, ds, pb.V1, self.o_ly_do.text().strip() or 'Giữ theo phương án niêm yết')
        self.da_doi = self.da_doi or n > 0
        self.ve_ds()
        self.ve_ho()
        self._bao(f'Đã trả {n} hộ về V1.' + ('\nKhông áp được:\n' + '\n'.join(loi[:10]) if loi else ''), loi=bool(loi))
        return n, loi

    # ------------------------------------------------ chi tiết hộ
    def nap_ho(self) -> None:
        ma = self.ma_ho()
        if ma is None:
            return
        v2 = [x['ma'] for x in pb.ds_phien_ban(self.con, ma) if x['ma'].startswith('V2.')]
        self.cb_v2.clear()
        for x in v2:
            self.cb_v2.addItem(x, x)
        self.cb_v2.setCurrentIndex(self.cb_v2.count() - 1)
        self.ve_ho()

    def ve_ho(self) -> None:
        ma = self.ma_ho()
        if ma is None:
            return
        d = pb.doi_chieu_ho(self.con, ma, self.cb_v2.currentData() or '')
        self.d = d
        t = d['tong']
        self.lb_ten.setText(self.ten.get(ma, ''))
        v2 = self.cb_v2.currentData() or 'V2'
        self.lb_tong.setText(f'V1 {vn(t[pb.V1])}   |   {v2} {vn(t["V2"])} ({_dau(t["d1"])})   |   V3 {vn(t[pb.V3])} ({_dau(t["d2"])}) đồng')
        self.bang.setRowCount(len(d['dong']))
        for r, x in enumerate(d['dong']):
            for c, v in enumerate((NHOM_NGAN.get(x['nhom'], ''), x['ten'], x['dvt'])):
                self.bang.setItem(r, c, QTableWidgetItem(str(v)))
            for c, (_, k, la_d) in enumerate(COT_HO, 3):
                self.bang.setItem(r, c, _o_so(_dau(x[k]) if la_d else vn(x[k]), bool(la_d and x[k] != 0)))
            self.bang.item(r, 1).setToolTip(f'{x["ten"]}\nThành tiền: V1 {vn(x["tt1"])} | V2 {vn(x["tt2"])} | V3 {vn(x["tt3"])} đồng. Đơn giá V3: {vn(x["dg3"])}')
            self.bang.setItem(r, 3 + len(COT_HO), QTableWidgetItem(x['trang_thai']))
        # cột Nội dung co lại (chú thích khi rê chuột) để chênh lệch, trạng thái luôn thấy, không phải kéo ngang
        hh = self.bang.horizontalHeader()
        for c in range(self.bang.columnCount()):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch if c == 1 else QHeaderView.ResizeMode.ResizeToContents)
        self.o_ly_do.setText(d['ly_do'] if d['co_v3'] else '')
        co_v2 = bool(self.cb_v2.count())
        self.b_v2.setEnabled(co_v2 and not self.chi_doc)
        self.b_v1.setEnabled(d['co_v1'] and not self.chi_doc)
        self.b_ghep.setEnabled(d['co_v1'] and not self.chi_doc)
        self.nut_mau['02'].setEnabled(co_v2)
        self.nut_mau['04'].setEnabled(d['co_v3'])

    def _bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def _sau_khi_doi(self) -> None:
        self.da_doi = True
        self.ve_ds()
        self.ve_ho()

    def dat_v3(self, nguon: str) -> bool:
        try:
            pb.dat_v3(self.con, self.ma_ho(), nguon, self.o_ly_do.text().strip())
        except LoiNhap as e:
            self._bao(str(e))
            return False
        self._sau_khi_doi()
        return True

    def hop_ghep(self, cho: bool = True):
        """Hộp chọn nguồn từng nhóm. cho=False: trả hộp (d.cb_nhom, d.accept)."""
        ma = self.ma_ho()
        cac = [pb.V1] + [x['ma'] for x in pb.ds_phien_ban(self.con, ma) if x['ma'].startswith('V2.')]
        d = QDialog(self)
        d.setWindowTitle('Ghép từng nhóm vào V3')
        f = QFormLayout(d)
        d.cb_nhom = {}
        for k, t in pb.NHOM:
            cb = QComboBox()
            for x in cac:
                cb.addItem(x, x)
            if k == pb.HO_TRO:
                cb.addItem('Tính lại theo số đã ghép', pb.TINH_LAI)
            d.cb_nhom[k] = cb
            f.addRow(t + ':', cb)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Ghép vào V3')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(d.accept)
        nut.rejected.connect(d.reject)
        f.addRow(nut)
        if not cho:
            return d
        if d.exec() == QDialog.DialogCode.Accepted:
            self.ghep({k: cb.currentData() for k, cb in d.cb_nhom.items()})
        return d

    def ghep(self, nguon_nhom: dict) -> bool:
        try:
            pb.ghep_v3(self.con, self.ma_ho(), nguon_nhom, self.o_ly_do.text().strip())
        except LoiNhap as e:
            self._bao(str(e))
            return False
        self._sau_khi_doi()
        return True

    # ------------------------------------------------ in
    def in_mau(self, ma: str, dich=None):
        from . import in_phien_ban as ipb
        """Mẫu 01, 03 theo các hộ đã tích (không tích: Mẫu 01 hộ đang chọn, Mẫu 03 cả danh sách); 02, 04 hộ đang chọn. dich: file / thư mục cho sẵn (kiểm thử)."""
        h = self.ma_ho()
        tich = self.ma_da_tich()
        try:
            from .csdl import duong_goi_y
            if ma == '01':
                d = dich or QFileDialog.getExistingDirectory(self, 'Chọn thư mục lưu Mẫu 01', duong_goi_y(self.con))
                if not d:
                    return None
                kq = ipb.mau_01(self.con, tich or [h], d)
            elif ma == '03':
                d = dich or QFileDialog.getSaveFileName(self, 'Lưu Mẫu 03', duong_goi_y(self.con, 'Mau03_DoiChieu.xlsx'), 'Excel (*.xlsx)')[0]
                if not d:
                    return None
                kq = ipb.mau_03(self.con, tich or self.ds, d)
            else:
                v2 = self.cb_v2.currentData() or ''
                goi_y = f'Mau02_{v2}_Ho{h}.docx' if ma == '02' else f'Mau04_V3_Ho{h}.docx'
                d = dich or QFileDialog.getSaveFileName(self, f'Lưu Mẫu {ma}', duong_goi_y(self.con, goi_y), 'Word (*.docx)')[0]
                if not d:
                    return None
                kq = ipb.mau_02(self.con, h, v2, d) if ma == '02' else ipb.mau_04(self.con, h, d)
        except (LoiNhap, OSError) as e:
            self._bao(str(e))
            return None
        self.ve_ds()
        self.nap_ho()
        ten = f'{len(kq)} file' if isinstance(kq, list) else Path(kq).name
        self._bao(f'Đã xuất Mẫu {ma}: {ten}.', loi=False)
        return kq
