"""Cửa sổ Trợ lý (phương án đột phá 9, 30/10/2026): giải thích số tiền một hộ, bản nháp tờ trình (ngoại tuyến), đọc văn bản dán vào
và diễn giải / viết lại bằng Claude (trực tuyến - TÙY CHỌN, mặc định tắt). Logic ở tro_ly."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QTabWidget, QVBoxLayout, QWidget)

from . import tro_ly


class HopTroLy(QDialog):
    im_lang = False

    def __init__(self, con, parent=None, ma_ho=None, im_lang: bool = False):
        super().__init__(parent)
        self.con, self.im_lang = con, im_lang
        self.setWindowTitle('Trợ lý - giải thích, soạn nháp')
        self.resize(900, 640)
        self.tab = QTabWidget()
        self.tab.addTab(self._the_giai_thich(ma_ho), 'Giải thích số tiền hộ')
        self.tab.addTab(self._the_to_trinh(), 'Nháp tờ trình')
        self.tab.addTab(self._the_van_ban(), 'Đọc văn bản')
        self.tab.addTab(self._the_cai_dat(), 'Cài đặt trợ lý trực tuyến')
        b = QPushButton('Đóng')
        b.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addStretch(1)
        hn.addWidget(b)
        lo = QVBoxLayout(self)
        lo.addWidget(self.tab, 1)
        lo.addLayout(hn)
        self._cap_nhat_nut_ai()

    # ---- thẻ 1
    def _the_giai_thich(self, ma_ho):
        w = QWidget()
        self.cb_ho = QComboBox()
        self.cb_ho.setEditable(True)
        self.cb_ho.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for r in self.con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu, ma_ho'):
            self.cb_ho.addItem(f'{r["thu_tu"]}. {r["ho_ten"] or ""}', r['ma_ho'])
        if ma_ho is not None:
            i = self.cb_ho.findData(ma_ho)
            if i >= 0:
                self.cb_ho.setCurrentIndex(i)
        b = QPushButton('Giải thích')
        b.clicked.connect(lambda: self.giai_thich())
        self.b_ai_gt = QPushButton('Nhờ Claude diễn giải dễ hiểu')
        self.b_ai_gt.clicked.connect(lambda: self.hoi_ai_giai_thich())
        h = QHBoxLayout()
        h.addWidget(QLabel('Hộ:'))
        h.addWidget(self.cb_ho, 1)
        h.addWidget(b)
        h.addWidget(self.b_ai_gt)
        self.o_gt = QPlainTextEdit()
        self.o_gt.setReadOnly(True)
        self.o_gt.setPlaceholderText('So sánh phương án hiện tại với quyết định phê duyệt, các lần lập phương án và số liệu Excel ban đầu '
                                     '- theo từng hạng mục (chạy trên máy, không cần mạng).')
        lo = QVBoxLayout(w)
        lo.addLayout(h)
        lo.addWidget(self.o_gt, 1)
        self.gt = None
        return w

    def giai_thich(self):
        ma = self.cb_ho.currentData()
        if ma is None:
            return None
        try:
            self.gt = tro_ly.giai_thich_ho(self.con, ma)
        except tro_ly.LoiTroLy as e:
            self.o_gt.setPlainText(str(e))
            return None
        self.o_gt.setPlainText(self.gt.chu)
        return self.gt

    def hoi_ai_giai_thich(self):
        g = self.gt if self.gt is not None and self.gt.ma_ho == self.cb_ho.currentData() else self.giai_thich()
        if g is None:
            return None
        import json
        ngu = f'Mã hộ {g.ma_ho}. Phân tích của phần mềm:\n{g.chu}\n\nSố liệu:\n{json.dumps(g.so_lieu, ensure_ascii=False)}'
        tl = self._hoi('Giải thích cho cán bộ (và để nói lại với hộ dân) vì sao số tiền của hộ này chênh lệch / thay đổi, việc cần '
                       'kiểm tra tiếp. Ngắn gọn, gạch đầu dòng.', ngu)
        if tl:
            self.o_gt.appendPlainText('\n--- Claude diễn giải ---\n' + tl)
        return tl

    # ---- thẻ 2
    def _the_to_trinh(self):
        w = QWidget()
        b = QPushButton('Tạo bản nháp từ số liệu dự án')
        b.clicked.connect(lambda: self.tao_nhap())
        self.b_ai_tt = QPushButton('Nhờ Claude viết lại cho chuẩn văn phong hành chính')
        self.b_ai_tt.clicked.connect(lambda: self.viet_lai_to_trinh())
        h = QHBoxLayout()
        h.addWidget(b)
        h.addWidget(self.b_ai_tt)
        h.addStretch(1)
        self.o_tt = QPlainTextEdit()
        self.o_tt.setPlaceholderText('Bản nháp nội dung tờ trình (sửa được, chép sang Word). Tờ trình chính thức vẫn xuất ở '
                                     '"Xuất hồ sơ & Bản in".')
        lo = QVBoxLayout(w)
        lo.addLayout(h)
        lo.addWidget(self.o_tt, 1)
        return w

    def tao_nhap(self) -> str:
        chu = tro_ly.nhap_to_trinh(self.con)
        self.o_tt.setPlainText(chu)
        return chu

    def viet_lai_to_trinh(self):
        nhap = self.o_tt.toPlainText().strip() or self.tao_nhap()
        tl = self._hoi('Viết lại bản nháp tờ trình dưới đây theo văn phong hành chính (Nghị định 30/2020/NĐ-CP), GIỮ NGUYÊN mọi số '
                       'liệu, chỗ chưa có thông tin để "…………".', nhap)
        if tl:
            self.o_tt.setPlainText(tl)
        return tl

    # ---- thẻ 3
    def _the_van_ban(self):
        w = QWidget()
        self.o_vb = QPlainTextEdit()
        self.o_vb.setPlaceholderText('Dán nội dung quyết định / văn bản (chữ) vào đây.')
        self.o_cau = QLineEdit('Tóm tắt: số, ngày, cơ quan ban hành, nội dung chính, đơn giá / mức hỗ trợ, đối tượng áp dụng, hiệu lực.')
        self.b_ai_vb = QPushButton('Hỏi Claude')
        self.b_ai_vb.clicked.connect(lambda: self.doc_van_ban())
        h = QHBoxLayout()
        h.addWidget(QLabel('Yêu cầu:'))
        h.addWidget(self.o_cau, 1)
        h.addWidget(self.b_ai_vb)
        self.o_tl = QPlainTextEdit()
        self.o_tl.setReadOnly(True)
        lo = QVBoxLayout(w)
        lo.addWidget(self.o_vb, 2)
        lo.addLayout(h)
        lo.addWidget(self.o_tl, 2)
        return w

    def doc_van_ban(self):
        vb = self.o_vb.toPlainText().strip()
        if not vb:
            self.o_tl.setPlainText('Dán nội dung văn bản trước.')
            return None
        tl = self._hoi(self.o_cau.text().strip() or 'Tóm tắt văn bản.', vb)
        if tl:
            self.o_tl.setPlainText(tl)
        return tl

    # ---- thẻ 4
    def _the_cai_dat(self):
        w = QWidget()
        cd = tro_ly.doc_cai_dat()
        gt = QLabel('Mặc định trợ lý chỉ chạy TRÊN MÁY (không cần mạng, không gửi dữ liệu). Bật trợ lý trực tuyến để nhờ Claude '
                    '(Anthropic) diễn giải, đọc văn bản, viết lại bản nháp - cần Internet và khóa API của đơn vị. Họ tên, CCCD, số '
                    'điện thoại được thay bằng mã trước khi gửi, trừ khi bật ô "Gửi cả dữ liệu cá nhân".')
        gt.setWordWrap(True)
        self.o_bat = QCheckBox('Bật trợ lý trực tuyến (Claude)')
        self.o_bat.setChecked(cd['bat'])
        self.o_bat.toggled.connect(lambda b: (tro_ly.ghi_cai_dat(bat=b), self._cap_nhat_nut_ai()))
        self.cb_mh = QComboBox()
        for m in tro_ly.MO_HINH:
            self.cb_mh.addItem(m, m)
        self.cb_mh.setCurrentIndex(self.cb_mh.findData(cd['mo_hinh']))
        self.cb_mh.activated.connect(lambda _: tro_ly.ghi_cai_dat(mo_hinh=self.cb_mh.currentData()))
        self.o_ca_nhan = QCheckBox('Gửi cả dữ liệu cá nhân (họ tên, CCCD, số điện thoại) - chỉ bật khi đơn vị cho phép')
        self.o_ca_nhan.setChecked(cd['gui_ca_nhan'])
        self.o_ca_nhan.toggled.connect(lambda b: tro_ly.ghi_cai_dat(gui_ca_nhan=b))
        self.o_khoa = QLineEdit()
        self.o_khoa.setEchoMode(QLineEdit.EchoMode.Password)
        self.o_khoa.setPlaceholderText('Đã lưu khóa (mã hóa)' if cd['co_khoa'] else 'Dán khóa API (sk-ant-…) - hoặc dùng biến ANTHROPIC_API_KEY')
        b_luu = QPushButton('Lưu khóa (mã hóa)')
        b_luu.clicked.connect(lambda: self.luu_khoa())
        b_xoa = QPushButton('Xóa khóa đã lưu')
        b_xoa.clicked.connect(lambda: self.luu_khoa(xoa=True))
        hk = QHBoxLayout()
        hk.addWidget(self.o_khoa, 1)
        hk.addWidget(b_luu)
        hk.addWidget(b_xoa)
        self.lb_cd = QLabel('')
        self.lb_cd.setWordWrap(True)
        f = QFormLayout()
        f.addRow(self.o_bat)
        f.addRow('Mô hình:', self.cb_mh)
        f.addRow(self.o_ca_nhan)
        f.addRow('Khóa API:', hk)
        lo = QVBoxLayout(w)
        lo.addWidget(gt)
        lo.addLayout(f)
        lo.addWidget(self.lb_cd)
        lo.addStretch(1)
        return w

    def luu_khoa(self, xoa: bool = False) -> bool:
        try:
            if xoa:
                tro_ly.ghi_cai_dat(xoa_khoa=True)
            else:
                k = self.o_khoa.text().strip()
                if not k:
                    return False
                tro_ly.ghi_cai_dat(khoa=k)
        except (tro_ly.LoiTroLy, OSError) as e:
            self.lb_cd.setText(str(e))
            return False
        self.o_khoa.clear()
        self.o_khoa.setPlaceholderText('Đã lưu khóa (mã hóa)' if not xoa else 'Dán khóa API (sk-ant-…)')
        self.lb_cd.setText('Đã xóa khóa.' if xoa else 'Đã lưu khóa (mã hóa bằng tài khoản Windows này).')
        return True

    def _cap_nhat_nut_ai(self) -> None:
        bat = tro_ly.doc_cai_dat()['bat']
        co = tro_ly.co_thu_vien()
        for b in (self.b_ai_gt, self.b_ai_tt, self.b_ai_vb):
            b.setEnabled(bat and co)
            b.setToolTip('' if bat and co else ('Máy chưa có thư viện "anthropic" (bản Windows 10/11)' if not co else
                                                'Bật ở thẻ "Cài đặt trợ lý trực tuyến"'))
        if hasattr(self, 'lb_cd'):
            self.lb_cd.setText(('Trợ lý trực tuyến: BẬT' if bat else 'Trợ lý trực tuyến: TẮT (chỉ chạy trên máy)') +
                               ('' if co else ' · Máy này chưa có thư viện "anthropic" - chỉ dùng được phần chạy trên máy.'))

    def _hoi(self, cau: str, ngu: str, khach=None) -> str | None:
        """Hỏi Claude ở luồng nền (cửa sổ không treo). Lỗi: báo trong thẻ đang xem, trả None."""
        from .giao_dien import chay_nen
        if not tro_ly.doc_cai_dat()['gui_ca_nhan']:     # che họ tên ở luồng giao diện (kết nối CSDL không dùng được ở luồng nền)
            cau, ngu = tro_ly.an_danh(cau, self.con), tro_ly.an_danh(ngu, self.con)
        try:
            return chay_nen(self, lambda: tro_ly.hoi_claude(cau, ngu, None, khach), 'Đang hỏi Claude…')
        except tro_ly.LoiTroLy as e:
            o = {0: self.o_gt, 1: self.o_tt, 2: self.o_tl}.get(self.tab.currentIndex(), self.o_tl)
            o.appendPlainText(f'\n[{e}]')
            return None
