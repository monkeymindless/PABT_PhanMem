"""Hộp "Chỉnh cột" khi nhập danh sách hộ / thửa từ file (Excel, PDF, ảnh scan): chọn bảng (sheet), dòng bắt đầu dữ liệu và cột nào là họ
tên, địa chỉ, tờ, thửa, diện tích... bằng tay khi phần mềm không tự nhận ra (hoặc nhận chưa đúng). Xem trước bảng gốc và kết quả (số hộ,
số thửa) ngay khi đổi. Cột file không có thì để "(không có)" - phần mềm bỏ qua."""
from __future__ import annotations
from .giao_dien import mau_o_theo_tong  # noqa: E402  (màu ô đổi theo tông nền)
from .giao_dien import mau_theo_tong  # noqa: E402  (màu rich text theo tông nền)

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import nhap_tho
from .thong_bao import TEN_UD

TRUONG = [('ho_ten', 'Họ và tên'), ('dia_chi', 'Địa chỉ'), ('so_cccd', 'Số CCCD'), ('ngay_cap', 'Ngày cấp'), ('noi_cap', 'Nơi cấp'),
          ('dien_thoai', 'Số điện thoại'), ('so_to', 'Số tờ bản đồ'), ('so_thua', 'Số thửa đất'), ('to_thua', 'Tờ / Thửa (chung một cột)'),
          ('dt_thu_hoi', 'Diện tích thu hồi (m²)'), ('dt_ban_do', 'Diện tích bản đồ (m²)'), ('loai_dat', 'Loại đất'),
          ('vi_tri', 'Vị trí đất'), ('nhan_khau', 'Nhân khẩu'), ('nguon_goc', 'Nguồn gốc'), ('ghi_chu', 'Ghi chú'),
          ('stt', 'STT (để gộp dòng gãy)')]
SO_DONG_XEM = 40
SO_COT_XEM = 40
MAU_DU_LIEU = mau_o_theo_tong(globals(), MAU_DU_LIEU='#EEF6FF')[0]
MAU_CHON = mau_o_theo_tong(globals(), MAU_CHON='#FFF3C4')[0]


