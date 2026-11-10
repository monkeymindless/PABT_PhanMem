"""Bảng thống kê nhanh Hộ · Thửa · Diện tích toàn dự án (người dùng 21/10/2026, Ctrl+Shift+T - menu Dữ liệu, huy hiệu "Lọc:" của
danh sách hộ): theo 7 trạng thái thực hiện và theo từng đợt trình thẩm định. Số liệu = các dòng danh sách hộ đang nạp (app.BangHo.dong
- cùng cờ phê duyệt / chi trả / bàn giao với thẻ KPI và bộ lọc), cộng bằng Decimal. Bôi đen ô bất kỳ: bộ đếm góc dưới trái hộp."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .tien import D, lam_tron, so_luong_vn, vn
from .giao_dien import dat_kieu_theo_tong, mau_theo_tong  # noqa: E402  (1.0.34: kiểu riêng đổi theo tông nền)

TIEU_DE = 'Bảng thống kê nhanh Hộ · Thửa · Diện tích toàn dự án (Ctrl+Shift+T)'
COT_TRANG_THAI = ['Hạng mục trạng thái', 'Số hộ', 'Tỷ lệ hộ', 'Số thửa', 'Tỷ lệ thửa', 'DT thu hồi (m²)', 'Quy đổi (ha)',
                  'Tổng kinh phí (đồng)']
COT_DOT = ['Đợt trình thẩm định', 'Số hộ', 'Số thửa', 'DT thu hồi (m²)', 'Quy đổi (ha)', 'Đã bàn giao MB', 'Tổng kinh phí (đồng)']
CHUA_XEP_DOT = 'Chưa xếp đợt trình'
MAU_DONG_TONG = '#F1F5F9'               # dòng 1 (toàn dự án): nền xám nhạt, chữ đậm
MAU_DONG_VUONG = '#FEF2F2'              # dòng 7 (còn vướng mặt bằng): nền đỏ nhạt
QSS_DAI_THONG_TIN = ('QLabel#dai_thong_ke { background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 4px; color: #1E3A5F; '
                     'padding: 6px 10px; font-weight: 600; }')
KICH_THUOC = (1000, 600)
DONG_DOT_TOI_DA = 8                    # bảng đợt cao tối đa bấy nhiêu dòng (nhiều đợt hơn: cuộn)


def _ma(d) -> str:
    return d.get('ma_ho')


def _thua(d) -> int:
    """Số thửa của dòng (khóa so_thua; dòng cũ: cột Số thửa o[3]) - như app.so_thua_dong."""
    v = d.get('so_thua')
    if v is None:
        o = d.get('o') or ()
        v = o[3] if len(o) > 3 else 0
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def cong_nhom(dong: list) -> dict:
    """{so_ho, so_thua, dt, tong} của một nhóm dòng danh sách hộ - Decimal."""
    return dict(so_ho=len(dong), so_thua=sum(_thua(d) for d in dong), dt=sum((D(d.get('dt') or 0) for d in dong), D(0)),
                tong=sum((D(d.get('tong') or 0) for d in dong), D(0)))


def ty_le(phan, tong) -> str:
    """Tỷ lệ một chữ số lẻ: 34 / 171 -> "19,9%"; tổng 0 -> "0,0%"."""
    tong = D(tong)
    return f'{vn(lam_tron(D(phan) * 100 / tong, 1) if tong else D(0), 1)}%'


def so_ha_bang(dt) -> str:
    return f'{vn(D(dt) / 10000, 2)} ha'


def thong_ke_trang_thai(dong: list, lap: dict | None = None) -> list:
    """7 dòng [(nhãn, nhóm cong_nhom)] theo trạng thái thực hiện. "Đã lập" = lap_pa.phan_loai_lap 'da_lap' (phương án phần mềm tự
    lập chưa soát tính là chưa lập - như thẻ KPI); không có lap: tổng > 0."""
    if lap:
        da_lap = [d for d in dong if lap.get(_ma(d)) == 'da_lap']
    else:
        da_lap = [d for d in dong if D(d.get('tong') or 0) > 0]
    co = {_ma(d) for d in da_lap}
    return [('1. Tổng quy mô toàn dự án', cong_nhom(dong)),
            ('2. Đã lập phương án bồi thường', cong_nhom(da_lap)),
            ('3. Chưa lập phương án (Tự lập/Chờ)', cong_nhom([d for d in dong if _ma(d) not in co])),
            ('4. Đã có Quyết định phê duyệt', cong_nhom([d for d in dong if d.get('da_phe_duyet')])),
            ('5. Đã chi trả tiền bồi thường', cong_nhom([d for d in dong if d.get('da_chi_tra')])),
            ('6. Đã bàn giao mặt bằng sạch', cong_nhom([d for d in dong if d.get('da_ban_giao')])),
            ('7. Chưa bàn giao mặt bằng (Còn vướng)', cong_nhom([d for d in dong if not d.get('da_ban_giao')]))]


def thong_ke_dot(dong: list, ten_dot: dict) -> list:
    """[(tên đợt, nhóm, nhóm đã bàn giao)] theo thứ tự đợt (ten_dot {id: tên}); cuối: hộ chưa xếp đợt (nếu có)."""
    kq = []
    for i, ten in ten_dot.items():
        ds = [d for d in dong if d.get('dot_id') == i]
        kq.append((ten, cong_nhom(ds), cong_nhom([d for d in ds if d.get('da_ban_giao')])))
    chua = [d for d in dong if d.get('dot_id') not in ten_dot]
    if chua or not ten_dot:
        kq.append((CHUA_XEP_DOT, cong_nhom(chua), cong_nhom([d for d in chua if d.get('da_ban_giao')])))
    return kq


def chu_quy_mo(n: dict) -> str:
    return (f'{n["so_ho"]} hộ · {n["so_thua"]} thửa · {so_luong_vn(n["dt"])} m² ({so_ha_bang(n["dt"])}) · {vn(n["tong"])} đ')


class HopThongKeDiaChinh(QDialog):
    """dong: BangHo.dong của cửa sổ chính; ten_dot {id: tên}; lap: lap_pa.phan_loai_lap (None: đã lập = tổng > 0)."""

    def __init__(self, dong: list, ten_dot: dict, ten_du_an: str = '', parent=None, im_lang: bool = False,
                 lap: dict | None = None):
        super().__init__(parent)
        self.im_lang = im_lang
        self.setWindowTitle(TIEU_DE)
        self.resize(*KICH_THUOC)
        self.ten_du_an = ten_du_an or ''
        self.tt = thong_ke_trang_thai(dong, lap)
        self.dot = thong_ke_dot(dong, ten_dot)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(14, 12, 14, 12)
        lo.setSpacing(8)
        self.lb_quy_mo = QLabel(f'Dự án: {self.ten_du_an or "(chưa đặt tên)"}  |  Quy mô: {chu_quy_mo(self.tt[0][1])}')
        self.lb_quy_mo.setObjectName('dai_thong_ke')
        dat_kieu_theo_tong(self.lb_quy_mo, QSS_DAI_THONG_TIN)       # nhãn lá (không phải khung chứa)
        self.lb_quy_mo.setWordWrap(True)
        lo.addWidget(self.lb_quy_mo)
        lo.addWidget(self._tieu_de('1. Tổng hợp Hộ · Thửa · Diện tích · Kinh phí theo Trạng thái thực hiện '
                                   '(Bôi đen ô bất kỳ để đếm / cộng nhanh):'))
        self.bang_tt = self._bang(COT_TRANG_THAI)
        self._nap_trang_thai()
        lo.addWidget(self.bang_tt)
        lo.addWidget(self._tieu_de('2. Tổng hợp Hộ · Thửa · Diện tích theo từng Đợt trình thẩm định:'))
        self.bang_dot = self._bang(COT_DOT)
        self._nap_dot()
        lo.addWidget(self.bang_dot)
        lo.addStretch(1)
        day = QHBoxLayout()
        from .giao_dien import KieuNut, NhanBoDem, ap_kieu_nut, cho_phep_sao_chep_bang
        self.lb_bo_dem_excel = NhanBoDem()                     # bộ đếm của hộp (góc dưới trái) - _BoChonVung gọi cap_nhat_bo_dem
        day.addWidget(self.lb_bo_dem_excel)
        day.addStretch(1)
        self.b_sao_chep = QPushButton('Sao chép tóm tắt báo cáo')
        ap_kieu_nut(self.b_sao_chep, KieuNut.CHINH)
        self.b_sao_chep.clicked.connect(lambda: self.sao_chep_tom_tat())
        self.b_dong = QPushButton('Đóng')
        self.b_dong.clicked.connect(self.reject)
        day.addWidget(self.b_sao_chep)
        day.addWidget(self.b_dong)
        lo.addLayout(day)
        for b in (self.bang_tt, self.bang_dot):
            cho_phep_sao_chep_bang(b)

    @staticmethod
    def _tieu_de(chu: str) -> QLabel:
        lb = QLabel(chu)
        dat_kieu_theo_tong(lb, 'QLabel { color: #0F172A; padding-top: 4px; }')
        f = lb.font()
        f.setBold(True)
        lb.setFont(f)
        lb.setWordWrap(True)
        return lb

    @staticmethod
    def _bang(cot: list) -> QTableWidget:
        b = QTableWidget(0, len(cot))
        b.setHorizontalHeaderLabels(cot)
        b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        b.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        b.verticalHeader().setVisible(False)
        b.setAlternatingRowColors(False)
        b.setWordWrap(False)
        return b

    def _o(self, b, r: int, c: int, chu: str, so: bool = True, dam: bool = False, nen: str | None = None) -> None:
        it = QTableWidgetItem(chu)
        it.setTextAlignment((Qt.AlignmentFlag.AlignRight if so else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter)
        if dam:
            f = QFont(QApplication.font())
            f.setBold(True)
            it.setFont(f)
        if nen:
            it.setBackground(QBrush(QColor(mau_theo_tong(nen, 'nen'))))
        b.setItem(r, c, it)

    def _vua(self, b) -> None:
        """Cột số vừa chữ (số / tiêu đề - không cắt "27.968.000.000"), cột 0 (nhãn) giãn lấp phần còn lại."""
        dau = b.horizontalHeader()
        dau.setStretchLastSection(False)
        dau.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, b.columnCount()):
            dau.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self._vua_cao(b)

    @staticmethod
    def _vua_cao(b) -> None:
        """Bảng cao vừa đủ mọi dòng (bảng đợt: tối đa DONG_DOT_TOI_DA dòng, nhiều hơn thì cuộn) - không thừa khoảng trống."""
        n = min(b.rowCount(), DONG_DOT_TOI_DA)
        cao = b.horizontalHeader().sizeHint().height() + sum(b.rowHeight(r) for r in range(n)) + 2 * b.frameWidth() + 2
        b.setFixedHeight(cao)

    def showEvent(self, e):                             # dòng bảng đổi chiều cao khi kiểu áp lúc hiện (giao_dien._BoToMau)
        super().showEvent(e)
        for b in (self.bang_tt, self.bang_dot):
            self._vua_cao(b)

    def _nap_trang_thai(self) -> None:
        b = self.bang_tt
        toan = self.tt[0][1]
        b.setRowCount(len(self.tt))
        for r, (nhan, n) in enumerate(self.tt):
            dam = r == 0
            nen = MAU_DONG_TONG if r == 0 else MAU_DONG_VUONG if r == len(self.tt) - 1 else None
            for c, (chu, so) in enumerate(((nhan, False), (str(n['so_ho']), True), (ty_le(n['so_ho'], toan['so_ho']), True),
                                           (str(n['so_thua']), True), (ty_le(n['so_thua'], toan['so_thua']), True),
                                           (so_luong_vn(n['dt']), True), (so_ha_bang(n['dt']), True), (vn(n['tong']), True))):
                self._o(b, r, c, chu, so, dam, nen)
        self._vua(b)

    def _nap_dot(self) -> None:
        b = self.bang_dot
        b.setRowCount(len(self.dot))
        for r, (ten, n, bg) in enumerate(self.dot):
            for c, (chu, so) in enumerate(((ten, False), (f'{n["so_ho"]} hộ', True), (f'{n["so_thua"]} thửa', True),
                                           (f'{so_luong_vn(n["dt"])} m²', True), (so_ha_bang(n['dt']), True),
                                           (f'{bg["so_ho"]}/{n["so_ho"]} hộ ({bg["so_thua"]} thửa)', True), (vn(n['tong']), True))):
                self._o(b, r, c, chu, so, dam=c == 0)
        self._vua(b)

    # ---- bộ đếm (giao_dien._BoChonVung gọi theo cửa sổ chứa bảng)
    def cap_nhat_bo_dem(self, bang, tk: dict) -> None:
        self.lb_bo_dem_excel.dat(tk)

    def tom_tat(self) -> str:
        """Tóm tắt báo cáo dạng chữ (dán vào Zalo / email / Word): quy mô, 7 trạng thái, từng đợt."""
        dong = [f'THỐNG KÊ HỘ · THỬA · DIỆN TÍCH - {self.ten_du_an or "Dự án"}',
                f'Quy mô: {chu_quy_mo(self.tt[0][1])}', '', 'I. Theo trạng thái thực hiện:']
        toan = self.tt[0][1]
        for nhan, n in self.tt:
            dong.append(f'{nhan}: {n["so_ho"]} hộ ({ty_le(n["so_ho"], toan["so_ho"])}) · {n["so_thua"]} thửa · '
                        f'{so_luong_vn(n["dt"])} m² ({so_ha_bang(n["dt"])}) · {vn(n["tong"])} đ')
        dong += ['', 'II. Theo đợt trình thẩm định:']
        for ten, n, bg in self.dot:
            dong.append(f'- {ten}: {n["so_ho"]} hộ · {n["so_thua"]} thửa · {so_luong_vn(n["dt"])} m² ({so_ha_bang(n["dt"])}) · '
                        f'đã bàn giao {bg["so_ho"]}/{n["so_ho"]} hộ · {vn(n["tong"])} đ')
        return '\n'.join(dong)

    def sao_chep_tom_tat(self) -> str:
        chu = self.tom_tat()
        QApplication.clipboard().setText(chu)
        from .giao_dien import thong_bao_noi
        thong_bao_noi(self, 'Đã sao chép tóm tắt báo cáo thống kê')
        return chu
