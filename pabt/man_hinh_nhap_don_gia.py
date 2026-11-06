"""Màn hình xem trước cập nhật đơn giá từ file Excel / Word / PDF / CSV: thông tin văn bản, nhóm từng dòng, bỏ chọn dòng,
áp dụng."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
                               QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QTabWidget, QTableWidget, QTableWidgetItem,
                               QToolButton, QVBoxLayout, QWidget)

from . import nhap_don_gia as ndg
from . import phan_tich_ai_don_gia as pai
from . import quy_dinh_van_ban as qvb
from .lap_pa import LoiNhap, bo_dau
from .giao_dien import vua_dong
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (kiểu riêng đổi theo tông nền)
from .tien import vn
from .thong_bao import TEN_UD

MAU = {'mới': QColor('#E8F5E9'), 'cập nhật': QColor('#FFF8E1'), 'đổi quy cách': QColor('#E3F2FD'), 'bỏ': QColor('#FFEBEE'),
       'giữ nguyên': QColor('#F5F5F5')}
DONG_TU_CAO_TOI_DA = 1500
TEN_NHOM_NGAN = {2: 'Nhà, công trình', 3: 'Cây trồng', ndg.NHOM_VN: 'Vật nuôi', 4: 'Hỗ trợ'}
# 1.0.57 (người dùng 04/11/2026: "chia làm 2 cột (2 phần dữ liệu), trái là … mã tài sản, tên tài sản hiện hành, đơn giá hiện hành, ghi
# chú | bên phải là mã tài sản mới, tên tài sản mới, đơn giá mới, ghi chú … để đối chiếu các tài sản cũ mới với nhau")
C_DUNG, C_MA_CU, C_TEN_CU, C_GIA_CU, C_GC_CU, C_MA, C_TEN, C_DVT, C_GIA, C_GC, C_TT, C_KV, C_NHOM = range(13)
COT = ('Dùng', 'Mã\n(hiện hành)', 'Tên hiện hành\n(bộ đơn giá đang dùng)', 'Đơn giá\nhiện hành (đ)', 'Ghi chú\nhiện hành',
       'Mã\n(mới)', 'Tên mới\n(theo văn bản)', 'ĐVT', 'Đơn giá\nmới (đ)', 'Ghi chú mới\n(quy cách)', 'Trạng thái', 'Khu vực',
       'Nhóm')
RONG_COT = (44, 64, 250, 96, 110, 70, 280, 56, 96, 130, 150, 100, 84)    # tên hiện hành / tên mới co giãn theo cửa sổ (Stretch)
KIEU_CANH = 'QLabel { color: #B71C1C; background: #FFEBEE; padding: 6px; border-radius: 4px; }'
KIEU_NUT_CANH = 'QPushButton { color: #B71C1C; font-weight: 600; }'
COT_HIEN_HANH = (C_MA_CU, C_TEN_CU, C_GIA_CU, C_GC_CU)
COT_MOI = (C_MA, C_TEN, C_DVT, C_GIA, C_GC)
# 30/10/2026 (người dùng): "thay thế toàn bộ văn bản cũ bằng văn bản mới, để đúng với toàn bộ nội dung theo văn bản mới"
# 1.0.46: chữ khác chuột phải "Thay thế dòng đang chọn" trên bảng Bộ đơn giá
# 1.0.61 (người dùng 05/11/2026): chữ ngắn trên ô chọn, giải thích đầy đủ ở chú thích (tooltip) - nhường chỗ cho bảng đối chiếu
CACH_CAP_NHAT = (('Bổ sung, sửa đổi', False), ('Thay cả nhóm theo văn bản này', True))
CACH_GIAI_THICH = ('Thêm mục mới, đổi giá - các mục khác của bộ đơn giá giữ nguyên.',
                   'Đổi tên, quy cách theo văn bản; bỏ mục cùng nhóm không còn trong văn bản.')
KHONG_VB_CU = '(Không đánh dấu văn bản nào hết hiệu lực)'
# 1.0.56 (người dùng 03/11/2026: "tự động tick vào ô có nội dung thay đổi… hạn chế để người dùng phải tự chọn từng dòng"): bộ lọc bảng
HIEN = (('Dòng cần xử lý', 'can'), ('Tất cả các dòng', 'tat_ca'))
HIEN_TAT_CA_DUOI = 60            # văn bản ít dòng hơn: mặc định hiện tất cả (không cần lọc)


def mo_ta_van_ban(vb: dict) -> str:
    """'Quyết định 48/2025/QĐ-UBND ngày 23/10/2025 của Ủy ban nhân dân tỉnh Đồng Nai' (rỗng nếu không nhận ra số hiệu)."""
    if not vb or not vb.get('so_hieu'):
        return ''
    return ' '.join(x for x in (vb.get('loai_vb', ''), vb['so_hieu'], f'ngày {vb["ngay"]}' if vb.get('ngay') else '',
                                f'của {vb["co_quan"]}' if vb.get('co_quan') else '') if x)


class HopNhapDonGia(QDialog):
    im_lang = False

    def __init__(self, file, parent=None, nguon: str = '', dong: list | None = None, van_ban: dict | None = None,
                 nhom_uu_tien: int | None = None, thay_the: bool | None = None):
        """dong: các dòng đã đọc sẵn (ndg.doc_bang_ocr, có hộp tiến trình khi phải nhận dạng bản scan; chữ dán từ Clipboard).
        van_ban: ndg.phan_tich_van_ban (không có thì tự phân tích các dòng đầu của file). nhom_uu_tien: nhóm của thẻ đang xem ở Bộ
        đơn giá (2 / 3 / 7 / 4) - dùng khi văn bản không cho biết nhóm (bảng dán, file không có trích yếu).
        thay_the: True = chọn sẵn "Thay cả nhóm theo văn bản này" (nút Cập nhật đơn giá)."""
        # đọc file trước khi tạo hộp thoại: file lỗi thì không để lại hộp thoại dở dang
        dong = ndg.doc_bang(file) if dong is None else dong
        vb = van_ban if van_ban is not None else ndg.phan_tich_van_ban(dong, Path(str(file)).name if file else (nguon or ''))
        nhom_vb = vb.get('nhom', 0) or nhom_uu_tien or 0
        quy_tac = []                                    # dòng quy định cách tính không có giá ("tính thêm 50%", "bằng 40% đơn giá…")
        ds = ndg.nhan_muc(dong, nhom_vb, quy_tac)
        # bảng giá cây lâm nghiệp theo NHÓM loài x cỡ đường kính -> từng loài một dòng mỗi cỡ (danh sách loài Phụ lục VI của văn bản)
        so_nhom = len({m.nhom_loai for m in ds if m.nhom_loai})
        ds, khong_tach = ndg.tach_theo_loai(ds, ndg.doc_nhom_loai(dong))
        xem_van, tu_loi_van = [], False
        # 1.0.60: văn bản chính sách (toàn văn QĐ 42/2025): LUÔN đọc điều khoản, kể cả khi có bảng nhỏ; dòng khớp mã CS đang dùng
        chinh_sach = nhom_vb == 4 and ndg.co_dieu_khoan(dong)
        bieu = []
        if chinh_sach:
            ds_van, xem_van, bieu = ndg.muc_chinh_sach_tu_dieu_khoan(dong, 4)
            tu_loi_van = bool(ds_van)
            ds = list(ds) + ds_van
        elif not ds:                                    # không có bảng: đơn giá viết trong điều khoản (QĐ 31/2025 vật nuôi...)
            ds, xem_van = ndg.muc_tu_loi_van(dong, nhom_vb)
            tu_loi_van = bool(ds)
        if not ds:
            raise ndg.LoiKhongCoGia('Không tìm thấy đơn giá nào trong file: không có bảng (cột Tên, ĐVT, Đơn giá) và không có câu '
                                    'ghi giá dạng "<tên> … <số> đồng/<đơn vị>".' +
                                    ('\n\n' + '\n'.join(xem_van[:10]) if xem_van else ''))
        # 1.0.56: quy định cách tính trong LỜI VĂN các điều khoản + dòng quy tắc của bảng (quy_dinh_van_ban)
        quy_dinh = qvb.trich_quy_dinh(dong, nhom_vb, quy_tac)
        super().__init__(parent)
        self.quy_dinh = quy_dinh
        self.dong = dong
        self.ket_qua_ai = None                          # 1.0.56: kết quả phân tích AI (tùy chọn) - áp lại sau mỗi lần so khớp
        self.tu_loi_van = tu_loi_van
        self.chinh_sach = chinh_sach
        self.bieu_thuong = bieu
        try:
            self.vb_cu_khop = ndg.van_ban_cu_theo_so_hieu(vb.get('thay_the_vb') or ())
        except Exception:                               # noqa: BLE001 - bộ đơn giá đọc không được: chỉ không gợi ý
            self.vb_cu_khop = []
        self.scan = bool(getattr(dong, 'scan', False))   # dòng đọc bằng nhận dạng chữ: chặn giá nghi đọc sai, không chọn sẵn mục "bỏ"
        # 1.0.57: văn bản nhiều khu vực giá (QĐ 18/2026 hợp nhất: Phụ lục I khu vực 1, Phụ lục II khu vực 2) - mặc định nhập CẢ HAI
        # khu vực, bộ đơn giá tách mục theo khu vực (khu_vuc_gia: dự án chỉ dùng phụ lục của xã dự án); ô "Khu vực giá" chọn một khu vực
        from . import khu_vuc_gia
        self.ds_tat_ca = ds
        self.khu_vuc = ndg.cac_khu_vuc(ds)
        self.kv = ndg.KV_CA_HAI if self.khu_vuc else ''
        self.ten_pl = khu_vuc_gia.ten_phu_luc_kv(dong) if self.khu_vuc else {}
        self.xa_kv = khu_vuc_gia.doc_ds_xa(dong) if self.khu_vuc else {}
        self.ds = ds
        self.van_ban = vb
        self.da_co = ndg.da_co(vb.get('so_hieu', ''))
        # văn bản đã có: file có gồm đủ các văn bản sửa đổi của nhóm đang dùng không (bản hợp nhất "48 được sửa đổi bởi 66") - gồm đủ thì
        # giá trong file không cũ hơn bộ đơn giá: dòng đổi giá chọn sẵn được (trước 1.0.56: văn bản đã có luôn bỏ chọn dòng đổi giá)
        self.chua_gom = []
        if self.da_co:
            try:
                self.chua_gom = qvb.van_ban_chua_gom(dong, vb, set(ndg.pham_vi_thay_the(ds, None)) or {nhom_vb or 3})
            except Exception:                           # noqa: BLE001 - không đọc được bộ đơn giá: coi như chưa gồm (an toàn)
                self.chua_gom = ['(không đọc được danh sách văn bản của bộ đơn giá)']
        self.da_co_cu = self.da_co and bool(self.chua_gom)
        self.ket_qua = None
        self.nguon = nguon or Path(str(file or 'Clipboard')).name
        self.setWindowTitle(f'Cập nhật đơn giá từ {self.nguon}')
        self.resize(1360, 820)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 8, 10, 8)
        lo.setSpacing(6)
        mt = mo_ta_van_ban(vb)
        if mt:
            ty = vb.get('trich_yeu', '')
            l_vb = QLabel(f'<b>{mt}</b>' + (f' - {ty}' if ty else ''))
            l_vb.setWordWrap(True)
            l_vb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lo.addWidget(l_vb)
        canh = []
        if self.da_co_cu:
            canh.append('Văn bản này ĐÃ CÓ trong danh sách văn bản của bộ đơn giá và KHÔNG nhắc tới văn bản sửa đổi đang dùng: '
                        + '; '.join(self.chua_gom[:4]) + ' - giá trong file có thể cũ hơn: các dòng ĐỔI GIÁ để trống ô "Dùng" (áp '
                        'dụng lại sẽ ghi đè giá mới bằng giá cũ) - chỉ chọn khi chắc chắn. Mục MỚI vẫn được chọn.')
        elif self.da_co:
            canh.append('Văn bản này ĐÃ CÓ trong bộ đơn giá; file gồm đủ các văn bản sửa đổi của nhóm đang dùng (bản hợp nhất / cùng văn '
                        'bản) - các dòng thay đổi được CHỌN SẴN.')
        if so_nhom:
            so_loai = len({m.ten_loai for m in ds if m.ten_loai})
            canh.append(f'Bảng giá cây lâm nghiệp theo nhóm loài: {so_nhom - len(khong_tach)} nhóm đã tách thành {so_loai} loài, mỗi '
                        'loài một dòng mỗi cỡ đường kính (danh sách loài theo văn bản; văn bản không có danh sách thì theo các loài '
                        'cùng bảng giá trong bộ đơn giá đang dùng).' +
                        (f' KHÔNG tách được: {"; ".join(khong_tach)} - văn bản không có danh sách loài của nhóm, giá khác bộ đơn giá '
                         'đang dùng: các dòng giữ theo tên nhóm.' if khong_tach else ''))
        if mt and not vb.get('dong_nai'):
            canh.append('Không thấy tên Đồng Nai trong văn bản: kiểm tra đây có đúng văn bản áp dụng tại địa phương không.')
        if self.chinh_sach:
            canh.append(f'Văn bản chính sách: {sum(1 for m in ds if m.can_cu)} mức đọc từ các điều khoản, đối chiếu với mã hỗ trợ đang dùng theo '
                        'Điều / khoản, đơn giá và nghiệp vụ. Mục dẫn chiếu Luật / Nghị định (ổn định đời sống, tái định cư, đào tạo) giữ nguyên.')
            if bieu:
                khac = ndg.so_bieu_thuong(bieu)
                canh.append(f'Biểu thưởng bàn giao mặt bằng ({len(bieu)} mức): ' + (f'KHÁC bộ đơn giá - {khac}; sửa ở Bộ đơn giá nếu đúng.' if khac else
                                                                                    'trùng bộ đơn giá.'))
        elif self.tu_loi_van:
            canh.append(f'Văn bản không có bảng giá: {len(ds)} đơn giá đọc từ LỜI VĂN các điều khoản (tên = chữ trước số tiền, ghép '
                        'tiêu đề khoản). Rê chuột vào tên để xem câu gốc; sửa tên / bỏ chọn dòng chưa đúng trước khi áp dụng.')
        if vb.get('thay_the_vb'):
            co_ = {ndg.chuan_so_hieu(x) for x in vb['thay_the_vb'] if any(ndg.chuan_so_hieu(x) in ndg.chuan_so_hieu(c[1]) for c in self.vb_cu_khop)}
            canh.append('Văn bản này thay thế: ' + ', '.join(vb['thay_the_vb']) + (' - dòng có trong danh sách văn bản căn cứ được ghi hết hiệu lực '
                        'khi áp dụng.' if co_ else '.'))
        if vb.get('sua_doi') and not self.chinh_sach:
            canh.append('Văn bản sửa đổi, bổ sung: chỉ các bảng giá trong văn bản được áp dụng; nội dung bãi bỏ / sửa điều khoản '
                        'ở khung bên dưới cần tự xử lý.')
        self.canh = canh                                # 1.0.61: lưu ý chuyển vào khung "Thông tin kèm theo" (thẻ Lưu ý) - nhường chỗ cho bảng
        self.o_nhom = QComboBox()
        self.o_nhom.addItem('Tự động theo văn bản', 0)
        self.o_nhom.setToolTip('Tự động: theo văn bản, tiêu đề nhóm và từng dòng (tên, ĐVT). Hoặc ép cả văn bản vào một nhóm danh mục.')
        for k, t in ndg.NHOM.items():
            self.o_nhom.addItem('Toàn bộ là ' + t, k)
        self.o_nhom.currentIndexChanged.connect(self._doi_cach)
        hang_cach = QHBoxLayout()
        hang_cach.setSpacing(8)
        for chu_, w_ in (('Nhóm', self.o_nhom),):
            n = QLabel(chu_)
            n.setProperty('vai', 'nhan')
            hang_cach.addWidget(n)
            hang_cach.addWidget(w_, 2)
        n = QLabel('Cách cập nhật')
        n.setProperty('vai', 'nhan')
        hang_cach.addWidget(n)
        self.o_cach = QComboBox()
        for i_, (chu, gt) in enumerate(CACH_CAP_NHAT):
            self.o_cach.addItem(chu, gt)
            self.o_cach.setItemData(i_, CACH_GIAI_THICH[i_], Qt.ItemDataRole.ToolTipRole)
        if thay_the and not chinh_sach:                 # văn bản chính sách: mặc định bổ sung, đối chiếu (không thay cả nhóm)
            for i in range(self.o_cach.count()):
                if self.o_cach.itemData(i):
                    self.o_cach.setCurrentIndex(i)
                    break
        self.o_cach.setToolTip('Thay cả nhóm: mục cũ khớp với văn bản được đổi tên / mật độ / ghi chú theo cách ghi của văn bản (mã giữ nguyên, '
                               'không thêm chú thích "(Năm thứ…)" - năm tuổi tính theo năm kiến thiết của loài); mục cũ '
                               'cùng nhóm (cây trồng / nhà, công trình / vật nuôi / hỗ trợ) không còn trong văn bản hiện dòng đỏ "bỏ" '
                               '- chọn sẵn, bỏ dấu "Dùng" để giữ. Dự án đã lập giữ nguyên số liệu; bộ đơn giá cũ được giữ.')
        self.o_cach.currentIndexChanged.connect(self._doi_cach)
        hang_cach.addWidget(self.o_cach, 1)
        self.cb_kv = None
        if self.khu_vuc:
            n = QLabel('Khu vực')
            n.setProperty('vai', 'nhan')
            hang_cach.addWidget(n)
            self.cb_kv = QComboBox()
            self.cb_kv.addItem('Cả ' + ' và '.join(self.ten_kv(k) for k, _ in self.khu_vuc) + ' - tách theo khu vực', ndg.KV_CA_HAI)
            for k, so in self.khu_vuc:
                self.cb_kv.addItem(f'Chỉ {self.ten_kv(k)} ({so} dòng)', k)
            self.cb_kv.setCurrentIndex(0)
            so_xa = sum(len(v) for v in self.xa_kv.values())
            self.cb_kv.setToolTip('Văn bản có nhiều khu vực giá (mỗi phụ lục một khu vực). Mặc định nhập CẢ các phụ lục: mỗi mục gắn khu vực '
                                  f'của phụ lục ({so_xa} xã / phường đọc được từ phần ghi chú của văn bản); dự án chỉ dùng phụ lục của '
                                  'khu vực có xã dự án, phụ lục kia tự khóa ẩn. "Chỉ khu vực …": như bộ đơn giá một khu vực.')
            self.cb_kv.currentIndexChanged.connect(lambda _: self.doi_khu_vuc(self.cb_kv.currentData()))
            hang_cach.addWidget(self.cb_kv)
        self.lb_vb_cu = QLabel('VB hết hiệu lực')
        self.lb_vb_cu.setProperty('vai', 'nhan')
        hang_cach.addWidget(self.lb_vb_cu)
        self.cb_vb_cu = QComboBox()
        self.cb_vb_cu.setToolTip('Văn bản trong danh sách văn bản căn cứ của bộ đơn giá được ghi "Hết hiệu lực - thay thế bởi …"')
        hang_cach.addWidget(self.cb_vb_cu)
        lo.addLayout(hang_cach)
        self.lb_vb_cu.setVisible(False)
        self.cb_vb_cu.setVisible(False)
        if self.vb_cu_khop:                             # văn bản ghi rõ văn bản bị thay thế: chọn sẵn, không cần chế độ thay cả nhóm
            self._nap_vb_cu()
            self.lb_vb_cu.setVisible(True)
            self.cb_vb_cu.setVisible(True)
        self.lb_canh_thay = QLabel()
        self.lb_canh_thay.setWordWrap(True)
        dat_kieu_theo_tong(self.lb_canh_thay, KIEU_CANH)
        self.lb_canh_thay.setVisible(False)
        self.xem_van = xem_van
        self.quy_tac = quy_tac
        self._cho_dem = False
        self._khoa_tim = {}
        # --- hàng lọc / chọn (1.0.61: gọn một hàng; nút "Chọn tất cả" + menu các cách chọn)
        hang_loc = QHBoxLayout()
        hang_loc.setSpacing(8)
        self.cb_hien = QComboBox()
        for chu_, k_ in HIEN:
            self.cb_hien.addItem(chu_, k_)
        self.cb_hien.setCurrentIndex(0 if len(ds) >= HIEN_TAT_CA_DUOI else 1)
        self.cb_hien.setToolTip('Dòng cần xử lý: mới, đổi giá, đổi tên / quy cách, bỏ, cần xem lại. Văn bản vài nghìn dòng mà chỉ vài dòng '
                                'thay đổi: chỉ hiện các dòng cần xem / cần cập nhật.')
        self.cb_hien.currentIndexChanged.connect(lambda _: self._loc())
        hang_loc.addWidget(self.cb_hien)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm theo mã, tên, ĐVT (không cần gõ dấu)')
        self.o_tim.setClearButtonEnabled(True)
        self.o_tim.textChanged.connect(lambda _: self._loc())
        hang_loc.addWidget(self.o_tim, 1)
        nhom_chon = QHBoxLayout()
        nhom_chon.setSpacing(1)
        self.b_chon_doi = QPushButton('Chọn tất cả')
        self.b_chon_doi.setToolTip('Đánh dấu "Dùng" mọi dòng của văn bản mới có thay đổi (mới / đổi giá / đổi tên, quy cách / bỏ) - gồm cả dòng giá '
                                   'cần xem lại của bản scan: đối chiếu trước khi áp dụng. Bấm tiêu đề cột "Dùng" để chọn / bỏ chọn các dòng đang hiện.')
        self.b_chon_doi.clicked.connect(lambda: self.chon_theo(True))
        nhom_chon.addWidget(self.b_chon_doi)
        self.b_menu_chon = QToolButton()
        self.b_menu_chon.setArrowType(Qt.ArrowType.DownArrow)
        self.b_menu_chon.setToolTip('Các cách chọn khác')
        self.b_menu_chon.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_chon = QMenu(self.b_menu_chon)
        self.menu_chon.addAction('Chọn tất cả dòng thay đổi (theo văn bản mới)', lambda: self.chon_theo(True))
        self.menu_chon.addAction('Chỉ chọn các dòng đang hiện', lambda: self.chon_theo(True, 'hien'))
        self.menu_chon.addAction('Đảo chọn các dòng đang hiện', lambda: self.chon_theo(True, 'dao'))
        self.menu_chon.addSeparator()
        self.menu_chon.addAction('Thay toàn bộ theo văn bản mới (thay cả nhóm + chọn tất cả)', lambda: self.thay_toan_bo())
        self.menu_chon.addSeparator()
        self.menu_chon.addAction('Bỏ chọn tất cả', lambda: self.chon_theo(False))
        self.b_menu_chon.setMenu(self.menu_chon)
        nhom_chon.addWidget(self.b_menu_chon)
        hang_loc.addLayout(nhom_chon)
        self.b_bo_chon = QPushButton('Bỏ chọn')
        self.b_bo_chon.setToolTip('Bỏ dấu "Dùng" của mọi dòng')
        self.b_bo_chon.clicked.connect(lambda: self.chon_theo(False))
        hang_loc.addWidget(self.b_bo_chon)
        self.b_ai = QPushButton('Kiểm tra bằng AI…')
        ok_ai, ly_do_ai = pai.dung_duoc()
        self.b_ai.setToolTip('AI (Claude) đọc TOÀN VĂN văn bản như một cán bộ thẩm định: xác minh tên / ĐVT / đơn giá các dòng cần xem, '
                             'tìm thêm quy định cách tính trong lời văn, quan hệ sửa đổi / thay thế. Chỉ gửi chữ của văn bản đơn giá '
                             '(văn bản công khai) - không gửi dữ liệu dự án / hộ dân. Không tự đổi đơn giá: dòng AI đọc khác bị bỏ chọn '
                             'để đối chiếu.' + ('' if ok_ai else f'\n\n{ly_do_ai}'))
        self.b_ai.setEnabled(ok_ai)
        self.b_ai.clicked.connect(lambda: self.phan_tich_ai())
        hang_loc.addWidget(self.b_ai)
        lo.addLayout(hang_loc)
        self.lb_ai = QLabel()
        self.lb_ai.setWordWrap(True)
        lo.addWidget(self.lb_ai)
        self.lb_ai.setVisible(False)
        # --- bảng đối chiếu: chiếm phần lớn cửa sổ
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(list(COT))
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate(RONG_COT):
            self.bang.setColumnWidth(c, w)
        hd = self.bang.horizontalHeader()
        hd.setStretchLastSection(False)
        hd.setFixedHeight(42)                           # tiêu đề hai dòng không bị cắt
        hd.setHighlightSections(False)
        for c in (C_TEN_CU, C_TEN):                     # chỗ trống của cửa sổ dành cho hai cột tên
            hd.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        hd.sectionClicked.connect(self._bam_dau_cot)
        self.bang.setWordWrap(True)                     # tên dài (điều kiện "nuôi dưới 50%…" ở cuối) không bị cắt "…"
        self.bang.setMinimumHeight(240)
        self.bang.horizontalHeaderItem(C_DUNG).setToolTip('Bấm để chọn / bỏ chọn cả các dòng đang hiện')
        for c in COT_HIEN_HANH:
            self.bang.horizontalHeaderItem(c).setToolTip('Bên trái: bộ đơn giá hiện hành (đang dùng)')
        for c in COT_MOI:
            self.bang.horizontalHeaderItem(c).setToolTip('Bên phải: văn bản mới (sẽ ghi vào bộ đơn giá mới khi áp dụng)')
        lo.addWidget(self.bang, 1)
        self.bang.setColumnHidden(C_KV, not self.khu_vuc)
        self.bang.cellChanged.connect(self._sua_o)
        self.bang.itemChanged.connect(self._hen_dem)
        # --- chú giải màu + tóm tắt
        hang_chu = QHBoxLayout()
        hang_chu.setSpacing(10)
        chip = ''.join(f'<span style="background-color:{MAU[k].name()}; color:black;">&nbsp;{t}&nbsp;</span>&nbsp; '
                       for k, t in (('mới', 'mới'), ('cập nhật', 'đổi giá'), ('đổi quy cách', 'đổi tên / quy cách'), ('bỏ', 'bỏ'),
                                    ('giữ nguyên', 'không đổi')))
        self.lb_chu = QLabel(chip)
        self.lb_chu.setToolTip('Xanh lá: mục mới (thêm vào danh mục). Vàng: đổi giá ("gần đúng": tên gần giống, xem kỹ). Xanh dương: đổi tên / '
                               'quy cách theo văn bản. Đỏ: thay thế toàn bộ - mục cũ không còn trong văn bản, sẽ bị bỏ. Xám: không đổi (bỏ '
                               'qua). Bỏ dấu ở cột "Dùng" với dòng không muốn cập nhật. Bộ đơn giá cũ được giữ; dự án đang lập muốn dùng giá '
                               'mới thì "Áp bộ đơn giá vào dự án".')
        hang_chu.addWidget(self.lb_chu)
        self.lb = QLabel()
        self.lb.setWordWrap(True)
        hang_chu.addWidget(self.lb, 1)
        lo.addLayout(hang_chu)
        # --- khung thông tin kèm theo (ẩn mặc định): lưu ý, quy định cách tính, câu cần nhập tay, nội dung sửa đổi
        self.khung_phu = QTabWidget()
        self.khung_phu.setMaximumHeight(200)

        def trang_chu(*thanh_phan) -> QWidget:
            tr = QWidget()
            v = QVBoxLayout(tr)
            v.setContentsMargins(6, 6, 6, 6)
            v.setSpacing(4)
            for w in thanh_phan:
                v.addWidget(w)
            return tr
        self.l_canh = QLabel('\n'.join('• ' + x for x in canh))
        self.l_canh.setWordWrap(True)
        dat_kieu_theo_tong(self.l_canh, KIEU_CANH)
        self.l_canh.setVisible(bool(canh))
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setWidget(trang_chu(self.l_canh, self.lb_canh_thay))
        self._tr_luu = cuon
        self.khung_phu.addTab(cuon, 'Lưu ý')
        self.lb_qd = QLabel()
        self.lb_qd.setWordWrap(True)
        self.o_quy_tac = QPlainTextEdit()
        self.o_quy_tac.setReadOnly(True)
        self._tr_qd = trang_chu(self.lb_qd, self.o_quy_tac)
        self.khung_phu.addTab(self._tr_qd, 'Quy định cách tính')
        if xem_van:
            o = QPlainTextEdit('\n'.join(xem_van))
            o.setReadOnly(True)
            self.khung_phu.addTab(o, f'Câu cần nhập tay ({len(xem_van)})')
            self.khung_phu.setTabToolTip(self.khung_phu.count() - 1, 'Câu có số tiền / tỷ lệ phần mềm KHÔNG tự lấy (khoảng giá, tỷ lệ %, '
                                                                    'không rõ tên) - xem và nhập tay nếu cần')
        if vb.get('can_xem'):
            o = QPlainTextEdit('\n'.join(vb['can_xem']))
            o.setReadOnly(True)
            self.khung_phu.addTab(o, f'Nội dung sửa đổi ({len(vb["can_xem"])})')
            self.khung_phu.setTabToolTip(self.khung_phu.count() - 1, 'Nội dung sửa đổi / bãi bỏ trong văn bản (phần mềm không tự áp dụng - '
                                                                    'xem và xử lý nếu cần)')
        lo.addWidget(self.khung_phu)
        self.khung_phu.setVisible(False)
        # --- hàng dưới cùng
        duoi = QHBoxLayout()
        duoi.setSpacing(8)
        self.b_phu = QPushButton('Lưu ý và quy định')
        self.b_phu.setCheckable(True)
        self.b_phu.setToolTip('Mở / đóng khung lưu ý, quy định cách tính, câu cần nhập tay của văn bản')
        dat_kieu_theo_tong(self.b_phu, KIEU_NUT_CANH)
        self.b_phu.toggled.connect(self.khung_phu.setVisible)
        duoi.addWidget(self.b_phu)
        self.o_luu_qd = QCheckBox()
        self.o_luu_qd.setChecked(True)
        duoi.addWidget(self.o_luu_qd)
        duoi.addStretch(1)
        self.lb_dem = QLabel()
        duoi.addWidget(self.lb_dem)
        b_huy = QPushButton('Hủy')
        b_huy.clicked.connect(self.reject)
        self.b_ap_dung = QPushButton('Áp dụng: tạo bộ đơn giá mới')
        self.b_ap_dung.setDefault(True)
        self.b_ap_dung.clicked.connect(self.accept)
        duoi.addWidget(b_huy)
        duoi.addWidget(self.b_ap_dung)
        lo.addLayout(duoi)
        self._ve_quy_dinh()
        self.khop()
        if self.da_co_cu:                               # cảnh báo nghiêm trọng (giá trong file có thể cũ hơn): mở sẵn thẻ Lưu ý
            self.khung_phu.setCurrentWidget(self._tr_luu)
            self.b_phu.setChecked(True)

    def _cap_nhat_phu(self):
        """Số lưu ý / quy định trên thẻ và nút; nút đỏ khi có lưu ý."""
        if not hasattr(self, 'b_phu'):
            return
        n_luu = len(self.canh) + (1 if self.lb_canh_thay.text() else 0)
        t = self.khung_phu
        i = t.indexOf(self._tr_luu)
        t.setTabText(i, f'Lưu ý ({n_luu})')
        t.setTabEnabled(i, n_luu > 0)
        i = t.indexOf(self._tr_qd)
        t.setTabText(i, f'Quy định cách tính ({len(self.quy_dinh)})')
        t.setTabEnabled(i, bool(self.quy_dinh))
        if not t.isTabEnabled(t.currentIndex()):
            for k in range(t.count()):
                if t.isTabEnabled(k):
                    t.setCurrentIndex(k)
                    break
        tong = n_luu + len(self.quy_dinh)
        self.b_phu.setText(f'Lưu ý và quy định ({tong})' if tong else 'Lưu ý và quy định')
        dau = '1' if n_luu else '0'
        if self.b_phu.property('canh') != dau:
            self.b_phu.setProperty('canh', dau)
            self.b_phu.style().unpolish(self.b_phu)
            self.b_phu.style().polish(self.b_phu)

    def _hen_dem(self, it):
        """Đổi dấu "Dùng": đếm lại sau khi xong lượt đổi (chọn cả nghìn dòng chỉ đếm một lần)."""
        if getattr(self, '_dang_ve', False) or it.column() != C_DUNG or self._cho_dem:
            return
        self._cho_dem = True
        QTimer.singleShot(0, self._dem_chon_an_toan)

    def _dem_chon_an_toan(self):
        try:
            self._dem_chon()
        except RuntimeError:                            # hộp thoại đã đóng trước khi hẹn giờ chạy
            pass

    def _dem_chon(self):
        self._cho_dem = False
        tong = chon = 0
        for i, m in enumerate(self.ds):
            if m.trang_thai in ndg.TRANG_THAI_GHI:
                tong += 1
                it = self.bang.item(i, C_DUNG)
                chon += 1 if it is not None and it.checkState() == Qt.CheckState.Checked else 0
        self.lb_dem.setText(f'Đã chọn {chon} / {tong} dòng thay đổi')

    def _bam_dau_cot(self, c: int):
        """Bấm tiêu đề cột "Dùng": chọn cả các dòng đang hiện (đã chọn hết thì bỏ chọn)."""
        if c != C_DUNG:
            return
        hien = [i for i, m in enumerate(self.ds) if not self.bang.isRowHidden(i) and m.trang_thai in ndg.TRANG_THAI_GHI]
        het = bool(hien) and all(self.bang.item(i, C_DUNG).checkState() == Qt.CheckState.Checked for i in hien)
        self.chon_theo(not het, 'hien')

    def thay_toan_bo(self) -> int:
        """Thay toàn bộ văn bản cũ bằng văn bản mới: chọn "Thay cả nhóm" rồi chọn mọi dòng thay đổi. Trả số dòng đổi dấu chọn."""
        i = self.o_cach.findData(True)
        if i >= 0 and self.o_cach.currentIndex() != i:
            self.o_cach.setCurrentIndex(i)              # so khớp lại (có mục "bỏ")
        return self.chon_theo(True)

    def thay_the(self) -> bool:
        return bool(self.o_cach.currentData())

    def _doi_cach(self, *_):
        tt = self.thay_the()
        if tt:
            self._nap_vb_cu()
        self.lb_vb_cu.setVisible(tt or bool(self.vb_cu_khop))
        self.cb_vb_cu.setVisible(tt or bool(self.vb_cu_khop))
        self.khop()

    def _nap_vb_cu(self):
        """Văn bản cũ cùng nhóm trong danh sách văn bản căn cứ; chỉ một văn bản thì chọn sẵn."""
        self.cb_vb_cu.blockSignals(True)
        self.cb_vb_cu.clear()
        self.cb_vb_cu.addItem(KHONG_VB_CU, None)
        try:
            ds = ndg.van_ban_cu_cua_nhom(set(ndg.pham_vi_thay_the(self.ds, self.o_nhom.currentData() or None)))
        except Exception:                                   # noqa: BLE001 - bộ đơn giá đọc không được: chỉ không gợi ý
            ds = []
        k = ndg.chuan_so_hieu(self.van_ban.get('so_hieu', ''))
        ds = [x for x in ds if not (k and k in ndg.chuan_so_hieu(x[1]))]        # không gợi ý chính văn bản đang nhập
        id_co = {x[0] for x in ds}
        ds = list(ds) + [x for x in self.vb_cu_khop if x[0] not in id_co]
        for i, sh, nd in ds:
            self.cb_vb_cu.addItem(sh, i)
            self.cb_vb_cu.setItemData(self.cb_vb_cu.count() - 1, nd, Qt.ItemDataRole.ToolTipRole)
        if self.vb_cu_khop:                             # 1.0.60: văn bản nêu đích danh (Điều 2 QĐ 42/2025) thắng gợi ý theo nhóm
            self.cb_vb_cu.setCurrentIndex(self.cb_vb_cu.findData(self.vb_cu_khop[0][0]))
        elif len(ds) == 1:
            self.cb_vb_cu.setCurrentIndex(1)
        self.cb_vb_cu.blockSignals(False)

    def _ve_quy_dinh(self):
        qd = self.quy_dinh
        self.o_quy_tac.setPlainText('\n'.join('• ' + (f'[{q["dieu"]}] ' if q['dieu'] else '') + ('(AI) ' if q['nguon'] == 'AI' else '')
                                               + q['chu'] for q in qd))
        so_bang = sum(1 for q in qd if q['nguon'] == 'bảng')
        so_ai = sum(1 for q in qd if q['nguon'] == 'AI')
        self.lb_qd.setText(f'Quy định cách tính trong văn bản: {len(qd)} quy định ({so_bang} trong bảng giá, '
                           f'{len(qd) - so_bang - so_ai} trong lời văn các điều khoản' + (f', {so_ai} do AI tìm thêm' if so_ai else '')
                           + ') - không có đơn giá, phần mềm không tạo mục:')
        self.o_luu_qd.setText(f'Lưu {len(qd)} quy định vào bộ đơn giá')
        self.o_luu_qd.setToolTip('Thẻ "Quy định cách tính"; mục có tên khớp phạm vi quy định được ghi thêm vào ghi chú; hiện ở Giải trình '
                                 'cách tính khi lập phương án')
        for w in (self.lb_qd, self.o_quy_tac, self.o_luu_qd):
            w.setVisible(bool(qd))
        self._cap_nhat_phu()

    def phan_tich_ai(self, khach=None, xac_nhan=None) -> str:
        """1.0.56: gửi toàn văn văn bản cho AI kiểm tra (pai). Trả chữ tóm tắt ('' = không chạy / lỗi). khach: client giả lập (kiểm thử)."""
        nd, so_xm, cat = pai.noi_dung_gui(self.dong, self.ds, self.can_xu_ly, self.o_nhom.currentData() or 0)
        if xac_nhan is None:
            xac_nhan = self.im_lang or QMessageBox.question(
                self, TEN_UD, f'Gửi chữ văn bản đơn giá ({len(nd):,} ký tự'.replace(',', '.') + f', {so_xm} dòng cần xác minh) cho AI '
                '(Claude) kiểm tra?\n\nChỉ gửi nội dung văn bản đơn giá (văn bản công khai), không gửi dữ liệu dự án / hộ dân. Có thể '
                'mất vài phút với văn bản dài.') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return ''
        try:
            if khach is not None or self.im_lang:
                kq = pai.goi_ai(nd, khach=khach)
            else:
                from .giao_dien import chay_nen_huy
                kq = chay_nen_huy(self, lambda: pai.goi_ai(nd), 'AI đang đọc toàn văn văn bản và xác minh các dòng…',
                                  gioi_han=pai.GIOI_HAN_GIAY + 30)
                if kq is None:
                    return ''
        except pai.LoiAI as e:
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, str(e))
            return ''
        self.ket_qua_ai = pai.gan_khoa(self.ds, kq)
        them_qd = pai.gop_quy_dinh(self.quy_dinh, kq)
        self._ve_quy_dinh()
        self._dem_ai = {'dung': 0, 'sai': 0, 'khong_thay': 0}
        self.khop()
        chu = pai.tom_tat(kq, self._dem_ai, them_qd, so_xm, cat)
        from .giao_dien import dat_trang_thai
        dat_trang_thai(self.lb_ai, 'tin', chu)
        self.lb_ai.setVisible(True)
        return chu

    def ten_kv(self, kv: str) -> str:
        pl = self.ten_pl.get(kv, '')
        return f'{pl} - khu vực {kv}' if pl else f'khu vực {kv}'

    def doi_khu_vuc(self, kv: str):
        """Đổi khu vực giá: '*' = cả các khu vực (tách theo khu vực); một khu vực: chỉ dòng của khu vực đó. So khớp lại."""
        if kv == self.kv:
            return
        self.kv = kv
        for m in self.ds_tat_ca:                        # so khớp khu vực trước đã đặt trạng thái / bỏ chọn: làm lại từ đầu
            m.chon = True
        self.ds = list(self.ds_tat_ca) if kv == ndg.KV_CA_HAI else ndg.loc_khu_vuc(self.ds_tat_ca, kv)
        self.khop()

    def khop(self):
        if self.kv == ndg.KV_CA_HAI:
            ndg.so_khop_khu_vuc(self.ds, self.o_nhom.currentData() or None, thay_the=self.thay_the(), scan=self.scan)
        else:
            ndg.so_khop(self.ds, self.o_nhom.currentData() or None, thay_the=self.thay_the(), scan=self.scan)
        if self.ket_qua_ai:
            self._dem_ai = pai.ap_xac_minh(self.ds, self.ket_qua_ai)
        nhom_bang = self.o_nhom.currentData() or 0
        self._khoa_tim = {}
        self._dang_ve = True
        self.bang.setRowCount(len(self.ds))
        for i, m in enumerate(self.ds):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # văn bản đã có: chỉ bỏ chọn sẵn dòng ĐỔI GIÁ (có thể ghi đè giá văn bản sau đã sửa); mục mới không ghi đè gì - vẫn chọn
            # (QĐ 31/2025 có tên trong danh sách văn bản nhưng bộ đơn giá chưa có mục vật nuôi nào)
            dung = m.chon and m.trang_thai != 'giữ nguyên' and not (self.da_co_cu and m.trang_thai == 'cập nhật')
            chk.setCheckState(Qt.CheckState.Checked if dung else Qt.CheckState.Unchecked)
            self.bang.setItem(i, C_DUNG, chk)
            # cách khớp ngoài tên (đặc trưng / dòng chung / khoảng giá) + độ giống: người dùng chỉ cần soát các dòng này
            ghi = '; '.join(x for x in (m.cach_khop, f'gần đúng {m.khop_gan:.0%}' if m.khop_gan else '',
                                        'giá cần xem lại' if m.nghi_gia and m.trang_thai != 'giữ nguyên' else '') if x)
            tt = m.trang_thai + (f' ({ghi})' if ghi else '')
            n = nhom_bang or m.nhom or 3
            # mục mới: tiền tố mã sẽ cấp khi áp dụng (số tiếp theo của bộ đơn giá - ma_tai_san.ma_tiep); mục khớp giữ mã
            if m.bo_cu:
                ma_moi = ''
            elif m.trang_thai == 'mới':
                ma_moi = m.ma or f'{m.ma_moi or ndg.TIEN_TO.get(n, "") + "…"} (mới)'
            else:
                ma_moi = m.ma_khop or m.ma
            co_cu = bool(m.ma_khop)
            gia = {C_DUNG: None,
                   C_MA_CU: m.ma_khop, C_TEN_CU: m.ten_cu if co_cu else '', C_GIA_CU: m.he_so_cu.replace('.', ',') if m.he_so else vn(m.gia_cu) if m.gia_cu is not None and co_cu else '',
                   C_GC_CU: m.ghi_chu_cu if co_cu else '',
                   C_MA: ma_moi, C_TEN: '' if m.bo_cu else (m.ten_thay or m.ten), C_DVT: '' if m.bo_cu else m.dvt,
                   C_GIA: '' if m.bo_cu else (m.he_so.replace('.', ',') if m.he_so else vn(m.don_gia)), C_GC: '' if m.bo_cu else (m.ghi_chu_thay or m.ghi_chu),
                   C_TT: tt, C_KV: self.ten_kv(m.khu_vuc) if m.khu_vuc else '', C_NHOM: TEN_NHOM_NGAN.get(n, '')}
            chu_thich = self._chu_thich(m)
            for c, v in gia.items():
                if c == C_DUNG:
                    continue
                it = QTableWidgetItem(v)
                # sửa được Tên, ĐVT, Đơn giá mới trước khi áp dụng (dòng phụ của dòng chung: sửa ở dòng đầu của nhóm)
                if c not in (C_TEN, C_DVT, C_GIA) or m.bo_cu or m.phu:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c in COT_HIEN_HANH:
                    it.setToolTip(f'Hiện hành: {m.ten_cu}' + (f'\nGhi chú: {m.ghi_chu_cu}' if m.ghi_chu_cu else '') if co_cu
                                  else 'Bộ đơn giá đang dùng chưa có mục này')
                else:
                    it.setToolTip(chu_thich)
                    it.setBackground(QBrush(MAU[m.trang_thai]))       # tô màu phần MỚI + trạng thái; phần hiện hành để nền thường
                if c in (C_GIA_CU, C_GIA):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(i, c, it)
        if len(self.ds) <= DONG_TU_CAO_TOI_DA:          # cao dòng theo chữ: đo từng dòng, bảng vài nghìn dòng thì bỏ qua
            vua_dong(self.bang)
        self._dang_ve = False
        dem = {k: sum(m.trang_thai == k for m in self.ds) for k in MAU}
        gan = sum(1 for m in self.ds if m.khop_gan)
        them = ''.join(f', {dem[k]} {chu}' for k, chu in (('đổi quy cách', 'đổi tên / quy cách'), ('bỏ', 'mục cũ không còn ghi'))
                       if dem[k])
        chung = sum(1 for m in self.ds if m.cach_khop == ndg.CACH_DONG_CHUNG)
        cap = sum(1 for m in self.ds if m.muc_gia == 'thap')
        dac = sum(1 for m in self.ds if m.cach_khop == ndg.CACH_DAC_TRUNG)
        nghi = sum(1 for m in self.ds if m.nghi_gia and m.trang_thai != 'giữ nguyên')
        tach = len({m.tach_tu for m in self.ds if m.tach_tu})
        them += (f', {chung} mục theo dòng chung' if chung else '') + (f', {cap} khoảng giá' if cap else '') + \
            (f', {dac} khớp theo đặc trưng' if dac else '') + (f', {tach} dòng nhiều loài đã tách' if tach else '') + \
            (f', {nghi} giá cần xem lại (bản scan)' if nghi else '')
        self.lb.setText(f'  {len(self.ds)} dòng: {dem["mới"]} mới, {dem["cập nhật"]} đổi giá{them}, {dem["giữ nguyên"]} không đổi'
                        + (f', {gan} khớp tên gần đúng.' if gan else '.'))
        so_vb = sum(1 for m in self.ds if not m.bo_cu)
        canh = ''
        if dem['bỏ']:
            nhom = ', '.join(ndg.NHOM_PHAM_VI.get(n, '') for n in ndg.pham_vi_thay_the(self.ds, self.o_nhom.currentData() or None))
            canh = (f'Thay thế toàn bộ danh mục {nhom}: văn bản có {so_vb} mục; {dem["bỏ"]} mục cũ không còn trong văn bản sẽ bị BỎ '
                    'khỏi bộ đơn giá (dòng đỏ, bỏ dấu "Dùng" để giữ).')
            if self.scan:
                canh += (' Văn bản đọc từ BẢN SCAN: dòng đọc hỏng cũng hiện thành "bỏ" - các dòng bỏ KHÔNG chọn sẵn, chỉ đánh dấu '
                         'mục chắc chắn văn bản mới không còn.')
            if dem['bỏ'] > so_vb:
                canh += (' Số mục bỏ nhiều hơn số mục văn bản: kiểm tra văn bản đã đọc ĐỦ các bảng / trang (bản scan, bảng nhiều '
                         'trang) và đúng nhóm trước khi áp dụng.')
        self.lb_canh_thay.setText(canh)
        self.lb_canh_thay.setVisible(bool(canh))
        self._cap_nhat_phu()
        self._loc()
        self._dem_chon()

    @staticmethod
    def can_xu_ly(m) -> bool:
        """Dòng người dùng cần nhìn: có thay đổi để ghi, giá bản scan cần xem lại, khớp tên gần đúng, tên văn bản khác chữ bộ đơn giá."""
        return m.trang_thai in ndg.TRANG_THAI_GHI or bool(m.nghi_gia) or bool(m.khop_gan) or \
            bool(m.ten_cu and m.ten_cu != (m.ten_thay or m.ten))

    def _khoa(self, i: int, m) -> str:
        """Chữ để tìm (không dấu, chữ thường): mã, tên cũ / mới, ĐVT - nhớ theo dòng, xóa khi so khớp lại."""
        k = self._khoa_tim.get(i)
        if k is None:
            k = bo_dau(' '.join(str(x or '') for x in (m.ma_khop, m.ma, m.ten_cu, m.ten_thay, m.ten, m.dvt))).lower()
            self._khoa_tim[i] = k
        return k

    def _loc(self):
        """Ẩn / hiện dòng theo ô "Hiện" và ô tìm (không đổi lựa chọn "Dùng")."""
        chi_can = self.cb_hien.currentData() == 'can'
        tim = bo_dau(self.o_tim.text()).lower().split()
        self.bang.setUpdatesEnabled(False)
        try:
            for i, m in enumerate(self.ds):
                an = chi_can and not self.can_xu_ly(m)
                if tim and not an:
                    k = self._khoa(i, m)
                    an = not all(t in k for t in tim)
                self.bang.setRowHidden(i, an)
        finally:
            self.bang.setUpdatesEnabled(True)

    def chon_theo(self, bat: bool, pham_vi: str = 'doi') -> int:
        """bat: đánh dấu "Dùng" mọi dòng có thay đổi để ghi; False: bỏ chọn mọi dòng. Trả số dòng đổi trạng thái đánh dấu.
        pham_vi: 'doi' (mặc định, mọi dòng) | 'hien' (chỉ dòng thay đổi đang hiện) | 'dao' (đảo chọn các dòng thay đổi đang hiện)."""
        n = 0
        for i, m in enumerate(self.ds):
            it = self.bang.item(i, C_DUNG)
            dang = it.checkState() == Qt.CheckState.Checked
            if pham_vi == 'doi':
                moi = bat and m.trang_thai in ndg.TRANG_THAI_GHI
            elif self.bang.isRowHidden(i) or m.trang_thai not in ndg.TRANG_THAI_GHI:
                continue
            else:
                moi = (not dang) if pham_vi == 'dao' else bat
            m.chon = moi
            if dang != moi:
                it.setCheckState(Qt.CheckState.Checked if moi else Qt.CheckState.Unchecked)
                n += 1
        return n

    @staticmethod
    def _chu_thich(m) -> str:
        """Dòng gốc của văn bản + giải thích cách khớp (02/11/2026: người dùng chỉ cần soát)."""
        giai = {ndg.CACH_DAC_TRUNG: 'Khớp theo đặc trưng (cỡ Φ, số đo, kết cấu, ĐVT, từ) - tên văn bản ghi khác tên trong bộ đơn giá.',
                ndg.CACH_DONG_CHUNG: f'Dòng chung: "{m.cha}" - một mức giá cho mọi mục cùng kết cấu của các tài sản nêu ở dòng cha.',
                ndg.CACH_THAP: f'Khoảng giá {m.khoang}: mức thấp -> mục tên không có dấu chấm cuối.',
                ndg.CACH_CAO: f'Khoảng giá {m.khoang}: mức cao -> mục tên có dấu chấm cuối (quy ước của bộ đơn giá).'}
        nghi = ''
        if m.nghi_gia:
            nghi = (f'Bản scan: {m.nghi_gia} - không chọn sẵn, đối chiếu văn bản gốc rồi đánh dấu "Dùng" nếu đúng.'
                    if m.nghi_gia.startswith(('nghi', 'cỡ')) else
                    f'Bản scan đọc ô giá "{m.nghi_gia}" không đúng dạng số tiền - giá {vn(m.don_gia)} là đoán; đối chiếu văn bản gốc.')
        tach = f'Văn bản ghi chung nhiều loài: "{m.tach_tu}" - mỗi loài một mục như bộ đơn giá.' if m.tach_tu else ''
        return '\n'.join(x for x in (m.nguon_dong, giai.get(m.cach_khop, ''), tach, nghi,
                                     m.ghi_chu if m.muc_gia and not m.ma_khop else '') if x)

    def _sua_o(self, r: int, c: int):
        """Sửa tên / ĐVT / đơn giá mới: ghi vào mục rồi so khớp lại với bộ đơn giá đang dùng (đổi trạng thái mới / đổi giá)."""
        if getattr(self, '_dang_ve', False) or c not in (C_TEN, C_DVT, C_GIA) or not 0 <= r < len(self.ds):
            return
        chu = ' '.join(self.bang.item(r, c).text().split())
        m = self.ds[r]
        if m.bo_cu or m.phu:
            return
        if c == C_GIA and m.he_so:                      # hệ số: 1,5 (lần giá đất) - không phải số tiền
            try:
                hs = str(ndg.D(chu.replace(',', '.')))
            except ValueError:
                hs = ''
            if hs and hs != m.he_so:
                m.he_so = hs
            elif not hs and not self.im_lang:
                QMessageBox.warning(self, TEN_UD, f'Hệ số "{chu}" không đọc được: gõ số (ví dụ 1,5).')
            self.khop()
            return
        if c == C_GIA:
            g = ndg.doc_gia(chu)
            if not g:
                if not self.im_lang:
                    QMessageBox.warning(self, TEN_UD, f'Đơn giá "{chu}" không đọc được: gõ số tiền (ví dụ 1.250.000).')
                self.khop()
                return
            if g == m.don_gia:
                return
            m.don_gia = g
            self.khop()
            return
        if not chu or chu == ((m.ten_thay or m.ten) if c == C_TEN else m.dvt):
            return
        if c == C_TEN:
            m.ten = chu
        else:
            m.dvt = chu
        m.ma_khop, m.gia_cu, m.khop_gan = '', None, 0.0
        self.khop()

    def accept(self):
        for i, m in enumerate(self.ds):
            m.chon = self.bang.item(i, C_DUNG).checkState() == Qt.CheckState.Checked
        luu_qd = self.quy_dinh if self.o_luu_qd is not None and self.o_luu_qd.isChecked() else None
        if not any(m.chon and m.trang_thai in ndg.TRANG_THAI_GHI for m in self.ds) and not luu_qd:
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, 'Chưa chọn dòng nào mới, đổi giá, đổi quy cách hoặc bỏ để cập nhật.')
            return
        so_bo = sum(1 for m in self.ds if m.chon and m.trang_thai == 'bỏ')
        if so_bo and not self.im_lang and QMessageBox.question(
                self, TEN_UD, f'Bỏ {so_bo} mục cũ không còn trong văn bản khỏi bộ đơn giá?\n\nBộ đơn giá hiện hành vẫn được giữ '
                              '(bộ mới là phiên bản sau); dự án đã lập phương án giữ nguyên số liệu.') != QMessageBox.StandardButton.Yes:
            return
        vb_cu = [self.cb_vb_cu.currentData()] if (self.thay_the() or self.vb_cu_khop) and self.cb_vb_cu.currentData() is not None else []
        vb_cu += [x[0] for x in self.vb_cu_khop if x[0] not in vb_cu]       # mọi văn bản bị thay thế nêu đích danh
        try:
            kv = dict(xa=self.xa_kv, ten=self.ten_pl) if self.kv == ndg.KV_CA_HAI else None
            self.ket_qua = ndg.ap_dung(self.ds, self.o_nhom.currentData() or None, self.nguon, van_ban=self.van_ban,
                                       van_ban_cu=vb_cu, quy_dinh=luu_qd, khu_vuc=kv)
        except LoiNhap as e:
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, str(e))
            return
        if not self.im_lang:
            kq = self.ket_qua
            them = ''.join(f', {kq[k]} {chu}' for k, chu in (('so_quy_cach', 'mục đổi tên / quy cách'), ('so_bo', 'mục bỏ'),
                                                              ('so_quy_dinh', 'quy định cách tính'),
                                                              ('so_muc_ghi_chu', 'mục được ghi chú quy định')) if kq.get(k))
            if kq.get('so_khu_vuc'):
                them += ('. Đã tách theo khu vực: ' + ', '.join(self.ten_kv(k) for k, _ in self.khu_vuc) + ' - dự án chỉ dùng phụ lục '
                         'của khu vực có xã dự án')
            QMessageBox.information(self, TEN_UD, f'Đã tạo bộ đơn giá phiên bản {kq["phien_ban"]}: '
                                                  f'{kq["so_moi"]} mục mới, {kq["so_cap_nhat"]} mục đổi giá{them}.')
        super().accept()