class HopGhepCot(QDialog):
    im_lang = False                 # True: kiểm thử, không hiện hộp báo

    def __init__(self, parent=None, ten_file: str = '', nguons: list | None = None, bo_cot=None, ly_do: str = ''):
        super().__init__(parent)
        self.setWindowTitle('Chỉnh cột nhập danh sách hộ, thửa')
        self.resize(1180, 760)
        self.nguons = list(nguons or [])
        self.ket_qua = None                      # KetQuaDoc của cách ghép hiện tại
        self._dang_nap = False
        lo = QVBoxLayout(self)
        gt = QLabel((f'<b>{ten_file}</b><br>' if ten_file else '') + (ly_do + '<br>' if ly_do else '') +
                    'Chọn bảng, dòng bắt đầu dữ liệu và cột tương ứng của từng thông tin. Cột file không có thì để "(không có)". '
                    'Cần ít nhất cột Họ và tên, hoặc cột Số tờ / Số thửa / Diện tích.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        h = QHBoxLayout()
        h.addWidget(QLabel('Bảng (sheet / trang):'))
        self.cb_nguon = QComboBox()
        for n in self.nguons:
            self.cb_nguon.addItem(f'{n.ten} ({len(n.luoi)} dòng)', n.ten)
        h.addWidget(self.cb_nguon, 1)
        h.addWidget(QLabel('Dữ liệu bắt đầu từ dòng:'))
        self.o_dong = QSpinBox()
        self.o_dong.setRange(1, 100000)
        self.o_dong.setToolTip('Dòng đầu tiên của danh sách (dưới dòng tiêu đề cột). 1 = file không có dòng tiêu đề.')
        h.addWidget(self.o_dong)
        self.b_tu_dong = QPushButton('Nhận cột tự động lại')
        self.b_tu_dong.setToolTip('Bỏ cách ghép đang chọn, để phần mềm tự dò lại bảng này')
        h.addWidget(self.b_tu_dong)
        lo.addLayout(h)
        self.bang = QTableWidget(0, 0)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        lo.addWidget(self.bang, 1)
        nhom = QGroupBox('Cột nào là gì')
        g = QGridLayout(nhom)
        self.cb = {}
        for i, (k, ten) in enumerate(TRUONG):
            o = QComboBox()
            o.setMinimumWidth(190)
            o.setProperty('truong', k)
            self.cb[k] = o
            g.addWidget(QLabel(ten + ':'), i // 3, (i % 3) * 2)
            g.addWidget(o, i // 3, (i % 3) * 2 + 1)
            o.currentIndexChanged.connect(self._doi)
        lo.addWidget(nhom)
        self.lb_kq = QLabel('')
        self.lb_kq.setWordWrap(True)
        lo.addWidget(self.lb_kq)
        nut = QHBoxLayout()
        self.b_huy = QPushButton('Hủy')
        self.b_dong_y = QPushButton('Dùng cách ghép này')
        self.b_dong_y.setDefault(True)
        nut.addStretch(1)
        nut.addWidget(self.b_huy)
        nut.addWidget(self.b_dong_y)
        lo.addLayout(nut)
        self.b_huy.clicked.connect(self.reject)
        self.b_dong_y.clicked.connect(self.dong_y)
        self.b_tu_dong.clicked.connect(self.nhan_tu_dong)
        self.cb_nguon.currentIndexChanged.connect(lambda _: self._chon_nguon(None))
        self.o_dong.valueChanged.connect(lambda _: self._doi())
        if self.nguons:
            ten = bo_cot.sheet if bo_cot is not None and any(n.ten == bo_cot.sheet for n in self.nguons) else self.nguons[0].ten
            self.cb_nguon.blockSignals(True)
            self.cb_nguon.setCurrentIndex(max(0, self.cb_nguon.findData(ten)))
            self.cb_nguon.blockSignals(False)
            self._chon_nguon(bo_cot)

    # ------------------------------------------------ nguồn đang chọn
    @property
    def nguon(self):
        return next((n for n in self.nguons if n.ten == self.cb_nguon.currentData()), None)

    def _chon_nguon(self, bo_cot) -> None:
        n = self.nguon
        if n is None:
            return
        if bo_cot is None:
            ung = nhap_tho.ung_vien(n, toi_da=1)
            bo_cot = ung[0] if ung else None
            if bo_cot is not None:
                nhap_tho._bo_sung_theo_noi_dung(n, bo_cot)
            elif len(n.luoi) >= 3:
                bo_cot = nhap_tho._khong_tieu_de(n)
        self._dang_nap = True
        try:
            self.o_dong.setMaximum(max(1, len(n.luoi)))
            self.o_dong.setValue((bo_cot.dong_tieu_de[-1] + 1) if bo_cot is not None else 1)
            self._lap_nhan_cot(n)
            for k, o in self.cb.items():
                j = bo_cot.cot.get(k) if bo_cot is not None else None
                o.setCurrentIndex((j + 1) if j is not None and j < min(n.rong, 200) else 0)
        finally:
            self._dang_nap = False
        self._ve_bang()
        self._tinh()

    def _lap_nhan_cot(self, n) -> None:
        dau = max(0, self.o_dong.value() - 2)
        for o in self.cb.values():
            o.blockSignals(True)
            o.clear()
            o.addItem('(không có)')
            for j in range(min(n.rong, 200)):
                mau = ''
                for r in n.luoi[dau:dau + 3]:
                    if j < len(r) and r[j] is not None and str(r[j]).strip():
                        mau = ' '.join(str(r[j]).split())[:26]
                        break
                o.addItem(f'Cột {nhap_tho._ten_cot(j)}' + (f': {mau}' if mau else ''))
            o.blockSignals(False)

    def _ve_bang(self) -> None:
        n = self.nguon
        if n is None:
            return
        cot_hien = min(n.rong, SO_COT_XEM)
        dong_hien = min(len(n.luoi), SO_DONG_XEM)
        self.bang.clear()
        self.bang.setRowCount(dong_hien)
        self.bang.setColumnCount(cot_hien)
        ten = {j: k for k, o in self.cb.items() for j in [o.currentIndex() - 1] if j >= 0}
        nhan = dict(TRUONG)
        self.bang.setHorizontalHeaderLabels([nhap_tho._ten_cot(j) + (f'\n{nhan[ten[j]]}' if j in ten else '') for j in range(cot_hien)])
        self.bang.setVerticalHeaderLabels([str(i + 1) for i in range(dong_hien)])
        dau = self.o_dong.value()
        for i in range(dong_hien):
            for j in range(cot_hien):
                v = n.luoi[i][j] if j < len(n.luoi[i]) else None
                it = QTableWidgetItem('' if v is None else ' '.join(str(v).split())[:40])
                if i + 1 >= dau:
                    it.setBackground(QBrush(MAU_DU_LIEU))
                if j in ten:
                    it.setBackground(QBrush(MAU_CHON if i + 1 < dau else QColor('#DFF0D8')))
                self.bang.setItem(i, j, it)
        self.bang.resizeColumnsToContents()
        for j in range(cot_hien):
            self.bang.setColumnWidth(j, min(self.bang.columnWidth(j), 220))

    # ------------------------------------------------ ghép cột
    def bo_cot(self):
        """BoCot theo các ô chọn hiện tại (thu_cong = True)."""
        n = self.nguon
        if n is None:
            return nhap_tho.BoCot('', [0], {}, {}, 0, [], set(), True)
        cot = {k: o.currentIndex() - 1 for k, o in self.cb.items() if o.currentIndex() > 0}
        dong = self.o_dong.value()

        def tieu(j):
            if dong >= 2 and j < len(n.luoi[dong - 2]):
                return ' '.join(str(n.luoi[dong - 2][j] or '').split()) or f'cột {nhap_tho._ten_cot(j)}'
            return f'cột {nhap_tho._ten_cot(j)}'
        return nhap_tho.BoCot(n.ten, [dong - 1], cot, {k: tieu(j) for k, j in cot.items()}, 0, [''] * n.rong, set(), True)

    def _doi(self) -> None:
        if self._dang_nap:
            return
        self._ve_bang()
        self._tinh()

    def _tinh(self) -> None:
        bo = self.bo_cot()
        if not bo.cot:
            self.ket_qua = None
            self.lb_kq.setText('Chưa chọn cột nào.')
            return
        kq = nhap_tho.doc_nguon(self.nguons, bo)
        self.ket_qua = kq
        if kq.ho:
            self.lb_kq.setText(f'Đọc được <b>{len(kq.ho)} hộ, {len(kq.thua)} thửa</b>; {len(kq.canh_bao)} điểm cần xem lại.')
        else:
            self.lb_kq.setText(f'<span style="color:{mau_theo_tong("#B83A3A", "chu")}">' + ' '.join(kq.loi[:1]) + '</span>')

    def nhan_tu_dong(self) -> None:
        self._chon_nguon(None)

    def dat_cot(self, truong: str, j: int | None) -> None:
        """Chọn cột j (0-based; None = không có) cho trường (kiểm thử / mã gọi)."""
        self.cb[truong].setCurrentIndex(0 if j is None else j + 1)

    def dong_y(self) -> None:
        if self.ket_qua is None or not self.ket_qua.ho:
            ly_do = ' '.join(self.ket_qua.loi[:1]) if self.ket_qua is not None else 'Chưa chọn cột nào.'
            if not self.im_lang:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, TEN_UD, 'Cách ghép này chưa đọc được hộ nào: ' + ly_do)
            return
        self.accept()
