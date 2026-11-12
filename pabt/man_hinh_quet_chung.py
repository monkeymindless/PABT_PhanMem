"""Nút Quét dùng chung (UnifiedScanTriggerButton) + hộp xem kết quả quét (AI Smart Scan hợp nhất, chạy trên máy - quet_chung.py).

Mọi nơi có nút "Quét / Nạp file" dùng `NutQuetChung(nhan, ngu_canh)` hoặc `chon_va_quet(cha, ngu_canh)`: chọn file -> hộp tiến trình (nhận dạng
chữ từng trang) -> `quet_chung.quet` -> `HopKetQuaQuet` cho người dùng XEM TRƯỚC: từng file nhận là loại gì + nút xử lý tiếp ở màn hình chuyên
trách (đổi được loại nếu nhận sai), văn bản căn cứ đã sắp 13 bậc, thửa đất, tài sản / cây trồng + nút đưa vào phương án của hộ. Không gửi dữ liệu ra
ngoài. Hộp chỉ ghi nhận việc được chọn (hanh_dong); nơi mở hộp (cửa sổ chính) làm việc đó sau khi hộp đóng."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import quet_chung as qc
from . import van_ban_can_cu as vb
from .tien import vn

TIEU_DE = 'LARC - Quét file'
TEN_NGU_CANH = {
    qc.AUTO: 'Quét file (tự nhận dạng loại văn bản)',
    qc.CAN_CU: 'Quét văn bản căn cứ',
    qc.GIA_DAT: 'Quét văn bản / bảng giá đất',
    qc.GIA_TAI_SAN: 'Quét đơn giá nhà, vật kiến trúc, cây trồng',
    qc.HO_SO_HO: 'Quét hồ sơ chi tiết của hộ',
    qc.BANG_TONG_HOP: 'Quét bảng tổng hợp',
}
TEN_NHOM = {'DAT_NONG_NGHIEP': 'Đất nông nghiệp', 'DAT_O': 'Đất ở', 'DAT_TMDV': 'Đất TMDV', 'DAT_SXKD_KHOANGSAN': 'Đất SX-KD, khoáng sản'}
TEN_KET_CAU = {'NHUA_BETONG': 'Đường nhựa, bê tông', 'DAT_SOI_DA_CAPPHOI': 'Đường đất, đá, sỏi, cấp phối'}


def quet_co_tien_do(cha, files, ngu_canh: str = qc.AUTO, doc=None):
    """qc.quet kèm hộp tiến trình (bản scan nhận dạng chữ từng trang, bấm Hủy được). None: người dùng hủy."""
    from . import ocr
    from .man_hinh_quan_ly import doc_co_tien_do
    try:
        return doc_co_tien_do(cha, qc.quet, list(files), ngu_canh, doc=doc)
    except ocr.DaHuy:
        return None


def chon_va_quet(cha, ngu_canh: str = qc.AUTO, files=None, doc=None):
    """Hộp chọn file (hoặc files cho sẵn - kiểm thử) -> kết quả quét; None nếu không chọn / hủy."""
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(cha, TEN_NGU_CANH.get(ngu_canh, 'Quét file'), '', qc.LOC_FILE)
    if not files:
        return None
    kq = quet_co_tien_do(cha, files, ngu_canh, doc)
    if kq is not None and kq.loi and not kq.co_du_lieu() and not getattr(cha, 'im_lang', False):
        QMessageBox.warning(cha, TIEU_DE, 'Không đọc được file:\n' + '\n'.join(kq.loi[:8]))
    return kq


class NutQuetChung(QPushButton):
    """UnifiedScanTriggerButton: một nút, một ngữ cảnh. Bấm -> chọn file -> quét -> phát tín hiệu da_quet(KetQuaQuet)."""
    da_quet = Signal(object)

    def __init__(self, nhan: str, ngu_canh: str = qc.AUTO, cha=None):
        super().__init__(nhan, cha)
        self.ngu_canh = ngu_canh
        self.kq = None
        self.setToolTip('Đọc file (PDF, Word .doc và .docx, Excel, ảnh scan) ngay trên máy, không gửi dữ liệu ra ngoài. '
                        'Xem toàn văn và câu quy định / đơn giá trước khi áp dụng.')
        self.clicked.connect(lambda *_: self.quet())

    def quet(self, files=None, doc=None):
        kq = chon_va_quet(self.window(), self.ngu_canh, files, doc)
        if kq is not None:
            self.kq = kq
            self.da_quet.emit(kq)
        return kq


def _bang(cot: list, dong: list) -> QTableWidget:
    b = QTableWidget(len(dong), len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    b.verticalHeader().setVisible(False)
    b.horizontalHeader().setStretchLastSection(True)
    for i, r in enumerate(dong):
        for j, v in enumerate(r):
            it = QTableWidgetItem(str(v))
            if isinstance(v, str) and v[:1].isdigit() and j > 1:
                it.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            b.setItem(i, j, it)
    b.resizeColumnsToContents()
    return b


class HopKetQuaQuet(QDialog):
    """Xem trước kết quả quét. Sau khi đóng: hanh_dong = '' | 'ghi_can_cu' | 'tinh_gia' | 'dua_vao_ho' | 'mo_file' (file_chon, loai_chon)."""
    im_lang = False
    # loại có màn hình xử lý tiếp (căn cứ ghi bằng nút riêng, "chưa nhận ra" không có việc)
    LOAI_CON_VIEC = (qc.D_DU_AN, qc.D_CHI_TIET, qc.D_HE_SO_K, qc.D_BANG_GIA, qc.D_DON_GIA, qc.D_HO_SO)

    def __init__(self, parent, kq: qc.KetQuaQuet, co_du_an: bool = False, chi_doc: bool = False, ds_ho=(), ma_ho=None):
        super().__init__(parent)
        self.kq, self.hanh_dong = kq, ''
        self.file_chon, self.loai_chon = None, ''
        self.setWindowTitle(f'{TIEU_DE} - kết quả')
        self.resize(940, 580)
        lo = QVBoxLayout(self)
        dau = QLabel(f'Đã đọc {kq.so_file} file trong {kq.thoi_gian_ms} ms: {len(kq.can_cu)} văn bản căn cứ, {len(kq.quy_tac)} câu quy tắc, '
                     f'{len(kq.dong_dat)} thửa đất, {len(kq.dong_dan) or len(kq.dong_tai_san)} dòng tài sản / cây trồng.'
                     + (f'  Không đọc được {len(kq.loi)} file.' if kq.loi else ''))
        dau.setWordWrap(True)
        lo.addWidget(dau)
        self.tab = QTabWidget()
        lo.addWidget(self.tab, 1)

        # ---- từng file: nhận là gì, mở màn hình nào
        self.b_file = QTableWidget(len(kq.tung_file), 4)
        self.b_file.setHorizontalHeaderLabels(['File', 'Nhận là (đổi được)', 'Xử lý tiếp', 'Cách đọc, chất lượng'])
        cl = {c.get('file'): c for c in kq.chat_luong}
        self.b_file.verticalHeader().setVisible(False)
        self.b_file.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.b_file.horizontalHeader().setStretchLastSection(True)
        self.o_loai, self.nut_mo = [], []
        for i, f in enumerate(kq.tung_file):
            self.b_file.setItem(i, 0, QTableWidgetItem(f['file'].name))
            cb = QComboBox()
            for ma, ten, _ in qc.DICH:
                cb.addItem(ten, ma)
            cb.setCurrentIndex(max(0, cb.findData(f['loai'])))
            b = QPushButton()
            cb.currentIndexChanged.connect(lambda *_, k=i: self._dat_nut_file(k))
            b.clicked.connect(lambda *_, k=i: self._mo_file(k))
            self.b_file.setCellWidget(i, 1, cb)
            self.b_file.setCellWidget(i, 2, b)
            c = cl.get(f['file'].name) or {}
            chu_cl = (f'{c.get("cach_doc", "")}; {vn(c.get("ky_tu", 0))} ký tự' + (' - ' + ' '.join(c['canh_bao']) if c.get('canh_bao') else ' - đọc tốt')) if c else ''
            it = QTableWidgetItem(chu_cl)
            it.setToolTip(chu_cl)
            self.b_file.setItem(i, 3, it)
            self.o_loai.append(cb)
            self.nut_mo.append(b)
        self.b_file.resizeColumnsToContents()
        # 1.0.90: tên file dài không bóp cột nút; cột Cách đọc, chất lượng nhận phần còn lại
        self.b_file.setColumnWidth(0, min(self.b_file.columnWidth(0), 380))
        self.b_file.setColumnWidth(2, max([self.b_file.columnWidth(2)] + [b.sizeHint().width() + 24 for b in self.nut_mo] +
                                          [b.fontMetrics().horizontalAdvance(f'Đã mở: {v}') + 28 for b in self.nut_mo[:1] for v in qc.VIEC_LOAI.values()]))
        self.tab.addTab(self.b_file, f'Từng file ({len(kq.tung_file)})')

        self.o_can_cu = QPlainTextEdit()
        self.o_can_cu.setReadOnly(True)
        self.o_can_cu.setPlainText(vb.gop_va_sap_xep(kq.can_cu)[0] if kq.can_cu else '(Không thấy văn bản căn cứ trong file.)')
        self.tab.addTab(self.o_can_cu, f'Văn bản căn cứ ({len(kq.can_cu)})')
        self.b_dat = _bang(['Tờ', 'Thửa', 'Loại đất', 'Nhóm đất', 'Diện tích (m²)', 'Mặt đường'],
                           [(d.to_ban_do, d.so_thua, d.loai_dat, TEN_NHOM.get(d.nhom_dat, d.nhom_dat), vn(d.dien_tich_thu_hoi, 1),
                             TEN_KET_CAU.get(d.ket_cau_mat_duong, '')) for d in kq.dong_dat])
        self.tab.addTab(self.b_dat, f'Thửa đất ({len(kq.dong_dat)})')
        if kq.dong_dan:
            self.b_ts = _bang(['Dòng tài sản (sẽ tự xếp mục, khớp danh mục đơn giá ở bước sau)'], [(x,) for x in kq.dong_dan])
            so_ts = len(kq.dong_dan)
        else:
            self.b_ts = _bang(['Nhóm', 'Tên tài sản / cây trồng', 'ĐVT', 'Khối lượng', 'Đơn giá', 'Thành tiền'],
                              [('Cây trồng' if t.danh_muc == 'CAY_TRONG_HOA_MAU' else 'Nhà & VKT', t.ten, t.dvt, vn(t.so_luong, 2), vn(t.don_gia),
                                vn(t.thanh_tien)) for t in kq.dong_tai_san])
            so_ts = len(kq.dong_tai_san)
        self.tab.addTab(self.b_ts, f'Tài sản, cây trồng ({so_ts})')
        self.o_tom_tat = QPlainTextEdit()
        self.o_tom_tat.setReadOnly(True)
        dong = list(kq.tom_tat)
        if kq.tham_so:
            dong.append('Thông số nhận diện: ' + '; '.join(f'{k} = {v}' for k, v in kq.tham_so.items()))
        dong += [f'Không đọc được: {x}' for x in kq.loi]
        self.o_tom_tat.setPlainText('\n'.join(dong) or '(Không nhận dạng được nội dung nào.)')
        self.tab.addTab(self.o_tom_tat, 'Nhật ký quét')
        self.o_toan_van = QPlainTextEdit()
        self.o_toan_van.setReadOnly(True)
        phan = []
        if kq.quy_tac:
            phan.append('Quy định, đơn giá, quy tắc trích từ file (đối chiếu với toàn văn phía dưới):')
            phan.extend(f'{i}. {c}' for i, c in enumerate(kq.quy_tac, 1))
            phan.append('')
        phan.append('Toàn văn đã đọc:')
        phan.append(kq.toan_van[:120000] if kq.toan_van else '(Không có chữ.)')
        if len(kq.toan_van) > 120000:
            phan.append('… (đã rút phần hiện; phần tính vẫn dùng đủ chữ đã đọc)')
        self.o_toan_van.setPlainText('\n'.join(phan))
        self.tab.addTab(self._khung_toan_van(), f'Nội dung ({len(kq.quy_tac)})')
        self.tab.addTab(self._khung_cau_truc(), f'Cấu trúc văn bản ({len(kq.cau_truc)})')

        # ---- đưa vào hộ
        self._sua_duoc = co_du_an and not chi_doc
        self.cb_ho = QComboBox()
        from .giao_dien import nap_o_chon
        nap_o_chon(self.cb_ho, [(f'{ma} - {ten}', ma, '') for ma, ten in ds_ho])
        if ma_ho is not None:
            self.cb_ho.setCurrentIndex(max(0, self.cb_ho.findData(ma_ho)))
        self.b_dua = QPushButton('Đưa vào phương án của hộ')
        self.b_dua.setToolTip('Thêm dòng đất theo tờ + thửa, tài sản qua hộp Dán danh sách tài sản. Chưa ghi vào file: soát rồi bấm Lưu ở cửa sổ phương án.')
        self.b_dua.setEnabled(self._sua_duoc and kq.co_du_lieu_ho() and self.cb_ho.count() > 0)
        self.b_dua.clicked.connect(lambda: self._chon('dua_vao_ho'))
        hang = QHBoxLayout()
        nhan = QLabel('Hộ:')
        nhan.setProperty('vai', 'nhan')
        hang.addWidget(nhan)
        hang.addWidget(self.cb_ho, 1)
        hang.addWidget(self.b_dua)
        lo.addLayout(hang)

        nut = QDialogButtonBox()
        self.b_ghi = QPushButton('Ghi văn bản căn cứ vào dự án')
        self.b_ghi.setEnabled(bool(kq.can_cu) and self._sua_duoc)
        self.b_ghi.setToolTip('Gộp vào mục Văn bản căn cứ của dự án, khử trùng lặp và sắp theo 13 bậc hiệu lực pháp lý')
        self.b_ghi.clicked.connect(lambda: self._chon('ghi_can_cu'))
        self.b_tinh = QPushButton('Mở bảng tính đơn giá đất…')
        self.b_tinh.setEnabled(bool(kq.tham_so or kq.dong_dat or kq.can_cu))
        self.b_tinh.clicked.connect(lambda: self._chon('tinh_gia'))
        self.b_luu_qt = QPushButton('Lưu quy tắc toàn văn để tính giá')
        self.b_luu_qt.setEnabled(bool(kq.nq_chu))
        self.b_luu_qt.setToolTip('Ghi quy tắc đọc từ nghị quyết bảng giá đất vào máy này. Bảng tính đơn giá đang mở dùng ngay. Không gửi file ra ngoài.')
        self.b_luu_qt.clicked.connect(self._luu_quy_tac)
        nut.addButton(self.b_ghi, QDialogButtonBox.ButtonRole.ActionRole)
        nut.addButton(self.b_tinh, QDialogButtonBox.ButtonRole.ActionRole)
        nut.addButton(self.b_luu_qt, QDialogButtonBox.ButtonRole.ActionRole)
        dong_b = nut.addButton('Đóng', QDialogButtonBox.ButtonRole.RejectRole)
        dong_b.clicked.connect(self.reject)
        lo.addWidget(nut)
        for k in range(len(self.nut_mo)):
            self._dat_nut_file(k)

    # ---------------------------------------------------------------- 1.0.90: tìm trong toàn văn, dàn ý phân cấp có lọc
    def _khung_toan_van(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(0, 4, 0, 0)
        hang = QHBoxLayout()
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm trong nội dung (Enter: chỗ tiếp theo)')
        self.o_tim.returnPressed.connect(lambda: self.tim_tiep())
        self.lb_tim = QLabel('')
        b_luu = QPushButton('Lưu nội dung ra file .txt…')
        b_luu.setToolTip('Ghi toàn văn đã đọc ra file chữ (UTF-8) để đối chiếu, lưu hồ sơ')
        b_luu.clicked.connect(lambda: self.luu_toan_van())
        hang.addWidget(self.o_tim, 1)
        hang.addWidget(self.lb_tim)
        hang.addWidget(b_luu)
        lo.addLayout(hang)
        lo.addWidget(self.o_toan_van, 1)
        return w

    def tim_tiep(self, chu: str | None = None) -> bool:
        """Tìm chữ (có phân biệt dấu như người gõ) từ vị trí con trỏ; hết thì quay lại đầu. True: tìm thấy."""
        from PySide6.QtGui import QTextCursor
        chu = self.o_tim.text() if chu is None else chu
        if not chu.strip():
            return False
        thay = self.o_toan_van.find(chu)
        if not thay:
            self.o_toan_van.moveCursor(QTextCursor.MoveOperation.Start)
            thay = self.o_toan_van.find(chu)
        self.lb_tim.setText('' if thay else 'Không thấy')
        return thay

    def luu_toan_van(self, file=None):
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu nội dung đã đọc', 'NoiDungDaQuet.txt', 'Văn bản (*.txt)')
        if not file:
            return None
        from pathlib import Path
        Path(file).write_text(self.o_toan_van.toPlainText(), encoding='utf-8-sig')
        return file

    def _khung_cau_truc(self) -> QWidget:
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(0, 4, 0, 0)
        hang = QHBoxLayout()
        self.o_loc_ct = QLineEdit()
        self.o_loc_ct.setPlaceholderText('Lọc theo chữ (không dấu cũng được): "bồi thường", "hệ số", "điều 5"…')
        self.cb_cap = QComboBox()
        self.cb_cap.addItem('Mọi cấp', 0)
        for c, ten in qc.TEN_CAP.items():
            self.cb_cap.addItem(ten, c)
        hang.addWidget(self.o_loc_ct, 1)
        hang.addWidget(self.cb_cap)
        lo.addLayout(hang)
        self.cay = QTreeWidget()
        self.cay.setHeaderLabels(['Cấp', 'Nội dung', 'Dòng', 'File'])
        self.cay.setRootIsDecorated(True)
        self.cay.setUniformRowHeights(True)
        cha = {}                                         # cấp -> mục cây gần nhất
        for x in self.kq.cau_truc:
            it = QTreeWidgetItem([x['nhan'], x['chu'], str(x['dong']), x['file']])
            it.setToolTip(1, x['chu'])
            it.setData(0, Qt.ItemDataRole.UserRole, x['cap'])
            cha_it = next((cha[c] for c in range(x['cap'] - 1, 0, -1) if c in cha and x['cap'] != 6), None)
            (cha_it.addChild(it) if cha_it is not None else self.cay.addTopLevelItem(it))
            cha[x['cap']] = it
            for c in [c for c in cha if c > x['cap']]:
                del cha[c]
        self.cay.expandToDepth(1)
        self.cay.setColumnWidth(0, 120)
        self.cay.setColumnWidth(1, 560)
        lo.addWidget(self.cay, 1)
        if not self.kq.cau_truc:
            lo.addWidget(QLabel('Không thấy Phần / Chương / Điều / Khoản / Bảng trong file (văn bản không chia điều, hoặc ảnh chưa nhận dạng).'))
        self.o_loc_ct.textChanged.connect(lambda *_: self.loc_cau_truc())
        self.cb_cap.currentIndexChanged.connect(lambda *_: self.loc_cau_truc())
        return w

    def loc_cau_truc(self) -> int:
        """Ẩn mục không khớp chữ lọc (không dấu) / cấp; mục cha của mục khớp vẫn hiện. Trả số mục khớp."""
        from .lap_pa import bo_dau
        k = bo_dau(self.o_loc_ct.text()).split()
        cap = self.cb_cap.currentData() or 0
        khop = 0
        ds = []

        def duyet(x):
            ds.append(x)
            for j in range(x.childCount()):
                duyet(x.child(j))
        for j in range(self.cay.topLevelItemCount()):
            duyet(self.cay.topLevelItem(j))
        for x in ds:
            chu = bo_dau(f'{x.text(0)} {x.text(1)}')
            dung = all(t in chu for t in k) and (not cap or x.data(0, Qt.ItemDataRole.UserRole) == cap)
            x.setHidden(not dung)
            khop += dung
        for x in ds:                                     # hiện đường dẫn tới mục khớp
            if not x.isHidden():
                p = x.parent()
                while p is not None:
                    p.setHidden(False)
                    p = p.parent()
        return khop

    def ho_chon(self):
        return self.cb_ho.currentData()

    def _dat_nut_file(self, k: int) -> None:
        """Chữ + trạng thái nút theo loại đang chọn của dòng k. Việc cần dự án / quyền sửa thì tắt và nói rõ."""
        loai = self.o_loai[k].currentData()
        b = self.nut_mo[k]
        b.setText(qc.VIEC_LOAI.get(loai, ''))
        ok = loai in self.LOAI_CON_VIEC
        ly_do = ''
        if self.kq.tung_file[k].get('da_xu_ly'):
            b.setText('Đã mở: ' + qc.VIEC_LOAI.get(loai, ''))
        if loai in (qc.D_HO_SO, qc.D_CHI_TIET) and not self._sua_duoc:
            ok, ly_do = False, 'Cần mở dự án (không ở chế độ chỉ xem).'
        elif loai == qc.D_HO_SO and not self.kq.co_du_lieu_ho():
            ok, ly_do = False, 'Không bóc được thửa hay tài sản từ file này.'
        elif loai == qc.D_CAN_CU:
            ly_do = 'Dùng nút "Ghi văn bản căn cứ vào dự án" ở dưới.'
        b.setEnabled(ok)
        b.setToolTip(ly_do)

    def _mo_file(self, k: int) -> None:
        self.file_chon = self.kq.tung_file[k]['file']
        self.loai_chon = self.o_loai[k].currentData()
        self._chon('mo_file')

    def _luu_quy_tac(self) -> None:
        from .man_hinh_don_gia import xin_quyen_sua
        from .quy_tac_vi_tri import doc_toan_van_nghi_quyet
        # 1.0.90: quy tắc toàn văn NQ 28 là dữ liệu giá đất dùng chung của máy (bảng tính đọc hệ số): cần quyền như bảng giá, hệ số K
        if not xin_quyen_sua(self, self.im_lang):
            if not self.im_lang:
                QMessageBox.information(self, TIEU_DE, 'Chưa lưu: cần quyền quản trị bộ đơn giá / bảng giá đất để cập nhật quy tắc giá đất.')
            return
        try:
            kq = doc_toan_van_nghi_quyet(self.kq.nq_chu, luu=True)
        except (OSError, ValueError) as e:
            if not self.im_lang:
                QMessageBox.warning(self, TIEU_DE, f'Chưa lưu được quy tắc toàn văn.\n{e}')
            return
        self.b_luu_qt.setEnabled(False)
        self.b_luu_qt.setText('Đã lưu quy tắc toàn văn')
        if not self.im_lang:
            QMessageBox.information(self, TIEU_DE, f'Đã lưu {len(kq.get("quy_tac") or [])} quy tắc của {len(kq.get("dieu") or [])} điều. '
                                    'Bảng tính đơn giá đất đang mở dùng ngay các hệ số này.')

    def _chon(self, hanh_dong: str) -> None:
        self.hanh_dong = hanh_dong
        self.accept()


class HopVanBanCanCu(QDialog):
    """Mục Văn bản căn cứ của dự án: quét thêm / sửa -> tự khử trùng lặp, sắp 13 bậc hiệu lực. Dùng chung nội dung với cửa sổ tính giá đất."""
    im_lang = False

    def __init__(self, parent, con, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc = con, chi_doc
        self.setWindowTitle('Văn bản căn cứ của dự án (13 bậc hiệu lực pháp lý)')
        self.resize(880, 520)
        lo = QVBoxLayout(self)
        self.o = QPlainTextEdit()
        self.o.setPlainText(vb.doc_can_cu_du_an(con))
        lo.addWidget(self.o, 1)
        nut = QDialogButtonBox()
        self.b_quet = NutQuetChung('Quét thêm văn bản…', qc.CAN_CU, self)
        self.b_quet.da_quet.connect(self.them)
        self.b_sap = QPushButton('Sắp xếp lại')
        self.b_sap.clicked.connect(lambda: self.them())
        self.b_luu = QPushButton('Lưu vào dự án')
        self.b_luu.setEnabled(not chi_doc)
        self.b_luu.clicked.connect(lambda: self.luu())
        nut.addButton(self.b_quet, QDialogButtonBox.ButtonRole.ActionRole)
        nut.addButton(self.b_sap, QDialogButtonBox.ButtonRole.ActionRole)
        nut.addButton(self.b_luu, QDialogButtonBox.ButtonRole.AcceptRole)
        nut.addButton('Đóng', QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self.reject)
        lo.addWidget(nut)

    def them(self, kq=None) -> None:
        self.o.setPlainText(vb.gop_va_sap_xep([self.o.toPlainText()], kq.can_cu if kq is not None else ())[0])

    def luu(self) -> bool:
        from .loi import LoiNhap
        try:
            self.o.setPlainText(vb.ghi_can_cu_du_an(self.con, self.o.toPlainText()))
        except LoiNhap as e:
            if not self.im_lang:
                QMessageBox.warning(self, TIEU_DE, str(e))
            return False
        self.accept()
        return True
