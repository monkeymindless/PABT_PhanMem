"""Cửa sổ "Cấu hình nghiệp vụ" (0.9.87 - người dùng 14/10/2026): sửa hồ sơ địa phương (pabt_profile.json) không cần mở file JSON -
mốc thời hạn (SLA) của quy trình 16 bước (niêm yết 10 ngày, đối thoại 30 ngày, thẩm định 15 ngày, thông báo thu hồi 60 / 120 ngày,
vận động trước cưỡng chế 10 ngày - Điều 89), kinh phí tổ chức thực hiện (mức tối đa, làm tròn, phân bổ), ngưỡng Bác sĩ hồ sơ, quy tắc
bản in, thông tin cơ quan. Lưu = dia_phuong.luu_cau_hinh (chỉ ghi phần khác mặc định vào %APPDATA%\\PABT\\pabt_profile.json, áp dụng
ngay cho mọi dự án). Dự án đặt riêng mốc thời hạn (Theo dõi tiến độ → Mốc thời hạn…) thì dự án đó theo số riêng."""
from __future__ import annotations
import copy
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from . import dia_phuong
from .quy_trinh_qd18 import MOC_CUA_BUOC, NHAN_MOC
from .thong_bao import TEN_UD

THU_TU_MOC = ('niem_yet', 'doi_thoai', 'tham_dinh', 'thu_hoi_nn', 'thu_hoi_pnn', 'van_dong')
LAM_TRON = [('Đến đồng', 0), ('Đến nghìn đồng', -3), ('Đến triệu đồng', -6)]
CAN_DOC = [('Canh trên', 'top'), ('Giữa', 'center'), ('Canh dưới', 'bottom')]
CO_QUAN = [('ten_phan_mem', 'Tên phần mềm (dòng 1 băng tiêu đề)'), ('vai_tro', 'Vai trò (băng tiêu đề)'), ('ten', 'Tên tổ chức làm nhiệm vụ bồi thường'), ('truc_thuoc', 'Trực thuộc'),
           ('dia_chi', 'Địa chỉ')]
BAN_IN_MAC_DINH = [('don_vi_cap_tren', 'Đơn vị cấp trên (bản in)'), ('don_vi_tieu_de', 'Tên đơn vị trên tiêu đề bản in'),
                   ('don_vi_lap', 'Đơn vị lập phương án'), ('ky_hieu_so', 'Ký hiệu số phương án'), ('chuc_vu_ky', 'Chức vụ người ký')]


def _so(x) -> str:
    """'2.5' -> '2,5' (hiện kiểu Việt Nam)."""
    return str(x).replace('.', ',')


def _doc_so(chu: str, ten: str) -> str:
    """'2,5' -> '2.5' (lưu dạng chuỗi Decimal). Sai -> ValueError có tên ô."""
    s = chu.strip().replace(' ', '').replace(',', '.')
    try:
        d = Decimal(s)
    except Exception:
        raise ValueError(f'{ten}: "{chu}" không phải số.') from None
    if not d.is_finite():
        raise ValueError(f'{ten}: "{chu}" không phải số.')
    return format(d.normalize(), 'f')


