"""Tìm nhanh Ctrl+K (bảng lệnh kiểu "command palette", người dùng 20/10/2026): một ô gõ - tìm KHÔNG DẤU theo số CCCD, mã hộ,
họ tên, tờ/thửa ("12/45") và tên chức năng (QAction trong CuaSoChinh.lenh + chữ ngắn NHAN_MENU). Danh sách phẳng; Enter = mở
hồ sơ hộ hoặc chạy lệnh. Hộp chỉ CHỌN (ket_qua) - cửa sổ chính thực hiện sau khi hộp đóng (CuaSoChinh.thuc_hien_tim_nhanh):
lệnh chạy qua QAction.trigger() nên lệnh đang tắt (chưa mở dự án / chỉ xem) không chạy được từ đây."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from .lap_pa import bo_dau

TOI_DA = 200                       # số dòng hiện tối đa (dự án 5.000 hộ: gõ một chữ không dựng 5.000 dòng)
MAU_TAT = QColor('#94A3B8')        # lệnh đang tắt: chữ xám, không chọn được
LOAI_HO, LOAI_LENH = 'ho', 'lenh'
TU_BO_QUA = ('Tìm nhanh…',)        # không liệt kê chính lệnh này


def _chu_lenh(ten: str) -> str:
    return ten.replace('&&', '&').replace('…', '').strip()


GAN_DAY_TOI_DA = 5                 # 1.0.95: số lệnh dùng gần đây đứng đầu khi chưa gõ
TIEN_TO = {'>': LOAI_LENH, '@': LOAI_HO}   # 1.0.95: gõ "> ..." chỉ tìm lệnh, "@ ..." chỉ tìm hộ


def ghi_gan_day(cua_so, ten: str) -> None:
    """Nhớ lệnh vừa chạy từ Tìm nhanh (mới nhất trước, trong phiên làm việc)."""
    ds = [t for t in getattr(cua_so, '_lenh_gan_day', []) if t != ten]
    cua_so._lenh_gan_day = [ten, *ds][:GAN_DAY_TOI_DA]


def ly_do_tat(cua_so, ten: str) -> str:
    """Vì sao lệnh đang tắt - nói rõ thay vì chỉ làm mờ (trước đây: "Lệnh đang tắt (chưa mở dự án hoặc đang chỉ xem)")."""
    from .lenh import LENH_CAN_DU_AN
    con = getattr(cua_so, 'con', None)
    if con is None and ten in LENH_CAN_DU_AN:
        return 'Mở hoặc tạo dự án trước'
    if con is not None:
        try:
            from . import phan_quyen
            vt = phan_quyen.vai_tro_cua(con)
            if vt is not None and ten in phan_quyen.lenh_bi_tat(vt, [ten]):
                return f'Vai trò "{phan_quyen.ten_vai_tro(vt)}" không có quyền dùng lệnh này'
        except Exception:                               # noqa: BLE001 - không đọc được vai trò: lý do chung
            pass
        if getattr(cua_so, 'chi_doc', False):
            return 'Dự án đang mở chỉ xem'
    return 'Lệnh đang tắt ở trạng thái hiện tại'


class Muc:
    """Một dòng của danh sách: hộ (khoa = mã hộ) hoặc lệnh (khoa = tên lệnh trong CuaSoChinh.lenh)."""
    __slots__ = ('loai', 'khoa', 'chu', 'phu', 'tim', 'tu', 'bat', 'ten', 'ly_do')

    def __init__(self, loai, khoa, chu, phu, tim, bat=True, ly_do=''):
        self.loai, self.khoa, self.chu, self.phu, self.bat, self.ly_do = loai, khoa, chu, phu, bat, ly_do
        self.tim = bo_dau(f'{chu} {phu} {tim}').lower()
        self.ten = ' ' + ' '.join(bo_dau(chu).lower().replace('.', ' ').split()) + ' '      # tên / nhãn: so trọn cụm theo từ
        self.tu = set(self.tim.split())

    def diem(self, tu_khoa: list) -> int | None:
        """None = không khớp (mọi từ gõ phải có trong chuỗi tìm); số nhỏ = đứng trước: 0 tên / nhãn chứa TRỌN cụm chữ gõ theo từ
        ("ho thu 1" khớp "Hộ thử 1", không khớp "Hộ thử 10"), 1 khớp trọn một từ có chữ số (mã hộ, CCCD, tờ/thửa), 2 tên bắt đầu
        bằng chữ gõ, 3 chỉ chứa chữ gõ (vd. chữ số trong địa chỉ "Ấp 1")."""
        if not all(t in self.tim for t in tu_khoa):
            return None
        if not tu_khoa:
            return 3
        if f' {" ".join(tu_khoa)} ' in self.ten:
            return 0
        if any(t in self.tu for t in tu_khoa if any(c.isdigit() for c in t)):
            return 1
        return 2 if self.ten.startswith(' ' + tu_khoa[0]) else 3


def ds_muc(cua_so) -> list:
    """Mọi hộ của dự án đang mở + mọi lệnh của cửa sổ chính (NHAN_MENU làm chữ chính, tên đầy đủ làm chữ phụ)."""
    from .lenh import NHAN_MENU
    kq = []
    con = getattr(cua_so, 'con', None)
    if con is not None:
        cccd = {r[0]: r[1] or '' for r in con.execute('SELECT ma_ho, so_cccd FROM ho')}
        for d in getattr(cua_so.mo_hinh, 'dong', []):
            o = d['o']
            ma = d['ma_ho']
            phu = ' · '.join(x for x in (f'Mã {ma}', f'CCCD {cccd[ma]}' if cccd.get(ma) else '', str(o[2] or '')) if x)
            kq.append(Muc(LOAI_HO, ma, f'{o[0]}. {o[1]}', phu, f'{ma} {d.get("tim", "")}'))
    for ten, a in cua_so.lenh.items():
        if ten in TU_BO_QUA:
            continue
        nhan = _chu_lenh(NHAN_MENU.get(ten, ten))
        day = _chu_lenh(ten)
        phim = a.shortcut().toString()
        bat = a.isEnabled()
        ly_do = '' if bat else ly_do_tat(cua_so, ten)
        phu = ' · '.join(x for x in ('Chức năng', day if day != nhan else '', phim, f'tắt: {ly_do}' if ly_do else '') if x)
        kq.append(Muc(LOAI_LENH, ten, nhan, phu, a.toolTip() or '', bat, ly_do))
    return kq


class HopTimKiemNhanh(QDialog):
    """Ô gõ + danh sách phẳng. Enter / bấm đúp = chọn (ket_qua() -> ('ho', mã hộ) | ('lenh', tên lệnh) | None)."""

    def __init__(self, cua_so, im_lang: bool = False):
        super().__init__(cua_so)
        self.im_lang = im_lang
        self.setWindowTitle('Tìm nhanh (Ctrl+K)')
        self.resize(720, 460)
        self.muc = ds_muc(cua_so)
        self.gan_day = list(getattr(cua_so, '_lenh_gan_day', []))
        self._chon = None
        self.o = QLineEdit()
        self.o.setPlaceholderText('Gõ CCCD, mã hộ, họ tên, tờ/thửa (12/45) hoặc tên chức năng - không cần dấu. "> " chỉ lệnh, "@ " chỉ hộ')
        self.o.setClearButtonEnabled(True)
        self.o.setObjectName('o_tim_nhanh')
        self.ds = QListWidget()
        self.ds.setObjectName('ds_tim_nhanh')
        self.ds.setUniformItemSizes(True)
        self.lb = QLabel('')
        self.lb.setProperty('vai', 'nhan')
        lo = QVBoxLayout(self)
        lo.addWidget(self.o)
        lo.addWidget(self.ds, 1)
        lo.addWidget(self.lb)
        self.o.textChanged.connect(self.loc)
        self.o.returnPressed.connect(self.chap_nhan)
        self.ds.itemActivated.connect(lambda *_: self.chap_nhan())
        self.o.installEventFilter(self)
        self.loc('')

    # ------------------------------------------------------------------ lọc
    def loc(self, chu: str = None):
        chu = self.o.text() if chu is None else chu
        chu_gon = chu.lstrip()
        chi_loai = TIEN_TO.get(chu_gon[:1])
        if chi_loai is not None:
            chu = chu_gon[1:]
        tu_khoa = bo_dau(chu).lower().split()
        co = []
        for i, m in enumerate(self.muc):
            if chi_loai is not None and m.loai != chi_loai:
                continue
            if not tu_khoa and m.loai == LOAI_HO and chi_loai is None:   # chưa gõ: chỉ liệt kê chức năng
                continue
            d = m.diem(tu_khoa)
            if d is not None:
                if not tu_khoa and m.loai == LOAI_LENH and m.khoa in self.gan_day:
                    d = -GAN_DAY_TOI_DA + self.gan_day.index(m.khoa)      # lệnh vừa dùng đứng đầu (mới nhất trước)
                co.append((d, 0 if m.bat else 1, i, m))
        co.sort(key=lambda x: x[:3])
        self.ds.clear()
        for _d, _t, _i, m in co[:TOI_DA]:
            it = QListWidgetItem(f'{m.chu}    —    {m.phu}' if m.phu else m.chu)
            it.setData(Qt.ItemDataRole.UserRole, (m.loai, m.khoa))
            if not m.bat:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsSelectable)
                it.setForeground(MAU_TAT)
                it.setToolTip(m.ly_do or 'Lệnh đang tắt')
            self.ds.addItem(it)
        for r in range(self.ds.count()):               # chọn sẵn dòng bật đầu tiên: Enter chạy luôn
            if self.ds.item(r).flags() & Qt.ItemFlag.ItemIsEnabled:
                self.ds.setCurrentRow(r)
                break
        n = len(co)
        self.lb.setText(f'{n} kết quả' + (f' (hiện {TOI_DA} đầu tiên - gõ thêm để thu hẹp)' if n > TOI_DA else '')
                        + ' · Enter: mở / chạy · ↑↓: chọn · Esc: đóng')

    def eventFilter(self, o, e):                       # ↑ ↓ PgUp PgDn ở ô gõ: di chuyển trong danh sách
        from PySide6.QtCore import QEvent
        if o is self.o and e.type() == QEvent.Type.KeyPress and e.key() in (
                Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            from PySide6.QtWidgets import QApplication
            QApplication.sendEvent(self.ds, e)
            return True
        return super().eventFilter(o, e)

    # ------------------------------------------------------------------ chọn
    def dong_hien(self) -> list:
        return [self.ds.item(r).data(Qt.ItemDataRole.UserRole) for r in range(self.ds.count())]

    def chap_nhan(self):
        it = self.ds.currentItem()
        if it is None or not (it.flags() & Qt.ItemFlag.ItemIsEnabled):
            return
        self._chon = tuple(it.data(Qt.ItemDataRole.UserRole))
        self.accept()

    def ket_qua(self):
        return self._chon
