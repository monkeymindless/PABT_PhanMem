"""Cửa sổ chính phần mềm PABT: nhập file Excel, danh sách hộ, lập phương án từng hộ, thông tin dự án, rà soát giá, đối chiếu."""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
                               QStackedWidget, QTableView, QTableWidget, QTableWidgetItem, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import BAN_THU_NGHIEM, NHAN_THU_NGHIEM, __version__, csdl, khoa, lap_pa, may_chu, nghiep_vu
from .tien import D, so_vn, vn, vn_gon
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, chu_loi

# doi_chieu, nhap_excel, nhap_tho (kéo theo openpyxl ~0,2 giây - 60% thời gian nạp mã lúc mở phần mềm) nạp khi dùng tới

TIEU_DE_CUA_SO = 'LARC' + (f' ({NHAN_THU_NGHIEM})' if BAN_THU_NGHIEM else '')   # tên hiển thị (15/10/2026: PABT -> LARC)
MO_TA_UD = 'Lập phương án bồi thường, hỗ trợ'      # tiêu đề cửa sổ khi chưa mở dự án
# danh sách hộ ở màn hình chính: gọn (0.9.12). Tiền từng mục, quyết định, chi trả, bàn giao, ghi chú: menu "Bảng tổng hợp",
# "Theo dõi tiến độ" (man_hinh_theo_doi)
COT = ['STT', 'Họ và tên', 'Địa chỉ', 'Số thửa', 'DT thu hồi (m²)', 'Trạng thái', 'Ghi chú']
MAU_LECH = QColor('#F8CBAD')          # vàng cam: hộ lệch so với file Excel đối chiếu
COT_SO = {4}
# các trang bên phải cửa sổ chính (chọn ở menu trái). 0.9.76 (Mục IV QĐ 18/2026, Nhóm 5 - 6): Bảng tổng hợp kinh phí là MỘT trang 3 thẻ
# (cơ cấu, chi tiết hộ, đối soát khái toán); Quyết định phê duyệt, Theo dõi chi trả & bàn giao, Báo cáo tiến độ GPMB (bảng điều hành)
# là ba trang riêng của Nhóm 6; Dự toán / khái toán (0.9.23 - lộ trình người dùng: mục tiêu tài chính của DỰ ÁN, trang trong cửa sổ chính)
TRANG = ['Danh sách hộ', 'Tổng hợp tiền theo phương án', 'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Báo cáo tổng hợp…',
         'Dự toán & khái toán']
TRANG_DS, TRANG_TONG_HOP, TRANG_QUYET_DINH, TRANG_THEO_DOI, TRANG_BAO_CAO, TRANG_DU_TOAN = range(6)
TRANG_CHAO = 4                     # chỉ số trong self.trang (QStackedWidget) của màn hình chào khi chưa mở dự án
# chỉ số TRANG -> chỉ số trong self.trang (QStackedWidget): 0 danh sách, 1 bảng tổng hợp, 2 theo dõi, 3 dự toán, 4 chào, 5 quyết định,
# 6 báo cáo tiến độ (các trang mới thêm cuối để giữ nguyên chỉ số cũ)
STACK_CUA_TRANG = (0, 1, 5, 2, 6, 3)
STACK_TONG_HOP, STACK_THEO_DOI, STACK_DU_TOAN, STACK_QUYET_DINH, STACK_BAO_CAO = 1, 2, 3, 5, 6
XANH, DO, VANG = QColor('#E2EFDA'), QColor('#F8CBAD'), QColor('#FFF2CC')
# menu trái: nhóm đóng sẵn lần đầu mở phần mềm (sau đó nhớ theo người dùng) - vừa màn hình 1366x768 không phải cuộn
# 0.9.70 (6 nhóm): nhóm ít dùng hằng ngày đóng sẵn - Khái toán (giai đoạn chuẩn bị đầu tư), Đơn giá, Phê duyệt & bàn giao
# 0.9.88 (người dùng 15/10/2026): nhóm Đơn giá & bảng giá xuống cuối (6); đóng sẵn 1, 5, 6 - mở sẵn 2, 3, 4 (thao tác hằng ngày)
NHOM_DONG_MAC_DINH = ('1. Khái toán & dự toán', '5. Phê duyệt & bàn giao', '6. Đơn giá & bảng giá')
GAN_DAY_TOI_DA = 8                 # số dự án nhớ trong danh sách "Dự án làm việc gần đây" (màn hình chào hiện 5)
# 0.9.80: chưa mở dự án thì các lệnh của dự án bị làm mờ (QAction tắt); mở / đóng dự án thì bật / tắt lại. Từ 0.9.88 (thứ tự nhóm
# mới): nhóm 3 (Lập phương án), 4 (Tổng hợp & trình duyệt), 5 (Phê duyệt & bàn giao) + Đơn giá đặc biệt của nhóm 6. Nhóm 1 (khái
# toán), 2, Đơn giá bồi thường, Bảng giá đất và Màn hình chính vẫn dùng được khi chưa có dự án
LENH_CAN_DU_AN = ('Lập phương án hộ…', 'Dự thảo PABT…', 'Kiểm tra lỗi…', 'Xuất báo cáo đối chiếu…',
                  'Tổng hợp tiền theo phương án', 'Đợt trình…', 'In / Xuất…',
                  'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Báo cáo tổng hợp…', 'Nhật ký kiểm toán…', 'Bản đồ thửa đất',
                  # nhóm 6 Đơn giá & bảng giá: Đơn giá đặc biệt là của DỰ ÁN (tắt khi chưa mở); Đơn giá bồi thường, Bảng giá đất vẫn
                  # bật (liên kết chân màn hình chào, tra cứu khi chưa có dự án)
                  'Đơn giá riêng dự án…')
# Nhập bản vẽ CAD, Phiếu kiểm đếm (menu Dữ liệu / Công cụ, 0.9.87): KHÔNG tắt khi chưa mở dự án - mục menu mờ bấm không có phản
# ứng, người dùng tưởng hỏng; bấm thì báo "mở dự án trước" (_can_du_an).
# nút A− / A+ trên thanh trạng thái: khung nút nhỏ, viền nhẹ, bo 4px
QSS_NUT_ZOOM = ('QToolButton#nut_zoom { border: 1px solid #CBD5E1; border-radius: 4px; padding: 1px 8px; background: #FFFFFF; '
                'color: #1E293B; font-weight: 600; }'
                'QToolButton#nut_zoom:hover { background: #F1F5F9; border-color: #94A3B8; }'
                'QToolButton#nut_zoom:pressed { background: #E2E8F0; }')
# chữ ngắn trên menu (khóa = tên lệnh đầy đủ trong self.lenh, hiện ở gợi ý khi rê chuột)
NHAN_MENU = {'Lập phương án hộ…': 'Lập phương án chi tiết', 'Thêm hộ…': 'Thêm hộ', 'Xóa hộ…': 'Xóa hộ',
             'Kiểm tra lỗi…': 'Kiểm tra lỗi pháp lý',
             # 0.9.70 (đặc tả ARCH-PABT-2026-V7, người dùng 12/10/2026): chữ trên menu trái theo 6 nhóm nghiệp vụ
             'Dự toán & khái toán': 'Lập khái toán & Dự toán', 'Danh sách hộ': 'Danh sách hộ và Thửa',
             'Theo dõi tiến độ': 'Theo dõi chi trả & Bàn giao',
             'Bộ đơn giá…': 'Đơn giá bồi thường', 'Đơn giá riêng dự án…': 'Đơn giá đặc biệt', 'Rà soát giá…': 'Rà soát giá',
             'Thông tin dự án…': 'Thông tin dự án',
             'Bảng giá đất NQ 28…': 'Bảng giá đất',
             'Cập nhật bảng giá đất…': 'Cập nhật giá đất',
             'Dự thảo PABT…': 'Niêm yết & Lấy ý kiến',
             'Tổng hợp tiền theo phương án': 'Bảng tổng hợp kinh phí',
             'Quyết định phê duyệt': 'Quyết định phê duyệt', 'Đợt trình…': 'Đợt trình thẩm định',
             'Trạng thái hộ…': 'Trạng thái hộ',
             'In / Xuất…': 'Xuất hồ sơ & Bản in', 'Báo cáo tổng hợp…': 'Báo cáo tiến độ GPMB', 'Cập nhật mẫu in…': 'Mẫu in',
             'Xuất báo cáo đối chiếu…': 'Đối chiếu số liệu'}
# 0.9.69 (người dùng 12/10/2026 đổi tên): gợi ý khi rê chuột theo tên mới (khóa self.lenh giữ tên cũ - mã / test gọi theo khóa)
GOI_Y_MENU = {'Bộ đơn giá…': 'Đơn giá bồi thường (bộ đơn giá nhà, cây, vật nuôi, chính sách hỗ trợ)',
              'Đơn giá riêng dự án…': 'Đơn giá đặc biệt của dự án (nhập tay, thẩm định giá)',
              'Dự thảo PABT…': 'Niêm yết công khai dự thảo phương án và lấy ý kiến',
              'Đợt trình…': 'Đợt trình thẩm định: đợt trình, số phương án, văn bản trình',
              'Dự toán & khái toán': 'Lập khái toán & dự toán (giai đoạn chuẩn bị đầu tư - file .pabtdt riêng)',
              'So sánh với thực tế': 'So sánh khái toán đã duyệt với số liệu áp giá thực tế của dự án',
              'Danh sách hộ': 'Danh sách hộ và thửa đất của dự án',
              'Tổng hợp tiền theo phương án': 'Bảng tổng hợp kinh phí: cơ cấu, chi tiết từng hộ, đối soát khái toán',
              'Xuất báo cáo đối chiếu…': 'Đối chiếu số liệu với file Excel kiểm đếm (xuất báo cáo)',
              'In / Xuất…': 'Xuất hồ sơ & bản in: phương án chi tiết, bảng tổng hợp, tờ trình',
              'Theo dõi tiến độ': 'Theo dõi chi trả tiền, bàn giao mặt bằng, mốc thu hồi đất, vận động và cưỡng chế',
              'Báo cáo tổng hợp…': 'Bảng điều hành tiến độ giải phóng mặt bằng: giải ngân, mặt bằng sạch, thửa còn vướng',
              'Quyết định phê duyệt': 'Quản lý quyết định phê duyệt phương án và các hộ của từng quyết định'}
TEN_TAB = {'don_gia': 'Đơn giá bồi thường', 'du_thao': 'Niêm yết && Lấy ý kiến'}   # "&&": QTabBar hiện "&"


def _file_gan_day() -> Path:
    return may_chu.thu_muc_may() / 'du_an_gan_day.json'


def doc_gan_day() -> list:
    """Đường dẫn các dự án mở gần đây (mới nhất trước) - màn hình chào."""
    import json
    try:
        ds = json.loads(_file_gan_day().read_text(encoding='utf-8'))
        return [str(x) for x in ds if isinstance(x, str)]
    except (OSError, ValueError):
        return []


def _con_tren_dia(x) -> bool:
    """False chỉ khi CHẮC file đã mất: ổ đĩa / thư mục dùng chung còn truy cập được mà không có file. Ổ mạng / USB đang ngắt
    -> giữ lại trong danh sách (cắm lại là mở được)."""
    f = Path(x)
    try:
        return f.is_file() or not Path(f.anchor).exists()
    except OSError:
        return True


def ghi_gan_day(p) -> None:
    import json
    try:
        moi = str(Path(p).resolve())
        # bỏ file không còn trên đĩa (15/10/2026): trước đây file tạm đã xóa vẫn chiếm chỗ trong GAN_DAY_TOI_DA mục, đẩy dự án thật
        # ra khỏi danh sách -> bảng "Dự án làm việc gần đây" trống dù vừa mở dự án
        ds = [moi] + [x for x in doc_gan_day() if x.lower() != moi.lower() and _con_tren_dia(x)]
        f = _file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds[:GAN_DAY_TOI_DA], ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:                                     # thư mục máy không ghi được: bỏ qua, không ảnh hưởng mở dự án
        pass


def bo_gan_day(p) -> list:
    """Xóa một đường dẫn khỏi danh sách dự án gần đây (file trên đĩa giữ nguyên)."""
    import json
    ds = [x for x in doc_gan_day() if x.lower() != str(Path(p)).lower()]
    try:
        f = _file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds[:GAN_DAY_TOI_DA], ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    return ds


def _file_ghim() -> Path:
    return may_chu.thu_muc_may() / 'du_an_ghim.json'


def doc_ghim() -> list:
    """Đường dẫn dự án được ghim lên đầu lưới gần đây."""
    import json
    try:
        ds = json.loads(_file_ghim().read_text(encoding='utf-8'))
        return [str(x) for x in ds if isinstance(x, str)]
    except (OSError, ValueError):
        return []


def ghim_du_an(p, ghim: bool = True) -> list:
    """Ghim / bỏ ghim một file .pabt. Trả danh sách ghim mới."""
    import json
    moi = str(Path(p).resolve())
    ds = [x for x in doc_ghim() if x.lower() != moi.lower()]
    if ghim:
        ds.insert(0, moi)
    try:
        f = _file_ghim()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    return ds


def _file_tong_du_an() -> Path:
    return may_chu.thu_muc_may() / 'tong_du_an.json'


