"""Màn hình tổng quan dự án (1.0.07 - "Executive Project Cockpit", người dùng 20/10/2026): Màn hình chính khi ĐÃ mở dự án.

Bố cục: dải tổng thuật dự án | 4 thẻ khởi tạo & nhập (dùng chính QAction của lệnh: Dự án mới, Mở dự án, Nhập file Excel, Nhập phương
án chi tiết) | 4 thẻ chỉ số (quy mô, tổng kinh phí, phê duyệt, bàn giao) | chia 65% / 35%: hộ đang làm dở (chưa phê duyệt, nút "Lập
PA" mở thẳng hộ) - đồng hồ pháp lý (niêm yết, hộ vướng V1-V5, vận động / cưỡng chế). Số liệu: tong_quan_du_an (không Qt). Không emoji
(Windows 7): biểu tượng theo phông Segoe MDL2 (icon_ky_hieu).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton, QSizePolicy, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import tong_quan_du_an as tq
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (1.0.34: kiểu riêng đổi theo tông nền)
from .tien import so_luong_vn, vn, vn_gon

LENH_KHOI_TAO = (                    # (khóa self.lenh, chữ trên thẻ, mô tả)
    ('Dự án mới…', 'Dự án mới', 'Khởi tạo CSDL .larc mới'),
    ('Mở dự án…', 'Mở dự án (Ctrl+O)', 'Chọn tệp từ máy / LAN / gần đây'),
    ('Nhập file Excel…', 'Nhập file Excel', 'Bảng kiểm đếm, đo đạc thô'),
    ('Nhập phương án chi tiết…', 'Nhập PA chi tiết từ Excel', 'Mỗi sheet một phương án'),
)
MAU_KPI = (('quy_mo', 'Quy mô dự án', '#2563EB'), ('kinh_phi', 'Tổng kinh phí phương án', '#D97706'),
           ('phe_duyet', 'Tiến độ phê duyệt', '#059669'), ('ban_giao', 'Bàn giao mặt bằng', '#0D9488'))
TI_LE_CHIA = (65, 35)                # bên trái : bên phải

QSS_TONG_QUAN = '''
QFrame#dai_tong_thuat { background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #1E3A8A; border-radius: 6px; }
QLabel#tq_ten { font-size: 16px; font-weight: 700; color: #0F172A; background: transparent; border: 0; }
QLabel#tq_phu { font-size: 12px; color: #64748B; background: transparent; border: 0; }
QToolButton#the_khoi_tao { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px;
    text-align: left; font-size: 13px; font-weight: 600; color: #0F172A; }
QToolButton#the_khoi_tao:hover { background: #F0F6FF; border-color: #1E3A8A; }
QToolButton#the_khoi_tao:disabled { color: #94A3B8; }
QFrame#khung_tq { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }
QLabel#tq_tieu_de { font-size: 13px; font-weight: 700; color: #1E3A8A; background: transparent; border: 0; }
QFrame#the_phap_ly { background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 3px solid #1E3A8A; border-radius: 3px; }
QFrame#the_phap_ly[muc="canh_bao"] { border-left-color: #C98A22; background: #FFFBEB; }
QFrame#the_phap_ly[muc="nguy"] { border-left-color: #B83A3A; background: #FEF2F2; }
QFrame#the_phap_ly[muc="dat"] { border-left-color: #1F6F66; }
QLabel#tq_dong_ho { font-size: 12px; color: #0F172A; background: transparent; border: 0; }
QPushButton#nut_lap_pa { background: transparent; color: #1E3A8A; border: 1px solid #CBD5E1; border-radius: 4px; padding: 1px 10px;
    margin: 3px 6px; font-weight: 600; }
QPushButton#nut_lap_pa:hover { background: #EFF6FF; border-color: #1E3A8A; }
'''


class KhungTongQuanDuAn(QWidget):
    mo_ho = Signal(int)              # bấm "Lập PA" của một hộ

    def __init__(self, lenh: dict | None = None, parent=None):
        super().__init__(parent)
        from .giao_dien import HangKpi, nut_lenh
        self.setObjectName('tong_quan_du_an')
        dat_kieu_theo_tong(self, QSS_TONG_QUAN)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(16, 12, 16, 12)
        lo.setSpacing(10)
        # dải tổng thuật
        dai = QFrame()
        dai.setObjectName('dai_tong_thuat')
        dv = QVBoxLayout(dai)
        dv.setContentsMargins(12, 8, 12, 8)
        dv.setSpacing(2)
        self.lb_ten = QLabel('')
        self.lb_ten.setObjectName('tq_ten')
        self.lb_ten.setWordWrap(True)
        self.lb_phu = QLabel('')
        self.lb_phu.setObjectName('tq_phu')
        self.lb_phu.setWordWrap(True)
        dv.addWidget(self.lb_ten)
        dv.addWidget(self.lb_phu)
        lo.addWidget(dai)
        # 4 thẻ khởi tạo & nhập - cùng QAction với menu (lệnh tắt thì thẻ tắt)
        h = QHBoxLayout()
        h.setSpacing(10)
        self.the_khoi_tao = {}
        for khoa, chu, mo_ta in LENH_KHOI_TAO:
            a = (lenh or {}).get(khoa)
            if a is None:
                continue
            b = nut_lenh(a, 22)
            b.setObjectName('the_khoi_tao')
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setMinimumHeight(44)
            b.setToolTip(f'{chu} - {mo_ta}')
            self.the_khoi_tao[khoa] = b
            h.addWidget(b, 1)
        lo.addLayout(h)
        # 4 thẻ chỉ số
        self.kpi = HangKpi([(k, ten, mau) for k, ten, mau in MAU_KPI])
        lo.addWidget(self.kpi)
        # chia 65 / 35
        self.chia = QSplitter(Qt.Orientation.Horizontal)
        self.chia.setChildrenCollapsible(False)
        trai = QFrame()
        trai.setObjectName('khung_tq')
        tv = QVBoxLayout(trai)
        tv.setContentsMargins(10, 8, 10, 8)
        tv.setSpacing(6)
        self.lb_dang_lam = QLabel('Hộ đang làm dở / chưa phê duyệt')
        self.lb_dang_lam.setObjectName('tq_tieu_de')
        tv.addWidget(self.lb_dang_lam)
        self.bang = QTableWidget(0, 5)
        self.bang.setHorizontalHeaderLabels(['STT', 'Họ và tên', 'Trạng thái', 'Tổng kinh phí', 'Thao tác'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.bang.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (0, 2, 3, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.bang.cellDoubleClicked.connect(lambda r, _c: self._mo_dong(r))
        tv.addWidget(self.bang, 1)
        phai = QFrame()
        phai.setObjectName('khung_tq')
        pv = QVBoxLayout(phai)
        pv.setContentsMargins(10, 8, 10, 8)
        pv.setSpacing(8)
        t = QLabel('Đồng hồ pháp lý')
        t.setObjectName('tq_tieu_de')
        pv.addWidget(t)
        self.dong_ho = {}
        for k in ('niem_yet', 'vuong', 'cuong_che'):
            f = QFrame()
            f.setObjectName('the_phap_ly')
            fv = QVBoxLayout(f)
            fv.setContentsMargins(10, 6, 10, 6)
            lb = QLabel('')
            lb.setObjectName('tq_dong_ho')
            lb.setWordWrap(True)
            lb.setTextFormat(Qt.TextFormat.RichText)
            fv.addWidget(lb)
            pv.addWidget(f)
            self.dong_ho[k] = (f, lb)
        pv.addStretch(1)
        self.chia.addWidget(trai)
        self.chia.addWidget(phai)
        self.chia.setStretchFactor(0, TI_LE_CHIA[0])
        self.chia.setStretchFactor(1, TI_LE_CHIA[1])
        lo.addWidget(self.chia, 1)
        self.so_lieu = None

    # ------------------------------------------------ nạp số liệu
    def nap(self, con, dong: list, ten: str = '', dia_ban: str = '', file: str = '', chu_dau_tu: str = '', hom_nay=None) -> dict:
        kq = tq.tinh(con, dong, hom_nay)
        self.so_lieu = kq
        self.lb_ten.setText(' · '.join(x for x in (ten or 'Dự án', dia_ban) if x))
        self.lb_phu.setText(' · '.join(x for x in ((f'Chủ đầu tư: {chu_dau_tu}' if chu_dau_tu else ''), file) if x))
        qm, kp, td = kq['quy_mo'], kq['kinh_phi'], kq['tien_do']
        self.kpi.dat('quy_mo', f'{qm["so_ho"]} hộ', f'{qm["so_thua"]} thửa · {vn(qm["dt_ha"], 2)} ha',
                     f'{qm["so_ho"]} hộ / {qm["so_thua"]} thửa / diện tích thu hồi {so_luong_vn(qm["dt_m2"])} m² ({vn(qm["dt_ha"], 4)} ha)')
        self.kpi.dat('kinh_phi', vn_gon(kp['tong']), f'Đất {vn_gon(kp["dat"])} · Tài sản, hỗ trợ {vn_gon(kp["con_lai"])}',
                     f'Tổng {vn(kp["tong"])} đồng\nĐất: {vn(kp["dat"])} đồng\nTài sản, cây, vật nuôi, hỗ trợ, thưởng: '
                     f'{vn(kp["con_lai"])} đồng')
        n = td['n'] or 0
        self.kpi.dat('phe_duyet', f'{td["da_pd"]}/{td["n"]} hộ', td['pt_pd'], f'Đã lập phương án: {td["da_lap"]}/{td["n"]} hộ',
                     tien_do=td['da_pd'] * 100 / n if n else 0)
        self.kpi.dat('ban_giao', f'{td["da_bg"]}/{td["n"]} hộ', td['pt_bg'],
                     'Bàn giao mặt bằng: đã có quyết định, nhận đủ tiền và ngày biên bản (phân tích tiến độ tự động)',
                     tien_do=td['da_bg'] * 100 / n if n else 0)
        self._ve_bang(kq)
        self._ve_dong_ho(kq)
        return kq

    def _ve_bang(self, kq: dict) -> None:
        ds = kq['ho_dang_lam']
        n = kq['so_ho_dang_lam']
        self.lb_dang_lam.setText(f'Hộ đang làm dở / chưa phê duyệt ({n} hộ' + (f', hiện {len(ds)} hộ đầu)' if n > len(ds) else ')'))
        b = self.bang
        b.setUpdatesEnabled(False)
        b.setRowCount(0)
        b.setRowCount(len(ds))
        for r, x in enumerate(ds):
            it = QTableWidgetItem('' if x['stt'] is None else str(x['stt']))
            it.setData(Qt.ItemDataRole.UserRole, x['ma_ho'])
            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            b.setItem(r, 0, it)
            b.setItem(r, 1, QTableWidgetItem(x['ho_ten']))
            b.setItem(r, 2, QTableWidgetItem(x['trang_thai'] or ('Đã lập, chưa duyệt' if x['da_lap'] else 'Chưa lập phương án')))
            t = QTableWidgetItem(vn(x['tong']) if x['tong'] else '-')
            t.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            b.setItem(r, 3, t)
            nut = QPushButton('Lập PA →')
            nut.setObjectName('nut_lap_pa')
            nut.setCursor(Qt.CursorShape.PointingHandCursor)
            nut.setToolTip('Mở thẳng cửa sổ lập phương án của hộ này')
            nut.clicked.connect(lambda _=False, m=x['ma_ho']: self.mo_ho.emit(m))
            b.setCellWidget(r, 4, nut)
        b.setUpdatesEnabled(True)

    def _mo_dong(self, r: int) -> None:
        it = self.bang.item(r, 0)
        if it is not None and it.data(Qt.ItemDataRole.UserRole) is not None:
            self.mo_ho.emit(int(it.data(Qt.ItemDataRole.UserRole)))

    @staticmethod
    def _muc(f: QFrame, muc: str) -> None:
        f.setProperty('muc', muc)
        f.style().unpolish(f)
        f.style().polish(f)

    def _ve_dong_ho(self, kq: dict) -> None:
        from . import du_thao
        f, lb = self.dong_ho['niem_yet']
        ny = kq['niem_yet']
        if ny is None:
            self._muc(f, '')
            lb.setText(f'<b>Niêm yết công khai</b> (Điều 87 Luật Đất đai 2024, {du_thao.SO_NGAY_NIEM_YET} ngày)<br>'
                       'Chưa có đợt niêm yết - mở <i>Niêm yết &amp; Lấy ý kiến</i> ở menu trái.')
        else:
            c = ny['con_ngay']
            if c is None:
                chu, muc = 'chưa có ngày kết thúc', ''
            elif c >= 0:
                chu, muc = f'còn <b>{c} ngày</b> (kết thúc {du_thao.hien_ngay(ny["ngay_ket_thuc"])})', 'canh_bao' if c <= 3 else 'dat'
            else:
                chu, muc = f'đã hết hạn {-c} ngày (kết thúc {du_thao.hien_ngay(ny["ngay_ket_thuc"])})', 'dat'
            dt = ny['con_ngay_doi_thoai']
            them = '' if dt is None else (f'<br>Hạn đối thoại: còn {dt} ngày' if dt >= 0 else f'<br>Hạn đối thoại đã qua {-dt} ngày')
            self._muc(f, muc)
            lb.setText(f'<b>Niêm yết công khai</b> (Điều 87, {ny["so_ngay"]} ngày) - {ny["ten"]}: {chu}{them}')
        f, lb = self.dong_ho['vuong']
        v = kq['so_ho_vuong']
        self._muc(f, 'canh_bao' if v else 'dat')
        lb.setText(f'<b>Hộ vướng V1-V5</b>: {v:02d} hộ chưa đủ điều kiện niêm yết' if v else
                   '<b>Hộ vướng V1-V5</b>: không có hộ vướng')
        f, lb = self.dong_ho['cuong_che']
        cc = kq['cuong_che']
        self._muc(f, 'nguy' if cc['du_cc'] else ('canh_bao' if cc['dang_vd'] else 'dat'))
        lb.setText(f'<b>Vận động, cưỡng chế</b> (Điều 89): {cc["dang_vd"]} hộ đang vận động · '
                   f'{cc["du_cc"]} hộ đủ điều kiện đề nghị cưỡng chế')
