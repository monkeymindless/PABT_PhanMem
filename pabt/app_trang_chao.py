"""Màn hình chính / màn hình chào của cửa sổ chính (1.1.05: tách từ CuaSoChinh - lớp app.py 3.800 dòng). Mixin, không dùng
riêng: CuaSoChinh kế thừa TrangChaoMixin; mọi self.X khác (mo, _chay_lenh, trang, lenh...) là của CuaSoChinh. Thân hàm chép
nguyên văn từ app.py; app.py nhập lại TRANG_CHAO, QSS_NUT_MO_GAN."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from pathlib import Path
from . import csdl, lap_pa
from .giao_dien import dat_kieu_theo_tong, dung_ve, phong_so
from .thong_bao import chu_loi
from .tien import D
from .du_an_gan_day import GAN_DAY_TOI_DA, _tom_tat_pabt, doc_gan_day, doc_ghim, ghi_tong_nho, ghim_du_an


# nút "Mở" của bảng dự án gần đây: viền + chữ navy, rê chuột nền navy chữ trắng (bộ chọn #id thắng tô màu theo chữ "Mở" của _BoToMau)
QSS_NUT_MO_GAN = ('QPushButton#nut_mo_gan { padding: 2px 14px; border: 1px solid #1E3A5F; border-radius: 4px; color: #1E3A5F; '
                  'background: #FFFFFF; font-weight: 600; } '
                  'QPushButton#nut_mo_gan:hover { background: #1E3A5F; color: #FFFFFF; } '
                  'QPushButton#nut_mo_gan:pressed { background: #092240; color: #FFFFFF; }')
TRANG_CHAO = 4                     # chỉ số trong self.trang (QStackedWidget) của màn hình chào khi chưa mở dự án


class TrangChaoMixin:
    """Phương thức màn hình chào / dự án gần đây / tổng quan dự án của CuaSoChinh."""
    def _trang_chao(self) -> QWidget:
        """Màn hình chính (ô TRANG_CHAO của self.trang) = ngan_chao: ô 0 màn hình chào khi chưa mở dự án (0.9.23: thẻ bắt đầu + dự
        án gần đây), ô 1 tổng quan dự án khi đã mở dự án (1.0.07, man_hinh_tong_quan - tạo khi cần lần đầu: _nap_tong_quan)."""
        self.ngan_chao = QStackedWidget()
        self.ngan_chao.addWidget(self._trang_chao_bat_dau())
        self.tong_quan = None
        return self.ngan_chao

    def _nap_tong_quan(self):
        """Đã mở dự án: Màn hình chính hiện tổng quan dự án (KPI, hộ đang làm dở, đồng hồ pháp lý); chưa mở: màn hình chào."""
        if not hasattr(self, 'ngan_chao'):
            return
        if self.con is None or self.file is None or not hasattr(self, 'mo_hinh'):
            self.ngan_chao.setCurrentIndex(0)
            return
        # 1.0.99 (Đợt 8): về Màn hình chính khi số liệu không đổi thì KHÔNG tính / vẽ lại (trước 150 ms mỗi lần bấm, dự án 3.000 hộ).
        # Khóa: dấu hiệu dữ liệu của kết nối (total_changes + data_version: máy khác ghi cũng đổi), ngày (hạn pháp lý), tông nền, cỡ chữ,
        # chế độ chỉ xem, danh sách hộ của mô hình, lần phương án đang xem ở phễu.
        from datetime import date
        from .giao_dien import TY_LE, TONG_NEN
        tt = csdl.trang_thai_nho(self.con)
        khoa_tq = None if tt is None else (tt, id(self.con), str(self.file), bool(getattr(self, 'chi_doc', False)), date.today(),
                                        TONG_NEN[0], TY_LE[0], id(self.mo_hinh.dong), len(self.mo_hinh.dong),
                                        None if self.tong_quan is None else self.tong_quan.pheu.cb_lan.currentData())
        if khoa_tq is not None and self.tong_quan is not None and getattr(self, '_khoa_tong_quan', None) == khoa_tq:
            self.ngan_chao.setCurrentWidget(self.tong_quan)
            return
        self._khoa_tong_quan = None
        if self.tong_quan is None:
            from .man_hinh_tong_quan import KhungTongQuanDuAn
            self.tong_quan = KhungTongQuanDuAn(self.lenh)
            self.tong_quan.mo_ho.connect(lambda m: self._chay_lenh(lambda: self.mo_lap_pa(m)))
            self.tong_quan.mo_buoc.connect(lambda b: self._chay_lenh(lambda: self.mo_buoc_quy_trinh(b)))
            self.tong_quan.chay_lenh.connect(self._kich_lenh)
            self.ngan_chao.addWidget(self.tong_quan)
            if self.isVisible():
                from .giao_dien import ap_kieu_cay
                ap_kieu_cay(self.tong_quan)
        da = {}
        try:
            r = self.con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
            da = dict(r) if r is not None else {}
        except Exception:
            da = {}
        dia_ban = f'{da.get("cap_dia_ban") or ""} {da.get("ten_dia_ban") or ""}'.strip()
        try:
            lap = lap_pa.phan_loai_lap(self.con)
            self.tong_quan.nap(self.con, self.mo_hinh.dong, da.get('ten') or self.file.stem, dia_ban, str(self.file),
                               da.get('chu_dau_tu') or '', lap=lap)
            self._khoa_tong_quan = khoa_tq                 # chỉ nhớ khi nạp trọn vẹn (lỗi giữa chừng: lần sau tính lại)
        except Exception as e:                          # số liệu phụ (niêm yết, vận động) lỗi: vẫn hiện màn hình chính
            self.statusBar().showMessage(chu_loi('Không tính được số liệu tổng quan', e), 8000)
        self.ngan_chao.setCurrentWidget(self.tong_quan)

    def _kich_lenh(self, khoa: str) -> None:
        """Chạy QAction của self.lenh (nút "Làm ngay" của buồng lái). Lệnh tắt (chưa đủ điều kiện / chỉ xem): trigger không làm gì."""
        a = self.lenh.get(khoa)
        if a is not None and a.isEnabled():
            a.trigger()

    def mo_buoc_quy_trinh(self, buoc: int, ngay=None, cho: bool = True):
        """Bấm một bước của quy trình QĐ 18 (buồng lái): bước đánh dấu bằng ngày (họp dân, thông báo thu hồi, công khai quyết định,
        gửi phương án, quyết định thu hồi) -> ghi ngày; bước khác -> mở chỗ làm (QAction quy_trinh.LENH_BUOC)."""
        from . import quy_trinh
        if self.con is None:
            return None
        if buoc in quy_trinh.MOC_BUOC:
            return self.ghi_ngay_buoc(buoc, ngay, cho)
        khoa = quy_trinh.LENH_BUOC.get(buoc)
        if khoa:
            self._kich_lenh(khoa)
        return khoa

    def _trang_chao_bat_dau(self) -> QWidget:
        """Màn hình chào khi chưa mở dự án (0.9.23 - thay dòng chữ vàng): 3 nút bắt đầu + dự án làm việc gần đây."""
        from .giao_dien import TOKEN, nut_lenh
        from .giao_dien import OTimKiemThongMinh
        w = QWidget()
        lo = QVBoxLayout(w)
        # 26/10/2026 (người dùng): nội dung sát lên trên (bỏ khoảng trống đầu trang), bảng dự án gần đây giãn hết phần còn lại
        lo.setContentsMargins(32, 12, 32, 12)
        tieu = QLabel('Hệ thống quản lý bồi thường, hỗ trợ và GPMB')
        tieu.setStyleSheet(f'QLabel {{ font-size: 18px; font-weight: 700; color: {TOKEN["chinh"]}; letter-spacing: 0; }}')
        tieu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(tieu)
        self.lb_chao = QLabel('Khởi tạo dự án mới hoặc tiếp tục làm việc với các hồ sơ gần đây')
        self.lb_chao.setWordWrap(True)
        self.lb_chao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_chao.setStyleSheet(f'QLabel {{ color: {TOKEN["chu_phu"]}; font-size: 13px; }}')
        lo.addWidget(self.lb_chao)
        h = QHBoxLayout()
        h.setSpacing(20)
        h.addStretch(1)
        self.nut_chao = {}
        mo_ta_nut = (
            ('Dự án mới…', 'moi', 'Khởi tạo CSDL .larc', 'Tạo dự án mới (3 bước) - Ctrl+N'),
            ('Mở dự án…', 'mo', 'Chọn tệp từ máy / LAN', 'Mở file dự án có sẵn (.larc, .pabt) - Ctrl+O'),
            ('Nhập file Excel…', 'excel', 'Bảng kiểm đếm số liệu', 'Nhập nhanh từ bảng kiểm đếm Excel'),
            # 1.0.04: tiếp nhận hồ sơ pháp lý đầu vào (máy trắng, chưa có dự án) - cùng QAction với menu trái (trigger)
            ('Tiếp nhận & Kiểm tra pháp lý dự án…', 'phap_ly', 'Kiểm tra hồ sơ đầu vào',
             'Tiếp nhận & kiểm tra pháp lý hồ sơ dự án trước khi triển khai - Ctrl+Shift+L'),
        )
        from .giao_dien import CO_ICON_THE_CHAO, TheChao
        self.the_chao = {}
        for ten, loai, phu, goi_y in mo_ta_nut:
            the = TheChao(loai=loai)
            b = nut_lenh(self.lenh[ten], CO_ICON_THE_CHAO, duoi=True)
            b.setToolTip(goi_y)
            the.setToolTip(goi_y)
            the.dat_noi_dung(b, phu, 'Hồ sơ pháp lý' if ten.startswith('Tiếp nhận') else '')   # biểu tượng 38px, tên lệnh, mô tả: tất cả trong thẻ
            h.addWidget(the)
            self.nut_chao[ten] = b
            self.the_chao[ten] = the
        h.addStretch(1)
        lo.addLayout(h)
        # Đóng / Xóa dự án chỉ ở menu Tệp tin (0.9.66: bỏ hàng nút luôn ẩn từ 0.9.38)
        # 0.9.80: thanh công cụ NGAY TRÊN ĐẦU bảng: tiêu đề | Mở đã chọn, Xóa khỏi danh sách, Xóa file | ô tìm (bo 6px); bảng trống thì ẩn cụm nút
        from PySide6.QtWidgets import QPushButton
        hang_gd = QHBoxLayout()
        hang_gd.setSpacing(8)
        nhan = QLabel('Hồ sơ dự án làm việc gần đây')
        nhan.setProperty('vai', 'nhan')
        hang_gd.addWidget(nhan)
        self.khung_nut_gan = QWidget()
        h3 = QHBoxLayout(self.khung_nut_gan)
        h3.setContentsMargins(8, 0, 0, 0)
        h3.setSpacing(6)
        self.b_mo_gan = QPushButton('Mở đã chọn')
        self.b_mo_gan.setToolTip('Đóng dự án hiện tại (nếu có) và mở file đang chọn — không cần thoát phần mềm')
        self.b_mo_gan.clicked.connect(lambda: self._chay_lenh(self._mo_gan_day_chon))
        self.b_bo_gan = QPushButton('Xóa khỏi danh sách')
        self.b_bo_gan.setToolTip('Bỏ khỏi danh sách gần đây; file dự án vẫn còn trên đĩa')
        self.b_bo_gan.clicked.connect(lambda: self._chay_lenh(lambda: self.xoa_du_an(xoa_file=False, tu_danh_sach=True)))
        self.b_xoa_gan = QPushButton('Xóa file dự án…')
        self.b_xoa_gan.setToolTip('Xóa hẳn file dự án đang chọn (không đưa vào Thùng rác). Thư mục bản in giữ nguyên.')
        self.b_xoa_gan.clicked.connect(lambda: self._chay_lenh(lambda: self.xoa_du_an(xoa_file=True, tu_danh_sach=True)))
        for b in (self.b_mo_gan, self.b_bo_gan, self.b_xoa_gan):
            h3.addWidget(b)
        hang_gd.addWidget(self.khung_nut_gan)
        hang_gd.addStretch(1)
        self.o_tim_gan = OTimKiemThongMinh()
        self.o_tim_gan.setPlaceholderText('Tìm theo tên dự án, địa bàn...')
        self.o_tim_gan.setMinimumWidth(240)
        self.o_tim_gan.setMaximumWidth(300)
        dat_kieu_theo_tong(self.o_tim_gan,
            'QLineEdit { border: 1px solid #8696AB; border-radius: 6px; padding: 4px 8px; background: #FFFFFF; }'
            'QLineEdit:focus { border: 2px solid #2563EB; padding: 3px 7px; }')
        self.o_tim_gan.chuoi_da_doi.connect(self._loc_gan_day)
        hang_gd.addWidget(self.o_tim_gan)
        lo.addSpacing(8)
        lo.addLayout(hang_gd)
        self.ds_gan_day = QTableWidget(0, 6)
        self.ds_gan_day.setHorizontalHeaderLabels(
            ['Tên dự án và địa bàn', 'Số hộ', 'Tổng kinh phí', 'Cập nhật', 'Ghim', 'Thao tác'])
        self.ds_gan_day.horizontalHeader().setStretchLastSection(True)
        self.ds_gan_day.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3, 4):                           # tiêu đề đậm (nền navy): cột vừa cả chữ tiêu đề lẫn số liệu, không cắt "Tổng kinh phí"
            self.ds_gan_day.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.ds_gan_day.verticalHeader().setVisible(False)
        self.ds_gan_day.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ds_gan_day.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ds_gan_day.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ds_gan_day.cellDoubleClicked.connect(lambda r, _c: self._mo_gan_day_dong(r))
        self.ds_gan_day.itemSelectionChanged.connect(self._cap_nhat_nut_gan_day)
        # trạng thái trống (0.9.80): không hiện lưới trắng trơ trọi - biểu tượng thư mục + hướng dẫn bắt đầu, ở giữa vùng bảng
        self.ngan_gan_day = QStackedWidget()
        self.ngan_gan_day.addWidget(self.ds_gan_day)
        self.ngan_gan_day.addWidget(self._trang_trong_gan_day())
        lo.addWidget(self.ngan_gan_day, 1)                # giãn hết chiều cao còn lại (trước: tối đa 220 px, dưới trống)
        # chân trang 4 liên kết (0.9.80): Hướng dẫn · Bảng giá đất NQ 28 · Quy trình 16 bước · Lịch sử cập nhật
        chan = QHBoxLayout()
        chan.setContentsMargins(0, 10, 0, 0)
        chan.setSpacing(14)
        chan.addStretch(1)
        self.lk_huong_dan = None
        self.lien_ket_chan = {}
        for i, (ma, ten, chu, goi_y, ham) in enumerate((
                (0xE897, 'huong_dan', 'Hướng dẫn sử dụng (F1)', 'Hướng dẫn sử dụng phần mềm',
                 lambda: self._chay_lenh(self.lenh['Hướng dẫn sử dụng'].trigger)),
                (0xE707, 'bang_gia_dat', 'Tra cứu Bảng giá đất NQ 28', 'Tra cứu bảng giá đất Nghị quyết 28/2025',
                 lambda: self._chay_lenh(self.lenh['Bảng giá đất NQ 28…'].trigger)),
                (0xE8FD, 'quy_trinh', 'Quy trình 16 bước QĐ 18', 'Quy trình 16 bước thu hồi đất, bồi thường theo QĐ 18/2026 và chỗ làm trong phần mềm',
                 lambda: self._chay_lenh(self.quy_trinh_16_buoc)),
                (0xE81C, 'lich_su', 'Lịch sử cập nhật phần mềm', 'Các bản cập nhật từ phiên bản 0.9.53',
                 lambda: self._chay_lenh(self.lich_su_cap_nhat)))):
            if i:
                cham = QLabel('·')
                dat_kieu_theo_tong(cham, 'QLabel { color: #94A3B8; font-size: 14px; font-weight: 700; background: transparent; }')
                chan.addWidget(cham)
            khung, lk = self._lien_ket_icon(ma, chu, ham)
            lk.setToolTip(goi_y)
            chan.addWidget(khung)
            self.lien_ket_chan[ten] = lk
        self.lk_huong_dan = self.lien_ket_chan['lich_su']      # tên cũ (test): liên kết "Lịch sử cập nhật phần mềm"
        chan.addStretch(1)
        lo.addLayout(chan)
        return w

    def _trang_trong_gan_day(self) -> QWidget:
        """Trạng thái trống của bảng dự án gần đây."""
        from .giao_dien import icon_ky_hieu
        w = QWidget()
        w.setObjectName('trong_gan_day')
        dat_kieu_theo_tong(w, 'QWidget#trong_gan_day { background: transparent; border: 1px dashed #CBD5E1; border-radius: 8px; }')
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        v.addStretch(1)
        self.lb_trong_icon = QLabel()
        self.lb_trong_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_trong_icon.setStyleSheet('QLabel { background: transparent; border: 0; }')
        ic = icon_ky_hieu(0xE8B7, '#94A3B8', 42)                 # thư mục (không dùng emoji: Windows 7 không có phông emoji)
        if ic is not None:
            self.lb_trong_icon.setPixmap(ic.pixmap(42, 42))
        else:
            self.lb_trong_icon.setVisible(False)
        v.addWidget(self.lb_trong_icon)
        self.lb_trong = QLabel('Chưa có hồ sơ dự án nào được mở gần đây.\n'
                               "Hãy bấm 'Dự án mới' hoặc 'Mở dự án' phía trên để bắt đầu.")
        self.lb_trong.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dat_kieu_theo_tong(self.lb_trong, 'QLabel { color: #64748B; font-size: 13px; background: transparent; border: 0; }')
        v.addWidget(self.lb_trong)
        v.addStretch(1)
        return w

    def _hien_trong_gan_day(self):
        """Bảng trống: hiện trạng thái trống, ẩn cụm nút thao tác, tắt ô tìm; có dòng: ngược lại."""
        co = self.ds_gan_day.rowCount() > 0
        self.ngan_gan_day.setCurrentIndex(0 if co else 1)
        self.khung_nut_gan.setVisible(co)
        self.o_tim_gan.setEnabled(co)

    def _nap_gan_day(self):
        from datetime import datetime
        import time
        viec = ('Khởi tạo dự án mới hoặc tiếp tục làm việc với các hồ sơ gần đây.')
        self.lb_chao.setText(f'Đang mở dự án {self.file.name} — bấm một mục ở menu trái để quay lại làm việc. {viec}'
                             if self.con is not None and self.file else viec)
        self.ds_gan_day.setRowCount(0)
        n = 0
        ghim = {x.lower() for x in doc_ghim()}
        ds = doc_gan_day()
        dau = [x for x in doc_ghim() if any(x.lower() == y.lower() for y in ds)]
        con = [x for x in ds if x.lower() not in ghim]
        from .giao_dien import icon_ky_hieu, TOKEN
        ic_file = icon_ky_hieu(0xE8E5, TOKEN['chinh'], 16)
        for f in map(Path, dau + con):
            try:
                st = f.stat()
            except OSError:
                continue
            if self.con is not None and self.file is not None and self.kq is not None and f.resolve() == self.file.resolve():
                ghi_tong_nho(f, len(self.kq.ho), sum((h['tong'] for h in self.kq.ho), D('0')))    # dự án đang mở: tổng vừa tính, khỏi tính lại
            so_ho, tong, chu_tim, ten_hien = _tom_tat_pabt(f)
            r = self.ds_gan_day.rowCount()
            self.ds_gan_day.insertRow(r)
            ten = QTableWidgetItem(ten_hien)
            ten.setData(Qt.ItemDataRole.UserRole, str(f))
            ten.setData(Qt.ItemDataRole.UserRole + 1, f'{f.name} {chu_tim}')      # ô tìm: tên file + tên dự án + địa bàn
            ten.setToolTip(str(f))
            if ic_file is not None:
                ten.setIcon(ic_file)
            self.ds_gan_day.setItem(r, 0, ten)
            self.ds_gan_day.setItem(r, 1, QTableWidgetItem('—' if so_ho is None else f'{so_ho} hộ'))
            o_tong = QTableWidgetItem('—' if tong is None else tong)
            o_tong.setFont(phong_so())                  # 1.0.51: số tiền phông số
            self.ds_gan_day.setItem(r, 2, o_tong)
            cach = time.time() - st.st_mtime
            if cach < 3600:
                luc = f'{max(1, int(cach // 60))} phút trước'
            elif cach < 86400:
                luc = 'Hôm nay'
            else:
                luc = datetime.fromtimestamp(st.st_mtime).strftime('%d/%m/%Y')
            self.ds_gan_day.setItem(r, 3, QTableWidgetItem(luc))
            from PySide6.QtWidgets import QPushButton, QToolButton
            da_ghim = str(f.resolve()).lower() in ghim or str(f).lower() in ghim
            b_ghim = QToolButton()
            # 17/10/2026: biểu tượng ghim của phông Segoe MDL2 (đã ghim: ghim đặc navy) thay emoji ghim - Windows 7 không có
            # phông emoji (hiện ô vuông); máy không có phông biểu tượng thì hiện chữ
            ic_ghim = icon_ky_hieu(0xE841 if da_ghim else 0xE718, TOKEN['chinh'] if da_ghim else '#94A3B8', 16)
            if ic_ghim is not None:
                b_ghim.setIcon(ic_ghim)
            else:
                b_ghim.setText('Bỏ ghim' if da_ghim else 'Ghim')
            b_ghim.setToolTip('Bỏ ghim — xuống theo thứ tự gần đây' if da_ghim else 'Ghim dự án quan trọng lên đầu')
            b_ghim.setAutoRaise(True)
            b_ghim.clicked.connect(lambda _=False, p=str(f), g=not da_ghim: self._chay_lenh(
                lambda: (ghim_du_an(p, g), self._nap_gan_day())))
            self.ds_gan_day.setCellWidget(r, 4, b_ghim)
            mo = QPushButton('Mở')
            mo.setCursor(Qt.CursorShape.PointingHandCursor)
            mo.setObjectName('nut_mo_gan')
            dat_kieu_theo_tong(mo, QSS_NUT_MO_GAN)
            mo.clicked.connect(lambda _=False, p=str(f): self._chay_lenh(lambda: self.mo(p)))
            hop_mo = QWidget()
            hm = QHBoxLayout(hop_mo)
            hm.setContentsMargins(4, 2, 4, 2)
            hm.addStretch(1)
            hm.addWidget(mo)
            hm.addStretch(1)
            self.ds_gan_day.setCellWidget(r, 5, hop_mo)
            n += 1
            if n >= GAN_DAY_TOI_DA:                       # trước 26/10/2026: tối đa 8 dòng
                break
        dang_mo = self.con is not None and self.file is not None
        self.lenh['Đóng dự án'].setEnabled(dang_mo)
        if hasattr(self, 'nut_chao'):
            goi_y = ('Mở file dự án khác (đóng dự án hiện tại, không thoát phần mềm) - Ctrl+O' if dang_mo
                     else 'Mở file dự án có sẵn (.larc, .pabt) - Ctrl+O')
            self.nut_chao['Mở dự án…'].setToolTip(goi_y)
            self.the_chao['Mở dự án…'].setToolTip(goi_y)
        self._hien_trong_gan_day()
        self._cap_nhat_nut_gan_day()
        if hasattr(self, 'o_tim_gan') and self.o_tim_gan.text().strip():
            self._loc_gan_day(self.o_tim_gan.text())
        if self.trang.currentIndex() == TRANG_CHAO:
            self._nap_tong_quan()

    def _loc_gan_day(self, chu: str = ''):
        from .lap_pa import bo_dau
        k = bo_dau((chu or '').strip())
        for r in range(self.ds_gan_day.rowCount()):
            it = self.ds_gan_day.item(r, 0)
            tim = (it.data(Qt.ItemDataRole.UserRole + 1) or it.text()) if it else ''
            self.ds_gan_day.setRowHidden(r, bool(k) and k not in bo_dau(tim))

    def _mo_gan_day_dong(self, r: int):
        it = self.ds_gan_day.item(r, 0) if r >= 0 else None
        p = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        if p:
            self._chay_lenh(lambda: self.mo(p))

    def _file_gan_day_chon(self):
        if not hasattr(self, 'ds_gan_day'):
            return None
        r = self.ds_gan_day.currentRow()
        it = self.ds_gan_day.item(r, 0) if r >= 0 else None
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def _cap_nhat_nut_gan_day(self):
        p = self._file_gan_day_chon()
        dang_mo = self.con is not None and self.file is not None
        if hasattr(self, 'b_mo_gan'):
            self.b_mo_gan.setEnabled(bool(p))
            self.b_bo_gan.setEnabled(bool(p))
            self.b_xoa_gan.setEnabled(bool(p))
        self.lenh['Xóa dự án…'].setEnabled(dang_mo or bool(p))

    def _mo_gan_day_chon(self):
        p = self._file_gan_day_chon()
        if p:
            self.mo(p)

    def _hien_trang_chao(self):
        """Chưa mở / vừa đóng dự án: màn hình chào thay danh sách trống (trang Dự toán dùng được khi chưa mở dự án: giữ)."""
        self._cap_nhat_chon()
        from .giao_dien import dat_to_chuc
        dat_to_chuc(self.bang_tieu_de)
        if hasattr(self, 'lb_don_vi'):
            from . import to_chuc
            self.lb_don_vi.setText(to_chuc.TEN)
        if self.trang.currentIndex() != 3:
            self.trang.setCurrentIndex(TRANG_CHAO)
            self.lb_trang.setVisible(False)
            self._danh_dau_trang_chu()
            self._dam_bao_tab(-1)
        self._nap_gan_day()
        self._cap_nhat_hien_hang_the()

    def ve_trang_chu(self):
        """Nút "Màn hình chính" (menu trái): về màn hình bắt đầu như lúc mở phần mềm - Dự án mới, Mở dự án,
        Nhập Excel, dự án gần đây. Dự án đang mở vẫn mở: bấm một trang ở menu trái để quay lại."""
        self._danh_dau_trang_chu()                       # 1.0.44: dấu chọn menu ngay, trước khi nạp / đổi trang
        self._tai_lai_neu_doi()                         # 1.0.09: tổng quan dự án tính cả hộ vừa thêm ở cửa sổ hộ
        with dung_ve(self):
            self.trang.setCurrentIndex(TRANG_CHAO)
            if hasattr(self, 'ngan_lv'):
                self.ngan_lv.setCurrentWidget(self.trang)
            self.lb_trang.setVisible(False)
            self._nap_gan_day()
            self._dam_bao_tab(-1)
            self._cap_nhat_hien_hang_the()

    def _danh_dau_trang_chu(self):
        self._dong_bo_menu_trai('Màn hình chính')