class HopCauHinhNghiepVu(QDialog):
    im_lang = False                      # kiểm thử: không bật hộp thông báo

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Cấu hình nghiệp vụ - hồ sơ địa phương')
        self.resize(1000, 640)
        self.hs = copy.deepcopy(dia_phuong.doc())
        dau = QLabel(f'Hồ sơ đang dùng: <b>{self.hs.get("ten_ho_so", "")}</b>. Sửa xong bấm <b>Lưu</b>: áp dụng ngay cho mọi dự án trên '
                     f'máy này (lưu ở {dia_phuong.file_may()}); gửi máy khác bằng Công cụ → Xuất gói mẫu in &amp; cấu hình.')
        dau.setWordWrap(True)
        self.o_ten = QLineEdit(self.hs.get('ten_ho_so', ''))
        self.tab = QTabWidget()
        self.tab.addTab(self._the_thoi_han(), 'Mốc thời hạn (SLA)')
        self.tab.addTab(self._the_kinh_phi(), 'Kinh phí tổ chức thực hiện')
        self.tab.addTab(self._the_kiem_tra(), 'Kiểm tra && bản in')
        self.tab.addTab(self._the_co_quan(), 'Cơ quan')
        b_luu = QPushButton('Lưu')
        b_luu.clicked.connect(lambda: self.luu())
        b_mac = QPushButton('Khôi phục mặc định…')
        b_mac.setToolTip('Bỏ mọi sửa đổi trên máy này, dùng lại hồ sơ đóng kèm phần mềm (file cũ giữ lại đuôi .bak)')
        b_mac.clicked.connect(lambda: self.khoi_phuc())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addWidget(b_mac)
        hn.addStretch(1)
        hn.addWidget(b_luu)
        hn.addWidget(b_dong)
        f = QFormLayout()
        f.addRow('Tên hồ sơ địa phương:', self.o_ten)
        lo = QVBoxLayout(self)
        lo.addWidget(dau)
        lo.addLayout(f)
        lo.addWidget(self.tab, 1)
        lo.addLayout(hn)

    # ---- thẻ 1: mốc thời hạn
    def _the_thoi_han(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        ghi = QLabel('Số ngày dương lịch. Dự án đã đặt riêng ở "Theo dõi tiến độ → Mốc thời hạn…" thì dự án đó theo số riêng; '
                     'niêm yết / đối thoại áp dụng cho mọi dự án.')
        ghi.setWordWrap(True)
        buoc_cua = {}
        for b, ds in MOC_CUA_BUOC.items():
            for k in ds:
                buoc_cua.setdefault(k, []).append(b)
        self.bang_th = QTableWidget(len(THU_TU_MOC), 4)
        self.bang_th.setHorizontalHeaderLabels(['Mốc', 'Bước (QĐ 18)', 'Số ngày', 'Căn cứ'])
        self.bang_th.verticalHeader().setVisible(False)
        self.o_ngay, self.o_can_cu = {}, {}
        for r, k in enumerate(THU_TU_MOC):
            m = self.hs['thoi_han'][k]
            for c, v in ((0, NHAN_MOC[k]), (1, ', '.join(f'Bước {b}' for b in buoc_cua.get(k, [])))):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.bang_th.setItem(r, c, it)
            o = QSpinBox()
            o.setRange(1, 3650)
            o.setSuffix(' ngày')
            o.setValue(int(m['so_ngay']))
            self.o_ngay[k] = o
            self.bang_th.setCellWidget(r, 2, o)
            e = QLineEdit(m.get('can_cu', ''))
            e.setToolTip(m.get('can_cu', ''))
            self.o_can_cu[k] = e
            self.bang_th.setCellWidget(r, 3, e)
        h = self.bang_th.horizontalHeader()
        for c in (0, 1, 2):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.bang_th.verticalHeader().setDefaultSectionSize(34)
        lo.addWidget(ghi)
        lo.addWidget(self.bang_th, 1)
        return w

    # ---- thẻ 2: kinh phí
    def _the_kinh_phi(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        kp = self.hs['kinh_phi_to_chuc']
        f = QFormLayout()
        self.o_cc_kp = QLineEdit(self.hs['can_cu_phap_ly']['kinh_phi_to_chuc'])
        f.addRow('Căn cứ:', self.o_cc_kp)
        self.o_kp = {}
        for k in ('tuyen', 'khac'):
            ten, tl = QLineEdit(kp['loai'][k]['ten']), QLineEdit(_so(kp['loai'][k]['ty_le_toi_da']))
            tl.setMaximumWidth(90)
            h = QHBoxLayout()
            h.addWidget(ten, 1)
            h.addWidget(QLabel('tối đa'))
            h.addWidget(tl)
            h.addWidget(QLabel('%'))
            self.o_kp[k] = (ten, tl)
            f.addRow('Dự án theo tuyến:' if k == 'tuyen' else 'Dự án khác:', h)
        self.cb_lam_tron = QComboBox()
        for t, v in LAM_TRON:
            self.cb_lam_tron.addItem(t, v)
        i = self.cb_lam_tron.findData(kp['lam_tron_den'])
        self.cb_lam_tron.setCurrentIndex(max(0, i))
        f.addRow('Làm tròn kinh phí:', self.cb_lam_tron)
        self.bang_pb = QTableWidget(0, 2)
        self.bang_pb.setHorizontalHeaderLabels(['Phân bổ cho', 'Tỷ lệ (%)'])
        self.bang_pb.verticalHeader().setVisible(False)
        self.bang_pb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for x in kp['phan_bo']:
            self._them_pb(x['ten'], _so(x['ty_le']))
        b_them = QPushButton('Thêm dòng phân bổ')
        b_them.clicked.connect(lambda: self._them_pb('', '0'))
        b_xoa = QPushButton('Xóa dòng đang chọn')
        b_xoa.clicked.connect(lambda: self.bang_pb.removeRow(self.bang_pb.currentRow()) if self.bang_pb.currentRow() >= 0 else None)
        hn = QHBoxLayout()
        hn.addWidget(b_them)
        hn.addWidget(b_xoa)
        hn.addStretch(1)
        lo.addLayout(f)
        lo.addWidget(QLabel('Phân bổ kinh phí tổ chức thực hiện (tổng phải bằng 100%; tỷ lệ in trên bảng tổng hợp theo đúng các số này):'))
        lo.addWidget(self.bang_pb, 1)
        lo.addLayout(hn)
        return w

    def _them_pb(self, ten: str, tl: str) -> None:
        r = self.bang_pb.rowCount()
        self.bang_pb.insertRow(r)
        self.bang_pb.setItem(r, 0, QTableWidgetItem(ten))
        it = QTableWidgetItem(tl)
        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.bang_pb.setItem(r, 1, it)

    # ---- thẻ 3: kiểm tra, bản in
    def _the_kiem_tra(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        qt = self.hs['quy_tac_kiem_tra']
        self.o_tl = QLineEdit(_so(qt['ty_le_toi_da_tai_san']))
        self.o_tl.setMaximumWidth(90)
        f.addRow('Tỷ lệ chất lượng / bồi thường tối đa (%):', self.o_tl)
        self.o_nk = QSpinBox()
        self.o_nk.setRange(1, 200)
        self.o_nk.setValue(int(qt['nhan_khau_canh_bao']))
        f.addRow('Cảnh báo nhân khẩu lớn hơn:', self.o_nk)
        self.o_hm = {}
        for k, nhan in (('xa', 'xã'), ('phuong', 'phường'), ('dac_khu', 'đặc khu')):
            v = qt['han_muc_dat_o_m2'].get(k)
            o = QLineEdit('' if v is None else _so(v))
            o.setPlaceholderText('để trống = không kiểm tra')
            o.setMaximumWidth(220)
            self.o_hm[k] = o
            f.addRow(f'Hạn mức đất ở tại {nhan} (m²):', o)
        bi = self.hs['ban_in']
        self.o_che = QCheckBox('Che số CCCD')       # 1.0.04: bỏ che CCCD - ô ẩn, luôn tắt
        self.o_che.setChecked(False)
        self.o_che.setVisible(False)
        self.cb_doc = QComboBox()
        for t, v in CAN_DOC:
            self.cb_doc.addItem(t, v)
        self.cb_doc.setCurrentIndex(max(0, self.cb_doc.findData(bi['nguon_goc']['can_doc'])))
        f.addRow('Ô nguồn gốc đất (căn đều hai bên):', self.cb_doc)
        # 24/10/2026: lề trang in bảng tổng hợp A3 ngang (trước chỉ sửa được trong file pabt_profile.json)
        le = dict(dia_phuong.mac_dinh()['ban_in']['le_trang']['tong_hop'])
        le.update((bi.get('le_trang') or {}).get('tong_hop') or {})
        self.o_le = {}
        hang_le = QHBoxLayout()
        for k, nhan in (('left', 'Trái'), ('right', 'Phải'), ('top', 'Trên'), ('bottom', 'Dưới')):
            o = QDoubleSpinBox()
            o.setRange(0, 7.5)
            o.setDecimals(2)
            o.setSingleStep(0.1)
            o.setSuffix(' cm')
            o.setValue(round(float(le[k]) * 2.54, 2))
            self.o_le[k] = o
            hang_le.addWidget(QLabel(nhan + ':'))
            hang_le.addWidget(o)
        hang_le.addStretch(1)
        f.addRow('Lề trang in bảng tổng hợp A3 ngang:', hang_le)
        gc = QLabel('Bảng được thu vừa bề ngang khổ A3 và chừa khoảng 3% nên lề PHẢI thực tế rộng hơn lề đặt chừng 0,5 cm; '
                    'lề trên thực tế cộng thêm khoảng trống trên dòng đầu (~0,2 cm). Áp dụng từ lần in sau.')
        gc.setWordWrap(True)
        f.addRow('', gc)
        return w

    # ---- thẻ 4: cơ quan
    def _the_co_quan(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        cq = self.hs['co_quan']
        self.o_cq = {}
        for k, nhan in CO_QUAN:
            self.o_cq[k] = QLineEdit(cq[k])
            f.addRow(f'{nhan}:', self.o_cq[k])
        self.o_bm = {}
        for k, nhan in BAN_IN_MAC_DINH:
            self.o_bm[k] = QLineEdit(cq['ban_in_mac_dinh'].get(k, ''))
            f.addRow(f'{nhan}:', self.o_bm[k])
        return w

    # ---- đọc / lưu
    def gia_tri(self) -> dict:
        """Hồ sơ đầy đủ theo các ô. Sai -> ValueError (thông báo tiếng Việt)."""
        hs = copy.deepcopy(self.hs)
        hs['ten_ho_so'] = self.o_ten.text().strip() or hs.get('ten_ho_so', '')
        for k in THU_TU_MOC:
            hs['thoi_han'][k] = dict(so_ngay=self.o_ngay[k].value(), can_cu=self.o_can_cu[k].text().strip())
        kp = hs['kinh_phi_to_chuc']
        hs['can_cu_phap_ly']['kinh_phi_to_chuc'] = self.o_cc_kp.text().strip()
        for k, (ten, tl) in self.o_kp.items():
            kp['loai'][k] = dict(ten=ten.text().strip(), ty_le_toi_da=_doc_so(tl.text(), f'Tỷ lệ tối đa ({ten.text()})'))
        kp['lam_tron_den'] = self.cb_lam_tron.currentData()
        pb = []
        for r in range(self.bang_pb.rowCount()):
            ten = (self.bang_pb.item(r, 0).text() if self.bang_pb.item(r, 0) else '').strip()
            tl = self.bang_pb.item(r, 1).text() if self.bang_pb.item(r, 1) else ''
            if ten or tl.strip():
                pb.append(dict(ten=ten, ty_le=_doc_so(tl, f'Tỷ lệ phân bổ dòng {r + 1}')))
        kp['phan_bo'] = pb
        qt = hs['quy_tac_kiem_tra']
        qt['ty_le_toi_da_tai_san'] = _doc_so(self.o_tl.text(), 'Tỷ lệ tối đa')
        qt['nhan_khau_canh_bao'] = self.o_nk.value()
        for k, o in self.o_hm.items():
            qt['han_muc_dat_o_m2'][k] = _doc_so(o.text(), f'Hạn mức đất ở ({k})') if o.text().strip() else None
        hs['ban_in']['che_cccd_ban_du_thao'] = False
        hs['ban_in']['nguon_goc']['can_doc'] = self.cb_doc.currentData()
        tong_hop = hs['ban_in'].setdefault('le_trang', {}).setdefault('tong_hop', {})
        for k, o in self.o_le.items():                    # cm -> inch (hồ sơ tính bằng inch, 0 - 3)
            tong_hop[k] = round(o.value() / 2.54, 4)
        for k, o in self.o_cq.items():
            hs['co_quan'][k] = o.text().strip()
        for k, o in self.o_bm.items():
            hs['co_quan']['ban_in_mac_dinh'][k] = o.text().strip()
        return hs

    def _bao(self, chu: str, loi: bool = False) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def luu(self) -> bool:
        try:
            hs = self.gia_tri()
            p = dia_phuong.luu_cau_hinh(hs)
        except (ValueError, dia_phuong.LoiHoSo) as e:
            self._bao(str(e), True)
            return False
        except OSError as e:
            self._bao(f'Không ghi được cấu hình: {e}', True)
            return False
        self.hs = copy.deepcopy(dia_phuong.doc())
        self._bao('Đã lưu cấu hình nghiệp vụ - áp dụng ngay.' + (f'\n{p}' if p else '\n(Giống hồ sơ mặc định: dùng mặc định.)'))
        self.accept()
        return True

    def khoi_phuc(self, hoi: bool = True) -> bool:
        if hoi and not self.im_lang and QMessageBox.question(
                self, TEN_UD, 'Bỏ mọi sửa đổi cấu hình nghiệp vụ trên máy này, dùng lại hồ sơ mặc định đóng kèm phần mềm?') \
                != QMessageBox.StandardButton.Yes:
            return False
        dia_phuong.khoi_phuc_mac_dinh()
        self._bao('Đã dùng lại hồ sơ mặc định.')
        self.accept()
        return True
