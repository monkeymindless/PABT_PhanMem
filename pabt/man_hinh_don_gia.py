"""Màn hình "Bộ đơn giá": xem (chỉ đọc) danh mục đơn giá, chính sách hỗ trợ, tham số - hạn mức, biểu thưởng, văn bản căn cứ;
cập nhật bộ đơn giá từ file hoặc qua Internet; tra cứu văn bản mới; áp bộ đơn giá vào dự án đang mở."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout)

from . import csdl, don_gia
from .lap_pa import LoiNhap, bo_dau
from .tien import vn
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, chu_loi

_TS = 'SELECT ma, phan_loai, ten, dvt, don_gia, ghi_chu FROM dm_taisan WHERE '
_COT_TS = (['Mã', 'Phân loại', 'Tên', 'ĐVT', 'Đơn giá (đ)', 'Ghi chú'], [70, 240, 420, 80, 110, 300])
# vật nuôi (mục 3 của phương án như cây trồng): mã VN.. của bộ tích hợp (QĐ 31/2025/QĐ-UBND) hoặc mục cập nhật từ văn bản vật
# nuôi (nhap_don_gia.ap_dung ghi phân loại PHAN_LOAI_VAT_NUOI) - thẻ riêng để thấy ngay, không lẫn trong 5.500 dòng cây trồng
_VAT_NUOI = f"(ma LIKE 'VN%' OR phan_loai LIKE '{don_gia.PHAN_LOAI_VAT_NUOI}%')"
THE = [
    ('Nhà, công trình', _TS + 'nhom <> 3 ORDER BY nhom, rowid', *_COT_TS),
    ('Cây trồng', _TS + f'nhom = 3 AND NOT {_VAT_NUOI} ORDER BY rowid', *_COT_TS),
    ('Vật nuôi', _TS + f'nhom = 3 AND {_VAT_NUOI} ORDER BY ma', *_COT_TS),
    ('Chính sách hỗ trợ (QĐ 42/2025)', 'SELECT ma, ten, dvt, don_gia, can_cu, cach_tinh FROM dm_hotro',
     ['Mã', 'Khoản hỗ trợ', 'ĐVT', 'Đơn giá / hệ số', 'Căn cứ', 'Cách tính'], [55, 420, 90, 110, 330, 330]),
    ('Tham số, hạn mức đất NN', 'SELECT ma, ten, gia_tri, dvt, can_cu, trang_thai FROM tham_so',
     ['Mã', 'Tham số', 'Giá trị', 'ĐVT', 'Căn cứ', 'Trạng thái'], [120, 430, 90, 90, 330, 160]),
    ('Thưởng bàn giao mặt bằng', 'SELECT tu, muc FROM bieu_thuong ORDER BY CAST(tu AS REAL)',
     ['Tổng bồi thường, hỗ trợ từ (đ)', 'Mức thưởng (đ/hộ)'], [220, 180]),
    ('Quy ước giá tương đương', 'SELECT ten_thuc_te, ten_tuong_duong, dvt, don_gia, can_cu FROM quy_uoc',
     ['Tên thực tế', 'Áp giá tương đương', 'ĐVT', 'Đơn giá', 'Căn cứ'], [260, 300, 70, 110, 330]),
    ('Văn bản căn cứ', 'SELECT so_hieu, co_quan, noi_dung, trang_thai FROM van_ban ORDER BY id',
     ['Văn bản', 'Cơ quan', 'Nội dung áp dụng', 'Trạng thái'], [380, 200, 440, 230]),
]


class HopBoDonGia(QDialog):

    im_lang = False             # True: không hiện hộp thông báo (kiểm thử); nội dung lưu ở thong_bao_cuoi

    def _bao(self, ham, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            ham(self, TEN_UD, chu)
    def __init__(self, parent=None, con_du_an=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con_du_an = con_du_an
        self.chi_doc = chi_doc
        self.da_ap = False
        self.setWindowTitle('Bộ đơn giá bồi thường, hỗ trợ, tái định cư')
        self.resize(1300, 720)
        self.lb = QLabel()
        self.lb.setProperty('vai', 'bang_ten')
        self.lb.setWordWrap(True)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm trong thẻ đang xem (không cần dấu): xoai, nha cap 4, HT09…')
        self.o_tim.textChanged.connect(self.loc)
        self.the = QTabWidget()
        # hàng nút gọn (trước 0.9.17: 7 nút một hàng, chật ở màn hình 1366): lệnh cùng việc gom vào nút xổ, việc chính ở bên phải
        nut = QHBoxLayout()
        self.b_cap = QPushButton('Cập nhật đơn giá')
        self.b_cap.setToolTip('Cập nhật bộ đơn giá từ văn bản mới: file Excel / Word / PDF / CSV, hoặc tìm và tải trên trang web')
        m = QMenu(self.b_cap)
        m.addAction('Từ file (Excel, Word, PDF, CSV, gói .sqlite)…', lambda: self.cap_nhat_file())
        m.addAction('Từ trang web (Công báo Đồng Nai, CSDL văn bản pháp luật)…', lambda: self.cap_nhat_web())
        m.addSeparator()
        tra = m.addMenu('Tra cứu văn bản mới trên trình duyệt')
        for ten, url in don_gia.TRA_CUU:
            tra.addAction(ten, lambda u=url: QDesktopServices.openUrl(QUrl(u)))
        self.b_cap.setMenu(m)
        self.b_gia_dat = QPushButton('Giá đất NQ 28/2025')
        m = QMenu(self.b_gia_dat)
        m.addAction('Tra bảng giá đất…', lambda: self.xem_gia_dat())
        m.addAction('Xuất bảng giá đất ra Excel…', lambda: self.xuat_gia_dat())
        self.b_gia_dat.setMenu(m)
        self.b_don = QPushButton('Đơn giá riêng của dự án…')
        self.b_don.clicked.connect(lambda: self.don_gia_rieng())
        self.b_ap = QPushButton('Áp bộ đơn giá vào dự án đang mở')
        self.b_ap.clicked.connect(lambda: self.ap_du_an())
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        for b in (self.b_cap, self.b_gia_dat, self.b_don):
            nut.addWidget(b)
        nut.addStretch(1)
        nut.addWidget(self.b_ap)
        nut.addWidget(dong)
        self.b_ap.setEnabled(con_du_an is not None and not chi_doc)
        self.b_don.setEnabled(con_du_an is not None)
        self.b_don.setToolTip('Quy ước giá tương đương nhập tay, đơn giá thẩm định giá (tài sản đặc biệt) của dự án đang mở')
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.o_tim)
        lo.addWidget(self.the, 1)
        lo.addLayout(nut)
        self.nap()

    def nap(self):
        tt = don_gia.thong_tin()
        self.lb.setText(f'<b>{tt["ten"]}</b> – phiên bản <b>{tt["phien_ban"]}</b> (nguồn {tt["nguon"]}, đóng gói {tt["ngay"][:10]})<br>'
                        f'{tt["ghi_chu"]}<br>Danh mục, chính sách, tham số được cố định; chỉ thay đổi bằng nút "Cập nhật đơn giá" '
                        'bên dưới.')
        self.the.clear()
        self._khoa_the = {}                             # loc: chữ tìm từng dòng của mỗi thẻ (dựng lại khi nạp lại bộ đơn giá)
        con = csdl.mo(tt['file'], chi_doc=True)
        try:
            for ten, sql, cot, rong in THE:
                ds = con.execute(sql).fetchall()
                b = QTableWidget(len(ds), len(cot))
                b.setHorizontalHeaderLabels(cot)
                b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                b.setAlternatingRowColors(True)
                b.verticalHeader().setVisible(False)
                for c, w in enumerate(rong):
                    b.setColumnWidth(c, w)
                b.horizontalHeader().setStretchLastSection(True)
                for r, dong in enumerate(ds):
                    for c, v in enumerate(dong):
                        s = '' if v is None else str(v)
                        if cot[c].startswith(('Đơn giá', 'Mức thưởng', 'Tổng bồi')) and s.replace('.', '').isdigit() and float(s) >= 100:
                            s = vn(s)
                        it = QTableWidgetItem(s)
                        it.setToolTip(s)
                        b.setItem(r, c, it)
                self.the.addTab(b, f'{ten} ({len(ds)})')
        finally:
            con.close()

    def don_gia_rieng(self, cho: bool = True):
        """Quy ước tương đương / đơn giá thẩm định riêng của dự án đang mở (bộ đơn giá chung vẫn cố định)."""
        from .man_hinh_don_gia_rieng import HopDonGiaRieng
        if self.con_du_an is None:
            return None
        d = HopDonGiaRieng(self.con_du_an, self, chi_doc=self.chi_doc)
        d.im_lang = self.im_lang
        if not cho:
            return d
        d.exec()
        if d.da_luu:
            self.da_ap = True                           # cửa sổ chính dựng lại danh mục của dự án
        return d

    def loc(self, chu: str):
        b = self.the.currentWidget()
        i = self.the.currentIndex()
        if i not in self._khoa_the:     # chữ không dấu từng dòng: tính một lần mỗi thẻ (trước: ghép lại 5.510 dòng × 6 ô mỗi phím)
            self._khoa_the[i] = ([bo_dau(' '.join(b.item(r, c).text() for c in range(b.columnCount()) if b.item(r, c)))
                                  for r in range(b.rowCount())], [False] * b.rowCount())
        khoa, an = self._khoa_the[i]
        tu = bo_dau(chu).split()
        b.setUpdatesEnabled(False)
        try:
            for r, k in enumerate(khoa):
                h = bool(tu) and not all(x in k for x in tu)
                if h != an[r]:                  # chỉ đổi dòng đổi trạng thái (setRowHidden từng dòng là phần tốn nhất)
                    b.setRowHidden(r, h)
                    an[r] = h
        finally:
            b.setUpdatesEnabled(True)

    def cap_nhat_file(self, p=None):
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn file đơn giá', '',
                                               'File đơn giá (*.xlsx *.xlsm *.docx *.pdf *.csv *.sqlite);;Tất cả (*.*)')
            if not p:
                return None
        from .nhap_tho import la_file_pabt
        if Path(p).suffix.lower() != '.sqlite' and not (Path(p).suffix.lower() in ('.xlsx', '.xlsm') and la_file_pabt(p)):
            return self.cap_nhat_file_bat_ky(p)
        try:
            with con_tro_cho():
                tt = don_gia.cap_nhat_tu_file(p)
        except Exception as e:
            self._bao(QMessageBox.warning, chu_loi('Không cập nhật được', e))
            return None
        self.nap()
        self._bao(QMessageBox.information, f'Đã cập nhật bộ đơn giá phiên bản {tt["phien_ban"]}. Dự án mới dùng bộ này; '
                                              'dự án đang lập muốn đổi thì bấm "Áp bộ đơn giá vào dự án đang mở".')
        return tt

    def cap_nhat_file_bat_ky(self, p, nguon: str = '', cho: bool = True):
        """File Excel / Word / PDF / CSV bất kỳ: xem trước các dòng đơn giá rồi áp dụng."""
        from . import nhap_don_gia as ndg, ocr
        from .man_hinh_nhap_don_gia import HopNhapDonGia
        from .man_hinh_quan_ly import doc_co_tien_do
        try:
            dong = doc_co_tien_do(self, ndg.doc_bang_ocr, p)        # PDF scan: nhận dạng chữ từng trang, có nút Hủy
            d = HopNhapDonGia(p, self, nguon, dong=dong)
        except ocr.DaHuy:
            return None
        except (LoiNhap, ocr.LoiOCR, OSError, ValueError) as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        d.im_lang = self.im_lang
        if not cho:
            return d
        if d.exec() and d.ket_qua:
            self.nap()
        return d.ket_qua

    def cap_nhat_web(self, url=None, cho: bool = True):
        """Quét trang web / tìm trên Công báo Đồng Nai, tải và phân tích văn bản đơn giá, chính sách (HopQuetWeb).
        Đường dẫn thông báo cập nhật bộ đơn giá (.json) đi theo cap_nhat_mang."""
        if url and url.strip().lower().split('?')[0].endswith('.json'):
            return self.cap_nhat_mang(url.strip())
        try:
            from .man_hinh_quet_web import HopQuetWeb   # phát hành riêng bằng gói cập nhật, không có trong bộ cài gốc
        except ImportError:
            self._bao(QMessageBox.information,
                      'Tính năng "Cập nhật từ trang web" (tự quét Công báo Đồng Nai, tải và phân tích văn bản đơn giá, chính '
                      'sách) được phát hành riêng bằng gói cập nhật phần mềm (PABT_CapNhat_<phiên bản>.pabtcn), không có sẵn '
                      'trong bộ cài.\n\nCài gói: bấm đúp file .pabtcn, hoặc nút "Cập nhật phần mềm" ở góc dưới bên phải → '
                      '"Cập nhật từ file…", rồi mở lại PABT.\n\nVẫn cập nhật được từ file đã tải về máy: "Cập nhật bộ đơn giá '
                      'từ file…".')
            return None
        d = HopQuetWeb(self, url or '')
        d.im_lang = self.im_lang
        if url:
            d.quet(url)
        if not cho:
            return d
        d.exec()
        if d.ket_qua:
            self.nap()
        return d.ket_qua

    def cap_nhat_mang(self, url=None):
        if url is None:
            return self.cap_nhat_web()
        try:
            with con_tro_cho():                                 # hỏi nơi phát hành: có bộ đơn giá mới không
                tb = don_gia.kiem_tra_mang(url.strip())
            if tb is None:
                self._bao(QMessageBox.information, 'Bộ đơn giá đang dùng là mới nhất.')
                return None
            # hỏi người dùng ngoài khối chờ: con trỏ đã trở lại bình thường
            if QMessageBox.question(self, TEN_UD, f'Có bộ đơn giá phiên bản {tb["phien_ban"]}.\n{tb.get("ghi_chu", "")}\n\nTải và cài?') \
                    != QMessageBox.StandardButton.Yes:
                return None
            with con_tro_cho():
                tt = don_gia.tai_va_cai(tb)
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.nap()
        self._bao(QMessageBox.information, f'Đã cài bộ đơn giá phiên bản {tt["phien_ban"]}.')
        return tt

    def xem_gia_dat(self, cho: bool = True):
        from .man_hinh_gia_dat import HopTraGiaDat
        d = HopTraGiaDat(self, chi_xem=True)
        if cho:
            d.exec()
        return d

    def xuat_gia_dat(self, p=None):
        from . import gia_dat_nq28 as nq
        if p is None:
            p, _ = QFileDialog.getSaveFileName(self, 'Lưu bảng giá đất', 'BANG_GIA_DAT_NQ28_2025.xlsx', 'File Excel (*.xlsx)')
            if not p:
                return None
        try:
            f = nq.xuat_excel(p)
        except OSError as e:
            self._bao(QMessageBox.warning, chu_loi('Không ghi được file', e))
            return None
        self._bao(QMessageBox.information, f'Đã lưu bảng giá đất:\n{f}')
        return f

    def ap_du_an(self, xac_nhan=None):
        if self.con_du_an is None or self.chi_doc:
            return None
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Thay danh mục đơn giá, chính sách, tham số của dự án đang mở bằng bộ đơn giá '
                                                          'này? Hồ sơ hộ, thửa, giá đất và phương án đã lập giữ nguyên (dòng đã lập '
                                                          'giữ đơn giá cũ; dùng Rà soát giá để kiểm tra).') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        tt = don_gia.ap_vao_du_an(self.con_du_an)
        self.da_ap = True
        self._bao(QMessageBox.information, f'Đã áp bộ đơn giá phiên bản {tt["phien_ban"]} vào dự án.')
        return tt