def _doc_tong_nho() -> dict:
    import json
    try:
        d = json.loads(_file_tong_du_an().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_tong_nho(p, so_ho: int, tong) -> None:
    """Nhớ tổng kinh phí CHUẨN (cùng cách tính danh sách hộ: mọi mục kể cả thưởng, làm tròn như dự án) của file dự án theo thời
    điểm sửa + cỡ file - màn hình chào hiện đúng số mà không tính lại cả dự án (0.9.95). Lỗi ghi: bỏ qua."""
    import json
    try:
        st = Path(p).stat()
        d = _doc_tong_nho()
        d[str(Path(p).resolve()).lower()] = [st.st_mtime_ns, st.st_size, int(so_ho), str(tong)]
        if len(d) > 60:                                 # chỉ giữ các file gần đây
            for k in list(d)[:len(d) - 60]:
                d.pop(k, None)
        f = _file_tong_du_an()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    except (OSError, ValueError):
        pass


def _tom_tat_pabt(p) -> tuple:
    """(số hộ, chuỗi tổng tiền, chữ để tìm: tên dự án + địa bàn, tên hiển thị) đọc file dự án chỉ xem; lỗi / khóa ->
    (None, None, '', tên file). Tổng = tổng kinh phí như danh sách hộ (0.9.95: trước đây cộng thô ct_dat / ct_khoan - thiếu thưởng
    bàn giao mặt bằng, không làm tròn, lệch số danh sách hộ). Tính một lần mỗi khi file đổi (ghi_tong_nho), lần sau đọc nhớ.
    Tên hiển thị: "<tên dự án> · <địa bàn> (<tên file>)" khi có tên dự án."""
    p = Path(p)
    try:
        con = csdl.mo(str(p), chi_doc=True)
        try:
            n = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
            ten = dia_ban = ''
            try:
                r = con.execute('SELECT ten, cap_dia_ban, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
                chu_tim = ' '.join(x for x in (r or ()) if x)
                if r is not None:
                    ten, dia_ban = str(r[0] or '').strip(), str(r[2] or '').strip()
            except sqlite3.Error:
                chu_tim = ''
            hien = (f'{ten}' + (f' · {dia_ban}' if dia_ban else '') + f' ({p.name})') if ten else p.name
            tong = None
            try:
                st = p.stat()
                nho = _doc_tong_nho().get(str(p.resolve()).lower())
                if nho and nho[0] == st.st_mtime_ns and nho[1] == st.st_size:
                    tong = D(nho[3])
            except (OSError, ValueError, IndexError, TypeError):
                pass
            if tong is None and n:
                try:
                    tong = sum((k.tong for k in nghiep_vu.tinh_tat_ca(con)), D('0'))
                    ghi_tong_nho(p, n, tong)
                except Exception:                       # file cũ / hỏng: không hiện tổng, vẫn liệt kê
                    tong = None
            return n, (vn(tong) if tong else None), chu_tim, hien
        finally:
            con.close()
    except Exception:
        return None, None, '', p.name


def file_huong_dan():
    """HUONG_DAN.md: đóng gói cạnh mã (bản cài: _internal) hoặc ở gốc mã nguồn."""
    ds = [Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / 'HUONG_DAN.md'] if getattr(sys, 'frozen', False) else []
    ds.append(Path(__file__).resolve().parents[1] / 'HUONG_DAN.md')
    return next((f for f in ds if f.exists()), None)


class TheSo(QWidget):
    """Thẻ số liệu ở đầu cửa sổ chính - bấm để lọc danh sách hộ theo chỉ số đó (0.9.23: thẻ tương tác, lộ trình người dùng)."""
    bam = Signal()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint() if hasattr(e, 'position')
                                                                          else e.pos()):
            self.bam.emit()
        super().mouseReleaseEvent(e)


class LocHo(QSortFilterProxyModel):
    """Lọc danh sách hộ theo đợt trình, trạng thái xử lý và từ khóa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dot = ''                  # '' tất cả / 'chua' chưa xếp đợt / id đợt
        self.trang_thai = ''           # khóa trong quan_ly.TRANG_THAI
        self.tu_khoa = []
        self._hop_tt = None            # quan_ly.hop_trang_thai - nạp khi lần đầu lọc theo trạng thái (không nạp lúc mở phần mềm)

    def dat(self, dot=None, trang_thai=None, tu_khoa=None):
        moi = hasattr(self, 'endFilterChange')          # Qt 6.10+: invalidateFilter() lỗi thời; Qt5 / Qt6 cũ chưa có begin/end
        if moi:
            self.beginFilterChange()
        if dot is not None:
            self.dot = dot
        if trang_thai is not None:
            self.trang_thai = trang_thai
            if trang_thai and self._hop_tt is None:
                from .quan_ly import hop_trang_thai
                self._hop_tt = hop_trang_thai
        if tu_khoa is not None:
            self.tu_khoa = lap_pa.bo_dau(tu_khoa).split()
        if moi:
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:
            self.invalidateFilter()

    def filterAcceptsRow(self, r, parent):
        # gọi cho TỪNG dòng mỗi lần lọc (5.000 hộ x mỗi phím gõ): không import / tra thuộc tính thừa ở đây
        d = self.sourceModel().dong[r]
        dot = self.dot
        if dot:
            if dot == 'chua':
                if d.get('dot_id'):
                    return False
            elif d.get('dot_id') != dot:
                return False
        if self.trang_thai and not self._hop_tt(d, self.trang_thai):
            return False
        tu_khoa = self.tu_khoa
        if tu_khoa:
            chu = d.get('_tim')
            if chu is None:                             # chuỗi tìm không dấu: tính một lần cho mỗi dòng rồi nhớ trên dòng
                chu = d['_tim'] = lap_pa.bo_dau(' '.join(str(x) for x in d['o']) + ' ' + d.get('tim', ''))
            return all(t in chu for t in tu_khoa)
        return True


class BangHo(QAbstractTableModel):
    """Danh sách hộ: mỗi dòng dict(ma_ho, tong, các trường trạng thái, o=[giá trị các cột COT], tim=chữ để tìm thêm)."""

    def __init__(self, dong=None):
        super().__init__()
        self.dong = dong or []

    def dat_du_lieu(self, dong):
        self.beginResetModel()
        self.dong = dong
        self.endResetModel()

    def thay_dong(self, r: int, dong: dict):
        """Thay một dòng (hộ vừa đổi): bảng lọc / sắp xếp tự cập nhật dòng đó, không dựng lại cả danh sách."""
        self.dong[r] = dong
        self.dataChanged.emit(self.index(r, 0), self.index(r, len(COT) - 1))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.dong)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COT)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COT[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        d, c = self.dong[index.row()], index.column()
        v = d['o'][c]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if c == 4:
                return so_vn(v)
            return str(v)
        if role == Qt.ItemDataRole.ToolTipRole:
            if c == 6 and v:
                return str(v)
            if c == 5:
                return d.get('goi_y_tt') or str(v)
            if c in (1, 2):
                dau = d.get('dia_chi') or v if c == 2 else v             # cột Địa chỉ: địa chỉ đầy đủ (0.9.72)
                return f'{dau}\nMã hộ {d["ma_ho"]}' + (f'\nGhi chú: {d["theo_doi"]}' if d.get('theo_doi') else '')
            return None
        if role == Qt.ItemDataRole.UserRole:                       # giá trị để sắp xếp
            return float(v) if c in COT_SO or c in (0, 3) else str(v)
        if role == Qt.ItemDataRole.TextAlignmentRole and (c in COT_SO or c in (0, 3)):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.BackgroundRole and c == 6 and d.get('mau_gc') is not None:
            return QBrush(d['mau_gc'])
        if role == Qt.ItemDataRole.BackgroundRole and c == 5 and d.get('mau_tt') is not None:
            return QBrush(d['mau_tt'])
        return None


class ChiTietHo(QDialog):
    def __init__(self, con, ma_ho, parent=None):
        super().__init__(parent)
        k = nghiep_vu.tinh_ho(con, ma_ho)
        self.setWindowTitle(f'Hộ {ma_ho} - {k.ho_ten}')
        self.resize(1050, 640)
        cay = QTreeWidget()
        cay.setColumnCount(7)
        cay.setHeaderLabels(['STT', 'Tên tài sản, khoản', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ', 'Thành tiền (đồng)'])
        dam = QFont()
        dam.setBold(True)
        for muc in nghiep_vu.THU_TU_MUC:                # 1 đất, 2 nhà, 3 cây, 4 vật nuôi, 5 hỗ trợ, 6 thưởng
            goc = QTreeWidgetItem([str(nghiep_vu.so_muc(muc)), nghiep_vu.TEN_MUC[muc], '', '', '', '', vn(k.muc[muc])])
            for i in (0, 1, 6):
                goc.setFont(i, dam)
            goc.setTextAlignment(6, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for d in (x for x in k.dong if x.muc == muc):
                tl = lap_pa.hien_ty_le(d.ty_le)
                it = QTreeWidgetItem([d.stt, d.ten, d.dvt, so_vn(d.so_luong), vn(d.don_gia),
                                      f'{tl}%' if tl else '', vn(d.thanh_tien)])
                for i in (3, 4, 5, 6):
                    it.setTextAlignment(i, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if d.thanh_tien_excel is not None and d.thanh_tien_excel != d.thanh_tien:
                    it.setBackground(6, QBrush(DO))
                    it.setToolTip(6, f'Excel: {vn(d.thanh_tien_excel)}')
                goc.addChild(it)
            cay.addTopLevelItem(goc)
        tong = QTreeWidgetItem(['', 'TỔNG CỘNG', '', '', '', '', vn(k.tong)])
        for i in (1, 6):
            tong.setFont(i, dam)
        tong.setTextAlignment(6, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        cay.addTopLevelItem(tong)
        cay.expandAll()
        cay.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in (0, 2, 3, 4, 5, 6):
            cay.resizeColumnToContents(i)
        ghi = QPlainTextEdit()
        ghi.setReadOnly(True)
        ct = nghiep_vu.kiem_tra_ho(con, ma_ho)
        ghi.setPlainText('Cần xem lại:\n' + '\n'.join('- ' + x for x in ct) if ct else 'Không có điểm cần xem lại.')
        ghi.setMaximumHeight(120)
        lo = QVBoxLayout(self)
        lo.addWidget(cay)
        lo.addWidget(ghi)


class CuaSoChinh(QMainWindow):
    def __init__(self, menu_trai: bool = False):
        """menu_trai: các lệnh thành cột dọc bên trái (kiểu mặc định khi mở phần mềm từ 0.9.3); False: thanh nút phía trên."""
        super().__init__()
        self.menu_trai = menu_trai
        self.la_cua_so_chinh = True
        self.ht = None                                   # hoan_tac.HoanTac của dự án đang mở (Ctrl+Z / Ctrl+Y)
        self.dv = None                                   # csdl.DauVetHo: hộ vừa đổi -> tai_lai chỉ tính lại các hộ đó
        self.con = None
        self.file = None
        self.kq = None
        self.khoa = None
        self.chi_doc = False
        self.dong_ho = QTimer(self)                      # làm mới khóa file mỗi phút
        self.dong_ho.setInterval(khoa.LAM_MOI * 1000)
        self.dong_ho.timeout.connect(self.lam_moi_khoa)
        self.setWindowTitle(TIEU_DE_CUA_SO)
        man = QApplication.primaryScreen()
        vung = man.availableGeometry() if man else None
        self.resize(min(1360, vung.width() - 40) if vung else 1360, min(760, vung.height() - 40) if vung else 760)
        from .giao_dien import dat_toi_thieu_cua_so
        dat_toi_thieu_cua_so(self)          # đặc tả V10: tối thiểu 1024 x 680 (màn hình nhỏ hơn thì theo màn hình)
        self.lenh = {}
        for ten, ham in (('Dự án mới…', lambda: self.du_an_moi()),
                         ('Nhập file Excel…', lambda: self.nhap_excel()), ('Mở dự án…', self.mo_du_an),
                         ('Nhập phương án chi tiết…', lambda: self.nhap_chi_tiet()),
                         ('Thêm hộ…', lambda: self.mo_ho_so(moi=True)),
                         ('Xóa hộ…', lambda: self.xoa_ho()),
                         ('Lập phương án hộ…', lambda: self.mo_lap_pa()), ('Thông tin dự án…', lambda: self.sua_du_an()),
                         ('Rà soát giá…', lambda: self.ra_soat_gia()), ('In / Xuất…', lambda: self.in_xuat()),
                         ('Cập nhật mẫu in…', lambda: self.cap_nhat_mau_in()),
                         ('Bộ đơn giá…', lambda: self.bo_don_gia()),
                         ('Đơn giá riêng dự án…', lambda: self.don_gia_rieng()),
                         ('Xuất báo cáo đối chiếu…', self.xuat_bao_cao), ('Cập nhật phần mềm…', lambda: self.cap_nhat_phan_mem()),
                         ('Giới thiệu', self.gioi_thieu),
                         ('Lưu dự án thành…', lambda: self.luu_du_an_thanh()), ('Đợt trình…', lambda: self.dot_trinh()),
                         ('Trạng thái hộ…', lambda: self.trang_thai_ho()),
                         ('Báo cáo tổng hợp…', lambda: self.bao_cao_tong_hop()), ('Kiểm tra lỗi…', lambda: self.kiem_tra_loi()),
                         ('Xuất danh sách hộ…', lambda: self.xuat_danh_sach()),
                         ('Màn hình chính', lambda: self.ve_trang_chu()),
                         ('Bảng giá đất NQ 28…', lambda: self.bang_gia_dat()),
                         ('Dự thảo PABT…', lambda: self.mo_du_thao()),
                         ('So sánh với thực tế', lambda: self.so_sanh_du_toan()),
                         ('Chọn hộ niêm yết…', lambda: self.chon_ho_niem_yet()),
                         ('Cập nhật bảng giá đất…', lambda: self.cap_nhat_bang_gia_dat()),
                         ('Đóng dự án', lambda: self.dong_du_an_lenh()),
                         ('Xóa dự án…', lambda: self.xoa_du_an()),
                         ('Thoát', self.close),
                         ('Hướng dẫn sử dụng', lambda: self.huong_dan()),
                         ('Lưu dự án', lambda: self.luu_du_an_lenh()),
                         ('Kết nối máy chủ LAN…', lambda: self.thiet_lap_may_chu()),
                         ('Phóng to chữ', lambda: self._phong_to(1)), ('Thu nhỏ chữ', lambda: self._phong_to(-1)),
                         ('Cỡ chữ 100%', lambda: self._phong_to(0)),
                         ('Dự án trên máy chủ…', lambda: self.du_an_may_chu()),
                         # 0.9.85: gói mẫu in & cấu hình .pabtcfg (máy đơn, gửi qua Zalo / email) - chỉ ở menu Công cụ
                         ('Xuất gói mẫu in & cấu hình…', lambda: self.xuat_goi_mau()),
                         ('Nhập gói mẫu in & cấu hình…', lambda: self.nhap_goi_mau()),
                         # 0.9.86: nhật ký kiểm toán (ai sửa, cũ -> mới) - menu Dữ liệu + chuột phải danh sách hộ (cùng QAction)
                         ('Nhật ký kiểm toán…', lambda: self.nhat_ky_kiem_toan()),
                         ('Cấu hình nghiệp vụ…', lambda: self.cau_hinh_nghiep_vu()),
                         # 0.9.87: bản đồ thửa đất (menu trái nhóm 4) + nhập bản vẽ CAD .dxf (menu Dữ liệu)
                         ('Bản đồ thửa đất', lambda: self.ban_do_thua()),
                         ('Nhập bản vẽ CAD (.dxf)…', lambda: self.nhap_ban_ve_cad()),
                         # 0.9.87: chẩn đoán + sửa file dự án + gói chẩn đoán (Trợ giúp); phiếu kiểm đếm thực địa (Công cụ)
                         ('Chẩn đoán & sửa lỗi hệ thống…', lambda: self.chan_doan_he_thong()),
                         ('Phiếu kiểm đếm thực địa…', lambda: self.phieu_kiem_dem()),
                         *((t, lambda _=False, i=i: self.mo_trang(i)) for i, t in enumerate(TRANG))):
            a = QAction(ten, self)
            a.triggered.connect(lambda _=False, ham=ham: self._chay_lenh(ham))
            self.lenh[ten] = a
        for k, t in enumerate(TRANG):                   # mục trang ở menu trái: đánh dấu trang đang xem; Ctrl+1..6 chuyển trang
            self.lenh[t].setCheckable(True)
            self.lenh[t].setChecked(k == 0)
            self.lenh[t].setShortcut(QKeySequence(f'Ctrl+{k + 1}'))
            self.addAction(self.lenh[t])
        self.lenh['Màn hình chính'].setCheckable(True)
        self.lenh['Màn hình chính'].setToolTip('Về màn hình bắt đầu (dự án mới, mở dự án, nhập Excel, dự án gần đây)')
        for ten, phim in (('Dự án mới…', 'Ctrl+N'), ('Mở dự án…', 'Ctrl+O'), ('Dự án trên máy chủ…', 'Ctrl+Shift+O'),
                          ('Lưu dự án', 'Ctrl+S'),
                          ('Lưu dự án thành…', 'Ctrl+Shift+S'), ('Hướng dẫn sử dụng', 'F1')):
            self.lenh[ten].setShortcut(QKeySequence(phim))
        self._i_trang = 0                                # trang (chỉ số TRANG) đang chọn - mở lại dự án thì về trang này
        self.khung_du_toan = None                        # trang Dự toán: tạo khi mở lần đầu (không làm chậm lúc khởi động)
        self.dm = None
        self.lb_ket_qua = QLabel('')
        self.lb_ket_qua.setStyleSheet('QLabel { font-weight: bold; padding: 5px 8px; }')
        self.lb_ket_qua.setWordWrap(True)               # chữ đối chiếu dài (~980 điểm) không ép cửa sổ rộng hơn màn hình 1366
        from .giao_dien import OTimKiemThongMinh
        self.o_tim = OTimKiemThongMinh()                 # chờ ngừng gõ 200 ms: bộ gõ tiếng Việt gửi nhiều phím / chữ có dấu
        self.o_tim.setPlaceholderText('Tìm theo mã hộ, họ tên, trạng thái, ghi chú (không cần dấu)…')
        self.o_tim.setClearButtonEnabled(True)
        self.o_tim.setMinimumWidth(220)
        self.mo_hinh = BangHo()
        self.loc = LocHo(self)
        self.loc.setSourceModel(self.mo_hinh)
        self.loc.setSortRole(Qt.ItemDataRole.UserRole)
        self.o_tim.chuoi_da_doi.connect(lambda t: self._loc(tu_khoa=t))
        self.cb_dot = QComboBox()
        self.cb_dot.setMinimumWidth(120)
        self.cb_dot.addItem('Tất cả đợt', '')
        self.cb_dot.currentIndexChanged.connect(lambda *_: self._loc(dot=self.cb_dot.currentData()))
        self.cb_tt = QComboBox()
        self.cb_tt.addItem('Tất cả trạng thái', '')
        from .quan_ly import TRANG_THAI
        for k, t in TRANG_THAI:
            self.cb_tt.addItem(t, k)
        self.cb_tt.currentIndexChanged.connect(lambda *_: self._loc(trang_thai=self.cb_tt.currentData()))
        self.lb_loc = QLabel('')
        self.bang = QTableView()
        self.bang.setModel(self.loc)
        self.bang.setSortingEnabled(True)
        self.bang.setAlternatingRowColors(True)
        self.bang.setWordWrap(True)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setResizeContentsPrecision(300)    # tự canh cột: đo 300 dòng mẫu, không đo hết (3.000 hộ)
        self.bang.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.bang.doubleClicked.connect(lambda idx: self._chay_lenh(lambda: self.mo_chi_tiet(idx)))
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(lambda p: self._menu_ho(self.bang, p))
        from PySide6.QtGui import QShortcut
        phim_xoa = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.bang)    # phím Delete trên danh sách hộ
        phim_xoa.setContext(Qt.ShortcutContext.WidgetShortcut)                            # (không áp khi đang sửa ô ghi chú)
        phim_xoa.activated.connect(lambda: self.lenh['Xóa hộ…'].isEnabled() and self._chay_lenh(self.xoa_ho))
        self._vua_tieu_de()
        # trang bên phải: danh sách hộ / bảng tổng hợp (3 mục) / theo dõi tiến độ - chọn ở menu trái
        from .man_hinh_bao_cao import KhungBaoCaoTienDo
        from .man_hinh_theo_doi import KhungBangTongHop, KhungQuyetDinh, KhungTienDo
        self.bang_tong_hop = KhungBangTongHop(None, self)
        self.tien_do = KhungTienDo(None, self)
        self.quyet_dinh = KhungQuyetDinh(None, self)             # Nhóm 6: màn hình DUY NHẤT quản lý quyết định phê duyệt
        self.bao_cao = KhungBaoCaoTienDo(None, self)             # Nhóm 6: bảng điều hành tiến độ GPMB
        # trang bên phải có khung riêng, theo chỉ số trong self.trang (QStackedWidget)
        self.khung_trang = {STACK_TONG_HOP: self.bang_tong_hop, STACK_THEO_DOI: self.tien_do, STACK_QUYET_DINH: self.quyet_dinh,
                            STACK_BAO_CAO: self.bao_cao}
        for k in self.khung_trang.values():
            k.da_doi.connect(lambda: self.tai_lai(giu_trang=True))
            k.mo_ho.connect(lambda m: self.trang_thai_ho([m]))
        self.bang_tong_hop.di_den_phe_duyet.connect(lambda: self.mo_trang(TRANG_QUYET_DINH))
        self.bang_tong_hop.doi_soat.nguon_dang_mo = self._khai_toan_dang_mo
        self.bao_cao.mo_theo_doi.connect(lambda: self.mo_trang(TRANG_THEO_DOI))
        self.bao_cao.xuat_tong_hop.connect(lambda: self.bao_cao_tong_hop(ds=[d['ma_ho'] for d in self.mo_hinh.dong],
                                                                           dieu_kien='Toàn bộ các hộ của dự án'))
        hang = self._thanh_cong_cu_ds()                  # Thêm hộ, Lập phương án, Xóa hộ (theo ngữ cảnh) | bộ lọc
        nen = QWidget()
        vo = QVBoxLayout(nen)
        vo.setContentsMargins(0, 0, 0, 0)
        vo.setSpacing(0)
        than = QWidget()
        lo = QVBoxLayout(than)
        lo.setContentsMargins(10, 8, 10, 6)
        lo.setSpacing(7)
        from .giao_dien import bang_to_chuc, thanh_lenh
        from .giao_dien import menu_trai as tao_menu_trai
        L = self.lenh
        # 0.9.20 (người dùng yêu cầu "gọn chữ"): chữ trên menu ngắn (NHAN_MENU, tên đầy đủ ở gợi ý); khóa self.lenh giữ tên cũ
        for k, ngan in NHAN_MENU.items():
            L[k].setText(ngan.replace('&', '&&'))      # "&" trên chữ QAction là phím tắt gạch dưới
            L[k].setToolTip(GOI_Y_MENU.get(k, k.rstrip('…')))
        for k in TRANG:                                  # "&" trong chữ QAction = phím tắt gạch dưới: viết "&&" để hiện "&"
            if '&' in k and k not in NHAN_MENU:
                L[k].setText(k.replace('&', '&&'))
        # 0.9.23 (lộ trình người dùng): 5 nhóm theo vòng đời nghiệp vụ - dự án -> bảng giá -> lập phương án -> tổng hợp, trình ->
        # tiến độ. Thao tác file (tạo / mở / lưu / nhập) lên thanh menu Tệp tin / Dữ liệu (trước: nút xổ "DỰ ÁN ▾" đầu menu trái,
        # danh sách xổ đè lên các nút bên dưới); Thêm hộ / Xóa hộ (thao tác theo hộ đang chọn) ở thanh công cụ của danh sách hộ.
        # Mọi nơi dùng chung MỘT QAction mỗi lệnh (cùng trạng thái tắt khi chỉ xem).
        # 0.9.70 (đặc tả ARCH-PABT-2026-V7 - người dùng 12/10/2026): "Màn hình chính" là nút độc lập đầu menu (nhóm không tên),
        # rồi 6 nhóm theo 16 bước của QĐ 18/2026. Cập nhật bảng giá đất -> menu Công cụ, Trạng thái hộ -> menu Dữ liệu (vẫn ở
        # chuột phải danh sách hộ). Khái toán tách nhóm riêng: dữ liệu .pabtdt độc lập với dự án triển khai .pabt
        nhom = [
            (None, [L['Màn hình chính']]),
            ('1. Khái toán & dự toán', [L['Dự toán & khái toán'], L['So sánh với thực tế']]),
            ('2. Dự án triển khai', [L['Thông tin dự án…'], L['Danh sách hộ']]),
            ('3. Lập phương án', [L['Lập phương án hộ…'], L['Dự thảo PABT…'], L['Bản đồ thửa đất'], L['Kiểm tra lỗi…'],
                                  L['Xuất báo cáo đối chiếu…']]),
            ('4. Tổng hợp & trình duyệt', [L['Tổng hợp tiền theo phương án'], L['Đợt trình…'], L['In / Xuất…']]),
            # mọi việc về quyết định ở MỘT chỗ: trang "Quyết định phê duyệt" (Thêm / Nhập từ file / Sửa / Xóa)
            ('5. Phê duyệt & bàn giao', [L['Quyết định phê duyệt'], L['Theo dõi tiến độ'], L['Báo cáo tổng hợp…']]),
            ('6. Đơn giá & bảng giá', [L['Bộ đơn giá…'], L['Đơn giá riêng dự án…'], L['Bảng giá đất NQ 28…']]),
        ]
        # hoàn tác / làm lại thao tác đã ghi vào file dự án: menu Chỉnh sửa trên thanh menu (người dùng 11/10/2026 - như các phần
        # mềm khác; trước đây nút trên băng tiêu đề). Chữ "Ctrl+Z" sau "\t" chỉ để hiện: KHÔNG gắn phím tắt cho QAction - phím
        # tắt của QAction được xử lý trước KeyPress, làm hỏng giao_dien.xu_ly_hoan_tac (Ctrl+Z theo khung đang làm việc)
        from .giao_dien import XU_LY_HOAN_TAC, icon_ky_hieu, ky_hieu_nut, mau_icon
        self.nut_ht = {}
        for k, chu, lai in (('lui', 'Hoàn tác', False), ('toi', 'Làm lại', True)):
            a = QAction(chu, self)
            ic = icon_ky_hieu(ky_hieu_nut(chu), mau_icon(chu), 18)
            if ic is not None:
                a.setIcon(ic)
            a.triggered.connect(lambda _=False, x=lai: self.hoan_tac(x))
            self.nut_ht[k] = a
        self._thanh_menu()
        self.bang_tieu_de = bang_to_chuc(f'Phiên bản {__version__}')
        self.bang_tieu_de.setParent(self)                 # giữ cho test / dat_to_chuc; không xếp vào layout (V5: header 38px)
        self.bang_tieu_de.hide()
        vo.addWidget(self.banner_ten)
        vo.addWidget(than, 1)
        if self.menu_trai:
            ngang = QHBoxLayout()
            ngang.setSpacing(8)
            # bấm tiêu đề nhóm để đóng / mở - menu không tràn màn hình 1366x768
            self.khung_menu = tao_menu_trai(nhom, dong_mac_dinh=NHOM_DONG_MAC_DINH)
            ngang.addWidget(self.khung_menu)
            phai = QVBoxLayout()
            phai.setSpacing(7)
            ngang.addLayout(phai, 1)
            lo.addLayout(ngang, 1)
        else:                                           # kiểu cũ (--menu-tren): thanh nút, kèm nhóm Dự án như trước
            lo.addWidget(thanh_lenh([('Dự án', [L['Dự án mới…'], L['Mở dự án…'], L['Lưu dự án thành…'],
                                                L['Nhập file Excel…'], L['Nhập phương án chi tiết…']]), *nhom]))
            phai = lo
        self.hang_the = QWidget()                        # thẻ số liệu (ẩn ở màn hình chào)
        self.hang_the.setLayout(self._hang_the_so())
        self.hang_the.layout().setContentsMargins(0, 0, 0, 0)
        phai.addWidget(self.hang_the)
        trang_ds = QWidget()
        lo_ds = QVBoxLayout(trang_ds)
        lo_ds.setContentsMargins(0, 0, 0, 0)
        lo_ds.setSpacing(7)
        # băng kết quả đối chiếu; Lập phương án / Thêm hộ chỉ ở menu trái (+ bấm đúp, chuột phải) - không lặp nút ở đây
        hang_kq = QHBoxLayout()                         # kết quả đối chiếu | số hộ đang hiện theo bộ lọc
        hang_kq.addWidget(self.lb_ket_qua, 1)
        hang_kq.addWidget(self.lb_loc)
        lo_ds.addLayout(hang_kq)
        lo_ds.addLayout(hang)
        lo_ds.addWidget(self.bang, 1)
        self.lb_trang = QLabel('')
        self.lb_trang.setProperty('vai', 'tieu_de')
        self.lb_trang.setVisible(False)
        from .giao_dien import KhungLamViecDaTab
        self.khung_tab = KhungLamViecDaTab(self)         # V5: tab trang chính + hộ / bộ đơn giá (giữ RAM)
        self.thanh_tab = self.khung_tab.bar
        self._tab_khoa = self.khung_tab.khoa
        self.khung_tab.da_doi.connect(self._tab_doi_khoa)
        self.khung_tab.yeu_cau_dong.connect(self._tab_dong)
        from PySide6.QtGui import QShortcut
        for chu, buoc in (('Ctrl+Tab', 1), ('Ctrl+Shift+Tab', -1)):
            phim = QShortcut(QKeySequence(chu), self)
            phim.activated.connect(lambda b=buoc: self._tab_ke(b))
        # thanh tab KHÔNG xếp vào bố cục (15/10/2026, người dùng: thu hồi ~40 px chiều cao) - chuyển trang bằng menu trái /
        # thanh menu (Ctrl+1..6 = các trang); khung_tab chỉ giữ danh sách trang / tab hộ đang mở trong RAM
        self.trang = QStackedWidget()
        self.trang_dt = QWidget()                        # trang Dự toán & khái toán (KhungDuToan tạo khi mở lần đầu)
        lo_dt = QVBoxLayout(self.trang_dt)
        lo_dt.setContentsMargins(0, 0, 0, 0)
        for w in (trang_ds, self.bang_tong_hop, self.tien_do, self.trang_dt, self._trang_chao(), self.quyet_dinh, self.bao_cao):
            self.trang.addWidget(w)
        self.ngan_lv = QStackedWidget()
        self.trang.currentChanged.connect(lambda *_: self._cap_nhat_hien_hang_the())
        self.ngan_lv.currentChanged.connect(lambda *_: self._cap_nhat_hien_hang_the())
        self.ngan_lv.addWidget(self.trang)
        self.ngan_lv.addWidget(self.khung_tab.stack_phu)
        phai.addWidget(self.lb_trang)
        phai.addWidget(self.ngan_lv, 1)
        self.bang.selectionModel().selectionChanged.connect(lambda *_: self._cap_nhat_chon())
        self.setCentralWidget(nen)
        self.lb_tom_tat = QLabel('Sẵn sàng')             # thanh trạng thái: Sẵn sàng · tổng số hộ | đã chọn
        self.lb_tom_tat.setToolTip('Nhấp đúp một hộ để lập / sửa phương án.')
        self.statusBar().addWidget(self.lb_tom_tat, 1)
        # cỡ giao diện: nút − / + , bấm vào % để về 100%; phím Ctrl + con lăn chuột, Ctrl + "+" / "-" / "0"
        from .giao_dien import KHI_DOI_TY_LE, TY_LE, phong_to
        goi_y = 'Cỡ giao diện: Ctrl + con lăn chuột, hoặc Ctrl + "+" / Ctrl + "-"; Ctrl + 0 về 100%'
        self.nut_ty_le = {}
        for k, chu, buoc in (('nho', 'A−', -1), ('ty_le', '', 0), ('to', 'A+', 1)):
            b = QToolButton()
            b.setText(chu)
            b.setToolTip(goi_y)
            b.setAutoRaise(True)
            if k != 'ty_le':                            # 0.9.80: A− / A+ có khung nút (viền nhẹ, bo 4px); "110%" là chữ bấm về 100%
                b.setObjectName('nut_zoom')
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(QSS_NUT_ZOOM)
            b.clicked.connect(lambda _=False, x=buoc: phong_to(x))
            self.statusBar().addPermanentWidget(b)
            self.nut_ty_le[k] = b
        self._hien_ty_le(TY_LE[0])
        KHI_DOI_TY_LE.append(self._hien_ty_le)
        XU_LY_HOAN_TAC.append(self.hoan_tac_phim)
        self._cap_nhat_nut_ht()
        self.nut_tk = QToolButton()                            # tài khoản / máy chủ LAN
        self.nut_tk.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.nut_tk.setMenu(QMenu(self.nut_tk))
        self.nut_tk.menu().aboutToShow.connect(self._menu_tai_khoan)
        self.statusBar().addPermanentWidget(self.nut_tk)
        self.cap_nhat_tai_khoan()
        # Cập nhật phần mềm / Giới thiệu: menu Trợ giúp (trước 0.9.23 thêm hai nút ở góc dưới - mỗi lệnh một chỗ)
        self._cap_nhat_lenh_theo_du_an()                # chưa mở dự án: làm mờ nhóm 3, 4, 5 + Đơn giá đặc biệt
        self._hien_trang_chao()

    # ------------------------------------------------ lệnh
    def nhap_excel(self, xl=None, dich=None):
        """Nhập file PABT Excel (mẫu .xlsm) hoặc file Excel bất kỳ có họ tên, địa chỉ, tờ, thửa, DT thu hồi, loại đất."""
        if xl is None:
            xl, _ = QFileDialog.getOpenFileName(self, 'Chọn file Excel (file PABT hoặc danh sách hộ, thửa)', '',
                                                'File Excel (*.xlsm *.xlsx)')
            if not xl:
                return
        from . import nhap_excel, nhap_tho
        try:
            tho = not nhap_tho.la_file_pabt(xl)
        except Exception as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không đọc được file', e))
            return
        from . import nhap_chi_tiet
        if tho and dich is None and nhap_chi_tiet.la_file_chi_tiet(xl):    # mỗi sheet một phương án chi tiết
            return self.nhap_chi_tiet(xl)
        if dich is None:
            mac_dinh = str(self.file if tho and self.file else Path(xl).with_suffix(csdl.DUOI_DU_AN))
            hoi = {'options': QFileDialog.Option.DontConfirmOverwrite} if tho else {}   # tự hỏi "xóa trắng" bên dưới
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu vào file dự án', mac_dinh, csdl.LOC_LUU, **hoi)
            if not dich:
                return
            if tho and Path(dich).exists() and QMessageBox.question(
                    self, TEN_UD, f'XÓA TRẮNG toàn bộ hồ sơ hộ, thửa, phương án trong\n{dich}\nrồi nhập danh sách mới?\n\n'
                                  'Danh mục đơn giá, tham số của file được giữ nguyên.') != QMessageBox.StandardButton.Yes:
                return
        k = khoa.KhoaFile(dich).nguoi_khac()
        if k:
            QMessageBox.warning(self, TEN_UD, f'File dự án đang được sửa trên {khoa.mo_ta(k)}.\nKhông ghi đè được.')
            return
        danh_muc = self.file if tho and self.file and not Path(dich).exists() else None
        try:
            with con_tro_cho():
                self.dong_du_an()
                from .giao_dien import chay_nen                 # luồng nền (tự mở kết nối file đích): file lớn không làm treo cửa sổ
                bc = chay_nen(self, lambda: nhap_tho.nhap(xl, dich, danh_muc=danh_muc) if tho else nhap_excel.nhap(xl, dich),
                              f'Đang nhập {Path(xl).name}…')
        except Exception as e:                       # file hỏng, đang mở khóa...
            QMessageBox.critical(self, TEN_UD, chu_loi('Không nhập được file', e))
            return
        if bc.loi:
            from .giao_dien import hop_ket_qua
            hop_ket_qua(self, 'Không nhập được file.', bc.loi, 'Lý do', canh_bao=True, tieu_de=TEN_UD)
            return
        tb = f'Đã nhập {bc.so_ho} hộ, {bc.so_thua} thửa, {sum(bc.so_dong.values())} dòng phương án.'
        if tho:
            tb += '\n\nNhận cột: ' + bc.nhan_cot
        from .giao_dien import hop_ket_qua                  # ô cuộn: đủ mọi lưu ý, nút Đóng luôn trong màn hình
        hop_ket_qua(self, tb, bc.canh_bao, 'Lưu ý', tieu_de=TEN_UD)
        self.mo(dich)

    def _ghi_chi_tiet_co_tien_do(self, nhap_chi_tiet, kq, cach: str, nguon: str, hien: bool = True):
        """nhap_chi_tiet.ghi vào dự án đang mở với QProgressDialog (hiện sau 0,5 s, nút Dừng)."""
        hop = None
        if hien and len(kq.ho) > nhap_chi_tiet.BAO_MOI:
            from PySide6.QtWidgets import QApplication, QProgressDialog
            hop = QProgressDialog('Đang ghi phương án chi tiết vào dự án…', 'Dừng', 0, len(kq.ho), self)
            hop.setWindowTitle(TEN_UD)
            hop.setWindowModality(Qt.WindowModality.WindowModal)
            hop.setMinimumDuration(500)

        def bao(i, n):
            if hop is None:
                return False
            hop.setValue(i)
            hop.setLabelText(f'Đang ghi phương án chi tiết: hộ {i + 1} / {n}…')
            QApplication.processEvents()
            return hop.wasCanceled()
        try:
            return nhap_chi_tiet.ghi(self.con, kq.ho, cach, nguon, kq.du_an, bao_tien_do=bao)
        finally:
            if hop is not None:
                hop.close()
                hop.deleteLater()

    def nhap_chi_tiet(self, xl=None, dich=None, sheet: list | None = None, trung: str | None = None, cho: bool = True):
        """Nhập file Excel phương án chi tiết (mỗi sheet một hộ) vào dự án đang mở, hoặc dự án mới khi chưa mở dự án.
        Kiểm thử: dich (file dự án mới), sheet (tên sheet), trung, cho=False (không hiện hộp thoại)."""
        from . import nhap_chi_tiet
        if xl is None:
            xl, _ = QFileDialog.getOpenFileName(self, 'Chọn file Excel phương án chi tiết (mỗi sheet một hộ)', '',
                                                'File Excel (*.xlsm *.xlsx)')
            if not xl:
                return None
        try:
            with con_tro_cho():
                from .giao_dien import chay_nen                 # chỉ đọc file Excel: chạy nền, cửa sổ không treo khi file nhiều sheet
                kq = chay_nen(self, lambda: nhap_chi_tiet.doc(xl), f'Đang đọc {Path(xl).name}…')
        except Exception as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không đọc được file', e))
            return None
        if not kq.ho:
            QMessageBox.warning(self, TEN_UD, 'File không có sheet phương án chi tiết nào (bảng STT / Tên tài sản / Số lượng / '
                                              'Thành tiền và dòng "Họ và tên").')
            return None
        vao_mo = self.con is not None and not self.chi_doc and dich is None
        if not vao_mo and dich is None:
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu vào file dự án', str(Path(xl).with_suffix(csdl.DUOI_DU_AN)),
                                                  csdl.LOC_LUU)
            if not dich:
                return None
        con_xem = self.con if vao_mo else (csdl.mo(dich, chi_doc=True) if dich and Path(dich).exists() else None)
        try:
            ten = con_xem.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()[0] if con_xem is not None else ''
            from .man_hinh_nhap_chi_tiet import HopNhapChiTiet
            hop = HopNhapChiTiet(kq, con_xem, self, ten)
            if cho and hop.exec() != QDialog.DialogCode.Accepted:
                return None
            if sheet is not None:
                for h in kq.ho:
                    h.chon = h.sheet in sheet and not h.loi
                cach = trung or 'bo_qua'
            else:
                cach = trung or hop.ap_dung()
        finally:
            if con_xem is not None and con_xem is not self.con:
                con_xem.close()
        if not vao_mo:
            k = khoa.KhoaFile(dich).nguoi_khac()
            if k:
                QMessageBox.warning(self, TEN_UD, f'File dự án đang được sửa trên {khoa.mo_ta(k)}.\nKhông ghi được.')
                return None
        try:
            with con_tro_cho():
                if vao_mo:
                    # dự án đang mở: ghi ở luồng giao diện (giữ Hoàn tác) + hộp tiến trình mỗi 10 hộ, Dừng = hoàn tác cả lô
                    bc = self._ghi_chi_tiet_co_tien_do(nhap_chi_tiet, kq, cach, Path(xl).name, cho)
                else:
                    if self.file is not None and Path(dich).resolve() == self.file.resolve():
                        self.dong_du_an()
                    from .giao_dien import chay_nen         # file khác (kết nối riêng): ghi ở luồng nền, cửa sổ không treo
                    bc = chay_nen(self, lambda: nhap_chi_tiet.ghi_file(kq, dich, cach), f'Đang ghi vào {Path(dich).name}…')
        except nhap_chi_tiet.DaDung as e:
            QMessageBox.information(self, TEN_UD, str(e))
            return None
        except Exception as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không nhập được', e))
            return None
        if vao_mo:
            self.tai_lai()
        else:
            self.mo(dich)
        if cho:                                         # hộp có ô cuộn: danh sách dài không đẩy nút Đóng ra ngoài màn hình
            from .giao_dien import hop_ket_qua
            ngan, ds = nhap_chi_tiet.ket_qua(bc)
            hop_ket_qua(self, ngan, ds, tieu_de=TEN_UD)
        return bc

    def mo_du_an(self):
        tm = self.file.parent if self.file else may_chu.thu_muc_mac_dinh()
        p, _ = QFileDialog.getOpenFileName(self, 'Mở dự án', str(tm), csdl.LOC_MO)
        if p:
            self.mo(p)

    def mo(self, p, chi_doc: bool | None = None):
        """Mở dự án. File đang được máy khác sửa thì hỏi: mở chỉ xem / vẫn mở để sửa (chi_doc: bỏ qua câu hỏi)."""
        try:
            if self.dong_du_an() is False:
                return
            kf = khoa.KhoaFile(p)
            k = kf.nguoi_khac()
            if k and chi_doc is None:
                hop = QMessageBox(QMessageBox.Icon.Warning, TEN_UD, f'File dự án đang được sửa trên {khoa.mo_ta(k)}.\n\n'
                                  'Mở chỉ xem để tránh hai người cùng sửa ghi đè lên nhau.', parent=self)
                nut_xem = hop.addButton('Mở chỉ xem', QMessageBox.ButtonRole.AcceptRole)
                nut_sua = hop.addButton('Vẫn mở để sửa', QMessageBox.ButtonRole.DestructiveRole)
                hop.addButton('Hủy', QMessageBox.ButtonRole.RejectRole)
                hop.exec()
                if hop.clickedButton() not in (nut_xem, nut_sua):
                    return
                chi_doc = hop.clickedButton() is nut_xem
            chi_doc = bool(chi_doc)
            if not chi_doc:
                kf.lay(ep=True)
                self.khoa = kf
                self.dong_ho.start()
            self.chi_doc = chi_doc
            self.con = csdl.mo(p, chi_doc=chi_doc)
            if not chi_doc:
                from .hoan_tac import HoanTac
                self.ht = HoanTac(self.con, hen=lambda ham: QTimer.singleShot(0, ham))
                self.ht.khi_doi.append(self._cap_nhat_nut_ht)
                try:
                    self.dv = csdl.DauVetHo(self.con)
                except Exception:                      # không tạo được: vẫn mở dự án, tai_lai nạp toàn bộ như trước
                    self.dv = None
                try:                                   # nhật ký kiểm toán (0.9.86): ai sửa, cũ -> mới
                    from . import kiem_toan
                    kiem_toan.gan(self.con)
                except sqlite3.Error:                  # file đang khóa / lỗi: vẫn mở dự án (nhat_ky vẫn ghi thao tác)
                    pass
            self._cap_nhat_nut_ht()
            self.file = Path(p)
            self.dm = lap_pa.DanhMuc(self.con)
            # chỉ xem: tắt mọi lệnh ghi. Mỗi lệnh một QAction dùng chung cho menu trái / chuột phải - không còn nút gọi thẳng
            # hàm (trước 0.9.18 hai nút nhanh "Thêm hộ…", "Lập phương án hộ đang chọn" vẫn bật khi chỉ xem -> lỗi ghi CSDL)
            for ten in ('Thêm hộ…', 'Xóa hộ…', 'Lập phương án hộ…', 'Thông tin dự án…', 'Trạng thái hộ…'):
                self.lenh[ten].setEnabled(not chi_doc)
            self.lenh['Đóng dự án'].setEnabled(True)
            self.lenh['Xóa dự án…'].setEnabled(True)
            self._cap_nhat_lenh_theo_du_an()            # mở dự án: bật sáng toàn bộ menu (Lập phương án vẫn tắt khi chỉ xem)
            for k in self.khung_trang.values():
                k.dat_du_an(self.con, chi_doc)
            if self.khung_du_toan is not None:
                self.khung_du_toan.dat_du_an(self.con, self.file)
            self.tai_lai()
            # mở / nhập dự án: luôn vào Danh sách hộ (người dùng 12/10/2026 - trước: về trang chọn lần trước, ví dụ Dự toán)
            self.mo_trang(0)
            ghi_gan_day(self.file)
            from .man_hinh import lam_san                 # lúc rảnh: dựng sẵn danh sách chọn của cửa sổ lập phương án
            dm = self.dm
            QTimer.singleShot(400, lambda: dm is self.dm and lam_san(dm))
            if may_chu.PHIEN is not None:                   # đăng nhập máy chủ: máy khác đăng nhập cùng tài khoản sẽ mở tiếp dự án
                import threading                            # luồng riêng: máy chủ chậm / mất mạng không làm chậm việc mở dự án
                threading.Thread(target=may_chu.ghi_mo_du_an, args=(self.file,), daemon=True).start()
        except Exception as e:
            self.dong_du_an()
            QMessageBox.critical(self, TEN_UD, chu_loi('Không mở được dự án', e))

    def _cap_nhat_lenh_theo_du_an(self):
        """Chưa mở dự án: tắt các lệnh của nhóm 3, 4, 5 + Đơn giá đặc biệt (LENH_CAN_DU_AN); có dự án: bật (riêng Lập phương án hộ vẫn tắt khi chỉ xem)."""
        co = self.con is not None
        for ten in LENH_CAN_DU_AN:
            a = self.lenh.get(ten)
            if a is not None:
                a.setEnabled(co and not (self.chi_doc and ten == 'Lập phương án hộ…'))
                if not co:
                    a.setStatusTip('Mở hoặc tạo dự án để dùng chức năng này')

    def lam_moi_khoa(self):
        if self.khoa is not None and not self.khoa.lam_moi():
            self.dong_ho.stop()
            k = self.khoa.doc() or {}
            QMessageBox.warning(self, TEN_UD, f'Một máy khác ({khoa.mo_ta(k)}) đã mở file dự án để sửa.\n'
                                              'Hai máy cùng sửa có thể ghi đè số liệu của nhau: hãy thống nhất chỉ một máy sửa.')

    def dong_du_an(self):
        if hasattr(self, 'khung_tab') and not self._dong_tab_phu(hoi=True):
            return False
        if self.con is not None and self.file is not None and self.kq is not None:
            try:                                        # nhớ tổng chuẩn cho bảng dự án gần đây (màn hình chào)
                self.con.commit()
            except sqlite3.Error:
                pass
            ghi_tong_nho(self.file, len(self.kq.ho), sum((h['tong'] for h in self.kq.ho), D('0')))
        self.dong_ho.stop()
        if self.khoa is not None:
            self.khoa.nha()
            self.khoa = None
        self.chi_doc = False
        for a in self.lenh.values():
            a.setEnabled(True)
        if self.ht is not None:
            self.ht.dong()
            self.ht = None
        self.dv = None
        if self.con is not None:
            self.con.close()
            self.con = None
        self._cap_nhat_lenh_theo_du_an()                # đóng dự án: làm mờ lại nhóm 3, 4, 5 (+ Đơn giá đặc biệt) của menu trái
        if hasattr(self, 'nut_ht'):
            self._cap_nhat_nut_ht()
        self.kq = None
        self.dm = None
        self.mo_hinh.dat_du_lieu([])
        if hasattr(self, 'khung_trang'):
            for k in self.khung_trang.values():
                k.dat_du_an(None)
        if getattr(self, 'khung_du_toan', None) is not None:
            self.khung_du_toan.dat_du_an(None)
        self._xoa_ket_qua()
        self.lb_loc.setText('')
        self._cap_nhat_the_so()
        if hasattr(self, 'trang'):
            self._hien_trang_chao()
        return True

    TAI_LAI_HO_TOI_DA = 200        # đổi nhiều hộ hơn (cập nhật trạng thái hàng loạt...): nạp lại toàn bộ

    def tai_lai(self, giu_trang: bool = False):
        """Nạp lại danh sách hộ (và các trang tổng hợp, tiến độ). giu_trang: gọi từ trang tổng hợp / tiến độ sau khi ghi.
        Chỉ một số hộ đổi (csdl.DauVetHo - lưu phương án, sửa hồ sơ, trạng thái một hộ, hoàn tác...): tính và vẽ lại các hộ đó;
        thêm / xóa hộ, đổi danh mục, dự án, quyết định, đợt, hoặc máy khác ghi vào file: nạp lại toàn bộ như trước."""
        doi = self.dv.lay() if self.dv is not None else None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            xong = False
            if self.kq is not None and doi is not None:
                try:
                    xong = self._tai_lai_ho(doi)
                except Exception:                      # tính riêng từng hộ lỗi: nạp lại toàn bộ (không để danh sách sai)
                    xong = False
            if not xong:
                self._tai_lai_toan_bo()
            self._sau_tai_lai(giu_trang)
        finally:
            QApplication.restoreOverrideCursor()

    def _so_lieu_dong(self, ds_ma_ho=None) -> tuple:
        """(số thửa + DT, trường trạng thái trên bảng ho, TongHopHo, tên đợt) để dựng dòng danh sách; ds_ma_ho: chỉ các hộ này."""
        from . import theo_doi
        from .quan_ly import TRUONG_TT, ds_dot
        loc, ts = '', ()
        if ds_ma_ho is not None:
            loc, ts = f' WHERE ma_ho IN ({",".join("?" * len(ds_ma_ho))})', tuple(ds_ma_ho)
        so_thua = {r[0]: (r[1], D(r[2] or 0)) for r in self.con.execute(
            f"SELECT ma_ho, COUNT(*), SUM(CAST(dt_thu_hoi AS REAL)) FROM thua{loc} GROUP BY ma_ho", ts)}
        tt = {r['ma_ho']: dict(r) for r in self.con.execute(
            f'SELECT ma_ho, trang_thai, dot_id, dia_chi, {", ".join(TRUONG_TT)} FROM ho{loc}', ts)}
        th = {x.ma_ho: x for x in theo_doi.tong_hop(self.con, ds_ma_ho, tinh_pa=False)}
        ten_dot = {d.id: d.ten for d in ds_dot(self.con)}
        r = self.con.execute('SELECT ten_dia_ban FROM du_an WHERE id = 1').fetchone()
        return so_thua, tt, th, ten_dot, (r[0] or '') if r else ''

    @staticmethod
    def _dong_ho(i: int, h: dict, so_lieu: tuple) -> dict:
        """Một dòng danh sách hộ (BangHo) từ kết quả đối chiếu h của hộ và số liệu _so_lieu_dong."""
        from .man_hinh_theo_doi import VANG as MAU_VANG, XANH as MAU_XANH
        from .quan_ly import TRUONG_TT
        from .ho_so import rut_gon_dia_chi
        so_thua, tt, th, ten_dot, dia_ban = so_lieu
        st, dt = so_thua.get(h['ma_ho'], (0, D(0)))
        x = tt.get(h['ma_ho'], {})
        t = th.get(h['ma_ho'])
        if t is not None:
            t.tong_pa = h['tong']
            trang_thai = t.trang_thai
            goi_y = '\n'.join([f'QĐ {q["so_qd"]} ({q["ngay_qd"]}): {vn(q["so_tien"]) if q["so_tien"] else "?"} đ - '
                               + (f'đã nhận {q["chi_tra_ngay"]}' if q['da_chi_tra'] else 'chưa nhận') for q in t.qd]
                              + [f'Bàn giao: {t.ban_giao_ngay or "đã"}' if t.da_ban_giao else '',
                                 f'Đợt trình: {ten_dot[x["dot_id"]]}' if x.get('dot_id') in ten_dot else '']).strip()
            mau = MAU_XANH if t.da_ban_giao else (MAU_VANG if t.qd else None)
            if t.qd and t.qd_chua_nhan and len(t.qd_chua_nhan) == len(t.qd):
                mau = None
        else:
            trang_thai, goi_y, mau = x.get('trang_thai', ''), '', None
        gc = h.get('ghi_chu_dc') or ''
        da_lap = bool(getattr(t, 'da_lap', False) or (t is not None and t.tong_pa > 0))
        return dict(ma_ho=h['ma_ho'], tong=h['tong'], lech=h['lech'], da_lap=da_lap,
                    **{k: x.get(k) for k in TRUONG_TT},
                    dot_id=x.get('dot_id'), goi_y_tt=goi_y, mau_tt=mau, mau_gc=MAU_LECH if gc else None,
                    tim=f'{h["ma_ho"]} {x.get("theo_doi") or ""} {ten_dot.get(x.get("dot_id"), "")} '
                        f'{x.get("qd_so") or ""} {x.get("dia_chi") or ""}',
                    dia_chi=x.get('dia_chi') or '',          # đầy đủ (chú thích); cột hiện bản gọn theo địa bàn dự án
                    o=[i, h['ho_ten'], rut_gon_dia_chi(x.get('dia_chi'), dia_ban), st, dt.quantize(D('0.1')), trang_thai, gc])

    def _tai_lai_toan_bo(self):
        from . import doi_chieu
        self.kq = doi_chieu.doi_chieu(self.con)
        so_lieu = self._so_lieu_dong()
        self.mo_hinh.dat_du_lieu([self._dong_ho(i, h, so_lieu) for i, h in enumerate(self.kq.ho, start=1)])
        self._nap_ds_dot(so_lieu[3])
        dau = self.bang.horizontalHeader()
        dau.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.bang.resizeColumnsToContents()
        self.bang.setColumnWidth(1, min(max(int(self.bang.columnWidth(1)), 240), 340))   # họ tên dài: xem đủ khi rê chuột
        self.bang.setColumnWidth(2, min(max(int(self.bang.columnWidth(2)), 240), 420))   # địa chỉ
        self.bang.setColumnWidth(5, max(int(self.bang.columnWidth(5)), 220))              # trạng thái
        self.bang.setColumnWidth(6, min(max(int(self.bang.columnWidth(6)), 220), 480))    # ghi chú lệch Excel
        dau.setStretchLastSection(True)
        self._vua_tieu_de()
        self.bang.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def _tai_lai_ho(self, doi: set) -> bool:
        """Tính lại và vẽ lại các hộ trong doi (csdl.DauVetHo.lay), giữ nguyên các hộ khác, cách sắp xếp, độ rộng cột.
        False: không làm riêng được (nhiều hộ quá, hộ lạ...) - gọi nạp lại toàn bộ."""
        if len(doi) > self.TAI_LAI_HO_TOI_DA:
            return False
        vi_tri = {h['ma_ho']: i for i, h in enumerate(self.kq.ho)}
        if len(self.mo_hinh.dong) != len(self.kq.ho) or any(m not in vi_tri for m in doi):
            return False
        if not doi:
            return True
        from . import doi_chieu
        ds = sorted(doi, key=vi_tri.get)
        moi = doi_chieu.doi_chieu(self.con, ds_ma_ho=ds)
        if sorted(h['ma_ho'] for h in moi.ho) != sorted(ds):
            return False
        for h in moi.ho:
            self.kq.ho[vi_tri[h['ma_ho']]] = h
        theo_vi_tri = lambda x: vi_tri[x[0]]            # noqa: E731 - giữ thứ tự hộ như khi tính cả dự án (sắp xếp ổn định)
        self.kq.dong_lech = sorted([x for x in self.kq.dong_lech if x[0] not in doi] + moi.dong_lech, key=theo_vi_tri)
        self.kq.canh_bao = sorted([x for x in self.kq.canh_bao if x[0] not in doi] + moi.canh_bao, key=theo_vi_tri)
        so_lieu = self._so_lieu_dong(ds)
        for h in moi.ho:
            i = vi_tri[h['ma_ho']]
            self.mo_hinh.thay_dong(i, self._dong_ho(i + 1, h, so_lieu))
        return True

    def _sau_tai_lai(self, giu_trang: bool):
        """Phần chung sau khi nạp lại (toàn bộ hay từng hộ): trang tổng hợp / tiến độ, thẻ số liệu, tiêu đề dự án, đối chiếu."""
        hien = self.trang.currentIndex()
        for i, k in self.khung_trang.items():                    # trang đang xem vừa tự nạp (_da_ghi): không nạp lại, trừ Danh sách hộ
            if giu_trang and i == hien:
                if k is self.bang_tong_hop:                      # thẻ khác của bảng tổng hợp nạp khi chuyển sang
                    k._can_nap = {0, 1, 2} - {k.tab.currentIndex()}
                continue
            k.nap()
        self._cap_nhat_the_so()
        self._dem_loc()
        da = self.con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
        # băng tiêu đề: đơn vị lập phương án của DỰ ÁN đang mở (0.9.23 - trước: luôn một đơn vị cố định trong to_chuc.py)
        from .giao_dien import dat_to_chuc
        k = da.keys()
        dv = str(da['don_vi_lap'] or '').strip() if 'don_vi_lap' in k else ''
        cap = str(da['don_vi_cap_tren'] or '').strip() if 'don_vi_cap_tren' in k else ''
        dat_to_chuc(self.bang_tieu_de, dv.upper(), (f'Trực thuộc {cap}   •   ' if cap else '') +
                    f'{da["cap_dia_ban"] or ""} {da["ten_dia_ban"] or ""}'.strip() if dv else '')
        if hasattr(self, 'lb_don_vi'):
            from . import to_chuc
            self.lb_don_vi.setText((dv or to_chuc.TEN).upper())
        self._cap_nhat_chon()
        sua = f' (trừ {self.kq.so_ho_sua} hộ đã sửa trong phần mềm)' if self.kq.so_ho_sua else ''
        from .giao_dien import dat_trang_thai
        if self.kq.khop_het:
            dat_trang_thai(self.lb_ket_qua, 'dat',
                           f'✓ Đối chiếu file Excel: KHỚP 100%{sua}  ·  {len(self.kq.canh_bao)} điểm cần xem lại')
        else:
            # lệch so với file Excel lúc nhập = cần rà lại (thường do đã sửa / áp giá mới), không phải lỗi: màu cảnh báo,
            # kèm bước tiếp theo thay vì chỉ báo con số
            dat_trang_thai(self.lb_ket_qua, 'canh_bao',
                           f'⚠ Đối chiếu file Excel: LỆCH {self.kq.so_ho_lech} hộ, {len(self.kq.dong_lech)} dòng{sua}  ·  '
                           'xem từng dòng lệch: menu trái Lập phương án → Đối chiếu file Excel')
        self.dat_tieu_de()
        self._cap_nhat_hien_hang_the()

    # ------------------------------------------------ lọc danh sách
    def _nap_ds_dot(self, ten_dot: dict):
        cu = self.cb_dot.currentData()
        self.cb_dot.blockSignals(True)
        self.cb_dot.clear()
        self.cb_dot.addItem('Tất cả đợt', '')
        self.cb_dot.addItem('Chưa xếp đợt', 'chua')
        for i, t in ten_dot.items():
            self.cb_dot.addItem(t, i)
        k = self.cb_dot.findData(cu) if cu not in (None, '') else 0
        self.cb_dot.setCurrentIndex(max(k, 0))
        self.cb_dot.blockSignals(False)
        self.loc.dat(dot=self.cb_dot.currentData() or '')

    def _loc(self, **kw):
        self.loc.dat(**{k: ('' if v is None else v) for k, v in kw.items()})
        self._dem_loc()

    def _dem_loc(self):
        n = self.loc.rowCount()
        tong = sum((self.mo_hinh.dong[self.loc.mapToSource(self.loc.index(r, 0)).row()]['tong'] for r in range(n)), D(0))
        self.lb_loc.setText(f'{n}/{len(self.mo_hinh.dong)} hộ · {vn(tong)} đ' if self.mo_hinh.dong else '')

    def ho_dang_loc(self) -> list:
        """Mã hộ đang hiện trong danh sách (sau lọc), theo thứ tự đang sắp."""
        return [self.mo_hinh.dong[self.loc.mapToSource(self.loc.index(r, 0)).row()]['ma_ho'] for r in range(self.loc.rowCount())]

    def _khung_dang_xem(self):
        """Trang bên phải đang xem có bảng hộ riêng (thẻ Bảng tổng hợp, Quyết định, Tiến độ, Báo cáo tiến độ); None = danh sách hộ."""
        i = self.trang.currentIndex() if hasattr(self, 'trang') else 0
        if i == STACK_TONG_HOP:
            return self.bang_tong_hop.tab.currentWidget()
        return getattr(self, 'khung_trang', {}).get(i)

    def ho_da_chon(self) -> list:
        """Hộ đang chọn TRÊN TRANG ĐANG XEM (trước 0.9.18 luôn lấy ở danh sách hộ - đang ở trang Tiến độ chọn hộ rồi bấm
        "Trạng thái hộ…" ở menu trái thì phần mềm lấy hộ của danh sách đang ẩn)."""
        k = self._khung_dang_xem()
        if k is not None and hasattr(k, 'ma_da_chon'):
            return sorted(k.ma_da_chon())
        if self.bang.selectionModel() is None:
            return []
        return sorted({self.mo_hinh.dong[self.loc.mapToSource(i).row()]['ma_ho'] for i in self.bang.selectionModel().selectedRows()})

    def mo_ta_loc(self) -> str:
        t = [x for x in (self.cb_dot.currentText() if self.cb_dot.currentData() else '',
                         self.cb_tt.currentText() if self.cb_tt.currentData() else '',
                         f'tìm "{self.o_tim.text()}"' if self.o_tim.text().strip() else '') if x]
        return ', '.join(t)

    def mo_chi_tiet(self, idx):
        if self.con is None:
            return
        r = self.loc.mapToSource(idx).row()
        if self.chi_doc:
            ChiTietHo(self.con, self.mo_hinh.dong[r]['ma_ho'], self).exec()
            return
        self.mo_lap_pa(self.mo_hinh.dong[r]['ma_ho'])

    # ------------------------------------------------ màn hình chính: thẻ số liệu, thao tác nhanh, menu chuột phải
    # màu từng thẻ: giao_dien.MAU_THE_SO (kiểu nằm trong QSS chung, thẻ chỉ gắn thuộc tính vai / the)
    THE_SO = [('so_ho', 'Số hộ'), ('da_pa', 'Đã lập phương án'), ('tong', 'Tổng kinh phí'), ('da_pd', 'Đã phê duyệt'),
              ('da_ct', 'Đã chi trả'), ('da_bg', 'Đã bàn giao mặt bằng')]
    # bấm thẻ: lọc danh sách hộ theo trạng thái (quan_ly.TRANG_THAI); '' = bỏ lọc trạng thái
    LOC_THE = {'so_ho': '', 'da_pa': 'co_pa', 'tong': '', 'da_pd': 'da_pd', 'da_ct': 'da_ct', 'da_bg': 'da_bg'}

    def _hien_ty_le(self, t: float):
        self.nut_ty_le['ty_le'].setText(f'{round(t * 100)}%')
        self.nut_ty_le['ty_le'].setToolTip('Bấm để về 100%. Ctrl + con lăn chuột, Ctrl + "+" / "-" để phóng to / thu nhỏ')

    def _vua_tieu_de(self):
        """Cột không hẹp hơn chữ tiêu đề (tiêu đề in đậm, có mũi tên sắp xếp): không bị mất chữ như "DT thu hồi (m²)"."""
        from PySide6.QtGui import QFontMetrics
        f = QFont(self.bang.font())
        f.setBold(True)
        fm = QFontMetrics(f)
        for v in (self.bang,):
            for c, ten in enumerate(COT):
                can = fm.horizontalAdvance(ten) + 34
                if v.columnWidth(c) < can:
                    v.setColumnWidth(c, can)

    def _hang_the_so(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(4)                                  # 0.9.95: dải KPI một dòng 30-32 px (số + nhãn cùng hàng), thẻ cách 4 px
        h.setProperty('giu_khoang_cach', True)          # giao_dien.gian_cach không nâng lên 10 px
        self.the_so = {}
        for k, ten in self.THE_SO:
            khung = TheSo()
            khung.setObjectName('the_so')
            khung.setCursor(Qt.CursorShape.PointingHandCursor)
            khung.setToolTip('Bấm để xem tất cả hộ' if not self.LOC_THE[k] else f'Bấm để lọc danh sách hộ: {ten.lower()}')
            khung.bam.connect(lambda k=k: self.bam_the_so(k))
            khung.setProperty('vai', 'the_so')
            khung.setProperty('the', k)
            khung.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)    # QWidget thường: cần để QSS vẽ nền / viền
            o = QHBoxLayout(khung)
            o.setContentsMargins(8, 2, 8, 2)
            o.setSpacing(6)
            o.setProperty('giu_khoang_cach', True)
            khung.setMaximumHeight(32)
            so = QLabel('–')
            so.setProperty('vai', 'so_the')
            nhan = QLabel(ten)
            nhan.setProperty('vai', 'nhan_the')
            o.addWidget(so)
            o.addWidget(nhan, 1)
            self.the_so[k] = so
            h.addWidget(khung, 1)
        return h

    def _cap_nhat_the_so(self):
        ds = self.mo_hinh.dong
        tong = sum((d['tong'] for d in ds), D(0))
        # "đã lập" không tính phương án phần mềm tự lập lúc tạo Dự án mới mà chưa mở soát (in_an.phan_loai_lap)
        lap = {}
        if ds and self.con is not None:
            try:
                lap = lap_pa.phan_loai_lap(self.con)
            except Exception:                           # file chỉ xem phiên bản cũ...: đếm như trước
                lap = {}
        da_pa = sum(1 for v in lap.values() if v == 'da_lap') if lap else sum(1 for d in ds if d['tong'] > 0)
        tu_lap = sum(1 for v in lap.values() if v == 'tu_lap')
        if 'da_pa' in self.the_so:
            self.the_so['da_pa'].setToolTip(f'{tu_lap} hộ có phương án phần mềm tự lập, chưa mở soát và lưu' if tu_lap else '')
        gt = dict(so_ho=len(ds), da_pa=da_pa, tong=vn_gon(tong) if ds else '–',
                  da_pd=sum(1 for d in ds if d.get('da_phe_duyet')), da_ct=sum(1 for d in ds if d.get('da_chi_tra')),
                  da_bg=sum(1 for d in ds if d.get('da_ban_giao')))
        for k, o in self.the_so.items():
            v = gt[k]
            o.setText(str(v) if ds else '–')
            if k in ('da_pa', 'da_pd', 'da_ct', 'da_bg') and ds:
                o.setText(f'{v} / {len(ds)}')
        if 'tong' in self.the_so:
            self.the_so['tong'].setToolTip(f'{vn(tong)} đồng' if ds else '')

    def bam_the_so(self, k: str):
        """Thẻ số liệu: Số hộ / Tổng kinh phí = bỏ mọi bộ lọc; thẻ khác = lọc trạng thái tương ứng; về danh sách hộ."""
        if self.con is None:
            return
        if not self.LOC_THE.get(k):
            self.cb_dot.setCurrentIndex(0)
            self.o_tim.clear()
            self.o_tim.phat_ngay()                      # bỏ lọc ngay, không chờ ô tìm
        self.cb_tt.setCurrentIndex(max(0, self.cb_tt.findData(self.LOC_THE.get(k, ''))))
        self.mo_trang(0)

    # ------------------------------------------------ thanh công cụ danh sách hộ, màn hình chào
    def _thanh_cong_cu_ds(self):
        """Thanh công cụ theo ngữ cảnh của danh sách hộ (0.9.23 - lộ trình người dùng): Thêm hộ, Lập phương án, Xóa hộ (chỉ
        sáng khi đang chọn hộ) - trước nằm ở menu trái (điều hướng) như một màn hình; đặt cùng hàng với bộ lọc. Chọn nhiều hộ:
        hàng "Đã chọn N hộ" với thao tác hàng loạt. Nút dùng chính QAction của lệnh (tắt khi chỉ xem như mọi nơi khác)."""
        from .giao_dien import KieuNut, XepDong, ap_kieu_nut, nut_lenh
        # hai khối (nút | bộ lọc) trong XepDong: hẹp thì bộ lọc xuống dòng - một hàng cứng cần 1136 điểm + menu trái 248 = cửa
        # sổ tối thiểu 1414 điểm, rộng hơn màn hình 1366 (và làm hỏng phóng to lúc mở: xem hien_cua_so)
        h = XepDong(cach=12)
        nhom_nut = QWidget()
        hn = QHBoxLayout(nhom_nut)
        hn.setContentsMargins(0, 0, 0, 0)
        hn.setSpacing(6)
        self.nut_ds = {}
        # 0.9.66 (bỏ lệnh trùng): chỉ lệnh KHÔNG có ở menu trái / thanh menu - Thêm hộ, Xóa hộ. Lập phương án (menu trái), Xuất
        # danh sách hộ (menu Dữ liệu) không lặp ở đây
        # 0.9.69: Chọn hộ niêm yết (đánh dấu hộ đủ điều kiện niêm yết, lấy ý kiến sau khi lập phương án) - chỉ có ở đây
        for ten, kieu in (('Thêm hộ…', KieuNut.LUU), ('Chọn hộ niêm yết…', KieuNut.PHU), ('Xóa hộ…', KieuNut.NGUY_HIEM)):
            b = nut_lenh(self.lenh[ten], 16)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setMinimumHeight(28)                      # nút thao tác chuẩn công sở 28-30 px (15/10/2026; nut_lenh mặc định 32)
            b.setMaximumHeight(30)
            ap_kieu_nut(b, kieu)
            hn.addWidget(b)
            self.nut_ds[ten] = b
        self.lenh['Chọn hộ niêm yết…'].setToolTip(
            'Đánh dấu hộ đủ điều kiện niêm yết công khai, lấy ý kiến (đã lập phương án, đủ họ tên, nguồn gốc thửa, không tranh '
            'chấp, không vướng): các hộ đang chọn (từ 2 hộ), không thì cả dự án')
        self.lenh['Xuất danh sách hộ…'].setToolTip(
            'Xuất Excel danh sách hộ để theo dõi, trình, lưu trữ: các hộ đang chọn (từ 2 hộ), không thì các hộ đang hiện theo '
            'Đợt / Trạng thái / Tìm')
        hn.addStretch(1)
        nhom_loc = QWidget()
        hl = QHBoxLayout(nhom_loc)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        for ten, w in (('Đợt:', self.cb_dot), ('Trạng thái:', self.cb_tt), ('Tìm:', self.o_tim)):
            nhan_tim = QLabel(ten)
            nhan_tim.setProperty('vai', 'nhan')
            hl.addWidget(nhan_tim)
            hl.addWidget(w, 1 if w is self.o_tim else 0)
        h.addWidget(nhom_nut)
        h.addWidget(nhom_loc)
        # 0.9.66: bỏ hàng "Đã chọn N hộ" (In / Xuất, Đợt trình, Trạng thái hộ - menu trái; Xóa hộ - nút ngay trên). Số hộ đang
        # chọn hiện ở thanh trạng thái (lb_tom_tat), thao tác hàng loạt qua menu trái / chuột phải trên các hộ đã chọn
        return h

    def _cap_nhat_chon(self):
        """Xóa hộ chỉ sáng khi đang chọn hộ trên danh sách; số hộ đang chọn ở thanh trạng thái."""
        sm = self.bang.selectionModel()
        n = len(sm.selectedRows()) if sm is not None and self.con is not None else 0
        self.lenh['Xóa hộ…'].setEnabled(n > 0 and not self.chi_doc)
        self.lb_tom_tat.setText(f'Sẵn sàng · Tổng cộng: {len(self.mo_hinh.dong)} hộ | Đã chọn: {n} hộ' if self.con is not None
                                else 'Sẵn sàng · Chưa mở dự án')

    def _trang_chao(self) -> QWidget:
        """Màn hình chào khi chưa mở dự án (0.9.23 - thay dòng chữ vàng): 3 nút bắt đầu + dự án làm việc gần đây."""
        from .giao_dien import TOKEN, nut_lenh
        from .giao_dien import OTimKiemThongMinh
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(40, 20, 40, 16)
        lo.addStretch(1)
        tieu = QLabel('HỆ THỐNG QUẢN LÝ BỒI THƯỜNG & GPMB')
        tieu.setStyleSheet(f'QLabel {{ font-size: 20px; font-weight: 700; color: {TOKEN["chinh"]}; letter-spacing: 0.4px; }}')
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
        )
        from .giao_dien import CO_ICON_THE_CHAO, TheChao
        self.the_chao = {}
        for ten, loai, phu, goi_y in mo_ta_nut:
            the = TheChao(loai=loai)
            b = nut_lenh(self.lenh[ten], CO_ICON_THE_CHAO, duoi=True)
            b.setToolTip(goi_y)
            the.setToolTip(goi_y)
            the.dat_noi_dung(b, phu)               # biểu tượng 38px, tên lệnh, mô tả: tất cả trong thẻ
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
        self.o_tim_gan.setStyleSheet('QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 8px; background: #FFFFFF; }'
                                     'QLineEdit:focus { border-color: #2563EB; }')
        self.o_tim_gan.chuoi_da_doi.connect(self._loc_gan_day)
        hang_gd.addWidget(self.o_tim_gan)
        lo.addSpacing(8)
        lo.addLayout(hang_gd)
        self.ds_gan_day = QTableWidget(0, 6)
        self.ds_gan_day.setHorizontalHeaderLabels(
            ['Tên dự án & địa bàn', 'Số hộ', 'Tổng kinh phí', 'Cập nhật', 'Ghim', 'Thao tác'])
        self.ds_gan_day.horizontalHeader().setStretchLastSection(True)
        self.ds_gan_day.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ds_gan_day.verticalHeader().setVisible(False)
        self.ds_gan_day.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ds_gan_day.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ds_gan_day.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ds_gan_day.setMaximumHeight(220)
        self.ds_gan_day.cellDoubleClicked.connect(lambda r, _c: self._mo_gan_day_dong(r))
        self.ds_gan_day.itemSelectionChanged.connect(self._cap_nhat_nut_gan_day)
        # trạng thái trống (0.9.80): không hiện lưới trắng trơ trọi - biểu tượng thư mục + hướng dẫn bắt đầu, ở giữa vùng bảng
        self.ngan_gan_day = QStackedWidget()
        self.ngan_gan_day.setMaximumHeight(220)
        self.ngan_gan_day.addWidget(self.ds_gan_day)
        self.ngan_gan_day.addWidget(self._trang_trong_gan_day())
        lo.addWidget(self.ngan_gan_day)
        lo.addStretch(2)
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
                cham.setStyleSheet('QLabel { color: #94A3B8; font-size: 14px; font-weight: 700; background: transparent; }')
                chan.addWidget(cham)
            khung, lk = self._lien_ket_icon(ma, chu, ham)
            lk.setToolTip(goi_y)
            chan.addWidget(khung)
            self.lien_ket_chan[ten] = lk
        self.lk_huong_dan = self.lien_ket_chan['lich_su']      # tên cũ (test): liên kết "Lịch sử cập nhật phần mềm"
        chan.addStretch(1)
        lo.addLayout(chan)
        return w

    def _lien_ket_icon(self, ma: int, chu: str, ham):
        """Liên kết chân trang: biểu tượng nhỏ (phông Segoe MDL2; máy không có phông chỉ hiện chữ) + chữ bấm được."""
        from .giao_dien import icon_ky_hieu
        khung = QWidget()
        h = QHBoxLayout(khung)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(5)
        ic = icon_ky_hieu(ma, '#475569', 16)
        if ic is not None:
            lb_ic = QLabel()
            lb_ic.setPixmap(ic.pixmap(16, 16))
            lb_ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            h.addWidget(lb_ic)
        lk = self._lien_ket_chan(chu, ham)
        h.addWidget(lk)
        return khung, lk

    def _trang_trong_gan_day(self) -> QWidget:
        """Trạng thái trống của bảng dự án gần đây."""
        from .giao_dien import icon_ky_hieu
        w = QWidget()
        w.setObjectName('trong_gan_day')
        w.setStyleSheet('QWidget#trong_gan_day { background: transparent; border: 1px dashed #CBD5E1; border-radius: 8px; }')
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
        self.lb_trong.setStyleSheet('QLabel { color: #64748B; font-size: 13px; background: transparent; border: 0; }')
        v.addWidget(self.lb_trong)
        v.addStretch(1)
        return w

    def _hien_trong_gan_day(self):
        """Bảng trống: hiện trạng thái trống, ẩn cụm nút thao tác, tắt ô tìm; có dòng: ngược lại."""
        co = self.ds_gan_day.rowCount() > 0
        self.ngan_gan_day.setCurrentIndex(0 if co else 1)
        self.khung_nut_gan.setVisible(co)
        self.o_tim_gan.setEnabled(co)

    def quy_trinh_16_buoc(self, cho: bool = True):
        """Liên kết chân trang "Quy trình 16 bước QĐ 18": bảng 16 bước và chỗ làm từng bước trong phần mềm."""
        from .man_hinh_quy_trinh import HopQuyTrinh
        hop = HopQuyTrinh(self)
        if cho:
            hop.exec()
        return hop

    def _lien_ket_chan(self, chu, ham):
        from .giao_dien import NhanBam
        lk = NhanBam(chu)
        lk.setProperty('vai', 'lien_ket')
        lk.setCursor(Qt.CursorShape.PointingHandCursor)
        lk.bam = ham
        return lk

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
            self.ds_gan_day.setItem(r, 2, QTableWidgetItem('—' if tong is None else tong))
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
            b_ghim.setText('📌' if da_ghim else '📍')
            b_ghim.setToolTip('Bỏ ghim — xuống theo thứ tự gần đây' if da_ghim else 'Ghim dự án quan trọng lên đầu')
            b_ghim.setAutoRaise(True)
            b_ghim.clicked.connect(lambda _=False, p=str(f), g=not da_ghim: self._chay_lenh(
                lambda: (ghim_du_an(p, g), self._nap_gan_day())))
            self.ds_gan_day.setCellWidget(r, 4, b_ghim)
            mo = QPushButton('Mở')
            mo.setCursor(Qt.CursorShape.PointingHandCursor)
            mo.setStyleSheet('QPushButton { padding: 3px 12px; border: 1px solid #2563EB; border-radius: 4px; '
                             'color: #2563EB; background: #FFFFFF; } QPushButton:hover { background: #E8F0FE; }')
            mo.clicked.connect(lambda _=False, p=str(f): self._chay_lenh(lambda: self.mo(p)))
            hop_mo = QWidget()
            hm = QHBoxLayout(hop_mo)
            hm.setContentsMargins(4, 2, 4, 2)
            hm.addStretch(1)
            hm.addWidget(mo)
            hm.addStretch(1)
            self.ds_gan_day.setCellWidget(r, 5, hop_mo)
            n += 1
            if n == 8:
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

    def xoa_du_an(self, p=None, xoa_file: bool = True, xac_nhan=None, tu_danh_sach: bool = False):
        """Xóa dự án khỏi danh sách gần đây; xoa_file=True thì xóa cả file .pabt (đóng nếu đang mở). Không xóa thư mục bản in."""
        if p is None:
            p = self._file_gan_day_chon() if tu_danh_sach else (str(self.file) if self.file else self._file_gan_day_chon())
        if not p:
            QMessageBox.information(self, TEN_UD, 'Hãy chọn một dự án trong danh sách gần đây, hoặc mở dự án rồi bấm Xóa dự án.')
            return None
        p = Path(p)
        dang_mo = self.file is not None and p.resolve() == self.file.resolve()
        if xoa_file:
            chu = (f'XÓA HẲN file dự án?\n\n{p}\n\nKhông đưa vào Thùng rác. Thư mục bản in / hồ sơ đợt (nếu có) giữ nguyên. '
                   + ('Dự án đang mở sẽ được đóng trước.' if dang_mo else ''))
        else:
            chu = f'Bỏ "{p.name}" khỏi danh sách gần đây? File dự án vẫn còn trên đĩa.'
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, chu) == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        if dang_mo:
            self.dong_du_an_lenh()
        bo_gan_day(p)
        if xoa_file:
            khoa_p = p.with_name(p.name + '.khoa')
            try:
                if khoa_p.exists():
                    khoa_p.unlink()
                if p.exists():
                    p.unlink()
            except OSError as e:
                QMessageBox.warning(self, TEN_UD, chu_loi('Không xóa được file dự án', e))
                self._nap_gan_day()
                return None
        self._nap_gan_day()
        self.statusBar().showMessage(('Đã xóa file dự án: ' if xoa_file else 'Đã bỏ khỏi danh sách: ') + p.name, 8000)
        return str(p)

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
        self.trang.setCurrentIndex(TRANG_CHAO)
        if hasattr(self, 'ngan_lv'):
            self.ngan_lv.setCurrentWidget(self.trang)
        self.lb_trang.setVisible(False)
        self._nap_gan_day()
        self._danh_dau_trang_chu()
        self._dam_bao_tab(-1)
        self._cap_nhat_hien_hang_the()

    def _danh_dau_trang_chu(self):
        for t in TRANG:
            self.lenh[t].setChecked(False)
        self.lenh['Màn hình chính'].setChecked(True)

    def luu_du_an_lenh(self):
        """Tệp tin → Lưu dự án (Ctrl+S). Mọi thao tác đã ghi ngay vào file dự án (SQLite, từng giao dịch); lệnh này ép ghi hẳn xuống
        đĩa (đồng bộ Google Drive / ổ mạng) và báo giờ lưu - người dùng quen Ctrl+S không phải đoán đã lưu chưa.
        Đang xem trang Khái toán & dự toán (0.9.71): Ctrl+S lưu file khái toán .pabtdt (nút "LƯU DỰ TOÁN (Ctrl+S)").
        Không gắn phím tắt riêng trên trang: hai phím tắt cùng Ctrl+S thì Qt không chạy cái nào."""
        if self.khung_du_toan is not None and self.trang.currentIndex() == 3 and self.khung_du_toan.isVisible():
            return self.khung_du_toan.luu() is not None
        if self.con is None or self.file is None:
            self.statusBar().showMessage('Chưa mở dự án.', 4000)
            return False
        if self.chi_doc:
            self.statusBar().showMessage('Dự án đang mở chỉ xem: không ghi.', 4000)
            return False
        hop = self._hop_tab_dang_soan()
        if hop is not None and not hop.luu():
            return False
        import os
        from datetime import datetime
        try:
            if self.con.in_transaction:
                self.con.commit()
            with open(self.file, 'rb+') as f:
                os.fsync(f.fileno())
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file dự án xuống đĩa', e))
            return False
        self.statusBar().showMessage(f'Đã lưu {self.file.name} lúc {datetime.now():%H:%M:%S} '
                                     '(mọi thay đổi được ghi ngay sau mỗi thao tác).', 6000)
        return True

    def _phong_to(self, buoc: int):
        from .giao_dien import phong_to
        phong_to(buoc)

    def _thanh_menu(self):
        """Thanh menu chuẩn (0.9.23 - lộ trình người dùng): thao tác file / dữ liệu / công cụ / trợ giúp, phím tắt."""
        L = self.lenh
        self.menu_tren = {}
        from .thanh_tieu_de import dung_thanh_hop_nhat
        from PySide6.QtWidgets import QMenuBar
        # thanh hợp nhất: QMenuBar riêng nằm trong thanh tiêu đề (setMenuWidget) - menuBar() trả thanh này; dùng menuBar() của
        # QMainWindow thì setMenuWidget sẽ xóa nó (deleteLater)
        self._mb_rieng = QMenuBar(self) if dung_thanh_hop_nhat() else None
        for ten, ds in (('&Tệp tin', ['Dự án mới…', 'Mở dự án…', 'Dự án trên máy chủ…', None, 'Lưu dự án', 'Lưu dự án thành…',
                                      'Đóng dự án', 'Xóa dự án…', None, 'Thoát']),
                        ('Chỉnh &sửa', [self.nut_ht['lui'], self.nut_ht['toi']]),
                        # 0.9.66 (người dùng 12/10/2026 - mỗi lệnh một chỗ): lệnh đã có ở menu trái không lặp ở đây - Báo cáo
                        # tổng hợp, Xuất báo cáo đối chiếu, Bộ đơn giá, Thông tin dự án (KIEM_TRA test_khong_trung_menu_trai)
                        ('&Dữ liệu', ['Nhập file Excel…', 'Nhập phương án chi tiết…', 'Nhập bản vẽ CAD (.dxf)…', None, 'Trạng thái hộ…',
                                      'Xuất danh sách hộ…', None, 'Nhật ký kiểm toán…']),
                        ('&Công cụ', ['Cập nhật mẫu in…', 'Rà soát giá…', 'Cập nhật bảng giá đất…', None,
                                      'Phiếu kiểm đếm thực địa…', None,
                                      'Xuất gói mẫu in & cấu hình…', 'Nhập gói mẫu in & cấu hình…']),
                        ('C&ài đặt', ['Cấu hình nghiệp vụ…', None, 'Kết nối máy chủ LAN…', None, 'Phóng to chữ', 'Thu nhỏ chữ',
                                      'Cỡ chữ 100%']),
                        ('Trợ &giúp', ['Hướng dẫn sử dụng', 'Cập nhật phần mềm…', None, 'Chẩn đoán & sửa lỗi hệ thống…',
                                       None, 'Giới thiệu'])):
            # QMenu có cha + giữ tham chiếu: PySide2 (bản Win7) xóa menu do menuBar().addMenu("chữ") trả về khi biến Python
            # hết phạm vi (thanh menu còn tiêu đề nhưng mất danh sách lệnh)
            m = QMenu(ten, self)
            self.menuBar().addMenu(m)
            self.menu_tren[ten.replace('&', '')] = m
            m.setToolTipsVisible(True)
            for t in ds:
                if t is None:
                    m.addSeparator()
                else:
                    m.addAction(t if isinstance(t, QAction) else L[t])
        from .giao_dien import kieu_menu_bar, tao_banner_ten, tao_dai_nhan_dien, _BamMenu
        if self._mb_rieng is not None:
            # thanh tiêu đề hợp nhất kiểu VS Code (12/10/2026): biểu tượng + menu + Hoàn tác / Làm lại | tiêu đề | nút cửa sổ
            from .thanh_tieu_de import ThanhTieuDe
            self.thanh_td = ThanhTieuDe(self, self._mb_rieng)
            self._mb_rieng._bam_menu = _BamMenu(self._mb_rieng)
            self.setMenuWidget(self.thanh_td)
            self.dai_nhan_dien = self.thanh_td.logo
            self.thanh_td.gan_khung()                   # trước khi hiện cửa sổ; lỗi -> khung Windows như 0.9.64
        else:
            self.thanh_td = None
            kieu_menu_bar(self.menuBar())
            self.dai_nhan_dien = tao_dai_nhan_dien()
            self.menuBar().setCornerWidget(self.dai_nhan_dien, Qt.Corner.TopLeftCorner)
        self.banner_ten = tao_banner_ten()
        self.lb_don_vi = self.banner_ten.lb_don_vi
        self.lb_ban_quyen_nho = self.banner_ten.lb_ban_quyen

    def menuBar(self):
        """Thanh menu: QMenuBar nằm trong thanh tiêu đề hợp nhất, hoặc thanh menu của QMainWindow (khung Windows / bản Qt 5)."""
        mb = getattr(self, '_mb_rieng', None)
        return mb if mb is not None else super().menuBar()

    def _xoa_ket_qua(self):
        """Băng kết quả trống (chưa mở / đã đóng dự án): bỏ cả nền màu, không để lại ô màu rỗng cạnh nút."""
        self.lb_ket_qua.setText('')
        self.lb_ket_qua.setStyleSheet('QLabel { font-weight: bold; padding: 5px 8px; }')

    def _chay_lenh(self, ham):
        """Chạy một lệnh (menu trái, thanh nút, chuột phải) rồi giải phóng các hộp thoại đã đóng."""
        try:
            ham()
        finally:
            self.don_hop_da_dong()

    def don_hop_da_dong(self) -> int:
        """Hộp thoại tạo với cha là cửa sổ chính / trang bên phải không tự xóa khi đóng: mở cửa sổ lập phương án 20 lần để lại
        20 cửa sổ ẩn (~5.800 thành phần, giữ kết nối dự án cũ) - dùng cả ngày phần mềm nặng dần. Gọi khi lệnh đã chạy xong
        (không còn mã nào dùng các hộp đó); còn hộp đang mở (lệnh gọi từ bên trong hộp khác) thì để lần sau."""
        if QApplication.activeModalWidget() is not None:
            return 0
        an = [h for h in self.findChildren(QDialog) if not h.isVisible() and not h.property('nhung_tab')]
        for h in an:
            h.deleteLater()
        return len(an)

    def _menu_ho(self, view, pos):
        idx = view.indexAt(pos)
        if self.con is None or not idx.isValid():
            return
        if view.currentIndex().row() != idx.row():     # chuột phải lên dòng khác dòng đang chọn: thao tác trên dòng đó
            view.setCurrentIndex(idx)
        m = QMenu(self)
        # lệnh của menu trái dùng lại đúng QAction (cùng tên, cùng trạng thái bật / tắt khi chỉ xem); chỉ "Xem chi tiết tính
        # tiền…" là riêng của chuột phải
        m.addAction(self.lenh['Lập phương án hộ…'])
        m.addAction('Xem chi tiết tính tiền…', lambda: self._chay_lenh(self.xem_chi_tiet_tinh))
        m.addSeparator()
        for ten in ('Trạng thái hộ…', 'Chọn hộ niêm yết…', 'Đợt trình…', 'In / Xuất…', 'Nhật ký kiểm toán…', None, 'Xóa hộ…'):
            if ten is None:
                m.addSeparator()
            else:
                m.addAction(self.lenh[ten])
        m.exec(view.viewport().mapToGlobal(pos))
        m.deleteLater()

    def nhap_ban_ve_cad(self, file=None, cho: bool = True):
        """Nhập ranh thửa từ bản vẽ địa chính .dxf vào bản đồ dự án (tùy chọn cập nhật DT thu hồi). True nếu đã lưu."""
        if self.con is None or self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Mở dự án (không ở chế độ chỉ xem) trước khi nhập bản vẽ.')
            return False
        from .man_hinh_ban_do import HopNhapCad
        d = HopNhapCad(self.con, self, file)
        if not cho:
            return d
        ok = d.exec() == QDialog.DialogCode.Accepted
        if ok:
            self.tai_lai()
        return ok

    def ban_do_thua(self, cho: bool = True):
        """Bản đồ thửa đất (cửa sổ riêng, không chặn): màu theo đồng thuận, bấm thửa mở hồ sơ / phương án của hộ."""
        if self.con is None:
            return None
        from .man_hinh_ban_do import HopBanDo
        d = HopBanDo(self.con, self, mo_ho=lambda ma: self.mo_lap_pa(ma),
                     nhap=None if self.chi_doc else (lambda: self.nhap_ban_ve_cad()))
        d.setWindowModality(Qt.WindowModality.NonModal)
        if cho:
            d.show()
        return d

    def cau_hinh_nghiep_vu(self, cho: bool = True):
        """Cấu hình nghiệp vụ (hồ sơ địa phương): mốc thời hạn 16 bước, kinh phí, ngưỡng kiểm tra, bản in, cơ quan (0.9.87)."""
        from .man_hinh_cau_hinh import HopCauHinhNghiepVu
        d = HopCauHinhNghiepVu(self)
        if cho and d.exec() == QDialog.DialogCode.Accepted and self.con is not None:
            self.tai_lai()                              # băng tiêu đề, kinh phí, mốc thời hạn theo cấu hình mới
        return d

    def chan_doan_he_thong(self, cho: bool = True):
        """Chẩn đoán máy, kiểm tra / sửa file dự án (đóng rồi mở lại dự án đang mở), xuất gói chẩn đoán ẩn danh (0.9.87)."""
        from .man_hinh_chan_doan import HopChanDoanHeThong

        def dong():
            if self.dong_du_an() is False:
                return False
            self.file = None
            self.dat_tieu_de()
            return True
        d = HopChanDoanHeThong(self, self.file, dong_du_an=dong, mo_lai=lambda f: self.mo(Path(f)), im_lang=not cho)
        if cho:
            d.exec()
        return d

    def phieu_kiem_dem(self, cho: bool = True):
        """Phiếu kiểm đếm thực địa: xuất trang HTML dùng trên điện thoại (không cần mạng), nhập kết quả .json vào phương án hộ,
        gắn ảnh hiện trạng theo mã hộ / CCCD / họ tên (0.9.87)."""
        if not self._can_du_an():
            return None
        from .man_hinh_kiem_dem import HopKiemDem
        d = HopKiemDem(self, self.con, self.file, self.dm, chi_doc=self.chi_doc, im_lang=not cho)
        if cho:
            d.exec()
            if d.da_ghi:
                self.tai_lai()
        return d

    def nhat_ky_kiem_toan(self, ma_ho=None, cho: bool = True):
        """Nhật ký kiểm toán của dự án (lọc sẵn hộ đang chọn nếu có). Xem được cả khi dự án mở chỉ xem."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Mở dự án trước để xem nhật ký kiểm toán.')
            return None
        from .man_hinh_kiem_toan import HopKiemToan
        da = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        d = HopKiemToan(self.con, self, self.ho_dang_chon() if ma_ho is None else ma_ho, da['ten'] if da else '',
                        self.file.parent if self.file else None)
        if cho:
            d.exec()
        return d

    def xem_chi_tiet_tinh(self, ma_ho=None, cho: bool = True):
        ma_ho = self.ho_dang_chon() if ma_ho is None else ma_ho
        if self.con is None or ma_ho is None:
            return None
        d = ChiTietHo(self.con, ma_ho, self)
        if cho:
            d.exec()
        return d

    # ------------------------------------------------ hoàn tác / làm lại
    def hoan_tac(self, lam_lai: bool = False) -> str:
        """Hoàn tác (lam_lai=False) / làm lại thao tác gần nhất đã ghi vào file dự án. Trả tên thao tác ('' nếu không có)."""
        if self.ht is None:
            return ''
        try:
            viec = self.ht.lam_lai() if lam_lai else self.ht.hoan_tac()
        except Exception as e:                          # file bị khóa / lỗi SQLite: không làm hỏng dữ liệu (đã rollback)
            QMessageBox.warning(self, TEN_UD, chu_loi(f'Không {"làm lại" if lam_lai else "hoàn tác"} được', e))
            return ''
        if not viec:
            self.statusBar().showMessage('Không còn thao tác để ' + ('làm lại.' if lam_lai else 'hoàn tác.'), 4000)
            return ''
        self.dm = lap_pa.DanhMuc(self.con) if 'đơn giá' in viec.lower() or 'danh mục' in viec.lower() else self.dm
        self.tai_lai()
        self.statusBar().showMessage(f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"}: {viec}', 8000)
        return viec

    def hoan_tac_phim(self, lam_lai: bool) -> bool:
        if self.ht is None:
            return False
        self.hoan_tac(lam_lai)
        return True

    def _cap_nhat_nut_ht(self):
        ht = self.ht
        for k, co, ten, phim in (('lui', ht is not None and ht.co_hoan_tac, ht.ten_hoan_tac() if ht else '', 'Ctrl+Z'),
                                 ('toi', ht is not None and ht.co_lam_lai, ht.ten_lam_lai() if ht else '', 'Ctrl+Y')):
            a = self.nut_ht[k]
            viec = 'Làm lại' if k == 'toi' else 'Hoàn tác'
            gon = ten if len(ten) <= 40 else ten[:39] + '…'
            a.setEnabled(bool(co))
            a.setText(f'{viec}: {gon}\t{phim}'.replace('&', '&&') if co else f'{viec}\t{phim}')    # như "Undo Typing" của Office
            a.setToolTip(f'{viec}: {ten}  ({phim})' if co else 'Chưa có thao tác để ' + viec.lower())

    def mo_trang(self, i: int):
        """Trang bên phải (chỉ số TRANG): 0 danh sách hộ, 1 bảng tổng hợp kinh phí (3 thẻ), 2 quyết định phê duyệt, 3 theo dõi chi
        trả & bàn giao, 4 báo cáo tiến độ GPMB, 5 dự toán & khái toán. Chưa mở dự án: trang 0-4 hiện màn hình chào (trang Dự toán dùng
        được cả khi chưa mở dự án)."""
        if i == TRANG_DU_TOAN:
            self._dam_bao_du_toan()
            self.khung_du_toan.tab.setCurrentIndex(0)   # menu trái "Lập khái toán & Dự toán" (So sánh: so_sanh_du_toan chọn thẻ 1)
            self.trang.setCurrentIndex(STACK_DU_TOAN)
        elif self.con is None:
            self.trang.setCurrentIndex(TRANG_CHAO)
        else:
            self.trang.setCurrentIndex(STACK_CUA_TRANG[i])
            k = self.khung_trang.get(STACK_CUA_TRANG[i])
            if k is self.bang_tong_hop:
                k.mo_the(k.tab.currentIndex())          # nạp thẻ đang xem (giữ thẻ người dùng chọn lần trước)
            elif k is not None and hasattr(k, '_can_nap') and k._can_nap:
                k.nap()
        self._dam_bao_tab(-1 if self.trang.currentIndex() == TRANG_CHAO else i)
        self._danh_dau_trang(i)
        self._cap_nhat_hien_hang_the()

    def _danh_dau_trang(self, i: int):
        """Tiêu đề trang bên phải và dấu chọn ở menu trái theo trang i (gọi cả khi bấm thẳng thẻ của Bảng tổng hợp)."""
        self._i_trang = i
        self.lb_trang.setText(NHAN_MENU.get(TRANG[i], TRANG[i]).upper())
        # không hiện tiêu đề trang ở trang nào: trùng mục menu trái đang chọn và tiêu đề khung của trang (người dùng 15-16/10/2026:
        # Dự toán, Quyết định phê duyệt "bị trùng tiêu đề mục"). lb_trang vẫn giữ chữ (test, tên trang hiện tại)
        self.lb_trang.setVisible(False)
        for k, t in enumerate(TRANG):
            self.lenh[t].setChecked(k == i)
        self.lenh['Màn hình chính'].setChecked(False)

    def _ten_tab(self, khoa) -> str:
        if isinstance(khoa, int):
            # QTabBar cũng coi "&" là phím tắt: "&&" để hiện "&" (trước: "Dự toán  khái toán" - mất "&", thừa dấu cách)
            return 'Màn hình chính' if khoa < 0 else NHAN_MENU.get(TRANG[khoa], TRANG[khoa]).replace('&', '&&')
        if khoa in TEN_TAB:
            return TEN_TAB[khoa]
        if isinstance(khoa, tuple) and khoa and khoa[0] == 'ho':
            return f'Hộ: {khoa[1]}'
        return str(khoa)

    def _dam_bao_tab(self, khoa, ten: str | None = None, widget=None, dong_duoc: bool | None = None):
        """Mở hoặc chuyển tab (khoa số = trang chính; ('ho', ma) / 'don_gia' = widget phụ giữ RAM)."""
        if not hasattr(self, 'khung_tab'):
            return
        self.khung_tab.dam_bao(khoa, ten or self._ten_tab(khoa), widget, dong_duoc)
        if widget is not None or not isinstance(khoa, int):
            self.ngan_lv.setCurrentWidget(self.khung_tab.stack_phu)
            self.lb_trang.setVisible(False)
        elif isinstance(khoa, int):
            self.ngan_lv.setCurrentWidget(self.trang)
        self._cap_nhat_hien_hang_the()

    def _cap_nhat_hien_hang_the(self):
        """0.9.95 (đặc tả "Ultra-Compact"): hàng thẻ số liệu CHỈ ở trang Danh sách hộ khi đã mở dự án - ẩn ở mọi trang khác (hộ đang
        soạn, Niêm yết, Đơn giá, Dự toán, Bảng tổng hợp, Quyết định, Tiến độ, Báo cáo). Banner xanh (tên phần mềm, đơn vị, phiên bản)
        CHỈ ở màn hình chào - màn hình làm việc nhường chiều cao cho bảng (tên dự án đã ở tiêu đề giữa thanh menu). Nối với tín hiệu
        đổi trang của `trang` / `ngan_lv` nên đúng dù trang đổi theo đường nào."""
        if not hasattr(self, 'ngan_lv') or not hasattr(self, 'hang_the'):
            return
        o_trang = self.ngan_lv.currentWidget() is self.trang
        chao = o_trang and self.trang.currentIndex() == TRANG_CHAO
        self.hang_the.setVisible(self.con is not None and o_trang and self.trang.currentIndex() == STACK_CUA_TRANG[TRANG_DS])
        if hasattr(self, 'banner_ten'):
            self.banner_ten.setVisible(self.con is None or chao)

    def _tab_doi(self, i: int):
        if i < 0 or i >= len(self._tab_khoa):
            return
        self._tab_doi_khoa(self._tab_khoa[i])

    def _tab_doi_khoa(self, k):
        if isinstance(k, int):
            self.ngan_lv.setCurrentWidget(self.trang)
            if k < 0:
                self.trang.setCurrentIndex(TRANG_CHAO)
                self.lb_trang.setVisible(False)
                self._danh_dau_trang_chu()
                return
            self.mo_trang(k)
            return
        self.ngan_lv.setCurrentWidget(self.khung_tab.stack_phu)
        w = self.khung_tab.widget.get(k)
        if w is not None:
            self.khung_tab.stack_phu.setCurrentWidget(w)
        self.lb_trang.setVisible(False)
        self._cap_nhat_hien_hang_the()

    def _tab_dong(self, i: int):
        if i < 0 or i >= len(self._tab_khoa):
            return
        k = self._tab_khoa[i]
        if isinstance(k, int) and k < 0:
            return
        w = self.khung_tab.widget.get(k)
        if w is not None and hasattr(w, 'hoi_luu') and not w.hoi_luu():
            return
        da_ap = bool(getattr(w, 'da_ap', False))
        da_ghi = bool(getattr(w, 'da_luu', False) or getattr(w, 'thay_doi_csdl', False))
        self.khung_tab.bo(i)
        if da_ap and self.con is not None:
            self.dm = lap_pa.DanhMuc(self.con)
            self.tai_lai()
        elif da_ghi and self.con is not None:
            self.tai_lai()
        if self.thanh_tab.count() == 0:
            self._dam_bao_tab(-1)
        elif self.thanh_tab.currentIndex() >= 0:
            self._tab_doi(self.thanh_tab.currentIndex())

    def _tab_ke(self, buoc: int):
        if hasattr(self, 'khung_tab'):
            self.khung_tab.ke(buoc)

    def _nhung_hop(self, hop):
        """Đưa hộp thoại thành trang tab: giữ nguyên widget / dữ liệu đang nhập, không exec().
        Tắt phím Ctrl+S riêng của hộp (trùng QAction cửa sổ chính -> Qt hỏi phím nào). Ctrl+S đi qua luu_du_an_lenh."""
        hop.setWindowFlags(Qt.WindowType.Widget)
        hop.setProperty('nhung_tab', True)
        from PySide6.QtGui import QKeySequence
        for sc in getattr(hop, '_phim', []):
            if sc.key() == QKeySequence(QKeySequence.StandardKey.Save):
                sc.setEnabled(False)

    def _hop_tab_dang_soan(self):
        """Tab hộ đang mở (có hàm luu). Ctrl+S ghi phương án hộ trước khi ép file xuống đĩa."""
        if not hasattr(self, 'khung_tab'):
            return None
        i = self.thanh_tab.currentIndex()
        if i < 0 or i >= len(self.khung_tab.khoa):
            return None
        w = self.khung_tab.widget.get(self.khung_tab.khoa[i])
        if w is not None and w.property('nhung_tab') and hasattr(w, 'luu') and hasattr(w, 'bo'):
            return w
        return None

    def _dong_tab_phu(self, hoi: bool = True) -> bool:
        """Đóng tab hộ / bộ đơn giá. False nếu người dùng hủy lưu."""
        if not hasattr(self, 'khung_tab'):
            return True
        phu = [k for k in list(self.khung_tab.khoa) if not isinstance(k, int)]
        if hoi:
            for khoa in phu:
                w = self.khung_tab.widget.get(khoa)
                if w is not None and hasattr(w, 'hoi_luu') and not w.hoi_luu():
                    return False
        for khoa in list(phu):
            if khoa in self.khung_tab.khoa:
                self.khung_tab.bo(self.khung_tab.khoa.index(khoa))
        if hasattr(self, 'ngan_lv'):
            self.ngan_lv.setCurrentWidget(self.trang)
        return True

    def _dam_bao_du_toan(self):
        if self.khung_du_toan is None:
            from .man_hinh_du_toan import KhungDuToan
            self.khung_du_toan = KhungDuToan(self.trang_dt, self.con, self.file if self.con is not None else None)
            self.trang_dt.layout().addWidget(self.khung_du_toan)

    def ho_dang_chon(self):
        k = self._khung_dang_xem()
        if k is not None and hasattr(k, 'ma_da_chon'):              # trang Tổng quát / Quyết định / Tiến độ: hộ chọn ở đó
            ds = k.ma_da_chon()
            return ds[0] if ds else None
        idx = self.bang.currentIndex()
        if not idx.isValid():
            return None
        return self.mo_hinh.dong[self.loc.mapToSource(idx).row()]['ma_ho']

    def mo_lap_pa(self, ma_ho=None, cho: bool = True, the: int | None = None, truoc: int | None = None):
        """Mở cửa sổ hồ sơ và phương án hộ (cho=False: chỉ tạo cửa sổ, dùng khi kiểm thử; the: thẻ mở đầu, 0 = thông tin hộ)."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        if ma_ho is None:
            ma_ho = self.ho_dang_chon()
        if self.chi_doc:                                # chỉ xem (máy khác đang sửa): xem chi tiết, không mở cửa sổ sửa
            return self.xem_chi_tiet_tinh(ma_ho, cho) if ma_ho is not None else None
        if ma_ho is None:
            r = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho LIMIT 1').fetchone()
            if r is None:
                QMessageBox.information(self, TEN_UD, 'Dự án chưa có hộ nào.')
                return None
            ma_ho = r[0]
        from .man_hinh import CuaSoLapPA
        khoa = ('ho', int(ma_ho))
        if cho and hasattr(self, 'khung_tab'):
            # không còn thanh tab (15/10/2026): hộ khác đang mở mà không có thay đổi chưa lưu thì đóng, khỏi chất cửa sổ ẩn trong
            # RAM; hộ còn thay đổi chưa lưu giữ lại (mở lại hộ đó là thấy; đóng dự án / thoát vẫn hỏi lưu)
            for k in [k for k in self.khung_tab.khoa if isinstance(k, tuple) and k[0] == 'ho' and k != khoa]:
                ww = self.khung_tab.widget.get(k)
                if ww is not None and not (ww.bo.co_thay_doi or ww.ho_so.co_thay_doi()):
                    self.khung_tab.bo(self.khung_tab.khoa.index(k))
        if cho and hasattr(self, 'khung_tab') and khoa in self.khung_tab.khoa:
            w = self.khung_tab.widget.get(khoa)
            if the is not None and w is not None:
                w.tab.setCurrentIndex(the)
            self._dam_bao_tab(khoa)
            return w
        w = CuaSoLapPA(self.con, ma_ho, self, self.dm)
        if the is not None:
            w.tab.setCurrentIndex(the)
        if not cho:
            return w
        self._nhung_hop(w)
        ten_ho = (getattr(getattr(w.bo, 'pa', None), 'ho', None) and w.bo.pa.ho.ho_ten) or f'Hộ {ma_ho}'
        self._dam_bao_tab(khoa, f'Hộ: {ten_ho}', widget=w, dong_duoc=True)
        cu_chuyen = w.chuyen_ho

        def _chuyen(ma):
            kq = cu_chuyen(ma)
            if kq and hasattr(self, 'khung_tab'):
                ten = (getattr(getattr(w.bo, 'pa', None), 'ho', None) and w.bo.pa.ho.ho_ten) or f'Hộ {ma}'
                moi = ('ho', int(w.bo.ma_ho))
                cu = next((k for k, ww in self.khung_tab.widget.items() if ww is w), None)
                if moi in self.khung_tab.khoa and self.khung_tab.widget.get(moi) is not w:
                    self.khung_tab.chon(moi)
                elif cu is not None:
                    self.khung_tab.doi_khoa(cu, moi, f'Hộ: {ten}')
            return kq
        w.chuyen_ho = _chuyen
        w.finished.connect(lambda *_: self._khi_hop_nhung_xong(w))
        return w

    def _khi_hop_nhung_xong(self, w):
        """Đóng tab khi hộp nhúng tự đóng (nút Đóng / accept) — không hỏi lưu lần hai nếu đã sạch."""
        if not hasattr(self, 'khung_tab'):
            return
        for i, k in enumerate(list(self.khung_tab.khoa)):
            if self.khung_tab.widget.get(k) is w:
                self._tab_dong(i)
                return

    XOA_HIEN_TOI_DA = 12           # hộp hỏi xóa: liệt kê tối đa bấy nhiêu hộ (danh sách dài không đẩy nút ra ngoài màn hình)

    def xoa_ho(self, ds_ma_ho=None, xac_nhan=None):
        """Xóa các hộ đang chọn trong danh sách (giữ Ctrl / Shift để chọn nhiều hộ; phím Delete) cùng thửa, phương án, quyết
        định / chi trả của hộ. Hoàn tác được (nút Hoàn tác / Ctrl+Z). xac_nhan: bỏ qua câu hỏi (kiểm thử)."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        if self.chi_doc:
            return None
        from . import ho_so
        ds = ho_so.thong_tin_xoa(self.con, self.ho_da_chon() if ds_ma_ho is None else ds_ma_ho)
        if not ds:
            if xac_nhan is None:
                QMessageBox.information(self, TEN_UD, 'Chọn hộ cần xóa trong danh sách (giữ Ctrl hoặc Shift để chọn nhiều hộ) rồi '
                                                      'bấm "Xóa hộ…" hoặc phím Delete.')
            return None
        if xac_nhan is None:
            n = self.XOA_HIEN_TOI_DA
            dong = [f'  {x["thu_tu"]}. {x["ho_ten"]} - {x["so_thua"]} thửa, {x["so_dong_pa"]} dòng phương án'
                    + (f', {x["so_qd"]} quyết định' if x['so_qd'] else '') + (', ĐÃ NHẬN TIỀN' if x['da_nhan_tien'] else '')
                    for x in ds[:n]]
            if len(ds) > n:
                dong.append(f'  … và {len(ds) - n} hộ khác')
            qd = sum(1 for x in ds if x['so_qd'])
            chu = (f'XÓA {len(ds)} hộ khỏi dự án?\n\n' + '\n'.join(dong) +
                   '\n\nXóa cả thửa đất, phương án' + (', quyết định phê duyệt / chi trả của hộ' if qd else '') + ' của các hộ này.'
                   + (f'\nCHÚ Ý: {qd} hộ đã có quyết định phê duyệt.' if qd else '') +
                   '\n\nXóa nhầm: bấm "Hoàn tác" trên băng tiêu đề (Ctrl+Z) để lấy lại.')
            hop = QMessageBox(QMessageBox.Icon.Warning, TEN_UD, chu,
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            hop.button(QMessageBox.StandardButton.Yes).setText(f'Xóa {len(ds)} hộ')
            hop.button(QMessageBox.StandardButton.No).setText('Không xóa')
            hop.setDefaultButton(QMessageBox.StandardButton.No)
            xac_nhan = hop.exec() == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        try:
            tb = ho_so.xoa_nhieu_ho(self.con, [x['ma_ho'] for x in ds])
        except (lap_pa.LoiNhap, sqlite3.Error) as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không xóa được', e))
            return None
        self.tai_lai()
        self.statusBar().showMessage(tb + '  Xóa nhầm: bấm Hoàn tác (Ctrl+Z).', 20000)
        return tb

    def mo_ho_so(self, ma_ho=None, moi: bool = False, cho: bool = True, ho_ten: str | None = None):
        """Hồ sơ hộ nằm chung cửa sổ với phương án (thẻ "Thông tin hộ, thửa đất"). moi: thêm hộ mới (hỏi họ tên) rồi mở."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        if moi and self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Dự án đang mở ở chế độ CHỈ XEM (máy khác đang sửa file): không thêm hộ được.\n\n'
                                                  'Đóng dự án ở máy kia rồi mở lại để sửa.')
            return None
        if moi:
            if ho_ten is None:
                from PySide6.QtWidgets import QInputDialog
                ho_ten, ok = QInputDialog.getText(self, 'Thêm hộ', 'Họ và tên chủ hộ (CCCD, địa chỉ, thửa đất nhập tiếp ở cửa sổ hồ sơ):')
                if not ok or not ho_ten.strip():
                    return None
            from . import ho_so
            truoc = self.con.total_changes                  # tải lại MỘT lần khi đóng cửa sổ hộ (tính cả hộ vừa thêm)
            try:
                ma_ho = ho_so.luu_ho(self.con, None, dict(ho_ten=ho_ten), [])
            except lap_pa.LoiNhap as e:
                QMessageBox.warning(self, TEN_UD, str(e))
                return None
            if not cho:
                self.tai_lai()
            return self.mo_lap_pa(ma_ho, cho=cho, the=0, truoc=truoc)
        elif ma_ho is None:
            ma_ho = self.ho_dang_chon()
            if ma_ho is None:
                QMessageBox.information(self, TEN_UD, 'Chọn một hộ trong danh sách (hoặc bấm "Thêm hộ…").')
                return None
        return self.mo_lap_pa(ma_ho, cho=cho, the=0)

    def sua_du_an(self, cho: bool = True):
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopDuAn
        dlg = HopDuAn(self.con, self)
        if cho and dlg.exec():
            self.tai_lai()
        return dlg

    def in_xuat(self, cho: bool = True, ma_ho: list | None = None, che_do: str | None = None, dot_id: int | None = None):
        """Trung tâm Xuất bản (Xuất hồ sơ & Bản in) - nơi DUY NHẤT in / xuất file. ma_ho: hộ truyền sẵn (mặc định hộ đang chọn trên danh
        sách); che_do: 'du_thao' (niêm yết, họp dân) / 'chinh_thuc' (trình thẩm định, gửi hộ) - None: như trước, không đặt sẵn; dot_id:
        đợt trình chọn sẵn."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopIn
        chon = sorted(ma_ho) if ma_ho is not None else (
            sorted({self.mo_hinh.dong[self.loc.mapToSource(i).row()]['ma_ho']
                    for i in self.bang.selectionModel().selectedRows()}) if self.bang.selectionModel() else [])
        dlg = HopIn(self.con, self, ma_ho_chon=chon, file_du_an=self.file, che_do=che_do, dot_id=dot_id)
        if cho:
            dlg.exec()
        return dlg

    def cap_nhat_mau_in(self, file_excel=None, ten_mau: str | None = None, loai: str | None = None, cho: bool = True):
        """Thêm / thay mẫu in từ file Excel: file PABT Excel (sheet IN_CHITIET và / hoặc IN_BANGTONGHOP) hoặc file mẫu đã sửa
        sẵn (một sheet, có chỗ trống {…}). ten_mau '' = thay mẫu chính, có tên = thêm mẫu riêng (chọn ở In / Xuất), None = hỏi."""
        from . import in_an
        if file_excel is None:
            file_excel, _ = QFileDialog.getOpenFileName(
                self, 'Chọn mẫu in (Excel hoặc PDF) để thay IN_CHITIET / IN_BANGTONGHOP', '',
                'Mẫu in (*.xlsx *.xlsm *.xls *.pdf)')
            if not file_excel:
                return None
        if ten_mau is None:
            hop = QMessageBox(QMessageBox.Icon.Question, TEN_UD,
                              f'Mẫu này chỉ lưu trên máy này (%APPDATA%\\PABT\\mau_in), không đè mẫu của máy khác.\n'
                              f'File: {Path(file_excel).name}\n\n'
                              'Chọn mẫu chi tiết hoặc mẫu tổng hợp. Máy này có thể dùng hai mẫu khác nhau.',
                              parent=self)
            b_ct = hop.addButton('Mẫu chi tiết', QMessageBox.ButtonRole.AcceptRole)
            b_th = hop.addButton('Mẫu tổng hợp', QMessageBox.ButtonRole.AcceptRole)
            b_rieng = hop.addButton('Thêm mẫu riêng…', QMessageBox.ButtonRole.AcceptRole)
            hop.addButton('Hủy', QMessageBox.ButtonRole.RejectRole)
            hop.exec()
            if hop.clickedButton() is b_ct:
                ten_mau, loai = '', in_an.TEN_CT
            elif hop.clickedButton() is b_th:
                ten_mau, loai = '', in_an.TEN_BTH
            elif hop.clickedButton() is b_rieng:
                import re
                from PySide6.QtWidgets import QInputDialog
                goi_y = re.sub(r'^(IN_CHITIET|IN_BANGTONGHOP)[_ -]*', '', Path(file_excel).stem, flags=re.I) or 'Mẫu 2'
                ten_mau, ok = QInputDialog.getText(self, TEN_UD, 'Tên mẫu riêng (hiện ở ô chọn mẫu khi In / Xuất):', text=goi_y)
                if not ok or not in_an.ten_mau_hop_le(ten_mau):
                    return None
            else:
                return None
        try:
            in_an.mau_de_sua()                          # bản cài: chép mẫu đang dùng sang thư mục ghi (đổi một mẫu, giữ mẫu kia)
        except Exception:
            pass
        if loai in (in_an.TEN_CT, in_an.TEN_BTH):
            try:
                ds = in_an.tao_mau_tu_excel(file_excel, in_an.thu_muc_mau_ghi(), loai=loai, ten_mau=ten_mau)
                chu = 'Đã phân tích cấu trúc file và đưa vào mẫu in.'
            except Exception:
                ds, chu = in_an.nap_mau_in(file_excel, in_an.thu_muc_mau_ghi(), ten_mau=ten_mau)
        else:
            ds, chu = in_an.nap_mau_in(file_excel, in_an.thu_muc_mau_ghi(), ten_mau=ten_mau)
        if cho:
            QMessageBox.information(self, TEN_UD, (('Mẫu riêng "' + in_an.ten_mau_hop_le(ten_mau) + '". ' if ten_mau else
                                                    'Mẫu in chính. ') + chu + '\n' + '\n'.join(str(p) for p in ds)))
        return ds

    def du_an_moi(self, cho: bool = True):
        """Dự án mới từ dữ liệu thô: 4 bước, tự lập phương án, xuất 2 bảng in; xong thì mở dự án."""
        from .man_hinh_du_an_moi import HopDuAnMoi
        dlg = HopDuAnMoi(self)
        if not cho:
            return dlg
        if dlg.exec() and dlg.ket_qua:
            self.mo_ket_qua_du_an_moi(dlg.ket_qua)
        return dlg

    def mo_ket_qua_du_an_moi(self, kq: dict):
        self.mo(kq['file'])
        tb = (f'Đã tạo dự án: {kq["so_ho"]} hộ, {kq["so_thua"]} thửa; {kq["so_ho_co_pa"]} hộ đã có phương án, '
              f'tổng {vn(kq["tong"])} đồng.')
        if kq.get('in'):
            tb += f'\n\nĐã xuất {len(kq["in"]["excel"])} file Excel' + (f', {len(kq["in"]["pdf"])} file PDF' if kq['in']['pdf'] else '') \
                  + f' vào:\n{kq["thu_muc_in"]}'
        from .giao_dien import hop_ket_qua                  # ô cuộn: đủ mọi điểm cần xem lại, nút Đóng luôn trong màn hình
        hop_ket_qua(self, tb, kq['canh_bao'], tieu_de=TEN_UD)

    def bo_don_gia(self, cho: bool = True):
        from .man_hinh_don_gia import HopBoDonGia
        if cho and hasattr(self, 'khung_tab') and 'don_gia' in self.khung_tab.khoa:
            self._dam_bao_tab('don_gia')
            return self.khung_tab.widget.get('don_gia')
        dlg = HopBoDonGia(self, self.con, self.chi_doc)
        if not cho:
            return dlg
        self._nhung_hop(dlg)
        self._dam_bao_tab('don_gia', TEN_TAB['don_gia'], widget=dlg, dong_duoc=True)
        dlg.finished.connect(lambda *_: self._khi_hop_nhung_xong(dlg))
        return dlg

    def don_gia_rieng(self, cho: bool = True, the: int = 0):
        """Quy ước giá tương đương nhập tay và đơn giá thẩm định giá (tài sản đặc biệt) của dự án đang mở."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh_don_gia_rieng import HopDonGiaRieng
        dlg = HopDonGiaRieng(self.con, self, self.dm, self.chi_doc, the)
        if not cho:
            return dlg
        dlg.exec()
        if dlg.da_luu:
            self.dm = lap_pa.DanhMuc(self.con)      # danh sách chọn nhanh dựng lại theo quy ước mới
        return dlg

    def nap_danh_muc(self, file_excel=None, xac_nhan=None):
        """Thay danh mục đơn giá, tham số, biểu thưởng của dự án đang mở bằng danh mục trong một file PABT Excel."""
        if self.con is None or self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Hãy mở một dự án (để sửa) trước.')
            return None
        if file_excel is None:
            file_excel, _ = QFileDialog.getOpenFileName(self, 'Chọn file PABT Excel có danh mục đơn giá', '',
                                                        'File PABT Excel (*.xlsm *.xlsx)')
            if not file_excel:
                return None
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Thay toàn bộ danh mục đơn giá, hỗ trợ, tham số, biểu thưởng, giá đất '
                                                          'của dự án bằng danh mục trong file đã chọn?\n\n'
                                                          'Hồ sơ hộ, thửa và phương án đã lập giữ nguyên.') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        from . import nhap_tho
        try:
            with con_tro_cho():
                dem = nhap_tho.nap_danh_muc(self.file, file_excel)
        except Exception as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không nạp được danh mục', e))
            return None
        self.dm = lap_pa.DanhMuc(self.con)
        self.tai_lai()
        self.statusBar().showMessage(f'Đã nạp danh mục: {dem["dm_taisan"]} tài sản, cây trồng; {dem["dm_hotro"]} khoản hỗ trợ; '
                                     f'{dem["tham_so"]} tham số; {dem["gia_dat"]} dòng giá đất.', 15000)
        return dem

    def ra_soat_gia(self, cho: bool = True):
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopRaSoat
        dlg = HopRaSoat(lap_pa.ra_soat_gia(self.con, self.dm), self)
        if cho and dlg.exec() and dlg.ma_ho_chon is not None:
            self.mo_lap_pa(dlg.ma_ho_chon)
        return dlg

    def xuat_bao_cao(self):
        if self.kq is None or self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return
        mac_dinh = str(self.file.with_name(self.file.stem + '_DoiChieu.xlsx'))
        p, _ = QFileDialog.getSaveFileName(self, 'Lưu báo cáo đối chiếu', mac_dinh, 'File Excel (*.xlsx)')
        if not p:
            return
        da = self.con.execute('SELECT ten, nguon_nhap FROM du_an WHERE id = 1').fetchone()
        from . import doi_chieu
        try:
            with con_tro_cho():
                rs = lap_pa.ra_soat_gia(self.con, self.dm)
                from .giao_dien import chay_nen             # chỉ ghi Excel (số liệu đã có): chạy nền
                chay_nen(self, lambda: doi_chieu.xuat_bao_cao(self.kq, p, da['ten'], da['nguon_nhap'], rs),
                         'Đang ghi báo cáo đối chiếu…')
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file', e))
            return
        QMessageBox.information(self, TEN_UD, f'Đã lưu báo cáo:\n{p}')

    # ------------------------------------------------ quản lý hồ sơ trình, tiến độ
    def _can_du_an(self, sua: bool = False) -> bool:
        if self.con is None or (sua and self.chi_doc):
            QMessageBox.information(self, TEN_UD, 'Hãy mở một dự án (để sửa) trước.' if sua else 'Hãy nhập hoặc mở một dự án trước.')
            return False
        return True

    def _tong_pa(self) -> dict:
        return {h['ma_ho']: h['tong'] for h in (self.kq.ho if self.kq else [])}

    def luu_du_an_thanh(self, dich=None, mo_ban_moi: bool | None = None):
        """Lưu (chép) file dự án đang mở sang đường dẫn khác, ví dụ vào thư mục hồ sơ dự án; rồi làm việc trên bản mới."""
        if not self._can_du_an():
            return None
        from . import quan_ly
        if dich is None:
            goc = quan_ly.thu_muc_ho_so(self.con, self.file)
            mac_dinh = str((goc if goc.exists() else self.file.parent) / self.file.name)
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu dự án thành', mac_dinh, csdl.LOC_LUU)
            if not dich:
                return None
        dich = Path(dich)
        if dich.resolve() == self.file.resolve():
            QMessageBox.information(self, TEN_UD, 'Đây là file đang mở: không cần lưu thành.')
            return None
        k = khoa.KhoaFile(dich).nguoi_khac()
        if k:
            QMessageBox.warning(self, TEN_UD, f'File đích đang được sửa trên {khoa.mo_ta(k)}.')
            return None
        try:
            p = quan_ly.luu_thanh(self.con, dich)
        except Exception as e:                         # thư mục không ghi được, file đích đang mở, SQLite...
            QMessageBox.warning(self, TEN_UD, chu_loi('Không lưu được', e))
            return None
        if mo_ban_moi is None:
            mo_ban_moi = QMessageBox.question(self, TEN_UD, f'Đã lưu dự án thành:\n{p}\n\nLàm việc tiếp trên file mới này?') \
                == QMessageBox.StandardButton.Yes
        if mo_ban_moi:
            self.mo(p, chi_doc=False)
        return p

    def dot_trinh(self, cho: bool = True):
        if not self._can_du_an():
            return None
        from .man_hinh_quan_ly import HopDotTrinh
        dlg = HopDotTrinh(self.con, self, self.ho_da_chon(), self.file, self.chi_doc)
        if not cho:
            return dlg
        dlg.exec()
        if dlg.thay_doi:
            self.tai_lai()
        if getattr(dlg, 'mo_xuat_dot', None) is not None:      # nút "Xuất bản hồ sơ đợt này": sang Trung tâm Xuất bản với đợt đó
            self.in_xuat(dot_id=dlg.mo_xuat_dot, che_do='chinh_thuc')
        return dlg

    def trang_thai_ho(self, ds_ma_ho: list | None = None, cho: bool = True):
        if not self._can_du_an(sua=True):
            return None
        ds = ds_ma_ho if ds_ma_ho is not None else self.ho_da_chon()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chọn một hoặc nhiều hộ trong danh sách (giữ Ctrl / Shift để chọn nhiều).')
            return None
        if len(ds) == 1:                        # một hộ: các quyết định (phê duyệt bổ sung), chi trả từng quyết định, bàn giao
            from .man_hinh_theo_doi import HopHoTheoDoi
            dlg = HopHoTheoDoi(self.con, ds[0], self, self._tong_pa().get(ds[0]))
        else:
            from .man_hinh_quan_ly import HopTrangThai
            dlg = HopTrangThai(self.con, ds, self, self._tong_pa())
        if not cho:
            return dlg
        if dlg.exec():
            self.tai_lai(giu_trang=True)
        return dlg

    def bao_cao_tong_hop(self, file=None, ds=None, dieu_kien: str | None = None, ten_file: str = '', tieu_de: str = '',
                         hoi: bool = True):
        """Báo cáo tổng hợp (Excel) các hộ đang hiện theo bộ lọc (đợt, trạng thái, từ khóa) - hoặc các hộ ds (Xuất danh sách hộ)."""
        if not self._can_du_an():
            return None
        from . import quan_ly
        ds = self.ho_dang_loc() if ds is None else ds
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Không có hộ nào theo bộ lọc hiện tại.')
            return None
        if file is None:
            goc = quan_ly.thu_muc_ho_so(self.con, self.file)
            mac_dinh = str((goc if goc.exists() else self.file.parent) / (ten_file or f'BaoCaoTongHop_{self.file.stem}.xlsx'))
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu danh sách hộ' if ten_file else 'Lưu báo cáo tổng hợp', mac_dinh,
                                                  'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            with con_tro_cho():
                # số liệu đọc ở đây (kết quả tính dùng chung), ghi Excel ở luồng nền: hàng nghìn hộ không "Không phản hồi"
                so_lieu = quan_ly.du_lieu_bao_cao(self.con, ds)
                dk = self.mo_ta_loc() if dieu_kien is None else dieu_kien
                from .giao_dien import chay_nen
                p = chay_nen(self, lambda: quan_ly.ghi_bao_cao_tong_hop(so_lieu, file, tieu_de, dk),
                             f'Đang ghi {len(ds)} hộ ra Excel…')
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file', e))
            return None
        if hoi and QMessageBox.question(self, TEN_UD, f'Đã lưu {len(ds)} hộ:\n{p}\n\nMở file?') == QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(p)
        return p

    def xuat_danh_sach(self, file=None, hoi: bool = True):
        """Nút "Xuất" (thanh công cụ danh sách hộ, người dùng 11/10/2026): Excel danh sách hộ để theo dõi, trình, lưu trữ - các hộ
        đang chọn (từ 2 hộ), không thì các hộ đang hiện theo Đợt / Trạng thái / Tìm. Cùng bảng với Báo cáo tổng hợp (đợt, tiền
        từng mục, phê duyệt / chi trả / bàn giao, ghi chú theo dõi); tên file theo đợt, trạng thái, giờ xuất."""
        if not self._can_du_an():
            return None
        import re
        from datetime import datetime
        loc = self.mo_ta_loc()
        chon = set(self.ho_da_chon()) if self._khung_dang_xem() is None else set()
        if len(chon) >= 2:
            ds = [m for m in self.ho_dang_loc() if m in chon]
            ds += sorted(chon - set(ds))
            dk = f'{len(ds)} hộ đang chọn' + (f' (trong danh sách lọc: {loc})' if loc else '')
        else:
            ds, dk = self.ho_dang_loc(), loc
        phan = [cb.currentText() for cb in (self.cb_dot, self.cb_tt) if cb.currentData()] + (['Chon'] if len(chon) >= 2 else [])
        ten = re.sub(r'[\\/:*?"<>|\s]+', '_', '_'.join(phan or ['TatCa'])).strip('_')[:80]
        return self.bao_cao_tong_hop(file, ds=ds, dieu_kien=dk, tieu_de='DANH SÁCH HỘ BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ',
                                     ten_file=f'DanhSachHo_{ten}_{datetime.now():%Y%m%d_%H%M}.xlsx', hoi=hoi)

    def kiem_tra_loi(self, cho: bool = True):
        if not self._can_du_an():
            return None
        from .man_hinh_quan_ly import HopKiemLoi
        da = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        dlg = HopKiemLoi(self.con, self, self.dm, self.chi_doc, da['ten'] if da else '')
        if not cho:
            return dlg
        dlg.exec()
        if dlg.da_sua:
            self.tai_lai()
        if dlg.ma_ho_chon is not None:
            if self.chi_doc:
                ChiTietHo(self.con, dlg.ma_ho_chon, self).exec()
            else:
                self.mo_lap_pa(dlg.ma_ho_chon)
        return dlg

    def du_toan(self, cho: bool = True):
        """Trang Dự toán & khái toán (0.9.23: trang trong cửa sổ chính, trước là hộp thoại riêng). Trả KhungDuToan."""
        self.mo_trang(TRANG_DU_TOAN)
        return self.khung_du_toan

    def chon_ho_niem_yet(self, cho: bool = True):
        """Chọn hộ đủ điều kiện niêm yết công khai, lấy ý kiến (0.9.69): các hộ đang chọn trên danh sách (từ 2 hộ), không thì
        cả dự án. Lưu -> ho.du_dieu_kien (+ đưa vào đợt niêm yết nếu chọn) -> nạp lại tab Niêm yết & Lấy ý kiến nếu đang mở."""
        if self.con is None:
            return None
        from .man_hinh_du_thao import HopChonNiemYet
        ds = self.ho_da_chon()
        d = HopChonNiemYet(self, self.con, ds if len(ds) >= 2 else None, self.chi_doc)
        if not cho:
            return d
        if d.exec() == QDialog.DialogCode.Accepted:
            w = self.khung_tab.widget.get('du_thao')
            if w is not None and getattr(w, 'con', None) is self.con:
                w.nap()
        return d

    def _khai_toan_dang_mo(self):
        """Bảng khái toán đang mở ở Nhóm 1 (thẻ Đối soát dự toán Pre-F/S dùng làm khái toán ban đầu); chưa mở / chưa có dòng: None."""
        k = self.khung_du_toan
        return k.dt if k is not None and k.dt.dong else None

    def so_sanh_du_toan(self):
        """Menu trái "So sánh với thực tế" (0.9.70): trang Khái toán, thẻ So sánh với thực tế áp giá."""
        k = self.du_toan(cho=False)
        if k is not None:
            k.tab.setCurrentIndex(1)
        return k

    def mo_du_thao(self, cho: bool = True):
        """Mở tab Dự thảo PABT của dự án đang mở (niêm yết, ý kiến, đối thoại, hộ vướng)."""
        if self.con is None:
            if cho:
                QMessageBox.information(self, TEN_UD, 'Mở một dự án trước khi lập dự thảo.')
            return None
        if 'du_thao' in self.khung_tab.widget:
            w = self.khung_tab.widget['du_thao']
            if getattr(w, 'con', None) is not self.con:
                self._tab_dong(self.khung_tab.khoa.index('du_thao'))
            else:
                w.nap()
                self._dam_bao_tab('du_thao', TEN_TAB['du_thao'], w, True)
                return w
        from .man_hinh_du_thao import KhungDuThao
        w = KhungDuThao(self.con, self, chi_doc=self.chi_doc)
        self._dam_bao_tab('du_thao', TEN_TAB['du_thao'], w, True)
        return w

    def bang_gia_dat(self, cho: bool = True):
        """Bảng giá đất NQ 28/2025 (tra cứu theo địa bàn của dự án đang mở)."""
        from .man_hinh_du_toan import HopTraNQ28
        xa = ''
        if self.con is not None:
            r = self.con.execute('SELECT ten_dia_ban FROM du_an WHERE id = 1').fetchone()
            xa = (r[0] or '') if r else ''
        d = HopTraNQ28(self, xa)
        if cho:
            d.exec()
        return d

    def cap_nhat_bang_gia_dat(self, cho: bool = True):
        """Tải bảng giá đất từ web hoặc file. Bảng mới thay bốn địa bàn gắn sẵn."""
        from .man_hinh_gia_dat import HopCapNhatGiaDat
        d = HopCapNhatGiaDat(self)
        if cho:
            d.exec()
        return d

    def lich_su_cap_nhat(self, cho: bool = True):
        """Chân trang: lịch sử cập nhật từ 0.9.53. Không mang các bản đã phát hành trước đó."""
        from PySide6.QtWidgets import QDialogButtonBox, QTextBrowser
        from .lich_su_cap_nhat import MUC
        d = QDialog(self)
        d.setWindowTitle(f'Lịch sử cập nhật phần mềm - {TEN_UD}')
        d.resize(640, 420)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(False)
        if MUC:
            khoi = []
            for pb, ngay, dong in MUC:
                khoi.append(f'## Phiên bản {pb}  ·  {ngay}')
                khoi.extend(f'- {x}' for x in dong)
                khoi.append('')
            tb.setMarkdown('\n'.join(khoi))
        else:
            tb.setPlainText('Chưa có mục lịch sử.')
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(d.reject)
        lo = QVBoxLayout(d)
        lo.addWidget(tb)
        lo.addWidget(nut)
        from .giao_dien import vua_man_hinh
        vua_man_hinh(d)
        if cho:
            d.exec()
        return d

    def huong_dan(self, cho: bool = True):
        """Hướng dẫn sử dụng (HUONG_DAN.md đóng gói kèm) - F1."""
        from PySide6.QtWidgets import QDialogButtonBox, QTextBrowser
        d = QDialog(self)
        d.setWindowTitle(f'Hướng dẫn sử dụng - {TEN_UD}')
        d.resize(1000, 720)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        f = file_huong_dan()
        if f is not None:
            tb.setMarkdown(f.read_text(encoding='utf-8'))
        else:
            tb.setPlainText('Không tìm thấy file hướng dẫn (HUONG_DAN.md) trong thư mục cài phần mềm.')
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(d.reject)
        lo = QVBoxLayout(d)
        lo.addWidget(tb)
        lo.addWidget(nut)
        from .giao_dien import vua_man_hinh
        vua_man_hinh(d)
        if cho:
            d.exec()
        return d

    def dong_du_an_lenh(self):
        """Lệnh Tệp tin → Đóng dự án: đóng file đang mở, về màn hình chào."""
        if self.dong_du_an() is False:
            return
        self.file = None
        self.dat_tieu_de()

    def quy_chuan(self, cho: bool = True):
        if not self._can_du_an():
            return None
        from .man_hinh_cay import HopQuyChuan
        dlg = HopQuyChuan(self.con, self, self.chi_doc)
        if cho:
            dlg.exec()
        return dlg

    def cap_nhat_phan_mem(self, file=None):
        from .man_hinh_cap_nhat import HopCapNhat
        h = HopCapNhat(self)
        if file:
            h.show()
            h.cai_file(file)
        h.exec()

    def gioi_thieu(self):
        from . import dia_phuong, to_chuc
        from .cap_nhat import ban_goc
        goc = ban_goc()
        pb = f'Phiên bản {__version__}' + (f' (bản cập nhật, bản cài gốc {goc})' if goc != __version__ else '') + \
            (f' - {NHAN_THU_NGHIEM}' if BAN_THU_NGHIEM else '') + '.'
        from .ban_quyen import mo_ta
        QMessageBox.about(self, TEN_UD, f'{TEN_UD}\n{pb}\n{mo_ta()}.\nHồ sơ địa phương: {dia_phuong.ten_ho_so()}.\n'
                                        f'{to_chuc.TAC_GIA}.')

    # ------------------------------------------------ gói mẫu in & cấu hình (.pabtcfg, 0.9.85)
    def xuat_goi_mau(self, file=None, cho: bool = True):
        """Đóng gói hồ sơ địa phương + mẫu in / mẫu văn bản trình đang dùng thành file .pabtcfg để gửi máy khác. Trả danh sách gói."""
        import re
        from datetime import datetime
        from . import dia_phuong, goi_mau
        from .lap_pa import bo_dau
        if file is None:
            ten = re.sub(r'[^\w\-]+', '_', bo_dau(dia_phuong.ten_ho_so()))[:40].strip('_') or 'LARC'
            mac = Path.home() / 'Documents' / f'PABT_MauIn_{ten}_{datetime.now():%Y%m%d}{goi_mau.DUOI}'
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu gói mẫu in & cấu hình', str(mac),
                                                  f'Gói mẫu in & cấu hình PABT (*{goi_mau.DUOI})')
            if not file:
                return None
        try:
            with con_tro_cho():
                ds = goi_mau.tao_goi(file, mo_ta=f'Xuất từ {__version__}')
        except goi_mau.LoiGoiMau as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if cho:
            mau = [t['ten'][len('mau_in/'):] for t in ds['tep'] if t['ten'].startswith('mau_in/')]
            QMessageBox.information(self, TEN_UD, f'Đã đóng gói hồ sơ địa phương "{ds["ho_so"]}" và {len(mau)} mẫu:\n'
                                    f'{ds["file"]}\n\nGửi file này qua Zalo / email; máy nhận bấm đúp file (hoặc Công cụ → Nhập '
                                    'gói mẫu in & cấu hình…) là cập nhật, không cần cài lại phần mềm.')
        return ds

    def nhap_goi_mau(self, file=None, xac_nhan: bool = True):
        """Cài gói .pabtcfg: kiểm tra, hỏi, sao lưu mẫu cũ, thay mẫu + hồ sơ địa phương. Trả kết quả goi_mau.cai hoặc None."""
        from . import goi_mau
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn gói mẫu in & cấu hình', str(Path.home() / 'Downloads'),
                                                  f'Gói mẫu in & cấu hình PABT (*{goi_mau.DUOI})')
            if not file:
                return None
        try:
            with con_tro_cho():
                ds = goi_mau.doc_goi(file)
        except goi_mau.LoiGoiMau as e:
            QMessageBox.warning(self, TEN_UD, chu_loi(f'Không nhập được gói {Path(file).name}', e))
            return None
        if xac_nhan and QMessageBox.question(
                self, TEN_UD, 'Cài gói mẫu in & cấu hình?\n\n' + '\n'.join(goi_mau.mo_ta_goi(ds)) +
                '\n\nMẫu / hồ sơ cũ được sao lưu trước khi thay.') != QMessageBox.StandardButton.Yes:
            return None
        try:
            kq = goi_mau.cai(file)
        except goi_mau.LoiGoiMau as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if self.con is not None:
            self.tai_lai()                              # băng tiêu đề lấy tên đơn vị mặc định mới khi dự án để trống
        else:
            self._hien_trang_chao()
        if xac_nhan:
            QMessageBox.information(self, TEN_UD, f'Đã cài {len(kq["mau"])} mẫu' + (' và hồ sơ địa phương' if kq['ho_so'] else '') +
                                    f'.\nHồ sơ địa phương đang dùng: {kq["ten_ho_so"]}' +
                                    (f'\nBản cũ sao lưu ở: {kq["sao_luu"]}' if kq['sao_luu'] else ''))
        return kq

    # ------------------------------------------------ máy chủ LAN, tài khoản
    def dat_tieu_de(self):
        """Tiêu đề cửa sổ = chỗ DUY NHẤT hiện tên dự án (15/10/2026, người dùng: trước đây lặp ở banner và dòng dưới banner):
        "PABT - <tên dự án> · <địa bàn> (<file>)"; chưa mở dự án: "PABT - Lập phương án bồi thường, hỗ trợ". Thanh tiêu đề hợp
        nhất hiện ở giữa thanh menu trắng (dài thì rút "…" ở giữa, đủ chữ ở chú thích)."""
        t = TIEU_DE_CUA_SO
        if self.file is None:
            t += ' - ' + MO_TA_UD
        else:
            ten = dia_ban = ''
            if self.con is not None:
                try:
                    da = self.con.execute('SELECT ten, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
                except sqlite3.Error:
                    da = None
                if da is not None:
                    ten, dia_ban = (str(da[0] or '').strip(), str(da[1] or '').strip())
            if ten:
                t += f' - {ten}' + (f' · {dia_ban}' if dia_ban else '') + f' ({self.file.name})'
            else:
                t += f' - {self.file.name}'
            if self.chi_doc:
                t += '  [CHỈ XEM]'
            try:
                if may_chu.thu_muc_offline() in self.file.resolve().parents:
                    t += '  [BẢN LÀM OFFLINE]'
            except OSError:
                pass
        if may_chu.PHIEN is not None:
            t += f'  ·  {may_chu.PHIEN.ten_hien}'
        self.setWindowTitle(t)

    def cap_nhat_tai_khoan(self):
        # đèn báo mạng LAN (đặc tả: Online / Offline trên thanh trạng thái) gộp vào nút tài khoản - một chỗ
        p = may_chu.PHIEN
        if p is not None:
            self.nut_tk.setText(f'● LAN: Trực tuyến · Tài khoản: {p.ten_hien}')
            self.nut_tk.setToolTip(f'Đăng nhập máy chủ {p.goc}')
            mau = '#107C41'
        elif may_chu.doc_cau_hinh().get('may_chu'):
            self.nut_tk.setText('● LAN: Ngoại tuyến (Offline) · Đăng nhập máy chủ')
            self.nut_tk.setToolTip('Đang làm việc offline với file trên máy này')
            mau = '#B86E00'
        else:
            self.nut_tk.setText('● Máy đơn · Máy chủ LAN')
            self.nut_tk.setToolTip('Không dùng máy chủ trong mạng nội bộ. Bấm để thiết lập (không bắt buộc).')
            mau = '#5F6368'
        self.nut_tk.setStyleSheet(f'QToolButton {{ color: {mau}; font-weight: 600; }}')
        self.dat_tieu_de()

    def _menu_tai_khoan(self):
        m = self.nut_tk.menu()
        m.clear()
        p = may_chu.PHIEN
        # chỉ việc của tài khoản; mở / mang về / đưa lên dự án trên máy chủ: "Dự án" → "Dự án trên máy chủ…" (trước 0.9.18 lặp
        # thêm ở đây dưới 2 tên khác: "Dự án trên máy chủ, làm offline…", "Dự án đã mang về làm offline…")
        if p is not None:
            m.addAction(f'Máy chủ: {p.goc}').setEnabled(False)
            m.addAction('Đổi mật khẩu…', lambda: self.doi_mat_khau())
            if p.la_quan_tri:
                m.addAction('Quản lý tài khoản người dùng…', lambda: self.quan_ly_tai_khoan())
            m.addSeparator()
            m.addAction('Đăng xuất', lambda: self.dang_xuat())
        else:
            m.addAction('Đăng nhập máy chủ…', lambda: self.dang_nhap())
        m.addSeparator()
        m.addAction('Thiết lập máy chủ…', lambda: self.thiet_lap_may_chu())

    def dang_nhap(self, cho: bool = True, tu_mo_lai: bool = True):
        """Hộp đăng nhập; đăng nhập được thì mở lại dự án làm gần nhất của tài khoản (ở máy bất kỳ)."""
        from .man_hinh_may_chu import HopDangNhap
        dlg = HopDangNhap(self)
        if not cho:
            return dlg
        dlg.exec()
        self.sau_dang_nhap(tu_mo_lai and self.con is None)
        return dlg

    def sau_dang_nhap(self, tu_mo_lai: bool = True):
        self.cap_nhat_tai_khoan()
        if may_chu.PHIEN is None:
            return None
        if self.con is not None and not self.chi_doc:       # nhật ký kiểm toán ghi đúng tài khoản vừa đăng nhập
            from . import kiem_toan
            try:
                kiem_toan.dat_phien(self.con)
            except sqlite3.Error:
                pass
        cuoi = None
        if tu_mo_lai:
            try:
                cuoi = may_chu.du_an_cuoi()
            except (may_chu.LoiMayChu, OSError):
                cuoi = None
        if cuoi is not None:
            self.mo(cuoi)
            self.statusBar().showMessage(f'Xin chào {may_chu.PHIEN.ten_hien}: đã mở lại dự án đang làm - {cuoi.name}', 15000)
        else:
            self.statusBar().showMessage(f'Xin chào {may_chu.PHIEN.ten_hien}. Dự án dùng chung: nút "Dự án trên máy chủ…".', 15000)
        return cuoi

    def dang_xuat(self, xac_nhan: bool | None = None):
        if may_chu.PHIEN is None:
            return
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Đăng xuất tài khoản? Dự án đang mở sẽ được đóng.') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return
        self.dong_du_an()
        self.file = None
        self._xoa_ket_qua()
        may_chu.dang_xuat()
        self.cap_nhat_tai_khoan()

    def thiet_lap_may_chu(self):
        from .man_hinh_may_chu import HopThietLap
        dlg = HopThietLap(self)
        if dlg.exec():
            if dlg.goc and may_chu.PHIEN is None:
                self.dang_nhap()
            elif not dlg.goc:
                self.cap_nhat_tai_khoan()
        return dlg

    def doi_mat_khau(self):
        from .man_hinh_may_chu import HopDoiMatKhau
        HopDoiMatKhau(self).exec()

    def quan_ly_tai_khoan(self):
        from .man_hinh_may_chu import HopTaiKhoan
        HopTaiKhoan(self).exec()

    def du_an_may_chu(self, cho: bool = True):
        if may_chu.PHIEN is None and not may_chu.ds_lay_ve_cuc_bo():
            if QMessageBox.question(self, TEN_UD, 'Chưa đăng nhập máy chủ. Đăng nhập (hoặc thiết lập máy chủ) ngay?') \
                    == QMessageBox.StandardButton.Yes:
                self.dang_nhap(tu_mo_lai=False)
            if may_chu.PHIEN is None:
                return None
        from .man_hinh_may_chu import HopDuAnMayChu
        if self.file is not None and may_chu.thu_muc_offline() in self.file.resolve().parents:
            self.dong_du_an()                       # để đưa lên / hủy được bản offline đang mở
        dlg = HopDuAnMayChu(self)
        if not cho:
            return dlg
        if dlg.exec() and dlg.mo_file is not None:
            self.mo(dlg.mo_file)
        return dlg

    def khoi_dong_may_chu(self, mo_lai: bool = True):
        """Khi mở phần mềm: có thiết lập máy chủ và kết nối được thì hiện đăng nhập; không thì làm việc offline bình thường."""
        goc = may_chu.doc_cau_hinh().get('may_chu')
        if not goc:
            return 'khong_dung'
        from .man_hinh_may_chu import ket_noi_duoc      # luồng nền: máy chủ không tới được thì cửa sổ không đứng hình 4 giây
        if ket_noi_duoc(self, goc):
            self.dang_nhap(tu_mo_lai=mo_lai)
            return 'dang_nhap' if may_chu.PHIEN is not None else 'offline'
        self.cap_nhat_tai_khoan()
        off = may_chu.ds_lay_ve_cuc_bo()
        self.statusBar().showMessage(f'Không kết nối được máy chủ {goc}: đang làm việc offline'
                                     + (f' ({len(off)} dự án đã mang về máy này).' if off else '.'), 20000)
        if off and mo_lai and self.con is None and QMessageBox.question(
                self, TEN_UD, f'Không kết nối được máy chủ:\n{goc}\n\nMáy này có {len(off)} dự án đã mang về làm offline. '
                              'Mở danh sách để làm tiếp?') == QMessageBox.StandardButton.Yes:
            self.du_an_may_chu()
        return 'mat_ket_noi'

    def closeEvent(self, e):
        from .giao_dien import KHI_DOI_TY_LE, XU_LY_HOAN_TAC
        if self._hien_ty_le in KHI_DOI_TY_LE:
            KHI_DOI_TY_LE.remove(self._hien_ty_le)
        if self.hoan_tac_phim in XU_LY_HOAN_TAC:
            XU_LY_HOAN_TAC.remove(self.hoan_tac_phim)
        self.dong_du_an()
        if may_chu.PHIEN is not None:                   # ghi "Đăng xuất" lên máy chủ: chờ tối đa 3 giây (mất mạng không treo lúc đóng)
            import threading
            t = threading.Thread(target=may_chu.dang_xuat, daemon=True)
            t.start()
            t.join(3)
        super().closeEvent(e)


def hien_cua_so(w) -> None:
    """Hiện cửa sổ chính phóng to. Kích thước thường đặt trước bằng vùng làm việc của màn hình: kiểu chữ / màu áp lúc Show
    (_BoToMau) làm bề rộng tối thiểu tăng; lớn hơn kích thước thường (từng 1414 > 1360 điểm) thì Qt ép lại kích thước SAU khi phóng
    to -> Windows vẫn ghi "phóng to" nhưng cửa sổ chỉ 1414 x 760, phần màn hình còn lại hiện cửa sổ phía sau (người dùng 11/10/2026:
    lỗi hình góc trên bên phải). Không hiện thường rồi mới phóng to: khung đầu tiên đen."""
    from .giao_dien import kich_thuoc_thuong
    # kích thước THƯỜNG = 1200 x 740 canh giữa (đặc tả V10): nút Thu về / Restore Down của Windows trả cửa sổ về đây, không còn "thu
    # về" mà vẫn kín màn hình (trước 0.9.77 kích thước thường = cả vùng làm việc)
    w.setGeometry(kich_thuoc_thuong(w))
    w.showMaximized()


APP_USER_MODEL_ID = 'gov.pabt.boithuong.enterprise.2026'


def dat_app_user_model_id() -> bool:
    """Windows: định danh ứng dụng riêng cho taskbar (0.9.74 - người dùng 13/10/2026) - gọi TRƯỚC khi tạo QApplication. Không có
    thì khi chạy bằng python.exe (mã nguồn) taskbar gộp vào biểu tượng Python; bản exe cũng gộp cửa sổ đúng nhóm PABT."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        return True
    except Exception:                                   # noqa: BLE001 - Windows quá cũ / thiếu API: bỏ qua, không chặn khởi động
        return False


def main() -> int:
    dat_app_user_model_id()
    app = QApplication(sys.argv)
    app.setApplicationName('PABT')
    from .giao_dien import ap_dung, cai_bat_loi
    ap_dung(app)
    cai_bat_loi()                                      # lỗi trong nút bấm: báo + ghi loi.log (trước đây mất im lặng)
    from .ban_quyen import kiem_tra_ban_quyen          # cổng chờ bản quyền (giai đoạn này luôn hợp lệ - ban_quyen.py)
    if not kiem_tra_ban_quyen():
        QMessageBox.critical(None, TEN_UD, 'Bản quyền phần mềm không hợp lệ hoặc đã hết hạn.')
        return 1
    menu_trai = '--menu-tren' not in sys.argv              # từ 0.9.3: menu dọc bên trái thay thanh nút phía trên
    w = CuaSoChinh(menu_trai=menu_trai)
    from .giao_dien import bieu_tuong
    w.setWindowIcon(bieu_tuong())                       # (app.setWindowIcon ở ap_dung đã gán cho mọi cửa sổ; gắn thẳng cho chắc)
    w.dat_tieu_de()
    tep = [a for a in sys.argv[1:] if not a.startswith('--')]
    co_file = bool(tep and csdl.la_file_du_an(tep[0]))
    hien_cua_so(w)                         # dùng hết màn hình: thanh nút gọn 2 dòng, danh sách hộ rộng
    w.khoi_dong_may_chu(mo_lai=not co_file)   # máy chủ LAN (nếu có thiết lập): đăng nhập, mở lại dự án đang làm
    if co_file:
        w.mo(tep[0])
    try:
        import nap_cap_nhat
        QTimer.singleShot(5000, nap_cap_nhat.khoi_dong_tot)
    except ImportError:
        pass
    if tep and tep[0].lower().endswith('.pabtcn'):                          # nhấp đúp gói cập nhật
        QTimer.singleShot(0, lambda: w.cap_nhat_phan_mem(tep[0]))
    if tep and tep[0].lower().endswith('.pabtcfg'):                         # nhấp đúp gói mẫu in & cấu hình (0.9.85)
        QTimer.singleShot(0, lambda: w.nhap_goi_mau(tep[0]))
    from . import dia_phuong
    if dia_phuong.loi():                                                    # hồ sơ địa phương trên máy sai: đang dùng mặc định
        QTimer.singleShot(800, lambda: QMessageBox.warning(
            w, TEN_UD, 'Hồ sơ địa phương trên máy chưa hợp lệ, phần mềm đang dùng hồ sơ mặc định:\n\n' + '\n'.join(dia_phuong.loi()) +
            f'\n\nSửa file {dia_phuong.file_may()} hoặc nhập lại gói .pabtcfg.'))
    return app.exec()
