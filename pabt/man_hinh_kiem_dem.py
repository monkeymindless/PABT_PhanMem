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
        gt = QLabel('1. Xuất phiếu (ứng dụng LARC Field Mobile - một file .html) → chép sang điện thoại, mở bằng trình duyệt (không '
                    'cần mạng): ghi nhà ở, vật kiến trúc, cây trồng, chụp ảnh biên bản, xem bản đồ thửa + định vị GPS → lưu file .json. '
                    'Điện thoại đã cài ứng dụng LARC Field Mobile (Android .apk / iPhone "Thêm vào MH chính"): xuất dữ liệu dự án (.json) '
                    'rồi mở file đó trong ứng dụng.'
                    '\n2. Nhập kết quả: các dòng được thêm vào phương án từng hộ như "Dán danh sách tài sản" (khớp danh mục đơn giá; '
                    'cây có số đo xếp theo quy cách); ảnh gửi kèm lưu vào thư mục Anh_kiem_dem cạnh file dự án; tọa độ GPS ghi vào '
                    'ghi chú hộ.\n3. Gắn ảnh: chọn thư mục ảnh chụp; ảnh đặt tên theo số CCCD, họ tên hoặc HO<số thứ tự> (vd '
                    'HO012_nha.jpg) được gắn vào hộ.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        from .giao_dien import XepDong
        hang = QWidget()
        h = XepDong(hang, 8)                            # màn hình hẹp: nút xuống dòng, không ép hộp rộng hơn màn hình
        h.setContentsMargins(0, 0, 0, 0)
        self.b_xuat = QPushButton('Xuất phiếu kiểm đếm (.html)…')
        self.b_du_lieu = QPushButton('Xuất dữ liệu cho ứng dụng điện thoại…')
        self.b_du_lieu.setToolTip('File .json mở trong ứng dụng LARC Field Mobile đã cài (Android .apk, iPhone bản PWA).')
        self.b_nhap = QPushButton('Nhập kết quả kiểm đếm (.json)…')
        self.b_anh = QPushButton('Gắn ảnh hiện trạng từ thư mục…')
        self.b_xuat.clicked.connect(lambda: self.xuat())
        self.b_du_lieu.clicked.connect(lambda: self.xuat_du_lieu())
        self.b_nhap.clicked.connect(lambda: self.nhap())
        self.b_anh.clicked.connect(lambda: self.gan_anh())
        for b in (self.b_xuat, self.b_du_lieu, self.b_nhap, self.b_anh):
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

    def xuat_du_lieu(self, file_ra=None):
        """File dữ liệu dự án cho ứng dụng LARC Field Mobile đã cài trên điện thoại (Android / iPhone)."""
        if file_ra is None:
            if self.im_lang:
                return None
            file_ra, _ = QFileDialog.getSaveFileName(self, 'Lưu dữ liệu cho ứng dụng điện thoại',
                                                     str(self.thu_muc / pk.ten_file_du_lieu(self.con)), 'Dữ liệu dự án (*.json)')
            if not file_ra:
                return None
        try:
            ra = pk.xuat_du_lieu_di_dong(self.con, file_ra)
        except Exception as e:                          # noqa: BLE001
            self._bao_loi(e)
            return None
        self._ghi_kq(f'Đã xuất dữ liệu cho ứng dụng điện thoại: {ra}\nGửi file này sang điện thoại, mở ứng dụng LARC Field Mobile -> '
                     '"Chọn file dữ liệu dự án…".')
        return ra

    def nhap(self, file=None, tao_ho_moi=None):
        """Nhập file .json của phiếu (một hộ "<Tên hộ>.json" hoặc cả dự án). Hộ của phiếu không khớp hộ nào của dự án (1.0.32: khớp theo
        CCCD -> tờ / thửa, lô rừng -> họ tên -> mã hộ): hỏi thêm thành hộ mới (tao_ho_moi None = hỏi; True / False cho kiểm thử)."""
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
            chua = [x for x in kq['chua_khop'] if not x['ung_vien']]     # nhiều hộ giống nhau: không tự tạo, người dùng chọn tay
            if chua:
                if tao_ho_moi is None:
                    tao_ho_moi = not self.im_lang and QMessageBox.question(
                        self, 'Phiếu kiểm đếm', f'{len(chua)} hộ trong phiếu chưa có trong dự án:\n- '
                        + '\n- '.join(f'{x["ten"]} ({x["so_dong"]} dòng)' for x in chua[:15])
                        + ('\n…' if len(chua) > 15 else '') + '\n\nThêm thành hộ mới của dự án?') == QMessageBox.StandardButton.Yes
                if tao_ho_moi:
                    with con_tro_cho():
                        k2 = pk.nhap_ket_qua_kiem_dem(self.con, file, self.dm, tao_ho_moi=True, chi={x['khoa'] for x in chua})
                    for k in ('so_dong', 'so_ho', 'so_anh', 'so_gps'):
                        kq[k] = kq.get(k, 0) + k2.get(k, 0)
                    kq['tao_moi'] = k2['tao_moi']
                    bo = {x['khoa'] for x in chua}
                    kq['loi'] = [x for x in kq['loi'] if not any(x.startswith(c['ten'] + ':') for c in kq['chua_khop']
                                                                 if c['khoa'] in bo)] + k2['loi']
        except Exception as e:                          # noqa: BLE001
            self._bao_loi(e)
            return None
        self.da_ghi = self.da_ghi or kq['so_dong'] > 0 or any(kq.get(k, 0) > 0 for k in ('tao_moi', 'so_anh', 'so_gps'))
        self._ghi_kq(f'Đã thêm {kq["so_dong"]} dòng vào phương án {kq["so_ho"]} hộ'
                     + (f' (thêm {kq["tao_moi"]} hộ mới)' if kq.get('tao_moi') else '')
                     + (f'; {kq["so_anh"]} ảnh mới ({kq.get("thu_muc_anh", "")})' if kq.get('so_anh') else '')
                     + (f'; tọa độ GPS {kq["so_gps"]} hộ (ghi chú hộ)' if kq.get('so_gps') else '') + '.' +
                     (f' {len(kq["loi"])} dòng chưa thêm được:\n- ' + '\n- '.join(kq['loi']) if kq['loi'] else ''))
        if kq.get('so_anh'):
            self.nap()
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
