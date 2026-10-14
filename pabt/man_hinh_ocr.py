"""Cửa sổ "Quét giấy tờ (OCR)" (0.9.87): chọn ảnh chụp / PDF của Giấy chứng nhận QSDĐ, biên bản kiểm kê -> nhận dạng chữ (ocr_ho_so) ->
soát / sửa trên bảng -> điền vào cửa sổ đang mở. Dùng ở Lập phương án hộ (CuaSoLapPA: thông tin hộ, thửa đất, tài sản) và Khái toán &
dự toán (KhungDuToan: dòng đất, tài sản). Không ghi gì vào dự án khi chưa bấm Lưu ở cửa sổ đích."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from . import ocr_ho_so
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, chu_loi
from .tien import so_vn

COT_THUA = ['Lấy', 'Tờ', 'Thửa', 'Diện tích (m²)', 'Loại đất', 'Địa chỉ thửa']


class HopQuetGiayTo(QDialog):
    """dich: 'lap_pa' (cua_so = CuaSoLapPA) hoặc 'du_toan' (cua_so = KhungDuToan)."""
    im_lang = False

    def __init__(self, cua_so, dich: str = 'lap_pa', parent=None, files=None):
        super().__init__(parent or cua_so)
        self.cua_so, self.dich = cua_so, dich
        self.kq = ocr_ho_so.KetQuaOcr()
        self.setWindowTitle('Quét giấy tờ (OCR) - Giấy chứng nhận QSDĐ, biên bản kiểm kê')
        self.resize(1200, 720)
        b_chon = QPushButton('Chọn ảnh chụp / PDF…')
        b_chon.setToolTip('Ảnh chụp bằng điện thoại (.jpg, .png - chép qua Zalo / cáp), PDF scan hoặc PDF có chữ. Chọn được nhiều file '
                          '(mặt trước, mặt sau, nhiều trang biên bản).')
        b_chon.clicked.connect(lambda: self.chon())
        self.lb_file = QLabel('Chưa chọn file.')
        self.lb_file.setWordWrap(True)
        h = QHBoxLayout()
        h.addWidget(b_chon)
        h.addWidget(self.lb_file, 1)
        # trái: chữ nhận dạng (sửa được) ; phải: kết quả bóc tách
        self.o_chu = QPlainTextEdit()
        self.o_chu.setPlaceholderText('Chữ nhận dạng được hiện ở đây - sửa chỗ sai rồi bấm "Bóc tách lại".')
        b_lai = QPushButton('Bóc tách lại từ chữ')
        b_lai.clicked.connect(lambda: self.boc_tach_lai())
        trai = QWidget()
        lt = QVBoxLayout(trai)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.addWidget(QLabel('Chữ nhận dạng:'))
        lt.addWidget(self.o_chu, 1)
        lt.addWidget(b_lai)
        self.o_ten, self.o_cccd, self.o_dc = QLineEdit(), QLineEdit(), QLineEdit()
        f = QFormLayout()
        f.addRow('Họ và tên:', self.o_ten)
        f.addRow('Số CCCD:', self.o_cccd)
        f.addRow('Địa chỉ:', self.o_dc)
        self.bang = QTableWidget(0, len(COT_THUA))
        self.bang.setHorizontalHeaderLabels(COT_THUA)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.o_ts = QPlainTextEdit()
        self.o_ts.setPlaceholderText('Tài sản (mỗi dòng: Tên  ĐVT  Số lượng) - sửa được, phân loại ở bước sau.')
        phai = QWidget()
        lp = QVBoxLayout(phai)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.addLayout(f)
        lp.addWidget(QLabel('Thửa đất:'))
        lp.addWidget(self.bang, 2)
        lp.addWidget(QLabel('Tài sản, cây trồng (biên bản kiểm kê):'))
        lp.addWidget(self.o_ts, 1)
        tach = QSplitter(Qt.Orientation.Horizontal)
        tach.addWidget(trai)
        tach.addWidget(phai)
        tach.setSizes([480, 720])
        self.lb = QLabel('Nhận dạng chữ in bằng Tesseract trên máy (không gửi giấy tờ ra ngoài). Chữ viết tay đọc không được / sai nhiều: '
                         'soát lại trước khi điền.')
        self.lb.setWordWrap(True)
        self.b_ho = QPushButton('Điền thông tin hộ && thửa' if dich == 'lap_pa' else 'Thêm dòng đất')
        self.b_ho.clicked.connect(lambda: self.dien_ho_thua())
        self.b_ts = QPushButton('Đưa tài sản vào phương án…' if dich == 'lap_pa' else 'Đưa tài sản vào khái toán…')
        self.b_ts.clicked.connect(lambda: self.dua_tai_san())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addStretch(1)
        hn.addWidget(self.b_ho)
        hn.addWidget(self.b_ts)
        hn.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        lo.addWidget(tach, 1)
        lo.addWidget(self.lb)
        lo.addLayout(hn)
        self._bat_nut()
        if files:
            self.doc(files)

    # ---- đọc
    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            self.lb.setText(chu)
        else:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def chon(self) -> bool:
        ds, _ = QFileDialog.getOpenFileNames(self, 'Chọn ảnh chụp / PDF giấy tờ', str(Path.home() / 'Downloads'),
                                             'Ảnh, PDF (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.pdf)')
        return self.doc(ds) if ds else False

    def doc(self, files) -> bool:
        files = [Path(f) for f in files]
        tien = None if self.im_lang else QProgressDialog('Đang nhận dạng chữ…', 'Dừng', 0, 0, self)
        if tien is not None:
            tien.setWindowTitle(TEN_UD)
            tien.setWindowModality(Qt.WindowModality.WindowModal)
            tien.setMinimumDuration(300)

        def bao(i, n):
            if tien is not None:
                tien.setMaximum(n)
                tien.setValue(i)
                QApplication.processEvents()

        def huy():
            QApplication.processEvents()
            return tien is not None and tien.wasCanceled()
        ds_kq, chu_all, loi = [], [], []
        from . import ocr
        try:
            with con_tro_cho():
                for f in files:
                    if tien is not None:
                        tien.setLabelText(f'Đang nhận dạng: {f.name}…')
                    try:
                        kq, chu, da_ocr = ocr_ho_so.doc_va_boc_tach(f, bao, huy)
                    except ocr.DaHuy:
                        raise
                    except Exception as e:                       # noqa: BLE001 - lỗi từng file: báo, đọc tiếp file khác
                        loi.append(chu_loi(f'{f.name}', e))
                        continue
                    ds_kq.append(kq)
                    chu_all.append(f'===== {f.name}{" (nhận dạng ảnh)" if da_ocr else ""} =====\n{chu}')
        except ocr.DaHuy:
            loi.append('Đã dừng nhận dạng.')
        finally:
            if tien is not None:
                tien.close()
                tien.deleteLater()
        self.lb_file.setText(', '.join(f.name for f in files))
        if not ds_kq:
            self._bao('Không đọc được file nào:\n' + '\n'.join(loi), True)
            return False
        self.o_chu.setPlainText('\n\n'.join(chu_all))
        self.hien(ocr_ho_so.gop(ds_kq), loi)
        return True

    def boc_tach_lai(self) -> None:
        self.hien(ocr_ho_so.boc_tach(self.o_chu.toPlainText()))

    def hien(self, kq: ocr_ho_so.KetQuaOcr, loi: list | None = None) -> None:
        self.kq = kq
        self.o_ten.setText(kq.ho_ten)
        self.o_cccd.setText(kq.so_cccd)
        self.o_dc.setText(kq.dia_chi)
        self.bang.setRowCount(len(kq.thua))
        for r, t in enumerate(kq.thua):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.bang.setItem(r, 0, chk)
            for c, v in enumerate((t['so_to'], t['so_thua'], '' if t['dt_thu_hoi'] is None else so_vn(t['dt_thu_hoi']),
                                   t['loai_dat'], t.get('dia_chi_thua', '')), start=1):
                self.bang.setItem(r, c, QTableWidgetItem(str(v)))
        self.o_ts.setPlainText('\n'.join(kq.dong_tai_san))
        ten = {'gcn': 'Giấy chứng nhận QSDĐ', 'bien_ban': 'Biên bản kiểm kê'}.get(kq.loai, 'Giấy tờ')
        self.lb.setText(f'{ten}: {len(kq.thua)} thửa, {len(kq.dong_tai_san)} dòng tài sản.' +
                        ('\n' + '\n'.join((loi or []) + kq.canh_bao) if (loi or kq.canh_bao) else ''))
        self._bat_nut()

    def _bat_nut(self) -> None:
        self.b_ho.setEnabled(self.bang.rowCount() > 0 or bool(self.o_ten.text().strip()))
        self.b_ts.setEnabled(bool(self.o_ts.toPlainText().strip()) or self.bang.rowCount() == 0)

    # ---- đọc bảng
    def thua_da_chon(self) -> list:
        from .lap_pa import LoiNhap, doc_so
        kq = []
        for r in range(self.bang.rowCount()):
            if self.bang.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            g = [self.bang.item(r, c).text().strip() if self.bang.item(r, c) else '' for c in range(1, len(COT_THUA))]
            try:
                dt = doc_so(g[2], 'Diện tích') if g[2] else None
            except LoiNhap:                                      # người dùng gõ sai ô diện tích: coi như chưa có
                dt = None
            kq.append(dict(so_to=g[0], so_thua=g[1], dt_thu_hoi=dt, loai_dat=g[3], dia_chi_thua=g[4]))
        return kq

    # ---- điền vào cửa sổ đích
    def dien_ho_thua(self) -> int:
        """Lập phương án: điền họ tên / CCCD / địa chỉ (ô trống hoặc người dùng đồng ý ghi đè) + thêm dòng thửa vào thẻ Thông tin hộ.
        Khái toán: thêm dòng đất (loại đất, diện tích). Trả số thửa đã thêm."""
        ds = self.thua_da_chon()
        if self.dich == 'du_toan':
            n, bo = 0, []
            for t in ds:
                ma = (t['loai_dat'] or '').split('+')[0]
                if not ma or t['dt_thu_hoi'] is None:
                    bo.append(t['so_thua'])
                    continue
                if self.cua_so.them_dat(ma, so_vn(t['dt_thu_hoi'])) is not None:
                    n += 1
            self._bao(f'Đã thêm {n} dòng đất vào bảng khái toán (đơn giá: tra NQ 28 hoặc nhập).' +
                      (f'\nBỏ qua thửa thiếu loại đất / diện tích: {", ".join(bo)}' if bo else ''))
            return n
        hs = self.cua_so.ho_so
        moi = {'ho_ten': self.o_ten.text().strip(), 'so_cccd': self.o_cccd.text().strip(), 'dia_chi': self.o_dc.text().strip()}
        khac = [k for k, v in moi.items() if v and hs.o[k].text().strip() and hs.o[k].text().strip() != v]
        ghi_de = True
        if khac and not self.im_lang:
            ghi_de = QMessageBox.question(self, TEN_UD, 'Hồ sơ hộ đã có ' + ', '.join({'ho_ten': 'họ tên', 'so_cccd': 'số CCCD',
                                          'dia_chi': 'địa chỉ'}[k] for k in khac) + ' khác giấy tờ. Ghi đè bằng thông tin trên giấy tờ?') \
                == QMessageBox.StandardButton.Yes
        for k, v in moi.items():
            if v and (ghi_de or not hs.o[k].text().strip()):
                hs.o[k].setText(v)
        co = {(str(hs.bang.item(r, hs.cot.index('so_to')).text() if hs.bang.item(r, hs.cot.index('so_to')) else '').strip(),
               str(hs.bang.item(r, hs.cot.index('so_thua')).text() if hs.bang.item(r, hs.cot.index('so_thua')) else '').strip())
              for r in range(hs.bang.rowCount())}
        n = 0
        for t in ds:
            if (t['so_to'], t['so_thua']) in co:
                continue                                       # thửa đã có trong hồ sơ: không thêm trùng
            hs.them_dong(dict(so_to=t['so_to'], so_thua=t['so_thua'], loai_dat=t['loai_dat'],
                              dt_thu_hoi='' if t['dt_thu_hoi'] is None else t['dt_thu_hoi']))
            n += 1
        self.cua_so.tab.setCurrentIndex(0)
        self._bao(f'Đã điền thông tin hộ và thêm {n} thửa vào thẻ "Thông tin hộ" (chưa lưu - soát rồi bấm Lưu).')
        return n

    def dua_tai_san(self):
        """Mở hộp "Dán danh sách tài sản" với các dòng tài sản (tự phân loại nhà / cây / vật nuôi / hỗ trợ)."""
        chu = self.o_ts.toPlainText().strip()
        if not chu:
            self._bao('Không có dòng tài sản nào.', True)
            return None
        self.accept()
        return self.cua_so.dan_tai_san(chu, cho=not self.im_lang)
