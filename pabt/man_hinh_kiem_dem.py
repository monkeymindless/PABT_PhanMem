"""Hộp "Phiếu kiểm đếm thực địa" (0.9.87, menu Công cụ): xuất phiếu HTML dùng trên điện thoại, nhập kết quả .json vào phương án
hộ, gắn ảnh hiện trạng; bảng số dòng đã ghi / số ảnh mỗi hộ (bấm đúp: mở ảnh đầu tiên của hộ). Logic ở phieu_kiem_dem."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import phieu_kiem_dem as pk
from .lap_pa import LoiNhap


class HopKiemDem(QDialog):
    def __init__(self, cha, con, file_du_an=None, dm=None, chi_doc: bool = False, im_lang: bool = False):
        super().__init__(cha)
        self.con, self.dm, self.chi_doc, self.im_lang = con, dm, chi_doc, im_lang
        self.thu_muc = Path(file_du_an).parent if file_du_an else Path.home()
        self.da_ghi = False
        self.setWindowTitle('Phiếu kiểm đếm thực địa')
        self.resize(860, 560)
        lo = QVBoxLayout(self)
        gt = QLabel('1. Xuất phiếu (một file .html) → chép sang điện thoại, mở bằng trình duyệt, ghi tài sản kiểm đếm ngoài thực địa '
                    '(không cần mạng) → tải file kết quả .json.\n2. Nhập kết quả: các dòng được thêm vào phương án từng hộ như "Dán '
                    'danh sách tài sản" (khớp danh mục đơn giá; cây có số đo xếp theo quy cách).\n3. Gắn ảnh: chọn thư mục ảnh chụp; '
                    'ảnh đặt tên theo số CCCD, họ tên hoặc HO<số thứ tự> (vd HO012_nha.jpg) được gắn vào hộ.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        from .giao_dien import XepDong
        hang = QWidget()
        h = XepDong(hang, 8)                            # màn hình hẹp: nút xuống dòng, không ép hộp rộng hơn màn hình
        h.setContentsMargins(0, 0, 0, 0)
        self.b_xuat = QPushButton('Xuất phiếu kiểm đếm (.html)…')
        self.b_nhap = QPushButton('Nhập kết quả kiểm đếm (.json)…')
        self.b_anh = QPushButton('Gắn ảnh hiện trạng từ thư mục…')
        self.b_xuat.clicked.connect(lambda: self.xuat())
        self.b_nhap.clicked.connect(lambda: self.nhap())
        self.b_anh.clicked.connect(lambda: self.gan_anh())
        for b in (self.b_xuat, self.b_nhap, self.b_anh):
            h.addWidget(b)
        lo.addWidget(hang)
        if chi_doc:
            for b in (self.b_nhap, self.b_anh):
                b.setEnabled(False)
                b.setToolTip('Dự án đang mở chỉ xem.')
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(['STT', 'Họ và tên', 'Số ảnh', 'Ảnh'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate((50, 260, 70)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.cellDoubleClicked.connect(lambda r, _c: self.mo_anh(r))
        lo.addWidget(self.bang, 2)
        self.o_kq = QPlainTextEdit()
        self.o_kq.setReadOnly(True)
        self.o_kq.setPlaceholderText('Kết quả nhập / gắn ảnh hiện ở đây.')
        lo.addWidget(self.o_kq, 1)
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hd = QHBoxLayout()
        hd.addStretch(1)
        hd.addWidget(b_dong)
        lo.addLayout(hd)
        self.nap()

    def nap(self) -> None:
        so = pk.so_anh_theo_ho(self.con)
        ds = [r for r in self.con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu, ma_ho')]
        self.bang.setRowCount(len(ds))
        self._ma = []
        for i, r in enumerate(ds):
            anh = pk.anh_cua_ho(self.con, r['ma_ho']) if so.get(r['ma_ho']) else []
            for c, chu in enumerate((str(r['thu_tu']), r['ho_ten'] or '', str(so.get(r['ma_ho'], '') or ''),
                                     ', '.join(a['ten_file'] for a in anh[:6]) + (' …' if len(anh) > 6 else ''))):
                self.bang.setItem(i, c, QTableWidgetItem(chu))
            self._ma.append(r['ma_ho'])

    def _ghi_kq(self, chu: str) -> None:
        self.o_kq.appendPlainText(chu)

    def _bao_loi(self, e) -> None:
        from .thong_bao import chu_loi
        chu = str(e) if isinstance(e, LoiNhap) else chu_loi('Không thực hiện được', e)
        self._ghi_kq(chu)
        if not self.im_lang:
            QMessageBox.warning(self, 'Phiếu kiểm đếm', chu)

    def xuat(self, file_ra=None):
        if file_ra is None:
            if self.im_lang:
                return None
            file_ra, _ = QFileDialog.getSaveFileName(self, 'Lưu phiếu kiểm đếm', str(self.thu_muc / 'PhieuKiemDem.html'),
                                                     'Trang web (*.html)')
            if not file_ra:
                return None
        try:
            ra = pk.xuat_phieu_kiem_dem_html(self.con, file_ra)
        except Exception as e:                          # noqa: BLE001
            self._bao_loi(e)
            return None
        self._ghi_kq(f'Đã xuất phiếu: {ra}')
        return ra

    def nhap(self, file=None):
        if self.chi_doc:
            return None
        if file is None:
            if self.im_lang:
                return None
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file kết quả kiểm đếm', str(self.thu_muc), 'Kết quả kiểm đếm (*.json)')
            if not file:
                return None
        from .giao_dien import con_tro_cho
        try:
            with con_tro_cho():
                kq = pk.nhap_ket_qua_kiem_dem(self.con, file, self.dm)
        except Exception as e:                          # noqa: BLE001
            self._bao_loi(e)
            return None
        self.da_ghi = self.da_ghi or kq['so_dong'] > 0
        self._ghi_kq(f'Đã thêm {kq["so_dong"]} dòng vào phương án {kq["so_ho"]} hộ.' +
                     (f' {len(kq["loi"])} dòng chưa thêm được:\n- ' + '\n- '.join(kq['loi']) if kq['loi'] else ''))
        return kq

    def gan_anh(self, thu_muc=None):
        if self.chi_doc:
            return None
        if thu_muc is None:
            if self.im_lang:
                return None
            thu_muc = QFileDialog.getExistingDirectory(self, 'Chọn thư mục ảnh hiện trạng', str(self.thu_muc))
            if not thu_muc:
                return None
        from .giao_dien import con_tro_cho
        try:
            with con_tro_cho():
                kq = pk.gan_anh_hien_trang(self.con, thu_muc)
        except Exception as e:                          # noqa: BLE001
            self._bao_loi(e)
            return None
        self.da_ghi = self.da_ghi or kq['da_gan'] > 0
        self._ghi_kq(f'{kq["so_anh"]} ảnh: gắn mới {kq["da_gan"]}.' +
                     (f' {len(kq["chua_khop"])} ảnh chưa gắn:\n- ' + '\n- '.join(kq['chua_khop'][:200]) if kq['chua_khop'] else ''))
        self.nap()
        return kq

    def mo_anh(self, r: int) -> None:
        if 0 <= r < len(self._ma):
            anh = pk.anh_cua_ho(self.con, self._ma[r])
            if anh and not self.im_lang:
                QDesktopServices.openUrl(QUrl.fromLocalFile(anh[0]['duong_dan']))
