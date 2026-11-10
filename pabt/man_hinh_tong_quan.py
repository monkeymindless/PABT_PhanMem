"""Màn hình tổng quan dự án (1.0.07 - "Executive Project Cockpit", người dùng 20/10/2026): Màn hình chính khi ĐÃ mở dự án.

Bố cục: dải tổng thuật dự án | 4 thẻ khởi tạo & nhập (dùng chính QAction của lệnh: Dự án mới, Mở dự án, Nhập file Excel, Nhập phương
án chi tiết) | 4 thẻ chỉ số (quy mô, tổng kinh phí, phê duyệt, bàn giao) | chia 65% / 35%: hộ đang làm dở (chưa phê duyệt, nút "Lập
PA" mở thẳng hộ) - đồng hồ pháp lý (niêm yết, hộ vướng V1-V5, vận động / cưỡng chế). Số liệu: tong_quan_du_an (không Qt). Không emoji
(Windows 7): biểu tượng theo phông Segoe MDL2 (icon_ky_hieu).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton, QSizePolicy,
                               QSplitter, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import pheu_tien_do as ph
from . import quy_trinh as qt
from . import tong_quan_du_an as tq
from .giao_dien import cai_dat_nho, dat_kieu_theo_tong, qmau_theo_tong  # noqa: E402  (1.0.34: kiểu riêng đổi theo tông nền)
from .tien import so_luong_vn, vn, vn_gon

LENH_KHOI_TAO = (                    # (khóa self.lenh, chữ trên thẻ, mô tả)
    ('Dự án mới…', 'Dự án mới', 'Khởi tạo CSDL .larc mới'),
    ('Mở dự án…', 'Mở dự án (Ctrl+O)', 'Chọn tệp từ máy / LAN / gần đây'),
    ('Nhập file Excel…', 'Nhập file Excel', 'Bảng kiểm đếm, đo đạc thô'),
    ('Nhập phương án chi tiết…', 'Nhập PA chi tiết từ Excel', 'Mỗi sheet một phương án'),
)
MAU_KPI = (('quy_mo', 'Quy mô dự án', '#2563EB'), ('kinh_phi', 'Tổng kinh phí phương án', '#D97706'),
           ('phe_duyet', 'Tiến độ phê duyệt', '#059669'), ('ban_giao', 'Bàn giao mặt bằng', '#0D9488'))
TI_LE_CHIA = (72, 28)                # bên trái : bên phải (31/10/2026: 65 : 35 -> bảng hộ rộng hơn)
RONG_COT_PHAI = (260, 380)           # cột việc nên làm tiếp / đồng hồ pháp lý: tối thiểu, tối đa (màn hình lớn không giãn mãi)
CAO_THE_KHOI_TAO = 36                # 30/10/2026: 44 -> 36 (đã mở dự án thì ít dùng - nhường chỗ cho thanh quy trình)
CAO_PHAN_DUOI_TOI_THIEU = 400        # bảng hộ đang làm + việc nên làm tiếp + đồng hồ pháp lý: thấp hơn thì cuộn, không bóp

QSS_TONG_QUAN = '''
QFrame#dai_tong_thuat { background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #1E3A5F; border-radius: 6px; }
QLabel#tq_ten { font-size: 16px; font-weight: 700; color: #0F172A; background: transparent; border: 0; }
QLabel#tq_phu { font-size: 12px; color: #64748B; background: transparent; border: 0; }
QToolButton#the_khoi_tao { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px;
    text-align: left; font-size: 13px; font-weight: 600; color: #0F172A; }
QToolButton#the_khoi_tao:hover { background: #F0F6FF; border-color: #1E3A5F; }
QToolButton#the_khoi_tao:disabled { color: #94A3B8; }
QFrame#khung_tq { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }
QLabel#tq_tieu_de { font-size: 13px; font-weight: 700; color: #1E3A5F; background: transparent; border: 0; }
QFrame#the_phap_ly { background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 3px solid #1E3A5F; border-radius: 3px; }
QFrame#the_phap_ly[muc="canh_bao"] { border-left-color: #C98A22; background: #FFFBEB; }
QFrame#the_phap_ly[muc="nguy"] { border-left-color: #B83A3A; background: #FEF2F2; }
QFrame#the_phap_ly[muc="dat"] { border-left-color: #1F6F66; }
QLabel#tq_dong_ho { font-size: 12px; color: #0F172A; background: transparent; border: 0; }
/* 1.0.93: nút trong dòng = cấp BA (liên kết phẳng, viền chỉ hiện khi rê chuột) - người dùng chọn hệ nút 3 cấp 10/11/2026 */
QPushButton#nut_lap_pa { background: transparent; color: #2563EB; border: 1px solid transparent; border-radius: 4px; padding: 1px 10px;
    margin: 3px 6px; font-weight: 600; }
QPushButton#nut_lap_pa:hover { background: #EFF6FF; border-color: #CBD5E1; }
QFrame#khung_pheu { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }
QLabel#ph_tieu_de { font-size: 13px; font-weight: 700; color: #1E3A5F; background: transparent; border: 0; }
QLabel#ph_phu { font-size: 12px; color: #475569; background: transparent; border: 0; }
QToolButton#ph_chu_giai { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 2px 6px; font-size: 12px;
    color: #0F172A; text-align: left; }
QToolButton#ph_chu_giai[rong="0"] { color: #64748B; }
QToolButton#ph_chu_giai[rong="1"] { color: #0F172A; font-weight: 600; }
QToolButton#ph_chu_giai:hover { background: #F1F5F9; border-color: #CBD5E1; }
QToolButton#ph_co { background: #FFFBEB; border: 1px solid #F1D9A0; border-radius: 10px; padding: 1px 9px; font-size: 12px; color: #7A4B00; }
QToolButton#ph_co:hover { border-color: #C98A22; }
QLabel#qt_viec { font-size: 12px; color: #0F172A; background: transparent; border: 0; }
QPushButton#nut_viec { background: transparent; color: #2563EB; border: 1px solid transparent; border-radius: 4px; padding: 2px 10px;
    min-height: 22px; font-weight: 600; }
QPushButton#nut_viec:hover { background: #EFF6FF; border-color: #CBD5E1; }
'''
# màu chấm trạng thái của việc (theo mức) - chữ trên nền trắng của khung
TOI_DA_VIEC_HIEN = 5                 # 1.0.94: Việc nên làm tiếp - số việc thấy ngay
MAU_MUC_VIEC = {'loi': '#DC2626', 'can': '#2563EB', 'nhac': '#B45309'}
TEN_MUC_VIEC = {'loi': 'Cần xử lý ngay', 'can': 'Việc cần làm', 'nhac': 'Nhắc việc'}


# phễu tiến độ theo hộ (30/10/2026 - thay thanh 16 bước cấp dự án): màu 8 giai đoạn từ xám (chưa lập) qua xanh tới lục (hoàn tất)
MAU_GIAI_DOAN = {'chua_lap': '#B4B2A9', 'da_lap': '#85B7EB', 'niem_yet': '#378ADD', 'cho_trinh': '#7F77DD', 'cho_phe_duyet': '#534AB7',
                 'cho_chi_tra': '#EF9F27', 'cho_ban_giao': '#1D9E75', 'hoan_tat': '#0F6E56'}
CAO_DAI_PHEU = 12
RONG_DAI_PHEU_TOI_THIEU = 120        # dải phễu nằm cùng hàng tiêu đề (31/10/2026) - hẹp hơn thì vẫn đọc được các đoạn chính
KHOA_THU_GON_PHEU = 'tong_quan/thu_gon_pheu'
BUOC_DU_AN = (1, 2, 3)               # việc làm một lần cho cả dự án (quy_trinh): khái toán / pháp lý, họp dân, thông báo thu hồi


class DaiPheu(QWidget):
    """Một dải mảnh chia đoạn theo số hộ của từng giai đoạn; bấm đoạn -> chon(giai đoạn). Rê chuột: tên + số hộ."""
    chon = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(CAO_DAI_PHEU)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.dem = {}

    def dat(self, dem: dict) -> None:
        self.dem = dict(dem)
        self.setToolTip('\n'.join(f'{ph.TEN_GIAI_DOAN[k]}: {n} hộ' for k, n in self.dem.items() if n))
        self.update()

    def _doan(self):
        tong = sum(self.dem.values())
        x, w = 0.0, float(self.width())
        for k, _ in ph.GIAI_DOAN_HO:
            n = self.dem.get(k, 0)
            if n and tong:
                rong = w * n / tong
                yield k, x, rong
                x += rong

    def paintEvent(self, _e):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QPainter, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        vien = QPainterPath()
        vien.addRoundedRect(r, self.height() / 2, self.height() / 2)
        p.setClipPath(vien)
        p.fillRect(r, qmau_theo_tong('#F1F5F9'))         # 1.0.93: nền thanh theo tông (Tối trước đây vẫn sáng)
        for k, x, rong in self._doan():
            p.fillRect(QRectF(x, 0, rong + 0.5, self.height()), QColor(MAU_GIAI_DOAN[k]))
        p.end()

    def mouseReleaseEvent(self, e):
        x = e.position().x() if hasattr(e, 'position') else e.x()
        for k, x0, rong in self._doan():
            if x0 <= x <= x0 + rong:
                self.chon.emit(k)
                return


class KhungPheu(QFrame):
    """Việc cấp dự án (bước 1-3, một dòng) + phễu tiến độ theo hộ (pheu_tien_do): ô chọn phạm vi (cả dự án / từng đợt niêm yết /
    đợt trình) và cách xét lần phương án (đang mở / gốc), dải 8 giai đoạn + chú giải bấm được, các cờ "Cần kiểm tra".
    Tín hiệu: mo_ds(tiêu đề, [HoPheu]) mở danh sách hộ; mo_buoc(bước) cho việc cấp dự án; doi_che_do(che_do) tính lại phễu."""
    mo_ds = Signal(str, list)
    mo_buoc = Signal(int)
    doi_che_do = Signal(str)

    def __init__(self, parent=None):
        from PySide6.QtWidgets import QComboBox
        from .giao_dien import XepDong
        super().__init__(parent)
        self.setObjectName('khung_pheu')
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 6, 10, 6)
        lo.setSpacing(4)
        # 31/10/2026 (người dùng: "giảm kích thước phễu để khung hộ dân rộng rãi cho màn hình nhỏ"): MỘT hàng tiêu đề + dải phễu +
        # ô chọn + nút thu gọn; chú giải, cờ, việc cả dự án xếp nối tiếp (XepDong - hẹp thì xuống dòng, không đẩy trang tràn ngang)
        h = QHBoxLayout()
        h.setSpacing(6)
        self.lb_tieu_de = QLabel('Tiến độ theo hộ')
        self.lb_tieu_de.setObjectName('ph_tieu_de')
        h.addWidget(self.lb_tieu_de)
        self.lb_tom_tat = QLabel('')
        self.lb_tom_tat.setObjectName('ph_phu')
        h.addWidget(self.lb_tom_tat)
        self.dai = DaiPheu()
        self.dai.setMinimumWidth(RONG_DAI_PHEU_TOI_THIEU)
        self.dai.chon.connect(self._chon_giai_doan)
        h.addWidget(self.dai, 1)
        self.cb_pham_vi = QComboBox()
        self.cb_pham_vi.setToolTip('Xem phễu của cả dự án hoặc của một đợt niêm yết / đợt trình')
        self.cb_pham_vi.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_pham_vi.setMinimumContentsLength(10)
        self.cb_pham_vi.currentIndexChanged.connect(lambda _: self._ve())
        h.addWidget(self.cb_pham_vi)
        self.cb_lan = QComboBox()
        self.cb_lan.addItem('Lần PA đang mở', 'mo')
        self.cb_lan.addItem('Phương án gốc (lần 1)', 'goc')
        self.cb_lan.setToolTip('Hộ có phương án bổ sung / điều chỉnh: xét theo lần đang mở, hoặc theo phương án gốc')
        self.cb_lan.currentIndexChanged.connect(lambda _: self.doi_che_do.emit(self.cb_lan.currentData()))
        h.addWidget(self.cb_lan)
        self.nut_thu_gon = QToolButton()
        self.nut_thu_gon.setObjectName('ph_chu_giai')
        self.nut_thu_gon.setCheckable(True)
        self.nut_thu_gon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nut_thu_gon.toggled.connect(self.thu_gon)
        h.addWidget(self.nut_thu_gon)
        lo.addLayout(h)
        # phần chi tiết (ẩn khi thu gọn): chú giải 8 giai đoạn | cờ cần kiểm tra + việc của cả dự án
        self.chi_tiet = QWidget()
        cv = QVBoxLayout(self.chi_tiet)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(2)
        x = XepDong(cach=2)
        self.chu_giai = {}
        for k, ten in ph.GIAI_DOAN_HO:
            n = QToolButton()
            n.setObjectName('ph_chu_giai')
            n.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)      # mặc định QToolButton chỉ vẽ biểu tượng
            n.setAutoRaise(True)
            n.setCursor(Qt.CursorShape.PointingHandCursor)
            n.setToolTip(ph.CHU_THICH_MOC.get(k) or f'{ten} - bấm để xem danh sách hộ')
            n.clicked.connect(lambda _=False, k=k: self._chon_giai_doan(k))
            self.chu_giai[k] = n
            x.addWidget(n)
        x.addWidget(self._gian(x))
        cv.addLayout(x)
        x = XepDong(cach=6)
        self.lb_co = QLabel('Cần kiểm tra:')
        self.lb_co.setObjectName('ph_phu')
        x.addWidget(self.lb_co)
        self.nut_co = {}
        for k, ten in ph.CO:
            n = QToolButton()
            n.setObjectName('ph_co')
            n.setCursor(Qt.CursorShape.PointingHandCursor)
            n.setToolTip(f'{ten} - bấm để xem danh sách hộ')
            n.clicked.connect(lambda _=False, k=k: self._chon_co(k))
            self.nut_co[k] = n
            x.addWidget(n)
        t = QLabel('Cả dự án:')
        t.setObjectName('ph_phu')
        x.addWidget(t)
        self.nut_du_an = {}
        for b in BUOC_DU_AN:
            n = QToolButton()
            n.setObjectName('ph_chu_giai')
            n.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            n.setCursor(Qt.CursorShape.PointingHandCursor)
            n.clicked.connect(lambda _=False, b=b: self.mo_buoc.emit(b))
            self.nut_du_an[b] = n
            x.addWidget(n)
        x.addWidget(self._gian(x))
        cv.addLayout(x)
        lo.addWidget(self.chi_tiet)
        self.ket_qua = None
        self.du_an = None
        cd = cai_dat_nho()
        self.nut_thu_gon.setChecked(bool(cd is not None and str(cd.value(KHOA_THU_GON_PHEU, '0')).lower() in ('1', 'true')))
        self.thu_gon(self.nut_thu_gon.isChecked(), luu=False)

    @staticmethod
    def _gian(x) -> QLabel:
        """Ô rỗng nhận phần rộng thừa cuối dòng - các mục chú giải xếp sát trái, không bị kéo giãn."""
        o = QLabel('')
        o.setStyleSheet('background: transparent; border: 0;')
        x.gian(o)
        return o

    def thu_gon(self, gon: bool, luu: bool = True) -> None:
        """Thu gọn = chỉ còn hàng tiêu đề + dải phễu (rê chuột / bấm dải vẫn xem được số hộ từng giai đoạn); nhớ lựa chọn."""
        self.chi_tiet.setVisible(not gon)
        self.nut_thu_gon.setText('Chi tiết ▾' if gon else 'Thu gọn ▴')
        self.nut_thu_gon.setToolTip('Hiện chú giải giai đoạn, các cờ cần kiểm tra và việc của cả dự án' if gon else
                                    'Chỉ giữ dải phễu - nhường chỗ cho bảng hộ (màn hình nhỏ)')
        if luu:
            cd = cai_dat_nho()
            if cd is not None:
                cd.setValue(KHOA_THU_GON_PHEU, '1' if gon else '0')

    @staticmethod
    def _bieu_tuong(mau: str):
        from PySide6.QtGui import QColor, QIcon, QPixmap
        pm = QPixmap(10, 10)
        pm.fill(QColor(mau))
        return QIcon(pm)

    def dat(self, kq, dot_ny: list, dot_trinh: list, du_an=None) -> None:
        """kq: pheu_tien_do.KetQuaPheu; dot_ny / dot_trinh: [(id, tên)]; du_an: quy_trinh.KetQuaQuyTrinh (bước 1-3) hoặc None."""
        self.ket_qua, self.du_an = kq, du_an
        cu = self.cb_pham_vi.currentData()
        self.cb_pham_vi.blockSignals(True)
        self.cb_pham_vi.clear()
        self.cb_pham_vi.addItem('Cả dự án', 'ca')
        for i, ten in dot_ny:
            self.cb_pham_vi.addItem(f'Niêm yết: {ten}', ('ny', i))
        for i, ten in dot_trinh:
            self.cb_pham_vi.addItem(f'Trình: {ten}', ('tr', i))
        j = self.cb_pham_vi.findData(cu if cu not in (None, '') else 'ca')
        self.cb_pham_vi.setCurrentIndex(max(j, 0))
        self.cb_pham_vi.blockSignals(False)
        for b, n in self.nut_du_an.items():
            t = du_an.buoc[b] if du_an is not None else None
            xong = t is not None and t.trang_thai == 'xong'
            n.setText(('Đã ' if xong else 'Chưa: ') + qt.TEN_NGAN[b].lower() + (f' {t.ngay.strftime("%d/%m/%Y")}' if xong and t.ngay else ''))
            n.setIcon(self._bieu_tuong('#0F6E56' if xong else '#B4B2A9'))
            n.setToolTip(f'Bước {b} - {qt.TEN_BUOC[b]}: ' + (t.mo_ta if t is not None else '') +
                         ('\nBấm để ghi / sửa ngày' if b in qt.MOC_BUOC else '\nBấm để mở chỗ làm'))
        self._ve()

    def ds_dang_xem(self) -> list:
        kq = self.ket_qua
        if kq is None:
            return []
        pv = self.cb_pham_vi.currentData()
        if pv in (None, '', 'ca') or not isinstance(pv, (tuple, list)) or len(pv) != 2:
            return kq.ho
        if pv[0] == 'ny':
            return kq.loc_dot(dot_niem_yet=pv[1])
        if pv[0] == 'tr':
            return kq.loc_dot(dot_trinh=pv[1])
        return kq.ho

    def _ve(self) -> None:
        kq = self.ket_qua
        if kq is None:
            return
        ds = self.ds_dang_xem()
        dem = kq.dem(ds)                    # dải phễu: mỗi hộ đúng một đoạn
        hien = kq.dem_hien_thi(ds)          # ô chú giải: Đã lập / Niêm yết = lũy kế
        self.dai.dat(dem)
        for k, n in self.chu_giai.items():
            so = hien.get(k, 0)
            n.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            n.setText(f'{ph.TEN_NGAN_GIAI_DOAN[k]}  {so}')
            n.setIcon(self._bieu_tuong(MAU_GIAI_DOAN[k]))
            n.setProperty('rong', '1' if so else '0')
            n.setVisible(bool(so))                         # 1.0.94: ẩn trạng thái 0 hộ (tên ở chú thích dòng tóm tắt)
            n.style().unpolish(n)
            n.style().polish(n)
            if k in ph.MOC_LUY_KE:
                n.setToolTip(ph.CHU_THICH_MOC[k] + (f' Đang đứng đúng ô này: {dem.get(k, 0)} hộ.' if dem.get(k) else ''))
            else:
                n.setToolTip(f'{ph.TEN_GIAI_DOAN[k]} - bấm để xem danh sách hộ')
        bs = sum(1 for x in ds if 'pa_bo_sung' in x.co)
        self.lb_tom_tat.setText(f'{len(ds)} hộ' + (f' · {bs} hộ đang xét phương án bổ sung / điều chỉnh' if bs else ''))
        an = [ph.TEN_NGAN_GIAI_DOAN[k] for k in self.chu_giai if not hien.get(k, 0)]
        self.lb_tom_tat.setToolTip(('Chưa có hộ ở: ' + ', '.join(an)) if an else '')
        co = kq.dem_co(ds)
        for k, n in self.nut_co.items():
            n.setText(f'{co.get(k, 0)} hộ: {ph.TEN_CO[k].lower()}')
            n.setVisible(bool(co.get(k)))
        self.lb_co.setVisible(any(co.get(k) for k in self.nut_co))

    def _chon_giai_doan(self, k: str) -> None:
        if self.ket_qua is None:
            return
        ds = self.ket_qua.theo_moc(k, self.ds_dang_xem())
        ten = ph.TEN_GIAI_DOAN.get(k, k)
        if k in ph.MOC_LUY_KE:
            ten = ph.CHU_THICH_MOC[k].split('.')[0]
        self.mo_ds.emit(f'{ten} ({len(ds)} hộ)', ds)

    def _chon_co(self, k: str) -> None:
        if self.ket_qua is None:
            return
        ds = [x for x in self.ds_dang_xem() if k in x.co]
        self.mo_ds.emit(f'{ph.TEN_CO[k]} ({len(ds)} hộ)', ds)


class HopHoPheu(QDialog):
    """Danh sách hộ của một giai đoạn / một cờ (hộp thoại KHÔNG chặn - show(), như HopBanDo): STT, họ tên, giai đoạn, lần PA, cần
    kiểm tra. Bấm đúp -> mo_ho(mã hộ). QDialog (không QWidget cửa sổ riêng): quy ước cửa sổ phụ của gói pabt - kiem_tra_giao_dien
    coi widget cấp cao không phải QDialog là "cửa sổ lạ"."""
    mo_ho = Signal(int)
    im_lang = False

    def __init__(self, tieu_de: str, ds: list, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle(tieu_de)
        self.resize(820, 480)
        lo = QVBoxLayout(self)
        lb = QLabel(f'{tieu_de} - bấm đúp một hộ để mở phương án.')
        lb.setWordWrap(True)
        lo.addWidget(lb)
        self.bang = QTableWidget(len(ds), 5)
        self.bang.setHorizontalHeaderLabels(['STT', 'Họ và tên', 'Giai đoạn', 'Lần PA', 'Cần kiểm tra'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.bang.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for r, x in enumerate(ds):
            it = QTableWidgetItem('' if x.stt is None else str(x.stt))
            it.setData(Qt.ItemDataRole.UserRole, x.ma_ho)
            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.bang.setItem(r, 0, it)
            self.bang.setItem(r, 1, QTableWidgetItem(x.ho_ten or ''))
            self.bang.setItem(r, 2, QTableWidgetItem(ph.ten_giai_doan(x)))
            it = QTableWidgetItem(str(x.lan))
            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.bang.setItem(r, 3, it)
            self.bang.setItem(r, 4, QTableWidgetItem('; '.join(ph.TEN_CO[k] for k, _ in ph.CO if k in x.co)))
        self.bang.cellDoubleClicked.connect(self._mo)
        lo.addWidget(self.bang, 1)

    def _mo(self, r: int, _c: int) -> None:
        it = self.bang.item(r, 0)
        if it is not None:
            self.mo_ho.emit(int(it.data(Qt.ItemDataRole.UserRole)))


class KhungViecTiep(QFrame):
    """"Việc nên làm tiếp" (pheu_tien_do.viec_tiep + việc cấp dự án chưa xong): mỗi việc một dòng - chấm màu theo mức, chữ, nút."""
    lam = Signal(object)                     # ViecPheu | ('buoc', số bước)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('khung_tq')
        self.lo = QVBoxLayout(self)
        self.lo.setContentsMargins(10, 8, 10, 8)
        self.lo.setSpacing(4)
        t = QLabel('Việc nên làm tiếp')
        t.setObjectName('tq_tieu_de')
        self.lo.addWidget(t)
        self.dong = []                           # [(QLabel, QPushButton | None)]

    def dat(self, viec: list, du_an=None) -> None:
        """viec: [pheu_tien_do.ViecPheu]; du_an: quy_trinh.KetQuaQuyTrinh - bước cấp dự án chưa xong thêm một dòng nhắc."""
        # các dòng nằm trong MỘT khung con: dựng lại = thay cả khung (deleteLater một widget). Trước 31/10/2026 lấy từng bố cục con ra
        # (takeAt) rồi deleteLater - Python cũng giữ / tự hủy đối tượng đó -> hủy hai lần, hỏng bộ nhớ, sập ngẫu nhiên lúc sau (mở dự
        # án vào Màn hình chính dựng lại khung này mỗi lần mở; kiểm tra giao diện bắt được)
        if getattr(self, 'than', None) is not None:
            self.lo.removeWidget(self.than)
            self.than.hide()
            self.than.deleteLater()
        self.than = QWidget()
        lo = QVBoxLayout(self.than)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(self.lo.spacing())
        self.lo.addWidget(self.than, 1)
        self.dong = []
        muc = []                                  # (chữ, mức, hành động, chữ nút)
        for v in viec:
            muc.append((v.chu, v.muc, v, 'Xem hộ' if v.loai == 'co' else 'Làm ngay →'))
        if du_an is not None:
            for b in BUOC_DU_AN:
                if du_an.buoc[b].trang_thai != 'xong':
                    muc.append((f'Cả dự án: {qt.TEN_NGAN[b].lower()} - {du_an.buoc[b].mo_ta.lower()}', 'nhac', ('buoc', b),
                                'Ghi ngày' if b in qt.MOC_BUOC else 'Mở'))
        if not muc:
            lb = QLabel('Không có việc tồn đọng.')
            lb.setObjectName('qt_viec')
            lb.setWordWrap(True)
            lo.addWidget(lb)
            self.dong.append((lb, None))
        for chu, m, hd, chu_nut in muc:
            h = QHBoxLayout()
            h.setSpacing(6)
            lb = QLabel(f'<span style="color:{MAU_MUC_VIEC[m]}">●</span> {chu}')
            lb.setObjectName('qt_viec')
            lb.setTextFormat(Qt.TextFormat.RichText)
            lb.setWordWrap(True)
            lb.setToolTip(TEN_MUC_VIEC[m])
            h.addWidget(lb, 1)
            nut = QPushButton(chu_nut)
            nut.setObjectName('nut_viec')
            nut.setCursor(Qt.CursorShape.PointingHandCursor)
            nut.clicked.connect(lambda _=False, hd=hd: self.lam.emit(hd))
            h.addWidget(nut)
            lo.addLayout(h)
            self.dong.append((lb, nut))
        if len(muc) > TOI_DA_VIEC_HIEN:                  # 1.0.94
            an = [(lb, nut) for lb, nut in self.dong[TOI_DA_VIEC_HIEN:]]
            for lb, nut in an:
                lb.setVisible(False)
                nut.setVisible(False)
            them = QPushButton(f'Xem thêm {len(an)} việc')
            them.setObjectName('nut_viec')
            them.setCursor(Qt.CursorShape.PointingHandCursor)
            them.setToolTip('Hiện / ẩn các việc còn lại (đã xếp theo mức ưu tiên)')

            def bat_tat(_=False, an=an, them=them):
                hien = not an[0][0].isVisible()
                for lb, nut in an:
                    lb.setVisible(hien)
                    nut.setVisible(hien)
                them.setText('Thu gọn' if hien else f'Xem thêm {len(an)} việc')
            them.clicked.connect(bat_tat)
            lo.addWidget(them, 0, Qt.AlignmentFlag.AlignRight)
        lo.addStretch(1)


class KhungTongQuanDuAn(QWidget):
    mo_ho = Signal(int)              # bấm "Lập PA" của một hộ
    mo_buoc = Signal(int)            # việc cấp dự án (bước 1-3 QĐ 18): ghi ngày / mở chỗ làm
    chay_lenh = Signal(str)          # nút "Làm ngay" của việc: khóa CuaSoChinh.lenh

    def __init__(self, lenh: dict | None = None, parent=None):
        super().__init__(parent)
        from .giao_dien import HangKpi, nut_lenh
        from PySide6.QtWidgets import QScrollArea
        self.setObjectName('tong_quan_du_an')
        dat_kieu_theo_tong(self, QSS_TONG_QUAN)
        # 30/10/2026: cả màn hình cuộn được - màn hình 1366 x 768 @125% không bóp nát khung việc / đồng hồ pháp lý
        ngoai = QVBoxLayout(self)
        ngoai.setContentsMargins(0, 0, 0, 0)
        self.cuon = QScrollArea()
        self.cuon.setObjectName('cuon_tong_quan')
        self.cuon.setWidgetResizable(True)
        self.cuon.setFrameShape(QFrame.Shape.NoFrame)
        self.cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ngoai.addWidget(self.cuon)
        noi_dung = QWidget()
        noi_dung.setObjectName('noi_dung_tong_quan')
        self.cuon.setWidget(noi_dung)
        lo = QVBoxLayout(noi_dung)
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
        dai.setVisible(False)                   # 31/10/2026: tên dự án / địa bàn đã ở tiêu đề cửa sổ - nhường chỗ cho bảng hộ
        self.dai_tong_thuat = dai
        # phễu tiến độ theo hộ (đại tu 30/10/2026)
        self.pheu = KhungPheu()
        self.pheu.mo_buoc.connect(self.mo_buoc.emit)
        self.pheu.mo_ds.connect(self.mo_danh_sach)
        self.pheu.doi_che_do.connect(self._doi_che_do)
        lo.addWidget(self.pheu)
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
            b.setMinimumHeight(CAO_THE_KHOI_TAO)
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
        self.viec = KhungViecTiep()
        self.viec.lam.connect(self._lam_viec)
        cot_phai = QWidget()
        cot_phai.setMinimumWidth(RONG_COT_PHAI[0])
        cot_phai.setMaximumWidth(RONG_COT_PHAI[1])
        cp = QVBoxLayout(cot_phai)
        cp.setContentsMargins(0, 0, 0, 0)
        cp.setSpacing(8)
        cp.addWidget(self.viec)
        phai = QFrame()
        phai.setObjectName('khung_tq')
        cp.addWidget(phai, 1)
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
        self.chia.addWidget(cot_phai)
        self.chia.setStretchFactor(0, TI_LE_CHIA[0])
        self.chia.setStretchFactor(1, TI_LE_CHIA[1])
        self.chia.setMinimumHeight(CAO_PHAN_DUOI_TOI_THIEU)
        lo.addWidget(self.chia, 1)
        self.so_lieu = None
        self.quy_trinh = None                   # quy_trinh.KetQuaQuyTrinh (việc cấp dự án, bước 1-3)
        self.ket_qua_pheu = None                # pheu_tien_do.KetQuaPheu
        self._nguon = None                      # (con, lap) để tính lại phễu khi đổi cách xét lần phương án
        self.hop_ds = []                        # cửa sổ danh sách hộ đang mở (giữ tham chiếu)

    def _lam_viec(self, hd) -> None:
        if isinstance(hd, tuple):               # ('buoc', b) - việc cấp dự án
            self.mo_buoc.emit(hd[1])
        elif self.ket_qua_pheu is None:         # dự án vừa đóng / phễu chưa tính: nút cũ còn trên màn hình - không làm gì
            return
        elif hd.loai == 'co' or not hd.lenh:
            ds = self.ket_qua_pheu.theo_co(hd.khoa) if hd.loai == 'co' else self.ket_qua_pheu.theo_giai_doan(hd.khoa)
            self.mo_danh_sach(hd.chu, ds)
        else:
            self.chay_lenh.emit(hd.lenh)

    def mo_danh_sach(self, tieu_de: str, ds: list):
        """Cửa sổ danh sách hộ của một giai đoạn / một cờ; bấm đúp mở phương án (mo_ho)."""
        h = HopHoPheu(tieu_de, ds, self.window())
        h.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        h.mo_ho.connect(self.mo_ho.emit)
        h.destroyed.connect(lambda _=None, h=h: self.hop_ds.remove(h) if h in self.hop_ds else None)
        self.hop_ds.append(h)
        h.show()
        return h

    def _doi_che_do(self, che_do: str) -> None:
        import sqlite3
        if self._nguon is None:
            return
        con, lap = self._nguon
        try:
            con.execute('SELECT 1')
        except sqlite3.ProgrammingError:                 # dự án đã đóng (kết nối cũ): không tính lại, giữ phễu đang hiện
            self._nguon = None
            return
        self._nap_pheu(con, lap, che_do)

    def _nap_pheu(self, con, lap, che_do: str = 'mo') -> None:
        from . import du_thao, quan_ly
        try:
            self.ket_qua_pheu = ph.tinh(con, lap, che_do)
            dot_ny = [(d['id'], d.get('ten') or f'Đợt {d["id"]}') for d in du_thao.ds_dot(con)] \
                if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'dot_du_thao'").fetchone() else []
            dot_tr = [(d.id, d.ten or f'Đợt {d.so}') for d in quan_ly.ds_dot(con)]
        except Exception:                               # noqa: BLE001 - phễu lỗi: vẫn hiện phần tổng quan còn lại
            self.ket_qua_pheu = None
        self.pheu.setVisible(self.ket_qua_pheu is not None)
        self.viec.setVisible(self.ket_qua_pheu is not None)
        if self.ket_qua_pheu is not None:
            self.pheu.dat(self.ket_qua_pheu, dot_ny, dot_tr, self.quy_trinh)
            self.viec.dat(ph.viec_tiep(self.ket_qua_pheu), self.quy_trinh)

    # ------------------------------------------------ nạp số liệu
    def nap(self, con, dong: list, ten: str = '', dia_ban: str = '', file: str = '', chu_dau_tu: str = '', hom_nay=None,
            lap: dict | None = None) -> dict:
        kq = tq.tinh(con, dong, hom_nay)
        self.so_lieu = kq
        try:
            self.quy_trinh = qt.tinh(con, dong, lap, hom_nay)
        except Exception:                               # noqa: BLE001 - việc cấp dự án lỗi: phễu vẫn hiện
            self.quy_trinh = None
        self._nguon = (con, lap)
        self._nap_pheu(con, lap, self.pheu.cb_lan.currentData() or 'mo')
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
            from .giao_dien import phong_so
            t.setFont(phong_so())                       # 1.0.51: số tiền phông số
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
