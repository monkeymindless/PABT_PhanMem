"""Công cụ trên bản đồ thửa đất (05/11/2026 - người dùng: đo đạc, nút la bàn / thu phóng như Google Earth, bấm thửa hiện thông tin phía dưới, gắn hộ vào ô thửa).

LaBan: la bàn vẽ bằng QPainter (vòng ngoài kéo để xoay bản đồ, chữ N về hướng Bắc lưới VN-2000, bốn mũi tên di chuyển). ThuocDo: đo đường / vùng / tọa độ trên KhungBanDo, bắt đỉnh thửa để
đo đúng góc thửa. KhungThongTinThua: dải thông tin dưới bản đồ. HopGanHo, HopSuaThua: hộp thoại. Tính toán ở do_dac (không Qt)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFormLayout, QGraphicsEllipseItem, QGraphicsPathItem,
                               QGraphicsSimpleTextItem, QGridLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import ban_do_cad, do_dac
from .giao_dien import TOKEN, qmau_theo_tong
from .lap_pa import LoiNhap, bo_dau
from .thong_bao import TEN_UD, chu_loi
from .tien import so_vn

CO_LA_BAN = 76
SNAP_PX = 9                      # bắt đỉnh thửa / đường trong bán kính này (điểm màn hình)
SO_DIEM_TOA_DO_GIU = 12


# ---------------------------------------------------------------- la bàn
class LaBan(QWidget):
    """Vòng ngoài: kéo để xoay; bấm chữ N hoặc nhấp đúp: về hướng Bắc. Bốn mũi tên giữa vòng: di chuyển bản đồ."""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.setFixedSize(CO_LA_BAN, CO_LA_BAN)
        self.setToolTip('La bàn: kéo vòng ngoài để xoay bản đồ, bấm chữ N về hướng Bắc (Bắc của lưới VN-2000). Bốn mũi tên: di chuyển bản đồ.')
        self.setMouseTracking(True)
        self._keo = None                 # góc lúc bắt đầu kéo
        self._da_keo = False

    def _vi_tri(self, p) -> tuple:
        """(khoảng cách tới tâm, góc từ đỉnh theo chiều kim đồng hồ - độ)."""
        c = self.rect().center()
        dx, dy = p.x() - c.x(), p.y() - c.y()
        return math.hypot(dx, dy), math.degrees(math.atan2(dx, -dy)) % 360

    def _mui_ten(self, p) -> tuple | None:
        """(dx, dy) của mũi tên tại điểm p, None nếu không trúng."""
        r, g = self._vi_tri(p)
        if r > CO_LA_BAN / 2 - 15 or r < 4:
            return None
        if g >= 315 or g < 45:
            return 0, -1
        if g < 135:
            return 1, 0
        if g < 225:
            return 0, 1
        return -1, 0

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.rect().center())
        r = CO_LA_BAN / 2 - 2
        nen = qmau_theo_tong(TOKEN['khung'])
        nen.setAlpha(235)
        chu = qmau_theo_tong(TOKEN['chu_phu'], 'chu')
        vach = qmau_theo_tong(TOKEN['vach'], 'vien')
        p.setPen(QPen(vach, 1))
        p.setBrush(QBrush(nen))
        p.drawEllipse(c, r, r)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, r - 13, r - 13)
        # bốn mũi tên
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(chu))
        for a in (0, 90, 180, 270):
            p.save()
            p.translate(c)
            p.rotate(a)
            p.drawPolygon(QPolygonF([QPointF(0, -(r - 17)), QPointF(5, -(r - 25)), QPointF(-5, -(r - 25))]))
            p.restore()
        # vòng ngoài: N và vạch xoay theo bản đồ
        goc = getattr(self.view, 'goc', 0.0)
        p.save()
        p.translate(c)
        p.rotate(goc)
        p.setPen(QPen(chu, 1.2))
        for a in range(0, 360, 90):
            if a:
                p.save()
                p.rotate(a)
                p.drawLine(QPointF(0, -r + 3), QPointF(0, -r + 8))
                p.restore()
        do = qmau_theo_tong(TOKEN['nguy_hiem'], 'chu')
        p.setPen(QPen(do))
        f = QFont('Segoe UI', 8)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(-8, -r, 16, 13), Qt.AlignmentFlag.AlignCenter, 'N')
        p.restore()
        p.end()

    def mousePressEvent(self, e):
        d = e.position().toPoint() if hasattr(e, 'position') else e.pos()
        m = self._mui_ten(d)
        if m is not None:
            self.view.dich_theo_o(*m)
            e.accept()
            return
        r, g = self._vi_tri(d)
        if r > CO_LA_BAN / 2 - 15:
            self._keo = (g, getattr(self.view, 'goc', 0.0))
            self._da_keo = False
        e.accept()

    def mouseMoveEvent(self, e):
        if self._keo is None:
            return
        d = e.position().toPoint() if hasattr(e, 'position') else e.pos()
        _r, g = self._vi_tri(d)
        delta = (g - self._keo[0] + 180) % 360 - 180
        if abs(delta) > 1.5:
            self._da_keo = True
        if self._da_keo:
            self.view.dat_goc(self._keo[1] + delta)
            self.update()

    def mouseReleaseEvent(self, e):
        if self._keo is not None and not self._da_keo:             # bấm vào vòng (không kéo): bấm trúng chữ N thì về Bắc
            d = e.position().toPoint() if hasattr(e, 'position') else e.pos()
            _r, g = self._vi_tri(d)
            if abs((g - getattr(self.view, 'goc', 0.0) + 180) % 360 - 180) <= 28:
                self.view.dat_goc(0.0)
                self.update()
        self._keo = None

    def mouseDoubleClickEvent(self, _e):
        self.view.dat_goc(0.0)
        self.update()


# ---------------------------------------------------------------- thước đo
class ThuocDo:
    """Đo trên KhungBanDo. Đơn vị cảnh = mét VN-2000 (y cảnh = -bắc). bao(chữ) nhận kết quả mỗi khi đổi. Hình QGraphics do thước giữ: trước khi cảnh bị xóa gọi quen_hinh(), sau đó ve_lai()."""
    TEN = {'duong': 'Đo đường', 'vung': 'Đo vùng', 'diem': 'Tọa độ'}

    def __init__(self, view, bao=None):
        self.view, self.bao = view, bao
        self.che_do = None
        self.diem = []                   # [(x, y)] tọa độ cảnh
        self.xong = False
        self._hinh = []
        self._ruoi = None

    def _vn2000(self) -> list:
        return [(x, -y) for x, y in self.diem]

    def ket_qua(self, kt: float) -> str:
        return do_dac.ket_qua_do(self.che_do or 'duong', self._vn2000(), kt) if self.diem else ''

    # ---- trạng thái
    def bat(self, che_do: str | None) -> None:
        """Bật kiểu đo (None: tắt, giữ kết quả đang hiện cho tới khi xóa)."""
        self.che_do = che_do
        if che_do is not None:
            self.xoa()
            self.che_do = che_do
        self.view.dat_con_tro_do(che_do is not None)
        self._bo_ruoi()

    def xoa(self) -> None:
        self.diem, self.xong = [], False
        self._bo_hinh()
        self._bao()

    def them(self, x: float, y: float) -> None:
        if self.che_do is None:
            return
        if self.xong:                    # phép đo trước đã kết thúc: bấm tiếp là đo mới
            self.diem, self.xong = [], False
        if self.che_do == 'diem' and len(self.diem) >= SO_DIEM_TOA_DO_GIU:
            self.diem.pop(0)
        if self.diem and abs(self.diem[-1][0] - x) < 1e-6 and abs(self.diem[-1][1] - y) < 1e-6:
            return
        self.diem.append((x, y))
        self.ve_lai()
        self._bao()

    def bo_diem_cuoi(self) -> bool:
        if not self.diem or self.xong:
            return False
        self.diem.pop()
        self.ve_lai()
        self._bao()
        return True

    def ket_thuc(self) -> bool:
        """Kết thúc đường / vùng đang đo (nhấp đúp, chuột phải, Enter)."""
        can = 3 if self.che_do == 'vung' else 2
        if self.che_do in ('duong', 'vung') and len(self.diem) >= can and not self.xong:
            self.xong = True
            self._bo_ruoi()
            self.ve_lai()
            self._bao()
            return True
        return False

    def _bao(self) -> None:
        if self.bao is not None:
            self.bao()

    # ---- hình trên cảnh
    def quen_hinh(self) -> None:
        """Cảnh sắp bị xóa cả loạt: quên tham chiếu (chạm vào hình đã hủy là sập)."""
        self._hinh, self._ruoi = [], None

    def _bo_hinh(self) -> None:
        for it in self._hinh:
            if it.scene() is not None:
                it.scene().removeItem(it)
        self._hinh = []
        self._bo_ruoi()

    def _bo_ruoi(self) -> None:
        if self._ruoi is not None and self._ruoi.scene() is not None:
            self._ruoi.scene().removeItem(self._ruoi)
        self._ruoi = None

    def _but(self, rong: float = 2.6) -> QPen:
        p = QPen(QColor(TOKEN['canh_bao']), rong)
        p.setCosmetic(True)
        p.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return p

    def _them(self, it, z: float = 40) -> None:
        it.setZValue(z)
        it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.view.scene().addItem(it)
        self._hinh.append(it)

    def _chu(self, x: float, y: float, chu: str, lech=(6, -18)) -> None:
        n = QGraphicsSimpleTextItem(chu)
        f = QFont('Segoe UI', 9)
        f.setBold(True)
        n.setFont(f)
        n.setBrush(QBrush(QColor(TOKEN['khung'])))
        n.setPen(QPen(QColor(TOKEN['chu']), 0.6))
        n.setFlag(QGraphicsSimpleTextItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        n.setPos(QPointF(x, y))
        n.setTransform(QTransform.fromTranslate(*lech))
        self._them(n, 42)

    def ve_lai(self) -> None:
        self._bo_hinh()
        if not self.diem or self.view.scene() is None:
            return
        if len(self.diem) >= 2 and self.che_do != 'diem':
            duong = QPainterPath(QPointF(*self.diem[0]))
            for p in self.diem[1:]:
                duong.lineTo(QPointF(*p))
            if self.che_do == 'vung' and (self.xong or len(self.diem) >= 3):
                duong.closeSubpath()
            it = QGraphicsPathItem(duong)
            it.setPen(self._but())
            if self.che_do == 'vung':
                c = QColor(TOKEN['canh_bao'])
                c.setAlpha(60)
                it.setBrush(QBrush(c))
            self._them(it)
        for i, (x, y) in enumerate(self.diem):
            v = QGraphicsEllipseItem(-4, -4, 8, 8)
            v.setPos(QPointF(x, y))
            v.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            v.setPen(QPen(QColor(TOKEN['khung']), 1.5))
            v.setBrush(QBrush(QColor(TOKEN['canh_bao'])))
            self._them(v, 41)
            if self.che_do == 'diem':
                self._chu(x, y, f'P{i + 1}  X {do_dac._so_m(-y)}  Y {do_dac._so_m(x)}')
        if self.che_do == 'diem' or len(self.diem) < 2:
            return
        ds = list(self.diem) + ([self.diem[0]] if self.che_do == 'vung' and (self.xong or len(self.diem) >= 3) else [])
        for i in range(len(ds) - 1):
            a, b = ds[i], ds[i + 1]
            self._chu((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, do_dac._so_m(math.hypot(b[0] - a[0], b[1] - a[1])), lech=(4, -8))

    def re_chuot(self, x: float, y: float) -> None:
        """Đường chun từ điểm cuối tới con trỏ, kèm chiều dài đoạn đang kéo ở thanh trạng thái (không đổi kết quả)."""
        if self.che_do not in ('duong', 'vung') or self.xong or not self.diem:
            self._bo_ruoi()
            return
        path = QPainterPath(QPointF(*self.diem[-1]))
        path.lineTo(QPointF(x, y))
        if self.che_do == 'vung' and len(self.diem) >= 2:
            path.lineTo(QPointF(*self.diem[0]))
        if self._ruoi is None:
            self._ruoi = QGraphicsPathItem(path)
            p = self._but(1.6)
            p.setStyle(Qt.PenStyle.DashLine)
            self._ruoi.setPen(p)
            self._ruoi.setZValue(40)
            self._ruoi.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene().addItem(self._ruoi)
        else:
            self._ruoi.setPath(path)


# ---------------------------------------------------------------- dải thông tin thửa
def _gon(chu: str, toi_da: int = 70) -> str:
    return chu if len(chu) <= toi_da else chu[:toi_da - 1] + '…'


CHU_THU_HOI = {'khop': 'khớp nhãn bản vẽ', 'ca_thua': 'cả thửa trong ranh', 'ngoai_ranh': 'ngoài ranh thu hồi', 'lech': 'LỆCH nhãn, theo hình học',
               'chi_hinh': 'theo hình học, chưa có nhãn', 'khong_ranh': ''}
CHU_DT = {'khop': 'khớp nhãn', 'lech': 'LỆCH nhãn', 'chua_co_nhan': 'chưa có nhãn'}


def chu_dt_thu_hoi(t) -> str:
    """Chữ DT thu hồi của thửa: bản vẽ (kèm trạng thái đối chiếu) và hồ sơ - hai con số khác nhau thì nêu cả hai, không chọn hộ người dùng."""
    ct = t.chi_tiet or {}
    doi = (ct.get('doi_chieu') or {}).get('thu_hoi', '')
    phan = []
    if t.dt_trong_ranh not in (None, ''):
        ghi = CHU_THU_HOI.get(doi, '')
        phan.append(f'{so_vn(t.dt_trong_ranh)} m²' + (f' ({ghi})' if ghi else ' (bản vẽ)'))
    if t.ma_ho is not None and t.dt_thu_hoi not in (None, ''):
        phan.append(f'hồ sơ {so_vn(t.dt_thu_hoi)} m²')
    return ' · '.join(phan) if phan else 'chưa xác định (bản vẽ không có ranh thu hồi)'


def chu_dt_thua(t) -> str:
    ct = t.chi_tiet or {}
    doi = (ct.get('doi_chieu') or {}).get('dt', '')
    chinh = t.dt_ban_ve if t.dt_ban_ve not in (None, '') else t.dt_hinh
    ra = f'{so_vn(chinh)} m²'
    if doi == 'lech':
        ra += f' (nhãn) · hình {so_vn(t.dt_hinh)} m² - LỆCH'
    elif t.dt_ban_ve in (None, ''):
        ra += ' (theo hình)'
    return ra


class KhungThongTinThua(QWidget):
    """Khung thông tin bên phải bản đồ: bấm thửa -> số tờ, số thửa, diện tích thửa, diện tích thu hồi, hộ, trạng thái, mốc ranh, ghi chú, tọa độ (chữ tự xuống dòng theo độ rộng bảng).
    gt[khóa]: QLabel giá trị (kiểm thử đọc chữ)."""
    MUC = (('loai_dat', 'Loại đất'), ('dt_thua', 'DT thửa'), ('dt_thu_hoi', 'DT thu hồi'), ('ho', 'Hộ'), ('trang_thai', 'Trạng thái'), ('doi_chieu', 'Đối chiếu'),
           ('moc', 'Mốc ranh'), ('ghi_chu', 'Ghi chú'), ('toa_do', 'Vị trí'))
    DAM = ('so_to', 'so_thua', 'dt_thua', 'dt_thu_hoi', 'ho')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('khung_tt_thua')
        self.gt = {}
        v0 = QVBoxLayout(self)
        v0.setContentsMargins(0, 0, 0, 0)
        v0.setSpacing(4)
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(2)

        def nhan(ten):
            lb = QLabel(ten + ':', self)
            lb.setProperty('vai', 'nhan')
            return lb

        def gia_tri(k):
            o = QLabel('-', self)
            o.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            o.setWordWrap(True)                          # hẹp thì xuống dòng, không ép bảng rộng ra
            sp = o.sizePolicy()
            sp.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
            o.setSizePolicy(sp)
            f = o.font()
            f.setBold(k in self.DAM)
            o.setFont(f)
            self.gt[k] = o
            return o
        g.addWidget(nhan('Tờ'), 0, 0)
        g.addWidget(gia_tri('so_to'), 0, 1)
        g.addWidget(nhan('Thửa'), 0, 2)
        g.addWidget(gia_tri('so_thua'), 0, 3)
        for h, (k, ten) in enumerate(self.MUC, start=1):
            lb = nhan(ten)
            lb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            g.addWidget(lb, h, 0)
            g.addWidget(gia_tri(k), h, 1, 1, 3)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)
        v0.addLayout(g)
        self.b_dinh_vi = QPushButton('Định vị')
        self.b_dinh_vi.setToolTip('Bay tới thửa đang chọn ở mức ảnh nét nhất, hiện tọa độ VN-2000 và GPS của tâm thửa')
        self.b_mo = QPushButton('Mở phương án')
        self.b_mo.setToolTip('Mở phương án của hộ (hoặc nhấp đúp vào ô thửa trên bản đồ)')
        self.b_gan = QPushButton('Gắn hộ…')
        self.b_gan.setToolTip('Thêm thửa này vào hồ sơ một hộ đã có, hoặc tạo hộ mới theo tên: bản đồ tô màu theo trạng thái của hộ')
        self.b_ho = QPushButton('Thửa của hộ')
        self.b_ho.setToolTip('Viền nổi mọi thửa của hộ này trên bản đồ')
        self.b_sua = QPushButton('Sửa số tờ, thửa…')
        self.b_sua.setToolTip('Sửa số tờ, số thửa, loại đất của ô thửa trên bản đồ khi bản vẽ đọc nhầm nhãn (không đổi hồ sơ hộ)')
        self.b_chep = QPushButton('Sao chép')
        self.b_chep.setToolTip('Sao chép thông tin thửa và tọa độ các đỉnh (VN-2000) vào bộ nhớ tạm')
        gn = QGridLayout()
        gn.setContentsMargins(0, 0, 0, 0)
        gn.setSpacing(4)
        for i, b in enumerate((self.b_dinh_vi, self.b_mo, self.b_gan, self.b_ho, self.b_sua, self.b_chep)):
            b.setAutoDefault(False)
            sp = b.sizePolicy()
            sp.setHorizontalPolicy(QSizePolicy.Policy.Ignored)   # hai cột chia đều bảng: chữ dài trên nút không ép bảng rộng ra (Qt5: chiếm tới 470 px)
            b.setSizePolicy(sp)
            gn.addWidget(b, i // 2, i % 2)
        v0.addLayout(gn)
        self.xoa()

    def _dat_nut(self, dinh_vi=False, mo=False, gan=False, ho=False, sua=False, chep=False) -> None:
        self.b_dinh_vi.setEnabled(dinh_vi)
        self.b_mo.setEnabled(mo)
        self.b_gan.setEnabled(gan)
        self.b_ho.setEnabled(ho)
        self.b_sua.setEnabled(sua)
        self.b_chep.setEnabled(chep)

    def xoa(self) -> None:
        for v in self.gt.values():
            v.setText('-')
            v.setToolTip('')
        self.gt['toa_do'].setText('Bấm một ô thửa để xem số tờ, số thửa, diện tích, diện tích thu hồi và hộ có đất.')
        self._dat_nut()

    def _dat(self, k: str, chu: str, toi_da: int = 240) -> None:
        self.gt[k].setText(_gon(chu or '-', toi_da))
        self.gt[k].setToolTip(chu if len(chu or '') > toi_da else '')

    def hien(self, t, trang_thai: str, toa_do: str, co_mo: bool = False, co_gan: bool = False, co_sua: bool = False) -> None:
        ct = t.chi_tiet or {}
        self._dat('so_to', str(t.so_to or '?'))
        self._dat('so_thua', str(t.so_thua))
        self._dat('loai_dat', t.loai_dat or '(chưa có nhãn)')
        self._dat('dt_thua', chu_dt_thua(t))
        self._dat('dt_thu_hoi', chu_dt_thu_hoi(t))
        self._dat('ho', f'{t.ho_ten} (mã {t.ma_ho})' if t.ma_ho is not None else 'Chưa gắn hộ')
        self._dat('trang_thai', trang_thai)
        ly_do = ct.get('ly_do') or []
        doi = ct.get('doi_chieu') or {}
        if ly_do:
            self._dat('doi_chieu', 'CẦN XEM LẠI: ' + '; '.join(ly_do))
        elif doi:
            self._dat('doi_chieu', 'DT ' + CHU_DT.get(doi.get('dt'), '') + (' · DT thu hồi ' + CHU_THU_HOI.get(doi.get('thu_hoi'), '') if CHU_THU_HOI.get(doi.get('thu_hoi')) else ''))
        else:
            self._dat('doi_chieu', 'Nhập từ bản vẽ, chưa có đối chiếu nhãn')
        self._dat('moc', ', '.join(ct.get('moc') or []) or '-')
        self._dat('toa_do', toa_do.replace('  ·  ', '\n'))
        self._dat('ghi_chu', '; '.join(ct.get('ghi_chu') or []) or '-')
        self._dat_nut(dinh_vi=True, mo=co_mo and t.ma_ho is not None, gan=co_gan, ho=t.ma_ho is not None, sua=co_sua, chep=True)
        self.b_gan.setText('Đổi hộ…' if t.ma_ho is not None else 'Gắn hộ…')

    def hien_doi_tuong(self, ten: str, chu: str, toa_do: str = '') -> None:
        """Bấm mốc ranh, ghi chú, đường, số thửa chưa khép kín: các ô thửa để trống, chữ đối tượng ở ô Ghi chú / Vị trí."""
        self.xoa()
        self._dat('toa_do', (toa_do or '-').replace('  ·  ', '\n'))
        self._dat('ghi_chu', f'{ten}: {chu}')


def chu_sao_chep(t, kt: float) -> str:
    """Thông tin thửa + tọa độ các đỉnh (X = Bắc, Y = Đông) để dán vào Word / Excel, đối chiếu thực địa."""
    dong = [f'Thửa {t.so_thua} tờ {t.so_to}' + (f' - {t.loai_dat}' if t.loai_dat else ''), f'DT thửa: {chu_dt_thua(t)}', f'DT thu hồi: {chu_dt_thu_hoi(t)}']
    if t.ma_ho is not None:
        dong.append(f'Hộ: {t.ho_ten}')
    moc = (t.chi_tiet or {}).get('moc') or []
    if moc:
        dong.append('Mốc ranh: ' + ', '.join(moc))
    dong.append(f'Tọa độ các đỉnh (VN-2000, kinh tuyến trục {kt}):')
    for i, (x, y) in enumerate(t.toa_do, start=1):
        dong.append(f'{i}\tX = {do_dac._so_m(y, 3)}\tY = {do_dac._so_m(x, 3)}')
    return '\n'.join(dong)


# ---------------------------------------------------------------- gắn hộ vào thửa
class HopGanHo(QDialog):
    """Chọn hộ cho một ô thửa: hộ đã có (thêm thửa vào hồ sơ hộ) hoặc hộ mới theo tên. Thửa đang thuộc hộ khác: chuyển sang hộ được chọn (ho_so.chuyen_thua). Trả True ở gan() khi đã ghi."""
    im_lang = False

    def __init__(self, con, t, parent=None):
        super().__init__(parent)
        self.con, self.t = con, t
        self.setWindowTitle(f'Gắn hộ vào thửa {t.so_thua} tờ {t.so_to}')
        self.resize(520, 460)
        self.lb = QLabel(f'Thửa {t.so_thua} tờ {t.so_to} · {t.loai_dat or "chưa có loại đất"} · DT thửa {chu_dt_thua(t)} · DT thu hồi {chu_dt_thu_hoi(t)}')
        self.lb.setWordWrap(True)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Lọc theo họ tên, mã hộ, CCCD…')
        self.o_tim.textChanged.connect(lambda _: self.nap())
        self.ds = QListWidget()
        self.ds.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ds.itemDoubleClicked.connect(lambda _it: self._dong_y())
        self.o_moi = QLineEdit()
        self.o_moi.setPlaceholderText('Họ và tên hộ mới (bỏ trống nếu chọn hộ trong danh sách)')
        hop = QDialogButtonBox()
        self.b_gan = hop.addButton('Gắn vào thửa', QDialogButtonBox.ButtonRole.AcceptRole)
        hop.addButton('Hủy', QDialogButtonBox.ButtonRole.RejectRole)
        hop.accepted.connect(self._dong_y)
        hop.rejected.connect(self.reject)
        v = QVBoxLayout(self)
        v.addWidget(self.lb)
        v.addWidget(self.o_tim)
        v.addWidget(self.ds, 1)
        f = QFormLayout()
        f.addRow('Hoặc hộ mới:', self.o_moi)
        v.addLayout(f)
        v.addWidget(hop)
        self._ho = [(r['ma_ho'], r['ho_ten'] or '', r['so_cccd'] or '', r['dia_chi'] or '') for r in
                    con.execute('SELECT ma_ho, ho_ten, so_cccd, dia_chi FROM ho ORDER BY thu_tu, ma_ho')]
        self.nap()

    def nap(self) -> None:
        q = bo_dau(self.o_tim.text().strip())
        self.ds.clear()
        for ma, ten, cccd, dc in self._ho:
            chu = f'{ten} (mã {ma})' + (f' - {dc}' if dc else '')
            if q and q not in bo_dau(f'{ten} {ma} {cccd} {dc}'):
                continue
            it = QListWidgetItem(chu)
            it.setData(Qt.ItemDataRole.UserRole, ma)
            self.ds.addItem(it)

    def _bao(self, chu: str) -> None:
        if self.im_lang:
            self.lb.setText(chu)
        else:
            QMessageBox.warning(self, TEN_UD, chu)

    def _dong_y(self) -> None:
        it = self.ds.currentItem()
        if self.gan(it.data(Qt.ItemDataRole.UserRole) if it is not None and not self.o_moi.text().strip() else None, self.o_moi.text()):
            self.accept()

    def gan(self, ma_ho=None, ho_ten: str = '') -> bool:
        try:
            gan_ho_vao_thua(self.con, self.t, ma_ho, ho_ten)
        except (LoiNhap, ValueError) as e:
            self._bao(str(e))
            return False
        except Exception as e:                           # noqa: BLE001 - file chỉ đọc / khóa
            self._bao(chu_loi('Không gắn được hộ vào thửa', e))
            return False
        return True


def _so_ghi(v) -> str:
    """Số TEXT trong CSDL ('1159.6') -> chữ kiểu Việt Nam để qua lại ho_so.chuan_hoa_thua (doc_so đọc 1.159 là một nghìn)."""
    return '' if v in (None, '') else str(v).replace('.', ',')


def gan_ho_vao_thua(con, t, ma_ho=None, ho_ten: str = '') -> int:
    """Gắn hộ vào ô thửa t: ma_ho (hộ đã có) hoặc ho_ten (tạo hộ mới). Thửa đang thuộc hộ khác: chuyển sang. DT thu hồi lấy theo bản vẽ, thửa ngoài ranh ghi 0. Trả mã hộ."""
    from . import ho_so
    ten = ' '.join(str(ho_ten or '').split())
    if ma_ho is None and not ten:
        raise LoiNhap('Chọn một hộ trong danh sách hoặc nhập họ tên hộ mới.')
    cm = ban_do_cad.chi_muc_thua(con).get((ban_do_cad._khoa(t.so_to), ban_do_cad._khoa(t.so_thua)))
    dong = dict(so_to=t.so_to, so_thua=t.so_thua, loai_dat=t.loai_dat, dt_thu_hoi=_so_ghi(t.dt_trong_ranh),
                dt_nguyen_thua=_so_ghi(t.dt_ban_ve if t.dt_ban_ve not in (None, '') else t.dt_hinh))
    if ma_ho is None:
        if cm is not None:
            ma_moi = ho_so.luu_ho(con, None, dict(ho_ten=ten), [])
            ho_so.chuyen_thua(con, cm[0], ma_moi)
            return ma_moi
        return ho_so.luu_ho(con, None, dict(ho_ten=ten), [dong])
    if cm is not None:
        if cm[1] == ma_ho:
            raise LoiNhap('Thửa đã thuộc hộ này.')
        ho_so.chuyen_thua(con, cm[0], ma_ho)
        return ma_ho
    ho_so.them_thua(con, ma_ho, dong)
    return ma_ho


# ---------------------------------------------------------------- sửa số tờ, số thửa
class HopSuaThua(QDialog):
    """Sửa số tờ / số thửa / loại đất của ô thửa trên bản đồ. gia_tri(): dict sau khi Đồng ý."""

    def __init__(self, t, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Sửa thửa {t.so_thua} tờ {t.so_to} trên bản đồ')
        self.o_to, self.o_thua, self.o_loai = QLineEdit(str(t.so_to)), QLineEdit(str(t.so_thua)), QLineEdit(str(t.loai_dat or ''))
        f = QFormLayout(self)
        f.addRow('Số tờ:', self.o_to)
        f.addRow('Số thửa:', self.o_thua)
        f.addRow('Loại đất:', self.o_loai)
        lb = QLabel('Chỉ sửa trên bản đồ, để khớp đúng hồ sơ. Muốn đổi hồ sơ hộ: mở hồ sơ hộ.')
        lb.setProperty('vai', 'nhan')
        lb.setWordWrap(True)
        f.addRow(lb)
        hop = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        hop.accepted.connect(self.accept)
        hop.rejected.connect(self.reject)
        f.addRow(hop)

    def gia_tri(self) -> dict:
        return dict(so_to=self.o_to.text().strip(), so_thua=self.o_thua.text().strip(), loai_dat=self.o_loai.text().strip().upper())

